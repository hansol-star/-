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
        # ★[9/28] 신선도 가드 — flows.json이 9/22에 멈춘 채 9/28(외인 -3.2조 순매도)에도
        #   '외국인 순매수 전환 🔴발동'을 띄웠다. 묵은 수급으로 발동하면 게이트②를 거꾸로 읽는다.
        #   as_of 이후 지나간 평일(오늘은 16시 이후만)이 2일 이상이면 발동 대신 stale로 낸다.
        #   ⚠️ 공휴일을 모르는 평일 계산이라 연휴 뒤엔 과하게 stale이 뜰 수 있다 — 안전한 쪽 오류.
        try:
            import datetime as _dt
            asof = _dt.date.fromisoformat(str(t.get("as_of"))[:10])
            now = _dt.datetime.utcnow() + _dt.timedelta(hours=9)
            d, missed = asof + _dt.timedelta(days=1), 0
            while d <= now.date():
                if d.weekday() < 5 and (d < now.date() or now.hour >= 16):
                    missed += 1
                d += _dt.timedelta(days=1)
            if missed >= 2:
                return {**alert, "state": "stale", "price": None,
                        "detail": detail + f" · ⚠️수급 {missed}거래일 미기입 — 발동 판정 보류(flows.json 갱신 필요)"}
        except (TypeError, ValueError):
            pass
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
try:                              # 룰6 국내 비중 밴드 — 정본은 tranche_rules(두 곳에 숫자를 두지 않는다)
    from tranche_rules import RULE6_KR_HI, RULE6_KR_LO, kr_weight_pct
except ImportError:
    RULE6_KR_HI, RULE6_KR_LO = 22.0, 18.0

    def kr_weight_pct():
        return None
FX_FALLBACK = 1380.0              # 환율 시세 실패 시 대체값 — 이 값으로 낸 비중은 '미산출'로 친다


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

    r = TR.rule1(cash, dd, storm, fear, capit, kr_weight=TR.kr_weight_pct())   # d207 룰6 우선
    # ★[2026-10-01 d223] 낙폭 사다리 폐기 → **원화 6개월 균등 분할**. 금액·사유는 tranche_rules.kr_track이 정본이고
    #   여기서는 그대로 옮긴다(해금 단계·승수·폭풍 분할 서술은 사다리와 함께 사라졌다 — 회차가 이미 분할이다).
    if r.get("mode") == "dca6":
        return {
            "amount": r["allowed_krw"], "splits": 1, "per_split": r["allowed_krw"],
            "dd_pct": dd, "ladder": r, "cash_total": cash,
            "reason": (f"국내 트랙 [{r.get('status')}] {r.get('why')} · {r['halt_why']}. "
                       "상한이지 목표 아님·자동집행 아님"),
        }
    if r["halted"]:
        return {"amount": 0, "dd_pct": dd, "reason": r["halt_why"], "ladder": r, "cash_total": cash}
    # ⚠️[2026-09-09] `f"D{i+1}"`은 **인덱스로 D번호를 만든다** — D0 신설로 i와 D번호가
    #   어긋나면서 해금된 D0가 "D1"으로 표시되고 있었다(금액은 정합, 라벨만 거짓말).
    #   tranche_rules의 STEP_LABELS를 정본으로 쓴다. 같은 실수를 두 파일에서 반복하지 않는다.
    _labels = getattr(TR, "STEP_LABELS", None)
    steps = "+".join(
        (_labels[i] if _labels and i < len(_labels) else f"D{i+1}")
        for i, s_ in enumerate(r["steps"]) if s_["unlocked"]
    ) or "없음"
    # ★[8/28] 분할 횟수는 폭풍 %ile이 정한다(tranche_rules.storm_splits) — 3 하드코딩이었다.
    _sp = r.get("storm_splits") or 3
    return {
        "amount": r["allowed_krw"],
        "splits": _sp,
        "per_split": round(r["allowed_krw"] / _sp) if r["allowed_krw"] else 0,
        "dd_pct": dd, "ladder": r, "cash_total": cash,
        "reason": (f"낙폭 {dd:+.1f}% → 해금 {steps}({r['unlocked_ratio']*100:.0f}%) "
                   f"× 승수 {r['final_mult']} = **상한** {r['allowed_krw']:,}원 "
                   f"({r['storm_why']}; {r['capitulation_why']}). 상한이지 목표 아님·자동집행 아님"),
    }


