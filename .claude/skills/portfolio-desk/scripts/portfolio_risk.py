#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
portfolio_risk.py — 포트폴리오 레벨 리스크 게이지·인사이트 (측정 전용)

왜 있나 [8/23 신설]
──────────────────
우리는 **종목마다** 별점·스코어를 매겨왔지만 **포트폴리오 전체를 한 눈으로 보는 축이 없었다.**
집중도·통화 쏠림·⭐2 방치·현금 대응력은 전부 "종목 하나"가 아니라 "조합"의 성질인데,
그 층위에 지표가 없으니 매 보고서가 15개 종목을 각각 논하고 조합은 산문으로만 다뤘다.

여기서 만드는 건 두 가지다:
  ① 리스크 점수 0~100 (높을수록 위험) — 7개 축의 가중합, 각 축의 기여를 항상 같이 낸다
  ② 인사이트 카드 — 규칙 기반 경보. **우리 룰 번호를 달고 나온다**(일반론 금지)

각 축은 이미 우리가 쓰던 임계를 그대로 쓴다(새 룰을 만드는 게 아니라 **모아서 보여주는 것**):
  · 집중도 40%/25%      — 참고소스 임계 + 우리 관행
  · 통화 쏠림           — roadmap 3-1 열린 질문(달러 71.9%)
  · ⭐2 이하 액션 의무   — 8/2 "관망은 결정이 아니다"
  · 사다리·하드플로어    — 리스크룰 1 (tranche_rules 판정 결과를 받아 쓴다)
  · 룰2 훼손 3중조건    — financials 플래그(있으면)

⚠️ **측정 전용 — 어떤 룰도 바꾸지 않고, 자동 매매도 없다.** 점수가 높다고 파는 게 아니라
   "지금 조합이 어디에 기울어 있는지"를 한 숫자로 보여줄 뿐이다. 결정은 정훈.

사용법:
  python3 portfolio_risk.py           # app/data.js 기준 요약
  python3 portfolio_risk.py --json    # 기계 출력 (build_app_data가 소비)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DATA_JS = os.path.join(REPO, "app", "data.js")
KST = dt.timezone(dt.timedelta(hours=9))

# 축 가중치 (합 100). 손실에 직결되는 순.
WEIGHTS = {
    "concentration": 22,   # 단일 종목 집중
    "currency": 16,        # 통화 쏠림
    "theme": 16,           # 테마(섹터) 집중
    "low_star": 18,        # ⭐2 이하 보유 비중
    "drawdown": 12,        # 하락 종목
    "cash": 10,            # 현금 대응력
    "regime": 6,           # 시장 국면(사다리·하드플로어)
}


def _band(v, lo, hi):
    """lo 이하=0, hi 이상=100 사이 선형."""
    if v is None:
        return 0.0
    if v <= lo:
        return 0.0
    if v >= hi:
        return 100.0
    return (v - lo) / (hi - lo) * 100


