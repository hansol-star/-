#!/usr/bin/env python3
"""루틴 프롬프트 추출 — `docs/routines.md`의 코드블록이 곧 실행 프롬프트다.

★[9/1 경로 B] 무인 루틴을 로컬(작업 스케줄러)로 옮기면서 신설.
舊 웹 Routines는 프롬프트를 **앱에 복사해 붙여둔 사본**이 돌았다. 그래서
`docs/routines.md`가 "정본"이라고 적혀 있어도 **실제로 도는 것은 사본**이었고,
R1·R2·R3는 `http_api`로 만들어진 트리거라 에이전트가 고칠 수도 없었다(8/6 실측).
⇒ 문서를 고쳐도 루틴은 안 바뀌는 상태가 4개월 지속됐다.

로컬에선 런처가 **매 실행마다 이 파일을 통해 문서에서 직접 프롬프트를 읽는다.**
정본과 실행물이 같은 것이 된다 = 문서를 고치면 다음 실행부터 반영된다.
(그 대가로 문서가 깨지면 루틴이 깨진다 → `--check`가 5개 전부 뽑히는지 검사한다.)

사용:
  python3 routine_prompts.py --kind r2          # 프롬프트 본문을 stdout으로
  python3 routine_prompts.py --check            # 5종 전부 추출되는지 검사(exit 1 = 실패)
  python3 routine_prompts.py --list
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DOC = os.path.join(REPO, "docs", "routines.md")

# 루틴 키 → 문서의 섹션 제목 정규식
SECTIONS = {
    "r1":  r"^###\s*R1\.",
    "r2":  r"^###\s*R2\.",
    "r3":  r"^###\s*R3\.",
    "r4a": r"^###\s*R4\.",
    "r4b": r"^###\s*R4\.",
}

# R4는 코드블록 하나를 두 시각이 공유한다(문서 표 참조). 차이는 여기서 붙인다 —
# 8/27 개정 배경대로 R4a는 '또 막히면 억지 축약본 대신 R4b로 넘긴다'가 추가된다.
VARIANT = {
    "r4a": ("\n- 이 세션은 R4a(20:00)다. 여기서 **또 토큰에 막히면 억지로 축약본을 내지 말고 그대로 종료**한다 "
            "— 21:15 R4b가 다음 창에서 이어받는다(report_guard 마커가 판정한다)."),
    "r4b": ("\n- 이 세션은 R4b(21:15)다. **오늘의 마지막 기회**이므로 완주를 최우선으로 둔다 "
            "(품질 < 완주). 정훈 폰창(20:50) 밖이라 집행은 다음 폰창·예약주문으로 넘긴다."),
}


def extract(kind):
    if kind not in SECTIONS:
        raise SystemExit(f"알 수 없는 루틴: {kind} (가능: {', '.join(SECTIONS)})")
    if not os.path.exists(DOC):
        raise SystemExit(f"정본 문서 없음: {DOC}")
    lines = open(DOC, encoding="utf-8").read().split("\n")
    pat = re.compile(SECTIONS[kind])
    start = next((i for i, ln in enumerate(lines) if pat.match(ln)), None)
    if start is None:
        raise SystemExit(f"섹션을 못 찾음: {kind}")
    # 섹션 안의 첫 ``` 블록
    body, inside = [], False
    for ln in lines[start + 1:]:
        if ln.startswith("### ") or ln.startswith("## "):
            break                      # 다음 섹션까지 왔으면 블록이 없는 것
        if ln.strip().startswith("```"):
            if inside:
                break
            inside = True
            continue
        if inside:
            body.append(ln)
    if not body:
        raise SystemExit(f"{kind}: 코드블록을 못 찾음 — 문서 구조가 바뀌었다")
    return "\n".join(body).strip() + VARIANT.get(kind, "")


def main():
    ap = argparse.ArgumentParser(description="docs/routines.md에서 루틴 프롬프트를 추출한다")
    ap.add_argument("--kind", help="r1 · r2 · r3 · r4a · r4b")
    ap.add_argument("--check", action="store_true", help="5종 전부 추출되는지 검사")
    ap.add_argument("--list", action="store_true", help="키 목록")
    ap.add_argument("--out", help="stdout 대신 이 파일에 UTF-8로 쓴다 "
                                  "(PowerShell 런처용 — 콘솔 코드페이지가 한글을 깨뜨리는 것 회피)")
    a = ap.parse_args()
    if a.list:
        print(" ".join(SECTIONS))
        return
    if a.check:
        bad = []
        for k in SECTIONS:
            try:
                t = extract(k)
                n = len(t)
                # 너무 짧으면 문서가 깨진 것 — 실제 프롬프트는 전부 500자 이상이다
                print(f"{'OK ' if n > 500 else 'THIN'} {k}: {n}자")
                if n <= 500:
                    bad.append(k)
            except SystemExit as ex:
                print(f"FAIL {k}: {ex}")
                bad.append(k)
        if bad:
            print(f"\n🔴 추출 실패/빈약: {', '.join(bad)} — 런처가 이 루틴을 못 돌린다")
            sys.exit(1)
        print("\n✅ 5종 전부 추출 OK")
        return
    if not a.kind:
        ap.error("--kind 또는 --check 필요")
    text = extract(a.kind)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"{len(text)}")   # 런처가 길이만 읽는다
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
