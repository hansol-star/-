#!/usr/bin/env python3
"""chart_read.py — 기술적 차트 리드 엔진 (stdlib only, 포터블·무의존)

착안: 외부 강의 "AI Trading with Claude + TradingView"(Mind Math Money, 2026-07-16,
study_log 2026-07-20). 강의의 차트 읽기 워크플로우(시장구조·지지저항 존·이동평균·
MACD·RSI·멀티TF·컨플루언스)를 우리 데스크에 이식한 것. ⚠️강의의 SMA크로스 자동매매
전략은 채택 안 함(장기 코어 홀딩·손절선 없음 철학과 충돌) — '차트 읽기'만 가져온다.

성격: **측정·판독 전용.** vol_gauge.py와 동일하게 숫자·판독만 내고 어떤 룰도 바꾸지
않는다. 별점·스코어·매수존은 여전히 펀더(컨센·FMP)가 정본이고, 이 기술 리드는 그
옆에 붙는 '타이밍 보조 렌즈'다. 최종 판단은 PM 종합, 최종 결정은 정훈.

산출(종목별, Yahoo OHLC):
  ① 추세/시장구조 — SMA50·SMA200·가격 위치·골든/데드크로스 + 스윙 고저(HH/HL vs LH/LL)
  ② 지지·저항 존 — 최근 스윙 클러스터 + 52주 고저에서 현재가 위/아래 가장 가까운 레벨
  ③ 모멘텀 — RSI(14, Wilder)·MACD(12,26,9)
  ④ 멀티 타임프레임 — 일봉 + 주봉 추세(상위 TF=방향, 하위 TF=타이밍)
  ⑤ 컨플루언스 — 강세/약세 신호 정렬 카운트 → 기술적 바이어스 + 확신도

데이터: Yahoo v8 chart(무키), market_data.py·vol_gauge.py와 동일 소스.
유니버스: market_data.py 재사용(portfolio.json 정본) — 티커 드리프트 방지.

사용:
  python3 chart_read.py                      # 코스피·코스닥 + 보유 15종목
  python3 chart_read.py --tickers NVDA,005930.KS,^KS11
  python3 chart_read.py --holdings           # 보유 15종목만
  python3 chart_read.py --index-only         # 코스피·코스닥만
  python3 chart_read.py --json               # 파이프라인용
  python3 chart_read.py --verbose            # 스윙 레벨·값 상세
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:  # market_data 유니버스 재사용(portfolio.json 정본 미러)
    import market_data as md
    _KR = md.HOLDINGS_KR
    _US = md.HOLDINGS_US
    _IDX = md.INDEX
except Exception:
    md = None
    _KR = _US = []
    _IDX = [("코스피", "^KS11"), ("코스닥", "^KQ11")]

import ta_core as ta  # [7/22] 전문가급 지표 코어(BB·ATR·일목·ADX·OBV·MFI·다이버전스·스테이지·미너비니·VCP·RS)
import cli_common

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

_BENCH_CACHE: dict = {}  # RS라인 벤치마크 종가 캐시(프로세스당 1회 페치)


def _bench_closes(symbol: str):
    """RS라인 벤치마크: KR(.KS/.KQ)→코스피, US→S&P500. 지수 자신은 RS 생략."""
    if symbol.startswith("^"):
        return None, None
    bench = "^KS11" if symbol.endswith((".KS", ".KQ")) else "^GSPC"
    if bench not in _BENCH_CACHE:
        db = fetch_ohlc(bench, rng="1y", interval="1d")
        _BENCH_CACHE[bench] = db["c"] if db else None
    return bench, _BENCH_CACHE[bench]


def _rsi_series(closes, n=14):
    """Wilder RSI 시계열(다이버전스 판정용)."""
    if len(closes) < n + 1:
        return []
    gains, losses = [], []
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    def _r(g, s):
        return 100.0 if s == 0 else round(100 - 100 / (1 + g / s), 1)
    out = [_r(ag, al)]
    for i in range(n, len(gains)):
        ag = (ag * (n - 1) + gains[i]) / n
        al = (al * (n - 1) + losses[i]) / n
        out.append(_r(ag, al))
    return out


# ── 데이터 수집 ────────────────────────────────────────────────────────────
def _cache_fallback_ohlc(symbol: str, bars: int = 260):
    """[7/22 회복탄력성] Yahoo 실패 시 history_backfill 캐시(종가만)로 강등 작동.
    o=h=l=c 의사봉이므로 ATR·스토캐·일목·캔들은 무의미 → 호출측이 degraded 플래그로 구분.
    RSI·MACD·MA·구조·다이버전스·스테이지 등 종가 기반 지표는 정상 산출."""
    try:
        import history_backfill as hb
        rows = hb.load_cached(symbol)
    except Exception:
        rows = []
    if len(rows) < 30:
        return None
    c = [x for _, x in rows[-bars:]]
    return {"o": c[:], "h": c[:], "l": c[:], "c": c, "v": [0] * len(c), "degraded": True}


def fetch_ohlc(symbol: str, rng: str = "1y", interval: str = "1d", timeout: float = 15.0,
               retries: int = 2):
    """Yahoo chart에서 시간순 OHLC 반환. [7/22] 재시도 후 실패 시 일봉은 캐시 폴백(강등).
    null 봉(휴장)은 같은 인덱스로 함께 제거해 O/H/L/C 정합 유지."""
    url = (YAHOO_CHART.format(symbol=urllib.parse.quote(symbol))
           + f"?interval={interval}&range={rng}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    data = None
    delay = 2.0
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode())
            break
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
    if data is None:  # Yahoo 불가 → 일봉만 캐시 강등(주봉은 폴백 없음)
        return _cache_fallback_ohlc(symbol) if interval == "1d" else None
    try:
        res = data["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        o, h, l, c = q["open"], q["high"], q["low"], q["close"]
        v = q.get("volume") or [0] * len(c)  # [7/22] 거래량 확보(OBV·MFI·VCP·거래량고갈용)
        out_o, out_h, out_l, out_c, out_v = [], [], [], [], []
        for i in range(len(c)):
            if None in (o[i], h[i], l[i], c[i]):
                continue
            out_o.append(o[i]); out_h.append(h[i]); out_l.append(l[i]); out_c.append(c[i])
            out_v.append(v[i] if i < len(v) and v[i] is not None else 0)
        if len(out_c) < 30:
            return None
        return {"o": out_o, "h": out_h, "l": out_l, "c": out_c, "v": out_v}
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError,
            IndexError, TypeError, ValueError):
        return None


# ── 지표 ──────────────────────────────────────────────────────────────────
def sma(series: list[float], n: int):
    if len(series) < n:
        return None
    return sum(series[-n:]) / n


def ema_series(series: list[float], n: int):
    """전 구간 EMA 리스트(첫 값은 SMA 시드)."""
    if len(series) < n:
        return []
    k = 2 / (n + 1)
    out = [sum(series[:n]) / n]
    for x in series[n:]:
        out.append(x * k + out[-1] * (1 - k))
    return out


def rsi(closes: list[float], n: int = 14):
    """Wilder RSI(14)."""
    if len(closes) < n + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_g = sum(gains[:n]) / n
    avg_l = sum(losses[:n]) / n
    for i in range(n, len(gains)):
        avg_g = (avg_g * (n - 1) + gains[i]) / n
        avg_l = (avg_l * (n - 1) + losses[i]) / n
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return round(100 - 100 / (1 + rs), 1)


def macd(closes: list[float], fast: int = 12, slow: int = 26, sig: int = 9):
    """MACD(12,26,9) → (macd_line, signal, histogram) 최신값."""
    if len(closes) < slow + sig:
        return None
    ef, es = ema_series(closes, fast), ema_series(closes, slow)
    # 두 EMA 길이 정렬(느린 쪽이 짧음)
    off = len(ef) - len(es)
    ef = ef[off:]
    macd_line = [a - b for a, b in zip(ef, es)]
    signal = ema_series(macd_line, sig)
    if not signal:
        return None
    m = macd_line[-1]
    s = signal[-1]
    return round(m, 3), round(s, 3), round(m - s, 3)


# ── 시장구조·스윙 ─────────────────────────────────────────────────────────
def swings(highs: list[float], lows: list[float], k: int = 5):
    """프랙탈 스윙: high[i]가 ±k 창의 최대면 스윙고, low[i]가 최소면 스윙저.
    반환: (swing_highs, swing_lows) = [(idx, price), ...] 시간순.
    끝의 k개 봉은 미확정이라 제외."""
    sh, sl = [], []
    n = len(highs)
    for i in range(k, n - k):
        seg_h = highs[i - k:i + k + 1]
        seg_l = lows[i - k:i + k + 1]
        if highs[i] == max(seg_h):
            sh.append((i, highs[i]))
        if lows[i] == min(seg_l):
            sl.append((i, lows[i]))
    return sh, sl


def structure_verdict(sh, sl, price):
    """스윙 고저로 기저 구조(HH/HL·LH/LL) 판정 + 현재가의 BOS(break of structure) 반영.
    강의 개념: 마지막 스윙저 하회 = 하락 이탈(BOS↓), 마지막 스윙고 상회 = 상승 돌파(BOS↑).
    기저가 상승이어도 현재가가 마지막 스윙저를 깨면 실질 방향은 하락으로 본다(급락일 정확도)."""
    if len(sh) < 2 or len(sl) < 2:
        return "판정불가(스윙 부족)", None
    hh = sh[-1][1] > sh[-2][1]
    hl = sl[-1][1] > sl[-2][1]
    last_sh, last_sl = sh[-1][1], sl[-1][1]
    base = "up" if (hh and hl) else ("down" if (not hh and not hl) else "range")
    base_txt = {"up": "상승구조(HH·HL)", "down": "하락구조(LH·LL)", "range": "레인지(혼조)"}[base]
    # BOS 오버레이 (현재가 vs 마지막 확정 스윙)
    if price < last_sl:
        return f"{base_txt}→하락 이탈(BOS↓·마지막 스윙저 {round(last_sl,2)} 하회)", "down"
    if price > last_sh:
        return f"{base_txt}→상승 돌파(BOS↑·마지막 스윙고 {round(last_sh,2)} 상회)", "up"
    return base_txt, base


def sr_zones(sh, sl, current: float, tol: float = 0.018):
    """스윙 고저를 근접(tol=1.8%)끼리 존으로 묶고, 현재가 위/아래 가장 가까운 레벨.
    반환: (nearest_support, nearest_resistance) — 각 (중심가, 터치수) or None."""
    levels = [p for _, p in sh] + [p for _, p in sl]
    if not levels:
        return None, None
    levels.sort()
    zones = []
    cur = [levels[0]]
    for p in levels[1:]:
        if abs(p - cur[-1]) / cur[-1] <= tol:
            cur.append(p)
        else:
            zones.append(cur); cur = [p]
    zones.append(cur)
    zc = [(sum(z) / len(z), len(z)) for z in zones]  # (중심, 터치수)
    below = [z for z in zc if z[0] < current]
    above = [z for z in zc if z[0] > current]
    sup = max(below, key=lambda z: z[0]) if below else None
    res = min(above, key=lambda z: z[0]) if above else None
    return sup, res


# ── 종합 리드 ──────────────────────────────────────────────────────────────
def read(symbol: str, verbose: bool = False, ohlc: dict | None = None,
         weekly: dict | None = None) -> dict:
    """[7/22] ohlc/weekly 주입 가능 — 소스 무관(Yahoo 기본, naver_chart는 네이버 봉 주입).
    주입하면 그 봉으로 13신호 엔진을 그대로 돌린다(엔진 단일화·KR은 네이버 네이티브 판독)."""
    out = {"symbol": symbol}
    d = ohlc if ohlc is not None else fetch_ohlc(symbol, rng="1y", interval="1d")
    if not d:
        out["_error"] = "OHLC 조회 실패/부족"
        return out
    c, h, l = d["c"], d["h"], d["l"]
    price = c[-1]
    out["price"] = round(price, 2)

    ma50, ma200 = sma(c, 50), sma(c, 200)
    hi52, lo52 = max(h), min(l)

    # 추세 — MA 기반
    ma_bits = []
    if ma50:
        ma_bits.append(("above" if price >= ma50 else "below", 50, ma50))
    if ma200:
        ma_bits.append(("above" if price >= ma200 else "below", 200, ma200))
    # [7/22 수정] 크로스는 가격 위치로 자격 부여 — MA50≥MA200(골든)이라도 가격이 MA50
    # 아래면 급등후 급락의 '래깅' 아티팩트라 강세 오신호. 자격미달은 라벨에 명시 + 카운트 제외.
    cross = None
    if ma50 and ma200:
        if ma50 >= ma200:
            cross = "골든크로스" if price >= ma50 else "골든크로스(가격이탈·래깅)"
        else:
            cross = "데드크로스" if price <= ma50 else "데드크로스(가격회복)"

    # 시장구조 — 스윙
    sh, sl = swings(h, l, k=5)
    struct_txt, struct_dir = structure_verdict(sh, sl, price)
    sup, res = sr_zones(sh, sl, price)

    # 모멘텀
    r = rsi(c, 14)
    mac = macd(c)

    # 멀티 TF — 주봉
    dw = weekly if weekly is not None else fetch_ohlc(symbol, rng="2y", interval="1wk")
    wk_dir = None
    stage = None
    if dw and len(dw["c"]) >= 30:
        wc = dw["c"]
        w50, w20 = sma(wc, 30), sma(wc, 10)
        if w50 and w20:
            wk_dir = "상승" if (wc[-1] >= w50 and w20 >= w50) else (
                "하락" if (wc[-1] < w50 and w20 < w50) else "중립")
        stage = ta.weinstein_stage(wc)  # 와인스타인 4단계(30주 MA)

    # ── [7/22 프로 레이어 — ta_core] ─────────────────────────────────────
    degraded = bool(d.get("degraded"))
    if degraded:
        out["degraded"] = True  # Yahoo 불가 → 캐시 종가 강등(거래량·진짜 고저 없음)
    vol = [] if degraded else (d.get("v") or [])
    atr_val, atr_pct = ta.atr(h, l, c)
    bb = ta.bollinger(c)
    sto = ta.stochastic(h, l, c)
    ax = ta.adx(h, l, c)
    ichi = ta.ichimoku(h, l, c)
    obv = ta.obv_trend(c, vol)
    mfi_v = ta.mfi(h, l, c, vol)
    rsi_ser = _rsi_series(c, 14)
    div = ta.divergence(c, rsi_ser) if rsi_ser else None
    candles = ta.candle_pattern(d["o"], h, l, c)
    swing_hi = max((p for _, p in sh[-3:]), default=None) if sh else None
    swing_lo = min((p for _, p in sl[-3:]), default=None) if sl else None
    fib = ta.fib_levels(swing_hi, swing_lo, price) if swing_hi and swing_lo else None
    bench_sym, bench_c = _bench_closes(symbol)
    rs = ta.rs_line(c, bench_c) if bench_c else None
    mv = ta.minervini_template(c, h, l, rs_ok=(rs or {}).get("above_ma50"))
    vcp = ta.vcp_check(h, l, c, vol)

    # 컨플루언스 v2 — 강세/약세 신호 카운트 (기존 7신호 + 프로 6신호)
    bull = bear = 0
    if ma50 and price >= ma50: bull += 1
    elif ma50: bear += 1
    if ma200 and price >= ma200: bull += 1
    elif ma200: bear += 1
    if cross == "골든크로스": bull += 1
    elif cross == "데드크로스": bear += 1
    if struct_dir == "up": bull += 1
    elif struct_dir == "down": bear += 1
    if mac and mac[2] > 0: bull += 1
    elif mac: bear += 1
    if r is not None:
        if r >= 55: bull += 1
        elif r <= 45: bear += 1
    if wk_dir == "상승": bull += 1
    elif wk_dir == "하락": bear += 1
    # 프로 신호 (일목·ADX방향·OBV·다이버전스·스테이지·RS)
    if ichi:
        if ichi["cloud_pos"] == "구름 위": bull += 1
        elif ichi["cloud_pos"] == "구름 아래": bear += 1
    if ax and ax["adx"] >= 25:
        if ax["dir"] == "+DI우세": bull += 1
        else: bear += 1
    if obv:
        if "매집" in obv["verdict"]: bull += 1
        elif "분산" in obv["verdict"]: bear += 1
    if div:
        if div["bullish"]: bull += 1
        elif div["bearish"]: bear += 1
    if stage:
        if stage["stage"] == 2: bull += 1
        elif stage["stage"] == 4: bear += 1
    if rs:
        if rs["above_ma50"]: bull += 1
        elif rs["above_ma50"] is False: bear += 1

    total = bull + bear
    if total == 0:
        bias, conf = "중립", "낮음"
    else:
        net = bull - bear
        # v2: 신호 수가 7→13으로 늘어 임계 상향(강세 판정 과발행 방지)
        if net >= 5: bias = "강세"
        elif net <= -5: bias = "약세"
        elif net > 0: bias = "약강세"
        elif net < 0: bias = "약약세"
        else: bias = "혼조"
        ratio = abs(net) / total
        conf = "높음" if ratio >= 0.6 else ("보통" if ratio >= 0.3 else "낮음")

    out.update({
        # [7/22 프로 레이어]
        "atr_pct": atr_pct,
        "bb": bb, "stoch": sto, "adx": ax, "ichimoku": ichi,
        "obv": obv, "mfi": mfi_v,
        "divergence": (div or {}).get("signal"),
        "candle": candles, "fib": fib,
        "stage": {"stage": stage["stage"], "name": stage["name"],
                  "ma30w_slope_pct": stage["ma30w_slope_pct"]} if stage else None,
        "minervini": {"passed": mv["passed"], "total": mv["total"],
                      "verdict": mv["verdict"], "rs_ok": mv["rs_ok"],
                      **({"checks": mv["checks"]} if verbose else {})} if mv else None,
        "vcp": vcp, "rs": rs, "bench": bench_sym,
    })
    out.update({
        "ma50": round(ma50, 2) if ma50 else None,
        "ma200": round(ma200, 2) if ma200 else None,
        "cross": cross,
        "hi52": round(hi52, 2), "lo52": round(lo52, 2),
        "pct_from_hi": round((price / hi52 - 1) * 100, 1),
        "structure": struct_txt, "struct_dir": struct_dir,
        "support": [round(sup[0], 2), sup[1]] if sup else None,
        "resistance": [round(res[0], 2), res[1]] if res else None,
        "rsi": r,
        "macd": {"line": mac[0], "signal": mac[1], "hist": mac[2]} if mac else None,
        "weekly": wk_dir,
        "bull": bull, "bear": bear, "bias": bias, "confidence": conf,
    })
    if verbose:
        out["swing_highs"] = [round(p, 2) for _, p in sh[-4:]]
        out["swing_lows"] = [round(p, 2) for _, p in sl[-4:]]
    return out


def _rsi_tag(r):
    if r is None: return ""
    if r >= 70: return f"RSI {r}(과매수)"
    if r <= 30: return f"RSI {r}(과매도)"
    if r >= 55: return f"RSI {r}(강세권)"
    if r <= 45: return f"RSI {r}(약세권)"
    return f"RSI {r}(중립)"


def fmt(o: dict, verbose: bool = False) -> str:
    sym = o["symbol"]
    if o.get("_error"):
        return f"■ {sym}: {o['_error']}"
    L = []
    deg = " ⚠️강등모드(캐시 종가·거래량/고저 지표 제외)" if o.get("degraded") else ""
    L.append(f"■ {sym}  {o['price']}  →  기술 바이어스: {o['bias']}(확신 {o['confidence']}·강세 {o['bull']}/약세 {o['bear']}){deg}")
    # 추세
    ma_parts = []
    for label, ma in (("MA50", o["ma50"]), ("MA200", o["ma200"])):
        if ma:
            side = "위" if o["price"] >= ma else "아래"
            gap = round((o["price"] / ma - 1) * 100, 1)
            ma_parts.append(f"{label} {ma}(가격 {gap:+}% {side})")
    cross = f" · {o['cross']}" if o.get("cross") else ""
    L.append(f"   추세: {' / '.join(ma_parts)}{cross}")
    # 구조
    L.append(f"   구조: {o['structure']} · 52주 {o['lo52']}~{o['hi52']}(현재 고점 {o['pct_from_hi']:+}%)")
    # 지지/저항
    sup = f"{o['support'][0]}(터치{o['support'][1]})" if o.get("support") else "—"
    res = f"{o['resistance'][0]}(터치{o['resistance'][1]})" if o.get("resistance") else "—"
    L.append(f"   지지/저항: 지지 {sup}  /  저항 {res}")
    # 모멘텀
    if o.get("macd"):
        mh = o["macd"]["hist"]
        mtag = f"MACD {'강세' if mh > 0 else '약세'}(히스토 {mh:+})"
    else:
        mtag = "MACD n/a"
    L.append(f"   모멘텀: {_rsi_tag(o['rsi'])} · {mtag}")
    # 멀티TF
    daily = {"up": "상승", "down": "하락", "range": "레인지"}.get(o.get("struct_dir"), "n/a")
    L.append(f"   멀티TF: 일봉 {daily} / 주봉 {o.get('weekly') or 'n/a'}  (상위=방향·하위=타이밍)")
    # [7/22] 프로 레이어 요약 1~3줄
    pro1 = []
    if o.get("stage"):
        pro1.append(o["stage"]["name"])
    if o.get("adx"):
        pro1.append(f"ADX {o['adx']['adx']}({o['adx']['strength']}·{o['adx']['dir']})")
    if o.get("ichimoku"):
        pro1.append(f"일목 {o['ichimoku']['cloud_pos']}·{o['ichimoku']['tk_cross']}")
    if pro1:
        L.append(f"   국면: {' · '.join(pro1)}")
    pro2 = []
    if o.get("bb") and o["bb"].get("pct_b") is not None:
        sq = " 🔒스퀴즈" if o["bb"].get("squeeze") else ""
        pro2.append(f"BB %B {o['bb']['pct_b']}(폭 {o['bb']['squeeze_pctile']}%ile{sq})")
    if o.get("atr_pct") is not None:
        pro2.append(f"ATR {o['atr_pct']}%")
    if o.get("stoch"):
        pro2.append(f"스토캐스틱 {o['stoch']['k']}/{o['stoch']['d']}({o['stoch']['zone']})")
    if o.get("mfi") is not None:
        pro2.append(f"MFI {o['mfi']}")
    if o.get("obv"):
        pro2.append(o["obv"]["verdict"])
    if pro2:
        L.append(f"   변동성·수급: {' · '.join(pro2)}")
    pro3 = []
    if o.get("rs"):
        pro3.append(o["rs"]["trend"] + (" ★RS신고" if o["rs"].get("rs_new_high") else ""))
    if o.get("minervini"):
        pro3.append(f"미너비니 {o['minervini']['passed']}/8")
    if o.get("vcp") and o["vcp"].get("valid_vcp"):
        pro3.append(f"★VCP 유효({o['vcp']['pullbacks_pct']})")
    if o.get("divergence"):
        pro3.append(f"⚡{o['divergence']}")
    if o.get("candle"):
        pro3.append("캔들 " + "·".join(o["candle"]))
    if pro3:
        L.append(f"   셋업: {' · '.join(pro3)}")
    if verbose:
        if o.get("fib"):
            f = o["fib"]
            L.append(f"   피보나치(스윙): 최근접 {f['nearest'][0]}={f['nearest'][1]}({f['nearest_dist_pct']:+}%) · {f['levels']}")
        if o.get("minervini") and o["minervini"].get("checks"):
            fails = [k for k, ok in o["minervini"]["checks"].items() if not ok]
            L.append(f"   미너비니 미충족: {', '.join(fails) if fails else '없음(8/8)'}")
        if o.get("vcp"):
            L.append(f"   VCP: 되돌림 {o['vcp']['pullbacks_pct']} · {o['vcp']['note']}")
    if verbose and o.get("swing_highs"):
        L.append(f"   스윙고: {o['swing_highs']} · 스윙저: {o['swing_lows']}")
    return "\n".join(L)


def build_universe(args) -> list[tuple[str, str]]:
    if args.tickers:
        return [(t, t) for t in cli_common.split_tickers(args.tickers) if t.strip()]
    if args.index_only:
        return list(_IDX)
    if args.holdings:
        return list(_KR) + list(_US)
    return list(_IDX) + list(_KR) + list(_US)


def main():
    ap = argparse.ArgumentParser(description="기술적 차트 리드 엔진(무키·stdlib)")
    ap.add_argument("--tickers", help="쉼표·공백구분 Yahoo 심볼(유니버스 무시)")
    ap.add_argument("--holdings", action="store_true", help="보유 15종목만")
    ap.add_argument("--index-only", action="store_true", help="코스피·코스닥만")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    ap.add_argument("--verbose", action="store_true", help="스윙 레벨 상세")
    args = ap.parse_args()

    uni = build_universe(args)
    results = []
    for label, sym in uni:
        o = read(sym, verbose=args.verbose)
        o["label"] = label
        results.append(o)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return

    print("기술적 차트 리드 (chart_read.py · 측정·판독 전용 — 룰 미변경, 최종결정 정훈)")
    print("=" * 74)
    for o in results:
        lbl = o.get("label", o["symbol"])
        head = fmt(o, verbose=args.verbose).replace(f"■ {o['symbol']}", f"■ {lbl}[{o['symbol']}]", 1)
        print(head)
        print("-" * 74)
    print("※ 펀더(컨센·FMP) 스코어가 별점 정본 / 이 기술 리드는 타이밍 보조 렌즈. "
          "SMA크로스 자동매매는 미채택(장기 코어·손절선없음 철학).")


if __name__ == "__main__":
    main()
