#!/usr/bin/env python3
"""naver_data.py — 네이버 오픈API(NCP NAVER API HUB) 조회 전용 (stdlib only).

정훈 데스크용 두 소스:
  ① 뉴스 검색  = naverapihub.apigw.ntruss.com/search/v1/news   (GET)  — 국장 뉴스 흐름
  ② 검색어트렌드 = naveropenapi.apigw.ntruss.com/datalab/v1/search (POST) — 리테일 관심/심리 게이지

인증 = NCP API Gateway 헤더 (X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY).
키는 반드시 환경변수로만 (저장·커밋 금지 — 토스키와 동일 취급, 조회 전용).
  export NAVER_NCP_KEY_ID=<Client ID>
  export NAVER_NCP_KEY=<Client Secret>

웹 환경(데이터센터 IP)에서 프록시 통과: SSL_CERT_FILE=/root/.ccr/ca-bundle.crt (기본값).
[7/19 실측] 뉴스 200 정상 / 데이터랩은 앱 등록 직후 구독 전파 지연 시 401(errorCode 210) — 몇 분 뒤 재시도.
"""
import os, sys, json, ssl, argparse, re, urllib.request, urllib.parse, urllib.error

CID = os.environ.get("NAVER_NCP_KEY_ID") or os.environ.get("NAVER_SEARCH_CLIENT_ID")
CSEC = os.environ.get("NAVER_NCP_KEY") or os.environ.get("NAVER_SEARCH_CLIENT_SECRET")
CAFILE = os.environ.get("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt"

NEWS_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
TREND_URL = "https://naveropenapi.apigw.ntruss.com/datalab/v1/search"

_TAG = re.compile(r"<[^>]+>")


def _ctx():
    try:
        return ssl.create_default_context(cafile=CAFILE)
    except Exception:
        return ssl.create_default_context()


def _headers(extra=None):
    if not CID or not CSEC:
        sys.exit("[naver_data] 환경변수 NAVER_NCP_KEY_ID / NAVER_NCP_KEY 필요 (조회전용·저장금지).")
    h = {"X-NCP-APIGW-API-KEY-ID": CID, "X-NCP-APIGW-API-KEY": CSEC}
    if extra:
        h.update(extra)
    return h


def _clean(s):
    return _TAG.sub("", s or "").replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")


def news(query, display=5, sort="date"):
    """국내 뉴스 검색. sort=date(최신)|sim(정확도). 최대 display 100."""
    qs = urllib.parse.urlencode({"query": query, "display": display, "sort": sort})
    req = urllib.request.Request(NEWS_URL + "?" + qs, headers=_headers())
    with urllib.request.urlopen(req, timeout=25, context=_ctx()) as r:
        return json.loads(r.read().decode("utf-8"))


def trend(groups, start, end, unit="week"):
    """검색어트렌드(상대 검색량 0~100). groups=[{groupName, keywords[]}...] 최대 5그룹."""
    body = json.dumps({"startDate": start, "endDate": end, "timeUnit": unit,
                       "keywordGroups": groups}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(TREND_URL, data=body,
                                 headers=_headers({"Content-Type": "application/json"}))
    with urllib.request.urlopen(req, timeout=25, context=_ctx()) as r:
        return json.loads(r.read().decode("utf-8"))


def _print_news(d):
    print("총 %s건 (표시 %d)" % (format(d.get("total", 0), ","), len(d.get("items", []))))
    for it in d.get("items", []):
        print("· [%s] %s" % ((it.get("pubDate", "")[:16]), _clean(it.get("title"))))
        print("    %s" % _clean(it.get("description"))[:110])
        print("    %s" % it.get("originallink") or it.get("link"))


def _print_trend(d):
    for g in d.get("results", []):
        data = g.get("data", [])
        line = "  ".join("%s:%.1f" % (p.get("period", "")[5:], p.get("ratio", 0)) for p in data[-8:])
        print("· %s (%d pt) 최근8: %s" % (g.get("title"), len(data), line))


def main():
    ap = argparse.ArgumentParser(description="네이버 오픈API 조회(뉴스/검색어트렌드) — 조회 전용")
    ap.add_argument("--news", metavar="QUERY", help="국내 뉴스 검색어")
    ap.add_argument("--display", type=int, default=5, help="뉴스 개수(최대 100)")
    ap.add_argument("--sort", default="date", choices=["date", "sim"], help="date=최신/sim=정확도")
    ap.add_argument("--trend", metavar="KW", help="검색어트렌드 키워드(쉼표구분, 한 그룹)")
    ap.add_argument("--start", default=None, help="트렌드 시작일 YYYY-MM-DD")
    ap.add_argument("--end", default=None, help="트렌드 종료일 YYYY-MM-DD")
    ap.add_argument("--unit", default="week", choices=["date", "week", "month"])
    ap.add_argument("--json", action="store_true", help="원본 JSON 출력")
    a = ap.parse_args()

    if not a.news and not a.trend:
        ap.error("--news 또는 --trend 중 하나 필요")

    try:
        if a.news:
            d = news(a.news, a.display, a.sort)
            if a.json:
                print(json.dumps(d, ensure_ascii=False, indent=1))
            else:
                _print_news(d)
        if a.trend:
            import datetime
            end = a.end or datetime.date.today().isoformat()
            start = a.start or (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
            groups = [{"groupName": a.trend.split(",")[0], "keywords": [k.strip() for k in a.trend.split(",")]}]
            d = trend(groups, start, end, a.unit)
            print(json.dumps(d, ensure_ascii=False, indent=1)) if a.json else _print_trend(d)
    except urllib.error.HTTPError as e:
        body = e.read(300).decode("utf-8", "replace")
        sys.exit("[naver_data] HTTP %d :: %s" % (e.code, body[:200]))
    except Exception as e:
        sys.exit("[naver_data] %s: %s" % (type(e).__name__, str(e)[:200]))


if __name__ == "__main__":
    main()
