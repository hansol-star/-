#!/usr/bin/env python3
"""score_calls.py — 콜 캘리브레이션·후행 백테스트 (reflection 루프 정량화)

배경(외부 레퍼런스 차용): FinMem·TradingAgents 등 SOTA 트레이딩 에이전트의 성능 차별점은
'reflection(과거 판단 회고) + memory'를 **자동 루프**로 돈다는 점이다. 정훈 세팅의 self-review는
훌륭하지만 산문·수동이었다 → 이 스크립트가 그 회고를 **기계가독 원장 + 정량 채점**으로 바꾼다.

핵심 통찰: data/app/stocks.json 의 git 히스토리 = 구조화된 콜(별점·스코어·목표가·매수존)의
시계열이다. 즉 별도 로깅 인프라 없이 **git이 이미 콜 원장**이다 → 백필로 즉시 후행채점 가능.

  python3 score_calls.py --backfill   # git 히스토리 → data/app/calls_log.jsonl 재생성
  python3 score_calls.py --append     # 현재 stocks.json 콜 1스냅샷을 원장에 추가(보고서마다)
  python3 score_calls.py              # 원장 채점 + 별점 캘리브레이션 요약(편향·역전 플래그)

의존성 없음(stdlib + market_data.py). 채점은 Yahoo 무키 시세 경로로 한다(네트워크 필요).
FAIL을 내지 않는다 — 어디까지나 회고·캘리브레이션 보조(자동 변경 ❌, 교정은 사람이 판단).

[7/4 정훈 승인 — 벤치마크 알파] 절대수익률만 보면 시장 전체 폭락(7/2 서킷 등)이 모든 콜에
일괄 벌점을 줘 '콜 실력 vs 레짐'이 안 갈라진다(6/29·7/4 캘리브레이션 2회 연속 오염 실증).
→ TradingAgents의 'vs SPY 알파' 후행채점을 차용해 콜별 **벤치마크 대비 초과수익(알파)**을
병기한다: 국내(.KS/.KQ) = 코스피(^KS11), 미국 = VOO 대비. ETF(VOO 자신)는 알파 집계 제외.
"""
import argparse, json, os, re, subprocess, sys, urllib.request, urllib.error
from datetime import datetime, date, timedelta, timezone

KST = timezone(timedelta(hours=9))


def today_kst() -> date:
    """[7/13] 날짜는 항상 KST 실측 — UTC 컨테이너에서 00~09시 KST에 하루 밀리는 것 방지."""
    return datetime.now(KST).date()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)
try:
    from market_data import YAHOO_CHART, UA          # 시세 소스 재사용(DRY)
except Exception:
    YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

STOCKS_REL = "data/app/stocks.json"
LEDGER_REL = "data/app/calls_log.jsonl"
ETF = {"VOO"}

# ── 별점 → 내재 상승확률 (proper scoring rule용) ──────────────────────────
# 근거(외부): LLM 예측의 1순위 실패 = 과신(overconfidence). ForecastBench·forecasting
# 연구가 권장하는 proper scoring rule(Brier)로 "별점이 표현하는 확신"을 실제 적중률과
# 정렬한다. 별점=확신도이므로 ⭐5=강한 상승확신 … ⭐1=강한 하락확신으로 단조 매핑.
# 보수적으로 0.85~0.15(끝을 0/1로 안 박음 = 과신 자체를 점수가 벌함).
# ★[8/22 재보정 · 정훈 승인] n=851 실측 캘리브레이션에 맞춰 확신 표현을 교정.
#   舊 {5:0.85, 4:0.68, 3:0.50, 2:0.32, 1:0.15} 대비 실측 상승률:
#     ⭐5 56%(과신 -29%p) · ⭐4 56%(-12%p) · ⭐3 42%(-8%p) · ⭐2 **62%(과소확신 +30%p)** · ⭐1 17%(정합)
#   ⚠️ 이건 **확신 표현의 보정이지 채점 기준 변경이 아니다** — 별점 자체는 안 바뀐다.
#   ⚠️ 표본이 코스피 -24% 붕괴장에 몰려 있어 ⭐2 상승분에 '낙폭과대 반등'이 섞였을 수 있다.
#      알파 기준 Brier(0.271)도 무정보(0.250)보다 나쁘다는 게 레짐만은 아니라는 방증이나,
#      정상장 표본이 쌓이면 재보정할 것(R3 주간 캘리브레이션에서 추적).
# ★[8/29 단조 복원 · 정훈 승인] ⭐2를 0.50 → 0.38.
#   8/22 재보정은 "⭐2 실측 상승 62% = 과소확신"을 근거로 0.32→0.50으로 올렸는데,
#   8/29 star_validate ③횡단면에서 그 62%의 정체가 **NAVER 단일 종목(+22.2%·n33)의
#   낙폭과대 반등**임이 드러났다(⭐2 버킷 4종목 중 하나가 버킷을 지배). 근거가 오염 표본이다.
#   결과로 ⭐2(0.50) > ⭐3(0.45)의 **비단조**가 생겼고, 순서 척도 위의 Brier가 무의미해졌다.
#   ⇒ 최소 개입으로 **단조성만 복원**한다(⭐1 0.17 < ⭐2 0.38 < ⭐3 0.45).
#   ⚠️ 이건 실측 재보정이 **아니다** — 舊 0.32로 되돌리지도 않았다(그 값도 근거가 약하다).
#      실측 재보정은 star_validate의 CI가 분리될 만큼 표본이 쌓인 뒤에 한다(현재 0/3 지평).
#   가드 = validate_report.check_star_prob_monotonic (비단조면 FAIL).
STAR_PROB = {5: 0.65, 4: 0.60, 3: 0.45, 2: 0.38, 1: 0.17}

