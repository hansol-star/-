#!/usr/bin/env python3
"""ratchet_test.py — 사다리 되돌림 정책 검증 (stdlib only·측정 전용)

■ 왜 이게 필요했나 — 2026-07-31 실전 첫날에 드러난 구멍

   7/30 룰1을 낙폭 사다리로 전면 개정했다. 그 다음날 코스피가 **+17.91%**
   (종가 기준 역대 최대 상승)로 튀어 고점대비 -38.6% → **-27.6%**로 되돌렸다.
   그런데 "되돌리면 사다리를 어떻게 하는가"가 **문서와 코드에서 서로 달랐다**:

     · 코드(`tranche_rules.ladder_state`) = **현재 낙폭**으로 매번 재계산 → D2 재잠금 → 15%
     · 문서(CLAUDE.md·crash_tf §2b) = *"각 단계 **첫 도달** 시 그 몫만 해금"*
       → 한 번 열리면 유지된다고 읽힌다(= 래칫) → 35%

   같은 날 같은 룰이 상한을 **121,045원 vs 282,438원**으로 갈랐다. 2.3배다.
   어느 쪽이 옳은지는 취향이 아니라 데이터로 정할 수 있다.

■ 두 정책의 정의

   · **RESET(재잠금)**  w = ladder(현재 낙폭).  되돌리면 몫이 줄어든다.
   · **RATCHET(래칫)**  w = ladder(이번 낙폭 국면의 최저점).  신고가 갱신 시에만 리셋.

   둘은 **되돌림 구간에서만** 갈린다. 그 구간에서 래칫이 더 넣는 돈
   (w_ratchet − w_reset)을 **한계 자금(marginal capital)** 이라 부르고,
   이 돈이 실제로 얼마나 벌었는지가 판정의 핵심이다.

■ 판정 규율
   · 한계 자금의 전방수익률을 **같은 날 RESET이 넣은 돈**과 비교한다.
     (전체 평균과 비교하면 국면이 달라 부당하다 — 되돌림 구간끼리 비교해야 한다.)
   · 표본 수와 **에피소드 수**를 항상 병기. 에피소드 <5면 판정하지 않는다.
   · 12개월을 정본으로 본다(항복 매수는 단기에 보상받지 않는다 — 7/30 확립).
   · **자동 변경 ❌** — 개정 제안만, 확정은 정훈.

■ ★1회차(7/31)에서 잡은 **지표 자체의 결함** — 반드시 승계할 교훈

   첫 실행에서 전 구간 단일 판정은 **RATCHET +1.5%p 우위**로 나왔다. 그런데
   낙폭 구간별로 쪼개니 방향이 뒤집혔다:

     -45% 이하 ±0.0%p · -45~-35% **−1.3%p** · -35~-25% **−0.6%p**  (RESET 우위)
     -25% 위   **+17.0%p**                                          (RATCHET 압도)

   전체 +1.5%p는 **오로지 '-25% 위' 구간 하나가 만든 것**이다. 그런데 그 구간에서
   RESET은 **해금이 0%다** — 즉 "RESET이 넣은 돈"이라는 게 애초에 존재하지 않는다.
   표에 찍힌 −7.1%는 낙폭이 정확히 -25.00%인 극소수 날짜만 분모에 걸린 허수였다.
   **분모가 0인 대상과 비교해 우위를 선언한 셈**이다.

   ⇒ 그래서 판정은 **사다리가 실제로 열려 있는 구간(-25% 이하)에서만** 한다.
      -25% 위에서 래칫이 넣는 돈은 "사다리 밖의 돈"이고, 그 +9.9%는 룰의 우위가
      아니라 **그냥 주식의 기저율**이다. 그 구간은 사다리가 아니라 예비 15% 해금과
      TF 해제 절차(crash_tf §5 3중 게이트)가 다룰 문제다.

   이건 7/30에 확립한 원칙 2 —*"지표는 국면별로 의미가 뒤집힌다. 전 구간 단일
   판정은 방향을 거꾸로 잡는다"*— 가 **하루 만에 그대로 재현된 사례**다.
   폭풍 감산 때와 같은 함정을, 이번엔 내가 만든 검증 도구가 밟았다.

사용:
  python3 ratchet_test.py                 # 11지수 풀링 판정
  python3 ratchet_test.py --symbol ^KS11  # 코스피 단독
  python3 ratchet_test.py --detail        # 낙폭 구간별 분해
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

HORIZONS = [(21, "1개월"), (63, "3개월"), (126, "6개월"), (252, "12개월")]
MIN_EPISODES = 5


def _ladder(dd_pct: float) -> float:
    """tranche_rules의 사다리를 그대로 재사용(룰이 바뀌면 자동 반영)."""
    import tranche_rules as TR
    return TR.ladder_state(dd_pct)[0]


def series(symbol: str):
    """일별로 두 정책의 배분 비중 + 전방수익률을 만든다."""
    import drawdown_history as D
    dates, closes = D.load(symbol)
    if not closes or len(closes) < 300:
        return []

    rows = []
    peak = closes[0]
    trough_dd = 0.0          # 이번 국면의 최저 낙폭(래칫이 기억하는 값)
    for i, c in enumerate(closes):
        if c >= peak:
            peak = c
            trough_dd = 0.0   # 신고가 = 국면 종료 → 래칫 리셋
        dd = (c / peak - 1) * 100
        trough_dd = min(trough_dd, dd)

        w_reset = _ladder(dd)
        w_ratchet = _ladder(trough_dd)
        if w_reset == 0 and w_ratchet == 0:
            continue

        fwd = {}
        for h, _ in HORIZONS:
            fwd[h] = (closes[i + h] / c - 1) * 100 if i + h < len(closes) else None
        rows.append({"date": dates[i], "dd": dd, "trough": trough_dd,
                     "w_reset": w_reset, "w_ratchet": w_ratchet, "fwd": fwd})
    return rows


def _episodes(dates, gap_days=63):
    ds = sorted(dates)
    if not ds:
        return 0
    n = 1
    for a, b in zip(ds, ds[1:]):
        if (dt.date.fromisoformat(b[:10]) - dt.date.fromisoformat(a[:10])).days > gap_days:
            n += 1
    return n


def _wavg(pairs):
    """[(weight, ret)] → 비중가중 평균."""
    pairs = [(w, r) for w, r in pairs if r is not None and w > 0]
    tw = sum(w for w, _ in pairs)
    return (sum(w * r for w, r in pairs) / tw, len(pairs)) if tw else (None, 0)


def judge(rows, label, detail=False):
    # 두 정책이 갈리는 날 = 되돌림 구간
    alldiff = [r for r in rows if r["w_ratchet"] > r["w_reset"]]
    # ★ 판정 대상 = **사다리가 실제로 열려 있는 구간**(D1 문턱 이하)만.
    #   -25% 위에서는 RESET 해금이 0%라 "비교 대상"이 존재하지 않는다(위 헤더 참조).
    import tranche_rules as TR
    D1 = TR.LADDER[0][0]          # 사다리 첫 문턱(현행 -25%) — 룰이 바뀌면 자동 추종
    diff = [r for r in alldiff if r["dd"] <= D1]
    outside = [r for r in alldiff if r["dd"] > D1]

    print(f"\n  [{label}]")
    print(f"    전체 {len(rows):,}일 · 두 정책이 갈린 날 {len(alldiff):,}일 "
          f"→ 그중 **사다리 활성({D1:.0f}% 이하) {len(diff):,}일**이 판정 대상")
    if outside:
        v, _ = _wavg([(r["w_ratchet"] - r["w_reset"], r["fwd"][252]) for r in outside])
        print(f"    ⚠️ {D1:.0f}% 위 {len(outside):,}일은 **판정에서 제외** — RESET 해금이 0%라 "
              f"비교 대상이 없다.\n       (참고: 그 구간 래칫 자금 12M {v:+.1f}% — "
              f"룰의 우위가 아니라 주식의 기저율)")
    if not diff:
        print("    → 사다리 활성 구간의 되돌림 없음 — 판정 불가")
        return None

    ep = _episodes([r["date"] for r in diff])
    print(f"    독립 에피소드 {ep}개")
    print(f"\n    {'구간':<26}{'표본':>8}" + "".join(f"{l:>10}" for _, l in HORIZONS))

    out = {}
    for name, key in (("RESET이 넣은 돈", "base"), ("RATCHET 한계 자금", "marg")):
        line = f"    {name:<26}"
        n0 = 0
        for h, _ in HORIZONS:
            if key == "base":
                pairs = [(r["w_reset"], r["fwd"][h]) for r in diff]
            else:
                pairs = [(r["w_ratchet"] - r["w_reset"], r["fwd"][h]) for r in diff]
            v, n = _wavg(pairs)
            n0 = max(n0, n)
            out.setdefault(key, {})[h] = v
        line = f"    {name:<26}{n0:>8,}"
        for h, _ in HORIZONS:
            v = out[key][h]
            line += f"{v:>+9.1f}%" if v is not None else f"{'—':>10}"
        print(line)

    line = f"    {'차이(한계−기존)':<26}{'':>8}"
    for h, _ in HORIZONS:
        a, b = out["marg"][h], out["base"][h]
        line += f"{a-b:>+9.1f}%" if (a is not None and b is not None) else f"{'—':>10}"
    print(line + "   ← 래칫이 더 넣은 돈의 초과성과")

    # ★ 낙폭 구간을 통제한 판정이 **정본**이다.
    #   위의 전 구간 집계는 두 정책의 자금이 서로 다른 낙폭 구간에 쏠려 있어
    #   (래칫 한계자금은 얕은 구간에 크게, RESET 자금은 깊은 구간에 크게 배분된다)
    #   **심슨의 역설**로 방향이 뒤집힌다. 같은 구간끼리만 비교해야 사과 대 사과다.
    print(f"\n    · 낙폭 구간 통제 비교 (12개월) ← **판정 정본**")
    buckets = [(-100, -45, "-45% 이하"), (-45, -35, "-45~-35%"),
               (-35, D1, f"-35~{D1:.0f}%")]
    wsum = nsum = 0.0
    for lo, hi, nm in buckets:
        sel = [r for r in diff if lo <= r["dd"] < hi]
        if len(sel) < 20:
            continue
        a, _ = _wavg([(r["w_ratchet"] - r["w_reset"], r["fwd"][252]) for r in sel])
        b, _ = _wavg([(r["w_reset"], r["fwd"][252]) for r in sel])
        if a is None or b is None:
            continue
        mark = "RESET" if a < b else ("RATCHET" if a > b else "동률")
        print(f"      {nm:<12}{len(sel):>7,}일   래칫 한계 {a:+6.1f}%  vs  RESET {b:+6.1f}%  "
              f"→ {a-b:+5.1f}%p  {mark} 우위")
        wsum += (a - b) * len(sel)
        nsum += len(sel)

    if nsum == 0:
        print("      (구간별 표본 부족 — 판정 불가)")
        return None
    ctrl = wsum / nsum
    raw = (out["marg"].get(252) or 0) - (out["base"].get(252) or 0)
    print(f"\n      구간가중 종합 **{ctrl:+.2f}%p**   "
          f"(전 구간 단일집계는 {raw:+.1f}%p — **구성 효과로 부호가 뒤집힌 값**)")

    if ep < MIN_EPISODES:
        print(f"    ⏳ 에피소드 {ep} < {MIN_EPISODES} — **판정 불가**(표본 부족)")
        return None
    return ctrl


def main():
    ap = argparse.ArgumentParser(description="사다리 되돌림 정책(RESET vs RATCHET) 검증")
    ap.add_argument("--symbol", help="단일 지수(기본=11지수 풀링)")
    ap.add_argument("--detail", action="store_true", help="낙폭 구간별 분해")
    a = ap.parse_args()

    import rule_tracker as RT
    pool = [(a.symbol, a.symbol)] if a.symbol else RT.POOL

    print("\n" + "=" * 78)
    print("  사다리 되돌림 정책 검증 — RESET(재잠금) vs RATCHET(한번 열면 유지)")
    print("=" * 78)
    print("  7/31 코스피 +17.91%(역대 최대) 반등으로 실제로 갈린 분기점.")
    print("  같은 날 상한이 121,045원(RESET) vs 282,438원(RATCHET)으로 2.3배 차이났다.")

    allrows, deltas = [], []
    for sym, lbl in pool:
        rows = series(sym)
        if not rows:
            continue
        allrows.extend(rows)
        if a.symbol:
            deltas.append(judge(rows, lbl, a.detail))

    if not a.symbol:
        d = judge(allrows, f"{len(pool)}개 지수 풀링", True)
        deltas = [d]

    print("\n" + "=" * 78)
    print("  판정")
    d = deltas[0] if deltas else None
    if d is None:
        print("    ⏳ **판정 불가** — 표본 부족. 현행(코드=RESET) 유지.")
    elif d > 0:
        print(f"    12개월 한계자금 초과성과 **{d:+.1f}%p** → 🟢 **RATCHET 우위**")
        print("       되돌림 구간에서 더 넣은 돈이 더 벌었다 = 한 번 열린 몫을 유지할 근거.")
    else:
        print(f"    12개월 한계자금 초과성과 **{d:+.1f}%p** → 🔴 **RESET 우위**")
        print("       되돌림 구간에서 더 넣은 돈이 덜 벌었다 = 재잠금이 옳다.")
        print("       ⇒ 문서(CLAUDE.md·crash_tf §2b)의 '첫 도달 시 해금' 문구가")
        print("          래칫으로 오독될 수 있으므로 **재잠금으로 명문화**해야 한다.")
    print("    ※ 자동 변경 ❌ — 개정 제안만, 확정은 정훈.\n")


if __name__ == "__main__":
    main()
