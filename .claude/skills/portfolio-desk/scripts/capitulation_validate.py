#!/usr/bin/env python3
"""capitulation_validate.py — 항복 가산(×1.2) 검증 (stdlib only·측정 전용)

정훈 지시(2026-07-30): *"항복 가산도 검증할 방법 찾아봐."*

■ 문제 — 항복 가산만 검증에서 통째로 빠져 있었다
   `rule_tracker --multi`(17,946표본)는 **사다리 × 폭풍감산**만 검증했다.
   심리 데이터(`sentiment.json`)가 **2026-07-26부터**라 과거 재구성이 불가능했기 때문이다.
   그런데 7/30 2차 개정에서 폭풍 금액 감산을 폐지한 결과, **승수는 항복 가산만 남았다** —
   즉 **오늘 상한을 112,975 → 282,438원으로 2.5배 만든 장본인이 미검증 상태**다.

■ 검증 경로 2개 (서로 독립 — 같은 방향이면 신뢰, 갈리면 판정 보류)

   ① **실측 심리** — 네이버 데이터랩 트렌드가 **2016-01-01부터** 제공된다(7/30 실측).
      공포·항복 키워드 그룹의 주간 시계열 → %ile → 룰과 동일한 판정(둘 다 ≥90 = 항복 ON).
      ⚠️ 한계: 10.5년이라 D2+ 도달 국면이 2~3개뿐. **표본 극소.**
      ⚠️ 상대 정규화 — 한 요청 안에서 최댓값 100으로 정규화되므로 **전 기간을 1콜로** 받아야 한다.

   ② **VIX 프록시** — 36년치. VIX %ile ≥90을 '항복'의 대리변수로 쓴다.
      ⚠️ 한계: **미국 지표라 한국 리테일 심리와 다르다.** 2026년 7월이 정확히 그 반례 —
      코스피가 29년 최속으로 무너지는데 VIX는 19.4였다. 그래서 프록시로만 쓰고 정본으로 안 쓴다.

■ 판정 규율
   · 두 경로가 **같은 방향**일 때만 결론. 갈리면 "판정 불가"로 두고 가산을 유지한다
     (유지가 현상이므로, 근거 없이 바꾸지 않는 쪽이 보수적).
   · 표본·국면 수를 항상 병기. 국면 <5면 판정하지 않는다.
   · **자동 변경 ❌** — 개정 제안만, 확정은 정훈.

사용:
  python3 capitulation_validate.py --fetch          # 네이버 트렌드 2016~ 수집·캐시
  python3 capitulation_validate.py --naver          # ① 실측 심리 검증
  python3 capitulation_validate.py --vix            # ② VIX 프록시 검증
  python3 capitulation_validate.py                  # 둘 다 + 종합 판정
"""
from __future__ import annotations

import argparse
import bisect
import datetime as dt
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CACHE = os.path.join(ROOT, "data", "app", "sentiment_history.json")

KOSPI = "^KS11"
VIX = "^VIX"
HORIZONS = [(21, "1개월"), (63, "3개월"), (126, "6개월"), (252, "12개월")]
MIN_EPISODES = 5


# ─────────────────────────────────────────── ① 실측 심리 (네이버 2016~)

def fetch_history(start="2016-01-01", unit="week") -> dict:
    """공포·항복 그룹의 전 기간 트렌드를 **1콜**로 받는다(상대 정규화 때문에 분할 금지)."""
    import naver_sentiment as NS
    import naver_data as N

    groups = [g for g in NS.PSYCH_GROUPS if g["groupName"] in ("공포", "항복")]
    end = dt.date.today().isoformat()
    d = N.trend(groups, start, end, unit)
    series = {}
    for res in d.get("results", []):
        series[res.get("title")] = [(p["period"], p["ratio"]) for p in res.get("data", [])]
    payload = {"updated": dt.date.today().isoformat(), "start": start, "unit": unit,
               "note": "네이버 데이터랩 트렌드 1콜 수집(상대 정규화 — 분할 수집 시 비교 불가). "
                       "항복 가산 검증 전용.",
               "series": series}
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return payload


