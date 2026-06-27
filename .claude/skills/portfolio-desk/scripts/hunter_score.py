#!/usr/bin/env python3
"""hunter_score.py — 경제사냥꾼 채널 트랙레코드 채점기 (grounded-sentiment 정량화)

배경(외부 레퍼런스): 금융 환각 가드레일·grounded sentiment(TradingAgents v0.2.5)는 외부
'센티먼트/뉴스 소스'를 **근거에 묶고 신뢰도를 정량 추적**하라고 한다. 우리는 이미 모든 채널
주장을 [검증]/[정정]/[미확인] 3단계로 태깅해 hunter_log.md에 쌓아왔다(사람이 수동 집계).
이 스크립트가 그 누적 태그를 **기계로 집계**해 채널의 트랙레코드(정정률·검증률) 추세를 낸다.
self-review §3의 '[정정] 비율 재확인'을 수동→자동으로 닫는다.

  hunter_score.py            # 섹션(날짜)별 + 누적 [검증/정정/미확인] 집계·추세
  hunter_score.py --recent 6 # 최근 6개 섹션만
  hunter_score.py --json     # 기계가독 출력

분류 규칙: 한 태그가 복합이면(예 [정정/미확인], [정정/자막오류]) **정정 우선**으로 친다
(채널이 틀린 신호를 보수적으로 집계 = 트랙레코드를 엄격하게). 우선순위 정정 > 미확인 > 검증.
의존성 없음(stdlib). FAIL 안 냄 — 신뢰도 추세 참고용.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
LOG = os.path.join(ROOT, "docs", "research", "hunter_log.md")


def classify(tag):
    """대괄호 태그 1개 → 검증/정정/미확인/None. 복합은 정정>미확인>검증 우선."""
    if "정정" in tag:
        return "정정"
    if "미확인" in tag:
        return "미확인"
    if "검증" in tag:   # '검증', '대체로검증', '검증·날짜' 등 포함
        return "검증"
    return None


def parse_sections(text):
    """## 날짜 헤더로 분할. 각 섹션의 [..]태그를 분류 집계."""
    # 첫 '## ' 이전(파일 머리말)은 버림
    parts = re.split(r"\n(?=## )", text)
    sections = []
    for p in parts:
        m = re.match(r"## (\d{4}-\d{2}-\d{2}.*)", p)
        if not m:
            continue
        head = m.group(1).strip()
        counts = {"검증": 0, "정정": 0, "미확인": 0}
        for tag in re.findall(r"\[([^\[\]]+)\]", p):
            c = classify(tag)
            if c:
                counts[c] += 1
        if sum(counts.values()) == 0:
            continue
        sections.append({"section": head, "date": head[:10], **counts,
                         "total": sum(counts.values())})
    return sections


def pct(n, d):
    return (n / d * 100) if d else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recent", type=int, default=0, help="최근 N개 섹션만")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(LOG):
        print(f"hunter_log 없음: {LOG}"); sys.exit(0)
    sections = parse_sections(open(LOG, encoding="utf-8").read())
    if not sections:
        print("태그가 있는 섹션 없음."); return

    shown = sections[:a.recent] if a.recent else sections  # 파일은 최신이 위
    tot = {"검증": sum(s["검증"] for s in sections),
           "정정": sum(s["정정"] for s in sections),
           "미확인": sum(s["미확인"] for s in sections)}
    grand = sum(tot.values())

    if a.json:
        print(json.dumps({"sections": shown, "cumulative": tot,
                          "total": grand,
                          "correction_rate": round(pct(tot["정정"], grand), 1),
                          "verified_rate": round(pct(tot["검증"], grand), 1)},
                         ensure_ascii=False, indent=1))
        return

    print("\n" + "=" * 64)
    print("  경제사냥꾼 트랙레코드 — hunter_score.py (채널 신뢰도 추세)")
    print("=" * 64)
    print(f"\n섹션별 ({'최근 '+str(a.recent) if a.recent else '전체'} · 파일 최신순)\n")
    print(f"{'날짜/섹션':<34}{'검증':>5}{'정정':>5}{'미확인':>7}{'정정률':>8}")
    for s in shown:
        label = s["section"][:32]
        print(f"{label:<34}{s['검증']:>5}{s['정정']:>5}{s['미확인']:>7}"
              f"{pct(s['정정'], s['total']):>7.0f}%")

    print("\n— 누적 (전 기간) —")
    print(f"  검증 {tot['검증']}  정정 {tot['정정']}  미확인 {tot['미확인']}  (총 {grand}개 주장)")
    print(f"  검증률 {pct(tot['검증'], grand):.0f}%  |  정정률 {pct(tot['정정'], grand):.0f}%"
          f"  |  미확인률 {pct(tot['미확인'], grand):.0f}%")
    print("\n  해석: 채널은 '방향성은 좋으나 수치·고유명사 자막오류 잦음'(기지정 사실).")
    print("  → 정정률은 **수치 신뢰도**, 검증률은 **방향성 신뢰도**의 대리지표. 방향 채택·숫자 교차검증 유지.")
    print("  ※ 자동 변경 없음 — self-review 캘리브레이션 참고용.\n")


if __name__ == "__main__":
    main()
