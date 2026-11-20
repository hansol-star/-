#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sector_cap_test.py — 한 섹터(반도체) 상한 트림이 나아지나 (stdlib · Ken French 49산업 · 측정 전용)

[왜 — 2026-11-21 정훈 "검정해서 올려줘"]
11/21 실측 반도체(삼성·NVDA·AVGO·MU) = 주식의 39.6%, AI 관련 합계 약 71%. 정훈 제안 = "반도체 쪽 전부 줄이고
분산". 룰에는 종목 상한(18%)만 있고 섹터 상한이 없다. 질문: **섹터를 상한까지 팔아 시장(VOO)으로 옮기면
위험·수익이 나아지나?**

[왜 산업 포트폴리오인가]  nonai_slot_test.py와 같다 — 개별 종목은 '살아남은 걸 알고 고른' 편향이 들어간다.
Ken French 49산업(CRSP 전 종목 VW 총수익 1926~)은 그 편향이 없고 Chips가 반도체를 직접 대응한다.
산업마다 '테마'로 놓고 반복해 8/5 절차 ③을 채운다.

[모형 — 사전등록 2026-11-21 trials.jsonl `sector_cap`, 돌리기 전에 고정]
  시작 = 테마 40% · 시장 60% (11/21 실측 39.6%)
  매월 초 납입 = 시작 포트의 3% → 전부 시장 (d284 근사 — 신규 자금 VOO · 존 종목은 비반도체)
  H   (현행) : 보유 · 매도 없음
  T35 / T25 : 매월 초 테마 비중이 35% / 25%를 넘으면 초과분을 시장으로 리밸런싱(첫 달 즉시)
  T0  (전량) : 첫 달 테마 전량 → 시장 (= '그냥 VOO' 대조군)
  '추가 매수 금지'형 상한은 현행과 같아(신규 자금이 이미 시장으로 간다) 증분이 0 → 검정하지 않는다.
  지표: K = 12M 최대낙폭 차 %p (+면 정책이 얕다) · R = 12M 종가 자산 차 % · 보조 36M
  ① Chips 전 시작월 중앙값  ② 10년대별 2/3 이상 같은 방향  ③ 49산업 2/3 이상 + 단측 이항 → Holm(3 변형)
  채택 후보 = K가 ①②③ + Holm p<0.05, 그리고 R이 유의하게 음수가 아닐 것
  층(기술만) = 테마 직전 4M 초과수익 ≤ -15%p (지금 상태)
  견고성 = ^SOX vs ^GSPC 1994~ 가격지수 월말(배당 없음 · 판정 아님)

⚠️ 산업 포트폴리오는 개별 4종목보다 덜 출렁인다 → 트림의 낙폭 완화 효과를 **과소평가**하는 쪽이다.
⚠️ 월말 해상도 · 세금·수수료 없음(실제 트림은 손실 실현 · 왕복 비용이 든다).
⚠️ 시장 안에도 테마가 들어 있다(2026-09 Chips = 시장의 22%) — 실효 노출은 따로 보고한다.
⚠️ **측정 전용.** 섹터 상한은 룰 변경이다 — 정훈 승인.

  python sector_cap_test.py            # 사전등록 검정 전체
  python sector_cap_test.py --save     # + data/research/sector_cap_test.json
  python sector_cap_test.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nonai_slot_test as base  # noqa: E402  (데이터 로더·이항·10년대 분할 재사용)

ROOT = base.ROOT
OUT = os.path.join(ROOT, "data", "research", "sector_cap_test.json")
INIT_T = 0.40
C = 0.03
POLICIES = {"H": None, "T35": 0.35, "T25": 0.25, "T0": 0.0}
ALTS = ["T35", "T25", "T0"]
THEME = "Chips"


def simulate(series, start: int, H: int, cap, c: float = C, init_t: float = INIT_T):
    """→ (종가 자산, MDD %, 끝 실효 테마 노출 %)"""
    t, m = init_t, 1.0 - init_t
    idx, peak, mdd, wt_last = 1.0, 1.0, 0.0, 0.0
    for k in range(H):
        rt, rm, _rx, wt = series[start + k]
        m += c
        if cap is not None and t / (t + m) > cap:
            v = t + m
            t, m = v * cap, v * (1 - cap)
        v0 = t + m
        t, m = t * (1 + rt), m * (1 + rm)
        pr = (t + m) / v0 - 1
        idx *= 1 + pr
        peak = max(peak, idx)
        mdd = min(mdd, idx / peak - 1)
        wt_last = wt
    V = t + m
    return V, mdd * 100, (t + m * wt_last) / V * 100