# ── 콜 문자열에서 가격 레벨 추출 ("480,000~530,000원", "$220~250", "295,000원 (눌림)") ──
_UNIT = {"만": 10_000, "억": 100_000_000, "조": 1_000_000_000_000,
         "k": 1_000, "K": 1_000}


def levels(s):
    """콜 문자열에서 가격 레벨 추출.

    ⚠️ [8/8 버그수정] 舊 구현은 **한글 단위(만·억)를 무시**했다. 국내 목표가는
    "24.6만~46만"처럼 쓰는데 이걸 24.6·46으로 읽으면 실제 주가(231,000원)와
    4자리가 어긋난다 → `target_hit = max(path) >= tg[0]`가 **국내주에서 항상 참**이
    되어 '목표가 하단 터치' 지표가 통째로 오염됐다(실측: 보정 전 68% → 보정 후 재계산).
    매수존(`buy_zone`)도 같은 표기를 쓰므로 동일 영향.
    ⇒ 숫자 뒤에 붙은 만/억/조를 곱해준다.
    """
    if not isinstance(s, str):
        return []
    s = s.replace("–", "-")

    # ⚠️ 범위 표기에서 단위가 **뒤에만** 붙는 게 우리 표기 관행이다:
    #    "295~305k" = 295,000~305,000 · "13~15만" = 130,000~150,000
    #    앞 숫자에 단위를 안 붙이면 (295, 305000)처럼 4자리 어긋난 범위가 나온다.
    #    ⇒ 범위 패턴을 먼저 찾아 **양쪽 모두**에 단위를 적용해 치환한다.
    unit_re = r"(만|억|조|[kK](?![a-zA-Z]))"
    def _expand(m):
        a, b, u = m.group(1), m.group(2), m.group(3)
        mul = _UNIT[u]
        try:
            return f"{float(a.replace(',', '')) * mul:.0f}~{float(b.replace(',', '')) * mul:.0f}"
        except ValueError:
            return m.group(0)
    s = re.sub(r"(\d[\d,]*\.?\d*)\s*[~-]\s*(\d[\d,]*\.?\d*)\s*" + unit_re, _expand, s)

    out = []
    for n, unit in re.findall(r"(\d[\d,]*\.?\d*)\s*" + unit_re + r"?", s):
        try:
            v = float(n.replace(",", ""))
        except ValueError:
            continue
        if unit:
            v *= _UNIT[unit]
        if v >= 1:                       # 연도·각주 0 등 잡음 최소화
            out.append(v)
    return out

