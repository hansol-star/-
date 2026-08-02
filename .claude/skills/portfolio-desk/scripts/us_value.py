#!/usr/bin/env python3
"""us_value.py — 미국주 밸류에이션 & '선반영 여부' 판단 (FMP forward·stdlib)

정훈 지시(2026-07-22 "미장 종목에도 밸류 선반영 층 확장"). naver_value(KR·네이버 재무)의
쌍둥이 — 미국주는 **FMP 애널리스트 추정(forward)**으로 같은 선반영 로직(value_core)을 적용.

소스(FMP stable·키 필요 = env FMP_API_KEY, fundamentals.py와 동일):
  · fundamentals.fetch  → 트레일링 PE·마진·성장·ROE·현재가
  · analyst-estimates   → **forward EPS(epsAvg)·매출·순이익** (다음 회계연도)
  · income-statement    → 과거 순이익 시계열(신고 실적 판정용)
  · price-target-consensus → 목표주가 컨센 → 상단
  · ratings-snapshot    → FMP 등급(참고)

판정 = value_core(선반영: 미반영여지/선반영고평가/밸류트랩/내러티브) — KR과 단일 로직.
⚠️ 무료 플랜 402 종목(MU·VOO·ANET·AVGO·ORCL)·키 없음 → WebSearch(증권사 리포트) 폴백 명시.
   VOO=ETF는 밸류 대상 아님. 측정·판독 전용 — 별점·매수존 정본은 펀더 스코어.

사용:
  FMP_API_KEY=xxx python3 us_value.py                 # 미국 보유(ETF 제외)
  FMP_API_KEY=xxx python3 us_value.py --tickers NVDA,AAPL
  FMP_API_KEY=xxx python3 us_value.py --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import cli_common

try:
    import fundamentals as fu   # FMP 클라이언트·트레일링 재사용
    import value_core as vc     # 선반영 판정 공용 코어
except Exception as e:  # pragma: no cover
    sys.exit(f"[us_value] 임포트 실패: {e}")

# 밸류 대상 미국 보유(ETF VOO 제외)
US = ["NVDA", "MU", "AAPL", "MSFT", "ANET", "TSLA", "AVGO", "GOOGL", "META", "ORCL"]


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _fwd_row(est):
    """analyst-estimates(연간)에서 오늘 이후 첫 회계연도(=다음 forward FY) 행."""
    if not isinstance(est, list) or not est:
        return None
    today = dt.date.today().isoformat()
    rows = sorted([e for e in est if e.get("date")], key=lambda e: e["date"])
    fwd = [e for e in rows if e["date"] >= today]
    return fwd[0] if fwd else rows[-1]


def value_read(ticker: str) -> dict:
    out = {"ticker": ticker}
    tr = fu.fetch(ticker)  # 트레일링(quote+income+ratios+key-metrics)
    if tr.get("_error"):
        out["_error"] = tr["_error"] + " → WebSearch(증권사 리포트) 폴백"
        return out
    price = _num(tr.get("price"))
    trail_per = _num(tr.get("pe"))
    out.update({"price": price, "trail_per": trail_per,
                "rev_g_yoy": tr.get("revenueGrowthYoY"), "eps_g_yoy": tr.get("epsGrowthYoY"),
                "net_margin_ttm": tr.get("netMarginTTM"), "roe_ttm": tr.get("roeTTM")})

    est = fu._get("analyst-estimates", {"symbol": ticker, "period": "annual", "limit": 6})
    inc = fu._get("income-statement", {"symbol": ticker, "period": "annual", "limit": 4})
    tgt = fu._get("price-target-consensus", {"symbol": ticker})
    rat = fu._get("ratings-snapshot", {"symbol": ticker})

    fwd = _fwd_row(est)
    fwd_eps = _num(fwd.get("epsAvg")) if fwd else None
    fwd_rev = _num(fwd.get("revenueAvg")) if fwd else None
    fwd_ni = _num(fwd.get("netIncomeAvg")) if fwd else None
    out["fwd_fy"] = fwd.get("date") if fwd else None
    out["n_analysts"] = (fwd or {}).get("numAnalystsEps")

    # 과거 순이익 시계열 + 최근 실적 EPS·마진
    ni_series, prior_margin, trail_eps = [], None, None
    if isinstance(inc, list) and inc:
        recs = sorted(inc, key=lambda r: r.get("date", ""))  # 오래된→최신
        ni_series = [_num(r.get("netIncome")) for r in recs]
        last = recs[-1]
        trail_eps = _num(last.get("eps"))
        rev0, ni0 = _num(last.get("revenue")), _num(last.get("netIncome"))
        prior_margin = (ni0 / rev0) if (rev0 and ni0 is not None) else None
    est_margin = (fwd_ni / fwd_rev) if (fwd_rev and fwd_ni is not None) else None

    # 포워드 PER·기대성장·EPS방향·마진방향
    fwd_per = (price / fwd_eps) if (price and fwd_eps and fwd_eps > 0) else None
    implied_g = (round(100 * (fwd_eps / trail_eps - 1), 1)
                 if (fwd_eps is not None and trail_eps and trail_eps > 0) else None)
    if trail_eps is not None and fwd_eps is not None:
        eps_dir = "증가" if fwd_eps > trail_eps else ("감소" if fwd_eps < trail_eps else "정체")
    else:
        eps_dir = "n/a"
    if prior_margin is not None and est_margin is not None:
        margin_dir = ("가속" if est_margin > prior_margin * 1.02
                      else "둔화" if est_margin < prior_margin * 0.98 else "횡보")
    else:
        margin_dir = "n/a"

    target = _num((tgt or [{}])[0].get("targetConsensus")) if isinstance(tgt, list) else None
    upside = round(100 * (target / price - 1), 1) if (target and price) else None
    rating = (rat or [{}])[0].get("rating") if isinstance(rat, list) else None

    decel = (eps_dir == "감소") or (margin_dir == "둔화")
    new_high_earn, aggressive, target_stale = vc.structural_flags(
        ni_series, fwd_ni, implied_g, prior_margin, est_margin, upside, decel)
    loss_now = (trail_eps is not None and trail_eps <= 0) or (trail_per is not None and trail_per < 0)
    verdict, tilt = vc.priced_in_verdict(
        trail_per=trail_per, fwd_per=fwd_per, implied_growth=implied_g, upside=upside,
        margin_dir=margin_dir, eps_dir=eps_dir, new_high_earn=new_high_earn,
        target_stale=target_stale, loss_now=loss_now)

    out.update({
        "fwd_eps": fwd_eps, "trail_eps": trail_eps, "fwd_per": fwd_per,
        "implied_growth": implied_g, "eps_dir": eps_dir, "margin_dir": margin_dir,
        "prior_margin": round(prior_margin * 100, 1) if prior_margin is not None else None,
        "est_margin": round(est_margin * 100, 1) if est_margin is not None else None,
        "target": target, "upside": upside, "rating": rating,
        "aggressive_consensus": aggressive, "new_high_earnings": new_high_earn,
        "target_stale": target_stale, "priced_in": verdict, "value_tilt": tilt,
    })
    return out


def _f(x, suf=""):
    if x is None:
        return "n/a"
    if abs(x) >= 10000:
        return f"{x:,.0f}{suf}"
    return f"{x:g}{suf}"


def fmt(o: dict) -> str:
    if o.get("_error"):
        return f"■ {o['ticker']}: {o['_error']}"
    agg = "  ⚠️컨센 공격적" if o.get("aggressive_consensus") else ""
    L = [f"■ {o['ticker']}  ${_f(o['price'])}  →  선반영: {o['priced_in']}{agg}"]
    L.append(f"   실적: 트레일링EPS {_f(o['trail_eps'])} → 포워드EPS {_f(o['fwd_eps'])}({o.get('fwd_fy')}, "
             f"애널 {o.get('n_analysts')}명) · 마진 {o['margin_dir']}"
             f"({_f(o['prior_margin'],'%')}→{_f(o['est_margin'],'%')})")
    L.append(f"   밸류: 트레일링PER {_f(o['trail_per'],'x')} → 포워드PER {_f(o['fwd_per'],'x')} · "
             f"기대EPS성장 {_f(o['implied_growth'],'%')} · EPS방향 {o['eps_dir']}")
    stale = "(⚠️stale)" if o.get("target_stale") else ""
    L.append(f"   컨센: 목표가 ${_f(o['target'])}(상단 {_f(o['upside'],'%')}{stale}) · "
             f"FMP등급 {o.get('rating')} · TTM 순마진 "
             f"{_f(o['net_margin_ttm']*100 if o.get('net_margin_ttm') is not None else None,'%')}")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="미국주 FMP forward 밸류에이션·선반영 판단")
    ap.add_argument("--tickers", help="쉼표·공백구분(기본=미국 보유·ETF 제외)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not fu._key():
        print("⚠️  FMP_API_KEY 없음 → 미장 밸류 조회 불가(정훈이 세션마다 제공). "
              "국내는 naver_value.py 사용.", file=sys.stderr)
        return 2

    tickers = [t.strip() for t in cli_common.split_tickers(args.tickers)] if args.tickers else US
    results = [value_read(t) for t in tickers]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return 0

    print("미국주 FMP forward 밸류에이션 — 선반영(미래가치 반영) 판독 (us_value.py · 측정·판독 전용)")
    print("=" * 84)
    for r in results:
        print(fmt(r))
        print("-" * 84)
    print("※ 포워드 저PER·목표 상단은 '컨센 실현 조건부'. 402/키없음 종목은 WebSearch(리포트) 폴백. "
          "별점·매수존 정본은 펀더 스코어. 최종 결정 정훈.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
