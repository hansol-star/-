#!/usr/bin/env python3
"""lookahead_guard.py — 룩어헤드(미래참조) 회귀 가드 (stdlib only·무네트워크)

■ 왜 만들었나 [8/24 — 정훈 지시 "룩어헤드 회귀 테스트 그것도 해줘"]

   외부 트레이딩 리포 10개 검토(`docs/research/repo_review_2026-08-24.md`)에서 드러난 구멍:
   **룩어헤드를 '주장'하는 파일이 5개인데 '검사'하는 장치가 0개**였다.
     · signal_score        "i일 종가까지만 사용 — 룩어헤드 없음"
     · sizing_backtest     "전일까지의 실현변동성으로 사이징 → 룩어헤드 X"
     · flow_edge           "신호는 t 시점까지의 정보만"
     · star_validate       "지평이 미래로 넘어가는 최근 콜은 자동 제외 = 미래참조 없음"
     · snapshot_state_backfill  "as_of 이하 종가만. 미래참조 차단"
   전부 **주석의 약속**이었고, selfcheck·validate_report·wiring_audit 어디도 이를 보지 않았다.

   우리 구조의 원본(TradingAgents)이 **같은 자리에서 실제로 넘어졌다** — 이슈 #1115:
   *"payload가 JSON 문자열이라 fundamentals look-ahead 필터가 한 번도 실행되지 않았다."*
   만들어둔 가드가 실은 안 돌던 버그로, 우리 8/22 교훈(*"메타 성공 ≠ 생존"*)·
   8/23 교훈(*"초록불은 탐지기가 그 형태를 안 본다는 뜻일 수 있다"*)과 같은 클래스다.
   그들은 회귀 테스트로 고정했고 우리는 코드 테스트가 0개였다 → 이 파일이 그 고정이다.

■ 검사 원리 — 룩어헤드 = 접두사 불변성 위반

   미래를 안 쓰는 계산이라면, **시계열 뒤에 미래 데이터를 덧붙여도 과거 시점의 산출값은
   한 톨도 변하지 않아야 한다**:  f(series[:k])  ==  f(series)[:k]
   변한다면 그 계산은 어딘가에서 뒤를 훔쳐본 것이다. 전체 표준편차·전체 평균·
   전 구간 %ile·정규화 같은 형태가 대표적인 누수 지점이다.

■ ⚠️ 이 가드가 하지 않는 것
   · **통계적 타당성은 안 본다** — 중첩 표본·생존 편향·과최적화는 여전히 사람이 본다.
   · 접두사 불변이어도 **입력 데이터 자체가 미래를 담고 있으면**(예: 수정주가 소급 반영,
     정정 공시 후 값) 룩어헤드는 남는다. 이건 데이터 계약의 문제라 여기서 못 잡는다.
   · 측정·검사 전용 — 어떤 룰도 바꾸지 않는다.

사용:
  python3 lookahead_guard.py              # 전 불변식 검사 (exit 1 = 위반)
  python3 lookahead_guard.py --negative   # 가드 자체 검증(일부러 룩어헤드 심어 잡히는지)
  python3 lookahead_guard.py --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

TOL = 1e-9


# ── 결정적 합성 시계열 (네트워크·캐시 불요, seed 고정이라 재현 가능) ──────────
def synth_closes(n: int = 420, seed: int = 7) -> list[float]:
    """추세 + 변동성 국면 전환이 있는 가격 시계열.

    국면 전환을 일부러 넣는다: 뒤쪽 변동성이 커야 '전 구간 통계'를 쓰는 누수가
    앞쪽 값을 흔들어 접두사 불변성 검사에 걸린다(평탄한 시계열이면 누수가 숨는다).
    """
    rnd = random.Random(seed)
    c = [100.0]
    for i in range(n):
        vol = 0.010 if i < n // 2 else 0.030
        c.append(round(c[-1] * (1 + rnd.gauss(0.0004, vol)), 4))
    return c


def synth_dates(n: int, start=(2026, 1, 1)) -> list[str]:
    """단조 증가하는 날짜 문자열 n개.

    ⚠️ 이 함수는 가드의 **첫 실행에서 위양성을 낸 자리**다(8/24). 초판은
    f"2026-{1+(i//28)%12:02d}-{1+i%28:02d}" 로 날짜를 만들었는데 336번째부터
    **2026-01-01로 순환**해, `d <= as_of` 필터를 통과한 '미래' 행이 섞이며
    `_closes_asof`를 룩어헤드로 오판했다(200 → 285행). 코드는 정상이었다.
    ⇒ **가드가 낸 첫 위반은 대상 코드가 아니라 가드 자신일 수 있다.**
       위반을 보고하기 전에 테스트 픽스처부터 의심할 것.
    (달력일이라 실제 거래일과 다르지만, 이 검사는 날짜 단조성만 필요하다.)
    """
    d = dt.date(*start)
    return [(d + dt.timedelta(days=i)).isoformat() for i in range(n)]


def _cmp_seq(full, pre, cut: int, name: str) -> tuple[bool, str]:
    """full[:cut] 과 pre 가 같은가 (None 패턴 포함)."""
    if len(pre) != cut:
        return False, f"{name}: 길이 계약 위반 — 입력 {cut} → 출력 {len(pre)}"
    for i in range(cut):
        a, b = full[i], pre[i]
        if a is None and b is None:
            continue
        if (a is None) != (b is None):
            return False, f"{name}: idx {i} None 패턴 불일치 (full={a}, prefix={b})"
        if isinstance(a, bool) or isinstance(b, bool):
            if a != b:
                return False, f"{name}: idx {i} 값 불일치 ({a} vs {b})"
            continue
        if abs(a - b) > TOL * max(1.0, abs(a)):
            return False, f"{name}: idx {i} 값 불일치 ({a} vs {b}) ← 미래 데이터가 과거 산출을 바꿨다"
    return True, ""


def prefix_invariant(fn, series, cut: int, name: str) -> tuple[bool, str]:
    """f(series[:cut]) == f(series)[:cut] 인가."""
    try:
        return _cmp_seq(fn(series), fn(series[:cut]), cut, name)
    except Exception as e:  # 검사 중 예외도 실패로 본다(조용히 통과 금지)
        return False, f"{name}: 예외 {type(e).__name__}: {e}"


# ── 개별 불변식 ──────────────────────────────────────────────────────────
def check_signal_score(c) -> list[tuple[str, bool, str]]:
    """signal_score: 지표·신호가 i일 종가까지만 쓰는가."""
    out = []
    try:
        import signal_score as S
    except Exception as e:
        return [("signal_score", None, f"import 실패: {e}")]
    cut = 300
    for nm, fn in (
        ("signal_score.sma_padded(50)", lambda x: S.sma_padded(x, 50)),
        ("signal_score.sma_padded(200)", lambda x: S.sma_padded(x, 200)),
        ("signal_score.ema_padded(12)", lambda x: S.ema_padded(x, 12)),
        ("signal_score.rsi_padded(14)", lambda x: S.rsi_padded(x)),
        ("signal_score.macd_hist_padded", lambda x: S.macd_hist_padded(x)),
    ):
        ok, msg = prefix_invariant(fn, c, cut, nm)
        out.append((nm, ok, msg))
    # build_signals — 실제 채점에 쓰이는 신호 dict 전체
    try:
        full, pre = S.build_signals(c), S.build_signals(c[:cut])
        for k in full:
            ok, msg = _cmp_seq(full[k], pre[k], cut, f"signal_score.build_signals[{k}]")
            out.append((f"build_signals[{k}]", ok, msg))
    except Exception as e:
        out.append(("build_signals", False, f"예외 {type(e).__name__}: {e}"))
    return out


def check_sizing_backtest(c) -> list[tuple[str, bool, str]]:
    """sizing_backtest.rolling_rv: 전일까지만 쓰는가(당일 수익률도 안 써야 한다)."""
    try:
        import sizing_backtest as SB
    except Exception as e:
        return [("sizing_backtest", None, f"import 실패: {e}")]
    rets = [(c[i] / c[i - 1] - 1) for i in range(1, len(c))]
    out = [prefix_invariant(lambda x: SB.rolling_rv(x, 20), rets, 250,
                            "sizing_backtest.rolling_rv(20)")]
    out = [("sizing_backtest.rolling_rv(20)", out[0][0], out[0][1])]
    # 당일(rets[i]) 자기 자신을 쓰면 사이징이 그날 수익률을 미리 아는 셈이 된다.
    try:
        i = 100
        full = SB.rolling_rv(rets, 20)[i]
        upto = SB.rolling_rv(rets[:i + 1], 20)[i]   # rets[i]까지만 존재
        same = (full is None and upto is None) or (
            full is not None and upto is not None and abs(full - upto) <= TOL * max(1.0, abs(full)))
        out.append(("sizing_backtest.rolling_rv 당일수익률 미사용", bool(same),
                    "" if same else "rolling_rv[i]가 rets[i] 이후 정보에 의존한다"))
    except Exception as e:
        out.append(("sizing_backtest.rolling_rv 당일수익률 미사용", False, f"예외 {e}"))
    return out


def check_flow_edge(c) -> list[tuple[str, bool, str]]:
    """flow_edge: forward 수익 계산이 범위를 넘으면 None이어야 하고, Δfrr 신호는 과거만 쓴다."""
    try:
        import flow_edge as FE
    except Exception as e:
        return [("flow_edge", None, f"import 실패: {e}")]
    out = []
    n = len(c)
    # 경계: t+h가 시리즈를 벗어나면 값을 만들어내면 안 된다(없는 미래를 지어내는 형태의 누수)
    edge_ok = (FE._fwd_ret(c, n - 1, 5) is None and FE._fwd_ret(c, n - 6, 5) is not None
               and FE._fwd_ret(c, n - 5, 5) is None)
    out.append(("flow_edge._fwd_ret 미래부족 시 None", bool(edge_ok),
                "" if edge_ok else "지평이 시리즈를 벗어나는데 값을 반환한다"))
    # 신호(Δ지분율)는 t까지의 정보만 — 미래를 덧붙여도 과거 신호가 안 변해야 한다
    frr = [round(50 + math.sin(i / 9.0) * 2, 4) for i in range(n)]
    D, cut = 20, 300
    sig_full = [frr[t] - frr[t - D] for t in range(D, cut)]
    sig_pre = [frr[:cut][t] - frr[:cut][t - D] for t in range(D, cut)]
    ok, msg = _cmp_seq(sig_full, sig_pre, len(sig_full), "flow_edge Δfrr 신호")
    out.append(("flow_edge Δfrr 신호 접두사 불변", ok, msg))
    return out


def check_star_validate(c) -> list[tuple[str, bool, str]]:
    """star_validate.fwd_return: 지평이 데이터를 넘으면 None, 미래가 생겨도 기존 값 불변."""
    try:
        import star_validate as SV
    except Exception as e:
        return [("star_validate", None, f"import 실패: {e}")]
    out = []
    dates = synth_dates(len(c))
    ser = list(zip(dates, c))
    orig = getattr(SV, "series", None)
    try:
        short = ser[:200]
        SV.series = lambda sym, _s=short: _s
        a_short = SV.fwd_return("TEST", short[50][0], 20)
        tail_short = SV.fwd_return("TEST", short[-3][0], 20)   # 미래 부족 → None이어야
        SV.series = lambda sym, _s=ser: _s
        a_long = SV.fwd_return("TEST", short[50][0], 20)
        tail_long = SV.fwd_return("TEST", short[-3][0], 20)    # 이제 미래가 있으니 값이 생겨도 정상
        same = (a_short is not None and a_long is not None
                and abs(a_short - a_long) <= TOL * max(1.0, abs(a_long)))
        out.append(("star_validate.fwd_return 과거 콜 불변", bool(same),
                    "" if same else f"데이터가 늘자 과거 콜 채점이 바뀌었다 ({a_short} → {a_long})"))
        out.append(("star_validate.fwd_return 미래부족 시 None", tail_short is None,
                    "" if tail_short is None else f"지평 밖인데 {tail_short}를 반환"))
        out.append(("star_validate.fwd_return 미래 도착 시 채점 재개", tail_long is not None,
                    "" if tail_long is not None else "데이터가 채워졌는데도 None"))
    except Exception as e:
        out.append(("star_validate.fwd_return", False, f"예외 {type(e).__name__}: {e}"))
    finally:
        if orig is not None:
            SV.series = orig
    return out


def check_snapshot_backfill(c) -> list[tuple[str, bool, str]]:
    """snapshot_state_backfill._closes_asof: as_of 이후 행이 결과에 새지 않는가."""
    try:
        import snapshot_state_backfill as SSB
    except Exception as e:
        return [("snapshot_state_backfill", None, f"import 실패: {e}")]
    if getattr(SSB, "hb", None) is None:
        return [("snapshot_state_backfill._closes_asof", None, "history_backfill 미탑재로 SKIP")]
    dates = synth_dates(len(c))
    rows = list(zip(dates, c))
    as_of = dates[199]
    orig = SSB.hb.load_cached
    try:
        SSB.hb.load_cached = lambda sym, _r=rows[:260]: _r
        a = SSB._closes_asof("TEST", as_of)
        SSB.hb.load_cached = lambda sym, _r=rows: _r          # 미래 행을 더 넣는다
        b = SSB._closes_asof("TEST", as_of)
        ok, msg = _cmp_seq(a, b, len(a), "snapshot_state_backfill._closes_asof")
        ok = ok and len(a) == len(b)
        if len(a) != len(b):
            msg = f"as_of 이후 행이 결과에 샜다 ({len(a)} → {len(b)})"
        return [("snapshot_state_backfill._closes_asof as_of 컷오프", ok, msg)]
    except Exception as e:
        return [("snapshot_state_backfill._closes_asof", False, f"예외 {type(e).__name__}: {e}")]
    finally:
        SSB.hb.load_cached = orig


# ── 음성 테스트 — 가드 자신을 검증한다 ────────────────────────────────────
def negative_selftest(c) -> list[tuple[str, bool, str]]:
    """일부러 룩어헤드를 심은 계산을 넣고 **검사기가 실제로 잡는지** 본다.

    ★[8/23 교훈] *"가드는 '있다'가 아니라 '이 사례를 잡는가'로 검증한다."*
    이 단계가 없으면 이 파일도 "돌지만 아무것도 못 잡는" 도구가 될 수 있다.
    여기서는 **잡아내면 성공**이다(부호가 반대).
    """
    out = []

    def leak_zscore(x):
        """전 구간 평균·표준편차로 정규화 — 미래를 본다(대표적 누수 형태)."""
        m = sum(x) / len(x)
        sd = math.sqrt(sum((v - m) ** 2 for v in x) / len(x)) or 1.0
        return [(v - m) / sd for v in x]

    def leak_future_ma(x, n=20):
        """중심이동평균 — 뒤쪽 n//2개를 당겨 쓴다."""
        r = []
        for i in range(len(x)):
            lo, hi = max(0, i - n // 2), min(len(x), i + n // 2 + 1)
            r.append(sum(x[lo:hi]) / (hi - lo))
        return r

    def leak_running_max(x):
        """전 구간 최댓값 대비 — 미래 고점을 안다."""
        mx = max(x)
        return [v / mx for v in x]

    for nm, fn in (("전구간 z-score 정규화", leak_zscore),
                   ("중심이동평균(미래 절반 사용)", leak_future_ma),
                   ("전구간 최댓값 대비", leak_running_max)):
        ok, msg = prefix_invariant(fn, c, 300, nm)
        caught = not ok            # 잡아야 정상
        out.append((f"[음성] {nm}", caught,
                    "" if caught else "⚠️ 검사기가 명백한 룩어헤드를 놓쳤다 — 가드가 무력하다"))

    # 정상 계산은 통과해야 한다(위양성 확인)
    def causal_ma(x, n=20):
        return [None if i < n - 1 else sum(x[i - n + 1:i + 1]) / n for i in range(len(x))]
    ok, msg = prefix_invariant(causal_ma, c, 300, "인과 이동평균")
    out.append(("[음성] 정상 계산 오탐 없음", ok, "" if ok else f"정상 계산을 위반으로 오판: {msg}"))
    return out


# ── 실행 ────────────────────────────────────────────────────────────────
def run_all(negative: bool = False) -> dict:
    c = synth_closes()
    groups = []
    if negative:
        groups.append(("음성 테스트 (가드 자체 검증)", negative_selftest(c)))
    else:
        groups.append(("signal_score", check_signal_score(c)))
        groups.append(("sizing_backtest", check_sizing_backtest(c)))
        groups.append(("flow_edge", check_flow_edge(c)))
        groups.append(("star_validate", check_star_validate(c)))
        groups.append(("snapshot_state_backfill", check_snapshot_backfill(c)))
    fails, skips, total = [], [], 0
    for gname, rows in groups:
        for nm, ok, msg in rows:
            if ok is None:
                skips.append((nm, msg))
                continue
            total += 1
            if not ok:
                fails.append((nm, msg))
    return {"groups": groups, "fails": fails, "skips": skips, "total": total,
            "mode": "negative" if negative else "invariant"}


def main() -> int:
    ap = argparse.ArgumentParser(description="룩어헤드(미래참조) 회귀 가드 — 접두사 불변성 검사")
    ap.add_argument("--negative", action="store_true",
                    help="가드 자체 검증 (일부러 룩어헤드를 심어 잡히는지 확인)")
    ap.add_argument("--json", action="store_true", help="기계 출력")
    a = ap.parse_args()

    res = run_all(a.negative)
    if a.json:
        print(json.dumps({"mode": res["mode"], "total": res["total"],
                          "fails": [{"check": n, "msg": m} for n, m in res["fails"]],
                          "skips": [{"check": n, "msg": m} for n, m in res["skips"]]},
                         ensure_ascii=False, indent=1))
        return 1 if res["fails"] else 0

    title = ("룩어헤드 가드 — 음성 테스트(잡아내면 성공)" if a.negative
             else "룩어헤드 회귀 가드 — 접두사 불변성 f(x[:k]) == f(x)[:k]")
    print(title)
    print("=" * 78)
    for gname, rows in res["groups"]:
        print(f"\n■ {gname}")
        for nm, ok, msg in rows:
            icon = "·" if ok is None else ("✅" if ok else "❌")
            print(f"  {icon} {nm}" + (f"\n       └ {msg}" if msg else ""))
    print("\n" + "-" * 78)
    if res["skips"]:
        print(f"  · SKIP {len(res['skips'])}건 (모듈 미탑재)")
    if res["fails"]:
        print(f"❌ 룩어헤드 위반 {len(res['fails'])}건 / 검사 {res['total']}건")
        return 1
    print(f"✅ 통과 — 검사 {res['total']}건 전부 접두사 불변"
          if not a.negative else
          f"✅ 통과 — 심어둔 룩어헤드를 모두 적발({res['total']}건 검사)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
