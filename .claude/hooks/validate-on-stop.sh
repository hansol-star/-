#!/usr/bin/env bash
# Stop 훅 (비차단·조건부): 보고서/앱 정본에 미커밋 변경이 있을 때만 validate_report.py를
# 돌려 FAIL이면 결과를 사용자에게 노출. 변경 없으면 침묵. 항상 exit 0(차단 안 함).
#
# ★[2026-11-22 개정 — 감사 C8·AX-F-07·K1]
#   ① 감시 정본을 넓혔다 — 舊엔 보고서·stocks·tasks·flows만 봤다. 체결 원장·portfolio·결정 원장·CLAUDE.md·master도
#      손으로 고치는 정본인데 미커밋으로 남아도 아무도 몰랐다.
#   ② 커밋은 됐는데 origin/main에 없는 정본(미푸시)과, 옛 판 위에 남은 수정(.git/git_sync_kept.json)을 알린다 —
#      git_sync.py --status(읽기 전용 · fetch 안 함 = 마지막으로 받은 origin 기준).
#
# ★[2026-11-24 K1 리뷰 H9·K1-CONC-01]
#   ① validate_report가 **죽으면**(ImportError·traceback) 舊는 'FAIL — 확인 요망:' 뒤에 빈 목록을 띄웠다 → 실행 실패와
#      FAIL을 가른다(rc=1 + ❌ 줄 = FAIL · 그 밖 = 실행 실패 + 마지막 줄). 시간 제한 VALIDATE_TIMEOUT(기본 45초 < 설정 60초)
#      — 舊는 멈추면 훅째 죽어 아무 말도 없었다.
#   ② `git status`가 매 Stop마다 index.lock을 잡아 동시에 도는 git_sync ff의 인덱스 교체와 부딪쳤다 →
#      `--no-optional-locks`(읽기만 · 인덱스 갱신 안 씀).
#   ③ 보존 기록 손상(kept_corrupt)·중단된 ff 저널도 알린다.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0
msgs=""
changed=$(git --no-optional-locks status --porcelain -- docs/reports data/app/stocks.json data/app/tasks.json data/app/flows.json \
          .claude/skills/portfolio-desk/portfolio.json data/app/trades.jsonl data/app/decisions.jsonl CLAUDE.md docs/master.md 2>/dev/null)
if [ -n "$changed" ]; then
  # [7/13 교정] 판정 = exit code (FAIL 있으면 1). 문자열 grep "FAIL"은 통과 문구
  # "✅ FAIL 없음"에도 걸려 WARN-only에서 오탐 systemMessage를 띄우던 버그.
  out=$(timeout "${VALIDATE_TIMEOUT:-45}" python3 .claude/skills/portfolio-desk/scripts/validate_report.py 2>&1)
  rc=$?
  if [ "$rc" -ne 0 ]; then
    summary=$(printf '%s' "$out" | grep -E "❌" | head -8)
    if [ "$rc" -eq 124 ]; then
      msgs=$(printf '⚠️ validate_report 시간 초과(%s초) — 판정 못 함, 커밋 전 수동 실행 요망' "${VALIDATE_TIMEOUT:-45}")
    elif [ "$rc" -eq 1 ] && [ -n "$summary" ]; then
      msgs=$(printf '⚠️ validate_report FAIL — 커밋 전 확인 요망:\n%s' "$summary")
    else
      last=$(printf '%s' "$out" | sed '/^[[:space:]]*$/d' | tail -n 1 | cut -c1-200)
      msgs=$(printf '⚠️ validate_report 실행 실패(rc=%s) — 판정 못 함: %s' "$rc" "$last")
    fi
  fi
fi
st=$(timeout 15 python3 .claude/skills/portfolio-desk/scripts/git_sync.py --status --json 2>/dev/null | tail -n 1)
extra=$(ST="$st" python3 -c '
import json, os
try:
    s = json.loads(os.environ.get("ST") or "{}")
except Exception:
    s = {}
if not isinstance(s, dict):
    s = {}
out = []
if s.get("ahead_canon"):
    out.append("⚠️ origin/main에 없는 로컬 커밋이 정본을 건드렸다(미푸시): " + ", ".join(s["ahead_canon"][:5]))
if s.get("kept"):
    out.append("⚠️ 옛 판 위에 남은 수정(git_sync_kept): " + ", ".join(list(s["kept"])[:5])
               + " — git_sync.py로 올리거나(자동 병합) 손으로 합친 뒤 git_sync.py --resolved <파일>")
if s.get("kept_corrupt"):
    out.append("🚨 .git/git_sync_kept.json 손상 — git_sync가 ff·publish를 멈췄다. 확인·복구할 것")
if s.get("journal_pending"):
    out.append("⚠️ 중단된 git_sync ff 저널 — git_sync.py --ff-only로 마무리할 것")
ol, ll = s.get("origin_latest"), s.get("local_latest")
if isinstance(ol, int) and isinstance(ll, int) and ol > ll:
    out.append("🚨 origin에 더 새 보고서 v%d (로컬 v%d) — git_sync.py --ff-only로 맞출 것" % (ol, ll))
print("\n".join(out))
' 2>/dev/null)
if [ -n "$extra" ]; then
  msgs=$(printf '%s\n%s' "$msgs" "$extra")
fi
msgs=$(printf '%s' "$msgs" | sed '/^$/d')
if [ -n "$msgs" ]; then
  msg=$(printf '%s' "$msgs" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')
  printf '{"systemMessage": %s}\n' "$msg"
fi
exit 0
