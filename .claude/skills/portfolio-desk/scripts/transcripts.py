#!/usr/bin/env python3
"""transcripts.py — 어닝콜 트랜스크립트 전문(Q&A 포함) · 무키 · stdlib only

`docs/data_coverage.md §3 #2` **완전 해소** (2026-08-01).
`guidance.py`(8-K Item 2.02)가 **문서 공시 가이던스 수치**를 덮었지만, 결손으로 남아 있던 건
**경영진이 애널리스트 질문에 답하는 부분** — 수요·재고·가격·공급 코멘트다.
하필 AAPL·MSFT·GOOGL·ORCL은 보도자료에 수치를 안 내고 **구두로만** 줘서, 매수 1순위 GOOGL이
통째로 사각지대였다.

■ 소스: earningscalls.dev — **브라우저 열람 무료·무가입·무페이월**(사이트 명시).
   (API는 유료지만 우리는 공개 페이지를 읽는다. 유료 API 키 불필요.)
   ⚠️ 3자 집계 사이트다. **수치를 인용할 땐 1차 출처(8-K·IR)와 교차**할 것 —
      회사 IR 원문이 정본이고 여기는 편의 경로다.

■ 왜 중요한가 (메모리 정점 판정)
   `master.md §10-2`의 판정 도구는 **마진 추세**인데, 마진이 꺾이기 *전에* 신호가 나오는 곳이
   어닝콜의 수요·공급 코멘트다. 실제로 MU FQ3 콜에서 Sumit Sadana가
   *"The demand continues to be well above our supply"*라고 말했다 — 공급 타이트의 1차 진술.

■ 참고 전용 — 자동 매매 아님.

사용:
  python3 transcripts.py --tickers MU            # 최신 1건 요약
  python3 transcripts.py --tickers MU --full     # 전문 출력
  python3 transcripts.py --tickers MU --grep HBM # 키워드 주변 발언만
  python3 transcripts.py --list MU               # 보유 중인 콜 목록
  python3 transcripts.py --save                  # data/app/transcripts.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.request
import cli_common

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "data", "app", "transcripts.json")
BASE = "https://earningscalls.dev"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

try:
    from insider_us import US                      # 보유 미국주 유니버스 재사용
except Exception:
    US = ["NVDA", "MU", "AAPL", "MSFT", "ANET", "AVGO", "GOOGL", "META", "ORCL"]

# 우리 논지에 직접 물리는 키워드 — 이 주변 발언을 뽑아준다
DEFAULT_KEYS = ["supply", "demand", "pricing", "inventory", "capex", "guidance", "margin", "HBM"]
_last = [0.0]


def _get(url: str) -> str:
    gap = time.time() - _last[0]
    if gap < 1.0:
        time.sleep(1.0 - gap)                      # 3자 사이트 예의상 페이싱
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
    finally:
        _last[0] = time.time()
    return data.decode("utf-8", "replace")


def _text(raw: str) -> str:
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    s = re.sub(r"(?i)</(p|div|br|li|h\d|tr)[^>]*>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = s.replace(" ", " ").replace("’", "'")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def list_calls(ticker: str, limit: int = 8) -> list[dict]:
    """회사별 콜 목록. 실패와 부재를 구분해 예외를 올린다(§4b)."""
    raw = _get(f"{BASE}/company/{ticker.lower()}")
    seen, out = set(), []
    for m in re.finditer(r'href="(/transcripts/([a-z0-9\-_]+)_(\d{4}-\d{2}-\d{2}))"', raw):
        path, slug, date = m.group(1), m.group(2), m.group(3)
        if path in seen:
            continue
        seen.add(path)
        out.append({"ticker": ticker.upper(), "date": date, "url": BASE + path})
        if len(out) >= limit:
            break
    out.sort(key=lambda r: r["date"], reverse=True)
    return out


def fetch_call(url: str) -> dict:
    body = _text(_get(url))
    # 페이지 상단 사이트 크롬 제거 — 'Earnings Call Transcript' 헤딩 뒤부터가 본문
    m = re.search(r"Earnings Call Transcript", body)
    if m:
        body = body[m.start():]
    return {"url": url, "chars": len(body), "text": body}


def find_quotes(text: str, keys: list[str], width: int = 260, per_key: int = 2) -> list[dict]:
    """키워드 주변 발언 추출. 발화자 라벨이 붙은 곳을 우선한다."""
    out = []
    for k in keys:
        n = 0
        for m in re.finditer(re.escape(k), text, re.I):
            seg = text[max(0, m.start() - width // 2): m.start() + width].strip()
            seg = re.sub(r"\s+", " ", seg)
            if len(seg) < 80:
                continue
            out.append({"key": k, "quote": seg})
            n += 1
            if n >= per_key:
                break
    return out


def render(rows: list[dict], full: bool, keys: list[str]):
    print("🗣️ 어닝콜 트랜스크립트 (earningscalls.dev · 무키·무가입)")
    print("   ※ 3자 집계 — **수치 인용 시 8-K·IR 1차 출처와 교차 필수**. 참고 전용.\n")
    for r in rows:
        t = r["ticker"]
        if r.get("error"):
            print(f"  🚨 {t:6} 수집 실패 — {r['error']}  (← '콜 없음'이 아니라 '못 봤음')")
            continue
        if r.get("absent"):
            print(f"  ·  {t:6} 트랜스크립트 없음 (사이트 미수록)")
            continue
        print(f"  ▸ {t:6} {r['date']}  ({r['chars']:,}자)  {r['url']}")
        if full:
            print(r["text"][:12000])
        else:
            for q in r.get("quotes", [])[:6]:
                print(f"      [{q['key']}] …{q['quote'][:230]}…")
        print()


def main():
    ap = argparse.ArgumentParser(description="어닝콜 트랜스크립트 (무키)")
    ap.add_argument("--tickers", help="쉼표·공백구분(생략 시 보유 미국주)")
    ap.add_argument("--list", help="해당 종목의 콜 목록만 출력")
    ap.add_argument("--full", action="store_true", help="본문 출력")
    ap.add_argument("--grep", help="키워드(쉼표·공백구분) 주변 발언만")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.list:
        try:
            for c in list_calls(a.list):
                print(f"  {c['date']}  {c['url']}")
        except Exception as e:
            print(f"🚨 수집 실패: {type(e).__name__} {str(e)[:60]}")
            return 1
        return 0

    keys = [k.strip() for k in a.grep.split(",")] if a.grep else DEFAULT_KEYS
    tickers = [t.strip().upper() for t in cli_common.split_tickers(a.tickers)] if a.tickers else list(US)
    rows = []
    for t in tickers:
        try:
            calls = list_calls(t, limit=3)
            if not calls:
                rows.append({"ticker": t, "absent": True})
                continue
            c = calls[0]
            d = fetch_call(c["url"])
            rows.append({"ticker": t, "date": c["date"], "url": c["url"],
                         "chars": d["chars"], "text": d["text"],
                         "quotes": find_quotes(d["text"], keys)})
        except Exception as e:
            rows.append({"ticker": t, "error": f"{type(e).__name__} {str(e)[:50]}"})

    if a.json:
        print(json.dumps([{k: v for k, v in r.items() if k != "text"} for r in rows],
                         ensure_ascii=False, indent=1))
    else:
        render(rows, a.full, keys)

    if a.save:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"updated": dt.date.today().isoformat(),
                       "note": "어닝콜 트랜스크립트 요약(earningscalls.dev·무키). 수치는 1차 출처 교차 필요.",
                       "rows": [{k: v for k, v in r.items() if k != "text"} for r in rows]},
                      f, ensure_ascii=False, indent=1)
        print(f"저장: {OUT}")
    return 1 if any(r.get("error") for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
