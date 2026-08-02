#!/usr/bin/env python3
"""history_analysis.py — 장기 이력(수십 년) 변동성·크래시 분석 (stdlib only·측정 전용)

동기(정훈 2026-07-21): "최대한 많은 데이터 가져와서 분석하자." history_backfill.py가
상장 이래 전 일봉(코스피 29.6년 등 총 26.9만개)을 캐시 → 이 스크립트가 그걸 소비해
'영상(Miles/GARCH)의 변동성 군집 주장을 우리 지수로 검증' + '크래시 카탈로그' +
'오늘이 역사적으로 얼마나 극단인가(1년이 아니라 수십 년 백분위)'를 낸다.

성격: **측정·분석 전용.** 룰 안 바꾼다. 크래시 TF의 '학술 근거'와 '역사 유사국면'을
정량으로 뒷받침하는 컨텍스트 산출기.

산출(심볼별):
  ① RV20 전이력 분포 + 오늘 백분위(작년이 아니라 수십 년 기준)
  ② 변동성 군집 검증 — P(급변) 무조건 vs P(급변|어제 급변). 영상 "10%→30%(3배)" 재현
  ③ 크래시 카탈로그 — 최악 일간 하락 top N + 그 전후 변동성
  ④ GARCH 요약(선행 예측·지속성) — garch.py 재사용

사용:
  python3 history_analysis.py                 # 코스피(기본)
  python3 history_analysis.py --symbol NVDA
  python3 history_analysis.py --symbol ^KS11 --threshold 3.0 --top 15
  python3 history_analysis.py --json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics

try:
    import history_backfill as hb
    import garch
except ImportError:
    hb = garch = None

TRADING_DAYS = 252


def load(symbol: str):
    rows = hb.load_cached(symbol) if hb else []
    return rows  # [(date, close)]


def daily_pct_returns(rows):
    out = []
    for i in range(1, len(rows)):
        p0, p1 = rows[i - 1][1], rows[i][1]
        if p0 and p1 and p0 > 0:
            out.append((rows[i][0], 100.0 * (p1 / p0 - 1)))
    return out


def rv20_series(rets_only, window=20):
    """뒤돌아본 window일 실현변동성(연율%)."""
    out = []
    for i in range(window, len(rets_only) + 1):
        seg = rets_only[i - window:i]
        sd = statistics.stdev(seg) if len(seg) > 1 else 0.0
        out.append(sd * math.sqrt(TRADING_DAYS))
    return out


def percentile_rank(series, value):
    if not series:
        return None
    below = sum(1 for v in series if v <= value)
    return round(100.0 * below / len(series), 1)


def clustering_test(dated_rets, threshold):
    """변동성 군집: P(|r|>thr) 무조건 vs 어제 |r|>thr였을 때. 영상 '10%→30%' 재현."""
    rets = [r for _, r in dated_rets]
    n = len(rets)
    big = [abs(r) > threshold for r in rets]
    uncond = sum(big) / n if n else 0
    # 어제 big였던 날들 중 오늘도 big인 비율
    after_big = [big[i] for i in range(1, n) if big[i - 1]]
    cond = (sum(after_big) / len(after_big)) if after_big else 0
    after_calm = [big[i] for i in range(1, n) if not big[i - 1]]
    cond_calm = (sum(after_calm) / len(after_calm)) if after_calm else 0
    return {
        "threshold": threshold, "n": n,
        "p_uncond": round(uncond * 100, 1),
        "p_after_big": round(cond * 100, 1),
        "p_after_calm": round(cond_calm * 100, 1),
        "ratio": round(cond / uncond, 2) if uncond else None,
    }


def crash_catalog(dated_rets, top=10):
    worst = sorted(dated_rets, key=lambda x: x[1])[:top]
    return [{"date": d, "ret": round(r, 2)} for d, r in worst]


def analyze(symbol: str, threshold: float, top: int) -> dict:
    rows = load(symbol)
    if len(rows) < 300:
        return {"symbol": symbol, "ok": False, "reason": f"이력 부족({len(rows)})"}
    dated_rets = daily_pct_returns(rows)
    rets_only = [r for _, r in dated_rets]
    rv = rv20_series(rets_only)
    today_rv = rv[-1] if rv else None
    res = {
        "symbol": symbol, "ok": True,
        "first": rows[0][0], "last": rows[-1][0], "days": len(rows),
        "years": round(len(rows) / TRADING_DAYS, 1),
        "today_rv20": round(today_rv, 1) if today_rv else None,
        "rv20_pctile_fullhist": percentile_rank(rv, today_rv),
        "rv20_min": round(min(rv), 1), "rv20_median": round(statistics.median(rv), 1),
        "rv20_max": round(max(rv), 1),
        "clustering": clustering_test(dated_rets, threshold),
        "worst_days": crash_catalog(dated_rets, top),
    }
    if garch:
        try:
            g = garch.fit_forecast(symbol)
            if g.get("ok"):
                res["garch"] = {"forecast_vol": g["forecast_vol"],
                                "persistence": g["persistence"],
                                "shock_w": g["shock_w"], "memory_w": g["memory_w"],
                                "longrun_vol": g["longrun_vol"], "regime": g["regime"]}
        except Exception:
            pass
    return res


def fmt(r: dict) -> str:
    if not r.get("ok"):
        return f"{r['symbol']}: {r.get('reason')}"
    L = []
    L.append(f"■ {r['symbol']} — {r['first']}~{r['last']} ({r['days']:,}일·{r['years']}년)")
    L.append(f"  RV20 오늘 {r['today_rv20']}% = 전이력 {r['rv20_pctile_fullhist']}%ile "
             f"(전이력 min {r['rv20_min']} / 중앙 {r['rv20_median']} / max {r['rv20_max']}%)")
    c = r["clustering"]
    L.append(f"  변동성 군집(|일간|>{c['threshold']}%): 무조건 {c['p_uncond']}% → "
             f"급변 다음날 {c['p_after_big']}% (×{c['ratio']}) / 차분 다음날 {c['p_after_calm']}%")
    if "garch" in r:
        g = r["garch"]
        L.append(f"  GARCH 내일예측 {g['forecast_vol']}% [{g['regime']}] · 지속성 {g['persistence']} · "
                 f"충격/메모리 {g['shock_w']}/{g['memory_w']} · 장기평균 {g['longrun_vol']}%")
    L.append(f"  최악 일간 하락 top{len(r['worst_days'])}: " +
             ", ".join(f"{w['date']}({w['ret']}%)" for w in r["worst_days"][:6]))
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="장기 이력 변동성·크래시 분석 (측정 전용·stdlib)")
    ap.add_argument("--symbol", "--tickers", default="^KS11", help="Yahoo 심볼(기본 코스피)")
    ap.add_argument("--threshold", type=float, default=3.0, help="'급변' 일간 절대%% 기준")
    ap.add_argument("--top", type=int, default=10, help="크래시 카탈로그 개수")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if hb is None:
        print("history_backfill 미탑재 — 먼저 python3 history_backfill.py 실행")
        return 1
    r = analyze(args.symbol, args.threshold, args.top)
    print(json.dumps(r, ensure_ascii=False, indent=1) if args.json else fmt(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
