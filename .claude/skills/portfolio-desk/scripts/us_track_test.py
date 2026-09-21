#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
us_track_test.py — 룰1 사다리(코스피 낙폭)가 **미국주 매수**까지 막는 게 맞는가 (stdlib·무네트워크)

[왜 — 2026-09-21 정훈 "저 룰 사다리를 좀 고쳐야될 필요가 있어보이네"]
사다리의 통계 근거는 **코스피 자신의** 낙폭 뒤 forward 수익률이다(-38.6% → 12M 중앙 +43%·승률 97%).
그런데 사다리 집행 5건 300,909원은 **전부 GOOGL**(미국주, 달러 결제)이었다 — 코스피 반등 프리미엄을
받는 자산이 아니다. 즉 사다리가 실제로 하는 일 = **"코스피 낙폭이 미국주 매수 속도를 정한다"**.
원래 설계(crash_tf §6.5, 7/13)는 *"미장은 안전핀 무관 별도 트랙"*이었고, 7/30 개정 뒤 사다리가
유일한 매수 관문이 되면서 조용히 흡수됐다(8/14 d111이 '미국 소수점 전용 룰'로 문서화만 했다).
그 결과 9/21 현재 달러 $668.89가 코스피 회복(→누적 재잠금)과 해제 게이트(7,500·외인·**유가**)에 묶여 있다.

[가설 H] **미국주 매수를 코스피 사다리로 게이팅하는 것(G)보다, 코스피와 무관하게 분할 집행(P)하는 게 낫다.**
  G(현행)  : TF 활성(코스피 낙폭 ≤ -20%) 동안 달러 더미를 사다리 해금비율(D0 8%…D4 25%, RESET+누적
             d197)만큼만 매수 · S&P 폭풍 ≥70 하드플로어 · 해제(낙폭 > -17.7% = 7,500 프록시) 후
             잔여를 3개월 분할. ⚠️ 게이트②③(외인·유가)은 무시 = 해제가 실제보다 **빠르다 = G에 유리**.
             해금되는 즉시 전액 매수 = 현행 룰의 **최대 사용**(실제보다 G에 유리).
  P3 / P6  : t0부터 3 / 6개월 균등 분할(21거래일 간격) · 같은 하드플로어(폭풍 ≥70이면 그 회차 연기).
  L        : t0 일시 매수(참고) · C: 전액 현금(참고)

[절차 — 8/5 확립, 판정 기준은 **실행 전에 고정**]
  ① 집계      : TF 활성일 전부를 시작점으로 12M 뒤 가치 차(P3−G) 중앙값 > 0 — 현금 이자 0%·3% 둘 다
  ② 에피소드  : TF 활성 에피소드(연속 구간)별 평균 P3−G 부호 — **2/3 이상**이 P 우위여야 통과
  ③ 횡단면    : 게이팅 지수를 비미국 지수 19개로 바꿔 같은 검정 — **2/3 이상**에서 중앙값 P3−G > 0
  ②·③을 통과 못 하면 룰을 건드리지 않는다.
  보조(판정 아님): A) 코스피 낙폭 구간별 S&P forward 12M(정보가 있나) B) 하드플로어가 미국 매수에 도움이 되나

⚠️ 자산 = S&P500 **가격지수**(배당 제외, 연 ~1.5–2%p 과소) · 현금 0% 기본 → 둘이 대략 상쇄.
   현금 3% 변형으로 P에 불리하게 스트레스한다. 개별 종목(GOOGL 등)이 아니라 지수 프록시다.
⚠️ 겹치는 창(일별 시작점)이라 표본이 독립이 아니다 — ②가 그걸 보정하는 단계다.
⚠️ **측정 전용.** 룰을 바꾸지 않는다 — 채택은 정훈 승인.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import os
import statistics as st
import sys
from datetime import date as _d

_HERE = os.path.abspath(__file__)
ROOT = os.path.abspath(os.path.join(_HERE, *([os.pardir] * 5)))
HIST = os.path.join(ROOT, "data", "history")

LADDER = [(-20.0, 0.08), (-25.0, 0.15), (-35.0, 0.20), (-45.0, 0.25), (-55.0, 0.25)]  # tranche_rules.LADDER
TF_ON = -20.0          # TF 활성 = D0 문턱 도달
RELEASE = -17.7        # 해제 프록시 = 코스피 7,500 / 고점 ≈9,115 (게이트① 단독 — ②③ 무시 = G에 유리)
FLOOR = 70.0           # 하드플로어 = S&P 폭풍 %ile
WINDOW, LOOKBACK = 20, 252
MONTH = 21
ASSET = "^GSPC"
MIN_EP = 20            # d0_test --min-ep 기본값과 동일

