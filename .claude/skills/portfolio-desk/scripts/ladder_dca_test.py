#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ladder_dca_test.py — 룰1 국내 낙폭 사다리 vs '같은 돈·신호 없음' 대조군(DCA) 검정 (stdlib·무네트워크)

[왜 — 2026-09-30 정훈 "새로 찾은 우리 결함과 조치 실시" (2차 외부 리서치에서 나온 결함)]
AQR(S&P 1965–2025, buy-the-dip 변형 196개)은 '떨어지면 산다'가 같은 돈을 기계적으로 나눠 넣는 DCA보다
최종 자산이 18.7% 적고, 60% 넘는 변형이 위험조정으로도 열위라고 보고했다. d208은 **S&P** 사다리를 기각했지만
**코스피 사다리(룰1)는 '같은 돈을 신호 없이 넣는' 대조군과 한 번도 비교된 적이 없다.**
d0_test(9/9)는 "-20~-25%에서 사면 12M 뒤 오르나"(기저율)만 봤다 — 그건 '사도 되나'의 답이지
'사다리 방식으로 넣는 게 그냥 나눠 넣는 것보다 나은가'의 답이 아니다.
9/22 교훈("통과한 변형엔 신호 없이 같은 행동을 한 대조군을 붙인다")을 룰1 자신에게 소급 적용한다.

[전략 — 시작일 t0에 현금 1, 미집행 현금은 r_cash(0% · 2.5%/년)로 불어난다. 최종 자산 = 평가액 + 현금]
  LF    : **현행 룰1 그대로** — 해금 비율 = 현재 낙폭 기준(RESET) 누적 상한 × 총재원, 상한이 오른 만큼 그날
          종가에 집행, 이미 산 것은 안 판다, 예비 7% 봉인, S&P 폭풍(vol_gauge 정의 RV20 %ile) ≥70이면 그날 신규 정지.
          ⇒ allowed = cap − 기집행 이므로 기집행 = '플로어 아닌 날들의 해금 비율' running max 이고,
            레벨 k의 몫은 **t0 이후 처음으로 (낙폭 ≤ 문턱_k 그리고 플로어 아님)인 날** 종가에 들어간다.
            (이 등가를 매 실행 self-check ⓐ가 tranche_rules.ladder_state 문언 시뮬레이션과 대조한다.)
  L     : LF에서 하드플로어만 뺀 변형
  LS    : t0 일시 매수(참고)
  DCA3 / DCA6 / DCA12 : 21거래일 간격 균등 3·6·12회 (첫 회 = t0)
  SAME  : '신호 없는 같은 행동'(9/22 대조군 규칙) — 사다리가 지평 끝까지 **실제로 넣은 비율 f**를
          처음 6개월에 균등 분할. f는 사후값(대조군이 미래를 안다) → 전략이 아니라 **판정 도구**다.
  CASH  : 전액 현금
  (보조) LR : LF + 해제 — 낙폭이 -17.7%(7,500 프록시, us_track_test.RELEASE) 위로 회복하면 남은 돈 전부
          (예비 포함)를 다음 날부터 3개월 분할. 사다리가 '회복 뒤 남은 돈을 결국 넣는' 현실에 더 가까운 참고치.
  룩어헤드: 사다리의 t 결정은 t 이하 종가만 쓴다(고점 = t까지의 누적 최고가). S&P 폭풍은 **아시아·유럽 시장엔
          전일 미국 종가 값**을 쓴다 — 같은 날짜의 S&P 종가는 코스피 마감(15:30 KST) 뒤인 다음 날 새벽 5시에 나온다.

[판정 — 실행 전에 고정(사전등록)]
  주판정 = 코스피 · 조건부 시작점(낙폭 ≤ -20% = 사다리가 살아 있는 날) · 12M · LF.
  판정 대상 대조군 = DCA3·DCA6·DCA12 (LS는 참고, SAME은 별도 질문).
  ① 집계     : 중앙(LF − X) 부호가 현금 0% · 2.5% **둘 다** 같은 방향
  ② 에피소드 : 신고가로 끝나는 낙폭 에피소드(d0_test 정의 · 시작점 20개 이상)별 **평균** 차 부호 ≥ 70%
  ③ 횡단면   : 다른 지수 22개(d0_test.INDEX_ONLY ∪ us_track_test.GATES − 코스피, 조건부 시작점 100개 이상)
               각자 자기 지수를 사다리로 산다(플로어 = S&P 폭풍) — 중앙 부호 ≥ 70% (현금 0%)
  ②③에는 정확 단측 이항 p값을 같이 낸다(통과선은 선례대로 70% — p는 강도 표시).
  KEEP         = 세 DCA **전부**에 대해 ①②③ LF 우위
  REPLACE      = 어떤 DCA가 ①②③ **전부** LF를 이김 → 추천 = 통과한 DCA 중 **하위 5% 최종자산이 가장 높은 것**
                 (사다리의 주장 편익이 수익이 아니라 꼬리일 수 있다 — 꼬리를 가장 덜 내주는 대체안을 고른다)
  INCONCLUSIVE = 그 외.
  강등 조건    = 24M(현금 0%)에서 판정 대조군의 ① 부호가 반대로 뒤집히면 KEEP/REPLACE → INCONCLUSIVE.
                 [9/30 감사 명확화] REPLACE는 **통과 + 24M 유지**인 DCA 중에서 추천을 고른다(舊 코드는 추천 1개만
                 검사해, 추천이 뒤집히면 다른 통과 DCA가 멀쩡해도 전체를 강등했다 — 이번 결과엔 영향 없음).
  보조 질문(판정 아님) = LF − SAME ①②③: 사다리의 **타이밍**에 정보가 있나(같은 금액·다른 시점).

