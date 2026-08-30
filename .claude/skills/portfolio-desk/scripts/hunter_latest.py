#!/usr/bin/env python3
"""유튜브 리서치 채널 신규 영상·쇼츠 자동 탐색 + 자막 추출 (기본 = 경제사냥꾼).

[7/7 다채널 확장] --channel <slug> 로 등록 채널 선택 (기본 hunter = 경제사냥꾼, 완전 하위호환).
등록 채널: hunter(경제사냥꾼) / supe(수페TV) / jisik(지식인사이드, 투자 시리즈 제목필터).
신규 채널 md는 OUTDIR/<slug>/ 서브폴더에 저장 (hunter는 기존 경로 유지).

[7/2 전면 개편 — yt-dlp 단일의존 제거, 웹(데이터센터 IP) 환경 실측 검증]
[★8/13 갱신 — 탐색 차선 순서 정정. 舊 "① RSS ← 1차"는 더 이상 사실이 아니다]
탐색 차선 (앞 차선 실패 시 자동 폴백):
  ⓪ **YouTube Data API v3** (`YOUTUBE_API_KEY`)  ← **현행 0차·유일하게 안정**
     날짜구간 전량 열거(--after/--before)·--catchup이 되는 유일한 경로.
  ① RSS(feeds/videos.xml)                        ← ⚠️ **8/12 이후 3채널 전부 HTTP 404 지속**
     (8/13 재확인: 3회 연속 404). 죽은 경로로 간주하되, 복구될 수 있으니 남겨 둔다.
  ② 채널 페이지 스크레이프(discover_pagescrape)  ← 최근 ~30편만 보임(과거 소급 불가)
  ③ yt-dlp (설치돼 있을 때만)                     ← 보조
자막: innertube(ANDROID→IOS). 페이싱 8~15초 + 지수백오프(60→120→240초).
핵심 실측 사실:
  - ⚠️ **舊 "RSS는 봇차단 대상이 아님(항상 200)"은 폐기된 서술이다.** 8/12부터 404가
    고착됐고 채널 페이지는 200이라 IP 차단이 아니라 엔드포인트 문제로 판단된다.
    `api_health.py`의 "YouTube RSS ❌"는 오류가 아니라 **이 사실의 정상 보고**다.
  - innertube "봇차단"의 실체 = 버스트 레이트리밋. 짧은 시간 12연속 호출 시
    LOGIN_REQUIRED 발생하나, 페이싱(영상 간 8~15초) + 지수백오프(60→120→240초)로 복구됨.
  - watch 페이지 HTML의 caption URL은 pot 토큰 요구로 빈 응답 → 쓰지 않는다.
    innertube ANDROID 클라이언트의 baseUrl은 pot 불필요(전문 추출 실측 성공).
  - "제목만 로깅" 폴백은 폐지. 자막 미확보 영상은 FAILED로 표기하고 재시도가 원칙.

사용:
  python3 hunter_latest.py                  # 최신 목록만 (RSS, 날짜 포함)
  python3 hunter_latest.py --fetch --max 9  # 자막까지 추출 → 임시폴더/*.md
  python3 hunter_latest.py --channel supe --fetch --max 2   # 수페TV
  python3 hunter_latest.py --channel jisik --fetch --max 3  # 지식인사이드(필터 적용)
"""
import argparse, html, json, os, random, re, shutil, ssl, subprocess, sys, tempfile, time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta, timezone

