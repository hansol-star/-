#!/usr/bin/env python3
"""web_shot.py — 웹 화면 판독기 (에이전트가 페이지를 '보는' 경로)

착안: 정훈이 가져온 외부 자료(claude-video 와치, 2026-08-22 검토)의 문제의식
      *"에이전트가 화면을 못 본다"*. 와치 자체는 이 환경에서 못 쓴다(유튜브 영상
      스트림·재생이 봇차단·reCAPTCHA로 전부 막힘 — 8/22 실측) → **문제의식만 가져와
      우리 업무에 맞는 형태로 구현**한 것이 이 도구다.

성격: **측정·판독 보조 전용.** vol_gauge·chart_read와 같은 층위 — 별점·스코어·매수존·
      트랜치 어떤 룰도 바꾸지 않는다. 텍스트·API로 얻을 수 있는 수치는 여전히
      market_data·financials·naver_data가 정본이고, 이건 그것들이 **닿지 못하는 화면**
      (렌더링된 표·차트·이미지형 공시)을 눈으로 확인하는 마지막 수단이다.

되는 것 / 안 되는 것 [8/22 실측]:
  ✅ 일반 웹페이지 렌더링 캡처 — 네이버금융 종목화면에서 시세·PER·외국인소진율·
     목표주가·52주 고저까지 전부 판독 확인.
  ✅ 유튜브 **썸네일**(i.ytimg.com CDN, HTTP 200).
  ❌ 유튜브 **영상 프레임** — watch 페이지는 reCAPTCHA, yt-dlp 스트림은 5개 클라이언트
     전부 봇차단. 로컬(주거 IP) 이전 후 재검토 대상이며 그 전까지 이 갭은 열려 있다.

⚠️ 토큰 규율: 캡처 1장은 대략 1,000~1,600 토큰이다. 보유 전종목을 매 보고서마다 찍는
   식으로 쓰지 말 것 — **텍스트 경로가 실패했거나, 표·차트를 눈으로 봐야 판단이 갈릴
   때만** 부른다. 영역을 아는 경우 --selector로 잘라 찍는 편이 싸고 정확하다.

사용:
  python3 web_shot.py https://finance.naver.com/item/main.naver?code=005930
  python3 web_shot.py <URL> --selector "#chart_area" --out /tmp/x.png
  python3 web_shot.py --naver 005930          # 네이버금융 종목 화면 프리셋
  python3 web_shot.py --yt-thumb D8L_tHNLj_A  # 유튜브 썸네일(영상 프레임 아님)
출력: 마지막 줄에 저장 경로 → 그 경로를 Read 도구로 열어 화면을 판독한다.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CJS = os.path.join(HERE, "web_shot.cjs")
NODE_MODULES = os.environ.get("NODE_PATH", "/opt/node22/lib/node_modules")
CA_BUNDLE = "/root/.ccr/ca-bundle.crt"
OUTDIR = os.environ.get("SHOT_OUTDIR", os.path.join(tempfile.gettempdir(), "web_shots"))


def _default_out(tag: str) -> str:
    os.makedirs(OUTDIR, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in tag)[:60]
    return os.path.join(OUTDIR, f"{safe or 'shot'}.png")


def yt_thumbnail(video_id: str, out: str | None = None) -> str | None:
    """유튜브 썸네일(CDN). ⚠️ 영상 프레임이 아니라 표지 1장이다."""
    out = out or _default_out(f"yt_{video_id}")
    for name in ("maxresdefault.jpg", "hqdefault.jpg"):
        url = f"https://i.ytimg.com/vi/{video_id}/{name}"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = r.read()
            if len(data) > 2000:
                path = out if out.endswith(".jpg") else out.rsplit(".", 1)[0] + ".jpg"
                with open(path, "wb") as f:
                    f.write(data)
                return path
        except Exception:
            continue
    return None


def capture(url: str, out: str, *, selector: str | None = None, full: bool = False,
            width: int = 1280, height: int = 900, wait: float = 3.0,
            scale: int = 1, timeout: int = 60) -> dict:
    if not os.path.exists(CJS):
        return {"ok": False, "error": f"헬퍼 없음: {CJS}"}
    opts = {"url": url, "out": out, "selector": selector, "full": full,
            "width": width, "height": height, "wait": wait, "scale": scale,
            "timeout": timeout}
    env = dict(os.environ, NODE_PATH=NODE_MODULES, NODE_USE_ENV_PROXY="1")
    if os.path.exists(CA_BUNDLE):
        env.setdefault("NODE_EXTRA_CA_CERTS", CA_BUNDLE)
    try:
        r = subprocess.run(["node", CJS, json.dumps(opts)], capture_output=True,
                           text=True, timeout=timeout + 60, env=env)
    except Exception as ex:
        return {"ok": False, "error": f"node 실행 실패: {ex}"}
    for line in reversed((r.stdout or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return {"ok": False, "error": (r.stderr or "무응답")[-300:]}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="웹 화면 캡처 → PNG (판독 보조 전용, 룰 변경 없음)")
    ap.add_argument("url", nargs="?", help="캡처할 URL")
    ap.add_argument("--naver", metavar="CODE", help="네이버금융 종목 화면 프리셋 (예: 005930)")
    ap.add_argument("--yt-thumb", metavar="VIDEO_ID",
                    help="유튜브 썸네일 저장 (⚠️ 영상 프레임 아님 — 웹 환경에선 프레임 불가)")
    ap.add_argument("--out", help="저장 경로 (기본: 임시폴더)")
    ap.add_argument("--selector", help="이 CSS 요소만 잘라서 캡처 (토큰 절약·정확)")
    ap.add_argument("--full", action="store_true", help="전체 페이지 (기본: 보이는 영역)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--scale", type=int, default=1, help="배율 2 = 작은 글자 판독용")
    ap.add_argument("--wait", type=float, default=3.0, help="로드 후 대기 초")
    ap.add_argument("--timeout", type=int, default=60)
    a = ap.parse_args()

    if a.yt_thumb:
        path = yt_thumbnail(a.yt_thumb, a.out)
        if not path:
            print("[FAIL] 썸네일 확보 실패", file=sys.stderr)
            return 1
        print("⚠️ 영상 프레임이 아니라 썸네일 1장이다 (웹 환경에서 프레임은 불가).",
              file=sys.stderr)
        print(path)
        return 0

    url, tag = a.url, a.url or ""
    if a.naver:
        url = f"https://finance.naver.com/item/main.naver?code={a.naver}"
        tag = f"naver_{a.naver}"
    if not url:
        ap.error("URL 또는 --naver / --yt-thumb 중 하나가 필요하다")

    out = a.out or _default_out(tag.replace("https://", "").replace("http://", ""))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    res = capture(url, out, selector=a.selector, full=a.full, width=a.width,
                  height=a.height, wait=a.wait, scale=a.scale, timeout=a.timeout)
    if not res.get("ok"):
        print(f"[FAIL] {res.get('error')}", file=sys.stderr)
        return 1
    if res.get("title"):
        print(f"[OK] {res['title']}", file=sys.stderr)
    print(res["path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