[9/30 재개 세션 감사 — 결과가 핵심 룰 교체(REPLACE)라 적대적으로 다시 봤다. 판정 규칙은 안 바꿨다]
  self-check(매 실행, 하나라도 FAIL이면 종료코드 2):
    ⓐ 빠른 경로 = tranche_rules.ladder_state로 하루씩 돌린 문언 시뮬레이션(base=현금+기집행, allowed=max(0,base×해금−기집행))
       — 현금 0%에서 코스피 전 시작점 **정확히 일치**, 2.5%에선 차이 크기를 보고(문언은 이자로 base가 커진다)
    ⓑ 낙폭 접두사 불변(drawdown(px[:c]) == dd[:c]) · 폭풍 국소성(값 i가 i 이전 272봉만으로 결정)
    ⓒ 폭풍 = vol_gauge.rolling_rv + percentile_rank 와 수치 일치
    ⓓ 코스피 폭풍 정렬이 **엄격히 이전** 미국 날짜만 쓰는지 독립 구현(투포인터)으로 재계산 대조
    ⓔ value() 회계 = 하루씩 현금·수량을 굴린 순진 시뮬레이션과 일치(이자 2.5%)
  견고성 렌즈(판정 아님 — 판정을 뒤집을 수 있는지만 본다):
    · 시차 1일(LAG1)  : 사다리는 **트리거 종가에 체결**된다(최대 유리). 다음 날 종가 체결로 다시 판정
    · 항복 가산 상한(LF12) : 룰1의 ×1.2(공포·항복 90%ile+)를 **항상 켠** 상한 — 과거 공포지표가 없어 상한으로 묶는다
    · LR 판정        : 사다리+해제(돈이 실제로 결국 들어가는 경로)도 ①②③으로
    · 현금금리 스윕   : 0~15% — 1997~2008 원화 금리(외환위기 두 자릿수)는 2.5%보다 높았다 = 사다리에 불리한 편향.
                       손익분기 금리를 낸다
    · onset 시작점   : 매일 시작 대신 **에피소드마다 -20% 첫 도달일 1개**(돈이 이미 기다리던 상황) — 코스피+22개 풀링
    · 시장×에피소드 풀링 : ②를 22개 시장까지 넓힌 에피소드 단위 이항검정
    · 노출 맞춤(SAMEBAR) : f의 **표본 평균 1개**만 쓰는 사전적 대조군 — SAME은 경로별 f(사후)를 알고, 사다리의
                       후속 매수는 '더 내려가야 발동'이라 정의상 더 싼 가격이다 → LF>SAME은 거의 기계적이다
    · 바닥 있는 DCA(DCA3F/6F) : REPLACE 제안이 미국 트랙처럼 하드플로어를 유지할 경우의 값

⚠️ 가격지수(배당 제외) — 더 많이·일찍 투자하는 쪽(DCA·LS)에 불리 = **사다리에 유리한 방향으로 보수적**.
⚠️ 거래비용·세금 0 · 환율 무관(원화로 국내주). 겹치는 창이라 표본 비독립 — ②가 그 보정이다.
⚠️ ③의 시장들은 같은 세계 위기(2008 등)를 공유 — 이항 p는 독립 가정이라 **과소평가된 불확실성**이다.
⚠️ 코스피 고점은 데이터 시작(1996-12-11) 이후 누적 최고가 — 1994년 고점(1,138)은 모른다.
⚠️ 폭풍 분할(2~4분할 권고)은 모델하지 않는다 — 해금분을 그날 전액 집행 = 현행 룰의 **최대 사용**(사다리에 유리).
⚠️ **측정 전용.** 룰을 바꾸지 않는다 — 결과가 REPLACE여도 제안일 뿐, 채택은 정훈 승인.

사용:
  python ladder_dca_test.py              # 전체(self-check + 주판정 + 22개 시장 + 견고성) · 결과 JSON 저장 (~2분)
  python ladder_dca_test.py --json       # 결과 JSON을 표준출력으로
  python ladder_dca_test.py --no-save    # data/research/ 에 저장하지 않음
  python ladder_dca_test.py --selfcheck  # self-check만
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import os
import random
import statistics as st
import sys
from datetime import date as _d

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import d0_test as D0              # noqa: E402  INDEX_ONLY (9/9 오염 교훈 — 주가 지수만)
import ladder_variants_test as LV  # noqa: E402  next_true
import tranche_rules as T         # noqa: E402  LADDER·RESERVE·ladder_state·MULT_CAP 정본 (사다리가 바뀌면 검정도 따라간다)
import us_track_test as U         # noqa: E402  load·drawdown·storm·ep_ids·pct·GATES·FLOOR·RELEASE
import vol_gauge as VG            # noqa: E402  폭풍 정본(self-check ⓒ 대조용)

ROOT = U.ROOT
OUT = os.path.join(ROOT, "data", "research", "ladder_dca_test.json")

LADDER = [(thr, a) for thr, a, _ in T.LADDER]
RESERVE = T.RESERVE
assert abs(sum(a for _, a in LADDER) + RESERVE - 1.0) < 1e-9, "사다리 배분 + 예비 ≠ 100%"
AMT = [a for _, a in LADDER]
# 항복 가산 상한: cap = base × 해금 × 1.2, 단 현금 1을 넘을 수 없다 → 누적 min(1, 1.2×누적)의 증분
_cum = [sum(AMT[:k + 1]) for k in range(len(AMT))]
_cum12 = [min(1.0, T.MULT_CAP * c) for c in _cum]
AMT12 = [_cum12[0]] + [_cum12[k] - _cum12[k - 1] for k in range(1, len(_cum12))]
TF_ON = LADDER[0][0]                    # -20 = 사다리가 살아 있는 문턱(D0)
FLOOR, RELEASE, MONTH, MIN_EP = U.FLOOR, U.RELEASE, U.MONTH, U.MIN_EP
SAME_N = 6                               # 9/22 대조군 = 처음 6개월 균등
DCAS = (3, 6, 12)
DCA_NAMES = [f"DCA{n}" for n in DCAS]
CTRLS = ["LS"] + DCA_NAMES + ["SAME", "CASH"]
AUX = ["SAME0", "SAMEBAR", "DCA3F", "DCA6F"]
ALL_CTRLS = CTRLS + AUX
PASS = 0.70
MIN_STARTS = 100
HORIZONS = (252, 504)
RATES = (0.0, 0.025)
RATE_GRID = (0.0, 0.025, 0.05, 0.075, 0.10, 0.15)
PRIMARY = "^KS11"
MARKETS = sorted((set(D0.INDEX_ONLY) | set(U.GATES)) - {PRIMARY})
# 미국 폭풍 값을 **같은 날짜**로 써도 되는 시장(마감이 미국 종가와 같은 시각대). 나머지는 전일 미국 값.
SAME_DAY_US = {"^GSPC", "^IXIC", "^DJI", "^RUT", "^GSPTSE", "^MXX", "^BVSP", "^MERV"}


