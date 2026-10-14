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
  ④ **회계 4분기는 분기 팩트가 없다**(10/14) — 10-K는 연간(12개월) 팩트만 태깅한다. 그대로 두면
     분기 시계열이 해마다 한 칸씩 비고, '최신 3개 분기'·'4칸 뒤 = 1년 전' 같은 **위치 가정이
     조용히 틀린다**(financials `margin_trend_break`가 4분기를 건너뛰고 비교했다).
     → 4분기 = 연간 − (그 회계연도 1~3분기 합)으로 역산하고 행에 `q4_derived: true`를 남긴다.
     세 분기가 다 있고 분기말 간격이 한 분기일 때만 역산한다. 희석 EPS·가중평균 주식수는
     **가산이 안 되므로** 근사값이고(`_derived`에 표기) 두 근사가 어긋나면 결측으로 둔다.
     ⚠️ 연간(10-K)이 분기(10-Q) 신고 뒤의 재분류·정정을 담으면 그 차이가 4분기에 몰린다.
  ⑤ **현금흐름표는 2·3분기를 누적(YTD)으로만 신고한다** — 1분기만 단독 값이 있어 분기 CFO·
     capex·FCF가 2·3분기에 비어 있었다. 누적 차분으로 **빈 분기만** 채운다(직접 신고가 우선).

사용:
  python3 edgar_facts.py                          # 미국 보유 전 종목
  python3 edgar_facts.py --tickers MU,ANET
  python3 edgar_facts.py --tickers NVDA --json
  python3 edgar_facts.py --save                   # data/financials/{TICKER}.json 캐시
  python3 edgar_facts.py --selftest               # 오프라인 — 4분기 역산·누적 차분·EPS 근사 검증
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
import cli_common

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
# ★[10/10 R3] CDNS 실측 — `UnsecuredLongTermDebt`($2.48B, 2026-03-31)로만 태깅해서
#   total_debt가 **결측**으로 나왔다(validate `부채태그 의심` WARN이 잡은 ORCL 사고 유형의 두 번째 사례).
#   ⇒ Unsecured 계열을 long/short에 추가. combined 우선 원칙은 그대로라 이중계상 없음.
DEBT_LONG = ["LongTermDebtNoncurrent", "LongTermDebt",
             "LongTermDebtAndCapitalLeaseObligations",
             "UnsecuredLongTermDebt", "UnsecuredLongTermNotesPayable"]
DEBT_SHORT = ["LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings",
              "OtherShortTermBorrowings", "UnsecuredDebtCurrent"]

# 시점(instant) 팩트 — start가 없다
STOCK_KEYS = {"assets", "liabilities", "equity", "cash", "inventory", "receivables",
              "assets_current", "liabilities_current", "deferred_revenue"}

# 가산되는 유량 계정 — 누적(YTD) 차분·4분기 역산 대상.
# ⚠️ 희석 EPS·가중평균 희석주식수는 **여기 넣지 않는다**: 6개월 가중평균 − 3개월 가중평균은
#    2분기 주식수가 아니라 0 근처의 쓰레기 값이다. 이 둘의 4분기는 `_q4_per_share`가 근사한다.
ADDITIVE_FLOW = {"revenue", "gross_profit", "operating_income", "net_income", "rnd",
                 "cfo", "capex", "buyback"}

# 연속한 두 분기말의 간격(일). 13주 = 91 · 14주(53주 회계연도) = 98 · 달력 분기 = 89~92.
# financials.py의 연속성 판정이 **이 상수를 그대로** 쓴다(따로 두면 한쪽만 고쳐진다).
QTR_GAP = (80, 100)
SHARES_Q4_TOL = 0.15    # 역산 4분기 주식수가 연간 가중평균과 이보다 벌어지면 버린다(분할 스케일 혼재)
EPS_Q4_TOL = 0.05       # 두 EPS 근사(순이익÷주식수 vs 연간−3분기)의 허용 이격 — 넘으면 결측
EPS_Q4_ABS = 0.03       # 위 허용치의 절대 하한(EPS는 센트 반올림 넷이 겹친다)


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


# ─────────────────────────────────────────── companyfacts 미반영 신고 보충
#
# ★[10/14] CDNS 실측 — 2026-07-29 신고 10-Q(기말 2026-06-30)가 companyfacts에 **2.5개월째 없었다**
#   (그 안의 가장 늦은 filed = 2026-05-01). submissions·frames API·신고 원본엔 다 있다 = 집계 API만 늦다.
#   financials의 폴백(EDGAR → Yahoo)은 EDGAR가 **응답은 했으니** 내려가지 않았고, 펀더 서브스코어는
#   한 분기 낡은 시계열로 계산됐다(최신 분기 2026-03-31).
#   ⇒ submissions의 최근 10-Q/10-K 중 companyfacts에 접수번호(accn)가 없는 신고를 찾아 **그 신고의 XBRL
#     인스턴스**를 companyfacts 행 모양으로 바꿔 끼운다. 같은 회사·같은 us-gaap 태그·같은 1차 출처라
#     4분기 역산·누적 차분·연속성 판정이 그대로 돈다. Yahoo로 메우지 않는 이유 = 정의가 다른 값
#     (영업이익·FCF 산식)이 한 시계열에 섞이면 그 분기의 '마진 변화'가 회계가 아니라 출처 차이가 된다.
#   못 메우면 `edgar_missing`에 남고 financials `margin_trend_gap`이 사유로 낸다(조용히 낡지 않게).
PERIODIC_FORMS = ("10-Q", "10-K")      # `_raw`가 읽는 form과 같다(정정 신고 /A는 둘 다 안 본다)
SUPPLEMENT_LOOKBACK = 400              # 이보다 오래된 미반영 신고는 보지 않는다(옛 비-XBRL 신고 등)
SUPPLEMENT_MAX = 6                     # 한 종목에서 받을 인스턴스 상한(companyfacts가 통째로 멈춘 경우)
_XI = "{http://www.xbrl.org/2003/instance}"
_XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"


def submissions(cik: str) -> dict:
    return json.loads(_get(f"https://data.sec.gov/submissions/CIK{cik}.json").decode())


def _accns(facts: dict) -> set[str]:
    out: set[str] = set()
    for ns in (facts.get("facts") or {}).values():
        for node in ns.values():
            for rows in (node.get("units") or {}).values():
                out.update(r["accn"] for r in rows if r.get("accn"))
    return out


