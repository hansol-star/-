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
  signal {when}        : 시세 무관 추적 신호 — 액션 노트만 표시
  flow {signal}        : flows.json 기계 평가 — foreign_reversal(외인 순매수 전환) /
                         selling_easing(매도강도 축소 조짐) [7/2 신설]
  done                 : 완료 기록 — 표시만

사용:
  python3 triggers.py            # 표
  python3 triggers.py --json
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timedelta, timezone

from market_data import fetch_quote

KST = timezone(timedelta(hours=9))


def today_kst() -> date:
    """[7/13] D-day는 항상 KST 기준 — UTC 컨테이너에서 00~09시 KST에 하루 밀리는 것 방지."""
    return datetime.now(KST).date()


def _dday(date_str: str | None):
    """'YYYY-MM-DD' → (남은일수 int, 표시문자열). 파싱 실패/없음이면 (None, '')."""
    if not date_str:
        return None, ""
    try:
        y, m, d = (int(x) for x in date_str.split("-"))
        delta = (date(y, m, d) - today_kst()).days
        txt = "D-DAY" if delta == 0 else (f"D-{delta}" if delta > 0 else f"D+{-delta} 경과")
        return delta, txt
    except Exception:
        return None, ""

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "..", "portfolio.json")


def evaluate(alert: dict) -> dict:
    cond = alert.get("cond")
    if cond == "event":
        delta, txt = _dday(alert.get("date"))
        when = alert.get("when", "")
        detail = (f"[{txt}] " if txt else "") + when
        return {**alert, "state": "event", "price": None, "detail": detail, "dday": delta}
    if cond == "signal":
        return {**alert, "state": "signal", "price": None, "detail": alert.get("when", "매 보고서")}
    if cond == "done":
        return {**alert, "state": "done", "price": None, "detail": alert.get("when", "완료")}
    if cond == "flow":
        try:
            from flow_trend import compute_trend, load_series
            t = compute_trend(load_series())
        except Exception as ex:
            return {**alert, "state": "error", "price": None, "detail": f"flows.json 평가 실패: {ex}"}
        sig = alert.get("signal", "foreign_reversal")
        if sig == "foreign_reversal":
            fired = bool(t.get("reversal"))
        else:  # selling_easing — 매도강도 20%+ 축소 또는 순매수 전환
            chg = (t.get("intensity") or {}).get("chg_pct")
            fired = bool(t.get("reversal")) or (chg is not None and chg < -20)
        amt = t.get("last_amount", 0)
        detail = (f"[{t.get('as_of')}] {t.get('direction')} {abs(amt)/10000:.2f}조 · "
                  f"{t.get('streak')}일 연속 · 단계={t.get('stage')}")
        if t.get("intensity"):
            detail += f" · 5일강도 {t['intensity']['chg_pct']:+.1f}%"
        return {**alert, "state": "fired" if fired else "armed", "price": None, "detail": detail}

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


# ── 포지션 사이징 (리스크매니저 정량화 — ai-hedge-fund Risk Manager 착안) ──────
# 산문 "3분할" → 현금·안전핀 버퍼·집중도 기반 '이번 트랜치 권장 규모 + 단일종목 비중 상한'.
CONCENTRATION_CAP = 0.25          # 단일종목 최대 비중(주식평가액 대비)


def _level(cfg, cond, ticker):
    for a in cfg.get("alerts", []):
        if a.get("cond") == cond and a.get("ticker") == ticker:
            return a.get("level")
    return None


# 매수 안전핀(룰1) = 코스피 7,500 종가. 하드코딩이 정본이다.
# ⚠️[2026-07-29 버그픽스] 舊 구현은 `_level(cfg,"below","^KS11")`로 alerts에서 골랐는데,
# 이 헬퍼는 '첫 번째로 매칭되는' below 알림을 집어온다. 7/13 급락TF가 6,500(S2 트리거) below
# 알림을 추가한 뒤로는 안전핀이 6,500으로 잘못 잡혔다.
# 둘 다 하회 중일 땐 판정이 같아 눈에 안 띄었으나, **코스피가 6,500~7,500으로 회복하는 순간
# "안전핀 위"로 오판해 트랜치를 열어준다** — 시나리오A(8월 기술반등 6,500~7,000)가 정확히 그 구간이다.
SAFETY_PIN_KOSPI = 7500   # ⚠️ 舊 룰 상수 — 이제 사이징에 쓰지 않는다(아래 참조). 이력·표시용으로만 남긴다.