# ───────────────────────────── 데이터
def _gpow(r: float, H: int) -> list[float]:
    g = U._daily(r)
    return [g ** k for k in range(H + 1)]


def align_prev(src_dates, src_vals, dates, same_day: bool, max_gap: int = 7):
    """src 값을 dates에 ffill. same_day=False면 **그 날짜보다 엄격히 이전** 봉만 쓴다(시차 룩어헤드 차단)."""
    out = []
    for d in dates:
        j = (bisect.bisect_right(src_dates, d) if same_day else bisect.bisect_left(src_dates, d)) - 1
        if j < 0 or (_d.fromisoformat(d) - _d.fromisoformat(src_dates[j])).days > max_gap:
            out.append(None)
        else:
            out.append(src_vals[j])
    return out


def prep(sym: str, spd: list[str], sps: list):
    """시장 하나의 전처리 — 레벨별 '처음 도달일' 역방향 스캔으로 시작점당 O(1)."""
    data = U.load(sym)
    if len(data) < 800:
        return None
    dates = [d for d, _ in data]
    px = [c for _, c in data]
    n = len(px)
    dd = U.drawdown(px)
    stm = sps if sym == "^GSPC" else align_prev(spd, sps, dates, same_day=sym in SAME_DAY_US)
    halted = [x is not None and x >= FLOOR for x in stm]
    lev = [LV.next_true([x <= thr for x in dd]) for thr, _ in LADDER]
    levF = [LV.next_true([dd[t] <= thr and not halted[t] for t in range(n)]) for thr, _ in LADDER]
    rel = LV.next_true([x > RELEASE for x in dd])
    nok = LV.next_true([not h for h in halted])
    return {"sym": sym, "dates": dates, "px": px, "dd": dd, "stm": stm, "halted": halted,
            "lev": lev, "levF": levF, "rel": rel, "nok": nok, "eps": U.ep_ids(data, dates)}


# ───────────────────────────── 시뮬레이션
def value(execs, px, s, H, gp):
    """execs = [(집행 인덱스, 금액)]. 가치 = 매수분 평가 + 남은 현금(이자 포함). ladder_variants.spend_value와 같은 회계."""
    end = s + H
    v = gp[H]
    for e, a in execs:
        v += a * (px[end] / px[e] - gp[end - e])
    return v


def spread(s, total, n):
    return [(s + MONTH * j, total / n) for j in range(n)]


def run_start(M, s, H, gp, with_lr=False, lag=0):
    """lag = 사다리 체결 시차(0 = 트리거 종가 체결 · 1 = 다음 날 종가). DCA 일정은 미리 정해져 있어 시차 없음."""
    px, end = M["px"], s + H
    out = {}
    for name, lv, amts in (("L", M["lev"], AMT), ("LF", M["levF"], AMT), ("LF12", M["levF"], AMT12)):
        ex = [(lv[k][s] + lag, a) for k, a in enumerate(amts) if lv[k][s] + lag <= end]
        f = sum(a for _, a in ex)
        out[name] = value(ex, px, s, H, gp)
        out["f_" + name] = f
        if name != "LF12":
            out["SAME_" + name] = value(spread(s, f, SAME_N), px, s, H, gp)
            out["SAME0_" + name] = value([(s, f)], px, s, H, gp)
    out["LS"] = px[end] / px[s]
    for N, nm in zip(DCAS, DCA_NAMES):
        out[nm] = value(spread(s, 1.0, N), px, s, H, gp)
    for N in (3, 6):   # 하드플로어를 유지한 DCA — 폭풍 ≥70이면 그 회차를 다음 비정지일로 연기(미국 트랙 P3와 같은 규칙)
        ex = [(M["nok"][s + MONTH * j], 1.0 / N) for j in range(N)]
        out[f"DCA{N}F"] = value([(e, a) for e, a in ex if e <= end], px, s, H, gp)
    out["CASH"] = gp[H]
    if with_lr:
        r = M["rel"][s]
        ex = [(M["levF"][k][s] + lag, a) for k, a in enumerate(AMT)
              if M["levF"][k][s] < r and M["levF"][k][s] + lag <= end]
        rem = 1.0 - sum(a for _, a in ex)
        ex += [(r + 1 + MONTH * k, rem / 3) for k in range(3) if r + 1 + MONTH * k <= end]
        out["LR"] = value(ex, px, s, H, gp)
    return out


def starts_of(M, H, conditional=True):
    n = len(M["px"])
    if conditional:
        return [s for s in range(n - H) if M["dd"][s] <= TF_ON]
    return list(range(n - H))


def onset_starts(M, H):
    """에피소드마다 낙폭 -20% **첫 도달일** 1개 — '돈이 이미 기다리던 상태에서 사다리가 켜지는' 시작점."""
    n, seen, out = len(M["px"]), set(), []
    for s in range(n - H):
        e = M["eps"][s]
        if M["dd"][s] <= TF_ON and e not in seen:
            seen.add(e)
            out.append(s)
    return out


# ───────────────────────────── self-check (감사)
def literal(M, s, H, r, floor=True):
    """tranche_rules.rule1 문언 그대로 하루씩: base = 현금 + 기집행, allowed = max(0, base×해금 − 기집행), 현금 한도."""
    g, px, end = U._daily(r), M["px"], s + H
    cash, spent, units = 1.0, 0.0, 0.0
    for t in range(s, end + 1):
        if not (floor and M["halted"][t]):
            unlocked, _ = T.ladder_state(M["dd"][t])
            allowed = min(cash, max(0.0, (cash + spent) * unlocked - spent))
            if allowed > 1e-15:
                units += allowed / px[t]
                cash -= allowed
                spent += allowed
        if t < end:
            cash *= g
    return cash + units * px[end]


def naive_dca(M, s, H, r, N):
    g, px, end = U._daily(r), M["px"], s + H
    sched = {s + MONTH * j for j in range(N)}
    cash, units = 1.0, 0.0
    for t in range(s, end + 1):
        if t in sched:
            units += (1.0 / N) / px[t]
            cash -= 1.0 / N
        if t < end:
            cash *= g
    return cash + units * px[end]


