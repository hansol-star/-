#!/usr/bin/env python3
"""drawdown_history.py — 낙폭 카탈로그 · 회복 통계 · 조건부 기저율 (stdlib only·측정 전용)

정훈 지시(2026-07-30): *"과거 n개년치 주가분석해서 어떤 상황에 떨어졌고 이런거
포트폴리오 주식들 다 분석하라고."*

■ 기존 `history_analysis.py`와 뭐가 다른가
   그건 **변동성**(RV·군집·GARCH)과 '최악의 하루' 카탈로그를 본다 — 즉 *얼마나 흔들렸나*.
   이건 **낙폭(drawdown)의 생애주기**를 본다 — *고점에서 얼마나·얼마 동안 빠졌고, 돌아오는 데
   얼마나 걸렸고, 지금이 그 분포의 어디인가.* 보유 판단에 필요한 건 후자다.

■ 이 스크립트가 답하는 질문 (전부 정훈이 실제로 물은 것)
   ① "어떤 상황에 떨어졌나"  → 낙폭 카탈로그: 고점→저점→회복, 깊이·소요일·회복일
   ② "지금이 얼마나 심각한가" → 현재 낙폭이 **상장 이래 몇 번째**인가 (백분위 아님, 순위)
   ③ "그래서 앞으로는?"       → **조건부 기저율**: 과거에 지금만큼 빠졌을 때
                                이후 1·3·6·12개월 수익률 분포(중앙값·승률·최악)
   ④ "그때 시장은 어땠나"     → 매크로 오버레이(VIX·유가·달러·환율·금리)를 낙폭 구간에 대조

■ ⚠️ 해석 규율 — 기저율은 예측이 아니다
   표본이 적고(대형 낙폭은 종목당 수 회), 생존 편향이 있으며(상장폐지된 회사는 이 표에 없다),
   같은 깊이라도 원인이 다르면 경로가 다르다. **"과거엔 이랬다"는 사전확률이지 전망이 아니다.**
   측정 전용 — 어떤 룰(안전핀·트랜치·별점)도 바꾸지 않는다.

사용:
  python3 drawdown_history.py                       # 보유 15종목 + 코스피 요약
  python3 drawdown_history.py --symbol 005930.KS    # 한 종목 상세(낙폭 카탈로그 전체)
  python3 drawdown_history.py --min-depth 30 --top 8
  python3 drawdown_history.py --base-rates           # 조건부 기저율 집중
  python3 drawdown_history.py --save                 # data/app/drawdowns.json
"""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
HIST = os.path.join(ROOT, "data", "history")
OUT = os.path.join(ROOT, "data", "app", "drawdowns.json")

# 보유 15 + 지수·매크로 참조
HOLDINGS = [
    ("005930.KS", "삼성전자"), ("066570.KS", "LG전자"), ("454910.KS", "두산로보틱스"),
    ("005380.KS", "현대차"), ("035420.KS", "NAVER"),
    ("NVDA", "NVDA"), ("MU", "MU"), ("AAPL", "AAPL"), ("VOO", "VOO"), ("MSFT", "MSFT"),
    ("ANET", "ANET"), ("AVGO", "AVGO"), ("GOOGL", "GOOGL"), ("META", "META"), ("ORCL", "ORCL"),
]
INDEXES = [("^KS11", "코스피"), ("^KQ11", "코스닥"), ("^IXIC", "나스닥"), ("^GSPC", "S&P500")]
MACRO = [("^VIX", "VIX"), ("CL=F", "WTI"), ("KRW=X", "원달러"), ("^TNX", "美10Y"), ("DX-Y.NYB", "달러지수")]

TD = 252  # 연 거래일


def _safe(sym: str) -> str:
    """history_backfill과 **동일한** 파일명 규칙 — 어긋나면 지수를 통째로 못 읽는다.
    (7/30: ^KS11을 그대로 찾다가 코스피·나스닥·S&P가 전부 '캐시 없음'으로 빠졌다.)"""
    return sym.replace("^", "_").replace("=", "_").replace("/", "_")


