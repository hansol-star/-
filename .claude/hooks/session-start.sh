#!/bin/bash
# SessionStart 훅 — 세션 실측 앵커 자동 주입 [2026-07-14 B5]
# ★7/6 날짜 앵커링 오류(영구교정)의 기계화: 세션이 열릴 때마다 KST 날짜·요일·시각,
# 장세션 상태(스케줄 계산), 최신 보고서 버전, 급락 TF 상태를 additionalContext로 주입한다.
# 어떤 실패에도 세션을 막지 않는다(조용히 통과).
# ※ 이 훅은 '스케줄 기준' 상태다 — 공휴일 미반영. 실시세(market_data.py) 교차검증 의무는 그대로.
#
# ★[2026-11-22 K1] 체크아웃 동기화를 여기서 먼저 한다. 공유 체크아웃이 11/5부터 `claude/report-1105-sync`에
#   머물렀고, 舊 git_sync·R2 런처는 `main`일 때만 따라가서 클라우드(C2·C3·R3)·봇 커밋이 17일간 로컬로 안
#   내려왔다 — 이 훅은 로컬 파일만 보고 'v140이 최신'이라고 주입했는데 origin엔 v141이 있었다.
#   ⇒ ① git_sync --ff-only(fetch 8초 제한 · 실패해도 마지막으로 받은 origin 기준으로 ff · dirty 파일 보호)
#      ② 보고서 번호는 로컬·origin 둘 다 보고 큰 쪽 기준 ③ 남은 뒤처짐·옛 판 위 수정·미푸시 정본을 경고로 주입.
#   네트워크는 ①의 fetch 한 번뿐이다. 테스트: SESSION_START_NOW=YYYY-MM-DDTHH:MM · SESSION_START_NO_SYNC=1.
#
# ★[2026-11-24 K1 리뷰 PM-3·H12·H1·K1-CONC-06·PM-4·H8·H10]
#   · PM-3·H12: 동기화(브랜치 이동)는 **로컬 공유 체크아웃에서만**. 클라우드 루틴(C2·C3·R3)은 이 설정으로 새 리눅스
#     클론에서 도는데, 舊 훅은 거기서도 브랜치를 옮기고 갈라진 기능 브랜치에 '🚨 자동 동기화 실패'를 띄웠다.
#     판정 = GIT_GUARD_SHARED=1/0 > CLAUDE_CODE_REMOTE 있으면 0 > 윈도우(MINGW/MSYS)면 1 (git-write-guard와 같은 신호).
#     compact(자동 압축)로 다시 불릴 때도 동기화하지 않는다(작업 중인 세션 밑에서 파일을 병합하지 않게) — 앵커만 넣는다.
#   · H1: 舊 `timeout 25`가 fetch 초과분을 못 막아 ff 한가운데를 죽였다. 이제 fetch는 git_sync 안에서 프로세스 트리째
#     8초에 끊기고, ff는 중단돼도 저널로 복구된다. 바깥 timeout 30은 마지막 안전망(설정 timeout 40 아래).
#   · K1-CONC-06·PM-4: 11/24 부팅 직후 '(fetch 실패 — … · 0분 전)'은 실패 **원인을 버리고**, 실패한 fetch도 갱신하는
#     FETCH_HEAD mtime을 '받은 시각'으로 썼다(그날은 캐치업 런처·R1과 동시 fetch → ref 잠금 경합 또는 부팅 직후 미연결로
#     추정 — 원인 문구가 버려져 확정 불가). 이제 원인(시간 초과/DNS/연결/인증/경합)과 **마지막 성공** fetch 시각을 쓴다.
#   · H12(3): 파이썬 출력 인코딩을 훅 안에서 고정(설정 env가 없으면 cp949 오류로 0바이트였다).
set -u
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

HOOK_INPUT=""
if [ ! -t 0 ]; then
  HOOK_INPUT="$(timeout 3 cat 2>/dev/null)"
fi
SRC="$(HOOK_INPUT="$HOOK_INPUT" python3 -c 'import json,os
try:
    d = json.loads(os.environ.get("HOOK_INPUT") or "{}")
    print(d.get("source", "") if isinstance(d, dict) else "")
except Exception:
    print("")' 2>/dev/null)"