# ③ 게이팅 후보 = 비미국 주가 지수만(9/9 d0_test 오염 교훈 — 종목·VIX·환율 금지)
GATES = ["^KS11", "^KQ11", "^N225", "^HSI", "^STOXX50E", "^TWII", "^BSESN", "^JKSE", "^BVSP",
         "^MXX", "XU100.IS", "^GSPTSE", "^AXJO", "^FTSE", "^GDAXI", "^KLSE", "^TA125.TA", "^MERV",
         "000001.SS"]


def load(sym: str) -> list[tuple[str, float]]:
    path = os.path.join(HIST, sym.replace("^", "_") + ".csv")
    rows = {}
    try:
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    c = float(r["close"])
                except (TypeError, ValueError):
                    continue
                if c > 0:
                    rows[r["date"][:10]] = c
    except OSError:
        return []
    return sorted(rows.items())


def drawdown(closes: list[float]) -> list[float]:
    out, peak = [], 0.0
    for c in closes:
        peak = max(peak, c)
        out.append((c / peak - 1) * 100)
    return out


def storm(closes: list[float]) -> list[float | None]:
    """vol_gauge와 같은 정의 — RV20(연율) 의 직전 252개 분포 내 백분위. 시점 i까지만 본다."""
    rets = [None] + [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    rv: list[float | None] = [None] * len(closes)
    for i in range(WINDOW, len(closes)):
        seg = rets[i - WINDOW + 1:i + 1]
        rv[i] = st.stdev(seg) * math.sqrt(252) * 100
    out: list[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        if rv[i] is None:
            continue
        hist = [x for x in rv[max(0, i - LOOKBACK + 1):i + 1] if x is not None]
        if len(hist) < 60:
            continue
        out[i] = sum(1 for x in hist if x <= rv[i]) / len(hist) * 100
    return out


def align(gate: list[tuple[str, float]], dates: list[str], max_gap: int = 7) -> list[float | None]:
    """게이팅 지수 낙폭을 자산 날짜에 ffill(그날 이전 마지막 봉, 7일 넘게 비면 None)."""
    gd = [d for d, _ in gate]
    dd = drawdown([c for _, c in gate])
    out = []
    for d in dates:
        j = bisect.bisect_right(gd, d) - 1
        if j < 0:
            out.append(None)
            continue
        gap = (_d.fromisoformat(d) - _d.fromisoformat(gd[j])).days
        out.append(dd[j] if gap <= max_gap else None)
    return out


def ep_ids(gate: list[tuple[str, float]], dates: list[str]) -> list[int | None]:
    """d0_test.drawdowns()와 같은 정의 — 게이팅 지수가 **신고가**를 낼 때마다 에피소드 id 증가.
    자산 날짜에 ffill."""
    gd, ids, peak, ep = [d for d, _ in gate], [], None, 0
    for _, c in gate:
        if peak is None or c >= peak:
            if peak is not None:
                ep += 1
            peak = c
        ids.append(ep)
    out = []
    for d in dates:
        j = bisect.bisect_right(gd, d) - 1
        out.append(ids[j] if j >= 0 else None)
    return out


def tf_active(gdd: list[float | None]) -> list[bool]:
    on, out = False, []
    for x in gdd:
        if x is None:
            on = False
        elif not on and x <= TF_ON:
            on = True
        elif on and x > RELEASE:
            on = False
        out.append(on)
    return out


def unlock(dd: float | None) -> float:
    return 0.0 if dd is None else sum(a for thr, a in LADDER if dd <= thr)


def _daily(r: float) -> float:
    return (1 + r) ** (1 / 252)


def sim_G(s, H, gdd, stm, px, r, floor=True):
    g = _daily(r)
    cash, units, spent = 1.0, 0.0, 0.0
    released, sched, per = False, [], 0.0
    for t in range(s, s + H + 1):
        halted = floor and stm[t] is not None and stm[t] >= FLOOR
        if not released:
            dd = gdd[t]
            if dd is None or dd > RELEASE:
                released = True
                per = cash / 3
                sched = [t + 1 + MONTH * k for k in range(3)]
            elif not halted:
                amt = min(cash, max(0.0, unlock(dd) - spent))   # 누적 상한 − 전체 기집행 (d197)
                if amt > 0:
                    units += amt / px[t]
                    cash -= amt
                    spent += amt
        if released:
            due = sum(1 for x in sched if x <= t)
            if due and not halted:
                amt = min(cash, per * due)
                units += amt / px[t]
                cash -= amt
                sched = [x for x in sched if x > t]
        if t < s + H:
            cash *= g
    return cash + units * px[s + H]


def sim_P(s, H, N, stm, px, r, floor=True):
    g = _daily(r)
    cash, units = 1.0, 0.0
    sched, per = [s + MONTH * k for k in range(N)], 1.0 / N
    for t in range(s, s + H + 1):
        halted = floor and stm[t] is not None and stm[t] >= FLOOR
        due = sum(1 for x in sched if x <= t)
        if due and not halted:
            amt = min(cash, per * due)
            units += amt / px[t]
            cash -= amt
            sched = [x for x in sched if x > t]
        if t < s + H:
            cash *= g
    return cash + units * px[s + H]


def episodes(dates, act, s_idx_ok):
    eps, cur = [], None
    for i, a in enumerate(act):
        if a and cur is None:
            cur = [i, i]
        elif a:
            cur[1] = i
        elif cur is not None:
            eps.append(tuple(cur))
            cur = None
    if cur is not None:
        eps.append(tuple(cur))
    return eps


def pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def run_gate(gate_sym, dates, px, stm, H, rates=(0.0, 0.03), detail=False, step=1):
    gate = load(gate_sym)
    if not gate:
        return None
    gdd = align(gate, dates)
    act = tf_active(gdd)
    eid = ep_ids(gate, dates)
    n = len(dates)
    starts = [i for i in range(n - H - 1) if act[i]][::step]
    if not starts:
        return {"gate": gate_sym, "n_starts": 0}
    res = {"gate": gate_sym, "n_starts": len(starts),
           "first": dates[starts[0]], "last": dates[starts[-1]], "by_rate": {}}
    for r in rates:
        d3, d6, dl, gc, p3nf = [], [], [], [], []
        per_start = {}
        for s in starts:
            G = sim_G(s, H, gdd, stm, px, r)
            P3 = sim_P(s, H, 3, stm, px, r)
            P6 = sim_P(s, H, 6, stm, px, r)
            L = px[s + H] / px[s]
            C = _daily(r) ** H
            d3.append((P3 - G) * 100)
            d6.append((P6 - G) * 100)
            dl.append((L - G) * 100)
            gc.append((G - C) * 100)
            if r == 0.0:
                p3nf.append((sim_P(s, H, 3, stm, px, r, floor=False) - P3) * 100)
            per_start[s] = (P3 - G) * 100
        eps = [e for e in episodes(dates, act, None) if any(e[0] <= s <= e[1] for s in starts)]
        ep_rows = []
        for a, b in eps:
            vals = [per_start[s] for s in starts if a <= s <= b]
            if not vals:
                continue
            mdd = min(x for x in gdd[a:b + 1] if x is not None)
            ep_rows.append({"from": dates[a], "to": dates[b], "n": len(vals),
                            "gate_min_dd": round(mdd, 1), "mean_p3_minus_g": round(st.mean(vals), 2)})
        pos = sum(1 for e in ep_rows if e["mean_p3_minus_g"] > 0)
        # 선례 정의(d0_test) — 신고가로 끝나는 낙폭 에피소드 · 표본 20 미만 제외 · 통과선 70%
        grp: dict = {}
        for st_i in starts:
            grp.setdefault(eid[st_i], []).append(st_i)
        dd_rows = []
        for k, idx in sorted(grp.items(), key=lambda kv: kv[1][0]):
            if len(idx) < MIN_EP:
                continue
            vals = [per_start[i] for i in idx]
            dd_rows.append({"from": dates[idx[0]], "to": dates[idx[-1]], "n": len(vals),
                            "gate_min_dd": round(min(gdd[i] for i in idx if gdd[i] is not None), 1),
                            "mean_p3_minus_g": round(st.mean(vals), 2),
                            "median_p3_minus_g": round(st.median(vals), 2)})
        dpos = sum(1 for e in dd_rows if e["mean_p3_minus_g"] > 0)
        res["by_rate"][f"{r:.2f}"] = {
            "p3_minus_g": {"median": round(st.median(d3), 2), "mean": round(st.mean(d3), 2),
                           "win": round(sum(1 for x in d3 if x > 0) / len(d3) * 100, 1),
                           "p5": round(pct(d3, 0.05), 2), "p95": round(pct(d3, 0.95), 2)},
            "p6_minus_g": {"median": round(st.median(d6), 2), "win": round(sum(1 for x in d6 if x > 0) / len(d6) * 100, 1),
                           "p5": round(pct(d6, 0.05), 2)},
            "lump_minus_g": {"median": round(st.median(dl), 2), "p5": round(pct(dl, 0.05), 2)},
            "g_minus_cash": {"median": round(st.median(gc), 2)},
            "episodes": {"n": len(ep_rows), "p_wins": pos, "rows": ep_rows if detail else None},
            "dd_episodes": {"n": len(dd_rows), "p_wins": dpos, "rows": dd_rows if detail else None},
            "floor_effect_p3": ({"median": round(st.median(p3nf), 2), "mean": round(st.mean(p3nf), 2)}
                                if p3nf else None),
        }
    return res


def info_lens(dates, px, stm, H):
    """보조 A — 코스피 낙폭 구간별 S&P forward H일 수익률(하드플로어 미발동일)."""
    gdd = align(load("^KS11"), dates)
    buckets = [("> -20%", -20.0, 999), ("-20~-25%", -25.0, -20.0), ("-25~-35%", -35.0, -25.0),
               ("-35~-45%", -45.0, -35.0), ("≤ -45%", -999, -45.0)]
    out = []
    for name, lo, hi in buckets:
        vals = [(px[i + H] / px[i] - 1) * 100 for i in range(len(dates) - H)
                if gdd[i] is not None and lo < gdd[i] <= hi and (stm[i] is None or stm[i] < FLOOR)]
        if hi == 999:
            vals = [(px[i + H] / px[i] - 1) * 100 for i in range(len(dates) - H)
                    if gdd[i] is not None and gdd[i] > -20 and (stm[i] is None or stm[i] < FLOOR)]
        out.append({"bucket": name, "n": len(vals),
                    "median": round(st.median(vals), 1) if vals else None,
                    "win": round(sum(1 for v in vals if v > 0) / len(vals) * 100, 1) if vals else None})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="사다리(코스피 낙폭)가 미국주 매수를 게이팅하는 게 맞는가 — 8/5 3단 검정")
    ap.add_argument("--horizon", type=int, default=252, help="평가 지평(거래일, 기본 252=12M)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gates", default=",".join(GATES), help="③ 게이팅 지수 목록(쉼표). 속도 때문에 ③은 5거래일 간격 시작점")
    a = ap.parse_args()

    asset = load(ASSET)
    dates = [d for d, _ in asset]
    px = [c for _, c in asset]
    stm = storm(px)
    H = a.horizon

    kospi = run_gate("^KS11", dates, px, stm, H, detail=True)
    cross = []
    for g in [x.strip() for x in a.gates.split(",") if x.strip()]:
        r = kospi if g == "^KS11" else run_gate(g, dates, px, stm, H, rates=(0.0,), step=5)
        if r and r.get("n_starts"):
            cross.append(r)
    info = info_lens(dates, px, stm, H)

    k0 = kospi["by_rate"]["0.00"]
    k3 = kospi["by_rate"]["0.03"]
    ep = k0["episodes"]
    pass1 = k0["p3_minus_g"]["median"] > 0 and k3["p3_minus_g"]["median"] > 0
    pass2 = ep["n"] > 0 and ep["p_wins"] / ep["n"] >= 2 / 3
    de = k0["dd_episodes"]
    pass2b = de["n"] > 0 and de["p_wins"] / de["n"] >= 0.70
    cpos = sum(1 for c in cross if c["by_rate"]["0.00"]["p3_minus_g"]["median"] > 0)
    pass3 = cross and cpos / len(cross) >= 2 / 3
    verdict = {"①집계": pass1, "②에피소드(사전등록·TF구간 2/3)": pass2,
               "②에피소드(선례 d0_test·신고가 구간 70%)": pass2b, "③횡단면": bool(pass3),
               "채택가능(두 ② 모두)": bool(pass1 and pass2 and pass2b and pass3),
               "채택가능(선례 ②)": bool(pass1 and pass2b and pass3)}
    out = {"horizon": H, "asset": ASSET, "kospi": kospi, "cross": cross, "info": info,
           "cross_pos": cpos, "cross_n": len(cross), "verdict": verdict}
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0

    print(f"=== 사다리가 미국주 매수를 게이팅하는 게 맞는가 — 지평 {H}거래일 · 자산 S&P500(USD) ===")
    print(f"게이팅=코스피 · TF 활성 시작일 {kospi['n_starts']}개 ({kospi['first']} ~ {kospi['last']})\n")
    print("① 집계 — 달러 1을 G(현행)로 굴렸을 때 대비 %p (양수 = 제안이 낫다)")
    for rk, lab in (("0.00", "현금 0%"), ("0.03", "현금 3%")):
        b = kospi["by_rate"][rk]
        print(f"  [{lab}] P3−G 중앙 {b['p3_minus_g']['median']:+.2f} · 평균 {b['p3_minus_g']['mean']:+.2f} · "
              f"승률 {b['p3_minus_g']['win']}% · 하위5% {b['p3_minus_g']['p5']:+.2f} · 상위5% {b['p3_minus_g']['p95']:+.2f}")
        print(f"           P6−G 중앙 {b['p6_minus_g']['median']:+.2f} · 승률 {b['p6_minus_g']['win']}% · 하위5% {b['p6_minus_g']['p5']:+.2f}"
              f" | 일시−G 중앙 {b['lump_minus_g']['median']:+.2f} · 하위5% {b['lump_minus_g']['p5']:+.2f}"
              f" | G−현금 중앙 {b['g_minus_cash']['median']:+.2f}")
    print(f"\n② 에피소드 — P 우위 {ep['p_wins']}/{ep['n']}")
    for e in ep["rows"] or []:
        print(f"  {e['from']} ~ {e['to']}  코스피 최저 {e['gate_min_dd']:>6}%  시작일 {e['n']:>4}  P3−G 평균 {e['mean_p3_minus_g']:+.2f}")
    print(f"\n②' 에피소드(선례 d0_test 정의 — 신고가로 끝나는 낙폭 구간 · 표본 {MIN_EP}+ · 통과선 70%) — P 우위 {de['p_wins']}/{de['n']}")
    for e in de["rows"] or []:
        print(f"  {e['from']} ~ {e['to']}  코스피 최저 {e['gate_min_dd']:>6}%  시작일 {e['n']:>4}  P3−G 평균 {e['mean_p3_minus_g']:+.2f} · 중앙 {e['median_p3_minus_g']:+.2f}")
    print(f"\n③ 횡단면 — 게이팅 지수를 바꿔도 P가 낫나: {cpos}/{len(cross)}")
    for c in cross:
        b = c["by_rate"]["0.00"]
        print(f"  {c['gate']:<10} 시작일 {c['n_starts']:>5}  P3−G 중앙 {b['p3_minus_g']['median']:+6.2f}  승률 {b['p3_minus_g']['win']:>5}%  "
              f"에피소드 {b['episodes']['p_wins']}/{b['episodes']['n']} · 선례 {b['dd_episodes']['p_wins']}/{b['dd_episodes']['n']}")
    print("\n보조 A — 코스피 낙폭 구간별 S&P forward 수익률(하드플로어 미발동일) — 코스피 낙폭이 미국 매수 타이밍 정보를 주나")
    for x in info:
        print(f"  {x['bucket']:<10} n={x['n']:>5}  중앙 {x['median']}%  승률 {x['win']}%")
    fe = k0.get("floor_effect_p3")
    if fe:
        print(f"\n보조 B — 하드플로어가 미국 분할매수에 준 효과(플로어 없음 − 있음): 중앙 {fe['median']:+.2f} · 평균 {fe['mean']:+.2f}%p")
    print(f"\n판정: ① {'✅' if pass1 else '❌'}  ②사전등록 {'✅' if pass2 else '❌'}  ②선례 {'✅' if pass2b else '❌'}  "
          f"③ {'✅' if pass3 else '❌'}")
    print("  ⚠️ ②는 정의가 둘이다 — 사전등록(TF 구간·2/3)은 이 스크립트를 쓸 때 정했고, 선례(신고가 구간·70%)는 d0_test가 "
          "9/9에 이미 쓴 정의다. 선례를 처음부터 따랐어야 했다. 두 결과를 모두 보고한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