def missing_filings(facts: dict, sub: dict, today: dt.date | None = None) -> list[dict]:
    """submissions엔 있는데 companyfacts엔 접수번호가 없는 최근 10-Q/10-K(XBRL 신고만). 최신 순."""
    have = _accns(facts)
    rec = (sub.get("filings") or {}).get("recent") or {}
    cutoff = ((today or dt.date.today()) - dt.timedelta(days=SUPPLEMENT_LOOKBACK)).isoformat()
    xbrl = rec.get("isXBRL") or []
    out = []
    for i, form in enumerate(rec.get("form") or []):
        if form not in PERIODIC_FORMS:
            continue
        accn, filed = rec["accessionNumber"][i], rec["filingDate"][i]
        if filed < cutoff or accn in have or (i < len(xbrl) and not xbrl[i]):
            continue
        out.append({"accn": accn, "form": form, "filed": filed, "period_end": rec["reportDate"][i]})
    return sorted(out, key=lambda m: m["filed"], reverse=True)


def instance_xml(cik: str, accn: str) -> bytes:
    """신고 폴더에서 XBRL 인스턴스를 받는다. 인라인 XBRL은 SEC가 `*_htm.xml`로 추출해 둔다."""
    import re
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}/"
    names = [it["name"] for it in json.loads(_get(base + "index.json").decode())["directory"]["item"]]
    pick = next((n for n in names if n.endswith("_htm.xml")), None) or next(
        (n for n in names if n.endswith(".xml")
         and not re.search(r"(_cal|_def|_lab|_pre)\.xml$|^FilingSummary", n)), None)
    if not pick:
        raise LookupError("인스턴스 파일 없음")
    time.sleep(SEC_PACE)
    return _get(base + pick, timeout=60)


def parse_instance(xml: bytes, meta: dict) -> dict[str, dict[str, list[dict]]]:
    """XBRL 인스턴스 → {us-gaap 태그: {단위: [companyfacts 모양 행]}}.

    companyfacts와 같게 **차원 없는 컨텍스트만** 담는다(세그먼트·제품별 매출이 합계 자리에 들어가면
    안 된다 — CDNS 2분기 매출 컨텍스트 288개 중 차원 없는 것은 10개). 같은 (태그·단위·기간)은
    본문·주석에 반복 태깅되므로 한 번만 담는다.
    """
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    ctx: dict[str, tuple[str | None, str]] = {}
    for c in root.iter(_XI + "context"):
        if c.find(f"{_XI}entity/{_XI}segment") is not None or c.find(_XI + "scenario") is not None:
            continue
        per = c.find(_XI + "period")
        if per is None:
            continue
        s, e, i = (per.findtext(_XI + k) for k in ("startDate", "endDate", "instant"))
        if s and e:
            ctx[c.get("id")] = (s.strip(), e.strip())
        elif i:
            ctx[c.get("id")] = (None, i.strip())

    def local(m) -> str:
        return (m.text or "").strip().split(":")[-1]

    units: dict[str, str] = {}
    for u in root.iter(_XI + "unit"):
        div = u.find(_XI + "divide")
        if div is not None:
            num = "*".join(local(m) for m in div.find(_XI + "unitNumerator").iter(_XI + "measure"))
            den = "*".join(local(m) for m in div.find(_XI + "unitDenominator").iter(_XI + "measure"))
            units[u.get("id")] = f"{num}/{den}"
        else:
            units[u.get("id")] = "*".join(local(m) for m in u.iter(_XI + "measure"))

    out: dict[str, dict[str, list[dict]]] = {}
    seen: set[tuple] = set()
    for el in root:
        if not el.tag.startswith("{http://fasb.org/us-gaap/"):
            continue
        cref, uref = el.get("contextRef"), el.get("unitRef")
        if cref not in ctx or uref not in units or el.get(_XSI_NIL) == "true":
            continue
        try:
            v = float((el.text or "").strip())
        except ValueError:
            continue
        s, e = ctx[cref]
        tag = el.tag.split("}", 1)[1]
        key = (tag, units[uref], s, e)
        if key in seen:
            continue
        seen.add(key)
        row = {"end": e, "val": int(v) if v.is_integer() else v, "accn": meta["accn"],
               "form": meta["form"], "filed": meta["filed"], "_from": "xbrl_instance"}
        if s:
            row["start"] = s
        out.setdefault(tag, {}).setdefault(units[uref], []).append(row)
    return out


def supplement(facts: dict, sub: dict, fetch_xml, today: dt.date | None = None) -> dict:
    """미반영 신고의 팩트를 facts(us-gaap)에 **제자리로** 끼운다. 반환 = {added, missing}.

    `fetch_xml(meta) -> bytes` — 실전은 `instance_xml`, 자가검증은 픽스처를 준다.
    끼운 행은 companyfacts 행과 같은 규칙(`_pick_facts` = 같은 기간이면 filed 최신)으로 경쟁한다
    — companyfacts가 그 신고를 담았다면 생겼을 상태와 같다(전년 비교 기간의 재분류 포함).
    """
    gaap = facts.setdefault("facts", {}).setdefault("us-gaap", {})
    added, missing = [], []
    for meta in missing_filings(facts, sub, today)[:SUPPLEMENT_MAX]:
        try:
            parsed = parse_instance(fetch_xml(meta), meta)
        except Exception as e:      # 네트워크·파싱 — 못 메운 사실을 남긴다
            missing.append({**meta, "why": f"{type(e).__name__}: {str(e)[:80]}"})
            continue
        n = 0
        for tag, by_unit in parsed.items():
            node = gaap.setdefault(tag, {"units": {}}).setdefault("units", {})
            for unit, rows in by_unit.items():
                node.setdefault(unit, []).extend(rows)
                n += len(rows)
        if n:
            added.append({**meta, "facts": n})
        else:
            missing.append({**meta, "why": "인스턴스에 차원 없는 us-gaap 팩트 0개"})
    facts["_supplement"] = {"added": added, "missing": missing}     # normalize가 여기서 읽는다
    return facts["_supplement"]


