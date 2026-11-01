#!/usr/bin/env python3
"""예측 원장 — 판단을 확률·만기·해소 조건으로 남기고 Brier로 기준선과 비교한다 (11/2 정훈 승인).

산문 전망은 틀려도 채점되지 않는다. 이 원장은 '맞혔다/틀렸다'가 기계로 정해지는 판단만 받는다.
  · price = 만기 첫 종가가 수준 위/아래인가 → 기준선은 그 종목 과거 같은 지평의 도달 빈도로 자동 계산.
  · event = 사람이 해소 → 기준선을 근거와 함께 직접 적는다(컨센서스·시장가·기저율).
  · 범주별 20건 이상에서 기준선을 못 이기면 🔴 — 그 범주는 새 예측을 받지 않는다.
측정 전용 — 포지션·룰을 자동으로 바꾸지 않는다.

  python forecast_ledger.py --price 코스피 ^KS11 above 6000 2026-11-30 0.45 --cat 지수1M --claim "..."
  python forecast_ledger.py --event JSON     # id·category·claim·by·prob·baseline·baseline_src·rule
  python forecast_ledger.py --auto           # 만기 지난 price 해소
  python forecast_ledger.py --resolve ID 1 --note "..."
  python forecast_ledger.py --score | --selftest
"""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *([os.pardir] * 4)))
LEDGER = os.path.join(ROOT, "data", "research", "forecast_ledger.jsonl")
MIN_N = 20


