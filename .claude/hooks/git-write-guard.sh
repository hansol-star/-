#!/usr/bin/env bash
# 정훈 증권 — git 파괴적 명령 차단 훅 (PreToolUse · Bash)
#
# 왜 있나 [9/1 신설]:
#   무인 루틴(R1~R4b)이 커밋을 못 해 연속성 규약이 파손돼 있었다(9/1 R1 실측 —
#   작업은 다 하고 git add/commit/push가 승인 대기로 실패, 그런데 verdict=OK).
#   고치려면 settings.json allow에 git 쓰기 권한을 열어야 하는데, allow는 **접두사 매칭**이라
#   `git push origin HEAD:main --force` 처럼 **뒤에 붙는 플래그를 못 막는다.**
#   deny 목록도 같은 접두사 한계를 갖는다 ⇒ 인자 순서와 무관하게 보는 장치가 필요하다.
#
# 무엇을 막나 (되돌릴 수 없는 것만 — 일상 git은 건드리지 않는다):
#   ① force push       : origin 히스토리 파괴 = 다른 세션의 작업 소실
#   ② reset --hard     : 워킹트리 소실 (R1이 남긴 미커밋 작업물이 실제로 이렇게 날아갈 수 있다)
#   ③ clean -f/-x      : 추적 안 되는 파일(자막·프레임 캐시) 소실
#   ④ checkout main    : 6/25 교정 — 로컬 main이 origin/main과 unrelated 히스토리라 깨진다
#   ⑤ branch -D / push :삭제 : 브랜치 삭제
#
# 규약: exit 2 = 차단(stderr가 모델에게 전달됨) · exit 0 = 통과.
# ⚠️ 이 훅은 Bash 도구만 본다. 다른 경로(스크립트 안의 subprocess)는 안 지나간다 —
#    가드의 사각을 숨기지 않기 위해 여기 적어둔다.
set -uo pipefail

payload="$(cat)"
cmd="$(printf '%s' "$payload" | python3 -c 'import sys,json;print((json.load(sys.stdin).get("tool_input") or {}).get("command",""))' 2>/dev/null || true)"
[ -z "$cmd" ] && exit 0

# git 명령이 아니면 관심 없다
printf '%s' "$cmd" | grep -Eq '(^|[;&|]|\s)git\s' || exit 0

block() { echo "🚫 git 파괴적 명령 차단: $1" >&2
          echo "   (.claude/hooks/git-write-guard.sh — 정훈이 직접 실행할 것)" >&2
          exit 2; }

norm="$(printf '%s' "$cmd" | tr -s ' ')"

case "$norm" in
  *"git push"*) case "$norm" in
      *--force*|*" -f "*|*" -f"|*--mirror*|*--delete*|*" :"*) block "force/삭제 push" ;;
    esac ;;
esac
case "$norm" in
  *"git reset"*--hard*)      block "reset --hard (워킹트리 소실)" ;;
  *"git clean"*-f*|*"git clean"*-x*) block "clean -f/-x (미추적 파일 소실)" ;;
  *"git checkout main"*|*"git switch main"*) block "checkout main (6/25 교정 — 로컬 main 체크아웃 금지)" ;;
  *"git branch -D"*|*"git branch -d"*) block "branch 삭제" ;;
  *"git filter-branch"*|*"git reflog delete"*|*"git gc --prune"*) block "히스토리 재작성" ;;
esac
exit 0
