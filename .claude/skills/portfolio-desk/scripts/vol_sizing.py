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
    # [7/22 룰1 개정 §5b] 아래=이진0 대신, 폭풍<90(패닉 진정)이면 25% 극소 트랜치 허용.
    frozen = False
    kospi_close = kospi_storm = None
    below_pin_nibble = 0.0
    if garch is not None:
        gk = garch.fit_forecast(KOSPI)
        if gk.get("ok"):
            kospi_close = gk.get("last_close")
            kospi_storm = gk.get("pct_rank")
    # [2026-07-26] 후행 실현변동성(vol_gauge RV20) %ile도 함께 재서 **두 척도 교차확인**.
    # 선행(GARCH 예측)은 충격에 즉시 반응해 높게, 후행(RV20)은 완만하게 나온다 — 같은 날
    # 94 vs 86처럼 갈릴 수 있다. §5b는 **매수를 허용하는** 게이트이므로 보수적으로 운용한다:
    # **둘 다 90 미만일 때만** 극소창을 열고, 하나라도 90 이상이면 전면 동결.
    kospi_storm_rv = None
    if vol_gauge is not None:
        try:
            vg = vol_gauge.gauge(KOSPI, 20, 252)
            kospi_storm_rv = (vg or {}).get("storm_pct")
        except Exception:
            kospi_storm_rv = None
    if kospi_close is not None and kospi_close < args.index_floor:
        storms = [s for s in (kospi_storm, kospi_storm_rv) if s is not None]
        if storms and max(storms) < 90:
            below_pin_nibble = 0.25
            frozen = False  # 두 척도 모두 진정 → 극소 트랜치 허용(전면 동결 아님)
        else:
            frozen = True

    rows = [(label, size_asset(sym, args.target)) for (label, sym) in uni]

    def _eff(r):
        """실제 제안 배수: 동결=0 / 핀 아래 극소창=min(제안,0.25) / 핀 위=제안."""
        s = r.get("suggested_tranche_mult")
        if frozen or s is None:
            return 0.0
        if below_pin_nibble:
            return round(min(s, below_pin_nibble), 2)
        return s

    if args.json:
        print(json.dumps({
            "target_vol": args.target, "index_floor": args.index_floor,
            "kospi_close": kospi_close, "kospi_storm_pct": kospi_storm,
            "kospi_storm_pct_rv": kospi_storm_rv,  # 후행 RV20 기준(교차확인용)
            "safety_pin_frozen": frozen, "below_pin_nibble": below_pin_nibble,
            "assets": [{**{"label": l}, **r, "effective_mult": _eff(r)} for (l, r) in rows],
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"변동성 타겟 트랜치 사이징 (목표 {args.target}% · 제안 전용 · 자동집행 아님)")
    storm_txt = f"폭풍 선행(GARCH) {kospi_storm}%ile · 후행(RV20) {kospi_storm_rv}%ile"
    if frozen:
        pin = f"🔒 안전핀 동결 — 코스피 {kospi_close} < {args.index_floor:.0f} · {storm_txt} → 하나라도 ≥90(극단) = 전면 동결(mult=0)"
    elif below_pin_nibble:
        pin = f"🌬️ 안전핀 아래 극소창 — 코스피 {kospi_close} < {args.index_floor:.0f}이나 {storm_txt} 둘 다 <90(진정) → §5b 25% 극소 트랜치 1회 허용"
    else:
        pin = f"안전핀 OK — 코스피 {kospi_close} ≥ {args.index_floor:.0f}. 폭풍%ile로 트랜치 연속 감산"
    print(pin)
    hdr = ["자산", "예측변동성%", "폭풍%ile", "국면", "vol타겟배수", "폭풍배수", "제안트랜치"]
    print("  ".join(f"{h:<11}" for h in hdr))
    print("-" * 88)
    for label, r in rows:
        if not r.get("ok"):
            print(f"{label:<11}  데이터 없음")
            continue
        eff = _eff(r)
        note = " (동결)" if frozen else (" (극소창)" if below_pin_nibble else "")
        print(f"{label:<11}  {str(r['forecast_vol']):<11}{str(r['storm_pct']):<9}"
              f"{r['regime']:<7}{str(r['vol_target_mult']):<11}{str(r['storm_mult']):<9}"
              f"{eff}{note}")
    print("\n※ '제안트랜치' = 다음 추가매수 트랜치를 평소의 몇 배로 넣을지(코어 청산·손절 신호 아님).")
    print("  7,500 안전핀 = 하드플로어. 아래+폭풍≥90=동결 / 아래+폭풍<90=25%극소창(§5b) / 위=폭풍 연속감산. 최종 결정 정훈.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
