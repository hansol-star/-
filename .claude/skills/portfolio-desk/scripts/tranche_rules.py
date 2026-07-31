#!/usr/bin/env python3
"""tranche_rules.py — 개정 리스크룰 1·2 판정기 (stdlib only)

정훈 승인(2026-07-30 "응 하자 룰도 다 바꾸자"). 낙폭연구(`drawdown_study_2026-07-30.md`)가
드러낸 기존 룰의 두 결함을 고친 **개정 룰의 기계 판정기**.

═══ 무엇이 왜 바뀌었나 ═══

■ 룰 1 (안전핀) — **이진 스위치 → 낙폭 사다리**
   舊: 코스피 종가 < 7,500 → 신규 매수 **전면 동결 0원**. (§5b 예외 = 폭풍 <90일 때 25% 1회)
   결함: 코스피 -38.6% 지점의 12개월 기저율이 **중앙 +43%·승률 97%(표본 750)**인데
        룰은 이 구간을 통째로 건너뛰고 **+34% 오른 뒤에야** 매수를 허용했다.
        게다가 §5b 폭풍 조항은 **역작동**했다 — 변동성이 극단일수록(=항복 바닥에 가까울 수 있는
        바로 그때) 가장 강하게 막았다.
   新: **고점 대비 낙폭**을 사다리로 나눠 단계별로 재원을 미리 배분. 각 단계 첫 도달 시 그 몫만 해금.
       폭풍·심리는 **금지가 아니라 승수(감산·가산)**로 작동한다.
       ★2차 개정(7/30 밤): 11개 지수 17,946표본 재판정에서 **폭풍 금액 감산이 해금 4단계 전부
       역효과**로 확인 → **금액 감산 폐지**, 폭풍은 **분할 횟수**로만 쓴다(총액 불변).

■ 룰 2 (LG전자 펀더 훼손) — **이벤트형만 → 추세형 판정 추가**
   舊: *"NVIDIA 냉각 인증 취소 등"* = **이벤트만** 훼손으로 인정.
   결함: LG전자 영업마진이 **4.4→3.9→2.8%로 3년 연속** 빠지는 동안 **아무 신호도 안 떴다.**
   新: 마진·FCF·순부채 **3중 조건**으로 추세형 훼손을 기계 판정(3/3=착수 · 2/3=감시상향).

═══ ⚠️ 안전장치 — 이 개정이 '더 공격적'이라는 뜻이 아니다 ═══
   ① **하드 플로어 신설**: 이번 국면의 근거는 *"국내 구조 사건(VIX 19.4)"*이다.
      **글로벌 시스템 위기로 번지면 그 전제가 깨지므로 사다리를 즉시 정지**한다.
   ② 사다리는 **누적 상한**이지 목표가 아니다. 집행은 여전히 PM 판단·정훈 결정.
   ③ 기저율은 **표본 중복·생존편향**이 있다. 사다리 배분은 그 불확실성을 반영해
      깊은 구간일수록 큰 몫을 두되 **예비 15%는 회복 확인 전까지 영구 봉인**한다.
   ④ **자동 집행 아님.** 이 스크립트는 '최대 얼마까지 허용되나'만 계산한다.

사용:
  python3 tranche_rules.py                     # 룰1 사다리 + 룰2 훼손 판정
  python3 tranche_rules.py --cash 672472       # 가용 현금 지정(생략 시 portfolio.json)
  python3 tranche_rules.py --rule2             # 룰2 추세형 훼손만
  python3 tranche_rules.py --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

KOSPI = "^KS11"

# ─────────────────────────────────────────── 룰 1: 낙폭 사다리
#
# 배분 근거 = 낙폭연구 §4 조건부 기저율 + 역대 낙폭 분포(29년 8회·최악 -64.7%).
# 깊을수록 몫을 키우되, 표본이 급감하는 구간(-45% 이하)은 신중히 나눈다.
LADDER = [
    (-25.0, 0.15, "1차 — 통상 조정 하단"),
    (-35.0, 0.20, "2차 — 12M 기저율 중앙 +43%·승률 97%(표본 750) 구간"),
    (-45.0, 0.25, "3차 — 29년 8회 중 3~4번째 깊이. 표본 급감"),
    (-55.0, 0.25, "4차 — IMF(-64.7%)·IT버블(-55.7%)급. 전례 2회뿐"),
]
RESERVE = 0.15  # 영구 예비 — 회복 확인(게이트 2/3+) 전까지 봉인

# ★[2026-07-30 2차 개정·정훈 승인 "해금 구간 감산 제거하자"] 폭풍 **금액 감산 폐지**.
#
# 근거 = 11개 지수 17,946표본 재판정(rule_tracker --multi). 12개월 중앙값,
# 강한 감산(≤0.6) vs 약한 감산(>0.6) — **해금된 4개 단계 전부 역효과**:
#   D1 +11.4% vs +10.1%(+1.3%p·98국면) / D2 +14.2% vs +10.0%(+4.2%p·61국면)
#   D3  +6.0% vs  +4.9%(+1.1%p·64국면) / D4 +13.8% vs  +9.4%(+4.3%p·62국면)
# 평시(D0)에서만 감산이 유효했으나 **D0는 해금이 0%라 승수가 무엇이든 결과가 0원** —
# 즉 D0 유효 판정은 룰에 아무 영향이 없다. ⇒ 실질적으로 금액 감산 조항 전체 폐지.
#
# 해석: 평시엔 변동성이 높으면 조심하는 게 맞지만, **크래시 구간에서는 변동성이 높은 것
# 자체가 바닥 신호에 가깝다.** 舊 §5b 역작동이 축소된 형태로 남아 있던 것이 확인됐다.
STORM_MULT = None   # 폐기 — 이력은 위 주석 + crash_tf §2b

# 대신 폭풍은 **분할 속도**에 쓴다 — 총액은 그대로, 나눠 넣는 횟수만 늘린다.
# 데이터와 정합: 12개월 성과는 폭풍이 높을 때가 좋았으므로(금액 줄일 이유 없음)
# 금액은 유지하되, 그 사이 경로 변동성은 크므로(한 번에 넣을 이유도 없음) 분할한다.
# ⚠️ 이건 **집행 방식 권고**이지 상한 계산을 바꾸지 않는다.
STORM_SPLITS = [(97, 4), (90, 3), (75, 2), (0, 2)]

# 심리 항복 가산 — "공포에 사라"의 기계화. 공포·항복 둘 다 90%ile+ 일 때만.
CAPITULATION_BONUS = 1.20

# 감산이 사라졌으므로 하한은 1.0 (항복 가산만 위로 작동)
MULT_FLOOR, MULT_CAP = 1.00, 1.20

# ⚠️ 금융 자회사를 연결하는 기업 — FCF·순부채 조건이 **구조적으로 왜곡**된다.
#    현대차는 현대캐피탈 할부금융 자산 증가가 영업활동현금흐름(CFO)에 마이너스로 잡혀
#    2023~25 CFO가 -2.5조→-5.7조→-6.0조다. 제조업 부진이 아니라 금융업 회계 특성이다.
#    (7/30 실측: 룰2 전종목 스캔에서 현대차가 3/3으로 오탐 → 이 예외 신설.)
#    ⇒ 이런 기업은 **마진 조건만 유효**로 보고, FCF·순부채는 판정에서 제외한 뒤 caveat를 붙인다.
FINANCIAL_ARM = {"005380.KS"}


def _storm_splits(pct):
    """폭풍 %ile → **권장 분할 횟수**(금액 불변). 舊 금액 감산의 대체물."""
    if pct is None:
        return 2, "폭풍 미확인 → 기본 2분할"
    for thr, n in STORM_SPLITS:
        if pct >= thr:
            label = {4: "극단", 3: "폭풍", 2: "경계/평온"}[n]
            return n, f"폭풍 {pct:.0f}%ile [{label}] → **{n}분할** 권장 (금액 감산 없음)"
    return 2, ""


def ladder_state(dd_pct: float):
    """**현재** 낙폭에서 해금된 누적 비율 + 단계별 상태.

    ★[2026-07-31 확정 — RESET(재잠금) 정책] 되돌리면 몫이 **다시 잠긴다.**
      즉 -38.6%에서 D2까지 열렸어도 -27.6%로 회복하면 D1(15%)로 돌아간다.

      왜 이게 쟁점이었나: 문서(CLAUDE.md·crash_tf §2b)의 *"각 단계 **첫 도달** 시
      그 몫만 해금"*이 **한 번 열리면 유지**(래칫)로 읽혔다. 7/31 코스피가
      +17.91%(역대 최대 상승) 튀면서 두 해석이 실제로 갈렸다 —
      같은 날 상한이 **121,045원(RESET) vs 282,438원(RATCHET)**, 2.3배 차이.

      판정 = `ratchet_test.py` 11지수 24,592일(에피소드 7개). 낙폭 구간을 통제하면
      **3개 구간 전부 RESET 우위**(-45%↓ ±0.0%p · -45~-35% -1.3%p · -35~-25% -0.6%p,
      구간가중 **-0.61%p**). 되돌림 구간에서 래칫이 더 넣은 돈은 **덜 벌었다.**
      ⚠️ 전 구간 단일집계는 +2.0%p로 **부호가 뒤집혀** 나온다 — 두 정책의 자금이
      서로 다른 낙폭 구간에 쏠려 있어 생기는 **심슨의 역설**이다. 속지 말 것.

      해석: 사다리의 약속은 *"이 깊이에는 이만큼"*이다. 값이 올라왔으면 그 깊이의
      배분으로 돌아가는 게 약속이고, 회복 구간의 매수는 사다리가 아니라
      **예비 15% 해금·TF 해제 절차(crash_tf §5 3중 게이트)**가 다룬다.
    """
    unlocked, steps = 0.0, []
    for thr, alloc, why in LADDER:
        hit = dd_pct <= thr
        if hit:
            unlocked += alloc
        steps.append({"threshold": thr, "alloc": alloc, "why": why, "unlocked": hit})
    return unlocked, steps


# ─────────────────────────────────────────── 집행 원장 (해금 ≠ 집행)
#
# ★[2026-07-31 신설] 舊 코드는 **이미 집행한 트랜치를 차감하지 않았다.**
#   crash_tf §2b 안전장치 2 *"단계 재진입 금지 — 한 단계는 1회만 해금"*이 문서에만
#   있고 코드엔 없었다. RESET 정책(되돌리면 재잠금)과 결합하면 이 구멍이 위험해진다:
#   D1에서 집행 → -35%까지 빠졌다 → -27%로 회복 → **D1이 또 열린 것처럼 보인다.**
#   낙폭이 오르내릴 때마다 같은 단계를 반복 집행하는 물타기가 되는 것이다.
#   ⇒ 집행분을 원장에 남기고, 판정에서 **이미 쓴 단계는 제외**한다.
LEDGER = os.path.join(ROOT, "data", "app", "tranche_ledger.json")


def _ledger_read() -> dict:
    try:
        with open(LEDGER, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def ledger_executed() -> dict:
    """{단계번호(int): {date, amount, note}} — 이미 집행이 끝난 단계."""
    d = _ledger_read()
    out = {}
    for k, v in (d.get("executed") or {}).items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            continue
    return out


def ledger_execute(step: int, amount: float, note: str = "", date: str | None = None):
    """단계 집행을 기록한다. **조회·기록 전용 — 주문을 내지 않는다.**"""
    if not (1 <= step <= len(LADDER)):
        raise ValueError(f"단계는 1~{len(LADDER)} (D1~D{len(LADDER)})")
    d = _ledger_read()
    ex = d.setdefault("executed", {})
    key = str(step)
    if key in ex:
        raise SystemExit(f"[tranche_rules] D{step}은 이미 집행됨 "
                         f"({ex[key].get('date')} · {ex[key].get('amount'):,.0f}원). "
                         f"단계 재진입 금지(crash_tf §2b 안전장치 2).")
    ex[key] = {"date": date or dt.date.today().isoformat(),
               "amount": round(float(amount)), "note": note}
    d["updated"] = dt.date.today().isoformat()
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    return ex[key]


def global_contagion_check():
    """하드 플로어 — 이 개정의 전제(국내 구조 사건)가 깨졌는지 본다.

    §0 프레임의 근거는 '저점 VIX 19.4 = 글로벌 위기 아님'이다. S&P500이 스톰에
    합류하면 그 전제가 무너지므로 **사다리를 정지**한다(舊 안전핀의 역할을 여기가 승계).
    """
    try:
        import vol_gauge
    except ImportError:
        return None, "vol_gauge 없음 — 확산 판정 불가"
    try:
        # ⚠️ gauge(symbol, window, lookback) — 3인자 필수(기본값 없음).
        r = vol_gauge.gauge("^GSPC", 20, 252)
        pct = r.get("storm_pct") if isinstance(r, dict) else None
    except Exception as e:
        return None, f"S&P 폭풍 조회 실패({type(e).__name__}) — 확산 판정 불가"
    if pct is None:
        return None, "S&P 폭풍 미확인"
    if pct >= 70:
        return True, f"🚨 S&P500 폭풍 {pct:.0f}%ile ≥70 = **글로벌 확산** → 사다리 전면 정지"
    return False, f"S&P500 폭풍 {pct:.0f}%ile <70 = 국지 유지(개정 전제 성립)"


def rule1(cash: float, dd_pct: float, storm_pct, fear_pct=None, capit_pct=None,
          check_contagion: bool = True, use_ledger: bool = True):
    unlocked, steps = ladder_state(dd_pct)
    splits, swhy = _storm_splits(storm_pct)

    # 이미 집행한 단계는 해금돼 있어도 **가용분에서 뺀다**(단계 재진입 금지).
    done = ledger_executed() if use_ledger else {}
    spent_ratio = 0.0
    for i, s in enumerate(steps, 1):
        s["executed"] = i in done
        if s["executed"]:
            s["executed_on"] = done[i].get("date")
            if s["unlocked"]:
                spent_ratio += s["alloc"]
    available = max(0.0, unlocked - spent_ratio)

    capit = (fear_pct is not None and capit_pct is not None
             and fear_pct >= 90 and capit_pct >= 90)
    mult = CAPITULATION_BONUS if capit else 1.0
    mult = max(MULT_FLOOR, min(MULT_CAP, mult))

    # 백테스트(rule_tracker --backfill)는 수천 번 호출하므로 네트워크 조회를 끈다.
    halted, hwhy = global_contagion_check() if check_contagion else (False, '확산 판정 생략(백테스트)')
    allowed = 0.0 if halted else cash * available * mult

    return {
        "dd_pct": dd_pct, "cash": cash,
        "unlocked_ratio": unlocked, "steps": steps,
        "spent_ratio": spent_ratio, "available_ratio": available,
        "executed_steps": sorted(done),
        "storm_splits": splits, "storm_why": swhy,
        "storm_mult": 1.0,   # 하위호환(원장 스키마) — 금액 감산 폐지로 항상 1.0
        "capitulation": capit,
        "capitulation_why": (f"공포 {fear_pct:.0f}%ile·항복 {capit_pct:.0f}%ile 동반 90+ → ×{CAPITULATION_BONUS}"
                             if capit else "항복 가산 미충족"),
        "final_mult": round(mult, 3),
        "halted": bool(halted), "halt_why": hwhy,
        "allowed_krw": round(allowed),
        "reserve_ratio": RESERVE,
    }


# ─────────────────────────────────────────── 룰 2: 추세형 훼손

def _series(rows, key, n=3):
    out = []
    for r in rows[:n]:
        v = r.get(key)
        if v is None:
            return None
        out.append(v)
    return out


def rule2(ticker="066570.KS"):
    """추세형 훼손 3중 조건. 3/3=훼손 착수 · 2/3=감시상향 · ≤1=정상.

    ⚠️ 이벤트형 훼손(인증 취소 등)은 이 판정과 **독립**이며 그쪽이 우선한다.
    """
    p = os.path.join(ROOT, "data", "app", "financials.json")
    if not os.path.exists(p):
        return {"error": "financials.json 없음 — financials.py --all --save 필요"}
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    rec = (d.get("stocks") or {}).get(ticker)
    if not rec:
        return {"error": f"{ticker} 재무 레코드 없음"}
    ann = rec.get("annual") or []
    if len(ann) < 3:
        return {"error": f"{ticker} 연간 3기 미만 — 추세 판정 불가"}

    conds, detail = [], []

    # financials.json 필드명 = op_margin (비율, 0.0278 = 2.78%). ann[0]이 최신.
    m = _series(ann, "op_margin")
    if m:
        m = [x * 100 for x in m]
    if m and m[0] < m[1] < m[2]:
        conds.append(True)
        detail.append(f"✅ 영업마진 3년 연속 하락 {m[2]:.1f}→{m[1]:.1f}→{m[0]:.1f}%")
    else:
        conds.append(False)
        detail.append(f"❌ 영업마진 연속 하락 아님 {'→'.join(f'{x:.1f}' for x in reversed(m))}%" if m
                      else "❌ 영업마진 결측(op_margin)")

    f_ = _series(ann, "fcf")
    if f_ and (f_[0] < f_[1] < f_[2] or f_[0] < 0):
        conds.append(True)
        detail.append(f"✅ FCF 악화 {f_[2]/1e8:,.0f}→{f_[1]/1e8:,.0f}→{f_[0]/1e8:,.0f}억")
    else:
        conds.append(False)
        detail.append(f"❌ FCF 악화 아님 {'→'.join(f'{x/1e8:,.0f}' for x in reversed(f_))}억" if f_
                      else "❌ FCF 결측")

    nc = _series(ann, "net_cash")
    if nc and nc[0] < nc[1] < nc[2]:
        conds.append(True)
        detail.append(f"✅ 순부채 2년 연속 증가 {nc[2]/1e8:,.0f}→{nc[1]/1e8:,.0f}→{nc[0]/1e8:,.0f}억")
    else:
        conds.append(False)
        detail.append(f"❌ 순부채 연속 증가 아님 {'→'.join(f'{x/1e8:,.0f}' for x in reversed(nc))}억" if nc
                      else "❌ 순현금 결측")

    caveat = None
    if ticker in FINANCIAL_ARM:
        # 금융 자회사 연결 → FCF·순부채 조건 무효화, 마진만 유효(1중 판정)
        caveat = ("⚠️ 금융 자회사 연결 기업 — 할부금융 자산 증가가 CFO에 마이너스로 잡혀 "
                  "FCF·순부채 조건이 구조적으로 왜곡된다. **마진 조건만 유효로 판정**한다.")
        conds = conds[:1]
        n = sum(conds)
        verdict = ("⚠️ 마진 추세 훼손 — 제조 수익성 딥다이브 필요(FCF·순부채는 판정 제외)"
                   if n == 1 else "✅ 정상 — 마진 추세 훼손 없음")
        return {"ticker": ticker, "name": rec.get("name"), "score": f"{n}/1 (금융연결)",
                "verdict": verdict, "detail": detail, "caveat": caveat}

    n = sum(conds)
    verdict = ("🚨 훼손 착수 — 딥다이브 + 트림 검토" if n == 3 else
               "⚠️ 감시 등급 상향 — 매도 아님" if n == 2 else
               "✅ 정상 — 추세형 훼손 없음")
    return {"ticker": ticker, "name": rec.get("name"), "score": f"{n}/3",
            "verdict": verdict, "detail": detail, "caveat": caveat}


# ─────────────────────────────────────────── 실행

def _stale_warning(last_date: str):
    """★[2026-07-31 신설] 캐시 신선도 가드 — 실전 첫날에 터진 사고의 재발방지.

    사고: 7/31 코스피가 **+17.91%**(역대 최대 상승) 튀어 낙폭이 -38.6%→-27.6%로
    되돌아왔는데, 이 스크립트는 `data/history/` 캐시(7/30까지)만 읽어
    **-38.6%로 판정**했다. 상한이 282,438원으로 나왔지만 실제로는 121,045원이었다.
    즉 **급등·급락 당일에 상한을 가장 크게 틀린다** — 하필 판단이 제일 중요한 날에.

    ⇒ 캐시 마지막 날짜가 오늘(KRX 기준 직전 영업일)보다 오래되면 경고를 띄운다.
      **차단하지 않는 이유**: 휴장일·주말엔 정상적으로 과거 날짜가 마지막이고,
      백테스트(rule_tracker)도 이 함수를 거치기 때문. 판단은 사람이 한다.
    """
    try:
        last = dt.date.fromisoformat(last_date[:10])
    except Exception:
        return None
    today = dt.date.today()
    gap = 0
    d = last
    while d < today:                      # 주말 제외 경과 영업일
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            gap += 1
    if gap <= 0:
        return None
    return (f"⚠️ 코스피 캐시가 **{last.isoformat()}**까지 (영업일 {gap}일 경과) — "
            f"오늘 시세가 반영되지 않았다.\n     "
            f"급등·급락일엔 상한이 크게 틀린다. `history_backfill.py --symbols '^KS11'` 먼저 실행할 것.")


def _load_inputs(cash_arg):
    cash = cash_arg
    if cash is None:
        p = os.path.join(ROOT, ".claude", "skills", "portfolio-desk", "portfolio.json")
        try:
            with open(p, encoding="utf-8") as f:
                cash = float((json.load(f) or {}).get("cash_krw") or 0)
        except Exception:
            cash = 0.0

    dd = storm = fear = capit = None
    stale = None
    try:
        import drawdown_history as D
        dates, closes = D.load(KOSPI)
        if closes:
            dd = D.current_drawdown(dates, closes)["dd_pct"]
            stale = _stale_warning(dates[-1])
    except Exception:
        pass
    try:
        import vol_gauge
        r = vol_gauge.gauge(KOSPI, 20, 252)
        storm = r.get("storm_pct") if isinstance(r, dict) else None
    except Exception:
        pass
    try:
        # sentiment.json 스키마 = {history: [{date, psych: [{name, pctile}]}]}
        with open(os.path.join(ROOT, "data", "app", "sentiment.json"), encoding="utf-8") as f:
            sj = json.load(f)
        hist = sj.get("history") or []
        if hist:
            for g in (hist[-1].get("psych") or []):
                if "공포" in str(g.get("name", "")):
                    fear = g.get("pctile")
                elif "항복" in str(g.get("name", "")):
                    capit = g.get("pctile")
    except Exception:
        pass
    return cash, dd, storm, fear, capit, stale


def main():
    ap = argparse.ArgumentParser(description="개정 리스크룰 1·2 판정 (측정·제안 전용)")
    ap.add_argument("--cash", type=float)
    ap.add_argument("--dd", type=float, help="코스피 낙폭%% 수동 지정(음수)")
    ap.add_argument("--storm", type=float, help="코스피 폭풍%%ile 수동 지정")
    ap.add_argument("--fear", type=float)
    ap.add_argument("--capitulation", type=float)
    ap.add_argument("--execute", type=int, metavar="STEP",
                    help="사다리 단계 집행 기록(1~4). --amount 필수. 조회·기록 전용 — 주문 안 냄")
    ap.add_argument("--amount", type=float, help="--execute 와 함께 쓰는 집행 금액(원)")
    ap.add_argument("--note", default="", help="--execute 메모(종목·체결가 등)")
    ap.add_argument("--rule2", action="store_true")
    ap.add_argument("--ticker", default="066570.KS")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.rule2:
        r = rule2(a.ticker)
        print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else "")
        if not a.json:
            print(f"\n📋 룰2 추세형 훼손 판정 — {r.get('name') or a.ticker}")
            if r.get("error"):
                print(f"   ⚠️ {r['error']}")
            else:
                for d in r["detail"]:
                    print(f"   {d}")
                if r.get("caveat"):
                    print(f"\n   {r['caveat']}")
                print(f"\n   판정 {r['score']} → {r['verdict']}")
                print("   ※ 이벤트형 훼손(인증 취소 등)은 이 판정과 독립이며 그쪽이 우선한다.\n")
        return

    if a.execute:
        if a.amount is None:
            sys.exit("[tranche_rules] --execute 에는 --amount 가 필요하다")
        rec = ledger_execute(a.execute, a.amount, a.note)
        print(f"\n📒 D{a.execute} 집행 기록 — {rec['date']} · {rec['amount']:,}원 "
              f"{('· ' + rec['note']) if rec['note'] else ''}")
        print(f"   원장: {os.path.relpath(LEDGER, ROOT)} (단계 재진입 금지가 다음 판정부터 적용된다)\n")
        return

    cash, dd, storm, fear, capit, stale = _load_inputs(a.cash)
    dd = a.dd if a.dd is not None else dd
    storm = a.storm if a.storm is not None else storm
    fear = a.fear if a.fear is not None else fear
    capit = a.capitulation if a.capitulation is not None else capit

    if dd is None:
        sys.exit("[tranche_rules] 코스피 낙폭 산출 실패 — history_backfill.py 필요 또는 --dd 지정")

    r = rule1(cash, dd, storm, fear, capit)
    if a.json:
        print(json.dumps({"rule1": r, "rule2": rule2(a.ticker)}, ensure_ascii=False, indent=1))
        return

    print("\n═══ 룰1 개정 — 낙폭 사다리 (舊 7,500 이진 안전핀 대체) ═══")
    if stale and a.dd is None:
        print(f"  {stale}\n")
    print(f"  코스피 고점대비 **{dd:+.1f}%** · 가용 현금 {cash:,.0f}원\n")
    print(f"  {'단계':<6}{'낙폭':>8}{'배분':>7}  상태   근거")
    for i, s in enumerate(r["steps"], 1):
        mark = ("✅집행" if s.get("executed") else "🟢해금") if s["unlocked"] else "🔒잠김"
        why = (f"{s['why']}  ← {s.get('executed_on')} 집행 완료(재진입 금지)"
               if s.get("executed") else s["why"])
        print(f"  D{i:<5}{s['threshold']:>7.0f}%{s['alloc']*100:>6.0f}%  {mark}  {why}")
    print(f"  {'예비':<6}{'—':>8}{RESERVE*100:>6.0f}%  🔒봉인  회복 확인(게이트 2/3+) 전까지 영구 봉인")

    print(f"\n  누적 해금 **{r['unlocked_ratio']*100:.0f}%**"
          + (f" − 기집행 {r['spent_ratio']*100:.0f}%(D{',D'.join(map(str, r['executed_steps']))}) "
             f"= **가용 {r['available_ratio']*100:.0f}%**" if r["spent_ratio"] else ""))
    print(f"  {r['storm_why']}")
    print(f"  {r['capitulation_why']}")
    print(f"  → 최종 승수 **×{r['final_mult']}**  (하한 {MULT_FLOOR}·상한 {MULT_CAP} — 금액 감산 폐지)")
    print(f"\n  {r['halt_why']}")
    if r["halted"]:
        print("\n  🔴 **허용 트랜치 0원** — 글로벌 확산으로 개정 전제가 깨졌다.")
    elif r["available_ratio"] <= 0:
        print("\n  ⛔ **가용 0원** — 해금된 단계를 이미 전부 집행했다(단계 재진입 금지). "
              "다음 단계 낙폭에 도달해야 새 몫이 열린다.")
    else:
        print(f"\n  💰 **허용 트랜치 상한 = {r['allowed_krw']:,}원**"
              f"  ({cash:,.0f} × {r['available_ratio']*100:.0f}% × {r['final_mult']})")
        print(f"     분할 권고: **{r['storm_splits']}회** "
              f"(1회 ≈ {round(r['allowed_krw']/r['storm_splits']):,}원) — 금액이 아니라 속도로 조절")
        print("     ※ 상한이지 목표가 아니다. 집행은 PM 판단·정훈 결정. 자동 집행 아님.")

    r2 = rule2(a.ticker)
    print(f"\n═══ 룰2 개정 — 추세형 훼손 ({r2.get('name') or a.ticker}) ═══")
    if r2.get("error"):
        print(f"  ⚠️ {r2['error']}")
    else:
        for d in r2["detail"]:
            print(f"  {d}")
        if r2.get("caveat"):
            print(f"  {r2['caveat']}")
        print(f"\n  판정 {r2['score']} → {r2['verdict']}")
    print()


if __name__ == "__main__":
    main()
