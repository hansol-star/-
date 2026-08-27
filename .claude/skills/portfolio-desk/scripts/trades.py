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

SIDES = ("opening", "buy", "sell", "closed")
# "closed" [8/23] = 원장 시작(6/13) 이전에 이미 청산된 포지션. 토스 **실현손익 화면**이 날짜·종목별
#   확정 손익만 주고 체결 주수·단가는 안 주므로, 체결(buy/sell)로 위장하지 않고 별도 종류로 둔다.
#   → 포지션 재생에는 들어가지 않고(이미 0), 실현손익 누계에만 더해진다.
DESK_START = "2026-06-13"   # 이 날짜 이전 = 데스크 착수 전 실적(우리 판단의 성과가 아니다)


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

        if r["side"] == "closed":
            # 이미 청산된 포지션 — 수량·평단에 영향 없음. 실현손익만 누적.
            g = float(r.get("realized") or 0)
            p["realized"] += g
            p["closed_count"] = p.get("closed_count", 0) + 1
            fx = r.get("fx_rate")
            p["realized_krw"] += g * float(fx) if (p["currency"] == "USD" and fx) else (
                g if p["currency"] != "USD" else 0)
            continue

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
        if r["side"] == "closed":
            cur = r.get("currency", "KRW")
            rate = float(r.get("fx_rate") or (1.0 if cur != "USD" else fx_now))
            g = float(r.get("realized") or 0)
            out.append({
                "date": r.get("date"), "ticker": tk, "label": r.get("label") or tk,
                "shares": None, "price": None, "currency": cur,
                "cost_basis": r.get("cost_basis_total"), "realized": round(g, 2),
                "realized_krw": round(g * rate), "return_pct": r.get("return_pct"),
                "fx_rate": round(rate, 2), "fx_estimated": cur == "USD",
                "fx_source": r.get("fx_source") or "market_close", "era": "pre",
                "source": r.get("source", ""), "note": r.get("note", ""),
            })
            continue
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
        # 우선순위: ①원장 기록(토스 기준환율) ②체결일 시장 종가 ③현재 환율(최후)
        if cur != "USD":
            rate, src = 1.0, "krw"
        elif fx:
            rate, src = float(fx), r.get("fx_source") or "toss"
        else:
            got, gsrc = fx_on(r.get("date") or "")
            rate, src = (got, gsrc) if got else (fx_now, "current")
        est = cur == "USD" and src != "toss"
        out.append({
            "date": r.get("date"), "ticker": tk, "label": r.get("label") or tk,
            "shares": sh, "price": float(r.get("price") or 0), "currency": cur,
            "cost_basis": p["avg"], "realized": gain, "realized_krw": gain * rate,
            "return_pct": (gain / (sh * p["avg"]) * 100) if p["avg"] and sh else None,
            "fx_rate": round(rate, 2), "fx_estimated": est, "fx_source": src, "era": "desk",
            "source": r.get("source", ""), "note": r.get("note", ""),
        })
    return out


def fx_on(date: str) -> tuple[float, str] | tuple[None, None]:
    """체결일의 원/달러 종가. (rate, source) — 없으면 (None, None).

    왜 있나 [8/23]: 초판은 체결 시점 환율이 원장에 없으면 **오늘 환율**로 환산했다.
    6/24 매도를 두 달 뒤 환율로 재는 셈이라, 원/달러가 그 사이 1,554→1,384로 11% 움직인
    구간에서는 실현손익 원화가 통째로 왜곡된다. 로컬 일봉 캐시(data/history/KRW_X.csv,
    history_backfill.py가 관리)에서 **그날 종가**를 읽고, 주말·휴장이면 직전 영업일로 내려간다.

    ⚠️ 이건 **시장 종가**이지 토스가 실제 적용한 환율이 아니다(스프레드·체결시각 차이).
       토스 스크린샷에 기준환율이 찍힌 건은 원장의 fx_rate가 우선이고 이 함수는 안 쓴다.
    """
    path = os.path.join(REPO, "data", "history", "KRW_X.csv")
    if not os.path.exists(path):
        return (None, None)
    try:
        rows = {}
        with open(path, encoding="utf-8") as f:
            next(f, None)
            for ln in f:
                d, _, c = ln.strip().partition(",")
                if c:
                    rows[d] = float(c)
    except (OSError, ValueError):
        return (None, None)
    if not rows:
        return (None, None)
    # 그날이 없으면 직전 영업일 (주말·공휴일 체결 표기 대응)
    cands = [d for d in rows if d <= date]
    if not cands:
        return (None, None)
    d = max(cands)
    return (rows[d], "market_close" if d == date else f"market_close({d})")


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


