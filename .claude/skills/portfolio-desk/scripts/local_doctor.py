#!/usr/bin/env python3
"""
local_doctor.py — 로컬 이전 프리플라이트 점검 [2026-08-31 신설]

왜 필요한가
────────────────────────────────────────────────────────────────
docs/local_migration.md §2d의 검증 순서(api_health → short_borrow → selfcheck)는
**전부 네트워크·코드 점검**이다. 그 앞단 = "이 기계가 우리 레포를 돌릴 조건을 갖췄나"를
보는 도구가 없었다. 실제 지뢰:
  · `python3`가 윈도우 네이티브엔 없다 — 지시층(agents·skills·settings) 561곳이 전부
    `python3 ...`로 스크립트를 부른다. 인터프리터는 멀쩡한데 **호출이 통째로 실패**한다.
  · `SSL_CERT_FILE`을 로컬에 걸면 정상 인증서 검증이 깨진다(웹 프록시 CA 전용).
  · 얕은 클론(50커밋)을 물려받으면 score_calls --backfill 표본이 조용히 비어 있다.
셋 다 **실패가 조용하다** — 8/22 "가드 없는 폴백은 침묵보다 나쁘다"의 환경판.

⚠️ 측정 전용 — 네트워크를 쓰지 않고(그건 api_health 담당) 어떤 룰도 바꾸지 않는다.
⚠️ 키는 존재 여부와 앞 4자만 표시한다. 값을 절대 찍지 않는다.

사용법
  python3 local_doctor.py           # 전체 점검
  python3 local_doctor.py --json    # 기계 판독용
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OK, WARN, FAIL, SKIP = "PASS", "WARN", "FAIL", "SKIP"

# 웹(원격) 환경 표식 — 프록시 CA 번들이 있으면 웹이다
WEB_CA = "/root/.ccr/ca-bundle.crt"
ON_WEB = os.path.exists(WEB_CA)

KEYS = ["YOUTUBE_API_KEY", "DART_API_KEY", "FMP_API_KEY",
        "NAVER_NCP_KEY_ID", "NAVER_NCP_KEY"]
# 없어도 폴백이 도는 키 (FAIL 아님)
KEY_OPTIONAL = {"FMP_API_KEY": "5종목 화이트리스트뿐 — EDGAR가 대체(8/1)"}

PIP_OPTIONAL = [
    ("matplotlib", "charts.py — 없으면 차트 자동 스킵"),
    ("openpyxl", "export_financials_xlsx.py"),
    ("pdfminer", "read_doc.py (pdfminer.six)"),
    ("pypdf", "read_doc.py"),
]


def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def _find_bash():
    """PATH에 없어도 Git for Windows 기본 설치 경로를 본다 (8/31 신설).
    훅은 Claude Code가 자체 셸로 부르므로 PATH 부재 = 훅 사망이 아니다."""
    import glob as _g
    cands = []
    for base in ("C:/Program Files/Git", "C:/Program Files (x86)/Git"):
        cands += [base + "/bin/bash.exe", base + "/usr/bin/bash.exe"]
    cands += _g.glob("C:/Users/*/AppData/Local/Programs/Git/bin/bash.exe")
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def mask(v: str) -> str:
    return (v[:4] + "…") if len(v) > 4 else "설정됨"


def checks():
    out = []

    def add(name, status, detail, why=""):
        out.append({"name": name, "status": status, "detail": detail, "why": why})

    # 1. 인터프리터
    v = sys.version_info
    add("Python 버전", OK if (v.major, v.minor) >= (3, 11) else FAIL,
        f"{v.major}.{v.minor}.{v.micro} @ {sys.executable}",
        "3.11+ 필요 (docs/local_migration.md §2a)")

    # 2. * python3 런처 — 지시층 561곳의 전제
    # !! which()로 "있다"만 보면 안 된다 — 윈도우 MS Store 별칭(WindowsApps)은
    #    PATH에 잡히지만 실행하면 exit 9009로 죽는다(8/31 실측).
    #    "메타 성공 != 생존"(8/22) — 실제로 돌려서 버전이 나오는지로 판정한다.
    p3 = shutil.which("python3")
    if not p3:
        add("`python3` 런처", FAIL, "PATH에 없음",
            "인터프리터는 있어도 지시층 561곳의 호출이 전부 실패한다 -> §2a 심(shim) 설치")
    else:
        rc, o = run([p3, "-c", "import sys;print('PY%d.%d' % sys.version_info[:2])"], timeout=25)
        if rc == 0 and "PY" in o:
            add("`python3` 런처", OK, "%s -> %s" % (p3, o.strip().splitlines()[-1]),
                "agents·skills·settings.json이 전부 `python3 ...`로 부른다")
        else:
            stub = "WindowsApps" in (p3 or "")
            add("`python3` 런처", FAIL,
                "%s — 실행 실패(rc=%s)%s" % (p3, rc, " · MS Store 별칭 스텁" if stub else ""),
                "PATH엔 잡히나 실행이 죽는다 -> 지시층 561곳 전부 실패. "
                "실제 python.exe를 가리키는 심(shim)으로 교체 (§2a)")

    # 3. bash + 훅
    bash = shutil.which("bash") or _find_bash()
    add("bash", OK if bash else FAIL, bash or "PATH에 없음",
        "훅 2개가 bash 스크립트 — 없으면 날짜 앵커링 가드(7/6)가 죽는다")
    for h in ("session-start.sh", "validate-on-stop.sh"):
        p = os.path.join(REPO, ".claude", "hooks", h)
        if not os.path.exists(p):
            add(f"훅 {h}", FAIL, "파일 없음", "")
        elif bash:
            rc, _ = run([bash, "-n", p])
            add(f"훅 {h}", OK if rc == 0 else FAIL,
                "문법 OK" if rc == 0 else "bash 문법 오류", "")
        else:
            add(f"훅 {h}", SKIP, "bash 없어 검사 불가", "")

    # 3b. 런처 .ps1 의 UTF-8 BOM  [9/2 신설]
    #   ★ PowerShell 5.1은 **BOM 없는 .ps1을 ANSI(cp949)로 읽는다.** 그래서 스크립트 안의
    #     한글 문자열이 **파싱 단계에서** 깨지고, 로그·상태 메시지가 통째로 판독 불능이 된다
    #     (9/2 실측: catchup.ps1 첫 실행 로그가 "罹먯튂???먭?"로 나왔다).
    #   ★ 이게 위험한 이유는 **깨져도 스크립트가 정상 종료한다**는 것이다 — 예외가 안 나고
    #     exit 0이라 아무 가드에도 안 걸린다. 8/31의 그 패턴(조용히 그럴듯한 값을 낸다)이다.
    #   ⇒ 새 .ps1을 UTF-8(BOM 없음)로 저장하는 편집기가 흔하므로 기계로 본다.
    ps1s = sorted(glob.glob(os.path.join(REPO, ".claude", "routines", "*.ps1")))
    if not ps1s:
        add("런처 .ps1 BOM", SKIP, "런처 없음", "")
    else:
        bad = []
        for f in ps1s:
            try:
                if open(f, "rb").read(3) != b"\xef\xbb\xbf":
                    bad.append(os.path.basename(f))
            except Exception:                                  # noqa: BLE001
                bad.append(os.path.basename(f) + "(읽기실패)")
        add("런처 .ps1 BOM", OK if not bad else FAIL,
            f"{len(ps1s)}개 전부 UTF-8 BOM" if not bad else f"BOM 없음: {', '.join(bad)}",
            "" if not bad else "PowerShell 5.1이 cp949로 읽어 한글이 조용히 깨진다 — "
                               "파일 앞에 UTF-8 BOM을 붙일 것")

    # 4. Node / Playwright
    node = shutil.which("node")
    if node:
        _, ver = run([node, "--version"])
        add("Node.js", OK, ver.strip(), "web_shot.cjs·browser_captions.cjs")
    else:
        add("Node.js", WARN, "PATH에 없음", "화면 판독(web_shot) 불가 — 치명 아님")
    if node:
        rc, _ = run([node, "-e", "require.resolve('playwright')"], timeout=30)
        if rc != 0:
            rc, _ = run([node, "-e", "require.resolve('playwright-core')"], timeout=30)
        add("Playwright", OK if rc == 0 else WARN,
            "설치됨" if rc == 0 else "미설치 (npx playwright install chromium)",
            "web_shot.py")

    # 5. yt-dlp — 로컬 이전의 성과 판정 대상
    # ★[8/31] `shutil.which`만 보면 **설치돼 있는데도 미설치로 잡힌다** —
    # 윈도우 pip은 Scripts/에 깔고 그 디렉터리가 PATH에 없을 수 있다(실측).
    # 판정은 ytdlp_bin의 해석 순서(PATH → `-m yt_dlp`)를 그대로 쓴다.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from ytdlp_bin import ytdlp_label
        _yt = ytdlp_label()
    except Exception:
        _yt = "미설치"
    ok_yt = _yt != "미설치"
    add("yt-dlp", OK if ok_yt else WARN,
        _yt if ok_yt else "미설치 (pip install -U yt-dlp)",
        "대기목록 2 — 고해상도 프레임·댓글. 실제 생존은 api_health가 판정")

    # 6. 선택 pip 패키지
    for mod, why in PIP_OPTIONAL:
        rc, _ = run([sys.executable, "-c", f"import {mod}"])
        add(f"pip: {mod}", OK if rc == 0 else WARN,
            "설치됨" if rc == 0 else "미설치", why)

    # 7. 환경변수 키 (값 절대 미출력)
    for k in KEYS:
        val = os.environ.get(k, "")
        if val:
            add(f"env {k}", OK, mask(val), "")
        else:
            optional = k in KEY_OPTIONAL
            add(f"env {k}", WARN if optional else FAIL, "미설정",
                KEY_OPTIONAL.get(k, "해당 소스 폴백으로 강등 — §2b"))

    # 8. SSL_CERT_FILE — 로컬에선 반드시 미설정
    sc = os.environ.get("SSL_CERT_FILE", "")
    if ON_WEB:
        add("SSL_CERT_FILE", OK if sc else WARN, sc or "미설정",
            "웹 환경 = 프록시 CA 필요")
    else:
        add("SSL_CERT_FILE", OK if not sc else FAIL, sc or "미설정 (정답)",
            "로컬에서 설정하면 정상 인증서 검증이 깨진다 — §2b")

    # 9. 토스 — ★[8/31 정훈 승인] 룰이 뒤집혔다: 舊 "저장 금지"(웹 전제) → 로컬은 **환경변수 저장**.
    #    ⇒ 이 항목이 검사할 것도 뒤집힌다. "키가 없는가"가 아니라 **"주문 차단 가드가 실제로 막는가"**.
    #    (舊 판정을 그대로 뒀더니 승인된 설정을 FAIL로 찍었다 = 폐기된 룰을 집행하는 가드 —
    #     8/23 check_repealed_rules와 같은 클래스라 여기서 같이 고친다.)
    have = [k for k in ("TOSS_CLIENT_ID", "TOSS_CLIENT_SECRET") if os.environ.get(k)]
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import toss_snapshot as _ts
        blocked = 0
        for m, path in (("POST", "/api/v1/orders"), ("POST", "/API/V1//Orders/?x=1"),
                        ("DELETE", "/api/v1/orders/1"), ("POST", "/api/v1/conditional-orders")):
            try:
                _ts._assert_readonly(m, path)
            except Exception:
                blocked += 1
        ok_get = True
        try:
            _ts._assert_readonly("GET", "/api/v1/accounts")
        except Exception:
            ok_get = False
        guard_ok = blocked == 4 and ok_get
        detail = (f"주문 4종 차단·조회 통과 (키 {len(have)}/2 보유)" if guard_ok
                  else f"가드 이상 — 차단 {blocked}/4 · 조회통과 {ok_get}")
    except Exception as ex:
        guard_ok, detail = False, f"가드 점검 실패: {str(ex)[:50]}"
    add("토스 주문차단 가드", OK if guard_ok else FAIL, detail,
        "조회 전용 불변식 — 키를 저장한 전제 조건(CLAUDE.md 운영제약)")

    # 10. 클론 깊이
    rc, o = run(["git", "-C", REPO, "rev-parse", "--is-shallow-repository"])
    shallow = o.strip() == "true"
    rc2, o2 = run(["git", "-C", REPO, "rev-list", "--count", "HEAD"])
    n = o2.strip() if rc2 == 0 else "?"
    add("git 전체 히스토리", WARN if shallow else OK,
        f"{'얕은 클론' if shallow else '전체'} · {n} 커밋",
        "얕으면 score_calls --backfill 표본이 조용히 빈다 → git fetch --unshallow (대기목록 1)")

    # 11. ★ UTF-8 모드 (윈도우 cp949 사고)
    # !! sys.stdout.encoding을 보면 안 된다 — main()에서 reconfigure 하므로 항상 utf-8이
    #    나와 영구 false PASS가 된다(8/31, 이 가드 자신이 그렇게 깨졌다).
    #    실제로 죽는 건 **자식 프로세스의 텍스트 파이프**다: selfcheck가 92개 스크립트를
    #    subprocess(text=True)로 읽는데 기본 코덱이 cp949면 한글 출력에서 통째로 터진다.
    import locale as _loc
    pref = (_loc.getpreferredencoding(False) or "").lower()
    utf8_mode = bool(getattr(sys.flags, "utf8_mode", 0))
    if utf8_mode or "utf" in pref:
        add("UTF-8 모드", OK,
            "utf8_mode=%s · 기본코덱=%s" % (int(utf8_mode), pref or "미상"),
            "자식 프로세스 파이프가 한글을 견딘다")
    else:
        add("UTF-8 모드", FAIL,
            "utf8_mode=0 · 기본코덱=%s" % (pref or "미상"),
            "selfcheck(커밋 게이트)가 92개 스크립트 한글 출력에서 죽는다 "
            "→ 환경변수 PYTHONUTF8=1 영구 설정 (8/31 실측)")

    # 12. 쓰기 권한
    probe = os.path.join(REPO, "data", "app", ".doctor_probe")
    try:
        os.makedirs(os.path.dirname(probe), exist_ok=True)
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        add("data/ 쓰기", OK, "가능", "")
    except Exception as e:  # noqa: BLE001
        add("data/ 쓰기", FAIL, str(e), "빌더·원장이 전부 막힌다")

    # 13. KST 시계
    # ★[8/31 정정] 舊 구현은 `TZ=Asia/Seoul` + `time.tzset()`이었는데 **윈도우엔 tzset이 없다**.
    # TZ만 남아 MSVC 런타임이 "Asia/Seoul"을 파싱 못 해 **UTC로 떨어진 07:49를 KST라며 OK로
    # 찍고 있었다**(9시간 오차 · %Z는 "a/S" 쓰레기). 날짜 앵커링(7/6 사고)의 가드가
    # 스스로 틀린 날짜를 만들던 셈 = 8/23 *"초록불은 탐지기가 그 형태를 안 본다는 뜻일 수 있다"*.
    # ⇒ 고정 오프셋(+9 · 한국은 서머타임 없음)으로 계산하고 시스템 로컬시각과 어긋나면 경고.
    kst = datetime.now(timezone.utc) + timedelta(hours=9)
    local = datetime.now()
    skew = abs((local - kst.replace(tzinfo=None)).total_seconds())
    add("KST 시각", OK if skew < 300 else WARN,
        kst.strftime("%Y-%m-%d (%a) %H:%M")
        + ("" if skew < 300 else f" · 시스템시계와 {skew/3600:.1f}h 차"),
        "SessionStart 훅 앵커와 일치해야 한다")

    return out


def main():
    # 파이프로 넘길 때 윈도우 기본 코덱(cp949)이 '—' 같은 문자에서 죽는다 (8/31 실측).
    # 도구가 파이프 뒤에서 죽으면 루틴·훅에서 조용히 사라진다.
    for _st in (sys.stdout, sys.stderr):
        try:
            _st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

    ap = argparse.ArgumentParser(description="로컬 이전 프리플라이트 점검 (네트워크 미사용)")
    ap.add_argument("--json", action="store_true", help="기계 판독용 JSON 출력")
    a = ap.parse_args()

    res = checks()
    if a.json:
        print(json.dumps({"on_web": ON_WEB, "checks": res}, ensure_ascii=False, indent=2))
    else:
        icon = {OK: "✅", WARN: "⚠️", FAIL: "❌", SKIP: "⚪"}
        print(f"\n로컬 프리플라이트 — {'웹(원격)' if ON_WEB else '로컬'} 환경 · repo={REPO}\n")
        for c in res:
            print(f"{icon[c['status']]} {c['name']:<22} {c['detail']}")
            if c["why"] and c["status"] in (WARN, FAIL):
                print(f"     └ {c['why']}")
        nf = sum(1 for c in res if c["status"] == FAIL)
        nw = sum(1 for c in res if c["status"] == WARN)
        print(f"\nFAIL {nf} · WARN {nw} · 총 {len(res)}")
        print("FAIL 0이면 §2d 순서로: api_health → short_borrow --status → selfcheck")
    return 1 if any(c["status"] == FAIL for c in res) else 0


if __name__ == "__main__":
    sys.exit(main())
