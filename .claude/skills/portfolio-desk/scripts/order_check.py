#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
order_check.py — 토스 미체결 주문 ↔ 우리 계획(tasks.json) 대조

왜 있나 [9/21 신설 — 앱 결함이 실주문이 된 날]
────────────────────────────────────────────────────────────
9/21 21:42 NAVER 1주 196,400원 **매수**가 토스에 접수됐다. 6/26에 만들어 '보류'로 멈춘 오더가
앱 결정 카드에 활성처럼 떴고(분류 결함), 정훈이 그걸 보고 걸었다. 계획과는 세 곳에서 충돌했다
(⭐2 기한부 홀드 · 룰6 국내 27.5% > 22% · 사다리 잔여 0원). 사람이 수동 대조로 잡았다.

같은 날 반대 방향 사고도 있었다: 두산로보 78,000원 '매일 등록' 오더가 9/21분 **미등록**이었고
(재등록 알림은 갔지만 확인 수단이 없었다), 과거 v81에선 '4건 접수 완료'로 3일 보고했는데 실제로는
비어 있었다. 알림(notify)은 "걸어라"까지만 하고 **"걸린 게 계획과 같은가"를 아무도 안 봤다.**

이 스크립트가 그 고리를 닫는다 — 토스 OPEN(GET 전용)을 계획과 대조해:

  🔴 계획 밖 매수 / 보류·폐기된 오더와 같은 주문 / ⭐2 이하 추가매수 / 룰6 초과 중 국내 매수
  🟡 계획 밖 매도 / 가격제한폭 밖(접수 거부·무효) / '매일 등록' 오더 미등록 / 사다리 0원 중 매수
  ✅ 계획과 일치

⚠️ 조회 전용 — 토스 가드(_assert_readonly)를 그대로 쓴다. 주문 취소·정정은 **정훈이 직접.**
⚠️ 키는 환경변수(로컬 대화형 세션). 무인 루틴엔 키가 없어서 '미확인'으로 끝난다 — 조용히 통과시키지 않는다.

사용법:
  python3 order_check.py                  # 토스 조회 → 대조 (🔴 있으면 exit 1)
  python3 order_check.py --file open.json # 저장된 OPEN 목록으로 대조(테스트·오프라인)
  python3 order_check.py --json
  결과는 매번 data/app/order_check.json에 남는다 → validate_report.check_order_check가 읽는다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)

TASKS = os.path.join(REPO, "data", "app", "tasks.json")
STOCKS = os.path.join(REPO, "data", "app", "stocks.json")
RULE_LOG = os.path.join(REPO, "data", "app", "rule_log.jsonl")
LIVE = os.path.join(REPO, "app", "live.json")
SNAPS = os.path.join(REPO, "data", "snapshots")
HIST = os.path.join(REPO, "data", "history")
OUT = os.path.join(REPO, "data", "app", "order_check.json")
KST = dt.timezone(dt.timedelta(hours=9))
KR_CAP_PCT = 22.0   # 룰6 국내 목표 상단

DEAD = re.compile(r"폐기|취소|체결|완료|종결|미접수 확정")
HOLD = re.compile(r"보류")


def _load(path, default=None):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _side(action: str) -> str | None:
    a = action or ""
    if "매도" in a or "익절" in a or "트림" in a:
        return "SELL"
    if "매수" in a:
        return "BUY"
    return None


def plan_state(o: dict) -> str:
    st = str(o.get("status") or "")
    if DEAD.search(st):
        return "dead"
    if HOLD.search(st):
        return "hold"
    return "active"


def known_tickers(tasks: dict, stocks: dict) -> list[str]:
    tk = {str(o.get("ticker") or "") for o in tasks.get("orders", [])}
    for grp in ("stocks", "watchlist", "watch"):
        tk.update((stocks.get(grp) or {}).keys())
    return sorted(t for t in tk if t)


def normalize(sym: str, known: list[str]) -> str:
    """토스 심볼(국내 '035420', 미국 'NVDA') → 우리 티커. 접미사는 아는 티커에서 찾는다(.KS/.KQ 혼동 금지)."""
    if re.fullmatch(r"\d{6}", sym or ""):
        for t in known:
            if t.split(".")[0] == sym:
                return t
        return sym + ".KS"
    return sym


def is_kr(t: str) -> bool:
    return bool(re.search(r"\.(KS|KQ)$", t))


def last_close(tk: str) -> tuple[float | None, str | None]:
    """다음 세션 가격제한폭 기준가 — 실시간층의 정규장 종가(rc)가 캐시보다 새로우면 그것."""
    best = (None, None)
    path = os.path.join(HIST, tk + ".csv")
    if os.path.exists(path):
        lines = [ln for ln in open(path, encoding="utf-8").read().splitlines()[1:] if ln.strip()]
        if lines:
            d, c = lines[-1].split(",")[:2]
            best = (float(c), d[:10])
    q = ((_load(LIVE, {}) or {}).get("quotes") or {}).get(tk) or {}
    if q.get("rc") and q.get("rt"):
        d = dt.datetime.fromtimestamp(q["rt"], KST).date().isoformat()
        if best[1] is None or d >= best[1]:
            best = (float(q["rc"]), d)
    return best