def recommend_tranche(cfg, kospi):
    """★[2026-07-30 전면 개정] 舊 '안전핀 7,500 이진 동결' → **낙폭 사다리**(crash_tf §2b).

    정훈 승인 "룰도 다 바꾸자". 舊 구현의 결함:
      ① 코스피 -38.6% 지점의 12M 기저율이 중앙 +43%·승률 97%(표본 750)인데
         **+34% 오른 뒤에야** 트랜치를 열어줬다(가장 유리한 구간을 통째로 건너뜀).
      ② 폭풍 조항이 **역작동** — 변동성 극단일수록 가장 강하게 막았다.

    新 판정은 `tranche_rules.py`가 정본이다. 여기서는 그것을 **호출만** 한다
    (사이징 로직을 두 곳에 두면 반드시 갈라진다 — 舊 안전핀이 6,500으로 잘못 잡혔던
    7/29 버그가 정확히 그 유형이었다).
    """
    if kospi is None:
        return {"amount": None, "reason": "코스피 시세 조회 실패 — 수동 판단"}
    try:
        import tranche_rules as TR
    except ImportError:
        return {"amount": None,
                "reason": "tranche_rules.py 로드 실패 — 사다리 판정 불가(수동 판단)"}

    # ⚠️[8/24 버그픽스] 舊 코드가 여기서 cfg["cash_krw"](원화만)로 cash를 덮어써
    # TR._load_inputs()가 이미 정확히 합산한 KRW+USD환산 현금을 버리고 있었다(둘 다 같은
    # portfolio.json을 읽으므로 이 덮어쓰기는 USD 현금만 무단 폐기하는 효과였다 — 8/24 리스크
    # 데스크가 tranche_rules.py 직접실행과 39,909원 vs 103,999원(2.6배) 괴리로 발견).
    # cash_krw 오버라이드는 폐기하고 TR._load_inputs()의 합산 현금을 그대로 쓴다.
    cash, dd, storm, fear, capit, _stale = TR._load_inputs(None)
    if dd is None:
        return {"amount": None,
                "reason": "코스피 낙폭 산출 실패 — history_backfill.py 필요(수동 판단)"}

    r = TR.rule1(cash, dd, storm, fear, capit)
    if r["halted"]:
        return {"amount": 0, "dd_pct": dd, "reason": r["halt_why"], "ladder": r, "cash_total": cash}
    steps = "+".join(f"D{i+1}" for i, s_ in enumerate(r["steps"]) if s_["unlocked"]) or "없음"
    return {
        "amount": r["allowed_krw"],
        "per_split": round(r["allowed_krw"] / 3) if r["allowed_krw"] else 0,
        "dd_pct": dd, "ladder": r, "cash_total": cash,
        "reason": (f"낙폭 {dd:+.1f}% → 해금 {steps}({r['unlocked_ratio']*100:.0f}%) "
                   f"× 승수 {r['final_mult']} = **상한** {r['allowed_krw']:,}원 "
                   f"({r['storm_why']}; {r['capitulation_why']}). 상한이지 목표 아님·자동집행 아님"),
    }


def concentration(cfg):
    """보유 종목별 실시간 평가비중 + 집중도 상한 초과 플래그."""
    fxq = fetch_quote("KRW=X")
    fx = (fxq or {}).get("price") or 1380.0
    vals = {}
    for region, lst in (cfg.get("holdings", {}) or {}).items():
        for h in lst:
            q = fetch_quote(h["ticker"])
            p = None if (not q or q.get("error")) else q.get("price")
            if p is None:
                continue
            v = h.get("shares", 0) * p * (fx if region == "us" else 1)
            vals[h.get("label", h["ticker"])] = v
    total = sum(vals.values())
    if total <= 0:
        return {"total_krw": 0, "weights": [], "flags": [], "fx": fx}
    weights = sorted(((k, v, v / total * 100) for k, v in vals.items()),
                     key=lambda x: -x[1])
    flags = [(k, w) for k, _, w in weights if w > CONCENTRATION_CAP * 100]
    return {"total_krw": total, "fx": fx,
            "weights": [(k, round(v), round(w, 1)) for k, v, w in weights],
            "flags": [(k, round(w, 1)) for k, w in flags]}