def rng(s):
    """(low, high) 또는 None. 단일값이면 (v, v).

    ⚠️ [8/8 버그수정] 舊 구현은 `levels(s)[:2]`로 **앞 숫자 2개를 그냥 집었다.**
    우리 목표가 표기엔 괄호 주석·퍼센트·집계수가 섞여 있어 이게 가격으로 오인됐다:
      "$302.83(+42.9%)"        → (42.9, 302.83)   ← 42.9를 가격으로
      "$321.66 (컨센 41명) …"   → (41.0, 321.66)   ← 애널 수를 가격으로
      "$1,507.38 ⚠️stale(6월 …)" → (6.0, 1507.38)   ← '6월'을 가격으로
    이 상태로 목표가를 채점하면 내재여력이 -76.9%처럼 나온다(실측).
    ⇒ ①괄호 주석 제거 ②퍼센트·집계 단위 토큰 제거 ③**맨 앞의 가격 토큰(범위면 범위)**만 취한다.
    """
    if not isinstance(s, str):
        return None
    t = s.replace("–", "-")
    t = re.sub(r"\([^)]*\)", " ", t)                       # ① 괄호 주석
    t = re.sub(r"[+-]?\d[\d,]*\.?\d*\s*%", " ", t)          # ② 퍼센트
    t = re.sub(r"\d[\d,]*\.?\d*\s*(명|사|개|월|일|년|분기|위)", " ", t)   # ② 집계·날짜 단위

    # ③ **맨 앞의** 가격 토큰 하나. 범위(~)는 선택적으로 뒤에 붙는다.
    #    범위를 따로 먼저 찾으면 안 된다 — "$321.66 … 개별 하우스 $245~400 분산"처럼
    #    뒤쪽 참고 레인지를 본 목표가로 오인한다(실측). 위치가 앞선 것이 본 목표가다.
    unit = r"(?:만|억|조|[kK](?![a-zA-Z]))"
    num = r"\d[\d,]*\.?\d*\s*" + unit + "?"
    m = re.search(rf"({num})(?:\s*[~-]\s*({num}))?", t)
    if not m:
        return None
    lv = levels(m.group(0))
    if not lv:
        return None
    if len(lv) >= 2:
        return (min(lv[:2]), max(lv[:2]))
    return (lv[0], lv[0])

# ── Yahoo 일봉 종가 시계열 ───────────────────────────────────────────────
_SERIES = {}
def series(symbol, rng_param="3mo"):
    if symbol in _SERIES:
        return _SERIES[symbol]
    url = YAHOO_CHART.format(symbol=urllib.request.quote(symbol)) + f"?interval=1d&range={rng_param}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    out = {}
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
        res = d["chart"]["result"][0]
        ts = res["timestamp"]
        cl = res["indicators"]["quote"][0]["close"]
        for t, c in zip(ts, cl):
            if c is not None:
                out[datetime.utcfromtimestamp(t).date().isoformat()] = float(c)
    except Exception as e:
        out = {"__error__": str(e)}
    _SERIES[symbol] = out
    return out

def close_on_or_after(ser, d):
    days = sorted(k for k in ser if not k.startswith("__"))
    for k in days:
        if k >= d:
            return ser[k]
    return None

def bench_symbol(ticker):
    """콜 티커 → 벤치마크 심볼. 국내(.KS/.KQ)=코스피, 미국=VOO. ETF 자신은 알파 제외(None)."""
    if ticker in ETF:
        return None
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        return "^KS11"
    return "VOO"

def bench_fwd(ticker, d):
    """콜과 같은 창(d→최신)의 벤치마크 전진수익률(%). 조회 불가 시 None."""
    sym = bench_symbol(ticker)
    if not sym:
        return None
    ser = series(sym)
    if "__error__" in ser:
        return None
    b0 = close_on_or_after(ser, d)
    bpath = path_from(ser, d)
    if not b0 or not bpath:
        return None
    return (bpath[-1] - b0) / b0 * 100

def path_from(ser, d):
    return [ser[k] for k in sorted(ser) if not k.startswith("__") and k >= d]

# ── 원장 백필: git 히스토리의 stocks.json 각 커밋 = 한 시점의 콜 묶음 ─────────
def git_commits():
    out = subprocess.run(
        ["git", "-C", ROOT, "log", "--format=%H %ad", "--date=short", "--", STOCKS_REL],
        capture_output=True, text=True)
    rows = []
    for ln in out.stdout.splitlines():
        h, _, dt = ln.partition(" ")
        if h:
            rows.append((h, dt.strip()))
    return rows  # 최신순

