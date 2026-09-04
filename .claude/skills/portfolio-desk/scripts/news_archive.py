#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""news_archive.py — 뉴스 기사 영구 누적 [2026-09-04 신설 · 정훈 지적]

■ 왜 만들었나 — 이게 우리 데이터 파이의 유일한 구멍이었다
9/4 누적 감사에서 확인된 사실: 우리는 자막 459편(4.1MB)·보고서 113편·일봉 9.3MB·
체결 292건·결정 191건을 **다 쌓고 있는데, 뉴스만 한 건도 안 쌓고 있었다.**
`naver_data.py --news`로 조회는 매일 하는데 **보고서 산문에 몇 줄 인용하고 원문은 버렸다.**
저장 경로 자체가 없었다.

그래서 잃은 것:
  · **왜 그날 그렇게 판단했는지의 1차 근거**가 사라진다. 보고서엔 결론만 남고
    그 결론을 만든 기사 원문은 없다 — self-review가 후행 채점할 때 근거를 못 되짚는다.
  · **같은 사건의 서술 변화**를 추적할 수 없다(7/29 CXMT처럼 초기 보도가 뒤집히는 건이 있다).
  · **채널 주장 vs 언론 보도**의 시점 대조가 안 된다(누가 먼저 말했나).

⚠️ 8/30에 자막을 /tmp → data/transcripts/ 로 옮긴 것과 **같은 클래스의 결함**이었고,
   그때 자막만 고치고 뉴스는 안 봤다(8/12 "형제 버그가 옆에 남아 있었다"의 재발).

■ 무엇을 저장하나
  data/news/YYYY-MM/YYYY-MM-DD.json  — 날짜별 1파일에 누적(같은 날 여러 번 돌려도 병합)
  각 기사 = {title, link, pubDate, description, query, collected_at}
  ⚠️ 링크·요약만 저장한다(네이버 API가 주는 범위). **본문 전문은 저작권상 저장하지 않는다.**
     인용은 항상 원문 URL과 함께, 짧게.

■ 중복 처리
  같은 기사가 여러 검색어에 걸린다 → **link 기준 dedupe**하고 `query`에 검색어를 누적한다.
  (기사를 지우는 게 아니라 '어느 질의로 걸렸나'를 합친다 — 그 자체가 정보다)

■ 사용
  news_archive.py --collect                 # 기본 질의 세트로 수집·누적
  news_archive.py --collect --query "삼성전자 HBM" "코스피 외국인"
  news_archive.py --status                  # 누적 현황
  news_archive.py --search 반도체 --days 7   # 아카이브에서 되짚기
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
NEWS = os.path.join(ROOT, "data", "news")

# 매일 도는 기본 질의 — 보유·워치 축 + 매크로 축.
# ⚠️ 늘리기 전에 생각할 것: 질의 하나가 곧 매일 N건의 누적이다.
#    "많이 모으기"가 목적이 아니라 **나중에 되짚을 수 있는 것**이 목적이다.
DEFAULT_QUERIES = [
    "코스피 외국인 수급", "삼성전자", "SK하이닉스 HBM", "현대차",
    "LG전자", "NAVER 네이버", "두산로보틱스",
    "반도체 수출", "원달러 환율", "한국은행 금리", "국제유가",
]


def _kst():
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)


def _path(d: dt.date) -> str:
    return os.path.join(NEWS, d.strftime("%Y-%m"), d.strftime("%Y-%m-%d") + ".json")


def _load(p: str) -> dict:
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:                                              # noqa: BLE001
        return {"date": None, "articles": []}


def _strip(s: str) -> str:
    """네이버 API가 <b> 태그와 HTML 엔티티를 섞어 준다 — 저장 전에 벗긴다."""
    s = re.sub(r"<[^>]+>", "", s or "")
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"),
                 ("&quot;", '"'), ("&apos;", "'"), ("&nbsp;", " ")):
        s = s.replace(a, b)
    return s.strip()


