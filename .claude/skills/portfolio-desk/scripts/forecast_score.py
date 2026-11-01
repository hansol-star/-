#!/usr/bin/env python3
"""단기 가격 예측 채점 — stocks.json `forecast`·tasks.json `index_forecast`의 git 이력을 사후 대조(11/1).

그동안 목표가·별점은 채점했지만 **매일 쓰는 주간·월간 예상 범위와 방향은 아무도 채점하지 않았다.**
측정 전용 — 어떤 룰도 바꾸지 않는다.

  · 같은 종목·같은 범위가 여러 커밋에 복제되면 처음 나온 날 1건으로 센다.
  · 지평 = 주간 5거래일 · 월간 21거래일 · 지표 = 만기 종가가 범위 안인가 · 방향 적중.
  · 대조군 = 같은 표본에서 '항상 오른다'고 말한 경우(상승 기저율).
  ⚠️ 종목×날짜는 독립이 아니다 — 유효 표본은 건수보다 훨씬 작다.

  python forecast_score.py [--save 경로.json]
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *([os.pardir] * 4)))
HIST = os.path.join(ROOT, "data", "history")
UP, DOWN = set("↑↗▲"), set("↓↘▼")
HORIZON = {"week": 5, "month": 21}
INDEX = {"if-kospi": "_KS11", "if-kosdaq": "_KQ11", "if-sp500": "_GSPC", "if-sox": "_SOX"}


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def versions(path: str, since: str = "2026-06-01") -> list[tuple[str, dict]]:
    """날짜별 마지막 커밋의 파일. 키 = KST 커밋일."""
    rows = [ln.split() for ln in git("log", f"--since={since}", "--format=%H %cI", "--", path).splitlines()]
    seen, out = set(), []
    for h, iso in rows:  # 최신 → 과거
        d = datetime.fromisoformat(iso).astimezone(KST).strftime("%Y-%m-%d")
        if d in seen:
            continue
        seen.add(d)
        try:
            out.append((d, json.loads(git("show", f"{h}:{path}").lstrip("﻿"))))
        except ValueError:
            continue
    return sorted(out, key=lambda x: x[0])


def history(sym: str):
    p = os.path.join(HIST, sym.replace("^", "_") + ".csv")
    if not os.path.exists(p):
        return None
    d, c = [], []
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                c.append(float(r["close"]))
                d.append(r["date"])
            except (TypeError, ValueError):
                continue
    return d, c


def grade(h, date: str, low: float, high: float, n: int, direction: str | None = None):
    i = bisect.bisect_right(h[0], date) - 1
    if i < 0 or i + n >= len(h[1]):
        return None
    p0, p1 = h[1][i], h[1][i + n]
    if not 0.2 < p0 / ((low + high) / 2) < 5:  # 단위가 어긋난 행(분할 등) 제외
        return None
    up = p1 > p0
    r = dict(inside=low <= p1 <= high, up=up, width=(high - low) / p0, ret=p1 / p0 - 1, above=p1 > high, below=p1 < low)
    if direction and direction[0] in UP | DOWN:
        r["dir_ok"] = up == (direction[0] in UP)
    return r


def summarize(name: str, rows: list[dict]) -> dict:
    if not rows:
        return dict(name=name, n=0)
    n = len(rows)
    d = [r for r in rows if "dir_ok" in r]
    base = sum(r["up"] for r in d) / len(d) if d else None
    out = dict(name=name, n=n, tickers=len({r["t"] for r in rows}), inside=round(sum(r["inside"] for r in rows) / n * 100, 1),
               above=round(sum(r["above"] for r in rows) / n * 100, 1), below=round(sum(r["below"] for r in rows) / n * 100, 1),
               width=round(sorted(r["width"] for r in rows)[n // 2] * 100, 1), dir_n=len(d),
               dir_hit=round(sum(r["dir_ok"] for r in d) / len(d) * 100, 1) if d else None,
               always_up=round(base * 100, 1) if d else None)
    print(f"{name:14} {n:4}건 {out['tickers']:2}종목 · 범위 안 {out['inside']:5}% (위 {out['above']} / 아래 {out['below']}) · 폭 중앙 {out['width']}%"
          f" · 방향 {out['dir_hit']}% vs 항상상승 {out['always_up']}% ({out['dir_n']}건)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="단기 가격 예측 채점(측정 전용)")
    ap.add_argument("--save", help="결과 JSON 경로")
    a = ap.parse_args()
    seen, rows = set(), {"week": [], "month": []}
    for date, s in versions("data/app/stocks.json"):
        for t, v in (s.get("stocks") or {}).items():
            for hz, f in (v.get("forecast") or {}).items():
                if hz not in HORIZON or not isinstance(f, dict) or not f.get("low") or not f.get("high"):
                    continue
                k = (t, hz, f["low"], f["high"])
                if k in seen:
                    continue
                seen.add(k)
                h = history(t)
                g = h and grade(h, date, float(f["low"]), float(f["high"]), HORIZON[hz], str(f.get("dir") or ""))
                if g:
                    g.update(t=t, date=date, mech="ATR" in str(f.get("note")))
                    rows[hz].append(g)
    idx, seen = [], set()
    for date, t in versions("data/app/tasks.json"):
        for f in t.get("index_forecast") or []:
            sym = INDEX.get(f.get("id"))
            m = re.findall(r"[\d,]+(?:\.\d+)?", str(f.get("range")))
            if not sym or len(m) < 2:
                continue
            lo, hi = float(m[0].replace(",", "")), float(m[1].replace(",", ""))
            k = (sym, lo, hi)
            if k in seen:
                continue
            seen.add(k)
            h = history(sym)
            g = h and grade(h, date, lo, hi, 5)
            if g:
                g.update(t=sym, date=date)
                idx.append(g)
    res = [summarize("주간(전체)", rows["week"]), summarize("월간(전체)", rows["month"]),
           summarize("주간(사람판단)", [r for r in rows["week"] if not r["mech"]]), summarize("주간(ATR기계)", [r for r in rows["week"] if r["mech"]]),
           summarize("월간(사람판단)", [r for r in rows["month"] if not r["mech"]]), summarize("월간(ATR기계)", [r for r in rows["month"] if r["mech"]]),
           summarize("지수 5일", idx)]
    if a.save:
        with open(a.save, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
