#!/usr/bin/env python3
"""rule_tracker.py — 개정 리스크룰의 **자기 검증** 원장 (stdlib only)

정훈 지시(2026-07-30): *"R3 캘리브레이션에 룰 추적도 배선해줘."*

■ 왜 필요한가 — 이 룰은 한 번도 검증된 적이 없다
   7/30 개정(룰1 낙폭 사다리·룰2 추세형 훼손)의 숫자들 — 사다리 배분(15/20/25/25/15),
   폭풍 승수 계단(0.4/0.6/0.8/1.0), 항복 가산 ×1.2, S&P 70%ile 플로어 — 은 **전부 그날
   PM이 정한 값**이다. 기저율에서 근거를 끌어왔지만 **캘리브레이션된 값이 아니다.**
   게다가 개정 방향이 "더 사는 쪽"(0원 → 112,975원)이라 **틀리면 손실 쪽으로 틀린다.**

■ 무엇을 채점하나 — **집행이 아니라 '룰이 낸 신호'**
   실제 매수는 안전핀·폰창·1주 제약 때문에 자주 못 한다. 그래서 집행 실적만 보면
   룰 자체를 검증할 수 없다. 이 추적기는 **반사실**을 본다:
     "그날 룰이 '상한 N원까지 사도 된다'고 했다. 그 시점에 샀다면 어떻게 됐나?"
   ⇒ 룰이 **켜진 날**과 **꺼진 날**의 이후 성과를 나눠 비교한다.

■ 채점 항목 (5개)
   ① 사다리 해금 시점 성과 — D1~D4 각 단계가 처음 켜진 날 이후 1/3/6/12개월 코스피
   ② 승수 유효성 — 폭풍 감산이 실제로 손실을 줄였나 (감산 강한 날 vs 약한 날)
   ③ 항복 가산 유효성 — ×1.2가 켜진 날이 실제로 더 좋았나 ("공포에 사라"의 검증)
   ④ 하드 플로어 — S&P 70%ile 정지가 발동했나·옳았나
   ⑤ 룰2 훼손 판정 — 3/3·2/3 판정 종목의 이후 주가(훼손 경보가 맞았나)

■ ⚠️ 규율
   · 표본이 쌓이기 전엔 **판정하지 않는다**. 최소 8주(≈40 스냅샷) 전엔 "표본 부족"만 출력.
   · 결과론 함정 — 룰이 옳았는지는 **분포**로 보지 단일 사건으로 보지 않는다.
   · **자동으로 룰을 바꾸지 않는다.** 편향이 보이면 '개정 제안'만 하고 확정은 정훈.

사용:
  python3 rule_tracker.py --snapshot     # 오늘 룰 상태를 원장에 append (매 보고서/R3)
  python3 rule_tracker.py --score        # 누적 원장 후행검증 (R3 주간)
  python3 rule_tracker.py --history      # 원장 요약
"""
from __future__ import annotations

import argparse
import bisect
import datetime as dt
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
LOG = os.path.join(ROOT, "data", "app", "rule_log.jsonl")

KOSPI = "^KS11"
MIN_SNAPSHOTS = 40          # 이 아래면 판정 보류(≈8주)
MIN_EPISODES = 5            # 독립 국면 최소치 — 표본 n이 커도 국면이 적으면 판정 불가
HORIZONS = [(21, "1개월"), (63, "3개월"), (126, "6개월"), (252, "12개월")]


# ─────────────────────────────────────────── 스냅샷

