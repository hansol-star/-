#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selfcheck.py — 데스크 품질 게이트 (dev 작업 커밋·머지 전 스모크 테스트)

정본 스크립트(validate_report·build_app_data·market_data 등 21+개)를 수정한 뒤
"다 됐다" 선언 전에 돌리는 기계 게이트. 은근한 문법·임포트 깨짐이 정본 데이터를
망치는 걸 막는다. 표준 라이브러리만 사용(py_compile) — 포터블.

검사 단계:
  1) py_compile  — 모든 스크립트 문법 컴파일 (문법/들여쓰기 오류 적발)
  2) import      — 각 스크립트를 서브프로세스로 임포트(모듈 최상위 실행 오류 적발; 네트워크 미접속)
  3) --help      — argparse 파서 구성 검증 (1·2가 절대 안 건드리는 __main__ 안쪽)
  4) validate    — validate_report.py 실행(보고서/풀표/밴드/정본버전 게이트)

사용:
  python3 .claude/skills/portfolio-desk/scripts/selfcheck.py
  python3 .claude/skills/portfolio-desk/scripts/selfcheck.py --no-validate   # 1~3만
  python3 .claude/skills/portfolio-desk/scripts/selfcheck.py --json

종료코드: 0=전부 통과, 1=하나라도 실패. (커밋/머지 전 이게 0인지 확인.)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import py_compile
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))  # .claude/skills/portfolio-desk/scripts → repo root


def discover_scripts() -> list[str]:
    """.claude/skills/*/scripts/ 아래 모든 .py (selfcheck 자신 제외)."""
    pat = os.path.join(REPO, ".claude", "skills", "*", "scripts", "*.py")
    found = sorted(glob.glob(pat))
    return [p for p in found if os.path.basename(p) != "selfcheck.py"]


def check_compile(path: str) -> tuple[bool, str]:
    try:
        py_compile.compile(path, doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e).strip().splitlines()[-1][:200]


def check_import(path: str, timeout: float = 20.0) -> tuple[bool, str]:
    """모듈을 서브프로세스로 임포트해 최상위 실행(임포트·NameError 등) 오류를 잡는다.
    __main__ 가드 안쪽(argparse·네트워크)은 실행되지 않음 → 오프라인·부작용 없음."""
    name = os.path.splitext(os.path.basename(path))[0]
    script_dir = os.path.dirname(path)
    # 스크립트를 직접 실행하면 자기 폴더가 sys.path[0]에 들어간다(sibling import 해소).
    # 그 동작을 그대로 재현해야 `import market_data` 같은 형제 임포트를 오탐하지 않음.
    code = (
        "import importlib.util,sys;"
        f"sys.path.insert(0, {script_dir!r});"
        f"spec=importlib.util.spec_from_file_location({name!r}, {path!r});"
        "m=importlib.util.module_from_spec(spec);"
        "spec.loader.exec_module(m)"
    )
    try:
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, timeout=timeout, cwd=REPO)
    except subprocess.TimeoutExpired:
        return False, f"import timeout >{timeout:.0f}s (최상위에서 네트워크/블로킹?)"
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        return False, tail[:200]
    return True, ""


