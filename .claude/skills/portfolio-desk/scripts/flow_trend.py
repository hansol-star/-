#!/usr/bin/env python3
"""flow_trend.py — 외인 수급 '추세' 판독 (방향만 보지 말고 강도 변화를 본다).

[7/2 정훈 지시] "외국인의 매도도 중요한데 점점 매수량도 느는지도 잘 확인해야 될 듯"
→ flows.json(일별 순매수 시계열)에서 다음을 기계 계산:
  - streak      : 확정값 기준 연속 순매도/순매수 일수 (미확인 null은 건너뜀·명시)
  - 최근5일합 vs 직전5일합 : 매도 강도가 축소되는지(전환 조짐) 확대되는지
  - 누적        : 시리즈 전체 누적 순매수
  - 전환 단계   : 없음 → 조짐(강도 축소) → 전환(순매수 1~2일) → 확립(3일+)

★[2026-10-19] **게이트②는 KRX 정규장 기준 값으로 판정한다.** 9/14 애프터마켓(16:00~20:00) 시행 뒤 네이버 시장
  수급은 마감 뒤에도 계속 바뀐다 — 10/19 16:10 -323억 → 20:10 +947억(부호 반전) · 9/21 매체 마감 -1,655억 ↔
  네이버 19:10 +74억. 캐시·통계 정본이 KRX 정규장 기준(10/13)인데 게이트만 통합값을 읽고 있었다.
  · 행의 `regular` 필드(정규장 캡처) > `basis: regular` 대표값 > 9/14 이전 행(legacy) 순으로 읽는다
  · 기준을 모르는 행은 **|값| ≥ SIGN_SAFE_EOK일 때만 부호를 인정**한다(애프터가 그만큼 못 뒤집는다)
  · 그것도 아니면 '판정 보류' — 최신 행이 보류면 reversal=None·gate2.met=None, 중간 행이면 연속 일수는 하한

보고서·quick-check·triggers.py(cond=flow)에서 공용. stdlib만 사용.

사용:
  python3 flow_trend.py            # 판독 요약
  python3 flow_trend.py --json     # 기계용
  python3 flow_trend.py --selftest # 게이트② 기준 판정 자가검증(오프라인)
"""
from __future__ import annotations

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FLOWS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..",
                                      "data", "app", "flows.json"))
if not os.path.exists(FLOWS):  # 스킬 폴더 구조가 바뀌어도 리포 루트 기준으로 탐색
    _root = HERE
    for _ in range(6):
        cand = os.path.join(_root, "data", "app", "flows.json")
        if os.path.exists(cand):
            FLOWS = cand
            break
        _root = os.path.dirname(_root)

REFORM = "2026-09-14"      # 애프터마켓 시행일 — 이날부터 마감 뒤 집계가 정규장과 갈린다
# 기준을 모르는 값의 부호를 믿는 크기. 애프터마켓이 외인 값을 옮긴 실측: 9/21 약 +1,730억(부호 반전) ·
#   10/13 -520 · 10/14 +156 · 10/15 -1,100 · 10/16 +191 · 10/19 +1,270(부호 반전) → 최대 ≈1,800억의 1.7배.
#   ⚠️ 표본 6개다 — 애프터 거래가 커지면 이 값도 다시 잰다(close_recon.json `after_market_foreign`).
SIGN_SAFE_EOK = 3000
BASES = ("regular", "integrated", "unverified")


def load_series(path: str = FLOWS) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("series", [])


def gate_value(e: dict) -> tuple[float | None, str]:
    """게이트②가 읽는 외인 값과 그 근거.

    근거: regular(정규장 캡처) · legacy(9/14 이전 — 애프터마켓 없음) · sign_safe(기준 미상이나 부호는 안전)
          · null(값 없음 — 연속을 끊지 않고 건너뛴다) · hold(기준 미상·작은 값 — 판정 보류)
    """
    v = e.get("foreign")
    if e.get("basis") == "regular" and v is not None:
        return v, "regular"
    reg = e.get("regular")
    if isinstance(reg, dict) and reg.get("foreign") is not None:
        return reg["foreign"], "regular"
    if v is None:
        return None, "null"
    if str(e.get("date", "")) < REFORM:
        return v, "legacy"
    if abs(v) >= SIGN_SAFE_EOK:
        return v, "sign_safe"
    return None, "hold"


