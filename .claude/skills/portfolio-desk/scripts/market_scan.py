#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""market_scan.py — 시장 전체 스캐너 (보유·워치 밖을 기계로 훑는다) [11/5 신설 · 정훈 "시장 전체를 훑는 방법을 고안해서 해보자"]

왜 있나
────────────────────────────────────────────────────────────
11/4 신규 아이디어 수신함(idea_inbox)을 만들었지만 들어오는 길이 **누가 말해 준 이름**뿐이었다
(경제사냥꾼 영상·데스크 특징주). 아무도 말하지 않은 종목은 여전히 안 보인다.
이 도구는 **미국 시총 $10B+ 전 종목 + 코스피 시총 상위 200 + 코스닥 상위 100**을 매번 같은 규칙으로 훑어
'밖에서 무언가 일어나고 있는 이름'을 수신함 후보로 올린다.

유니버스 (키 없음)
  · 미국 = 나스닥 스크리너 API(NYSE·NASDAQ·AMEX 전 상장 ~6,900) → 시총 ≥ $10B · 보통주 심볼만
  · 국내 = 네이버 모바일 시총 순위(stockEndType=stock → ETF·ETN 제외)
  · 공통 = 20일 평균 거래대금 하한(미국 $50M · 국내 100억원) — 체결 못 할 이름은 안 올린다
  · 보유·워치는 제외하지 않고 **표시만** 한다(같은 잣대로 우리 종목이 어디쯤인지 보이게)

스크린 4개 — 전부 공개된 방법론이고 손으로 고른 임계값이 아니다
  ① LEADER  추세 리더   = 미너비니 트렌드템플릿 8/8 + RS 백분위 ≥ 80
                          (RS = IBD식 가중 수익률 0.4·3M + 0.2·6M + 0.2·9M + 0.2·12M, 시장별 횡단면 백분위)
  ② GAP     이벤트 갭    = 최근 10거래일 안에 시가 갭 ≥ +5% · 거래량 ≥ 50일 평균 2.5배 · 지금 종가 ≥ 그날 저가
                          (오닐·미너비니의 '파워 어닝 갭' — 갭이 메워지지 않은 것만)
  ③ HIGH    52주 신고가권 = 종가 ≥ 52주 고점 × 0.97 + RS 백분위 ≥ 70
  ④ CONTRA  역발상 공포   = 52주 고점 대비 ≤ min(-35%, 지수 낙폭 − 15%p) · 시총 상위(미국 ≥ $30B · 국내 ≥ 3조원)
                          (지수가 -40%인 시장에서 -35% 절대 기준은 전 종목을 고른다 → 지수보다 15%p 더 빠진 것만)
                          ("공포에 사라" 철학의 후보 공급 — **펀더를 안 봤다.** 떨어진 이유가 정당할 수 있다)
  ⑤ HOLDUP  버틴 종목    = 지수가 고점 대비 -15% 이하인 국면에서만: 종목 낙폭 ≤ 지수 낙폭의 절반 · RS 백분위 ≥ 85
                          (오닐: 조정장에서 가장 덜 빠진 종목이 다음 상승을 이끈다 — 붕괴장에선 ①③이 0이 되므로 이 축이 필요)
  · 종합 = ①②③⑤ 적중 수 → 같은 수면 RS 백분위 순. ④는 따로 줄 세운다(모멘텀과 섞지 않는다).
  · 섹터 분포 = 리더(①)의 섹터 집계 — 밖에서 어느 업종이 끌고 있는지(순환매) 한 줄로.

수신함 연결 (--to-inbox)
  · 회당 상한 K(기본 미국 4 · 국내 2 · 역발상 2) — 수신함은 7일 안에 판정해야 하므로(check_idea_inbox) 홍수를 막는다
  · 이미 수신함에 있는 이름은 출처만 덧붙는다(merge) · 보유·워치는 안 넣는다

채점 (--score) — 이 스캐너도 채점받는다
  · 매 실행의 적중 전부를 `data/app/market_scan_log.jsonl`에 (날짜·가격·스크린) 남긴다
  · `--score`가 20·60거래일 뒤 벤치(^GSPC·^KS11) 대비 초과수익을 스크린별로 집계한다
  · ⚠️ 스크린이 알파를 낸다는 증거는 아직 없다 — 쌓이기 전엔 '발견 도구'일 뿐 예측 도구가 아니다

