#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bottom_study.py — '많이 빠진 종목 중 무엇이 오르나' 검정 [11/5 신설 · 정훈 "고점 대비 많이 빠지거나 바닥선인 친구들 중 오를 가능성 높은 주식을 잘 발견해야 돼"]

질문
────────────────────────────────────────────────────────────
market_scan의 CONTRA(역발상)는 '많이 빠졌다'만 본다. 많이 빠진 종목은 **계속 빠지는 것**(논지 붕괴·떨어지는 칼)과
**바닥을 다지고 오르는 것**이 섞여 있다. 그 둘을 가르는 가격 신호가 있는가? — 사전등록 = trials.jsonl `bottom_signals`.

설계
  · 유니버스 = market_scan과 같은 현재 구성(미국 시총 $10B+ · 코스피200+코스닥100) · Yahoo 10년 일봉
  · 표본일 = 매월 마지막 거래일 t. **낙폭군** = 그날 종가가 직전 252일 고점 대비 ≤ -35%
  · 신호(전부 t까지의 데이터만):
      S1 저점 안정   = 최근 20일 저가 > 직전 60일 저가(최근 20일 새 저점 없음) · 종가 ≥ 60일 저가 × 1.10
      S2 50일선 탈환 = 종가 > MA50 · 20일 전엔 종가 < MA50
      S3 강세 다이버전스 = 최근 60일 두 스윙 저점: 가격 저점↓ · RSI14 저점↑ (ta_core.divergence)
      S4 투매→고갈   = 최근 60일 중 거래량 ≥ 200일 평균 3배인 날이 있고 · 최근 20일 평균 거래량 < 50일 평균
      S5 상대강도 전환 = 3개월 수익률 > 같은 시장 지수 3개월 수익률
      S6 30주선 상향 = 종가 > MA150 · MA150이 20일 전보다 높다(와인스타인 1→2단계)
  · 진입 = t+1 종가(1일 지연) · 지평 60·120·250거래일
  · **주 비교 = 낙폭군 내부**: 신호 적중 종목 수익 − 같은 날 낙폭군 평균 수익(횡단면 차감)
      ← 생존 편향 때문이다. 유니버스가 '지금 살아남아 큰 회사'라서 낙폭군 전체가 과거에 회복한 이름으로 채워져 있다.
        낙폭군 vs 전체 비교는 그 편향을 그대로 먹는다. 낙폭군 **안에서** 신호가 가르는지만 보면 편향이 양쪽에 같이 걸린다.
      ⚠️ 그래도 완전하진 않다 — 상장폐지·시총 탈락 종목(진짜 떨어지는 칼)이 빠져 있어 '안 오른 쪽'이 덜 나쁘게 보인다.
  · ① 집계 → ② 연도별 분해(부호 일치 연도 수) → ③ 시장 간(미국·국내) + 미국 섹터 횡단면 → Holm
  · 대조군 = 같은 날 낙폭군에서 적중 수만큼 무작위로 뽑은 위약(200회) 분포 대비 백분위

⚠️ 측정 전용 — 통과해도 룰이 아니다. 스캐너의 '후보 순서'에만 쓴다(정훈 승인 없이 매수 규칙 안 바꾼다).

사용법
  python bottom_study.py --fetch          # 10년 일봉 수집 → 캐시(스크래치 경로 · 약 3~5분)
  python bottom_study.py                  # 검정 (캐시 사용)
  python bottom_study.py --json out.json
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import math
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
import market_scan as ms  # noqa: E402

CACHE = os.path.join(ROOT, "data", "tmp", "bottom_study_bars.json")
DD_CUT = -0.35
HORIZONS = (60, 120, 250)
SIGNALS = ("S1", "S2", "S3", "S4", "S5", "S6")
NAMES = {"S1": "저점 안정", "S2": "50일선 탈환", "S3": "강세 다이버전스", "S4": "투매→고갈",
         "S5": "상대강도 전환", "S6": "30주선 상향"}


def fetch(workers=8):
    uni = [u for u in ms.us_universe()] + ms.kr_universe()
    out = {"meta": {u["ticker"]: {"market": u["market"], "sector": u["sector"], "name": u["name"]} for u in uni},
           "bars": {}}
    syms = [u["ticker"] for u in uni] + list(ms.BENCH.values())
    with cf.ThreadPoolExecutor(workers) as ex:
        for s, b in zip(syms, ex.map(lambda s: ms.bars(s, "10y"), syms)):
            if b:
                out["bars"][s] = {"d": b["d"], "c": b["c"], "l": b["l"], "v": b["v"]}
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(out, open(CACHE, "w", encoding="utf-8"))
    print(f"수집 {len(out['bars'])}/{len(syms)} → {os.path.relpath(CACHE, ROOT)}")


