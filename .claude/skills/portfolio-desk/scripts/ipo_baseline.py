#!/usr/bin/env python3
"""ipo_baseline.py — 대형 기술주 IPO 기저율 (측정 전용 · 룰 변경 없음 · 2026-11-19)

■ 왜
  정훈 11/19 *"앤트로픽 금요일 상장 예정 대응 준비 스페이스 x 사례 참고"* — 상장 첫날 시초가에 사면 어떻게 되나,
  기다리면 더 싸게 살 기회가 오나를 숫자로 본다. 개인이 실제로 잡을 수 있는 가격 = **첫날 시초가**(공모가 아님).

■ 측정
  · 진입 = 첫날 시초가(open) · 비교 = 공모가 · 첫날 종가
  · 1M/3M/6M/12M(21/63/126/252거래일) 뒤 종가 수익률 · 같은 기간 S&P500(^GSPC) 대비 초과
  · 6개월 안 최저 종가 ÷ 시초가(기다렸으면 얼마나 싸게 살 수 있었나) · 그 날짜(상장 후 며칠)
  ⚠️ 표본 = 이름 있는 대형 IPO 12건(선택 편향 — 망한 소형 IPO는 없다) · 이벤트 1건씩이라 통계 검정 아님.

사용:
  python ipo_baseline.py           # 표
  python ipo_baseline.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# (티커, 이름, 상장일, 공모가 $) — 공모가 = 공식 확정가
IPOS = [
    ("META", "Facebook", "2012-05-18", 38.0),
    ("BABA", "Alibaba", "2014-09-19", 68.0),
    ("UBER", "Uber", "2019-05-10", 45.0),
    ("SNOW", "Snowflake", "2020-09-16", 120.0),
    ("ABNB", "Airbnb", "2020-12-10", 68.0),
    ("RIVN", "Rivian", "2021-11-10", 78.0),
    ("ARM", "Arm", "2023-09-14", 51.0),
    ("RDDT", "Reddit", "2024-03-21", 34.0),
    ("CRWV", "CoreWeave", "2025-03-28", 40.0),
    ("CRCL", "Circle", "2025-06-05", 31.0),
    ("FIG", "Figma", "2025-07-31", 33.0),
    ("SPCX", "SpaceX", "2026-06-12", 135.0),
]
# --short(단기 매매) 표본 확대 — 미국 대형 IPO(직상장 제외). 공모가는 공식 확정가.
IPOS_EXTRA = [
    ("SNAP", "Snap", "2017-03-02", 17.0),
    ("DBX", "Dropbox", "2018-03-23", 21.0),
    ("LYFT", "Lyft", "2019-03-29", 72.0),
    ("PINS", "Pinterest", "2019-04-18", 19.0),
    ("ZM", "Zoom", "2019-04-18", 36.0),
    ("CRWD", "CrowdStrike", "2019-06-12", 34.0),
    ("U", "Unity", "2020-09-18", 52.0),
    ("DASH", "DoorDash", "2020-12-09", 102.0),
    ("BMBL", "Bumble", "2021-02-11", 43.0),
    ("CPNG", "Coupang", "2021-03-11", 35.0),
    ("HOOD", "Robinhood", "2021-07-29", 38.0),
    ("CART", "Instacart", "2023-09-19", 30.0),
    ("KVYO", "Klaviyo", "2023-09-20", 30.0),
    ("BIRK", "Birkenstock", "2023-10-11", 46.0),
    ("ALAB", "Astera Labs", "2024-03-20", 36.0),
    ("CHYM", "Chime", "2025-06-12", 27.0),
    ("KLAR", "Klarna", "2025-09-10", 40.0),
]
HORIZONS = (("1M", 21), ("3M", 63), ("6M", 126), ("12M", 252))
# 사전등록(trials.jsonl `ipo_flip` · 11/20) — 진입 4 × 보유 4 + 조건부 4 = 20
ENTRIES = (("첫날 시초", 0, "o"), ("첫날 종가", 0, "c"), ("2일 종가", 1, "c"), ("3일 종가", 2, "c"))
HOLDS = (1, 3, 5, 10)
COND = (("2일 종가 if 첫날 종가>시초", 1, lambda b: b[0][2] > b[0][1]),
        ("3일 종가 if 3일 종가>첫날 시초", 2, lambda b: b[2][2] > b[0][1]))
ERAS = (("2012-19", "2012", "2019-12-31"), ("2020-21", "2020", "2021-12-31"), ("2023-26", "2023", "2099"))


def _bars(sym, start):
    import history_backfill as hb
    t0 = int(time.mktime(time.strptime(start, "%Y-%m-%d"))) - 86400 * 3
    t1 = int(time.time())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
           f"?period1={t0}&period2={t1}&interval=1d&events=div%2Csplits")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=20))["chart"]["result"][0]
    off = d["meta"].get("gmtoffset", 0)
    q = d["indicators"]["quote"][0]
    adj = (d["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    out = []
    for i, ts in enumerate(d.get("timestamp") or []):
        o, c = q["open"][i], q["close"][i]
        if o is None or c is None:
            continue
        # 분할 보정: adjclose/close 비율로 open도 맞춘다(배당 효과는 작아 무시)
        k = (adj[i] / c) if adj and adj[i] else 1.0
        out.append((hb.bar_date(ts, off), o * k, c * k, k))
    return [b for b in out if b[0] >= start]


def measure():
    spx = {b[0]: b[2] for b in _bars("^GSPC", "2012-05-01")}
    rows = []
    for sym, name, day, offer in IPOS:
        try:
            b = _bars(sym, day)
        except Exception as e:  # noqa: BLE001
            rows.append({"ticker": sym, "name": name, "error": str(e)[:80]})
            continue
        if not b or b[0][0] != day:
            rows.append({"ticker": sym, "name": name, "error": f"첫 봉 {b[0][0] if b else '없음'} ≠ {day}"})
            continue
        k0 = b[0][3]
        o, c = b[0][1], b[0][2]
        offer_adj = offer * k0
        r = {"ticker": sym, "name": name, "date": day, "offer": offer,
             "open_vs_offer": round((o / offer_adj - 1) * 100, 1),
             "close_vs_open": round((c / o - 1) * 100, 1)}
        for lab, n in HORIZONS:
            if len(b) > n:
                d2 = b[n][0]
                ret = b[n][2] / o - 1
                s0 = spx.get(day)
                s1 = spx.get(d2)
                r[lab] = round(ret * 100, 1)
                r[lab + "_xs"] = None if not (s0 and s1) else round((ret - (s1 / s0 - 1)) * 100, 1)
            else:
                r[lab] = r[lab + "_xs"] = None
        w = b[1:127]
        if w:
            lo = min(w, key=lambda x: x[2])
            r["min6m_vs_open"] = round((lo[2] / o - 1) * 100, 1)
            r["min6m_day"] = b.index(lo)
        rows.append(r)
    return rows


def _med(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def show(rows):
    f = lambda x: "—" if x is None else f"{x:+.1f}"
    print("── 대형 IPO 기저율 — 진입 = 첫날 시초가 · xs = S&P500 대비 초과(%p)")
    print(f"{'종목':<10}{'시초/공모':>9}{'첫날종가/시초':>12}{'1M':>7}{'3M':>7}{'6M':>7}{'6M xs':>7}{'12M':>7}{'12M xs':>7}{'6M 최저':>8}{'(일)':>5}")
    for r in rows:
        if r.get("error"):
            print(f"{r['name']:<10} 오류: {r['error']}")
            continue
        print(f"{r['name']:<10}{f(r['open_vs_offer']):>9}{f(r['close_vs_open']):>12}{f(r['1M']):>7}{f(r['3M']):>7}"
              f"{f(r['6M']):>7}{f(r['6M_xs']):>7}{f(r['12M']):>7}{f(r['12M_xs']):>7}{f(r.get('min6m_vs_open')):>8}{r.get('min6m_day', '—'):>5}")
    ok = [r for r in rows if not r.get("error")]
    print(f"{'중앙값':<10}{f(_med([r['open_vs_offer'] for r in ok])):>9}{f(_med([r['close_vs_open'] for r in ok])):>12}"
          f"{f(_med([r['1M'] for r in ok])):>7}{f(_med([r['3M'] for r in ok])):>7}{f(_med([r['6M'] for r in ok])):>7}"
          f"{f(_med([r['6M_xs'] for r in ok])):>7}{f(_med([r['12M'] for r in ok])):>7}{f(_med([r['12M_xs'] for r in ok])):>7}"
          f"{f(_med([r.get('min6m_vs_open') for r in ok])):>8}")
    neg6 = sum(1 for r in ok if r.get("6M_xs") is not None and r["6M_xs"] < 0)
    n6 = sum(1 for r in ok if r.get("6M_xs") is not None)
    below = sum(1 for r in ok if r.get("min6m_vs_open") is not None and r["min6m_vs_open"] <= -20)
    print(f"6M S&P 대비 패배 {neg6}/{n6} · 6개월 안에 시초가 -20% 이하 기회 {below}/{len(ok)}")
    print("⚠️ 선택 편향(이름 있는 대형 IPO만) · 이벤트 1건씩 = 검정 아님")


def _binom_p(k, n):
    """단측: 승 k/n이 50%보다 클 확률의 p."""
    from math import comb
    return sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0


def _holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def measure_short():
    """상장 초반 단기 매매 — 진입·보유 변형별 S&P 대비 초과(%p) 분포."""
    spx = {b[0]: b[2] for b in _bars("^GSPC", "2012-05-01")}
    sdays = sorted(spx)
    events, skipped = [], []
    for sym, name, day, offer in IPOS + IPOS_EXTRA:
        try:
            b = _bars(sym, day)
        except Exception as e:  # noqa: BLE001
            skipped.append(f"{name}: {str(e)[:40]}")
            continue
        if not b or b[0][0] != day or len(b) < 14:
            skipped.append(f"{name}: 첫 봉 {b[0][0] if b else '없음'}")
            continue
        k0 = b[0][3]
        below = min(x[2] for x in b[:21]) / (offer * k0) - 1  # 20거래일 안 최저 종가 ÷ 공모가
        events.append({"name": name, "date": day, "bars": b, "below_offer_20d": round(below * 100, 1),
                       "open_vs_offer": round((b[0][1] / (offer * k0) - 1) * 100, 1)})

    def spx_ret(d0, d1):
        a = spx.get(d0) or spx.get(max([d for d in sdays if d <= d0] or [None]) or "")
        z = spx.get(d1) or spx.get(max([d for d in sdays if d <= d1] or [None]) or "")
        return (z / a - 1) if (a and z) else 0.0

    variants = []
    for lab, ei, px in ENTRIES:
        for h in HOLDS:
            variants.append((f"{lab} → {h}일", ei, px, h, None))
    for lab, ei, cond in COND:
        for h in (5, 10):
            variants.append((f"{lab} → {h}일", ei, "c", h, cond))
    out = []
    for name, ei, px, h, cond in variants:
        xs, raw, eras = [], [], {e[0]: [] for e in ERAS}
        for ev in events:
            b = ev["bars"]
            if len(b) <= ei + h or (cond and not cond(b)):
                continue
            p0 = b[ei][1] if px == "o" else b[ei][2]
            d0 = b[ei][0] if px == "c" else (b[ei - 1][0] if ei else None)
            p1 = b[ei + h][2]
            r = p1 / p0 - 1
            # 시초 진입의 벤치 기준 = 전일 S&P 종가(같은 날 시초 S&P는 없다)
            base_day = d0 or max(d for d in sdays if d < b[0][0])
            x = (r - spx_ret(base_day, b[ei + h][0])) * 100
            xs.append(x)
            raw.append(r * 100)
            for en, lo, hi in ERAS:
                if lo <= ev["date"][:4] <= hi[:4] or (lo <= ev["date"] <= hi):
                    eras[en].append(x)
                    break
        n = len(xs)
        k = sum(1 for x in xs if x > 0)
        srt = sorted(xs)
        out.append({"variant": name, "n": n, "mean_xs": round(sum(xs) / n, 2) if n else None,
                    "median_xs": round(_med(xs), 2) if n else None, "win": k,
                    "p": _binom_p(k, n), "worst10": round(srt[max(0, int(n * 0.1) - 1)], 1) if n else None,
                    "best": round(srt[-1], 1) if n else None,
                    "era_mean": {e: (round(sum(v) / len(v), 1) if v else None) for e, v in eras.items()},
                    "mean_raw": round(sum(raw) / n, 2) if n else None})
    adj = _holm([o["p"] for o in out])
    for o, a in zip(out, adj):
        o["holm"] = round(a, 3)
    return {"events": [{k: v for k, v in e.items() if k != "bars"} for e in events], "skipped": skipped,
            "variants": out}


def show_short(res):
    ev = res["events"]
    print(f"── 상장 초반 단기 매매 — 표본 {len(ev)}건 · 초과 = S&P500 대비 %p · 사전등록 ipo_flip(20 변형)")
    if res["skipped"]:
        print("   제외:", " · ".join(res["skipped"]))
    print(f"{'변형':<30}{'n':>3}{'평균':>7}{'중앙':>7}{'승':>6}{'하위10%':>8}{'최고':>7}{'Holm':>7}  시기별 평균(12-19 / 20-21 / 23-26)")
    for o in res["variants"]:
        e = o["era_mean"]
        f = lambda x: "—" if x is None else f"{x:+.1f}"
        print(f"{o['variant']:<30}{o['n']:>3}{f(o['mean_xs']):>7}{f(o['median_xs']):>7}{o['win']:>3}/{o['n']:<2}"
              f"{f(o['worst10']):>8}{f(o['best']):>7}{o['holm']:>7.3f}  {f(e['2012-19'])} / {f(e['2020-21'])} / {f(e['2023-26'])}")
    bo = [e["below_offer_20d"] for e in ev]
    print(f"20거래일 안 종가가 공모가 아래로 간 건: {sum(1 for x in bo if x < 0)}/{len(bo)} · 중앙 최저 {_med(bo):+.1f}% (공모가 대비)")


def main():
    ap = argparse.ArgumentParser(description="대형 기술주 IPO 기저율 — 첫날 시초가 진입 (측정 전용)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--short", action="store_true", help="상장 초반 단기 매매(사전등록 ipo_flip 20 변형) — 표본 약 29건")
    a = ap.parse_args()
    if a.short:
        res = measure_short()
        print(json.dumps(res, ensure_ascii=False, indent=1) if a.json else "", end="")
        if not a.json:
            show_short(res)
        return
    rows = measure()
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        show(rows)


if __name__ == "__main__":
    main()
