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
   ① **하드 플로어 신설**: 이번 국면의 근거는 *"국내 구조 사건(VIX 17.1)"*이다.
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
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

KOSPI = "^KS11"

# ─────────────────────────────────────────── 룰 1: 낙폭 사다리
#
# 배분 근거 = 낙폭연구 §4 조건부 기저율 + 역대 낙폭 분포(29년 8회·최악 -64.7%).
# 깊을수록 몫을 키우되, 표본이 급감하는 구간(-45% 이하)은 신중히 나눈다.
# ★[2026-09-09 개정·정훈 승인 "D0 승인, 적용해줘"] **D0(-20%) 신설 · 예비 15% → 7%**
#
# 왜: 룰1 원장 24일 실측에서 **상한 0원인 날이 14일(58%)**이었고, 그중 **9일의 사유가
#     "낙폭이 -25%(D1 문턱)에 못 미쳐서"**였다. 코스피가 -22~-25%를 오가는 내내 사다리가
#     잠겨 있었고 그 사이 현금은 69만 → 145만으로 늘었다 — 재원은 쌓이는데 쓸 문이 없었다.
# 검정(`d0_test.py`, 8/5 3단 절차):
#   ① 집계     -25~-20% 12M 중앙 **+9.5%·승률 75%**(n=855)
#              vs 대조 D2(-40~-35%) +16.7%·83%(n=168) → **D0가 확실히 못하다**
#   ② 에피소드 **6/6 = 100% 일관**(소수 에피소드가 만든 값이 아니다)
#   ③ 횡단면   **18/21 = 86% 재현**(반대 3 = 코스닥·니케이·유로스톡스)
# 배분 8%인 근거: D0의 12M 중앙값이 D2의 **57% 수준**이고 D1(15%)보다 얕은 구간이므로
#   그보다 작아야 한다 → D1의 절반을 보수적으로 잡았다. 재원은 **예비에서 뗀다**(15% → 7%).
# ⚠️ **반대 근거도 남긴다**: 코스닥이 -7.4%·승률 29%로 반대이고(우리 워치에 코스닥 2종목),
#    얕은 조정에서 실탄을 먼저 써 깊은 구간에서 모자랄 위험이 생긴다 — 예비 축소가 그 대가다.
# ⚠️ **인덱스가 한 칸씩 밀렸다**: 舊 1=D1 → 新 2=D1. `tranche_ledger.json`을 같은 날
#    리맵했다(백업 .bak-20260909). 안 하면 기존 D1 집행 125,598원이 D0 집행으로 둔갑한다.
LADDER = [
    (-20.0, 0.08, "0차 — 얕은 조정. 12M 중앙 +9.5%·승률 75%(표본 855)"),
    (-25.0, 0.15, "1차 — 통상 조정 하단"),
    (-35.0, 0.20, "2차 — 12M 기저율 중앙 +43%·승률 97%(표본 750) 구간"),
    (-45.0, 0.25, "3차 — 29년 8회 중 3~4번째 깊이. 표본 급감"),
    (-55.0, 0.25, "4차 — IMF(-64.7%)·IT버블(-55.7%)급. 전례 2회뿐"),
]
# 표시 라벨 — **인덱스로 D 번호를 만들지 않는다.** D0 신설로 i와 D번호가 어긋났고,
# `D{i}` 식으로 찍으면 D0가 "D1"으로 표시된다(라벨이 조용히 거짓말하는 그 클래스).
STEP_LABELS = ["D0", "D1", "D2", "D3", "D4"]
RESERVE = 0.07  # 영구 예비 — 회복 확인(게이트 2/3+) 전까지 봉인. [9/9] D0 재원으로 15%→7%

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
KR_TRACK_KRW_ONLY = True   # d205 — False로 돌리면 舊 통합 재원(원화+달러 환산)
RULE_LOG = os.path.join(ROOT, "data", "app", "rule_log.jsonl")

# ★[2026-09-23 d207 승인 · 정훈 "승인"] 순서 = 룰6(어디에) → 국내 사다리(얼마나 빨리).
#   국내주 비중(주식 기준)이 룰6 상단 22%를 넘는 동안 국내 사다리는 **판정·적립만** 하고 집행 허용액은 0원.
#   22% 이하가 되면 사다리 상한만큼 집행한다. 舊엔 두 룰이 같은 원화에 다른 말을 했다
#   (사다리 = "사도 된다" / 룰6 = "국내 신규 매수 금지") — 누가 이기는지 코드에 없었다.
#   정본 = docs/research/ladder_variants_2026-09-22.md · decisions d207/d209.
RULE6_KR_HI = 22.0
RULE6_KR_LO = 18.0                     # 밴드 하단 — 표시용(triggers 룰6 줄). 게이트는 상단만 쓴다
SNAPS = os.path.join(ROOT, "data", "snapshots")


def kr_weight_pct() -> float | None:
    """최신 일일 스냅샷의 국내주 비중(주식 기준 %). order_check.kr_weight()와 같은 소스·같은 식."""
    try:
        snaps = sorted(f for f in os.listdir(SNAPS) if f.endswith(".json"))
        with open(os.path.join(SNAPS, snaps[-1]), encoding="utf-8") as f:
            s = json.load(f) or {}
        kr = float(s["kr_value"]); us = float(s["us_value_usd"]) * float(s["fx_usdkrw"])
        return kr / (kr + us) * 100 if kr + us else None
    except (OSError, IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _ledger_read() -> dict:
    try:
        with open(LEDGER, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def ledger_executed() -> dict:
    """{단계번호(int): {date, amount, note, fills:[...]}} — 그 단계에 **누적 집행된 금액**.

    ★[2026-08-28 개정 — 이진 → 금액 누적] 舊 구조는 단계를 **이진**으로 봐서 첫 집행에
    그 단계 전체(예: D1 15%)를 소진 처리하고 재진입을 막았다. 그런데 같은 도구가
    "폭풍 %ile에 따라 2~3분할" 을 권고한다 — **1회차를 넣는 순간 2·3회차가 불가능**해지는
    자기모순이었다. 룰 문구는 *"누적 상한이지 목표 아님"*(CLAUDE.md 리스크룰1)이므로
    **금액 누적**이 옳은 해석이다.
    ⚠️ 이 결함은 8/24 GOOGL D1 1회차를 집행하고도 **원장 파일 자체가 생성되지 않아**
    (아무도 --execute를 부르지 않았다) 8/28에 상한이 통째로 부활하면서 발견됐다.
    """
    d = _ledger_read()
    out = {}
    for k, v in (d.get("executed") or {}).items():
        try:
            step = int(k)
        except (TypeError, ValueError):
            continue
        fills = v.get("fills")
        if fills is None:                       # 舊 스키마(단건) 호환
            fills = [{"date": v.get("date"), "amount": v.get("amount"), "note": v.get("note")}]
        total = sum(float(f.get("amount") or 0) for f in fills)
        out[step] = {"date": fills[-1].get("date"), "amount": total,
                     "note": fills[-1].get("note"), "fills": fills, "n": len(fills)}
    return out


def ledger_execute(step: int, amount: float, note: str = "", date: str | None = None):
    """단계 집행을 기록한다. **조회·기록 전용 — 주문을 내지 않는다.**"""
    if not (1 <= step <= len(LADDER)):
        raise ValueError(f"단계는 1~{len(LADDER)} ({STEP_LABELS[0]}~{STEP_LABELS[len(LADDER)-1]})")
    d = _ledger_read()
    ex = d.setdefault("executed", {})
    key = str(step)
    rec = ex.setdefault(key, {"fills": []})
    if "fills" not in rec:                       # 舊 스키마 승격
        rec = ex[key] = {"fills": [{"date": rec.get("date"), "amount": rec.get("amount"),
                                    "note": rec.get("note")}]}
    rec["fills"].append({"date": date or dt.date.today().isoformat(),
                         "amount": round(float(amount)), "note": note})
    rec["date"] = rec["fills"][-1]["date"]
    rec["amount"] = sum(float(f.get("amount") or 0) for f in rec["fills"])
    rec["note"] = note
    d["updated"] = dt.date.today().isoformat()
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    return ex[key]


def cap_delta_explain(base, unlocked, mult, cap_now=None):
    """오늘 상한이 어제와 달라진 이유를 **낙폭 기여 vs 현금 기여**로 분해한다.

    ★[2026-08-29 신설 — 리스크 데스크 지적 채택] 사다리 상한은 `cash × 해금비율 × 승수`라
    **포지션을 팔아 현금이 늘어도 상한이 커진다.** 실제로 8/28 META 1주 매도로 현금이
    655,618 → 1,455,006원(+122%)이 되면서 상한이 63,675 → 183,583원(+188%)으로 뛰었는데
    **코스피 낙폭은 -25.5% 그대로였다.** 이걸 그냥 보여주면 "사다리가 더 열렸다"는 착시가 된다.
    사다리 비율은 *낙폭 심도에 대한 위험허용도*를 재려는 설계이므로, 매도 재원으로 커진 몫은
    **낙폭과 무관하다는 사실을 숫자로 갈라서** 표시한다.
    ⚠️ 표시 전용 — 상한 계산 자체는 바꾸지 않는다(룰 변경은 정훈 승인 사항).

    ★[2026-09-20 정정] 분모가 `cash`로 남아 있었다 — 9/9에 상한 공식을 `cash → base(=현금+전체 기집행)`로
      바꿀 때 **이 설명기에 전파되지 않았다.** 그래서 9/20 출력이 실제 상한 117,986원을
      "오늘 93,913원"으로 적었다(= cash×8%). 설명기가 본체와 다른 공식을 쓰면
      **분해 숫자가 맞아도 총합이 틀린다** — 8/31 '데이터 모양이 바뀌면 모양에 기댄 라벨은
      조용히 거짓말한다'와 같은 클래스다. 이제 base로 계산하고, cap_now를 받으면 그 값을 쓴다.
      과거 로그 행에는 base_krw·cap_krw가 없으므로 cash로 폴백한다(그 행들은 근사).
    """
    try:
        rows = [json.loads(l) for l in open(RULE_LOG, encoding="utf-8") if l.strip()]
    except Exception:
        return None
    # ⚠️ 컨테이너가 UTC라 dt.date.today()는 KST 자정~09시에 **하루 전**을 준다.
    # 그대로 쓰면 어제 기록을 '오늘'로 오인해 건너뛴다(2026-08-29 실측 — 7/13 triggers.py와 같은 버그 클래스).
    _today = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).date().isoformat()
    prev = next((r for r in reversed(rows)
                 if r.get("date") != _today and r.get("cash") is not None), None)
    if not prev:
        return None
    # base_krw가 있으면 그것이 정본. 없으면(9/20 이전 행) cash로 근사한다.
    c0 = float(prev.get("base_krw") or prev["cash"])
    u0 = float(prev.get("unlocked_ratio") or 0)
    m0 = float(prev.get("final_mult") or 1.0)
    cap0 = float(prev["cap_krw"]) if prev.get("cap_krw") is not None else c0 * u0 * m0
    cap1 = float(cap_now) if cap_now is not None else base * unlocked * mult
    if abs(cap1 - cap0) < 1:
        return None
    dd_part = c0 * (unlocked * mult - u0 * m0)      # 낙폭·승수가 바꾼 몫
    cash_part = (base - c0) * u0 * m0               # 재원이 바꾼 몫
    cross = (cap1 - cap0) - dd_part - cash_part     # 교차항(+ 폴백 행의 근사 오차)
    return {"prev_date": prev.get("date"), "cap_prev": round(cap0), "cap_now": round(cap1),
            "delta": round(cap1 - cap0), "by_drawdown": round(dd_part),
            "by_cash": round(cash_part), "cross": round(cross),
            "cash_prev": round(c0), "cash_now": round(base),
            "approx": prev.get("base_krw") is None,
            "dd_prev": prev.get("dd_pct")}


# ─────────────────────────────────────────── 🇺🇸 미국 트랙 (d205 · 2026-09-21)
#
# ★[정훈 승인 "승인, 적용해줘"] 미국주 매수를 코스피 사다리에서 떼어낸다.
#   왜: 사다리의 근거는 **코스피 자신의** forward 수익률(-38.6% → 12M 중앙 +43%)인데
#   집행 5건 300,909원이 **전부 GOOGL**이었다. 코스피 반등 프리미엄을 받지 않는 자산이다.
#   원래 설계(crash_tf §6.5, 7/13)도 "미장은 안전핀 무관 별도 트랙"이었다.
#   검정(us_track_test.py, 1997~2025): 3개월 분할(P3)이 코스피 게이팅(G)보다
#   12M 중앙 +2.29%p(현금 3%에도 +1.86)·승률 73.5%·하위5% -6.03 / 선례 에피소드 6/6 /
#   비미국 게이팅 지수 19/19. ⚠️ 사전등록 에피소드 정의로는 24/38(무차이 14) — 실질 손실은
#   **2000-02 닷컴 약세장**(-3.85%p) 하나다: **미국 자체가 느리게 빠지는 약세장이 이 룰의 약점**이다.
#
# 규칙: 달러 잔고를 **3회 균등 분할**(월 1회) · 회차 금액 = 그날 달러 잔고 ÷ 남은 회차 수
#   (새로 들어온 달러는 남은 회차에 자동으로 퍼지고, 덜 쓴 몫은 다음 회차로 넘어간다)
#   · S&P 폭풍 ≥70(하드플로어)이면 그 회차 **연기** · 룰3(추격금지)은 그대로 · 자동 집행 아님.
#   대상 순서: 매수존 안의 우선순위(GEV·ANET·CDNS — d220 9/30 CDNS ④ 편입) → 없으면 GOOGL(주식 비중 18% 상한까지) → 나머지 VOO.
US_TRACK = os.path.join(ROOT, "data", "app", "us_track.json")
US_TRANCHES = 3
US_MIN_CYCLE_USD = 50.0      # 이보다 적은 달러로는 새 사이클을 열지 않는다(소수점 체결 실익)
US_GOOGL_CAP = 0.18          # d191 — 주식 평가액 기준
US_ZONE_TICKERS = ("GEV", "ANET", "CDNS")   # d191 ②③ + d220 ④ — 매수존은 portfolio.json alerts(below)가 정본
# ★[10/21 d251 정훈 승인 "다 승인"] '월 1회차' = **직전 회차 체결 세션 + 1개월 이후**.
#   舊 코드는 2회차를 기록하는 순간 3회차 zone_open을 냈다(10/19 실측 — 따르면 달러가 한 주 안에 바닥난다).
#   ⇒ 다음 회차(존 조기 집행이든 회차일 집행이든)는 직전 회차의 마지막 체결 세션(美 현지일) + 1개월 전엔 열지 않는다.
#   밀린 회차가 둘이어도 한 번에 한 회차만(몰아 사지 않는다).
US_SPACING_MONTHS = 1
# ★[10/21 d254 정훈 승인] 추격 상한 = min(존 상단, 전일 정규장 종가 × 1.03) — d191 '+3% 이상 급등이면 다음 날'과
#   d235⑤ '-5% 이상 갭이면 취소'를 동시에 만족하는 **상한**(10/19 $182·10/20 $188이 이 식이었다 — 그때는 이 값을 지정가로 걸었다).
US_CHASE_CAP = 1.03
#   ⚠️ [10/21 lessons] 이 값은 **추격 상한**(이 위로는 사지 않는다)이지 '걸 가격'이 아니다 — v118이 $188을 지정가 칸에 적어
#   토스 현재가 $181과 부딪혔다. 출력은 상한·걸 가격(그날 토스 현재가 근처·PM 판단)·예상 체결가를 따로 적는다.
US_FEE = 0.001               # 토스 미국 수수료 약 0.1%(9/22 체결 $77.92+$0.07·$144.85+$0.14 실측) — 잔액 추정용
# ★[10/22 리뷰 반영] 한 회차는 여러 체결로 채워진다(존 1주 지정가 + 잔액 GOOGL→VOO · 1주가 안 채워지면 그 몫까지 VOO — d235 ①).
#   舊 원장은 '체결 기록이 하나라도 있으면 그 회차 끝'으로 읽어서, ANET 1주를 기록하는 순간 같은 회차 잔액이 사라지고
#   (다음 회차 금액에 섞인다) d251 대기가 그 잔액 매수까지 막았다. ⇒ 회차 첫 체결에 **회차 금액(budget)**을 남기고,
#   체결 합이 budget − 이 값에 닿거나 명시적으로 닫을 때(--us-close) 회차가 끝난다. budget이 없는 옛 기록은 닫힌 회차.
US_TRANCHE_SLACK = 1.0
_PF_JSON = os.path.join(ROOT, ".claude", "skills", "portfolio-desk", "portfolio.json")


def _kst_today() -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).date().isoformat()


def _us_session_today() -> str:
    """지금 걸어 둔 주문이 체결되면 잡힐 美 세션일(us_session_of와 같은 식) — d251 간격 게이트 전용.

    ★[10/22 리뷰 반영] ⓐ KST 00:00~05:00(美 장중 = 전날 세션)에 KST 날짜와 비교해 하루 일찍 열렸다 → 세션일로 비교.
      ⓑ 舊 식(UTC−5h)은 KST 오전(05:00~14:00)을 전날로 읽어 회차를 열 수 있는 첫날 아침 브리핑이 재등록을 빼고
      그날 아침 건 주문을 '간격 위반'으로 봤다 → 세션 식 자체를 고쳤다(us_session_of: 동부시각 + 4시간)."""
    return us_session_of(dt.datetime.now(dt.timezone.utc).isoformat())[0]


class UsLedgerError(ValueError):
    """us_track.json이 있는데 못 읽거나 형식이 깨졌다 — '사이클 없음'과 다르다(덮어쓰면 기록이 사라진다)."""


