#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""정훈 증권 — 알림 발송기 (폰 푸시 복구)

★[9/1 신설] 왜 필요한가
  무인 루틴을 웹 Claude Code Routines → 윈도우 작업 스케줄러로 옮기면서(경로 B),
  웹이 공짜로 주던 **폰 푸시를 잃었다**. `docs/local_migration.md`가 이걸
  "인정된 후퇴"로 적어뒀지만 후퇴를 인정한다고 문제가 사라지지 않는다 —
  R2가 16:00에 오더북을 내도 정훈은 **17:30에 앱을 직접 열어야만** 안다.
  폰창(평일 17:30~20:50)은 국내 시간외단일가(~18:00)와 겹치는 유일한 실시간 거래창인데,
  그 창이 열리는 걸 알려주는 장치가 없다.

  ⇒ 런처의 윈도우 토스트는 **PC 앞에 있을 때만** 보인다. 폰에 닿는 경로가 필요하다.

경로: 텔레그램 봇 (무료·앱 설치만·서버 불요·stdlib urllib으로 충분)
  환경변수 2개:  TELEGRAM_BOT_TOKEN  ·  TELEGRAM_CHAT_ID
  ⚠️ 이 키는 **알림 전송만** 가능하다 — 토스 키와 달리 계좌 권한이 없으므로
     무인 루틴에 노출해도 매매 위험이 없다(run_routine.ps1의 §토스 스크럽 대상 아님).

⚠️ 설정이 없으면 **조용히 성공한 척하지 않는다**(8/22 "가드 없는 폴백은 침묵보다 나쁘다").
   exit 3 = 미설정/미발송. 런처가 이 코드를 로그에 남긴다.

용법:
  notify.py --routine r2 --verdict OK --status data/logs/routines/last_status.json
  notify.py --orders                 # 오늘의 오더북 요약(액션 대기분만)
  notify.py --text "임의 메시지"
  notify.py --check                  # 설정 여부만 확인(발송 안 함)
