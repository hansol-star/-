#!/usr/bin/env python3
"""
consensus.py — 애널리스트 목표주가·투자의견 (Yahoo 무키, crumb 인증).

master.md §5 ③ 룰 자동화: 핵심종목·후보의 목표주가/의견을 모으고
현재가 대비 ±30% 괴리 시 익절/추가매수 플래그를 단다.

Yahoo quoteSummary는 crumb(쿠키→토큰) 인증이 필요 → http.cookiejar로 처리.
국내(.KS) 종목은 Yahoo 애널리스트 커버리지가 없을 수 있음(그땐 '데이터 없음').
정확한 한국 증권사 컨센서스는 보고서 단계에서 WebSearch로 교차확인.

사용:
  python3 consensus.py             # 보유 US + 워치 US 목표주가 표
  python3 consensus.py --tickers NVDA,META
  python3 consensus.py --json
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "..", "portfolio.json")
GAP_FLAG = 30.0  # ±30% 괴리 플래그


def _opener():
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", UA)]
    return op


def get_crumb(op) -> str | None:
    try:
        op.open("https://fc.yahoo.com", timeout=10).read()
    except Exception:
        pass  # 쿠키만 받으면 됨 (404여도 set-cookie는 옴)
    try:
        with op.open("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=10) as r:
            crumb = r.read().decode().strip()
        return crumb or None
    except Exception:
        return None


def fetch_consensus(op, crumb, symbol) -> dict:
    url = (f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
           f"?modules=financialData&crumb={urllib.request.quote(crumb)}")
    try:
        with op.open(url, timeout=12) as r:
            data = json.load(r)
        fd = data["quoteSummary"]["result"][0]["financialData"]
    except Exception as e:
        return {"symbol": symbol, "error": str(e)[:60]}

    def raw(k):
        v = fd.get(k)
        return v.get("raw") if isinstance(v, dict) else v

    price = raw("currentPrice")
    target = raw("targetMeanPrice")
    gap = round((target - price) / price * 100, 1) if (price and target) else None
    flag = ""
    if gap is not None and abs(gap) >= GAP_FLAG:
        flag = "🟢 추가매수 검토(상방 큼)" if gap > 0 else "🔴 익절 검토(목표 하회)"
    return {
        "symbol": symbol, "price": price, "target_mean": target,
        "target_high": raw("targetHighPrice"), "target_low": raw("targetLowPrice"),
        "rec_key": fd.get("recommendationKey"), "n_analysts": raw("numberOfAnalystOpinions"),
        "gap_pct": gap, "flag": flag,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="애널리스트 목표주가 (Yahoo crumb)")
    ap.add_argument("--tickers", help="쉼표구분 티커 (기본: portfolio.json US 보유+워치)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.tickers:
        syms = [t.strip() for t in args.tickers.split(",") if t.strip()]
    else:
        with open(CFG, encoding="utf-8") as f:
            cfg = json.load(f)
        syms = [h["ticker"] for h in cfg["holdings"]["us"]]
        syms += [w["ticker"] for w in cfg["watchlist"] if not w["ticker"].endswith(".KS")]

    op = _opener()
    crumb = get_crumb(op)
    if not crumb:
        print("crumb 발급 실패 — Yahoo 인증 거부. WebSearch로 컨센서스 수집 권장.")
        return 1

    rows = [fetch_consensus(op, crumb, s) for s in syms]

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print(f"| {'종목':<7} | {'현재가':>9} | {'목표(평균)':>10} | {'괴리':>7} | {'의견':<10} | {'#':>3} | 플래그 |")
    print(f"|{'-'*9}|{'-'*11}|{'-'*12}|{'-'*9}|{'-'*12}|{'-'*5}|--------|")
    for r in rows:
        if r.get("error"):
            print(f"| {r['symbol']:<7} | {'데이터 없음':>9} | {'—':>10} | {'—':>7} | {'—':<10} | {'—':>3} | {r['error'][:18]} |")
            continue
        gap = f"{r['gap_pct']:+.1f}%" if r["gap_pct"] is not None else "—"
        tm = f"{r['target_mean']:,.2f}" if r["target_mean"] else "—"
        pr = f"{r['price']:,.2f}" if r["price"] else "—"
        print(f"| {r['symbol']:<7} | {pr:>9} | {tm:>10} | {gap:>7} "
              f"| {str(r['rec_key'] or '—'):<10} | {str(r['n_analysts'] or '—'):>3} | {r['flag']} |")
    print(f"\n※ ±{GAP_FLAG:.0f}% 이상 괴리 시 플래그. 국내 종목·미커버리지는 WebSearch 교차확인.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
