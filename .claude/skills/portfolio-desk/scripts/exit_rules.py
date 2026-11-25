#!/usr/bin/env python3
"""exit_rules.py — 정리 기준 판정 (룰8 · d282 · 2026-11-19 정훈 승인 "대안 기준 적용")

■ 왜
  정훈 11/19 *"+몇% 하락 몇% 되면 팔고 정리하는 기준을 정해두자"* → `pct_exit_test.py`로 가격 % 룰
  24개를 검정했더니 **전부 보유보다 못했다**(Holm 1.000 · docs/research/pct_exit_test_2026-11-19.md).
  그래서 '가격'이 아니라 '오를 근거가 사라졌나'로 정리한다.

■ 룰8 (정본 = CLAUDE.md 리스크 룰 8)
  정리 조건 3개 중 **2개 이상 = 정리**(매도 오더 의무 · 사유 `논지무효`):
    A. 이익 전망: +1y EPS 추정치 90일 변화 ≤ -10%           (eps_revisions.json · Yahoo)
    B. 분기 영업마진 2분기 연속 하락 (최신 < 직전 < 그 전)    (financials.json quarterly)
    C. 룰2 추세 훼손 2/3 이상 (금융연결 기업은 1/1)            (tranche_rules.rule2)
  1개 = 감시 · 0개 = 정상 · ETF·재무 없음 = 제외.
  **재점검 트리거**: 매수가 대비 -20% 이하 → 그 보고서에서 위 판정을 반드시 표로 적는다(자동 매도 아님).

■ 하지 않는 것
  · 가격만으로 팔지 않는다(검정 기각). 고정 % 익절 없음(룰4 그대로).
  · 자동 집행 아님 — 판정과 오더 제안까지. 주문은 정훈.
  ⚠️ 이 3조건 자체는 검정되지 않았다(EPS 이력이 없었다) — `eps_revisions.py --save`로 11/19부터 쌓아
     2027-05 이후 사후 채점한다. '입증된 룰'이라고 쓰지 말 것.
  ★[2026-11-22 감사 B5·D1③·D2③] 입력이 판정할 수 없는 상태면 True/False가 아니라 **결측**이다 —
     B = 연속 3분기(financials.contiguous_run)만 · 이상치 분기(margin_suspect·영업이익 = 매출총이익) 제외 ·
     A = EPS 스냅샷이 EPS_MAX_AGE_TD 거래일보다 낡으면 결측. 행마다 fin_as_of·eps_date·q_ends를 남긴다.

사용:
  python exit_rules.py            # 보유 전종목 판정 표
  python exit_rules.py --save     # data/app/exit_rules.json 저장 (validate check_exit_rules가 읽는다)
  python exit_rules.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

EPS_CUT = -10.0      # A: 90일 EPS 변화 %
REVIEW_CUT = -20.0   # 재점검: 매수가 대비 %
ETF = {"VOO"}
OUT = os.path.join(ROOT, "data", "app", "exit_rules.json")
# ★[2026-11-22 감사 D2③] EPS 스냅샷 신선도 — 판정일과 스냅샷일 사이 거래일(주말 제외)이 이보다 많으면 A = 결측.
#   舊 = eps_revisions.json 'latest'의 chg_90d를 날짜 확인 없이 썼다(11/21 판정 ↔ 11/19 스냅샷 · 클라우드 crumb 거부로
#   저장이 빠지는 날이 잦다). 룰 문턱(-10%)은 그대로 — 바꾸는 건 '그 숫자가 오늘 것인가'를 보는 장치뿐이다.
EPS_MAX_AGE_TD = 2
try:                 # 분기 연속성 판정 = financials 한 벌(분기말 간격 80~100일 · 최신 분기 185일 초과 = 미수집)
    from financials import contiguous_run as _contig, STALE_Q_DAYS
except Exception:    # noqa: BLE001 — financials를 못 읽어도 같은 의미로 돈다(위치로 읽는 舊 방식으로 돌아가지 않는다)
    STALE_Q_DAYS = 185

    def _contig(q, n=3):
        run = list(q[:1])
        for newer, older in zip(q, q[1:n]):
            try:
                g = (dt.date.fromisoformat(newer["end"]) - dt.date.fromisoformat(older["end"])).days
            except (KeyError, TypeError, ValueError):
                break
            if not (80 <= g <= 100):
                break
            run.append(older)
        return run


def _load(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _r2_met(score):
    """'3/3'·'2/3' → True · '1/1 (금융연결)' → True · 그 외 False · None → None(결측)."""
    if not score:
        return None
    m = re.match(r"\s*(\d)/(\d)", str(score))
    if not m:
        return None
    n, d = int(m.group(1)), int(m.group(2))
    return n >= 1 if d == 1 else n >= 2


def _td_between(d0: dt.date, d1: dt.date) -> int:
    """d0 다음 날부터 d1까지의 평일 수(휴장일은 무시 — 보수적으로 덜 센다)."""
    n, d = 0, d0
    while d < d1:
        d += dt.timedelta(days=1)
        n += d.weekday() < 5
    return n


def eps_stale_why(eps_date, ref) -> str | None:
    """★[2026-11-22 감사 D2③] EPS 스냅샷이 판정에 쓰기엔 낡았으면 그 사유(아니면 None). 날짜를 모르면 낡은 것으로 본다."""
    try:
        d0 = dt.date.fromisoformat(str(eps_date)[:10])
    except (TypeError, ValueError):
        return "스냅샷 날짜 없음"
    ref = ref or dt.date.today()
    if isinstance(ref, str):
        ref = dt.date.fromisoformat(ref[:10])
    age = _td_between(d0, ref)
    return f"스냅샷 {d0.isoformat()} — {age}거래일 지남(허용 {EPS_MAX_AGE_TD})" if age > EPS_MAX_AGE_TD else None


def margin_b(quarters, ref=None):
    """룰8 B(분기 영업마진 2분기 연속 하락 · 최신 < 직전 < 그 전) → (True/False/None, 결측 사유).

    ★[2026-11-22 감사 B5] 舊 = `[x for x in qmargins[:3] if x is not None]`를 위치로 비교했다 —
      ⓐ 분기말 간격을 안 봐서 SPCX(2026-06-30 ↔ 2025-09-30 = 273일)를 '연속 3분기'로 판정했고
      ⓑ 중간 분기가 None이면 그걸 빼고 그 뒤 분기를 끌어와 비교했다(비연속 비교).
      ⇒ financials.contiguous_run(분기말 간격 80~100일 · margin_trend_break와 같은 정의)으로 **연속 3분기**만 비교한다.
      연속이 안 되거나 그 안에 결측·이상치가 있으면 True/False가 아니라 **결측**(None + 사유)이다.
    ★[2026-11-22 감사 D1③] 분기 행에 `suspect`(financials의 margin_suspect · 영업이익 = 매출총이익 같은 오매핑)가 있으면
      그 분기는 판정에 못 쓴다(LG전자 3Q 영업마진 24.4% = 매출총이익이 영업이익 칸에 들어간 값이었다).
    quarters = [{"end": "YYYY-MM-DD", "m": 영업마진 % 또는 None, "suspect": 사유 또는 None}, …] 최신부터.
    날짜 없는 숫자 목록은 연속을 확인할 수 없으니 결측이다."""
    q = list(quarters or [])
    if len(q) < 3:
        return None, f"분기 {len(q)}기뿐"
    if not all(isinstance(x, dict) and x.get("end") for x in q[:3]):
        return None, "분기말 날짜 없음 — 연속 확인 불가"
    run = _contig(q, 3)
    if len(run) < 3:
        newer, older = q[len(run) - 1], q[len(run)]
        try:
            g = (dt.date.fromisoformat(newer["end"]) - dt.date.fromisoformat(older["end"])).days
        except (KeyError, TypeError, ValueError):
            g = "?"
        return None, f"{older.get('end')} ↔ {newer.get('end')} 간격 {g}일 — 비연속(그 사이 분기 없음)"
    sus = [f"{r['end']}({r['suspect']})" for r in run if r.get("suspect")]
    if sus:
        return None, "영업마진 이상치 " + "·".join(sus)
    miss = [r["end"] for r in run if r.get("m") is None]
    if miss:
        return None, "영업마진 결측 " + "·".join(miss)
    if ref is not None:
        if isinstance(ref, str):
            ref = dt.date.fromisoformat(ref[:10])
        try:
            age = (ref - dt.date.fromisoformat(run[0]["end"])).days
        except (TypeError, ValueError):
            age = None
        if age is not None and age > STALE_Q_DAYS:
            return None, f"최신 분기 {run[0]['end']}가 {age}일 전 — 그 뒤 분기 미수집"
    return bool(run[0]["m"] < run[1]["m"] < run[2]["m"]), None


def judge(eps90, qmargins, r2score, pnl_pct, etf=False, eps_why=None, ref=None):
    """순수 함수 — 입력만으로 판정한다(selftest 대상).
    qmargins = margin_b의 분기 행 목록(분기말 날짜 포함) · eps_why = A를 결측으로 돌릴 사유(EPS 스냅샷이 낡음 등)."""
    if etf:
        return {"count": None, "verdict": "제외", "conds": {}, "missing": [], "review": False}
    missing = []
    a = None if (eps90 is None or eps_why) else eps90 <= EPS_CUT
    if a is None:
        missing.append("A 이익전망" + (f"({eps_why})" if eps_why else ""))
    b, b_why = margin_b(qmargins, ref)
    if b is None:
        missing.append(f"B 분기마진({b_why})" if b_why else "B 분기마진")
    c = _r2_met(r2score)
    if c is None:
        missing.append("C 룰2")
    n = sum(1 for x in (a, b, c) if x)
    verdict = "정리" if n >= 2 else ("감시" if n == 1 else "정상")
    review = pnl_pct is not None and pnl_pct <= REVIEW_CUT
    return {"count": n, "verdict": verdict, "conds": {"A": a, "B": b, "C": c},
            "missing": missing, "review": review}


def _last_close(ticker):
    p = os.path.join(ROOT, "data", "history", ticker.replace("^", "_").replace("=", "_") + ".csv")
    if not os.path.exists(p):
        return None
    last = None
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                last = float(r["close"])
            except (TypeError, ValueError):
                pass
    return last


def _flag_ends(f: dict, ends: list) -> list:
    """종목 단위 margin_suspect 플래그가 가리키는 분기말 — end/quarter 키 → 메시지 속 분기말 → 못 찾으면 최신 분기."""
    where = str(f.get("end") or f.get("quarter") or "")
    if where:
        return [where]
    hit = [e for e in ends if e and e in str(f.get("message") or "")]
    return hit or ends[:1]


def _suspect(q: dict, flagged: set) -> str | None:
    """★[2026-11-22 감사 D1③] 이 분기 영업마진을 판정에 쓰면 안 되는 사유(없으면 None).
    ⓐ financials가 분기 행에 단 margin_suspect(키·flags 목록) ⓑ 종목 flags의 margin_suspect가 이 분기를 가리킴
    ⓒ 영업이익 == 매출총이익(0 아님) — LG전자·삼성 3Q의 오매핑 서명(Yahoo 분기값).
    ⓒ는 판관비 미분류 회사에서 실제로 같을 수도 있다 — 그래도 B를 True/False로 확정하지 않고 결측으로 둔다(값은 안 고친다)."""
    v = q.get("margin_suspect")
    if v:
        return v if isinstance(v, str) else "margin_suspect"
    if "margin_suspect" in (q.get("flags") or []) or str(q.get("end") or "") in flagged:
        return "margin_suspect"
    gp, oi = q.get("gross_profit"), q.get("operating_income")
    if isinstance(gp, (int, float)) and isinstance(oi, (int, float)) and gp and abs(oi - gp) <= abs(gp) * 1e-6:
        return "영업이익 = 매출총이익"
    return None


def _quarters(rec: dict) -> list[dict]:
    """financials.json 종목 레코드 → margin_b 입력(최신부터 · 분기말 날짜·이상치 사유 포함)."""
    qs = list((rec or {}).get("quarterly") or [])
    ends = [str(x.get("end") or "") for x in qs]
    flagged = set()
    for f in (rec or {}).get("flags") or []:
        if isinstance(f, dict) and f.get("code") == "margin_suspect":
            flagged.update(_flag_ends(f, ends))
    out = []
    for x in qs:
        m = x.get("op_margin")
        out.append({"end": x.get("end"), "m": None if m is None else m * 100, "suspect": _suspect(x, flagged)})
    return out


def evaluate(today=None):
    import tranche_rules as T
    today = today or dt.date.today()
    port = _load(".claude/skills/portfolio-desk/portfolio.json") or {}
    eps_doc = (_load("data/app/eps_revisions.json") or {}).get("latest") or {}
    eps = {r["symbol"]: r for r in eps_doc.get("rows", [])}
    eps_date = eps_doc.get("date")
    eps_why = eps_stale_why(eps_date, today)          # ★[감사 D2③] 낡은 스냅샷이면 A = 결측
    fin_doc = _load("data/app/financials.json") or {}
    fin = fin_doc.get("stocks") or {}
    rows = []
    for region in ("kr", "us"):
        for h in (port.get("holdings") or {}).get(region) or []:
            t = h["ticker"]
            px = _last_close(t)
            pnl = None if not (px and h.get("cost")) else (px / h["cost"] - 1) * 100
            e = eps.get(t) or {}
            eps90 = e.get("chg_90d") if e.get("status") == "ok" else None
            qs = _quarters(fin.get(t) or {})
            r2 = T.rule2(t) if t in fin else {}
            j = judge(eps90, qs, r2.get("score"), pnl, etf=t in ETF,
                      eps_why=eps_why if eps90 is not None else None, ref=today)
            # ★[2026-11-22 감사 D1③·D2③] 판정에 쓴 입력의 날짜를 행마다 남긴다 — 재무 as_of·EPS 스냅샷일·쓴 분기말
            j.update({"ticker": t, "name": h.get("label"), "price": px, "cost": h.get("cost"),
                      "pnl_pct": None if pnl is None else round(pnl, 1), "eps90": eps90,
                      "qmargins": [None if x["m"] is None else round(x["m"], 1) for x in qs[:3]],
                      "q_ends": [x["end"] for x in qs[:3]],
                      "q_suspect": [x["suspect"] for x in qs[:3] if x["suspect"]],
                      "fin_as_of": (fin.get(t) or {}).get("as_of"), "eps_date": eps_date,
                      "r2": r2.get("score")})
            rows.append(j)
    return {"date": today.isoformat(), "rule": "룰8 d282 — A EPS90≤-10% · B 분기마진 2연속↓ · C 룰2≥2/3(금융 1/1) · 2개 이상=정리 · -20%=재점검",
            "eps_date": eps_date, "fin_updated": fin_doc.get("updated"),
            "rows": rows}


def _fmt(x):
    return "—" if x is None else ("✅" if x else "❌")


def show(res):
    print(f"── 정리 기준 판정 (룰8 · {res['date']}) — 2개 이상 = 정리 · 매수가 -20% = 재점검")
    # ★[2026-11-22 감사 D1③·D2③] 판정 입력의 날짜를 같이 보인다(낡은 입력으로 낸 판정이 신선해 보이지 않게)
    ew = eps_stale_why(res.get("eps_date"), res.get("date"))
    print(f"   입력: EPS 스냅샷 {res.get('eps_date') or '없음'}{' ⚠️ ' + ew + ' → A 결측' if ew else ''}"
          f" · 재무 갱신 {res.get('fin_updated') or '미상'}")
    print(f"{'종목':<10}{'원가대비':>9}  {'A EPS90':>9} {'B 분기마진(최신→)':<22}{'C 룰2':<14}{'판정':<6}")
    for r in res["rows"]:
        if r["verdict"] == "제외":
            print(f"{r['name']:<10}{'':>9}  ETF·재무 없음 → 제외")
            continue
        qm = "→".join("—" if x is None else f"{x:.1f}" for x in r["qmargins"]) or "—"
        flag = " 🔍재점검" if r["review"] else ""
        miss = f" (결측: {', '.join(r['missing'])})" if r["missing"] else ""
        pnl = "—" if r["pnl_pct"] is None else f"{r['pnl_pct']:+.1f}%"
        eps = "—" if r["eps90"] is None else f"{r['eps90']:+.1f}%"
        print(f"{r['name']:<10}{pnl:>9}  {_fmt(r['conds'].get('A'))}{eps:>7} {_fmt(r['conds'].get('B'))} {qm:<20}"
              f"{_fmt(r['conds'].get('C'))} {str(r['r2']):<12}{r['verdict']} {r['count']}/3{flag}{miss}")
    print("※ 3조건은 아직 사후 검정 전(EPS 이력 11/19부터 누적) — 자동 집행 아님.")


def _qs(*ms, start="2026-09-30", ends=None):
    """selftest용 — 최신부터 연속 분기(분기말 간격 약 91일) 행. ends를 주면 그 분기말을 쓴다."""
    if ends is None:
        d = dt.date.fromisoformat(start)
        ends = []
        for _ in ms:
            ends.append(d.isoformat())
            m0 = d.month - 3
            y = d.year + (m0 - 1) // 12
            m0 = (m0 - 1) % 12 + 1
            nxt = dt.date(y, m0 % 12 + 1, 1) - dt.timedelta(days=1) if m0 != 12 else dt.date(y, 12, 31)
            d = nxt
    return [{"end": e, "m": m, "suspect": None} for e, m in zip(ends, ms)]


def selftest():
    cases = [
        ("3조건 전부", judge(-15, _qs(10, 12, 14), "3/3", -30), "정리", 3, True),
        ("A+C(두산로보형)", judge(-51.6, _qs(28.5, -81.6, -78.9), "3/3", -49), "정리", 2, True),
        ("A+금융연결 1/1(현대차형)", judge(-15.7, _qs(5.8, 5.5, 3.6), "1/1 (금융연결)", -57), "정리", 2, True),
        ("A+B(NAVER형)", judge(-10.1, _qs(13.0, 15.3, 16.7), "0/3", -33), "정리", 2, True),
        ("B만(GOOGL형)", judge(0.5, _qs(31.8, 34.0, 36.1), "1/3", -15), "감시", 1, False),
        ("경계 -10.0은 충족", judge(-10.0, _qs(1, 2, 3), "0/3", 0), "정리", 2, False),
        ("경계 -9.9는 미충족", judge(-9.9, _qs(3, 2, 1), "1/3", 0), "정상", 0, False),
        ("결측은 미충족·표시", judge(None, _qs(1, 2), None, None), "정상", 0, False),
        ("2/3 룰2 + 마진 횡보", judge(1.3, _qs(5, 5, 6), "2/3", -18), "감시", 1, False),
        ("-20.0 재점검", judge(0, _qs(3, 2, 1), "0/3", -20.0), "정상", 0, True),
        # ★[2026-11-22 감사 B5] 비연속·중간 결측은 True/False가 아니라 결측 — 舊 위치 비교는 아래 둘을 '하락 ✅'로 읽었다
        ("273일 공백(SPCX형) → B 결측", judge(0, _qs(-5, 2, 10, ends=["2026-09-30", "2026-06-30", "2025-09-30"]),
                                       "0/3", 0), "정상", 0, False),
        ("중간 분기 None → B 결측", judge(0, _qs(1, None, 3, 5), "0/3", 0), "정상", 0, False),
        ("진짜 연속 2분기 하락 → B 충족", judge(0, _qs(1, 3, 5), "0/3", 0), "감시", 1, False),
        # ★[2026-11-22 감사 D1③] 이상치 분기(영업이익 = 매출총이익)는 판정에 못 쓴다
        ("이상치 분기 → B 결측", judge(0, [dict(r, suspect="영업이익 = 매출총이익" if i == 0 else None)
                                         for i, r in enumerate(_qs(1, 3, 5))], "0/3", 0), "정상", 0, False),
        # ★[2026-11-22 감사 D2③] 낡은 EPS 스냅샷은 A 결측(문턱 -10%는 그대로)
        ("낡은 EPS(-15%) → A 결측", judge(-15, _qs(5, 5, 6), "0/3", 0,
                                       eps_why=eps_stale_why("2026-11-10", dt.date(2026, 11, 20))), "정상", 0, False),
    ]
    bad = 0
    for name, j, v, n, rv in cases:
        ok = j["verdict"] == v and j["count"] == n and j["review"] == rv
        bad += not ok
        print(f"{'✅' if ok else '❌'} {name}: {j['verdict']} {j['count']}/3 review={j['review']} (기대 {v} {n}/3 {rv})")

    def chk(name, cond, got=""):
        nonlocal bad
        bad += not cond
        print(f"{'✅' if cond else '❌'} {name}{(' — ' + str(got)) if got != '' else ''}")

    e = judge(None, None, None, None, etf=True)
    chk("ETF 제외", e["verdict"] == "제외")
    m = judge(None, _qs(1, 2), None, None)
    chk("결측 3개 표시", len(m["missing"]) == 3, m["missing"])
    g = judge(0, _qs(-5, 2, 10, ends=["2026-09-30", "2026-06-30", "2025-09-30"]), "0/3", 0)
    chk("273일 공백 → conds B None + 사유(간격 273일)",
        g["conds"]["B"] is None and any("273일" in x for x in g["missing"]), g["missing"])
    chk("실제 SPCX 값(19.1→-1.8→-4.9 · 273일) → B None",
        margin_b(_qs(19.1, -1.8, -4.9, ends=["2026-09-30", "2026-06-30", "2025-09-30"]))[0] is None)
    chk("중간 None → 사유 '영업마진 결측'", "영업마진 결측" in (margin_b(_qs(1, None, 3, 5))[1] or ""))
    chk("날짜 없는 숫자 목록 → 결측(연속 확인 불가)", margin_b([1, 3, 5])[0] is None)
    chk("최신 분기 185일 초과 → 결측(미수집)",
        margin_b(_qs(1, 3, 5), ref=dt.date(2027, 5, 1))[0] is None)
    chk("연속 하락 + 신선 → True", margin_b(_qs(1, 3, 5), ref=dt.date(2026, 11, 22)) == (True, None))
    # financials.json 레코드 → 분기 행: 영업이익 = 매출총이익(LG전자 3Q형) · 종목 flags margin_suspect
    lg = {"quarterly": [{"end": "2026-09-30", "op_margin": 0.2441, "gross_profit": 5.8e12, "operating_income": 5.8e12},
                        {"end": "2026-06-30", "op_margin": 0.0663, "gross_profit": 4.0e12, "operating_income": 1.2e12},
                        {"end": "2026-03-31", "op_margin": 0.0705, "gross_profit": 4.1e12, "operating_income": 1.3e12}]}
    qlg = _quarters(lg)
    chk("LG전자 3Q형(영업이익 = 매출총이익) → 그 분기 suspect · B 결측",
        qlg[0]["suspect"] and margin_b(qlg)[0] is None, qlg[0]["suspect"])
    fl = dict(lg, quarterly=[dict(x, gross_profit=None) for x in lg["quarterly"]],
              flags=[{"code": "margin_suspect", "message": "2026-09-30 분기 영업이익 이상치"}])
    chk("종목 flags margin_suspect(분기말 언급) → 그 분기 suspect", _quarters(fl)[0]["suspect"] == "margin_suspect")
    ok_rec = dict(lg, quarterly=[dict(x, gross_profit=None) for x in lg["quarterly"]])
    chk("플래그·서명 없으면 suspect 없음", not any(x["suspect"] for x in _quarters(ok_rec)))
    # EPS 신선도 — 11/19(목) 스냅샷: 11/22(일) 판정은 1거래일(허용) · 11/25(수)는 4거래일(결측)
    chk("EPS 11/19 → 11/22 판정 = 신선", eps_stale_why("2026-11-19", dt.date(2026, 11, 22)) is None)
    chk("EPS 11/19 → 11/25 판정 = 낡음", eps_stale_why("2026-11-19", dt.date(2026, 11, 25)) is not None)
    chk("EPS 날짜 없음 = 낡음", eps_stale_why(None, dt.date(2026, 11, 22)) is not None)
    print("SELFTEST", "PASS" if not bad else f"FAIL {bad}")
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description="정리 기준 판정 — 룰8 d282 (측정·제안 · 자동 집행 아님)")
    ap.add_argument("--save", action="store_true", help="data/app/exit_rules.json 저장")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    res = evaluate()
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        show(res)
    if a.save:
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        print(f"저장: {OUT}")


if __name__ == "__main__":
    main()
