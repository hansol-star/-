#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diversify_candidates.py — 분산 후보 랭킹 (실효 분산 종목수 개선 기여도)

왜 있나 [8/24 신설 — 정훈 이슈③ "동조 2.3을 줄일 것인가"]
────────────────────────────────────────────────────────────
`portfolio_stats.py`(8/23)가 **"우리는 14종목이지만 실효 분산은 2.3종목"**이라는 진단을 줬다.
그런데 거기서 멈췄다 — **진단은 있는데 처방을 고를 축이 없었다.** "분산 후보가 필요한가,
필요하면 무엇인가"를 물으면 다시 사람의 섹터 라벨 눈대중으로 돌아갔다(8/23이 고친 바로 그 병).

이 도구는 **워치리스트 종목을 '가상으로 편입했을 때 실효 분산 종목수(ENB)가 얼마나 오르는지'**로
줄 세운다. 랭킹 기준은 상관 하나가 아니다 — **낮은 상관 × 낮은(또는 감당 가능한) 변동성**이
같이 있어야 ENB가 오른다. 상관이 낮아도 변동성이 극단이면 편입이 오히려 포트 변동성을 키운다.

계산:
  · 합성 포트 수익률 = Σ wᵢ·rᵢ (현재 비중 고정 — portfolio_stats와 같은 한계)
  · 후보 편입 = 후보에 비중 w_new, 기존은 (1-w_new)로 **비례 축소**(= 전 종목 트림해 재원 마련)
  · ENB = (가중평균 변동성 / 포트 변동성)²  ← portfolio_stats와 동일 정의
  · ΔENB = 편입 후 ENB - 현재 ENB

⚠️ **측정 전용 — 매수 트리거가 아니다.** ENB가 오른다는 건 '같이 안 움직인다'는 뜻일 뿐,
   그 종목이 오른다는 뜻이 아니다. 펀더(별점·스코어)·룰(사다리·하드플로어·룰3)이 위에 그대로 있다.
⚠️ **합성 시계열**이라 실제 계좌 수익률이 아니다(portfolio_stats와 동일 단서).
⚠️ 상관은 **공통 거래일 교집합**으로 잰다 — KR·US 달력이 어긋나므로 변동성은 자기 달력 기준.
⚠️ 과거 상관이 미래에 유지된다는 보장은 없다. 위기에는 상관이 1로 수렴하는 경향이 있고,
   그때가 정확히 분산이 필요한 때다 — 이 표의 가장 큰 한계다.

사용법:
  python3 diversify_candidates.py                 # 워치 전 종목, 편입비중 5% 가정
  python3 diversify_candidates.py --weight 10     # 편입비중 변경
  python3 diversify_candidates.py --window 120
  python3 diversify_candidates.py --json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

import portfolio_stats as ps  # noqa: E402

STOCKS_JSON = os.path.join(REPO, "data", "app", "stocks.json")


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _enb(tks, w, vols, corr):
    """실효 분산 종목수 = (가중평균 변동성 / 포트 변동성)²  (portfolio_stats와 동일 정의)."""
    var_p = 0.0
    for a in tks:
        for b in tks:
            c = corr.get(a, {}).get(b)
            if c is None:
                continue
            var_p += w[a] * w[b] * (vols[a] / 100) * (vols[b] / 100) * c
    vol_p = math.sqrt(max(var_p, 0.0)) * 100
    vol_w = sum(w[t] * vols[t] for t in tks)
    if not vol_p:
        return None, None
    ratio = vol_w / vol_p
    return ratio ** 2, vol_p


