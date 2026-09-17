#!/usr/bin/env python3
"""무인 루틴 커밋을 origin/main에 올린다 — 푸시는 모델이 아니라 런처가 한다.

★[2026-09-17 신설] 왜 필요한가 — **로컬 무인 루틴은 한 번도 스스로 푸시하지 못했다.**
  세션 기록 전수(9/1~9/17) 실측: `sdk-cli`(무인) 세션의 `git push origin HEAD:main`은
  **7/7회 전부 "requires approval"로 막혔다**(9/4·9/9 R1·9/9 R4b). 커밋은 통과했다.
  원인 = 허용목록 `Bash(git push origin HEAD:*)`의 `:*`는 **접두사 `git push origin HEAD` + 단어경계**로
  해석돼 `HEAD:main`과 매칭되지 않는다. 대화형 세션은 사람이 승인해서 몰랐다.
  9/9 R1은 그걸 뚫으려다 detached HEAD + 곁가지 브랜치(`r1-prefetch-0909`)를 만들었고 런처는 verdict=OK를 찍었다.
  ⇒ 모델에게 푸시를 맡기지 않는다. 런처가 claude 종료 후 이 스크립트를 부른다(권한 게이트 밖).

왜 단순 `git push`/`git rebase`가 아닌가 — 10:00 R1 시점의 **실제 상태**가 둘 다 막는다:
  ① origin/main이 거의 항상 앞서 있다 — `refresh-prices.yml`이 하루 두 번 `app/data.js`를 커밋한다.
  ② 워킹트리에 **다른 세션의 미완 작업**(추적 파일 수정)이 흔하다 — `git rebase`는 그 상태에서 거부한다.
     9/17 실측: R1 실행 중 대화형 세션 2개가 스크립트 6개·JSON을 고치고 있었다.
  ③ R1의 `build_app_data`와 시세 갱신 커밋이 **같은 `app/data.js`를 고친다** — 9/9 R1 리베이스 충돌이 정확히 이것.
  ⇒ **임시 worktree**를 origin/main에 붙여 거기서 cherry-pick → push. 사용자 워킹트리는 건드리지 않는다.
     생성물(`app/data.js`·`app/sw.js`) 충돌만 origin 쪽을 택한다 — 다음 `refresh-prices`가 커밋된 JSON에서
     다시 빌드하므로 잃는 것이 없다. 그 외 충돌은 **중단하고 CONFLICT로 보고**한다(자동 해결 금지).

⚠️ force push 없음. 언제나 origin/main 위에 쌓은 fast-forward만 올린다.
⚠️ 로컬 main은 그대로 둔다(체크아웃·리셋 금지 — 6/25 규약). 리베이스해 올렸으면 로컬은 origin과 갈라지고,
   다음 대화형 세션의 `git rebase origin/main`이 같은 패치를 건너뛴다(생성물만 다시 충돌할 수 있다).

결과(stdout 마지막 줄 `PUSH_RESULT=<값>`, 종료코드):
  NOTHING(0)  새 커밋 없음        OK(0)  fast-forward 푸시     OK_REBASED(0)  임시 worktree에서 쌓아 푸시
  GIT_STATE(3) 브랜치 밖·리베이스 중   CONFLICT(4) 생성물 외 충돌   FAILED(5) fetch/push 실패

사용:
  python3 routine_push.py --since <루틴 시작 전 HEAD>
  python3 routine_push.py --since <sha> --dry-run     # 판정만, 푸시·worktree 생성 안 함
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GENERATED = {"app/data.js", "app/sw.js"}      # 충돌 시 origin 쪽을 택해도 되는 생성물
LEDGER = os.path.join("data", "logs", "routines", "pushed.jsonl")   # 재적용해 올린 로컬 커밋(gitignore 하위)
CODES = {"NOTHING": 0, "OK": 0, "OK_REBASED": 0, "GIT_STATE": 3, "CONFLICT": 4, "FAILED": 5}


def git(*args, cwd=None, check=False):
    p = subprocess.run(["git", *args], cwd=cwd or REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()[:300]}")
    return p


def out(*args, cwd=None):
    return git(*args, cwd=cwd).stdout.strip()


def finish(result, detail=""):
    if detail:
        print(detail)
    print(f"PUSH_RESULT={result}")
    return CODES[result]


def push_ff(ref, cwd=None):
    for attempt in range(2):
        p = git("push", "-q", "origin", f"{ref}:refs/heads/main", cwd=cwd)
        if p.returncode == 0:
            return True, ""
        time.sleep(3 * (attempt + 1))
    return False, p.stderr.strip()[:300]


def replayed_shas():
    try:
        with open(os.path.join(REPO, LEDGER), encoding="utf-8") as f:
            return {json.loads(ln)["local"] for ln in f if ln.strip()}
    except (OSError, ValueError, KeyError):
        return set()


def record_replayed(commits, remote_head):
    path = os.path.join(REPO, LEDGER)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for c in commits:
            f.write(json.dumps({"local": c, "remote_head": remote_head,
                                "at": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")


def replay_on_origin(commits, dry_run=False):
    """origin/main에 붙인 임시 worktree에서 commits를 차례로 cherry-pick 후 푸시."""
    if dry_run:
        return finish("OK_REBASED", f"[dry-run] origin/main 위에 {len(commits)}커밋 재적용 예정")
    tmp = tempfile.mkdtemp(prefix="jd_push_")
    wt = os.path.join(tmp, "wt")
    try:
        p = git("worktree", "add", "-q", "--detach", wt, "origin/main")
        if p.returncode != 0:
            return finish("FAILED", f"worktree 생성 실패: {p.stderr.strip()[:300]}")
        for c in commits:
            p = git("cherry-pick", "--allow-empty", c, cwd=wt)
            if p.returncode == 0:
                continue
            conflicted = set(out("diff", "--name-only", "--diff-filter=U", cwd=wt).splitlines())
            if not conflicted or not conflicted <= GENERATED:
                git("cherry-pick", "--abort", cwd=wt)
                other = sorted(conflicted - GENERATED) or ["(충돌 파일 판독 실패)"]
                return finish("CONFLICT", f"{c[:7]} 충돌 — 생성물 외 파일: {', '.join(other)} "
                                          f"(대화형 세션에서 수동 해결)")
            for f in conflicted:
                git("checkout", "--ours", "--", f, cwd=wt, check=True)
                git("add", "--", f, cwd=wt, check=True)
            env_commit = git("-c", "core.editor=true", "cherry-pick", "--continue", cwd=wt)
            if env_commit.returncode != 0:
                git("commit", "--allow-empty", "--no-edit", cwd=wt)
            print(f"{c[:7]} 생성물 충돌 {sorted(conflicted)} → origin 쪽 유지(refresh-prices가 재빌드)")
        ok, err = push_ff("HEAD", cwd=wt)
        if not ok:
            return finish("FAILED", f"push 실패: {err}")
        record_replayed(commits, out("rev-parse", "HEAD", cwd=wt))
        return finish("OK_REBASED", f"origin/main ← {out('rev-parse', '--short', 'HEAD', cwd=wt)} "
                                    f"({len(commits)}커밋 재적용 · 로컬 main은 갈라진 채 유지)")
    finally:
        git("worktree", "remove", "--force", wt)
        git("worktree", "prune")
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="무인 루틴 커밋을 origin/main에 fast-forward로 올린다(런처 전용)")
    ap.add_argument("--since", required=True, help="루틴 시작 전 HEAD sha")
    ap.add_argument("--dry-run", action="store_true", help="판정만 하고 푸시하지 않는다")
    ap.add_argument("--repo", default=None, help="대상 저장소(기본 = 이 레포 · 샌드박스 검증용)")
    a = ap.parse_args()
    global REPO
    if a.repo:
        REPO = os.path.abspath(a.repo)

    head = out("rev-parse", "HEAD")
    since = out("rev-parse", "--verify", "-q", a.since + "^{commit}")
    if not since:
        return finish("GIT_STATE", f"--since {a.since}를 커밋으로 해석 못 함")
    if head == since:
        return finish("NOTHING")
    if git("merge-base", "--is-ancestor", since, head).returncode != 0:
        return finish("GIT_STATE", "시작 HEAD가 현재 HEAD의 조상이 아니다 — 루틴이 브랜치를 바꿨거나 리셋했다")
    rebasing = any(os.path.exists(os.path.join(REPO, out("rev-parse", "--git-path", d)))
                   for d in ("rebase-merge", "rebase-apply"))
    branch = out("symbolic-ref", "-q", "--short", "HEAD")
    if rebasing or not branch:
        return finish("GIT_STATE", f"리베이스 중이거나 detached HEAD (branch='{branch}') — 9/9 R1과 같은 상태")

    if git("fetch", "-q", "origin", "main").returncode != 0:
        return finish("FAILED", "fetch origin main 실패(네트워크)")
    commits = out("rev-list", "--reverse", f"{since}..{head}").splitlines()
    if git("merge-base", "--is-ancestor", "origin/main", head).returncode == 0:
        if a.dry_run:
            return finish("OK", f"[dry-run] fast-forward 가능 · {len(commits)}커밋")
        ok, err = push_ff("HEAD")
        return finish("OK" if ok else "FAILED", "" if ok else f"push 실패: {err}")
    # 루틴 시작 전부터 로컬에만 있던 커밋이 있으면 = 사람의 미푸시 작업 → 손대지 않는다(대화형 세션 몫).
    # 단 ①origin에 같은 패치가 이미 있는 것(`git cherry` '-') ②이 스크립트가 전에 재적용해 올린 것(원장)은 뺀다.
    #   ②가 없으면 재적용 푸시 다음 날부터 로컬 main이 갈라져 있어 **영원히 GIT_STATE**가 된다(샌드박스 T4 실측).
    done = replayed_shas()
    pending = [ln[2:] for ln in out("cherry", "origin/main", since).splitlines()
               if ln.startswith("+ ") and ln[2:] not in done]
    if pending:
        return finish("GIT_STATE", f"루틴 시작 전부터 origin/main에 없는 커밋 {len(pending)}건"
                                   f"({', '.join(c[:7] for c in pending[:5])}) — 사람의 미푸시 작업이 섞여 있어 손대지 않는다")
    return replay_on_origin(commits, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
