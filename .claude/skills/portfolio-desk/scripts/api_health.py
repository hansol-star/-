#!/usr/bin/env python3
"""
api_health.py — 외부 데이터 소스 생존 점검 [2026-08-12 신설]

왜 필요한가
────────────────────────────────────────────────────────────────
CLAUDE.md 교훈: **"외부 API는 말없이 죽는다 — 문서의 '✅ 정상'은 마지막 확인일의
사실일 뿐, 키 붙은 레이어는 주기적 실호출로 생존 확인할 것."**
그런데 정작 그 '실호출로 확인하는 도구'가 없었다. 실제 사고 이력:
  · 8/1  FMP 레거시 /api/v3 전면 차단 — 문서엔 '✅ 정상'으로 남아 있었다
  · 8/12 YouTube RSS 3채널 동시 404 + yt-dlp 동시 실패 (무인 R1이 조용히 죽을 뻔)
  · 8/12 data/history 67/70종목 정지 (게이트 밖이라 아무도 몰랐다)

⇒ **각 소스에 실제로 1회씩 쏴 보고** 응답을 확인한다. 문서를 믿지 않는다.

사용법
  python3 api_health.py            # 전체 점검
  python3 api_health.py --quick    # 키 없는 무료 소스만(빠름)
  python3 api_health.py --json     # 기계 판독용

⚠️ 측정 전용 — 어떤 데이터도 쓰지 않고 어떤 룰도 바꾸지 않는다.
⚠️ 키는 환경변수에서만 읽는다. 출력에 키 값을 절대 찍지 않는다(앞 4자만 마스킹 표시).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
TIMEOUT = 20


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytdlp_bin import ytdlp_cmd  # noqa: E402  PATH에 exe가 없어도 찾는다

def _get(url: str, headers: dict | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read().decode("utf-8", "replace")


def _mask(key: str) -> str:
    if not key:
        return "미설정"
    return f"{key[:4]}…{key[-2:]} ({len(key)}자)"


# ── 개별 점검 ────────────────────────────────────────────────────────────
def chk_yahoo():
    """★[8/12 자체 버그 교정 — DRY] 초판이 URL을 직접 때려 429 위양성을 냈다.
    같은 시각 `market_data.py`는 멀쩡히 돌았다. **점검 도구가 본 스크립트와 다른 방식으로
    호출하면 없는 장애를 만든다** — refresh_stale이 COVERAGE_LAYERS를 import하는 것과 같은 이유로
    여기서도 **본 스크립트의 함수를 그대로 재사용**한다."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from market_data import fetch_quote
    q = fetch_quote("005930.KS")
    px = q.get("price") if isinstance(q, dict) else None
    return px is not None, f"삼성전자 {px:,.0f}원 (market_data.fetch_quote 경유)"


