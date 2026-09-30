#!/usr/bin/env python3
"""risk_cap_test.py — 단일종목 '위험 기여 상한'이 '비중 상한'보다 나은가 (8/5 3단 절차 + 9/22 대조군)

■ 왜 만들었나 [2026-09-30 · 정훈 승인 "B 바로 진행해" — 시스템 평가 제안 B]
   단일종목 상한 25%는 **비중** 기준이라 변동성을 모른다. 9/30 실측: 삼성 비중 15%인데 포트 위험 약 40%,
   NVDA는 비중·변동성 둘 다 최대. 외부 근거(arXiv 2609.05663: 실돈 LLM 에이전트의 사이징이 '변동성 무시')와
   같은 모양의 결함이다. → "종목 하나의 위험 기여를 30%로 묶으면 더 나은가"를 룰 후보로 올리기 전에 검정한다.

■ 가설·변형 (사전 등록)
   BASE = 목표 비중(집중형 무작위) + 비중 상한 25%        ← 현행 룰
   RC30 = BASE를 출발점으로, 과거 252일 공분산 기준 위험 기여 > 30%인 종목을 30%까지 깎고 나머지에 비례 재배분
   CTRL = **대조군** — RC30과 같은 만큼 집중도(허핀달)를 줄이되 공분산을 쓰지 않는다(동일가중 쪽으로 λ 수축)
          → RC30이 CTRL을 못 이기면 효과는 '위험 신호'가 아니라 '그냥 분산'이다(9/22 d208 교훈).
   리밸런싱 21거래일 · 무거래비용 · 시장별 현지통화(환 제외).
   1차 지표 = Sharpe 차 · 최대낙폭 차. 통과 조건 = ①집계 ②연도 에피소드 ③시장 횡단면(KR·US)에서
   RC30이 BASE와 CTRL **둘 다**를 같은 방향으로 이길 것.

■ 룩어헤드
   t일 종가에 비중을 정할 때 공분산은 t까지의 수익률만 쓰고, 보유 수익은 t+1부터 센다.

■ ⚠️ 한계
   · **생존 편향** — 지금 추적 중인 종목(살아남은 대형주)만 쓴다.
   · 무작위 포트이지 우리 포트가 아니다(일반 명제 검정). 거래비용·세금·분수주 제약 없음.
   · 측정 전용 — 어떤 룰도 바꾸지 않는다. 통과해도 룰 채택은 정훈 승인.

사용:
  python risk_cap_test.py                 # 시장당 200개 무작위 포트
  python risk_cap_test.py --n 400 --k 8 --cap 0.30
정본 결과 = docs/research/risk_cap_test_2026-09-30.md
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
HIST = os.path.join(ROOT, "data", "history")

EXCLUDE = {"VOO", "SPCX", "GEV", "454910.KS", "329180.KS", "BTC-USD", "BZ_F", "CL_F", "GC_F",
           "DX-Y.NYB", "KRW_X", "000001.SS", "XU100.IS", "IONQ", "PLTR"}
START = "2009-01-01"          # 이 날짜 이전 252일 이상 이력이 있는 종목만
LOOKBACK, HOLD, WCAP = 252, 21, 0.25


def market(t: str) -> str:
    return "KR" if t.endswith((".KS", ".KQ")) else "US"


def load() -> dict[str, dict[str, float]]:
    out = {}
    for p in glob.glob(os.path.join(HIST, "*.csv")):
        t = os.path.basename(p)[:-4]
        if t.startswith("_") or t in EXCLUDE:
            continue
        rows = {}
        for r in csv.DictReader(open(p, encoding="utf-8")):
            try:
                v = float(r["close"])
            except (KeyError, TypeError, ValueError):
                continue
            if v > 0:
                rows[r["date"]] = v
        if rows and min(rows) < "2008-01-01":
            out[t] = rows
    return out


def panel(data: dict, tickers: list[str]):
    import numpy as np
    dates = sorted(set.intersection(*(set(data[t]) for t in tickers)))
    dates = [d for d in dates if d >= "2008-01-01"]
    px = np.array([[data[t][d] for t in tickers] for d in dates])
    ret = px[1:] / px[:-1] - 1
    ret = np.clip(ret, -0.5, 1.0)   # 액면분할 미조정 틱 방어
    return dates[1:], ret


def cap_weights(w, cap=WCAP):
    import numpy as np
    w = np.array(w, float)
    for _ in range(100):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        free = ~over & (w < cap)
        if not free.any():
            break
        w[free] += excess * w[free] / w[free].sum()
    return w / w.sum()


def rc(w, cov):
    import numpy as np
    pv = w @ cov @ w
    return w * (cov @ w) / pv if pv > 0 else np.zeros_like(w)


def rc_cap(w0, cov, cap):
    import numpy as np
    w = np.array(w0, float)
    for _ in range(200):
        r = rc(w, cov)
        if r.max() <= cap + 1e-4:
            break
        hi = r > cap
        w[hi] *= (cap / r[hi]) ** 0.5
        w = w / w.sum()
    return w


def shrink_to_match(w0, target_hhi):
    """동일가중 쪽으로 λ만큼 수축해 허핀달을 target에 맞춘다(공분산 미사용 대조군)."""
    import numpy as np
    w0 = np.asarray(w0, float)
    ew = np.full_like(w0, 1 / len(w0))
    lo, hi = 0.0, 1.0
    for _ in range(60):
        lam = (lo + hi) / 2
        h = (((1 - lam) * w0 + lam * ew) ** 2).sum()
        if h > target_hhi:
            lo = lam
        else:
            hi = lam
    return (1 - hi) * w0 + hi * ew


def simulate(dates, ret, w_target, cap):
    """세 변형의 일별 수익률 경로. t 종가에 비중 결정(t까지 수익률만) → t+1..t+HOLD 보유(드리프트)."""
    import numpy as np
    n = ret.shape[0]
    base_w = cap_weights(w_target)
    paths = {"BASE": [], "RC30": [], "CTRL": []}
    days = []
    bind = [0, 0, 0.0]   # [상한이 걸린 리밸런싱 수, 전체 리밸런싱 수, 누적 비중 이동량]
    i0 = next(i for i, d in enumerate(dates) if d >= START)
    i0 = max(i0, LOOKBACK)
    for t in range(i0, n - 1, HOLD):
        cov = np.cov(ret[t - LOOKBACK + 1:t + 1].T)
        w_rc = rc_cap(base_w, cov, cap)
        bind[1] += 1
        if rc(base_w, cov).max() > cap + 1e-4:
            bind[0] += 1
            bind[2] += float(np.abs(w_rc - base_w).sum()) / 2
        w_ct = shrink_to_match(base_w, (w_rc ** 2).sum())
        seg = ret[t + 1:min(t + 1 + HOLD, n)]
        for name, w in (("BASE", base_w), ("RC30", w_rc), ("CTRL", w_ct)):
            val = np.cumprod(1 + seg, axis=0) @ w
            daily = np.diff(np.concatenate([[1.0], val])) / np.concatenate([[1.0], val[:-1]])
            paths[name].extend(daily.tolist())
        days.extend(dates[t + 1:min(t + 1 + HOLD, n)])
    return days, {k: np.array(v) for k, v in paths.items()}, bind


def stats(r):
    import numpy as np
    if len(r) < 20:
        return None
    eq = np.cumprod(1 + r)
    dd = (eq / np.maximum.accumulate(eq) - 1).min()
    vol = r.std() * 252 ** 0.5
    ann = eq[-1] ** (252 / len(r)) - 1
    return {"ann": ann, "vol": vol, "sharpe": (r.mean() * 252) / vol if vol > 0 else 0.0, "mdd": dd}


def main() -> int:
    ap = argparse.ArgumentParser(description="위험 기여 상한 vs 비중 상한 vs 대조군 (측정 전용)")
    ap.add_argument("--n", type=int, default=200, help="시장당 무작위 포트 수")
    ap.add_argument("--k", type=int, default=8, help="포트당 종목 수")
    ap.add_argument("--cap", type=float, default=0.30, help="위험 기여 상한")
    ap.add_argument("--alpha", type=float, default=0.6, help="디리클레 집중도(작을수록 집중)")
    ap.add_argument("--seed", type=int, default=20260930)
    a = ap.parse_args()
    import numpy as np

    data = load()
    rng = random.Random(a.seed)
    nrng = np.random.default_rng(a.seed)
    res = {"KR": [], "US": []}
    binds = {"KR": [0, 0, 0.0], "US": [0, 0, 0.0]}
    yearly = {"KR": {}, "US": {}}
    for mk in ("KR", "US"):
        uni = sorted(t for t in data if market(t) == mk)
        print(f"{mk} 유니버스 {len(uni)}종목: {', '.join(uni)}")
        for _ in range(a.n):
            tick = rng.sample(uni, min(a.k, len(uni)))
            dates, ret = panel(data, tick)
            w = nrng.dirichlet([a.alpha] * len(tick))
            days, p, b = simulate(dates, ret, w, a.cap)
            for j in range(3):
                binds[mk][j] += b[j]
            s = {k: stats(v) for k, v in p.items()}
            if None in s.values():
                continue
            res[mk].append(s)
            yrs = sorted({d[:4] for d in days})
            idx = np.array([d[:4] for d in days])
            for y in yrs:
                m = idx == y
                ys = {k: stats(v[m]) for k, v in p.items()}
                if None in ys.values():
                    continue
                yearly[mk].setdefault(y, []).append(ys)

    def agg(rows, key, a_, b_):
        d = np.array([r[a_][key] - r[b_][key] for r in rows])
        return d.mean(), (d > 0).mean()

    for mk, b in binds.items():
        if b[1]:
            print(f"{mk} 상한 작동 {b[0]}/{b[1]} 리밸런싱({b[0] / b[1]:.0%}) · 작동 시 평균 비중 이동 "
                  f"{(b[2] / b[0] * 100 if b[0] else 0):.1f}%p")
    print(f"\n=== ① 집계 (포트 {sum(len(v) for v in res.values())}개 · 상한 {a.cap:.0%} · k={a.k}) ===")
    print("시장  비교            ΔSharpe(승률)        Δ최대낙폭%p(승률)     Δ변동성%p      Δ연수익%p")
    verdict = {}
    for mk, rows in res.items():
        for a_, b_ in (("RC30", "BASE"), ("RC30", "CTRL"), ("CTRL", "BASE")):
            sh, shw = agg(rows, "sharpe", a_, b_)
            dd, ddw = agg(rows, "mdd", a_, b_)
            vo, _ = agg(rows, "vol", a_, b_)
            an, _ = agg(rows, "ann", a_, b_)
            print(f"{mk}   {a_}−{b_:5s}   {sh:+.3f} ({shw:4.0%})      {dd * 100:+.2f} ({ddw:4.0%})        "
                  f"{vo * 100:+.2f}        {an * 100:+.2f}")
            verdict[(mk, a_, b_)] = (sh, dd)

    print("\n=== ② 연도 에피소드 — RC30이 이긴 해의 비율 (연도별 포트 평균 ΔSharpe>0) ===")
    for mk, ys in yearly.items():
        wins_b = wins_c = tot = 0
        worst = []
        for y, rows in sorted(ys.items()):
            db = np.mean([r["RC30"]["sharpe"] - r["BASE"]["sharpe"] for r in rows])
            dc = np.mean([r["RC30"]["sharpe"] - r["CTRL"]["sharpe"] for r in rows])
            tot += 1
            wins_b += db > 0
            wins_c += dc > 0
            worst.append((db, y))
        worst.sort()
        print(f"{mk}: vs BASE {wins_b}/{tot} · vs CTRL {wins_c}/{tot} · 최악 해(vs BASE) "
              + ", ".join(f"{y} {d:+.2f}" for d, y in worst[:3]))

    print("\n=== ③ 시장 횡단면 — 두 시장에서 같은 방향인가 ===")
    for a_, b_ in (("RC30", "BASE"), ("RC30", "CTRL")):
        sh = [verdict[(mk, a_, b_)][0] for mk in ("KR", "US")]
        dd = [verdict[(mk, a_, b_)][1] for mk in ("KR", "US")]
        same_sh = all(x > 0 for x in sh) or all(x < 0 for x in sh)
        same_dd = all(x > 0 for x in dd) or all(x < 0 for x in dd)
        print(f"{a_}−{b_}: ΔSharpe KR {sh[0]:+.3f} / US {sh[1]:+.3f} → {'같은 방향' if same_sh else '갈림'} · "
              f"Δ최대낙폭 KR {dd[0] * 100:+.2f} / US {dd[1] * 100:+.2f}%p → {'같은 방향' if same_dd else '갈림'}")
    print("\n측정 전용 — 통과해도 룰 채택은 정훈 승인 사항.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