def _rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n:
        return out
    g = [max(c[i] - c[i - 1], 0) for i in range(1, len(c))]
    lo = [max(c[i - 1] - c[i], 0) for i in range(1, len(c))]
    ag, al = sum(g[:n]) / n, sum(lo[:n]) / n
    for i in range(n, len(c)):
        if i > n:
            ag = (ag * (n - 1) + g[i - 1]) / n
            al = (al * (n - 1) + lo[i - 1]) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def _cum(x):
    s = [0.0]
    for v in x:
        s.append(s[-1] + v)
    return s


def signals_at(t, c, l, v, cs, vs, rsi, bench_ret3):
    """t 시점 신호(t까지의 데이터만). 반환 = {S1..S6: bool}."""
    import ta_core
    ma = lambda n, k=t: (cs[k + 1] - cs[k + 1 - n]) / n  # noqa: E731
    vma = lambda n, k=t: (vs[k + 1] - vs[k + 1 - n]) / n  # noqa: E731
    low20 = min(l[t - 19:t + 1])
    low60_prior = min(l[t - 79:t - 19])
    low60 = min(l[t - 59:t + 1])
    s = {}
    s["S1"] = low20 > low60_prior and c[t] >= low60 * 1.10
    s["S2"] = c[t] > ma(50) and c[t - 20] < ma(50, t - 20)
    rs = [x for x in rsi[t - 59:t + 1]]
    s["S3"] = bool(None not in rs and (ta_core.divergence(c[t - 59:t + 1], rs, 60) or {}).get("bullish"))
    a200 = vma(200)
    s["S4"] = a200 > 0 and max(v[t - 59:t + 1]) >= 3 * a200 and vma(20) < vma(50)
    r3 = c[t] / c[t - 63] - 1
    s["S5"] = bench_ret3 is not None and r3 > bench_ret3
    s["S6"] = c[t] > ma(150) and ma(150) > ma(150, t - 20)
    return s


def build_events(data):
    """월말 표본: [{date, ticker, market, sector, sig{}, fwd{H: r}}] — 낙폭군만."""
    bars, meta = data["bars"], data["meta"]
    bench = {}
    for mk, sym in ms.BENCH.items():
        b = bars.get(sym)
        bench[mk] = dict(zip(b["d"], b["c"])) if b else {}
    ev = []
    for tk, b in bars.items():
        if tk not in meta:
            continue
        mk = meta[tk]["market"]
        d, c, l, v = b["d"], b["c"], b["l"], b["v"]
        if len(c) < 400:
            continue
        cs, vs, rsi = _cum(c), _cum(v), _rsi(c)
        bd = bench[mk]
        bdates = sorted(bd)
        for t in range(260, len(c) - 2):
            if d[t][:7] == d[t + 1][:7]:
                continue                                   # 월말만
            hi = max(c[t - 251:t + 1])
            dd = c[t] / hi - 1
            if dd > DD_CUT:
                continue
            # 지수 3M 수익률(같은 날짜 기준)
            br3 = None
            if d[t] in bd:
                k = bdates.index(d[t]) if False else None
            if d[t] in bd and d[t - 63] in bd:
                br3 = bd[d[t]] / bd[d[t - 63]] - 1
            sig = signals_at(t, c, l, v, cs, vs, rsi, br3)
            e0 = t + 1                                     # 1일 지연 진입
            fwd = {H: (c[e0 + H] / c[e0] - 1) if e0 + H < len(c) else None for H in HORIZONS}
            ev.append({"date": d[t], "ticker": tk, "market": mk, "sector": meta[tk]["sector"],
                       "dd": dd, "sig": sig, "fwd": fwd})
    return ev


