#!/usr/bin/env python3
"""sizing_backtest.py — 변동성 타겟 사이징 백테스트 (stdlib only·측정 전용)

정훈 지시(2026-07-21 "가자"): vol_sizing의 폭풍%ile→트랜치 감산이 실제로 위험조정
수익을 개선하는지 과거로 검증. 영상(Miles/GARCH)의 백테스트를 우리 지수(코스피 29년)에
재현 — 변동성 타겟(폭풍엔 노출↓) vs 고정(buy&hold) 사이징을 나란히.

방법(미래참조 없음):
  · 각 날 t의 노출 = target_vol / RV20_{t-1}  (전일까지의 실현변동성으로 사이징 → 룩어헤드 X)
  · **우리 룰 = 무레버리지** → 노출 상한 1.0(폭풍엔 <1로 축소, 평시 100%). cap>1은 옵션.
  · 전략수익_t = 노출_t × 지수수익_t.  고정 = 노출 1.0 상시(buy&hold).
지표: 최종부(1→), CAGR, 연율변동성, 샤프(rf=0), 최대낙폭(MDD), 최악 21일.
영상 결론(주식): vol타겟은 CAGR 소폭 손해 대신 MDD·최악월을 크게 줄인다(보험). 검증.

사용:
  python3 sizing_backtest.py                     # 코스피
  python3 sizing_backtest.py --symbol ^KS11 --target 20 --cap 1.0
  python3 sizing_backtest.py --symbol NVDA --cap 1.5
  python3 sizing_backtest.py --json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics

try:
    import history_backfill as hb
except ImportError:
    hb = None

TD = 252


def load(symbol):
    rows = hb.load_cached(symbol) if hb else []
    return [c for _, c in rows], [d for d, _ in rows]


def daily_rets(closes):
    return [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes)) if closes[i - 1]]


def rolling_rv(rets, w=20):
    """전일까지 w일 실현변동성(연율, 소수). index i는 rets[:i] 기반(룩어헤드 없음)."""
    out = [None] * len(rets)
    for i in range(w, len(rets)):
        seg = rets[i - w:i]
        out[i] = statistics.pstdev(seg) * math.sqrt(TD)
    return out


def equity_metrics(strat_rets):
    """누적부·CAGR·연율변동성·샤프·MDD·최악21일."""
    eq = [1.0]
    for r in strat_rets:
        eq.append(eq[-1] * (1 + r))
    final = eq[-1]
    n = len(strat_rets)
    cagr = final ** (TD / n) - 1 if n else 0
    vol = statistics.pstdev(strat_rets) * math.sqrt(TD) if n > 1 else 0
    mean = statistics.fmean(strat_rets) * TD if n else 0
    sharpe = mean / vol if vol else 0
    # MDD
    peak = eq[0]
    mdd = 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    # 최악 21일 롤링
    worst21 = 0.0
    for i in range(21, len(eq)):
        worst21 = min(worst21, eq[i] / eq[i - 21] - 1)
    return {"final": round(final, 2), "cagr": round(cagr * 100, 2),
            "vol": round(vol * 100, 1), "sharpe": round(sharpe, 2),
            "mdd": round(mdd * 100, 1), "worst21d": round(worst21 * 100, 1)}


def backtest(symbol, target, cap, w=20):
    closes, dates = load(symbol)
    if len(closes) < 400:
        return {"symbol": symbol, "ok": False, "reason": f"이력 부족({len(closes)})"}
    rets = daily_rets(closes)
    rv = rolling_rv(rets, w)
    tv = target / 100.0
    fixed, volscaled, exps = [], [], []
    for i in range(len(rets)):
        if rv[i] is None or rv[i] <= 0:
            continue
        exp = min(cap, tv / rv[i])   # 노출(상한 cap)
        volscaled.append(exp * rets[i])
        fixed.append(rets[i])         # buy&hold(노출 1.0)
        exps.append(exp)
    return {
        "symbol": symbol, "ok": True, "n": len(fixed),
        "span": f"{dates[0]}~{dates[-1]}", "target_vol": target, "cap": cap,
        "avg_exposure": round(statistics.fmean(exps), 2),
        "fixed": equity_metrics(fixed),
        "volscaled": equity_metrics(volscaled),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="변동성 타겟 사이징 백테스트 (측정 전용·stdlib)")
    ap.add_argument("--symbol", default="^KS11")
    ap.add_argument("--target", type=float, default=20.0, help="목표 연율변동성 %%")
    ap.add_argument("--cap", type=float, default=1.0, help="노출 상한(우리 무레버리지=1.0)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if hb is None:
        print("history_backfill 미탑재 — 먼저 python3 history_backfill.py")
        return 1
    r = backtest(args.symbol, args.target, args.cap)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if not r.get("ok"):
        print(f"{args.symbol}: {r.get('reason')}")
        return 0
    print(f"■ 변동성 타겟 사이징 백테스트 — {r['symbol']} ({r['span']}·{r['n']:,}일)")
    print(f"  목표변동성 {r['target_vol']}% · 노출상한 {r['cap']} · 평균노출 {r['avg_exposure']}")
    print(f"  {'전략':<14}{'최종부':>8}{'CAGR%':>8}{'변동성%':>8}{'샤프':>7}{'MDD%':>8}{'최악21d%':>9}")
    for name, k in [("고정(buy&hold)", "fixed"), ("변동성타겟", "volscaled")]:
        m = r[k]
        print(f"  {name:<14}{m['final']:>8}{m['cagr']:>8}{m['vol']:>8}{m['sharpe']:>7}{m['mdd']:>8}{m['worst21d']:>9}")
    f, v = r["fixed"], r["volscaled"]
    print(f"\n  → 샤프 {f['sharpe']}→{v['sharpe']} · MDD {f['mdd']}→{v['mdd']}% · "
          f"최악21일 {f['worst21d']}→{v['worst21d']}% · CAGR {f['cagr']}→{v['cagr']}%")
    print("  (영상 결론 검증: 주식은 vol타겟이 CAGR 소폭 손해 대신 낙폭·꼬리 축소=보험)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
