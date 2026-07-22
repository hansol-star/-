#!/usr/bin/env python3
"""frr_validate.py — 외국인 지분율 프록시 품질 검증 (stdlib·무키)

정훈 지시(2026-07-22 자가점검 #4). naver_chart/flow_edge는 **Δ외국인지분율(frr)=외인 순매수
수량 프록시**라고 전제했다. 그 전제를 숫자로 검증 — 네이버 두 소스가 ~60일 겹치므로 대사 가능:
  · frr 시계열   = api.stock.naver.com chart/day (봉별 foreignRetentionRate)
  · 실제 순매수량 = m.stock.naver.com trend (naver_flows·일별 foreign 순매수 수량)

같은 날짜로 정렬해 일별 Δfrr vs 실제 외인 순매수 수량의 상관·부호일치를 계산.
r 높으면 프록시 양호(지분율 심층 백테스트 신뢰), 낮으면 경고(float·지수편입 잡음 큼).

사용: python3 frr_validate.py   /   --json
"""
from __future__ import annotations

import argparse
import json
import math

try:
    import naver_chart as nc
    import naver_flows as nf
except Exception as e:  # pragma: no cover
    raise SystemExit(f"[frr_validate] 임포트 실패: {e}")

UNIVERSE = [("삼성전자", "005930"), ("LG전자", "066570"), ("두산로보틱스", "454910"),
            ("현대차", "005380"), ("NAVER", "035420"), ("SK하이닉스", "000660")]


def _pearson(xs, ys):
    n = len(xs)
    if n < 5:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs)
    sy = sum((y - my) ** 2 for y in ys)
    if sx <= 0 or sy <= 0:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return round(cov / math.sqrt(sx * sy), 3)


def check(code: str) -> dict:
    d = nc.fetch_naver_ohlc(code, "day", 200)
    if not d:
        return {"code": code, "_error": "OHLC 없음"}
    # frr[date] (봉별 지분율)
    frr_by_date = {}
    for dt, f in zip(d.get("dates") or [], d.get("frr") or []):
        if f is not None:
            frr_by_date[dt] = f  # dt = 'YYYYMMDD'
    # 실제 외인 순매수(수량) by date — naver_flows(날짜 'YYYY-MM-DD')
    rows = nf.stock_flows(code, pages=2)
    dfrr, qty = [], []
    prev = None
    matched = 0
    for r in rows:  # 시간순
        dkey = (r.get("date") or "").replace("-", "")
        f = frr_by_date.get(dkey)
        q = r.get("foreign_qty")
        if f is not None and prev is not None and q is not None:
            dfrr.append(f - prev)
            qty.append(q)
            matched += 1
        if f is not None:
            prev = f
    r_pear = _pearson(dfrr, qty)
    sign_hit = (round(100 * sum(1 for a, b in zip(dfrr, qty)
                               if (a > 0) == (b > 0)) / len(dfrr), 1) if dfrr else None)
    return {"code": code, "overlap_days": matched, "pearson_r": r_pear,
            "sign_agree_pct": sign_hit}


def main() -> int:
    ap = argparse.ArgumentParser(description="외국인 지분율(frr) 프록시 품질 검증")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    res = [dict(label=l, **check(c)) for l, c in UNIVERSE]
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0

    print("외국인 지분율(Δfrr) 프록시 검증 — Δ지분율 vs 실제 외인 순매수 수량 (naver 두 소스 대사)")
    print("=" * 78)
    print(f"{'종목':<12}{'겹침일':>7}{'Pearson r':>11}{'부호일치%':>10}  판정")
    rs = []
    for x in res:
        if x.get("_error"):
            print(f"{x['label']:<12}  {x['_error']}")
            continue
        r = x["pearson_r"]
        rs.append(r if r is not None else 0)
        verdict = ("강함(프록시 양호)" if r and r >= 0.6 else
                   "중간" if r and r >= 0.3 else "약함(잡음 큼·경고)")
        print(f"{x['label']:<12}{x['overlap_days']:>7}{str(r):>11}{str(x['sign_agree_pct']):>10}  {verdict}")
    if rs:
        avg = round(sum(rs) / len(rs), 3)
        print("-" * 78)
        print(f"평균 Pearson r = {avg}  → "
              + ("Δfrr는 외인 순매수의 신뢰 프록시(지분율 심층 백테스트 유효)" if avg >= 0.5
                 else "부분 프록시(방향은 잡으나 크기 잡음 — 지분율 백테스트는 방향 위주로 해석)"))
    print("※ 겹침이 ~60일이라 표본 제한 — 시간이 갈수록 flows 캐시 축적으로 재검증 가능(측정 전용).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
