#!/usr/bin/env python3
"""missed_moves.py — 결정 후행회고: 안 산/안 판 결정의 반사실(counterfactual) 채점

배경: self-review(score_calls.py)는 **내가 실제로 내린 콜**(별점·목표가·매수존)이 맞았나만 채점한다.
그러나 실전 손익의 절반은 **하지 않은 행동**에서 난다 — "관망·보류·홀딩·추격 금지"라고 판단했는데
그 뒤 크게 오르거나(놓친 매수) 내린(놓친 매도/트림) 종목. 워치에만 두고 안 들어갔는데 급등한 종목.
이 **누락(omission)**은 지금 어떤 스크립트도 추적하지 않는다 → 이 스크립트가 그 사각을 채운다.

핵심 통찰(score_calls와 동일): data/app/stocks.json 의 git 히스토리 = 결정의 시계열.
**지금 카드의 신호(관망/홀딩/워치 등록)가 시작된 날**을 '결정 시점'으로 잡고(안 산다·안 판다 따로 — 10/14.
舊엔 종목 첫 등장일이었다), 그 이후 Yahoo 시세 경로에서
최고 상승(fwd_max)·최저 하락(fwd_min)을 뽑아 "그때 샀으면/팔았으면"을 정량화한다.

  python3 missed_moves.py                    # 놓친 매수·매도 후보 + 반복 패턴(콘솔 표)
  python3 missed_moves.py --min-move 20      # 임계값 조정(기본 15%)
  python3 missed_moves.py --since 2026-06-20 # 결정 시점 하한(그 이후 등록분만)
  python3 missed_moves.py --json             # 기계가독(에이전트가 검증 후 missed_moves.jsonl 기입)

의존성 없음(stdlib + score_calls.py 재사용). 시세는 Yahoo 무키 일봉(네트워크 필요).
FAIL 안 냄 — 회고·캘리브레이션 보조. 원장 기입·교훈 확정은 사람(에이전트) 판단(자동 변경 ❌).
※ 결과론 함정 경계: 표본·기간(horizon) 명시, 단기 노이즈(noise)와 진짜 미스(miss) 구분,
  '올바른 무행동(good_inaction)'도 함께 집계해 무행동이 운인지 실력인지 균형있게 본다.
"""
import argparse, json, os, re, subprocess, sys
from datetime import datetime, date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)

# score_calls의 검증된 프리미티브 재사용(DRY): git 타임머신 + Yahoo 시세 경로 + 가격 레벨 추출
from score_calls import (today_kst, series, close_on_or_after, path_from,
                         git_commits, stocks_at)

STOCKS_REL = "data/app/stocks.json"
DECISIONS_REL = "data/app/decisions.jsonl"
LEDGER_REL = "data/app/missed_moves.jsonl"
ETF = {"VOO"}