def compute(holdings, totals, safety=None, fx=None, trades=None, orders=None) -> dict:
    """holdings = build_app_data 종목 dict 리스트(value_krw·pnl_pct·stars·sector 필요)."""
    hs = [h for h in holdings if h.get("value_krw")]
    stock_total = sum(float(h["value_krw"]) for h in hs) or 1.0
    assets = float((totals or {}).get("assets_krw") or stock_total)
    cash = float((totals or {}).get("cash_krw") or 0) + float((totals or {}).get("cash_usd_krw") or 0)

    # ── 축별 원지표 ──
    by_w = sorted(hs, key=lambda h: -float(h["value_krw"]))
    top = by_w[0] if by_w else None
    top_w = float(top["value_krw"]) / stock_total * 100 if top else 0.0
    hhi = sum((float(h["value_krw"]) / stock_total * 100) ** 2 for h in hs)  # 0~10,000

    sec = {}
    for h in hs:
        sec[h.get("sector") or "기타"] = sec.get(h.get("sector") or "기타", 0) + float(h["value_krw"])
    top_sec, top_sec_v = max(sec.items(), key=lambda kv: kv[1]) if sec else ("—", 0)
    top_sec_w = top_sec_v / stock_total * 100

    usd_w = None   # fx 미배선 시 0으로 두면 "달러 노출 없음"이라는 거짓 안전 신호가 된다
    if fx:
        for b in fx.get("buckets", []):
            if b["currency"] == "USD":
                usd_w = float(b["weight"])
    low_star = [h for h in hs if (h.get("stars") or 5) <= 2]
    low_star_w = sum(float(h["value_krw"]) for h in low_star) / stock_total * 100
    losers = [h for h in hs if (h.get("pnl_pct") or 0) < -10]
    worst = min(hs, key=lambda h: h.get("pnl_pct") or 0) if hs else None
    cash_w = cash / assets * 100 if assets else 0.0

    axes = {
        # 25% 넘어가면 오르기 시작, 45%에서 만점
        "concentration": _band(top_w, 25, 45),
        # 60% 넘어가면 오르기 시작, 85%에서 만점 (roadmap 3-1: 71.9%가 의도된 것인지 열린 질문)
        # fx 미배선이면 None = 미측정 (0으로 채우지 않는다 — 8/22 "가드 없는 폴백은 침묵보다 나쁘다")
        "currency": _band(usd_w, 60, 85) if usd_w is not None else None,
        "theme": _band(top_sec_w, 30, 60),
        "low_star": _band(low_star_w, 0, 30),
        "drawdown": _band(len(losers) / len(hs) * 100 if hs else 0, 20, 70),
        # 현금은 적을수록 위험 — 방향을 뒤집는다 (15% 이상이면 0)
        "cash": 100 - _band(cash_w, 0, 15),
        "regime": 0.0,
    }
    s = (safety or {})
    if s.get("halted") or s.get("status") == "freeze":
        axes["regime"] = 100.0   # 하드플로어 발동 = 글로벌 확산 전제
    elif (s.get("drawdown_pct") or 0) <= -25:
        axes["regime"] = 60.0
    elif (s.get("drawdown_pct") or 0) <= -15:
        axes["regime"] = 30.0

    # 미측정 축은 점수에서 빼고 **가중치 분모도 줄인다** (0점 처리하면 위험이 낮아 보인다)
    measured = [k for k in WEIGHTS if axes[k] is not None]
    wsum = sum(WEIGHTS[k] for k in measured) or 1
    score = sum(axes[k] * WEIGHTS[k] for k in measured) / wsum
    score = max(0, min(100, round(score)))
    unmeasured = [k for k in WEIGHTS if axes[k] is None]
    level = "높음" if score >= 60 else "보통" if score >= 35 else "낮음"

    # ── 인사이트 (규칙 기반 · 우리 룰 번호를 단다) ──
    ins = []
    def add(lv, cat, title, detail):
        ins.append({"level": lv, "category": cat, "title": title, "detail": detail})

    if top and top_w > 40:
        add("danger", "concentration", "단일 종목 집중 — 최우선 점검",
            f"{top['label']} 비중 {top_w:.1f}%. 권장 상한 40% 초과. 트림을 **오더북에 가격·수량으로** 올릴지 검토"
            f"(8/2 원칙: 산문에 남은 판단은 증발한다).")
    elif top and top_w > 25:
        add("warning", "concentration", "비중 집중 주의",
            f"최대 보유 {top['label']} {top_w:.1f}%. 추가 노출은 분할로만 — 룰3 추격매수 금지.")

    if usd_w >= 70:
        pctl = ((fx or {}).get("percentile") or {}).get("windows", {}).get("1y", {}).get("percentile")
        tail = f" · 원/달러 1년 {pctl}%ile" if pctl is not None else ""
        add("warning", "currency", "통화 쏠림 — 달러 편중",
            f"달러 자산 {usd_w:.1f}%{tail}. 환율 1% 변동 = 총자산 "
            f"{(fx or {}).get('sensitivity_1pct_krw', 0):+,}원. roadmap 3-1(목표 비중을 정할 것인가)이 아직 열린 질문.")

    if fx and fx.get("attribution", {}).get("fx_krw", 0) < 0:
        a = fx["attribution"]
        if abs(a["fx_krw"]) > abs(a["price_krw"]) * 0.5:
            add("info", "currency", "환손익이 종목손익을 잠식 중",
                f"미국주 종목 기여 {a['price_krw']:+,}원인데 환 기여 {a['fx_krw']:+,}원 — "
                f"주가로 번 걸 환율이 되돌리고 있다(교차 {a['cross_krw']:+,}원).")

    if low_star:
        names = "·".join(h["label"] for h in low_star)
        low_tk = {h.get("ticker") for h in low_star}
        dead = ("폐기", "취소", "완료", "체결", "대체")
        n_ord = len([o for o in (orders or [])
                     if o.get("ticker") in low_tk
                     and not any(d in str(o.get("status") or "") for d in dead)])
        add("danger" if not n_ord else "warning", "low_star", "⭐2 이하 보유 — 액션 의무",
            f"{names} (비중 {low_star_w:.1f}%). 오더북 등록 {n_ord}건. "
            f"'관망'은 결정이 아니다 — 트림 오더 또는 기한부 홀드 중 하나여야 한다(8/2).")

    if losers:
        add("warning" if len(losers) >= 3 else "info", "drawdown", "하락 종목 점검",
            f"{len(losers)}개가 -10% 이하 (최대 {worst['label']} {worst.get('pnl_pct', 0):+.1f}%). "
            f"단기 손절선은 영구 폐기 — 룰2 3중조건(마진·FCF·순부채)으로만 트림을 판단한다.")

    if cash_w < 10:
        add("info", "cash", "현금 대응력",
            f"현금 비중 {cash_w:.1f}%. 사다리가 해금돼도 넣을 실탄이 얇다.")

    if trades and trades.get("sells"):
        r = trades["realized_krw"]
        add("positive" if r >= 0 else "warning", "realized", "실현손익 누계",
            f"매도 {trades['sells']}건 확정 {r:+,}원 · 승률 {trades.get('win_rate')}%. "
            f"평가손익과 별개 — 원장(trades.jsonl) 재생 기준.")

    if s.get("status") == "freeze" or s.get("halted"):
        add("danger", "regime", "하드플로어 발동 — 사다리 전면 정지",
            f"{s.get('floor_note') or 'S&P500 폭풍 ≥70%ile'}. 신규 매수 판단 금지(리스크룰 1).")
    elif s.get("drawdown_pct") is not None:
        add("info", "regime", "낙폭 사다리 상태",
            f"고점대비 {s['drawdown_pct']:.1f}% · 해금 {s.get('unlocked_pct', 0)}%. "
            f"RESET 정책 — 회복하면 다시 잠긴다(누적 상한이지 목표 아님).")

    order = {"danger": 0, "warning": 1, "info": 2, "positive": 3}
    ins.sort(key=lambda x: order[x["level"]])

    return {
        "score": score, "level": level,
        "axes": [{"key": k, "label": {
            "concentration": "종목 집중", "currency": "통화 쏠림", "theme": "테마 집중",
            "low_star": "⭐2 이하", "drawdown": "하락 종목", "cash": "현금 대응력",
            "regime": "시장 국면"}[k],
            "value": round(axes[k]) if axes[k] is not None else None, "weight": WEIGHTS[k],
            "contribution": round(axes[k] * WEIGHTS[k] / wsum, 1) if axes[k] is not None else None}
            for k in WEIGHTS],
        "facts": {
            "top": top["label"] if top else None, "top_weight": round(top_w, 1),
            "hhi": round(hhi), "top_sector": top_sec, "top_sector_weight": round(top_sec_w, 1),
            "usd_weight": round(usd_w, 1) if usd_w is not None else None, "low_star_weight": round(low_star_w, 1),
            "losers": len(losers), "holdings": len(hs), "cash_weight": round(cash_w, 1),
        },
        "insights": ins,
        "unmeasured": unmeasured,
        "disclaimer": "측정 전용 — 점수는 조합의 기울기를 보여줄 뿐, 매매 신호가 아니다.",
    }