def facts_full(cik: str) -> dict:
    """companyfacts + 미반영 신고 보충. 보충 결과는 `facts["_supplement"]`에 남는다.

    submissions 조회가 실패하면 보충 없이 companyfacts만 돌려준다(그 사실도 남긴다 —
    '확인 못 함'과 '미반영 없음'을 구별해야 한다).
    """
    facts = company_facts(cik)
    try:
        time.sleep(SEC_PACE)
        supplement(facts, submissions(cik), lambda m: instance_xml(cik, m["accn"]))
    except Exception as e:
        facts["_supplement"] = {"added": [], "missing": [],
                                "error": f"submissions 조회 실패 — {type(e).__name__}: {str(e)[:80]}"}
    return facts


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


def _pick_facts(rows: list[dict], bucket: str, is_stock: bool) -> dict[str, dict]:
    """해당 bucket 팩트만 골라 {end: 팩트}. 중복 신고는 filed 최신 채택(함정 ②)."""
    want = "instant" if is_stock else bucket
    best: dict[str, dict] = {}
    for f in rows:
        if _bucket(f, is_stock) != want:
            continue
        e = f["end"]
        prev = best.get(e)
        if prev is None or (f.get("filed") or "") > (prev.get("filed") or ""):
            best[e] = f
    return best


def _pick(rows: list[dict], bucket: str, is_stock: bool) -> dict[str, float]:
    """`_pick_facts`의 {end: val} 판."""
    return {e: f.get("val") for e, f in _pick_facts(rows, bucket, is_stock).items()}


def _ytd_to_quarterly(rows: list[dict]) -> dict[str, float]:
    """누적(YTD) 팩트만 신고하는 회사의 분기값을 차분으로 복원.

    현금흐름표는 분기 단독 수치를 안 내고 회계연도 누적만 내는 회사가 많다(MU 등).
    같은 `start`를 공유하는 팩트를 end 순으로 세워 인접 차분을 취하되, 증분 구간이
    한 분기(60~120일)일 때만 채택한다.

    ⚠️ **가산되는 유량 계정에만** 쓴다(`ADDITIVE_FLOW`) — 가중평균 주식수·EPS엔 성립하지 않는다.
    ⚠️ 연간(12개월) 팩트는 여기서 쓰지 않는다. 4분기는 `_derive_q4` 한 군데서만 만든다
       (세 분기가 다 있는지·회계연도 창 안인지 검사하는 곳이 거기다).
    """
    by_start: dict[str, dict[str, dict]] = {}
    for f in rows:
        d = _days(f)
        if d is None or not (0 < d < 330):
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


def _fy_q123(end: str, start: str | None, quarterly: dict[str, float]) -> list[str] | None:
    """회계연도 [start, end] 안의 1~3분기 분기말 3개. 조건이 하나라도 안 맞으면 None.

    조건 = 연도 창 안에 값 있는 분기말이 **정확히 3개**이고, 연도 시작→1분기말→2분기말→
    3분기말→연도말의 네 구간이 전부 한 분기(`QTR_GAP`)다. 분기가 하나 빠졌거나 회계연도가
    바뀌는 전환기면 None — 그때 '연간 − 있는 분기들'을 하면 두 분기 값이 4분기로 둔갑한다.
    """
    if not start:
        return None
    inside = sorted(x for x, v in quarterly.items() if v is not None and start < x < end)
    if len(inside) != 3:
        return None
    try:
        d = [dt.date.fromisoformat(x) for x in [start] + inside + [end]]
    except ValueError:
        return None
    gaps = [(d[1] - d[0]).days + 1] + [(d[i + 1] - d[i]).days for i in (1, 2, 3)]
    if not all(QTR_GAP[0] <= g <= QTR_GAP[1] for g in gaps):
        return None
    return inside


def _derive_q4(annual: dict[str, float], fy_start: dict[str, str],
               quarterly: dict[str, float]) -> dict[str, float]:
    """회계 4분기 = 연간 − (그 회계연도 1~3분기 합). 함정 ④ 대응.

    직접 신고된 4분기 값이 있으면 건드리지 않는다(옛 10-K는 분기별 주석을 태깅했다).
    """
    out: dict[str, float] = {}
    for e, a_val in annual.items():
        if a_val is None or quarterly.get(e) is not None:
            continue
        q123 = _fy_q123(e, fy_start.get(e), quarterly)
        if q123:
            out[e] = a_val - sum(quarterly[x] for x in q123)
    return out


def _series(facts: dict, tag_list: list[str], is_stock: bool,
            additive: bool = False) -> dict[str, dict]:
    """{bucket: {end: value}} (+ 유량 계정은 `_fy_start`·`_src`).

    `_fy_start` = {연도말: 연도 시작일} — 4분기 역산이 회계연도 창을 여기서 읽는다.
    `_src`      = {분기말: "ytd" | "q4"} — 직접 신고가 아닌 분기 값의 출처(없으면 직접 신고).

    ⚠️ 폴백 체인은 **버킷별로** 평가한다(함정 ①의 심화형). ANET capex가 실례 —
    `PaymentsToAcquirePropertyPlantAndEquipment`엔 분기 팩트만 있고 연간은
    `PaymentsToAcquireProductiveAssets`에만 있다. 태그 단위로 끊으면 연간이 통째로 날아간다.

    ⚠️ 그리고 체인은 "먼저 잡히면 끝"이 아니라 **우선순위를 지킨 합집합**이다. 회사가 연도
    중간에 태그를 갈아타기 때문 — ANET capex는 `...PropertyPlantAndEquipment`에 2019년까지만
    연간이 있고 2020년 이후는 `...ProductiveAssets`에 있다. 먼저 잡힌 태그로 끊으면 최근
    연도가 빈다 → 낮은 우선순위부터 덮어써서 커버리지는 합치고, 충돌 시 앞 태그가 이긴다.
    """
    raws = {t: _raw(facts, t) for t in tag_list}
    out: dict[str, dict] = {}
    fy_start: dict[str, str] = {}
    src: dict[str, str] = {}
    for bucket in ("annual", "quarterly"):
        merged: dict[str, float] = {}
        for t in reversed(tag_list):
            picked = _pick_facts(raws[t], bucket, is_stock)
            merged.update({e: f.get("val") for e, f in picked.items()})
            if bucket == "annual" and not is_stock:
                fy_start.update({e: f.get("start") for e, f in picked.items()})
        if bucket == "quarterly" and additive:
            # ① 누적(YTD) 차분으로 **빈 분기만** 채운다(함정 ⑤). 직접 신고가 있으면 그게 이긴다.
            #    ★[10/14] 舊 = "직접 신고가 하나도 없을 때만" 복원 — 1분기는 누적 = 단독이라 늘
            #    직접 신고가 있었고, 그래서 이 복원은 한 번도 돌지 않았다(2·3분기 CFO·capex 결측).
            ytd: dict[str, float] = {}
            for t in reversed(tag_list):
                ytd.update(_ytd_to_quarterly(raws[t]))
            for e, v in ytd.items():
                if merged.get(e) is None:
                    merged[e] = v
                    src[e] = "ytd"
            # ② 회계 4분기 역산(함정 ④)
            for e, v in _derive_q4(out.get("annual", {}), fy_start, merged).items():
                merged[e] = v
                src[e] = "q4"
        if merged:
            out[bucket] = merged
    if fy_start:
        out["_fy_start"] = fy_start
    if src:
        out["_src"] = src
    return out