⚠️ 측정·발견 전용 — 매수 트리거가 아니다. 적중 = "들여다볼 이유"이지 "살 이유"가 아니다.
   룰3(갭 당일 추격 금지)·룰6(국내 22% 초과 동안 국내 매수 0원)·룰1 트랙 순서가 위에 그대로 있다.
⚠️ 모멘텀 스크린(①②③)은 **이미 오른 것**을 고른다 — 별점 철학(데이터 우선 코어 vs 모멘텀 테마)상
   펀더 확인 전엔 '모멘텀 후보'로만 부른다.
⚠️ 생존 편향: 유니버스 = 지금 시총 기준이라 과거 채점에 쓰면 안 된다(--score는 실행 시점 기록만 쓴다).

사용법
  python market_scan.py                    # 전체 스캔 → data/app/market_scan.json + 로그
  python market_scan.py --to-inbox         # + 상위 후보를 idea_inbox에 넣기
  python market_scan.py --report           # 마지막 스캔을 보고서용 마크다운으로
  python market_scan.py --score            # 과거 적중의 20·60거래일 초과수익
  python market_scan.py --us-only / --kr-only / --limit N(디버그)
  python market_scan.py --selftest
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

import idea_inbox  # noqa: E402
import ta_core  # noqa: E402
from history_backfill import bar_date  # noqa: E402

OUT = os.path.join(ROOT, "data", "app", "market_scan.json")
LOG = os.path.join(ROOT, "data", "app", "market_scan_log.jsonl")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{s}?interval=1d&range={r}"
NASDAQ = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&download=true"
NAVER = "https://m.stock.naver.com/api/stocks/marketValue/{m}?page={p}&pageSize=100"

US_MCAP_MIN = 10e9
US_ADV_MIN = 50e6           # 20일 평균 거래대금 $
KR_ADV_MIN = 10e9           # 100억원
KR_TOP = {"KOSPI": 200, "KOSDAQ": 100}
CONTRA_MCAP = {"US": 30e9, "KR": 3e12}
BENCH = {"US": "^GSPC", "KR": "^KS11"}
INBOX_K = {"US": 4, "KR": 2, "CONTRA": 2}
SCREENS = ("LEADER", "GAP", "HIGH", "HOLDUP", "CONTRA")


def _get(url: str, timeout: float = 20.0, tries: int = 3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (404, 400):
                break
            time.sleep(1.5 * (i + 1))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            last = e
            time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"{url[:80]}: {last}")


# ── 유니버스 ─────────────────────────────────────────────────────────────
def us_universe() -> list[dict]:
    rows = _get(NASDAQ, timeout=40)["data"]["rows"]
    out = []
    for x in rows:
        sym = (x.get("symbol") or "").strip()
        try:
            mc = float(x.get("marketCap") or 0)
        except ValueError:
            mc = 0
        if mc < US_MCAP_MIN or not re.fullmatch(r"[A-Z]{1,5}(/[A-Z])?", sym):
            continue                                   # 우선주·워런트·유닛(^ · . · 6자+) 제외
        out.append({"ticker": sym.replace("/", "-"), "name": _clean(x.get("name")), "market": "US",
                    "sector": x.get("sector") or "", "industry": x.get("industry") or "", "mcap": mc,
                    "ref_px": _num(x.get("lastsale"))})
    return out


_SUFFIX = re.compile(r"\s+(Class [A-C] )?(Common Stock|Ordinary Shares|American Depositary Shares|ADS|"
                     r"Common Shares|Depositary Shares|Registered Shares|Subordinate Voting Shares).*$", re.I)


def _clean(n: str | None) -> str:
    n = _SUFFIX.sub("", (n or "").strip())
    return re.sub(r",?\s+(Inc\.?|Corporation|Corp\.?|Co\.|Ltd\.?|plc|N\.V\.|S\.A\.|Holdings?)$", "", n, flags=re.I).strip()


