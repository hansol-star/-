#!/usr/bin/env python3
"""yt-dlp 실행 경로 해석 — PATH에 exe가 없어도 모듈로 부른다.

★[8/31 로컬 이전 실측] `pip install -U yt-dlp`로 **설치가 끝났는데도** 레포 전체의
yt-dlp 경로가 죽어 있었다. 원인은 설치 실패가 아니라 **발견 실패**다 —
윈도우 pip은 `.../Python312/Scripts/yt-dlp.exe`에 깔고 그 디렉터리는 PATH에 없어서,
call site 5곳이 전부 쓰던 `shutil.which("yt-dlp")`가 None을 돌려줬다.
그 5곳은 모두 `if not which(): return None`이라 **조용히** 폴백으로 넘어간다.

= 8/22 *"만든 도구가 '불리는지'는 기계가 본다"* · 8/12 *"쓰는 쪽과 읽는 쪽이 갈리면
데이터는 조용히 사라진다"* 의 세 번째 형태. 실행파일 이름 하나에 기대면 OS가 바뀔 때 끊긴다.

⇒ 해석 순서: ①PATH의 `yt-dlp` ②현재 인터프리터의 `-m yt_dlp`(pip 설치분은 항상 여기 있다).
   호출부는 `cmd = ytdlp_cmd()`로 받아 인자를 붙인다. 없으면 None.
"""
import functools
import importlib.util
import shutil
import sys


@functools.lru_cache(maxsize=1)
def ytdlp_cmd():
    """yt-dlp 실행 커맨드 접두 리스트. 설치돼 있지 않으면 None."""
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    if importlib.util.find_spec("yt_dlp") is not None:
        return [sys.executable, "-m", "yt_dlp"]
    return None


def have_ytdlp():
    return ytdlp_cmd() is not None


def ytdlp_label():
    """진단 출력용 — 어떤 경로로 잡혔는지 사람이 읽게."""
    cmd = ytdlp_cmd()
    if not cmd:
        return "미설치"
    return cmd[0] if len(cmd) == 1 else f"{sys.executable} -m yt_dlp"


if __name__ == "__main__":
    print(ytdlp_label())
