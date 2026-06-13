#!/usr/bin/env python3
"""경제사냥꾼 채널 신규 영상·쇼츠 자동 탐색 + 자막 추출.

검증된 우회법 (원래 claude.ai 샌드박스 테스트 기준):
- 채널 목록: yt-dlp --flat-playlist  → videos/shorts 탭 모두 동작
- 개별 영상 자막: youtube-watch 스킬 스크립트(클라이언트 web→tv→mweb 폴백 내장) 우선,
  없으면 내장 폴백(클라이언트 순회 + vtt 파싱)

--------------------------------------------------------------------------------
[Claude Code 로컬 적응판]
  * youtube-watch fetch_youtube.py 경로를 __file__ 기준 상대경로로 계산
    (샌드박스 절대경로 /mnt/skills/... 제거). 환경변수 YW_FETCH_SCRIPT 로 덮어쓰기 가능.
  * 샌드박스 전용 --no-check-certificates 제거(로컬은 cert 검증 ON). 프록시 뒤면
    환경변수 HUNTER_INSECURE=1 로 다시 켤 수 있음.
  * 출력 폴더를 OS 임시폴더 기준으로 변경(원본 /home/claude/youtube).
--------------------------------------------------------------------------------

사용:
  python3 hunter_latest.py                  # 최신 영상/쇼츠 목록만 (기본 각 탭 6개)
  python3 hunter_latest.py --fetch --max 4  # 자막까지 추출 → 임시폴더/*.md
"""
import argparse, json, os, re, subprocess, sys, glob, tempfile

CHANNEL = "UC7usMJDHmtbs_oegmzQKKMA"

HERE = os.path.dirname(os.path.abspath(__file__))
# .claude/skills/portfolio-desk/scripts/  →  ../../youtube-watch/scripts/fetch_youtube.py
YW_SCRIPT = os.environ.get(
    "YW_FETCH_SCRIPT",
    os.path.normpath(os.path.join(HERE, "..", "..", "youtube-watch", "scripts", "fetch_youtube.py")),
)
OUTDIR = os.environ.get("HUNTER_OUTDIR", os.path.join(tempfile.gettempdir(), "hunter_yt"))

# TLS 검증 기본 ON. 웹(프록시 가로채기) 환경에선 cert 에러 감지 시 자동 insecure 폴백.
# 로컬(주거용 IP, 직결)에선 그대로 검증 유지 — 포터블. HUNTER_INSECURE=1 로 강제 가능.
_INSECURE = os.environ.get("HUNTER_INSECURE") == "1"


def ytbase():
    b = ["yt-dlp", "--js-runtimes", "node"]
    if _INSECURE:
        b.append("--no-check-certificates")
    return b


def _is_cert_err(s):
    s = (s or "").lower()
    return "certificate" in s or "_ssl.c" in s or "cert_" in s


def run(cmd, timeout=180):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"


def run_yt(extra, timeout=180):
    """yt-dlp 실행. TLS 가로채기 감지 시 자동으로 --no-check-certificates 재시도."""
    global _INSECURE
    code, out, err = run(ytbase() + extra, timeout)
    if code != 0 and not _INSECURE and _is_cert_err(err):
        _INSECURE = True
        print("[INFO] TLS 가로채기 감지 — insecure로 재시도(웹 프록시 환경; 로컬이면 안 뜸)",
              file=sys.stderr)
        code, out, err = run(ytbase() + extra, timeout)
    return code, out, err


def list_tab(tab, n):
    url = f"https://www.youtube.com/channel/{CHANNEL}/{tab}"
    code, out, err = run_yt(["--flat-playlist", "--playlist-items", f"1-{n}",
                             "--print", "%(id)s\t%(title)s\t%(duration)s", url])
    items = []
    for line in out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            items.append({"id": parts[0], "title": parts[1],
                          "duration": parts[2] if len(parts) > 2 else "?",
                          "tab": tab})
    if code != 0 and not items:
        print(f"[WARN] {tab} 탭 탐색 실패: {err.strip()[-200:]}", file=sys.stderr)
    return items


def fetch_transcript(vid):
    """자막 추출. youtube-watch 스킬 우선, 없으면 내장 폴백."""
    url = f"https://www.youtube.com/watch?v={vid}"
    if os.path.exists(YW_SCRIPT):
        code, out, err = run(["python3", YW_SCRIPT, url, "--outdir", OUTDIR], timeout=240)
        for line in out.strip().splitlines()[::-1]:
            if line.strip().endswith(".md") and os.path.exists(line.strip()):
                return line.strip()
        print(f"[WARN] youtube-watch 실패({vid}), 내장 폴백 시도", file=sys.stderr)
    return fallback_fetch(vid, url)


def fallback_fetch(vid, url):
    """내장 폴백: 클라이언트 순회하며 ko 자막 vtt 다운로드 → md 변환."""
    os.makedirs(OUTDIR, exist_ok=True)
    for client in ("ios", "web", "tv", "mweb"):  # ios가 데이터센터 IP 자막 우회에 가장 안정적
        run_yt(["--extractor-args", f"youtube:player_client={client}",
                "--skip-download", "--write-auto-subs", "--write-subs",
                "--sub-langs", "ko,en", "--ignore-no-formats-error",
                "-o", f"{OUTDIR}/{vid}.%(ext)s", url], timeout=180)
        vtts = glob.glob(f"{OUTDIR}/{vid}*.vtt")
        if vtts:
            return vtt_to_md(vid, url, vtts[0])
    return None


def vtt_to_md(vid, url, vtt_path):
    seen, lines = set(), []
    with open(vtt_path, encoding="utf-8") as f:
        for line in f:
            line = re.sub(r"<[^>]+>", "", line).strip()
            if (not line or "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:"))
                    or line.isdigit() or line in seen):
                continue
            seen.add(line)
            lines.append(line)
    md = f"{OUTDIR}/{vid}.md"
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# (폴백 추출) {vid}\n- URL: {url}\n\n## 트랜스크립트\n\n" + "\n".join(lines))
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="자막까지 추출")
    ap.add_argument("--max", type=int, default=4, help="자막 추출 최대 개수")
    ap.add_argument("--per-tab", type=int, default=6, help="탭당 목록 개수")
    args = ap.parse_args()

    items = list_tab("videos", args.per_tab) + list_tab("shorts", args.per_tab)
    if not items:
        print("[FAIL] 채널 탐색 전부 실패 — 웹검색 폴백 사용 권장 "
              "(검색어: 경제사냥꾼 + 주제 + 날짜)")
        sys.exit(1)

    print(json.dumps(items, ensure_ascii=False, indent=1))

    if args.fetch:
        print("\n--- 자막 추출 ---")
        for it in items[: args.max] + [x for x in items if x["tab"] == "shorts"][:2]:
            path = fetch_transcript(it["id"])
            print(f"{it['id']} ({it['tab']}): {path or 'FAILED'}")
        print("\n→ 생성된 md 파일들을 view로 읽고, 업로드 날짜(파일 내 '업로드' 필드)로 "
              "당일/전일 영상만 보고서에 반영할 것. 자동자막 수치는 교차검증 필수.")


if __name__ == "__main__":
    main()
