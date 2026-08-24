#!/usr/bin/env python3
"""guard_selftest.py — **가드가 실제로 위반을 잡는지** 검증하는 메타 가드 (stdlib only)

■ 왜 필요한가 [8/24 정훈 지시 *"가드가 실제로 도는지 확인하는 절차도 만들어줘"*]

   같은 실패가 **세 번** 반복됐다. 전부 "가드는 초록불인데 실제로는 아무것도 안 잡던" 형태다:
     · 8/23 `check_repealed_rules` — **7주간 초록불**이었는데 손으로 찾아보니 폐기된 7,500 안전핀이
       세 군데에 현행처럼 살아 있었다. 원인은 룰이 아니라 탐지기의 사각(정규식 창 20자·스캔 목록 1개).
     · 8/24 `lookahead_guard` — 첫 실행의 위반 1건이 대상 코드가 아니라 **가드 자신의 픽스처 버그**였다.
     · 8/24 `split_guard` — `validate`를 오프라인으로 걸어 `high`가 **구조적으로 뜰 수 없는** 상태였다.

   ⇒ **초록불은 "위반이 없다"가 아니라 "탐지기가 그 형태를 안 본다"는 뜻일 수 있다.**
     그동안 우리는 이걸 매번 **손으로**(git stash로 위반을 되돌려 넣어) 확인했고, 그 확인은
     주석에만 남아 **재실행이 불가능**했다. 이 파일이 그 절차를 기계로 고정한다.

■ 방법 — 위반을 심고 잡히는지 본다 (mutation testing의 축소판)

   ① **서브프로세스형** — 자체 음성 테스트를 가진 가드는 그것을 실행한다.
   ② **주입형** — 임시 ROOT에 **위반 파일**을 만들고 `validate_report`의 check를 돌려
      기대한 FAIL/WARN이 나오는지 본다. 그리고 **정상 파일**로도 돌려 **오탐이 없는지** 본다.
      두 방향을 모두 봐야 한다 — 무조건 잡는 가드는 무조건 통과하는 가드만큼 쓸모없다.
      판정은 `expect_pattern` 정규식으로 한다(파일 부재 등 부수 실패에 흔들리지 않게).
   ③ **커버리지** — 음성 테스트가 **없는** 가드를 목록으로 드러낸다. 이게 결핍 목록이다.

■ ⚠️ 한계 (과장하지 않기)
   · 여기 통과 = "이 가드가 **이 형태의** 위반을 잡는다"일 뿐. 다른 형태의 사각은 여전히 있을 수 있다.
     8/23 사고가 정확히 그것이었다 — 한글 문구는 잡았지만 영문 서술은 못 잡았다.
   · 그래서 **새 사고가 나면 그 사례를 여기에 픽스처로 추가**하는 것이 이 파일의 사용법이다.
   · 커버리지 숫자를 성취로 읽지 말 것. 미등록 가드가 훨씬 많다.

사용:
  python3 guard_selftest.py            # 전체 (exit 1 = 가드가 무력)
  python3 guard_selftest.py --coverage # 커버리지 표만
  python3 guard_selftest.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


# ── ① 서브프로세스형 (자체 음성 테스트를 가진 가드) ─────────────────────
SUBPROCESS_TESTS = [
    ("lookahead_guard.py", ["--negative"], "룩어헤드 접두사 불변성 — 심어둔 미래참조 3종 적발"),
    ("split_guard.py", ["--selftest"], "분할 스케일 혼재 — 10배 왜곡 적발 + 오프라인 경로"),
]


def run_subprocess_tests() -> list[dict]:
    out = []
    for script, args, desc in SUBPROCESS_TESTS:
        p = os.path.join(HERE, script)
        if not os.path.exists(p):
            out.append({"guard": script, "ok": None, "desc": desc, "msg": "스크립트 없음"})
            continue
        try:
            r = subprocess.run([sys.executable, p] + args, capture_output=True,
                               text=True, timeout=180, cwd=REPO)
            ok = r.returncode == 0
            msg = "" if ok else (r.stdout or r.stderr or "")[-400:]
        except subprocess.TimeoutExpired:
            ok, msg = False, "timeout"
        out.append({"guard": f"{script} {' '.join(args)}", "ok": ok, "desc": desc, "msg": msg})
    return out


# ── ② 주입형 (임시 ROOT에 위반을 심는다) ────────────────────────────────
SAFE_CLAUDE = (
    "# CLAUDE.md\n\n"
    "- 최신 보고서 = `docs/reports/`에서 가장 높은 `report_v*.md`(현재 **v83**·2026-08-24).\n"
    "- 매수 안전핀: 낙폭 사다리(`tranche_rules.py`)로 판정한다. 하드플로어 = S&P500 폭풍 ≥70%ile.\n"
)
VIOLATING_CLAUDE = (
    "# CLAUDE.md\n\n"
    "- 최신 보고서 = `docs/reports/`에서 가장 높은 `report_v*.md`(현재 **v83**·2026-08-24).\n"
    "- **매수 안전핀 — 코스피 종가가 7,500을 하회하면 신규 매수 전면 동결(0원).**\n"
)

INJECTION_TESTS = [
    {
        "name": "check_repealed_rules",
        "desc": "폐기된 룰(7,500 안전핀)이 정본에 살아 있으면 잡는가",
        "why": "8/23 실사고 — 7주간 초록불인 채 세 군데에 현행처럼 살아 있었다",
        "pattern": r"7[,.]?500|안전핀|폐기",
        "violate": {"CLAUDE.md": VIOLATING_CLAUDE},
        "clean": {"CLAUDE.md": SAFE_CLAUDE},
        "args": (),
    },
    {
        "name": "check_versions",
        "desc": "정본(stocks.json)이 옛 보고서를 가리키면 stale로 잡는가",
        "why": "정본 stale은 앱·데스크가 옛 상태로 판단하게 만든다",
        "pattern": r"stale|source_report",
        "violate": {
            "docs/reports/report_v83_2026-08-24.md": "# v83\n",
            "data/app/stocks.json": json.dumps({"source_report": "report_v80_2026-08-21.md"}),
        },
        "clean": {
            "docs/reports/report_v83_2026-08-24.md": "# v83\n",
            "data/app/stocks.json": json.dumps({"source_report": "report_v83_2026-08-24.md"}),
        },
        "args": (83,),
    },
    {
        "name": "check_low_star_action",
        "desc": "⭐2 이하 보유가 '관망'으로 방치되면 잡는가",
        "why": "8/2 실사고 — 보고서 산문엔 트림이 8~9회 등장했는데 orders 등록은 0회였고, "
               "7주 손실의 68.7%가 그 두 종목(⭐2)에서 났다",
        "pattern": r"무결정 방치|관망",
        "violate": {
            "data/app/stocks.json": json.dumps(
                {"stocks": {"005380.KS": {"stars": 2, "trim": "관망"}}}, ensure_ascii=False),
            "data/app/tasks.json": json.dumps({"orders": []}),
        },
        "clean": {
            "data/app/stocks.json": json.dumps(
                {"stocks": {"005380.KS": {"stars": 2, "trim": "470,000원 1주 트림 지정가"}}},
                ensure_ascii=False),
            "data/app/tasks.json": json.dumps({"orders": [{"ticker": "005380.KS"}]}),
        },
        "args": (),
    },
]


def _make_root(files: dict[str, str]) -> str:
    tmp = tempfile.mkdtemp(prefix="guard_selftest_")
    for rel, body in files.items():
        p = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
    return tmp


def _run_check(check_name: str, files: dict, args: tuple) -> list[str]:
    """임시 ROOT에서 check 하나를 돌리고 FAIL+WARN 메시지를 돌려준다."""
    import validate_report as V
    tmp = _make_root(files)
    old_root = V.ROOT
    old_fails, old_warns = list(V.FAILS), list(V.WARNS)
    try:
        V.ROOT = tmp
        V.FAILS.clear()
        V.WARNS.clear()
        fn = getattr(V, check_name, None)
        if fn is None:
            return ["__MISSING__"]
        try:
            fn(*args)
        except Exception as e:                     # 가드가 죽는 것도 결함이다
            return [f"__EXCEPTION__ {type(e).__name__}: {e}"]
        return list(V.FAILS) + list(V.WARNS)
    finally:
        V.ROOT = old_root
        V.FAILS.clear(); V.FAILS.extend(old_fails)
        V.WARNS.clear(); V.WARNS.extend(old_warns)
        shutil.rmtree(tmp, ignore_errors=True)


def run_injection_tests() -> list[dict]:
    out = []
    for t in INJECTION_TESTS:
        rx = re.compile(t["pattern"])
        got_v = _run_check(t["name"], t["violate"], t["args"])
        got_c = _run_check(t["name"], t["clean"], t["args"])
        if got_v == ["__MISSING__"]:
            out.append({"guard": t["name"], "ok": None, "desc": t["desc"],
                        "msg": "validate_report에 해당 check 없음(이름 변경?)"})
            continue
        caught = any(rx.search(m) for m in got_v)
        false_pos = any(rx.search(m) for m in got_c)
        ok = caught and not false_pos
        msg = ""
        if not caught:
            msg = "위반을 심었는데 못 잡는다 ← 가드가 무력하다"
        elif false_pos:
            msg = f"정상 데이터를 위반으로 오판: {[m for m in got_c if rx.search(m)][:1]}"
        out.append({"guard": t["name"], "ok": ok, "desc": t["desc"], "why": t["why"],
                    "caught": caught, "false_positive": false_pos, "msg": msg})
    return out


# ── ③ 커버리지 — 음성 테스트가 없는 가드를 드러낸다 ──────────────────────
def coverage() -> dict:
    try:
        import validate_report as V
    except Exception:
        return {"checks": [], "covered": [], "uncovered": []}
    checks = sorted(n for n in dir(V) if n.startswith("check_") and callable(getattr(V, n)))
    covered = {t["name"] for t in INJECTION_TESTS}
    return {"checks": checks, "covered": sorted(covered),
            "uncovered": [c for c in checks if c not in covered]}


def selftest() -> int:
    """이 메타 가드 자신을 검증한다 — **무력한 가드를 실제로 ❌로 잡는가.**

    ★ 이 단계가 없으면 `guard_selftest` 자신이 정확히 그 세 번째 사례가 된다
      ("돌지만 아무것도 못 잡는 도구"). 무력화 두 종류를 주입한다:
        ① **아무것도 안 잡는 가드**(no-op) → ❌ 여야 한다
        ② **무조건 잡는 가드**(항상 fail) → 정상 데이터에서도 걸리므로 ❌ 여야 한다
      ②가 중요하다 — 무조건 잡는 가드는 무조건 통과하는 가드만큼 쓸모없는데,
      '위반을 잡았는가'만 보면 통과해버린다.
    """
    import validate_report as V
    print("guard_selftest 음성 테스트 — 무력한 가드를 ❌로 잡아내면 성공")
    print("=" * 78)
    ok = True

    target = INJECTION_TESTS[0]["name"]          # check_repealed_rules
    orig = getattr(V, target)

    # ① no-op — 위반을 심어도 아무 말이 없다
    setattr(V, target, lambda *a, **k: None)
    r = [x for x in run_injection_tests() if x["guard"] == target][0]
    caught_noop = r["ok"] is False and not r["caught"]
    print(f"  {'✅' if caught_noop else '❌'} 아무것도 안 잡는 가드(no-op)를 적발"
          + ("" if caught_noop else " ← 메타 가드가 무력하다"))
    ok = ok and caught_noop

    # ② 무조건 fail — 정상 데이터에서도 걸린다
    setattr(V, target, lambda *a, **k: V.fail("7,500 안전핀 위반 (무조건)"))
    r = [x for x in run_injection_tests() if x["guard"] == target][0]
    caught_always = r["ok"] is False and r["false_positive"]
    print(f"  {'✅' if caught_always else '❌'} 무조건 잡는 가드(오탐)를 적발"
          + ("" if caught_always else " ← 위반 적발만 보고 오탐을 놓쳤다"))
    ok = ok and caught_always

    # ③ 원복 후 정상 통과 확인
    setattr(V, target, orig)
    r = [x for x in run_injection_tests() if x["guard"] == target][0]
    print(f"  {'✅' if r['ok'] else '❌'} 원복 후 정상 통과")
    ok = ok and bool(r["ok"])

    # ④ 가드가 예외로 죽으면 그것도 결함으로 잡는가
    setattr(V, target, lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = [x for x in run_injection_tests() if x["guard"] == target][0]
    caught_exc = r["ok"] is False
    print(f"  {'✅' if caught_exc else '❌'} 예외로 죽는 가드를 적발")
    ok = ok and caught_exc
    setattr(V, target, orig)

    print("-" * 78)
    print("✅ 통과 — 메타 가드가 실제로 작동한다" if ok else "❌ 실패 — guard_selftest를 고칠 것")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="가드가 실제로 위반을 잡는지 검증하는 메타 가드")
    ap.add_argument("--coverage", action="store_true", help="커버리지 표만 출력")
    ap.add_argument("--selftest", action="store_true",
                    help="이 메타 가드 자신을 검증(무력한 가드를 잡는지)")
    ap.add_argument("--json", action="store_true", help="기계 출력")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    cov = coverage()
    if a.coverage and not a.json:
        print("가드 음성테스트 커버리지 — validate_report.check_*")
        print("=" * 78)
        for c in cov["checks"]:
            mark = "✅ 음성테스트 있음" if c in cov["covered"] else "· 미등록"
            print(f"  {mark:<20} {c}")
        print("-" * 78)
        print(f"  {len(cov['covered'])}/{len(cov['checks'])} 등록 — **미등록 {len(cov['uncovered'])}개가 결핍 목록이다**")
        print("  ⚠️ 커버리지를 성취로 읽지 말 것. 새 사고가 나면 그 사례를 INJECTION_TESTS에 추가한다.")
        return 0

    subs = run_subprocess_tests()
    injs = run_injection_tests()
    rows = subs + injs
    fails = [r for r in rows if r["ok"] is False]

    if a.json:
        print(json.dumps({"results": rows, "coverage": cov,
                          "failed": len(fails)}, ensure_ascii=False, indent=1))
        return 1 if fails else 0

    print("가드 자가검증 — 위반을 심고 **실제로 잡는지** 본다")
    print("=" * 78)
    print("\n■ 자체 음성 테스트를 가진 가드")
    for r in subs:
        icon = "·" if r["ok"] is None else ("✅" if r["ok"] else "❌")
        print(f"  {icon} {r['guard']}")
        print(f"       {r['desc']}")
        if r["msg"]:
            print(f"       └ {r['msg']}")
    print("\n■ 주입 테스트 (임시 ROOT에 위반을 심는다)")
    for r in injs:
        icon = "·" if r["ok"] is None else ("✅" if r["ok"] else "❌")
        print(f"  {icon} {r['guard']} — {r['desc']}")
        if r.get("why"):
            print(f"       근거: {r['why']}")
        if r.get("ok") is not None:
            print(f"       위반 적발 {'O' if r['caught'] else 'X'} · 정상 오탐 "
                  f"{'있음' if r['false_positive'] else '없음'}")
        if r["msg"]:
            print(f"       └ {r['msg']}")

    print("\n" + "-" * 78)
    print(f"  커버리지: validate_report check {len(cov['checks'])}개 중 "
          f"주입 테스트 등록 **{len(cov['covered'])}개** · 미등록 {len(cov['uncovered'])}개")
    print("  ⚠️ 미등록이 훨씬 많다 — 이 숫자는 성취가 아니라 **결핍 목록**이다"
          " (`--coverage`로 전체 목록).")
    if fails:
        print(f"\n❌ 무력한 가드 {len(fails)}건 — 가드를 고칠 것(초록불이 거짓이 된다)")
        return 1
    print("\n✅ 등록된 가드 전부 실제로 위반을 잡는다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
