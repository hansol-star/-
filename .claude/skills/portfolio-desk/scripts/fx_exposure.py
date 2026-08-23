#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fx_exposure.py — 통화 익스포저·환손익 분해 (roadmap P0 2-3)

왜 있나 [8/23 신설]
──────────────────
roadmap 2-3이 **P0(손실 직결)**로 올려둔 채 미구현이던 축이다. 진단 문장 그대로:

  "원/달러가 3개월 -8.6% 움직이는 동안 **우리는 이 축을 한 번도 측정하지 않았다.**
   종목 손익만 보고 환손익을 안 본 것."

우리 포트는 달러 자산이 7할이라 **환율이 종목보다 큰 단일 변수**인데, 앱·보고서 어디에도
통화 비중이 없었다. 여기서 세 가지를 낸다:

  ① 통화별 자산 비중(주식+현금) — 원화 vs 달러
  ② 원/달러 %ile(1y·3y·5y) + 환율 1% 변동의 총자산 영향(원)
  ③ **환손익 기여도 3분해** — 같은 평가손익을 종목/환율/교차항으로 가른다

③의 산식 (V = P·Q·F, 0=취득 1=현재):
    ΔV        = P₁Q F₁ − P₀Q F₀
    종목 기여 = (P₁−P₀)·Q·F₀      환율 고정, 주가만 변한 몫
    환 기여   = P₀·Q·(F₁−F₀)      주가 고정, 환율만 변한 몫
    교차항    = (P₁−P₀)·Q·(F₁−F₀) 둘이 같이 움직인 몫 (분해의 잔차 — 숨기지 않고 표기)

취득환율(F₀)은 portfolio.json `us_avg_fx_cost`(현재 1,456.5 — 토스 실손익 역산 추정치).
⚠️ **추정치이므로 환 기여 절대액은 ±오차를 안는다** — 방향과 크기 감각용이고,
   체결별 실환율이 원장(trades.jsonl fx_rate)에 쌓이면 그쪽으로 정밀화한다.

⚠️ 측정 전용 — 어떤 룰(사다리·안전핀·별점)도 바꾸지 않는다.

사용법:
  python3 fx_exposure.py              # 앱 빌드 산출물(app/data.js) 기준 요약
  python3 fx_exposure.py --json       # 기계 출력 (build_app_data가 소비)
  python3 fx_exposure.py --no-percentile   # 네트워크 없이(환율 %ile 생략)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PORTFOLIO_JSON = os.path.join(HERE, "..", "portfolio.json")
DATA_JS = os.path.join(REPO, "app", "data.js")

KST = dt.timezone(dt.timedelta(hours=9))
FX_SYMBOL = "KRW=X"

sys.path.insert(0, HERE)


def fx_percentiles(timeout: float = 15.0) -> dict:
    """원/달러 현재 수준의 1y·3y·5y 백분위. 네트워크 실패 시 값 None(정직 표기)."""
    out = {"symbol": FX_SYMBOL, "windows": {}, "status": "unavailable"}
    try:
        from vol_gauge import fetch_closes, percentile_rank
    except Exception:
        return out
    closes = fetch_closes(FX_SYMBOL, rng="5y", timeout=timeout)
    if not closes or len(closes) < 60:
        return out
    cur = closes[-1]
    out["current"] = round(cur, 2)
    out["status"] = "live"
    for label, days in (("1y", 252), ("3y", 756), ("5y", 1260)):
        win = closes[-days:]
        if len(win) < 60:
            continue
        out["windows"][label] = {
            "percentile": percentile_rank(win, cur),
            "low": round(min(win), 2), "high": round(max(win), 2), "n": len(win),
        }
    # 3개월 변화율 — roadmap이 지적한 "원화 강세가 이어지면 달러 비중이 깎인다"의 추세축
    if len(closes) > 63:
        out["chg_3m_pct"] = round((cur - closes[-63]) / closes[-63] * 100, 2)
    return out


