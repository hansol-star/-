#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tax_tracker.py — 해외주식 양도소득세 트래커 + 연말 이익 실현(gain harvesting) 계획

왜 있나 [9/30 신설 — TASK K, 정훈 승인]
──────────────────────────────────────
정훈은 이 시스템에 월 약 3만원(연 36만원 ≈ 계좌 812만원의 4.4%)을 낸다. 종목 선택으로
연 4.4% 알파를 매년 내는 건 현실적인 목표가 아니다(d222 실측: 데스크 매매 기여 -2.83%p).
반면 **세금은 확정된 돈**이다. 이 도구는 우리가 이미 가진 체결 원장(trades.jsonl)을
**세법 방식 그대로** 다시 계산해 두 가지를 낸다:

  ① 올해 국외주식 양도차익(원화) — 기본공제 250만원 중 얼마를 썼고 얼마가 남았나
  ② 남은 공제 한도만큼 '이익 실현 → 즉시 재매수'하면 취득가가 비과세로 올라간다
     (한국엔 미국식 워시세일 규정이 없다 — 근거는 docs/research/tax_plan_2026-09-30.md)

우리 원장(trades.py)은 **달러 이동평균**으로 손익을 잰다. 세법은 다르다:

  · 과세 단위 = 달력연도 1년, 전 국외주식 손익 **통산**(국내주식과는 통산 불가 · 이월공제 없음)
  · 기본공제 250만원 → 초과분에 22%(양도세 20% + 지방소득세 2%)
  · 원화 환산 = 취득·양도 **각각의 결제일** 기준환율(국세청·증권사 신고 안내 — 조문 번호는 미확인)
  · 귀속 연도 = 결제일. 미국은 2024-05-28부터 T+1
  · 수수료·제세금은 필요경비로 공제
  · 취득가액 = 선입선출(시행령 §162⑤ 원칙) 또는 증권사가 계속 적용한 이동평균(국세청 허용)
    → 증권사마다 다르고(미래에셋·키움·메리츠=선입선출 / NH·KB=선택, 비즈워치 26.4.14)
      토스는 **1차 출처 미확인**이라 **둘 다** 계산하고, 한도 판정엔 불리한 쪽(더 큰 이익)을 쓴다.
  · 국내 상장주식 소액주주 = 양도세 없음(증권거래세만) → 통산 대상에서 뺀다

그래서 달러로 +인 종목이 원화로는 −일 수 있다(1,460원에 사서 1,355원인 지금).
이 차이를 모르고 연말에 '이익 종목'을 팔면 오히려 손실을 확정해 **버리게** 된다
(양도차손은 이월되지 않는다).

⚠️ 측정·계획 전용 — 주문 없음. 토스 주문 API를 부르지 않는다. 집행은 정훈.
⚠️ 환율은 Yahoo KRW=X 종가(결제일 또는 직전 영업일) 근사다 — 서울외국환중개 매매기준율과
   통상 ±0.5% 이내 차이. 한도 계획에 버퍼(기본 10%)를 두는 이유다.

왜 trades.py의 원화 실현손익과 다른가: trades.py는 **달러 손익 × 매도일 환율**이다(매수 수수료도
원가에 안 넣는다). 세법은 매수 원가를 **매수 결제일 환율**로 따로 환산한다 → 비싼 환율(1,450~1,500)에
사서 싼 환율(1,360)에 판 올해는 세법 기준 이익이 더 작게 나온다. 신고·한도 판정은 이 도구 숫자를 쓴다.

사용법:
  python tax_tracker.py                  # 올해(KST) 실현·미실현·하베스트 계획
  python tax_tracker.py --year 2025      # 다른 귀속 연도
  python tax_tracker.py --sells          # 올해 매도 건별 상세(결제일·환율)
  python tax_tracker.py --fx 1358        # 현재 환율 직접 지정
  python tax_tracker.py --pension        # 연금저축·IRP 세액공제 가치표(납입액×공제율 vs 시스템 비용)
  python tax_tracker.py --json           # 기계 출력
  python tax_tracker.py --save           # data/research/tax_tracker_{날짜}.json 저장
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import trades  # noqa: E402  — 원장 파싱·환율 캐시는 한 곳에서만 (재파싱 금지)

REPO = trades.REPO
HIST_DIR = os.path.join(REPO, "data", "history")
OUT_DIR = os.path.join(REPO, "data", "research")

TAX_RATE = 0.22                 # 양도소득세 20% + 지방소득세 2%
BASIC_DEDUCTION = 2_500_000     # 양도소득 기본공제(주식 그룹, 연 1회)
T1_START = dt.date(2024, 5, 28)  # 미국 결제주기 T+2 → T+1 전환일
QTY_TOL = 1e-6
KST = dt.timezone(dt.timedelta(hours=9))
SYSTEM_COST_KRW_YR = 360_000    # 정훈이 이 시스템에 내는 비용(월 3만원) — '제 값을 하나'의 기준선

# 연금계좌 세액공제(2026 현행 — 2026 세제개편안에서 변경 확인 안 됨, tax_plan 문서 참조)
PENSION_CAP = 6_000_000         # 연금저축 단독 세액공제 대상 한도
PENSION_IRP_CAP = 9_000_000     # 연금저축+IRP 합산 한도
CREDIT_HIGH = 0.165             # 총급여 5,500만원 이하(종합소득 4,500만원 이하), 지방세 포함
CREDIT_LOW = 0.132              # 그 초과
EARLY_WITHDRAW_TAX = 0.165      # 55세 전·연금 외 수령 시 기타소득세(공제받은 원금+운용수익에 부과)