def compute_trend(series: list[dict]) -> dict:
    """값이 있는 날(foreign is not None)로 강도·누적을, **게이트 기준 값**으로 방향·연속·전환을 계산한다."""
    rows = [e for e in series if e.get("foreign") is not None]
    unconfirmed = [e["date"] for e in series if e.get("foreign") is None]
    if not rows:
        return {"error": "확정 데이터 없음"}

    gv = [(e,) + gate_value(e) for e in rows]
    held = [e["date"] for e, _, k in gv if k == "hold"]
    last, last_v, last_kind = gv[-1]

    # 강도·누적은 크기를 보는 축이라 기준이 갈려도 쓸 수 있다 — 정규장 값이 있으면 그것을 쓴다
    vals = [v if v is not None else e["foreign"] for e, v, _ in gv]
    recent5 = vals[-5:]
    prev5 = vals[-10:-5]
    sum_r, sum_p = sum(recent5), sum(prev5) if prev5 else None

    # 매도 강도 변화: 두 구간 모두 순매도일 때, 매도액이 줄면 '축소'(전환 조짐)
    intensity = None
    if sum_p is not None and sum_p < 0 and sum_r < 0:
        chg = (abs(sum_r) - abs(sum_p)) / abs(sum_p) * 100
        intensity = {"recent5": sum_r, "prev5": sum_p, "chg_pct": round(chg, 1),
                     "label": "매도강도 축소(전환 조짐)" if chg < -20
                     else ("매도강도 확대(악화)" if chg > 20 else "매도강도 비슷")}

    base = {"as_of": last["date"], "recent5_sum": sum_r, "prev5_sum": sum_p, "intensity": intensity,
            "cumulative": sum(vals), "unconfirmed_dates": unconfirmed, "held_dates": held,
            "basis": last_kind}

    if last_kind == "hold":
        why = (f"{last['date']} 외인 {last['foreign']:+,}억은 정규장 기준인지 모른다(정규장 캡처 없음 · "
               f"|값| < {SIGN_SAFE_EOK:,}억이라 애프터마켓이 부호를 바꿨을 수 있다)")
        return {**base, "direction": "판정 보류", "streak": 0, "streak_lower_bound": True,
                "last_amount": last["foreign"], "stage": "보류(정규장 기준 값 없음)", "reversal": None,
                "gate2": {"met": None, "streak": 0, "basis": "hold", "lower_bound": True, "reason": why}}

    buy = last_v > 0
    direction = "순매수" if buy else "순매도"
    streak, lower_bound = 0, False
    for e, v, k in reversed(gv):
        if k == "hold":                     # 기준 미상 행 앞은 이어졌는지 모른다 → 지금까지가 하한
            lower_bound = True
            break
        if (v > 0) == buy:
            streak += 1
        else:
            break

    # 전환 단계 판정
    if buy:
        stage = "확립(3일+)" if streak >= 3 else f"전환({streak}일째 순매수{' 이상' if lower_bound else ''})"
    elif intensity and intensity["chg_pct"] < -20:
        stage = "조짐(매도강도 축소)"
    else:
        stage = "없음(순매도 지속)"

    if not buy:
        met, reason = False, f"{last['date']} 정규장 기준 순매도"
    elif streak >= 2:
        met, reason = True, f"{streak}거래일 연속 순매수{'(하한)' if lower_bound else ''}"
    elif lower_bound:
        met, reason = None, "순매수 1일째 — 직전 거래일이 기준 미상이라 2일 연속인지 모른다"
    else:
        met, reason = False, "순매수 1일째(2거래일 요건 미충족)"

    return {
        **base,
        "direction": direction,
        "streak": streak,
        "streak_lower_bound": lower_bound,
        "last_amount": last_v,
        "stage": stage,
        "reversal": buy,
        "gate2": {"met": met, "streak": streak, "basis": last_kind, "lower_bound": lower_bound, "reason": reason},
    }