def concentration(cfg):
    """보유 종목별 실시간 평가비중 + 집중도 상한 초과 플래그."""
    fxq = fetch_quote("KRW=X")
    fx_live = None if (not fxq or fxq.get("error")) else fxq.get("price")
    fx = fx_live or FX_FALLBACK
    vals = {}
    kr_val = 0.0
    missing = []
    for region, lst in (cfg.get("holdings", {}) or {}).items():
        for h in lst:
            q = fetch_quote(h["ticker"])
            p = None if (not q or q.get("error")) else q.get("price")
            if p is None:
                missing.append(h.get("label", h["ticker"]))
                continue
            v = h.get("shares", 0) * p * (fx if region == "us" else 1)
            vals[h.get("label", h["ticker"])] = v
            if region != "us":
                kr_val += v
    total = sum(vals.values())
    if total <= 0:
        return {"total_krw": 0, "weights": [], "flags": [], "fx": fx}
    weights = sorted(((k, v, v / total * 100) for k, v in vals.items()),
                     key=lambda x: -x[1])
    flags = [(k, w) for k, _, w in weights if w > CONCENTRATION_CAP * 100]
    # ★[10/13] 룰6 국내 비중을 **실행 시점 시세로** 낸다 — 알림 문구에 박아 둔 숫자(9/3의 28.2%·410,164원)가
    #   한 달 넘게 현행처럼 읽혔다. 22%까지 팔아야 하는 금액 x는 (KR−x)/(T−x)=0.22 의 해다.
    kr_pct, kr_trim = rule6_weight(kr_val, total)
    # 종목 하나라도 시세가 빠지거나 환율이 대체값이면 분모·분자가 틀린다 — 숫자를 내지 않는다
    # (미국주 시세만 실패하면 국내 비중이 부풀고, 국내주가 빠지면 '밴드 안'으로 잘못 읽힌다).
    why = []
    if missing:
        why.append("시세 실패: " + "·".join(missing))
    if not fx_live:
        why.append(f"환율 시세 실패(대체값 {FX_FALLBACK:,.0f})")
    if why:
        kr_pct = kr_trim = None
    return {"total_krw": total, "fx": fx, "kr_pct": kr_pct, "kr_trim_krw": kr_trim,
            "kr_note": " · ".join(why) or None, "missing": missing,
            "weights": [(k, round(v), round(w, 1)) for k, v, w in weights],
            "flags": [(k, round(w, 1)) for k, w in flags]}


def rule6_weight(kr_val: float, total: float):
    """(국내 비중 %, 상단까지 팔아야 하는 금액). 금액 x는 (KR−x)/(T−x) = 상단 의 해 — 판 돈이 분모에서도 빠진다."""
    if not total or total <= 0:
        return None, None
    hi = RULE6_KR_HI / 100
    return round(kr_val / total * 100, 1), round(max(0.0, (kr_val - hi * total) / (1 - hi)))


def rule6_line(con: dict, snap_pct=None) -> str:
    """사이징 패널의 룰6 줄. 실시세 값과 **게이트가 실제로 쓰는 값(일일 스냅샷)**을 같이 보인다 —
    둘이 22% 양쪽으로 갈리면 이 줄과 tranche_rules 판정이 서로 다른 말을 하게 된다."""
    hi, lo = RULE6_KR_HI, RULE6_KR_LO
    snap = f" · 게이트 판정값(일일 스냅샷) {snap_pct:.1f}%" if snap_pct is not None else ""
    pct = con.get("kr_pct")
    if pct is None:
        return f"- 룰6 국내 비중 **미산출** — {con.get('kr_note') or '시세 없음'}{snap}"
    if pct > hi:
        split = ""
        if snap_pct is not None and snap_pct <= hi:
            split = f" ⚠️ 스냅샷은 {hi:.0f}% 이하 — 게이트는 스냅샷으로 판정한다"
        return (f"- 룰6 국내 비중 **{pct}%** > {hi:.0f}% — {hi:.0f}%까지 트림 필요액 약 {con['kr_trim_krw']:,.0f}원"
                f"(지금 시세 기준). 착수는 코스피 고점대비 -15% 회복 후·저점 매도 금지{snap}{split}")
    split = ""
    if snap_pct is not None and snap_pct > hi:
        split = f" ⚠️ 스냅샷은 {hi:.0f}% 초과 — 게이트는 스냅샷으로 판정한다"
    if pct < lo:
        return f"- 룰6 국내 비중 {pct}% < {lo:.0f}% — 밴드 하단 미달{snap}{split}"
    return f"- 룰6 국내 비중 {pct}% — 밴드({lo:.0f}~{hi:.0f}%) 안{snap}{split}"


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
        # ★[8/28] 분할 횟수를 3으로 하드코딩하고 있었다 — 폭풍 %ile이 정하는 값인데
        # 같은 실행의 reason 문자열은 "2분할 권장"이라 **한 화면에서 2와 3이 동시에 보였다**.
        # 집행 금액이 갈리는 자리라 tranche_rules가 준 값을 그대로 쓴다.
        nsp = rec.get("splits") or 3
        _split_txt = "이번 회차 몫" if nsp == 1 else f"{nsp}분할 1회 ≈ {round(cap_amt/nsp):,.0f}원"
        print(f"- 권장 트랜치 **상한**: **{cap_amt:,.0f}원** ({_split_txt}){tail}")
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
        print(rule6_line(con, kr_weight_pct()))
    return {"recommend": rec, "concentration": con, "kospi": kospi,
            "cash_krw": cash_krw_only, "cash_total": cash}


