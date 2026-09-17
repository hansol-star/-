#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""watch_calls.py — 워치리스트 콜 원장화 (측정 전용 · 어떤 룰도 바꾸지 않는다)

★[2026-09-14 신설 — 정훈 "데이터 나름 많이 쌓이지 않았나? 점점 잘 맞았으면"]

[왜 만들었나 — 채점 표본의 진짜 병목]
`calls_log.jsonl`은 991행이지만 **독립 단위는 종목 16개**다. 66일치 반복은 같은 종목의
중첩 전진창이라 검정력을 거의 안 늘린다. 그래서 별점 버킷 5개로 쪼개면 **버킷당 종목 3~4개**가
되고, `star_validate`의 부트스트랩 CI가 전부 겹친다 — 8/29 이후 5회 연속 '판정 불가'의
상당 부분이 표본 부족이 아니라 **표본을 버리고 있었기 때문**이다.

우리는 매 보고서 워치 22종목에도 ⭐별점·스코어를 매긴다(CLAUDE.md 풀표 규약). 그런데
`score_calls.py`의 백필 소스가 **`stocks.json` git 히스토리**이고 stocks.json에는 **보유만**
들어 있다 → 워치 콜은 구조적으로 원장에 못 들어갔다. **매 보고서 22건씩 만들어 매 보고서 버렸다.**
실측 소급 = **816콜 · 종목 23개**. 병합하면 독립 단위가 **16 → 약 36개(2.25배)**가 된다.

8/2 원칙의 채점판이다: *"오더북에 들어간 것만 집행된다"* ⇒ **원장에 들어간 것만 채점된다.**

[왜 워치가 오히려 좋은 표본인가]
  · **선택 편향이 없다** — 보유는 우리가 이미 산 것(좋아하는 것만 남는다). 워치는 안 산 것을 포함한다.
  · **처분효과가 안 낀다** — 팔지 않으므로 손익 심리가 별점에 되먹임되지 않는다.
  · **별점 스펙트럼이 넓다** — 보유는 ⭐3~5에 몰리지만 워치는 ⭐2(SPCX 32·IONQ 42)부터 ⭐4(ANET 87)까지 퍼져 있다.

⚠️ **한계 — 반드시 같이 읽을 것**
  · 워치 별점이 보유만큼 정성껏 매겨졌다는 보장이 없다(노이즈가 더 클 수 있다).
    ⇒ 그래서 병합이 **기본값이 아니다**. `star_validate --with-watch`로 **따로 본다.**
    두 원장이 같은 방향이면 그게 8/5 절차 ③(횡단면 재현)이고, 갈리면 그 자체가 산출물이다.
  · 과거 보고서의 ⭐ 표기가 3종(⭐N/NN · ⭐N 단독 · ⭐ 반복)이라 **스코어는 대부분 결측**이다
    (⭐N/NN 형식이 최근 도입). 별점 축은 온전하고 **연속 스코어 축은 워치로 못 늘린다.**
  · 보고서 마크다운이 1차 출처다 — 같은 날 addendum이 있으면 **나중 파일이 이긴다**(날짜+종목 dedupe).

사용:
  python3 .claude/skills/portfolio-desk/scripts/watch_calls.py            # 현황 요약
  python3 .claude/skills/portfolio-desk/scripts/watch_calls.py --save     # 원장 생성·갱신
  python3 .claude/skills/portfolio-desk/scripts/watch_calls.py --unmapped # 매핑 실패 진단
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
REPORTS = os.path.join(ROOT, "docs", "reports")
LEDGER = os.path.join(ROOT, "data", "app", "watch_calls.jsonl")

# 코스닥 종목코드 — 접미사가 다르면 다른 회사다(영구교정).
KQ_CODES = {"240810", "095610"}

