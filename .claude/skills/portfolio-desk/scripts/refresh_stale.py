#!/usr/bin/env python3
"""refresh_stale.py — 신선도 게이트가 잡아낸 stale 레이어를 스스로 갱신한다.

왜 이게 필요한가 [2026-08-10 신설]
────────────────────────────────────────────────────────────────────
`validate_report.py --coverage`는 레이어가 상했다는 걸 **말해주기만** 했다.
그런데 그 경고를 받아 실제로 `--save`를 돌려주는 주체가 파이프라인 어디에도 없었다.

8/10 실측 — 배선 감사 결과:
  eps_revisions.py / naver_sentiment.py / guidance.py / transcripts.py
  네 개가 **SKILL.md·routines.md 어디에도 등장하지 않는다**(grep 0건).
  8/1에 만들어 CLAUDE.md 데이터 소스 절에 등재까지 해놓고, **아무 루틴도 호출하지 않았다.**
  결과: eps_revisions.json 9일 경과 → --coverage FAIL. sentiment.json 4일 경과 → WARN.

이건 7/29 재무제표 "2개월 0건" 사고와 **같은 구조의 반복**이다.
그때 얻은 교훈은 "게이트에 등록하라"였고 등록은 됐다 — 그런데 게이트는 **감시자**지 **집행자**가 아니다.
8/2에 확정한 원칙의 데이터판이 정확히 이것이다:

    "오더북에 들어간 것만 집행된다 — 산문에 남은 판단은 증발한다."
    ⇒ **루틴에 배선된 것만 갱신된다 — 문서에만 있는 레이어는 상한다.**

⚠️ 왜 프롬프트가 아니라 코드로 고치는가 [8/6 확인된 제약]
   R1~R4 루틴은 `http_api`로 생성된 트리거라 `update_trigger`가 **거부**한다.
   에이전트는 루틴 프롬프트를 못 고친다 ⇒ **루틴 동작 변경은 코드/스킬 쪽에 심어야 한다.**
   그래서 이 스크립트를 만들고 SKILL.md 수집 단계에 한 줄로 건다.

설계
────────────────────────────────────────────────────────────────────
· 신선도 표는 **validate_report.COVERAGE_LAYERS를 그대로 import**한다(DRY).
  두 벌로 두면 반드시 갈라진다 — 갈라지는 순간 이 스크립트는 거짓말을 시작한다.
· **FAIL 나기 전에** 갱신한다. 게이트 FAIL(age > max_age)을 기다리면 이미 늦다
  → 임계 = `max_age - 2`(허용 5일 이상인 레이어). 하루 걸러도 FAIL 안 나는 여유.
· **stale한 것만** 돌린다. 신선한 날은 네트워크 호출 0회 = 사실상 무비용(R2 예산 보호).
· 실행 주체가 없는 레이어(stocks·tasks = 보고서 파이프라인, hunter·feeds = R1,
  guru_flows = 트리거 게이트·분기 cadence)는 **일부러 뺐다.** 여기서 돌리면 R1/R2 역할이 겹친다.

⚠️ 측정·갱신 전용 — 별점·스코어·트랜치 어떤 룰도 바꾸지 않는다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
APP = os.path.join(ROOT, "data", "app")

sys.path.insert(0, HERE)
try:
    from validate_report import COVERAGE_LAYERS  # 정본 신선도 표 (DRY)
except Exception as e:  # pragma: no cover - import 실패는 치명적이라 즉시 드러내야 한다
    print(f"❌ validate_report.COVERAGE_LAYERS import 실패: {e}", file=sys.stderr)
    sys.exit(2)

# 레이어 → 실제 실행 가능한 명령. COVERAGE_LAYERS의 `how`는 사람이 읽는 문장이라
# ("보고서 파이프라인" 같은 것도 있다) 기계가 돌릴 수 있는 것만 여기 명시적으로 등록한다.
# 여기 없는 레이어는 "갱신 주체가 이 스크립트가 아님"을 뜻한다(R1·보고서 파이프라인 담당).
RUNNERS: dict[str, list[str]] = {
    "eps_revisions.json": ["eps_revisions.py", "--save"],
    "sentiment.json":     ["naver_sentiment.py", "--save"],
    "guidance.json":      ["guidance.py", "--save"],
    "transcripts.json":   ["transcripts.py", "--save"],
    # 안전망 — R2가 매일 명시적으로 돌리므로 보통 age=0이라 발동하지 않는다.
    # R2가 이 단계를 건너뛴 날에만 그물 역할.
    "financials.json":    ["financials.py", "--all", "--save"],
}

# 레이어별 타임아웃(초). 전문(트랜스크립트)·전종목 재무는 느리다.
TIMEOUTS: dict[str, int] = {
    "transcripts.json": 900,
    "financials.json":  1500,
}
DEFAULT_TIMEOUT = 420


def _layer_age(fn: str) -> int | None:
    """레이어 파일의 경과일. validate_report.check_coverage와 같은 규칙으로 읽는다."""
    p = os.path.join(APP, fn)
    if not os.path.exists(p):
        return 10**6  # 파일 자체가 없으면 최대 stale = 무조건 갱신 대상
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return 10**6  # 손상 = 갱신해서 복구 시도
    raw = str((d.get("updated") or d.get("as_of") or d.get("date") or ""))[:10]
    m = re.match(r"\d{4}-\d{2}-\d{2}", raw)
    if not m:
        return None  # 날짜 필드 없음 = 판정 불가(임의 갱신하지 않는다)
    return (dt.date.today() - dt.date.fromisoformat(m.group(0))).days


def _threshold(max_age: int) -> int:
    """FAIL(age > max_age) 전에 손대는 임계. 하루 걸러도 게이트가 안 터지도록 -2일."""
    return max_age - 2 if max_age >= 5 else max_age


def main() -> int:
    ap = argparse.ArgumentParser(
        description="stale 데이터 레이어를 자동 갱신 (validate_report.COVERAGE_LAYERS 기준)")
    ap.add_argument("--check", action="store_true",
                    help="갱신하지 않고 무엇이 대상인지만 출력 (dry-run)")
    ap.add_argument("--force", action="store_true",
                    help="신선도와 무관하게 등록된 레이어 전부 갱신")
    ap.add_argument("--only", metavar="LAYER",
                    help="특정 레이어만 (예: eps_revisions.json)")
    args = ap.parse_args()

    print("=" * 62)
    print("  refresh_stale — stale 레이어 자동 갱신")
    print("=" * 62)

    targets: list[tuple[str, int, int]] = []   # (파일명, 경과일, 임계)
    skipped: list[str] = []

    for fn, max_age, _how, _why in COVERAGE_LAYERS:
        if args.only and fn != args.only:
            continue
        if fn not in RUNNERS:
            skipped.append(fn)
            continue
        age = _layer_age(fn)
        if age is None:
            print(f"  ⚠️  {fn:<20} 날짜 필드 없음 — 판정 불가, 건너뜀")
            continue
        thr = _threshold(max_age)
        shown = "없음/손상" if age >= 10**6 else f"{age}일"
        if args.force or age >= thr:
            targets.append((fn, age, thr))
            print(f"  🔄 {fn:<20} {shown} (임계 {thr}일/허용 {max_age}일) → 갱신 대상")
        else:
            print(f"  ✅ {fn:<20} {shown} (임계 {thr}일) — 신선, 건너뜀")

    if skipped:
        print(f"\n  ℹ️  갱신 주체가 다른 레이어(여기서 안 돌림): {', '.join(skipped)}")

    if not targets:
        print("\n✅ 갱신할 레이어 없음 — 네트워크 호출 0회 (무비용 종료)")
        return 0

    if args.check:
        print(f"\n[dry-run] 갱신 대상 {len(targets)}개 — 실제 실행하려면 --check 없이 재실행")
        return 0

    print(f"\n갱신 시작 — 대상 {len(targets)}개\n" + "-" * 62)
    failed: list[str] = []
    for fn, age, _thr in targets:
        cmd = [sys.executable, os.path.join(HERE, RUNNERS[fn][0])] + RUNNERS[fn][1:]
        to = TIMEOUTS.get(fn, DEFAULT_TIMEOUT)
        print(f"\n▶ {fn} ({age}일 경과) — {' '.join(RUNNERS[fn])} (timeout {to}s)")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=to, cwd=ROOT)
        except subprocess.TimeoutExpired:
            print(f"  ⏱️  타임아웃 {to}s 초과 — 실패 처리")
            failed.append(f"{fn} (타임아웃)")
            continue
        except Exception as e:
            print(f"  ❌ 실행 실패: {str(e)[:120]}")
            failed.append(f"{fn} ({str(e)[:40]})")
            continue
        tail = [ln for ln in (r.stdout or "").strip().splitlines() if ln.strip()][-3:]
        for ln in tail:
            print(f"     {ln[:110]}")
        new_age = _layer_age(fn)
        if r.returncode != 0:
            err = (r.stderr or "").strip().splitlines()
            print(f"  ❌ exit {r.returncode} — {err[-1][:120] if err else '(stderr 없음)'}")
            failed.append(f"{fn} (exit {r.returncode})")
        elif new_age is not None and new_age < 10**6 and new_age <= 1:
            print(f"  ✅ 갱신 완료 → {new_age}일 경과")
        else:
            # exit 0인데 날짜가 안 움직였다 = 조용한 실패(빈 응답·API 차단 등).
            # 이걸 성공으로 넘기면 게이트가 다시 FAIL을 낼 때까지 아무도 모른다.
            print(f"  ⚠️  exit 0이나 갱신일이 안 움직임(경과 {new_age}일) — 소스 응답 확인 필요")
            failed.append(f"{fn} (무변화)")

    print("\n" + "=" * 62)
    if failed:
        print(f"⚠️  {len(targets)}개 중 {len(failed)}개 실패: {', '.join(failed)}")
        print("   → 실패는 게이트(validate_report --coverage)가 계속 FAIL/WARN으로 들고 있는다.")
        return 1
    print(f"✅ {len(targets)}개 레이어 갱신 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
