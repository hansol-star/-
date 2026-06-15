#!/usr/bin/env python3
"""
triggers.py — 매수존·안전핀·이벤트 트리거 실시간 점검.

portfolio.json의 alerts를 실시간 시세(Yahoo)와 대조해
🔴발동 / 🟢대기(레벨까지 거리) / 📅이벤트 를 한눈에 보여준다.
폰 가용 17:30~18:00 거래창에서 "지금 뭘 눌러야 하나"를 즉시 판단.

조건 종류:
  below {level}        : 현재가 < level 이면 발동
  above {level}        : 현재가 > level 이면 발동
  between {low,high}   : low ≤ 현재가 ≤ high 이면 발동(매수존 진입)
  event {when}         : 자동평가 불가 — 캘린더로 표시만
  signal {when}        : 시세 무관 추적 신호(외인 수급 등) — 액션 노트만 표시

사용:
  python3 triggers.py            # 표
  python3 triggers.py --json
"""
from __future__ import annotations

import argparse
import json
import os

from market_data import fetch_quote

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "..", "portfolio.json")


def evaluate(alert: dict) -> dict:
    cond = alert.get("cond")
    if cond == "event":
        return {**alert, "state": "event", "price": None, "detail": alert.get("when", "")}
    if cond == "signal":
        return {**alert, "state": "signal", "price": None, "detail": alert.get("when", "매 보고서")}

    q = fetch_quote(alert["ticker"])
    price = None if (not q or q.get("error")) else q.get("price")
    if price is None:
        return {**alert, "state": "error", "price": None, "detail": "시세 조회 실패"}

    fired, detail = False, ""
    if cond == "below":
        lv = alert["level"]
        fired = price < lv
        detail = f"현재 {price:,.0f} vs 기준 {lv:,.0f} ({(price-lv)/lv*100:+.1f}%)"
    elif cond == "above":
        lv = alert["level"]
        fired = price > lv
        detail = f"현재 {price:,.0f} vs 기준 {lv:,.0f} ({(price-lv)/lv*100:+.1f}%)"
    elif cond == "between":
        lo, hi = alert["low"], alert["high"]
        fired = lo <= price <= hi
        if price > hi:
            detail = f"현재 {price:,.0f} — 매수존 {lo:,.0f}~{hi:,.0f} 위 ({(price-hi)/hi*100:+.1f}%)"
        elif price < lo:
            detail = f"현재 {price:,.0f} — 매수존 {lo:,.0f}~{hi:,.0f} 아래 ({(price-lo)/lo*100:+.1f}%)"
        else:
            detail = f"현재 {price:,.0f} — 매수존 {lo:,.0f}~{hi:,.0f} 진입!"
    return {**alert, "state": "fired" if fired else "armed", "price": price, "detail": detail}


def main() -> int:
    ap = argparse.ArgumentParser(description="트리거·매수존 실시간 점검")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    with open(CFG, encoding="utf-8") as f:
        cfg = json.load(f)
    results = [evaluate(a) for a in cfg.get("alerts", [])]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    icon = {"fired": "🔴 발동", "armed": "🟢 대기", "event": "📅 이벤트", "signal": "📡 신호", "error": "⚠️ 오류"}
    fired = [r for r in results if r["state"] == "fired"]

    print("## 트리거 점검\n")
    if fired:
        print("### 🔴 지금 발동된 트리거")
        for r in fired:
            print(f"- **{r['id']}** — {r['detail']}\n  → {r['action']}")
        print()
    print("### 전체")
    for r in results:
        print(f"- {icon.get(r['state'],'?')} **{r['id']}**: {r['detail']}")
        if r["state"] in ("armed", "event", "signal"):
            print(f"    ↳ {r['action']}")
    if not fired:
        print("\n→ 발동된 트리거 없음. 대기 상태 유지.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
