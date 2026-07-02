#!/usr/bin/env python3
"""flow_trend.py — 외인 수급 '추세' 판독 (방향만 보지 말고 강도 변화를 본다).

[7/2 정훈 지시] "외국인의 매도도 중요한데 점점 매수량도 느는지도 잘 확인해야 될 듯"
→ flows.json(일별 순매수 시계열)에서 다음을 기계 계산:
  - streak      : 확정값 기준 연속 순매도/순매수 일수 (미확인 null은 건너뜀·명시)
  - 최근5일합 vs 직전5일합 : 매도 강도가 축소되는지(전환 조짐) 확대되는지
  - 누적        : 시리즈 전체 누적 순매수
  - 전환 단계   : 없음 → 조짐(강도 축소) → 전환(순매수 1~2일) → 확립(3일+)

보고서·quick-check·triggers.py(cond=flow)에서 공용. stdlib만 사용.

사용:
  python3 flow_trend.py            # 판독 요약
  python3 flow_trend.py --json     # 기계용
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


def load_series(path: str = FLOWS) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("series", [])


def compute_trend(series: list[dict]) -> dict:
    """확정값(foreign is not None)만으로 추세 계산. null 일자는 unconfirmed로 별도 보고."""
    confirmed = [e for e in series if e.get("foreign") is not None]
    unconfirmed = [e["date"] for e in series if e.get("foreign") is None]
    if not confirmed:
        return {"error": "확정 데이터 없음"}

    last = confirmed[-1]
    direction = "순매수" if last["foreign"] > 0 else "순매도"
    streak = 0
    for e in reversed(confirmed):
        if (e["foreign"] > 0) == (last["foreign"] > 0):
            streak += 1
        else:
            break

    vals = [e["foreign"] for e in confirmed]
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

    # 전환 단계 판정
    if last["foreign"] > 0:
        stage = "확립(3일+)" if streak >= 3 else f"전환({streak}일째 순매수)"
    elif intensity and intensity["chg_pct"] < -20:
        stage = "조짐(매도강도 축소)"
    else:
        stage = "없음(순매도 지속)"

    return {
        "as_of": last["date"],
        "direction": direction,
        "streak": streak,
        "last_amount": last["foreign"],
        "recent5_sum": sum_r,
        "prev5_sum": sum_p,
        "intensity": intensity,
        "cumulative": sum(vals),
        "stage": stage,
        "unconfirmed_dates": unconfirmed,
        "reversal": last["foreign"] > 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="외인 수급 추세 판독")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    t = compute_trend(load_series())
    if args.json:
        print(json.dumps(t, ensure_ascii=False, indent=2))
        return 0
    if t.get("error"):
        print(f"⚠️ {t['error']}")
        return 1

    def uk(v):
        return f"{v/10000:+,.2f}조" if abs(v) >= 10000 else f"{v:+,.0f}억"

    print("## 외인 수급 추세 판독 (flows.json 기계 계산)\n")
    print(f"- 최종 확정일: **{t['as_of']}** — {t['direction']} {uk(t['last_amount'])} "
          f"(**{t['streak']}거래일 연속 {t['direction']}**)")
    print(f"- 최근 5일 합 {uk(t['recent5_sum'])}"
          + (f" vs 직전 5일 합 {uk(t['prev5_sum'])}" if t["prev5_sum"] is not None else ""))
    if t["intensity"]:
        print(f"    ↳ **{t['intensity']['label']}** (강도 {t['intensity']['chg_pct']:+.1f}%)")
    print(f"- 시리즈 누적: {uk(t['cumulative'])}")
    print(f"- 전환 단계: **{t['stage']}**")
    if t["unconfirmed_dates"]:
        print(f"- ⚠️ 미확정(null) 일자: {', '.join(t['unconfirmed_dates'])} — 확정치 수집 필요")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
