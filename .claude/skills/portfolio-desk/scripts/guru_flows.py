#!/usr/bin/env python3
"""guru_flows.py — 주식 대가 13F 보유변동 자동 수집 (SEC EDGAR 무키 JSON/XML·stdlib)

정훈 지시(2026-07-23): "워런버핏 같은 주식 대가들의 흐름도 알아보자 — 데이터를 무겁게
다 가져와서 분석해, 대가들이 그렇게 결정하는 '이유'를 보고 우리가 참고할 걸 찾자."

이 스크립트는 **팩트 레이어**만 담당한다(무엇을·얼마나·언제·궤적·우리종목 겹침).
'왜(rationale)'와 '우리 참고점(our_takeaway)'은 guru-flow-desk 서브에이전트가
버크셔 주주서한·외신·sell-side를 WebSearch로 캐서 채운다(스크립트는 추측 금지).

소스(무키 공개, User-Agent 필수 — SEC 요건):
  ① 파일러 제출목록: data.sec.gov/submissions/CIK##########.json  (13F-HR accession 추출)
  ② 파일링 인덱스:   www.sec.gov/Archives/edgar/data/<CIK>/<ACC>/index.json
  ③ 정보표(보유):    같은 폴더의 *infotable* XML (informationTable 네임스페이스)

⚠️ 단위 주의: SEC는 2023-01-03부터 13F value 단위를 '천달러 → 달러'로 변경.
   filingDate 연도로 스케일 보정(2023 이전 = ×1000).

사용:
  python3 guru_flows.py                       # 버크셔 최신분기 표(상위·최대변동·우리겹침)
  python3 guru_flows.py --quarters 8          # 최근 8분기 궤적까지
  python3 guru_flows.py --cik 0001067983      # 특정 파일러
  python3 guru_flows.py --json                # 구조화 JSON stdout(데스크/파이프라인용)
  python3 guru_flows.py --emit                # data/app/guru_flows.json 정본 갱신(팩트만)
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
# SEC는 식별 가능한 UA(이메일형 연락처 포함)를 요구한다 — 없으면 403. 무키.
UA = "jeonghun-portfolio-desk research jeonghun.desk@gmail.com"
CAFILE = os.environ.get("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt"

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", "data"))
GURU_JSON = os.path.join(_DATA, "app", "guru_flows.json")

# 추적 대가 레지스트리 — CIK만 추가하면 확장. 시각이 갈리는 6인(가치·역발상·매크로·집중·행동).
# ⚠️ Bridgewater(700+종목 시스템 분산)는 개별 '왜'가 없어 의도적 제외.
GURUS = {
    "berkshire":   {"cik": "0001067983", "name": "Berkshire Hathaway (Warren Buffett)",
                    "style": "가치·현금·AI는 알파벳 집중"},
    "scion":       {"cik": "0001649339", "name": "Scion Asset Management (Michael Burry)",
                    "style": "역발상·베어·풋옵션 — AI 회의론"},
    "duquesne":    {"cik": "0001536411", "name": "Duquesne Family Office (Stanley Druckenmiller)",
                    "style": "매크로·모멘텀 — AI 사이클 타이밍"},
    "pershing":    {"cik": "0001336528", "name": "Pershing Square (Bill Ackman)",
                    "style": "집중·퀄리티 컴파운더"},
    "appaloosa":   {"cik": "0001656456", "name": "Appaloosa (David Tepper)",
                    "style": "테크·중국·경기민감 밸류"},
    "thirdpoint":  {"cik": "0001040273", "name": "Third Point (Daniel Loeb)",
                    "style": "행동주의·테크 재편"},
}

# CUSIP → 정훈 보유·워치 티커(겹침 특정용). 미매핑은 발행사명으로 노출.
HOLDINGS_CUSIP = {
    "037833100": "AAPL",
    "02079K305": "GOOGL", "02079K107": "GOOGL",   # Alphabet C/A
    "67066G104": "NVDA", "30303M102": "META", "594918104": "MSFT",
    "68389X105": "ORCL", "040413106": "ANET", "595112103": "MU", "11135F101": "AVGO",
    "88160R101": "TSLA", "872590104": "TMUS", "36328W109": "GEV",
}


def _ctx():
    try:
        return ssl.create_default_context(cafile=CAFILE)
    except Exception:
        return ssl.create_default_context()


def _get(url: str, tries: int = 4):
    """무키 GET(gzip 대응·백오프). 실패 시 예외를 올려 호출부에서 error dict로 감싼다."""
    delay = 1.5
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate",
                              "Accept": "application/json, text/xml, */*"})
            with urllib.request.urlopen(req, timeout=25, context=_ctx()) as r:
                data = r.read()
                if r.headers.get("Content-Encoding", "") == "gzip":
                    data = gzip.decompress(data)
                return data
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            if i < tries - 1:
                time.sleep(delay)
                delay *= 2
    raise last if last else RuntimeError("unknown fetch error")


def _lname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _num(x) -> int:
    try:
        return int(float((x or "0").strip()))
    except (ValueError, AttributeError):
        return 0


def _autoscale_value(holdings: dict) -> None:
    """13F value 단위(달러 vs 천달러)를 내재가격(value/shares) 중앙값으로 자동 판정.
    SEC 2023 '달러 단위' 규칙에도 일부 파일러(예: Duquesne)는 여전히 천달러로 제출 →
    종목값이 실주가의 1/1000. filingDate 기반 추정은 오판하므로 데이터로 판정."""
    implied = [h["value"] / h["shares"] for h in holdings.values()
               if h["shares"] > 0 and h["value"] > 0]
    if not implied:
        return
    implied.sort()
    med = implied[len(implied) // 2]
    if med < 1.0:   # 실주가로 보기엔 1000배 작음 → 천달러 단위 → 달러로 승격
        for h in holdings.values():
            h["value"] *= 1000


def list_13f(cik: str, limit: int = 8):
    """제출목록에서 최근 13F-HR(및 /A) 파일링 메타를 최신순으로 반환."""
    cik10 = str(cik).zfill(10)
    body = _get(f"https://data.sec.gov/submissions/CIK{cik10}.json")
    j = json.loads(body.decode("utf-8", "replace"))
    name = j.get("name", "")
    rec = j["filings"]["recent"]
    forms, accs = rec["form"], rec["accessionNumber"]
    fdates, rdates = rec["filingDate"], rec.get("reportDate", [""] * len(forms))
    by_report = {}
    for i, f in enumerate(forms):
        if f not in ("13F-HR", "13F-HR/A"):
            continue
        by_report.setdefault(rdates[i], []).append(
            {"form": f, "accession": accs[i], "filing_date": fdates[i],
             "report_date": rdates[i]})
    chosen = []
    for rd, cands in by_report.items():
        # 원본 13F-HR 우선(부분 정정 /A가 전체 포트를 덮어써 종목이 사라지는 것 방지),
        # 같은 폼이면 최신 제출.
        cands.sort(key=lambda c: (c["form"] == "13F-HR", c["filing_date"]), reverse=True)
        chosen.append(cands[0])
    chosen.sort(key=lambda c: c["report_date"], reverse=True)
    return name, chosen[:limit]


def fetch_infotable(cik: str, accession: str, filing_date: str):
    """파일링 폴더의 정보표 XML을 파싱해 CUSIP 단위로 집계한 보유 스냅샷 반환."""
    cik_num = str(int(cik))
    acc_nodash = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_nodash}"
    idx = json.loads(_get(f"{base}/index.json").decode("utf-8", "replace"))
    files = [it["name"] for it in idx.get("directory", {}).get("item", [])]
    # 정보표 XML 후보: primary_doc(표지) 제외한 .xml 중 informationTable 포함.
    xmls = [f for f in files if f.lower().endswith(".xml") and "primary_doc" not in f.lower()]
    xmls += [f for f in files if f.lower().endswith(".xml") and f not in xmls]  # 폴백
    for fn in xmls:
        try:
            raw = _get(f"{base}/{fn}")
            root = ET.fromstring(raw)
        except (ET.ParseError, urllib.error.HTTPError):
            continue
        holdings, options, saw = {}, 0, False
        for el in root.iter():
            if _lname(el.tag) != "infoTable":
                continue
            saw = True
            d = {}
            for ch in el.iter():
                n = _lname(ch.tag)
                if n in ("nameOfIssuer", "titleOfClass", "cusip", "value",
                         "sshPrnamt", "putCall"):
                    d[n] = (ch.text or "").strip()
            cusip = (d.get("cusip") or "").upper()
            if not cusip:
                continue
            if d.get("putCall"):        # 옵션 포지션은 별도 카운트(주식 궤적 왜곡 방지 — 단 버리류 풋은 신호)
                options += 1
                continue
            h = holdings.setdefault(cusip, {"issuer": d.get("nameOfIssuer", ""),
                                            "value": 0, "shares": 0})
            h["value"] += _num(d.get("value"))
            h["shares"] += _num(d.get("sshPrnamt"))
        # infoTable을 봤으면(전부 옵션이라 holdings 비어도) 유효 스냅샷 반환 — 옵션중심 파일러(Scion) 대응.
        if saw:
            _autoscale_value(holdings)   # 달러/천달러 단위 자동 판정·보정
            total = sum(h["value"] for h in holdings.values())
            return {"holdings": holdings, "total_value": total,
                    "positions": len(holdings), "option_lines": options, "xml": fn}
    return {"holdings": {}, "total_value": 0, "positions": 0, "option_lines": 0,
            "error": "info table not found/parsed"}


def _action(prev_sh: int, cur_sh: int) -> str:
    if prev_sh == 0 and cur_sh > 0:
        return "NEW"
    if cur_sh == 0 and prev_sh > 0:
        return "EXIT"
    if cur_sh > prev_sh:
        return "ADD"
    if cur_sh < prev_sh:
        return "TRIM"
    return "HOLD"


def diff_quarters(cur: dict, prev: dict):
    """cur vs prev 보유를 CUSIP로 대사해 변동 리스트 반환(최신 스냅샷 기준)."""
    ch, ph = cur.get("holdings", {}), prev.get("holdings", {})
    moves = []
    for cusip in set(ch) | set(ph):
        cs = ch.get(cusip, {}).get("shares", 0)
        ps = ph.get(cusip, {}).get("shares", 0)
        act = _action(ps, cs)
        if act == "HOLD":
            continue
        issuer = (ch.get(cusip) or ph.get(cusip) or {}).get("issuer", "")
        delta_pct = None
        if ps > 0 and cs > 0:
            delta_pct = round((cs - ps) / ps * 100, 1)
        moves.append({
            "cusip": cusip, "issuer": issuer, "ticker": HOLDINGS_CUSIP.get(cusip),
            "action": act, "shares_from": ps, "shares_to": cs,
            "shares_delta_pct": delta_pct,
            "value_to": ch.get(cusip, {}).get("value", 0),
        })
    # 정렬: 신규/청산 우선, 그다음 최신 비중 큰 순.
    rank = {"NEW": 0, "EXIT": 1, "ADD": 2, "TRIM": 3}
    moves.sort(key=lambda m: (rank.get(m["action"], 9), -m["value_to"]))
    return moves


def top_positions(snap: dict, n: int = 12):
    tot = snap.get("total_value", 0) or 1
    rows = []
    for cusip, h in snap.get("holdings", {}).items():
        rows.append({"cusip": cusip, "issuer": h["issuer"], "ticker": HOLDINGS_CUSIP.get(cusip),
                     "value_usd": h["value"], "shares": h["shares"],
                     "pct": round(h["value"] / tot * 100, 2)})
    rows.sort(key=lambda r: -r["value_usd"])
    return rows[:n]


def build_trajectory(snaps: list, cusips: set):
    """관심 CUSIP(우리 겹침 + 최신 상위)의 분기별 주식수·비중 궤적."""
    traj = {}
    for cusip in cusips:
        series = []
        for s in snaps:
            h = s["snap"].get("holdings", {}).get(cusip)
            tot = s["snap"].get("total_value", 0) or 1
            series.append({
                "quarter": s["meta"]["report_date"],
                "shares": h["shares"] if h else 0,
                "pct": round(h["value"] / tot * 100, 2) if h else 0.0,
            })
        series.sort(key=lambda x: x["quarter"])  # 오래된→최신(분기 정렬)
        issuer = next((s["snap"]["holdings"][cusip]["issuer"]
                       for s in snaps if cusip in s["snap"].get("holdings", {})), "")
        traj[cusip] = {"issuer": issuer, "ticker": HOLDINGS_CUSIP.get(cusip),
                       "series": series}
    return traj


def collect(cik: str, quarters: int = 4):
    """한 대가의 다분기 13F를 수집·분석해 구조화 dict 반환."""
    try:
        name, filings = list_13f(cik, limit=quarters + 1)  # diff용 +1
    except Exception as e:
        return {"cik": cik, "error": f"submissions: {e}"}
    if not filings:
        return {"cik": cik, "name": "", "error": "no 13F-HR filings"}
    snaps = []
    for meta in filings:
        snap = fetch_infotable(cik, meta["accession"], meta["filing_date"])
        snaps.append({"meta": meta, "snap": snap})
        time.sleep(0.4)  # SEC 예우(≤10req/s)
    # 정정(/A)·지연 제출로 filing 순서 ≠ 분기 순서 → report_date로 정렬(최신 먼저).
    snaps.sort(key=lambda s: s["meta"]["report_date"], reverse=True)
    cur, prev = snaps[0], (snaps[1] if len(snaps) > 1 else {"snap": {"holdings": {}}})
    tops = top_positions(cur["snap"])
    moves = diff_quarters(cur["snap"], prev["snap"])
    # 우리 종목 겹침 — 티커 단위 집계(Alphabet A/C 등 share class 합산)
    cur_h, prev_h = cur["snap"].get("holdings", {}), prev["snap"].get("holdings", {})
    ov = {}
    for cusip, tk in HOLDINGS_CUSIP.items():
        if cusip not in cur_h and cusip not in prev_h:
            continue
        e = ov.setdefault(tk, {"ticker": tk, "issuer": "", "value_to": 0,
                               "shares_to": 0, "shares_from": 0})
        e["issuer"] = (cur_h.get(cusip) or prev_h.get(cusip))["issuer"]
        e["value_to"] += cur_h.get(cusip, {}).get("value", 0)
        e["shares_to"] += cur_h.get(cusip, {}).get("shares", 0)
        e["shares_from"] += prev_h.get(cusip, {}).get("shares", 0)
    overlap = []
    for tk, e in ov.items():
        e["action"] = _action(e["shares_from"], e["shares_to"])
        e["shares_delta_pct"] = (round((e["shares_to"] - e["shares_from"])
                                       / e["shares_from"] * 100, 1)
                                 if e["shares_from"] > 0 and e["shares_to"] > 0 else None)
        overlap.append(e)
    overlap.sort(key=lambda o: -o["value_to"])
    focus = {r["cusip"] for r in tops[:8]} | {c for c in HOLDINGS_CUSIP
                                              if c in cur["snap"].get("holdings", {})}
    traj = build_trajectory(snaps[:quarters], focus)
    return {
        "cik": str(int(cik)).zfill(10), "name": name,
        "filing_date": cur["meta"]["filing_date"], "quarter": cur["meta"]["report_date"],
        "prev_quarter": prev.get("meta", {}).get("report_date"),
        "portfolio_value_usd": cur["snap"].get("total_value", 0),
        "positions": cur["snap"].get("positions", 0),
        "options_latest": cur["snap"].get("option_lines", 0),
        "top_positions": tops, "moves": moves, "overlap_with_holdings": overlap,
        "trajectory": traj,
        "sources": [f"SEC EDGAR 13F-HR acc {m['meta']['accession']} ({m['meta']['report_date']})"
                    for m in snaps[:quarters]],
    }


def _fmt_usd(v: int) -> str:
    if v >= 1e9:
        return f"${v/1e9:.1f}B"
    if v >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"${v:,}"


def print_table(g: dict):
    if g.get("error"):
        print(f"[{g.get('name') or g.get('cik')}] ERROR: {g['error']}", file=sys.stderr)
        return
    print(f"# {g['name']}  ({g['quarter']} 공시 {g['filing_date']})")
    print(f"  포트폴리오: {_fmt_usd(g['portfolio_value_usd'])} · {g['positions']}종목")
    print("  ── 상위 보유 ──")
    for r in g["top_positions"][:10]:
        tk = f" [{r['ticker']}]" if r["ticker"] else ""
        print(f"    {r['issuer'][:26]:26} {r['pct']:5.1f}%  {_fmt_usd(r['value_usd'])}{tk}")
    print(f"  ── 분기 변동 (vs {g['prev_quarter']}) ──")
    for m in g["moves"][:12]:
        tk = f" [{m['ticker']}]" if m["ticker"] else ""
        dp = f" {m['shares_delta_pct']:+.0f}%" if m.get("shares_delta_pct") is not None else ""
        print(f"    {m['action']:4} {m['issuer'][:26]:26}{dp}{tk}")
    if g["overlap_with_holdings"]:
        print("  ── 우리 종목 겹침 ──")
        for o in g["overlap_with_holdings"]:
            print(f"    {o['ticker']:5} {o.get('action','')}  {o['issuer'][:26]}")


def main() -> int:
    ap = argparse.ArgumentParser(description="주식 대가 13F 보유변동 수집 (SEC EDGAR 무키)")
    ap.add_argument("--cik", help="특정 파일러 CIK (기본 = GURUS 전체)")
    ap.add_argument("--quarters", type=int, default=4, help="분석할 최근 분기 수 (기본 4)")
    ap.add_argument("--json", action="store_true", help="구조화 JSON stdout")
    ap.add_argument("--emit", action="store_true", help="data/app/guru_flows.json 팩트 갱신")
    args = ap.parse_args()

    if args.cik:
        targets = [("custom", {"cik": args.cik, "name": args.cik})]
    else:
        targets = list(GURUS.items())

    result = {}
    for slug, meta in targets:
        result[slug] = collect(meta["cik"], quarters=args.quarters)
        if not result[slug].get("name"):
            result[slug]["name"] = meta["name"]
        result[slug]["style"] = meta.get("style", "")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.emit:
        payload = _emit_payload(result, args.quarters)
        os.makedirs(os.path.dirname(GURU_JSON), exist_ok=True)
        with open(GURU_JSON, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[emit] {GURU_JSON} ← {len(result)}인 (팩트 레이어)", file=sys.stderr)

    if not args.json and not args.emit:
        for slug, g in result.items():
            print_table(g)
            print()
    return 0


def _load_existing() -> dict:
    try:
        with open(GURU_JSON, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _emit_payload(result: dict, quarters: int) -> dict:
    """스크립트 팩트 → guru_flows.json 스키마.
    'rationale/our_takeaway/themes/narrative'(데스크 이유분석)는 기존 파일에서 보존 —
    분기 팩트 갱신(--emit)이 데스크 서사를 지우지 않게 병합한다."""
    today = datetime.now(KST).strftime("%Y-%m-%d")
    old_gurus = _load_existing().get("gurus", {})
    gurus = {}
    for slug, g in result.items():
        if g.get("error"):
            gurus[slug] = {"name": g.get("name"), "error": g["error"]}
            continue
        oldg = old_gurus.get(slug, {})
        old_moves = {(m.get("cusip"), m.get("action")): m for m in oldg.get("moves", [])}
        old_ov = {o.get("ticker"): o for o in oldg.get("overlap_with_holdings", [])}
        moves = []
        for m in g["moves"]:
            p = old_moves.get((m["cusip"], m["action"]), {})
            moves.append(dict(m, rationale=p.get("rationale", ""),
                              our_takeaway=p.get("our_takeaway", ""), tag=p.get("tag", "미확인")))
        overlap = []
        for o in g["overlap_with_holdings"]:
            p = old_ov.get(o["ticker"], {})
            overlap.append(dict(o, our_takeaway=p.get("our_takeaway", "")))
        gurus[slug] = {
            "name": g["name"], "style": g.get("style", ""), "cik": g["cik"],
            "filing_date": g["filing_date"],
            "quarter": g["quarter"], "prev_quarter": g.get("prev_quarter"),
            "portfolio_value_usd": g["portfolio_value_usd"], "positions": g["positions"],
            "options_latest": g.get("options_latest", 0),
            "top_positions": g["top_positions"],
            "trajectory": g["trajectory"],
            "moves": moves, "overlap_with_holdings": overlap,
            "themes": oldg.get("themes", []), "narrative": oldg.get("narrative", ""),
            "sources": g["sources"],
        }
    return {
        "_comment": ("SEC EDGAR 13F(무키 팩트) — 'rationale/our_takeaway/themes/narrative'는 "
                     "guru-flow-desk가 주주서한·외신·sell-side로 채운다. 지연 확증 렌즈이지 "
                     "매수 트리거 아님(단일출처 매수 금지)."),
        "updated": today, "as_of_quarter": next(iter(gurus.values()), {}).get("quarter", ""),
        "source": "SEC EDGAR 13F-HR (무키) + guru-flow-desk 이유분석(WebSearch)",
        "gurus": gurus,
    }


if __name__ == "__main__":
    raise SystemExit(main())
