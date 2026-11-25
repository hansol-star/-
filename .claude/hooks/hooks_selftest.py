#!/usr/bin/env python3
"""hooks_selftest.py — .claude/hooks/*.sh 자가검증 (오프라인 · 실제 저장소엔 쓰기 없음) [2026-11-22 신설 — 감사 C7·C5·E3]

왜 있나:
  ① git-write-guard.sh는 9/1부터 '되돌릴 수 없는 git'을 막는다고 적혀 있었지만 자기 테스트가 없었다.
     11/22 감사에서 주입 9종을 넣어 보니 `push origin +HEAD:main`·`git -C <경로> reset --hard`·`stash`·`add -A`·
     `restore .`가 전부 통과했다(문자열 glob 판정의 사각). 가드는 **위반을 심어** 검증한다(8/22·8/24 교훈).
  ② session-start.sh의 KRX 시간대 문구가 9/14 개편 뒤 두 달 넘게 옛 구조(시간외단일가 16:00–18:00 · 18시 이후
     '종가 고정')를 매 세션 '정본 앵커'로 주입했다. 정본 = price_watch.market_open_kst — 이 표와 대조한다.

★[2026-11-24 K1 리뷰 H7 — 이 검사 자체가 변이를 못 잡았다] 경계(07:50·15:30·20:00)를 한 칸씩 옮긴 변이, 미국장 문구 파손,
  동기화 줄 삭제, origin 최신 보고서 줄 삭제가 전부 PASS였다(SESSION_START_NO_SYNC=1로만 돌렸고 경계를 안 찍었다).
  ⇒ ① 경계 양쪽(07:50/07:51·15:30/15:31·20:00/20:01) + 미국 ET 09:29/09:30/16:00(서머타임 앞뒤)
     ② 임시 저장소에서 **동기화를 켠** 시나리오(뒤처짐→자동 동기화 · 갈라짐→🚨 · origin 최신 보고서→v+1 · fetch 실패 →
        원인·마지막 성공 시각 · 클라우드/compact → 브랜치 불변)
     ③ 가드는 공유(GIT_GUARD_SHARED=1)·클라우드(0) 두 모드 + H2(여러 줄)·H3(디렉터리)·H4(commit -a·autostash)·
        H5(커밋 메시지·grep·heredoc의 '글자' = 통과)·H11(별칭·백틱·xargs) + 보존 파일 add 차단
     ④ 훅은 **settings.json에 적힌 명령 그대로**(bash -c) 실행한다 — 舊는 `bash <경로>`로 불러 실행 비트(H6)·공백 경로
        따옴표(K1-CONC-12) 문제를 가렸다. ⑤ validate-on-stop: 실행 실패 ≠ FAIL · 시간 초과 · 보존 기록 손상.

사용: python .claude/hooks/hooks_selftest.py   (selfcheck 게이트에 등록)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
SCRIPTS = os.path.join(ROOT, ".claude", "skills", "portfolio-desk", "scripts")
BASH = os.environ.get("HOOK_BASH", "bash")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")

# (명령, 막혀야 하나) — 공유 체크아웃 모드(GIT_GUARD_SHARED=1 · 저장소 = CLAUDE_PROJECT_DIR)
GUARD_CASES: list[tuple[str, bool]] = [
    # ── 막아야 한다 ──
    ("git push --force origin HEAD:main", True),
    ("git push origin HEAD:main --force", True),
    ("git push --force-with-lease origin HEAD:main", True),
    ("git push -f origin main", True),
    ("git push origin +HEAD:main", True),                       # 舊 통과(+refspec)
    ("git push origin :claude/old-branch", True),
    ("git push --delete origin claude/x", True),
    ("git push --mirror", True),
    ("git reset --hard origin/main", True),
    ("git -C /c/Users/sd182/portfolio-desk reset --hard HEAD", True),   # 舊 통과(-C)
    ("cd x && git -c core.x=y reset --hard", True),
    ("git reset --merge", True),
    ("git clean -fd", True),
    ("git clean -xf", True),
    ("git checkout main", True),
    ("git switch main", True),
    ("git switch claude/other", True),
    ("git checkout -b claude/new", True),
    ("git checkout -f", True),
    ("git checkout -- .", True),
    ("git checkout .", True),
    ("git restore .", True),                                     # 舊 통과
    ("git restore --source=HEAD --worktree -- .", True),
    ("git stash", True),                                         # 舊 통과
    ("git stash pop", True),
    ("git stash push -m wip", True),
    ("git add -A", True),                                        # 舊 통과
    ("git add .", True),
    ("git add --all", True),
    ("git add -u", True),
    ("git branch -D claude/x", True),
    ("git branch -f main HEAD", True),
    ("git update-ref -d refs/heads/x", True),
    ("git filter-branch --tree-filter x", True),
    ("git reflog expire --all", True),
    ("git gc --prune=now", True),
    ('bash -c "git reset --hard"', True),                        # 따옴표 안 git
    ("git status && git reset --hard", True),
    ("echo hi; git push origin +main", True),
    # ★[11/24 H2] 여러 줄 — 줄바꿈도 구분자 · 구간마다 모든 git
    ("git fetch origin main\ngit reset --hard origin/main", True),
    ("git add data/app/tasks.json\ngit commit -m x\ngit push --force origin HEAD:main", True),
    ("git status\ngit stash\ngit rebase origin/main\ngit stash pop", True),
    ("cd {ROOT}\ngit status\ngit checkout -- .", True),
    ("git log -1 # comment\ngit clean -fdx", True),
    ("git status\r\ngit reset --hard", True),
    ("cat <<'EOF' > /tmp/x\nsee git log\nEOF\ngit push -f origin HEAD:main", True),
    # ★[11/24 H3] 디렉터리·글롭 경로
    ("git checkout -- data/app", True),
    ("git restore data", True),
    ("git checkout HEAD -- data", True),
    ("git checkout HEAD~3 -- docs", True),
    ("git restore -s HEAD~3 -W docs", True),
    ("git restore -s origin/main -- docs data .claude", True),
    ("git checkout -- docs data", True),
    ("git restore -- '*.json'", True),
    ("git rm -rf docs", True),
    ("git rm -r .", True),
    # ★[11/24 H4] commit -a · 디렉터리 add · autostash
    ("git commit -a -m x", True),
    ("git commit -am x", True),
    ("git commit --all -m x", True),
    ("git add data/ && git commit -m report", True),
    ("git add docs/ data/app/ app/data.js && git commit -m r", True),
    ("git add -A docs/", True),
    ("git add docs/..", True),
    ("git rebase --autostash origin/main", True),
    ("git pull --rebase --autostash origin main", True),
    # ★[11/24 H11] 우회 형태
    ('git -c alias.x="reset --hard" x', True),
    ("git -c alias.x='!git reset --hard' x", True),
    ('"/c/Program Files/Git/cmd/git.exe" reset --hard', True),
    ("GIT.EXE reset --hard", True),
    ("echo `git reset --hard`", True),
    ('echo "$(git stash)"', True),
    ("echo . | xargs git checkout --", True),
    ("find . -name x -exec git checkout -- {} \\;", True),
    ("git read-tree -u --reset HEAD", True),
    ("git worktree remove --force x", True),
    ("git merge --abort", True),
    ("git checkout --detach origin/main", True),
    ("git checkout origin/main", True),
    ("git branch -M main", True),
    ("git update-ref refs/heads/main HEAD~3", True),
    ("git symbolic-ref HEAD refs/heads/main", True),
    ("git tag -d v1", True),
    ("git rm -r --cached .", True),
    ("git reset --keep HEAD~3", True),
    ("git branch -m main", True),
    ("git sparse-checkout set foo", True),
    ('git config --global alias.x "reset --hard"', True),
    ("git config core.hooksPath /dev/null", True),
    ("timeout 30 git reset --hard", True),
    ("env GIT_DIR=x git stash", True),
    ("FOO=1 git push -f", True),
    ("powershell -Command git reset --hard", True),
    ("cmd /c git stash", True),
    ("eval 'git reset --hard'", True),
    ("bash -lc 'git stash'", True),
    ("bash <<'EOF'\ngit reset --hard\nEOF", True),
    # ── 통과해야 한다(일상 git) ──
    ("git status --porcelain", False),
    ("git fetch -q origin main", False),
    ("git push origin HEAD:main", False),
    ("git push origin HEAD:main HEAD:claude/report-1105-sync", False),
    ("git log --oneline -5 origin/main", False),
    ("git diff --stat", False),
    ("git add data/app/tasks.json docs/reports/report_v142_2026-11-23.md", False),
    ("git add -A -- data/app/tasks.json", False),
    ("git commit -m 'x'", False),
    ("git restore --staged .", False),
    ("git restore -- data/app/tasks.json", False),
    ("git checkout origin/main -- data/app/tasks.json", False),
    ("git checkout -- data/app/tasks.json", False),
    ("git stash list", False),
    ("git stash create", False),
    ("git reset -q", False),
    ("git reset --soft origin/main", False),
    ("git rebase origin/main", False),
    ("git rebase --abort", False),
    ("git branch --show-current", False),
    ("git merge-base --is-ancestor origin/main HEAD", False),
    ("git clean -n", False),
    ("git clean -fn", False),
    ("git config --get alias.x", False),
    ("git config user.name t", False),
    ("git sparse-checkout list", False),
    ("git rm --cached -r data/tmp", False),
    ("git restore --staged data", False),
    ("python .claude/skills/portfolio-desk/scripts/git_sync.py --ff-only", False),
    ("echo 'git is great'", False),
    ("git status\ngit log -1", False),
    # ★[11/24 H5] git '글자'는 명령이 아니다
    ('git commit -m "가드: git stash 차단 규칙 추가"', False),
    ('git commit -m "fix: avoid git reset --hard in launcher"', False),
    ("git commit -m 'msg with -a flag'", False),
    ("git commit -F msg.txt data/app/tasks.json", False),
    ('python .claude/skills/portfolio-desk/scripts/git_sync.py --json -m "K1 guard: block git checkout -b and git stash" '
     "data/app/tasks.json", False),
    ("git commit -m \"$(cat <<'EOF'\nguard: git push --force blocked\nEOF\n)\"", False),
    ('grep -n "git reset --hard" file', False),
    ('grep -rn "git stash" docs/', False),
    ('rg "git checkout -b" .', False),
    ('echo "do not run git add -A"', False),
    ("python -c \"print('git push --force')\"", False),
    ("cat > /tmp/x.sh <<'EOF'\ngit checkout -- .\nEOF", False),
    ("cd /tmp/k1test && git add . && git commit -am x", False),   # 공유 체크아웃 밖(임시 저장소)
]

# 클라우드(새 클론) 모드 — 공유 체크아웃 규칙은 풀고 되돌릴 수 없는 것만 막는다(PM-2)
CLOUD_CASES: list[tuple[str, bool]] = [
    ("git push --force origin HEAD:main", True),
    ("git push origin HEAD:main --force", True),
    ("git push origin +HEAD:main", True),
    ("git reset --hard origin/main", True),
    ("git clean -fd", True),
    ("git checkout -f", True),
    ("git branch -D x", True),
    ("git filter-branch x", True),
    ("git -c alias.x='reset --hard' x", True),
    ("git merge --abort", True),
    ("git rm -rf docs", True),
    ("git stash", False),
    ("git stash pop", False),
    ("git checkout -b claude/x", False),
    ("git switch -c claude/x", False),
    ("git restore .", False),
    ("git checkout -- .", False),
    ("git add -A", False),
    ("git commit -am x", False),
    ("git rebase --autostash origin/main", False),
    ("git checkout origin/main", False),
]


def hook_cmd(name: str) -> str:
    """settings.json에 적힌 그 훅의 명령 문자열(그대로 bash -c로 실행한다 · ★H6·K1-CONC-12)."""
    with open(SETTINGS, encoding="utf-8") as f:
        d = json.load(f)
    for lst in d.get("hooks", {}).values():
        for m in lst:
            for h in m.get("hooks", []):
                if name in h.get("command", ""):
                    return h["command"]
    raise KeyError(name)


def run_hook(name: str, env_extra: dict, inp: str = "", project: str = ROOT, timeout: float = 90):
    alt = os.environ.get("HOOKS_SELFTEST_DIR")      # 회귀 확인용: 다른(예: 옛) 훅 사본을 같은 케이스로 돌린다
    src = alt or HERE
    if os.path.abspath(project) != ROOT and not os.path.exists(os.path.join(project, ".claude", "hooks", name)):
        shutil.copytree(src, os.path.join(project, ".claude", "hooks"), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__"))      # 설정 명령 = $CLAUDE_PROJECT_DIR 기준
    cmd = f'bash "{alt}/{name}"' if (alt and os.path.abspath(project) == ROOT) else hook_cmd(name)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": project, **env_extra}
    for k, v in list(env_extra.items()):
        if v is None:
            env.pop(k, None)
    return subprocess.run([BASH, "-c", cmd], input=inp, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, env=env, cwd=project)


def run_guard(cmd: str, shared: str = "1", kept_file: str | None = None) -> int:
    if ROOT[1:2] == ":":                                    # C:\x\y → /c/x/y (Git Bash)
        cmd = cmd.replace("{ROOT}", "/" + ROOT[0].lower() + ROOT[2:].replace(os.sep, "/"))
    cmd = cmd.replace("{ROOT}", ROOT)
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": ROOT})
    env = {"GIT_GUARD_SHARED": shared, "GIT_GUARD_KEPT_FILE": kept_file or os.path.join(ROOT, ".git", "_no_such_kept")}
    return run_hook("git-write-guard.sh", env, payload).returncode


def ctx_of(r) -> str:
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])["hookSpecificOutput"]["additionalContext"]
    except Exception:  # noqa: BLE001
        return ""


def run_session_start(at: str, project: str = ROOT, extra: dict | None = None, inp: str = "") -> str:
    env = {"SESSION_START_NOW": at, "SESSION_START_NO_SYNC": "1", **(extra or {})}
    return ctx_of(run_hook("session-start.sh", env, inp, project))


def main() -> int:  # noqa: C901
    fails: list[str] = []

    def chk(cond, what):
        if not cond:
            fails.append(what)
            print("  ❌", what)
        return cond

    print("⓪ settings.json 훅 명령 형태 — bash \"$CLAUDE_PROJECT_DIR/…\"(실행 비트·공백 경로 무관)")
    for h in ("git-write-guard.sh", "session-start.sh", "validate-on-stop.sh"):
        c = hook_cmd(h)
        chk(c.startswith('bash "$CLAUDE_PROJECT_DIR/.claude/hooks/') and c.endswith('"'), f"settings 명령 형태: {c}")
    ls = subprocess.run(["git", "-C", ROOT, "ls-files", "-s", "--", ".claude/hooks/"], capture_output=True, text=True).stdout
    nonexec = [ln.split("\t")[-1] for ln in ls.splitlines() if ln.startswith("100644") and ln.endswith(".sh")]
    if nonexec:
        print(f"  ℹ️ 실행 비트 없는 훅(설정이 bash로 부르므로 무해): {nonexec}")

    print("① git-write-guard.sh — 위반 주입(공유 체크아웃 모드)")
    n0 = len(fails)
    for cmd, should_block in GUARD_CASES:
        rc = run_guard(cmd)
        chk((rc == 2) if should_block else (rc == 0),
            f"guard[공유]: {'차단돼야' if should_block else '통과해야'} 하는데 rc={rc} — {cmd!r}")
    print(f"  {len(GUARD_CASES) - (len(fails) - n0)}/{len(GUARD_CASES)} 통과")
    print("①' 클라우드 모드(GIT_GUARD_SHARED=0)")
    n0 = len(fails)
    for cmd, should_block in CLOUD_CASES:
        rc = run_guard(cmd, shared="0")
        chk((rc == 2) if should_block else (rc == 0),
            f"guard[클라우드]: {'차단돼야' if should_block else '통과해야'} 하는데 rc={rc} — {cmd!r}")
    print(f"  {len(CLOUD_CASES) - (len(fails) - n0)}/{len(CLOUD_CASES)} 통과")
    print("①'' 옛 판 위 수정(git_sync_kept) 파일 add/commit 차단 · 비문자열 command")
    tmpd = tempfile.mkdtemp(prefix="hooks_selftest_")
    try:
        kf = os.path.join(tmpd, "kept.json")
        with open(kf, "w", encoding="utf-8") as f:
            json.dump({"data/app/tasks.json": "0" * 40}, f)
        chk(run_guard("git add data/app/tasks.json", kept_file=kf) == 2, "guard: 보존 파일 add 차단")
        chk(run_guard("git commit -m x -- data/app/tasks.json", kept_file=kf) == 2, "guard: 보존 파일 commit 차단")
        chk(run_guard("git add docs/master.md", kept_file=kf) == 0, "guard: 보존 아닌 파일 add 통과")
        r = run_hook("git-write-guard.sh", {"GIT_GUARD_SHARED": "1"},
                     json.dumps({"tool_input": {"command": ["git", "reset", "--hard"]}, "cwd": ROOT}))
        chk(r.returncode == 2 and "Traceback" not in r.stderr, f"guard: 리스트 command도 판정(traceback 없음) rc={r.returncode}")

        print("② session-start.sh — KRX 경계 ↔ price_watch.market_open_kst 대조")
        sys.path.insert(0, SCRIPTS)
        try:
            import price_watch  # noqa: E402
        except Exception as e:  # noqa: BLE001
            fails.append(f"price_watch import 실패: {e}")
            price_watch = None
        day = "2026-11-23"   # 월요일
        cases = [("06:59", "개장 전", None), ("07:00", "프리마켓 중", "KRX 프리마켓"), ("07:50", "프리마켓 중", "KRX 프리마켓"),
                 ("07:51", "정규장 개장 전", None), ("08:59", "정규장 개장 전", None), ("09:00", "정규장 중", "KRX 정규장"),
                 ("15:30", "정규장 중", "KRX 정규장"), ("15:31", "정규장 마감", None), ("15:59", "정규장 마감", None),
                 ("16:00", "애프터마켓 중", "KRX 애프터마켓"), ("20:00", "애프터마켓 중", "KRX 애프터마켓"),
                 ("20:01", "장 종료", None)]
        for hm, word, pw_name in cases:
            ctx = run_session_start(f"{day}T{hm}")
            line = next((ln for ln in ctx.splitlines() if ln.startswith("- KRX")), "")
            chk(word in line, f"session-start {hm}: KRX 문구에 '{word}' 없음 — {line[:80]}")
            label = line.split("※")[0]
            chk("시간외단일가" not in label and "종가 고정" not in label, f"session-start {hm}: 폐지된 시간외단일가 문구")
            if price_watch is not None:
                now = datetime.fromisoformat(f"{day}T{hm}").replace(tzinfo=timezone(timedelta(hours=9)))
                is_open, name = price_watch.market_open_kst(now)
                if pw_name:
                    chk(is_open and name == pw_name, f"session-start {hm}: 훅 '{word}' ↔ price_watch ({is_open}, {name})")
                else:
                    chk(not (is_open and str(name).startswith("KRX")), f"session-start {hm}: 훅은 닫힘인데 price_watch = {name}")
        print("②' 미국장 경계(서머타임 앞뒤)")
        us_cases = [("2026-11-23T23:29", "개장 전"), ("2026-11-23T23:30", "정규장 중"), ("2026-11-24T05:59", "정규장 중"),
                    ("2026-11-24T06:00", "장 마감"), ("2026-07-15T22:29", "개장 전"), ("2026-07-15T22:30", "정규장 중"),
                    ("2026-07-16T04:59", "정규장 중"), ("2026-07-16T05:00", "장 마감")]
        for at, word in us_cases:
            line = next((ln for ln in run_session_start(at).splitlines() if ln.startswith("- 미국장")), "")
            # 주의 문구 안의 '정규장 중'에 속지 않게 라벨(※ 앞)만 본다
            chk(word in line.split("※")[0] and "공휴일" in line, f"session-start {at}: 미국장 '{word}'·공휴일 주의 — {line[:90]}")
        ctx = run_session_start("2026-11-22T10:00")      # 일요일
        chk("주말 휴장" in ctx, "session-start 일요일: '주말 휴장' 없음")
        for need in ("오늘(KST): 2026-11-22 (일)", "최신 보고서:", "정훈 폰: 지금 불가(주말)"):
            chk(need in ctx, f"session-start: 앵커 줄 누락 — {need}")
        # ★H12(3) 인코딩 env 없이도 · ★K1-CONC-12 공백 경로
        r = run_hook("session-start.sh", {"SESSION_START_NO_SYNC": "1", "PYTHONUTF8": None, "PYTHONIOENCODING": None})
        chk("오늘(KST)" in ctx_of(r), "session-start: PYTHONUTF8 없이도 출력(cp949)")
        sp = os.path.join(tmpd, "dir with space")
        shutil.copytree(HERE, os.path.join(sp, ".claude", "hooks"))
        shutil.copy(SETTINGS, os.path.join(sp, ".claude", "settings.json"))
        r = run_hook("session-start.sh", {"SESSION_START_NO_SYNC": "1"}, project=sp)
        chk(r.returncode == 0 and "오늘(KST)" in ctx_of(r), f"session-start: 공백 있는 프로젝트 경로 rc={r.returncode}")
        # ★H8 git_sync가 JSON null·리스트를 내도 앵커는 남는다
        for bad in ("null", "[1]"):
            stub = os.path.join(tmpd, f"stub_{len(bad)}")
            os.makedirs(os.path.join(stub, ".claude", "skills", "portfolio-desk", "scripts"))
            with open(os.path.join(stub, ".claude", "skills", "portfolio-desk", "scripts", "git_sync.py"), "w") as f:
                f.write(f"print('{bad}')\n")
            r = run_hook("session-start.sh", {"GIT_GUARD_SHARED": "1", "SESSION_START_NOW": "2026-11-23T10:00"}, project=stub)
            chk("오늘(KST)" in ctx_of(r), f"session-start: git_sync 출력 {bad}여도 앵커 유지")

        print("③ session-start.sh — 동기화 켠 시나리오(임시 저장소)")
        sync_scenarios(tmpd, chk)

        print("④ validate-on-stop.sh — 실행 실패·시간 초과·FAIL·보존 기록")
        stop_scenarios(tmpd, chk)
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)

    print(f"hooks selftest: {'PASS' if not fails else 'FAIL'} ({len(fails)} 실패)")
    for f in fails:
        print("  -", f)
    return 0 if not fails else 1


def _sh(cwd, *a):
    r = subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(a)}: {r.stderr}")
    return r.stdout


def _wr(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def _repo(tmpd, tag, files):
    d = os.path.join(tmpd, tag)
    bare, local, cloud = (os.path.join(d, x) for x in ("remote.git", "local", "cloud"))
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", cloud], check=True)
    for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
        _sh(cloud, "config", k, v)
    for p, s in files.items():
        _wr(os.path.join(cloud, p), s)
    _sh(cloud, "add", "-A")
    _sh(cloud, "commit", "-q", "-m", "init")
    _sh(cloud, "remote", "add", "origin", bare)
    _sh(cloud, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", bare, local], check=True, capture_output=True)
    for k, v in (("user.name", "t"), ("user.email", "t@t")):
        _sh(local, "config", k, v)
    _sh(local, "checkout", "-q", "-b", "claude/feat")
    dst = os.path.join(local, ".claude", "skills", "portfolio-desk", "scripts")
    os.makedirs(dst)
    shutil.copy(os.path.join(SCRIPTS, "git_sync.py"), dst)      # 미추적 사본(훅이 상대 경로로 부른다)
    return bare, local, cloud


def _cloud_commit(cloud, changes):
    for p, s in changes.items():
        _wr(os.path.join(cloud, p), s)
    _sh(cloud, "add", "-A")
    _sh(cloud, "commit", "-q", "-m", "cloud")
    _sh(cloud, "push", "-q", "origin", "main")


def sync_scenarios(tmpd, chk):
    at = {"SESSION_START_NOW": "2026-11-23T10:00"}
    start = json.dumps({"source": "startup"})
    files = {"A.txt": "a\n", "docs/reports/report_v2_2026-11-20.md": "r2\n"}

    def head(p):
        return _sh(p, "rev-parse", "HEAD").strip()

    # a. 뒤처짐 → 자동 동기화(공유)
    bare, local, cloud = _repo(tmpd, "sync_a", files)
    _cloud_commit(cloud, {"A.txt": "a cloud\n"})
    r = run_hook("session-start.sh", {**at, "GIT_GUARD_SHARED": "1"}, start, local)
    ctx = ctx_of(r)
    chk("자동 동기화 완료" in ctx and head(local) == _sh(bare, "rev-parse", "main").strip(),
        f"sync a: 뒤처지면 자동 동기화 — {ctx[-200:]!r}")
    # b. 클라우드 모드 → 브랜치 불변 · c. compact → 브랜치 불변
    for tag, env, inp in (("sync_b", {"GIT_GUARD_SHARED": "0"}, start),
                          ("sync_c", {"GIT_GUARD_SHARED": "1"}, json.dumps({"source": "compact"}))):
        bare, local, cloud = _repo(tmpd, tag, files)
        h0 = head(local)
        _cloud_commit(cloud, {"A.txt": "a cloud\n"})
        _sh(local, "fetch", "-q", "origin", "main")
        ctx = ctx_of(run_hook("session-start.sh", {**at, **env}, inp, local))
        chk(head(local) == h0 and "자동 동기화 완료" not in ctx and "오늘(KST)" in ctx,
            f"{tag}: 훅이 브랜치를 옮기지 않는다(클라우드·compact) — {ctx[-160:]!r}")
        if tag == "sync_b":
            chk("클라우드 클론" in ctx and "🚨" not in ctx, f"sync b: 클라우드 문구(🚨 없음) — {ctx[-160:]!r}")
    # d. 갈라짐 + origin에 더 새 보고서 → 🚨 · 다음 번호 = origin 기준
    bare, local, cloud = _repo(tmpd, "sync_d", files)
    _wr(os.path.join(local, "X.txt"), "local only\n")
    _sh(local, "add", "X.txt")
    _sh(local, "commit", "-q", "-m", "local only")
    _cloud_commit(cloud, {"docs/reports/report_v3_2026-11-21.md": "r3\n"})
    ctx = ctx_of(run_hook("session-start.sh", {**at, "GIT_GUARD_SHARED": "1"}, start, local))
    chk("🚨 체크아웃이 origin/main보다" in ctx and "갈라짐" in ctx, f"sync d: 갈라짐 🚨 — {ctx[-240:]!r}")
    chk("origin에 더 새 보고서 v3" in ctx and "v4" in ctx, "sync d: origin 최신 보고서 v3 → 다음 v4")
    # e. fetch 실패 → 원인·마지막 성공 시각 · '= origin/main' 주장 안 함
    bare, local, cloud = _repo(tmpd, "sync_e", files)
    run_hook("session-start.sh", {**at, "GIT_GUARD_SHARED": "1"}, start, local)     # 성공 fetch 기록
    _sh(local, "remote", "set-url", "origin", "http://127.0.0.1:1/repo.git")
    ctx = ctx_of(run_hook("session-start.sh", {**at, "GIT_GUARD_SHARED": "1"}, start, local))
    chk("origin 확인 불가" in ctx and "연결 실패" in ctx and "= origin/main" not in ctx and "분 전" in ctx,
        f"sync e: fetch 실패 원인·마지막 성공 시각 — {ctx[-240:]!r}")


def stop_scenarios(tmpd, chk):
    def repo(tag, validate_src):
        d = os.path.join(tmpd, tag)
        subprocess.run(["git", "init", "-q", "-b", "main", d], check=True)
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
            _sh(d, "config", k, v)
        _wr(os.path.join(d, "data/app/tasks.json"), "{}\n")
        _sh(d, "add", "data/app/tasks.json")
        _sh(d, "commit", "-q", "-m", "i")
        _wr(os.path.join(d, "data/app/tasks.json"), '{"x":1}\n')
        sd = os.path.join(d, ".claude", "skills", "portfolio-desk", "scripts")
        os.makedirs(sd)
        shutil.copy(os.path.join(SCRIPTS, "git_sync.py"), sd)
        _wr(os.path.join(sd, "validate_report.py"), validate_src)
        return d

    def msg(d, extra=None):
        r = run_hook("validate-on-stop.sh", extra or {}, "", d)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])["systemMessage"]
        except Exception:  # noqa: BLE001
            return ""
    m = msg(repo("stop_crash", "import no_such_module_xyz\n"))
    chk("실행 실패" in m and "FAIL" not in m, f"stop: validate 실행 실패 ≠ FAIL — {m!r}")
    m = msg(repo("stop_slow", "import time\ntime.sleep(8)\n"), {"VALIDATE_TIMEOUT": "2"})
    chk("시간 초과" in m, f"stop: validate 시간 초과 — {m!r}")
    d = repo("stop_fail", "print('❌ 보유 풀표 누락')\nraise SystemExit(1)\n")
    m = msg(d)
    chk("FAIL" in m and "보유 풀표 누락" in m, f"stop: FAIL 목록 — {m!r}")
    with open(os.path.join(d, ".git", "git_sync_kept.json"), "w", encoding="utf-8") as f:
        f.write("null")
    m = msg(d)
    chk("손상" in m, f"stop: 보존 기록 손상 경고 — {m!r}")


if __name__ == "__main__":
    sys.exit(main())
