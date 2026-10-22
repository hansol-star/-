#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
order_check.py — 토스 미체결 주문 ↔ 우리 계획(tasks.json) 대조

왜 있나 [9/21 신설 — 앱 결함이 실주문이 된 날]
────────────────────────────────────────────────────────────
9/21 21:42 NAVER 1주 196,400원 **매수**가 토스에 접수됐다. 6/26에 만들어 '보류'로 멈춘 오더가
앱 결정 카드에 활성처럼 떴고(분류 결함), 정훈이 그걸 보고 걸었다. 계획과는 세 곳에서 충돌했다
(⭐2 기한부 홀드 · 룰6 국내 27.5% > 22% · 사다리 잔여 0원). 사람이 수동 대조로 잡았다.

같은 날 반대 방향 사고도 있었다: 두산로보 78,000원 '매일 등록' 오더가 9/21분 **미등록**이었고
(재등록 알림은 갔지만 확인 수단이 없었다), 과거 v81에선 '4건 접수 완료'로 3일 보고했는데 실제로는
비어 있었다. 알림(notify)은 "걸어라"까지만 하고 **"걸린 게 계획과 같은가"를 아무도 안 봤다.**

이 스크립트가 그 고리를 닫는다 — 토스 OPEN(GET 전용)을 계획과 대조해:

  🔴 계획 밖 매수 / 보류·폐기된 오더와 같은 주문 / ⭐2 이하 추가매수 / 룰6 초과 중 국내 매수
  🟡 계획 밖 매도 / 가격제한폭 밖(접수 거부·무효) / '매일 등록' 오더 미등록 / 국내 트랙 회차 0원 중 매수
  ✅ 계획과 일치

⚠️ 조회 전용 — 토스 가드(_assert_readonly)를 그대로 쓴다. 주문 취소·정정은 **정훈이 직접.**
⚠️ 키는 환경변수(로컬 대화형 세션). 무인 루틴엔 키가 없어서 '미확인'으로 끝난다 — 조용히 통과시키지 않는다.

사용법:
  python3 order_check.py                  # 토스 조회 → 대조 (🔴 있으면 exit 1)
  python3 order_check.py --file open.json # 저장된 OPEN 목록으로 대조(테스트·오프라인)
  python3 order_check.py --json
  python3 order_check.py --file open.json --now "2026-09-22 22:01" --no-save   # 그 시각 기준으로 재현
  python3 order_check.py --selftest       # 가격제한폭 기준가 회귀 테스트(guard_selftest가 부른다)
  결과는 매번 data/app/order_check.json에 남는다 → validate_report.check_order_check가 읽는다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)

TASKS = os.path.join(REPO, "data", "app", "tasks.json")
STOCKS = os.path.join(REPO, "data", "app", "stocks.json")
RULE_LOG = os.path.join(REPO, "data", "app", "rule_log.jsonl")
SNAPS = os.path.join(REPO, "data", "snapshots")
OUT = os.path.join(REPO, "data", "app", "order_check.json")
KST = dt.timezone(dt.timedelta(hours=9))
KR_CAP_PCT = 22.0   # 룰6 국내 목표 상단

# ★[10/19] '체결' 앞에 '미'가 붙으면 살아 있는 오더다 — 舊 정규식은 "미체결이면 매일 재등록" 같은
#   상태 문구를 '체결 = 종결'로 읽어 '매일 등록' 역방향 검사에서 조용히 뺐다(ANET $182 실측).
# ★[10/21] '접수완료'·'등록완료'·'예약완료'는 살아 있는 오더다 — 舊 '완료' 단독 매칭이 이를 종결로 읽었다
#   (8/19 현대차 470,000 '접수완료'가 그 형태). 종결 의미의 '완료'(환전 완료·매도 완료 등)는 그대로 dead.
# ★[10/22 리뷰 반영] '체결 대기·체결 예정·체결권·체결확률·체결되면'은 아직 안 끝난 오더다 — 舊 정규식은 이들을 종결로 읽어
#   d244 역방향 검사에서 조용히 뺐고, 토스에 실제로 걸려 있으면 "계획상 종결인 오더와 같은 주문" 🔴(취소 권고)까지 냈다.
# ★[10/22 리뷰 2차 — 실제 tasks.json 이력 143개 상태 문장] 해설이 상태를 정했다: '✅ 예약 접수 완료 — … 즉시체결도 가능'·
#   '등록 완료 … 익일 체결확률'·'재등록 대상 — 舊 접수완료는…'이 종결로 읽혔다. ⇒ **상태 = 앞 구절**(첫 '—'·'⚠️'·'. ' 앞)과
#   ✅·⚪·⛔·❌로 시작하는 뒤 구절만 본다(체결을 뒤에 덧붙인 '오늘 밤 등록 — ✅ 체결 10/23'도 잡는다).
# ★[10/22 리뷰 3차] ⓐ '체결 실패'·'체결 안 됨'·'체결 못'·'체결 없음'은 살아 있는 오더다(舊 = 종결로 읽혀 다시 걸면 🔴 취소 권고)
#   ⓑ '체결된 것 확인'·'체결을 확인'·'체결가 $X 확인'은 종결이다(위 '된·을·가' 예외가 이들을 살려 뒀다).
# ★[10/22 리뷰 3차 C0] 조건·미래·금지형은 종결이 아니다 — '체결 후·체결되지 않으면·체결 전까지·체결이 안 되면·체결까지·
#   체결 기대·체결 확인 예정/은 내일·체결 소식 없음'·'취소 시·취소하지 말 것·취소 금지·취소 안 함'(舊 = 전부 dead → 살아 있는
#   매일 등록 오더를 d244 역방향 검사에서 빼고, 토스에 걸려 있으면 🔴 취소 권고).
_CHK_NOT_DONE = r"(?!\s*(?:대기|요망|필요|전|못|안|불가|후|예정|은|는|되면|하면|할|해야))"
_COND_END = r"(?!\s*(?:시(?![가-힣])|하면|하지|할|금지|안\s*함|안\s*한다|않|예정|검토|여부|가능|될|되면|되지|후보))"
DEAD = re.compile(r"(?:폐기|취소)" + _COND_END + r"|대체됨|건너뜀|종결|미접수 확정"
                  r"|체결(?:된\s*(?:것|거)|을|이)?\s*(?:을\s*)?확인" + _CHK_NOT_DONE +
                  r"|체결가\s*\$?\s*[\d,.]+\s*(?:원\s*)?(?:에\s*)?확인" + _CHK_NOT_DONE +
                  r"|(?<!미)(?<!즉시)체결(?!\s*(?:대기|예정|권|확률|여부|유력|가능|되면|하면|이면|될|된|되지|도|을|가(?![가-힣])"
                  r"|검토|미확인|확인\s*(?:대기|요망|필요|전|예정|은|는|되면|하면|할|해야)|전까지|전(?![가-힣])|시(?![가-힣])"
                  r"|후(?![가-힣])|까지|기대|소식|이\s*(?:안|못|없|되면)|실패|안|못|없|불가))"
                  r"|완료")
