#!/usr/bin/env python3
"""단기 가격 범위 = ATR 기계값 고정 (11/2 정훈 승인 — 사람 판단의 주간·월간 방향 폐지).

`forecast_score.py` 첫 채점: 주간 방향 25.0%(48건) vs 항상 상승 39.6% · 범위 이탈이 아래로 쏠림.
⇒ 범위는 변동폭 참고값이지 예측이 아니다. dir은 항상 '→'. 손으로 고치지 말고 이걸 돌린다.

  python forecast_band.py          # 미리보기
  python forecast_band.py --write  # stocks.json forecast · tasks.json index_forecast 갱신
  python forecast_band.py --coverage  # 과거 범위 적중률(이 범위가 몇 % 구간인지)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *([os.pardir] * 4)))
WEEK, MONTH = 1.3, 2.6
INDEX = {"if-kospi": "_KS11", "if-kosdaq": "_KQ11", "if-sp500": "_GSPC", "if-sox": "_SOX"}


def rows(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def series(sym: str) -> tuple[list[float], list[float], list[float]]:
    """(고가, 저가, 종가). OHLC가 없으면 종가만 — 고가=저가=종가라 TR이 종가 간 변동이 된다."""
    name = sym.replace("^", "_") + ".csv"
    r = [x for x in rows(os.path.join(ROOT, "data", "history_ohlcv", name)) if x.get("high") and x.get("low") and x.get("close")]
    if len(r) > 30:
        return [float(x["high"]) for x in r], [float(x["low"]) for x in r], [float(x["close"]) for x in r]
    c = [float(x["close"]) for x in rows(os.path.join(ROOT, "data", "history", name)) if x.get("close")]
    return c, c, c


def atr(h: list[float], l: list[float], c: list[float], end: int, n: int = 14) -> float:
    """end(포함)까지의 값만 읽는다."""
    tr = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(end - n + 1, end + 1)]
    return sum(tr) / n


def band(sym: str) -> dict | None:
    h, l, c = series(sym)
    if len(c) < 20:
        return None
    a, p = atr(h, l, c, len(c) - 1), c[-1]
    # 기준가 = 매일 갱신되는 종가 캐시(data/history)의 마지막 값. OHLCV 캐시는 주간(R3)에만 갱신돼
    # 그걸 기준가로 쓰면 범위가 며칠 전 가격에 고정된다(11/3: AVGO 범위 하단 > 현재가). ATR은 OHLCV 그대로.
    last = [float(x["close"]) for x in rows(os.path.join(ROOT, "data", "history", sym.replace("^", "_") + ".csv")) if x.get("close")]
    if last:
        p = last[-1]
    return dict(ref=p, week=(p - WEEK * a, p + WEEK * a), month=(p - MONTH * a, p + MONTH * a))


def rnd(x: float, ref: float) -> float:
    return round(x, 2) if ref < 5000 else round(x, -1)


def coverage() -> None:
    for sym in ("_KS11", "_GSPC", "NVDA", "005930.KS"):
        h, l, c = series(sym)
        for k, n, lab in ((WEEK, 5, "5일"), (MONTH, 21, "21일")):
            idx = range(20, len(c) - n, 5)
            hit = sum(abs(c[i + n] - c[i]) <= k * atr(h, l, c, i) for i in idx)
            print(f"{sym:10} {lab:4} ±{k}ATR 범위 안 {hit / len(idx) * 100:5.1f}% ({len(idx)}건)")


def main() -> int:
    ap = argparse.ArgumentParser(description="단기 범위 ATR 기계값")
    ap.add_argument("--write", action="store_true", help="정본 JSON 갱신")
    ap.add_argument("--coverage", action="store_true", help="과거 범위 적중률")
    a = ap.parse_args()
    if a.coverage:
        coverage()
        return 0
    sp = os.path.join(ROOT, "data", "app", "stocks.json")
    tp = os.path.join(ROOT, "data", "app", "tasks.json")
    s = json.load(open(sp, encoding="utf-8"))
    t = json.load(open(tp, encoding="utf-8"))
    for tk, v in s["stocks"].items():
        b = band(tk)
        if not b:
            print(f"{tk}: 이력 없음 — 범위 비움")
            v.pop("forecast", None)
            continue
        p = b["ref"]
        v["forecast"] = {hz: {"low": rnd(b[hz][0], p), "high": rnd(b[hz][1], p), "dir": "→",
                              "note": f"ATR 기계 범위(±{k}배) — 변동폭 참고 · 예측 아님"}
                         for hz, k in (("week", WEEK), ("month", MONTH))}
        print(f"{tk}: 주간 {v['forecast']['week']['low']:,}~{v['forecast']['week']['high']:,}")
    for f in t.get("index_forecast") or []:
        b = band(INDEX.get(f.get("id"), "_없음"))
        if not b:
            continue
        p = b["ref"]
        lo, hi = rnd(b["week"][0], p), rnd(b["week"][1], p)
        f.update(ref=round(p, 2), low=lo, high=hi, base=round(p, 2), dir="→", range=f"{lo:,.0f}~{hi:,.0f}",
                 note=f"ATR 기계 범위(±{WEEK}배) — 변동폭 참고 · 예측 아님", confidence="기계")
        print(f"{f.get('label')}: {f['range']}")
    if a.write:
        for p, d in ((sp, s), (tp, t)):
            with open(p, "w", encoding="utf-8", newline="") as w:
                w.write(json.dumps(d, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
