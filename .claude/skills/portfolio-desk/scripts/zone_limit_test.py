#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zone_limit_test.py — 낙폭군에서 '지금 사기' vs '더 아래 지정가로 기다리기' (stdlib · 측정 전용)

[왜 — 2026-11-09 정훈 선택 "1 GEV 존 재정의"]
GEV가 고점 대비 -35%(Stage4·MA200 아래)까지 빠지자 전력 데스크가 매수존을 $740~790으로 내리자고 했다.
"더 내려오면 사자"는 실은 **현재가 아래 지정가**다. 그게 지금 사는 것보다 나았는지를 과거 낙폭군에서 잰다.

[모형 — 사전등록 2026-11-09 trials.jsonl `gev_zone_limit`, 돌리기 전에 고정]
  유니버스 = data/tmp/bottom_study_bars.json (market_scan 유니버스 · 미국 시총 $10B+·코스피200+코스닥100 · Yahoo 10년 일봉)
  낙폭군   = 월말 종가가 252일 고점 대비 ≤ -30% · 종가 < MA200 · MA50 < MA200
  진입     = t+1 종가 P0
  즉시 매수 = P0에 산다
  지정가 d = P0×(1−d) (d = 5·10·15·20%) · 60거래일 안 저가가 닿으면 그 가격에 체결 ·
             미체결이면 그 돈은 t+1에 벤치(미국 ^GSPC · 국내 ^KS11)로 간다 — 우리 미국 트랙에서 존 밖이면 회차가 VOO로 가는 것과 같다
  지표     = (지정가 부 − 즉시 매수 부), t+1 기준 250거래일(주) · 120거래일(보조)
  단위     = 날짜별 평균 → 연도별 평균의 부호검정 · ③ 미국·국내 횡단면 · Holm = 4변형 × 2시장
  탐색(Holm 밖) = 60일 실현변동성 상위 1/3

⚠️ 생존편향 — 유니버스가 '지금 살아남은 큰 회사'다. 계속 빠져 시총에서 탈락한 종목(= 지정가가 덜 잃는 경우)이 빠져 있어
   **지정가 쪽에 불리하게** 기운다(사전등록 메모는 반대 방향으로 적었다 — 11/9 결과 기록에서 정정).
   ⇒ 지정가가 지면 '지금 사는 게 낫다'가 아니라 **'기다려서 나아진다는 근거가 없다'**로만 읽는다.
⚠️ 체결가 = 지정가(갭 하락 시 실제로는 시가가 더 싸다 — 지정가에 약간 불리). 현금 이자 없음.
⚠️ **측정 전용.** 매수존은 정훈 승인 사항이다.

  python zone_limit_test.py                 # 사전등록 검정
  python zone_limit_test.py --json out.json # 표본별 결과 저장
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *([os.pardir] * 4)))
CACHE = os.path.join(ROOT, "data", "tmp", "bottom_study_bars.json")
BENCH = {"US": "^GSPC", "KR": "^KS11"}
DEPTHS = (0.05, 0.10, 0.15, 0.20)
HS = (120, 250)


def binom_p(k: int, n: int) -> float:
    """단측 P(X ≥ k), p = 0.5."""
    if n == 0:
        return float("nan")
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def _bench_lookup(bars: dict, sym: str):
    b = bars[sym]
    mp, ds = dict(zip(b["d"], b["c"])), b["d"]

    def val(date: str):
        if date in mp:
            return mp[date]
        if date < ds[0]:
            return None
        lo, hi = 0, len(ds) - 1
        while lo < hi:                      # 직전 거래일
            mid = (lo + hi + 1) // 2
            if ds[mid] <= date:
                lo = mid
            else:
                hi = mid - 1
        return mp[ds[lo]]
    return val


def samples(data: dict, dd_cut: float, win: int) -> list[dict]:
    meta, bars = data["meta"], data["bars"]
    bv = {m: _bench_lookup(bars, s) for m, s in BENCH.items()}
    rows = []
    for sym, b in bars.items():
        if sym.startswith("^") or sym not in meta or meta[sym]["market"] not in BENCH:
            continue
        m = meta[sym]["market"]
        d, c, lo = b["d"], b["c"], b["l"]
        n = len(c)
        if n < 300:
            continue
        for i in range(251, n - 1):
            if d[i][:7] == d[i + 1][:7]:
                continue                                   # 월말만
            w = c[i - 251:i + 1]
            if any(x is None for x in w):
                continue
            if c[i] / max(w) - 1 > dd_cut:
                continue
            ma200, ma50 = sum(c[i - 199:i + 1]) / 200, sum(c[i - 49:i + 1]) / 50
            if not (c[i] < ma200 and ma50 < ma200):
                continue
            e = i + 1
            p0, b0 = c[e], bv[m](d[e])
            if not p0 or not b0:
                continue
            seg = c[max(1, i - 59):i + 1]
            lr = [math.log(seg[k] / seg[k - 1]) for k in range(1, len(seg)) if seg[k] and seg[k - 1]]
            rec = {"sym": sym, "m": m, "date": d[e],
                   "vol": st.pstdev(lr) * math.sqrt(252) if len(lr) > 20 else None}
            ok = False
            for h in HS:
                if e + h >= n:
                    continue
                ok = True
                bw = bv[m](d[e + h]) / b0
                now = c[e + h] / p0
                rec[f"now{h}"] = now - bw
                for dp in DEPTHS:
                    lim = p0 * (1 - dp)
                    fill = next((j for j in range(e + 1, min(e + 1 + win, n))
                                 if lo[j] is not None and lo[j] <= lim), None)
                    wealth = c[e + h] / lim if fill is not None and fill < e + h else bw
                    rec[f"L{int(dp * 100)}_{h}"] = wealth - now
                    rec[f"F{int(dp * 100)}"] = fill is not None
            for dp in DEPTHS:                              # 체결 확률(창 20·60·120일)
                lim = p0 * (1 - dp)
                for wn in (20, 60, 120):
                    s2 = [x for x in lo[e + 1:min(e + 1 + wn, n)] if x is not None]
                    rec[f"P{int(dp * 100)}_{wn}"] = (min(s2) <= lim) if s2 and e + wn < n else None
            if ok:
                rows.append(rec)
    return rows


