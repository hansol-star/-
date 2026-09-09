#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
target_reset.py — 목표가 재산정 (12개월 지평 · 낙관 보정 · stdlib)

[왜 만들었나 — 2026-09-09 정훈 지시 "목표가 다 재설정 한번 해볼래?"]
`target_score.py` 실측이 결함 두 개를 동시에 가리켰다:

  ① **여력을 크게 부를수록 그만큼 빗나갔다.**
       +10~25% 목표 → 편향 +21.5%p / +25~50% → +36.8%p / **+50%↑ → +52.6%p**
       정직했던 둘은 여력을 작게 불렀다: AAPL(+1.3% 여력, 편향 -0.5%p)·ANET(+9.5%, +1.6%p).
       종목별 최악은 삼성전자 +71.6%p·ORCL +61.1%p였다.
  ② **밴드 적중률 0~6%.** 삼성전자 목표가가 `251,000~460,000`(폭 83%)이었는데도
       주가가 그 안에 안 들어왔다 — 넓기만 하고 의미가 정의돼 있지 않았다.

  ⚠️ ①의 상당 부분은 **지평 불일치**다. 12개월짜리 목표를 20거래일로 채점하면 실현이
     0 근처로 나오는 게 당연하고, 채점 구간은 코스피 -22.6% 붕괴장이었다.
     그래서 여력을 통째로 깎지 않고 **일부만** 깎는다(아래 낙관계수).

[방법론]
    중심(12M) = 현재가 × (1 + 컨센여력 × (1 − 낙관계수))
      컨센여력 = 컨센 평균 목표가 / 현재가 − 1
      낙관계수 = 0.33 기본 · 펀더 서브스코어 ≥85 → 0.25 · <40 → 0.50 · stale 의심 → +0.15
    밴드      = 애널 low/high를 같은 보정으로 스케일 → 중심의 [0.80, 1.30]으로 클램프
      (국내는 애널 low/high가 없어 ±18%)

  **왜 σ(변동성) 밴드를 안 쓰나** — 처음엔 ±1σ(68% 확률구간)로 짰다가 버렸다.
  통계적으로는 정직한데 삼성전자 밴드가 290,758~715,150(폭 146%)으로 **기존보다 더 넓어졌다.**
  목표가의 실제 용도는 확률 서술이 아니라 **익절·트림·매수 우선순위 판단**이다 —
  거기에 폭 146% 구간은 아무 쓸모가 없다. 밴드는 애널 분산에서 오는 게 맞다.

⚠️ **제안 계산기다 — `--save` 없이는 stocks.json을 바꾸지 않는다.**
⚠️ **별점·스코어·트랜치는 건드리지 않는다.** 목표가는 매 보고서 갱신 항목이지 룰이 아니다.
⚠️ 컨센이 낡으면 우리 목표도 낡는다 — `naver_value`의 stale 플래그를 반드시 반영할 것.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys

_HERE = os.path.abspath(__file__)
ROOT = os.path.abspath(os.path.join(_HERE, *([os.pardir] * 5)))
APP = os.path.join(ROOT, "data", "app")

# 국내 컨센 — naver_value.py·broker_reports.py 실측(무키). 파일 캐시가 없어 스냅샷으로 둔다.
# ⚠️ 갱신 시 반드시 두 스크립트를 다시 돌리고 날짜를 같이 바꿀 것.
KR_CONSENSUS = {
    "005930.KS": (480000, 9, False, "broker_reports 2026-09-08"),
    "066570.KS": (180000, 12, False, "broker_reports 2026-09-08"),
    "005380.KS": (701600, 22, True, "naver_value 2026-09-09 ⚠️stale 의심(크래시 미반영)"),
    "035420.KS": (330958, 4, True, "naver_value 2026-09-09 ⚠️stale 의심(크래시 미반영)"),
    "454910.KS": (None, 0, False, "적자 — 목표 미부여"),
}
# 12M 선행 EPS 스냅샷 — us_value.py/naver_value.py 실측(2026-09-09).
# ⚠️ 이게 필요한 이유: validate의 내재배수 검사는 **TTM EPS 기준**이라, 성장주는
#    선행 EPS를 안 적으면 "배수 과대"로 잡힌다(8/14 거증책임 규율). 없으면 없다고 쓴다 —
#    빈칸으로 두면 가드가 '명시 안 함'과 '값이 없음'을 구별하지 못한다.
FWD_EPS = {
    "AAPL": 8.83, "MSFT": 19.72, "GOOGL": 20.57, "META": 31.40,
    # NVDA·MU·AVGO·ORCL = FMP 402(유료 전용)로 us_value가 못 준다 — 미확보로 명시.
}
NAMES = {"005930.KS": "삼성전자", "066570.KS": "LG전자", "454910.KS": "두산로보틱스",
         "005380.KS": "현대차", "035420.KS": "NAVER"}


