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
RULE_LOG = os.path.join(ROOT, "data", "app", "rule_log.jsonl")


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
        raise ValueError(f"단계는 1~{len(LADDER)} (D1~D{len(LADDER)})")
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


def cap_delta_explain(cash, unlocked, mult):
    """오늘 상한이 어제와 달라진 이유를 **낙폭 기여 vs 현금 기여**로 분해한다.

    ★[2026-08-29 신설 — 리스크 데스크 지적 채택] 사다리 상한은 `cash × 해금비율 × 승수`라
    **포지션을 팔아 현금이 늘어도 상한이 커진다.** 실제로 8/28 META 1주 매도로 현금이
    655,618 → 1,455,006원(+122%)이 되면서 상한이 63,675 → 183,583원(+188%)으로 뛰었는데
    **코스피 낙폭은 -25.5% 그대로였다.** 이걸 그냥 보여주면 "사다리가 더 열렸다"는 착시가 된다.
    사다리 비율은 *낙폭 심도에 대한 위험허용도*를 재려는 설계이므로, 매도 재원으로 커진 몫은
    **낙폭과 무관하다는 사실을 숫자로 갈라서** 표시한다.
    ⚠️ 표시 전용 — 상한 계산 자체는 바꾸지 않는다(룰 변경은 정훈 승인 사항).
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
    c0, u0 = float(prev["cash"]), float(prev.get("unlocked_ratio") or 0)
    m0 = float(prev.get("final_mult") or 1.0)
    cap0, cap1 = c0 * u0 * m0, cash * unlocked * mult
    if abs(cap1 - cap0) < 1:
        return None
    dd_part = c0 * (unlocked * mult - u0 * m0)      # 낙폭·승수가 바꾼 몫
    cash_part = (cash - c0) * u0 * m0               # 현금이 바꾼 몫
    cross = (cap1 - cap0) - dd_part - cash_part     # 교차항
    return {"prev_date": prev.get("date"), "cap_prev": round(cap0), "cap_now": round(cap1),
            "delta": round(cap1 - cap0), "by_drawdown": round(dd_part),
            "by_cash": round(cash_part), "cross": round(cross),
            "cash_prev": round(c0), "cash_now": round(cash),
            "dd_prev": prev.get("dd_pct")}


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
    spent_krw = 0.0
    for i, s in enumerate(steps, 1):
        s["executed"] = i in done
        if s["executed"]:
            s["executed_on"] = done[i].get("date")
            s["executed_krw"] = done[i].get("amount")
            s["executed_n"] = done[i].get("n")
            if s["unlocked"]:
                spent_krw += float(done[i].get("amount") or 0)
    available = unlocked   # 해금 비율 자체는 낙폭이 정한다(RESET). 소진은 금액으로 뺀다.
    spent_ratio = (spent_krw / cash) if cash else 0.0

    capit = (fear_pct is not None and capit_pct is not None
             and fear_pct >= 90 and capit_pct >= 90)
    mult = CAPITULATION_BONUS if capit else 1.0
    mult = max(MULT_FLOOR, min(MULT_CAP, mult))

    # 백테스트(rule_tracker --backfill)는 수천 번 호출하므로 네트워크 조회를 끈다.
    halted, hwhy = global_contagion_check() if check_contagion else (False, '확산 판정 생략(백테스트)')
    # 누적 상한 = 해금분 전체. 여기서 **이미 집행한 금액**을 뺀 잔여가 오늘 여력이다.
    cap = cash * available * mult
    allowed = 0.0 if halted else max(0.0, cap - spent_krw)

    return {
        "dd_pct": dd_pct, "cash": cash,
        "unlocked_ratio": unlocked, "steps": steps,
        "spent_ratio": spent_ratio, "available_ratio": available,
        "spent_krw": round(spent_krw), "cap_krw": round(cap),
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
KR_CANDIDATES = {           # 국내 매수후보 1주 가격(보고서 갱신 시 함께 갱신)
    "NAVER": 227500, "삼성전자": 274000, "KT&G": 176300, "두산에너빌리티": 81800,
}


def _kr_accrual_note(allowed_krw, cash):
    """해금 상한이 국내 1주에 얼마나 모자란지 / 어디까지 닿는지."""
    reach = {k: v for k, v in KR_CANDIDATES.items() if allowed_krw >= v}
    lines = ["\n═══ 🇰🇷 국내 이월 적립 (crash_tf §2b · 8/14 신설) ═══"]
    if allowed_krw <= 0:
        lines.append(f"  현재 허용 상한 **0원** — 적립 대기(사다리 잠김 또는 하드플로어).")
    if reach:
        lines.append(f"  ✅ 1주 도달: {', '.join(f'{k} {v:,}원' for k, v in sorted(reach.items(), key=lambda x: x[1]))}")
    nearest = min((v for v in KR_CANDIDATES.values() if v > allowed_krw), default=None)
    if nearest is not None:
        name = next(k for k, v in KR_CANDIDATES.items() if v == nearest)
        lines.append(f"  ⏳ 최근접 미달: {name} {nearest:,}원 — **{nearest - allowed_krw:,.0f}원 부족**")
    lines.append(f"  참고 가용현금 {cash:,.0f}원 · 적립분은 미국 매수에 쓰지 않는다(§2b 규칙3)")
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
            usd = float(pf.get("cash_usd") or 0)
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
                    help="사다리 단계 집행 기록(1~4). --amount 필수. 조회·기록 전용 — 주문 안 냄")
    ap.add_argument("--amount", type=float, help="--execute 와 함께 쓰는 집행 금액(원)")
    ap.add_argument("--note", default="", help="--execute 메모(종목·체결가 등)")
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
        _n = s.get("executed_n") or 1
        _nlabel = f"({_n}회)" if _n > 1 else ""
        why = (f"{s['why']}  ← {s.get('executed_on')} 집행 {s.get('executed_krw', 0):,.0f}원{_nlabel}"
               if s.get("executed") else s["why"])
        print(f"  D{i:<5}{s['threshold']:>7.0f}%{s['alloc']*100:>6.0f}%  {mark}  {why}")
    print(f"  {'예비':<6}{'—':>8}{RESERVE*100:>6.0f}%  🔒봉인  회복 확인(게이트 2/3+) 전까지 영구 봉인")

    print(f"\n  누적 해금 **{r['unlocked_ratio']*100:.0f}%** = 상한 {r['cap_krw']:,}원"
          + (f" − 기집행 **{r['spent_krw']:,}원**(D{',D'.join(map(str, r['executed_steps']))}) "
             f"= **잔여 {r['allowed_krw']:,}원**" if r["spent_krw"] else ""))
    print(f"  {r['storm_why']}")
    print(f"  {r['capitulation_why']}")
    print(f"  → 최종 승수 **×{r['final_mult']}**  (하한 {MULT_FLOOR}·상한 {MULT_CAP} — 금액 감산 폐지)")
    print(f"\n  {r['halt_why']}")
    if r["halted"]:
        print("\n  🔴 **허용 트랜치 0원** — 글로벌 확산으로 개정 전제가 깨졌다.")
    elif r["allowed_krw"] <= 0:
        # ★[8/28] 舊 문구는 원인을 항상 '이미 집행했다'로 단정했다 — 해금 자체가 0일 때도
        # 그렇게 나와 8/27에 오독을 만들었다(실제 원인은 낙폭이 -25%를 안 넘긴 것).
        if r["unlocked_ratio"] <= 0:
            print(f"\n  ⛔ **가용 0원** — 낙폭 {r['dd_pct']:.1f}%로 **어느 단계도 해금되지 않았다**"
                  f"(D1 기준 -25%). 더 빠져야 열린다.")
        else:
            print(f"\n  ⛔ **가용 0원** — 해금 상한 {r['cap_krw']:,}원을 "
                  f"기집행 {r['spent_krw']:,}원으로 **모두 소진**했다. "
                  f"다음 단계 낙폭에 도달해야 새 몫이 열린다.")
    else:
        print(f"\n  💰 **오늘 허용 잔여 = {r['allowed_krw']:,}원**"
              f"  (상한 {cash:,.0f} × {r['available_ratio']*100:.0f}% × {r['final_mult']}"
              f" = {r['cap_krw']:,}원"
              + (f" − 기집행 {r['spent_krw']:,}원)" if r["spent_krw"] else ")"))
        print(f"     분할 권고: **{r['storm_splits']}회** "
              f"(1회 ≈ {round(r['allowed_krw']/r['storm_splits']):,}원) — 금액이 아니라 속도로 조절")
        print("     ※ 상한이지 목표가 아니다. 집행은 PM 판단·정훈 결정. 자동 집행 아님.")
        _ex = cap_delta_explain(cash, r["available_ratio"], r["final_mult"])
        if _ex and abs(_ex["by_cash"]) > 1000:
            print(f"\n  🔍 **상한 변동 분해** ({_ex['prev_date']} {_ex['cap_prev']:,}원 → 오늘 {_ex['cap_now']:,}원 · {_ex['delta']:+,}원)")
            print(f"     · 낙폭·승수 기여 **{_ex['by_drawdown']:+,}원**  (낙폭 {_ex['dd_prev']:+.1f}% → {r['dd_pct']:+.1f}%)")
            print(f"     · 현금 기여     **{_ex['by_cash']:+,}원**  (현금 {_ex['cash_prev']:,}원 → {_ex['cash_now']:,}원)")
            if abs(_ex["cross"]) >= 1:
                print(f"     · 교차항        {_ex['cross']:+,}원")
            if _ex["by_cash"] > abs(_ex["by_drawdown"]):
                print("     ⚠️ **상한 증가의 주된 원인이 낙폭이 아니라 현금이다** — 매도·입금으로 늘어난 몫은")
                print("        '사다리가 더 열렸다'는 뜻이 아니다. 사다리 비율은 낙폭 심도에 대한 위험허용도다.")

    print(_kr_accrual_note(r["allowed_krw"], cash))

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
