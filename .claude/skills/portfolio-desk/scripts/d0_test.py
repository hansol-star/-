#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
d0_test.py — 룰1 사다리에 **D0(-20%) 단계를 신설할 것인가** 검정 (stdlib·무네트워크)

[왜 — 2026-09-09 정훈 지시 "룰1 상한 계산 방식 좀 바꿔보자"]
룰1 원장 24일 실측: **상한이 0원인 날이 14일(58%)**이고, 그중 9일의 사유가
"낙폭이 -25%(D1 문턱)에 못 미쳐서"였다. 코스피가 -22~-25%를 오가는 내내 사다리가 잠겨 있었고,
그 사이 현금은 69만 → 145만으로 늘었다. **재원은 쌓이는데 쓸 문이 없는 상태.**

그런데 코스피 -23% 지점의 조건부 기저율은 12M **중앙 +20.9%·승률 86%**(표본 2,135)다.
-38.6%(중앙 +43%·승률 97%)보다 못하지만 **"사면 안 되는 구간"으로 보기 어렵다.**

⚠️ **이건 룰 변경 가설이므로 8/5에 확립한 절차를 반드시 거친다:**
      ① 집계 → ② 에피소드 분해 → ③ 시장 간 횡단면 재현
      **②·③을 통과 못 하면 룰을 건드리지 않는다.**
   8/5에 검토한 룰 변경 2건이 **둘 다 ①에선 그럴듯했다가 ②③에서 무너졌다** —
   집계 숫자가 소수 에피소드의 구성 효과였다. 같은 함정을 밟지 않으려고 이 순서를 강제한다.

[검정하는 것]
  가설 H: "-20~-25% 구간도 12개월 지평에서 유의한 상승 기대를 준다"
  ① 집계      : 전 기간 -20~-25% 구간의 forward 수익률 분포
  ② 에피소드  : 낙폭 에피소드별로 쪼개 **부호가 일관되는가**(소수 에피소드가 만든 값인가)
  ③ 횡단면    : 비미국 시장들에서 **재현되는가**(7/17 = 41%면 동전던지기 — 8/5 기각 기준)

