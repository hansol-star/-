#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""price_watch.py — 장중 실시간 트리거 감시 + 폰 알림 [2026-09-03 신설 · 정훈 지시]

■ 왜 만들었나
`triggers.py`는 **세션당 1회** 평가하고 끝난다. 그래서 매수존·트림가에 가격이 닿아도
**아무도 알려주지 않았다** — 다음 보고서(R2 16:00)에서야 "닿았었다"를 사후에 안다.
이 구조는 정훈 폰창이 하루 3시간20분(17:30~20:50)일 때는 합리적이었다.
어차피 그 창에서만 집행할 수 있으니 실시간으로 알아봐야 할 일이 없었다.

**9/3에 그 전제가 사라졌다** — 폰 가용이 평일 상시로 바뀌면서
국내 정규장(09:00~15:30)·미국 정규장(22:30~05:00) 실시간 대응이 가능해졌다.
⇒ 이제 "가격이 닿는 순간"을 아는 것이 실제 행동으로 이어진다. 그 배관이 이 파일이다.

■ 무엇을 하나
  portfolio.json `alerts`(28건)를 N분마다 평가 → **새로 발동한 것만** 텔레그램으로 보낸다.
  발동 판정·조건 해석은 전부 `triggers.evaluate()`를 그대로 쓴다(두 벌로 두면 갈라진다).

■ 규율 — 이 파일이 절대 하지 않는 것
  · **자동 매매 없음.** 알림만 보낸다. 주문 API는 코드 레벨에서 차단돼 있다(toss_snapshot 가드).
  · **룰을 바꾸지 않는다.** 발동은 "PM 판단·정훈 결정"의 입력일 뿐이다.
  · **중복 알림 금지.** 같은 알림을 하루에 한 번만 보낸다(state 파일). 폰이 상시라고
    같은 말을 반복하면 알림 자체가 무시된다 — 그러면 만든 의미가 없다.
  · **미발송을 숨기지 않는다.** 텔레그램 키가 없으면 notify.py가 exit 3을 내고,
    이 스크립트는 그걸 로그에 남긴다(8/22 "가드 없는 폴백은 침묵보다 나쁘다").

■ 사용
  price_watch.py --once                 # 1회 평가(스케줄러용)
  price_watch.py --loop 5               # 5분 간격 연속 감시(장중 수동 실행)
  price_watch.py --once --dry-run       # 발송 없이 판정만
  price_watch.py --status               # 오늘 발동 이력

상태: data/logs/price_watch_state.json (gitignore — data/logs/ 하위)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)

# ⚠️ portfolio.json은 scripts/ 가 아니라 그 **상위**(portfolio-desk/)에 있다.
#    triggers.py:53과 같은 경로를 써야 한다 — 첫 구현이 여기서 한 단계를 틀려
#    "감시 0건"을 조용히 출력했다(파일이 없으면 _load가 {}를 주므로 예외도 안 난다).
#    가드 없는 폴백은 침묵보다 나쁘다(8/22) — 아래 run_once가 0건이면 경고한다.
CFG = os.path.join(HERE, "..", "portfolio.json")
STATE_DIR = os.path.join(ROOT, "data", "logs")
STATE = os.path.join(STATE_DIR, "price_watch_state.json")

# 가격이 실제로 움직이는 시간대만 본다(KST). 그 밖엔 호출 자체를 아낀다.
#   미국 정규장 22:30~05:00(익일) — 서머타임은 ±1h 오차를 허용해 넉넉히 잡는다
#
# ★[9/3] 국내 거래시간이 **2026-09-14부터 바뀐다**(한국거래소 확정·다출처 [검증]):
#   舊  정규장 09:00~15:30 + 시간외단일가 16:00~18:00(10분 일괄체결·당일종가 ±10%)
#   新  프리마켓 07:00~07:50 + 정규장 09:00~15:30 + 애프터마켓 16:00~20:00
#       애프터마켓은 **정규장과 동일한 실시간 접속매매**(전일종가 ±30%·지정가만)
#   ⇒ 시행일로 갈라 자동 전환한다. 미리 켜면 9/13까지 안 열리는 시간에 헛돌고,
#     안 켜면 9/14부터 애프터마켓 4시간(16:00~20:00)이 통째로 감시 사각이 된다.
AFTER_MKT_REFORM = dt.date(2026, 9, 14)


