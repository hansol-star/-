#!/usr/bin/env python3
"""
market_data.py — 무키(無key) 시세·환율 수집기 (Yahoo Finance)

토스 Open API 키 없이도 국내·미국 주식 시세, 주요 지수, 환율을 가져온다.
표준 라이브러리(urllib)만 사용 — pip 설치 불필요, 로컬 이전 시에도 그대로 작동.

용도:
  - 보유 + 워치리스트 현재가/등락률 (명단 정본 = portfolio.json)
  - 코스피·코스닥·S&P500·나스닥·다우·필반(SOX) 지수
  - USD/KRW 환율
  - (선택) 원가 대비 평가손익 — master.md 기준값을 넘기면 계산

  ※ 이 스크립트는 "시세·환율" 전용이다. 사용자의 실제 보유수량·현금 잔액은
    토스 실데이터(toss_snapshot.py) 또는 계좌 스크린샷이 source of truth.
    원가 고정 테이블의 정본은 docs/master.md.

사용법:
  python3 market_data.py                      # 기본 유니버스 전체 (표 출력)
  python3 market_data.py --json               # JSON 출력 (서브에이전트/파이프라인용)
  python3 market_data.py --tickers AAPL,NVDA  # 특정 티커만
  python3 market_data.py --group holdings      # holdings|watchlist|index|fx|all
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import cli_common

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# ── 유니버스 정의 (정훈 포트폴리오 기준; 원가의 정본은 docs/master.md) ──────────
# label: 화면 표기명, symbol: Yahoo 티커
# ★[2026-11-22 감사 A7] 아래 세 목록은 **portfolio.json을 못 읽을 때만** 쓰는 폴백이다(정본 = portfolio.json).
#   舊 폴백엔 9/23 매도 AAPL·META, 11/13 매도 MSFT, 11/20 매도 두산로보·현대차·NAVER가 '보유'로 남아 있었다 —
#   폴백이 쓰이는 날 판 종목을 보유로 읽는다. 11/22 portfolio.json holdings·watchlist와 맞췄다.
HOLDINGS_KR = [
    ("삼성전자", "005930.KS"),
    ("LG전자", "066570.KS"),
]
HOLDINGS_US = [
    ("NVDA", "NVDA"), ("VOO", "VOO"), ("GOOGL", "GOOGL"), ("ORCL", "ORCL"),
    ("MU", "MU"), ("AVGO", "AVGO"), ("SpaceX", "SPCX"),
]  # [9/17] 폴백 정합 — TSLA(7/7)·ANET(8/11) 매도분 제거 · ★[11/22] AAPL·META·MSFT 제거·SPCX 추가
WATCHLIST = [  # 폴백 (portfolio.json 없을 때만). 정본은 portfolio.json.
    ("GEV", "GEV"), ("삼성전기", "009150.KS"), ("SK하이닉스", "000660.KS"), ("KT&G", "033780.KS"),
    ("AMD", "AMD"), ("TSM", "TSM"), ("CDNS", "CDNS"), ("ANET", "ANET"), ("MSFT", "MSFT"),
    ("LRCX", "LRCX"), ("VRT", "VRT"), ("LLY", "LLY"), ("BRK-B", "BRK-B"), ("셀트리온", "068270.KS"),
]  # [11/18 d276] 두산E·SK이노·AMAT·ISRG 제외 / LRCX·MSFT·VRT·LLY·BRK-B 편입  # [9/17 d193] 원익IPS·테스·SPCX 제외, TSM·AMAT 편입 · [9/29 d218] 삼성바이오·PLTR 제외, CDNS·ISRG 편입
INDEX = [
    ("코스피", "^KS11"), ("코스닥", "^KQ11"), ("S&P500", "^GSPC"),
    ("나스닥", "^IXIC"), ("다우", "^DJI"), ("필라델피아반도체", "^SOX"),
]
FX = [("USD/KRW", "KRW=X")]


def _load_universe():
    """portfolio.json이 있으면 거기서 유니버스를 읽어 덮어쓴다 (master.md 미러, 단일 정본).
    없으면 위 임베드 기본값 사용 — 포터블."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "portfolio.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        pairs = lambda items: [(d["label"], d["ticker"]) for d in items]
        return (pairs(cfg["holdings"]["kr"]), pairs(cfg["holdings"]["us"]),
                pairs(cfg["watchlist"]), pairs(cfg["indices"]), pairs(cfg["fx"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None


_u = _load_universe()
if _u:
    HOLDINGS_KR, HOLDINGS_US, WATCHLIST, INDEX, FX = _u

GROUPS = {
    "holdings": HOLDINGS_KR + HOLDINGS_US,
    "watchlist": WATCHLIST,
    "index": INDEX,
    "fx": FX,
    # [7/13 급락 TF] 유가 = 해제 조건3(유가/이란 진정) 감시 지표 — docs/crash_tf.md
    "oil": [("WTI", "CL=F"), ("브렌트", "BZ=F")],
}
GROUPS["all"] = GROUPS["holdings"] + GROUPS["watchlist"] + GROUPS["index"] + GROUPS["fx"] + GROUPS["oil"]


def _load_retired_watch(today=None):
    """[9/17 d193] 워치에서 뺐지만 **채점 꼬리(track_until)**가 남은 종목.
    GROUPS에는 넣지 않는다 — 시세표·데스크엔 안 나오고 history_backfill(일봉 캐시)만 소비한다.
    제외와 동시에 캐시 갱신이 끊기면 제외 직전 워치 콜의 +20거래일 채점이 조용히 불가가 된다."""
    import datetime as _dt
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "portfolio.json")
    today = (today or _dt.date.today()).isoformat()
    try:
        with open(path, encoding="utf-8") as f:
            items = json.load(f).get("watch_retired") or []
    except (OSError, ValueError):
        return []
    return [(d["label"], d["ticker"]) for d in items
            if d.get("ticker") and str(d.get("track_until") or "") >= today]


RETIRED_WATCH = _load_retired_watch()


# ─────────────────────────────────────────────────────────────────────────────
# ★[2026-11-22 감사 A7] **데스크 배정 정본 = portfolio.json 각 holdings·watchlist 항목의 `desk` 필드.**
#   舊엔 desk_gate.SECTOR · peer_compare.GROUPS · build_app_data.SECTOR_MAP · financials.PEERS
#   네 곳에 손으로 복사한 목록이 있었고, 서로 다르고 낡았다 — peer_compare가 이미 판 7종목을
#   '●보유'로 찍고, SPCX는 어느 데스크에도 없어 앱에서 '기타'로 빠졌다(desk_gate의
#   "바뀌면 같이 고칠 것" 주석이 그 실패의 증거다). ⇒ 이제 네 곳 모두 여기서 파생한다.
#   값 = 'semi-ai' | 'power-physical' | 'bigtech-platform' | null(ETF — 데스크 담당 없음).
#   watch_retired 항목엔 desk가 없어도 된다(데스크 담당이 끝난 종목).
# ★[2026-11-22 감사 A1] 수집 유니버스에 **거래 이력 유니버스**(traded_tickers)를 더한다 —
#   '현재 명단'으로만 수집하면 매도 종목 캐시가 매도 다음 날 얼어붙고(10/3 교훈의 재발:
#   11/20 매도 NAVER·현대차·두산로보 캐시가 11/19에서 정지), 룰7 '가만히' 다리와 매도 기여가
#   동결가로 계산된다.
# ─────────────────────────────────────────────────────────────────────────────
DESKS = ("semi-ai", "power-physical", "bigtech-platform")
_HERE = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_JSON = os.path.join(_HERE, "..", "portfolio.json")
LEDGER_JSONL = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "data", "app", "trades.jsonl"))
DESK_START = "2026-06-13"   # = trades.DESK_START (순환 import를 피하려고 값만 둔다 — 아래 _desk_start가 정본을 먼저 본다)


