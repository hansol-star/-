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
# ★[2026-11-22 개정 — 감사 C7] 舊 판정은 명령 문자열 glob이라 +refspec·`git -C <경로> reset --hard`·stash·add -A·
#   restore .를 통과시켰다 ⇒ 명령을 토큰으로 나눠 git 호출마다 전역 옵션을 건너뛰고 하위 명령·인자를 본다.
#
# ★[2026-11-24 K1 리뷰 H2·H3·H4·H5·H11·PM-2] 11/22 판도 구멍·오탐이 컸다(주입 실측):
#   · H2: 여러 줄 명령에서 줄바꿈이 구분자가 아니었고, 구간마다 **첫 git만** 봤다 →
#     `git fetch …⏎git reset --hard`·`git status⏎git stash` 통과. ⇒ 줄바꿈·CR도 구분자, 구간의 **명령어 자리**를 본다.
#   · H5: 따옴표 안이든 아니든 'git <단어>'만 있으면 명령으로 봤다 → 커밋 메시지·grep 패턴·echo·heredoc 본문의
#     'git stash' 같은 **글자**가 차단됐다(publisher의 `git_sync.py -m "…git stash…"`도). ⇒ git은 구간의 명령어 자리
#     (VAR=·env·command·timeout·xargs·find -exec 뒤)일 때만, 따옴표 안은 셸 실행기(bash/sh -c·eval·powershell
#     -Command·cmd /c)의 인자일 때만, heredoc 본문은 셸에 먹일 때만 본다. $( )·`…` 치환 안은 본다.
#   · H3: 전체 경로(. :/)만 막았다 → `git checkout -- data/app`·`git restore -s HEAD~3 -W docs`가 다른 세션 WIP를
#     지웠다. ⇒ 디렉터리·글롭·'/'로 끝나는 경로·`docs/..`도 막는다(파일 경로만 허용).
#   · H4: `commit -a/-am/--all`·`--autostash`·`add docs/`가 통과했다(SKILL §3 절차가 바로 `git add docs/ data/app/`).
#     ⇒ 막는다. 그리고 .git/git_sync_kept.json의 **옛 판 위 수정** 파일을 add/commit하면 막는다(업스트림 되돌림).
#   · H11: 별칭(-c alias.*)·대문자/따옴표 git.exe·백틱·xargs/find -exec·read-tree -u·worktree remove --force·
#     merge --abort·checkout --detach/<원격 ref>·branch -M·update-ref refs/heads·symbolic-ref HEAD·tag -d 통과. ⇒ 막는다.
#   · PM-2: 클라우드 루틴(C2·C3·R3)도 이 설정으로 새 리눅스 클론에서 돈다 — 공유 체크아웃 규칙(stash·브랜치 전환·
#     전역 add·디렉터리 복원·commit -a·autostash)은 **로컬 공유 체크아웃에서만** 적용한다.
#     판정 = GIT_GUARD_SHARED=1/0(시험·수동) > CLAUDE_CODE_REMOTE 있으면 0 > 윈도우면 1, 그리고 대상 저장소(-C·cd 추적)가
#     CLAUDE_PROJECT_DIR 안일 때만(임시 저장소 /tmp 등은 공유 체크아웃이 아니다).
#
# 무엇을 막나 (되돌릴 수 없거나 다른 세션의 작업을 지우는 것만 — 일상 git은 건드리지 않는다):
#   [어디서나] ① force/삭제 push(+refspec·:refspec·--force*·-f·-d·--mirror·--delete·--prune)
#     ② reset --hard/--merge · merge --abort · checkout -f · read-tree -u · rm -f <디렉터리/전체>
#     ③ clean -f ④ branch -D/-d/-f/-M/-C · tag -d · update-ref -d · worktree remove --force
#     ⑤ filter-branch/filter-repo · reflog delete/expire · gc --prune · prune ⑥ -c alias.*(별칭으로 우회)
#   [공유 체크아웃만] ⑦ switch · checkout -b/-B/--orphan/--detach · checkout <브랜치·ref>(경로 아님) · symbolic-ref HEAD ·
#     update-ref refs/heads/* ⑧ stash(list·show·create 제외) · add -A/-u/./디렉터리/글롭 · commit -a/--all · --autostash
#     ⑨ checkout/restore(워킹트리)·rm의 디렉터리·글롭·전체 경로 · xargs/find -exec로 경로를 모르는 checkout/restore/add/rm
#     ⑩ 옛 판 위 수정(git_sync_kept) 파일의 add/commit
#
# 규약: exit 2 = 차단(stderr가 모델에게 전달됨) · exit 0 = 통과.
# ⚠️ 이 훅은 Bash 도구만 본다. 다른 경로(스크립트 안의 subprocess)는 안 지나간다.
#    별칭은 -c alias.*만 본다 — 저장소 설정에 이미 있는 별칭(`git x`)은 모른다. 변수로 만든 명령(`$G reset --hard`)도 모른다.
#    자가검증 = .claude/hooks/hooks_selftest.py (공유·클라우드 두 모드).
set -uo pipefail
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

