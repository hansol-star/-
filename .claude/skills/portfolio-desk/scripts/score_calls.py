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
"""
import argparse, json, os, re, subprocess, sys, urllib.request, urllib.error
from datetime import datetime, date

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

# ── 콜 문자열에서 가격 레벨 추출 ("480,000~530,000원", "$220~250", "295,000원 (눌림)") ──
def levels(s):
    if not isinstance(s, str):
        return []
    nums = re.findall(r"\d[\d,]*\.?\d*", s.replace("–", "-"))
    out = []
    for n in nums:
        try:
            v = float(n.replace(",", ""))
        except ValueError:
            continue
        if v >= 1:                       # 연도·각주 0 등 잡음 최소화
            out.append(v)
    return out

def rng(s):
    """(low, high) 또는 None. 단일값이면 (v, v)."""
    lv = levels(s)
    if not lv:
        return None
    # 연도/날짜 토큰(2026 등) 큰 잡음 제거: 가격대만 보려고 최빈 자릿수 군집을 쓰진 않고
    # 단순히 1~2개만 — 콜 문자열은 보통 맨 앞에 가격 범위가 온다.
    lv = lv[:2]
    return (min(lv), max(lv)) if len(lv) == 2 else (lv[0], lv[0])

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

def backfill():
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
    with open(os.path.join(ROOT, LEDGER_REL), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"✅ 백필 완료: {len(rows)}개 콜 → {LEDGER_REL} ({len(git_commits())} 커밋, 중복일 제거)")

def append_today():
    p = os.path.join(ROOT, STOCKS_REL)
    sj = json.load(open(p, encoding="utf-8"))
    # as_of는 서술 문장일 수 있음 → source_report 파일명의 날짜를 우선, 없으면 오늘.
    m = re.search(r"(\d{4}-\d{2}-\d{2})", str(sj.get("source_report", "")))
    if not m:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(sj.get("as_of", "")))
    dt = m.group(1) if m else date.today().isoformat()
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
    today = date.today()
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
        graded.append({**c, "age": age, "fwd": fwd, "buy_touched": buy_touched,
                       "target_hit": target_hit, "dir_ok": dir_ok})

    print("\n" + "=" * 60)
    print("  콜 캘리브레이션 — score_calls.py (reflection 정량화)")
    print("=" * 60)
    if not graded:
        print(f"\n채점할 성숙 콜 없음(나이 ≥ {min_age}일). 원장은 계속 누적됨.")
        if net_err: print(f"시세 조회 실패: {sorted(set(net_err))}")
        return

    # 별점 버킷별 평균 전진수익률 + 방향 적중률
    print(f"\n채점 콜 {len(graded)}개 (나이 ≥ {min_age}일, 최신 시세 경로 기준)\n")
    print(f"{'별점':<6}{'콜수':>5}{'평균전진%':>11}{'방향적중':>12}")
    by = {}
    for g in graded:
        by.setdefault(g.get("stars"), []).append(g)
    for st in sorted([k for k in by if isinstance(k, int)], reverse=True):
        rows = by[st]
        avg = sum(r["fwd"] for r in rows) / len(rows)
        dirs = [r["dir_ok"] for r in rows if r["dir_ok"] is not None]
        hit = f"{sum(dirs)}/{len(dirs)}" if dirs else "—(중립)"
        print(f"⭐{st:<5}{len(rows):>5}{avg:>10.2f}%{hit:>12}")

    bz = [g for g in graded if g["buy_touched"] is not None]
    if bz:
        touched = sum(1 for g in bz if g["buy_touched"])
        print(f"\n매수존 진입(눌림 도달): {touched}/{len(bz)}  ({touched/len(bz)*100:.0f}%)")
    tg = [g for g in graded if g["target_hit"] is not None]
    if tg:
        hit = sum(1 for g in tg if g["target_hit"])
        print(f"목표가 하단 터치:        {hit}/{len(tg)}  ({hit/len(tg)*100:.0f}%)")

    # 편향 플래그(self-review가 찾던 것 — 자동 탐지)
    print("\n— 편향 점검 —")
    means = {st: sum(r["fwd"] for r in by[st]) / len(by[st])
             for st in by if isinstance(st, int)}
    if 5 in means and 3 in means and means[5] < means[3]:
        print(f"  ⚠️ 별점 역전: ⭐5 평균({means[5]:+.2f}%) < ⭐3({means[3]:+.2f}%) — 채점기준 재점검 후보")
    if 5 in means and 4 in means and means[5] < means[4]:
        print(f"  ⚠️ ⭐5 평균({means[5]:+.2f}%) < ⭐4({means[4]:+.2f}%) — 최상위 확신 콜 과신 여부 점검")
    star_dist = {st: len(by[st]) for st in sorted(by) if isinstance(st, int)}
    print(f"  별점 분포(최신 원장 비중 포함): {star_dist}")
    if net_err:
        print(f"  시세 조회 실패(채점 제외): {sorted(set(net_err))}")
    print("\n※ 자동 변경 없음 — 캘리브레이션 참고용. 교정은 self-review에서 사람이 판단.")
    print("※ 데이터가 짧을수록(콜 나이 적음) 노이즈 큼 — 누적될수록 신뢰도↑.\n")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backfill", action="store_true", help="git 히스토리에서 원장 재생성")
    ap.add_argument("--append", action="store_true", help="현재 stocks.json 콜을 원장에 추가")
    ap.add_argument("--min-age", type=int, default=1, help="채점 최소 보유일(기본 1)")
    a = ap.parse_args()
    if a.backfill:
        backfill()
    if a.append:
        append_today()
    if not a.backfill and not a.append:
        score(a.min_age)
    else:
        score(a.min_age)

if __name__ == "__main__":
    main()
