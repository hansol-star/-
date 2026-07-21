#!/usr/bin/env python3
"""snapshot_state_backfill.py — 과거 스냅샷에 '그 시점' 차트·변동성 상태 소급 태깅

정훈 지시(2026-07-21 "다 붙여줘"): 앞으로의 스냅샷은 snapshot.py가 차트·변동성을
태깅하지만 과거 스냅샷(6/29~7/20)엔 없다. 이 스크립트가 history_backfill 캐시로
**각 과거 날짜까지만 자른 종가**를 써서(=point-in-time, 미래참조 없음) 그 시점 상태를
재구성해 주입한다. 측정 3종이 가격의 순수 함수라 소급 가능 — 미래 데이터를 안 쓰므로
'그날 그 순간 우리가 봤을 차트'를 정직하게 복원.

⚠️ 소급분은 **종가 기반 지표만**(RV20·폭풍%ile·GARCH선행·RSI·MACD·MA크로스·52주고
대비). 스윙 고저(OHLC 필요)는 캐시에 종가만 있어 생략 — src="retro-pit"로 구분.

사용:
  python3 snapshot_state_backfill.py --dry-run     # 계산만(저장 안 함)
  python3 snapshot_state_backfill.py               # 상태 없는 과거 스냅샷에 주입·저장
  python3 snapshot_state_backfill.py --force        # 이미 있어도 재계산·덮어쓰기
  python3 snapshot_state_backfill.py --date 2026-07-02
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import statistics

try:
    import history_backfill as hb
    import garch
    import chart_read as cr
    import market_data as md
except ImportError:
    hb = garch = cr = md = None

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "data", "snapshots"))
TRADING_DAYS = 252


def _closes_asof(symbol: str, as_of: str) -> list[float]:
    """history 캐시에서 as_of(포함) 이하 날짜 종가만. 미래참조 차단."""
    rows = hb.load_cached(symbol) if hb else []
    return [c for d, c in rows if d <= as_of]


def _rv20_pct(closes: list[float]):
    """오늘 RV20이 전이력 RV20 분포에서 몇 %ile(그 시점까지)."""
    rets = [100.0 * (closes[i] / closes[i - 1] - 1)
            for i in range(1, len(closes)) if closes[i - 1]]
    if len(rets) < 40:
        return None, None
    rv = []
    for i in range(20, len(rets) + 1):
        seg = rets[i - 20:i]
        rv.append(statistics.stdev(seg) * math.sqrt(TRADING_DAYS))
    today = rv[-1]
    below = sum(1 for v in rv if v <= today)
    return round(today, 1), round(100.0 * below / len(rv), 0)


def pit_state(symbol: str, as_of: str) -> dict:
    """point-in-time 상태 — 그 날짜까지의 종가만 사용."""
    closes = _closes_asof(symbol, as_of)
    if len(closes) < 200:
        return {}
    rec = {"src": "retro-pit"}
    rv, rvp = _rv20_pct(closes)
    if rv is not None:
        rec["rv20"] = rv
        rec["storm_pct"] = rvp
    try:
        g = garch.fit_forecast(symbol, closes=closes)
        if g.get("ok"):
            rec["garch_fc"] = g["forecast_vol"]
            rec["regime"] = g["regime"]
    except Exception:
        pass
    try:
        rec["rsi"] = cr.rsi(closes)
        m = cr.macd(closes)
        rec["macd_h"] = round(m["hist"], 1) if m else None
        ma50 = cr.sma(closes, 50)
        ma200 = cr.sma(closes, 200)
        if ma50 and ma200:
            rec["cross"] = "골든크로스" if ma50 >= ma200 else "데드크로스"
        hi = max(closes[-252:]) if len(closes) >= 252 else max(closes)
        rec["pct_from_hi"] = round((closes[-1] / hi - 1) * 100, 1) if hi else None
    except Exception:
        pass
    return rec


def holdings_symbols():
    if md is None:
        return []
    cfg = md._load_universe()
    if cfg:
        kr, us, *_ = cfg
        return [s for _, s in kr] + [s for _, s in us]
    return [s for _, s in md.GROUPS["holdings"]]


def process(path: str, force: bool, dry: bool) -> str:
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    date = snap.get("date") or os.path.basename(path)[:10]
    has = bool(snap.get("market_state"))
    if has and not force:
        return f"  {date}  이미 태깅됨(건너뜀 — --force로 덮어쓰기)"
    idx = {s: pit_state(s, date) for s in ("^KS11", "^KQ11")}
    mkt = {s: pit_state(s, date) for s in holdings_symbols()}
    idx = {k: v for k, v in idx.items() if v}
    mkt = {k: v for k, v in mkt.items() if v}
    snap["index_state"] = {**snap.get("index_state", {}), **idx}
    snap["market_state"] = {**snap.get("market_state", {}), **mkt}
    if not dry:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
    ks = idx.get("^KS11", {})
    return (f"  {date}  태깅 {len(mkt)}종목 + 지수 · "
            f"코스피 RV20 {ks.get('rv20','?')}%({ks.get('storm_pct','?')}%ile) "
            f"GARCH {ks.get('garch_fc','?')}% [{ks.get('regime','?')}]"
            + ("  [dry]" if dry else ""))


def main() -> int:
    ap = argparse.ArgumentParser(description="과거 스냅샷 차트·변동성 소급 태깅(point-in-time)")
    ap.add_argument("--force", action="store_true", help="이미 태깅돼도 재계산")
    ap.add_argument("--dry-run", action="store_true", help="계산만·저장 안 함")
    ap.add_argument("--date", help="특정 날짜만(YYYY-MM-DD)")
    args = ap.parse_args()
    if hb is None:
        print("의존 모듈 미탑재 — history_backfill 먼저 실행")
        return 1
    files = sorted(glob.glob(os.path.join(SNAP_DIR, "*.json")))
    if args.date:
        files = [f for f in files if os.path.basename(f).startswith(args.date)]
    print(f"과거 스냅샷 소급 태깅 (point-in-time·미래참조 없음) — {len(files)}개")
    for f in files:
        print(process(f, args.force, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
