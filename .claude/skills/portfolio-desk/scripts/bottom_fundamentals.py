#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bottom_fundamentals.py — 낙폭군 × 룰2 3중조건 검정 (11/5 후속, 정훈 "나중에" → "지금 해")

bottom_study.py가 가격 신호만으로는 '오를 낙폭주'를 못 가른다고 결론 낸 뒤 남긴 다음 후보:
"펀더가 멀쩡한데 가격만 빠진 낙폭주가, 펀더가 망가진 낙폭주보다 더 오르나?" (docs/research/bottom_study_2026-11-05.md §한계3)

방법
  · 유니버스 = bottom_study 낙폭군(US만 — KR은 DART 점시점 재무가 없어 제외, 아래 한계 참조)
  · 룰2 3중조건(master.md 리스크룰2 그대로): ①영업마진 3년 연속 하락 ②FCF 2년 연속 감소 or 마이너스 전환
    ③순부채 2년 연속 증가 — SEC EDGAR companyfacts 연간(10-K) 팩트, **그 시점에 "처음 신고된" 값**만 쓴다
    (나중 정정치를 쓰면 미래참조가 된다 — 사실상 lookahead_guard 원칙의 수동 적용).
  · 각 샘플일(월말, 낙폭 ≤-35%)에서 "그날 이전에 filed된" 최근 3개 회계연도로 플래그(0~3) 산정.
  · 건강군(0~1) vs 훼손군(2~3) — 같은 날 낙폭군 평균 대비 120거래일(+60·250 보조) 초과수익, ①집계 ②연도분해 ③섹터 횡단면.

한계 (반드시 같이 읽을 것)
  1. **③ 시장 간 재현을 못 한다** — KR 종목의 점시점 분기/연간 재무를 DART에서 재구성할 인프라가 없다.
     이 검정은 미국 단일시장이라 8/5 절차 ①②③의 ③이 원천적으로 생략된다 — 결과가 통과해도 "확정"이 아니라
     "미국 한정 관찰"이다. 대신 미국 섹터 횡단면으로 일부 대체한다.
  2. 연간 팩트가 매년 정확히 "FY, FY-1, FY-2"로 떨어지지 않는 회사(회계연도 변경·상장 초기)는 제외된다.
  3. bottom_study와 같은 생존편향(현재 $10B+로 살아있는 회사만의 유니버스)을 그대로 공유한다.
  4. "첫 신고값"은 point-in-time으로는 맞지만, 그 분기가 아직 4분기 역산·XBRL 보충 전인 원시값이라
     financials.py의 정제 파이프라인보다 거칠다 — 측정 전용이라는 전제가 여기서도 유효하다.

사용법
  python bottom_fundamentals.py --fetch         # CIK 전체 companyfacts 수집(캐시, 20~40분 예상)
  python bottom_fundamentals.py                 # 검정(캐시 사용)
  python bottom_fundamentals.py --json out.json
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import math
import os
import statistics as st
import sys
import time
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
import bottom_study as bstudy  # noqa: E402
import edgar_facts as ef  # noqa: E402

LEDGER_CACHE = os.path.join(ROOT, "data", "tmp", "bottom_fund_ledger.json")
HORIZONS = bstudy.HORIZONS


# ─────────────────────────────────────────── 1종목 연간 "첫 신고" 원장

def _first_filed(raws: list[dict], bucket: str, is_stock: bool) -> dict[str, tuple]:
    """{end: (first_filed, val)} — 그 end에 대해 **가장 먼저 filed된** 값(점시점 원칙 — 정정치 배제)."""
    want = "instant" if is_stock else bucket
    best: dict[str, tuple] = {}
    for f in raws:
        if ef._bucket(f, is_stock) != want or f.get("val") is None or not f.get("filed"):
            continue
        e = f["end"]
        prev = best.get(e)
        if prev is None or f["filed"] < prev[0]:
            best[e] = (f["filed"], f["val"])
    return best