# 종결이 아닌 '완료'(등록 완료·재등록 완료·예약주문 완료·등록 확인 완료·접수완료·재설계 완료·기한 갱신 완료·입금 확인 완료)는
# DEAD를 보기 전에 지운다. 종결 의미('체결 완료'·'매도 완료'·'환전 완료'·'결정 완료'·'확인 완료')는 남는다.
PLACED_DONE = re.compile(r"(?:등록|접수|예약|재설계|설계|갱신|입금\s*확인|준비|검토|계산|세팅|설정|산정|정정|조정)"
                         r"\s*(?:주문\s*|확인\s*)?완료")
# ★[10/22 리뷰 3차 C1] 조건형('…면 중지')·해제형('보류 해제')은 보류가 아니다 — 舊 = 문장 어디든 '중지'가 있으면 hold로 읽어
#   살아 있는 오더를 역방향 검사에서 뺐다.
HOLD = re.compile(r"(?<!면 )(?<!면)(?:보류|중지|중단|동결)(?!\s*(?:해제|재개|없이|시(?![가-힣])|하면|되면|예정|검토))"
                  r"|^\W*⏸(?!.*(?:재시도|해제))")
_HEAD_CUT = re.compile(r"\s*(?:—|⚠️|\.\s)")
# ★[10/22 리뷰 3차] ⓐ 맨 앞 ⚠️는 자르기 전에 뗀다 — 舊 = '⚠️ 폐기(9/21) — …'의 앞 구절이 빈 문자열이 돼 폐기 오더가 active로 읽혔다
#   (토스에 남아 있으면 🔴 대신 ✅ '계획과 일치', 없으면 d244가 '재등록'을 권했다 · 이력 152개 중 9개가 ⚠️로 시작)
#   ⓑ 뒤 구절이 **종결어로 시작**하면(— 체결 10/23 · → 취소 · — 폐기) 이모지가 없어도 종결로 본다.
_LEAD_WARN = re.compile(r"^\s*\**\s*(?:⚠️|⚠)\s*\**\s*")
_TERMINAL_CLAUSE = re.compile(
    r"(?:—|·|\||→)\s*\**\s*((?:[✅⚪⛔❌]|\(?\d{1,2}/\d{1,2}\)?\s*(?=폐기|취소|대체됨|건너뜀|종결|체결|미접수)"
    r"|(?=폐기|취소|대체됨|건너뜀|종결|체결|미접수))[^—·|→]*)")
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"|‘[^’]*’|“[^”]*”")
# ★[10/21 d244 정훈 승인 "다 승인"] 역방향 검사를 '매일 등록' 밖으로 넓힌다 — 계획 상태가 "걸었다"고 말하는데
#   토스 OPEN에 없으면 미접수이거나 1거래일 소멸(d128)이다. '재등록 권고'·'미등록'·'등록선'은 걸었다는 말이 아니다.
# ★[10/22 리뷰 반영] ⓐ '재등록 완료'·'접수됐다'·'등록돼 있음'·상태 '예약'(계획→예약→체결)·'8/13 재접수'·'생존(… 만료)'·
#   '커버됨'도 걸었다는 말이다 ⓑ '안 걸었음'·'못 걸었다'·'걸 예정'·'등록 확인 필요'·'예약 중지'·'미체결이면 매 거래일 재등록'·
#   인용된 舊 표기('✅접수완료'는 …)는 걸었다는 말이 **아니다**(뒤집어 읽으면 일부러 안 건 오더를 걸라고 한다).
# ★[10/22 리뷰 3차] 부정·과거·의문형은 '걸려 있다'가 아니다 — '등록돼 있지 않음'·'등록했던 오더 만료'·'등록 중이던 주문'·
#   '등록됐는지 미확인'·'등록 확인 못 함'·'재등록 — 안 함' (뒤집어 읽으면 일부러 안 건 방식ⓑ 오더를 매일 걸라고 한다 = d151).
# ★[10/22 리뷰 3차 C3·C4] ⓐ '접수됐으나 만료'·'등록됐다가 소멸'·'점등 시 등록함'·'등록 확인 예정'·'예약 접수 대기'·
#   '예약(정훈 결정 대기)'·'재등록 — 정훈 결정 대기'는 걸려 있다는 말이 아니다 ⓑ '걸려 있음'·'걸어 둔'·'토스 OPEN 확인'·
#   '주문 들어가 있음'은 걸려 있다는 말이다(舊 = 못 읽어 d244가 보지 않았다).
_NOT_NOW = r"(?!\s*있지\s*않|\s*있진\s*않|\s*않|\s*아님|\s*아니|는지|던|었던|이던|\s*으나|\s*다가|\s*지만)"
REG_CLAIM = re.compile(
    r"(?<!미)(?<!시 )(?:등록|접수|예약)\s*(?:주문\s*)?(?:완료|확인(?!\s*(?:필요|대기|요망|전|불가|안|못|후|되면|할|해야|예정))"
    r"|(?:됨|함|했|됐|돼|중(?![지단])|걸어|걸었|걸림)" + _NOT_NOW + r")"
    r"|(?<!안 )(?<!못 )(?<!안)(?<!못)걸어\s*(?:둠|뒀|놨|둔|논|놓은)|(?<!안 )(?<!못 )(?<!안)(?<!못)걸었" + _NOT_NOW +
    r"|(?<!안 )(?<!못 )걸림"
    r"|(?<!안 )(?<!못 )(?<!안)(?<!못)걸려\s*있(?!지\s*않|진\s*않|는지|던|었던)"
    r"|OPEN\s*(?:에\s*)?확인(?!\s*(?:필요|대기|예정|안|못|요망|전))"
    r"|주문\s*들어가\s*있(?!지\s*않|진\s*않|는지)"
    r"|^[^0-9A-Za-z가-힣]*예약(?=\s*(?:$|접수(?!\s*(?:대기|예정|전))|\((?![^)]*(?:대기|(?:접수|등록|예약)\s*예정))|—|·|-|,))"
    r"|(?:^|—\s*)[^0-9A-Za-z가-힣]*(?:\d{1,2}/\d{1,2}\s*)?재(?:등록|접수)(?=\s*(?:$|\(|—|·|,))"
    r"(?!\s*—\s*(?:안|못|미|보류|중지|[^—·]*(?:대기|예정)))"
    r"|생존\(|커버됨")


