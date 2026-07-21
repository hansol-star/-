#!/usr/bin/env python3
"""naver_flows.py — 외인·기관·개인 수급 자동 수집 (네이버 증권 무키 JSON·stdlib)

정훈 질문(2026-07-21): "그럼 지금은 외인·기관이 얼마나 수급하는지 어떻게 알아?"
→ 그동안은 국장 데스크가 매 보고서 때 WebSearch로 확정 순매수를 손으로 flows.json에
기입(그래서 22~27일치뿐). KRX 공식 API는 데이터센터 IP에서 400/LOGOUT(세션·IP 가드)로
막힘. **뚫은 소스 = 네이버 모바일 증권 API(무키 JSON, 데이터센터서 정상)**:

  ① 시장 전체(코스피·코스닥) 투자자 순매수 **억원** — flows.json이 손으로 적던 그 값.
     `m.stock.naver.com/api/index/{KOSPI|KOSDAQ}/trend`  (당일 1건 → 매일 자동 갱신용)
  ② 종목별 외인/기관/개인 순매수 **수량** + 외인보유율 — 페이징으로 깊은 이력.
     `m.stock.naver.com/api/stock/{code}/trend?pageSize=100&page=N`  (하닉 매도중단 트리거 등)

조회 전용·stdlib. 값은 참고(네이버 표기), 확정 대사는 KRX 발표와 교차 권장.

사용:
  python3 naver_flows.py                      # 코스피·코스닥 당일 + 보유 국내5 종목별 최근
  python3 naver_flows.py --market             # 코스피·코스닥 당일 순매수(억원)만
  python3 naver_flows.py --stock 000660 --pages 4   # SK하이닉스 외인/기관 이력
  python3 naver_flows.py --flows-line         # flows.json series 항목 형식으로 오늘 코스피 출력
  python3 naver_flows.py --json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile Safari"
BASE = "https://m.stock.naver.com/api"

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", "data"))
FLOW_DIR = os.path.join(_DATA, "history", "flows")          # 종목별 수급 롤링 누적
MARKET_JSONL = os.path.join(_DATA, "history", "market_flows.jsonl")  # 시장 억원 누적
FLOWS_JSON = os.path.join(_DATA, "app", "flows.json")       # 기존 확정 시드

# 보유 국내 5 (라벨·6자리코드) — market_data/portfolio.json 정본과 동일
KR_HOLDINGS = [
    ("삼성전자", "005930"), ("LG전자", "066570"), ("두산로보틱스", "454910"),
    ("현대차", "005380"), ("NAVER", "035420"),
]
# 수급 트리거 감시(하닉 매도중단 게이트 — CLAUDE.md foreign_hynix)
WATCH = [("SK하이닉스", "000660")]


def _get(url: str, tries: int = 4):
    delay = 2.0
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                         "Referer": "https://m.stock.naver.com/"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
            if i < tries - 1:
                time.sleep(delay)
                delay *= 1.8
    return None


def _num(s):
    """'+1,943,936' → 1943936 · '-16,421' → -16421 · '46.62%' → 46.62 · None 안전."""
    if s is None:
        return None
    s = str(s).replace(",", "").replace("%", "").strip()
    if s in ("", "-", "+"):
        return None
    try:
        return float(s) if "." in s else int(s)
    except ValueError:
        return None


def _fmt_date(yyyymmdd: str) -> str:
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}" if yyyymmdd and len(yyyymmdd) == 8 else yyyymmdd


def market(index: str = "KOSPI") -> dict | None:
    """시장 전체 당일 투자자 순매수(억원). index=KOSPI|KOSDAQ."""
    d = _get(f"{BASE}/index/{index}/trend")
    if not isinstance(d, dict):
        return None
    return {
        "index": index, "date": _fmt_date(d.get("bizdate", "")),
        "foreign": _num(d.get("foreignValue")),      # 억원
        "inst": _num(d.get("institutionalValue")),
        "indiv": _num(d.get("personalValue")),
        "unit": "억원",
    }


def stock_flows(code: str, pages: int = 2) -> list[dict]:
    """종목별 외인/기관/개인 순매수(수량) + 외인보유율. 페이징 이력(최신 뒤→앞)."""
    out = []
    for p in range(1, pages + 1):
        arr = _get(f"{BASE}/stock/{code}/trend?pageSize=60&page={p}")  # 60=네이버 상한(100은 400)
        if not isinstance(arr, list) or not arr:
            break
        for r in arr:
            out.append({
                "date": _fmt_date(r.get("bizdate", "")),
                "close": _num(r.get("closePrice")),
                "foreign_qty": _num(r.get("foreignerPureBuyQuant")),
                "organ_qty": _num(r.get("organPureBuyQuant")),
                "indiv_qty": _num(r.get("individualPureBuyQuant")),
                "foreign_hold_pct": _num(r.get("foreignerHoldRatio")),
            })
        time.sleep(0.6)  # 페이싱
    # 중복 제거·시간순
    seen, dedup = set(), []
    for r in sorted(out, key=lambda x: x["date"]):
        if r["date"] not in seen:
            seen.add(r["date"])
            dedup.append(r)
    return dedup


# ---------- 누적 캐시 (롤링 60일 창을 매일 저장 → 시간이 갈수록 60일 너머 축적) ----------
def cache_stock(code: str, label: str, pages: int = 1) -> tuple[int, int]:
    """종목별 수급(~60일 창)을 data/history/flows/<code>.csv에 병합 저장. (총일수, 신규)."""
    os.makedirs(FLOW_DIR, exist_ok=True)
    path = os.path.join(FLOW_DIR, f"{code}.csv")
    old = {}
    if os.path.exists(path):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                old[row["date"]] = row
    fresh = stock_flows(code, pages)
    added = 0
    for r in fresh:
        if r["date"] not in old:
            added += 1
        old[r["date"]] = {"date": r["date"], "close": r["close"],
                          "foreign_qty": r["foreign_qty"], "organ_qty": r["organ_qty"],
                          "indiv_qty": r["indiv_qty"], "foreign_hold_pct": r["foreign_hold_pct"]}
    rows = [old[d] for d in sorted(old)]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "close", "foreign_qty", "organ_qty",
                                          "indiv_qty", "foreign_hold_pct"])
        w.writeheader()
        w.writerows(rows)
    return len(rows), added


def _seed_market_from_flows_json() -> dict:
    """기존 flows.json 확정 27일을 시장누적 시드로(중복 방지). {date: rec}."""
    out = {}
    if os.path.exists(FLOWS_JSON):
        try:
            fj = json.load(open(FLOWS_JSON, encoding="utf-8"))
            for s in fj.get("series", []):
                if s.get("foreign") is not None:
                    out[s["date"]] = {"date": s["date"], "index": "KOSPI",
                                      "foreign": s["foreign"], "inst": s.get("inst"),
                                      "indiv": s.get("indiv"), "src": "flows.json(확정)"}
        except (OSError, ValueError):
            pass
    return out


def append_market() -> str:
    """오늘 코스피·코스닥 시장 순매수(억원)를 market_flows.jsonl에 누적(dedup date+index)."""
    existing = {}
    if os.path.exists(MARKET_JSONL):
        with open(MARKET_JSONL, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    existing[(r["date"], r["index"])] = r
    # 시드(코스피 확정) — 없을 때만
    for d, r in _seed_market_from_flows_json().items():
        existing.setdefault((d, "KOSPI"), r)
    added = 0
    for idx in ("KOSPI", "KOSDAQ"):
        m = market(idx)
        if m and m["date"]:
            key = (m["date"], idx)
            if key not in existing:
                added += 1
            existing[key] = {"date": m["date"], "index": idx, "foreign": m["foreign"],
                             "inst": m["inst"], "indiv": m["indiv"], "src": "naver"}
        time.sleep(0.5)
    os.makedirs(os.path.dirname(MARKET_JSONL), exist_ok=True)
    rows = [existing[k] for k in sorted(existing, key=lambda x: (x[0], x[1]))]
    with open(MARKET_JSONL, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    kdays = sum(1 for r in rows if r["index"] == "KOSPI")
    return f"시장누적: 코스피 {kdays}일 (총 {len(rows)}행, +{added} today)"


def main() -> int:
    ap = argparse.ArgumentParser(description="외인·기관·개인 수급 수집 (네이버 무키·조회전용)")
    ap.add_argument("--market", action="store_true", help="코스피·코스닥 당일 순매수(억원)만")
    ap.add_argument("--stock", metavar="CODE", help="종목코드(6자리) 외인/기관 이력")
    ap.add_argument("--pages", type=int, default=2, help="종목 이력 페이지수(100일/페이지)")
    ap.add_argument("--flows-line", action="store_true", help="flows.json series 형식으로 오늘 코스피")
    ap.add_argument("--backfill", action="store_true",
                    help="종목별 롤링60일 캐시 + 시장 억원 누적(매일 실행 → 60일 너머 축적)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.backfill:
        print("■ 수급 누적 캐시 (롤링 60일 창을 디스크에 병합 — 시간이 갈수록 60일 너머 축적)")
        for label, code in KR_HOLDINGS + WATCH:
            tot, add = cache_stock(code, label)
            print(f"  {label:<12}{code}  총 {tot}일 (+{add})")
            time.sleep(0.6)
        print("  " + append_market())
        return 0

    if args.flows_line:
        m = market("KOSPI")
        if m:
            print(json.dumps({"date": m["date"], "foreign": m["foreign"], "inst": m["inst"],
                              "indiv": m["indiv"], "note": "네이버 자동수집(KRX 확정 대사 권장)"},
                             ensure_ascii=False))
        return 0

    if args.stock:
        rows = stock_flows(args.stock, args.pages)
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
            return 0
        print(f"종목 {args.stock} 수급(수량·최근 {len(rows)}일) — 외인/기관/개인 순매수 + 외인보유%")
        print(f"{'날짜':<12}{'종가':>9}{'외인':>11}{'기관':>11}{'개인':>11}{'외인보유%':>9}")
        for r in rows[-20:]:
            print(f"{r['date']:<12}{str(r['close']):>9}{str(r['foreign_qty']):>11}"
                  f"{str(r['organ_qty']):>11}{str(r['indiv_qty']):>11}{str(r['foreign_hold_pct']):>9}")
        return 0

    # 기본/--market: 시장 전체 + (기본이면 보유 종목별 최신)
    mkts = [market("KOSPI"), market("KOSDAQ")]
    if args.json:
        out = {"market": mkts}
        if not args.market:
            out["holdings"] = {c: (stock_flows(c, 1)[-1:] or [{}])[-1]
                               for _, c in KR_HOLDINGS + WATCH}
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0

    print("■ 시장 전체 투자자 순매수 (억원·네이버 자동수집)")
    print(f"{'시장':<8}{'날짜':<12}{'외인':>10}{'기관':>10}{'개인':>10}")
    for m in mkts:
        if m:
            print(f"{m['index']:<8}{m['date']:<12}{str(m['foreign']):>10}{str(m['inst']):>10}{str(m['indiv']):>10}")
    if not args.market:
        print("\n■ 보유 국내 + 하닉 — 당일 외인/기관 순매수(수량)·외인보유%")
        print(f"{'종목':<12}{'외인':>11}{'기관':>11}{'외인보유%':>9}")
        for label, code in KR_HOLDINGS + WATCH:
            rows = stock_flows(code, 1)
            if rows:
                r = rows[-1]
                print(f"{label:<12}{str(r['foreign_qty']):>11}{str(r['organ_qty']):>11}{str(r['foreign_hold_pct']):>9}")
            time.sleep(0.4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
