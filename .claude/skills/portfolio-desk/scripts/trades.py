#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trades.py — 체결 원장 재생·대사 (Trade Ledger Replay & Reconcile)

왜 있나 [8/23 신설 — 정훈 지시 "참고 소스 보고 앱 발전시키자"]
────────────────────────────────────────────────────────────
우리는 **수량·평단을 정본으로 두고 체결은 산문에 적어왔다.** 그래서 체결이 날 때마다
사람이 세 곳(portfolio.json → master.md 표 → tasks.json)을 손으로 맞춰야 했고,
실제로 두 번 어긋났다:

  · 8/6  GOOGL 7/29 매수가 master 표에 1주일 stale
  · 8/19 ANET 전량매도·VOO 적립체결이 8일간 반영 안 됨 (master.md §2 2차 정정)

master.md는 그때 *"산문 표는 기계가 안 보므로 validate_report도 못 잡는다"*고 적고
**절차(한 커밋에 세 곳 동시수정)**로 막기로 했다. 하지만 절차는 사람이 지키는 것이고
같은 다짐을 적어둔 뒤에 그대로 재발했다. 이 스크립트는 그걸 **구조**로 바꾼다:

  체결 원장(data/app/trades.jsonl)이 정본 → 수량·평단·실현손익은 **재생된 파생물**

파생물은 원본과 어긋날 수가 없다. 남는 위험은 '원장에 기입을 빠뜨리는 것' 하나뿐이고,
그건 `--reconcile`이 portfolio.json과 대조해 **숫자로 잡는다**(빠뜨리면 수량이 안 맞는다).

회계 방식
────────
· 이동평균법 — 매수 시 평단 재계산, 매도는 평단 불변(토스·국내 관행과 동일)
· 취득원가에 수수료를 **넣지 않는다** — 문서화된 평단 변화(GOOGL $387.73→$358.01,
  VOO $645.40→$648.75)를 그대로 재현하는 쪽이 수수료 포함식이다. 실현손익에서는 차감.
· `side="opening"` = 데스크 착수 시점 기초 잔고. 원장 이전의 매매는 우리 기록이 아니므로
  체결로 위장하지 않고 기초로 명시한다(삼성전자 기초 평단만 derived=true).

⚠️ 측정·대사 전용 — 자동 매매 없음. 원장 기입은 체결 확인(토스 스크린샷) 후에만.

사용법:
  python3 trades.py                      # 포지션 재생 + 실현손익
  python3 trades.py --reconcile          # portfolio.json 대사 (어긋나면 exit 1)
  python3 trades.py --realized           # 실현손익 상세
  python3 trades.py --ticker AAPL        # 한 종목 체결 이력
  python3 trades.py --json               # 기계 출력 (build_app_data가 소비)
  python3 trades.py --add --date 2026-08-26 --ticker META --side sell \\
      --shares 1 --price 580 --currency USD --source "토스 스크린샷 8/26"
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
LEDGER = os.path.join(REPO, "data", "app", "trades.jsonl")
PORTFOLIO_JSON = os.path.join(HERE, "..", "portfolio.json")

# 대사 허용오차 — 수량은 소수점 6자리(토스 표기 한계), 평단은 0.5%
# (문서화된 평단이 반올림된 값이라 기초 역산에 $0.2 수준 잔차가 남는다. 그 이상은 기입 누락 신호.)
QTY_TOL = 1e-6
COST_TOL_PCT = 0.5

SIDES = ("opening", "buy", "sell")


def load_ledger(path: str = LEDGER) -> list[dict]:
    if not os.path.exists(path):
        return []
    rows = []
    for i, ln in enumerate(open(path, encoding="utf-8"), 1):
        ln = ln.strip()
        if not ln or ln.startswith("//"):
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError as e:
            print(f"⚠️ {os.path.basename(path)}:{i} JSON 파싱 실패 — {e}", file=sys.stderr)
            continue
        if r.get("side") not in SIDES:
            print(f"⚠️ {os.path.basename(path)}:{i} 알 수 없는 side={r.get('side')!r} — 건너뜀", file=sys.stderr)
            continue
        rows.append(r)
    rows.sort(key=lambda r: (r.get("date", ""), 0 if r.get("side") == "opening" else 1))
    return rows


