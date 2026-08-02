#!/usr/bin/env python3
"""dart_facts.py — 국내 보유종목 재무제표 3표 (DART OpenAPI, 1차 출처·stdlib)

정훈 지시(2026-07-29). 국내 5종목의 **1차 출처** — 금융감독원 전자공시(DART)에 회사가 직접
신고한 재무제표다. Yahoo(yahoo_facts.py)가 무키 백본으로 이미 3표를 채우지만 Yahoo는 2차
가공이고 **최대 4~5기**만 준다. DART는 1차 신고 원문 + 장기 시계열을 준다.

역할: KR 재무의 **감사·검증 축**. yahoo_facts와 계정이 1% 넘게 갈리면 DART를 채택하고
`source_conflict` 플래그로 병기한다(CLAUDE.md "단일 출처 의심 수치는 항상 교차검증").
실제로 Yahoo에서 NAVER 2025-06-30 영업이익이 매출과 동일하게 오는 매핑 오류를 확인했다 —
1차 출처 대조가 없으면 이런 게 그대로 마진 추세 판정에 들어간다.

키: 환경변수 `DART_API_KEY` (**조회 전용**). 토스 키와 동일 취급 —
    **파일에 저장 금지·커밋 금지.** 키가 없으면 조용히 비활성(Yahoo 백본으로 충분히 돌아감).

엔드포인트:
  · fnlttSinglAcntAll.json  — 단일회사 전체 재무제표(재무상태표·손익계산서·현금흐름표 전 계정)
      reprt_code 11013(1분기)·11012(반기)·11014(3분기)·11011(사업보고서)
      fs_div CFS(연결) 우선, 없으면 OFS(별도)
  · corpCode.xml(zip)       — 종목코드 → corp_code 매핑(1회 받아 캐시)

⚠️ 분기 환산 규칙은 **재무제표 종류마다 다르다**(FLOW_IS/FLOW_CF 주석에 실측 근거).
   손익=3개월 단독 / 현금흐름=연누적 / 재무상태표=시점잔액. 하나로 뭉뚱그리면 분기 매출이
   음수로 나온다. [7/29 검증] 삼성 2025 4개 분기 전부 Yahoo와 일치 확인.

사용:
  DART_API_KEY=xxx python3 dart_facts.py                  # 국내 보유 5
  DART_API_KEY=xxx python3 dart_facts.py --code 005930
  DART_API_KEY=xxx python3 dart_facts.py --years 2023,2024,2025 --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CACHE_DIR = os.path.join(ROOT, "data", "financials")
CORP_CACHE = os.path.join(CACHE_DIR, "_dart_corp.json")

BASE = "https://opendart.fss.or.kr/api"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# 국내 보유 5 — Yahoo 티커와 상호 변환
KR = {"005930": "삼성전자", "066570": "LG전자", "454910": "두산로보틱스",
      "005380": "현대차", "035420": "NAVER"}
# 보유 국내 5종목은 **전부 코스피(.KS)** — 두산로보틱스(454910)도 2023년 코스피 상장이다.
# [7/30 실측] 454910.KS=Doosan Robotics(KSE) / 454910.KQ=코스닥의 다른 종목(83,900원).
# 여기 "두산로보틱스만 코스닥" 오기가 financials/yahoo_facts로 번져 재무제표에 남의 회사가 들어갔다.
YAHOO_SUFFIX = {}   # 예외 없음 — 접미사가 다르면 다른 회사다

# 보고서 코드 → (분기순번, 누적개월)
REPORTS = [("11013", 1, 3), ("11012", 2, 6), ("11014", 3, 9), ("11011", 4, 12)]

# DART 계정ID(account_id) → 우리 단일 스키마. 표준계정 우선, 없으면 계정명으로 폴백.
IDS = {
    "revenue": ["ifrs-full_Revenue", "ifrs-full_RevenueFromSaleOfGoods"],
    "gross_profit": ["ifrs-full_GrossProfit"],
    "operating_income": ["dart_OperatingIncomeLoss", "ifrs-full_ProfitLossFromOperatingActivities"],
    # ⚠️ 순이익은 **지배주주 귀속** 우선. `ifrs-full_ProfitLoss`는 비지배지분을 포함한 총
    # 순이익이라 ROE·EPS·순마진이 부풀려진다. [7/29 실측] 삼성 2025 총 452,068억 vs
    # 지배주주 442,610억(Yahoo와 일치) — 2.1% 차이가 그대로 지표에 실린다.
    "net_income": ["ifrs-full_ProfitLossAttributableToOwnersOfParent", "ifrs-full_ProfitLoss"],
    "net_income_total": ["ifrs-full_ProfitLoss"],
    "assets": ["ifrs-full_Assets"],
    "liabilities": ["ifrs-full_Liabilities"],
    "equity": ["ifrs-full_Equity"],
    "assets_current": ["ifrs-full_CurrentAssets"],
    "liabilities_current": ["ifrs-full_CurrentLiabilities"],
    "inventory": ["ifrs-full_Inventories"],
    "cash": ["ifrs-full_CashAndCashEquivalents"],
    "receivables": ["dart_ShortTermTradeReceivable", "ifrs-full_TradeAndOtherCurrentReceivables"],
    "cfo": ["ifrs-full_CashFlowsFromUsedInOperatingActivities"],
}
NAMES = {   # account_id가 '-표준계정코드 미사용-'인 회사 대비 계정명 폴백
    "revenue": ["수익(매출액)", "매출액", "영업수익"],
    "gross_profit": ["매출총이익"],
    "operating_income": ["영업이익", "영업이익(손실)"],
    "net_income": ["지배기업의 소유주에게 귀속되는 당기순이익",
                   "지배기업 소유주지분", "당기순이익", "당기순이익(손실)"],
    "net_income_total": ["당기순이익", "당기순이익(손실)"],
    "assets": ["자산총계"], "liabilities": ["부채총계"], "equity": ["자본총계"],
    "assets_current": ["유동자산"], "liabilities_current": ["유동부채"],
    "inventory": ["재고자산"], "cash": ["현금및현금성자산"],
    "receivables": ["매출채권", "매출채권 및 기타유동채권"],
    "cfo": ["영업활동현금흐름", "영업활동으로인한현금흐름"],
    "capex": ["유형자산의 취득", "유형자산의취득"],
}


def _key() -> str | None:
    return os.environ.get("DART_API_KEY", "").strip() or None


def _get(path: str, params: dict, tries: int = 3) -> dict:
    """⚠️ 재시도 필수 — 일시적 예외 1번에 CFS(연결)를 포기하고 OFS(별도)로 떨어지면
    한 시계열에 연결·별도가 섞인다. [7/29 실측] 삼성 2025 Q1이 이 경로로 별도(555,349억)를
    물어와 Yahoo(연결 791,405억)와 30% 어긋났다. 기준이 섞인 시계열은 마진·성장률을 전부 오염시킨다.
    """
    url = f"{BASE}/{path}?{urllib.parse.urlencode({**params, 'crtfc_key': _key()})}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last  # type: ignore[misc]


CORP_CACHE_V = 2   # v1 = 보유 5종목만 담던 구버전(자동 폐기)


def _fetch_corp_zip(timeout: float = 300.0, tries: int = 3) -> bytes:
    """corpCode.xml zip(약 20MB) 수신. 데이터센터 회선에서 3분 걸린 실측이 있어
    타임아웃을 넉넉히 잡고 재시도한다(구 60초는 정상 회선에서도 자주 끊겼다)."""
    url = f"{BASE}/corpCode.xml?crtfc_key={_key()}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(2.0 * (i + 1))
    raise last  # type: ignore[misc]


def _corp_cache() -> dict:
    """{'_v':2,'_updated':…,'codes':{6자리:corp_code},'names':{6자리:한글명}}"""
    if os.path.exists(CORP_CACHE):
        try:
            with open(CORP_CACHE, encoding="utf-8") as f:
                d = json.load(f)
            # v1은 flat dict({코드:corp_code})이고 보유 5종목만 들어 있다.
            # 파일이 '존재'하므로 구버전 로직은 임의 종목에서 영구 미스가 났다 → 폐기 후 재수신.
            if isinstance(d, dict) and d.get("_v") == CORP_CACHE_V:
                return d
        except Exception:
            pass
    return {}


def corp_codes(refresh: bool = False) -> dict[str, str]:
    """종목코드(6자리) → corp_code(8자리). **상장사 전체**를 1회 받아 캐시한다.

    ⚠️ [8/2 설계 결함 수정] 구버전은 20MB zip을 통째로 받아놓고 `stock in KR`로
    보유 5종목만 남긴 뒤 저장했다. 그래서 ①보유 외 종목은 항상 미스인데 ②캐시 파일은
    존재하므로 재수신도 안 되고 ③강제 refresh하면 20MB를 다시 받아 또 5개만 남겼다.
    오디텍(080520) 조회 때 corpCode.xml 수신이 2분 타임아웃으로 죽은 근본원인.
    상장사 전체를 담아도 파일은 수백 KB 수준이라 '파일 비대' 우려는 근거가 없었다.
    """
    if not refresh:
        c = _corp_cache()
        if c.get("codes"):
            return c["codes"]

    with zipfile.ZipFile(io.BytesIO(_fetch_corp_zip())) as z:
        xml = z.read(z.namelist()[0]).decode("utf-8")
    import xml.etree.ElementTree as ET
    codes: dict[str, str] = {}
    names: dict[str, str] = {}
    for el in ET.fromstring(xml).iter("list"):
        stock = (el.findtext("stock_code") or "").strip()
        if not stock or stock == "-":      # 비상장은 제외(종목코드 없음)
            continue
        codes[stock] = (el.findtext("corp_code") or "").strip()
        names[stock] = (el.findtext("corp_name") or "").strip()
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CORP_CACHE, "w", encoding="utf-8") as f:
        json.dump({"_v": CORP_CACHE_V, "_updated": dt.date.today().isoformat(),
                   "codes": codes, "names": names}, f, ensure_ascii=False)
    return codes


def corp_names(refresh: bool = False) -> dict[str, str]:
    """종목코드(6자리) → 회사 한글명. corp_codes()와 같은 1회 수신분을 공유한다."""
    c = _corp_cache()
    if refresh or not c.get("names"):
        corp_codes(refresh=True)
        c = _corp_cache()
    return c.get("names", {})


def resolve(ticker: str) -> tuple[str, str | None, str | None]:
    """'080520.KQ' | '080520' → (6자리코드, corp_code, 회사명). 미상장/미해결이면 None."""
    code = str(ticker).split(".")[0].strip()
    return code, corp_codes().get(code), corp_names().get(code)


def _num(s) -> float | None:
    if s in (None, "", "-"):
        return None
    try:
        return float(str(s).replace(",", "").replace(" ", ""))
    except ValueError:
        return None


def _extract(rows: list[dict]) -> dict[str, dict]:
    """전체 계정 리스트 → {field: {'amt':값, 'cum':누적, 'sj':재무제표구분}} 한 보고서분."""
    by_id: dict[str, dict] = {}
    by_nm: dict[str, dict] = {}
    for r in rows:
        aid = (r.get("account_id") or "").strip()
        nm = (r.get("account_nm") or "").strip()
        if aid and aid not in by_id:
            by_id[aid] = r
        if nm and nm not in by_nm:
            by_nm[nm] = r
    out: dict[str, dict] = {}
    for field in set(list(IDS) + list(NAMES)):
        row = None
        for aid in IDS.get(field, []):
            if aid in by_id:
                row = by_id[aid]
                break
        if row is None:
            for nm in NAMES.get(field, []):
                if nm in by_nm:
                    row = by_nm[nm]
                    break
        out[field] = {"amt": _num(row.get("thstrm_amount")) if row else None,
                      "cum": _num(row.get("thstrm_add_amount")) if row else None,
                      "sj": (row or {}).get("sj_div")}
    return out


def fetch_year(corp: str, year: int) -> dict[int, dict]:
    """한 사업연도의 1~4분기 **누적** 스냅샷 {분기순번: 계정dict}."""
    got: dict[int, dict] = {}
    for code, qn, _months in REPORTS:
        for fs in ("CFS", "OFS"):
            try:
                d = _get("fnlttSinglAcntAll.json",
                         {"corp_code": corp, "bsns_year": str(year),
                          "reprt_code": code, "fs_div": fs})
            except Exception:
                continue
            if d.get("status") != "000" or not d.get("list"):
                continue
            got[qn] = _extract(d["list"])
            got[qn]["_fs_div"] = {"amt": None, "cum": None, "sj": fs}
            break
        time.sleep(0.12)
    return got


# ⚠️ [7/29 실측] DART는 **재무제표 종류마다 기간 규칙이 다르다**. 이걸 하나로 뭉뜽그리면
#    분기 매출이 음수로 나온다(초기 구현에서 삼성 2025-06-30 매출 -45,742억 발생).
#      · 손익계산서(IS/CIS) : thstrm_amount = **당 3개월 단독**, thstrm_add_amount = 누적
#            (삼성 2025 반기보고서 745,663억 = Yahoo 2분기와 일치 → 차분 불필요)
#      · 현금흐름표(CF)     : thstrm_amount = **회계연도 누적**, add 없음
#            (3분기 565,155억 = Q1+Q2+Q3 정확히 일치 → 차분 필요)
#      · 재무상태표(BS)     : 시점 잔액 — 그대로 사용
FLOW_IS = {"revenue", "gross_profit", "operating_income", "net_income", "net_income_total"}
FLOW_CF = {"cfo", "capex"}
FLOW = FLOW_IS | FLOW_CF
STOCK = {"assets", "liabilities", "equity", "assets_current", "liabilities_current",
         "inventory", "cash", "receivables"}


def fetch(ticker: str, years: list[int] | None = None) -> dict:
    """Yahoo 티커(005930.KS) 또는 6자리 코드 → 단일 스키마 레코드."""
    if not _key():
        return {"ticker": ticker, "_error": "DART_API_KEY 없음"}
    # [8/2] 구버전은 보유 5종목(KR) 밖이면 즉시 거부했다 — 신규 종목 조사(오디텍 등)에서
    # DART 1차 출처 경로가 통째로 막힌다. 상장사면 누구든 조회 가능하게 풀되,
    # 이름은 보유 유니버스 → DART 공식명 순으로 해석한다.
    code, corp, dart_name = resolve(ticker)
    if not corp:
        return {"ticker": ticker,
                "_error": f"corp_code 매핑 실패({code}) — 비상장이거나 종목코드 오기"}
    # ⚠️ DART는 KOSPI/KOSDAQ 구분을 안 준다 → 접미사를 추측하면 남의 회사가 된다(7/30 사고).
    #    호출자가 준 접미사를 그대로 보존하고, 없으면 보유 유니버스에서만 채운다.
    given_sfx = ("." + ticker.split(".", 1)[1]) if "." in str(ticker) else None
    sfx = given_sfx or YAHOO_SUFFIX.get(code) or (".KS" if code in KR else "")

    this_year = dt.date.today().year
    years = years or list(range(this_year - 3, this_year + 1))

    annual: list[dict] = []
    quarterly: list[dict] = []
    for y in sorted(years):
        snaps = fetch_year(corp, y)
        if not snaps:
            continue
        # 연간 = 사업보고서(11011)의 당기 금액
        if 4 in snaps:
            av = {f: v.get("amt") for f, v in snaps[4].items()}
            av["_fs_div"] = snaps[4].get("_fs_div", {}).get("sj")
            annual.append(_row(f"{y}-12-31", "annual", av))
        # 분기 — 재무제표 종류별 규칙(위 주석) 적용
        ENDS = {1: f"{y}-03-31", 2: f"{y}-06-30", 3: f"{y}-09-30", 4: f"{y}-12-31"}
        prev_cf: dict[str, float] = {}
        for qn in (1, 2, 3):
            cur = snaps.get(qn)
            if not cur:
                continue
            vals: dict[str, float | None] = {}
            vals["_fs_div"] = cur.get("_fs_div", {}).get("sj")
            for f in STOCK | FLOW_IS:
                vals[f] = cur.get(f, {}).get("amt")        # IS는 이미 3개월 단독
            for f in FLOW_CF:                              # CF는 누적 → 직전 분기 차감
                c = cur.get(f, {}).get("amt")
                vals[f] = None if c is None else c - prev_cf.get(f, 0.0)
                if c is not None:
                    prev_cf[f] = c
            quarterly.append(_row(ENDS[qn], "quarterly", vals))
        # 4분기 = 연간 − 3분기 누적 (사업보고서엔 4분기 단독 수치가 없다)
        if 4 in snaps:
            q3 = snaps.get(3) or {}
            vals = {"_fs_div": snaps[4].get("_fs_div", {}).get("sj")}
            for f in STOCK:
                vals[f] = snaps[4].get(f, {}).get("amt")   # 기말 잔액
            for f in FLOW_IS:
                yr = snaps[4].get(f, {}).get("amt")
                c3 = q3.get(f, {}).get("cum")              # IS 누적은 add 컬럼
                vals[f] = (yr - c3) if (yr is not None and c3 is not None) else None
            for f in FLOW_CF:
                yr = snaps[4].get(f, {}).get("amt")
                c3 = q3.get(f, {}).get("amt")              # CF는 amt 자체가 누적
                vals[f] = (yr - c3) if (yr is not None and c3 is not None) else None
            quarterly.append(_row(ENDS[4], "quarterly", vals))

    return {
        "ticker": code + sfx,
        "name": KR.get(code) or dart_name or code,
        "region": "KR",
        "currency": "KRW",
        "source": "DART OpenAPI fnlttSinglAcntAll (1차 출처)",
        "depth": "full",
        "as_of": dt.date.today().isoformat(),
        "annual": sorted(annual, key=lambda r: r["end"], reverse=True),
        "quarterly": sorted(quarterly, key=lambda r: r["end"], reverse=True),
    }


def _row(end: str, period: str, vals: dict) -> dict:
    r = {"end": end, "period": period, "_fs_div": vals.get("_fs_div")}
    for f in FLOW | STOCK:
        r[f] = vals.get(f)
    r["total_debt"] = None          # DART 표준계정에 총차입금 단일항목 없음(미확인으로 남긴다)
    r["eps_diluted"] = None
    r["shares_diluted"] = None
    r["deferred_revenue"] = None
    cfo, capex = r.get("cfo"), r.get("capex")
    r["fcf"] = (cfo - abs(capex)) if (cfo is not None and capex is not None) else None
    r["_derived"] = []
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="DART 국내 재무제표 3표 (1차 출처)")
    ap.add_argument("--code", "--tickers", help="6자리 종목코드 또는 야후 티커")
    ap.add_argument("--years", help="쉼표·공백 구분 사업연도 (기본: 최근 4개년)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not _key():
        print("❌ DART_API_KEY 없음 — 환경변수로 지정하세요(파일 저장 금지).")
        print("   키 없이도 yahoo_facts.py가 국내 3표를 채웁니다(무키 백본).")
        return 1

    years = [int(y) for y in a.years.split(",")] if a.years else None
    targets = [a.code] if a.code else list(KR)
    out = [fetch(t, years) for t in targets]

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0

    for r in out:
        if r.get("_error"):
            print(f"\n❌ {r['ticker']}: {r['_error']}")
            continue
        print(f"\n═══ {r['name']} ({r['ticker']}) — 연간 {len(r['annual'])}기 · "
              f"분기 {len(r['quarterly'])}기  [{r['source']}]")
        print("  [연간 억원] 기간말        매출     영업이익     순이익     자산총계"
              "    부채총계     재고      영업CF")
        for w in r["annual"][:4]:
            g = lambda k: "—" if w.get(k) is None else f"{w[k]/1e8:,.0f}"  # noqa: E731
            print(f"             {w['end']} {g('revenue'):>11} {g('operating_income'):>10}"
                  f" {g('net_income'):>10} {g('assets'):>12} {g('liabilities'):>11}"
                  f" {g('inventory'):>9} {g('cfo'):>11}")
        print("  [분기 억원] 기간말        매출     영업이익     순이익")
        for w in r["quarterly"][:4]:
            g = lambda k: "—" if w.get(k) is None else f"{w[k]/1e8:,.0f}"  # noqa: E731
            print(f"             {w['end']} {g('revenue'):>11} {g('operating_income'):>10}"
                  f" {g('net_income'):>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
