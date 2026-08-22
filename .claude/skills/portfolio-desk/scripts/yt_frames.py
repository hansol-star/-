#!/usr/bin/env python3
"""yt_frames.py — 유튜브 영상의 **화면**을 확보한다 (자막과 짝을 이루는 축)

배경: 정훈 지시(8/22) *"화면이랑 자막 둘 다 하면 정보를 더 깊게 알 거 아니야."*
      맞는 말인데 정공법(영상 다운로드 → ffmpeg 프레임 추출)은 이 환경에서 전부 막혔다.
      막힌 것과 뚫린 것을 실측으로 갈라 **뚫린 경로만** 도구화한 것이 이 파일이다.

[8/22 실측 — 무엇이 막혔나]
  ❌ yt-dlp 스트림           : web·android·ios·tv·mweb 5개 클라이언트 전부 봇차단
  ❌ Playwright watch 재생   : reCAPTCHA("unusual traffic") — video 엘리먼트조차 안 뜸
  ❌ googlevideo 직접 다운로드: innertube IOS로 **서명 없는 1080p URL은 얻어지지만**
                               미디어 서버가 403 — URL이 발급 IP에 바인딩돼 있고
                               (`ip=` IPv6) 우리 프록시 출구(`mip=` IPv4)와 다르다.
                               `ipbypass=yes`가 붙은 리다이렉트 URL도, urllib/curl,
                               iOS UA, Range 헤더/파라미터 조합 전부 403.
[8/22 실측 — 무엇이 뚫렸나]
  ✅ **스토리보드**(i.ytimg.com/sb/…) — 플레이어 스크럽 미리보기용 **실제 영상 프레임**을
     격자 시트로 제공. CDN이라 캡차·IP 바인딩 없음. L2 = 160×90 타일 5×5 = 시트당 25프레임.
     실측 판독: 종목 화면의 **가격·등락률·거래정지 표시·자막 문구**까지 읽힌다.
  ✅ 썸네일 — maxresdefault(1280×720 고해상도 표지) + 1/2/3.jpg(25/50/75% 지점).

⚠️ 한계를 정직하게: 160×90에서 **차트 축 눈금·표 세부 숫자는 못 읽는다.** 큰 자막과
   화면 구성, 어떤 종목 화면이 언제 나왔는지까지가 판독 범위다. 고해상도 프레임은
   12월 로컬(주거 IP) 이전 후 yt-dlp 경로가 살아나야 가능하다 —
   `api_health.py`의 "yt-dlp 스트림"이 ✅로 바뀌는 날이 그 신호다.

⚠️ **자막을 대체하지 않는다.** 화면은 자막의 *보조 축*이다(채널의 자막 수치 오류를
   화면으로 교차검증하는 용도). 영상 내용의 정본은 여전히 `hunter_latest.py --fetch`.
⚠️ **토큰 규율**: 시트 1장 ≈1,100~1,600토큰. 119프레임 = L2 기준 5시트 ≈7,000토큰이다.
   R1이 하루 7~8편을 도는 걸 감안하면 **전편 상시 캡처는 예산을 태운다** →
   ①자막에서 수치·차트 언급이 나왔는데 검증이 필요할 때 ②정훈이 특정 영상을 콕 집을 때만.
   `--sheets 1`(앞 25프레임)이 기본값인 이유다.

사용:
  python3 yt_frames.py <영상ID|URL>                  # L2 시트 1장 (앞 25프레임)
  python3 yt_frames.py <ID> --sheets all             # 전체 프레임
  python3 yt_frames.py <ID> --level 1                # 더 촘촘한 격자(80x45, 100프레임/시트)
  python3 yt_frames.py <ID> --thumbs                 # 고해상도 표지 + 25/50/75% 지점
  python3 yt_frames.py <ID> --at 5:30                # 그 시점이 든 시트 + 타일 위치 안내
출력: 저장 경로들 → **Read 도구로 열어 화면을 판독**한다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUTDIR = os.environ.get("YTFRAME_OUTDIR", os.path.join(tempfile.gettempdir(), "yt_frames"))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
_VID_RE = re.compile(r"(?:v=|/shorts/|/live/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})")


def video_id(s: str) -> str | None:
    m = _VID_RE.search(s or "")
    if m:
        return m.group(1)
    s = (s or "").strip()
    return s if re.fullmatch(r"[A-Za-z0-9_-]{11}", s) else None


def _get(url: str, timeout: int = 40) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_time(s: str) -> float:
    """'5:30' / '1:02:03' / '330' → 초."""
    parts = str(s).split(":")
    try:
        vals = [float(p) for p in parts]
    except ValueError:
        raise ValueError(f"시각 형식 오류: {s}")
    sec = 0.0
    for v in vals:
        sec = sec * 60 + v
    return sec


def player_response(vid: str) -> dict:
    """hunter_latest의 innertube 경로를 재사용한다(자막과 같은 사슬 — 배선 일원화)."""
    import hunter_latest as H
    last = None
    for c in H.INNERTUBE_CLIENTS:
        try:
            d = H.innertube_player(vid, c)
        except Exception as ex:
            last = str(ex)
            continue
        if ((d.get("storyboards") or {}).get("playerStoryboardSpecRenderer") or {}).get("spec"):
            return d
        last = d.get("playabilityStatus", {}).get("status")
    raise RuntimeError(f"스토리보드 spec 미확보 (마지막 상태: {last})")


def parse_spec(spec: str) -> tuple[str, list[dict]]:
    """spec = base|L0params|L1params|… , params = W#H#총개수#열#행#간격ms#이름#sigh"""
    parts = spec.split("|")
    levels = []
    for p in parts[1:]:
        f = p.split("#")
        if len(f) < 8:
            continue
        levels.append({"w": int(f[0]), "h": int(f[1]), "count": int(f[2]),
                       "cols": int(f[3]), "rows": int(f[4]), "interval_ms": int(f[5]),
                       "name": f[6], "sigh": f[7]})
    return parts[0], levels


