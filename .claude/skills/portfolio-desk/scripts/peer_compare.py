#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""peer_compare.py — 보유종목 횡단면 상대비교 (peer z-score·백분위) [2026-08-05 신설]

■ 왜 만들었나
`financials.py`는 종목을 **세로로** 본다 — 한 회사의 3~5년 시계열, 마진 추세, 플래그.
그래서 "이 회사가 **동종 대비** 어디쯤인가"를 물을 수단이 없었다. 실제로 이게 없어서
생긴 구멍이 있다: 현대차 서브스코어 25.8이 **낮다**는 건 알지만, 그게 자동차 업종이
원래 그런 건지(업종 특성) 이 회사만 그런 건지(회사 문제)를 우리 숫자로 못 갈랐다.
sell-side 리포트의 '업종 대비' 서술을 받아쓰기만 했다.

상대가치 문헌의 결론은 단순하다 — **피어 선정이 결과를 지배한다**. 그래서 여기선
피어를 임의로 안 뽑고 **우리 데스크 3축(반도체·빅테크·전력/피지컬)** 그대로 쓴다.
이미 그 축으로 분석·판단하고 있으니 비교축도 같아야 서술이 안 갈린다.

■ 무엇을 비교하나 (전부 **단위 없는 비율**)
  성장  : 매출 YoY · EPS YoY
  수익성: 영업마진 · 순마진 · FCF마진
  건전성: ROE · 부채비율(D/E, 낮을수록 좋음)
  ⚠️ **절대금액(매출·자산)은 절대 비교하지 않는다** — 원화(삼성 조원)와 달러(NVDA $B)가
     한 표에 섞이면 순위가 통째로 무의미해진다. 비율만 쓰면 통화가 상쇄된다.

■ 두 개의 렌즈 (같이 봐야 뜻이 생긴다)
  1) **피어 백분위** = 동종 안에서 몇 등인가 (횡단면)
  2) **자기 이력 백분위** = 그 회사의 과거 대비 지금이 어디인가 (시계열)
  → 둘이 갈릴 때가 정보다. 예: 피어 하위인데 자기 이력 상위 = 원래 낮은 업종의 회복 국면.
     피어 상위인데 자기 이력 하위 = 좋은 회사의 둔화 초입(= 트림 검토 신호).

■ 규율
  · **측정 전용 — 별점·스코어·트랜치 어떤 룰도 바꾸지 않는다.** 매수/매도 트리거 아님.
  · [8/6] 피어에 **워치 종목을 편입**해 n을 키웠다(전력 3→10, 반도체 5→10).
    ⚠️ **n이 늘어도 비교가능성이 같이 늘지는 않는다.** 이 그룹은 *경제적 동질 피어*가 아니라
    **데스크 담당 범위**다(전력 = 전력기기+로봇+완성차+방산·조선 혼재).
    백분위를 "업종 내 위치"로 읽지 말고 **"우리 커버리지 안에서의 순위"**로 읽을 것.
  · 표본이 얇으면 n을 병기하고 n<4면 "표본 희박"을 찍는다(drawdown_history 규율과 같은 문법).
  · 회계연도 말이 회사마다 다르다(MU 8월·NVDA 1월·삼성 12월) → **최근 연간 1기**를
    비교하되 기준일을 같이 출력한다. 같은 날의 스냅샷이 아니다.

■ 사용
  peer_compare.py                      # 3개 피어그룹 전부
  peer_compare.py --group semi         # 반도체·AI인프라만
  peer_compare.py --tickers MU         # 한 종목의 피어 내 위치 상세
  peer_compare.py --json

데이터: data/app/financials.json (financials.py 산출 = EDGAR/DART/Yahoo 하드넘버). stdlib만.
⚠️ 피어(워치) 재무는 `financials.py --with-peers --save`로 채운다 — **주간 R3에서 갱신**한다.
   국내 1종목 수집이 1~2분이라 매일 도는 R2에 붙이면 보고서 완주 예산을 갉아먹는다.
   피어 재무가 없으면 그 종목은 자동 제외되고 출력에 "재무 미수집"으로 표기된다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

try:
    from cli_common import add_tickers, split_tickers
