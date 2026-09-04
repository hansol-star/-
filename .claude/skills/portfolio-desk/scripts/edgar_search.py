#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""edgar_search.py — SEC EDGAR 전문검색(FTS) + 8-K 이벤트 스트림 [2026-08-05 신설·무키]

■ 왜 만들었나 (기존 도구가 못 하던 것)
우리 EDGAR 계열 도구는 전부 **숫자를 정해진 자리에서 꺼내오는** 구조다:
  · financials.py / edgar_facts.py → companyfacts XBRL(정해진 계정 태그)
  · guidance.py                    → 8-K Item 2.02 보도자료의 가이던스 수치
  · insider_us.py                  → Form 4 / 13D·13G
그래서 **"이 표현이 어느 공시에 처음 등장했나"**를 물을 수단이 없었다. 예:
"HBM4 양산"이 MU 10-Q에 언제부터 쓰였나, "supply agreement"가 누구 공시에 떴나,
CXMT·관세·리스크팩터 문구 변화 — 전부 산문이라 XBRL엔 없다. 7/29 CXMT 오류처럼
**1차 문서를 직접 확인 못 해서 2차 매체 서술을 그대로 받아쓴 사고**의 예방 장치다.

■ 두 기능
  1) FTS  = efts.sec.gov 전문검색(2001~현재 전 공시 본문·첨부). 무키.
            → "우리 종목 공시에서 이 문구를 찾아라" = 1차 출처로 바로 내려가는 길.
  2) 8-K  = submissions 피드의 **item 코드** 스트림. 8-K는 '무슨 일이 났나'를 코드로 말한다.
            2.02 실적발표 / 1.01 중대계약 / 5.02 임원변동 / 2.01 인수·매각 / 8.01 기타중요 …
            → 코드로 읽으면 제목 안 읽고도 사건 종류가 잡힌다(경보 전용).

■ 규율 (반드시 지킬 것)
  · **측정·탐색 전용 — 별점·스코어·트랜치 어떤 룰도 바꾸지 않는다.** 매수 트리거 아님.
  · FTS 히트는 **문구가 있다**는 사실일 뿐 맥락이 아니다. 인용하려면 --open 으로 원문 URL을
    열어 문장을 직접 확인한다(7/26·7/28 정정룰: 주체·범위·형식·단위를 원문에서 확인).
  · SEC 레이트리밋 10 req/s — 이 스크립트는 요청 간 페이싱을 넣는다. User-Agent 필수.
  · FTS 범위 = **2001년 이후**. 그 전 문서는 안 잡힌다.

■ 사용
  edgar_search.py --q "HBM4"                     # 보유 미국주 전체에서 문구 검색
  edgar_search.py --q "supply agreement" --tickers MU,NVDA --forms 8-K
  edgar_search.py --q "tariff" --since 2026-01-01 --limit 20
  edgar_search.py --events                       # 보유 미국주 최근 8-K 이벤트 스트림
  edgar_search.py --events --tickers MU --days 180
  edgar_search.py --json                         # 기계 소비용

데이터: SEC EDGAR (efts.sec.gov/LATEST/search-index · data.sec.gov/submissions). 무키·stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

try:
    from cli_common import add_tickers, split_tickers
except ImportError:  # 단독 실행 폴백
    def split_tickers(value):
        import re
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            out = []
            for v in value:
                out.extend(split_tickers(v))
            return out
        return [t for t in re.split(r"[,\s]+", str(value).strip()) if t]

    def add_tickers(ap, *names, help="", **kw):
        ap.add_argument(*(names or ("--tickers",)), help=help, **kw)

# SEC는 **연락처가 든** User-Agent를 요구한다 — 없거나 형식이 어긋나면 전 요청 403.
# edgar_facts.py·insider_us.py와 같은 문자열을 쓴다(한 곳에서 막히면 전부 같이 막히도록 = 진단 단순화).
UA = "Jeonghun Portfolio Desk (contact: dpm5bfb6k9@privaterelay.appleid.com)"
FTS_URL = "https://efts.sec.gov/LATEST/search-index"
SUB_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"

# 보유 미국주 CIK (VOO=ETF 제외 — 운용사 공시라 종목 이벤트가 아님)
HOLDINGS_US = {
    "NVDA": "0001045810",
    "MU": "0000723125",
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "ANET": "0001596532",
    "AVGO": "0001730168",
    "GOOGL": "0001652044",
    "META": "0001326801",
    "ORCL": "0001341439",
}