def _amount(r: dict) -> float:
    """거래대금. amount가 있으면 그걸(원문 기록), 없으면 주수×단가."""
    a = r.get("amount")
    if a is not None:
        return float(a)
    return float(r.get("shares") or 0) * float(r.get("price") or 0)


def replay(rows: list[dict]) -> dict:
    """원장을 시간순으로 재생해 종목별 최종 포지션·실현손익을 만든다."""
    pos: dict[str, dict] = {}
    for r in rows:
        tk = r["ticker"]
        p = pos.setdefault(tk, {
            "ticker": tk, "label": r.get("label") or tk, "currency": r.get("currency", "KRW"),
            "shares": 0.0, "avg_cost": 0.0, "realized": 0.0, "realized_krw": 0.0,
            "fees": 0.0, "buys": 0, "sells": 0, "fx_estimated": False,
            "first_date": r.get("date"), "last_date": r.get("date"),
        })
        p["last_date"] = r.get("date")
        if r.get("label"):
            p["label"] = r["label"]
        sh = float(r.get("shares") or 0)
        amt = _amount(r)
        fee = float(r.get("fee") or 0) + float(r.get("tax") or 0)
        p["fees"] += fee

        if r["side"] in ("opening", "buy"):
            new_sh = p["shares"] + sh
            if new_sh > 0:
                p["avg_cost"] = (p["shares"] * p["avg_cost"] + amt) / new_sh
            p["shares"] = new_sh
            if r["side"] == "buy":
                p["buys"] += 1
        else:  # sell — 평단 불변, 실현손익 확정
            gain = amt - sh * p["avg_cost"] - fee
            p["realized"] += gain
            p["shares"] = p["shares"] - sh
            if abs(p["shares"]) < QTY_TOL:
                p["shares"] = 0.0
            p["sells"] += 1
            fx = r.get("fx_rate")
            if p["currency"] == "USD":
                if fx:
                    p["realized_krw"] += gain * float(fx)
                else:
                    p["fx_estimated"] = True   # 환율 미기록 → 아래에서 현재 환율로 보정
            else:
                p["realized_krw"] += gain
    return pos


def realized_krw_detail(rows: list[dict], fx_now: float) -> list[dict]:
    """매도 건별 실현손익(USD/KRW) — 환율 미기록분은 현재 환율로 추정 표기."""
    pos = {}
    out = []
    for r in rows:
        tk = r["ticker"]
        p = pos.setdefault(tk, {"shares": 0.0, "avg": 0.0})
        sh = float(r.get("shares") or 0)
        amt = _amount(r)
        fee = float(r.get("fee") or 0) + float(r.get("tax") or 0)
        if r["side"] in ("opening", "buy"):
            new_sh = p["shares"] + sh
            if new_sh > 0:
                p["avg"] = (p["shares"] * p["avg"] + amt) / new_sh
            p["shares"] = new_sh
            continue
        gain = amt - sh * p["avg"] - fee
        p["shares"] -= sh
        cur = r.get("currency", "KRW")
        fx = r.get("fx_rate")
        est = cur == "USD" and not fx
        rate = float(fx) if fx else (fx_now if cur == "USD" else 1.0)
        out.append({
            "date": r.get("date"), "ticker": tk, "label": r.get("label") or tk,
            "shares": sh, "price": float(r.get("price") or 0), "currency": cur,
            "cost_basis": p["avg"], "realized": gain, "realized_krw": gain * rate,
            "return_pct": (gain / (sh * p["avg"]) * 100) if p["avg"] and sh else None,
            "fx_rate": rate, "fx_estimated": est,
            "source": r.get("source", ""), "note": r.get("note", ""),
        })
    return out


