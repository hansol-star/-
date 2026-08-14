#!/usr/bin/env python3
"""target_score.py — 목표가 사후 채점 (레벨 정확도 · 낙관 편향)

배경 [8/8 정훈 승인 — target_basis 의무화의 짝]:
`check_target_basis`는 목표가 **근거의 존재와 나이**만 본다. 근거가 타당한지,
우리가 고른 배수(20~26x 같은)가 맞는지는 검사하지 못한다.
그리고 기존 `score_calls`의 '목표가 하단 터치'는 **레벨을 채점하지 않는다** —
목표를 아무리 높게 불러도 "안 터졌다"로 끝날 뿐 **과대 호가에 벌점이 없다.**
실제로 ORCL은 한 달간 실제 컨센(~$155)보다 45~73% 높은 $225~268을 달고 있었는데
어떤 지표도 이를 잡지 못했다.

이 스크립트가 재는 것 — **콜 시점에 우리가 약속한 상승여력 vs 실제 실현**:
  ① 내재여력(implied) = 목표 하단/현재가 - 1  … 그때 우리가 "이만큼 오른다"고 말한 값
  ② 실현(realized)   = 고정 지평(기본 20·60 거래일) 전진수익률
  ③ **낙관 편향 = 내재 - 실현** … 양수면 과대 호가, 0 근처면 정직
  ④ 밴드 적중        = 지평 종가가 [목표 하단, 상단] 안에 들어왔나
  ⑤ 도달             = 지평 내 고가가 목표 하단을 터치했나(기존 지표·비교용)

여력 구간별로 나눠 본다 — "+10% 목표"와 "+80% 목표"는 같은 잣대로 채점하면 안 된다.
공격적 목표일수록 편향이 커지는지가 배수 선택의 품질을 말해준다.

⚠️ 측정 전용. 별점·목표가·트랜치 어떤 룰도 자동으로 바꾸지 않는다.
⚠️ 종목 클러스터 보정 적용(star_validate와 같은 이유 — 콜 단위는 n을 46배 부풀린다).

사용:
  python3 target_score.py                 # 20·60일 지평 채점
  python3 target_score.py --horizons 20   # 지평 지정
  python3 target_score.py --by-ticker     # 종목별 상세
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics as st
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
LEDGER = os.path.join(ROOT, "data/app/calls_log.jsonl")
HIST = os.path.join(ROOT, "data/history")
sys.path.insert(0, HERE)
from score_calls import rng            # 단위(만·억·k) 인식 파서 재사용


_CACHE = {}
def series(sym):
    """일봉 [(date, close)] 오름차순."""
    if sym in _CACHE:
        return _CACHE[sym]
    p = os.path.join(HIST, sym.replace("^", "_") + ".csv")
    out = []
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    out.append((r["date"], float(r["close"])))
                except (ValueError, KeyError, TypeError):
                    continue
        out.sort()
    _CACHE[sym] = out
    return out


def window(sym, d0, horizon):
    """콜 시점 종가와 그 뒤 horizon 거래일 구간. (p0, path) 또는 None."""
    s = series(sym)
    if not s:
        return None
    i = next((k for k, (d, _) in enumerate(s) if d >= d0), None)
    if i is None or i + horizon >= len(s):
        return None
    return s[i][1], [p for _, p in s[i:i + horizon + 1]]


def build(horizon):
    rows = []
    for ln in open(LEDGER, encoding="utf-8"):
        if not ln.strip():
            continue
        r = json.loads(ln)
        tk, d, tgt = r.get("ticker"), r.get("date"), r.get("target")
        if not tk or not d:
            continue
        tr = rng(tgt)
        if not tr:
            continue
        w = window(tk, d, horizon)
        if not w:
            continue
        p0, path = w
        lo, hi = tr
        # 목표가가 현재가와 자릿수가 어긋나면 파싱 실패로 보고 버린다(단위 오인 방어)
        if not (0.2 <= lo / p0 <= 8.0):
            continue
        implied = (lo - p0) / p0 * 100          # 그때 약속한 상승여력(하단 기준)
        realized = (path[-1] - p0) / p0 * 100   # 실제
        rows.append({
            "ticker": tk, "date": d, "stars": r.get("stars"),
            "p0": p0, "lo": lo, "hi": hi, "end": path[-1],
            "implied": implied, "realized": realized,
            "bias": implied - realized,
            "band_hit": lo <= path[-1] <= hi,
            "reached": max(path) >= lo,
        })
    return rows


def by_cluster(rows, key):
    """종목별 평균 후 그룹 평균(종목 1개 = 1표)."""
    g = defaultdict(lambda: defaultdict(list))
    for r in rows:
        g[key(r)][r["ticker"]].append(r)
    out = {}
    for k, tks in g.items():
        per = {t: {
            "implied": st.fmean(x["implied"] for x in v),
            "realized": st.fmean(x["realized"] for x in v),
            "bias": st.fmean(x["bias"] for x in v),
            "band": st.fmean(1.0 if x["band_hit"] else 0.0 for x in v),
            "reach": st.fmean(1.0 if x["reached"] else 0.0 for x in v),
        } for t, v in tks.items()}
        out[k] = {
            "n_calls": sum(len(v) for v in tks.values()),
            "n_tickers": len(per),
            "implied": st.fmean(p["implied"] for p in per.values()),
            "realized": st.fmean(p["realized"] for p in per.values()),
            "bias": st.fmean(p["bias"] for p in per.values()),
            "band": st.fmean(p["band"] for p in per.values()),
            "reach": st.fmean(p["reach"] for p in per.values()),
            "per": per,
        }
    return out


def band_of(implied):
    if implied < 10:
        return "① ~+10%"
    if implied < 25:
        return "② +10~25%"
    if implied < 50:
        return "③ +25~50%"
    return "④ +50%~"


def show(rows, horizon, by_ticker=False):
    print("=" * 78)
    print(f"  목표가 사후 채점 — 지평 +{horizon} 거래일 "
          f"(콜 {len(rows)} · 종목 {len({r['ticker'] for r in rows})})")
    print("=" * 78)
    if not rows:
        print("  (표본 없음 — 지평이 미래로 넘어가는 최근 콜은 자동 제외된다)\n")
        return

    ov = by_cluster(rows, lambda r: "전체")["전체"]
    # 우리 목표가는 통상 12개월(≈250거래일)이다. 20일 지평에서 편향이 양수인 건
    # **기계적으로 당연**하므로 절대값을 '틀렸다'로 읽으면 안 된다.
    # ⇒ 진도율 = 실현 / (내재 × 지평비율). 1.0이면 목표를 향해 정확히 제 속도.
    pace_den = ov["implied"] * (horizon / 250.0)
    pace = (ov["realized"] / pace_den) if abs(pace_den) > 1e-9 else None
    print(f"\n  내재여력 평균 **{ov['implied']:+.1f}%**  vs  실현 **{ov['realized']:+.1f}%**"
          f"   →  낙관 편향 **{ov['bias']:+.1f}%p**")
    print(f"  ⚠️ 12개월 목표를 {horizon}일로 재면 편향은 기계적으로 양수다 — "
          f"**절대값이 아니라 아래 진도율·구간 단조성·종목 순서를 볼 것.**")
    if pace is not None:
        verdict = ("제 속도 이상" if pace >= 1 else
                   "제 속도의 절반 이상" if pace >= 0.5 else
                   "정체" if pace >= 0 else "**역주행**")
        print(f"  진도율 **{pace:+.2f}배** (기대 {pace_den:+.1f}% vs 실제 {ov['realized']:+.1f}%) → {verdict}")
    print(f"  밴드 적중 {ov['band']*100:.0f}%  ·  하단 도달 {ov['reach']*100:.0f}%"
          f"   (종목 {ov['n_tickers']}개 클러스터 보정 · 밴드 적중은 단기 지평에선 낮은 게 정상)")

    # ★[8/14 신설] 지평 보정 편향 — 원편향의 단조성은 **지평 불일치의 산물**일 수 있다.
    #   12개월 목표를 20일로 재면 '+59% 목표'는 20일 안에 실현될 수 없어 편향이 기계적으로 커진다.
    #   ⇒ 기대치를 지평 비율로 프로레이트한 뒤 실현과 비교해야 방향을 제대로 본다.
    #   8/14 실측: 원편향 +17.4 → +58.7(단조 증가)이 보정 후 -14.4 → -3.9로 **부호·방향이 뒤집혔다.**
    #   즉 '공격적 목표일수록 더 틀렸다'가 아니라 보정하면 **덜 틀렸다** — 8/8~8/13 해석은 이 보정이 없었다.
    _pr = horizon / 250.0
    print(f"\n── 내재여력 구간별 (공격적 목표일수록 편향이 커지는가)")
    print(f"   ※ 보정편향 = 실현 − (내재 × {horizon}/250) — 지평을 맞춘 값. **이쪽이 방향의 정본이다.**")
    print(f"   {'구간':<12}{'종목':>4}{'콜':>6}{'내재%':>9}{'실현%':>9}{'편향%p':>9}{'보정편향%p':>12}{'밴드적중':>9}")
    g = by_cluster(rows, lambda r: band_of(r["implied"]))
    for k in sorted(g):
        v = g[k]
        print(f"   {k:<12}{v['n_tickers']:>4}{v['n_calls']:>6}"
              f"{v['implied']:>+9.1f}{v['realized']:>+9.1f}{v['bias']:>+9.1f}"
              f"{v['realized'] - v['implied'] * _pr:>+12.2f}{v['band']*100:>8.0f}%")

    print(f"\n── 별점별")
    print(f"   {'별점':<12}{'종목':>4}{'콜':>6}{'내재%':>9}{'실현%':>9}{'편향%p':>9}{'밴드적중':>9}")
    gs = by_cluster([r for r in rows if isinstance(r["stars"], int)],
                    lambda r: f"⭐{r['stars']}")
    for k in sorted(gs, reverse=True):
        v = gs[k]
        print(f"   {k:<12}{v['n_tickers']:>4}{v['n_calls']:>6}"
              f"{v['implied']:>+9.1f}{v['realized']:>+9.1f}{v['bias']:>+9.1f}{v['band']*100:>8.0f}%")

    if by_ticker:
        print(f"\n── 종목별 (편향 큰 순 = 목표가를 가장 높게 부른 순)")
        print(f"   {'종목':<12}{'콜':>5}{'내재%':>9}{'실현%':>9}{'편향%p':>9}{'밴드적중':>9}")
        for t, p in sorted(ov["per"].items(), key=lambda x: -x[1]["bias"]):
            n = sum(1 for r in rows if r["ticker"] == t)
            print(f"   {t:<12}{n:>5}{p['implied']:>+9.1f}{p['realized']:>+9.1f}"
                  f"{p['bias']:>+9.1f}{p['band']*100:>8.0f}%")

    print(f"\n  ※ 편향 = 내재 - 실현. **양수 = 과대 호가**(약속보다 덜 올랐다), 0 근처 = 정직.")
    print(f"  ※ 지평 내 미실현일 뿐 나중에 도달할 수 있다 — 단기 지평의 편향을 '틀렸다'로 읽지 말 것.")
    print(f"  ※ 측정 전용 — 목표가·별점을 자동으로 바꾸지 않는다.\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--horizons", default="20,60", help="고정 지평(거래일), 쉼표구분")
    ap.add_argument("--by-ticker", action="store_true", help="종목별 상세 출력")
    a = ap.parse_args()
    for h in [int(x) for x in a.horizons.split(",")]:
        show(build(h), h, by_ticker=a.by_ticker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
