#!/usr/bin/env python3
"""dart_disclosure.py — DART 수시공시 감시 (국내 보유·워치) · stdlib only

정훈 지시(2026-07-30 "다 하자"). `docs/data_coverage.md` §3 **미보유 레이어 우선순위 1번**.

■ 왜 이게 없으면 안 되는가
   리스크룰 2는 *"LG전자 — 단기 손절선 영구 폐기. **펀더멘털 훼손 시에만** 매도 검토"*다.
   그런데 우리에겐 **훼손을 감지할 장치가 없었다.** 유상증자·대규모 공급계약 해지·소송·
   최대주주 지분변동·감사의견이 전부 사각지대였고, 리스크 데스크는 룰만 들고 근거 없이
   "훼손 없음"을 말해 왔다. 이 스크립트가 그 근거를 만든다.

■ 설계 원칙 — **분류가 본체다**
   삼성전자 한 종목만 한 달 784건이 쏟아진다(7/30 실측). 원문을 그대로 흘리면 노이즈에
   묻혀 아무도 안 본다. 그래서 이 스크립트의 핵심은 수집이 아니라 **중대성 3단 분류**다:
     🚨 critical  = 정훈 룰에 직접 걸리는 것(훼손·희석·지배구조)
     ⚠️  notable  = 판단에 영향(대형계약·자사주·대량보유·내부자매매·실적)
     ·  routine   = 정기·형식 공시(특수관계인 거래 등) — 기본 숨김

■ 경보 전용 (측정 규율 준수)
   `vol_gauge`·`naver_sentiment`와 같은 규율 — **매수·매도 자동발동 아님.**
   훼손 '후보'를 PM·리스크 데스크에 올릴 뿐, 룰(안전핀·트랜치·별점)은 바꾸지 않는다.

키 = 환경변수 `DART_API_KEY` (조회 전용·저장 금지). 일 20,000콜.

사용:
  python3 dart_disclosure.py                    # 보유 5종목 최근 7일 중대공시
  python3 dart_disclosure.py --days 30 --all    # routine 포함 전체
  python3 dart_disclosure.py --watch            # 워치 종목까지
  python3 dart_disclosure.py --insider          # 내부자 보유증감 합산(elestock)
  python3 dart_disclosure.py --major            # 5% 대량보유 변동(국민연금 등·majorstock)
  python3 dart_disclosure.py --save             # data/app/disclosures.json 갱신
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "data", "app", "disclosures.json")
BASE = "https://opendart.fss.or.kr/api"
VIEW = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="

# 보유 국내 5 + 워치. 6자리 종목코드 → 표시명
HOLD = {"005930": "삼성전자", "066570": "LG전자", "454910": "두산로보틱스",
        "005380": "현대차", "035420": "NAVER"}
WATCH = {"000660": "SK하이닉스", "240810": "원익IPS", "095610": "테스",
         "009150": "삼성전기", "034020": "두산에너빌리티", "096770": "SK이노베이션",
         "012450": "한화에어로스페이스", "042660": "한화오션", "010140": "삼성중공업",
         "329180": "HD현대중공업"}

# ─────────────────────────────────────────── 중대성 분류
#
# (정규식, 등급, 카테고리, 왜 중요한가 — 정훈 룰과의 연결)
# 순서가 곧 우선순위: 위에서 처음 걸리는 규칙이 그 공시의 등급이 된다.
RULES = [
    # 🚨 생존·훼손 — 리스크룰 2의 '펀더멘털 훼손' 본체
    (r"감사보고서.*(거절|한정|부적정)|의견거절",      "critical", "감사의견", "감사의견 훼손 = 최상위 경보"),
    (r"회생절차|파산|부도|영업정지|상장폐지|관리종목",   "critical", "생존",     "존속 리스크"),
    (r"소송|가처분|형사|과징금|제재|시정명령|담합",      "critical", "법적분쟁", "훼손 판정 입력"),
    (r"손상차손|대손충당금.*설정|자산재평가.*손실",      "critical", "손상",     "자산 가치 훼손"),
    # ⚠️ 자기주식취득**신탁**계약 해지는 자사주 프로그램 종료이지 수주 취소가 아니다.
    #    (7/30 실측 오탐: LG전자 "자기주식취득신탁계약해지결정"이 🚨계약해지로 잡혔다.)
    (r"신탁계약.*(해지|체결)",                          "notable",  "자사주",   "자사주 신탁 프로그램 변경"),
    (r"(공급|판매|납품|수주)계약.*(해지|해제|취소)|수주.*(취소|중단)", "critical", "계약해지", "수주 논지 붕괴 신호"),
    # 🚨 희석 — 주주가치 직접 훼손
    (r"유상증자|전환사채|신주인수권부사채|교환사채|무상감자", "critical", "희석",  "주주가치 희석"),
    (r"합병|분할|주식교환|영업양수도|포괄적",            "critical", "지배구조", "구조 변경"),
    (r"최대주주.*변경",                                "critical", "지배구조", "지배구조 변경"),
    # ⚠️ 판단 재료
    (r"단일판매.*공급계약|수주",                        "notable",  "대형계약", "성장 논지 검증"),
    (r"자기주식.*(취득|처분|소각)",                     "notable",  "자사주",   "수급·주주환원"),
    (r"주식등의대량보유상황보고|대량보유",               "notable",  "5%보고",   "대주주 매매"),
    # 개별 제목은 삼성전자만 2주 763건 — 낱개로는 무의미하고 **합산이 신호**다.
    #    목록에서는 routine으로 눌러 두고, 방향·수량은 elestock.json(--insider)에서 집계한다.
    (r"임원.*주요주주.*소유상황",                       "routine",  "내부자",   "개별 무의미 — --insider로 합산"),
    (r"영업.*잠정.*실적|결산실적|매출액.*손익구조",       "notable",  "실적",     "하드넘버 갱신"),
    (r"배당",                                          "notable",  "배당",     "주주환원"),
    (r"신규시설투자|유형자산.*취득|타법인.*주식.*취득",   "notable",  "투자",     "capex 방향"),
    (r"주식매수선택권|스톡옵션",                        "notable",  "희석",     "잠재 희석"),
]

_TAG = re.compile(r"[\s​]+")


def _key():
    k = os.environ.get("DART_API_KEY")
    if not k:
        sys.exit("[dart_disclosure] 환경변수 DART_API_KEY 필요 (조회 전용·저장 금지).")
    return k


def _ctx():
    try:
        return ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt")
    except Exception:
        return ssl.create_default_context()


def classify(name: str):
    """공시명 → (등급, 카테고리, 사유). 어느 규칙에도 안 걸리면 routine."""
    n = _TAG.sub("", name or "")
    for pat, level, cat, why in RULES:
        if re.search(pat, n):
            return level, cat, why
    return "routine", "정기·형식", ""


def fetch(corp_code: str, bgn: str, end: str, page_count: int = 100) -> list[dict]:
    """DART list.json — 한 종목의 기간 내 공시 목록(페이지 순회)."""
    out, page = [], 1
    while True:
        q = urllib.parse.urlencode({"crtfc_key": _key(), "corp_code": corp_code,
                                    "bgn_de": bgn, "end_de": end,
                                    "page_no": page, "page_count": page_count})
        try:
            with urllib.request.urlopen(BASE + "/list.json?" + q, timeout=25, context=_ctx()) as r:
                d = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"  ⚠️ {corp_code} 조회 실패: {type(e).__name__} {str(e)[:60]}", file=sys.stderr)
            break
        st = d.get("status")
        if st == "013":          # 조회된 데이터 없음 = 정상(공시 0건)
            break
        if st != "000":
            print(f"  ⚠️ {corp_code} DART status={st} {d.get('message')}", file=sys.stderr)
            break
        out.extend(d.get("list") or [])
        if page >= int(d.get("total_page") or 1):
            break
        page += 1
    return out


def collect(universe: dict, days: int) -> list[dict]:
    import dart_facts as D
    codes = D.corp_codes()
    end = dt.date.today()
    bgn = end - dt.timedelta(days=days)
    rows = []
    for code, name in universe.items():
        cc = codes.get(code)
        if not cc:
            print(f"  ⚠️ {name}({code}) corp_code 미해결 — 건너뜀", file=sys.stderr)
            continue
        for it in fetch(cc, bgn.strftime("%Y%m%d"), end.strftime("%Y%m%d")):
            nm = _TAG.sub(" ", it.get("report_nm") or "").strip()
            level, cat, why = classify(nm)
            rows.append({
                "code": code, "name": name, "date": it.get("rcept_dt"),
                "title": nm, "level": level, "category": cat, "why": why,
                "rcept_no": it.get("rcept_no"), "filer": it.get("flr_nm"),
                "url": VIEW + (it.get("rcept_no") or ""),
            })
    order = {"critical": 0, "notable": 1, "routine": 2}
    rows.sort(key=lambda r: (order[r["level"]], -int(r["date"] or 0)))
    return rows


# ─────────────────────────────────────────── 출력

MARK = {"critical": "🚨", "notable": "⚠️ ", "routine": "· "}


def render(rows: list[dict], show_all: bool, days: int):
    shown = rows if show_all else [r for r in rows if r["level"] != "routine"]
    n_c = sum(1 for r in rows if r["level"] == "critical")
    n_n = sum(1 for r in rows if r["level"] == "notable")
    print(f"\n📋 DART 수시공시 최근 {days}일 — 총 {len(rows)}건 "
          f"(🚨중대 {n_c} · ⚠️주목 {n_n} · ·정기 {len(rows)-n_c-n_n})")
    if not show_all:
        print("   (정기·형식 공시는 숨김 — 전체는 --all)")
    if not shown:
        print("\n   중대·주목 공시 없음. ※'없음'도 결론이다 — 훼손 징후 부재의 근거로 인용 가능.")
        return
    cur = None
    for r in shown:
        if r["name"] != cur:
            cur = r["name"]
            print(f"\n── {cur} ({r['code']})")
        d = r["date"]
        ds = f"{d[4:6]}/{d[6:8]}" if d and len(d) == 8 else (d or "")
        why = f"  ← {r['why']}" if r["why"] else ""
        print(f"  {MARK[r['level']]}[{r['category']}] {ds} {r['title'][:56]}{why}")
        if r["level"] == "critical":
            print(f"      {r['url']}")


def _api(ep: str, corp_code: str) -> list[dict]:
    q = urllib.parse.urlencode({"crtfc_key": _key(), "corp_code": corp_code})
    try:
        with urllib.request.urlopen(f"{BASE}/{ep}?{q}", timeout=25, context=_ctx()) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  ⚠️ {ep} {corp_code}: {type(e).__name__} {str(e)[:50]}", file=sys.stderr)
        return []
    return (d.get("list") or []) if d.get("status") == "000" else []


def _num(x):
    """DART는 '1,030' · '-' · '' 를 섞어 준다."""
    if not x or x in ("-", "–"):
        return None
    try:
        return int(str(x).replace(",", "").replace("+", ""))
    except ValueError:
        try:
            return float(str(x).replace(",", ""))
        except ValueError:
            return None


def insider(universe: dict, days: int) -> list[dict]:
    """임원·주요주주 소유상황(elestock.json) **합산**.

    개별 보고서는 삼성전자만 2주 763건 — 낱개로는 무의미하다. 구조화 엔드포인트가
    보유수량(sp_stock_lmp_cnt)과 **증감(sp_stock_lmp_irds_cnt)**을 주므로,
    이걸 회사 단위로 합산해 **경영진 순매수/순매도 방향**을 낸다.
    ⚠️ 스톡옵션 행사·우리사주 배정도 '증가'로 잡힌다 — 순증 자체를 확신 신호로 읽지 말 것.
    """
    import dart_facts as D
    codes = D.corp_codes()
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    out = []
    for code, name in universe.items():
        cc = codes.get(code)
        if not cc:
            continue
        rows = [r for r in _api("elestock.json", cc) if (r.get("rcept_dt") or "") >= cutoff]
        buys = [r for r in rows if (_num(r.get("sp_stock_lmp_irds_cnt")) or 0) > 0]
        sells = [r for r in rows if (_num(r.get("sp_stock_lmp_irds_cnt")) or 0) < 0]
        net = sum(_num(r.get("sp_stock_lmp_irds_cnt")) or 0 for r in rows)
        top = sorted(rows, key=lambda r: abs(_num(r.get("sp_stock_lmp_irds_cnt")) or 0), reverse=True)[:4]
        out.append({"code": code, "name": name, "n": len(rows), "net": net,
                    "n_buy": len(buys), "n_sell": len(sells),
                    "top": [{"who": r.get("repror"), "ofcps": r.get("isu_exctv_ofcps"),
                             "regist": r.get("isu_exctv_rgist_at"),
                             "delta": _num(r.get("sp_stock_lmp_irds_cnt")),
                             "held": _num(r.get("sp_stock_lmp_cnt")),
                             "date": r.get("rcept_dt")} for r in top]})
    return out


def major(universe: dict, days: int) -> list[dict]:
    """5% 대량보유상황(majorstock.json) — **국민연금 등 기관 지분변동이 여기 있다.**

    보고 사유(report_resn)까지 오므로 '단순투자→일반투자 목적변경' 같은 행동주의 신호도 잡힌다.
    국내 수급(외인·기관) 일간 흐름과 달리 **누가 얼마를 들고 있나**의 확정 값이다.
    """
    import dart_facts as D
    codes = D.corp_codes()
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    out = []
    for code, name in universe.items():
        cc = codes.get(code)
        if not cc:
            continue
        for r in _api("majorstock.json", cc):
            if (r.get("rcept_dt") or "") < cutoff:
                continue
            out.append({"code": code, "name": name, "date": r.get("rcept_dt"),
                        "who": r.get("repror"), "qty": _num(r.get("stkqy")),
                        "d_qty": _num(r.get("stkqy_irds")), "rate": r.get("stkrt"),
                        "d_rate": r.get("stkrt_irds"), "reason": r.get("report_resn"),
                        "url": VIEW + (r.get("rcept_no") or "")})
    out.sort(key=lambda r: r["date"] or "", reverse=True)
    return out


def render_insider(ins: list[dict], days: int):
    print(f"\n👤 내부자(임원·주요주주) 보유증감 합산 — 최근 {days}일 · elestock.json")
    print("   ⚠️ 스톡옵션 행사·우리사주도 '증가'로 잡힌다 — 순증을 곧바로 확신 신호로 읽지 말 것.")
    any_row = False
    for r in ins:
        if not r["n"]:
            continue
        any_row = True
        sign = "순증" if r["net"] > 0 else "순감" if r["net"] < 0 else "중립"
        print(f"\n── {r['name']}: 보고 {r['n']}건 (증가 {r['n_buy']} / 감소 {r['n_sell']}) "
              f"→ {sign} {r['net']:+,}주")
        for t in r["top"]:
            if t["delta"] is None:
                continue
            print(f"     {t['date']} {t['who']} ({t['regist']}·{t['ofcps']}) "
                  f"{t['delta']:+,}주 → 보유 {t['held']:,}주" if t["held"] is not None
                  else f"     {t['date']} {t['who']} {t['delta']:+,}주")
    if not any_row:
        print("\n   해당 기간 보고 없음.")


def render_major(mj: list[dict], days: int):
    print(f"\n🏛️ 5% 대량보유 변동 — 최근 {days}일 · majorstock.json (국민연금·지주사 포함)")
    if not mj:
        print("   해당 기간 변동 보고 없음. ※'없음'도 결론 — 대주주 이탈 부재의 근거.")
        return
    for r in mj:
        d = (r["d_rate"] or "").strip()
        arrow = "▲" if d and not d.startswith("-") and d != "0.00" else ("▼" if d.startswith("-") else "―")
        print(f"  {arrow} {r['date']} {r['name']}: {r['who']} 지분 {r['rate']}% ({d}%p) "
              f"수량 {r['qty']:,}주 ({r['d_qty']:+,})" if r["qty"] is not None else
              f"  {arrow} {r['date']} {r['name']}: {r['who']} 지분 {r['rate']}%")
        if r["reason"] and r["reason"] != "-":
            print(f"      사유: {r['reason'][:70]}")


def main():
    ap = argparse.ArgumentParser(description="DART 수시공시 감시 (조회 전용·경보 전용)")
    ap.add_argument("--days", type=int, default=7, help="조회 기간(일, 기본 7)")
    ap.add_argument("--watch", action="store_true", help="워치 종목까지 포함")
    ap.add_argument("--all", action="store_true", help="routine(정기·형식) 공시도 표시")
    ap.add_argument("--insider", action="store_true", help="내부자(임원·주요주주) 보유증감 합산만")
    ap.add_argument("--major", action="store_true", help="5%% 대량보유 변동만(국민연금 등)")
    ap.add_argument("--save", action="store_true", help="data/app/disclosures.json 갱신")
    a = ap.parse_args()

    uni = dict(HOLD)
    if a.watch:
        uni.update(WATCH)

    rows = collect(uni, a.days)
    ins = mj = None
    if a.insider:
        render_insider(insider(uni, a.days), a.days)
    elif a.major:
        render_major(major(uni, a.days), a.days)
    else:
        render(rows, a.all, a.days)
        ins, mj = insider(uni, a.days), major(uni, a.days)
        render_insider(ins, a.days)
        render_major(mj, a.days)

    if a.save:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        payload = {
            "updated": dt.date.today().isoformat(),
            "days": a.days,
            "universe": list(uni),
            "counts": {lv: sum(1 for r in rows if r["level"] == lv)
                       for lv in ("critical", "notable", "routine")},
            # routine은 저장하지 않는다 — 노이즈가 파일을 삼키면 아무도 안 본다
            "items": [r for r in rows if r["level"] != "routine"],
            "insider": ins if ins is not None else insider(uni, a.days),
            "major": mj if mj is not None else major(uni, a.days),
            "note": "경보 전용 — 매수·매도 자동발동 아님. 훼손 판정은 PM·리스크 데스크.",
        }
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        print(f"\n💾 {os.path.relpath(OUT, ROOT)} 저장 (중대·주목 {len(payload['items'])}건)")
    print()


if __name__ == "__main__":
    main()
