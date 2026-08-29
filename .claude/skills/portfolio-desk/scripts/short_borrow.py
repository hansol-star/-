#!/usr/bin/env python3
"""short_borrow.py — 종목별 공매도·대차 + NAT 프록시 (KRX·stdlib·포터블)

정훈 지시(2026-07-22 "다 하자" — 공매도/대차 NAT 축). 학술 근거 = **NAT(Net Arbitrage Trading)
= 외국인 비정상 지분 − 비정상 공매도**가 한국시장 분기 초과수익 알파 2.22%(KAIST, study 7/22).
우리는 외국인 지분율(네이버 frr)은 이미 심층 확보 → 남은 축이 **공매도/대차**.

⚠️ 데이터 접근 현실(2026-07-22 실측): KRX(data.krx.co.kr) 공매도 JSON은 **데이터센터 IP에서 차단**
   (getJsonData 400 / download 302 'document moved'). 네이버 모바일엔 공매도 필드 없음(404).
   → 이 페처는 **쿠키 프라이밍 + 2단계 OTP**로 시도하되, 막히면 **정직하게 degrade**(추측 금지).
   **정훈 로컬 이전(1단계 8/31 예정·주거용 IP) 후 그대로 작동** — youtube 페처와 동일 포터블 설계.
   그전까지 공매도는 매 보고서 WebSearch(공매도 과열종목·대차잔고 뉴스)로 보강.

사용:
  python3 short_borrow.py --code 005930          # 공매도 일별(가능 시) or 차단 상태 리포트
  python3 short_borrow.py --status               # 접근 가능 여부만 점검
  python3 short_borrow.py --nat 005930           # NAT 프록시(외인지분 추세 + 공매도, 가능분만)
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
KRX = "https://data.krx.co.kr"
GEN = KRX + "/comm/fileDn/GenerateOTP/generate.cmd"
GETJSON = KRX + "/comm/bldAttendant/getJsonData.cmd"
PORTAL = KRX + "/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020506"  # 공매도 종합
# 공매도 거래(일별매매) / 잔고
BLD_TRADE = "dbms/MDC/STAT/srt/MDCSTAT30101"
BLD_BALANCE = "dbms/MDC/STAT/srt/MDCSTAT30401"


def _opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def _prime(op):
    """포털 페이지를 먼저 열어 세션 쿠키 획득(KRX 세션 가드 완화 시도)."""
    try:
        op.open(urllib.request.Request(PORTAL, headers={"User-Agent": UA}), timeout=15).read()
        return True
    except Exception:
        return False


def _isu(code: str) -> str:
    """6자리 → KRX 표준 ISU 코드(KR7+코드+0). (대부분 보통주 규칙, 예외 종목은 실패 가능)"""
    return f"KR7{code}0" + "03"[:1] * 0 + "3" if len(code) == 6 else code


def fetch_short(code: str, bld: str = BLD_TRADE, days: int = 30) -> dict:
    """공매도 일별 데이터 시도. 반환 {ok, status, rows|reason}."""
    op = _opener()
    primed = _prime(op)
    params = {
        "locale": "ko_KR", "bld": bld, "mktId": "STK",
        "isuCd": _isu(code), "strtDd": "20260601", "endDd": "20260722",
        "share": "1", "money": "1", "csvxls_isNo": "false",
    }
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(GETJSON, data=data, headers={
        "User-Agent": UA, "Referer": PORTAL,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    })
    try:
        raw = op.open(req, timeout=20).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": f"HTTP {e.code}", "reason": "KRX 차단(IP/세션 가드)", "primed": primed}
    except Exception as e:
        return {"ok": False, "status": "ERR", "reason": str(e)[:80], "primed": primed}
    if not raw or raw.lstrip()[:1] not in "{[":
        return {"ok": False, "status": "non-JSON",
                "reason": "302/HTML 응답(데이터센터 IP 차단) — 로컬 이전 후 작동", "primed": primed}
    try:
        j = json.loads(raw)
    except ValueError:
        return {"ok": False, "status": "parse", "reason": "JSON 파싱 실패", "primed": primed}
    rows = j.get("output") or j.get("OutBlock_1") or []
    return {"ok": True, "status": "OK", "rows": rows[:days], "primed": primed}


def nat_proxy(code: str) -> dict:
    """NAT 프록시 = 외국인 지분율 추세(네이버 frr) + 공매도(가능분). 공매도 없으면 반쪽(외인축만)."""
    out = {"code": code}
    try:
        import naver_chart as ncmod
        d = ncmod.fetch_naver_ohlc(code, "day", 400)
        ft = ncmod.frr_trend(d.get("frr") or [], d.get("dates") or []) if d else None
        out["foreign_axis"] = ft  # 지분율 방향(외인 매집/이탈)
    except Exception as e:
        out["foreign_axis"] = {"_error": str(e)[:60]}
    sh = fetch_short(code)
    out["short_axis"] = ({"available": True, "rows": len(sh["rows"])} if sh["ok"]
                         else {"available": False, "reason": sh["reason"]})
    # NAT 해석 — 두 축이 다 있을 때만 완결(외인 매집↑ + 공매도↓ = 강세 차익; 반대 = 약세)
    if sh["ok"] and out.get("foreign_axis") and not out["foreign_axis"].get("_error"):
        fdir = out["foreign_axis"]["direction"]
        out["nat_note"] = f"외인 {fdir} + 공매도 데이터 확보 → NAT 산출 가능(로컬)"
    else:
        out["nat_note"] = ("반쪽(외인 지분율 축만) — 공매도 축 차단. "
                           "매 보고서 WebSearch 공매도 과열/대차 뉴스로 보강.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="공매도·대차 + NAT 프록시(KRX·포터블)")
    ap.add_argument("--code", "--tickers", help="종목코드 6자리 공매도 일별 시도")
    ap.add_argument("--status", action="store_true", help="KRX 접근 가능 여부만 점검")
    ap.add_argument("--nat", metavar="CODE", help="NAT 프록시(외인지분+공매도)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.nat:
        r = nat_proxy(args.nat)
        print(json.dumps(r, ensure_ascii=False, indent=1) if args.json else
              f"■ NAT 프록시 {args.nat}\n  외인축: {r.get('foreign_axis')}\n"
              f"  공매도축: {r.get('short_axis')}\n  → {r.get('nat_note')}")
        return 0

    code = args.code or "005930"
    r = fetch_short(code)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if args.status or not r["ok"]:
        state = "✅ 접근 가능" if r["ok"] else "🔴 차단"
        print(f"■ KRX 공매도 접근 점검 ({code}): {state} — {r['status']}"
              + (f" · {r.get('reason')}" if r.get("reason") else ""))
        if not r["ok"]:
            print("  = 현재 데이터센터 IP에서 KRX 공매도 JSON 차단. 로컬 이전(1단계 8/31 예정) 후 작동 예상 — 그때 --status로 실측 확인.")
            print("  = 그전까지 공매도/대차는 WebSearch(공매도 과열종목·대차잔고 급증 뉴스)로 보강.")
        return 0
    print(f"■ 공매도 일별 {code} (최근 {len(r['rows'])}행)")
    for row in r["rows"][:10]:
        print("  ", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