except ImportError:
    def split_tickers(value):
        import re
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            out = []
            for v in value:
                out.extend(split_tickers(v))
            return out
        return [t for t in re.split(r"[,\s]+", str(value).strip()) if t]

    def add_tickers(ap, *names, help="", **kw):
        ap.add_argument(*(names or ("--tickers",)), help=help, **kw)

HERE = os.path.dirname(os.path.abspath(__file__))
# scripts → portfolio-desk → skills → .claude → 레포 루트 (financials.py와 동일 규약)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
FIN = os.path.join(ROOT, "data", "app", "financials.json")

# 피어 그룹 = 데스크 3축 그대로 (섹터 데스크 담당 종목과 일치시킨다).
# [8/6] 보유(HOLD) + 워치 피어(PEER)로 확장 — 전력 그룹이 n=3이라 순위조차 못 되던 걸 키웠다.
# ⚠️ **n이 늘어도 비교가능성이 같이 늘지는 않는다.** 이 그룹은 *경제적 동질 피어*가 아니라
#    **데스크 담당 범위**다(특히 전력 = 전력기기+로봇+완성차+방산·조선 혼재).
#    백분위를 '업종 내 위치'로 읽지 말고 '우리 커버리지 안에서의 순위'로 읽을 것.
GROUPS = {
    "semi": ("반도체·AI인프라",
             ["NVDA", "MU", "AVGO", "ANET", "005930.KS"],
             ["000660.KS", "009150.KS", "240810.KQ", "095610.KQ", "STM"]),
    "bigtech": ("빅테크·플랫폼",
                ["AAPL", "MSFT", "GOOGL", "META", "ORCL", "035420.KS"],
                ["TMUS"]),
    "power": ("전력·피지컬AI",
              ["066570.KS", "454910.KS", "005380.KS"],
              ["034020.KS", "012450.KS", "042660.KS", "010140.KS", "329180.KS",
               "096770.KS", "GEV"]),
}

# (필드, 표시명, 높을수록 좋은가, 표시배율)
# ⚠️ financials.json은 **단위가 섞여 있다**: *_yoy 는 이미 퍼센트(65.47),
#    마진·ROE는 비율(0.6038). 초판에서 이걸 안 맞춰 NVDA 영업마진이 "0.6%"로 찍혔다.
#    백분위 계산은 단조변환이라 배율과 무관하지만, **사람이 읽는 원값은 반드시 맞춰야** 한다.
METRICS = [
    ("revenue_yoy", "매출YoY%", True, 1),
    ("eps_yoy", "EPS YoY%", True, 1),
    ("op_margin", "영업마진%", True, 100),
    ("net_margin", "순마진%", True, 100),
    ("fcf_margin", "FCF마진%", True, 100),
    ("roe", "ROE%", True, 100),
    ("debt_to_equity", "D/E", False, 1),
]
SHORT = {"005930.KS": "삼성전자", "066570.KS": "LG전자", "454910.KS": "두산로보",
         "005380.KS": "현대차", "035420.KS": "NAVER",
         # 피어(워치)
         "000660.KS": "SK하이닉스", "009150.KS": "삼성전기", "240810.KQ": "원익IPS",
         "095610.KQ": "테스", "034020.KS": "두산에너빌", "012450.KS": "한화에어로",
         "042660.KS": "한화오션", "010140.KS": "삼성중공업", "329180.KS": "HD현대중",
         "096770.KS": "SK이노베이션"}


def load():
    if not os.path.exists(FIN):
        print(f"🔴 {FIN} 없음 — 먼저 financials.py 를 돌려 재무 정본을 만들 것.", file=sys.stderr)
        sys.exit(1)
    with open(FIN, encoding="utf-8") as f:
        return json.load(f)


def latest_annual(stock):
    """가장 최근 연간 1기. financials.json은 최신이 앞(내림차순)."""
    ann = stock.get("annual") or []
    return ann[0] if ann else None


def pct_rank(value, pool, higher_better=True):
    """pool 안에서 value의 백분위(0~100). 동점은 중간값 처리.

    n이 작아 '백분위'라기보다 순위에 가깝다 — 호출부에서 n을 반드시 병기할 것.
    """
    vals = [v for v in pool if v is not None]
    if value is None or len(vals) < 2:
        return None
    below = sum(1 for v in vals if v < value)
    equal = sum(1 for v in vals if v == value)
    p = (below + 0.5 * equal) / len(vals) * 100
    return p if higher_better else 100 - p