def _pctile_series(vals, window=52):
    """직전 window 구간 대비 백분위(룰이 쓰는 1년 %ile과 같은 문법)."""
    out = []
    for i, v in enumerate(vals):
        hist = vals[max(0, i - window):i]
        out.append(None if len(hist) < 20 else
                   sum(1 for x in hist if x <= v) / len(hist) * 100)
    return out


def naver_episodes():
    """항복 ON(공포·항복 둘 다 ≥90%ile) 주간 목록 → 코스피 전방수익률."""
    if not os.path.exists(CACHE):
        return None, "sentiment_history.json 없음 — --fetch 먼저 실행"
    with open(CACHE, encoding="utf-8") as f:
        d = json.load(f)
    ser = d.get("series") or {}
    if "공포" not in ser or "항복" not in ser:
        return None, "공포·항복 시계열 누락"

    fear = ser["공포"]
    capit = {p: v for p, v in ser["항복"]}
    periods = [p for p, _ in fear]
    fp = _pctile_series([v for _, v in fear])
    cp = _pctile_series([capit.get(p, 0) for p in periods])

    on = [periods[i] for i in range(len(periods))
          if fp[i] is not None and cp[i] is not None and fp[i] >= 90 and cp[i] >= 90]
    off = [periods[i] for i in range(len(periods))
           if fp[i] is not None and cp[i] is not None and not (fp[i] >= 90 and cp[i] >= 90)]
    return {"on": on, "off": off, "start": d.get("start"), "n_periods": len(periods)}, None


# ─────────────────────────────────────────── ② VIX 프록시

def vix_dates(threshold=90.0, window=252):
    """VIX %ile ≥ threshold 인 날짜(항복 대리변수)."""
    import drawdown_history as D
    vd, vc = D.load(VIX)
    if not vc:
        return [], []
    on, off = [], []
    for i in range(window, len(vc)):
        hist = vc[i - window:i]
        pct = sum(1 for x in hist if x <= vc[i]) / len(hist) * 100
        (on if pct >= threshold else off).append(vd[i])
    return on, off


# ─────────────────────────────────────────── 공통 채점

def _fwd(dates, closes, date_str, h):
    i = bisect.bisect_left(dates, date_str)
    if i >= len(dates) or i + h >= len(closes):
        return None
    return (closes[i + h] / closes[i] - 1) * 100


def _episodes(ds, gap_days=63):
    ds = sorted(ds)
    if not ds:
        return 0
    n = 1
    for a, b in zip(ds, ds[1:]):
        if (dt.date.fromisoformat(b[:10]) - dt.date.fromisoformat(a[:10])).days > gap_days:
            n += 1
    return n


def _compare(label, on_dates, off_dates, deep_only=False):
    """항복 ON vs OFF의 코스피 전방수익률 비교."""
    import drawdown_history as D
    dates, closes = D.load(KOSPI)
    if not closes:
        print("  ⚠️ 코스피 캐시 없음")
        return None

    # 사다리 해금 구간(D1 이상 = 낙폭 -25% 이하)만 보는 옵션 —
    # 항복 가산은 해금 구간에서만 실제로 금액에 영향을 주므로 그쪽이 진짜 검증 대상이다.
    dd = []
    m = closes[0]
    for c in closes:
        m = max(m, c)
        dd.append((c / m - 1) * 100)
    deep = {dates[i] for i in range(len(dates)) if dd[i] <= -25.0}

    rows = []
    for name, ds in (("항복 ON", on_dates), ("항복 OFF", off_dates)):
        use = [x for x in ds if (not deep_only or x[:10] in deep)]
        med = {}
        for h, _ in HORIZONS:
            vals = [v for v in (_fwd(dates, closes, x[:10], h) for x in use) if v is not None]
            med[h] = statistics.median(vals) if vals else None
        rows.append((name, len(use), _episodes([x[:10] for x in use]), med))

    scope = "해금 구간(낙폭 ≤ -25%)만" if deep_only else "전 구간"
    print(f"\n  [{label} · {scope}]")
    print(f"    {'구간':<10}{'표본':>7}{'국면':>6}" + "".join(f"{lbl:>10}" for _, lbl in HORIZONS))
    for name, n, ep, med in rows:
        line = f"    {name:<10}{n:>7}{ep:>6}"
        for h, _ in HORIZONS:
            line += f"{med[h]:>+9.1f}%" if med[h] is not None else f"{'—':>10}"
        print(line)

    on_row, off_row = rows[0], rows[1]
    if on_row[2] < MIN_EPISODES:
        print(f"    ⏳ 항복 ON 국면 {on_row[2]}개 < {MIN_EPISODES} — **판정 불가**(표본 부족)")
        return None
    a, b = on_row[3].get(252), off_row[3].get(252)
    if a is None or b is None:
        print("    ⏳ 12개월 전방 미확보 — 판정 불가")
        return None
    verdict = "🟢 가산 유효" if a > b else "🔴 가산 근거 없음"
    print(f"    → 12M: ON {a:+.1f}% vs OFF {b:+.1f}% (차 {a-b:+.1f}%p) → **{verdict}**")
    return a - b


