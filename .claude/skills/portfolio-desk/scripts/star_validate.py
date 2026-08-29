#!/usr/bin/env python3
"""star_validate.py — 별점 예측력 재검정 (클러스터 보정 · 구간 층화 · 고정지평)

배경 [8/6 감사 §3 → 8/7 정훈 지시 "지금 바로 돌려줘"]:
`score_calls.py`가 708콜/46일 표본에서 **별점 순서 역전**을 냈다
(⭐5 알파 -1.13% < ⭐3 +0.31% < ⭐2 +9.93%, Brier 0.259 > 무정보 0.250).
그런데 그 집계엔 **세 가지 구조적 결함**이 있어 그대로 믿을 수 없다:

  ① **독립표본이 아니다** — ⭐2 113콜의 실체는 종목 2~3개가 46일 반복된 것.
     콜 단위로 평균내면 한 종목의 운명이 113번 투표한다.
  ② **지평이 콜마다 다르다** — score_calls는 "콜 시점 → 최신가"로 잰다.
     6/20 콜은 48일, 8/6 콜은 1일. 오래된 콜일수록 큰 수익/손실이 붙는 구조.
  ③ **레짐이 섞였다** — 표본이 폭락(-38%)과 사상 최대 반등(+17.91%)을 모두 포함.
     낙폭 큰 종목(=⭐2)이 반등기에 더 튀는 건 채점 실력과 무관하다.

이 스크립트는 셋을 각각 제거한다:
  ① **종목 클러스터 보정** — 종목별로 먼저 평균낸 뒤 버킷 평균(종목 1개 = 1표).
     신뢰구간도 **종목 단위 부트스트랩**(콜 단위 아님).
  ② **고정 지평** — 콜 시점 +5/+10/+20 거래일 전진수익률.
  ③ **구간 층화** — 폭락기 / 반등기 분리 집계.

판정 절차는 8/5에 확립한 룰 검증 3단계를 그대로 쓴다:
  ①집계 → ②구간(에피소드) 분해 → ③횡단면(종목 간) 재현.
  **②·③을 통과 못 하면 그 역전은 없는 것으로 본다.**

⚠️ 측정 전용 — 별점·스코어·트랜치 어떤 룰도 자동으로 바꾸지 않는다. 교정은 정훈 판단.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import math
import random
import statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
LEDGER = os.path.join(ROOT, "data/app/calls_log.jsonl")
HIST = os.path.join(ROOT, "data/history")
ETF = {"VOO"}
REGIME_SPLIT = "2026-07-31"      # 코스피 +17.91%(사상 최대 상승) = 폭락→반등 전환일


def load_series(sym):
    """일봉 종가 시계열 → [(date, close)] 오름차순. ^KS11은 _KS11.csv로 저장돼 있다."""
    fn = sym.replace("^", "_") + ".csv"
    p = os.path.join(HIST, fn)
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                out.append((row["date"], float(row["close"])))
            except (ValueError, KeyError, TypeError):
                continue
    out.sort()
    return out


_CACHE = {}
def series(sym):
    if sym not in _CACHE:
        _CACHE[sym] = load_series(sym)
    return _CACHE[sym]


def fwd_return(sym, d0, horizon):
    """d0 이후 첫 거래일 종가 → 그로부터 horizon 거래일 뒤 종가의 수익률(%).
    데이터가 모자라면 None (지평이 미래로 넘어가는 최근 콜은 자동 제외 = 미래참조 없음)."""
    s = series(sym)
    if not s:
        return None
    idx = None
    for i, (d, _) in enumerate(s):
        if d >= d0:
            idx = i
            break
    if idx is None or idx + horizon >= len(s):
        return None
    p0, p1 = s[idx][1], s[idx + horizon][1]
    if not p0:
        return None
    return (p1 - p0) / p0 * 100


def window_end(sym, d0, horizon):
    """콜 d0의 전진창이 끝나는 실제 날짜(거래일 기준). 데이터 부족이면 None."""
    ser = series(sym)
    if not ser:
        return None
    for i, (d, _) in enumerate(ser):
        if d >= d0:
            j = i + horizon
            return ser[j][0] if j < len(ser) else None
    return None


def bench_of(ticker):
    if ticker in ETF:
        return None
    return "^KS11" if ticker.endswith((".KS", ".KQ")) else "VOO"


def build(horizon):
    """원장 → [(ticker, stars, date, alpha, raw)] (알파 계산 가능한 것만)."""
    rows = []
    for ln in open(LEDGER, encoding="utf-8"):
        if not ln.strip():
            continue
        r = json.loads(ln)
        tk, stars, d = r.get("ticker"), r.get("stars"), r.get("date")
        if not tk or not isinstance(stars, int) or not d:
            continue
        b = bench_of(tk)
        if not b:
            continue
        fr = fwd_return(tk, d, horizon)
        br = fwd_return(b, d, horizon)
        if fr is None or br is None:
            continue
        rows.append((tk, stars, d, fr - br, fr))
    return rows


def build_score(horizon):
    """원장 → [(ticker, score, date, alpha)] — **연속 스코어 축**.

    ★[8/29 신설 · 정훈 승인] 왜 필요한가: 별점은 스코어(0~100)를 **15점 폭 밴드**로
    이산화한 값이다. 실측(8/29): 10주간 **스코어는 69회 움직였는데 별점은 15회**만 바뀌었다
    (MSFT 66→84 +18점 동안 ⭐4 고정 · ORCL 71→55 -16점 동안 ⭐3 고정). 즉 **정보의 약 78%가
    밴드에서 버려진 채** 채점되고 있었다. 게다가 버킷이 4개뿐이라 버킷당 종목이 3~4개로
    쪼개져 부트스트랩 CI가 벌어졌다(=8/29 '판정 불가'의 상당 부분이 이산화의 산물).
    ⇒ 같은 원장을 **연속값 순위상관**으로 다시 본다. 버킷을 안 나누므로 전 종목이 한 표본이다.
    """
    rows = []
    for ln in open(LEDGER, encoding="utf-8"):
        if not ln.strip():
            continue
        r = json.loads(ln)
        tk, sc, d = r.get("ticker"), r.get("score"), r.get("date")
        if not tk or not isinstance(sc, (int, float)) or not d:
            continue
        b = bench_of(tk)
        if not b:
            continue
        fr = fwd_return(tk, d, horizon)
        br = fwd_return(b, d, horizon)
        if fr is None or br is None:
            continue
        rows.append((tk, float(sc), d, fr - br))
    return rows


def _ranks(v):
    """동점 평균순위(ties → average rank). Spearman의 전제."""
    order = sorted(range(len(v)), key=lambda i: v[i])
    out = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = st.fmean(rx), st.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return (num / (dx * dy)) if dx and dy else None


def score_axis(horizon, boot=2000, seed=11):
    """연속 스코어 축 — 두 렌즈로 본다(둘이 갈리는 지점이 정보다).

      ⓐ **횡단면(종목 간)**: 종목 평균스코어 ↔ 종목 평균알파의 Spearman.
         "스코어 높은 종목이 실제로 더 이겼나" = 별점이 답하려던 바로 그 질문.
      ⓑ **시계열(종목 내)**: 종목마다 자기 스코어 변화 ↔ 자기 알파의 Spearman을 구해
         종목 평균. "스코어가 **오를 때** 실제로 더 이겼나" = 이산화로 버려지던 69회의 정보.

    ⚠️ 둘 다 **측정 전용**이고, ⓑ는 같은 종목 안의 중첩 전진창을 쓰므로 자기상관이 있다
       (CI가 실제보다 좁게 나온다) — 부호와 크기만 읽고 유의성으로 쓰지 말 것.
    """
    rows = build_score(horizon)
    if not rows:
        return None
    by = defaultdict(list)
    for tk, sc, d, a in rows:
        by[tk].append((sc, a, d))

    keys = sorted(by)
    m_sc = {t: st.fmean([x[0] for x in by[t]]) for t in keys}
    m_al = {t: st.fmean([x[1] for x in by[t]]) for t in keys}
    rho_x = spearman([m_sc[t] for t in keys], [m_al[t] for t in keys])

    within = {}
    for t in keys:
        v = by[t]
        if len(v) >= 5 and len({x[0] for x in v}) >= 2:
            r = spearman([x[0] for x in v], [x[1] for x in v])
            if r is not None:
                within[t] = r
    rho_w = st.fmean(within.values()) if within else None

    rnd = random.Random(seed)
    ci_x = ci_w = None
    if len(keys) >= 3:
        samp = []
        for _ in range(boot):
            pick = [rnd.choice(keys) for _ in keys]
            r = spearman([m_sc[t] for t in pick], [m_al[t] for t in pick])
            if r is not None:
                samp.append(r)
        if len(samp) > 20:
            samp.sort()
            ci_x = (samp[int(0.025 * len(samp))], samp[int(0.975 * len(samp))])
    if len(within) >= 3:
        wk = sorted(within)
        samp = [st.fmean([within[rnd.choice(wk)] for _ in wk]) for _ in range(boot)]
        samp.sort()
        ci_w = (samp[int(0.025 * boot)], samp[int(0.975 * boot)])

    # 이산화 손실 — 같은 행을 별점으로 묶었을 때의 횡단면 상관과 비교
    st_rows = build(horizon)
    by_st = defaultdict(list)
    for tk, stars, d, a, _ in st_rows:
        by_st[tk].append((float(stars), a))
    sk = sorted(by_st)
    rho_star = spearman([st.fmean([x[0] for x in by_st[t]]) for t in sk],
                        [st.fmean([x[1] for x in by_st[t]]) for t in sk]) if len(sk) >= 3 else None

    return {"h": horizon, "n_calls": len(rows), "n_tk": len(keys),
            "rho_cross": rho_x, "ci_cross": ci_x,
            "rho_within": rho_w, "ci_within": ci_w, "n_within": len(within),
            "rho_star_cross": rho_star, "within_detail": within}


def print_score_axis(o):
    if not o:
        print("\n── ④ 연속 스코어 축: 원장에 score가 없어 판정 불가")
        return
    def fmt(r, ci):
        if r is None:
            return "판정 불가"
        c = f"  [{ci[0]:+.2f}, {ci[1]:+.2f}]" if ci else ""
        return f"ρ {r:+.3f}{c}"
    print(f"\n── ④ 연속 스코어 축 (Spearman · 종목 부트스트랩)  "
          f"{o['n_calls']}행 · 종목 {o['n_tk']}개")
    print(f"   ⓐ 횡단면(종목 간)  스코어↔알파 : {fmt(o['rho_cross'], o['ci_cross'])}")
    print(f"   ⓑ 시계열(종목 내)  스코어↔알파 : {fmt(o['rho_within'], o['ci_within'])}"
          f"   (판정가능 종목 {o['n_within']}개)")
    if o["rho_star_cross"] is not None and o["rho_cross"] is not None:
        d = o["rho_cross"] - o["rho_star_cross"]
        print(f"   ↳ 같은 행을 **별점**으로 묶으면 ρ {o['rho_star_cross']:+.3f} "
              f"(연속 대비 {d:+.3f}) — 이산화가 신호를 {'죽인다' if d > 0.05 else '거의 안 바꾼다' if abs(d) <= 0.05 else '오히려 키운다'}")
    if o["within_detail"]:
        top = sorted(o["within_detail"].items(), key=lambda kv: -kv[1])
        head = " · ".join(f"{t} {r:+.2f}" for t, r in top[:4])
        tail = " · ".join(f"{t} {r:+.2f}" for t, r in top[-3:])
        print(f"   ↳ 종목 내 상위: {head}")
        print(f"   ↳ 종목 내 하위: {tail}")
    print("   ⚠️ 측정 전용. ⓑ는 중첩 전진창이라 자기상관이 있다 — 부호·크기만 읽을 것.")


def cluster_stats(rows, boot=2000, seed=7):
    """종목 클러스터 보정 집계.
    ① 종목별 평균 알파를 먼저 구하고 ② 그 값들의 평균 = 버킷 대표값(종목 1개 = 1표).
    ③ 신뢰구간은 **종목 단위** 부트스트랩(콜 단위로 하면 n을 46배 부풀린다)."""
    by_tk = defaultdict(list)
    for tk, _, _, a, _ in rows:
        by_tk[tk].append(a)
    if not by_tk:
        return None
    means = {tk: st.fmean(v) for tk, v in by_tk.items()}
    keys = sorted(means)
    point = st.fmean(means.values())
    rnd = random.Random(seed)
    if len(keys) < 2:
        return {"mean": point, "lo": None, "hi": None,
                "n_calls": len(rows), "n_tickers": len(keys), "per_ticker": means}
    samp = []
    for _ in range(boot):
        pick = [means[rnd.choice(keys)] for _ in keys]
        samp.append(st.fmean(pick))
    samp.sort()
    return {"mean": point, "lo": samp[int(0.025 * boot)], "hi": samp[int(0.975 * boot)],
            "n_calls": len(rows), "n_tickers": len(keys), "per_ticker": means}


def table(rows, title, boot=2000):
    print(f"\n── {title}")
    if not rows:
        print("   (표본 없음)")
        return {}
    out = {}
    print(f"   {'별점':<6}{'종목':>4}{'콜':>6}{'평균알파%':>11}{'95% CI (종목 부트스트랩)':>30}")
    for s in (5, 4, 3, 2, 1):
        sub = [r for r in rows if r[1] == s]
        if not sub:
            continue
        cs = cluster_stats(sub, boot=boot)
        out[s] = cs
        ci = (f"[{cs['lo']:+6.2f}, {cs['hi']:+6.2f}]"
              if cs["lo"] is not None else "  (종목 1개 — CI 불가)")
        print(f"   ⭐{s:<5}{cs['n_tickers']:>4}{cs['n_calls']:>6}"
              f"{cs['mean']:>+11.2f}{ci:>30}")
    return out


def leave_one_out(rows, s_hi=5, s_lo=2):
    """③ 횡단면 재현의 엄밀판 — **한 종목을 빼면 결론이 뒤집히는가.**

    버킷 평균이 종목 1개에 끌려가는지 본다. 종목을 하나씩 제외하며 Δ(⭐hi-⭐lo)를
    재계산해서, 부호가 유지되면 '재현', 뒤집히면 '단일종목 산물'이다.
    (8/5 붕괴구간 면제 기각 때 쓴 논리와 동일 — 집계 +9.5%p가 IMF 하나였다.)
    """
    def bucket(rs, s):
        by = defaultdict(list)
        for tk, ss, _, a, _ in rs:
            if ss == s:
                by[tk].append(a)
        return {tk: st.fmean(v) for tk, v in by.items()}

    hi, lo = bucket(rows, s_hi), bucket(rows, s_lo)
    if not hi or not lo:
        return None
    base = st.fmean(hi.values()) - st.fmean(lo.values())
    flips, res = [], []
    for tk in sorted(set(hi) | set(lo)):
        h2 = {k: v for k, v in hi.items() if k != tk}
        l2 = {k: v for k, v in lo.items() if k != tk}
        if not h2 or not l2:
            continue
        d = st.fmean(h2.values()) - st.fmean(l2.values())
        res.append((tk, d))
        if (d < 0) != (base < 0):
            flips.append(tk)
    print(f"\n── ③b Leave-one-out — 종목 1개 제외 시 Δ(⭐{s_hi}-⭐{s_lo}) 부호 유지 검정")
    print(f"   기준 Δ = {base:+.2f}%p")
    for tk, d in sorted(res, key=lambda x: x[1]):
        mark = "🔁부호반전" if (d < 0) != (base < 0) else ""
        print(f"   −{tk:<12} → Δ {d:+7.2f}%p  {mark}")
    if flips:
        print(f"   ⇒ 🔴 **{', '.join(flips)} 하나만 빼도 결론이 뒤집힌다 = 단일종목 산물**")
    else:
        print(f"   ⇒ 🟢 모든 제외에서 부호 유지 = 횡단면 재현")
    return {"base": base, "flips": flips}


def verdict(out, label):
    """⭐5 > ⭐2 순서가 살아있는가? CI가 겹치면 '판정 불가'다."""
    if 5 not in out or 2 not in out:
        print(f"   ⇒ {label}: 판정 불가(버킷 결손)")
        return None
    a5, a2 = out[5]["mean"], out[2]["mean"]
    inverted = a5 < a2
    overlap = True
    if out[5]["lo"] is not None and out[2]["lo"] is not None:
        overlap = not (out[5]["lo"] > out[2]["hi"] or out[2]["lo"] > out[5]["hi"])
    tag = ("🔴 역전(⭐5<⭐2)" if inverted else "🟢 정상(⭐5>⭐2)")
    sig = "· CI 겹침 = 통계적으로 구분 불가" if overlap else "· CI 분리 = 유의"
    print(f"   ⇒ {label}: {tag}  Δ={a5-a2:+.2f}%p  {sig}")
    return {"inverted": inverted, "overlap": overlap, "delta": a5 - a2}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--horizons", default="5,10,20", help="고정 지평(거래일), 쉼표구분")
    ap.add_argument("--boot", type=int, default=2000, help="부트스트랩 반복(기본 2000)")
    ap.add_argument("--split", default=REGIME_SPLIT, help=f"레짐 분할일(기본 {REGIME_SPLIT})")
    a = ap.parse_args()

    print("=" * 74)
    print("  별점 예측력 재검정 — 클러스터 보정 · 구간 층화 · 고정지평")
    print("=" * 74)
    print(f"\n검정 절차(8/5 확립): ①집계 → ②구간 분해 → ③횡단면 재현")
    print(f"②·③을 통과 못 하면 역전은 '없었던 것'으로 본다.")
    print(f"\n레짐 분할일: {a.split} (코스피 +17.91% = 사상 최대 상승일)")

    summary = {}
    for h in [int(x) for x in a.horizons.split(",")]:
        rows = build(h)
        print("\n" + "=" * 74)
        print(f"  지평 +{h} 거래일   (총 {len(rows)}콜 · 종목 {len({r[0] for r in rows})}개)")
        print("=" * 74)

        # ① 집계 (클러스터 보정만 적용)
        o_all = table(rows, f"① 전체 집계 — 종목 클러스터 보정", a.boot)
        v_all = verdict(o_all, "전체")

        # ④ 연속 스코어 축 [8/29] — 별점 이산화로 버려진 정보를 되찾는다
        print_score_axis(score_axis(h, a.boot))

        # ② 구간 층화
        # ⚠️ 콜 날짜로 나누면 '폭락기 콜'의 전진창이 7/31 반등을 품는다(창이 겹침).
        #    그래서 두 갈래로 본다: ⓐ 콜 날짜 기준 ⓑ **전진창이 반등 전에 끝난 것만**.
        crash = [r for r in rows if r[2] < a.split]
        rally = [r for r in rows if r[2] >= a.split]
        o_c = table(crash, f"②ⓐ 폭락기 콜 (~{a.split} 이전 · 전진창은 반등 포함 가능)", a.boot)
        v_c = verdict(o_c, "폭락기 콜")
        o_r = table(rally, f"②ⓐ 반등기 콜 ({a.split} 이후)", a.boot)
        v_r = verdict(o_r, "반등기 콜")

        pure = [r for r in rows if window_end(r[0], r[2], h) and
                window_end(r[0], r[2], h) < a.split]
        o_p = table(pure, f"②ⓑ 반등 제외 — 전진창이 {a.split} 전에 끝난 콜만", a.boot)
        v_p = verdict(o_p, "반등 제외")

        # ③ 횡단면 재현 — 종목별로 ⭐5 대비 ⭐2가 이겼는지
        print(f"\n── ③ 횡단면 — 종목별 평균 알파(클러스터 원자료)")
        by = defaultdict(lambda: defaultdict(list))
        for tk, s, _, al, _ in rows:
            by[s][tk].append(al)
        for s in (5, 4, 3, 2, 1):
            if s not in by:
                continue
            items = sorted(((tk, st.fmean(v), len(v)) for tk, v in by[s].items()),
                           key=lambda x: -x[1])
            txt = " · ".join(f"{tk} {m:+.1f}%(n{n})" for tk, m, n in items)
            print(f"   ⭐{s}: {txt}")

        loo = leave_one_out(rows)

        summary[h] = {"all": v_all, "crash": v_c, "rally": v_r,
                      "pure": v_p, "loo": loo}

    # 최종 판정
    print("\n" + "=" * 74)
    print("  최종 판정")
    print("=" * 74)
    inv_all = [h for h, v in summary.items() if v["all"] and v["all"]["inverted"]]
    sep = [h for h, v in summary.items() if v["all"] and not v["all"]["overlap"]]
    pure_inv = [h for h, v in summary.items() if v.get("pure") and v["pure"]["inverted"]]
    pure_testable = [h for h, v in summary.items() if v.get("pure")]
    loo_ok = [h for h, v in summary.items() if v.get("loo") and not v["loo"]["flips"]]
    loo_testable = [h for h, v in summary.items() if v.get("loo")]
    rally_testable = [h for h, v in summary.items() if v.get("rally")]

    n = len(summary)
    print(f"\n  ① 집계에서 역전            : {len(inv_all)}/{n} 지평 {inv_all}")
    print(f"  ②ⓐ 반등기 콜 단독 판정     : {len(rally_testable)}/{n} "
          f"{'(표본 미성숙 — 7/31 이후 콜은 전진창이 아직 안 참)' if not rally_testable else rally_testable}")
    print(f"  ②ⓑ 반등 제외에서도 역전    : {len(pure_inv)}/{len(pure_testable)} 지평 {pure_inv}")
    print(f"  ③b LOO 부호 유지(재현)     : {len(loo_ok)}/{len(loo_testable)} 지평 {loo_ok}")
    print(f"  ③  CI 분리(통계적 유의)    : {len(sep)}/{n} 지평 {sep}")

    # 견고성(방향이 보정에서 살아남았나)과 유의성(구분 가능한가)은 다른 축이다.
    # ★[8/29 교정] 舊 robust는 **전 지평 만장일치**만 견고로 봤다 → ②ⓑ 3/3인데 ③b가
    # 2/3이면 곧장 "무너졌다"(🟢)로 떨어졌고, 그 초록불이 **"별점 정상"으로 오독**된다.
    # 실제 8/29 실측이 그 경우였다(①3/3·②ⓑ3/3·③b2/3·CI 0/3). 방향이 대부분 살아남은
    # 것과 방향이 깨진 것은 다른 상태이므로 **부분 견고** 단계를 신설해 가른다.
    def _ratio(ok, testable):
        return (len(ok) / len(testable)) if testable else None

    pure_r, loo_r = _ratio(pure_inv, pure_testable), _ratio(loo_ok, loo_testable)
    robust = (pure_r == 1.0 and loo_r == 1.0)
    robust_part = (not robust and pure_r is not None and loo_r is not None
                   and pure_r >= 0.5 and loo_r >= 0.5)
    print()
    if robust_part and not sep:
        print("  ⇒ 🟡 **방향은 부분적으로 견고, 유의성은 없음 = 판정 불가.**")
        print(f"     역전(⭐5<⭐2)이 반등 제외 {len(pure_inv)}/{len(pure_testable)}·"
              f"LOO {len(loo_ok)}/{len(loo_testable)} 지평에서 살아남았다 —")
        print("     **'보정하니 사라졌다'가 아니다.** 그러나 95% CI가 전부 겹쳐")
        print("     ⭐5와 ⭐2를 통계적으로 구분할 수 없다(버킷당 종목 3~4개).")
        print("     ⇒ **룰 변경 근거로 부족하고, '별점이 잘 가른다'는 반대 주장도 못 한다.**")
        print("     ⇒ 표본 축적 후 재검정(8/5 절차 ③ 미달).")
    elif robust and not sep:
        print("  ⇒ 🟡 **방향은 견고, 유의성은 없음.**")
        print("     역전(⭐5<⭐2)이 클러스터 보정·고정지평·반등 제외·LOO를 **전부 통과**했다.")
        print("     즉 8/6의 '⭐2 +9.93%'가 통째로 반등 착시였다는 결론은 **틀렸다** —")
        print("     방향 자체는 보정 후에도 남는다(Δ -4.3 ~ -6.9%p).")
        print("     그러나 **95% CI가 전부 겹쳐 통계적으로 ⭐5와 ⭐2를 구분할 수 없다**")
        print("     (버킷당 종목 3~4개 = 유효표본이 종목 수라 CI가 넓다).")
        print("     ⇒ **룰 변경 근거로는 아직 부족. 표본 축적 후 재검정**(8/5 절차 ③ 미달).")
        print("     ⇒ 단 '별점이 forward 수익을 잘 가른다'는 반대 주장도 이 데이터로는 못 한다.")
    elif robust and sep:
        print("  ⇒ 🔴 **역전이 견고하고 통계적으로도 유의하다. 채점기준 재교정 검토 대상.**")
    elif not robust and not robust_part:
        print("  ⇒ 🟢 **역전이 보정에서 무너졌다** — 레짐·중복집계·단일종목의 산물.")
        print("     별점 기준을 이 근거로 바꾸지 말 것(8/5 절차 ②③ 불통과).")
        if not sep:
            print("     ⚠️ 단 CI도 전부 겹친다 — 이건 '별점이 정상임을 확인했다'는 뜻이 **아니다**.")
            print("        역전을 못 세운 것이지 예측력을 입증한 게 아니다(무판정).")
    else:
        print("  ⇒ 판정 보류 — 표본 축적 후 재검정.")

    print("\n※ 측정 전용 — 어떤 룰도 자동 변경하지 않는다. 교정은 정훈 판단.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