def fetch(query: str, display: int = 20) -> list[dict]:
    """naver_data.py를 그대로 호출한다 — API 호출 로직을 복제하지 않는다."""
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "naver_data.py"),
                            "--news", query, "--display", str(display)],
                           capture_output=True, text=True, timeout=60)
    except Exception as e:                                         # noqa: BLE001
        print(f"  ⚠️ {query}: {type(e).__name__}", file=sys.stderr)
        return []
    # ⚠️ naver_data.py는 **JSON이 아니라 사람용 텍스트**로 찍는다(9/4 실측).
    #    처음엔 json.loads를 시도했다가 전 질의 0건이 나왔다 — 조용히 빈 결과를 쌓을 뻔했다.
    #    형식: "· [pubDate] 제목" / 들여쓴 요약 / 들여쓴 URL 3줄 묶음.
    lines = (r.stdout or "").splitlines()
    now = _kst().strftime("%Y-%m-%d %H:%M")
    arts, cur = [], None
    for ln in lines:
        m = re.match(r"^·\s*\[([^\]]*)\]\s*(.+)$", ln.strip())
        if m:
            if cur and cur.get("link"):
                arts.append(cur)
            cur = {"title": _strip(m.group(2)), "pubDate": m.group(1).strip(),
                   "description": "", "link": None,
                   "query": [query], "source": "naver", "collected_at": now}
            continue
        if cur is None:
            continue
        t = ln.strip()
        if t.startswith("http"):
            cur["link"] = t
        elif t and not cur["description"]:
            cur["description"] = _strip(t)[:400]
    if cur and cur.get("link"):
        arts.append(cur)
    if not arts and "총" not in (r.stdout or ""):
        print(f"  ⚠️ {query}: 응답 없음(키 미설정 의심)", file=sys.stderr)
    return arts


# 해외 기사 — 보유 미국 9종목 + 워치. Yahoo Finance RSS(무키·종목별).
# ⚠️ 국내(네이버)와 **같은 파일에 섞어 저장**하되 source로 구분한다.
#    분리 저장하면 "그날 무슨 일이 있었나"를 두 군데서 봐야 한다 — 시점 대조가 목적이므로 한 곳에 둔다.
US_TICKERS = ["NVDA", "MSFT", "GOOGL", "AAPL", "META", "AVGO", "MU", "ORCL", "VOO"]
YF_RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US"


def fetch_intl(ticker: str) -> list[dict]:
    """해외 기사 — Yahoo Finance RSS. 키 불요·종목별.

    ⚠️ RSS는 조용히 빈 결과를 준다(종목 폐지·심볼 오타). 0건이면 그 사실을 남긴다.
    """
    import urllib.request
    now = _kst().strftime("%Y-%m-%d %H:%M")
    try:
        req = urllib.request.Request(YF_RSS.format(t=ticker),
                                     headers={"User-Agent": "Mozilla/5.0"})
        x = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
    except Exception as e:                                         # noqa: BLE001
        print(f"  ⚠️ {ticker}: {type(e).__name__}", file=sys.stderr)
        return []
    out = []
    for it in re.findall(r"<item>(.*?)</item>", x, re.S):
        def g(tag):
            m = re.search(rf"<{tag}>(.*?)</{tag}>", it, re.S)
            return _strip(m.group(1)) if m else ""
        link = g("link")
        if not link:
            continue
        out.append({"title": g("title"), "link": link, "pubDate": g("pubDate"),
                    "description": g("description")[:400], "query": [ticker],
                    "source": "yahoo", "collected_at": now})
    if not out:
        print(f"  ⚠️ {ticker}: 0건(심볼 확인)", file=sys.stderr)
    return out


