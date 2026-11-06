#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nonai_slot_test.py — 미국 매수 순서에 '비AI 칸'을 넣으면 나아지나 (stdlib · 데이터 = Ken French 산업 포트폴리오)

[왜 — 2026-11-07 시스템 점검 → 정훈 "테스트 돌려"]
11/7 점검에서 대가 13F 클론을 비교하니 6/30 이후 돈을 번 셋(애크먼·버핏·드러켄밀러)은 AI 설비투자 사슬
밖(결제·신평·에너지·필수소비·헬스케어)에 절반 넘게 있었고, 우리와 가장 닮은 테퍼가 꼴찌였다. 우리 미국
슬리브는 AI 개별주 71%·VOO 29%(11/6 실측)이고, 미국 트랙 매수 순서(GEV·ANET·CDNS → GOOGL 18% →
VOO)는 VOO를 빼면 전부 AI다. 질문: **신규 자금 순서에 비AI 칸을 넣으면 위험·수익이 나아지나?**

[왜 개별 종목이 아니라 산업 포트폴리오인가]
GEV·ANET·NVDA로 과거를 돌리면 '이긴 걸 알고 고른 종목'으로 채점하는 생존·사후선택 편향이 그대로 들어간다.
Ken French 산업 포트폴리오(CRSP 전 종목·VW 총수익·1926~)는 그 편향이 없고, **산업마다 '테마'로 놓고
같은 검정을 반복**할 수 있어 8/5 절차 ③(횡단면)을 시장 대신 테마로 채운다(BusEq = 컴퓨터·소프트웨어·
전자 = AI·테크 대응).

[모형 — 사전등록 2026-11-07 trials.jsonl `nonai_slot`, 돌리기 전에 고정]
  시작 슬리브 = 테마 71% · 시장 29%(11/6 실측) · 비테마 0
  매월 초 납입 = 시작 슬리브의 c(기본 3% · 민감도 1·6%) — 정책별로 칸에 나눠 넣고 그 달 수익률 적용
  C   (현행)   : 테마 43% · 시장 57%  ← d205 첫 사이클 실현 비율(GOOGL+ANET $255 / VOO $335)
  V   (VOO 먼저): 시장 100%            ← 대조군 = '전용 칸 없이 그냥 시장'
  N33 (비AI 칸) : 현행 × 2/3 + 비테마 1/3
  NX  (비AI 먼저): 비테마 100%
  시장 = 12산업 VW 합성(가중 = 월초 시가총액 = 평균 규모 × 기업 수 — F-F Mkt와 대조로 검증)
  비테마 = 시장에서 테마를 뺀 나머지(VW)
  지표: K = 12M 최대낙폭(TWR 월말 지수) 차 %p (+면 정책이 더 얕다) · R = 12M 종가 자산 차 % · 보조 36M
  ① BusEq 전 시작월 중앙값  ② 10년대별 2/3 이상 같은 방향  ③ 12산업 2/3 이상 + 단측 이항
  대조군 = NX vs V  ·  채택 후보 = K가 ①②③ + Holm p<0.05, 그리고 R이 유의하게 음수가 아닐 것
  층(기술만) = 테마 직전 36M 초과수익 상위 1/3 · 직전 4M 초과수익 ≤ -15%p(11/7 지금 상태)

⚠️ 산업 포트폴리오는 개별 7종목보다 덜 출렁인다 → 분산 효과를 **과소평가**하는 쪽이다.
⚠️ 월말 해상도라 장중·월중 낙폭은 안 잡힌다. 세금·수수료·환율 없음(미국 슬리브 안 달러 기준).
⚠️ 겹치는 창(매월 시작)이라 시작월끼리 독립이 아니다 — ②가 그 보정 단계다.
⚠️ **측정 전용.** 매수 순서는 룰(d205·d191)이다 — 바꾸는 건 정훈 승인.

  python nonai_slot_test.py                 # 사전등록 검정 전체
  python nonai_slot_test.py --save          # + data/research/nonai_slot_test.json
  python nonai_slot_test.py --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics as st
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *([os.pardir] * 4)))
FF = os.path.join(ROOT, "data", "cache", "famafrench")
OUT = os.path.join(ROOT, "data", "research", "nonai_slot_test.json")
URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"

INIT = (0.71, 0.29, 0.0)          # (테마, 시장, 비테마) — 11/6 미국 슬리브 실측
CUR = (0.43, 0.57, 0.0)           # d205 첫 사이클 실현 비율
POLICIES = {
    "C": CUR,
    "V": (0.0, 1.0, 0.0),
    "N33": (CUR[0] * 2 / 3, CUR[1] * 2 / 3, 1 / 3),
    "NX": (0.0, 0.0, 1.0),
}
ALTS = ["V", "N33", "NX"]
THEME = "BusEq"