def report(rows: list[dict]) -> None:
    print(f"표본 {len(rows)}건 · 종목 {len({r['sym'] for r in rows})}개")
    for m in BENCH:
        R = [r for r in rows if r["m"] == m]
        if not R:
            continue
        print(f"\n===== {m} · 표본 {len(R)} · 종목 {len({r['sym'] for r in R})} =====")
        print("체결 확률(저가 터치) — 창 20/60/120일:")
        for dp in DEPTHS:
            k = int(dp * 100)
            parts = []
            for wn in (20, 60, 120):
                v = [r[f"P{k}_{wn}"] for r in R if r.get(f"P{k}_{wn}") is not None]
                parts.append(f"{100 * sum(v) / len(v):.0f}%" if v else "-")
            print(f"  -{k}%: " + " / ".join(parts))
        for h in HS:
            RR = [r for r in R if f"now{h}" in r]
            nv = [r[f"now{h}"] for r in RR]
            print(f"\n[H={h}] n={len(RR)} · 즉시 매수 벤치 대비 평균 {100 * st.mean(nv):+.2f}%p · "
                  f"중앙 {100 * st.median(nv):+.2f}%p (⚠️생존편향 — 인용 금지)")
            print("  변형      체결률   차이평균   차이중앙   날짜승률   연도+    p(연도)")
            for dp in DEPTHS:
                k = int(dp * 100)
                key = f"L{k}_{h}"
                diffs = [r[key] for r in RR]
                fr = sum(r[f"F{k}"] for r in RR) / len(RR)
                byd = defaultdict(list)
                for r in RR:
                    byd[r["date"]].append(r[key])
                dm = {dt: st.mean(v) for dt, v in byd.items()}
                byy = defaultdict(list)
                for dt, v in dm.items():
                    byy[dt[:4]].append(v)
                ym = {y: st.mean(v) for y, v in sorted(byy.items())}
                ky = sum(1 for v in ym.values() if v > 0)
                print(f"  -{k:>2}%   {100 * fr:5.1f}%  {100 * st.mean(diffs):+7.2f}   {100 * st.median(diffs):+7.2f}   "
                      f"{100 * sum(1 for v in dm.values() if v > 0) / len(dm):5.1f}%   {ky}/{len(ym)}   {binom_p(ky, len(ym)):.3f}")
                if h == 250:
                    print("        연도별: " + " ".join(f"{y[2:]}:{100 * v:+.1f}" for y, v in ym.items()))
    vols = sorted(r["vol"] for r in rows if r["vol"])
    if not vols:
        return
    t2 = vols[int(len(vols) * 2 / 3)]
    print(f"\n[탐색 · Holm 밖] 60일 실현변동성 상위 1/3(≥{100 * t2:.0f}%) · H=250")
    for m in BENCH:
        RR = [r for r in rows if r["m"] == m and r["vol"] and r["vol"] >= t2 and "now250" in r]
        if not RR:
            continue
        print(f"  {m} n={len(RR)}")
        for dp in DEPTHS:
            k = int(dp * 100)
            diffs = [r[f"L{k}_250"] for r in RR]
            print(f"    -{k}%: 체결 {100 * sum(r[f'F{k}'] for r in RR) / len(RR):.0f}% · "
                  f"차이 평균 {100 * st.mean(diffs):+.2f} · 중앙 {100 * st.median(diffs):+.2f}")


def main() -> int:
    ap = argparse.ArgumentParser(description="낙폭군 즉시 매수 vs 아래 지정가 (사전등록 gev_zone_limit · 측정 전용)")
    ap.add_argument("--cut", type=float, default=-0.30, help="낙폭군 문턱(252일 고점 대비, 기본 -0.30)")
    ap.add_argument("--window", type=int, default=60, help="지정가 대기 거래일(기본 60)")
    ap.add_argument("--json", help="표본별 결과를 이 경로에 저장")
    a = ap.parse_args()
    if not os.path.exists(CACHE):
        print(f"캐시 없음: {os.path.relpath(CACHE, ROOT)} — bottom_study.py --fetch로 먼저 수집")
        return 1
    with open(CACHE, encoding="utf-8") as f:
        data = json.load(f)
    rows = samples(data, a.cut, a.window)
    report(rows)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rows, f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