def load(path: str = LEDGER) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def save(rows: list[dict], path: str = LEDGER) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def history(sym: str) -> tuple[list[str], list[float]]:
    d, c = [], []
    with open(os.path.join(ROOT, "data", "history", sym.replace("^", "_") + ".csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("close"):
                d.append(r["date"])
                c.append(float(r["close"]))
    return d, c


def base_rate(c: list[float], need: float, h: int, above: bool) -> float:
    """h거래일 수익률이 need를 넘긴 과거 빈도(최근 2,520거래일 · 라플라스 보정)."""
    c = c[-2520:]
    r = [c[i + h] / c[i] for i in range(len(c) - h)]
    k = sum(x >= need if above else x <= need for x in r)
    return (k + 1) / (len(r) + 2)


def score(rows: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for r in rows:
        if r.get("outcome") is None:
            continue
        o = out.setdefault(r["category"], dict(n=0, bs=0.0, base=0.0))
        o["n"] += 1
        o["bs"] += (r["prob"] - r["outcome"]) ** 2
        o["base"] += (r["baseline"] - r["outcome"]) ** 2
    for o in out.values():
        o["bs"], o["base"] = o["bs"] / o["n"], o["base"] / o["n"]
        o["skill"] = 1 - o["bs"] / o["base"] if o["base"] else 0.0
        o["stop"] = o["n"] >= MIN_N and o["skill"] <= 0
    return out


def add(rows: list[dict], t: dict) -> list[dict]:
    if t["id"] in {r["id"] for r in rows}:
        raise SystemExit(f"중복 id: {t['id']}")
    if not 0 < float(t["prob"]) < 1 or not 0 < float(t["baseline"]) < 1:
        raise SystemExit("prob·baseline은 0~1 사이")
    if not t.get("claim") or not t.get("by") or not t.get("category"):
        raise SystemExit("claim·by·category 필수")
    if score(rows).get(t["category"], {}).get("stop"):
        raise SystemExit(f"🔴 '{t['category']}' 범주는 기준선 미달 — 새 예측을 받지 않는다")
    return rows + [dict(t, outcome=None)]


def resolve_due(rows: list[dict], today: str, hist=history) -> int:
    n = 0
    for r in rows:
        if r.get("outcome") is not None or r.get("kind") != "price" or r["by"] > today:
            continue
        d, c = hist(r["ticker"])
        i = bisect.bisect_left(d, r["by"])
        if i >= len(c):
            continue
        hit = c[i] >= r["level"] if r["side"] == "above" else c[i] <= r["level"]
        r.update(outcome=int(hit), resolved_at=d[i], resolved_close=c[i])
        n += 1
    return n


def selftest() -> int:
    t = dict(id="a", category="x", claim="c", by="2026-01-02", prob=0.9, baseline=0.5, kind="price",
             ticker="T", level=100.0, side="above", date="2026-01-01")
    rows = add([], t)
    assert resolve_due(rows, "2026-01-01", lambda s: (["2026-01-02"], [101.0])) == 0, "만기 전 해소 금지"
    assert resolve_due(rows, "2026-01-05", lambda s: (["2026-01-01"], [101.0])) == 0, "만기 뒤 종가 없으면 보류"
    assert resolve_due(rows, "2026-01-05", lambda s: (["2026-01-02"], [101.0])) == 1 and rows[0]["outcome"] == 1
    s = score(rows)["x"]
    assert abs(s["bs"] - 0.01) < 1e-9 and abs(s["base"] - 0.25) < 1e-9 and not s["stop"]
    bad = [dict(t, id=str(i), prob=0.9, outcome=0) for i in range(MIN_N)]
    assert score(bad)["x"]["stop"]
    try:
        add(bad, dict(t, id="z"))
    except SystemExit:
        pass
    else:
        raise AssertionError("🔴 범주가 새 예측을 받았다")
    assert abs(base_rate([100.0, 110.0, 100.0, 110.0], 1.05, 1, True) - 3 / 5) < 1e-9
    print("selftest OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="예측 원장·Brier 채점")
    ap.add_argument("--price", nargs=6, metavar=("이름", "심볼", "방향", "수준", "만기", "확률"), help="가격 판단(방향 = above|below)")
    ap.add_argument("--cat", help="범주")
    ap.add_argument("--claim", help="판단 문장")
    ap.add_argument("--event", metavar="JSON", help="사건 판단")
    ap.add_argument("--auto", action="store_true", help="만기 지난 가격 판단 해소")
    ap.add_argument("--resolve", nargs=2, metavar=("ID", "결과"), help="사건 판단 해소(1/0)")
    ap.add_argument("--note", help="해소 근거")
    ap.add_argument("--score", action="store_true", help="범주별 채점")
    ap.add_argument("--selftest", action="store_true", help="자가검증")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    rows = load()
    today = dt.date.today().isoformat()
    if a.price:
        name, sym, side, lv, by, p = a.price
        if side not in ("above", "below"):
            raise SystemExit("방향 = above|below")
        d, c = history(sym)
        h = max(1, int(round((dt.date.fromisoformat(by) - dt.date.fromisoformat(d[-1])).days * 5 / 7)))
        b = base_rate(c, float(lv) / c[-1], h, side == "above")
        t = dict(id=f"{name}-{side}-{lv}-{by}", date=today, category=a.cat, claim=a.claim or f"{name} {by} 종가 {side} {lv}",
                 by=by, prob=float(p), baseline=round(b, 3), baseline_src=f"최근 10년 {h}거래일 도달 빈도", kind="price",
                 ticker=sym, level=float(lv), side=side, ref_close=c[-1])
        rows = add(rows, t)
        print(f"등록 {t['id']} · 확률 {p} · 기준선 {t['baseline']}")
    if a.event:
        t = json.loads(a.event)
        if not t.get("baseline_src") or not t.get("rule"):
            raise SystemExit("event는 baseline_src·rule 필수")
        rows = add(rows, dict(t, date=t.get("date", today), kind="event"))
    if a.auto:
        print(f"해소 {resolve_due(rows, today)}건")
    if a.resolve:
        r = next((x for x in rows if x["id"] == a.resolve[0]), None)
        if not r or r.get("outcome") is not None or a.resolve[1] not in ("0", "1"):
            raise SystemExit("해소 불가 — id·결과 확인")
        r.update(outcome=int(a.resolve[1]), resolved_at=today, resolved_note=a.note)
    if a.price or a.event or a.auto or a.resolve:
        save(rows)
    if a.score or not (a.price or a.event or a.auto or a.resolve):
        print(f"원장 {len(rows)}건 · 미해소 {sum(r.get('outcome') is None for r in rows)}건")
        for k, o in score(rows).items():
            print(f"{k:10} {o['n']:3}건 · Brier {o['bs']:.3f} vs 기준선 {o['base']:.3f} · 스킬 {o['skill']:+.2f}" + (" 🔴 예측 중단" if o["stop"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