# 채널 레지스트리. title_filter(정규식)가 있으면 매칭 안 되는 영상은 자막 추출에서 제외
# (목록 JSON엔 filtered:true 로 표기만). 자산제곱(UCpTC-SMFjA3EDRhZIKOcKuQ)은 7/7 판단으로
# 미편입 — 원칙론 위주·종목 콜 부재. 편입하려면 여기 한 줄 추가면 된다.
CHANNELS = {
    "hunter": {"id": "UC7usMJDHmtbs_oegmzQKKMA", "name": "경제사냥꾼"},
    "supe":   {"id": "UCfnqgWlC5IvJEAPTmyjaixA", "name": "수페TV"},
    # 지식인사이드는 비투자 콘텐츠(심리·건강·역사)가 절반 이상 → 투자 키워드 필터.
    # [7/26 교정] 舊 필터는 시리즈명(지식인클래스·지식선발대)을 '금융 전용'으로 보고 통과시켰으나
    # feeds_log 실측 3건(7/21 지식선발대 EP.5 커리어·7/22 성수동 지식클럽·7/24 지식인클래스 EP.10 한글사)
    # 전부 비투자 → 자막 추출만 낭비. 시리즈명을 통과 키워드에서 제거하고, 비투자 시리즈는
    # title_exclude로 명시 차단한다. 단 그 시리즈라도 제목에 실제 투자 키워드가 있으면 통과(오차단 방지).
    "jisik":  {"id": "UCA_hgsFzmynpv1zkvA5A7jA", "name": "지식인사이드",
               "title_filter": r"투자|증시|증권|주식|주가|코스피|코스닥|반도체|삼성전자|하이닉스|삼전"
                               r"|매수|매도|배당|ETF|금리|환율|부동산|자산|버블|경제|폭락|급등|연준|달러",
               "title_exclude": r"지식선발대|성수동\s?지식클럽"},
}
# title_exclude(비투자 시리즈)를 무시하고 통과시키는 '강한' 투자 키워드 — 오차단 방지.
# 약한 키워드(경제·자산·투자 등 일반어)는 여기 넣지 않는다(비투자 회차 제목에도 흔히 등장).
HARD_KW = re.compile(r"증시|주식|주가|코스피|코스닥|반도체|삼성전자|하이닉스|삼전|매수|매도"
                     r"|배당|ETF|금리|환율|연준|달러|폭락|급등|채권|실적")

CHANNEL = CHANNELS["hunter"]["id"]  # --channel 인자로 재설정됨 (기본 = 경제사냥꾼)
CHANNEL_NAME = CHANNELS["hunter"]["name"]
TITLE_FILTER = None
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
KST = timezone(timedelta(hours=9))


def rss_url():
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL}"

HERE = os.path.dirname(os.path.abspath(__file__))
YW_SCRIPT = os.environ.get(
    "YW_FETCH_SCRIPT",
    os.path.normpath(os.path.join(HERE, "..", "..", "youtube-watch", "scripts", "fetch_youtube.py")),
)
BROWSER_SCRIPT = os.path.join(HERE, "browser_captions.cjs")
# ★[8/30 정훈 지적 "데이터는 다 저장해두라고 했잖아"] 기본 저장 위치를 **레포 안**으로 옮긴다.
# 舊 기본값은 tempfile.gettempdir()이라 **세션이 끝나면 자막이 통째로 사라졌다.**
# 그 결과 8/13(d101)에 이미 "94건 자막 재추출 = 1시간+"의 비용을 치렀고,
# 8/30엔 아카이브 648편 중 원문이 **0편** 남아 재분석이 메타데이터로 제한됐다.
# 8/14(d113) 교훈 *"저장은 조회의 부산물이어야 한다"*를 같은 도구군에 적용하지 않은 것이 원인.
# 자막은 텍스트(편당 ~5KB)라 648편이어도 ~3MB — 레포에 담기에 무해하다.
_REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
OUTDIR = os.environ.get("HUNTER_OUTDIR", os.path.join(_REPO, "data", "transcripts", "hunter"))

# 페이싱: 영상 간 간격(초). 버스트 레이트리밋 방지 — 실측상 8초 미만 연속 호출이 위험.
PACE_MIN, PACE_MAX = 8, 15
BACKOFFS = (60, 120, 240)  # LOGIN_REQUIRED(봇플래그) 시 대기 후 재시도

