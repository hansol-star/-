#!/usr/bin/env python3
"""flow_edge.py — 수급 신호(Δ외국인지분율)의 forward 예측력 정직 백테스트 (stdlib·무키)

정훈 지시(2026-07-22 "네이버로 차트분석 공부"). signal_score.py가 **순수 가격신호의
방향 엣지 ≈ 0**(Stage4 회피·RSI 역발상만 유효)을 29년으로 실증했다. 자연스러운 다음 질문:
**한국 특유의 수급 = 외국인 지분율 추세는, 가격신호와 달리 forward 수익에 진짜 엣지가 있나?**

데이터 = 네이버 chart/day의 **봉별 foreignRetentionRate(외국인 지분율)** 심층 시계열
(삼성 1,608봉/6.5년 등). Yahoo엔 없는 한국 특화 축.

⚠️ 방법론(룩어헤드 차단·정직):
  · 신호는 **t 시점까지의 정보만**(Δ지분율 = frr[t] − frr[t−n]). 진입=t 종가, 성과=t→t+H.
  · "외인 순매수일 코스피 89.7% 상승"은 **같은 날 동행상관**(tradeable 아님) — 이 백테스트는
    과거 n일 지분율 변화 → **미래** 수익의 lead-lag라 그 착시를 배제한다.
  · 엣지 = 신호일 평균 forward수익 − **그 종목 자신의 baseline**(전일 평균). 종목 드리프트 통제
    (signal_score와 동일 정직 기준). 부호·크기·표본수(n)·양(+)비율을 함께 보고.
  · 지분율은 float·지수편입 변동에도 바뀔 수 있음(순수 매매 아님) → 20/60일 변화로 노이즈 완화.

표본 = 국내 보유 5 + 하닉 + 국내 워치(원익IPS·테스·두산E·SK이노). pooled + 종목별.

사용:
  python3 flow_edge.py                 # 전체 백테스트 표
  python3 flow_edge.py --json
  python3 flow_edge.py --codes 005930,000660
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import cli_common

try:
    import naver_chart as nc  # fetch_naver_ohlc 재사용
except Exception as e:  # pragma: no cover
    sys.exit(f"[flow_edge] naver_chart 임포트 실패: {e}")

UNIVERSE = [
    ("삼성전자", "005930"), ("LG전자", "066570"), ("두산로보틱스", "454910"),
    ("현대차", "005380"), ("NAVER", "035420"), ("SK하이닉스", "000660"),
    ("원익IPS", "240810"), ("테스", "095610"), ("두산에너빌리티", "034020"),
    ("SK이노베이션", "096770"),
]
HORIZONS = (5, 20)
DELTAS = (20, 60)          # 지분율 변화 창(빠름/느림)
THR = 0.10                 # Δ지분율 유의미 임계(%p) — 노이즈 컷


def _fwd_ret(c, t, h):
    if t + h >= len(c) or c[t] <= 0:
        return None
    return 100 * (c[t + h] / c[t] - 1)


def _mean(xs):
    return round(statistics.fmean(xs), 3) if xs else None


def _hit(xs):
    return round(100 * sum(1 for x in xs if x > 0) / len(xs), 1) if xs else None


def analyze_code(code: str) -> dict | None:
    d = nc.fetch_naver_ohlc(code, "day", 2600)  # 심층(상장이래~)
    if not d:
        return None
    c = d["c"]
    frr = d.get("frr") or []
    n = len(c)
    if n < 120 or len(frr) != n:
        return None

    # 종목별 Δ지분율 분위수 임계 — 등선택도(각 종목 상·하위 20%만 '강한' 매집/분산)
    q = {}
    for D in DELTAS:
        vals = [frr[t] - frr[t - D] for t in range(D, n)
                if frr[t] is not None and frr[t - D] is not None]
        vals.sort()
        if len(vals) >= 20:
            q[D] = (vals[int(len(vals) * 0.8)], vals[int(len(vals) * 0.2)])  # (상위20%컷, 하위20%컷)
        else:
            q[D] = (THR, -THR)

    res = {"code": code, "bars": n, "q": {D: [round(a, 3), round(b, 3)] for D, (a, b) in q.items()}}
    for H in HORIZONS:
        # baseline = 전 구간 forward 수익
        base = [r for t in range(n) if (r := _fwd_ret(c, t, H)) is not None]
        res[f"base_{H}"] = {"mean": _mean(base), "hit": _hit(base), "n": len(base)}
        bmean = res[f"base_{H}"]["mean"] or 0
        for D in DELTAS:
            hi_cut, lo_cut = q[D]
            up, dn = [], []       # 임계(THR) 방식 — 완만
            sup, sdn = [], []     # 분위수 방식 — 강한 극단(상·하위 20%)
            for t in range(D, n):
                if frr[t] is None or frr[t - D] is None:
                    continue
                r = _fwd_ret(c, t, H)
                if r is None:
                    continue
                dfrr = frr[t] - frr[t - D]
                if dfrr >= THR:
                    up.append(r)
                elif dfrr <= -THR:
                    dn.append(r)
                if dfrr >= hi_cut:
                    sup.append(r)
                elif dfrr <= lo_cut:
                    sdn.append(r)
            res[f"up{D}_{H}"] = {"mean": _mean(up), "hit": _hit(up), "n": len(up),
                                 "edge": round((_mean(up) or 0) - bmean, 3) if up else None}
            res[f"dn{D}_{H}"] = {"mean": _mean(dn), "hit": _hit(dn), "n": len(dn),
                                 "edge": round((_mean(dn) or 0) - bmean, 3) if dn else None}
            res[f"sup{D}_{H}"] = {"mean": _mean(sup), "hit": _hit(sup), "n": len(sup),
                                  "edge": round((_mean(sup) or 0) - bmean, 3) if sup else None}
            res[f"sdn{D}_{H}"] = {"mean": _mean(sdn), "hit": _hit(sdn), "n": len(sdn),
                                  "edge": round((_mean(sdn) or 0) - bmean, 3) if sdn else None}
    return res


def pool(per_stock: list[dict]) -> dict:
    """종목별 엣지를 표본수 가중 평균(pooled)."""
    out = {}
    for H in HORIZONS:
        for D in DELTAS:
            for sig in (f"up{D}_{H}", f"dn{D}_{H}", f"sup{D}_{H}", f"sdn{D}_{H}"):
                num = den = 0
                hit_num = 0
                for s in per_stock:
                    cell = s.get(sig)
                    if cell and cell["edge"] is not None and cell["n"] > 0:
                        num += cell["edge"] * cell["n"]
                        den += cell["n"]
                        if cell["hit"] is not None:
                            hit_num += cell["hit"] * cell["n"]
                out[sig] = {"edge_w": round(num / den, 3) if den else None,
                            "hit_w": round(hit_num / den, 1) if den else None, "n": den}
        base_num = base_den = 0
        for s in per_stock:
            b = s.get(f"base_{H}")
            if b and b["mean"] is not None:
                base_num += b["mean"] * b["n"]
                base_den += b["n"]
        out[f"base_{H}"] = {"mean_w": round(base_num / base_den, 3) if base_den else None, "n": base_den}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="수급(Δ외국인지분율) forward 엣지 백테스트")
    ap.add_argument("--codes", "--tickers", help="쉼표·공백구분 6자리(기본=국내 유니버스)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    uni = ([(c, c) for c in cli_common.split_tickers(args.codes)] if args.codes else UNIVERSE)
    per = []
    labels = {}
    for label, code in uni:
        r = analyze_code(code)
        if r:
            r["label"] = label
            labels[code] = label
            per.append(r)
    if not per:
        print("데이터 부족 — 백테스트 불가")
        return 1
    pooled = pool(per)

    if args.json:
        print(json.dumps({"per_stock": per, "pooled": pooled}, ensure_ascii=False, indent=1))
        return 0

    print("수급 신호 forward 엣지 백테스트 (flow_edge.py · Δ외국인지분율 → 미래수익 · 룩어헤드 차단)")
    print("=" * 84)
    print(f"표본: {len(per)}종목 · 임계 |Δ지분율|≥{THR}%p · 엣지 = 신호평균 − 종목baseline(자기 드리프트 통제)")
    print("-" * 84)
    # pooled 요약
    print("■ POOLED (표본수 가중) — 핵심 결론  [완만=|Δ|≥0.1%p · 강함=종목별 상·하위 20%]")
    for H in HORIZONS:
        b = pooled[f"base_{H}"]
        print(f"  [{H}일 forward] baseline 평균수익 {b['mean_w']}% (n={b['n']:,})")
        for D in DELTAS:
            u = pooled[f"up{D}_{H}"]; dn = pooled[f"dn{D}_{H}"]
            su = pooled[f"sup{D}_{H}"]; sd = pooled[f"sdn{D}_{H}"]
            print(f"     완만 Δ{D}: ↑엣지 {u['edge_w']:+}%p(n={u['n']:,}) · ↓엣지 {dn['edge_w']:+}%p(n={dn['n']:,})")
            print(f"     강함 Δ{D}: ↑엣지 {su['edge_w']:+}%p 승률{su['hit_w']}%(n={su['n']:,}) · "
                  f"↓엣지 {sd['edge_w']:+}%p 승률{sd['hit_w']}%(n={sd['n']:,})")
    print("-" * 84)
    # 종목별(20일·Δ20만 간결 표)
    print("■ 종목별 (20일 forward · Δ지분율20 기준)")
    print(f"{'종목':<12}{'봉수':>6}{'base%':>8}{'↑엣지':>8}{'↑승률':>7}{'↑n':>6}{'↓엣지':>8}{'↓승률':>7}{'↓n':>6}")
    for s in per:
        b = s["base_20"]["mean"]
        u = s["up20_20"]; dn = s["dn20_20"]
        print(f"{s['label']:<12}{s['bars']:>6}{b:>8}"
              f"{(u['edge'] if u['edge'] is not None else 0):>8}{(u['hit'] or 0):>7}{u['n']:>6}"
              f"{(dn['edge'] if dn['edge'] is not None else 0):>8}{(dn['hit'] or 0):>7}{dn['n']:>6}")
    print("-" * 84)
    print("※ 엣지 = 신호일 평균 forward수익 − 그 종목 baseline. +면 지분율 변화가 방향 예측력.")
    print("  해석은 콘솔 밖(study_log) — 큰 엣지라도 표본·기간 편향 점검 후 채택. 측정 전용·룰 불변.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
