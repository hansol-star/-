#!/usr/bin/env python3
"""
build_app_data.py — 포트폴리오 앱 데이터 빌더

portfolio.json(수량·원가·트리거) + data/app/stocks.json(종목별 분석:별점·목표·매수존·트림·이슈)
+ Yahoo 실시간 시세(market_data.fetch_quote)를 합쳐 평가손익까지 계산해
app/data.js (window.APP_DATA = {...}) 한 파일로 떨군다.

정적 웹앱(app/index.html)이 이 data.js 하나만 읽으면 폰에서 바로 동작한다.
백엔드·키 불필요(stdlib만). 로컬 이전 후에도 그대로.

사용법:
  python3 build_app_data.py            # 실시간 시세로 빌드
  python3 build_app_data.py --offline  # 시세 호출 없이 stocks.json 값만 (네트워크 차단 시)
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# scripts -> portfolio-desk -> skills -> .claude -> repo
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PORTFOLIO_JSON = os.path.join(HERE, "..", "portfolio.json")
STOCKS_JSON = os.path.join(REPO, "data", "app", "stocks.json")
HUNTER_JSON = os.path.join(REPO, "data", "app", "hunter.json")
HUNTER_ARCHIVE_JSON = os.path.join(REPO, "data", "app", "hunter_archive.json")
FLOWS_JSON = os.path.join(REPO, "data", "app", "flows.json")
REPORTS_DIR = os.path.join(REPO, "docs", "reports")
OUT_JS = os.path.join(REPO, "app", "data.js")

# 보고서 종류 → 앱 배지 라벨 (파일명 접두어 기준)
REPORT_KINDS = [
    ("report_", "보고서"),
    ("holdings_final", "보유확정"),
    ("holdings_sell", "매도원칙"),
    ("holdings_", "보유점검"),
    ("fomc_", "이벤트"),
]

sys.path.insert(0, HERE)
import urllib.request  # noqa: E402
from market_data import fetch_quote, YAHOO_CHART, UA  # noqa: E402


def fetch_history(symbol: str, rng: str = "1mo", interval: str = "1d", offline: bool = False) -> dict:
    """Yahoo chart에서 종가 시계열 → {dates:[YYYY-MM-DD], closes:[float]}."""
    if offline:
        return {"dates": [], "closes": []}
    url = YAHOO_CHART.format(symbol=urllib.request.quote(symbol)) + f"?interval={interval}&range={rng}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.load(resp)
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        closes = res["indicators"]["quote"][0]["close"]
        out = {"dates": [], "closes": []}
        for t, c in zip(ts, closes):
            if c is None:
                continue
            out["dates"].append(dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"))
            out["closes"].append(round(c, 2))
        return out
    except Exception:
        return {"dates": [], "closes": []}


def _report_kind(name: str) -> str:
    for prefix, label in REPORT_KINDS:
        if name.startswith(prefix):
            return label
    return "기타"


def build_reports() -> list:
    """docs/reports/*.md 를 스캔해 앱에서 클릭→본문을 볼 수 있는 목록으로.

    각 항목: id·file·title(첫 H1)·date·version·kind(배지)·preview(첫 문단)·content(원문 md).
    최신순(날짜 desc → 버전 desc → 파일명 desc) 정렬.
    """
    reports = []
    for path in glob.glob(os.path.join(REPORTS_DIR, "*.md")):
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue
        if not content.strip():
            continue

        # 제목 = 첫 번째 H1, 없으면 파일명
        title = name.replace("_", " ")
        for line in content.splitlines():
            s = line.strip()
            if s.startswith("# "):
                title = s.lstrip("#").strip()
                break

        # 미리보기 = 헤딩·표·구분선이 아닌 첫 실질 문단
        preview = ""
        for line in content.splitlines():
            s = line.strip()
            if not s or s.startswith(("#", "|", "-", "*", ">", "`", "=")):
                continue
            preview = re.sub(r"[*_`>#]", "", s)[:140]
            break

        m_date = re.search(r"(\d{4}-\d{2}-\d{2})", name)
        m_ver = re.search(r"_v(\d+)", name)
        reports.append({
            "id": name,
            "file": "docs/reports/" + os.path.basename(path),
            "title": title,
            "date": m_date.group(1) if m_date else "",
            "version": int(m_ver.group(1)) if m_ver else None,
            "kind": _report_kind(name),
            "preview": preview,
            "content": content,
        })

    reports.sort(key=lambda r: (r["date"], r["version"] or -1, r["id"]), reverse=True)
    return reports


def hunter_scorecard(verdicts) -> dict:
    """판정 리스트를 집계해 채널 정확도 스코어카드 산출.

    버킷: 정확(검증/방향/개선) · 근사 · 시점 · 미확인 · 정정(자막오류 포함) · 과장.
    accuracy = (정확+근사) / 전체. 채널 신뢰도를 정량화해 '방향성 채택·숫자 교차검증'
    원칙을 데이터로 뒷받침한다. (전체 영상 아카이브 verdict 기준)
    """
    b = {"정확": 0, "근사": 0, "시점": 0, "미확인": 0, "정정": 0, "과장": 0}
    for v in verdicts:
        v = str(v)
        if "미확인" in v and "검증" not in v:
            b["미확인"] += 1
        elif "정정" in v or "오류" in v:
            b["정정"] += 1
        elif "과장" in v:
            b["과장"] += 1
        elif "근사" in v or "일부" in v:
            b["근사"] += 1
        elif "시점" in v:
            b["시점"] += 1
        elif "검증" in v or "개선" in v:
            b["정확"] += 1
        else:
            b["미확인"] += 1
    total = sum(b.values())
    acc = round((b["정확"] + b["근사"]) / total * 100) if total else None
    return {"buckets": b, "total": total, "accuracy_pct": acc}


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_json_opt(path: str) -> dict:
    try:
        return load_json(path)
    except (FileNotFoundError, ValueError):
        return {}


def quote(symbol: str, offline: bool) -> dict:
    if offline:
        return {"symbol": symbol, "price": None, "prev_close": None,
                "change_pct": None, "currency": None}
    q = fetch_quote(symbol)
    return q or {"symbol": symbol, "error": "no data"}


def pct(a, b):
    if a is None or b in (None, 0):
        return None
    return round((a - b) / b * 100, 2)


def build(offline: bool) -> dict:
    pf = load_json(PORTFOLIO_JSON)
    sj = load_json(STOCKS_JSON)
    stock_meta = sj.get("stocks", {})
    watch_meta = sj.get("watchlist", {})

    # ── 환율 ──
    fx_q = quote("KRW=X", offline)
    usdkrw = fx_q.get("price") or pf.get("us_avg_fx_cost", 1456.5)

    # ── 보유 종목 ──
    holdings = []
    total_value_krw = 0.0
    total_prev_krw = 0.0
    total_cost_krw = 0.0
    us_fx_cost = pf.get("us_avg_fx_cost", 1456.5)

    for region, key in (("kr", "kr"), ("us", "us")):
        for h in pf["holdings"][key]:
            sym = h["ticker"]
            q = quote(sym, offline)
            price = q.get("price")
            prev = q.get("prev_close")
            cur = q.get("currency") or ("KRW" if region == "kr" else "USD")
            shares = h["shares"]
            cost = h["cost"]

            if region == "kr":
                value_krw = (price or 0) * shares
                prev_krw = (prev or price or 0) * shares
                cost_krw = cost * shares
            else:
                value_krw = (price or 0) * shares * usdkrw
                prev_krw = (prev or price or 0) * shares * usdkrw
                cost_krw = cost * shares * us_fx_cost

            total_value_krw += value_krw
            total_prev_krw += prev_krw
            total_cost_krw += cost_krw

            meta = stock_meta.get(sym, {})
            holdings.append({
                "label": h["label"],
                "ticker": sym,
                "region": region,
                "currency": cur,
                "shares": shares,
                "cost": cost,
                "price": price,
                "change_pct": q.get("change_pct"),
                "value_krw": round(value_krw),
                "pnl_pct": pct(price, cost),
                "pnl_krw": round(value_krw - cost_krw),
                "outlook": meta.get("outlook", "hold"),
                "stars": meta.get("stars", 3),
                "target": meta.get("target", "—"),
                "buy_zone": meta.get("buy_zone", "—"),
                "trim": meta.get("trim", "—"),
                "comment": meta.get("comment", ""),
                "issues": meta.get("issues", []),
            })

    # ── 워치리스트 (분석 데이터 있는 활성만) ──
    watchlist = []
    for sym, meta in watch_meta.items():
        q = quote(sym, offline)
        watchlist.append({
            "label": meta.get("label", sym),
            "ticker": sym,
            "currency": q.get("currency"),
            "price": q.get("price"),
            "change_pct": q.get("change_pct"),
            "stars": meta.get("stars", 3),
            "target": meta.get("target", "—"),
            "comment": meta.get("comment", ""),
            "issues": meta.get("issues", []),
        })

    # ── 지수 ──
    indices = []
    for idx in pf.get("indices", []):
        q = quote(idx["ticker"], offline)
        indices.append({
            "label": idx["label"],
            "ticker": idx["ticker"],
            "price": q.get("price"),
            "change_pct": q.get("change_pct"),
        })

    # ── 코스피 안전핀 상태 ──
    kospi = next((i for i in indices if i["ticker"] == "^KS11"), None)
    kospi_price = kospi["price"] if kospi else None
    safety = {"pin": 7500, "level2": 8000, "price": kospi_price,
              "change_pct": kospi["change_pct"] if kospi else None}
    if kospi_price is None:
        safety["status"] = "unknown"
    elif kospi_price < 7500:
        safety["status"] = "freeze"   # 잔여 트랜치 전면 동결
    elif kospi_price < 8000:
        safety["status"] = "watch"    # 2차 트랜치 구간
    else:
        safety["status"] = "ok"

    # ── 트리거/알림 (가격 조건 평가) ──
    price_by_ticker = {h["ticker"]: h["price"] for h in holdings}
    price_by_ticker.update({i["ticker"]: i["price"] for i in indices})
    price_by_ticker.update({w["ticker"]: w["price"] for w in watchlist})
    alerts = []
    for a in pf.get("alerts", []):
        fired = None
        p = price_by_ticker.get(a.get("ticker"))
        cond = a.get("cond")
        if p is not None and cond == "below":
            fired = p < a["level"]
        elif p is not None and cond == "above":
            fired = p > a["level"]
        elif p is not None and cond == "between":
            fired = a["low"] <= p <= a["high"]
        alerts.append({
            "id": a["id"],
            "ticker": a.get("ticker"),
            "cond": cond,
            "when": a.get("when"),
            "action": a["action"],
            "price": p,
            "fired": fired,
        })

    day_change_krw = round(total_value_krw - total_prev_krw)
    cash = pf.get("cash_krw", 0)

    # ── 시계열 차트 (환율·코스피) + 경제사냥꾼 + 수급 ──
    fx_history = fetch_history("KRW=X", offline=offline)
    kospi_history = fetch_history("^KS11", offline=offline)
    hunter = load_json_opt(HUNTER_JSON)
    archive = load_json_opt(HUNTER_ARCHIVE_JSON)
    archive_videos = archive.get("videos", []) if isinstance(archive, dict) else []
    if hunter:
        # 전체 아카이브 verdict 기준(없으면 track_record 폴백)으로 채널 정확도 집계
        verdicts = [v.get("verdict", "") for v in archive_videos] \
            or [r.get("verdict", "") for r in hunter.get("track_record", [])]
        hunter["scorecard"] = hunter_scorecard(verdicts)
    flows = load_json_opt(FLOWS_JSON)
    reports = build_reports()

    return {
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M KST"),
        "as_of": sj.get("as_of", ""),
        "source_report": sj.get("source_report", ""),
        "offline": offline,
        "fx": {"usdkrw": round(usdkrw, 2) if usdkrw else None},
        "totals": {
            "assets_krw": round(total_value_krw + cash),
            "stocks_value_krw": round(total_value_krw),
            "cash_krw": cash,
            "day_change_krw": day_change_krw,
            "day_change_pct": pct(total_value_krw, total_prev_krw),
            "total_pnl_krw": round(total_value_krw - total_cost_krw),
            "total_pnl_pct": pct(total_value_krw, total_cost_krw),
        },
        "safety": safety,
        "indices": indices,
        "alerts": alerts,
        "holdings": holdings,
        "watchlist": watchlist,
        "tranches": pf.get("tranches", []),
        "fx_history": fx_history,
        "kospi_history": kospi_history,
        "hunter": hunter,
        "hunter_archive": archive_videos,
        "flows": flows,
        "reports": reports,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="시세 호출 없이 빌드")
    args = ap.parse_args()

    data = build(args.offline)
    os.makedirs(os.path.dirname(OUT_JS), exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write("// 자동 생성 — build_app_data.py. 직접 수정 금지.\n")
        f.write("window.APP_DATA = " + payload + ";\n")

    t = data["totals"]
    print(f"✅ app/data.js 생성 — 총자산 {t['assets_krw']:,}원 "
          f"(당일 {t['day_change_krw']:+,}원 / {t['day_change_pct']}%) "
          f"· 보유 {len(data['holdings'])} · 워치 {len(data['watchlist'])} "
          f"· 보고서 {len(data['reports'])} "
          f"· 발동 알림 {sum(1 for a in data['alerts'] if a['fired'])}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