"""
import argparse, json, os, sys, urllib.parse, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
API = "https://api.telegram.org/bot{token}/sendMessage"
LIMIT = 4000                      # 텔레그램 메시지 상한 4096자 — 여유를 둔다


def _creds():
    return os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")


def send(text: str, dry: bool = False) -> int:
    """0=발송 · 3=미설정 · 4=발송실패. 성공을 가장하지 않는 것이 이 함수의 계약이다."""
    token, chat = _creds()
    if dry:
        print(text); return 0
    if not token or not chat:
        missing = [n for n, v in (("TELEGRAM_BOT_TOKEN", token),
                                  ("TELEGRAM_CHAT_ID", chat)) if not v]
        print(f"⚠️ 알림 미발송 — 환경변수 없음: {', '.join(missing)}\n"
              f"   설정법: @BotFather 로 봇 생성 → 토큰 획득 → 그 봇에게 아무 말이나 보낸 뒤\n"
              f"   https://api.telegram.org/bot<토큰>/getUpdates 에서 chat id 확인 →\n"
              f"   setx TELEGRAM_BOT_TOKEN <토큰> ; setx TELEGRAM_CHAT_ID <id>\n"
              f"   ⚠️ setx 후에는 Claude Code·작업 스케줄러를 재시작해야 보인다"
              f"(환경변수는 프로세스 시작 시각에 고정된다 — 8/31 교훈)", file=sys.stderr)
        return 3
    body = urllib.parse.urlencode({
        "chat_id": chat, "text": text[:LIMIT],
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(API.format(token=token), data=body,
                                 headers={"User-Agent": "jd-desk/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            ok = json.load(r).get("ok")
        if ok:
            print("✅ 텔레그램 발송"); return 0
        print("⚠️ 텔레그램이 ok=false 반환", file=sys.stderr); return 4
    except urllib.error.HTTPError as e:
        print(f"⚠️ 발송 실패 HTTP {e.code} — {e.read()[:200]!r}", file=sys.stderr); return 4
    except Exception as e:                                        # noqa: BLE001
        print(f"⚠️ 발송 실패 {type(e).__name__}: {e}", file=sys.stderr); return 4


def msg_routine(kind: str, verdict: str, status_path: str) -> str:
    st = {}
    try:
        st = json.load(open(status_path, encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        pass
    icon = {"OK": "✅", "UNCOMMITTED": "🟠", "TOKEN_LIMIT": "🟡",
            "NOT_LOGGED_IN": "🔴", "PERMISSION_BLOCKED": "🟠"}.get(verdict, "🔴")
    lines = [f"{icon} 루틴 {kind} — {verdict}",
             f"{st.get('kst', '')} · {st.get('minutes', '?')}분"]
    if st.get("late_min"):
        lines.append(f"⏰ 예정 {st.get('scheduled')}보다 {st['late_min']}분 지각")
    if st.get("uncommitted"):
        lines.append(f"⚠️ 미커밋 {st['uncommitted']}건 — 다음 세션이 못 본다")
    if verdict == "OK":
        lines.append(_orders_digest(limit=5))
    return "\n".join(x for x in lines if x)


def _orders_digest(limit: int = 8, days: int = 14) -> str:
    """오더북에서 **아직 액션이 남은 것**만. 체결·종결은 폰에서 볼 이유가 없다.

    ⚠️ 두 겹으로 거른다. 상태만 보면 6~7월 잔재(폐기된 7,500 안전핀 오더 등)까지
       23건이 딸려와 폰 알림이 노이즈가 된다 — 최근 {days}일 안의 건으로 한정한다.
       (미래 날짜 = 예정 오더이므로 남긴다.)
    """
    import datetime as _dt
    try:
        d = json.load(open(os.path.join(ROOT, "data", "app", "tasks.json"),
                           encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        return ""
    today = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=9)).date()
    live = []
    for o in (d.get("orders") or []):
        st = str(o.get("status") or "")
        if st.startswith("✅") or "체결 확인 완료" in st or "종결" in st or "폐기" in st:
            continue
        try:
            od = _dt.date.fromisoformat(str(o.get("date"))[:10])
            if (today - od).days > days:
                continue
        except Exception:                                         # noqa: BLE001
            continue          # 날짜 없는 건 = 언제 것인지 모른다 → 폰에 안 올린다
        label = str(o.get("label") or o.get("ticker") or "")[:70]
        px = o.get("price")
        live.append(f"· {label}" + (f" @ {px}" if px else ""))
    if not live:
        return ""
    head = f"\n📋 대기 오더 {len(live)}건 (폰창 17:30~20:50)"
    return head + "\n" + "\n".join(live[:limit]) + (
        f"\n… 외 {len(live) - limit}건" if len(live) > limit else "")


def main() -> int:
    ap = argparse.ArgumentParser(description="폰 알림 발송 (텔레그램) — 웹 Routines push 대체")
    ap.add_argument("--routine", help="루틴 종류 (r1/r2/r3/r4a/r4b)")
    ap.add_argument("--verdict", default="OK", help="런처 판정")
    ap.add_argument("--status", default=os.path.join(ROOT, "data", "logs", "routines",
                                                     "last_status.json"))
    ap.add_argument("--orders", action="store_true", help="대기 오더북만 발송")
    ap.add_argument("--text", help="임의 텍스트 발송")
    ap.add_argument("--check", action="store_true", help="설정 여부만 확인")
    ap.add_argument("--dry-run", action="store_true", help="발송 없이 본문만 출력")
    a = ap.parse_args()

    if a.check:
        tok, chat = _creds()
        print(f"TELEGRAM_BOT_TOKEN: {'설정됨' if tok else '없음'} · "
              f"TELEGRAM_CHAT_ID: {'설정됨' if chat else '없음'}")
        return 0 if (tok and chat) else 3

    if a.text:
        text = a.text
    elif a.orders:
        text = _orders_digest(limit=12).strip() or "대기 오더 없음"
    elif a.routine:
        text = msg_routine(a.routine, a.verdict, a.status)
    else:
        ap.error("--routine · --orders · --text · --check 중 하나가 필요하다")
    return send(text, dry=a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