# ───────────────────────── 데이터 ─────────────────────────
def fetch(names=("12_Industry_Portfolios", "49_Industry_Portfolios", "F-F_Research_Data_Factors")) -> None:
    import io
    import urllib.request
    import zipfile
    os.makedirs(FF, exist_ok=True)
    for n in names:
        req = urllib.request.Request(URL + n + "_CSV.zip", headers={"User-Agent": "portfolio-desk research"})
        z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(req, timeout=60).read()))
        for m in z.namelist():
            with open(os.path.join(FF, m), "wb") as f:
                f.write(z.read(m))


def _sections(path: str) -> dict:
    """제목 줄 → (헤더, {yyyymm: [값…]}) — 월별 6자리 행만."""
    out, cur, hdr = {}, None, None
    with open(path, encoding="latin-1") as f:
        for line in f:
            s = line.rstrip("\n")
            if not s.strip():
                continue
            if not s.startswith(",") and not s.strip()[:1].isdigit():
                cur, hdr = s.strip(), None
                continue
            if s.startswith(","):
                hdr = [h.strip() for h in s.split(",")[1:]]
                out.setdefault(cur, (hdr, {}))
                continue
            parts = [p.strip() for p in s.split(",")]
            if cur and hdr and len(parts[0]) == 6:
                out[cur][1][int(parts[0])] = [float(x) for x in parts[1:]]
    return out


def load_industries(n: int = 12) -> dict:
    path = os.path.join(FF, f"{n}_Industry_Portfolios.csv")
    if not os.path.exists(path):
        fetch()
    sec = _sections(path)
    hdr, vw = sec["Average Value Weighted Returns -- Monthly"]
    _, nf = sec["Number of Firms in Portfolios"]
    _, sz = sec["Average Firm Size"]
    months = sorted(vw)
    R, W = [], []
    for m in months:
        r = [None if x <= -99 else x / 100 for x in vw[m]]
        cap = [(a * b if (a > 0 and b > 0) else 0.0) for a, b in zip(nf[m], sz[m])]
        R.append(r)
        W.append(cap)
    return {"names": hdr, "months": months, "R": R, "CAP": W}


def load_mkt() -> dict:
    path = os.path.join(FF, "F-F_Research_Data_Factors.csv")
    if not os.path.exists(path):
        fetch()
    sec = _sections(path)
    key = next(k for k in sec if "Annual" not in k)
    hdr, rows = sec[key]
    i, j = hdr.index("Mkt-RF"), hdr.index("RF")
    return {m: (v[i] + v[j]) / 100 for m, v in rows.items()}


def market_and_ex(D: dict, theme: int):
    """월별 (테마 r, 시장 r, 비테마 r, 테마 시총비중) — 결측 산업은 그 달 가중에서 뺀다."""
    out = []
    for r, cap in zip(D["R"], D["CAP"]):
        tot = sum(c for c, x in zip(cap, r) if x is not None and c > 0)
        if r[theme] is None or cap[theme] <= 0 or tot <= 0:
            out.append(None)
            continue
        rm = sum(c * x for c, x in zip(cap, r) if x is not None and c > 0) / tot
        wt = cap[theme] / tot
        rx = (rm - wt * r[theme]) / (1 - wt) if wt < 1 else rm
        out.append((r[theme], rm, rx, wt))
    return out


# ───────────────────────── 시뮬레이션 ─────────────────────────
def simulate(series, start: int, H: int, pol, c: float, init=INIT):
    """series[start:start+H] 월별 (rt, rm, rx, wt). → (종가 자산, MDD %, 월 변동성 %, 끝 테마 실효비중 %)"""
    h = list(init)
    idx, peak, mdd, rets = 1.0, 1.0, 0.0, []
    wt_last = None
    for k in range(H):
        rt, rm, rx, wt = series[start + k]
        h = [h[0] + c * pol[0], h[1] + c * pol[1], h[2] + c * pol[2]]
        v0 = sum(h)
        h = [h[0] * (1 + rt), h[1] * (1 + rm), h[2] * (1 + rx)]
        pr = sum(h) / v0 - 1
        rets.append(pr)
        idx *= 1 + pr
        peak = max(peak, idx)
        mdd = min(mdd, idx / peak - 1)
        wt_last = wt
    V = sum(h)
    vol = st.pstdev(rets) * math.sqrt(12) * 100 if len(rets) > 1 else 0.0
    eff = (h[0] + h[1] * (wt_last or 0)) / V * 100   # 시장 안의 테마분까지 포함한 실효 테마 노출
    return V, mdd * 100, vol, eff


