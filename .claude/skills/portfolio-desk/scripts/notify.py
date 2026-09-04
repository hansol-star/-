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
import argparse, json, os, sys, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
API = "https://api.telegram.org/bot{token}/sendMessage"

# ── 카카오톡 "나에게 보내기" [9/4 신설 · 정훈 요청 "카톡으로는 못해?"] ──────────
#   왜 넣나: 텔레그램은 설정이 두 줄이지만 **정훈이 안 쓰는 앱**이다.
#   안 보는 알림은 없는 알림이라, 설정이 번거로워도 실제로 보는 채널이 낫다.
#
#   ⚠️ 토큰 수명이 짧다 — 이 채널의 유일한 함정이다:
#     · access_token  6시간   → 매번 refresh로 재발급(자동)
#     · refresh_token 2개월   → **남은 기간이 1개월 미만일 때만** 새 값이 응답에 실려 온다
#   ⇒ 응답에 refresh_token이 오면 **반드시 저장**해야 한다. 안 하면 2개월 뒤
#     조용히 죽고, 그날부터 알림이 안 가는데 아무도 모른다(이 레포가 가장 싫어하는 형태).
#     아래 _kakao_refresh()가 그걸 파일에 즉시 덮어쓰고, 저장 사실을 출력한다.
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
KAKAO_CACHE = os.path.join(ROOT, "data", "logs", "kakao_token.json")
LIMIT = 4000                      # 텔레그램 메시지 상한 4096자 — 여유를 둔다


def _creds():
    return os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")


def _kakao_creds():
    return os.environ.get("KAKAO_REST_KEY"), os.environ.get("KAKAO_REFRESH_TOKEN")


