#!/usr/bin/env python3
"""report_guard.py — 보고서 토큰-리셋 재시도 가드 [2026-07-16 정훈 지시]

정훈: "보고서 만들 때 자주 토큰이 없다 → 세션/루틴이 토큰으로 막히면 리셋 시간
고려해서 그 이후 자동 재실행하고 보고서 들어가게."

■ 왜 이 형태인가 (원천 제약):
  1. 토큰이 완전 소진된 세션은 도구 호출·트리거 등록조차 못 하고 죽는다
     → "막힌 그 세션이 스스로 재예약"은 불가능.
  2. 무인 루틴 세션에선 트리거 등록 API가 승인 게이트에 막힌다(routines.md).
  ⇒ 작동하는 유일한 길 = 미리 등록해둔 저녁 재시도 루틴(R4)이 '리셋된 신선 창'에서
     오늘 보고서가 이미 났는지 싸게 판정하고, 안 났으면 그때 풀 보고서를 낸다.
     5시간 롤링 리셋을 '시간 간격'으로 넘긴다.

이 스크립트는 그 판정을 오프라인·결정적·무네트워크(<0.1초)로 제공한다.

■ 두 가지 재시도 경로 (용도별):
  A. 동적 self-arm/disarm [2026-07-16 정훈 제안 — 대화 세션·권한되는 세션]:
     세션/보고서 시작 시 PM이 '재개 원샷 트리거'를 리셋 추정시각(reset_est)에 걸어둔다(arm)
     → 안 막히고 완주하면 그 트리거를 스스로 삭제(disarm) → 막히면 트리거가 남아 리셋 때 발동.
     이 스크립트는 그 트리거 id를 마커에 보관(--set-trigger)·조회(--get-trigger)해 접착제 역할.
     실제 트리거 생성/삭제는 MCP 도구(create_trigger/delete_trigger)라 PM이 호출한다.
  B. 고정 파수꾼 폴백 [R4a/R4b cron]: 무인 루틴은 트리거 자가생성 권한이 불안정하므로,
     미리 한 번 등록해둔 저녁 파수꾼이 --check로 판정해 미완이면 완주(성공한 날은 즉시 종료).

이 스크립트는 판정·상태보관을 오프라인·결정적·무네트워크(<0.1초)로 제공한다.

상태 파일 = data/app/report_run.json
  { "date": "YYYY-MM-DD",         # 이 실행이 겨냥한 거래일(KST)
    "target_version": 52,          # 이번에 내려는 보고서 번호(참고용)
    "status": "running"|"done",
    "session_kind": "R2"|"R4",     # 어느 루틴이 시작했나
    "started_at": ISO8601(KST),
    "completed_at": ISO8601(KST)|null,
    "reset_est": ISO8601(KST),     # started_at + 5h = 이 세션 첫사용 기준 추정 리셋(= arm 시각)
    "resume_trigger_id": "trig_..."|null }  # arm해둔 재개 원샷 트리거(완주 시 disarm 대상)

서브커맨드:
  --start [--kind R2|R4] [--version N]
        오늘 실행 시작 마커 기록(status=running, started_at=now, reset_est=+5h).
        보고서 루틴(R2)·재시도 루틴(R4)의 '첫 액션'으로 호출.
  --done
        오늘 실행 완료 마커 기록(status=done, completed_at=now).
        validate PASS·커밋 직전에만 호출(성공 신호). 완주했으므로 resume_trigger_id가 있으면 PM이 disarm.
  --check
        오늘(평일) 풀 보고서가 완료됐는지 판정 → 재시도 경로가 소비.
        exit 0 = 완료(재시도 불필요, 즉시 종료하라는 뜻)
        exit 1 = 미완료(토큰에 막혀 못 냈다 → 지금 보고서를 내라는 뜻)
        (주말은 평일 보고서 대상이 아니므로 항상 완료 취급 exit 0.)
  --set-trigger ID
        방금 arm한 재개 원샷 트리거의 id를 오늘 마커에 보관(disarm 대상).
  --get-trigger
        마커에 보관된 재개 트리거 id를 stdout에 출력(완주 후 삭제할 대상).
        있으면 exit 0(id 한 줄), 없으면 exit 1(빈 출력).
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except Exception:  # pragma: no cover
    from datetime import timezone
    KST = timezone(timedelta(hours=9))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
MARKER = os.path.join(ROOT, "data", "app", "report_run.json")
REPORTS = os.path.join(ROOT, "docs", "reports")
ROLLING_HOURS = 5  # 토큰 5시간 롤링 리셋


def now_kst():
    return datetime.now(KST)


def today_str(dt=None):
    return (dt or now_kst()).strftime("%Y-%m-%d")


def load_marker():
    try:
        with open(MARKER, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_marker(d):
    os.makedirs(os.path.dirname(MARKER), exist_ok=True)
    with open(MARKER, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")


def primary_report_path(day):
    """그 거래일의 '기본' 풀 보고서 = report_v{N}_{day}.md (부록 접미사 없음).
    _night·_midday·_scenario 같은 부록은 제외한다."""
    hits = []
    for p in glob.glob(os.path.join(REPORTS, f"report_v*_{day}.md")):
        base = os.path.basename(p)
        if re.fullmatch(rf"report_v\d+(?:\.\d+)?_{re.escape(day)}\.md", base):
            hits.append(p)
    return sorted(hits)[-1] if hits else None


def parse_iso(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def cmd_start(args):
    now = now_kst()
    day = today_str(now)
    marker = {
        "date": day,
        "target_version": args.version,
        "status": "running",
        "session_kind": args.kind,
        "started_at": now.isoformat(timespec="seconds"),
        "completed_at": None,
        "reset_est": (now + timedelta(hours=ROLLING_HOURS)).isoformat(timespec="seconds"),
        "resume_trigger_id": None,
    }
    save_marker(marker)
    print(f"[report_guard] START {args.kind} {day} v{args.version or '?'} "
          f"@ {now.strftime('%H:%M')} · 추정 리셋 {marker['reset_est'][11:16]} (첫사용+5h)")
    print(f"[report_guard] arm 안내: 재개 원샷 트리거를 run_once_at={marker['reset_est']} 로 걸고 "
          f"--set-trigger <id> 로 보관하라(완주 시 --get-trigger→delete).")
    return 0


def cmd_set_trigger(args):
    day = today_str()
    marker = load_marker()
    if marker.get("date") != day:
        marker = {"date": day, "status": marker.get("status", "running")}
    marker["resume_trigger_id"] = args.set_trigger
    save_marker(marker)
    print(f"[report_guard] arm 트리거 보관: {args.set_trigger} (완주 시 disarm 대상)")
    return 0


def cmd_get_trigger(args):
    marker = load_marker()
    tid = marker.get("resume_trigger_id")
    if tid:
        print(tid)  # stdout = 삭제할 trigger_id 한 줄(PM이 delete_trigger에 사용)
        return 0
    return 1


def cmd_done(args):
    now = now_kst()
    day = today_str(now)
    marker = load_marker()
    if marker.get("date") != day:
        # start 없이 done만 부른 경우도 안전하게 완료 기록
        marker = {"date": day, "target_version": args.version, "session_kind": args.kind or "R2",
                  "started_at": None, "reset_est": None}
    marker["status"] = "done"
    marker["completed_at"] = now.isoformat(timespec="seconds")
    if args.version:
        marker["target_version"] = args.version
    save_marker(marker)
    print(f"[report_guard] DONE {marker.get('session_kind','?')} {day} "
          f"v{marker.get('target_version') or '?'} @ {now.strftime('%H:%M')}")
    return 0


def cmd_check(args):
    now = now_kst()
    day = today_str(now)

    if now.weekday() >= 5:
        print(f"[report_guard] {day} 주말 — 평일 보고서 대상 아님 → 완료 취급(재시도 불필요).")
        return 0

    marker = load_marker()
    primary = primary_report_path(day)

    # 오늘 마커가 'running'이면 = 시작했으나 완주 못 함(토큰에 막힘) → 재시도 필요
    if marker.get("date") == day and marker.get("status") == "running":
        st = marker.get("started_at", "?")
        rs = marker.get("reset_est", "")
        st_hm = st[11:16] if isinstance(st, str) and len(st) >= 16 else "?"
        rs_hm = rs[11:16] if isinstance(rs, str) and len(rs) >= 16 else "?"
        print(f"[report_guard] {day} R{marker.get('session_kind','?')[-1:]}가 {st_hm} 시작 후 "
              f"미완(토큰 추정) · 추정 리셋 {rs_hm} → 지금 재시도 진행. exit=1")
        return 1

    if marker.get("date") == day and marker.get("status") == "done":
        print(f"[report_guard] {day} 보고서 완료(done @ "
              f"{str(marker.get('completed_at',''))[11:16]}) → 재시도 불필요. exit=0")
        return 0

    # 마커가 없거나 옛날 것 → 파일 존재로 판정(구버전·수동 보고서 호환)
    if primary:
        print(f"[report_guard] {day} 보고서 파일 존재({os.path.basename(primary)}) "
              f"→ 완료 취급(재시도 불필요). exit=0")
        return 0

    print(f"[report_guard] {day} 오늘 풀 보고서 없음(마커·파일 모두 부재) "
          f"→ 미완 = 지금 보고서를 내라. exit=1")
    return 1


def main():
    ap = argparse.ArgumentParser(description="보고서 토큰-리셋 재시도 가드")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--start", action="store_true", help="시작 마커 기록(running)")
    g.add_argument("--done", action="store_true", help="완료 마커 기록(done)")
    g.add_argument("--check", action="store_true", help="오늘 보고서 완료 판정(exit 0/1)")
    g.add_argument("--set-trigger", dest="set_trigger", metavar="ID",
                   help="arm한 재개 트리거 id를 마커에 보관")
    g.add_argument("--get-trigger", dest="get_trigger", action="store_true",
                   help="보관된 재개 트리거 id 출력(없으면 exit 1)")
    ap.add_argument("--kind", default="R2", help="세션 종류 R2|R4 (기본 R2)")
    ap.add_argument("--version", type=int, default=None, help="보고서 번호(참고)")
    args = ap.parse_args()

    if args.start:
        return cmd_start(args)
    if args.done:
        return cmd_done(args)
    if args.check:
        return cmd_check(args)
    if args.set_trigger:
        return cmd_set_trigger(args)
    if args.get_trigger:
        return cmd_get_trigger(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
