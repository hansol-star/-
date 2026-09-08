#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hunter_digest.py — 자막 전문 → '검증 대상 문장'만 남기는 압축 다이제스트 (stdlib 전용)

[왜 만들었나 — 2026-09-09]
R1(영상 프리페치)이 매일 TOKEN_LIMIT으로 죽고, 그 여파로 R2·R4a·R4b까지 굶는다.
원인을 뜯어보니 R1의 토큰은 **네트워크(자막 다운로드)가 아니라 에이전트가 자막 전문을 읽는 데**
들어간다. 실측: 편당 3,600~6,700자 × 8~20편 = 한 번에 5만~13만자를 컨텍스트에 올린다.

그런데 우리가 자막에서 실제로 쓰는 건 **[검증/정정/대립·미결/미확인]을 붙일 수 있는 문장**뿐이다
— 수치가 박힌 주장, 종목·기관 이름이 나온 문장, 조건부 예측. 나머지(인사말·"딱 1분만 집중해 봐"·
같은 말 반복)는 한 글자도 판정에 쓰이지 않는다.

⇒ 이 스크립트가 그 선별을 **파이썬으로**(토큰 0) 먼저 하고, 에이전트는 걸러진 것만 읽는다.

⚠️ **압축이지 요약이 아니다.** 원문 문장을 그대로 잘라 올릴 뿐 다시 쓰지 않는다 —
   요약을 스크립트가 하면 그게 곧 '제목만 로깅(추측 분석)'의 자동화판이 된다(7/2 규율).
⚠️ **원문은 그대로 남는다.** data/transcripts/ 는 손대지 않는다. 의심되면 언제든 전문을 읽는다.
⚠️ **판정은 사람(에이전트) 몫이다.** 이 스크립트는 태그를 붙이지 않는다 — 후보만 고른다.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys

_HERE = os.path.abspath(__file__)                     # …/.claude/skills/portfolio-desk/scripts/이 파일
ROOT = os.path.abspath(os.path.join(_HERE, *([os.pardir] * 5)))   # scripts→portfolio-desk→skills→.claude→repo
TDIR = os.path.join(ROOT, "data", "transcripts", "hunter")

# ── 신호어: 우리 유니버스 + 판정에 걸리는 어휘 ────────────────────────────────
UNIVERSE = [
    "삼성전자", "삼성", "SK하이닉스", "하이닉스", "LG전자", "LG이노텍", "삼성전기",
    "두산로보", "두산에너빌", "두산", "현대차", "네이버", "NAVER", "카카오",
    "원익", "테스", "한화에어로", "한화오션", "삼성중공업", "HD현대", "KT&G",
    "SK이노베이션", "한전기술", "BHI", "삼성바이오",
    "엔비디아", "NVDA", "마이크론", "MU", "브로드컴", "AVGO", "애플", "AAPL",
    "구글", "알파벳", "GOOGL", "마이크로소프트", "MSFT", "메타", "META",
    "오라클", "ORCL", "테슬라", "TSLA", "AMD", "팔란티어", "PLTR", "아리스타", "ANET",
    "VOO", "S&P", "나스닥", "다우", "필라델피아", "반도체지수", "코스피", "코스닥",
    "연준", "FOMC", "한국은행", "금통위", "환율", "원달러", "국채", "금리",
    "유가", "WTI", "브렌트", "CPI", "PPI", "고용", "실업",
    "외국인", "외인", "기관", "개인", "연기금", "국민연금", "공매도", "대차",
    "HBM", "DRAM", "D램", "낸드", "관세", "실적", "영업이익", "목표주가", "컨센서스",
]
CLAIM = ["전망", "예상", "발표", "확정", "계약", "수주", "체결", "상향", "하향",
         "급등", "급락", "돌파", "하회", "상회", "인상", "인하", "합의", "추진", "검토"]

DATE10 = re.compile(r"^\d{4}-\d{2}-\d{2}")
NUM = re.compile(r"\d")
PCT = re.compile(r"\d[\d,.]*\s*(?:%|퍼센트|프로)")
MONEY = re.compile(r"\d[\d,.]*\s*(?:조|억|만|천|달러|원|불|弗|bp|배)")
FILLER = re.compile(
    r"(딱\s*1분|집중해\s*봐|좋아요|구독|알림설정|안녕|경제\s*사냥꾼이|영상\s*제작|"
    r"님들|알고\s*있었어|알려줄테니|끝까지|댓글|도움됐으면)"
)


def split_sentences(text: str) -> list[str]:
    """자막은 문장부호가 성글다 — 마침표·물음표 + 접속 어미로 자른다."""
    text = re.sub(r"\[음악\]|\[박수\]|\s+", " ", text)
    parts = re.split(r"(?<=[.?!])\s+|(?<=거야)\s+|(?<=거지)\s+|(?<=했어)\s+|(?<=이야)\s+", text)
    return [p.strip() for p in parts if p.strip()]


def score(sent: str) -> int:
    """판정 가능성 점수 — 수치가 있으면 크게, 종목·기관·주장어가 있으면 더."""
    if FILLER.search(sent):
        return 0
    s = 0
    if PCT.search(sent):
        s += 4
    if MONEY.search(sent):
        s += 4
    elif NUM.search(sent):
        s += 1
    hits = sum(1 for w in UNIVERSE if w in sent)
    s += min(hits, 3) * 2
    if any(w in sent for w in CLAIM):
        s += 2
    if len(sent) < 12:
        s = 0
    return s


