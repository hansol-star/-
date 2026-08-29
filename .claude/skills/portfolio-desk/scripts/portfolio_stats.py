#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
portfolio_stats.py — 상관·베타·변동성·낙폭 (gs-quant econometrics 방법론 이식)

왜 있나 [8/23 신설 — 정훈 지시 "골드만삭스 깃헙 코드 참고"]
────────────────────────────────────────────────────────────
우리는 집중도를 **비중과 사람이 붙인 섹터 라벨**로만 재왔다. risk-desk 지시문에도
*"memory-bet overlap(삼성·NVDA·MU·AVGO·SK하이닉스)"*이 적혀 있는데, 그걸 **눈대중**으로 본다.

문제는 라벨이 분산을 결정하지 않는다는 것이다. '빅테크'와 '반도체'로 갈라 적어도 같이 떨어지면
분산이 아니다. **분산이 진짜인지 결정하는 건 상관계수 하나뿐인데 우리 시스템엔 그 축이 없었다.**

`goldmansachs/gs-quant`(Apache-2.0, v2.1.4) `gs_quant/timeseries/econometrics.py`의 정의를
**stdlib로 다시 구현**했다(코드 복사가 아니라 수식 이식 — gs-quant는 pandas/numpy 의존이고
우리 레포는 로컬 이전 대비 stdlib 전용이라 import 자체가 불가):

  · volatility   sample std(N-1) of simple returns × √252 × 100   (20% → 20.0)
  · correlation  Pearson on simple returns (표본평균 사용)
  · beta         Cov(R,S)/Var(S) on simple returns
  · max_drawdown min(x_t / rolling_max − 1)  → 비율 반환(-0.2 = 20% 낙폭)

여기에 우리 포트폴리오용으로 두 개를 더 얹는다:
  · **포트폴리오 변동성** σp = √(wᵀΣw) — 개별 변동성의 가중합이 아니다(상관이 낮으면 그보다 작다)
  · **실효 분산 종목 수(ENB)** = (Σw)²/(wᵀΣw)를 상관행렬로 정규화한 값
    → "14종목 보유"가 실제로 몇 종목어치 분산인지. 이 숫자가 낮으면 종목 수는 착시다.

⚠️ **측정 전용 — 어떤 룰도 바꾸지 않는다.** 상관이 높다고 파는 게 아니라, 우리가 분산됐다고
   믿고 있었는지 아닌지를 숫자로 보여줄 뿐이다. 판정은 룰, 결정은 정훈.
⚠️ **합성 시계열이다** — 현재 비중을 과거에 고정해 되돌린 것이지 실제 계좌 수익률이 아니다.
   라벨을 항상 같이 쓴다. 실제 계좌 기준으로의 승격은 **로컬 이전·토스 API로 매수 이력을
   수집한 뒤**다(정훈 8/23 지시, CLAUDE.md 실행환경 §대기목록 1번) — 그 전엔 시도하지 않는다.

사용법:
  python3 portfolio_stats.py                 # 요약 (60일 창)
  python3 portfolio_stats.py --window 120    # 창 변경
  python3 portfolio_stats.py --corr          # 상관행렬 전체
  python3 portfolio_stats.py --json          # 기계 출력 (build_app_data가 소비)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
HISTORY = os.path.join(REPO, "data", "history")
PORTFOLIO_JSON = os.path.join(HERE, "..", "portfolio.json")
DATA_JS = os.path.join(REPO, "app", "data.js")
KST = dt.timezone(dt.timedelta(hours=9))

TRADING_DAYS = 252          # gs-quant AnnualizationFactor.DAILY
BENCHMARKS = [("^KS11", "코스피"), ("^GSPC", "S&P500"), ("^SOX", "필라델피아반도체"), ("KRW=X", "원/달러")]


def cache_path(symbol: str) -> str:
    """vol_gauge._cache_path와 동일 규약 — 심볼→파일명(^·=·/ 를 _ 로)."""
    safe = symbol.replace("^", "_").replace("=", "_").replace("/", "_")
    return os.path.join(HISTORY, f"{safe}.csv")


