#!/usr/bin/env bash
# Stop 훅 (비차단·조건부): 보고서/앱 정본에 미커밋 변경이 있을 때만 validate_report.py를
# 돌려 FAIL이면 결과를 사용자에게 노출. 변경 없으면 침묵. 항상 exit 0(차단 안 함).
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0
changed=$(git status --porcelain -- docs/reports data/app/stocks.json data/app/tasks.json data/app/flows.json 2>/dev/null)
[ -z "$changed" ] && exit 0
out=$(python3 .claude/skills/portfolio-desk/scripts/validate_report.py 2>&1)
if printf '%s' "$out" | grep -q "FAIL"; then
  summary=$(printf '%s' "$out" | grep -E "❌" | head -8)
  msg=$(printf '⚠️ validate_report FAIL — 커밋 전 확인 요망:\n%s' "$summary" \
        | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')
  printf '{"systemMessage": %s}\n' "$msg"
fi
exit 0