def snapshot(save=True) -> dict:
    """오늘의 룰 상태를 기록. 매 보고서·R3에서 호출."""
    import tranche_rules as TR

    cash, dd, storm, fear, capit = TR._load_inputs(None)
    if dd is None:
        return {"error": "코스피 낙폭 산출 실패 — history_backfill.py 필요"}

    r1 = TR.rule1(cash, dd, storm, fear, capit)

    # 룰2는 보유 전종목 판정을 요약 저장
    r2 = {}
    fp = os.path.join(ROOT, "data", "app", "financials.json")
    if os.path.exists(fp):
        try:
            with open(fp, encoding="utf-8") as f:
                for t in (json.load(f).get("stocks") or {}):
                    v = TR.rule2(t)
                    if not v.get("error"):
                        r2[t] = v["score"]
        except Exception:
            pass

    # 코스피 종가(당일)
    kospi = None
    try:
        import drawdown_history as D
        _, closes = D.load(KOSPI)
        kospi = closes[-1] if closes else None
    except Exception:
        pass

    rec = {
        "date": dt.date.today().isoformat(),
        "kospi": kospi,
        "dd_pct": round(dd, 2),
        "unlocked_ratio": r1["unlocked_ratio"],
        "steps_unlocked": [i + 1 for i, s in enumerate(r1["steps"]) if s["unlocked"]],
        "storm_pct": storm,
        "storm_mult": r1["storm_mult"],
        "capitulation": r1["capitulation"],
        "fear_pct": fear, "capit_pct": capit,
        "final_mult": r1["final_mult"],
        "halted": r1["halted"],
        "allowed_krw": r1["allowed_krw"],
        "cash": cash,
        "rule2": r2,
    }
    if save:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        # 같은 날 재실행이면 덮어쓴다(중복 표본 방지 — 기저율 표본중복 교훈)
        rows = [x for x in _read() if x.get("date") != rec["date"]]
        rows.append(rec)
        with open(LOG, "w", encoding="utf-8") as f:
            for x in sorted(rows, key=lambda r: r["date"]):
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
    return rec


