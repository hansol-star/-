#!/usr/bin/env python3
"""value_core.py — '선반영(미래가치 반영)' 판정 공용 코어 (stdlib·순수함수)

정훈 지시(2026-07-22). KR(naver_value·네이버 재무)·US(us_value·FMP)가 **같은 로직**으로
"앞으로의 가치가 주가에 얼마나 반영됐나"를 판정하도록 판정부만 추출. 네트워크·I/O 없음.

성격: 측정·판독 전용. 별점·매수존 정본은 펀더 스코어(컨센·FMP). 이 축은 '선반영' 렌즈.
"""
from __future__ import annotations


def structural_flags(prior_vals, est_val, implied_growth, prior_margin, est_margin,
                     upside, decel):
    """구조 플래그 3종 — 소스 무관(KR=영업이익 억 / US=순이익 $).
    · new_high_earn = 추정 실적이 과거 피크의 1.2배↑(순환회복 아닌 구조 신고)
    · aggressive    = 기대성장>100% or 추정마진이 최근의 2배↑(포워드 저PER의 조건부성)
    · target_stale  = 목표 상단>50%인데 실적 하락/둔화(크래시 후 애널 목표 미갱신 프록시)
    """
    pos = [x for x in (prior_vals or []) if x is not None and x > 0]
    new_high_earn = bool(est_val and pos and est_val > 1.2 * max(pos))
    aggressive = bool((implied_growth is not None and implied_growth > 100)
                      or (est_margin and prior_margin and est_margin > 2 * prior_margin))
    target_stale = bool(upside is not None and upside > 50 and decel)
    return new_high_earn, aggressive, target_stale


def priced_in_verdict(*, trail_per, fwd_per, implied_growth, upside,
                      margin_dir, eps_dir, new_high_earn, target_stale, loss_now):
    """선반영 판정 → (verdict_text, tilt[-2..+2]). naver_value 원 로직과 동일(단일화)."""
    cheap_fwd = bool(trail_per and fwd_per and fwd_per < 0.7 * trail_per)
    strong_g = implied_growth is not None and implied_growth >= 30
    stall = (eps_dir == "감소") or (margin_dir == "둔화"
                                   and implied_growth is not None and implied_growth < 15)
    credible_room = bool(upside is not None and upside >= 20 and not target_stale)

    if loss_now or fwd_per is None:
        return "내러티브(적자·PER 무의미 — 실적 아닌 스토리에 프라이싱)", 0
    if new_high_earn and strong_g and margin_dir == "가속":
        return "미반영 여지(신고 실적·마진 가속 — 컨센 실현 시 재평가 룸)", 2
    if stall and fwd_per >= 12:
        return "선반영·고평가 경계(성장 정체·EPS감소인데 배수 부담)", -2
    if trail_per and trail_per < 8 and stall:
        return "저평가나 실적 하락(밸류트랩 경계 — 싼 데는 이유)", -1
    if cheap_fwd and strong_g and not new_high_earn:
        return "부분 반영(순환 회복 — 구조성장 아님·트레일링PER 착시 주의)", 1
    if credible_room and strong_g:
        return "부분 반영(성장·목표 여유 있으나 배수 일부 반영)", 1
    return "대체로 적정 반영", 0
