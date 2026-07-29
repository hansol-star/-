#!/usr/bin/env python3
"""financials.py — 보유 전종목 재무제표 통합 파사드 + 재무 플래그 + 펀더 서브스코어 (stdlib)

정훈 지시(2026-07-29 "우리 포트폴리오 기업들 재무제표도 다 보고 있나? 없으면 다 찾아").

이 레포는 시세·수급·심리·변동성·기술적·13F까지 46개 스크립트로 덮으면서 **재무제표만 비어
있었다**(대차대조표 0건·현금흐름표 0건). 매일 "오늘 뭐가 움직였나"에 최적화된 나머지 매일
안 바뀌는 "이 회사가 뭘 버는가"가 계속 밀린 결과. 이 스크립트가 그 구멍을 메운다.

■ 소스 3단 폴백 (어느 하나가 죽어도 재무제표가 비지 않는다)
   US : EDGAR(1차 출처·상장 이래 전 시계열) → Yahoo(대조·보강) → FMP(TTM 파생, 화이트리스트만)
   KR : Yahoo(무키 백본·23/23 계정) → DART(1차 출처 감사, 환경변수 DART_API_KEY) → 네이버 비율
   두 소스가 같은 계정에서 1% 초과로 갈리면 `source_conflict` 플래그 + 두 값 병기.

■ 재무 플래그 = 정훈 룰에 직결된 것만 (측정·경보 전용, 매수·매도 자동발동 아님)
   margin_trend_break  리스크룰 4 "메모리 정점 판정 = 마진 추세"의 기계화
   inventory_surge     재고가 매출보다 빨리 늘면 사이클 정점 선행 신호
   fcf_negative_turn   AI capex 과부하(ORCL·META·MSFT)
   debt_buildup        순부채 급증 — ORCL 레버리지 논지의 하드넘버
   receivable_divergence  매출채권이 매출보다 빨리 늘면 매출의 질 악화
   backlog_growth      계약부채 증가 = 강세 플래그(ANET·ORCL)
   dilution            희석주식수 증가

■ 펀더 서브스코어(0~100) = **부분 기계화**(정훈 7/29 승인)
   데이터로 채점 가능한 5축만 자동 산출: C(분기EPS)·A(연간EPS)·마진방향·FCF건전성·재무건전성.
   CANSLIM의 N(촉매)·L(주도주)·M(시장방향)은 **PM 판단으로 남긴다** — 크래시 국면 재량 유지.
   최종 score = 서브스코어 + PM 가감. 축별 점수·투입수치를 같이 내보내 self-review가
   "그때 그 점수의 근거"를 후행검증할 수 있게 한다(지금까지는 불가능했다).

사용:
  python3 financials.py                      # 보유 전종목 표
  python3 financials.py --tickers MU,005930.KS
  python3 financials.py --flags              # 플래그만
  python3 financials.py --score              # 펀더 서브스코어
  python3 financials.py --all --save         # data/app/financials.json 갱신
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "data", "app", "financials.json")

import edgar_facts as E
import yahoo_facts as Y

# 보유 15종목 (VOO=ETF는 재무제표 대상 아님 → 14종목이 커버 대상)
US = ["NVDA", "MU", "AAPL", "MSFT", "ANET", "AVGO", "GOOGL", "META", "ORCL"]
KR = ["005930.KS", "066570.KS", "454910.KQ", "005380.KS", "035420.KS"]
ETF = ["VOO"]
ALL = US + KR


# ─────────────────────────────────────────── 파생지표

def _pct(new, old):
    if new is None or old in (None, 0):
        return None
    return (new - old) / abs(old) * 100.0


def _ratio(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


def derive(rows: list[dict], prior: list[dict]) -> list[dict]:
    """각 기간에 마진·회전·성장률을 붙인다. prior = 같은 종목의 전체 시계열(YoY 계산용)."""
    by_end = {r["end"]: r for r in prior}
    ends = sorted(by_end, reverse=True)
    out = []
    for r in rows:
        d = dict(r)
        rev = r.get("revenue")
        d["gross_margin"] = _m(_ratio(r.get("gross_profit"), rev))
        d["op_margin"] = _m(_ratio(r.get("operating_income"), rev))
        d["net_margin"] = _m(_ratio(r.get("net_income"), rev))
        d["fcf_margin"] = _m(_ratio(r.get("fcf"), rev))
        d["roe"] = _m(_ratio(r.get("net_income"), r.get("equity")))
        d["debt_to_equity"] = _m(_ratio(r.get("total_debt"), r.get("equity")))
        d["current_ratio"] = _m(_ratio(r.get("assets_current"), r.get("liabilities_current")))
        cash, debt = r.get("cash"), r.get("total_debt")
        d["net_cash"] = (cash - debt) if (cash is not None and debt is not None) else None
        # YoY = 4기 전(분기) / 1기 전(연간) — ends는 내림차순
        try:
            i = ends.index(r["end"])
        except ValueError:
            i = -1
        lag = 4 if r.get("period") == "quarterly" else 1
        base = by_end.get(ends[i + lag]) if 0 <= i and i + lag < len(ends) else None
        if base:
            d["revenue_yoy"] = _m(_pct(rev, base.get("revenue")))
            d["eps_yoy"] = _m(_pct(r.get("eps_diluted"), base.get("eps_diluted")))
            d["net_income_yoy"] = _m(_pct(r.get("net_income"), base.get("net_income")))
            d["inventory_yoy"] = _m(_pct(r.get("inventory"), base.get("inventory")))
            d["receivables_yoy"] = _m(_pct(r.get("receivables"), base.get("receivables")))
            d["shares_yoy"] = _m(_pct(r.get("shares_diluted"), base.get("shares_diluted")))
            d["deferred_yoy"] = _m(_pct(r.get("deferred_revenue"), base.get("deferred_revenue")))
        out.append(d)
    return out


def _m(v, nd=4):
    """반올림만 — 스케일은 건드리지 않는다(마진은 비율 0~1, 성장률은 %)."""
    return None if v is None else round(v, nd)


# ─────────────────────────────────────────── 수집

def collect(ticker: str, cmap=None, op=None, crumb=None) -> dict:
    """단일 종목 수집 — 지역별 소스 우선순위 적용 + 교차검증."""
    t = ticker.upper()
    if t in ETF:
        return {"ticker": t, "region": "US", "depth": "n/a",
                "note": "ETF — 개별 재무제표 대상 아님(보유 지수의 구성종목 재무가 실체)"}

    is_kr = t.endswith((".KS", ".KQ"))
    primary, cross = None, None
    if is_kr:
        primary = Y.fetch(t, op, crumb)
        cross = _dart(t)                      # 키 있을 때만 실제 조회
    else:
        primary = E.fetch(t, cmap)
        cross = Y.fetch(t, op, crumb)

    if primary.get("_error"):
        # 1차가 죽으면 2차로 승격(폴백의 존재 이유)
        if cross and not cross.get("_error"):
            cross["_fallback_from"] = primary.get("_error")
            primary, cross = cross, None
        else:
            return {"ticker": t, "_error": primary.get("_error")}

    rec = dict(primary)
    rec["annual"] = derive(primary["annual"], primary["annual"])
    rec["quarterly"] = derive(primary["quarterly"], primary["quarterly"])
    rec["cross_source"] = (cross or {}).get("source")
    rec["source_conflict"] = _conflicts(primary, cross) if cross and not cross.get("_error") else []
    return rec


def _dart(ticker: str) -> dict | None:
    """DART 1차 출처 감사 — 키(DART_API_KEY)가 환경에 있을 때만.

    ⚠️ 키는 조회 전용이며 파일에 저장하지 않는다(토스 키와 동일 취급).
    키가 없으면 조용히 None — Yahoo 백본만으로 재무제표는 이미 채워진다.
    """
    if not os.environ.get("DART_API_KEY", "").strip():
        return None
    try:
        import dart_facts as D
        return D.fetch(ticker)
    except Exception as e:
        return {"_error": f"DART 조회 실패: {str(e)[:80]}"}


def _conflicts(a: dict, b: dict, tol: float = 1.0) -> list[dict]:
    """두 소스 최신 연간의 동일 계정 이격(>tol%) 목록 — 단일 출처 금지 룰의 기계화."""
    if not a.get("annual") or not b.get("annual"):
        return []
    ra, rb = a["annual"][0], b["annual"][0]
    if ra.get("end") != rb.get("end"):
        return []
    out = []
    for k in ("revenue", "operating_income", "net_income", "assets", "liabilities",
              "equity", "cash", "inventory", "cfo"):
        va, vb = ra.get(k), rb.get(k)
        if va is None or vb is None or va == 0:
            continue
        gap = abs(va - vb) / abs(va) * 100
        if gap > tol:
            out.append({"field": k, "end": ra["end"], "primary": va, "cross": vb,
                        "gap_pct": round(gap, 2)})
    return out


# ─────────────────────────────────────────── 재무 플래그

def flags(rec: dict) -> list[dict]:
    q = rec.get("quarterly") or []
    a = rec.get("annual") or []
    out: list[dict] = []

    def add(code, sev, msg, ev):
        out.append({"code": code, "severity": sev, "message": msg, "evidence": ev})

    # ① 마진 추세 꺾임 — 리스크룰 4의 기계화
    oms = [(r["end"], r.get("op_margin")) for r in q[:3] if r.get("op_margin") is not None]
    if len(oms) >= 3 and oms[0][1] < oms[1][1] < oms[2][1]:
        add("margin_trend_break", "high",
            f"영업마진 2분기 연속 하락 ({oms[2][1]:.1%}→{oms[1][1]:.1%}→{oms[0][1]:.1%})",
            [{"end": e, "op_margin": v} for e, v in oms])

    # ② 재고 급증 (매출보다 빨리)
    #    ⚠️ 중요도 하한 — 재고가 매출의 2% 미만이면 증가율이 아무리 커도 의미 없다.
    #    (NAVER 재고 202억 = 매출의 0.2%인데 +50.4%로 🔴가 떴다. 플랫폼 기업엔 재고 개념이
    #     사실상 없으므로 사이클 신호로 읽으면 오독이다.)
    if q:
        r = q[0]
        iy, ry = r.get("inventory_yoy"), r.get("revenue_yoy")
        inv, rev = r.get("inventory"), r.get("revenue")
        material = inv is not None and rev not in (None, 0) and (inv / rev) >= 0.02
        if material and iy is not None and ry is not None and iy > 20 and iy - ry > 15:
            add("inventory_surge", "high",
                f"재고 YoY +{iy:.1f}% 가 매출 YoY +{ry:.1f}% 를 {iy-ry:.1f}%p 초과 — 사이클 정점 선행신호",
                [{"end": r["end"], "inventory_yoy": iy, "revenue_yoy": ry}])

    # ③ FCF 적자 전환
    fs = [(r["end"], r.get("fcf")) for r in a[:2] if r.get("fcf") is not None]
    if len(fs) == 2 and fs[0][1] < 0 <= fs[1][1]:
        add("fcf_negative_turn", "high",
            f"연간 FCF 흑→적 전환 ({fs[1][1]/1e9:,.1f}B → {fs[0][1]/1e9:,.1f}B) — capex 과부하",
            [{"end": e, "fcf": v} for e, v in fs])

    # ④ 순부채 급증
    ns = [(r["end"], r.get("net_cash")) for r in a[:2] if r.get("net_cash") is not None]
    if len(ns) == 2 and ns[0][1] < ns[1][1] and ns[1][1] != 0:
        drop = ns[1][1] - ns[0][1]
        if drop > abs(ns[1][1]) * 0.3:
            add("debt_buildup", "med",
                f"순현금 {ns[1][1]/1e9:,.1f}B → {ns[0][1]/1e9:,.1f}B (1년 새 {drop/1e9:,.1f}B 악화)",
                [{"end": e, "net_cash": v} for e, v in ns])

    # ⑤ 매출채권 괴리 (매출의 질)
    if q:
        r = q[0]
        ry_, ay = r.get("revenue_yoy"), r.get("receivables_yoy")
        if ry_ is not None and ay is not None and ay - ry_ > 20:
            add("receivable_divergence", "med",
                f"매출채권 YoY +{ay:.1f}% 가 매출 YoY +{ry_:.1f}% 를 크게 상회 — 매출의 질 점검",
                [{"end": r["end"], "receivables_yoy": ay, "revenue_yoy": ry_}])

    # ⑥ 백로그(계약부채) 증가 = 강세
    if q and q[0].get("deferred_yoy") is not None and q[0]["deferred_yoy"] > 15:
        add("backlog_growth", "bull",
            f"계약부채(선수금·백로그) YoY +{q[0]['deferred_yoy']:.1f}% — 수주 잔고 확대",
            [{"end": q[0]["end"], "deferred_yoy": q[0]["deferred_yoy"]}])

    # ⑦ 희석
    if a and a[0].get("shares_yoy") is not None and a[0]["shares_yoy"] > 2:
        add("dilution", "low", f"희석주식수 YoY +{a[0]['shares_yoy']:.1f}%",
            [{"end": a[0]["end"], "shares_yoy": a[0]["shares_yoy"]}])

    if rec.get("source_conflict"):
        add("source_conflict", "med",
            f"두 소스 간 {len(rec['source_conflict'])}개 계정 이격 — 1차 출처 채택, 수치 인용 시 병기",
            rec["source_conflict"][:5])
    return out


# ─────────────────────────────────────────── 펀더 서브스코어 (부분 기계화)

def subscore(rec: dict) -> dict:
    """데이터로 채점 가능한 5축만 0~100. N·L·M(촉매·주도주·시장)은 PM 몫."""
    q = rec.get("quarterly") or []
    a = rec.get("annual") or []
    axes: dict[str, dict] = {}

    def ax(name, pts, cap, why):
        axes[name] = {"score": None if pts is None else round(pts, 1), "max": cap, "why": why}

    # C — 분기 EPS YoY (오닐: +25% 이상이 기준선)
    c = q[0].get("eps_yoy") if q else None
    ax("C_분기EPS", None if c is None else max(0, min(25, 12.5 + c / 4)), 25,
       "—" if c is None else f"분기 희석EPS YoY {c:+.1f}%")

    # A — 연간 EPS YoY
    an = a[0].get("eps_yoy") if a else None
    ax("A_연간EPS", None if an is None else max(0, min(25, 12.5 + an / 4)), 25,
       "—" if an is None else f"연간 희석EPS YoY {an:+.1f}%")

    # 마진 방향 (최근 3분기 영업마진 기울기)
    oms = [r.get("op_margin") for r in q[:3] if r.get("op_margin") is not None]
    if len(oms) >= 2:
        delta = (oms[0] - oms[-1]) * 100  # %p
        ax("마진방향", max(0, min(20, 10 + delta * 2)), 20, f"영업마진 {delta:+.2f}%p (최근 {len(oms)}분기)")
    else:
        ax("마진방향", None, 20, "—")

    # FCF 건전성 (연간 FCF 마진)
    fm = a[0].get("fcf_margin") if a else None
    ax("FCF건전성", None if fm is None else max(0, min(15, 7.5 + fm * 50)), 15,
       "—" if fm is None else f"FCF 마진 {fm*100:+.1f}%")

    # 재무건전성 (순현금 / 부채비율)
    nc = a[0].get("net_cash") if a else None
    de = a[0].get("debt_to_equity") if a else None
    if nc is not None or de is not None:
        s = 7.5
        if nc is not None:
            s += 4 if nc > 0 else -3
        if de is not None:
            s += 3.5 if de < 0.5 else (0 if de < 1.5 else -4)
        ax("재무건전성", max(0, min(15, s)), 15,
           f"순현금 {'+' if (nc or 0) > 0 else ''}{(nc or 0)/1e9:,.1f}B · D/E {de if de is None else round(de,2)}")
    else:
        ax("재무건전성", None, 15, "—")

    got = [v["score"] for v in axes.values() if v["score"] is not None]
    cap = sum(v["max"] for v in axes.values() if v["score"] is not None)
    # 채점 가능한 축만으로 100점 환산 (결측 축은 점수를 깎지 않는다 — 추측 금지)
    total = round(sum(got) / cap * 100, 1) if cap else None
    return {"fund_subscore": total, "graded_weight": cap, "axes": axes,
            "note": "CANSLIM의 N(촉매)·L(주도주)·M(시장방향)은 미채점 — PM 가감 몫"}


# ─────────────────────────────────────────── 실행

def build_all(tickers: list[str]) -> dict:
    cmap = E.cik_map()
    op = Y._opener()
    crumb = Y._crumb(op)
    recs, errors = {}, {}
    import time
    for i, t in enumerate(tickers):
        if i:
            time.sleep(0.6)
        r = collect(t, cmap, op, crumb)
        if r.get("_error"):
            errors[t] = r["_error"]
            continue
        r["flags"] = flags(r)
        r.update(subscore(r))
        recs[t] = r
    return {"updated": dt.date.today().isoformat(), "covered": sorted(recs),
            "errors": errors, "stocks": recs}


def save(data: dict) -> str:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    slim = {"updated": data["updated"], "covered": data["covered"], "errors": data["errors"],
            "stocks": {}}
    for t, r in data["stocks"].items():
        slim["stocks"][t] = {
            "ticker": t, "name": r.get("name"), "region": r.get("region"),
            "currency": r.get("currency"), "source": r.get("source"),
            "cross_source": r.get("cross_source"), "depth": r.get("depth"),
            "as_of": r.get("as_of"),
            "annual": r.get("annual", [])[:5],        # 앱·보고서 소비용 요약(원본은 data/financials/)
            "quarterly": r.get("quarterly", [])[:8],
            "flags": r.get("flags", []),
            "fund_subscore": r.get("fund_subscore"),
            "graded_weight": r.get("graded_weight"),
            "axes": r.get("axes"),
            "source_conflict": r.get("source_conflict", []),
        }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=1)
    return OUT


def main() -> int:
    ap = argparse.ArgumentParser(description="보유 전종목 재무제표 통합")
    ap.add_argument("--tickers")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--flags", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    tickers = [t.strip() for t in a.tickers.split(",")] if a.tickers else ALL
    data = build_all(tickers)

    if a.save:
        print(f"💾 {save(data)}")
    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return 0

    print(f"\n📑 재무제표 커버리지 {len(data['covered'])}/{len(tickers)}  (기준일 {data['updated']})")
    if data["errors"]:
        for t, e in data["errors"].items():
            print(f"   ❌ {t}: {e}")

    if a.score:
        print("\n[펀더 서브스코어 — 데이터 채점분만. N·L·M은 PM 몫]")
        print(" 종목        서브스코어  채점가중  축별")
        for t, r in data["stocks"].items():
            ax = " · ".join(f"{k.split('_')[-1]} {v['score']}" for k, v in r["axes"].items()
                            if v["score"] is not None)
            print(f" {t:<11} {str(r['fund_subscore']):>9}  {r['graded_weight']:>6}   {ax}")
        return 0

    if a.flags:
        print("\n[재무 플래그]")
        for t, r in data["stocks"].items():
            if not r["flags"]:
                continue
            print(f"\n {t} ({r.get('name')})")
            for f in r["flags"]:
                icon = {"high": "🔴", "med": "🟡", "low": "⚪", "bull": "🟢"}.get(f["severity"], "•")
                print(f"   {icon} [{f['code']}] {f['message']}")
        return 0

    for t, r in data["stocks"].items():
        unit = 1e8 if r.get("region") == "KR" else 1e6
        lbl = "억원" if r.get("region") == "KR" else "백만USD"
        aa = r.get("annual", [])
        print(f"\n═══ {t} {r.get('name')} — {r.get('source')} "
              f"(연간 {len(aa)}기 · 분기 {len(r.get('quarterly',[]))}기) · 서브스코어 {r.get('fund_subscore')}")
        print(f"  [연간 {lbl}] 기간말        매출     영업이익   영업마진    자산      부채"
              f"      FCF     순현금")
        for w in aa[:3]:
            om = "—" if w.get("op_margin") is None else f"{w['op_margin']*100:.1f}%"
            g = lambda k: "—" if w.get(k) is None else f"{w[k]/unit:,.0f}"  # noqa: E731
            print(f"              {w['end']} {g('revenue'):>11} {g('operating_income'):>10}"
                  f" {om:>8} {g('assets'):>11} {g('liabilities'):>10} {g('fcf'):>10} {g('net_cash'):>10}")
        for f in r.get("flags", []):
            icon = {"high": "🔴", "med": "🟡", "low": "⚪", "bull": "🟢"}.get(f["severity"], "•")
            print(f"   {icon} {f['message']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