def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return d


def live_prices() -> dict:
    """market_data.py --json 로 실시간가. ⚠️ consensus.json 가격은 스냅샷이라 며칠 낡는다."""
    out = {}
    for grp in ("holdings", "watchlist"):
        try:
            r = subprocess.run([sys.executable, os.path.join(os.path.dirname(_HERE), "market_data.py"),
                                "--group", grp, "--json"],
                               capture_output=True, text=True, encoding="utf-8", timeout=600)
            for row in json.loads(r.stdout or "[]"):
                if row.get("price"):
                    out[row["symbol"]] = row["price"]
        except Exception as e:                                # noqa: BLE001
            print(f"[warn] 실시간가 {grp} 실패 — 스냅샷으로 폴백: {e}", file=sys.stderr)
    return out


# 재무 경보 → 낙관계수 가산.
# ⚠️ 이게 없으면 계산기가 **컨센만 보고 우리 판단을 무시한다** — 초판에서 실제로 그랬다:
#    NAVER는 margin_trend_break가 새로 떴는데 목표가가 오르고, AVGO는 재고 서지가
#    분기마다 벌어지는데 서브스코어가 높다는 이유로 낙관계수가 가장 낮게(0.25) 나왔다.
#    컨센은 이 플래그들을 모른다. 우리가 아는 걸 목표가에 반영하는 자리가 여기다.
# ⚠️ source_conflict·backlog_growth는 제외 — 전자는 데이터 품질 표시이고
#    후자는 오히려 긍정 신호다(경보를 뭉뚱그리면 지표가 오염된다).
FLAG_PENALTY = {
    "margin_trend_break": 0.15,     # 마진이 꺾였다 = 컨센 EPS 전제가 흔들린다
    "fcf_negative_turn": 0.12,
    "inventory_surge": 0.08,        # 사이클 정점 선행신호
    "debt_buildup": 0.05,
    "receivable_divergence": 0.05,
    "dilution": 0.05,
}


def optimism(sub, stale, flags=()) -> float:
    k = 0.33 if sub is None else (0.25 if sub >= 85 else (0.50 if sub < 40 else 0.33))
    if stale:
        k += 0.15
    for fl in set(flags):
        k += FLAG_PENALTY.get(fl, 0.0)
    return round(min(k, 0.65), 3)