def runs(series, months, H: int):
    rows = []
    for s in range(len(series) - H + 1):
        if any(x is None for x in series[s:s + H]):
            continue
        res = {p: simulate(series, s, H, cap) for p, cap in POLICIES.items()}
        p4 = None
        if s >= 4 and all(series[q] is not None for q in range(s - 4, s)):
            a = b = 1.0
            for q in range(s - 4, s):
                a *= 1 + series[q][0]
                b *= 1 + series[q][1]
            p4 = (a - b) * 100
        rows.append({"m": months[s], "res": res, "p4": p4})
    return rows


def diffs(rows, a: str, b: str = "H"):
    K = [r["res"][a][1] - r["res"][b][1] for r in rows]
    R = [(r["res"][a][0] / r["res"][b][0] - 1) * 100 for r in rows]
    return K, R


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, ps[i] * (len(ps) - rank)))
        out[i] = run
    return out


def evaluate(D, H: int):
    names = D["names"]
    per = {t: runs(base.market_and_ex(D, names.index(t)), D["months"], H) for t in names}
    out = {"H": H, "theme": THEME, "variants": {}}
    for a in ALTS:
        rows = per[THEME]
        K, R = diffs(rows, a)
        decK = base.episode_split(rows, K)
        decR = base.episode_split(rows, R)
        kposK = sum(1 for v in decK.values() if v > 0)
        cross = {}
        for t, rr in per.items():
            if len(rr) < 120:
                continue
            k_, r_ = diffs(rr, a)
            cross[t] = (base.med(k_), base.med(r_))
        n = len(cross)
        kK = sum(1 for v in cross.values() if v[0] > 0)
        kRneg = sum(1 for v in cross.values() if v[1] < 0)
        now = [(k, r) for row, k, r in zip(rows, K, R) if row["p4"] is not None and row["p4"] <= -15]
        eff = [(row["res"][a][2], row["res"]["H"][2]) for row in rows]
        out["variants"][a] = {
            "K_med": base.med(K), "K_pos_share": sum(1 for v in K if v > 0) / len(K) * 100,
            "R_med": base.med(R), "R_p10": sorted(R)[len(R) // 10], "R_neg_share": sum(1 for v in R if v < 0) / len(R) * 100,
            "dec_K": decK, "dec_R": decR, "dec_K_pos": kposK, "dec_n": len(decK),
            "cross_n": n, "cross_K_pos": kK, "cross_K_p": base.sign_p(kK, n),
            "cross_R_neg": kRneg, "cross_R_neg_p": base.sign_p(kRneg, n),
            "chips_cross": cross.get(THEME),
            "now_n": len(now), "now_K_med": base.med([x[0] for x in now]), "now_R_med": base.med([x[1] for x in now]),
            "eff_end_med": base.med([e[0] for e in eff]), "eff_end_H_med": base.med([e[1] for e in eff]),
            "start_months": len(rows),
        }
    ps = [out["variants"][a]["cross_K_p"] for a in ALTS]
    for a, hp in zip(ALTS, holm(ps)):
        out["variants"][a]["cross_K_holm"] = hp
    pr = [out["variants"][a]["cross_R_neg_p"] for a in ALTS]
    for a, hp in zip(ALTS, holm(pr)):
        out["variants"][a]["cross_R_neg_holm"] = hp
    return out, per


def worst_cases(per, k=5):
    """Chips 시작월 중 H의 12M MDD가 가장 깊었던 창 — 정책별 비교(기술만)."""
    rows = sorted(per[THEME], key=lambda r: r["res"]["H"][1])[:k]
    return [{"m": r["m"], **{p: [round(r["res"][p][0], 3), round(r["res"][p][1], 1)] for p in POLICIES}} for r in rows]


def sox_robust(H: int = 12):
    def monthly(sym):
        path = os.path.join(ROOT, "data", "history", sym + ".csv")
        last = {}
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                last[row["date"][:7]] = float(row["close"])
        return last
    s, g = monthly("_SOX"), monthly("_GSPC")
    ms = sorted(set(s) & set(g))
    ser, months = [], []
    for a, b in zip(ms, ms[1:]):
        ser.append((s[b] / s[a] - 1, g[b] / g[a] - 1, 0.0, 0.10))
        months.append(int(b.replace("-", "")))
    rows = runs(ser, months, H)
    out = {}
    for a in ALTS:
        K, R = diffs(rows, a)
        out[a] = {"K_med": base.med(K), "K_pos_share": sum(1 for v in K if v > 0) / len(K) * 100,
                  "R_med": base.med(R), "R_neg_share": sum(1 for v in R if v < 0) / len(R) * 100, "n": len(rows)}
    return out


def report(res, label):
    print(f"\n━━━ {label} · 지평 {res['H']}M · 테마 {res['theme']} · 시작 테마 40% · 월 납입 3% → 시장 ━━━")
    print("  변형  K중앙(%p) K>0비율  R중앙(%)  R하위10%  ②10년대K+  ③49산업K+  p      Holm   ③R<0   Holm   지금상태(n) K/R")
    for a, v in res["variants"].items():
        print(f"  {a:<4} {v['K_med']:+8.2f}  {v['K_pos_share']:5.1f}%  {v['R_med']:+7.2f}  {v['R_p10']:+8.2f}  "
              f"{v['dec_K_pos']:>3}/{v['dec_n']:<3}    {v['cross_K_pos']:>3}/{v['cross_n']:<3} {v['cross_K_p']:.4f} {v['cross_K_holm']:.4f}  "
              f"{v['cross_R_neg']:>3}/{v['cross_n']:<3} {v['cross_R_neg_holm']:.4f}  ({v['now_n']}) {v['now_K_med']:+.2f}/{v['now_R_med']:+.2f}")
    v = res["variants"]["T35"]
    print(f"  끝 실효 테마 노출 중앙: H {v['eff_end_H_med']:.1f}% · T35 {v['eff_end_med']:.1f}% · "
          f"T25 {res['variants']['T25']['eff_end_med']:.1f}% · T0 {res['variants']['T0']['eff_end_med']:.1f}%")


def verdict(res):
    out = {}
    for a, v in res["variants"].items():
        k_ok = v["K_med"] > 0 and v["dec_K_pos"] >= math.ceil(v["dec_n"] * 2 / 3) and \
            v["cross_K_pos"] >= math.ceil(v["cross_n"] * 2 / 3) and v["cross_K_holm"] < 0.05
        r_bad = v["cross_R_neg_holm"] < 0.05
        out[a] = "채택 후보" if (k_ok and not r_bad) else ("K 통과·R 유의 손해" if k_ok else "기각")
    return out


def selftest() -> int:
    ok = True
    flat = [(0.0, 0.0, 0.0, 0.1)] * 12
    for cap in POLICIES.values():
        V, mdd, _ = simulate(flat, 0, 12, cap)
        ok &= abs(V - 1.36) < 1e-9 and mdd == 0
    crash = [(-0.5, 0.0, 0.0, 0.1)] + [(0.0, 0.0, 0.0, 0.1)] * 11
    h = simulate(crash, 0, 12, None)
    t0 = simulate(crash, 0, 12, 0.0)
    t35 = simulate(crash, 0, 12, 0.35)
    ok &= t0[1] == 0 and h[1] < t35[1] < 0     # 전량 매도는 낙폭 0, 35% 트림은 그 사이
    ok &= abs(holm([0.01, 0.04, 0.03])[0] - 0.03) < 1e-12
    print("selftest", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    D = base.load_industries(49)
    out = {}
    for H in (12, 36):
        res, per = evaluate(D, H)
        report(res, "주 검정" if H == 12 else "보조")
        out[f"H{H}"] = res
        if H == 12:
            out["verdict_12"] = verdict(res)
            out["worst_chips_12"] = worst_cases(per)
            print("  판정:", out["verdict_12"])
            print("  Chips 최악 창(H 기준) [자산, MDD]:")
            for w in out["worst_chips_12"]:
                print("   ", w)
    out["sox_robust_12"] = sox_robust(12)
    print("\n━━━ 견고성 ^SOX vs ^GSPC (가격지수 · 1994~ · 12M) ━━━")
    for k, v in out["sox_robust_12"].items():
        print(f"  {k:<4} K중앙 {v['K_med']:+.2f}%p (K>0 {v['K_pos_share']:.0f}%) · R중앙 {v['R_med']:+.2f}% (R<0 {v['R_neg_share']:.0f}%) · n {v['n']}")
    if a.save:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1, default=str)
        print("saved", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