def has_argparse(path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as f:
            return "argparse" in f.read()
    except Exception:
        return False


def check_cli(path: str, timeout: float = 25.0) -> tuple[bool, str]:
    """`--help`를 실제로 실행해 argparse 정의 자체를 검증한다.

    왜 필요한가 — compile·import 단계는 `if __name__ == "__main__":` 안쪽을 절대
    실행하지 않는다. 그래서 파서를 만들 때만 터지는 결함(help 문자열의 미이스케이프
    `%`, 잘못된 type/choices/default)이 두 단계를 모두 통과해 정본에 남는다.
    실제로 2026-08-02에 dart_disclosure·history_analysis·naver_sentiment 3개가
    `--help`에서 ValueError/TypeError로 죽는 채로 게이트를 통과하고 있었다.

    --help는 파서 구성 직후 SystemExit(0)으로 끝나므로 네트워크·파일 부작용이 없다.
    argparse를 안 쓰는 스크립트는 `--help`가 무시되고 본문이 실행돼버리므로 제외한다.
    타임아웃 = parse_args() 앞에서 무거운 일을 한다는 뜻이라 그 자체가 결함이다.
    """
    if not has_argparse(path):
        return True, "(argparse 미사용 — 생략)"
    try:
        r = subprocess.run([sys.executable, path, "--help"], capture_output=True,
                           text=True, timeout=timeout, cwd=REPO)
    except subprocess.TimeoutExpired:
        return False, f"--help timeout >{timeout:.0f}s (parse_args 앞에서 네트워크/블로킹?)"
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        return False, tail[:200]
    return True, ""


def run_validate(timeout: float = 120.0) -> tuple[str, str]:
    vp = os.path.join(HERE, "validate_report.py")
    if not os.path.exists(vp):
        return "SKIP", "validate_report.py 없음"
    try:
        r = subprocess.run([sys.executable, vp], capture_output=True, text=True,
                           timeout=timeout, cwd=REPO)
    except subprocess.TimeoutExpired:
        return "FAIL", f"validate timeout >{timeout:.0f}s"
    status = "PASS" if r.returncode == 0 else "FAIL"
    return status, (r.stdout or r.stderr or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="데스크 품질 게이트 (커밋·머지 전 스모크)")
    ap.add_argument("--no-validate", action="store_true", help="validate_report 단계 생략")
    ap.add_argument("--no-import", action="store_true", help="import 단계 생략(문법만)")
    ap.add_argument("--no-cli", action="store_true", help="--help(argparse) 스모크 생략")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    args = ap.parse_args()

    scripts = discover_scripts()
    results = []
    for p in scripts:
        rel = os.path.relpath(p, REPO)
        ok_c, msg_c = check_compile(p)
        row = {"script": rel, "compile": ok_c, "compile_msg": msg_c,
               "import": None, "import_msg": "", "cli": None, "cli_msg": ""}
        if ok_c and not args.no_import:
            ok_i, msg_i = check_import(p)
            row["import"] = ok_i
            row["import_msg"] = msg_i
        if ok_c and not args.no_cli:
            ok_h, msg_h = check_cli(p)
            row["cli"] = ok_h
            row["cli_msg"] = msg_h
        results.append(row)

    val_status, val_out = ("SKIP", "") if args.no_validate else run_validate()

    def failed(r):
        return (not r["compile"]) or (r["import"] is False) or (r["cli"] is False)

    fails = [r for r in results if failed(r)]
    gate_ok = not fails and val_status in ("PASS", "SKIP")

    if args.json:
        print(json.dumps({"scripts": results, "validate": val_status,
                          "validate_out": val_out, "ok": gate_ok},
                         ensure_ascii=False, indent=2))
        return 0 if gate_ok else 1

    print(f"=== selfcheck: {len(scripts)}개 스크립트 ===")
    for r in results:
        c = "✅" if r["compile"] else "❌"
        i = "·" if r["import"] is None else ("✅" if r["import"] else "❌")
        h = "·" if r["cli"] is None else ("✅" if r["cli"] else "❌")
        mark = "" if not failed(r) else "  ← FAIL"
        print(f"  compile {c}  import {i}  --help {h}   {r['script']}{mark}")
        if not r["compile"]:
            print(f"        └ compile: {r['compile_msg']}")
        if r["import"] is False:
            print(f"        └ import:  {r['import_msg']}")
        if r["cli"] is False:
            print(f"        └ --help:  {r['cli_msg']}")

    if not args.no_validate:
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "·"}[val_status]
        print(f"\n=== validate_report: {icon} {val_status} ===")
        if val_status == "FAIL":
            print(val_out[-1500:])

    print("\n" + ("✅ GATE PASS — 커밋·머지 OK" if gate_ok
                  else f"❌ GATE FAIL — {len(fails)}개 스크립트 오류"
                       + ("" if val_status != "FAIL" else " + validate FAIL")))
    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
