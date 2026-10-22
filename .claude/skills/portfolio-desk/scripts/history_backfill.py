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
import re
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
    return time.strftime("%Y-%m-%d", time.gmtime(t + int(gmtoffset or 0) + 3600))  # label-ok: 정본


# ★[2026-10-20] 라벨러는 한 벌이다 — Yahoo 봉 타임스탬프 → 날짜는 **bar_date만** 한다.
#   10/13 이 함수로 캐시 날짜를 바로잡았는데 vol_gauge는 자기 UTC 라벨을 그대로 써서 두 벌이 갈라졌고,
#   KRW=X 병합에 가짜 주말 행 152개가 들어가 원/달러 5y %ile이 26.7(정답 35.2)로 나왔다(v116 '저평가' 오판독).
#   복사본(같은 식을 옮겨 적은 것)도 다음 정정 때 같은 식으로 갈라진다 → 다른 스크립트는 이 함수를 부른다.
#   labeler_lint = 그 규약의 기계 검사(selftest가 전 스크립트에 돌린다 · 정당한 예외 줄은 '# label-ok: 사유').
_LABEL_CONV = re.compile(r"utcfromtimestamp\(|\bgmtime\(\s*[^)\s]|fromtimestamp\([^)]*utc")
_YAHOO_BARS = re.compile(r"""\[\s*["']timestamp["']\s*\]|get\(\s*["']timestamp["']|finance/chart|YAHOO_CHART|["']splits["']""")


def labeler_lint(sources: dict) -> list:
    """{파일명: 소스} → [(파일, 줄번호, 줄)] — Yahoo 봉·이벤트를 읽는 파일에서 타임스탬프를 직접 날짜로 바꾸는 줄."""
    hits = []
    for name, src in sorted(sources.items()):
        if not _YAHOO_BARS.search(src):
            continue
        for i, line in enumerate(src.splitlines(), 1):
            code = line.split("#", 1)[0]
            if _LABEL_CONV.search(code) and "label-ok" not in line:
                hits.append((name, i, line.strip()))
    return hits


def fetch_daily_with_gaps(symbol: str, period1: int = 0, timeout: float = 30.0):
    """상장(period1=0) → 오늘 진짜 일봉. ([(date_str, close), ...], [결측 날짜, ...]). 실패 None.

    결측 날짜 = Yahoo가 **타임스탬프는 주면서 종가를 비워(null) 보낸 봉**. 휴장일은 타임스탬프
    자체가 없으므로 여기 잡히는 날은 거래가 있었는데 값만 빠진 날이다(10/13 실측 — .KS 개별종목
    10/12 봉이 통째로 null, 같은 날 ^KS11은 정상).
    ⚠️ range=max는 장기서 월봉 다운샘플 → 반드시 period1/period2(일봉 보장)."""
    got = fetch_chart_result(symbol, period1, timeout)
    try:
        return parse_chart(*got) if got else None
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def fetch_chart_result(symbol: str, period1: int = 0, timeout: float = 30.0):
    """Yahoo 일봉 chart result 원본 + 받은 시각 → (result, now). 실패 None. (meta가 필요한 호출용 — settled_meta_close)"""
    now = int(time.time())
    url = (YAHOO_CHART.format(symbol=urllib.parse.quote(symbol))
           + f"?interval=1d&period1={period1}&period2={now}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        return data["chart"]["result"][0], now
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError,
            IndexError, TypeError, ValueError):
        return None


SETTLE_GRACE_SEC = 40 * 60   # Yahoo가 적는 정규장 끝 + 이 시간까지는 그 세션 봉을 종가로 보지 않는다


def live_session_day(meta: dict, now: int):
    """아직 **끝나지 않은** 세션의 현지일(아니면 None) — Yahoo meta.currentTradingPeriod.regular 기준.

    ★[2026-10-16] 美 정규장 도중(23:4x KST)에 이 스크립트를 돌렸더니 ^GSPC·ANET 등 미국·유럽 33종목에
      **10/16 장중값**이 그날 종가 행으로 들어갔다(^GSPC 7,732.59 · ANET 181.86 — 장은 아직 5시간 남았다).
      국내는 close_reconcile가 마감 뒤에 돌아서 안 보였을 뿐, 해외 시장은 이 스크립트를 언제 돌려도 어딘가는 열려 있다.
      개정창(REVISE_WINDOW_DAYS)이 다음 실행에서 덮긴 하지만, 그 전까지 캐시를 정본으로 읽는 vol_gauge·
      가격 대조가 장중값을 종가로 쓴다 → **진행 중인 세션의 봉은 처음부터 쓰지 않는다.**
    ★[2026-10-19] '진행 중'(start ≤ now < end)만 막으면 두 구멍이 남는다(실측):
      ① **Yahoo가 적는 정규장 끝이 실제 마감보다 이르다** — ^KS11·국내 종목은 regular.end = 15:00 KST인데
         KRX 종가 단일가는 15:20~15:30이다. 15:00~15:30에 돌리면 장중값이 그날 종가 행으로 들어간다.
         종가 경매·지수 확정값도 마감 직후 몇 분 늦게 붙는다(런던 16:30~16:35 · 도쿄 15:30 뒤 15:45 갱신).
      ② **장 시작 전**(now < start)에 그날 봉이 이미 와 있으면(장전 거래가 있는 종목) 막지 않았다.
      ⇒ 세션이 **끝나고 SETTLE_GRACE_SEC가 지나기 전**까지는 그 세션 날짜의 봉을 쓰지 않는다.
         24시간 상품(선물·환율·코인: regular = 현지 00:00~23:59)은 원래대로 그날 내내 막힌다.
      ⚠️ 2026-08-13 개정창 upsert 이전에 쓰인 장중값은 이 가드로 안 고쳐진다 — `--audit-yahoo`가 그 자리다
         (10/19 ^VIX 7/21·7/22·7/30·8/3 4건 = 정본 '저점 VIX 19.4'의 출처).
    """
    reg = ((meta or {}).get("currentTradingPeriod") or {}).get("regular") or {}
    try:
        start, end = int(reg.get("start") or 0), int(reg.get("end") or 0)
    except (TypeError, ValueError):
        return None
    if start and end and now < end + SETTLE_GRACE_SEC:
        return bar_date(start, (meta or {}).get("gmtoffset") or 0)
    return None


def parse_chart(res: dict, now: int):
    """Yahoo chart result → ([(date, close), ...], [결측 날짜, ...]). 진행 중인 세션의 봉은 뺀다."""
    ts = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    meta = res.get("meta") or {}
    off = meta.get("gmtoffset") or 0
    live = live_session_day(meta, now)
    book, nulls = {}, []
    for t, c in zip(ts, closes):
        d = bar_date(t, off)
        if d == live:
            continue                          # 아직 종가가 아니다(결측도 아니다)
        if c is None:
            nulls.append(d)
            continue
        book[d] = round(float(c), 4)      # 같은 날짜가 둘이면(미형성 봉 + 라이브 행) 뒤의 값
    out = sorted(book.items())
    # 오늘 세션의 미형성 봉(null)과 라이브 행은 같은 날짜다 — 값이 있으면 결측이 아니다.
    gaps = sorted({d for d in nulls if d not in book})
    return out, gaps


def settled_meta_close(res: dict, now: int):
    """끝난 세션의 일봉이 **종가 null**로 올 때 그 세션의 정규장 종가 → (date, close). 아니면 None.

    ★[2026-10-22 실측] 美 마감 5시간 뒤(KST 10:30) ANET 10/21 일봉 close = null인데 meta.regularMarketPrice = 184.33
      (regularMarketTime = 정규장 끝 +3초 · 5분봉 마지막 값과 같다). parse_chart는 그 봉을 결측으로 빼므로 마지막 봉이
      **한 세션 전**(10/20 181.19)이 되고, 그걸 '전일 종가'로 읽은 지정가 추격 상한(d254)이 $186.62로 나왔다(정답 $189.85).
    ★[10/22 리뷰 반영] Yahoo는 몇 시간 뒤 currentTradingPeriod를 **다음 세션으로 넘긴다**(KST 15:30 실측 — regular.start =
      10/22 09:30 ET). 舊 조건(meta 정규장 = 그 세션)은 그때부터 None이라 주문을 거는 저녁에 다시 $186.62가 나왔다.
    읽는 경우 두 가지 — 마지막 봉(가장 늦은 날짜)이 null이고 regularMarketTime이 그 날짜일 때만:
      ⓐ meta 정규장이 아직 그 세션: 끝 + SETTLE_GRACE_SEC가 지났고 regularMarketTime ≥ 끝 − 60초
      ⓑ meta 정규장이 다음 세션으로 넘어감: 다음 세션이 아직 안 열렸고(now < start) regularMarketTime + 유예가 지났다
    다음 세션이 열리면(regularMarketPrice = 장중 값) None — 그땐 intraday_session_close.
    ⚠️ **실시간 판단 전용 — 캐시에 쓰지 않는다**(캐시는 개정창이 진짜 봉으로 덮는다 · 출처가 다른 값을 섞지 않는다).
    ⚠️ 국내(Asia/Seoul)는 안 읽는다 — Yahoo 국내는 20분 지연이고 정규장 끝을 15:00으로 적어 유예 안에 종가 경매 전 값이 온다
       (국내 결측 봉은 토스 1분봉 경로가 따로 있다)."""
    meta = res.get("meta") or {}
    if (meta.get("exchangeTimezoneName") or "") == "Asia/Seoul":
        return None
    reg = (meta.get("currentTradingPeriod") or {}).get("regular") or {}
    start, end = reg.get("start"), reg.get("end")
    rmt, rmp = meta.get("regularMarketTime"), meta.get("regularMarketPrice")
    if not (start and end and rmt and rmp):
        return None
    off = meta.get("gmtoffset") or 0
    bars = list(zip(res.get("timestamp") or [],
                    ((res.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []))
    if not bars:
        return None
    last_t, last_c = max(bars, key=lambda b: b[0])
    d = bar_date(last_t, off)
    if last_c is not None or bar_date(rmt, off) != d:
        return None
    if bar_date(start, off) == d:                                       # ⓐ
        ok = now >= end + SETTLE_GRACE_SEC and rmt >= end - 60
    else:                                                               # ⓑ
        ok = rmt < start and now < start and now >= rmt + SETTLE_GRACE_SEC
    return (d, round(float(rmp), 4)) if ok else None


def intraday_session_close(symbol: str, day: str, timeout: float = 10.0):
    """그 날짜(거래소 현지일) **정규장 5분봉의 마지막 종가** — 일봉이 null인 끝난 세션의 보조 판독. 실패·진행 중 세션이면 None.
    ★[10/22] 다음 세션이 열리면 meta로는 전 세션 종가를 못 읽는다(settled_meta_close ⓑ 끝) — 그때 쓰는 경로.
    ⚠️ 마지막 5분봉 종가 = 공식 종가(16:00 경매)와 몇 센트 다를 수 있다(10/21 ANET은 같았다) · 실시간 판단 전용."""
    now = int(time.time())
    url = YAHOO_CHART.format(symbol=urllib.parse.quote(symbol)) + "?interval=5m&range=5d"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode())["chart"]["result"][0]
        meta = res.get("meta") or {}
        if day == live_session_day(meta, now):
            return None
        off = meta.get("gmtoffset") or 0
        vals = [c for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"])
                if c is not None and bar_date(t, off) == day]
        return round(float(vals[-1]), 4) if vals else None
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError, IndexError, TypeError, ValueError, OSError):
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
SRC_TOSS = "toss-1분봉 15:40(KRX 정규장 종가)"
TOSS_PACE = 0.25                       # 토스 차트 조회 간 페이싱(초)
SRC_POLL_TODAY = "naver-polling 당일종가(KRX)"
SRC_POLL_PREV = "naver-polling 전일종가(KRX)"
SRC_DAILY = "naver-일봉(통합시세 = 애프터마켓 종가 · 근사)"
SRC_TOSS_ADJ = "toss-1분봉(수정주가 — 호가단위 격자 밖 · 근사)"
APPROX_SRCS = (SRC_DAILY, SRC_TOSS_ADJ)  # 근사 출처 — 캐시에 이미 값이 있으면 덮지 못한다(merge_rows)
KR_CLOSE_PRINT = ("15:30:00", "16:00:00")   # polling closePrice가 KRX 종가인 시간창(체결시각 기준)
POLL_TOLERANCE = 0.03                  # 일봉 저가·고가를 모를 때만 쓰는 종가 대비 허용오차
GAPFILL_LOG = os.path.join(HIST_DIR, "_gapfill.jsonl")
NOTES: list[dict] = []                 # 이번 실행의 보정·미검증 기록(main이 출력·적재)