_INSECURE = os.environ.get("HUNTER_INSECURE") == "1"
_VISITOR_DATA = None


def _ssl_ctx():
    if _INSECURE:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    cafile = os.environ.get("SSL_CERT_FILE")
    if not cafile and os.path.exists("/root/.ccr/ca-bundle.crt"):
        cafile = "/root/.ccr/ca-bundle.crt"  # 웹 프록시 CA. 로컬(직결)에선 없음 → 기본 스토어
    return ssl.create_default_context(cafile=cafile)


def http(url, data=None, headers=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as r:
        return r.read().decode("utf-8", "replace")


# ── ① 탐색: RSS ────────────────────────────────────────────────────────────

def discover_rss():
    """RSS로 최신 업로드(영상+쇼츠 통합, 최대 15개) 목록. published는 KST 변환."""
    xml = http(rss_url())
    items = []
    for e in re.findall(r"<entry>.*?</entry>", xml, re.S):
        vid = re.search(r"<yt:videoId>([^<]+)", e)
        title = re.search(r"<title>([^<]+)", e)
        pub = re.search(r"<published>([^<]+)", e)
        if not (vid and title and pub):
            continue
        dt = datetime.fromisoformat(pub.group(1)).astimezone(KST)
        items.append({"id": vid.group(1), "title": html.unescape(title.group(1)),
                      "published_kst": dt.strftime("%Y-%m-%d %H:%M"), "tab": "rss"})
    return items


def discover_catchup(per_tab=50):
    """★[2026-08-12 신설] **마지막 수집 이후 전량**을 가져온다 — 누락의 근본 해소.

    8/12 감사에서 확인된 구조적 누락 86건(커버리지 73%)의 원인은 둘이었다:
      ① R1이 평일만 실행 → 누락의 28%가 토·일 업로드
      ② `--max 10` 상한 + 저녁 몰림 → 39%가 17시 이후.
         SKILL의 *"저녁분은 다음날 R1이 커버"* 전제가 **다음날도 10편 상한**이라 깨졌다.
         (누락이 월·화에 집중된 것이 증거 — 주말 누적분이 월요일 상한에 걸린다)

    ⇒ 고정 편수(N편)가 아니라 **아카이브의 마지막 날짜 이후 전부**를 가져온다.
       월요일이면 금~일 3일치가 통째로 들어오고, 연휴 뒤엔 그만큼 더 들어온다.
       API가 있어야 가능하다(RSS·스크레이프는 최신 N편만 보여준다).

    키가 없으면 빈 리스트 → 기존 폴백 흐름 유지.
    """
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        return []
    # 아카이브 최신 날짜 = 우리가 마지막으로 본 지점
    try:
        import json as _j
        arc = _j.load(open(os.path.join(REPO_ROOT, "data", "app", "hunter_archive.json"), encoding="utf-8"))
        dates = [v.get("date") for v in arc.get("videos", []) if v.get("date")]
        last = max(dates) if dates else None
    except Exception:
        last = None
    if not last:
        return discover_api(per_tab)
    # 마지막 날 당일도 다시 훑는다(그날 저녁분이 빠졌을 수 있으므로)
    after = f"{last}T00:00:00+09:00"
    after = datetime.fromisoformat(after).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = discover_api(per_tab, after, None)
    if items:
        print(f"[INFO] catchup: 아카이브 최신({last}) 이후 {len(items)}건 열거", file=sys.stderr)
    return items


def discover_api(per_tab=15, published_after=None, published_before=None):
    """탐색 0차: **YouTube Data API v3** (환경변수 `YOUTUBE_API_KEY` 있을 때만).

    ★[2026-08-12 신설] 이 경로가 필요한 이유는 두 가지다.
    ① **안정성** — 8/12에 RSS가 3채널 동시 404, yt-dlp도 동시 실패해 무인 R1이
       조용히 죽을 뻔했다. 공식 API는 그 경로들과 독립이라 1차로 두면 가장 안전하다.
    ② **과거 구간 열거** — 페이지 스크레이프는 최근 30편만 보여서 6주 전 영상을 못 찾는다.
       `publishedAfter/Before`로 **날짜 구간 전량**(쇼츠 포함)을 뽑을 수 있는 건 이 경로뿐이다.
       실제로 8/12에 7/1 영상 3건을 끝내 특정 못 해 `미채점(원본 특정 실패)`로 남겼다.

    키가 없으면 조용히 빈 리스트를 반환한다 → 기존 RSS·yt-dlp·스크레이프 폴백이 그대로 동작.
    할당량: search.list 1회 = 100 units / 일 10,000 units(무료) → 하루 100회, 우리 용도엔 충분.
    """
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        return []
    params = {
        "key": key, "channelId": CHANNEL, "part": "snippet", "type": "video",
        "order": "date", "maxResults": str(min(max(per_tab, 1), 50)),
    }
    if published_after:
        params["publishedAfter"] = published_after
    if published_before:
        params["publishedBefore"] = published_before
    url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(params)
    try:
        data = json.loads(http(url))
    except Exception as ex:
        print(f"[WARN] YouTube Data API 실패({ex}) — 키/할당량 확인 후 폴백 진행", file=sys.stderr)
        return []
    items = []
    for it in data.get("items", []):
        vid = (it.get("id") or {}).get("videoId")
        sn = it.get("snippet") or {}
        if not vid:
            continue
        pub = sn.get("publishedAt", "")
        try:
            kst = datetime.fromisoformat(pub.replace("Z", "+00:00")).astimezone(KST).strftime("%Y-%m-%d %H:%M")
        except Exception:
            kst = "?"
        items.append({"id": vid, "title": html.unescape(sn.get("title", "")),
                      "published_kst": kst, "tab": "api"})
    return items


def discover_pagescrape(per_tab=15):
    """폴백②: 채널 /videos·/shorts 페이지 HTML에서 videoId 직접 추출.

    ★[2026-08-12 실사고] YouTube **RSS(feeds/videos.xml)가 3개 채널 전부 HTTP 404**로
    죽었다(채널 페이지는 200 = 차단이 아니라 엔드포인트 문제). yt-dlp 폴백도 동시 실패해
    `[FAIL] 탐색 전부 실패`가 났고, 그대로 뒀으면 **다음날 R1이 무인으로 조용히 실패**했다.

    ⚠️ 한계 — 이 경로는 **ID만** 준다. YouTube가 채널 그리드를 신규 레이아웃으로 바꿔
    `ytInitialData`의 `videoRenderer`가 없어 제목·게시시각은 못 얻는다(실측 확인).
    ID만 있으면 `--ids`/`--fetch` 경로로 자막·메타는 정상 취득되므로 탐색용으로는 충분하다.
    published_kst='?'라 날짜 필터를 못 거니 **캐시 대조로 신규만 골라내는 용도**로 쓴다.
    """
    items, seen = [], set()
    for tab in ("videos", "shorts"):
        try:
            h = http(f"https://www.youtube.com/channel/{CHANNEL}/{tab}")
        except Exception as ex:
            print(f"[WARN] 페이지 스크레이프 실패({tab}): {ex}", file=sys.stderr)
            continue
        for vid in re.findall(r'"videoId":"([\w-]{11})"', h):
            if vid in seen:
                continue
            seen.add(vid)
            items.append({"id": vid, "title": "", "published_kst": "?", "tab": tab + ":scrape"})
            if len([i for i in items if i["tab"].startswith(tab)]) >= per_tab:
                break
    return items


def discover_ytdlp(per_tab):
    """폴백: yt-dlp flat-playlist (설치돼 있을 때만)."""
    if not shutil.which("yt-dlp"):
        return []
    items = []
    for tab in ("videos", "shorts"):
        url = f"https://www.youtube.com/channel/{CHANNEL}/{tab}"
        try:
            r = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--playlist-items", f"1-{per_tab}",
                 "--print", "%(id)s\t%(title)s", url],
                capture_output=True, text=True, timeout=180)
            for line in r.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    items.append({"id": parts[0], "title": parts[1],
                                  "published_kst": "?", "tab": tab})
        except Exception as ex:
            print(f"[WARN] yt-dlp {tab} 탐색 실패: {ex}", file=sys.stderr)
    return items


