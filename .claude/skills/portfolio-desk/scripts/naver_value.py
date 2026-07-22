#!/usr/bin/env python3
"""naver_value.py — 네이버 재무·컨센으로 밸류에이션 & '선반영 여부' 판단 (stdlib·무키)

정훈 지시(2026-07-22 "각 기업 영업이익 등 발표자료 분석해서 주가 가치로도 판단,
앞으로의 가치가 반영이 다 된 상태인지"). 네이버가 봉·수급뿐 아니라 **재무 3개년 실적 +
2026(E) 컨센**과 **목표주가·투자의견**을 무키로 준다 → 이걸로 '미래가치 선반영' 정량 판독.

두 소스:
  ① m.stock.naver.com/api/stock/{code}/finance/annual
     = 매출·영업이익·영업이익률·순이익·EPS·PER·PBR·ROE 3개년 실적 + 2026.12(E, isConsensus=Y).
  ② m.stock.naver.com/api/stock/{code}/integration → consensusInfo(목표가·투자의견) + totalInfos(추정PER/EPS).

핵심 산출 = **선반영 판단**(미래 가치가 주가에 얼마나 들어왔나):
  · 미반영 여지  = 포워드PER ≪ 트레일링PER + 강한 실적성장 + 목표가 상단 여유 + 마진 가속.
  · 선반영/고평가 = 포워드PER 높음 + EPS 정체·하락 or 마진 둔화 + 목표가 여유 적음.
  · 밸류트랩 경계 = 저PER인데 실적·마진 하락(싼 데는 이유).
  · 내러티브(보류) = 적자·PER 무의미(모멘텀 종목).

⚠️ 냉정 경계: 삼성·하이닉스처럼 2026E 영업이익 +수백%·마진 급점프는 **컨센이 공격적**이다 →
"포워드 저PER = 싸다"는 **추정 실현 조건부**. 리스크는 배수가 아니라 추정치. 이 플래그를 항상 병기.
별점·매수존 정본은 여전히 펀더 스코어(컨센·FMP) — 이 모듈은 그 '선반영' 축을 정량화하는 보조 렌즈.

사용:
  python3 naver_value.py                 # 보유 국내 5 + 하닉
  python3 naver_value.py --code 005930   # 단일
  python3 naver_value.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

BASE_M = "https://m.stock.naver.com/api/stock/{code}/{path}"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile Safari"

KR = [("삼성전자", "005930"), ("LG전자", "066570"), ("두산로보틱스", "454910"),
      ("현대차", "005380"), ("NAVER", "035420"), ("SK하이닉스", "000660")]


def _get(url: str, tries: int = 4):
    delay = 2.0
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Referer": "https://m.stock.naver.com/"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
            if i < tries - 1:
                time.sleep(delay)
                delay *= 1.8
    return None


def _pf(s):
    """'3,336,059'→3336059.0 · '52.32'→52.32 · '5.55배'→5.55 · '-'/'N/A'/None→None."""
    if s is None:
        return None
    s = str(s).replace(",", "").replace("배", "").replace("원", "").replace("%", "").strip()
    if s in ("", "-", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fetch_financials(code: str) -> dict | None:
    """finance/annual 파싱 → {periods:[(key,title,is_est)], rows:{title:[vals per period]}}."""
    d = _get(BASE_M.format(code=code, path="finance/annual"))
    if not isinstance(d, dict):
        return None
    fi = d.get("financeInfo") or {}
    tl = fi.get("trTitleList") or []
    if not tl:
        return None
    periods = [(t["key"], t.get("title", t["key"]), t.get("isConsensus") == "Y") for t in tl]
    rows = {}
    for r in fi.get("rowList", []):
        cols = r.get("columns", {})
        rows[r["title"]] = [_pf(cols.get(k, {}).get("value")) for k, _, _ in periods]
    return {"periods": periods, "rows": rows}


def fetch_consensus(code: str) -> dict:
    """integration → 목표가·투자의견·추정PER/EPS·현재가·트레일링 배수."""
    d = _get(BASE_M.format(code=code, path="integration")) or {}
    ci = d.get("consensusInfo") or {}
    ti = {x.get("code"): x.get("value") for x in (d.get("totalInfos") or [])}
    return {
        "name": d.get("stockName"),
        "recomm_mean": _pf(ci.get("recommMean")),        # 네이버 5=적극매수 … 1=적극매도(대형주 통상 4점대)
        "target_mean": _pf(ci.get("priceTargetMean")),
        "price": _pf(ti.get("closePrice")) or _pf(ti.get("lastClosePrice")),
        "per": _pf(ti.get("per")), "pbr": _pf(ti.get("pbr")),
        "eps": _pf(ti.get("eps")), "bps": _pf(ti.get("bps")),
        "cns_per": _pf(ti.get("cnsPer")), "cns_eps": _pf(ti.get("cnsEps")),
        "div_yield": _pf(ti.get("dividendYieldRatio")),
        "hi52": _pf(ti.get("highPriceOf52Weeks")), "lo52": _pf(ti.get("lowPriceOf52Weeks")),
    }


def _yoy(series):
    """연속 성장률(%) 리스트. None 안전. 적자→흑자 등 부호전환은 None(비율 무의미)."""
    out = []
    for a, b in zip(series, series[1:]):
        if a is None or b is None or a == 0 or a < 0:
            out.append(None)
        else:
            out.append(round(100 * (b - a) / a, 1))
    return out


def value_read(code: str, price: float | None = None) -> dict:
    fin = fetch_financials(code)
    con = fetch_consensus(code)
    out = {"code": code, "name": con.get("name")}
    px = price or con.get("price")
    out["price"] = px
    if not fin:
        out["_error"] = "네이버 재무 조회 실패"
        return out

    periods, rows = fin["periods"], fin["rows"]
    est_idx = [i for i, (_, _, e) in enumerate(periods) if e]
    act_idx = [i for i, (_, _, e) in enumerate(periods) if not e]
    labels = [t for _, t, _ in periods]

    def row(name):
        return rows.get(name, [None] * len(periods))

    op = row("영업이익")           # 억원
    opm = row("영업이익률")        # %
    eps = row("EPS")               # 원
    per = row("PER")               # 배
    sales = row("매출액")          # 억원
    roe = row("ROE")               # %

    # 영업이익 추세(실적 구간) + 2026E
    op_yoy = _yoy(op)
    op_act = [op[i] for i in act_idx]
    op_est = op[est_idx[0]] if est_idx else None
    last_act = act_idx[-1] if act_idx else None

    # 마진 방향(메모리 정점 프록시 — master.md §10-2)
    opm_act = [opm[i] for i in act_idx if opm[i] is not None]
    if len(opm_act) >= 2:
        margin_dir = "가속" if opm_act[-1] > opm_act[-2] else ("둔화" if opm_act[-1] < opm_act[-2] else "횡보")
    else:
        margin_dir = "n/a"

    # 트레일링 vs 포워드 PER
    trail_per = con.get("per") or (per[last_act] if last_act is not None else None)
    fwd_per = con.get("cns_per") or (per[est_idx[0]] if est_idx else None)
    # 컨센이 기대하는 EPS 성장(추정EPS / 최근실적EPS - 1)
    eps_last = eps[last_act] if last_act is not None else None
    cns_eps = con.get("cns_eps") or (eps[est_idx[0]] if est_idx else None)
    if eps_last and cns_eps and eps_last > 0:
        implied_g = round(100 * (cns_eps / eps_last - 1), 1)
    else:
        implied_g = None
    # 목표가 상단 여유
    tgt = con.get("target_mean")
    upside = round(100 * (tgt / px - 1), 1) if (tgt and px) else None
    # PEG류(포워드PER / 기대성장%)
    peg = round(fwd_per / implied_g, 2) if (fwd_per and implied_g and implied_g > 0) else None
    # EPS 방향(추정 vs 최근실적)
    if eps_last is not None and cns_eps is not None:
        eps_dir = "증가" if cns_eps > eps_last else ("감소" if cns_eps < eps_last else "정체")
    else:
        eps_dir = "n/a"

    # 컨센 공격성 플래그(포워드 저PER의 조건부성)
    aggressive = bool(implied_g is not None and implied_g > 100)
    est_margin = opm[est_idx[0]] if est_idx else None
    if est_margin and opm_act and opm_act[-1] and est_margin > 2 * opm_act[-1]:
        aggressive = True

    # 신고 실적 여부 — 2026E 영업이익이 과거 피크를 크게(>1.2x) 넘나(구조성장) vs 순환회복 구분
    prior_pos_op = [x for x in op_act if x is not None and x > 0]
    new_high_earn = bool(op_est and prior_pos_op and op_est > 1.2 * max(prior_pos_op))
    # 목표가 stale 의심 — 상단 과대(>50%)인데 실적 하락/둔화 = 크래시 후 애널 목표 미갱신 프록시
    target_stale = bool(upside is not None and upside > 50 and (eps_dir == "감소" or margin_dir == "둔화"))

    # ── 선반영 판단 ──────────────────────────────────────────────────────────
    loss_now = (eps_last is not None and eps_last <= 0) or (trail_per is not None and trail_per < 0)
    cheap_fwd = bool(trail_per and fwd_per and fwd_per < 0.7 * trail_per)  # 포워드≪트레일링
    strong_g = implied_g is not None and implied_g >= 30
    stall = (eps_dir == "감소") or (margin_dir == "둔화" and implied_g is not None and implied_g < 15)
    credible_room = bool(upside is not None and upside >= 20 and not target_stale)  # stale이면 상단 무시

    if loss_now or fwd_per is None:
        verdict, tilt = "내러티브(적자·PER 무의미 — 실적 아닌 스토리에 프라이싱)", 0
    elif new_high_earn and strong_g and margin_dir == "가속":
        # 구조적 성장(신고 실적·마진 가속)인데 포워드 저PER → 진짜 미반영 룸(단 컨센 조건부)
        verdict, tilt = "미반영 여지(신고 실적·마진 가속 — 컨센 실현 시 재평가 룸)", 2
    elif stall and fwd_per >= 12:
        verdict, tilt = "선반영·고평가 경계(성장 정체·EPS감소인데 배수 부담)", -2
    elif trail_per and trail_per < 8 and stall:
        verdict, tilt = "저평가나 실적 하락(밸류트랩 경계 — 싼 데는 이유)", -1
    elif cheap_fwd and strong_g and not new_high_earn:
        # 포워드 저PER이지만 신고 실적 아님 = 바닥실적 순환회복(트레일링PER 착시)
        verdict, tilt = "부분 반영(순환 회복 — 구조성장 아님·트레일링PER 착시 주의)", 1
    elif credible_room and strong_g:
        verdict, tilt = "부분 반영(성장·목표 여유 있으나 배수 일부 반영)", 1
    else:
        verdict, tilt = "대체로 적정 반영", 0

    out.update({
        "labels": labels,
        "sales": sales, "op": op, "op_yoy": op_yoy, "op_margin": opm, "op_est": op_est,
        "eps": eps, "per_series": per, "roe": roe,
        "trail_per": trail_per, "fwd_per": fwd_per,
        "implied_growth": implied_g, "peg": peg, "eps_dir": eps_dir,
        "margin_dir": margin_dir, "est_margin": est_margin,
        "target_mean": tgt, "upside": upside, "recomm_mean": con.get("recomm_mean"),
        "div_yield": con.get("div_yield"), "pbr": con.get("pbr"),
        "aggressive_consensus": aggressive,
        "new_high_earnings": new_high_earn, "target_stale": target_stale,
        "priced_in": verdict, "value_tilt": tilt,
    })
    return out


def _fnum(x, suf=""):
    if x is None:
        return "n/a"
    if abs(x) >= 10000:
        return f"{x:,.0f}{suf}"
    return f"{x:g}{suf}"


def fmt(o: dict) -> str:
    if o.get("_error"):
        return f"■ {o.get('name') or o['code']}[{o['code']}]: {o['_error']}"
    L = []
    L.append(f"■ {o['name']}[{o['code']}]  {_fnum(o['price'])}원  →  선반영: {o['priced_in']}"
             + (f"  ⚠️컨센 공격적" if o.get("aggressive_consensus") else ""))
    labels = o["labels"]
    # 영업이익 추세(억원) + YoY
    op = o["op"]
    seg = []
    for i, lab in enumerate(labels):
        v = op[i]
        est = "(E)" if i == len(labels) - 1 else ""
        seg.append(f"{lab[:7]}{est} {_fnum(v)}")
    L.append("   영업이익(억): " + " → ".join(seg))
    yoy = o["op_yoy"]
    if yoy:
        L.append("   영업이익 YoY%: " + " · ".join(_fnum(y, "%") for y in yoy)
                 + f"  (마진 {o['margin_dir']}, 2026E 마진 {_fnum(o['est_margin'],'%')})")
    # 밸류에이션 요약
    L.append(f"   밸류: 트레일링PER {_fnum(o['trail_per'],'배')} → 포워드PER {_fnum(o['fwd_per'],'배')}"
             f"  ·  컨센 기대EPS성장 {_fnum(o['implied_growth'],'%')}"
             f"  ·  PEG {o['peg'] if o['peg'] is not None else 'n/a'}  ·  PBR {_fnum(o['pbr'],'배')}")
    stale = "  ⚠️목표가 stale 의심(크래시 미반영)" if o.get("target_stale") else ""
    L.append(f"   컨센: 목표가 {_fnum(o['target_mean'])}원(상단 {_fnum(o['upside'],'%')}{stale})"
             f"  ·  투자의견 {o['recomm_mean']}(네이버 5=적극매수)"
             f"  ·  배당수익 {_fnum(o['div_yield'],'%')}  ·  EPS방향 {o['eps_dir']}")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="네이버 재무·컨센 밸류에이션·선반영 판단(무키)")
    ap.add_argument("--code", help="종목코드(쉼표구분). 없으면 보유 국내 5 + 하닉")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.code:
        uni = []
        for tok in args.code.split(","):
            tok = tok.strip().split(".")[0]
            name = next((n for n, c in KR if c == tok), tok)
            uni.append((name, tok))
    else:
        uni = KR

    results = [value_read(c) for _, c in uni]
    for r, (n, _) in zip(results, uni):
        r.setdefault("name", n)
        time.sleep(0.3)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return 0

    print("네이버 재무·컨센 밸류에이션 — 선반영(미래가치 반영) 판독 (naver_value.py · 측정·판독 전용)")
    print("=" * 84)
    for r in results:
        print(fmt(r))
        print("-" * 84)
    print("※ 포워드 저PER·목표 상단은 '컨센 실현 조건부'(공격적 추정일수록 리스크는 배수 아닌 추정치). "
          "별점·매수존 정본은 펀더 스코어. 최종 결정 정훈.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