def _num(x) -> float:
    return float(str(x).replace(",", ""))


# ── 토스 1분봉 = KRX 정규장 종가의 1차 출처 ───────────────────────────────────
# ★[2026-10-13 정훈 "토스로 보면 되는 거 아닌가? 왜 네이버로 봐?"] 맞는 지적이었다 — 토스에 캔들 API가
#   있는지 확인도 안 하고 네이버를 붙였다(데이터 우선순위 정본은 토스 > Yahoo > …).
#   실측해 보니 기준이 셋으로 갈린다:
#     · 토스 **일봉** = 통합시세(KRX+NXT)라 네이버 일봉과 같은 문제를 가진다
#       (10/13 삼성 237,000 ↔ KRX 종가 232,000 · 10/8 262,500 ↔ 262,000).
#     · 토스 **1분봉**은 종가 단일가가 그대로 보인다 — 15:22~15:40 사이에 **거래량이 찍힌 봉이 딱 하나**
#       (종가 단일가)이고 그 앞(단일가 호가접수 15:20~)과 뒤(애프터마켓 전)는 전부 거래량 0이다.
#       그 봉의 가격이 KRX 정규장 종가다(10/13 삼성 232,000 · 하이닉스 1,443,000 · 10/12 삼성 250,500
#       = Yahoo·네이버 기준가와 일치). 단일가 봉의 시각은 고정이 아니다 — NXT 상장 종목은 15:31,
#       KRX 단독 종목(두산로보·원익IPS)은 15:30, 단일가가 연장된 날(10/8)은 15:33이었다.
#     · 네이버 기준가는 **전일 하루**만 주고 권리락·배당락일엔 조정된 값이다. 1분봉은 1년 전 날짜도 준다.
#   ⇒ 순서: 토스 1분봉 → 네이버 기준가(전일) → 네이버 일봉(근사·빈 날짜만).
#   ⚠️ 키가 없는 곳(클라우드·무인 claude 세션)에선 토스를 못 쓴다 → 네이버로 물러난다. 그래서 네이버 경로를 지우지 않는다.
#   ⚠️ 조회 전용 — toss_snapshot.req()만 쓴다(_assert_readonly가 GET·토큰 발급 외 전부 막는다).
TOSS_BARS = 19                         # 15:40 → 15:22 (최신순)
AUCTION_MIN = (30, 35)                 # 종가 단일가 봉이 올 수 있는 분(15:30~15:35) — 뒤에 무거래 봉이 5개 이상 남는다


def krx_close_from_bars(bars, date: str):
    """토스 1분봉 19개(15:40→15:22 · 최신순)에서 KRX 정규장 종가를 읽는다. 서명이 안 맞으면 None.

    서명 = 그 구간에 **거래량이 있는 봉이 정확히 하나**(종가 단일가)이고, 그 봉이 15:30~15:35에 있으며,
           그 뒤 15:40까지의 무거래 봉들이 전부 같은 가격이다.
    안 맞는 경우(= None, 다음 출처로 물러난다): 휴장일 · 장 마감 전 · 마감이 늦는 날(수능일 — 15:22~15:40에
    연속 거래가 찍힌다) · 단일가 체결이 없는 종목 · 장 시간이 바뀐 뒤.
    ⚠️ 마감이 늦는 날 + 그 19분간 딱 한 번만 거래된 비유동 종목이면 장중값을 종가로 읽을 수 있다
       (연 1일 × 초저유동 — 우리 유니버스엔 없다. 넓히려면 장 운영시간 API로 마감 시각을 먼저 확인할 것).
    """
    if not bars or len(bars) != TOSS_BARS:
        return None
    want = [f"{date}T15:{m:02d}" for m in range(40, 40 - TOSS_BARS, -1)]
    try:
        if [str(b["timestamp"])[:16] for b in bars] != want:
            return None
        vol = [_num(b["volume"]) for b in bars]
        px = [_num(b["closePrice"]) for b in bars]
    except (KeyError, TypeError, ValueError):
        return None
    hit = [i for i, v in enumerate(vol) if v > 0]
    if len(hit) != 1:
        return None
    i = hit[0]
    if not AUCTION_MIN[0] <= 40 - i <= AUCTION_MIN[1]:
        return None
    if any(c != px[i] for c in px[:i]):
        return None
    return px[i]


TOSS_NO_KEY = "토스 키 없음(TOSS_CLIENT_ID/SECRET)"
TOSS_WHY = [""]                        # 토스를 못 쓰는 이유 — '키 없음'(설정)과 '토큰 발급 실패'(장애)는 다른 일이다


def toss_source():
    """(종목코드, 날짜) → KRX 정규장 종가 | None 을 주는 함수. 키가 없거나 토큰 발급이 안 되면 None.

    못 쓰는 이유는 TOSS_WHY[0]에 남긴다 — 둘을 뭉치면 IP 허용목록이 풀려 감사가 죽은 것(장애)이
    '키 없는 환경'(정상)처럼 읽힌다. 예외 메시지는 넣지 않는다(요청 본문에 시크릿이 있다) — 종류만.
    """
    if not (os.environ.get("TOSS_CLIENT_ID") and os.environ.get("TOSS_CLIENT_SECRET")):
        TOSS_WHY[0] = TOSS_NO_KEY
        return None
    try:
        import sys as _sys
        if _HERE not in _sys.path:
            _sys.path.insert(0, _HERE)
        import toss_snapshot as T
        ctx = T.make_ctx(False)
        tok = T.req("POST", "/oauth2/token", ctx, form=True, data={
            "grant_type": "client_credentials", "client_id": os.environ["TOSS_CLIENT_ID"],
            "client_secret": os.environ["TOSS_CLIENT_SECRET"]})
        if not tok or not tok.get("access_token"):
            TOSS_WHY[0] = "토스 토큰 발급 실패 — 키는 있다(IP 허용목록·키 만료·토스 장애 확인)"
            return None
        auth = {"Authorization": "Bearer " + tok["access_token"]}
    except Exception as e:  # noqa: BLE001 — 토스가 안 되면 네이버로 물러난다
        TOSS_WHY[0] = f"토스 토큰 발급 실패({type(e).__name__}) — 키는 있다"
        return None
    TOSS_WHY[0] = ""

    def fetch(code: str, date: str):
        time.sleep(TOSS_PACE)
        r = T.req("GET", f"/api/v1/candles?symbol={code}&interval=1m&count={TOSS_BARS}"
                         f"&before={date}T15:40:00%2B09:00", ctx, headers=auth)
        return krx_close_from_bars(((r or {}).get("result") or {}).get("candles") or [], date)
    return fetch


_TOSS = [False]                        # False = 아직 안 만듦 · None = 못 씀(키 없음·토큰 실패)


def _toss():
    if _TOSS[0] is False:
        _TOSS[0] = toss_source()
    return _TOSS[0]


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


def kr_gap_fill(symbol: str, dates, now=None, daily=None, poll=None, toss=None) -> dict:
    """Yahoo가 비워 보낸 국내 종목 봉을 메운다 → {date: (close, 출처)}.

    출처 순서: ① 토스 1분봉(toss = (코드, 날짜) → 종가 함수 · 없으면 건너뜀) ② 네이버 기준가 ③ 네이버 일봉(근사)
              ④ 토스 1분봉이 줬지만 호가단위 격자 밖인 값(수정주가 · 근사 — 앞의 셋이 다 못 준 날만).
    daily·poll·now·toss는 주입 가능(자가검증용). 메울 수 없는 날짜는 결과에서 빠진다:
      · 토스 서명이 안 맞고 네이버 일봉에도 없는 날 = 거래일이 아니다
      · 오늘인데 토스가 못 주고 polling 체결시각이 15:30~16:00 밖 = 장중값·애프터마켓 가격을 종가로 적지 않는다
    """
    dates = sorted(set(dates))
    if not dates:
        return {}
    code = symbol.split(".")[0]
    now = now or dt.datetime.now(KST)
    today = now.date().isoformat()
    out, adj = {}, {}
    if toss:
        for d in dates:
            if d > today:
                continue
            px = toss(code, d)
            if not px:
                continue
            # 토스 1분봉은 수정주가다 — 권리락·분할이 지나가면 과거 봉이 소급 조정돼 호가단위 격자를 벗어난다.
            # 그 값은 Yahoo close와 기준이 달라 KRX 종가로 못 쓴다 → 네이버에 먼저 묻고, 그래도 비면 근사로만 채운다.
            if on_tick(px):
                out[d] = (round(float(px), 4), SRC_TOSS)
            else:
                adj[d] = (round(float(px), 4), SRC_TOSS_ADJ)

    def done():
        for d, v in adj.items():
            out.setdefault(d, v)
        return out

    dates = [d for d in dates if d not in out]
    if not dates:
        return done()
    if daily is None:
        start = (dt.date.fromisoformat(dates[0]) - dt.timedelta(days=10)).isoformat()
        daily = _naver_daily(code, start, now.date().isoformat())
    if not daily:
        return done()
    if poll is None:
        poll = _naver_poll(code)
    pdate = (poll or {}).get("date")
    prev_td = max((d for d in daily if pdate and d < pdate), default=None)
    ptime = (poll or {}).get("time") or ""
    regular = bool(pdate) and KR_CLOSE_PRINT[0] <= ptime < KR_CLOSE_PRINT[1]
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
    return done()


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
    pin_rows = _pin_rows(symbol) if symbol.upper().endswith(KR_SUFFIX) else {}
    pins = {d: new for d, (new, _old) in pin_rows.items()}
    if pins:                             # 감사가 고친 날짜는 Yahoo 값 대신 고친 값을 쓴다(안 그러면 다음 갱신이 되돌린다)
        yahoo = dict(fresh)
        for d in sorted(d for d in pins if d in yahoo and not _pin_holds(pins[d], pin_rows[d][1], yahoo[d])):
            _skip_pin(symbol, d, pins.pop(d), yahoo[d])     # 분할·권리락 뒤의 옛 단위 핀 — 박으면 하루짜리 급등락이 된다
        fresh = [(d, pins.get(d, c)) for d, c in fresh]
    gaps_w = [d for d in gaps if d >= cutoff and d not in pins]      # 핀이 있는 날짜는 다시 메우지 않는다
    fills = (kr_gap_fill(symbol, gaps_w, toss=_toss())
             if gaps_w and symbol.upper().endswith(KR_SUFFIX) else {})
    merged, added, revised, patched = merge_rows(cached, fresh, fills, cutoff)
    lost = [d for d in gaps if d in pins and d not in dict(merged)]  # 재풀 + Yahoo 결측 = 핀 날짜가 통째로 빠진 경우
    for d in list(lost):                 # 같은 날 Yahoo 값이 없으니 가장 가까운 날과 견준다 — 단위가 다르면 넣지 않는다
        near = _nearest(merged, d)
        if near is not None and not _pin_fits(pins[d], near, PIN_NEAR_BAND, tick=False):
            lost.remove(d)
            _skip_pin(symbol, d, pins.pop(d), near)
    if lost:
        merged = sorted({**dict(merged), **{d: pins[d] for d in lost}}.items(), key=lambda x: x[0])
        added += len(lost)
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
        ref = (f" · {'토스 수정주가' if f[1] == SRC_TOSS_ADJ else '네이버 일봉'} {f[0]:,.0f}"
               f"({(have[d] / f[0] - 1) * 100:+.1f}%)") if f else ""
        NOTES.append({"symbol": symbol, "date": d, "kind": "unverified", "old": have[d], "new": None,
                      "src": "Yahoo 봉 결측 — 캐시값을 KRX 종가로 확인 못 함(장중 스냅샷일 수 있음)" + ref})
    if not cached or added or revised:
        save_cached(symbol, merged)
    return merged, (len(merged) if not cached else added + revised)