def _desk_start() -> str:
    try:
        import trades as _T
        return _T.DESK_START
    except Exception:            # noqa: BLE001 — trades 모듈을 못 읽어도 값은 같다
        return DESK_START


def _portfolio(path: str | None = None) -> dict | None:
    try:
        with open(path or PORTFOLIO_JSON, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def _entries(pf: dict | None, sections=("holdings", "watchlist")) -> list[tuple[str, dict]]:
    """(소속, 항목) 목록 — 소속 = 'holdings' | 'watchlist' | 'watch_retired'. 보유가 앞."""
    out = []
    if not pf:
        return out
    for sec in sections:
        v = pf.get(sec)
        if isinstance(v, dict):                       # holdings = {kr: [...], us: [...]}
            items = [x for k in ("kr", "us") for x in (v.get(k) or [])]
        elif isinstance(v, list):
            items = v
        else:
            items = []
        out += [(sec, x) for x in items if isinstance(x, dict) and x.get("ticker")]
    return out


def desk_map(path: str | None = None) -> dict[str, str | None]:
    """{티커: 데스크 키 또는 None} — **`desk` 필드가 명시된** 보유·워치 항목만.
    필드가 없는 항목은 빠진다(= '모름'). 명시된 null(ETF)은 None으로 들어간다."""
    out: dict[str, str | None] = {}
    for _, e in _entries(_portfolio(path)):
        if "desk" not in e:
            continue
        d = e.get("desk")
        out.setdefault(e["ticker"], d if d in DESKS else None)
    return out


def desk_of(ticker: str, path: str | None = None) -> str | None:
    """종목의 담당 섹터 데스크('semi-ai'·'power-physical'·'bigtech-platform'). ETF·미배정·명단 밖 = None."""
    return desk_map(path).get(ticker)


def desk_members(desk: str, path: str | None = None, section: str | None = None) -> list[str]:
    """그 데스크가 맡은 티커(보유 먼저, 그다음 워치 · portfolio.json 순서).
    section = 'holdings' | 'watchlist'로 한쪽만 고를 수 있다."""
    out = []
    for sec, e in _entries(_portfolio(path)):
        if section and sec != section:
            continue
        if e.get("desk") == desk and e["ticker"] not in out:
            out.append(e["ticker"])
    return out


def held_tickers(path: str | None = None) -> list[str]:
    """현재 보유 티커(portfolio.json holdings — kr 먼저)."""
    return [e["ticker"] for _, e in _entries(_portfolio(path), ("holdings",))]


def labels(path: str | None = None) -> dict[str, str]:
    """티커 → 표시명(보유·워치·퇴역 워치)."""
    out: dict[str, str] = {}
    for _, e in _entries(_portfolio(path), ("holdings", "watchlist", "watch_retired")):
        out.setdefault(e["ticker"], e.get("label") or e["ticker"])
    return out


def _ledger_rows(ledger: str | None = None) -> list[dict]:
    rows = []
    try:
        with open(ledger or LEDGER_JSONL, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("//"):
                    continue
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("ticker"):
                    rows.append(r)
    except OSError:
        return []
    rows.sort(key=lambda r: (str(r.get("date") or ""), 0 if r.get("side") == "opening" else 1))
    return rows


def traded_tickers(since: str | None = None, ledger: str | None = None) -> list[str]:
    """★[2026-11-22 감사 A1] **측정 시작에 들고 있던 티커 ∪ 그 뒤 체결된 티커** (원장 접미사 그대로).

    since 기본 = 데스크 착수일(trades.DESK_START). performance의 q0(시작일 보유)와 기간 내 체결을
    모두 덮는다 — '가만히' 다리와 매도 기여가 읽는 캐시가 바로 이 집합이다.
    데스크 이전에 이미 정리된 옛 티커(122870.KQ·035720.KS 등)는 넣지 않는다(검증자 지적: 쓸데없는 수집).
    만료가 없다 — 매도한 종목도 계속 수집해야 사후 기여가 동결가로 계산되지 않는다.
    """
    since = since or _desk_start()
    held: dict[str, float] = {}
    traded: list[str] = []
    for r in _ledger_rows(ledger):
        side = r.get("side")
        if side not in ("opening", "buy", "sell"):
            continue
        tk = r["ticker"]
        if str(r.get("date") or "") < since:
            try:
                sh = float(r.get("shares") or 0)
            except (TypeError, ValueError):
                sh = 0.0
            held[tk] = held.get(tk, 0.0) + (-sh if side == "sell" else sh)
        elif tk not in traded:
            traded.append(tk)
    out = [t for t, q in held.items() if abs(q) > 1e-6]
    out += [t for t in traded if t not in out]
    return out


def kr_suffix_map(path: str | None = None, ledger: str | None = None) -> dict[str, str]:
    """★[2026-11-22 감사 A11] 국내 6자리 코드 → 접미사(.KS/.KQ). 정본(portfolio.json 보유·워치·퇴역 워치
    + 체결 원장)에서만 만든다 — '접미사는 정본에서만'(7/30 원칙). 같은 코드가 .KS·.KQ로 동시에
    나오면 ValueError(어느 쪽이 맞는지 기계가 고르지 않는다)."""
    seen: dict[str, set[str]] = {}
    tks = [e["ticker"] for _, e in _entries(_portfolio(path), ("holdings", "watchlist", "watch_retired"))]
    tks += [r["ticker"] for r in _ledger_rows(ledger)]
    for t in tks:
        t = str(t).upper()
        if t.endswith((".KS", ".KQ")):
            code, suf = t[:-3], t[-3:]
            if code.isdigit() and len(code) == 6:
                seen.setdefault(code, set()).add(suf)
    bad = {c: sorted(s) for c, s in seen.items() if len(s) > 1}
    if bad:
        raise ValueError(f"같은 종목코드가 접미사 둘로 나온다 — {bad} (portfolio.json·trades.jsonl 정정 필요)")
    return {c: next(iter(s)) for c, s in seen.items()}


def _selftest() -> int:
    """★[2026-11-22 감사 A1·A7·A11] 오프라인 자가검증 — 임시 portfolio·원장으로 심는다."""
    import tempfile
    ok = True

    def check(cond, label, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  {'✅' if cond else '❌'} {label}" + (f" — {detail}" if detail and not cond else ""))

    print("market_data 자가검증 — 데스크 정본(desk 필드) · 거래 이력 유니버스 · 국내 접미사 맵")
    pf = {"holdings": {"kr": [{"label": "삼성전자", "ticker": "005930.KS", "desk": "semi-ai"}],
                       "us": [{"label": "VOO", "ticker": "VOO", "desk": None},
                              {"label": "SpaceX", "ticker": "SPCX", "desk": "bigtech-platform"}]},
          "watchlist": [{"label": "GEV", "ticker": "GEV", "desk": "power-physical"},
                        {"label": "KT&G", "ticker": "033780.KS", "desk": "power-physical"},
                        {"label": "무필드", "ticker": "ZZZ"}],
          "watch_retired": [{"label": "현대차", "ticker": "005380.KS"}]}
    led = [{"date": "2026-01-02", "ticker": "122870.KQ", "side": "buy", "shares": 1},
           {"date": "2026-02-02", "ticker": "122870.KQ", "side": "sell", "shares": 1},   # 데스크 전 정리 = 제외
           {"date": "2026-03-02", "ticker": "005380.KS", "side": "buy", "shares": 1},    # 시작 보유 → 11/20 매도
           {"date": "2026-11-20", "ticker": "005380.KS", "side": "sell", "shares": 1},
           {"date": "2026-11-18", "ticker": "TSLA", "side": "buy", "shares": 0.1},       # 기간 내 매수·매도
           {"date": "2026-11-20", "ticker": "TSLA", "side": "sell", "shares": 0.1},
           {"date": "2026-11-20", "ticker": "X", "side": "closed"}]
    with tempfile.TemporaryDirectory() as td:
        pp, lp = os.path.join(td, "p.json"), os.path.join(td, "t.jsonl")
        with open(pp, "w", encoding="utf-8") as f:
            json.dump(pf, f, ensure_ascii=False)
        with open(lp, "w", encoding="utf-8") as f:
            f.write("// 주석\n" + "\n".join(json.dumps(r) for r in led) + "\n")
        check(desk_of("SPCX", pp) == "bigtech-platform", "SPCX = 빅테크·플랫폼 데스크(우주는 그 데스크 헌장)")
        check(desk_of("VOO", pp) is None and "VOO" in desk_map(pp), "ETF = desk null(명시) — desk_map엔 None으로 있다")
        check("ZZZ" not in desk_map(pp), "desk 필드가 없는 항목은 '모름'(맵에서 빠진다)")
        check(desk_members("power-physical", pp) == ["GEV", "033780.KS"], "데스크 담당 = 보유 먼저·워치 순서",
              str(desk_members("power-physical", pp)))
        check(desk_members("semi-ai", pp, "watchlist") == [], "section 필터(워치만)")
        tt = traded_tickers("2026-06-13", lp)
        check("005380.KS" in tt and "TSLA" in tt, "시작 보유(현대차)·기간 내 체결(TSLA)은 매도 뒤에도 남는다", str(tt))
        check("122870.KQ" not in tt, "데스크 전에 정리한 옛 티커는 넣지 않는다", str(tt))
        check(held_tickers(pp) == ["005930.KS", "VOO", "SPCX"], "held_tickers = holdings kr→us")
        m = kr_suffix_map(pp, lp)
        check(m.get("033780") == ".KS" and m.get("122870") == ".KQ" and m.get("005380") == ".KS",
              "국내 접미사 = 워치·퇴역·원장에서 파생", str(m))
        with open(lp, "a", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-11-21", "ticker": "033780.KQ", "side": "buy", "shares": 1}) + "\n")
        try:
            kr_suffix_map(pp, lp)
            check(False, "같은 코드가 .KS·.KQ로 갈리면 중단")
        except ValueError:
            check(True, "같은 코드가 .KS·.KQ로 갈리면 중단(ValueError)")
    check(desk_map(os.path.join(os.sep, "nonexistent", "p.json")) == {}, "portfolio.json을 못 읽으면 빈 맵(호출부가 폴백)")
    print("✅ 통과" if ok else "❌ 실패")
    return 0 if ok else 1


def _prev_close(data: dict, meta: dict, price):
    """직전 **거래일** 종가를 일봉 시계열에서 직접 집는다.

    ★[2026-07-31 신설] `meta.chartPreviousClose`를 그대로 쓰면 안 되는 이유:
      코스닥에서 이 값이 **전전거래일**을 가리키는 케이스가 반복됐다
      (7/8·7/23·7/24·7/28·7/30·7/31 — **6회**). 7/31엔 등락률이 +8.61%로 나왔지만
      실제는 **+11.63%**(전일 644.78 기준)였다. 매번 사람이 뉴스로 대조해 수기 정정했다 =
      **코드에 가드가 없었다**는 뜻이라 재발이 보장돼 있었다.

    방법: 5일 일봉에서 **오늘 봉을 뺀 마지막 종가**를 쓴다. 오늘 봉은
      ①현재가와 사실상 같거나(장중·마감) ②마지막 원소라는 두 단서로 식별한다.
    실패하면 meta 값으로 폴백하되 출처를 `meta(폴백)`으로 표기해 추적 가능하게 둔다.
    """
    fallback = meta.get("chartPreviousClose") or meta.get("previousClose")
    try:
        res = data["chart"]["result"][0]
        raw = res["indicators"]["quote"][0]["close"]
        closes = [c for c in raw if c]
    except (KeyError, IndexError, TypeError):
        return fallback, "meta(폴백)"
    if len(closes) < 2:
        return fallback, "meta(폴백)"
    # ★[2026-10-15] **오늘 봉이 None으로 비어 있으면** 마지막 유효 종가가 곧 직전 종가다.
    #   10/14 .KS 전 종목·^KS11의 10/14 봉이 None으로 왔고, 삼성전자 10/14 종가가 10/13과
    #   같은 232,000원이라 아래 '현재가 == 마지막 봉' 판정이 10/13 봉을 오늘 봉으로 오인 →
    #   10/12 대비 **-7.39%**(실제 0.00%)가 찍혀 desk_gate가 반도체 데스크를 헛스폰시켰다.
    #   판정 = 비어 있는 마지막 봉의 날짜 == regularMarketTime의 거래소 현지 날짜.
    try:
        ts = res.get("timestamp") or []
        rmt = meta.get("regularMarketTime")
        off = meta.get("gmtoffset") or 0
        if raw and raw[-1] is None and ts and rmt and len(ts) == len(raw):
            day = lambda t: (t + off) // 86400
            if day(ts[-1]) == day(rmt):
                return closes[-1], "series(오늘봉 결측)"
    except (TypeError, ValueError):
        pass
    # 마지막 봉이 오늘치면 그 앞을, 아니면 마지막을 직전 종가로 본다.
    last = closes[-1]
    if price is not None and abs(last - price) < max(abs(price) * 1e-6, 1e-9):
        # ★[2026-10-13] 오늘 봉 바로 앞 봉이 결측(None)이면 closes[-2]는 **전전거래일**이다.
        #   10/13에 Yahoo가 .KS 개별종목의 10/12 봉을 통째로 비워 보냈고(지수 ^KS11은 정상),
        #   위의 `if c` 필터가 그 봉을 조용히 버려 등락률이 **이틀치 합산**으로 찍혔다
        #   (삼성 -7.39% → -11.07%, LG전자 -3.6% → -12.9%). 지수만 1일치라
        #   "종목이 지수의 2배 빠진다"는 거짓 인상이 장중 대응 답변에 그대로 들어갔다.
        #   ⇒ 결측을 출처 라벨에 남긴다 — 호출부가 다른 소스로 메우거나 경고를 띄운다.
        idx = max(i for i, c in enumerate(raw) if c)
        if idx >= 1 and not raw[idx - 1]:
            return closes[-2], PREV_GAP
        return closes[-2], "series"
    return last, "series"


PREV_GAP = "series(직전봉 결측)"


def _naver_prev_close(symbol: str, timeout: float = 6.0):
    """국내 종목(.KS/.KQ)의 직전 거래일 종가를 네이버 실시간 API에서 받는다. 실패 시 None.

    Yahoo 일봉에 구멍이 났을 때만 쓰는 보정 경로다(평소엔 호출하지 않는다).
    """
    code = symbol.split(".")[0]
    url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{code}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            d = json.load(resp)["datas"][0]
        close = float(str(d["closePrice"]).replace(",", ""))
        diff = float(str(d["compareToPreviousClosePrice"]).replace(",", ""))
        return close - diff
    except Exception:
        return None


def fetch_quote(symbol: str, timeout: float = 10.0) -> dict | None:
    """Yahoo chart 엔드포인트에서 단일 심볼 시세를 가져온다. 실패 시 None."""
    url = YAHOO_CHART.format(symbol=urllib.request.quote(symbol))
    # ★[2026-07-31] range=1d → 5d. `chartPreviousClose`가 **전전거래일**을 가리키는
    #   케이스가 있어(코스닥에서 7/8·7/23·7/24·7/28·7/30·7/31 **6회 재발**) 등락률이
    #   틀렸다. 7/31엔 +8.61%로 나왔지만 실제는 **+11.63%**였다.
    #   ⇒ 메타값을 믿지 않고 **일봉 시계열에서 직전 거래일 종가를 직접 집는다**(_prev_close).
    url += "?interval=1d&range=5d"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
        return {"symbol": symbol, "error": str(e)}
    try:
        meta = data["chart"]["result"][0]["meta"]
    except (KeyError, IndexError, TypeError):
        return {"symbol": symbol, "error": "no data (delisted/invalid ticker?)"}
    price = meta.get("regularMarketPrice")
    prev, prev_src = _prev_close(data, meta, price)
    if prev_src == PREV_GAP and symbol.upper().endswith((".KS", ".KQ")):
        nv = _naver_prev_close(symbol)
        if nv:
            prev, prev_src = nv, "naver(결측 보정)"
    chg_pct = None
    if price is not None and prev:
        chg_pct = round((price - prev) / prev * 100, 2)
    return {
        "symbol": symbol,
        "price": price,
        "prev_close": prev,
        "prev_src": prev_src,
        "change_pct": chg_pct,
        "currency": meta.get("currency"),
        "market_state": meta.get("marketState"),
    }


def collect(universe: list[tuple[str, str]]) -> list[dict]:
    out = []
    for label, symbol in universe:
        q = fetch_quote(symbol)
        q["label"] = label
        out.append(q)
    return out


def fmt_price(p, cur) -> str:
    if p is None:
        return "—"
    if cur == "KRW":
        return f"{p:,.0f}"
    return f"{p:,.2f}"


def fmt_pct(p) -> str:
    if p is None:
        return "—"
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.2f}%"


def print_table(rows: list[dict]) -> None:
    print(f"| {'종목':<14} | {'현재가':>12} | {'등락률':>8} | {'통화':<4} | 상태 |")
    print(f"|{'-'*16}|{'-'*14}|{'-'*10}|{'-'*6}|------|")
    for r in rows:
        if r.get("error"):
            print(f"| {r['label']:<14} | {'ERROR':>12} | {'—':>8} | {'—':<4} | {r['error'][:20]} |")
            continue
        print(
            f"| {r['label']:<14} | {fmt_price(r['price'], r['currency']):>12} "
            f"| {fmt_pct(r['change_pct']):>8} | {str(r['currency'] or '—'):<4} "
            f"| {r.get('market_state','—')} |"
            + (" ⚠️직전봉 결측 — 등락률이 2거래일 누적일 수 있음" if r.get("prev_src") == PREV_GAP else "")
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="무키 시세·환율 수집기 (Yahoo Finance)")
    ap.add_argument("--group", default="all", choices=list(GROUPS.keys()),
                    help="조회 그룹 (기본 all)")
    ap.add_argument("--tickers", help="쉼표·공백구분 티커 직접 지정 (group 무시)")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    ap.add_argument("--selftest", action="store_true",
                    help="오프라인 자가검증 — desk 정본·거래 이력 유니버스·국내 접미사 맵(네트워크 없음)")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()

    if args.tickers:
        universe = [(t, t) for t in cli_common.split_tickers(args.tickers) if t.strip()]
    else:
        universe = GROUPS[args.group]

    rows = collect(universe)

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    # 그룹별 섹션 출력 (group=all일 때만 구분)
    if not args.tickers and args.group == "all":
        sections = [
            ("📈 보유 — 국내", HOLDINGS_KR),
            ("📈 보유 — 미국", HOLDINGS_US),
            ("👀 워치리스트", WATCHLIST),
            ("📊 지수", INDEX),
            ("💱 환율", FX),
        ]
        by_symbol = {r["symbol"]: r for r in rows}
        for title, uni in sections:
            print(f"\n### {title}")
            print_table([by_symbol[s] for _, s in uni])
    else:
        print_table(rows)

    errs = [r for r in rows if r.get("error")]
    if errs:
        print(f"\n⚠️  {len(errs)}개 실패: {', '.join(r['label'] for r in errs)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