def own_history_rank(stock, field, higher_better=True):
    """자기 이력 백분위 — 같은 지표의 과거 연간치들 대비 현재 위치."""
    ann = stock.get("annual") or []
    series = [a.get(field) for a in ann if a.get(field) is not None]
    if len(series) < 3:
        return None, len(series)
    return pct_rank(series[0], series, higher_better), len(series)


def build(data, group_key):
    label, held, peers = GROUPS[group_key]
    stocks = data["stocks"]
    members = list(held) + [p for p in peers if p not in held]
    rows = []
    for t in members:
        s = stocks.get(t)
        if not s:
            continue
        a = latest_annual(s)
        if not a:
            continue
        vals = {f: a.get(f) for f, _, _, _ in METRICS}
        rows.append({"ticker": t, "name": SHORT.get(t, t), "end": a.get("end", "?"),
                     "held": t in held, "as_of": s.get("as_of"),
                     "subscore": s.get("fund_subscore"), "vals": vals,
                     # disp = 사람이 읽을 단위로 맞춘 값(마진·ROE ×100). 순위 계산엔 vals를 쓴다.
                     "disp": {f: (None if vals[f] is None else vals[f] * sc)
                              for f, _, _, sc in METRICS},
                     "_stock": s})
    # 지표별 백분위
    for f, _, hb, _ in METRICS:
        pool = [r["vals"][f] for r in rows]
        for r in rows:
            r.setdefault("pct", {})[f] = pct_rank(r["vals"][f], pool, hb)
            r.setdefault("own", {})[f] = own_history_rank(r["_stock"], f, hb)
    # 종합 = 지표별 피어 백분위의 단순평균(가중 없음 — 가중을 두면 별점 채점기와 겹친다)
    for r in rows:
        got = [v for v in r["pct"].values() if v is not None]
        r["peer_avg"] = round(sum(got) / len(got), 1) if got else None
    rows.sort(key=lambda r: (r["peer_avg"] is None, -(r["peer_avg"] or 0)))
    return {"group": group_key, "label": label, "n": len(rows), "rows": rows,
            "n_held": sum(1 for r in rows if r["held"]),
            "missing": [t for t in members if t not in {r["ticker"] for r in rows}]}


def fmt(v, nd=1):
    return "—" if v is None else f"{v:,.{nd}f}"


def print_group(g):
    n = g["n"]
    thin = "  ⚠️표본 희박(n<4)" if n < 4 else ""
    print(f"\n═══ {g['label']}  (n={n} · 보유 {g['n_held']} + 피어 {n - g['n_held']}){thin}")
    print("   백분위 = 이 그룹 안에서의 상대 순위(100=최상). 절대금액은 비교하지 않는다(통화 혼재).")
    print("   ⚠️ 이 그룹은 **데스크 담당 범위**이지 경제적 동질 피어가 아니다 —")
    print("      '업종 내 위치'가 아니라 '우리 커버리지 안 순위'로 읽을 것. ●=보유 ·=피어(워치)")
    if g["missing"]:
        print(f"   ⚠️ 재무 미수집 {len(g['missing'])}종목 제외: {', '.join(g['missing'])}"
              f" — `financials.py --with-peers --save`로 보강")
    hdr = f"   {'종목':<12}{'기준':<12}{'종합%ile':>9}"
    for _, name, _, _ in METRICS:
        hdr += f"{name:>10}"
    print(hdr)
    for r in g["rows"]:
        mark = "●" if r["held"] else "·"
        line = f"   {mark}{r['name'][:10]:<11}{r['end']:<12}{fmt(r['peer_avg']):>9}"
        for f, _, _, _ in METRICS:
            p = r["pct"][f]
            line += f"{('—' if p is None else f'{p:.0f}'):>10}"
        print(line)
    # 값 자체도 한 번 (백분위만 보면 수준 감각이 사라진다)
    print(f"\n   [원값]")
    hdr = f"   {'종목':<12}"
    for _, name, _, _ in METRICS:
        hdr += f"{name:>10}"
    print(hdr)
    for r in g["rows"]:
        line = f"   {'●' if r['held'] else '·'}{r['name'][:10]:<11}"
        for f, _, _, _ in METRICS:
            line += f"{fmt(r['disp'][f]):>10}"
        print(line)
    # 두 렌즈가 갈리는 지점 = 이 도구의 핵심 산출
    print(f"\n   [피어 vs 자기이력 — 갈리는 지점만]")
    print("     ※ 두 축 모두 표본이 5 안팎이라 '백분위'는 사실상 순위다. 정황일 뿐 판정이 아니다.")
    found = False
    for r in g["rows"]:
        for f, name, _, _ in METRICS:
            p, (o, ny) = r["pct"][f], r["own"][f]
            # 자기이력 표본이 4기 미만이면 비교 자체를 하지 않는다(3기 백분위는 노이즈).
            if p is None or o is None or ny < 4:
                continue
            if p >= 70 and o <= 25:
                print(f"     ⚠️ {r['name']} {name}: 피어 상위({p:.0f}) ↔ 자기이력 하위({o:.0f}, {ny}기)"
                      f" — 동종 대비 앞서 있으나 **자기 기준으론 내려오는 중**")
                found = True
            elif p <= 30 and o >= 75:
                print(f"     🔵 {r['name']} {name}: 피어 하위({p:.0f}) ↔ 자기이력 상위({o:.0f}, {ny}기)"
                      f" — 동종엔 못 미치나 **자기 기준으론 최고 수준**")
                found = True
    if not found:
        print("     없음 — 두 렌즈가 같은 방향. ※'없음'도 결론.")


