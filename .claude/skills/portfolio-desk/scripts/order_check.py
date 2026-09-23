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
  python3 order_check.py --file open.json --now "2026-09-22 22:01" --no-save   # 그 시각 기준으로 재현
  python3 order_check.py --selftest       # 가격제한폭 기준가 회귀 테스트(guard_selftest가 부른다)
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
SNAPS = os.path.join(REPO, "data", "snapshots")
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


def band_note(bb: dict) -> str:
    """기준가 표기 — '기준 {날짜} 종가 → {세션} 세션', 폴백이면 무엇이 빠졌는지까지."""
    ss = dt.date.fromisoformat(bb["session"])
    s = f"기준 {bb['date']} 종가 → {ss.month}/{ss.day} 세션"
    return s + (f" ⚠️{bb['want']} 종가 미확보" if bb["stale"] else "")


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
          kr_w: float | None, allowed: float | None, us: dict | None = None,
          now: dt.datetime | None = None) -> dict:
    # ★[9/22] 기준가 = validate_report.kr_band_base(check_kr_price_band와 같은 함수) — 舊 last_close()는
    #   history 캐시·live.json만 봐서 마감 후에도 전일 종가를 썼다(9/22 22:01 현대차 상한 466,500 vs 실제 468,500).
    from validate_report import _kr_band, kr_band_base
    now = now or dt.datetime.now(KST)
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
            bb = kr_band_base(tk, now)
            if bb:
                up, lo = _kr_band(bb["base"])
                row["band"] = [lo, up]
                row["band_base"] = {k: bb[k] for k in ("date", "base", "src", "session", "stale")}
                if not (lo <= price <= up):
                    add("yellow", tk, f"{what} — 가격제한폭 {lo:,}~{up:,}({band_note(bb)} {bb['base']:,.0f}) 밖 → 접수 거부/무효")
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
            bb = kr_band_base(tk, now)
            if bb:
                up, lo = _kr_band(bb["base"])
                if not (lo <= float(price) <= up):
                    edge = f"상한 {up:,} < 주문가" if float(price) > up else f"하한 {lo:,} > 주문가"
                    add("info", tk, f"{lb} {verb} {float(price):,.0f} 미등록 — 정상({edge}, {band_note(bb)})")
                    continue
        add("yellow", tk, f"{lb} {verb} {float(price):,.0f} '매일 등록' 오더가 토스에 없다({p['id']}) — 재등록 필요")

    lv = [f["level"] for f in findings]
    return {"checked_at": now.astimezone(KST).strftime("%Y-%m-%d %H:%M"),
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


def selftest() -> int:
    """가격제한폭 기준가 회귀 테스트 — 임시 ROOT 픽스처 + --file 경로(OPEN 목록 직접 주입)로 시각별 판정을 고정한다.

    ★[9/22 실사고] 22:01 현대차 470,000 미등록 판정이 '상한 466,500, 기준 2026-09-21 종가'로 나왔다.
    9/22 종가 360,500(quotes.jsonl 16:04 적재)가 있었으니 9/23 세션 상한은 468,500이어야 했다.
    픽스처 = 그날 실제 값(9/21 종가 359,000 · 9/22 종가 360,500 · 추석 9/24~25 휴장).
    """
    import shutil
    import tempfile
    import validate_report as V

    tk, hist = "005380.KS", "data/history/005380.KS.csv"
    h = lambda d, hm: dt.datetime.fromisoformat(f"{d}T{hm}:00+09:00")  # noqa: E731
    files = {
        hist: "date,close\n2026-09-18,365000.0\n2026-09-21,359000.0\n",
        "data/timeseries/quotes.jsonl": "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in [
            {"date": "2026-09-21", "ts": "2026-09-21T16:25:27+09:00", "symbol": tk, "price": 359000.0},
            {"date": "2026-09-22", "ts": "2026-09-22T11:00:00+09:00", "symbol": tk, "price": 358000.0},  # 장중
            {"date": "2026-09-22", "ts": "2026-09-22T16:04:41+09:00", "symbol": tk, "price": 360500.0},
            {"date": "2026-07-20", "ts": "2026-07-20", "symbol": tk, "price": 1.0},                     # 소급분(시각 없음)
        ]),
        # 로컬 실시간층 — 9/21 21:29에 멈춘 상태 그대로. p(애프터마켓 361,500)는 기준가가 아니다.
        "app/live.json": json.dumps({"quotes": {tk: {"p": 361500.0, "rc": 359000.0,
                                                    "rt": int(h("2026-09-21", "15:30").timestamp()) + 8}}}),
        "data/app/macro_events.json": json.dumps({"events": [
            {"date": "2026-09-24", "end": "2026-09-25", "kind": "휴장", "name": "추석"}]}, ensure_ascii=False),
    }
    tmp = tempfile.mkdtemp(prefix="order_check_selftest_")
    old_root, ok = V.ROOT, True

    def expect(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'✅' if good else '❌'} {label}: {got}" + ("" if good else f"  (기대 {want})"))

    def base(now):
        bb = V.kr_band_base(tk, now)
        return bb and (bb["date"], bb["base"], bb["session"], bb["stale"])

    try:
        for rel, body in files.items():
            p = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(body)
        V.ROOT = tmp
        print("order_check 가격제한폭 기준가 selftest")
        expect("9/22 22:01 마감 후 → 오늘 종가", base(h("2026-09-22", "22:01")),
               ("2026-09-22", 360500.0, "2026-09-23", False))
        expect("9/22 15:38 마감 직후·적재 전 → 전일 종가 폴백 + stale", base(h("2026-09-22", "15:38")),
               ("2026-09-21", 359000.0, "2026-09-23", True))
        expect("9/22 11:00 장중 → 전일 종가(장중 358,000 제외)", base(h("2026-09-22", "11:00")),
               ("2026-09-21", 359000.0, "2026-09-22", False))
        expect("9/22 07:30 프리마켓 → 전일 종가", base(h("2026-09-22", "07:30")),
               ("2026-09-21", 359000.0, "2026-09-22", False))
        expect("9/23 22:00 오늘 종가 없음 → 폴백 + stale(세션 = 추석 뒤 9/28)", base(h("2026-09-23", "22:00")),
               ("2026-09-22", 360500.0, "2026-09-28", True))
        expect("9/26(토) → 9/28 세션", base(h("2026-09-26", "10:00"))[2], "2026-09-28")

        # --file 경로: OPEN 목록 직접 주입 → 실제 판정 문구(기준일 병기)까지 본다
        tasks = {"orders": [{"id": "o-hmc-470k", "ticker": tk, "action": "트림 매도 지정가", "price": 470000,
                             "status": "매일 등록", "register_policy": "always"}]}
        r = check([], tasks, {}, None, None, None, now=h("2026-09-22", "22:01"))
        msg = next((f["msg"] for f in r["findings"] if f["ticker"] == tk), "")
        expect("미등록 판정 문구", ("상한 468,500" in msg, "기준 2026-09-22 종가" in msg, "9/23 세션" in msg),
               (True, True, True))
        r = check([{"symbol": "005380", "side": "SELL", "price": "470000", "quantity": "1"}],
                  tasks, {}, None, None, None, now=h("2026-09-22", "22:01"))
        row, f0 = r["open"][0], r["findings"][0]
        expect("OPEN 주문 밴드", (row["band"][1], f0["level"], "기준 2026-09-22 종가" in f0["msg"]),
               (468500, "yellow", True))

        # 캐시 오염(8/13) — history에 장중값이 오늘 종가로 박혀 있어도 시각 있는 확정 종가가 이긴다
        with open(os.path.join(tmp, hist), "a", encoding="utf-8") as f:
            f.write("2026-09-22,358000.0\n")
        expect("history 장중 오염 vs quotes 확정", base(h("2026-09-22", "22:01"))[:2], ("2026-09-22", 360500.0))
        expect("장중엔 오염 행도 제외", base(h("2026-09-22", "11:00"))[:2], ("2026-09-21", 359000.0))
        # quotes·live가 없으면 history 폴백 — 기준일이 그대로 드러나야 한다
        os.remove(os.path.join(tmp, "data/timeseries/quotes.jsonl"))
        os.remove(os.path.join(tmp, "app/live.json"))
        with open(os.path.join(tmp, hist), "w", encoding="utf-8") as f:
            f.write(files[hist])
        expect("history만 → 9/21 폴백 + stale", base(h("2026-09-22", "22:01")),
               ("2026-09-21", 359000.0, "2026-09-23", True))
    finally:
        V.ROOT = old_root
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS" if ok else "FAIL — 기준가 선택이 회귀했다")
    return 0 if ok else 1