def _read() -> list[dict]:
    if not os.path.exists(LOG):
        return []
    out = []
    with open(LOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


# ─────────────────────────────────────────── 소급 재구성 (백테스트)

# 풀링 대상 — 룰1 입력(낙폭·폭풍%ile)은 **지수 가격의 순수 함수**라 어느 지수에도 그대로 적용된다.
# 코스피 단독으로는 D2~D4 구간의 강한-감산 표본이 15개 미만이라 판정이 불가능했다(7/30 1회차).
# 서로 다른 시장의 크래시는 코스피 인접일보다 훨씬 독립적이므로, 시장을 늘리는 게 정당한 증량이다.
POOL = [
    ("^KS11", "코스피"), ("^KQ11", "코스닥"), ("^GSPC", "S&P500"), ("^IXIC", "나스닥"),
    ("^DJI", "다우"), ("^RUT", "러셀2000"), ("^SOX", "필라델피아반도체"),
    ("^N225", "니케이225"), ("^HSI", "항셍"), ("000001.SS", "상해종합"),
    ("^STOXX50E", "유로스톡스50"),
]


def backfill(years: float = 29, step: int = 5, symbol: str = KOSPI,
             label: str | None = None) -> list[dict]:
    """과거 일봉으로 **룰이 그날 뭐라고 했을지**를 재구성한다.

    왜 필요한가: 실시간 스냅샷만 쌓으면 첫 판정까지 8주가 걸린다. 그런데 룰1의 입력
    (낙폭·폭풍 %ile)은 **가격의 순수 함수**라 과거 전 구간을 그대로 재계산할 수 있다.

    ⚠️ 한계 — 실시간 스냅샷과 **같은 것이 아니다**:
      · 심리(공포·항복 %ile)는 네이버 트렌드가 2025년부터라 과거엔 없다 → **항복 가산 OFF로 가정**.
      · S&P 하드 플로어도 재계산 비용이 커 생략 → 정지 미적용(공격적 가정).
      · 표본이 시계열로 겹친다 → **에피소드 클러스터링**으로 독립 표본 수를 병기한다.
    ⇒ 결과는 **방향 감각용**이며, 실시간 원장(--snapshot)이 정본이다.
    """
    import drawdown_history as D
    dates, closes = D.load(symbol)
    if not closes:
        return []

    dd_series, m = [], closes[0]
    for c in closes:
        m = max(m, c)
        dd_series.append((c / m - 1) * 100)

    import math
    rets = [0.0] + [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    rv = [None] * len(closes)
    for i in range(20, len(closes)):
        w = rets[i - 19:i + 1]
        mu = sum(w) / len(w)
        var = sum((x - mu) ** 2 for x in w) / (len(w) - 1)
        rv[i] = math.sqrt(var * 252) * 100

    cutoff = (dt.date.today() - dt.timedelta(days=int(years * 365.25))).isoformat()
    import tranche_rules as TR
    out = []
    for i in range(272, len(closes), step):
        if dates[i] < cutoff or rv[i] is None:
            continue
        hist = [x for x in rv[i - 252:i] if x is not None]
        if len(hist) < 100:
            continue
        storm = sum(1 for x in hist if x <= rv[i]) / len(hist) * 100
        r1 = TR.rule1(1.0, dd_series[i], storm, None, None, check_contagion=False)
        out.append({
            "date": dates[i], "symbol": symbol, "market": label or symbol,
            "kospi": closes[i], "dd_pct": round(dd_series[i], 2),
            "unlocked_ratio": r1["unlocked_ratio"],
            "steps_unlocked": [k + 1 for k, s_ in enumerate(r1["steps"]) if s_["unlocked"]],
            "storm_pct": round(storm, 1), "storm_mult": r1["storm_mult"],
            "capitulation": False, "fear_pct": None, "capit_pct": None,
            "final_mult": r1["final_mult"], "halted": False,
            "allowed_krw": 0, "cash": 0, "rule2": {}, "_backfill": True,
        })
    return out


def backfill_multi(years: float = 40, step: int = 5, verbose: bool = True) -> list[dict]:
    """11개 주요 지수 풀링 — D2~D4 표본 증량의 정당한 방법."""
    out, per = [], []
    for sym, lbl in POOL:
        r = backfill(years, step, sym, lbl)
        if r:
            out.extend(r)
            per.append((lbl, len(r)))
    if verbose:
        print(f"\n  풀링 {len(per)}개 지수 → {len(out)}개 표본")
        for lbl, n in per:
            print(f"    · {lbl:<16}{n:>6}")
    return sorted(out, key=lambda r: (r["market"], r["date"]))


def episodes(rows: list[dict], gap_days: int = 63) -> int:
    """**독립 표본 수** — 인접일은 같은 국면이므로 하나로 센다.

    같은 시장에서 날짜 간격이 gap_days(≈3개월) 이하로 이어지면 한 에피소드.
    표본 n이 아무리 커도 에피소드가 3개면 그건 사건 3개다 — 이걸 숨기면 안 된다.
    """
    by_mkt = {}
    for r in rows:
        by_mkt.setdefault(r.get("market", "?"), []).append(r["date"])
    total = 0
    for _, ds in by_mkt.items():
        ds = sorted(ds)
        total += 1
        for a, b in zip(ds, ds[1:]):
            da = dt.date.fromisoformat(a)
            db = dt.date.fromisoformat(b)
            if (db - da).days > gap_days:
                total += 1
    return total


# ─────────────────────────────────────────── 후행 검증

def _fwd(dates, closes, date_str, h):
    """date_str 이후 h거래일 수익률(%). 미래가 부족하면 None."""
    i = bisect.bisect_left(dates, date_str)
    if i >= len(dates) or i + h >= len(closes):
        return None
    return (closes[i + h] / closes[i] - 1) * 100


def _price_cache(rows):
    """시장별 가격 시계열 — **표본이 나온 시장으로 채점해야 한다.**
    (풀링 후에도 코스피로만 채점하면 다른 시장 표본이 통째로 무의미해진다.)"""
    import drawdown_history as D
    cache = {}
    for sym in {r.get("symbol") or KOSPI for r in rows}:
        cache[sym] = D.load(sym)
    return cache


def _fwd_row(cache, r, h):
    dates, closes = cache.get(r.get("symbol") or KOSPI, ([], []))
    if not closes:
        return None
    return _fwd(dates, closes, r["date"], h)


def score(rows: list[dict]):
    cache = _price_cache(rows)
    if not any(c[1] for c in cache.values()):
        print("  ⚠️ 가격 캐시 없음 — history_backfill.py 필요")
        return

    mkts = sorted({r.get("market", "코스피") for r in rows})
    print(f"\n{'='*78}")
    print("  개정 리스크룰 자기검증 (rule_tracker)")
    print(f"{'='*78}")
    # ⚠️ 전체 표본의 에피소드 수는 의미가 없다 — 시장별로 날짜가 연속이라 '시장 수'로 수렴한다.
    #    의미 있는 건 **각 비교 그룹(단계·버킷)의 국면 수**다(아래 표 '국면' 열).
    print(f"  표본 {len(rows)}개 · {rows[0]['date']} ~ {rows[-1]['date']}")
    print("  ※ '국면' 열 = 그룹별 독립 에피소드 수(같은 시장 내 3개월 이상 끊기면 별개). 표본 n보다 이쪽이 정직한 크기다.")
    print(f"  시장 {len(mkts)}개: {', '.join(mkts)}")

    if len(rows) < MIN_SNAPSHOTS:
        print(f"\n  ⏳ **판정 보류** — 표본 {len(rows)}개 < 최소 {MIN_SNAPSHOTS}개(≈8주).")
        print("     지금 채점하면 단일 국면의 노이즈를 룰의 성질로 오인한다.")
        print("     매 보고서·R3에서 --snapshot을 계속 쌓을 것.\n")
        _quick_state(rows[-1])
        return

    # ① 사다리 단계별 해금 시점 성과
    print("\n  ① 사다리 해금 시점 이후 성과 (룰이 '사도 된다'고 한 날들)")
    by_step = {}
    for r in rows:
        by_step.setdefault(max(r["steps_unlocked"]) if r["steps_unlocked"] else 0, []).append(r)
    print(f"     {'단계':<9}{'표본':>7}{'국면':>6}" + "".join(f"{lbl:>10}" for _, lbl in HORIZONS))
    for k in sorted(by_step):
        rs = by_step[k]
        line = f"     {('D'+str(k)+'까지') if k else '해금없음':<9}{len(rs):>7}{episodes(rs):>6}"
        for h, _ in HORIZONS:
            vals = [v for v in (_fwd_row(cache, r, h) for r in rs) if v is not None]
            line += f"{statistics.median(vals):>+9.1f}%" if vals else f"{'—':>10}"
        print(line)

    # ② 폭풍 감산 유효성
    print("\n  ② 폭풍 감산 — 감산이 강했던 날이 실제로 나빴나(=감산이 옳았나)")
    _bucket(rows, cache, lambda r: ("강한 감산(≤0.6)" if (r["storm_mult"] or 1) <= 0.6
                                    else "약한 감산(>0.6)"))
    # ⚠️ 단순 비교는 **교란변수**가 있다 — 폭풍이 강한 날은 대체로 낙폭도 깊고,
    #    낙폭이 깊을수록 이후 성과가 좋다(①). ⇒ 같은 단계 안에서만 비교해야 순효과가 보인다.
    print("\n  ②b 폭풍 감산 — **낙폭 단계를 통제한 층화 비교**(교란 제거)")
    print(f"     {'단계':<7}{'폭풍':<15}{'표본':>7}{'국면':>6}" + "".join(f"{lbl:>10}" for _, lbl in HORIZONS))
    verdicts = []
    for k in sorted(by_step):
        got = {}
        for label, pred in (("강한 감산(≤0.6)", lambda r: (r["storm_mult"] or 1) <= 0.6),
                            ("약한 감산(>0.6)", lambda r: (r["storm_mult"] or 1) > 0.6)):
            rs = [r for r in by_step[k] if pred(r)]
            ep = episodes(rs) if rs else 0
            if len(rs) < 15 or ep < MIN_EPISODES:
                if rs:
                    print(f"     {('D'+str(k)) if k else '없음':<7}{label:<15}{len(rs):>7}{ep:>6}"
                          f"   ⏳ 표본/국면 부족(최소 15표본·{MIN_EPISODES}국면)")
                continue
            line = f"     {('D'+str(k)) if k else '없음':<7}{label:<15}{len(rs):>7}{ep:>6}"
            med = {}
            for h, _ in HORIZONS:
                vals = [v for v in (_fwd_row(cache, r, h) for r in rs) if v is not None]
                med[h] = statistics.median(vals) if vals else None
                line += f"{med[h]:>+9.1f}%" if med[h] is not None else f"{'—':>10}"
            print(line)
            got[label] = med
        if len(got) == 2:
            a = got["강한 감산(≤0.6)"].get(252)
            b = got["약한 감산(>0.6)"].get(252)
            if a is not None and b is not None:
                verdicts.append((k, a, b))
    if verdicts:
        print("\n     [12개월 순효과 판정 — 강한 감산이 더 좋으면 감산은 역효과]")
        for k, a, b in verdicts:
            tag = "🔴 역효과" if a > b else "🟢 감산 유효"
            print(f"       D{k}: 강한 {a:+.1f}% vs 약한 {b:+.1f}%  (차 {a-b:+.1f}%p) → {tag}")
    else:
        print("\n     ⏳ 모든 단계에서 표본/국면 부족 — 폭풍 감산 순효과 판정 불가.")

    # ③ 항복 가산
    print("\n  ③ 항복 가산(×1.2) — 켜진 날이 실제로 더 좋았나")
    _bucket(rows, cache, lambda r: "항복 ON" if r["capitulation"] else "항복 OFF")

    # ④ 하드 플로어
    n_halt = sum(1 for r in rows if r["halted"])
    print(f"\n  ④ 하드 플로어(S&P 폭풍 ≥70%ile) — 발동 {n_halt}/{len(rows)}회")
    if n_halt:
        _bucket(rows, cache, lambda r: "정지 ON" if r["halted"] else "정지 OFF")
    else:
        print("     미발동/미적용 — 발동 표본이 없어 유효성 판정 불가.")

    # ⑤ 룰2
    print("\n  ⑤ 룰2 훼손 판정 종목의 이후 성과 (경보가 맞았나)")
    _rule2_score(rows, __import__("drawdown_history"))

    print("\n  ⚠️ 결과론 함정 주의 — 룰의 옳고그름은 분포로 본다. 자동 변경 ❌(확정은 정훈).\n")


def _bucket(rows, cache, keyfn):
    groups = {}
    for r in rows:
        groups.setdefault(keyfn(r), []).append(r)
    print(f"     {'구간':<16}{'표본':>7}{'국면':>6}" + "".join(f"{lbl:>10}" for _, lbl in HORIZONS))
    for k in sorted(groups):
        rs = groups[k]
        line = f"     {k:<16}{len(rs):>7}{episodes(rs):>6}"
        for h, _ in HORIZONS:
            vals = [v for v in (_fwd_row(cache, r, h) for r in rs) if v is not None]
            line += f"{statistics.median(vals):>+9.1f}%" if vals else f"{'—':>10}"
        print(line)


def _rule2_score(rows, D):
    """3/3·2/3 판정이 처음 뜬 종목의 그 이후 주가 — 훼손 경보의 적중 여부."""
    first_flag = {}
    for r in rows:
        for t, sc in (r.get("rule2") or {}).items():
            if sc.startswith(("3/3", "2/3", "1/1")) and t not in first_flag:
                first_flag[t] = (r["date"], sc)
    if not first_flag:
        print("     훼손 판정 이력 없음.")
        return
    print(f"     {'종목':<12}{'최초판정':<12}{'등급':<10}" + "".join(f"{lbl:>10}" for _, lbl in HORIZONS))
    for t, (d0, sc) in sorted(first_flag.items()):
        ds, cs = D.load(t)
        if not cs:
            continue
        line = f"     {t:<12}{d0:<12}{sc:<10}"
        for h, _ in HORIZONS:
            v = _fwd(ds, cs, d0, h)
            line += f"{v:>+9.1f}%" if v is not None else f"{'—':>10}"
        print(line)
    print("     ↳ 훼손 경보가 옳았다면 **이후 수익률이 음(-)**이어야 한다.")


def _quick_state(r):
    print("  [최신 스냅샷]")
    print(f"    코스피 {r.get('kospi') or 0:,.0f} · 낙폭 {r['dd_pct']:+.1f}% "
          f"· 해금 D{r['steps_unlocked']}({r['unlocked_ratio']*100:.0f}%)")
    print(f"    폭풍 {r.get('storm_pct')}%ile ×{r['storm_mult']} · 항복 "
          f"{'ON' if r['capitulation'] else 'OFF'} → 승수 ×{r['final_mult']}")
    print(f"    허용 상한 {r['allowed_krw']:,}원 " + ("(🔴 하드 플로어 정지)" if r["halted"] else ""))
    flags = {t: s for t, s in (r.get("rule2") or {}).items() if not s.startswith("0/")}
    if flags:
        print(f"    룰2 플래그: {', '.join(f'{t} {s}' for t, s in flags.items())}")
    print()


def main():
    ap = argparse.ArgumentParser(description="개정 리스크룰 자기검증 원장")
    ap.add_argument("--snapshot", action="store_true", help="오늘 룰 상태 append")
    ap.add_argument("--score", action="store_true", help="누적 원장 후행검증(R3)")
    ap.add_argument("--history", action="store_true", help="원장 요약")
    ap.add_argument("--backfill", action="store_true",
                    help="과거 일봉으로 룰 소급 재구성 후 검증(코스피 단독)")
    ap.add_argument("--multi", action="store_true",
                    help="11개 주요 지수 풀링 백테스트 — D2~D4 표본 증량")
    ap.add_argument("--years", type=float, default=29)
    ap.add_argument("--step", type=int, default=5, help="표본 간격(거래일) — 표본중복 완화")
    a = ap.parse_args()

    if a.snapshot:
        r = snapshot()
        if r.get("error"):
            sys.exit(f"[rule_tracker] {r['error']}")
        print(f"\n📌 룰 스냅샷 기록 — {r['date']}")
        _quick_state(r)
        print(f"💾 {os.path.relpath(LOG, ROOT)} ({len(_read())}개 누적)\n")
        return

    if a.multi:
        rows = backfill_multi(a.years, a.step)
        if not rows:
            sys.exit("[rule_tracker] 멀티 백필 실패")
        print("   ⚠️ 항복 가산 OFF 가정·하드 플로어 미적용 — 방향 감각용. 실시간 원장이 정본.")
        score(rows)
        return

    if a.backfill:
        rows = backfill(a.years, a.step)
        if not rows:
            sys.exit("[rule_tracker] 백필 실패 — history_backfill.py 필요")
        print(f"\n🔁 소급 재구성 {len(rows)}개 표본 ({rows[0]['date']} ~ {rows[-1]['date']}, {a.step}일 간격)")
        print("   ⚠️ 항복 가산 OFF 가정(심리 데이터 과거 부재)·하드 플로어 미적용 — 방향 감각용")
        score(rows)
        return

    rows = _read()
    if not rows:
        sys.exit("[rule_tracker] 원장 비어있음 — --snapshot 먼저 실행")

    if a.history:
        print(f"\n원장 {len(rows)}개 — {rows[0]['date']} ~ {rows[-1]['date']}")
        print(f"  {'날짜':<12}{'코스피':>9}{'낙폭':>8}{'해금':>7}{'승수':>7}{'허용액':>11}")
        for r in rows[-20:]:
            print(f"  {r['date']:<12}{(r.get('kospi') or 0):>9,.0f}{r['dd_pct']:>7.1f}%"
                  f"{r['unlocked_ratio']*100:>6.0f}%{r['final_mult']:>7.2f}{r['allowed_krw']:>11,}")
        print()
        return

    score(rows)


if __name__ == "__main__":
    main()
