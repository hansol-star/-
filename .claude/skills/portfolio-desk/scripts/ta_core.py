#!/usr/bin/env python3
"""ta_core.py — 전문가급 기술지표 코어 라이브러리 (stdlib only·무의존·포터블)

정훈 지시(2026-07-22 "차트 분석 완벽 구현, 진짜 전문가처럼"). chart_read.py가 소비하는
순수 계산 모듈 — 네트워크·파일 I/O 없음, 입력은 OHLCV 리스트, 출력은 dict.

방법론 출처(외부 검증·study_log 2026-07-22):
  · 볼린저밴드·%B·밴드폭 스퀴즈 = John Bollinger 표준(20,2)
  · ATR = Wilder / 스토캐스틱(14,3) / ADX(14) = Wilder DMI
  · 일목균형표 = 전환(9)·기준(26)·선행스팬A/B(26시프트, 52) 표준
  · OBV = Granville / MFI(14) = 거래량 가중 RSI
  · 다이버전스 = 가격 스윙 고저 vs RSI 고저 비교(강세/약세 다이버전스)
  · 캔들패턴 = 망치·역망치·장악형·도지 (보조 신호로만)
  · 와인스타인 4단계 = 30주 MA 기울기+가격 위치 (Stage 1기초~4하락)
  · 미너비니 트렌드템플릿 8포인트 + VCP(수축 점감·거래량 고갈) — study_log 7/18 '보류' 숙제 완결
  · RS라인 = 종목/벤치마크 비율의 추세 (오닐·미너비니 상대강도 프록시)

⚠️ 전부 측정 전용. 별점·매수존 정본은 펀더(컨센·FMP) — 이 지표는 타이밍·리스크 보조 렌즈.
"""
from __future__ import annotations

import math
import statistics


# ── 기본 유틸 ─────────────────────────────────────────────────────────────
def sma(s, n):
    if len(s) < n:
        return None
    return sum(s[-n:]) / n


def sma_series(s, n):
    if len(s) < n:
        return []
    out, acc = [], sum(s[:n])
    out.append(acc / n)
    for i in range(n, len(s)):
        acc += s[i] - s[i - n]
        out.append(acc / n)
    return out


def _wilder_smooth(vals, n):
    """Wilder smoothing: 첫값=단순합, 이후 prev - prev/n + cur."""
    if len(vals) < n:
        return []
    out = [sum(vals[:n])]
    for v in vals[n:]:
        out.append(out[-1] - out[-1] / n + v)
    return out


# ── 변동성 ────────────────────────────────────────────────────────────────
def atr(h, l, c, n=14):
    """ATR(연속). 반환 (atr값, atr% of price)."""
    if len(c) < n + 1:
        return None, None
    trs = []
    for i in range(1, len(c)):
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    sm = _wilder_smooth(trs, n)
    if not sm:
        return None, None
    a = sm[-1] / n
    return round(a, 4), round(100 * a / c[-1], 2) if c[-1] else None


def bollinger(c, n=20, k=2.0, squeeze_lookback=120):
    """볼린저(20,2): %B·밴드폭 + 스퀴즈(밴드폭이 최근 lookback 중 몇 %ile로 좁은가).
    스퀴즈(저 %ile) = 변동성 수축 → 확장(방향 미정) 임박 신호."""
    if len(c) < n:
        return None
    mid = sum(c[-n:]) / n
    sd = statistics.pstdev(c[-n:])
    up, lo = mid + k * sd, mid - k * sd
    pb = (c[-1] - lo) / (up - lo) if up != lo else None
    # 밴드폭 시계열로 스퀴즈 백분위
    bws = []
    start = max(n, len(c) - squeeze_lookback)
    for i in range(start, len(c) + 1):
        seg = c[i - n:i]
        m = sum(seg) / n
        s = statistics.pstdev(seg)
        if m:
            bws.append(2 * k * s / m)
    bw = bws[-1] if bws else None
    sq_pct = (100 * sum(1 for x in bws if x <= bw) / len(bws)) if bws and bw is not None else None
    return {"mid": round(mid, 2), "upper": round(up, 2), "lower": round(lo, 2),
            "pct_b": round(pb, 2) if pb is not None else None,
            "bandwidth_pct": round(100 * bw, 2) if bw else None,
            "squeeze_pctile": round(sq_pct, 0) if sq_pct is not None else None,
            "squeeze": bool(sq_pct is not None and sq_pct <= 20)}