⚠️ **측정 전용.** 이 스크립트는 룰을 바꾸지 않는다 — 판정 재료만 낸다. 채택은 정훈 승인.
⚠️ 표본 중복(겹치는 창)·생존편향이 있다. "승률 86%"를 "86% 확률"로 읽지 말 것(7/30 규율).
"""
from __future__ import annotations
import argparse
import csv
import glob
import os
import statistics as st
import sys

_HERE = os.path.abspath(__file__)
ROOT = os.path.abspath(os.path.join(_HERE, *([os.pardir] * 5)))
HIST = os.path.join(ROOT, "data", "history")

# ③ 횡단면은 **주가 지수만** 쓴다.
# ⚠️ 9/9 실사고: 처음엔 data/history/*.csv 전부를 돌렸더니 개별 종목(NVDA·META…)과
#    VIX·환율·금리·원자재가 섞여 79% 재현이 나왔다. VIX는 낙폭 뒤 내리는 게 당연한
#    역방향 자산이고 환율·금리는 주가 지수가 아니다 — **8/5에 경고한 바로 그 오염**이다.
#    정본 = history_backfill.VERIFY_MARKETS(비미국 13) + 주요 지수.
INDEX_ONLY = {
    "^TWII", "^BSESN", "^JKSE", "^BVSP", "^MXX", "XU100.IS", "^GSPTSE", "^AXJO",
    "^FTSE", "^GDAXI", "^KLSE", "^TA125.TA", "^MERV",              # VERIFY_MARKETS 13
    "^GSPC", "^IXIC", "^DJI", "^RUT", "^N225", "^HSI", "^STOXX50E", "^KQ11",  # 주요 지수
}

LO, HI = -25.0, -20.0          # 검정 대상 구간(D0 후보)
REF_LO, REF_HI = -40.0, -35.0  # 대조군 = 이미 채택된 D2 구간


def load_series(path):
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                d, c = row.get("date"), row.get("close")
                if not d or not c:
                    continue
                try:
                    out.append((d, float(c)))
                except ValueError:
                    continue
    except OSError:
        return []
    out.sort()
    return out


def drawdowns(series):
    """각 시점의 고점대비 낙폭(%)과 에피소드 id(고점 갱신마다 증가)."""
    peak, ep, res = None, 0, []
    for d, c in series:
        if peak is None or c >= peak:
            if peak is not None and c >= peak:
                ep += 1                       # 신고가 = 이전 낙폭 에피소드 종료
            peak = c
        res.append((d, c, (c / peak - 1) * 100, ep))
    return res


def forward(series, i, horizon):
    if i + horizon >= len(series):
        return None
    return (series[i + horizon][1] / series[i][1] - 1) * 100


def bucket_stats(series, dd, lo, hi, horizon):
    vals, eps = [], {}
    for i, (d, c, x, ep) in enumerate(dd):
        if not (lo <= x < hi):
            continue
        f = forward(series, i, horizon)
        if f is None:
            continue
        vals.append(f)
        eps.setdefault(ep, []).append(f)
    return vals, eps


def summarize(vals):
    if not vals:
        return None
    return {"n": len(vals), "median": st.median(vals),
            "win": sum(1 for v in vals if v > 0) / len(vals) * 100}


def main() -> int:
    ap = argparse.ArgumentParser(description="D0(-20%) 단계 신설 검정 — 8/5 3단 절차")
    ap.add_argument("--horizon", type=int, default=252, help="forward 거래일(기본 252=12개월)")
    ap.add_argument("--min-ep", type=int, default=20, help="에피소드 최소 표본")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(HIST, "*.csv")))
    files = [f for f in files if "flows" not in f]
    if not files:
        print("[ERR] data/history 캐시 없음 — history_backfill.py 먼저", file=sys.stderr)
        return 1

    kospi = os.path.join(HIST, "^KS11.csv")
    if not os.path.exists(kospi):
        cand = [f for f in files if "KS11" in os.path.basename(f)]
        kospi = cand[0] if cand else None

    print("=" * 88)
    print(f"  D0(-20%) 신설 검정 — forward {a.horizon}거래일 · 8/5 절차 ①→②→③")
    print("=" * 88)

    # ── ① 집계 (코스피) ────────────────────────────────────────────────
    ser = load_series(kospi) if kospi else []
    if not ser:
        print("[ERR] 코스피 시계열 없음", file=sys.stderr)
        return 1
    dd = drawdowns(ser)
    v_d0, ep_d0 = bucket_stats(ser, dd, LO, HI, a.horizon)
    v_d2, ep_d2 = bucket_stats(ser, dd, REF_LO, REF_HI, a.horizon)
    s0, s2 = summarize(v_d0), summarize(v_d2)

    print("\n【① 집계 — 코스피】")
    print(f"{'구간':<18}{'표본':>7}{'중앙값':>10}{'승률':>8}")
    if s0:
        print(f"{'D0 후보 -25~-20%':<18}{s0['n']:>7}{s0['median']:>9.1f}%{s0['win']:>7.0f}%")
    if s2:
        print(f"{'대조 D2 -40~-35%':<18}{s2['n']:>7}{s2['median']:>9.1f}%{s2['win']:>7.0f}%")

    # ── ② 에피소드 분해 ────────────────────────────────────────────────
    print("\n【② 에피소드 분해 — 코스피】 (소수 에피소드가 만든 값인지)")
    print(f"{'에피소드':>8}{'표본':>7}{'중앙값':>10}{'승률':>8}")
    pos = neg = 0
    for ep in sorted(ep_d0):
        vs = ep_d0[ep]
        if len(vs) < a.min_ep:
            continue
        m = st.median(vs)
        w = sum(1 for v in vs if v > 0) / len(vs) * 100
        pos, neg = (pos + 1, neg) if m > 0 else (pos, neg + 1)
        print(f"{ep:>8}{len(vs):>7}{m:>9.1f}%{w:>7.0f}%")
    tot = pos + neg
    print(f"  → 양(+) {pos} / 음(−) {neg}"
          + (f"  = **{pos/tot*100:.0f}% 일관**" if tot else "  = 판정 불가(표본 부족)"))

    # ── ③ 시장 간 횡단면 재현 ──────────────────────────────────────────
    print("\n【③ 횡단면 재현 — 다른 시장에서도 같은 방향인가】")
    print(f"{'시장':<16}{'표본':>7}{'중앙값':>10}{'승률':>8}")
    rep_pos = rep_neg = 0
    for f in files:
        nm = os.path.splitext(os.path.basename(f))[0]
        if "KS11" in nm:
            continue
        # 캐시 파일명은 ^·/ 를 _ 로 바꿔 저장된다 → 같은 규칙으로 되돌려 대조한다
        sym = nm.replace("_", "^", 1) if nm.startswith("_") else nm
        if sym not in INDEX_ONLY and nm not in INDEX_ONLY:
            continue
        s = load_series(f)
        if len(s) < a.horizon + 300:
            continue
        v, _ = bucket_stats(s, drawdowns(s), LO, HI, a.horizon)
        stt = summarize(v)
        if not stt or stt["n"] < 60:
            continue
        rep_pos, rep_neg = ((rep_pos + 1, rep_neg) if stt["median"] > 0
                            else (rep_pos, rep_neg + 1))
        print(f"{nm:<16}{stt['n']:>7}{stt['median']:>9.1f}%{stt['win']:>7.0f}%")
    rt = rep_pos + rep_neg
    print(f"  → 양(+) {rep_pos} / 음(−) {rep_neg}"
          + (f"  = **{rep_pos/rt*100:.0f}% 재현**" if rt else "  = 판정 불가"))

    # ── 판정 ───────────────────────────────────────────────────────────
    print("\n" + "=" * 88)
    ok2 = tot and pos / tot >= 0.70
    ok3 = rt and rep_pos / rt >= 0.70
    print(f"  ② 에피소드 일관 ≥70% : {'✅ 통과' if ok2 else '❌ 미통과'}")
    print(f"  ③ 횡단면 재현  ≥70% : {'✅ 통과' if ok3 else '❌ 미통과'}")
    print(f"  ⇒ 종합: {'✅ D0 신설 검토 가능 (정훈 승인 필요)' if (ok2 and ok3) else '❌ 기각 — 룰을 건드리지 않는다'}")
    print("  ⚠️ 8/5 규율: ②·③을 통과 못 하면 ①이 아무리 좋아도 룰을 바꾸지 않는다.")
    print("  ⚠️ 표본은 창이 겹쳐 중복된다 — 승률을 확률로 읽지 말 것.")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