def _kakao_cache():
    try:
        return json.load(open(KAKAO_CACHE, encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        return {}


def _kakao_save(d):
    os.makedirs(os.path.dirname(KAKAO_CACHE), exist_ok=True)
    json.dump(d, open(KAKAO_CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def _kakao_refresh(rest_key, refresh_token):
    """access_token 재발급. 응답에 refresh_token이 오면 **반드시 저장한다.**

    카카오는 refresh_token 잔여가 1개월 미만일 때만 새 값을 준다 — 그 한 번을 놓치면
    2개월 뒤 만료되고, 그때부터 알림이 조용히 끊긴다. 저장은 선택이 아니라 필수다.
    """
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token", "client_id": rest_key,
        "refresh_token": refresh_token}).encode()
    req = urllib.request.Request(KAKAO_TOKEN_URL, data=body,
                                 headers={"Content-Type":
                                          "application/x-www-form-urlencoded;charset=utf-8"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.load(r)
    cache = _kakao_cache()
    cache["access_token"] = d.get("access_token")
    cache["expires_at"] = time.time() + int(d.get("expires_in", 21600)) - 300  # 5분 여유
    if d.get("refresh_token"):
        cache["refresh_token"] = d["refresh_token"]
        print("🔑 카카오 refresh_token 갱신됨 — 저장 완료. "
              "환경변수 KAKAO_REFRESH_TOKEN도 이 값으로 바꿔둘 것(캐시 유실 대비)",
              file=sys.stderr)
    _kakao_save(cache)
    return cache["access_token"]


def _kakao_token():
    rest_key, env_refresh = _kakao_creds()
    if not rest_key:
        return None
    cache = _kakao_cache()
    if cache.get("access_token") and cache.get("expires_at", 0) > time.time():
        return cache["access_token"]
    refresh = cache.get("refresh_token") or env_refresh
    if not refresh:
        return None
    return _kakao_refresh(rest_key, refresh)


def send_kakao(text: str) -> tuple[int, str]:
    """0=성공 · 3=미설정 · 4=실패. 성공을 가장하지 않는다."""
    rest_key, refresh = _kakao_creds()
    if not (rest_key and (refresh or _kakao_cache().get("refresh_token"))):
        return 3, "KAKAO_REST_KEY/KAKAO_REFRESH_TOKEN 미설정"
    try:
        tok = _kakao_token()
        if not tok:
            return 3, "카카오 토큰 발급 불가"
        tpl = {"object_type": "text", "text": text[:1900],
               "link": {"web_url": "https://github.com", "mobile_web_url": "https://github.com"}}
        body = urllib.parse.urlencode({"template_object":
                                       json.dumps(tpl, ensure_ascii=False)}).encode()
        req = urllib.request.Request(KAKAO_SEND_URL, data=body, headers={
            "Authorization": "Bearer " + tok,
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"})
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.load(r)
        if res.get("result_code") == 0:
            return 0, "카카오톡 발송"
        return 4, f"카카오 result_code={res.get('result_code')}"
    except urllib.error.HTTPError as e:
        return 4, f"카카오 HTTP {e.code} — {e.read()[:160]!r}"
    except Exception as e:                                        # noqa: BLE001
        return 4, f"카카오 {type(e).__name__}: {e}"


def send(text: str, dry: bool = False) -> int:
    """0=발송 · 3=미설정 · 4=발송실패. 성공을 가장하지 않는 것이 이 함수의 계약이다.

    채널 우선순위 = **카카오톡 → 텔레그램**. 정훈이 실제로 보는 앱이 카톡이라
    거기가 1순위이고, 텔레그램은 카톡 미설정·실패 시의 폴백이다.
    ⚠️ 하나라도 성공하면 0이지만 **어느 채널로 갔는지 반드시 출력**한다 —
       "보냈다"만 알고 어디로 갔는지 모르면 한쪽이 죽어도 눈치채지 못한다.
    """
    if dry:
        print(text); return 0

    k_code, k_msg = send_kakao(text)
    if k_code == 0:
        print(f"✅ {k_msg}"); return 0
    if k_code == 4:                       # 설정은 됐는데 실패 — 조용히 넘기지 않는다
        print(f"⚠️ {k_msg} → 텔레그램 폴백 시도", file=sys.stderr)

    token, chat = _creds()
    if not token or not chat:
        if k_code == 3:
            print("⚠️ 알림 미발송 — 카카오·텔레그램 **둘 다 미설정**.\n"
                  "   카카오(권장·정훈이 실제로 보는 채널):\n"
                  "     developers.kakao.com 앱 생성 → REST API 키 획득\n"
                  "     → 카카오 로그인 활성화 + 동의항목 'talk_message' 체크\n"
                  "     → 인가코드로 refresh_token 발급\n"
                  "     → setx KAKAO_REST_KEY <키> ; setx KAKAO_REFRESH_TOKEN <토큰>\n"
                  "   텔레그램(설정은 더 간단):\n"
                  "     @BotFather → /newbot → 토큰 →\n"
                  "     setx TELEGRAM_BOT_TOKEN <토큰> ; setx TELEGRAM_CHAT_ID <id>\n"
                  "   ⚠️ setx 후 Claude Code·작업 스케줄러 재시작 필요"
                  "(환경변수는 프로세스 시작 시각에 고정된다 — 8/31 교훈)", file=sys.stderr)
            return 3
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


def _todos() -> str:
    """오늘 할 일 — **알림 맨 위**. 정훈 9/4 지시 "내가 할 일, 그리고 했는지도 체크".

    알림을 여는 이유는 '지금 뭘 해야 하나'를 알기 위해서다. 시세·지표는 그 다음이다.
    ⚠️ 완료분도 ✅로 같이 보여준다 — 안 보이면 '내가 했던가?'를 매번 다시 확인해야 한다.
    """
    try:
        d = json.load(open(os.path.join(ROOT, "data", "app", "tasks.json"), encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        return ""
    items = (d.get("tasks") or {}).get("today") or []
    if not items:
        return ""
    undone = [x for x in items if not x.get("done")]
    done = [x for x in items if x.get("done")]
    lines = [f"📌 오늘 할 일 {len(done)}/{len(items)}"]
    for x in undone:
        lines.append(f"☐ {str(x.get('text',''))[:60]}")
    for x in done:
        lines.append(f"✅ {str(x.get('text',''))[:44]}")
    return "\n".join(lines)


def _market_line() -> str:
    """상세 — 알림 **아래쪽**. 판단 배경이지 행동 지시가 아니다."""
    try:
        raw = open(os.path.join(ROOT, "app", "data.js"), encoding="utf-8").read()
        d = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    except Exception:                                             # noqa: BLE001
        return ""
    out = []
    tot = d.get("total_krw") or d.get("total_assets")
    chg = d.get("total_change_krw") or d.get("daily_change_krw")
    if tot:
        s = f"💰 총자산 {int(tot):,}원"
        if chg:
            s += f" ({int(chg):+,})"
        out.append(s)
    idx = d.get("indices") or {}
    for k in ("코스피", "KOSPI"):
        v = idx.get(k) if isinstance(idx, dict) else None
        if isinstance(v, dict) and v.get("price"):
            out.append(f"📈 코스피 {v['price']:,} ({v.get('change_pct', 0):+.2f}%)")
            break
    return " · ".join(out)


def compose(trigger_block: str = "") -> str:
    """알림 표준 형식 — **할 일 → 트리거 → 상세** 순서.

    정훈 9/4: "자세한 내용은 아래로 내리고 내가 할 일, 그리고 했는지도 체크".
    순서가 곧 우선순위다. 폰을 여는 이유는 행동이지 관찰이 아니다.
    """
    parts = [p for p in (_todos(), trigger_block) if p]
    tail = _market_line()
    if tail:
        parts.append("─────────\n" + tail)
    return "\n\n".join(parts)


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
    ap.add_argument("--brief", action="store_true",
                    help="정기 브리핑 — 할 일 먼저, 상세는 아래(하루 3회: 개장·마감·미장)")
    ap.add_argument("--text", help="임의 텍스트 발송")
    ap.add_argument("--check", action="store_true", help="설정 여부만 확인")
    ap.add_argument("--dry-run", action="store_true", help="발송 없이 본문만 출력")
    a = ap.parse_args()

    if a.check:
        kk, kr = _kakao_creds()
        cached = _kakao_cache().get("refresh_token")
        print(f"KAKAO_REST_KEY: {'설정됨' if kk else '없음'} · "
              f"KAKAO_REFRESH_TOKEN: {'설정됨' if (kr or cached) else '없음'}"
              + ("  (캐시본 사용 중)" if cached and not kr else ""))
        tok, chat = _creds()
        print(f"TELEGRAM_BOT_TOKEN: {'설정됨' if tok else '없음'} · "
              f"TELEGRAM_CHAT_ID: {'설정됨' if chat else '없음'}")
        return 0 if (tok and chat) else 3

    if a.brief:
        text = compose()
        if not text.strip():
            print("보낼 내용 없음 — 할 일도 시세도 비었다"); return 0
    elif a.text:
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