payload="$(cat)"
GUARD_PAYLOAD="$payload" python3 - <<'PY'
import json, os, re, shlex, sys

try:
    pl = json.loads(os.environ.get("GUARD_PAYLOAD") or "{}")
except Exception:
    sys.exit(0)
ti = pl.get("tool_input") if isinstance(pl, dict) else None
cmd = ti.get("command") if isinstance(ti, dict) else None
if isinstance(cmd, list):                     # ★H11 — 문자열이 아니면 traceback으로 열리던 것
    cmd = " ".join(str(c) for c in cmd)
if not isinstance(cmd, str) or not re.search(r"git", cmd, re.I):
    sys.exit(0)


def win_path(p: str) -> str:
    m = re.match(r"^/([a-zA-Z])(/.*)?$", p)
    if m and sys.platform == "win32":
        return f"{m.group(1).upper()}:{m.group(2) or '/'}"
    return p


def norm(p: str) -> str:
    return os.path.normcase(os.path.normpath(win_path(p)))


PROJECT = norm(os.environ.get("CLAUDE_PROJECT_DIR") or "") if os.environ.get("CLAUDE_PROJECT_DIR") else ""
START_CWD = win_path(pl.get("cwd") or os.getcwd()) if isinstance(pl, dict) else os.getcwd()
_v = os.environ.get("GIT_GUARD_SHARED", "")
SHARED_ENV = (_v == "1") if _v in ("0", "1") else (not os.environ.get("CLAUDE_CODE_REMOTE") and sys.platform == "win32")
SEP = set(";&|()\n")
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "busybox"}
GLOBAL_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix",
                   "--config-env"}
ALLPATHS = {".", ":/", "*", ":/*", "./", ":"}


def block(why: str, shared_rule: bool = False):
    print(f"🚫 git 파괴적 명령 차단: {why}", file=sys.stderr)
    print("   (.claude/hooks/git-write-guard.sh — 꼭 필요하면 정훈이 직접 실행할 것. "
          + ("공유 체크아웃 규칙: stash·브랜치 전환·전역/디렉터리 add·commit -a 금지, 내 파일만 경로로 지정하거나 "
             "git_sync.py -m … <파일>로 올릴 것)" if shared_rule else "되돌릴 수 없는 명령)"), file=sys.stderr)
    sys.exit(2)


def base(t: str) -> str:
    b = re.split(r"[\\/]", t.strip("'\""))[-1].lower()
    return b[:-4] if b.endswith(".exe") else b