def _fx_coverage(rows: list[dict]) -> dict:
    """미국주 취득원가 중 **체결 환율을 우리가 아는 비중**.

    왜 재는가: 환손익 분해(fx_exposure)의 F₀는 지금 `us_avg_fx_cost`(토스 실손익 역산 **추정치**)다.
    원장에 실제 체결환율이 쌓일수록 그 추정을 실측으로 대체할 수 있는데, **얼마나 왔는지**를
    숫자로 안 보면 "곧 정밀해진다"는 말만 반복하게 된다.
    ⚠️ 기초 잔고(opening)는 6/13 이전 매입이라 취득환율을 모른다 — **그날 종가로 채우지 않는다**
       (그건 데이터가 아니라 가짜 정밀도다). 그래서 분모엔 들어가고 분자엔 안 들어간다.
    """
    known = total = 0.0
    for r in rows:
        if r.get("currency") != "USD" or r.get("side") not in ("opening", "buy"):
            continue
        amt = _amount(r)
        total += amt
        if r.get("side") == "buy" and r.get("fx_rate"):
            known += amt
    wsum = sum(_amount(r) * float(r["fx_rate"]) for r in rows
               if r.get("currency") == "USD" and r.get("side") == "buy" and r.get("fx_rate"))
    return {
        "known_pct": round(known / total * 100, 1) if total else 0.0,
        "known_usd": round(known, 2), "total_usd": round(total, 2),
        "weighted_fx": round(wsum / known, 1) if known else None,
        "note": "기초 잔고는 취득환율 미상(원장 시작 이전) — 분모에만 포함. 체결이 쌓일수록 known_pct가 오른다.",
    }


def _payoff(detail: list[dict]) -> dict:
    """승률로는 안 보이는 축 — 손익비·기대값 (측정 전용).

    ■ 왜 신설했나 [8/24 — 외부 트레이딩 리포 10개 검토 중 발견]
       우리 검증기 10종(score_calls·target_score·drawdown_history·ma_test·signal_score·
       rule_tracker·multiple_backtest·ratchet_test·capitulation_validate·trades)은
       **전부 승률·중앙값만** 쟀다. 손익비·기대값을 내는 스크립트가 83개 중 **0개**였다.
       그런데 원장이 실측한 우리 실패 유형은 승률이 아니라 **손익비**다:
         · 미국주 40건 = 승률 **72.5%**인데 손익비 **0.81** (평균이익 +14.9% vs 평균손실 -18.4%)
           → *자주 이기지만 작게 이기고 크게 진다* (처분효과 — 옳은 건 빨리 팔고 내린 건 붙든다)
         · 국내주 6건 = 승률 33.3%인데 손익비 3.05 (드물게 이기지만 크게 이긴다)
       **승률만 보면 "72%면 잘하는 중"으로 읽혀 이 병이 안 보인다.** 8/23에 이 숫자를 손으로
       계산해 CLAUDE.md 산문에만 적어뒀는데, 산문에 있는 지표는 다음 세션에 갱신되지 않는다
       (8/2 *"오더북에 들어간 것만 집행된다"* 의 지표판) → 원장이 매번 자동 산출하게 옮긴다.

    ⚠️ **측정 전용 — 별점·트랜치·안전핀 어떤 룰도 바꾸지 않는다.**
    ⚠️ 표본이 작으면(특히 데스크 이후 6건) 손익비는 한 건에 크게 흔들린다 — n을 항상 같이 읽을 것.
    """
    rs = [d for d in detail if d.get("return_pct") is not None]
    if not rs:
        return {"n": 0}
    w = [d["return_pct"] for d in rs if d["return_pct"] > 0]
    l = [d["return_pct"] for d in rs if d["return_pct"] <= 0]
    avg_w = (sum(w) / len(w)) if w else 0.0
    avg_l = (sum(l) / len(l)) if l else 0.0
    # 손익비 = 평균이익 / |평균손실|. 손실 0건이면 정의되지 않는다(무한대로 쓰지 않음).
    payoff = round(avg_w / abs(avg_l), 2) if l and avg_l else None
    return {
        "n": len(rs),
        "win_rate": round(len(w) / len(rs) * 100, 1),
        "avg_win_pct": round(avg_w, 1),
        "avg_loss_pct": round(avg_l, 1),
        "payoff_ratio": payoff,
        # 기대값 = 승률·평균이익 + 패률·평균손실 (건당 기대 수익률 %)
        "expectancy_pct": round(len(w) / len(rs) * avg_w + len(l) / len(rs) * avg_l, 2),
    }


