#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""live_quotes.py — 앱 실시간 시세 스냅샷(app/live.json) [2026-09-21 신설 · 정훈 지시]

■ 왜 만들었나
앱(app/data.js)의 시세는 **빌드 시점에 굳는다** — 보고서·refresh-prices(하루 2회) 때만 바뀐다.
그래서 장중에 폰으로 앱을 열면 몇 시간 전 가격으로 총자산·손익·사다리·밴드를 보고 있었다.
9/21 실측: 현대차가 애프터마켓에서 361,000원에 거래되는 동안 앱은 18:27 빌드값에 멈춰 있었다.
정훈 지시 *"앱에 실시간 데이터가 보이게 해도 되고 · 로컬과 클라우드 다 사용 가능하잖아"*.

■ 왜 브라우저가 직접 안 부르나 (9/21 실측)
GitHub Pages 오리진에서 fetch 시험: Yahoo·네이버 전부 **CORS 차단**(open.er-api·업비트만 통과).
⇒ 서버 쪽에서 받아 **같은 오리진의 정적 파일**(app/live.json)로 내려준다.

■ 누가 돌리나
  · 클라우드 = `.github/workflows/deploy-app.yml` 스케줄(장중 5~10분) — PC가 꺼져 있어도 돈다.
  · 로컬    = `price_watch.py`(작업 스케줄러 10분)가 끝에 `--kick`을 부른다 — 배포된 live.json이
              오래됐을 때만(클라우드 cron 지연) 배포 워크플로를 한 번 찌른다. 로컬이 직접 파일을
              올리지 않는다(커밋 히스토리를 5분마다 더럽히지 않기 위해).

■ 소스 (전부 무키 · 조회 전용)
  · 국내 주식·지수 = 네이버 polling(실시간·delayTime 0) — **프리/애프터마켓 가격 포함**
  · 국내 정규장 종가 = Yahoo(regularMarketPrice) — **다음 거래일 가격제한폭의 기준가**라 애프터 가격과 분리
  · 미국 주식·지수·환율·WTI = Yahoo chart(includePrePost) — 프리/애프터 가격 분리 보관

■ 규율
  · **룰을 판정하지 않는다.** 가격만 나른다. 사다리·밴드·게이트 계산은 앱이 data.js의 정본 값
    (peak·steps·base·spent)에 이 가격을 대입해 "장중 추정"으로만 표시한다 — 확정은 종가·보고서.
  · 실패를 숨기지 않는다: 소스별 오류를 `errors`에 남기고, 앱은 나이(age)로 지연을 표시한다.

■ 사용
  live_quotes.py                      # app/live.json 생성(유니버스 = app/data.js)
  live_quotes.py --out PATH --src cloud
  live_quotes.py --print              # 표로 확인
  live_quotes.py --kick [--max-age 8] # 로컬 백업: 배포본이 오래됐으면 배포 워크플로 1회 실행
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
APP_DATA = os.path.join(ROOT, "app", "data.js")
OUT = os.path.join(ROOT, "app", "live.json")
LOG_DIR = os.path.join(ROOT, "data", "logs")
KICK_STATE = os.path.join(LOG_DIR, "live_kick_state.json")
PAGES_LIVE = "https://hansol-star.github.io/-/live.json"
REPO = "hansol-star/-"
WORKFLOW = "deploy-app.yml"

