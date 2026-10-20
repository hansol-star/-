#!/usr/bin/env python3
"""multiple_backtest.py — 목표가 배수 선택의 역사적 검증 (기다리지 않고 지금 채점)

배경 [8/8 정훈 지적 — "자료들을 구해서 하면 안 되나, 데이터 쌓이길 기다리는 것보다"]:
`target_score.py`는 우리가 낸 목표가를 사후 채점하지만 원장이 6/20 시작이라
**20거래일 지평 하나**뿐이다. 12개월 목표를 제대로 채점하려면 몇 달을 기다려야 한다.
⇒ 기다리는 대신 **우리 방법론(EPS × 배수)을 과거에 적용해** 지금 검증한다.

데이터는 이미 있다: 가격은 수십 년(`data/history/`, MSFT 1986~·MU 1984~),
EPS는 EDGAR companyfacts가 **전 시계열**을 준다(무키). `financials.json`이 5기/8기로
자를 뿐 원본은 깊다 — 여기서는 `edgar_facts.fetch()`로 직접 받는다.

방법:
  ① 분기 희석EPS → **TTM EPS**(4분기 롤링) 시계열 구성
  ② 각 시점 T에서 합성 목표가 = TTM_EPS(T) × 배수 m  (m을 격자로 훑는다)
  ③ T+horizon(기본 250거래일 ≈ 12개월) 실제 주가와 대조
  ④ **오차를 최소화하는 m** = 그 종목의 '역사적으로 정당했던 배수'
  ⑤ 우리가 지금 쓰는 배수가 그 분포의 어디인지 백분위로 표시

핵심 산출 = **우리 배수가 역사적 정당 구간 안인가, 위인가.**
위면 낙관 편향이 배수 선택에서 온다는 뜻이고, 안이면 편향의 원인은 EPS 추정 쪽이다.

⚠️ 한계(반드시 같이 읽을 것):
  · TTM EPS(후행)로 검증한다. 실제 우리 목표가는 **컨센 EPS(선행)** 기반이라 축이 다르다.
    ⇒ 이 결과는 '배수 자체의 타당 범위'이지 우리 목표가의 정오 판정이 아니다.
  · 생존편향 없음(보유 종목만 봄 = 이미 살아남은 기업). 절대 수준을 일반화하지 말 것.
  · 국내주는 EDGAR 미대상이라 제외(EPS 깊은 이력이 없다).

★[10/14] TTM 정의 수정 — **회계 4분기가 영원히 빠진 합이었다.**
  EDGAR엔 4분기 분기 팩트가 없다(10-K는 연간만 태깅). 舊 코드는 80~100일 팩트만 모아
  **위치로 4개**를 더했으므로 TTM이 'FQ3+FQ2+FQ1+**전년 FQ3**'였다 — 이익이 급증하는 국면에서
  크게 과소(MU 43.02 ↔ 실제 FY26 74.33) → 내재배수 과대 → '상단초과' 판정이 부풀었다.
  ⇒ ① 4분기 EPS = **연간 EPS − 1~3분기 EPS**(그 해 세 분기가 다 있고 간격이 한 분기일 때만)
       → 회계연도 말의 TTM이 **신고된 연간 EPS와 정확히 같아진다.**
     ② TTM은 **분기말 간격으로 연속이 확인된 4개 분기**만 더한다(이가 빠진 창은 버린다).
     ③ 디스크 캐시에 버전·수명을 뒀다(舊엔 만료가 없어 9/17 값이 그대로 굳어 있었다).
  자가검증 = `--selftest`(오프라인 픽스처 · guard_selftest 등록). 같은 원인의 다른 자리 =
  `financials.flags()`·`edgar_facts`(docs/lessons.md 10/14).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
HIST = os.path.join(ROOT, "data/history")
CACHE = os.path.join(ROOT, "data/financials/_ttm_cache.json")
sys.path.insert(0, HERE)

QTR_GAP = (80, 100)       # 분기말 간격(일) — 13·14주. edgar_facts.QTR_GAP과 같은 값(--selftest가 대조)
YEAR_SPAN = (350, 380)    # 회계연도 길이(일) — 52·53주
CACHE_VER = 2             # [10/14] TTM 정의가 바뀌었다 — 舊 캐시(4분기가 빠진 합)는 읽지 않는다
CACHE_TTL_DAYS = 6        # 캐시 수명. 舊엔 만료가 없어 한 번 만든 값이 계속 재사용됐다

# 8/8 우리가 채택한 배수 (target_basis 기준) — **선행(컨센) EPS 기준**이다
OURS = {"NVDA": (20, 26), "META": (19, 24), "MSFT": (23, 28), "AAPL": (28, 34),
        "GOOGL": (26, 31), "MU": (7, 10), "AVGO": (22, 27), "ORCL": (14, 17.5),
        "ANET": (40, 47)}
# 8/8 채택 목표가 절대값 — 이걸 최신 TTM EPS로 나눠 **후행 축으로 환산**해야
# 역사 밴드와 사과 대 사과 비교가 된다(아래 §축 정합 참조).
# ⚠️ **폴백 전용이다.** ★[9/19 R3] 舊엔 이게 유일한 소스라, 이 도구가 매주 돌면서도
#    **6주 전(8/8)에 얼어붙은 목표가**를 채점하고 있었다 — ANET은 8/11에 전량 매도해
#    보유도 워치도 아닌데 여전히 '🔴 상단초과'로 찍혔다. 하드코딩 상수는 조용히 거짓말한다
#    (CLAUDE.md 교훈: '인덱스로 라벨을 만들지 말 것'과 같은 클래스 — 모양·상수에 기댄 라벨).
#    ⇒ 1차 소스 = `calls_log.jsonl`의 **종목별 최신 목표가**(아래 latest_targets).
OUR_TARGET_FALLBACK = {"NVDA": (260, 335), "META": (650, 815), "MSFT": (540, 655),
                       "AAPL": (270, 325), "GOOGL": (385, 455), "MU": (1090, 1555),
                       "AVGO": (430, 525), "ORCL": (150, 190), "ANET": (205, 240)}
LEDGER = os.path.join(ROOT, "data/app/calls_log.jsonl")
LIVE_TARGETS: dict = {}    # main()에서 원장으로 채운다 (ticker → (lo, hi, as_of))


def latest_targets():
    """원장에서 종목별 **최신** 목표가 (ticker → (lo, hi, as_of)).

    파서는 `score_calls.rng`를 그대로 쓴다(단위·괄호주석·퍼센트 방어가 거기 있다).
    원장이 없거나 파싱이 안 되면 그 종목만 8/8 폴백으로 내려간다 — 도구가 죽지 않게.
    """
    out = {}
    if not os.path.exists(LEDGER):
        return out
    try:
        from score_calls import rng
    except Exception:
        return out
    for ln in open(LEDGER, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        tk, d, tgt = r.get("ticker"), r.get("date"), r.get("target")
        if not tk or not d:
            continue
        prev = out.get(tk)
        if prev and prev[2] >= d:
            continue
        tr = rng(tgt)
        if tr:
            out[tk] = (tr[0], tr[1], d)
    return out


_SPLIT_CACHE = {}


def yahoo_splits(tk):
    """Yahoo chart API에서 분할 이벤트 [(YYYY-MM-DD, ratio)]. 무키.
    EDGAR EPS(당시 보고치)를 분할조정 가격축에 맞추는 데 쓴다."""
    if tk in _SPLIT_CACHE:
        return _SPLIT_CACHE[tk]
    import urllib.request
    from datetime import datetime, timezone
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.request.quote(tk)
           + "?interval=1d&range=40y&events=split")
    out = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
        res = d["chart"]["result"][0]
        ev = (res.get("events") or {}).get("splits") or {}
        import history_backfill as _hb      # 분할일 = 거래소 현지일 한 벌(10/20) — prices()의 캐시 날짜와 같은 라벨
        off = (res.get("meta") or {}).get("gmtoffset") or 0
        for v in ev.values():
            ts = v.get("date")
            num, den = v.get("numerator"), v.get("denominator")
            if ts and num and den:
                day = _hb.bar_date(ts, off)
                out.append((day, num / den))
    except Exception:
        out = []
    out.sort()
    _SPLIT_CACHE[tk] = out
    return out


def prices(tk):
    p = os.path.join(HIST, tk.replace("^", "_") + ".csv")
    out = []
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    out.append((r["date"], float(r["close"])))
                except (ValueError, KeyError, TypeError):
                    continue
        out.sort()
    return out


def eps_facts(tk):
    """분기 희석EPS를 **(기말, filed, 값)** 으로. companyfacts 재사용(추가 호출 없음).

    ★[8/24] `filed`가 왜 필요한가 — **EDGAR는 분할 후 과거 EPS를 소급 조정해 재보고한다.**
    후속 보고서의 비교 컬럼에 실린 분기만 다시 신고되므로, 한 시계열 안에
    **원본·1차 조정·2차 조정이 섞인다**. NVDA 실측(24분기):
      · 2020-04-26 = 1.47 (원본, filed 2021-05)      → 40배 보정 필요
      · 2020-07-26 = 0.25 (4:1 조정본, filed 2021-08) → 10배만 필요한데 40배 적용 = **4배 과소**
      · 2023-10-29 = 0.37 (10:1 조정본, filed 2024-11) → 보정 불필요한데 10배 적용 = **10배 과소**
    기말일 기준으로 보정하면 6/24분기가 틀린다(PE가 4~10배 과대).
    ⇒ **filed 이후에 일어난 분할만** 적용하는 것이 유일하게 옳은 규칙이다
      (filed 이전 분할은 이미 그 보고값에 반영돼 있다).
    """
    return _eps_rows(tk)[0]


def split_eps_facts(facts):
    """EarningsPerShareDiluted 팩트 목록 → (분기 [(기말, filed, 값)], 연간 [(시작, 기말, filed, 값)]).

    분기 = 80~100일 · 연간 = 350~380일(반기·9개월 누적은 버린다). 같은 기간이 여러 번 신고되면
    **가장 늦게 신고된 값**을 쓴다(분할 소급 조정본 — 위 `eps_facts` 주석). 순수 함수(네트워크 없음).
    """
    q_best, a_best = {}, {}
    for f in facts or []:
        if f.get("form") not in ("10-Q", "10-K"):
            continue
        st, en = f.get("start"), f.get("end")
        if not st or not en:
            continue
        try:
            span = (dt.date.fromisoformat(en) - dt.date.fromisoformat(st)).days
        except ValueError:
            continue
        if QTR_GAP[0] <= span <= QTR_GAP[1]:
            best, key = q_best, en
        elif YEAR_SPAN[0] <= span <= YEAR_SPAN[1]:
            best, key = a_best, (st, en)
        else:
            continue
        prev = best.get(key)
        if prev is None or (f.get("filed") or "") > (prev[0] or ""):
            best[key] = (f.get("filed"), f.get("val"))
    q = sorted((en, fi, v) for en, (fi, v) in q_best.items() if v is not None)
    a = sorted((st, en, fi, v) for (st, en), (fi, v) in a_best.items() if v is not None)
    return q, a


def _eps_rows(tk):
    """(분기, 연간) EPS 팩트. companyfacts를 못 받으면 ([], [])."""
    import edgar_facts as EF
    cik = EF.cik_map().get(tk.upper())
    if not cik:
        return [], []
    try:
        cf = EF.facts_full(cik)            # companyfacts + 미반영 신고 원본 XBRL(10/14 CDNS)
    except Exception:
        return [], []
    units = ((((cf.get("facts") or {}).get("us-gaap") or {})
              .get("EarningsPerShareDiluted") or {}).get("units") or {})
    return split_eps_facts(units.get("USD/shares") or [])


def _days(a, b):
    """두 날짜(ISO) 사이 일수 b − a. 못 읽으면 None."""
    try:
        return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days
    except (TypeError, ValueError):
        return None


def _in_gap(a, b):
    d = _days(a, b)
    return d is not None and QTR_GAP[0] <= d <= QTR_GAP[1]


def quarters_with_q4(q_rows, a_rows, factor_after):
    """분할 보정한 분기 EPS에 **회계 4분기(= 연간 − 1~3분기)** 를 끼워 넣는다 → [(기말, eps, 역산?)].

    조건(하나라도 어긋나면 역산하지 않는다 — 그 4분기는 빈 채로 둔다):
      · 그 회계연도 창(시작 < 분기말 < 기말) 안에 분기 EPS가 **정확히 3개**
      · 시작→1분기말→2분기말→3분기말→기말 네 구간이 모두 한 분기(`QTR_GAP`)
    보정은 **팩트마다 자기 filed 기준**으로 한다(연간 값과 분기 값은 신고일이 달라 분할 반영 여부가 다르다).
    EPS는 원래 가산되지 않지만(분기마다 주식수가 다르다) 이 차분은 업계 관행이고,
    무엇보다 **회계연도 말의 TTM이 신고된 연간 EPS와 정확히 같아진다.**
    """
    adj = {en: v / factor_after(fi or en) for en, fi, v in q_rows if v is not None}
    derived = set()
    for st_, en, fi, v in a_rows:
        if v is None or en in adj:
            continue
        inside = sorted(x for x in adj if st_ < x < en and x not in derived)
        if len(inside) != 3:
            continue
        first = _days(st_, inside[0])
        if first is None or not (QTR_GAP[0] <= first + 1 <= QTR_GAP[1]):   # 시작일은 기간 첫날
            continue
        if not all(_in_gap(x, y) for x, y in zip(inside, inside[1:] + [en])):
            continue
        adj[en] = v / factor_after(fi or en) - sum(adj[x] for x in inside)
        derived.add(en)
    return [(en, adj[en], en in derived) for en in sorted(adj)]


def ttm_from_quarters(qs):
    """[(기말, eps, …)] → TTM [(기말, 4개 분기 합)]. **분기말 간격으로 연속이 확인된 4개**만 더한다.

    舊 코드는 리스트 위치로 4개를 더했다 — 분기가 하나 빠지면 5분기 전 값이 섞여도 몰랐다.
    """
    out = []
    for i in range(3, len(qs)):
        win = qs[i - 3:i + 1]
        if any(w[1] is None for w in win):
            continue
        if not all(_in_gap(win[k][0], win[k + 1][0]) for k in range(3)):
            continue
        ttm = sum(w[1] for w in win)
        if ttm > 0:                       # 적자 구간은 PE가 의미 없다
            out.append((win[-1][0], ttm))
    return out


def _legacy_ttm(q_rows, factor_after):
    """舊 정의(위치로 4개 합 · 4분기 없음). `--selftest`가 픽스처가 진짜 함정인지 확인하는 데만 쓴다."""
    adj = [(d, (v / factor_after(fi or d)) if v is not None else None) for d, fi, v in q_rows]
    out = []
    for i in range(3, len(adj)):
        vals = [adj[j][1] for j in range(i - 3, i + 1)]
        if any(v is None for v in vals):
            continue
        if sum(vals) > 0:
            out.append((adj[i][0], sum(vals)))
    return out


def load_cache(path=None, today=None):
    """디스크 캐시 — **버전이 같고 CACHE_TTL_DAYS 안에 만든 것**만 쓴다. 아니면 빈 dict(다시 받는다)."""
    path = path or CACHE
    today = today or dt.date.today()
    try:
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError):
        return {}
    meta = c.get("_meta") if isinstance(c, dict) else None
    if not isinstance(meta, dict) or meta.get("ver") != CACHE_VER:
        return {}
    try:
        age = (today - dt.date.fromisoformat(meta.get("built") or "")).days
    except ValueError:
        return {}
    return c if 0 <= age <= CACHE_TTL_DAYS else {}


def save_cache(cache, path=None, today=None):
    path = path or CACHE
    meta = cache.get("_meta") if isinstance(cache.get("_meta"), dict) else {}
    cache["_meta"] = {"ver": CACHE_VER,
                      "built": meta.get("built") or (today or dt.date.today()).isoformat()}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f)


def ttm_series(tk, cache):
    """분기 희석EPS → TTM EPS [(기말일, ttm_eps)]. EDGAR 전 시계열 사용.

    ⚠️ [8/8 보정 → 8/24 정정] **주식분할**. Yahoo 가격 이력은 분할조정(현재 주식수 기준)이다.
    8/8엔 "EDGAR EPS는 **당시 보고치**"라 전제하고 기말일 기준으로 나눴는데, 그 전제가 반만 맞다 —
    **EDGAR는 분할 후 과거 EPS를 소급 조정해 재보고**하므로 한 시계열에 원본과 조정본이 섞인다.
    기말일 기준 보정은 이미 조정된 분기를 **또** 나눠 NVDA 24분기 중 6개를 4~10배 과소로 만들었다.
    ⇒ 8/24부터 **filed(보고일) 기준**으로 그 이후 분할만 적용한다(`eps_facts` 주석). 그대로 PE를 만들면 분할한 종목이 전부 망가진다 —
    첫 실행에서 NVDA 실현PE **1.6배**, AAPL 4.7, GOOGL 2.3처럼 불가능한 값이 나왔고
    '상단초과' 5종목이 정확히 분할 종목이었다.
    ⇒ 분할 이력을 **Yahoo에서 직접** 받아(무키·권위 있음) 그 시점 이전 EPS를
      누적 분할배수로 나눈다.
      ⚠️ `shares_diluted` 급등으로 추론하는 방식은 **실패했다**(1차 시도) —
      GOOGL은 초기 주식수가 아예 `None`이라 2022년 20:1 분할을 못 잡았고(실현PE 2.3),
      AAPL은 대규모 자사주 매입이 섞여 배수가 어긋났다(6.6). 추론 대신 실제 이벤트를 쓴다.
    """
    if tk in cache:
        return [(d, v) for d, v in cache[tk]]
    rows, annual = _eps_rows(tk)           # [(기말, filed, 값)] · [(시작, 기말, filed, 값)]
    if not rows:                           # 폴백 — filed를 못 얻으면 기존 경로(정확도 낮음)
        import edgar_facts
        rec = edgar_facts.fetch(tk)
        q = rec.get("quarterly") or []     # 여긴 4분기가 이미 역산돼 있다(q4_derived · EPS 근사)
        rows = [(x["end"], None, x.get("eps_diluted"))
                for x in sorted(q, key=lambda z: z["end"]) if x.get("eps_diluted")]
        annual = []

    splits = yahoo_splits(tk)              # [(YYYY-MM-DD, ratio)]

    def factor_after(d):
        """d **이후** 일어난 분할의 누적배수. d = 보고일(filed)이지 기말일이 아니다.
        기말일을 쓰면 '기말 후 재보고로 이미 조정된 값'을 또 나눠 이중 조정된다(8/24 실측)."""
        f = 1.0
        for sd, r in splits:
            if sd > d:
                f *= r
        return f

    # filed가 없으면(폴백) 기말일로 근사 — 부정확할 수 있음을 감수
    # ★[10/14] 4분기를 연간에서 역산해 끼우고, 연속 4개 분기만 더한다(모듈 독스트링).
    out = ttm_from_quarters(quarters_with_q4(rows, annual, factor_after))
    cache[tk] = out
    return out


def backtest(tk, cache, horizon=250, grid=None):
    """각 분기말 T에서 'TTM_EPS × m'이 T+horizon 실제가와 얼마나 맞았나."""
    grid = grid or [x / 2 for x in range(4, 121)]      # 2.0 ~ 60.0배, 0.5 간격
    px = prices(tk)
    ttm = ttm_series(tk, cache)
    if not px or len(ttm) < 6:
        return None
    dates = [d for d, _ in px]

    pairs = []          # (eps, 미래가)
    for end, eps in ttm:
        i = next((k for k, d in enumerate(dates) if d >= end), None)
        if i is None or i + horizon >= len(px):
            continue
        pairs.append((eps, px[i + horizon][1], px[i][1]))
    if len(pairs) < 5:
        return None

    # 각 배수의 중앙 절대 백분율 오차(MAPE) — 이상치에 강하게 중앙값 사용
    best, curve = None, []
    for m in grid:
        errs = [abs(eps * m - fut) / fut for eps, fut, _ in pairs]
        e = st.median(errs)
        curve.append((m, e))
        if best is None or e < best[1]:
            best = (m, e)
    # 오차가 최저의 1.25배 이내인 배수 구간 = '정당 구간'
    lo_e = best[1] * 1.25
    ok = [m for m, e in curve if e <= lo_e]
    # 실현 배수 분포(미래가 ÷ 그때 TTM EPS) — 사후적으로 시장이 매긴 배수
    realized = sorted((fut / eps) for eps, fut, _ in pairs)
    return {"n": len(pairs), "best_m": best[0], "best_err": best[1],
            "band": (min(ok), max(ok)) if ok else None,
            "realized_p25": realized[len(realized) // 4],
            "realized_med": st.median(realized),
            "realized_p75": realized[3 * len(realized) // 4],
            "span": (ttm[0][0], ttm[-1][0])}


def pct_rank(vals, x):
    return 100.0 * sum(1 for v in vals if v <= x) / len(vals)


def _fixture_eps(scale=None, drop_q=(), drop_annual=(), direct_q4=None):
    """오프라인 픽스처 — MU FY24~FY26 실제 희석 EPS(`edgar_facts`의 픽스처와 같은 숫자).

    손잡이: scale {기말: 배수}(그 팩트만 분할 전 스케일로) · drop_q(분기 팩트 제거) ·
    drop_annual(연간 팩트 제거) · direct_q4 {연도말: 값}(4분기를 분기 팩트로 직접 신고).
    반기 누적(6개월) 팩트를 해마다 하나씩 섞는다 — 분기·연간 어느 쪽으로도 새면 안 된다.
    """
    import edgar_facts as EF
    scale = scale or {}
    one = dt.timedelta(days=1)
    facts = []
    for (y0, q_ends, y1, k_filed), (q_eps, a_eps) in zip(EF._FX_YEARS, EF._FX_EPS):
        st_ = y0
        for en, v in zip(q_ends, q_eps):
            if en not in drop_q:
                filed = (dt.date.fromisoformat(en) + dt.timedelta(days=28)).isoformat()
                facts.append({"form": "10-Q", "start": st_, "end": en, "filed": filed,
                              "val": round(v * scale.get(en, 1.0), 4)})
            st_ = (dt.date.fromisoformat(en) + one).isoformat()
        facts.append({"form": "10-Q", "start": y0, "end": q_ends[1],            # 반기 누적(미끼)
                      "filed": (dt.date.fromisoformat(q_ends[1]) + dt.timedelta(days=28)).isoformat(),
                      "val": round(q_eps[0] + q_eps[1], 4)})
        if y1 not in drop_annual:
            facts.append({"form": "10-K", "start": y0, "end": y1, "filed": k_filed,
                          "val": round(a_eps * scale.get(y1, 1.0), 4)})
        if direct_q4 and y1 in direct_q4:
            facts.append({"form": "10-K", "start": st_, "end": y1, "filed": k_filed,
                          "val": direct_q4[y1]})
    return facts


def selftest():
    """TTM이 회계 4분기를 품는가 · 이가 빠진 창을 버리는가 · 캐시가 낡으면 버리는가(오프라인).

    심는 위반 = 실제로 있었던 형태: 분기 팩트엔 4분기가 없는데 위치로 4개를 더한다
    → 'FQ3+FQ2+FQ1+전년 FQ3' = 43.02(10/13까지 캐시에 굳어 있던 MU 값 그대로).
    """
    import tempfile
    import edgar_facts as EF
    print("multiple_backtest 자가검증 — 4분기 역산 TTM · 연속 4개 분기 · 캐시 수명")
    print("=" * 78)
    ok = True

    def check(cond, label, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  {'✅' if cond else '❌'} {label}" + (f" — {detail}" if detail and not cond else ""))

    def near(a, b, tol=0.005):
        return a is not None and abs(a - b) <= tol

    no_split = lambda d: 1.0                                           # noqa: E731
    q, a = split_eps_facts(_fixture_eps())
    check(len(q) == 9 and len(a) == 3, "팩트 분류 — 분기 9 · 연간 3(반기 누적은 버린다)",
          f"분기 {len(q)} · 연간 {len(a)}")
    qs = quarters_with_q4(q, a, no_split)
    by = {en: (v, d) for en, v, d in qs}
    check(near(by.get("2025-08-28", (None,))[0], 2.83) and near(by.get("2026-09-03", (None,))[0], 32.99),
          "4분기 EPS = 연간 − 1~3분기 (FQ4-25 2.83 · FQ4-26 32.99)",
          str({k: round(v[0], 2) for k, v in by.items() if v[1]}))
    check(all(by[e][1] for e in ("2024-08-29", "2025-08-28", "2026-09-03"))
          and sum(1 for v in by.values() if v[1]) == 3, "역산 분기에만 표시가 붙는다")
    ttm = dict(ttm_from_quarters(qs))
    check(near(ttm.get("2025-08-28"), 7.59) and near(ttm.get("2026-09-03"), 74.33),
          "회계연도 말 TTM = 신고된 연간 EPS (7.59 · 74.33)",
          str({k: round(v, 2) for k, v in ttm.items()}))
    check(near(ttm.get("2026-05-28"), 4.60 + 12.07 + 24.67 + 2.83),
          "FQ3-26 TTM은 직전 4개 분기(FQ4-25 포함) 합 = 44.17", str(round(ttm.get("2026-05-28", 0), 2)))
    legacy = dict(_legacy_ttm(q, no_split))
    check(near(legacy.get("2026-05-28"), 43.02) and "2026-09-03" not in legacy,
          "위반 주입 확인 — 舊 위치 합은 같은 입력에서 43.02(전년 FQ3 혼입)이고 연도 말 TTM이 없다",
          str({k: round(v, 2) for k, v in legacy.items()}))

    # 연간 팩트가 없는 해 — 4분기를 못 만들면 그 이를 넘는 창은 버린다(조용히 5분기 전 값을 섞지 않는다)
    q2, a2 = split_eps_facts(_fixture_eps(drop_annual=("2025-08-28",)))
    t2 = dict(ttm_from_quarters(quarters_with_q4(q2, a2, no_split)))
    check(not any(e in t2 for e in ("2025-08-28", "2025-11-27", "2026-02-26", "2026-05-28"))
          and near(t2.get("2026-09-03"), 74.33),
          "연간 팩트 없는 해 — 그 4분기를 넘는 창 4개는 TTM 없음 · 다음 연도 말은 그대로",
          str({k: round(v, 2) for k, v in t2.items()}))
    # 분기 하나가 빠진 해 — '연간 − 두 분기'를 4분기로 둔갑시키지 않는다
    q3, a3 = split_eps_facts(_fixture_eps(drop_q=("2026-02-26",)))
    by3 = {en: v for en, v, d in quarters_with_q4(q3, a3, no_split)}
    t3 = dict(ttm_from_quarters(quarters_with_q4(q3, a3, no_split)))
    check("2026-09-03" not in by3 and not any(e >= "2026-02-26" for e in t3),
          "분기 하나 빠진 해 — 4분기 역산 안 함 · 그 뒤 TTM 없음", str(sorted(t3)))
    # 직접 신고된 4분기가 있으면 그 값이 이긴다
    q4, a4 = split_eps_facts(_fixture_eps(direct_q4={"2026-09-03": 33.10}))
    by4 = {en: (v, d) for en, v, d in quarters_with_q4(q4, a4, no_split)}
    check(near(by4["2026-09-03"][0], 33.10) and not by4["2026-09-03"][1],
          "직접 신고된 4분기가 있으면 역산하지 않는다", str(by4.get("2026-09-03")))
    # 분할 — FQ3-26 기말(5/28)과 그 10-Q 신고(6/25) 사이에 10:1 분할. FQ3 10-Q와 10-K는 분할 뒤 값으로
    # 신고됐고 그 앞 팩트는 분할 전 값이다 → **팩트마다 자기 filed 기준**으로 보정해야 맞는다.
    # (기말일 기준이면 이미 조정된 FQ3를 또 나눠 10배 과소 — 8/24에 실제로 났던 이중 조정)
    pre = {e: 10.0 for y in EF._FX_YEARS[:2] for e in y[1] + [y[2]]}
    pre.update({e: 10.0 for e in EF._FX_YEARS[2][1][:2]})
    q5, a5 = split_eps_facts(_fixture_eps(scale=pre))
    split_day = "2026-06-10"
    after = lambda d: 10.0 if d < split_day else 1.0                   # noqa: E731
    t5 = dict(ttm_from_quarters(quarters_with_q4(q5, a5, after)))
    check(set(t5) == set(ttm) and all(near(t5[k], ttm[k]) for k in ttm),
          "분할(10:1 · 기말과 신고 사이) — filed 기준 보정으로 분할 없는 기준과 TTM 전부 일치",
          str({k: round(v, 2) for k, v in t5.items()}))
    by_end = [(en, None, v) for en, fi, v in q5], [(s, en, None, v) for s, en, fi, v in a5]
    t5e = dict(ttm_from_quarters(quarters_with_q4(by_end[0], by_end[1], after)))
    check(not near(t5e.get("2026-05-28"), ttm["2026-05-28"]),
          "위반 주입 확인 — 같은 픽스처를 기말일 기준으로 보정하면 FQ3-26 TTM이 틀어진다",
          str(round(t5e.get("2026-05-28", 0), 2)))

    # 캐시 — 舊 형식(메타 없음 = 10/13까지의 실제 파일 모양)·버전 불일치·수명 초과는 버린다
    today = dt.date(2026, 10, 14)
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "c.json")

        def put(obj):
            with open(p, "w", encoding="utf-8") as f:
                json.dump(obj, f)

        put({"MU": [["2026-05-28", 43.02]]})
        check(load_cache(p, today) == {}, "캐시 — 메타 없는 舊 파일은 읽지 않는다")
        put({"_meta": {"ver": CACHE_VER - 1, "built": today.isoformat()}, "MU": [["2026-09-03", 1.0]]})
        check(load_cache(p, today) == {}, "캐시 — 버전이 다르면 읽지 않는다")
        old = (today - dt.timedelta(days=CACHE_TTL_DAYS + 1)).isoformat()
        put({"_meta": {"ver": CACHE_VER, "built": old}, "MU": [["2026-09-03", 74.33]]})
        check(load_cache(p, today) == {}, f"캐시 — {CACHE_TTL_DAYS}일 넘으면 읽지 않는다")
        c = {"MU": [["2026-09-03", 74.33]]}
        save_cache(c, p, today)
        got = load_cache(p, today + dt.timedelta(days=CACHE_TTL_DAYS))
        check(got.get("MU") == [["2026-09-03", 74.33]] and got["_meta"]["built"] == today.isoformat(),
              "캐시 — 방금 만든 것은 수명 안에서 다시 읽힌다", str(got))
        again = load_cache(p, today + dt.timedelta(days=3))
        save_cache(again, p, today + dt.timedelta(days=3))
        check(load_cache(p, today + dt.timedelta(days=CACHE_TTL_DAYS + 1)) == {},
              "캐시 — 다시 저장해도 만든 날은 안 늦춰진다(읽을 때마다 수명이 연장되지 않는다)")
    check(QTR_GAP == tuple(EF.QTR_GAP), "분기 간격 상수가 edgar_facts와 같다", f"{QTR_GAP} vs {EF.QTR_GAP}")

    print("=" * 78)
    print("✅ PASS" if ok else "❌ FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tickers", default=",".join(OURS))
    ap.add_argument("--horizon", type=int, default=250, help="검증 지평(거래일·기본 250≈12M)")
    ap.add_argument("--save", action="store_true",
                    help="역사 정당배수 밴드를 data/app/multiple_bands.json에 저장(validate가 소비)")
    ap.add_argument("--selftest", action="store_true",
                    help="오프라인 자가검증 — 4분기 역산 TTM · 연속 4개 분기 · 캐시 수명")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    cache = load_cache()      # 버전·수명이 맞을 때만 재사용(아니면 EDGAR에서 다시 받는다)

    print("=" * 88)
    print(f"  목표가 배수의 역사적 검증 — 지평 +{a.horizon}거래일(≈{a.horizon/250*12:.0f}개월)")
    print("=" * 88)
    print("  방법: 각 분기말 TTM EPS × 배수 = 합성 목표가 → 지평 후 실제가와 대조")
    print("  ⚠️ TTM(후행) 기준이라 '배수의 타당 범위'를 보는 것 — 우리 목표가의 정오 판정이 아니다.\n")
    print(f"  {'종목':8s}{'표본':>5}{'기간':>20}{'역사 정당구간':>12}"
          f"{'실현PE중앙':>10}{'우리목표→TTM':>13}{'판정':>11}")
    print("  " + "-" * 82)

    rows = []
    asofs = []
    LIVE_TARGETS.update(latest_targets())
    for tk in [x.strip() for x in a.tickers.split(",") if x.strip()]:
        try:
            r = backtest(tk, cache, horizon=a.horizon)
        except Exception as e:
            print(f"  {tk:8s}  실패: {str(e)[:50]}")
            continue
        if not r:
            print(f"  {tk:8s}  표본 부족(EPS 이력 또는 지평 미달)")
            continue
        band = r["band"]
        # ★축 정합: 우리 목표가는 **선행 EPS** 기준이라 배수를 그대로 비교하면 안 된다.
        #   목표가 절대값 ÷ **최신 TTM EPS** = 후행 축 내재배수 → 역사 밴드와 직접 비교.
        cur = LIVE_TARGETS.get(tk)
        if cur:
            tgt, tgt_asof = (cur[0], cur[1]), cur[2]
        else:
            tgt, tgt_asof = OUR_TARGET_FALLBACK.get(tk), "8/8 폴백"
        ttm_now = cache[tk][-1][1] if cache.get(tk) else None
        imp = (tgt[0] / ttm_now, tgt[1] / ttm_now) if (tgt and ttm_now) else None
        verdict = "—"
        if imp and band:
            if imp[0] >= band[0] and imp[1] <= band[1]:
                verdict = "🟢 구간내"
            elif imp[0] > band[1]:
                verdict = "🔴 상단초과"
            elif imp[1] < band[0]:
                verdict = "🔵 보수적"
            else:
                verdict = "🟡 부분겹침"
        print(f"  {tk:8s}{r['n']:>5}{r['span'][0][:7]+'~'+r['span'][1][:7]:>20}"
              f"{f'{band[0]:.0f}~{band[1]:.0f}' if band else '—':>12}"
              f"{r['realized_med']:>10.1f}"
              f"{f'{imp[0]:.0f}~{imp[1]:.0f}x' if imp else '—':>13}{verdict:>11}")
        rows.append((tk, r, imp, verdict))
        asofs.append((tk, tgt_asof))

    save_cache(cache)

    # ★[8/14 신설·정훈 승인] 밴드를 원장으로 떨궈 validate_report.check_target_multiple이 소비한다.
    #   이 도구는 네트워크·EDGAR를 쓰므로 매 보고서 호출이 불가 → 주간 R3에서 갱신하고 검사기는 캐시를 읽는다.
    if a.save:
        bands = {"updated": dt.date.today().isoformat(), "horizon": a.horizon, "stocks": {}}
        for tk, r, imp, verdict in rows:
            bands["stocks"][tk] = {
                "band": r["band"], "n": r["n"], "span": r["span"],
                "realized_med": r["realized_med"],
                "ttm_eps": (cache[tk][-1][1] if cache.get(tk) else None),
                "ttm_end": (cache[tk][-1][0] if cache.get(tk) else None),   # 이 TTM이 끝나는 분기말
                "implied": imp, "verdict": verdict,
            }
        out = os.path.join(ROOT, "data", "app", "multiple_bands.json")
        json.dump(bands, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n  💾 {out} 저장 ({len(bands['stocks'])}종목)")

    n_over = sum(1 for *_, v in rows if v == "🔴 상단초과")
    n_in = sum(1 for *_, v in rows if v == "🟢 구간내")
    print(f"\n  구간내 {n_in} · 상단초과 {n_over} · 기타 {len(rows)-n_in-n_over} (총 {len(rows)})")
    stale = [t for t, d in asofs if d == "8/8 폴백"]
    live = sorted({d for _, d in asofs if d != "8/8 폴백"})
    src = (f"원장 최신 목표가(as_of {live[0]}~{live[-1]})" if live else "8/8 하드코딩 폴백")
    print(f"\n  ※ **우리목표→TTM** = {src} ÷ 최신 TTM EPS.")
    if stale:
        print("  ※   ⚠️ 원장에 최신 목표가가 없어 **8/8 폴백**을 쓴 종목: " + ", ".join(stale))
    print("  ※   우리 배수는 선행(컨센) EPS 기준이라 그대로 비교하면 안 되고,")
    print("  ※   이렇게 후행 축으로 환산해야 역사 밴드와 사과 대 사과가 된다.")
    print("  ※   ⚠️ 환산 없이 배수만 비교하면 '보수적'으로 잘못 읽힌다(8/8 1차 실행에서 실제로 그랬다).")
    print("  ※ '정당 구간' = 중앙 절대오차가 최저의 1.25배 이내인 배수 범위.")
    print("  ※ 실현PE 중앙 = 지평 후 실제가 ÷ 그때 TTM EPS = 사후적으로 시장이 매긴 배수.")
    print("  ※ 보유 종목만 보므로 생존편향 있음 — 절대 수준을 일반화하지 말 것.")
    print("  ※ 측정 전용 — 목표가·배수를 자동으로 바꾸지 않는다.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
