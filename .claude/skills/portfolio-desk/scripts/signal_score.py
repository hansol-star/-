#!/usr/bin/env python3
"""signal_score.py — 기술신호 예측력 후행채점 (stdlib only·측정 전용)

동기(정훈 2026-07-22 "보완할 점 지금 보완해"): PM 자체 비판 = "13지표 컨플루언스의
실전 예측력 검증 0회 — 도구가 많다 ≠ 판단이 좋다". 이 스크립트가 그 검증을 수행한다:
history_backfill 캐시(상장 이래 종가)로 각 신호의 **당시 상태 → 이후 5·20일 수익률**을
전이력 채점(룩어헤드 없음). 신호가 무정보(기준선)보다 나은지 '엣지'를 숫자로 낸다.

채점 신호(종가 기반 — 거래량·고저 필요한 지표는 제외):
  rsi_bull/bear(≥55/≤45) · above_ma50 · above_ma200 · qualified_cross(가격자격 크로스)
  macd_hist(양/음) · mom20(20일 모멘텀) · stage_proxy(MA150 상승+가격 위 ≈ Stage2)

해석: edge5/edge20 = 신호 발생일의 평균 forward수익 − 그 종목 무조건 평균(기준선).
  양수 = 신호가 정보를 담음 / 0 근처 = 장식 / 음수 = 역신호(반대로 써야 함).
⚠️ 통계일 뿐 — 개별 시점 판단은 여전히 PM 종합·펀더 정본. R3 주간 캘리브레이션에서
누적 추적(self-review 스킬 편입 2026-07-22).

사용:
  python3 signal_score.py                     # 코스피 + 보유 15 풀채점
  python3 signal_score.py --symbols ^KS11
  python3 signal_score.py --pooled            # 전 종목 합산(신호별 총평)만
  python3 signal_score.py --json
"""
from __future__ import annotations

import argparse
import json
import statistics
import cli_common

try:
    import history_backfill as hb
    import market_data as md
except ImportError:
    hb = md = None


# ── 시리즈 유틸 (전부 head-None 패딩으로 인덱스 정렬) ─────────────────────
def sma_padded(c, n):
    out = [None] * (n - 1)
    if len(c) < n:
        return out + [None] * max(0, len(c) - n + 1)
    acc = sum(c[:n])
    out.append(acc / n)
    for i in range(n, len(c)):
        acc += c[i] - c[i - n]
        out.append(acc / n)
    return out


def ema_padded(c, n):
    out = [None] * (n - 1)
    if len(c) < n:
        return out + [None] * max(0, len(c) - n + 1)
    k = 2 / (n + 1)
    cur = sum(c[:n]) / n
    out.append(cur)
    for x in c[n:]:
        cur = x * k + cur * (1 - k)
        out.append(cur)
    return out


def rsi_padded(c, n=14):
    if len(c) < n + 1:
        return [None] * len(c)
    out = [None] * n
    gains = [max(c[i] - c[i - 1], 0.0) for i in range(1, len(c))]
    losses = [max(c[i - 1] - c[i], 0.0) for i in range(1, len(c))]
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    def _r(g, s):
        return 100.0 if s == 0 else 100 - 100 / (1 + g / s)
    out.append(_r(ag, al))
    for i in range(n, len(gains)):
        ag = (ag * (n - 1) + gains[i]) / n
        al = (al * (n - 1) + losses[i]) / n
        out.append(_r(ag, al))
    return out


def macd_hist_padded(c, fast=12, slow=26, sig=9):
    ef, es = ema_padded(c, fast), ema_padded(c, slow)
    line = [None if (a is None or b is None) else a - b for a, b in zip(ef, es)]
    vals = [x for x in line if x is not None]
    if len(vals) < sig:
        return [None] * len(c)
    k = 2 / (sig + 1)
    out = [None] * len(c)
    start = next(i for i, x in enumerate(line) if x is not None)
    cur = sum(vals[:sig]) / sig
    for i in range(start + sig - 1, len(c)):
        cur = line[i] * k + cur * (1 - k)
        out[i] = line[i] - cur
    return out


# ── 신호 정의 (i일 종가까지만 사용 — 룩어헤드 없음) ───────────────────────
def build_signals(c):
    ma50 = sma_padded(c, 50)
    ma150 = sma_padded(c, 150)
    ma200 = sma_padded(c, 200)
    r = rsi_padded(c)
    mh = macd_hist_padded(c)
    sigs = {}
    n = len(c)
    def arr(fn):
        return [fn(i) if all(x is not None for x in deps(i)) else None for i in range(n)]
    # 각 신호: True=강세상태, False=약세상태, None=판정불가
    sigs["rsi_zone"] = [None if r[i] is None else (True if r[i] >= 55 else (False if r[i] <= 45 else None)) for i in range(n)]
    sigs["above_ma50"] = [None if ma50[i] is None else c[i] >= ma50[i] for i in range(n)]
    sigs["above_ma200"] = [None if ma200[i] is None else c[i] >= ma200[i] for i in range(n)]
    sigs["qualified_cross"] = [
        None if (ma50[i] is None or ma200[i] is None) else
        (True if (ma50[i] >= ma200[i] and c[i] >= ma50[i]) else
         (False if (ma50[i] < ma200[i] and c[i] < ma50[i]) else None))
        for i in range(n)]
    sigs["macd_hist"] = [None if mh[i] is None else mh[i] > 0 for i in range(n)]
    sigs["mom20"] = [None if i < 20 else c[i] > c[i - 20] for i in range(n)]
    sigs["stage_proxy"] = [
        None if (ma150[i] is None or i < 21 or ma150[i - 21] is None) else
        (ma150[i] > ma150[i - 21] and c[i] > ma150[i])
        for i in range(n)]
    return sigs


