---
name: youtube-watch
description: Fetch and analyze YouTube videos directly — metadata, full timestamped transcripts (Korean/English/auto-generated captions), chapters, top comments, and even visual frames. Use this skill whenever the user shares ANY YouTube link (youtube.com/watch, youtu.be, /shorts/, /live/) and wants Claude to watch, summarize, analyze, fact-check, translate, or reference the video's content — including stock/investment commentary videos, lectures, news clips, and shorts. Also use when the user says things like "이 영상 봐줘", "영상 정리해줘", "summarize this video", or pastes a YouTube URL with a question about its content. Do NOT answer from the URL title alone; always fetch the actual transcript first.
---

# YouTube Watch

Lets Claude actually read a YouTube video's content (transcript + metadata) instead of guessing from the title.

## Quick start

For any YouTube URL the user shares (run from the project root):

```bash
pip install yt-dlp --break-system-packages -q   # once per machine (or: pip install -U yt-dlp)
python3 .claude/skills/youtube-watch/scripts/fetch_youtube.py "<URL>"
```

This prints the path of a Markdown file (default in the OS temp dir, e.g. `/tmp/yt_cache/<video_id>.md`) containing:
- Title, channel, upload date, duration, view count
- Video description and chapters (if present)
- A clean, deduplicated transcript with `[m:ss]` timestamps in ~20-second blocks

Then **read that file with the Read tool** and answer the user's question based on its content. Cite timestamps like `[3:45]` when referencing specific moments.

## Options

```bash
python3 .claude/skills/youtube-watch/scripts/fetch_youtube.py "<URL>" \
    --langs ko,en        # subtitle language priority (default ko,en)
    --comments 30        # also fetch top N comments → <id>_comments.md
    --frames 6           # extract N evenly-spaced frames as JPGs → frames_<id>/
    --interval 20        # transcript block size in seconds
    --outdir DIR         # output directory (default: OS temp /yt_cache)
    --insecure           # ONLY if behind a self-signed-cert proxy (see below)
```

- `--frames`: downloads the lowest-quality video and extracts still images. Use when visuals matter (charts shown on screen, shorts with little speech, "이 영상에 나온 차트 봐줘"). View the JPGs afterwards. Slower (~30s–2min); skip for talk-only videos.
- `--comments`: useful for gauging audience reaction/sentiment.

## Environment notes (local machine — different from the old sandbox)

The script already handles YouTube's quirks; don't reinvent them:
- It falls back through player clients (`web → tv → mweb`) automatically. The `tv` client almost always gets through, including subtitle downloads, when the default `web` client hits "Sign in to confirm you're not a bot."
- **On a normal home/office (residential) IP this bot-check is rare** — the old claude.ai sandbox hit it constantly because it ran from a datacenter IP. So locally the first client usually succeeds outright. The fallback chain is just insurance.
- **TLS cert checking is ON by default** (correct for a local machine talking directly to YouTube). The old sandbox needed `--no-check-certificates` because of its egress proxy's self-signed cert — you do **not** need that locally. If you're behind a corporate proxy that breaks TLS, add `--insecure`.
- `youtube-transcript-api` is unreliable from automated environments — this script uses `yt-dlp`, don't swap it.
- Requires `ffmpeg`/`ffprobe` on PATH only for `--frames` (not for transcripts). Node.js is required by Claude Code anyway and helps yt-dlp's signature handling.
- Transient `429 Too Many Requests` warnings are normal. If a whole run fails, wait ~10s and retry once.

## Subtitle selection logic

Prefers, in order: uploader-provided subs in requested languages → auto-generated captions in requested languages → original-language auto captions. Auto-generated Korean captions ("자동 생성") are usually fine for summarization but may garble proper nouns and numbers — flag this when quoting exact figures (stock prices, percentages) from an auto transcript.

## Workflow guidance

1. Fetch the transcript file, then read it fully before answering.
2. For summaries: lead with the core thesis/conclusion, then key points with timestamps.
3. For investment/finance videos: clearly separate the **creator's claims/opinions** from **verifiable facts**, and offer to fact-check key numbers with web search.
4. For shorts (< 60s): the transcript may be just a few lines; `--frames 4` often adds useful context.
5. Multiple URLs: run the script once per URL (sequentially), then synthesize.
6. If no captions exist at all, say so honestly — offer `--frames` for visual inspection or a metadata-only summary instead of guessing.
