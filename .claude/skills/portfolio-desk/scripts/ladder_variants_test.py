#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ladder_variants_test.py — d205 트랙 분리 뒤 남은 두 질문 (stdlib·무네트워크)

[왜 — 2026-09-21 정훈 "국내 사다리도 한번 더 생각해보고, 미국은 사다리같은 판단을 만들 필요 없는지 생각해보고"]

(B) 국내 — 달러 일부를 **코스피 깊은 낙폭용 실탄**으로 남겨둬야 하나?
    d205 뒤 국내 트랙 재원은 원화 247,500원뿐이라 D4(누적 93%)까지 가도 23만원 = 삼성 1주 미만이다.
    사다리의 가장 강한 통계(-35% 이하 12M 중앙 +43%·승률 97%)를 실제로 쓰려면 달러를 남겨야 한다.
    그 대가 = 기다리는 동안 미국 분할매수(P3)를 못 한다.
      U    : 지금 S&P를 3회 분할(P3 — d205 미국 트랙)
      R12  : 코스피 낙폭 ≤ -35%(D2)가 오면 **그날 전액 코스피**, 12개월 안에 안 오면 그때부터 S&P P3
      R6   : 같은데 대기 6개월
    시작점 = 코스피 낙폭 -25 ~ -20%(지금 -23.1%)인 날.
    ★사전등록 판정: **1차 = R12 − U, 24M 지평.** ①중앙 > 0 ②에피소드(코스피 신고가로 끝나는 구간·표본 20+)
      70%+ ③게이팅 지수 19개(그 지수를 '국내'로 놓고) 70%+. 셋 다 통과해야 실탄 유보를 제안한다.

(C) 미국 — 미국 트랙에도 **S&P 자체 낙폭**에 반응하는 사다리가 필요한가?
      P3 : 3회 균등 분할(월 1회) — d205 현행
      SL : 순수 낙폭 사다리 — S&P 고점대비 -10 / -15 / -20% 첫 도달마다 1/3씩 (안 오면 현금)
      PA : P3 + 가속 — 분할 도중 S&P 낙폭 ≤ -10%면 남은 회차를 그날 전부
           (가속이 발동 안 한 시작점은 P3와 **똑같아 차이 0**이므로, PA는 **발동한 시작점만**으로 판정한다 — 실행 전 고정)
    시작점 = 모든 거래일(미국 트랙은 코스피 조건 없이 돈이 들어오면 시작한다).
    ★사전등록 판정: X − P3 ①12M 중앙 > 0(현금 0%·3% 둘 다) ②S&P 신고가 구간 에피소드(표본 20+) 70%+
      ③다른 지수 19개 + 나스닥(각자 자기 자산) 70%+. 셋 다 통과해야 미국 사다리를 제안한다.

    ★대조군(사후 추가 — 판정을 뒤집을 수 있어 결과와 함께 명시): PA 발동분의 대부분(89%)은 "시작일에 이미
      -10% 이하 = 그날 전부 매수"다. 그렇다면 PA의 이득이 **낙폭 정보**인지 **빨리 사면 드리프트만큼 이긴다**인지
      갈라야 한다 → 낙폭이 **없는** 시작점에서 "그날 전부 매수 − P3"를 같이 낸다. 이게 PA 이득 이상이면
      낙폭 조건은 정보가 없다(사전등록 ①②③ 통과는 필요조건이지 충분조건이 아니다).

공통: 하드플로어(S&P 폭풍 ≥70%ile, vol_gauge 정의)면 집행 **연기**(d205 미국 트랙과 동일).
⚠️ 가격지수(배당 제외) · 환율 무시(B: 코스피 위기 때 원화 약세 → 달러로 사면 유리 = **R에 불리한 쪽으로 보수적**).
⚠️ 겹치는 창이라 표본이 독립이 아니다 — ②가 그 보정. ⚠️ **측정 전용** — 룰을 바꾸지 않는다. 채택은 정훈 승인.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import us_track_test as U  # noqa: E402  (load·drawdown·storm·align·ep_ids·pct·GATES 재사용)