def chk_fred():
    """★[8/12 DRY 교정] 초판은 20초 타임아웃으로 직접 CSV를 받아 timeout 위양성을 냈다.
    macro_data.py는 같은 시각 정상 동작했다 → 본 스크립트 경로를 재사용한다."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import macro_data as M
    for fn in ("fetch_series", "fred_series", "get_series"):
        f = getattr(M, fn, None)
        if callable(f):
            try:
                r = f("DGS10")
                if r:
                    last = r[-1] if isinstance(r, list) else r
                    return True, f"DGS10 응답 ({fn} 경유)"
            except Exception:
                continue
    # 함수명이 다르면 CSV 직접(넉넉한 타임아웃)
    req = urllib.request.Request(
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=2026-08-01",
        headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = [x for x in r.read().decode("utf-8", "replace").strip().splitlines() if x]
    return True, f"DGS10 마지막 {rows[-1]}"


def chk_edgar():
    url = "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Revenues.json"
    st, body = _get(url, {"User-Agent": "portfolio-desk research contact@example.com"})
    d = json.loads(body)
    n = sum(len(v) for v in d.get("units", {}).values())
    return True, f"AAPL Revenues 데이터포인트 {n}개"


def chk_edgar_fts():
    url = "https://efts.sec.gov/LATEST/search-index?q=%22HBM4%22&forms=10-Q"
    try:
        st, body = _get("https://efts.sec.gov/LATEST/search-index?q=test", {"User-Agent": "portfolio-desk research"})
        return True, "FTS 엔드포인트 응답"
    except Exception:
        # 실제 검색 경로로 재시도
        st, body = _get("https://www.sec.gov/cgi-bin/srqsb?text=test", {"User-Agent": "portfolio-desk research"})
        return True, "FTS 대체 경로 응답"


def chk_youtube_rss():
    ch = "UC7usMJDHmtbs_oegmzQKKMA"
    st, body = _get(f"https://www.youtube.com/feeds/videos.xml?channel_id={ch}")
    n = body.count("<entry>")
    return n > 0, f"경제사냥꾼 RSS {n}건"


def chk_youtube_api():
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        return None, "키 미설정 — 폴백(RSS/스크레이프)으로 동작 중"
    ch = "UC7usMJDHmtbs_oegmzQKKMA"
    q = urllib.parse.urlencode({"key": key, "channelId": ch, "part": "snippet",
                                "type": "video", "order": "date", "maxResults": "3"})
    st, body = _get("https://www.googleapis.com/youtube/v3/search?" + q)
    d = json.loads(body)
    n = len(d.get("items", []))
    return n > 0, f"search.list {n}건 (키 {_mask(key)})"


def chk_youtube_captions():
    """innertube 자막 경로 — hunter_latest가 쓰는 실제 경로.
    ⚠️ 429 = 봇플래그(일시적 레이트리밋)이며 hunter_latest는 60→120→240초 백오프로 자동
    복구한다(8/12·8/13 실측 전부 복구).

    ★[8/13 수정 — 없는 장애를 만들지 않는다] 舊 구현은 10초 백오프 1회 후에도 429면
    **🔴 실패**로 찍었다. 그런데 실사용 백오프는 60초부터라 10초는 애초에 부족했고,
    같은 날 실제로는 자막 3건을 정상 추출한 상태에서 헬스체크만 빨간불이었다.
    상시 빨간불은 읽히지 않는다 — 이 도구가 잡아야 할 **진짜 죽음**(8/1 FMP형)을
    가리게 된다. ⇒ 429가 지속되면 실패가 아니라 **⚪(레이트리밋·폴백 동작)**로 보고한다.
    실패로 올려야 하는 건 429가 아니라 '자막 트랙 자체가 안 나오는' 경우다.
    (chk_naver 주석과 같은 원칙: 점검 도구가 본 스크립트와 다르게 굴면 없는 장애를 만든다.)"""
    url = "https://www.youtube.com/watch?v=lnU78beHI9E"
    try:
        st, body = _get(url)
    except urllib.error.HTTPError as e:
        if e.code != 429:
            raise
        time.sleep(10)
        try:
            st, body = _get(url)
        except urllib.error.HTTPError as e2:
            if e2.code != 429:
                raise
            return None, ("429 레이트리밋 지속 — 실패 아님. hunter_latest는 60~240초 "
                          "백오프로 복구한다(당일 자막 추출 실적으로 확인). 점검 시점만의 상태")
    ok = "captionTracks" in body or "playerCaptionsTracklistRenderer" in body
    return ok, "자막 트랙 노출" if ok else "자막 트랙 미노출(봇플래그 가능)"


def chk_naver():
    """⚠️ [8/12 자체 버그 교정] 초판이 레거시 openapi.naver.com + X-Naver-* 헤더를 써서
    401을 냈다. 실제 경로는 **NCP API HUB**(naverapihub.apigw.ntruss.com) + X-NCP-APIGW-* 헤더다.
    naver_data.py 주석에도 '레거시 naveropenapi/datalab(401 구독필요) 아님'이라 못 박혀 있었다.
    ⇒ 점검 도구가 본 스크립트와 다른 경로를 때리면 **없는 장애를 만든다**."""
    kid = os.environ.get("NAVER_NCP_KEY_ID", "").strip()
    ksec = os.environ.get("NAVER_NCP_KEY", "").strip()
    if not (kid and ksec):
        return None, "키 미설정 — WebSearch 폴백"
    url = "https://naverapihub.apigw.ntruss.com/search/v1/news?" + urllib.parse.urlencode(
        {"query": "삼성전자", "display": 1})
    try:
        _get(url, {"X-NCP-APIGW-API-KEY-ID": kid, "X-NCP-APIGW-API-KEY": ksec})
        return True, f"API HUB 뉴스 응답 (키 {_mask(kid)})"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} (401=키·구독 확인)"


def chk_dart():
    key = os.environ.get("DART_API_KEY", "").strip()
    if not key:
        return None, "키 미설정 — Yahoo/네이버 폴백"
    url = f"https://opendart.fss.or.kr/api/list.json?crtfc_key={key}&corp_code=00126380&bgn_de=20260801&page_count=1"
    st, body = _get(url)
    d = json.loads(body)
    return d.get("status") == "000", f"status={d.get('status')} {d.get('message','')[:30]}"


def chk_fmp():
    key = os.environ.get("FMP_API_KEY", "").strip()
    if not key:
        return None, "키 미설정 — EDGAR/Yahoo가 대체(8/1 확정: 유료전환 불필요)"
    url = f"https://financialmodelingprep.com/stable/quote?symbol=NVDA&apikey={key}"
    try:
        st, body = _get(url)
        d = json.loads(body)
        return bool(d), f"NVDA 응답 {len(d) if isinstance(d,list) else 1}건"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} (402=화이트리스트 밖 심볼)"


def chk_ytdlp():
    """yt-dlp 스트림/메타 경로 — youtube-watch(fetch_youtube.py)의 舊 단일 의존.

    ★[8/22 신설] 7/2 메모에 "웹에서 SSL_CERT_FILE 지정 시 yt-dlp 정상(3/3편)"이라
    적어둔 뒤 아무도 재확인하지 않았는데, 8/22 실측에서 web·android·ios·tv·mweb
    **5개 클라이언트 전부** 봇차단("Sign in to confirm you're not a bot")이었다.
    탐색·자막·스트림 어느 경로도 안 열린다. = 8/1 FMP형 '말없이 죽는 외부 도구'의 재발.
    ⇒ 이 체크가 그 침묵을 깬다. **실패해도 파이프라인은 정상**이다(innertube 폴백이
    받는다) → 그래서 🔴가 아니라 ⚪ 미설정으로 보고한다. 판단 기준은 하나:
    **✅로 바뀌면 프레임 추출(--frames)이 다시 가능해졌다는 뜻**(로컬 이전 후 기대)."""
    cmd = ytdlp_cmd()
    if not cmd:
        return None, "미설치 — youtube-watch는 innertube 폴백으로 동작(웹 환경 정상)"
    vid = "xwJio17IZZw"
    try:
        p = subprocess.run(cmd + ["--skip-download", "-J", "--no-warnings",
                            f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, timeout=90)
    except Exception as ex:
        return None, f"실행 실패: {str(ex)[:60]} — innertube 폴백 유효"
    if p.returncode == 0 and p.stdout.strip():
        # ⚠️ 8/22 "메타 성공 ≠ 생존" — `--ignore-no-formats-error` 탓에 봇차단 상태에서도
        # 메타는 통과한다. 프레임 추출이 실제로 가능한지는 **영상 포맷 유무**로 판정한다
        # (스토리보드 sb*는 CDN이라 차단돼도 남으므로 제외하고 센다).
        try:
            import json as _json
            fmts = _json.loads(p.stdout).get("formats") or []
            real = [f for f in fmts
                    if not str(f.get("format_id", "")).startswith("sb")
                    and (f.get("vcodec") not in (None, "none")
                         or f.get("acodec") not in (None, "none"))]
        except Exception:
            real = []
        if not real:
            return False, "메타만 통과·스트림 0개 = 봇차단(프레임 추출 불가)"
        return True, f"스트림 {len(real)}개 취득 — --frames(프레임 추출) 사용 가능"
    err = (p.stderr or "").strip().splitlines()
    head = err[-1][:80] if err else "무응답"
    return None, f"봇차단 지속 — innertube 폴백이 대체 중 ({head})"


def chk_web_shot():
    """웹 화면 판독 경로(Playwright+Chromium) — web_shot.py·browser_captions.cjs 공용 기반.
    ★[8/22 신설] 유튜브 영상 프레임은 불가(watch=reCAPTCHA)지만 **일반 웹페이지 캡처는 정상**이다.

    ★[9/1 정정 — 경로를 보지 말고 실제로 띄워본다] 舊 구현은 `/opt/pw-browsers/chromium-*/
    chrome-linux/chrome` 존재 여부로 판정했다. **리눅스 경로 규약에 기댄 검사**라 윈도우에선
    브라우저가 멀쩡히 설치되고 네이버금융 캡처가 실제로 성공하는데도 🔴를 냈다
    (8/31 "환경을 옮기면 실행파일 이름·경로에 기댄 코드가 먼저 틀린다"의 네 번째 사례).
    ⇒ 판정을 **최종 산출물**로 바꾼다 = 실제로 chromium을 띄워 페이지를 하나 연다.
    느리지만(1~3초) 이 검사의 존재 이유가 '조용히 죽는 것'을 잡는 것이므로 값을 치른다."""
    if not shutil.which("node"):
        return False, "node 없음 — web_shot·browser_captions 정지"
    probe = ("const{chromium}=require('playwright');"
             "chromium.launch({args:['--no-sandbox']}).then(async b=>{"
             "const p=await b.newPage();await p.setContent('<h1>ok</h1>');"
             "const t=await p.evaluate(()=>document.querySelector('h1').textContent);"
             "await b.close();console.log(t);})"
             ".catch(e=>{console.error(String(e.message).slice(0,120));process.exit(1)})")
    try:
        r = subprocess.run(["node", "-e", probe], capture_output=True, text=True,
                           timeout=90,
                           cwd=os.path.abspath(os.path.join(
                               os.path.dirname(os.path.abspath(__file__)),
                               "..", "..", "..", "..")))   # 레포 루트 = node_modules 위치
    except Exception as ex:
        return False, f"실행 실패: {str(ex)[:60]}"
    if r.returncode == 0 and "ok" in (r.stdout or ""):
        return True, "Chromium 기동·페이지 렌더 확인"
    err = ((r.stderr or "").strip().splitlines() or ["무응답"])[-1][:80]
    hint = " — `npm install playwright && npx playwright install chromium`"            if "Cannot find module" in err or "Executable doesn" in err else ""
    return False, f"기동 실패: {err}{hint}"


def chk_transcripts():
    """transcripts.py의 실제 경로 = {BASE}/company/{ticker}. 초판이 존재하지 않는
    /api/v1/transcripts를 때려 404를 냈다(자체 버그)."""
    st, body = _get("https://earningscalls.dev/company/mu")
    return len(body) > 500, f"company/mu 응답 {len(body):,}자"


CHECKS = [
    ("Yahoo 시세",            "무키", chk_yahoo,            "market_data·history·vol_gauge·chart_read"),
    ("FRED 매크로",           "무키", chk_fred,             "macro_data (금리·물가 하드넘버)"),
    ("SEC EDGAR XBRL",        "무키", chk_edgar,            "financials(US)·edgar_facts·guidance"),
    ("SEC EDGAR 전문검색",    "무키", chk_edgar_fts,        "edgar_search (공시 본문)"),
    ("YouTube RSS",           "무키", chk_youtube_rss,      "hunter_latest 1차 폴백"),
    ("YouTube Data API v3",   "키",   chk_youtube_api,      "hunter_latest 0차 경로 ★신규"),
    ("YouTube 자막(innertube)", "무키", chk_youtube_captions, "hunter_latest --fetch"),
    ("네이버 오픈API",        "키",   chk_naver,            "naver_data·naver_sentiment·naver_flows"),
    ("DART",                  "키",   chk_dart,             "dart_disclosure·financials(KR)"),
    ("FMP",                   "키",   chk_fmp,              "fundamentals·valuation (보조)"),
    ("earningscalls.dev",     "무키", chk_transcripts,      "transcripts (어닝콜 전문)"),
    ("yt-dlp 스트림",         "무키", chk_ytdlp,            "youtube-watch --frames/--comments"),
    ("웹 화면 판독",          "무키", chk_web_shot,         "web_shot·browser_captions (Playwright)"),
]


def main():
    ap = argparse.ArgumentParser(description="외부 데이터 소스 생존 점검 (측정 전용)")
    ap.add_argument("--quick", action="store_true", help="키 없는 무료 소스만")
    ap.add_argument("--json", action="store_true", help="기계 판독 출력")
    a = ap.parse_args()

    results = []
    for name, kind, fn, used_by in CHECKS:
        if a.quick and kind == "키":
            continue
        t0 = time.time()
        try:
            ok, msg = fn()
        except Exception as ex:
            ok, msg = False, f"{type(ex).__name__}: {str(ex)[:70]}"
        results.append({"name": name, "kind": kind, "ok": ok, "msg": msg,
                        "used_by": used_by, "ms": int((time.time() - t0) * 1000)})
        time.sleep(0.2)

    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return 0

    print("=" * 76)
    print("  외부 데이터 소스 생존 점검 (api_health.py) — 실호출 기준")
    print("=" * 76)
    up = down = skip = 0
    for r in results:
        if r["ok"] is None:
            mark, skip = "⚪ 미설정", skip + 1
        elif r["ok"]:
            mark, up = "✅ 정상", up + 1
        else:
            mark, down = "🔴 실패", down + 1
        print(f"{mark:9} {r['name']:22} {r['ms']:>5}ms  {r['msg'][:52]}")
        print(f"{'':9} └ 사용처: {r['used_by']}")
    print("-" * 76)
    print(f"정상 {up} · 실패 {down} · 미설정(폴백 동작) {skip}")
    if down:
        print("\n🔴 실패 항목은 해당 레이어가 폴백으로 도는지 확인할 것 —")
        print("   폴백이 없으면 그 데이터는 조용히 낡는다(8/12 history 67종목 사고).")
    return 1 if down else 0


if __name__ == "__main__":
    sys.exit(main())