# ── ② 자막: innertube (ANDROID → IOS) ─────────────────────────────────────

INNERTUBE_CLIENTS = [
    {"clientName": "ANDROID", "clientVersion": "20.10.38", "androidSdkVersion": 30},
    {"clientName": "IOS", "clientVersion": "20.10.4", "deviceMake": "Apple",
     "deviceModel": "iPhone16,2", "osName": "iPhone", "osVersion": "18.3.2.22D82"},
]


def innertube_player(vid, client):
    global _VISITOR_DATA
    ctx = {"client": dict(client, hl="ko")}
    if _VISITOR_DATA:
        ctx["client"]["visitorData"] = _VISITOR_DATA
    body = json.dumps({"context": ctx, "videoId": vid}).encode()
    out = http("https://www.youtube.com/youtubei/v1/player?prettyPrint=false",
               data=body, headers={"Content-Type": "application/json"})
    d = json.loads(out)
    vd = d.get("responseContext", {}).get("visitorData")
    if vd:
        _VISITOR_DATA = vd  # 세션 일관성 — 이후 요청에 재사용
    return d


def parse_timedtext(raw):
    """timedtext 응답(json3 또는 srv3 XML) → 평문 트랜스크립트."""
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith("{"):
        d = json.loads(raw)
        evs = [e for e in d.get("events", []) if e.get("segs")]
        text = " ".join("".join(s.get("utf8", "") for s in e["segs"]) for e in evs)
        return " ".join(text.split())
    segs = re.findall(r"<s[^>]*>([^<]*)</s>", raw)
    if not segs:
        segs = re.findall(r"<p[^>]*>([^<]*)</p>", raw)
    return html.unescape(" ".join(" ".join(segs).split()))


