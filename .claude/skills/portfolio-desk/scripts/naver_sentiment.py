#!/usr/bin/env python3
"""naver_sentiment.py — 리테일 심리·관심도 게이지 (네이버 검색어트렌드 + 뉴스, stdlib only)

근거(외부 조사 2026-07-26): 검색량 기반 투자자 관심도(GSVI, Google Search Volume Index)
문헌 — 검색량 급증은 **개인 주도 시장에서 이후 초과수익을 되돌리는(negative lagged)** 경향이
반복 관측된다(Financial Innovation 2023 systematic review, Cogent Econ. 2021 리테일 우위시장
실증). 한국은 개인 비중이 큰 시장이고 네이버가 사실상 유일한 국내 검색 관문이므로
**네이버 검색어트렌드 = 한국판 GSVI**로 쓴다.

vol_gauge.py(폭풍 점수 = 변동성 %ile)와 **같은 문법(%ile)** 으로 설계했다:
  · vol_gauge  = 시장이 얼마나 격렬한가(가격)         → 트랜치 사이즈
  · 이 스크립트 = 개인이 얼마나 공포/과열인가(심리)    → 역발상 타이밍 참고
둘 다 높으면 '항복(capitulation) 정황' — CLAUDE.md 투자철학 "공포에 사라"의 정량 게이지.

⚠️ 측정 전용이다. 어떤 룰(안전핀·트랜치·별점)도 이 숫자가 바꾸지 않는다. 매수 트리거 아님.
⚠️ 검색어트렌드 ratio는 **요청 1콜 내부에서만** 상대 정규화된다(0~100) → 콜 간 절대 비교 금지.
   그래서 이 스크립트는 항상 **1년치를 한 콜로** 받아 그 안에서 %ile을 뽑는다(자기완결 비교).

산출:
  ① 공포/항복/유입 3개 심리 그룹의 최근값·MA5·**1년 %ile**·1년 최고일
  ② 보유 국내 5종목의 **관심도 %ile**(관심 급증 = 과열 경계, 문헌의 lagged negative)
  ③ 뉴스 버즈 = 최근 24/72시간 기사 건수(네이버 뉴스 검색 API)
  ④ --save 시 data/app/sentiment.json에 시계열 누적(%ile은 콜 간 비교 가능한 값)

사용:
  python3 naver_sentiment.py                 # 심리 3그룹 게이지(기본)
  python3 naver_sentiment.py --stocks        # 보유 국내 5종목 관심도 %ile
  python3 naver_sentiment.py --news-buzz     # 종목별 24/72h 기사 건수
  python3 naver_sentiment.py --all --save    # 전부 + 시계열 누적 저장
  python3 naver_sentiment.py --json          # 파이프라인용

키 = naver_data.py와 동일(NAVER_NCP_KEY_ID / NAVER_NCP_KEY, 환경변수·조회전용).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import naver_data as nd
except Exception as e:  # pragma: no cover
    sys.exit("[naver_sentiment] naver_data.py 임포트 실패: %s" % e)

try:  # 유니버스는 market_data(=portfolio.json 미러)에서 — 티커·종목 드리프트 방지
    import market_data as md
    _KR_NAMES = [n for n, _ in md.HOLDINGS_KR]
except Exception:
    _KR_NAMES = ["삼성전자", "LG전자", "두산로보틱스", "현대차", "NAVER"]

KST = datetime.timezone(datetime.timedelta(hours=9))
STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..",
                     "data", "app", "sentiment.json")

# 심리 그룹 — 키워드는 고정한다(바꾸면 과거 %ile과 비교 불가).
PSYCH_GROUPS = [
    {"groupName": "공포", "keywords": ["주식 폭락", "코스피 폭락", "증시 폭락"]},
    {"groupName": "항복", "keywords": ["반대매매", "손절", "마진콜"]},
    {"groupName": "유입", "keywords": ["주식 계좌 개설", "주식 시작", "빚투"]},
]

MA_WINDOW = 5      # 5일 평균(주말 검색 포함 — 요일효과 완화)
LOOKBACK_DAYS = 365


def today_kst() -> datetime.date:
    return datetime.datetime.now(KST).date()


def _ma(vals, w):
    """단순이동평균 시계열(길이 = len(vals)-w+1)."""
    return [sum(vals[i:i + w]) / w for i in range(0, len(vals) - w + 1)]


def _pctile(series, value) -> float:
    """value가 series 분포에서 몇 %ile인지(이하 비율)."""
    if not series:
        return float("nan")
    return 100.0 * sum(1 for v in series if v <= value) / len(series)


def _band(p):
    """%ile → 사람이 읽는 판정(공포계열 기준)."""
    if p != p:
        return "?"
    if p >= 90:
        return "극단"
    if p >= 70:
        return "고조"
    if p >= 30:
        return "보통"
    return "무관심"


def _series(groups, days=LOOKBACK_DAYS, end=None):
    """1년치 일간 트렌드를 한 콜로 받아 그룹별 {name: [(date, ratio)...]} 반환."""
    end_d = end or today_kst()
    start_d = end_d - datetime.timedelta(days=days)
    raw = nd.trend(groups, start_d.isoformat(), end_d.isoformat(), "date")
    out = {}
    for g in raw.get("results", []):
        pts = [(p.get("period"), float(p.get("ratio", 0.0))) for p in g.get("data", [])]
        out[g.get("title")] = pts
    return out


def gauge(groups, days=LOOKBACK_DAYS):
    """그룹별 최근값·MA5·1년 %ile·최고일을 계산."""
    ser = _series(groups, days)
    rows = []
    for g in groups:
        name = g["groupName"]
        pts = ser.get(name) or []
        if len(pts) < MA_WINDOW + 10:
            rows.append({"name": name, "error": "데이터 부족(%d pt)" % len(pts)})
            continue
        vals = [v for _, v in pts]
        ma = _ma(vals, MA_WINDOW)
        cur_ma = ma[-1]
        peak_i = max(range(len(vals)), key=lambda i: vals[i])
        rows.append({
            "name": name,
            "keywords": g["keywords"],
            "last_date": pts[-1][0],
            "last": round(vals[-1], 3),
            "ma5": round(cur_ma, 3),
            "pctile": round(_pctile(ma, cur_ma), 1),
            "band": _band(_pctile(ma, cur_ma)),
            "y_max": round(vals[peak_i], 3),
            "y_max_date": pts[peak_i][0],
            "y_median": round(statistics.median(vals), 3),
            "points": len(vals),
        })
    return rows


def stock_attention(names=None, days=LOOKBACK_DAYS):
    """보유 종목 관심도 %ile. 트렌드 API는 1콜 최대 5그룹 → 5개씩 나눠 호출."""
    names = names or _KR_NAMES
    rows = []
    for i in range(0, len(names), 5):
        chunk = names[i:i + 5]
        groups = [{"groupName": n, "keywords": [n]} for n in chunk]
        rows += gauge(groups, days)
    return rows


def news_buzz(names=None, display=100):
    """종목별 최근 24h/72h 기사 건수(네이버 뉴스 검색, sort=date 최신 100건 기준)."""
    names = names or _KR_NAMES
    now = datetime.datetime.now(datetime.timezone.utc)
    out = []
    for n in names:
        try:
            d = nd.news(n + " 주가", display=display, sort="date")
        except Exception as e:
            out.append({"name": n, "error": "%s" % type(e).__name__})
            continue
        h24 = h72 = 0
        for it in d.get("items", []):
            try:
                pub = datetime.datetime.strptime(it.get("pubDate", "")[:25].strip(),
                                                 "%a, %d %b %Y %H:%M:%S")
            except Exception:
                continue
            age_h = (now.replace(tzinfo=None) - pub).total_seconds() / 3600.0
            if age_h <= 24:
                h24 += 1
            if age_h <= 72:
                h72 += 1
        items = d.get("items", [])
        out.append({
            "name": n,
            "h24": h24,
            "h72": h72,
            "saturated": len(items) >= display and h72 >= display,  # 100건 상한에 막힘 = 최소치
            "top": nd._clean(items[0].get("title")) if items else "",
        })
    return out


# ── 리테일 담론 게이지 [8/1 신설] ───────────────────────────────────────────
# 검색어트렌드(=관심의 **양**)와 다른 축: 개인이 **실제로 뭘 쓰고 묻는가**(발화).
#   · cafearticle = 주식 카페 글 볼륨 — 개인투자자 담론의 본진
#   · kin         = 지식iN 질문량 — **"주식 초보" 질문 급증 = 개인 대량유입**(고전적 역발상 신호)
#   · blog        = 블로그 언급량 — 테마 확산 속도(전문 블로거가 리테일에 선행)
#
# ⚠️ `total`은 **누적 문서 수**라 절대값 자체엔 의미가 적다. 원장(--save)에 스냅샷을 쌓아
#    **콜 간 델타**로 급증을 본다. blog는 postdate가 있어 최근 N일 카운트가 가능하지만
#    kin·cafearticle은 날짜가 없어 델타가 유일한 방법이다.
# ⚠️ **측정 전용** — 이 숫자는 안전핀·트랜치·별점 어떤 룰도 바꾸지 않는다.
DISCOURSE_QUERIES = [
    ("초보유입", "kin", "주식 초보"),
    # "반대매매" 단독은 부동산 매도청구소송 글까지 잡힌다(8/1 실측) → "주식"으로 한정.
    # 질의어를 바꾸면 과거 total과 비교 불가하므로 **이후 고정**한다(PSYCH_GROUPS와 같은 규율).
    ("반대매매질문", "kin", "주식 반대매매"),
    ("카페담론", "cafearticle", "코스피"),
    ("카페공포", "cafearticle", "주식 폭락"),
    ("테마확산", "blog", "반도체 전망"),
]


def discourse():
    """리테일 담론량 스냅샷. 실패는 error로 남겨 '0건'과 구분한다(§4b)."""
    out = []
    for label, kind, query in DISCOURSE_QUERIES:
        try:
            d = nd.search(kind, query, display=3, sort="date")
            out.append({"label": label, "kind": kind, "query": query,
                        "total": d.get("total"),
                        "top": nd._clean((d.get("items") or [{}])[0].get("title", ""))})
        except Exception as e:
            out.append({"label": label, "kind": kind, "query": query,
                        "error": "%s %s" % (type(e).__name__, str(e)[:40])})
    return out


def _discourse_delta(rows):
    """직전 저장분 대비 증감 — total은 누적값이라 델타가 신호다."""
    st = _load_store()
    prev = None
    for h in reversed(st.get("history", [])):
        if h.get("discourse"):
            prev = {r["label"]: r.get("total") for r in h["discourse"] if r.get("total")}
            break
    if not prev:
        return None
    out = {}
    for r in rows:
        p, c = prev.get(r["label"]), r.get("total")
        if isinstance(p, int) and isinstance(c, int) and p:
            out[r["label"]] = round((c - p) / p * 100, 2)
    return out or None


def _print_discourse(rows, delta):
    print("── 리테일 담론량 (카페·지식iN·블로그 · 누적 문서수)")
    for r in rows:
        if r.get("error"):
            print("  · %-10s 수집 실패 — %s" % (r["label"], r["error"]))
            continue
        d = (delta or {}).get(r["label"])
        dtxt = "  Δ%+.2f%%" % d if d is not None else "  (첫 표본)"
        print("  · %-10s [%s:%s] %12s건%s" % (r["label"], r["kind"], r["query"],
                                             format(r["total"], ","), dtxt))
        if r.get("top"):
            print("      최신: %s" % r["top"][:60])
    if delta is None:
        print("  ※ 첫 표본 — total은 누적값이라 **다음 콜부터 델타**가 신호가 된다.")


def _load_store():
    try:
        with open(os.path.abspath(STORE), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"note": "네이버 검색어트렌드 기반 리테일 심리 시계열 (naver_sentiment.py --save)",
                "history": []}


def save(record, keep=400):
    st = _load_store()
    hist = [h for h in st.get("history", []) if h.get("date") != record.get("date")]
    hist.append(record)
    hist.sort(key=lambda h: h.get("date", ""))
    st["history"] = hist[-keep:]
    st["updated"] = record.get("date")
    path = os.path.abspath(STORE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    return path


def _print_gauge(rows, title):
    print("── %s" % title)
    for r in rows:
        if r.get("error"):
            print("  · %-8s %s" % (r["name"], r["error"]))
            continue
        print("  · %-8s MA5 %6.2f | 1년 %5.1f%%ile [%s] | 최고 %s(%.1f) | 최신 %s"
              % (r["name"], r["ma5"], r["pctile"], r["band"],
                 r["y_max_date"], r["y_max"], r["last_date"]))


def _verdict(psych):
    """공포·항복 %ile 조합의 한 줄 판정(참고용 — 룰 아님)."""
    by = {r["name"]: r for r in psych if not r.get("error")}
    f = by.get("공포", {}).get("pctile")
    s = by.get("항복", {}).get("pctile")
    if f is None or s is None:
        return "판정 불가(데이터 부족)"
    if f >= 90 and s >= 90:
        return "패닉 극단(공포·항복 동반 90%ile+) — vol_gauge 폭풍 %ile과 교차확인 시 항복 정황"
    if f >= 90:
        return "공포 극단(90%ile+) — 항복 지표는 아직 미동반, 역발상은 안전핀 룰 우선"
    if f >= 70:
        return "공포 고조(70%ile+) — 관심만, 트리거 아님"
    if f < 30:
        return "무관심 구간 — 심리 신호 없음(가격·수급으로 판단)"
    return "보통 구간 — 심리 특이신호 없음"


def main():
    ap = argparse.ArgumentParser(description="네이버 검색어트렌드·뉴스 기반 리테일 심리 게이지(조회 전용)")
    ap.add_argument("--stocks", action="store_true", help="보유 국내 종목 관심도 %%ile")
    ap.add_argument("--news-buzz", action="store_true", help="종목별 24/72h 기사 건수")
    ap.add_argument("--discourse", action="store_true",
                    help="리테일 담론량(카페·지식iN·블로그) — '주식 초보' 질문 급증 = 역발상 신호")
    ap.add_argument("--all", action="store_true", help="심리 + 관심도 + 뉴스버즈 전부")
    ap.add_argument("--names", help="종목명 쉼표구분(기본 = 보유 국내 5종목)")
    ap.add_argument("--days", type=int, default=LOOKBACK_DAYS, help="백분위 기준 기간(일, 기본 365)")
    ap.add_argument("--save", action="store_true", help="data/app/sentiment.json에 누적 저장")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    a = ap.parse_args()

    names = [x.strip() for x in a.names.split(",")] if a.names else None
    want_psych = a.all or not (a.stocks or a.news_buzz)
    out = {"date": today_kst().isoformat(), "source": "naver_search_trend+news"}

    try:
        if want_psych:
            out["psych"] = gauge(PSYCH_GROUPS, a.days)
            out["verdict"] = _verdict(out["psych"])
        if a.stocks or a.all:
            out["stocks"] = stock_attention(names, a.days)
        if a.news_buzz or a.all:
            out["news_buzz"] = news_buzz(names)
        if a.discourse or a.all:
            out["discourse"] = discourse()
            out["discourse_delta"] = _discourse_delta(out["discourse"])
    except SystemExit:
        raise
    except Exception as e:
        sys.exit("[naver_sentiment] %s: %s" % (type(e).__name__, str(e)[:200]))

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print("[리테일 심리 게이지] %s KST · 최근 %d일 분포 기준" % (out["date"], a.days))
        if "psych" in out:
            _print_gauge(out["psych"], "심리 3그룹 (검색량 %ile)")
            print("  ▶ %s" % out["verdict"])
        if "stocks" in out:
            _print_gauge(out["stocks"], "보유 국내 종목 관심도 (급증 = 과열 경계·GSVI 문헌)")
        if "discourse" in out:
            _print_discourse(out["discourse"], out.get("discourse_delta"))
        if "news_buzz" in out:
            print("── 뉴스 버즈 (최근 24h / 72h 기사수)")
            for r in out["news_buzz"]:
                if r.get("error"):
                    print("  · %-8s %s" % (r["name"], r["error"]))
                    continue
                print("  · %-8s 24h %3d건 / 72h %3d건%s | %s"
                      % (r["name"], r["h24"], r["h72"], " (상한)" if r["saturated"] else "",
                         r["top"][:46]))

    if a.save:
        rec = {"date": out["date"],
               "psych": [{k: r.get(k) for k in ("name", "ma5", "pctile", "band")}
                         for r in out.get("psych", []) if not r.get("error")],
               "stocks": [{k: r.get(k) for k in ("name", "ma5", "pctile", "band")}
                          for r in out.get("stocks", []) if not r.get("error")],
               "news_buzz": [{k: r.get(k) for k in ("name", "h24", "h72")}
                             for r in out.get("news_buzz", []) if not r.get("error")],
               "verdict": out.get("verdict", "")}
        print("saved → %s" % save(rec))


if __name__ == "__main__":
    main()