def sizing_panel(cfg):
    kq = fetch_quote("^KS11")
    kospi = None if (not kq or kq.get("error")) else kq.get("price")
    rec = recommend_tranche(cfg, kospi)
    con = concentration(cfg)
    cash_krw_only = cfg.get("cash_krw")
    cash = rec.get("cash_total") or cash_krw_only
    print("\n## 포지션 사이징 (정량)\n")
    if cash is not None:
        krw_tail = (f" (원화 {cash_krw_only:,.0f}원 + 외화환산 {cash - cash_krw_only:,.0f}원)"
                    if cash_krw_only is not None and abs(cash - cash_krw_only) > 1 else "")
        print(f"- 가용 현금: **{cash:,.0f}원**{krw_tail}")
    if rec.get("amount") is None:
        print(f"- 권장 트랜치: — ({rec['reason']})")
    elif rec["amount"] == 0:
        print(f"- 🔴 권장 트랜치: **0원** — {rec['reason']}")
    else:
        cap_amt = min(rec["amount"], cash) if cash else rec["amount"]
        # 舊 'buffer_pct'(안전핀까지 거리)는 사다리 개정으로 사라졌다 → 낙폭%로 대체.
        dd = rec.get("dd_pct")
        tail = f" · 코스피 낙폭 {dd:+.1f}%" if dd is not None else ""
        print(f"- 권장 트랜치 **상한**: **{cap_amt:,.0f}원** "
              f"(3분할 1회 ≈ {round(cap_amt/3):,.0f}원){tail}")
        print(f"    ↳ {rec['reason']}")
    if con["total_krw"]:
        print(f"- 주식 평가액 {con['total_krw']:,.0f}원 · 단일종목 상한 {CONCENTRATION_CAP*100:.0f}%")
        top = con["weights"][:5]
        print("    비중 상위: " + ", ".join(f"{k} {w}%" for k, _, w in top))
        if con["flags"]:
            for k, w in con["flags"]:
                print(f"    ⚠️ **{k} {w}%** > 상한 {CONCENTRATION_CAP*100:.0f}% — 추가매수 금지·트림 후보")
        else:
            print(f"    ✅ 상한 초과 종목 없음")
    return {"recommend": rec, "concentration": con, "kospi": kospi,
            "cash_krw": cash_krw_only, "cash_total": cash}


def main() -> int:
    ap = argparse.ArgumentParser(description="트리거·매수존 실시간 점검 + 포지션 사이징")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-size", action="store_true", help="포지션 사이징 패널 생략(시세 호출 절감)")
    args = ap.parse_args()

    with open(CFG, encoding="utf-8") as f:
        cfg = json.load(f)
    results = [evaluate(a) for a in cfg.get("alerts", [])]

    if args.json:
        out = {"triggers": results}
        if not args.no_size:
            kq = fetch_quote("^KS11")
            kospi = None if (not kq or kq.get("error")) else kq.get("price")
            out["sizing"] = {"recommend": recommend_tranche(cfg, kospi),
                             "concentration": concentration(cfg), "kospi": kospi,
                             "cash_krw": cfg.get("cash_krw")}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    icon = {"fired": "🔴 발동", "armed": "🟢 대기", "event": "📅 이벤트", "signal": "📡 신호",
            "done": "✅ 완료", "error": "⚠️ 오류"}
    fired = [r for r in results if r["state"] == "fired"]
    imminent = sorted(
        (r for r in results if r["state"] == "event" and r.get("dday") is not None and 0 <= r["dday"] <= 7),
        key=lambda x: x["dday"],
    )

    print("## 트리거 점검\n")
    if fired:
        print("### 🔴 지금 발동된 트리거")
        for r in fired:
            print(f"- **{r['id']}** — {r['detail']}\n  → {r['action']}")
        print()
    if imminent:
        print("### ⏰ 임박 이벤트 (D-7 이내 — 사전 베이킹 점검)")
        for r in imminent:
            print(f"- **{r['id']}**: {r['detail']}\n    ↳ {r['action']}")
        print()
    print("### 전체")
    for r in results:
        print(f"- {icon.get(r['state'],'?')} **{r['id']}**: {r['detail']}")
        if r["state"] in ("armed", "event", "signal"):
            print(f"    ↳ {r['action']}")
    if not fired:
        print("\n→ 발동된 트리거 없음. 대기 상태 유지.")
    if not args.no_size:
        sizing_panel(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
