#!/usr/bin/env python3
"""
pnl.py — 실시간 포트폴리오 평가손익 (Yahoo 무키 시세 + portfolio.json 원가).

PM이 손으로 하던 "현재가 × 수량 − 원금" 계산을 자동화한다. 환율 환산까지.
원가·수량 정본 = portfolio.json (master.md 미러). 시세 = market_data.fetch_quote.

사용:
  python3 pnl.py            # 종목별 + 합계 손익 표
  python3 pnl.py --json     # JSON (파이프라인용)

※ 토스 실데이터(toss_snapshot.py)가 있으면 그게 수량·평단의 정본. 이 스크립트는
  키 없을 때의 기준선(원가 고정) 평가용. 보고서엔 둘을 교차확인.
"""
from __future__ import annotations

import argparse
import json
import os

from market_data import fetch_quote  # 같은 디렉터리

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "..", "portfolio.json")


def load_cfg() -> dict:
    with open(CFG, encoding="utf-8") as f:
        return json.load(f)


def fx_usdkrw() -> float | None:
    q = fetch_quote("KRW=X")
    return q.get("price") if q and not q.get("error") else None


def eval_positions(items: list[dict]) -> list[dict]:
    rows = []
    for it in items:
        q = fetch_quote(it["ticker"])
        price = None if (not q or q.get("error")) else q.get("price")
        cost, shares = it["cost"], it["shares"]
        if price is None:
            rows.append({**it, "price": None, "ret_pct": None, "pnl": None, "value": None})
            continue
        value = price * shares
        principal = cost * shares
        pnl = value - principal
        ret = (price - cost) / cost * 100 if cost else None
        rows.append({**it, "price": price, "ret_pct": round(ret, 2) if ret is not None else None,
                     "pnl": pnl, "value": value, "principal": principal})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="실시간 평가손익 (Yahoo + portfolio.json)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg = load_cfg()
    fx = fx_usdkrw()
    kr = eval_positions(cfg["holdings"]["kr"])
    us = eval_positions(cfg["holdings"]["us"])

    if args.json:
        print(json.dumps({"fx_usdkrw": fx, "kr": kr, "us": us}, ensure_ascii=False, indent=2))
        return 0

    def section(title, rows, cur):
        print(f"\n### {title}")
        print(f"| {'종목':<12} | {'현재가':>10} | {'평단':>10} | {'수익률':>8} | {'평가손익':>12} |")
        print(f"|{'-'*14}|{'-'*12}|{'-'*12}|{'-'*10}|{'-'*14}|")
        for r in rows:
            if r["price"] is None:
                print(f"| {r['label']:<12} | {'ERROR':>10} | {r['cost']:>10,.0f} | {'—':>8} | {'—':>12} |")
                continue
            pf = (lambda v: f"{v:,.0f}") if cur == "KRW" else (lambda v: f"{v:,.2f}")
            sign = "+" if r["ret_pct"] >= 0 else ""
            print(f"| {r['label']:<12} | {pf(r['price']):>10} | {pf(r['cost']):>10} "
                  f"| {sign}{r['ret_pct']:>6.2f}% | {r['pnl']:>+12,.2f} |")

    section("📈 국내 (KRW)", kr, "KRW")
    section("📈 미국 (USD)", us, "USD")

    # 합계 (KRW 환산)
    kr_val = sum(r["value"] for r in kr if r["value"])
    kr_pnl = sum(r["pnl"] for r in kr if r["pnl"] is not None)
    us_val_usd = sum(r["value"] for r in us if r["value"])
    us_pnl_usd = sum(r["pnl"] for r in us if r["pnl"] is not None)
    cash = cfg.get("cash_krw", 0)

    print(f"\n### 💰 합계")
    print(f"- 환율(USD/KRW): {fx:,.2f}" if fx else "- 환율: 미확인")
    print(f"- 국내 평가액: {kr_val:,.0f}원 (평가손익 {kr_pnl:+,.0f}원)")
    if fx:
        us_val_krw = us_val_usd * fx
        us_pnl_krw = us_pnl_usd * fx
        print(f"- 미국 평가액: ${us_val_usd:,.2f} ≈ {us_val_krw:,.0f}원 (평가손익 ${us_pnl_usd:+,.2f} ≈ {us_pnl_krw:+,.0f}원)")
        total = kr_val + us_val_krw + cash
        total_pnl = kr_pnl + us_pnl_krw
        print(f"- 현금: {cash:,.0f}원")
        print(f"- **총 자산(주식+현금): {total:,.0f}원** | 주식 평가손익 합계: {total_pnl:+,.0f}원")
    else:
        print(f"- 미국 평가액: ${us_val_usd:,.2f} (평가손익 ${us_pnl_usd:+,.2f}) — 환율 미확인으로 원화 환산 생략")
    print("\n※ 원가 고정 기준선 평가. 실제 수량·평단은 토스 실데이터가 정본.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