def stochastic(h, l, c, k_n=14, d_n=3):
    """스토캐스틱 %K(14) 및 %D(3 SMA)."""
    if len(c) < k_n + d_n:
        return None
    ks = []
    for i in range(k_n - 1, len(c)):
        hh = max(h[i - k_n + 1:i + 1])
        ll = min(l[i - k_n + 1:i + 1])
        ks.append(100 * (c[i] - ll) / (hh - ll) if hh != ll else 50.0)
    k = ks[-1]
    d = sum(ks[-d_n:]) / d_n
    zone = "과매수" if k >= 80 else ("과매도" if k <= 20 else "중립")
    return {"k": round(k, 1), "d": round(d, 1), "zone": zone}


# ── 추세 강도·구름 ────────────────────────────────────────────────────────
def adx(h, l, c, n=14):
    """Wilder ADX(14) + DI. 반환 {adx, plus_di, minus_di, strength}."""
    if len(c) < 2 * n + 1:
        return None
    trs, pdms, ndms = [], [], []
    for i in range(1, len(c)):
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        pdms.append(up if (up > dn and up > 0) else 0.0)
        ndms.append(dn if (dn > up and dn > 0) else 0.0)
    tr_s, p_s, n_s = _wilder_smooth(trs, n), _wilder_smooth(pdms, n), _wilder_smooth(ndms, n)
    m = min(len(tr_s), len(p_s), len(n_s))
    dxs = []
    pdi = ndi = None
    for i in range(m):
        if tr_s[i] == 0:
            continue
        pdi = 100 * p_s[i] / tr_s[i]
        ndi = 100 * n_s[i] / tr_s[i]
        s = pdi + ndi
        dxs.append(100 * abs(pdi - ndi) / s if s else 0.0)
    if len(dxs) < n:
        return None
    a = _wilder_smooth(dxs, n)[-1] / n
    strength = "강추세" if a >= 40 else ("추세" if a >= 25 else ("약추세" if a >= 20 else "무추세"))
    return {"adx": round(a, 1), "plus_di": round(pdi, 1), "minus_di": round(ndi, 1),
            "strength": strength, "dir": "+DI우세" if pdi > ndi else "-DI우세"}


def ichimoku(h, l, c):
    """일목균형표: 전환(9)·기준(26)·선행A/B(26시프트). 가격 vs 구름 위치."""
    if len(c) < 78:  # 52 + 26 시프트
        return None
    def mid_hl(n, end_off=0):
        e = len(c) - end_off
        return (max(h[e - n:e]) + min(l[e - n:e])) / 2
    tenkan = mid_hl(9)
    kijun = mid_hl(26)
    # 현재 봉 위의 구름 = 26봉 전 시점에서 계산된 선행스팬
    spanA = (mid_hl(9, 26) + mid_hl(26, 26)) / 2
    spanB = mid_hl(52, 26)
    top, bot = max(spanA, spanB), min(spanA, spanB)
    price = c[-1]
    pos = "구름 위" if price > top else ("구름 아래" if price < bot else "구름 안")
    tk = "TK강세(전환>기준)" if tenkan > kijun else ("TK약세" if tenkan < kijun else "TK중립")
    return {"tenkan": round(tenkan, 2), "kijun": round(kijun, 2),
            "spanA": round(spanA, 2), "spanB": round(spanB, 2),
            "cloud_pos": pos, "tk_cross": tk,
            "cloud_color": "양운(A>B)" if spanA > spanB else "음운(B>A)"}