def stocks_at(commit):
    out = subprocess.run(["git", "-C", ROOT, "show", f"{commit}:{STOCKS_REL}"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except Exception:
        return None

def call_rows(stocks_json, dt):
    rows = []
    for tk, v in (stocks_json.get("stocks") or {}).items():
        rows.append({
            "date": dt, "ticker": tk,
            "stars": v.get("stars"), "score": v.get("score"),
            "target": v.get("target"), "buy_zone": v.get("buy_zone"),
            "source_report": stocks_json.get("source_report"),
        })
    return rows

def is_shallow():
    """[8/6 신설] 얕은 클론 감지. 웹/원격 세션은 얕게 클론돼 git 히스토리가
    며칠치뿐일 수 있다 — 그 상태로 백필하면 원장이 그 며칠로 잘린다."""
    out = subprocess.run(["git", "-C", ROOT, "rev-parse", "--is-shallow-repository"],
                         capture_output=True, text=True)
    return out.stdout.strip() == "true"


def backfill(force=False):
    """git 히스토리에서 콜 원장을 복원한다.

    ⚠️ [8/6 사고예방] 舊 구현은 결과를 **"w"로 통째 덮어썼다**. 원격 세션은 얕은
    클론(oldest 3일)이라 R3 주말루틴의 `--backfill`이 원장을 3일치로 잘라먹는
    구조였다(실측: 135개 중 75개 = 7/28~8/1 소실 예정). 두 겹으로 막는다:
      ① 얕은 클론이면 중단하고 `git fetch --unshallow`를 안내(--force로 강행 가능)
      ② 덮어쓰기가 아니라 **기존 원장과 병합** — 복원분이 기존을 이기되,
         히스토리에 없는 과거 날짜는 보존한다(백필은 복원이지 삭제가 아니다).
    """
    if is_shallow() and not force:
        print("🔴 백필 중단 — 얕은 클론(shallow)이라 git 히스토리가 잘려 있다.\n"
              "   이대로 백필하면 원장이 그 며칠치로 잘린다.\n"
              "   먼저: git fetch --unshallow origin   (그 뒤 --backfill 재실행)\n"
              "   그래도 강행하려면 --force")
        return 1

    seen, rows = set(), []
    for h, dt in reversed(git_commits()):          # 과거→현재
        sj = stocks_at(h)
        if not sj:
            continue
        for r in call_rows(sj, dt):
            key = (r["date"], r["ticker"])          # 같은 날 여러 커밋 → 그날 마지막만
            if key in seen:
                rows = [x for x in rows if (x["date"], x["ticker"]) != key]
            seen.add(key)
            rows.append(r)

    # ② 병합: 복원분에 없는 기존 (날짜,종목)은 살린다.
    lp = os.path.join(ROOT, LEDGER_REL)
    kept = []
    if os.path.exists(lp):
        for ln in open(lp, encoding="utf-8"):
            if not ln.strip():
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if (r.get("date"), r.get("ticker")) not in seen:
                kept.append(r)
    merged = sorted(rows + kept, key=lambda r: (r.get("date") or "", r.get("ticker") or ""))
    with open(lp, "w", encoding="utf-8") as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    days = len({r["date"] for r in merged})
    print(f"✅ 백필 완료: {len(merged)}개 콜 / {days}일 → {LEDGER_REL} "
          f"(복원 {len(rows)} + 히스토리 밖 보존 {len(kept)}, {len(git_commits())} 커밋)")
    return 0

def append_today():
    p = os.path.join(ROOT, STOCKS_REL)
    sj = json.load(open(p, encoding="utf-8"))
    # as_of는 서술 문장일 수 있음 → source_report 파일명의 날짜를 우선, 없으면 오늘.
    m = re.search(r"(\d{4}-\d{2}-\d{2})", str(sj.get("source_report", "")))
    if not m:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(sj.get("as_of", "")))
    dt = m.group(1) if m else today_kst().isoformat()
    lp = os.path.join(ROOT, LEDGER_REL)
    existing = []
    if os.path.exists(lp):
        existing = [json.loads(l) for l in open(lp, encoding="utf-8") if l.strip()]
    existing = [r for r in existing if r.get("date") != dt]   # 같은 날 갱신 시 교체
    existing += call_rows(sj, dt)
    with open(lp, "w", encoding="utf-8") as f:
        for r in sorted(existing, key=lambda r: (r["date"], r["ticker"])):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"✅ {dt} 콜 {len(sj.get('stocks',{}))}종목 원장 반영 → {LEDGER_REL}")