def strip_heredocs(s: str) -> str:
    """heredoc 본문은 데이터다 — 셸(bash/sh …)에 먹일 때만 남기고 지운다(★H5)."""
    out, pending = [], []
    for line in s.split("\n"):
        if pending:
            d, strip_tabs, keep = pending[0]
            cmpl = (line.lstrip("\t") if strip_tabs else line).rstrip("\r")
            if cmpl == d:
                pending.pop(0)
                out.append("")
                continue
            out.append(line if keep else "")
            continue
        out.append(line)
        for m in re.finditer(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][\w.-]*)\2", line):
            seg = re.split(r"[;&|(]", line[:m.start()])[-1].split()
            pending.append((m.group(3), m.group(1) == "-", bool(seg) and base(seg[0]) in SHELLS))
    return "\n".join(out)


def substitutions(s: str) -> list[str]:
    """$( … )·` … ` 치환 안의 명령(작은따옴표 밖) — 실행되는 명령이다(★H11 백틱)."""
    res, i, n, sq, dq = [], 0, len(s), False, False
    while i < n:
        c = s[i]
        if c == "\\" and not sq:
            i += 2
            continue
        if c == "'" and not dq:
            sq = not sq
        elif c == '"' and not sq:
            dq = not dq
        elif not sq and s.startswith("$(", i) and not s.startswith("$((", i):
            depth, j = 1, i + 2
            while j < n and depth:
                depth += {"(": 1, ")": -1}.get(s[j], 0)
                j += 1
            res.append(s[i + 2:j - 1])
            i = j
            continue
        elif not sq and c == "`":
            j = s.find("`", i + 1)
            if j < 0:
                break
            res.append(s[i + 1:j])
            i = j + 1
            continue
        i += 1
    return res


def tokens(s: str):
    lx = shlex.shlex(s, posix=True, punctuation_chars=";&|()\n")
    lx.whitespace = " \t\r"
    lx.whitespace_split = True
    lx.commenters = ""
    return list(lx)


class Ctx:
    cwd = START_CWD          # None = 모름(변수 cd)


def eff_dir(extra: str | None = None):
    d = Ctx.cwd
    if extra:
        if "$" in extra or extra.startswith("~"):
            return None
        e = win_path(extra)
        d = e if os.path.isabs(e) else (os.path.join(d, e) if d else None)
    return d


def is_shared(d) -> bool:
    if not SHARED_ENV:
        return False
    if d is None or not PROJECT:
        return True
    nd = norm(d)
    return nd == PROJECT or nd.startswith(PROJECT + os.sep)


def bad_path(p: str, d) -> bool:
    """파일 하나가 아닌 경로(전체·디렉터리·글롭·매직 pathspec) — ★H3."""
    if p in ALLPATHS or p.startswith(":/") or p.startswith(":(") or any(ch in p for ch in "*?["):
        return True
    if p.endswith("/") or p.endswith("\\"):
        return True
    n = os.path.normpath(p)
    if n in (".", "..") or n.startswith(".." + os.sep) or n.startswith("../"):
        return True
    full = win_path(p) if os.path.isabs(win_path(p)) else (os.path.join(d, p) if d else p)
    return os.path.isdir(full)


