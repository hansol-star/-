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
   ★[11/22 D1] `OperatingIncome == GrossProfit`(영업이익 칸에 매출총이익)도 무효화 + margin_suspect.

사용:
  python3 yahoo_facts.py                       # 국내 보유(portfolio.json) + 미국 402
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

# 국내 보유 (Yahoo 티커) — 원익IPS·테스는 .KQ (6/14 교정 이력 준수)
# ★[2026-11-22 감사 A7] 舊 리터럴 = 11/20 매도 두산로보·현대차·NAVER가 남은 '국내 보유 5'였고, 이름표도 그 5개뿐이라
#   국내 워치(KT&G·셀트리온 등) 재무의 name이 티커로 찍혔다. 이제 기본 대상·이름 = portfolio.json(market_data)
#   보유·워치·퇴역 워치이고, 아래 리터럴은 그것을 못 읽을 때만 쓰는 폴백이다(11/22 국내 보유와 같은 값).
KR_HOLDINGS = ["005930.KS", "066570.KS"]
KR_NAMES = {"005930.KS": "삼성전자", "066570.KS": "LG전자", "454910.KS": "두산로보틱스",
            "005380.KS": "현대차", "035420.KS": "NAVER"}
# FMP가 402로 막는 미국 종목 = EDGAR 교차검증 우선 대상 (★11/22 — ANET 11/13 매도로 기본 대상에서 뺐다)
US_402 = ["MU", "AVGO", "ORCL"]


def _md():
    try:
        import market_data as m
        return m
    except Exception:                                    # noqa: BLE001
        return None


def kr_holdings() -> list[str]:
    """국내 보유(portfolio.json holdings) — 못 읽으면 KR_HOLDINGS 폴백."""
    m = _md()
    try:
        tks = [t for t in m.held_tickers() if t.endswith((".KS", ".KQ"))] if m else []
    except Exception:                                    # noqa: BLE001
        tks = []
    return tks or list(KR_HOLDINGS)


def name_of(ticker: str) -> str:
    """표시명 — portfolio.json(보유·워치·퇴역 워치) label → KR_NAMES → 티커."""
    m = _md()
    try:
        lab = (m.labels() if m else {}).get(ticker)
    except Exception:                                    # noqa: BLE001
        lab = None
    return lab or KR_NAMES.get(ticker, ticker)

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


def _same(a, b) -> bool:
    """두 금액이 사실상 같은가(상대 오차 1e-6 — 한쪽만 천 단위 반올림된 경우까지)."""
    return a is not None and b is not None and abs(a - b) < max(1, abs(b) * 1e-6)


def sanitize(row: dict) -> list[str]:
    """Yahoo(2차 가공) 실측 이상치를 **무효화**하고 사유 목록을 돌려준다(row를 제자리 수정).

    · gross_profit==revenue : NAVER 등 서비스업 매출원가 미분류(구조적)
    · operating_income==revenue : 순수 매핑 오류(NAVER 2025-06-30에서 실제 발생.
      영업이익률 19%인 회사가 100%로 찍힘 → 그대로 쓰면 마진 추세 판정이 붕괴)
    · ★[2026-11-22 감사 D1] operating_income==gross_profit : 영업이익 칸에 **매출총이익**이 들어온 매핑 오류.
      2026-09-30 분기에 LG전자(영업마진 24.4% ↔ 연간 2.8%·순마진 2.8%)·두산로보·삼성전기·셀트리온 4종목이
      동시에 걸렸고, 삼성전자도 같은 R3 직전엔 69.3%였다. 룰8 ⓑ(분기 영업마진 2분기 연속 하락)가 가려진다.
      판관비를 따로 안 나누는 회사는 실제로 둘이 같을 수 있다 → 값을 **추정해 넣지 않고** None +
      `margin_suspect` 플래그만 단다(판정은 '결측'으로 보류된다 — financials margin_trend_gap).
    어느 쪽이든 추정으로 메우지 않고 None + 플래그(CLAUDE.md "추측 금지·미확인 명시")."""
    derived = []
    gp0 = row.get("gross_profit")
    for fld in ("gross_profit", "operating_income"):
        # ★[11/1] 절대 오차 1 → 상대 오차 — Yahoo가 한쪽만 천 단위로 반올림해 차이 210원으로
        #   빠져나갔다(NAVER 2025-06 영업이익 = 매출, 영업마진 100%).
        if row.get("revenue") and _same(row.get(fld), row["revenue"]):
            row[fld] = None
            derived.append(f"{fld} 무효화(매출과 동일 — Yahoo 매핑 이상)")
    # 매출총이익이 매출과 같아 이미 무효화됐으면(서비스업 구조) 이 비교는 뜻이 없다 — 남은 값끼리만 본다
    if row.get("gross_profit") is not None and _same(row.get("operating_income"), gp0):
        row["operating_income"] = None
        row["margin_suspect"] = True
        derived.append("operating_income 무효화(매출총이익과 동일 — Yahoo 매핑 이상 · margin_suspect)")
    return derived


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
            derived = sanitize(row)
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
        "name": name_of(ticker),
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
    ap.add_argument("--tickers", help="쉼표·공백 구분 (기본: 국내 보유(portfolio.json) + 미국 402)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()

    tickers = [t.strip() for t in cli_common.split_tickers(a.tickers)] if a.tickers else kr_holdings() + US_402
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