def selftest() -> int:
    """룰6 국내 비중 줄 자가검증(오프라인) — 시세를 주입해 계산·미산출·밴드 문구를 확인한다."""
    global fetch_quote
    fails = []

    def ok(name, cond):
        print(f"  {'✅' if cond else '❌'} {name}")
        if not cond:
            fails.append(name)

    cfg = {"holdings": {"kr": [{"ticker": "A.KS", "label": "국내A", "shares": 10}],
                        "us": [{"ticker": "B", "label": "미국B", "shares": 2}]}}
    px = {"KRW=X": 1000.0, "A.KS": 30000.0, "B": 350.0}      # 국내 300,000 / 미국 700,000 = 30.0%
    keep = fetch_quote
    try:
        fetch_quote = lambda s: {"price": px[s]} if px.get(s) else {"error": "no data"}   # noqa: E731
        con = concentration(cfg)
        ok("국내 비중 30.0% · 22%까지 트림 필요액 = (300,000 − 0.22×1,000,000)/0.78 = 102,564원",
           con["kr_pct"] == 30.0 and con["kr_trim_krw"] == 102564)
        x = con["kr_trim_krw"]
        ok("그만큼 팔면 정확히 22%", abs((300000 - x) / (1000000 - x) * 100 - RULE6_KR_HI) < 0.01)
        line = rule6_line(con, 29.4)
        ok("초과 문구에 필요액·스냅샷 값이 같이 나온다", "102,564원" in line and "29.4%" in line and "**30.0%**" in line)
        ok("실시세는 초과인데 스냅샷이 밴드 안이면 경고", "게이트는 스냅샷으로 판정" in rule6_line(con, 21.5))
        px["B"] = None                                        # 미국주 시세 실패 → 국내 100%로 부풀 뻔한 자리
        bad = concentration(cfg)
        ok("종목 시세가 하나라도 빠지면 비중을 내지 않는다",
           bad["kr_pct"] is None and bad["kr_trim_krw"] is None and "미국B" in (bad["kr_note"] or ""))
        ok("미산출 문구에 빠진 종목이 나온다", "미산출" in rule6_line(bad) and "미국B" in rule6_line(bad))
        px["B"], px["KRW=X"] = 350.0, None                    # 환율 실패 → 대체값으로 낸 비중은 버린다
        fxbad = concentration(cfg)
        ok("환율이 대체값이면 비중을 내지 않는다", fxbad["kr_pct"] is None and "환율" in (fxbad["kr_note"] or ""))
    finally:
        fetch_quote = keep
    ok("밴드 안(18~22%)", "밴드(18~22%) 안" in rule6_line({"kr_pct": 20.0, "kr_trim_krw": 0}))
    ok("하단 미달(<18%)을 '밴드 안'이라 하지 않는다",
       "하단 미달" in rule6_line({"kr_pct": 15.0, "kr_trim_krw": 0}))
    ok("22.0%는 초과가 아니다(게이트와 같은 부등호)", "안" in rule6_line({"kr_pct": 22.0, "kr_trim_krw": 0}))
    print()
    print("✅ SELFTEST PASS" if not fails else f"❌ SELFTEST FAIL {len(fails)}건: {fails}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="트리거·매수존 실시간 점검 + 포지션 사이징")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-size", action="store_true", help="포지션 사이징 패널 생략(시세 호출 절감)")
    ap.add_argument("--selftest", action="store_true", help="룰6 국내 비중 줄 자가검증(오프라인)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

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
            "done": "✅ 완료", "error": "⚠️ 오류", "stale": "⏸️ 데이터 묵음"}
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
