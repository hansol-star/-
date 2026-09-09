#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
playbook.py — 데스크가 **자기에게 필요한 부분만** 읽게 하는 플레이북 추출기 (stdlib)

[왜 만들었나 — 2026-09-09 정훈 지시 "데스크 구조도 지금 해줘"]
주간 토큰 50% 소진의 원인을 실측했더니, 데스크 서브에이전트가 평균 **13만 토큰**인데
실제 작업은 3만 안팎이고 나머지가 **문서 로드**였다(risk 155,499 · kr 136,681 · us 128,804 …).

`docs/desk_playbook.md`는 31,994자인데 데스크가 전문을 읽는다. 그런데 구성을 뜯어보면:
    §1 공통 지침        4,608자   ← 전 데스크가 필요 ✅
    §2 캘리브레이션    11,660자   ← **PM·self-review용**. 시계열 누적이라 6~7월분이 대부분
    §3 데스크별        14,587자   ← **자기 블록은 평균 1,450자**. 나머지 13,000자는 남의 것
    §4 유지 규약          765자   ← 필요 ✅
즉 **데스크 하나가 실제로 쓰는 건 6,000자 남짓인데 32,000자를 읽고 있었다.**
남는 26,000자 × 데스크 7개 = 약 18만 자가 매 보고서마다 버려진다.

⇒ 이 스크립트가 `--desk <name>`으로 **§1 + §2 최신 요약 + 자기 §3 + §4**만 조립해 준다.

⚠️ **정본은 여전히 `docs/desk_playbook.md`다.** 이건 뷰(view)일 뿐이고, 갱신은 원문에 한다
   (§4 지속 학습 루프 그대로). 두 벌로 두면 반드시 갈라진다.
⚠️ **§2를 통째로 버리지 않는다** — 최신 2건은 전문, 나머지는 헤드라인으로 남긴다.
   캘리브레이션 교훈이 사라지면 데스크가 같은 편향을 반복한다(그게 §2가 생긴 이유다).
⚠️ 구조가 깨지면 **조용히 빈 결과를 주지 않는다** — 섹션을 못 찾으면 전문으로 폴백하고
   그 사실을 stderr에 남긴다(8/22 "가드 없는 폴백은 침묵보다 나쁘다").