# 8-K item 코드 → 뜻 + 중대성. dart_disclosure.py의 3단 분류와 같은 문법을 쓴다.
#   critical = 실적·중대계약·인수·상장폐지 등 논지를 바꿀 수 있는 것
#   notable  = 임원변동·정관·주총 등 봐둘 것
#   routine  = 첨부·규정공시 (기본 숨김)
ITEM_MAP = {
    "1.01": ("중대계약 체결", "critical"),
    "1.02": ("중대계약 종료", "critical"),
    "1.03": ("파산·법정관리", "critical"),
    "1.05": ("사이버 침해사고", "critical"),
    "2.01": ("인수·자산매각 완료", "critical"),
    "2.02": ("실적 발표", "critical"),
    "2.03": ("중대 채무 발생", "critical"),
    "2.04": ("채무 기한이익 상실", "critical"),
    "2.05": ("구조조정 비용", "notable"),
    "2.06": ("자산 손상차손", "critical"),
    "3.01": ("상장규정 위반·상폐", "critical"),
    "3.02": ("지분 사모발행(희석)", "critical"),
    "3.03": ("주주권리 변경", "notable"),
    "4.01": ("회계법인 교체", "critical"),
    "4.02": ("과거 재무제표 신뢰불가", "critical"),
    "5.01": ("경영권 변동", "critical"),
    "5.02": ("임원 선임·사임", "notable"),
    "5.03": ("정관·회계연도 변경", "routine"),
    "5.07": ("주주총회 결과", "routine"),
    "7.01": ("Reg FD 공개", "notable"),
    "8.01": ("기타 중요사항", "notable"),
    "9.01": ("재무제표·첨부", "routine"),
}
SEV_MARK = {"critical": "🚨", "notable": "⚠️", "routine": "·"}

_last_call = [0.0]


