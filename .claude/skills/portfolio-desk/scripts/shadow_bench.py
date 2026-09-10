"""그림자 벤치마크 — "지수만 샀으면 지금 얼마였나" (측정 전용 · 어떤 룰도 바꾸지 않는다)

★[2026-09-10 신설 — 정훈 "우리의 목적은 돈을 키우는 거잖아, 잘 되고 있는지 궁금해"]
  체결 원장(trades.jsonl)의 **모든 매수·매도를 같은 날 같은 금액으로 지수에 한 것으로 재생**한다.
  미국 체결 → VOO, 국내 체결 → 코스피(^KS11). 현금흐름이 동일하므로
  **최종 보유가치 차이 = 종목선택 + 타이밍의 순효과**다.
  환율은 양쪽(실제 미국주 vs VOO 그림자)에 똑같이 걸리므로 차이에서 상쇄된다 — 환율은 '시장'이지 '실력'이 아니다.
  두 창을 본다: ①원장 전체(2024-07~) ②데스크 기간(2026-06-12~, 시작 보유를 시가로 그림자에 이식).

⚠️ 한계: VOO 배당 미반영(가격 이력) · 체결가 대신 종가 · 코스피는 지수(ETF 보수 없음)
   · 데스크 기간 3개월은 실력 판정엔 짧다(8/5 절차 ②③ 미적용 — 참고 지표).

사용:
  python3 .claude/skills/portfolio-desk/scripts/shadow_bench.py
  python3 .claude/skills/portfolio-desk/scripts/shadow_bench.py --desk-start 2026-06-12
"""
import argparse
import csv
import json
import os
import sys
from bisect import bisect_right
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
H = os.path.join(ROOT, "data", "history")
SNAPS = os.path.join(ROOT, "data", "snapshots")
TRADES = os.path.join(ROOT, "data", "app", "trades.jsonl")


def load(name):
    d, p = [], []
    with open(os.path.join(H, name), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                p.append(float(r["close"]))
                d.append(r["date"][:10])
            except Exception:
                pass
    return d, p


def at(series, day):
    d, p = series
    i = bisect_right(d, day) - 1
    return p[i] if i >= 0 else None


def fname(t):
    return t.replace("^", "_").replace("=", "_") + ".csv"


def cash(r):
    amt = float(r.get("amount") or float(r["shares"]) * float(r["price"]))
    fee = float(r.get("fee") or 0) + float(r.get("tax") or 0)
    return amt + fee if r["side"] in ("buy", "opening") else amt - fee


def sign(r):
    return 1 if r["side"] in ("buy", "opening") else -1


def main():
    ap = argparse.ArgumentParser(description="그림자 벤치마크 — 원장 재생 vs VOO·코스피 (측정 전용)")
    ap.add_argument("--desk-start", default="2026-06-12", help="데스크 기간 시작일 (기본 2026-06-12)")
    a = ap.parse_args()

    VOO, KS, FX = load("VOO.csv"), load("_KS11.csv"), load("KRW_X.csv")
    rows = sorted((json.loads(l) for l in open(TRADES, encoding="utf-8")
                   if l.strip() and not l.startswith("//")), key=lambda r: r["date"])
    snap_file = sorted(f for f in os.listdir(SNAPS) if f.endswith(".json"))[-1]
    snap = json.load(open(os.path.join(SNAPS, snap_file), encoding="utf-8"))
    kr_now, us_now, fx_now = snap["kr_value"], snap["us_value_usd"], snap["fx_usdkrw"]
    ks_now = (snap.get("index_state", {}).get("^KS11") or {}).get("close") or KS[1][-1]
    pos = snap.get("positions", {}).get("VOO") or {}
    voo_now = next((float(pos[k]) for k in ("price", "close", "last") if isinstance(pos, dict) and pos.get(k)), VOO[1][-1])

    def replay(start=None, init=None):
        units, flows = {"USD": 0.0, "KRW": 0.0}, {"USD": 0.0, "KRW": 0.0}
        if init:
            units["USD"] = init["USD"] / at(VOO, start)
            units["KRW"] = init["KRW"] / at(KS, start)
        for r in rows:
            if start and r["date"] <= start:
                continue
            c, cur = cash(r), r["currency"]
            px = at(VOO, r["date"]) if cur == "USD" else at(KS, r["date"])
            units[cur] += sign(r) * c / px
            flows[cur] += sign(r) * c
        return units, flows

    def report(label, units, flows):
        sh_us, sh_kr = units["USD"] * voo_now, units["KRW"] * ks_now
        ex_us, ex_kr = us_now - sh_us, kr_now - sh_kr
        print(f"\n== {label}")
        print(f"  미국: 실제 ${us_now:,.0f} vs VOO그림자 ${sh_us:,.0f} → 차이 ${ex_us:+,.0f} (≈{ex_us * fx_now:+,.0f}원) · 순투입 ${flows['USD']:,.0f}")
        print(f"  국내: 실제 {kr_now:,.0f}원 vs 코스피그림자 {sh_kr:,.0f}원 → 차이 {ex_kr:+,.0f}원 · 순투입 {flows['KRW']:,.0f}원")
        print(f"  합계 차이 {ex_us * fx_now + ex_kr:+,.0f}원  (+ = 지수보다 잘함)")

    print(f"기준: {snap['date']} 스냅샷 · KS11 {ks_now:,.2f} · VOO ${voo_now:,.2f} · 환율 {fx_now} "
          f"(이력 마지막 VOO {VOO[0][-1]} · KS11 {KS[0][-1]})")
    u, f = replay()
    report(f"원장 전체 {rows[0]['date']} ~ {snap['date']}", u, f)

    d0 = a.desk_start
    sh, cur = defaultdict(float), {}
    for r in rows:
        if r["date"] > d0:
            break
        sh[r["ticker"]] += sign(r) * float(r["shares"])
        cur[r["ticker"]] = r["currency"]
    init, miss = {"USD": 0.0, "KRW": 0.0}, []
    for t, s in sh.items():
        if s <= 1e-6:
            continue
        if not os.path.exists(os.path.join(H, fname(t))):
            miss.append(t)
            continue
        init[cur[t]] += s * at(load(fname(t)), d0)
    fx0 = at(FX, d0)
    print(f"\n{d0} 시작 보유: 미국 ${init['USD']:,.0f} · 국내 {init['KRW']:,.0f}원 · 환율 {fx0:,.1f}"
          f"{' · ⚠️가격이력 없음 ' + ','.join(miss) if miss else ''}")
    u2, f2 = replay(d0, init)
    report(f"데스크 기간 {d0} ~ {snap['date']}", u2, f2)
    for c, now, i_now, i0 in (("USD", us_now, voo_now, at(VOO, d0)), ("KRW", kr_now, ks_now, at(KS, d0))):
        pnl = now - init[c] - f2[c]
        base = init[c] + max(f2[c], 0) / 2
        print(f"  {c}: 실제 손익 {pnl:+,.0f} ({pnl / base * 100:+.1f}% · 평균투입 대비) · 지수 자체 {i_now / i0 * 100 - 100:+.1f}%")
    print(f"  환율 {fx0:,.1f} → {fx_now:,.1f} ({fx_now / fx0 * 100 - 100:+.1f}%) — 원화 기준 미국주 가치에 그대로 반영(그림자도 동일)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
