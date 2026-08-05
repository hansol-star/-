#!/usr/bin/env python3
"""이평선이 실제로 쓸모 있나 — 조건부 기저율 검정 (측정 전용).

질문: 5·20·60·120 배열 상태가 '이후 수익률'을 실제로 가르는가?
방법: 매 거래일의 배열 상태(정배열/역배열/혼조)와 120일선 위/아래를 라벨로 붙이고,
      그 시점의 forward 1/3/6/12개월 수익률 분포를 비교한다(drawdown_history와 같은 문법).
⚠️ 표본은 중첩된다(overlapping windows) — 승률을 '확률'로 읽지 말 것.
"""
import sys, json, statistics as st
sys.path.insert(0, "/home/user/-/.claude/skills/portfolio-desk/scripts")
import ma_board as M

FWD = {"1M": 21, "3M": 63, "6M": 126, "12M": 252}
UNIVERSE = [
    ("코스피", "^KS11"), ("코스닥", "^KQ11"), ("S&P500", "^GSPC"), ("나스닥", "^IXIC"),
    ("필라델피아반도체", "^SOX"),
    ("삼성전자", "005930.KS"), ("LG전자", "066570.KS"), ("현대차", "005380.KS"),
    ("NAVER", "035420.KS"), ("두산로보틱스", "454910.KS"),
    ("NVDA", "NVDA"), ("MSFT", "MSFT"), ("AAPL", "AAPL"), ("GOOGL", "GOOGL"),
    ("META", "META"), ("MU", "MU"), ("AVGO", "AVGO"), ("ANET", "ANET"), ("ORCL", "ORCL"),
]


def label_days(closes):
    """각 시점의 (배열, 120선위) 라벨."""
    s = {n: M.sma_series(closes, n) for n in M.WINDOWS}
    out = []
    for i in range(len(closes)):
        v = [s[n][i] for n in M.WINDOWS]
        if any(x is None for x in v):
            out.append((None, None)); continue
        if v[0] > v[1] > v[2] > v[3]:
            a = "정배열"
        elif v[0] < v[1] < v[2] < v[3]:
            a = "역배열"
        else:
            a = "혼조"
        out.append((a, closes[i] > v[3]))
    return out


def run():
    buckets = {k: {h: [] for h in ("정배열", "역배열", "혼조", "ALL",
                                   "120선위", "120선아래")} for k in FWD}
    per_sym = {}
    for lbl, sym in UNIVERSE:
        dates, closes, cur, gaps = M.fetch_closes(sym, rng="max")
        if not closes or len(closes) < 400:
            print(f"  skip {lbl} ({gaps or len(closes) if closes else 'no data'})"); continue
        labs = label_days(closes)
        n_used = 0
        loc = {k: {h: [] for h in ("정배열", "역배열", "혼조")} for k in FWD}
        for i, (a, above) in enumerate(labs):
            if a is None:
                continue
            for k, d in FWD.items():
                j = i + d
                if j >= len(closes):
                    continue
                r = (closes[j] / closes[i] - 1) * 100
                buckets[k][a].append(r); buckets[k]["ALL"].append(r)
                buckets[k]["120선위" if above else "120선아래"].append(r)
                loc[k][a].append(r)
                if k == "12M":
                    n_used += 1
        per_sym[lbl] = (len(closes), dates[0], loc)
        print(f"  {lbl:<14} 일봉 {len(closes):>6,}개  ({dates[0]}~)  12M표본 {n_used:,}")
    return buckets, per_sym


def summarize(buckets):
    print("\n" + "=" * 78)
    print("  배열 상태별 forward 수익률 (전 종목 통합 · 중첩표본)")
    print("=" * 78)
    print(f'{"기간":<5}{"조건":<10}{"표본":>9}{"중앙":>9}{"평균":>9}{"승률":>8}{"ALL대비":>10}')
    print("-" * 78)
    for k in FWD:
        base = st.median(buckets[k]["ALL"]) if buckets[k]["ALL"] else 0
        for h in ("정배열", "혼조", "역배열", "120선위", "120선아래", "ALL"):
            v = buckets[k][h]
            if not v:
                continue
            med = st.median(v); mean = sum(v) / len(v)
            win = sum(1 for x in v if x > 0) / len(v) * 100
            edge = med - base
            print(f'{k:<5}{h:<10}{len(v):>9,}{med:>8.1f}%{mean:>8.1f}%{win:>7.0f}%'
                  f'{edge:>+9.1f}%p')
        print("-" * 78)


if __name__ == "__main__":
    print("데이터 수집 중...")
    b, p = run()
    summarize(b)
    json.dump({k: {h: {"n": len(v), "median": round(st.median(v), 2) if v else None,
                       "mean": round(sum(v) / len(v), 2) if v else None,
                       "win": round(sum(1 for x in v if x > 0) / len(v) * 100, 1) if v else None}
                   for h, v in d.items()} for k, d in b.items()},
              open("/tmp/claude-0/-home-user--/0f4f0eaa-b665-50f2-baea-19b76c8b2ac7/scratchpad/ma_test.json", "w"),
              ensure_ascii=False, indent=1)