def runs(series, months, H: int, c: float):
    """시작월마다 정책 4개 결과 → 행 리스트."""
    rows = []
    for s in range(len(series) - H + 1):
        win = series[s:s + H]
        if any(x is None for x in win):
            continue
        res = {p: simulate(series, s, H, POLICIES[p], c) for p in POLICIES}
        # 층: 직전 36M · 4M 테마 초과수익(누적, %p)
        def prior(n):
            if s - n < 0 or any(series[q] is None for q in range(s - n, s)):
                return None
            a = b = 1.0
            for q in range(s - n, s):
                a *= 1 + series[q][0]
                b *= 1 + series[q][1]
            return (a - b) * 100
        rows.append({"m": months[s], "res": res, "p36": prior(36), "p4": prior(4)})
    return rows


def diffs(rows, a: str, b: str = "C"):
    """K = MDD_a − MDD_b (%p, +면 a가 얕다) · R = W_a/W_b − 1 (%) · Vo = 변동성 차(%p, −면 a가 낮다)"""
    K = [r["res"][a][1] - r["res"][b][1] for r in rows]
    R = [(r["res"][a][0] / r["res"][b][0] - 1) * 100 for r in rows]
    Vo = [r["res"][a][2] - r["res"][b][2] for r in rows]
    return K, R, Vo