def _num(x):
    try:
        return float(str(x).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def px_mismatch(yahoo_px, ref_px, prev_px=None, tol: float = 0.15) -> bool:
    """Yahoo 마지막 봉·직전 봉 **둘 다**가 유니버스 출처(나스닥·네이버) 가격과 tol 넘게 다르면 True.
    ★ 하나만 보면 안 된다 — 장중엔 나스닥 lastsale이 전일 종가라 실적 급변 종목(그날 ±15%)이 데이터 결함으로
      빠졌다(11/5 첫 실행: FIS·FIX·UNM·TRMB 등 6개 = GAP 후보가 정확히 그 종목들). 국내는 Yahoo 봉이 하루 늦다.
      둘 다 15%+ 어긋나면 분할 미반영·잘못된 심볼이다."""
    if not (yahoo_px and ref_px):
        return False
    far = lambda x: x is None or abs(x / ref_px - 1) > tol  # noqa: E731
    return far(yahoo_px) and far(prev_px)


def kr_universe() -> list[dict]:
    out = []
    for m, n in KR_TOP.items():
        suf = ".KS" if m == "KOSPI" else ".KQ"
        got = []
        for p in range(1, 10):
            st = _get(NAVER.format(m=m, p=p)).get("stocks") or []
            got += [s for s in st if s.get("stockEndType") == "stock"]
            if len(got) >= n or not st:
                break
        for s in got[:n]:
            out.append({"ticker": s["itemCode"] + suf, "name": s.get("stockName"), "market": "KR",
                        "sector": m, "industry": "", "mcap": float(s.get("marketValueRaw") or 0),
                        "ref_px": _num(s.get("closePriceRaw"))})
    return out


# ── 시세 ───────────────────────────────────────────────────────────────
def bars(sym: str, rng: str = "2y") -> dict | None:
    try:
        d = _get(YAHOO.format(s=urllib.request.quote(sym), r=rng))
        res = d["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        off = res.get("meta", {}).get("gmtoffset", 0)
    except Exception:
        return None
    o, h, l, c, v, t = [], [], [], [], [], []
    for i, ts in enumerate(res.get("timestamp") or []):
        vals = [q[k][i] for k in ("open", "high", "low", "close", "volume")]
        if any(x is None for x in vals) or vals[3] <= 0:
            continue
        o.append(vals[0]); h.append(vals[1]); l.append(vals[2]); c.append(vals[3]); v.append(vals[4])
        t.append(bar_date(ts, off))
    return {"o": o, "h": h, "l": l, "c": c, "v": v, "d": t} if len(c) >= 60 else None


def _ret(c, n):
    return c[-1] / c[-1 - n] - 1 if len(c) > n and c[-1 - n] > 0 else None


def metrics(b: dict) -> dict:
    """스크린 입력값(순수 함수 — 시세 dict만 받는다)."""
    c, h, l, o, v = b["c"], b["h"], b["l"], b["o"], b["v"]
    c252, h252, l252 = c[-252:], h[-252:], l[-252:]
    r3, r6, r9, r12 = (_ret(c, n) for n in (63, 126, 189, 252))
    parts = [(0.4, r3), (0.2, r6), (0.2, r9), (0.2, r12)]
    have = [(w, r) for w, r in parts if r is not None]
    rs_raw = sum(w * r for w, r in have) / sum(w for w, _ in have) if have else None
    adv20 = sum(c[i] * v[i] for i in range(-20, 0)) / 20
    hi52, lo52 = max(h252), min(l252)
    tmpl = ta_core.minervini_template(c252, h252, l252) if len(c) >= 252 else None
    gap = None
    for i in range(max(len(c) - 10, 51), len(c)):
        avg50 = sum(v[i - 50:i]) / 50
        g = o[i] / c[i - 1] - 1
        if g >= 0.05 and avg50 > 0 and v[i] >= 2.5 * avg50 and c[-1] >= l[i]:
            if gap is None or g > gap["gap_pct"]:
                gap = {"date": b["d"][i], "gap_pct": round(g * 100, 1), "vol_x": round(v[i] / avg50, 1)}
    return {"price": c[-1], "date": b["d"][-1], "adv20": adv20, "rs_raw": rs_raw,
            "ret_3m": r3, "ret_12m": r12, "from_high": c[-1] / hi52 - 1, "from_low": c[-1] / lo52 - 1,
            "tmpl": tmpl["passed"] if tmpl else None, "gap": gap,
            "chg_1d": _ret(c, 1)}


def rank_pct(vals: list) -> list:
    """횡단면 백분위(0~100). None은 None."""
    idx = sorted((x, i) for i, x in enumerate(vals) if x is not None)
    out = [None] * len(vals)
    n = len(idx)
    for r, (_, i) in enumerate(idx):
        out[i] = round(100 * r / (n - 1), 1) if n > 1 else 50.0
    return out


def screen(rows: list[dict], idx_dd: float = 0.0) -> None:
    """rows(같은 시장) 제자리 갱신: rs_pct·screens·hits. idx_dd = 지수 52주 고점 대비(음수)."""
    contra_cut = min(-0.35, idx_dd - 0.15)
    for r, p in zip(rows, rank_pct([r["m"]["rs_raw"] for r in rows])):
        r["rs_pct"] = p
    for r in rows:
        m, s = r["m"], []
        rs = r["rs_pct"] or 0
        if m["tmpl"] == 8 and rs >= 80:
            s.append("LEADER")
        if m["gap"]:
            s.append("GAP")
        if m["from_high"] >= -0.03 and rs >= 70:
            s.append("HIGH")
        if idx_dd <= -0.15 and m["from_high"] >= idx_dd / 2 and rs >= 85:
            s.append("HOLDUP")
        if m["from_high"] <= contra_cut and r["mcap"] >= CONTRA_MCAP[r["market"]]:
            s.append("CONTRA")
        r["screens"] = s
        r["hits"] = sum(1 for x in s if x != "CONTRA")


def run(markets=("US", "KR"), limit: int | None = None, workers: int = 8, log=print) -> dict:
    uni_own = idea_inbox.universe()
    inbox = {idea_inbox._key(x["ticker"]) for x in idea_inbox.load().get("ideas", [])}
    out = {"run_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="minutes"),
           "markets": {}}
    for mk in markets:
        t0 = time.time()
        uni = us_universe() if mk == "US" else kr_universe()
        if limit:
            uni = sorted(uni, key=lambda x: -x["mcap"])[:limit]
        bb = bars(BENCH[mk])
        idx_dd = (bb["c"][-1] / max(bb["h"][-252:]) - 1) if bb else 0.0
        rows, fail = [], []
        with cf.ThreadPoolExecutor(workers) as ex:
            futs = {ex.submit(bars, u["ticker"]): u for u in uni}
            for f in cf.as_completed(futs):
                u, b = futs[f], f.result()
                if not b:
                    fail.append(u["ticker"]); continue
                m = metrics(b)
                if m["adv20"] < (US_ADV_MIN if mk == "US" else KR_ADV_MIN):
                    continue
                m["px_flag"] = px_mismatch(m["price"], u.get("ref_px"), b["c"][-2])
                rows.append({**u, "m": m})
        bad = [r["ticker"] for r in rows if r["m"]["px_flag"]]
        rows = [r for r in rows if not r["m"]["px_flag"]]     # 가격이 출처와 15%+ 다르면 스크린에서 뺀다(분할·심볼 결함)
        screen(rows, idx_dd)
        for r in rows:
            r["own"] = r["ticker"] in uni_own
            r["in_inbox"] = idea_inbox._key(r["ticker"]) in inbox
        mom = sorted([r for r in rows if r["hits"]], key=lambda r: (-r["hits"], -(r["rs_pct"] or 0)))
        con = sorted([r for r in rows if "CONTRA" in r["screens"]], key=lambda r: r["m"]["from_high"])
        lead_sec = {}
        for r in rows:
            if "LEADER" in r["screens"]:
                k = r["industry"] or r["sector"] or "?"
                if mk == "US":
                    k = r["sector"] or "?"
                lead_sec[k] = lead_sec.get(k, 0) + 1
        out["markets"][mk] = {
            "index": BENCH[mk], "index_from_high": round(idx_dd * 100, 1),
            "contra_cut": round(min(-0.35, idx_dd - 0.15) * 100, 1),
            "universe": len(uni), "fetched": len(uni) - len(fail), "liquid": len(rows),
            "fail_sample": fail[:10], "fail_n": len(fail), "px_mismatch": bad,
            "asof": max((r["m"]["date"] for r in rows), default=None), "secs": round(time.time() - t0),
            "counts": {s: sum(1 for r in rows if s in r["screens"]) for s in SCREENS},
            "leader_sectors": dict(sorted(lead_sec.items(), key=lambda kv: -kv[1])),
            "momentum": [_slim(r) for r in mom[:40]],
            "contra": [_slim(r) for r in con[:25]],
            "own_view": [_slim(r) for r in rows if r["own"]],
        }
        log(f"[{mk}] 유니버스 {len(uni)} · 시세 {len(uni) - len(fail)} · 유동성 통과 {len(rows)} · "
            f"{out['markets'][mk]['counts']} · {round(time.time() - t0)}초")
    return out


def _slim(r: dict) -> dict:
    m = r["m"]
    f = lambda x, k=1: None if x is None else round(x * 100, k)  # noqa: E731
    return {"ticker": r["ticker"], "name": r["name"], "market": r["market"], "sector": r["sector"],
            "industry": r["industry"], "mcap": r["mcap"], "price": m["price"], "date": m["date"],
            "rs_pct": r["rs_pct"], "tmpl": m["tmpl"], "ret_3m": f(m["ret_3m"]), "ret_12m": f(m["ret_12m"]),
            "from_high": f(m["from_high"]), "chg_1d": f(m["chg_1d"], 2), "gap": m["gap"],
            "screens": r["screens"], "hits": r["hits"], "own": r["own"], "in_inbox": r["in_inbox"]}


def scan_age_days(path: str = OUT, now: dt.datetime | None = None) -> float | None:
    try:
        at = dt.datetime.fromisoformat(json.load(open(path, encoding="utf-8"))["run_at"])
    except (OSError, ValueError, KeyError):
        return None
    now = now or dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    return (now - at).total_seconds() / 86400


def append_log(res: dict) -> int:
    n = 0
    with open(LOG, "a", encoding="utf-8") as f:
        for mk, blk in res["markets"].items():
            seen = set()
            for r in blk["momentum"] + blk["contra"]:
                if r["ticker"] in seen:
                    continue
                seen.add(r["ticker"])
                f.write(json.dumps({"scan": res["run_at"][:10], "ticker": r["ticker"], "market": mk,
                                    "date": r["date"], "price": r["price"], "screens": r["screens"],
                                    "own": r["own"]}, ensure_ascii=False) + "\n")
                n += 1
    return n


def pick_inbox(res: dict) -> list[dict]:
    """수신함 후보: 보유·워치·기존 수신함 제외, 시장별 상한."""
    picks = []
    for mk in res["markets"]:
        blk = res["markets"][mk]
        fresh = [r for r in blk["momentum"] if not r["own"] and not r["in_inbox"] and r["hits"] >= 2]
        picks += fresh[:INBOX_K[mk]]
        # 역발상은 **시총 큰 순** — 가장 깊이 빠진 순으로 뽑으면 논지가 깨진 이름(삼천당 -86%·RKLB -65%)이 먼저 온다.
        #   '공포에 사라'의 후보는 큰 회사가 과하게 빠진 경우다(11/5 첫 실행에서 교정).
        con = sorted([r for r in blk["contra"] if not r["own"] and not r["in_inbox"]], key=lambda r: -(r.get("mcap") or 0))
        picks += con[:1 if mk == "KR" else INBOX_K["CONTRA"] - 1]
    return picks


def to_inbox(picks: list[dict], day: str) -> list[tuple]:
    d, uni = idea_inbox.load(), idea_inbox.universe()
    res = []
    for r in picks:
        kind = "역발상(고점 대비 %s%%)" % r["from_high"] if "CONTRA" in r["screens"] else \
               "모멘텀(%s · RS %s)" % ("+".join(r["screens"]), r["rs_pct"])
        idea = {"ticker": r["ticker"], "name": r["name"], "market": r["market"], "ref": f"scan:{day}",
                "claim": f"[시장 스캔] {kind} · 3M {r['ret_3m']}% · 12M {r['ret_12m']}% · {r['sector']} {r['industry']}".strip(),
                "verdict": "미확인(스캔 = 가격 신호만 · 펀더 미검토)",
                "first_take": "스캔 적중 — 펀더·밸류·보유 연결 미검토. 모멘텀이면 룰3, 국내면 룰6이 먼저 막는다."}
        res.append((r["ticker"], idea_inbox.add(d, idea, "scan", uni, day)))
    idea_inbox.save(d)
    return res


# ── 출력 ───────────────────────────────────────────────────────────────
def _cap(r):
    return f"${r['mcap'] / 1e9:,.0f}B" if r["market"] == "US" else f"{r['mcap'] / 1e12:,.1f}조"


def report_md(res: dict, top: int = 10) -> str:
    L = [f"### 🛰️ 시장 전체 스캔 ({res['run_at']} · 측정 전용 — 적중 = 들여다볼 이유, 살 이유 아님)", ""]
    for mk, blk in res["markets"].items():
        L.append(f"**{'미국 시총 $10B+' if mk == 'US' else '코스피 200 + 코스닥 100'}** — 유니버스 {blk['universe']} · "
                 f"유동성 통과 {blk['liquid']} · 리더 {blk['counts']['LEADER']} · 갭 {blk['counts']['GAP']} · "
                 f"신고가권 {blk['counts']['HIGH']} · 버팀 {blk['counts']['HOLDUP']} · 역발상 {blk['counts']['CONTRA']}"
                 f" · 지수 고점대비 {blk['index_from_high']}%"
                 + f" · 시세 기준일 {blk.get('asof')}"
                 + (f" · ⚠️시세 실패 {blk['fail_n']}" if blk["fail_n"] else "")
                 + (f" · ⚠️출처 가격 불일치 제외 {len(blk.get('px_mismatch') or [])}" if blk.get("px_mismatch") else ""))
        if blk["leader_sectors"]:
            L.append("리더 섹터: " + " · ".join(f"{k} {v}" for k, v in list(blk["leader_sectors"].items())[:6]))
        L += ["", "| 종목 | 시총 | 스크린 | RS%ile | 템플릿 | 3M | 12M | 고점대비 | 갭 | 상태 |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for r in blk["momentum"][:top]:
            g = f"{r['gap']['date'][5:]} +{r['gap']['gap_pct']}% ×{r['gap']['vol_x']}" if r["gap"] else ""
            st = "보유·워치" if r["own"] else ("수신함" if r["in_inbox"] else "새 이름")
            L.append(f"| {r['name'][:22]} ({r['ticker']}) | {_cap(r)} | {'+'.join(r['screens'])} | {r['rs_pct']} | "
                     f"{r['tmpl']}/8 | {r['ret_3m']}% | {r['ret_12m']}% | {r['from_high']}% | {g} | {st} |")
        if blk["contra"]:
            L.append("")
            L.append(f"역발상(고점 대비 {blk['contra_cut']}% 이하 대형주 · 펀더 미검토): " + " · ".join(
                f"{r['name'][:16]}({r['ticker']}) {r['from_high']}%" + (" [보유·워치]" if r["own"] else "")
                for r in sorted(blk["contra"], key=lambda r: -(r.get("mcap") or 0))[:8]))
        L.append("")
    return "\n".join(L)


def score(log_path: str = LOG, horizons=(20, 60)) -> int:
    if not os.path.exists(log_path):
        print("로그 없음 — 스캔을 먼저 돌린다"); return 0
    recs = [json.loads(x) for x in open(log_path, encoding="utf-8") if x.strip()]
    cache, agg = {}, {}
    for r in recs:
        for s in (r["screens"] or ["-"]):
            for H in horizons:
                agg.setdefault((r["market"], s, H), [])
    for r in recs:
        for sym in (r["ticker"], BENCH[r["market"]]):
            if sym not in cache:
                cache[sym] = bars(sym, "2y")
        b, bb = cache[r["ticker"]], cache[BENCH[r["market"]]]
        if not b or not bb or r["date"] not in b["d"] or r["date"] not in bb["d"]:
            continue
        i, j = b["d"].index(r["date"]), bb["d"].index(r["date"])
        for H in horizons:
            if i + H < len(b["c"]) and j + H < len(bb["c"]):
                ex = (b["c"][i + H] / b["c"][i]) - (bb["c"][j + H] / bb["c"][j])
                for s in r["screens"]:
                    agg[(r["market"], s, H)].append(ex * 100)
    print("시장 스크린 지평  n  평균초과%p  중앙%p  승률")
    for (mk, s, H), xs in sorted(agg.items()):
        if not xs:
            print(f"{mk} {s:7} {H:3}d  0  (지평 미도래)"); continue
        xs2 = sorted(xs)
        print(f"{mk} {s:7} {H:3}d {len(xs):3} {sum(xs) / len(xs):+8.2f} {xs2[len(xs2) // 2]:+7.2f} "
              f"{100 * sum(1 for x in xs if x > 0) / len(xs):5.1f}%")
    return 0


# ── 자가검증 ───────────────────────────────────────────────────────────
def _synth(n=260, drift=0.002, gap_at=None, seed=1):
    import random
    rnd = random.Random(seed)
    c, o, h, l, v, d = [], [], [], [], [], []
    p = 100.0
    base = dt.date(2025, 1, 1)
    for i in range(n):
        op = p * (1.08 if gap_at is not None and i == gap_at else 1.0)
        p = op * (1 + drift + rnd.uniform(-0.005, 0.005))
        o.append(op); c.append(p); h.append(max(op, p) * 1.003); l.append(min(op, p) * 0.997)
        v.append(3e6 if gap_at is not None and i == gap_at else 1e6)
        d.append((base + dt.timedelta(days=i)).isoformat())
    return {"o": o, "h": h, "l": l, "c": c, "v": v, "d": d}


def selftest() -> int:
    ok = True

    def chk(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok &= bool(cond)

    up = metrics(_synth(drift=0.003))
    dn = metrics(_synth(drift=-0.003))
    gp = metrics(_synth(drift=0.001, gap_at=255))
    chk("상승 추세 = 템플릿 8/8", up["tmpl"] == 8)
    chk("하락 추세 = 템플릿 8/8 아님", dn["tmpl"] != 8)
    chk("갭 +8%·거래량 3배 = GAP 적발", gp["gap"] and gp["gap"]["gap_pct"] >= 7.9 and gp["gap"]["vol_x"] >= 2.5)
    chk("갭 없음 = GAP 없음", up["gap"] is None)
    filled = _synth(drift=0.001, gap_at=255)
    filled["c"][-1] = filled["l"][255] * 0.9           # 갭이 메워짐
    chk("메워진 갭은 GAP 아님", metrics(filled)["gap"] is None)
    chk("백분위 단조·None 보존", rank_pct([3, None, 1, 2]) == [100.0, None, 0.0, 50.0])
    rows = [{"ticker": t, "market": "US", "mcap": mc, "m": metrics(b)} for t, mc, b in
            [("UP", 50e9, _synth(drift=0.003)), ("DN", 50e9, _synth(drift=-0.003)),
             ("FLAT", 50e9, _synth(drift=0.0)), ("SMALLDN", 5e9, _synth(drift=-0.003, seed=3))]]
    screen(rows)
    s = {r["ticker"]: r["screens"] for r in rows}
    crash = [{"ticker": t, "market": "KR", "mcap": 5e12, "m": metrics(b)} for t, b in
             [("HOLD", _synth(drift=0.0, seed=5)), ("FALL", _synth(drift=-0.002)), ("CRASH", _synth(drift=-0.005))]]
    screen(crash, idx_dd=-0.40)
    cs = {r["ticker"]: r["screens"] for r in crash}
    chk("붕괴장(지수 -40%): 버틴 종목 = HOLDUP", "HOLDUP" in cs["HOLD"])
    chk("붕괴장: 지수만큼 빠진 종목은 CONTRA 아님(상대 기준)", "CONTRA" not in cs["FALL"])
    chk("붕괴장: 지수보다 15%p+ 더 빠진 종목 = CONTRA", "CONTRA" in cs["CRASH"])
    chk("평상장(지수 -2%)엔 HOLDUP 없음", not any("HOLDUP" in x for x in s.values()))
    chk("가격 불일치: 분할 미반영(1/10) 적발", px_mismatch(10.0, 100.0, 10.5))
    chk("가격 불일치: 하루 변동(-8%)은 통과", not px_mismatch(92.0, 100.0, 99.0))
    chk("가격 불일치: 장중 실적 급락(-25%, 출처=전일 종가)은 통과", not px_mismatch(75.0, 100.0, 100.0))
    chk("이름 정리", _clean("Visa Inc. Class A Common Stock") == "Visa" and _clean("Eli Lilly and Company Common Stock") == "Eli Lilly and Company")
    chk("상승주 = LEADER·HIGH", "LEADER" in s["UP"] and "HIGH" in s["UP"])
    chk("대형 하락주 = CONTRA", "CONTRA" in s["DN"])
    chk("소형 하락주는 CONTRA 아님(시총 하한)", "CONTRA" not in s["SMALLDN"])
    chk("하락주는 모멘텀 적중 0", next(r for r in rows if r["ticker"] == "DN")["hits"] == 0)
    # 수신함 후보: 보유·기존 수신함 제외 · 적중 2개 미만 제외 · 상한
    fake = {"run_at": "2026-11-05T00:00", "markets": {"US": {"momentum": [
        {"ticker": "A", "own": True, "in_inbox": False, "hits": 3, "screens": ["LEADER"]},
        {"ticker": "B", "own": False, "in_inbox": True, "hits": 3, "screens": ["LEADER"]},
        {"ticker": "C", "own": False, "in_inbox": False, "hits": 1, "screens": ["GAP"]},
        *[{"ticker": f"N{i}", "own": False, "in_inbox": False, "hits": 2, "screens": ["LEADER", "HIGH"]}
          for i in range(9)]], "contra": [
        {"ticker": "Zsmall", "own": False, "in_inbox": False, "hits": 0, "screens": ["CONTRA"], "mcap": 3e10},
        {"ticker": "Z", "own": False, "in_inbox": False, "hits": 0, "screens": ["CONTRA"], "mcap": 3e11}]}}}
    pk = [r["ticker"] for r in pick_inbox(fake)]
    chk("수신함 후보: 보유·기존·적중1 제외", not {"A", "B", "C"} & set(pk))
    chk(f"수신함 후보 상한(미국 {INBOX_K['US']}+역발상 1)", pk == ["N0", "N1", "N2", "N3", "Z"])
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="시장 전체 스캐너 (측정·발견 전용)")
    ap.add_argument("--us-only", action="store_true")
    ap.add_argument("--kr-only", action="store_true")
    ap.add_argument("--limit", type=int, help="시장별 시총 상위 N만(디버그)")
    ap.add_argument("--to-inbox", action="store_true", help="상위 후보를 idea_inbox에 넣는다")
    ap.add_argument("--report", action="store_true", help="마지막 스캔 마크다운")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--no-log", action="store_true")
    ap.add_argument("--if-stale", type=float, metavar="DAYS",
                    help="마지막 스캔이 DAYS일보다 오래됐을 때만 돈다(보고서 파이프라인용 · 주간 주기)")
    ap.add_argument("--commit", action="store_true", help="결과·로그·수신함만 origin/main 위에 커밋(git_sync)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.score:
        return score()
    if a.report:
        if not os.path.exists(OUT):
            print("스캔 결과 없음 — market_scan.py를 먼저 돌린다"); return 1
        print(report_md(json.load(open(OUT, encoding="utf-8")), a.top)); return 0
    if a.if_stale is not None and (age := scan_age_days()) is not None and age <= a.if_stale:
        print(f"마지막 스캔 {age:.1f}일 전 — {a.if_stale}일 이내라 건너뜀 (--report로 재사용)")
        return 0
    mk = ("US",) if a.us_only else ("KR",) if a.kr_only else ("US", "KR")
    res = run(mk, a.limit)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    if not a.no_log:
        print(f"로그 {append_log(res)}건 → {os.path.relpath(LOG, ROOT)}")
    if a.to_inbox:
        for tk, r in to_inbox(pick_inbox(res), res["run_at"][:10]):
            print(f"수신함 {r:12} {tk}")
    print(report_md(res, a.top))
    if a.commit:
        import git_sync
        files = [os.path.relpath(x, ROOT).replace(os.sep, "/") for x in (OUT, LOG, idea_inbox._path())]
        n = sum(blk["counts"]["LEADER"] for blk in res["markets"].values())
        print("git:", git_sync.describe(git_sync.publish(ROOT, files, f"시장 전체 스캔 자동 {res['run_at'][:10]} — 리더 {n}")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
