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


def judge(eps90, qmargins, r2score, pnl_pct, etf=False):
    """순수 함수 — 입력만으로 판정한다(selftest 대상)."""
    if etf:
        return {"count": None, "verdict": "제외", "conds": {}, "missing": [], "review": False}
    missing = []
    a = None if eps90 is None else eps90 <= EPS_CUT
    if a is None:
        missing.append("A 이익전망")
    q = [x for x in (qmargins or [])[:3] if x is not None]
    b = None if len(q) < 3 else (q[0] < q[1] < q[2])
    if b is None:
        missing.append("B 분기마진")
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


def evaluate():
    import tranche_rules as T
    port = _load(".claude/skills/portfolio-desk/portfolio.json") or {}
    eps = {r["symbol"]: r for r in ((_load("data/app/eps_revisions.json") or {}).get("latest") or {}).get("rows", [])}
    fin = (_load("data/app/financials.json") or {}).get("stocks") or {}
    rows = []
    for region in ("kr", "us"):
        for h in (port.get("holdings") or {}).get(region) or []:
            t = h["ticker"]
            px = _last_close(t)
            pnl = None if not (px and h.get("cost")) else (px / h["cost"] - 1) * 100
            e = eps.get(t) or {}
            eps90 = e.get("chg_90d") if e.get("status") == "ok" else None
            qm = [(x.get("op_margin") * 100 if x.get("op_margin") is not None else None)
                  for x in (fin.get(t) or {}).get("quarterly") or []]
            r2 = T.rule2(t) if t in fin else {}
            j = judge(eps90, qm, r2.get("score"), pnl, etf=t in ETF)
            j.update({"ticker": t, "name": h.get("label"), "price": px, "cost": h.get("cost"),
                      "pnl_pct": None if pnl is None else round(pnl, 1), "eps90": eps90,
                      "qmargins": [None if x is None else round(x, 1) for x in qm[:3]],
                      "r2": r2.get("score")})
            rows.append(j)
    return {"date": dt.date.today().isoformat(), "rule": "룰8 d282 — A EPS90≤-10% · B 분기마진 2연속↓ · C 룰2≥2/3(금융 1/1) · 2개 이상=정리 · -20%=재점검",
            "rows": rows}


def _fmt(x):
    return "—" if x is None else ("✅" if x else "❌")


def show(res):
    print(f"── 정리 기준 판정 (룰8 · {res['date']}) — 2개 이상 = 정리 · 매수가 -20% = 재점검")
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


def selftest():
    cases = [
        ("3조건 전부", judge(-15, [10, 12, 14], "3/3", -30), "정리", 3, True),
        ("A+C(두산로보형)", judge(-51.6, [28.5, -81.6, -78.9], "3/3", -49), "정리", 2, True),
        ("A+금융연결 1/1(현대차형)", judge(-15.7, [5.8, 5.5, 3.6], "1/1 (금융연결)", -57), "정리", 2, True),
        ("A+B(NAVER형)", judge(-10.1, [13.0, 15.3, 16.7], "0/3", -33), "정리", 2, True),
        ("B만(GOOGL형)", judge(0.5, [31.8, 34.0, 36.1], "1/3", -15), "감시", 1, False),
        ("경계 -10.0은 충족", judge(-10.0, [1, 2, 3], "0/3", 0), "정리", 2, False),
        ("경계 -9.9는 미충족", judge(-9.9, [3, 2, 1], "1/3", 0), "정상", 0, False),
        ("결측은 미충족·표시", judge(None, [1, 2], None, None), "정상", 0, False),
        ("2/3 룰2 + 마진 횡보", judge(1.3, [5, 5, 6], "2/3", -18), "감시", 1, False),
        ("-20.0 재점검", judge(0, [3, 2, 1], "0/3", -20.0), "정상", 0, True),
    ]
    bad = 0
    for name, j, v, n, rv in cases:
        ok = j["verdict"] == v and j["count"] == n and j["review"] == rv
        bad += not ok
        print(f"{'✅' if ok else '❌'} {name}: {j['verdict']} {j['count']}/3 review={j['review']} (기대 {v} {n}/3 {rv})")
    e = judge(None, None, None, None, etf=True)
    ok = e["verdict"] == "제외"
    bad += not ok
    print(f"{'✅' if ok else '❌'} ETF 제외")
    m = judge(None, [1, 2], None, None)
    ok = len(m["missing"]) == 3
    bad += not ok
    print(f"{'✅' if ok else '❌'} 결측 3개 표시")
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