SHARED="${GIT_GUARD_SHARED:-}"
if [ "$SHARED" != "0" ] && [ "$SHARED" != "1" ]; then
  if [ -n "${CLAUDE_CODE_REMOTE:-}" ]; then SHARED=0
  else case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) SHARED=1 ;; *) SHARED=0 ;; esac
  fi
fi
SYNC_JSON=""
if [ -n "${SESSION_START_NO_SYNC:-}" ]; then SYNC_MODE="off(test)"
elif [ "$SHARED" != "1" ]; then SYNC_MODE="off(cloud)"
elif [ "$SRC" = "compact" ]; then SYNC_MODE="off(compact)"
else
  SYNC_MODE="on"
  SYNC_JSON="$(timeout 30 python3 .claude/skills/portfolio-desk/scripts/git_sync.py --ff-only --json --fetch-timeout 8 --lock-wait 6 2>/dev/null | tail -n 1)"
fi
export SYNC_JSON SYNC_MODE

python3 - <<'PY' 2>/dev/null || exit 0
import glob, json, os, re, sys, time
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
_fixed = os.environ.get("SESSION_START_NOW", "").strip()
try:
    from zoneinfo import ZoneInfo
    _tz_kst, _tz_et = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
except Exception:
    _tz_kst, _tz_et = KST, None
if _fixed:
    now_kst = datetime.fromisoformat(_fixed).replace(tzinfo=_tz_kst)
else:
    now_kst = datetime.now(_tz_kst)
now_et = now_kst.astimezone(_tz_et) if _tz_et is not None else None

wd = now_kst.weekday()
day_kr = "월화수목금토일"[wd]
hm = now_kst.hour * 60 + now_kst.minute

# ★[11/22] 9/14 KRX 개편 뒤 구조(정본 = price_watch.market_open_kst · CLAUDE.md 운영 제약):
#   프리마켓 07:00–07:50 · 정규 09:00–15:30 · 애프터마켓(시간외 접속매매) 16:00–20:00(지정가 · 전일종가 ±30%).
#   舊 문구(시간외단일가 16:00–18:00 · 18시 이후 '종가 고정')가 개편 뒤 두 달 넘게 매 세션 주입됐다(C5·E3).
#   '종가'는 기준이 셋이다(CLAUDE.md 10/13) — 정규장 종가는 15:30에 확정, 통합(애프터) 종가는 20:00.
#   hooks_selftest.py가 이 표를 price_watch.market_open_kst와 대조한다(드리프트 가드).
if wd >= 5:
    krx = "주말 휴장"
elif hm < 7 * 60:
    krx = "개장 전 (프리마켓 07:00–07:50 · 정규 09:00–15:30)"
elif hm <= 7 * 60 + 50:
    krx = "프리마켓 중 (07:00–07:50 · 지정가만)"
elif hm < 9 * 60:
    krx = "정규장 개장 전 (09:00 · 프리마켓 종료)"
elif hm <= 15 * 60 + 30:
    krx = "정규장 중 (09:00–15:30) — 지수가 장중 등락 중이어야 정상"
elif hm < 16 * 60:
    krx = "정규장 마감 — 정규장 종가 확정 (애프터마켓 16:00–20:00 대기)"
elif hm <= 20 * 60:
    krx = "애프터마켓 중 (16:00–20:00 · 접속매매·지정가만) — 정규장 종가는 15:30 확정, 통합 종가는 20:00"
else:
    krx = "장 종료 (정규장 종가 15:30 · 통합 종가 20:00 확정)"

if now_et is not None:
    ewd, ehm = now_et.weekday(), now_et.hour * 60 + now_et.minute
    if ewd >= 5:
        us = "주말 휴장"
    elif ehm < 9 * 60 + 30:
        us = "개장 전 (정규 09:30–16:00 ET, 서머타임 자동반영)"
    elif ehm < 16 * 60:
        us = "정규장 중 (09:30–16:00 ET)"
    else:
        us = "장 마감 (애프터마켓)"
    us += " ※공휴일·조기폐장 미반영(★11/24 H10 — 추수감사절·다음 날 13:00 ET 조기폐장도 '정규장 중'으로 보인다)"
else:
    us = "ET 계산 불가 — 수동 확인"

