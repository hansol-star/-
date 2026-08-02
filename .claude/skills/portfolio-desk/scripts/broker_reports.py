#!/usr/bin/env python3
"""broker_reports.py — 증권사 리서치 리포트 실제 수집·본문 추출·누적 (한경 컨센서스, 무키·stdlib)

정훈 지시(2026-07-30 "기관들 자료들도 실제로 다운받아서 분석도 해보고 우리 포트폴리오 종목
전부다"). 그리고 CLAUDE.md §데이터소스 [6/16 정훈 지침] "증권사/IB sell-side 리포트를 폭넓게·
유심히, 목표가 레인지·상향/하향 이력·양쪽 논거 명시, 단일 출처 금지".

**이전까지의 결함**: sell-side를 '우선하라'는 지침만 있고 **실제로 리포트를 읽은 적이 없었다.**
WebSearch로 기사에 인용된 목표가 숫자만 주웠다 — 기사는 리포트의 결론 한 줄만 옮기고
논거·가정·리스크는 버린다. 그래서 "왜 그 목표가인지"를 우리가 재현할 수 없었다.

**지금**: 한경 컨센서스가 국내 증권사 리포트 원문 PDF를 무료 공개한다.
  [7/30 실측] 목록 200 OK · PDF 818KB 5페이지 정상 수신 · read_doc.py로 한글 본문 완전 추출
  (사업부별 실적·컨센서스 상회 여부·가정까지 원문 그대로).

수집 구조 (정훈 "계속 누적하고 그 이전 자료들도 다 가져와서 학습" 지시 반영):
  · 목록 = 날짜·제목·**목표가·투자의견·애널리스트·증권사**가 정형 컬럼 → 컨센서스 하드넘버.
  · 본문 = PDF 다운로드 → read_doc.extract → 텍스트 캐시.
  · **append-only 인덱스** — 한 번 받은 리포트는 지우지 않는다. 목표가 상향/하향 이력이
    시계열로 쌓여야 "이 증권사가 언제 뷰를 바꿨나"를 추적할 수 있다.

저장: data/research/broker/index.json (메타 누적)
      data/research/broker/text/{idx}.txt (본문)
      data/research/broker/pdf/{idx}.pdf (--keep-pdf 일 때만)

⚠️ 리포트는 **해당 증권사의 견해**다. 우리 목표가·별점의 정본이 아니라 교차검증용 입력이며,
   복수 증권사 레인지와 상·하향 방향을 같이 봐야 한다(단일 출처 금지).

사용:
  python3 broker_reports.py --days 7                    # 최근 7일 우리 종목 리포트 목록
  python3 broker_reports.py --code 005930 --days 30
  python3 broker_reports.py --days 7 --fetch            # 본문까지 다운로드·추출·누적
  python3 broker_reports.py --targets                   # 종목별 목표가 컨센 레인지
  python3 broker_reports.py --show 651278               # 저장된 본문 보기
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
BASE_DIR = os.path.join(ROOT, "data", "research", "broker")
INDEX = os.path.join(BASE_DIR, "index.json")
TEXT_DIR = os.path.join(BASE_DIR, "text")
PDF_DIR = os.path.join(BASE_DIR, "pdf")

HOST = "https://consensus.hankyung.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# 보유 국내 5 + 국내 워치(반도체·전력 테마) — 6자리 코드로 필터
HOLDINGS = {"005930": "삼성전자", "066570": "LG전자", "454910": "두산로보틱스",
            "005380": "현대차", "035420": "NAVER"}
WATCH = {"000660": "SK하이닉스", "240810": "원익IPS", "095610": "테스",
         "009150": "삼성전기", "034020": "두산에너빌리티", "096770": "SK이노베이션",
         "012450": "한화에어로스페이스", "042660": "한화오션", "010140": "삼성중공업",
         "329180": "HD현대중공업"}
TRACKED = {**HOLDINGS, **WATCH}


def _get(url: str, referer: str | None = None, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": referer or f"{HOST}/analysis/list"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _num(s: str) -> float | None:
    s = (s or "").replace(",", "").strip()
    if not s or not re.match(r"^-?\d+(\.\d+)?$", s):
        return None
    return float(s)


def list_reports(sdate: str, edate: str, page: int = 1,
                 search: str | None = None) -> list[dict]:
    """한경 컨센서스 기업분석(CO) 목록 파싱.

    컬럼(실측): [0]작성일 [1]제목+종목코드+report_idx [2]목표가 [3]투자의견
                [4]애널리스트 [5]증권사

    ⚠️ `search_text`(종목명)로 **종목별 직접 검색**이 된다. 전체 목록을 페이지로 훑으면
    하루 200건 넘는 전체 리포트에 묻혀 우리 종목이 안 잡힌다(초기 구현에서 14일 조회에
    4건만 걸림 — 최근 하루치만 스캔된 것). 종목당 1콜이 정확하고 싸다.
    """
    q = {"sdate": sdate, "edate": edate, "report_type": "CO", "page": str(page)}
    if search:
        q["search_text"] = search
    url = f"{HOST}/analysis/list?{urllib.parse.urlencode(q)}"
    html = _get(url).decode("utf-8", "ignore")
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) < 6:
            continue
        date = _clean(tds[0])
        if not re.match(r"\d{4}-\d{2}-\d{2}", date):
            continue
        idx_m = re.search(r"report_idx=(\d+)", tr)
        title = _clean(tds[1])
        code_m = re.search(r"\((\d{6})\)", title)
        out.append({
            "date": date,
            "report_idx": idx_m.group(1) if idx_m else None,
            "title": re.sub(r"\s+", " ", title.split("(")[0]).strip() if code_m else title,
            "full_title": title,
            "code": code_m.group(1) if code_m else None,
            "target_price": _num(_clean(tds[2])),
            "rating": _clean(tds[3]),
            "analyst": _clean(tds[4]),
            "broker": _clean(tds[5]),
        })
    return out


def collect(days: int = 7, code: str | None = None, pages: int = 2) -> list[dict]:
    """추적 종목**별로** 검색해 기간 내 리포트를 모은다(중복 report_idx 제거)."""
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    targets = {code: TRACKED[code]} if code and code in TRACKED else TRACKED
    seen, rows = set(), []
    for c, name in targets.items():
        for p in range(1, pages + 1):
            try:
                batch = list_reports(start.isoformat(), end.isoformat(), p, search=name)
            except Exception as e:
                print(f"  ⚠️ {name} 조회 실패: {str(e)[:60]}", file=sys.stderr)
                break
            if not batch:
                break
            for r in batch:
                key = r.get("report_idx")
                # 검색어가 제목에 걸려도 종목코드가 우리 것이 아니면 버린다
                # (예: '삼성전자' 검색에 삼성전기 리포트가 딸려오는 경우)
                if not key or key in seen or r.get("code") != c:
                    continue
                seen.add(key)
                r["name"] = name
                r["held"] = c in HOLDINGS
                rows.append(r)
            time.sleep(0.4)
    return sorted(rows, key=lambda r: (r["date"], r["report_idx"]), reverse=True)


def fetch_body(idx: str, keep_pdf: bool = False) -> dict:
    """PDF 다운로드 → 본문 텍스트 추출. 이미 받은 건 캐시 재사용(누적·재다운로드 방지)."""
    os.makedirs(TEXT_DIR, exist_ok=True)
    tpath = os.path.join(TEXT_DIR, f"{idx}.txt")
    if os.path.exists(tpath):
        with open(tpath, encoding="utf-8") as f:
            return {"report_idx": idx, "text": f.read(), "cached": True}
    try:
        blob = _get(f"{HOST}/analysis/downpdf?report_idx={idx}", timeout=60)
    except Exception as e:
        return {"report_idx": idx, "_error": f"PDF 수신 실패: {str(e)[:70]}"}
    if not blob.startswith(b"%PDF"):
        return {"report_idx": idx, "_error": "PDF 아님(비공개 또는 만료)"}

    os.makedirs(PDF_DIR, exist_ok=True)
    ppath = os.path.join(PDF_DIR, f"{idx}.pdf")
    with open(ppath, "wb") as f:
        f.write(blob)
    try:
        import read_doc
        text = read_doc.extract(ppath)
    except Exception as e:
        text = ""
        err = str(e)[:70]
    else:
        err = None
    if not keep_pdf:
        try:
            os.remove(ppath)
        except OSError:
            pass
    if not text:
        return {"report_idx": idx, "_error": f"본문 추출 실패(스캔본 가능): {err}"}
    with open(tpath, "w", encoding="utf-8") as f:
        f.write(text)
    return {"report_idx": idx, "text": text, "cached": False, "chars": len(text)}


def load_index() -> dict:
    if os.path.exists(INDEX):
        try:
            with open(INDEX, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"updated": None, "reports": {}}


def save_index(rows: list[dict]) -> tuple[int, int]:
    """append-only 누적 — 기존 항목은 덮되 삭제하지 않는다(목표가 이력 보존)."""
    os.makedirs(BASE_DIR, exist_ok=True)
    db = load_index()
    before = len(db["reports"])
    for r in rows:
        db["reports"][r["report_idx"]] = r
    db["updated"] = dt.date.today().isoformat()
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    return len(db["reports"]) - before, len(db["reports"])


def target_consensus() -> list[dict]:
    """누적 인덱스에서 종목별 목표가 레인지·최신 방향 산출."""
    db = load_index()
    by_code: dict[str, list[dict]] = {}
    for r in db["reports"].values():
        if r.get("target_price"):
            by_code.setdefault(r["code"], []).append(r)
    out = []
    for code, rs in by_code.items():
        rs.sort(key=lambda x: x["date"])
        tps = [r["target_price"] for r in rs]
        latest = rs[-1]
        # 같은 증권사의 직전 목표가와 비교해 상향/하향 판정
        moves = []
        seen: dict[str, float] = {}
        for r in rs:
            prev = seen.get(r["broker"])
            if prev and abs(r["target_price"] - prev) > 1:
                moves.append((r["date"], r["broker"],
                              "상향" if r["target_price"] > prev else "하향",
                              prev, r["target_price"]))
            seen[r["broker"]] = r["target_price"]
        out.append({
            "code": code, "name": TRACKED.get(code, code), "held": code in HOLDINGS,
            "n": len(rs), "low": min(tps), "high": max(tps),
            "median": sorted(tps)[len(tps) // 2],
            "latest_date": latest["date"], "latest_broker": latest["broker"],
            "latest_target": latest["target_price"], "latest_rating": latest["rating"],
            "recent_moves": moves[-4:],
        })
    return sorted(out, key=lambda x: (not x["held"], x["name"]))


def main() -> int:
    ap = argparse.ArgumentParser(description="증권사 리포트 수집·본문추출·누적")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--code", "--tickers", help="6자리 종목코드")
    ap.add_argument("--fetch", action="store_true", help="PDF 본문까지 다운로드·추출")
    ap.add_argument("--keep-pdf", action="store_true")
    ap.add_argument("--targets", action="store_true", help="누적분에서 목표가 컨센 산출")
    ap.add_argument("--show", help="저장된 본문 출력 (report_idx)")
    ap.add_argument("--limit", type=int, default=12, help="--fetch 시 최대 건수")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.show:
        p = os.path.join(TEXT_DIR, f"{a.show}.txt")
        if not os.path.exists(p):
            print(f"❌ 본문 없음: {a.show} (--fetch 로 먼저 수집)")
            return 1
        with open(p, encoding="utf-8") as f:
            print(f.read())
        return 0

    if a.targets:
        rows = target_consensus()
        if a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
            return 0
        db = load_index()
        print(f"\n📊 목표가 컨센서스 (누적 리포트 {len(db['reports'])}건 기준)")
        print(" 종목            보유  n   최저      중앙      최고    최신(증권사·의견)")
        for r in rows:
            print(f" {r['name']:<14} {'●' if r['held'] else '○'}  {r['n']:>2}"
                  f" {r['low']:>9,.0f} {r['median']:>9,.0f} {r['high']:>9,.0f}"
                  f"   {r['latest_target']:>9,.0f} {r['latest_broker']} {r['latest_rating']}")
            for d, b, dirn, o, n in r["recent_moves"]:
                icon = "🔺" if dirn == "상향" else "🔻"
                print(f"      {icon} {d} {b} {o:,.0f} → {n:,.0f}")
        return 0

    rows = collect(a.days, a.code)
    if not rows:
        print(f"최근 {a.days}일 우리 추적 종목 리포트 없음.")
        return 0

    if a.fetch:
        got = 0
        for r in rows[:a.limit]:
            res = fetch_body(r["report_idx"], a.keep_pdf)
            if res.get("_error"):
                r["body_error"] = res["_error"]
            else:
                r["body_chars"] = len(res["text"])
                r["cached"] = res.get("cached")
                got += 1
            time.sleep(0.8)
        added, total = save_index(rows)
        print(f"📥 본문 확보 {got}건 · 인덱스 신규 {added}건 (누적 {total}건)")

    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0

    print(f"\n📄 최근 {a.days}일 우리 종목 증권사 리포트 {len(rows)}건")
    print(" 날짜        보유 종목          목표가     의견    증권사        제목")
    for r in rows:
        tp = f"{r['target_price']:,.0f}" if r["target_price"] else "—"
        mark = "●" if r["held"] else "○"
        body = ""
        if r.get("body_chars"):
            body = f"  📄{r['body_chars']//1000}k"
        elif r.get("body_error"):
            body = f"  ⚠️{r['body_error'][:20]}"
        print(f" {r['date']}  {mark}  {r['name']:<12} {tp:>9}  {r['rating']:<6}"
              f" {r['broker']:<12} {r['full_title'][:34]}{body}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
