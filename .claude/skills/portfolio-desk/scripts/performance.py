#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
performance.py — 계좌 실수익률(시간가중) · 데스크 매매의 가치 · 현금의 비용

왜 있나 [9/21 신설 — 정훈 "우리가 잘 자금들 운용하고 있는지 체크해봐"]
────────────────────────────────────────────────────────────
그 질문에 우리는 **숫자로 답을 못 했다.** 가진 건 세 개뿐이었다:
  · 평가손익률(-2.8%) — 매입 시점이 다 달라서 '운용'의 성과가 아니다
  · 실현손익(+10.6만·7건) — 판 것만 본다. 안 판 결정·산 결정은 채점 안 된다
  · portfolio_stats의 60일 수익률(-6.9%) — **지금 비중을 과거에 거꾸로 적용한 역산**이다.
    그 사이 한 매매(트림·매수)가 전부 빠져 있어서 '우리가 한 일'을 재지 못한다.

이 스크립트는 체결 원장(trades.jsonl)을 날마다 재생해 **그날 실제로 들고 있던 수량**으로
수익률을 잇는다(시간가중 = 입출금에 오염되지 않는다). 그리고 같은 기간을 두 번 더 돌린다:

  ① 실제        — 원장대로 사고판 포트
  ② 가만히      — 시작일 수량을 그대로 들고 아무것도 안 했다면
  ③ 벤치마크    — 코스피 · S&P500(원화 환산) · 시작일 국내비중으로 섞은 혼합

  ①-② = **데스크 매매가 더한(뺀) 가치**. 트림·매수·청산 전부의 합산 성적표다.

현금은 따로 잰다 — "놀고 있는 돈"이 실제로 얼마를 잃었고(혹은 피했고) 있는지:
  Σ(전일 현금 × 그날 S&P500 원화수익률) = 현금을 S&P에 넣어뒀다면의 차이.

방법 (주식 슬리브, 일별 Modified Dietz → 기하 연결)
────────────────────────────────────────────────
  r_d = (V_d − V_{d-1} − F_d) / (V_{d-1} + ½·F_d)
  V = Σ 수량 × 종가 × (미국이면 환율), F = 그날 매수대금 − 매도대금(원화, 수수료·세금 포함)
  → 그날 중간에 산 것의 손익도 들어간다(체결가 → 종가). 원장 밖 입출금은 F에 없으니 수익률을 안 흐린다.
  계좌 전체(현금 포함) = 같은 손익 + 달러 현금의 환평가 / (주식 + 현금). 현금 잔고는
  data/snapshots의 그날 이전 최근값을 쓴다(초기 스냅샷은 현금이 갱신 안 된 날이 있어 **근사**).

⚠️ 한계 — 측정 전용, 어떤 룰도 안 바꾼다
  · 배당은 원장에 없다 → 주식 수익률이 배당만큼 과소(보유가 성장주 위주라 작다).
  · 미국 날짜(美 장 기준)와 국내 날짜를 같은 달력에 놓는다 — 하루 단위 시차는 기간 전체에선 상쇄된다.
  · ②는 '아무것도 안 했다면'이지 '더 잘할 수 있었다'가 아니다. ①<②여도 위험을 줄인 대가일 수 있다
    (예: 폭락장 트림) — 수익률만으로 판단하지 말고 최대낙폭을 같이 본다.

사용법:
  python3 performance.py                 # 데스크 착수(6/13)부터 오늘까지
  python3 performance.py --from 2026-07-30
  python3 performance.py --json          # 기계 출력
  python3 performance.py --emit          # data/app/performance.json 갱신 (build_app_data가 소비)