def kept_paths() -> dict:
    kf = os.environ.get("GIT_GUARD_KEPT_FILE") or os.path.join(os.environ.get("CLAUDE_PROJECT_DIR") or START_CWD or ".",
                                                                ".git", "git_sync_kept.json")
    try:
        with open(win_path(kf), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def is_kept(p: str, d) -> bool:
    k = kept_paths()
    if not k:
        return False
    root = win_path(os.environ.get("CLAUDE_PROJECT_DIR") or START_CWD or ".")
    full = os.path.join(d or root, win_path(p))
    try:
        rel = os.path.relpath(full, root).replace("\\", "/")
    except ValueError:
        return False
    return rel in k or p.replace("\\", "/") in k


def split_opts(args, with_val=()):
    """(--앞 옵션들, 위치 인자, -- 뒤 경로) — with_val의 옵션은 다음 토큰을 값으로 먹는다."""
    opts, pos, paths, i = [], [], [], 0
    while i < len(args):
        a = args[i]
        if a == "--":
            paths = args[i + 1:]
            break
        if a.startswith("-") and a != "-":
            opts.append(a)
            if a in with_val and i + 1 < len(args):
                i += 1
        else:
            pos.append(a)
        i += 1
    return opts, pos, paths


def short_flags(opts):
    out = set()
    for a in opts:
        if re.fullmatch(r"-[A-Za-z]+", a):
            out.update(a[1:])
    return out


def check_git(argv, dyn: bool):
    i, gdir = 0, None
    while i < len(argv):                      # 전역 옵션 건너뛰기
        a = argv[i]
        if a in GLOBAL_WITH_ARG:
            val = argv[i + 1] if i + 1 < len(argv) else ""
            if a == "-C":
                gdir = val if gdir is None else os.path.join(gdir, val)
            if a in ("-c", "--config-env") and re.match(r"\s*alias\.", val, re.I):
                block("-c alias.* — 별칭으로 가드를 우회하는 형태")
            i += 2
            continue
        if a.startswith("-c") and re.match(r"-calias\.", a, re.I):
            block("-c alias.* — 별칭으로 가드를 우회하는 형태")
        if a.startswith("-"):
            i += 1
            continue
        break
    if i >= len(argv):
        return
    d = eff_dir(gdir)
    shared = is_shared(d)
    sub, args = argv[i].lower(), argv[i + 1:]
    opts, pos, paths = split_opts(args)
    sf = short_flags(opts)
    if any(o == "--autostash" for o in opts) and shared:
        block(f"{sub} --autostash = stash(공유 워킹트리 — 다른 세션의 작업을 섞는다)", True)

    if sub == "push":
        if any(a.startswith("--force") or a in ("--mirror", "--delete", "--prune") for a in opts) or "f" in sf \
                or "d" in sf:
            block("force/삭제 push")
        if any(p.startswith("+") or p.startswith(":") for p in pos[1:]):
            block("+refspec(강제) 또는 :refspec(삭제) push")
    elif sub == "reset":
        if "--hard" in opts or "--merge" in opts:
            block("reset --hard/--merge (워킹트리 소실)")
        if "--keep" in opts and shared:     # ★[2026-11-24 K1 리뷰 H11] 브랜치를 옮기며 워킹트리 파일을 갈아 끼운다
            block("reset --keep (공유 체크아웃의 브랜치·워킹트리를 되돌린다)", True)
    elif sub == "merge":
        if "--abort" in opts:
            block("merge --abort = reset --merge (워킹트리 소실)")
    elif sub == "clean":
        if ("f" in sf or "--force" in opts) and not ("n" in sf or "--dry-run" in opts):
            block("clean -f (미추적 파일 소실)")
    elif sub == "read-tree":
        if "-u" in opts or "u" in sf:
            block("read-tree -u (워킹트리 덮어쓰기)")
    elif sub == "worktree":
        if pos[:1] == ["remove"] and ("--force" in opts or "f" in sf):
            block("worktree remove --force")
    elif sub == "checkout":
        if "--force" in opts or "f" in sf:
            block("checkout -f (워킹트리 변경 폐기)")
        if not shared:
            return
        if any(o in ("-b", "-B", "--orphan", "--detach") for o in opts) or ("b" in sf or "B" in sf):
            block("checkout -b/-B/--orphan/--detach (공유 체크아웃 브랜치 전환 — 작업은 지금 브랜치에서, "
                  "올리기는 git_sync/HEAD:main)", True)
        if dyn:
            block("xargs/find -exec로 경로를 모르는 checkout", True)
        if "--" not in args:
            if "main" in pos:
                block("checkout main (6/25 교정 — 로컬 main 체크아웃 금지)", True)
            if len(pos) == 1 and not os.path.lexists(os.path.join(d, pos[0]) if d else pos[0]) \
                    and pos[0] not in ALLPATHS:
                block(f"checkout {pos[0]} — 브랜치·ref 전환(detach 포함)은 공유 체크아웃에서 금지", True)
            targets = pos[1:] if len(pos) > 1 else pos
        else:
            targets = paths
        if any(bad_path(p, d) for p in targets):
            block("checkout 디렉터리·글롭·전체 경로 — 다른 세션의 미커밋 작업까지 지운다(파일 경로만)", True)
    elif sub == "switch":
        if shared:
            block("switch (공유 체크아웃 브랜치 전환 금지)", True)
    elif sub == "restore":
        opts, pos, paths = split_opts(args, ("-s", "--source"))
        sf = short_flags(opts)
        staged = "--staged" in opts or "S" in sf
        wt = "--worktree" in opts or "W" in sf
        if shared and (wt or not staged):
            if dyn:
                block("xargs/find -exec로 경로를 모르는 restore", True)
            if any(bad_path(p, d) for p in paths + pos):
                block("restore 디렉터리·글롭·전체 경로 — 다른 세션의 미커밋 작업까지 지운다(파일 경로만)", True)
    elif sub == "rm":
        cached = "--cached" in opts
        force = "--force" in opts or "f" in sf
        targets = paths + pos
        badt = any(bad_path(p, d) for p in targets)
        if not cached and force and badt:
            block("rm -f 디렉터리·전체 경로 (수정 중인 파일까지 강제로 지운다)")
        if shared and not cached and (badt or dyn):
            block("rm 디렉터리·글롭·전체 경로 — 공유 체크아웃(파일 경로만)", True)
        # ★[2026-11-24 K1 리뷰 H11] rm --cached . = 공유 인덱스 전체를 비운다 → 다음 커밋이 전 파일 삭제
        if shared and cached and any(p in ALLPATHS or os.path.normpath(p) == "." for p in targets):
            block("rm --cached <전체> — 공유 인덱스를 비운다(다음 커밋이 전 파일을 지운다)", True)
    elif sub == "stash":
        what = pos[0] if pos else "push"
        if what not in ("list", "show", "create") and shared:
            block(f"stash {what} (공유 워킹트리 — 다른 세션의 작업을 섞거나 지운다)", True)
    elif sub == "add":
        if not shared:
            return
        broad = any(o in ("-A", "--all", "-u", "--update", "--no-ignore-removal") for o in opts) or ("A" in sf or "u" in sf)
        targets = paths + pos
        if (broad and not targets) or dyn:
            block("전역 스테이징(add -A/-u) — 내 파일 경로만 지정할 것", True)
        if any(bad_path(p, d) for p in targets):
            block("add 디렉터리·글롭·전체 경로(. docs/ data/app/) — 다른 세션의 미완 파일까지 담긴다. 내 파일만 경로로", True)
        kp = [p for p in targets if is_kept(p, d)]
        if kp:
            block(f"옛 판 위 수정(.git/git_sync_kept.json) 파일 add: {', '.join(kp[:4])} — 그대로 커밋하면 업스트림이 되돌아간다. "
                  "git_sync.py -m … <파일>로 올리거나(자동 병합·충돌 시 중단), 손으로 합친 뒤 git_sync.py --resolved <파일>", True)
    elif sub == "commit":
        if not shared:
            return
        vals = {"-m", "-F", "-C", "-c", "-t", "--message", "--file", "--reuse-message", "--reedit-message",
                "--template", "--author", "--date", "--fixup", "--squash", "--trailer", "--cleanup"}
        allf, k, targets = False, 0, []
        while k < len(args):
            a = args[k]
            if a == "--":
                targets += args[k + 1:]
                break
            if a == "--all":
                allf = True
            elif a in vals:
                k += 1
            elif re.fullmatch(r"-[A-Za-z].*", a) and not a.startswith("--"):
                for j, ch in enumerate(a[1:]):
                    if ch == "a":
                        allf = True
                    if ch in "mFCct":
                        if j == len(a) - 2:
                            k += 1             # 값이 다음 토큰
                        break
            elif not a.startswith("-"):
                targets.append(a)
            k += 1
        if allf:
            block("commit -a/--all — 다른 세션이 고치던 추적 파일까지 커밋된다(내 파일만 add 후 commit)", True)
        if any(bad_path(p, d) for p in targets):
            block("commit <디렉터리·전체 경로> — 다른 세션의 미완 파일까지 담긴다", True)
        kp = [p for p in targets if is_kept(p, d)]
        if kp:
            block(f"옛 판 위 수정(git_sync_kept) 파일 commit: {', '.join(kp[:4])} — git_sync.py로 올리거나 --resolved", True)
    elif sub == "branch":
        if any(o in ("-D", "-d", "--delete", "-f", "--force", "-M", "-C") for o in opts) or (sf & set("dDfMC")):
            block("branch 삭제·강제 이동/이름변경")
        if shared and (any(o in ("-m", "--move") for o in opts) or "m" in sf):
            block("branch -m (공유 체크아웃의 브랜치 이름을 바꾼다 — 다른 세션의 HEAD가 따라간다)", True)
    elif sub == "sparse-checkout":            # ★[2026-11-24 K1 리뷰 H11] set/add/init = 워킹트리 파일을 걷어낸다
        if shared and (pos[:1] or ["?"])[0] != "list":
            block("sparse-checkout (공유 워킹트리 파일을 걷어낸다)", True)
    elif sub == "config":                     # ★[2026-11-24 K1 리뷰 H11] 별칭·훅 경로를 심어 두고 나중에 우회
        reading = any(o in ("--get", "--get-all", "--get-regexp", "-l", "--list", "--show-origin", "--unset",
                            "--unset-all") for o in opts) or (pos[:1] in (["get"], ["list"]))
        if not reading and any(re.match(r"(?i)alias\.|core\.hookspath$", p) for p in pos):
            block("config alias.*/core.hooksPath 설정 — 별칭·훅 경로로 가드를 우회하는 형태")
    elif sub == "tag":
        if "-d" in opts or "--delete" in opts or "d" in sf:
            block("tag -d (ref 삭제)")
    elif sub == "update-ref":
        if "-d" in opts or "--delete" in opts:
            block("update-ref -d (ref 삭제)")
        if shared and pos and (pos[0].startswith("refs/heads/") or pos[0] == "HEAD"):
            block("update-ref refs/heads/* (공유 체크아웃의 브랜치를 직접 옮긴다)", True)
    elif sub == "symbolic-ref":
        if shared and len(pos) >= 2 and pos[0] == "HEAD":
            block("symbolic-ref HEAD <ref> (공유 체크아웃 브랜치 전환)", True)
    elif sub in ("filter-branch", "filter-repo"):
        block("히스토리 재작성")
    elif sub == "reflog" and pos and pos[0] in ("delete", "expire"):
        block("reflog 삭제·만료")
    elif sub == "gc" and any(o.startswith("--prune") for o in opts):
        block("gc --prune")
    elif sub == "prune":
        block("prune")


KEYWORDS = {"!", "{", "}", "then", "do", "else", "elif", "if", "while", "until", "exec"}


def command_at(seg):
    """구간의 명령어 자리(VAR=·env·command·time·nohup·nice·timeout·sudo·xargs 건너뜀) → (index, xargs여부)."""
    i, dyn = 0, False
    while i < len(seg):
        t, b = seg[i], base(seg[i])
        if t in KEYWORDS or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", t, re.S):
            i += 1
        elif b == "env":
            i += 1
            while i < len(seg) and (seg[i].startswith("-") or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", seg[i], re.S)):
                i += 2 if seg[i] in ("-u", "-C", "-S") else 1
        elif b in ("command", "builtin", "nohup", "winpty", "chronic", "time", "stdbuf", "ionice"):
            i += 1
            while i < len(seg) and seg[i].startswith("-"):
                i += 1
        elif b in ("sudo", "nice"):
            i += 1
            while i < len(seg) and seg[i].startswith("-"):
                i += 2 if seg[i] in ("-u", "-g", "-n") else 1
        elif b == "timeout":
            i += 1
            while i < len(seg) and seg[i].startswith("-"):
                i += 2 if seg[i] in ("-s", "-k") else 1
            i += 1                                 # 시간
        elif b == "xargs":
            dyn, i = True, i + 1
            while i < len(seg) and seg[i].startswith("-"):
                i += 2 if seg[i] in ("-I", "-n", "-P", "-L", "-d", "-a", "-E", "-s") else 1
        else:
            return i, dyn
    return None, dyn


def handle(argv, depth, dyn=False):
    if not argv:
        return
    i, dyn2 = command_at(argv)
    if i is None:
        return
    dyn = dyn or dyn2
    argv = argv[i:]
    b = base(argv[0])
    if b == "cd":
        tgt = argv[1] if len(argv) > 1 else os.path.expanduser("~")
        if "$" in tgt or "`" in tgt:
            Ctx.cwd = None
        else:
            tgt = win_path(os.path.expanduser(tgt))
            Ctx.cwd = tgt if os.path.isabs(tgt) else (os.path.join(Ctx.cwd, tgt) if Ctx.cwd else None)
    elif b == "git":
        check_git(argv[1:], dyn)
    elif b == "find":
        for j, t in enumerate(argv):
            if t in ("-exec", "-execdir", "-ok", "-okdir"):
                handle([x for x in argv[j + 1:] if x not in ("{}", ";", "+")], depth, True)
    elif b in SHELLS:
        for k in range(1, len(argv)):
            if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", argv[k]) and k + 1 < len(argv):
                scan(argv[k + 1], depth + 1)
                break
    elif b == "eval":
        scan(" ".join(argv[1:]), depth + 1)
    elif b in ("powershell", "pwsh"):
        for k in range(1, len(argv)):
            if argv[k].lower() in ("-command", "-c"):
                scan(" ".join(argv[k + 1:]), depth + 1)
                break
    elif b == "cmd":
        for k in range(1, len(argv)):
            if argv[k].lower() in ("/c", "/k"):
                scan(" ".join(argv[k + 1:]), depth + 1)
                break


def scan(s: str, depth: int = 0):
    if depth > 3:
        return
    s = strip_heredocs(s)
    for inner in substitutions(s):
        scan(inner, depth + 1)
    try:
        toks = tokens(s)
    except ValueError:                        # 따옴표 불균형 — 공백·줄바꿈으로라도 본다
        toks = re.split(r"[ \t\r]+|(\n|;|&&|\|\||\|)", s)
        toks = [t for t in toks if t]
    seg = []
    for t in toks + [";"]:
        if t and set(t) <= SEP:
            handle(seg, depth)
            seg = []
        else:
            seg.append(t)


try:
    scan(cmd)
except SystemExit:
    raise
except Exception as e:                        # 파서 결함 — 아주 거친 형태만 막고 나머지는 연다(조용히 무력화되지 않게 알린다)
    if re.search(r"git\S*\s+(-\S+\s+)*(push\b.*(--force|\s-f\b|\s\+)|reset\s+--hard|clean\s+-\w*f|stash\b)", cmd, re.I):
        block(f"가드 파서 오류({type(e).__name__}) — 파괴적 형태로 보여 막는다")
    print(f"⚠️ git-write-guard 파서 오류(통과시킴): {type(e).__name__}: {e}", file=sys.stderr)
sys.exit(0)
PY
rc=$?
[ "$rc" -eq 2 ] && exit 2
exit 0