def selfcheck(K, spd, sp_closes, sps):
    res = []
    H = 252
    ss = starts_of(K, H)
    for r in (0.0, 0.025):
        gp = _gpow(r, H)
        worst = {"L": 0.0, "LF": 0.0}
        for s in ss:
            w = run_start(K, s, H, gp)
            for nm, fl in (("L", False), ("LF", True)):
                worst[nm] = max(worst[nm], abs(w[nm] - literal(K, s, H, r, fl)))
        ok = (max(worst.values()) < 1e-9) if r == 0 else (max(worst.values()) < 0.01)
        res.append({"id": "a", "ok": ok, "what": f"빠른 경로 = ladder_state 문언 시뮬 (현금 {r*100:.1f}%, 시작점 {len(ss)}개)",
                    "detail": f"최대 |차| L {worst['L']:.2e} · LF {worst['LF']:.2e}"
                              + ("" if r == 0 else " (문언은 이자로 base가 커져 조금 더 넣는다 — 허용 1%p 미만)")})
    rng = random.Random(7)
    n = len(K["px"])
    bad = sum(1 for c in (rng.randrange(300, n) for _ in range(40)) if U.drawdown(K["px"][:c]) != K["dd"][:c])
    loc_bad, m = 0, len(sp_closes)
    for j in (rng.randrange(2000, m) for _ in range(5)):
        sub = U.storm(sp_closes[j - 1000:j])
        loc_bad += sum(1 for k in range(500, 1000) if sub[k] != sps[j - 1000 + k])
    res.append({"id": "b", "ok": bad == 0 and loc_bad == 0, "what": "낙폭 접두사 불변 · 폭풍 국소성(미래 봉 무관)",
                "detail": f"낙폭 불일치 {bad}/40 · 폭풍 불일치 {loc_bad}/2500"})
    vg_bad = []
    for i in (rng.randrange(400, m) for _ in range(30)):
        rv = VG.rolling_rv(VG.log_returns(sp_closes[i - 300:i + 1]), 20)
        v = VG.percentile_rank(rv[-252:], rv[-1])
        if sps[i] is None or abs(v - sps[i]) > 0.051:
            vg_bad.append((i, v, sps[i]))
    res.append({"id": "c", "ok": not vg_bad, "what": "폭풍 = vol_gauge.rolling_rv+percentile_rank (S&P 30개 시점)",
                "detail": f"불일치 {len(vg_bad)}/30" + (f" 예 {vg_bad[:2]}" if vg_bad else "")})
    j, mis, same_used = -1, 0, 0
    for t, d in enumerate(K["dates"]):
        while j + 1 < len(spd) and spd[j + 1] < d:
            j += 1
        exp = None
        if j >= 0 and (_d.fromisoformat(d) - _d.fromisoformat(spd[j])).days <= 7:
            exp = sps[j]
        if exp != K["stm"][t]:
            mis += 1
        k = bisect.bisect_left(spd, d)
        if k < len(spd) and spd[k] == d and K["stm"][t] is not None and K["stm"][t] == sps[k] and sps[k] != exp:
            same_used += 1
    res.append({"id": "d", "ok": mis == 0 and same_used == 0, "what": "코스피 폭풍 = 엄격히 이전 미국 날짜(독립 투포인터)",
                "detail": f"불일치 {mis} · 같은 날 미국값 사용 {same_used} (코스피 {len(K['dates'])}일)"})
    gp = _gpow(0.025, H)
    worst = 0.0
    for s in rng.sample(ss, 50):
        w = run_start(K, s, H, gp)
        for N, nm in zip(DCAS, DCA_NAMES):
            worst = max(worst, abs(w[nm] - naive_dca(K, s, H, 0.025, N)))
    res.append({"id": "e", "ok": worst < 1e-9, "what": "value() 회계 = 하루씩 굴린 순진 시뮬(DCA·이자 2.5%·50개)",
                "detail": f"최대 |차| {worst:.2e}"})
    return res


# ───────────────────────────── 통계
def summ(xs):
    if not xs:
        return None
    return {"n": len(xs), "med": st.median(xs), "mean": st.mean(xs),
            "win": sum(1 for x in xs if x > 0) / len(xs) * 100,
            "p5": U.pct(xs, 0.05), "p95": U.pct(xs, 0.95)}


def wstats(ws):
    return {"n": len(ws), "med": st.median(ws), "mean": st.mean(ws), "p1": U.pct(ws, 0.01), "p5": U.pct(ws, 0.05),
            "p25": U.pct(ws, 0.25), "p75": U.pct(ws, 0.75), "p95": U.pct(ws, 0.95),
            "loss": sum(1 for w in ws if w < 1) / len(ws) * 100}


def binom_ge(k: int, n: int) -> float | None:
    """정확 단측 이항 p = P(X ≥ k | n, 0.5)."""
    if n <= 0:
        return None
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def ctrl_key(ctrl, var):
    if ctrl in ("SAME", "SAME0"):
        return f"{ctrl}_{var}" if var in ("L", "LF") else None
    return ctrl


def episodes(M, rows, var, ctrl):
    """신고가로 끝나는 낙폭 에피소드별 평균(var − ctrl) %p. 시작점 MIN_EP 미만 제외."""
    key = ctrl_key(ctrl, var)
    grp = {}
    for s, w in rows:
        grp.setdefault(M["eps"][s], []).append((s, w))
    out = []
    for k, items in sorted(grp.items(), key=lambda kv: kv[1][0][0]):
        if len(items) < MIN_EP:
            continue
        d = [(w[var] - w[key]) * 100 for _, w in items]
        ss = [s for s, _ in items]
        out.append({"from": M["dates"][ss[0]], "to": M["dates"][ss[-1]], "n": len(d),
                    "min_dd": round(min(M["dd"][ss[0]:ss[-1] + 1]), 1),
                    "f_mean": round(st.mean(w["f_LF"] for _, w in items), 3),
                    "mean": st.mean(d), "med": st.median(d)})
    return out


