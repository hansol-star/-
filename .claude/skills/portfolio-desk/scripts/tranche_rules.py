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

# 폭풍 %ile → 승수. **0으로 만들지 않는다** — 이게 舊 §5b 역작동의 해소점.
STORM_MULT = [(97, 0.40), (90, 0.60), (75, 0.80), (0, 1.00)]

# 심리 항복 가산 — "공포에 사라"의 기계화. 공포·항복 둘 다 90%ile+ 일 때만.
CAPITULATION_BONUS = 1.20

MULT_FLOOR, MULT_CAP = 0.30, 1.20

# ⚠️ 금융 자회사를 연결하는 기업 — FCF·순부채 조건이 **구조적으로 왜곡**된다.
#    현대차는 현대캐피탈 할부금융 자산 증가가 영업활동현금흐름(CFO)에 마이너스로 잡혀
#    2023~25 CFO가 -2.5조→-5.7조→-6.0조다. 제조업 부진이 아니라 금융업 회계 특성이다.
#    (7/30 실측: 룰2 전종목 스캔에서 현대차가 3/3으로 오탐 → 이 예외 신설.)
#    ⇒ 이런 기업은 **마진 조건만 유효**로 보고, FCF·순부채는 판정에서 제외한 뒤 caveat를 붙인다.
FINANCIAL_ARM = {"005380.KS"}


def _storm_mult(pct):
    if pct is None:
        return 1.0, "폭풍 미확인 → 감산 없음(보수적 판단 필요)"
    for thr, m in STORM_MULT:
        if pct >= thr:
            label = {0.40: "극단", 0.60: "폭풍", 0.80: "경계", 1.00: "평온"}[m]
            return m, f"폭풍 {pct:.0f}%ile [{label}] → ×{m}"
    return 1.0, ""


def ladder_state(dd_pct: float):
    """현재 낙폭에서 해금된 누적 비율 + 단계별 상태."""
    unlocked, steps = 0.0, []
    for thr, alloc, why in LADDER:
        hit = dd_pct <= thr
        if hit:
            unlocked += alloc
        steps.append({"threshold": thr, "alloc": alloc, "why": why, "unlocked": hit})
    return unlocked, steps


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
          check_contagion: bool = True):
    unlocked, steps = ladder_state(dd_pct)
    smult, swhy = _storm_mult(storm_pct)

    capit = (fear_pct is not None and capit_pct is not None
             and fear_pct >= 90 and capit_pct >= 90)
    mult = smult * (CAPITULATION_BONUS if capit else 1.0)
    mult = max(MULT_FLOOR, min(MULT_CAP, mult))

    # 백테스트(rule_tracker --backfill)는 수천 번 호출하므로 네트워크 조회를 끈다.
    halted, hwhy = global_contagion_check() if check_contagion else (False, '확산 판정 생략(백테스트)')
    allowed = 0.0 if halted else cash * unlocked * mult

    return {
        "dd_pct": dd_pct, "cash": cash,
        "unlocked_ratio": unlocked, "steps": steps,
        "storm_mult": smult, "storm_why": swhy,
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
    try:
        import drawdown_history as D
        dates, closes = D.load(KOSPI)
        if closes:
            dd = D.current_drawdown(dates, closes)["dd_pct"]
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
    return cash, dd, storm, fear, capit


def main():
    ap = argparse.ArgumentParser(description="개정 리스크룰 1·2 판정 (측정·제안 전용)")
    ap.add_argument("--cash", type=float)
    ap.add_argument("--dd", type=float, help="코스피 낙폭%% 수동 지정(음수)")
    ap.add_argument("--storm", type=float, help="코스피 폭풍%%ile 수동 지정")
    ap.add_argument("--fear", type=float)
    ap.add_argument("--capitulation", type=float)
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

    cash, dd, storm, fear, capit = _load_inputs(a.cash)
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
    print(f"  코스피 고점대비 **{dd:+.1f}%** · 가용 현금 {cash:,.0f}원\n")
    print(f"  {'단계':<6}{'낙폭':>8}{'배분':>7}  상태   근거")
    for i, s in enumerate(r["steps"], 1):
        mark = "🟢해금" if s["unlocked"] else "🔒잠김"
        print(f"  D{i:<5}{s['threshold']:>7.0f}%{s['alloc']*100:>6.0f}%  {mark}  {s['why']}")
    print(f"  {'예비':<6}{'—':>8}{RESERVE*100:>6.0f}%  🔒봉인  회복 확인(게이트 2/3+) 전까지 영구 봉인")

    print(f"\n  누적 해금 **{r['unlocked_ratio']*100:.0f}%**")
    print(f"  {r['storm_why']}")
    print(f"  {r['capitulation_why']}")
    print(f"  → 최종 승수 **×{r['final_mult']}**  (하한 {MULT_FLOOR}·상한 {MULT_CAP})")
    print(f"\n  {r['halt_why']}")
    if r["halted"]:
        print("\n  🔴 **허용 트랜치 0원** — 글로벌 확산으로 개정 전제가 깨졌다.")
    else:
        print(f"\n  💰 **허용 트랜치 상한 = {r['allowed_krw']:,}원**"
              f"  ({cash:,.0f} × {r['unlocked_ratio']*100:.0f}% × {r['final_mult']})")
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
