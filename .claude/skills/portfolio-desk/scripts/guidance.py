#!/usr/bin/env python3
"""guidance.py — 실적 보도자료의 **가이던스**(SEC 8-K Item 2.02) · 무키 · stdlib only

`docs/data_coverage.md §3 #2` **부분** 해소 (2026-08-01 신설).
그 문서의 표현: *"실적 '숫자'는 이제 있지만 경영진이 말한 다음 분기 가이던스·수요 코멘트가
없다. 메모리 정점 판정의 핵심 입력."*

■ 이게 덮는 것 / 못 덮는 것 (★과대 광고 금지)
   ✅ 덮음  — 회사가 **문서로 공시한** 다음 분기 가이던스 수치(매출·마진·EPS 레인지)와
              보도자료 본문의 경영진 코멘트. 8-K Item 2.02(Results of Operations)에
              EX-99.1로 첨부되는 실적 보도자료가 1차 출처다.
   ❌ 못 덮음 — **어닝콜 Q&A 전문**(트랜스크립트). 애널리스트가 캐묻는 수요·재고·가격
              코멘트는 여기 안 나온다. 그건 여전히 결손이다.
   ⇒ `data_coverage.md §3 #2`는 **"부분 해소"로만** 내리고 완료로 지우지 않는다.

■ 왜 재무제표(financials.py)로 안 되나
   `edgar_facts.py`가 뽑는 XBRL은 **이미 지나간 분기의 확정치**다. 가이던스는 XBRL 태그가
   없는 **산문·표**라 보도자료 원문을 읽어야만 나온다. 메모리 정점 판정처럼 *앞을 보는*
   질문에는 확정치가 답을 못 준다.

■ 경보·참고 전용 — 자동 매매 아님. 추출된 문장은 **원문 URL과 함께** 쓰고,
  수치를 인용할 땐 CLAUDE.md 7/26 규칙(주체·범위·형식 병기)을 적용할 것.

SEC 요구: User-Agent에 연락처(없으면 403). 10 req/s 제한 → insider_us.py의 페이싱 재사용.

사용:
  python3 guidance.py                     # 보유 미국주 최근 가이던스
  python3 guidance.py --tickers MU,NVDA
  python3 guidance.py --full MU           # 추출 문장 전체(잘라내지 않음)
  python3 guidance.py --save              # data/app/guidance.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "data", "app", "guidance.json")

import edgar_facts as _E
from insider_us import _get, US          # 검증된 SEC 클라이언트·페이싱·유니버스 재사용

ITEM_RESULTS = "2.02"                    # Item 2.02 = Results of Operations and Financial Condition

# ★가이던스는 **문장이 아니라 표**로 나온다 (2026-08-01 실측).
#   첫 구현은 문장 단위로 훑어서 MU 보도자료에서 0건이 나왔다 — 실제로는
#   "Revenue $50.0 billion ± $1.0 billion / Gross margin Approximately 86% /
#    Diluted earnings per share $30.73 ± $1.00"이 버젓이 있었는데, 표에는 마침표가 없어
#   문장 분리가 통째로 한 덩어리(>600자)로 만들어 버렸다.
#   ⇒ 문장 대신 **'Business Outlook' 앵커 뒤 블록**을 잡는다.
#   (data_coverage.md §4b — 0은 결론이 아니라 가설. 원문을 열어보니 부재가 아니라 파서 결함이었다.)
OUTLOOK_ANCHOR = re.compile(
    r"(business outlook|financial outlook|(?:cfo )?outlook commentary|"
    r"(?:guidance|outlook) for the (?:first|second|third|fourth|next)[^.]{0,60}quarter|"
    r"(?:first|second|third|fourth) quarter (?:of )?(?:fiscal )?20\d\d outlook|"
    r"we expect (?:first|second|third|fourth) quarter 20\d\d)", re.I)
OUTLOOK_STOP = re.compile(
    r"(product highlights|conference call|investor webcast|about (?:micron|nvidia|the company)|"
    r"non-gaap financial measures|use of non-gaap)", re.I)
# 면책 고지 블록은 가이던스가 아니다 — NVDA 보도자료에도 "business outlook for the second
# quarter ... and other statements that are not historical facts"라는 **고지문**이 따로 있다.
BOILERPLATE = re.compile(
    r"not historical facts|forward[- ]looking statements? (?:within|are|involve|speak)|"
    r"safe harbor|Private Securities Litigation Reform Act|risks and uncertainties", re.I)
# 가이던스 수치의 존재 표식 — 블록 후보를 고를 때 '숫자 밀도'로 점수를 매긴다
GUIDE_NUM = re.compile(r"\$\s?[\d.,]+\s*(?:billion|million)|[\d.]+\s*(?:%|percent|basis points)", re.I)

# 라벨과 값 사이에 끼는 연결어("guidance of approximately", "is expected to be")를 흡수한다.
#   MU  = "Revenue $50.0 billion ± $1.0 billion"            (표 — 연결어 없음)
#   NVDA= "Revenue is expected to be $91.0 billion, plus or minus 2%"
#   AVGO= "Third quarter revenue guidance of approximately $29.4 billion"
_CONN = (r"(?:\s*(?:guidance|outlook|is|are|of|to|be|expected|approximately|about|projected|"
         r"anticipated|at|in|the|range)\b){0,7}[^a-zA-Z0-9$]{0,6}")
_PM = (r"(?:\s*,?\s*(?:±|\+/-|plus or minus)\s*\$?\s?[\d.,]+"
       r"\s*(?:billion|million|%|percent|basis points)?)?")   # "…billion, plus or minus 2%" 쉼표 허용
# 레인지 표기 지원 — META는 "in the range of $61-64 billion"으로 낸다(단일 값이 아님)
_RANGE = r"(?:\s*(?:-|–|—|to)\s*\$?\s?[\d.,]+)?"
_MONEY = r"(\$\s?[\d.,]+" + _RANGE + r"\s*(?:billion|million)?" + _PM + r")"
_PCT = r"((?:[\d.]+\s*(?:%|percent))" + _PM + r")"

METRIC_PATTERNS = [
    ("매출", r"(?:total )?revenue" + _CONN + _MONEY),
    ("매출총이익률", r"gross margins?" + _CONN + _PCT),
    ("영업비용", r"operating expenses" + _CONN + _MONEY),
    # 총비용·capex = AI 캐펙스 논지의 핵심 수치(META·GOOGL·MSFT는 여기가 가이던스의 본체다)
    ("총비용", r"total expenses" + _CONN + _MONEY),
    ("설비투자", r"capital expenditures" + _CONN + _MONEY),
    ("EPS", r"(?:diluted )?earnings per share" + _CONN + r"(\$\s?[\d.,]+" + _RANGE + _PM + r")"),
]

# 경영진 코멘트(따옴표 인용) — 표에 안 담기는 '톤'이 여기 있다
QUOTE = re.compile(r"[“\"]([^”\"]{60,600})[”\"]\s*,?\s*said\s+([A-Z][\w.\- ]{2,40})", re.S)


def _text(raw: str) -> str:
    """HTML → 평문. 표(<td>)는 셀 경계를 공백으로 살려야 숫자가 붙어버리지 않는다."""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    s = re.sub(r"(?i)</(td|th|tr|p|div|br|li)[^>]*>", " ", s)
    s = re.sub(r"(?i)<br[^>]*/?>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = s.replace(" ", " ").replace("’", "'").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip()


def outlook_block(text: str, span: int = 1400) -> str:
    """'Business Outlook' 앵커 뒤 블록을 잘라낸다(다음 섹션 제목에서 멈춤).

    가장 마지막 앵커가 아니라 **가장 내용이 실한** 후보를 고른다 — 보도자료 뒤쪽
    GAAP↔non-GAAP 조정표에도 'OUTLOOK'이 또 나오기 때문.
    """
    best, best_score = "", 0
    for m in OUTLOOK_ANCHOR.finditer(text):
        chunk = text[m.start(): m.start() + span]
        stop = OUTLOOK_STOP.search(chunk, m.end() - m.start())
        if stop:
            chunk = chunk[:stop.start()]
        # ★길이가 아니라 **가이던스 수치 밀도**로 고른다. 길이로 골랐더니 NVDA에서
        #   면책 고지문("...business outlook for the second quarter... not historical facts")을
        #   집어 실제 outlook($91.0 billion)을 놓쳤다(2026-08-01 실측).
        score = len(GUIDE_NUM.findall(chunk))
        if BOILERPLATE.search(chunk[:300]):
            score -= 5
        if score > best_score or (score == best_score and len(chunk) > len(best)):
            best, best_score = chunk, score
    return best.strip() if best_score > 0 else best.strip()


def parse_metrics(block: str) -> dict:
    """가이던스 블록에서 핵심 수치를 라벨 기준으로 뽑는다. 실패한 항목은 넣지 않는다."""
    out = {}
    for label, pat in METRIC_PATTERNS:
        m = re.search(pat, block, re.I)
        if m:
            v = re.sub(r"\s+", " ", m.group(1)).strip(" .,")
            if v and re.search(r"\d", v):
                out[label] = v
    return out


def extract_quotes(text: str, limit: int = 2) -> list[str]:
    """경영진 인용 — 수치 표가 못 담는 '수요·사이클 톤'이 여기 있다."""
    out = []
    for m in QUOTE.finditer(text):
        body = re.sub(r"\s+", " ", m.group(1)).strip()
        out.append(f"{m.group(2).strip()}: “{body}”")
        if len(out) >= limit:
            break
    return out


def latest_results_8k(ticker: str, days: int = 190) -> dict | None:
    """최근 Item 2.02(실적) 8-K 1건 → EX-99.1 보도자료 본문.

    ⚠️ 없으면 None을 돌려주되, 호출부는 **'실패'와 '부재'를 구분해서** 보고해야 한다
       (data_coverage.md §4b — 0은 결론이 아니라 가설).
    """
    cik = _E.cik_map().get(ticker.upper())
    if not cik:
        return {"error": "CIK 없음(티커 오류이거나 SEC 미신고)"}
    sub = json.loads(_get(f"https://data.sec.gov/submissions/CIK{cik}.json").decode())
    rec = sub.get("filings", {}).get("recent", {})
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    forms, items = rec.get("form", []), rec.get("items", [])

    for i, form in enumerate(forms):
        if form != "8-K":
            continue
        fdate = rec["filingDate"][i]
        if fdate < cutoff:
            break                                   # recent는 최신순
        if ITEM_RESULTS not in (items[i] if i < len(items) else ""):
            continue
        acc = rec["accessionNumber"][i].replace("-", "")
        base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}"
        try:
            idx = json.loads(_get(f"{base}/index.json").decode())
        except Exception as e:
            return {"error": f"인덱스 조회 실패 {type(e).__name__}"}
        # ⚠️ 첨부물 이름으로 고르면 안 된다 — 회사마다 제각각이다.
        #    MU  = "a2026q3ex991-pressrelease.htm"  (ex99 포함)
        #    NVDA= "q1fy27pr.htm" + "q1fy27cfocommentary.htm"  (ex99 **없음**)
        #    첫 구현은 /ex-?99/ 로만 걸러 NVDA를 통째로 '부재'로 보고했다(2026-08-01 실측).
        #    ⇒ 본문 첨부를 **크기순으로 열어 실제 내용으로** 고른다. CFO commentary는
        #      가이던스 근거가 더 풍부해서 같이 읽는다.
        items = idx.get("directory", {}).get("item", [])
        primary = rec.get("primaryDocument", [""] * len(forms))[i].split("/")[-1].lower()
        acc_dash = rec["accessionNumber"][i].lower()
        cand = []
        for it in items:
            n = it.get("name", "")
            nl = n.lower()
            if not nl.endswith((".htm", ".html", ".txt")):
                continue
            if nl == primary or nl.startswith(acc_dash) or re.fullmatch(r"r\d+\.htm", nl):
                continue                              # 8-K 본문·인덱스·XBRL 렌더는 제외
            try:
                size = int(it.get("size") or 0)
            except (TypeError, ValueError):
                size = 0
            cand.append((size, n))
        if not cand:
            continue
        cand.sort(reverse=True)                       # 큰 것부터 = 보도자료 본문일 확률 높음
        body, urls = "", []
        for _, n in cand[:3]:
            try:
                body += " " + _text(_get(f"{base}/{n}").decode("utf-8", "replace"))
                urls.append(f"{base}/{n}")
            except Exception:
                continue
        if not body.strip():
            return {"error": "보도자료 본문 다운로드 실패(첨부는 있음)"}
        blk = outlook_block(body)
        return {"ticker": ticker.upper(), "filed": fdate, "accession": rec["accessionNumber"][i],
                "url": urls[0] if urls else base, "sources": urls, "chars": len(body),
                "outlook": blk, "metrics": parse_metrics(blk),
                "commentary": extract_quotes(body)}
    return None                                      # 부재 (기간 내 실적 8-K 없음)


def render(rows: list[dict], full: bool = False):
    print("가이던스 — SEC 8-K Item 2.02 실적 보도자료(EX-99.1) · 무키")
    print("※ 이건 **문서 공시 가이던스**다. 어닝콜 Q&A 전문은 여전히 결손(§3 #2 부분 해소).\n")
    for r in rows:
        t = r.get("ticker", "?")
        if r.get("error"):
            print(f"  🚨 {t:6} 수집 실패 — {r['error']}  (← '가이던스 없음'이 아니라 '못 봤음')")
            continue
        if r.get("absent"):
            print(f"  ·  {t:6} 기간 내 Item 2.02 8-K 없음 (부재 — 실적 시즌 밖일 수 있음)")
            continue
        met, blk, com = r.get("metrics") or {}, r.get("outlook") or "", r.get("commentary") or []
        print(f"  ▸ {t:6} {r['filed']}  {r['url']}")
        if met:
            print("      [가이던스] " + " · ".join(f"{k} {v}" for k, v in met.items()))
        elif blk:
            print("      · 수치 파싱 실패(블록은 있음) — 아래 원문 블록 확인:")
        else:
            print("      · Business Outlook 블록 미검출 — 회사가 보도자료에 가이던스를 안 낼 수도,")
            print("        표현이 달라 앵커를 못 맞췄을 수도 있다. **부재로 단정 말고 원문 확인.**")
        if blk and (full or not met):
            print("      원문: " + (blk if full else blk[:400] + ("…" if len(blk) > 400 else "")))
        for c in com:
            print("      💬 " + (c if full else c[:260] + ("…" if len(c) > 260 else "")))
        print()


def main():
    ap = argparse.ArgumentParser(description="실적 보도자료 가이던스 (SEC 8-K Item 2.02)")
    ap.add_argument("--tickers", help="쉼표구분(생략 시 보유 미국주)")
    ap.add_argument("--days", type=int, default=190, help="조회 기간(기본 190일 = 최근 2분기)")
    ap.add_argument("--full", action="store_true", help="문장 자르지 않고 전체 출력")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",")] if args.tickers else list(US)
    rows = []
    for t in tickers:
        try:
            r = latest_results_8k(t, args.days)
        except Exception as e:
            r = {"ticker": t, "error": f"{type(e).__name__} {str(e)[:50]}"}
        if r is None:
            r = {"ticker": t, "absent": True}
        r.setdefault("ticker", t)
        rows.append(r)

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        render(rows, args.full)

    if args.save:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"updated": dt.date.today().isoformat(),
                       "note": "SEC 8-K Item 2.02 보도자료 가이던스. 어닝콜 Q&A 전문은 미포함.",
                       "rows": rows}, f, ensure_ascii=False, indent=1)
        print(f"저장: {OUT}")

    return 1 if any(r.get("error") for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