# ── 채점 ────────────────────────────────────────────────────────────────
def score(min_age=1):
    lp = os.path.join(ROOT, LEDGER_REL)
    if not os.path.exists(lp):
        print("원장 없음 — 먼저 --backfill 또는 --append"); return
    calls = [json.loads(l) for l in open(lp, encoding="utf-8") if l.strip()]
    today = today_kst()
    graded, net_err = [], []
    for c in calls:
        try:
            cdt = datetime.fromisoformat(c["date"]).date()
        except Exception:
            continue
        age = (today - cdt).days
        if age < min_age:
            continue
        ser = series(c["ticker"])
        if "__error__" in ser:
            net_err.append(c["ticker"]); continue
        p0 = close_on_or_after(ser, c["date"])
        path = path_from(ser, c["date"])
        if not p0 or not path:
            continue
        pnow = path[-1]
        fwd = (pnow - p0) / p0 * 100
        bz = rng(c.get("buy_zone")); tg = rng(c.get("target"))
        buy_touched = (min(path) <= bz[1]) if bz else None
        target_hit = (max(path) >= tg[0]) if tg else None
        st = c.get("stars")
        # 별점 방향 적중: ⭐4-5=상승 기대, ⭐1-2=하락/약세 기대, ⭐3=중립(제외)
        dir_ok = None
        if isinstance(st, int):
            if st >= 4:   dir_ok = fwd > 0
            elif st <= 2: dir_ok = fwd < 0
        # 벤치마크 알파 [7/4]: 같은 창의 코스피/VOO 수익률 차감 → 레짐과 콜 실력 분리
        bfwd = bench_fwd(c["ticker"], c["date"])
        alpha = (fwd - bfwd) if bfwd is not None else None
        alpha_ok = None
        if isinstance(st, int) and alpha is not None:
            if st >= 4:   alpha_ok = alpha > 0
            elif st <= 2: alpha_ok = alpha < 0
        graded.append({**c, "age": age, "fwd": fwd, "alpha": alpha, "alpha_ok": alpha_ok,
                       "buy_touched": buy_touched, "target_hit": target_hit, "dir_ok": dir_ok})

    print("\n" + "=" * 60)
    print("  콜 캘리브레이션 — score_calls.py (reflection 정량화)")
    print("=" * 60)
    if not graded:
        print(f"\n채점할 성숙 콜 없음(나이 ≥ {min_age}일). 원장은 계속 누적됨.")
        if net_err: print(f"시세 조회 실패: {sorted(set(net_err))}")
        return

    # 별점 버킷별 평균 전진수익률 + 방향 적중률
    print(f"\n채점 콜 {len(graded)}개 (나이 ≥ {min_age}일, 최신 시세 경로 기준)")
    print("알파 = 같은 창 벤치마크(국내 ^KS11 / 미국 VOO) 대비 초과수익 — 레짐과 콜 실력 분리 [7/4]\n")
    print(f"{'별점':<6}{'콜수':>5}{'평균전진%':>11}{'평균알파%':>11}{'방향적중':>12}{'알파적중':>12}")
    by = {}
    for g in graded:
        by.setdefault(g.get("stars"), []).append(g)
    for st in sorted([k for k in by if isinstance(k, int)], reverse=True):
        rows = by[st]
        avg = sum(r["fwd"] for r in rows) / len(rows)
        al = [r["alpha"] for r in rows if r["alpha"] is not None]
        avg_a = f"{sum(al)/len(al):>+10.2f}%" if al else f"{'—':>11}"
        dirs = [r["dir_ok"] for r in rows if r["dir_ok"] is not None]
        hit = f"{sum(dirs)}/{len(dirs)}" if dirs else "—(중립)"
        ahits = [r["alpha_ok"] for r in rows if r["alpha_ok"] is not None]
        ahit = f"{sum(ahits)}/{len(ahits)}" if ahits else "—(중립)"
        print(f"⭐{st:<5}{len(rows):>5}{avg:>10.2f}%{avg_a}{hit:>12}{ahit:>12}")

    bz = [g for g in graded if g["buy_touched"] is not None]
    if bz:
        touched = sum(1 for g in bz if g["buy_touched"])
        print(f"\n매수존 진입(눌림 도달): {touched}/{len(bz)}  ({touched/len(bz)*100:.0f}%)")
    tg = [g for g in graded if g["target_hit"] is not None]
    if tg:
        hit = sum(1 for g in tg if g["target_hit"])
        print(f"목표가 하단 터치:        {hit}/{len(tg)}  ({hit/len(tg)*100:.0f}%)")

    # ── 유효표본 경고 (★8/29 신설 — 이 블록 없이는 아래 숫자가 반드시 오독된다) ──
    # 이 원장은 stocks.json 스냅샷 백필이라 **매 보고서마다 전 종목이 1행씩 복제**된다.
    # 즉 "n=949 콜"의 실체는 (종목 수) × (보고서 수)이고, 독립 판단은 **별점이 바뀐 횟수**뿐이다.
    # 8/29에 PM이 이 구분을 놓치고 아래 Brier를 그대로 인용해 "별점은 동전던지기"라고
    # 단정했다(8/12 '분모를 의심하라'의 재발). 그래서 숫자보다 먼저 분모를 찍는다.
    _seq = {}
    for g in sorted(graded, key=lambda r: r.get("date") or ""):
        _seq.setdefault(g["ticker"], []).append(g.get("stars"))
    _changes = sum(sum(1 for a, b in zip(v, v[1:]) if a != b) for v in _seq.values())
    _flat = [t for t, v in _seq.items() if len(set(v)) == 1]
    print("\n— ⚠️ 유효표본 (아래 통계를 읽기 전에) —")
    print(f"  스냅샷 {len(graded)}행 = 종목 {len(_seq)}개 × 보고서 {len({g.get('date') for g in graded})}일")
    print(f"  독립 판단 ≈ {len(_seq)} 초기 + {_changes} 변경 = **{len(_seq) + _changes}개**"
          f"  (10주 내내 불변 {len(_flat)}종목)")
    print("  ⇒ 버킷 평균·Brier의 유효 n은 **콜 수가 아니라 종목 수**다. 한 종목의 운명이")
    print("     수십 번 투표한다 → 이 출력으로 별점 기준을 판정하지 말 것.")
    print("     정본 = star_validate.py (종목 클러스터 보정·고정지평·부트스트랩 CI).")

    # 편향 플래그(self-review가 찾던 것 — 자동 탐지)
    print("\n— 편향 점검 —")
    means = {st: sum(r["fwd"] for r in by[st]) / len(by[st])
             for st in by if isinstance(st, int)}
    if 5 in means and 3 in means and means[5] < means[3]:
        print(f"  ⚠️ 별점 역전: ⭐5 평균({means[5]:+.2f}%) < ⭐3({means[3]:+.2f}%) — 채점기준 재점검 후보")
    if 5 in means and 4 in means and means[5] < means[4]:
        print(f"  ⚠️ ⭐5 평균({means[5]:+.2f}%) < ⭐4({means[4]:+.2f}%) — 최상위 확신 콜 과신 여부 점검")
    # 알파 기준 역전 — 절대수익 역전이 레짐 탓인지 실력 탓인지 판별 [7/4]
    a_means = {}
    for st in by:
        if isinstance(st, int):
            al = [r["alpha"] for r in by[st] if r["alpha"] is not None]
            if al:
                a_means[st] = sum(al) / len(al)
    if 5 in a_means and 3 in a_means:
        if a_means[5] < a_means[3]:
            print(f"  ⚠️ 알파 기준으로도 역전: ⭐5 알파({a_means[5]:+.2f}%) < ⭐3({a_means[3]:+.2f}%) — 레짐 아닌 채점 문제 신호")
        else:
            print(f"  ✅ 알파 기준 순서 정상: ⭐5 알파({a_means[5]:+.2f}%) ≥ ⭐3({a_means[3]:+.2f}%) — 절대수익 역전은 레짐(시장 전체 하락) 소산")
    star_dist = {st: len(by[st]) for st in sorted(by) if isinstance(st, int)}
    # 콜 수만 찍으면 ⭐5 223건이 4종목의 복제라는 사실이 안 보인다 → 고유 종목 수 병기.
    star_uniq = {st: len({r["ticker"] for r in by[st]}) for st in sorted(by) if isinstance(st, int)}
    print(f"  별점 분포(콜 수): {star_dist}")
    print(f"  └ 고유 종목 수  : {star_uniq}   ← 이쪽이 유효 n")
    if net_err:
        print(f"  시세 조회 실패(채점 제외): {sorted(set(net_err))}")

    # ── proper scoring(Brier) + 버킷별 캘리브레이션 갭 ────────────────────
    # outcome = 실제 상승(1)/하락(0), p = 별점 내재확률. Brier=(p-outcome)^2 평균.
    # 0.25 = 무정보(항상 0.5) 기준선 — 이보다 낮아야 별점에 정보가 있다는 뜻.
    scored = [g for g in graded if isinstance(g.get("stars"), int)
              and g["stars"] in STAR_PROB and g.get("fwd") is not None]
    print("\n— 캘리브레이션(Brier proper score) —")
    if scored:
        brier = sum((STAR_PROB[g["stars"]] - (1.0 if g["fwd"] > 0 else 0.0)) ** 2
                    for g in scored) / len(scored)
        base = sum((0.5 - (1.0 if g["fwd"] > 0 else 0.0)) ** 2
                   for g in scored) / len(scored)
        verdict = "정보있음(무정보 대비 우위)" if brier < base else "무정보 이하(과신 의심)"
        print(f"  Brier {brier:.3f}  vs  무정보(0.5고정) {base:.3f}  → {verdict}"
              f"  (낮을수록 좋음·n={len(scored)})")
        print(f"  {'별점':<5}{'표현확신':>9}{'실제상승률':>12}{'갭':>8}{'판정':>9}")
        for st in sorted({g["stars"] for g in scored}, reverse=True):
            rows = [g for g in scored if g["stars"] == st]
            realized = sum(1 for g in rows if g["fwd"] > 0) / len(rows)
            p, gap = STAR_PROB[st], None
            gap = realized - p
            tag = "과신" if (st >= 4 and gap < -0.15) else (
                  "과소확신" if (st <= 2 and gap > 0.15) else "정합")
            print(f"  ⭐{st:<4}{p*100:>8.0f}%{realized*100:>11.0f}%{gap*100:>+7.0f}%{tag:>9}")
        a_scored = [g for g in scored if g.get("alpha") is not None]
        if a_scored:
            brier_a = sum((STAR_PROB[g["stars"]] - (1.0 if g["alpha"] > 0 else 0.0)) ** 2
                          for g in a_scored) / len(a_scored)
            print(f"  Brier(알파 기준·outcome=벤치마크 초과) {brier_a:.3f}  (n={len(a_scored)})"
                  f" — 절대 Brier와의 차이가 레짐 오염의 크기")
        print("  ※ 표본 작을 때 갭은 노이즈 — 누적 추세로 해석. 매핑(STAR_PROB) 고정·교정은 사람이.")
    else:
        print("  채점 가능한 별점 콜 없음.")

    print("\n※ 자동 변경 없음 — 캘리브레이션 참고용. 교정은 self-review에서 사람이 판단.")
    print("※ 데이터가 짧을수록(콜 나이 적음) 노이즈 큼 — 누적될수록 신뢰도↑.\n")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backfill", action="store_true", help="git 히스토리에서 원장 복원(기존과 병합)")
    ap.add_argument("--force", action="store_true", help="얕은 클론이어도 백필 강행(원장 잘림 위험)")
    ap.add_argument("--append", action="store_true", help="현재 stocks.json 콜을 원장에 추가")
    ap.add_argument("--min-age", type=int, default=1, help="채점 최소 보유일(기본 1)")
    a = ap.parse_args()
    if a.backfill:
        # [8/6] 얕은 클론이면 백필만 건너뛰고 **채점은 계속한다.**
        # R2/R3 루틴 프롬프트는 http_api 소유라 에이전트가 못 고친다 → 이 코드가
        # 유일한 방어선이다. 여기서 종료해버리면 원장은 지키지만 R3가 스코어카드를
        # 통째로 못 내므로, 기존 원장 그대로 채점까지 가는 게 맞다.
        backfill(force=a.force)
    if a.append:
        append_today()
    if not a.backfill and not a.append:
        score(a.min_age)
    else:
        score(a.min_age)

if __name__ == "__main__":
    main()