def _calendar_window(now: dt.datetime):
    """토스 1차 출처로 오늘 장 운영시간을 읽는다 [9/4 배선].

    하드코딩은 **공휴일을 모른다** — 그게 이 함수 이전의 구조적 약점이었다
    (market_open_kst 주석에 "공휴일 미반영"이 약점으로 적혀 있었다).
    토스 `market-calendar`는 today/nextBusinessDay를 주므로 휴장일이 자동 처리되고,
    9/14 제도 변경도 API가 알아서 반영한다 — 우리가 날짜 분기를 유지할 필요가 없어진다.

    ⚠️ 실패하면 **조용히 넘어가지 않고 None을 반환**해 하드코딩 폴백으로 내려간다.
       그 사실은 호출부가 phase 문자열에 남긴다("추정") — 어느 근거로 판정했는지 보이게.
    ⚠️ `integrated` = KRX + NXT 통합이다. 9/4 실측: 오늘도 이미 08:00~20:00으로,
       "9/14부터 확장"이라는 우리 서술이 NXT를 빼먹은 것이었다.
    """
    try:
        cache = _load(os.path.join(ROOT, "data", "app", "toss_market.json"), {})
        day = ((cache.get("calendars") or {}).get("KR") or {}).get("today") or {}
        if day.get("date") != now.strftime("%Y-%m-%d"):
            return None                       # 캐시가 오늘 것이 아니면 못 믿는다
        seg = day.get("integrated") or {}
        spans = []
        for k, nm in (("preMarket", "KRX 프리"), ("regularMarket", "KRX 정규"),
                      ("afterMarket", "KRX 애프터")):
            v = seg.get(k)
            if not v:
                continue
            st, en = str(v.get("startTime"))[11:16], str(v.get("endTime"))[11:16]
            if len(st) == 5 and len(en) == 5:
                spans.append((int(st[:2]) * 60 + int(st[3:]), int(en[:2]) * 60 + int(en[3:]), nm))
        return spans or None
    except Exception:                                              # noqa: BLE001
        return None


def market_open_kst(now: dt.datetime) -> tuple[bool, str]:
    if now.weekday() >= 5:                      # 토·일 — 정훈 폰도 주말은 제외다
        return False, "주말"
    m = now.hour * 60 + now.minute
    # 1차 출처가 있으면 그걸 쓴다. 없을 때만 아래 하드코딩으로 내려간다.
    spans = _calendar_window(now)
    if spans:
        for st, en, nm in spans:
            if st <= m <= en:
                return True, nm
        if m >= 1350 or m <= 330:
            return True, "미국 정규장"
        return False, "장 마감"
    reformed = now.date() >= AFTER_MKT_REFORM
    if reformed and 420 <= m <= 470:
        return True, "KRX 프리마켓"
    if 540 <= m <= 930:
        return True, "KRX 정규장"
    if reformed:
        if 960 <= m <= 1200:
            return True, "KRX 애프터마켓"
    elif 960 <= m <= 1080:
        return True, "KRX 시간외단일가"
    if m >= 1350 or m <= 330:
        return True, "미국 정규장"
    return False, "장 마감"


def _load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return default


def _today():
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).strftime("%Y-%m-%d")


def _kst():
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)


def load_state() -> dict:
    """상태는 **두 층**이다 — 섞으면 안 된다.

    · `seen`  : 알림별 마지막 상태. **날짜가 바뀌어도 유지**한다.
                알림의 의미는 '지금 발동해 있다'가 아니라 **'방금 발동으로 넘어갔다'**이기 때문이다.
                이걸 매일 초기화하면 며칠째 발동 상태인 알림을 매일 아침 다시 쏜다 = 알림 피로.
                (첫 실행 실측: 5건이 전부 '신규'로 잡혔는데 실제론 며칠 전부터 발동 상태였다)
    · `fired` : 오늘 실제로 보낸 것. **날짜가 바뀌면 초기화**한다 = 하루 1회 스로틀.
    """
    st = _load(STATE, {})
    st.setdefault("seen", {})
    if st.get("date") != _today():
        st["date"] = _today()
        st["fired"] = {}                            # 스로틀만 초기화 · seen은 보존
    st.setdefault("fired", {})
    return st


