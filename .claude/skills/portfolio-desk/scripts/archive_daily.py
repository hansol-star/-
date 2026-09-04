#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""archive_daily.py — 스냅샷 파일을 날짜별로 영구 누적 [2026-09-04 신설 · 정훈 지적]

■ 왜 만들었나 — "덮어쓰기"와 "누적"은 다르다
정훈: *"우리 모든 정보는 계속 누적해서 확인하기로 했는데 파일 크기가 왜 이렇게 작아?"*

9/4 감사에서 드러난 것: 여러 수집 도구가 `--save`를 갖고 있는데 **전부 단일 파일을
덮어쓴다.** 그래서 매일 돌려도 크기가 안 는다 — **어제 것이 사라지기 때문**이다.

  disclosures.json  2KB   ← 국내 공시. 매번 최근 7일로 갈아엎음
  transcripts.json  5KB   ← 어닝콜. 조회한 1종목만 남음
  consensus·eps·sentiment·toss_flows 등도 같은 구조

**스냅샷은 "지금 상태"를 답하고, 아카이브는 "그때 무엇이었나"를 답한다.**
후자가 없으면 self-review가 후행 채점할 때 *그날의 근거*를 되짚을 수 없고,
"목표가가 언제 어떻게 바뀌었나" 같은 질문은 원리적으로 답이 안 나온다.

⚠️ 이건 8/30 자막(/tmp)·9/4 뉴스(저장 경로 없음)·9/4 프레임(%TEMP%)과 **같은 클래스**의
   네 번째 사례다. 매번 "그 도구만" 고쳤기 때문에 옆에 남은 형제를 못 봤다
   (8/12 "형제 버그가 옆에 남아 있었다").

■ 설계 — 원본을 건드리지 않는다
각 도구는 지금처럼 스냅샷을 쓰고, 이 스크립트가 **그 파일을 날짜별로 복사**해 쌓는다.
  data/archive/<name>/YYYY-MM/YYYY-MM-DD.json
  · 도구 코드를 안 고쳐도 된다(수집 로직 복제 없음)
  · 내용이 **직전과 같으면 저장하지 않는다** — 같은 값을 매일 복사하면 용량만 는다
  · 원본이 없거나 stale하면 **건너뛰되 그 사실을 말한다**(조용한 성공 금지)

사용:
  archive_daily.py            # 등록된 스냅샷 전부 아카이브
  archive_daily.py --status   # 누적 현황
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ARC = os.path.join(ROOT, "data", "archive")

# 아카이브 대상 — (이름, 원본 경로).
# ⚠️ 추가할 땐 "그때 무엇이었나"를 나중에 물을 값인지 먼저 따진다.
#    매일 같은 값이면 dedupe에 걸려 안 쌓이므로 넣어도 손해는 없지만,
#    목록이 길어지면 무엇이 왜 있는지 아무도 모르게 된다.
TARGETS = [
    ("disclosures", "data/app/disclosures.json"),      # 국내 공시(중대성 3단)
    ("transcripts", "data/app/transcripts.json"),      # 어닝콜 전문
    ("consensus", "data/app/consensus.json"),          # 증권사 목표가
    ("edgar_events", "data/app/edgar_events.json"),    # 미국 8-K 이벤트 [9/4]
    ("eps_revisions", "data/app/eps_revisions.json"),  # 추정치 리비전
    ("sentiment", "data/app/sentiment.json"),          # 리테일 심리
    ("toss_flows", "data/app/toss_flows.json"),        # 국내 수급 4축
    ("toss_market", "data/app/toss_market.json"),      # 장운영·가격제한폭
    ("guru_flows", "data/app/guru_flows.json"),        # 대가 13F
    ("financials", "data/app/financials.json"),        # 재무 3표
    ("flows", "data/app/flows.json"),                  # 국내 수급(일별)
]


def _kst():
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)


def _digest(p: str) -> str:
    try:
        return hashlib.sha1(open(p, "rb").read()).hexdigest()[:16]
    except Exception:                                              # noqa: BLE001
        return ""


def _latest(name: str) -> str | None:
    fs = sorted(glob.glob(os.path.join(ARC, name, "*", "*.json")))
    return fs[-1] if fs else None


def run(quiet: bool = False) -> int:
    today = _kst().date()
    saved = skipped = same = missing = 0
    for name, rel in TARGETS:
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            if not quiet:
                print(f"  ·  {name:<14} 원본 없음 ({rel}) — 그 도구가 아직 --save 로 안 돌았다")
            missing += 1
            continue
        prev = _latest(name)
        if prev and _digest(prev) == _digest(src):
            # 직전 아카이브와 내용이 같다 = 새 정보 없음. 복사해봐야 용량만 는다.
            if not quiet:
                print(f"  =  {name:<14} 직전과 동일 — 건너뜀")
            same += 1
            continue
        dst = os.path.join(ARC, name, today.strftime("%Y-%m"),
                           today.strftime("%Y-%m-%d") + ".json")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        if not quiet:
            print(f"  ✅ {name:<14} → {os.path.relpath(dst, ROOT)}  "
                  f"({os.path.getsize(dst)/1024:.0f}KB)")
        saved += 1
    if not quiet:
        print(f"\n저장 {saved} · 동일 {same} · 원본없음 {missing}")
    # 원본이 하나도 없으면 배선이 끊긴 것이다 — 성공으로 끝내지 않는다.
    return 1 if (saved == 0 and same == 0) else 0


def status() -> int:
    if not os.path.isdir(ARC):
        print("❌ 아카이브 없음 — archive_daily.py 로 시작")
        return 1
    print(f"{'축':<16}{'일수':>5}{'용량':>9}  기간")
    tot = 0
    for name, _ in TARGETS:
        fs = sorted(glob.glob(os.path.join(ARC, name, "*", "*.json")))
        if not fs:
            print(f"{name:<16}{'0':>5}{'-':>9}  (없음)")
            continue
        sz = sum(os.path.getsize(f) for f in fs)
        tot += sz
        print(f"{name:<16}{len(fs):>5}{sz/1e6:>8.2f}MB  "
              f"{os.path.basename(fs[0])[:-5]} ~ {os.path.basename(fs[-1])[:-5]}")
    print(f"{'합계':<16}{'':>5}{tot/1e6:>8.2f}MB")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="스냅샷 → 날짜별 영구 아카이브 (원본 불변)")
    ap.add_argument("--status", action="store_true", help="누적 현황")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args()
    return status() if a.status else run(a.quiet)


if __name__ == "__main__":
    sys.exit(main())