def reg_claim(st: str) -> bool:
    """상태 문장이 '토스에 걸려 있다'고 말하나 — 인용부호 안(舊 표기·정훈 말 인용)은 뺀다."""
    return bool(REG_CLAIM.search(_QUOTED.sub("", st or "")))


def _load(path, default=None):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _side(action: str) -> str | None:
    a = action or ""
    if "매도" in a or "익절" in a or "트림" in a:
        return "SELL"
    if "매수" in a:
        return "BUY"
    return None


def plan_state(o: dict) -> str:
    st = _QUOTED.sub("", str(o.get("status") or ""))     # ★[10/22 리뷰 3차] 인용(舊 표기·정훈 말)은 먼저 뺀다 — 뒤 구절도
    head = _HEAD_CUT.split(_LEAD_WARN.sub("", st), maxsplit=1)[0]
    clauses = [head] + _TERMINAL_CLAUSE.findall(st)
    if any(DEAD.search(PLACED_DONE.sub("", c)) for c in clauses):
        return "dead"
    if HOLD.search(st):
        return "hold"
    return "active"


def known_tickers(tasks: dict, stocks: dict) -> list[str]:
    tk = {str(o.get("ticker") or "") for o in tasks.get("orders", [])}
    for grp in ("stocks", "watchlist", "watch"):
        tk.update((stocks.get(grp) or {}).keys())
    return sorted(t for t in tk if t)


def normalize(sym: str, known: list[str]) -> str:
    """토스 심볼(국내 '035420', 미국 'NVDA') → 우리 티커. 접미사는 아는 티커에서 찾는다(.KS/.KQ 혼동 금지)."""
    if re.fullmatch(r"\d{6}", sym or ""):
        for t in known:
            if t.split(".")[0] == sym:
                return t
        return sym + ".KS"
    return sym


def is_kr(t: str) -> bool:
    return bool(re.search(r"\.(KS|KQ)$", t))


def band_note(bb: dict) -> str:
    """기준가 표기 — '기준 {날짜} 종가 → {세션} 세션', 폴백이면 무엇이 빠졌는지까지."""
    ss = dt.date.fromisoformat(bb["session"])
    s = f"기준 {bb['date']} 종가 → {ss.month}/{ss.day} 세션"
    return s + (f" ⚠️{bb['want']} 종가 미확보" if bb["stale"] else "")


def kr_weight() -> float | None:
    snaps = sorted(f for f in os.listdir(SNAPS) if f.endswith(".json")) if os.path.isdir(SNAPS) else []
    if not snaps:
        return None
    s = _load(os.path.join(SNAPS, snaps[-1]), {}) or {}
    try:
        kr = float(s["kr_value"]); us = float(s["us_value_usd"]) * float(s["fx_usdkrw"])
    except (KeyError, TypeError, ValueError):
        return None
    return kr / (kr + us) * 100 if kr + us else None


