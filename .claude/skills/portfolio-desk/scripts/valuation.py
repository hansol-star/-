#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
valuation.py — 자체 내재가치(DCF) + 상대가치(comps) 밸류에이션.

지금 우리 0~100 스코어·별점은 FMP 하드넘버 + **증권사 컨센서스 목표가**에 기댄다.
이 스크립트는 **우리만의 숫자**를 만들어 sell-side 목표가와 교차검증한다 —
"증권사 우선하되 과신은 견제"(CLAUDE.md) 철학의 정량 근거.

  1) DCF: FCF/주를 성장률(감쇠)·WACC·터미널로 현가화 → 3시나리오(보수/기준/낙관) 내재가치.
  2) comps: 피어 P/E 중앙값 × 대상 EPS → 상대 적정가.
  3) 현재가·(있으면) 컨센서스와 나란히 상승/하락 여력.

⚠️ 정직 원칙: DCF는 성장·WACC·터미널 가정에 극도로 민감(고성장주 특히) → **가정 전부
   출력에 노출**하고 CLI로 조정 가능. FCF/주가 음수·결측이면 DCF 부적합으로 **플래그**(추정 강행 X),
   그땐 comps·컨센서스 참조. 국내주·FMP 402 종목은 fundamentals와 동일하게 WebSearch 폴백.

데이터: fundamentals.py 재사용(FMP stable, 키=FMP_API_KEY). 표준 라이브러리만.

사용:
  FMP_API_KEY=xxx python3 valuation.py --tickers NVDA,MSFT          # DCF 3시나리오
  FMP_API_KEY=xxx python3 valuation.py --tickers NVDA --comps        # + 피어 상대가치
  FMP_API_KEY=xxx python3 valuation.py --tickers MSFT --wacc 0.085 --terminal 0.03 --years 10
  python3 valuation.py --demo        # 키 없이 DCF 수학 검증(합성 입력)
  FMP_API_KEY=xxx python3 valuation.py --tickers NVDA --json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import cli_common

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from fundamentals import fetch as fetch_fund, FMP_402_TICKERS, _is_us
except ImportError:
    fetch_fund, FMP_402_TICKERS, _is_us = None, [], lambda t: True

# 섹터 피어 맵(comps용, 미국 유동 대형주 중심). --peers로 재정의 가능.
PEERS = {
    "NVDA": ["AMD", "QCOM", "TXN", "MRVL", "AVGO"], "AVGO": ["NVDA", "QCOM", "TXN", "AMD"],
    "MU": ["STX", "WDC"], "ANET": ["CSCO", "NVDA", "AVGO"],
    "AAPL": ["MSFT", "GOOGL"], "MSFT": ["GOOGL", "ORCL", "AAPL"],
    "GOOGL": ["META", "MSFT"], "META": ["GOOGL", "MSFT"],
    "ORCL": ["MSFT", "SAP", "CRM"], "TSLA": ["GM", "F", "RIVN"],
}

# DCF 3시나리오: (성장 배수, WACC, 터미널 성장). 기준 WACC/터미널은 CLI로 덮어씀.
SCENARIOS = [
    ("보수", 0.6, +0.010, -0.005),   # 성장×0.6, WACC +1.0%p, 터미널 -0.5%p
    ("기준", 1.0, 0.000, 0.000),
    ("낙관", 1.3, -0.005, +0.005),   # 성장×1.3, WACC -0.5%p, 터미널 +0.5%p
]

GROWTH_CAP = 0.30   # 고성장주 초기성장 상한(과대추정 방지)
MIN_PEERS = 2       # comps 최소 유효 피어 수(1개 아웃라이어로 헛값 방지)


def dcf_per_share(fcf0: float, g0: float, wacc: float, term_g: float, years: int) -> float:
    """FCF/주를 성장(감쇠)·WACC·터미널(고든)로 현가화 → 주당 내재가치.
    g0에서 term_g로 years에 걸쳐 선형 감쇠. wacc>term_g 필수."""
    if wacc <= term_g:
        wacc = term_g + 0.01
    pv, fcf = 0.0, fcf0
    for t in range(1, years + 1):
        g = g0 + (term_g - g0) * (t - 1) / (years - 1) if years > 1 else g0
        fcf *= (1 + g)
        pv += fcf / (1 + wacc) ** t
    tv = fcf * (1 + term_g) / (wacc - term_g)   # 마지막해 FCF 기준 터미널가치
    pv += tv / (1 + wacc) ** years
    return pv