def tail_match(wealth, c, var="LF"):
    """꼬리 맞춤 렌즈(사후 추가 · 판정 아님): X를 현금과 섞어 **하위 5% 최종자산을 사다리와 같게** 만든 뒤 중앙을 비교.

    왜: 사다리는 12M에 평균 절반도 안 넣는다 — 중앙에서 DCA에 지는 게 '신호가 나빠서'인지
    '덜 넣어서(=위험을 덜 져서)'인지 갈라야 한다. x·W_X + (1−x)·현금 은 단조 아핀 변환이라
    분위수가 그대로 옮겨진다 → p5를 맞추는 x가 닫힌 해로 나온다.
    edge > 0 = 같은 꼬리에서 사다리 중앙이 더 높다. 사다리 꼬리가 현금보다도 좋으면(p5 ≥ 현금)
    어떤 혼합도 못 맞추므로 x=0(현금)과 비교하고 dominates=True로 표시한다.
    """
    out = {}
    p5L, medL = wealth[var]["p5"], wealth[var]["med"]
    for X in ["LS"] + DCA_NAMES:
        p5X = wealth[X]["p5"]
        if p5L >= c:
            x, dom = 0.0, True
        elif p5X >= p5L:
            x, dom = 1.0, False
        else:
            x, dom = (c - p5L) / (c - p5X), False
        bm = x * wealth[X]["med"] + (1 - x) * c
        out[X] = {"x": x, "blend_med": bm, "edge": (medL - bm) * 100, "dominates": dom}
    return out


def ep_count(rows):
    win = sum(1 for r in rows if r["mean"] > 0)
    lose = sum(1 for r in rows if r["mean"] < 0)
    return {"L_win": win, "X_win": lose, "n": len(rows),
            "p_L": binom_ge(win, win + lose), "p_X": binom_ge(lose, win + lose)}


# ───────────────────────────── 한 시장·한 설정 전체
def analyze(M, H, r, conditional=True, detail=False, lag=0):
    gp = _gpow(r, H)
    ss = starts_of(M, H, conditional)
    if not ss:
        return None
    rows = [(s, run_start(M, s, H, gp, with_lr=conditional, lag=lag)) for s in ss]
    fbar = st.mean(w["f_LF"] for _, w in rows)           # 노출 맞춤 대조군 — 표본 평균 스칼라 1개
    for s, w in rows:
        w["SAMEBAR"] = value(spread(s, fbar, SAME_N), M["px"], s, H, gp)
    res = {"n": len(rows), "first": M["dates"][ss[0]], "last": M["dates"][ss[-1]], "fbar": fbar,
           "diff": {}, "wealth": {}, "deploy": {}}
    vars_ = ["LF", "L", "LF12"] + (["LR"] if conditional else [])
    names = vars_ + ["LS", *DCA_NAMES, "DCA3F", "DCA6F", "SAME_L", "SAME_LF", "SAME0_LF", "SAMEBAR", "CASH"]
    for nm in names:
        res["wealth"][nm] = wstats([w[nm] for _, w in rows])
    res["tail_match"] = tail_match(res["wealth"], gp[H], "LF")
    if detail:
        for var in ("L", "LF", "LF12"):
            fs = [w["f_" + var] for _, w in rows]
            res["deploy"][var] = {"mean": st.mean(fs), "med": st.median(fs),
                                  "share_ge": {f"{c:.2f}": sum(1 for f in fs if f >= c - 1e-9) / len(fs) * 100
                                               for c in (0.08, 0.23, 0.43, 0.68, 0.93)}}
    for var in vars_:
        res["diff"][var] = {}
        for c in ALL_CTRLS:
            k = ctrl_key(c, var)
            if k is not None:
                res["diff"][var][c] = summ([(w[var] - w[k]) * 100 for _, w in rows])
        if detail:
            res.setdefault("ep", {})[var] = {}
            for c in ALL_CTRLS:
                if ctrl_key(c, var) is not None:
                    er = episodes(M, rows, var, c)
                    res["ep"][var][c] = {"count": ep_count(er), "rows": er}
    return res


def cross_market(mk, H, r, conditional=True, lag=0):
    out = []
    for sym, M in mk.items():
        a = analyze(M, H, r, conditional, detail=conditional, lag=lag)
        if not a or a["n"] < MIN_STARTS:
            out.append({"sym": sym, "n": a["n"] if a else 0, "skip": True})
            continue
        row = {"sym": sym, "n": a["n"], "first": a["first"], "last": a["last"], "fbar": a["fbar"],
               "med": {var: {c: x["med"] for c, x in a["diff"][var].items()} for var in a["diff"]},
               "p5": {nm: a["wealth"][nm]["p5"] for nm in ("LF", "LS", *DCA_NAMES)},
               "tm_edge": {X: a["tail_match"][X]["edge"] for X in a["tail_match"]},
               "skip": False}
        if conditional:
            row["ep"] = {var: {c: a["ep"][var][c]["count"] for c in DCA_NAMES + ["SAMEBAR"]} for var in a["ep"]}
        out.append(row)
    return out


def tm_count(cross, X):
    use = [c for c in cross if not c["skip"]]
    win = sum(1 for c in use if c["tm_edge"][X] > 0)
    lose = sum(1 for c in use if c["tm_edge"][X] < 0)
    return {"L_win": win, "X_win": lose, "n": len(use), "p_L": binom_ge(win, win + lose),
            "p_X": binom_ge(lose, win + lose)}


def cross_count(cross, var, ctrl):
    use = [c for c in cross if not c["skip"] and ctrl in c["med"].get(var, {})]
    win = sum(1 for c in use if c["med"][var][ctrl] > 0)
    lose = sum(1 for c in use if c["med"][var][ctrl] < 0)
    return {"L_win": win, "X_win": lose, "n": len(use),
            "p_L": binom_ge(win, win + lose), "p_X": binom_ge(lose, win + lose)}


def ep_pool(prim_ep, cross, var, ctrl):
    """시장×에피소드 풀링 — 코스피 ② + 22개 시장 각자의 에피소드(시작점 20+)를 한 표본으로."""
    win, lose = prim_ep["L_win"], prim_ep["X_win"]
    for c in cross:
        if not c["skip"]:
            e = c["ep"][var][ctrl]
            win += e["L_win"]
            lose += e["X_win"]
    return {"L_win": win, "X_win": lose, "n": win + lose,
            "p_L": binom_ge(win, win + lose), "p_X": binom_ge(lose, win + lose)}