# 종목명 → 티커. 국내는 6자리 코드가 표에 함께 오면 코드가 이긴다(별칭보다 안전).
# ⚠️ 티커 자체(pltr·tsla…)도 별칭으로 자동 추가된다 — 표에 티커로만 적힌 행이 실제로 있다.
NAMES = {
    "000660.KS": ["sk하이닉스", "하이닉스"],
    "009150.KS": ["삼성전기"],
    "034020.KS": ["두산에너빌리티", "두산에너", "두산에너빌"],
    "011070.KS": ["lg이노텍", "이노텍"],
    "042660.KS": ["한화오션"],
    "033780.KS": ["kt&g", "케이티앤지"],
    "240810.KQ": ["원익ips", "원익"],
    "095610.KQ": ["테스"],
    "012450.KS": ["한화에어로스페이스", "한화에어로"],
    "010140.KS": ["삼성중공업", "삼성중공", "삼성중"],
    "329180.KS": ["hd현대중공업", "hd현대중", "현대중공업"],
    "207940.KS": ["삼성바이오로직스", "삼성바이오"],
    "096770.KS": ["sk이노베이션", "sk이노"],
    "GEV": ["ge vernova", "지이버노바", "ge버노바"],
    "TMUS": ["t-mobile", "tmobile", "티모바일"],
    "PLTR": ["팔란티어", "palantir"],
    "IONQ": ["아이온큐"],
    "IBM": ["아이비엠"],
    "TSLA": ["테슬라", "tesla"],
    "AMD": ["에이엠디"],
    "ANET": ["아리스타", "arista"],
    "STM": ["st마이크로", "에스티마이크로"],
    "SPCX": ["스페이스x", "스페이스엑스", "spacex"],
    # [9/17 편입 d193] — 위 제외 종목 별칭은 **과거 보고서 소급용이라 지우지 않는다**.
    "TSM": ["tsmc", "티에스엠씨", "대만반도체"],
    "AMAT": ["어플라이드머티리얼즈", "어플라이드 머티리얼즈", "어플라이드머티어리얼즈", "applied materials"],
    # 보유 종목도 워치표에 섞여 등장하는 시기가 있었다(편입 직전 등).
    "005930.KS": ["삼성전자"],
    "005380.KS": ["현대차"],
    "066570.KS": ["lg전자"],
    "035420.KS": ["네이버", "naver"],
    "454910.KS": ["두산로보틱스", "두산로보"],
    "NVDA": ["엔비디아"],
    "MU": ["마이크론"],
    "AAPL": ["애플"],
    "MSFT": ["마이크로소프트"],
    "GOOGL": ["구글", "알파벳"],
    "META": ["메타"],
    "AVGO": ["브로드컴"],
    "ORCL": ["오라클"],
    "VOO": [],
}

# 티커 본체를 별칭에 자동 편입(예: PLTR → "pltr"). 손으로 적으면 반드시 빠진다.
for _tk, _al in NAMES.items():
    _base = _tk.split(".")[0].lower()
    if _base not in _al:
        _al.append(_base)

CODE_RE = re.compile(r"\((\d{6})\)")
STAR_RE = re.compile(r"⭐\s*([1-5])(?:\s*/\s*(\d{1,3}))?")
DATE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})\.md$")
HEAD_RE = re.compile(r"^#{2,4}\s*[^\n]*워치리스트[^\n]*$", re.M)

# 워치 섹션이 아니라 '워치'를 제목에 쓴 이슈 심층(예: "④ 두산에너빌리티 워치→보유 편입 결정")은
# 표가 아니라 산문이라 파싱 대상이 아니다. 표 행만 읽으므로 자연히 걸러지지만,
# 제목에 화살표/편입 같은 말이 있으면 아예 건너뛴다(오탐 방지).
SKIP_HEAD = re.compile(r"편입|딥다이브|→|전환|재돌파")