def main() -> int:
    ap = argparse.ArgumentParser(description="목표가 재산정 (12M · 낙관 보정)")
    ap.add_argument("--save", action="store_true", help="stocks.json 목표가에 실제 반영")
    a = ap.parse_args()

    cons = load(os.path.join(APP, "consensus.json"), {}) or {}
    rows = {r["symbol"]: r for r in cons.get("rows", [])}
    fin = load(os.path.join(APP, "financials.json"), {}) or {}
    stocks = load(os.path.join(APP, "stocks.json"), {}) or {}
    px = live_prices()

    sub, flags = {}, {}

    def walk(o, tk=None):
        if isinstance(o, dict):
            for k, v in o.items():
                nt = k if (k.isupper() or ".KS" in k or ".KQ" in k) else tk
                if isinstance(v, dict):
                    s = v.get("fund_subscore") or v.get("subscore")
                    if s is not None:
                        sub[k] = s
                if k in ("flags", "alerts") and isinstance(v, list) and tk:
                    codes = [(x.get("code") if isinstance(x, dict) else str(x)) for x in v]
                    flags.setdefault(tk, []).extend([c for c in codes if c])
                walk(v, nt)
        elif isinstance(o, list):
            for x in o:
                walk(x, tk)
    walk(fin)

    st = stocks.get("stocks", {})
    print(f"{'종목':<12}{'현재가':>11}{'컨센':>11}{'컨센여력':>9}{'낙관k':>7}"
          f"{'→중심':>11}{'중심여력':>9}{'하단':>11}{'상단':>11}")
    print("─" * 94)
    updates = {}

    for tk in st:
        name = NAMES.get(tk, tk)
        kr = tk.endswith(".KS")
        if tk in KR_CONSENSUS:
            anchor, n, stale, src = KR_CONSENSUS[tk]
            lo_a = hi_a = None
        else:
            r = rows.get(tk)
            if not r or not r.get("target_mean"):
                print(f"{name:<12}{'—':>11}   컨센 없음(ETF 등) — 목표 미부여")
                continue
            anchor, n, stale, src = r["target_mean"], r.get("n_analysts"), False, "Yahoo consensus.json"
            lo_a, hi_a = r.get("target_low"), r.get("target_high")
        if not anchor:
            print(f"{name:<12}{'—':>11}   목표 미부여({src})")
            continue

        price = px.get(tk) or (rows.get(tk, {}) or {}).get("price")
        if not price:
            print(f"{name:<12}{'—':>11}   현재가 없음 — 건너뜀")
            continue

        fl = flags.get(tk, [])
        k = optimism(sub.get(tk), stale, fl)
        up_c = anchor / price - 1
        center = price * (1 + up_c * (1 - k))

        if lo_a and hi_a:
            lo = price * (1 + (lo_a / price - 1) * (1 - k))
            hi = price * (1 + (hi_a / price - 1) * (1 - k))
        else:
            lo, hi = center * 0.82, center * 1.18
        lo = max(lo, center * 0.80)             # 애널 극단값이 밴드를 무의미하게 벌리는 것을 막는다
        hi = min(hi, center * 1.30)

        f = (lambda v: f"{v:,.0f}") if kr else (lambda v: f"{v:,.1f}")
        pen = [x for x in set(fl) if x in FLAG_PENALTY]
        print(f"{name:<12}{f(price):>11}{f(anchor):>11}{up_c*100:>8.1f}%{k:>7.2f}"
              f"{f(center):>11}{(center/price-1)*100:>8.1f}%{f(lo):>11}{f(hi):>11}"
              f"  {'·'.join(sorted(pen)) if pen else ''}")
        updates[tk] = dict(low=lo, center=center, high=hi, anchor=anchor, n=n,
                           k=k, src=src, stale=stale, price=price, kr=kr, flags=sorted(pen))

    print("\n※ 중심 = 현재가 × (1 + 컨센여력 × (1−낙관계수)). 컨센을 앵커로 쓰되 종속되지 않는다.")
    print("※ 낙관계수 근거 = target_score 실측 '여력이 클수록 편향이 크다'(+50%↑ 목표는 +52.6%p 빗나갔다).")
    print("※ 지평은 **12개월**이다 — 20거래일 채점으로 '틀렸다'고 읽지 말 것.")
    print("※ 제안 전용 — --save 없이는 stocks.json을 안 바꾼다. 최종 결정은 정훈.")

    if a.save:
        for tk, u in updates.items():
            f = (lambda v: f"{v:,.0f}원") if u["kr"] else (lambda v: f"${v:,.0f}")
            st[tk]["target"] = f"{f(u['low'])}~{f(u['high'])} (중심 {f(u['center'])}·12M)"
            fe = FWD_EPS.get(tk)
            eps_note = (f"12M 선행 EPS {fe} (us_value 실측) → 중심 내재배수 {u['center']/fe:.1f}x. "
                        if fe else
                        "⚠️12M 선행 EPS **미확보**(FMP 402·국내 미제공) — 앵커인 애널 컨센이 "
                        "선행 EPS 기반이므로 TTM 기준 내재배수 검사는 과대 표시된다. ")
            st[tk]["target_basis"] = (
                f"산정일 2026-09-09 · [전면 재설정] 12M 목표 = 현재가 {f(u['price'])} × "
                f"(1 + 컨센여력 × (1−낙관계수 {u['k']:.2f})). "
                f"앵커 = 컨센 {f(u['anchor'])}(n={u['n']}, {u['src']}). {eps_note}"
                f"{'⚠️컨센 stale 의심으로 낙관계수 +0.15 가산. ' if u['stale'] else ''}"
                f"낙관계수 근거 = target_score 실측(여력이 클수록 편향이 커진다 — +50%↑ 목표 편향 +52.6%p)"+ (f" + 재무경보 가산({'·'.join(u['flags'])})" if u['flags'] else "") + ". "
                f"밴드는 애널 low/high를 같은 보정으로 스케일 후 중심의 [0.80, 1.30] 클램프."
            )
        with open(os.path.join(APP, "stocks.json"), "w", encoding="utf-8", newline="\n") as f2:
            json.dump(stocks, f2, ensure_ascii=False, indent=1)
        print(f"\n💾 stocks.json 목표가 {len(updates)}종목 반영")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
