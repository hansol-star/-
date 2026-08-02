#!/usr/bin/env python3
"""naver_flows.py — 외인·기관·개인 수급 자동 수집 (네이버 증권 무키 JSON·stdlib)

정훈 질문(2026-07-21): "그럼 지금은 외인·기관이 얼마나 수급하는지 어떻게 알아?"
→ 그동안은 국장 데스크가 매 보고서 때 WebSearch로 확정 순매수를 손으로 flows.json에
기입(그래서 22~27일치뿐). KRX 공식 API는 데이터센터 IP에서 400/LOGOUT(세션·IP 가드)로
막힘. **뚫은 소스 = 네이버 모바일 증권 API(무키 JSON, 데이터센터서 정상)**:

  ① 시장 전체(코스피·코스닥) 투자자 순매수 **억원** — flows.json이 손으로 적던 그 값.
     `m.stock.naver.com/api/index/{KOSPI|KOSDAQ}/trend`  (당일 1건 → 매일 자동 갱신용)
  ② 종목별 외인/기관/개인 순매수 **수량** + 외인보유율 — 커서 페이징으로 깊은 이력.
     `m.stock.naver.com/api/stock/{code}/trend?pageSize=60&bizdate=YYYYMMDD`
     **보유 유니버스 밖 임의 종목도 조회된다**(--stock/--code/--tickers).
     ⚠️ `page=N`은 네이버가 무시한다 — 커서는 `bizdate`. 8/2 이전엔 이걸 몰라 --pages가
     무동작이었고 60일치를 240일치로 착각했다(침묵 고장).

조회 전용·stdlib. 값은 참고(네이버 표기), 확정 대사는 KRX 발표와 교차 권장.

사용:
  python3 naver_flows.py                      # 코스피·코스닥 당일 + 보유 국내5 종목별 최근
  python3 naver_flows.py --market             # 코스피·코스닥 당일 순매수(억원)만
  python3 naver_flows.py --stock 000660 --pages 4   # SK하이닉스 외인/기관 이력(240일)
  python3 naver_flows.py --stock 080520 --pages 5 --summary   # 임의 종목 구간 누적 요약
  python3 naver_flows.py --flows-line         # flows.json series 항목 형식으로 오늘 코스피 출력
  python3 naver_flows.py --json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
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
    """종목별 외인/기관/개인 순매수(수량) + 외인보유율. 커서 페이징(최신 뒤→앞).

    ⚠️ [8/2 무동작 수정] 구버전은 `&page=N`으로 페이징한다고 믿었지만 **네이버는 그 파라미터를
    무시한다** — page 1·2·3이 전부 같은 60건을 돌려주고, dedup이 그걸 삼켜서 `--pages 4`가
    조용히 60일치만 내놓았다(요청 3회·대기 1.8초는 그대로 낭비). 실패가 아니라 '그럴듯한 값'을
    반환해서 아무도 눈치채지 못한 종류의 침묵 고장이다.
    실제 커서는 **`bizdate=YYYYMMDD`** — 그 날짜 **미만**의 60건을 준다. 직전 배치의 가장 오래된
    날짜를 커서로 넘기면 겹침·구멍 없이 이어진다([8/2 실측] 5배치 300건 고유, 2025-05~2026-07).
    ※ pageSize는 60이 상한(200은 빈 응답).
    """
    out: list[dict] = []
    cursor: str | None = None
    for _ in range(max(1, pages)):
        q = "trend?pageSize=60" + (f"&bizdate={cursor}" if cursor else "")
        arr = _get(f"{BASE}/stock/{code}/{q}")
        if not isinstance(arr, list) or not arr:
            break
        dates = [str(r.get("bizdate") or "") for r in arr if r.get("bizdate")]
        if not dates:
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
        nxt = min(dates)
        if cursor is not None and nxt >= cursor:
            break            # 커서가 안 물러나면 더 캘 게 없다(무한루프 방지)
        cursor = nxt
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


def summarize(rows: list[dict]) -> dict:
    """일별 수급 → 구간 누적 요약. 딥다이브에서 '기관이 들어와 있나'를 한눈에 보려는 용도.

    소형주에서 결정적인 건 순매수 부호가 아니라 **기관 참여 자체**다. 기관 순매수가
    대부분의 날 정확히 0이면 그건 '중립'이 아니라 **기관이 이 종목을 안 본다**는 뜻이고,
    저평가가 해소될 경로가 없다는 신호다. 그래서 참여일수를 같이 낸다.
    """
    def blk(sub: list[dict]) -> dict:
        if not sub:
            return {}
        f = sum(r["foreign_qty"] or 0 for r in sub)
        i = sum(r["organ_qty"] or 0 for r in sub)
        p = sum(r["indiv_qty"] or 0 for r in sub)
        holds = [r["foreign_hold_pct"] for r in sub if r["foreign_hold_pct"] is not None]
        return {
            "days": len(sub), "from": sub[0]["date"], "to": sub[-1]["date"],
            "foreign": int(f), "inst": int(i), "indiv": int(p),
            "inst_active_days": sum(1 for r in sub if (r["organ_qty"] or 0) != 0),
            "fhold_from": holds[0] if holds else None,
            "fhold_to": holds[-1] if holds else None,
        }
    return {lab: blk(rows[-n:] if n else rows)
            for lab, n in (("20d", 20), ("60d", 60), ("all", 0))}


def render_summary(code: str, rows: list[dict]) -> None:
    s = summarize(rows)
    px0, px1 = rows[0]["close"], rows[-1]["close"]
    print(f"■ {code} 수급 요약 — {rows[0]['date']} ~ {rows[-1]['date']} ({len(rows)}일)")
    print(f"   종가 {px0:,.0f} → {px1:,.0f}  ({(px1/px0-1)*100:+.1f}%)")
    print(f"{'구간':<6}{'일수':>5}{'외인(주)':>13}{'기관(주)':>13}{'개인(주)':>13}"
          f"{'기관참여':>10}{'외인보유%':>14}")
    for lab in ("20d", "60d", "all"):
        b = s[lab]
        if not b:
            continue
        fh = ("—" if b["fhold_from"] is None
              else f"{b['fhold_from']:.2f}→{b['fhold_to']:.2f}")
        print(f"{lab:<6}{b['days']:>5}{b['foreign']:>13,}{b['inst']:>13,}{b['indiv']:>13,}"
              f"{b['inst_active_days']:>7}/{b['days']:<3}{fh:>14}")
    a = s["all"]
    if a and a["inst_active_days"] / max(1, a["days"]) < 0.25:
        print(f"   ⚠️ 기관 참여 {a['inst_active_days']}/{a['days']}일 — 기관이 사실상 부재. "
              f"저평가 해소 주체가 없다는 뜻(측정치일 뿐, 매매 신호 아님).")


def main() -> int:
    ap = argparse.ArgumentParser(description="외인·기관·개인 수급 수집 (네이버 무키·조회전용)")
    ap.add_argument("--market", action="store_true", help="코스피·코스닥 당일 순매수(억원)만")
    ap.add_argument("--stock", "--code", "--tickers", metavar="CODE",
                    help="종목코드(6자리) 외인/기관 이력. 보유 유니버스 밖 임의 종목도 가능")
    ap.add_argument("--pages", type=int, default=2, help="종목 이력 페이지수(60일/페이지·커서 페이징)")
    ap.add_argument("--summary", action="store_true",
                    help="--stock 일별 덤프 대신 구간 누적 요약(딥다이브용)")
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
        if not rows:
            print(f"종목 {args.stock} 수급 데이터 없음 — 종목코드(6자리) 확인", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps({"code": args.stock, "summary": summarize(rows), "rows": rows},
                             ensure_ascii=False, indent=1))
            return 0
        if args.summary:
            render_summary(args.stock, rows)
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
