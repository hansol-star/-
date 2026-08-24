#!/usr/bin/env python3
"""multiple_backtest.py — 목표가 배수 선택의 역사적 검증 (기다리지 않고 지금 채점)

배경 [8/8 정훈 지적 — "자료들을 구해서 하면 안 되나, 데이터 쌓이길 기다리는 것보다"]:
`target_score.py`는 우리가 낸 목표가를 사후 채점하지만 원장이 6/20 시작이라
**20거래일 지평 하나**뿐이다. 12개월 목표를 제대로 채점하려면 몇 달을 기다려야 한다.
⇒ 기다리는 대신 **우리 방법론(EPS × 배수)을 과거에 적용해** 지금 검증한다.

데이터는 이미 있다: 가격은 수십 년(`data/history/`, MSFT 1986~·MU 1984~),
EPS는 EDGAR companyfacts가 **전 시계열**을 준다(무키). `financials.json`이 5기/8기로
자를 뿐 원본은 깊다 — 여기서는 `edgar_facts.fetch()`로 직접 받는다.

방법:
  ① 분기 희석EPS → **TTM EPS**(4분기 롤링) 시계열 구성
  ② 각 시점 T에서 합성 목표가 = TTM_EPS(T) × 배수 m  (m을 격자로 훑는다)
  ③ T+horizon(기본 250거래일 ≈ 12개월) 실제 주가와 대조
  ④ **오차를 최소화하는 m** = 그 종목의 '역사적으로 정당했던 배수'
  ⑤ 우리가 지금 쓰는 배수가 그 분포의 어디인지 백분위로 표시

핵심 산출 = **우리 배수가 역사적 정당 구간 안인가, 위인가.**
위면 낙관 편향이 배수 선택에서 온다는 뜻이고, 안이면 편향의 원인은 EPS 추정 쪽이다.

⚠️ 한계(반드시 같이 읽을 것):
  · TTM EPS(후행)로 검증한다. 실제 우리 목표가는 **컨센 EPS(선행)** 기반이라 축이 다르다.
    ⇒ 이 결과는 '배수 자체의 타당 범위'이지 우리 목표가의 정오 판정이 아니다.
  · 생존편향 없음(보유 종목만 봄 = 이미 살아남은 기업). 절대 수준을 일반화하지 말 것.
  · 국내주는 EDGAR 미대상이라 제외(EPS 깊은 이력이 없다).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
HIST = os.path.join(ROOT, "data/history")
CACHE = os.path.join(ROOT, "data/financials/_ttm_cache.json")
sys.path.insert(0, HERE)

# 8/8 우리가 채택한 배수 (target_basis 기준) — **선행(컨센) EPS 기준**이다
OURS = {"NVDA": (20, 26), "META": (19, 24), "MSFT": (23, 28), "AAPL": (28, 34),
        "GOOGL": (26, 31), "MU": (7, 10), "AVGO": (22, 27), "ORCL": (14, 17.5),
        "ANET": (40, 47)}
# 8/8 채택 목표가 절대값 — 이걸 최신 TTM EPS로 나눠 **후행 축으로 환산**해야
# 역사 밴드와 사과 대 사과 비교가 된다(아래 §축 정합 참조).
OUR_TARGET = {"NVDA": (260, 335), "META": (650, 815), "MSFT": (540, 655),
              "AAPL": (270, 325), "GOOGL": (385, 455), "MU": (1090, 1555),
              "AVGO": (430, 525), "ORCL": (150, 190), "ANET": (205, 240)}


_SPLIT_CACHE = {}


def yahoo_splits(tk):
    """Yahoo chart API에서 분할 이벤트 [(YYYY-MM-DD, ratio)]. 무키.
    EDGAR EPS(당시 보고치)를 분할조정 가격축에 맞추는 데 쓴다."""
    if tk in _SPLIT_CACHE:
        return _SPLIT_CACHE[tk]
    import urllib.request
    from datetime import datetime, timezone
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.request.quote(tk)
           + "?interval=1d&range=40y&events=split")
    out = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
        ev = (d["chart"]["result"][0].get("events") or {}).get("splits") or {}
        for v in ev.values():
            ts = v.get("date")
            num, den = v.get("numerator"), v.get("denominator")
            if ts and num and den:
                day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
                out.append((day, num / den))
    except Exception:
        out = []
    out.sort()
    _SPLIT_CACHE[tk] = out
    return out


def prices(tk):
    p = os.path.join(HIST, tk.replace("^", "_") + ".csv")
    out = []
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    out.append((r["date"], float(r["close"])))
                except (ValueError, KeyError, TypeError):
                    continue
        out.sort()
    return out


def eps_facts(tk):
    """분기 희석EPS를 **(기말, filed, 값)** 으로. companyfacts 재사용(추가 호출 없음).

    ★[8/24] `filed`가 왜 필요한가 — **EDGAR는 분할 후 과거 EPS를 소급 조정해 재보고한다.**
    후속 보고서의 비교 컬럼에 실린 분기만 다시 신고되므로, 한 시계열 안에
    **원본·1차 조정·2차 조정이 섞인다**. NVDA 실측(24분기):
      · 2020-04-26 = 1.47 (원본, filed 2021-05)      → 40배 보정 필요
      · 2020-07-26 = 0.25 (4:1 조정본, filed 2021-08) → 10배만 필요한데 40배 적용 = **4배 과소**
      · 2023-10-29 = 0.37 (10:1 조정본, filed 2024-11) → 보정 불필요한데 10배 적용 = **10배 과소**
    기말일 기준으로 보정하면 6/24분기가 틀린다(PE가 4~10배 과대).
    ⇒ **filed 이후에 일어난 분할만** 적용하는 것이 유일하게 옳은 규칙이다
      (filed 이전 분할은 이미 그 보고값에 반영돼 있다).
    """
    import edgar_facts as EF
    cik = EF.cik_map().get(tk.upper())
    if not cik:
        return []
    try:
        cf = EF.company_facts(cik)
    except Exception:
        return []
    units = ((((cf.get("facts") or {}).get("us-gaap") or {})
              .get("EarningsPerShareDiluted") or {}).get("units") or {})
    best = {}
    for f in (units.get("USD/shares") or []):
        if f.get("form") not in ("10-Q", "10-K"):
            continue
        st, en = f.get("start"), f.get("end")
        if not st or not en:
            continue
        try:
            span = (dt.date.fromisoformat(en) - dt.date.fromisoformat(st)).days
        except ValueError:
            continue
        if not (80 <= span <= 100):        # 분기 팩트만(연간·반기 제외)
            continue
        prev = best.get(en)
        if prev is None or (f.get("filed") or "") > (prev[0] or ""):
            best[en] = (f.get("filed"), f.get("val"))
    return sorted((en, fi, v) for en, (fi, v) in best.items() if v is not None)


def ttm_series(tk, cache):
    """분기 희석EPS → TTM EPS [(기말일, ttm_eps)]. EDGAR 전 시계열 사용.

    ⚠️ [8/8 보정 → 8/24 정정] **주식분할**. Yahoo 가격 이력은 분할조정(현재 주식수 기준)이다.
    8/8엔 "EDGAR EPS는 **당시 보고치**"라 전제하고 기말일 기준으로 나눴는데, 그 전제가 반만 맞다 —
    **EDGAR는 분할 후 과거 EPS를 소급 조정해 재보고**하므로 한 시계열에 원본과 조정본이 섞인다.
    기말일 기준 보정은 이미 조정된 분기를 **또** 나눠 NVDA 24분기 중 6개를 4~10배 과소로 만들었다.
    ⇒ 8/24부터 **filed(보고일) 기준**으로 그 이후 분할만 적용한다(`eps_facts` 주석). 그대로 PE를 만들면 분할한 종목이 전부 망가진다 —
    첫 실행에서 NVDA 실현PE **1.6배**, AAPL 4.7, GOOGL 2.3처럼 불가능한 값이 나왔고
    '상단초과' 5종목이 정확히 분할 종목이었다.
    ⇒ 분할 이력을 **Yahoo에서 직접** 받아(무키·권위 있음) 그 시점 이전 EPS를
      누적 분할배수로 나눈다.
      ⚠️ `shares_diluted` 급등으로 추론하는 방식은 **실패했다**(1차 시도) —
      GOOGL은 초기 주식수가 아예 `None`이라 2022년 20:1 분할을 못 잡았고(실현PE 2.3),
      AAPL은 대규모 자사주 매입이 섞여 배수가 어긋났다(6.6). 추론 대신 실제 이벤트를 쓴다.
    """
    if tk in cache:
        return [(d, v) for d, v in cache[tk]]
    rows = eps_facts(tk)                   # [(기말, filed, 값)]
    if not rows:                           # 폴백 — filed를 못 얻으면 기존 경로(정확도 낮음)
        import edgar_facts
        rec = edgar_facts.fetch(tk)
        q = rec.get("quarterly") or []
        rows = [(x["end"], None, x.get("eps_diluted"))
                for x in sorted(q, key=lambda z: z["end"]) if x.get("eps_diluted")]

    splits = yahoo_splits(tk)              # [(YYYY-MM-DD, ratio)]

    def factor_after(d):
        """d **이후** 일어난 분할의 누적배수. d = 보고일(filed)이지 기말일이 아니다.
        기말일을 쓰면 '기말 후 재보고로 이미 조정된 값'을 또 나눠 이중 조정된다(8/24 실측)."""
        f = 1.0
        for sd, r in splits:
            if sd > d:
                f *= r
        return f

    # filed가 없으면(폴백) 기말일로 근사 — 부정확할 수 있음을 감수
    adj = [(d, (v / factor_after(fi or d)) if v is not None else None)
           for d, fi, v in rows]
    out = []
    for i in range(3, len(adj)):
        vals = [adj[j][1] for j in range(i - 3, i + 1)]
        if any(v is None for v in vals):
            continue
        ttm = sum(vals)
        if ttm > 0:                       # 적자 구간은 PE가 의미 없다
            out.append((adj[i][0], ttm))
    cache[tk] = out
    return out


def backtest(tk, cache, horizon=250, grid=None):
    """각 분기말 T에서 'TTM_EPS × m'이 T+horizon 실제가와 얼마나 맞았나."""
    grid = grid or [x / 2 for x in range(4, 121)]      # 2.0 ~ 60.0배, 0.5 간격
    px = prices(tk)
    ttm = ttm_series(tk, cache)
    if not px or len(ttm) < 6:
        return None
    dates = [d for d, _ in px]

    pairs = []          # (eps, 미래가)
    for end, eps in ttm:
        i = next((k for k, d in enumerate(dates) if d >= end), None)
        if i is None or i + horizon >= len(px):
            continue
        pairs.append((eps, px[i + horizon][1], px[i][1]))
    if len(pairs) < 5:
        return None

    # 각 배수의 중앙 절대 백분율 오차(MAPE) — 이상치에 강하게 중앙값 사용
    best, curve = None, []
    for m in grid:
        errs = [abs(eps * m - fut) / fut for eps, fut, _ in pairs]
        e = st.median(errs)
        curve.append((m, e))
        if best is None or e < best[1]:
            best = (m, e)
    # 오차가 최저의 1.25배 이내인 배수 구간 = '정당 구간'
    lo_e = best[1] * 1.25
    ok = [m for m, e in curve if e <= lo_e]
    # 실현 배수 분포(미래가 ÷ 그때 TTM EPS) — 사후적으로 시장이 매긴 배수
    realized = sorted((fut / eps) for eps, fut, _ in pairs)
    return {"n": len(pairs), "best_m": best[0], "best_err": best[1],
            "band": (min(ok), max(ok)) if ok else None,
            "realized_p25": realized[len(realized) // 4],
            "realized_med": st.median(realized),
            "realized_p75": realized[3 * len(realized) // 4],
            "span": (ttm[0][0], ttm[-1][0])}


def pct_rank(vals, x):
    return 100.0 * sum(1 for v in vals if v <= x) / len(vals)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tickers", default=",".join(OURS))
    ap.add_argument("--horizon", type=int, default=250, help="검증 지평(거래일·기본 250≈12M)")
    ap.add_argument("--save", action="store_true",
                    help="역사 정당배수 밴드를 data/app/multiple_bands.json에 저장(validate가 소비)")
    a = ap.parse_args()

    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE, encoding="utf-8"))
        except Exception:
            cache = {}

    print("=" * 88)
    print(f"  목표가 배수의 역사적 검증 — 지평 +{a.horizon}거래일(≈{a.horizon/250*12:.0f}개월)")
    print("=" * 88)
    print("  방법: 각 분기말 TTM EPS × 배수 = 합성 목표가 → 지평 후 실제가와 대조")
    print("  ⚠️ TTM(후행) 기준이라 '배수의 타당 범위'를 보는 것 — 우리 목표가의 정오 판정이 아니다.\n")
    print(f"  {'종목':8s}{'표본':>5}{'기간':>20}{'역사 정당구간':>12}"
          f"{'실현PE중앙':>10}{'우리목표→TTM':>13}{'판정':>11}")
    print("  " + "-" * 82)

    rows = []
    for tk in [x.strip() for x in a.tickers.split(",") if x.strip()]:
        try:
            r = backtest(tk, cache, horizon=a.horizon)
        except Exception as e:
            print(f"  {tk:8s}  실패: {str(e)[:50]}")
            continue
        if not r:
            print(f"  {tk:8s}  표본 부족(EPS 이력 또는 지평 미달)")
            continue
        band = r["band"]
        # ★축 정합: 우리 목표가는 **선행 EPS** 기준이라 배수를 그대로 비교하면 안 된다.
        #   목표가 절대값 ÷ **최신 TTM EPS** = 후행 축 내재배수 → 역사 밴드와 직접 비교.
        tgt = OUR_TARGET.get(tk)
        ttm_now = cache[tk][-1][1] if cache.get(tk) else None
        imp = (tgt[0] / ttm_now, tgt[1] / ttm_now) if (tgt and ttm_now) else None
        verdict = "—"
        if imp and band:
            if imp[0] >= band[0] and imp[1] <= band[1]:
                verdict = "🟢 구간내"
            elif imp[0] > band[1]:
                verdict = "🔴 상단초과"
            elif imp[1] < band[0]:
                verdict = "🔵 보수적"
            else:
                verdict = "🟡 부분겹침"
        print(f"  {tk:8s}{r['n']:>5}{r['span'][0][:7]+'~'+r['span'][1][:7]:>20}"
              f"{f'{band[0]:.0f}~{band[1]:.0f}' if band else '—':>12}"
              f"{r['realized_med']:>10.1f}"
              f"{f'{imp[0]:.0f}~{imp[1]:.0f}x' if imp else '—':>13}{verdict:>11}")
        rows.append((tk, r, imp, verdict))

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"))

    # ★[8/14 신설·정훈 승인] 밴드를 원장으로 떨궈 validate_report.check_target_multiple이 소비한다.
    #   이 도구는 네트워크·EDGAR를 쓰므로 매 보고서 호출이 불가 → 주간 R3에서 갱신하고 검사기는 캐시를 읽는다.
    if a.save:
        bands = {"updated": dt.date.today().isoformat(), "horizon": a.horizon, "stocks": {}}
        for tk, r, imp, verdict in rows:
            bands["stocks"][tk] = {
                "band": r["band"], "n": r["n"], "span": r["span"],
                "realized_med": r["realized_med"],
                "ttm_eps": (cache[tk][-1][1] if cache.get(tk) else None),
                "implied": imp, "verdict": verdict,
            }
        out = os.path.join(ROOT, "data", "app", "multiple_bands.json")
        json.dump(bands, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n  💾 {out} 저장 ({len(bands['stocks'])}종목)")

    n_over = sum(1 for *_, v in rows if v == "🔴 상단초과")
    n_in = sum(1 for *_, v in rows if v == "🟢 구간내")
    print(f"\n  구간내 {n_in} · 상단초과 {n_over} · 기타 {len(rows)-n_in-n_over} (총 {len(rows)})")
    print("\n  ※ **우리목표→TTM** = 8/8 채택 목표가 ÷ 최신 TTM EPS.")
    print("  ※   우리 배수는 선행(컨센) EPS 기준이라 그대로 비교하면 안 되고,")
    print("  ※   이렇게 후행 축으로 환산해야 역사 밴드와 사과 대 사과가 된다.")
    print("  ※   ⚠️ 환산 없이 배수만 비교하면 '보수적'으로 잘못 읽힌다(8/8 1차 실행에서 실제로 그랬다).")
    print("  ※ '정당 구간' = 중앙 절대오차가 최저의 1.25배 이내인 배수 범위.")
    print("  ※ 실현PE 중앙 = 지평 후 실제가 ÷ 그때 TTM EPS = 사후적으로 시장이 매긴 배수.")
    print("  ※ 보유 종목만 보므로 생존편향 있음 — 절대 수준을 일반화하지 말 것.")
    print("  ※ 측정 전용 — 목표가·배수를 자동으로 바꾸지 않는다.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