MONTH, N = U.MONTH, 3
FLOOR = U.FLOOR
PASS = 0.70                        # 선례(d0_test) 통과선
MIN_EP = U.MIN_EP
B_LO, B_HI, B_TRIG = -25.0, -20.0, -35.0
C_LEVELS = (-10.0, -15.0, -20.0)
C_ACCEL = -10.0
OTHER = ["^IXIC"] + U.GATES       # (C) ③ — 각자 자기 자산


# ───────────────────────────── 공통 전처리 (전부 O(n) 역방향 스캔 → 시작점당 O(1))
def next_true(flags):
    """nxt[t] = t 이후(포함) 처음 True인 인덱스, 없으면 len."""
    n = len(flags)
    out, j = [n] * (n + 1), n
    for t in range(n - 1, -1, -1):
        if flags[t]:
            j = t
        out[t] = j
    return out


def spend_value(execs, per, px, s, H, g):
    """execs = 회차별 집행 인덱스(없으면 None). 가치 = 매수분 평가 + 남은 현금(이자 포함)."""
    end = s + H
    v = g ** H
    for e in execs:
        if e is None or e > end:
            continue
        v += per / px[e] * px[end] - per * g ** (end - e)
    return v


def p3_execs(s, nok, H):
    return [nok[s + MONTH * k] if s + MONTH * k <= s + H else None for k in range(N)]


def summ(xs):
    if not xs:
        return None
    return {"n": len(xs), "med": round(st.median(xs), 2), "med_raw": st.median(xs), "mean": round(st.mean(xs), 2),
            "win": round(sum(1 for x in xs if x > 0) / len(xs) * 100, 1),
            "p5": round(U.pct(xs, 0.05), 2), "p95": round(U.pct(xs, 0.95), 2)}


def ep_pass(diffs_by_ep):
    """에피소드별 중앙 부호 — 표본 MIN_EP 이상만."""
    rows = [(k, len(v), st.median(v)) for k, v in diffs_by_ep.items() if len(v) >= MIN_EP]
    good = sum(1 for _, _, m in rows if m > 0)
    return good, len(rows), rows


# ───────────────────────────── (B) 국내 실탄 유보
def run_B(gate_sym, H, r=0.0, detail=False):
    sp = U.load(U.ASSET)
    gate = U.load(gate_sym)
    if not sp or not gate:
        return None
    dates = [d for d, _ in sp]
    px = [c for _, c in sp]
    stm = U.storm(px)
    gdd = U.align(gate, dates)
    # 게이트 가격을 자산 날짜에 ffill (align과 같은 7일 규칙)
    import bisect
    from datetime import date as _d
    gd = [d for d, _ in gate]
    gpx = []
    for d in dates:
        j = bisect.bisect_right(gd, d) - 1
        ok = j >= 0 and (_d.fromisoformat(d) - _d.fromisoformat(gd[j])).days <= 7
        gpx.append(gate[j][1] if ok else None)
    eps = U.ep_ids(gate, dates)
    halted = [x is not None and x >= FLOOR for x in stm]
    nok = next_true([not h for h in halted])
    trig_ok = next_true([(gdd[t] is not None and gdd[t] <= B_TRIG and not halted[t] and gpx[t] is not None)
                         for t in range(len(dates))])
    trig_any = next_true([(gdd[t] is not None and gdd[t] <= B_TRIG) for t in range(len(dates))])
    g = U._daily(r)
    out = {"R12": [], "R6": []}
    hit_d = {"R12": [], "R6": []}      # 조건부 — 실탄이 실제로 쓰인 경우만
    by_ep = {"R12": {}, "R6": {}}
    hit6 = hit12 = n = 0
    n_len = len(dates)
    for s in range(len(dates) - H - 1):
        x = gdd[s]
        if x is None or not (B_LO <= x <= B_HI) or gpx[s] is None:
            continue
        end = s + H
        if gpx[end] is None:
            continue
        n += 1
        uval = spend_value(p3_execs(s, nok, H), 1 / N, px, s, H, g)
        ta = trig_any[s]
        hit6 += ta <= s + 126
        hit12 += ta <= s + 252
        for name, W in (("R12", 252), ("R6", 126)):
            e = trig_ok[s]
            used = e < n_len and e <= s + W and e <= end
            if used:
                v = gpx[end] / gpx[e] * 1.0 + (g ** H - g ** (end - e))   # 전액 게이트 지수
            else:
                f = s + W                                                  # 대기 끝 → S&P P3
                ex = [nok[f + MONTH * k] if f + MONTH * k <= end else None for k in range(N)]
                v = spend_value(ex, 1 / N, px, s, H, g)
            d = (v - uval) * 100
            out[name].append(d)
            if used:
                hit_d[name].append(d)
            by_ep[name].setdefault(eps[s], []).append(d)
    if not n:
        return {"gate": gate_sym, "n": 0}
    res = {"gate": gate_sym, "n": n, "hit6": round(hit6 / n * 100, 1), "hit12": round(hit12 / n * 100, 1)}
    for name in ("R12", "R6"):
        res[name] = summ(out[name])
        res[name]["if_used"] = summ(hit_d[name])
        good, tot, rows = ep_pass(by_ep[name])
        res[name]["ep"] = [good, tot]
        if detail:
            res[name]["ep_rows"] = [(dates[0] if k is None else k, c, round(m, 2)) for k, c, m in rows]
    return res