def fetch_via_innertube(vid):
    """innertube 자막. LOGIN_REQUIRED(봇플래그)면 백오프 후 재시도. 성공 시 (제목, 날짜, 전문)."""
    attempts = [0] + list(BACKOFFS)
    for i, wait in enumerate(attempts):
        if wait:
            print(f"[INFO] 봇플래그 감지 — {wait}초 백오프 후 재시도 ({i}/{len(BACKOFFS)})",
                  file=sys.stderr)
            time.sleep(wait)
        flagged = False
        for client in INNERTUBE_CLIENTS:
            try:
                d = innertube_player(vid, client)
            except Exception as ex:
                print(f"[WARN] innertube {client['clientName']} 오류: {ex}", file=sys.stderr)
                continue
            status = d.get("playabilityStatus", {}).get("status")
            if status == "LOGIN_REQUIRED":
                flagged = True
                break  # 클라이언트 바꿔도 IP 플래그는 동일 — 백오프로
            tracks = (d.get("captions", {})
                       .get("playerCaptionsTracklistRenderer", {})
                       .get("captionTracks", []))
            if not tracks:
                continue
            tracks.sort(key=lambda t: (t.get("languageCode") != "ko",))
            try:
                raw = http(tracks[0]["baseUrl"] + "&fmt=json3", timeout=40)
            except Exception as ex:
                print(f"[WARN] timedtext 오류: {ex}", file=sys.stderr)
                continue
            text = parse_timedtext(raw)
            if len(text) <= 50:
                # json3 응답 이상(유튜브 내부 포맷 변경이 잦음 — 2026 상반기 다수 보고)
                # → 같은 트랙을 srv3 XML로 재시도 (parse_timedtext가 둘 다 파싱)
                try:
                    text = parse_timedtext(http(tracks[0]["baseUrl"] + "&fmt=srv3", timeout=40))
                except Exception as ex:
                    print(f"[WARN] srv3 폴백 오류: {ex}", file=sys.stderr)
            if len(text) > 50:
                det = d.get("videoDetails", {})
                mf = (d.get("microformat", {}).get("playerMicroformatRenderer", {})
                      .get("publishDate", ""))
                return det.get("title", ""), mf, text
        if not flagged:
            return None  # 자막 트랙 자체가 없는 영상 — 백오프해도 소용없음
    return None