def load_series(symbol: str) -> dict:
    """{date: close}. 캐시가 없으면 빈 dict(네트워크 호출 안 함 — 오프라인 계산 도구)."""
    p = cache_path(symbol)
    if not os.path.exists(p):
        return {}
    out = {}
    try:
        with open(p, encoding="utf-8") as f:
            next(f, None)
            for ln in f:
                d, _, c = ln.strip().partition(",")
                if c:
                    try:
                        out[d] = float(c)
                    except ValueError:
                        continue
    except OSError:
        return {}
    return out


def simple_returns(series: dict, dates: list[str]) -> list[float]:
    """gs-quant Returns.SIMPLE — R_t = X_t/X_{t-1} − 1."""
    out = []
    for i in range(1, len(dates)):
        p0, p1 = series[dates[i - 1]], series[dates[i]]
        out.append((p1 - p0) / p0 if p0 else 0.0)
    return out


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def stdev(v: list[float], sample: bool = True) -> float:
    """gs-quant 기본값 assume_zero_mean=False → 표본 표준편차(N-1)."""
    n = len(v)
    if n < 2:
        return 0.0
    m = _mean(v)
    den = n - 1 if sample else n
    return math.sqrt(sum((x - m) ** 2 for x in v) / den)


def volatility(rets: list[float]) -> float:
    """연환산 실현변동성(%). gs-quant: std × √252 × 100."""
    return stdev(rets) * math.sqrt(TRADING_DAYS) * 100


