#!/usr/bin/env python3
"""
validate_report.py — 보고서 '완료의 정의' 게이트 (하네스 엔지니어링: 검증을 명령어로)

커밋·main 머지 전에 한 줄로 돌려 산출물이 '진짜 완성'인지 기계로 검사한다.
빌더(PM)가 눈으로 자가채점하던 완성도 점검을 독립 검사기로 분리한 것 —
풀표 누락·컬럼 빠짐·별점↔스코어 어긋남·정본 stale을 사람 대신 기계가 잡는다.
(만든 역할 ≠ 검사 역할. AI가 '다 됐다' 선언하기 전의 답안지.)

  python3 .claude/skills/portfolio-desk/scripts/validate_report.py
  python3 .claude/skills/portfolio-desk/scripts/validate_report.py --report docs/reports/report_v26_2026-06-22.md

FAIL(❌, exit 1) = 반드시 고치고 커밋.  WARN(⚠️, exit 0) = 눈으로 확인.
의존성 없음(stdlib). 정본 = data/app/{stocks,flows,tasks}.json · CLAUDE.md · docs/reports/.
"""
import argparse, datetime as dt, json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# 보유 15종목 정본 (티커 → 보고서 본문에서 찾을 별칭들). 변동 시 여기 + master.md 동시 갱신. [7/7 TSLA 전량 매도 → 제외]
HOLDINGS = {
    "005930.KS": ["삼성전자", "삼성"],
    "066570.KS": ["LG전자"],
    "454910.KS": ["두산로보", "두산로보틱스"],
    "005380.KS": ["현대차"],
    "035420.KS": ["NAVER", "네이버"],
    "NVDA": ["NVDA", "엔비디아"],
    "META": ["META", "메타"],
    "VOO": ["VOO"],
    "MSFT": ["MSFT", "마이크로소프트"],
    "AAPL": ["AAPL", "애플"],
    "GOOGL": ["GOOGL", "구글", "알파벳"],
    "ORCL": ["ORCL", "오라클"],
    # [8/11] ANET 전량 매도 체결(8/10 잔여 0.141767주 $27.29 · 8/5 절반 $30.17)로 보유에서 제외.
    #        보유 15 → 14종목. 워치리스트로 이관(재진입 조건부).
    "MU": ["MU", "마이크론"],
    "AVGO": ["AVGO", "브로드컴"],
}
ETF_NO_SCORE = {"VOO"}                 # ETF = 0~100 스코어 제외(null 허용)
REQUIRED_COLS = ["stars", "target", "buy_zone", "trim", "comment"]  # +score(ETF 외)

FAILS, WARNS = [], []
def fail(m): FAILS.append(m)
def warn(m): WARNS.append(m)

