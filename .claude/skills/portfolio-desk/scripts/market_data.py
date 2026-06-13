#!/usr/bin/env python3
"""
market_data.py — 무키(無key) 시세·환율 수집기 (Yahoo Finance)

토스 Open API 키 없이도 국내·미국 주식 시세, 주요 지수, 환율을 가져온다.
표준 라이브러리(urllib)만 사용 — pip 설치 불필요, 로컬 이전 시에도 그대로 작동.

용도:
  - 보유 16종목 + 워치리스트 현재가/등락률
  - 코스피·코스닥·S&P500·나스닥·다우·필반(SOX) 지수
  - USD/KRW 환율
  - (선택) 원가 대비 평가손익 — master.md 기준값을 넘기면 계산

  ※ 이 스크립트는 "시세·환율" 전용이다. 사용자의 실제 보유수량·현금 잔액은
    토스 실데이터(toss_snapshot.py) 또는 계좌 스크린샷이 source of truth.
    원가 고정 테이블의 정본은 docs/master.md.

사용법:
  python3 market_data.py                      # 기본 유니버스 전체 (표 출력)
  python3 market_data.py --json               # JSON 출력 (서브에이전트/파이프라인용)
  python3 market_data.py --tickers AAPL,NVDA  # 특정 티커만
  python3 market_data.py --group holdings      # holdings|watchlist|index|fx|all
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# ── 유니버스 정의 (정훈 포트폴리오 기준; 원가의 정본은 docs/master.md) ──────────
# label: 화면 표기명, symbol: Yahoo 티커
HOLDINGS_KR = [
    ("삼성전자", "005930.KS"),
    ("LG전자", "066570.KS"),
    ("두산로보틱스", "454910.KS"),
    ("현대차", "005380.KS"),
    ("NAVER", "035420.KS"),
]
HOLDINGS_US = [
    ("NVDA", "NVDA"), ("META", "META"), ("VOO", "VOO"), ("MSFT", "MSFT"),
    ("AAPL", "AAPL"), ("GOOGL", "GOOGL"), ("TSLA", "TSLA"), ("ORCL", "ORCL"),
    ("ANET", "ANET"), ("MU", "MU"), ("AVGO", "AVGO"),
]
WATCHLIST = [  # 폴백 (portfolio.json 없을 때만). 정본은 portfolio.json.
    ("원익IPS", "240810.KQ"), ("테스", "095610.KQ"), ("SK이노베이션", "096770.KS"),
    ("두산에너빌리티", "034020.KS"),
    ("GEV", "GEV"), ("STM", "STM"), ("TMUS", "TMUS"), ("SPCX", "SPCX"),
]
INDEX = [
    ("코스피", "^KS11"), ("코스닥", "^KQ11"), ("S&P500", "^GSPC"),
    ("나스닥", "^IXIC"), ("다우", "^DJI"), ("필라델피아반도체", "^SOX"),
]
FX = [("USD/KRW", "KRW=X")]


def _load_universe():
    """portfolio.json이 있으면 거기서 유니버스를 읽어 덮어쓴다 (master.md 미러, 단일 정본).
    없으면 위 임베드 기본값 사용 — 포터블."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "portfolio.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        pairs = lambda items: [(d["label"], d["ticker"]) for d in items]
        return (pairs(cfg["holdings"]["kr"]), pairs(cfg["holdings"]["us"]),
                pairs(cfg["watchlist"]), pairs(cfg["indices"]), pairs(cfg["fx"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None


_u = _load_universe()
if _u:
    HOLDINGS_KR, HOLDINGS_US, WATCHLIST, INDEX, FX = _u

GROUPS = {
    "holdings": HOLDINGS_KR + HOLDINGS_US,
    "watchlist": WATCHLIST,
    "index": INDEX,
    "fx": FX,
}
GROUPS["all"] = GROUPS["holdings"] + GROUPS["watchlist"] + GROUPS["index"] + GROUPS["fx"]


def fetch_quote(symbol: str, timeout: float = 10.0) -> dict | None:
    """Yahoo chart 엔드포인트에서 단일 심볼 시세를 가져온다. 실패 시 None."""
    url = YAHOO_CHART.format(symbol=urllib.request.quote(symbol))
    url += "?interval=1d&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
        return {"symbol": symbol, "error": str(e)}
    try:
        meta = data["chart"]["result"][0]["meta"]
    except (KeyError, IndexError, TypeError):
        return {"symbol": symbol, "error": "no data (delisted/invalid ticker?)"}
    price = meta.get("regularMarketPrice")
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")
    chg_pct = None
    if price is not None and prev:
        chg_pct = round((price - prev) / prev * 100, 2)
    return {
        "symbol": symbol,
        "price": price,
        "prev_close": prev,
        "change_pct": chg_pct,
        "currency": meta.get("currency"),
        "market_state": meta.get("marketState"),
    }


def collect(universe: list[tuple[str, str]]) -> list[dict]:
    out = []
    for label, symbol in universe:
        q = fetch_quote(symbol)
        q["label"] = label
        out.append(q)
    return out


def fmt_price(p, cur) -> str:
    if p is None:
        return "—"
    if cur == "KRW":
        return f"{p:,.0f}"
    return f"{p:,.2f}"


def fmt_pct(p) -> str:
    if p is None:
        return "—"
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.2f}%"


def print_table(rows: list[dict]) -> None:
    print(f"| {'종목':<14} | {'현재가':>12} | {'등락률':>8} | {'통화':<4} | 상태 |")
    print(f"|{'-'*16}|{'-'*14}|{'-'*10}|{'-'*6}|------|")
    for r in rows:
        if r.get("error"):
            print(f"| {r['label']:<14} | {'ERROR':>12} | {'—':>8} | {'—':<4} | {r['error'][:20]} |")
            continue
        print(
            f"| {r['label']:<14} | {fmt_price(r['price'], r['currency']):>12} "
            f"| {fmt_pct(r['change_pct']):>8} | {str(r['currency'] or '—'):<4} "
            f"| {r.get('market_state','—')} |"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="무키 시세·환율 수집기 (Yahoo Finance)")
    ap.add_argument("--group", default="all", choices=list(GROUPS.keys()),
                    help="조회 그룹 (기본 all)")
    ap.add_argument("--tickers", help="쉼표구분 티커 직접 지정 (group 무시)")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    args = ap.parse_args()

    if args.tickers:
        universe = [(t, t) for t in args.tickers.split(",") if t.strip()]
    else:
        universe = GROUPS[args.group]

    rows = collect(universe)

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    # 그룹별 섹션 출력 (group=all일 때만 구분)
    if not args.tickers and args.group == "all":
        sections = [
            ("📈 보유 — 국내", HOLDINGS_KR),
            ("📈 보유 — 미국", HOLDINGS_US),
            ("👀 워치리스트", WATCHLIST),
            ("📊 지수", INDEX),
            ("💱 환율", FX),
        ]
        by_symbol = {r["symbol"]: r for r in rows}
        for title, uni in sections:
            print(f"\n### {title}")
            print_table([by_symbol[s] for _, s in uni])
    else:
        print_table(rows)

    errs = [r for r in rows if r.get("error")]
    if errs:
        print(f"\n⚠️  {len(errs)}개 실패: {', '.join(r['label'] for r in errs)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