def covariance(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    ma, mb = _mean(a[:n]), _mean(b[:n])
    return sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (n - 1)


def correlation(a: list[float], b: list[float]) -> float | None:
    sa, sb = stdev(a), stdev(b)
    if not sa or not sb:
        return None
    return covariance(a, b) / (sa * sb)


def beta(x: list[float], bench: list[float]) -> float | None:
    """gs-quant beta = Cov(R,S)/Var(S)."""
    vb = stdev(bench) ** 2
    if not vb:
        return None
    return covariance(x, bench) / vb


def max_drawdown(levels: list[float]) -> float:
    """gs-quant max_drawdown — min(x_t/누적최대 − 1). 비율 반환(-0.2 = -20%)."""
    peak, worst = None, 0.0
    for v in levels:
        peak = v if peak is None else max(peak, v)
        if peak:
            worst = min(worst, v / peak - 1)
    return worst


def own_calendar_vol(series: dict, window: int) -> float | None:
    """변동성은 **그 종목의 자기 거래일**로 잰다.

    왜 나눠 재는가 [8/23]: 상관·베타는 같은 날끼리 맞춰야 하므로 KR·US 거래일 교집합이 필요한데,
    교집합을 쓰면 한쪽만 열린 날이 빠지면서 일부 수익률이 **2~3거래일치를 하루로** 담는다.
    그 상태로 √252를 곱하면 변동성이 통째로 부풀려진다(실측: 78→60일로 18일이 빠져 약 1.14배 과대).
    ⇒ 변동성만 자기 달력으로 되돌린다. 교집합은 상관·베타에만 쓴다.
    """
    ds = sorted(series)[-(window + 1):]
    if len(ds) < 20:
        return None
    return volatility(simple_returns(series, ds))


def align(symbols: list[str], window: int) -> tuple[list[str], dict]:
    """전 종목이 공통으로 가진 마지막 window+1 거래일로 정렬. 짧은 종목이 창을 결정한다."""
    series = {s: load_series(s) for s in symbols}
    have = {s: v for s, v in series.items() if len(v) > 5}
    if not have:
        return [], {}
    common = set.intersection(*(set(v) for v in have.values()))
    dates = sorted(common)[-(window + 1):]
    return dates, have


def analyze(holdings: list[dict], window: int = 60) -> dict:
    """holdings = build_app_data 종목 dict(ticker·label·value_krw 필요)."""
    hs = [h for h in holdings if h.get("value_krw") and h.get("ticker")]
    syms = [h["ticker"] for h in hs]
    dates, series = align(syms + [b[0] for b in BENCHMARKS], window)
    covered = [h for h in hs if h["ticker"] in series]
    missing = [h["label"] for h in hs if h["ticker"] not in series]
    if len(dates) < 20 or len(covered) < 2:
        return {"status": "unavailable",
                "reason": f"공통 거래일 {len(dates)}일·종목 {len(covered)}개 — 계산 불가",
                "missing": missing}

    rets = {h["ticker"]: simple_returns(series[h["ticker"]], dates) for h in covered}
    tot = sum(h["value_krw"] for h in covered)
    w = {h["ticker"]: h["value_krw"] / tot for h in covered}
    tk2label = {h["ticker"]: h["label"] for h in covered}
    tks = [h["ticker"] for h in covered]

    # 변동성 = 자기 거래일 기준(위 주석). 실패 시에만 교집합 수익률로 폴백하고 그 사실을 표시한다.
    vols, vol_fallback = {}, []
    for t in tks:
        v = own_calendar_vol(series[t], window)
        if v is None:
            v = volatility(rets[t]); vol_fallback.append(tk2label[t])
        vols[t] = v
    corr = {a: {b: correlation(rets[a], rets[b]) for b in tks} for a in tks}

    # 포트폴리오 변동성 σp = √(wᵀΣw) — 개별 변동성의 가중합이 아니다
    var_p = 0.0
    for a in tks:
        for b in tks:
            c = corr[a][b]
            if c is None:
                continue
            var_p += w[a] * w[b] * (vols[a] / 100) * (vols[b] / 100) * c
    vol_p = math.sqrt(max(var_p, 0.0)) * 100
    vol_weighted = sum(w[t] * vols[t] for t in tks)          # 상관을 무시했을 때
    # 분산비율 = 가중평균 변동성 / 포트 변동성 (1이면 분산 효과 0)
    div_ratio = vol_weighted / vol_p if vol_p else None
    # 실효 분산 종목 수 — 분산비율의 제곱(등가중·등변동성 가정 하의 유효 자산 수)
    enb = div_ratio ** 2 if div_ratio else None
    # 비중만 본 실효 종목수(역-HHI) — 상관 기반 ENB와의 **차이가 정보**다
    hhi = sum(w[t] ** 2 for t in tks)
    enb_weight = 1 / hhi if hhi else None

    # 상관 상위 쌍 (분산 착시의 실체)
    pairs = []
    for i, a in enumerate(tks):
        for b in tks[i + 1:]:
            c = corr[a][b]
            if c is not None:
                pairs.append({"a": tk2label[a], "b": tk2label[b], "corr": round(c, 3),
                              "w_sum": round((w[a] + w[b]) * 100, 1)})
    pairs.sort(key=lambda p: -p["corr"])

    # 벤치마크 베타 — 합성 포트 수익률 대비
    port_ret = [sum(w[t] * rets[t][i] for t in tks) for i in range(len(dates) - 1)]
    bench = {}
    for sym, label in BENCHMARKS:
        if sym not in series:
            continue
        br = simple_returns(series[sym], dates)
        bv = own_calendar_vol(series[sym], window)   # 벤치 변동성도 자기 달력
        bench[label] = {
            "beta": round(beta(port_ret, br), 3) if beta(port_ret, br) is not None else None,
            "corr": round(correlation(port_ret, br), 3) if correlation(port_ret, br) is not None else None,
            "vol": round(bv if bv is not None else volatility(br), 1),
        }

    # 합성 포트 레벨(현재 비중 고정) → 낙폭
    lvl, v = [1.0], 1.0
    for r in port_ret:
        v *= (1 + r)
        lvl.append(v)
    mdd = max_drawdown(lvl)

    return {
        "status": "live",
        "window": len(dates) - 1,
        "from": dates[0], "to": dates[-1],
        "holdings": len(covered), "missing": missing,
        "portfolio_vol": round(vol_p, 1),
        "weighted_vol": round(vol_weighted, 1),
        "diversification_ratio": round(div_ratio, 3) if div_ratio else None,
        "effective_bets": round(enb, 2) if enb else None,
        "effective_bets_weight_only": round(enb_weight, 2) if enb_weight else None,
        "enb_note": ("상관 기반 ENB = 분산비율²(등가중·등변동성 가정하의 근사). "
                     "비중만 본 역-HHI와 갈리면 그 차이가 **라벨로는 안 보이던 동조**다."),
        "vol_fallback": vol_fallback,
        "max_drawdown_pct": round(mdd * 100, 1),
        "period_return_pct": round((lvl[-1] - 1) * 100, 1),
        "benchmarks": bench,
        "vols": [{"label": tk2label[t], "ticker": t, "vol": round(vols[t], 1),
                  "weight": round(w[t] * 100, 1)} for t in
                 sorted(tks, key=lambda t: -vols[t])],
        "top_pairs": pairs[:8],
        "matrix": {tk2label[a]: {tk2label[b]: (round(corr[a][b], 2) if corr[a][b] is not None else None)
                                 for b in tks} for a in tks},
        "caveat": ("현재 비중을 과거에 고정한 **합성 시계열** — 실제 계좌 수익률이 아니다"
                   "(실제 트랙레코드는 체결 원장이 6/13 이전까지 채워져야 나온다). 측정 전용."),
        "method": ("gs-quant v2.1.4 econometrics 정의 이식(Apache-2.0) — 수식만, 코드 복사 아님. "
                   "변동성은 각 심볼의 자기 거래일, 상관·베타는 공통 거래일 교집합(정렬이 필수라)."),
    }


def _load_holdings() -> list[dict]:
    raw = open(DATA_JS, encoding="utf-8").read()
    return json.loads(raw[raw.index("{"):raw.rindex("}") + 1]).get("holdings") or []


def main() -> int:
    ap = argparse.ArgumentParser(description="상관·베타·변동성·낙폭 (측정 전용·stdlib·오프라인)")
    ap.add_argument("--window", type=int, default=60, help="거래일 창 (기본 60)")
    ap.add_argument("--corr", action="store_true", help="상관행렬 전체 출력")
    ap.add_argument("--json", action="store_true", help="기계 출력")
    a = ap.parse_args()

    try:
        holdings = _load_holdings()
    except Exception as e:  # noqa: BLE001
        print(f"❌ app/data.js를 읽지 못했습니다 ({e}) — build_app_data.py를 먼저 돌리세요.", file=sys.stderr)
        return 1
    r = analyze(holdings, a.window)
    r["as_of"] = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if r["status"] != "live":
        print(f"❌ {r['reason']}")
        return 1

    print(f"── 포트폴리오 통계 ({r['from']} ~ {r['to']} · {r['window']}거래일 · 보유 {r['holdings']}) ──")
    print(f"  포트 변동성   {r['portfolio_vol']:>6.1f}%   (가중평균 {r['weighted_vol']:.1f}% — 상관 무시 시)")
    print(f"  분산비율      {r['diversification_ratio']:>6.3f}   실효 분산 종목수 **{r['effective_bets']}**"
          f"  (비중만 보면 {r['effective_bets_weight_only']})")
    print(f"                → {r['holdings']}종목 보유가 비중상 {r['effective_bets_weight_only']}종목어치, "
          f"**상관까지 보면 {r['effective_bets']}종목어치**")
    print(f"  최대낙폭      {r['max_drawdown_pct']:>6.1f}%   기간수익 {r['period_return_pct']:+.1f}%")
    print("\n  벤치마크 베타·상관")
    for k, v in r["benchmarks"].items():
        print(f"    {k:<14} β {v['beta']:>6}   ρ {v['corr']:>6}   (벤치 변동성 {v['vol']}%)")
    print("\n  종목 변동성 (높은 순)")
    for x in r["vols"]:
        print(f"    {x['label']:<10} {x['vol']:>6.1f}%  비중 {x['weight']:>5.1f}%")
    print("\n  상관 상위 쌍 — 분산 착시의 실체")
    for p in r["top_pairs"]:
        print(f"    {p['a']:<10} ↔ {p['b']:<10} ρ {p['corr']:>6.3f}   합산비중 {p['w_sum']:>5.1f}%")
    if r["missing"]:
        print(f"\n  ⚠️ 시계열 없음(계산 제외): {', '.join(r['missing'])}")
    if a.corr:
        labels = list(r["matrix"])
        print("\n  상관행렬")
        print("    " + "".join(f"{l[:4]:>7}" for l in labels))
        for l in labels:
            print(f"    {l[:4]:<4}" + "".join(
                f"{(r['matrix'][l][c] if r['matrix'][l][c] is not None else 0):>7.2f}" for c in labels))
    print(f"\n  ⚠️ {r['caveat']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