def save_state(st: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def evaluate_all() -> list[dict]:
    """triggers.evaluate()를 그대로 쓴다 — 판정 로직을 복제하지 않는다.

    ⚡ 1회 실행에 한해 시세를 메모한다. 알림 21건이 고유 티커 13개를 쓰므로
       같은 값을 8번 더 받아오고 있었다(같은 순간이라 값도 동일하다).
       하루 80회 실행이면 1,680 → 1,040콜 — Yahoo 레이트리밋 여유를 벌어둔다.
    """
    import market_data as _md
    _memo = {}
    _orig = _md.fetch_quote

    def _cached(ticker, *a, **k):
        if ticker not in _memo:
            _memo[ticker] = _orig(ticker, *a, **k)
        return _memo[ticker]

    _md.fetch_quote = _cached
    try:
        return _evaluate_all_inner()
    finally:
        _md.fetch_quote = _orig          # 원복 — 다른 호출자에 새어나가지 않게


def _evaluate_all_inner() -> list[dict]:
    import triggers as _t
    import market_data as _md
    _t.fetch_quote = _md.fetch_quote     # triggers가 from-import한 참조도 교체
    evaluate = _t.evaluate
    cfg = _load(CFG, {})
    out = []
    for a in (cfg.get("alerts") or []):
        if a.get("cond") in ("event", "signal", "done"):
            continue                                # 가격 감시 대상이 아니다
        # 폐기된 알림은 원장에 기록으로 남지만 폰으로 보내면 안 된다.
        # (실측: 舊 2차 트랜치 8,000 · 舊 7,500 안전핀 등이 아직 alerts에 살아 있다)
        if str(a.get("id", "")).startswith(("⚪[폐기]", "⚪폐기", "[폐기]")):
            continue
        try:
            out.append(evaluate(a))
        except Exception as e:                                 # noqa: BLE001
            out.append({**a, "state": "error", "detail": f"{type(e).__name__}: {e}"})
    return out


def send(text: str, dry: bool) -> tuple[int, str]:
    if dry:
        return 0, "(dry-run)"
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "notify.py"), "--text", text],
                           capture_output=True, text=True, timeout=30)
        return r.returncode, (r.stdout or r.stderr or "").strip()[:200]
    except Exception as e:                                     # noqa: BLE001
        return 4, f"{type(e).__name__}: {e}"