def _norm(cell: str) -> str:
    s = re.sub(r"\*\*|__|`|~~", "", cell).strip().lower()
    s = re.sub(r"\(워치\)|\(신규\)|\(매도[^)]*\)|\(비상장\)", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def to_ticker(cell: str):
    """표의 종목 셀 → 티커. 6자리 코드가 있으면 코드 우선(별칭 오매칭 방지)."""
    m = CODE_RE.search(cell)
    if m:
        code = m.group(1)
        return code + (".KQ" if code in KQ_CODES else ".KS")
    n = re.sub(r"\(.*?\)", "", _norm(cell)).strip()
    if not n:
        return None
    # 긴 별칭부터 맞춰야 '원익'이 '원익ips'를 가로채지 않는다.
    best = None
    for tk, aliases in NAMES.items():
        for a in aliases:
            if not a:
                continue
            if n == a or n.startswith(a) or a in n:
                if best is None or len(a) > best[1]:
                    best = (tk, len(a))
    return best[0] if best else None


def extract(unmapped_counter=None):
    """보고서 마크다운 전체 → 워치 콜 목록(날짜+종목 dedupe, 나중 파일 우선)."""
    seen, rows_raw = {}, 0
    for path in sorted(glob.glob(os.path.join(REPORTS, "report_v*.md"))):
        dm = DATE_RE.search(path)
        if not dm:
            continue
        day = dm.group(1)
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for hm in HEAD_RE.finditer(text):
            if SKIP_HEAD.search(hm.group(0)):
                continue
            seg = re.split(r"\n#{2,4}\s", text[hm.end():hm.end() + 8000])[0]
            for line in seg.splitlines():
                if not line.strip().startswith("|"):
                    continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) < 3 or set(cells[0]) <= set("-: "):
                    continue
                sm = None
                for c in cells[1:]:
                    sm = STAR_RE.search(c)
                    if sm:
                        break
                if not sm:
                    continue
                rows_raw += 1
                tk = to_ticker(cells[0])
                if not tk:
                    if unmapped_counter is not None:
                        unmapped_counter[cells[0][:28]] += 1
                    continue
                seen[(day, tk)] = {
                    "date": day,
                    "ticker": tk,
                    "stars": int(sm.group(1)),
                    "score": int(sm.group(2)) if sm.group(2) else None,
                    "source_report": os.path.basename(path),
                    "origin": "watch",
                }
    rows = sorted(seen.values(), key=lambda r: (r["date"], r["ticker"]))
    return rows, rows_raw


def main() -> int:
    ap = argparse.ArgumentParser(description="워치리스트 콜 원장화 (측정 전용)")
    ap.add_argument("--save", action="store_true", help="data/app/watch_calls.jsonl 생성·갱신")
    ap.add_argument("--unmapped", action="store_true", help="종목명 매핑 실패 목록")
    args = ap.parse_args()

    unmapped = Counter()
    rows, raw = extract(unmapped)

    tickers = Counter(r["ticker"] for r in rows)
    days = {r["date"] for r in rows}
    scored = sum(1 for r in rows if r["score"] is not None)

    print("=" * 64)
    print("  워치 콜 원장 — 버려지던 채점 표본 회수")
    print("=" * 64)
    print(f"  표에서 읽은 행 {raw} → dedupe 후 **{len(rows)}콜**")
    print(f"  고유 종목 {len(tickers)} · 고유 일자 {len(days)}")
    print(f"  스코어 동반 {scored}콜 ({scored / max(len(rows), 1) * 100:.0f}%) "
          f"— ⭐N/NN 표기가 최근 도입이라 **연속축은 워치로 못 늘린다**")
    if unmapped:
        miss = sum(unmapped.values())
        print(f"  ⚠️ 매핑 실패 {miss}행 ({miss / max(raw, 1) * 100:.1f}%)"
              + ("  — --unmapped 로 확인" if not args.unmapped else ""))

    # 보유 원장과 합쳤을 때의 독립 단위 — 이 도구의 존재 이유다.
    hold = os.path.join(ROOT, "data", "app", "calls_log.jsonl")
    if os.path.exists(hold):
        ht = set()
        for ln in open(hold, encoding="utf-8"):
            if ln.strip():
                try:
                    ht.add(json.loads(ln).get("ticker"))
                except json.JSONDecodeError:
                    pass
        ht.discard(None)
        union = ht | set(tickers)
        print(f"\n  독립 단위(클러스터) = 보유 {len(ht)} → 병합 **{len(union)}** "
              f"({len(union) / max(len(ht), 1):.2f}배)")
        print(f"  ↳ 별점 버킷 5개 기준 버킷당 종목 {len(ht) / 5:.1f} → {len(union) / 5:.1f}")

    print("\n  별점 분포:", dict(sorted(Counter(r["stars"] for r in rows).items(), reverse=True)))
    if args.unmapped:
        print("\n  매핑 실패 상위:")
        for k, v in unmapped.most_common(20):
            print(f"    {v:>4}회  {k}")

    if args.save:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        with open(LEDGER, "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\n  ✅ 저장: {os.path.relpath(LEDGER, ROOT)} ({len(rows)}행)")
    else:
        print("\n  (--save 없이는 원장을 쓰지 않는다)")

    print("\n※ 측정 전용 — 별점·스코어·트랜치 어떤 룰도 바꾸지 않는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