def run(window: int = 60, new_weight: float = 5.0) -> dict:
    holdings = ps._load_holdings()
    hs = [h for h in holdings if h.get("value_krw") and h.get("ticker")]
    if not hs:
        return {"status": "unavailable", "reason": "보유 데이터 없음 (app/data.js 미생성?)"}

    st = _load(STOCKS_JSON)
    watch = st.get("watchlist") or {}
    cands = [t for t in watch if t not in {h["ticker"] for h in hs}]

    # ⚠️ 후보를 전부 한 창에 넣으면 **상장이 짧은 후보 하나가 전체 창을 잘라버린다**
    #    (첫 실행에서 SPCX 6/12 상장이 60일 창을 46일로 잘라 기준 ENB가 2.31→2.66으로 바뀌었다).
    #    → 기준선은 보유만으로 잡고, 후보는 **한 종목씩 따로 정렬**해 그 후보의 창 안에서만 비교한다.
    #    ΔENB는 항상 같은 창의 (전 vs 후) 차이라 내부 정합이 유지된다.
    # 창 정의는 portfolio_stats와 **같은 규약**을 쓴다(벤치마크 포함 정렬) — 그래야 여기 기준선이
    # 그 도구의 헤드라인 ENB와 같은 숫자가 되어 두 표를 나란히 읽을 수 있다.
    _BM = [b[0] for b in ps.BENCHMARKS]
    dates, series = ps.align([h["ticker"] for h in hs] + _BM, window)
    covered = [h for h in hs if h["ticker"] in series]
    if len(dates) < 20 or len(covered) < 2:
        return {"status": "unavailable",
                "reason": f"공통 거래일 {len(dates)}일·보유 {len(covered)}종목 — 계산 불가"}

    tks = [h["ticker"] for h in covered]
    label = {h["ticker"]: h["label"] for h in covered}
    tot = sum(h["value_krw"] for h in covered)
    w0 = {t: h["value_krw"] / tot for t, h in zip(tks, covered)}

    rets = {t: ps.simple_returns(series[t], dates) for t in tks}
    vols = {}
    for t in tks:
        v = ps.own_calendar_vol(series[t], window)
        vols[t] = v if v is not None else ps.volatility(rets[t])
    corr = {a: {b: ps.correlation(rets[a], rets[b]) for b in tks} for a in tks}

    base_enb, base_vol = _enb(tks, w0, vols, corr)
    port_ret = [sum(w0[t] * rets[t][i] for t in tks) for i in range(len(dates) - 1)]

    wn = new_weight / 100.0
    rows = []
    for c in cands:
        d2, s2 = ps.align(tks + _BM + [c], window)    # 이 후보만의 공통 창(같은 규약)
        if len(d2) < 20 or c not in s2 or any(t not in s2 for t in tks):
            continue
        r2 = {t: ps.simple_returns(s2[t], d2) for t in tks}
        rc = ps.simple_returns(s2[c], d2)
        v2 = {}
        for t in tks:
            v = ps.own_calendar_vol(s2[t], window)
            v2[t] = v if v is not None else ps.volatility(r2[t])
        vc = ps.own_calendar_vol(s2[c], window)
        vc = vc if vc is not None else ps.volatility(rc)
        c2 = {a: {b: ps.correlation(r2[a], r2[b]) for b in tks} for a in tks}

        # 같은 창에서의 기준선 — 표의 Δ는 항상 이 값과의 차이다
        base2, basevol2 = _enb(tks, w0, v2, c2)
        if base2 is None:
            continue
        pr2 = [sum(w0[t] * r2[t][i] for t in tks) for i in range(len(d2) - 1)]
        rho_p = ps.correlation(rc, pr2)
        if rho_p is None:
            continue

        tks2 = tks + [c]
        w2 = {t: w0[t] * (1 - wn) for t in tks}
        w2[c] = wn
        vols2 = dict(v2); vols2[c] = vc
        corr2 = {a: dict(c2[a]) for a in tks}
        for a in tks:
            corr2[a][c] = ps.correlation(r2[a], rc)
        corr2[c] = {a: corr2[a][c] for a in tks}
        corr2[c][c] = 1.0

        enb2, vol2 = _enb(tks2, w2, vols2, corr2)
        if enb2 is None:
            continue
        rows.append({
            "ticker": c,
            "label": (watch.get(c) or {}).get("label") or c,
            "stars": (watch.get(c) or {}).get("stars"),
            "score": (watch.get(c) or {}).get("score"),
            "corr_port": round(rho_p, 3),
            "vol": round(vc, 1),
            "enb_after": round(enb2, 3),
            "d_enb": round(enb2 - base2, 3),
            "vol_after": round(vol2, 1),
            "d_vol": round(vol2 - basevol2, 1),
            "days": len(d2) - 1,
            "base_enb_window": round(base2, 3),
        })
    rows.sort(key=lambda r: -r["d_enb"])
    return {
        "status": "ok", "window": window, "dates": len(dates) - 1,
        "from": dates[0], "to": dates[-1], "new_weight_pct": new_weight,
        "base_enb": round(base_enb, 3), "base_vol": round(base_vol, 1),
        "holdings_n": len(tks), "candidates": rows,
    }