def _get(url: str, timeout: int = 30):
    """SEC 요청 — UA 필수 + 최소 0.15초 페이싱(10 req/s 제한 여유)."""
    gap = time.time() - _last_call[0]
    if gap < 0.15:
        time.sleep(0.15 - gap)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                import gzip
                raw = gzip.decompress(raw)
            return json.loads(raw.decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001 — 네트워크·파싱 전부 '조회 실패'로 동일 취급
        return {"_error": f"{type(e).__name__}: {e}"}
    finally:
        _last_call[0] = time.time()


# ───────────────────────────── 1) 전문검색 ─────────────────────────────

def _fts_one(query, cik=None, forms=None, since=None, until=None):
    """efts 단일 호출. **cik은 하나만** — 여러 개를 쉼표로 넘기면 서버가 500을 준다(8/5 실측).

    같은 실측에서 확인한 또 하나: 필터 없는 순수 q 검색도 500이 잦다.
    ⇒ 호출은 항상 '한 회사 + (선택)폼' 단위로 쪼개고, 합치는 건 우리가 한다.
    """
    params = {"q": f'"{query}"' if " " in query else query}
    if cik:
        params["ciks"] = cik.lstrip("0").zfill(10)
    if forms:
        params["forms"] = ",".join(forms)
    if since:
        params["startdt"] = since
        params["enddt"] = until or date.today().isoformat()
    d = _get(FTS_URL + "?" + urllib.parse.urlencode(params))
    if "_error" in d:
        return None, d["_error"]
    hits = []
    for h in d.get("hits", {}).get("hits", []):
        src = h.get("_source", {})
        names = src.get("display_names") or []
        # _id = "0000723125-24-000016:doc.htm" → 원문 URL 조립
        acc, _, doc = h.get("_id", "").partition(":")
        hcik = (src.get("ciks") or [""])[0]
        link = ""
        if acc and doc and hcik:
            link = DOC_URL.format(cik=hcik.lstrip("0"), acc=acc.replace("-", ""), doc=doc)
        hits.append({
            "company": names[0] if names else "?",
            "date": src.get("file_date", ""),
            "form": src.get("root_form") or src.get("file_type", ""),
            "doc_type": src.get("file_type", ""),
            "url": link,
        })
    return {"total": d.get("hits", {}).get("total", {}).get("value", 0), "hits": hits}, None


def fts(query: str, ciks=None, forms=None, since=None, until=None, limit=10):
    """종목별로 따로 조회해 합친다(서버가 다중 CIK를 안 받으므로).

    부분 실패는 전체 실패로 만들지 않는다 — 성공한 회사 결과는 그대로 보여주고
    실패한 회사만 errors에 남긴다(한 종목이 죽어서 나머지를 못 보는 걸 막는다).
    """
    all_hits, total, errors = [], 0, []
    for cik in (ciks or [None]):
        res, err = _fts_one(query, cik=cik, forms=forms, since=since, until=until)
        if err:
            errors.append(f"CIK {cik or '(전체)'}: {err}")
            continue
        total += res["total"]
        all_hits.extend(res["hits"])
    all_hits.sort(key=lambda h: h["date"], reverse=True)
    return {"total": total, "hits": all_hits[:limit],
            "error": "; ".join(errors) if errors and not all_hits else None,
            "partial_errors": errors}


# ─────────────────────────── 2) 8-K 이벤트 스트림 ───────────────────────────

def events(ticker: str, cik: str, days: int = 90, include_routine: bool = False):
    """submissions 피드에서 최근 8-K를 item 코드로 분류해 돌려준다."""
    d = _get(SUB_URL.format(cik=cik))
    if "_error" in d:
        return {"ticker": ticker, "error": d["_error"], "events": []}
    r = d.get("filings", {}).get("recent", {})
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    out = []
    for i, form in enumerate(r.get("form", [])):
        if form != "8-K":
            continue
        fdate = r["filingDate"][i]
        if fdate < cutoff:
            break  # 피드는 최신순 — 컷오프 밑이면 나머지도 전부 오래됨
        codes = [c.strip() for c in (r.get("items", [""])[i] or "").split(",") if c.strip()]
        labeled = [(c, *ITEM_MAP.get(c, ("미분류", "notable"))) for c in codes]
        # 이 공시의 중대성 = 포함된 item 중 가장 높은 것
        sev = "routine"
        for _, _, s in labeled:
            if s == "critical":
                sev = "critical"
                break
            if s == "notable":
                sev = "notable"
        if sev == "routine" and not include_routine:
            continue
        acc = r["accessionNumber"][i].replace("-", "")
        out.append({
            "date": fdate,
            "severity": sev,
            "items": [{"code": c, "label": lab, "severity": s} for c, lab, s in labeled],
            "url": f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc}/"
                   f"{r['primaryDocument'][i]}",
        })
    return {"ticker": ticker, "error": None, "events": out}


# ───────────────────────────── 출력 ─────────────────────────────

def print_fts(query, res, scope_note):
    print(f"\n🔎 EDGAR 전문검색 — \"{query}\"  {scope_note}")
    print("   ※ 히트 = 그 문구가 공시에 있다는 사실일 뿐이다. 인용 전 원문 URL로 문장을 직접 확인할 것.")
    if res["error"]:
        print(f"   🔴 조회 실패: {res['error']}")
        return
    if not res["hits"]:
        print("   해당 없음. ※'없음'도 결론 — 그 표현이 1차 공시엔 아직 안 쓰였다는 뜻.")
        return
    print(f"   전체 {res['total']}건 (표시 {len(res['hits'])})")
    for e in res.get("partial_errors") or []:
        print(f"   ⚠️ 일부 조회 실패 — {e}")
    print()
    for h in res["hits"]:
        print(f"   {h['date']}  {h['form']:<6} {h['company'][:46]}")
        if h["url"]:
            print(f"      {h['url']}")


def print_events(results, days):
    print(f"\n📋 8-K 이벤트 스트림 — 최근 {days}일 · SEC submissions (무키)")
    print("   중대성: 🚨critical(실적·계약·인수·희석) ⚠️notable(임원·기타중요) ·routine(첨부·주총, 기본숨김)")
    print("   경보 전용 — 자동 매매 아님. 룰(별점·트랜치)을 바꾸지 않는다.\n")
    any_hit = False
    for r in results:
        if r["error"]:
            print(f"── {r['ticker']}: 🔴 {r['error']}")
            continue
        if not r["events"]:
            continue
        any_hit = True
        print(f"── {r['ticker']}: {len(r['events'])}건")
        for e in r["events"]:
            labels = " / ".join(f"{i['code']} {i['label']}" for i in e["items"]
                                if i["severity"] != "routine") or "첨부만"
            print(f"     {SEV_MARK[e['severity']]} {e['date']}  {labels}")
            print(f"        {e['url']}")
        print()
    if not any_hit:
        print("   기간 내 중대 8-K 없음. ※'없음'도 결론 — 사건 부재의 근거.")