def _us_read() -> dict:
    """원장 읽기. **없으면 {}**, 있는데 못 읽으면 UsLedgerError.
    ★[10/22 리뷰 반영] 舊 = 모든 예외를 {}로 삼켰다 → 깨진 원장이 '사이클 없음'으로 읽혀 미국 매수 알림이 꺼지고,
      --us-start가 그 위에 새 사이클을 써서 기록을 덮을 수 있었다."""
    if not os.path.exists(US_TRACK):
        return {}
    try:
        with open(US_TRACK, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:  # noqa: BLE001
        raise UsLedgerError(f"us_track.json 읽기 실패({type(e).__name__})") from e
    if d is None:
        return {}
    if not isinstance(d, dict):
        raise UsLedgerError("us_track.json 최상위가 객체가 아니다")
    return d


def _us_write(d: dict):
    d["updated"] = _kst_today()
    os.makedirs(os.path.dirname(US_TRACK), exist_ok=True)
    with open(US_TRACK, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


_ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _iso_day(v, what: str) -> dt.date:
    """'YYYY-MM-DD'만 받는다 — 문자열 비교·max()가 날짜 순서와 같아지는 형식이 이것뿐이다('2026/10/22' > '2026-10-22')."""
    if not isinstance(v, str) or not _ISO_DAY.match(v):
        raise UsLedgerError(f"{what} 날짜 형식 오류: {v!r}(YYYY-MM-DD)")
    try:
        return dt.date.fromisoformat(v)
    except ValueError as e:
        raise UsLedgerError(f"{what} 날짜 오류: {v!r}") from e


def _check_cycle(cur: dict) -> None:
    """원장 사이클의 형식 검사 — 깨진 행이 있으면 UsLedgerError(조용히 넘어가면 d251 간격이 엉뚱한 날에서 계산된다).
    ★[10/22] 모양이 틀린 값(사이클·행이 객체가 아님 · 목록이 목록이 아님 · 문자열 budget)도 여기서 멈춘다 —
      舊엔 AttributeError로 새거나, 문자열 budget이 '없음'으로 읽혀 진행 중 회차가 닫힌 회차로 보였다."""
    if not isinstance(cur, dict):
        raise UsLedgerError("사이클이 객체가 아니다")
    n = cur.get("n", US_TRANCHES)
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise UsLedgerError(f"회차 수 오류: {n!r}")
    _iso_day(cur.get("start"), "사이클 시작")
    for key in ("schedule", "fills", "closed_tranches"):
        if cur.get(key) is not None and not isinstance(cur[key], list):
            raise UsLedgerError(f"{key}가 목록이 아니다")
    sched = [_iso_day(d, f"{i}회 회차일") for i, d in enumerate(cur.get("schedule") or [], 1)]
    if len(sched) != n:
        raise UsLedgerError(f"회차일 {len(sched)}개 ≠ 회차 수 {n}")       # 짧으면 us_track이 IndexError로 죽는다(→ 알림이 fail-open)
    if sched != sorted(sched):
        raise UsLedgerError("회차일이 날짜 순서가 아니다")
    for f in cur.get("fills") or []:
        if not isinstance(f, dict):
            raise UsLedgerError("체결 행이 객체가 아니다")
        k = f.get("tranche")
        if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= n:
            raise UsLedgerError(f"체결 행 회차 번호 오류: {k!r}")
        if not isinstance(f.get("usd"), (int, float)) or isinstance(f.get("usd"), bool):
            raise UsLedgerError(f"{k}회차 체결 금액 오류: {f.get('usd')!r}")
        b = f.get("budget")
        if b is not None and (not isinstance(b, (int, float)) or isinstance(b, bool) or b <= 0):
            raise UsLedgerError(f"{k}회차 회차 금액(budget) 오류: {b!r}")
        _iso_day(f.get("date"), f"{k}회차 체결일")
        if f.get("session") is not None:
            _iso_day(f["session"], f"{k}회차 체결 세션")
    for k in cur.get("closed_tranches") or []:
        if not isinstance(k, int) or not 1 <= k <= n:
            raise UsLedgerError(f"닫은 회차 번호 오류: {k!r}")


def us_tranches(cur: dict) -> dict:
    """회차별 상태 {k: {fills, spent, budget, closed, left, tickers}} — 체결 기록이 있는 회차만.

    닫힘 = ⓐ budget이 없다(옛 기록 — 한 번에 기록한 회차) ⓑ 체결 합 ≥ budget − US_TRANCHE_SLACK ⓒ closed_tranches에 있다."""
    st: dict = {}
    for f in (cur or {}).get("fills") or []:
        k = int(f["tranche"])
        s = st.setdefault(k, {"fills": [], "spent": 0.0, "budget": None, "tickers": []})
        s["fills"].append(f)
        s["spent"] = round(s["spent"] + float(f.get("usd") or 0), 2)
        if s["budget"] is None and isinstance(f.get("budget"), (int, float)):
            s["budget"] = round(float(f["budget"]), 2)
        if f.get("ticker") and f["ticker"] not in s["tickers"]:
            s["tickers"].append(f["ticker"])
        day = str(f.get("session") or f.get("date") or "")[:10]
        s.setdefault("sessions", [])
        if day and day not in s["sessions"]:
            s["sessions"].append(day)
    shut = set((cur or {}).get("closed_tranches") or [])
    for k, s in st.items():
        b = s["budget"]
        # ★[10/22 리뷰] 센트로 반올림해 비교 — 舊 spent >= b − 1.0은 잔액이 정확히 $1.00일 때 부동소수로 열린 채 남았다(128.02 등)
        s["closed"] = k in shut or b is None or round(b - s["spent"], 2) <= US_TRANCHE_SLACK
        s["left"] = 0.0 if s["closed"] else round(b - s["spent"], 2)
    return st


def _add_months(d: dt.date, k: int) -> dt.date:
    y, m = divmod(d.month - 1 + k, 12)
    y, m = d.year + y, m + 1
    feb = 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28
    last = [31, feb, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    out = dt.date(y, m, min(d.day, last))
    fwd = out
    while fwd.weekday() >= 5:                 # 주말이면 월요일로
        fwd += dt.timedelta(days=1)
    if fwd.month == out.month:
        return fwd
    # ★[10/1] 월말이 주말이면 월요일이 **다음 달**로 넘어가 그 달 회차가 사라지고 다음 달에 두 번 잡혔다
    #   (8/31 시작 6회 → 10월 없음·11월 2회). 달을 넘기면 금요일로 당긴다.
    while out.weekday() >= 5:
        out -= dt.timedelta(days=1)
    return out


def us_schedule(start: str, n: int = US_TRANCHES) -> list[str]:
    s0 = dt.date.fromisoformat(start)
    return [_add_months(s0, k).isoformat() for k in range(n)]


def us_start(start: str | None = None, pool_usd: float | None = None, note: str = "") -> dict:
    """새 사이클을 연다. 진행 중 사이클이 있으면 거부한다(끝나기 전 재시작 = 회차 건너뛰기)."""
    d = _us_read()                            # 깨진 원장이면 여기서 멈춘다(덮어쓰지 않는다)
    cur = d.get("cycle")
    if cur:
        _check_cycle(cur)
        ts = us_tranches(cur)
        if sum(1 for s in ts.values() if s["closed"]) < cur.get("n", US_TRANCHES):
            raise ValueError(f"진행 중 사이클({cur.get('start')})이 끝나지 않았다 — 회차를 건너뛰는 재시작 금지")
    if cur:
        d.setdefault("history", []).append(cur)
    start = start or _kst_today()
    _iso_day(start, "사이클 시작")
    d["cycle"] = {"start": start, "n": US_TRANCHES, "schedule": us_schedule(start),
                  "pool_usd_at_start": pool_usd, "fills": [], "note": note}
    d["rule"] = "d205 — 달러 잔고 3회 균등 분할(월 1회) · 회차=그날 잔고÷남은 회차 · S&P 폭풍≥70이면 연기"
    _us_write(d)
    return d["cycle"]


def _et_offset(u: dt.datetime) -> dt.timedelta:
    """UTC 시각 u의 美 동부 오프셋(EDT −4h / EST −5h). zoneinfo가 없으면 규칙(3월 둘째 일요일 ~ 11월 첫째 일요일 02:00 현지)."""
    try:
        from zoneinfo import ZoneInfo
        return u.astimezone(ZoneInfo("America/New_York")).utcoffset()
    except Exception:  # noqa: BLE001 — tzdata 없는 환경
        def nth_sunday(month: int, k: int) -> dt.date:
            d0 = dt.date(u.year, month, 1)
            return d0 + dt.timedelta(days=(6 - d0.weekday()) % 7, weeks=k - 1)
        on = dt.datetime.combine(nth_sunday(3, 2), dt.time(7), dt.timezone.utc)    # 02:00 EST
        off = dt.datetime.combine(nth_sunday(11, 1), dt.time(6), dt.timezone.utc)  # 02:00 EDT
        return dt.timedelta(hours=-4 if on <= u < off else -5)


def us_session_of(filled_at: str) -> tuple[str, str]:
    """토스 체결 시각(ISO·타임존 포함) → (美 거래일 = 세션일, KST 체결일).

    세션일 = **美 동부시각 + 4시간**의 날짜. 美 거래일은 동부 20:00에 넘어간다:
      주간거래(블루오션 야간 20:00~04:00 ET = KST 09:00~17:00경) → 다음 거래일 · 프리 04:00~ · 정규 · 애프터 ~20:00 → 그날.
    (9/22 01:19 KST 체결 = 9/21 정규장 · 10/22 10:30 KST 주간거래 = 10/22 거래일.)
    ★[10/22 리뷰 반영] 舊 식(UTC−5h)은 서머타임 중 주간거래를 **전날**로 읽어 수동 --us-session이 필요했고, 같은 식을 쓰는
      d251 게이트가 회차를 열 수 있는 첫날 KST 오전을 전날 세션으로 봤다. 정규·애프터 체결의 결과는 舊 식과 같다.
    ⚠️ 美 휴장일 전날 밤 주간거래는 휴장일 날짜로 나온다(실제 귀속 = 다음 거래일) — 하루 이르게 잡히는 유일한 경우.
    """
    t = dt.datetime.fromisoformat(filled_at)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone(dt.timedelta(hours=9)))
    u = t.astimezone(dt.timezone.utc)
    return ((u + _et_offset(u) + dt.timedelta(hours=4)).date().isoformat(),
            (u + dt.timedelta(hours=9)).date().isoformat())


def _us_cash_now() -> float:
    try:
        with open(_PF_JSON, encoding="utf-8") as f:
            return float((json.load(f) or {}).get("cash_usd") or 0)
    except Exception:  # noqa: BLE001
        return 0.0


def us_execute(usd: float, ticker: str, tranche: int | None = None, note: str = "",
               date: str | None = None, session: str | None = None,
               filled_at: str | None = None, budget: float | None = None,
               close: bool = False, force: bool = False) -> dict:
    """회차 집행 기록. **조회·기록 전용 — 주문을 내지 않는다.** 한 회차를 여러 체결로 나눠 기록할 수 있다.

    ★[10/21 d251] 체결 세션(美 거래일)을 같이 남긴다 — '월 1회차' 간격이 이 값에서 계산된다.
    ★[10/22 리뷰 반영]
      ⓐ 체결 시각이 필수다(`filled_at` = 토스 filledAt, 또는 date/session) — 舊엔 없으면 **기록한 날**이 박혀 간격이 며칠씩 늦게 풀렸다.
      ⓑ 날짜는 YYYY-MM-DD만 · 세션 ≤ 체결일 ≤ 오늘 · 세션 ≥ 사이클 시작 − 1일 — 舊엔 '2026/10/21'이 그대로 기록돼
         그 뒤 모든 판정이 예외로 죽었고(d251 가드가 꺼졌다) 미래 세션은 트랙을 1년 막았다.
      ⓒ 회차 = 생략하면 **진행 중인 회차**(잔액이 남은 회차), 없으면 다음 회차. 1..n 밖·닫힌 회차·건너뛰기·d251 간격 전
         새 회차는 거부(실제로 그렇게 체결됐으면 --force로 기록 — 위반이 원장에 남는다).
      ⓓ 새 회차 첫 체결엔 **회차 금액을 명시**한다 — 나눠 사면 `budget`(오더북의 회차 금액), 이 체결이 회차 전부면 `close`.
         ★[10/22 리뷰 2차] 舊 = budget을 생략하면 portfolio.json 현금 ÷ 남은 회차로 추정했다 — 그 현금이 **체결 뒤 값**이면
         회차 일부(ANET 1주)가 회차 전부로 읽혀 조용히 닫혔다(마지막 회차면 잔액 $181.69가 사이클 '완료'로 사라졌다).
         현금이 체결 전인지 뒤인지 도구는 모른다 → 추정하지 않는다.
      ⓔ budget < 이 체결(자릿수 오타)은 거부 · 이미 있는 회차 금액은 여기서 못 바꾼다 → `us_set_budget`(체결을 추가하지 않는다)
      ⓕ 진행 중 회차에 **잔액보다 큰 체결**은 거부 — 다음 회차 체결이 기본 회차(= 진행 중 회차)로 잘못 들어가는 형태.
         잔액을 버리고 다음 회차로 가려면 먼저 `us_close`.
    """
    d = _us_read()
    cur = d.get("cycle")
    if not cur:
        raise ValueError("열린 사이클이 없다 — --us-start 먼저")
    _check_cycle(cur)
    n = cur.get("n", US_TRANCHES)
    if not (filled_at or date or session):
        raise ValueError("체결 시각이 없다 — --filled-at(토스 filledAt) 또는 --date/--us-session을 준다 "
                         "(기록한 날로 간격을 세면 d251이 며칠씩 늦게 풀린다)")
    if filled_at:
        s_, kd = us_session_of(filled_at)
        session, date = session or s_, date or kd
    date = date or session
    dd, sd = _iso_day(date, "체결일"), _iso_day(session, "체결 세션") if session else None
    if dd > dt.date.fromisoformat(_kst_today()):
        raise ValueError(f"체결일 {date}이 오늘({_kst_today()})보다 뒤다")
    if sd and sd > dd:
        raise ValueError(f"세션 {session}이 체결일 {date}보다 뒤다 — 美 거래일은 KST 체결일과 같거나 하루 앞이다")
    if (sd or dd) < _iso_day(cur["start"], "사이클 시작") - dt.timedelta(days=1):
        raise ValueError(f"세션 {session or date}이 사이클 시작 {cur['start']}보다 앞이다")
    ts = us_tranches(cur)
    closed = {k for k, s_ in ts.items() if s_["closed"]}
    remaining = [i for i in range(1, n + 1) if i not in closed]
    if not remaining:
        raise ValueError("사이클 3회 완료 — 새 사이클(--us-start) 먼저")
    if tranche is None:
        tranche = remaining[0]                # 진행 중 회차가 있으면 그게 remaining[0]이다(회차는 순서대로 연다)
    tranche = int(tranche)
    if not 1 <= tranche <= n:
        raise ValueError(f"회차 번호 {tranche}는 1~{n} 밖이다")
    if tranche in closed and not force:
        raise ValueError(f"{tranche}회차는 이미 닫혔다 — 정정 기록이면 --force")
    if tranche != remaining[0] and not force:
        raise ValueError(f"회차 건너뛰기 — 지금 회차는 {remaining[0]}회차다(정정 기록이면 --force)")
    if not float(usd) > 0:
        raise ValueError(f"체결 금액 ${float(usd):,.2f} ≤ 0 — 체결 없이 회차를 닫으려면 --us-close")
    rec = {"date": date, "tranche": tranche, "usd": round(float(usd), 2), "ticker": ticker, "note": note}
    if session:
        rec["session"] = session
    if tranche not in ts:                     # 새 회차의 첫 체결
        sp = us_spacing(cur)
        w = spacing_wait_until(sp, remaining, session or date)
        if w and not force:
            raise ValueError(f"d251 — {sp['last_tranche']}회차 마지막 세션 {sp['last_session']} + 1개월 = {w}부터인데 "
                             f"세션 {session or date} 체결이다. 실제로 그렇게 체결됐으면 --force로 기록(위반이 원장에 남는다)")
        if budget is None and not close:
            per = _us_cash_now() / len(remaining)
            raise ValueError(f"{tranche}회차 첫 체결 — 회차 금액을 정해 준다: 나눠 사면(1주 + 잔액) --budget <오더북의 회차 금액>, "
                             f"이 체결이 회차 전부면 --close (참고: portfolio.json 현금 ÷ 남은 {len(remaining)}회 = ${per:,.2f} — "
                             "현금이 체결 뒤 값이면 이 숫자는 작다 · 그래서 추정하지 않는다)")
        if budget is not None:
            b = round(float(budget), 2)
            if b <= 0 or b < rec["usd"] - US_TRANCHE_SLACK:
                raise ValueError(f"회차 금액 ${b:,.2f} < 이 체결 ${rec['usd']:,.2f} — 자릿수 확인(회차 금액은 체결보다 크거나 같다)")
            # ★[10/22 리뷰 3차] 위쪽 상한 — 회차 금액 ≤ 달러 잔고 + 이 체결(잔고가 체결 전 값이든 뒤 값이든 성립) · 자릿수 오타(3668.70) 방지
            cap = _us_cash_now() + rec["usd"] + US_TRANCHE_SLACK
            if b > cap and not force:
                raise ValueError(f"회차 금액 ${b:,.2f} > 달러 잔고 + 이 체결 ${cap - US_TRANCHE_SLACK:,.2f} — 자릿수 확인"
                                 "(portfolio.json 잔고가 낡았으면 갱신 후 · 확인한 예외면 --force)")
            rec["budget"] = b
    else:
        if budget is not None:
            raise ValueError(f"{tranche}회차 금액은 첫 체결에 이미 있다(${ts[tranche]['budget']}) — "
                             f"고치려면 --us-set-budget {tranche} --budget <금액>(체결을 추가하지 않는다)")
        left = ts[tranche]["left"]
        if tranche not in closed and rec["usd"] > left + US_TRANCHE_SLACK and not force:
            raise ValueError(f"체결 ${rec['usd']:,.2f} > {tranche}회차 잔액 ${left:,.2f} — 다음 회차 체결이면 먼저 "
                             f"--us-close {tranche}로 잔액을 닫고 기록한다(실제로 이 회차에 더 샀으면 --force)")
    cur.setdefault("fills", []).append(rec)
    if close and tranche not in (cur.get("closed_tranches") or []):
        cur.setdefault("closed_tranches", []).append(tranche)
    _check_cycle(cur)
    _us_write(d)
    st = us_tranches(cur)[tranche]
    rec = dict(rec, tranche_spent=st["spent"], tranche_left=st["left"], tranche_closed=st["closed"])
    return rec


def us_set_budget(tranche: int, budget: float, note: str = "", force: bool = False) -> dict:
    """★[10/22 리뷰 2차] 회차 금액 정정 — **체결을 추가하지 않는다**(舊 안내 '--force'는 체결 1건을 더하고 금액은 안 바꿨다).
    그 회차 첫 체결의 budget을 바꾸고 정정 이력을 남긴다. 닫은 회차(us_close)·뒤 회차에 체결이 있는 회차는 거부(순서가 뒤집힌다)."""
    d = _us_read()
    cur = d.get("cycle")
    if not cur:
        raise ValueError("열린 사이클이 없다")
    _check_cycle(cur)
    tranche, b = int(tranche), round(float(budget), 2)
    ts = us_tranches(cur)
    if tranche not in ts:
        raise ValueError(f"{tranche}회차는 체결 기록이 없다 — 첫 체결에 --budget으로 남긴다")
    if tranche in (cur.get("closed_tranches") or []):
        raise ValueError(f"{tranche}회차는 --us-close로 닫혔다 — 정정은 원장을 직접 본다")
    if ts[tranche]["budget"] is None:
        # ★[10/22 리뷰 3차] 회차 금액이 없는 옛 기록(= 한 번에 기록한 회차 · 9/22 1회차)은 닫힌 회차다 — 금액을 붙이면 다시 열려
        #   도래한 다음 회차가 그 '잔액' 뒤에 막힌다
        raise ValueError(f"{tranche}회차는 회차 금액 없이 한 번에 기록된 회차(닫힘)다 — 다시 열지 않는다")
    if any(k > tranche for k in ts):
        raise ValueError(f"{tranche}회차 뒤 회차에 이미 체결이 있다 — 앞 회차를 다시 열 수 없다")
    if b <= 0 or b < ts[tranche]["spent"] - US_TRANCHE_SLACK:
        raise ValueError(f"회차 금액 ${b:,.2f} < 이미 체결 ${ts[tranche]['spent']:,.2f}")
    cap = _us_cash_now() + ts[tranche]["spent"] + US_TRANCHE_SLACK
    if b > cap and not force:
        raise ValueError(f"회차 금액 ${b:,.2f} > 달러 잔고 + 이 회차 체결 ${cap - US_TRANCHE_SLACK:,.2f} — 자릿수 확인(확인한 예외면 --force)")
    first = next(f for f in cur["fills"] if int(f["tranche"]) == tranche)
    old = ts[tranche]["budget"]
    for f in cur["fills"]:
        if int(f["tranche"]) == tranche:
            f.pop("budget", None)
    first["budget"] = b
    cur.setdefault("budget_notes", []).append({"tranche": tranche, "date": _kst_today(), "old": old, "new": b, "note": note})
    _check_cycle(cur)
    _us_write(d)
    st = us_tranches(cur)[tranche]
    return {"tranche": tranche, "old": old, "budget": b, "spent": st["spent"], "left": st["left"], "closed": st["closed"]}


def us_close(tranche: int, note: str = "") -> dict:
    """진행 중 회차를 체결 없이 닫는다(잔액이 1달러 남짓이거나 정훈이 끝내기로 했을 때) — 다음 회차 간격은 마지막 체결 세션 기준."""
    d = _us_read()
    cur = d.get("cycle")
    if not cur:
        raise ValueError("열린 사이클이 없다")
    _check_cycle(cur)
    ts = us_tranches(cur)
    if tranche not in ts:
        raise ValueError(f"{tranche}회차는 체결 기록이 없다 — 닫을 것이 없다")
    if ts[tranche]["closed"]:
        raise ValueError(f"{tranche}회차는 이미 닫혔다")
    cur.setdefault("closed_tranches", []).append(int(tranche))
    cur.setdefault("close_notes", []).append({"tranche": int(tranche), "date": _kst_today(),
                                              "left_usd": ts[tranche]["left"], "note": note})
    _us_write(d)
    return {"tranche": int(tranche), "left_usd": ts[tranche]["left"]}


def _plain_add_months(d: dt.date, k: int) -> dt.date:
    """달력 월 더하기(말일 클램프 · 주말 보정 없음) — '이후' 판정용. 회차 일정용 _add_months와 다르다."""
    y, m = divmod(d.month - 1 + k, 12)
    y, m = d.year + y, m + 1
    feb = 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28
    last = [31, feb, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return dt.date(y, m, min(d.day, last))


def us_spacing(cur: dict) -> dict | None:
    """★[10/21 d251] 직전 회차의 마지막 체결 세션과 다음 회차를 열 수 있는 첫날.

    직전 회차 = 체결 기록이 있는 가장 큰 회차 번호. 한 회차가 여러 밤에 나뉘어 체결됐으면 **마지막** 세션 기준(보수적).
    세션이 없으면 KST 체결일을 쓴다(美 세션일 ≤ KST 체결일이라 늦게 풀리는 쪽). 날짜는 파싱해서 비교한다(문자열 max 금지).
    """
    fills = [f for f in (cur or {}).get("fills") or [] if f.get("tranche") is not None]
    if not fills:
        return None
    last_t = max(int(f["tranche"]) for f in fills)
    sess = [_iso_day(str(f.get("session") or f.get("date")), f"{last_t}회차 세션")
            for f in fills if int(f["tranche"]) == last_t]
    last = max(sess)
    earliest = _plain_add_months(last, US_SPACING_MONTHS)
    est = any(not f.get("session") for f in fills if int(f["tranche"]) == last_t)
    return {"last_tranche": last_t, "last_session": last.isoformat(), "earliest": earliest.isoformat(),
            "session_estimated": est}


def spacing_wait_until(sp: dict | None, remaining: list, gate_day: str) -> str | None:
    """d251 — 다음 회차를 아직 못 열면 열 수 있는 첫날, 열 수 있으면 None. gate_day = 지금의 美 세션일."""
    return sp["earliest"] if (sp and remaining and gate_day < sp["earliest"]) else None


def _first_night(st: dict | None, gate_day: str) -> bool:
    """★[10/22 리뷰 3차] 진행 중 회차가 **아직 첫 밤**인가 — 그 회차 체결이 전부 지금 美 세션이고 존 종목은 안 샀다.
    d235 ① '1주가 그 밤에 안 체결되면 그 몫까지 VOO' = 존 종목 1주는 **그 밤 동안** 유효하다. 舊 = VOO가 먼저 체결돼
    기록되면(시장가가 지정가보다 먼저 체결된다) 같은 밤의 ANET 1주 지정가를 '첫 밤의 몫이었다'며 막았다."""
    if not st or any(t in US_ZONE_TICKERS for t in st.get("tickers") or []):
        return False
    days = st.get("sessions") or []
    return bool(days) and all(d == gate_day for d in days)


def _partial_block(part: int, tickers: list, left: float, ticker: str | None, price,
                   first_night: bool = False) -> str | None:
    """진행 중 회차에서 **이 종목·이 가격**을 걸면 안 되는 이유(없으면 None) — us_buy_block 두 경로 공용.
    ★[10/22 리뷰 2차] 舊 = 진행 중 회차면 종목을 안 보고 None → ANET 1주 체결 뒤에도 '매일 등록' ANET을 다시 걸라고 했다
      (us_standing은 같은 상태에서 ANET = 'done'이라고 말했다 · 그대로 걸면 같은 회차에 ANET 2주 · 잔액 GOOGL·VOO 몫을 넘는다).
    ★[10/22 리뷰 3차] 존 종목(GEV·ANET·CDNS)만 본다 — 잔액의 행선지(GOOGL·VOO)는 막지 않는다(舊 = VOO를 먼저 산 회차에서
      VOO 잔액까지 '이미 체결'로 막았다). 진행 중 회차엔 존 종목을 **다시 걸지 않는다**: 존 종목이 체결됐으면 회차당 1종목(d235 ④),
      안 됐으면 그 1주는 회차 첫 밤의 몫이었다(d235 ① '1주가 그 밤에 안 체결되면 그 몫까지 VOO').
    price는 존 종목 1주 지정가일 때만 의미가 있다(잔액보다 비싸면 못 건다)."""
    if not ticker or ticker not in US_ZONE_TICKERS:
        return None
    if ticker in tickers:
        return f"{part}회차에 {ticker} 이미 체결 — 다시 걸지 않는다(잔액 ${left:,.2f} → GOOGL 18% → VOO)"
    zone_done = [t for t in tickers if t in US_ZONE_TICKERS]
    if zone_done:
        return f"{part}회차는 존 종목({zone_done[0]}) 체결 — 존 종목은 회차당 1종목(d235 ④) · 잔액 ${left:,.2f}은 GOOGL 18% → VOO"
    if isinstance(price, (int, float)) and price > left + US_TRANCHE_SLACK:
        return f"1주 ${price:,.2f} > {part}회차 잔액 ${left:,.2f} — 지정가 1주를 못 건다"
    if first_night:
        return None                    # 같은 밤 — 존 종목 1주 지정가는 잔액 안이면 아직 유효(d235 ①)
    return (f"{part}회차 진행 중 — 존 종목 1주는 회차 첫 밤의 몫이었다(d235 ① 안 체결되면 그 몫도 VOO) · "
            f"잔액 ${left:,.2f}은 GOOGL 18% → VOO")


def us_buy_block(us: dict | None = None, ticker: str | None = None, price=None) -> str | None:
    """미국 트랙 매수가 지금 **막혀 있으면 그 이유**, 아니면 None — order_check·notify 공용(d251·하드플로어).

    ★[10/22 리뷰 반영] 대기(wait)를 us_standing만 알고 있어서, 3회차 대기 중에도 order_check는 "ANET '매일 등록'
      오더가 토스에 없다 — 재등록 필요"를, notify는 "🔁 오늘 재등록"을 띄웠다 → 그대로 걸면 d251보다 한 달 먼저 3회차가 산다.
    · 진행 중 회차(잔액이 남은 회차)는 막지 않는다 — 같은 회차의 잔액 매수는 간격 대상이 아니다.
    · 하드플로어면 막는다(대기 회차가 없어도 — 상시 예약은 걸지 않는다 · 걸려 있으면 취소).
    · 원장이 깨졌으면 **그 사실을 이유로 막는다**(조용히 '사이클 없음'으로 읽지 않는다 — 고치기 전 매수 판단 보류).
    us를 주면 그 판정을 쓰고, 없으면 원장을 읽어 계산한다(시세 조회 없음 · 하드플로어는 vol_gauge 판정).
    ticker·price를 주면 진행 중 회차에서 그 종목을 다시 걸어도 되는지까지 본다(_partial_block).
    ★[10/22 리뷰 2차] 원장 경로에서 예상 못 한 예외도 **막는다**(舊 = 호출자가 삼켜 fail-open — 알림이 재등록을 띄웠다)."""
    if us is None:
        try:
            cur = _us_read().get("cycle")
            if cur:
                _check_cycle(cur)
        except UsLedgerError as e:
            return f"미국 트랙 원장 오류({e}) — 고치기 전 매수 판단 보류"
        if not cur:
            return "미국 트랙 사이클 없음"
        try:
            ts = us_tranches(cur)
            n = cur.get("n", US_TRANCHES)
            remaining = [i for i in range(1, n + 1) if not (i in ts and ts[i]["closed"])]
            if not remaining:
                return "미국 트랙 사이클 3회 완료(새 사이클 전 매수 없음)"
            halted, hwhy = global_contagion_check()
            if halted:
                return "하드플로어 — 예약 금지(걸려 있으면 취소)"
            if remaining[0] in ts:            # 진행 중 회차 — 잔액 매수는 간격 대상이 아니다(종목·가격만 본다)
                k = remaining[0]
                return _partial_block(k, ts[k]["tickers"], ts[k]["left"], ticker, price,
                                      first_night=_first_night(ts[k], _us_session_today()))
            w = spacing_wait_until(us_spacing(cur), remaining, _us_session_today())
            return f"d251 월 1회차 대기 — {w}부터" if w else None
        except Exception as e:  # noqa: BLE001
            return f"미국 트랙 판정 실패({type(e).__name__}) — 고치기 전 매수 판단 보류"
    if us.get("status") == "error":
        return f"미국 트랙 원장 오류({us.get('why', '')}) — 고치기 전 매수 판단 보류"
    if us.get("status") in ("complete", "no_cycle"):
        return "미국 트랙 " + ("사이클 3회 완료" if us["status"] == "complete" else "사이클 없음") + "(새 사이클 전 매수 없음)"
    if us.get("halted"):
        return "하드플로어 — 예약 금지(걸려 있으면 취소)"
    if us.get("status") == "partial":
        return _partial_block(us.get("partial_tranche"), us.get("partial_tickers") or [],
                              float(us.get("partial_left") or 0), ticker, price,
                              first_night=bool(us.get("partial_first_night")))
    if us.get("wait_until"):
        return f"d251 월 1회차 대기 — {us['wait_until']}부터"
    return None


def _last_close(sym: str):
    try:
        import drawdown_history as D
        ds, cs = D.load(sym)
        return (cs[-1], ds[-1]) if cs else (None, None)
    except Exception:
        return None, None


_LIVE: dict = {}


def _quote(sym: str) -> dict:
    """Yahoo 실시간 시세 1회 조회(프로세스 안 캐시). 실패하면 빈 dict."""
    if sym not in _LIVE:
        try:
            from market_data import fetch_quote
            _LIVE[sym] = fetch_quote(sym, timeout=6.0) or {}
        except Exception:
            _LIVE[sym] = {}
    return _LIVE[sym]


def _px(sym: str, live: bool = True):
    """(가격, 출처) — 실시간(Yahoo) 우선, 실패하면 일봉 캐시.
    ★[9/22] 캐시만 쓰면 하루 늦다 — 9/21 밤 GOOGL이 +2% 오르자 18%까지 남은 몫이
    캐시 기준 $88.52 vs 실시간 $78.79로 $10 갈렸다(회차의 4%). 제안 금액은 집행 시점 가격으로."""
    if live:
        p = _quote(sym).get("price")
        if p:
            return float(p), "live"
    px, d = _last_close(sym)
    return px, (f"cache {d}" if px else None)


def _prev_regular_close(sym: str, live: bool = True):
    """(오늘 밤 세션의 '전일 종가', 출처) — 지정가 +3% 상한(d254)의 기준.

    ★[10/21] 일봉 캐시는 美 마감(KST 05:00) 뒤 그날 16:10 대사 전까지 한 세션 늦다 — 10/21 낮에 캐시는 10/19 $182.95,
    실제 오늘 밤 기준은 10/20 종가였다. ⇒ 실시간이면 Yahoo 일봉을 history_backfill 규칙 그대로 다시 받는다 —
    **끝나지 않은 세션(정규장 끝+40분 전)의 봉은 빠지므로** 마지막 봉이 곧 다음(또는 진행 중) 세션의 전일 종가다.
    (chart meta엔 marketState가 비어 와서 '장 중인가'를 거기서 읽을 수 없다 — 10/21 실측.) 실패하면 캐시."""
    if live:
        key = ("prev", sym)
        if key not in _LIVE:
            try:
                import time as _t
                import history_backfill as HB
                got = HB.fetch_chart_result(sym, period1=int(_t.time()) - 14 * 86400, timeout=10.0)
                rows, gaps = HB.parse_chart(*got) if got else ([], [])
                # ★[10/22] 끝난 세션의 봉이 null이면(Yahoo 마감 뒤 몇 시간 흔하다) 마지막 봉은 한 세션 전이다 →
                #   그 세션 정규장 종가를 meta에서 읽는다(HB.settled_meta_close). 못 읽으면 舊 동작(한 세션 전 · 날짜가 표시된다).
                fill = None
                if got and gaps and (not rows or gaps[-1] > rows[-1][0]):
                    fill = HB.settled_meta_close(*got)
                    if not fill:                 # 다음 세션이 이미 열렸다 → 그 날짜 정규장 5분봉 마지막 값
                        px = HB.intraday_session_close(sym, gaps[-1])
                        fill = (gaps[-1], px) if px else None
                _LIVE[key] = ((fill[1], fill[0]) if fill
                              else (float(rows[-1][1]), rows[-1][0]) if rows else (None, None))
            except Exception:
                _LIVE[key] = (None, None)
        if _LIVE[key][0]:
            return _LIVE[key]
    return _last_close(sym)


def googl_room_usd(live: bool = True) -> dict:
    """GOOGL이 주식 평가액의 18%에 닿기까지 남은 달러(실시간 우선 · 실패 시 캐시 종가 — 제안용)."""
    try:
        with open(_PF_JSON, encoding="utf-8") as f:
            pf = json.load(f) or {}
    except Exception:
        return {"error": "portfolio.json 없음"}
    fx, fx_src = _px("KRW=X", live)
    if not fx:
        return {"error": "환율 없음"}
    tot = g = 0.0
    miss, srcs = [], set()
    for reg, rows in (pf.get("holdings") or {}).items():
        for h in rows:
            px, src = _px(h["ticker"], live)
            if src:
                srcs.add(src.split(" ")[0])
            if not px:
                miss.append(h["ticker"])
                continue
            v = float(h.get("shares") or 0) * px * (1 if reg == "kr" else fx)
            tot += v
            if h["ticker"] == "GOOGL":
                g = v
    if not tot:
        return {"error": "평가액 계산 불가"}
    room_krw = max(0.0, (US_GOOGL_CAP * tot - g) / (1 - US_GOOGL_CAP))
    return {"weight_pct": round(g / tot * 100, 1), "room_usd": round(room_krw / fx, 2),
            "fx": round(fx, 2), "missing": miss, "price_src": "+".join(sorted(srcs)) or None}


APPROACH_MARK = "접근"          # '👀 … 매수존 접근 $200 이하' = 예약 점검 알림이지 매수존이 아니다


def _us_zone_levels() -> dict:
    """우선순위 ②③④의 **매수존 상단**(portfolio.json alerts, cond=below)을 종목별로 하나씩.

    ★[2026-10-13 수정] 10/12 d235에서 '매수존 접근' 알림(ANET $200·GEV $945·CDNS $330)을 같은
    ticker·cond=below로 추가했는데, 여기가 종목당 알림을 하나로 가정하고 있어 **뒤에 온 접근선이
    승인된 존($190·$900·$315)을 덮어썼다**. 그 결과 us_standing이 "ANET 1주 지정가 $200"을 내놓았고
    `_zone_hits`는 $199에서 존 진입으로 판정할 뻔했다(= 승인가보다 5% 비싸게 회차를 쓴다).
    ⇒ 접근 알림은 id로 제외하고, 그래도 여럿이면 **가장 낮은 값**(= 더 보수적인 쪽)을 쓴다.
    """
    try:
        with open(_PF_JSON, encoding="utf-8") as f:
            alerts = (json.load(f) or {}).get("alerts") or []
    except Exception:
        return {}
    lv: dict = {}
    for a in alerts:
        t = a.get("ticker")
        if t not in US_ZONE_TICKERS or a.get("cond") != "below" or not a.get("level"):
            continue
        if APPROACH_MARK in str(a.get("id") or ""):
            continue
        v = float(a["level"])
        lv[t] = min(lv[t], v) if t in lv else v
    return lv


def _chase_limit(t: str, level: float, live: bool = True) -> dict:
    """★[10/21 d254] **추격 상한** = min(존 상단, 전일 정규장 종가 × 1.03) — 센트 내림. 이 위로는 1주를 사지 않는다.
    ⚠️ 반환 키 'limit'은 하위호환 이름일 뿐 **걸 가격이 아니다**(걸 가격 = 그날 토스 현재가·존 안 되돌림 가격 · PM 판단).
    전일 종가 = _prev_regular_close(실시간 우선 · 실패하면 일봉 캐시 마지막 확정 봉). 둘 다 없으면 존 상단 그대로."""
    prev, d = _prev_regular_close(t, live)
    if not prev:
        return {"limit": float(level), "prev_close": None, "prev_date": None, "capped": False}
    cap = math.floor(round(float(prev) * US_CHASE_CAP * 100, 6)) / 100   # round: 부동소수 102.9999… 내림 방지
    return {"limit": min(float(level), cap), "prev_close": round(float(prev), 2), "prev_date": d,
            "capped": cap < float(level)}


def _zone_hits(live: bool = True) -> list[dict]:
    """우선순위 ②③④(GEV·ANET·CDNS) 중 매수존(portfolio.json alerts, cond=below) 안에 든 종목.
    ★[10/21] 반환 순서 = 우선순위(US_ZONE_TICKERS) — alerts 순서가 아니다."""
    lv, out = _us_zone_levels(), []
    for t in US_ZONE_TICKERS:
        if t not in lv:
            continue
        px, d = _px(t, live)
        if px and px <= lv[t]:
            out.append({"ticker": t, "price": round(px, 2), "level": lv[t], "asof": d})
    return out


def _us_split(budget: float, zone: dict | None, live: bool = True) -> tuple[list[dict], dict]:
    """★[10/21 d235 ④ · d191] 한 회차의 배분 — 존 종목은 **최상위 1종목만**:
      · 정수 1주의 추격 상한(min(존 상단, 전일 종가×1.03)) ≤ 회차 금액 → 1주 지정가(걸 가격은 따로) + 잔액은 GOOGL 18% → VOO
      · 1주 > 회차 금액(GEV) → 회차 금액 전부 소수점 시장가(분수주 = 지정가 불가)
    舊 코드는 존 종목에 회차 전액을 주거나(zone_open 'ANET $366.87 전액' — d235 ④와 다름) 존 여러 개에 균등 분할했다(d191 순위 무시).
    GOOGL 여유 = 코드 공식(GOOGL만 산다고 가정한 18%까지 남은 몫 — 9/22 1회차와 같은 식, 10/21 d255 승인)."""
    split, left = [], float(budget)
    if zone:
        cl = _chase_limit(zone["ticker"], zone["level"], live)
        cap = cl["limit"]
        src = (f"min(존 ${zone['level']:,.0f}, 전일 종가 ${cl['prev_close']:,.2f}({cl['prev_date']})×1.03)"
               if cl["prev_close"] else f"존 상단 ${zone['level']:,.0f}(전일 종가 없음)")
        if cap <= left:
            est = min(float(zone["price"]), cap)              # 예상 체결가 = 현재가(상한 밑) — 잔액은 이걸로 추정
            cost = round(est * (1 + US_FEE), 2)
            split.append({"ticker": zone["ticker"], "usd": cost, "shares": 1, "order": "limit",
                          "chase_cap": cap, "est_fill": round(est, 2),
                          "why": (f"정수 1주 지정가 — 걸 가격은 토스 현재가(${zone['price']}) 근처·PM 판단, "
                                  f"**추격 상한 ${cap:,.2f}** 위로는 걸지 않는다({src}) · 잔액은 예상 체결가 ${est:,.2f}+수수료 기준")})
            left -= cost
        else:
            split.append({"ticker": zone["ticker"], "usd": round(left, 2), "order": "market_fraction",
                          "chase_cap": cap,
                          "why": f"매수존 안(${zone['price']}) · 1주 상한 ${cap:,.2f} > 회차 ${left:,.2f} → 소수점 시장가(당일 +3% 이상이면 다음 날 · 룰3)"})
            left = 0.0
    room = googl_room_usd(live)
    if left > 0 and not room.get("error"):
        g = min(left, room["room_usd"])
        if g >= 1:
            split.append({"ticker": "GOOGL", "usd": round(g, 2), "order": "market_fraction",
                          "why": f"비중 {room['weight_pct']}% → 18%까지 ${room['room_usd']:,.2f}"})
            left -= g
    if left >= 1:
        split.append({"ticker": "VOO", "usd": round(left, 2), "order": "market_fraction",
                      "why": (("존 종목 1주 뒤 잔액 · " if zone else "매수존 종목 없음 · ") + "GOOGL 18% 상한 → 지수로"
                              if not room.get("error") else "GOOGL 상한 계산 불가 → 확인 후 배분")})
    if zone and split and split[0].get("order") == "limit":
        split[0]["note"] = "잔액(GOOGL·VOO)은 1주 체결 뒤 **실제 체결가+수수료**로 다시 계산 — 위 금액은 추정"
    return split, room


def us_standing(per: float, halted: bool, live: bool = True, wait_until: str | None = None,
                exclude=(), zone_done: str | None = None, in_progress: bool = False) -> list[dict]:
    """★[10/12 d235 정훈 승인] 미국 트랙 후보의 매수존을 **회차일 하루**가 아니라 **상시** 본다.

    바꾸는 것은 '언제 가격을 보는가'뿐 — 회차 금액(잔고 ÷ 남은 회차)·월 1회차·하드플로어는 그대로다.
    그래서 **회차 금액 안에서 실제로 낼 수 있는 주문**만 상시 예약으로 내놓는다:
      · 정수 1주 ≤ 회차 금액 → 지정가 예약 가능. 단 **한 번에 한 종목만**(우선순위 최상위) —
        둘 다 걸어 두면 같은 밤에 둘 다 체결돼 회차 금액을 넘는다.
      · 정수 1주 > 회차 금액 → 분수주 = 시장가 전용이라 **예약 불가** → 가격 알림 후 수동 집행.
    하드플로어(halted)면 예약 자체를 걸지 않는다(걸려 있으면 취소).
    ★[10/21 d251] `wait_until`(다음 회차를 열 수 있는 첫날) 전이면 예약을 걸지 않는다 — 존에 닿아도 그 회차는 아직 없다.
    ★[10/21 d254] 추격 상한 = min(존 상단, 전일 종가 × 1.03) — 걸 가격은 그 밑에서 따로 정한다. 토스 미국 지정가는 1거래일 소멸(d128) → 매일 다시 건다.
    """
    lv = _us_zone_levels()
    out, slot_used = [], False
    for t in US_ZONE_TICKERS:                      # 튜플 순서 = 우선순위 ②③④
        if t not in lv:
            continue
        px, d = _px(t, live)
        cl = _chase_limit(t, lv[t], live)
        lim = cl["limit"]
        row = {"ticker": t, "level": lv[t], "price": round(px, 2) if px else None, "asof": d,
               "gap_pct": round((px / lv[t] - 1) * 100, 1) if px else None,
               "chase_cap": lim, "prev_close": cl["prev_close"], "prev_date": cl["prev_date"]}
        if halted:
            row.update({"mode": "off", "why": "하드플로어 — 예약 금지(걸려 있으면 취소)"})
        elif t in exclude:
            row.update({"mode": "done", "why": "이 회차에 이미 체결 — 다시 걸지 않는다(잔액은 GOOGL 18% → VOO)"})
        elif in_progress:
            # ★[10/22 리뷰 2차·3차] 진행 중 회차엔 존 종목을 다시 걸지 않는다 — 체결됐으면 회차당 1종목(d235 ④),
            #   안 됐으면 그 1주는 회차 첫 밤의 몫이었다(d235 ①). zone_done = 이 회차에 체결된 존 종목(없으면 None)
            row.update({"mode": "off", "why": (f"이 회차는 존 종목({zone_done}) 체결" if zone_done
                                               else "이 회차 진행 중(존 종목 1주는 첫 밤의 몫)") +
                        " — 다음 회차까지 걸지 않는다(잔액은 GOOGL 18% → VOO)"})
        elif wait_until:
            row.update({"mode": "wait", "why": f"월 1회차(d251) — {wait_until}부터 예약 가능(그 전엔 존에 닿아도 회차가 없다)"})
        elif lim > per:
            row.update({"mode": "alert", "usd": round(per, 2),
                        "why": f"1주 ${lim:,.2f} > 회차 ${per:,.2f} → 지정가 불가(분수주=시장가). 알림 뜨면 소수점 시장가"})
        elif slot_used:
            row.update({"mode": "alert", "usd": round(lim, 2),
                        "why": "상위 순위 예약이 이미 회차를 쓴다 → 알림만(동시 체결 = 회차 금액 초과)"})
        else:
            slot_used = True
            capw = (f" = min(존 ${lv[t]:,.0f}, 전일 종가 ${cl['prev_close']:,.2f}({cl['prev_date']})×1.03)"
                    if cl["prev_close"] else " (전일 종가 없음 → 존 상단)")
            row.update({"mode": "limit", "shares": 1, "usd": round(lim, 2),
                        "why": (f"정수 1주 지정가 예약 — **추격 상한 ${lim:,.2f}**{capw} ≤ 회차 ${per:,.2f} · "
                                "걸 가격은 그날 토스 현재가·존 안 되돌림 가격(상한 위 금지) · 매 거래일 재등록(d128)")})
        out.append(row)
    return out


def us_track(usd_cash: float | None = None, today: str | None = None, check_floor: bool = True,
             live: bool = True, session_day: str | None = None) -> dict:
    """미국 트랙 오늘 판정 — _us_track + 하드플로어 **판정 불가** 표시.
    ★[10/22 리뷰 3차] vol_gauge 실패(halted=None)는 현행 룰상 연기 사유가 아니다(국내 트랙·rule1과 같은 처리 — 바꾸려면 룰 변경 승인).
      다만 조용히 '도래'로만 보이면 플로어를 확인한 것처럼 읽힌다 → 집행 가능한 판정의 why에 판정 불가를 붙인다."""
    r = _us_track(usd_cash, today, check_floor, live, session_day)
    live_limit = any(x.get("mode") == "limit" for x in r.get("standing") or [])   # 대기 중이라도 상시 예약을 걸라고 한다(C9)
    if r.get("floor_unknown") and (r.get("status") in ("due", "zone_open", "partial") or live_limit):
        r["why"] = (r.get("why") or "") + f" · ⚠️ 하드플로어 판정 불가({r.get('halt_why')}) — 걸기 전 S&P 폭풍 확인"
    return r


def _us_track(usd_cash: float | None = None, today: str | None = None, check_floor: bool = True,
              live: bool = True, session_day: str | None = None) -> dict:
    """미국 트랙 오늘 판정 — 이번 회차에 쓸 수 있는 달러와 대상 제안.

    today = KST 날짜(회차일 비교) · session_day = 美 세션일(d251 간격 비교). 둘 다 생략하면 지금 시각.
    today만 주면 그 값을 세션일로도 쓴다(CLI --date·검정 호환). order_check --now는 둘을 따로 준다."""
    if usd_cash is None:
        usd_cash = _us_cash_now()
    today_given = today is not None
    today = today or _kst_today()
    out = {"usd_cash": round(usd_cash, 2), "today": today, "rule": "d205"}
    try:
        cur = _us_read().get("cycle")
        if cur:
            _check_cycle(cur)
            sp = us_spacing(cur)
    except UsLedgerError as e:
        # ★[10/22] 깨진 원장은 '사이클 없음'이 아니다 — 판정을 멈추고 이유를 그대로 낸다(앱·알림·validate가 보인다)
        out.update({"status": "error", "allowed_usd": 0.0, "why": str(e)})
        return out
    if not cur:
        out.update({"status": "no_cycle", "allowed_usd": 0.0,
                    "why": (f"열린 사이클 없음 — 달러 ${usd_cash:,.2f} ≥ ${US_MIN_CYCLE_USD:.0f}이면 "
                            "`tranche_rules.py --us-start`로 연다") if usd_cash >= US_MIN_CYCLE_USD
                    else f"열린 사이클 없음 · 달러 ${usd_cash:,.2f} < ${US_MIN_CYCLE_USD:.0f}"})
        return out
    n, sched = cur.get("n", US_TRANCHES), cur.get("schedule") or []
    fills = cur.get("fills") or []
    ts = us_tranches(cur)
    done = sorted(k for k, s in ts.items() if s["closed"])
    remaining = [i for i in range(1, n + 1) if i not in done]
    part = remaining[0] if remaining and remaining[0] in ts else None      # 진행 중 회차(잔액이 남았다)
    left = min(ts[part]["left"], usd_cash) if part else 0.0
    zdone = next((t for t in ts[part]["tickers"] if t in US_ZONE_TICKERS), None) if part else None   # 이 회차에 체결된 존 종목
    due = [i for i, d in enumerate(sched, 1) if d <= today]
    pending = [i for i in due if i not in done]
    # 회차 금액 = 그날 잔고 ÷ 남은 회차. 진행 중 회차가 있으면 그 잔액을 뺀 나머지를 그 뒤 회차들이 나눈다.
    if part:
        later = len(remaining) - 1
        per = (usd_cash - left) / later if later else 0.0
    else:
        per = usd_cash / len(remaining) if remaining else 0.0
    # ★[10/21 d251] 한 번에 한 회차 — 밀린 회차가 둘이어도 몰아 사지 않는다(舊 = per × 밀린 회차 수).
    allowed = per if pending else 0.0
    halted, hwhy = (global_contagion_check() if check_floor else (False, "하드플로어 판정 생략"))
    nxt = next((sched[i - 1] for i in remaining if i != part and sched[i - 1] > today), None)
    # ★[10/22] 간격 게이트는 **세션일**로 본다 — today를 직접 주면 그 값을 세션일로 쓴다(CLI --date·검정).
    gate_day = session_day or (today if today_given else _us_session_today())
    wait_until = None if part else spacing_wait_until(sp, remaining, gate_day)
    first = bool(part) and _first_night(ts[part], gate_day)                 # 진행 중 회차의 첫 밤(존 1주 아직 유효)
    if wait_until:
        nxt = wait_until                       # ★[10/22] 앱·문구의 '다음 회차' = 실제로 열 수 있는 첫날(회차일이 지났어도)
    out.update({"cycle_start": cur.get("start"), "schedule": sched, "n": n,
                "done": done, "due": due, "pending": pending,
                "per_tranche_usd": round(per, 2), "next_date": nxt,
                "halted": bool(halted), "halt_why": hwhy, "floor_unknown": bool(check_floor and halted is None),
                "spacing": sp, "wait_until": wait_until, "gate_day": gate_day,
                "spent_usd": round(sum(float(f.get("usd") or 0) for f in fills), 2),
                "fills": fills})
    if part:
        out.update({"partial_tranche": part, "partial_left": round(left, 2),
                    "partial_budget": ts[part]["budget"], "partial_spent": ts[part]["spent"],
                    "partial_tickers": ts[part]["tickers"], "partial_first_night": first})
    if remaining:
        # ★[10/12 d235] 다음 미집행 회차 금액 한도 안의 상시 예약(회차일 전에도 존이 닿으면 그 회차가 집행된다)
        #   진행 중 회차면 그 잔액이 한도이고, 그 회차에 이미 산 종목은 다시 걸지 않는다.
        out["standing"] = us_standing(left if part else per, bool(halted), live, wait_until,
                                      exclude=ts[part]["tickers"] if part else (), zone_done=zdone,
                                      in_progress=bool(part) and not first)
        out["standing_tranche"] = remaining[0]
    if not remaining:
        out.update({"status": "complete", "allowed_usd": 0.0,
                    "why": "사이클 3회 완료" + (f" — 달러 ${usd_cash:,.2f} ≥ ${US_MIN_CYCLE_USD:.0f}: 새 사이클 가능"
                                                if usd_cash >= US_MIN_CYCLE_USD else "")})
        return out
    if halted and (pending or part):
        k = part or pending[0]
        out.update({"status": "deferred", "allowed_usd": 0.0,
                    "why": f"회차 {k} " + ("잔액" if part else "도래") + f"했으나 하드플로어로 **연기** — {hwhy}"})
        return out
    if part:
        # ★[10/22 리뷰 반영] 같은 회차의 잔액 — d251 간격 대상이 아니다(회차를 새로 여는 게 아니다).
        #   잔액은 GOOGL 18% → VOO만 — 존 종목은 다시 보지 않는다: 체결됐으면 회차당 1종목(d235 ④),
        #   안 됐으면 그 1주는 회차 첫 밤의 몫이었다(d235 ① 안 체결되면 그 몫까지 VOO · 회차일을 늦추지 않는다).
        #   ★[10/22 리뷰 2차·3차] 舊 = '아직 안 산 존 종목'을 다시 후보로 봐 잔액 전부를 CDNS·GEV 소수점 시장가로,
        #   VOO를 먼저 산 회차에선 다음 날 ANET을 다시 제안했다.
        split, room = _us_split(left, None, live)
        for x in split:
            if x["ticker"] == "VOO":
                x["why"] = f"{part}회차 잔액 · GOOGL 18% 상한 → 지수로"
        b = ts[part]["budget"]
        # ★[10/22 리뷰 2차] 뒤 회차의 회차일이 지났으면 말한다 — 잔액이 $1 넘게 남은 회차는 저절로 안 닫혀 다음 회차가 조용히 밀린다
        later = [i for i in pending if i != part]
        lat = (f" · ⚠️ {later[0]}회차 회차일({sched[later[0] - 1]}) 지남 — 잔액을 집행하거나 --us-close {part}로 닫아야 "
               f"{later[0]}회차가 열린다(d251 간격 = 마지막 체결 세션 기준)") if later else ""
        if first:
            lat += (f" · 첫 밤(세션 {gate_day}) — 존 종목 1주 지정가는 잔액 안이면 오늘 밤까지 유효(d235 ①) · "
                    "안 체결되면 그 몫도 VOO")
        else:
            # ★[10/22 리뷰 3차 C7] 잔액을 사면 d251 간격이 **그 세션부터** 다시 센다 — 작으면 닫는 편이 낫다
            lat += (f" · 잔액을 사면 다음 회차 간격(d251)이 그 체결 세션부터 다시 센다 — 소액이면 --us-close {part}")
            if sp and len(remaining) > 1 and gate_day >= sp["earliest"]:
                lat += f"(닫으면 {remaining[1]}회차를 바로 열 수 있다)"
        out.update({"status": "partial", "allowed_usd": round(left, 2), "split": split, "googl": room,
                    "why": (f"{part}회차 진행 중 — 회차 금액 ${b:,.2f} 중 ${ts[part]['spent']:,.2f} 체결"
                            f"({'·'.join(ts[part]['tickers'])}) · **잔액 ${left:,.2f}** — 같은 회차라 d251 간격 대상 아님{lat}")})
        return out
    if wait_until:
        est = " · 세션 미기재 → KST 체결일로 계산" if sp.get("session_estimated") else ""
        out.update({"status": "spacing_wait", "allowed_usd": 0.0,
                    "why": (f"월 1회차(d251) — {sp['last_tranche']}회차 체결 세션 {sp['last_session']} + 1개월 = "
                            f"**{wait_until}부터** {remaining[0]}회차(회차일 {sched[remaining[0] - 1]}"
                            + (" 도래)" if pending else ")") + est)})
        return out
    if not pending:
        # ★[10/12 d235] 회차일 전이라도 후보가 매수존 안이면 다음 회차를 그 종목으로 집행한다(회차당 1회 · 금액 불변).
        zh = [] if halted else _zone_hits(live)
        if zh:
            z = zh[0]                               # _zone_hits가 우선순위 순서로 준다
            split, room = _us_split(per, z, live)
            out.update({"status": "zone_open", "allowed_usd": round(per, 2), "split": split, "googl": room,
                        "why": f"{z['ticker']} 매수존 진입 — {remaining[0]}회차 ${per:,.2f}를 회차일({sched[remaining[0] - 1]}) 전에 집행 가능(d235 · 회차일 재집행 없음)"})
            return out
        out.update({"status": "waiting", "allowed_usd": 0.0,
                    "why": f"다음 회차 {nxt} (회차당 약 ${per:,.2f} — 그날 잔고로 다시 계산)"})
        return out
    # 대상 제안 — 매수존 안 **최상위 1종목**(d191 ②>③>④) → GOOGL 18% 상한 → VOO
    zones = _zone_hits(live)
    split, room = _us_split(allowed, zones[0] if zones else None, live)
    extra = f" · 밀린 회차 {pending[1:]}는 몰아 사지 않는다(d251)" if len(pending) > 1 else ""
    if zones and split and split[0].get("order") == "limit":
        extra += f" · {zones[0]['ticker']} 1주가 이 밤에 안 체결되면 그 몫까지 VOO(회차일은 늦추지 않는다 · d235 ①)"
    out.update({"status": "due", "allowed_usd": round(allowed, 2), "split": split, "googl": room,
                "why": f"회차 {pending[0]} 도래 — ${allowed:,.2f} (잔고 ${usd_cash:,.2f} ÷ 남은 {len(remaining)}회){extra}"})
    return out


def global_contagion_check():
    """하드 플로어 — 이 개정의 전제(국내 구조 사건)가 깨졌는지 본다.

    §0 프레임의 근거는 '저점 VIX 17.1 = 글로벌 위기 아님'이다. S&P500이 스톰에
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
    # ★[2026-10-20] 美 정규장 중(22:30~05:40 KST)엔 판독에 장중 봉이 들어간다 — 판정은 그대로 두고 **표시만** 한다
    #   (장중 판독이 그 세션 확정 판독과 더 가깝다: 70 경계 불일치 0.99% vs 전일 확정 3.57% · vol_gauge.closes_with_meta).
    note = vol_gauge.provisional_note(r) if hasattr(vol_gauge, "provisional_note") else ""
    tail = f" · {note}" if note else ""
    if pct >= 70:
        return True, f"🚨 S&P500 폭풍 {pct:.0f}%ile ≥70 = **글로벌 확산** → 사다리 전면 정지{tail}"
    return False, f"S&P500 폭풍 {pct:.0f}%ile <70 = 국지 유지(개정 전제 성립){tail}"


def rule1_ladder(cash: float, dd_pct: float, storm_pct, fear_pct=None, capit_pct=None,
                 check_contagion: bool = True, use_ledger: bool = True, kr_weight=None):
    """★[2026-10-01 d223 폐기 · 정훈 승인] **舊 낙폭 사다리 판정 — 현행 룰이 아니다.**
    과거 검정(rule_tracker --backfill·ratchet_test·d0_test·ladder_dca_test)의 재현용으로만 남긴다.
    현행 룰1 = `rule1()`(원화 6개월 균등 분할 = `kr_track()`).

    kr_weight = 국내주 비중 %(주식 기준). 주면 d207 룰6 우선 게이트를 적용한다 —
    None이면 게이트 없음(백테스트·rule_tracker --backfill 하위호환)."""
    unlocked, steps = ladder_state(dd_pct)
    splits, swhy = _storm_splits(storm_pct)

    # 이미 집행한 단계는 해금돼 있어도 **가용분에서 뺀다**(단계 재진입 금지).
    done = ledger_executed() if use_ledger else {}
    # 두 가지 합계를 **따로** 센다 — 쓰임이 다르다.
    #   spent_krw   = **해금된 단계**의 기집행 → 오늘 여력에서 차감할 금액
    #   total_spent = **모든 단계**의 기집행   → base(총 재원) 복원용
    # ⚠️ 9/9 실측: 이 둘을 하나로 쓰면 잠긴 단계의 집행분이 base에서도 빠져
    #    재원이 과소 계산된다(오늘 D1이 잠기자 base가 125,598원만큼 줄었다).
    #    "총 재원"은 낙폭과 무관하게 이미 쓴 돈을 포함해야 한다.
    spent_krw = 0.0
    total_spent = 0.0
    for i, s in enumerate(steps, 1):
        s["executed"] = i in done
        if s["executed"]:
            s["executed_on"] = done[i].get("date")
            s["executed_krw"] = done[i].get("amount")
            s["executed_n"] = done[i].get("n")
            amt = float(done[i].get("amount") or 0)
            total_spent += amt
            if s["unlocked"]:
                spent_krw += amt
    available = unlocked   # 해금 비율 자체는 낙폭이 정한다(RESET). 소진은 금액으로 뺀다.
    spent_ratio = (spent_krw / cash) if cash else 0.0

    capit = (fear_pct is not None and capit_pct is not None
             and fear_pct >= 90 and capit_pct >= 90)
    mult = CAPITULATION_BONUS if capit else 1.0
    mult = max(MULT_FLOOR, min(MULT_CAP, mult))

    # 백테스트(rule_tracker --backfill)는 수천 번 호출하므로 네트워크 조회를 끈다.
    halted, hwhy = global_contagion_check() if check_contagion else (False, '확산 판정 생략(백테스트)')
    # 누적 상한 = 해금분 전체. 여기서 **이미 집행한 금액**을 뺀 잔여가 오늘 여력이다.
    #
    # ★[2026-09-09 정정 — 이중 차감 제거 · 정훈 지시 "룰1 상한 계산 방식 좀 바꿔보자"]
    # 舊: cap = cash * available * mult  ← **현재 현금**이 분모였다.
    #   그러면 집행이 두 번 깎인다: ①사면 cash가 줄어 cap이 작아지고 ②spent_krw로 또 뺀다.
    #   설계 의도는 §2b가 적은 대로 "**총 재원**을 낙폭 단계별로 나눠 쓴다"인데,
    #   재원을 '매일의 잔액'으로 잡으면 사다리가 낙폭이 아니라 **현금 잔액**을 따라간다.
    #   실측(rule_log): 8/26 낙폭 -25.3%·현금 69.4만 → 상한 104,070 /
    #                   8/28 낙폭 -25.5%·현금 145.5만 → 상한 183,583.
    #   **낙폭은 0.2%p 차이인데 상한이 76% 뛰었다 — 상한을 움직인 건 낙폭이 아니라 입금이었다.**
    # 新: base = cash + spent_krw  (집행해도 불변 · 입금·매도로만 증가)
    #   → 같은 낙폭이면 같은 상한. 이게 "낙폭 사다리"라는 이름에 맞는 동작이다.
    # ⚠️ 효과는 크지 않다(8/24 +5,200원·9/03 +18,840원). **이건 정확성 수정이지 완화가 아니다** —
    #    진짜 병목은 D1 문턱(-25%)이고 그건 8/5 룰 검정 절차를 거쳐야 바꿀 수 있다.
    base = cash + total_spent      # 총 재원 = 남은 현금 + 이미 사다리로 쓴 돈(잠긴 단계 포함)
    cap = base * available * mult

    # ★[2026-09-21 정훈 승인 d197 — "버킷 해석" 폐기, 누적 해석 확정]
    # 舊: allowed = cap - spent_krw  (spent_krw = **해금된 단계**의 기집행만)
    #   → 잠긴 단계의 집행이 cap에서도 spent에서도 같이 빠져 "닫힌 버킷"처럼 동작했다.
    #   내부모순은 없었지만 **회복 구간에서 사다리가 매수를 자금지원**했다:
    #   9/20 실측 = 낙폭 -26.3%→-24.36%로 D1이 잠긴 날, D1에 쓴 243,437원이 통째로 면제돼
    #   **잔여 60,565원이 새로 생겼다** — 코스피 +2.66% 반등 당일에.
    # 新: allowed = cap - total_spent  (전체 기집행 차감 = 누적 상한)
    #   근거 = 정본 두 곳이 이미 답을 적어두고 있었다:
    #     · CLAUDE.md 룰1 RESET — *"누적 상한이지 목표 아님"*
    #     · crash_tf.md §2b   — ***"회복 구간의 매수는 사다리 소관이 아니다"***
    #       (예비 해금과 §5 해제 3중 게이트가 다룬다)
    #   버킷 해석은 D1의 예산만 회수하고 **지출은 사면**하므로 **부분 래칫**이고,
    #   래칫은 7/31 `ratchet_test.py`(11지수 24,592일)에서 3개 구간 전부 기각됐다.
    # ⚠️ 두 해석은 **회복 국면에서만** 갈린다. 하강 국면(집행 단계가 전부 해금)에선
    #    spent_krw == total_spent라 값이 **완전히 같다** — 완화도 긴축도 아니고
    #    "되돌리면 다시 잠긴다"를 지출 쪽까지 일관되게 적용하는 것이다.
    #    실측 대조(9/21): D0 버킷 60,565 vs 누적 0 / D1·D2는 둘 다 38,446·333,538로 동일.
    # ⚠️ D0 신설(9/9) 취지와 충돌하지 않는다 — 그건 *문이 닫혀 상한이 0*이던 문제였고,
    #    지금은 문이 열려 있는데 **이미 예산을 2.55배 초과 집행**(300,909 vs 118,037)한 상태다.
    allowed = 0.0 if halted else max(0.0, cap - total_spent)
    ladder_allowed = allowed                  # 룰6 게이트 전 = 사다리 자체 판정(적립 기록용)
    rule6_block = kr_weight is not None and kr_weight > RULE6_KR_HI
    if rule6_block:
        allowed = 0.0

    return {
        "dd_pct": dd_pct, "cash": cash,
        "unlocked_ratio": unlocked, "steps": steps,
        "spent_ratio": spent_ratio, "available_ratio": available,
        "spent_krw": round(total_spent), "cap_krw": round(cap), "base_krw": round(base),
        "spent_unlocked_krw": round(spent_krw),                       # 舊 버킷 해석 대조용
        "allowed_bucket_krw": round(max(0.0, cap - spent_krw)),       # 둘이 갈리면 = 회복 국면
        "executed_steps": sorted(done),
        "storm_splits": splits, "storm_why": swhy,
        "storm_mult": 1.0,   # 하위호환(원장 스키마) — 금액 감산 폐지로 항상 1.0
        "capitulation": capit,
        "capitulation_why": (f"공포 {fear_pct:.0f}%ile·항복 {capit_pct:.0f}%ile 동반 90+ → ×{CAPITULATION_BONUS}"
                             if capit else "항복 가산 미충족"),
        "final_mult": round(mult, 3),
        "halted": bool(halted), "halt_why": hwhy,
        "allowed_krw": round(allowed),
        "ladder_allowed_krw": round(ladder_allowed),
        "kr_weight_pct": round(kr_weight, 1) if kr_weight is not None else None,
        "rule6_block": bool(rule6_block),
        "rule6_why": (f"룰6 우선(d207) — 국내주 {kr_weight:.1f}% > {RULE6_KR_HI:.0f}% → 판정·적립만, 집행 0원"
                      if rule6_block else
                      (f"룰6 게이트 통과 — 국내주 {kr_weight:.1f}% ≤ {RULE6_KR_HI:.0f}%" if kr_weight is not None
                       else "룰6 게이트 미적용(비중 미입력)")),
        "reserve_ratio": RESERVE,
    }


# ─────────────────────────────────────────── 룰 1 (현행): 국내 트랙 = 원화 6개월 균등 분할
#
# ★[2026-10-01 d223 · 정훈 승인 "나머지 승인은 다 승인할게"] 낙폭 사다리(D0~D4·예비 7%·RESET·항복 가산) 폐기 →
#   **코스피 고점대비 -20% 이하에서 원화를 6회(월 1회) 균등 분할**. 하드플로어·룰6 우선은 그대로.
#
# 근거 = `ladder_dca_test.py`(9/30 · 사전등록 판정). 사다리(LF)는 "같은 원화를 6개월 균등 분할"에 ①②③ 전패:
#   ① 12M 중앙 LF−DCA6 **-3.95%p**(현금 2.5%에도 -2.83) · 24M -9.89%p
#   ② 에피소드 사다리 우위 **1/6**   ③ 22개 시장 중 사다리 우위 **2/22**(Holm 보정 p 4e-4)
#   하드플로어를 유지한 DCA6F(= 이 구현)도 같다: 12M -3.28%p · ② 1/6 · ③ 3/22.
#   시차 1일·항복 가산 상시·사다리+해제 변형 전부 같은 판정. 손익분기 현금금리 연 8.4~10.1%.
# ⚠️ **사다리가 나았던 것 = 꼬리**(사다리는 평균 26%만 넣어서 덜 잃는다 — 12M 하위 5% 최종자산 DCA6F 0.85).
#    이 교체는 **더 일찍·더 많이 투자하는** 결정이다. 꼬리를 줄이는 수단은 속도가 아니라 총량이다
#    (룰6 국내 18~22% 상한이 그 역할을 한다).
# ⚠️ 검정은 **조건부 시작점(낙폭 ≤ -20%)**만 본다. 평시(-20% 위)엔 이 룰이 말하지 않는다 —
#    그때의 국내 매수는 매수존·룰3·룰6 판단이다(무조건 시작점에선 사다리와 DCA6가 비등했다).
# 정본 = docs/research/ladder_dca_test_2026-09-30.md · crash_tf §2b.
KR_TRACK = os.path.join(ROOT, "data", "app", "kr_track.json")
KR_TRANCHES = 6
KR_TRIGGER_DD = -20.0        # 이 낙폭 이하에서만 사이클이 열린다(검정의 조건부 시작점과 같은 문턱)
KR_MIN_CYCLE_KRW = 50_000    # 이보다 적은 원화로는 사이클을 열지 않는다(국내는 정수 1주 이상)
KR_RULE = ("d223 — 코스피 낙폭 ≤-20%에서 원화 6회 균등 분할(월 1회) · 회차=그날 원화÷남은 회차 · "
           "S&P 폭풍≥70이면 연기 · 국내주>22%면 집행 0원(룰6 우선)")


KR_EXPIRE_DAYS = 31          # 마지막 회차일에서 이만큼 지나도 미집행이면 사이클 만료(영원히 열려 있지 않게)


class KrLedgerError(RuntimeError):
    """국내 트랙 원장이 있는데 읽을 수 없다 — **빈 원장으로 취급하면 안 된다**(이미 집행한 회차를 잊고 또 연다)."""


def _kr_read() -> dict:
    if not os.path.exists(KR_TRACK):
        return {}
    try:
        with open(KR_TRACK, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        raise KrLedgerError(f"국내 트랙 원장 손상({os.path.basename(KR_TRACK)}): {e}") from e
    if d is None:
        return {}
    if not isinstance(d, dict) or not isinstance(d.get("cycle") or {}, dict):
        raise KrLedgerError(f"국내 트랙 원장 형식 오류({os.path.basename(KR_TRACK)}) — dict가 아니다")
    cur = d.get("cycle")
    if cur and cur.get("start") and len(cur.get("schedule") or []) != cur.get("n", KR_TRANCHES):
        cur["schedule"] = us_schedule(cur["start"], cur.get("n", KR_TRANCHES))   # 일정 누락 → 시작일로 복원
    return d


def _kr_done(cur) -> list:
    """집행된 회차(1..n 범위의 정수만 — 범위 밖 기록이 완료 판정을 속이지 못하게)."""
    n = (cur or {}).get("n", KR_TRANCHES)
    return sorted({f.get("tranche") for f in (cur or {}).get("fills", [])
                   if isinstance(f.get("tranche"), int) and 1 <= f.get("tranche") <= n})


def _kr_current(cur, today: str):
    """오늘 기준 **현재 회차**(도래한 회차 중 가장 최근) — 없으면 None."""
    due = [i for i, d in enumerate(cur.get("schedule") or [], 1) if d <= today]
    return max(due) if due else None


def _kr_write(d: dict):
    d["updated"] = _kst_today()
    os.makedirs(os.path.dirname(KR_TRACK), exist_ok=True)
    with open(KR_TRACK, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def _kr_cycle_open(cur, today: str | None = None) -> bool:
    """열림 = 마지막 회차가 아직 집행 안 됐고 만료 전. (중간 회차를 건너뛰었어도 마지막 회차를 쓰면 끝난다.)"""
    if not cur:
        return False
    n, sched = cur.get("n", KR_TRANCHES), cur.get("schedule") or []
    if n in _kr_done(cur):
        return False
    if sched:
        last = dt.date.fromisoformat(sched[-1]) + dt.timedelta(days=KR_EXPIRE_DAYS)
        if (today or _kst_today()) > last.isoformat():
            return False
    return True


def kr_start(start: str | None = None, pool_krw: float | None = None, dd_pct: float | None = None,
             note: str = "", force: bool = False) -> dict:
    """국내 트랙 새 사이클. 진행 중이면 거부(회차 건너뛰기) · 낙폭이 -20% 위면 거부(룰 대상 아님)."""
    d = _kr_read()
    cur = d.get("cycle")
    start = start or _kst_today()
    if _kr_cycle_open(cur, start):
        raise ValueError(f"진행 중 사이클({cur.get('start')})이 끝나지 않았다 — 회차를 건너뛰는 재시작 금지")
    if not force and (dd_pct is None or dd_pct > KR_TRIGGER_DD):
        raise ValueError(f"코스피 낙폭 {dd_pct}% > {KR_TRIGGER_DD:.0f}% — 룰1 대상 구간이 아니다(--force로만 개시)")
    if not force and pool_krw is not None and pool_krw < KR_MIN_CYCLE_KRW:
        raise ValueError(f"원화 {pool_krw:,.0f}원 < {KR_MIN_CYCLE_KRW:,}원 — 사이클을 열 재원이 없다(--force로만 개시)")
    if cur:
        d.setdefault("history", []).append(cur)
    d["cycle"] = {"start": start, "n": KR_TRANCHES, "schedule": us_schedule(start, KR_TRANCHES),
                  "pool_krw_at_start": pool_krw, "dd_at_start": dd_pct, "fills": [], "note": note}
    d["rule"] = KR_RULE
    _kr_write(d)
    return d["cycle"]


def kr_execute(krw: float, ticker: str, tranche: int | None = None, note: str = "",
               date: str | None = None, dd_pct: float | None = None, force: bool = False) -> dict:
    """회차 집행 기록. **조회·기록 전용 — 주문을 내지 않는다.**
    열린 사이클이 없으면 체결일로 연다(1회차 = 시작일) — 단 낙폭이 -20% 위면 거부한다(force 제외)."""
    if not float(krw or 0) > 0:
        raise ValueError(f"집행 금액 {krw} — 0원 이하는 회차 집행이 아니다")
    date = date or _kst_today()
    d = _kr_read()
    if not _kr_cycle_open(d.get("cycle"), date):
        kr_start(date, None, dd_pct, note="첫 집행으로 개시", force=force)
        d = _kr_read()
    cur = d["cycle"]
    now_k = _kr_current(cur, date) or 1
    # ★[10/1 검토 반영] 회차 미지정 = **현재 회차**. 舊 '다음 미집행 회차'는 같은 달에 두 번 기록하면(두 종목·분할 체결)
    #   둘째 건이 다음 달 회차로 잡혀 그 달이 통째로 사라졌다. 한 회차에 여러 건이 붙는 건 정상이다.
    if tranche is None:
        tranche = now_k
    tranche = int(tranche)
    if not 1 <= tranche <= cur["n"]:
        raise ValueError(f"회차 {tranche} — 1~{cur['n']} 범위 밖")
    if tranche > now_k and not force:
        raise ValueError(f"회차 {tranche}는 아직 도래 전(현재 {now_k}회) — 회차를 앞당기지 않는다(--force로만)")
    rec = {"date": date, "tranche": tranche, "krw": round(float(krw)),
           "ticker": ticker, "note": note}
    cur.setdefault("fills", []).append(rec)
    _kr_write(d)
    return rec


def kr_track(krw_cash: float, dd_pct: float | None, today: str | None = None, check_floor: bool = True,
             kr_weight=None, use_ledger: bool = True) -> dict:
    """국내 트랙 오늘 판정 — 이번 회차에 쓸 수 있는 원화(상한이지 목표 아님 · 자동 집행 아님)."""
    today = today or _kst_today()
    krw_cash = float(krw_cash or 0)
    ledger_err = None
    try:
        cur = _kr_read().get("cycle") if use_ledger else None
    except KrLedgerError as e:
        cur, ledger_err = None, str(e)
    rule6_block = kr_weight is not None and kr_weight > RULE6_KR_HI
    rule6_why = (f"룰6 우선(d207) — 국내주 {kr_weight:.1f}% > {RULE6_KR_HI:.0f}% → 집행 0원 · 원화는 미국 트랙으로(d207 ②)"
                 if rule6_block else
                 (f"룰6 게이트 통과 — 국내주 {kr_weight:.1f}% ≤ {RULE6_KR_HI:.0f}%" if kr_weight is not None
                  else "룰6 게이트 미적용(비중 미입력)"))
    out = {"krw_cash": round(krw_cash), "dd_pct": dd_pct, "today": today, "rule": "d223", "n": KR_TRANCHES,
           "rule6_block": bool(rule6_block), "rule6_why": rule6_why,
           "kr_weight_pct": round(kr_weight, 1) if kr_weight is not None else None,
           "pre_gate_krw": 0, "per_tranche_krw": 0,
           "schedule": [], "done": [], "due": [], "pending": [], "skipped": [], "fills": [], "spent_krw": 0}
    # ★[10/1 검토 반영] 하드플로어는 **회차 유무와 무관하게 매일 판정**한다 — 초안은 회차가 있을 때만 봐서
    #   평시·대기 중엔 halted가 늘 False로 원장(rule_log)에 남았다(플로어가 켜진 날을 기록에서 잃는다).
    halted, hwhy = (global_contagion_check() if check_floor else (False, "하드플로어 판정 생략"))
    out.update({"halted": bool(halted), "halt_why": hwhy})
    if ledger_err:
        out.update({"status": "unknown", "allowed_krw": 0,
                    "why": f"{ledger_err} — 집행 이력을 읽을 수 없어 판정 불가(빈 원장으로 보고 새로 열지 않는다)"})
        return out

    def _gate(allowed, status_ok, why_ok):
        """하드플로어 → 룰6 순으로 막는다. pre_gate = 두 게이트 전 금액(기록용)."""
        out.update({"pre_gate_krw": round(allowed)})
        if halted:
            out.update({"status": "deferred", "allowed_krw": 0,
                        "why": f"회차 몫 {allowed:,.0f}원이 있으나 하드플로어로 **연기** — {hwhy}"})
        elif rule6_block:
            out.update({"status": "rule6_block", "allowed_krw": 0,
                        "why": f"회차 몫 {allowed:,.0f}원이 있으나 {rule6_why}"})
        else:
            out.update({"status": status_ok, "allowed_krw": round(allowed), "why": why_ok})
        return out

    if not _kr_cycle_open(cur, today):
        done_note = " (직전 사이클 종료)" if cur else ""
        if dd_pct is None:
            out.update({"status": "unknown", "allowed_krw": 0, "why": "코스피 낙폭 미확인 — 판정 불가"})
        elif dd_pct > KR_TRIGGER_DD:
            out.update({"status": "idle", "allowed_krw": 0,
                        "why": f"낙폭 {dd_pct:+.1f}% > {KR_TRIGGER_DD:.0f}% — 룰1 대상 구간 아님{done_note}. "
                               "평시 국내 매수는 매수존·룰3·룰6 판단"})
        elif krw_cash < KR_MIN_CYCLE_KRW:
            out.update({"status": "no_funds", "allowed_krw": 0,
                        "why": f"낙폭 {dd_pct:+.1f}% ≤ {KR_TRIGGER_DD:.0f}%이나 원화 {krw_cash:,.0f}원 < "
                               f"{KR_MIN_CYCLE_KRW:,}원 — 사이클을 열 재원이 없다{done_note}"})
        else:
            per = krw_cash / KR_TRANCHES
            out["per_tranche_krw"] = round(per)
            out["schedule"] = us_schedule(today, KR_TRANCHES)
            out["pending"] = [1]
            _gate(per, "armed",
                  f"낙폭 {dd_pct:+.1f}% ≤ {KR_TRIGGER_DD:.0f}% · 사이클 미개시 — **1회차 {per:,.0f}원** "
                  f"(원화 {krw_cash:,.0f} ÷ {KR_TRANCHES}) · 집행을 기록하면 사이클이 열린다(--kr-execute)")
        return out

    n, sched = cur.get("n", KR_TRANCHES), cur.get("schedule") or []
    fills = cur.get("fills") or []
    done = _kr_done(cur)
    due = [i for i, d in enumerate(sched, 1) if d <= today]
    now_k = max(due) if due else None
    # ★[10/1 검토 반영] **밀린 회차를 몰아서 사지 않는다.** 한 달에 한 회차(현재 회차)만 열리고, 건너뛴 회차의 몫은
    #   남은 회차에 퍼진다(그날 원화 ÷ 남은 일정 수). 초안은 per × 밀린 회차 수라 룰6·하드플로어가 몇 달 막은 뒤
    #   풀리는 날 원화 전액이 한 번에 열렸다 — '6개월 균등 분할'의 정반대다.
    pending = [now_k] if now_k and now_k not in done else []
    skipped = [i for i in due if i != now_k and i not in done]
    slots = (n - now_k + (1 if pending else 0)) if now_k else n      # 남은 일정 수(현재 회차 미집행이면 포함)
    per = krw_cash / slots if slots > 0 else 0.0
    nxt = next((d for d in sched if d > today), None)
    out.update({"cycle_start": cur.get("start"), "schedule": sched, "n": n, "done": done, "due": due,
                "pending": pending, "skipped": skipped, "per_tranche_krw": round(per), "next_date": nxt,
                "fills": fills, "spent_krw": round(sum(float(f.get("krw") or 0) for f in fills))})
    if not pending:
        out.update({"status": "waiting", "allowed_krw": 0,
                    "why": f"다음 회차 {nxt} (회차당 약 {per:,.0f}원 — 그날 원화로 다시 계산). "
                           "낙폭이 -20% 위로 회복해도 사이클은 끝까지 간다(검정한 규칙 그대로)"})
        return out
    allowed = per
    skip_note = f" · 건너뛴 회차 {skipped}의 몫은 남은 회차에 퍼졌다" if skipped else ""
    return _gate(allowed, "due",
                 f"{now_k}회차 도래 — {allowed:,.0f}원 (원화 {krw_cash:,.0f} ÷ 남은 {slots}회){skip_note}")


def rule1(cash: float, dd_pct: float, storm_pct=None, fear_pct=None, capit_pct=None,
          check_contagion: bool = True, use_ledger: bool = True, kr_weight=None, today: str | None = None):
    """★[2026-10-01 d223] **현행 룰1 = 국내 트랙 원화 6개월 균등 분할**(`kr_track`).

    舊 사다리 판정은 `rule1_ladder()`(재현 전용). 이 함수는 소비처(triggers·build_app_data·rule_tracker·order_check)가
    읽던 키를 그대로 채워 돌려준다 — 뜻이 바뀐 키는 아래와 같다:
      unlocked_ratio = 사이클에서 **도래한 회차 비율**(舊: 낙폭 해금 비율) · steps = **회차 목록**(舊: D0~D4)
      cap_krw = 기집행 + 오늘 몫 · base_krw = 원화 + 기집행 · ladder_allowed_krw = 하드플로어·룰6 **게이트 전** 금액
      storm_pct·fear_pct·capit_pct는 받기만 한다(폭풍 분할·항복 가산은 사다리와 함께 폐기 — 회차가 이미 분할이다).
    """
    k = kr_track(cash, dd_pct, today=today, check_floor=check_contagion, kr_weight=kr_weight, use_ledger=use_ledger)
    n = k.get("n", KR_TRANCHES)
    sched, done, due = k.get("schedule") or [], k.get("done") or [], k.get("due") or []
    pending = k.get("pending") or []
    by_tr: dict = {}
    for f in k.get("fills") or []:
        by_tr.setdefault(f.get("tranche"), []).append(f)
    steps = []
    for i in range(1, n + 1):
        fs = by_tr.get(i) or []
        steps.append({
            "label": f"{i}회", "date": sched[i - 1] if i - 1 < len(sched) else None,
            "threshold": None, "alloc": 1.0 / n,
            "unlocked": i in due or i in pending,
            "executed": bool(fs), "executed_on": fs[-1].get("date") if fs else None,
            "executed_krw": sum(float(f.get("krw") or 0) for f in fs) if fs else None,
            "executed_n": len(fs) or None,
            "why": ", ".join(f"{f.get('ticker')} {float(f.get('krw') or 0):,.0f}원" for f in fs) if fs else "",
        })
    spent = float(k.get("spent_krw") or 0)
    unlocked = len({*due, *pending}) / n
    return {
        "mode": "dca6", "kr_track": k, "status": k.get("status"), "why": k.get("why"),
        "dd_pct": dd_pct, "cash": cash,
        "unlocked_ratio": unlocked, "steps": steps,
        "spent_ratio": (spent / (cash + spent)) if (cash + spent) else 0.0, "available_ratio": unlocked,
        "spent_krw": round(spent), "cap_krw": round(spent + (k.get("pre_gate_krw") or 0)),
        "base_krw": round(cash + spent),
        "spent_unlocked_krw": round(spent), "allowed_bucket_krw": int(k.get("allowed_krw") or 0),
        "executed_steps": done,
        "storm_splits": 1, "storm_why": "폭풍 분할 폐지(d223) — 회차 자체가 6개월 분할이다",
        "storm_mult": 1.0, "capitulation": False, "capitulation_why": "항복 가산 폐지(d223)",
        "final_mult": 1.0,
        "halted": bool(k.get("halted")), "halt_why": k.get("halt_why"),
        "allowed_krw": int(k.get("allowed_krw") or 0),
        "ladder_allowed_krw": int(k.get("pre_gate_krw") or 0),
        "kr_weight_pct": k.get("kr_weight_pct"),
        "rule6_block": bool(k.get("rule6_block")), "rule6_why": k.get("rule6_why"),
        "reserve_ratio": 0.0,
    }


# ─────────────────────────────────────────── d211 현대차 3Q 판정기 (10/21 d253 승인 A~E)
#
# 10/29(유력) 14:00 DART 「연결재무제표기준영업(잠정)실적」 원문 두 숫자만 넣으면 판정·지정가가 나온다.
#   A 판정 = 연결 영업이익 ÷ 매출을 **반올림 없이** 0.054306과 비교(파업 일회성·환입·환율 조정 없음 · 동률 밴드 없음
#     · 공시의 '전년동기' 칸이 재작성돼 있어도 기준선은 3Q25 최초 공시 5.4306% 고정)
#   B 미달 = 1주 지정가 max(341,500, 그날 저장된 12M 밴드 하단의 호가 올림, 직전 지정가) — 4Q26 실적일까지 매 거래일 재등록,
#     하단이 내려가도 안 내리고 올라가면 따라 올린다(d210 ②) · 미체결이면 4Q 실적으로 다시 판정
#   C 통과 = o-kr-band-trim-plan-0903(코스피 7,747 '①현대차 1주') 순서 재결정 안건 · 다음 기한부 기준 4Q26 영업마진 ≥ 5.43%
#   D 미달 + 이벤트형 훼손 = 룰2 딥다이브·밴드 재산정 먼저, 결론까지 지정가 유지·시장가 금지
#   E 판정 전 현대차 12M 밴드 재저장 동결(target_reset --save가 tasks.json freeze_band_save 오더를 보고 건너뛴다)
# ⚠️ 판정기이지 주문기가 아니다 — 주문은 정훈이 토스에서.
D211_TICKER = "005380.KS"
D211_BASELINE = "0.054306"
D211_FLOOR_KRW = 341_500


def kr_tick_up(x: float) -> int:
    """국내 호가단위로 올림(밴드 하단 341,279 → 341,500)."""
    from validate_report import _kr_tick
    t = _kr_tick(x)
    return int(-(-float(x) // t) * t)


def band_low_krw(tk: str = D211_TICKER) -> float | None:
    """stocks.json에 **저장된** 12M 밴드 하단('341,279원~523,000원 (중심 …)'의 앞 숫자)."""
    import re
    try:
        with open(os.path.join(ROOT, "data", "app", "stocks.json"), encoding="utf-8") as f:
            tgt = str(((json.load(f) or {}).get("stocks") or {}).get(tk, {}).get("target") or "")
    except Exception:
        return None
    m = re.search(r"([\d,]+)\s*원\s*~", tgt)
    return float(m.group(1).replace(",", "")) if m else None


def d211_hmc(op, rev, band_low: float | None = None, prev_limit: float | None = None) -> dict:
    """현대차 d211 판정. op·rev는 같은 단위면 무엇이든(원·억원). 문자열 콤마 허용. Decimal로 정확히 비교한다."""
    from decimal import Decimal, getcontext
    getcontext().prec = 40
    o, r = (Decimal(str(x).replace(",", "").strip()) for x in (op, rev))
    if r <= 0:
        raise ValueError("매출이 0 이하 — 숫자를 다시 확인")
    ratio = o / r
    passed = ratio >= Decimal(D211_BASELINE)
    out = {"ratio": f"{ratio:.10f}", "ratio_pct": f"{ratio * 100:.6f}%", "baseline": D211_BASELINE,
           "passed": bool(passed), "gap_bp": f"{(ratio - Decimal(D211_BASELINE)) * 10000:+.2f}"}
    if passed:
        out["verdict"] = "통과 — 장기 보유(d211) · 주문 없음"
        out["next"] = ["C①: o-kr-band-trim-plan-0903 순서(①현대차 1주)를 다시 정하는 안건 — 장기 보유와 충돌(정훈 결정)",
                       "C②: 다음 기한부 기준 = 4Q26 연결 영업마진 ≥ 5.43%(절대선)",
                       "o-hmc-d211-1029 종결 · freeze_band_save 해제(E 종료)"]
        return out
    bl = band_low if band_low is not None else band_low_krw(D211_TICKER)
    cands = {"floor": D211_FLOOR_KRW}
    if bl:
        cands["band_low_tick_up"] = kr_tick_up(bl)
    if prev_limit:
        cands["prev_limit"] = int(prev_limit)
    lim = max(cands.values())
    out.update({"verdict": "미달 — 반등 지정가 정리(d211·B)", "limit_krw": lim, "limit_parts": cands,
                "band_low": bl})
    out["next"] = [f"B: 1주 지정가 {lim:,}원 즉시 제출 = max(341,500 · 밴드 하단 호가 올림 · 직전 지정가) — "
                   "4Q26 실적일(2027-01 하순)까지 매 거래일 재등록(register_policy=always) · 하단이 내려가도 안 내린다",
                   "15:30 소멸 시 16:00~20:00 애프터 재주문(지정가 · ±30%) → 다음 날부터 프리·정규장",
                   "D: 가이던스 철회 같은 이벤트형 훼손이 같이 나오면 룰2 딥다이브·밴드 재산정 먼저 — 결론까지 지정가 유지·시장가 금지",
                   "freeze_band_save 해제(E 종료) — 이후 밴드가 오르면 target_reset --save가 지정가를 따라 올린다(band_floor)",
                   "미체결이면 4Q26 실적으로 다시 판정"]
    return out


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
        detail.append(f"✅ 순부채 2년 연속 증가 (순현금 {nc[2]/1e8:,.0f}→{nc[1]/1e8:,.0f}→{nc[0]/1e8:,.0f}억)")
    else:
        conds.append(False)
        detail.append(f"❌ 순부채 연속 증가 아님 (순현금 {'→'.join(f'{x/1e8:,.0f}' for x in reversed(nc))}억)" if nc
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


# ★[8/14 신설·정훈 승인] 국내 이월 적립 — 사다리가 국내에서 작동하지 않던 결함의 교정.
#   토스는 국내 소수점 미지원 → 해금액 < 1주 가격이면 그 단계는 국내에서 집행 방법이 없다.
#   8/14 실측: D1~D4 전부 합산 226,151원 < NAVER 227,500원(1,349원 부족).
#   ⇒ 소멸시키지 않고 **대기(적립)**로 유지하고, 1주 가격 도달 시 그 단계가 열려 있으면 집행.
#   ⚠️ 자동 집행 아님 — 도달 여부만 표시한다. 정본 = crash_tf §2b.
# 국내 매수후보 티커 — 1주 가격은 **실시간 조회**가 1차, 아래 스냅샷은 폴백이다.
KR_CANDIDATE_TICKERS = {
    "NAVER": "035420.KS", "삼성전자": "005930.KS",
    "KT&G": "033780.KS", "두산에너빌리티": "034020.KS",
}

# ★[2026-08-29 결함 수정 — 하드코딩 가격이 stale이라 판정이 뒤집혔다]
#   舊 주석은 *"보고서 갱신 시 함께 갱신"*이었으나 실제로는 갱신되지 않았고,
#   8/29 실측에서 **4개 중 3개가 틀렸다**:
#     NAVER 227,500 → 실제 220,500 (-7,000) · 삼성전자 274,000 → 257,000 (-17,000)
#     두산에너빌리티 81,800 → 88,200 (+6,400) · KT&G 176,300 → 일치
#   이 오차가 판정을 실제로 뒤집었다: 항복 가산(×1.2) 발동 시 상한 226,585원인데
#   舊 값(227,500)으로는 **915원 부족 = 불가**, 실제가(220,500)로는 **6,085원 여유 = 가능**.
#   "1주를 살 수 있나"는 이진 판정이라 몇 천 원 오차가 결론을 바꾼다.
#   ⇒ market_data 실시간 조회를 1차로 두고, 실패 시에만 아래 스냅샷으로 폴백한다.
#   (CLAUDE.md 8/12 교훈 — 문서의 값은 마지막 확인일의 사실일 뿐이다.)
KR_CANDIDATES = {           # 폴백 스냅샷 — 최종 실측 2026-08-29
    "NAVER": 220500, "삼성전자": 257000, "KT&G": 176300, "두산에너빌리티": 88200,
}


def kr_candidate_prices():
    """국내 매수후보 1주 가격 {이름: 원} + 출처 라벨.

    실시간 조회가 1차(위 주석 참조). 종목별로 개별 폴백하므로 일부만 실패해도
    나머지는 실가격을 쓴다. 폴백이 섞이면 라벨에 명시한다 — 어느 값이 스냅샷인지
    보이지 않으면 8/29 이전과 같은 침묵형 stale이 된다.
    """
    prices = dict(KR_CANDIDATES)
    stale = sorted(prices)
    try:
        import market_data as _md
        for name, tk in KR_CANDIDATE_TICKERS.items():
            try:
                q = _md.fetch_quote(tk) or {}
                px = q.get("price")
                if px and float(px) > 0:
                    prices[name] = int(round(float(px)))
                    stale.remove(name)
            except Exception:
                pass
    except Exception:
        pass
    if not stale:
        src = "실시간"
    elif len(stale) == len(prices):
        src = "폴백 스냅샷(2026-08-29) — 실시간 조회 실패"
    else:
        src = f"실시간 + 폴백({', '.join(stale)})"
    return prices, src


def _kr_accrual_note(allowed_krw, cash):
    """해금 상한이 국내 1주에 얼마나 모자란지 / 어디까지 닿는지."""
    prices, src = kr_candidate_prices()
    reach = {k: v for k, v in prices.items() if allowed_krw >= v}
    lines = [f"\n═══ 🇰🇷 국내 이월 적립 (crash_tf §2b · 8/14 신설) ═══",
             f"  1주 가격 출처: {src}"]
    if allowed_krw <= 0:
        lines.append(f"  현재 허용 **0원** — 회차 미도래·재원 부족·하드플로어·룰6 중 하나(위 판정 참조).")
    if reach:
        lines.append(f"  ✅ 1주 도달: {', '.join(f'{k} {v:,}원' for k, v in sorted(reach.items(), key=lambda x: x[1]))}")
    nearest = min((v for v in prices.values() if v > allowed_krw), default=None)
    if nearest is not None:
        name = next(k for k, v in prices.items() if v == nearest)
        lines.append(f"  ⏳ 최근접 미달: {name} {nearest:,}원 — **{nearest - allowed_krw:,.0f}원 부족**")
    lines.append(f"  참고 가용현금 {cash:,.0f}원 · 국내주 22% 초과 동안 원화는 미국 트랙 합류(d207 ②) — "
                 f"22% 이하일 때만 §2b 규칙3(적립분 미국 매수 금지)")
    lines.append("  ⚠️ 표시 전용 — 회차 몫이 1주에 못 미치면 남은 원화가 다음 회차로 넘어간다(회차 = 그날 원화 ÷ 남은 회차).")
    return "\n".join(lines)


def _provisional_warning(last_date: str):
    """★[2026-08-14 신설] _stale_warning의 **거울 짝** — 캐시가 너무 낡은 게 아니라
    **너무 이른** 경우를 잡는다.

    사고 재발: 8/13에 장중 수집 오염을 발견해 `history_backfill`에 upsert(개정창 7일)를
    넣었는데, 그 다음날인 8/14 14:35에 같은 함정을 그대로 밟았다. backfill을 장중에 돌려
    **그날 장중값(6,920.08)이 종가 자리에 기록**됐고, `tranche_rules`가 그 값으로
    낙폭 -24.1%를 내며 **D1 재잠금**을 보고했다. 마감까지 1시간 남은 시점의 잠정치였다.

    upsert는 **마감 후 재실행하면 고쳐준다**(8/13 수정의 효과) — 그러나 아무도
    *"지금 보고 있는 이 숫자가 잠정치"*라고 말해주지 않는다는 점은 그대로였다.
    D1 경계(-25% = 코스피 6,835.91)처럼 임계 근처에선 장중 몇십 포인트가 판정을 뒤집는다.

    ⇒ 캐시 마지막 봉이 **오늘이고 KRX가 아직 안 닫혔으면** 잠정치라고 명시한다.
      차단하지 않는 이유는 _stale_warning과 같다 — 판단은 사람이 한다.
    """
    try:
        last = dt.date.fromisoformat(last_date[:10])
    except Exception:
        return None
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))   # KST 고정(서버 TZ 무관)
    if last != now.date() or now.weekday() >= 5:
        return None
    if (now.hour, now.minute) >= (15, 30):        # 정규장 마감 후 = 종가 확정
        return None
    return (f"⚠️ 코스피 마지막 봉 **{last.isoformat()}**은 **장중 잠정치**다 "
            f"(현재 KST {now:%H:%M} · 마감 15:30 전).\n     "
            f"아래 낙폭·해금 판정은 확정이 아니다 — 임계 근처면 마감 후 뒤집힌다. "
            f"`history_backfill.py --symbols '^KS11'`를 **마감 후 다시 돌려** 재판정할 것.")


def _load_inputs(cash_arg):
    cash = cash_arg
    if cash is None:
        p = os.path.join(ROOT, ".claude", "skills", "portfolio-desk", "portfolio.json")
        try:
            with open(p, encoding="utf-8") as f:
                pf = json.load(f) or {}
            # ★[8/20 결함 수정] 원화만 읽고 **달러 현금을 빼먹고 있었다.**
            # 사다리 상한 = 가용현금 × 해금%인데 그 '가용현금'이 cash_krw뿐이라,
            # 매도대금이 달러로 들어와 있으면 상한이 그만큼 과소 계산된다.
            # 8/19 AAPL 매도로 $308.94(≈431,000원)가 들어오며 드러났다 —
            # 같은 날 build_app_data의 assets_krw에서 고친 것과 **같은 클래스**다
            # (원화 현금만 쓰던 시절의 가정이 두 군데에 남아 있었다).
            # 미국 소수점 매수는 이 달러로 바로 집행하므로 재원이 맞다.
            cash = float(pf.get("cash_krw") or 0)
            # ★[2026-09-21 d205 트랙 분리 · 정훈 승인 "승인, 적용해줘"] 사다리 = **국내 트랙** → 재원은 **원화만**.
            #   舊(8/20~9/21)는 달러를 원화로 환산해 합쳤다. 그 결과 코스피 통계로 만든 사다리가
            #   달러로 사는 미국주(GOOGL 5건 300,909원 전부)의 속도를 정하고 있었다.
            #   달러는 이제 미국 트랙(us_track)이 다룬다 — 코스피 낙폭과 무관한 3개월 분할.
            #   검정 = us_track_test.py · 정본 = docs/research/us_track_test_2026-09-21.md
            usd = 0.0 if KR_TRACK_KRW_ONLY else float(pf.get("cash_usd") or 0)
            if usd:
                fx = float(pf.get("us_avg_fx_cost") or 0) or 1400.0
                try:
                    import market_data as _md
                    q = _md.fetch_quote("KRW=X") or {}
                    fx = float(q.get("price") or fx)
                except Exception:
                    pass  # 환율 조회 실패 시 us_avg_fx_cost 폴백(장부 평균)
                cash += usd * fx
        except Exception:
            cash = 0.0

    dd = storm = fear = capit = None
    stale = None
    try:
        import drawdown_history as D
        dates, closes = D.load(KOSPI)
        if closes:
            dd = D.current_drawdown(dates, closes)["dd_pct"]
            # 둘은 배타적이다: stale = 마지막 봉 < 오늘 / provisional = 마지막 봉 == 오늘(장중)
            stale = _stale_warning(dates[-1]) or _provisional_warning(dates[-1])
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


def selftest() -> int:
    """미국 트랙 배분·간격·지정가 상한 + d211 판정기 회귀 테스트(네트워크·실원장 없음 — 임시 원장 + 가격 주입).

    10/19 실측 결함 4종을 고정한다: ①2회차 기록 직후 3회차 zone_open(달러가 한 주 안에 바닥) ②zone_open이 존 종목에
    회차 전액('ANET $366.87 전액' — d235 ④와 다름) ③회차일 존 2개 균등 분할(d191 순위 무시) ④밀린 회차 몰아 사기(per × 회차 수).
    """
    import tempfile
    g = globals()
    keep = {k: g[k] for k in ("US_TRACK", "_px", "_last_close", "_us_zone_levels", "googl_room_usd",
                              "global_contagion_check", "_us_session_today", "_kst_today", "_us_cash_now")}
    tmp = tempfile.mkdtemp(prefix="tranche_selftest_")
    ok = True

    def expect(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'✅' if good else '❌'} {label}: {got}" + ("" if good else f"  (기대 {want})"))

    px = {"GEV": 950.0, "ANET": 185.0, "CDNS": 330.0, "GOOGL": 340.0, "VOO": 700.0}
    prev = {"GEV": 940.0, "ANET": 182.95, "CDNS": 325.86}
    room = {"room_usd": 0.0, "weight_pct": 18.1}

    def write(fills, schedule=("2026-09-21", "2026-10-21", "2026-11-23")):
        with open(g["US_TRACK"], "w", encoding="utf-8") as f:
            json.dump({"cycle": {"start": schedule[0], "n": 3, "schedule": list(schedule), "fills": fills}}, f)

    try:
        g["US_TRACK"] = os.path.join(tmp, "us_track.json")
        g["_px"] = lambda s, live=True: (px.get(s), "test") if px.get(s) else (None, None)
        g["_last_close"] = lambda s: (prev.get(s), "2026-10-20") if prev.get(s) else (None, None)
        g["_us_zone_levels"] = lambda: {"GEV": 900.0, "ANET": 190.0, "CDNS": 315.0}
        g["googl_room_usd"] = lambda live=True: dict(room)
        g["global_contagion_check"] = lambda: (False, "test")
        print("tranche_rules 미국 트랙 selftest")

        expect("세션 9/22 01:19 KST → 9/21 세션", us_session_of("2026-09-22T01:19:11+09:00"), ("2026-09-21", "2026-09-22"))
        expect("세션 10/21 22:31 KST → 10/21 세션", us_session_of("2026-10-21T22:31:00+09:00"), ("2026-10-21", "2026-10-21"))
        expect("세션 11/3 06:30 KST(서머타임 끝) → 11/2 세션", us_session_of("2026-11-03T06:30:00+09:00")[0], "2026-11-02")
        expect("월 더하기 말일 클램프 1/31 → 2/28", _plain_add_months(dt.date(2027, 1, 31), 1).isoformat(), "2027-02-28")

        f1 = [{"date": "2026-09-22", "session": "2026-09-21", "tranche": 1, "usd": 222.98, "ticker": "VOO"}]
        write(f1)
        r = us_track(733.74, "2026-10-19", live=False)
        expect("2회차 회차일 전 · 1회차 세션+1개월(10/21) 전 → spacing_wait", (r["status"], r["wait_until"]),
               ("spacing_wait", "2026-10-21"))
        expect("간격 대기 중 상시 예약 = wait", [x["mode"] for x in r["standing"]], ["wait", "wait", "wait"])

        r = us_track(733.74, "2026-10-21", live=False)
        sp = [(x["ticker"], x["usd"], x.get("order")) for x in r["split"]]
        expect("회차일 ANET 존 안 → 1주(예상 체결 $185+0.1%) + 잔액 VOO", (r["status"], sp),
               ("due", [("ANET", 185.18, "limit"), ("VOO", 181.69, "market_fraction")]))
        expect("추격 상한 = min($190, 182.95×1.03) = 188.43 · 예상 체결 = 현재가 185",
               (r["split"][0]["chase_cap"], r["split"][0]["est_fill"]), (188.43, 185.0))
        expect("상시 예약 ANET 추격 상한 = 188.43", [(x["ticker"], x["mode"], x["chase_cap"]) for x in r["standing"]][1],
               ("ANET", "limit", 188.43))

        px["GEV"] = 890.0
        r = us_track(733.74, "2026-10-21", live=False)
        expect("존 2개(GEV·ANET) → 최상위 GEV 하나에 회차 전액 소수점(1주 > 회차)",
               [(x["ticker"], x["usd"], x.get("order")) for x in r["split"]], [("GEV", 366.87, "market_fraction")])
        px["GEV"] = 950.0

        room["room_usd"] = 50.0
        r = us_track(733.74, "2026-10-21", live=False)
        expect("GOOGL 여유 $50(코드 공식) → ANET 1주 · GOOGL $50 · VOO 나머지",
               [(x["ticker"], x["usd"]) for x in r["split"]], [("ANET", 185.18), ("GOOGL", 50.0), ("VOO", 131.69)])
        room["room_usd"] = 0.0

        write([])
        r = us_track(900.0, "2026-10-22", live=False)
        expect("밀린 회차 2개(1·2) → 한 회차만(900÷3=300)", (r["pending"], r["allowed_usd"]), ([1, 2], 300.0))

        f2 = f1 + [{"date": "2026-10-22", "session": "2026-10-21", "tranche": 2, "usd": 188.43, "ticker": "ANET"}]
        write(f2)
        r = us_track(366.87, "2026-10-26", live=False)
        expect("2회차 체결(10/21 세션) 직후 존 안 → 3회차 zone_open 아님(11/21까지 대기)", (r["status"], r["wait_until"]),
               ("spacing_wait", "2026-11-21"))
        r = us_track(366.87, "2026-11-21", live=False)
        expect("11/21(세션+1개월) 존 안 → 3회차 zone_open · ANET 1주 + VOO",
               (r["status"], [(x["ticker"], x.get("order")) for x in r["split"]]),
               ("zone_open", [("ANET", "limit"), ("VOO", "market_fraction")]))

        # ★[10/22 리뷰] 게이트는 KST 날짜가 아니라 **세션일**로 본다 — KST 11/21 00:30은 아직 美 11/20 세션이다
        g["_kst_today"], g["_us_session_today"] = (lambda: "2026-11-21"), (lambda: "2026-11-20")
        r = us_track(366.87, live=False)
        expect("KST 11/21 00:30(美 11/20 세션) → 아직 대기", (r["status"], r["wait_until"]), ("spacing_wait", "2026-11-21"))
        expect("us_buy_block(원장만) = 대기 사유", us_buy_block(), "d251 월 1회차 대기 — 2026-11-21부터")
        expect("us_buy_block(판정) = 같은 사유", us_buy_block(r), "d251 월 1회차 대기 — 2026-11-21부터")
        g["_us_session_today"] = lambda: "2026-11-21"
        expect("美 11/21 세션 → 대기 풀림", (us_track(366.87, live=False)["wait_until"], us_buy_block()), (None, None))
        g["_kst_today"], g["_us_session_today"] = keep["_kst_today"], keep["_us_session_today"]

        f_late = f1 + [{"date": "2026-11-10", "session": "2026-11-09", "tranche": 2, "usd": 300, "ticker": "VOO"}]
        write(f_late)
        r = us_track(366.87, "2026-11-23", live=False)
        expect("2회차가 늦게(11/9) 체결 → 3회차 회차일(11/23)도 12/9까지 대기(정의 문언)", (r["status"], r["wait_until"]),
               ("spacing_wait", "2026-12-09"))
        r = us_track(366.87, "2026-11-12", live=False)
        expect("다음 회차 표시 = 실제로 열 수 있는 첫날(회차일 11/23 → 12/9)", (r["next_date"], r["wait_until"]),
               ("2026-12-09", "2026-12-09"))
        write(f2 + [{"date": "2026-11-24", "session": "2026-11-23", "tranche": 3, "usd": 366.87, "ticker": "VOO"}])
        expect("3회 완료 → us_buy_block = 완료 사유", (us_buy_block() or "").startswith("미국 트랙 사이클 3회 완료"), True)
        with open(g["US_TRACK"], "w", encoding="utf-8") as f:
            json.dump({}, f)
        expect("사이클 없음 → us_buy_block = 없음 사유", us_buy_block(), "미국 트랙 사이클 없음")

        f_nos = [{"date": "2026-09-22", "tranche": 1, "usd": 222.98, "ticker": "VOO"}]
        write(f_nos)
        r = us_track(733.74, "2026-10-21", live=False)
        expect("세션 미기재 → KST 체결일(9/22)+1개월 = 10/22까지 대기(늦게 풀리는 쪽)", (r["status"], r["wait_until"]),
               ("spacing_wait", "2026-10-22"))

        # ★[10/22 리뷰] 세션일 = 동부시각 + 4h — 주간거래(KST 오전)는 그날 거래일, 겨울 애프터마켓은 전날
        expect("주간거래 10/22 10:30 KST(서머타임) → 10/22", us_session_of("2026-10-22T10:30:00+09:00")[0], "2026-10-22")
        expect("주간거래 11/3 10:30 KST(겨울) → 11/3", us_session_of("2026-11-03T10:30:00+09:00")[0], "2026-11-03")
        expect("애프터 11/3 09:30 KST(겨울 · 20:00 ET 전) → 11/2", us_session_of("2026-11-03T09:30:00+09:00")[0], "2026-11-02")
        expect("애프터 10/22 08:30 KST(서머타임 · 19:30 ET) → 10/21", us_session_of("2026-10-22T08:30:00+09:00")[0], "2026-10-21")

        # ★[10/22 리뷰 3차 C5] 첫 밤 — VOO 시장가가 ANET 지정가보다 먼저 체결·기록돼도 같은 밤의 ANET 1주는 막지 않는다(d235 ①)
        rf = {"status": "partial", "partial_tranche": 2, "partial_tickers": ["VOO"], "partial_left": 182.18,
              "partial_first_night": True}
        expect("첫 밤(판정) · VOO 먼저 · ANET $182 → 안 막는다", us_buy_block(rf, "ANET", 182.0), None)
        expect("첫 밤(판정) · 잔액보다 비싼 1주 → 그래도 막는다",
               (us_buy_block(dict(rf, partial_left=60.0), "ANET", 182.0) or "").startswith("1주 $182.00 > 2회차 잔액 $60.00"), True)
        write(f1 + [{"date": "2026-10-22", "session": "2026-10-22", "tranche": 2, "usd": 184.69, "ticker": "VOO",
                     "budget": 366.87}])
        g["_us_session_today"] = lambda: "2026-10-22"
        r = us_track(548.56, "2026-10-22", live=False, session_day="2026-10-22")
        expect("첫 밤(원장) · partial_first_night · ANET 1주 안 막는다(원장·판정 같은 답)",
               (r["partial_first_night"], us_buy_block(None, "ANET", 182.0), us_buy_block(r, "ANET", 182.0)), (True, None, None))
        expect("첫 밤 · 상시 예약은 잔액 한도로 정상 판정(진행 중 'off' 아님)", "off" in [x["mode"] for x in r["standing"]], False)
        expect("첫 밤 · why에 '첫 밤' 안내", "첫 밤(세션 2026-10-22)" in r["why"], True)
        g["_us_session_today"] = lambda: "2026-10-23"
        r = us_track(548.56, "2026-10-23", live=False, session_day="2026-10-23")
        expect("다음 세션 → 첫 밤 끝 · ANET 막는다(원장)",
               (r["partial_first_night"], (us_buy_block(None, "ANET", 182.0) or "").startswith("2회차 진행 중")), (False, True))
        expect("첫 밤 지난 잔액 → why에 d251 재기산·--us-close 안내", "--us-close 2" in r["why"] and "다시 센다" in r["why"], True)
        g["_us_session_today"] = keep["_us_session_today"]

        # ★[10/22 리뷰] 한 회차 = 여러 체결 — ANET 1주를 기록해도 같은 회차 잔액(GOOGL→VOO)은 살아 있고 d251이 막지 않는다
        g["_kst_today"] = lambda: "2026-11-30"
        g["_us_cash_now"] = lambda: 733.74
        write(f1)
        rec = us_execute(185.18, "ANET", filled_at="2026-10-23T01:10:00+09:00", budget=366.87)
        r = us_track(548.56, "2026-10-23", live=False)
        expect("ANET 1주 기록 → 2회차 partial · 잔액 $181.69 · ANET 제외 → VOO",
               (rec["tranche_closed"], r["status"], r["allowed_usd"], [x["ticker"] for x in r["split"]]),
               (False, "partial", 181.69, ["VOO"]))
        expect("partial 중 다음 회차 금액 = (잔고 − 잔액) ÷ 1", r["per_tranche_usd"], 366.87)
        expect("partial 중 상시 예약 ANET = 이미 체결(done)", [x["mode"] for x in r["standing"]][1], "done")
        expect("partial → us_buy_block 안 막는다(원장·판정 둘 다)", (us_buy_block(r), us_buy_block()), (None, None))
        # ★[10/22 리뷰 2차] 종목을 주면 본다 — 이미 산 ANET·다른 존 종목·잔액보다 비싼 1주는 막고, VOO는 안 막는다
        expect("partial · ANET 다시 걸기 → 막는다(원장·판정 같은 답)",
               ((us_buy_block(r, "ANET") or "").startswith("2회차에 ANET 이미 체결"),
                (us_buy_block(None, "ANET") or "").startswith("2회차에 ANET 이미 체결")), (True, True))
        expect("partial · 다른 존 종목(CDNS) → 막는다(존 종목 회차당 1종목)", (us_buy_block(r, "CDNS") or "").startswith("2회차는 존 종목(ANET)"), True)
        expect("partial · VOO·GOOGL(잔액 행선지) → 안 막는다(가격 무관)", (us_buy_block(r, "VOO"), us_buy_block(r, "GOOGL", 250.0)), (None, None))
        # VOO를 먼저 산 회차(ANET 1주는 그 밤에 안 됨) — 다음 날 ANET을 다시 걸라고 하지 않는다(d235 ①)
        rv = {"status": "partial", "partial_tranche": 2, "partial_tickers": ["VOO"], "partial_left": 185.18}
        expect("VOO 먼저 · ANET 1주 → 막는다(첫 밤의 몫 · d235 ①)", (us_buy_block(rv, "ANET", 182.0) or "").startswith("2회차 진행 중"), True)
        expect("VOO 먼저 · 잔액보다 비싼 존 1주 → '못 건다'", (us_buy_block(dict(rv, partial_left=60.0), "ANET", 182.0) or "").startswith("1주 $182.00 > 2회차 잔액 $60.00"), True)
        px["CDNS"] = 310.0
        r = us_track(548.56, "2026-10-23", live=False)
        expect("partial 중 CDNS 존 진입 → 잔액은 그래도 VOO(존 종목 회차당 1종목 · d235 ④)",
               ([(x["ticker"], x["usd"]) for x in r["split"]], [x["mode"] for x in r["standing"]]),
               ([("VOO", 181.69)], ["off", "done", "off"]))
        px["CDNS"] = 330.0
        try:
            us_execute(366.87, "VOO", filled_at="2026-11-24T00:10:00+09:00")
            got = "기록됨"
        except ValueError as e:
            got = "잔액" if "잔액 $181.69" in str(e) else str(e)[:40]
        expect("partial 중 잔액보다 큰 체결(다음 회차 몫) → 거부(진행 중 회차로 잘못 안 들어간다)", got, "잔액")
        rec = us_execute(181.69, "VOO", filled_at="2026-10-23T23:40:00+09:00")
        r = us_track(366.87, "2026-10-26", live=False)
        expect("잔액 체결(--tranche 생략 = 진행 중 2회차) → 닫힘 · 간격 = 마지막 세션 10/23 + 1개월",
               (rec["tranche"], rec["tranche_closed"], r["status"], r["wait_until"]), (2, True, "spacing_wait", "2026-11-23"))
        for kw, want in [(dict(usd=10, ticker="VOO", session="2026/10/23"), "형식"),
                         (dict(usd=10, ticker="VOO"), "체결 시각"),
                         (dict(usd=10, ticker="VOO", session="2026-12-01", date="2026-12-01"), "오늘"),
                         (dict(usd=10, ticker="VOO", tranche=5, session="2026-11-24"), "1~3"),
                         (dict(usd=366.87, ticker="VOO", session="2026-11-02"), "d251"),
                         (dict(usd=10, ticker="VOO", session="2026-11-24"), "--budget"),
                         (dict(usd=366.87, ticker="VOO", session="2026-11-24"), "--close"),
                         (dict(usd=185.18, ticker="ANET", session="2026-11-24", budget=36.69), "자릿수"),
                         (dict(usd=1, ticker="VOO", session="2026-11-24", tranche=2, budget=1, force=True), "--us-set-budget")]:
            try:
                us_execute(**kw)
                got = "기록됨"
            except ValueError as e:
                got = want if want in str(e) else str(e)[:40]
            expect(f"us_execute 거부 {kw}", got, want)
        expect("거부한 기록은 원장을 안 바꾼다", len(_us_read()["cycle"]["fills"]), 3)
        g["_us_cash_now"] = lambda: 366.87
        rec = us_execute(366.87, "VOO", session="2026-11-02", close=True, force=True)
        expect("--force = 위반 체결도 기록(원장에 남는다)", (rec["tranche"], rec["tranche_closed"]), (3, True))

        # ★[10/22 리뷰 2차] 체결 뒤 현금(portfolio.json 동기화 후)으로는 회차 일부가 회차 전부로 읽혔다 → 추정하지 않는다
        write(f1 + [{"date": "2026-10-22", "session": "2026-10-21", "tranche": 2, "usd": 366.87, "ticker": "VOO"}])
        g["_us_cash_now"] = lambda: 181.69          # 3회차 ANET 1주 체결 **뒤** 현금
        try:
            us_execute(185.18, "ANET", filled_at="2026-11-24T00:10:00+09:00")
            got = "기록됨"
        except ValueError as e:
            got = "거부" if "--budget" in str(e) and "--close" in str(e) else str(e)[:40]
        expect("마지막 회차 · 체결 뒤 현금 · budget 생략 → 거부(舊 = 닫혀 사이클 '완료' · 잔액 소실)", got, "거부")
        # 회차 금액 정정 = 체결을 추가하지 않는다
        write(f1)
        us_execute(185.18, "ANET", session="2026-10-22", budget=300)
        r1 = us_set_budget(2, 366.87, "오타 정정")
        expect("us_set_budget → 잔액 재계산 · 체결 행 수 그대로", (r1["left"], r1["closed"], len(_us_read()["cycle"]["fills"])),
               (181.69, False, 2))
        try:
            us_set_budget(2, 100)
            got = "바뀜"
        except ValueError:
            got = "거부"
        expect("us_set_budget < 이미 체결 → 거부", got, "거부")
        for fn, want in [(lambda: us_set_budget(1, 300), "한 번에 기록된 회차"),
                         (lambda: us_set_budget(2, 3668.70), "자릿수"),
                         (lambda: us_execute(0, "VOO", session="2026-10-22"), "≤ 0")]:
            try:
                fn()
                got = "바뀜"
            except ValueError as e:
                got = want if want in str(e) else str(e)[:40]
            expect(f"거부 — {want}", got, want)
        write(f1)
        try:
            us_execute(185.18, "ANET", session="2026-10-22", budget=3668.70)
            got = "기록됨"
        except ValueError as e:
            got = "자릿수" if "자릿수" in str(e) else str(e)[:40]
        expect("첫 체결 budget 자릿수 오타(3668.70 > 잔고+체결) → 거부", got, "자릿수")
        # 잔액 정확히 $1.00 → 닫힘(센트 반올림 — 舊 부동소수로 열린 채)
        write(f1 + [{"date": "2026-10-22", "session": "2026-10-21", "tranche": 2, "usd": 127.02, "ticker": "VOO", "budget": 128.02}])
        expect("budget 128.02 · 체결 127.02(잔액 $1.00) → 닫힘", us_tranches(_us_read()["cycle"])[2]["closed"], True)
        # 잔액 $3.19가 남은 채 뒤 회차일이 지나면 말한다
        write(f1 + [{"date": "2026-10-22", "session": "2026-10-21", "tranche": 2, "usd": 183.68, "ticker": "ANET", "budget": 366.87},
                    {"date": "2026-10-23", "session": "2026-10-22", "tranche": 2, "usd": 180.0, "ticker": "VOO"}])
        r = us_track(369.06, "2026-12-01", live=False)
        expect("잔액 $3.19 partial · 3회차 회차일 지남 → why에 '--us-close 2'", (r["status"], "--us-close 2" in r["why"]), ("partial", True))

        write(f1)
        us_execute(185.18, "ANET", session="2026-10-22", budget=366.87)
        expect("us_close → 잔액은 다음 회차로 · 간격 시작", (us_close(2)["left_usd"], us_track(548.56, "2026-10-26", live=False)["status"]),
               (181.69, "spacing_wait"))
        g["_kst_today"], g["_us_cash_now"] = keep["_kst_today"], keep["_us_cash_now"]

        # 깨진 원장 = '사이클 없음'이 아니다(덮어쓰지 않고 이유를 낸다)
        with open(g["US_TRACK"], "w", encoding="utf-8") as f:
            f.write('{"cycle": {"start": "2026-09-21", <<<<<<< HEAD')
        r = us_track(366.87, "2026-10-26", live=False)
        expect("깨진 원장 → status error · us_buy_block = 원장 오류",
               (r["status"], (us_buy_block() or "")[:10], (us_buy_block(r) or "")[:10]), ("error", "미국 트랙 원장 오", "미국 트랙 원장 오"))
        try:
            us_start("2026-10-26")
            got = "덮어씀"
        except ValueError:
            got = "거부"
        expect("깨진 원장 위에 --us-start 거부", got, "거부")
        write(f1 + [{"date": "2026-10-23", "session": "2026/10/22", "tranche": 2, "usd": 1.0, "ticker": "VOO"}])
        expect("형식 깨진 체결 행 → status error(예외로 죽지 않는다)", us_track(366.87, "2026-10-26", live=False)["status"], "error")
        write(f1 + [{"date": "2026-10-23", "session": "2026-10-22", "tranche": 2, "usd": 185.18, "ticker": "ANET",
                     "budget": "366.87"}])
        expect("문자열 budget → error(진행 중 회차가 '닫힌 회차'로 읽히지 않는다)",
               us_track(366.87, "2026-10-26", live=False)["status"], "error")
        sch = '"schedule": ["2026-09-21", "2026-10-21", "2026-11-23"]'
        for bad in ('{"cycle": ["x"]}', '{"cycle": {"start": "2026-09-21", ' + sch + ', "fills": ["x"]}}',
                    '{"cycle": {"start": "2026-09-21", ' + sch + ', "fills": {"a": 1}}}',
                    '{"cycle": {"start": "2026-09-21", "n": 3, "schedule": ["2026-09-21", "2026-10-21"], "fills": []}}'):
            with open(g["US_TRACK"], "w", encoding="utf-8") as f:
                f.write(bad)
            expect(f"모양이 틀린 원장 {bad[:34]}… → error · us_buy_block 보류",
                   (us_track(366.87, "2026-10-26", live=False)["status"], (us_buy_block() or "")[:10]),
                   ("error", "미국 트랙 원장 오"))
        write(f_late)
        r = us_track(366.87, "2026-11-25", live=False)
        expect("회차일(11/23)이 지난 대기 → 다음 회차 표시 = 12/9(빈칸 아님)", (r["status"], r["next_date"]), ("spacing_wait", "2026-12-09"))
        expect("하드플로어면 대기 회차가 없어도 막는다", us_buy_block({"status": "waiting", "halted": True})[:5], "하드플로어")
        g["global_contagion_check"] = lambda: (None, "S&P 폭풍 조회 실패(X) — 확산 판정 불가")
        write(f1)
        r = us_track(733.74, "2026-10-21", live=False)
        expect("하드플로어 판정 불가 → 연기 아님(현행 룰) · why에 '판정 불가' 표시",
               (r["status"], r["floor_unknown"], "하드플로어 판정 불가" in r["why"]), ("due", True, True))
        g["global_contagion_check"] = lambda: (False, "test")

        _LIVE[("prev", "ANET")] = (182.73, "2026-10-20")
        expect("전일 종가 — 실시간 일봉(끝난 세션만) 마지막 봉이 캐시보다 우선(캐시 하루 늦음 대응)",
               _prev_regular_close("ANET", True), (182.73, "2026-10-20"))
        expect("지정가 상한 = floor(182.73×1.03) = 188.21", _chase_limit("ANET", 190.0, True)["limit"], 188.21)
        expect("부동소수 내림 방지 — 100×1.03 = 103.00", (_LIVE.__setitem__(("prev", "X"), (100.0, "d")),
                                                         _chase_limit("X", 190.0, True)["limit"])[1], 103.0)
        _LIVE[("prev", "ANET")] = (None, None)
        expect("실시간 실패 → 캐시", _prev_regular_close("ANET", True), (182.95, "2026-10-20"))
        _LIVE.pop(("prev", "ANET"), None)
        _LIVE.pop(("prev", "X"), None)

        print("d211 현대차 판정기")
        expect("호가 올림 341,279 → 341,500", kr_tick_up(341279), 341500)
        expect("호가 올림 199,990 → 200,000", kr_tick_up(199990), 200000)
        expect("정확히 0.054306 = 통과(이상)", d211_hmc("54306", "1000000")["passed"], True)
        expect("0.0543059999 = 미달(반올림 없음)", d211_hmc("54305.9999", "1000000")["passed"], False)
        r = d211_hmc("2,376,000", "44,300,000", band_low=341279)
        expect("하우스 중앙(2.376조/44.3조) → 미달 · 지정가 341,500", (r["passed"], r["limit_krw"]), (False, 341500))
        expect("밴드 하단 344,200 → 344,500", d211_hmc("1", "100", band_low=344200)["limit_krw"], 344500)
        expect("밴드가 내려가도(330,000) 직전 지정가 344,500 유지",
               d211_hmc("1", "100", band_low=330000, prev_limit=344500)["limit_krw"], 344500)
    finally:
        g.update(keep)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS" if ok else "FAIL — 미국 트랙 배분·간격 또는 d211 판정이 회귀했다")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="개정 리스크룰 1·2 판정 (측정·제안 전용)")
    ap.add_argument("--cash", type=float)
    ap.add_argument("--dd", type=float, help="코스피 낙폭%% 수동 지정(음수)")
    ap.add_argument("--storm", type=float, help="코스피 폭풍%%ile 수동 지정")
    ap.add_argument("--fear", type=float)
    ap.add_argument("--capitulation", type=float)
    ap.add_argument("--execute", type=int, metavar="STEP",
                    help="[폐기 10/1 d223] 舊 사다리 단계 집행 기록 — 이제 거부한다. --kr-execute 를 쓸 것")
    ap.add_argument("--amount", type=float, help="[폐기] 舊 --execute 금액")
    ap.add_argument("--note", default="", help="집행 메모(종목·체결가 등)")
    # ★[10/1 d223] 국내 트랙 = 원화 6개월 균등 분할
    ap.add_argument("--kr-start", nargs="?", const="", metavar="YYYY-MM-DD",
                    help="국내 트랙 새 사이클 시작(날짜 생략 = 오늘). 낙폭 > -20%%면 거부(--force 제외)")
    ap.add_argument("--kr-execute", action="store_true",
                    help="국내 트랙 회차 집행 기록(--krw·--ticker 필수). 열린 사이클이 없으면 체결일로 연다. 주문 안 냄")
    ap.add_argument("--krw", type=float, help="--kr-execute 금액(원)")
    ap.add_argument("--force", action="store_true", help="--kr-start/--kr-execute 낙폭 문턱 무시 · --us-execute 정정 기록(닫힌 회차·건너뛰기·d251 위반 체결) — 정훈 지시가 있을 때만")
    # ★[2026-09-20] 체결일 지정 — 없으면 오늘로 박힌다. 9/17 체결을 9/20 세션에서 기입하니
    #   원장 날짜가 사흘 밀렸다(cap_delta_explain의 prev_date·감사 추적이 어긋난다).
    #   ledger_execute()는 처음부터 date 인자를 받고 있었는데 CLI만 안 뚫려 있었다.
    ap.add_argument("--date", help="--execute 체결일(YYYY-MM-DD). 생략 시 오늘")
    # ★[9/21 d205] 미국 트랙
    ap.add_argument("--us-start", nargs="?", const="", metavar="YYYY-MM-DD",
                    help="미국 트랙 새 사이클 시작(날짜 생략 = 오늘). 진행 중 사이클이 있으면 거부")
    ap.add_argument("--us-execute", action="store_true", help="미국 트랙 회차 집행 기록(--usd·--ticker 필수). 주문 안 냄")
    ap.add_argument("--usd", type=float, help="--us-execute 금액($)")
    ap.add_argument("--tranche", type=int, help="--us-execute 회차 번호(생략 = 진행 중 회차, 없으면 다음 회차)")
    # ★[10/22] 한 회차를 여러 체결로 채운다 — 첫 체결에 회차 금액, 끝낼 때 --close(또는 체결 합이 회차 금액에 닿으면 자동)
    ap.add_argument("--budget", type=float, help="--us-execute 새 회차 첫 체결에 그 회차 금액($ · 오더북의 회차 금액 — 나눠 살 때 필수) · --us-set-budget 새 금액")
    ap.add_argument("--close", action="store_true", help="--us-execute 이 체결로 회차를 닫는다(회차 전부를 한 번에 샀을 때 · 잔액은 다음 회차로)")
    ap.add_argument("--us-set-budget", type=int, metavar="TRANCHE", help="회차 금액 정정(--budget 필수 · 체결을 추가하지 않는다)")
    ap.add_argument("--us-close", type=int, metavar="TRANCHE", help="진행 중 회차를 체결 없이 닫는다(잔액 → 다음 회차)")
    # ★[10/21 d251] '월 1회차' 간격은 체결 세션(美 현지일)에서 계산된다 — 토스 filledAt을 그대로 넘기면 된다
    ap.add_argument("--filled-at", help="--us-execute 토스 체결 시각(filledAt ISO, 예: 2026-10-22T01:19:23+09:00) → 세션·체결일 자동 "
                    "(이것 또는 --date/--us-session 필수)")
    ap.add_argument("--us-session", help="--us-execute 美 거래일(YYYY-MM-DD) 직접 지정 — filledAt이 없을 때")
    ap.add_argument("--d211", nargs=2, metavar=("OP", "REV"),
                    help="현대차 3Q 판정(d211·d253 A~E) — DART 잠정실적 연결 영업이익·매출(같은 단위, 콤마 허용)")
    ap.add_argument("--prev-limit", type=float, help="--d211 직전 등록 지정가(내리지 않는다)")
    ap.add_argument("--selftest", action="store_true", help="미국 트랙 배분·간격·지정가 상한 + d211 판정기 회귀 테스트")
    ap.add_argument("--kr-weight", type=float, help="국내주 비중%% 수동 지정(d207 룰6 게이트 확인용). 생략 = 최신 스냅샷")
    ap.add_argument("--rule2", action="store_true")
    ap.add_argument("--ticker", "--tickers", default="066570.KS")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest())
    if a.d211:
        r = d211_hmc(a.d211[0], a.d211[1], prev_limit=a.prev_limit)
        if a.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
            return
        print(f"\n🚗 현대차 d211 판정 — 연결 영업이익 ÷ 매출 = {r['ratio']} ({r['ratio_pct']}) vs 기준 {r['baseline']} "
              f"(차이 {r['gap_bp']}bp · 반올림 없음 · 조정 없음)")
        print(f"   → **{r['verdict']}**" + (f" · 지정가 **{r['limit_krw']:,}원** {r['limit_parts']}" if not r["passed"] else ""))
        for x in r["next"]:
            print(f"   · {x}")
        print("   ※ 판정기이지 주문기가 아니다 — 주문은 정훈이 토스에서.\n")
        return

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

    if a.us_start is not None:
        c = us_start(a.us_start or None, us_track(check_floor=False).get("usd_cash"), a.note)
        print(f"\n🇺🇸 미국 트랙 사이클 시작 — {c['start']} · 회차 {', '.join(c['schedule'])} · 시작 잔고 ${c['pool_usd_at_start']:,.2f}\n")
        return
    if a.us_set_budget is not None:
        if a.budget is None:
            sys.exit("[tranche_rules] --us-set-budget 에는 --budget(새 회차 금액)이 필요하다")
        try:
            r = us_set_budget(a.us_set_budget, a.budget, a.note, a.force)
        except ValueError as e:
            sys.exit(f"[tranche_rules] --us-set-budget 거부(원장 안 바뀜): {e}")
        print(f"\n📒 미국 트랙 {r['tranche']}회차 금액 정정 ${r['old']} → ${r['budget']:,.2f} — 체결 ${r['spent']:,.2f} · "
              + ("닫힘" if r["closed"] else f"잔액 ${r['left']:,.2f}") + "\n")
        return
    if a.us_close is not None:
        try:
            r = us_close(a.us_close, a.note)
        except ValueError as e:
            sys.exit(f"[tranche_rules] --us-close 거부: {e}")
        print(f"\n📒 미국 트랙 {r['tranche']}회차 닫음 — 잔액 ${r['left_usd']:,.2f}는 다음 회차로(간격 = 마지막 체결 세션 기준)\n")
        return
    if a.us_execute:
        if a.usd is None or not a.ticker or a.ticker == "066570.KS":
            sys.exit("[tranche_rules] --us-execute 에는 --usd 와 --ticker(미국 종목)가 필요하다")
        try:
            rec = us_execute(a.usd, a.ticker, a.tranche, a.note, a.date, a.us_session, a.filled_at,
                             a.budget, a.close, a.force)
        except ValueError as e:
            sys.exit(f"[tranche_rules] --us-execute 거부(원장 안 바뀜): {e}")
        state = ("닫힘 — 다음 회차는 이 회차 마지막 체결 세션 + 1개월부터(d251)" if rec["tranche_closed"]
                 else f"진행 중 — 잔액 ${rec['tranche_left']:,.2f}(같은 회차 · 간격 대상 아님)")
        print(f"\n📒 미국 트랙 {rec['tranche']}회차 기록 — {rec['date']} · 세션 {rec.get('session') or '미기재(KST 체결일로 간격 계산)'} · "
              f"{rec['ticker']} ${rec['usd']:,.2f} {('· ' + rec['note']) if rec['note'] else ''}\n"
              f"   회차 체결 합 ${rec['tranche_spent']:,.2f} · {state}\n")
        return

    if a.kr_start is not None or a.kr_execute:
        _cash, _dd = _load_inputs(a.cash)[:2]
        _dd = a.dd if a.dd is not None else _dd
        try:
            if a.kr_execute:
                if a.krw is None or not a.ticker or a.ticker == "066570.KS" and "--ticker" not in " ".join(sys.argv):
                    sys.exit("[tranche_rules] --kr-execute 에는 --krw 와 --ticker(국내 종목)가 필요하다")
                rec = kr_execute(a.krw, a.ticker, a.tranche, a.note, a.date, _dd, a.force)
                print(f"\n📒 국내 트랙 {rec['tranche']}회차 기록 — {rec['date']} · {rec['ticker']} {rec['krw']:,}원 "
                      f"{('· ' + rec['note']) if rec['note'] else ''}\n")
            else:
                c = kr_start(a.kr_start or None, _cash, _dd, a.note, a.force)
                print(f"\n🇰🇷 국내 트랙 사이클 시작 — {c['start']} · 회차 {', '.join(c['schedule'])} · "
                      f"시작 원화 {(_cash or 0):,.0f}원 · 낙폭 "
                      + (f"{_dd:+.1f}%" if _dd is not None else "미확인(--force)") + "\n")
        except (ValueError, KrLedgerError) as e:
            sys.exit(f"[tranche_rules] {e}")
        return

    if a.execute:
        sys.exit("[tranche_rules] 낙폭 사다리는 2026-10-01 d223로 폐기됐다 — 단계 집행 기록(--execute)은 받지 않는다. "
                 "국내 트랙 회차 기록은 `--kr-execute --krw N --ticker 종목`.")

    cash, dd, storm, fear, capit, stale = _load_inputs(a.cash)
    dd = a.dd if a.dd is not None else dd
    storm = a.storm if a.storm is not None else storm
    fear = a.fear if a.fear is not None else fear
    capit = a.capitulation if a.capitulation is not None else capit

    if dd is None:
        sys.exit("[tranche_rules] 코스피 낙폭 산출 실패 — history_backfill.py 필요 또는 --dd 지정")

    kw = a.kr_weight if a.kr_weight is not None else kr_weight_pct()
    r = rule1(cash, dd, storm, fear, capit, kr_weight=kw)
    if a.json:
        print(json.dumps({"rule1": r, "us_track": us_track(), "rule2": rule2(a.ticker)}, ensure_ascii=False, indent=1))
        return

    k = r["kr_track"]
    print("\n═══ 룰1 🇰🇷 국내 트랙 — 원화 6개월 균등 분할 (d223 · 낙폭 ≤-20%에서 개시 · 재원 = 원화) ═══")
    if stale and a.dd is None:
        print(f"  {stale}\n")
    print(f"  코스피 고점대비 **{dd:+.1f}%** (개시 문턱 {KR_TRIGGER_DD:.0f}%) · 원화 현금 {cash:,.0f}원 (달러는 아래 미국 트랙)")
    if k.get("schedule") and k.get("status") != "armed":
        marks = []
        for i, d_ in enumerate(k["schedule"], 1):
            m = "✅" if i in k["done"] else ("🟢" if i in k["pending"] else "⏳")
            marks.append(f"{i}회 {d_} {m}")
        print(f"  사이클 {k.get('cycle_start')} · " + " · ".join(marks) + f" · 기집행 {k['spent_krw']:,}원")
    print(f"  {k['halt_why']}")
    print(f"  {k['rule6_why']}")
    icon = {"due": "💰", "armed": "💰", "waiting": "⏳", "idle": "➖", "no_funds": "⛔",
            "rule6_block": "⛔", "deferred": "🔴", "unknown": "⚠️"}.get(k.get("status"), "•")
    print(f"\n  {icon} [{k.get('status')}] **오늘 허용 {r['allowed_krw']:,}원** — {k['why']}")
    if r["allowed_krw"] > 0:
        print("     ※ 상한이지 목표가 아니다. 룰3(추격 금지) 그대로. 집행은 PM 판단·정훈 결정. 자동 집행 아님.")
    print("  ※ 舊 낙폭 사다리(D0~D4·예비·RESET·항복 가산)는 10/1 d223로 폐기 — 같은 원화의 6개월 분할에 ①②③ 전패.")

    print(_kr_accrual_note(r["allowed_krw"], cash))

    u = us_track()
    print("\n═══ 룰1 🇺🇸 미국 트랙 — 달러 3회 균등 분할 (d205 · 코스피 낙폭과 무관 · d235 매수존 상시 감시) ═══")
    print(f"  달러 잔고 ${u['usd_cash']:,.2f}")
    if u.get("schedule"):
        marks = []
        for i, d in enumerate(u["schedule"], 1):
            m = ("✅" if i in u["done"] else
                 f"🟡 잔액 ${u['partial_left']:,.2f}" if i == u.get("partial_tranche") else
                 ("🟢" if i in u["pending"] else "⏳"))
            marks.append(f"{i}회 {d} {m}")
        print(f"  사이클 {u['cycle_start']} · " + " · ".join(marks) + f" · 기집행 ${u['spent_usd']:,.2f}")
    if u.get("halt_why"):
        print(f"  {u['halt_why']}")
    print(f"  → **{u['why']}**")
    for x in u.get("split") or []:
        print(f"     · {x['ticker']:<6} ${x['usd']:>8,.2f}  {x['why']}")
    if u.get("standing"):
        lim = u["partial_left"] if u.get("partial_tranche") else u["per_tranche_usd"]
        print(f"  ── 상시 매수존 감시(d235) · {u['standing_tranche']}회차 한도 ${lim:,.2f} ──")
        icon = {"limit": "📌예약", "alert": "🔔알림", "off": "⛔중지", "wait": "⏳대기", "done": "✅체결"}
        for x in u["standing"]:
            gap = f"{x['gap_pct']:+.1f}%" if x.get("gap_pct") is not None else "?"
            print(f"     · {icon.get(x['mode'], x['mode'])} {x['ticker']:<5} 존 ${x['level']:,.0f} · 현재 ${x.get('price')} (존까지 {gap})  {x['why']}")
        print("     ※ 예약은 한 번에 한 종목 · 체결되면 그 회차 끝(회차일 재집행 없음) · 회차 금액에서 남는 달러는 같은 날 GOOGL 18% → VOO 소수점으로 채운다 · 장전 -5% 이상 갭이면 취소(룰3) · 주문은 정훈이 토스 앱에서.")
    if u.get("status") in ("due", "zone_open", "partial"):
        print("     ※ 룰3(추격금지) — 대상이 당일 +3% 이상 급등이면 다음 거래일로. 분수주 = 시장가. 자동 집행 아님.")

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