def _q4_per_share(cols: dict[str, dict]) -> dict[str, dict]:
    """역산 4분기의 희석주식수·희석 EPS **근사**. {분기말: {shares_diluted?, eps_diluted?, notes}}.

    둘 다 가산이 안 된다 — 그래서 `ADDITIVE_FLOW` 밖에 두고 여기서 따로 만든다.
      · 주식수 = 가중평균의 일수 가중 항등식: 연간평균×연간일수 = Σ 분기평균×분기일수
        (기본주식수엔 정확하고 희석주식수엔 근사다). 역산값이 연간 평균과 15% 넘게 벌어지면
        분할 스케일이 섞인 것이므로 버린다.
      · EPS   = 4분기 순이익 ÷ 위 주식수. '연간 EPS − 1~3분기 EPS 합'과 대조해 5% 넘게
        어긋나면 **결측**으로 둔다(틀린 EPS는 YoY·C축으로 그대로 흘러간다).
    """
    ni = cols.get("net_income") or {}
    sh = cols.get("shares_diluted") or {}
    ep = cols.get("eps_diluted") or {}
    sh_q, ep_q = sh.get("quarterly") or {}, ep.get("quarterly") or {}
    out: dict[str, dict] = {}
    for e, how in (ni.get("_src") or {}).items():
        if how != "q4":
            continue
        rec: dict = {}
        notes: list[str] = []
        ni_q4 = (ni.get("quarterly") or {}).get(e)

        s4 = sh_q.get(e)
        sh_a = (sh.get("annual") or {}).get(e)
        if s4 is None and sh_a:
            start = (sh.get("_fy_start") or {}).get(e)
            q123 = _fy_q123(e, start, sh_q)
            if q123:
                d = [dt.date.fromisoformat(x) for x in [start] + q123 + [e]]
                w = [(d[1] - d[0]).days + 1] + [(d[i + 1] - d[i]).days for i in (1, 2, 3)]
                cand = (sum(w) * sh_a - sum(wi * sh_q[x] for wi, x in zip(w, q123))) / w[3]
                if abs(cand / sh_a - 1) <= SHARES_Q4_TOL:
                    s4 = rec["shares_diluted"] = round(cand)
                    notes.append("shares_diluted≈(연간 가중평균×연간일수 − Σ분기 가중평균×분기일수)"
                                 "÷4분기일수 [근사]")
                else:
                    notes.append("shares_diluted=결측(역산값이 연간 평균과 15% 넘게 이격 — "
                                 "분할 스케일 혼재 의심)")

        if ep_q.get(e) is None:
            if s4 and ni_q4 is not None:
                est = ni_q4 / s4
                ep_a = (ep.get("annual") or {}).get(e)
                q123 = _fy_q123(e, (ep.get("_fy_start") or {}).get(e), ep_q)
                alt = (ep_a - sum(ep_q[x] for x in q123)) if (q123 and ep_a is not None) else None
                if alt is not None and abs(est - alt) > max(EPS_Q4_TOL * abs(alt), EPS_Q4_ABS):
                    notes.append(f"eps_diluted=결측(두 근사 불일치 — 순이익÷주식수 {est:.2f} vs "
                                 f"연간−3분기 {alt:.2f})")
                else:
                    rec["eps_diluted"] = round(est, 2)
                    notes.append("eps_diluted≈net_income÷shares_diluted [근사 — 희석 EPS는 "
                                 "분기 합이 연간과 같지 않다]")
            else:
                notes.append("eps_diluted=결측(4분기 희석주식수를 근사할 수 없다)")
        out[e] = {**rec, "notes": notes}
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
    cols: dict[str, dict] = {}
    for name, tags in TAGS.items():
        cols[name] = _series(facts, tags, name in STOCK_KEYS, additive=name in ADDITIVE_FLOW)
    cols["total_debt"] = _debt_series(facts)
    per_share = _q4_per_share(cols)
    sup = facts.get("_supplement") or {}
    sup_end = {m["period_end"]: m for m in sup.get("added") or []}

    def build(bucket: str, limit: int | None) -> list[dict]:
        # 기준 축 = 매출(없으면 순이익) 신고 기간
        anchor_name = "revenue" if cols["revenue"].get(bucket) else "net_income"
        anchor = cols[anchor_name].get(bucket) or {}
        ends = sorted(anchor, reverse=True)
        if limit:
            ends = ends[:limit]
        rows = []
        for e in ends:
            row = {"end": e, "period": bucket}
            for name in list(TAGS) + ["total_debt"]:
                row[name] = cols.get(name, {}).get(bucket, {}).get(e)
            derived = []
            if bucket == "quarterly":
                # 직접 신고가 아닌 값의 출처를 행에 남긴다 — 역산값이 1차 신고값처럼 보이면 안 된다.
                how = {n: (cols[n].get("_src") or {}).get(e) for n in TAGS}
                q4 = [n for n in TAGS if how[n] == "q4"]
                ytd = [n for n in TAGS if how[n] == "ytd"]
                if q4:
                    derived.append("q4=annual-(q1+q2+q3): " + ",".join(q4))
                if ytd:
                    derived.append("ytd_diff: " + ",".join(ytd))
                ps = per_share.get(e)
                if ps:
                    for k in ("shares_diluted", "eps_diluted"):
                        if k in ps:
                            row[k] = ps[k]
                    derived += ps["notes"]
                if anchor_name in q4:
                    row["q4_derived"] = True     # 이 분기 행 자체가 역산으로 생겼다(회계 4분기)
            if e in sup_end:
                # companyfacts가 아니라 신고 원본 인스턴스에서 읽은 기간 — 같은 1차 출처지만 경로가 다르다
                m = sup_end[e]
                derived.append(f"신고 원본 XBRL 보충(companyfacts 미반영 {m['form']} {m['accn']} · {m['filed']} 신고)")
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

    out = {
        "ticker": ticker,
        "name": facts.get("entityName"),
        "region": "US",
        "currency": "USD",
        "source": "SEC EDGAR XBRL companyfacts"
                  + (f" + 신고 원본 XBRL {len(sup_end)}건(companyfacts 미반영)" if sup_end else ""),
        "depth": "full",
        "as_of": dt.date.today().isoformat(),
        "annual": build("annual", n_annual),
        "quarterly": build("quarterly", n_quarter),
    }
    # 보충 결과는 있을 때만 남긴다(대부분의 종목은 미반영 신고가 없다)
    for k, v in (("edgar_supplement", sup.get("added")), ("edgar_missing", sup.get("missing")),
                 ("edgar_supplement_error", sup.get("error"))):
        if v:
            out[k] = v
    return out


