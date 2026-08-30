#!/usr/bin/env python3
"""ohlcv_backfill.py — 상장 이래 **OHLCV** 일봉 영구 캐시 (stdlib only·수집 전용)

왜 있나 [2026-08-30 정훈 지시 "주가 흐름도 다 저장"]
──────────────────────────────────────────────────────
기존 `data/history/<sym>.csv`는 헤더가 **`date,close` 두 컬럼뿐**이다. 그래서
  · `signal_score.py`가 스스로 *"종가 기반 — 거래량·고저 필요한 지표는 제외"* 라고 적어둔 채
    RSI/MA/MACD 계열만 채점하고 **거래량 확인·갭·장중 레인지 지표를 통째로 못 쓴다**
    (오닐 CANSLIM의 **S(수급)** 은 거래량 동반이 핵심인데 그 입력이 없다).
  · `vol_gauge.py`는 OHLC가 필요해 **매번 Yahoo를 재조회**한다(캐시가 못 받쳐준다).

⚠️ **기존 `data/history/`는 건드리지 않는다.** 여러 도구가 `(date, close)` 2튜플 형태를
   전제로 읽고 있어 헤더를 바꾸면 조용히 깨진다(8/12 *"쓰는 쪽과 읽는 쪽이 갈리면 데이터는
   조용히 사라진다"*). 그래서 **별도 축** `data/history_ohlcv/`에 쌓고, 소비자가 준비되면
   그쪽이 새 축을 읽게 한다.

수집: Yahoo chart API `interval=1d&period1=0` (range=max는 장기서 월봉으로 다운샘플되므로 금지 —
      history_backfill의 8/x 교훈 그대로).
저장: `data/history_ohlcv/<safe_symbol>.csv`  헤더 `date,open,high,low,close,volume`
⚠️ 최근 5거래일은 값이 바뀔 수 있어 **매번 덮어쓴다**(8/13 장중값 고착 사고 대응 규칙 승계).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "history_ohlcv")
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _safe(sym: str) -> str:
    return sym.replace("^", "_").replace("/", "_")


def universe() -> list[str]:
    """보유 + 워치 + 벤치마크. app/data.js와 stocks.json이 정본."""
    syms = []
    try:
        raw = open(os.path.join(ROOT, "app", "data.js"), encoding="utf-8").read()
        d = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
        syms += [h["ticker"] for h in (d.get("holdings") or []) if h.get("ticker")]
    except Exception:
        pass
    try:
        st = json.load(open(os.path.join(ROOT, "data", "app", "stocks.json"), encoding="utf-8"))
        syms += list((st.get("watchlist") or {}).keys())
        syms += list((st.get("stocks") or {}).keys())
    except Exception:
        pass
    syms += ["^KS11", "^KQ11", "^GSPC", "^IXIC", "KRW=X"]
    seen, out = set(), []
    for s in syms:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def fetch(symbol: str, timeout: float = 40.0):
    now = int(time.time())
    url = YAHOO.format(symbol=urllib.parse.quote(symbol)) + \
        f"?interval=1d&period1=0&period2={now}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        q = res["indicators"]["quote"][0]
        rows = []
        for i, t in enumerate(ts):
            c = q["close"][i]
            if c is None:
                continue
            def g(k):
                v = q.get(k, [None] * len(ts))[i]
                return "" if v is None else round(float(v), 4)
            rows.append([time.strftime("%Y-%m-%d", time.gmtime(t)),
                         g("open"), g("high"), g("low"), round(float(c), 4),
                         int(q["volume"][i]) if q.get("volume", [None])[i] is not None else ""])
        return rows
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError,
            IndexError, TypeError, ValueError):
        return None


def save(symbol: str, rows) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, _safe(symbol) + ".csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        w.writerows(rows)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="상장 이래 OHLCV 일봉 캐시 (수집 전용)")
    ap.add_argument("--symbols", help="쉼표구분 (기본=보유+워치+벤치마크)")
    ap.add_argument("--pace", type=float, default=1.5, help="심볼 간 페이싱 초")
    ap.add_argument("--stats", action="store_true", help="캐시 현황만 출력")
    a = ap.parse_args()

    syms = [s.strip() for s in a.symbols.split(",")] if a.symbols else universe()

    if a.stats:
        print(f"OHLCV 캐시 — {OUT_DIR}")
        tot = 0
        for s in syms:
            p = os.path.join(OUT_DIR, _safe(s) + ".csv")
            if not os.path.exists(p):
                print(f"  {s:<14} 없음")
                continue
            rows = list(csv.reader(open(p)))[1:]
            tot += len(rows)
            print(f"  {s:<14} {rows[0][0]} ~ {rows[-1][0]}  {len(rows):>6}행")
        print(f"총 {tot:,}행")
        return 0

    print(f"■ OHLCV 수집 {len(syms)}종목 → {OUT_DIR}")
    ok = fail = 0
    for i, s in enumerate(syms, 1):
        rows = fetch(s)
        if not rows:
            print(f"  [{i}/{len(syms)}] {s:<14} ❌ 실패")
            fail += 1
        else:
            save(s, rows)
            print(f"  [{i}/{len(syms)}] {s:<14} {rows[0][0]} ~ {rows[-1][0]}  {len(rows):>6}행")
            ok += 1
        sys.stdout.flush()
        if i < len(syms):
            time.sleep(a.pace + random.uniform(0, 0.8))
    print(f"\n완료 — 성공 {ok} · 실패 {fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