def print_detail(data, ticker):
    """한 종목의 피어 내 위치 상세."""
    gk = next((k for k, (_, h, p) in GROUPS.items() if ticker in h or ticker in p), None)
    if not gk:
        print(f"🔴 {ticker} 는 피어 그룹에 없다. 지원: "
              f"{', '.join(sum((list(h) + list(p) for _, h, p in GROUPS.values()), []))}",
              file=sys.stderr)
        return 1
    g = build(data, gk)
    r = next((x for x in g["rows"] if x["ticker"] == ticker), None)
    if not r:
        print(f"🔴 {ticker} 재무 데이터 없음 — financials.py 먼저 실행.", file=sys.stderr)
        return 1
    rank = g["rows"].index(r) + 1
    print(f"\n🔬 {r['name']} ({ticker}) — {g['label']} 내 위치")
    print(f"   피어 종합 백분위 {fmt(r['peer_avg'])} · 그룹 {rank}/{g['n']}위 · "
          f"재무 서브스코어 {r['subscore']} · 기준 {r['end']}")
    if g["n"] < 4:
        print("   ⚠️ 표본 희박(n<4) — 순위를 통계로 읽지 말 것.")
    print(f"\n   {'지표':<12}{'값':>10}{'피어%ile':>10}{'자기이력%ile':>14}")
    for f, name, _, _ in METRICS:
        p, (o, ny) = r["pct"][f], r["own"][f]
        own_s = "—" if o is None else f"{o:.0f} ({ny}기)"
        print(f"   {name:<12}{fmt(r['disp'][f]):>10}{('—' if p is None else f'{p:.0f}'):>10}{own_s:>14}")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="보유종목 횡단면 상대비교 — 피어 백분위 + 자기이력 백분위 (측정 전용)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="예) peer_compare.py --group semi\n    peer_compare.py --tickers 005380.KS")
    ap.add_argument("--group", choices=list(GROUPS), help="피어 그룹 하나만")
    add_tickers(ap, "--tickers", help="한 종목의 피어 내 위치 상세")
    ap.add_argument("--json", action="store_true", help="기계 소비용 JSON")
    args = ap.parse_args()

    data = load()
    picked = split_tickers(args.tickers)
    if picked:
        return print_detail(data, picked[0])

    keys = [args.group] if args.group else list(GROUPS)
    groups = [build(data, k) for k in keys]

    if args.json:
        out = {"as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
               "financials_updated": data.get("updated"),
               "groups": [{k: v for k, v in g.items() if k != "rows"} |
                          {"rows": [{k: v for k, v in r.items() if k != "_stock"}
                                    for r in g["rows"]]} for g in groups]}
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return 0

    print(f"\n📊 보유종목 횡단면 상대비교 (financials.json 기준일 {data.get('updated')})")
    print("   측정 전용 — 별점·스코어·트랜치 어떤 룰도 바꾸지 않는다.")
    for g in groups:
        print_group(g)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