def build_ledger(ticker: str, facts: dict) -> list[dict] | None:
    """연간 원장: [{end, rev:(filed,val), op:(filed,val), fcf:(filed,val), net_debt:(filed,val)}, ...] end 오름차순."""
    rev = _first_filed([x for t in ef.TAGS["revenue"] for x in ef._raw(facts, t)], "annual", False)
    op = _first_filed([x for t in ef.TAGS["operating_income"] for x in ef._raw(facts, t)], "annual", False)
    cfo = _first_filed([x for t in ef.TAGS["cfo"] for x in ef._raw(facts, t)], "annual", False)
    capex = _first_filed([x for t in ef.TAGS["capex"] for x in ef._raw(facts, t)], "annual", False)
    cash = _first_filed([x for t in ef.TAGS["cash"] for x in ef._raw(facts, t)], "instant", True)
    d_comb = _first_filed([x for t in ef.DEBT_COMBINED for x in ef._raw(facts, t)], "instant", True)
    d_long = _first_filed([x for t in ef.DEBT_LONG for x in ef._raw(facts, t)], "instant", True)
    d_short = _first_filed([x for t in ef.DEBT_SHORT for x in ef._raw(facts, t)], "instant", True)

    ends = sorted(set(rev) | set(op))
    if len(ends) < 3:
        return None
    out = []
    for e in ends:
        row = {"end": e}
        if e in rev and e in op:
            row["margin_avail"] = max(rev[e][0], op[e][0])
            row["margin"] = (op[e][1] / rev[e][1]) if rev[e][1] else None
        if e in cfo and e in capex:
            row["fcf_avail"] = max(cfo[e][0], capex[e][0])
            row["fcf"] = cfo[e][1] - capex[e][1]
        debt_v, debt_f = None, None
        if e in d_comb:
            debt_v, debt_f = d_comb[e][1], d_comb[e][0]
        elif e in d_long or e in d_short:
            lf, lv = d_long.get(e, (None, None))
            sf, sv = d_short.get(e, (None, None))
            if lv is not None or sv is not None:
                debt_v = (lv or 0) + (sv or 0)
                debt_f = max(f for f in (lf, sf) if f)
        if debt_v is not None and e in cash:
            row["net_debt_avail"] = max(debt_f, cash[e][0])
            row["net_debt"] = debt_v - cash[e][1]
        out.append(row)
    return out


# ─────────────────────────────────────────── 수집(스레드)

def fetch(workers: int = 6):
    uni = bstudy.ms.us_universe()
    tickers = sorted({u["ticker"] for u in uni})
    cmap = ef.cik_map()
    todo = [(t, cmap.get(t)) for t in tickers if cmap.get(t)]
    print(f"대상 {len(todo)}/{len(tickers)}종목 (CIK 미매핑 {len(tickers) - len(todo)}) — companyfacts 수집 시작")
    ledgers: dict[str, list] = {}
    errs = {"no_data": 0, "http": 0, "other": 0}

    def work(item):
        t, cik = item
        try:
            facts = ef.company_facts(cik)
            time.sleep(ef.SEC_PACE)
            led = build_ledger(t, facts)
            return t, led, None
        except urllib.error.HTTPError as e:
            return t, None, f"http {e.code}"
        except Exception as e:
            return t, None, f"{type(e).__name__}: {str(e)[:60]}"

    done = 0
    with cf.ThreadPoolExecutor(workers) as ex:
        for t, led, err in ex.map(work, todo):
            done += 1
            if led:
                ledgers[t] = led
            elif err and err.startswith("http"):
                errs["http"] += 1
            elif err:
                errs["other"] += 1
            else:
                errs["no_data"] += 1
            if done % 50 == 0:
                print(f"  {done}/{len(todo)} ({len(ledgers)} 확보)")
    os.makedirs(os.path.dirname(LEDGER_CACHE), exist_ok=True)
    with open(LEDGER_CACHE, "w", encoding="utf-8") as f:
        json.dump(ledgers, f)
    print(f"완료 — 연간원장 확보 {len(ledgers)}/{len(todo)} · 미확보(no_data={errs['no_data']} http={errs['http']} other={errs['other']})")
    print(f"→ {os.path.relpath(LEDGER_CACHE, ROOT)}")


# ─────────────────────────────────────────── 점시점 룰2 플래그

def flags_asof(ledger: list[dict], asof: str) -> int | None:
    """asof 시점에 '이미 filed'된 값만으로 최근 연간 3개를 골라 룰2 플래그(0~3). 데이터 부족이면 None."""
    def latest3(key_val: str, key_avail: str):
        pts = [(r["end"], r[key_val]) for r in ledger
               if r.get(key_val) is not None and r.get(key_avail, "9999-99-99") <= asof]
        pts.sort(key=lambda x: x[0], reverse=True)
        return [v for _, v in pts[:3]] if len(pts) >= 3 else None

    m = latest3("margin", "margin_avail")
    if m is None:
        return None
    flags = 0
    if m[0] < m[1] < m[2]:
        flags += 1
    f = latest3("fcf", "fcf_avail")
    if f is not None:
        if (f[0] < f[1] < f[2]) or (f[0] < 0 <= f[1]):
            flags += 1
    nd = latest3("net_debt", "net_debt_avail")
    if nd is not None and nd[0] > nd[1] > nd[2]:
        flags += 1
    return flags


# ─────────────────────────────────────────── 분석