def load(symbol: str):
    """data/history/<sym>.csv → ([date], [close]). history_backfill 캐시 소비."""
    for cand in (_safe(symbol), symbol):
        p = os.path.join(HIST, f"{cand}.csv")
        if os.path.exists(p):
            dates, closes = [], []
            with open(p, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    try:
                        c = float(row["close"])
                    except (ValueError, KeyError, TypeError):
                        continue
                    if c > 0:
                        dates.append(row["date"])
                        closes.append(c)
            return dates, closes
    return [], []


# ─────────────────────────────────────────── 낙폭 카탈로그

def drawdowns(dates, closes, min_depth=15.0):
    """고점→저점→회복 구간을 전부 추출.

    정의: 신고점 갱신 시점부터 다음 신고점 회복까지가 하나의 낙폭 사이클.
    깊이가 min_depth% 미만이면 버린다(노이즈).
    마지막 사이클은 아직 회복 안 됐을 수 있다 → recovered=False, 진행 중.
    """
    if not closes:
        return []
    out = []
    peak_i = 0
    trough_i = 0
    for i in range(1, len(closes)):
        if closes[i] >= closes[peak_i]:
            # 신고점 — 직전 사이클 종료
            depth = (closes[trough_i] / closes[peak_i] - 1) * 100
            if depth <= -min_depth:
                out.append({
                    "peak_date": dates[peak_i], "peak": closes[peak_i],
                    "trough_date": dates[trough_i], "trough": closes[trough_i],
                    "recover_date": dates[i], "depth_pct": depth,
                    "days_to_trough": trough_i - peak_i,
                    "days_to_recover": i - trough_i,
                    "total_days": i - peak_i, "recovered": True,
                })
            peak_i = trough_i = i
        elif closes[i] < closes[trough_i]:
            trough_i = i
    # 진행 중 사이클
    depth = (closes[trough_i] / closes[peak_i] - 1) * 100
    if depth <= -min_depth:
        out.append({
            "peak_date": dates[peak_i], "peak": closes[peak_i],
            "trough_date": dates[trough_i], "trough": closes[trough_i],
            "recover_date": None, "depth_pct": depth,
            "days_to_trough": trough_i - peak_i,
            "days_to_recover": None,
            "total_days": len(closes) - 1 - peak_i, "recovered": False,
            "current_pct": (closes[-1] / closes[peak_i] - 1) * 100,
        })
    return out


def current_drawdown(dates, closes):
    """현재가가 **사상 최고점** 대비 몇 % 아래인가 + 그 고점 시점."""
    if not closes:
        return None
    hi = max(closes)
    hi_i = closes.index(hi)
    return {"peak": hi, "peak_date": dates[hi_i], "last": closes[-1],
            "last_date": dates[-1], "dd_pct": (closes[-1] / hi - 1) * 100,
            "days_since_peak": len(closes) - 1 - hi_i}


# ─────────────────────────────────────────── 조건부 기저율

def base_rates(dates, closes, dd_threshold, horizons=(21, 63, 126, 252)):
    """**지금만큼 빠졌던 모든 과거 시점** 이후의 전방 수익률 분포.

    각 거래일의 '그 시점 고점 대비 낙폭'을 구하고, 그게 dd_threshold보다 깊은 날들을
    표본으로 잡아 이후 1·3·6·12개월 수익률을 모은다.
    ⚠️ 표본이 시계열로 겹치므로(연속된 날들이 다 잡힘) **독립 표본이 아니다** —
       승률·중앙값은 방향 감각용이지 통계적 신뢰구간을 주지 않는다.
    """
    n = len(closes)
    if n < TD:
        return None
    run_max, dd = [], []
    m = closes[0]
    for c in closes:
        m = max(m, c)
        run_max.append(m)
        dd.append((c / m - 1) * 100)

    idx = [i for i in range(n) if dd[i] <= dd_threshold]
    if not idx:
        return {"n_samples": 0, "threshold": dd_threshold}

    res = {"n_samples": len(idx), "threshold": dd_threshold,
           "first": dates[idx[0]], "last": dates[idx[-1]], "horizons": {}}
    for h in horizons:
        rr = [(closes[i + h] / closes[i] - 1) * 100 for i in idx if i + h < n]
        if not rr:
            continue
        rr.sort()
        res["horizons"][h] = {
            "n": len(rr),
            "median": statistics.median(rr),
            "mean": statistics.fmean(rr),
            "win_rate": sum(1 for x in rr if x > 0) / len(rr) * 100,
            "p10": rr[int(len(rr) * 0.10)],
            "p90": rr[int(len(rr) * 0.90)],
            "worst": rr[0], "best": rr[-1],
        }
    return res


# ─────────────────────────────────────────── 매크로 오버레이

def macro_at(date_str, cache):
    """특정 날짜의 매크로 값들(그 날짜 이하 최근값 = as-of 조회)."""
    out = {}
    for sym, label in MACRO:
        d, c = cache.get(sym, ([], []))
        if not d:
            continue
        i = bisect.bisect_right(d, date_str) - 1
        if i >= 0:
            out[label] = c[i]
    return out


# ─────────────────────────────────────────── 출력

def _fmt_days(n):
    if n is None:
        return "진행중"
    return f"{n}일({n/TD:.1f}년)" if n >= TD else f"{n}일"


def report_symbol(sym, label, min_depth, top, macro_cache, verbose=True):
    dates, closes = load(sym)
    if not closes:
        print(f"  ⚠️ {label}({sym}) 캐시 없음 — history_backfill.py 필요")
        return None
    cur = current_drawdown(dates, closes)
    dds = drawdowns(dates, closes, min_depth)
    done = [d for d in dds if d["recovered"]]
    span = f"{dates[0]}~{dates[-1]} ({len(closes)}일·{len(closes)/TD:.1f}년)"

    # 현재 낙폭이 역사적으로 몇 번째인가
    # ⚠️ 현재 낙폭이 min_depth에 못 미치면 카탈로그에 사이클이 없다 → 순위 개념 자체가 없다.
    #    (7/30 버그: NVDA -19.4%가 "17/16번째"로 표기됐다. 16회 중 17번째는 성립 불가.)
    all_depths = sorted([d["depth_pct"] for d in dds])
    in_catalog = cur["dd_pct"] <= -min_depth
    rank = (sum(1 for x in all_depths if x <= cur["dd_pct"]) + 1) if in_catalog else None

    if verbose:
        print(f"\n{'═'*76}")
        print(f"■ {label} ({sym})  {span}")
        print(f"  사상최고 {cur['peak']:,.2f} ({cur['peak_date']}) → 현재 {cur['last']:,.2f}"
              f"  = **{cur['dd_pct']:+.1f}%**  (고점 후 {_fmt_days(cur['days_since_peak'])})")
        if dds:
            if rank:
                print(f"  {min_depth:.0f}%+ 낙폭 이력 {len(dds)}회 중 현재는 **{rank}번째로 깊다**"
                      f" (역대 최악 {all_depths[0]:.1f}%)")
            else:
                print(f"  현재 낙폭은 {min_depth:.0f}% 미만 — 카탈로그 대상 아님"
                      f" (과거 {len(dds)}회·역대 최악 {all_depths[0]:.1f}%)")
        if done:
            rec = [d["days_to_recover"] for d in done]
            tot = [d["total_days"] for d in done]
            print(f"  회복 완료 {len(done)}회 — 저점→회복 중앙값 {_fmt_days(int(statistics.median(rec)))}"
                  f" · 고점→회복 전체 중앙값 {_fmt_days(int(statistics.median(tot)))}")

        print(f"\n  [최악 낙폭 top {top}]  깊이 | 고점→저점 | 저점→회복 | 그때 시장")
        for d in sorted(dds, key=lambda x: x["depth_pct"])[:top]:
            mk = macro_at(d["trough_date"], macro_cache)
            bits = []
            if "VIX" in mk: bits.append(f"VIX {mk['VIX']:.0f}")
            if "WTI" in mk: bits.append(f"WTI ${mk['WTI']:.0f}")
            if "원달러" in mk: bits.append(f"₩{mk['원달러']:,.0f}")
            if "美10Y" in mk: bits.append(f"10Y {mk['美10Y']:.1f}%")
            tag = "  ← **현재 진행중**" if not d["recovered"] else ""
            print(f"   {d['depth_pct']:>7.1f}%  {d['peak_date']}→{d['trough_date']}"
                  f"  {_fmt_days(d['days_to_trough']):>12}  {_fmt_days(d['days_to_recover']):>12}"
                  f"  {' · '.join(bits)}{tag}")

    br = base_rates(dates, closes, cur["dd_pct"])
    if verbose and br and br.get("n_samples"):
        print(f"\n  [조건부 기저율] 과거에 고점대비 {cur['dd_pct']:.0f}% 이하였던 {br['n_samples']}개 거래일 이후")
        print(f"   {'기간':<6}{'표본':>6}{'중앙값':>9}{'승률':>8}{'하위10%':>10}{'상위10%':>10}{'최악':>9}")
        for h, lbl in ((21, "1개월"), (63, "3개월"), (126, "6개월"), (252, "12개월")):
            x = br["horizons"].get(h)
            if not x:
                continue
            print(f"   {lbl:<6}{x['n']:>6}{x['median']:>+8.1f}%{x['win_rate']:>7.0f}%"
                  f"{x['p10']:>+9.1f}%{x['p90']:>+9.1f}%{x['worst']:>+8.1f}%")
    elif verbose:
        print("\n  [조건부 기저율] 표본 없음 — 사상 최대 낙폭 구간(전례 없음)")

    return {"symbol": sym, "label": label, "span": span, "bars": len(closes),
            "current": cur, "rank_among_drawdowns": rank, "n_drawdowns": len(dds),
            "worst_depth": all_depths[0] if all_depths else None,
            "median_recover_days": (int(statistics.median([d["days_to_recover"] for d in done]))
                                    if done else None),
            "drawdowns": sorted(dds, key=lambda x: x["depth_pct"])[:top],
            "base_rates": br}


def summary_table(rows):
    print(f"\n{'═'*76}")
    print("■ 보유 전종목 낙폭 요약 — 지금이 역사적으로 어디인가")
    print(f"\n  {'종목':<12}{'이력':>7}{'현재낙폭':>10}{'역대순위':>9}{'역대최악':>10}{'중앙회복':>10}")
    for r in rows:
        if not r:
            continue
        c = r["current"]
        rec = f"{r['median_recover_days']}일" if r["median_recover_days"] else "—"
        rank = (f"{r['rank_among_drawdowns']}/{r['n_drawdowns']}"
                if r.get("rank_among_drawdowns") else f"—/{r['n_drawdowns']}")
        worst = f"{r['worst_depth']:.0f}%" if r["worst_depth"] is not None else "—"
        print(f"  {r['label']:<12}{r['bars']/TD:>6.0f}년{c['dd_pct']:>+9.1f}%{rank:>9}{worst:>10}{rec:>10}")


def main():
    ap = argparse.ArgumentParser(description="낙폭 카탈로그·회복 통계·조건부 기저율 (측정 전용)")
    ap.add_argument("--symbol", "--tickers", help="한 종목만 상세")
    ap.add_argument("--min-depth", type=float, default=20.0, help="낙폭 최소 깊이%% (기본 20)")
    ap.add_argument("--top", type=int, default=6, help="표시할 최악 낙폭 개수")
    ap.add_argument("--indexes", action="store_true", help="지수도 포함")
    ap.add_argument("--base-rates", action="store_true", help="기저율 요약만")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()

    macro_cache = {sym: load(sym) for sym, _ in MACRO}

    if a.symbol:
        lbl = dict(HOLDINGS + INDEXES).get(a.symbol, a.symbol)
        rows = [report_symbol(a.symbol, lbl, a.min_depth, a.top, macro_cache)]
    else:
        uni = list(HOLDINGS)
        if a.indexes:
            uni = INDEXES + uni
        rows = [report_symbol(s, l, a.min_depth, a.top, macro_cache,
                              verbose=not a.base_rates) for s, l in uni]
        summary_table(rows)

    if a.save:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"updated": dt.date.today().isoformat(),
                       "min_depth": a.min_depth,
                       "note": "측정 전용 — 기저율은 사전확률이지 전망이 아니다. "
                               "표본 중복·생존편향 있음. 어떤 룰도 바꾸지 않는다.",
                       "symbols": [r for r in rows if r]}, f, ensure_ascii=False, indent=1)
        print(f"\n💾 {os.path.relpath(OUT, ROOT)} 저장")
    print()


if __name__ == "__main__":
    main()
