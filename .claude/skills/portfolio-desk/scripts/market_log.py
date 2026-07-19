#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
market_log.py — 시장 시세 시계열 축적·조회 (지수·환율·보유·워치).

정훈 지시(2026-07-19): "우리가 계속 시장 분석하는 것도 꾸준히 데이터로 남겨 저장,
시장에 데이터 올라와 있으면 참고." → 매일 라이브 시세를 append-only jsonl로 쌓아
**심볼별 과거 추세를 한 파일에서 조회**할 수 있게 한다.

snapshot.py와의 분업:
  - snapshot.py    = 포트폴리오 '손익 회계'(총자산·평가손익) 일별 JSON. 보유 전용.
  - market_log.py  = '시장 시세' 시계열(지수·환율·보유·워치) 조회용 jsonl. 추세·백테스트 입력.
  둘 다 커밋됨(연속성). 서로 대체 아님 — 보완.

저장: data/timeseries/quotes.jsonl  (한 줄 = 한 (거래일, 심볼))
  {"date","ts","group","label","symbol","price","change_pct","currency"}
  같은 (거래일, 심볼) 중복은 조회 시 '마지막 줄'만 채택(append-only, 안전).

사용:
  python3 market_log.py                       # 오늘 시세 수집→append (하루 1회, 이미 있으면 skip)
  python3 market_log.py --force               # 오늘 이미 기록돼도 다시 append
  python3 market_log.py --groups index,fx     # 수집 그룹 선택 (기본 index,fx,holdings,watchlist)
  python3 market_log.py --query 코스피 --days 30   # 심볼/라벨 과거 추세 조회 + 통계
  python3 market_log.py --query ^KS11 --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os

from market_data import GROUPS, fetch_quote  # 형제 모듈 재사용(시세 로직 단일화)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
TS_DIR = os.path.join(REPO, "data", "timeseries")
STORE = os.path.join(TS_DIR, "quotes.jsonl")

KST = dt.timezone(dt.timedelta(hours=9))

DEFAULT_GROUPS = ["index", "fx", "holdings", "watchlist"]


def trading_day() -> str:
    """스냅샷 귀속 거래일 = KST 현재시각 − 9h 의 날짜 (snapshot.py와 동일 규칙)."""
    return (dt.datetime.now(KST) - dt.timedelta(hours=9)).date().isoformat()


def _universe(groups: list[str]) -> list[tuple[str, str, str]]:
    """(group, label, symbol) 목록. holdings/watchlist/index/fx/oil 지원."""
    uni = []
    for g in groups:
        for label, symbol in GROUPS.get(g, []):
            uni.append((g, label, symbol))
    return uni


