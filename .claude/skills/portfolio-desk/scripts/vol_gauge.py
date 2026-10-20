#!/usr/bin/env python3
"""vol_gauge.py — 변동성 게이지·'폭풍 점수' (stdlib only, 포터블·무의존)

근거: study_log.md 2026-07-18 ④ (GARCH·Engle 노벨상 프레임). 핵심 사상 =
  "방향(which way)은 약신호·예측불가 / 변동성(how much)은 군집(clustering)하니
   예측가능 → 노력을 사이즈(변동성)에 배분한다." 폭풍일수록 노출을 줄인다.

이 스크립트는 **측정 전용**이다 — 숫자만 산출하고 어떤 룰도 바꾸지 않는다.
크래시 TF 안전핀을 '7,500 이진 동결'에서 '변동성 백분위로 트랜치 연속 스케일'로
정밀화하는 **매핑은 정훈 승인 후** 적용(구조적 결정). 여기선 그 근거 수치만 낸다.

산출(자산별, Yahoo OHLC 일봉):
  ① 실현변동성(RV, N일 종가수익률 표준편차 × √252) = 연율 %
  ② EWMA 변동성(RiskMetrics λ=0.94, 군집·메모리 반영) = 연율 % ('지금' 변동성)
  ③ **폭풍 점수** = 오늘 RV가 최근 1년 RV 분포에서 몇 %ile인지("작년의 96%보다 격렬")
  ④ 1년 RV 레인지(min·median·max)로 맥락

데이터: Yahoo v8 chart (range=2y interval=1d), market_data.py와 동일 무키 소스.
유니버스: market_data.py에서 재사용(portfolio.json 정본) — 티커 드리프트 방지.

사용:
  python3 vol_gauge.py                       # 코스피·코스닥 + 보유 15종목
  python3 vol_gauge.py --index-only          # 코스피·코스닥만 (안전핀 헤드라인)
  python3 vol_gauge.py --tickers ^KS11,NVDA  # 임의 Yahoo 심볼
  python3 vol_gauge.py --json                # 파이프라인용
  python3 vol_gauge.py --window 20 --lookback 252   # 창·백분위 기간 조정
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import cli_common

try:  # 날짜 라벨·세션 확정 판정 = 캐시를 쓰는 history_backfill과 **같은 함수**(두 벌로 두면 갈라진다)
    import history_backfill as _hb
except Exception:  # noqa: BLE001 — 없으면 UTC+오프셋 근사 · 미확정 판정 없음(舊 동작)
    _hb = None

try:  # 같은 폴더의 market_data 유니버스 재사용(portfolio.json 정본 미러)
    import market_data as md
    _KR = md.HOLDINGS_KR
    _US = md.HOLDINGS_US
    _IDX = md.INDEX
except Exception:  # 임포트 실패 시 최소 폴백(코스피·코스닥)
    md = None
    _KR = _US = []
    _IDX = [("코스피", "^KS11"), ("코스닥", "^KQ11")]

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
# 로컬 일봉 캐시(history_backfill.py 관리) — 폭풍 %ile 재현성의 바닥.
# ⚠️ 경로 규칙은 history_backfill.HIST_DIR와 **반드시 동일**해야 한다(두 벌로 두면 갈라진다).
_HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", "data", "history"))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
TRADING_DAYS = 252  # 연율화 상수

# 폭풍 점수(백분위) → 국면 라벨. 매핑(트랜치 스케일)은 정훈 승인 후 별도.
REGIMES = [
    (50, "평온"),    # <50%ile
    (75, "보통"),    # 50~75
    (90, "경계"),    # 75~90
    (97, "폭풍"),    # 90~97
    (101, "극단"),   # >97
]


def _regime(pct: float | None) -> str:
    if pct is None:
        return "-"
    for hi, label in REGIMES:
        if pct < hi:
            return label
    return "극단"


def _cache_path(symbol: str) -> str:
    """history_backfill.py와 동일한 파일명 규칙(^→_, =→_, /→_)."""
    safe = symbol.replace("^", "_").replace("=", "_").replace("/", "_")
    return os.path.join(HISTORY_DIR, f"{safe}.csv")


def _load_cache(symbol: str) -> dict:
    """data/history/<sym>.csv → {date: close}. 없으면 빈 dict."""
    p = _cache_path(symbol)
    out: dict[str, float] = {}
    try:
        with open(p, encoding="utf-8") as f:
            next(f, None)  # header: date,close
            for line in f:
                d, _, c = line.strip().partition(",")
                if d and c:
                    try:
                        out[d] = float(c)
                    except ValueError:
                        pass
    except OSError:
        pass
    return out


def _bar_date(t: int, gmtoffset: int = 0) -> str:
    """Yahoo 일봉 타임스탬프 → 거래소 현지일. 캐시와 같은 라벨이어야 병합이 맞는다 → history_backfill.bar_date 위임.
    ★[2026-10-20] 舊 = UTC 날짜. 현지 자정 전후에 여는 시장은 하루 앞 날짜가 됐다 — KRW=X 월요일 봉이
      '10/18(일)'로 들어가고, 캐시 마지막 날과 겹친 봉은 setdefault에 밀려 그날 수익률이 사라졌다.
      ^GSPC·^KS11·보유 종목은 UTC 날짜 = 현지 날짜라 하드플로어 판독은 안 바뀐다(selftest 대조)."""
    if _hb is not None:
        return _hb.bar_date(t, gmtoffset)
    return dt.datetime.utcfromtimestamp(t + int(gmtoffset or 0) + 3600).strftime("%Y-%m-%d")  # label-ok: history_backfill 임포트 실패 폴백


def _parse_dated(res: dict, now: int, settled_only: bool = False) -> tuple[dict, str | None]:
    """Yahoo chart result → ({date: close}, 미확정 세션 현지일 | None). null 종가는 건너뛴다.

    미확정 세션 = history_backfill.live_session_day(정규장 끝 + 40분 전)와 **같은 판정**.
    기본은 그 봉도 넣는다(장중 판독) — settled_only면 뺀다."""
    ts = res.get("timestamp") or []
    closes = res["indicators"]["quote"][0]["close"]
    meta = res.get("meta") or {}
    off = meta.get("gmtoffset") or 0
    live = _hb.live_session_day(meta, now) if _hb is not None else None
    out = {}
    for t, c in zip(ts, closes):
        if c is None:
            continue
        d = _bar_date(t, off)
        if settled_only and d == live:
            continue
        out[d] = float(c)
    return out, live


def _fetch_chart(symbol: str, rng: str, timeout: float):
    url = YAHOO_CHART.format(symbol=urllib.parse.quote(symbol)) + f"?interval=1d&range={rng}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())["chart"]["result"][0]
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError,
            IndexError, TypeError, ValueError, OSError):
        return None


def _fetch_dated(symbol: str, rng: str, timeout: float, settled_only: bool = False,
                 now: int | None = None) -> tuple[dict, str | None]:
    """Yahoo chart → ({date: close}, 미확정 세션 현지일). 실패 시 ({}, None)."""
    res = _fetch_chart(symbol, rng, timeout)
    if res is None:
        return {}, None
    try:
        return _parse_dated(res, int(now if now is not None else time.time()), settled_only)
    except (KeyError, IndexError, TypeError, ValueError):
        return {}, None


def closes_with_meta(symbol: str, rng: str = "2y", timeout: float = 15.0, settled_only: bool = False):
    """(시간순 종가, 출처 메타) — 실패 시 (None, meta).

    meta = {as_of: 마지막 봉 날짜, prev: 그 전 봉 날짜, provisional: 마지막 봉이 **아직 확정 안 된 세션**인가,
            live_day: 미확정 세션 현지일(장 시작 전엔 다가올 세션 날짜일 수 있다)}.
    ★[2026-10-20] 기본(settled_only=False)은 舊 동작 그대로 — 장중 봉이 그날 종가 자리에 들어간다.
      실측(`docs/research/vol_gauge_live_bar_2026-10-20.md`): 그 장중 판독이 **그 세션의 확정 판독과 더 가깝다**
      (S&P 1시간봉 3년 · 70 경계 불일치 장중 0.99% vs 전일 확정 3.57%). 그래서 빼지 않고 **표시만** 한다.
      settled_only=True = 확정 봉만(재현·감사용) — 캐시에 그날 행이 있어도 뺀다(장중에 쓰인 행일 수 있다)."""
    merged = _load_cache(symbol)
    got, live = _fetch_dated(symbol, rng, timeout, settled_only)
    # 캐시가 이미 가진 날짜는 **캐시가 정본**이고, Yahoo는 캐시에 없는 최신 봉만 채운다.
    #   · 덮어쓰기로 두면 Yahoo가 같은 날짜에 미세하게 다른 종가를 돌려줄 때 RV가 흔들린다
    #     (실측 잔여 편차 rv 13.9 ↔ 14.0 → storm 71.4 ↔ 72.2).
    #   · 두 소스가 **같은 필드**(indicators.quote[0].close, raw)를 쓰므로 seam 없음
    #     — history_backfill.py:113과 동일. 조정종가/원종가 혼입 아님.
    for d, c in got.items():
        merged.setdefault(d, c)
    if settled_only and live:
        merged.pop(live, None)
    meta = {"as_of": None, "prev": None, "provisional": False, "live_day": live}
    if not merged:
        return None, meta
    days = sorted(merged)
    meta.update({"as_of": days[-1], "prev": days[-2] if len(days) > 1 else None,
                 "provisional": bool(live) and days[-1] == live})
    return [merged[d] for d in days], meta


def fetch_closes(symbol: str, rng: str = "2y", timeout: float = 15.0, settled_only: bool = False):
    """시간순 유효 종가 리스트. 실패 시 None.

    ★[8/13 결함 수정 — 폭풍 %ile 비결정성] 舊 구현은 Yahoo 응답의 종가 배열에서
    null만 걸러 **일자를 버린 리스트**를 반환했다. 그런데 Yahoo가 동일 요청에
    **호출마다 다른 개수의 봉**(실측 498 vs 501, 첫·끝 종가는 동일)을 돌려주는 바람에
    252일 분포 창의 내용이 흔들려 `storm_pct`가 **72.2 ↔ 75.4로 튀었다.**
    하필 하드플로어 임계가 70이라, **같은 시점에 매수 허용 여부가 호출마다 뒤집힐 수**
    있었다(8/13 실측: triggers.py 75%ile vs tranche_rules.py 72%ile 동시 출력).

    ⇒ 수정: ①일자를 유지해 **date 키로 병합·중복제거** ②로컬 일봉 캐시
    (`data/history/`, history_backfill.py가 관리)를 과거 구간의 정본으로 깔고
    Yahoo는 **최신 봉 보충용**으로만 쓴다. 캐시가 없으면 Yahoo 단독으로 동작(하위호환).

    이 수정은 룰을 바꾸지 않는다 — 8/5에 `vol_gauge`를 폭풍 %ile **정본**으로 택한
    근거가 *"닫힌 계산이라 재현된다"*였는데 실제로는 재현되지 않고 있었다.
    그 결정을 바꾸는 게 아니라 **전제를 실제로 성립시키는** 수정이다.
    (정본 = docs/research/storm_pct_canon_2026-08-05.md)
    출처 메타(장중 잠정 여부)가 필요하면 closes_with_meta().
    """
    return closes_with_meta(symbol, rng, timeout, settled_only)[0]


def log_returns(closes: list[float]) -> list[float]:
    out = []
    for i in range(1, len(closes)):
        p0, p1 = closes[i - 1], closes[i]
        if p0 and p1 and p0 > 0 and p1 > 0:
            out.append(math.log(p1 / p0))
    return out


def rolling_rv(rets: list[float], window: int) -> list[float]:
    """각 시점의 뒤돌아본 window일 실현변동성(연율 %). 표본 표준편차 사용."""
    out = []
    for i in range(window, len(rets) + 1):
        seg = rets[i - window:i]
        sd = statistics.stdev(seg) if len(seg) > 1 else 0.0
        out.append(sd * math.sqrt(TRADING_DAYS) * 100)
    return out


def ewma_vol(rets: list[float], lam: float = 0.94) -> float | None:
    """RiskMetrics EWMA 변동성(연율 %). σ²_t = λσ²_{t-1} + (1-λ)r²_{t-1}.
    군집·메모리(어제 충격/변동성 계승)를 반영한 '지금' 변동성."""
    if len(rets) < 5:
        return None
    seed = statistics.pvariance(rets[:20]) if len(rets) >= 20 else statistics.pvariance(rets)
    var = seed
    for r in rets:
        var = lam * var + (1 - lam) * r * r
    return math.sqrt(var) * math.sqrt(TRADING_DAYS) * 100


def percentile_rank(series: list[float], value: float) -> float:
    """value가 series 분포에서 차지하는 백분위(0~100). ≤ 기준."""
    if not series:
        return None
    n = sum(1 for x in series if x <= value)
    return round(n / len(series) * 100, 1)


def _storm_of(closes: list[float], window: int, lookback: int):
    """종가 리스트 → (rv 시계열, 현재 rv, 분포 창) | None."""
    rv = rolling_rv(log_returns(closes), window)
    if not rv:
        return None
    hist = rv[-lookback:] if len(rv) > lookback else rv  # 최근 1년 분포
    return rv, rv[-1], hist


def gauge(symbol: str, window: int, lookback: int, settled_only: bool = False, _closes=None) -> dict:
    """폭풍 %ile 정본. 기본 = 장중 봉 포함(舊 동작 그대로 · 하드플로어 판독 불변).

    ★[2026-10-20] 출처 표시 추가 — 판독 값은 안 바뀐다:
      as_of = 마지막 봉 날짜 · provisional = 그 봉이 아직 확정 안 된 세션(장중·마감 직후 40분)인가 ·
      provisional이면 settled_storm_pct / settled_as_of = 직전 확정 봉까지의 판독(재현 가능한 값).
    settled_only=True면 확정 봉만으로 잰다(재현·감사용 · 기본값 전환은 정훈 승인 사항)."""
    out = {"symbol": symbol}
    closes, meta = _closes if _closes is not None else closes_with_meta(symbol, settled_only=settled_only)
    if not closes or len(closes) < window + 5:
        out["_error"] = "히스토리 부족/조회 실패"
        return out
    rets = log_returns(closes)
    got = _storm_of(closes, window, lookback)
    if not got:
        out["_error"] = "RV 계산 불가"
        return out
    rv, cur_rv, hist = got
    ewma = ewma_vol(rets)
    out["close"] = round(closes[-1], 2)
    out["rv_ann"] = round(cur_rv, 1)
    out["ewma_ann"] = round(ewma, 1) if ewma is not None else None
    out["storm_pct"] = percentile_rank(hist, cur_rv)
    out["regime"] = _regime(out["storm_pct"])
    out["rv_1y_min"] = round(min(hist), 1)
    out["rv_1y_med"] = round(statistics.median(hist), 1)
    out["rv_1y_max"] = round(max(hist), 1)
    out["n_days"] = len(rv)
    out["as_of"] = meta.get("as_of")
    out["provisional"] = bool(meta.get("provisional"))
    out["settled_only"] = bool(settled_only)
    if out["provisional"]:
        prev = _storm_of(closes[:-1], window, lookback)
        out["settled_storm_pct"] = percentile_rank(prev[2], prev[1]) if prev else None
        out["settled_as_of"] = meta.get("prev")
    return out


def provisional_note(g: dict) -> str:
    """장중 잠정 판독 표기 한 줄('' = 확정 판독). 보고서·알림 문구에 그대로 붙인다."""
    if not (g or {}).get("provisional"):
        return ""
    s = g.get("settled_storm_pct")
    tail = f"확정 {s:.0f}%ile({g.get('settled_as_of')})" if s is not None else "확정 판독 미산출"
    return f"장중 잠정 — {g.get('as_of')} 세션 미확정 봉 포함 · {tail}"


def _universe(args) -> list[tuple[str, str]]:
    if args.tickers:
        return [(t.strip(), t.strip()) for t in cli_common.split_tickers(args.tickers) if t.strip()]
    if args.index_only:
        return [(l, s) for (l, s) in _IDX if s in ("^KS11", "^KQ11")]
    idx = [(l, s) for (l, s) in _IDX if s in ("^KS11", "^KQ11")]
    return idx + list(_KR) + list(_US)


def main() -> int:
    ap = argparse.ArgumentParser(description="변동성 게이지·폭풍 점수 (측정 전용·stdlib)")
    ap.add_argument("--tickers", help="쉼표·공백구분 Yahoo 심볼(라벨=심볼). 기본=코스피·코스닥+보유15")
    ap.add_argument("--index-only", action="store_true", help="코스피·코스닥만")
    ap.add_argument("--window", type=int, default=20, help="RV 창(거래일, 기본 20≈1개월)")
    ap.add_argument("--lookback", type=int, default=TRADING_DAYS, help="폭풍 백분위 기간(기본 252≈1년)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--settled-only", action="store_true",
                    help="확정 봉만(장중·마감 직후 40분 봉 제외 · 재현·감사용). 기본 = 장중 봉 포함(하드플로어 정본 동작)")
    ap.add_argument("--selftest", action="store_true", help="장중 봉 표시·settled_only·날짜 라벨 자가검증(오프라인)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    uni = _universe(args)
    rows = [(label, gauge(sym, args.window, args.lookback, settled_only=args.settled_only))
            for (label, sym) in uni]

    if args.json:
        print(json.dumps([{**{"label": l}, **g} for (l, g) in rows], ensure_ascii=False, indent=2))
        return 0

    mode = " · 확정 봉만" if args.settled_only else ""
    print(f"변동성 게이지 (RV{args.window}일·EWMA0.94·연율%, 폭풍=최근{args.lookback}일 백분위{mode})")
    hdr = ["자산", "종가", "RV연율%", "EWMA%", "폭풍%ile", "국면", "1년(min–중–max)", "기준일"]
    print(" | ".join(hdr))
    print("-" * 82)
    notes = []
    for label, g in rows:
        if g.get("_error"):
            print(f"{label:<8} | {g['_error']}")
            continue
        rng = f"{g['rv_1y_min']}–{g['rv_1y_med']}–{g['rv_1y_max']}"
        mark = "*" if g.get("provisional") else ""
        print(f"{label:<8} | {g['close']} | {g['rv_ann']} | {g['ewma_ann']} | "
              f"{g['storm_pct']}{mark} | {g['regime']} | {rng} | {g.get('as_of')}")
        if mark:
            notes.append(f"  * {label}: {provisional_note(g)}")
    if notes:
        print("\n" + "\n".join(notes))
    print("\n※ 측정 전용. 폭풍 점수→트랜치 스케일 매핑은 정훈 승인 후 적용(구조적 결정).")
    return 0


def selftest() -> int:
    """오프라인 — 합성 Yahoo 응답 + 합성 캐시로 출처 표시·settled_only·날짜 라벨을 검증한다."""
    fails = []

    def check(name, cond, detail=""):
        if not cond:
            fails.append(f"{name}: {detail}")

    import random
    rnd = random.Random(7)
    day0 = dt.date(2024, 1, 1)
    days, px, d, p = [], [], day0, 100.0
    while len(days) < 400:
        if d.weekday() < 5:
            p *= math.exp(rnd.gauss(0, 0.01))
            days.append(d.isoformat())
            px.append(round(p, 4))
        d += dt.timedelta(days=1)
    cache = dict(zip(days[:-1], px[:-1]))          # 캐시 = 어제까지
    last, last_px = days[-1], px[-1] * 1.04          # 오늘 장중 +4% 급등(장중 봉)
    k09 = int(dt.datetime.fromisoformat(last + "T00:00:00+00:00").timestamp())   # 09:00 KST = 00:00 UTC

    def chart(now_end_offset):
        """KST 시장: 오늘 봉 + 정규장 09:00~15:00(Yahoo 기준) 메타. now_end_offset = 정규장 끝 기준 경과 초."""
        ts = [int(dt.datetime.fromisoformat(x + "T00:00:00+00:00").timestamp()) for x in days]
        res = {"timestamp": ts,
               "indicators": {"quote": [{"close": px[:-1] + [last_px]}]},
               "meta": {"gmtoffset": 32400, "currentTradingPeriod": {"regular": {"start": k09, "end": k09 + 21600}}}}
        return res, k09 + 21600 + now_end_offset

    global _load_cache, _fetch_chart
    o_load, o_fetch = _load_cache, _fetch_chart
    try:
        _load_cache = lambda s: dict(cache)                          # noqa: E731
        for name, off, want_prov in (("장중", -3600, True), ("마감 직후 유예 안", 20 * 60, True),
                                     ("유예 지남", 41 * 60, False)):
            res, now = chart(off)
            _fetch_chart = lambda s, r, t, _res=res: _res              # noqa: E731
            tnow = time.time
            time.time = lambda _n=now: _n                              # noqa: E731
            try:
                cl, meta = closes_with_meta("SYN")
                g = gauge("SYN", 20, 252, _closes=(cl, meta))
                cs, ms = closes_with_meta("SYN", settled_only=True)
                gs = gauge("SYN", 20, 252, _closes=(cs, ms))
            finally:
                time.time = tnow
            check(f"{name}: 기본은 오늘 봉 포함", meta["as_of"] == last and abs(cl[-1] - last_px) < 1e-9,
                  f"{meta}")
            check(f"{name}: provisional", g["provisional"] is want_prov, f"{g.get('provisional')}")
            if want_prov:
                check(f"{name}: settled_only는 오늘 봉을 뺀다", ms["as_of"] == days[-2] and len(cs) == len(cl) - 1,
                      f"{ms}")
                check(f"{name}: settled_storm_pct = settled_only 판독",
                      g.get("settled_storm_pct") == gs["storm_pct"] and g.get("settled_as_of") == days[-2],
                      f"{g.get('settled_storm_pct')} vs {gs['storm_pct']}")
                check(f"{name}: 급등 장중 봉이 판독을 올린다", g["storm_pct"] > gs["storm_pct"],
                      f"{g['storm_pct']} vs {gs['storm_pct']}")
                check(f"{name}: 표기 한 줄", "장중 잠정" in provisional_note(g) and days[-2] in provisional_note(g),
                      provisional_note(g))
                check(f"{name}: settled_only 판독은 잠정이 아니다", gs["provisional"] is False, f"{gs}")
            else:
                check(f"{name}: 확정이면 settled_only도 같다", gs["storm_pct"] == g["storm_pct"] and ms["as_of"] == last,
                      f"{gs['storm_pct']} vs {g['storm_pct']}")
                check(f"{name}: 확정이면 표기 없음", provisional_note(g) == "" and "settled_storm_pct" not in g, f"{g}")

        # settled_only는 캐시에 그날 행이 있어도 뺀다(장중에 쓰인 행일 수 있다)
        res, now = chart(-3600)
        _load_cache = lambda s: {**cache, last: last_px}               # noqa: E731
        _fetch_chart = lambda s, r, t, _res=res: _res                  # noqa: E731
        tnow = time.time
        time.time = lambda _n=now: _n                                  # noqa: E731
        try:
            cl2, m2 = closes_with_meta("SYN")
            cs2, ms2 = closes_with_meta("SYN", settled_only=True)
        finally:
            time.time = tnow
        check("캐시에 장중 행: 기본은 잠정 표시", m2["provisional"] is True, f"{m2}")
        check("캐시에 장중 행: settled_only는 뺀다", ms2["as_of"] == days[-2], f"{ms2}")
    finally:
        _load_cache, _fetch_chart = o_load, o_fetch

    # 날짜 라벨 — 현지 자정에 여는 시장(KRW=X 영국 서머타임: 세션 시작 = 전날 23:00 UTC)
    if _hb is not None:
        mon = int(dt.datetime(2026, 10, 18, 23, 0, tzinfo=dt.timezone.utc).timestamp())   # 월 10/19 00:00 BST
        check("라벨: KRW=X 월요일 봉은 10/19", _bar_date(mon, 3600) == "2026-10-19", _bar_date(mon, 3600))
        gspc = int(dt.datetime(2026, 10, 19, 13, 30, tzinfo=dt.timezone.utc).timestamp())  # 09:30 ET
        check("라벨: ^GSPC는 UTC 날짜와 같다", _bar_date(gspc, -14400) == "2026-10-19", _bar_date(gspc, -14400))
        check("라벨: ^KS11(09:00 KST = 00:00 UTC)도 같다", _bar_date(k09, 32400) == last, _bar_date(k09, 32400))
    else:
        fails.append("history_backfill 임포트 실패 — 라벨·미확정 판정이 舊 동작으로 강등된다")

    if fails:
        print("❌ vol_gauge selftest 실패")
        for f in fails:
            print("  -", f)
        return 1
    print("✅ vol_gauge selftest 통과 — 장중 봉 표시(잠정·확정 병기)·settled_only·마감 유예·캐시 장중 행·날짜 라벨")
    return 0


if __name__ == "__main__":
    sys.exit(main())