def main():
    ap = argparse.ArgumentParser(description="항복 가산(×1.2) 검증 — 측정 전용")
    ap.add_argument("--fetch", action="store_true", help="네이버 트렌드 2016~ 수집")
    ap.add_argument("--naver", action="store_true")
    ap.add_argument("--vix", action="store_true")
    ap.add_argument("--start", default="2016-01-01")
    a = ap.parse_args()

    if a.fetch:
        d = fetch_history(a.start)
        n = {k: len(v) for k, v in d["series"].items()}
        print(f"\n💾 {os.path.relpath(CACHE, ROOT)} 저장 — {n} ({d['start']}~, {d['unit']})\n")
        return

    print("\n" + "=" * 74)
    print("  항복 가산(×1.2) 검증 — 두 독립 경로")
    print("=" * 74)
    print("  ⚠️ 이 가산은 7/30 2차 개정 후 **승수에 남은 유일한 조정 장치**다.")
    print("     오늘 상한을 112,975 → 282,438원으로 만든 장본인이므로 검증이 중요하다.")

    d_naver = d_vix = None

    if not a.vix:
        print("\n" + "─" * 74)
        print("  ① 실측 심리 (네이버 데이터랩 2016~) — 룰과 동일한 판정식")
        res, err = naver_episodes()
        if err:
            print(f"    ⚠️ {err}")
        else:
            print(f"    주간 {res['n_periods']}포인트 · 항복 ON {len(res['on'])}주 / OFF {len(res['off'])}주")
            _compare("① 네이버 실측", res["on"], res["off"])
            d_naver = _compare("① 네이버 실측", res["on"], res["off"], deep_only=True)

    if not a.naver:
        print("\n" + "─" * 74)
        print("  ② VIX 프록시 (36년) — 독립 교차검증")
        print("    ⚠️ 미국 지표라 한국 리테일 심리와 다르다. 2026년 7월이 정확한 반례 —")
        print("       코스피가 29년 최속으로 무너지는데 VIX는 19.4였다. 프록시일 뿐 정본 아님.")
        on, off = vix_dates()
        if on:
            _compare("② VIX ≥90%ile", on, off)
            d_vix = _compare("② VIX ≥90%ile", on, off, deep_only=True)
        else:
            print("    ⚠️ VIX 캐시 없음")

    print("\n" + "=" * 74)
    print("  종합 판정 (해금 구간 기준)")
    if d_naver is None and d_vix is None:
        print("    ⏳ **판정 불가** — 두 경로 모두 표본 부족.")
        print("       ⇒ 가산을 **유지**한다(근거 없이 바꾸지 않는 쪽이 보수적).")
    elif d_naver is not None and d_vix is not None:
        same = (d_naver > 0) == (d_vix > 0)
        print(f"    ① 네이버 {d_naver:+.1f}%p · ② VIX {d_vix:+.1f}%p → "
              + ("**같은 방향 — 결론 채택 가능**" if same else "**방향 상충 — 판정 보류·가산 유지**"))
    else:
        got = d_naver if d_naver is not None else d_vix
        print(f"    한 경로만 성립({got:+.1f}%p) — **단독 경로로는 확정하지 않는다.** 가산 유지.")
    print("    ※ 자동 변경 ❌ — 개정 제안만, 확정은 정훈.\n")


if __name__ == "__main__":
    main()
