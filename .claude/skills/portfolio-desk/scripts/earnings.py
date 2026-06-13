#!/usr/bin/env python3
"""
earnings.py — 보유·워치 종목의 다가오는 실적 발표일 (Yahoo calendarEvents, crumb 무키).

이벤트 캘린더(보고서 §4 '지켜볼 것')를 보강한다. 실적일이 폰 가용시간/장 시간과
겹치는지, 다가오는 2~N주 안에 있는지 플래그.

사용:
  python3 earnings.py            # portfolio.json 보유+워치 전체
  python3 earnings.py --tickers NVDA,AAPL
  python3 earnings.py --json
  python3 earnings.py --within 21    # N일 이내만 (기본 60)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os

from consensus import _opener, get_crumb  # crumb 플로우 재사용

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "..", "portfolio.json")


def fetch_earnings(op, crumb, symbol) -> dict:
    import urllib.request
    url = (f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
           f"?modules=calendarEvents&crumb={urllib.request.quote(crumb)}")
    try:
        with op.open(url, timeout=12) as r:
            data = json.load(r)
        ev = data["quoteSummary"]["result"][0]["calendarEvents"]["earnings"]
        dates = ev.get("earningsDate") or []
        out = [d.get("fmt") for d in dates if isinstance(d, dict) and d.get("fmt")]
        return {"symbol": symbol, "earnings_dates": out}
    except Exception as e:
        return {"symbol": symbol, "earnings_dates": [], "error": str(e)[:50]}


def main() -> int:
    ap = argparse.ArgumentParser(description="실적 발표일 (Yahoo crumb)")
    ap.add_argument("--tickers")
    ap.add_argument("--within", type=int, default=60, help="N일 이내만 (기본 60)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    with open(CFG, encoding="utf-8") as f:
        cfg = json.load(f)
    label_of = {}
    if args.tickers:
        syms = [t.strip() for t in args.tickers.split(",") if t.strip()]
        for s in syms:
            label_of[s] = s
    else:
        syms = []
        for h in cfg["holdings"]["kr"] + cfg["holdings"]["us"] + cfg["watchlist"]:
            syms.append(h["ticker"])
            label_of[h["ticker"]] = h["label"]

    op = _opener()
    crumb = get_crumb(op)
    if not crumb:
        print("crumb 발급 실패 — WebSearch로 '[종목] 실적 발표일' 확인 권장.")
        return 1

    today = dt.date.today()
    rows = []
    for s in syms:
        r = fetch_earnings(op, crumb, s)
        r["label"] = label_of.get(s, s)
        # 가장 가까운 미래 날짜
        nearest, days = None, None
        for d in r.get("earnings_dates", []):
            try:
                dd = dt.date.fromisoformat(d)
            except ValueError:
                continue
            delta = (dd - today).days
            if delta >= 0 and (days is None or delta < days):
                nearest, days = d, delta
        r["nearest"], r["days_until"] = nearest, days
        rows.append(r)

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    upcoming = sorted([r for r in rows if r["days_until"] is not None and r["days_until"] <= args.within],
                      key=lambda r: r["days_until"])
    print(f"## 다가오는 실적 발표 ({args.within}일 이내)\n")
    if not upcoming:
        print("- 해당 기간 내 예정된 실적 발표 없음 (또는 미커버리지)")
    for r in upcoming:
        flag = " ⚡임박" if r["days_until"] <= 7 else ""
        print(f"- **{r['label']}** ({r['symbol']}): {r['nearest']} (D-{r['days_until']}){flag}")
    miss = [r for r in rows if not r.get("earnings_dates")]
    if miss:
        print(f"\n_미확인({len(miss)}): {', '.join(r['label'] for r in miss)} → WebSearch 보강_")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