"""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)
import trades  # noqa: E402  체결 원장 로더(정본)

HIST = os.path.join(REPO, "data", "history")
SNAPS = os.path.join(REPO, "data", "snapshots")
OUT = os.path.join(REPO, "data", "app", "performance.json")
START_DEFAULT = trades.DESK_START
KOSPI, SPX, FX = "^KS11", "^GSPC", "KRW=X"


# ── 시세 ─────────────────────────────────────────────────────────────
_cache: dict[str, tuple[list[str], list[float]]] = {}


def _series(sym: str) -> tuple[list[str], list[float]]:
    if sym in _cache:
        return _cache[sym]
    fn = sym.replace("^", "_").replace("=", "_")
    path = os.path.join(HIST, fn + ".csv")
    if not os.path.exists(path):
        path = os.path.join(HIST, sym + ".csv")
    ds, cs = [], []
    if os.path.exists(path):
        for r in csv.DictReader(open(path, encoding="utf-8")):
            try:
                c = float(r["close"])
            except (KeyError, TypeError, ValueError):
                continue
            ds.append(r["date"][:10])
            cs.append(c)
    _cache[sym] = (ds, cs)
    return ds, cs


def close_on(sym: str, d: str) -> float | None:
    """d 이전(포함) 마지막 종가 — 휴장일은 직전 종가로 채운다."""
    ds, cs = _series(sym)
    i = bisect.bisect_right(ds, d) - 1
    return cs[i] if i >= 0 else None


def calendar(start: str, end: str) -> list[str]:
    """국내 또는 미국 중 한쪽이라도 열린 날."""
    days = set()
    for sym in (KOSPI, SPX):
        ds, _ = _series(sym)
        days.update(x for x in ds if start <= x <= end)
    return sorted(days)


# ── 원장 재생(날짜별 수량) ─────────────────────────────────────────────
def positions_by_day(rows: list[dict], days: list[str]) -> dict[str, dict[str, float]]:
    """각 날짜 **장 마감 후** 보유 수량. 그날 체결까지 반영."""
    out, q, i = {}, {}, 0
    rows = [r for r in rows if r.get("side") in ("opening", "buy", "sell")]
    for d in days:
        while i < len(rows) and rows[i]["date"] <= d:
            r = rows[i]
            sh = float(r.get("shares") or 0)
            q[r["ticker"]] = q.get(r["ticker"], 0.0) + (sh if r["side"] != "sell" else -sh)
            if abs(q[r["ticker"]]) < trades.QTY_TOL:
                q.pop(r["ticker"])
            i += 1
        out[d] = dict(q)
    return out


def names() -> dict[str, str]:
    """티커 → 표시 이름. 원장 label은 국내가 종목코드라 portfolio.json(보유·워치·퇴역 워치) 이름을 쓴다."""
    out = {}
    try:
        p = json.load(open(trades.PORTFOLIO_JSON, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    for grp in (p.get("holdings") or {}).values():
        for h in grp:
            out[h["ticker"]] = h.get("label") or h["ticker"]
    for key in ("watchlist", "watch_retired"):
        w = p.get(key) or []
        for h in (w if isinstance(w, list) else []):
            if isinstance(h, dict) and h.get("ticker"):
                out.setdefault(h["ticker"], h.get("label") or h["ticker"])
    return out


def currency_of(rows: list[dict]) -> dict[str, str]:
    return {r["ticker"]: r.get("currency", "KRW") for r in rows}


def value(q: dict[str, float], d: str, cur: dict[str, str]) -> tuple[float, list[str]]:
    fx = close_on(FX, d)
    v, miss = 0.0, []
    for tk, sh in q.items():
        p = close_on(tk, d)
        if p is None:
            miss.append(tk)
            continue
        v += sh * p * (fx if cur.get(tk) == "USD" else 1.0)
    return v, miss


def flows_on(rows: list[dict], d: str, cur: dict[str, str]) -> float:
    """그날 주식 슬리브로 들어간 돈(매수 +, 매도 -). 수수료·세금은 비용 쪽."""
    fx = close_on(FX, d)
    f = 0.0
    for r in rows:
        if r.get("date") != d or r.get("side") not in ("buy", "sell"):
            continue
        amt = trades._amount(r)
        fee = float(r.get("fee") or 0) + float(r.get("tax") or 0)
        m = fx if cur.get(r["ticker"]) == "USD" else 1.0
        f += (amt + fee) * m if r["side"] == "buy" else -(amt - fee) * m
    return f


# ── 현금(스냅샷) ─────────────────────────────────────────────────────
def cash_series() -> tuple[list[str], list[tuple[float, float]]]:
    ds, vs = [], []
    for fn in sorted(glob.glob(os.path.join(SNAPS, "*.json"))):
        try:
            s = json.load(open(fn, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if s.get("cash_krw") is None:
            continue
        ds.append(str(s.get("date") or os.path.basename(fn)[:10]))
        vs.append((float(s["cash_krw"]), float(s.get("cash_usd") or 0.0)))
    return ds, vs


def cash_on(cs, d: str) -> tuple[float, float] | None:
    ds, vs = cs
    i = bisect.bisect_right(ds, d) - 1
    return vs[i] if i >= 0 else None


# ── 계산 ─────────────────────────────────────────────────────────────
def _mdd(curve: list[float]) -> float:
    peak, worst = 1.0, 0.0
    for x in curve:
        peak = max(peak, x)
        worst = min(worst, x / peak - 1)
    return round(worst * 100, 2)


def run(start: str, end: str) -> dict:
    rows = trades.load_ledger()
    cur = currency_of(rows)
    days = calendar(start, end)
    if len(days) < 2:
        return {"error": f"기간 내 거래일 부족: {start}~{end}"}
    base = days[0]
    pos = positions_by_day(rows, days)
    cs = cash_series()

    q0 = pos[base]
    kr0 = sum(sh * (close_on(tk, base) or 0) for tk, sh in q0.items() if cur.get(tk) != "USD")
    v0, _ = value(q0, base, cur)
    kr_w0 = kr0 / v0 if v0 else 0.0

    act, hold, tot = [1.0], [1.0], [1.0]
    bench = {"코스피": [1.0], "S&P500(원화)": [1.0], "혼합(시작 국내비중)": [1.0]}
    missing, trade_days, flow_sum = set(), 0, 0.0
    cash_cost_spx = cash_cost_ks = 0.0
    cash_w = []
    prev = base
    for d in days[1:]:
        va_p, m1 = value(pos[prev], prev, cur)
        va_d, m2 = value(pos[d], d, cur)
        missing.update(m1 + m2)
        f = flows_on(rows, d, cur)
        if f:
            trade_days += 1
            flow_sum += f
        gain = va_d - va_p - f
        den = va_p + 0.5 * f
        act.append(act[-1] * (1 + (gain / den if den > 0 else 0.0)))

        vh_p, _ = value(q0, prev, cur)
        vh_d, _ = value(q0, d, cur)
        hold.append(hold[-1] * (vh_d / vh_p if vh_p else 1.0))

        fx_p, fx_d = close_on(FX, prev), close_on(FX, d)
        c = cash_on(cs, prev)
        ck, cu = c if c else (0.0, 0.0)
        cash_p = ck + cu * fx_p
        fx_gain = cu * (fx_d - fx_p)
        tden = va_p + cash_p + 0.5 * f
        tot.append(tot[-1] * (1 + ((gain + fx_gain) / tden if tden > 0 else 0.0)))
        cash_w.append(cash_p / (va_p + cash_p) if (va_p + cash_p) else 0.0)

        rk = close_on(KOSPI, d) / close_on(KOSPI, prev) - 1
        rs = (close_on(SPX, d) * fx_d) / (close_on(SPX, prev) * fx_p) - 1
        bench["코스피"].append(bench["코스피"][-1] * (1 + rk))
        bench["S&P500(원화)"].append(bench["S&P500(원화)"][-1] * (1 + rs))
        bench["혼합(시작 국내비중)"].append(bench["혼합(시작 국내비중)"][-1] * (1 + kr_w0 * rk + (1 - kr_w0) * rs))
        # 현금을 S&P(원화)·코스피에 넣어뒀다면 — 원화 현금만. 달러 현금의 환손익은 이미 tot에 있다.
        cash_cost_spx += ck * rs + cu * fx_p * (close_on(SPX, d) / close_on(SPX, prev) - 1)
        cash_cost_ks += cash_p * rk
        prev = d

    # 스냅샷 대사 — 재생한 주식가치가 스냅샷과 맞는가(분할·원장 누락 탐지).
    #   ⚠️ 스냅샷은 portfolio.json(수기 갱신)을 따라가서 체결 반영이 1~5일 늦는다(7/29 GOOGL·8/27 META 실측).
    #   그래서 '괴리 = 원장 오류'가 아니다 → 직전 7일 안에 원장 체결이 있던 괴리는 '스냅샷 지연'으로 분리하고,
    #   체결과 무관한 괴리만 원장 누락·분할 의심으로 올린다.
    #   값은 **스냅샷 자신의 가격**으로 매긴다 — 스냅샷은 저녁(KST)에 찍혀 美 전일 종가를 쓰는 날과
    #   당일 종가를 쓰는 날이 섞여 있어, 우리 시세로 매기면 가격 시차가 수량 오류처럼 보인다(6/18 실측).
    #   수량만 비교해야 원장 누락·분할이 드러난다.
    trade_dates = sorted({r["date"] for r in rows if r.get("side") in ("buy", "sell")})
    label = names()
    recon, unexplained = [], []
    for fn in sorted(glob.glob(os.path.join(SNAPS, "*.json"))):
        s = json.load(open(fn, encoding="utf-8"))
        d = str(s.get("date") or "")
        if not (base <= d <= end) or s.get("kr_value") is None or s.get("us_value_usd") is None:
            continue
        sfx = float(s.get("fx_usdkrw") or close_on(FX, d))
        snap_v = float(s["kr_value"]) + float(s["us_value_usd"]) * sfx
        dd = max([x for x in days if x <= d] or [base])
        sp = s.get("positions") or {}
        rep_v = 0.0
        for tk, sh in pos[dd].items():
            p = (sp.get(tk) or sp.get(label.get(tk, "")) or {}).get("price") or close_on(tk, dd) or 0.0
            rep_v += sh * float(p) * (sfx if cur.get(tk) == "USD" else 1.0)
        if not snap_v:
            continue
        dev = round((rep_v / snap_v - 1) * 100, 2)
        recon.append((d, dev))
        if abs(dev) >= 1.0:
            # 스냅샷은 수기 갱신이라 체결보다 늦게도, 소급 생성돼 앞서게도 된다 → 앞뒤 7일
            day = dt.date.fromisoformat(d)
            lo, hi = (day - dt.timedelta(days=7)).isoformat(), (day + dt.timedelta(days=7)).isoformat()
            if not any(lo <= t <= hi for t in trade_dates):
                unexplained.append((d, dev))
    worst = max(recon, key=lambda x: abs(x[1])) if recon else None

    # 매매별 기여 — 체결가 → 기간 말 종가(원화, 기말 환율). 매도는 '팔지 않았다면'의 부호 반대.
    #   합계는 desk_value와 대략 맞는다(현금의 환효과·일중 경로는 빠진다). 사후확신이지 판정이 아니다.
    fx_e = close_on(FX, days[-1])
    contrib = []
    for r in rows:
        if r.get("side") not in ("buy", "sell") or not (base < r["date"] <= days[-1]):
            continue
        pe = close_on(r["ticker"], days[-1])
        if pe is None:
            continue
        m = fx_e if cur.get(r["ticker"]) == "USD" else 1.0
        sh, px = float(r.get("shares") or 0), float(r.get("price") or 0)
        v = sh * (pe - px) * m * (1 if r["side"] == "buy" else -1)
        contrib.append({"date": r["date"], "ticker": r["ticker"], "label": label.get(r["ticker"], r["ticker"]),
                        "side": r["side"], "shares": round(sh, 6), "price": px, "end_price": pe,
                        "krw": round(v), "move_pct": round((pe / px - 1) * 100, 1) if px else None})
    contrib.sort(key=lambda x: x["krw"])
    by_side = {s: round(sum(c["krw"] for c in contrib if c["side"] == s)) for s in ("buy", "sell")}

    pct = lambda x: round((x - 1) * 100, 2)  # noqa: E731
    out = {
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "from": base, "to": days[-1], "days": len(days) - 1,
        "method": "주식=일별 Modified Dietz 기하연결(원장 재생 수량) · 계좌=주식손익+달러현금 환평가 / (주식+스냅샷 현금)",
        "actual": {"stocks_twr_pct": pct(act[-1]), "account_twr_pct": pct(tot[-1]),
                   "stocks_mdd_pct": _mdd(act), "account_mdd_pct": _mdd(tot)},
        "hold": {"stocks_twr_pct": pct(hold[-1]), "stocks_mdd_pct": _mdd(hold),
                 "note": f"{base} 수량을 그대로 들고 아무 매매도 안 했다면"},
        "desk_value_pct": round((act[-1] - hold[-1]) * 100, 2),
        "benchmarks": {k: {"twr_pct": pct(v[-1]), "mdd_pct": _mdd(v)} for k, v in bench.items()},
        "start_kr_weight_pct": round(kr_w0 * 100, 1),
        "trade_days": trade_days, "net_into_stocks_krw": round(flow_sum),
        "cash": {"avg_weight_pct": round(sum(cash_w) / len(cash_w) * 100, 1) if cash_w else None,
                 "vs_spx_krw": round(cash_cost_spx), "vs_kospi": round(cash_cost_ks),
                 "note": "현금을 S&P500(원화)·코스피에 넣어뒀다면의 손익. 음수 = 현금이 손실을 피했다"},
        "trades": {"by_side_krw": by_side, "n": len(contrib),
                   "worst": contrib[:5], "best": contrib[::-1][:5],
                   "note": "체결가→기간 말 종가 · 매도는 '팔지 않았다면'의 반대 부호 · 사후확신이지 판정이 아니다"},
        "reconcile": {"n": len(recon), "worst": worst,
                      "within_1pct": sum(1 for _, v in recon if abs(v) < 1.0),
                      "snapshot_lag": sum(1 for _, v in recon if abs(v) >= 1.0) - len(unexplained),
                      "unexplained": unexplained,
                      "ok": not unexplained},
        "missing_prices": sorted(missing),
        "curve": [{"d": d, "act": round(a, 5), "hold": round(h, 5), "acct": round(t, 5),
                   "ks": round(k, 5), "spx": round(s, 5)}
                  for d, a, h, t, k, s in zip(days, act, hold, tot, bench["코스피"], bench["S&P500(원화)"])],
    }
    return out


def render(r: dict) -> str:
    if r.get("error"):
        return "⚠️ " + r["error"]
    a, h, b = r["actual"], r["hold"], r["benchmarks"]
    L = [f"=== 운용 성과 {r['from']} → {r['to']} ({r['days']}일) ===", "",
         f"{'':22}{'수익률':>9}{'최대낙폭':>10}",
         f"{'실제 · 주식':22}{a['stocks_twr_pct']:>+8.2f}%{a['stocks_mdd_pct']:>+9.2f}%",
         f"{'실제 · 계좌(현금 포함)':20}{a['account_twr_pct']:>+8.2f}%{a['account_mdd_pct']:>+9.2f}%",
         f"{'가만히 있었다면':20}{h['stocks_twr_pct']:>+8.2f}%{h['stocks_mdd_pct']:>+9.2f}%"]
    for k, v in b.items():
        L.append(f"{k:20}{v['twr_pct']:>+8.2f}%{v['mdd_pct']:>+9.2f}%")
    L += ["", f"데스크 매매가 더한 가치 = {r['desk_value_pct']:+.2f}%p (실제 주식 − 가만히) · 매매일 {r['trade_days']}일",
          f"시작 국내비중 {r['start_kr_weight_pct']}% · 주식으로 순유입 {r['net_into_stocks_krw']:+,}원"]
    c = r["cash"]
    if c["avg_weight_pct"] is not None:
        L.append(f"현금 평균 비중 {c['avg_weight_pct']}% · S&P(원화)에 넣었다면 {c['vs_spx_krw']:+,}원 · 코스피였다면 {c['vs_kospi']:+,}원")
    t = r["trades"]
    if t["n"]:
        L += ["", f"매매별 기여(사후) — 매수 {t['by_side_krw']['buy']:+,}원 · 매도 {t['by_side_krw']['sell']:+,}원"]
        for c in t["worst"][:3] + [x for x in t["best"][:3] if x["krw"] > 0]:
            side = "매수" if c["side"] == "buy" else "매도"
            L.append(f"  {c['date']} {c['label']:<10} {side} {c['price']:,.2f} → {c['end_price']:,.2f} ({c['move_pct']:+.1f}%)  {c['krw']:+,}원")
    rc = r["reconcile"]
    L.append("")
    L.append(f"스냅샷 대사 {rc['n']}일 · 1% 이내 {rc['within_1pct']}일 · 스냅샷 지연 {rc['snapshot_lag']}일"
             + (f" · ⚠️ 체결 무관 괴리 {len(rc['unexplained'])}일 {rc['unexplained'][:3]} — 원장 누락·분할 의심" if rc["unexplained"] else " · 원장 정상"))
    if r["missing_prices"]:
        L.append("⚠️ 시세 없는 종목(가치 0 처리): " + ", ".join(r["missing_prices"]))
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="계좌 실수익률(시간가중)·데스크 매매 가치·현금 비용 — 측정 전용")
    ap.add_argument("--from", dest="start", default=START_DEFAULT, help=f"시작일 (기본 {START_DEFAULT} 데스크 착수)")
    ap.add_argument("--to", dest="end", default=dt.date.today().isoformat())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--emit", action="store_true", help="data/app/performance.json 갱신")
    a = ap.parse_args()
    r = run(a.start, a.end)
    if a.emit and not r.get("error"):
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
            f.write("\n")
    if a.json:
        print(json.dumps({k: v for k, v in r.items() if k != "curve"}, ensure_ascii=False, indent=1))
    else:
        print(render(r))
    return 1 if r.get("error") or not r.get("reconcile", {}).get("ok", True) else 0


if __name__ == "__main__":
    sys.exit(main())
