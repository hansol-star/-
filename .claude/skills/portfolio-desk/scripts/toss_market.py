#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""toss_market.py — 장 운영시간·가격제한폭·매수유의 (토스 1차 출처) [2026-09-04 신설]

■ 왜 만들었나 — 우리가 추정으로 쓰던 것들의 1차 출처가 있었다
9/4에 토스 Open API 엔드포인트를 전수 확인해보니 27개 중 **9개만 쓰고 있었다**.
그중 우리가 *추정으로 때우던* 축 셋이 1차 출처로 열려 있었다:

  ① **장 운영시간** — `price_watch.market_open_kst()`가 시각을 **하드코딩**하고
     "공휴일 미반영"을 약점으로 안고 있었다. 이 API는 today/previousBusinessDay/
     **nextBusinessDay**를 주므로 주말·공휴일이 자동으로 처리된다.
  ② **가격제한폭** — `validate_report.check_kr_price_band()`가 캐시 일봉 × 1.3으로
     **추정**한다. 8/12 LG전자 접수거부(240,000 > 상한 236,000) 사고를 막으려고 만든
     검사인데 정작 기준가가 추정치였다. 이 API는 실제 상·하한가를 준다.
  ③ **매수 유의사항** — 9/14 애프터마켓 **제외 종목**(투자경고·관리·이상급등) 판정에 필요.

★ 붙이자마자 **어제 서술의 오류가 잡혔다**: 9/3에 "9/14부터 국내 거래시간이 6.5h→13h로
  늘어난다"고 적었는데, 토스 `integrated`(KRX + **NXT 넥스트레이드** 통합) 기준으로는
  **오늘(9/4)도 이미 08:00~20:00**이다. NXT가 이미 연장 운영 중이었고, 9/14는
  **KRX 본장이 합류**하는 사건이다. ⇒ 정훈은 *지금도* 20:00까지 거래할 수 있다.
  **추정과 1차 출처의 차이가 하루짜리 오해가 아니라 '오늘 뭘 할 수 있나'를 갈랐다.**

⚠️ 조회 전용. toss_snapshot의 주문 차단 가드(_assert_readonly)를 그대로 통과한다.
⚠️ `integrated`는 KRX 단독이 아니다 — KRX만의 시간이 필요한 판정에는 쓰지 말 것.

사용:
  toss_market.py --calendar KR          # 국내 장 운영시간
  toss_market.py --calendar US
  toss_market.py --limits 005930        # 상·하한가
  toss_market.py --warnings 005930      # 매수 유의사항
  toss_market.py --save                 # 전부 수집 → data/app/toss_market.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)
OUT = os.path.join(ROOT, "data", "app", "toss_market.json")

KR_HOLDINGS = ["005930", "066570", "454910", "005380", "035420"]


def _auth():
    """토스 토큰 — toss_snapshot의 req()를 그대로 쓴다(가드 포함)."""
    import toss_snapshot as T
    ctx = T.make_ctx(False)
    cid = os.environ.get("TOSS_CLIENT_ID")
    sec = os.environ.get("TOSS_CLIENT_SECRET")
    if not (cid and sec):
        return None, None, "TOSS_CLIENT_ID/SECRET 미설정"
    tok = T.req("POST", "/oauth2/token", ctx, form=True, data={
        "grant_type": "client_credentials", "client_id": cid, "client_secret": sec})
    if not tok or not tok.get("access_token"):
        return None, None, "토큰 발급 실패"
    return ctx, {"Authorization": "Bearer " + tok["access_token"]}, None


def calendar(market: str = "KR"):
    import toss_snapshot as T
    ctx, auth, err = _auth()
    if err:
        return None, err
    r = T.req("GET", f"/api/v1/market-calendar/{market}", ctx, headers=auth)
    return (r or {}).get("result"), None if r else "조회 실패"


def _hhmm(iso):
    try:
        return iso[11:16]
    except Exception:                                              # noqa: BLE001
        return "?"