# ── K1: 체크아웃 동기화 결과 + 읽기 전용 상태(origin ref 기준) ──
sync_lines = []
st = {}
try:
    sys.path.insert(0, os.path.join(".claude", "skills", "portfolio-desk", "scripts"))
    import git_sync  # noqa: E402
    st = git_sync.status(os.getcwd())
except Exception:
    st = {}
try:
    sy = json.loads(os.environ.get("SYNC_JSON") or "{}")
except Exception:
    sy = {}
if not isinstance(st, dict):                 # ★[11/24 H8] null·리스트면 앵커까지 통째로 사라졌다
    st = {}
if not isinstance(sy, dict):
    sy = {}
sync_mode = os.environ.get("SYNC_MODE", "")
shared = sync_mode in ("on", "off(compact)", "off(test)")

def _age_txt():
    """마지막 **성공** fetch(git_sync 기록) — 없으면 비어 있지 않은 FETCH_HEAD(실패한 fetch는 0바이트로 덮는다)."""
    t = st.get("last_fetch_ok")
    if not t:
        try:
            g = os.path.join(".git", "FETCH_HEAD")
            if os.path.getsize(g) > 0:
                t = os.path.getmtime(g)
        except Exception:
            t = None
    if not t:
        return "미상"
    mins = (time.time() - float(t)) / 60
    return f"{mins / 60:.0f}시간 전" if mins >= 90 else f"{mins:.0f}분 전"

branch = st.get("branch") or sy.get("branch") or "?"
behind, nonbot, ahead = st.get("behind"), st.get("behind_nonbot"), st.get("ahead")
local = str(sy.get("local") or "")
if sy.get("recovered"):
    sync_lines.append(f"- (git_sync: {sy['recovered']})")
if local == "ff":
    extra = []
    if sy.get("merged_dirty"):
        extra.append(f"dirty 병합 {len(sy['merged_dirty'])}건")
    if sy.get("kept_dirty"):
        extra.append(f"⚠️ 충돌로 보존 {len(sy['kept_dirty'])}건")
    sync_lines.append(f"- 체크아웃: `{branch}` ← origin/main 자동 동기화 완료" + (f" ({' · '.join(extra)})" if extra else ""))
if sy.get("fetch"):
    reason = str(sy["fetch"]).split("기준:", 1)[-1].strip()
    sync_lines.append(f"- ⚠️ origin 확인 불가 — fetch 실패({reason[:90]}) · 마지막 성공 fetch {_age_txt()} 기준으로 판정")
elif local != "ff" and behind == 0 and ahead == 0:
    sync_lines.append(f"- 체크아웃: `{branch}` = origin/main (마지막 성공 fetch {_age_txt()})")
if behind:
    if shared:
        sync_lines.append(f"- 🚨 체크아웃이 origin/main보다 **{behind}커밋 뒤**(봇 제외 {nonbot}) — 자동 동기화 안 됨: "
                          f"{local or sync_mode or '미실행'}. 커밋·보고서 작성 전에 "
                          "`python .claude/skills/portfolio-desk/scripts/git_sync.py --ff-only`로 맞출 것")
    else:
        sync_lines.append(f"- (클라우드 클론 — 훅은 브랜치를 옮기지 않는다) `{branch}`는 origin/main보다 {behind}커밋 뒤"
                          f"(봇 제외 {nonbot}) · 앞 {ahead or 0}")
if st.get("kept"):
    ks = ", ".join(list(st["kept"])[:6])
    sync_lines.append(f"- ⚠️ 옛 판 위에 남은 수정 {len(st['kept'])}건(.git/git_sync_kept.json): {ks} — "
                      "그대로 커밋하면 업스트림 변경이 되돌아간다. git_sync.py -m … <파일>로 올리거나(자동 병합·충돌 시 중단) "
                      "손으로 합친 뒤 `git_sync.py --resolved <파일>`")
if st.get("kept_corrupt"):
    sync_lines.append("- 🚨 .git/git_sync_kept.json 손상 — git_sync가 ff·publish를 멈췄다. 파일을 확인·복구할 것")
if st.get("journal_pending"):
    sync_lines.append("- ⚠️ 중단된 git_sync ff 저널이 있다 — `git_sync.py --ff-only`가 마무리한다(index.lock이 남았으면 그 뒤 풀린다)")