def parse_header(raw: str) -> dict:
    head = {}
    m = re.search(r"^#\s*(.+)$", raw, re.M)
    if m:
        head["title"] = m.group(1).strip()
    for key, pat in (("channel", r"^-\s*채널:\s*(.+)$"),
                     ("url", r"^-\s*URL:\s*(.+)$"),
                     ("date", r"^-\s*업로드:\s*(.+)$")):
        mm = re.search(pat, raw, re.M)
        if mm:
            head[key] = mm.group(1).strip()
    return head


def digest_one(path: str, keep: int) -> dict | None:
    try:
        raw = open(path, encoding="utf-8").read()
    except OSError:
        return None
    head = parse_header(raw)
    body = raw.split("## 트랜스크립트", 1)
    body = body[1] if len(body) > 1 else raw
    sents = split_sentences(body)
    scored = [(score(s), i, s) for i, s in enumerate(sents)]
    picked = [t for t in scored if t[0] > 0]
    picked.sort(key=lambda t: (-t[0], t[1]))
    picked = picked[:keep]
    picked.sort(key=lambda t: t[1])          # 원문 순서로 되돌린다(맥락 보존)
    lines = [t[2] for t in picked]
    # 수치 주장만 따로 — 교차검증 체크리스트가 된다
    claims = [s for s in lines if PCT.search(s) or MONEY.search(s)]
    return {
        "id": os.path.splitext(os.path.basename(path))[0],
        "title": head.get("title", ""),
        "date": head.get("date", ""),
        "url": head.get("url", ""),
        "chars_raw": len(raw),
        "lines": lines,
        "numeric_claims": claims[:12],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="자막 전문 → 검증 대상 문장만 압축 (R1 토큰 절감)")
    ap.add_argument("--ids", help="쉼표구분 영상 ID (생략 시 --since 로 최근분)")
    ap.add_argument("--since", help="업로드 날짜 YYYY-MM-DD 이후만")
    ap.add_argument("--keep", type=int, default=12, help="영상당 남길 문장 수 (기본 12 — 452편 실측 4.4x 절감)")
    ap.add_argument("--channel", default="hunter", choices=["hunter", "supe", "jisik"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="마크다운 저장 경로")
    a = ap.parse_args()

    base = TDIR if a.channel == "hunter" else os.path.join(TDIR, a.channel)
    if not os.path.isdir(base):
        print(f"[ERR] 자막 디렉터리 없음: {base}", file=sys.stderr)
        return 1

    if a.ids:
        paths = [os.path.join(base, i.strip() + ".md") for i in a.ids.split(",") if i.strip()]
    else:
        paths = [os.path.join(base, f) for f in os.listdir(base) if f.endswith(".md")]
        paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)

    out, raw_total = [], 0
    for p in paths:
        if not os.path.exists(p):
            print(f"[skip] 없음 {os.path.basename(p)}", file=sys.stderr)
            continue
        d = digest_one(p, a.keep)
        if not d:
            continue
        if a.since:
            # 날짜가 없거나 파싱 불가면 --since 를 줬을 때 제외한다.
            # ⚠️ 9/9 실사고: 상당수 자막 헤더가 `업로드: ?`인데 `'?' < '2026-09-07'`이
            #    **문자열 비교로 False**('?'=0x3F > '2'=0x32)라 필터가 통째로 무력화됐다
            #    — "최근 20편"을 요청했는데 452편 전량이 조용히 통과했다.
            #    날짜형이 아닌 값은 비교 자체를 하지 않는다.
            if not DATE10.match(d["date"] or "") or d["date"][:10] < a.since:
                continue
        raw_total += d["chars_raw"]
        out.append(d)
        if not a.ids and a.since is None and len(out) >= 20:
            break

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0

    buf = [f"# 영상 다이제스트 — {len(out)}편 (압축: 판정 가능한 문장만)", ""]
    buf.append("> ⚠️ **압축이지 요약이 아니다** — 원문 문장을 그대로 골라 실었다. "
               "판정([검증/정정/대립·미결/미확인])과 교차검증은 읽는 쪽 몫이다.")
    buf.append("> 원문 전량은 `data/transcripts/` 에 그대로 있다 — 의심되면 전문을 열 것.")
    buf.append("")
    for d in out:
        buf.append(f"## `{d['id']}` {d['title']}")
        buf.append(f"- 업로드 {d['date']} · {d['url']}")
        if d["numeric_claims"]:
            buf.append(f"- **교차검증 대상 수치 {len(d['numeric_claims'])}건**")
        buf.append("")
        for ln in d["lines"]:
            buf.append(f"- {ln}")
        buf.append("")
    md = "\n".join(buf)

    kept = len(md)
    if raw_total:
        print(f"[digest] {len(out)}편 · 원문 {raw_total:,}자 → 압축 {kept:,}자 "
              f"({kept / raw_total * 100:.0f}%, {raw_total / max(kept,1):.1f}x 절감)", file=sys.stderr)
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
        print(f"[digest] 저장 {a.out}", file=sys.stderr)
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
