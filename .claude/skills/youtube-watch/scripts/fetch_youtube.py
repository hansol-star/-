#!/usr/bin/env python3
"""
fetch_youtube.py - Fetch YouTube video metadata + transcript and save as clean Markdown.

Usage:
    python3 fetch_youtube.py <URL> [--langs ko,en] [--outdir DIR] [--comments N] [--frames N]

Output:
    <outdir>/<video_id>.md          - metadata + timestamped transcript
    <outdir>/<video_id>_comments.md - top comments (if --comments)
    <outdir>/frames_<video_id>/     - extracted frames (if --frames)

--------------------------------------------------------------------------------
[Claude Code 로컬 적응판 — 원본은 claude.ai 샌드박스용]
샌드박스(이그레스 프록시+자가서명 인증서, 데이터센터 IP 봇차단) 전용이던 부분을
로컬 머신 기준으로 바꿨다:
  * 기본 cert 검증 ON.  프록시 뒤(회사망 등)라 CERTIFICATE_VERIFY_FAILED가 나면
    --insecure 플래그로 --no-check-certificates 를 켤 수 있음.
  * 봇 차단(web→tv→mweb) 클라이언트 폴백은 그대로 유지 — 로컬에서도 가끔 유용.
    단 집/회사의 일반(주거용) IP는 데이터센터 IP보다 차단을 훨씬 덜 받으므로
    대개 첫 클라이언트(web)로 바로 성공한다.
  * --js-runtimes node 유지 (Claude Code는 Node.js 필수라 항상 존재, YouTube 서명 처리에 도움).
  * 기본 출력 폴더를 OS 임시 폴더 기준으로 변경(원본은 /home/claude/youtube).
--------------------------------------------------------------------------------
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

# cert 검증 ON 이 기본. 프록시 뒤라면 --insecure 사용.
YTDLP_BASE = ["yt-dlp", "--js-runtimes", "node", "--ignore-no-formats-error"]
INSECURE_FLAG = "--no-check-certificates"

DEFAULT_OUTDIR = os.environ.get("YT_OUTDIR", os.path.join(tempfile.gettempdir(), "yt_cache"))

# YouTube intermittently throws "Sign in to confirm you're not a bot" at the
# default web client. ios 클라이언트가 메타 우회에 안정적이나, 데이터센터 IP에서
# 자막 트랙은 ios/tv/mweb이 막거나(봇차단·DRM) 미노출하는 경우가 있음 →
# web_embedded가 자막 트랙을 내주는 유일한 클라이언트였음 (2026-06-17 경제사냥꾼 6건 재추출 검증).
# 그래서 web_embedded를 ios 다음 우선순위로 둠. 이후 web→tv→mweb 폴백.
CLIENT_CHAIN = ["ios", "web_embedded", None, "tv", "mweb"]
# 기본 검증 ON. --insecure 또는 YT_INSECURE=1, 혹은 cert 에러 자동 감지 시 insecure.
_INSECURE = os.environ.get("YT_INSECURE") == "1"


def _is_cert_err(s):
    s = (s or "").lower()
    return "certificate" in s or "_ssl.c" in s or "cert_" in s


def base_cmd(client):
    cmd = list(YTDLP_BASE)
    if _INSECURE:
        cmd.append(INSECURE_FLAG)
    if client:
        cmd += ["--extractor-args", f"youtube:player_client={client}"]
    return cmd


def run(cmd, timeout=180):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def get_metadata(url):
    """Fetch metadata as JSON (no download), falling back across player clients.
    TLS 가로채기(웹 프록시) 감지 시 자동으로 insecure 재시도."""
    global _INSECURE
    last_err = ""
    for client in CLIENT_CHAIN:
        cmd = base_cmd(client) + ["--skip-download", "-J", "--no-warnings", url]
        p = run(cmd, timeout=120)
        if p.returncode == 0 and p.stdout.strip():
            meta = json.loads(p.stdout)
            meta["_client"] = client
            return meta
        last_err = p.stderr[-500:]
        if not _INSECURE and _is_cert_err(last_err):
            _INSECURE = True
            print("  TLS 가로채기 감지 — insecure로 재시도(웹 프록시 환경)", file=sys.stderr)
            p = run(base_cmd(client) + ["--skip-download", "-J", "--no-warnings", url], timeout=120)
            if p.returncode == 0 and p.stdout.strip():
                meta = json.loads(p.stdout)
                meta["_client"] = client
                return meta
            last_err = p.stderr[-500:]
        print(f"  client={client or 'web'} failed, trying next...", file=sys.stderr)
    raise RuntimeError(f"Metadata fetch failed on all clients: {last_err}")


def hms(seconds):
    if seconds is None:
        return "?"
    seconds = int(seconds)
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def pick_sub_langs(meta, wanted):
    """Pick best available subtitle language codes: manual subs first, then auto."""
    manual = set((meta.get("subtitles") or {}).keys())
    auto = set((meta.get("automatic_captions") or {}).keys())

    def match(pool, lang):
        if lang in pool:
            return lang
        for code in sorted(pool):
            if code == f"{lang}-orig" or code.startswith(f"{lang}-"):
                return code
        return None

    for lang in wanted:
        m = match(manual, lang)
        if m:
            return m, "manual"
    for lang in wanted:
        m = match(auto, lang)
        if m:
            return m, "auto"
    for code in sorted(auto):
        if code.endswith("-orig"):
            return code, "auto"
    if manual:
        return sorted(manual)[0], "manual"
    if auto:
        return sorted(auto)[0], "auto"
    return None, None


def download_vtt(url, lang_code, is_auto, workdir, client=None):
    flag = "--write-auto-subs" if is_auto else "--write-subs"
    clients = [client] + [c for c in CLIENT_CHAIN if c != client]
    for cl in clients:
        cmd = base_cmd(cl) + [
            "--skip-download", flag, "--sub-langs", lang_code,
            "--sub-format", "vtt", "--no-warnings",
            "-o", os.path.join(workdir, "sub.%(ext)s"), url,
        ]
        run(cmd, timeout=180)
        files = glob.glob(os.path.join(workdir, "sub*.vtt"))
        if files:
            return files[0]
    return None


TAG_RE = re.compile(r"<[^>]+>")
TS_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.\d{3}\s+-->")


def vtt_to_transcript(vtt_path, interval=20):
    """Parse VTT into deduplicated text grouped into ~interval-second blocks
    with [m:ss] timestamps. Handles rolling auto-caption duplication."""
    with open(vtt_path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    cues = []
    cur_start = None
    seen_last = ""
    for line in lines:
        m = TS_RE.match(line.strip())
        if m:
            cur_start = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            continue
        if cur_start is None:
            continue
        text = TAG_RE.sub("", line).strip()
        if not text or text == seen_last:
            continue
        if text.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        cues.append((cur_start, text))
        seen_last = text

    deduped = []
    for start, text in cues:
        if deduped and deduped[-1][1] == text:
            continue
        deduped.append((start, text))

    blocks = []
    block_start, parts = None, []
    for start, text in deduped:
        if block_start is None:
            block_start = start
        if start - block_start >= interval and parts:
            blocks.append((block_start, " ".join(parts)))
            block_start, parts = start, []
        parts.append(text)
    if parts:
        blocks.append((block_start, " ".join(parts)))

    return "\n".join(f"[{hms(s)}] {t}" for s, t in blocks)


def get_comments(url, n, client=None):
    cmd = base_cmd(client) + [
        "--skip-download", "--write-comments", "--no-warnings",
        "--extractor-args", f"youtube:max_comments={n},all,0,0;comment_sort=top",
        "-J", url,
    ]
    p = run(cmd, timeout=240)
    if p.returncode != 0:
        return []
    try:
        data = json.loads(p.stdout)
        return (data.get("comments") or [])[:n]
    except Exception:
        return []


def extract_frames(url, n, outdir, video_id, client=None):
    """Download lowest-res video and extract n evenly spaced frames as JPG."""
    frames_dir = os.path.join(outdir, f"frames_{video_id}")
    os.makedirs(frames_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        vpath = os.path.join(tmp, "video.%(ext)s")
        files = []
        for cl in [client] + [c for c in CLIENT_CHAIN if c != client]:
            cmd = base_cmd(cl) + ["-f", "worstvideo[height>=144]/worst",
                                  "--no-warnings", "-o", vpath, url]
            p = run(cmd, timeout=600)
            files = glob.glob(os.path.join(tmp, "video.*"))
            if files:
                break
        if not files:
            print(f"  Frame extraction failed: {p.stderr[-300:]}", file=sys.stderr)
            return None
        video = files[0]
        pr = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                  "-of", "csv=p=0", video])
        try:
            dur = float(pr.stdout.strip())
        except ValueError:
            dur = 60.0
        for i in range(n):
            t = dur * (i + 0.5) / n
            out = os.path.join(frames_dir, f"frame_{i+1:02d}_{int(t)}s.jpg")
            run(["ffmpeg", "-y", "-ss", str(t), "-i", video, "-frames:v", "1",
                 "-q:v", "4", out], timeout=60)
    return frames_dir


def main():
    global _INSECURE
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--langs", default="ko,en", help="preferred subtitle languages, comma-separated")
    ap.add_argument("--outdir", default=DEFAULT_OUTDIR)
    ap.add_argument("--comments", type=int, default=0, help="fetch top N comments")
    ap.add_argument("--frames", type=int, default=0, help="extract N video frames as images")
    ap.add_argument("--interval", type=int, default=20, help="transcript block size in seconds")
    ap.add_argument("--insecure", action="store_true",
                    help="자가서명 인증서 프록시 뒤일 때만: yt-dlp cert 검증 끔")
    args = ap.parse_args()
    _INSECURE = args.insecure

    os.makedirs(args.outdir, exist_ok=True)
    wanted = [l.strip() for l in args.langs.split(",") if l.strip()]

    print("Fetching metadata...", file=sys.stderr)
    meta = get_metadata(args.url)
    vid = meta.get("id", "video")

    lang_code, kind = pick_sub_langs(meta, wanted)
    transcript, sub_note = "", "자막 없음"
    if lang_code:
        print(f"Downloading subtitles: {lang_code} ({kind})...", file=sys.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            vtt = download_vtt(args.url, lang_code, kind == "auto", tmp, meta.get("_client"))
            if vtt:
                transcript = vtt_to_transcript(vtt, args.interval)
                sub_note = f"{lang_code} ({'자동 생성' if kind == 'auto' else '업로더 제공'})"

    chapters = meta.get("chapters") or []
    upload_date = meta.get("upload_date", "")
    if len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

    md = [
        f"# {meta.get('title', '')}",
        "",
        f"- **채널**: {meta.get('channel') or meta.get('uploader', '?')}",
        f"- **업로드**: {upload_date or '?'}",
        f"- **길이**: {hms(meta.get('duration'))}",
        f"- **조회수**: {meta.get('view_count', '?'):,}" if isinstance(meta.get("view_count"), int) else f"- **조회수**: ?",
        f"- **URL**: https://www.youtube.com/watch?v={vid}",
        f"- **자막**: {sub_note}",
        "",
    ]
    desc = (meta.get("description") or "").strip()
    if desc:
        md += ["## 설명", "", desc[:2000], ""]
    if chapters:
        md += ["## 챕터", ""]
        md += [f"- [{hms(c.get('start_time'))}] {c.get('title')}" for c in chapters]
        md += [""]
    md += ["## 트랜스크립트", "", transcript or "(자막을 가져올 수 없었습니다)"]

    out_path = os.path.join(args.outdir, f"{vid}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(out_path)

    if args.comments:
        print(f"Fetching top {args.comments} comments...", file=sys.stderr)
        comments = get_comments(args.url, args.comments, meta.get("_client"))
        if comments:
            cpath = os.path.join(args.outdir, f"{vid}_comments.md")
            clines = [f"# 댓글 ({meta.get('title','')})", ""]
            for c in comments:
                clines.append(f"- **{c.get('author','?')}** (\U0001f44d{c.get('like_count',0)}): {c.get('text','').strip()}")
            with open(cpath, "w", encoding="utf-8") as f:
                f.write("\n".join(clines))
            print(cpath)

    if args.frames:
        print(f"Extracting {args.frames} frames...", file=sys.stderr)
        fdir = extract_frames(args.url, args.frames, args.outdir, vid, meta.get("_client"))
        if fdir:
            print(fdir)


if __name__ == "__main__":
    main()