# ───────────────────────────── (C) 미국 사다리
def run_C(sym, H, r=0.0, floor_sym=None, step=1, detail=False):
    """sym = 자산(자기 낙폭). floor = S&P 폭풍(sym이 S&P면 자기 폭풍)."""
    data = U.load(sym)
    if len(data) < 800:
        return None
    dates = [d for d, _ in data]
    px = [c for _, c in data]
    dd = U.drawdown(px)
    stm = U.storm(px)
    halted = [x is not None and x >= FLOOR for x in stm]
    nok = next_true([not h for h in halted])
    lev = {L: next_true([x <= L for x in dd]) for L in C_LEVELS}
    acc = next_true([(dd[t] <= C_ACCEL and not halted[t]) for t in range(len(dd))])
    eps = U.ep_ids(data, dates)
    g = U._daily(r)
    n_len = len(dates)
    out = {"SL": [], "PA": []}
    by_ep = {"SL": {}, "PA": {}}
    ctl_calm, ctl_dip = [], []          # 대조군: 일시 매수 − P3 (낙폭 없음 / PA 발동 시작점)
    for s in range(0, n_len - H - 1, step):
        end = s + H
        e3 = p3_execs(s, nok, H)
        base = spend_value(e3, 1 / N, px, s, H, g)
        lump = (spend_value([nok[s]] * N, 1 / N, px, s, H, g) - base) * 100
        # SL — 각 레벨 첫 도달 → 하드플로어면 연기
        esl = []
        for L in C_LEVELS:
            u = lev[L][s]
            esl.append(nok[u] if u < n_len else None)
        vsl = spend_value(esl, 1 / N, px, s, H, g)
        # PA — P3 도중 낙폭 ≤ -10%(플로어 아님)면 남은 회차 전부 그날
        a = acc[s]
        epa = [(min(e, a) if e is not None else (a if a <= end else None)) if a < n_len else e for e in e3]
        vpa = spend_value(epa, 1 / N, px, s, H, g)
        (ctl_calm if epa == e3 else ctl_dip).append(lump)
        for name, v in (("SL", vsl), ("PA", vpa)):
            if name == "PA" and epa == e3:
                continue                      # 가속 미발동 = P3와 동일 — 판정 표본에서 제외
            d = (v - base) * 100
            out[name].append(d)
            by_ep[name].setdefault(eps[s], []).append(d)
    res = {"asset": sym, "from": dates[0], "n": len(out["SL"]), "pa_trig": len(out["PA"]),
           "ctl_calm": summ(ctl_calm), "ctl_dip": summ(ctl_dip)}
    for name in ("SL", "PA"):
        res[name] = summ(out[name])
        good, tot, rows = ep_pass(by_ep[name])
        res[name]["ep"] = [good, tot]
    return res


