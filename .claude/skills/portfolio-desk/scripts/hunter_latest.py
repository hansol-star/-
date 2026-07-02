#!/usr/bin/env python3
"""경제사냥꾼 채널 신규 영상·쇼츠 자동 탐색 + 자막 추출.

[7/2 전면 개편 — yt-dlp 단일의존 제거, 웹(데이터센터 IP) 환경 실측 검증]
탐색·자막 3중 차선 (앞 차선 실패 시 자동 폴백):
  ① RSS(feeds/videos.xml) 탐색 + innertube(ANDROID→IOS) 자막  ← 1차, stdlib만, 봇차단 무관
  ② Playwright 헤드리스 크롬(browser_captions.cjs)             ← 봇플래그 장기화 보험
  ③ yt-dlp (설치돼 있을 때만)                                   ← 보조
핵심 실측 사실:
  - RSS는 봇차단 대상이 아님(항상 200). 채널 최신 15개(영상+쇼츠) 포함.
  - innertube "봇차단"의 실체 = 버스트 레이트리밋. 짧은 시간 12연속 호출 시
    LOGIN_REQUIRED 발생하나, 페이싱(영상 간 8~15초) + 지수백오프(60→120→240초)로 복구됨.
  - watch 페이지 HTML의 caption URL은 pot 토큰 요구로 빈 응답 → 쓰지 않는다.
    innertube ANDROID 클라이언트의 baseUrl은 pot 불필요(전문 추출 실측 성공).
  - "제목만 로깅" 폴백은 폐지. 자막 미확보 영상은 FAILED로 표기하고 재시도가 원칙.

사용:
  python3 hunter_latest.py                  # 최신 목록만 (RSS, 날짜 포함)
  python3 hunter_latest.py --fetch --max 9  # 자막까지 추출 → 임시폴더/*.md
"""
import argparse, html, json, os, random, re, shutil, ssl, subprocess, sys, tempfile, time
import urllib.request
from datetime import datetime, timedelta, timezone

CHANNEL = "UC7usMJDHmtbs_oegmzQKKMA"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL}"
KST = timezone(timedelta(hours=9))

HERE = os.path.dirname(os.path.abspath(__file__))
YW_SCRIPT = os.environ.get(
    "YW_FETCH_SCRIPT",
    os.path.normpath(os.path.join(HERE, "..", "..", "youtube-watch", "scripts", "fetch_youtube.py")),
)
BROWSER_SCRIPT = os.path.join(HERE, "browser_captions.cjs")
OUTDIR = os.environ.get("HUNTER_OUTDIR", os.path.join(tempfile.gettempdir(), "hunter_yt"))

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
    xml = http(RSS_URL)
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
            r = subprocess.run(["python3", YW_SCRIPT, url, "--outdir", OUTDIR],
                               capture_output=True, text=True, timeout=240)
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
                f"- URL: https://www.youtube.com/watch?v={vid}\n"
                f"- 업로드: {date or '?'}\n\n## 트랜스크립트\n\n{text}\n")
    return md


# ── main ───────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="자막까지 추출")
    ap.add_argument("--max", type=int, default=4, help="자막 추출 최대 개수")
    ap.add_argument("--per-tab", type=int, default=6, help="(yt-dlp 폴백용) 탭당 목록 개수")
    ap.add_argument("--ids", help="쉼표구분 영상 ID 직접 지정(목록 탐색 생략)")
    ap.add_argument("--all-dates", action="store_true",
                    help="오늘/어제 필터 없이 RSS 전체를 자막 대상에 포함")
    args = ap.parse_args()

    if args.ids:
        items = [{"id": v, "title": "", "published_kst": "?", "tab": "manual"}
                 for v in args.ids.split(",") if v.strip()]
    else:
        try:
            items = discover_rss()
        except Exception as ex:
            print(f"[WARN] RSS 탐색 실패({ex}) — yt-dlp 폴백", file=sys.stderr)
            items = discover_ytdlp(args.per_tab)
        if not items:
            print("[FAIL] 채널 탐색 전부 실패 — 웹검색 폴백 사용 권장 "
                  "(검색어: 경제사냥꾼 + 주제 + 날짜)")
            sys.exit(1)

    print(json.dumps(items, ensure_ascii=False, indent=1))

    if args.fetch:
        today = datetime.now(KST).date()
        targets = []
        for it in items:
            if args.ids or args.all_dates or it["published_kst"] == "?":
                targets.append(it)
            else:
                d = datetime.strptime(it["published_kst"][:10], "%Y-%m-%d").date()
                if (today - d).days <= 1:
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