# ── 결정 시그널 사전 ──────────────────────────────────────────────────────
# 안 사는(매수 누락) 판단 vs 안 파는(매도 누락) 판단을 텍스트에서 뽑는다.
# ★[8/22 전면 수정] 8/22 감사에서 오미션 검출이 2건뿐이라 "no_sell 트랙이 비었다"고 진단했는데,
#   실제 원인은 **트랙 부재가 아니라 ①키워드 미스매치 ②분류 오류** 둘이었다.
#     ① 실제 표기는 "물타기 **영구**금지"·"추가매수 **영구**금지"·"신규매수 **금지**"인데
#        키워드는 "물타기 금지"·"신규매수 **안함**"이라 **한 건도 안 걸렸다**
#        (= 8/12 "쓰는 쪽과 읽는 쪽이 갈리면 데이터가 조용히 사라진다"의 재현).
#     ② **"물타기 금지"가 NO_SELL_KW에 들어 있었다** — 물타기(추가매수) 금지는 '안 판다'가
#        아니라 **'안 산다'**다. 분류가 반대로 박혀 no_buy 집계도 같이 오염됐다.
#   ⇒ 문자열 상수 대신 **정규식**으로 바꿔 표기 변형(영구·永久·공백 유무)을 흡수한다.
# ★[10/14] 같은 실패가 세 번째로 났다 — 10/13에 MU 카드를 "룰4 = 홀딩"에서 "첫 둔화 = 중립(보유 유지·증액 없음)"으로
#   바꾸자 (no_buy, no_sell)이 (None, '홀딩') → (None, None)이 됐다. '안 판다·안 늘린다'는 결정(d243)인데
#   이 사전에 그 표현이 없어서, MU가 더 빠져도 그 결정의 반사실 채점 행이 생기지 않을 뻔했다(검토에서 발견).
#   ⇒ "보유 유지"·"잔여 보유"·"보유(d210 …" 꼴(안 판다)을 넣고, 사전을 `--selftest`로 못박는다.
#   카드 문구를 새로 쓸 때는 이 사전에 걸리는지 `--selftest`의 문구 목록에 같이 넣을 것.
#   ("— 보유(d211). …" 꼴은 3차 검토에서 추가 — 현대차·ORCL이 같은 d210/d211 보유 결정인데 안 읽히고 있었다.)
# ★[10/14 결정일 귀속 수정] 舊 analyze()는 종목의 **첫 등장일**(= 3개월 창의 시작)에 **지금 카드의 신호**를 붙였다.
#   최근에 생긴 신호가 석 달 전 결정처럼 채점됐다 — "증액 없음"(안 늘린다)을 NO_BUY에 넣자 MU에
#   "관망 후 -25% 하락 = 안 사길 잘함"이 찍혔다(그 구간의 MU는 신규자금 3차 매수 대상이었다 — d51 7/27 ~ d158 8/29 오더 폐기.
#   체결은 없었다: trades.jsonl의 MU 매수는 5/18이 마지막).
#   ⇒ 결정일 = **지금 신호가 끊기지 않고 이어진 구간의 시작일**(`_advance` · 안 산다/안 판다 따로). 고친 뒤에 '증액 없음'을 넣었다.
#   수정 전후(같은 입력 · 임계 15%): 34행 → 28행(삭제 7 · 추가 1). 삭제 7행 중 문구 깜빡임 때문인 것은 없다 —
#     현대차 놓친매도(8/19~9/22는 470,000원 트림 지정가를 매일 등록 중 → d211 9/23 보유 · 그날부터 -10.9%)
#     NAVER 놓친매수(7/29 '조건부 add' → 8/7 보류 · 고점 8/5는 결정 전) · MSFT 놓친매수(매수존 '눌림' → 9/20 신규 확대 보류)
#     ORCL 놓친매수(매수존 '눌림' → 8/7 매수 후보에서 제외) · ANET 놓친매수(8/10까지 보유였는데 6/20부터 '워치미진입'으로 채점)
#     META 놓친매도(8/27 트림 체결 뒤 9/9 '잔여 홀드') · META 잘홀딩(9/23 전량 매도한 종목에 '안 팔길 잘함').
#
# ⚠️ **공백(깜빡임)을 커밋 수로 잇지 않는다** — 재 보니 실제 결정 변경과 문구 누락의 길이가 완전히 겹친다(10/14 실측 · 209커밋):
#   신호가 꺼졌다 다시 켜진 공백은 26개. 가장 짧은 실제 변경 = **2커밋**(현대차 9/22 트림 등록 → 9/23 d211 보유),
#   가장 긴 문구 누락 = **75커밋**(삼성전자 8/3~9/22 — '룰4 홀딩'은 그날 코멘트가 그 말을 할 때만 읽힌다).
#   어떤 N을 골라도 N≥2면 현대차의 d211이 8/27로 밀리고, N<75면 삼성전자가 안 이어진다
#   (공백을 안 이으면 삼성전자 '안 판다'의 시작일이 10/6으로 밀려 -18.7% 놓친매도 행이 사라진다 = 깜빡임이 지우는 유일한 행).
#   ⇒ 잇는 기준은 길이가 아니라 **입장 칸이 그대로인가**다: 신호가 꺼진 동안 그 신호의 칸(안 판다 = 트림 칸 · 안 산다 = 매수존 칸)이
#     한 글자도 안 바뀌었으면 결정을 다시 쓴 적이 없다 — 그날 코멘트가 그 말을 안 했을 뿐이다 → 같은 구간.
#     칸이 고쳐졌으면(다시 켜지는 날 포함) 새 결정 → 그날부터.
#     실측: 26개 중 5개를 잇고(7·12·13·22·75커밋 — 삼성전자 2 · NAVER · ORCL · META) 21개를 끊는다(2~157커밋).
#   남는 한계: ①결정일 = 카드가 커밋된 날(결정 다음 날일 수 있다 — d243 10/13 → 카드 10/14) ②결정일이 시세 창(3개월)보다 앞서면
#   ref는 창의 첫 종가다(`ref_date`로 드러낸다) ③칸은 그대로 두고 코멘트에만 적은 매도·매수 계획, 칸을 안 고친 채 난 체결은
#   구간을 못 끊는다(10/14 대조: 지금 켜진 42개 구간 안에 반대 방향 체결 0건 — trades.jsonl)
#   ④지금 켜져 있는 신호만 잰다 — 끝난 결정(관망하다 산 종목의 관망 구간)은 채점하지 않는다.
NO_BUY_RE = re.compile(
    r"관망|보류|추격\s*금지|진입\s*금지|"
    r"(물타기|추가\s*매수|추가매수|신규\s*매수|신규매수|신규\s*자금)\s*(영구)?\s*(금지|안함|제외)|"
    r"봉인|매수\s*후보\s*(에서\s*제외|아님)|신규자금\s*영구제외|증액\s*(없음|금지|종료)")
NO_SELL_RE = re.compile(
    r"홀딩|홀드|인내|장기\s*보유|보유\s*유지|잔여\s*보유|보유\s*\(d\d+|"
    r"패닉셀\s*금지|손절선\s*(없음|영구\s*폐기)|정리후보|"
    r"트림\s*(실익\s*없음|보류)|잔여\s*(절반\s*)?홀딩")
# ★[10/14] 트림 칸이 '보류'·'관망'으로 시작하면 **매도 보류**(안 판다)이기도 하다. 舊엔 칸을 안 가리고 '안 산다'로만 읽어서,
#   삼성전자 6/20~7/29 카드(트림 = '보류')의 '안 판다'가 안 읽혔고 그 구간이 7/30(코멘트의 '룰4 홀딩')에서야 시작됐다.
#   ⚠️ '안 산다'로 읽는 舊 동작은 **그대로 둔다**(더하기만 한다) — 떼어 봤더니 현대차의 '안 산다' 구간이 끊겼다:
#   7/29 카드가 '관망'을 매수존 칸에서 트림 칸으로 옮겨 적었을 뿐인데 시작일이 6/20 → 8/2로 밀렸다.
TRIM_HOLD_RE = re.compile(r"\s*(트림\s*)?(보류|관망)")
# 하위호환(다른 스크립트가 import할 수 있음)
NO_BUY_KW = ("관망", "보류", "추격 금지", "추격금지", "진입금지", "진입 금지")
NO_SELL_KW = ("홀딩", "인내", "손절선 없음", "정리후보")

# ── 클러스터(반복 편향 집계용) ────────────────────────────────────────────
CLUSTER = {
    "메모리·AI하드웨어": {"005930.KS", "000660.KS", "MU", "AVGO", "ANET",
                          "240810.KQ", "095610.KQ", "STM", "005070.KS", "TSM", "AMAT", "CDNS"},
    "국내수급민감 대형": {"005930.KS", "000660.KS", "005380.KS", "035420.KS"},
    "급등주·모멘텀":     {"454910.KS", "TSLA", "SPCX", "IONQ", "PLTR", "IBM"},
    "전력·피지컬AI":     {"066570.KS", "GEV", "034020.KS", "011070.KS",
                          "042660.KS", "096770.KS", "012450.KS", "010140.KS", "329180.KS",
                          "ISRG"},
    "빅테크·플랫폼":     {"META", "MSFT", "AAPL", "GOOGL", "ORCL", "NAVER",
                          "035420.KS", "TMUS", "033780.KS"}  # TMUS = 10/12 d239 워치 제외(사후 추적용 매핑 유지),
}
def clusters_of(ticker):
    tags = [name for name, mem in CLUSTER.items() if ticker in mem]
    return tags or ["기타"]