def analyze(ev: list[dict], ledgers: dict):
    for e in ev:
        e["flags"] = flags_asof(ledgers[e["ticker"]], e["date"]) if e["ticker"] in ledgers else None

    usable = [e for e in ev if e["flags"] is not None]
    by_date: dict[str, list] = {}
    for e in usable:
        by_date.setdefault(e["date"], []).append(e)

    def bucket_stats(label: str, pred, H: int):
        ex_all, years, sectors = [], {}, {}
        n_hit = 0
        for dte, grp in by_date.items():
            g = [x for x in grp if x["fwd"][H] is not None]
            if len(g) < 5:
                continue
            mean = st.fmean(x["fwd"][H] for x in g)
            hits = [x for x in g if pred(x["flags"])]
            if not hits:
                continue
            n_hit += len(hits)
            gap = st.fmean(x["fwd"][H] for x in hits) - mean
            ex_all.append((gap, len(hits)))
            years.setdefault(dte[:4], []).append(gap)
            for x in hits:
                sectors.setdefault(x["sector"], []).append(x["fwd"][H] - mean)
        if not ex_all:
            return None
        w = sum(n for _, n in ex_all)
        agg = sum(g * n for g, n in ex_all) / w
        date_pos = sum(1 for g, _ in ex_all if g > 0)
        yr = {y: st.fmean(v) for y, v in years.items()}
        return {"label": label, "H": H, "n_hit": n_hit, "n_dates": len(ex_all),
                "excess_pct": round(agg * 100, 2), "date_win": round(100 * date_pos / len(ex_all), 1),
                "years_pos": sum(1 for v in yr.values() if v > 0), "years": len(yr),
                "year_detail": {y: round(v * 100, 1) for y, v in sorted(yr.items())},
                "sector_pos": sum(1 for v in sectors.values() if len(v) >= 10 and st.fmean(v) > 0),
                "sector_n": sum(1 for v in sectors.values() if len(v) >= 10),
                "p_sign": bstudy._sign_p(date_pos, len(ex_all))}

    res = {}
    for H in HORIZONS:
        for label, pred in (("건강(0-1)", lambda f: f <= 1), ("훼손(2-3)", lambda f: f >= 2),
                             ("무훼손(0)", lambda f: f == 0), ("3/3전훼손", lambda f: f == 3)):
            r = bucket_stats(label, pred, H)
            if r:
                res[(label, H)] = r

    # 사전등록 원문 그대로의 직접비교: 같은 날 건강군 평균 vs 훼손군 평균(둘 다 있는 날짜만, 페어드)
    head2head = {}
    for H in HORIZONS:
        pos, n, gaps = 0, 0, []
        for dte, grp in by_date.items():
            g = [x for x in grp if x["fwd"][H] is not None]
            healthy = [x["fwd"][H] for x in g if x["flags"] <= 1]
            damaged = [x["fwd"][H] for x in g if x["flags"] >= 2]
            if len(healthy) < 3 or len(damaged) < 3:
                continue
            gap = st.fmean(healthy) - st.fmean(damaged)
            gaps.append(gap)
            n += 1
            if gap > 0:
                pos += 1
        if n:
            head2head[H] = {"n_dates": n, "건강-훼손_평균%p": round(st.fmean(gaps) * 100, 2),
                             "건강-훼손_중앙%p": round(st.median(gaps) * 100, 2),
                             "건강이_이긴_날_비율": round(100 * pos / n, 1), "p_sign": bstudy._sign_p(pos, n)}
    return res, head2head, len(usable), len(ev)


def main() -> int:
    ap = argparse.ArgumentParser(description="낙폭군 × 룰2 3중조건 검정 (측정 전용, 미국만)")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    if a.fetch:
        fetch()
        return 0
    if not os.path.exists(LEDGER_CACHE):
        print("연간원장 캐시 없음 — --fetch 먼저")
        return 1
    if not os.path.exists(bstudy.CACHE):
        print("bottom_study 일봉 캐시 없음 — bottom_study.py --fetch 먼저")
        return 1
    ledgers = json.load(open(LEDGER_CACHE, encoding="utf-8"))
    data = json.load(open(bstudy.CACHE, encoding="utf-8"))
    ev = [e for e in bstudy.build_events(data) if e["market"] == "US"]
    res, head2head, usable, total = analyze(ev, ledgers)
    print(f"US 낙폭군 표본 {total}건 중 룰2 판정 가능 {usable}건 "
          f"(연간원장 확보 {len(ledgers)}종목, margin 3개년 미달 등으로 제외 {total - usable}건)")
    print("\n[사전등록 직접비교] 같은 날 건강군(0-1) 평균 vs 훼손군(2-3) 평균 (둘 다 있는 날짜만)")
    for H, r in sorted(head2head.items()):
        print(f"  {H:4}일: 평균{r['건강-훼손_평균%p']:+7.2f}%p · 중앙{r['건강-훼손_중앙%p']:+7.2f}%p · "
              f"건강이 이긴 날 {r['건강이_이긴_날_비율']}%({r['n_dates']}일) · p={r['p_sign']:.3g}")
    print("\n그룹        지평  적중  날짜  낙폭군대비%p  날짜승률  연도+   섹터+   p(부호)")
    for (label, H), r in sorted(res.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        print(f"{label:10} {H:4} {r['n_hit']:6} {r['n_dates']:4} {r['excess_pct']:+9.2f} "
              f"{r['date_win']:8.1f}% {r['years_pos']:2}/{r['years']:<4} {r['sector_pos']:2}/{r['sector_n']:<4} {r['p_sign']:.3g}")
    if a.json:
        out = {f"{k[0]}|{k[1]}": v for k, v in res.items()}
        out["_head2head"] = {str(k): v for k, v in head2head.items()}
        json.dump(out, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
