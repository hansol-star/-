#!/usr/bin/env python3
"""ohlcv_backfill.py — 상장 이래 **OHLCV** 일봉 영구 캐시 (stdlib only·수집 전용)

왜 있나 [2026-08-30 정훈 지시 "주가 흐름도 다 저장"]
──────────────────────────────────────────────────────
기존 `data/history/<sym>.csv`는 헤더가 **`date,close` 두 컬럼뿐**이다. 그래서
  · `signal_score.py`가 스스로 *"종가 기반 — 거래량·고저 필요한 지표는 제외"* 라고 적어둔 채
    RSI/MA/MACD 계열만 채점하고 **거래량 확인·갭·장중 레인지 지표를 통째로 못 쓴다**
    (오닐 CANSLIM의 **S(수급)** 은 거래량 동반이 핵심인데 그 입력이 없다).
  · `vol_gauge.py`는 OHLC가 필요해 **매번 Yahoo를 재조회**한다(캐시가 못 받쳐준다).

⚠️ **기존 `data/history/`는 건드리지 않는다.** 여러 도구가 `(date, close)` 2튜플 형태를
   전제로 읽고 있어 헤더를 바꾸면 조용히 깨진다(8/12 *"쓰는 쪽과 읽는 쪽이 갈리면 데이터는
   조용히 사라진다"*). 그래서 **별도 축** `data/history_ohlcv/`에 쌓고, 소비자가 준비되면
   그쪽이 새 축을 읽게 한다.

수집: Yahoo chart API `interval=1d&period1=0` (range=max는 장기서 월봉으로 다운샘플되므로 금지 —
      history_backfill의 8/x 교훈 그대로).
저장: `data/history_ohlcv/<safe_symbol>.csv`  헤더 `date,open,high,low,close,volume`
⚠️ 최근 5거래일은 값이 바뀔 수 있어 **매번 덮어쓴다**(8/13 장중값 고착 사고 대응 규칙 승계).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "history_ohlcv")
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _safe(sym: str) -> str:
    return sym.replace("^", "_").replace("/", "_")


def universe(md=None) -> list[str]:
    """보유 + 워치 + 거래 이력 + 벤치마크. app/data.js·stocks.json + market_data(portfolio.json·체결 원장).

    ★[2026-11-22 감사 A1] 舊엔 app/data.js 보유 + stocks.json 키만 봤다 — '현재 명단'이라 매도 종목이
      빠지는 순간 캐시가 멎는다(11/20 매도 NAVER·현대차·두산로보 OHLCV가 11/06에서 정지).
      이제 market_data.GROUPS(보유·워치) + RETIRED_WATCH(채점 꼬리) + traded_tickers()(데스크 착수 때 보유 ∪
      그 뒤 체결 — 만료 없음·원장 접미사 그대로)를 합친다. md 인자 = 자가검증 주입용."""
    syms = []
    try:
        raw = open(os.path.join(ROOT, "app", "data.js"), encoding="utf-8").read()
        d = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
        syms += [h["ticker"] for h in (d.get("holdings") or []) if h.get("ticker")]
    except Exception:
        pass
    try:
        st = json.load(open(os.path.join(ROOT, "data", "app", "stocks.json"), encoding="utf-8"))
        syms += list((st.get("watchlist") or {}).keys())
        syms += list((st.get("stocks") or {}).keys())
    except Exception:
        pass
    if md is None:
        try:
            import market_data as md
        except Exception as e:                      # noqa: BLE001
            print(f"[warn] market_data 로드 실패 — 매도 종목·퇴역 워치가 수집에서 빠진다: {e}", file=sys.stderr)
            md = None
    if md is not None:
        g = getattr(md, "GROUPS", {}) or {}
        syms += [s for grp in ("holdings", "watchlist") for _, s in g.get(grp, [])]
        syms += [s for _, s in getattr(md, "RETIRED_WATCH", [])]
        try:
            syms += list(md.traded_tickers())
        except Exception as e:                      # noqa: BLE001
            print(f"[warn] 거래 이력 유니버스 로드 실패 — 매도 종목 캐시가 멈춘다: {e}", file=sys.stderr)
    syms += ["^KS11", "^KQ11", "^GSPC", "^IXIC", "KRW=X"]
    seen, out = set(), []
    for s in syms:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def topup_kr_index(symbol: str, rows, today: str | None = None, daily=None):
    """국내 **지수**(^KS11·^KQ11)의 최근 결측 봉을 네이버 지수 일봉으로 꼬리에 붙인다.

    ★[2026-11-28 R3] 같은 구멍이 두 캐시에 있었다 — `data/history`(종가 캐시)는 `kr_index_gap_fill`로
    막았는데 이 OHLCV 캐시는 **Yahoo만** 본다. 11/28 실측에서 ^KS11·^KQ11이 11/26에 멈춰
    (Yahoo가 11/27 국내 지수 봉을 안 올렸다) `forecast_band`의 지수 밴드 앵커가 하루 낡아 있었다.
    판정(장중 차단·거래일 여부·출처 등급)은 `history_backfill.kr_index_gap_fill` 한 벌을 그대로 쓴다
    (★10/20 교훈 — 식을 옮겨 적으면 다음 정정 때 갈라진다). 네이버 지수 일봉엔 **시가·거래량이 없다**
    → 그 두 칸은 빈칸으로 둔다(소비자 `forecast_band`는 high·low·close만 요구한다).
    """
    import datetime as dt
    import history_backfill as _hb
    if symbol.upper() not in _hb.KR_INDEX or not rows:
        return rows
    today = today or dt.datetime.now(_hb.KST).date().isoformat()
    cand, d, end = [], dt.date.fromisoformat(rows[-1][0]) + dt.timedelta(days=1), dt.date.fromisoformat(today)
    while d <= end and len(cand) < 14:
        if d.weekday() < 5:
            cand.append(d.isoformat())
        d += dt.timedelta(days=1)
    if not cand:
        return rows
    if daily is None:
        code = _hb.KR_INDEX[symbol.upper()]
        start = (dt.date.fromisoformat(cand[0]) - dt.timedelta(days=10)).isoformat()
        daily = _hb._naver_daily(code, start, today) or {}
    got = _hb.kr_index_gap_fill(symbol, cand, daily=daily)
    for d2 in sorted(got):
        close = got[d2][0]
        bar = daily.get(d2) or ()
        hi = round(float(bar[2]), 4) if len(bar) > 2 else close     # 네이버 순서 = (종가, 저가, 고가)
        lo = round(float(bar[1]), 4) if len(bar) > 1 else close
        rows.append([d2, "", hi, lo, close, ""])
    return rows


def selftest() -> int:
    """★[2026-11-22 감사 A1] 오프라인 — 명단에서 빠진 매도 종목이 수집 유니버스에 남는가."""
    import types
    ok = True

    def check(cond, label):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  {'✅' if cond else '❌'} {label}")

    print("ohlcv_backfill 자가검증 — 수집 유니버스")
    fake = types.SimpleNamespace(GROUPS={"holdings": [("삼성전자", "005930.KS")], "watchlist": [("GEV", "GEV")]},
                                 RETIRED_WATCH=[("애플", "AAPL")],
                                 traded_tickers=lambda: ["005930.KS", "035420.KS", "TSLA"])
    u = universe(fake)
    check("035420.KS" in u and "TSLA" in u, "매도 종목(NAVER·TSLA) = 거래 이력으로 수집 대상에 남는다")
    check("AAPL" in u and "GEV" in u and "005930.KS" in u, "보유·워치·퇴역 워치 꼬리도 그대로")
    check(len(u) == len(set(u)), "중복 없음")
    fake.traded_tickers = lambda: (_ for _ in ()).throw(OSError("원장 없음"))
    u2 = universe(fake)
    check("005930.KS" in u2 and "^GSPC" in u2, "원장을 못 읽어도 나머지 유니버스는 그대로")

    # ★[2026-11-28 R3] 국내 지수 꼬리 보정 — Yahoo가 11/27 ^KS11을 안 올려 캐시가 하루 낡아 있었다.
    import inspect
    base = [["2026-11-25", "", 4800.0, 4700.0, 4750.0, ""],
            ["2026-11-26", "", 4760.0, 4690.0, 4711.21, ""]]
    nav = {"2026-11-27": (4915.68, 4870.0, 4930.0)}
    r = topup_kr_index("^KS11", [x[:] for x in base], today="2026-11-27", daily=nav)
    check(len(r) == 3 and r[-1][0] == "2026-11-27" and r[-1][4] == 4915.68,
          "결측 지수 봉을 네이버 일봉으로 꼬리에 붙인다")
    check(r[-1][2] == 4930.0 and r[-1][3] == 4870.0 and r[-1][1] == "" and r[-1][5] == "",
          "고가·저가는 채우고 시가·거래량은 빈칸(네이버 지수 일봉에 없다)")
    r2 = topup_kr_index("^KS11", [x[:] for x in base], today="2026-11-27", daily={})
    check(len(r2) == 2, "네이버가 비면 아무것도 안 붙인다(없는 봉을 만들지 않는다)")
    r3 = topup_kr_index("005930.KS", [x[:] for x in base], today="2026-11-27", daily=nav)
    check(len(r3) == 2, "종목 심볼엔 적용하지 않는다(종목은 kr_gap_fill 축)")
    r4 = topup_kr_index("^GSPC", [x[:] for x in base], today="2026-11-27", daily=nav)
    check(len(r4) == 2, "미국 지수엔 적용하지 않는다")
    check("topup_kr_index(s, fetch(s))" in inspect.getsource(main),
          "배선 — main 수집 루프가 보정을 실제로 부른다")

    print("✅ 통과" if ok else "❌ 실패")
    return 0 if ok else 1


def fetch(symbol: str, timeout: float = 40.0):
    now = int(time.time())
    url = YAHOO.format(symbol=urllib.parse.quote(symbol)) + \
        f"?interval=1d&period1=0&period2={now}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        q = res["indicators"]["quote"][0]
        # [10/13] 날짜 = 거래소 현지일(UTC로 붙이면 KRW=X 서머타임 봉이 하루 앞 날짜가 된다)
        # ★[10/20] 식을 옮겨 적지 않고 history_backfill.bar_date를 부른다 — 복사본은 다음 정정 때 갈라진다(vol_gauge 사고)
        import history_backfill as _hb
        off = (res.get("meta") or {}).get("gmtoffset") or 0
        rows = []
        for i, t in enumerate(ts):
            c = q["close"][i]
            if c is None:
                continue
            def g(k):
                v = q.get(k, [None] * len(ts))[i]
                return "" if v is None else round(float(v), 4)
            rows.append([_hb.bar_date(t, off),
                         g("open"), g("high"), g("low"), round(float(c), 4),
                         int(q["volume"][i]) if q.get("volume", [None])[i] is not None else ""])
        return rows
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError,
            IndexError, TypeError, ValueError):
        return None


def save(symbol: str, rows) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, _safe(symbol) + ".csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")  # [9/10] csv 기본 \r\n 금지 — .gitattributes eol=lf와 맞춘다
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        w.writerows(rows)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="상장 이래 OHLCV 일봉 캐시 (수집 전용)")
    ap.add_argument("--symbols", help="쉼표구분 (기본=보유+워치+퇴역 워치+거래 이력+벤치마크)")
    ap.add_argument("--pace", type=float, default=1.5, help="심볼 간 페이싱 초")
    ap.add_argument("--stats", action="store_true", help="캐시 현황만 출력")
    ap.add_argument("--list", action="store_true", help="수집 대상 심볼만 출력(수집·쓰기 없음)")
    ap.add_argument("--selftest", action="store_true", help="오프라인 자가검증 — 수집 유니버스(매도 종목 포함)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    syms = [s.strip() for s in a.symbols.split(",")] if a.symbols else universe()
    if a.list:
        print(f"수집 대상 {len(syms)}종목: " + ", ".join(syms))
        return 0

    if a.stats:
        print(f"OHLCV 캐시 — {OUT_DIR}")
        tot = 0
        for s in syms:
            p = os.path.join(OUT_DIR, _safe(s) + ".csv")
            if not os.path.exists(p):
                print(f"  {s:<14} 없음")
                continue
            rows = list(csv.reader(open(p)))[1:]
            tot += len(rows)
            print(f"  {s:<14} {rows[0][0]} ~ {rows[-1][0]}  {len(rows):>6}행")
        print(f"총 {tot:,}행")
        return 0

    print(f"■ OHLCV 수집 {len(syms)}종목 → {OUT_DIR}")
    ok = fail = 0
    for i, s in enumerate(syms, 1):
        rows = topup_kr_index(s, fetch(s))
        if not rows:
            print(f"  [{i}/{len(syms)}] {s:<14} ❌ 실패")
            fail += 1
        else:
            save(s, rows)
            print(f"  [{i}/{len(syms)}] {s:<14} {rows[0][0]} ~ {rows[-1][0]}  {len(rows):>6}행")
            ok += 1
        sys.stdout.flush()
        if i < len(syms):
            time.sleep(a.pace + random.uniform(0, 0.8))
    print(f"\n완료 — 성공 {ok} · 실패 {fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
