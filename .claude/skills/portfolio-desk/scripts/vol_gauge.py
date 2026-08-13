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
import urllib.error
import urllib.parse
import urllib.request
import cli_common

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


def _fetch_dated(symbol: str, rng: str, timeout: float) -> dict:
    """Yahoo chart → {date: close}. 실패 시 빈 dict. null 종가는 건너뛴다."""
    url = YAHOO_CHART.format(symbol=urllib.parse.quote(symbol)) + f"?interval=1d&range={rng}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        res = data["chart"]["result"][0]
        ts = res.get("timestamp") or []
        closes = res["indicators"]["quote"][0]["close"]
        out = {}
        for t, c in zip(ts, closes):
            if c is None:
                continue
            out[dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")] = float(c)
        return out
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError,
            IndexError, TypeError, ValueError, OSError):
        return {}


def fetch_closes(symbol: str, rng: str = "2y", timeout: float = 15.0):
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
    """
    merged = _load_cache(symbol)
    # 캐시가 이미 가진 날짜는 **캐시가 정본**이고, Yahoo는 캐시에 없는 최신 봉만 채운다.
    #   · 덮어쓰기로 두면 Yahoo가 같은 날짜에 미세하게 다른 종가를 돌려줄 때 RV가 흔들린다
    #     (실측 잔여 편차 rv 13.9 ↔ 14.0 → storm 71.4 ↔ 72.2).
    #   · 두 소스가 **같은 필드**(indicators.quote[0].close, raw)를 쓰므로 seam 없음
    #     — history_backfill.py:113과 동일. 조정종가/원종가 혼입 아님.
    for d, c in _fetch_dated(symbol, rng, timeout).items():
        merged.setdefault(d, c)
    if not merged:
        return None
    return [merged[d] for d in sorted(merged)]


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


def gauge(symbol: str, window: int, lookback: int) -> dict:
    out = {"symbol": symbol}
    closes = fetch_closes(symbol)
    if not closes or len(closes) < window + 5:
        out["_error"] = "히스토리 부족/조회 실패"
        return out
    rets = log_returns(closes)
    rv = rolling_rv(rets, window)
    if not rv:
        out["_error"] = "RV 계산 불가"
        return out
    cur_rv = rv[-1]
    hist = rv[-lookback:] if len(rv) > lookback else rv  # 최근 1년 분포
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
    return out


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
    args = ap.parse_args()

    uni = _universe(args)
    rows = [(label, gauge(sym, args.window, args.lookback)) for (label, sym) in uni]

    if args.json:
        print(json.dumps([{**{"label": l}, **g} for (l, g) in rows], ensure_ascii=False, indent=2))
        return 0

    print(f"변동성 게이지 (RV{args.window}일·EWMA0.94·연율%, 폭풍=최근{args.lookback}일 백분위)")
    hdr = ["자산", "종가", "RV연율%", "EWMA%", "폭풍%ile", "국면", "1년(min–중–max)"]
    print(" | ".join(hdr))
    print("-" * 82)
    for label, g in rows:
        if g.get("_error"):
            print(f"{label:<8} | {g['_error']}")
            continue
        rng = f"{g['rv_1y_min']}–{g['rv_1y_med']}–{g['rv_1y_max']}"
        print(f"{label:<8} | {g['close']} | {g['rv_ann']} | {g['ewma_ann']} | "
              f"{g['storm_pct']} | {g['regime']} | {rng}")
    print("\n※ 측정 전용. 폭풍 점수→트랜치 스케일 매핑은 정훈 승인 후 적용(구조적 결정).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