# ── ②' 자막 폴백: Playwright 브라우저 / yt-dlp ────────────────────────────

def fetch_via_browser(vid):
    if not os.path.exists(BROWSER_SCRIPT) or not shutil.which("node"):
        return None
    env = dict(os.environ,
               NODE_PATH=os.environ.get("NODE_PATH", "/opt/node22/lib/node_modules"),
               NODE_USE_ENV_PROXY="1")
    if os.path.exists("/root/.ccr/ca-bundle.crt"):
        env.setdefault("NODE_EXTRA_CA_CERTS", "/root/.ccr/ca-bundle.crt")
    try:
        r = subprocess.run(["node", BROWSER_SCRIPT, vid], capture_output=True,
                           text=True, timeout=180, env=env)
        out = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {}
        if out.get("text") and len(out["text"]) > 50:
            return out.get("title", ""), out.get("date", ""), out["text"]
    except Exception as ex:
        print(f"[WARN] 브라우저 폴백 실패({vid}): {ex}", file=sys.stderr)
    return None


def fetch_via_ytdlp(vid):
    if not shutil.which("yt-dlp"):
        return None
    url = f"https://www.youtube.com/watch?v={vid}"
    if os.path.exists(YW_SCRIPT):
        try:
            # 재귀 차단: fetch_youtube는 실패 시 hunter_latest(=이 파일)를 되부른다.
            env = dict(os.environ, YW_NO_INNERTUBE_FALLBACK="1")
            # 인터프리터는 sys.executable로 — "python3"는 윈도우 로컬에 없어
            # 이 경로가 조용히 죽는다(except Exception: pass에 먹힘).
            r = subprocess.run([sys.executable, YW_SCRIPT, url, "--outdir", OUTDIR],
                               capture_output=True, text=True, timeout=240, env=env)
            for line in r.stdout.strip().splitlines()[::-1]:
                p = line.strip()
                if p.endswith(".md") and os.path.exists(p):
                    return ("", "", open(p, encoding="utf-8").read())
        except Exception:
            pass
    return None


def fetch_transcript(vid, title_hint=""):
    """3중 차선 자막 확보 → md 파일 경로. 실패 시 None (제목 기반 추측 분석 금지)."""
    os.makedirs(OUTDIR, exist_ok=True)
    got = fetch_via_innertube(vid) or fetch_via_browser(vid) or fetch_via_ytdlp(vid)
    if not got:
        return None
    title, date, text = got
    md = os.path.join(OUTDIR, f"{vid}.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# {title or title_hint}\n"
                f"- 채널: {CHANNEL_NAME}\n"
                f"- URL: https://www.youtube.com/watch?v={vid}\n"
                f"- 업로드: {date or '?'}\n\n## 트랜스크립트\n\n{text}\n")
    return md


# ── main ───────────────────────────────────────────────────────────────────