def analyze(ev, seed=7):
    rnd = random.Random(seed)
    by_date = {}
    for e in ev:
        by_date.setdefault((e["market"], e["date"]), []).append(e)
    res = {}
    for mk in ("US", "KR", "ALL"):
        for S in SIGNALS:
            for H in HORIZONS:
                ex_all, years, sectors, placebo_gap = [], {}, {}, []
                n_hit = 0
                for (m, dte), grp in by_date.items():
                    if mk != "ALL" and m != mk:
                        continue
                    g = [x for x in grp if x["fwd"][H] is not None]
                    if len(g) < 5:
                        continue
                    mean = st.fmean(x["fwd"][H] for x in g)
                    hits = [x for x in g if x["sig"][S]]
                    if not hits:
                        continue
                    n_hit += len(hits)
                    gap = st.fmean(x["fwd"][H] for x in hits) - mean
                    ex_all.append((gap, len(hits)))
                    years.setdefault(dte[:4], []).append(gap)
                    for x in hits:
                        sectors.setdefault(x["sector"], []).append(x["fwd"][H] - mean)
                if not ex_all:
                    continue
                # 날짜 가중(적중 수) 평균 — 날짜 = 독립 단위에 가까움
                w = sum(n for _, n in ex_all)
                agg = sum(g * n for g, n in ex_all) / w
                date_pos = sum(1 for g, _ in ex_all if g > 0)
                yr = {y: st.fmean(v) for y, v in years.items()}
                res[(mk, S, H)] = {"n_hit": n_hit, "n_dates": len(ex_all), "excess_pct": round(agg * 100, 2),
                                   "date_win": round(100 * date_pos / len(ex_all), 1),
                                   "years_pos": sum(1 for v in yr.values() if v > 0), "years": len(yr),
                                   "year_detail": {y: round(v * 100, 1) for y, v in sorted(yr.items())},
                                   "sector_pos": sum(1 for v in sectors.values() if len(v) >= 20 and st.fmean(v) > 0),
                                   "sector_n": sum(1 for v in sectors.values() if len(v) >= 20),
                                   "p_sign": _sign_p(date_pos, len(ex_all))}
    return res


def _sign_p(k, n):
    """단측 이항 p(날짜 부호) — 정규근사."""
    if n == 0:
        return 1.0
    z = (k - n / 2) / math.sqrt(n / 4)
    return 0.5 * math.erfc(z / math.sqrt(2))


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [None] * len(ps), 0
    m = len(ps)
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * ps[i]))
        adj[i] = run
    return adj


def main():
    ap = argparse.ArgumentParser(description="낙폭 종목 바닥 신호 검정 (측정 전용)")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    if a.fetch:
        fetch(); return 0
    if not os.path.exists(CACHE):
        print("캐시 없음 — --fetch 먼저"); return 1
    data = json.load(open(CACHE, encoding="utf-8"))
    ev = build_events(data)
    print(f"낙폭군 표본 {len(ev)}건 (미국 {sum(e['market'] == 'US' for e in ev)} · 국내 {sum(e['market'] == 'KR' for e in ev)})")
    res = analyze(ev)
    keys = [k for k in res if k[2] == 120 and k[0] in ("US", "KR")]
    adj = holm([res[k]["p_sign"] for k in keys])
    for k, p in zip(keys, adj):
        res[k]["p_holm"] = p
    print("\n시장 신호            지평  적중  날짜  낙폭군대비%p  날짜승률  연도+  섹터+  p(부호)  Holm(120d·12검정)")
    for mk in ("US", "KR", "ALL"):
        for S in SIGNALS:
            for H in HORIZONS:
                r = res.get((mk, S, H))
                if not r:
                    continue
                print(f"{mk:3} {S} {NAMES[S]:8} {H:4} {r['n_hit']:6} {r['n_dates']:4} {r['excess_pct']:+9.2f} "
                      f"{r['date_win']:8.1f}% {r['years_pos']:2}/{r['years']:<2} {r['sector_pos']:2}/{r['sector_n']:<2} "
                      f"{r['p_sign']:.3g}  {r.get('p_holm', ''):.3g}" if 'p_holm' in r else
                      f"{mk:3} {S} {NAMES[S]:8} {H:4} {r['n_hit']:6} {r['n_dates']:4} {r['excess_pct']:+9.2f} "
                      f"{r['date_win']:8.1f}% {r['years_pos']:2}/{r['years']:<2} {r['sector_pos']:2}/{r['sector_n']:<2} "
                      f"{r['p_sign']:.3g}")
        print()
    if a.json:
        json.dump({f"{k[0]}|{k[1]}|{k[2]}": v for k, v in res.items()}, open(a.json, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