def selftest() -> int:
    """게이트②가 정규장 값을 읽고, 기준을 모르면 '판정 보류'라 말하는가(네트워크 없음)."""
    fails = []

    def ok(name, cond):
        if not cond:
            fails.append(name)
        print(f"  {'✅' if cond else '❌'} {name}")

    def row(d, v, **kw):
        return {"date": d, "foreign": v, **kw}

    # 10/19 실측 — 통합(20:10)이 대표값이면 2일 연속 순매수로 읽히지만 정규장(16:10)은 순매도다
    s1019 = [row("2026-10-15", -36537, basis="regular"),
             row("2026-10-16", 3446, basis="regular"),
             row("2026-10-19", -323, basis="regular", regular={"foreign": -323, "at": "16:10"},
                 integrated={"foreign": 947, "at": "20:10"})]
    t = compute_trend(s1019)
    ok("정규장 기준: 10/19 -323억 = 순매도 → 게이트② 미충족(통합 +947억에 속지 않는다)",
       t["gate2"]["met"] is False and t["direction"] == "순매도" and t["reversal"] is False)
    leg = [dict(r, basis=None) for r in s1019]
    leg[-1]["foreign"] = 947                       # 舊 행 = 대표값이 통합치
    t = compute_trend(leg)
    ok("대표값이 통합치여도 regular 필드가 있으면 그것을 읽는다", t["gate2"]["met"] is False and t["last_amount"] == -323)
    held = [row("2026-10-15", -36537, basis="regular"), row("2026-10-16", 3446, basis="regular"),
            row("2026-10-19", 947, basis="integrated")]
    t = compute_trend(held)
    ok("정규장 캡처가 없고 |값| < 3,000억 = '판정 보류'(reversal None · met None)",
       t["gate2"]["met"] is None and t["reversal"] is None and t["direction"] == "판정 보류"
       and t["held_dates"] == ["2026-10-19"])
    big = held[:-1] + [row("2026-10-19", 4200, basis="integrated")]
    t = compute_trend(big)
    ok("정규장 캡처가 없어도 |값| ≥ 3,000억이면 부호는 인정(sign_safe)",
       t["gate2"]["met"] is True and t["basis"] == "sign_safe" and t["streak"] == 2)
    mid = [row("2026-10-14", -11770, basis="regular"), row("2026-10-15", 900, basis="unverified"),
           row("2026-10-16", 3446, basis="regular")]
    t = compute_trend(mid)
    ok("중간 행이 기준 미상이면 연속은 하한 · 순매수 1일이면 met None(2일인지 모른다)",
       t["streak"] == 1 and t["streak_lower_bound"] and t["gate2"]["met"] is None)
    mid2 = mid + [row("2026-10-19", 500, basis="regular")]
    t = compute_trend(mid2)
    ok("하한이어도 2일 연속 순매수가 보이면 충족", t["gate2"]["met"] is True and t["streak"] == 2
       and t["streak_lower_bound"])
    pre = [row("2026-09-01", 2129), row("2026-09-02", 800)]
    t = compute_trend(pre)
    ok("9/14 이전 행(애프터마켓 없음)은 기준 표기 없이 그대로 판정(legacy)",
       t["gate2"]["met"] is True and t["basis"] == "legacy")
    nul = [row("2026-10-15", 3000, basis="regular"), row("2026-10-16", None), row("2026-10-19", 500, basis="regular")]
    t = compute_trend(nul)
    ok("null 행은 연속을 끊지 않고 건너뛴다(기존 규칙 유지)", t["streak"] == 2 and t["unconfirmed_dates"] == ["2026-10-16"])
    t = compute_trend([row("2026-10-16", 3446, basis="regular")])
    ok("순매수 1일 + 앞 행 없음 = 미충족(보류 아님)", t["gate2"]["met"] is False)

    print(f"\n{'✅ SELFTEST PASS' if not fails else '❌ SELFTEST FAIL: ' + ', '.join(fails)}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="외인 수급 추세 판독")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="게이트② 정규장 기준 판정 자가검증(오프라인)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    t = compute_trend(load_series())
    if args.json:
        print(json.dumps(t, ensure_ascii=False, indent=2))
        return 0
    if t.get("error"):
        print(f"⚠️ {t['error']}")
        return 1

    def uk(v):
        return f"{v/10000:+,.2f}조" if abs(v) >= 10000 else f"{v:+,.0f}억"

    g = t["gate2"]
    print("## 외인 수급 추세 판독 (flows.json 기계 계산)\n")
    if g["met"] is None and t["direction"] == "판정 보류":
        print(f"- 최종일: **{t['as_of']}** — **판정 보류** · {g['reason']}")
    else:
        print(f"- 최종 확정일: **{t['as_of']}** — {t['direction']} {uk(t['last_amount'])} "
              f"(**{t['streak']}거래일{' 이상' if t['streak_lower_bound'] else ''} 연속 {t['direction']}** · 기준 {t['basis']})")
    print(f"- 게이트②(외인 2거래일+ 순매수): **{ {True: '충족', False: '미충족', None: '판정 보류'}[g['met']] }** — {g['reason']}")
    print(f"- 최근 5일 합 {uk(t['recent5_sum'])}"
          + (f" vs 직전 5일 합 {uk(t['prev5_sum'])}" if t["prev5_sum"] is not None else ""))
    if t["intensity"]:
        print(f"    ↳ **{t['intensity']['label']}** (강도 {t['intensity']['chg_pct']:+.1f}%)")
    print(f"- 시리즈 누적: {uk(t['cumulative'])}")
    print(f"- 전환 단계: **{t['stage']}**")
    if t["held_dates"]:
        print(f"- ⚠️ 정규장 기준 미상(판정 보류) 일자: {', '.join(t['held_dates'][-8:])}")
    if t["unconfirmed_dates"]:
        print(f"- ⚠️ 미확정(null) 일자: {', '.join(t['unconfirmed_dates'])} — 확정치 수집 필요")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