def onset_lens(K, mk, H, r=0.0):
    gp = _gpow(r, H)
    rows = []
    for sym, M in [(PRIMARY, K)] + list(mk.items()):
        for s in onset_starts(M, H):
            w = run_start(M, s, H, gp, with_lr=True)
            rows.append({"sym": sym, "date": M["dates"][s], "dd": round(M["dd"][s], 1),
                         "f_LF": w["f_LF"], **{f"{v}-{c}": (w[v] - w[c]) * 100
                                               for v in ("LF", "LR") for c in ["LS", *DCA_NAMES, "CASH"]}})
    out = {"n": len(rows), "rows": rows, "count": {}}
    for v in ("LF", "LR"):
        for c in ["LS", *DCA_NAMES, "CASH"]:
            xs = [x[f"{v}-{c}"] for x in rows]
            win, lose = sum(1 for x in xs if x > 0), sum(1 for x in xs if x < 0)
            out["count"][f"{v}-{c}"] = {"med": st.median(xs) if xs else None, "L_win": win, "X_win": lose,
                                        "p_L": binom_ge(win, win + lose), "p_X": binom_ge(lose, win + lose)}
    return out


def rate_sweep(K, H):
    """현금금리 스윕 — 코스피 ①②. 미집행 현금이 많은 사다리에 금리가 유리하게 작동한다."""
    out = {}
    for r in RATE_GRID:
        a = analyze(K, H, r, True, detail=True)
        out[f"{r}"] = {X: {"med": a["diff"]["LF"][X]["med"], "ep": a["ep"]["LF"][X]["count"]}
                       for X in DCA_NAMES}
    be = {}
    for X in DCA_NAMES:
        pts = [(r, out[f"{r}"][X]["med"]) for r in RATE_GRID]
        be[X] = None
        for (r0, m0), (r1, m1) in zip(pts, pts[1:]):
            if m0 < 0 <= m1:
                be[X] = r0 + (r1 - r0) * (-m0) / (m1 - m0)
                break
        if be[X] is None and pts[0][1] >= 0:
            be[X] = 0.0
    return {"grid": out, "breakeven": be}


# ───────────────────────────── 판정(사전등록 그대로)
def judge(prim, cross12, var, ctrls):
    """prim[H][r] = analyze(detail) 결과. 반환 = 대조군별 ①②③ 방향 + 종합."""
    per = {}
    for X in ctrls:
        m0 = prim["252"]["0.0"]["diff"][var][X]["med"]
        m25 = prim["252"]["0.025"]["diff"][var][X]["med"]
        e = prim["252"]["0.0"]["ep"][var][X]["count"]
        c = cross_count(cross12, var, X)
        m24 = prim["504"]["0.0"]["diff"][var][X]["med"]
        p = {"m0": m0, "m25": m25, "m24": m24, "ep": e, "cross": c,
             "L1": m0 > 0 and m25 > 0, "X1": m0 < 0 and m25 < 0,
             "L2": e["n"] > 0 and e["L_win"] / e["n"] >= PASS, "X2": e["n"] > 0 and e["X_win"] / e["n"] >= PASS,
             "L3": c["n"] > 0 and c["L_win"] / c["n"] >= PASS, "X3": c["n"] > 0 and c["X_win"] / c["n"] >= PASS}
        p["L_all"] = p["L1"] and p["L2"] and p["L3"]
        p["X_all"] = p["X1"] and p["X2"] and p["X3"]
        per[X] = p
    return per


def verdict(prim, cross12, var="LF"):
    per = judge(prim, cross12, var, DCA_NAMES)
    wealth = prim["252"]["0.0"]["wealth"]
    note = ""
    rec = None
    if all(p["L_all"] for p in per.values()):
        v = "KEEP"
        flipped = [X for X, p in per.items() if p["m24"] < 0]
        if flipped:
            v, note = "INCONCLUSIVE", f"24M에서 {','.join(flipped)} 대비 ① 부호 반전 → 강등"
    else:
        passing = [X for X, p in per.items() if p["X_all"]]
        stable = [X for X in passing if per[X]["m24"] < 0]
        if stable:
            rec, v = max(stable, key=lambda X: wealth[X]["p5"]), "REPLACE"
            if len(stable) < len(passing):
                note = f"24M에서 뒤집혀 추천 후보 제외: {','.join(X for X in passing if X not in stable)}"
        elif passing:
            v, note = "INCONCLUSIVE", f"①②③ 통과 {','.join(passing)} 전부 24M에서 부호 반전 → 강등"
        else:
            v = "INCONCLUSIVE"
    return {"verdict": v, "recommend": rec, "note": note, "per": per,
            "passing": [X for X, p in per.items() if p["X_all"]]}


# ───────────────────────────── 출력
def f2(x):
    return "—" if x is None else f"{x:+.2f}"


def pfmt(p):
    return "—" if p is None else (f"{p:.4f}" if p >= 0.0001 else f"{p:.1e}")