def _read_rows() -> list[dict]:
    if not os.path.exists(STORE):
        return []
    rows = []
    with open(STORE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return rows


def _dates_logged() -> set[str]:
    return {r.get("date") for r in _read_rows()}


def collect_and_log(groups: list[str], force: bool) -> int:
    day = trading_day()
    if not force and day in _dates_logged():
        print(f"이미 오늘({day}) 기록됨 — skip. 다시 쌓으려면 --force.")
        return 0
    uni = _universe(groups)
    ts = dt.datetime.now(KST).isoformat(timespec="seconds")
    os.makedirs(TS_DIR, exist_ok=True)
    n_ok, n_err = 0, 0
    with open(STORE, "a", encoding="utf-8") as f:
        for group, label, symbol in uni:
            q = fetch_quote(symbol)
            if q.get("error") or q.get("price") is None:
                n_err += 1
                continue
            rec = {"date": day, "ts": ts, "group": group, "label": label,
                   "symbol": symbol, "price": q["price"],
                   "change_pct": q.get("change_pct"), "currency": q.get("currency")}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_ok += 1
    print(f"logged {n_ok} quotes for {day} → {os.path.relpath(STORE, REPO)}"
          + (f"  ({n_err} 실패/무가격 skip)" if n_err else ""))
    return 0


def backfill_snapshots() -> int:
    """기존 data/snapshots/*.json(포트폴리오 손익 일별)에서 보유 종목가·환율을
    시계열로 소급 축적. 이미 store에 있는 (거래일,심볼)은 건너뜀. change_pct는
    스냅샷에 없으니 null. 지수·워치는 스냅샷에 없어 backfill 대상 아님(오늘부터 라이브)."""
    import glob
    snaps = sorted(glob.glob(os.path.join(REPO, "data", "snapshots", "*.json")))
    if not snaps:
        print("스냅샷 없음 — backfill 불가.")
        return 1
    # label → (symbol, currency) 맵 (보유 종목)
    lab2sym = {}
    for label, symbol in GROUPS.get("holdings", []):
        cur = "KRW" if symbol.endswith((".KS", ".KQ")) else "USD"
        lab2sym[label] = (symbol, cur)

    existing = {(r["date"], r["symbol"]) for r in _read_rows()}
    os.makedirs(TS_DIR, exist_ok=True)
    n = 0
    with open(STORE, "a", encoding="utf-8") as f:
        for sp in snaps:
            try:
                d = json.load(open(sp, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            day = d.get("date")
            if not day:
                continue
            # 환율
            fx = d.get("fx_usdkrw")
            if fx and (day, "KRW=X") not in existing:
                f.write(json.dumps({"date": day, "ts": day, "group": "fx",
                                    "label": "USD/KRW", "symbol": "KRW=X",
                                    "price": fx, "change_pct": None, "currency": "KRW"},
                                   ensure_ascii=False) + "\n")
                existing.add((day, "KRW=X")); n += 1
            # 보유 종목가
            for label, info in (d.get("positions") or {}).items():
                sym_cur = lab2sym.get(label)
                price = info.get("price") if isinstance(info, dict) else None
                if not sym_cur or price is None:
                    continue
                symbol, cur = sym_cur
                if (day, symbol) in existing:
                    continue
                f.write(json.dumps({"date": day, "ts": day, "group": "holdings",
                                    "label": label, "symbol": symbol, "price": price,
                                    "change_pct": None, "currency": cur},
                                   ensure_ascii=False) + "\n")
                existing.add((day, symbol)); n += 1
    print(f"backfilled {n} rows from {len(snaps)} snapshots → {os.path.relpath(STORE, REPO)}")
    return 0


def query(term: str, days: int, as_json: bool) -> int:
    rows = _read_rows()
    t = term.lower()
    hit = [r for r in rows if t in str(r.get("symbol", "")).lower()
           or t in str(r.get("label", "")).lower()]
    if not hit:
        print(f"'{term}' 시계열 없음. 먼저 축적: python3 market_log.py")
        return 1
    # (거래일)별 마지막 값만 채택
    by_date: dict[str, dict] = {}
    for r in hit:
        by_date[r["date"]] = r
    series = sorted(by_date.values(), key=lambda r: r["date"])[-days:]
    label = series[-1]["label"]
    symbol = series[-1]["symbol"]

    if as_json:
        print(json.dumps({"label": label, "symbol": symbol, "series": series},
                         ensure_ascii=False, indent=2))
        return 0

    prices = [r["price"] for r in series]
    latest, first = prices[-1], prices[0]
    chg = (latest - first) / first * 100 if first else 0.0
    cur = series[-1].get("currency") or ""
    print(f"### {label} ({symbol}) — 최근 {len(series)}거래일 [{cur}]")
    print(f"| {'거래일':<12} | {'종가':>12} | {'당일%':>7} |")
    print(f"|{'-'*14}|{'-'*14}|{'-'*9}|")
    for r in series:
        p = r["price"]
        pct = r.get("change_pct")
        pct_s = f"{pct:+.2f}" if isinstance(pct, (int, float)) else "-"
        p_s = f"{p:,.0f}" if cur == "KRW" else f"{p:,.2f}"
        print(f"| {r['date']:<12} | {p_s:>12} | {pct_s:>7} |")
    lo, hi = min(prices), max(prices)
    fmt = (lambda v: f"{v:,.0f}") if cur == "KRW" else (lambda v: f"{v:,.2f}")
    print(f"\n구간: 최저 {fmt(lo)} · 최고 {fmt(hi)} · 최신 {fmt(latest)} "
          f"· 기간변화 {chg:+.2f}%  (n={len(series)})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="시장 시세 시계열 축적·조회")
    ap.add_argument("--groups", default=",".join(DEFAULT_GROUPS),
                    help="수집 그룹 쉼표구분 (index,fx,holdings,watchlist,oil)")
    ap.add_argument("--force", action="store_true", help="오늘 이미 기록돼도 재수집")
    ap.add_argument("--backfill-snapshots", action="store_true",
                    help="기존 data/snapshots에서 보유가·환율 시계열 소급 축적")
    ap.add_argument("--query", help="심볼/라벨 과거 추세 조회")
    ap.add_argument("--days", type=int, default=30, help="조회 기간(거래일 수, 기본 30)")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    args = ap.parse_args()

    if args.query:
        return query(args.query, args.days, args.json)
    if args.backfill_snapshots:
        return backfill_snapshots()
    groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    return collect_and_log(groups, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