def sig_from(v, is_watch):
    """종목 스냅샷 → 결정 시그널. (no_buy, no_sell, label, rule_blocked)"""
    bz = str(v.get("buy_zone") or "")
    trim = str(v.get("trim") or "")
    comment = str(v.get("comment") or "")
    text = " ".join([bz, trim, comment])
    rule_blocked = ("진입금지" in text) or ("진입 금지" in text) or ("상장 전" in text)
    if is_watch:
        # 워치 = 미보유 후보. 룰차단(상장 전 등)만 아니면 '안 산' 결정으로 본다.
        label = "워치미진입(룰차단)" if rule_blocked else "워치미진입"
        return (True, False, label, rule_blocked)
    no_buy = bool(NO_BUY_RE.search(text))
    no_sell = bool(NO_SELL_RE.search(text) or TRIM_HOLD_RE.match(trim))
    # 라벨 = 대표 시그널(표시용)
    label = (bz.strip()[:14] or trim.strip()[:14] or "—")
    return (no_buy, no_sell, label, rule_blocked)


def _ensure_full_history():
    """★[8/22] shallow clone이면 이 도구는 **조용히 잘린 범위만** 본다.

    8/22 실측: 세션 클론이 shallow라 커밋 61개(8/14~)뿐이었고 stocks.json 이력이 11개였다
    → 오미션 검출이 **2건**. `git fetch --unshallow` 후 658커밋·이력 133개가 되자
    **놓친 매수 7건·놓친 매도 2건**이 드러났다(PLTR +51%·ANET +21%·META +21% 등).
    즉 "오미션이 없다"는 결론 자체가 **클론 깊이의 산물**이었다.
    ⇒ 사람 기억(validate WARN)에 맡기지 않고 도구가 직접 확인·복구한다.

    → 복구에 실패해 **잘린 이력으로 채점하게 됐으면** 그 이유(문자열), 아니면 None. 호출자가 결과에 싣는다.
    ★[10/14 4차 검토] fetch의 종료코드를 안 봤다 — origin 접속 실패·인증 거부(종료코드 128)여도 '히스토리를 복구한다'만
      찍고 잘린 이력으로 채점했다(8/22와 같은 결론이 조용히 다시 나온다). 종료코드와 복구 뒤 상태를 둘 다 본다."""
    def is_shallow():
        r = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30, cwd=ROOT)
        return (r.stdout or "").strip() == "true"
    try:
        if not is_shallow():
            return None
    except (OSError, subprocess.SubprocessError):
        # ★[10/14] 여기가 `except Exception`이라 NameError(subprocess 미임포트 · REPO 미정의)가 8/22부터 삼켜졌다 —
        #   shallow clone 복구가 한 번도 돈 적이 없다. git 실행 실패만 넘긴다.
        return None
    print("[INFO] shallow clone 감지 — 히스토리를 복구한다(git fetch --unshallow). "
          "이걸 안 하면 잘린 범위만 보고 '오미션 없음'이라는 틀린 결론이 나온다.",
          file=sys.stderr)
    why = None
    try:
        f = subprocess.run(["git", "fetch", "--unshallow", "origin"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600, cwd=ROOT)
        if f.returncode != 0 or is_shallow():
            last = ((f.stderr or "").strip().splitlines() or ["(출력 없음)"])[-1][:100]
            why = f"종료코드 {f.returncode} · {last}"
    except (OSError, subprocess.SubprocessError) as ex:
        why = f"{type(ex).__name__}: {str(ex)[:60]}"
    if why:
        print(f"[WARN] unshallow 실패({why}) — 결과가 잘린 범위 기준임을 감안할 것.", file=sys.stderr)
    return why


def _advance(rec, dt, is_watch, v):
    """한 커밋의 카드로 신호별 구간 상태를 전진시킨다 — rec["nb"]·rec["ns"] = {since, field, on} 또는 None.

    since = 그 신호가 끊기지 않고 이어진 구간의 시작일 · field = 그 신호의 입장 칸(안 산다 = 매수존 · 안 판다 = 트림) · on = 지금 켜져 있나.
    · 신호별로 따로 센다 — '안 산다'와 '안 판다'는 시작일이 다르다(MU: 안 판다 = 6/25 잔여 홀딩부터, 안 늘린다 = 그 문구가
      카드에 들어간 날부터). 튜플 하나로 묶으면 한쪽이 바뀐 날 다른 쪽도 끊긴다.
    · 켜진 채로 문구·칸만 바뀌면 시작일은 그대로다(홀딩 → 보유 유지).
    · 버킷 전환(워치↔보유)은 실제 매수·매도 체결이다 → 그 전의 무행동 결정은 거기서 끝났다. 둘 다 새로 센다.
    · 꺼진 동안 입장 칸이 그대로면 다시 켜질 때 같은 구간으로 잇고, 칸이 고쳐졌으면 새 결정이다(근거 = 파일 상단 주석)."""
    fields = {"nb": str(v.get("buy_zone") or ""), "ns": str(v.get("trim") or "")}
    on = dict(zip(("nb", "ns"), sig_from(v, is_watch)[:2]))
    if rec.get("last_is_watch", is_watch) != is_watch:
        rec["nb"] = rec["ns"] = None
    for key, field in fields.items():
        st = rec.get(key)
        if st and not st["on"] and st["field"] != field:
            st = None                              # 꺼진 사이(다시 켜지는 날 포함) 입장 칸이 고쳐졌다 = 이전 결정은 끝났다
        if on[key]:
            st = {"since": st["since"] if st else dt, "field": field, "on": True}
        elif st:
            st = {**st, "on": False}               # 칸은 그대로인데 그날 코멘트가 그 말을 안 했다 — 구간을 열어 둔다
        rec[key] = st


def build_history(since):
    """git 히스토리 순회 → 종목별 {first_date, first_val, last_val, is_watch, last_is_watch, nb_since, ns_since, gone}.

    nb_since·ns_since = **지금 카드의** 안 산다/안 판다 신호가 시작된 날(지금 꺼져 있으면 None).
    gone = 최신 스냅샷에 없는 종목(워치 탈락 · 보유였으면 전량 매도)."""
    hist, latest = {}, None
    for h, dt in reversed(git_commits()):        # 과거→현재
        if since and dt < since:
            continue
        sj = stocks_at(h)
        if not sj:
            continue
        latest = h
        buckets = [("stocks", False), ("watchlist", True)]
        for key, is_watch in buckets:
            for tk, v in (sj.get(key) or {}).items():
                if tk in ETF:
                    continue
                rec = hist.setdefault(tk, {"first_date": dt, "is_watch": is_watch,
                                            "first_val": v})
                _advance(rec, dt, is_watch, v)
                # 워치→보유 승격 시 최종 상태는 보유로 갱신
                rec["last_val"] = v
                rec["last_is_watch"] = is_watch
                rec["last_commit"] = h
    for rec in hist.values():
        for key in ("nb", "ns"):
            st = rec.pop(key, None)
            rec[key + "_since"] = st["since"] if st and st["on"] else None
        rec["gone"] = rec.pop("last_commit") != latest
    return hist


def _window(ser, d0, today):
    """결정일 d0 이후의 시세 경로 → (ref, ref_date, fwd_max, fwd_min, fwd_now, peak_date, trough_date, horizon_d). 시세가 없으면 None."""
    ref = close_on_or_after(ser, d0)
    path_days = [k for k in sorted(ser) if not k.startswith("__") and k >= d0]
    path = [ser[k] for k in path_days]
    if not ref or not path:
        return None
    pmax, pmin = max(path), min(path)
    return (ref, path_days[0], (pmax - ref) / ref * 100, (pmin - ref) / ref * 100, (path[-1] - ref) / ref * 100,
            path_days[path.index(pmax)], path_days[path.index(pmin)],
            (today - datetime.fromisoformat(d0).date()).days)


def analyze(min_move, since):
    hist = build_history(since)
    today = today_kst()  # [7/13] KST 실측 (score_calls 공용 헬퍼)
    rows, net_err = [], []
    for tk, rec in hist.items():
        ser = series(tk)
        if "__error__" in ser:
            net_err.append(tk); continue
        is_watch = rec.get("last_is_watch", rec["is_watch"])
        no_buy, no_sell, label, blocked = sig_from(rec.get("last_val", rec["first_val"]), is_watch)
        if rec.get("gone") and not is_watch:
            # 보유였다가 최신 스냅샷에서 사라졌다 = 전량 매도. '안 판다'는 거기서 끝났다 — 舊엔 마지막 카드의 '홀드'를
            # 오늘까지 이어 붙여, 9/23에 판 META에 '홀딩 유지 후 현재 +15% = 안 팔길 잘함'을 찍었다.
            no_sell = False

        def cand(d0):
            # ★[10/14] 결정일 = 종목 첫 등장일이 아니라 **그 신호가 시작된 날**. ref·경로·기간·집행가능성 전부 그날 기준.
            w = _window(ser, d0, today)
            if not w:
                return None
            ref, ref_date, fwd_max, fwd_min, fwd_now, peak_date, trough_date, horizon = w
            # ★[8/14] 집행가능성 판정 — 놓친매수에만 적용(매도는 현금 제약과 무관하다)
            blk, blk_why = executability(_SNAPS, d0, tk, ref)
            return ({
                "ticker": tk, "decision_at": d0, "horizon_d": horizon,
                "ref_price": round(ref, 2), "ref_date": ref_date, "signal": label, "is_watch": is_watch,
                "rule_blocked": blocked, "fwd_max": round(fwd_max, 1),
                "fwd_min": round(fwd_min, 1), "fwd_now": round(fwd_now, 1),
                "peak_date": peak_date, "trough_date": trough_date,
                "clusters": clusters_of(tk),
                "blocked_exec": blk, "blocked_why": blk_why,
            }, fwd_max, fwd_min, fwd_now)

        # 분류: 안 샀는데 급등 / 안 팔았는데 급락 / 올바른 무행동(결과론 함정 견제).
        # 안 산다와 안 판다는 시작일이 다를 수 있어 **창을 따로** 잰다.
        c = cand(rec.get("nb_since") or rec["first_date"]) if no_buy else None
        if c:
            base, fwd_max, fwd_min, _ = c
            d0, blk, blk_why = base["decision_at"], base["blocked_exec"], base["blocked_why"]
            if fwd_max >= min_move:
                rows.append({**base,
                             "type": "집행불가" if blk else "놓친매수",
                             "severity": round(fwd_max, 1),
                             "note": (f"{d0} {label} → {base['peak_date']} +{fwd_max:.0f}% 고점"
                                      + (f" · ⛔{blk_why}" if blk else ""))})
            elif fwd_min <= -min_move:
                rows.append({**base, "type": "잘참음", "severity": round(abs(fwd_min), 1),
                             "note": f"{d0} 관망 후 {fwd_min:.0f}% 하락 = 안 사길 잘함"})
        c = cand(rec.get("ns_since") or rec["first_date"]) if no_sell else None
        if c:
            base, _, fwd_min, fwd_now = c
            d0 = base["decision_at"]
            if fwd_min <= -min_move:
                rows.append({**base, "type": "놓친매도", "severity": round(abs(fwd_min), 1),
                             "note": f"{d0} {label} → {base['trough_date']} {fwd_min:.0f}% 저점"})
            if fwd_now >= min_move:
                rows.append({**base, "type": "잘홀딩", "severity": round(fwd_now, 1),
                             "note": f"{d0} 홀딩 유지 후 현재 +{fwd_now:.0f}% = 안 팔길 잘함"})
    return rows, sorted(set(net_err))


def match_rejected(ticker):
    """decisions.jsonl에서 이 종목이 언급된 '기각된 대안'을 찾아 병기(반사실 힌트)."""
    p = os.path.join(ROOT, DECISIONS_REL)
    if not os.path.exists(p):
        return []
    out = []
    base = ticker.split(".")[0]
    for ln in open(p, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        blob = " ".join(str(d.get(k, "")) for k in ("topic", "decision", "rejected"))
        if base and base in blob and d.get("rejected"):
            out.append({"date": d.get("date"), "rejected": d.get("rejected")})
    return out


# ─────────────────────────────────────────────────────────────────────
# ★[8/14 신설·정훈 승인] 집행가능성 게이트 — "놓쳤다"와 "못 샀다"를 가른다.
#
# 배경(9회차 캘리브레이션): 8/14 미스 4건(삼성전기 +22%·원익IPS +22%·LG이노텍 +18%·
# SK하이닉스 +16%)이 전부 8/8 워치미진입으로 잡혔는데, 그 기간 내내
# **사다리 허용액 0원 + 하드플로어 발동**이라 진입이 물리적으로 불가능했다.
# 이 원장의 반사실은 "샀다면 어땠나"인데 **살 수 없었으면 반사실 자체가 성립하지 않는다.**
# 제약을 판단 실패로 세면 오미션 지표가 부풀고, 거기서 잘못된 교훈이 나온다.
#
# 판정 2단계(둘 중 하나라도 걸리면 blocked):
#   ① 그날 룰1 허용액이 0원(rule_log.jsonl `allowed_krw` / `halted`)
#   ② 국내 종목인데 **1주 가격 > 그날 가용현금** (토스 국내 소수점 미지원)
# 원장이 그날짜를 못 덮으면 **판정 보류(None)** — 없는 근거로 miss를 지우지 않는다.
_RULE_LOG = os.path.join(ROOT, "data", "app", "rule_log.jsonl")


def _rule_snapshots():
    path = _RULE_LOG or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "..", "..", "data", "app", "rule_log.jsonl")
    out = {}
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    d = json.loads(ln)
                except Exception:
                    continue
                if d.get("date"):
                    out[d["date"]] = d
    except Exception:
        return {}
    return out


def executability(snaps, decision_date, ticker, ref_price):
    """(blocked: bool|None, reason: str) — None = 원장 미커버로 판정 보류."""
    if not snaps:
        return None, "원장 없음"
    days = sorted(snaps)
    prior = [d for d in days if d <= decision_date]
    if not prior:
        return None, "원장이 결정일을 못 덮음"
    snap = snaps[prior[-1]]
    allowed = snap.get("allowed_krw")
    if snap.get("halted") or (allowed is not None and allowed <= 0):
        return True, f"룰1 허용액 0원({prior[-1]} 기준" + (" ·하드플로어" if snap.get("halted") else "") + ")"
    cash = snap.get("cash")
    if allowed is not None and str(ticker).endswith((".KS", ".KQ")) and ref_price:
        if ref_price > allowed:
            return True, (f"국내 1주 {ref_price:,.0f}원 > 그날 허용액 {allowed:,.0f}원"
                          f"{'' if cash is None else f' (가용현금 {cash:,.0f}원)'} · 소수점 불가")
    return False, "집행 가능했음"


_SNAPS = _rule_snapshots()


def report(rows, net_err, min_move):
    print("\n" + "=" * 68)
    print(f"  결정 후행회고 — missed_moves.py  (임계 ±{min_move}%)")
    print("=" * 68)
    if not rows:
        print("\n임계 초과 미스무브 없음(또는 채점 성숙 콜 부족). 원장은 계속 누적됨.")
        if net_err:
            print(f"시세 조회 실패: {net_err}")
        return

    order = {"놓친매수": 0, "놓친매도": 1, "집행불가": 2, "잘참음": 3, "잘홀딩": 4}
    for typ in ("놓친매수", "놓친매도", "집행불가", "잘참음", "잘홀딩"):
        sub = sorted([r for r in rows if r["type"] == typ],
                     key=lambda r: -r["severity"])
        if not sub:
            continue
        head = {"놓친매수": "🔺 놓친 매수 (안 샀는데 급등 — '그때 살걸')",
                "집행불가": "⛔ 집행 불가였음 (급등했으나 살 수 없었다 — miss 아님·반사실 미성립)",
                "놓친매도": "🔻 놓친 매도/트림 (안 팔았는데 급락 — '그때 팔걸')",
                "잘참음": "✅ 올바른 무행동 — 관망 후 하락(안 사길 잘함)",
                "잘홀딩": "✅ 올바른 무행동 — 홀딩 후 상승(안 팔길 잘함)"}[typ]
        print(f"\n{head}")
        print(f"  {'종목':<12}{'결정':<9}{'기간':>5}{'최고%':>8}{'최저%':>8}{'현재%':>8}  근거")
        for r in sub:
            print(f"  {r['ticker']:<12}{r['signal'][:8]:<9}{r['horizon_d']:>4}d"
                  f"{r['fwd_max']:>+8.0f}{r['fwd_min']:>+8.0f}{r['fwd_now']:>+8.0f}  {r['note']}")

    # ── 반복 패턴·편향 집계(클러스터별 미스 카운트) ──────────────────────
    print("\n— 반복 패턴·편향 (클러스터별 미스 집계) —")
    miss = [r for r in rows if r["type"] in ("놓친매수", "놓친매도")]
    ccount = {}
    for r in miss:
        for c in r["clusters"]:
            ccount.setdefault(c, {"놓친매수": 0, "놓친매도": 0})
            ccount[c][r["type"]] += 1
    for c, d in sorted(ccount.items(), key=lambda x: -(x[1]["놓친매수"] + x[1]["놓친매도"])):
        print(f"  {c:<18} 놓친매수 {d['놓친매수']} · 놓친매도 {d['놓친매도']}")

    # 기각된 대안 병기(반사실 힌트)
    # ★[9/26 R3] 舊 구조는 종목별로 모은 줄을 **평평하게 이어붙인 뒤 [:12]로 잘라서**,
    #   매칭이 많은 한 종목이 12줄을 전부 먹고 나머지 종목의 반사실을 통째로 가렸다.
    #   9/26 실측: 놓친매수 10종목(PLTR +70%·096770 +64%·MSFT +38% …)이 잡혔는데
    #   출력 12줄이 **전부 META**였다 — 가장 크게 놓친 종목들의 '그때 기각한 대안'을
    #   한 줄도 못 봤다. 반사실 재검토가 이 블록의 존재 이유인데 그게 안 보이면 블록이 헛돈다.
    #   ⇒ 종목별로 최신 기각부터 담고 **라운드로빈**으로 섞어 모든 종목이 최소 1줄을 받게 한다.
    REJ_MAX = 12
    per_tk = {}
    for r in miss:
        tk = r["ticker"]
        if tk in per_tk:
            continue
        seen, bucket = set(), []
        for rj in match_rejected(tk):
            if rj["date"] in seen:
                continue
            seen.add(rj["date"])
            bucket.append(rj)
        bucket.sort(key=lambda x: str(x.get("date") or ""), reverse=True)  # 최신 기각 먼저
        if bucket:
            per_tk[tk] = bucket
    lines = []
    depth = 0
    while per_tk and len(lines) < REJ_MAX:
        progressed = False
        for tk in list(per_tk):
            if depth < len(per_tk[tk]) and len(lines) < REJ_MAX:
                rj = per_tk[tk][depth]
                lines.append(f"  {tk} · {rj['date']} 기각: {rj['rejected'][:60]}")
                progressed = True
        if not progressed:
            break
        depth += 1
    if lines:
        total = sum(len(v) for v in per_tk.values())
        print("\n— 그때 기각한 대안(decisions.jsonl) — 반사실로 재검토 —")
        for l in lines:
            print(l)
        if total > len(lines):
            print(f"  … 종목 {len(per_tk)}개 · 기각 {total}건 중 {len(lines)}건 표시"
                  f"(종목별 최신부터 라운드로빈)")

    if net_err:
        print(f"\n  시세 조회 실패(회고 제외): {net_err}")
    print("\n※ 결과론 함정 경계 — 표본·기간 명시, noise vs miss 구분. 자동 변경 없음(교정은 사람 판단).")
    print("※ 검증 후 missed_moves.jsonl 기입 + hindsight_log.md 회고 블록 prepend(self-review Step 6).\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-move", type=float, default=15.0, help="미스 임계 %% (기본 15)")
    ap.add_argument("--since", type=str, default=None, help="결정 시점 하한 YYYY-MM-DD")
    ap.add_argument("--json", action="store_true", help="기계가독 출력")
    ap.add_argument("--selftest", action="store_true", help="결정 시그널 사전 자가검증(오프라인 · git·시세 안 봄)")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    truncated = _ensure_full_history()
    rows, net_err = analyze(a.min_move, a.since)
    if a.json:
        print(json.dumps({"min_move": a.min_move, "since": a.since,
                          "candidates": rows, "net_err": net_err, "history_truncated": truncated},
                         ensure_ascii=False, indent=1))
    else:
        if truncated:
            print(f"⚠️ 이력이 잘려 있다(shallow clone · 복구 실패: {truncated}) — 아래 결과는 잘린 범위 기준이다. "
                  "'오미션 없음'으로 읽지 말 것.")
        report(rows, net_err, a.min_move)


def selftest() -> int:
    """결정 시그널 사전이 실제 카드 문구를 읽는가. 쓰는 쪽(카드)과 읽는 쪽(이 사전)이 갈리면 결정이 조용히 사라진다."""
    fails = []

    def ok(name, cond):
        if not cond:
            fails.append(name)
        print(f"  {'✅' if cond else '❌'} {name}")

    def sig(buy_zone="", trim="", comment=""):
        nb, ns, _, _ = sig_from({"buy_zone": buy_zone, "trim": trim, "comment": comment}, False)
        return nb, ns

    # 실제 카드에서 가져온 문구들
    ok("d243 MU 카드(첫 둔화 = 중립 · 보유 유지·증액 없음) = 안 판다 + 안 늘린다",
       sig(buy_zone="—", trim="잔여 보유(d210 9/23: 가격 < 목표 밴드 하단 · 마진 첫 둔화 = 중립(d243 10/13))",
           comment="룰4 = **첫 둔화 = 중립(보유 유지·증액 없음 · d243 10/13 정훈 승인)** — 하락 전환 아님") == (True, True))
    ok("'— 보유(d211). …' · '— 보유(d210 9/23: …)' 꼴도 안 판다(현대차·ORCL 카드)",
       sig(trim="— 보유(d211). 3Q 영업마진 ≥5.43% 보유 / 미만이면 반등 지정가 정리 … 등록 없음") == (False, True)
       and sig(trim="— 보유(d210 9/23: 가격 < 목표 밴드 하단)") == (False, True))
    ok("'보유'만으로는 안 걸린다(보유 12종목 · 보유 비중 · 장기보유는 별도 패턴)",
       sig(comment="보유 12종목 · 보유 비중 16.3%") == (False, False))
    ok("'보유 유지'만 있어도 안 판다", sig(comment="중립 — 보유 유지") == (False, True))
    ok("'잔여 보유'도 안 판다", sig(trim="잔여 보유") == (False, True))
    ok("'증액 없음'·'증액 금지'·'증액 종료' = 안 늘린다(결정일 귀속을 고친 뒤 넣었다 · '배당 증액 공식화'는 아니다)",
       all(sig(comment=c) == (True, False) for c in ("증액 없음", "증액 금지", "증액  종료"))
       and sig(comment="배당 증액 공식화 여부") == (False, False))
    ok("띄어 쓴 변형도 읽는다('트림 실익 없음' · '매수 후보에서 제외' — ORCL 8/7 카드가 8커밋 동안 안 읽혔다)",
       sig(buy_zone="**제외** — 매수 우선순위에 넣지 않는다", trim="—(트림 실익 없음·비중 0.5%) · 매수 후보에서 제외") == (True, True)
       and sig(buy_zone="제외(매수후보 아님)", trim="—(트림 실익없음·비중 0.5%)") == (True, True))
    ok("트림 칸의 '보류'·'관망' = 매도 보류이기도 하다(삼성전자 6/20 카드) · 매수존 칸의 '보류'는 안 산다뿐",
       sig(buy_zone="295,000~305,000원 (눌림 대기)", trim="보류")[1] is True
       and sig(buy_zone="—", trim="관망(모멘텀)") == (True, True) and sig(buy_zone="보류", trim="—") == (True, False)
       and sig(trim="$308 지정가 1주(미회복 시 7/30 보류)")[1] is False)
    ok("舊 표기는 그대로 읽는다(홀딩 · 물타기 영구금지 · 추가매수 영구금지 · 신규매수 금지 · 관망)",
       sig(comment="룰4 = 홀딩") == (False, True) and sig(buy_zone="물타기 영구금지") == (True, False)
       and sig(buy_zone="추가매수 영구금지") == (True, False) and sig(buy_zone="신규매수 금지") == (True, False)
       and sig(buy_zone="관망") == (True, False))
    ok("'물타기 금지'는 안 사는 것이지 안 파는 것이 아니다(8/22 분류 오류 재발 방지)",
       sig(buy_zone="물타기 금지") == (True, False))
    ok("결정 문구가 없는 카드는 시그널 없음(가격대·숫자만)",
       sig(buy_zone="$880~900 눌림", trim="$1,400 일부 익절", comment="FQ4 매출 $54.23B") == (False, False))
    ok("워치 = 미보유 후보는 문구와 무관하게 '안 산' 결정",
       sig_from({"buy_zone": "$180~190"}, True)[:2] == (True, False))

    # ── 결정일 귀속 — 합성 이력(하루 한 커밋 · d1~d8)으로 build_history()·analyze()를 끝까지 태운다 ──
    D = [None] + [f"2026-01-{i:02d}" for i in range(1, 9)]

    def card(bz="", trim="", comment=""):
        return {"buy_zone": bz, "trim": trim, "comment": comment}

    plan = {   # 종목 → (그날 i의 버킷 's'보유/'w'워치, 카드) 또는 None(스냅샷에 없음)
        "CHG": lambda i: ("s", card("눌림", "$100 지정가 매도 접수" if i < 3 else "— 보유(d900 1/3: 가격 < 밴드 하단)")),
        "LBL": lambda i: ("s", card(trim="홀딩" if i < 4 else "보유 유지")),
        "PRO": lambda i: ("w", card("$90~95 눌림")) if i < 4 else ("s", card("—(추가매수 금지)", "홀딩")),
        "DEM": lambda i: ("s", card(trim="홀딩")) if i < 4 else ("w", card("재진입 조건부")),
        "SIL": lambda i: ("s", card("눌림" if i < 5 else "적립만", "—", "" if 3 <= i <= 5 else "룰4 홀딩")),
        "CUT": lambda i: ("s", card(trim="홀드 — 재검토" if i < 4 else "470,000원 지정가 매도 접수" if i == 4 else "— 보유(d211)")),
        "SEP": lambda i: ("s", card(trim="잔여 절반 홀딩", comment="보유 유지·증액 없음" if i == 8 else "")),
        "OUT": lambda i: ("s", card("제외(신규자금 영구제외)", "잔여 홀드")) if i <= 5 else None,
        "WCH": lambda i: ("w", card("$50 눌림")) if i <= 4 else None,
        "END": lambda i: ("s", card(trim="—", comment="룰4 홀딩" if i <= 6 else "")),
        "RET": lambda i: ("w" if 3 <= i <= 4 else "s", card(trim="홀딩")),       # 매도 → 워치 → 재매수, 카드 문구는 그대로
    }
    px = {     # d1~d8 종가
        "CHG": [100, 70, 70, 71, 72, 72, 72, 72],          # 보유 결정(d3) **전에** -30%
        "LBL": [100, 80, 80, 80, 80, 80, 80, 80],
        "PRO": [100, 120, 150, 150, 152, 153, 154, 155],   # 워치 때 +50% → d4 매수 → 그 뒤 '추가매수 금지'
        "DEM": [100, 100, 100, 100, 110, 130, 130, 130],
        "SIL": [100, 100, 80, 80, 80, 80, 80, 80],
        "CUT": [100, 100, 100, 100, 100, 80, 80, 80],
        "SEP": [100, 100, 78, 78, 79, 80, 80, 80],         # '증액 없음'(d8) **전에** -22%
        "OUT": [100, 100, 100, 100, 100, 110, 120, 130],   # d5 뒤 전량 매도 → 그 뒤 +30%
        "WCH": [100, 100, 100, 100, 110, 120, 130, 130],
        "END": [100, 80, 80, 80, 80, 80, 80, 80],
        "RET": [100, 100, 100, 100, 100, 100, 100, 100],
    }

    def fake_stocks_at(h):
        sj = {"stocks": {}, "watchlist": {}}
        for tk, f in plan.items():
            got = f(int(h))
            if got:
                sj["stocks" if got[0] == "s" else "watchlist"][tk] = got[1]
        return sj

    g = globals()
    keep = {k: g[k] for k in ("git_commits", "stocks_at", "series", "today_kst", "_SNAPS")}
    try:
        g.update(git_commits=lambda: [(str(i), D[i]) for i in range(8, 0, -1)],       # 최신순(원본 규약)
                 stocks_at=fake_stocks_at,
                 series=lambda tk, rng_param="3mo": dict(zip(D[1:], px[tk])),
                 today_kst=lambda: date(2026, 1, 20), _SNAPS={})
        hist = build_history(None)
        rows, _ = analyze(15.0, None)
    finally:
        g.update(keep)
    since = {tk: (r["nb_since"], r["ns_since"]) for tk, r in hist.items()}
    at = {(r["ticker"], r["type"]): r["decision_at"] for r in rows}
    ok("① 신호가 중간에 바뀐 종목의 결정일 = 바뀐 날(매도 주문 → d3 보유 결정) — 그 전의 -30%는 '놓친매도'가 아니다",
       since["CHG"] == (None, D[3]) and not [k for k in at if k[0] == "CHG"])
    ok("② 라벨만 바뀌면(홀딩 → 보유 유지) 결정일은 그대로다",
       since["LBL"] == (None, D[1]) and at.get(("LBL", "놓친매도")) == D[1])
    ok("③ 워치 → 보유 승격 = 매수 체결 → '안 산다'·'안 판다' 둘 다 승격일부터(워치 때 +50%를 '놓친매수'로 안 센다)",
       since["PRO"] == (D[4], D[4]) and not [k for k in at if k[0] == "PRO"])
    ok("③' 보유 → 워치(매도 후 재편입) = '워치미진입'은 매도일부터 센다(ANET을 6/20부터 미진입으로 채점하던 것)",
       since["DEM"] == (D[4], None) and at.get(("DEM", "놓친매수")) == D[4])
    ok("③\" 팔았다가 다시 산 종목의 '안 판다'는 재매수일부터다 — 트림 칸 문구가 같아도 버킷 전환을 건너 잇지 않는다",
       since["RET"] == (None, D[5]))
    ok("④ 트림 칸은 그대로인데 코멘트만 조용했던 공백(3커밋)은 같은 구간으로 잇는다 — 매수존 칸이 바뀐 것은 상관없다(삼성전자)",
       since["SIL"] == (None, D[1]) and at.get(("SIL", "놓친매도")) == D[1])
    ok("⑤ 꺼진 사이 트림 칸이 고쳐졌으면 1커밋 공백도 잇지 않는다(현대차 9/22 매도 등록 → 9/23 d211 보유)",
       since["CUT"] == (None, D[5]) and at.get(("CUT", "놓친매도")) == D[5]
       and [r["ref_date"] for r in rows if r["ticker"] == "CUT"] == [D[5]])
    ok("⑥ 안 산다·안 판다는 시작일이 따로다 — '증액 없음'이 d8에 생겨도 d1부터의 -22%에 '안 사길 잘함'을 찍지 않는다(MU)",
       since["SEP"] == (D[8], D[1]) and ("SEP", "잘참음") not in at and at.get(("SEP", "놓친매도")) == D[1])
    ok("⑦ 전량 매도된 보유 종목엔 '안 팔길 잘함'·'놓친매도'를 찍지 않는다(META) — '안 산다'는 계속 잰다",
       hist["OUT"]["gone"] and ("OUT", "잘홀딩") not in at and ("OUT", "놓친매도") not in at
       and at.get(("OUT", "놓친매수")) == D[1])
    ok("⑧ 워치에서 빠진 종목은 계속 '워치미진입'으로 잰다(사후 추적)",
       hist["WCH"]["gone"] and at.get(("WCH", "놓친매수")) == D[1])
    ok("⑨ 지금 카드에 신호가 없으면 시작일도 없다(열어 둔 구간이 결정일로 새지 않는다)",
       since["END"] == (None, None) and not [k for k in at if k[0] == "END"])

    calls = []
    keep_run = subprocess.run

    state = {"shallow": ["true", "false"], "fetch_rc": 0}     # rev-parse가 차례로 내는 답 · fetch 종료코드

    def fake_git(cmd, **k):
        calls.append((cmd, k.get("cwd")))
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=state["shallow"].pop(0) + "\n", stderr="")
        return subprocess.CompletedProcess(cmd, state["fetch_rc"], stdout="",
                                           stderr="" if not state["fetch_rc"] else "fatal: 'origin' does not appear to be a git repository")
    import contextlib
    import io
    try:
        subprocess.run = fake_git
        with contextlib.redirect_stderr(io.StringIO()) as e_ok:
            r_ok = _ensure_full_history()
        n_ok = [c[0][1] for c in calls]
        state.update(shallow=["true", "true"], fetch_rc=128)
        with contextlib.redirect_stderr(io.StringIO()) as e_fail:
            r_fail = _ensure_full_history()
        state.update(shallow=["true", "true"], fetch_rc=0)       # fetch는 0인데 여전히 shallow(부분 복구)
        with contextlib.redirect_stderr(io.StringIO()):
            r_still = _ensure_full_history()
        state.update(shallow=["false"], fetch_rc=0)
        del calls[:]
        r_full = _ensure_full_history()
        n_full = [c[0][1] for c in calls]
    finally:
        subprocess.run = keep_run
    ok("shallow clone이면 복구(git fetch --unshallow)를 실제로 부른다 — 레포 루트에서(8/22부터 NameError로 안 돌았다)",
       n_ok == ["rev-parse", "fetch", "rev-parse"] and r_ok is None and "WARN" not in e_ok.getvalue())
    ok("복구 실패(fetch 종료코드 128)는 WARN + 이유를 돌려준다 — '복구한다'만 찍고 넘어가지 않는다",
       r_fail and "128" in r_fail and "WARN" in e_fail.getvalue())
    ok("fetch가 0이어도 여전히 shallow면 실패로 본다", bool(r_still))
    ok("전체 이력이면 아무것도 하지 않는다(fetch 미호출)", r_full is None and n_full == ["rev-parse"])

    print(f"\n{'✅ SELFTEST PASS' if not fails else '❌ SELFTEST FAIL: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    main()