def collect(queries: list[str], display: int = 20, quiet: bool = False,
            intl: bool = True) -> int:
    today = _kst().date()
    p = _path(today)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    cur = _load(p)
    by_link = {a["link"]: a for a in cur.get("articles") or []}
    before = len(by_link)
    for q in queries:
        got = fetch(q, display)
        for a in got:
            ex = by_link.get(a["link"])
            if ex:
                # 이미 있는 기사 — 지우지 않고 **어느 질의로도 걸렸는지**를 합친다
                for qq in a["query"]:
                    if qq not in ex.setdefault("query", []):
                        ex["query"].append(qq)
            else:
                by_link[a["link"]] = a
        if not quiet:
            print(f"  🇰🇷 {q:<18} {len(got):>3}건")
    if intl:
        for t in US_TICKERS:
            got = fetch_intl(t)
            for a in got:
                ex = by_link.get(a["link"])
                if ex:
                    for qq in a["query"]:
                        if qq not in ex.setdefault("query", []):
                            ex["query"].append(qq)
                else:
                    by_link[a["link"]] = a
            if not quiet:
                print(f"  🇺🇸 {t:<18} {len(got):>3}건")
    arts = sorted(by_link.values(), key=lambda x: str(x.get("pubDate") or ""), reverse=True)
    json.dump({"date": today.isoformat(), "updated": _kst().strftime("%Y-%m-%d %H:%M"),
               "queries": queries, "articles": arts},
              open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not quiet:
        print(f"\n✅ {p}\n   누적 {len(arts)}건 (신규 {len(arts)-before})")
    return 0


def status() -> int:
    files = sorted(glob.glob(os.path.join(NEWS, "*", "*.json")))
    if not files:
        print("❌ 아카이브 비어 있음 — news_archive.py --collect 로 시작")
        return 1
    tot = 0
    for f in files:
        tot += len(_load(f).get("articles") or [])
    size = sum(os.path.getsize(f) for f in files)
    print(f"뉴스 아카이브 — {len(files)}일 · 기사 {tot:,}건 · {size/1e6:.2f}MB")
    print(f"  기간: {os.path.basename(files[0])[:-5]} ~ {os.path.basename(files[-1])[:-5]}")
    for f in files[-5:]:
        d = _load(f)
        print(f"  {os.path.basename(f)[:-5]}  {len(d.get('articles') or []):>4}건")
    return 0


def search(term: str, days: int = 14, limit: int = 20) -> int:
    cutoff = _kst().date() - dt.timedelta(days=days)
    hits = []
    for f in sorted(glob.glob(os.path.join(NEWS, "*", "*.json")), reverse=True):
        try:
            d = dt.date.fromisoformat(os.path.basename(f)[:-5])
        except ValueError:
            continue
        if d < cutoff:
            continue
        for a in _load(f).get("articles") or []:
            if term in (a.get("title") or "") or term in (a.get("description") or ""):
                hits.append((d, a))
    print(f"«{term}» 최근 {days}일 · {len(hits)}건")
    for d, a in hits[:limit]:
        print(f"  {d} {a.get('title')[:60]}")
        print(f"       {a.get('link')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="뉴스 기사 영구 누적 (조회 전용·저작권상 본문 미저장)")
    ap.add_argument("--collect", action="store_true", help="수집·누적")
    ap.add_argument("--query", nargs="*", help="검색어(생략 시 기본 세트)")
    ap.add_argument("--display", type=int, default=20, help="질의당 기사 수(최대 100)")
    ap.add_argument("--status", action="store_true", help="누적 현황")
    ap.add_argument("--search", help="아카이브에서 되짚기")
    ap.add_argument("--days", type=int, default=14, help="--search 기간")
    ap.add_argument("--no-intl", action="store_true", help="해외(Yahoo RSS) 생략")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args()
    if a.status:
        return status()
    if a.search:
        return search(a.search, a.days)
    if a.collect:
        return collect(a.query or DEFAULT_QUERIES, a.display, a.quiet, not a.no_intl)
    ap.error("--collect · --status · --search 중 하나가 필요하다")


if __name__ == "__main__":
    sys.exit(main())
