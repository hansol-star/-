#!/usr/bin/env python3
"""일회성 검정 — 추세 규칙 3종(200일선·시계열 모멘텀·52주 고점 근접도, 11/1 공부).

**측정 전용 — 어떤 룰도 바꾸지 않는다.** 사전등록 = trial_registry `trend_study` 가족(13변형).

  · 신호 = 월말 종가까지의 정보. 그다음 날 종가에 집행(1일 지연) · 왕복 0.2% · 현금 수익 0.
  · 대조군 ① 같은 평균 노출의 상시 보유(샤프 = 매수보유) ② 월별 신호를 원형 이동한 위약 500회.
  · ③ 18개 시장 부호검정 ④ 2008 전/후(Faber 2007 발표 뒤 감쇠) ⑤ CSCV로 PBO.
  ⚠️ 가격지수(배당 제외) — 현금 쪽이 약간 유리 · 고금리 시장은 현금 0이라 반대로 불리.

  python trend_rules_test.py [--save 경로.json] | --selftest
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import os
import sys

try:
    import numpy as np
except ModuleNotFoundError:            # numpy 없는 환경(클라우드 컨테이너)에서도 게이트는 통과해야 한다
    np = None                          # ↑ 11/7: 모듈 최상위 import라 selfcheck의 import·--help 단계가 FAIL이었다.
                                       #   같은 numpy 사용 스크립트(memory_embed·risk_cap_test)는 함수 안에서
                                       #   늦게 import해 이 문제가 없었다 — 그 관례를 맞춘다(annotations는 이미 postponed).

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *([os.pardir] * 4)))
HIST = os.path.join(ROOT, "data", "history")
MARKETS = [("코스피", "_KS11"), ("S&P500", "_GSPC"), ("닛케이", "_N225"), ("항셍", "_HSI"), ("대만", "_TWII"),
           ("독일", "_GDAXI"), ("영국", "_FTSE"), ("브라질", "_BVSP"), ("인도", "_BSESN"), ("인니", "_JKSE"),
           ("말레이", "_KLSE"), ("멕시코", "_MXX"), ("호주", "_AXJO"), ("캐나다", "_GSPTSE"), ("터키", "XU100.IS"),
           ("이스라엘", "_TA125.TA"), ("아르헨", "_MERV"), ("상하이", "000001.SS")]
GRID = [("ma", n) for n in (50, 100, 150, 200, 250, 300)] + [("mom", n) for n in (3, 6, 9, 12)] \
    + [("high", x) for x in (85, 90, 95)]
PRIMARY = [("ma", 200), ("mom", 12), ("high", 90)]
COST = 0.001  # 편도
WARM = 320
DAY = 252


def load(sym: str) -> tuple[list[str], np.ndarray]:
    dates, px = [], []
    with open(os.path.join(HIST, sym + ".csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                v = float(r["close"])
            except (TypeError, ValueError):
                continue
            if v > 0:
                dates.append(r["date"])
                px.append(v)
    return dates, np.array(px)


def month_ends(dates: list[str]) -> np.ndarray:
    return np.array([i for i in range(len(dates) - 1) if dates[i][:7] != dates[i + 1][:7]])


def signal(px: np.ndarray, me: np.ndarray, kind: str, n: int) -> np.ndarray:
    """월말 i까지의 값만 읽는다(px[:i+1])."""
    out = np.zeros(len(me))
    for j, i in enumerate(me):
        if i < WARM:
            out[j] = np.nan
        elif kind == "ma":
            out[j] = px[i] > px[i - n + 1:i + 1].mean()
        elif kind == "mom":
            out[j] = px[i] > px[i - n * 21]
        else:
            out[j] = px[i] >= px[i - DAY + 1:i + 1].max() * n / 100
    return out


def daily_pos(n: int, me: np.ndarray, sig: np.ndarray) -> np.ndarray:
    """월말 d 신호 → d+1 종가 집행 → d+2 수익부터 보유. 시작 전은 NaN."""
    pos = np.full(n, np.nan)
    for j, i in enumerate(me):
        end = me[j + 1] + 2 if j + 1 < len(me) else n
        pos[i + 2:end] = sig[j]
    return pos


def run(ret: np.ndarray, pos: np.ndarray) -> np.ndarray:
    p = np.nan_to_num(pos)
    prev = np.concatenate([[0.0], p[:-1]])
    return p * ret - np.abs(p - prev) * COST


def sharpe(r: np.ndarray) -> float:
    s = r.std()
    return float(r.mean() / s * math.sqrt(DAY)) if s > 0 else 0.0


def cagr(r: np.ndarray) -> float:
    return float(np.exp(np.log1p(r).sum() * DAY / len(r)) - 1)


def mdd(r: np.ndarray) -> float:
    eq = np.cumprod(1 + r)
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def evaluate(dates, px, kind, n, rng, draws=500):
    ret = np.concatenate([[0.0], px[1:] / px[:-1] - 1])
    me = month_ends(dates)
    sig = signal(px, me, kind, n)
    ok = ~np.isnan(sig)
    me, sig = me[ok], sig[ok]
    pos = daily_pos(len(px), me, sig)
    live = ~np.isnan(pos)
    r_s, r_b = run(ret, pos)[live], ret[live]
    w = float(pos[live].mean())
    r_c = w * r_b
    placebo = []
    for _ in range(draws):
        k = int(rng.integers(12, max(13, len(sig) - 12)))
        placebo.append(sharpe(run(ret, daily_pos(len(px), me, np.roll(sig, k)))[live]))
    d = np.array(dates)[live]
    post = d >= "2008-01-01"
    row = dict(start=str(d[0]), exposure=round(w, 3), switches=int(np.abs(np.diff(sig)).sum()),
               sharpe=round(sharpe(r_s), 3), sharpe_bh=round(sharpe(r_b), 3),
               cagr=round(cagr(r_s) * 100, 2), cagr_bh=round(cagr(r_b) * 100, 2), cagr_ctrl=round(cagr(r_c) * 100, 2),
               mdd=round(mdd(r_s) * 100, 1), mdd_bh=round(mdd(r_b) * 100, 1), mdd_ctrl=round(mdd(r_c) * 100, 1),
               placebo_pct=round(float(np.mean(np.array(placebo) < sharpe(r_s))) * 100, 1) if placebo else None,
               d_pre=round(sharpe(r_s[~post]) - sharpe(r_b[~post]), 3) if (~post).sum() > 500 else None,
               d_post=round(sharpe(r_s[post]) - sharpe(r_b[post]), 3))
    return row, dict(zip(d.tolist(), (r_s - r_c).tolist()))


def pbo(mat: np.ndarray, s: int = 12) -> dict:
    """CSCV(Bailey et al.) — 월별 초과수익 T×N을 s조각으로 나눠 IS 최고가 OOS 중앙 아래인 비율."""
    T = mat.shape[0] // s * s
    parts = np.array_split(np.arange(T), s)
    logits, oos = [], []
    for c in itertools.combinations(range(s), s // 2):
        o = [i for i in range(s) if i not in c]
        a, b = np.concatenate([parts[i] for i in c]), np.concatenate([parts[i] for i in o])
        sa, sb = mat[a].mean(0) / mat[a].std(0), mat[b].mean(0) / mat[b].std(0)
        best = int(np.argmax(sa))
        w = ((sb < sb[best]).sum() + 1) / (mat.shape[1] + 1)
        logits.append(math.log(w / (1 - w)))
        oos.append(sb[best])
    return dict(pbo=round(float(np.mean(np.array(logits) <= 0)), 3), oos_mean_sr=round(float(np.mean(oos)) * math.sqrt(12), 3))


def sign_p(k, n):
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def selftest() -> int:
    dates, px = load("_KS11")
    me = month_ends(dates)
    full = {g: signal(px, me, *g) for g in GRID}
    k = len(px) * 2 // 3
    cut = me[me < k - 1]
    for g in GRID:
        assert np.array_equal(signal(px[:k], cut, *g), full[g][:len(cut)], equal_nan=True), g
    sig = full[("ma", 200)]
    ok = ~np.isnan(sig)
    m2, s2 = me[ok], sig[ok]
    pos = daily_pos(len(px), m2, s2)
    i = int(m2[100])
    assert pos[i + 1] == s2[99] and pos[i + 2] == s2[100], "월말 신호는 d+2 수익부터"
    print("selftest OK")
    return 0


def _require_numpy() -> None:
    if np is None:
        sys.exit("numpy가 필요하다 — 이 검정은 numpy 환경에서만 돈다(pip install numpy). "
                 "게이트(compile·import·--help)는 numpy 없이도 통과한다.")


def main() -> int:
    ap = argparse.ArgumentParser(description="추세 규칙 3종 검정(측정 전용)")
    ap.add_argument("--save", help="결과 JSON 경로")
    ap.add_argument("--selftest", action="store_true", help="룩어헤드 불변 검사")
    a = ap.parse_args()
    _require_numpy()
    if a.selftest:
        return selftest()
    rng = np.random.default_rng(20261101)
    data = {lab: load(sym) for lab, sym in MARKETS}
    out, excess = {}, {}
    for g in GRID:
        key = f"{g[0]}{g[1]}"
        rows, ser = {}, {}
        for lab, (dates, px) in data.items():
            rows[lab], ser[lab] = evaluate(dates, px, g[0], g[1], rng, 500 if g in PRIMARY else 0)
        out[key], excess[key] = rows, ser
        v = list(rows.values())
        k = sum(x["sharpe"] > x["sharpe_bh"] for x in v)
        print(f"{key:7} 샤프↑ {k:2}/{len(v)} p={sign_p(k, len(v)):.4f} · 중앙Δ샤프 {np.median([x['sharpe'] - x['sharpe_bh'] for x in v]):+.3f}"
              f" · CAGR>대조 {sum(x['cagr'] > x['cagr_ctrl'] for x in v):2} · CAGR>보유 {sum(x['cagr'] > x['cagr_bh'] for x in v):2}"
              f" · MDD개선 {sum(x['mdd'] > x['mdd_bh'] for x in v):2} · MDD>대조 {sum(x['mdd'] > x['mdd_ctrl'] for x in v):2} · 노출 {np.median([x['exposure'] for x in v]):.2f}")
    res = {}
    for g in PRIMARY:
        key = f"{g[0]}{g[1]}"
        v = out[key]
        pl = sum(x["placebo_pct"] >= 95 for x in v.values())
        pre = [x["d_pre"] for x in v.values() if x["d_pre"] is not None]
        post = [x["d_post"] for x in v.values()]
        res[key] = dict(placebo95=pl, pre_pos=sum(x > 0 for x in pre), pre_n=len(pre), post_pos=sum(x > 0 for x in post),
                        post_n=len(post), pre_med=round(float(np.median(pre)), 3), post_med=round(float(np.median(post)), 3))
        print(f"\n[{key}] 위약95%↑ {pl}/18 · 2008전 {res[key]['pre_pos']}/{len(pre)}({res[key]['pre_med']:+.3f}) · 2008후 {res[key]['post_pos']}/{len(post)}({res[key]['post_med']:+.3f})")
        for lab in ("코스피", "S&P500"):
            x = v[lab]
            print(f"  {lab}: 샤프 {x['sharpe']}/{x['sharpe_bh']} · CAGR {x['cagr']}/보유 {x['cagr_bh']}/대조 {x['cagr_ctrl']} · MDD {x['mdd']}/{x['mdd_bh']}/대조 {x['mdd_ctrl']} · 위약 {x['placebo_pct']} · 전환 {x['switches']}")
    keys = list(excess)
    months = sorted({d[:7] for s in excess[keys[0]].values() for d in s if d >= "2000-01"})
    idx = {m: i for i, m in enumerate(months)}
    mat = np.zeros((len(months), len(keys)))
    cnt = np.zeros_like(mat)
    for c, key in enumerate(keys):
        for ser in excess[key].values():
            for d, x in ser.items():
                if d[:7] in idx:
                    mat[idx[d[:7]], c] += x
                    cnt[idx[d[:7]], c] += 1
    mat = mat / np.maximum(1, cnt / 21)
    p = pbo(mat)
    print(f"\nPBO(13변형·시장 동일가중·2000~) = {p['pbo']} · 선택 변형 OOS 샤프 {p['oos_mean_sr']}")
    if a.save:
        with open(a.save, "w", encoding="utf-8") as f:
            json.dump(dict(primary=res, pbo=p, table=out), f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
