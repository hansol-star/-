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
#   대상 순서: 매수존 안의 우선순위(GEV·ANET) → 없으면 GOOGL(주식 비중 18% 상한까지) → 나머지 VOO.
US_TRACK = os.path.join(ROOT, "data", "app", "us_track.json")
US_TRANCHES = 3
US_MIN_CYCLE_USD = 50.0      # 이보다 적은 달러로는 새 사이클을 열지 않는다(소수점 체결 실익)
US_GOOGL_CAP = 0.18          # d191 — 주식 평가액 기준
US_ZONE_TICKERS = ("GEV", "ANET")   # d191 ②③ — 매수존은 portfolio.json alerts(below)가 정본
_PF_JSON = os.path.join(ROOT, ".claude", "skills", "portfolio-desk", "portfolio.json")


def _kst_today() -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).date().isoformat()


def _us_read() -> dict:
    try:
        with open(US_TRACK, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _us_write(d: dict):
    d["updated"] = _kst_today()
    os.makedirs(os.path.dirname(US_TRACK), exist_ok=True)
    with open(US_TRACK, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def _add_months(d: dt.date, k: int) -> dt.date:
    y, m = divmod(d.month - 1 + k, 12)
    y, m = d.year + y, m + 1
    feb = 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28
    last = [31, feb, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    out = dt.date(y, m, min(d.day, last))
    while out.weekday() >= 5:                 # 주말이면 월요일로
        out += dt.timedelta(days=1)
    return out


def us_schedule(start: str, n: int = US_TRANCHES) -> list[str]:
    s0 = dt.date.fromisoformat(start)
    return [_add_months(s0, k).isoformat() for k in range(n)]


def us_start(start: str | None = None, pool_usd: float | None = None, note: str = "") -> dict:
    """새 사이클을 연다. 진행 중 사이클이 있으면 거부한다(끝나기 전 재시작 = 회차 건너뛰기)."""
    d = _us_read()
    cur = d.get("cycle")
    if cur and len({f.get("tranche") for f in cur.get("fills", [])}) < cur.get("n", US_TRANCHES):
        raise ValueError(f"진행 중 사이클({cur.get('start')})이 끝나지 않았다 — 회차를 건너뛰는 재시작 금지")
    if cur:
        d.setdefault("history", []).append(cur)
    start = start or _kst_today()
    d["cycle"] = {"start": start, "n": US_TRANCHES, "schedule": us_schedule(start),
                  "pool_usd_at_start": pool_usd, "fills": [], "note": note}
    d["rule"] = "d205 — 달러 잔고 3회 균등 분할(월 1회) · 회차=그날 잔고÷남은 회차 · S&P 폭풍≥70이면 연기"
    _us_write(d)
    return d["cycle"]


def us_execute(usd: float, ticker: str, tranche: int | None = None, note: str = "",
               date: str | None = None) -> dict:
    """회차 집행 기록. **조회·기록 전용 — 주문을 내지 않는다.** 한 회차를 여러 종목으로 나눠 기록할 수 있다."""
    d = _us_read()
    cur = d.get("cycle")
    if not cur:
        raise ValueError("열린 사이클이 없다 — --us-start 먼저")
    done = sorted({f.get("tranche") for f in cur.get("fills", [])})
    if tranche is None:
        tranche = next((i for i in range(1, cur["n"] + 1) if i not in done), cur["n"])
    rec = {"date": date or _kst_today(), "tranche": int(tranche), "usd": round(float(usd), 2),
           "ticker": ticker, "note": note}
    cur.setdefault("fills", []).append(rec)
    _us_write(d)
    return rec


def _last_close(sym: str):
    try:
        import drawdown_history as D
        ds, cs = D.load(sym)
        return (cs[-1], ds[-1]) if cs else (None, None)
    except Exception:
        return None, None


_LIVE: dict = {}


def _px(sym: str, live: bool = True):
    """(가격, 출처) — 실시간(Yahoo) 우선, 실패하면 일봉 캐시.
    ★[9/22] 캐시만 쓰면 하루 늦다 — 9/21 밤 GOOGL이 +2% 오르자 18%까지 남은 몫이
    캐시 기준 $88.52 vs 실시간 $78.79로 $10 갈렸다(회차의 4%). 제안 금액은 집행 시점 가격으로."""
    if live:
        if sym not in _LIVE:
            try:
                from market_data import fetch_quote
                _LIVE[sym] = (fetch_quote(sym, timeout=6.0) or {}).get("price")
            except Exception:
                _LIVE[sym] = None
        if _LIVE[sym]:
            return float(_LIVE[sym]), "live"
    px, d = _last_close(sym)
    return px, (f"cache {d}" if px else None)


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


def _zone_hits(live: bool = True) -> list[dict]:
    """우선순위 ②③(GEV·ANET) 중 매수존(portfolio.json alerts, cond=below) 안에 든 종목."""
    try:
        with open(_PF_JSON, encoding="utf-8") as f:
            alerts = (json.load(f) or {}).get("alerts") or []
    except Exception:
        return []
    out = []
    for a in alerts:
        if a.get("ticker") in US_ZONE_TICKERS and a.get("cond") == "below" and a.get("level"):
            px, d = _px(a["ticker"], live)
            if px and px <= float(a["level"]):
                out.append({"ticker": a["ticker"], "price": round(px, 2), "level": a["level"], "asof": d})
    return out


def us_track(usd_cash: float | None = None, today: str | None = None, check_floor: bool = True,
             live: bool = True) -> dict:
    """미국 트랙 오늘 판정 — 이번 회차에 쓸 수 있는 달러와 대상 제안."""
    if usd_cash is None:
        try:
            with open(_PF_JSON, encoding="utf-8") as f:
                usd_cash = float((json.load(f) or {}).get("cash_usd") or 0)
        except Exception:
            usd_cash = 0.0
    today = today or _kst_today()
    cur = _us_read().get("cycle")
    out = {"usd_cash": round(usd_cash, 2), "today": today, "rule": "d205"}
    if not cur:
        out.update({"status": "no_cycle", "allowed_usd": 0.0,
                    "why": (f"열린 사이클 없음 — 달러 ${usd_cash:,.2f} ≥ ${US_MIN_CYCLE_USD:.0f}이면 "
                            "`tranche_rules.py --us-start`로 연다") if usd_cash >= US_MIN_CYCLE_USD
                    else f"열린 사이클 없음 · 달러 ${usd_cash:,.2f} < ${US_MIN_CYCLE_USD:.0f}"})
        return out
    n, sched = cur.get("n", US_TRANCHES), cur.get("schedule") or []
    fills = cur.get("fills") or []
    done = sorted({f.get("tranche") for f in fills})
    due = [i for i, d in enumerate(sched, 1) if d <= today]
    pending = [i for i in due if i not in done]
    remaining = [i for i in range(1, n + 1) if i not in done]
    per = usd_cash / len(remaining) if remaining else 0.0
    allowed = per * len(pending)
    halted, hwhy = (global_contagion_check() if check_floor else (False, "하드플로어 판정 생략"))
    nxt = next((sched[i - 1] for i in remaining if sched[i - 1] > today), None)
    out.update({"cycle_start": cur.get("start"), "schedule": sched, "n": n,
                "done": done, "due": due, "pending": pending,
                "per_tranche_usd": round(per, 2), "next_date": nxt,
                "halted": bool(halted), "halt_why": hwhy,
                "spent_usd": round(sum(float(f.get("usd") or 0) for f in fills), 2),
                "fills": fills})
    if not remaining:
        out.update({"status": "complete", "allowed_usd": 0.0,
                    "why": "사이클 3회 완료" + (f" — 달러 ${usd_cash:,.2f} ≥ ${US_MIN_CYCLE_USD:.0f}: 새 사이클 가능"
                                                if usd_cash >= US_MIN_CYCLE_USD else "")})
        return out
    if halted and pending:
        out.update({"status": "deferred", "allowed_usd": 0.0,
                    "why": f"회차 {pending} 도래했으나 하드플로어로 **연기** — {hwhy}"})
        return out
    if not pending:
        out.update({"status": "waiting", "allowed_usd": 0.0,
                    "why": f"다음 회차 {nxt} (회차당 약 ${per:,.2f} — 그날 잔고로 다시 계산)"})
        return out
    # 대상 제안 — 매수존 안 우선순위 → GOOGL 18% 상한 → VOO
    split, left = [], allowed
    zones = _zone_hits(live)
    if zones:
        each = left / len(zones)
        split = [{"ticker": z["ticker"], "usd": round(each, 2),
                  "why": f"매수존 ${z['level']} 이하(종가 ${z['price']})"} for z in zones]
        left = 0.0
    room = googl_room_usd(live)
    if left > 0 and not room.get("error"):
        g = min(left, room["room_usd"])
        if g >= 1:
            split.append({"ticker": "GOOGL", "usd": round(g, 2),
                          "why": f"비중 {room['weight_pct']}% → 18%까지 ${room['room_usd']:,.2f}"})
            left -= g
    if left >= 1:
        split.append({"ticker": "VOO", "usd": round(left, 2),
                      "why": ("매수존 종목 없음 · GOOGL 18% 상한 → 지수로" if not room.get("error")
                              else "GOOGL 상한 계산 불가 → 확인 후 배분")})
    out.update({"status": "due", "allowed_usd": round(allowed, 2), "split": split, "googl": room,
                "why": f"회차 {pending} 도래 — ${allowed:,.2f} (잔고 ${usd_cash:,.2f} ÷ 남은 {len(remaining)}회 × {len(pending)})"})
    return out


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
          check_contagion: bool = True, use_ledger: bool = True, kr_weight=None):
    """kr_weight = 국내주 비중 %(주식 기준). 주면 d207 룰6 우선 게이트를 적용한다 —
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
        lines.append(f"  현재 허용 상한 **0원** — 적립 대기(사다리 잠김 또는 하드플로어).")
    if reach:
        lines.append(f"  ✅ 1주 도달: {', '.join(f'{k} {v:,}원' for k, v in sorted(reach.items(), key=lambda x: x[1]))}")
    nearest = min((v for v in prices.values() if v > allowed_krw), default=None)
    if nearest is not None:
        name = next(k for k, v in prices.items() if v == nearest)
        lines.append(f"  ⏳ 최근접 미달: {name} {nearest:,}원 — **{nearest - allowed_krw:,.0f}원 부족**")
    lines.append(f"  참고 가용현금 {cash:,.0f}원 · 국내주 22% 초과 동안 원화는 미국 트랙 합류(d207 ②) — "
                 f"22% 이하일 때만 §2b 규칙3(적립분 미국 매수 금지)")
    lines.append("  ⚠️ 표시 전용 — 도달해도 §5 3중 게이트·하드플로어가 위에 그대로 있다.")
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


def main():
    ap = argparse.ArgumentParser(description="개정 리스크룰 1·2 판정 (측정·제안 전용)")
    ap.add_argument("--cash", type=float)
    ap.add_argument("--dd", type=float, help="코스피 낙폭%% 수동 지정(음수)")
    ap.add_argument("--storm", type=float, help="코스피 폭풍%%ile 수동 지정")
    ap.add_argument("--fear", type=float)
    ap.add_argument("--capitulation", type=float)
    ap.add_argument("--execute", type=int, metavar="STEP",
                    help="사다리 단계 집행 기록(1~5 = D0~D4. ⚠️D0 신설로 1=D0다). --amount 필수. 조회·기록 전용 — 주문 안 냄")
    ap.add_argument("--amount", type=float, help="--execute 와 함께 쓰는 집행 금액(원)")
    ap.add_argument("--note", default="", help="--execute 메모(종목·체결가 등)")
    # ★[2026-09-20] 체결일 지정 — 없으면 오늘로 박힌다. 9/17 체결을 9/20 세션에서 기입하니
    #   원장 날짜가 사흘 밀렸다(cap_delta_explain의 prev_date·감사 추적이 어긋난다).
    #   ledger_execute()는 처음부터 date 인자를 받고 있었는데 CLI만 안 뚫려 있었다.
    ap.add_argument("--date", help="--execute 체결일(YYYY-MM-DD). 생략 시 오늘")
    # ★[9/21 d205] 미국 트랙
    ap.add_argument("--us-start", nargs="?", const="", metavar="YYYY-MM-DD",
                    help="미국 트랙 새 사이클 시작(날짜 생략 = 오늘). 진행 중 사이클이 있으면 거부")
    ap.add_argument("--us-execute", action="store_true", help="미국 트랙 회차 집행 기록(--usd·--ticker 필수). 주문 안 냄")
    ap.add_argument("--usd", type=float, help="--us-execute 금액($)")
    ap.add_argument("--tranche", type=int, help="--us-execute 회차 번호(생략 = 다음 미집행 회차)")
    ap.add_argument("--kr-weight", type=float, help="국내주 비중%% 수동 지정(d207 룰6 게이트 확인용). 생략 = 최신 스냅샷")
    ap.add_argument("--rule2", action="store_true")
    ap.add_argument("--ticker", "--tickers", default="066570.KS")
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

    if a.us_start is not None:
        c = us_start(a.us_start or None, us_track(check_floor=False).get("usd_cash"), a.note)
        print(f"\n🇺🇸 미국 트랙 사이클 시작 — {c['start']} · 회차 {', '.join(c['schedule'])} · 시작 잔고 ${c['pool_usd_at_start']:,.2f}\n")
        return
    if a.us_execute:
        if a.usd is None or not a.ticker or a.ticker == "066570.KS":
            sys.exit("[tranche_rules] --us-execute 에는 --usd 와 --ticker(미국 종목)가 필요하다")
        rec = us_execute(a.usd, a.ticker, a.tranche, a.note, a.date)
        print(f"\n📒 미국 트랙 {rec['tranche']}회차 기록 — {rec['date']} · {rec['ticker']} ${rec['usd']:,.2f} "
              f"{('· ' + rec['note']) if rec['note'] else ''}\n")
        return

    if a.execute:
        if a.amount is None:
            sys.exit("[tranche_rules] --execute 에는 --amount 가 필요하다")
        rec = ledger_execute(a.execute, a.amount, a.note, a.date)
        # ⚠️[9/9] 같은 버그를 **세 번** 고쳤다(사다리 표시부·triggers.py·여기).
        #   `f"D{a.execute}"`처럼 인덱스로 D번호를 만들면 단계가 늘어난 순간 라벨이 거짓말한다.
        #   실제로 D0 첫 집행을 "D1 집행 기록"으로 찍었다 — 금액·원장은 정확한데 표시만 틀려서
        #   더 위험하다(원장을 안 열어보면 D1을 또 쓴 줄 안다). STEP_LABELS가 정본이다.
        _lab = (STEP_LABELS[a.execute - 1] if 0 < a.execute <= len(STEP_LABELS)
                else f"D{a.execute}")
        print(f"\n📒 {_lab} 집행 기록 — {rec['date']} · {rec['amount']:,}원 "
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

    kw = a.kr_weight if a.kr_weight is not None else kr_weight_pct()
    r = rule1(cash, dd, storm, fear, capit, kr_weight=kw)
    if a.json:
        print(json.dumps({"rule1": r, "us_track": us_track(), "rule2": rule2(a.ticker)}, ensure_ascii=False, indent=1))
        return

    print("\n═══ 룰1 🇰🇷 국내 트랙 — 코스피 낙폭 사다리 (재원 = 원화 · d205 트랙 분리) ═══")
    if stale and a.dd is None:
        print(f"  {stale}\n")
    print(f"  코스피 고점대비 **{dd:+.1f}%** · 원화 현금 {cash:,.0f}원 (달러는 아래 미국 트랙)\n")
    print(f"  {'단계':<6}{'낙폭':>8}{'배분':>7}  상태   근거")
    for i, s in enumerate(r["steps"], 1):
        mark = ("✅집행" if s.get("executed") else "🟢해금") if s["unlocked"] else "🔒잠김"
        _n = s.get("executed_n") or 1
        _nlabel = f"({_n}회)" if _n > 1 else ""
        why = (f"{s['why']}  ← {s.get('executed_on')} 집행 {s.get('executed_krw', 0):,.0f}원{_nlabel}"
               if s.get("executed") else s["why"])
        _lab = STEP_LABELS[i - 1] if i - 1 < len(STEP_LABELS) else f"D{i}"
        print(f"  {_lab:<6}{s['threshold']:>7.0f}%{s['alloc']*100:>6.0f}%  {mark}  {why}")
    print(f"  {'예비':<6}{'—':>8}{RESERVE*100:>6.0f}%  🔒봉인  회복 확인(게이트 2/3+) 전까지 영구 봉인")

    print(f"\n  누적 해금 **{r['unlocked_ratio']*100:.0f}%** = 상한 {r['cap_krw']:,}원"
          + (f" − 기집행 **{r['spent_krw']:,}원**({','.join(STEP_LABELS[i-1] for i in r['executed_steps'])}) "
             f"= **잔여 {r['allowed_krw']:,}원**" if r["spent_krw"] else ""))
    print(f"  {r['storm_why']}")
    print(f"  {r['capitulation_why']}")
    print(f"  → 최종 승수 **×{r['final_mult']}**  (하한 {MULT_FLOOR}·상한 {MULT_CAP} — 금액 감산 폐지)")
    print(f"\n  {r['halt_why']}")
    print(f"  {r['rule6_why']}")
    if r["halted"]:
        print("\n  🔴 **허용 트랜치 0원** — 글로벌 확산으로 개정 전제가 깨졌다.")
    elif r["rule6_block"]:
        print(f"\n  ⛔ **집행 0원 — 룰6 우선(d207)**. 사다리 자체 판정은 {r['ladder_allowed_krw']:,}원(적립 기록). "
              f"국내주가 {RULE6_KR_HI:.0f}% 이하로 내려오면 그 상한만큼 집행한다. 그동안 원화는 미국 트랙으로(d207 ②).")
    elif r["allowed_krw"] <= 0:
        # ★[8/28] 舊 문구는 원인을 항상 '이미 집행했다'로 단정했다 — 해금 자체가 0일 때도
        # 그렇게 나와 8/27에 오독을 만들었다(실제 원인은 낙폭이 -25%를 안 넘긴 것).
        if r["unlocked_ratio"] <= 0:
            print(f"\n  ⛔ **가용 0원** — 낙폭 {r['dd_pct']:.1f}%로 **어느 단계도 해금되지 않았다**"
                  f"(D0 기준 -20%). 더 빠져야 열린다.")
        else:
            print(f"\n  ⛔ **가용 0원** — 해금 상한 {r['cap_krw']:,}원을 "
                  f"기집행 {r['spent_krw']:,}원으로 **모두 소진**했다. "
                  f"다음 단계 낙폭에 도달해야 새 몫이 열린다.")
    else:
        print(f"\n  💰 **오늘 허용 잔여 = {r['allowed_krw']:,}원**"
              f"  (상한 = 총재원 {r['base_krw']:,.0f} × {r['available_ratio']*100:.0f}% × {r['final_mult']}"
              f" = {r['cap_krw']:,}원"
              + (f" − 기집행 {r['spent_krw']:,}원)" if r["spent_krw"] else ")"))
        print(f"     분할 권고: **{r['storm_splits']}회** "
              f"(1회 ≈ {round(r['allowed_krw']/r['storm_splits']):,}원) — 금액이 아니라 속도로 조절")
        print("     ※ 상한이지 목표가 아니다. 집행은 PM 판단·정훈 결정. 자동 집행 아님.")
        _ex = cap_delta_explain(r["base_krw"], r["available_ratio"], r["final_mult"], r["cap_krw"])
        if _ex and abs(_ex["by_cash"]) > 1000:
            print(f"\n  🔍 **상한 변동 분해** ({_ex['prev_date']} {_ex['cap_prev']:,}원 → 오늘 {_ex['cap_now']:,}원 · {_ex['delta']:+,}원)")
            print(f"     · 낙폭·승수 기여 **{_ex['by_drawdown']:+,}원**  (낙폭 {_ex['dd_prev']:+.1f}% → {r['dd_pct']:+.1f}%)")
            print(f"     · 재원 기여     **{_ex['by_cash']:+,}원**  (총재원 {_ex['cash_prev']:,}원 → {_ex['cash_now']:,}원)"
                  + ("  ※직전 행에 base 미기록 → 현금으로 근사" if _ex.get("approx") else ""))
            if abs(_ex["cross"]) >= 1:
                print(f"     · 교차항        {_ex['cross']:+,}원")
            if _ex["by_cash"] > abs(_ex["by_drawdown"]):
                print("     ⚠️ **상한 증가의 주된 원인이 낙폭이 아니라 현금이다** — 매도·입금으로 늘어난 몫은")
                print("        '사다리가 더 열렸다'는 뜻이 아니다. 사다리 비율은 낙폭 심도에 대한 위험허용도다.")

    print(_kr_accrual_note(r["allowed_krw"], cash))

    u = us_track()
    print("\n═══ 룰1 🇺🇸 미국 트랙 — 달러 3회 균등 분할 (d205 · 코스피 낙폭과 무관) ═══")
    print(f"  달러 잔고 ${u['usd_cash']:,.2f}")
    if u.get("schedule"):
        marks = []
        for i, d in enumerate(u["schedule"], 1):
            m = "✅" if i in u["done"] else ("🟢" if i in u["pending"] else "⏳")
            marks.append(f"{i}회 {d} {m}")
        print(f"  사이클 {u['cycle_start']} · " + " · ".join(marks) + f" · 기집행 ${u['spent_usd']:,.2f}")
    if u.get("halt_why"):
        print(f"  {u['halt_why']}")
    print(f"  → **{u['why']}**")
    for x in u.get("split") or []:
        print(f"     · {x['ticker']:<6} ${x['usd']:>8,.2f}  {x['why']}")
    if u.get("status") == "due":
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