def fetch(ticker: str, cmap: dict[str, str] | None = None) -> dict:
    t = ticker.upper()
    cmap = cmap or cik_map()
    cik = cmap.get(t)
    if not cik:
        return {"ticker": t, "_error": f"CIK 없음 (SEC 미신고 종목이거나 티커 오류)"}
    try:
        return normalize(t, facts_full(cik))
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


# ─────────────────────────────────────────── 자가검증 (오프라인)

# MU가 실제로 신고한 FY2024~FY2026 손익(단위 $M) — 10-Q는 분기 단독 + 누적, 10-K는 연간만.
# 4분기 정답 = SEC 8-K EX-99.1 GAAP 표(FQ4-26 2026-09-30 · FQ4-25 2025-09-23 · FQ4-24 2024-09-25).
# 현금흐름 누적 분할(2·3분기)과 재무상태표는 합성값이다.
_FX_YEARS = [
    # (연도 시작, [1~3분기말], 연도말, 10-K 신고일)
    ("2023-09-01", ["2023-11-30", "2024-02-29", "2024-05-30"], "2024-08-29", "2024-10-04"),
    ("2024-08-30", ["2024-11-28", "2025-02-27", "2025-05-29"], "2025-08-28", "2025-10-03"),
    ("2025-08-29", ["2025-11-27", "2026-02-26", "2026-05-28"], "2026-09-03", "2026-10-08"),
]
_FX_FLOW = {      # 태그: 연도별 ([1~3분기], 연간)
    "Revenues": [([4726, 5824, 6811], 25111), ([8709, 8053, 9301], 37378),
                 ([13643, 23860, 41456], 133188)],
    "GrossProfit": [([-35, 1079, 1832], 5613), ([3348, 2963, 3508], 14873),
                    ([7646, 17755, 35056], 107504)],
    "OperatingIncomeLoss": [([-1128, 191, 719], 1304), ([2174, 1773, 2169], 9770),
                            ([6136, 16135, 33318], 99340)],
    "NetIncomeLoss": [([-1234, 793, 332], 778), ([1870, 1583, 1885], 8539),
                      ([5240, 13785, 28243], 84969)],
}
_FX_CASHFLOW = {  # 누적으로만 신고(1분기는 누적 = 단독)
    "NetCashProvidedByUsedInOperatingActivities": [
        ([1401, 2620, 5102], 8507), ([3244, 7186, 11795], 17525), ([8411, 20314, 45702], 89675)],
    "PaymentsToAcquirePropertyPlantAndEquipment": [
        ([1796, 3180, 5320], 8386), ([3206, 7261, 10199], 15857), ([5389, 11776, 19602], 30712)],
}
_FX_EPS = [([-1.12, 0.71, 0.30], 0.70), ([1.67, 1.41, 1.68], 7.59), ([4.60, 12.07, 24.67], 74.33)]
_FX_SHARES = [([1100, 1114, 1123], 1118), ([1122, 1123, 1125], 1125), ([1138, 1142, 1145], 1143)]
_FX_ASSETS = {"2025-11-27": 85971, "2026-02-26": 98210, "2026-05-28": 121340, "2026-09-03": 158000,
              "2025-08-28": 82798, "2025-05-29": 78400, "2025-02-27": 73050, "2024-11-28": 71461,
              "2024-08-29": 69416}