def current_fx(default: float = 1383.9) -> float:
    """USD/KRW 현재 환율. portfolio.json의 fx는 티커 목록이라 값이 없다 →
    빌드 산출물(app/data.js)의 fx.usdkrw를 쓴다. 없으면 default."""
    path = os.path.join(REPO, "app", "data.js")
    try:
        raw = open(path, encoding="utf-8").read()
        body = raw[raw.index("{"):raw.rindex("}") + 1]
        return float(json.loads(body).get("fx", {}).get("usdkrw") or default)
    except Exception:
        return default


def load_portfolio() -> dict:
    with open(PORTFOLIO_JSON, encoding="utf-8") as f:
        return json.load(f)


def portfolio_positions(p: dict) -> dict:
    out = {}
    for region in ("kr", "us"):
        for h in (p.get("holdings") or {}).get(region, []):
            out[h["ticker"]] = {
                "label": h.get("label", h["ticker"]), "shares": float(h.get("shares") or 0),
                "cost": float(h.get("cost") or 0), "region": region,
                "currency": "KRW" if region == "kr" else "USD",
            }
    return out


def reconcile(pos: dict, book: dict) -> list[dict]:
    """원장 재생 결과 vs portfolio.json — 어긋나는 지점을 찾아낸다."""
    rows = []
    for tk in sorted(set(pos) | set(book)):
        led = pos.get(tk)
        bk = book.get(tk)
        led_sh = led["shares"] if led else 0.0
        led_cost = led["avg_cost"] if led else 0.0
        bk_sh = bk["shares"] if bk else 0.0
        bk_cost = bk["cost"] if bk else 0.0
        # 원장이 0주로 재생했고 장부에도 없으면 = 전량매도 종목(정상)
        if led_sh == 0 and bk is None:
            rows.append({"ticker": tk, "label": (led or {}).get("label", tk), "status": "closed",
                         "ledger_shares": 0.0, "book_shares": None, "ledger_cost": led_cost,
                         "book_cost": None, "detail": "전량매도 — 장부에 없는 것이 정상"})
            continue
        qty_ok = abs(led_sh - bk_sh) <= QTY_TOL
        cost_ok = (bk_cost == 0 and led_cost == 0) or (
            bk_cost > 0 and abs(led_cost - bk_cost) / bk_cost * 100 <= COST_TOL_PCT)
        status = "ok" if (qty_ok and cost_ok) else "diff"
        detail = []
        if not qty_ok:
            detail.append(f"수량 {led_sh:.6f} vs 장부 {bk_sh:.6f} (차 {led_sh - bk_sh:+.6f})")
        if not cost_ok:
            gap = (led_cost - bk_cost) / bk_cost * 100 if bk_cost else 0
            detail.append(f"평단 {led_cost:,.2f} vs 장부 {bk_cost:,.2f} ({gap:+.2f}%)")
        rows.append({"ticker": tk, "label": (led or bk or {}).get("label", tk), "status": status,
                     "ledger_shares": led_sh, "book_shares": bk_sh,
                     "ledger_cost": led_cost, "book_cost": bk_cost,
                     "detail": " · ".join(detail) or "일치"})
    return rows


