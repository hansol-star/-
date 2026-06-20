#!/usr/bin/env python3
"""
fundamentals.py — 미국주 펀더멘털 하드넘버 수집기 (FMP, 0~100 스코어 근거)

별점·0~100 스코어를 "감"이 아니라 검증된 방법론(오닐 CANSLIM·미너비니)의
실제 숫자(EPS 성장·매출 성장·마진·FCF·PE) 위에서 채점하기 위한 펀더멘털 소스.
표준 라이브러리(urllib)만 사용 — pip 불필요, 로컬 이전 시에도 그대로 작동.

⚠️ FMP 무료 플랜 = **미국 상장사 전용**(250회/일·5년). 국내(.KS/.KQ)는 무료 미지원
   → 국내 종목 펀더멘털은 기존대로 WebSearch(증권사 리포트)로 보강. 이 스크립트는 미국주만.

키: 환경변수 FMP_API_KEY (조회 전용·읽기 키). 키 없으면 안내 후 종료(추측 금지).
   세션마다 정훈이 줄 수도 있음: `FMP_API_KEY=xxx python3 fundamentals.py --tickers NVDA`

엔드포인트: FMP stable API (신규 키 기본). 403/429는 키·플랜·한도 문제로 명시.

사용:
  FMP_API_KEY=xxx python3 fundamentals.py --tickers NVDA,MU,AAPL   # 표
  FMP_API_KEY=xxx python3 fundamentals.py --tickers NVDA --json     # 파이프라인용
  python3 fundamentals.py --selftest                                # 키·연결 점검 1콜
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://financialmodelingprep.com/stable"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# 미국주만 (국내 .KS/.KQ 는 무료 플랜 미지원 → 건너뜀)
US_HOLDINGS = ["NVDA", "MU", "AAPL", "VOO", "MSFT", "ANET", "TSLA", "AVGO", "GOOGL", "META", "ORCL"]


def _key() -> str | None:
    k = os.environ.get("FMP_API_KEY", "").strip()
    return k or None


def _get(path: str, params: dict) -> object:
    """FMP stable 엔드포인트 GET. 실패 시 {'_error': ...} 반환."""
    key = _key()
    params = {**params, "apikey": key}
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        msg = {401: "키 무효", 403: "키 무효 또는 무료 플랜 미포함 엔드포인트",
               429: "일일 250회 한도 초과", 402: "유료 플랜 전용"}.get(e.code, f"HTTP {e.code}")
        return {"_error": f"{msg} ({e.code})"}
    except Exception as e:
        return {"_error": str(e)}


def _is_us(t: str) -> bool:
    return not (t.endswith(".KS") or t.endswith(".KQ"))


def _pct(new, old):
    try:
        if old in (None, 0):
            return None
        return round((float(new) - float(old)) / abs(float(old)) * 100, 1)
    except Exception:
        return None


def fetch(ticker: str) -> dict:
    """한 종목의 핵심 펀더멘털을 모아 채점용 dict로 반환."""
    out: dict = {"ticker": ticker}
    if not _is_us(ticker):
        out["_error"] = "국내주 — FMP 무료 미지원(WebSearch로 보강)"
        return out

    quote = _get("quote", {"symbol": ticker})
    if isinstance(quote, dict) and quote.get("_error"):
        out["_error"] = quote["_error"]
        return out
    q = quote[0] if isinstance(quote, list) and quote else {}
    out["price"] = q.get("price")
    out["marketCap"] = q.get("marketCap")
    # PE는 stable /quote 응답에 없음 → 아래 ratios-ttm 에서 가져온다.

    # 연간 손익 4년 → 매출·EPS YoY 추세 (CANSLIM의 A)
    inc = _get("income-statement", {"symbol": ticker, "period": "annual", "limit": 4})
    if isinstance(inc, list) and len(inc) >= 2:
        out["revenueGrowthYoY"] = _pct(inc[0].get("revenue"), inc[1].get("revenue"))
        out["epsGrowthYoY"] = _pct(inc[0].get("eps"), inc[1].get("eps"))

    # 분기 손익 5개 → 최근 분기 EPS YoY (CANSLIM의 C)
    qinc = _get("income-statement", {"symbol": ticker, "period": "quarter", "limit": 5})
    if isinstance(qinc, list) and len(qinc) >= 5:
        out["epsGrowthQoQ_YoY"] = _pct(qinc[0].get("eps"), qinc[4].get("eps"))

    # TTM 비율: 총마진·순마진·PE·FCF/주 (모두 ratios-ttm). 마진은 0~1 소수.
    ratios = _get("ratios-ttm", {"symbol": ticker})
    if isinstance(ratios, list) and ratios:
        r0 = ratios[0]
        out["grossMarginTTM"] = r0.get("grossProfitMarginTTM")
        out["netMarginTTM"] = r0.get("netProfitMarginTTM")
        out["pe"] = r0.get("priceToEarningsRatioTTM")
        out["fcfPerShareTTM"] = r0.get("freeCashFlowPerShareTTM")

    # ROE는 ratios-ttm 엔 없고 key-metrics-ttm 에 있음. 0~1 소수.
    km = _get("key-metrics-ttm", {"symbol": ticker})
    if isinstance(km, list) and km:
        out["roeTTM"] = km[0].get("returnOnEquityTTM")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="쉼표구분. 기본=미국 보유 11")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="키·연결 점검(1콜)")
    args = ap.parse_args()

    if not _key():
        print("⚠️  FMP_API_KEY 환경변수가 없습니다.\n"
              "    무료 키 발급: https://site.financialmodelingprep.com/developer/docs\n"
              "    사용:  FMP_API_KEY=발급키 python3 fundamentals.py --tickers NVDA",
              file=sys.stderr)
        sys.exit(2)

    if args.selftest:
        r = _get("quote", {"symbol": "AAPL"})
        if isinstance(r, dict) and r.get("_error"):
            print(f"❌ 연결 실패: {r['_error']}", file=sys.stderr); sys.exit(1)
        print("✅ FMP 연결·키 정상 (AAPL quote 수신).")
        return

    tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else US_HOLDINGS
    rows = [fetch(t) for t in tickers]

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2)); return

    hdr = ["티커", "현재가", "PE", "매출YoY%", "EPS YoY%", "분기EPS YoY%", "총마진%", "순마진%", "ROE%", "FCF/주"]
    print(" | ".join(hdr))
    print("-" * 96)
    for r in rows:
        if r.get("_error"):
            print(f"{r['ticker']:<6} | {r['_error']}"); continue

        def num(k, nd=1):  # 일반 수치 (성장률·PE·FCF)
            v = r.get(k)
            return "-" if v is None else f"{float(v):.{nd}f}"

        def pct(k):  # 0~1 소수 비율 → %
            v = r.get(k)
            return "-" if v is None else f"{float(v) * 100:.1f}"

        print(f"{r['ticker']:<6} | {num('price', 2)} | {num('pe')} | {num('revenueGrowthYoY')} | "
              f"{num('epsGrowthYoY')} | {num('epsGrowthQoQ_YoY')} | {pct('grossMarginTTM')} | "
              f"{pct('netMarginTTM')} | {pct('roeTTM')} | {num('fcfPerShareTTM', 2)}")
    print("\n※ 국내주는 FMP 무료 미지원 → WebSearch(증권사 리포트)로 보강. 수치는 0~100 스코어 채점 근거로만.")


if __name__ == "__main__":
    main()