def score_symbol(symbol, fwds=(5, 20)):
    rows = hb.load_cached(symbol) if hb else []
    c = [x for _, x in rows]
    if len(c) < 300:
        return None
    sigs = build_signals(c)
    n = len(c)
    fwd = {}
    for f in fwds:
        fwd[f] = [None] * n
        for i in range(n - f):
            if c[i]:
                fwd[f][i] = 100 * (c[i + f] / c[i] - 1)
    base = {f: statistics.fmean([x for x in fwd[f] if x is not None]) for f in fwds}
    out = {"symbol": symbol, "n_days": n, "baseline": {f: round(base[f], 3) for f in fwds},
           "signals": {}}
    for name, states in sigs.items():
        rec = {}
        for state, label in ((True, "bull"), (False, "bear")):
            idx = [i for i in range(n) if states[i] is state]
            st = {}
            for f in fwds:
                vals = [fwd[f][i] for i in idx if fwd[f][i] is not None]
                if len(vals) < 30:
                    continue
                mean = statistics.fmean(vals)
                hit = 100 * sum(1 for v in vals if v > 0) / len(vals)
                st[f] = {"n": len(vals), "mean": round(mean, 3),
                         "hit": round(hit, 1), "edge": round(mean - base[f], 3)}
            if st:
                rec[label] = st
        out["signals"][name] = rec
    return out


def pool(results, fwds=(5, 20)):
    """전 종목 합산 — 신호별 edge 평균(종목 동일가중)."""
    agg = {}
    for r in results:
        for name, rec in r["signals"].items():
            for label, st in rec.items():
                for f, v in st.items():
                    agg.setdefault((name, label, f), []).append(v["edge"])
    out = {}
    for (name, label, f), edges in sorted(agg.items()):
        out.setdefault(name, {}).setdefault(label, {})[f] = {
            "symbols": len(edges), "avg_edge": round(statistics.fmean(edges), 3),
            "positive_ratio": round(100 * sum(1 for e in edges if e > 0) / len(edges), 0)}
    return out


def _universe(args):
    if args.symbols:
        return [s.strip() for s in cli_common.split_tickers(args.symbols) if s.strip()]
    syms = ["^KS11"]
    if md:
        syms += [s for _, s in md.GROUPS["holdings"]]
    return syms


def main() -> int:
    ap = argparse.ArgumentParser(description="기술신호 예측력 후행채점 (측정 전용·stdlib)")
    ap.add_argument("--symbols", "--tickers", help="쉼표·공백구분(기본=코스피+보유15)")
    ap.add_argument("--pooled", action="store_true", help="전 종목 합산 총평만")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if hb is None:
        print("history_backfill 미탑재 — 먼저 python3 history_backfill.py")
        return 1
    results = [r for s in _universe(args) if (r := score_symbol(s))]
    pooled = pool(results)
    if args.json:
        print(json.dumps({"pooled": pooled} if args.pooled else
                         {"symbols": results, "pooled": pooled}, ensure_ascii=False, indent=1))
        return 0
    print(f"신호 예측력 채점 — {len(results)}종목 전이력 (edge = 신호일 평균 fwd수익% − 무조건 기준선)")
    print(f"{'신호':<17}{'상태':<6}{'fwd5 edge':>10}{'양(+)비율':>9}{'fwd20 edge':>11}{'양(+)비율':>9}")
    print("-" * 64)
    for name, rec in pooled.items():
        for label in ("bull", "bear"):
            if label not in rec:
                continue
            e5 = rec[label].get(5, {})
            e20 = rec[label].get(20, {})
            print(f"{name:<17}{label:<6}{str(e5.get('avg_edge','—')):>10}{str(e5.get('positive_ratio','—'))+'%':>9}"
                  f"{str(e20.get('avg_edge','—')):>11}{str(e20.get('positive_ratio','—'))+'%':>9}")
    print("\n해석: bull 신호는 edge>0, bear 신호는 edge<0이어야 '정보 있음'. 0 근처=장식.")
    print("※ 통계 참고 — 개별 판단은 펀더·PM 종합 정본. R3 주간 캘리브레이션에서 누적 추적.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