def ladder_allowed() -> float | None:
    try:
        last = [ln for ln in open(RULE_LOG, encoding="utf-8").read().splitlines() if ln.strip()][-1]
        return float(json.loads(last).get("allowed_krw"))
    except (OSError, IndexError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _same_price(tk: str, a: float, b: float) -> bool:
    if a is None or b is None:
        return False
    if is_kr(tk):
        from validate_report import _kr_tick
        return abs(a - b) < _kr_tick(max(a, b))
    return abs(a - b) <= max(0.01, 0.005 * max(a, b))


def us_track_state(now: dt.datetime | None = None) -> dict | None:
    """★[9/21 d205] 미국 트랙 — 달러로 사는 미국주는 코스피 사다리가 아니라 3회 분할 규칙이 다룬다.
    ★[10/22 리뷰 반영] ⓐ 하드플로어도 본다(舊 check_floor=False → 플로어 중에도 '재등록 필요'를 냈다 · d235 = 걸려 있으면 취소)
      ⓑ --now(재현)면 그 시각의 KST 날짜·美 세션일로 판정한다(舊 = 벽시계 — 재현이 다른 답을 냈다)."""
    try:
        import tranche_rules as TR
        if now is None:
            return TR.us_track(check_floor=True)
        return TR.us_track(today=now.astimezone(KST).date().isoformat(), check_floor=True,
                           session_day=TR.us_session_of(now.isoformat())[0])
    except Exception as e:  # noqa: BLE001
        # ★[10/22 리뷰 2차] 판정 실패 = 'error'로 낸다(舊 None → 미국 매수 게이트가 전부 꺼져 fail-open이었다)
        return {"status": "error", "allowed_usd": 0.0, "why": f"미국 트랙 판정 실패({type(e).__name__}: {str(e)[:60]})"}


def us_block(us: dict | None, ticker: str | None = None, price=None) -> str | None:
    """★[10/22 리뷰 반영 — d251] 미국 매수가 지금 막혀 있으면 그 이유(tranche_rules.us_buy_block과 같은 판정).
    ticker·price를 주면 진행 중 회차에서 그 종목을 다시 걸어도 되는지까지 본다(이미 산 종목·다른 존 종목·잔액보다 비싼 1주).
    us가 없으면(트랙을 안 본 호출) None — 막혔다고 지어내지 않는다. 판정 실패는 us_track_state가 'error'로 준다."""
    if not us:
        return None
    try:
        import tranche_rules as TR
        return TR.us_buy_block(us, ticker, price)
    except Exception as e:  # noqa: BLE001
        return f"미국 트랙 판정 실패({type(e).__name__}) — 매수 판단 보류"


def check(open_orders: list[dict], tasks: dict, stocks: dict,
          kr_w: float | None, allowed: float | None, us: dict | None = None,
          now: dt.datetime | None = None) -> dict:
    # ★[9/22] 기준가 = validate_report.kr_band_base(check_kr_price_band와 같은 함수) — 舊 last_close()는
    #   history 캐시·live.json만 봐서 마감 후에도 전일 종가를 썼다(9/22 22:01 현대차 상한 466,500 vs 실제 468,500).
    from validate_report import _kr_band, kr_band_base
    now = now or dt.datetime.now(KST)
    known = known_tickers(tasks, stocks)
    plans = [o for o in tasks.get("orders", []) if _side(o.get("action", ""))]
    stars = {t: (v or {}).get("stars") for g in ("stocks", "watchlist", "watch")
             for t, v in (stocks.get(g) or {}).items()}
    held = set((stocks.get("stocks") or {}).keys())
    try:
        from performance import names
        nm = names()
    except Exception:  # noqa: BLE001 — 이름은 표시용일 뿐, 대조를 막지 않는다
        nm = {}
    rows, findings = [], []

    def add(level, tk, msg):
        findings.append({"level": level, "ticker": tk, "msg": msg})

    for o in open_orders:
        tk = normalize(str(o.get("symbol") or ""), known)
        side = str(o.get("side") or "").upper()
        price = float(o["price"]) if o.get("price") not in (None, "") else None
        qty = o.get("quantity")
        cand = [p for p in plans if p.get("ticker") == tk and _side(p.get("action", "")) == side
                and _same_price(tk, price, p.get("price"))]
        act = [p for p in cand if plan_state(p) == "active"]
        match = (act or cand or [None])[0]
        state = plan_state(match) if match else "none"
        row = {"ticker": tk, "side": side, "price": price, "qty": qty,
               "ordered_at": o.get("orderedAt"), "plan_id": match.get("id") if match else None,
               "plan_state": state}
        rows.append(row)
        verb = "매수" if side == "BUY" else "매도"
        lb = nm.get(tk, tk)
        what = f"{lb} {verb} {price:,.0f} × {qty}" if price else f"{lb} {verb} × {qty}"

        if state in ("dead", "hold"):
            add("red" if side == "BUY" else "yellow", tk,
                f"{what} — 계획상 '{match['status'][:40]}'인 오더({match['id']})와 같은 주문이 살아 있다")
        elif state == "none":
            add("red" if side == "BUY" else "yellow", tk, f"{what} — 계획(tasks.json)에 없는 주문")
        if side == "BUY":
            st = stars.get(tk)
            if st is not None and st <= 2 and tk in held:
                add("red", tk, f"{what} — ⭐{st} 보유 종목 추가매수(⭐2 이하 = 트림 또는 기한부 홀드)")
            if is_kr(tk) and kr_w is not None and kr_w > KR_CAP_PCT:
                add("red", tk, f"{what} — 룰6: 국내 {kr_w:.1f}% > 상단 {KR_CAP_PCT:.0f}% 동안 신규 자금은 100% 미국")
            # d205: 사다리(국내 트랙)는 국내 매수만 본다. 미국 매수는 미국 트랙 회차가 본다.
            if is_kr(tk) and allowed is not None and allowed <= 0 and state != "active":
                add("yellow", tk, f"{what} — 국내 트랙 이번 회차 0원(계획된 예외가 아니면 재원이 없다)")
            if (not is_kr(tk)) and us and state != "active" and (us.get("allowed_usd") or 0) <= 0:
                add("yellow", tk, f"{what} — 미국 트랙 이번 회차 없음({us.get('why', '')[:60]})")
            elif (not is_kr(tk)) and state == "active" and (ub := us_block(us, tk, price)):
                # 계획엔 살아 있어도 d251 대기·하드플로어·이 회차에 이미 산 종목이면 지금 걸린 매수는 규칙을 넘는다
                add("yellow", tk, f"{what} — {ub}인데 매수 주문이 걸려 있다(체결되면 위반 — 취소 검토)")
        if is_kr(tk) and price:
            bb = kr_band_base(tk, now)
            if bb:
                up, lo = _kr_band(bb["base"])
                row["band"] = [lo, up]
                row["band_base"] = {k: bb[k] for k in ("date", "base", "src", "session", "stale")}
                if not (lo <= price <= up):
                    add("yellow", tk, f"{what} — 가격제한폭 {lo:,}~{up:,}({band_note(bb)} {bb['base']:,.0f}) 밖 → 접수 거부/무효")
        if not any(f["ticker"] == tk and f["msg"].startswith(what) for f in findings):
            add("ok", tk, f"{what} — 계획({match['id']})과 일치" if match else what)

    # '매일 등록' 오더가 빠졌나 — 접수 가능한 가격인데 OPEN에 없으면 미등록
    for p in plans:
        if p.get("register_policy") != "always" or plan_state(p) != "active":
            continue
        tk, side, price = p.get("ticker"), _side(p.get("action", "")), p.get("price")
        if any(r["ticker"] == tk and r["side"] == side and _same_price(tk, r["price"], price) for r in rows):
            continue
        verb = "매수" if side == "BUY" else "매도"
        lb = nm.get(tk, tk)
        if side == "BUY" and not is_kr(tk) and (ub := us_block(us, tk, price)):
            add("info", tk, f"{lb} {verb} ${float(price):,.2f} 미등록 — 정상({ub} · 지금 걸면 위반)")
            continue
        if is_kr(tk) and price:
            bb = kr_band_base(tk, now)
            if bb:
                up, lo = _kr_band(bb["base"])
                if not (lo <= float(price) <= up):
                    edge = f"상한 {up:,} < 주문가" if float(price) > up else f"하한 {lo:,} > 주문가"
                    add("info", tk, f"{lb} {verb} {float(price):,.0f} 미등록 — 정상({edge}, {band_note(bb)})")
                    continue
        add("yellow", tk, f"{lb} {verb} {float(price):,.0f} '매일 등록' 오더가 토스에 없다({p['id']}) — 재등록 필요")

    # ★[10/21 d244] '매일 등록' 밖 계획 오더 — 걸려 있어야 하는 오더가 OPEN에 없으면 🟡
    #   ⓐ 상태가 접수·등록을 주장(REG_CLAIM) ⓑ 방식ⓑ(b_line) 오더의 등록선이 점등(기준 종가가 register_line 통과)
    #   제외: 등록선 대기(점등 전) · 조건부·판정 대기 · 알림 방식 · 가격 없음 · 지수(^) · 보류·종결
    excluded = 0
    for p in plans:
        if p.get("register_policy") == "always" or plan_state(p) != "active":
            continue
        tk, side, price = str(p.get("ticker") or ""), _side(p.get("action", "")), p.get("price")
        if not isinstance(price, (int, float)) or tk.startswith("^"):
            continue
        if any(r["ticker"] == tk and r["side"] == side and _same_price(tk, r["price"], price) for r in rows):
            continue
        verb = "매수" if side == "BUY" else "매도"
        lb = nm.get(tk, tk)
        st = str(p.get("status") or "")
        why = None
        if side == "BUY" and not is_kr(tk) and us_block(us, tk, price):
            excluded += 1                       # d251 대기·하드플로어·이 회차 체결 종목 — 안 걸려 있는 게 맞다
            continue
        if reg_claim(st):
            why = f"상태 '{st[:30]}'는 걸려 있다는 뜻인데 토스에 없다 — 미접수 또는 1거래일 소멸(d128) → 재등록하거나 상태 갱신"
        elif p.get("register_policy") == "b_line":
            ln = p.get("register_line") or {}
            bb = kr_band_base(tk, now) if is_kr(tk) else None
            lvl, cond = ln.get("level"), ln.get("cond", "above")
            if bb and isinstance(lvl, (int, float)):
                hit = bb["base"] >= lvl if cond == "above" else bb["base"] <= lvl
                if hit:
                    why = (f"등록선 {lvl:,.0f} 점등(기준 {bb['date']} 종가 {bb['base']:,.0f}) — 방식ⓑ면 오늘 등록해야 하는데 토스에 없다")
            elif not isinstance(lvl, (int, float)):
                add("info", tk, f"{lb} {verb} {float(price):,.0f} 방식ⓑ인데 register_line이 없어 점등을 못 본다({p['id']})")
        if why:
            add("yellow", tk, f"{lb} {verb} {float(price):,.0f} — {why} ({p['id']})")
        else:
            excluded += 1

    lv = [f["level"] for f in findings]
    return {"checked_at": now.astimezone(KST).strftime("%Y-%m-%d %H:%M"),
            "source": "toss", "open": rows, "findings": findings,
            "counts": {k: lv.count(k) for k in ("red", "yellow", "ok", "info")},
            "context": {"kr_weight_pct": round(kr_w, 1) if kr_w is not None else None,
                        "ladder_allowed_krw": allowed,
                        "us_allowed_usd": (us or {}).get("allowed_usd"),
                        "waiting_plans": excluded}}


ICON = {"red": "🔴", "yellow": "🟡", "ok": "✅", "info": "ℹ️"}


def _usd(v) -> str:
    return "미확인" if v is None else f"${float(v):,.2f}"


def _won(v) -> str:
    return "미확인" if v is None else f"{float(v):,.0f}원"


def render(r: dict) -> str:
    if r.get("source") == "unavailable":
        return "⚠️ 토스 조회 불가(키 없음·인증 실패) — **대조 미실행**. '주문 없음'이 아니다."
    L = [f"=== 토스 미체결 ↔ 계획 대조 ({r['checked_at']}) — 미체결 {len(r['open'])}건 ==="]
    for lvl in ("red", "yellow", "ok", "info"):
        for f in r["findings"]:
            if f["level"] == lvl:
                L.append(f"{ICON[lvl]} {f['msg']}")
    c = r["counts"]
    L.append(f"\n🔴 {c['red']} · 🟡 {c['yellow']} · ✅ {c['ok']}  (국내 비중 {r['context']['kr_weight_pct']}% · 국내 트랙 회차 {_won(r['context']['ladder_allowed_krw'])} · 미국 회차 {_usd(r['context'].get('us_allowed_usd'))})")
    if c["red"]:
        L.append("→ 🔴 주문은 정훈이 토스에서 직접 취소·정정(주문 API 호출 금지).")
    return "\n".join(L)


def selftest() -> int:
    """가격제한폭 기준가 회귀 테스트 — 임시 ROOT 픽스처 + --file 경로(OPEN 목록 직접 주입)로 시각별 판정을 고정한다.

    ★[9/22 실사고] 22:01 현대차 470,000 미등록 판정이 '상한 466,500, 기준 2026-09-21 종가'로 나왔다.
    9/22 종가 360,500(quotes.jsonl 16:04 적재)가 있었으니 9/23 세션 상한은 468,500이어야 했다.
    픽스처 = 그날 실제 값(9/21 종가 359,000 · 9/22 종가 360,500 · 추석 9/24~25 휴장).
    """
    import shutil
    import tempfile
    import validate_report as V

    tk, hist = "005380.KS", "data/history/005380.KS.csv"
    h = lambda d, hm: dt.datetime.fromisoformat(f"{d}T{hm}:00+09:00")  # noqa: E731
    files = {
        hist: "date,close\n2026-09-18,365000.0\n2026-09-21,359000.0\n",
        "data/timeseries/quotes.jsonl": "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in [
            {"date": "2026-09-21", "ts": "2026-09-21T16:25:27+09:00", "symbol": tk, "price": 359000.0},
            {"date": "2026-09-22", "ts": "2026-09-22T11:00:00+09:00", "symbol": tk, "price": 358000.0},  # 장중
            {"date": "2026-09-22", "ts": "2026-09-22T16:04:41+09:00", "symbol": tk, "price": 360500.0},
            {"date": "2026-07-20", "ts": "2026-07-20", "symbol": tk, "price": 1.0},                     # 소급분(시각 없음)
        ]),
        # 로컬 실시간층 — 9/21 21:29에 멈춘 상태 그대로. p(애프터마켓 361,500)는 기준가가 아니다.
        "app/live.json": json.dumps({"quotes": {tk: {"p": 361500.0, "rc": 359000.0,
                                                    "rt": int(h("2026-09-21", "15:30").timestamp()) + 8}}}),
        "data/app/macro_events.json": json.dumps({"events": [
            {"date": "2026-09-24", "end": "2026-09-25", "kind": "휴장", "name": "추석"}]}, ensure_ascii=False),
    }
    tmp = tempfile.mkdtemp(prefix="order_check_selftest_")
    old_root, ok = V.ROOT, True

    def expect(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'✅' if good else '❌'} {label}: {got}" + ("" if good else f"  (기대 {want})"))

    def base(now):
        bb = V.kr_band_base(tk, now)
        return bb and (bb["date"], bb["base"], bb["session"], bb["stale"])

    try:
        for rel, body in files.items():
            p = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(body)
        V.ROOT = tmp
        print("order_check 가격제한폭 기준가 selftest")
        expect("9/22 22:01 마감 후 → 오늘 종가", base(h("2026-09-22", "22:01")),
               ("2026-09-22", 360500.0, "2026-09-23", False))
        expect("9/22 15:38 마감 직후·적재 전 → 전일 종가 폴백 + stale", base(h("2026-09-22", "15:38")),
               ("2026-09-21", 359000.0, "2026-09-23", True))
        expect("9/22 11:00 장중 → 전일 종가(장중 358,000 제외)", base(h("2026-09-22", "11:00")),
               ("2026-09-21", 359000.0, "2026-09-22", False))
        expect("9/22 07:30 프리마켓 → 전일 종가", base(h("2026-09-22", "07:30")),
               ("2026-09-21", 359000.0, "2026-09-22", False))
        expect("9/23 22:00 오늘 종가 없음 → 폴백 + stale(세션 = 추석 뒤 9/28)", base(h("2026-09-23", "22:00")),
               ("2026-09-22", 360500.0, "2026-09-28", True))
        expect("9/26(토) → 9/28 세션", base(h("2026-09-26", "10:00"))[2], "2026-09-28")

        # --file 경로: OPEN 목록 직접 주입 → 실제 판정 문구(기준일 병기)까지 본다
        tasks = {"orders": [{"id": "o-hmc-470k", "ticker": tk, "action": "트림 매도 지정가", "price": 470000,
                             "status": "매일 등록", "register_policy": "always"}]}
        r = check([], tasks, {}, None, None, None, now=h("2026-09-22", "22:01"))
        msg = next((f["msg"] for f in r["findings"] if f["ticker"] == tk), "")
        expect("미등록 판정 문구", ("상한 468,500" in msg, "기준 2026-09-22 종가" in msg, "9/23 세션" in msg),
               (True, True, True))
        r = check([{"symbol": "005380", "side": "SELL", "price": "470000", "quantity": "1"}],
                  tasks, {}, None, None, None, now=h("2026-09-22", "22:01"))
        row, f0 = r["open"][0], r["findings"][0]
        expect("OPEN 주문 밴드", (row["band"][1], f0["level"], "기준 2026-09-22 종가" in f0["msg"]),
               (468500, "yellow", True))

        # 10/19 — '미체결'은 살아 있는 오더다('체결'로 읽으면 역방향 검사에서 빠진다) · 미국 '매일 등록'도 본다
        expect("plan_state 미체결 = active", plan_state({"status": "등록 — 미체결이면 매 거래일 재등록"}), "active")
        expect("plan_state 체결 = dead", plan_state({"status": "체결 10/19"}), "dead")
        us_tasks = {"orders": [{"id": "o-anet", "ticker": "ANET", "action": "매수", "price": 182,
                                "status": "등록 — 미체결이면 매 거래일 재등록", "register_policy": "always"}]}
        r = check([], us_tasks, {}, None, None, None, now=h("2026-10-19", "22:40"))
        expect("미국 매일 등록 미등록 → yellow", [f["level"] for f in r["findings"] if f["ticker"] == "ANET"], ["yellow"])

        # 10/21 d244 — '매일 등록' 밖 계획 오더: 상태가 걸었다고 주장하거나 등록선이 점등했는데 OPEN에 없으면 🟡
        expect("plan_state 접수완료 = active(살아 있는 오더)", plan_state({"status": "접수완료(8/19 18:49)"}), "active")
        expect("plan_state 환전 완료 = dead", plan_state({"status": "✅ 완료 확인 — 환전"}), "dead")
        now0 = h("2026-09-22", "22:01")

        def lv_of(o):
            r_ = check([], {"orders": [dict(o, id="o-x", ticker=tk, action="매도", price=470000)]}, {}, None, None, None, now=now0)
            return [f["level"] for f in r_["findings"] if f["ticker"] == tk]
        expect("상태 '9/22분 등록 확인' + OPEN 없음 → yellow", lv_of({"status": "9/22분 등록 확인"}), ["yellow"])
        expect("상태 '접수완료' + OPEN 없음 → yellow", lv_of({"status": "접수완료"}), ["yellow"])
        expect("'재등록 권고'는 걸었다는 말이 아니다 → 무발견", lv_of({"status": "미체결 만료 → 오늘 밤 재등록 권고"}), [])
        expect("조건부·판정 대기 → 무발견", lv_of({"status": "조건부 — 10/29 판정 대기"}), [])
        expect("방식ⓑ 등록선 점등(기준 360,500 ≥ 350,000) → yellow",
               lv_of({"status": "계획", "register_policy": "b_line", "register_line": {"level": 350000, "cond": "above"}}), ["yellow"])
        expect("방식ⓑ 등록선 대기(기준 360,500 < 400,000) → 무발견(제외)",
               lv_of({"status": "계획", "register_policy": "b_line", "register_line": {"level": 400000, "cond": "above"}}), [])
        expect("방식ⓑ인데 register_line 없음 → info",
               lv_of({"status": "계획", "register_policy": "b_line"}), ["info"])
        r = check([{"symbol": "005380", "side": "SELL", "price": "470000", "quantity": "1"}],
                  {"orders": [{"id": "o-x", "ticker": tk, "action": "매도", "price": 470000, "status": "9/22분 등록 확인"}]},
                  {}, None, None, None, now=now0)
        expect("OPEN에 있으면 역방향 무발견", [f["level"] for f in r["findings"] if f["ticker"] == tk], ["yellow"])  # 밴드 밖 정방향 🟡 하나뿐

        # 10/22 리뷰 — 실제 tasks.json 이력 문구. '체결 대기'는 종결이 아니고, '안 걸었음'은 걸었다는 말이 아니다
        for st_, want in [("예약 접수 완료 — 체결 대기", "active"), ("등록 완료 · 익일 체결확률 15.7%", "active"),
                          ("✅ 등록 확인 완료(토스 10/22)", "active"), ("체결되면 VOO", "active"),
                          ("예약주문 완료", "active"), ("체결 완료", "dead"), ("매도 완료", "dead"),
                          ("예약 중지", "hold")]:
            expect(f"plan_state '{st_}'", plan_state({"status": st_}), want)
        for st_, want in [("10/22 재등록 완료", ["yellow"]), ("접수됐다", ["yellow"]), ("예약", ["yellow"]),
                          ("🎯 $312로 하향 — 8/13 재접수", ["yellow"]), ("아직 안 걸었음", []), ("못 걸었다", []),
                          ("오늘 밤 예약 걸 예정", []), ("등록 확인 필요", [])]:
            expect(f"역방향 '{st_}'", lv_of({"status": st_}), want)

        # 10/22 리뷰 2차 — tasks.json 이력의 **실제 전체 문장**(줄인 형태가 아니라) — 해설이 상태를 바꾸면 안 된다
        real = [
            ("✅ **예약 접수 완료**(정훈 2026-08-23 15:10 직접 접수) — 470,000원·정수 1주. ⚠️생존 재확인 주기 = 매 보고서. 즉시체결도 가능.", "active", True),
            ("✅ **등록 완료(정훈 8/27 19:5x 폰창 확인 '오케이 걸었음')** — 78,000원 1주 판매 지정가 = **전량청산**. 기저율상 익일 체결확률 **15.7%**", "active", True),
            ("🟡 **예약 접수(정훈 8/24 20:0x 폰창)** — 22:30 미장 개장 시장가 집행 예정. ⚠️룰5: 체결가·주수·수수료 확인 전 '완료' 처리 금지 → 8/25 첫 세션 첫 단계에서 체결 검토.", "active", True),
            ("🔴 **재설계 완료 — 오늘 폰창(17:30~20:50) 예약등록 대상**. 舊 90,000원은 도달 불가", "active", False),
            ("예약 대기(입금 확인 완료·정훈 폰창 집행)", "active", False),
            ("체결확인대기", "active", False),
            ("🚨 [9/2 v88 갱신] **5거래일째 체결 미확인 — 룰5 위반 소지.**", "active", False),
            ("⚠️ 재등록 필요 — 8/21 정훈 실측으로 대기주문 부재/불명 확인. 舊 '✅접수완료'는 **8/19 18:49 스냅샷**이었다", "active", False),
            ("오늘 밤(10/19) 등록 — 지정가 $182 1주 · 미체결이면 매 거래일 재등록(d128)", "active", False),
            ("🟢 **생존(8/25 08:50 만료)** — 오늘 밤 미장(22:30~) 커버됨.", "active", True),
            ("⚪ 대체됨(9/21 d205) — 미국 트랙으로 이관", "dead", False),
            ("건너뜀", "dead", False),
            ("동결(안전핀)", "hold", False),
            ("⏸ d151 결정 대기", "hold", False),
            ("⚪ 미체결 확정(취소) — 정훈 8/3 원화 327,970원 개인 인출로 재원 소진", "dead", False),
            ("✅ 확인 완료 — 둘 다 미체결(취소), 8/3 원화 인출이 원인", "dead", False),
            ("⛔ 폐기 · ✅ 토스 취소 확인(9/21 22:36:51 — order_check·토스 CLOSED 조회)", "dead", False),
            ("오늘 밤 등록 — ✅ 체결 10/23 01:10", "dead", False),
        ]
        for st_, want, claim in real:
            expect(f"실제 문장 '{st_[:28]}…'", (plan_state({"status": st_}), reg_claim(st_)), (want, claim))

        # 10/22 리뷰 — d251 대기 중이면 미국 매수는 '안 걸려 있는 게 정상'이고, 걸려 있으면 그게 🟡다
        wait = {"status": "spacing_wait", "allowed_usd": 0.0, "wait_until": "2026-11-21", "why": "월 1회차(d251)"}
        due = {"status": "due", "allowed_usd": 74.0, "wait_until": None, "why": "회차 2 도래"}
        nowu = h("2026-10-22", "22:40")
        r = check([], us_tasks, {}, None, None, wait, now=nowu)
        expect("d251 대기 + '매일 등록' 미등록 → info(재등록 권고 안 함)",
               [(f["level"], "d251" in f["msg"]) for f in r["findings"] if f["ticker"] == "ANET"], [("info", True)])
        r = check([], us_tasks, {}, None, None, due, now=nowu)
        expect("회차 도래 + 미등록 → yellow(그대로)", [f["level"] for f in r["findings"] if f["ticker"] == "ANET"], ["yellow"])
        r = check([{"symbol": "ANET", "side": "BUY", "price": "182", "quantity": "1"}], us_tasks, {}, None, None, wait, now=nowu)
        expect("d251 대기인데 매수 OPEN → yellow",
               [(f["level"], "d251" in f["msg"]) for f in r["findings"] if f["ticker"] == "ANET"], [("yellow", True)])
        r = check([{"symbol": "ANET", "side": "BUY", "price": "182", "quantity": "1"}], us_tasks, {}, None, None, due, now=nowu)
        expect("회차 도래 + 매수 OPEN → ok", [f["level"] for f in r["findings"] if f["ticker"] == "ANET"], ["ok"])
        r = check([], {"orders": [dict(us_tasks["orders"][0], register_policy=None, status="예약 접수 완료")]},
                  {}, None, None, wait, now=nowu)
        expect("d251 대기 + 비'매일 등록' 접수 주장 → 무발견(대기 집계)",
               ([f["level"] for f in r["findings"] if f["ticker"] == "ANET"], r["context"]["waiting_plans"]), ([], 1))
        # ★[10/22 리뷰 2차] 진행 중 회차 — ANET 1주가 이미 체결됐으면 'ANET 매일 등록'을 다시 걸라고 하지 않는다
        part = {"status": "partial", "allowed_usd": 181.69, "partial_tranche": 2, "partial_left": 181.69,
                "partial_tickers": ["ANET"], "why": "2회차 진행 중"}
        r = check([], us_tasks, {}, None, None, part, now=nowu)
        expect("partial(ANET 체결) + ANET 매일 등록 미등록 → info(재등록 권고 안 함)",
               [(f["level"], "이미 체결" in f["msg"]) for f in r["findings"] if f["ticker"] == "ANET"], [("info", True)])
        r = check([{"symbol": "ANET", "side": "BUY", "price": "182", "quantity": "1"}], us_tasks, {}, None, None, part, now=nowu)
        expect("partial(ANET 체결) + ANET 매수 OPEN → yellow(같은 회차 2주째)",
               [f["level"] for f in r["findings"] if f["ticker"] == "ANET"], ["yellow"])
        part_v = dict(part, partial_tickers=["VOO"], partial_left=60.0)
        r = check([], us_tasks, {}, None, None, part_v, now=nowu)
        expect("partial(잔액 $60) + ANET 1주 $182 미등록 → info(1주 > 잔액)",
               [(f["level"], "잔액" in f["msg"]) for f in r["findings"] if f["ticker"] == "ANET"], [("info", True)])
        err = {"status": "error", "allowed_usd": 0.0, "why": "미국 트랙 판정 실패(IndexError: x)"}
        r = check([], us_tasks, {}, None, None, err, now=nowu)
        expect("판정 실패(error) → 재등록 권고 안 함(fail-closed)",
               [(f["level"], "보류" in f["msg"]) for f in r["findings"] if f["ticker"] == "ANET"], [("info", True)])
        # 분류기 — 부정·실패·확인 문형(10/22 리뷰 3차)
        for st_, want, claim in [("⚠️ 폐기(9/21) — 앱 오표시로 토스에 접수됨 → 정훈 취소 필요", "dead", True),
                                 ("오늘 밤 등록 — 체결 10/23 01:10", "dead", False),
                                 ("✅ 체결된 것 확인(토스 API 10/23 01:10)", "dead", False),
                                 ("체결가 $182.18 확인", "dead", False),
                                 ("❌ 체결 실패(10/22 고가 $181 < $182) → 오늘 밤 재등록", "active", False),
                                 ("체결 안 됨 — 오늘 밤 재등록", "active", False),
                                 ("oo에 등록돼 있지 않음(10/22 조회) — 방식ⓑ 등록선 228,000 미점등 대기", "active", False),
                                 ("재등록 — 안 함(등록선 미점등)", "active", False),
                                 ("등록했던 오더 만료", "active", False),
                                 ("등록됐는지 미확인", "active", False),
                                 ("등록 확인 못 함", "active", False)]:
            expect(f"문형 '{st_[:24]}…'", (plan_state({"status": st_}), reg_claim(st_)), (want, claim))
        # 분류기 — 조건·미래·금지형 체결/취소(C0) · 조건형 중지·해제(C1) · 걸려 있지 않은 말(C3) · 걸려 있는 말(C4)
        for st_, want, claim in [("오늘 밤 등록 — 체결 후 잔액 VOO", "active", False), ("체결되지 않으면 VOO", "active", False),
                                 ("체결 전까지 매일 재등록", "active", False), ("체결이 안 되면 내일 재등록", "active", False),
                                 ("체결까지 매일 등록", "active", False), ("체결 기대 — 지정가 $182", "active", False),
                                 ("체결 확인 예정(내일 아침 토스)", "active", False), ("체결 확인은 내일 아침", "active", False),
                                 ("체결 소식 없음 — 토스 확인 필요", "active", False), ("취소 시 VOO로", "active", False),
                                 ("취소하지 말 것 — 매일 등록 유지", "active", False), ("취소 금지(d235)", "active", False),
                                 ("취소 안 함 — 내일 재등록", "active", False), ("등록 — 하드플로어면 중지", "active", False),
                                 ("보류 해제 — 오늘 밤 등록", "active", False), ("예약 접수 대기", "active", False),
                                 ("예약(정훈 결정 대기)", "active", False), ("재등록 — 정훈 결정 대기", "active", False),
                                 ("등록 확인 예정", "active", False), ("접수됐으나 만료(d128)", "active", False),
                                 ("등록됐다가 소멸", "active", False), ("점등 시 등록함", "active", False),
                                 ("걸려 있지 않음 — 재등록 필요", "active", False), ("안 걸려 있음", "active", False),
                                 ("OPEN 확인 필요", "active", False), ("주문 들어가 있지 않음", "active", False),
                                 ("토스에 걸려 있음(10/22)", "active", True), ("걸어 둔 지정가 $182", "active", True),
                                 ("토스 OPEN 확인(10/22 21:00)", "active", True), ("주문 들어가 있음", "active", True),
                                 ("🟡 예약(정훈 폰창 접수, 22:30 미장 개장 시 체결 예정)", "active", True),
                                 ("체결 확인(토스 10/23)", "dead", False), ("취소됨", "dead", False),
                                 ("취소 권고 — 토스에 걸려 있음", "dead", True), ("⏸ 보류 — 정훈 결정", "hold", False),
                                 ("매수 보류(d192)", "hold", False)]:
            expect(f"문형 '{st_[:24]}…'", (plan_state({"status": st_}), reg_claim(st_)), (want, claim))

        # 캐시 오염(8/13) — history에 장중값이 오늘 종가로 박혀 있어도 시각 있는 확정 종가가 이긴다
        with open(os.path.join(tmp, hist), "a", encoding="utf-8") as f:
            f.write("2026-09-22,358000.0\n")
        expect("history 장중 오염 vs quotes 확정", base(h("2026-09-22", "22:01"))[:2], ("2026-09-22", 360500.0))
        expect("장중엔 오염 행도 제외", base(h("2026-09-22", "11:00"))[:2], ("2026-09-21", 359000.0))
        # quotes·live가 없으면 history 폴백 — 기준일이 그대로 드러나야 한다
        os.remove(os.path.join(tmp, "data/timeseries/quotes.jsonl"))
        os.remove(os.path.join(tmp, "app/live.json"))
        with open(os.path.join(tmp, hist), "w", encoding="utf-8") as f:
            f.write(files[hist])
        expect("history만 → 9/21 폴백 + stale", base(h("2026-09-22", "22:01")),
               ("2026-09-21", 359000.0, "2026-09-23", True))
    finally:
        V.ROOT = old_root
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS" if ok else "FAIL — 기준가 선택이 회귀했다")
    return 0 if ok else 1


