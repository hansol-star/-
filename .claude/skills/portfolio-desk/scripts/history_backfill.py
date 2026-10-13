#!/usr/bin/env python3
"""history_backfill.py — 상장 이래 전 일봉 소급·캐시 엔진 (stdlib only·무키·포터블)

동기(정훈 2026-07-21): "데이터가 6/12~13부터라 22일치뿐. 그 앞도 찾아낼 수 있잖아 —
최대한 많이 가져와서 분석하자." 실측 결과 Yahoo v8 chart에 period1=0을 넣으면 상장
이래 진짜 일봉이 전부 나온다(코스피 7,287일·29.6년, NVDA 6,914일 등 — range=max는
월봉 다운샘플이라 오답, period1/period2가 정답). 측정 3종(폭풍·GARCH·차트지표)은
전부 '가격의 순수 함수'라 과거 종가만 확보하면 과거 전 구간을 그대로 재계산할 수 있다.

성격: **데이터 수집·캐시 전용.** 어떤 룰도 안 바꾼다. vol_gauge·garch·chart_read가
이 캐시를 소비해 장기 백분위·GARCH 적합·역사 유사국면 분석을 한다.

캐시: data/history/<safe_symbol>.csv  (헤더 date,close — 종가는 정적이라 1회 확보 후
재사용, 매일 tail만 증분 append). 매니페스트 data/history/_manifest.json.
소급 불가 2종(외인·기관 수급 / 우리 포트폴리오 의사결정)은 이 엔진 범위 밖 — 그건
flows.json·decisions.jsonl이 정본이고 22~27일치 그대로.

사용:
  python3 history_backfill.py                 # 유니버스 증분 갱신(캐시 있으면 tail만)
  python3 history_backfill.py --refresh        # 전체 재풀(상장~오늘)
  python3 history_backfill.py --stats          # 캐시 현황(심볼·기간·일수)
  python3 history_backfill.py --symbols ^KS11,NVDA
  python3 history_backfill.py --json
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import cli_common

try:  # 유니버스는 market_data(=portfolio.json 정본) 재사용 — 티커 드리프트 방지
    import market_data as md
except ImportError:
    md = None

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

_HERE = os.path.dirname(os.path.abspath(__file__))
HIST_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", "data", "history"))
MANIFEST = os.path.join(HIST_DIR, "_manifest.json")


def _safe(symbol: str) -> str:
    """파일명 안전화: ^KS11 → _KS11, KRW=X → KRW_X, 005930.KS → 005930.KS."""
    return symbol.replace("^", "_").replace("=", "_").replace("/", "_")


# [7/21] 해외·매크로 크로스에셋 (정훈 "해외 자료도 좋아, 다 분석 가능하잖아").
# 전부 Yahoo 무키 딥이력 실측 확인: VIX 36.5년·美10Y 56.5년·달러 55.5년·니케이 56.5년 등.
# 크로스에셋 변동성·상관·위험선호 컨텍스트용(측정 전용).
XASSET = [
    ("VIX", "^VIX"), ("美10Y금리", "^TNX"), ("美2Y금리", "^FVX"),
    ("달러지수", "DX-Y.NYB"), ("니케이225", "^N225"), ("항셍", "^HSI"),
    ("상해종합", "000001.SS"), ("유로스톡스50", "^STOXX50E"), ("러셀2000", "^RUT"),
    ("금", "GC=F"), ("비트코인", "BTC-USD"),
]

# [8/5] 룰 검증용 **에피소드 표본 확대** 세트 — 비미국 13개 시장.
# 왜: 우리 룰(하드플로어·사다리)의 반례를 코스피 하나로 검정하면 **에피소드가 7개뿐**이라
#     어떤 결론도 안 난다(8/5에 '붕괴구간 면제'가 이 이유로 기각됐고, '국내 전용 플로어'는
#     이 세트를 붙여 188개 에피소드로 검정한 끝에 기각됐다).
#     룰 가설은 대개 "한국 특수"가 아니라 일반 명제라 **횡단면으로 표본을 늘릴 수 있다.**
# ⚠️ 신흥국을 일부러 넣었다 — 통화·정치·구조 위기가 잦아 '고유위기' 표본의 핵심 공급원이다.
# ⚠️ 측정·검증 전용. 이 지수들로 매매 판단을 하지 않는다(보유·워치가 아니다).
VERIFY_MARKETS = [
    ("대만", "^TWII"), ("인도", "^BSESN"), ("인니", "^JKSE"), ("브라질", "^BVSP"),
    ("멕시코", "^MXX"), ("터키", "XU100.IS"), ("캐나다", "^GSPTSE"), ("호주", "^AXJO"),
    ("영국", "^FTSE"), ("독일", "^GDAXI"), ("말레이", "^KLSE"),
    ("이스라엘", "^TA125.TA"), ("아르헨", "^MERV"),
]


def _universe(include_xasset: bool = True) -> list[tuple[str, str]]:
    """코스피·코스닥 + 보유 + 워치 + 유가 + (해외·매크로 크로스에셋). 순수 시세축."""
    if md is None:
        base = [("코스피", "^KS11"), ("코스닥", "^KQ11")]
    else:
        g = md.GROUPS
        seen, base = set(), []
        for grp in ("index", "holdings", "watchlist", "fx", "oil"):
            for label, sym in g.get(grp, []):
                if sym not in seen:
                    seen.add(sym)
                    base.append((label, sym))
        # [9/17 d193] 제외 워치의 채점 꼬리 — track_until까지만 갱신(제외 직전 콜의 +20거래일 채점용)
        for label, sym in getattr(md, "RETIRED_WATCH", []):
            if sym not in seen:
                seen.add(sym)
                base.append((label, sym))
    if include_xasset:
        have = {s for _, s in base}
        base += [(l, s) for (l, s) in XASSET if s not in have]
        have |= {s for _, s in XASSET}
        # 룰 검증용 표본 확대 세트도 같이 유지한다(안 붙이면 orphan 파일이 되어 stale해진다)
        base += [(l, s) for (l, s) in VERIFY_MARKETS if s not in have]
    return base


def bar_date(t: int, gmtoffset: int = 0) -> str:
    """Yahoo 일봉 타임스탬프 → **거래소 현지일**(YYYY-MM-DD).
    ★[2026-10-13] UTC로 붙이면 안 된다. 일봉 타임스탬프 = 세션 시작 시각이라, 현지 자정·오전에 여는 시장은
      UTC로 전날 23시가 된다(KRW=X 영국 서머타임·^AXJO 호주 서머타임) → 그 봉이 **하루 앞 날짜**로 들어가
      금요일 행에 장중 스냅샷이 굳고(KRW=X 10/09 = 1340.02 ↔ 실제 종가 1342.99는 10/08 행에),
      일요일 날짜 행이 생겼다(KRW=X 3,476봉·^AXJO 3,909봉이 하루씩 밀려 있었다).
      +1h = 서머타임이 끝난 뒤 다시 받을 때 과거 서머타임 봉(현지 자정 = UTC 23시)이 밀리지 않게 하는 여유
      (세션이 현지 23시 이후에 여는 시장은 없다 — 전 유니버스 73심볼에서 다른 봉의 라벨은 안 바뀐다)."""
    return time.strftime("%Y-%m-%d", time.gmtime(t + int(gmtoffset or 0) + 3600))


def fetch_daily_with_gaps(symbol: str, period1: int = 0, timeout: float = 30.0):
    """상장(period1=0) → 오늘 진짜 일봉. ([(date_str, close), ...], [결측 날짜, ...]). 실패 None.

    결측 날짜 = Yahoo가 **타임스탬프는 주면서 종가를 비워(null) 보낸 봉**. 휴장일은 타임스탬프
    자체가 없으므로 여기 잡히는 날은 거래가 있었는데 값만 빠진 날이다(10/13 실측 — .KS 개별종목
    10/12 봉이 통째로 null, 같은 날 ^KS11은 정상).
    ⚠️ range=max는 장기서 월봉 다운샘플 → 반드시 period1/period2(일봉 보장)."""
    now = int(time.time())
    url = (YAHOO_CHART.format(symbol=urllib.parse.quote(symbol))
           + f"?interval=1d&period1={period1}&period2={now}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        closes = res["indicators"]["quote"][0]["close"]
        off = (res.get("meta") or {}).get("gmtoffset") or 0
        book, nulls = {}, []
        for t, c in zip(ts, closes):
            d = bar_date(t, off)
            if c is None:
                nulls.append(d)
                continue
            book[d] = round(float(c), 4)      # 같은 날짜가 둘이면(미형성 봉 + 라이브 행) 뒤의 값
        out = sorted(book.items())
        # 오늘 세션의 미형성 봉(null)과 라이브 행은 같은 날짜다 — 값이 있으면 결측이 아니다.
        gaps = sorted({d for d in nulls if d not in book})
        return out, gaps
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError,
            IndexError, TypeError, ValueError):
        return None


def fetch_full_daily(symbol: str, period1: int = 0, timeout: float = 30.0):
    """[(date_str, close), ...] 시간순. 실패 None. (결측 날짜가 필요하면 fetch_daily_with_gaps)"""
    got = fetch_daily_with_gaps(symbol, period1, timeout)
    return got[0] if got else None


def fetch_with_backoff(symbol: str, period1: int = 0, tries: int = 4, with_gaps: bool = False):
    """레이트리밋(429) 대비 지수백오프. 웹환경 페이싱 정책과 동일 철학."""
    delay = 3.0
    for attempt in range(tries):
        got = fetch_daily_with_gaps(symbol, period1)
        if got and got[0]:
            return got if with_gaps else got[0]
        if attempt < tries - 1:
            time.sleep(delay)
            delay *= 2
    return None


# ── 국내 종목 결측 봉 보정 ───────────────────────────────────────────────────────
# ★[2026-10-13 신설] 8/13에 "최근 7일은 덮어쓴다(upsert)"를 넣었지만 **덮어쓸 원본이 없으면**
#   아무 일도 안 일어난다. 10/12 12:47 보고서 세션이 장중값(삼성 257,000)을 그날 행으로 썼고,
#   그 뒤 Yahoo가 10/12 봉을 null로 보내면서 장중값이 종가(250,500) 자리에 그대로 굳었다
#   (6종목 · 최대 2.6% 오차 · vol_gauge 종목 행·낙폭·check_price_grounding이 이 값을 읽는다).
#   ⇒ 국내 종목(.KS/.KQ)의 결측 봉은 네이버에서 메운다. 기준이 둘이라 출처를 남긴다:
#     · polling API의 전일 종가(기준가) = **KRX 정규장 종가**(Yahoo와 같은 기준) → 우선
#     · polling API의 당일 종가는 **15:30~16:00에만** KRX 종가다 — 16:00 애프터마켓이 열리면
#       같은 필드가 통합시세를 따라 움직인다(10/13 실측: 15:43 232,000 → 17:13 234,000).
#       그 창 밖이면 당일 봉은 메우지 않고 다음 거래일의 '전일 종가'로 채운다.
#     · 일봉 API = 통합시세(KRX+NXT)라 **애프터마켓 종가**다 — KRX 종가와 보통 ±0.5%, 급변일엔
#       2% 넘게 어긋난다(10/8 삼성 263,000 vs 262,000 · 10/13 하이닉스 1,479,000 vs 1,443,000).
#       → **캐시가 비어 있는 날짜를 채우는 데만** 쓴다. 이미 있는 값은 덮지 않는다 —
#         안 그러면 D+1에 기준가로 바로잡은 값을 D+2 실행이 근사값으로 되돌린다(리뷰에서 재현).
#       Yahoo가 나중에 봉을 채우면 개정창 upsert가 덮어쓴다.
KR_SUFFIX = (".KS", ".KQ")
KST = dt.timezone(dt.timedelta(hours=9))
NAVER_DAY = ("https://api.finance.naver.com/siseJson.naver?symbol={code}&requestType=1"
             "&startTime={start}&endTime={end}&timeframe=day")
NAVER_POLL = "https://polling.finance.naver.com/api/realtime/domestic/stock/{code}"
SRC_POLL_TODAY = "naver-polling 당일종가(KRX)"
SRC_POLL_PREV = "naver-polling 전일종가(KRX)"
SRC_DAILY = "naver-일봉(통합시세 = 애프터마켓 종가 · 근사)"
APPROX_SRCS = (SRC_DAILY,)             # 근사 출처 — 캐시에 이미 값이 있으면 덮지 못한다(merge_rows)
KR_CLOSE_PRINT = ("15:30:00", "16:00:00")   # polling closePrice가 KRX 종가인 시간창(체결시각 기준)
POLL_TOLERANCE = 0.03                  # 일봉 저가·고가를 모를 때만 쓰는 종가 대비 허용오차
GAPFILL_LOG = os.path.join(HIST_DIR, "_gapfill.jsonl")
NOTES: list[dict] = []                 # 이번 실행의 보정·미검증 기록(main이 출력·적재)


def _num(x) -> float:
    return float(str(x).replace(",", ""))


def _naver_daily(code: str, start: str, end: str, timeout: float = 10.0):
    """{YYYY-MM-DD: (종가, 저가, 고가)} — 네이버 일봉(통합시세 = 애프터마켓 포함). 실패 None."""
    url = NAVER_DAY.format(code=code, start=start.replace("-", ""), end=end.replace("-", ""))
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://finance.naver.com/"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read().decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return None
    out = {}
    for line in txt.splitlines():       # ["20261012", 시가, 고가, 저가, 종가, 거래량, 외인소진율],
        cells = [c.strip().strip('"') for c in line.strip().strip("[],").split(",")]
        if len(cells) >= 5 and len(cells[0]) == 8 and cells[0].isdigit():
            try:
                out[f"{cells[0][:4]}-{cells[0][4:6]}-{cells[0][6:]}"] = (
                    float(cells[4]), float(cells[3]), float(cells[2]))
            except ValueError:
                continue
    return out or None


def _naver_poll(code: str, timeout: float = 8.0):
    """{"date","close","prev"} — 정규장 최종가와 그 전일 종가(KRX 기준). 실패 None."""
    req = urllib.request.Request(NAVER_POLL.format(code=code), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))["datas"][0]
        close = _num(d["closePrice"])
        at = str(d["localTradedAt"])
        return {"date": at[:10], "time": at[11:19], "close": close,
                "prev": close - _num(d["compareToPreviousClosePrice"])}
    except Exception:  # noqa: BLE001 — 보정 실패가 수집을 막지 않는다
        return None


def kr_gap_fill(symbol: str, dates, now=None, daily=None, poll=None) -> dict:
    """Yahoo가 비워 보낸 국내 종목 봉을 메운다 → {date: (close, 출처)}.

    daily·poll·now는 주입 가능(자가검증용). 메울 수 없는 날짜는 결과에서 빠진다:
      · 네이버 일봉에 없는 날 = 거래일이 아니다
      · 오늘인데 polling 체결시각이 15:30~16:00 밖 = 장중값·애프터마켓 가격을 종가로 적지 않는다
    """
    dates = sorted(set(dates))
    if not dates:
        return {}
    code = symbol.split(".")[0]
    now = now or dt.datetime.now(KST)
    if daily is None:
        start = (dt.date.fromisoformat(dates[0]) - dt.timedelta(days=10)).isoformat()
        daily = _naver_daily(code, start, now.date().isoformat())
    if not daily:
        return {}
    if poll is None:
        poll = _naver_poll(code)
    today = now.date().isoformat()
    pdate = (poll or {}).get("date")
    prev_td = max((d for d in daily if pdate and d < pdate), default=None)
    ptime = (poll or {}).get("time") or ""
    regular = bool(pdate) and KR_CLOSE_PRINT[0] <= ptime < KR_CLOSE_PRINT[1]
    out = {}
    for d in dates:
        bar = daily.get(d)
        if not bar:
            continue
        ref, lo, hi = bar if isinstance(bar, tuple) else (bar, None, None)
        if d == today and not (d == pdate and regular):
            continue
        cand = None
        if poll and d == pdate and regular:
            cand = (poll["close"], SRC_POLL_TODAY)
        elif poll and d == prev_td:
            cand = (poll["prev"], SRC_POLL_PREV)
        # polling 값이 정말 그날 값인지: 그날 일봉의 저가~고가 안이어야 한다(통합시세 범위는 정규장 종가를 포함한다).
        # 종가끼리 비교하면 안 된다 — 일봉 종가는 애프터마켓 종가라 급변일엔 KRX 종가와 3% 넘게 벌어진다.
        if cand and lo is not None and hi is not None:
            sane = lo <= cand[0] <= hi
        else:
            sane = bool(cand) and abs(cand[0] / ref - 1) <= POLL_TOLERANCE
        if sane:
            out[d] = (round(float(cand[0]), 4), cand[1])
        else:
            out[d] = (round(float(ref), 4), SRC_DAILY)
    return out


def merge_rows(cached, fresh, fills, cutoff: str):
    """캐시 + Yahoo 새 봉 + 결측 보정을 합친다(순수 함수) → (merged, added, revised, patched).

    · Yahoo에 있는 날짜: 없던 날은 추가, 개정창(cutoff 이후) 안이면 덮어쓴다(8/13)
    · Yahoo가 비운 날짜: fills가 있으면 그 값으로 추가·교체(10/13) — 개정창 안에서만
      - Yahoo가 값을 준 날짜의 fill은 버린다(Yahoo 우선)
      - 근사 출처(APPROX_SRCS)는 **빈 날짜만** 채운다 — 이미 있는 값(기준가로 바로잡은 값일 수 있다)은 못 덮는다
    patched = [(date, 이전값|None, 새값, 출처)]
    """
    book = dict(cached)
    added = revised = 0
    for d, c in fresh:
        if d not in book:
            book[d] = c
            added += 1
        elif d >= cutoff and book[d] != c:
            book[d] = c          # 개정창 안 = 덮어쓴다
            revised += 1
    patched = []
    yahoo_dates = {d for d, _ in fresh}
    for d, (c, src) in sorted((fills or {}).items()):
        if d < cutoff or d in yahoo_dates or book.get(d) == c:
            continue
        if src in APPROX_SRCS and d in book:
            continue
        patched.append((d, book.get(d), c, src))
        if d in book:
            revised += 1
        else:
            added += 1
        book[d] = c
    return sorted(book.items(), key=lambda x: x[0]), added, revised, patched


def load_cached(symbol: str):
    path = os.path.join(HIST_DIR, _safe(symbol) + ".csv")
    if not os.path.exists(path):
        return []
    out = []
    with open(path, newline="") as f:
        rd = csv.reader(f)
        next(rd, None)  # 헤더
        for row in rd:
            if len(row) >= 2:
                try:
                    out.append((row[0], float(row[1])))
                except ValueError:
                    continue
    return out


def save_cached(symbol: str, rows) -> None:
    os.makedirs(HIST_DIR, exist_ok=True)
    path = os.path.join(HIST_DIR, _safe(symbol) + ".csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")  # [9/10] csv 기본 \r\n 금지 — .gitattributes eol=lf와 맞춘다
        w.writerow(["date", "close"])
        for d, c in rows:
            w.writerow([d, c])


# 최근 이 일수 안의 봉은 값이 바뀔 수 있다고 보고 **매번 덮어쓴다**.
# ★[8/13 실사고] 이 루틴이 14시대(KRX 장중)에 돌면서 **장중값을 그날 종가로 기록**했고,
#   기존 로직이 "이미 있는 날짜는 건너뜀"이라 마감 후에 다시 돌려도 영영 안 고쳐졌다.
#   결과: 코스피가 캐시엔 6,865.61(장중 고점 근처)로 남았는데 실제 종가는 6,813.34였고,
#   낙폭이 -24.67% vs **-25.25%** 로 갈려 **룰1 D1(-25%) 해금 판정이 정반대**로 나왔다
#   (보고서 v74는 "D1 재잠김·해금 0%"로 나갔다). 거래소 사후 정정도 같은 경로로 놓친다.
#   ⇒ 최근 구간은 append가 아니라 **upsert**한다.
REVISE_WINDOW_DAYS = 7


def update_symbol(symbol: str, refresh: bool = False):
    """캐시 있으면 마지막 날 이후만 증분(period1=마지막 ts). 없거나 refresh면 전체.
    단 최근 REVISE_WINDOW_DAYS 안의 날짜는 이미 있어도 **새 값으로 덮어쓴다**(장중 오염·사후정정 대응).
    Yahoo가 그 구간의 봉을 비워 보내면 국내 종목은 네이버로 메우고, 못 메운 캐시값은 '미검증'으로 남긴다."""
    cached = [] if refresh else load_cached(symbol)
    p1 = 0
    if cached:
        # 마지막 날 '이후'가 아니라 개정창 시작점부터 다시 받아야 덮어쓸 원본이 생긴다.
        p1_dt = dt.date.fromisoformat(cached[-1][0]) - dt.timedelta(days=REVISE_WINDOW_DAYS)
        p1 = int(time.mktime(p1_dt.timetuple()))
    got = fetch_with_backoff(symbol, period1=p1, with_gaps=True)
    if not got:
        return cached, 0
    fresh, gaps = got
    cutoff = (dt.date.today() - dt.timedelta(days=REVISE_WINDOW_DAYS)).isoformat()
    gaps_w = [d for d in gaps if d >= cutoff]
    fills = kr_gap_fill(symbol, gaps_w) if gaps_w and symbol.upper().endswith(KR_SUFFIX) else {}
    merged, added, revised, patched = merge_rows(cached, fresh, fills, cutoff)
    for d, old, new, src in patched:
        NOTES.append({"symbol": symbol, "date": d, "kind": "patched", "old": old, "new": new, "src": src})
    have = dict(merged)
    done = {d for d, _, _, _ in patched}
    for d in gaps_w:
        # 캐시에 값이 있는데 KRX 기준으로 확인하지 못한 날만 남긴다(기준가로 메웠거나 값이 일치하면 확인된 것).
        if d not in have or d in done:
            continue
        f = fills.get(d)
        if f and f[1] not in APPROX_SRCS:
            continue
        ref = f" · 네이버 일봉 {f[0]:,.0f}({(have[d] / f[0] - 1) * 100:+.1f}%)" if f else ""
        NOTES.append({"symbol": symbol, "date": d, "kind": "unverified", "old": have[d], "new": None,
                      "src": "Yahoo 봉 결측 — 캐시값을 KRX 종가로 확인 못 함(장중 스냅샷일 수 있음)" + ref})
    if not cached or added or revised:
        save_cached(symbol, merged)
    return merged, (len(merged) if not cached else added + revised)


def write_manifest(stats: dict, partial: bool = False) -> None:
    """매니페스트 저장. partial이면 기존 파일에 **해당 심볼만 갱신해 합친다**.

    ★[2026-10-13] `--symbols`로 돌릴 때마다 매니페스트가 그 심볼만 남게 통째로 덮였다 —
      close_reconcile이 매일 ^KS11·^KQ11만 갱신하면서 60여 심볼짜리 파일을 2개로 줄여 커밋하고 있었다.
    """
    os.makedirs(HIST_DIR, exist_ok=True)
    if partial:
        try:
            with open(MANIFEST, encoding="utf-8") as f:
                base = json.load(f)
        except (OSError, ValueError):
            base = {}
        syms = dict(base.get("symbols") or {})
        syms.update(stats.get("symbols") or {})
        stats = {"updated": stats.get("updated"), "symbols": syms,
                 "total_daily_bars": sum(v.get("days", 0) for v in syms.values())}
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)


def report_notes() -> None:
    """이번 실행의 결측 보정·미검증을 출력하고 원장(_gapfill.jsonl)에 남긴다."""
    if not NOTES:
        return
    print("\n결측 봉 처리:")
    for n in NOTES:
        if n["kind"] == "patched":
            was = "신규" if n["old"] is None else f"{n['old']:,.0f} →"
            print(f"  🔧 {n['symbol']} {n['date']}  {was} {n['new']:,.0f}  [{n['src']}]")
        else:
            print(f"  ⚠️ {n['symbol']} {n['date']}  캐시 {n['old']:,.4g} 미검증 — {n['src']}")
    stamp = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    seen = set()                        # 같은 (심볼·날짜·종류·값)은 한 번만 — 매 실행 같은 미검증이 쌓이지 않게
    try:
        with open(GAPFILL_LOG, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    seen.add((r.get("symbol"), r.get("date"), r.get("kind"), r.get("old"), r.get("new")))
                except ValueError:
                    continue
    except OSError:
        pass
    try:
        with open(GAPFILL_LOG, "a", encoding="utf-8", newline="\n") as f:
            for n in NOTES:
                key = (n["symbol"], n["date"], n["kind"], n["old"], n["new"])
                if key in seen:
                    continue
                seen.add(key)
                f.write(json.dumps({"run_at": stamp, **n}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def build_stats(only=None) -> dict:
    uni = _universe()
    if only:
        keep = set(only)
        uni = [(l, s) for (l, s) in uni if s in keep]
    out = {"updated": time.strftime("%Y-%m-%d"), "symbols": {}}
    for label, sym in uni:
        rows = load_cached(sym)
        if rows:
            out["symbols"][sym] = {
                "label": label, "first": rows[0][0], "last": rows[-1][0],
                "days": len(rows),
                "years": round((time.time() - time.mktime(
                    time.strptime(rows[0][0], "%Y-%m-%d"))) / 31557600, 1),
            }
        else:
            out["symbols"][sym] = {"label": label, "days": 0}
    total = sum(v.get("days", 0) for v in out["symbols"].values())
    out["total_daily_bars"] = total
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="상장 이래 전 일봉 소급·캐시 (수집 전용·stdlib)")
    ap.add_argument("--refresh", action="store_true", help="전체 재풀(상장~오늘)")
    ap.add_argument("--stats", action="store_true", help="캐시 현황만(풀 안 함)")
    ap.add_argument("--symbols", "--tickers", help="쉼표·공백구분 Yahoo 심볼(기본=유니버스 전체)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--pace", type=float, default=1.2, help="심볼 간 페이싱 초(레이트리밋)")
    ap.add_argument("--selftest", action="store_true", help="결측 봉 보정·매니페스트 병합 자가검증(오프라인)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    only = [s.strip() for s in cli_common.split_tickers(args.symbols)] if args.symbols else None

    if args.stats:
        stats = build_stats(only)
        if not only:  # 전체 조회면 매니페스트를 디스크 진실로 갱신
            write_manifest(stats)
        print(json.dumps(stats, ensure_ascii=False, indent=1) if args.json
              else _fmt_stats(stats))
        return 0

    uni = _universe()
    if only:
        keep = set(only)
        uni = [(l, s) for (l, s) in uni if s in keep]

    print(f"[history_backfill] {len(uni)}종목 {'전체 재풀' if args.refresh else '증분 갱신'} 시작…")
    for i, (label, sym) in enumerate(uni):
        rows, added = update_symbol(sym, refresh=args.refresh)
        span = f"{rows[0][0]}~{rows[-1][0]}" if rows else "실패"
        print(f"  {label:<12}{sym:<12} {len(rows):>6}일 (+{added}) {span}")
        if i < len(uni) - 1:
            time.sleep(args.pace)  # 페이싱

    report_notes()
    stats = build_stats(only)
    write_manifest(stats, partial=bool(only))
    print(f"\n총 {stats['total_daily_bars']:,}개 일봉 캐시 (data/history/). "
          f"매니페스트 갱신 완료.")
    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=1))
    return 0


def selftest() -> int:
    """10/13 실사고를 그대로 심어 보정이 잡는지 확인한다(네트워크 없음)."""
    global MANIFEST, HIST_DIR, GAPFILL_LOG, fetch_with_backoff, _naver_daily, _naver_poll
    import tempfile
    fails = []

    def ok(name, cond):
        if not cond:
            fails.append(name)
        print(f"  {'✅' if cond else '❌'} {name}")

    cached = [("2026-10-08", 262000.0), ("2026-10-12", 257000.0)]        # 10/12 = 장중 스냅샷
    fresh = [("2026-10-08", 262000.0), ("2026-10-13", 232000.0)]          # Yahoo: 10/12 봉 null
    # 네이버 일봉 = (종가, 저가, 고가) · 통합시세라 종가가 KRX 종가와 다르다
    daily = {"2026-10-07": (269000.0, 268000.0, 279500.0), "2026-10-08": (263000.0, 262000.0, 270000.0),
             "2026-10-12": (251000.0, 249000.0, 262500.0), "2026-10-13": (234000.0, 228000.0, 247500.0)}
    poll = {"date": "2026-10-13", "time": "15:30:00", "close": 232000.0, "prev": 250500.0}
    live = {"date": "2026-10-13", "time": "11:00:12", "close": 233000.0, "prev": 250500.0}
    late = {"date": "2026-10-13", "time": "17:13:04", "close": 234000.0, "prev": 250500.0}   # 애프터마켓
    after = dt.datetime(2026, 10, 13, 16, 10, tzinfo=KST)
    during = dt.datetime(2026, 10, 13, 11, 0, tzinfo=KST)

    # 가드 없이는 안 고쳐진다(= 이 검증이 실제로 사고를 가른다)
    m0, _, _, _ = merge_rows(cached, fresh, {}, "2026-10-06")
    ok("보정 없으면 장중값이 그대로 남는다(사고 재현)", dict(m0)["2026-10-12"] == 257000.0)

    f = kr_gap_fill("005930.KS", ["2026-10-12"], now=after, daily=daily, poll=poll)
    ok("전일 결측 = polling 전일종가(KRX 기준 250,500)", f.get("2026-10-12") == (250500.0, SRC_POLL_PREV))
    m1, a1, r1, p1 = merge_rows(cached, fresh, f, "2026-10-06")
    ok("장중값 257,000 → 종가 250,500으로 교체", dict(m1)["2026-10-12"] == 250500.0 and r1 == 1 and len(p1) == 1)

    ok("장중엔 당일 결측을 메우지 않는다",
       kr_gap_fill("005930.KS", ["2026-10-13"], now=during, daily=daily, poll=live) == {})
    ok("15:30~16:00 당일 결측 = polling 당일종가",
       kr_gap_fill("005930.KS", ["2026-10-13"], now=after, daily=daily, poll=poll).get("2026-10-13")
       == (232000.0, SRC_POLL_TODAY))
    ok("애프터마켓 가격(234,000)을 당일 종가로 적지 않는다",
       kr_gap_fill("005930.KS", ["2026-10-13"], now=after, daily=daily, poll=late) == {})
    ok("애프터마켓 중에도 전일 결측은 기준가(250,500)로 메운다",
       kr_gap_fill("005930.KS", ["2026-10-12"], now=after, daily=daily, poll=late).get("2026-10-12")
       == (250500.0, SRC_POLL_PREV))
    wknd = dt.datetime(2026, 10, 17, 10, 0, tzinfo=KST)                   # 토요일 — polling은 금요일 20:00 체결
    fri = {"date": "2026-10-16", "time": "19:59:58", "close": 240000.0, "prev": 236000.0}
    ok("주말에 금요일 결측 = 애프터마켓 종가 대신 일봉 근사(월요일 기준가로 자가치유)",
       kr_gap_fill("005930.KS", ["2026-10-16"], now=wknd,
                   daily={"2026-10-15": (236500.0, 233000.0, 238000.0), "2026-10-16": (239500.0, 235000.0, 241000.0)},
                   poll=fri).get("2026-10-16") == (239500.0, SRC_DAILY))
    ok("D-2 이전 결측 = 일봉 근사 + 출처 표기",
       kr_gap_fill("005930.KS", ["2026-10-08"], now=after, daily=daily, poll=poll).get("2026-10-08")
       == (263000.0, SRC_DAILY))
    ok("거래일이 아니면 메우지 않는다",
       kr_gap_fill("005930.KS", ["2026-10-09"], now=after, daily=daily, poll=poll) == {})
    bad = {"date": "2026-10-13", "time": "15:30:00", "close": 232000.0, "prev": 200000.0}   # 날짜가 어긋난 polling
    ok("polling 값이 그날 저가~고가 밖이면 일봉으로 물러난다",
       kr_gap_fill("005930.KS", ["2026-10-12"], now=after, daily=daily, poll=bad).get("2026-10-12")
       == (251000.0, SRC_DAILY))
    # 애프터마켓이 KRX 종가에서 3% 넘게 벌어진 날 — 종가끼리 비교하면 옳은 기준가를 버린다
    swing = {"2026-10-12": (251000.0, 249000.0, 262500.0), "2026-10-13": (240500.0, 228000.0, 247500.0)}
    nxt = dt.datetime(2026, 10, 14, 10, 0, tzinfo=KST)
    ok("애프터마켓이 3% 넘게 벌어져도 기준가(232,000)를 쓴다",
       kr_gap_fill("005930.KS", ["2026-10-13"], now=nxt, daily=swing,
                   poll={"date": "2026-10-14", "time": "10:00:03", "close": 236000.0, "prev": 232000.0})
       .get("2026-10-13") == (232000.0, SRC_POLL_PREV))
    ok("개정창 밖 날짜는 건드리지 않는다",
       dict(merge_rows(cached, fresh, {"2026-10-08": (261000.0, SRC_POLL_PREV)}, "2026-10-10")[0])["2026-10-08"]
       == 262000.0)
    ok("Yahoo가 준 봉은 보정보다 우선(같은 날짜에 fill이 있어도)",
       dict(merge_rows([("2026-10-12", 257000.0)], [("2026-10-12", 250500.0)],
                       {"2026-10-12": (249000.0, SRC_POLL_PREV)}, "2026-10-06")[0])["2026-10-12"] == 250500.0)
    # 이틀 연속 실행 — D+1에 기준가로 바로잡은 값을 D+2의 일봉 근사가 되돌리면 안 된다
    day2 = kr_gap_fill("005930.KS", ["2026-10-12"], now=nxt, daily=daily,
                       poll={"date": "2026-10-14", "time": "10:00:03", "close": 236000.0, "prev": 232000.0})
    m2, _, r2, p2 = merge_rows(m1, fresh, day2, "2026-10-06")
    ok("D+2 실행: 일봉 근사(251,000)가 기준가로 바로잡은 250,500을 못 덮는다",
       day2.get("2026-10-12") == (251000.0, SRC_DAILY) and dict(m2)["2026-10-12"] == 250500.0 and not p2)
    ok("근사 출처도 빈 날짜는 채운다",
       dict(merge_rows([("2026-10-08", 262000.0)], fresh, day2, "2026-10-06")[0]).get("2026-10-12") == 251000.0)

    # 배선 — fetch → gaps → kr_gap_fill → merge → CSV 저장이 실제로 이어지는가(함수만 맞고 연결이 끊기면 사고는 그대로다)
    keep_all = (HIST_DIR, GAPFILL_LOG, fetch_with_backoff, _naver_daily, _naver_poll)
    today = dt.date.today()
    dm2, dm1 = (today - dt.timedelta(days=2)).isoformat(), (today - dt.timedelta(days=1)).isoformat()
    t0 = today.isoformat()
    with tempfile.TemporaryDirectory() as td:
        try:
            HIST_DIR, GAPFILL_LOG = td, os.path.join(td, "_gapfill.jsonl")
            save_cached("TEST.KS", [(dm2, 262000.0), (dm1, 257000.0)])          # dm1 = 장중 스냅샷
            fetch_with_backoff = lambda *a, **k: ([(dm2, 262000.0), (t0, 232000.0)], [dm1])   # noqa: E731
            _naver_daily = lambda *a, **k: {dm2: (263000.0, 262000.0, 270000.0),             # noqa: E731
                                            dm1: (251000.0, 249000.0, 262500.0),
                                            t0: (234000.0, 228000.0, 247500.0)}
            _naver_poll = lambda *a, **k: {"date": t0, "time": "17:13:04",                   # noqa: E731
                                           "close": 234000.0, "prev": 250500.0}
            del NOTES[:]
            rows, n = update_symbol("TEST.KS")
            wired = dict(load_cached("TEST.KS")).get(dm1) == 250500.0 and n >= 1 and any(
                x["kind"] == "patched" and x["new"] == 250500.0 for x in NOTES)
            # 국내 종목이 아니면 메우지 않고 '미검증'만 남긴다
            save_cached("TEST", [(dm2, 100.0), (dm1, 101.0)])
            fetch_with_backoff = lambda *a, **k: ([(dm2, 100.0), (t0, 103.0)], [dm1])        # noqa: E731
            del NOTES[:]
            update_symbol("TEST")
            flagged = dict(load_cached("TEST")).get(dm1) == 101.0 and [x["kind"] for x in NOTES] == ["unverified"]
        finally:
            HIST_DIR, GAPFILL_LOG, fetch_with_backoff, _naver_daily, _naver_poll = keep_all
            del NOTES[:]
    ok("배선: update_symbol이 결측 봉을 받아 CSV의 장중값을 기준가로 바꾼다", wired)
    ok("배선: 국내 종목이 아니면 값은 두고 '미검증'만 남긴다", flagged)

    keep = MANIFEST
    with tempfile.TemporaryDirectory() as td:
        MANIFEST = os.path.join(td, "_manifest.json")
        try:
            write_manifest({"updated": "d1", "symbols": {"A": {"days": 10}, "B": {"days": 5}},
                            "total_daily_bars": 15})
            write_manifest({"updated": "d2", "symbols": {"A": {"days": 11}}, "total_daily_bars": 11},
                           partial=True)
            with open(MANIFEST, encoding="utf-8") as fh:
                m = json.load(fh)
        finally:
            MANIFEST = keep
    # 날짜 라벨 = 거래소 현지일(UTC 아님)
    import calendar
    sun23 = calendar.timegm((2026, 10, 11, 23, 0, 0))            # 일 23:00 UTC = 런던 월 00:00(BST)
    ok("환율 서머타임 봉(일 23:00 UTC) = 월요일 날짜", bar_date(sun23, 3600) == "2026-10-12")
    ok("서머타임 끝난 뒤 다시 받아도(gmtoffset 0) 같은 날짜", bar_date(sun23, 0) == "2026-10-12")
    ok("호주 서머타임 봉(일 23:00 UTC · +11h) = 월요일", bar_date(sun23, 39600) == "2026-10-12")
    ok("국내 봉(00:00 UTC · +9h)은 그대로",
       bar_date(calendar.timegm((2026, 10, 13, 0, 0, 0)), 32400) == "2026-10-13")
    ok("미국 봉(13:30 UTC · -4h)은 그대로",
       bar_date(calendar.timegm((2026, 10, 12, 13, 30, 0)), -14400) == "2026-10-12")
    ok("미국 선물 봉(04:00 UTC)을 겨울(-5h)에 받아도 그대로",
       bar_date(calendar.timegm((2026, 10, 12, 4, 0, 0)), -18000) == "2026-10-12")

    ok("부분 갱신이 다른 심볼을 지우지 않는다",
       set(m["symbols"]) == {"A", "B"} and m["symbols"]["A"]["days"] == 11 and m["total_daily_bars"] == 16)

    print(f"\n{'✅ SELFTEST PASS' if not fails else '❌ SELFTEST FAIL: ' + ', '.join(fails)}")
    return 1 if fails else 0


def _fmt_stats(stats: dict) -> str:
    lines = [f"캐시 현황 (updated {stats.get('updated','?')}) — "
             f"총 {stats.get('total_daily_bars',0):,}개 일봉",
             f"{'심볼':<14}{'라벨':<14}{'기간':<26}{'일수':>7}{'년':>6}"]
    lines.append("-" * 68)
    for sym, v in stats["symbols"].items():
        if v.get("days"):
            span = f"{v['first']}~{v['last']}"
            lines.append(f"{sym:<14}{v['label']:<14}{span:<26}{v['days']:>7}{v.get('years',0):>6}")
        else:
            lines.append(f"{sym:<14}{v['label']:<14}{'(캐시 없음)':<26}{0:>7}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
