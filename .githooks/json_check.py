#!/usr/bin/env python3
"""커밋 전 JSON 무결성 검사 [9/30 시스템 평가 C].

9/30 R1(무인)이 data/app/feeds.json 문자열 안에 raw 개행을 넣어 커밋·푸시했고,
validate_report가 FAIL을 낸 건 그 뒤 대화형 세션이었다 — 망가진 정본이 main에 먼저 올라갔다.
→ 커밋 시점에 스테이징된 .json을 전부 엄격 파싱한다. 실패하면 커밋을 막고 복구 명령을 알려준다.
   --fix <파일>: 비엄격 파싱으로 읽어 다시 쓴다(제어문자를 이스케이프 — 내용 손실 없음).
"""
import json
import subprocess
import sys


def staged_json():
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         capture_output=True, text=True, encoding="utf-8").stdout
    return [p for p in out.splitlines() if p.endswith(".json")]


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--fix":
        for p in sys.argv[2:]:
            d = json.loads(open(p, encoding="utf-8").read(), strict=False)
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                json.dump(d, f, ensure_ascii=False, indent=1)
                f.write("\n")
            print(f"복구: {p}")
        return 0
    bad = []
    for p in staged_json():
        blob = subprocess.run(["git", "show", f":{p}"], capture_output=True).stdout
        try:
            json.loads(blob.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            bad.append((p, e))
    if bad:
        print("❌ 커밋 차단 — 파싱 안 되는 JSON이 스테이징돼 있다(정본이 main에서 깨진다):")
        for p, e in bad:
            print(f"   {p}: {e}")
        print("   복구: python .githooks/json_check.py --fix " + " ".join(p for p, _ in bad)
              + "  → 다시 git add 후 커밋")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