def main():
    ap = argparse.ArgumentParser(
        description="SEC EDGAR 전문검색(FTS) + 8-K 이벤트 스트림 — 무키·1차 출처 탐색",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="예) edgar_search.py --q \"HBM4\" --forms 10-Q\n"
               "    edgar_search.py --events --tickers MU --days 180")
    ap.add_argument("--q", help="검색할 문구(공백 포함이면 자동으로 완전일치 처리)")
    ap.add_argument("--events", action="store_true", help="8-K item 코드 이벤트 스트림")
    add_tickers(ap, "--tickers", help="대상 티커(기본 = 보유 미국주 9종). 쉼표·공백 구분")
    ap.add_argument("--forms", help="공시 종류 필터 (예 8-K,10-Q,10-K)")
    ap.add_argument("--since", help="시작일 YYYY-MM-DD (FTS 전용)")
    ap.add_argument("--until", help="종료일 YYYY-MM-DD (FTS 전용)")
    ap.add_argument("--days", type=int, default=90, help="8-K 조회 기간(일, 기본 90)")
    ap.add_argument("--limit", type=int, default=10, help="FTS 표시 건수(기본 10)")
    ap.add_argument("--routine", action="store_true", help="routine 등급 8-K도 표시")
    ap.add_argument("--json", action="store_true", help="기계 소비용 JSON 출력")
    ap.add_argument("--save", action="store_true",
                    help="data/app/edgar_events.json 저장 — archive_daily가 날짜별로 누적 [9/4]")
    args = ap.parse_args()

    if not args.q and not args.events:
        ap.error("--q(전문검색) 또는 --events(8-K 스트림) 중 하나는 필요하다")

    picked = [t.upper() for t in split_tickers(args.tickers)] or list(HOLDINGS_US)
    unknown = [t for t in picked if t not in HOLDINGS_US]
    targets = {t: HOLDINGS_US[t] for t in picked if t in HOLDINGS_US}
    if unknown:
        print(f"⚠️ CIK 미등록 티커 무시: {', '.join(unknown)} "
              f"(보유 미국주만 지원 — 국내주는 dart_disclosure.py)", file=sys.stderr)
    if not targets:
        print("🔴 대상 종목이 없다.", file=sys.stderr)
        return 1

    payload = {"as_of": datetime.now().strftime("%Y-%m-%d %H:%M"), "source": "SEC EDGAR"}

    if args.q:
        forms = split_tickers(args.forms) if args.forms else None
        res = fts(args.q, ciks=list(targets.values()), forms=forms,
                  since=args.since, until=args.until, limit=args.limit)
        payload["fts"] = {"query": args.q, **res}
        if not args.json:
            scope = f"· 대상 {len(targets)}종목" + (f" · {'/'.join(forms)}" if forms else "")
            print_fts(args.q, res, scope)

    if args.events:
        results = [events(t, c, days=args.days, include_routine=args.routine)
                   for t, c in targets.items()]
        payload["events"] = results
        if not args.json:
            print_events(results, args.days)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.save:
        # ★[9/4] 저장 경로 신설. 舊엔 8-K 이벤트를 조회만 하고 버려서, 나중에
        #   "그 공시가 언제 떴나"를 되짚을 수 없었다(9/4 누적 감사 — dart_disclosure의
        #   미국 짝인데 그쪽만 --save가 있었다. 형제 버그가 옆에 남아 있었다).
        import datetime as _dt
        _kst = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=9)
        _p = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "..", "..", "..", "data", "app", "edgar_events.json"))
        os.makedirs(os.path.dirname(_p), exist_ok=True)
        json.dump({"updated": _kst.strftime("%Y-%m-%d %H:%M"),
                   "days": args.days,
                   "note": "SEC 8-K item 코드 스트림. item 코드는 '사건이 있었다'는 사실이지 "
                           "내용이 아니다 — 논지를 바꿀 건이면 원문 URL로 내려갈 것.",
                   **payload},
                  open(_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"저장: {_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