def base_growth(fund: dict) -> float | None:
    """DCF 초기성장 = EPS·매출 YoY의 보수적 블렌드(둘 중 작은 쪽 쪽으로), 상한 캡."""
    g_eps = fund.get("epsGrowthYoY")
    g_rev = fund.get("revenueGrowthYoY")
    vals = [v / 100.0 for v in (g_eps, g_rev) if isinstance(v, (int, float))]
    if not vals:
        return None
    g = min(vals) * 0.5 + (sum(vals) / len(vals)) * 0.5   # min쪽 가중 블렌드
    return max(min(g, GROWTH_CAP), 0.0)


def value_ticker(ticker: str, wacc: float, term_g: float, years: int) -> dict:
    out = {"ticker": ticker}
    if fetch_fund is None:
        out["_error"] = "fundamentals 모듈 없음"
        return out
    f = fetch_fund(ticker)
    if f.get("_error"):
        out["_error"] = f["_error"]
        return out
    price = f.get("price")
    fcf = f.get("fcfPerShareTTM")
    out["price"] = price
    out["fcfPerShareTTM"] = fcf
    out["pe"] = f.get("pe")
    out["g_base"] = base_growth(f)

    # DCF (FCF/주 양수·성장 확보 시만)
    if isinstance(fcf, (int, float)) and fcf > 0 and out["g_base"] is not None:
        dcf = {}
        for name, gmul, dw, dt in SCENARIOS:
            iv = dcf_per_share(fcf, out["g_base"] * gmul, wacc + dw, term_g + dt, years)
            up = ((iv - price) / price * 100) if price else None
            dcf[name] = {"intrinsic": round(iv, 2),
                         "upside_pct": round(up, 1) if up is not None else None}
        out["dcf"] = dcf
    else:
        out["dcf_flag"] = ("FCF/주 음수·결측 → DCF 부적합(comps·컨센서스 참조)"
                           if not (isinstance(fcf, (int, float)) and fcf > 0)
                           else "성장률 결측 → DCF 보류")
    return out


def add_comps(row: dict, peers: list[str], pe_cache: dict) -> None:
    """피어 P/E 중앙값 × 대상 EPS → 상대 적정가. EPS = price/pe."""
    price, pe = row.get("price"), row.get("pe")
    if not (isinstance(price, (int, float)) and isinstance(pe, (int, float)) and pe > 0):
        row["comps_flag"] = "대상 PE 결측 → comps 불가"
        return
    eps = price / pe
    peer_pes = []
    for p in peers:
        if p not in pe_cache:
            pf = fetch_fund(p) if fetch_fund else {"_error": "no mod"}
            pe_cache[p] = pf.get("pe") if not pf.get("_error") else None
        v = pe_cache[p]
        if isinstance(v, (int, float)) and v > 0:
            peer_pes.append(v)
    if len(peer_pes) < MIN_PEERS:
        row["comps_flag"] = (f"유효 피어 {len(peer_pes)}개(<{MIN_PEERS}) — comps 신뢰불가. "
                             f"402/국내 피어 제외됨({'·'.join(peers)})")
        return
    med = statistics.median(peer_pes)
    fair = med * eps
    row["comps"] = {"peer_median_pe": round(med, 1), "fair_price": round(fair, 2),
                    "upside_pct": round((fair - price) / price * 100, 1),
                    "peers_used": len(peer_pes)}


