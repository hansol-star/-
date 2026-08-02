#!/usr/bin/env python3
"""history_backfill.py — 상장 이래 전 일봉 소급·캐시 엔진 (stdlib only·무키·포터블)

동기(정훈 2026-07-21): "데이터가 6/12~13부터라 22일치뿐. 그 앞도 찾아낼 수 있잖아 —
최대한 많이 가져와서 분석하자." 실측 결과 Yahoo v8 chart에 period1=0을 넣으면 상장
이래 진짜 일봉이 전부 나온다(코스피 7,287일·29.6년, NVDA 6,914일 등 — range=max는
월봉 다운샘플이라 오답, period1/period2가 정답). 측정 3종(폭풍·GARCH·차트지표)은
전부 '가격의 순수 함수'라 과거 종가만 확보하면 과거 전 구간을 그대로 재계산할 수 있다.

성격: **데이터 수집·캐시 전용.** 어떤 룰도 안 바꾼다. vol_gauge·garch·chart_read가
이 캐시를 소비해 장기 백분위·GARCH 적합·역사 유사국면 분석을 한다.

캐시: data/history/<safe_symbol>.csv  (헤더 date,close — 종가는 정적이라 1회 확보 후
재사용, 매일 tail만 증분 append). 매니페스트 data/history/_manifest.json.
소급 불가 2종(외인·기관 수급 / 우리 포트폴리오 의사결정)은 이 엔진 범위 밖 — 그건
flows.json·decisions.jsonl이 정본이고 22~27일치 그대로.

사용:
  python3 history_backfill.py                 # 유니버스 증분 갱신(캐시 있으면 tail만)
  python3 history_backfill.py --refresh        # 전체 재풀(상장~오늘)
  python3 history_backfill.py --stats          # 캐시 현황(심볼·기간·일수)
  python3 history_backfill.py --symbols ^KS11,NVDA
  python3 history_backfill.py --json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import cli_common

try:  # 유니버스는 market_data(=portfolio.json 정본) 재사용 — 티커 드리프트 방지
    import market_data as md
except ImportError:
    md = None

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

_HERE = os.path.dirname(os.path.abspath(__file__))
HIST_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", "data", "history"))
MANIFEST = os.path.join(HIST_DIR, "_manifest.json")


def _safe(symbol: str) -> str:
    """파일명 안전화: ^KS11 → _KS11, KRW=X → KRW_X, 005930.KS → 005930.KS."""
    return symbol.replace("^", "_").replace("=", "_").replace("/", "_")


# [7/21] 해외·매크로 크로스에셋 (정훈 "해외 자료도 좋아, 다 분석 가능하잖아").
# 전부 Yahoo 무키 딥이력 실측 확인: VIX 36.5년·美10Y 56.5년·달러 55.5년·니케이 56.5년 등.
# 크로스에셋 변동성·상관·위험선호 컨텍스트용(측정 전용).
XASSET = [
    ("VIX", "^VIX"), ("美10Y금리", "^TNX"), ("美2Y금리", "^FVX"),
    ("달러지수", "DX-Y.NYB"), ("니케이225", "^N225"), ("항셍", "^HSI"),
    ("상해종합", "000001.SS"), ("유로스톡스50", "^STOXX50E"), ("러셀2000", "^RUT"),
    ("금", "GC=F"), ("비트코인", "BTC-USD"),
]


def _universe(include_xasset: bool = True) -> list[tuple[str, str]]:
    """코스피·코스닥 + 보유 + 워치 + 유가 + (해외·매크로 크로스에셋). 순수 시세축."""
    if md is None:
        base = [("코스피", "^KS11"), ("코스닥", "^KQ11")]
    else:
        g = md.GROUPS
        seen, base = set(), []
        for grp in ("index", "holdings", "watchlist", "fx", "oil"):
            for label, sym in g.get(grp, []):
                if sym not in seen:
                    seen.add(sym)
                    base.append((label, sym))
    if include_xasset:
        have = {s for _, s in base}
        base += [(l, s) for (l, s) in XASSET if s not in have]
    return base


def fetch_full_daily(symbol: str, period1: int = 0, timeout: float = 30.0):
    """상장(period1=0) → 오늘 진짜 일봉. [(date_str, close), ...] 시간순. 실패 None.
    ⚠️ range=max는 장기서 월봉 다운샘플 → 반드시 period1/period2(일봉 보장)."""
    now = int(time.time())
    url = (YAHOO_CHART.format(symbol=urllib.parse.quote(symbol))
           + f"?interval=1d&period1={period1}&period2={now}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        closes = res["indicators"]["quote"][0]["close"]
        out = []
        for t, c in zip(ts, closes):
            if c is None:
                continue
            d = time.strftime("%Y-%m-%d", time.gmtime(t))
            out.append((d, round(float(c), 4)))
        return out
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError,
            IndexError, TypeError, ValueError):
        return None


def fetch_with_backoff(symbol: str, period1: int = 0, tries: int = 4):
    """레이트리밋(429) 대비 지수백오프. 웹환경 페이싱 정책과 동일 철학."""
    delay = 3.0
    for attempt in range(tries):
        rows = fetch_full_daily(symbol, period1)
        if rows:
            return rows
        if attempt < tries - 1:
            time.sleep(delay)
            delay *= 2
    return None


def load_cached(symbol: str):
    path = os.path.join(HIST_DIR, _safe(symbol) + ".csv")
    if not os.path.exists(path):
        return []
    out = []
    with open(path, newline="") as f:
        rd = csv.reader(f)
        next(rd, None)  # 헤더
        for row in rd:
            if len(row) >= 2:
                try:
                    out.append((row[0], float(row[1])))
                except ValueError:
                    continue
    return out


def save_cached(symbol: str, rows) -> None:
    os.makedirs(HIST_DIR, exist_ok=True)
    path = os.path.join(HIST_DIR, _safe(symbol) + ".csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "close"])
        for d, c in rows:
            w.writerow([d, c])


def update_symbol(symbol: str, refresh: bool = False):
    """캐시 있으면 마지막 날 이후만 증분(period1=마지막 ts). 없거나 refresh면 전체."""
    cached = [] if refresh else load_cached(symbol)
    if cached:
        last_date = cached[-1][0]
        p1 = int(time.mktime(time.strptime(last_date, "%Y-%m-%d")))
        fresh = fetch_with_backoff(symbol, period1=p1)
        if not fresh:
            return cached, 0
        have = {d for d, _ in cached}
        added = [(d, c) for d, c in fresh if d not in have]
        merged = cached + added
        merged.sort(key=lambda x: x[0])
        if added:
            save_cached(symbol, merged)
        return merged, len(added)
    fresh = fetch_with_backoff(symbol, period1=0)
    if not fresh:
        return [], 0
    save_cached(symbol, fresh)
    return fresh, len(fresh)


def write_manifest(stats: dict) -> None:
    os.makedirs(HIST_DIR, exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)


def build_stats(only=None) -> dict:
    uni = _universe()
    if only:
        keep = set(only)
        uni = [(l, s) for (l, s) in uni if s in keep]
    out = {"updated": time.strftime("%Y-%m-%d"), "symbols": {}}
    for label, sym in uni:
        rows = load_cached(sym)
        if rows:
            out["symbols"][sym] = {
                "label": label, "first": rows[0][0], "last": rows[-1][0],
                "days": len(rows),
                "years": round((time.time() - time.mktime(
                    time.strptime(rows[0][0], "%Y-%m-%d"))) / 31557600, 1),
            }
        else:
            out["symbols"][sym] = {"label": label, "days": 0}
    total = sum(v.get("days", 0) for v in out["symbols"].values())
    out["total_daily_bars"] = total
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="상장 이래 전 일봉 소급·캐시 (수집 전용·stdlib)")
    ap.add_argument("--refresh", action="store_true", help="전체 재풀(상장~오늘)")
    ap.add_argument("--stats", action="store_true", help="캐시 현황만(풀 안 함)")
    ap.add_argument("--symbols", "--tickers", help="쉼표·공백구분 Yahoo 심볼(기본=유니버스 전체)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--pace", type=float, default=1.2, help="심볼 간 페이싱 초(레이트리밋)")
    args = ap.parse_args()

    only = [s.strip() for s in cli_common.split_tickers(args.symbols)] if args.symbols else None

    if args.stats:
        stats = build_stats(only)
        if not only:  # 전체 조회면 매니페스트를 디스크 진실로 갱신
            write_manifest(stats)
        print(json.dumps(stats, ensure_ascii=False, indent=1) if args.json
              else _fmt_stats(stats))
        return 0

    uni = _universe()
    if only:
        keep = set(only)
        uni = [(l, s) for (l, s) in uni if s in keep]

    print(f"[history_backfill] {len(uni)}종목 {'전체 재풀' if args.refresh else '증분 갱신'} 시작…")
    for i, (label, sym) in enumerate(uni):
        rows, added = update_symbol(sym, refresh=args.refresh)
        span = f"{rows[0][0]}~{rows[-1][0]}" if rows else "실패"
        print(f"  {label:<12}{sym:<12} {len(rows):>6}일 (+{added}) {span}")
        if i < len(uni) - 1:
            time.sleep(args.pace)  # 페이싱

    stats = build_stats(only)
    write_manifest(stats)
    print(f"\n총 {stats['total_daily_bars']:,}개 일봉 캐시 (data/history/). "
          f"매니페스트 갱신 완료.")
    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=1))
    return 0


def _fmt_stats(stats: dict) -> str:
    lines = [f"캐시 현황 (updated {stats.get('updated','?')}) — "
             f"총 {stats.get('total_daily_bars',0):,}개 일봉",
             f"{'심볼':<14}{'라벨':<14}{'기간':<26}{'일수':>7}{'년':>6}"]
    lines.append("-" * 68)
    for sym, v in stats["symbols"].items():
        if v.get("days"):
            span = f"{v['first']}~{v['last']}"
            lines.append(f"{sym:<14}{v['label']:<14}{span:<26}{v['days']:>7}{v.get('years',0):>6}")
        else:
            lines.append(f"{sym:<14}{v['label']:<14}{'(캐시 없음)':<26}{0:>7}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