KRX_TICKS = ((2000, 1), (5000, 5), (20000, 10), (50000, 50), (200000, 100), (500000, 500))


def on_tick(px: float) -> bool:
    """KRX **주식** 호가단위 격자 위의 값인가. 주식의 실제 체결가는 격자 위다 — 격자 밖이면 수정주가(분할·권리락 소급 조정)다.

    ⚠️ 주식 전용이다. ETF·ETN은 격자가 다르다(2,000원 이상 5원 단위) — 주식 격자로 재면 실제 체결가가 '격자 밖'으로
       읽혀 감사에서 통째로 '비교 제외'가 된다(틀린 값을 쓰지는 않지만 눈이 먼다). 지금 국내 유니버스 18종목은 전부
       주식이다. ETF를 넣게 되면 5원 격자를 **그 종목에만** 적용할 것 — 전 종목에 5원 격자를 허용하면 수정주가의
       5분의 1이 격자 위로 읽혀 가짜 불일치가 된다.
    ⚠️ 격자 위 = 실제 체결가라는 보증은 아니다(수정주가가 우연히 격자에 올 수 있다) — 걸러내는 쪽으로만 믿는다.
    """
    tick = next((t for lim, t in KRX_TICKS if px < lim), 1000)
    return abs(px - round(px / tick) * tick) < 1e-6


SRC_AUDIT = SRC_TOSS + " · 감사"
LOG_BAD = [0]           # 마지막 _log_rows()가 못 읽은 줄 수(깨진 JSON · dict 아님 · 깨진 글자) — 감사 결과(ledger_bad)에 실려 메모가 된다
PIN_BAND = 1.15         # 핀과 같은 날 Yahoo 값이 이 배율 넘게 벌어지면 다른 가격 단위(분할·권리 소급 조정)로 본다
PIN_NEAR_BAND = 1.45    # 같은 날 값이 없어 가장 가까운 날과 견줄 때의 폭(상·하한가 ±30% + 여유)