if st.get("ahead_canon"):
    sync_lines.append(f"- ⚠️ origin/main에 없는 로컬 커밋 {ahead}개가 정본을 건드렸다: "
                      f"{', '.join(st['ahead_canon'][:5])} — 푸시 확인")

best, bestv = None, -1.0
for p in glob.glob("docs/reports/report_v*.md"):
    m = re.search(r"report_v(\d+(?:\.\d+)?)", os.path.basename(p))
    if m and float(m.group(1)) > bestv:
        bestv, best = float(m.group(1)), os.path.basename(p)
olat = st.get("origin_latest")
if isinstance(olat, int) and olat > bestv:
    sync_lines.append(f"- 🚨 origin에 더 새 보고서 v{olat}가 있다(로컬 최신 {best or '없음'}) — 로컬 기준으로 쓰면 번호 중복·정본 되돌림")
    bestv = float(olat)
    best = f"report_v{olat}_*.md (origin/main — 로컬 미반영)"
next_v = int(bestv) + 1 if bestv >= 0 else "?"

tf_line = ""
try:
    if "급락대응 TF = ACTIVE" in open("CLAUDE.md", encoding="utf-8").read():
        tf_line = "\n- 🚨 급락대응 TF = ACTIVE — 행동 정본 docs/crash_tf.md, 보고서마다 §1 상황판 갱신·§5 해제 게이트 판정"
except Exception:
    pass

# ★[2026-09-03 정훈 갱신] 폰 가용 = **평일 상시(주말 제외)**. 舊 '평일 17:30~20:50 / 주말 09:00~20:50' 폐기.
#   ⚠️ 이 값이 stale하면 세션마다 '지금 불가'라는 틀린 앵커가 주입돼 오더 설계가 통째로 왜곡된다
#     (9/4 실측: CLAUDE.md·master.md는 9/3에 고쳤는데 이 훅만 옛 창을 계속 주입하고 있었다).
phone_ok = wd < 5

# 📌 당일 지시 채널 [2026-08-12 신설] — 정훈이 대화 세션에서 내린 '오늘만' 지시를 그날 모든 세션
# (무인 루틴 포함)에 전달한다. date가 오늘(KST)일 때만 노출 = 자동 만료.
directive_line = ""
try:
    with open("data/app/session_directive.json", encoding="utf-8") as f:
        _d = json.load(f)
    if isinstance(_d, dict):
        _items = _d.get("directives") if isinstance(_d.get("directives"), list) else [_d]
    elif isinstance(_d, list):
        _items = _d
    else:
        _items = []
    _today = now_kst.strftime("%Y-%m-%d")
    for _it in _items:
        if not isinstance(_it, dict):
            continue
        if _it.get("date") == _today and _it.get("text"):
            _scope = _it.get("scope") or "전체 세션"
            directive_line += f"\n- 📌 **오늘 지시(정훈 · {_scope} · 오늘 한정)**: {_it['text']}"
except Exception:
    pass

ctx = (
    "[세션 실측 앵커 — SessionStart 훅 자동 주입 (★7/6 날짜 앵커링 재발방지 기계화)]\n"
    f"- 오늘(KST): {now_kst.strftime('%Y-%m-%d')} ({day_kr}) {now_kst.strftime('%H:%M')} — 이 앵커가 날짜의 정본. 직전 보고서의 '오늘/다음 세션' 서사는 참조용.\n"
    f"- KRX(스케줄 기준): {krx} ※공휴일 미반영 — market_data.py 실시세(장중 등락 vs 종가 고정)로 교차검증 필수\n"
    f"- 미국장(스케줄 기준): {us}\n"
    f"- 최신 보고서: {best or '없음'} → 새 거래일 보고서는 v{next_v} (직전 보고서에 부록으로 덧붙이지 말 것)\n"
    f"- 정훈 폰: {'지금 가용' if phone_ok else '지금 불가(주말)'} (평일 상시 · 주말 제외 — 9/3 갱신)"
    + ("\n" + "\n".join(sync_lines) if sync_lines else "")
    + tf_line
    + directive_line
)

print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                         "additionalContext": ctx}}, ensure_ascii=False))
PY
exit 0