def _parse_now(s: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(s.replace(" ", "T"))
    return t.replace(tzinfo=KST) if t.tzinfo is None else t


def main() -> int:
    ap = argparse.ArgumentParser(description="토스 미체결 주문 ↔ tasks.json 계획 대조 (조회 전용)")
    ap.add_argument("--file", help="OPEN 주문 JSON(리스트 또는 toss_snapshot --orders 출력)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-save", action="store_true", help="data/app/order_check.json을 안 쓴다(테스트용)")
    ap.add_argument("--now", type=_parse_now, help="판정 시각 고정(KST, 예: '2026-09-22 22:01') — 재현용")
    ap.add_argument("--selftest", action="store_true", help="가격제한폭 기준가 회귀 테스트(임시 ROOT 픽스처)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    if a.file:
        raw = _load(a.file)
        opens = raw.get("orders", []) if isinstance(raw, dict) else (raw or [])
        src = "file"
    else:
        import toss_snapshot
        opens = toss_snapshot.fetch_orders("OPEN")
        src = "toss"
    if opens is None:
        r = {"checked_at": (a.now or dt.datetime.now(KST)).strftime("%Y-%m-%d %H:%M"), "source": "unavailable",
             "open": [], "findings": [], "counts": {"red": 0, "yellow": 0, "ok": 0, "info": 0}}
    else:
        r = check([o for o in opens if str(o.get("status", "PENDING")).upper() != "CANCELED"],
                  _load(TASKS, {}) or {}, _load(STOCKS, {}) or {}, kr_weight(), ladder_allowed(),
                  us_track_state(a.now), now=a.now)
        r["source"] = src
    # unavailable(토스 미접근)은 저장하지 않는다 — 안 그러면 마지막 실제 대조 결과를 빈 값으로 덮어쓴다(9/23 클라우드 실사고).
    if not a.no_save and src != "file" and r["source"] != "unavailable":
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
            f.write("\n")
    print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else render(r))
    return 1 if r["counts"]["red"] else (2 if r["source"] == "unavailable" else 0)


if __name__ == "__main__":
    sys.exit(main())