# ── 거래량 ────────────────────────────────────────────────────────────────
def obv_trend(c, v, n=20):
    """OBV 최근 n봉 기울기(정규화). >0 매집 우세, <0 분산 우세."""
    if not v or len(c) != len(v) or len(c) < n + 2:
        return None
    obv = [0.0]
    for i in range(1, len(c)):
        obv.append(obv[-1] + (v[i] if c[i] > c[i - 1] else (-v[i] if c[i] < c[i - 1] else 0)))
    seg = obv[-n:]
    # 단순 선형 기울기(최소자승) / 평균 거래량으로 정규화
    xs = list(range(n))
    xm, ym = sum(xs) / n, sum(seg) / n
    cov = sum((x - xm) * (y - ym) for x, y in zip(xs, seg))
    var = sum((x - xm) ** 2 for x in xs)
    slope = cov / var if var else 0.0
    avg_v = sum(v[-n:]) / n
    norm = slope / avg_v if avg_v else 0.0
    verdict = "매집(OBV↑)" if norm > 0.05 else ("분산(OBV↓)" if norm < -0.05 else "중립")
    return {"slope_norm": round(norm, 3), "verdict": verdict}


def mfi(h, l, c, v, n=14):
    """Money Flow Index(14) — 거래량 가중 RSI."""
    if not v or len(c) < n + 1:
        return None
    pos = neg = 0.0
    for i in range(len(c) - n, len(c)):
        tp = (h[i] + l[i] + c[i]) / 3
        tp_prev = (h[i - 1] + l[i - 1] + c[i - 1]) / 3
        flow = tp * v[i]
        if tp > tp_prev:
            pos += flow
        elif tp < tp_prev:
            neg += flow
    if neg == 0:
        return 100.0
    return round(100 - 100 / (1 + pos / neg), 1)


def volume_dryup(v, short=20, long=50):
    """거래량 고갈(VCP 요건): 최근 20일 평균 < 50일 평균이면 dry-up."""
    if not v or len(v) < long:
        return None
    s, lg = sum(v[-short:]) / short, sum(v[-long:]) / long
    ratio = s / lg if lg else None
    return {"ratio": round(ratio, 2) if ratio else None, "dryup": bool(ratio and ratio < 0.85)}


# ── 위치·되돌림 ───────────────────────────────────────────────────────────
def fib_levels(swing_hi, swing_lo, price):
    """스윙 고저 기반 피보나치 되돌림 + 현재가와 가장 가까운 레벨."""
    if not swing_hi or not swing_lo or swing_hi <= swing_lo:
        return None
    rng = swing_hi - swing_lo
    levels = {"23.6%": swing_hi - 0.236 * rng, "38.2%": swing_hi - 0.382 * rng,
              "50.0%": swing_hi - 0.5 * rng, "61.8%": swing_hi - 0.618 * rng,
              "78.6%": swing_hi - 0.786 * rng}
    nearest = min(levels.items(), key=lambda kv: abs(kv[1] - price))
    return {"levels": {k: round(vv, 2) for k, vv in levels.items()},
            "nearest": (nearest[0], round(nearest[1], 2)),
            "nearest_dist_pct": round(100 * (price - nearest[1]) / nearest[1], 2)}


# ── 다이버전스 ────────────────────────────────────────────────────────────
def _swing_idx(vals, k=3, mode="low"):
    """국소 스윙 인덱스(양옆 k봉 대비 극값)."""
    out = []
    for i in range(k, len(vals) - k):
        win = vals[i - k:i + k + 1]
        if mode == "low" and vals[i] == min(win):
            out.append(i)
        elif mode == "high" and vals[i] == max(win):
            out.append(i)
    return out