# NYSE 휴장일 — 결제일(T+1) 계산용. 목록 밖 연도는 주말만 제외한다(연말 판정엔 충분).
NYSE_HOLIDAYS = {
    # 2024
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27", "2024-06-19",
    "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
    # 2025 (1/9 카터 전 대통령 국가 애도일 휴장 포함)
    "2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
    "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
    # 2026
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19",
    "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    # 2027
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18",
    "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24",
}

_TS = re.compile(r"(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?")


# ─────────────────────────── 날짜: 체결 → 미국 거래일 → 결제일 ───────────────────────────
def is_bday(d: dt.date) -> bool:
    return d.weekday() < 5 and d.isoformat() not in NYSE_HOLIDAYS


def next_bday(d: dt.date) -> dt.date:
    d += dt.timedelta(days=1)
    while not is_bday(d):
        d += dt.timedelta(days=1)
    return d


def _nth_sunday(year: int, month: int, n: int) -> dt.date:
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(6 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _et_offset(utc: dt.datetime) -> dt.timedelta:
    """미국 동부 UTC 오프셋 — 3월 둘째 일요일 07:00Z ~ 11월 첫째 일요일 06:00Z는 EDT(-4)."""
    y = utc.year
    start = dt.datetime.combine(_nth_sunday(y, 3, 2), dt.time(7), tzinfo=dt.timezone.utc)
    end = dt.datetime.combine(_nth_sunday(y, 11, 1), dt.time(6), tzinfo=dt.timezone.utc)
    return dt.timedelta(hours=-4 if start <= utc < end else -5)


def fill_time_kst(r: dict) -> tuple[dt.datetime, bool]:
    """체결 시각(KST). filled_at → source/note 속 타임스탬프 → (없으면) 그날 22:30 가정.

    반환 (시각, 가정여부). 22:30 가정 = 원장 체결의 대다수가 미국 개장 직후(KST 22~23시)라서다.
    """
    fa = r.get("filled_at")
    if fa:
        try:
            t = dt.datetime.fromisoformat(fa)
            return (t if t.tzinfo else t.replace(tzinfo=KST)).astimezone(KST), False
        except ValueError:
            pass
    m = _TS.search(f"{r.get('source', '')} {r.get('note', '')}")
    if m:
        d, hh, mm, ss = m.groups()
        return dt.datetime.fromisoformat(f"{d}T{hh}:{mm}:{ss or '00'}").replace(tzinfo=KST), False
    return dt.datetime.fromisoformat(f"{r.get('date')}T22:30:00").replace(tzinfo=KST), True


def us_trade_date(kst: dt.datetime) -> dt.date:
    """KST 체결 시각 → 미국 거래일(ET).

    ET 04:00~20:00(프리·정규·애프터) = 그날. ET 20:00~익일 04:00 = 야간세션(토스 '주간거래'가
    여기에 해당) → **다음 거래일** 귀속. 연말 판정에서 이 차이가 하루를 가른다.
    """
    utc = kst.astimezone(dt.timezone.utc)
    et = utc + _et_offset(utc)
    d = et.date()
    if et.hour >= 20:
        return next_bday(d)
    return d if is_bday(d) else next_bday(d)


def settle_date(trade: dt.date) -> dt.date:
    d = next_bday(trade)
    return d if trade >= T1_START else next_bday(d)


def year_end_deadline(year: int) -> dict:
    """그 해 귀속되는 마지막 미국 거래일(결제일 ≤ 12/31)과 권장일(하루 버퍼)."""
    d = dt.date(year, 12, 31)
    while not (is_bday(d) and settle_date(d) <= dt.date(year, 12, 31)):
        d -= dt.timedelta(days=1)
    rec = d - dt.timedelta(days=1)
    while not is_bday(rec):
        rec -= dt.timedelta(days=1)

    def kst_window(day: dt.date) -> str:
        # 정규장 09:30~16:00 ET → KST
        o = dt.datetime.combine(day, dt.time(9, 30))
        off = _et_offset(o.replace(tzinfo=dt.timezone.utc) + dt.timedelta(hours=14))
        o_kst = (o - off).replace(tzinfo=dt.timezone.utc).astimezone(KST)
        c_kst = o_kst + dt.timedelta(hours=6, minutes=30)
        return f"KST {o_kst:%m/%d %H:%M} ~ {c_kst:%m/%d %H:%M}"

    wd = "월화수목금토일"
    return {
        "last_trade_date_et": d.isoformat(), "last_weekday": wd[d.weekday()],
        "last_settle": settle_date(d).isoformat(), "last_session_kst": kst_window(d),
        "recommended_trade_date_et": rec.isoformat(), "recommended_weekday": wd[rec.weekday()],
        "recommended_session_kst": kst_window(rec),
        "note": "야간세션(토스 '주간거래', ET 20:00~04:00)은 다음 거래일 귀속 — 연말엔 정규장만 쓴다.",
    }


# ─────────────────────────── 환율 ───────────────────────────
def fx_at(date: dt.date, fallback: float | None) -> tuple[float, str]:
    """결제일 기준환율 근사 = KRW=X 종가(그날 또는 직전 영업일). 없으면 원장 환율 → 현재."""
    rate, src = trades.fx_on(date.isoformat())
    if rate:
        return float(rate), src
    if fallback:
        return float(fallback), "ledger"
    return trades.current_fx(), "current"


# ─────────────────────────── 원화 로트 엔진 ───────────────────────────
def build_books(rows: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    """USD 체결을 결제일·결제일환율로 재생 → (종목별 잔여 로트/이동평균, 매도 건별 과세손익, 국내 매도)."""
    ev = []
    for i, r in enumerate(rows):
        kst, assumed = fill_time_kst(r)
        td = us_trade_date(kst) if r.get("currency") == "USD" else dt.date.fromisoformat(r["date"])
        ev.append((td, kst, 0 if r["side"] == "opening" else 1, i, r, assumed))
    ev.sort(key=lambda e: (e[0], e[1], e[2], e[3]))

    books: dict[str, dict] = {}
    sells: list[dict] = []
    domestic: list[dict] = []
    for td, kst, _, _, r, assumed in ev:
        tk = r["ticker"]
        if r.get("currency") != "USD":
            if r["side"] == "sell":
                domestic.append({"date": r["date"], "ticker": tk, "label": r.get("label") or tk})
            continue
        b = books.setdefault(tk, {"ticker": tk, "label": r.get("label") or tk, "lots": [],
                                  "ma_sh": 0.0, "ma_krw": 0.0, "ma_usd": 0.0})
        if r.get("label"):
            b["label"] = r["label"]
        sd = settle_date(td)
        sh = float(r.get("shares") or 0)
        amt = trades._amount(r)
        cost_x = float(r.get("fee") or 0) + float(r.get("tax") or 0)
        rate, src = fx_at(sd, r.get("fx_rate"))
        est = assumed or src not in ("market_close",) and not src.startswith("market_close")

        if r["side"] == "closed":   # 원장 이전 청산분(현 원장엔 없음) — 손익만 알고 주수·단가는 없다
            g = float(r.get("realized") or 0) * rate
            sells.append({"ticker": tk, "label": b["label"], "trade_date": td.isoformat(),
                          "settle": sd.isoformat(), "shares": None, "proceeds_krw": None,
                          "gain_fifo": g, "gain_ma": g, "gain_usd": float(r.get("realized") or 0),
                          "fx": rate, "fx_src": src, "estimated": True, "note": "closed(손익만)"})
            continue

        if r["side"] in ("opening", "buy"):
            krw = (amt + cost_x) * rate
            b["lots"].append({"shares": sh, "krw": krw, "usd": amt + cost_x,
                              "settle": sd.isoformat(), "est": bool(est or r["side"] == "opening")})
            b["ma_sh"] += sh
            b["ma_krw"] += krw
            b["ma_usd"] += amt + cost_x
            continue

        # sell
        proceeds = amt * rate
        expense = cost_x * rate
        need = sh
        cost_fifo = 0.0
        usd_fifo = 0.0
        lot_est = False
        while need > QTY_TOL and b["lots"]:
            lot = b["lots"][0]
            take = min(need, lot["shares"])
            frac = take / lot["shares"] if lot["shares"] else 0
            cost_fifo += lot["krw"] * frac
            usd_fifo += lot["usd"] * frac
            lot_est = lot_est or lot["est"]
            lot["shares"] -= take
            lot["krw"] -= lot["krw"] * frac
            lot["usd"] -= lot["usd"] * frac
            need -= take
            if lot["shares"] <= QTY_TOL:
                b["lots"].pop(0)
        short = need > QTY_TOL
        if b["ma_sh"] > QTY_TOL:
            f = min(1.0, sh / b["ma_sh"])
            cost_ma, usd_ma = b["ma_krw"] * f, b["ma_usd"] * f
            b["ma_krw"] -= cost_ma
            b["ma_usd"] -= usd_ma
            b["ma_sh"] = max(0.0, b["ma_sh"] - sh)
            if b["ma_sh"] <= QTY_TOL:
                b["ma_sh"] = b["ma_krw"] = b["ma_usd"] = 0.0
        else:
            cost_ma = usd_ma = 0.0
        sells.append({
            "ticker": tk, "label": b["label"], "trade_date": td.isoformat(), "settle": sd.isoformat(),
            "shares": sh, "price": float(r.get("price") or 0), "proceeds_krw": proceeds,
            "expense_krw": expense, "cost_fifo_krw": cost_fifo, "cost_ma_krw": cost_ma,
            "gain_fifo": proceeds - cost_fifo - expense, "gain_ma": proceeds - cost_ma - expense,
            "gain_usd": amt - usd_ma - cost_x,  # 참고: 달러 기준(환율 효과 제외)
            "fx": rate, "fx_src": src, "estimated": bool(est or lot_est),
            "note": "⚠️로트 부족(원장 누락 의심)" if short else "",
        })
    return books, sells, domestic


# ─────────────────────────── 집계 ───────────────────────────
def year_summary(sells: list[dict], year: int) -> dict:
    ys = [s for s in sells if s["settle"][:4] == str(year)]
    by: dict[str, dict] = {}
    for s in ys:
        t = by.setdefault(s["ticker"], {"ticker": s["ticker"], "label": s["label"], "n": 0,
                                        "gain_fifo": 0.0, "gain_ma": 0.0, "gain_usd": 0.0,
                                        "proceeds_krw": 0.0, "estimated": False})
        t["n"] += 1
        t["gain_fifo"] += s["gain_fifo"]
        t["gain_ma"] += s["gain_ma"]
        t["gain_usd"] += s["gain_usd"]
        t["proceeds_krw"] += s.get("proceeds_krw") or 0
        t["estimated"] = t["estimated"] or s["estimated"]
    net_f = sum(s["gain_fifo"] for s in ys)
    net_m = sum(s["gain_ma"] for s in ys)
    worst = max(net_f, net_m)     # 한도 판정은 불리한(이익이 큰) 쪽으로

    def tax_of(net: float) -> float:
        return max(0.0, net - BASIC_DEDUCTION) * TAX_RATE

    return {
        "year": year, "n_sells": len(ys),
        "by_ticker": sorted(by.values(), key=lambda t: -max(t["gain_fifo"], t["gain_ma"])),
        "net_fifo": net_f, "net_ma": net_m, "net_conservative": worst,
        "remaining_room": max(0.0, BASIC_DEDUCTION - worst),
        "tax_fifo": tax_of(net_f), "tax_ma": tax_of(net_m), "tax_conservative": tax_of(worst),
        "estimated_rows": sum(1 for s in ys if s["estimated"]),
    }


def last_close(ticker: str) -> tuple[float | None, str | None]:
    path = os.path.join(HIST_DIR, f"{ticker.replace('^', '_')}.csv")
    if not os.path.exists(path):
        return None, None
    last = None
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln and not ln.startswith("date"):
                last = ln
    if not last:
        return None, None
    d, _, c = last.partition(",")
    try:
        return float(c.split(",")[0]), d
    except ValueError:
        return None, None


def fee_model(rows: list[dict], n: int = 30) -> dict:
    """왕복 비용을 **원장 실측**에서 추정 — 최근 USD 체결 n건의 수수료율 중앙값 + 매도 제세금."""
    usd = [r for r in rows if r.get("currency") == "USD" and r["side"] in ("buy", "sell")
           and trades._amount(r) >= 20]
    usd.sort(key=lambda r: r.get("filled_at") or r.get("date"))
    recent = usd[-n:]

    def med(side: str) -> float:
        xs = [float(r.get("fee") or 0) / trades._amount(r) for r in recent if r["side"] == side]
        return statistics.median(xs) if xs else 0.001

    sell_tax = [float(r.get("tax") or 0) for r in usd if r["side"] == "sell"][-n:]
    return {"buy_rate": med("buy"), "sell_rate": med("sell"),
            "sell_tax_usd_per_order": statistics.median(sell_tax) if sell_tax else 0.01,
            "n": len(recent)}


def unrealized(books: dict, pf: dict, fx_now: float, fees: dict) -> list[dict]:
    out = []
    for h in (pf.get("holdings") or {}).get("us", []):
        tk = h["ticker"]
        b = books.get(tk) or {"lots": [], "ma_sh": 0.0, "ma_krw": 0.0, "ma_usd": 0.0, "label": tk}
        sh_book = float(h.get("shares") or 0)
        sh_lots = sum(l["shares"] for l in b["lots"])
        px, px_date = last_close(tk)
        row = {"ticker": tk, "label": h.get("label") or tk, "shares": sh_book,
               "shares_ledger": round(sh_lots, 6), "reconciled": abs(sh_lots - sh_book) <= 1e-5,
               "price": px, "price_date": px_date}
        if px is None:
            row["error"] = "시세 캐시 없음"
            out.append(row)
            continue
        value_usd = sh_book * px
        sell_exp = (value_usd * fees["sell_rate"] + fees["sell_tax_usd_per_order"]) * fx_now
        value_krw = value_usd * fx_now
        k_fifo = sum(l["krw"] for l in b["lots"])
        u_fifo = sum(l["usd"] for l in b["lots"])
        g_fifo = value_krw - k_fifo - sell_exp
        g_ma = value_krw - b["ma_krw"] - sell_exp
        row.update({
            "value_krw": value_krw, "cost_fifo_krw": k_fifo, "cost_ma_krw": b["ma_krw"],
            "gain_fifo": g_fifo, "gain_ma": g_ma,
            # 원화 손익 = 주가 효과(현재환율로) + 환율 효과(달러원가를 지금 환율로 − 원화원가)
            "price_effect": (value_usd - u_fifo) * fx_now,
            "fx_effect": u_fifo * fx_now - k_fifo,
            "avg_fx_fifo": (k_fifo / u_fifo) if u_fifo else None,
            "est_lots": any(l["est"] for l in b["lots"]),
            "lots": [{"shares": round(l["shares"], 6), "krw_per_share": l["krw"] / l["shares"],
                      "usd_per_share": l["usd"] / l["shares"], "settle": l["settle"]}
                     for l in b["lots"] if l["shares"] > QTY_TOL],
        })
        out.append(row)
    return out


def _fifo_gain_for(row: dict, n: float, fx_now: float, fees: dict) -> float:
    """보유 로트에서 n주를 선입선출로 팔 때의 원화 과세손익(매도비용 차감)."""
    px = row["price"]
    need, cost = n, 0.0
    for l in row["lots"]:
        take = min(need, l["shares"])
        cost += take * l["krw_per_share"]
        need -= take
        if need <= QTY_TOL:
            break
    proceeds = n * px * fx_now
    exp = (n * px * fees["sell_rate"] + fees["sell_tax_usd_per_order"]) * fx_now
    return proceeds - cost - exp


def harvest_plan(unr: list[dict], room: float, fx_now: float, fees: dict,
                 buffer: float, slip_bps: float, max_breakeven: float) -> dict:
    """남은 공제 한도 안에서 '이익 실현 → 즉시 재매수' 후보를 고른다.

    · 한도 판정 = max(선입선출, 이동평균) 이익 (토스 신고 방식 미확인 → 불리한 쪽)
    · 순서 = 원화 이익률(이익/평가액) 높은 순 = 같은 절세 한도를 가장 적은 거래대금으로 채운다
    · 효율 컷 = 왕복비용 ÷ (22% × 실현이익) = 손익분기 확률. 이게 max_breakeven을 넘으면 뺀다
    """
    target = room * (1 - buffer)
    left = target
    plan = []
    rt_rate = fees["buy_rate"] + fees["sell_rate"] + 2 * slip_bps / 10_000
    cands = [u for u in unr if u.get("price") and min(u["gain_fifo"], u["gain_ma"]) > 0]
    cands.sort(key=lambda u: -min(u["gain_fifo"], u["gain_ma"]) / u["value_krw"])
    skipped = []
    for u in cands:
        if left <= 0:
            break
        full_worst = max(u["gain_fifo"], u["gain_ma"])
        if full_worst <= left:
            n = u["shares"]
        else:
            # 이동평균: 주당 이익 일정 / 선입선출: 로트를 따라 걸으며 누적 → 둘 중 작은 주수
            ps_ma = u["gain_ma"] / u["shares"]
            n_ma = left / ps_ma if ps_ma > 0 else u["shares"]
            lo, hi = 0.0, u["shares"]
            for _ in range(60):
                mid = (lo + hi) / 2
                if _fifo_gain_for(u, mid, fx_now, fees) <= left:
                    lo = mid
                else:
                    hi = mid
            n = min(n_ma, lo, u["shares"])
            n = int(n * 1e6) / 1e6          # 토스 소수점 6자리, 내림
        if n <= 0:
            continue
        g_ma = u["gain_ma"] * n / u["shares"]
        g_fifo = _fifo_gain_for(u, n, fx_now, fees) if n < u["shares"] else u["gain_fifo"]
        notional_usd = n * u["price"]
        rt_cost = (notional_usd * rt_rate + fees["sell_tax_usd_per_order"]) * fx_now
        g_low, g_high = min(g_fifo, g_ma), max(g_fifo, g_ma)
        max_saving = TAX_RATE * g_low
        be = rt_cost / max_saving if max_saving > 0 else None
        whole = int(n + QTY_TOL)
        frac = round(n - whole, 6)
        if frac <= QTY_TOL:
            otype = f"{whole}주 지정가 가능"
        elif whole == 0:
            otype = f"{frac:.6f}주 = 소수점 → 시장가 전용"
        else:
            otype = f"{whole}주 지정가 + {frac:.6f}주 시장가(소수점은 지정가 불가)"
        item = {
            "ticker": u["ticker"], "label": u["label"], "shares": n,
            "whole_shares": whole, "fractional_shares": frac,
            "full_position": abs(n - u["shares"]) <= QTY_TOL, "price": u["price"],
            "notional_usd": notional_usd, "notional_krw": notional_usd * fx_now,
            "gain_low": g_low, "gain_high": g_high, "roundtrip_cost_krw": rt_cost,
            "max_future_tax_saved": max_saving, "breakeven_prob": be,
            "order_type": otype,
        }
        if be is None or be > max_breakeven:
            item["skip_reason"] = f"손익분기 확률 {be:.0%} > 기준 {max_breakeven:.0%}" if be else "이익 없음"
            skipped.append(item)
            continue
        plan.append(item)
        left -= g_high
    tot_gain = sum(p["gain_low"] for p in plan)
    tot_cost = sum(p["roundtrip_cost_krw"] for p in plan)
    avail = sum(max(u["gain_fifo"], u["gain_ma"]) for u in cands)
    # 무엇이 하베스트 크기를 막나 — 공제 한도인가, 쌓인 이익 자체가 적은가
    binding = "공제 한도" if avail > target else "미실현 이익 부족(한도가 남는다)"
    return {
        "room": room, "buffer": buffer, "target": target, "roundtrip_rate": rt_rate,
        "unrealized_gain_available": avail, "binding_constraint": binding,
        "room_after_harvest": max(0.0, room - sum(p["gain_high"] for p in plan)),
        "plan": plan, "skipped": skipped,
        "harvest_gain_low": tot_gain, "harvest_gain_high": sum(p["gain_high"] for p in plan),
        "roundtrip_cost_krw": tot_cost, "max_future_tax_saved": TAX_RATE * tot_gain,
        "breakeven_prob": (tot_cost / (TAX_RATE * tot_gain)) if tot_gain > 0 else None,
        "honest_note": ("절세액은 '최대치'다 — 이렇게 올린 취득가가 돈이 되는 건 **나중에 어느 해든 "
                        "국외주식 순이익이 250만원을 넘을 때뿐**이다. 그런 해가 끝내 안 오면 이득 0, "
                        "손실은 왕복비용뿐. 손익분기 확률 = 왕복비용 ÷ 최대절세액."),
    }


def loss_view(unr: list[dict], ys: dict) -> dict:
    """원화 기준 손실 종목 — 올해 순이익이 공제 안이면 손실 실현은 버려진다(이월 없음)."""
    losers = [u for u in unr if u.get("price") and max(u["gain_fifo"], u["gain_ma"]) < 0]
    excess = max(0.0, ys["net_conservative"] - BASIC_DEDUCTION)
    return {
        "losers": [{"ticker": u["ticker"], "label": u["label"], "gain_fifo": u["gain_fifo"],
                    "gain_ma": u["gain_ma"], "fx_effect": u["fx_effect"],
                    "price_effect": u["price_effect"]} for u in losers],
        "excess_over_deduction": excess,
        "advice": ("올해 순이익이 공제 초과 → 손실 종목 매도(즉시 재매수)로 초과분 상쇄 = 확정 절세."
                   if excess > 0 else
                   "올해 순이익이 공제 이내 → 원화 손실 종목을 올해 팔면 손실이 버려지고(이월공제 없음) "
                   "재매수 시 취득가만 낮아진다. 포트 판단상 꼭 팔 게 아니면 손실 실현은 순이익이 250만을 "
                   "넘는 해로 미룬다(세금은 포트 판단보다 후순위)."),
    }


def ledger_view_krw(rows: list[dict], year: int, fx_now: float) -> float | None:
    """trades.py 방식(달러 손익 × 매도일 환율, 매수 수수료 원가 미포함)의 같은 해 원화 실현손익.

    세법 숫자와 나란히 보여 '우리 원장 숫자로 한도를 판정하면 틀린다'를 매번 드러낸다.
    """
    try:
        det = trades.realized_krw_detail(rows, fx_now)
    except Exception:
        return None
    return sum(float(x.get("realized_krw") or 0) for x in det
               if x.get("currency") == "USD" and str(x.get("date") or "")[:4] == str(year))


def pension_table(levels=(1_000_000, 3_000_000, 6_000_000, 9_000_000)) -> dict:
    """연금저축(+IRP) 납입액별 세액공제 — 두 공제율 × 시스템 비용 대비.

    · 600만 초과분은 IRP로만 공제된다(연금저축 단독 한도 600만).
    · 공제액은 **결정세액 한도 안에서만** 돌려받는다 — 세금을 그만큼 안 내면 초과분은 사라진다.
    · 55세 전 연금 외 인출 = 공제받은 원금에 16.5% → 13.2% 구간은 원금 기준 −3.3%p 순손실.
    """
    rows = []
    for c in levels:
        ps = min(c, PENSION_CAP)
        irp = max(0, min(c, PENSION_IRP_CAP) - PENSION_CAP)
        row = {"contribution": c, "pension_savings": ps, "irp_needed": irp}
        for tag, r in (("high", CREDIT_HIGH), ("low", CREDIT_LOW)):
            cr = min(c, PENSION_IRP_CAP) * r
            row[f"credit_{tag}"] = cr
            row[f"cover_{tag}"] = cr / SYSTEM_COST_KRW_YR
            row[f"early_net_{tag}"] = cr - min(c, PENSION_IRP_CAP) * EARLY_WITHDRAW_TAX
        rows.append(row)
    return {
        "rows": rows, "system_cost": SYSTEM_COST_KRW_YR,
        "breakeven_contribution_high": SYSTEM_COST_KRW_YR / CREDIT_HIGH,
        "breakeven_contribution_low": SYSTEM_COST_KRW_YR / CREDIT_LOW,
        "caveats": ["결정세액 한도 내 환급", "근로·종합소득이 있어야 공제",
                    "55세 전 연금 외 인출 시 공제받은 원금+수익에 기타소득세 16.5%",
                    "IRP는 위험자산 70% 한도·중도인출 제한(법정 사유 외 해지)"],
    }


# ─────────────────────────── 출력 ───────────────────────────
def _w(x: float | None) -> str:
    return "—" if x is None else f"{x:+,.0f}"


def render(res: dict, show_sells: bool) -> None:
    ys, dl, hv = res["year_summary"], res["deadline"], res["harvest"]
    print(f"── 해외주식 양도세 트래커 · {res['as_of']} · 환율 {res['fx_now']:,.2f}({res['fx_src']}) ──")
    print("   (측정·계획 전용 — 주문 없음. 원화환산 = 결제일 KRW=X 종가 근사)\n")

    print(f"■ {ys['year']} 귀속 실현(결제일 기준) — 매도 {ys['n_sells']}건 · 추정 포함 {ys['estimated_rows']}건")
    print(f"  {'종목':<10}{'건':>3} {'선입선출(원)':>14} {'이동평균(원)':>14} {'달러기준($)':>12}")
    for t in ys["by_ticker"]:
        print(f"  {t['label'][:10]:<10}{t['n']:>3} {_w(t['gain_fifo']):>14} {_w(t['gain_ma']):>14} "
              f"{t['gain_usd']:>+12,.2f}{'  ~' if t['estimated'] else ''}")
    print(f"  {'합계':<13} {_w(ys['net_fifo']):>14} {_w(ys['net_ma']):>14}")
    print(f"  기본공제 250만 잔여(불리한 쪽 기준) {ys['remaining_room']:,.0f}원 · "
          f"예상세액 선입선출 {ys['tax_fifo']:,.0f} / 이동평균 {ys['tax_ma']:,.0f}원")
    lv_krw = res.get("ledger_view_krw")
    if lv_krw is not None:
        print(f"  (대조: trades.py 방식 = 달러손익×매도일 환율 {lv_krw:+,.0f}원 — 매수 결제일 환율·매수 수수료를"
              f" 안 넣어 세법 숫자와 {lv_krw - ys['net_conservative']:+,.0f}원 다르다. 한도 판정은 위 숫자)")
    if res["domestic_sells_year"]:
        print(f"  (국내 상장주식 매도 {res['domestic_sells_year']}건 = 소액주주 비과세, 통산 제외)")
    if show_sells:
        print("\n  매도 건별:")
        for s in res["sells_year"]:
            print(f"   {s['trade_date']}→결제 {s['settle']} {s['ticker'][:8]:<8} "
                  f"{(s['shares'] or 0):>10.6f}주 환율 {s['fx']:,.1f} "
                  f"FIFO {_w(s['gain_fifo']):>10} MA {_w(s['gain_ma']):>10}"
                  f"{'  ~추정' if s['estimated'] else ''} {s.get('note', '')}")

    print(f"\n■ 미실현(현재 보유 미국 {len(res['unrealized'])}종목, 매도비용 차감 · 환율 {res['fx_now']:,.1f})")
    print(f"  {'종목':<7}{'주수':>11}{'종가':>10} {'평가(원)':>12} {'FIFO손익':>11} {'MA손익':>11}"
          f" {'주가효과':>11} {'환효과':>11} {'평균취득환율':>9}")
    for u in res["unrealized"]:
        if u.get("error"):
            print(f"  {u['ticker']:<7} {u['error']}")
            continue
        warn = "" if u["reconciled"] else f" ⚠️원장 {u['shares_ledger']}주"
        print(f"  {u['ticker']:<7}{u['shares']:>11.6f}{u['price']:>10,.2f} {u['value_krw']:>12,.0f} "
              f"{_w(u['gain_fifo']):>11} {_w(u['gain_ma']):>11} {_w(u['price_effect']):>11} "
              f"{_w(u['fx_effect']):>11} {u['avg_fx_fifo'] or 0:>9,.1f}{warn}")
    tf = sum(u.get("gain_fifo", 0) for u in res["unrealized"])
    tm = sum(u.get("gain_ma", 0) for u in res["unrealized"])
    print(f"  합계 FIFO {_w(tf)} · MA {_w(tm)}원 (가격일 {res['unrealized'][0].get('price_date') if res['unrealized'] else '—'})")

    print(f"\n■ 이익 실현·재매수(gain harvesting) — 한도 {hv['room']:,.0f}원 × (1−버퍼 {hv['buffer']:.0%})"
          f" = 목표 {hv['target']:,.0f}원")
    print(f"  마감: {dl['last_trade_date_et']}({dl['last_weekday']}) 미국 정규장 [{dl['last_session_kst']}]"
          f" → 결제 {dl['last_settle']}")
    print(f"  권장: {dl['recommended_trade_date_et']}({dl['recommended_weekday']}) 정규장 "
          f"[{dl['recommended_session_kst']}] — {dl['note']}")
    if not hv["plan"]:
        print("  → 실행 후보 없음 (원화 기준 이익 종목이 없거나 효율 컷 미달)")
    for p in hv["plan"]:
        print(f"  ✓ {p['ticker']:<6} {p['shares']:.6f}주{'(전량)' if p['full_position'] else ''} "
              f"≈${p['notional_usd']:,.2f} · 실현이익 {p['gain_low']:,.0f}~{p['gain_high']:,.0f}원 · "
              f"왕복비용 {p['roundtrip_cost_krw']:,.0f}원 · 손익분기 {p['breakeven_prob']:.1%} · {p['order_type']}")
    for p in hv["skipped"]:
        print(f"  ✗ {p['ticker']:<6} {p['shares']:.6f}주 이익 {p['gain_low']:,.0f}원 — {p['skip_reason']}")
    if hv["plan"]:
        be = hv["breakeven_prob"]
        print(f"  합계: 실현이익 {hv['harvest_gain_low']:,.0f}원 · 왕복비용 {hv['roundtrip_cost_krw']:,.0f}원 · "
              f"최대 미래절세 {hv['max_future_tax_saved']:,.0f}원 · 손익분기 확률 {be:.1%}")
    print(f"  제약: {hv['binding_constraint']} — 원화 기준 미실현 이익 합 {hv['unrealized_gain_available']:,.0f}원 · "
          f"하베스트 후 잔여 한도 {hv['room_after_harvest']:,.0f}원(12/31에 소멸)")
    print(f"  ⚠️ {hv['honest_note']}")

    lv = res["loss_view"]
    if lv["losers"]:
        names = ", ".join(f"{l['ticker']}({_w(max(l['gain_fifo'], l['gain_ma']))}, 환효과 {_w(l['fx_effect'])})"
                          for l in lv["losers"])
        print(f"\n■ 원화 기준 손실 종목: {names}")
    print(f"  → {lv['advice']}")

    pt = res.get("pension")
    if pt:
        print(f"\n■ 연금저축·IRP 세액공제 가치(연) — 시스템 비용 {pt['system_cost']:,.0f}원 대비")
        print(f"  {'납입':>10} {'연금저축':>10} {'IRP':>10} │ {'16.5% 공제':>11} {'비용대비':>7}"
              f" │ {'13.2% 공제':>11} {'비용대비':>7} │ {'55세 전 해지 순효과(13.2%)':>14}")
        for r in pt["rows"]:
            print(f"  {r['contribution']:>10,} {r['pension_savings']:>10,} {r['irp_needed']:>10,} │ "
                  f"{r['credit_high']:>11,.0f} {r['cover_high']:>6.2f}x │ {r['credit_low']:>11,.0f} "
                  f"{r['cover_low']:>6.2f}x │ {r['early_net_low']:>+14,.0f}")
        print(f"  시스템 비용을 공제로만 메우는 납입액: 16.5% → {pt['breakeven_contribution_high']:,.0f}원 · "
              f"13.2% → {pt['breakeven_contribution_low']:,.0f}원")
        print(f"  ⚠️ {' · '.join(pt['caveats'])}")

    print("\n  근거·한계: 결제일 기준환율(국세청·증권사 안내) · 선입선출 원칙(시행령 §162⑤)·이동평균 허용 · "
          "토스 신고 방식 미확인 · 환율은 종가 근사 · 상세 docs/research/tax_plan_2026-09-30.md")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="해외주식 양도세 트래커 — 결제일·원화 기준 실현손익, 공제 잔여, 연말 이익실현 계획 "
                    "(측정·계획 전용, 주문 없음)")
    ap.add_argument("--year", type=int, default=None, help="귀속 연도(기본: KST 올해)")
    ap.add_argument("--fx", type=float, default=None, help="현재 원/달러(기본: app/data.js)")
    ap.add_argument("--buffer", type=float, default=0.10,
                    help="공제 잔여 중 남겨둘 비율(환율·주가 변동·환율 근사 오차 대비, 기본 0.10)")
    ap.add_argument("--slippage-bps", type=float, default=5.0,
                    help="시장가 체결 편차 가정(편도 bp, 기본 5)")
    ap.add_argument("--max-breakeven", type=float, default=0.20,
                    help="하베스트 효율 컷 — 손익분기 확률이 이보다 크면 제외(기본 0.20)")
    ap.add_argument("--sells", action="store_true", help="귀속 연도 매도 건별 상세")
    ap.add_argument("--pension", action="store_true",
                    help="연금저축·IRP 세액공제 가치표(100/300/600/900만 × 16.5%%/13.2%%, 시스템 비용 대비)")
    ap.add_argument("--json", action="store_true", help="기계 출력")
    ap.add_argument("--save", action="store_true", help="data/research/tax_tracker_{날짜}.json 저장")
    args = ap.parse_args()

    now = dt.datetime.now(KST)
    year = args.year or now.year
    rows = trades.load_ledger()
    if not rows:
        print("원장이 비었습니다 — data/app/trades.jsonl", file=sys.stderr)
        return 1
    pf = trades.load_portfolio()
    fx_now = args.fx or trades.current_fx()
    fx_src = "--fx" if args.fx else "app/data.js"

    books, sells, domestic = build_books(rows)
    ys = year_summary(sells, year)
    fees = fee_model(rows)
    unr = unrealized(books, pf, fx_now, fees)
    # 지난 해는 결제가 끝났다 — 현재 보유로 그 해 한도를 채우는 계획은 성립하지 않는다
    closed_year = year < now.year
    hv = harvest_plan(unr, 0.0 if closed_year else ys["remaining_room"], fx_now, fees,
                      args.buffer, args.slippage_bps, args.max_breakeven)
    hv["closed_year"] = closed_year
    if closed_year:
        hv["binding_constraint"] = f"{year}년은 이미 마감 — 하베스트 불가(실현 집계만 유효)"
    res = {
        "as_of": now.strftime("%Y-%m-%d %H:%M KST"), "year": year,
        "fx_now": fx_now, "fx_src": fx_src,
        "rules": {"tax_rate": TAX_RATE, "basic_deduction": BASIC_DEDUCTION,
                  "attribution": "결제일", "us_settlement": "T+1 (2024-05-28~)",
                  "fx_rule": "취득·양도 각 결제일 기준환율(국세청·증권사 안내) — KRW=X 종가 근사",
                  "cost_method": "선입선출(원칙) · 이동평균(증권사 계속적용 시 허용) 병기",
                  "netting": "국외주식끼리만 통산 · 국내 상장주식(소액주주)은 비과세라 제외 · 이월공제 없음"},
        "fees": fees,
        "year_summary": ys,
        "ledger_view_krw": ledger_view_krw(rows, year, fx_now),
        "sells_year": [s for s in sells if s["settle"][:4] == str(year)],
        "domestic_sells_year": sum(1 for d in domestic if d["date"][:4] == str(year)),
        "unrealized": unr,
        "deadline": year_end_deadline(year),
        "harvest": hv,
        "loss_view": loss_view(unr, ys),
        "system_cost_krw_yr": SYSTEM_COST_KRW_YR,
        # JSON엔 항상 싣고(소비자가 고르게), 사람 출력엔 --pension일 때만
        "pension": pension_table(),
    }

    if args.save:
        os.makedirs(OUT_DIR, exist_ok=True)
        path = os.path.join(OUT_DIR, f"tax_tracker_{now:%Y-%m-%d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1, default=float)
        print(f"저장: {os.path.relpath(path, REPO)}", file=sys.stderr)

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1, default=float))
        return 0
    if not args.pension:
        res = {**res, "pension": None}
    render(res, args.sells)
    return 0


if __name__ == "__main__":
    sys.exit(main())
