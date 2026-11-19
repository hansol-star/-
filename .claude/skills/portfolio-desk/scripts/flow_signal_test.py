#!/usr/bin/env python3
"""flow_signal_test.py — '외인·기관이 사면 오르나' 검정 (측정 전용 · 룰 변경 없음 · 2026-11-20)

■ 왜
  정훈 11/20 *"기관 외국인 개인 매수 매도도 봐봐 현대차 같은 경우는 지금 많이들 사는거 같기도 하고
  다시 올라갈 가능성은 없나"* — 수급이 이후 수익률을 맞추는지 숫자로 본다. 사전등록 = trials.jsonl `flow_signal`.

■ 방법
  · 표본 = data/history 국내 19종목 · 네이버 종목 수급(외인·기관·개인 순매수 수량 + 외인보유율) 약 600거래일
  · 20거래일마다 한 번 표본(신호 창이 겹치지 않게) — 신호 = 직전 20일
      S1 외인+기관 동반: 외인 20일 합 > 0 그리고 기관 20일 합 > 0 → '매수' / 둘 다 < 0 → '매도'
      S2 외인보유율 20일 변화 > 0 → '매수' / < 0 → '매도'
  · 결과 = 신호일 종가 → 20·60거래일 뒤 종가, 같은 기간 지수(코스피 .KS · 코스닥 .KQ) 대비 초과(%p)
  · 판정 = ①풀링 '매수−매도' 평균 차 · ②반기별 부호 · ③종목별 차 부호 k/n(이항 p) → Holm 4
  ⚠️ 종목 19개는 지금 추적 중인 종목(생존 편향) · 국면 = 2024~2026 한 번(급등 + 붕괴)

사용:
  python flow_signal_test.py            # 수집(약 3~4분) + 표
  python flow_signal_test.py --cached   # data/research/flow_signal_test.json 재사용
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import os
import sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
HIST = os.path.join(ROOT, "data", "history")
OUT = os.path.join(ROOT, "data", "research", "flow_signal_test.json")
SIG, FWD, STEP = 20, (20, 60), 20


def _load_index(sym):
    rows = []
    with open(os.path.join(HIST, sym + ".csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rows.append((r["date"], float(r["close"])))
            except (TypeError, ValueError):
                pass
    return rows


def collect(pages=10):
    import naver_flows as nf
    codes = sorted(n[:-4] for n in os.listdir(HIST) if n.endswith((".KS.csv", ".KQ.csv")))
    data = {}
    for c in codes:
        rows = nf.stock_flows(c.split(".")[0], pages=pages)
        data[c] = [r for r in rows if r.get("close")]
        print(f"  {c}: {len(data[c])}일 {data[c][0]['date'] if data[c] else ''}~", file=sys.stderr)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False)
    return data


def _binom_p(k, n):
    return sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0


def _holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def analyze(data):
    idx = {"KS": _load_index("_KS11"), "KQ": _load_index("_KQ11")}
    idx_d = {k: [d for d, _ in v] for k, v in idx.items()}

    def ix(key, day):
        i = bisect.bisect_right(idx_d[key], day) - 1
        return idx[key][i][1] if i >= 0 else None

    obs = []  # (종목, 날짜, s1, s2, {h: 초과})
    for code, rows in data.items():
        key = "KQ" if code.endswith(".KQ") else "KS"
        for t in range(SIG, len(rows) - min(FWD), STEP):
            w = rows[t - SIG + 1:t + 1]
            f = sum(r["foreign_qty"] or 0 for r in w)
            g = sum(r["organ_qty"] or 0 for r in w)
            s1 = "매수" if (f > 0 and g > 0) else ("매도" if (f < 0 and g < 0) else None)
            h0, h1 = rows[t - SIG].get("foreign_hold_pct"), rows[t].get("foreign_hold_pct")
            s2 = None if (h0 is None or h1 is None or h0 == h1) else ("매수" if h1 > h0 else "매도")
            xs = {}
            for h in FWD:
                if t + h < len(rows):
                    r = rows[t + h]["close"] / rows[t]["close"] - 1
                    a, b = ix(key, rows[t]["date"]), ix(key, rows[t + h]["date"])
                    if a and b:
                        xs[h] = (r - (b / a - 1)) * 100
            obs.append((code, rows[t]["date"], s1, s2, xs))

    res = []
    for sname, si in (("S1 외인+기관 동반", 2), ("S2 외인보유율 변화", 3)):
        for h in FWD:
            buy = [o for o in obs if o[si] == "매수" and h in o[4]]
            sell = [o for o in obs if o[si] == "매도" and h in o[4]]
            allx = [o[4][h] for o in obs if h in o[4]]
            mb = sum(o[4][h] for o in buy) / len(buy) if buy else None
            ms = sum(o[4][h] for o in sell) / len(sell) if sell else None
            # ② 반기
            halves = {}
            for o in buy + sell:
                y, m = o[1][:4], int(o[1][5:7])
                halves.setdefault(f"{y}H{1 if m <= 6 else 2}", {"매수": [], "매도": []})[o[si]].append(o[4][h])
            hs = {k: (round(sum(v["매수"]) / len(v["매수"]) - sum(v["매도"]) / len(v["매도"]), 1)
                      if v["매수"] and v["매도"] else None) for k, v in sorted(halves.items())}
            # ③ 종목
            per = {}
            for o in buy + sell:
                per.setdefault(o[0], {"매수": [], "매도": []})[o[si]].append(o[4][h])
            diffs = [sum(v["매수"]) / len(v["매수"]) - sum(v["매도"]) / len(v["매도"])
                     for v in per.values() if v["매수"] and v["매도"]]
            k = sum(1 for d in diffs if d > 0)
            res.append({"signal": sname, "h": h, "n_buy": len(buy), "n_sell": len(sell),
                        "mean_buy": None if mb is None else round(mb, 2),
                        "mean_sell": None if ms is None else round(ms, 2),
                        "diff": None if (mb is None or ms is None) else round(mb - ms, 2),
                        "mean_all": round(sum(allx) / len(allx), 2) if allx else None,
                        "halves": hs, "stocks_k": k, "stocks_n": len(diffs), "p": _binom_p(k, len(diffs))})
    for r, a in zip(res, _holm([r["p"] for r in res])):
        r["holm"] = round(a, 3)
    span = sorted(o[1] for o in obs)
    return {"obs": len(obs), "span": [span[0], span[-1]] if span else None, "stocks": len(data), "results": res}


def show(out):
    print(f"── 수급 신호 검정(사전등록 flow_signal) — 국내 {out['stocks']}종목 · 표본 {out['obs']}개 · {out['span'][0]}~{out['span'][1]}")
    print("   초과 = 지수 대비 %p · 20거래일 간격 비중첩")
    for r in out["results"]:
        hs = " ".join(f"{k}:{'—' if v is None else f'{v:+.1f}'}" for k, v in r["halves"].items())
        print(f"{r['signal']:<14} {r['h']:>2}일 | 매수 {r['mean_buy']:+6.2f} (n={r['n_buy']:>3}) · 매도 {r['mean_sell']:+6.2f} (n={r['n_sell']:>3}) · "
              f"차 {r['diff']:+6.2f} · 무조건 {r['mean_all']:+6.2f} | 종목 {r['stocks_k']}/{r['stocks_n']} · Holm {r['holm']:.3f}")
        print(f"{'':<17}반기별 차: {hs}")
    print("⚠️ 생존 편향(지금 추적 중인 종목) · 국면 1회 · 측정 전용 — 어떤 룰도 바꾸지 않는다")


def main():
    ap = argparse.ArgumentParser(description="외인·기관 수급 신호 → 이후 초과수익 검정 (측정 전용)")
    ap.add_argument("--cached", action="store_true", help="저장된 수집본 재사용")
    ap.add_argument("--pages", type=int, default=10, help="종목당 60일 페이지 수")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.cached and os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = collect(a.pages)
    out = analyze(data)
    print(json.dumps(out, ensure_ascii=False, indent=1) if a.json else "", end="")
    if not a.json:
        show(out)


if __name__ == "__main__":
    main()