def summary(rows: list[dict], fx_now: float) -> dict:
    """build_app_data가 소비할 요약 — 실현손익 누계 + 최근 체결."""
    detail = realized_krw_detail(rows, fx_now)
    fills = [r for r in rows if r.get("side") != "opening"]
    realized_krw = sum(d["realized_krw"] for d in detail)
    wins = [d for d in detail if d["realized"] > 0]
    # 합계를 낸 뒤 건별 표시값을 원 단위로 정리 — 앱이 소수점 원(72,255.786원)을 그리던 결함
    for d in detail:
        d["realized_krw"] = round(d["realized_krw"])
        d["realized"] = round(d["realized"], 2)
        d["cost_basis"] = round(d["cost_basis"], 2)
        if d["return_pct"] is not None:
            d["return_pct"] = round(d["return_pct"], 1)
    return {
        "fills": len(fills),
        "buys": sum(1 for r in fills if r["side"] == "buy"),
        "sells": len(detail),
        "realized_krw": round(realized_krw),
        "realized_usd": round(sum(d["realized"] for d in detail if d["currency"] == "USD"), 2),
        "realized_krw_only": round(sum(d["realized"] for d in detail if d["currency"] == "KRW")),
        "win_rate": round(len(wins) / len(detail) * 100, 1) if detail else None,
        "fx_estimated": any(d["fx_estimated"] for d in detail),
        "first_date": fills[0]["date"] if fills else None,
        "last_date": fills[-1]["date"] if fills else None,
        "sells_detail": sorted(detail, key=lambda d: d["date"], reverse=True),
        "recent": [{
            "date": r["date"], "ticker": r["ticker"], "label": r.get("label") or r["ticker"],
            "side": r["side"], "shares": r.get("shares"), "price": r.get("price"),
            "currency": r.get("currency"), "note": r.get("note", ""), "source": r.get("source", ""),
        } for r in sorted(fills, key=lambda r: r["date"], reverse=True)],
    }


