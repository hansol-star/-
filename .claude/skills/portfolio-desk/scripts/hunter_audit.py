#!/usr/bin/env python3
"""
hunter_audit.py — 영상 아카이브 누락 감사 [2026-08-12 신설]

왜 필요한가
────────────────────────────────────────────────────────────────
8/12에 YouTube Data API를 처음 붙여 아카이브 vs 실제 업로드를 대조했더니
**커버리지 73% · 구조적 누락 86건**이 나왔다. 그동안 이 사실을 **알 방법 자체가 없었다** —
RSS·스크레이프는 최신 N편만 보여주므로 "우리가 뭘 못 봤는지"를 알 수 없다.

누락이 단순한 '안 본 영상'이 아니었다는 실증:
  · 모건스탠리 8/6 「Memory — A Small Bump」(조정 종료·재진입 기회, 삼성 EPS -10%)를
    다룬 영상이 누락돼 v72(8/10)·v73(8/12) 어디에도 반영되지 못했다 = **판단 재료의 누락**

누락의 두 원인(8/12 실측)
  ① R1이 평일만 실행 → 누락의 28%가 토·일
  ② `--max 10` 상한 + 저녁 업로드 몰림 → 39%가 17시 이후.
     SKILL의 "저녁분은 다음날 R1이 커버" 전제가 10편 상한에 걸려 성립하지 않았다.

⇒ 이 스크립트는 **구멍이 다시 생기는지 정기적으로 재는 자**다. 주간 R3에 배선한다.

사용법
  python3 hunter_audit.py                    # 최근 30일 감사
  python3 hunter_audit.py --days 60
  python3 hunter_audit.py --after 2026-06-13 --before 2026-08-12
  python3 hunter_audit.py --emit-ids         # 누락 ID만 출력(--fetch 파이프용)
  python3 hunter_audit.py --save             # data/app/hunter_missing_backlog.json 갱신

⚠️ YOUTUBE_API_KEY 필요. 없으면 감사 자체가 불가능하다(그게 이 도구의 존재 이유) —
   키 없으면 명확히 알리고 종료한다. **조용히 0건으로 통과시키지 않는다.**
⚠️ 측정 전용 — 아카이브를 수정하지 않는다(등재는 사람이 판단해서).
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ARCHIVE = os.path.join(REPO, "data", "app", "hunter_archive.json")
BACKLOG = os.path.join(REPO, "data", "app", "hunter_missing_backlog.json")
KST = dt.timezone(dt.timedelta(hours=9))
CHANNEL = "UC7usMJDHmtbs_oegmzQKKMA"   # 경제사냥꾼
UA = {"User-Agent": "Mozilla/5.0"}


def _norm(t: str) -> str:
    """제목 정규화 — 수기 이관 항목이 요약체 제목을 쓰는 경우가 있어 느슨하게 맞춘다."""
    t = html.unescape(t or "")
    t = re.sub(r"\(.*?\)|\[.*?\]", "", t)
    return re.sub(r"[\s'\"‘’“”·,:=+?!.…—\-~]", "", t).lower()


def enumerate_uploads(key: str, after: str, before: str, max_pages: int = 12) -> dict:
    """기간 내 채널 업로드 전량(쇼츠 포함). search.list 1회 = 100 units."""
    out, tok, calls = {}, None, 0
    while True:
        q = {"key": key, "channelId": CHANNEL, "part": "snippet", "type": "video",
             "order": "date", "maxResults": "50",
             "publishedAfter": after, "publishedBefore": before}
        if tok:
            q["pageToken"] = tok
        url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(q)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            d = json.load(r)
        calls += 1
        for it in d.get("items", []):
            vid = (it.get("id") or {}).get("videoId")
            sn = it.get("snippet") or {}
            if vid:
                out[vid] = {"title": html.unescape(sn.get("title", "")),
                            "published": sn.get("publishedAt", "")}
        tok = d.get("nextPageToken")
        if not tok or calls >= max_pages:
            break
        time.sleep(0.3)
    return out, calls


def main():
    ap = argparse.ArgumentParser(description="영상 아카이브 누락 감사 (측정 전용)")
    ap.add_argument("--days", type=int, default=30, help="최근 N일 (기본 30)")
    ap.add_argument("--after", help="YYYY-MM-DD (지정 시 --days 무시)")
    ap.add_argument("--before", help="YYYY-MM-DD")
    ap.add_argument("--emit-ids", action="store_true", help="누락 ID만 쉼표로 출력")
    ap.add_argument("--save", action="store_true", help="누락 목록을 backlog json에 저장")
    a = ap.parse_args()

    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        print("❌ YOUTUBE_API_KEY 미설정 — 누락 감사는 API 없이는 불가능하다.", file=sys.stderr)
        print("   (RSS·스크레이프는 최신 N편만 보여줘 '무엇을 못 봤는지'를 알 수 없다)", file=sys.stderr)
        return 2

    now = dt.datetime.now(dt.timezone.utc)
    if a.after:
        after = f"{a.after}T00:00:00Z"
    else:
        after = (now - dt.timedelta(days=a.days)).strftime("%Y-%m-%dT00:00:00Z")
    before = f"{a.before}T23:59:59Z" if a.before else now.strftime("%Y-%m-%dT%H:%M:%SZ")

    uploads, calls = enumerate_uploads(key, after, before)
    arc = json.load(open(ARCHIVE, encoding="utf-8"))
    have_ids = {v.get("id") for v in arc.get("videos", []) if v.get("id")}
    have_titles = {_norm(v.get("title")) for v in arc.get("videos", []) if v.get("title")}

    missing, by_title = {}, 0
    for vid, v in uploads.items():
        if vid in have_ids:
            continue
        n = _norm(v["title"])
        if n and (n in have_titles or any(n[:12] and n[:12] in h for h in have_titles)):
            by_title += 1
            continue
        missing[vid] = v

    # 오늘 업로드분은 R1(10:00) 이후일 수 있어 '정상 지연'으로 분리
    today_kst = dt.datetime.now(KST).strftime("%Y-%m-%d")
    def _kst(p):
        return dt.datetime.fromisoformat(p.replace("Z", "+00:00")).astimezone(KST)
    today_n = sum(1 for v in missing.values() if _kst(v["published"]).strftime("%Y-%m-%d") == today_kst)
    structural = len(missing) - today_n

    if a.emit_ids:
        print(",".join(missing))
        return 0

    cov = (1 - len(missing) / len(uploads)) * 100 if uploads else 100.0
    print("=" * 72)
    print(f"  영상 아카이브 누락 감사 — {after[:10]} ~ {before[:10]}")
    print("=" * 72)
    print(f"  API 열거      : {len(uploads):>4}건  (search {calls}회 = {calls*100} units / 일 10,000)")
    print(f"  ID 매칭       : {len(uploads)-len(missing)-by_title:>4}건")
    print(f"  제목만 매칭   : {by_title:>4}건  (ID 없이 등재됐던 항목)")
    print(f"  ★ 누락        : {len(missing):>4}건   → 커버리지 {cov:.1f}%")
    print(f"     └ 오늘분   : {today_n:>4}건  (R1 이후 업로드 = 정상 지연)")
    print(f"     └ 구조적   : {structural:>4}건  ← 이게 진짜 구멍")

    if missing:
        wd = collections.Counter("월화수목금토일"[_kst(v["published"]).weekday()] for v in missing.values())
        hr = collections.Counter(_kst(v["published"]).hour for v in missing.values())
        wknd = wd.get("토", 0) + wd.get("일", 0)
        even = sum(n for h, n in hr.items() if h >= 17)
        print(f"\n  요일 편중: 주말 {wknd}건 ({wknd/len(missing)*100:.0f}%) — R1은 평일만 실행")
        print(f"  시간 편중: 17시 이후 {even}건 ({even/len(missing)*100:.0f}%) — R1(10:00) 이후 업로드")
        print("\n  누락 최근 10건:")
        for p, vid, t in sorted(((v["published"], k, v["title"]) for k, v in missing.items()), reverse=True)[:10]:
            print(f"    {_kst(p):%m-%d %H:%M} | {vid} | {t[:46]}")

    if a.save:
        json.dump(missing, open(BACKLOG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n  저장 → {os.path.relpath(BACKLOG, REPO)} ({len(missing)}건)")

    if structural > 0:
        print("\n  ⚠️ 구조적 누락이 있으면 R1 설정을 의심할 것 — `--max` 상한·주말 미실행이 8/12의 원인이었다.")
        print("     소급: hunter_audit.py --emit-ids | xargs -I{} hunter_latest.py --ids {} --fetch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
