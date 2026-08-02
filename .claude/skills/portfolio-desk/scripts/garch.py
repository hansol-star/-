#!/usr/bin/env python3
"""garch.py — GARCH(1,1) 변동성 '선행' 예측 엔진 (stdlib only·무의존·포터블)

근거: study_log 2026-07-18 ④ (Miles Deutscher · Engle 2003 노벨상 ARCH → Bollerslev
GARCH). vol_gauge.py는 '어제까지 얼마나 격렬했나'(후행 실현변동성 RV/EWMA)를 재고,
이 스크립트는 '내일 얼마나 격렬할까'(선행 1일 예측)를 낸다 — 영상 방법론의 진짜 핵심.

모델:  σ²_t = ω + α·r²_{t-1} + β·σ²_{t-1}
  ω=기본레벨(자산 성격) · α=오늘충격 반영(여진) · β=어제변동성 반영(메모리).
  지속성 = α+β (1에 가까울수록 변동성이 오래 간다 = 예측이 먹히는 이유).
  장기평균 변동성 = √(ω/(1−α−β)). 방향은 일절 예측 안 함(그래서 노벨상 — 데이터가
  지지하는 것[크기]만 주장). fit = 가우시안 로그우도 MLE, 최적화 = Nelder-Mead 자체구현.

성격: **측정·예측 전용.** 숫자만 낸다 — 사이즈/트랜치/안전핀 룰은 안 바꾼다(그 매핑은
정훈 승인 별건). history_backfill.py 캐시(상장 이래 전 일봉)를 1차로 소비 → GARCH를
'수십 년' 이력에 적합(BTC 15년 대신 코스피 29.6년). 캐시 없으면 Yahoo 2년 폴백.

사용:
  python3 garch.py                    # 코스피·코스닥 + 보유 15종목
  python3 garch.py --tickers ^KS11,NVDA
  python3 garch.py --index-only
  python3 garch.py --verbose          # 파라미터·지속성·장기평균·기간구조
  python3 garch.py --json
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import statistics
import urllib.error
import urllib.parse
import urllib.request
import cli_common

try:
    import history_backfill as hb
except ImportError:
    hb = None
try:
    import market_data as md
except ImportError:
    md = None

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
TRADING_DAYS = 252
PCT_LOOKBACK = 252  # 폭풍 %ile 랭킹 창 = 최근 1년(vol_gauge·crash_tf §5b 정의와 일치)


# ---------- 데이터 ----------
def _yahoo_rows(symbol: str, rng: str = "2y") -> list[tuple[str, float]]:
    """Yahoo 일봉 (ISO날짜, 종가) 리스트. 실패 시 빈 리스트."""
    url = (YAHOO_CHART.format(symbol=urllib.parse.quote(symbol))
           + f"?interval=1d&range={rng}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        closes = res["indicators"]["quote"][0]["close"]
        out = []
        for t, c in zip(ts, closes):
            if c is None:
                continue
            # KRX 09:00 KST = 00:00 UTC, 미장 09:30 ET = 13:30/14:30 UTC → UTC 날짜가 거래일과 일치
            out.append((datetime.datetime.utcfromtimestamp(t).date().isoformat(), float(c)))
        return out
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError,
            IndexError, TypeError, ValueError):
        return []


def load_closes(symbol: str) -> list[float]:
    """history_backfill 캐시(상장 이래 전 일봉) + **최신 봉 top-up** → 없으면 Yahoo 2년 폴백.

    [2026-07-26 교정 — 안전핀 판정에 직결된 실사고] 캐시만 읽던 舊 구현은 백필 루틴이
    밀리면 **최근 거래일이 통째로 빠진 채** GARCH를 적합했다. 실측: ^KS11 캐시 마지막이
    7/22(6,797.70)라 **7/24 -5.72% 급락(6,690.62)을 못 본 상태로** vol_sizing이 안전핀·
    폭풍 %ile을 판정 중이었다(같은 시각 vol_gauge는 라이브라 6,690.62·86.1%ile).
    → 캐시 뒤에 **캐시 마지막 날짜보다 새로운 Yahoo 봉만 이어붙인다**(깊은 이력 유지 +
    최신성 확보). 네트워크 실패 시 캐시 그대로 = 기존 동작보다 나빠지지 않는다.
    """
    if hb is not None:
        rows = hb.load_cached(symbol)
        if len(rows) > 60:
            closes = [c for _, c in rows]
            last_date = rows[-1][0]
            fresh = [(d, c) for d, c in _yahoo_rows(symbol, "3mo") if d > last_date]
            closes += [c for _, c in fresh]
            return closes
    return [c for _, c in _yahoo_rows(symbol, "2y")]


def pct_log_returns(closes: list[float]) -> list[float]:
    """퍼센트 로그수익률(×100) — 수치 조건수 개선용."""
    out = []
    for i in range(1, len(closes)):
        p0, p1 = closes[i - 1], closes[i]
        if p0 and p1 and p0 > 0 and p1 > 0:
            out.append(100.0 * math.log(p1 / p0))
    return out


# ---------- GARCH(1,1) 우도 (분산 타겟팅) ----------
# Engle-Mezrich 분산 타겟팅: 무조건 분산을 표본분산 uvar에 고정 →
#   ω = uvar·(1−α−β). (α,β) 2개만 적합. 지속성이 단위근에 붙어도 장기평균이
#   폭발하지 않고 '표본 변동성'과 일치 → 해석·수치 둘 다 안정.
def neg_loglik(params, rets, var0, uvar):
    """음의 로그우도(2파라미터·분산타겟팅). 제약 위반 시 큰 페널티."""
    alpha, beta = params
    if alpha < 0 or beta < 0 or alpha + beta >= 0.99999:
        return 1e12
    omega = uvar * (1 - alpha - beta)
    if omega <= 1e-10:
        return 1e12
    ll = 0.0
    sig2 = var0
    for r in rets:
        if sig2 <= 1e-12:
            sig2 = 1e-12
        ll += math.log(sig2) + (r * r) / sig2
        sig2 = omega + alpha * (r * r) + beta * sig2
    return 0.5 * ll  # 상수항(ln2π) 생략 — 최적화엔 무관


def neg_loglik_t(params, rets, var0, uvar):
    """Student-t GARCH 음의 로그우도(팻테일). params=(α,β,ν). ν>2(분산 유한).
    표준화잔차를 단위분산 t로 스케일 → 극단이벤트(크래시)에 더 잘 맞는다."""
    alpha, beta, nu = params
    if alpha < 0 or beta < 0 or alpha + beta >= 0.99999 or nu <= 2.05:
        return 1e12
    omega = uvar * (1 - alpha - beta)
    if omega <= 1e-10:
        return 1e12
    c = (math.lgamma((nu + 1) / 2) - math.lgamma(nu / 2)
         - 0.5 * math.log(math.pi * (nu - 2)))  # t 정규화상수(관측당 상수)
    ll = 0.0
    sig2 = var0
    for r in rets:
        if sig2 <= 1e-12:
            sig2 = 1e-12
        z2 = (r * r) / sig2
        ll += -c + 0.5 * math.log(sig2) + 0.5 * (nu + 1) * math.log(1 + z2 / (nu - 2))
        sig2 = omega + alpha * (r * r) + beta * sig2
    return ll


def nelder_mead(f, x0, args=(), step=0.5, tol=1e-8, maxiter=2000):
    """자체 구현 Nelder-Mead 심플렉스(3차원). scipy 없이 GARCH MLE."""
    n = len(x0)
    # 초기 심플렉스
    simplex = [list(x0)]
    for i in range(n):
        pt = list(x0)
        pt[i] = pt[i] + step * (abs(pt[i]) + 0.1)
        simplex.append(pt)
    fvals = [f(p, *args) for p in simplex]
    a, g, r, s = 1.0, 2.0, 0.5, 0.5  # 반사·확장·수축·축소 계수

    for _ in range(maxiter):
        # 정렬
        order = sorted(range(n + 1), key=lambda k: fvals[k])
        simplex = [simplex[k] for k in order]
        fvals = [fvals[k] for k in order]
        if abs(fvals[-1] - fvals[0]) < tol:
            break
        # 무게중심(최악점 제외)
        centroid = [sum(simplex[k][j] for k in range(n)) / n for j in range(n)]
        # 반사
        xr = [centroid[j] + a * (centroid[j] - simplex[-1][j]) for j in range(n)]
        fr = f(xr, *args)
        if fvals[0] <= fr < fvals[-2]:
            simplex[-1], fvals[-1] = xr, fr
            continue
        if fr < fvals[0]:  # 확장
            xe = [centroid[j] + g * (xr[j] - centroid[j]) for j in range(n)]
            fe = f(xe, *args)
            simplex[-1], fvals[-1] = (xe, fe) if fe < fr else (xr, fr)
            continue
        # 수축
        xc = [centroid[j] + r * (simplex[-1][j] - centroid[j]) for j in range(n)]
        fc = f(xc, *args)
        if fc < fvals[-1]:
            simplex[-1], fvals[-1] = xc, fc
            continue
        # 축소
        best = simplex[0]
        for k in range(1, n + 1):
            simplex[k] = [best[j] + s * (simplex[k][j] - best[j]) for j in range(n)]
            fvals[k] = f(simplex[k], *args)
    order = sorted(range(n + 1), key=lambda k: fvals[k])
    return simplex[order[0]], fvals[order[0]]


def conditional_vol_series(params, rets, var0):
    """전 구간 조건부 분산 σ²_t 시계열(연율% 변동성으로 반환). 백분위·기간구조용."""
    omega, alpha, beta = params
    out = []
    sig2 = var0
    for r in rets:
        out.append(math.sqrt(max(sig2, 1e-12)) * math.sqrt(TRADING_DAYS))  # 연율%
        sig2 = omega + alpha * (r * r) + beta * sig2
    # 마지막 이후(=내일) 예측
    fwd = math.sqrt(max(sig2, 1e-12)) * math.sqrt(TRADING_DAYS)
    return out, fwd, sig2


def _regime(pct: float | None) -> str:
    if pct is None:
        return "?"
    if pct >= 90:
        return "폭풍"
    if pct >= 70:
        return "높음"
    if pct >= 40:
        return "보통"
    return "차분"


def fit_forecast(symbol: str, closes: list[float] | None = None,
                 student_t: bool = False) -> dict:
    """symbol의 GARCH(1,1) 적합·1일 선행예측.
    closes 주면 그걸 씀(=point-in-time 소급 태깅용 — 과거 날짜까지 자른 종가 전달).
    student_t=True면 팻테일 t분포 우도(ν 추정) — 크래시 꼬리에 더 정직."""
    if closes is None:
        closes = load_closes(symbol)
    if len(closes) < 120:
        return {"symbol": symbol, "ok": False, "reason": f"데이터 부족({len(closes)})"}
    rets = pct_log_returns(closes)
    mu = statistics.fmean(rets)
    rets = [r - mu for r in rets]  # 디민
    uvar = statistics.pvariance(rets) if len(rets) > 1 else 1.0  # 표본 무조건분산(타겟)
    var0 = uvar
    nu = None
    if student_t:
        # (α,β,ν) 적합. 초기 ν=6(주식 전형 팻테일)
        (alpha, beta, nu), _ = nelder_mead(neg_loglik_t, [0.08, 0.90, 6.0],
                                           args=(rets, var0, uvar))
        nu = round(nu, 1)
    else:
        # 분산타겟팅: (α,β) 2개만 적합. 초기값 α=0.08, β=0.90(주식 GARCH 전형)
        (alpha, beta), _ = nelder_mead(neg_loglik, [0.08, 0.90], args=(rets, var0, uvar))
    omega = uvar * (1 - alpha - beta)
    persist = alpha + beta
    series, fwd, sig2_next = conditional_vol_series((omega, alpha, beta), rets, var0)
    # 장기평균 변동성 = 표본 변동성(타겟팅으로 일치·robust). 연율%
    lr_vol = math.sqrt(uvar) * math.sqrt(TRADING_DAYS)
    # 백분위: 내일 예측이 조건부변동성 분포에서 몇 %ile.
    # [2026-07-26 교정] 정본 기준창 = **최근 1년(252거래일)** — CLAUDE.md·crash_tf가 정의한
    # 폭풍 점수가 "오늘 변동성의 **최근 1년** 백분위"이기 때문. 舊 구현은 상장 이래 전 이력
    # (^KS11 = 7,290봉 ≈ 30년) 대비로 재서 같은 시장을 vol_gauge 86%ile / garch 99%ile로
    # 다르게 불렀고, §5b(폭풍 ≥90 동결 vs <90 극소창)의 판정이 스크립트마다 갈렸다.
    # 적합(fit)은 전 이력을 그대로 쓰고, **랭킹 창만** 1년으로 맞춘다. 전 이력 기준값은
    # pct_rank_all로 함께 반환(맥락용 — "30년 기준으론 몇 %ile인가").
    win = series[-PCT_LOOKBACK:] if len(series) > PCT_LOOKBACK else series
    pct = 100.0 * sum(1 for v in win if v <= fwd) / len(win) if win else None
    pct_all = 100.0 * sum(1 for v in series if v <= fwd) / len(series) if series else None
    # 다일 기간구조(5·20일 평균 예측 — 평균회귀)
    def hstep(h):
        s2 = sig2_next
        acc = s2
        for _ in range(1, h):
            s2 = omega + persist * s2
            acc += s2
        return math.sqrt(acc / h) * math.sqrt(TRADING_DAYS)
    return {
        "symbol": symbol, "ok": True,
        "n": len(series), "last_close": round(closes[-1], 2),
        "forecast_vol": round(fwd, 1),          # 내일 예측 연율%
        "rv_now": round(series[-1], 1),          # 오늘 조건부(≈현재)
        "pct_rank": round(pct, 0) if pct is not None else None,          # 정본 = 최근 1년 창
        "pct_rank_all": round(pct_all, 0) if pct_all is not None else None,  # 전 이력 기준(맥락용)
        "pct_window": min(len(series), PCT_LOOKBACK),
        "regime": _regime(pct),
        "omega": round(omega, 5), "alpha": round(alpha, 3), "beta": round(beta, 3),
        "persistence": round(persist, 3),
        "shock_w": round(alpha / persist, 2) if persist > 0 else None,
        "memory_w": round(beta / persist, 2) if persist > 0 else None,
        "longrun_vol": round(lr_vol, 1) if lr_vol else None,
        "fc_5d": round(hstep(5), 1), "fc_20d": round(hstep(20), 1),
        "dist": "student-t" if student_t else "gaussian", "df": nu,
    }


# ---------- 유니버스 ----------
def _universe(args):
    if args.tickers:
        return [(t.strip(), t.strip()) for t in cli_common.split_tickers(args.tickers) if t.strip()]
    idx_all = md.GROUPS["index"] if md else [("코스피", "^KS11"), ("코스닥", "^KQ11")]
    idx = [(l, s) for (l, s) in idx_all if s in ("^KS11", "^KQ11")]
    if args.index_only:
        return idx
    hold = md.GROUPS["holdings"] if md else []
    return idx + list(hold)


def main() -> int:
    ap = argparse.ArgumentParser(description="GARCH(1,1) 선행 변동성 예측 (측정 전용·stdlib)")
    ap.add_argument("--tickers", help="쉼표·공백구분 Yahoo 심볼(기본=코스피·코스닥+보유15)")
    ap.add_argument("--index-only", action="store_true")
    ap.add_argument("--verbose", action="store_true", help="파라미터·지속성·장기평균·기간구조")
    ap.add_argument("--student-t", action="store_true", help="팻테일 t분포 우도(ν 추정)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    uni = _universe(args)
    rows = [(label, fit_forecast(sym, student_t=args.student_t)) for (label, sym) in uni]

    if args.json:
        print(json.dumps([{**{"label": l}, **g} for (l, g) in rows], ensure_ascii=False, indent=2))
        return 0

    print("GARCH(1,1) 선행 변동성 예측 (내일 연율%·전이력 적합·측정 전용)")
    if args.verbose:
        hdr = ["자산", "종가", "내일예측%", "%ile", "국면", "지속성", "충격/메모리", "장기평균%", "5d", "20d"]
        print("  ".join(f"{h:<9}" for h in hdr))
        print("-" * 96)
        for label, g in rows:
            if not g.get("ok"):
                print(f"{label:<9}  {g.get('reason','?')}")
                continue
            sm = f"{g['shock_w']}/{g['memory_w']}"
            print(f"{label:<9}  {g['last_close']:<9}{g['forecast_vol']:<9}"
                  f"{str(g['pct_rank']):<7}{g['regime']:<7}{g['persistence']:<8}"
                  f"{sm:<11}{str(g['longrun_vol']):<9}{g['fc_5d']:<6}{g['fc_20d']}")
    else:
        hdr = ["자산", "종가", "내일예측(연율%)", "%ile", "국면", "장기평균%"]
        print("  ".join(f"{h:<12}" for h in hdr))
        print("-" * 74)
        for label, g in rows:
            if not g.get("ok"):
                print(f"{label:<12}  {g.get('reason','?')}")
                continue
            print(f"{label:<12}  {g['last_close']:<12}{g['forecast_vol']:<16}"
                  f"{str(g['pct_rank']):<6}{g['regime']:<7}{g['longrun_vol']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