KST = dt.timezone(dt.timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
NAVER_STOCK = "https://polling.finance.naver.com/api/realtime/domestic/stock/{codes}"
NAVER_INDEX = "https://polling.finance.naver.com/api/realtime/domestic/index/{codes}"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=2d&interval=5m&includePrePost=true"
YAHOO_SPARK = "https://query1.finance.yahoo.com/v7/finance/spark?symbols={syms}&range=1d&interval=1d"

NAVER_INDEX_CODE = {"^KS11": "KOSPI", "^KQ11": "KOSDAQ"}
# 앱이 늘 보여주는 시장 스트립(유니버스에 없어도 받는다). CL=F = TF 게이트③ 프록시.
EXTRA = ["^KS11", "^KQ11", "^GSPC", "^IXIC", "^DJI", "^SOX", "KRW=X", "CL=F"]
# 장중 추이선을 싣는 대상(보유 + 지수 + 환율·유가) — 워치까지 넣으면 파일이 커진다
SERIES_ALWAYS = {"^KS11", "^KQ11", "^GSPC", "^IXIC", "^SOX", "KRW=X", "CL=F"}


def _get(url: str, timeout: float = 8.0, tries: int = 2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001 — 소스별로 errors에 남긴다
            last = e
            time.sleep(0.6 * (i + 1))
    raise last  # type: ignore[misc]


def _num(s):
    if s is None:
        return None
    try:
        return float(str(s).replace(",", ""))
    except ValueError:
        return None


def _epoch(iso: str | None):
    if not iso:
        return None
    try:
        return int(dt.datetime.fromisoformat(iso).timestamp())
    except ValueError:
        return None


def is_kr(sym: str) -> bool:
    return sym.endswith(".KS") or sym.endswith(".KQ")


# ── 유니버스 = 앱이 실제로 그리는 종목(app/data.js) ─────────────────────────
def load_universe(path: str = APP_DATA):
    with open(path, encoding="utf-8") as f:
        txt = f.read()
    i = txt.index("window.APP_DATA = ") + len("window.APP_DATA = ")
    data = json.loads(txt[i:].rstrip().rstrip(";"))
    hold = [h["ticker"] for h in data.get("holdings", [])]
    watch = [w["ticker"] for w in data.get("watchlist", [])]
    idx = [x["ticker"] for x in data.get("indices", [])]
    alert_tk = [a.get("ticker") for a in data.get("alerts", [])
                if a.get("ticker") and a.get("ticker") not in ("EVENT", "FLOW")
                and a.get("cond") in ("above", "below", "between")]
    allsyms = []
    for s in hold + watch + idx + EXTRA + alert_tk:
        if s and s not in allsyms:
            allsyms.append(s)
    return allsyms, set(hold)


# ── 국내: 네이버 polling (실시간 · 프리/애프터 포함) ─────────────────────────
def _naver_session(d: dict) -> str:
    st = (d.get("marketStatus") or "").upper()
    typ = (d.get("marketSessionType") or "")
    over = d.get("overMarketPriceInfo") or {}
    if st != "OPEN":
        return "closed"
    if typ == "afterMarket" or over.get("tradingSessionType") == "AFTER_MARKET" and typ != "regularMarket":
        return "post"
    if typ == "preMarket" or over.get("tradingSessionType") == "PRE_MARKET" and typ != "regularMarket":
        return "pre"
    return "reg"


def naver_kr(symbols: list[str]) -> dict:
    out = {}
    codes = [s.split(".")[0] for s in symbols]
    by_code = {s.split(".")[0]: s for s in symbols}
    for i in range(0, len(codes), 20):
        chunk = codes[i:i + 20]
        d = _get(NAVER_STOCK.format(codes=",".join(chunk)))
        for x in d.get("datas", []):
            sym = by_code.get(x.get("itemCode"))
            p = _num(x.get("closePriceRaw") or x.get("closePrice"))
            if not sym or p is None:
                continue
            chg = _num(x.get("compareToPreviousClosePriceRaw") or x.get("compareToPreviousClosePrice"))
            out[sym] = {
                "p": p,
                "pc": (p - chg) if chg is not None else None,
                "c": _num(x.get("fluctuationsRatioRaw") or x.get("fluctuationsRatio")),
                "s": _naver_session(x),
                "t": _epoch(x.get("localTradedAt")),
                "src": "naver",
            }
    return out


def naver_index(symbols: list[str]) -> dict:
    out = {}
    want = {NAVER_INDEX_CODE[s]: s for s in symbols if s in NAVER_INDEX_CODE}
    if not want:
        return out
    d = _get(NAVER_INDEX.format(codes=",".join(want)))
    for x in d.get("datas", []):
        sym = want.get(x.get("itemCode"))
        p = _num(x.get("closePriceRaw"))
        if not sym or p is None:
            continue
        chg = _num(x.get("compareToPreviousClosePriceRaw"))
        st = (x.get("marketStatus") or "").upper()
        out[sym] = {"p": p, "pc": (p - chg) if chg is not None else None,
                    "c": _num(x.get("fluctuationsRatioRaw")),
                    "s": "reg" if st == "OPEN" else "closed",
                    "t": _epoch(x.get("localTradedAt")), "src": "naver"}
    return out


# ── Yahoo chart (미국 전부 + 국내 정규장 종가·장중 추이) ────────────────────
def _period(m: dict, key: str):
    p = ((m.get("currentTradingPeriod") or {}).get(key) or {})
    return p.get("start"), p.get("end")


def yahoo_chart(sym: str, now: int) -> dict:
    d = _get(YAHOO_CHART.format(sym=urllib.parse.quote(sym)))
    r = (d.get("chart") or {}).get("result") or []
    if not r:
        raise ValueError("빈 결과")
    r = r[0]
    m = r.get("meta") or {}
    ts = r.get("timestamp") or []
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    closes = q.get("close") or []
    reg = m.get("regularMarketPrice")
    rt = m.get("regularMarketTime")
    pre_s, pre_e = _period(m, "pre")
    reg_s, reg_e = _period(m, "regular")
    post_s, post_e = _period(m, "post")

    # 정규장 시리즈(추이선) + 마지막 체결(프리/애프터 포함).
    #   range=2d인 이유: 미국 프리마켓(월 17:00~22:30 KST)엔 '오늘' 정규장 점이 0개라 1d로는
    #   추이선이 비었다(9/21 실측). 정규장 시각대(거래소 현지 시각)에 든 점만 모아 **가장 최근 하루**를 쓴다.
    off = m.get("gmtoffset") or 0
    by_day: dict = {}
    last_p, last_t = None, None
    rs_tod = (reg_s + off) % 86400 if reg_s else None
    re_tod = (reg_e + off) % 86400 if reg_e else None
    for t, c in zip(ts, closes):
        if c is None:
            continue
        last_p, last_t = c, t
        if rs_tod is None or re_tod is None:
            continue
        tod = (t + off) % 86400
        if rs_tod <= tod < re_tod:
            by_day.setdefault((t + off) // 86400, []).append(c)
    series = by_day[max(by_day)] if by_day else []

    sess = "closed"
    if reg_s and reg_e and reg_s <= now < reg_e:
        sess = "reg"
    elif pre_s and pre_e and pre_s <= now < pre_e:
        sess = "pre"
    elif post_s and post_e and post_s <= now < post_e:
        sess = "post"

    # rpc = rc(마지막 정규장)의 **그 전날** 종가. chartPreviousClose는 정규장 가격 기준으로 따라온다
    #   (9/21 월 프리 실측: rc=222.27(금) · chartPreviousClose=219.34(목) → 금 +1.34% = 보고서와 일치).
    rpc = m.get("chartPreviousClose") or m.get("previousClose")
    out = {"rc": reg, "rt": rt, "rpc": rpc, "src": "yahoo", "s": sess, "cur": m.get("currency")}
    if reg is not None and rpc:
        out["rcc"] = round((reg / rpc - 1) * 100, 2)
    ext = last_p is not None and last_t and rt and last_t > rt
    if sess in ("pre", "post") and ext:
        # 시간외 체결이 '현재가' — 등락 기준은 마지막 정규장 종가(프리=어제 종가, 애프터=오늘 종가)
        out.update({"p": last_p, "t": last_t, "pc": reg, "x": 1})
    else:
        out.update({"p": reg, "t": rt, "pc": rpc})
        if ext:  # 장 마감 후 남은 시간외 체결은 참고로만
            out.update({"xp": last_p, "xc": round((last_p / reg - 1) * 100, 2) if reg else None})
    if out.get("p") is not None and out.get("pc"):
        out["c"] = round((out["p"] / out["pc"] - 1) * 100, 2)
    if series:
        out["_series"] = series
    return out


def yahoo_spark_meta(symbols: list[str]) -> dict:
    """국내 워치 정규장 종가만 배치로(차트 호출 절약)."""
    out = {}
    for i in range(0, len(symbols), 15):
        chunk = symbols[i:i + 15]
        d = _get(YAHOO_SPARK.format(syms=urllib.parse.quote(",".join(chunk))))
        for r in ((d.get("spark") or {}).get("result") or []):
            resp = (r.get("response") or [{}])[0]
            m = resp.get("meta") or {}
            if m.get("regularMarketPrice") is not None:
                out[r.get("symbol")] = {"rc": m.get("regularMarketPrice"),
                                        "rt": m.get("regularMarketTime")}
    return out


def _compact(vals: list[float], n: int = 80) -> list:
    """추이선 압축: 최대 n점 + 유효숫자 5자리."""
    if len(vals) > n:
        step = len(vals) / n
        vals = [vals[int(i * step)] for i in range(n - 1)] + [vals[-1]]
    return [float(f"{v:.5g}") for v in vals]


def build(now: int | None = None, src: str = "local") -> dict:
    now = now or int(time.time())
    syms, hold = load_universe()
    kr = [s for s in syms if is_kr(s)]
    kr_idx = [s for s in syms if s in NAVER_INDEX_CODE]
    yahoo_syms = [s for s in syms if not is_kr(s) and s not in NAVER_INDEX_CODE]
    # 국내 보유·지수는 추이선·정규장 종가가 필요해 chart로, 국내 워치는 spark 배치로 종가만
    chart_syms = yahoo_syms + [s for s in kr if s in hold] + kr_idx
    spark_syms = [s for s in kr if s not in hold]

    quotes: dict = {}
    series: dict = {}
    errors: list = []

    try:
        quotes.update(naver_kr(kr))
    except Exception as e:  # noqa: BLE001
        errors.append(f"naver-kr: {e}")
    try:
        quotes.update(naver_index(kr_idx))
    except Exception as e:  # noqa: BLE001
        errors.append(f"naver-index: {e}")

    def _one(s):
        return s, yahoo_chart(s, now)

    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(_one, s) for s in chart_syms]
        for f in cf.as_completed(futs):
            try:
                s, y = f.result()
            except Exception as e:  # noqa: BLE001
                errors.append(f"yahoo: {e}")
                continue
            ser = y.pop("_series", None)
            if is_kr(s) or s in NAVER_INDEX_CODE:
                # 국내: 가격은 네이버(실시간) 우선, Yahoo는 정규장 종가·추이선만
                q = quotes.setdefault(s, {})
                q["rc"], q["rt"] = y.get("rc"), y.get("rt")
                if "p" not in q:  # 네이버 실패 시 폴백
                    q.update({k: y[k] for k in ("p", "pc", "c", "s", "t") if k in y})
                    q["src"] = "yahoo"
            else:
                y.pop("cur", None)
                quotes[s] = y
            if ser and (s in hold or s in SERIES_ALWAYS):
                q = quotes.get(s) or {}
                last = q.get("p")
                vals = list(ser)
                if last is not None and q.get("s") == "reg":
                    vals.append(last)
                series[s] = _compact(vals)
    try:
        for s, m in yahoo_spark_meta(spark_syms).items():
            quotes.setdefault(s, {}).update(m)
    except Exception as e:  # noqa: BLE001
        errors.append(f"yahoo-spark: {e}")

    # 세션 요약(앱 상단 배지): 국내는 보유 국내주 / 미국은 보유 미국주 기준 다수결
    def _sess(pred):
        c = {}
        for s, q in quotes.items():
            if pred(s) and q.get("s"):
                c[q["s"]] = c.get(q["s"], 0) + 1
        return max(c, key=c.get) if c else "closed"

    market = {"kr": _sess(lambda s: is_kr(s) and s in hold),
              "us": _sess(lambda s: not is_kr(s) and s in hold)}
    missing = [s for s in syms if s not in quotes or quotes[s].get("p") is None]
    return {
        "v": 1,
        "generated_at": dt.datetime.fromtimestamp(now, KST).strftime("%Y-%m-%d %H:%M:%S KST"),
        "ts": now,
        "src": src,
        "market": market,
        "quotes": quotes,
        "series": series,
        "missing": missing,
        "errors": errors[:12],
    }


def write(payload: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


# ── 로컬 백업 킥 ────────────────────────────────────────────────────────────
def _us_dst(d: dt.date) -> bool:
    """미국 서머타임(3월 둘째 일요일 ~ 11월 첫째 일요일). zoneinfo는 윈도우에서 tzdata가 없을 수 있다."""
    def nth_sunday(y, mth, n):
        first = dt.date(y, mth, 1)
        return first + dt.timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))
    return nth_sunday(d.year, 3, 2) <= d < nth_sunday(d.year, 11, 1)


def market_window_open(now_kst: dt.datetime) -> bool:
    """국내 07:00~20:00 · 미국 프리~애프터(ET 04:00~20:00) 중이면 True. 주말 제외."""
    wd = now_kst.weekday()
    hm = now_kst.hour * 60 + now_kst.minute
    if wd < 5 and 7 * 60 <= hm < 20 * 60:
        return True
    et = now_kst - dt.timedelta(hours=13 if _us_dst(now_kst.date()) else 14)
    ehm = et.hour * 60 + et.minute
    return et.weekday() < 5 and 4 * 60 <= ehm < 20 * 60


def kick(max_age_min: float = 8.0, quiet: bool = False) -> int:
    now = dt.datetime.now(KST)
    if not market_window_open(now):
        if not quiet:
            print("[live-kick] 장 시간 밖 — 건너뜀")
        return 0
    age = None
    try:
        d = _get(PAGES_LIVE + "?t=%d" % time.time(), timeout=8, tries=1)
        age = (time.time() - int(d.get("ts") or 0)) / 60
    except Exception as e:  # noqa: BLE001 — 없거나 깨졌으면 오래된 것으로 본다
        if not quiet:
            print(f"[live-kick] 배포본 조회 실패({e}) — 오래된 것으로 간주")
    if age is not None and age < max_age_min:
        if not quiet:
            print(f"[live-kick] 배포본 {age:.1f}분 전 — 신선, 킥 불필요")
        return 0
    try:
        st = json.load(open(KICK_STATE, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        st = {}
    if time.time() - st.get("last", 0) < max_age_min * 60:
        if not quiet:
            print("[live-kick] 직전 킥 후 대기 중 — 중복 킥 안 함")
        return 0
    try:
        r = subprocess.run(["gh", "workflow", "run", WORKFLOW, "--repo", REPO, "--ref", "main"],
                           capture_output=True, text=True, timeout=40)
        ok = r.returncode == 0
        msg = (r.stdout or r.stderr or "").strip()[:200]
    except Exception as e:  # noqa: BLE001
        ok, msg = False, str(e)
    os.makedirs(LOG_DIR, exist_ok=True)
    st = {"last": time.time(), "ok": ok, "age_min": age, "msg": msg,
          "at": now.strftime("%Y-%m-%d %H:%M KST")}
    with open(KICK_STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    with open(os.path.join(LOG_DIR, "live_kick.log"), "a", encoding="utf-8") as f:
        f.write(json.dumps(st, ensure_ascii=False) + "\n")
    if not quiet or not ok:
        print(f"[live-kick] {'배포 요청 OK' if ok else '배포 요청 실패'} (배포본 {age if age is None else round(age, 1)}분) {msg}")
    return 0 if ok else 3


def main() -> int:
    ap = argparse.ArgumentParser(description="앱 실시간 시세 스냅샷(app/live.json) — 무키·조회 전용")
    ap.add_argument("--out", default=OUT, help="출력 경로 (기본 app/live.json)")
    ap.add_argument("--src", default="local", choices=["local", "cloud"], help="생성 위치 표기")
    ap.add_argument("--print", action="store_true", help="표로 출력(파일도 씀)")
    ap.add_argument("--kick", action="store_true", help="로컬 백업: 배포본이 오래됐으면 배포 워크플로 1회 실행")
    ap.add_argument("--max-age", type=float, default=8.0, help="--kick 신선도 기준(분, 기본 8)")
    ap.add_argument("--quiet", action="store_true", help="정상일 때 출력 생략")
    a = ap.parse_args()
    if a.kick:
        return kick(a.max_age, a.quiet)
    t0 = time.time()
    payload = build(src=a.src)
    write(payload, a.out)
    n = sum(1 for q in payload["quotes"].values() if q.get("p") is not None)
    if a.print:
        for s, q in sorted(payload["quotes"].items()):
            print(f"{s:12} {q.get('p')!s:>12} {q.get('c')!s:>7}% {q.get('s', ''):6} rc={q.get('rc')} {q.get('src', '')}")
    if not a.quiet or payload["errors"]:
        print(f"[live] {payload['generated_at']} · {n}종목 · 장 {payload['market']} · "
              f"추이선 {len(payload['series'])} · 누락 {len(payload['missing'])} · 오류 {len(payload['errors'])} "
              f"· {time.time() - t0:.1f}s → {os.path.relpath(a.out, ROOT)}")
        for e in payload["errors"]:
            print("  !", e)
    return 0 if n else 2


if __name__ == "__main__":
    sys.exit(main())