def run_trim(window: int = 60, trim_pct: float = 50.0) -> dict:
    """**역방향** — 보유 종목을 줄였을 때 실효 분산이 얼마나 오르는가.

    왜 필요한가 [8/29 신설]: 이 파일의 `run()`은 **편입(매수)** 관점만 본다. 그런데
    **크래시 TF가 ACTIVE인 동안 래더 밖 신규 매수는 룰이 막는다** — 즉 그 표는 진단은 되지만
    **집행이 안 되는 처방**이다. 실제로 8/24에 도구를 만들고 risk-desk에 배선까지 했는데
    실효 분산은 2.28(8/23) → **2.13**(8/29)으로 **오히려 나빠졌다**. 처방이 오더가 된 적이 없다.

    TF 하에서 집행 가능한 경로는 **트림**뿐이다(8/2 확정: *크래시 TF는 매수 동결이지 매도 동결이
    아니다*). 그래서 "무엇을 **줄이면** 분산이 오르나"를 같은 ENB 문법으로 계산한다.
    비중을 뺀 만큼은 **나머지 보유에 비례 재분배**된다(= 현금화가 아니라 상대비중 이동 가정).

    ⚠️ **측정 전용 — 매도 트리거가 아니다.** ENB가 오른다는 건 '그 종목이 포트를 지배하고
       있다'는 뜻이지 '그 종목이 나쁘다'는 뜻이 아니다. 별점·룰2(펀더 훼손)·룰4가 위에 그대로 있다.
    ⚠️ 합성 시계열·과거 상관의 한계는 `run()`과 동일하다. 위기엔 상관이 1로 수렴한다.
    """
    holdings = ps._load_holdings()
    hs = [h for h in holdings if h.get("value_krw") and h.get("ticker")]
    if not hs:
        return {"status": "unavailable", "reason": "보유 데이터 없음 (app/data.js 미생성?)"}

    _BM = [b[0] for b in ps.BENCHMARKS]
    dates, series = ps.align([h["ticker"] for h in hs] + _BM, window)
    covered = [h for h in hs if h["ticker"] in series]
    if len(dates) < 20 or len(covered) < 3:
        return {"status": "unavailable",
                "reason": f"공통 거래일 {len(dates)}일·보유 {len(covered)}종목 — 계산 불가"}

    tks = [h["ticker"] for h in covered]
    label = {h["ticker"]: h["label"] for h in covered}
    val = {h["ticker"]: h["value_krw"] for h in covered}
    tot = sum(val[t] for t in tks)
    w0 = {t: val[t] / tot for t in tks}

    rets = {t: ps.simple_returns(series[t], dates) for t in tks}
    vols = {}
    for t in tks:
        v = ps.own_calendar_vol(series[t], window)
        vols[t] = v if v is not None else ps.volatility(rets[t])
    corr = {a: {b: ps.correlation(rets[a], rets[b]) for b in tks} for a in tks}

    base_enb, base_vol = _enb(tks, w0, vols, corr)
    frac = trim_pct / 100.0
    rows = []
    for t in tks:
        freed = w0[t] * frac
        rest = 1.0 - w0[t]
        if rest <= 0:
            continue
        w2 = {u: (w0[u] + freed * (w0[u] / rest) if u != t else w0[u] - freed) for u in tks}
        enb2, vol2 = _enb(tks, w2, vols, corr)
        if enb2 is None:
            continue
        # 포트 평균과의 상관(자기 제외 가중평균) — 왜 이 종목이 포트를 지배하는지의 근거
        rho_bar = None
        if rest > 0:
            acc = sum(w0[u] * (corr.get(t, {}).get(u) or 0.0) for u in tks if u != t)
            rho_bar = acc / rest
        rows.append({
            "ticker": t, "label": label[t],
            "weight_pct": round(w0[t] * 100, 1),
            "value_krw": val[t],
            "trim_krw": int(val[t] * frac),
            "vol": round(vols[t], 1),
            "rho_bar": round(rho_bar, 3) if rho_bar is not None else None,
            "enb_after": round(enb2, 3),
            "d_enb": round(enb2 - base_enb, 3),
            "vol_after": round(vol2, 1),
            "d_vol": round(vol2 - base_vol, 1),
        })
    rows.sort(key=lambda r: -r["d_enb"])
    return {"status": "ok", "mode": "trim", "window": window,
            "dates": len(dates) - 1, "from": dates[0], "to": dates[-1],
            "trim_pct": trim_pct, "base_enb": round(base_enb, 3),
            "base_vol": round(base_vol, 1), "holdings_n": len(tks), "rows": rows}