def _fixture_facts(drop_quarters: tuple[str, ...] = (), annual_eps_scale: float = 1.0,
                   annual_shares_scale: float = 1.0,
                   direct_q4: dict[str, float] | None = None) -> dict:
    """오프라인 픽스처 — companyfacts 모양. 위반을 심는 손잡이:

      drop_quarters       그 분기말의 분기 단독·누적 팩트를 뺀다(분기 하나가 빠진 회계연도)
      annual_eps_scale    연간 EPS만 다른 스케일로(분할 뒤 재보고가 한쪽만 온 상태)
      annual_shares_scale 연간 가중평균 주식수만 다른 스케일로
      direct_q4           {연도말: 매출} — 4분기 단독 팩트를 직접 신고한 회사(옛 10-K)
    """
    def filed(end: str) -> str:
        return (dt.date.fromisoformat(end) + dt.timedelta(days=28)).isoformat()

    def fact(start, end, val, form, filed_on):
        return {"start": start, "end": end, "val": val, "form": form, "filed": filed_on}

    def q_start(start: str, qs: list[str], i: int) -> str:
        return start if i == 0 else (dt.date.fromisoformat(qs[i - 1]) + dt.timedelta(days=1)).isoformat()

    gaap: dict[str, dict] = {}

    def put(tag, unit, rows):
        gaap.setdefault(tag, {"units": {}})["units"].setdefault(unit, []).extend(rows)

    for yi, (start, qs, end, k_filed) in enumerate(_FX_YEARS):
        # 손익: 분기 단독(3개월) + 누적(6·9개월) + 연간
        for tag, years in _FX_FLOW.items():
            qv, av = years[yi]
            rows, ytd = [], 0
            for i, qe in enumerate(qs):
                ytd += qv[i]
                if qe in drop_quarters:
                    continue
                rows.append(fact(q_start(start, qs, i), qe, qv[i] * 1e6, "10-Q", filed(qe)))
                if i:
                    rows.append(fact(start, qe, ytd * 1e6, "10-Q", filed(qe)))
            rows.append(fact(start, end, av * 1e6, "10-K", k_filed))
            put(tag, "USD", rows)
        # 현금흐름: 누적만
        for tag, years in _FX_CASHFLOW.items():
            cum, av = years[yi]
            rows = [fact(start, qe, cum[i] * 1e6, "10-Q", filed(qe))
                    for i, qe in enumerate(qs) if qe not in drop_quarters]
            rows.append(fact(start, end, av * 1e6, "10-K", k_filed))
            put(tag, "USD", rows)
        # EPS·가중평균 주식수: 분기 단독 + **누적도 신고된다**(여기에 차분을 걸면 쓰레기가 나온다)
        for tag, unit, years, mul, scale in (
                ("EarningsPerShareDiluted", "USD/shares", _FX_EPS, 1, annual_eps_scale),
                ("WeightedAverageNumberOfDilutedSharesOutstanding", "shares", _FX_SHARES, 1e6,
                 annual_shares_scale)):
            qv, av = years[yi]
            rows = []
            for i, qe in enumerate(qs):
                if qe in drop_quarters:
                    continue
                rows.append(fact(q_start(start, qs, i), qe, qv[i] * mul, "10-Q", filed(qe)))
                if i:      # 누적 값 = 그때까지의 단순 평균(주식수)·합(EPS) 근사
                    cum = sum(qv[:i + 1]) if tag.startswith("Earnings") else sum(qv[:i + 1]) / (i + 1)
                    rows.append(fact(start, qe, round(cum, 2) * mul, "10-Q", filed(qe)))
            rows.append(fact(start, end, av * mul * scale, "10-K", k_filed))
            put(tag, unit, rows)
    for end, v in (direct_q4 or {}).items():
        yr = next(y for y in _FX_YEARS if y[2] == end)
        q4_start = (dt.date.fromisoformat(yr[1][2]) + dt.timedelta(days=1)).isoformat()
        put("Revenues", "USD", [fact(q4_start, end, v * 1e6, "10-K", yr[3])])
    k_ends = {y[2]: y[3] for y in _FX_YEARS}
    put("Assets", "USD", [{"end": e, "val": v * 1e6, "form": "10-K" if e in k_ends else "10-Q",
                           "filed": k_ends.get(e) or filed(e)} for e, v in _FX_ASSETS.items()])
    return {"entityName": "SELFTEST MEMORY CO (MU 신고값 픽스처)", "facts": {"us-gaap": gaap}}


# 미반영 신고 픽스처 — FQ3-26(기말 2026-05-28) 10-Q가 companyfacts에 안 들어온 상태(10/14 CDNS 형태).
_FX_LAG_END, _FX_LAG_FILED, _FX_LAG_ACCN = "2026-05-28", "2026-06-25", "FX-2026-06-25"


def _fixture_lagged() -> dict:
    """companyfacts 픽스처에서 FQ3-26 신고를 뺀 것 + 행마다 접수번호(accn = 'FX-' + 신고일)."""
    f = _fixture_facts(drop_quarters=(_FX_LAG_END,))
    for node in f["facts"]["us-gaap"].values():
        for unit, rows in node["units"].items():
            # 그 신고의 팩트는 전부 빠진다(재무상태표 시점 팩트 포함)
            node["units"][unit] = [dict(r, accn="FX-" + r["filed"]) for r in rows
                                   if r["filed"] != _FX_LAG_FILED]
    return f


def _fixture_sub(extra: list[tuple] = ()) -> dict:
    """submissions 픽스처 — 최근 신고 목록(최신 순). extra = (form, filed, report, accn, isXBRL)."""
    rows = [("8-K", "2026-06-26", "2026-06-25", "FX-8K", 1),
            ("10-Q", _FX_LAG_FILED, _FX_LAG_END, _FX_LAG_ACCN, 1),
            ("10-Q", "2026-03-26", "2026-02-26", "FX-2026-03-26", 1),
            ("10-Q", "2025-12-25", "2025-11-27", "FX-2025-12-25", 1)] + list(extra)
    rows.sort(key=lambda r: r[1], reverse=True)
    keys = ("form", "filingDate", "reportDate", "accessionNumber", "isXBRL")
    return {"filings": {"recent": {k: [r[i] for r in rows] for i, k in enumerate(keys)}}}


def _fixture_instance() -> bytes:
    """그 10-Q의 XBRL 인스턴스(인라인 추출본 모양). MU FQ3-26 신고값 + 버려야 할 것 셋:
    차원(세그먼트) 매출 · 같은 팩트 중복 태깅 · nil 팩트."""
    q = '<period><startDate>2026-02-27</startDate><endDate>2026-05-28</endDate></period>'
    y = '<period><startDate>2025-08-29</startDate><endDate>2026-05-28</endDate></period>'
    i = '<period><instant>2026-05-28</instant></period>'
    ent = '<entity><identifier scheme="http://www.sec.gov/CIK">0000000000</identifier>{}</entity>'
    seg = ('<segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">'
           'x:HbmMember</xbrldi:explicitMember></segment>')
    ctx = "".join(f'<context id="{cid}">{ent.format(s)}{p}</context>'
                  for cid, s, p in (("cq", "", q), ("cy", "", y), ("ci", "", i), ("cd", seg, q)))
    units = ('<unit id="usd"><measure>iso4217:USD</measure></unit>'
             '<unit id="shares"><measure>shares</measure></unit>'
             '<unit id="usdPerShare"><divide><unitNumerator><measure>iso4217:USD</measure></unitNumerator>'
             '<unitDenominator><measure>shares</measure></unitDenominator></divide></unit>')
    # 차원 팩트를 **맨 앞에** 둔다 — 뒤에 두면 중복 제거가 차원 필터의 결함을 가린다(같은 기간·태그)
    facts = [("Revenues", "cd", "usd", "99999000000"),
             ("Revenues", "cq", "usd", "41456000000"), ("Revenues", "cq", "usd", "41456000000"),
             ("Revenues", "cy", "usd", "78959000000"),
             ("GrossProfit", "cq", "usd", "35056000000"), ("OperatingIncomeLoss", "cq", "usd", "33318000000"),
             ("NetIncomeLoss", "cq", "usd", "28243000000"),
             ("NetCashProvidedByUsedInOperatingActivities", "cy", "usd", "45702000000"),
             ("PaymentsToAcquirePropertyPlantAndEquipment", "cy", "usd", "19602000000"),
             ("EarningsPerShareDiluted", "cq", "usdPerShare", "24.67"),
             ("WeightedAverageNumberOfDilutedSharesOutstanding", "cq", "shares", "1145000000"),
             ("Assets", "ci", "usd", "121340000000")]
    body = "".join(f'<us-gaap:{t} contextRef="{c}" unitRef="{u}" decimals="-6">{v}</us-gaap:{t}>'
                   for t, c, u, v in facts)
    body += '<us-gaap:InventoryNet contextRef="ci" unitRef="usd" xsi:nil="true"/>'
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://fasb.org/us-gaap/2025" '
            'xmlns:iso4217="http://www.xbrl.org/2003/iso4217" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
            'xmlns:srt="http://fasb.org/srt/2025" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'{ctx}{units}{body}</xbrl>').encode()