def divergence(c, rsi_series, lookback=60):
    """가격 vs RSI 다이버전스 — 최근 두 스윙 비교.
    강세: 가격 저점 낮아지는데 RSI 저점 높아짐 / 약세: 가격 고점 높아지는데 RSI 고점 낮아짐."""
    if len(c) < lookback or len(rsi_series) < lookback:
        return None
    off_c = len(c) - lookback
    off_r = len(rsi_series) - lookback
    pc = c[off_c:]
    pr = rsi_series[off_r:]
    n = min(len(pc), len(pr))
    pc, pr = pc[-n:], pr[-n:]
    res = {"bullish": False, "bearish": False}
    lows = _swing_idx(pc, 3, "low")
    if len(lows) >= 2:
        i1, i2 = lows[-2], lows[-1]
        if pc[i2] < pc[i1] and pr[i2] > pr[i1] + 1:
            res["bullish"] = True
    highs = _swing_idx(pc, 3, "high")
    if len(highs) >= 2:
        j1, j2 = highs[-2], highs[-1]
        if pc[j2] > pc[j1] and pr[j2] < pr[j1] - 1:
            res["bearish"] = True
    res["signal"] = ("강세 다이버전스" if res["bullish"] else
                     ("약세 다이버전스" if res["bearish"] else None))
    return res


# ── 캔들 패턴 (보조) ──────────────────────────────────────────────────────
def candle_pattern(o, h, l, c):
    """마지막 1~2봉 패턴: 망치/역망치/장악형/도지. 보조 신호로만."""
    if len(c) < 2:
        return None
    o1, h1, l1, c1 = o[-1], h[-1], l[-1], c[-1]
    o0, c0 = o[-2], c[-2]
    rng = h1 - l1
    if rng <= 0:
        return None
    body = abs(c1 - o1)
    up_wick = h1 - max(o1, c1)
    dn_wick = min(o1, c1) - l1
    pats = []
    if body / rng < 0.1:
        pats.append("도지")
    if dn_wick >= 2 * body and up_wick <= body and body / rng < 0.35:
        pats.append("망치형(하방꼬리)")
    if up_wick >= 2 * body and dn_wick <= body and body / rng < 0.35:
        pats.append("역망치/유성형(상방꼬리)")
    if c1 > o1 and c0 < o0 and c1 >= o0 and o1 <= c0:
        pats.append("상승장악형")
    if c1 < o1 and c0 > o0 and c1 <= o0 and o1 >= c0:
        pats.append("하락장악형")
    return pats or None


# ── 스테이지·템플릿·VCP ──────────────────────────────────────────────────
def weinstein_stage(weekly_c):
    """와인스타인 4단계 — 30주 MA 기울기 + 가격 위치.
    1기초(MA평탄·가격 주변) / 2상승(MA상승·가격 위) / 3천장(MA평탄·가격 진동) / 4하락(MA하락·가격 아래)."""
    if len(weekly_c) < 34:
        return None
    ma30 = sma_series(weekly_c, 30)
    if len(ma30) < 5:
        return None
    cur, prev = ma30[-1], ma30[-5]  # 5주 전 대비 기울기
    slope_pct = 100 * (cur - prev) / prev if prev else 0
    price = weekly_c[-1]
    above = price > cur
    flat = abs(slope_pct) < 1.0
    if flat and not above:
        stage, name = 1, "Stage1 기초(바닥권 횡보)"
    elif slope_pct >= 1.0 and above:
        stage, name = 2, "Stage2 상승(매수 우위 국면)"
    elif flat and above:
        stage, name = 3, "Stage3 천장(분산 의심)"
    elif slope_pct <= -1.0 and not above:
        stage, name = 4, "Stage4 하락(신규매수 금지 국면)"
    else:
        stage, name = (2, "Stage2 진입 시도") if above else (4, "Stage4 이탈 진행")
    return {"stage": stage, "name": name, "ma30w": round(cur, 2),
            "ma30w_slope_pct": round(slope_pct, 2), "price_above": above}


