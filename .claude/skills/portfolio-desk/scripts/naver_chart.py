#!/usr/bin/env python3
"""naver_chart.py — 네이버 네이티브 '한국식' 차트 리더 (가격 TA + 수급 융합·stdlib·무키)

정훈 지시(2026-07-22 "네이버 연결 이용해 주식 차트 분석하는 법 공부하고 만들어봐").
기존 chart_read.py는 **Yahoo OHLC**만 읽어 한국 차트의 핵심인 **수급(투자자별 매매동향·
외국인 지분율)**이 판독에 안 붙어 있었다. Yahoo엔 한국 수급이 아예 없다 → 이 모듈이 그 빈틈을 닫는다.

두 개의 무키 네이버 소스(데이터센터 IP 정상):
  ① api.stock.naver.com/chart/domestic/item/{code}/{day|week}
     = 봉별 OHLCV + **foreignRetentionRate(외국인 지분율)** — 6.5년 심층·Yahoo엔 없음.
  ② m.stock.naver.com/api/stock/{code}/trend  (naver_flows 재사용)
     = 최근 ~60거래일 외인/기관/개인 순매수 **수량** + 외인보유율.

판독 = 두 층의 융합:
  · 가격 층 — chart_read.read()에 네이버 봉을 **주입**해 13신호 엔진을 그대로 재사용
    (엔진 단일화 — Yahoo/네이버 어느 소스든 같은 컨플루언스 로직). RS 벤치는 코스피.
  · 수급 층 — 외국인 지분율 추세(Δ5/20/60·1년 %ile) + 순매수 연속일·5/20일 누적·
    기관 동행/역행·개인 대치 → 매집/분산 판정.

⚠️ 냉정한 경계(study_log 2026-07-22 교차검증):
  · "외인 순매수일 코스피 89.7% 상승"은 **같은 날 동행상관**이지 매매가능 선행엣지가 아님
    (학술: 외국인 추종수익률 < 코스피). flow_edge.py가 Δ외인지분율의 forward 엣지를 정직 측정.
  · 외인 지분율은 'Sell Korea' 중에도 비핵심 처분·핵심(반도체) 유지로 오를 수 있음(소진율 착시).
  · 프로그램/선물 오버레이 — 현물 중립인 날도 외인 선물매도가 차익거래로 지수를 끌어내림.
  ∴ 수급은 '동행 강도·매집분산 상태'의 서술 렌즈. 별점·매수존 정본은 여전히 펀더(컨센·FMP).

사용:
  python3 naver_chart.py                       # 보유 국내 5 + 하닉
  python3 naver_chart.py --code 005930         # 단일 종목(6자리 or 티커)
  python3 naver_chart.py --with-watch          # 국내 워치 포함
  python3 naver_chart.py --json                # 파이프라인용
  python3 naver_chart.py --verbose             # 피보나치·미너비니·수급 상세
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.request

try:
    import chart_read as cr
    import ta_core as ta  # noqa: F401  (chart_read가 이미 사용·여기선 존재확인)
except Exception as e:  # pragma: no cover
    sys.exit(f"[naver_chart] chart_read/ta_core 임포트 실패: {e}")

try:
    import naver_flows as nf  # 종목별 순매수 수량(무키) 재사용
except Exception:
    nf = None

try:
    import naver_value as nv  # [7/22] 영업이익·컨센 밸류에이션·선반영 판단 층
except Exception:
    nv = None

try:
    import market_data as md  # 유니버스(portfolio.json 정본 미러)
    _KR = md.HOLDINGS_KR
    _KR_WATCH = [(l, t) for l, t in md.WATCHLIST if t.endswith((".KS", ".KQ"))]
except Exception:
    md = None
    _KR = [("삼성전자", "005930.KS"), ("LG전자", "066570.KS"),
           ("두산로보틱스", "454910.KS"), ("현대차", "005380.KS"), ("NAVER", "035420.KS")]
    _KR_WATCH = [("원익IPS", "240810.KQ"), ("테스", "095610.KQ")]

WATCH_FLOW = [("SK하이닉스", "000660.KS")]  # 하닉 수급 트리거(CLAUDE.md foreign_hynix)

CHART = "https://api.stock.naver.com/chart/domestic/item/{code}/{period}"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile Safari"


# ── 유틸 ────────────────────────────────────────────────────────────────────
def code_of(ticker: str) -> str:
    """'005930.KS' → '005930' · 이미 6자리면 그대로."""
    return ticker.split(".")[0]


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


def fetch_naver_ohlc(code: str, period: str = "day", lookback_days: int = 620) -> dict | None:
    """네이버 차트 API에서 시간순 OHLCV + 외국인지분율(frr). period=day|week|month."""
    end = dt.date.today()
    start = end - dt.timedelta(days=lookback_days)
    url = CHART.format(code=code, period=period) + (
        f"?startDateTime={start.strftime('%Y%m%d')}0000"
        f"&endDateTime={end.strftime('%Y%m%d')}0000")
    arr = _get(url)
    if not isinstance(arr, list) or len(arr) < 30:
        return None
    o = h = l = c = v = None  # noqa: E741
    O, H, L, C, V, F, D = [], [], [], [], [], [], []
    for r in arr:
        cp = r.get("closePrice")
        op = r.get("openPrice")
        hp = r.get("highPrice")
        lp = r.get("lowPrice")
        if None in (cp, op, hp, lp):
            continue
        O.append(float(op)); H.append(float(hp)); L.append(float(lp)); C.append(float(cp))
        V.append(int(r.get("accumulatedTradingVolume") or 0))
        F.append(r.get("foreignRetentionRate"))  # % or None
        D.append(r.get("localDate"))
    if len(C) < 30:
        return None
    return {"o": O, "h": H, "l": L, "c": C, "v": V, "frr": F, "dates": D}


# ── 수급 층 ──────────────────────────────────────────────────────────────────
def _pctile(series, val):
    xs = [x for x in series if x is not None]
    if not xs:
        return None
    return round(100 * sum(1 for x in xs if x <= val) / len(xs), 1)


def frr_trend(frr: list, dates: list) -> dict | None:
    """외국인 지분율 추세: Δ5/20/60봉 + 1년 %ile + 방향 판정.
    지분율(보유주식/발행주식)은 순매수 '수량' 방향의 심층 프록시(억원 net보다 float·가격 착시 적음)."""
    f = [x for x in frr if x is not None]
    if len(f) < 25:
        return None
    cur = f[-1]

    def delta(n):
        return round(cur - f[-1 - n], 3) if len(f) > n else None

    d5, d20, d60 = delta(5), delta(20), delta(60)
    win = f[-250:] if len(f) >= 250 else f
    pct = _pctile(win, cur)
    ref = d20 if d20 is not None else (d5 or 0)
    if ref > 0.05:
        direction = "상승(외인 매집)"
    elif ref < -0.05:
        direction = "하락(외인 이탈)"
    else:
        direction = "횡보"
    return {"cur": round(cur, 2), "d5": d5, "d20": d20, "d60": d60,
            "pct_1y": pct, "direction": direction}


def flow_read(code: str, avg_vol: float | None = None) -> dict | None:
    """최근 ~60거래일 외인/기관/개인 순매수 수량 → 연속일·5/20일 누적·동행/역행·대치·매집분산.

    ⚠️ 부호만 보면 미미한 순매수(하루 거래량의 몇 %)를 '매집'으로 과대평가한다 →
    20일 누적을 **평균거래량 대비 days-of-volume**으로 정규화, 임계(0.5일) 미만은 중립 처리.
    (LG전자 20d +3.7만주 = 하루 거래량 2%는 사실상 flat — 실전 판독 정합.)"""
    if nf is None:
        return None
    rows = nf.stock_flows(code, pages=2)  # 시간순(오래된→최신)
    rows = [r for r in rows if r.get("foreign_qty") is not None]
    if len(rows) < 5:
        return None

    def streak(key):
        s = 0
        sign = None
        for r in reversed(rows):
            q = r.get(key)
            if q is None or q == 0:
                break
            cur = 1 if q > 0 else -1
            if sign is None:
                sign = cur
            if cur != sign:
                break
            s += 1
        return sign or 0, s

    def cum(key, n):
        return sum((r.get(key) or 0) for r in rows[-n:])

    f_sign, f_streak = streak("foreign_qty")
    f5, f20 = cum("foreign_qty", 5), cum("foreign_qty", 20)
    o5, o20 = cum("organ_qty", 5), cum("organ_qty", 20)
    i5, i20 = cum("indiv_qty", 5), cum("indiv_qty", 20)

    # 크기 정규화 — 20d 순매수를 평균거래량 대비 '일수'로. 임계 0.5일 미만 = 방향 0(중립).
    THR = 0.5
    def dir_of(net):
        if not avg_vol or avg_vol <= 0:
            return (1 if net > 0 else -1 if net < 0 else 0), None
        dov = round(net / avg_vol, 2)  # days-of-volume(부호 유지)
        if abs(dov) < THR:
            return 0, dov
        return (1 if dov > 0 else -1), dov
    f_dir, f_dov = dir_of(f20)
    o_dir, o_dov = dir_of(o20)

    align = ("동행" if f_dir == o_dir else "역행") if (f_dir and o_dir) else "혼재/미미"
    # 개인 대치(방향 유의미할 때만)
    if f_dir < 0 and i20 > 0:
        retail = "개인이 외인 물량 받음(분산 경고)"
    elif f_dir > 0 and i20 < 0:
        retail = "개인이 외인에 매도(매집 우위)"
    else:
        retail = "대치 뚜렷치 않음"

    table = {
        (1, 1): ("쌍끌이 매집(외인+기관)", 2), (1, 0): ("외인 매집(기관 중립)", 1),
        (1, -1): ("외인 매집·기관 매도(역행)", 1), (0, 1): ("기관 매집(외인 중립)", 1),
        (0, 0): ("수급 중립(미미)", 0), (0, -1): ("기관 분산(외인 중립)", -1),
        (-1, 1): ("외인 분산·기관 매수(역행)", -1), (-1, 0): ("외인 분산(기관 중립)", -1),
        (-1, -1): ("쌍끌이 분산(외인+기관)", -2),
    }
    verdict, sup = table[(f_dir, o_dir)]

    return {"n_days": len(rows), "last_date": rows[-1]["date"],
            "foreign_streak": f_streak, "foreign_sign": f_sign,
            "f5": f5, "f20": f20, "o5": o5, "o20": o20, "i5": i5, "i20": i20,
            "f_dov": f_dov, "o_dov": o_dov, "align": align, "retail": retail,
            "verdict": verdict, "sup_score": sup,
            "foreign_hold_pct": rows[-1].get("foreign_hold_pct")}


def supply_bias(frr_t: dict | None, flow: dict | None) -> dict:
    """수급 종합: 지분율 추세(느린·구조) + 순매수 누적(빠른·전술) → 매집/분산 강도."""
    score = 0
    parts = []
    if flow:
        score += flow["sup_score"]
        parts.append(flow["verdict"])
        if flow["foreign_streak"] >= 3:
            tag = "매수" if flow["foreign_sign"] > 0 else "매도"
            parts.append(f"외인 {flow['foreign_streak']}일 연속{tag}")
    if frr_t:
        if "상승" in frr_t["direction"]:
            score += 1
        elif "하락" in frr_t["direction"]:
            score -= 1
        parts.append(f"지분율 {frr_t['direction']}")
    if score >= 2:
        bias = "강매집"
    elif score == 1:
        bias = "매집"
    elif score == 0:
        bias = "중립"
    elif score == -1:
        bias = "분산"
    else:
        bias = "강분산"
    return {"bias": bias, "score": score, "notes": parts}


# ── 융합 리드 ────────────────────────────────────────────────────────────────
def read(ticker: str, label: str = "", verbose: bool = False) -> dict:
    code = code_of(ticker)
    out = {"label": label or ticker, "ticker": ticker, "code": code}
    day = fetch_naver_ohlc(code, "day", 620)
    if not day:
        out["_error"] = "네이버 OHLC 조회 실패(코드/네트워크)"
        return out
    week = fetch_naver_ohlc(code, "week", 1400)
    # 가격 층 — 네이버 봉을 chart_read 엔진에 주입(티커로 넘겨 RS 벤치=코스피 정상해석).
    # chart_read의 52주 고저·MA200은 주입 슬라이스 '전체'로 계산 → Yahoo rng="1y"와 맞추려
    # 일봉은 최근 252봉(≈52주)만, 주봉은 최근 110주만 넘긴다(frr 심층은 아래서 day 전체 사용).
    price = cr.read(ticker, verbose=verbose,
                    ohlc={k: day[k][-252:] for k in ("o", "h", "l", "c", "v")},
                    weekly=({k: week[k][-110:] for k in ("o", "h", "l", "c", "v")} if week else None))
    # 수급 층 — 20d 순매수 크기 정규화용 평균거래량(최근 20봉)
    vv = [x for x in (day.get("v") or []) if x]
    avg_vol = (sum(vv[-20:]) / len(vv[-20:])) if vv else None
    ft = frr_trend(day.get("frr") or [], day.get("dates") or [])
    fl = flow_read(code, avg_vol)
    sb = supply_bias(ft, fl)
    # 융합 방향 — 가격 바이어스 부호 + 수급 부호
    price_dir = {"강세": 2, "약강세": 1, "혼조": 0, "중립": 0,
                 "약약세": -1, "약세": -2}.get(price.get("bias", "중립"), 0)
    combo = price_dir + sb["score"]
    if combo >= 3:
        fused = "가격·수급 정렬 강세"
    elif combo >= 1:
        fused = "완만 강세(정렬 약함)"
    elif combo <= -3:
        fused = "가격·수급 정렬 약세"
    elif combo <= -1:
        fused = "완만 약세"
    else:
        fused = "혼조(가격·수급 상충)"
    # 상충 강조 — 정보량 큰 케이스
    if price_dir <= -1 and sb["score"] >= 1:
        fused += " ※가격 약세인데 외인 매집(바닥 신호 후보)"
    elif price_dir >= 1 and sb["score"] <= -1:
        fused += " ※가격 강세인데 외인 분산(되돌림 경계)"

    # 가치 층 — 영업이익·컨센·선반영(구조 축, 타이밍과 별개 시야)
    px = day["c"][-1]
    val = nv.value_read(code, price=px) if nv else None

    out.update({"price": price, "frr_trend": ft, "flow": fl,
                "supply": sb, "fused": fused, "value": val,
                "synthesis": _synthesis(price_dir, sb["score"],
                                        (val or {}).get("value_tilt", 0),
                                        (val or {}).get("priced_in", ""), fused),
                "last_bar": (day.get("dates") or [None])[-1],
                "degraded_flow": fl is None})
    return out


def _synthesis(price_dir: int, sup_score: int, value_tilt: int,
               priced_in: str, fused: str) -> str:
    """3층 종합 — 구조(가치)와 국면(가격+수급)을 분리해 한 줄 판단(과신 금지·상충 병기)."""
    timing = price_dir + sup_score  # 타이밍 축(가격+수급)
    tim_txt = ("정렬 강세" if timing >= 3 else "완만 강세" if timing >= 1
               else "정렬 약세" if timing <= -3 else "완만 약세" if timing <= -1 else "혼조")
    val_txt = {2: "저평가(성장 미반영)", 1: "부분 반영", 0: "적정/보류",
               -1: "밸류트랩 경계", -2: "선반영·고평가"}.get(value_tilt, "적정/보류")
    # 조합 코멘트
    if value_tilt >= 1 and timing <= -1:
        note = "구조는 싸나 국면(수급·추세)은 아직 약함 → 분할·인내 구간(추격 금지)"
    elif value_tilt >= 1 and timing >= 1:
        note = "구조·국면 동반 우호 → 정훈 매수존서 트랜치 집행 후보"
    elif value_tilt <= -1 and timing >= 1:
        note = "국면은 강하나 밸류 선반영 → 반등 시 트림/차익 우위"
    elif value_tilt <= -1 and timing <= -1:
        note = "구조·국면 모두 부담 → 신규 진입 회피"
    else:
        note = "구조·국면 혼재 → 펀더 스코어·안전핀 우선"
    return f"구조(가치) {val_txt} · 국면(타이밍) {tim_txt} → {note}"


# ── 출력 ────────────────────────────────────────────────────────────────────
def _sig(n):
    return f"{n:+,}" if isinstance(n, (int, float)) else str(n)


def fmt(o: dict, verbose: bool = False) -> str:
    if o.get("_error"):
        return f"■ {o['label']}[{o['code']}]: {o['_error']}"
    L = []
    L.append(f"■ {o['label']}[{o['code']}]  (네이버 봉·마지막 {o.get('last_bar')})  →  융합: {o['fused']}")
    # 가격 층 — chart_read.fmt 재사용(심볼 라벨만 치환)
    pblock = cr.fmt(o["price"], verbose=verbose)
    pblock = pblock.replace(f"■ {o['price']['symbol']}", "  [가격층] ", 1)
    L.append(pblock)
    # 수급 층
    sb = o["supply"]
    L.append(f"  [수급층] 종합: {sb['bias']}(점수 {sb['score']:+}) — {' · '.join(sb['notes']) or 'n/a'}")
    ft = o.get("frr_trend")
    if ft:
        L.append(f"    외국인 지분율: {ft['cur']}%  (Δ5={_sig(ft['d5'])} Δ20={_sig(ft['d20'])} "
                 f"Δ60={_sig(ft['d60'])} · 1년 {ft['pct_1y']}%ile · {ft['direction']})")
    fl = o.get("flow")
    if fl:
        dov = (f"  [외인 20d={fl['f_dov']}일·기관 20d={fl['o_dov']}일 거래량]"
               if fl.get("f_dov") is not None else "")
        L.append(f"    순매수(수량·최근 {fl['n_days']}일 {fl['last_date']}): "
                 f"외인 5d {_sig(fl['f5'])}/20d {_sig(fl['f20'])} · "
                 f"기관 5d {_sig(fl['o5'])}/20d {_sig(fl['o20'])} · 개인 20d {_sig(fl['i20'])}{dov}")
        L.append(f"    수급 성격: {fl['verdict']} · 외인·기관 {fl['align']} · {fl['retail']}"
                 + (f" · 외인보유 {fl['foreign_hold_pct']}%" if fl.get("foreign_hold_pct") else ""))
    else:
        L.append("    순매수 수량: 조회불가(네이버 trend) — 지분율 추세만으로 수급 판독")
    # 가치 층
    val = o.get("value")
    if val and not val.get("_error") and nv is not None:
        agg = "  ⚠️컨센 공격적" if val.get("aggressive_consensus") else ""
        L.append(f"  [가치층] 선반영: {val['priced_in']}{agg}")
        op = val.get("op") or []
        labels = val.get("labels") or []
        if op and labels:
            seg = " → ".join(f"{labels[i][:7]}{'(E)' if i == len(labels)-1 else ''} "
                             f"{nv._fnum(op[i])}" for i in range(len(labels)))
            L.append(f"    영업이익(억): {seg}  (마진 {val.get('margin_dir')}, "
                     f"2026E {nv._fnum(val.get('est_margin'),'%')})")
        L.append(f"    밸류: 트레일링PER {nv._fnum(val.get('trail_per'),'배')} → "
                 f"포워드PER {nv._fnum(val.get('fwd_per'),'배')} · 기대EPS성장 "
                 f"{nv._fnum(val.get('implied_growth'),'%')} · "
                 f"PEG {val.get('peg') if val.get('peg') is not None else 'n/a'} · "
                 f"목표가 상단 {nv._fnum(val.get('upside'),'%')}"
                 + ("(⚠️stale)" if val.get("target_stale") else ""))
    elif val and val.get("_error"):
        L.append(f"  [가치층] {val['_error']}")
    # 종합
    if o.get("synthesis"):
        L.append(f"  ▶ 종합: {o['synthesis']}")
    return "\n".join(L)


def build_universe(args):
    if args.code:
        uni = []
        for tok in args.code.split(","):
            tok = tok.strip()
            if not tok:
                continue
            # 라벨 매칭(보유/워치에 있으면 이름 붙이기)
            label = tok
            for lab, tk in _KR + _KR_WATCH + WATCH_FLOW:
                if code_of(tk) == code_of(tok):
                    label = lab
                    break
            uni.append((label, tok if "." in tok else tok))
        return uni
    uni = list(_KR) + list(WATCH_FLOW)
    if args.with_watch:
        uni = list(_KR) + list(_KR_WATCH) + list(WATCH_FLOW)
    return uni


def main() -> int:
    ap = argparse.ArgumentParser(description="네이버 네이티브 한국식 차트 리더(가격+수급·무키)")
    ap.add_argument("--code", help="종목코드/티커(쉼표구분). 예: 005930 또는 005930.KS")
    ap.add_argument("--with-watch", action="store_true", help="국내 워치(원익IPS·테스 등) 포함")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    ap.add_argument("--verbose", action="store_true", help="피보나치·미너비니·스윙 상세")
    args = ap.parse_args()

    uni = build_universe(args)
    results = []
    for label, ticker in uni:
        results.append(read(ticker, label, verbose=args.verbose))
        time.sleep(0.5)  # 페이싱

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return 0

    print("네이버 네이티브 한국식 차트 리드 (naver_chart.py · 가격 TA + 수급 융합 · 측정·판독 전용)")
    print("=" * 82)
    for o in results:
        print(fmt(o, verbose=args.verbose))
        print("-" * 82)
    print("※ 수급은 '동행 강도·매집분산 상태'의 서술 렌즈(선행엣지는 flow_edge.py 참조). "
          "별점·매수존 정본은 펀더(컨센·FMP). 최종 결정 정훈.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