def selftest() -> int:
    """4분기 역산이 **맞는 값을 만들고, 만들면 안 될 때 안 만드는지** 본다(오프라인).

    가드 제작 3단계(dev_workflow §1b): 위반을 심어 잡히는지 · 정상 데이터에 오탐이 없는지 ·
    그 확인을 guard_selftest에 등록. 정답은 실제 사례(MU 8-K GAAP 표)를 쓴다.
    """
    print("edgar_facts 자가검증 — 회계 4분기 역산 · 누적 차분 · EPS 근사")
    print("=" * 78)
    ok = True

    def check(cond: bool, label: str, detail: str = "") -> None:
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  {'✅' if cond else '❌'} {label}" + (f" — {detail}" if detail and not cond else ""))

    def rows(**kw) -> dict[str, dict]:
        return {r["end"]: r for r in normalize("TEST", _fixture_facts(**kw))["quarterly"]}

    q = rows()
    m = lambda r, k: None if r.get(k) is None else round(r[k] / 1e6)   # noqa: E731

    # ① 정답 대조 — 8-K GAAP 표
    r26, r25 = q.get("2026-09-03") or {}, q.get("2025-08-28") or {}
    check((m(r26, "revenue"), m(r26, "gross_profit"), m(r26, "operating_income")) == (54229, 47047, 43751),
          "FQ4-26 역산 = 8-K 표(매출 54,229 · 매출총이익 47,047 · 영업이익 43,751)",
          f"{m(r26, 'revenue')}, {m(r26, 'gross_profit')}, {m(r26, 'operating_income')}")
    check((m(r25, "revenue"), m(r25, "operating_income"), m(r25, "net_income")) == (11315, 3654, 3201),
          "FQ4-25 역산 = 8-K 표(매출 11,315 · 영업이익 3,654 · 순이익 3,201)",
          f"{m(r25, 'revenue')}, {m(r25, 'operating_income')}, {m(r25, 'net_income')}")
    check(r26.get("q4_derived") is True and r25.get("q4_derived") is True
          and not q["2026-05-28"].get("q4_derived"),
          "역산한 분기에만 q4_derived 표시(직접 신고 분기엔 없다)")
    check(any(d.startswith("q4=annual-(q1+q2+q3)") for d in r26.get("_derived", [])),
          "역산한 계정 목록이 _derived에 남는다", str(r26.get("_derived")))

    # ② 연속성 — 4분기가 채워져 최근 8개 분기말이 전부 한 분기 간격
    ends = sorted(q, reverse=True)[:8]
    gaps = [(dt.date.fromisoformat(a) - dt.date.fromisoformat(b)).days for a, b in zip(ends, ends[1:])]
    check(all(QTR_GAP[0] <= g <= QTR_GAP[1] for g in gaps), "최근 8개 분기말이 연속", str(gaps))

    # ③ 현금흐름 — 누적 차분으로 2·3분기, 역산으로 4분기
    check(m(q["2026-02-26"], "cfo") == 11903 and m(q["2026-05-28"], "cfo") == 25388,
          "CFO 2·3분기 = 누적 차분(6개월 − 3개월 · 9개월 − 6개월)",
          f"{m(q['2026-02-26'], 'cfo')}, {m(q['2026-05-28'], 'cfo')}")
    check(m(r26, "cfo") == 43973 and m(r26, "capex") == 11110 and m(r26, "fcf") == 43973 - 11110,
          "CFO·capex·FCF 4분기 = 연간 − 1~3분기", f"{m(r26, 'cfo')}, {m(r26, 'capex')}, {m(r26, 'fcf')}")

    # ④ EPS·주식수 — 가산이 안 된다. 누적 차분을 걸지 않고, 4분기는 근사 + 표기
    check(q["2026-02-26"].get("shares_diluted") == 1142e6 and q["2026-02-26"].get("eps_diluted") == 12.07,
          "EPS·주식수 2분기 = 직접 신고값 그대로(누적 차분 미적용)",
          f"{q['2026-02-26'].get('shares_diluted')}, {q['2026-02-26'].get('eps_diluted')}")
    check(r25.get("eps_diluted") == 2.83 and abs((r25.get("shares_diluted") or 0) / 1130e6 - 1) < 0.01,
          "FQ4-25 EPS 근사 = 실제 발표 2.83 · 주식수 ≈ 11.3억", f"{r25.get('eps_diluted')}, {r25.get('shares_diluted')}")
    check(any("eps_diluted≈" in d for d in r25.get("_derived", [])), "EPS가 근사값이라는 표기")
    check(m(r26, "assets") == 158000, "재무상태표는 10-K 기말 값 그대로", str(m(r26, "assets")))

    # ⑤ 위반 주입 — 분기가 하나 빠진 회계연도는 역산하지 않는다
    #    ('연간 − 있는 분기들'을 하면 두 분기 값(5,824 + 7,750)이 4분기로 둔갑한다)
    q_drop = rows(drop_quarters=("2024-02-29",))
    check("2024-08-29" not in q_drop and "2025-08-28" in q_drop,
          "1~3분기 중 하나가 빠지면 그 해 4분기는 만들지 않는다(다른 해는 그대로)",
          f"2024-08-29 매출 {m(q_drop.get('2024-08-29') or {}, 'revenue')}")

    # ⑥ 위반 주입 — 연간 EPS·주식수만 다른 스케일(분할 재보고가 한쪽만 온 상태)이면 결측
    r_eps = rows(annual_eps_scale=0.1).get("2025-08-28") or {}
    check(r_eps.get("eps_diluted") is None and any("eps_diluted=결측" in d for d in r_eps.get("_derived", []))
          and m(r_eps, "revenue") == 11315,
          "두 EPS 근사가 어긋나면 EPS만 결측 + 사유 표기(매출은 그대로)", str(r_eps.get("eps_diluted")))
    r_sh = rows(annual_shares_scale=10).get("2025-08-28") or {}
    check(r_sh.get("shares_diluted") is None and r_sh.get("eps_diluted") is None,
          "역산 주식수가 연간 평균과 15% 넘게 벌어지면 주식수·EPS 결측",
          f"{r_sh.get('shares_diluted')}, {r_sh.get('eps_diluted')}")

    # ⑦ 직접 신고된 4분기는 덮어쓰지 않는다
    r_dir = rows(direct_q4={"2025-08-28": 11000}).get("2025-08-28") or {}
    check(m(r_dir, "revenue") == 11000 and not r_dir.get("q4_derived"),
          "4분기 단독 신고값이 있으면 그 값을 쓴다(역산 표시 없음)", str(m(r_dir, "revenue")))

    # ⑧ companyfacts 미반영 신고(10/14 CDNS) — 신고 원본 XBRL로 메우면 역산·누적 차분까지 복원된다
    today = dt.date(2026, 10, 14)
    lag = _fixture_lagged()
    q_lag = {r["end"]: r for r in normalize("TEST", lag)["quarterly"]}
    check(_FX_LAG_END not in q_lag and "2026-09-03" not in q_lag,
          "함정 확인: 미반영 상태 = FQ3-26이 없고, 그 때문에 FQ4-26 역산도 못 한다",
          "미반영 픽스처가 이미 그 분기를 갖고 있으면 아래 검사는 아무것도 증명하지 못한다")
    miss = missing_filings(lag, _fixture_sub(), today)
    check([x["accn"] for x in miss] == [_FX_LAG_ACCN],
          "미반영 신고만 찾는다(8-K·이미 반영된 10-Q 제외)", str(miss))
    old = _fixture_sub([("10-Q", "2025-03-01", "2025-01-30", "FX-OLD", 1),
                        ("10-Q", "2026-06-20", "2026-05-01", "FX-NOXBRL", 0)])
    check([x["accn"] for x in missing_filings(lag, old, today)] == [_FX_LAG_ACCN],
          f"{SUPPLEMENT_LOOKBACK}일보다 오래된 신고·XBRL 없는 신고는 보충 대상이 아니다")
    sup = supplement(lag, _fixture_sub(), lambda meta: _fixture_instance(), today)
    rec = normalize("TEST", lag)
    q_sup = {r["end"]: r for r in rec["quarterly"]}
    r3, r4 = q_sup.get(_FX_LAG_END) or {}, q_sup.get("2026-09-03") or {}
    check([a["accn"] for a in sup["added"]] == [_FX_LAG_ACCN] and not sup["missing"]
          and "신고 원본 XBRL 1건" in rec["source"] and rec.get("edgar_supplement"),
          "보충 결과가 레코드에 남는다(source · edgar_supplement)", f"{sup} / {rec['source']}")
    check((m(r3, "revenue"), m(r3, "operating_income"), m(r3, "assets")) == (41456, 33318, 121340)
          and r3.get("eps_diluted") == 24.67 and sup["added"][0]["facts"] == 10
          # EPS 단위가 companyfacts와 같은 'USD/shares'여야 기존 분기 EPS와 한 시계열이 된다
          and q_sup["2026-02-26"].get("eps_diluted") == 12.07,
          "보충 분기 = 신고값(차원 매출 99,999·중복 태깅·nil은 버린다)",
          f"{m(r3, 'revenue')}, {m(r3, 'operating_income')}, {m(r3, 'assets')}, {r3.get('eps_diluted')}")
    check(m(r3, "cfo") == 25388 and m(r3, "capex") == 7826,
          "보충 분기 CFO·capex = 누적(9개월) − 6개월(companyfacts 쪽 값과 차분)",
          f"{m(r3, 'cfo')}, {m(r3, 'capex')}")
    check(m(r4, "revenue") == 54229 and r4.get("q4_derived") is True,
          "보충으로 세 분기가 갖춰져 FQ4-26 역산이 되살아난다(8-K 표 54,229)", str(m(r4, "revenue")))
    check(any(d.startswith("신고 원본 XBRL 보충") for d in r3.get("_derived", []))
          and not any("신고 원본" in d for d in (q_sup["2026-02-26"].get("_derived") or [])),
          "보충한 기간의 행에만 출처 표기", str(r3.get("_derived")))
    # 못 메우면 사유가 남는다(조용히 낡지 않게) — 그 사유를 financials가 margin_trend_gap으로 낸다
    lag2 = _fixture_lagged()

    def boom(meta):
        raise urllib.error.URLError("503")
    sup2 = supplement(lag2, _fixture_sub(), boom, today)
    rec2 = normalize("TEST", lag2)
    check(not sup2["added"] and [x["accn"] for x in rec2.get("edgar_missing") or []] == [_FX_LAG_ACCN]
          and "URLError" in rec2["edgar_missing"][0]["why"] and _FX_LAG_END not in
          {r["end"] for r in rec2["quarterly"]},
          "보충 실패 → edgar_missing에 신고·사유가 남고 분기는 비어 있다", str(rec2.get("edgar_missing")))
    check("edgar_supplement" not in normalize("TEST", _fixture_facts()),
          "미반영 신고가 없는 종목엔 보충 키가 생기지 않는다")

    print("-" * 78)
    print("✅ 통과 — 역산이 맞고, 만들면 안 될 때 안 만든다" if ok else "❌ 실패")
    return 0 if ok else 1


# ─────────────────────────────────────────── CLI

def _fmt(v, unit=1e6):
    if v is None:
        return "—"
    return f"{v/unit:,.0f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="SEC EDGAR 재무제표 3표 수집")
    ap.add_argument("--tickers", help="쉼표·공백 구분 (기본: 미국 보유 전 종목)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--save", action="store_true", help="data/financials/ 에 캐시")
    ap.add_argument("--quarters", type=int, default=8)
    ap.add_argument("--selftest", action="store_true",
                    help="오프라인 자가검증 — 회계 4분기 역산·누적 차분·EPS 근사(네트워크 없음)")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    tickers =[t.strip().upper() for t in cli_common.split_tickers(a.tickers)] if a.tickers else US_HOLDINGS
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
