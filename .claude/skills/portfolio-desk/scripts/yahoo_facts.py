#!/usr/bin/env python3
"""yahoo_facts.py — 재무제표 3표 수집기 (Yahoo fundamentals-timeseries, 무키·stdlib)

정훈 지시(2026-07-29). **국내 5종목의 실질 1차 소스** — DART 키 없이도 국내 보유 전 종목의
손익·재무상태·현금흐름 3표가 다 나온다. [7/29 실측] 삼성전자·LG전자·두산로보틱스·현대차·NAVER
**23/23 계정 만점**(연간 4기 + 분기 5기). 미국 FMP 402 종목(MU·ANET·AVGO·ORCL)도 커버.

역할 2가지:
  ① KR 재무제표 백본 — 국내는 EDGAR가 없고 DART는 키가 필요하다. 이게 무키 기본 경로.
  ② US 교차검증 대조군 — EDGAR(1차 출처) 파서가 맞게 읽었는지 대조.
     [7/29 실측] MU 자산 $82,798,000,000 · ANET 매출 $9,005,700,000 = EDGAR와 자릿수까지 일치.
     CLAUDE.md "단일 출처 의심 수치는 항상 교차검증" 룰을 재무제표에도 적용.

⚠️ 파싱 함정 3가지 (전부 실측 확인):
  ① crumb이 레이트리밋되면 토큰 자리에 **"Too Many Requests" 문자열이 그대로 온다** →
     유효성 검사 없이 쓰면 조용히 전 종목 실패. 검사 + 백오프 필수.
  ② result 오브젝트 키에 `meta`뿐 아니라 **`timestamp`도 섞여 있다** — 둘 다 걸러야 계정이 잡힌다.
  ③ 일부 기간 원소가 `null`이다 → isinstance(x, dict) 가드.

⚠️ 성격: Yahoo는 **2차 가공 데이터**(비공식 API·스키마 변동 리스크). 1차 출처는 미국=EDGAR,
   국내=DART. 수치가 갈리면 1차를 채택하고 `source_conflict` 플래그를 단다.
   NAVER는 `GrossProfit == Revenue`로 오는데 매출원가 미분류 아티팩트다(파서가 감지·무효화).

사용:
  python3 yahoo_facts.py                       # 국내 보유 5 + 미국 402 4종목
  python3 yahoo_facts.py --tickers 005930.KS
  python3 yahoo_facts.py --json / --save
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CACHE_DIR = os.path.join(ROOT, "data", "financials")

from consensus import _opener, get_crumb  # crumb 쿠키 플로우 재사용(레포 기존 자산)
import cli_common

BASE = "https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/"
# [7/29 실측] period2를 9999999999로 크게 잡으면 **빈 응답**이 온다(에러도 안 뜸) → 2e9 상한.
# 또한 period1을 아무리 과거로 내려도 Yahoo가 주는 건 **최대 4~5기**다. 장기 시계열은
# 미국=EDGAR(상장 이래 전부)·국내=DART가 답이고, Yahoo는 '최근 몇 기 + 무키 커버리지' 역할.
P1, P2 = 1041379200, 2000000000

# 국내 보유 5 (Yahoo 티커) — 원익IPS·테스는 .KQ (6/14 교정 이력 준수)
KR_HOLDINGS = ["005930.KS", "066570.KS", "454910.KS", "005380.KS", "035420.KS"]
KR_NAMES = {"005930.KS": "삼성전자", "066570.KS": "LG전자", "454910.KS": "두산로보틱스",
            "005380.KS": "현대차", "035420.KS": "NAVER"}
# FMP가 402로 막는 미국 종목 = EDGAR 교차검증 우선 대상
US_402 = ["MU", "ANET", "AVGO", "ORCL"]

# 우리 단일 스키마 ← Yahoo 계정명
FIELDS = {
    "revenue": "TotalRevenue",
    "gross_profit": "GrossProfit",
    "operating_income": "OperatingIncome",
    "net_income": "NetIncome",
    "eps_diluted": "DilutedEPS",
    "shares_diluted": "DilutedAverageShares",
    "assets": "TotalAssets",
    "liabilities": "TotalLiabilitiesNetMinorityInterest",
    "equity": "StockholdersEquity",
    "cash": "CashAndCashEquivalents",
    "inventory": "Inventory",
    "receivables": "AccountsReceivable",
    "assets_current": "CurrentAssets",
    "liabilities_current": "CurrentLiabilities",
    "total_debt": "TotalDebt",
    "cfo": "OperatingCashFlow",
    "capex": "CapitalExpenditure",
    "fcf": "FreeCashFlow",
}


def _crumb(op, tries: int = 4) -> str | None:
    """함정 ① — 레이트리밋 시 crumb 자리에 에러 문구가 온다. 검증 후 백오프 재시도."""
    for i in range(tries):
        c = get_crumb(op)
        if c and len(c) <= 24 and " " not in c:
            return c
        time.sleep(3 * (i + 1))
    return None


def fetch(ticker: str, op=None, crumb: str | None = None) -> dict:
    op = op or _opener()
    crumb = crumb or _crumb(op)
    if not crumb:
        return {"ticker": ticker, "_error": "Yahoo crumb 획득 실패(레이트리밋) — 재시도 필요"}
    types = [p + y[0].upper() + y[1:] for y in FIELDS.values() for p in ("annual", "quarterly")]
    url = (f"{BASE}{ticker}?symbol={ticker}&type={','.join(types)}"
           f"&period1={P1}&period2={P2}&crumb={urllib.parse.quote(crumb)}")
    try:
        with op.open(url, timeout=25) as r:
            data = json.load(r)
    except Exception as e:
        return {"ticker": ticker, "_error": str(e)[:120]}

    series: dict[str, dict[str, float]] = {}
    for s in data.get("timeseries", {}).get("result", []):
        for k in s:
            if k in ("meta", "timestamp"):      # 함정 ②
                continue
            vals = {}
            for x in s[k]:
                if not isinstance(x, dict):    # 함정 ③
                    continue
                rv = x.get("reportedValue")
                v = rv.get("raw") if isinstance(rv, dict) else rv
                if x.get("asOfDate") and v is not None:
                    vals[x["asOfDate"]] = v
            if vals:
                series[k] = vals

    def build(prefix: str) -> list[dict]:
        anchor = series.get(prefix + "TotalRevenue", {})
        rows = []
        for end in sorted(anchor, reverse=True):
            row = {"end": end, "period": "annual" if prefix == "annual" else "quarterly"}
            for ours, y in FIELDS.items():
                row[ours] = series.get(prefix + y[0].upper() + y[1:], {}).get(end)
            derived = []
            # ⚠️ Yahoo(2차 가공) 실측 이상치 — 하위 항목이 매출과 **정확히 일치**하는 케이스.
            #   · gross_profit==revenue : NAVER 등 서비스업 매출원가 미분류(구조적)
            #   · operating_income==revenue : 순수 매핑 오류(NAVER 2025-06-30에서 실제 발생.
            #     영업이익률 19%인 회사가 100%로 찍힘 → 그대로 쓰면 마진 추세 판정이 붕괴)
            # 어느 쪽이든 추정으로 메우지 않고 None + 플래그(CLAUDE.md "추측 금지·미확인 명시").
            for fld in ("gross_profit", "operating_income"):
                v = row.get(fld)
                if v is not None and row.get("revenue") and abs(v - row["revenue"]) < 1:
                    row[fld] = None
                    derived.append(f"{fld} 무효화(매출과 동일 — Yahoo 매핑 이상)")
            # Yahoo capex는 유출을 음수로 신고 → EDGAR(양수) 부호규약에 맞춰 뒤집는다
            if row.get("capex") is not None and row["capex"] < 0:
                row["capex"] = -row["capex"]
            if row.get("fcf") is None and row.get("cfo") is not None \
                    and row.get("capex") is not None:
                row["fcf"] = row["cfo"] - row["capex"]
            row["_derived"] = derived
            rows.append(row)
        return rows

    is_kr = ticker.endswith((".KS", ".KQ"))
    return {
        "ticker": ticker,
        "name": KR_NAMES.get(ticker, ticker),
        "region": "KR" if is_kr else "US",
        "currency": "KRW" if is_kr else "USD",
        "source": "Yahoo fundamentals-timeseries",
        "depth": "full",
        "as_of": dt.date.today().isoformat(),
        "annual": build("annual"),
        "quarterly": build("quarterly"),
    }


def fetch_many(tickers: list[str]) -> list[dict]:
    op = _opener()
    crumb = _crumb(op)
    out = []
    for i, t in enumerate(tickers):
        if i:
            time.sleep(1.2)          # 야후 페이싱
        out.append(fetch(t, op, crumb))
    return out


def save(rec: dict) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    p = os.path.join(CACHE_DIR, f"{rec['ticker'].replace('.', '_')}_yahoo.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    return p


def _fmt(v, unit):
    return "—" if v is None else f"{v/unit:,.0f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Yahoo 재무제표 3표 수집(무키)")
    ap.add_argument("--tickers", help="쉼표·공백 구분 (기본: 국내 보유 5 + 미국 402 4)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()

    tickers = [t.strip() for t in cli_common.split_tickers(a.tickers)] if a.tickers else KR_HOLDINGS + US_402
    out = fetch_many(tickers)
    if a.save:
        for r in out:
            if "_error" not in r:
                save(r)
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0

    for r in out:
        if "_error" in r:
            print(f"\n❌ {r['ticker']}: {r['_error']}")
            continue
        unit = 1e8 if r["region"] == "KR" else 1e6
        label = "억원" if r["region"] == "KR" else "백만USD"
        print(f"\n═══ {r['name']} ({r['ticker']}) — 연간 {len(r['annual'])}기 · "
              f"분기 {len(r['quarterly'])}기  [{r['source']}]")
        for tag, rows in (("연간", r["annual"][:3]), ("분기", r["quarterly"][:4])):
            if not rows:
                continue
            print(f"  [{tag}] ({label})")
            print("   기간말        매출     영업이익     순이익     자산총계    부채총계"
                  "     재고      영업CF       FCF")
            for w in rows:
                print(f"   {w['end']} {_fmt(w['revenue'],unit):>11} {_fmt(w['operating_income'],unit):>10}"
                      f" {_fmt(w['net_income'],unit):>10} {_fmt(w['assets'],unit):>12}"
                      f" {_fmt(w['liabilities'],unit):>11} {_fmt(w['inventory'],unit):>9}"
                      f" {_fmt(w['cfo'],unit):>11} {_fmt(w['fcf'],unit):>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