def main():
    global CHANNEL, CHANNEL_NAME, TITLE_FILTER, OUTDIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--catchup", action="store_true",
                    help="아카이브 최신 날짜 이후 전량 수집(고정 N편 상한 대신) — 주말·저녁 누락 해소용. API 키 필요")
    ap.add_argument("--after", help="RFC3339 시각 이후 업로드분만 (YouTube Data API 경로 전용, 예 2026-07-01T00:00:00Z)")
    ap.add_argument("--before", help="RFC3339 시각 이전 업로드분만 (과거 구간 소급 탐색용)")
    ap.add_argument("--channel", default="hunter", choices=sorted(CHANNELS),
                    help="채널 slug (기본 hunter=경제사냥꾼)")
    ap.add_argument("--fetch", action="store_true", help="자막까지 추출")
    ap.add_argument("--max", type=int, default=4, help="자막 추출 최대 개수")
    ap.add_argument("--per-tab", type=int, default=6, help="(yt-dlp 폴백용) 탭당 목록 개수")
    ap.add_argument("--ids", help="쉼표구분 영상 ID 직접 지정(목록 탐색 생략)")
    ap.add_argument("--all-dates", action="store_true",
                    help="오늘/어제 필터 없이 RSS 전체를 자막 대상에 포함")
    ap.add_argument("--since-days", type=int, default=None,
                    help="며칠 전 업로드까지 자막 대상에 포함(기본: 1일, 월요일은 주말 커버로 3일)")
    ap.add_argument("--archive-backfill", type=int, metavar="N", default=None,
                    help="★[8/30] 아카이브에 있으나 **자막 원문이 없는** 과거 영상 N편을 소급 수집. "
                         "舊 기본 저장경로가 /tmp라 648편 중 원문이 0편 남은 사고의 회수 경로 "
                         "(429 페이싱 탓에 한 번에 다 못 받는다 → R1이 매일 소량씩 호출)")
    args = ap.parse_args()

    # ── 아카이브 소급 회수 ──────────────────────────────────────────────
    # 신규 탐색을 건너뛰고 "자막이 없는 과거 id"만 골라 --ids 경로로 흘린다.
    # ⚠️ 오래된 것부터 채운다 — 최신분은 어차피 R1이 매일 받는다.
    if args.archive_backfill:
        arch = os.path.join(_REPO, "data", "app", "hunter_archive.json")
        try:
            with open(arch, encoding="utf-8") as f:
                vids = (json.load(f) or {}).get("videos") or []
        except Exception as e:
            print(f"[archive-backfill] 아카이브를 읽지 못했다: {e}")
            return 1
        have = set()
        if os.path.isdir(OUTDIR):
            have = {fn[:-3] for fn in os.listdir(OUTDIR) if fn.endswith(".md")}
        todo = [v for v in vids if v.get("id") and v["id"] not in have]
        todo.sort(key=lambda v: v.get("date") or "")
        pick = todo[:args.archive_backfill]
        if not pick:
            print("[archive-backfill] 회수할 영상 없음 — 아카이브 자막 커버리지 100%")
            return 0
        print(f"[archive-backfill] 미보유 {len(todo)}편 중 {len(pick)}편 소급 (오래된 순) "
              f"→ 저장 {OUTDIR}")
        args.ids = ",".join(v["id"] for v in pick)
        args.fetch = True
        args.all_dates = True
        args.max = len(pick)

    ch = CHANNELS[args.channel]
    CHANNEL, CHANNEL_NAME = ch["id"], ch["name"]
    TITLE_FILTER = re.compile(ch["title_filter"]) if ch.get("title_filter") else None
    TITLE_EXCLUDE = re.compile(ch["title_exclude"]) if ch.get("title_exclude") else None
    if args.channel != "hunter":  # hunter는 기존 경로 유지(하위호환)
        OUTDIR = os.path.join(OUTDIR, args.channel)

    if args.ids:
        items = [{"id": v, "title": "", "published_kst": "?", "tab": "manual"}
                 for v in args.ids.split(",") if v.strip()]
    else:
        # 0차 = 공식 API(키 있을 때만). 없으면 즉시 빈 리스트라 기존 흐름 그대로.
        if getattr(args, "catchup", False):
            items = discover_catchup(max(args.per_tab, 50))
        else:
            items = discover_api(args.per_tab, getattr(args, "after", None), getattr(args, "before", None))
        if items:
            print(f"[INFO] YouTube Data API 경로로 {len(items)}건 탐색", file=sys.stderr)
        try:
            if not items:
                items = discover_rss()
        except Exception as ex:
            print(f"[WARN] RSS 탐색 실패({ex}) — yt-dlp 폴백", file=sys.stderr)
            items = []
        if not items:
            items = discover_ytdlp(args.per_tab)
        if not items:
            # ★[8/12] RSS·yt-dlp가 동시에 죽는 경우가 실제로 나왔다 → 페이지 스크레이프 3차 폴백.
            print("[WARN] RSS·yt-dlp 모두 실패 — 채널 페이지 스크레이프 폴백(ID만 취득)",
                  file=sys.stderr)
            items = discover_pagescrape(args.per_tab)
        if not items:
            print(f"[FAIL] 채널({CHANNEL_NAME}) 탐색 전부 실패 — 웹검색 폴백 사용 권장 "
                  f"(검색어: {CHANNEL_NAME} + 주제 + 날짜)")
            sys.exit(1)

    if TITLE_FILTER or TITLE_EXCLUDE:
        for it in items:
            if not it["title"]:
                continue
            hit = TITLE_FILTER.search(it["title"]) if TITLE_FILTER else True
            if not hit:
                it["filtered"] = True  # 비투자 콘텐츠 — 목록엔 남기고 자막은 스킵
            elif (TITLE_EXCLUDE and TITLE_EXCLUDE.search(it["title"])
                  and not HARD_KW.search(it["title"])):
                # 비투자 시리즈 — 단 제목에 강한 투자 키워드(종목·증시 용어)가 있으면 오차단 방지로 통과.
                it["filtered"] = True
                it["filter_reason"] = "비투자 시리즈"

    print(json.dumps(items, ensure_ascii=False, indent=1))

    if args.fetch:
        today = datetime.now(KST).date()
        # [7/26 교정] 기본 창 = 전일~오늘. 단 **월요일엔 토요일 업로드가 창 밖으로 떨어진다**
        # (R1은 평일 10:00만 실행 → 월요일 today-1 = 일요일까지만 봄). 지금까진 주말 보고서
        # 세션이 우연히 메워왔다(예: 7/18 토 업로드 = v53 토요 세션이 발견해 track_record 기입)
        # — 즉 구조적으로는 '주말 세션이 없으면 유실'인 상태였다. 월요일은 3일로 자동 확장한다.
        span = args.since_days if args.since_days is not None else (3 if today.weekday() == 0 else 1)
        targets = []
        for it in items:
            if it.get("filtered"):
                continue
            if args.ids or args.all_dates or it["published_kst"] == "?":
                targets.append(it)
            else:
                d = datetime.strptime(it["published_kst"][:10], "%Y-%m-%d").date()
                if (today - d).days <= span:
                    targets.append(it)
        targets = targets[: args.max]
        print(f"\n--- 자막 추출 ({len(targets)}편, 영상 간 {PACE_MIN}~{PACE_MAX}초 페이싱) ---")
        failed = []
        for i, it in enumerate(targets):
            if i:
                time.sleep(random.uniform(PACE_MIN, PACE_MAX))
            path = fetch_transcript(it["id"], it["title"])
            print(f"{it['id']} [{it['published_kst']}] {it['title'][:40]}: {path or 'FAILED'}")
            if not path:
                failed.append(it["id"])
        if failed:
            print(f"\n[RETRY] 미확보 {len(failed)}편: {','.join(failed)}\n"
                  f"→ 같은 세션에서 몇 분 뒤 --ids {','.join(failed)} 로 재시도할 것. "
                  f"제목만 보고 분석 금지.")
        print("\n→ 생성된 md를 읽고 업로드 날짜 기준 당일/전일 영상만 보고서에 반영. "
              "자동자막 수치는 교차검증 필수.")


if __name__ == "__main__":
    main()