def _era_split(detail: list[dict]) -> dict:
    """데스크 착수(6/13) 전후로 실현손익을 가른다.

    왜 가르나: 합쳐 놓으면 **우리 판단의 성과와 그 이전 성과가 섞인다.** 데스크가 만든 결과만
    따로 봐야 자기 채점이 성립하고, 그 전 실적은 '출발선'으로만 쓴다.
    """
    out = {}
    for k, sel in (("pre", lambda d: d.get("era") == "pre"), ("desk", lambda d: d.get("era") != "pre")):
        rs = [d for d in detail if sel(d)]
        wins = [d for d in rs if d["realized"] > 0]
        out[k] = {
            "n": len(rs), "wins": len(wins),
            "win_rate": round(len(wins) / len(rs) * 100, 1) if rs else None,
            "realized_krw": round(sum(d["realized_krw"] for d in rs)),
            "realized_usd": round(sum(d["realized"] for d in rs if d["currency"] == "USD"), 2),
            "realized_krw_only": round(sum(d["realized"] for d in rs if d["currency"] == "KRW")),
            # 통화별로 갈라 본다 — 손익비가 미국주 0.81 vs 국내주 3.05로 **정반대**라 합치면 병이 사라진다.
            "payoff": _payoff(rs),
            "payoff_usd": _payoff([d for d in rs if d["currency"] == "USD"]),
            "payoff_krw": _payoff([d for d in rs if d["currency"] == "KRW"]),
        }
    return out