def _log_rows() -> list:
    """원장(_gapfill.jsonl)의 dict 행만 읽는다. 깨진 줄 · dict가 아닌 줄([]·null) · 깨진 인코딩은 건너뛴다.

    원장은 사람이 손으로 고치는 파일이다(핀을 풀려면 줄을 지운다). 한 줄이 깨졌다고 예외가 나면 국내 종목 갱신이
    전부 죽고, 마감 대사는 그 종료코드를 안 봐서 조용히 멈춘다(10/14 검토에서 재현 — cp949로 재저장된 원장).
    ★[10/14 3차 검토] 건너뛰기만 하면 그것도 침묵이다 — 못 읽은 줄 수를 LOG_BAD에 남기고 감사가 ledger_bad로 올린다
      (윈도우 PowerShell 5.1의 Get-Content | Set-Content는 cp949로, Out-File은 UTF-16으로 다시 쓴다). BOM은 받아 준다.
    """
    rows, bad = [], 0
    try:
        with open(GAPFILL_LOG, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    bad += 1
                    continue
                if not isinstance(r, dict):
                    bad += 1
                    continue
                if chr(0xFFFD) in line:
                    bad += 1                 # 줄은 읽히지만 글자가 깨졌다(cp949 재저장) — 한글 출처 비교가 어긋난다
                rows.append(r)
    except OSError:
        pass
    LOG_BAD[0] = bad
    return rows


def audit_pins(symbol: str) -> dict:
    """감사 --fix가 토스 값으로 고친 {날짜: 값} — 원장(_gapfill.jsonl)의 감사 기록(SRC_AUDIT)에서 읽는다.

    ★[2026-10-13 검토] --fix로 고친 날짜가 개정창(7일) 안이면 Yahoo가 같은 값을 계속 주는 한 **다음 갱신이 되돌렸다**
      (merge_rows는 Yahoo 우선 · 마감 대사가 하루 두 번 갱신한다). 반나절도 못 가는 수리였다 → 감사가 고친 날짜는
      Yahoo가 못 덮는다.
    ★[10/14 검토] 날짜 제한을 두지 않는다 — 첫 판은 개정창 안 날짜만 핀으로 돌려줘서, 창 밖 날짜를 고친 뒤
      전체 재풀(--refresh · 캐시 파일 유실)을 하면 Yahoo 값으로 되돌아갔다(감사 7거래일은 달력 9~12일이라
      고친 날짜의 일부는 늘 창 밖이다). 증분 갱신은 창 밖 날짜를 원래 안 건드리므로 제한을 풀어도 무해하다.
    ★[10/14 3차 검토] 핀 표지는 ASCII(`"pin": true`)다 — 한글 출처(SRC_AUDIT) 일치로만 가리면 원장이 cp949로
      재저장되는 순간 **모든 핀이 조용히 풀렸다**(줄은 읽히는데 출처 글자가 깨져 비교가 어긋난다). 출처 비교는 옛 기록용.
    되돌리려면 원장에서 그 줄을 지운다(사람이 확인하고 고친 값이라 자동으로 풀지 않는다 — UTF-8로 저장할 것).
    """
    return {d: new for d, (new, _old) in _pin_rows(symbol).items()}


def _pin_rows(symbol: str) -> dict:
    """{날짜: (고친 값, 고치기 전 값 또는 None)} — audit_pins의 원본. 같은 날짜가 여러 줄이면 마지막 줄."""
    pins = {}
    for r in _log_rows():
        if str(r.get("symbol") or "").upper() != symbol.upper() or r.get("kind") != "patched":
            continue
        if r.get("pin") is not True and r.get("src") != SRC_AUDIT:
            continue
        try:
            new = float(r["new"])
        except (KeyError, TypeError, ValueError):
            continue
        try:
            old = float(r.get("old"))
        except (TypeError, ValueError):
            old = None
        pins[str(r["date"])] = (new, old)
    return pins


def _pin_holds(pin: float, old, yahoo: float) -> bool:
    """핀을 지금 Yahoo 값 위에 써도 되는가.

    ★[10/14 4차 검토] 단위 검사(_pin_fits)만 두면 **정당한 핀도 버려졌다** — Yahoo가 그날 KRX 종가와 15% 넘게 다른 값을
      계속 주는 경우(상·하한가 날의 굳은 장중값)다. `--fix`는 '되돌리지 못한다'고 말하는데 다음 갱신이 되돌렸다.
      ⇒ Yahoo가 **고치기 전 값(old)을 그대로** 주고 있으면 재조정이 아니라 같은 오류다 → 핀을 쓴다.
      Yahoo 값이 달라졌을 때만(스스로 정정했거나 분할·권리락으로 소급 조정했거나) 단위 검사로 가른다.
    """
    if old is not None and abs(yahoo - old) < 0.5:
        return True
    return _pin_fits(pin, yahoo)


def _pin_fits(pin: float, ref: float, band: float = PIN_BAND, tick: bool = True) -> bool:
    """핀(고친 날의 KRX 원시 종가)이 지금 시계열과 같은 가격 단위인가.

    ★[10/14 3차 검토] Yahoo는 분할·권리락을 **소급 조정**한다. 그 뒤에도 옛 단위의 핀을 박으면 그날만 +400%/-80%로 튄다
      (재현: 5대1 분할 뒤 --refresh → 50,000 · 250,500 · 49,800). 같은 날 Yahoo 값이 호가단위 격자 밖(= 수정주가)이거나
      핀과 band 넘게 벌어지면 다른 단위로 보고 핀을 쓰지 않는다 — 조용히 버리지 않고 '미검증' 메모를 남긴다.
    ⚠️ 격자 위에 우연히 놓인 band 이내의 작은 조정(소규모 무상증자·유상증자 권리락)은 못 잡는다.
    """
    try:
        return bool(ref and ref > 0 and (on_tick(ref) or not tick) and 1 / band <= pin / ref <= band)
    except (TypeError, ZeroDivisionError):
        return True


def _nearest(rows: list, d: str):
    """rows[(날짜, 값)]에서 d와 가장 가까운 날의 값(없으면 None)."""
    try:
        d0 = dt.date.fromisoformat(d)
        return min(rows, key=lambda x: abs((dt.date.fromisoformat(x[0]) - d0).days))[1] if rows else None
    except ValueError:
        return None


def _skip_pin(symbol: str, d: str, pin: float, ref: float) -> None:
    NOTES.append({"symbol": symbol, "date": d, "kind": "unverified", "old": pin, "new": None,
                  "src": f"감사가 고친 값(핀)을 쓰지 않았다 — 지금 시계열({ref:,.4g})과 가격 단위가 다르다(분할·권리 소급 조정 추정) · "
                         "원장(_gapfill.jsonl)의 그 줄을 지우고 `--audit`으로 다시 볼 것"})


def audit_kr(days: int = 7, symbols=None, toss=None, now=None, fix: bool = False) -> dict:
    """국내 종목 캐시의 최근 N거래일을 **토스 KRX 종가와 대조**한다(읽기 전용 · fix면 불일치를 고쳐 쓴다).

    결측 봉 보정은 Yahoo가 봉을 비웠을 때만 돈다. Yahoo가 **값을 줬는데 그 값이 틀린** 경우
    (개정창 7일이 지난 장중값 · Yahoo 자체 오류)는 아무도 안 본다 — 이 감사가 그 자리다.
    ⚠️ 수정주가는 비교하지 않는다: 토스와 Yahoo는 소급 조정 계수가 달라(10/1 삼성바이오 1,417,997 ↔ 1,419,364)
       조정된 구간은 원래 다르다. 어느 한쪽이 호가단위 격자 밖이면 'adjusted'로 세고 넘긴다 — 장중값이 굳은 것과
       구별된다(굳은 값은 실제 체결가라 격자 위에 있다).
    → {"checked", "unresolved", "adjusted", "mismatch": [{symbol, date, cached, toss, pct}], "fixed", "error", "no_key"}
       error = 감사를 아예 못 돌린 이유 · no_key = 그 이유가 '키 없음'(설정)인가 — 아니면 토큰 발급 실패(장애)다.
       ⚠️ 돌았더라도 checked가 0이거나 unresolved가 대부분이면 본 게 없는 것이다 — 호출자가 '불일치 0'으로 읽지 말 것.
    """
    toss = toss if toss is not None else _toss()
    _log_rows()                          # 원장이 깨졌는지(ledger_bad)는 감사를 못 돌린 날에도 올린다
    out = {"days": days, "checked": 0, "unresolved": 0, "unresolved_list": [], "adjusted": 0,
           "mismatch": [], "fixed": 0, "error": None, "no_key": False, "ledger_bad": LOG_BAD[0]}
    if not toss:
        why = TOSS_WHY[0] or TOSS_NO_KEY
        out["error"], out["no_key"] = why, why == TOSS_NO_KEY
        return out
    now = now or dt.datetime.now(KST)
    today = now.date().isoformat()
    after_close = now.strftime("%H:%M") >= "15:42"
    if symbols is None:
        symbols = [s for _, s in _universe() if s.upper().endswith(KR_SUFFIX)]
    for symbol in symbols:
        rows = load_cached(symbol)
        tail = [(d, c) for d, c in rows if d < today or (d == today and after_close)][-days:]
        book, changed = dict(rows), False
        for d, c in tail:
            px = toss(symbol.split(".")[0], d)
            if px is None:
                out["unresolved"] += 1
                out["unresolved_list"].append([symbol, d])
                continue
            out["checked"] += 1
            if abs(px - c) < 0.5:
                continue
            if not (on_tick(px) and on_tick(c)):
                out["adjusted"] += 1
                continue
            out["mismatch"].append({"symbol": symbol, "date": d, "cached": c, "toss": px,
                                    "pct": round((c / px - 1) * 100, 2)})
            if fix:
                book[d] = round(float(px), 4)
                changed = True
                out["fixed"] += 1
                NOTES.append({"symbol": symbol, "date": d, "kind": "patched", "old": c, "new": book[d],
                              "src": SRC_AUDIT, "pin": True})
        if changed:
            # 원장(핀)을 먼저 쓰고 캐시를 고친다 — 반대 순서면 도중에 끊긴 실행이 '고쳤는데 핀은 없는' 값을 남기고,
            #   다시 돌려도 캐시 == 토스라 불일치로 안 잡혀 영영 핀이 안 생긴다(10/14 3차 검토 재현 — 다음 갱신이 되돌린다).
            report_notes(quiet=True)
            save_cached(symbol, sorted(book.items(), key=lambda x: x[0]))
    return out


SRC_YAHOO_AUDIT = "Yahoo 일봉 종가 · 감사"
YAHOO_TOL = 0.001        # 캐시 ↔ Yahoo 종가 허용 상대오차(0.1%) — 장중값이 굳은 것은 보통 이보다 훨씬 크다
RESCALE_SHARE = 0.8      # 창 안 대조의 이 비율 이상이 **같은 배율**로 어긋나면 개별 오류가 아니라 소급 재조정(분할)이다
REBASE_RUN = 10          # 대조한 거래일이 이만큼 **연속으로** 어긋나면 개별 오류가 아니라 Yahoo의 과거 재기준이다


def _longest_run(dates: list, bad: set) -> int:
    """dates(대조한 거래일 순서) 안에서 bad에 속한 날이 끊김 없이 이어진 최장 길이."""
    best = cur = 0
    for d in dates:
        cur = cur + 1 if d in bad else 0
        best = max(best, cur)
    return best


def audit_yahoo(days: int = 400, symbols=None, fix: bool = False, fetch=None, pace: float = 0.6,
                now: int | None = None, deadline: float | None = None) -> dict:
    """국내 개별종목(.KS/.KQ)을 뺀 캐시(美 종목·지수·매크로·검증용 해외지수 · ^KS11/^KQ11 포함)의 최근 N일을
    **Yahoo 일봉 종가와 대조**한다(읽기 전용 · fix면 Yahoo 값으로 고쳐 쓴다).

    ★[2026-10-19 신설] ^VIX 캐시에 **종가가 아니라 장중값**이 4건 굳어 있었다(7/21·7/22·7/30·8/3 — 7/30 19.38 ↔
      종가 17.09가 정본 '저점 VIX 19.4'의 출처). 개정창 upsert(8/13)·진행 세션 제외(10/16)보다 먼저 쓰인 값이라
      어느 장치도 다시 보지 않았다. 국내 종목은 audit_kr(토스)이 같은 자리를 보지만 나머지는 아무도 안 봤다.
    해외·지수의 정본은 Yahoo다 → 고친 값은 다음 Yahoo 갱신이 되돌리지 않는다(국내처럼 핀이 필요 없다).
    · mismatch  = 같은 날짜인데 |캐시/Yahoo − 1| > 0.1%
    · rescaled  = 창 안 대조의 80%+가 같은 배율로 어긋남 = Yahoo가 소급 재조정(분할) → 개별 수정 대신 `--refresh`
    · extra     = 캐시엔 있는데 Yahoo엔 없는 날짜(옛 날짜 라벨 버그의 흔적일 수 있다) — 지우지 않고 보고만
    · missing   = Yahoo엔 있는데 캐시엔 없는 날짜(개정창보다 오래된 구멍) — fix면 채운다
    · pending   = 캐시엔 있는데 Yahoo는 아직 '끝나지 않은 세션'이라 안 준 날짜(장중에 쓰인 값 — 다음 갱신이 덮는다)
    · errors    = Yahoo를 못 받은 심볼 · skipped = 시간 예산(deadline)이 끝나 못 본 심볼 — **둘 다 '불일치 없음'이 아니다**
    """
    fetch = fetch or (lambda s, p1: fetch_with_backoff(s, period1=p1, with_gaps=True))
    now_ts = int(now if now is not None else time.time())
    start = (dt.datetime.fromtimestamp(now_ts, dt.timezone.utc).date() - dt.timedelta(days=days)).isoformat()  # label-ok: 감사 창 시작일(봉 라벨 아님)
    p1 = max(0, now_ts - (days + 3) * 86400)
    if symbols is None:
        symbols = [s for _, s in _universe() if not s.upper().endswith(KR_SUFFIX)]
    out = {"days": days, "symbols": 0, "checked": 0, "mismatch": [], "rescaled": [], "extra": [],
           "missing": [], "pending": 0, "unverifiable": 0, "fixed": 0, "filled": 0, "errors": [], "skipped": []}
    for i, sym in enumerate(symbols):
        if deadline is not None and time.monotonic() > deadline:
            out["skipped"] = list(symbols[i:])
            break
        if i and pace:
            time.sleep(pace)
        rows = load_cached(sym)
        if not rows:
            continue
        got = fetch(sym, p1)
        if not got or not got[0]:
            out["errors"].append(sym)
            continue
        fresh, gaps = got
        yh, gapset, book = dict(fresh), set(gaps or []), dict(rows)
        last_y = fresh[-1][0]
        out["symbols"] += 1
        mm, checked = [], 0
        for d, c in rows:
            if d < start:
                continue
            y = yh.get(d)
            if y is None:
                if d in gapset:
                    out["unverifiable"] += 1
                elif d > last_y:
                    out["pending"] += 1
                else:
                    out["extra"].append({"symbol": sym, "date": d, "cached": c})
                continue
            checked += 1
            if abs(c - y) > max(1e-4, abs(y) * YAHOO_TOL):
                mm.append({"symbol": sym, "date": d, "cached": c, "yahoo": round(float(y), 4),
                           "pct": round((c / y - 1) * 100, 3) if y else None})
        out["checked"] += checked
        # 캐시 마지막 날짜 뒤의 Yahoo 봉은 '아직 안 받은 것'(증분 갱신 몫)이지 구멍이 아니다 — 매일 저녁 아시아 지수가 걸린다
        miss = [d for d in sorted(yh) if start <= d < rows[-1][0] and d not in book]
        ratios = [m["cached"] / m["yahoo"] for m in mm if m["yahoo"]]
        run = _longest_run([d for d, _ in rows if d >= start and d in yh], {m["date"] for m in mm})
        if ratios and ((len(mm) >= 5 and len(mm) >= RESCALE_SHARE * checked and max(ratios) / min(ratios) < 1.01)
                       or run >= REBASE_RUN):
            # 굳은 장중값은 **띄엄띄엄** 난다(그날 장중에 돌린 날만). 연속 구간 전체가 어긋나면 Yahoo가 과거를 다시 쓴 것이다
            #   — 분할 소급(같은 배율) 또는 연속선물 롤오버 재기준(배율이 천천히 변한다 · 10/19 GC=F 216일 -1.0~-1.8%).
            out["rescaled"].append({"symbol": sym, "ratio": round(sorted(ratios)[len(ratios) // 2], 4), "n": len(mm),
                                    "run": run, "from": mm[0]["date"], "to": mm[-1]["date"]})
            mm = []                     # 개별 날짜로 고치면 창 밖과 단위가 갈린다 — 전체 재풀로만
        out["mismatch"] += mm
        out["missing"] += [{"symbol": sym, "date": d, "yahoo": round(float(yh[d]), 4)} for d in miss]
        if fix and (mm or miss):
            for m in mm:
                book[m["date"]] = m["yahoo"]
                NOTES.append({"symbol": sym, "date": m["date"], "kind": "patched", "old": m["cached"],
                              "new": m["yahoo"], "src": SRC_YAHOO_AUDIT})
            for d in miss:
                book[d] = round(float(yh[d]), 4)
                NOTES.append({"symbol": sym, "date": d, "kind": "patched", "old": None,
                              "new": book[d], "src": SRC_YAHOO_AUDIT})
            save_cached(sym, sorted(book.items(), key=lambda x: x[0]))
            out["fixed"] += len(mm)
            out["filled"] += len(miss)
    return out


def _fmt_audit_yahoo(res: dict) -> str:
    lines = [f"■ 캐시 ↔ Yahoo 일봉 종가 감사(국내 개별종목 제외) — 최근 {res['days']}일 · 심볼 {res['symbols']} · "
             f"대조 {res['checked']}건 · 불일치 {len(res['mismatch'])}건"
             + (f" · 재조정 의심 {len(res['rescaled'])}종목" if res["rescaled"] else "")
             + (f" · 빈 날짜 {len(res['missing'])}건" if res["missing"] else "")
             + (f" · Yahoo에 없는 날짜 {len(res['extra'])}건" if res["extra"] else "")
             + (f" · 고침 {res['fixed']}건·채움 {res['filled']}건" if res.get("fixed") or res.get("filled") else "")]
    for m in res["mismatch"][:40]:
        lines.append(f"  ⚠️ {m['symbol']:<10} {m['date']}  캐시 {m['cached']:>12,.4f} ↔ Yahoo {m['yahoo']:>12,.4f} "
                     f"({m['pct']:+.2f}%)")
    if len(res["mismatch"]) > 40:
        lines.append(f"  … 외 {len(res['mismatch']) - 40}건")
    for r in res["rescaled"]:
        lines.append(f"  ⚠️ {r['symbol']} — {r['n']}건({r.get('from')}~{r.get('to')} · 최장 연속 {r.get('run')}일 · 중앙 배율 "
                     f"{r['ratio']})이 한 덩어리로 어긋남 = Yahoo가 과거를 재기준(분할·연속선물 롤오버) · 개별 수정 안 함 → "
                     f"`--refresh --symbols {r['symbol']}`")
    for m in res["missing"][:10]:
        lines.append(f"  · 빈 날짜 {m['symbol']} {m['date']} (Yahoo {m['yahoo']:,.4f})")
    for m in res["extra"][:10]:
        lines.append(f"  · Yahoo에 없는 날짜 {m['symbol']} {m['date']} (캐시 {m['cached']:,.4f}) — 지우지 않음, `--refresh`로 확인")
    if res["errors"]:
        lines.append(f"  ⚠️ Yahoo를 못 받음 {len(res['errors'])}종목: {', '.join(res['errors'][:12])} — 이 심볼들은 본 게 없다")
    if res["skipped"]:
        lines.append(f"  ⚠️ 시간 예산 끝 — 못 본 {len(res['skipped'])}종목: {', '.join(res['skipped'][:12])}")
    if not res["checked"]:
        lines.append("  ⚠️ 대조한 날짜가 0건이다 — '불일치 없음'이 아니라 본 게 없다")
    elif not (res["mismatch"] or res["rescaled"]):
        lines.append("  ✅ 대조한 날짜는 전부 일치")
    if res["mismatch"] and not res.get("fixed"):
        lines.append(f"  → 값을 확인한 뒤 `history_backfill.py --audit-yahoo {res['days']} --fix`(Yahoo 값으로 교체 · 원장 기록)")
    return "\n".join(lines)


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


def _note_key(r: dict) -> tuple:
    """원장 중복 제거 키. patched는 **출처까지** 본다 — 같은 값쌍의 결측 보정 기록이 이미 있다고 감사 기록(SRC_AUDIT)을
    건너뛰면 핀이 안 생긴다(10/14 검토에서 재현: 고쳤다고 출력하고 원장엔 아무것도 안 남았다).
    미검증은 출처 문구에 참고값이 섞여 있어 종전대로 값까지만 본다(매 실행 같은 줄이 쌓이지 않게)."""
    return (r.get("symbol"), r.get("date"), r.get("kind"), r.get("old"), r.get("new"),
            r.get("src") if r.get("kind") == "patched" else None)


def report_notes(quiet: bool = False) -> None:
    """이번 실행의 결측 보정·미검증을 출력하고 원장(_gapfill.jsonl)에 남긴다. quiet = 출력 없이 원장에만(--json)."""
    if not NOTES:
        return
    def px(v):              # 국내 종목(원)은 정수, 지수·VIX·금리·환율은 소수 — 17.09를 '17'로 찍으면 고친 게 안 보인다
        return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:,.4f}"

    if not quiet:
        print("\n결측 봉 처리:")
        for n in NOTES:
            if n["kind"] == "patched":
                was = "신규" if n["old"] is None else f"{px(n['old'])} →"
                print(f"  🔧 {n['symbol']} {n['date']}  {was} {px(n['new'])}  [{n['src']}]")
            else:
                print(f"  ⚠️ {n['symbol']} {n['date']}  캐시 {n['old']:,.4g} 미검증 — {n['src']}")
    stamp = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    seen = {_note_key(r) for r in _log_rows()}   # 같은 기록은 한 번만 — 매 실행 같은 미검증이 쌓이지 않게
    try:
        with open(GAPFILL_LOG, "a", encoding="utf-8", newline="\n") as f:
            for n in NOTES:
                key = _note_key(n)
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
    ap.add_argument("--audit", nargs="?", const=7, type=int, metavar="N",
                    help="국내 종목 캐시의 최근 N거래일(기본 7)을 토스 KRX 종가와 대조(읽기 전용)")
    ap.add_argument("--audit-yahoo", nargs="?", const=400, type=int, metavar="N",
                    help="국내 개별종목을 뺀 캐시(美·지수·매크로)의 최근 N일(기본 400)을 Yahoo 일봉 종가와 대조(읽기 전용)")
    ap.add_argument("--fix", action="store_true",
                    help="--audit/--audit-yahoo와 함께만: 불일치를 토스(국내)·Yahoo(그 외) 값으로 고쳐 쓴다"
                         "(사람이 확인한 뒤 수동으로 — 무인 경로 금지)")
    ap.add_argument("--max-sec", type=float, metavar="S",
                    help="--audit-yahoo와 함께: S초가 지나면 남은 심볼은 skipped로 남기고 끝낸다(마감 대사의 시간 예산용)")
    ap.add_argument("--selftest", action="store_true", help="결측 봉 보정·매니페스트 병합 자가검증(오프라인)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.fix and args.audit is None and args.audit_yahoo is None:
        # --fix만 주면 조용히 무시되고 평소 증분 갱신이 돌았다 — 고쳤다고 믿게 만드는 침묵이다.
        ap.error("--fix는 --audit 또는 --audit-yahoo와 함께만 쓴다 (예: --audit 7 --fix)")
    if args.audit is not None and args.audit_yahoo is not None:
        ap.error("--audit(국내·토스)과 --audit-yahoo(그 외·Yahoo)는 따로 돌린다")

    only = [s.strip() for s in cli_common.split_tickers(args.symbols)] if args.symbols else None

    if args.audit_yahoo is not None:
        res = audit_yahoo(max(1, args.audit_yahoo), fix=args.fix, pace=min(args.pace, 0.6),
                          symbols=[s for s in only if not s.upper().endswith(KR_SUFFIX)] if only else None,
                          deadline=(time.monotonic() + args.max_sec) if args.max_sec else None)
        if args.fix and (res["fixed"] or res["filled"]):
            report_notes(quiet=args.json)
            write_manifest(build_stats(), partial=False)
        print(json.dumps(res, ensure_ascii=False, indent=1) if args.json else _fmt_audit_yahoo(res))
        return 0

    if args.audit is not None:
        res = audit_kr(max(1, args.audit), fix=args.fix,
                       symbols=[s.upper() for s in only if s.upper().endswith(KR_SUFFIX)] if only else None)
        if args.fix and res["fixed"]:
            report_notes(quiet=args.json)
            # 고쳤다고 말하기 전에 원장에서 되읽는다 — 핀이 안 남았으면 다음 갱신이 되돌린다
            res["pinned"] = sum(1 for m in res["mismatch"]
                                if audit_pins(m["symbol"]).get(m["date"]) == round(float(m["toss"]), 4))
        print(json.dumps(res, ensure_ascii=False, indent=1) if args.json else _fmt_audit(res))
        return 0

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


def _fmt_audit(res: dict) -> str:
    bad = (f"\n  ⚠️ 보정 원장(_gapfill.jsonl)에 못 읽은 줄 {res['ledger_bad']}개 — UTF-8로 저장됐는지 확인"
           "(감사가 고친 값의 고정이 풀렸을 수 있다)") if res.get("ledger_bad") else ""
    if res.get("error"):
        return f"■ 캐시 ↔ 토스 KRX 종가 감사 — 못 돌림: {res['error']}" + bad
    lines = [f"■ 캐시 ↔ 토스 KRX 종가 감사 — 최근 {res['days']}거래일 · 대조 {res['checked']}건 · "
             f"불일치 {len(res['mismatch'])}건 · 토스 미확인 {res['unresolved']}건"
             + (f" · 수정주가라 비교 제외 {res['adjusted']}건" if res.get("adjusted") else "")
             + (f" · 고침 {res['fixed']}건" if res.get("fixed") else "")]
    for m in res["mismatch"]:
        lines.append(f"  ⚠️ {m['symbol']:<10} {m['date']}  캐시 {m['cached']:>12,.0f} ↔ 토스 {m['toss']:>12,.0f} "
                     f"({m['pct']:+.2f}%)")
    if not res["mismatch"] and res["checked"]:
        lines.append("  ✅ 대조한 날짜는 전부 일치")
    if not res["checked"]:
        lines.append("  ⚠️ 대조한 날짜가 0건이다 — '불일치 없음'이 아니라 본 게 없다(토스 응답·캐시 확인)")
    if res.get("fixed"):
        if res.get("pinned") == res["fixed"]:
            lines.append("  (고친 날짜는 _gapfill.jsonl에 남아 이후 Yahoo 갱신·전체 재풀이 되돌리지 못한다 — 되돌리려면 그 줄을 지운다)")
        else:
            lines.append(f"  ⚠️ 고친 {res['fixed']}건 중 {res.get('pinned', 0)}건만 원장에 남았다 — 나머지는 다음 갱신이 되돌린다"
                         "(_gapfill.jsonl 쓰기 권한·내용 확인)")
    if res["unresolved"]:
        lines.append("  (미확인 = 토스 1분봉에서 종가 단일가 서명을 못 찾은 날 — 휴장·마감 전·단일가 무체결·장 시간 변경)")
    return "\n".join(lines) + bad


def selftest() -> int:
    """10/13 실사고를 그대로 심어 보정이 잡는지 확인한다(네트워크 없음)."""
    global MANIFEST, HIST_DIR, GAPFILL_LOG, fetch_with_backoff, _naver_daily, _naver_poll
    import contextlib
    import io
    import sys as _sys
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
    keep_toss = _TOSS[0]
    today = dt.date.today()
    dm2, dm1 = (today - dt.timedelta(days=2)).isoformat(), (today - dt.timedelta(days=1)).isoformat()
    t0 = today.isoformat()
    with tempfile.TemporaryDirectory() as td:
        try:
            _TOSS[0] = None                                                     # 키 없는 환경 = 네이버 경로
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
            # 토스 키가 있는 환경 = 토스 1분봉이 먼저 · 다 메우면 네이버를 부르지 않는다
            naver_calls = []
            _naver_daily = lambda *a, **k: naver_calls.append("daily")                       # noqa: E731
            _naver_poll = lambda *a, **k: naver_calls.append("poll")                         # noqa: E731
            _TOSS[0] = lambda code, d: 250500.0 if (code, d) == ("TEST", dm1) else None       # noqa: E731
            save_cached("TEST.KS", [(dm2, 262000.0), (dm1, 257000.0)])
            fetch_with_backoff = lambda *a, **k: ([(dm2, 262000.0), (t0, 232000.0)], [dm1])   # noqa: E731
            del NOTES[:]
            update_symbol("TEST.KS")
            toss_wired = (dict(load_cached("TEST.KS")).get(dm1) == 250500.0 and not naver_calls
                          and [x["src"] for x in NOTES] == [SRC_TOSS])
            # 감사 — Yahoo가 값을 줬는데 그 값이 틀린 경우(결측 봉 보정이 못 보는 자리)
            save_cached("AUD.KS", [(dm2, 262000.0), (dm1, 257000.0)])
            fake = lambda code, d: {dm2: 262000.0, dm1: 250500.0}.get(d) if code == "AUD" else None   # noqa: E731
            del NOTES[:]
            ro = audit_kr(7, symbols=["AUD.KS"], toss=fake)
            audit_ro = (ro["checked"] == 2 and [(m["date"], m["toss"]) for m in ro["mismatch"]] == [(dm1, 250500.0)]
                        and dict(load_cached("AUD.KS"))[dm1] == 257000.0 and not NOTES)
            fx = audit_kr(7, symbols=["AUD.KS"], toss=fake, fix=True)
            audit_fix = (fx["fixed"] == 1 and dict(load_cached("AUD.KS"))[dm1] == 250500.0
                         and dict(load_cached("AUD.KS"))[dm2] == 262000.0 and len(NOTES) == 1)
            un = audit_kr(7, symbols=["AUD.KS"], toss=lambda code, d: None)
            audit_un = un["unresolved"] == 2 and not un["mismatch"]
            save_cached("ADJ.KS", [(dm1, 1419364.0)])
            aj = audit_kr(7, symbols=["ADJ.KS"], toss=lambda code, d: 1417997.0, fix=True)
            audit_adj = (aj["adjusted"] == 1 and not aj["mismatch"] and not aj["fixed"]
                         and dict(load_cached("ADJ.KS"))[dm1] == 1419364.0)
            # 당일 행은 종가 단일가가 찍힌 뒤(15:42~)에만 본다 — 그 전엔 캐시도 토스도 장중값이다
            save_cached("TDY.KS", [(dm1, 250500.0), (t0, 233000.0)])            # 당일 행 = 장중 스냅샷
            tfake = lambda code, d: {dm1: 250500.0, t0: 232000.0}.get(d)        # noqa: E731
            a41 = audit_kr(7, symbols=["TDY.KS"], toss=tfake,
                           now=dt.datetime.combine(today, dt.time(15, 41), tzinfo=KST))
            a42 = audit_kr(7, symbols=["TDY.KS"], toss=tfake,
                           now=dt.datetime.combine(today, dt.time(15, 42), tzinfo=KST))
            audit_today = (a41["checked"] == 1 and not a41["mismatch"]
                           and a42["checked"] == 2 and [m["date"] for m in a42["mismatch"]] == [t0])
            # 감사가 고친 값을 다음 Yahoo 갱신이 되돌리지 못한다 — 원장의 감사 기록이 핀이다
            _TOSS[0] = None
            pinfake = lambda code, d: {dm2: 262000.0, dm1: 250500.0}.get(d)     # noqa: E731
            fetch_with_backoff = lambda *a, **k: ([(dm2, 262000.0), (dm1, 257000.0)], [])     # noqa: E731 — Yahoo는 계속 장중값
            save_cached("PIN.KS", [(dm2, 262000.0), (dm1, 257000.0)])
            del NOTES[:]
            audit_kr(7, symbols=["PIN.KS"], toss=pinfake, fix=True)
            wrote_first = audit_pins("PIN.KS") == {dm1: 250500.0}               # 고치는 순간 원장에 남는다(main을 안 거쳐도)
            os.remove(GAPFILL_LOG)                                              # 원장 기록이 없던 첫 판을 재현
            update_symbol("PIN.KS")
            unpinned = dict(load_cached("PIN.KS"))[dm1] == 257000.0             # = 되돌아간다(사고 재현)
            # 원장에 같은 값쌍의 **다른 출처** 기록과 깨진 줄들을 미리 심는다 — 그래도 감사 기록이 남고, 읽다가 죽지 않아야 한다
            with open(GAPFILL_LOG, "wb") as fh:
                fh.write((json.dumps({"symbol": "PIN.KS", "date": dm1, "kind": "patched", "old": 257000.0,
                                      "new": 250500.0, "src": SRC_POLL_PREV}, ensure_ascii=False) + "\n").encode("utf-8"))
                fh.write((json.dumps({"symbol": "PIN.KS", "date": dm2, "kind": "patched", "old": 262000.0,
                                      "new": 111.0, "src": SRC_POLL_PREV}, ensure_ascii=False) + "\n").encode("utf-8"))
                fh.write(b"[]\nnull\n{broken\n" + "깨진 인코딩".encode("cp949") + b"\n")
            not_audit = audit_pins("PIN.KS") == {}                              # 감사 기록이 아닌 patched는 핀이 아니다
            _TOSS[0] = pinfake
            keep_argv = _sys.argv
            _sys.argv = ["history_backfill.py", "--audit", "7", "--fix", "--symbols", "PIN.KS"]
            try:
                with contextlib.redirect_stdout(io.StringIO()) as buf:
                    main()                                                      # --fix가 실제로 타는 경로
            finally:
                _sys.argv = keep_argv
            said_pinned = "되돌리지 못한다" in buf.getvalue() and "🔧" in buf.getvalue()   # 고친 내역도 화면에 나온다
            _TOSS[0] = None
            update_symbol("PIN.KS")
            pinned = (dict(load_cached("PIN.KS")) == {dm2: 262000.0, dm1: 250500.0} and said_pinned
                      and audit_pins("PIN.KS") == {dm1: 250500.0})
            # 원장이 cp949로 재저장돼도(PowerShell 5.1 Get-Content | Set-Content) 핀은 ASCII 표지로 읽히고, 깨진 줄이 보고된다
            bad0 = LOG_BAD[0]
            raw_log = open(GAPFILL_LOG, "rb").read()
            with open(GAPFILL_LOG, "wb") as fh:
                fh.write(raw_log.decode("utf-8", errors="replace").encode("cp949", errors="replace"))
            pin_cp949 = audit_pins("PIN.KS") == {dm1: 250500.0} and LOG_BAD[0] > bad0
            cp_audit = audit_kr(7, symbols=["PIN.KS"], toss=pinfake)
            ledger_bad = cp_audit["ledger_bad"] > bad0 and "못 읽은 줄" in _fmt_audit(cp_audit)
            pin_line = [ln for ln in raw_log.split(b"\n") if b'"pin": true' in ln][0]
            with open(GAPFILL_LOG, "wb") as fh:                                 # BOM이 붙은 원장(메모장 저장) — 첫 줄이 핀
                fh.write(b"\xef\xbb\xbf" + pin_line + b"\n")
            pin_bom = audit_pins("PIN.KS") == {dm1: 250500.0} and LOG_BAD[0] == 0 and audit_pins("pin.ks") == {dm1: 250500.0}
            with open(GAPFILL_LOG, "wb") as fh:
                fh.write(raw_log)
            # 소문자 접미사로 불러도(--symbols low.ks) 핀은 캐시 파일과 같은 이름으로 남는다
            save_cached("LOW.KS", [(dm2, 262000.0), (dm1, 257000.0)])
            _TOSS[0] = pinfake
            _sys.argv = ["history_backfill.py", "--audit", "7", "--fix", "--symbols", "low.ks", "--json"]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    main()
            finally:
                _sys.argv = keep_argv
            _TOSS[0] = None
            pin_case = (any(r.get("symbol") == "LOW.KS" and r.get("pin") is True for r in _log_rows())
                        and dict(load_cached("LOW.KS"))[dm1] == 250500.0)
            # --fix가 도중에 끊겨도(Ctrl-C) 이미 고친 종목의 핀은 원장에 있다 — 캐시보다 원장을 먼저 쓴다
            save_cached("INT1.KS", [(dm1, 257000.0)])
            save_cached("INT2.KS", [(dm1, 257000.0)])

            def cut(code, d):
                if code == "INT2":
                    raise KeyboardInterrupt
                return 250500.0
            del NOTES[:]
            try:
                audit_kr(7, symbols=["INT1.KS", "INT2.KS"], toss=cut, fix=True)
            except KeyboardInterrupt:
                pass
            pin_atomic = dict(load_cached("INT1.KS"))[dm1] == 250500.0 and audit_pins("INT1.KS") == {dm1: 250500.0}
            # Yahoo가 핀 날짜의 봉을 비우고 네이버 기준가가 다른 값(권리락 조정 기준가 등)을 줘도 핀을 덮지 못한다
            fetch_with_backoff = lambda *a, **k: ([(dm2, 262000.0), (t0, 232000.0)], [dm1])   # noqa: E731
            _naver_daily = lambda *a, **k: {dm1: (251000.0, 248000.0, 262500.0),             # noqa: E731
                                            t0: (234000.0, 228000.0, 247500.0)}
            _naver_poll = lambda *a, **k: {"date": t0, "time": "17:13:04",                   # noqa: E731
                                           "close": 234000.0, "prev": 249000.0}
            del NOTES[:]
            update_symbol("PIN.KS")
            pin_naver = dict(load_cached("PIN.KS")).get(dm1) == 250500.0 and not NOTES
            # 개정창 밖 날짜를 고친 뒤 전체 재풀 — Yahoo 값으로 되돌아가면 안 된다
            d10 = (today - dt.timedelta(days=10)).isoformat()
            save_cached("OLD.KS", [(d10, 257000.0), (dm1, 232000.0)])
            del NOTES[:]
            audit_kr(30, symbols=["OLD.KS"], toss=lambda code, d: {d10: 250500.0, dm1: 232000.0}.get(d), fix=True)
            with contextlib.redirect_stdout(io.StringIO()):
                report_notes()
            fetch_with_backoff = lambda *a, **k: ([(d10, 257000.0), (dm1, 232000.0)], [])    # noqa: E731
            update_symbol("OLD.KS", refresh=True)
            pin_refresh = dict(load_cached("OLD.KS")) == {d10: 250500.0, dm1: 232000.0}
            # 재풀인데 Yahoo가 그 날짜 봉까지 비운 경우 — 핀 날짜가 통째로 빠지면 안 된다
            fetch_with_backoff = lambda *a, **k: ([(dm1, 232000.0)], [d10])                   # noqa: E731
            update_symbol("OLD.KS", refresh=True)
            pin_gap = dict(load_cached("OLD.KS")) == {d10: 250500.0, dm1: 232000.0}
            # 분할·권리락으로 Yahoo가 시계열을 소급 조정하면 옛 단위의 핀은 쓰지 않고 메모를 남긴다
            fetch_with_backoff = lambda *a, **k: ([(d10, 51400.0), (dm1, 46400.0)], [])      # noqa: E731 — 5대1 분할 뒤
            del NOTES[:]
            update_symbol("OLD.KS", refresh=True)
            pin_split = (dict(load_cached("OLD.KS")) == {d10: 51400.0, dm1: 46400.0}
                         and [n["kind"] for n in NOTES] == ["unverified"] and "핀" in NOTES[0]["src"])
            fetch_with_backoff = lambda *a, **k: ([(dm1, 46400.0)], [d10])                   # noqa: E731 — 분할 + 그날 봉 결측
            del NOTES[:]
            update_symbol("OLD.KS", refresh=True)
            pin_split_gap = dict(load_cached("OLD.KS")) == {dm1: 46400.0} and len(NOTES) == 1
            fetch_with_backoff = lambda *a, **k: ([(d10, 256871.3), (dm1, 231883.9)], [])    # noqa: E731 — 격자 밖 = 수정주가
            del NOTES[:]
            update_symbol("OLD.KS", refresh=True)
            pin_adj = dict(load_cached("OLD.KS"))[d10] == 256871.3 and len(NOTES) == 1
            # Yahoo가 KRX 종가와 15% 넘게 다른 값을 **그대로** 주는 날(하한가 날의 굳은 장중값) — 재조정이 아니므로 핀을 지킨다
            fetch_with_backoff = lambda *a, **k: ([(dm2, 100000.0), (dm1, 100000.0)], [])    # noqa: E731
            save_cached("BIG.KS", [(dm2, 100000.0), (dm1, 100000.0)])
            del NOTES[:]
            audit_kr(7, symbols=["BIG.KS"], toss=lambda code, d: {dm2: 100000.0, dm1: 85000.0}.get(d), fix=True)
            del NOTES[:]
            update_symbol("BIG.KS")
            pin_far = dict(load_cached("BIG.KS")) == {dm2: 100000.0, dm1: 85000.0} and not NOTES
            # --fix만 주면 거부 — 가드가 빠지면 실제 수집이 돌지 않게 수집 함수를 '불리면 실패'로 막고 확인한다
            ran = []
            keep_us, keep_uni, keep_man = update_symbol, _universe, MANIFEST
            try:
                MANIFEST = os.path.join(td, "_manifest.json")       # 가드가 빠져 끝까지 달려도 진짜 매니페스트는 안 건드린다
                globals()["update_symbol"] = lambda *a, **k: ran.append(a) or ([], 0)
                globals()["_universe"] = lambda *a, **k: [("x", "X.KS")]
                _sys.argv = ["history_backfill.py", "--fix"]
                try:
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        main()
                    fix_alone = False
                except SystemExit as e:
                    fix_alone = e.code == 2 and not ran
            finally:
                globals()["update_symbol"], globals()["_universe"] = keep_us, keep_uni
                MANIFEST = keep_man
                _sys.argv = keep_argv
            audit_nokey = bool(audit_kr(7, symbols=["AUD.KS"])["error"])
        finally:
            HIST_DIR, GAPFILL_LOG, fetch_with_backoff, _naver_daily, _naver_poll = keep_all
            _TOSS[0] = keep_toss
            del NOTES[:]
    ok("배선: update_symbol이 결측 봉을 받아 CSV의 장중값을 기준가로 바꾼다", wired)
    ok("배선: 국내 종목이 아니면 값은 두고 '미검증'만 남긴다", flagged)
    ok("배선: 토스가 되면 토스 1분봉으로 메우고 네이버는 부르지 않는다", toss_wired)
    ok("감사: 캐시 ↔ 토스 불일치를 찾되 기본은 읽기 전용", audit_ro)
    ok("감사 --fix: 불일치만 고치고 기록을 남긴다", audit_fix)
    ok("감사: 토스가 못 준 날은 불일치가 아니라 '미확인'", audit_un)
    ok("감사: 키가 없으면 '전부 일치'가 아니라 못 돌렸다고 말한다", audit_nokey)
    ok("감사: 당일 행은 15:41엔 빼고 15:42부터 본다(장중값끼리 대조하지 않는다)", audit_today)
    ok("감사 --fix: 원장에 안 남기면 다음 Yahoo 갱신이 되돌린다(사고 재현)", unpinned)
    ok("감사 --fix(main 경로): 원장에 남긴 수정값은 Yahoo 갱신이 못 되돌린다 · 같은 값쌍의 다른 출처 기록이 있어도 남는다", pinned)
    ok("핀: 감사 기록이 아닌 patched 줄은 핀이 아니다 · 깨진 줄([]·null·잘린 JSON·cp949)에 죽지 않는다", not_audit)
    ok("핀: Yahoo가 그 날짜를 비우고 네이버 기준가가 다른 값을 줘도 덮이지 않는다(미검증 메모도 없다)", pin_naver)
    ok("핀: 개정창 밖 날짜도 전체 재풀(--refresh)에서 지켜진다", pin_refresh)
    ok("핀: 재풀 + Yahoo가 그 날짜 봉을 비워도 빠지지 않는다", pin_gap)
    ok("핀: 고치는 순간 원장에 남는다 — 도중에 끊겨도(Ctrl-C) 고친 종목의 핀은 있다", wrote_first and pin_atomic)
    ok("핀: 원장이 cp949로 재저장돼도 읽힌다(ASCII 표지) · BOM이 붙어도 · 심볼 대소문자가 달라도", pin_cp949 and pin_bom)
    ok("감사: 원장에 못 읽은 줄이 있으면 결과(ledger_bad)와 출력에 올린다", ledger_bad)
    ok("핀: 소문자 접미사(--symbols low.ks)로 고쳐도 핀은 캐시 파일과 같은 이름으로 남는다", pin_case)
    ok("핀: 분할 뒤 옛 단위의 핀은 쓰지 않고 메모를 남긴다(같은 날 비교 · 그날 봉 결측이면 가까운 날 비교 · 격자 밖)",
       pin_split and pin_split_gap and pin_adj)
    ok("핀: Yahoo가 고치기 전 값을 그대로 주면(15% 넘게 틀려도) 재조정이 아니다 → 핀을 지킨다", pin_far)
    ok("--fix만 주면 조용히 증분 갱신하지 않고 거부한다(종료코드 2 · 수집 함수 미호출)", fix_alone)
    ok("호가단위: 실제 체결가는 격자 위(232,000 · 62,000 · 18,010 · 1,443,000)",
       all(on_tick(v) for v in (232000.0, 62000.0, 18010.0, 1443000.0)))
    ok("호가단위: 수정주가는 격자 밖(1,419,364 · 232,100)", not on_tick(1419364.0) and not on_tick(232100.0))
    ok("호가단위 경계: 1,999·2,000·199,900·200,000·499,500·500,000은 격자 위",
       all(on_tick(v) for v in (1999.0, 2000.0, 199900.0, 200000.0, 499500.0, 500000.0)))
    ok("호가단위 경계: 2,001·199,950·200,100·500,500은 격자 밖",
       not any(on_tick(v) for v in (2001.0, 199950.0, 200100.0, 500500.0)))
    ok("감사: 수정주가끼리 다른 것은 불일치가 아니라 '비교 제외'", audit_adj)

    # 토스를 못 쓰는 이유 — '키 없음'(설정)과 '토큰 발급 실패'(장애)를 가른다. 뭉치면 장애가 정상처럼 읽힌다.
    import toss_snapshot as _T
    env_keys = ("TOSS_CLIENT_ID", "TOSS_CLIENT_SECRET")
    keep_env, keep_req, keep_why = {k: os.environ.get(k) for k in env_keys}, _T.req, TOSS_WHY[0]
    try:
        for k in env_keys:
            os.environ.pop(k, None)
        nokey = toss_source() is None and TOSS_WHY[0] == TOSS_NO_KEY
        _TOSS[0] = None
        a_nokey = audit_kr(7, symbols=[])
        for k in env_keys:
            os.environ[k] = "selftest"                     # 가짜 값 — 요청은 아래에서 막는다(네트워크 없음)
        _T.req = lambda *a, **k: None                      # noqa: E731 — 토큰 발급 실패(403·장애)
        tokfail = toss_source() is None and "토큰 발급 실패" in TOSS_WHY[0]
        a_tok = audit_kr(7, symbols=[])
    finally:
        _T.req, TOSS_WHY[0], _TOSS[0] = keep_req, keep_why, keep_toss
        for k, v in keep_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    ok("토스: 키가 없으면 이유 = '키 없음' · 감사 no_key = True", nokey and a_nokey["no_key"] and a_nokey["error"])
    ok("토스: 키는 있는데 토큰이 안 나오면 이유 = '토큰 발급 실패' · no_key = False(장애)",
       tokfail and a_tok["no_key"] is False and "토큰 발급 실패" in a_tok["error"])

    # 토스 1분봉 서명 — 15:31 종가 단일가 뒤 15:32~15:40 무거래
    def bars(day="2026-10-13", px=232000, pre=232500, at=31, auction=2060007, other=None, n=TOSS_BARS):
        """15:40→15:22. at = 종가 단일가 봉의 분 · pre = 단일가 전 가격 · other = {분: 거래량}(끼어든 거래)."""
        out = []
        for m in range(40, 40 - TOSS_BARS, -1):
            v = auction if m == at else (other or {}).get(m, 0)
            out.append({"timestamp": f"{day}T15:{m:02d}:00.000+09:00",
                        "closePrice": str(px if m >= at else pre), "volume": str(v)})
        return out[:n]
    ok("토스 서명 일치(단일가 15:31) → KRX 종가 232,000", krx_close_from_bars(bars(), "2026-10-13") == 232000.0)
    ok("KRX 단독 종목(단일가 15:30)도 읽는다", krx_close_from_bars(bars(at=30), "2026-10-13") == 232000.0)
    ok("단일가가 연장된 날(15:33)도 읽는다", krx_close_from_bars(bars(at=33), "2026-10-13") == 232000.0)
    ok("휴장일(직전 거래일 봉이 온다) → None", krx_close_from_bars(bars("2026-10-08"), "2026-10-09") is None)
    ok("단일가 뒤에 거래가 또 있으면(마감이 늦는 날) → None",
       krx_close_from_bars(bars(other={36: 1200}), "2026-10-13") is None)
    ok("단일가 전에 거래가 있으면(연속 거래 중) → None",
       krx_close_from_bars(bars(other={25: 300}), "2026-10-13") is None)
    ok("단일가 봉이 15:36 이후면(뒤가 너무 짧다) → None", krx_close_from_bars(bars(at=37), "2026-10-13") is None)
    ok("단일가 창의 경계: 15:35는 읽고 15:36·15:29는 안 읽는다",
       krx_close_from_bars(bars(at=35), "2026-10-13") == 232000.0
       and krx_close_from_bars(bars(at=36), "2026-10-13") is None
       and krx_close_from_bars(bars(at=29), "2026-10-13") is None)
    shifted = [dict(b, timestamp=f"2026-10-13T15:{39 - i:02d}:00.000+09:00") for i, b in enumerate(bars())]
    ok("봉 19개가 1분 밀려 오면(15:39→15:21 · 마감 직전 조회) → None",
       krx_close_from_bars(shifted, "2026-10-13") is None)
    ok("종가 단일가 체결이 없으면 → None", krx_close_from_bars(bars(auction=0), "2026-10-13") is None)
    mixed = bars()
    mixed[3] = dict(mixed[3], closePrice="232500")
    ok("단일가 뒤 가격이 한 줄이 아니면 → None", krx_close_from_bars(mixed, "2026-10-13") is None)
    ok("봉이 모자라면(마감 전) → None", krx_close_from_bars(bars(n=6), "2026-10-13") is None)
    ok("빈 응답 → None", krx_close_from_bars([], "2026-10-13") is None and krx_close_from_bars(None, "x") is None)
    # 출처 순서 — 토스 > 네이버 기준가 > 네이버 일봉
    tfn = lambda code, d: {"2026-10-12": 250500.0, "2026-10-13": 232000.0}.get(d)             # noqa: E731
    both = kr_gap_fill("005930.KS", ["2026-10-12", "2026-10-13"], now=after, daily={}, poll=None, toss=tfn)
    ok("토스가 주면 토스 값 · 애프터마켓 중에도 당일 종가(232,000)를 메운다",
       both == {"2026-10-12": (250500.0, SRC_TOSS), "2026-10-13": (232000.0, SRC_TOSS)})
    ok("토스가 못 주는 날만 네이버로 물러난다",
       kr_gap_fill("005930.KS", ["2026-10-08", "2026-10-12"], now=after, daily=daily, poll=poll,
                   toss=lambda code, d: 262000.0 if d == "2026-10-08" else None)
       == {"2026-10-08": (262000.0, SRC_TOSS), "2026-10-12": (250500.0, SRC_POLL_PREV)})
    ok("토스 값은 근사가 아니다 — 캐시의 기존 값을 덮는다",
       dict(merge_rows([("2026-10-12", 251000.0)], fresh, {"2026-10-12": (250500.0, SRC_TOSS)},
                       "2026-10-06")[0])["2026-10-12"] == 250500.0)
    ok("미래 날짜는 토스가 값을 줘도 메우지 않는다",
       kr_gap_fill("005930.KS", ["2026-10-14"], now=after, daily={}, poll=None, toss=lambda code, d: 240000.0) == {})
    # 토스가 수정주가(격자 밖)를 주면 KRX 종가로 쓰지 않는다 — 네이버에 먼저 묻고, 그래도 비면 근사로만
    adjfn = lambda code, d: 250512.0                                                          # noqa: E731
    ok("토스 값이 격자 밖(수정주가)이면 네이버 기준가가 먼저다",
       kr_gap_fill("005930.KS", ["2026-10-12"], now=after, daily=daily, poll=poll, toss=adjfn)
       == {"2026-10-12": (250500.0, SRC_POLL_PREV)})
    only_adj = kr_gap_fill("005930.KS", ["2026-10-12"], now=after, daily={}, poll=None, toss=adjfn)
    ok("네이버도 못 주면 토스 수정주가를 '근사'로 표기해 채운다",
       only_adj == {"2026-10-12": (250512.0, SRC_TOSS_ADJ)})
    ok("네이버 일봉이 다른 날짜만 줘도 토스 수정주가(근사)는 빠지지 않는다",
       kr_gap_fill("005930.KS", ["2026-10-12"], now=after, daily={"2026-10-08": (263000.0, 262000.0, 270000.0)},
                   poll=None, toss=adjfn) == {"2026-10-12": (250512.0, SRC_TOSS_ADJ)})
    ok("근사로 표기된 토스 수정주가는 캐시의 기존 값을 못 덮는다(빈 날짜만)",
       dict(merge_rows([("2026-10-12", 250500.0)], fresh, only_adj, "2026-10-06")[0])["2026-10-12"] == 250500.0
       and dict(merge_rows([("2026-10-08", 262000.0)], fresh, only_adj, "2026-10-06")[0])["2026-10-12"] == 250512.0)

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

    # ★[10/16] 정규장 진행 중인 세션의 봉은 쓰지 않는다(美 장중 23:4x KST 실행 → 10/16 장중값 고착)
    o15, o16 = calendar.timegm((2026, 10, 15, 13, 30, 0)), calendar.timegm((2026, 10, 16, 13, 30, 0))
    res = {"timestamp": [o15, o16], "indicators": {"quote": [{"close": [7744.06, 7732.59]}]},
           "meta": {"gmtoffset": -14400,
                    "currentTradingPeriod": {"regular": {"start": o16, "end": o16 + 23400}}}}
    rows, gaps = parse_chart(res, o16 + 4500)                        # 개장 75분 뒤
    ok("美 장중: 진행 중 세션(10/16) 봉 제외 · 결측으로도 안 셈",
       rows == [("2026-10-15", 7744.06)] and gaps == [])
    rows, _ = parse_chart(res, o16 + 23400 + 60)                    # 마감 1분 뒤 — 종가 확정 유예 안
    ok("美 마감 1분 뒤: 아직 안 쓴다(종가 경매·지수 확정 유예 40분)", rows == [("2026-10-15", 7744.06)])
    rows, _ = parse_chart(res, o16 + 23400 + SETTLE_GRACE_SEC + 60)  # 유예 지난 뒤
    ok("美 마감+유예 뒤: 10/16 봉 기록", rows[-1] == ("2026-10-16", 7732.59))
    rows, _ = parse_chart(res, o16 - 3 * 3600)                       # ★[10/19] 장 시작 3시간 전(장전 거래)
    ok("장 시작 전에 와 있는 그날 봉은 안 쓴다(장전값)", rows == [("2026-10-15", 7744.06)])
    res["indicators"]["quote"][0]["close"] = [7744.06, None]
    rows, gaps = parse_chart(res, o16 + 4500)
    ok("美 장중 미형성 봉(null)은 결측이 아니다", gaps == [] and rows == [("2026-10-15", 7744.06)])
    res["meta"].pop("currentTradingPeriod")
    rows, _ = parse_chart({**res, "indicators": {"quote": [{"close": [7744.06, 7732.59]}]}}, o16 + 4500)
    ok("meta에 거래시간이 없으면 舊 동작 그대로(개정창이 보정)", len(rows) == 2)
    # ★[10/22] 끝난 세션의 봉이 null로 오면 meta 정규장 종가로 읽는다(실시간 판단 전용 — ANET 10/21 null ↔ meta 184.33)
    o21 = calendar.timegm((2026, 10, 21, 13, 30, 0))
    nb = {"timestamp": [o21 - 86400, o21], "indicators": {"quote": [{"close": [181.19, None]}]},
          "meta": {"gmtoffset": -14400, "regularMarketPrice": 184.33, "regularMarketTime": o21 + 23400 + 3,
                   "currentTradingPeriod": {"regular": {"start": o21, "end": o21 + 23400}}}}
    ok("끝난 세션 null 봉 → meta 종가 (10/21, 184.33)", settled_meta_close(nb, o21 + 23400 + 5 * 3600) == ("2026-10-21", 184.33))
    ok("유예(40분) 전엔 안 읽는다", settled_meta_close(nb, o21 + 23400 + 600) is None)
    ok("봉에 값이 있으면 안 읽는다(봉이 정본)",
       settled_meta_close({**nb, "indicators": {"quote": [{"close": [181.19, 184.0]}]}}, o21 + 23400 + 5 * 3600) is None)
    ok("regularMarketTime이 장중이면 안 읽는다(종가 아님)",
       settled_meta_close({**nb, "meta": {**nb["meta"], "regularMarketTime": o21 + 3600}}, o21 + 23400 + 5 * 3600) is None)
    ok("parse_chart는 그대로 결측으로 센다(캐시 경로 불변)", parse_chart(nb, o21 + 23400 + 5 * 3600) == ([("2026-10-20", 181.19)], ["2026-10-21"]))
    # ★[10/22 리뷰] Yahoo가 currentTradingPeriod를 다음 세션으로 넘긴 뒤(KST 15:30 실측)에도 읽는다 — 다음 세션이 열리기 전까지
    o22 = o21 + 86400
    rolled = {**nb, "meta": {**nb["meta"], "currentTradingPeriod": {"regular": {"start": o22, "end": o22 + 23400}}}}
    ok("넘어간 meta(다음 세션 전) → (10/21, 184.33)", settled_meta_close(rolled, o22 - 7 * 3600) == ("2026-10-21", 184.33))
    ok("다음 세션이 열린 뒤엔 안 읽는다(장중 값)", settled_meta_close(rolled, o22 + 600) is None)
    ok("마지막 봉이 null이 아니면(다음 날 봉이 있다) 안 읽는다",
       settled_meta_close({**rolled, "timestamp": [o21 - 86400, o21, o22],
                           "indicators": {"quote": [{"close": [181.19, None, 186.0]}]}}, o22 - 7 * 3600) is None)
    ok("국내(Asia/Seoul)는 안 읽는다",
       settled_meta_close({**nb, "meta": {**nb["meta"], "exchangeTimezoneName": "Asia/Seoul"}}, o21 + 23400 + 5 * 3600) is None)
    # ★[10/19] Yahoo는 KRX 정규장 끝을 15:00으로 적는다(실제 종가 단일가 15:20~15:30) — 15:00~15:30 장중값이 굳던 자리
    k09, k15 = calendar.timegm((2026, 10, 19, 0, 0, 0)), calendar.timegm((2026, 10, 19, 6, 0, 0))   # 09:00 · 15:00 KST
    kr = {"timestamp": [k09 - 86400 * 3, k09], "indicators": {"quote": [{"close": [5668.05, 5751.0]}]},
          "meta": {"gmtoffset": 32400, "currentTradingPeriod": {"regular": {"start": k09, "end": k15}}}}
    ok("KRX 15:20(Yahoo 정규장 끝 15:00 뒤)에도 그날 봉은 안 쓴다",
       parse_chart(kr, k15 + 20 * 60)[0] == [("2026-10-16", 5668.05)])
    ok("KRX 15:45(유예 끝)엔 그날 종가를 쓴다", parse_chart(kr, k15 + 45 * 60)[0][-1] == ("2026-10-19", 5751.0))
    # 24시간 상품(선물·환율: regular = 현지 00:00~23:59) — 그날 봉은 그날 안 쓴다
    d0 = calendar.timegm((2026, 10, 19, 4, 0, 0))                    # 뉴욕 00:00(-4h)
    fut = {"timestamp": [d0 - 86400 * 3, d0], "indicators": {"quote": [{"close": [101.41, 97.66]}]},
           "meta": {"gmtoffset": -14400, "currentTradingPeriod": {"regular": {"start": d0, "end": d0 + 86340}}}}
    ok("24시간 상품: 그날 봉은 그날 안 쓴다", parse_chart(fut, d0 + 10 * 3600)[0] == [("2026-10-16", 101.41)])

    # ★[10/19] Yahoo 대조 감사 — 개정창 밖에 굳은 장중값(^VIX 7/30 19.38 ↔ 종가 17.09)을 잡는가
    keep_all2 = (HIST_DIR, GAPFILL_LOG)
    with tempfile.TemporaryDirectory() as td:
        try:
            HIST_DIR, GAPFILL_LOG = td, os.path.join(td, "_gapfill.jsonl")
            days = [(dt.date(2026, 7, 1) + dt.timedelta(days=i)).isoformat() for i in range(60)]
            truth = [(d, 15.0 + i * 0.1) for i, d in enumerate(days)]
            stuck = [(d, 19.38 if d == "2026-07-30" else c) for d, c in truth]
            save_cached("^VIX", [r for r in stuck if r[0] != "2026-07-12"])    # 07-12 = 오래된 구멍
            yfetch = lambda s, p1: (list(truth), [])                         # noqa: E731
            now7 = int(calendar.timegm((2026, 9, 1, 0, 0, 0)))
            del NOTES[:]
            a0 = audit_yahoo(90, symbols=["^VIX"], fetch=yfetch, pace=0, now=now7)
            ok("감사: 개정창 밖 장중값 1건 적발(읽기 전용 = 캐시 그대로)",
               [m["date"] for m in a0["mismatch"]] == ["2026-07-30"]
               and dict(load_cached("^VIX"))["2026-07-30"] == 19.38 and not NOTES)
            ok("감사: 개정창보다 오래된 빈 날짜도 잡는다", [m["date"] for m in a0["missing"]] == ["2026-07-12"])
            a1 = audit_yahoo(90, symbols=["^VIX"], fetch=yfetch, pace=0, now=now7, fix=True)
            fixed = dict(load_cached("^VIX"))
            ok("감사 --fix: Yahoo 종가로 교체 + 빈 날짜 채움 + 원장 기록",
               fixed["2026-07-30"] == truth[29][1] and "2026-07-12" in fixed and a1["fixed"] == 1
               and a1["filled"] == 1 and any(n["src"] == SRC_YAHOO_AUDIT for n in NOTES))
            ok("감사 --fix 뒤 다시 보면 불일치 0",
               not audit_yahoo(90, symbols=["^VIX"], fetch=yfetch, pace=0, now=now7)["mismatch"])
            # 연속선물 재기준(GC=F) — 천천히 변하는 배율로 연속 구간 전체가 어긋남 → 개별 수정 금지
            save_cached("GC=F", [(d, c * (0.985 + i * 0.0002)) for i, (d, c) in enumerate(truth)])
            a2 = audit_yahoo(90, symbols=["GC=F"], fetch=yfetch, pace=0, now=now7, fix=True)
            ok("연속 구간 재기준은 '재조정'으로 분류 · 개별 수정 안 함",
               [r["symbol"] for r in a2["rescaled"]] == ["GC=F"] and not a2["mismatch"] and a2["fixed"] == 0)
            # 못 받은 심볼·시간 예산 — '불일치 0'과 구별돼야 한다
            a3 = audit_yahoo(90, symbols=["^VIX", "GC=F"], fetch=lambda s, p1: None, pace=0, now=now7)
            ok("Yahoo를 못 받은 심볼은 errors로 남는다", a3["errors"] == ["^VIX", "GC=F"] and a3["checked"] == 0)
            a4 = audit_yahoo(90, symbols=["^VIX", "GC=F"], fetch=yfetch, pace=0, now=now7, deadline=0)
            ok("시간 예산이 끝나면 못 본 심볼을 skipped로 남긴다", a4["skipped"] == ["^VIX", "GC=F"])
            ok("포맷: 본 게 없으면 '불일치 없음'이라 말하지 않는다", "본 게 없다" in _fmt_audit_yahoo(a3))
            # 아직 끝나지 않은 세션이라 Yahoo가 안 준 날짜(캐시엔 장중에 쓴 값) = pending
            save_cached("^VIX", list(truth) + [("2026-08-30", 22.0)])
            ok("Yahoo 최신 봉보다 뒤의 캐시 날짜 = pending(불일치·extra 아님)",
               audit_yahoo(90, symbols=["^VIX"], fetch=yfetch, pace=0, now=now7)["pending"] == 1)
        finally:
            HIST_DIR, GAPFILL_LOG = keep_all2
            del NOTES[:]

    # ── 라벨러 한 벌(10/20) — 위반을 심어 잡히는지 보고, 실제 스크립트 전체에 돌린다 ──
    U, G, F = "utcfrom" + "timestamp(", "gm" + "time(", "from" + "timestamp("   # 이 파일 스캔에 안 걸리게 쪼갠다
    planted = {
        "a.py": f'res = d["chart"]["result"][0]\nfor t in res["timestamp"]:\n    k = datetime.{U}t).date()\n',
        "b.py": f'ts = res.get("timestamp")\nday = time.strftime("%Y-%m-%d", time.{G}t + shift))\n',
        "c.py": f'ev = r.get("events")["splits"]\nday = datetime.{F}v["date"], tz=timezone.utc)\n',
        "d.py": f'res = d["chart"]["result"][0]\nfor t in res["timestamp"]:\n'
                f'    k = datetime.{U}t)  # label-ok: 테스트 예외\n',
        "e.py": f'now = datetime.{U}time.time())\n',                # Yahoo 봉을 안 읽는 파일
    }
    got = {h[0] for h in labeler_lint(planted)}
    ok("라벨러 검사: 심은 UTC 라벨 3종(utcfromtimestamp·gmtime+shift 복사본·fromtimestamp utc)을 잡는다",
       got == {"a.py", "b.py", "c.py"})
    here = os.path.dirname(os.path.abspath(__file__))
    srcs = {}
    for fn in sorted(os.listdir(here)):
        if fn.endswith(".py"):
            try:
                with open(os.path.join(here, fn), encoding="utf-8") as f:
                    srcs[fn] = f.read()
            except (OSError, UnicodeDecodeError):
                pass
    real = labeler_lint(srcs)
    ok("라벨러 검사: Yahoo 봉을 읽는 스크립트에 bar_date 밖 라벨러가 없다"
       + ("" if not real else " — " + "; ".join(f"{a}:{b}" for a, b, _ in real[:6])), not real)

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
