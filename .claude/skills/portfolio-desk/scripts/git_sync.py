#!/usr/bin/env python3
"""git_sync.py — 공유 워킹트리에서 **내 파일만** origin/main 위 커밋으로 올리고, 로컬 체크아웃은 안전하게 따라가게 한다.

★[2026-10-16 신설] `close_reconcile`가 10/15~10/16 마감 대사 커밋 4개를 **로컬에만** 쌓았다.
  설계는 *"origin/main이 앞서 있으면 푸시 보류(다음 세션이 합친다)"*였는데, 클라우드 keyless 시세 갱신이
  **하루 두 번** origin/main에 커밋한다 → 마감 대사(16:10·20:10)가 돌 때마다 origin이 이미 앞서 있다
  → 푸시는 사실상 영영 안 되고, 로컬 main은 갈라진 채로 남는다(R2 런처의 ff가 `exit 128`로 매일 실패).
  그 사이 클라우드(C2·C3)와 폰 앱은 10/15 코스피 -7.57%·외인 -3.7조 대사값을 못 봤다.
  ⇒ 로컬에 먼저 커밋하지 않는다. **origin/main 트리 + 내 파일**로 임시 인덱스를 만들어 커밋 하나를
  origin/main 위에 바로 올리고(push 경합이면 다시 받아 재구성), 로컬은 **조상일 때만** 그 커밋으로
  옮긴다. 다른 세션이 고치던 파일(워킹트리 dirty)은 절대 덮지 않는다.

★[2026-11-22 개정 — K1 체크아웃 드리프트 · 11/21 R3 항목 소실]
  ① 舊 `fast_forward_local`은 체크아웃이 **`main`일 때만** 옮겼다. 공유 체크아웃은 11/5부터
     `claude/report-1105-sync`에 있었고, 그래서 클라우드(C2·C3·R3)·봇 커밋이 **17일간 로컬로 안 내려왔다**
     (15커밋 뒤 · 로컬 세션은 v141이 origin에 있는데 v140을 최신으로 읽었다). 런처 ff도 `main`일 때만 돌았다.
     ⇒ 이제 **지금 체크아웃된 브랜치**를 옮긴다(로컬 전용 변경이 있으면 舊대로 건드리지 않는다).
  ② 舊 `publish`는 경로의 **워킹트리 내용 그대로**를 올렸다. 워킹트리가 옛 판을 바탕으로 고쳐진 것이면
     그 사이 남이 넣은 변경이 **조용히 되돌아간다** — 11/21 09:34 클라우드 R3가 tasks.json에 넣은
     pre_report 2건을 14:30 로컬 커밋(502640af)이 지웠다(아무 경고 없이).
     ⇒ 기반 판(= merge-base(HEAD, origin) · 아래 ④의 보존 기록이 있으면 그 판)과 origin 판이 다른 파일은
     **3-way 병합해서** 올린다. 충돌·삭제 충돌·바이너리면 **아무것도 올리지 않고** `stale_conflict`로 멈춘다.
  ③ ff 중 dirty 파일도 업스트림 변경과 3-way 텍스트 병합이 깨끗하면 워킹트리에 반영한다(그 세션의 수정 +
     업스트림 둘 다 남는다). 충돌이면 舊대로 보존(kept_dirty).
  ④ 보존된 dirty 파일은 HEAD가 옮겨 간 뒤에도 **옛 판 위의 수정**이다 — 그대로 커밋하면 ②와 같은 되돌림이
     난다. 그 파일의 진짜 기반 커밋을 `.git/git_sync_kept.json`에 적어 두고, 다음 ff·publish가 그 판을 기반으로
     병합한다(깨끗해지면 기록에서 빠진다). `validate_report.check_checkout_sync`가 남은 기록을 WARN으로 올린다.

★[2026-11-24 K1 리뷰 — 리뷰어 3인 · 결함 30여 건 일괄 수정] 요지(각 줄 = 고친 것 · 자세한 건 해당 함수 주석):
  · ff 순서(DS-1·DS-11·K1-CONC-01·02·H1·PM-1): 舊는 ref를 먼저 옮기고 인덱스 reset을 나중에 했다(반환코드 미확인).
    index.lock이 잡혀 있거나 그 사이 죽으면 인덱스가 **옛 블롭을 staged**로 들고 남아, 다음 평범한
    `git add <다른 파일> && git commit`이 업스트림을 되돌렸다. ⇒ 새 인덱스를 옆에서 다 만들고 → 워킹트리(CAS) →
    index.lock 직접 잡기 → 저널 → ref CAS → 인덱스 원자 교체. 어느 단계든 실패하면 되돌리고 'skipped'.
    죽어도(타임아웃 kill) 다음 실행이 저널로 마무리·취소하고, 보존 기록은 ref보다 **먼저** 쓴다(write-ahead).
  · 보존 기록(DS-7·K1-CONC-03·09): 원자 쓰기(임시+os.replace) · 저장소 잠금 · 손상이면 {}로 보지 않고 ff·publish 중단.
  · 저장소 잠금(K1-CONC-05): git_sync 실행끼리 직렬화(.git/git_sync.lock · 죽은 pid는 자동 해제).
  · fetch(K1-CONC-04·05·06·11·H1·PM-4): 파이프 대신 파일 · 시간 초과면 프로세스 트리째 kill · 저속 제한 ·
    ref 잠금 경합 재시도 · 명시 refspec · 실패 원인 분류(시간 초과/DNS/연결/인증/경합) · 마지막 **성공** 시각 기록.
  · publish(DS-2·DS-3·DS-4·DS-13·DS-14·K1-CONC-07·10): 변경 집합 = 임시 인덱스 vs base(추가·삭제 포함) ·
    삭제 충돌 판정 · 로컬에서 안 고친 파일은 업스트림을 따른다 · 병합본은 워킹트리에 쓰지 않고 임시 인덱스에만
    (재시도마다 원래 워킹트리가 ours — 로컬 반영은 ff가 한다) · 디렉터리 경로 거부 · 원격 추적 ref CAS ·
    경로 목록은 pathspec-from-file.
  · 분류(DS-5·DS-6·DS-8·DS-9·DS-12·K1-CONC-08): 미추적 디렉터리/파일과 겹치는 경로는 덮지 않는다 · 덮기 직전
    재확인(CAS) · 대소문자만 바뀐 이름 · CRLF 워킹트리는 정규화해서 병합 · staged 항목은 인덱스 쪽도 병합해 지킨다.
  · 해결 경로(DS-10): `--resolved <path>` — 손으로 합친 보존 파일의 기록을 지운다.

규약(공유 워킹트리 — memory `shared-worktree-concurrent-sessions`): stash·브랜치 전환·`git add -A`(전역) 금지.
여기서 쓰는 `add -A -- <paths>`는 **경로 한정**이고 임시 인덱스에만 쓴다(본 인덱스 무관).

사용:
  python3 git_sync.py -m "메시지" -- path1 path2 ...          # 올리기 + 로컬 ff (파일 경로만 — 디렉터리 거부)
  python3 git_sync.py --ff-only [--no-fetch] [--json]         # 올리지 않고 로컬 체크아웃만 안전하게 따라가기
  python3 git_sync.py --status [--json]                       # 읽기 전용: 뒤처짐·앞섬·보존 파일·최신 보고서 대조
  python3 git_sync.py --resolved path ...                     # 손으로 합친 보존 파일 → 기록 해제(다음 publish가 그대로 올린다)
  python3 git_sync.py --selftest                              # 임시 저장소 시나리오(오프라인)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, *([os.pardir] * 4)))
REPORT_RE = re.compile(r"^docs/reports/report_v(\d+)_[\d-]+\.md$")
BOT_AUTHORS = ("portfolio-desk-bot",)          # 시세 자동 갱신(keyless) — 뒤처져도 판단에 영향 적은 커밋

LOCK_WAIT_SYNC = 60.0        # sync_checkout·fast_forward_local이 다른 git_sync 실행을 기다리는 시간(초)
LOCK_WAIT_PUBLISH = 180.0    # publish(fetch·push 포함)
LOCK_STALE_S = 900.0         # 이보다 오래된 저장소 잠금은 죽은 것으로 본다(pid 확인과 별개)
INDEX_LOCK_WAIT = 5.0        # 다른 git이 잡은 .git/index.lock을 기다리는 시간
_FAULT: str | None = None    # 자가검증 전용 — 이 이름의 단계에서 예외/종료를 낸다


class _Fault(Exception):
    pass


def _fault(step: str) -> None:
    """자가검증용 고장 주입점. `_FAULT == step`이면 예외(또는 GIT_SYNC_FAULT_EXIT=1이면 즉시 프로세스 종료 = kill 모사)."""
    if _FAULT and _FAULT == step:
        if os.environ.get("GIT_SYNC_FAULT_EXIT") == "1":
            os._exit(9)
        raise _Fault(step)


def _git(root: str, *a: str, env: dict | None = None, inp: str | None = None,
         timeout: float = 180) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", root, *a], capture_output=True, text=True, timeout=timeout,
                          env=env, input=inp, encoding="utf-8", errors="replace")


def _git_bytes(root: str, *a: str, env: dict | None = None, inp: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", root, *a], capture_output=True, timeout=180, env=env, input=inp)


def _rev(root: str, spec: str) -> str | None:
    r = _git(root, "rev-parse", "-q", "--verify", spec)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def _gitdir(root: str) -> str:
    g = _git(root, "rev-parse", "--absolute-git-dir").stdout.strip()
    return g or os.path.join(root, ".git")


def _is_ancestor(root: str, a: str, b: str) -> bool:
    return _git(root, "merge-base", "--is-ancestor", a, b).returncode == 0


def _atomic_write(path: str, data: bytes) -> None:
    """임시 파일 + os.replace — 읽는 쪽이 반쯤 쓴 파일을 보지 않는다(★11/24 DS-7·K1-CONC-03)."""
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".gs_tmp_", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        for i in range(20):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:      # 윈도우: 읽는 쪽이 공유 삭제 없이 열고 있으면 잠깐 실패한다
                time.sleep(0.05 * (i + 1))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ── 저장소 잠금 · ★[2026-11-24 K1 리뷰 K1-CONC-03·05] ─────────────────────────────────
#   舊엔 git_sync 실행끼리 아무 조율이 없었다 — 부팅 직후 캐치업 런처 2개·R1·SessionStart·close_reconcile이
#   동시에 fetch해서 'cannot lock ref'로 publish 24건 중 23건이 fetch_failed였고, 보존 기록 읽기-수정-쓰기가
#   서로의 기록을 지웠다. ⇒ .git/git_sync.lock(O_EXCL)로 직렬화한다. 같은 프로세스 안에선 재진입 가능.
#   주인이 죽었으면(pid 없음) 또는 LOCK_STALE_S보다 오래됐으면 깨고 들어간다(SessionStart `timeout` kill 대비).
_HELD: dict[tuple[str, int], int] = {}   # (잠금 파일, 스레드) — 같은 스레드 안에서만 재진입


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.OpenProcess.restype = wintypes.HANDLE
            h = k32.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return ctypes.get_last_error() == 5           # 접근 거부 = 살아 있다
            code = wintypes.DWORD()
            ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
            k32.CloseHandle(h)
            return bool(ok) and code.value == 259             # STILL_ACTIVE
        except Exception:  # noqa: BLE001 — 모르면 살아 있다고 본다(나이 기준이 따로 있다)
            return True
    try:
        os.kill(pid, 0)                                       # POSIX 전용(윈도우에선 0이 종료 신호다 — 쓰지 않는다)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


class _RepoLock:
    def __init__(self, root: str, wait: float):
        self.path = os.path.join(_gitdir(root), "git_sync.lock")
        self.wait = max(0.0, wait)
        self.got = False

    def _stale(self) -> bool:
        try:
            st = os.stat(self.path)
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
            age = time.time() - float(d.get("t") or st.st_mtime)
            pid = int(d.get("pid") or 0)
        except FileNotFoundError:
            return False
        except Exception:  # noqa: BLE001 — 내용이 깨졌으면(만들다 죽음) 파일 나이로만 본다
            try:
                return time.time() - os.stat(self.path).st_mtime > 30
            except OSError:
                return False
        return age > LOCK_STALE_S or not _pid_alive(pid)

    def acquire(self) -> bool:
        self.key = (self.path, threading.get_ident())
        if _HELD.get(self.key):
            _HELD[self.key] += 1
            self.got = True
            return True
        deadline = time.time() + self.wait
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump({"pid": os.getpid(), "t": time.time(), "argv": sys.argv[:4]}, f)
                _HELD[self.key] = 1
                self.got = True
                return True
            except FileExistsError:
                if self._stale():
                    try:
                        os.replace(self.path, f"{self.path}.stale{os.getpid()}")
                        os.remove(f"{self.path}.stale{os.getpid()}")
                    except OSError:
                        pass
                    continue
                if time.time() >= deadline:
                    return False
                time.sleep(0.15 + random.random() * 0.2)
            except OSError:
                return False

    def release(self) -> None:
        if not self.got:
            return
        self.got = False
        n = _HELD.get(self.key, 0) - 1
        if n > 0:
            _HELD[self.key] = n
            return
        _HELD.pop(self.key, None)
        try:
            os.remove(self.path)
        except OSError:
            pass


# ── fetch · ★[2026-11-24 K1 리뷰 K1-CONC-04·05·06·11·H1·PM-4] ─────────────────────────
#   舊 `subprocess.run(timeout=)`는 윈도우에서 시간 초과 뒤 git을 죽이고도 communicate()가 **손자
#   git-remote-https가 쥔 파이프**를 기다렸다(3초 제한이 21~75초+ · SessionStart `timeout 25`가 그 한가운데서
#   ff를 죽였다). ⇒ 출력은 파일로, 시간 초과면 프로세스 트리째 kill(taskkill /T) · curl 저속 제한으로 git이 스스로
#   끊게 · 'cannot lock ref'(동시 fetch)는 재시도 · 명시 refspec(단일 브랜치 클론에서도 origin/main이 생긴다) ·
#   실패 원인을 분류해 남기고 마지막 **성공** 시각을 .git/git_sync_last_fetch.json에 적는다(FETCH_HEAD mtime은
#   실패한 fetch도 갱신해서 '0분 전 받음'이라는 거짓 신선도를 만들었다).
def _kill_tree(p: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, timeout=15)
        else:
            import signal
            os.killpg(p.pid, signal.SIGKILL)
    except Exception:  # noqa: BLE001
        pass
    try:
        p.kill()
    except Exception:  # noqa: BLE001
        pass
    try:
        p.wait(timeout=5)
    except Exception:  # noqa: BLE001
        pass


def _run_killable(argv: list[str], timeout: float, env: dict | None = None) -> tuple[int | None, str]:
    """파이프 없이 실행 — 시간 초과면 (None, stderr). 손자 프로세스가 남아도 기다리지 않는다."""
    with tempfile.TemporaryFile() as ef:
        kw: dict = {"start_new_session": True} if os.name != "nt" else \
            {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=ef, env=env, **kw)
        try:
            rc: int | None = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(p)
            rc = None
        ef.seek(0)
        err = ef.read().decode("utf-8", "replace")
    return rc, err


def _classify_fetch_err(err: str) -> str:
    e = err.lower()
    first = next((ln.strip() for ln in err.splitlines() if ln.strip()), "")[:160]
    if "could not resolve host" in e or "name or service not known" in e or "getaddrinfo" in e:
        kind = "DNS 실패(네트워크 미연결?)"
    elif "cannot lock ref" in e or "unable to update local ref" in e:
        kind = "동시 fetch 경합(ref 잠금)"
    elif "authentication failed" in e or "could not read username" in e or "permission denied" in e \
            or " 403" in e or " 401" in e or "access denied" in e:
        kind = "인증 실패"
    elif "operation too slow" in e or "transfer rate" in e or "low speed" in e:
        kind = "전송 정지(저속 제한 초과)"
    elif "failed to connect" in e or "connection refused" in e or "couldn't connect" in e \
            or "timed out" in e or "connection reset" in e or "unable to access" in e:
        kind = "연결 실패"
    else:
        kind = "fetch 오류"
    return f"{kind}: {first}" if first else kind


def _last_fetch_file(root: str) -> str:
    return os.path.join(_gitdir(root), "git_sync_last_fetch.json")


def _record_fetch(root: str, ok: bool, err: str = "") -> None:
    p = _last_fetch_file(root)
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            d = {}
    except Exception:  # noqa: BLE001
        d = {}
    if ok:
        d["ok_t"] = time.time()
    else:
        d.update(fail_t=time.time(), fail_err=err[:200])
    try:
        _atomic_write(p, json.dumps(d, ensure_ascii=False).encode("utf-8"))
    except OSError:
        pass


def last_fetch_ok(root: str) -> float | None:
    """마지막으로 **성공한** fetch(git_sync 경유)의 epoch 초. 기록이 없으면 None."""
    try:
        with open(_last_fetch_file(root), encoding="utf-8") as f:
            d = json.load(f)
        t = d.get("ok_t") if isinstance(d, dict) else None
        return float(t) if t else None
    except Exception:  # noqa: BLE001
        return None


def _fetch(root: str, remote: str = "origin", branch: str = "main", timeout: float = 120) -> tuple[bool, str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never",
           "GIT_HTTP_LOW_SPEED_LIMIT": "1000", "GIT_HTTP_LOW_SPEED_TIME": str(max(5, int(timeout)))}
    refspec = f"+refs/heads/{branch}:refs/remotes/{remote}/{branch}"
    deadline = time.time() + timeout
    err = ""
    for attempt in range(4):
        left = deadline - time.time()
        if left <= 0.5:
            break
        rc, raw = _run_killable(["git", "-C", root, "fetch", "-q", remote, refspec], left, env)
        if rc is None:
            err = f"fetch 시간 초과({timeout:.0f}초 — 네트워크 미응답·부팅 직후 미연결?)"
            _record_fetch(root, False, err)
            return False, err
        if rc == 0:
            _record_fetch(root, True)
            return True, ""
        err = _classify_fetch_err(raw)
        if err.startswith("동시 fetch 경합") and attempt < 3:
            time.sleep(0.3 + random.random() * 0.7)          # 다른 실행이 막 받는 중 — 잠깐 뒤 다시
            continue
        break
    _record_fetch(root, False, err)
    return False, err


# ── 트리·인덱스·워킹트리 조회 ───────────────────────────────────────────────────────
def _tree_entries(root: str, rev: str | None, paths: list[str]) -> dict[str, tuple[str, str]]:
    """rev 트리에서 paths의 (mode, sha) — 없는 경로는 빠진다."""
    out: dict[str, tuple[str, str]] = {}
    if not rev or not paths:
        return out
    for i in range(0, len(paths), 150):
        r = _git_bytes(root, "--literal-pathspecs", "ls-tree", "-r", "-z", "--full-tree", rev, "--", *paths[i:i + 150])
        for rec in r.stdout.split(b"\0"):
            meta, _, path = rec.partition(b"\t")
            parts = meta.split()
            if len(parts) >= 3 and parts[1] in (b"blob", b"commit"):
                out[path.decode("utf-8", "surrogateescape")] = (parts[0].decode(), parts[2].decode())
    return out


def _blobs(root: str, rev: str | None, paths: list[str]) -> dict[str, str]:
    """rev 트리에서 paths의 블롭 sha(없는 경로는 빠진다)."""
    return {p: e[1] for p, e in _tree_entries(root, rev, paths).items()}


def _index_all(root: str, env: dict | None = None) -> dict[str, tuple[str, str, str]]:
    """본(또는 env의) 인덱스 전체 — {path: (mode, sha, stage)} · 병합 중 stage가 여럿이면 마지막 값."""
    r = _git_bytes(root, "ls-files", "-s", "-z", env=env)
    out: dict[str, tuple[str, str, str]] = {}
    for rec in r.stdout.split(b"\0"):
        meta, _, path = rec.partition(b"\t")
        parts = meta.split()
        if len(parts) == 3:
            out[path.decode("utf-8", "surrogateescape")] = (parts[0].decode(), parts[1].decode(), parts[2].decode())
    return out


_NONFILE = object()   # 경로 자리에 파일이 아닌 것(디렉터리·링크)이 있다


def _snap(root: str, p: str):
    """워킹트리 원본 바이트(없으면 None · 파일이 아니면 _NONFILE)."""
    fp = os.path.join(root, p)
    if os.path.islink(fp):
        return _NONFILE
    if os.path.isfile(fp):
        try:
            with open(fp, "rb") as f:
                return f.read()
        except OSError:
            return _NONFILE
    if os.path.lexists(fp):
        return _NONFILE
    return None


def _wt_hashes(root: str, paths: list[str]) -> dict[str, str]:
    """워킹트리 파일의 블롭 sha(필터 적용 = 커밋될 모양) — 없는 파일은 빠진다."""
    exist = [p for p in paths if os.path.isfile(os.path.join(root, p)) and not os.path.islink(os.path.join(root, p))]
    if not exist:
        return {}
    r = _git(root, "hash-object", "--stdin-paths", inp="".join(p + "\n" for p in exist))
    shas = r.stdout.split()
    if r.returncode == 0 and len(shas) == len(exist):
        return dict(zip(exist, shas))
    return {p: _git(root, "hash-object", "--", p).stdout.strip() for p in exist}


def _hash_bytes(root: str, path: str, data: bytes, write: bool = False, filters: bool = True) -> str:
    a = ["hash-object"] + (["-w"] if write else []) + (["--path", path] if filters else ["--no-filters"]) + ["--stdin"]
    r = _git_bytes(root, *a, inp=data)
    if r.returncode != 0:
        raise OSError(f"hash-object 실패: {r.stderr.decode('utf-8', 'replace')[:120]}")
    return r.stdout.decode().strip()


def _cat_blob(root: str, sha: str) -> bytes | None:
    r = _git_bytes(root, "cat-file", "blob", sha)
    return r.stdout if r.returncode == 0 else None


def _smudge(root: str, path: str, sha: str) -> bytes | None:
    """블롭을 **체크아웃될 모양**(eol·필터 적용)으로."""
    r = _git_bytes(root, "cat-file", "--filters", f"--path={path}", sha)
    return r.stdout if r.returncode == 0 else None


def _checkout_bytes(root: str, spec: str | None) -> bytes | None:
    """`<rev>:<path>` 블롭을 체크아웃될 모양 그대로(하위호환)."""
    if not spec:
        return None
    r = _git_bytes(root, "cat-file", "--filters", spec)
    return r.stdout if r.returncode == 0 else None


def _merge3(root: str, base: bytes, ours: bytes, theirs: bytes) -> bytes | None:
    """3-way 텍스트 병합. 깨끗하면 병합본, 충돌·바이너리·오류면 None."""
    if b"\0" in base or b"\0" in ours or b"\0" in theirs:
        return None
    d = tempfile.mkdtemp(prefix="git_sync_m3_")
    try:
        paths = []
        for name, data in (("ours", ours), ("base", base), ("theirs", theirs)):
            p = os.path.join(d, name)
            with open(p, "wb") as f:
                f.write(data)
            paths.append(p)
        r = _git_bytes(root, "merge-file", "-p", "-q", *paths)
        return r.stdout if r.returncode == 0 else None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _merge_norm(root: str, path: str, base_sha: str | None, ours_raw: bytes, theirs_sha: str) -> tuple[bytes, str] | None:
    """★[2026-11-24 K1 리뷰 DS-9] **정규화(인덱스) 모양**에서 병합한다 → (워킹트리에 쓸 바이트, 병합 블롭 sha).

    舊는 워킹트리 원본(CRLF)을 cat-file --filters(LF) 판과 병합해 **모든 줄이 달라** 실제 수정 하나만 있어도 파일 통째
    충돌이 됐다(실제 저장소 = `* text=auto eol=lf` · 워킹트리 CRLF 673개). ours를 clean 필터로 정규화하고, base·theirs는
    날 블롭으로 병합한 뒤, 워킹트리용으로 smudge한다 — ours가 CRLF였으면 CRLF로 되돌려 쓴다."""
    theirs = _cat_blob(root, theirs_sha)
    base = _cat_blob(root, base_sha) if base_sha else b""
    if theirs is None or base is None:
        return None
    ours = _cat_blob(root, _hash_bytes(root, path, ours_raw, write=True))
    if ours is None:
        return None
    m = _merge3(root, base, ours, theirs)
    if m is None:
        return None
    sha = _hash_bytes(root, path, m, write=True, filters=False)
    wt = _smudge(root, path, sha)
    if wt is None:
        return None
    return _match_eol(ours_raw, wt), sha


def _match_eol(ref_raw, data: bytes) -> bytes:
    """참조 워킹트리 파일이 전부 CRLF였으면 CRLF로 맞춘다(다른 세션 편집기의 줄바꿈을 바꾸지 않는다)."""
    if isinstance(ref_raw, bytes) and b"\r\n" in ref_raw and ref_raw.count(b"\n") == ref_raw.count(b"\r\n") \
            and b"\r\n" not in data:
        return data.replace(b"\n", b"\r\n")
    return data


def _index_info(root: str, env: dict, entries: dict[str, tuple[str, str] | None], zero: str) -> None:
    """env 인덱스의 항목을 정한다 — 값 None = 경로 제거."""
    if not entries:
        return
    rec = "".join((f"0 {zero}\t{p}\0" if e is None else f"{e[0]} {e[1]}\t{p}\0") for p, e in entries.items())
    r = _git(root, "update-index", "-z", "--index-info", env=env, inp=rec)
    if r.returncode != 0:
        raise OSError(f"update-index --index-info 실패: {r.stderr.strip()[:160]}")


# ── ④ 보존된 dirty 파일의 진짜 기반 커밋 ──────────────────────────────────────────
class KeptCorrupt(Exception):
    """★[2026-11-24 K1 리뷰 DS-7·K1-CONC-03·09] 보존 기록이 깨졌다 — {}로 보면 그 파일들이 되돌림으로 올라간다."""


def _kept_file(root: str) -> str:
    return os.path.join(_gitdir(root), "git_sync_kept.json")


def _load_kept_strict(root: str) -> dict[str, str]:
    p = _kept_file(root)
    raw = ""
    for i in range(10):
        try:
            with open(p, encoding="utf-8") as f:
                raw = f.read()
            break
        except FileNotFoundError:
            return {}
        except PermissionError as e:              # 윈도우: 교체(os.replace) 순간의 공유 위반 — 잠깐 뒤 다시
            if i == 9:
                raise KeptCorrupt(f"읽기 실패: {e}") from e
            time.sleep(0.02 * (i + 1))
        except OSError as e:
            raise KeptCorrupt(f"읽기 실패: {e}") from e
    try:
        d = json.loads(raw)
    except ValueError as e:
        raise KeptCorrupt(f"JSON 손상: {e}") from e
    if not isinstance(d, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in d.items()):
        raise KeptCorrupt("형식 손상(경로→커밋 객체가 아님)")
    return dict(d)


def load_kept(root: str) -> dict[str, str]:
    """하위호환(읽기 전용 표시용) — 손상이면 {}. 판정에 쓰는 쪽은 _load_kept_strict를 쓴다(status는 kept_corrupt를 낸다)."""
    try:
        return _load_kept_strict(root)
    except KeptCorrupt:
        return {}


def _save_kept(root: str, kept: dict[str, str]) -> bool:
    p = _kept_file(root)
    try:
        if kept:
            _atomic_write(p, json.dumps(dict(sorted(kept.items())), ensure_ascii=False, indent=1).encode("utf-8"))
        elif os.path.exists(p):
            os.remove(p)
        return True
    except OSError:
        return False


def _prune_kept(root: str, kept: dict[str, str], head: str | None) -> dict[str, str]:
    """워킹트리가 HEAD와 같아졌으면(커밋·되돌림 — 둘 다 없음 포함) 기록에서 뺀다.

    ★[2026-11-24 K1 리뷰 DS-3] 舊는 **워킹트리에 없는 파일도** 뺐다 — 로컬 삭제(미커밋) 위로 업스트림이 그 파일을
    고친 경우 기록이 바로 사라졌고, 다음 publish가 삭제를 그대로 올려 업스트림 수정을 지웠다. 이제 '삭제 의도'도 남긴다."""
    if not kept or not head:
        return kept
    paths = list(kept)
    hb, wb = _blobs(root, head, paths), _wt_hashes(root, paths)
    out = {}
    for p, b in kept.items():
        snap_nonfile = _snap(root, p) is _NONFILE
        if not snap_nonfile and wb.get(p) == hb.get(p):
            continue
        out[p] = b
    return out


def resolve_kept(root: str, paths: list[str], lock_wait: float = LOCK_WAIT_SYNC) -> dict:
    """★[2026-11-24 K1 리뷰 DS-10] 손으로 합친 보존 파일의 기록을 지운다 → 다음 publish는 워킹트리를 HEAD 위의 수정으로 본다.

    舊엔 해결 경로가 없었다 — 충돌 줄에서 내 줄을 일부러 남기면 publish가 옛 기반으로 영원히 다시 병합해 stale_conflict만
    냈고, 빠져나갈 길은 kept.json을 지우는 것(문서 없음·DS-7 되돌림 경로)뿐이었다.
    조건: HEAD가 origin/main의 조상(또는 같음)이어야 한다 — 아니면 먼저 --ff-only."""
    paths = [p.replace("\\", "/") for p in paths if p]
    out: dict = {"resolved": [], "not_kept": [], "error": "", "diff": ""}
    lk = _RepoLock(root, lock_wait)
    if not lk.acquire():
        out["error"] = "다른 git_sync 실행 중(잠금 대기 초과)"
        return out
    try:
        try:
            kept = _load_kept_strict(root)
        except KeptCorrupt as e:
            out["error"] = f"보존 기록 손상({e}) — .git/git_sync_kept.json을 직접 확인할 것"
            return out
        head, om = _rev(root, "HEAD"), _rev(root, "refs/remotes/origin/main")
        if not head or (om and not _is_ancestor(root, head, om)):
            out["error"] = "HEAD가 origin/main 뒤가 아니다 — 먼저 `git_sync.py --ff-only`로 맞춘 뒤 다시"
            return out
        for p in paths:
            if p in kept:
                kept.pop(p)
                out["resolved"].append(p)
            else:
                out["not_kept"].append(p)
        if out["resolved"]:
            out["diff"] = _git(root, "--literal-pathspecs", "diff", "--stat", "HEAD", "--", *out["resolved"]).stdout.strip()
            if not _save_kept(root, kept):
                out["error"] = "보존 기록 쓰기 실패"
    finally:
        lk.release()
    return out


# ── 중단된 ff 저널 · ★[2026-11-24 K1 리뷰 K1-CONC-02·H1·PM-1] ─────────────────────────
def _journal_file(root: str) -> str:
    return os.path.join(_gitdir(root), "git_sync_journal.json")


def _sha1_file(p: str) -> str | None:
    try:
        with open(p, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return None


def _recover_journal(root: str) -> str:
    """앞선 ff가 index.lock을 쥔 채 죽었으면 마무리(ref가 이미 옮겨졌으면 인덱스 교체)하거나 정리한다(잠금 보유 중 호출)."""
    jp = _journal_file(root)
    gd0 = _gitdir(root)
    try:                                           # 죽은 실행이 남긴 임시 인덱스 정리
        for n in os.listdir(gd0):
            m = re.match(r"git_sync_(?:ffidx|index)_(\d+)$", n)
            if m and int(m.group(1)) != os.getpid() and not _pid_alive(int(m.group(1))):
                os.remove(os.path.join(gd0, n))
    except OSError:
        pass
    try:
        with open(jp, encoding="utf-8") as f:
            j = json.load(f)
    except FileNotFoundError:
        return ""
    except Exception:  # noqa: BLE001
        j = {}
    gd = _gitdir(root)
    lock, index = os.path.join(gd, "index.lock"), os.path.join(gd, "index")
    note = "중단된 ff 저널 정리"
    if isinstance(j, dict) and os.path.exists(lock) and _sha1_file(lock) == j.get("lock_sha"):
        try:
            if j.get("ref") and _rev(root, j["ref"]) == j.get("target"):
                os.replace(lock, index)
                note = "중단된 ff 마무리(인덱스 교체)"
            else:
                os.remove(lock)
                note = "중단된 ff 취소(index.lock 해제)"
        except OSError as e:
            return f"중단된 ff 복구 실패: {e}"
    for p in (jp, j.get("tmp") if isinstance(j, dict) else None):
        if p:
            try:
                os.remove(p)
            except OSError:
                pass
    return note


def _rmdirs_up(root: str, rel: str) -> None:
    d = os.path.dirname(rel)
    while d:
        try:
            os.rmdir(os.path.join(root, d))
        except OSError:
            return
        d = os.path.dirname(d)


def _do_op(root: str, op: dict) -> None:
    fp = os.path.join(root, op["path"])
    if op["kind"] == "remove":
        os.remove(fp)
        _rmdirs_up(root, op["path"])
        return
    parent = os.path.dirname(fp)
    if parent:
        os.makedirs(parent, exist_ok=True)
    try:
        _atomic_write(fp, op["data"])
    except OSError:
        with open(fp, "wb") as f:                     # 다른 프로그램이 공유 삭제 없이 열고 있으면 제자리 쓰기
            f.write(op["data"])
    if os.name != "nt" and op.get("mode"):
        try:
            os.chmod(fp, 0o755 if op["mode"] == "100755" else 0o644)
        except OSError:
            pass


def _undo_ops(root: str, done: list[dict]) -> None:
    """쓴 내용이 그대로일 때만 원래대로 되돌린다(그 사이 남이 고쳤으면 손대지 않는다)."""
    for op in reversed(done):
        after = op["data"] if op["kind"] == "write" else None
        if _snap(root, op["path"]) != after:
            continue
        try:
            before = op["expect"]
            if before is None:
                os.remove(os.path.join(root, op["path"]))
                _rmdirs_up(root, op["path"])
            elif isinstance(before, bytes):
                _do_op(root, {"kind": "write", "path": op["path"], "data": before})
        except OSError:
            pass


def _take_index_lock(gd: str, src: str, wait: float) -> bool:
    """index.lock을 **완성된 새 인덱스로** 원자적으로 만든다(하드링크 — 있으면 실패). 다른 git이 쥐었으면 기다린다."""
    lock = os.path.join(gd, "index.lock")
    deadline = time.time() + wait
    while True:
        try:
            os.link(src, lock)
            return True
        except FileExistsError:
            if time.time() >= deadline:
                return False
            time.sleep(0.05 + random.random() * 0.1)
        except OSError:                                  # 하드링크 불가 파일시스템 — O_EXCL로 쓴다
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0))
            except FileExistsError:
                if time.time() >= deadline:
                    return False
                time.sleep(0.05 + random.random() * 0.1)
                continue
            except OSError:
                return False
            with open(src, "rb") as f, os.fdopen(fd, "wb") as g:
                g.write(f.read())
            return True


def _read_bytes(p: str) -> bytes | None:
    try:
        with open(p, "rb") as f:
            return f.read()
    except OSError:
        return None


def _ignorecase(root: str) -> bool:
    return _git(root, "config", "--bool", "core.ignorecase").stdout.strip() == "true"


def _disk_name(root: str, rel: str) -> str | None:
    """대소문자 무시 파일시스템에서 실제 디스크 이름(같은 폴더의 항목 중 소문자 일치)."""
    parent = os.path.join(root, os.path.dirname(rel))
    try:
        names = os.listdir(parent)
    except OSError:
        return None
    b = os.path.basename(rel).lower()
    for n in names:
        if n.lower() == b:
            d = os.path.dirname(rel)
            return f"{d}/{n}" if d else n
    return None


def fast_forward_local(root: str, target: str, branch: str = "main", lock_wait: float = LOCK_WAIT_SYNC) -> dict:
    """지금 체크아웃된 브랜치를 target으로 옮긴다 — **로컬 전용 변경이 없을 때만**, dirty 파일은 지킨다.

    git merge --ff-only는 바뀌는 경로에 dirty 파일이 하나라도 있으면 통째로 거부한다(공유 워킹트리에선 거의 항상).
    여기선 경로마다 판정한다: 깨끗하면 target 내용으로, 이미 target과 같으면 그대로, 다른 세션이 고치던 중이면
    3-way 병합이 깨끗할 때만 워킹트리에 반영하고(★11/22), 충돌이면 **워킹트리를 건드리지 않고** 인덱스만
    target으로 맞춘 뒤 그 파일의 진짜 기반을 보존 기록에 남긴다(→ status에 그 세션의 수정으로 남는다).
    `branch`는 하위호환용 인자다 — ★[11/22] 舊엔 이 이름(main)일 때만 옮겼다(K1 드리프트의 원인).
    ★[2026-11-24 K1 리뷰] 전부 옮기거나(ref·인덱스·워킹트리) 아무것도 안 바꾼다 — 순서는 _ff_locked 주석.
    """
    lk = _RepoLock(root, lock_wait)
    if not lk.acquire():
        return {"local": "skipped(다른 git_sync 실행 중 — 잠금 대기 초과)", "kept_dirty": [], "merged_dirty": [],
                "branch": _git(root, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip() or None}
    try:
        return _ff_locked(root, target)
    finally:
        lk.release()


def _ff_locked(root: str, target: str) -> dict:
    """fast_forward_local 본체(저장소 잠금 보유 중).

    ★[2026-11-24 K1 리뷰 DS-1·DS-11·K1-CONC-01·02·H1·PM-1] 舊 순서 = checkout(인덱스+워킹트리) → update-ref →
    병합본 쓰기 → reset(반환코드 미확인) → 보존 기록. 어디서 끊겨도 'ff'를 내거나 **staged 되돌림**을 남겼다.
    새 순서(전부 아니면 전무):
      ① 분류(워킹트리 원본 바이트 스냅숏 · 인덱스 staged 여부 · 미추적 충돌 · 대소문자)
      ② 보존 기록 write-ahead(dirty 경로마다 진짜 기반) — ref보다 먼저 써서 죽어도 기반을 잃지 않는다
      ③ 새 인덱스를 **옆 파일**에 만든다(본 인덱스 사본 + 바뀐 경로만 target/병합본)
      ④ 워킹트리 쓰기·삭제 — 매 경로 직전에 스냅숏과 대조(CAS), 달라졌으면 덮지 않고 보존으로 돌린다
      ⑤ index.lock을 새 인덱스로 직접 잡는다(하드링크) — 본 인덱스가 그 사이 바뀌었으면 ③부터 다시
      ⑥ 저널 → ⑦ update-ref CAS(head→target) → ⑧ index.lock → index 원자 교체
      실패: ⑤⑦⑧이 안 되면 ref를 되돌리고 워킹트리를 되돌리고(내가 쓴 그대로일 때만) 'skipped(...)'.
      kill: ⑥~⑧ 사이에 죽으면 index.lock이 남아 git이 **시끄럽게** 멈추고, 다음 git_sync가 저널로 마무리·취소한다.
    """
    gd = _gitdir(root)
    cur_branch = _git(root, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip()
    res: dict = {"local": "", "kept_dirty": [], "merged_dirty": [], "branch": cur_branch or None}
    rec = _recover_journal(root)
    if rec:
        res["recovered"] = rec
    if not cur_branch:
        res["local"] = "skipped(detached HEAD)"
        return res
    head = _rev(root, "HEAD")
    if not head:
        res["local"] = "skipped(HEAD 없음)"
        return res
    try:
        kept = _load_kept_strict(root)
    except KeptCorrupt as e:
        res.update(local=f"skipped(보존 기록 손상 — .git/git_sync_kept.json 확인: {e})", kept_corrupt=True)
        return res
    ref = f"refs/heads/{cur_branch}"
    if head == target:
        _save_kept(root, _prune_kept(root, kept, head))
        res["local"] = "already"
        return res
    if _is_ancestor(root, target, head):
        # ★[2026-11-24 K1 리뷰 K1-CONC-07] 이미 target보다 앞서 있고 그 앞선 부분이 origin에 있으면(다른 실행이 더 새
        #   origin으로 ff한 직후 등) 갈라짐이 아니다 — 舊는 '로컬에만 있는 변경'이라는 거짓 경고를 냈다.
        om = _rev(root, "refs/remotes/origin/main")
        if om and (om == head or _is_ancestor(root, head, om)):
            _save_kept(root, _prune_kept(root, kept, head))
            res["local"] = "already"
            return res
    if not _is_ancestor(root, head, target):
        # 갈라졌어도 **로컬 전용 커밋이 바꾼 경로가 target에 같은 내용으로 이미 다 있으면** 옮겨도 잃는 게 없다
        # (= 같은 변경이 다른 커밋으로 올라갔다 · 10/16 마감 대사 4커밋을 한 커밋으로 올린 경우).
        mb = _git(root, "merge-base", head, target).stdout.strip()
        mine = [n for n in _git(root, "diff", "--name-only", "--no-renames", "-z", mb, head).stdout.split("\0") if n] \
            if mb else []
        hb, tb = _blobs(root, head, mine), _blobs(root, target, mine)
        lost = [p for p in mine if hb.get(p) != tb.get(p)]
        if not mb or lost:
            res["local"] = f"skipped(갈라짐 — 로컬에만 있는 변경 {len(lost) or '?'}건)"
            res["local_only"] = lost[:20]
            return res
    names = [n for n in _git(root, "diff", "--name-only", "--no-renames", "-z", head, target).stdout.split("\0") if n]
    zero = "0" * len(head)

    # ① 분류 ─────────────────────────────────────────────────────────────────────
    idx = _index_all(root)
    if any(idx.get(p, ("", "", "0"))[2] != "0" for p in names):
        res["local"] = "skipped(병합 중인 인덱스 항목이 바뀌는 경로에 있다)"
        return res
    old_e, new_e = _tree_entries(root, head, names), _tree_entries(root, target, names)
    if any(e[0] in ("120000", "160000") for e in list(old_e.values()) + list(new_e.values())):
        res["local"] = "skipped(심볼릭 링크·서브모듈 경로 — 수동 확인)"
        return res
    snap = {p: _snap(root, p) for p in names}
    cur_b = _wt_hashes(root, names)
    unstable = {p for p in names if _snap(root, p) != snap[p]}   # 해시하는 사이 바뀌는 중 — 손대지 않는다
    for p in names:
        if snap[p] is _NONFILE:
            cur_b[p] = "<nonfile>"
        elif snap[p] is None:
            cur_b.pop(p, None)
    kept_base_e: dict[str, tuple[str, str] | None] = {p: _tree_entries(root, kept[p], [p]).get(p) for p in names if p in kept}

    entries: dict[str, tuple[str, str] | None] = {p: new_e.get(p) for p in names}
    ops: list[dict] = []
    kept_list: list[str] = []
    merged: list[str] = []
    staged_merged: list[str] = []
    blocked: list[str] = []
    new_kept = dict(kept)
    pre_kept = dict(kept)
    planned_removals: set[str] = set()

    def sha(e):
        return e[1] if e else None

    def keep(p, base_c, why=None):
        kept_list.append(p)
        new_kept[p] = base_c
        pre_kept[p] = base_c
        if why == "blocked":
            blocked.append(p)

    # ★[2026-11-24 K1 리뷰 DS-8] 대소문자만 바뀐 이름(a.txt → A.txt · 리눅스 클라우드가 만든다) — 대소문자 무시
    #   파일시스템에선 두 이름이 같은 파일이라 舊는 'A.txt = 이미 같음' + 'a.txt 삭제'로 **하나뿐인 사본을 지웠다**.
    handled: set[str] = set()
    if _ignorecase(root):
        groups: dict[str, list[str]] = {}
        for p in names:
            groups.setdefault(p.lower(), []).append(p)
        for g in (v for v in groups.values() if len(v) > 1):
            disk = _disk_name(root, g[0])
            adds = [p for p in g if p in new_e]
            clean = (disk in g and disk in old_e and disk not in kept and disk not in unstable
                     and cur_b.get(disk) == sha(old_e.get(disk)) and len(adds) <= 1
                     and all(sha(idx.get(p) and idx[p][:2]) == sha(old_e.get(p)) for p in g))
            if not clean:
                res["local"] = f"skipped(대소문자만 다른 경로에 수정 중 — 수동 확인: {', '.join(g[:4])})"
                return res
            ops.append({"kind": "remove", "path": disk, "expect": snap[disk]})
            planned_removals.add(disk)
            if adds:
                data = _smudge(root, adds[0], new_e[adds[0]][1])
                if data is None:
                    res["local"] = "skipped(블롭 읽기 실패)"
                    return res
                ops.append({"kind": "write", "path": adds[0], "data": data, "expect": None, "mode": new_e[adds[0]][0],
                            "group": True})
            handled.update(g)

    for p in names:
        if p in handled:
            continue
        o, n = old_e.get(p), new_e.get(p)
        cur = cur_b.get(p)
        ie = idx.get(p)
        base_c = kept.get(p, head)
        base_e = kept_base_e.get(p) if p in kept else o
        staged = (ie[:2] if ie else None) != o
        if p in unstable:
            keep(p, base_c)
            continue
        # ★[2026-11-24 K1 리뷰 DS-12] 인덱스에 staged 항목(HEAD와 다름)이 있으면 舊는 그걸 무시하고 checkout/reset으로
        #   덮었다(staged 내용 소실 · 또는 조용히 unstaged). 이제 staged 블롭도 업스트림과 병합해 **staged로 남긴다**.
        #   병합이 안 되면(충돌·삭제) 전체 ff를 건너뛴다 — 옛 판 staged를 새 HEAD 밑에 두면 다음 commit이 되돌린다.
        if staged:
            if ie is None or o is None or n is None:
                res["local"] = f"skipped(staged 항목이 업스트림 삭제·추가와 겹친다: {p})"
                return res
            sm = _merge_norm(root, p, o[1], _cat_blob(root, ie[1]) or b"", n[1])
            if sm is None:
                res["local"] = f"skipped(staged 항목이 업스트림과 충돌: {p})"
                return res
            entries[p] = (n[0], sm[1])
            staged_merged.append(p)
            if cur == ie[1]:                               # 워킹트리 = staged 내용 → 병합본으로
                ops.append({"kind": "write", "path": p, "data": _match_eol(snap[p], sm[0]), "expect": snap[p],
                            "mode": n[0]})
                continue
        if cur == sha(n) or (cur is None and n is None):
            new_kept.pop(p, None)
            continue                                       # 이미 같다 — 인덱스만 맞추면 된다
        if p not in kept and cur == sha(o):                # 깨끗(HEAD 그대로 · 둘 다 없음 포함) → target으로
            if n is None:
                ops.append({"kind": "remove", "path": p, "expect": snap[p]})
                planned_removals.add(p)
            else:
                data = _smudge(root, p, n[1])
                if data is None:
                    keep(p, base_c)
                    continue
                ops.append({"kind": "write", "path": p, "data": data, "expect": snap[p], "mode": n[0]})
            continue
        if base_e and n and isinstance(snap[p], bytes):
            m = _merge_norm(root, p, base_e[1], snap[p], n[1])
            if m is not None:
                ops.append({"kind": "write", "path": p, "data": m[0], "expect": snap[p], "mode": n[0], "merge": True})
                pre_kept[p] = base_c                       # write-ahead — 쓰기 전에 죽어도 기반을 안다
                new_kept.pop(p, None)
                continue
        keep(p, base_c, "blocked" if snap[p] is _NONFILE else None)   # 충돌·삭제·바이너리 — 덮지 않는다

    # ★[2026-11-24 K1 리뷰 DS-5] 미추적 디렉터리·파일이 그 경로(또는 상위 경로)를 차지하고 있으면 덮지 않는다 —
    #   舊 `checkout <target> -- path`는 강제 의미라 미추적 cache/·notes를 **복구 불가로** 지웠다.
    for op in list(ops):
        if op["kind"] != "write" or op.get("group"):
            continue
        parts = op["path"].split("/")
        for i in range(1, len(parts)):
            pre = "/".join(parts[:i])
            fp = os.path.join(root, pre)
            if os.path.lexists(fp) and not (os.path.isdir(fp) and not os.path.islink(fp)) and pre not in planned_removals:
                ops.remove(op)
                keep(op["path"], kept.get(op["path"], head), "blocked")
                break

    # ② 보존 기록 write-ahead ─────────────────────────────────────────────────────
    if not _save_kept(root, pre_kept):
        res["local"] = "skipped(보존 기록 쓰기 실패)"
        return res

    tmp = os.path.join(gd, f"git_sync_ffidx_{os.getpid()}")
    env = {**os.environ, "GIT_INDEX_FILE": tmp}
    done: list[dict] = []

    def build_index() -> bytes | None:
        cur_idx = _read_bytes(os.path.join(gd, "index"))
        for p in (tmp, tmp + ".lock"):
            if os.path.exists(p):
                os.remove(p)
        if cur_idx is not None:
            with open(tmp, "wb") as f:
                f.write(cur_idx)
        _index_info(root, env, entries, zero)
        _fault("after_index_build")
        _git(root, "update-index", "-q", "--refresh", env=env)
        return cur_idx

    def abort(why: str) -> dict:
        _undo_ops(root, done)
        _save_kept(root, kept)
        for p in (tmp, os.path.join(gd, "git_sync_journal.json")):
            try:
                os.remove(p)
            except OSError:
                pass
        res.update(local=f"skipped({why})", kept_dirty=[], merged_dirty=[])
        return res

    try:
        # ③ 새 인덱스(옆 파일)
        build_index()
        # ④ 워킹트리 — CAS(★DS-6·K1-CONC-08: 분류 뒤 다른 세션이 쓴 내용은 덮지 않는다)
        ops.sort(key=lambda o: 0 if o["kind"] == "remove" else 1)
        for op in ops:
            p = op["path"]
            if _snap(root, p) != op["expect"]:
                if not op.get("group"):
                    entries_keep = kept.get(p, head)
                    keep(p, entries_keep)
                    if p in merged:
                        merged.remove(p)
                    continue
                return abort(f"대소문자 경로가 그 사이 바뀌었다: {p}")
            try:
                _do_op(root, op)
            except OSError:
                keep(p, kept.get(p, head))
                continue
            done.append(op)
            if op.get("merge"):
                merged.append(p)
            _fault("mid_ops")
        _fault("after_ops")
        if kept_list:                                      # CAS로 돌린 경로까지 기반을 다시 적어 둔다
            _save_kept(root, pre_kept)
        _git(root, "update-index", "-q", "--refresh", env=env)
        # ⑤ index.lock = 새 인덱스(본 인덱스가 그 사이 바뀌었으면 다시 만든다)
        snap_idx = _read_bytes(os.path.join(gd, "index"))
        lock = os.path.join(gd, "index.lock")
        journal = _journal_file(root)
        for _attempt in range(5):
            lsha = _sha1_file(tmp)
            _atomic_write(journal, json.dumps({"pid": os.getpid(), "ref": ref, "head": head, "target": target,
                                               "lock_sha": lsha, "tmp": tmp, "t": time.time()}).encode("utf-8"))
            if not _take_index_lock(gd, tmp, INDEX_LOCK_WAIT):
                return abort(f"index.lock 사용 중 — 다른 git이 {INDEX_LOCK_WAIT:.0f}초 넘게 쥐고 있다 · 아무것도 안 바꿈")
            if _read_bytes(os.path.join(gd, "index")) == snap_idx:
                break
            os.remove(lock)                                 # 다른 세션이 그 사이 add했다 — 그 위에 다시 만든다
            snap_idx = build_index()
            _git(root, "update-index", "-q", "--refresh", env=env)
        else:
            return abort("인덱스가 계속 바뀐다(다른 세션 작업 중)")
        _fault("after_lock")
        # ⑦ ref CAS
        r = _git(root, "update-ref", "-m", "git_sync: fast-forward", ref, target, head)
        if r.returncode != 0:                              # 그 사이 다른 세션이 HEAD를 옮겼다
            try:
                os.remove(lock)
            except OSError:
                pass
            return abort(f"update-ref 경합: {r.stderr.strip()[:120]}")
        _fault("after_ref")
        # ⑧ 인덱스 원자 교체
        swapped = False
        for i in range(40):
            try:
                os.replace(lock, os.path.join(gd, "index"))
                swapped = True
                break
            except PermissionError:
                time.sleep(0.05 * (1 + i % 5))
            except OSError:
                break
        if not swapped:
            _git(root, "update-ref", "-m", "git_sync: fast-forward 되돌림", ref, head, target)
            try:
                os.remove(lock)
            except OSError:
                pass
            return abort("index 교체 실패 — ref 되돌림")
        _fault("after_swap")
        for p in (journal, tmp):
            try:
                os.remove(p)
            except OSError:
                pass
    except _Fault:
        raise
    except (OSError, subprocess.SubprocessError) as e:
        lock = os.path.join(gd, "index.lock")
        if _rev(root, ref) == target:                      # ref는 옮겨졌는데 그 뒤가 실패 — 되돌린다
            _git(root, "update-ref", "-m", "git_sync: fast-forward 되돌림", ref, head, target)
        if _sha1_file(lock) == _sha1_file(tmp):
            try:
                os.remove(lock)
            except OSError:
                pass
        return abort(f"{type(e).__name__}: {str(e)[:120]}")
    _save_kept(root, _prune_kept(root, new_kept, target))
    res.update(local="ff", kept_dirty=kept_list, merged_dirty=merged)
    if staged_merged:
        res["staged_merged"] = staged_merged
    if blocked:
        res["blocked"] = blocked
    return res


def sync_checkout(root: str, fetch: bool = True, remote: str = "origin", branch: str = "main",
                  fetch_timeout: float = 120, lock_wait: float = LOCK_WAIT_SYNC) -> dict:
    """(fetch →) 지금 체크아웃을 origin/main으로 안전하게 따라가게 한다. 자동 작성기(마감 대사·스캔)가
    파일을 고치기 **전에** 부른다 — 옛 판 위에서 고치면 publish가 병합·충돌로 막힌다.
    fetch는 잠금 밖에서(경합은 _fetch가 재시도), ff는 저장소 잠금 안에서 한다."""
    note = ""
    if fetch:
        ok, err = _fetch(root, remote, branch, fetch_timeout)
        if not ok:
            note = f"fetch 실패 — 마지막으로 받은 origin 기준: {err}"
    t = _rev(root, f"refs/remotes/{remote}/{branch}")
    if t:
        o = fast_forward_local(root, t, lock_wait=lock_wait)
    else:
        o = {"local": "skipped(origin ref 없음 — refs/remotes/origin/main · fetch 확인)", "kept_dirty": [],
             "merged_dirty": [], "branch": _git(root, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip() or None}
    if note:
        o["fetch"] = note
    lf = last_fetch_ok(root)
    o["last_fetch_age_min"] = round((time.time() - lf) / 60, 1) if lf else None
    return o


def _rebase_stale(root: str, base: str, changed: list[str], env: dict, kept: dict[str, str]
                  ) -> tuple[list[str], list[str], list[str]]:
    """올릴 파일 중 **옛 판을 바탕으로 고친 것**을 origin(base) 판과 3-way 병합한다(★11/22).

    판정 = 기반 판(보존 기록 > merge-base(HEAD, base))과 base 판이 다르면 — 그대로 올리면 그 사이 남이 넣은 변경이
    되돌아간다. 반환: (병합한 파일, 충돌·불가 파일, 로컬에서 안 고쳐 업스트림을 따른 파일).
    ★[2026-11-24 K1 리뷰]
      · DS-2: 변경 집합을 **임시 인덱스 vs base**(`diff --cached`)로 받는다 — 舊 `diff --name-only`는 base에 없는 파일을
        미추적으로 봐서 업스트림이 지운 파일이 판정 없이 되살아났다. 한쪽만 있는 경로는 충돌.
      · DS-3: 워킹트리에 없는데(로컬 삭제) 기반 ≠ origin이면 충돌.
      · 로컬에서 안 고친 파일(워킹트리 = 기반)은 커밋에서 빼고 업스트림을 따른다(고정 경로 목록의 깨끗한 옛 사본이
        업스트림 수정·삭제를 되돌리던 11/21형 소실).
      · DS-4·DS-14: 병합본은 **임시 인덱스에만** 넣고 워킹트리에 쓰지 않는다 — 재시도마다 원래 워킹트리가 ours이고,
        로컬 반영은 푸시 뒤 ff가 같은 병합으로 한다(ff를 못 하면 워킹트리는 그대로 = 업스트림이 옛 HEAD 위에 안 섞인다).
    임시 인덱스(env)는 이미 base 트리 + 내 경로를 add한 상태여야 한다."""
    if not changed:
        return [], [], []
    mb = _git(root, "merge-base", "HEAD", base).stdout.strip()
    if not mb and not any(c in kept for c in changed):
        return [], [], []                  # 무관한 히스토리 — 판정 불가(舊 동작)
    rb = _tree_entries(root, base, changed)
    lb: dict[str, tuple[str, str] | None] = {}
    if mb:
        lb.update(_tree_entries(root, mb, [c for c in changed if c not in kept]))
    for c in changed:
        if c in kept:
            lb[c] = _tree_entries(root, kept[c], [c]).get(c)
    tidx = _index_all(root, env=env)
    zero = "0" * len(base)
    rebased, conflicts, unchanged = [], [], []
    upd: dict[str, tuple[str, str] | None] = {}
    for c in changed:
        if c not in kept and not mb:
            continue
        remote, lbase = rb.get(c), lb.get(c)
        if (remote[1] if remote else None) == (lbase[1] if lbase else None):
            continue                       # 워킹트리 수정이 지금의 origin 판 위에 있다 — 안전
        w = _snap(root, c)
        if w is _NONFILE:
            conflicts.append(c)
            continue
        wh = _hash_bytes(root, c, w) if isinstance(w, bytes) else None
        if wh == (lbase[1] if lbase else None):
            upd[c] = remote                # 로컬에선 안 고쳤다 — 업스트림을 따른다(되돌림 방지)
            unchanged.append(c)
            continue
        if remote is None or lbase is None or w is None:
            conflicts.append(c)            # 한쪽이 지우거나 새로 만든 경로가 겹침 — 사람이 판단
            continue
        m = _merge_norm(root, c, lbase[1], w, remote[1])
        if m is None:
            conflicts.append(c)
            continue
        mode = (tidx.get(c) or (remote[0],))[0]
        upd[c] = (mode, m[1])
        rebased.append(c)
    if conflicts:
        return rebased, conflicts, unchanged
    _index_info(root, env, upd, zero)
    return rebased, [], unchanged


def _bad_paths(root: str, paths: list[str]) -> list[str]:
    """★[2026-11-24 K1 리뷰 DS-13] 파일 경로만 받는다 — 디렉터리 pathspec은 임시 인덱스에 그 아래 **다른 세션의
    dirty·미추적 파일까지** 쓸어 담았다(공유 워킹트리 규약 위반)."""
    bad = []
    for p in paths:
        n = os.path.normpath(p).replace("\\", "/")
        if (not p or n in (".", "..") or n.startswith("../") or os.path.isabs(p) or p.endswith("/")
                or os.path.isdir(os.path.join(root, p))):
            bad.append(p)
    return bad


def publish(root: str, paths: list[str], msg: str, remote: str = "origin", branch: str = "main",
            retries: int = 3, ff_local: bool = True, lock_wait: float = LOCK_WAIT_PUBLISH) -> dict:
    """paths의 워킹트리 내용을 remote/branch 위 커밋 하나로 올린다(★11/22 — 옛 판 바탕이면 3-way 병합본).

    반환: {"status": pushed|nochange|push_failed|fetch_failed|stale_conflict, "commit", "base", "local",
           "kept_dirty", "merged_dirty", "rebased", "conflicts", "error", "unchanged"}
    """
    paths = [p.replace("\\", "/") for p in paths if p]
    out: dict = {"status": "push_failed", "commit": None, "base": None, "local": "skipped", "kept_dirty": [],
                 "merged_dirty": [], "rebased": [], "conflicts": [], "error": "", "unchanged": []}
    bad = _bad_paths(root, paths)
    if bad or not paths:
        out["error"] = ("경로 오류 — 파일 경로만 받는다(디렉터리·전체 경로 거부): " + ", ".join(bad[:8])) if bad \
            else "경로 없음"
        return out
    lk = _RepoLock(root, lock_wait)
    if not lk.acquire():
        out["error"] = f"다른 git_sync 실행 중 — 잠금 대기 {lock_wait:.0f}초 초과(.git/git_sync.lock)"
        return out
    try:
        return _publish_locked(root, paths, msg, remote, branch, retries, ff_local, out)
    finally:
        lk.release()


def _publish_locked(root, paths, msg, remote, branch, retries, ff_local, out) -> dict:
    rec = _recover_journal(root)
    if rec:
        out["recovered"] = rec
    try:
        kept = _load_kept_strict(root)
    except KeptCorrupt as e:
        out.update(status="stale_conflict", conflicts=list(paths),
                   error=f"보존 기록 손상({e}) — 어느 파일이 옛 판 위인지 알 수 없어 아무것도 올리지 않았다. "
                         ".git/git_sync_kept.json을 확인·복구할 것")
        return out
    idx = os.path.join(_gitdir(root), f"git_sync_index_{os.getpid()}")
    env = {**os.environ, "GIT_INDEX_FILE": idx}
    want = set(paths)
    try:
        for _ in range(max(1, retries)):
            ok, err = _fetch(root, remote, branch)
            base = _rev(root, f"refs/remotes/{remote}/{branch}")
            if not ok or not base:
                out.update(status="fetch_failed",
                           error=err or f"origin ref 없음(refs/remotes/{remote}/{branch}) — fetch refspec 확인")
                return out
            out["base"] = base
            r = _git(root, "read-tree", base, env=env)
            if r.returncode != 0:
                out.update(status="push_failed", error=f"read-tree: {r.stderr.strip()[:200]}")
                return out
            r = _git(root, "--literal-pathspecs", "add", "-A", "--pathspec-from-file=-", "--pathspec-file-nul",
                     env=env, inp="\0".join(paths))
            if r.returncode != 0:
                out.update(status="push_failed", error=f"add: {r.stderr.strip()[:200]}")
                return out
            changed = [n for n in _git(root, "diff", "--cached", "--name-only", "--no-renames", "-z", base,
                                       env=env).stdout.split("\0") if n]
            stray = [c for c in changed if c not in want]
            if stray:
                out.update(status="push_failed", error="요청 밖 경로가 섞였다(중단): " + ", ".join(stray[:8]))
                return out
            rebased, conflicts, unchanged = _rebase_stale(root, base, changed, env, kept)
            out["rebased"] = sorted(set(rebased))
            out["unchanged"] = sorted(set(unchanged))
            if conflicts:
                out.update(status="stale_conflict", conflicts=conflicts,
                           error="옛 판을 바탕으로 고친 파일이 origin 변경과 충돌 — 아무것도 올리지 않았다. "
                                 "`git_sync.py --ff-only`로 맞춘 뒤 충돌 파일을 직접 합치고, 합친 파일은 "
                                 "`git_sync.py --resolved <경로>`로 기록을 푼 뒤 다시 올릴 것: " + ", ".join(conflicts[:8]))
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
                # ★[2026-11-24 K1 리뷰 K1-CONC-07] CAS — 다른 실행이 그 사이 더 새 origin을 받았으면 뒤로 감지 않는다
                _git(root, "update-ref", f"refs/remotes/{remote}/{branch}", new, base)
                out.update(status="pushed", commit=new, error="")
                break
            out["error"] = (p.stderr or "").strip()[:200]   # 그 사이 누가 올렸다 → 다시 받아 재구성(원래 워킹트리 기준)
    except (OSError, subprocess.SubprocessError) as e:      # ★K1-CONC-10 — 긴 명령줄 등은 상태로 돌려준다
        out.update(status="push_failed", error=f"{type(e).__name__}: {str(e)[:160]}")
        return out
    finally:
        try:
            os.remove(idx)
        except OSError:
            pass
    if ff_local and out["status"] in ("pushed", "nochange") and out["commit"]:
        out.update(_ff_locked(root, out["commit"]))
    return out


def status(root: str) -> dict:
    """읽기 전용 — fetch하지 않는다(마지막으로 받은 origin 기준). 훅·validate가 쓴다."""
    head = _rev(root, "HEAD")
    om = _rev(root, "refs/remotes/origin/main")
    o: dict = {"branch": _git(root, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip() or None,
               "head": head, "origin": om, "behind": None, "behind_nonbot": None, "ahead": None,
               "ahead_canon": [], "local_latest": None, "origin_latest": None, "kept": {},
               "kept_corrupt": False, "last_fetch_ok": last_fetch_ok(root),
               "journal_pending": os.path.exists(_journal_file(root))}
    try:
        o["kept"] = _load_kept_strict(root)
    except KeptCorrupt:
        o["kept_corrupt"] = True
    if not head or not om:
        return o
    o["behind"] = int(_git(root, "rev-list", "--count", f"HEAD..{om}").stdout.strip() or 0)
    authors = _git(root, "log", "--format=%an", f"HEAD..{om}").stdout.split("\n")
    o["behind_nonbot"] = sum(1 for a in authors if a.strip() and a.strip() not in BOT_AUTHORS)
    o["ahead"] = int(_git(root, "rev-list", "--count", f"{om}..HEAD").stdout.strip() or 0)
    if o["ahead"]:
        ch = _git(root, "diff", "--name-only", "--no-renames", f"{om}...HEAD").stdout.split("\n")
        o["ahead_canon"] = [c for c in ch if c.startswith(("docs/reports/", "data/app/", "docs/master.md"))][:20]

    def latest(names: list[str]) -> int | None:
        vs = [int(m.group(1)) for n in names if (m := REPORT_RE.match(n.strip()))]
        return max(vs) if vs else None

    try:
        local = ["docs/reports/" + n for n in os.listdir(os.path.join(root, "docs", "reports"))]
    except OSError:
        local = []
    o["local_latest"] = latest(local)
    o["origin_latest"] = latest(_git(root, "ls-tree", "--name-only", om, "docs/reports/").stdout.split("\n"))
    return o


def describe(o: dict) -> str:
    s = {"pushed": "푸시 완료", "nochange": "변경 없음", "push_failed": "푸시 실패",
         "fetch_failed": "fetch 실패", "stale_conflict": "푸시 중단(옛 판 충돌)"}.get(o.get("status"), o.get("status"))
    tail = f" · 로컬 {o.get('branch') or '체크아웃'} {o.get('local')}"
    if o.get("rebased"):
        tail += f" · 옛 판 병합 {len(o['rebased'])}건"
    if o.get("unchanged"):
        tail += f" · 안 고친 파일 업스트림 따름 {len(o['unchanged'])}건"
    if o.get("merged_dirty"):
        tail += f" · dirty 병합 {len(o['merged_dirty'])}건"
    if o.get("kept_dirty"):
        tail += f"(다른 세션 수정 보존 {len(o['kept_dirty'])}건)"
    if o.get("recovered"):
        tail += f" · {o['recovered']}"
    err = f" — {o['error']}" if o.get("error") and o.get("status") not in ("pushed", "nochange") else ""
    return s + (f" {o['commit'][:8]}" if o.get("status") == "pushed" else "") + tail + err


# ── 자가검증(오프라인 · 임시 저장소) ─────────────────────────────────────────────
#   ★[2026-11-24 K1 리뷰] `selftest(gs)` — 검사 대상 모듈을 받는다(기본 = 이 모듈). 리뷰 재현 때 舊 모듈을 넣어
#   각 케이스가 **고치기 전 코드에선 실패**하는지 확인했다(케이스 이름 끝 [id] = 리뷰 결함 번호).
_CHILD = r'''
import importlib.util, json, os, sys
spec = importlib.util.spec_from_file_location("gs_child", sys.argv[1])
gs = importlib.util.module_from_spec(spec); spec.loader.exec_module(gs)
mode, local, step = sys.argv[2], sys.argv[3], sys.argv[4]
if step.startswith("git:"):
    verb, orig = step[4:], gs._git
    def g(root, *a, **k):
        if verb in a:
            os._exit(9)
        return orig(root, *a, **k)
    gs._git = g
elif step != "-":
    gs._FAULT = step
    os.environ["GIT_SYNC_FAULT_EXIT"] = "1"
if mode == "sync":
    o = gs.sync_checkout(local, fetch=False)
else:
    o = gs.publish(local, sys.argv[5:], "child " + " ".join(sys.argv[5:]))
print(json.dumps(o, ensure_ascii=False))
'''


def selftest(gs=None) -> int:  # noqa: C901 — 시나리오 나열
    import threading
    gs = gs or sys.modules[__name__]
    tmp = tempfile.mkdtemp(prefix="git_sync_")
    fails: list[str] = []
    n_case = [0]

    def sh(cwd, *a, check=True):
        r = subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if check and r.returncode != 0:
            raise RuntimeError(f"git {' '.join(a)}: {r.stderr}")
        return r.stdout

    def wr(path, s, nl="\n"):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8", newline=nl) as f:
            f.write(s)

    def rd(path):
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()

    def chk(cond, what):
        print(("  ✅ " if cond else "  ❌ ") + what)
        if not cond:
            fails.append(what)

    def setup(tag, files, attrs=None, branch="claude/feat"):
        """bare origin + local(공유 체크아웃 = 기능 브랜치) + cloud. files = {path: text}."""
        n_case[0] += 1
        d = os.path.join(tmp, f"{n_case[0]:02d}_{tag}")
        bare, local, cloud = (os.path.join(d, x) for x in ("remote.git", "local", "cloud"))
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", cloud], check=True)
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
            sh(cloud, "config", k, v)
        if attrs:
            wr(os.path.join(cloud, ".gitattributes"), attrs)
            files = {**files, ".gitattributes": attrs}
        for p, s in files.items():
            wr(os.path.join(cloud, p), s)
        sh(cloud, "add", "-A")
        sh(cloud, "commit", "-q", "-m", "init")
        sh(cloud, "remote", "add", "origin", bare)
        sh(cloud, "push", "-q", "origin", "main")
        subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", bare, local], check=True, capture_output=True)
        for k, v in (("user.name", "t"), ("user.email", "t@t")):
            sh(local, "config", k, v)
        if branch != "main":
            sh(local, "checkout", "-q", "-b", branch)
        return bare, local, cloud

    def cloud_commit(cloud, changes, msg="cloud"):
        sh(cloud, "pull", "-q", "--rebase", "origin", "main", check=False)
        for p, s in changes.items():
            fp = os.path.join(cloud, p)
            if s is None:
                sh(cloud, "rm", "-q", "--", p)
            else:
                wr(fp, s)
                sh(cloud, "add", "--", p)
        sh(cloud, "commit", "-q", "-m", msg)
        sh(cloud, "push", "-q", "origin", "main")
        return sh(cloud, "rev-parse", "HEAD").strip()

    def child(mode, local, step, *paths):
        script = os.path.join(tmp, "child.py")
        if not os.path.exists(script):
            with open(script, "w", encoding="utf-8") as f:
                f.write(_CHILD)
        r = subprocess.run([sys.executable, script, gs.__file__, mode, local, step, *paths], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=180)
        try:
            return r.returncode, json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            return r.returncode, {"_err": r.stderr[-300:]}

    only = os.environ.get("GIT_SYNC_SELFTEST_ONLY", "")

    def case(name, fn):
        if only and not any(k in name for k in only.split(",")):
            return
        print(f"── {name}")
        t0 = time.time()
        try:
            fn()
        except Exception as e:  # noqa: BLE001 — 舊 모듈은 예외로 무너진다 = 실패로 센다
            fails.append(f"{name}: 예외 {type(e).__name__}: {str(e)[:160]}")
            print(f"  ❌ 예외 {type(e).__name__}: {str(e)[:200]}")
        print(f"     ({time.time() - t0:.1f}초)")

    L = "".join(f"l{i}\n" for i in range(1, 11))

    # ── ①~⑩ 기본 시나리오(11/22) ───────────────────────────────────────────────
    def legacy():
        bare = os.path.join(tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
        local, cloud = os.path.join(tmp, "local"), os.path.join(tmp, "cloud")
        for d in (local, cloud):
            subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", bare, d], check=True, capture_output=True)
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
        o = gs.publish(local, ["C.txt"], "mine C")
        print("  ①", gs.describe(o))
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

        o = gs.publish(local, ["C.txt"], "noop")
        chk(o["status"] == "nochange", "② 변경 없으면 커밋 안 만든다")

        sh(cloud, "pull", "-q", "origin", "main")
        wr(os.path.join(cloud, "B.txt"), "B.txt cloud2\n")
        sh(cloud, "commit", "-q", "-am", "cloud B")
        sh(cloud, "push", "-q", "origin", "main")
        head_b3 = sh(local, "rev-parse", "HEAD").strip()
        wr(os.path.join(local, "C.txt"), "C.txt mine2\n")
        o = gs.publish(local, ["C.txt"], "mine C2")
        chk(o["status"] == "pushed" and "B.txt" in o["kept_dirty"], "③ 겹치는 dirty 파일은 kept_dirty로 보고")
        chk(rd(os.path.join(local, "B.txt")) == "B.txt someone-else WIP\n", "③ 그 파일 워킹트리는 그대로")
        chk(sh(local, "show", "HEAD:B.txt") == "B.txt cloud2\n", "③ HEAD는 업스트림 내용")
        chk(gs.load_kept(local).get("B.txt") == head_b3, "③ 보존 기록 = 그 파일의 진짜 기반 커밋(④)")
        before = sh(bare, "rev-parse", "main").strip()
        o = gs.publish(local, ["B.txt"], "would revert cloud B")
        chk(o["status"] == "stale_conflict" and sh(bare, "rev-parse", "main").strip() == before,
            f"③' 보존 파일 그대로 올리기 = stale_conflict({o['status']}) · origin 불변")
        sh(local, "checkout", "--", "B.txt")                       # 그 세션이 WIP를 버렸다
        gs.fast_forward_local(local, sh(local, "rev-parse", "HEAD").strip())
        chk("B.txt" not in gs.load_kept(local), "③'' 깨끗해지면 보존 기록에서 빠진다")

        wr(os.path.join(local, "D.txt"), "D local-only\n")
        sh(local, "add", "D.txt")
        sh(local, "commit", "-q", "-m", "local only D")
        before = sh(local, "rev-parse", "HEAD").strip()
        wr(os.path.join(local, "C.txt"), "C.txt mine3\n")
        o = gs.publish(local, ["C.txt"], "mine C3")
        chk(o["status"] == "pushed" and o["local"].startswith("skipped(갈라짐"), "④ 갈라짐이면 로컬 ref 불변")
        chk(sh(local, "rev-parse", "HEAD").strip() == before, "④ HEAD 그대로")
        chk(rd(os.path.join(local, "C.txt")) == "C.txt mine3\n", "④ 내 파일 내용 그대로")

        wr(os.path.join(local, "E.txt"), "E local-only\n")
        sh(local, "add", "E.txt")
        sh(local, "commit", "-q", "-m", "local only E")
        o = gs.publish(local, ["D.txt", "E.txt"], "carry D E")
        remote_head = sh(bare, "rev-parse", "main").strip()
        chk(o["status"] == "pushed" and o["local"] == "ff", f"⑤ 로컬 전용 변경이 다 올라갔으면 로컬 ff ({o['local']})")
        chk(sh(local, "rev-parse", "HEAD").strip() == remote_head, "⑤ HEAD = origin")
        st = sorted(sh(local, "status", "--porcelain").splitlines())
        chk(st == [], f"⑤ status 깨끗 ({st})")

        sh(cloud, "pull", "-q", "origin", "main")
        wr(os.path.join(cloud, "T.txt"), "t1\nt2\nt3\nt4\nt5\nt6\nt7\nt8\n")
        sh(cloud, "add", "T.txt")
        sh(cloud, "commit", "-q", "-m", "T init")
        sh(cloud, "push", "-q", "origin", "main")
        gs.sync_checkout(local)
        sh(local, "checkout", "-q", "-B", "claude/drift-test")
        chk(sh(local, "rev-parse", "HEAD").strip() == sh(bare, "rev-parse", "main").strip(),
            "⑥ 준비: 기능 브랜치가 origin/main과 같은 지점")
        wr(os.path.join(cloud, "T.txt"), "t1\nR3-added\nt2\nt3\nt4\nt5\nt6\nt7\nt8\n")
        sh(cloud, "commit", "-q", "-am", "R3 adds item")
        sh(cloud, "push", "-q", "origin", "main")
        sh(local, "fetch", "-q", "origin", "main")
        s6 = gs.status(local)
        chk(s6["behind"] == 1 and s6["behind_nonbot"] == 1 and s6["ahead"] == 0, f"⑥ status 뒤처짐 1 ({s6['behind']})")
        o = gs.sync_checkout(local, fetch=False)
        tgt = sh(local, "rev-parse", "origin/main").strip()
        chk(o["local"] == "ff" and o.get("branch") == "claude/drift-test"
            and sh(local, "rev-parse", "HEAD").strip() == tgt, f"⑥ 기능 브랜치 체크아웃도 ff ({o['local']})")
        chk("R3-added" in rd(os.path.join(local, "T.txt")), "⑥ 클라우드 줄이 로컬 워킹트리에 내려왔다")

        sh(local, "checkout", "-q", "-B", "claude/drift-test", "HEAD~1")
        wr(os.path.join(local, "T.txt"), "t1\nt2\nt3\nt4\nt5\nt6\nlocal-edit\nt7\nt8\n")
        o = gs.publish(local, ["T.txt"], "local edits T on stale base")
        print("  ⑦", gs.describe(o))
        tr = sh(bare, "show", "main:T.txt")
        chk(o["status"] == "pushed", f"⑦ 푸시됨 ({o['status']} {o.get('error', '')})")
        chk("R3-added" in tr, "⑦ 클라우드가 넣은 줄이 살아 있다(11/21 소실 사고 재발 방지)")
        chk("local-edit" in tr, "⑦ 내 수정도 올라갔다")
        chk("T.txt" in o["rebased"], "⑦ rebased에 보고된다")
        chk("R3-added" in rd(os.path.join(local, "T.txt")), "⑦ 병합본이 워킹트리에도 반영됐다(ff가 같은 병합으로)")
        chk(o["local"] == "ff" and sh(local, "status", "--porcelain").strip() == "", f"⑦ 로컬 ff·깨끗 ({o['local']})")

        sh(cloud, "pull", "-q", "origin", "main")
        wr(os.path.join(cloud, "T.txt"), rd(os.path.join(cloud, "T.txt")).replace("t3\n", "t3-cloud\n"))
        wr(os.path.join(cloud, "U.txt"), "u1\nu2\n")
        sh(cloud, "add", "U.txt")
        sh(cloud, "commit", "-q", "-am", "cloud edits t3 + U")
        sh(cloud, "push", "-q", "origin", "main")
        sh(local, "fetch", "-q", "origin", "main")
        before_remote = sh(bare, "rev-parse", "main").strip()
        cur = rd(os.path.join(local, "T.txt"))
        wr(os.path.join(local, "T.txt"), cur.replace("t3\n", "t3-local\n"))
        o = gs.publish(local, ["T.txt"], "conflicting edit")
        chk(o["status"] == "stale_conflict" and "T.txt" in o["conflicts"], f"⑧ 충돌이면 stale_conflict ({o['status']})")
        chk(sh(bare, "rev-parse", "main").strip() == before_remote, "⑧ origin 불변(부분 커밋도 없음)")
        chk("t3-local" in rd(os.path.join(local, "T.txt")), "⑧ 내 워킹트리 수정은 그대로")

        wr(os.path.join(local, "T.txt"), cur.replace("t8\n", "t8-wip\n"))
        head_before = sh(local, "rev-parse", "HEAD").strip()
        o = gs.sync_checkout(local, fetch=False)
        t_now = rd(os.path.join(local, "T.txt"))
        chk(o["local"] == "ff" and "T.txt" in o["merged_dirty"], f"⑨ dirty 병합 보고 ({o['local']} {o['merged_dirty']})")
        chk("t3-cloud" in t_now and "t8-wip" in t_now, "⑨ 업스트림 줄과 그 세션의 WIP가 둘 다 남는다")
        chk(sh(local, "rev-parse", "HEAD").strip() != head_before, "⑨ HEAD가 따라갔다")
        chk(rd(os.path.join(local, "U.txt")) == "u1\nu2\n", "⑨ 새 파일도 내려왔다")
        st = sh(local, "status", "--porcelain").splitlines()
        chk(st == [" M T.txt"], f"⑨ status = WIP 1건만 ({st})")
        chk("T.txt" not in gs.load_kept(local), "⑨ 병합된 파일은 보존 기록 없음")

        os.makedirs(os.path.join(cloud, "docs", "reports"), exist_ok=True)
        sh(cloud, "pull", "-q", "origin", "main")
        wr(os.path.join(cloud, "docs", "reports", "report_v2_2026-11-21.md"), "r\n")
        sh(cloud, "add", "docs/reports/report_v2_2026-11-21.md")
        sh(cloud, "commit", "-q", "-m", "report v2")
        sh(cloud, "push", "-q", "origin", "main")
        wr(os.path.join(local, "docs", "reports", "report_v1_2026-11-20.md"), "old\n")
        sh(local, "fetch", "-q", "origin", "main")
        s10 = gs.status(local)
        chk(s10["origin_latest"] == 2 and s10["local_latest"] == 1, f"⑩ 보고서 번호 대조 ({s10['local_latest']}→{s10['origin_latest']})")

    # ── ★[11/24 K1 리뷰] 순서·원자성 ─────────────────────────────────────────────
    def order_scene(tag, with_clean=True):
        bare, local, cloud = setup(tag, {"A.txt": L, "B.txt": L, "C.txt": "c\n", "D.txt": "d\n", "E.txt": "e\n"})
        head0 = sh(local, "rev-parse", "HEAD").strip()
        ch = {"A.txt": L.replace("l2\n", "l2-cloud\n"), "B.txt": L.replace("l5\n", "l5-cloud\n"), "D.txt": None}
        if with_clean:
            ch["E.txt"] = "e cloud\n"                  # 깨끗한 파일의 업스트림 변경(舊 checkout 경로)
        tgt = cloud_commit(cloud, ch)
        sh(local, "fetch", "-q", "origin", "main")
        wr(os.path.join(local, "A.txt"), L.replace("l9\n", "l9-local\n"))      # dirty · 병합 가능
        wr(os.path.join(local, "B.txt"), L.replace("l5\n", "l5-local\n"))      # dirty · 충돌
        return bare, local, cloud, head0, tgt

    def no_staged_revert(local, what):
        staged = sh(local, "diff", "--cached", "--name-status").strip()
        lock = os.path.exists(os.path.join(local, ".git", "index.lock"))
        chk(not staged or lock, f"{what}: staged 되돌림이 없다(있으면 index.lock이 git을 막고 있어야) — staged={staged!r}")

    def final_ok(local, bare, head0, tgt, what):
        o = gs.sync_checkout(local, fetch=False)
        chk(sh(local, "rev-parse", "HEAD").strip() == tgt, f"{what}: 복구 뒤 HEAD = origin ({o.get('local')} {o.get('recovered', '')})")
        chk(sh(local, "diff", "--cached", "--name-only").strip() == "", f"{what}: 복구 뒤 staged 없음")
        a = rd(os.path.join(local, "A.txt"))
        chk("l2-cloud" in a and "l9-local" in a, f"{what}: A = 업스트림+WIP")
        chk(rd(os.path.join(local, "B.txt")) == L.replace("l5\n", "l5-local\n"), f"{what}: B WIP 보존")
        chk(not os.path.exists(os.path.join(local, "D.txt")), f"{what}: 업스트림이 지운 D는 없다")
        before = sh(bare, "rev-parse", "main").strip()
        o = gs.publish(local, ["B.txt"], "would revert B")
        chk(o["status"] == "stale_conflict" and sh(bare, "rev-parse", "main").strip() == before,
            f"{what}: 보존 B 그대로 올리기 = stale_conflict ({o['status']})")
        wr(os.path.join(local, "C.txt"), "c mine\n")
        sh(local, "add", "C.txt")
        sh(local, "commit", "-q", "-m", "unrelated C")
        ch = sh(local, "show", "--name-only", "--format=", "HEAD").split()
        chk(ch == ["C.txt"], f"{what}: 다음 평범한 commit은 C만 담는다 ({ch})")

    def t_index_lock_held():
        gs.INDEX_LOCK_WAIT = 0.5
        bare, local, cloud, head0, tgt = order_scene("idxlock", with_clean=False)
        lock = os.path.join(local, ".git", "index.lock")
        open(lock, "w").close()                       # 다른 git이 index.lock을 쥐고 있다(validate-on-stop의 git status 등)
        o = gs.sync_checkout(local, fetch=False)
        os.remove(lock)
        print("   ", o.get("local"))
        chk(o["local"] != "ff" or sh(local, "diff", "--cached", "--name-only").strip() == "",
            f"index.lock 보유 중 ff = 'ff'라면 인덱스도 맞아야 [DS-1·K1-CONC-01] ({o['local']})")
        if o["local"].startswith("skipped"):
            chk(sh(local, "rev-parse", "HEAD").strip() == head0 and os.path.exists(os.path.join(local, "D.txt"))
                and "l2-cloud" not in rd(os.path.join(local, "A.txt")),
                "index.lock 때문에 건너뛰면 HEAD·워킹트리 불변 [PM-1]")
        no_staged_revert(local, "index.lock [DS-1]")
        final_ok(local, bare, head0, tgt, "index.lock 해제 후")

    def t_index_lock_released():
        gs.INDEX_LOCK_WAIT = 4.0
        bare, local, cloud, head0, tgt = order_scene("idxlock2")
        lock = os.path.join(local, ".git", "index.lock")
        open(lock, "w").close()
        threading.Timer(0.6, lambda: os.remove(lock)).start()
        o = gs.sync_checkout(local, fetch=False)
        chk(o["local"] == "ff" and sh(local, "diff", "--cached", "--name-only").strip() == "",
            f"잠금이 곧 풀리면 기다렸다가 온전히 ff [K1-CONC-01] ({o['local']})")
        gs.INDEX_LOCK_WAIT = 5.0

    def t_kill(step, ids):
        def run():
            bare, local, cloud, head0, tgt = order_scene("kill_" + step.replace(":", "_"))
            rc, o = child("sync", local, step)
            print(f"    child rc={rc}")
            no_staged_revert(local, f"kill@{step} 직후 [{ids}]")
            k = gs.load_kept(local)
            if sh(local, "rev-parse", "HEAD").strip() == tgt:
                chk(k.get("B.txt") == head0, f"kill@{step}: ref가 옮겨졌으면 B의 기반 기록이 이미 있다(write-ahead) [{ids}]")
            final_ok(local, bare, head0, tgt, f"kill@{step}")
        return run

    def t_update_ref_race():
        bare, local, cloud, head0, tgt = order_scene("refrace")
        orig = gs._git

        def g(root, *a, **k):
            if a[:1] == ("update-ref",) and "git_sync: fast-forward" in a and root == local:
                gs._git = orig                         # 다른 세션이 그 사이 ref를 옮겼다(CAS 실패 유도)
                tree = orig(root, "rev-parse", "HEAD^{tree}").stdout.strip()
                c = orig(root, "commit-tree", tree, "-p", head0, "-m", "other session").stdout.strip()
                orig(root, "update-ref", "refs/heads/claude/feat", c)
            return orig(root, *a, **k)
        gs._git = g
        try:
            o = gs.sync_checkout(local, fetch=False)
        finally:
            gs._git = orig
        st = sh(local, "status", "--porcelain").splitlines()
        chk(o["local"].startswith("skipped"), f"update-ref 경합 = skipped ({o['local']}) [DS-11]")
        chk(sh(local, "diff", "--cached", "--name-only").strip() == "", f"update-ref 경합 뒤 staged 없음 [DS-11] ({st})")
        chk(os.path.exists(os.path.join(local, "D.txt")) and "l2-cloud" not in rd(os.path.join(local, "A.txt"))
            and rd(os.path.join(local, "E.txt")) == "e\n", "update-ref 경합 뒤 워킹트리 원상 [DS-11]")

    # ── publish ──────────────────────────────────────────────────────────────────
    def t_resurrect():
        bare, local, cloud = setup("resurrect", {"A.txt": "a\n", "B.txt": "b\n"})
        cloud_commit(cloud, {"A.txt": None}, "cloud deletes A")
        wr(os.path.join(local, "B.txt"), "b mine\n")
        o = gs.publish(local, ["A.txt", "B.txt"], "pub A B stale")
        names = sh(bare, "ls-tree", "--name-only", "main").split()
        chk("A.txt" not in names, f"업스트림이 지운 깨끗한 A를 되살리지 않는다 [DS-2] ({o['status']} {names})")
        chk(sh(bare, "show", "main:B.txt") == "b mine\n", "B는 올라갔다")
        bare, local, cloud = setup("resurrect2", {"A.txt": "a\n", "B.txt": "b\n"})
        cloud_commit(cloud, {"A.txt": None}, "cloud deletes A")
        wr(os.path.join(local, "A.txt"), "a dirty\n")
        o = gs.publish(local, ["A.txt"], "pub A dirty")
        chk(o["status"] == "stale_conflict" and "A.txt" not in sh(bare, "ls-tree", "--name-only", "main").split(),
            f"업스트림 삭제 vs 로컬 수정 = stale_conflict [DS-2] ({o['status']})")

    def t_local_delete():
        bare, local, cloud = setup("localdel", {"A.txt": L, "B.txt": "b\n"})
        cloud_commit(cloud, {"A.txt": L.replace("l5\n", "l5-cloud-important\n")})
        os.remove(os.path.join(local, "A.txt"))
        o = gs.sync_checkout(local)
        chk("A.txt" in o["kept_dirty"] and "A.txt" in gs.load_kept(local), f"로컬 삭제 위 업스트림 수정 = 보존 기록 유지 [DS-3] ({gs.load_kept(local)})")
        o = gs.publish(local, ["A.txt"], "push deletion")
        chk(o["status"] == "stale_conflict" and "A.txt" in sh(bare, "ls-tree", "--name-only", "main").split(),
            f"삭제를 그대로 올리지 않는다 [DS-3] ({o['status']})")

    def t_push_race(variant):
        def run():
            bare, local, cloud = setup("pushrace_" + variant, {"T.txt": L})
            if variant == "R1":
                cloud_commit(cloud, {"T.txt": "C2-ITEM\n" + L}, "C2 adds item")
                racer = {"T.txt": L}
            else:
                cloud_commit(cloud, {"T.txt": L.replace("l3\n", "l3-v1\n")}, "C2 edits l3")
                racer = {"T.txt": L.replace("l3\n", "l3-v2\n")}
            wr(os.path.join(local, "T.txt"), L.replace("l9\n", "l9-local\n"))
            orig = gs._git
            fired = []

            def g(root, *a, **k):
                if a[:1] == ("push",) and not fired:
                    fired.append(1)
                    cloud_commit(cloud, racer, "C3 racer")
                return orig(root, *a, **k)
            gs._git = g
            try:
                o = gs.publish(local, ["T.txt"], "local T")
            finally:
                gs._git = orig
            t = sh(bare, "show", "main:T.txt")
            if variant == "R1":
                chk(o["status"] == "pushed" and "C2-ITEM" not in t and "l9-local" in t,
                    f"push 경합 재시도가 C3의 제거를 되돌리지 않는다 [DS-4 R1] ({o['status']})")
            else:
                chk(o["status"] == "pushed" and "l3-v2" in t and "l9-local" in t,
                    f"push 경합 재시도에 거짓 충돌 없음 [DS-4 R2] ({o['status']} {o.get('error', '')[:60]})")
        return run

    def t_dir_path():
        bare, local, cloud = setup("dirpath", {"data/app/tasks.json": "{}\n", "data/app/stocks.json": "{}\n"})
        wr(os.path.join(local, "data/app/tasks.json"), '{"mine":1}\n')
        wr(os.path.join(local, "data/app/stocks.json"), '{"OTHER SESSION WIP":1}\n')
        wr(os.path.join(local, "data/app/scratch_other.json"), "{}\n")
        before = sh(bare, "rev-parse", "main").strip()
        o = gs.publish(local, ["data/app"], "dir pathspec")
        chk(o["status"] not in ("pushed", "nochange") and sh(bare, "rev-parse", "main").strip() == before,
            f"디렉터리 경로는 거부 [DS-13] ({o['status']} {o.get('error', '')[:50]})")

    def t_detached():
        bare, local, cloud = setup("detached", {"A.txt": L, "C.txt": "c\n"})
        cloud_commit(cloud, {"A.txt": L.replace("l2\n", "l2-cloud\n")})
        sh(local, "checkout", "-q", "--detach")
        wr(os.path.join(local, "A.txt"), L.replace("l9\n", "l9-local\n"))
        o = gs.publish(local, ["A.txt"], "detached publish")
        a = rd(os.path.join(local, "A.txt"))
        chk(o["status"] == "pushed" and "l2-cloud" not in a,
            f"로컬이 못 따라가면 업스트림 내용을 옛 HEAD 위 워킹트리에 쓰지 않는다 [DS-14] ({o['status']} {o['local']})")

    # ── 분류 ─────────────────────────────────────────────────────────────────────
    def t_untracked_collision():
        bare, local, cloud = setup("collide", {"A.txt": "a\n"})
        cloud_commit(cloud, {"cache": "upstream file\n", "notes/x.md": "x\n"})
        wr(os.path.join(local, "cache", "frame1.jpg"), "jpg")
        wr(os.path.join(local, "notes"), "my notes (untracked)\n")
        o = gs.sync_checkout(local)
        chk(os.path.isfile(os.path.join(local, "cache", "frame1.jpg")), f"미추적 디렉터리를 지우지 않는다 [DS-5 T1] ({o['local']})")
        chk(os.path.isfile(os.path.join(local, "notes")) and rd(os.path.join(local, "notes")).startswith("my notes"),
            "미추적 파일을 디렉터리로 바꾸지 않는다 [DS-5 T2]")

    def t_toctou(kind):
        def run():
            if kind == "clean":
                bare, local, cloud = setup("toctou_c", {"E.txt": L})
                cloud_commit(cloud, {"E.txt": L.replace("l2\n", "l2-cloud\n")})
                fp, edit = os.path.join(local, "E.txt"), L.replace("l9\n", "l9-OTHER-SESSION-EDIT\n")
            else:
                bare, local, cloud = setup("toctou_m", {"A.txt": L})
                cloud_commit(cloud, {"A.txt": L.replace("l2\n", "l2-cloud\n")})
                fp = os.path.join(local, "A.txt")
                wr(fp, L.replace("l9\n", "l9-wip\n"))
                edit = L.replace("l9\n", "l9-wip\n") + "l11-LATEST-EDIT\n"
            sh(local, "fetch", "-q", "origin", "main")
            orig = gs._git
            fired = []

            def g(root, *a, **k):
                if not fired and ("--index-info" in a or "checkout" in a or "update-ref" in a):
                    fired.append(1)
                    wr(fp, edit)                       # 다른 세션이 분류 직후에 저장했다
                return orig(root, *a, **k)
            gs._git = g
            try:
                o = gs.sync_checkout(local, fetch=False)
            finally:
                gs._git = orig
            chk(rd(fp) == edit, f"분류 뒤 다른 세션의 저장을 덮지 않는다 [DS-6·K1-CONC-08 {kind}] ({o['local']} kept={o['kept_dirty']})")
        return run

    def t_case_rename():
        bare, local, cloud = setup("caserename", {"a.txt": "content\n", "B.txt": "b\n"})
        if gs._git(local, "config", "--bool", "core.ignorecase").stdout.strip() != "true":
            print("  (대소문자 구분 파일시스템 — 건너뜀)")
            return
        sh(cloud, "mv", "a.txt", "tmp.txt")
        sh(cloud, "mv", "tmp.txt", "A.txt")
        sh(cloud, "commit", "-q", "-m", "case rename")
        sh(cloud, "push", "-q", "origin", "main")
        o = gs.sync_checkout(local)
        names = os.listdir(local)
        st = sh(local, "status", "--porcelain").strip()
        chk("A.txt" in names and st == "", f"대소문자만 바뀐 이름: 파일이 남고 status 깨끗 [DS-8] ({o['local']} {names} {st!r})")

    def t_crlf():
        attrs = "* text=auto eol=lf\n"
        J = "".join(f'"k{i}": {i},\n' for i in range(1, 11))
        bare, local, cloud = setup("crlf", {"A.json": J}, attrs=attrs)
        cloud_commit(cloud, {"A.json": J.replace('"k2": 2', '"k2": 222')})
        wr(os.path.join(local, "A.json"), J.replace('"k9": 9', '"k9": 999'), nl="\r\n")
        o = gs.sync_checkout(local)
        a = rd(os.path.join(local, "A.json"))
        chk("A.json" in o["merged_dirty"] and '"k2": 222' in a and '"k9": 999' in a,
            f"CRLF 워킹트리도 줄 단위로 병합 [DS-9 E2] ({o['local']} merged={o['merged_dirty']} kept={o['kept_dirty']})")
        chk("\r\n" in a, "CRLF 워킹트리는 CRLF로 남긴다")
        bare, local, cloud = setup("crlf2", {"A.json": J}, attrs=attrs)
        cloud_commit(cloud, {"A.json": J.replace('"k2": 2', '"k2": 222')})
        wr(os.path.join(local, "A.json"), J.replace('"k9": 9', '"k9": 999'), nl="\r\n")
        o = gs.publish(local, ["A.json"], "crlf stale publish")
        t = sh(bare, "show", "main:A.json")
        chk(o["status"] == "pushed" and '"k2": 222' in t and '"k9": 999' in t,
            f"CRLF 옛 판 publish도 병합 [DS-9 E2b] ({o['status']})")

    def t_staged(kind):
        def run():
            bare, local, cloud = setup("staged_" + kind, {"A.txt": L})
            cloud_commit(cloud, {"A.txt": L.replace("l2\n", "l2-cloud\n")})
            sh(local, "fetch", "-q", "origin", "main")
            wr(os.path.join(local, "A.txt"), L.replace("l9\n", "l9-STAGED\n"))
            sh(local, "add", "A.txt")
            if kind == "S2":
                wr(os.path.join(local, "A.txt"), L)          # 워킹트리는 HEAD로 되돌림(staged만 남김)
            o = gs.sync_checkout(local, fetch=False)
            cached = sh(local, "diff", "--cached")
            chk("+l9-STAGED" in cached and "-l2-cloud" not in cached,
                f"staged 항목을 지키고 업스트림을 되돌리는 staged가 없다 [DS-12 {kind}] ({o['local']})")
        return run

    # ── 보존 기록 ────────────────────────────────────────────────────────────────
    def t_kept_corrupt(form):
        def run():
            bare, local, cloud = setup("keptbad_" + str(len(form)), {"A.txt": L})
            cloud_commit(cloud, {"A.txt": L.replace("l2\n", "l2-cloud-R3-item\n")})
            wr(os.path.join(local, "A.txt"), L.replace("l2\n", "l2-local\n"))
            gs.sync_checkout(local)
            kf = os.path.join(local, ".git", "git_sync_kept.json")
            if form == "half":
                s = open(kf, encoding="utf-8").read()
                open(kf, "w", encoding="utf-8").write(s[: len(s) // 2])
            else:
                open(kf, "w", encoding="utf-8").write(form)
            o = gs.sync_checkout(local, fetch=False)
            chk(os.path.exists(kf), f"손상된 보존 기록을 지우지 않는다 [DS-7 {form}] ({o.get('local')})")
            o = gs.publish(local, ["A.txt"], "after corrupt")
            chk(o["status"] != "pushed" and "l2-cloud-R3-item" in sh(bare, "show", "main:A.txt"),
                f"손상 시 publish 중단(되돌림 없음) [DS-7·K1-CONC-03·09 {form}] ({o['status']})")
            s = gs.status(local)
            chk(s.get("kept_corrupt") is True, "status가 kept_corrupt를 낸다")
        return run

    def t_kept_race():
        bare, local, cloud = setup("keptrace", {"A.txt": "a\n"})
        seen_empty, stop = [0], []
        big = {f"data/f{i}.json": "0" * 40 for i in range(200)}

        def writer():
            for _ in range(150):
                gs._save_kept(local, big)
            stop.append(1)

        def reader():
            while not stop:
                if gs.load_kept(local) == {}:
                    seen_empty[0] += 1
        gs._save_kept(local, big)
        tw, tr = threading.Thread(target=writer), threading.Thread(target=reader)
        tr.start()
        tw.start()
        tw.join()
        tr.join()
        chk(seen_empty[0] == 0, f"쓰는 중에 읽어도 기록이 사라져 보이지 않는다(원자 쓰기) [K1-CONC-03] ({seen_empty[0]}회)")

    def t_resolved():
        bare, local, cloud = setup("resolved", {"A.txt": L})
        cloud_commit(cloud, {"A.txt": L.replace("l2\n", "l2-cloud\n").replace("l8\n", "l8-cloud\n")})
        wr(os.path.join(local, "A.txt"), L.replace("l2\n", "l2-local\n"))
        gs.sync_checkout(local)
        final = L.replace("l2\n", "l2-local-final\n").replace("l8\n", "l8-cloud\n")
        wr(os.path.join(local, "A.txt"), final)            # 손으로 합침(충돌 줄은 내 것으로)
        o1 = gs.publish(local, ["A.txt"], "try 1")
        r = gs.resolve_kept(local, ["A.txt"]) if hasattr(gs, "resolve_kept") else {"error": "없음"}
        o2 = gs.publish(local, ["A.txt"], "after resolve")
        chk(o1["status"] == "stale_conflict" and "--resolved" in o1.get("error", ""), "충돌 안내가 --resolved를 알려준다 [DS-10]")
        chk(not r.get("error") and o2["status"] == "pushed" and sh(bare, "show", "main:A.txt") == final,
            f"--resolved 뒤엔 손으로 합친 판이 올라간다 [DS-10] ({r.get('error')} {o2['status']})")

    # ── fetch · 동시성 ──────────────────────────────────────────────────────────
    def t_fetch_hang():
        import socket
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(8)
        port = srv.getsockname()[1]
        conns = []

        def serve():
            srv.settimeout(1.0)
            t_end = time.time() + 45
            while time.time() < t_end:
                try:
                    c, _ = srv.accept()
                    conns.append(c)                       # 받기만 하고 응답 안 함(반쯤 열린 연결)
                except OSError:
                    pass
            for c in conns:
                c.close()
            srv.close()
        th = threading.Thread(target=serve, daemon=True)
        th.start()
        bare, local, cloud = setup("hang", {"A.txt": "a\n"})
        sh(local, "remote", "set-url", "origin", f"http://127.0.0.1:{port}/repo.git")
        t0 = time.time()
        ok, err = gs._fetch(local, timeout=3)
        dt = time.time() - t0
        chk(not ok and dt < 15, f"응답 없는 원격 — fetch 3초 제한이 지켜진다 [K1-CONC-04·H1] ({dt:.1f}초 · {err[:50]})")
        chk("시간 초과" in err, "실패 원인 = 시간 초과로 분류 [PM-4]")

    def t_fetch_fail_kind():
        bare, local, cloud = setup("deadurl", {"A.txt": "a\n"})
        gs._fetch(local)
        before = gs.last_fetch_ok(local) if hasattr(gs, "last_fetch_ok") else "없음"
        sh(local, "remote", "set-url", "origin", "http://127.0.0.1:1/repo.git")
        o = gs.sync_checkout(local, fetch_timeout=10)
        chk("연결 실패" in (o.get("fetch") or ""), f"fetch 실패 원인 분류(연결 실패) [PM-4] ({(o.get('fetch') or '')[:70]})")
        after = gs.last_fetch_ok(local) if hasattr(gs, "last_fetch_ok") else "없음"
        chk(before != "없음" and after == before, "실패한 fetch는 '마지막 성공 fetch' 시각을 바꾸지 않는다 [K1-CONC-06]")

    def t_concurrent_publish():
        bare, local, cloud = setup("concpub", {"P0.txt": "0\n", "P1.txt": "1\n", "P2.txt": "2\n"})
        for i in range(3):
            wr(os.path.join(local, f"P{i}.txt"), f"{i} mine\n")
        script = os.path.join(tmp, "child.py")
        if not os.path.exists(script):
            with open(script, "w", encoding="utf-8") as f:
                f.write(_CHILD)
        ps = [subprocess.Popen([sys.executable, script, gs.__file__, "pub", local, "-", f"P{i}.txt"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
              for i in range(3)]
        sts = []
        for p in ps:
            out, _ = p.communicate(timeout=240)
            try:
                sts.append(json.loads(out.strip().splitlines()[-1])["status"])
            except Exception:  # noqa: BLE001
                sts.append("crash")
        ok_all = all(sh(bare, "show", f"main:P{i}.txt") == f"{i} mine\n" for i in range(3))
        chk(ok_all and sts.count("pushed") == 3, f"동시 publish 3건이 전부 올라간다(직렬화·fetch 경합 재시도) [K1-CONC-05] ({sts})")

    def t_tracking_rewind():
        bare, local, cloud = setup("rewind", {"data/app/tasks.json": "{}\n", "X.txt": "x\n"})
        wr(os.path.join(local, "data/app/tasks.json"), '{"mine":1}\n')
        orig = gs._git
        fired = []

        def g(root, *a, **k):
            r = orig(root, *a, **k)
            if a[:1] == ("push",) and r.returncode == 0 and not fired:
                fired.append(1)
                cloud_commit(cloud, {"X.txt": "x cloud\n"}, "cloud right after")
                gs._git = orig
                gs.sync_checkout(local)                  # 다른 실행이 그 사이 더 새 origin으로 ff했다
                gs._git = g
            return r
        gs._git = g
        try:
            o = gs.publish(local, ["data/app/tasks.json"], "tasks")
        finally:
            gs._git = orig
        s = gs.status(local)
        chk(s["ahead"] == 0 and not s["ahead_canon"] and sh(local, "rev-parse", "refs/remotes/origin/main").strip()
            == sh(bare, "rev-parse", "main").strip(),
            f"원격 추적 ref를 뒤로 감지 않고 거짓 '미푸시' 경고 없음 [K1-CONC-07] ({o['local']} ahead={s['ahead']})")

    def t_many_paths():
        files = {f"m/f{i:04d}_{'p' * 45}.txt": f"{i}\n" for i in range(700)}   # 명령줄 ≈ 38,000자 > 윈도우 32,767
        bare, local, cloud = setup("many", files)
        for p in files:
            wr(os.path.join(local, p), "changed\n")
        o = gs.publish(local, list(files), "many paths")
        chk(o["status"] == "pushed", f"경로 700개도 명령줄 한도 없이 [K1-CONC-10] ({o['status']} {o.get('error', '')[:60]})")

    def t_single_branch():
        bare, local, cloud = setup("single", {"A.txt": "a\n"})
        sh(cloud, "push", "-q", "origin", "main:claude/feat")
        sb = os.path.join(os.path.dirname(local), "sb")
        subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", "--single-branch", "-b", "claude/feat",
                        bare, sb], check=True, capture_output=True)
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
            sh(sb, "config", k, v)
        wr(os.path.join(sb, "A.txt"), "a sb\n")
        o = gs.publish(sb, ["A.txt"], "single-branch clone")
        chk(o["status"] == "pushed", f"단일 브랜치 클론에서도 origin/main을 받는다 [K1-CONC-11] ({o['status']} {o.get('error', '')!r})")

    try:
        case("①~⑩ 기본 시나리오", legacy)
        case("index.lock 보유 중 ff [DS-1·K1-CONC-01·PM-1]", t_index_lock_held)
        case("index.lock 곧 해제 [K1-CONC-01]", t_index_lock_released)
        for step, ids in (("git:reset", "DS-1b·K1-CONC-02·H1"), ("git:update-ref", "DS-11c"),
                          ("after_index_build", "PM-1"), ("mid_ops", "PM-1"), ("after_ops", "PM-1"),
                          ("after_lock", "PM-1"), ("after_ref", "K1-CONC-02·H1"), ("after_swap", "PM-1")):
            case(f"kill @ {step} [{ids}]", t_kill(step, ids))
        case("update-ref 경합 [DS-11d]", t_update_ref_race)
        case("업스트림 삭제 되살림 [DS-2]", t_resurrect)
        case("로컬 삭제 vs 업스트림 수정 [DS-3]", t_local_delete)
        case("push 경합 R1 [DS-4]", t_push_race("R1"))
        case("push 경합 R2 [DS-4]", t_push_race("R2"))
        case("디렉터리 경로 [DS-13]", t_dir_path)
        case("detached HEAD publish [DS-14]", t_detached)
        case("미추적 충돌 [DS-5]", t_untracked_collision)
        case("TOCTOU 깨끗한 파일 [DS-6 T4·K1-CONC-08]", t_toctou("clean"))
        case("TOCTOU 병합 파일 [DS-6 T5·K1-CONC-08]", t_toctou("merge"))
        case("대소문자 이름 변경 [DS-8]", t_case_rename)
        case("CRLF 병합 [DS-9]", t_crlf)
        case("staged S1 [DS-12]", t_staged("S1"))
        case("staged S2 [DS-12]", t_staged("S2"))
        for form in ("half", "null", "[]"):
            case(f"보존 기록 손상 {form} [DS-7·K1-CONC-03·09]", t_kept_corrupt(form))
        case("보존 기록 동시 쓰기 [K1-CONC-03]", t_kept_race)
        case("--resolved [DS-10]", t_resolved)
        case("fetch 무응답 [K1-CONC-04·H1]", t_fetch_hang)
        case("fetch 실패 분류 [PM-4·K1-CONC-06]", t_fetch_fail_kind)
        case("동시 publish [K1-CONC-05]", t_concurrent_publish)
        case("원격 추적 ref 되감기 [K1-CONC-07]", t_tracking_rewind)
        case("경로 700개 [K1-CONC-10]", t_many_paths)
        case("단일 브랜치 클론 [K1-CONC-11]", t_single_branch)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"git_sync selftest: {'PASS' if not fails else 'FAIL'} ({len(fails)} 실패)")
    for f in fails:
        print("  -", f)
    return 0 if not fails else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="내 파일만 origin/main 위 커밋으로 올리고 로컬 체크아웃을 안전하게 따라가게 한다")
    ap.add_argument("-m", "--message", help="커밋 메시지")
    ap.add_argument("--ff-only", action="store_true", help="올리지 않고 로컬 체크아웃만 origin/main으로 안전하게 이동")
    ap.add_argument("--no-fetch", action="store_true", help="fetch 생략(마지막으로 받은 origin 기준)")
    ap.add_argument("--fetch-timeout", type=float, default=120, help="fetch 제한 시간(초) — SessionStart 훅은 짧게")
    ap.add_argument("--lock-wait", type=float, default=None, help="다른 git_sync 실행을 기다릴 시간(초)")
    ap.add_argument("--status", action="store_true", help="읽기 전용: 뒤처짐·앞섬·보존 파일·최신 보고서 번호(fetch 안 함)")
    ap.add_argument("--resolved", action="store_true", help="손으로 합친 보존 파일(paths)의 기록을 지운다(다음 publish가 그대로 올린다)")
    ap.add_argument("--json", action="store_true", help="결과를 JSON 한 줄로 출력(훅·스크립트용)")
    ap.add_argument("--no-ff-local", action="store_true", help="푸시만 하고 로컬 체크아웃은 건드리지 않는다")
    ap.add_argument("--selftest", action="store_true", help="임시 저장소 시나리오 자가검증(오프라인)")
    ap.add_argument("paths", nargs="*", help="올릴 파일 경로(저장소 루트 기준 · 디렉터리 거부)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.status:
        s = status(ROOT)
        print(json.dumps(s, ensure_ascii=False) if a.json else
              f"{s['branch']} · 뒤처짐 {s['behind']}(봇 제외 {s['behind_nonbot']}) · 앞섬 {s['ahead']} · "
              f"보고서 로컬 v{s['local_latest']} / origin v{s['origin_latest']} · 보존 {len(s['kept'])}건"
              + (" · ⚠️ 보존 기록 손상" if s.get("kept_corrupt") else ""))
        return 0
    if a.resolved:
        if not a.paths:
            ap.error("--resolved에는 경로가 필요하다")
        r = resolve_kept(ROOT, a.paths, **({"lock_wait": a.lock_wait} if a.lock_wait is not None else {}))
        if a.json:
            print(json.dumps(r, ensure_ascii=False))
        else:
            if r.get("diff"):
                print(r["diff"])
            print(f"기록 해제 {r['resolved']}" + (f" · 기록 없음 {r['not_kept']}" if r["not_kept"] else "")
                  + (f" · ⚠️ {r['error']}" if r.get("error") else ""))
        return 0 if not r.get("error") else 1
    if a.ff_only:
        kw = {"lock_wait": a.lock_wait} if a.lock_wait is not None else {}
        o = sync_checkout(ROOT, fetch=not a.no_fetch, fetch_timeout=a.fetch_timeout, **kw)
        if a.json:
            print(json.dumps(o, ensure_ascii=False))
        else:
            print("로컬", o.get("branch") or "체크아웃", o["local"],
                  (f"· dirty 병합 {o['merged_dirty']}" if o.get("merged_dirty") else ""),
                  (f"· 보존 {o['kept_dirty']}" if o.get("kept_dirty") else ""),
                  (f"· {o['recovered']}" if o.get("recovered") else ""),
                  (f"· {o['fetch']}" if o.get("fetch") else ""))
        return 0 if o["local"] in ("ff", "already") else 1
    if not a.message or not a.paths:
        ap.error("-m 메시지와 경로가 필요하다")
    kw = {"lock_wait": a.lock_wait} if a.lock_wait is not None else {}
    o = publish(ROOT, a.paths, a.message, ff_local=not a.no_ff_local, **kw)
    print(json.dumps(o, ensure_ascii=False) if a.json else describe(o))
    return 0 if o["status"] in ("pushed", "nochange") else 1


if __name__ == "__main__":
    sys.exit(main())
