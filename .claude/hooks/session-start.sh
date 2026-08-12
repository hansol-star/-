#!/bin/bash
# SessionStart 훅 — 세션 실측 앵커 자동 주입 [2026-07-14 B5]
# ★7/6 날짜 앵커링 오류(영구교정)의 기계화: 세션이 열릴 때마다 KST 날짜·요일·시각,
# 장세션 상태(스케줄 계산), 최신 보고서 버전, 급락 TF 상태를 additionalContext로 주입한다.
# 오프라인·결정적(네트워크 호출 없음, <1초). 어떤 실패에도 세션을 막지 않는다(조용히 통과).
# ※ 이 훅은 '스케줄 기준' 상태다 — 공휴일 미반영. 실시세(market_data.py) 교차검증 의무는 그대로.
set -u
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

python3 - <<'PY' 2>/dev/null || exit 0
import glob, json, os, re
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    now_et = datetime.now(ZoneInfo("America/New_York"))
except Exception:
    now_kst = datetime.now(timezone(timedelta(hours=9)))
    now_et = None

wd = now_kst.weekday()
day_kr = "월화수목금토일"[wd]
hm = now_kst.hour * 60 + now_kst.minute

if wd >= 5:
    krx = "주말 휴장"
elif hm < 9 * 60:
    krx = "개장 전 (정규장 09:00–15:30)"
elif hm < 15 * 60 + 30:
    krx = "정규장 중 (09:00–15:30) — 지수가 장중 등락 중이어야 정상"
elif hm < 16 * 60:
    krx = "정규장 마감 (시간외단일가 16:00–18:00 대기)"
elif hm < 18 * 60:
    krx = "시간외단일가 중 (16:00–18:00)"
else:
    krx = "장 종료 (종가 고정)"

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
else:
    us = "ET 계산 불가 — 수동 확인"

best, bestv = None, -1.0
for p in glob.glob("docs/reports/report_v*.md"):
    m = re.search(r"report_v(\d+(?:\.\d+)?)", os.path.basename(p))
    if m and float(m.group(1)) > bestv:
        bestv, best = float(m.group(1)), os.path.basename(p)
next_v = int(bestv) + 1 if bestv >= 0 else "?"

tf_line = ""
try:
    if "급락대응 TF = ACTIVE" in open("CLAUDE.md", encoding="utf-8").read():
        tf_line = "\n- 🚨 급락대응 TF = ACTIVE — 행동 정본 docs/crash_tf.md, 보고서마다 §1 상황판 갱신·§5 해제 게이트 판정"
except Exception:
    pass

phone_ok = (9 * 60 <= hm <= 20 * 60 + 50) if wd >= 5 else (17 * 60 + 30 <= hm <= 20 * 60 + 50)

# 📌 당일 지시 채널 [2026-08-12 신설] — 정훈이 대화 세션에서 내린 '오늘만' 지시를 그날 모든 세션
# (무인 루틴 포함)에 전달한다. 루틴 프롬프트는 에이전트가 못 고치므로(8/6 확정 — http_api 트리거는
# update_trigger 거부) 배선은 코드 쪽에 심는다. date가 오늘(KST)일 때만 노출 = 자동 만료.
directive_line = ""
try:
    with open("data/app/session_directive.json", encoding="utf-8") as f:
        _d = json.load(f)
    # 단일 객체 / 리스트 / {"directives":[...]} 모두 허용 — 며칠치를 미리 적어둘 수 있게.
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
    f"- 정훈 폰: {'지금 가용' if phone_ok else '지금 불가'} (평일 17:30–20:50 / 주말 09:00–20:50 KST)"
    + tf_line
    + directive_line
)

print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                         "additionalContext": ctx}}, ensure_ascii=False))
PY
exit 0