def info_lens_C(H=252):
    """S&P 자기 낙폭 구간별 12M forward — 미국 낙폭이 미국 매수 타이밍 정보인가."""
    data = U.load(U.ASSET)
    px = [c for _, c in data]
    dd = U.drawdown(px)
    b = [(0, -5), (-5, -10), (-10, -15), (-15, -20), (-20, -100)]
    out = []
    for hi, lo in b:
        xs = [(px[t + H] / px[t] - 1) * 100 for t in range(len(px) - H) if lo < dd[t] <= hi]
        if xs:
            out.append({"bucket": f"{hi}~{lo}%", "n": len(xs), "med": round(st.median(xs), 1),
                        "win": round(sum(1 for x in xs if x > 0) / len(xs) * 100, 1)})
    return out


def fmt(x):
    return "—" if x is None else f"{x:+.2f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="d205 후속 — (B) 국내 실탄 유보 · (C) 미국 낙폭 사다리 검정")
    ap.add_argument("--part", choices=["B", "C", "all"], default="all")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--step", type=int, default=3, help="(C) ③ 횡단면 시작점 간격(기본 3거래일)")
    a = ap.parse_args()
    J = {}

    if a.part in ("B", "all"):
        B = {}
        for H in (252, 504):
            for r in (0.0, 0.03):
                B[f"{H}_{r}"] = run_B("^KS11", H, r, detail=True)
        cross = [run_B(gs, 504, 0.0) for gs in U.GATES if gs != "^KS11"]
        cross = [c for c in cross if c and c.get("n", 0) >= 100]
        J["B"] = {"kospi": B, "cross": cross}
        if not a.json:
            k = B["504_0.0"]
            print("\n══ (B) 국내 실탄 유보 — 코스피 -25~-20%에서 시작 · 기준 U = 지금 S&P 3회 분할 ══")
            print(f"  시작점 {k['n']}개 · 6개월 안 -35% 도달 {k['hit6']}% · 12개월 안 {k['hit12']}%")
            for H in (252, 504):
                for r in (0.0, 0.03):
                    b = B[f"{H}_{r}"]
                    for nm in ("R12", "R6"):
                        x = b[nm]
                        print(f"  {H//21:>2}M 현금{int(r*100)}% {nm:<4} − U : 중앙 {fmt(x['med'])} · 평균 {fmt(x['mean'])} · "
                              f"승률 {x['win']}% · 하위5% {fmt(x['p5'])} · 상위5% {fmt(x['p95'])} · 에피소드 {x['ep'][0]}/{x['ep'][1]}")
            for H in (252, 504):
                x = B[f"{H}_0.0"]["R12"]["if_used"]
                if x:
                    print(f"  조건부(실탄이 실제로 쓰인 {x['n']}개만) {H//21}M R12 − U : 중앙 {fmt(x['med'])} · 승률 {x['win']}% · 하위5% {fmt(x['p5'])}")
            print("  에피소드(R12·24M): " + " / ".join(f"#{e}:{c}개 {m:+.1f}" for e, c, m in k["R12"]["ep_rows"]))
            good = sum(1 for c in cross if c["R12"]["med_raw"] > 0)
            print(f"  ③ 횡단면(R12·24M): {good}/{len(cross)} 중앙>0")
            for c in cross:
                print(f"     {c['gate']:<10} n={c['n']:<5} 12M도달 {c['hit12']:>5}% · R12−U 중앙 {fmt(c['R12']['med'])} · 승률 {c['R12']['win']}%")
            k1 = k["R12"]
            p1 = k1["med"] > 0
            p2 = k1["ep"][1] > 0 and k1["ep"][0] / k1["ep"][1] >= PASS
            p3 = bool(cross) and good / len(cross) >= PASS
            print(f"  판정(1차 R12·24M): ①{'✅' if p1 else '❌'} ②{'✅' if p2 else '❌'} ③{'✅' if p3 else '❌'}"
                  f" → {'실탄 유보 제안' if p1 and p2 and p3 else '유보 기각 — 룰 변경 없음'}")

    if a.part in ("C", "all"):
        C = {}
        for H in (252, 504):
            for r in (0.0, 0.03):
                C[f"{H}_{r}"] = run_C(U.ASSET, H, r)
        cross = [run_C(sym, 252, 0.0, step=a.step) for sym in OTHER]
        cross = [c for c in cross if c]
        lens = info_lens_C()
        J["C"] = {"sp": C, "cross": cross, "lens": lens}
        if not a.json:
            s0 = C["252_0.0"]
            print(f"\n══ (C) 미국 낙폭 사다리 — S&P {s0['from']}~ 모든 거래일 시작 · 기준 = P3(d205) ══")
            print(f"  시작점 {s0['n']}개 · PA 가속 발동 {s0['pa_trig']}개({s0['pa_trig'] / s0['n'] * 100:.1f}%) — PA 줄은 발동분만")
            for H in (252, 504):
                for r in (0.0, 0.03):
                    c = C[f"{H}_{r}"]
                    for nm in ("SL", "PA"):
                        x = c[nm]
                        print(f"  {H//21:>2}M 현금{int(r*100)}% {nm} − P3 : 중앙 {fmt(x['med'])} · 평균 {fmt(x['mean'])} · "
                              f"승률 {x['win']}% · 하위5% {fmt(x['p5'])} · 상위5% {fmt(x['p95'])} · 에피소드 {x['ep'][0]}/{x['ep'][1]}")
            for nm in ("SL", "PA"):
                good = sum(1 for c in cross if c[nm]["med_raw"] > 0)
                print(f"  ③ 횡단면 {nm}: {good}/{len(cross)} 중앙>0 — " +
                      " ".join(f"{c['asset']}:{c[nm]['med_raw']:+.3f}" for c in cross))
            print("  보조 — S&P 자기 낙폭 구간별 12M forward: " +
                  " / ".join(f"{b['bucket']} n={b['n']} 중앙 {b['med']:+.1f}% 승률 {b['win']}%" for b in lens))
            cc, cd = s0["ctl_calm"], s0["ctl_dip"]
            print(f"  대조군(12M·현금0%) 일시 매수 − P3 : 낙폭 없는 시작점 중앙 {fmt(cc['med'])} · 승률 {cc['win']}% · 하위5% {fmt(cc['p5'])}"
                  f"  |  PA 발동 시작점 중앙 {fmt(cd['med'])} · 하위5% {fmt(cd['p5'])}")
            beat = sum(1 for c in cross if c["ctl_calm"] and c["ctl_calm"]["med_raw"] >= c["PA"]["med_raw"])
            print(f"  대조군 횡단면: 낙폭 없이 일시 매수한 이득 ≥ PA 이득인 시장 {beat}/{len(cross)}")
            for nm in ("SL", "PA"):
                x0, x3 = C["252_0.0"][nm], C["252_0.03"][nm]
                p1 = x0["med"] > 0 and x3["med"] > 0
                p2 = x0["ep"][1] > 0 and x0["ep"][0] / x0["ep"][1] >= PASS
                good = sum(1 for c in cross if c[nm]["med_raw"] > 0)
                p3 = bool(cross) and good / len(cross) >= PASS
                ok = p1 and p2 and p3
                if ok and nm == "PA":
                    drift = cc["med_raw"] >= x0["med_raw"]
                    verdict = ("사전등록 통과 — 그러나 대조군이 같거나 크다 = 이득의 정체는 낙폭 정보가 아니라 드리프트 → 제안 안 함"
                               if drift else "사전등록 통과 + 대조군보다 큼 → 미국 사다리 제안")
                else:
                    verdict = "미국 사다리 제안" if ok else "기각 — P3 유지"
                print(f"  판정 {nm}: ①{'✅' if p1 else '❌'} ②{'✅' if p2 else '❌'} ③{'✅' if p3 else '❌'} → {verdict}")

    if a.json:
        print(json.dumps(J, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