def _parse_now(s: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(s.replace(" ", "T"))
    return t.replace(tzinfo=KST) if t.tzinfo is None else t


def main() -> int:
    ap = argparse.ArgumentParser(description="토스 미체결 주문 ↔ tasks.json 계획 대조 (조회 전용)")
    ap.add_argument("--file", help="OPEN 주문 JSON(리스트 또는 toss_snapshot --orders 출력)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-save", action="store_true", help="data/app/order_check.json을 안 쓴다(테스트용)")
    ap.add_argument("--now", type=_parse_now, help="판정 시각 고정(KST, 예: '2026-09-22 22:01') — 재현용")
    ap.add_argument("--selftest", action="store_true", help="가격제한폭 기준가 회귀 테스트(임시 ROOT 픽스처)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    if a.file:
        raw = _load(a.file)
        opens = raw.get("orders", []) if isinstance(raw, dict) else (raw or [])
        src = "file"
    else:
        import toss_snapshot
        opens = toss_snapshot.fetch_orders("OPEN")
        src = "toss"
    if opens is None:
        r = {"checked_at": (a.now or dt.datetime.now(KST)).strftime("%Y-%m-%d %H:%M"), "source": "unavailable",
             "open": [], "findings": [], "counts": {"red": 0, "yellow": 0, "ok": 0, "info": 0}}
    else:
        r = check([o for o in opens if str(o.get("status", "PENDING")).upper() != "CANCELED"],
                  _load(TASKS, {}) or {}, _load(STOCKS, {}) or {}, kr_weight(), ladder_allowed(),
                  us_track_state(), now=a.now)
        r["source"] = src
    # unavailable(토스 미접근)은 저장하지 않는다 — 안 그러면 마지막 실제 대조 결과를 빈 값으로 덮어쓴다(9/23 클라우드 실사고).
    if not a.no_save and src != "file" and r["source"] != "unavailable":
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
            f.write("\n")
    print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else render(r))
    return 1 if r["counts"]["red"] else (2 if r["source"] == "unavailable" else 0)


if __name__ == "__main__":
    sys.exit(main())