def print_trim(res):
    print(f"\n✂️  트림 시 분산 개선 — 보유 종목을 {res['trim_pct']:.0f}% 줄였을 때")
    print(f"   창 {res['window']}거래일 ({res['from']}~{res['to']}) · 보유 {res['holdings_n']}종목")
    print(f"   현재 실효 분산 **{res['base_enb']}종목** · 포트 변동성 {res['base_vol']}%")
    print("   ※ 뺀 비중은 나머지에 비례 재분배 가정. **측정 전용 — 매도 트리거 아님.**\n")
    print(f"   {'종목':<14}{'비중%':>6}{'ρ̄(포트)':>9}{'변동성':>7}{'실효분산':>9}{'Δ':>7}"
          f"{'포트변동성':>10}{'Δ':>7}{'트림액(원)':>12}")
    for r in res["rows"]:
        rb = f"{r['rho_bar']:+.3f}" if r["rho_bar"] is not None else "  —  "
        print(f"   {r['label'][:13]:<14}{r['weight_pct']:>6.1f}{rb:>9}{r['vol']:>7.1f}"
              f"{r['enb_after']:>9.2f}{r['d_enb']:>+7.2f}{r['vol_after']:>10.1f}{r['d_vol']:>+7.1f}"
              f"{r['trim_krw']:>12,}")
    print("\n   ⚠️ ΔENB가 크다 = 그 종목이 포트를 **지배**하고 있다는 뜻이지, 나쁘다는 뜻이 아니다.")
    print("   ⚠️ 트림 판단은 별점·룰2(펀더 훼손)·룰4가 위에 있다. 이 표는 **분산 축 하나**만 본다.")


def main() -> int:
    ap = argparse.ArgumentParser(description="분산 후보 랭킹 (ENB 개선 기여도·측정 전용)")
    ap.add_argument("--window", type=int, default=60, help="거래일 창 (기본 60)")
    ap.add_argument("--weight", type=float, default=5.0, help="가상 편입 비중%% (기본 5)")
    ap.add_argument("--trim", nargs="?", const=50.0, type=float, default=None,
                    metavar="PCT",
                    help="역방향: 보유를 PCT%% 트림했을 때의 ENB 개선 (기본 50). "
                         "크래시 TF 하에서 집행 가능한 유일한 분산 경로")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.trim is not None:
        res = run_trim(a.window, a.trim)
        if a.json:
            print(json.dumps(res, ensure_ascii=False, indent=1)); return 0
        if res.get("status") != "ok":
            print(f"⚠️  {res.get('reason')}"); return 1
        print_trim(res)
        return 0

    res = run(a.window, a.weight)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    if res.get("status") != "ok":
        print(f"⚠️  {res.get('reason')}")
        return 1

    print(f"🔗 분산 후보 랭킹 — 워치 종목을 {res['new_weight_pct']:.0f}% 편입했을 때 실효 분산 개선")
    print(f"   창 {res['dates']}거래일 ({res['from']}~{res['to']}) · 보유 {res['holdings_n']}종목")
    print(f"   현재 실효 분산 **{res['base_enb']}종목** · 포트 변동성 {res['base_vol']}%")
    print(f"   ※ 편입 재원은 기존 전 종목 비례 축소 가정. 측정 전용 — 매수 트리거 아님.\n")
    print(f"   {'종목':<14}{'⭐':>3}{'스코어':>6}{'ρ(포트)':>9}{'변동성':>8}{'실효분산':>9}{'Δ':>7}{'포트변동성':>10}{'Δ':>7}{'일수':>6}")
    for r in res["candidates"]:
        star = f"{r['stars']}" if r["stars"] else "-"
        sc = f"{r['score']}" if r["score"] else "-"
        print(f"   {r['label'][:13]:<14}{star:>3}{sc:>6}{r['corr_port']:>9.3f}{r['vol']:>8.1f}"
              f"{r['enb_after']:>9.2f}{r['d_enb']:>+7.2f}{r['vol_after']:>10.1f}{r['d_vol']:>+7.1f}"
              f"{r['days']:>6}")
    print("\n   ※ '일수'가 짧은 종목(신규 상장 등)은 그 종목만의 짧은 창에서 잰 값이라 다른 행과 직접 비교하지 말 것.")
    print("\n   ⚠️ ENB가 오른다 = '같이 안 움직인다'일 뿐, 오른다는 뜻이 아니다.")
    print("   ⚠️ 위기에는 상관이 1로 수렴한다 — 분산이 가장 필요한 때에 이 표가 가장 약해진다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
