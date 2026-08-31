#!/usr/bin/env python3
"""wiring_audit.py — 도구 배선 감사: '만들었는데 아무도 안 부르는' 스크립트를 잡는다

배경 [8/22 정훈 지시 "다양한 스킬이나 기능들 다 잘 사용되고 있는지"]:
  수동 감사에서 **`broker_reports.py`가 7/30부터 멀쩡히 돌고 있었는데(60일 89건 실측)
  어떤 데스크도 안 읽고 있었다**는 게 드러났다. CLAUDE.md가 *"증권사 리포트가 그 위에
  얹힌다"*고 선언까지 해둔 상태였다. `ma_board.py`(정훈 8/4 지시)도 같은 상태였다.
  = 8/12 교훈 **"쓰는 쪽과 읽는 쪽이 갈리면 데이터는 조용히 사라진다"**의 재현이고,
  8/2 **"오더북에 들어간 것만 집행된다"**의 도구 버전이다.
  ⇒ 이 감사를 사람의 기억이 아니라 **기계**가 매번 하게 만든다.

판정 ①**스크립트 단위**: 각 스크립트가 **호출처**(에이전트 md · 스킬 SKILL.md · routines.md ·
      다른 스크립트)에서 언급되는지 본다. 0이면 UNWIRED.
판정 ②**기능 단위** [8/24 신설]: 배선된 스크립트라도 **어떤 기능이 불리는지**까지 본다.
      ★[8/24 실사고] `trades.py --realized`(손익비)를 자동화했는데 지시층은 `--reconcile`(수량 대사)만
        부르고 있었다. 스크립트 단위로는 "6곳에서 불림 = 배선됨"이라 **이 감사가 못 잡았다.**
        = 8/12 *"쓰는 쪽과 읽는 쪽이 갈리면 데이터는 조용히 사라진다"* 가 도구 **내부**에서 재현된 것.
      ⇒ `store_true` 플래그(= 산출 모드)를 추출해, 스크립트명이 나온 줄 근처에서 그 플래그가
        불리는지 본다. 안 불리면 **기능 미배선**(INFO) — 게이트를 막지는 않되 목록으로 드러낸다.
      ⚠️ docs/·CLAUDE.md 언급은 호출처로 **안 친다** — 문서에 적혀 있다고 실행되지 않는다.
         (broker_reports가 정확히 그 함정이었다: 문서 8곳·CLAUDE.md 1곳, 호출처 0곳.)

EXPECTED_UNWIRED = 배선이 없는 게 **정상**인 것들(일회성 검정·백필·수동 유틸).
  여기 없는데 UNWIRED로 잡히면 둘 중 하나다 — 배선을 빠뜨렸거나, 이 목록에 등록해야 하거나.
  **아무 판단 없이 목록에 추가하지 말 것.** 등록은 "이건 상시로 안 불려도 된다"는 선언이다.

사용:
  python3 wiring_audit.py            # 표 + 요약
  python3 wiring_audit.py --strict   # UNWIRED가 있으면 exit 1 (selfcheck 게이트용)
  python3 wiring_audit.py --json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", ".."))
SC = os.path.join(ROOT, ".claude", "skills", "portfolio-desk", "scripts")

# 배선 없는 게 정상인 것 — 이유를 반드시 적는다(적을 이유가 없으면 배선이 필요한 것이다)
EXPECTED_UNWIRED = {
    "local_doctor.py":            "이전 프리플라이트 — 새 기계 첫 세션에 사람이 1회 돌리는 수동 유틸(8/31). "
                                  "네트워크를 안 쓰고 어떤 산출물도 안 만들어서 데스크가 읽을 것이 없다. "
                                  "정본 = docs/local_migration.md §2d 0단계",
    "frr_validate.py":            "일회성 검정 — 외국인 지분율 프록시 품질(7/22)",
    "guard_selftest.py":          "메타 가드 — selfcheck가 6단계로 직접 호출(8/24). "
                                  "가드를 검증하는 도구라 데스크가 읽을 산출물이 아니다",
    "split_guard.py":             "가드 라이브러리 — financials가 채점 제외에 직접 쓰고 "
                                  "validate_report가 WARN으로 표면화(8/24). 데스크가 읽을 산출물이 아니다",
    "lookahead_guard.py":         "dev 게이트 도구 — selfcheck가 5단계로 직접 호출(8/24). "
                                  "데스크가 아니라 커밋 전 게이트가 부르는 층위라 지시층 배선이 없는 게 정상",
    "ma_test.py":                 "일회성 검정 — 이평 배열의 조건부 기저율(8/4)",
    "sizing_backtest.py":         "일회성 백테스트 — vol_sizing 감산 검증(7/21, 결과: 감산 폐기)",
    "snapshot_state_backfill.py": "일회성 백필 — 과거 스냅샷 소급 태깅(7/21)",
    "multiple_backtest.py":       "주기적 검증 — 목표가 배수 역사 검정(self-review 재량)",
    "star_validate.py":           "주기적 검증 — 별점 예측력 재검정(self-review 재량)",
    "export_financials_xlsx.py":  "수동 유틸 — 정훈이 엑셀로 요청할 때만",
    "read_doc.py":                "수동 유틸 — 정훈이 PDF·문서를 줄 때만",
    "short_borrow.py":            "⏸️ KRX가 데이터센터 IP 차단 — 로컬 이전 후 배선(8/22 재확인)",
    "wiring_audit.py":            "이 감사 도구 자신",
    # ── 라이브러리: 데스크가 직접 부르지 않고 다른 스크립트가 import 한다 ──
    "cli_common.py":              "라이브러리 — 22개 스크립트 공용 CLI/포맷",
    "ta_core.py":                 "라이브러리 — 기술지표 코어(chart_read·naver_chart가 import)",
    "value_core.py":              "라이브러리 — 선반영 판정 코어(us_value·naver_value가 import)",
    "edgar_facts.py":             "라이브러리 — EDGAR XBRL 취득(financials·guidance 등이 import)",
    "yahoo_facts.py":             "라이브러리 — Yahoo 재무 취득(financials가 import)",
    "flow_edge.py":               "라이브러리 — 수급 엣지 계산(naver_chart가 import)",
    "web_shot.cjs":               "라이브러리 — web_shot.py가 부르는 Playwright 헬퍼",
    "browser_captions.cjs":       "라이브러리 — hunter_latest가 부르는 자막 폴백 헬퍼",
    "ratchet_test.py":            "일회성 검정 — RESET vs 래칫(7/31, 결과: RESET 채택)",
    "selfcheck.py":               "dev 세션의 상위 게이트 — 사람이 직접 부른다(CLAUDE.md 명시)",
}

# 기능 단위 감사에서 **제외**할 유틸 플래그 — 산출 모드가 아니라 형식·편의다
UTIL_FLAGS = {
    "--json", "--save", "--help", "--dry-run", "--force", "--verbose", "--quiet",
    "--debug", "--all", "--strict", "--refresh", "--append", "--backfill", "--selftest",
    "--negative", "--no-network", "--coverage", "--features", "--full", "--pooled",
}

# "이 기능은 상시로 안 불려도 정상" — 이유를 반드시 적는다(EXPECTED_UNWIRED와 같은 문법)
EXPECTED_UNUSED_FEATURES = {
    ("trades.py", "--add"):          "체결 기입 — 정훈이 체결을 알릴 때만 사람이 실행",
    ("decisions.py", "--add"):       "결정 등재 — 세션 중 PM이 판단해 실행",
    ("wiring_audit.py", "--strict"): "게이트용 종료코드 모드 — selfcheck가 내부적으로 판단",
    ("toss_snapshot.py", "--raw"):   "디버그 출력",
    ("toss_snapshot.py", "--insecure"): "TLS 우회 — 평시 금지",
    ("api_health.py", "--quick"):    "빠른 모드 — 기본 실행이 정본",
    ("broker_reports.py", "--keep-pdf"): "PDF 보존 — 디스크 절약상 평시 미사용",
    ("build_dashboard.py", "--no-vol"): "부분 렌더 옵션",
    ("chart_read.py", "--index-only"): "지수만 — 기본 실행이 종목 포함 정본",
    ("capitulation_validate.py", "--naver"): "검증 경로 선택 — 일회성 검정(7/30) 내부 옵션",
    ("capitulation_validate.py", "--vix"):   "검증 경로 선택 — 일회성 검정(7/30) 내부 옵션",
    ("edgar_search.py", "--routine"): "루틴 프리셋 — 데스크가 --q/--events를 직접 쓴다",
}

CALLER_GLOBS = [
    ".claude/agents/*.md",
    ".claude/skills/*/SKILL.md",
    "docs/routines.md",
    "docs/desk_playbook.md",   # 전 데스크가 Task 0에서 읽는 공통 지침 = 지시층
]


def _features_of(path: str) -> list[str]:
    """스크립트가 제공하는 **산출 모드** 플래그(store_true)를 정적 추출한다.

    `--help`를 실행하지 않고 소스에서 뽑는다 — 네트워크·부작용 없이 결정적이어야 하고,
    selfcheck가 이미 `--help`를 따로 검증하기 때문이다.
    """
    try:
        src = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return []
    feats = []
    # add_argument("--foo", action="store_true", ...) / sub.add_argument('--foo', ..., action='store_true')
    for m in re.finditer(r"""add_argument\(\s*["'](--[a-z0-9][a-z0-9\-]*)["'][^)]*?action\s*=\s*["']store_true["']""",
                         src, re.S):
        f = m.group(1)
        if f not in UTIL_FLAGS and f not in feats:
            feats.append(f)
    return feats


def _feature_used(flag: str, basename: str, instr_pool) -> list[str]:
    """지시층에서 그 스크립트와 **같은 줄 또는 3줄 이내**에 플래그가 등장하는가.

    파일 전체에서 플래그만 찾으면 다른 스크립트의 동명 플래그와 섞인다 → 근접성을 본다.
    """
    hits = []
    for f, text in instr_pool:
        lines = text.splitlines()
        for i, ln in enumerate(lines):
            if basename in ln:
                window = "\n".join(lines[i:i + 4])
                if re.search(rf"{re.escape(flag)}(?:\s|$|[|`'\"])", window):
                    hits.append(os.path.relpath(f, ROOT))
                    break
    return hits


def scan() -> list[dict]:
    """호출처를 **두 층으로 갈라** 센다.

    ★[8/22 음성테스트로 발견한 설계 오류] 초판은 두 층을 한 바구니에 세었다. 그랬더니
      `broker_reports.py`가 **다른 스크립트에 이름이 있다는 이유로 '배선됨'**이 되어,
      정작 오늘 발견한 진짜 구멍(어떤 데스크도 안 읽음)을 0건으로 보고했다.
      = "메타 성공 ≠ 생존"(8/22)의 이 도구 안에서의 재현.
    ⇒ **지시층(에이전트·스킬·루틴 = 에이전트가 읽고 실행하는 문서)이 0이면 UNWIRED**다.
      코드층 참조는 그 도구가 라이브러리로 쓰인다는 뜻일 뿐, 데스크가 그 산출물을
      본다는 보장이 전혀 아니다.
    """
    scripts = sorted(glob.glob(os.path.join(SC, "*.py")) + glob.glob(os.path.join(SC, "*.cjs")))

    def load(paths):
        out = []
        for f in paths:
            try:
                out.append((os.path.abspath(f), open(f, encoding="utf-8", errors="ignore").read()))
            except OSError:
                pass
        return out

    instr_files = []
    for g in CALLER_GLOBS:
        instr_files += glob.glob(os.path.join(ROOT, g))
    instr = load(instr_files)
    # selfcheck는 전 스크립트를 기계적으로 도니 코드층에서 뺀다(안 빼면 전부 '배선됨'이 된다)
    code = load([p for p in scripts if os.path.basename(p) != "selfcheck.py"])

    out = []
    for path in scripts:
        b = os.path.basename(path)
        stem = b.rsplit(".", 1)[0]
        pats = [
            re.compile(rf"(?:python3?\s+\S*|/|^|['\"`\s]){re.escape(b)}\b"),
            re.compile(rf"^\s*(?:from|import)\s+{re.escape(stem)}\b", re.M),
            re.compile(rf"import\s+{re.escape(stem)}\s+as\b"),
            re.compile(rf"\bnode\s+\S*{re.escape(b)}\b"),
            re.compile(rf"{re.escape(stem.upper())}_SCRIPT\b"),
        ]

        def count(pool):
            hits = []
            for f, t in pool:
                if f == os.path.abspath(path):
                    continue
                if any(p.search(t) for p in pats):
                    hits.append(os.path.relpath(f, ROOT))
            return hits

        ih, ch = count(instr), count(code)
        # 기능 단위 — 지시층에 배선된 스크립트에 한해 본다
        # (미배선 스크립트는 이미 UNWIRED로 잡히므로 기능을 따질 단계가 아니다)
        feats, unused = _features_of(path), []
        if ih:
            for fl in feats:
                if (b, fl) in EXPECTED_UNUSED_FEATURES:
                    continue
                if not _feature_used(fl, b, instr):
                    unused.append(fl)
        out.append({"script": b, "instr": len(ih), "code": len(ch),
                    "by": ih[:4], "expected": b in EXPECTED_UNWIRED,
                    "note": EXPECTED_UNWIRED.get(b, ""),
                    "features": feats, "unused_features": unused})
    return out


def selftest() -> int:
    """음성 테스트 — 배선을 걷어낸 상태를 **메모리에서** 만들어 잡히는지 본다.

    ⚠️ 실제 파일을 수정했다 원복하는 방식은 쓰지 않는다 — 실패하면 지시층 문서가 깨진다.
       `_feature_used`가 pool을 인자로 받으므로 **가짜 지시층**을 넘기면 부작용 없이 검증된다.

    ★[8/24] 이 테스트의 첫 시도가 **실패했는데 도구가 아니라 테스트가 틀렸다** — 손익비를
      risk-desk·desk_playbook·self-review **3곳**에 배선해 뒀는데 한 곳만 지우고 "못 잡는다"고
      판정했다. *가드가 낸 첫 위반은 가드 자신일 수 있다*(lookahead_guard 픽스처 버그)의 변형:
      **음성 테스트 실패도 도구 결함이 아니라 테스트 설계 결함일 수 있다.**
    """
    print("wiring_audit 음성 테스트 — 걷어낸 배선을 잡아내면 성공")
    print("=" * 74)
    ok = True
    W = "python3 .claude/skills/portfolio-desk/scripts/trades.py --realized | tail -8"
    WO = "python3 .claude/skills/portfolio-desk/scripts/trades.py --reconcile"

    used = _feature_used("--realized", "trades.py", [("/fake/a.md", W)])
    print(f"  {'✅' if used else '❌'} 배선된 기능을 사용중으로 인식")
    ok = ok and bool(used)

    unused = _feature_used("--realized", "trades.py", [("/fake/a.md", WO)])
    print(f"  {'✅' if not unused else '❌'} 배선 없는 기능을 미사용으로 적발"
          + ("" if not unused else " ← 감사가 무력하다"))
    ok = ok and not unused

    # 근접성 규율 — 다른 스크립트 줄에 붙은 동명 플래그를 오인하지 않는가
    other = _feature_used("--realized", "trades.py",
                          [("/fake/b.md", "python3 other_tool.py --realized\n\n\n\n\npython3 trades.py --reconcile")])
    print(f"  {'✅' if not other else '❌'} 다른 스크립트의 동명 플래그를 오인하지 않음")
    ok = ok and not other

    # 스크립트 단위 축이 여전히 살아 있는가(기능 축 추가로 깨지지 않았는지)
    rows = scan()
    real_unwired = [r for r in rows if r["instr"] == 0 and not r["expected"]]
    print(f"  {'✅' if isinstance(rows, list) and rows else '❌'} 스크립트 단위 스캔 정상"
          f" (스크립트 {len(rows)}개 · 미배선 {len(real_unwired)})")
    ok = ok and bool(rows)

    print("-" * 74)
    print("✅ 통과 — 기능 단위 감사가 실제로 작동한다" if ok else "❌ 실패 — wiring_audit를 고칠 것")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="도구 배선 감사 (호출처 없는 스크립트 검출)")
    ap.add_argument("--selftest", action="store_true",
                    help="음성 테스트 — 배선을 걷어낸 상태를 만들어 잡히는지 확인")
    ap.add_argument("--features", action="store_true",
                    help="기능 단위 미배선 상세 (스크립트는 불리는데 그 기능은 안 불리는 것)")
    ap.add_argument("--strict", action="store_true",
                    help="예상 밖 UNWIRED가 있으면 exit 1 (selfcheck 게이트용)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    rows = scan()
    unwired = [r for r in rows if r["instr"] == 0 and not r["expected"]]
    parked = [r for r in rows if r["instr"] == 0 and r["expected"]]
    thin = [r for r in rows if r["instr"] == 1 and not r["expected"]]

    if a.json:
        print(json.dumps({"unwired": unwired, "parked": parked, "thin": thin,
                          "total": len(rows)}, ensure_ascii=False, indent=1))
        return 1 if (a.strict and unwired) else 0

    print("=" * 78)
    print(f"  도구 배선 감사 — 스크립트 {len(rows)}개 (판정 = **지시층**: 에이전트·스킬·루틴)")
    print("=" * 78)
    if unwired:
        print(f"\n🔴 배선 없음 {len(unwired)}건 — 만들었는데 아무도 안 부른다")
        for r in unwired:
            lib = f" (코드층 {r['code']}곳에서 import — 라이브러리로는 쓰이나 " \
                  f"**데스크가 산출물을 안 읽는다**)" if r["code"] else ""
            print(f"   {r['script']}{lib}")
        print("   → 담당 데스크/스킬/루틴에 연결하거나, 상시 호출이 불필요하면")
        print("     wiring_audit.py의 EXPECTED_UNWIRED에 **이유와 함께** 등록할 것.")
    else:
        print("\n✅ 배선 없는 스크립트 없음")
    if thin:
        print(f"\n🟡 호출처 1곳 {len(thin)}건 — 그 한 곳이 사라지면 같이 죽는다")
        print("   " + ", ".join(r["script"] for r in thin))
    if parked:
        print(f"\n⏸️  의도적 미배선 {len(parked)}건")
        for r in parked:
            print(f"   {r['script']:<28} {r['note']}")
    # ── 기능 단위 [8/24 신설] — 스크립트는 불리는데 그 **기능**은 안 불리는 것
    feat_rows = [r for r in rows if r["unused_features"]]
    n_feat = sum(len(r["unused_features"]) for r in feat_rows)
    if a.features and feat_rows:
        print(f"\n🟡 기능 미배선 {n_feat}건 — 스크립트는 불리는데 이 산출 모드는 아무도 안 쓴다")
        for r in sorted(feat_rows, key=lambda x: -len(x["unused_features"])):
            print(f"   {r['script']:<26} {' '.join(r['unused_features'])}")
        print("   → 지시층(데스크·스킬·루틴)에 연결하거나, 상시 호출이 불필요하면")
        print("     wiring_audit.EXPECTED_UNUSED_FEATURES에 **이유와 함께** 등록한다.")
        print("   ⚠️ 8/24 실사고: trades.py는 6곳에서 불려 '배선됨'이었는데 --realized(손익비)는")
        print("      아무도 안 읽고 있었다. 스크립트 단위 감사로는 구조적으로 못 잡는 형태다.")

    print(f"\n요약: 배선됨 {len(rows)-len(unwired)-len(parked)} · "
          f"미배선(예상밖) {len(unwired)} · 의도적 미배선 {len(parked)} · "
          f"**기능 미배선 {n_feat}**" + ("" if a.features else " (--features로 상세)"))
    return 1 if (a.strict and unwired) else 0


if __name__ == "__main__":
    sys.exit(main())