def show_calendar(market: str) -> int:
    res, err = calendar(market)
    if err or not res:
        print(f"❌ {err or '응답 없음'}", file=sys.stderr)
        return 1
    print(f"■ {market} 장 운영 (토스 1차 출처 · integrated = KRX+NXT 통합)")
    for k, lab in (("previousBusinessDay", "직전영업일"), ("today", "오늘"),
                   ("nextBusinessDay", "다음영업일")):
        d = res.get(k) or {}
        seg = d.get("integrated") or {}
        if not seg:
            continue
        parts = []
        for s, nm in (("preMarket", "프리"), ("regularMarket", "정규"),
                      ("dayMarket", "데이"), ("afterMarket", "애프터")):
            v = seg.get(s)
            if v:
                parts.append(f"{nm} {_hhmm(v.get('startTime'))}~{_hhmm(v.get('endTime'))}")
        print(f"  {lab:<8} {d.get('date')}  " + " · ".join(parts))
    return 0


def limits(symbol: str):
    import toss_snapshot as T
    ctx, auth, err = _auth()
    if err:
        return None, err
    r = T.req("GET", f"/api/v1/price-limits?symbol={symbol}", ctx, headers=auth)
    return (r or {}).get("result"), None if r else "조회 실패"


def warnings(symbol: str):
    import toss_snapshot as T
    ctx, auth, err = _auth()
    if err:
        return None, err
    r = T.req("GET", f"/api/v1/stocks/{symbol}/warnings", ctx, headers=auth)
    return (r or {}).get("result"), None if r else "조회 실패"


def save() -> int:
    """보유 국내 5종목의 상하한가·유의사항 + KR/US 캘린더를 한 파일로."""
    now = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9))
    out = {"updated": now.strftime("%Y-%m-%d %H:%M"), "calendars": {}, "stocks": {}}
    for m in ("KR", "US"):
        res, err = calendar(m)
        if res:
            out["calendars"][m] = res
        else:
            print(f"  ⚠️ {m} 캘린더 실패: {err}", file=sys.stderr)
    for s in KR_HOLDINGS:
        row = {}
        lim, e1 = limits(s)
        if lim:
            row["limits"] = lim
        warn, e2 = warnings(s)
        if warn is not None:
            row["warnings"] = warn
        if row:
            out["stocks"][s] = row
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n_w = sum(1 for v in out["stocks"].values() if v.get("warnings"))
    print(f"✅ {OUT}")
    print(f"   캘린더 {len(out['calendars'])} · 종목 {len(out['stocks'])} "
          f"· 유의사항 있는 종목 {n_w}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="장 운영시간·가격제한폭·매수유의 (토스 1차 출처·조회 전용)")
    ap.add_argument("--calendar", choices=["KR", "US"], help="장 운영시간")
    ap.add_argument("--limits", metavar="SYMBOL", help="상·하한가")
    ap.add_argument("--warnings", metavar="SYMBOL", help="매수 유의사항")
    ap.add_argument("--save", action="store_true", help="전부 수집 저장")
    a = ap.parse_args()
    if a.calendar:
        return show_calendar(a.calendar)
    if a.limits:
        r, e = limits(a.limits)
        if e:
            print(f"❌ {e}", file=sys.stderr); return 1
        print(f"■ {a.limits} 가격제한폭 (1차 출처)")
        print(f"   상한 {int(r['upperLimitPrice']):,} · 하한 {int(r['lowerLimitPrice']):,} "
              f"{r.get('currency','')}")
        return 0
    if a.warnings:
        r, e = warnings(a.warnings)
        if e:
            print(f"❌ {e}", file=sys.stderr); return 1
        print(f"■ {a.warnings} 매수 유의사항: " + ("없음" if not r else json.dumps(r, ensure_ascii=False)))
        return 0
    if a.save:
        return save()
    ap.error("--calendar · --limits · --warnings · --save 중 하나가 필요하다")


if __name__ == "__main__":
    sys.exit(main())
