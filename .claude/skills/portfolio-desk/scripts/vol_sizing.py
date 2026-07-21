#!/usr/bin/env python3
"""vol_sizing.py — 변동성 타겟 트랜치 사이징 (측정·제안 전용·stdlib)

정훈 승인(2026-07-21 "다 붙여줘"): 7/18 study_log ④ '변동성 스케일 사이징'을 구축.
영상(Miles/GARCH) 공식 = risk = size × violence. 변동성은 통제 불가 → 사이즈로 조절.
  size_mult = target_vol / forecast_vol  (크루즈컨트롤: 도로경사↑면 속도 유지 위해 스로틀↓)

우리 데스크 특성 반영(CLAUDE.md 리스크룰):
  · **코어 홀딩은 손절 안 함** — 이건 '기존 포지션 청산'이 아니라 **'다음 트랜치(추가매수)를
    얼마로 넣을까'** 제안기다. 트림/청산 신호 아님.
  · **7,500 안전핀 = 이진 하드 플로어(불변)** — 코스피 종가 7,500 하회면 트랜치 전면 동결(mult=0).
    그 위에서만 폭풍 %ile로 트랜치를 **연속 감산**(CLAUDE.md vol_gauge 헌장 그대로).
  · 최종 판단 = PM 종합, 최종 결정 = 정훈. **자동 집행 아님.**

입력: garch.py 선행 예측(내일 변동성·폭풍%ile) — 없으면 vol_gauge(후행 RV) 폴백.
출력(종목별): 변동성타겟 배수 · 폭풍티어 배수 · **제안 트랜치 배수(둘의 보수적 min)** · 상태.

사용:
  python3 vol_sizing.py                    # 코스피·코스닥 + 보유 15
  python3 vol_sizing.py --target 15        # 연간 목표 리스크(변동성) % (기본 15=기관 관행)
  python3 vol_sizing.py --tickers ^KS11,NVDA
  python3 vol_sizing.py --index-floor 7500 # 안전핀 하드플로어(코스피 종가)
  python3 vol_sizing.py --json
"""
from __future__ import annotations

import argparse
import json

try:
    import garch
    import vol_gauge
    import market_data as md
except ImportError:
    garch = vol_gauge = md = None

KOSPI = "^KS11"


def _storm_tier_mult(pct):
    """폭풍 %ile → 트랜치 배수(연속 감산). ≥90 폭풍=1/3 … <40 차분=full."""
    if pct is None:
        return None
    if pct >= 90:
        return 0.33
    if pct >= 70:
        # 70~90 구간 선형: 0.5→0.33
        return round(0.5 - (pct - 70) / 20 * (0.5 - 0.33), 2)
    if pct >= 40:
        # 40~70 구간 선형: 1.0→0.5
        return round(1.0 - (pct - 40) / 30 * 0.5, 2)
    return 1.0


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def size_asset(symbol: str, target_vol: float) -> dict:
    """종목별 변동성타겟·폭풍티어·제안 트랜치 배수."""
    fc_vol = pct = regime = None
    src = None
    if garch is not None:
        g = garch.fit_forecast(symbol)
        if g.get("ok"):
            fc_vol, pct, regime = g["forecast_vol"], g["pct_rank"], g["regime"]
            src = "garch(선행)"
    if fc_vol is None and vol_gauge is not None:  # 폴백: 후행 RV
        try:
            gg = vol_gauge.gauge(symbol, 20, 252)
            fc_vol, pct, regime = gg.get("rv"), gg.get("storm_pct"), gg.get("regime")
            src = "vol_gauge(후행)"
        except Exception:
            pass
    if fc_vol is None:
        return {"symbol": symbol, "ok": False}
    vol_target_mult = _clamp(target_vol / fc_vol, 0.2, 1.0) if fc_vol else None
    storm_mult = _storm_tier_mult(pct)
    # 제안 = 두 방어신호의 보수적 min (둘 다 '줄이라'면 더 줄인다)
    cands = [m for m in (vol_target_mult, storm_mult) if m is not None]
    suggested = round(min(cands), 2) if cands else None
    return {
        "symbol": symbol, "ok": True, "src": src,
        "forecast_vol": fc_vol, "storm_pct": pct, "regime": regime,
        "vol_target_mult": round(vol_target_mult, 2) if vol_target_mult else None,
        "storm_mult": storm_mult, "suggested_tranche_mult": suggested,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="변동성 타겟 트랜치 사이징 (제안 전용·stdlib)")
    ap.add_argument("--target", type=float, default=15.0, help="연간 목표 변동성 %% (기본 15)")
    ap.add_argument("--tickers", help="쉼표구분(기본=코스피·코스닥+보유15)")
    ap.add_argument("--index-only", action="store_true")
    ap.add_argument("--index-floor", type=float, default=7500.0,
                    help="안전핀 하드플로어 — 코스피 종가 이 값 하회면 트랜치 전면 동결")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.tickers:
        uni = [(t.strip(), t.strip()) for t in args.tickers.split(",") if t.strip()]
    else:
        idx = [("코스피", "^KS11"), ("코스닥", "^KQ11")]
        uni = idx if args.index_only else idx + (list(md.GROUPS["holdings"]) if md else [])

    # 안전핀 하드플로어 게이트: 코스피 종가 확인
    frozen = False
    kospi_close = None
    if garch is not None:
        gk = garch.fit_forecast(KOSPI)
        kospi_close = gk.get("last_close") if gk.get("ok") else None
    if kospi_close is not None and kospi_close < args.index_floor:
        frozen = True

    rows = [(label, size_asset(sym, args.target)) for (label, sym) in uni]

    if args.json:
        print(json.dumps({
            "target_vol": args.target, "index_floor": args.index_floor,
            "kospi_close": kospi_close, "safety_pin_frozen": frozen,
            "assets": [{**{"label": l}, **r} for (l, r) in rows],
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"변동성 타겟 트랜치 사이징 (목표 {args.target}% · 제안 전용 · 자동집행 아님)")
    pin = (f"🔒 안전핀 동결 — 코스피 {kospi_close} < {args.index_floor:.0f} → 잔여 트랜치 전면 동결(mult=0)"
           if frozen else
           f"안전핀 OK — 코스피 {kospi_close} ≥ {args.index_floor:.0f}. 폭풍%ile로 트랜치 연속 감산")
    print(pin)
    hdr = ["자산", "예측변동성%", "폭풍%ile", "국면", "vol타겟배수", "폭풍배수", "제안트랜치"]
    print("  ".join(f"{h:<11}" for h in hdr))
    print("-" * 88)
    for label, r in rows:
        if not r.get("ok"):
            print(f"{label:<11}  데이터 없음")
            continue
        eff = 0.0 if frozen else r["suggested_tranche_mult"]
        note = " (동결)" if frozen else ""
        print(f"{label:<11}  {str(r['forecast_vol']):<11}{str(r['storm_pct']):<9}"
              f"{r['regime']:<7}{str(r['vol_target_mult']):<11}{str(r['storm_mult']):<9}"
              f"{eff}{note}")
    print("\n※ '제안트랜치' = 다음 추가매수 트랜치를 평소의 몇 배로 넣을지(코어 청산·손절 신호 아님).")
    print("  7,500 안전핀은 이진 하드플로어(불변), 그 위 폭풍%ile 연속 감산. 최종 결정 정훈.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