def compute(holdings: list[dict], fx_rate: float, cash_krw: float = 0.0,
            cash_usd: float = 0.0, fx_cost: float | None = None) -> dict:
    """통화 비중 + 환손익 3분해.

    holdings: build_app_data가 만든 종목 dict 리스트
              (currency·shares·cost·price·value_krw 필요)
    fx_rate : 현재 원/달러      fx_cost: 미국주 평균 취득환율(F₀)
    """
    krw_stock = usd_stock_krw = 0.0
    px_krw = fx_krw = cross_krw = 0.0
    per_stock = []

    for h in holdings:
        val = float(h.get("value_krw") or 0)
        if (h.get("currency") or "KRW").upper() != "USD":
            krw_stock += val
            continue
        usd_stock_krw += val
        q = float(h.get("shares") or 0)
        p1 = float(h.get("price") or 0)
        p0 = float(h.get("cost") or 0)
        if not (q and p0 and fx_cost):
            continue
        d_px = (p1 - p0) * q * fx_cost          # 종목 기여
        d_fx = p0 * q * (fx_rate - fx_cost)      # 환 기여
        d_x = (p1 - p0) * q * (fx_rate - fx_cost)  # 교차항
        px_krw += d_px
        fx_krw += d_fx
        cross_krw += d_x
        per_stock.append({
            "label": h.get("label"), "ticker": h.get("ticker"),
            "total_krw": round(p1 * q * fx_rate - p0 * q * fx_cost),
            "price_krw": round(d_px), "fx_krw": round(d_fx), "cross_krw": round(d_x),
        })

    krw_total = krw_stock + float(cash_krw or 0)
    usd_total = usd_stock_krw + float(cash_usd or 0) * fx_rate
    total = krw_total + usd_total

    per_stock.sort(key=lambda x: x["fx_krw"])
    return {
        "fx_rate": fx_rate,
        "fx_cost_basis": fx_cost,
        "total_krw": round(total),
        "buckets": [
            {"currency": "USD", "value_krw": round(usd_total),
             "weight": round(usd_total / total * 100, 1) if total else 0,
             "stock_krw": round(usd_stock_krw), "cash_krw": round(float(cash_usd or 0) * fx_rate)},
            {"currency": "KRW", "value_krw": round(krw_total),
             "weight": round(krw_total / total * 100, 1) if total else 0,
             "stock_krw": round(krw_stock), "cash_krw": round(float(cash_krw or 0))},
        ],
        # 환율 1% 변동 시 총자산 영향 = 달러자산 × 1%
        "sensitivity_1pct_krw": round(usd_total * 0.01),
        "attribution": {
            "price_krw": round(px_krw), "fx_krw": round(fx_krw), "cross_krw": round(cross_krw),
            "total_krw": round(px_krw + fx_krw + cross_krw),
            "note": "미국주만 분해 · F₀=us_avg_fx_cost(추정치)라 환 기여 절대액은 오차를 안는다",
        },
        "by_stock": per_stock,
    }


def _from_data_js() -> tuple[list[dict], float, float, float]:
    raw = open(DATA_JS, encoding="utf-8").read()
    d = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    t = d.get("totals") or {}
    return (d.get("holdings") or [], float((d.get("fx") or {}).get("usdkrw") or 0),
            float(t.get("cash_krw") or 0), float(t.get("cash_usd") or 0))


def main() -> int:
    ap = argparse.ArgumentParser(description="통화 익스포저·환손익 분해 (측정 전용)")
    ap.add_argument("--json", action="store_true", help="기계 출력")
    ap.add_argument("--no-percentile", action="store_true", help="환율 %%ile 생략(네트워크 없이)")
    ap.add_argument("--timeout", type=float, default=15.0)
    args = ap.parse_args()

    try:
        holdings, fx_rate, cash_krw, cash_usd = _from_data_js()
    except Exception as e:
        print(f"❌ app/data.js를 읽지 못했습니다 ({e}) — build_app_data.py를 먼저 돌리세요.", file=sys.stderr)
        return 1
    if not fx_rate:
        print("❌ 환율 미확인 — data.js fx.usdkrw 없음", file=sys.stderr)
        return 1

    with open(PORTFOLIO_JSON, encoding="utf-8") as f:
        pf = json.load(f)
    res = compute(holdings, fx_rate, cash_krw, cash_usd, pf.get("us_avg_fx_cost"))
    res["percentile"] = {} if args.no_percentile else fx_percentiles(args.timeout)
    res["as_of"] = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0

    print(f"── 통화 익스포저 ({res['as_of']}) ──")
    print(f"  원/달러 {res['fx_rate']:,.2f} · 취득환율(추정) {res['fx_cost_basis']:,.1f}")
    for b in res["buckets"]:
        print(f"  {b['currency']:<4} {b['value_krw']:>10,}원 ({b['weight']:>5.1f}%)"
              f"  주식 {b['stock_krw']:>9,} · 현금 {b['cash_krw']:>8,}")
    print(f"  환율 1% 변동 = 총자산 {res['sensitivity_1pct_krw']:+,}원")

    p = res.get("percentile") or {}
    if p.get("status") == "live":
        parts = [f"{k} {v['percentile']:>5.1f}%ile" for k, v in p["windows"].items()]
        print(f"\n  원/달러 위치: " + " · ".join(parts)
              + (f"  (3개월 {p['chg_3m_pct']:+.1f}%)" if p.get("chg_3m_pct") is not None else ""))
    elif not args.no_percentile:
        print("\n  ⚠️ 환율 %ile 미확인 (히스토리 조회 실패)")

    a = res["attribution"]
    print(f"\n── 환손익 3분해 (미국주) ──")
    print(f"  종목 기여 {a['price_krw']:>+10,}원   환 기여 {a['fx_krw']:>+10,}원   교차 {a['cross_krw']:>+9,}원"
          f"   합계 {a['total_krw']:>+10,}원")
    print(f"  ⚠️ {a['note']}")
    if res["by_stock"]:
        print("\n  환 기여 하위 3:")
        for s in res["by_stock"][:3]:
            print(f"    {s['label']:<8} 총 {s['total_krw']:>+9,} = 종목 {s['price_krw']:>+9,} + 환 {s['fx_krw']:>+8,} + 교차 {s['cross_krw']:>+7,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