"""
from __future__ import annotations
import argparse
import os
import re
import sys

_HERE = os.path.abspath(__file__)
ROOT = os.path.abspath(os.path.join(_HERE, *([os.pardir] * 5)))
PB = os.path.join(ROOT, "docs", "desk_playbook.md")

DESKS = ["kr-market-desk", "us-market-desk", "macro-desk", "risk-desk", "research-feed",
         "semi-ai-desk", "power-physical-desk", "bigtech-platform-desk", "guru-flow-desk", "PM"]


def _sections(text: str) -> dict:
    """`## §N ...` 단위로 자른다. 키는 '1','2','3','4'."""
    out, marks = {}, [(m.start(), m.group(0)) for m in re.finditer(r"^##\s+§?(\d)\s.*$", text, re.M)]
    for i, (pos, head) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        num = re.search(r"§?(\d)", head).group(1)
        out[num] = text[pos:end].rstrip() + "\n"
    return out


def _desk_block(sec3: str, desk: str) -> str | None:
    """§3 안에서 `### <desk>` 블록만."""
    subs = [(m.start(), m.group(0)) for m in re.finditer(r"^###\s+.+$", sec3, re.M)]
    for i, (pos, head) in enumerate(subs):
        if desk.lower() in head.lower():
            end = subs[i + 1][0] if i + 1 < len(subs) else len(sec3)
            return sec3[pos:end].rstrip() + "\n"
    return None


def _calib_digest(sec2: str, keep_full: int) -> str:
    """§2 = 최신 keep_full건은 전문, 나머지는 헤드라인만.

    §2는 시계열 누적이라 6~7월 항목이 대부분인데, 데스크가 오늘 쓰는 건 최신 몇 건이다.
    그렇다고 통째로 버리면 같은 편향을 반복한다 — **헤드라인은 남긴다.**
    """
    items = [(m.start(), m.group(0)) for m in re.finditer(r"^-\s+\*\*.+?\*\*", sec2, re.M)]
    if not items:
        return sec2
    head = sec2[:items[0][0]].rstrip()
    full, brief = [], []
    for i, (pos, title) in enumerate(items):
        end = items[i + 1][0] if i + 1 < len(items) else len(sec2)
        (full if i < keep_full else brief).append(
            sec2[pos:end].rstrip() if i < keep_full else "  " + title.strip())
    out = [head, ""]
    out += full
    if brief:
        out += ["", f"<details><summary>이전 캘리브레이션 교훈 {len(brief)}건 (헤드라인 — "
                    f"전문은 `docs/desk_playbook.md` §2)</summary>", ""]
        out += brief
        out += ["", "</details>"]
    return "\n".join(out) + "\n"


def build(desk: str, keep_full: int = 2) -> tuple[str, dict]:
    try:
        raw = open(PB, encoding="utf-8").read()
    except OSError as e:
        print(f"[ERR] 플레이북 없음: {e}", file=sys.stderr)
        return "", {}
    secs = _sections(raw)
    if not {"1", "3"} <= set(secs):
        print("[warn] §1/§3을 못 찾았다 — **전문으로 폴백**한다(구조 변경 의심). "
              "`docs/desk_playbook.md` 헤딩 형식을 확인할 것.", file=sys.stderr)
        return raw, {"full": len(raw), "out": len(raw), "fallback": True}

    parts = [f"# 데스크 플레이북 — {desk} 전용 뷰",
             "",
             f"> ⚠️ **정본은 `docs/desk_playbook.md`다.** 이건 {desk}에게 필요한 부분만 뽑은 뷰이고,",
             "> 교훈 갱신은 **원문에** 한다(§4 지속 학습 루프). 두 벌로 두면 갈라진다.",
             "> 다른 데스크의 §3 블록과 §2 과거 항목은 생략됐다 — 필요하면 원문을 열 것.",
             ""]
    parts.append(secs["1"])
    if "2" in secs:
        parts.append(_calib_digest(secs["2"], keep_full))
    blk = _desk_block(secs["3"], desk)
    if blk:
        parts.append("## §3 이 데스크의 누적 교훈\n")
        parts.append(blk)
    else:
        parts.append(f"## §3 이 데스크의 누적 교훈\n\n(아직 없음 — {desk} 블록 미생성)\n")
    if "4" in secs:
        parts.append(secs["4"])
    out = "\n".join(parts)
    return out, {"full": len(raw), "out": len(out), "fallback": False}


def main() -> int:
    ap = argparse.ArgumentParser(description="데스크별 플레이북 뷰 (토큰 절감)")
    ap.add_argument("--desk", help="데스크 이름 (예: kr-market-desk)")
    ap.add_argument("--keep-full", type=int, default=2, help="§2 캘리브레이션 전문 유지 건수(기본 2)")
    ap.add_argument("--full", action="store_true", help="전문 그대로 출력")
    ap.add_argument("--stats", action="store_true", help="전 데스크 절감량만 표로")
    a = ap.parse_args()

    if a.full or (not a.desk and not a.stats):
        print(open(PB, encoding="utf-8").read())
        return 0

    if a.stats:
        raw = len(open(PB, encoding="utf-8").read())
        print(f"{'데스크':<24}{'뷰':>9}{'전문대비':>10}")
        print("─" * 45)
        tot = 0
        for d in DESKS:
            _, st = build(d, a.keep_full)
            tot += st["out"]
            print(f"{d:<24}{st['out']:>8,}자{st['out']/raw*100:>9.0f}%")
        print("─" * 45)
        print(f"{'전문 1회':<24}{raw:>8,}자")
        print(f"{'데스크 9개 뷰 합':<24}{tot:>8,}자  vs 전문 9회 {raw*9:,}자 "
              f"= **{(1-tot/(raw*9))*100:.0f}% 절감**")
        return 0

    out, st = build(a.desk, a.keep_full)
    if not out:
        return 1
    print(out)
    print(f"[playbook] {a.desk}: {st['full']:,}자 → {st['out']:,}자 "
          f"({st['out']/st['full']*100:.0f}%)" + ("  ⚠️폴백" if st.get("fallback") else ""),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