def run_demo() -> int:
    """키 없이 DCF 수학 검증: FCF/주 $10, 성장 12%, WACC 9%, 터미널 2.5%, 10년."""
    iv = dcf_per_share(10.0, 0.12, 0.09, 0.025, 10)
    print("=== DCF 데모 (합성 입력) ===")
    print("FCF/주 $10.00 · 초기성장 12% → 터미널 2.5% 감쇠 · WACC 9% · 10년")
    print(f"→ 주당 내재가치 ≈ ${iv:,.2f}")
    # 단조성 sanity: 성장↑ → 가치↑, WACC↑ → 가치↓
    hi = dcf_per_share(10.0, 0.20, 0.09, 0.025, 10)
    lo = dcf_per_share(10.0, 0.12, 0.12, 0.025, 10)
    assert hi > iv > lo, "DCF 단조성 위반"
    print(f"  성장 20% → ${hi:,.2f} (↑ 확인) · WACC 12% → ${lo:,.2f} (↓ 확인)  [sanity PASS]")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="자체 DCF+comps 밸류에이션")
    ap.add_argument("--tickers", help="쉼표·공백구분 미국 티커")
    ap.add_argument("--comps", action="store_true", help="피어 상대가치도 계산")
    ap.add_argument("--peers", help="피어 티커 쉼표·공백구분(--tickers 1개일 때 재정의)")
    ap.add_argument("--wacc", type=float, default=0.09, help="기준 WACC (기본 0.09)")
    ap.add_argument("--terminal", type=float, default=0.025, help="터미널 성장 (기본 0.025)")
    ap.add_argument("--years", type=int, default=10, help="명시적 예측기간 (기본 10)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--demo", action="store_true", help="키 없이 DCF 수학 검증")
    args = ap.parse_args()

    if args.demo:
        return run_demo()
    if not args.tickers:
        print("사용: --tickers NVDA,MSFT [--comps]  (또는 --demo)", file=sys.stderr)
        return 2
    if not os.environ.get("FMP_API_KEY", "").strip():
        print("⚠️ FMP_API_KEY 없음 — 라이브 밸류에이션 불가. DCF 수학만 볼거면 --demo.",
              file=sys.stderr)
        return 2

    tickers = [t.strip() for t in cli_common.split_tickers(args.tickers) if t.strip()]
    pe_cache: dict = {}
    rows = []
    for t in tickers:
        row = value_ticker(t, args.wacc, args.terminal, args.years)
        if args.comps and not row.get("_error"):
            peers = ([p.strip() for p in args.peers.split(",")] if args.peers and len(tickers) == 1
                     else PEERS.get(t, []))
            if peers:
                add_comps(row, peers, pe_cache)
            else:
                row["comps_flag"] = "피어맵 없음(--peers로 지정)"
        rows.append(row)

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print(f"## 자체 밸류에이션 (WACC {args.wacc:.1%} · 터미널 {args.terminal:.1%} · {args.years}년)")
    print("_DCF는 가정 민감 — 목표가 아닌 '참고 밴드'. FCF 음수는 부적합._\n")
    for r in rows:
        if r.get("_error"):
            print(f"### {r['ticker']} — {r['_error']}")
            continue
        price = r.get("price")
        pe_str = f"{r['pe']:.1f}" if isinstance(r.get("pe"), (int, float)) else "-"
        g_str = f"{r['g_base']*100:.1f}%" if isinstance(r.get("g_base"), (int, float)) else "-"
        print(f"### {r['ticker']}  현재가 ${price:,.2f}  (PE {pe_str}, 초기성장 {g_str})")
        if r.get("dcf"):
            for name in ("보수", "기준", "낙관"):
                d = r["dcf"][name]
                up = d["upside_pct"]
                arrow = "▲" if (up or 0) >= 0 else "▼"
                print(f"  - DCF {name}: ${d['intrinsic']:,.2f}  ({arrow}{abs(up):.1f}% vs 현재)")
        if r.get("dcf_flag"):
            print(f"  - DCF: {r['dcf_flag']}")
        if r.get("comps"):
            c = r["comps"]
            up = c["upside_pct"]
            arrow = "▲" if up >= 0 else "▼"
            print(f"  - comps: 피어 PE중앙값 {c['peer_median_pe']} → 적정 ${c['fair_price']:,.2f} "
                  f"({arrow}{abs(up):.1f}%, 피어 {c['peers_used']}개)")
        if r.get("comps_flag"):
            print(f"  - comps: {r['comps_flag']}")
    print("\n※ 자체 숫자 = 컨센서스 목표가(consensus.py) 교차검증용. 단일 근거로 매매 X.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