def run_once(dry: bool = False, quiet: bool = False) -> int:
    now = _kst()
    is_open, phase = market_open_kst(now)
    st = load_state()
    rows = evaluate_all()
    if not rows:
        # 감시 대상 0건은 "알림이 없다"가 아니라 **설정을 못 읽었다**일 가능성이 높다.
        # 조용히 0을 찍으면 감시가 죽은 걸 아무도 모른다(첫 구현이 정확히 그랬다).
        print(f"⚠️ 감시 대상 0건 — portfolio.json alerts를 못 읽었을 수 있다 ({CFG})",
              file=sys.stderr)
        return 1
    fired = [r for r in rows if r.get("state") == "fired"]
    errs = [r for r in rows if r.get("state") == "error"]

    # **전이**만 신규로 본다: 직전에 fired가 아니었는데 지금 fired인 것.
    new = [r for r in fired
           if st["seen"].get(str(r.get("id"))) != "fired"
           and str(r.get("id")) not in st["fired"]]
    if not quiet:
        print(f"[{now:%H:%M}] {phase} · 감시 {len(rows)}건 · 발동 {len(fired)} · "
              f"신규 {len(new)}" + (f" · 오류 {len(errs)}" if errs else ""))
        for r in new:
            print(f"  🔔 {r.get('id')} — {str(r.get('detail'))[:90]}")
        # 오류는 조용히 넘기지 않는다. 평가 못 한 알림은 '발동 안 함'이 아니다.
        for r in errs:
            print(f"  ⚠️ 평가 실패: {r.get('id')} — {str(r.get('detail'))[:90]}")

    if new:
        lines = [f"🔔 트리거 {len(new)}건 발동 ({now:%m/%d %H:%M} · {phase})"]
        for r in new:
            px = r.get("price")
            lines.append(f"· {r.get('id')}" + (f"  현재 {px:,}" if isinstance(px, (int, float)) else ""))
            act = str(r.get("action") or "")[:110]
            if act:
                lines.append(f"   → {act}")
        lines.append("⚠️ 알림일 뿐 자동 집행 아님 — 룰 확인 후 정훈 결정.")
        # 정훈 9/4: "내가 할 일을 위로, 자세한 내용은 아래로".
        #   notify.compose()가 [할 일 → 트리거 → 상세] 순서로 조립한다.
        #   ⚠️ 조립이 실패해도 알림 자체는 나가야 한다 — 형식 때문에 신호를 잃지 않는다.
        try:
            sys.path.insert(0, HERE)
            import notify as _n
            body = _n.compose(chr(10).join(lines))
        except Exception:                                          # noqa: BLE001
            body = chr(10).join(lines)
        code, msg = send(body, dry)
        if not quiet:
            print(f"  발송: exit={code} {msg}")
        if code == 0:                       # 발송 성공한 것만 '보냈다'로 기록한다
            for r in new:
                st["fired"][str(r.get("id"))] = now.strftime("%H:%M")
        elif not quiet:
            print("  ⚠️ 미발송 — 다음 주기에 재시도한다(fired 기록 안 함)")
    # seen은 **발송 성공 여부와 무관하게** 매번 갱신한다 — 이건 '보냈나'가 아니라
    # '시장이 어떤 상태였나'의 기록이다. 둘을 한 필드로 합치면 미발송 시 전이를 잃는다.
    for r in rows:
        st["seen"][str(r.get("id"))] = r.get("state")
    save_state(st)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="장중 트리거 실시간 감시 + 폰 알림 (알림 전용·자동매매 없음)")
    ap.add_argument("--once", action="store_true", help="1회 평가(스케줄러용)")
    ap.add_argument("--loop", type=int, metavar="MIN", help="N분 간격 연속 감시")
    ap.add_argument("--status", action="store_true", help="오늘 발동 이력")
    ap.add_argument("--dry-run", action="store_true", help="발송 없이 판정만")
    ap.add_argument("--ignore-hours", action="store_true", help="장 시간 무시하고 평가")
    ap.add_argument("-q", "--quiet", action="store_true", help="신규 발동 없으면 침묵")
    ap.add_argument("--baseline", action="store_true",
                    help="현재 상태를 기준선으로 기록만(발송 없음) — 최초 도입 시 1회")
    a = ap.parse_args()

    if a.status:
        st = load_state()
        print(f"오늘({st.get('date')}) 발동·발송 {len(st.get('fired') or {})}건")
        for k, v in (st.get("fired") or {}).items():
            print(f"  {v}  {k}")
        return 0

    if a.baseline:
        st = load_state(); rows = evaluate_all()
        for r in rows:
            st["seen"][str(r.get("id"))] = r.get("state")
        save_state(st)
        f = sum(1 for r in rows if r.get("state") == "fired")
        print(f"기준선 기록 — 감시 {len(rows)}건(발동 상태 {f}건)은 이미 발동한 것으로 간주해 "
              f"알리지 않는다. 이후 **새로 넘어가는 것**만 폰으로 간다.")
        return 0

    if a.loop:
        print(f"연속 감시 시작 — {a.loop}분 간격 (Ctrl+C 종료)")
        while True:
            is_open, phase = market_open_kst(_kst())
            if is_open or a.ignore_hours:
                run_once(a.dry_run, a.quiet)
            elif not a.quiet:
                print(f"[{_kst():%H:%M}] {phase} — 건너뜀")
            time.sleep(max(1, a.loop) * 60)

    is_open, phase = market_open_kst(_kst())
    if not is_open and not a.ignore_hours:
        if not a.quiet:
            print(f"[{_kst():%H:%M}] {phase} — 감시 대상 시간 아님 (--ignore-hours로 강제)")
        return 0
    return run_once(a.dry_run, a.quiet)


if __name__ == "__main__":
    sys.exit(main())