def summary(rows: list[dict], fx_now: float) -> dict:
    """build_app_data가 소비할 요약 — 실현손익 누계 + 최근 체결."""
    detail = realized_krw_detail(rows, fx_now)
    fills = [r for r in rows if r.get("side") in ("buy", "sell")]
    closed = [r for r in rows if r.get("side") == "closed"]
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
        "closed_pre_desk": len(closed),
        "coverage": {
            # 토스 실현손익 화면 조회범위는 2024-07-08~2026-08-23인데, 받은 스크린샷은 그 일부만 덮는다.
            # 누계를 '전체 계좌 실적'으로 읽으면 틀린다 → 범위를 데이터에 박아 화면까지 따라가게 한다.
            "closed_from": min([r["date"] for r in closed], default=None),
            "closed_to": max([r["date"] for r in closed], default=None),
            "toss_range": "2024-07-08 ~ 2026-08-23",
            # [8/23 2차 수령] 스크롤 끝까지 확인 — 마지막 항목이 "25년 1월 24일"로 연도 표기가 붙어 있고
            # 그 아래는 피드백 섹션(리스트 끝)이다. 즉 조회범위 24.7.8~26.8.23에서 실현이 발생한 건은
            # 이게 전부이며, 2025-01-24 ~ 2026-01-19 사이에는 청산이 없었다.
            "complete": True,
            "gaps": [],
            "note": "토스 조회범위 전체를 덮는다(리스트 끝까지 확인). 단 **실현손익만** — 현재 보유분의 취득일·취득환율은 여전히 미상.",
        },
        "eras": _era_split(detail),
        "buys": sum(1 for r in fills if r["side"] == "buy"),
        "sells": len(detail),
        "realized_krw": round(realized_krw),
        "realized_usd": round(sum(d["realized"] for d in detail if d["currency"] == "USD"), 2),
        "realized_krw_only": round(sum(d["realized"] for d in detail if d["currency"] == "KRW")),
        "win_rate": round(len(wins) / len(detail) * 100, 1) if detail else None,
        "payoff": _payoff(detail),
        "fx_estimated": any(d["fx_estimated"] for d in detail),
        "fx_sources": sorted({d.get("fx_source") for d in detail if d["currency"] == "USD"}),
        "fx_cost_coverage": _fx_coverage(rows),
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
            # closed = 데스크 이전 청산분(토스 실현손익 화면) — 주수·단가가 애초에 없다.
            mark = {"opening": "기초", "buy": "매수", "sell": "매도", "closed": "청산"}.get(r["side"], r["side"])
            if r.get("shares") is None or r.get("price") is None:
                rp = f" ({r['return_pct']:+.1f}%)" if r.get("return_pct") is not None else ""
                real = f" 실현 {r['realized']:>+10,.2f}" if r.get("realized") is not None else ""
                print(f"  {r['date']} {mark} {'(주수·단가 미기록)':>22} {r['currency']}{real}{rp}"
                      f"{'  (derived)' if r.get('derived') else ''}")
            else:
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
            src = d.get("fx_source") or ""
            est = "" if src in ("toss", "krw") else (
                f" ~체결일종가 {d['fx_rate']:,.0f}" if src.startswith("market_close") else
                f" ~현재환율 {d['fx_rate']:,.0f}")
            # 데스크 이전 청산분(closed)은 주수·단가가 화면에 없다 — 없는 칸을 지어내지 않는다.
            qty = f"{d['shares']:>10,.6f}주 @{d['price']:>10,.2f}" if d.get("shares") else f"{'(주수·단가 미기록)':>22}"
            cb = f"{d['cost_basis']:>10,.2f}" if d.get("cost_basis") else f"{'—':>10}"
            rp = f"({d['return_pct']:+.1f}%)" if d.get("return_pct") is not None else "        "
            tag = "  ·이전" if d.get("era") == "pre" else ""
            print(f"  {d['date']} {d['label']:<10} {qty} 원가 {cb} → {d['realized']:>+9,.2f} {d['currency']} "
                  f"{rp} = {d['realized_krw']:>+10,.0f}원{est}{tag}")
        print(f"  {'':-<100}")
        e = summ["eras"]
        print(f"  {'':-<100}")
        print(f"  데스크 이전({e['pre']['n']}건·승률 {e['pre']['win_rate']}%) {e['pre']['realized_krw']:+,}원"
              f"   |   데스크 이후({e['desk']['n']}건·승률 {e['desk']['win_rate']}%) {e['desk']['realized_krw']:+,}원")
        print(f"  누계 실현손익 {summ['realized_krw']:+,}원 "
              f"(USD {summ['realized_usd']:+,.2f} · KRW {summ['realized_krw_only']:+,}) · "
              f"승률 {summ['win_rate']}% ({len([d for d in det if d['realized']>0])}/{len(det)})")
        po = summ.get("payoff") or {}
        if po.get("payoff_ratio") is not None:
            print(f"  손익비 {po['payoff_ratio']} (평균이익 {po['avg_win_pct']:+.1f}% / 평균손실 "
                  f"{po['avg_loss_pct']:+.1f}%) · 건당 기대값 {po['expectancy_pct']:+.2f}%")
            for era_k, era_ko in (("pre", "이전"), ("desk", "이후")):
                for cur_k, cur_ko in (("payoff_usd", "미국주"), ("payoff_krw", "국내주")):
                    q = (e.get(era_k) or {}).get(cur_k) or {}
                    if q.get("n") and q.get("payoff_ratio") is not None:
                        print(f"    데스크 {era_ko}·{cur_ko} n={q['n']} 승률 {q['win_rate']}% · "
                              f"손익비 {q['payoff_ratio']} ({q['avg_win_pct']:+.1f}% / {q['avg_loss_pct']:+.1f}%)"
                              + ("   ⚠️표본 극소" if q["n"] < 10 else ""))
            print("  ⚠️ 손익비는 측정 전용 — 룰 판정에 쓰지 않는다. 표본 수와 함께 읽을 것.")
        srcs = {d.get("fx_source") for d in det if d["currency"] == "USD"}
        if srcs - {"toss"}:
            print(f"  ⚠️ 환율 출처 — toss=스크린샷 기준환율(정확) / 체결일종가=시장 종가(스프레드 미반영) / "
                  f"현재환율=최후 폴백. 현재 원장: {', '.join(sorted(s or '?' for s in srcs))}")
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