def cmd_add(args) -> int:
    if not args.source:
        print("❌ --source 필수 — 체결 확인 근거(토스 스크린샷·보고서)를 반드시 남긴다.", file=sys.stderr)
        return 1
    row = {
        "date": args.date, "ticker": args.ticker, "label": args.label or args.ticker,
        "side": args.side, "shares": args.shares, "price": args.price,
        "amount": args.amount if args.amount is not None else round(args.shares * args.price, 4),
        "currency": args.currency, "fee": args.fee, "tax": args.tax,
        "fx_rate": args.fx_rate, "derived": False, "source": args.source, "note": args.note or "",
    }
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"✅ 원장 기입: {row['date']} {row['label']} {row['side']} {row['shares']}주 @{row['price']}")
    print("→ 이어서 `python3 trades.py --reconcile`로 portfolio.json과 대사할 것.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="체결 원장 재생·대사 (측정 전용, 자동매매 없음)")
    ap.add_argument("--reconcile", action="store_true", help="portfolio.json과 대사 (불일치 시 exit 1)")
    ap.add_argument("--realized", action="store_true", help="매도 건별 실현손익 상세")
    ap.add_argument("--ticker", help="한 종목 체결 이력만")
    ap.add_argument("--fx", type=float, default=None, help="환율 미기록 실현분에 쓸 환율(기본: portfolio.json)")
    ap.add_argument("--json", action="store_true", help="기계 출력")
    sub = ap.add_argument_group("--add (신규 체결 기입)")
    ap.add_argument("--add", action="store_true", help="체결 1건을 원장에 append")
    sub.add_argument("--date", default=dt.date.today().isoformat())
    sub.add_argument("--side", choices=("buy", "sell"), default="buy")
    sub.add_argument("--shares", type=float, default=0.0)
    sub.add_argument("--price", type=float, default=0.0)
    sub.add_argument("--amount", type=float, default=None, help="실제 거래대금(있으면 단가보다 우선)")
    sub.add_argument("--currency", choices=("KRW", "USD"), default="KRW")
    sub.add_argument("--fee", type=float, default=0.0)
    sub.add_argument("--tax", type=float, default=0.0)
    sub.add_argument("--fx-rate", dest="fx_rate", type=float, default=None, help="체결 시점 기준환율")
    sub.add_argument("--label")
    sub.add_argument("--source", help="체결 확인 근거 (필수)")
    sub.add_argument("--note")
    args = ap.parse_args()

    if args.add:
        return cmd_add(args)

    rows = load_ledger()
    if not rows:
        print("원장이 비었습니다 — data/app/trades.jsonl", file=sys.stderr)
        return 1

    pf = load_portfolio()
    fx_now = args.fx or current_fx()
    pos = replay(rows)
    book = portfolio_positions(pf)
    rec = reconcile(pos, book)
    summ = summary(rows, fx_now)

    if args.json:
        print(json.dumps({
            "as_of": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST"),
            "fx_used": fx_now,
            "positions": [pos[k] for k in sorted(pos)],
            "reconcile": rec,
            "reconcile_ok": all(r["status"] != "diff" for r in rec),
            "summary": summ,
        }, ensure_ascii=False, indent=1))
        return 0 if all(r["status"] != "diff" for r in rec) else 1

    if args.ticker:
        tk = args.ticker
        hits = [r for r in rows if r["ticker"].upper() == tk.upper() or (r.get("label") or "") == tk]
        if not hits:
            print(f"'{tk}' 체결 기록 없음")
            return 1
        print(f"── {hits[0].get('label')} ({hits[0]['ticker']}) 체결 이력 {len(hits)}건 ──")
        for r in hits:
            mark = {"opening": "기초", "buy": "매수", "sell": "매도"}[r["side"]]
            print(f"  {r['date']} {mark} {r['shares']:>12,.6f}주 @ {r['price']:>12,.2f} {r['currency']}"
                  f"{'  (derived)' if r.get('derived') else ''}")
            if r.get("note"):
                print(f"          {r['note']}")
        p = pos.get(hits[0]["ticker"])
        if p:
            print(f"  → 현재 {p['shares']:,.6f}주 · 평단 {p['avg_cost']:,.2f} · 실현 {p['realized']:+,.2f} {p['currency']}")
        return 0

    if args.realized:
        det = summ["sells_detail"]
        print(f"── 실현손익 {len(det)}건 (매도 확정분) ──")
        for d in det:
            est = " ~추정환율" if d["fx_estimated"] else ""
            print(f"  {d['date']} {d['label']:<8} {d['shares']:>10,.6f}주 @{d['price']:>10,.2f} "
                  f"원가 {d['cost_basis']:>10,.2f} → {d['realized']:>+9,.2f} {d['currency']} "
                  f"({d['return_pct']:+.1f}%) = {d['realized_krw']:>+10,.0f}원{est}")
        print(f"  {'':-<100}")
        print(f"  누계 실현손익 {summ['realized_krw']:+,}원 "
              f"(USD {summ['realized_usd']:+,.2f} · KRW {summ['realized_krw_only']:+,}) · "
              f"승률 {summ['win_rate']}% ({len([d for d in det if d['realized']>0])}/{len(det)})")
        if summ["fx_estimated"]:
            print(f"  ⚠️ 일부 매도는 체결 시점 환율이 원장에 없어 현재 환율({fx_now:,.1f})로 환산 — 추정치")
        return 0

    # 기본: 포지션 재생 + 대사 요약
    print(f"── 체결 원장 재생 ({summ['fills']}건 체결 · 매수 {summ['buys']}·매도 {summ['sells']}) ──")
    for tk in sorted(pos, key=lambda k: (-pos[k]["shares"] * (1 if pos[k]["currency"] == "USD" else 0.001))):
        p = pos[tk]
        if p["shares"] == 0:
            print(f"  {p['label']:<10} 전량매도 · 실현 {p['realized']:+,.2f} {p['currency']}")
        else:
            print(f"  {p['label']:<10} {p['shares']:>12,.6f}주 · 평단 {p['avg_cost']:>12,.2f} {p['currency']}"
                  + (f" · 실현 {p['realized']:+,.2f}" if p["realized"] else ""))
    print(f"\n  누계 실현손익 {summ['realized_krw']:+,}원 · 승률 {summ['win_rate']}%")

    if args.reconcile or True:
        bad = [r for r in rec if r["status"] == "diff"]
        print(f"\n── portfolio.json 대사 ── ({len(rec)}종목)")
        for r in rec:
            icon = {"ok": "✅", "closed": "⚪", "diff": "❌"}[r["status"]]
            print(f"  {icon} {r['label']:<10} {r['detail']}")
        if bad:
            print(f"\n❌ 대사 실패 {len(bad)}건 — 원장 기입 누락이거나 장부가 틀렸다. 둘 중 하나를 고칠 것.")
            return 1 if args.reconcile else 0
        print("\n✅ 원장 재생 = portfolio.json (전 종목 일치)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