def load(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        fail(f"{rel} 없음 (정본 파일 누락)"); return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception as e:
        fail(f"{rel} JSON 파싱 실패: {e}"); return None

def band_star(score):
    return 5 if score >= 85 else 4 if score >= 70 else 3 if score >= 55 else 2 if score >= 40 else 1

def ver(name):
    m = re.search(r"report_v(\d+)", name or "")
    return int(m.group(1)) if m else None

# ── A. stocks.json: 보유 전종목(len(HOLDINGS)) 완전성 + 컬럼 + 별점↔스코어 ──────────
def check_stocks():
    d = load("data/app/stocks.json")
    if not d: return
    s = d.get("stocks", {})
    keys = set(s.keys())
    miss, extra = set(HOLDINGS) - keys, keys - set(HOLDINGS)
    if miss:  fail(f"stocks.json 보유종목 누락: {sorted(miss)}")
    if extra: fail(f"stocks.json 미지정 종목: {sorted(extra)}")
    if len(s) != len(HOLDINGS):
        fail(f"stocks.json 보유 {len(s)}종목 ({len(HOLDINGS)} 아님)")
    for t, v in s.items():
        for c in REQUIRED_COLS:
            val = v.get(c)
            if val in (None, "", []):
                fail(f"{t}: '{c}' 컬럼 비어있음 (풀표 컬럼 누락)")
        st = v.get("stars")
        if not (isinstance(st, int) and 1 <= st <= 5):
            fail(f"{t}: stars={st!r} (1~5 정수 아님)")
        sc = v.get("score")
        if t in ETF_NO_SCORE:
            continue
        if not (isinstance(sc, int) and 0 <= sc <= 100):
            fail(f"{t}: score={sc!r} (0~100 정수 아님 · ETF만 null 허용)"); continue
        if isinstance(st, int):
            exp = band_star(sc)
            # 정성가중: 별점은 score밴드 ±1 이내 허용(코어 확신·리스크 보수·모멘텀 가점).
            # ±2 이상 벌어지면 재점검 필요 → WARN. 모멘텀주(454910)는 score가 낮아 자동 ±1 수렴.
            if abs(st - exp) >= 2:
                warn(f"{t}: ⭐{st} vs score {sc}→밴드 ⭐{exp} ±2 이상 어긋남 — 근거 재점검")
    if not d.get("as_of"):        warn("stocks.json: as_of 비어있음")
    if not d.get("source_report"): warn("stocks.json: source_report 비어있음")

# ── B. flows.json: 추측 수치 금지(미확인=null) ────────────────────────────
def check_flows():
    d = load("data/app/flows.json")
    if not d: return
    ser = d.get("series")
    if not isinstance(ser, list) or not ser:
        fail("flows.json: series 비어있음"); return
    for e in ser:
        if not e.get("date"):
            fail("flows.json: date 없는 항목")
        for k in ("foreign", "inst", "indiv"):
            x = e.get(k, None)
            if x is not None and not isinstance(x, (int, float)):
                fail(f"flows.json {e.get('date')}: {k}={x!r} (숫자/ null 만 — 추측 문자열 금지)")
    if not d.get("updated"): warn("flows.json: updated 비어있음")

# ── C. tasks.json: source_report 실존 ────────────────────────────────────
def check_tasks():
    d = load("data/app/tasks.json")
    if not d: return
    sr = d.get("source_report")
    if not sr:
        warn("tasks.json: source_report 비어있음")
    elif not os.path.exists(os.path.join(ROOT, sr)):
        fail(f"tasks.json: source_report 파일 없음 → {sr}")
    if not d.get("as_of"): warn("tasks.json: as_of 비어있음")

# ── C2. 오더 실행가능성: 토스 주문 제약과 모순되는 계획 주문 적발 ────────────────
#   [8/1 신설 — v66 실사고] §7 오더북이 "AAPL 25% 트림을 $318 **지정가**로"라 적었는데
#   25% = 0.2556주 = **분수주**라 지정가가 애초에 안 걸린다(토스: 美 정수주=지정가 / 분수주=시장가 전용).
#   같은 보고서 §5·§9는 "25% 분할", §7은 "정수 1주(=97.8%)"로 서로 다른 걸 가리키고 있었다.
#   사람이 읽어선 안 걸리는 종류라 기계로 잡는다. 국내는 분수주 자체가 미지원(정수 1주 이상).
_FRACTION_OK_STATUS = ("체결", "취소")            # 이미 끝난 주문
_BLOCKED_STATUS = ("결정대기", "불가", "재검토",
                   # ★[8/13 추가] 휴면 주문 — 접수 예정 자체가 없으니 가격밴드 경고를 내지 않는다.
                   # 밴드는 **하루짜리 제약**이라 되살아나는 날 다시 계산되므로 미리 경고할 실익이 없고,
                   # 상시 WARN은 살아있는 주문의 경고를 묻는다(같은 세션 부채태그·429 경보 피로와 동일 교훈).
                   "보류", "동결", "폐기", "무효", "홀드 결정", "결정 완료",
                   # ★[8/24 추가] 방식ⓑ(트리거 기반 등록, d135) 도입으로 생긴 새 휴면 상태.
                   # 트림 오더는 **등록선(트림가 -5%)에 점등될 때까지 접수하지 않는다** —
                   # 접수 예정이 없는 날의 밴드 경고는 위 휴면 주문과 같은 이유로 소음이다.
                   # 점등되어 실제로 등록하는 날엔 status가 바뀌므로 밴드 검사가 다시 살아난다.
                   "트리거 대기")

def _is_kr(ticker: str) -> bool:
    return bool(re.search(r"\.(KS|KQ)$", ticker or "")) or bool(re.fullmatch(r"\d{6}", ticker or ""))

import pathlib  # noqa: E402  (가격밴드 검사용)


def _kr_tick(price: float) -> int:
    """KRX 호가단위(2023 개편 기준, 주식)."""
    if price >= 500_000: return 1000
    if price >= 200_000: return 1000
    if price >= 50_000:  return 100
    if price >= 20_000:  return 50
    if price >= 5_000:   return 10
    if price >= 2_000:   return 5
    return 1


def check_history_cache():
    """data/history 일봉 캐시의 정지 여부 검사 [8/12 신설].

    vol_gauge·garch·tranche_rules(하드플로어)·drawdown·chart_read·가격밴드 검사가
    전부 이 캐시를 읽는다. 낡으면 **룰 판정이 낡은 값으로 나온다** — 8/12에 실제로
    67/70 종목이 최대 8일 정지 상태였고, 그 캐시로 계산한 상한가가 4,000원 틀려
    LG전자 오더 경고가 어긋났다. 거래일 기준이 아니라 달력일 기준의 느슨한 임계를 쓴다.
    """
    import glob as _glob
    import csv as _csv
    files = _glob.glob("data/history/*.csv")
    if not files:
        return
    # ⚠️ 추적 대상만 본다 — 과거에 담았다가 빠진 종목(IBM 등)의 잔존 파일까지 FAIL로 잡으면
    # 게이트가 소음이 되고, 소음이 되면 사람이 무시한다. 유니버스 = 보유 + 워치 + 지수/매크로.
    pf = load(".claude/skills/portfolio-desk/portfolio.json") or {}
    tracked = set()
    for it in (list((pf.get("holdings") or {}).get("kr") or [])
               + list((pf.get("holdings") or {}).get("us") or [])
               + list(pf.get("watchlist") or [])):
        if (it or {}).get("ticker"):
            tracked.add(it["ticker"])
    today = dt.date.today()
    stale, orphan = [], []
    for fp in files:
        sym = os.path.basename(fp)[:-4]
        # 지수·환율·원자재는 유니버스 목록엔 없지만 룰 판정(매크로 오버레이)에 쓰이므로 추적 대상.
        # ⚠️ 파일명에서 Yahoo 심볼의 `=`·`^`가 `_`로 치환된다(BZ=F→BZ_F, KRW=X→KRW_X, ^GSPC→_GSPC)
        #    → 접두만 보면 매크로를 '고아'로 오분류한다(8/12 실측).
        _macro = (sym.startswith(("^", "_"))
                  or sym.endswith(("_F", "_X", ".SS", ".IS", ".TA", ".NYB"))
                  or "-" in sym)
        if sym not in tracked and not _macro:
            orphan.append(sym)
            continue
        try:
            rows = pathlib.Path(fp).read_text(encoding="utf-8").splitlines()
            last = rows[-1].split(",")[0]
            age = (today - dt.date.fromisoformat(last)).days
        except Exception:
            continue
        if age > HISTORY_MAX_STALE_DAYS:
            stale.append((sym, last, age))
    if orphan:
        info = ", ".join(sorted(orphan)[:6])
        warn(f"history 캐시에 추적목록 밖 잔존 파일 {len(orphan)}개 — {info}"
             f"{' 외' if len(orphan) > 6 else ''} (워치 편입이면 portfolio.json에 등록, "
             f"아니면 정리 대상 — 8/12 ANET '워치 전환' 미배선이 이렇게 발각됐다)")
    if not stale:
        return
    stale.sort(key=lambda x: -x[2])
    worst = ", ".join(f"{n}({a}d)" for n, _, a in stale[:5])
    msg = (f"history 캐시 정지 {len(stale)}/{len(files)}종목 (최대 {stale[0][2]}일) — {worst}"
           f"{' 외' if len(stale) > 5 else ''}. `{HISTORY_CMD}` 실행 필요 — "
           f"vol_gauge·하드플로어·가격밴드 판정이 낡은 값으로 나온다")
    (fail if stale[0][2] > HISTORY_MAX_STALE_DAYS * 2 else warn)(msg)


def check_high_low_claims():
    """'신고가·신저가' 주장을 일봉 캐시로 검증한다.

    ★[2026-08-12 실사고] v73이 **LG전자 "52주 신고가"**를 3곳에 실었는데 오류였다.
    실제 52주 고가는 종가 **392,500원(6/2)**·장중 438,000원이고 당일 205,000원은
    고가 대비 **-47.8%**였다. 오늘 212,500원은 '당일 고가'일 뿐인데
    토스 1일 차트의 '최고/최저' 표기를 52주 값으로 오독하기 쉽고,
    데스크가 매체 헤드라인("52주 신고가 경신")을 검증 없이 받아썼다.

    ⇒ 신고가 주장은 **매체가 아니라 우리 캐시**로 판정한다. 종가 기준이라
    장중 신고가는 못 잡지만, '52주 고가 대비 -47.8%'처럼 **명백히 어긋나는 주장**은 잡는다.
    """
    import glob as _glob
    import csv as _csv
    latest = newest_report_file()
    if not latest:
        return
    try:
        body = pathlib.Path("docs/reports") .joinpath(latest).read_text(encoding="utf-8")
    except Exception:
        try:
            body = pathlib.Path(latest).read_text(encoding="utf-8")
        except Exception:
            return
    # "<종목명> ... 52주 신고가" 패턴 — 같은 줄에 있을 때만(문맥 밖 오탐 방지)
    # 종목명 → 티커. stocks.json에는 이름 필드가 없다(8/12 음성테스트에서 확인) →
    # portfolio.json의 label을 정본으로 쓴다(보유 kr/us + 워치리스트).
    names = {}
    pf = load(".claude/skills/portfolio-desk/portfolio.json") or {}
    buckets = list((pf.get("holdings") or {}).get("kr") or []) \
        + list((pf.get("holdings") or {}).get("us") or []) \
        + list(pf.get("watchlist") or [])
    for it in buckets:
        lb, tk = (it or {}).get("label"), (it or {}).get("ticker")
        if lb and tk:
            names[lb] = tk
    for line in body.splitlines():
        if "신고가" not in line and "신저가" not in line:
            continue
        # 자기 정정문("…신고가는 오류다")이 스스로를 FAIL시키는 위양성 차단.
        if any(k in line for k in ("오류", "아님", "정정", "🔧", "재발방지")):
            continue
        for nm, tk in names.items():
            if nm not in line:
                continue
            fp = f"data/history/{tk}.csv"
            if not _glob.glob(fp):
                continue
            try:
                rows = list(_csv.reader(pathlib.Path(fp).read_text(encoding="utf-8").splitlines()))[1:]
                ser = [(r[0], float(r[1])) for r in rows if len(r) > 1 and r[1]]
            except Exception:
                continue
            if len(ser) < 30:
                continue
            cur = ser[-1][1]
            win = ser[-252:] if "52주" in line or "신고가" in line else ser[-252:]
            hi = max(win, key=lambda x: x[1])
            lo = min(win, key=lambda x: x[1])
            oid = f"{nm}"
            if "신고가" in line and cur < hi[1] * 0.98:
                fail(f"신고가 주장 오류 [{oid}]: 현재 종가 {cur:,.0f} vs 52주 고가 "
                     f"{hi[1]:,.0f}(@{hi[0]}) = {cur/hi[1]-1:+.1%} — 신고가 아님. "
                     f"매체 헤드라인이 아니라 data/history 캐시로 확인할 것")
            if "신저가" in line and cur > lo[1] * 1.02:
                fail(f"신저가 주장 오류 [{oid}]: 현재 종가 {cur:,.0f} vs 52주 저가 "
                     f"{lo[1]:,.0f}(@{lo[0]}) = {cur/lo[1]-1:+.1%} — 신저가 아님")


def check_kr_price_band():
    """국내 지정가 오더가 당일 가격제한폭(±30%) 안인지 검사.

    ★[2026-08-12 실사고] LG전자 익절 지정가 **240,000원**이 당일 상한가 **236,000원**
    (8/11 종가 181,700 × 1.3, 호가단위 1,000원 반영)을 4,000원 초과해 **주문 자체가
    접수 거부**됐다. 판단(무엇을 얼마에 팔까)은 맞았는데 **그 주문이 물리적으로 접수
    가능한지**를 아무도 확인하지 않았다 — 8/1 '분수주는 지정가가 안 걸린다'(AAPL)와
    같은 클래스다. 8/2 '오더북에 들어간 것만 집행된다'의 숨은 전제 =
    **애초에 오더북에 들어갈 수 있는 가격일 것**.

    밴드는 매일 전일 종가로 재계산되므로 **하루짜리 제약**이다 → FAIL이 아니라 WARN으로
    내고, "며칠 뒤면 들어간다"는 판단은 사람이 한다. 기준가는 캐시된 일봉(data/history)의
    직전 종가를 쓰며, 캐시가 없으면 조용히 건너뛴다(네트워크 호출 안 함).
    """
    d = load("data/app/tasks.json")
    if not d:
        return
    import glob as _glob
    for o in d.get("orders", []) or []:
        st = str(o.get("status", ""))
        if any(k in st for k in _BLOCKED_STATUS) or "체결" in st or "취소" in st:
            continue
        tk = str(o.get("ticker") or "")
        price = o.get("price")
        if not _is_kr(tk) or not isinstance(price, (int, float)) or price <= 0:
            continue
        act = str(o.get("action", "")) + " " + str(o.get("label", ""))
        if "시장가" in act:
            continue
        # 기준가 = 캐시된 일봉(data/history/<ticker>.csv "date,close")의 마지막 종가.
        # ⚠️ 캐시가 오늘까지 안 왔으면 기준가가 낡아 밴드도 낡는다 → 경고에 기준일을 병기한다.
        base, base_date = None, None
        for fp in _glob.glob(f"data/history/{tk}.csv"):
            try:
                rows = [r for r in pathlib.Path(fp).read_text(encoding="utf-8").splitlines() if r.strip()]
                if len(rows) > 1:
                    last = rows[-1].split(",")
                    base_date, base = last[0], float(last[1])
            except Exception:
                pass
            break
        if not base:
            continue
        tick = _kr_tick(base * 1.3)
        cap = int(base * 1.3 // tick * tick)
        floor = int(-(-(base * 0.7) // tick) * tick)
        oid = o.get("id") or o.get("label") or tk
        if price > cap:
            warn(f"오더 접수불가 우려 [{oid}]: 지정가 {price:,.0f}원 > 상한가 "
                 f"{cap:,}원(기준가 {base:,.0f}원 @{base_date}×1.3) — 밴드는 매일 재계산되니 "
                 f"기준가가 {price/1.3:,.0f}원 이상이면 등록 가능")
        elif price < floor:
            warn(f"오더 접수불가 우려 [{oid}]: 지정가 {price:,.0f}원 < 하한가 "
                 f"{floor:,}원(기준가 {base:,.0f}원 @{base_date}×0.7)")

        # ★[8/13 신설] 시간외단일가(16:00~18:00)는 **당일 종가 ±10%**라는 별도의 더 좁은
        # 밴드를 쓴다(당일 상·하한가 이내라는 조건이 추가로 붙는다).
        # 왜 필요한가: 평일 정훈 폰창은 17:30~20:50이라 국내 주문의 실제 접수 창이
        # **시간외 30분(17:30~18:00)뿐**인 날이 대부분이다. 정규장 ±30%만 검사하면
        # "밴드 안"이라고 통과시켜 놓고 정작 그 30분엔 못 넣는다.
        # 실사고: 8/13 LG전자 240,000원 — 정규장 상한(268,450원)엔 들어가는데
        # 시간외 상한은 종가 206,500×1.1 = 227,150원이라 접수 불가였다.
        # 이건 8/12 d93에 "③시간외단일가 등록 — 기각(별도 가격범위 제약)"으로 이미
        # 적어둔 사실인데 다음날 오더북이 되살렸다 = 산문 기록만으론 재발을 못 막는다.
        #
        # ★[8/19 실측 교정] 최초 문구는 "평일 폰창으론 못 넣는다"고 단정했으나 **틀렸다** —
        # 정훈이 18:49(시간외 종료 후)에 현대차 470,000원·두산로보 90,000원을 걸었고
        # 둘 다 정상 접수돼 '대기 중인 주문'에 남았다(시간외 밴드는 455,000·78,600원).
        # 8/13 정정("토스 국내주식도 예약주문 된다")이 이 함수 문구에 반영되지 않은 것이었다.
        # ⇒ 이 검사는 **접수 불가 경고가 아니라 주문 경로 안내**다: 시간외 즉시체결은 못 노리니
        # 정규장 예약(±30%)으로 걸라는 뜻. WARN 등급 유지(경로를 헷갈리면 실제로 못 넣으므로).
        aft_cap = int(base * 1.1 // tick * tick)
        aft_floor = int(-(-(base * 0.9) // tick) * tick)
        if floor <= price <= cap and not (aft_floor <= price <= aft_cap):
            warn(f"시간외 즉시주문 불가 [{oid}]: 지정가 {price:,.0f}원이 시간외단일가 밴드 "
                 f"{aft_floor:,}~{aft_cap:,}원(종가 {base:,.0f}원 @{base_date}±10%) 밖 — "
                 f"**정규장 예약주문으로 걸 것**(±30% 밴드 적용). 시간외(16:00~18:00) 즉시 체결을 "
                 f"노리려면 종가 {price/1.1:,.0f}원 이상이어야 한다")


def check_target_multiple():
    """목표가가 함의하는 **후행 배수**가 역사 정당구간 상단을 넘으면 선행 EPS 가정을 요구한다.

    ★[2026-08-14 신설·정훈 승인] 9회차 캘리브레이션에서 확인된 유일한 '콜 품질' 결함의 기계화.
    `target_score`가 낸 낙관 편향이 **내재여력과 단조 비례**했고(+17.4 → +22.7 → +39.9 → +58.7%p),
    `multiple_backtest`(16년 EPS×가격)도 같은 방향으로 **상단초과 5종**을 지목했다.

    ⚠️ **그런데 '역사 정당배수 상단으로 캡'을 기계적으로 적용하면 안 된다** — 실측해보니
    5종 전부 캡 적용 목표가가 **현재가 아래**로 떨어져(AAPL -23.1%·MU -31.5%·AVGO -26.3%·
    ORCL -17.1%·ANET -5.3%) 동시 매도 신호가 된다. TTM(후행) 배수는 **이익이 급성장하는
    국면에서 구조적으로 높게** 나오기 때문이다(MU = 메모리 사이클, AVGO·ANET = AI).
    `multiple_backtest` 자신도 *"배수의 타당 범위이지 우리 목표가의 정오 판정이 아니다"*라고 경고한다.
    ⇒ **캡이 아니라 거증책임으로 구현한다**: 상단을 넘는 목표가는 금지가 아니라
      **선행 EPS 가정을 명시**해야 통과한다. 낙관을 막는 게 아니라 **말 없는 낙관**을 막는 것.

    밴드 원장 = `data/app/multiple_bands.json`(`multiple_backtest.py --save`, 주간 R3 갱신).
    원장이 없거나 낡아도 조용히 건너뛴다(네트워크 호출 안 함).
    """
    b = load("data/app/multiple_bands.json")
    d = load("data/app/stocks.json")
    if not b or not d:
        return
    # ⚠️ [8/14 음성테스트로 즉시 교정] 1차 구현은 토큰 매칭("컨센" 등)이었는데
    #    "컨센 목표 $428" 같은 문구가 거의 모든 코멘트에 있어 **9/9 전부 통과 = 절대 발동 불가**였다.
    #    오늘 정리한 (B)계열('죽은 배선')을 새로 만드는 짓이므로 그 자리에서 조인다.
    #    ⇒ 요구조건 = `target_basis`에 **숫자를 가진 EPS 가정**이 있을 것(EPS $9.55 / EPS 155.56 형태).
    #      코멘트는 보지 않는다 — 근거는 target_basis에 있어야 한다.
    import re as _re
    eps_num = _re.compile(r"EPS[^0-9$]{0,12}\$?\s*\*{0,2}\s*[0-9][0-9,\.]*", _re.I)
    for tk, meta in (b.get("stocks") or {}).items():
        band, imp = meta.get("band"), meta.get("implied")
        if not band or not imp:
            continue
        if imp[0] <= band[1]:          # 하단이 밴드 상단 이내면 '상단초과'가 아니다
            continue
        ent = (d.get("stocks") or {}).get(tk) or (d.get("watchlist") or {}).get(tk)
        if not isinstance(ent, dict):
            continue
        basis = str(ent.get("target_basis") or "")
        if eps_num.search(basis):
            continue
        warn(f"{tk}: 목표가 내재배수 {imp[0]:.0f}~{imp[1]:.0f}x > 역사 정당구간 상단 {band[1]:.1f}x "
             f"(TTM EPS {meta.get('ttm_eps')}) — **선행 EPS 가정을 target_basis에 명시할 것** "
             f"(캡 아님·거증책임. 8/14 캘리브레이션 9회차)")


def check_order_feasibility():
    """tasks.json orders가 토스 주문 제약을 위반하는지 검사.
    지정가 주문인데 수량이 분수(미국) / 1주 미만(국내)이면 그 주문은 낼 수 없다."""
    d = load("data/app/tasks.json")
    if not d:
        return
    pf = load(".claude/skills/portfolio-desk/portfolio.json") or {}
    held = {}
    for reg in ("kr", "us"):
        for h in (pf.get("holdings", {}) or {}).get(reg, []) or []:
            held[h.get("ticker") or h.get("label")] = h.get("shares")

    for o in d.get("orders", []) or []:
        st = str(o.get("status", ""))
        if any(k in st for k in _FRACTION_OK_STATUS):
            continue
        if any(k in st for k in _BLOCKED_STATUS):
            continue                       # 이미 '실행 불가'로 표기됨 — 재경고는 소음
        tk = str(o.get("ticker") or "")
        # ⚠️ 의도 판정은 action·label(선언문)만 본다. note는 산문이라 정정 설명("25%는 분수라
        #    지정가 불가")이 그대로 주문 의도로 오독된다(8/1 위양성 실측).
        act = str(o.get("action", "")) + " " + str(o.get("label", ""))
        sh = o.get("shares")
        oid = o.get("id") or o.get("label") or tk
        wants_limit = ("지정가" in act) or (o.get("price") is not None and "시장가" not in act)

        if _is_kr(tk):
            if isinstance(sh, (int, float)) and 0 < sh < 1:
                fail(f"오더 실행불가 [{oid}]: 국내는 분수주 미지원인데 수량 {sh}주 — 정수 1주 이상으로")
            continue

        # 미국: 지정가는 정수주만
        if wants_limit and isinstance(sh, (int, float)) and sh > 0 and abs(sh - round(sh)) > 1e-9:
            fail(f"오더 실행불가 [{oid}]: 미국 지정가는 정수주 전용인데 수량 {sh}주(분수) — "
                 f"시장가로 바꾸거나 정수주로 조정")

        # 트림인데 '보유의 N%'를 지정가로 팔려는 경우: 그 비율이 분수면 지정가 불가
        m = re.search(r"(\d{1,3})\s*%", act)
        if wants_limit and m and tk in held and isinstance(held[tk], (int, float)):
            pct = int(m.group(1))
            if 0 < pct < 100:
                q = held[tk] * pct / 100.0
                if q < 1:
                    warn(f"오더 설계 모순 [{oid}]: 보유 {held[tk]}주의 {pct}% = {q:.4f}주(분수)라 "
                         f"지정가 불가 — 지정가로 낼 수 있는 최소 단위는 정수 1주"
                         f"(= 보유의 {100/held[tk]:.1f}%). 비율과 주문방식 중 하나를 고쳐야 함")

# ── C-2. 집행 배선 가드 [8/2 신설 — '신호는 났는데 집행이 안 따라간' 7주 진단] ──
#  근거(실측): 보고서 산문에 현대차·두산로보 트림이 8~9회 등장했으나 tasks.json orders에는
#  단 한 번도 등록된 적이 없다(git log -S 0건). 반대로 실제 체결된 7건(AAPL·MU·TSLA·삼성·
#  VOO·GOOGL)은 전부 orders에 등록돼 있었다. ⇒ **오더북에 들어간 것만 집행된다.
#  산문에 남은 판단은 증발한다.** 손실의 68.7%가 이 경로로 방치된 ⭐2 두 종목에서 나왔다.
_NO_DECISION = {"관망", "—", "-", "", "보류", "대기", "홀딩", "홀드", "유지"}
# 결정으로 인정하는 최소 요건: 가격·수량 / 재검토 트리거 / 기한 중 하나라도 박혀 있을 것
_DECISION_MARK = re.compile(
    r"\d|트리거|조건|재검토|기한|까지|이하|이상|청산|트림|실적|게이트|D\+|월|일"
)

def check_low_star_action():
    """⭐2 이하 보유 종목은 '관망'으로 넘어갈 수 없다 — 명시적 결정을 강제.

    ⭐2는 우리 채점기가 낸 경고 신호다. 그 신호에 대해 매 보고서가 내놓아야 하는 건
    '관망' 두 글자가 아니라 ①트림 오더(가격·수량) 또는 ②홀드 + 재검토 트리거·기한이다.
    둘 다 없으면 그 종목은 채점만 되고 관리되지 않는 상태 = 49일 방치의 재생산.

    ★[8/22 정훈 승인 — ⭐1과 ⭐2를 가른다] n=851 실측에서 두 구간이 **정반대**로 나왔다:
      · ⭐1 (n=12)  알파 **-8.75%** → 채점이 제대로 작동. **트림이 맞다.**
      · ⭐2 (n=130) 알파 **+3.31%** → ⭐5(+1.29%)보다 높다. **팔면 손해였다.**
    ⇒ 결정 강제(이 FAIL)는 두 구간 모두 유지하되, **권장 기본값을 갈라 안내**한다.
      ⭐2에 기계적으로 트림을 걸던 관행이 알파를 깎았을 가능성이 실측으로 드러났다.
    ⚠️ 붕괴장 표본이라 ⭐2 상승에 낙폭과대 반등이 섞였을 수 있다 — 정상장 표본 축적 후 재검토."""
    st = load("data/app/stocks.json")
    tk = load("data/app/tasks.json")
    if not st or not tk:
        return
    ordered = {str(o.get("ticker") or "") for o in (tk.get("orders") or [])}
    for t, v in (st.get("stocks") or {}).items():
        stars = v.get("stars")
        if not isinstance(stars, int) or stars > 2:
            continue
        trim = str(v.get("trim") or "").strip()
        core = re.sub(r"[()（）\s]|모멘텀|코어", "", trim)
        has_order = t in ordered
        decided = bool(_DECISION_MARK.search(trim)) and core not in _NO_DECISION
        if not has_order and not decided:
            rec = ("**트림 우선**(⭐1 실측 알파 -8.75%)" if stars == 1
                   else "**홀드+재검토 트리거 우선**(⭐2 실측 알파 +3.31% — 기계적 트림이 알파를 깎았다, 8/22 승인)")
            fail(f"{t}: ⭐{stars}인데 trim='{trim}' = 무결정 방치 — "
                 f"트림 오더(tasks.json orders)를 걸든 '홀드 + 재검토 트리거·기한'을 명시하든 "
                 f"결정을 내려야 한다('관망'은 결정이 아님). 권장 = {rec}")
        elif not has_order:
            warn(f"{t}: ⭐{stars} 종목이 orders에 없음 — 산문 결정('{trim[:30]}')이 "
                 f"오더로 배선되지 않으면 집행되지 않는다(7주 실측)")

def check_prose_order_link(rel):
    """보고서 산문이 보유 종목의 트림/매도/청산을 말하는데 orders에 없으면 경고.

    산문↔오더북 단절이 집행 실패의 실제 경로였다. 말한 것과 등록한 것을 기계가 대조한다."""
    tk = load("data/app/tasks.json")
    if not tk or not rel:
        return
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return
    ordered = {str(o.get("ticker") or "") for o in (tk.get("orders") or [])}
    txt = open(p, encoding="utf-8").read()
    act = re.compile(r"(트림|매도|청산)")
    for t, aliases in HOLDINGS.items():
        if t in ordered:
            continue
        hits = 0
        for ln in txt.splitlines():
            if act.search(ln) and any(a in ln for a in aliases):
                hits += 1
        if hits >= 3:                       # 스치듯 1~2회는 서술, 3회+는 의도로 본다
            warn(f"{t}: 보고서에서 트림/매도를 {hits}회 논하면서 orders 미등록 — "
                 f"오더로 옮기지 않으면 다음 세션에 사라진다(현대차 8회·두산로보 9회 전례)")

def check_pending_decisions(today=None):
    """'정훈 결정 대기'가 며칠째 방치 중인지 — 결정 큐에 SLA를 건다.

    d21(GOOGL 재배치 지정가 상향)이 7/7부터 26일째 미결이었다. 대기 항목은 아무도
    재촉하지 않으면 영원히 대기한다 → 7일 초과 WARN, 14일 초과 FAIL로 끌어올린다."""
    p = os.path.join(ROOT, "data/app/decisions.jsonl")
    if not os.path.exists(p):
        return
    today = today or dt.date.today()
    pend = re.compile(r"결정\s*대기|결정대기|택1|승인\s*대기|정훈\s*확인\s*요망")
    for ln in open(p, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if str(r.get("status")) == "closed":
            continue
        blob = f"{r.get('topic','')} {r.get('decision','')} {r.get('status','')}"
        if not pend.search(blob):
            continue
        try:
            d0 = dt.date.fromisoformat(str(r.get("date"))[:10])
        except Exception:
            continue
        age = (today - d0).days
        if age > 14:
            fail(f"결정 대기 {age}일 방치 [{r.get('id')}] {str(r.get('topic'))[:60]} — "
                 f"정훈에게 다시 올리거나 PM 디폴트로 종결할 것")
        elif age > 7:
            warn(f"결정 대기 {age}일 [{r.get('id')}] {str(r.get('topic'))[:60]} — 재촉 필요")

# ── D. 버전 정합: CLAUDE.md/stocks/tasks 가 최신 보고서를 가리키는가(stale 방지) ─
def latest_version():
    rdir = os.path.join(ROOT, "docs/reports")
    vs = [ver(f) for f in os.listdir(rdir) if re.match(r"report_v\d+", f)]
    vs = [v for v in vs if v is not None]
    return (max(vs) if vs else None)

def _report_file_times():
    """docs/reports 내 report_v* 파일별 '유효 시각'(epoch).
    [7/13 교정] fresh clone은 모든 파일 mtime이 클론 시각으로 뭉개져 mtime 비교가
    비결정적(v47 본편·시나리오 부록이 같은 커밋인데 가짜 FAIL 난 실사고) → 정본 시각 = git
    최종 커밋시각. 단 워킹트리에서 수정/미추적인 파일(방금 쓴 새 보고서 — validate는 커밋 전
    실행이 정상 플로우)은 mtime이 진실. git 불가 환경이면 전부 mtime 폴백(구 동작)."""
    rdir = os.path.join(ROOT, "docs/reports")
    files = [f for f in os.listdir(rdir) if re.match(r"report_v\d+_", f)]
    commit_t, dirty = {}, None
    try:
        log = subprocess.run(["git", "-C", ROOT, "log", "--pretty=%ct", "--name-only",
                              "--", "docs/reports"], capture_output=True, text=True, timeout=30)
        if log.returncode == 0:
            cur = None
            for line in log.stdout.splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.isdigit():
                    cur = int(s)
                elif cur is not None:
                    commit_t.setdefault(os.path.basename(s), cur)  # log는 최신순 → 첫 값 = 최종 커밋
        st = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", "docs/reports"],
                            capture_output=True, text=True, timeout=30)
        if st.returncode == 0:
            dirty = {os.path.basename(l[3:].split(" -> ")[-1].strip().strip('"'))
                     for l in st.stdout.splitlines() if len(l) > 3}
    except Exception:
        commit_t, dirty = {}, None
    eff = {}
    for f in files:
        if f in commit_t and (dirty is not None and f not in dirty):
            eff[f] = commit_t[f]
        else:
            try:
                eff[f] = os.path.getmtime(os.path.join(rdir, f))
            except OSError:
                eff[f] = 0
    return eff

def newest_report_files():
    """최신 보고서 '파일 집합'(버전+유효시각 최댓값) — intra-version stale 감지용.
    같은 커밋으로 함께 들어온 파일들(본편+부록 등 동시각 tie)은 같은 세션 산출물이므로
    집합으로 취급: source_report가 집합의 어느 멤버를 가리켜도 stale 아님."""
    eff = _report_file_times()
    if not eff:
        return []
    key = lambda f: (ver(f) or 0, eff[f])
    top = max(key(f) for f in eff)
    return sorted(f for f in eff if key(f) == top)

def newest_report_file():
    """최신 보고서 파일 1개(집합 대표 — 날짜 추출 등 단일값 용도)."""
    fs = newest_report_files()
    return fs[-1] if fs else None

def check_versions(latest):
    if latest is None:
        warn("docs/reports/ 에 report_v*.md 없음"); return
    newest_set = newest_report_files()
    st = load("data/app/stocks.json")
    if st and ver(st.get("source_report")) and ver(st.get("source_report")) < latest:
        fail(f"stocks.json source_report=v{ver(st.get('source_report'))} < 최신 v{latest} (정본 stale)")
    # [7/2 신설·7/13 git시각 교정] intra-version stale: v번호는 같아도 같은 날 아침→EXEC 등
    # 최신 '파일 집합'에 없으면 FAIL. (v37 아침 서사가 EXEC 폭락 뒤에도 앱에 남았던 사고 재발 방지)
    elif st and newest_set:
        sr_base = os.path.basename(st.get("source_report") or "")
        if ver(sr_base) == latest and sr_base not in newest_set:
            fail(f"stocks.json source_report={sr_base} ≠ 최신 파일 {'/'.join(newest_set)} "
                 f"(같은 v{latest} 내 stale — EXEC/밤 대화 등 부록 세션도 stocks.json 동기화 의무)")
    tk = load("data/app/tasks.json")
    if tk and ver(tk.get("source_report")) and ver(tk.get("source_report")) < latest:
        warn(f"tasks.json source_report=v{ver(tk.get('source_report'))} < 최신 v{latest}")
    elif tk and newest_set:
        tk_base = os.path.basename(tk.get("source_report") or "")
        if ver(tk_base) == latest and tk_base not in newest_set:
            warn(f"tasks.json source_report={tk_base} ≠ 최신 파일 {'/'.join(newest_set)} (intra-version stale)")
    # CLAUDE.md (자동로드 지도). 한/영 하이브리드 토큰 모두 인식.
    cp = os.path.join(ROOT, "CLAUDE.md")
    if os.path.exists(cp):
        txt = open(cp, encoding="utf-8").read()
        m = (re.search(r"최신[^\n]*?v(\d+)", txt) or re.search(r"현재[^\n]*?\bv(\d+)\b", txt)
             or re.search(r"(?:latest|current)[^\n]*?\bv(\d+)\b", txt, re.I))
        if m and int(m.group(1)) < latest:
            fail(f"CLAUDE.md 현재상태 = v{m.group(1)} < 최신 v{latest} (지도가 stale — 새 세션이 옛 상태로 출발)")
        elif not m:
            warn("CLAUDE.md 에서 현재 버전 토큰을 못 찾음 (검증 생략)")
    # config_overview.md (인덱스/지도). v28→v31 stale 재발 방지 [2026-06-25].
    op = os.path.join(ROOT, "docs/config_overview.md")
    if os.path.exists(op):
        otxt = open(op, encoding="utf-8").read()
        om = re.search(r"현재[^\n]*?\bv(\d+)\b", otxt) or re.search(r"정본[^\n]*?\bv(\d+)\b", otxt)
        if om and int(om.group(1)) < latest:
            fail(f"config_overview.md 정본 = v{om.group(1)} < 최신 v{latest} (인덱스 stale)")

# ── E. 보고서 파일(선택): 디스클레이머 1회·STATE SNAPSHOT·보유 전종목 등장 ──────
def latest_report_path(latest):
    rdir = os.path.join(ROOT, "docs/reports")
    cands = [f for f in os.listdir(rdir) if re.match(rf"report_v{latest}_", f)]
    return os.path.join("docs/reports", sorted(cands)[0]) if cands else None

def check_report(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        fail(f"보고서 파일 없음: {rel}"); return
    txt = open(p, encoding="utf-8").read()
    dc = len(re.findall(r"투자\s*자문\s*아님", txt))
    if dc > 1:
        warn(f"{rel}: 디스클레이머 '투자 자문 아님' {dc}회 (파일 끝 1회만 — 정훈 지적)")
    if "STATE SNAPSHOT" not in txt:
        fail(f"{rel}: STATE SNAPSHOT 블록 없음 (연속성 백본 누락)")
    absent = [t for t, al in HOLDINGS.items()
              if not any(a in txt for a in al) and t not in txt]
    if absent:
        warn(f"{rel}: 본문에 안 보이는 보유종목 {absent} (풀표 누락 가능 — 확인)")

# ── F. 정본 일관성: portfolio.json(원가·trigger 기계정본) ↔ stocks.json(앱 정본) ─
def check_consistency():
    pf = load(".claude/skills/portfolio-desk/portfolio.json")
    sj = load("data/app/stocks.json")
    if not pf or not sj:
        return
    flat = pf.get("holdings", {}).get("kr", []) + pf.get("holdings", {}).get("us", [])
    pf_tk = {x.get("ticker") for x in flat}
    sj_tk = set(sj.get("stocks", {}).keys())
    if pf_tk - sj_tk:
        fail(f"portfolio.json holdings에만(stocks 누락): {sorted(pf_tk - sj_tk)}")
    if sj_tk - pf_tk:
        fail(f"stocks.json에만(portfolio holdings 누락): {sorted(sj_tk - pf_tk)} — pnl·trigger가 못 봄")
    for x in flat:
        if not x.get("cost"):
            fail(f"portfolio.json {x.get('ticker')}: cost(원가) 없음 — 수익률 정본 누락")
    pf_w = {x.get("ticker") for x in pf.get("watchlist", [])}
    sjw = sj.get("watchlist", {})
    sj_w = set(sjw.keys()) if isinstance(sjw, dict) else {x.get("ticker") for x in sjw}
    if pf_w != sj_w:
        warn(f"워치 불일치 portfolio↔stocks: portfolio만 {sorted(pf_w - sj_w)} / stocks만 {sorted(sj_w - pf_w)}")

def check_hunter():
    """경제사냥꾼 앱 데이터 동기화 게이트.
    ① latest_videos 요약 필드(summary) 누락 = 앱 상세 '—' 빈칸 → FAIL/WARN.
    ② hunter_log.md 날짜 vs hunter_archive.json 날짜 비교 → 로그에만 있는 날짜=아카이브 정체 FAIL.
       [7/4 격상] latest_videos는 커버로 치지 않는다 — 앱 '전체 영상 아카이브' 화면은
       archive만 읽으므로 latest에만 있으면 화면에서 통째로 빠진다(7/3 정체 재발 원인).
       build_app_data.py가 latest→archive 자동 롤오버하므로 빌드만 돌리면 해소."""
    hu = load("data/app/hunter.json")
    arch = load("data/app/hunter_archive.json")
    if not hu:
        return
    lv = hu.get("latest_videos", [])
    for i, v in enumerate(lv):
        has_sum = bool((v.get("summary") or "").strip())
        has_note = bool((v.get("note") or "").strip())
        title = v.get("title", f"#{i}")
        if not has_sum and not has_note:
            fail(f"hunter latest_videos '{title}': 요약(summary) 없음 — 앱 상세가 '—' 빈칸")
        elif not has_sum and has_note:
            warn(f"hunter latest_videos '{title}': 정본 키는 'summary'인데 'note'로 들어옴 — summary로 교정 권고")

    # 커버리지 갭: 로그 날짜가 hunter_archive.json에 실제 반영됐는지 (latest는 커버 아님)
    log_path = os.path.join(ROOT, "docs/research/hunter_log.md")
    if os.path.exists(log_path):
        txt = open(log_path, encoding="utf-8").read()
        log_dates = set(re.findall(r"^#{2,3}\s+(\d{4}-\d{2}-\d{2})", txt, re.M))
        latest_dates = {v.get("date") for v in lv if v.get("date")}
        arch_dates = set()
        if isinstance(arch, dict):
            arch_dates = {v.get("date") for v in arch.get("videos", []) if v.get("date")}
        # 내부 구멍(=앱 최신일보다 오래됐는데 빠진 날짜)만 대상.
        # 로그 헤더가 브리핑 날짜(영상 업로드일보다 하루 뒤)인 경우가 있어
        # (archive ∪ latest) 최신일보다 '새로운' 로그 날짜는 오탐이므로 제외.
        #
        # [2026-08-24 정정] 위 주석의 '하루 뒤' 톨러런스가 "지금 이 순간 최신"에만
        # 적용돼 있었다 — frontier가 하루 더 전진하면(다음날 새 영상이 archive에 들어오면)
        # 예전엔 봐줬던 브리핑 헤더가 그대로 FAIL로 뒤집힌다(실측: 2026-08-23 헤더가
        # 8/24 신규 영상 반영 직후 FAIL 전환 — 콘텐츠는 그대로인데 frontier만 움직였다).
        # ⇒ '가장 최신 헤더만 봐준다'가 아니라 **frontier 기준 1일 이내 헤더는 상시 톨러런스**로
        # 바꾼다(브리핑 헤더는 원래 구조상 항상 다음날 표기될 수 있으므로).
        all_dates = arch_dates | latest_dates
        if all_dates:
            newest = max(all_dates)
            try:
                newest_d = dt.date.fromisoformat(newest)
            except ValueError:
                newest_d = None
            def _briefing_offset_ok(d):
                if newest_d is None:
                    return False
                try:
                    return (newest_d - dt.date.fromisoformat(d)).days <= 1
                except ValueError:
                    return False
            missing = sorted(d for d in log_dates
                              if d not in arch_dates and d <= newest and not _briefing_offset_ok(d))
            if missing:
                fail(f"hunter 아카이브 정체(로그엔 있으나 hunter_archive.json 미반영): {missing}"
                     " — build_app_data.py 실행 시 latest→archive 자동 롤오버로 해소")

    # 스키마 게이트 [7/4 실사고]: tickers가 문자열이면 앱 renderArchive가 forEach에서
    # 크래시 → 화면 전체 "데이터 로딩 중" 멈춤. 빌드가 자동 교정하므로 FAIL=빌드 미실행 신호.
    if isinstance(arch, dict):
        bad = [str(v.get("title", "?"))[:28] for v in arch.get("videos", [])
               if not isinstance(v.get("tickers"), list)]
        if bad:
            fail(f"hunter_archive tickers 비리스트 {len(bad)}건(앱 아카이브 화면 크래시): {bad[:3]}"
                 " — build_app_data.py 실행하면 자동 교정")

def check_feeds():
    """[7/7 신설] 외부 채널(수페TV·지식인사이드) feeds.json 게이트 — 신규라 WARN 수준.
    안정화(2~3주) 후 check_hunter처럼 FAIL 승격 검토."""
    fd = load("data/app/feeds.json")
    if not fd:
        return
    for slug, ch in (fd.get("channels") or {}).items():
        name = ch.get("name", slug)
        for i, v in enumerate(ch.get("latest_videos", [])):
            if not (v.get("summary") or "").strip() and not (v.get("note") or "").strip():
                warn(f"feeds[{name}] latest_videos '{v.get('title', f'#{i}')}': summary 없음 — 앱 빈칸")
            if not isinstance(v.get("tickers", []), list):
                warn(f"feeds[{name}] '{v.get('title', '?')[:28]}': tickers 비리스트 — 리스트로 교정할 것")


def check_guru():
    """[7/23 신설] 대가 13F 흐름 guru_flows.json 게이트 — 분기 cadence라 WARN 수준
    (13F는 분기말 후 ~45일 지연 → 일일 보고서를 FAIL로 막지 않는다). 파일 없으면 스킵(옵션 피드).
    구조·필수필드·액션값·과도 staleness만 점검."""
    import datetime as _dt
    p = os.path.join(ROOT, "data/app/guru_flows.json")
    if not os.path.exists(p):
        return
    try:
        gf = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        warn(f"guru_flows.json JSON 파싱 실패: {e}"); return
    gurus = gf.get("gurus") or {}
    if not isinstance(gurus, dict) or not gurus:
        warn("guru_flows.json: gurus 비어있음 — guru_flows.py --emit 실행 필요"); return
    valid = {"NEW", "ADD", "TRIM", "EXIT", "HOLD"}
    for slug, g in gurus.items():
        if g.get("error"):
            warn(f"guru_flows[{slug}]: 수집 오류 — {g['error']}"); continue
        for fld in ("name", "quarter"):
            if not str(g.get(fld) or "").strip():
                warn(f"guru_flows[{slug}]: {fld} 없음")
        if not isinstance(g.get("moves", []), list):
            warn(f"guru_flows[{slug}]: moves 비리스트")
        if not isinstance(g.get("overlap_with_holdings", []), list):
            warn(f"guru_flows[{slug}]: overlap_with_holdings 비리스트")
        for m in (g.get("moves") or []):
            if m.get("action") not in valid:
                warn(f"guru_flows[{slug}] move '{str(m.get('issuer', '?'))[:20]}': 액션값 이상 ({m.get('action')})")
                break
    upd = gf.get("updated")
    if upd:
        try:
            gap = (_dt.date.today() - _dt.date.fromisoformat(upd)).days
            if gap > 120:
                warn(f"guru_flows.json {gap}일 경과 — 새 13F 공시창 지났을 수 있음(guru_flows.py --emit + 데스크 갱신)")
        except Exception:
            pass


# ── G. [7/2 신설] 신선도·정합 sanity: forecast 레인지 vs 실시세 · pm_view/decisions 날짜 ──
def check_freshness(latest):
    import datetime as _dt
    # 최신 보고서 날짜(파일명 YYYY-MM-DD)
    nf = newest_report_file() or ""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", nf)
    rep_date = m.group(1) if m else None

    # pm_view.json 오래됨 [7/13 강화: 3일→1일 — PM 사견은 매 보고서 필수(6/28 규약)인데
    # 앱 4파일 동기화 의무에 pm_view가 빠져 v47서 하루 stale 방치된 구멍]
    pv = load("data/app/pm_view.json")
    if pv and rep_date and pv.get("updated"):
        try:
            gap = (_dt.date.fromisoformat(rep_date) - _dt.date.fromisoformat(pv["updated"])).days
            if gap >= 1:
                warn(f"pm_view.json updated={pv['updated']} < 최신 보고서 {rep_date} "
                     f"({gap}일 stale — PM 사견은 매 보고서 필수, 앱 #pmview 동기화 누락)")
        except ValueError:
            pass

    # [7/12 신설] tasks.json 신선도 — R2가 outlook·index_forecast·할일 갱신을 빠뜨리는 사고 재발방지.
    # (v46서 as_of/source_report만 바꾸고 내용은 v45 7/9 상태로 남았는데 통과된 구멍. §3b 매 보고서 동기화 의무 = updated는 보고서 날짜와 같아야.)
    tk_fr = load("data/app/tasks.json")
    if tk_fr and rep_date and tk_fr.get("updated"):
        try:
            gap = (_dt.date.fromisoformat(rep_date) - _dt.date.fromisoformat(tk_fr["updated"])).days
            if gap >= 1:
                fail(f"tasks.json updated={tk_fr['updated']} < 최신 보고서 {rep_date} "
                     f"({gap}일 stale — outlook·index_forecast·할일 갱신 누락 의심. §3b 매 보고서 동기화 의무)")
        except ValueError:
            pass
    # index_forecast 코스피 ref vs flows 최신 종가 (updated는 갱신했지만 forecast 숫자를 안 고친 내용-stale 감지)
    fl_fr = load("data/app/flows.json")
    if tk_fr and fl_fr:
        ser = fl_fr.get("series") or []
        kospi_close = None
        if ser:
            mm = re.search(r"코스피\s*([\d,]+(?:\.\d+)?)", ser[-1].get("note") or "")
            if mm:
                try: kospi_close = float(mm.group(1).replace(",", ""))
                except ValueError: pass
        if kospi_close:
            for fc in (tk_fr.get("index_forecast") or []):
                if "코스피" in (fc.get("name") or ""):
                    ref = fc.get("ref")
                    if isinstance(ref, (int, float)) and abs(ref - kospi_close) / kospi_close > 0.03:
                        warn(f"tasks.json index_forecast 코스피 ref={ref:,} ≠ flows 최신 종가 {kospi_close:,.0f} "
                             f"(>3% 이격 — forecast 갱신 누락 의심)")
                    break

    # decisions.jsonl 최근성 (최신 보고서 날짜 엔트리 부재 = WARN)
    dp = os.path.join(ROOT, "data/app/decisions.jsonl")
    if os.path.exists(dp) and rep_date:
        dates = re.findall(r'"date":\s*"(\d{4}-\d{2}-\d{2})"', open(dp, encoding="utf-8").read())
        if dates and max(dates) < rep_date:
            warn(f"decisions.jsonl 최신 엔트리={max(dates)} < 보고서 {rep_date} — 당일 결정 기록 없음")

    # forecast.week 레인지 vs 실시세 (app/data.js 빌드 결과 기준 — 없으면 생략)
    dj = os.path.join(ROOT, "app/data.js")
    sj = load("data/app/stocks.json")
    if os.path.exists(dj) and sj:
        try:
            raw = open(dj, encoding="utf-8").read()
            payload = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
            # [7/13 신설] 빌드 stale: stocks.json을 고치고 build_app_data.py 재실행을 빠뜨리면
            # 앱(data.js)이 옛 서사를 노출 — source_report 대조로 감지.
            sr_app = os.path.basename(payload.get("source_report") or "")
            sr_st = os.path.basename(sj.get("source_report") or "")
            if sr_app and sr_st and sr_app != sr_st:
                warn(f"app/data.js source_report={sr_app} ≠ stocks.json {sr_st} "
                     "— build_app_data.py 재실행 누락(빌드 stale)")
            prices = {h.get("ticker"): h.get("price") for h in payload.get("holdings", [])}
            for t, v in sj.get("stocks", {}).items():
                wk = ((v.get("forecast") or {}).get("week") or {})
                lo, hi, px = wk.get("low"), wk.get("high"), prices.get(t)
                if all(isinstance(x, (int, float)) for x in (lo, hi, px)) and not (lo * 0.97 <= px <= hi * 1.03):
                    warn(f"{t}: 현재가 {px:,.0f}이 forecast.week {lo:,.0f}~{hi:,.0f} 밖 — 전망 재산정 필요")
        except Exception:
            pass

def check_financials(latest=None):
    """재무제표 **데이터 레이어**의 결손 검사 — [7/30 신설, docs/data_coverage.md §0]

    ⚠️ 이 검사가 없어서 사고가 났다. 기존 게이트는 '보고서'의 완결성(풀표·컬럼·별점 밴드)만
    봤고 '데이터 레이어'의 결손은 안 봤다 → 보유 15종목 재무제표가 **0건**인 채로 두 달간
    매일 FAIL 0으로 통과했다. 게이트가 있다는 사실이 오히려 다 갖췄다는 착각을 줬다.
    앞으로 재무제표가 비면 보고서를 못 낸다.
    """
    p = os.path.join(ROOT, "data", "app", "financials.json")
    if not os.path.exists(p):
        fail("financials.json 없음 — `python3 financials.py --all --save` 실행 필요"
             " (보유 종목 재무제표 = 스코어의 하드넘버 근거)")
        return
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        fail(f"financials.json 파싱 실패: {str(e)[:60]}")
        return

    stocks = d.get("stocks") or {}
    # ⚠️ 접미사를 흡수해 6자리 코드로만 대조하면 **시장이 틀린 티커를 놓친다**.
    #    실제 사고(7/30): financials가 454910.**KQ**(코스닥의 남의 종목)를 담고 있었는데
    #    코드 454910만 대조해 통과 → "커버리지 14/14"가 빈 껍데기를 세고 있었다.
    #    (6/14 원익IPS·테스 .KQ 사고의 반대방향 재발.) 따라서 **접미사까지 정확히** 본다.
    need = {t for t in HOLDINGS if t not in ETF_NO_SCORE}
    missing = sorted(need - set(stocks))
    if missing:
        fail(f"재무제표 미커버 {len(missing)}종목: {', '.join(missing)}"
             f" — financials.py 재실행 또는 소스 폴백 점검")
    for t in sorted(set(stocks) - need):
        if t.split(".")[0] in {x.split(".")[0] for x in need}:
            fail(f"{t}: 보유 티커와 접미사 불일치 — market_data.py 기준({', '.join(sorted(x for x in need if x.split('.')[0]==t.split('.')[0]))})으로 정정 필요"
                 f" (접미사가 다르면 다른 회사다)")

    # 3표가 실제로 들어왔는지(껍데기만 있는 레코드 적발)
    # 결측을 WARN으로 두면 '0건인데 통과'가 반복된다 → 보유 종목은 FAIL.
    for t, r in stocks.items():
        a = (r.get("annual") or [{}])[0] if r.get("annual") else {}
        hard = t in need
        say = fail if hard else warn
        if not a:
            say(f"{t} 연간 재무제표 비어 있음 — 소스 3단 폴백(EDGAR/Yahoo/DART) 점검")
            continue
        if a.get("assets") is None and a.get("revenue") is None:
            say(f"{t} 손익·재무상태 둘 다 결측 — 소스 확인")

    check_debt_integrity(stocks)

    # 신선도: 최신 보고서 날짜보다 오래되면 그날 상태가 아님(7/12 tasks.json stale과 같은 유형)
    if latest:
        rel = latest_report_path(latest)
        m = re.search(r"(\d{4}-\d{2}-\d{2})", rel or "")
        if m and (d.get("updated") or "") < m.group(1):
            warn(f"financials.json updated={d.get('updated')} < 보고서 {m.group(1)}"
                 f" — 재무 갱신 없이 보고서만 새로 남")

    # 스코어 근거: PM이 손으로 쓴 score와 데이터 서브스코어의 이격
    sp = os.path.join(ROOT, "data", "app", "stocks.json")
    if os.path.exists(sp):
        try:
            with open(sp, encoding="utf-8") as f:
                sj = json.load(f)
        except Exception:
            sj = {}
        src = sj.get("stocks") if isinstance(sj.get("stocks"), dict) else sj
        for t, r in stocks.items():
            sub = r.get("fund_subscore")
            if sub is None:
                continue
            ent = (src or {}).get(t) or (src or {}).get(t.split(".")[0]) or {}
            sc = ent.get("score") if isinstance(ent, dict) else None
            if isinstance(sc, (int, float)) and abs(sc - sub) >= 25:
                warn(f"{t} 스코어 {sc} vs 펀더 서브스코어 {sub} (이격 {abs(sc-sub):.0f})"
                     f" — N·L·M 가감분으로 설명되는지 근거 명시 필요")


# 무차입이 **검증된** 기업 — 결측이 정상인 곳. 근거를 남겨야 화이트리스트가 썩지 않는다.
#   ANET: EDGAR 부채 태그 최신 신고가 2013-12-31(IPO 전 $98.8M). 2014 상장 이후 신고 없음
#         = 실제 무차입 (2026-08-01 확인).
DEBT_FREE_VERIFIED = {"ANET": "EDGAR 부채 태그 2013년 이후 없음 — 실제 무차입(8/1 확인)"}

# 총차입금이 총부채 대비 작은 게 **검증된** 저차입 기업 — 비율 분기(td/li < 5%)의 화이트리스트.
# ★[8/13 신설] 결측 분기에만 화이트리스트가 있고 **비율 분기엔 없어서** 검증 끝난 3종이 매 세션
#   WARN을 냈다. 안 꺼지는 경보는 읽히지 않는다 — 이 검사가 막으려던 ORCL형 사고를 오히려
#   경보 피로로 통과시키는 구조였다. ⇒ 두 분기 모두 '검증 후 등재'로 통일한다.
#   ⚠️ 등재 조건은 **1차/준1차 출처 확인**이다. 근거 문자열 없이 넣지 말 것(화이트리스트가 썩는다).
DEBT_LIGHT_VERIFIED = {
    "GEV": "SEC EDGAR 전 태그 스윕 — 부채 계열 태그가 ShortTermBorrowings($63M)뿐, "
           "장기차입·combined 태그 자체가 존재하지 않음. 2024 스핀오프 후 순현금 $8.5B "
           "(2026-08-13 companyfacts 직접 확인)",
    "329180.KS": "KIS신용평가 2026-03-23 리포트 차입금의존도 2.6% — 총자산 26.16조 × 2.6% "
                 "= 약 6,802억으로 우리 값 6,821억과 정합. 순현금 2.9조(KIS 기준) "
                 "(2026-08-13 확인). 조선업 특성상 총부채는 계약부채(선수금) 비중이 크다",
    "240810.KQ": "순차입금비율 -24.2%(음수=순현금)·부채비율 20.1% — 후자는 우리 값 "
                 "(부채 1,946억/자본 9,700억=20.06%)과 정확히 일치. 반도체 장비사 특성상 "
                 "총부채는 매입채무·선수금 비중이 크다 (2026-08-13 확인)",
}


def check_debt_integrity(stocks: dict):
    """총차입금 태그가 제대로 잡혔는지 감사 — [8/1 신설]

    ★사고: ORCL은 `LongTermDebtNoncurrent`를 안 쓰고 `DebtLongtermAndShorttermCombinedAmount`로
    신고하는데 우리 태그 목록에 그게 없어서 `DebtCurrent`(단기 $7.2B)만 잡혔다. 실제 총차입금은
    **$129.5B** — 1/18로 과소집계됐고, net_cash가 **-98B(순차입) → +24B(순현금)** 로 **부호까지
    뒤집혔다.** 그 결과 룰2 조건③(순부채 증가)이 구조적으로 발동 불가였고 재무건전성
    서브스코어가 거꾸로 매겨졌다. **에러 없이 조용히** 굴러갔다.

    ⇒ 총차입금이 총부채 대비 비현실적으로 작거나 결측이면 **태그 미스를 의심**한다.
      (data_coverage.md §4b — 0은 결론이 아니라 가설이다.)
    """
    for t, r in sorted(stocks.items()):
        a = (r.get("annual") or [{}])[0] if r.get("annual") else {}
        if not a:
            continue
        td, li = a.get("total_debt"), a.get("liabilities")
        if not isinstance(li, (int, float)) or li <= 0:
            continue
        if td is None:
            if t not in DEBT_FREE_VERIFIED:
                warn(f"[부채태그 의심] {t}: total_debt 결측인데 총부채 {li/1e9:,.1f}B 존재 — "
                     f"실제 무차입인지 태그 미스인지 EDGAR 원문 확인 후 "
                     f"DEBT_FREE_VERIFIED 등재 (ORCL 사고 유형)")
            continue
        if td / li < 0.05 and t not in DEBT_LIGHT_VERIFIED:
            warn(f"[부채태그 의심] {t}: total_debt {td/1e9:,.1f}B 가 총부채 {li/1e9:,.1f}B의 "
                 f"{td/li*100:.1f}% — combined 태그 누락 의심(edgar_facts.DEBT_* 점검). "
                 f"1차 출처로 실제 저차입임이 확인되면 DEBT_LIGHT_VERIFIED에 근거와 함께 등재")


# ─────────────────────────────────────────── 데이터 레이어 감사 (--coverage)

# 레이어별 산출물 · 허용 지연(일) · 생성 스크립트 · 왜 필요한가
# ⚠️ 이 표가 곧 "리서치센터라면 당연히 있어야 하는 것" 목록이다. 정본 = docs/data_coverage.md §1~§2.
COVERAGE_LAYERS = [
    ("financials.json", 7,  "financials.py --all --save", "재무제표 3표 — 스코어의 하드넘버 근거 (2개월 0건 사고 재발방지)"),
    ("stocks.json",     1,  "보고서 파이프라인",            "종목별 콜(별점·스코어·매수존)"),
    ("flows.json",      1,  "naver_flows.py",             "외인·기관 수급"),
    ("tasks.json",      1,  "보고서 파이프라인",            "계획·할일·매수추적 (앱 #plan)"),
    ("hunter.json",     3,  "hunter_latest.py (R1)",       "경제사냥꾼 영상 논지·setups"),
    ("feeds.json",      3,  "hunter_latest.py (R1)",       "수페TV·지식인사이드"),
    ("sentiment.json",  7,  "naver_sentiment.py --save",   "리테일 심리 %ile (한국판 GSVI)"),
    ("guru_flows.json", 100, "guru_flows.py",              "대가 13F (분기 cadence — Feb/May/Aug/Nov)"),
    # [8/1 신설] data_coverage.md §3 #3·#2 해소분. 등록 안 하면 또 조용히 stale해진다 —
    # 재무제표 2개월 0건 사고의 구멍이 정확히 "게이트에 없어서"였다.
    ("eps_revisions.json", 7,  "eps_revisions.py --save",  "EPS 추정치 리비전 (측정 전용·CANSLIM 선행축)"),
    ("guidance.json",     30,  "guidance.py --save",       "실적 가이던스 (8-K Item 2.02 · 분기 cadence)"),
    ("transcripts.json",  30,  "transcripts.py --save",    "어닝콜 전문 Q&A (수요·공급 코멘트 · 분기 cadence)"),
]

# ★[8/12 신설] data/history 일봉 캐시 — 위 표는 data/app/*.json만 봐서
# **정작 가장 널리 쓰이는 레이어를 감시하지 않고 있었다.** 8/12 실측: 70종목 중 67종목이
# 최대 8일 정지(대부분 8/4~8/5). 이 캐시는 vol_gauge·garch·tranche_rules(하드플로어)·
# drawdown·chart_read·가격밴드 검사가 전부 읽는다 → 낡으면 **룰 판정 자체가 낡는다**.
# 8/10 교훈("루틴에 배선된 것만 갱신된다")의 정확한 재발 — 게이트에 없으면 조용히 상한다.
HISTORY_MAX_STALE_DAYS = 3
HISTORY_CMD = "history_backfill.py"


# ─────────────────── 폐기 룰 잔존 감지 [8/5 신설] ───────────────────
# 왜: 8/5에 desk_playbook.md risk-desk 고정 룰에서 **7/30에 폐기된 룰 두 개**가 발견됐다
#     (7,500 매수 안전핀 · 폭풍 %ile 금액 감산 스케일). 리스크 데스크는 매 보고서 Task 0에서
#     그 파일을 읽으므로 **폐기된 룰을 계속 적용할 뻔했다.**
#     원인은 단순하다 — 룰 개정이 CLAUDE.md·crash_tf엔 반영됐는데 playbook까지 안 내려왔다.
#     정본이 여러 개(CLAUDE.md·crash_tf·playbook·agent 파일·SKILL)인데 **개정 전파를 검증하는
#     기계가 없었다.** 이 검사가 그 기계다.
#
# 설계에서 제일 중요한 건 **오탐을 안 내는 것**이다. 정정 노트는 폐기 문구를 일부러 인용하고
# ("❌ 舊 '안전핀 7,500'은 폐기"), 7,500은 §5 해제 게이트로는 **아직 살아 있다**.
# 그래서 단순 grep은 소음이 되고, 소음이 되면 사람이 이 검사를 꺼버린다 → 없느니만 못하다.
#   ⇒ 같은 줄에 **폐기 표식**(폐기·舊·❌·정정·승계·대체·오독)이나 **허용 맥락**이 있으면 통과.
#   ⇒ 현재 유효한 용법이 전혀 없는 패턴만 FAIL, 문맥에 따라 갈리는 건 WARN.
_REPEAL_MARK = re.compile(r"폐기|舊|❌|정정|승계|대체|오독|stale|아니다|였다|금지")
# 과거 사실을 적어둔 **기록**은 고치면 안 된다 — 그날의 판단 기록을 위조하는 셈이다.
# (예: master §검증로그 "2026-06-16 … 안전핀(7,500) 미발동" = 그때는 실제로 유효했던 룰)
_HISTORICAL = re.compile(
    r"\[(검증|정정|미확인)[,\s]|미발동|당시|그때|\bv\d+\]"
    # 날짜로 시작하는 표 행 = 결정로그·이력 항목(master §9 등). 그날의 판단 기록이므로 불가침.
    r"|^\s*\|\s*20\d\d-\d\d-\d\d\s*\|")

# (이름, 탐지 패턴, 허용 맥락 패턴|None, 심각도, 무엇으로 대체됐나)
REPEALED_RULES = [
    ("룰1 매수 안전핀 7,500 (7/30 폐기)",
     # ★[8/23] 창을 20→60자로 넓힘 — risk-desk.md의 영문 서술
     #   ("매수 안전핀: when 코스피 falls **below 7,500**")이 20자 창을 넘겨 **7주간 통과**했다.
     #   같은 파일 아래쪽엔 "舊 안전핀은 폐기"라고 적혀 있었는데 절대룰 블록만 옛 문구였다(손으로 발견).
     re.compile(r"안전핀[^\n]{0,60}7[,.]?500|7[,.]?500[^\n]{0,40}안전핀"),
     # 7,500은 §5 **해제 게이트 조건①**로만 유효하다.
     # ⚠️ 초판은 허용어에 '해제'를 단독으로 넣어 crash_tf §6("…하드 플로어 그대로 … 해제 후 각 트랜치")을
     #    통째로 면제해버렸다(8/5 실측 false negative). 게이트 맥락을 **구체적으로** 요구한다.
     re.compile(r"해제\s*게이트|게이트\s*조건|조건\s*①|해제\s*3중|L0\b|above|종가\s*회복|게이트①"),
     "warn",
     "낙폭 사다리(tranche_rules.py) + 하드플로어 = S&P500 폭풍 ≥70%ile"),

    ("폭풍 %ile 트랜치 '금액' 감산 스케일 (7/30 2차 개정으로 전면 폐기)",
     # 이 숫자 조합은 현재 유효한 용법이 전혀 없다 → 발견 즉시 FAIL.
     # 산문형("75~90=75%")과 **마크다운 표형**(| 90~97 | 폭풍 | **50%** |) 둘 다 잡는다.
     # 표형을 빠뜨려 crash_tf §6 감산표가 통과했다(8/5 실측 false negative).
     re.compile(r"(75%\s*=\s*100%|90~97\s*=\s*50%|>?\s*97\s*=\s*25%|극단\s*>\s*97"
                r"|\|\s*90~97\s*\||\|\s*>\s*97\s*\||\|\s*75~90\s*\|)"),
     None, "fail",
     "폭풍은 이제 **분할 횟수만** 바꾼다(≥97 4분할/90~97 3분할/<90 2분할, 총액 불변)"),

    ("§5b '숨구멍'(폭풍<90 시 25% 1회) — 룰1 개정과 함께 폐기 (7/30)",
     re.compile(r"§?\s*5b[^\n]{0,20}(숨구멍|폭풍)|숨구멍"),
     None, "warn",
     "낙폭 사다리가 단계별 해금을 대신한다 — 별도 '1회 예외' 조항 없음"),

    ("사다리 '첫 도달 시 해금' 래칫 오독 (7/31 RESET 정책으로 정정)",
     re.compile(r"첫\s*도달\s*시\s*해금"),
     None, "fail",
     "해금은 **현재 낙폭 기준 매일 재계산**(되돌리면 다시 잠긴다) — ratchet_test.py"),

    ("국내 펀더 = WebSearch 폴백 (7/30 폐기)",
     re.compile(r"국내(주)?[^\n]{0,24}(FMP\s*미지원|WebSearch\s*폴백)"),
     None, "fail",
     "국내도 Yahoo·DART 하드넘버가 1차(financials.py)"),

    ("한국은행 점도표 미발표 (7/7 정정)",
     re.compile(r"한(국)?은[^\n]{0,16}점도표[^\n]{0,16}(미발표|없|안\s*함)"),
     None, "fail",
     "한은은 2026-02부터 자체 점도표 발표(경제전망월 2·5·8·11월)"),

    ("CXMT = 저가 공세/반값 (7/29 정정)",
     re.compile(r"CXMT[^\n]{0,40}(반값|저가\s*공세|싸게|저가로)"),
     None, "fail",
     "CXMT는 삼성보다 **비싸게** 판다 — 우위는 가격이 아니라 물량"),
]

# 데스크·PM이 실제로 읽는 정본만 스캔한다(보고서 본문은 그날의 기록이므로 제외 —
# 과거 보고서를 고치면 그날의 판단 기록을 위조하는 셈이다).
REPEAL_SCAN = [
    "CLAUDE.md", "docs/desk_playbook.md", "docs/crash_tf.md", "docs/master.md",
    "docs/routines.md", "docs/data_coverage.md",
]
# ★[8/23] 舊 목록은 portfolio-desk 하나만 봤다 → quick-check/SKILL.md가 "안전핀 7,500 하회 시 전면 동결"을
#   현행처럼 적고 있었는데 스캔 밖이라 안 걸렸다. 스킬은 계속 늘어나므로 **하드코딩 대신 열거**한다.
_SKILLS_DIR = os.path.join(ROOT, ".claude", "skills")
if os.path.isdir(_SKILLS_DIR):
    REPEAL_SCAN += [os.path.join(".claude", "skills", d, "SKILL.md")
                    for d in sorted(os.listdir(_SKILLS_DIR))
                    if os.path.exists(os.path.join(_SKILLS_DIR, d, "SKILL.md"))]

def check_score_basis():
    """[8/7 신설] score ↔ fund_subscore 괴리 게이트.

    규약은 *"스코어 = 별점의 정량 근거, 펀더 서브스코어가 1차"*인데, 실제로는
    **별점을 먼저 올리고 스코어를 밴드에 맞춰 사후 정당화한** 사례가 확인됐다
    (NAVER 7/30 ⭐4 승격 시 score 68 = ⭐3 밴드 위반 → 7/31 score를 70(⭐4 하한)으로 조정).
    8/7 실측: 보유 14종 중 **6종이 괴리 ≥10p**, 최대 현대차 +24.2p.

    N·L·M(신제품·주도주·시장방향)은 PM 판단이라 괴리 자체는 정상이다. 다만
    **밴드를 바꿀 만큼 큰 괴리는 근거가 문서화돼야** 한다 → score_rationale 요구.
    """
    d = load("data/app/stocks.json")
    if not d:
        return

    def band(s):
        return 5 if s >= 85 else 4 if s >= 70 else 3 if s >= 55 else 2 if s >= 40 else 1

    # ── 0단계: fund_subscore가 financials.json 최신값과 같은가 ──────────────
    # [8/7 실사고] stocks.json의 fund_subscore는 **손으로 복사한 사본**이라
    # financials.py 재실행 뒤 동기화를 빼먹으면 조용히 낡는다. 실측: ORCL 68.8→54.3,
    # ANET 72.1→86.9로 **둘 다 14.5p 어긋난 채** 괴리 검사를 통과하고 있었다
    # (ORCL은 없는 괴리가 보이고, ANET은 있는 괴리가 숨었다 = 양방향 오판).
    fin = load("data/app/financials.json") or {}
    fstocks = fin.get("stocks") or {}
    for tk, v in (d.get("stocks") or {}).items():
        rec, cur = v.get("fund_subscore"), (fstocks.get(tk) or {}).get("fund_subscore")
        if not isinstance(rec, (int, float)) or not isinstance(cur, (int, float)):
            continue
        if abs(rec - cur) >= 1.0:
            fail(f"{tk}: fund_subscore {rec} ≠ financials.json {cur:.1f} "
                 f"({cur - rec:+.1f}p stale) — financials.py 실행 후 stocks.json 동기화 누락. "
                 "이 값이 틀리면 아래 괴리 검사 전체가 오판한다")

    for tk, v in (d.get("stocks") or {}).items():
        s, f = v.get("score"), v.get("fund_subscore")
        if s is None or f is None:
            continue
        gap = s - f
        if abs(gap) < 15:
            continue
        moved = band(s) != band(f)
        why = (v.get("score_rationale") or "").strip()
        msg = (f"{tk}: score {s} vs 펀더 서브스코어 {f:.1f} = {gap:+.1f}p 괴리"
               + (f" (밴드 ⭐{band(f)}→⭐{band(s)} 이동)" if moved else ""))
        if not why:
            fail(msg + " — 밴드를 바꿀 괴리엔 score_rationale 필수"
                       "(펀더가 1차 근거·N/L/M 가산은 근거를 적을 것)")
        else:
            warn(msg + " — 근거 있음, 타당성 재확인")


# 목표가 근거(target_basis) 의무화 유예 기한 — 이 날부터 미기재는 FAIL.
# 기한을 코드에 박는 이유: "나중에 채우자"가 정확히 ORCL을 한 달 방치한 방식이다.
TARGET_BASIS_DEADLINE = "2026-08-22"
TARGET_BASIS_WARN_AGE = 30      # 근거가 이만큼 낡으면 재산정 검토
TARGET_BASIS_FAIL_AGE = 60      # 이만큼 낡으면 목표가를 못 믿는다


def check_target_basis():
    """[8/8 신설·정훈 지시] 목표가 산정 근거 의무화 게이트.

    ORCL 실패 재발방지: 목표가 $225~268이 7/14부터 **한 달간 'stale 의심' 딱지만 달린 채
    한 번도 재산정되지 않았다.** 그 사이 실제 컨센은 ~$155로 내려와 -31~-42% 괴리가 났다.
    원인은 **목표가가 숫자만 있고 근거가 보고서 산문에 흩어져 있어** 무엇이 낡았는지
    기계가 볼 수 없었던 것.

    ⇒ `target_basis`(산정식·앵커·배수·날짜)를 종목 데이터에 붙이고 나이를 잰다.

    판정 3단:
      ① 목표가에 **stale/의심/극단/실적전** 딱지가 있는데 근거가 없다 → **즉시 FAIL**
         (딱지는 경고이지 수정이 아니다 — 유예 대상 아님)
      ② 근거 없음 → 유예기한 전 WARN(D-n 표시) / 기한 후 FAIL
      ③ 근거 있음 → 날짜 파싱해 30일+ WARN · 60일+ FAIL
    면제: 목표가에 숫자가 없는 것(ETF·"분산 큼" 등 정량 목표가 아닌 경우).
    """
    d = load("data/app/stocks.json")
    if not d:
        return
    today = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).date()
    deadline = dt.date.fromisoformat(TARGET_BASIS_DEADLINE)

    for tk, v in (d.get("stocks") or {}).items():
        tgt = str(v.get("target") or "")
        if not re.search(r"\d", tgt):        # 정량 목표가가 아니면 면제
            continue
        basis = (v.get("target_basis") or "").strip()
        tag = re.search(r"stale|의심|극단|실적전", tgt)

        if not basis:
            if tag:
                fail(f"{tk}: 목표가에 '{tag.group(0)}' 경고가 붙었는데 target_basis 없음 — "
                     f"딱지는 경고이지 수정이 아니다(ORCL 8/8 교훈). 재산정하고 근거를 남길 것")
            elif today >= deadline:
                fail(f"{tk}: target_basis 없음 — 목표가 근거 의무화 기한"
                     f"({TARGET_BASIS_DEADLINE}) 경과")
            else:
                warn(f"{tk}: target_basis 없음 — 의무화 D-{(deadline - today).days}"
                     f"({TARGET_BASIS_DEADLINE}부터 FAIL). 산정식·앵커·배수·날짜를 적을 것")
            continue

        m = re.search(r"(\d{4}-\d{2}-\d{2})", basis)
        if not m:
            warn(f"{tk}: target_basis에 산정일(YYYY-MM-DD) 없음 — 나이를 잴 수 없다")
            continue
        try:
            age = (today - dt.date.fromisoformat(m.group(1))).days
        except ValueError:
            warn(f"{tk}: target_basis 산정일 '{m.group(1)}' 파싱 불가")
            continue
        if age >= TARGET_BASIS_FAIL_AGE:
            fail(f"{tk}: 목표가 근거가 {age}일 경과({m.group(1)}) — 재산정 필수")
        elif age >= TARGET_BASIS_WARN_AGE:
            warn(f"{tk}: 목표가 근거 {age}일 경과({m.group(1)}) — 재산정 검토")


def check_setups():
    """[8/7 신설] 경제사냥꾼 조건 트래커(setups) 게이트 — setup_schema.py 감사 재사용.

    정훈 6/28 지시 = *"조건 ~75%+ 충족 & 가격존 진입 시 지정가 발동"* 인데,
    8/6 감사에서 **그 75%를 아무도 계산하지 않고 있었다**(updated 0/19·met_pct 필드
    없음·orders 26건 전부 setup_id 없음). 8/2 "산문 8~9회 vs 오더 0회"와 같은 구조 =
    판단은 있는데 기계에 안 실린다. 여기서 매 보고서마다 기계가 센다.

    FAIL = 스키마 결손(필수 필드·met_pct 불일치·비표준 status) → --migrate로 해소.
    WARN = 운영 신호(stale·기한경과 미채점·발동권 도달인데 오더 미배선) → 사람이 판단.
    """
    try:
        sys.path.insert(0, os.path.join(ROOT, ".claude/skills/portfolio-desk/scripts"))
        import setup_schema
    except Exception as e:
        warn(f"setup_schema 로드 실패 — 셋업 게이트 생략 ({e})")
        return
    try:
        fails, warns = setup_schema.check(quiet=True)
    except Exception as e:
        warn(f"셋업 감사 실패 ({e})")
        return
    for m in fails:
        fail(m)
    for m in warns:
        warn(m)


def check_rule_ledger(latest=None):
    """[8/6 신설] 룰1 낙폭 사다리 원장(rule_log.jsonl) 신선도 게이트.

    룰1은 7/31 RESET 정책으로 **매일 재계산**이 전제다(되돌리면 다시 잠긴다).
    그런데 원장은 7/30 1건에서 멈춰 있었다 — 그 1건이 말하는 상태
    (해금 35%·상한 282,438원·halted=false)와 8/6 실제
    (해금 15%·상한 0원·하드플로어 halted=true)가 정반대였다.
    원장을 읽는 쪽(self-review §8 룰 추적·rule_tracker --score)이 통째로 옛 상태를
    보게 되므로, 보고서 날짜와 원장 최신일이 어긋나면 경고한다.
    """
    p = os.path.join(ROOT, "data/app/rule_log.jsonl")
    if not os.path.exists(p):
        warn("rule_log.jsonl 없음 — 룰1 사다리 원장 미기록(rule_tracker.py --snapshot)")
        return
    dates = []
    for ln in open(p, encoding="utf-8"):
        if not ln.strip():
            continue
        try:
            dates.append(json.loads(ln).get("date"))
        except Exception:
            continue
    dates = sorted(d for d in dates if d)
    if not dates:
        warn("rule_log.jsonl 비어 있음 — 룰1 사다리 원장 미기록")
        return
    last = dates[-1]
    # 최신 보고서 날짜와 비교 (보고서가 있으면 그날, 없으면 오늘 KST)
    ref = None
    if latest:
        rel = latest_report_path(latest)
        if rel:
            m = re.search(r"(\d{4}-\d{2}-\d{2})", rel)
            if m:
                ref = m.group(1)
    if not ref:
        ref = (dt.datetime.now(dt.timezone.utc)
               + dt.timedelta(hours=9)).date().isoformat()
    if last < ref:
        gap = (dt.date.fromisoformat(ref) - dt.date.fromisoformat(last)).days
        msg = (f"rule_log 최신 {last} < 보고서 {ref} ({gap}일 정지) — "
               "룰1은 RESET 정책상 매일 재계산이 전제다. "
               "rule_tracker.py --snapshot 미실행 = 사다리 상태가 옛날 값으로 읽힌다")
        (fail if gap >= 3 else warn)(msg)


def check_git_depth():
    """[8/6 신설] 얕은 클론 감지 — git 히스토리를 소급 재구성하는 도구의 안전장치.

    원격/웹 세션은 레포를 얕게 클론한다(실측 8/6: 50커밋·최古 8/3 = 3일치).
    그런데 `score_calls.py --backfill`(R3 주말루틴)은 git 히스토리에서 콜 원장을
    복원하므로, 얕은 상태로 돌리면 원장이 그 며칠치로 잘린다
    (실측: 135콜 중 75콜 = 7/28~8/1 소실 예정이었다).
    self-review §1의 '2~3주 전 커밋 복원'도 같은 이유로 불가능해진다.
    ⇒ 얕으면 경고하고 `git fetch --unshallow origin`을 안내한다.
    """
    try:
        out = subprocess.run(["git", "-C", ROOT, "rev-parse", "--is-shallow-repository"],
                             capture_output=True, text=True, timeout=20)
    except Exception:
        return
    if out.stdout.strip() != "true":
        return
    warn("git 얕은 클론(shallow) — 히스토리 소급 도구가 잘린 범위만 본다. "
         "`git fetch --unshallow origin` 후 작업할 것 "
         "(score_calls --backfill·self-review §1 콜 스냅샷 복원이 영향)")


def check_trade_ledger():
    """[8/23 신설] 체결 원장 ↔ portfolio.json 대사 게이트.

    master.md §2가 **같은 결함을 두 번** 기록했다 — 8/6 GOOGL 매수가 1주일, 8/19 ANET 전량매도·VOO
    적립체결이 8일간 산문 표에 반영 안 됨. 그때 결론이 *"산문 표는 기계가 안 보므로 validate_report도
    못 잡는다 ⇒ 다짐이 아니라 절차로 막는다"*였는데, **절차(한 커밋에 세 곳 동시수정)는 사람이 지키는
    것**이라 같은 다짐을 적어둔 뒤에 재발했다.

    이제 원장(trades.jsonl)이 정본이고 수량·평단은 재생된 파생물이다 → 기입을 빠뜨리면 **수량이 안 맞는다.**
    그 불일치를 여기서 FAIL로 잡는다(허용오차: 수량 1e-6주·평단 0.5%).

    ⚠️ FAIL이 떴을 때 고칠 곳은 **둘 중 하나**다 — 원장에 체결을 안 넣었거나(대부분), 장부가 틀렸거나.
       `python3 trades.py --reconcile`로 어느 종목인지 보고, 체결이면 `trades.py --add`로 먼저 원장에 넣는다.
    """
    import subprocess
    script = os.path.join(ROOT, ".claude", "skills", "portfolio-desk", "scripts", "trades.py")
    if not os.path.exists(script) or not os.path.exists(os.path.join(ROOT, "data", "app", "trades.jsonl")):
        return  # 원장 미도입 상태면 조용히 통과(하위호환)
    try:
        r = subprocess.run([sys.executable, script, "--json"], capture_output=True, text=True, timeout=60)
        data = json.loads(r.stdout) if r.stdout.strip() else {}
    except Exception as e:  # noqa: BLE001
        WARNS.append(f"체결 원장 대사를 실행하지 못했다 ({e}) — trades.py --reconcile 수동 확인")
        return
    bad = [x for x in (data.get("reconcile") or []) if x.get("status") == "diff"]
    if bad:
        for x in bad:
            FAILS.append(f"체결 원장 불일치 — {x['label']}: {x['detail']} "
                         f"(원장 기입 누락이거나 portfolio.json이 틀렸다. trades.py --reconcile 참조)")
    else:
        n = (data.get("summary") or {}).get("fills")
        print(f"  ✅ 체결 원장 대사 일치 (체결 {n}건 재생 = portfolio.json)")


def check_repealed_rules():
    """정본 문서에 **폐기된 룰**이 살아 있는지 감지 [8/5 신설].

    데스크는 매 보고서 Task 0에서 playbook·agent 파일을 읽는다 → 거기 남은 폐기 룰은
    조용히 계속 적용된다. 개정이 한 정본에만 반영되고 나머지에 안 내려오는 게 실제 사고였다."""
    targets = list(REPEAL_SCAN)
    agents = os.path.join(ROOT, ".claude", "agents")
    if os.path.isdir(agents):
        targets += [os.path.join(".claude", "agents", f)
                    for f in sorted(os.listdir(agents)) if f.endswith(".md")]

    for rel in targets:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        try:
            lines = open(p, encoding="utf-8").read().splitlines()
        except OSError:
            continue
        # 舊 원문을 일부러 보존한 아카이브 블록은 통째로 제외.
        #   <details><summary>舊 §5b 원문 (… 이력 보존)</summary> … </details>
        # 줄 단위 판정만으론 블록 **안쪽** 줄에 폐기 표식이 없어 전부 걸린다(8/5 실측 2건).
        # 이력 보존은 의도된 것이므로 지우면 안 된다 — 왜 폐기했는지의 근거가 사라진다.
        archived = set()
        depth, opened_as_archive = 0, False
        for i, ln in enumerate(lines, 1):
            low = ln.lower()
            if "<details" in low:
                depth += 1
                if depth == 1:
                    opened_as_archive = bool(_REPEAL_MARK.search(ln) or "이력" in ln)
            if depth >= 1 and opened_as_archive:
                archived.add(i)
            if "</details>" in low:
                depth = max(0, depth - 1)
                if depth == 0:
                    opened_as_archive = False

        for name, pat, allow, sev, replaced_by in REPEALED_RULES:
            for i, ln in enumerate(lines, 1):
                if i in archived:
                    continue
                if not pat.search(ln):
                    continue
                # 폐기 표식이 같은 줄에 있으면 '정정 기록'이므로 정상
                if _REPEAL_MARK.search(ln):
                    continue
                # 과거 사실 기록(날짜 태그·미발동 등)은 고치는 게 오히려 위조
                if _HISTORICAL.search(ln):
                    continue
                # 허용 맥락(예: 7,500 = §5 해제 게이트)이면 정상
                if allow and allow.search(ln):
                    continue
                msg = (f"{rel}:{i} 폐기된 룰이 살아 있다 — {name}. "
                       f"현행 = {replaced_by}. "
                       f"(데스크가 Task 0에서 이 파일을 읽으므로 폐기 룰이 계속 적용된다)")
                (fail if sev == "fail" else warn)(msg)

def check_coverage():
    """데이터 **레이어**의 결손·신선도 감사 — 보고서와 무관하게 단독 실행.

    [7/30 신설] 기존 게이트는 '보고서'만 봤다. 재무제표가 두 달간 0건이었는데도 매일 PASS가
    난 이유다. 이 감사는 **산출물이 존재하는가 · 오늘 것인가**를 레이어별로 본다.
    주간 R3(토 09:00)에서 콜 채점과 **함께** 돌린다 — 콜 채점은 '우리가 낸 답'만 검사하므로
    '애초에 못 낸 답'은 이 감사가 아니면 영원히 안 보인다.
    """
    today = dt.date.today()
    print("\n" + "=" * 66)
    print("  데이터 레이어 감사 (--coverage) — docs/data_coverage.md §1~§3")
    print("=" * 66)
    print(f"  기준일 {today} · 형식: 레이어 | 갱신일 | 지연 | 상태\n")

    for fn, max_age, how, why in COVERAGE_LAYERS:
        p = os.path.join(ROOT, "data", "app", fn)
        if not os.path.exists(p):
            fail(f"[레이어 결손] {fn} 없음 — `{how}` 실행 필요 ({why})")
            print(f"  ❌ {fn:<18} 없음                    → {how}")
            continue
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:
            fail(f"[레이어 손상] {fn} 파싱 실패: {str(e)[:60]}")
            print(f"  ❌ {fn:<18} 파싱실패")
            continue
        raw = str((d.get("updated") or d.get("as_of") or d.get("date") or ""))[:10]
        m = re.match(r"\d{4}-\d{2}-\d{2}", raw)
        if not m:
            warn(f"[레이어 신선도] {fn}에 날짜 필드 없음 — stale 감지 불가")
            print(f"  ⚠️  {fn:<18} 날짜필드 없음")
            continue
        age = (today - dt.date.fromisoformat(m.group(0))).days
        if age > max_age:
            fail(f"[레이어 stale] {fn} {age}일 경과(허용 {max_age}일) — `{how}` 재실행 ({why})")
            mark = "❌"
        elif age > max_age // 2 and max_age > 2:
            warn(f"[레이어 노후] {fn} {age}일 경과(허용 {max_age}일)")
            mark = "⚠️ "
        else:
            mark = "✅"
        print(f"  {mark} {fn:<18} {m.group(0)}  {age:>3}일 경과 (허용 {max_age})")

    # 재무제표 커버리지(종목 단위)는 기존 검사 재사용
    check_financials(None)

    print("\n  🚨 미보유 레이어(아직 없는 것) — docs/data_coverage.md §3에서 우선순위 재평가할 것.")
    print("     '있는 것 목록'이 아니라 '없는 것 목록'이 이 감사의 핵심이다.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="검사할 보고서 .md (생략 시 최신 자동)")
    ap.add_argument("--no-report", action="store_true", help="보고서 파일 검사 생략")
    ap.add_argument("--coverage", action="store_true",
                    help="데이터 레이어 감사만 수행(보고서 검사 생략) — 주간 R3 역량 감사용")
    a = ap.parse_args()

    if a.coverage:
        check_coverage()
        print("=" * 66)
        if FAILS:
            print(f"❌ 레이어 FAIL {len(FAILS)}:")
            for m in FAILS: print(f"   ❌ {m}")
        if WARNS:
            print(f"⚠️  레이어 WARN {len(WARNS)}:")
            for m in WARNS: print(f"   ⚠️  {m}")
        if not FAILS:
            print("✅ 데이터 레이어 결손 없음.")
        print()
        sys.exit(1 if FAILS else 0)

    check_stocks(); check_flows(); check_tasks(); check_order_feasibility(); check_kr_price_band(); check_target_multiple(); check_high_low_claims(); check_history_cache()
    check_low_star_action(); check_pending_decisions(); check_repealed_rules(); check_trade_ledger()
    check_consistency(); check_hunter(); check_setups(); check_score_basis(); check_target_basis()
    check_feeds(); check_guru()
    latest = latest_version(); check_versions(latest); check_freshness(latest)
    check_financials(latest); check_rule_ledger(latest); check_git_depth()
    if not a.no_report:
        rel = a.report or (latest_report_path(latest) if latest else None)
        if rel: check_report(rel); check_prose_order_link(rel)

    print("\n" + "=" * 56)
    print("  보고서 완료-검증 (validate_report.py)")
    print("=" * 56)
    if FAILS:
        print(f"\n❌ FAIL {len(FAILS)} — 고치고 커밋:")
        for m in FAILS: print(f"   ❌ {m}")
    if WARNS:
        print(f"\n⚠️  WARN {len(WARNS)} — 눈으로 확인:")
        for m in WARNS: print(f"   ⚠️  {m}")
    if not FAILS and not WARNS:
        print("\n✅ 완벽 — 보유 전종목·컬럼·별점/스코어·정본 버전 전부 정합. 커밋 OK.")
    elif not FAILS:
        print(f"\n✅ FAIL 없음 — 커밋 OK (WARN {len(WARNS)}건은 판단).")
    print()
    sys.exit(1 if FAILS else 0)

if __name__ == "__main__":
    main()
