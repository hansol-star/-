#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
event_calendar.py — 통합 이벤트 캘린더 (실적 + 매크로) D-day 정렬.

보고서 §4 '지켜볼 것'을 하나의 D-day 뷰로. 두 소스를 병합:
  1) 실적 발표일 — earnings.py 재사용(Yahoo calendarEvents, 보유+워치 라이브).
  2) 매크로 이벤트 — data/app/macro_events.json 큐레이션(FOMC·CPI·금통위, macro-desk 검증).

폰 가용창(평일 17:30~20:50 / 주말 09:00~20:50 KST) 밖 이벤트는 kst_note로 플래그
→ 사전 조건부 룰·예약주문으로 베이킹해야 함(당일 밤 트리거 금지, 운영제약 영구룰).

사용:
  python3 event_calendar.py                 # 45일 이내 실적+매크로 (기본)
  python3 event_calendar.py --within 30
  python3 event_calendar.py --no-earnings   # 매크로만(네트워크 없이 빠르게)
  python3 event_calendar.py --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MACRO = os.path.join(HERE, "..", "..", "..", "..", "data", "app", "macro_events.json")
KST = dt.timezone(dt.timedelta(hours=9))


def today_kst() -> dt.date:
    return dt.datetime.now(KST).date()


def load_macro(today: dt.date) -> list[dict]:
    if not os.path.exists(MACRO):
        return []
    try:
        with open(MACRO, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    for e in data.get("events", []):
        try:
            d = dt.date.fromisoformat(e["date"])
        except (ValueError, KeyError):
            continue
        out.append({
            "date": e["date"], "days_until": (d - today).days,
            "kind": e.get("kind", "매크로"), "label": e.get("name", "?"),
            "note": e.get("kst_note", ""), "confidence": e.get("confidence", "미확인"),
            "type": "macro",
        })
    return out


def load_earnings(today: dt.date) -> list[dict]:
    """earnings.py의 crumb·fetch 로직 재사용. 실패(네트워크·crumb)해도 캘린더는 계속."""
    try:
        from consensus import _opener, get_crumb
        from earnings import fetch_earnings
    except ImportError:
        return []
    cfg_path = os.path.join(HERE, "..", "portfolio.json")
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return []
    op = _opener()
    crumb = get_crumb(op)
    if not crumb:
        return []
    out = []
    for h in cfg["holdings"]["kr"] + cfg["holdings"]["us"] + cfg.get("watchlist", []):
        r = fetch_earnings(op, crumb, h["ticker"])
        nearest, days = None, None
        for d in r.get("earnings_dates", []):
            try:
                dd = dt.date.fromisoformat(d)
            except ValueError:
                continue
            delta = (dd - today).days
            if delta >= 0 and (days is None or delta < days):
                nearest, days = d, delta
        if nearest is not None:
            out.append({"date": nearest, "days_until": days, "kind": "실적",
                        "label": h["label"], "note": "", "confidence": "확정",
                        "type": "earnings"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="통합 이벤트 캘린더 (실적+매크로)")
    ap.add_argument("--within", type=int, default=45, help="N일 이내 (기본 45)")
    ap.add_argument("--no-earnings", action="store_true", help="실적 생략(매크로만)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    today = today_kst()
    events = load_macro(today)
    if not args.no_earnings:
        events += load_earnings(today)

    upcoming = sorted([e for e in events
                       if e["days_until"] is not None and 0 <= e["days_until"] <= args.within],
                      key=lambda e: e["days_until"])

    if args.json:
        print(json.dumps(upcoming, ensure_ascii=False, indent=2))
        return 0

    print(f"## 📅 다가오는 이벤트 캘린더 ({args.within}일 이내) — 기준 {today.isoformat()} KST\n")
    if not upcoming:
        print("- 해당 기간 내 이벤트 없음")
        return 0
    for e in upcoming:
        icon = {"FOMC": "🏦", "CPI": "📈", "BOK": "🇰🇷", "실적": "💵"}.get(e["kind"], "•")
        soon = " ⚡임박" if e["days_until"] <= 7 else ""
        conf = "" if e["confidence"] == "확정" else f" [{e['confidence']}]"
        line = f"- {icon} **D-{e['days_until']:<2}** {e['date']}  {e['label']}{conf}{soon}"
        print(line)
        if e["note"]:
            print(f"      └ {e['note']}")
    # 폰창 밖 = 사전 베이킹 필요한 것 요약
    baked = [e for e in upcoming if "폰창 밖" in e.get("note", "")]
    if baked:
        print(f"\n⚠️ 폰창 밖({len(baked)}) — 사전 조건부 룰·예약주문 필요: "
              + ", ".join(f"{e['label']}(D-{e['days_until']})" for e in baked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