def vline(lab, VV):
    s = f"  판정 {lab}: **{VV['verdict']}**" + (f" → 추천 {VV['recommend']}" if VV["recommend"] else "")
    s += f"  ({VV['note']})" if VV["note"] else ""
    for X, p in VV["per"].items():
        s += (f"\n    vs {X:<6} ①LF우위 {'✅' if p['L1'] else '❌'}/대조우위 {'✅' if p['X1'] else '❌'} "
              f"(12M 중앙 {f2(p['m0'])}·{f2(p['m25'])} · 24M {f2(p['m24'])})  "
              f"②{p['ep']['L_win']}:{p['ep']['X_win']}/{p['ep']['n']}  ③{p['cross']['L_win']}:{p['cross']['X_win']}/{p['cross']['n']}")
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description="룰1 코스피 낙폭 사다리 vs 같은 돈 DCA 대조군 — 8/5 3단 절차 + 9/22 대조군 + 9/30 감사")
    ap.add_argument("--json", action="store_true", help="결과 JSON을 표준출력으로")
    ap.add_argument("--no-save", action="store_true", help="data/research/ladder_dca_test.json 저장 안 함")
    ap.add_argument("--selfcheck", action="store_true", help="self-check(감사 5종)만 돌리고 끝낸다")
    a = ap.parse_args()

    sp = U.load("^GSPC")
    if not sp:
        print("[ERR] data/history/_GSPC.csv 없음 — history_backfill.py 먼저", file=sys.stderr)
        return 1
    spd, spc = [d for d, _ in sp], [c for _, c in sp]
    sps = U.storm(spc)
    K = prep(PRIMARY, spd, sps)
    if not K:
        print("[ERR] 코스피 시계열 없음", file=sys.stderr)
        return 1
    SC = selfcheck(K, spd, spc, sps)
    sc_ok = all(x["ok"] for x in SC)
    if a.selfcheck or not a.json:
        print("【self-check — 감사】")
        for x in SC:
            print(f"  {'PASS' if x['ok'] else 'FAIL'} ⓐⓑⓒⓓⓔ"[0:5] + f" ({x['id']}) {x['what']} — {x['detail']}")
    if a.selfcheck:
        return 0 if sc_ok else 2
    if not sc_ok:
        print("[FAIL] self-check 실패 — 결과를 믿을 수 없어 중단", file=sys.stderr)
        return 2

    mk = {}
    for sym in MARKETS:
        M = prep(sym, spd, sps)
        if M:
            mk[sym] = M

    prim = {str(H): {str(r): analyze(K, H, r, True, detail=True) for r in RATES} for H in HORIZONS}
    uncond = {str(H): {str(r): analyze(K, H, r, False, detail=True) for r in RATES} for H in HORIZONS}
    cross = {str(H): cross_market(mk, H, 0.0, True) for H in HORIZONS}
    cross_u = cross_market(mk, 252, 0.0, False)
    # 견고성 — 시차 1일
    prim_lag = {str(H): {str(r): analyze(K, H, r, True, detail=True, lag=1) for r in RATES} for H in HORIZONS}
    cross_lag = cross_market(mk, 252, 0.0, True, lag=1)

    V = verdict(prim, cross["252"], "LF")
    VL = verdict(prim, cross["252"], "L")
    robust = {"LAG1_LF": verdict(prim_lag, cross_lag, "LF"),
              "LF12": verdict(prim, cross["252"], "LF12"),
              "LR": verdict(prim, cross["252"], "LR")}
    same = judge(prim, cross["252"], "LF", ["SAME", "SAME0", "SAMEBAR", "DCA3F", "DCA6F", "LS", "CASH"])
    pooled = {var: {X: ep_pool(prim["252"]["0.0"]["ep"][var][X]["count"], cross["252"], var, X)
                    for X in DCA_NAMES + ["SAMEBAR"]} for var in ("LF", "L", "LR")}
    onset = {str(H): onset_lens(K, mk, H) for H in HORIZONS}
    sweep = {str(H): rate_sweep(K, H) for H in HORIZONS}

    J = {"as_of_data": K["dates"][-1], "ladder": LADDER, "reserve": RESERVE, "floor": FLOOR,
         "amt12": AMT12, "selfcheck": SC,
         "primary": prim, "uncond": uncond, "cross": cross, "cross_uncond_252": cross_u,
         "verdict_LF": V, "verdict_L": VL, "aux_LF": same, "robust": robust,
         "primary_lag1": {H: {r: {"diff": x["diff"], "wealth": x["wealth"]} for r, x in d.items()}
                          for H, d in prim_lag.items()},
         "pooled_ep_12m": pooled, "onset": onset, "rate_sweep": sweep,
         "tail_match_cross": {str(H): {X: tm_count(cross[str(H)], X) for X in ["LS"] + DCA_NAMES} for H in HORIZONS},
         "markets": {s: {"from": m["dates"][0], "to": m["dates"][-1]} for s, m in mk.items()}}

    if not a.no_save:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(J, f, ensure_ascii=False, indent=1, default=float)
    if a.json:
        print(json.dumps(J, ensure_ascii=False, indent=1, default=float))
        return 0

    P = prim["252"]["0.0"]
    print("=" * 96)
    print(f"  룰1 코스피 사다리 vs 같은 돈 DCA — 조건부 시작점(낙폭 ≤ {TF_ON:.0f}%) {P['n']}개 "
          f"({P['first']} ~ {P['last']}) · 데이터 {K['dates'][0]}~{K['dates'][-1]}")
    print("=" * 96)
    for var in ("LF", "LF12"):
        dp = P["deploy"][var]
        print(f"\n[사다리 실제 집행 비율 12M · {var}] 평균 {dp['mean']*100:.1f}% · 중앙 {dp['med']*100:.1f}% · "
              + " / ".join(f"≥{float(k)*100:.0f}% {v:.0f}%" for k, v in dp["share_ge"].items()))
    for H in HORIZONS:
        for r in RATES:
            R = prim[str(H)][str(r)]
            print(f"\n【① {H // 21}M · 현금 {r*100:.1f}%】 최종자산(시작 1.00)")
            print(f"  {'전략':<9}{'중앙':>8}{'평균':>8}{'하위5%':>8}{'하위1%':>8}{'상위5%':>8}{'손실확률':>9}")
            for nm in ["LF", "L", "LF12", "LR", "LS", "DCA3", "DCA6", "DCA12", "DCA3F", "SAME_LF", "SAMEBAR", "CASH"]:
                w = R["wealth"][nm]
                print(f"  {nm:<9}{w['med']:>8.3f}{w['mean']:>8.3f}{w['p5']:>8.3f}{w['p1']:>8.3f}{w['p95']:>8.3f}{w['loss']:>8.1f}%")
            print(f"  {'LF − X (%p)':<14}{'중앙':>8}{'평균':>8}{'승률':>8}{'하위5%':>8}{'상위5%':>8}")
            for c in ALL_CTRLS:
                x = R["diff"]["LF"][c]
                print(f"  {c:<14}{f2(x['med']):>8}{f2(x['mean']):>8}{x['win']:>7.1f}%{f2(x['p5']):>8}{f2(x['p95']):>8}")

    print("\n【② 에피소드 분해 — 코스피 12M · 현금 0% · LF − X 평균 %p】")
    er = P["ep"]["LF"]
    show = CTRLS + ["SAMEBAR"]
    rows0 = er["DCA3"]["rows"]
    print(f"  {'시작점 구간':<25}{'n':>5}{'최저DD':>8}{'집행':>6}" + "".join(f"{c:>8}" for c in show))
    for i, row in enumerate(rows0):
        vals = "".join(f"{er[c]['rows'][i]['mean']:>+8.2f}" for c in show)
        print(f"  {row['from']}~{row['to']:<14}{row['n']:>5}{row['min_dd']:>8}{row['f_mean']*100:>5.0f}%{vals}")
    for c in show:
        e = er[c]["count"]
        print(f"  vs {c:<7} LF 우위 {e['L_win']}/{e['n']} (p={pfmt(e['p_L'])}) · 대조군 우위 {e['X_win']}/{e['n']} (p={pfmt(e['p_X'])})")

    print("\n【③ 횡단면 — 각 지수가 자기 사다리 · 12M · 현금 0% · 중앙 LF − X %p】")
    print(f"  {'시장':<11}{'n':>6}{'f̄':>6}" + "".join(f"{c:>8}" for c in show))
    for c in cross["252"]:
        if c["skip"]:
            print(f"  {c['sym']:<11}{c['n']:>6}  (조건부 시작점 < {MIN_STARTS} — 제외)")
            continue
        print(f"  {c['sym']:<11}{c['n']:>6}{c['fbar']*100:>5.0f}%" + "".join(f"{c['med']['LF'][x]:>+8.2f}" for x in show))
    for x in show:
        cc = cross_count(cross["252"], "LF", x)
        c24 = cross_count(cross["504"], "LF", x)
        print(f"  vs {x:<7} LF 우위 {cc['L_win']}/{cc['n']} (p={pfmt(cc['p_L'])}) · 대조군 우위 {cc['X_win']}/{cc['n']} "
              f"(p={pfmt(cc['p_X'])})  | 24M: LF 우위 {c24['L_win']}/{c24['n']}")

    print("\n【꼬리 맞춤 렌즈(사후 추가 · 판정 아님) — X를 현금과 섞어 하위 5%를 사다리(LF)와 같게 만든 뒤 중앙 비교】")
    print("  edge = LF 중앙 − 혼합 중앙 (%p, 양수 = 같은 꼬리에서 사다리가 더 번다) · x = 혼합 속 X 비중")
    for H in HORIZONS:
        for r in RATES:
            tm = prim[str(H)][str(r)]["tail_match"]
            print(f"  {H // 21:>2}M 현금{r*100:.1f}%: " + " · ".join(
                f"{X} x={t['x']:.2f} edge {t['edge']:+.2f}" + ("(LF꼬리>현금)" if t["dominates"] else "")
                for X, t in tm.items()))
    for H in HORIZONS:
        print(f"  ③ 횡단면 {H // 21}M · 현금 0% — 꼬리 맞춤에서 LF 우위: " + " · ".join(
            f"{X} {tm_count(cross[str(H)], X)['L_win']}/{tm_count(cross[str(H)], X)['n']}"
            f"(p={pfmt(tm_count(cross[str(H)], X)['p_L'])})" for X in ["LS"] + DCA_NAMES))

    print("\n【견고성 — 판정을 뒤집을 수 있는가】")
    print("  (1) 현금금리 스윕 · 코스피 LF − X 중앙 %p (② 대조군 우위 에피소드 수)")
    for H in HORIZONS:
        g = sweep[str(H)]
        for r in RATE_GRID:
            x = g["grid"][f"{r}"]
            print(f"    {H // 21:>2}M 현금 {r*100:>4.1f}%: " + " · ".join(
                f"{X} {f2(x[X]['med'])} (②{x[X]['ep']['X_win']}/{x[X]['ep']['n']})" for X in DCA_NAMES))
        print(f"    {H // 21:>2}M 손익분기 금리(① 중앙 = 0): " + " · ".join(
            f"{X} {'>' + format(RATE_GRID[-1]*100, '.0f') + '%' if b is None else format(b*100, '.1f') + '%'}"
            for X, b in g["breakeven"].items()))
    print("  (2) onset 시작점(에피소드마다 -20% 첫 도달일 1개 · 코스피+22개 풀링) — 12M/24M · 현금 0%")
    for H in HORIZONS:
        o = onset[str(H)]
        print(f"    {H // 21:>2}M n={o['n']}: " + " · ".join(
            f"{k} 중앙 {f2(v['med'])} 사다리 우위 {v['L_win']}/{v['L_win'] + v['X_win']}(p_X={pfmt(v['p_X'])})"
            for k, v in o["count"].items() if k.split('-')[1] in ("DCA3", "DCA6", "DCA12")))
    print("    코스피 onset: " + " / ".join(
        f"{x['date']}({x['dd']}%) LF−DCA3 {x['LF-DCA3']:+.1f} · LR−DCA3 {x['LR-DCA3']:+.1f}"
        for x in onset["252"]["rows"] if x["sym"] == PRIMARY))
    print("  (3) 시장×에피소드 풀링(12M · 현금 0% · 코스피 ② + 22개 시장 에피소드)")
    for var in ("LF", "L", "LR"):
        print(f"    {var}: " + " · ".join(
            f"vs {X} 사다리 우위 {p['L_win']}/{p['n']} (p_X={pfmt(p['p_X'])})" for X, p in pooled[var].items()))
    print("  (4) 변형 판정(사전등록 규칙 그대로 적용)")
    print(vline("LAG1(다음 날 종가 체결)", robust["LAG1_LF"]))
    print(vline("LF12(항복 가산 ×1.2 항상 켬 = 상한)", robust["LF12"]))
    print(vline("LR(사다리+해제 = 돈이 결국 들어가는 경로)", robust["LR"]))

    print("\n【참고 — 무조건 시작점(모든 날) · 코스피 12M · 현금 0%】")
    Uc = uncond["252"]["0.0"]
    print(f"  시작점 {Uc['n']}개 · LF 평균 집행 {Uc['deploy']['LF']['mean']*100:.1f}%")
    for c in CTRLS:
        x = Uc["diff"]["LF"][c]
        cc = cross_count(cross_u, "LF", c)
        print(f"  LF − {c:<6} 중앙 {f2(x['med'])} · 승률 {x['win']:.1f}% · 하위5% {f2(x['p5'])}  | 횡단면 LF 우위 {cc['L_win']}/{cc['n']}")

    print("\n" + "=" * 96)
    print(vline("LF(현행 룰1·플로어 포함) — 주판정", V))
    print(vline("L(플로어 없음) — 참고", VL))
    for X, p in same.items():
        print(f"  보조 LF − {X:<7}: ① 12M {f2(p['m0'])}·{f2(p['m25'])} · 24M {f2(p['m24'])}  "
              f"② LF 우위 {p['ep']['L_win']}/{p['ep']['n']} (p={pfmt(p['ep']['p_L'])})  "
              f"③ LF 우위 {p['cross']['L_win']}/{p['cross']['n']} (p={pfmt(p['cross']['p_L'])})")
    print("  ⚠️ 측정 전용 — 룰을 바꾸지 않는다. REPLACE여도 제안이며 채택은 정훈 승인.")
    if not a.no_save:
        print(f"  저장: {os.path.relpath(OUT, ROOT)}")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
