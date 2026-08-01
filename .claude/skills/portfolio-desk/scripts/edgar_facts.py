#!/usr/bin/env python3
"""edgar_facts.py — 미국 보유종목 재무제표 3표 수집기 (SEC EDGAR XBRL, 무키·stdlib)

정훈 지시(2026-07-29 "우리 포트폴리오 기업들 재무제표도 다 보고 있나? 없으면 다 찾아").

**왜 EDGAR인가**: FMP 무료 플랜은 MU·ANET·AVGO·ORCL을 402로 막는다 — 하필 메모리·AI인프라
논지의 중심 4종목이라 이들 0~100 스코어가 하드넘버 없이 떠 있었다. EDGAR `companyfacts`는
**무키·전 종목·전 시계열**이고 회사가 SEC에 신고한 **1차 출처**다(FMP·야후는 2차 가공).
레포에 이미 EDGAR 사용 선례 있음 — guru_flows.py(13F).

산출 = 손익계산서·재무상태표·현금흐름표를 지역 무관 단일 스키마(financials.py와 공유)로 정규화:
  연간(10-K) 최근 5기 + 분기(10-Q/10-K) 최근 8기.

⚠️ XBRL 파싱 함정 3가지 (전부 실측으로 확인·대응):
  ① **태그가 회사마다 다르다** — ANET엔 `Revenues`가 없고 `RevenueFromContractWith
     CustomerExcludingAssessedTax`만 있다 → 항목별 폴백 체인(TAGS)으로 순차 시도.
  ② **같은 기간이 여러 번 신고된다** — MU `Assets` 2024-08-29가 fy2024·fy2025 두 번 등장.
     → (end, 기간종류) 그룹에서 `filed` 최신 1건만 채택.
  ③ **flow vs stock 구분** — 손익·현금흐름은 기간(start~end) 팩트, 재무상태표는 시점(end) 팩트.
     기간 길이로 연간(330~400일)/분기(60~120일)를 갈라야 분기 숫자가 연간 자리에 섞이지 않는다.

사용:
  python3 edgar_facts.py                          # 미국 보유 전 종목
  python3 edgar_facts.py --tickers MU,ANET
  python3 edgar_facts.py --tickers NVDA --json
  python3 edgar_facts.py --save                   # data/financials/{TICKER}.json 캐시
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CACHE_DIR = os.path.join(ROOT, "data", "financials")
CIK_MAP = os.path.join(CACHE_DIR, "_cik_map.json")

# SEC는 식별 가능한 User-Agent를 요구한다(없으면 403). 연락처 포함이 SEC 권고.
UA = "Jeonghun Portfolio Desk (contact: dpm5bfb6k9@privaterelay.appleid.com)"
SEC_PACE = 0.15  # SEC 권고 10 req/s 이하

# 미국 보유 10종목 (VOO=ETF는 SEC 재무제표 신고 대상 아님 → 제외)
US_HOLDINGS = ["NVDA", "MU", "AAPL", "MSFT", "ANET", "AVGO", "GOOGL", "META", "ORCL"]

# 항목별 us-gaap 태그 폴백 체인 — 앞에서부터 시도해 먼저 잡히는 것을 쓴다.
TAGS: dict[str, list[str]] = {
    # ── 손익계산서 (flow)
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "eps_diluted": ["EarningsPerShareDiluted"],
    "shares_diluted": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "rnd": ["ResearchAndDevelopmentExpense"],
    # ── 재무상태표 (stock/instant)
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue",
             "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "inventory": ["InventoryNet"],
    "receivables": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"],
    "assets_current": ["AssetsCurrent"],
    "liabilities_current": ["LiabilitiesCurrent"],
    "deferred_revenue": ["ContractWithCustomerLiabilityCurrent", "DeferredRevenueCurrent"],
    # ── 현금흐름표 (flow)
    "cfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment",
              "PaymentsToAcquireProductiveAssets"],
    "buyback": ["PaymentsForRepurchaseOfCommonStock"],
}
# 부채는 장기+단기를 합쳐야 해서 별도 처리
#
# ★[8/1 사고 수정] 회사에 따라 **장·단기를 이미 합친 단일 태그**만 신고한다.
#   ORCL이 그 경우다 — `LongTermDebtNoncurrent`가 아예 없고 `DebtCurrent`(단기 $7.2B)만
#   잡혀서 총차입금이 **실제 $129.5B의 1/18**로 들어왔다. 그 결과 net_cash가
#   **-98B(순차입) → +24.1B(순현금 흑자)** 로 부호까지 뒤집혀, 룰2 조건③(순부채 증가)이
#   구조적으로 발동 불가였고 재무건전성 서브스코어가 거꾸로 매겨졌다.
#   ⇒ combined 태그를 **최우선**으로 보고, 없을 때만 long+short를 더한다(이중계상 방지).
DEBT_COMBINED = ["DebtLongtermAndShorttermCombinedAmount"]
DEBT_LONG = ["LongTermDebtNoncurrent", "LongTermDebt",
             "LongTermDebtAndCapitalLeaseObligations"]
DEBT_SHORT = ["LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings",
              "OtherShortTermBorrowings"]

# 시점(instant) 팩트 — start가 없다
STOCK_KEYS = {"assets", "liabilities", "equity", "cash", "inventory", "receivables",
              "assets_current", "liabilities_current", "deferred_revenue"}


# ─────────────────────────────────────────── HTTP

def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Encoding": "gzip", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        return raw


def cik_map(refresh: bool = False) -> dict[str, str]:
    """티커 → 10자리 CIK. sec.gov/files/company_tickers.json 1회 받아 캐시."""
    if not refresh and os.path.exists(CIK_MAP):
        try:
            with open(CIK_MAP, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    data = json.loads(_get("https://www.sec.gov/files/company_tickers.json").decode())
    out = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CIK_MAP, "w", encoding="utf-8") as f:
        json.dump(out, f)
    return out


def company_facts(cik: str) -> dict:
    return json.loads(_get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json").decode())


# ─────────────────────────────────────────── XBRL 정규화

def _days(f: dict) -> int | None:
    s, e = f.get("start"), f.get("end")
    if not s or not e:
        return None
    try:
        return (dt.date.fromisoformat(e) - dt.date.fromisoformat(s)).days
    except ValueError:
        return None


def _bucket(f: dict, is_stock: bool) -> str | None:
    """팩트를 'annual' / 'quarterly' 로 분류. 함정 ③ 대응."""
    if is_stock:
        return "instant"
    d = _days(f)
    if d is None:
        return None
    if 330 <= d <= 400:
        return "annual"
    if 60 <= d <= 120:
        return "quarterly"
    return None  # 6개월·9개월 누적 팩트는 버린다(연간/분기 어느 쪽도 아님)


def _raw(facts: dict, tag: str) -> list[dict]:
    """태그의 원본 팩트 리스트(10-K/10-Q만)."""
    node = facts.get("facts", {}).get("us-gaap", {}).get(tag)
    if not node:
        return []
    units = node.get("units", {})
    # USD 우선, 없으면 첫 단위(EPS는 USD/shares, 주식수는 shares)
    key = next((u for u in ("USD", "USD/shares", "shares") if u in units), None) or \
        next(iter(units), None)
    if key is None:
        return []
    return [f for f in units[key] if f.get("form") in ("10-K", "10-Q")]


def _pick(rows: list[dict], bucket: str, is_stock: bool) -> dict[str, float]:
    """해당 bucket 팩트만 골라 {end: val}. 중복 신고는 filed 최신 채택(함정 ②)."""
    want = "instant" if is_stock else bucket
    best: dict[str, dict] = {}
    for f in rows:
        if _bucket(f, is_stock) != want:
            continue
        e = f["end"]
        prev = best.get(e)
        if prev is None or (f.get("filed") or "") > (prev.get("filed") or ""):
            best[e] = f
    return {e: f.get("val") for e, f in best.items()}


def _ytd_to_quarterly(rows: list[dict]) -> dict[str, float]:
    """누적(YTD) 팩트만 신고하는 회사의 분기값을 차분으로 복원.

    현금흐름표는 분기 단독 수치를 안 내고 회계연도 누적만 내는 회사가 많다(MU 등).
    같은 `start`를 공유하는 팩트를 end 순으로 세워 인접 차분을 취하되, 증분 구간이
    한 분기(60~120일)일 때만 채택한다.
    """
    by_start: dict[str, dict[str, dict]] = {}
    for f in rows:
        d = _days(f)
        if d is None or not (0 < d <= 400):
            continue
        slot = by_start.setdefault(f["start"], {})
        prev = slot.get(f["end"])
        if prev is None or (f.get("filed") or "") > (prev.get("filed") or ""):
            slot[f["end"]] = f
    out: dict[str, float] = {}
    for _start, ends in by_start.items():
        prev_val, prev_end = 0.0, None
        for e, f in sorted(ends.items()):
            span = _days(f) if prev_end is None else \
                (dt.date.fromisoformat(e) - dt.date.fromisoformat(prev_end)).days
            if f.get("val") is not None and 60 <= span <= 120:
                out.setdefault(e, f["val"] - prev_val)
            prev_val, prev_end = f.get("val") or 0.0, e
    return out


def _series(facts: dict, tag_list: list[str], is_stock: bool) -> dict[str, dict[str, float]]:
    """{bucket: {end: value}}.

    ⚠️ 폴백 체인은 **버킷별로** 평가한다(함정 ①의 심화형). ANET capex가 실례 —
    `PaymentsToAcquirePropertyPlantAndEquipment`엔 분기 팩트만 있고 연간은
    `PaymentsToAcquireProductiveAssets`에만 있다. 태그 단위로 끊으면 연간이 통째로 날아간다.

    ⚠️ 그리고 체인은 "먼저 잡히면 끝"이 아니라 **우선순위를 지킨 합집합**이다. 회사가 연도
    중간에 태그를 갈아타기 때문 — ANET capex는 `...PropertyPlantAndEquipment`에 2019년까지만
    연간이 있고 2020년 이후는 `...ProductiveAssets`에 있다. 먼저 잡힌 태그로 끊으면 최근
    연도가 빈다 → 낮은 우선순위부터 덮어써서 커버리지는 합치고, 충돌 시 앞 태그가 이긴다.
    """
    raws = {t: _raw(facts, t) for t in tag_list}
    out: dict[str, dict[str, float]] = {}
    for bucket in ("annual", "quarterly"):
        merged: dict[str, float] = {}
        for t in reversed(tag_list):
            merged.update(_pick(raws[t], bucket, is_stock))
        # 분기 직접 신고가 없으면 YTD 차분으로 복원(현금흐름표에서 흔함)
        if bucket == "quarterly" and not is_stock and not merged:
            for t in reversed(tag_list):
                merged.update(_ytd_to_quarterly(raws[t]))
        if merged:
            out[bucket] = merged
    return out


def _debt_series(facts: dict) -> dict[str, dict[str, float]]:
    """총차입금. **combined 태그 우선**, 없으면 장기+단기 합산.

    ⚠️ combined는 이미 장·단기를 합친 값이라 long/short와 **더하면 이중계상**된다.
       그래서 시점(end)마다 combined가 있으면 그것만 쓴다.
    """
    cb = _series(facts, DEBT_COMBINED, True)
    lo = _series(facts, DEBT_LONG, True)
    sh = _series(facts, DEBT_SHORT, True)
    out: dict[str, dict[str, float]] = {}
    for b in ("annual", "quarterly"):
        ends = set(cb.get(b, {})) | set(lo.get(b, {})) | set(sh.get(b, {}))
        for e in ends:
            c = cb.get(b, {}).get(e)
            v = c if c else (lo.get(b, {}).get(e) or 0) + (sh.get(b, {}).get(e) or 0)
            if v:
                out.setdefault(b, {})[e] = v
    return out


def normalize(ticker: str, facts: dict, n_annual: int | None = None,
              n_quarter: int | None = None) -> dict:
    """companyfacts → 단일 스키마(financials.py 공유).

    기본은 **전 시계열 적재**(정훈 지시 "이전 자료들도 다 가져와서 학습"). companyfacts는
    한 콜에 상장 이래 전부를 주므로 잘라 담을 이유가 없다 — 상장 이래 마진·재고·FCF 사이클을
    통째로 갖고 있어야 "지금이 메모리 정점인가"를 과거 사이클과 대조할 수 있다.
    """
    cols: dict[str, dict[str, dict[str, float]]] = {}
    for name, tags in TAGS.items():
        cols[name] = _series(facts, tags, name in STOCK_KEYS)
    cols["total_debt"] = _debt_series(facts)

    def build(bucket: str, limit: int | None) -> list[dict]:
        # 기준 축 = 매출(없으면 순이익) 신고 기간
        anchor = cols["revenue"].get(bucket) or cols["net_income"].get(bucket) or {}
        ends = sorted(anchor, reverse=True)
        if limit:
            ends = ends[:limit]
        rows = []
        for e in ends:
            row = {"end": e, "period": bucket}
            for name in list(TAGS) + ["total_debt"]:
                row[name] = cols.get(name, {}).get(bucket, {}).get(e)
            derived = []
            # ORCL처럼 `Liabilities`를 아예 신고 안 하는 회사가 있다 → 자산 - 자본으로 유도.
            if row.get("liabilities") is None and row.get("assets") is not None \
                    and row.get("equity") is not None:
                row["liabilities"] = row["assets"] - row["equity"]
                derived.append("liabilities=assets-equity")
            capex = row.get("capex")
            cfo = row.get("cfo")
            # EDGAR capex는 유출을 양수로 신고 → FCF = CFO - capex
            row["fcf"] = (cfo - capex) if (cfo is not None and capex is not None) else None
            row["_derived"] = derived
            rows.append(row)
        return rows

    return {
        "ticker": ticker,
        "name": facts.get("entityName"),
        "region": "US",
        "currency": "USD",
        "source": "SEC EDGAR XBRL companyfacts",
        "depth": "full",
        "as_of": dt.date.today().isoformat(),
        "annual": build("annual", n_annual),
        "quarterly": build("quarterly", n_quarter),
    }


def fetch(ticker: str, cmap: dict[str, str] | None = None) -> dict:
    t = ticker.upper()
    cmap = cmap or cik_map()
    cik = cmap.get(t)
    if not cik:
        return {"ticker": t, "_error": f"CIK 없음 (SEC 미신고 종목이거나 티커 오류)"}
    try:
        return normalize(t, company_facts(cik))
    except urllib.error.HTTPError as e:
        return {"ticker": t, "_error": f"HTTP {e.code}"}
    except Exception as e:  # pragma: no cover
        return {"ticker": t, "_error": str(e)[:120]}


def save(rec: dict) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    p = os.path.join(CACHE_DIR, f"{rec['ticker']}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    return p


# ─────────────────────────────────────────── CLI

def _fmt(v, unit=1e6):
    if v is None:
        return "—"
    return f"{v/unit:,.0f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="SEC EDGAR 재무제표 3표 수집")
    ap.add_argument("--tickers", help="쉼표 구분 (기본: 미국 보유 전 종목)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--save", action="store_true", help="data/financials/ 에 캐시")
    ap.add_argument("--quarters", type=int, default=8)
    a = ap.parse_args()

    tickers = [t.strip().upper() for t in a.tickers.split(",")] if a.tickers else US_HOLDINGS
    cmap = cik_map()
    out = []
    for i, t in enumerate(tickers):
        if i:
            time.sleep(SEC_PACE)
        out.append(fetch(t, cmap))

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
        print(f"\n═══ {r['ticker']}  {r['name']}  ({r['source']})")
        for label, rows in (("연간", r["annual"][:3]), ("분기", r["quarterly"][:4])):
            if not rows:
                continue
            print(f"  [{label}] (백만 USD)")
            print("   기간말      매출      영업이익    순이익    자산총계   부채총계"
                  "    현금      재고    영업CF     FCF")
            for w in rows:
                print(f"   {w['end']}  {_fmt(w['revenue']):>9} {_fmt(w['operating_income']):>10}"
                      f" {_fmt(w['net_income']):>9} {_fmt(w['assets']):>10} {_fmt(w['liabilities']):>10}"
                      f" {_fmt(w['cash']):>9} {_fmt(w['inventory']):>9}"
                      f" {_fmt(w['cfo']):>9} {_fmt(w['fcf']):>9}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