def minervini_template(c, h, l, rs_ok=None):
    """미너비니 트렌드템플릿 8포인트 (외부 검증본 기준):
    ①가격>MA50 ②가격>MA150 ③가격>MA200 ④MA150>MA200 ⑤MA200 상승(1개월+)
    ⑥MA50>MA150 ⑦52주 저점 대비 +25%↑ ⑧52주 고점 대비 -25% 이내. (+RS는 별도 표기)"""
    if len(c) < 210:
        return None
    ma50, ma150, ma200 = sma(c, 50), sma(c, 150), sma(c, 200)
    ma200_series = sma_series(c, 200)
    ma200_rising = len(ma200_series) >= 21 and ma200_series[-1] > ma200_series[-21]
    hi52, lo52 = max(h), min(l)
    price = c[-1]
    checks = {
        "①P>MA50": price > ma50, "②P>MA150": price > ma150, "③P>MA200": price > ma200,
        "④MA150>MA200": ma150 > ma200, "⑤MA200상승": ma200_rising,
        "⑥MA50>MA150": ma50 > ma150,
        "⑦저점+25%↑": price >= lo52 * 1.25, "⑧고점-25%이내": price >= hi52 * 0.75,
    }
    passed = sum(1 for v in checks.values() if v)
    return {"passed": passed, "total": 8, "checks": checks,
            "verdict": "통과(Stage2 추세)" if passed == 8 else f"{passed}/8 미달",
        "rs_ok": rs_ok}


def vcp_check(h, l, c, v):
    """VCP(변동성 수축 패턴) — 수축 점감 + 거래량 고갈 (study_log 7/18 보류 숙제 완결).
    스윙고→스윙저 되돌림 깊이가 순차 감소(예 25%→15%→8%)하고 거래량이 마르면 유효."""
    if len(c) < 60:
        return None
    highs = _swing_idx(h, 3, "high")
    lows = _swing_idx(l, 3, "low")
    if len(highs) < 2 or len(lows) < 2:
        return None
    # 최근 스윙고 뒤의 스윙저를 짝지어 되돌림 깊이 계산 (최대 4개)
    pulls = []
    used = set()
    for hi_i in highs[-5:]:
        after = [lo_i for lo_i in lows if lo_i > hi_i and lo_i not in used]
        if after:
            lo_i = after[0]
            depth = 100 * (h[hi_i] - l[lo_i]) / h[hi_i]
            if depth > 0:  # 스윙저가 스윙고보다 높은 상승장 아티팩트 배제
                used.add(lo_i)
                pulls.append(round(depth, 1))
    pulls = pulls[-4:]
    contracting = len(pulls) >= 2 and all(pulls[i] > pulls[i + 1] for i in range(len(pulls) - 1))
    dry = volume_dryup(v)
    valid = bool(contracting and pulls and pulls[-1] < 12 and dry and dry["dryup"])
    return {"pullbacks_pct": pulls, "contracting": contracting,
            "volume_dryup": dry, "valid_vcp": valid,
            "note": "수축 점감+거래량 고갈 충족" if valid else "미충족(수축 점감 or 거래량 고갈 부재)"}


def rs_line(c, bench_c, n=50):
    """RS라인(종목/벤치) — 50일 추세와 신고 여부. 오닐·미너비니 상대강도 프록시."""
    m = min(len(c), len(bench_c))
    if m < n + 10:
        return None
    ratio = [c[-m + i] / bench_c[-m + i] for i in range(m) if bench_c[-m + i]]
    ma = sma(ratio, n)
    cur = ratio[-1]
    hi = max(ratio[-252:]) if len(ratio) >= 252 else max(ratio)
    return {"above_ma50": cur > ma if ma else None,
            "rs_new_high": cur >= hi * 0.99,
            "trend": "RS강세(벤치 아웃퍼폼)" if ma and cur > ma else "RS약세(벤치 언더퍼폼)"}