def sign_p(k: int, n: int) -> float:
    """단측 이항 P(X ≥ k | n, ½)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0


def med(xs):
    return st.median(xs) if xs else float("nan")


# ───────────────────────── 검정 ─────────────────────────
def episode_split(rows, vals):
    """② 10년대별(시작월 기준) 중앙값 — 시작월 24개 미만 10년대는 뺀다."""
    by = {}
    for r, v in zip(rows, vals):
        by.setdefault((r["m"] // 100) // 10 * 10, []).append(v)
    return {d: med(v) for d, v in sorted(by.items()) if len(v) >= 24}


def full(D, H: int, c: float, theme_names=None):
    names = D["names"]
    themes = theme_names or names
    per = {}
    for t in themes:
        ti = names.index(t)
        ser = market_and_ex(D, ti)
        per[t] = runs(ser, D["months"], H, c)
    return per


def report(per, H: int, c: float, label: str, out: dict, primary: bool) -> None:
    print(f"\n━━━ {label} · 지평 {H}M · 월 납입 {c*100:.0f}% ━━━")
    res = {}
    rows = per.get(THEME)
    if rows:
        print(f"① {THEME}(=AI·테크) 시작월 {len(rows)}개 ({rows[0]['m']}~{rows[-1]['m']}) — 정책 − 현행C")
        print(f"   {'정책':5} {'K MDD차 중앙':>12} {'K>0 비율':>9} {'R 자산차 중앙':>13} {'R>0 비율':>9} {'변동성차':>8}")
        for a in ALTS:
            K, R, Vo = diffs(rows, a)
            print(f"   {a:5} {med(K):+11.2f}p {sum(k > 0 for k in K)/len(K)*100:8.0f}% {med(R):+12.2f}% "
                  f"{sum(x > 0 for x in R)/len(R)*100:8.0f}% {med(Vo):+7.2f}p")
            res[f"{THEME}_{a}"] = {"K_med": med(K), "K_pos": sum(k > 0 for k in K) / len(K),
                                   "R_med": med(R), "R_pos": sum(x > 0 for x in R) / len(R), "Vo_med": med(Vo)}
        K, R, _ = diffs(rows, "NX", "V")
        print(f"   대조 NX−V: K {med(K):+.2f}p (>0 {sum(k > 0 for k in K)/len(K)*100:.0f}%) · R {med(R):+.2f}% "
              f"(>0 {sum(x > 0 for x in R)/len(R)*100:.0f}%)")
        res[f"{THEME}_NX_vs_V"] = {"K_med": med(K), "R_med": med(R)}
        # ②
        print(f"② {THEME} 10년대별 중앙값 (K %p / R %)")
        for a in ALTS:
            K, R, _ = diffs(rows, a)
            ek, er = episode_split(rows, K), episode_split(rows, R)
            kp = sum(v > 0 for v in ek.values())
            rn = sum(v < 0 for v in er.values())
            cells = " ".join(f"{d}s {ek[d]:+.1f}/{er[d]:+.1f}" for d in ek)
            print(f"   {a:4} K>0 {kp}/{len(ek)} · R<0 {rn}/{len(er)} | {cells}")
            res[f"{THEME}_{a}_decades"] = {"K_pos": kp, "R_neg": rn, "n": len(ek),
                                           "K": ek, "R": er}
    # ③
    print(f"③ 테마 {len(per)}개 횡단면 — 테마별 중앙값의 부호")
    for a in ALTS + ["NX_vs_V"]:
        ka = kr_neg = n = 0
        cells = []
        for t, rws in per.items():
            if len(rws) < 60:
                continue
            K, R, _ = diffs(rws, "NX", "V") if a == "NX_vs_V" else diffs(rws, a)
            n += 1
            ka += med(K) > 0
            kr_neg += med(R) < 0
            cells.append(f"{t.strip()} {med(K):+.1f}/{med(R):+.1f}")
        pk, pr = sign_p(ka, n), sign_p(kr_neg, n)
        print(f"   {a:8} K>0 {ka}/{n} (p {pk:.4f}) · R<0 {kr_neg}/{n} (p {pr:.4f})")
        if primary:
            print("            " + " · ".join(cells))
        res[f"xs_{a}"] = {"K_pos": ka, "R_neg": kr_neg, "n": n, "pK": pk, "pR_neg": pr}
    out[label] = res


def strata(per, H: int, c: float, out: dict) -> None:
    print(f"\n━━━ 층(기술만 · 판정 아님) · {H}M · 납입 {c*100:.0f}% · 정책 NX − 현행C ━━━")
    res = {}
    for t, rows in per.items():
        hi = [r for r in rows if r["p36"] is not None]
        if len(hi) < 60:
            continue
        cut = sorted(r["p36"] for r in hi)[int(len(hi) * 2 / 3)]
        top = [r for r in hi if r["p36"] >= cut]
        crash = [r for r in rows if r["p4"] is not None and r["p4"] <= -15]
        boom_crash = [r for r in top if r["p4"] is not None and r["p4"] <= -15]
        line = []
        for nm, sub in (("전체", rows), ("붐 후(36M 상위⅓)", top), ("직전4M ≤-15p", crash), ("붐+급락", boom_crash)):
            if len(sub) < 6:
                line.append(f"{nm} n={len(sub)}")
                continue
            K, R, _ = diffs(sub, "NX")
            line.append(f"{nm} n={len(sub)} K{med(K):+.1f}/R{med(R):+.1f}")
            res[f"{t}|{nm}"] = {"n": len(sub), "K": med(K), "R": med(R)}
        print(f"   {t.strip():6} " + " · ".join(line))
    out["strata"] = res


def cases(D, out: dict) -> None:
    print("\n━━━ 사례(BusEq · 12M · 납입 3%) — MDD %(정책별) / 종가 자산 ━━━")
    ti = D["names"].index(THEME)
    ser = market_and_ex(D, ti)
    res = {}
    for m in (192909, 197301, 199912, 200003, 200710, 202112, 202501):
        if m not in D["months"]:
            continue
        s = D["months"].index(m)
        if s + 12 > len(ser) or any(x is None for x in ser[s:s + 12]):
            continue
        r = {p: simulate(ser, s, 12, POLICIES[p], 0.03) for p in POLICIES}
        print(f"   {m}: " + " · ".join(f"{p} MDD {r[p][1]:+.1f}% 자산 {r[p][0]:.3f}" for p in POLICIES))
        res[m] = {p: {"mdd": r[p][1], "W": r[p][0], "eff_theme": r[p][3]} for p in POLICIES}
    # 2026-07~ (데이터 끝까지) — 지금 국면
    s = D["months"].index(202607) if 202607 in D["months"] else None
    if s is not None:
        H = len(ser) - s
        r = {p: simulate(ser, s, H, POLICIES[p], 0.03) for p in POLICIES}
        print(f"   202607~{D['months'][-1]}({H}M): " + " · ".join(f"{p} MDD {r[p][1]:+.1f}% 자산 {r[p][0]:.3f}" for p in POLICIES))
        res["2026-07~"] = {p: {"mdd": r[p][1], "W": r[p][0]} for p in POLICIES}
    out["cases"] = res


def mkt_check(D) -> dict:
    """합성 시장(월초 시총 가중) vs F-F Mkt — 가중 시점이 맞는지(룩어헤드 아님)."""
    mk = load_mkt()
    a, b, a2 = [], [], []
    for i, (m, r, cap) in enumerate(zip(D["months"], D["R"], D["CAP"])):
        if m not in mk or any(x is None for x in r):
            continue
        tot = sum(cap)
        a.append(sum(c * x for c, x in zip(cap, r)) / tot)
        b.append(mk[m])
        if i + 1 < len(D["CAP"]):          # 다음 달 시총(= 이번 달 말) 가중 = 룩어헤드 대조
            c2 = D["CAP"][i + 1]
            a2.append(sum(c * x for c, x in zip(c2, r)) / sum(c2))
    te = st.pstdev([x - y for x, y in zip(a, b)]) * 100
    te2 = st.pstdev([x - y for x, y in zip(a2, b[:len(a2)])]) * 100
    return {"n": len(a), "te_pct": te, "te_endmonth_pct": te2}


def selftest() -> int:
    ok = True
    # 1) 무수익이면 종가 자산 = 1 + c·H, MDD 0
    ser = [(0.0, 0.0, 0.0, 0.2)] * 12
    V, mdd, vol, _ = simulate(ser, 0, 12, POLICIES["NX"], 0.03)
    ok &= abs(V - 1.36) < 1e-9 and mdd == 0
    # 2) 테마 = 시장 = 비테마면 정책 차 0
    ser = [(0.02 * ((-1) ** k), 0.02 * ((-1) ** k), 0.02 * ((-1) ** k), 0.2) for k in range(12)]
    vs = {p: simulate(ser, 0, 12, POLICIES[p], 0.03)[:2] for p in POLICIES}
    ok &= max(abs(vs[p][0] - vs["C"][0]) for p in vs) < 1e-12
    # 3) 테마만 폭락하면 NX가 C보다 얕다
    ser = [(-0.10, -0.03, 0.0, 0.3)] * 6 + [(0.0, 0.0, 0.0, 0.3)] * 6
    a, b = simulate(ser, 0, 12, POLICIES["NX"], 0.03), simulate(ser, 0, 12, POLICIES["C"], 0.03)
    ok &= a[1] > b[1] and a[0] > b[0]
    # 4) 비테마 산식: rm = wt·rt + (1−wt)·rx
    D = load_industries(12)
    s = market_and_ex(D, D["names"].index(THEME))
    ok &= all(abs(x[1] - (x[3] * x[0] + (1 - x[3]) * x[2])) < 1e-12 for x in s if x)
    # 5) 가중 시점: 월초 시총이 F-F Mkt에 더 가깝다(이번 달 말 시총 = 룩어헤드)
    mc = mkt_check(D)
    ok &= mc["te_pct"] < 0.25 and mc["te_pct"] < mc["te_endmonth_pct"]
    # 6) 이항 p
    ok &= abs(sign_p(12, 12) - 1 / 4096) < 1e-15 and sign_p(0, 12) == 1.0
    print(f"selftest {'PASS' if ok else 'FAIL'} · 합성시장 추적오차 {mc['te_pct']:.3f}%/월 "
          f"(월말 가중 대조 {mc['te_endmonth_pct']:.3f}%) · n={mc['n']}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="미국 매수 순서 비AI 칸 검정 — 측정 전용(룰 안 바꿈)")
    ap.add_argument("--save", action="store_true", help="data/research/nonai_slot_test.json 저장")
    ap.add_argument("--fetch", action="store_true", help="Ken French CSV 재수집")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        fetch()
    if a.selftest:
        return selftest()
    D = load_industries(12)
    mc = mkt_check(D)
    print(f"데이터 = Ken French 12산업 VW 총수익 {D['months'][0]}~{D['months'][-1]} · "
          f"합성시장 vs F-F Mkt 추적오차 {mc['te_pct']:.3f}%/월")
    out = {"meta": {"init": INIT, "policies": POLICIES, "data_end": D["months"][-1], "mkt_check": mc}}
    per12 = full(D, 12, 0.03)
    report(per12, 12, 0.03, "주 검정(12산업)", out, primary=True)
    for c in (0.01, 0.06):
        report(full(D, 12, c), 12, c, f"민감도 납입 {c*100:.0f}%", out, primary=False)
    report(full(D, 36, 0.03), 36, 0.03, "보조 36M", out, primary=False)
    strata(per12, 12, 0.03, out)
    cases(D, out)
    D49 = load_industries(49)
    report(full(D49, 12, 0.03), 12, 0.03, "견고성 49산업", out, primary=False)
    if a.save:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1, default=str)
        print(f"\n저장 → {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