def sheet_url(base: str, lvl_idx: int, lvl: dict, sheet_no: int) -> str:
    u = base.replace("$L", str(lvl_idx)).replace("$N", lvl["name"]).replace("$M", str(sheet_no))
    return f"{u}&sigh={lvl['sigh']}"


def fetch_thumbs(vid: str, outdir: str) -> list[str]:
    """고해상도 표지 + 25/50/75% 지점 프레임. CDN이라 항상 열린다."""
    got = []
    for name, label in (("maxresdefault", "표지(고해상도)"), ("1", "25%지점"),
                        ("2", "50%지점"), ("3", "75%지점")):
        try:
            data = _get(f"https://i.ytimg.com/vi/{vid}/{name}.jpg")
        except Exception:
            continue
        if len(data) < 2000:
            continue
        path = os.path.join(outdir, f"{vid}_{name}.jpg")
        with open(path, "wb") as f:
            f.write(data)
        got.append(f"{path}  [{label}]")
    return got


def main() -> int:
    ap = argparse.ArgumentParser(
        description="유튜브 화면 확보 (스토리보드·썸네일 — 판독 보조 전용, 룰 변경 없음)")
    ap.add_argument("video", help="영상 ID 또는 URL")
    ap.add_argument("--level", type=int, default=2,
                    help="스토리보드 레벨: 2=160x90 25프레임/시트(기본) · 1=80x45 100/시트")
    ap.add_argument("--sheets", default="1",
                    help="받을 시트 수 (기본 1 = 앞부분만) 또는 'all'")
    ap.add_argument("--at", help="이 시점(예 5:30)이 든 시트만 받고 타일 위치를 알려준다")
    ap.add_argument("--thumbs", action="store_true", help="썸네일(표지+25/50/75%%)만 받는다")
    ap.add_argument("--outdir", default=OUTDIR)
    a = ap.parse_args()

    vid = video_id(a.video)
    if not vid:
        print("[FAIL] 영상 ID를 못 읽었다", file=sys.stderr)
        return 1
    os.makedirs(a.outdir, exist_ok=True)

    if a.thumbs:
        got = fetch_thumbs(vid, a.outdir)
        if not got:
            print("[FAIL] 썸네일 확보 실패", file=sys.stderr)
            return 1
        print("\n".join(got))
        return 0

    try:
        d = player_response(vid)
    except Exception as ex:
        print(f"[FAIL] {ex}", file=sys.stderr)
        print("  → innertube 레이트리밋(429)일 수 있다. 몇 분 뒤 재시도하거나 "
              "--thumbs로 표지만 받을 것.", file=sys.stderr)
        return 1

    spec = d["storyboards"]["playerStoryboardSpecRenderer"]["spec"]
    base, levels = parse_spec(spec)
    if not levels:
        print("[FAIL] 스토리보드 레벨 파싱 실패", file=sys.stderr)
        return 1
    lvl_idx = min(a.level, len(levels) - 1)
    lvl = levels[lvl_idx]
    per_sheet = lvl["cols"] * lvl["rows"]
    total_sheets = -(-lvl["count"] // per_sheet)
    step = lvl["interval_ms"] / 1000.0

    wanted = list(range(total_sheets))
    if a.at:
        idx = int(parse_time(a.at) // step) if step else 0
        sheet = idx // per_sheet
        if sheet >= total_sheets:
            print(f"[FAIL] {a.at}는 영상 길이를 넘는다(프레임 {lvl['count']}개)", file=sys.stderr)
            return 1
        pos = idx % per_sheet
        wanted = [sheet]
        print(f"[안내] {a.at} → 프레임 #{idx} = 시트{sheet}의 "
              f"{pos // lvl['cols'] + 1}행 {pos % lvl['cols'] + 1}열 "
              f"(격자 {lvl['cols']}열×{lvl['rows']}행, 프레임 간격 {step:.1f}초)", file=sys.stderr)
    elif a.sheets != "all":
        try:
            wanted = list(range(min(int(a.sheets), total_sheets)))
        except ValueError:
            print("[FAIL] --sheets 는 숫자 또는 'all'", file=sys.stderr)
            return 1

    # ★[8/22 실측] 쇼츠(세로 영상)는 같은 L2라도 타일이 **50×90**으로 쪼그라들어 판독이 안 된다.
    #   경제사냥꾼 최근 업로드는 상당수가 쇼츠라 이 구분이 중요하다 — 받기 전에 알려준다.
    #   (롱폼 160×90에서는 종목 화면 가격·뉴스 원문 문장까지 읽혔다.)
    is_short = lvl["w"] < 100
    print(f"[정보] L{lvl_idx}: 타일 {lvl['w']}×{lvl['h']} · 프레임 {lvl['count']}개 · "
          f"시트 {total_sheets}장(장당 {per_sheet}프레임) · 간격 {step:.1f}초 "
          f"→ {len(wanted)}장 받는다", file=sys.stderr)
    if is_short:
        print(f"⚠️ **쇼츠(세로) 판정 — 타일 {lvl['w']}×{lvl['h']}로 판독 거의 불가.** "
              "차트선·화면 전환만 보이고 숫자·문구는 안 읽힌다. 자막으로 갈음할 것. "
              "(8/22 실측: 쇼츠 2편 판독 실패 / 롱폼 160×90은 종목가격·뉴스원문까지 판독)",
              file=sys.stderr)

    saved = []
    for n in wanted:
        try:
            data = _get(sheet_url(base, lvl_idx, lvl, n))
        except Exception as ex:
            print(f"  시트{n} 실패: {str(ex)[:80]}", file=sys.stderr)
            continue
        path = os.path.join(a.outdir, f"{vid}_L{lvl_idx}_s{n}.jpg")
        with open(path, "wb") as f:
            f.write(data)
        t0 = n * per_sheet * step
        t1 = min((n + 1) * per_sheet - 1, lvl["count"] - 1) * step
        saved.append(f"{path}  [{int(t0)//60}:{int(t0)%60:02d}~{int(t1)//60}:{int(t1)%60:02d}]")
    if not saved:
        print("[FAIL] 시트를 하나도 못 받았다", file=sys.stderr)
        return 1
    print("\n".join(saved))
    print("→ 위 경로를 Read로 열어 판독. ⚠️160×90이라 차트 축·표 세부 숫자는 안 읽힌다 — "
          "수치는 자막·API 정본과 교차할 것.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