def _load_data_js() -> dict:
    raw = open(DATA_JS, encoding="utf-8").read()
    return json.loads(raw[raw.index("{"):raw.rindex("}") + 1])


def main() -> int:
    ap = argparse.ArgumentParser(description="포트폴리오 리스크 게이지·인사이트 (측정 전용)")
    ap.add_argument("--json", action="store_true", help="기계 출력")
    args = ap.parse_args()
    try:
        d = _load_data_js()
    except Exception as e:
        print(f"❌ app/data.js를 읽지 못했습니다 ({e}) — build_app_data.py를 먼저 돌리세요.", file=sys.stderr)
        return 1

    fx = d.get("fx_exposure")
    if not fx:   # 아직 배선 전이거나 오프라인 빌드 — 여기서 직접 계산해 '0%'로 새지 않게 한다
        try:
            sys.path.insert(0, HERE)
            from fx_exposure import compute as fx_compute
            pf = json.load(open(os.path.join(HERE, "..", "portfolio.json"), encoding="utf-8"))
            t = d.get("totals") or {}
            fx = fx_compute(d.get("holdings") or [], float((d.get("fx") or {}).get("usdkrw") or 0),
                            t.get("cash_krw"), t.get("cash_usd"), pf.get("us_avg_fx_cost"))
        except Exception:
            fx = None
    res = compute(d.get("holdings") or [], d.get("totals") or {}, d.get("safety") or {},
                  fx, d.get("trades"), (d.get("orders") or []))
    res["as_of"] = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0

    f = res["facts"]
    print(f"── 포트폴리오 리스크 {res['score']}/100 ({res['level']}) · {res['as_of']} ──")
    for a in sorted(res["axes"], key=lambda a: -(a["contribution"] if a["contribution"] is not None else -1)):
        if a["value"] is None:
            print(f"  {a['label']:<8} {'미측정':<12} (가중 {a['weight']}% → 분모에서 제외)")
            continue
        bar = "█" * int(a["value"] / 10) + "·" * (10 - int(a["value"] / 10))
        print(f"  {a['label']:<8} {bar} {a['value']:>3}  (가중 {a['weight']}% → 기여 {a['contribution']:>4.1f})")
    print(f"\n  최대 {f['top']} {f['top_weight']}% · 테마 {f['top_sector']} {f['top_sector_weight']}% · "
          f"달러 {f['usd_weight'] if f['usd_weight'] is not None else '미측정'}% · ⭐2이하 {f['low_star_weight']}% · 현금 {f['cash_weight']}%")
    print(f"\n── 인사이트 {len(res['insights'])}건 ──")
    icon = {"danger": "🔴", "warning": "🟠", "info": "🔵", "positive": "🟢"}
    for i in res["insights"]:
        print(f"  {icon[i['level']]} {i['title']}\n     {i['detail']}")
    print(f"\n  {res['disclaimer']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