def kr_weight() -> float | None:
    snaps = sorted(f for f in os.listdir(SNAPS) if f.endswith(".json")) if os.path.isdir(SNAPS) else []
    if not snaps:
        return None
    s = _load(os.path.join(SNAPS, snaps[-1]), {}) or {}
    try:
        kr = float(s["kr_value"]); us = float(s["us_value_usd"]) * float(s["fx_usdkrw"])
    except (KeyError, TypeError, ValueError):
        return None
    return kr / (kr + us) * 100 if kr + us else None


def ladder_allowed() -> float | None:
    try:
        last = [ln for ln in open(RULE_LOG, encoding="utf-8").read().splitlines() if ln.strip()][-1]
        return float(json.loads(last).get("allowed_krw"))
    except (OSError, IndexError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _same_price(tk: str, a: float, b: float) -> bool:
    if a is None or b is None:
        return False
    if is_kr(tk):
        from validate_report import _kr_tick
        return abs(a - b) < _kr_tick(max(a, b))
    return abs(a - b) <= max(0.01, 0.005 * max(a, b))


def us_track_state() -> dict | None:
    """★[9/21 d205] 미국 트랙 — 달러로 사는 미국주는 코스피 사다리가 아니라 3회 분할 규칙이 다룬다."""
    try:
        import tranche_rules as TR
        return TR.us_track(check_floor=False)
    except Exception:  # noqa: BLE001
        return None


def check(open_orders: list[dict], tasks: dict, stocks: dict,
          kr_w: float | None, allowed: float | None, us: dict | None = None) -> dict:
    from validate_report import _kr_band
    known = known_tickers(tasks, stocks)
    plans = [o for o in tasks.get("orders", []) if _side(o.get("action", ""))]
    stars = {t: (v or {}).get("stars") for g in ("stocks", "watchlist", "watch")
             for t, v in (stocks.get(g) or {}).items()}
    held = set((stocks.get("stocks") or {}).keys())
    try:
        from performance import names
        nm = names()
    except Exception:  # noqa: BLE001 — 이름은 표시용일 뿐, 대조를 막지 않는다
        nm = {}
    rows, findings = [], []

    def add(level, tk, msg):
        findings.append({"level": level, "ticker": tk, "msg": msg})

    for o in open_orders:
        tk = normalize(str(o.get("symbol") or ""), known)
        side = str(o.get("side") or "").upper()
        price = float(o["price"]) if o.get("price") not in (None, "") else None
        qty = o.get("quantity")
        cand = [p for p in plans if p.get("ticker") == tk and _side(p.get("action", "")) == side
                and _same_price(tk, price, p.get("price"))]
        act = [p for p in cand if plan_state(p) == "active"]
        match = (act or cand or [None])[0]
        state = plan_state(match) if match else "none"
        row = {"ticker": tk, "side": side, "price": price, "qty": qty,
               "ordered_at": o.get("orderedAt"), "plan_id": match.get("id") if match else None,
               "plan_state": state}
        rows.append(row)
        verb = "매수" if side == "BUY" else "매도"
        lb = nm.get(tk, tk)
        what = f"{lb} {verb} {price:,.0f} × {qty}" if price else f"{lb} {verb} × {qty}"

        if state in ("dead", "hold"):
            add("red" if side == "BUY" else "yellow", tk,
                f"{what} — 계획상 '{match['status'][:40]}'인 오더({match['id']})와 같은 주문이 살아 있다")
        elif state == "none":
            add("red" if side == "BUY" else "yellow", tk, f"{what} — 계획(tasks.json)에 없는 주문")
        if side == "BUY":
            st = stars.get(tk)
            if st is not None and st <= 2 and tk in held:
                add("red", tk, f"{what} — ⭐{st} 보유 종목 추가매수(⭐2 이하 = 트림 또는 기한부 홀드)")
            if is_kr(tk) and kr_w is not None and kr_w > KR_CAP_PCT:
                add("red", tk, f"{what} — 룰6: 국내 {kr_w:.1f}% > 상단 {KR_CAP_PCT:.0f}% 동안 신규 자금은 100% 미국")
            # d205: 사다리(국내 트랙)는 국내 매수만 본다. 미국 매수는 미국 트랙 회차가 본다.
            if is_kr(tk) and allowed is not None and allowed <= 0 and state != "active":
                add("yellow", tk, f"{what} — 국내 사다리 잔여 0원(계획된 예외가 아니면 재원이 없다)")
            if (not is_kr(tk)) and us and state != "active" and (us.get("allowed_usd") or 0) <= 0:
                add("yellow", tk, f"{what} — 미국 트랙 이번 회차 없음({us.get('why', '')[:60]})")
        if is_kr(tk) and price:
            base, bd = last_close(tk)
            if base:
                up, lo = _kr_band(base)
                row["band"] = [lo, up]
                if not (lo <= price <= up):
                    add("yellow", tk, f"{what} — 가격제한폭 {lo:,}~{up:,}(기준 {bd} 종가 {base:,.0f}) 밖 → 접수 거부/무효")
        if not any(f["ticker"] == tk and f["msg"].startswith(what) for f in findings):
            add("ok", tk, f"{what} — 계획({match['id']})과 일치" if match else what)

    # '매일 등록' 오더가 빠졌나 — 접수 가능한 가격인데 OPEN에 없으면 미등록
    for p in plans:
        if p.get("register_policy") != "always" or plan_state(p) != "active":
            continue
        tk, side, price = p.get("ticker"), _side(p.get("action", "")), p.get("price")
        if any(r["ticker"] == tk and r["side"] == side and _same_price(tk, r["price"], price) for r in rows):
            continue
        verb = "매수" if side == "BUY" else "매도"
        lb = nm.get(tk, tk)
        if is_kr(tk) and price:
            base, bd = last_close(tk)
            if base:
                up, lo = _kr_band(base)
                if not (lo <= float(price) <= up):
                    add("info", tk, f"{lb} {verb} {float(price):,.0f} 미등록 — 정상(상한 {up:,} < 주문가, 기준 {bd} 종가)")
                    continue
        add("yellow", tk, f"{lb} {verb} {float(price):,.0f} '매일 등록' 오더가 토스에 없다({p['id']}) — 재등록 필요")

    lv = [f["level"] for f in findings]
    return {"checked_at": dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
            "source": "toss", "open": rows, "findings": findings,
            "counts": {k: lv.count(k) for k in ("red", "yellow", "ok", "info")},
            "context": {"kr_weight_pct": round(kr_w, 1) if kr_w is not None else None,
                        "ladder_allowed_krw": allowed,
                        "us_allowed_usd": (us or {}).get("allowed_usd")}}


ICON = {"red": "🔴", "yellow": "🟡", "ok": "✅", "info": "ℹ️"}


def _usd(v) -> str:
    return "미확인" if v is None else f"${float(v):,.2f}"


def _won(v) -> str:
    return "미확인" if v is None else f"{float(v):,.0f}원"


def render(r: dict) -> str:
    if r.get("source") == "unavailable":
        return "⚠️ 토스 조회 불가(키 없음·인증 실패) — **대조 미실행**. '주문 없음'이 아니다."
    L = [f"=== 토스 미체결 ↔ 계획 대조 ({r['checked_at']}) — 미체결 {len(r['open'])}건 ==="]
    for lvl in ("red", "yellow", "ok", "info"):
        for f in r["findings"]:
            if f["level"] == lvl:
                L.append(f"{ICON[lvl]} {f['msg']}")
    c = r["counts"]
    L.append(f"\n🔴 {c['red']} · 🟡 {c['yellow']} · ✅ {c['ok']}  (국내 비중 {r['context']['kr_weight_pct']}% · 국내 사다리 잔여 {_won(r['context']['ladder_allowed_krw'])} · 미국 회차 {_usd(r['context'].get('us_allowed_usd'))})")
    if c["red"]:
        L.append("→ 🔴 주문은 정훈이 토스에서 직접 취소·정정(주문 API 호출 금지).")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="토스 미체결 주문 ↔ tasks.json 계획 대조 (조회 전용)")
    ap.add_argument("--file", help="OPEN 주문 JSON(리스트 또는 toss_snapshot --orders 출력)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-save", action="store_true", help="data/app/order_check.json을 안 쓴다(테스트용)")
    a = ap.parse_args()

    if a.file:
        raw = _load(a.file)
        opens = raw.get("orders", []) if isinstance(raw, dict) else (raw or [])
        src = "file"
    else:
        import toss_snapshot
        opens = toss_snapshot.fetch_orders("OPEN")
        src = "toss"
    if opens is None:
        r = {"checked_at": dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "source": "unavailable",
             "open": [], "findings": [], "counts": {"red": 0, "yellow": 0, "ok": 0, "info": 0}}
    else:
        r = check([o for o in opens if str(o.get("status", "PENDING")).upper() != "CANCELED"],
                  _load(TASKS, {}) or {}, _load(STOCKS, {}) or {}, kr_weight(), ladder_allowed(),
                  us_track_state())
        r["source"] = src
    if not a.no_save and src != "file":
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
            f.write("\n")
    print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else render(r))
    return 1 if r["counts"]["red"] else (2 if r["source"] == "unavailable" else 0)


if __name__ == "__main__":
    sys.exit(main())
