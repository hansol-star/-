#!/usr/bin/env python3
"""git_sync.py — 공유 워킹트리에서 **내 파일만** origin/main 위 커밋으로 올리고, 로컬 main은 안전하게 따라가게 한다.

★[2026-10-16 신설] `close_reconcile`가 10/15~10/16 마감 대사 커밋 4개를 **로컬에만** 쌓았다.
  설계는 *"origin/main이 앞서 있으면 푸시 보류(다음 세션이 합친다)"*였는데, 클라우드 keyless 시세 갱신이
  **하루 두 번** origin/main에 커밋한다 → 마감 대사(16:10·20:10)가 돌 때마다 origin이 이미 앞서 있다
  → 푸시는 사실상 영영 안 되고, 로컬 main은 갈라진 채로 남는다(R2 런처의 ff가 `exit 128`로 매일 실패).
  그 사이 클라우드(C2·C3)와 폰 앱은 10/15 코스피 -7.57%·외인 -3.7조 대사값을 못 봤다.
  ⇒ 로컬에 먼저 커밋하지 않는다. **origin/main 트리 + 내 파일**로 임시 인덱스를 만들어 커밋 하나를
  origin/main 위에 바로 올리고(push 경합이면 다시 받아 재구성), 로컬 main은 **조상일 때만** 그 커밋으로
  옮긴다. 다른 세션이 고치던 파일(워킹트리 dirty)은 절대 덮지 않는다.

규약(공유 워킹트리 — memory `shared-worktree-concurrent-sessions`): stash·브랜치 전환·`git add -A`(전역) 금지.
여기서 쓰는 `add -A -- <paths>`는 **경로 한정**이고 임시 인덱스에만 쓴다(본 인덱스 무관).

사용:
  python3 git_sync.py -m "메시지" -- path1 path2 ...     # 올리기 + 로컬 ff
  python3 git_sync.py --ff-only                          # 올리지 않고 로컬 main만 안전하게 따라가기
  python3 git_sync.py --selftest                         # 임시 저장소 4개 시나리오(오프라인)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, *([os.pardir] * 4)))


def _git(root: str, *a: str, env: dict | None = None, inp: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", root, *a], capture_output=True, text=True, timeout=180,
                          env=env, input=inp, encoding="utf-8", errors="replace")


def _rev(root: str, spec: str) -> str | None:
    r = _git(root, "rev-parse", "-q", "--verify", spec)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def _gitdir(root: str) -> str:
    g = _git(root, "rev-parse", "--absolute-git-dir").stdout.strip()
    return g or os.path.join(root, ".git")


def fast_forward_local(root: str, target: str, branch: str = "main") -> dict:
    """로컬 `branch`를 target으로 옮긴다 — **HEAD가 target의 조상일 때만**, dirty 파일은 그대로 둔다.

    git merge --ff-only는 바뀌는 경로에 dirty 파일이 하나라도 있으면 통째로 거부한다(공유 워킹트리에선 거의 항상).
    여기선 경로마다 판정한다: 깨끗하면 target 내용으로, 이미 target과 같으면 그대로, 다른 세션이 고치던 중이면
    **워킹트리를 건드리지 않고** 인덱스만 target으로 맞춘다(→ status에 그 세션의 수정으로 남는다).
    """
    cur_branch = _git(root, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip()
    if cur_branch != branch:
        return {"local": f"skipped(현재 브랜치 {cur_branch or 'detached'} ≠ {branch})", "kept_dirty": []}
    head = _rev(root, "HEAD")
    if head == target:
        return {"local": "already", "kept_dirty": []}
    if not head:
        return {"local": "skipped(HEAD 없음)", "kept_dirty": []}
    if _git(root, "merge-base", "--is-ancestor", head, target).returncode != 0:
        # 갈라졌어도 **로컬 전용 커밋이 바꾼 경로가 target에 같은 내용으로 이미 다 있으면** 옮겨도 잃는 게 없다
        # (= 같은 변경이 다른 커밋으로 올라갔다 · 10/16 마감 대사 4커밋을 한 커밋으로 올린 경우).
        mb = _git(root, "merge-base", head, target).stdout.strip()
        mine = [n for n in _git(root, "diff", "--name-only", "--no-renames", "-z", mb, head).stdout.split("\0") if n] \
            if mb else []
        lost = [p for p in mine if _rev(root, f"{head}:{p}") != _rev(root, f"{target}:{p}")]
        if not mb or lost:
            return {"local": f"skipped(갈라짐 — 로컬에만 있는 변경 {len(lost) or '?'}건)", "kept_dirty": []}
    names = _git(root, "diff", "--name-only", "--no-renames", "-z", head, target).stdout.split("\0")
    names = [n for n in names if n]
    kept, to_checkout, to_remove = [], [], []
    for p in names:
        old = _rev(root, f"{head}:{p}")
        new = _rev(root, f"{target}:{p}")
        wt = os.path.join(root, p)
        cur = _git(root, "hash-object", "--", p).stdout.strip() if os.path.isfile(wt) else None
        if cur == new:
            continue                       # 이미 같다 — 인덱스만 맞추면 된다
        if cur == old:                     # 깨끗(HEAD 그대로 · 둘 다 없음 포함) → target으로
            (to_checkout if new else to_remove).append(p)
        else:
            kept.append(p)                 # 다른 세션이 고치던 중 — 덮지 않는다
    if to_checkout:
        r = _git(root, "checkout", target, "--pathspec-from-file=-", "--pathspec-file-nul",
                 inp="\0".join(to_checkout))
        if r.returncode != 0:
            return {"local": f"skipped(checkout 실패: {r.stderr.strip()[:120]})", "kept_dirty": kept}
    for p in to_remove:
        try:
            os.remove(os.path.join(root, p))
        except OSError:
            pass
    r = _git(root, "update-ref", "-m", "git_sync: fast-forward", f"refs/heads/{branch}", target, head)
    if r.returncode != 0:                  # 그 사이 다른 세션이 HEAD를 옮겼다 — 아무것도 하지 않은 것으로
        return {"local": f"skipped(update-ref 경합: {r.stderr.strip()[:120]})", "kept_dirty": kept}
    if names:                              # 바뀐 경로만 인덱스를 target으로(다른 세션의 staged 항목은 유지)
        _git(root, "reset", "-q", target, "--pathspec-from-file=-", "--pathspec-file-nul", inp="\0".join(names))
    _git(root, "update-index", "-q", "--refresh")
    return {"local": "ff", "kept_dirty": kept}


def publish(root: str, paths: list[str], msg: str, remote: str = "origin", branch: str = "main",
            retries: int = 3, ff_local: bool = True) -> dict:
    """paths의 **워킹트리 내용 그대로**를 remote/branch 위 커밋 하나로 올린다.

    반환: {"status": pushed|nochange|push_failed|fetch_failed, "commit", "base", "local", "kept_dirty", "error"}
    """
    paths = [p.replace("\\", "/") for p in paths if p]
    out: dict = {"status": "push_failed", "commit": None, "base": None, "local": "skipped", "kept_dirty": [],
                 "error": ""}
    idx = os.path.join(_gitdir(root), f"git_sync_index_{os.getpid()}")
    env = {**os.environ, "GIT_INDEX_FILE": idx}
    try:
        for _ in range(max(1, retries)):
            f = _git(root, "fetch", "-q", remote, branch)
            base = _rev(root, f"refs/remotes/{remote}/{branch}")
            if f.returncode != 0 or not base:
                out.update(status="fetch_failed", error=(f.stderr or "").strip()[:200])
                return out
            out["base"] = base
            for step in (("read-tree", base), ("add", "-A", "--", *paths)):
                r = _git(root, *step, env=env)
                if r.returncode != 0:
                    out.update(status="push_failed", error=f"{step[0]}: {r.stderr.strip()[:200]}")
                    return out
            if _git(root, "diff", "--cached", "--quiet", base, env=env).returncode == 0:
                out.update(status="nochange", commit=base)
                break
            tree = _git(root, "write-tree", env=env).stdout.strip()
            new = _git(root, "commit-tree", tree, "-p", base, "-m", msg).stdout.strip()
            if not tree or not new:
                out.update(status="push_failed", error="write-tree/commit-tree 실패")
                return out
            p = _git(root, "push", "-q", remote, f"{new}:refs/heads/{branch}")
            if p.returncode == 0:
                _git(root, "update-ref", f"refs/remotes/{remote}/{branch}", new)
                out.update(status="pushed", commit=new, error="")
                break
            out["error"] = (p.stderr or "").strip()[:200]   # 그 사이 누가 올렸다 → 다시 받아 재구성
    finally:
        try:
            os.remove(idx)
        except OSError:
            pass
    if ff_local and out["status"] in ("pushed", "nochange") and out["commit"]:
        out.update(fast_forward_local(root, out["commit"], branch))
    return out


def describe(o: dict) -> str:
    s = {"pushed": "푸시 완료", "nochange": "변경 없음", "push_failed": "푸시 실패",
         "fetch_failed": "fetch 실패"}.get(o.get("status"), o.get("status"))
    tail = f" · 로컬 main {o.get('local')}"
    if o.get("kept_dirty"):
        tail += f"(다른 세션 수정 보존 {len(o['kept_dirty'])}건)"
    err = f" — {o['error']}" if o.get("error") and o.get("status") not in ("pushed", "nochange") else ""
    return s + (f" {o['commit'][:8]}" if o.get("status") == "pushed" else "") + tail + err


# ── 자가검증(오프라인 · 임시 저장소) ─────────────────────────────────────────────
def selftest() -> int:
    tmp = tempfile.mkdtemp(prefix="git_sync_")
    fails: list[str] = []

    def sh(cwd, *a):
        r = subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            raise RuntimeError(f"git {' '.join(a)}: {r.stderr}")
        return r.stdout

    def wr(path, s):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(s)

    def rd(path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def chk(cond, what):
        print(("  ✅ " if cond else "  ❌ ") + what)
        if not cond:
            fails.append(what)

    try:
        bare = os.path.join(tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
        local, cloud = os.path.join(tmp, "local"), os.path.join(tmp, "cloud")
        for d in (local, cloud):
            subprocess.run(["git", "clone", "-q", bare, d], check=True, capture_output=True)
            for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
                sh(d, "config", k, v)
        for n in ("A.txt", "B.txt", "C.txt"):
            wr(os.path.join(local, n), f"{n} v0\n")
        sh(local, "checkout", "-q", "-b", "main")
        sh(local, "add", "A.txt", "B.txt", "C.txt")
        sh(local, "commit", "-q", "-m", "init")
        sh(local, "push", "-q", "origin", "main")
        sh(cloud, "pull", "-q", "origin", "main")

        # ① origin이 앞서 있고(클라우드가 A 수정) · 로컬엔 다른 세션의 dirty B · 내 파일 C
        wr(os.path.join(cloud, "A.txt"), "A.txt cloud\n")
        sh(cloud, "commit", "-q", "-am", "cloud A")
        sh(cloud, "push", "-q", "origin", "main")
        wr(os.path.join(local, "B.txt"), "B.txt someone-else WIP\n")
        wr(os.path.join(local, "C.txt"), "C.txt mine\n")
        o = publish(local, ["C.txt"], "mine C")
        print("  ①", describe(o))
        remote_head = sh(bare, "rev-parse", "main").strip()
        chk(o["status"] == "pushed" and o["commit"] == remote_head, "① origin이 앞서도 푸시된다(보류 아님)")
        chk(sh(bare, "show", "main:A.txt") == "A.txt cloud\n", "① 클라우드 커밋을 되돌리지 않는다")
        chk(sh(bare, "show", "main:C.txt") == "C.txt mine\n", "① 내 파일이 올라갔다")
        chk(sh(bare, "show", "main:B.txt") == "B.txt v0\n", "① 다른 세션의 미완 파일은 안 올라갔다")
        chk(sh(local, "rev-parse", "HEAD").strip() == remote_head and o["local"] == "ff", "① 로컬 main이 따라갔다")
        chk(rd(os.path.join(local, "A.txt")) == "A.txt cloud\n", "① 깨끗한 파일은 새 내용으로")
        chk(rd(os.path.join(local, "B.txt")) == "B.txt someone-else WIP\n", "① dirty 파일은 보존")
        st = sh(local, "status", "--porcelain").splitlines()
        chk(st == [" M B.txt"], f"① status = 다른 세션 수정 1건만 ({st})")

        # ② 변경 없음
        o = publish(local, ["C.txt"], "noop")
        chk(o["status"] == "nochange", "② 변경 없으면 커밋 안 만든다")

        # ③ 업스트림이 바꾼 파일을 로컬 다른 세션이 고치던 중 → 덮지 않는다
        sh(cloud, "pull", "-q", "origin", "main")
        wr(os.path.join(cloud, "B.txt"), "B.txt cloud2\n")
        sh(cloud, "commit", "-q", "-am", "cloud B")
        sh(cloud, "push", "-q", "origin", "main")
        wr(os.path.join(local, "C.txt"), "C.txt mine2\n")
        o = publish(local, ["C.txt"], "mine C2")
        chk(o["status"] == "pushed" and "B.txt" in o["kept_dirty"], "③ 겹치는 dirty 파일은 kept_dirty로 보고")
        chk(rd(os.path.join(local, "B.txt")) == "B.txt someone-else WIP\n", "③ 그 파일 워킹트리는 그대로")
        chk(sh(local, "show", "HEAD:B.txt") == "B.txt cloud2\n", "③ HEAD는 업스트림 내용")

        # ④ 로컬에 안 올라간 커밋이 있으면(갈라짐) — 푸시는 하되 로컬은 건드리지 않는다
        wr(os.path.join(local, "D.txt"), "D local-only\n")
        sh(local, "add", "D.txt")
        sh(local, "commit", "-q", "-m", "local only D")
        before = sh(local, "rev-parse", "HEAD").strip()
        wr(os.path.join(local, "C.txt"), "C.txt mine3\n")
        o = publish(local, ["C.txt"], "mine C3")
        chk(o["status"] == "pushed" and o["local"].startswith("skipped(갈라짐"), "④ 갈라짐이면 로컬 ref 불변")
        chk(sh(local, "rev-parse", "HEAD").strip() == before, "④ HEAD 그대로")
        chk(rd(os.path.join(local, "C.txt")) == "C.txt mine3\n", "④ 내 파일 내용 그대로")

        # ⑤ 舊 방식으로 로컬에만 쌓인 커밋(D·E)을 같은 내용으로 올리면 → 잃는 게 없으니 로컬도 옮긴다
        wr(os.path.join(local, "E.txt"), "E local-only\n")
        sh(local, "add", "E.txt")
        sh(local, "commit", "-q", "-m", "local only E")
        o = publish(local, ["D.txt", "E.txt"], "carry D E")
        remote_head = sh(bare, "rev-parse", "main").strip()
        chk(o["status"] == "pushed" and o["local"] == "ff", f"⑤ 로컬 전용 변경이 다 올라갔으면 로컬 ff ({o['local']})")
        chk(sh(local, "rev-parse", "HEAD").strip() == remote_head, "⑤ HEAD = origin")
        st = sorted(sh(local, "status", "--porcelain").splitlines())
        chk(st == [" M B.txt"], f"⑤ status = 다른 세션 수정만 ({st})")
    except Exception as e:  # noqa: BLE001 — 자가검증은 어떤 실패든 FAIL로 보고
        fails.append(f"예외: {e}")
        print("  ❌ 예외:", e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"git_sync selftest: {'PASS' if not fails else 'FAIL'} ({len(fails)} 실패)")
    return 0 if not fails else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="내 파일만 origin/main 위 커밋으로 올리고 로컬 main을 안전하게 따라가게 한다")
    ap.add_argument("-m", "--message", help="커밋 메시지")
    ap.add_argument("--ff-only", action="store_true", help="올리지 않고 로컬 main만 origin/main으로 안전하게 이동")
    ap.add_argument("--no-ff-local", action="store_true", help="푸시만 하고 로컬 main은 건드리지 않는다")
    ap.add_argument("--selftest", action="store_true", help="임시 저장소 4개 시나리오 자가검증(오프라인)")
    ap.add_argument("paths", nargs="*", help="올릴 경로(저장소 루트 기준)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.ff_only:
        _git(ROOT, "fetch", "-q", "origin", "main")
        t = _rev(ROOT, "refs/remotes/origin/main")
        o = fast_forward_local(ROOT, t) if t else {"local": "fetch 실패", "kept_dirty": []}
        print("로컬 main", o["local"], (f"· 보존 {o['kept_dirty']}" if o["kept_dirty"] else ""))
        return 0 if o["local"] in ("ff", "already") else 1
    if not a.message or not a.paths:
        ap.error("-m 메시지와 경로가 필요하다")
    o = publish(ROOT, a.paths, a.message, ff_local=not a.no_ff_local)
    print(describe(o))
    return 0 if o["status"] in ("pushed", "nochange") else 1


if __name__ == "__main__":
    sys.exit(main())
