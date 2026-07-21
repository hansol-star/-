#!/usr/bin/env python3
"""
snapshot.py — 일별 포트폴리오 손익 스냅샷 저장 + 전일 대비 비교.

매일 손익 합계를 data/snapshots/YYYY-MM-DD.json 에 저장(커밋됨 → 시계열).
직전 스냅샷과 비교해 총자산·평가손익 전일대비 변화를 보여준다.
보고서 '변경점' 섹션과 연속성을 정량으로 보강.

사용:
  python3 snapshot.py            # 오늘 스냅샷 저장 + 전일대비
  python3 snapshot.py --no-save  # 저장 없이 비교만
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os

from pnl import load_cfg, eval_positions, fx_usdkrw

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "data", "snapshots"))

KST = dt.timezone(dt.timedelta(hours=9))


def trading_day() -> str:
    """스냅샷 귀속 거래일 = KST 현재시각 − 9h 의 날짜.
    [7/13 교정] 새벽 실행분(05:30 KST 미장 마감 크론)은 전일 거래일 파일에 귀속되고,
    낮/저녁 실행분은 당일 — UTC 컨테이너·KST 로컬 어디서 돌려도 같은 결과(기존 UTC
    date.today() 동작을 명시적 규칙으로 고정, 12월 로컬 이전 후에도 파일 체계 동일)."""
    return (dt.datetime.now(KST) - dt.timedelta(hours=9)).date().isoformat()


def _market_state(symbols: list[str]) -> dict:
    """[7/21 신설] 그날의 차트·변동성 상태를 종목별로 태깅.
    정훈 지시: '이슈와 그 때마다의 차트 변화를 기록' — 사건 로그(decisions)는 좋은데
    그 순간의 차트·변동성 상태가 정량으로 안 남던 공백을 메운다. GARCH 선행예측·폭풍
    %ile·차트 바이어스를 스냅샷에 박아 나중에 '그날 차트가 어땠나' 정량 조회 가능.
    측정 전용 — best-effort(네트워크 실패해도 스냅샷 저장은 계속). 무거우면 --no-state."""
    state = {}
    try:
        import garch
        import chart_read
    except ImportError:
        return state
    for sym in symbols:
        rec = {}
        try:
            g = garch.fit_forecast(sym)
            if g.get("ok"):
                rec.update({"garch_fc": g["forecast_vol"], "storm_pct": g["pct_rank"],
                            "regime": g["regime"]})
        except Exception:
            pass
        try:
            c = chart_read.read(sym)
            rec.update({"bias": c.get("bias"), "rsi": c.get("rsi"),
                        "cross": c.get("cross"), "struct": c.get("struct_dir"),
                        "macd_h": round(c["macd"]["hist"], 1) if c.get("macd") else None,
                        "pct_from_hi": c.get("pct_from_hi")})
        except Exception:
            pass
        if rec:
            state[sym] = rec
    return state


def compute(tag_state: bool = True) -> dict:
    cfg = load_cfg()
    fx = fx_usdkrw()
    kr = eval_positions(cfg["holdings"]["kr"])
    us = eval_positions(cfg["holdings"]["us"])
    kr_val = sum(r["value"] for r in kr if r["value"])
    kr_pnl = sum(r["pnl"] for r in kr if r["pnl"] is not None)
    us_val = sum(r["value"] for r in us if r["value"])
    us_pnl = sum(r["pnl"] for r in us if r["pnl"] is not None)
    cash = cfg.get("cash_krw", 0)
    us_val_krw = us_val * fx if fx else 0
    total = kr_val + us_val_krw + cash
    out = {
        "date": trading_day(),
        "fx_usdkrw": fx,
        "kr_value": round(kr_val), "kr_pnl": round(kr_pnl),
        "us_value_usd": round(us_val, 2), "us_pnl_usd": round(us_pnl, 2),
        "cash_krw": cash,
        "total_assets_krw": round(total),
        "stock_pnl_krw": round(kr_pnl + (us_pnl * fx if fx else 0)),
        "positions": {r["label"]: {"price": r["price"], "ret_pct": r["ret_pct"]}
                      for r in kr + us},
    }
    if tag_state:
        syms = [d["ticker"] for d in cfg["holdings"]["kr"] + cfg["holdings"]["us"]]
        out["index_state"] = _market_state(["^KS11", "^KQ11"])  # 크래시 TF 헤드라인
        out["market_state"] = _market_state(syms)               # 보유 종목별 차트·변동성
    return out


def prev_snapshot(today: str) -> dict | None:
    files = sorted(glob.glob(os.path.join(SNAP_DIR, "*.json")))
    files = [f for f in files if os.path.basename(f) < f"{today}.json"]
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser(description="일별 손익 스냅샷 + 전일대비")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--no-state", action="store_true",
                    help="차트·변동성 태깅 생략(빠른 손익만)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    snap = compute(tag_state=not args.no_state)
    prev = prev_snapshot(snap["date"])

    if not args.no_save:
        os.makedirs(SNAP_DIR, exist_ok=True)
        path = os.path.join(SNAP_DIR, f"{snap['date']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps({"today": snap, "prev": prev}, ensure_ascii=False, indent=2))
        return 0

    print(f"## 📸 스냅샷 {snap['date']}\n")
    print(f"- 총 자산: {snap['total_assets_krw']:,}원")
    print(f"- 주식 평가손익 합계: {snap['stock_pnl_krw']:+,}원")
    print(f"- 환율: {snap['fx_usdkrw']:,.2f}" if snap["fx_usdkrw"] else "- 환율: 미확인")
    if prev:
        d_total = snap["total_assets_krw"] - prev["total_assets_krw"]
        d_pnl = snap["stock_pnl_krw"] - prev["stock_pnl_krw"]
        print(f"\n### 직전({prev['date']}) 대비")
        print(f"- 총 자산: {d_total:+,}원")
        print(f"- 주식 평가손익: {d_pnl:+,}원")
        # 종목별 수익률 변화 큰 것 top3
        deltas = []
        for label, cur in snap["positions"].items():
            p = prev.get("positions", {}).get(label)
            if p and cur["ret_pct"] is not None and p.get("ret_pct") is not None:
                deltas.append((label, cur["ret_pct"] - p["ret_pct"]))
        deltas.sort(key=lambda x: abs(x[1]), reverse=True)
        if deltas:
            top = ", ".join(f"{l} {d:+.1f}%p" for l, d in deltas[:3])
            print(f"- 수익률 변화 큰 종목: {top}")
    else:
        print("\n(직전 스냅샷 없음 — 오늘이 첫 기록. 내일부터 전일대비 비교 가능)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
