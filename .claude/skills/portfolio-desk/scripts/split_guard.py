#!/usr/bin/env python3
"""split_guard.py — 주식분할 스케일 혼재 가드 (stdlib only)

■ 왜 필요한가 [8/24 — 데이터 미래참조 감사에서 발견, roadmap 2-1b]

   `financials.eps_yoy`가 CANSLIM **C축·A축** 점수 → 펀더 서브스코어 → **별점의 정량 근거**로
   들어간다. 그런데 **EDGAR는 분할 후 과거 EPS를 소급 조정해 재보고**하되, 후속 보고서의
   비교 컬럼에 실린 분기만 다시 신고한다 — 재보고는 약 1년 뒤에 온다.
   ⇒ **분할 직후 ~1년간은 최근 분기(조정본)와 4분기 전(미조정 원본)이 섞일 수 있고**,
     그러면 yoy가 **분할 비율만큼(최대 10배) 왜곡**된다. `shares_yoy`도 같이 망가져
     **가짜 희석 경보**(`dilution` 플래그)가 뜬다.
   같은 원인의 실제 버그를 `multiple_backtest`에서 발견·수정했다(NVDA 24분기 중 6개가 4~10배 과소).

■ 판정 원리 — 크기로 추측하지 않고 **항등식으로 검산한다**

   EPS = 순이익 / 주식수 이므로, 세 성장률 사이에 항등식이 성립한다:

       (1 + eps_yoy)  ==  (1 + ni_yoy) / (1 + shares_yoy)

   스케일이 섞이면 이 항등식이 **분할 비율만큼 깨진다**. 자기 데이터만 쓰므로
   **네트워크·`filed` 불필요하고 국내주에도 적용**된다.
   실측(8/24 보유·워치 전 종목 174건): **169건(97.1%) 성립** — 검사기로 충분히 정밀하다.

■ ⚠️ 오탐 억제가 이 가드의 본체다

   이격이 크다고 전부 분할이 아니다. 8/24 실측에서 걸린 5건은 **전부 분할이 아니었다**:
     · 두산로보 1.25배 — **적자**(비율 계산 자체가 불안정)
     · STM 0.18배 — EPS 0.04의 **반올림 오차**(유효숫자 1자리)
     · 한화오션 1.92배 · SK이노 2.86배 — **유상증자·합병 신주**
       (EPS 분모는 **가중평균** 주식수인데 `shares_diluted`는 기말 시점이라 구조적으로 어긋난다)
     · 현대차 0.77배 — 주식수 변동(자사주)
   ⇒ 그래서 `split_scale_mix`(high)로 올리려면 **두 조건을 동시에** 요구한다:
     ① 이격이 **정수 분할 비율에 근접** ② 그 구간에 **실제 분할 이벤트가 존재**.
     둘 중 하나만이면 `yoy_identity_gap`(low·정보성)으로만 남긴다.
   *8/24 교훈: "크기가 이상한 건 가설이지 판정이 아니다 — 경계를 특정해 대조해야 판정이 된다."*

■ 조치
   · 경보만 한다. **자동 보정하지 않는다** — 정확한 보정엔 `filed` 기반 스케일이 필요하고
     그건 US(EDGAR)만 가능하다. 대신 의심 값은 채점에서 **제외**한다(0으로 채우지 않는다 —
     8/22 *"미측정 축은 분모에서 제외"*).
   · 룰·별점 밴드는 건드리지 않는다.

사용:
  python3 split_guard.py                 # financials.json 전수 검사
  python3 split_guard.py --ticker NVDA
  python3 split_guard.py --no-network    # 분할 이벤트 조회 없이 항등식만
  python3 split_guard.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
FIN = os.path.join(REPO, "data", "app", "financials.json")

IDENT_TOL = 0.15          # 항등식 이격 허용치(±15%)
MIN_EPS_ABS = 0.10        # 이보다 작은 EPS는 반올림 오차가 지배 → 판정 보류
SPLIT_RATIOS = (1.5, 2, 3, 4, 5, 6, 7, 8, 10, 15, 20, 25, 30, 40, 50, 100)
UA = "Mozilla/5.0 (compatible; jeonghoon-desk/1.0)"
_SPLIT_CACHE: dict[str, list] = {}


# ── 항등식 ──────────────────────────────────────────────────────────────
def identity_gap(row: dict) -> float | None:
    """(1+eps_yoy) ÷ [(1+ni_yoy)/(1+sh_yoy)]. 1.0이면 정합, 벗어나면 이격 배수."""
    e, n, s = row.get("eps_yoy"), row.get("net_income_yoy"), row.get("shares_yoy")
    if e is None or n is None or s is None:
        return None
    lhs = 1 + e / 100.0
    den = 1 + s / 100.0
    if den == 0:
        return None
    rhs = (1 + n / 100.0) / den
    if lhs <= 0 or rhs <= 0:      # 적자 전환 등 부호가 뒤집히면 비율이 무의미
        return None
    return lhs / rhs


def near_split_ratio(gap: float, tol: float = 0.08) -> float | None:
    """이격이 분할 비율(또는 그 역수)에 근접하면 그 비율을 돌려준다."""
    if gap is None or gap <= 0:
        return None
    for r in SPLIT_RATIOS:
        if abs(gap - r) / r <= tol:
            return r
        if abs(gap - 1.0 / r) * r <= tol:
            return 1.0 / r
    return None


# ── 분할 이벤트 (선택적·네트워크) ────────────────────────────────────────
def splits(ticker: str, timeout: float = 15.0) -> list[tuple[str, float]]:
    """Yahoo chart events=split → [(YYYY-MM-DD, ratio)]. 실패하면 빈 리스트(가드는 계속 돈다)."""
    if ticker in _SPLIT_CACHE:
        return _SPLIT_CACHE[ticker]
    import datetime as dt
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(ticker) + "?interval=1mo&range=40y&events=split")
    out: list[tuple[str, float]] = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode())
        ev = ((d["chart"]["result"][0].get("events") or {}).get("splits") or {})
        for v in ev.values():
            num, den = v.get("numerator"), v.get("denominator")
            if not num or not den:
                continue
            day = dt.datetime.utcfromtimestamp(v["date"]).strftime("%Y-%m-%d")
            out.append((day, float(num) / float(den)))
        out.sort()
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError, ValueError,
            TimeoutError, OSError):
        out = []
    _SPLIT_CACHE[ticker] = out
    return out


def split_between(ticker: str, start: str, end: str, use_network: bool = True) -> list[tuple[str, float]]:
    """[start, end+1년] 구간의 분할. 재보고 지연(~1년)을 감안해 뒤쪽을 넉넉히 잡는다."""
    if not use_network:
        return []
    try:
        end_pad = str(int(end[:4]) + 1) + end[4:]
    except (ValueError, IndexError):
        end_pad = end
    return [(d, r) for d, r in splits(ticker) if start <= d <= end_pad]


# ── 감사 ────────────────────────────────────────────────────────────────
def audit_rows(ticker: str, rows: list[dict], period: str,
               use_network: bool = True) -> list[dict]:
    """한 종목의 기간 시계열을 검사해 플래그 목록을 낸다."""
    out = []
    ends = [r.get("end") for r in rows if r.get("end")]
    lag = 4 if period == "quarterly" else 1
    for i, r in enumerate(rows):
        gap = identity_gap(r)
        if gap is None:
            continue
        if abs(gap - 1.0) <= IDENT_TOL:
            continue
        base_end = ends[i + lag] if i + lag < len(ends) else None
        base_row = rows[i + lag] if i + lag < len(rows) else None
        eps = r.get("eps_diluted")
        base_eps = (base_row or {}).get("eps_diluted")
        # 반올림 지배 구간은 판정 보류. **비교 대상(4분기 전)의 EPS가 작아도** 마찬가지다 —
        # 이격은 두 값의 비율에서 나오므로 어느 쪽이든 작으면 오차가 지배한다(STM 실측).
        # 적자 구간은 비율 자체가 무의미하다(부호 전환이면 yoy가 -318%처럼 튄다).
        # STM 2026-06-30이 그 사례 — 기준기 EPS가 -0.11이라 항등식이 성립할 수 없었다.
        neg = [lab for lab, v in (("당기 EPS", eps), ("기준기 EPS", base_eps),
                                  ("당기 순이익", r.get("net_income")),
                                  ("기준기 순이익", (base_row or {}).get("net_income")))
               if v is not None and v < 0]
        if neg:
            out.append({"end": r["end"], "period": period, "gap": round(gap, 3),
                        "level": "info", "kind": "loss_period",
                        "msg": f"{' · '.join(neg)} 음수 — 적자·흑전 구간이라 비율 판정 보류"})
            continue
        small = [f"{lab} |{v}|" for lab, v in (("당기", eps), ("기준기", base_eps))
                 if v is not None and abs(v) < MIN_EPS_ABS]
        if small:
            out.append({"end": r["end"], "period": period, "gap": round(gap, 3),
                        "level": "info", "kind": "rounding_noise",
                        "msg": f"{' · '.join(small)} < {MIN_EPS_ABS} — 반올림 오차 지배, 판정 보류"})
            continue
        ratio = near_split_ratio(gap)
        ev = split_between(ticker, base_end or r["end"], r["end"], use_network) if base_end else []
        if ratio and ev:
            out.append({
                "end": r["end"], "period": period, "gap": round(gap, 3),
                "level": "high", "kind": "split_scale_mix",
                "splits": ev,
                "msg": (f"이격 {gap:.2f}배가 분할비율 {ratio}에 근접하고 구간에 실제 분할"
                        f"({', '.join(f'{d} {x}:1' for d, x in ev)}) — EPS 스케일 혼재 의심. "
                        f"eps_yoy·shares_yoy를 채점에서 제외할 것"),
            })
        else:
            why = []
            sy = r.get("shares_yoy")
            if sy is not None and abs(sy) > 10:
                why.append(f"주식수 {sy:+.1f}%(증자·자사주 — EPS 분모는 가중평균이라 구조적 이격)")
            if not ratio:
                why.append("이격이 분할비율과 무관")
            elif not ev:
                why.append("구간에 분할 이벤트 없음")
            out.append({"end": r["end"], "period": period, "gap": round(gap, 3),
                        "level": "low", "kind": "yoy_identity_gap",
                        "msg": "항등식 이격 — " + " · ".join(why or ["원인 미상"])})
    return out


def audit_all(path: str = FIN, only: str | None = None,
              use_network: bool = True) -> dict:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    st = d.get("stocks") or d
    res, n_rows = {}, 0
    for tk, rec in st.items():
        if only and tk.upper() != only.upper():
            continue
        if not isinstance(rec, dict):
            continue
        flags = []
        for per in ("quarterly", "annual"):
            rows = rec.get(per) or []
            n_rows += len(rows)
            flags += audit_rows(tk, rows, per, use_network)
        if flags:
            res[tk] = flags
    return {"checked_rows": n_rows, "flagged": res,
            "high": sum(1 for v in res.values() for x in v if x["level"] == "high"),
            "low": sum(1 for v in res.values() for x in v if x["level"] == "low"),
            "info": sum(1 for v in res.values() for x in v if x["level"] == "info")}


def selftest() -> int:
    """음성 테스트 — 일부러 스케일 혼재를 심어 **가드가 잡는지** 본다.

    ★[8/23·8/24 교훈] *"가드는 '있다'가 아니라 '이 사례를 잡는가'로 검증한다."*
    이 단계가 없으면 이 파일도 "돌지만 아무것도 못 잡는" 도구가 된다.
    """
    print("split_guard 음성 테스트 — 심어둔 스케일 혼재를 잡아내면 성공")
    print("=" * 78)
    ok = True

    # 정상 시계열: 순이익 +50%, 주식수 -1% → EPS +51.5%
    def mk(end, eps, ni_yoy, sh_yoy, eps_yoy):
        return {"end": end, "eps_diluted": eps, "net_income_yoy": ni_yoy,
                "shares_yoy": sh_yoy, "eps_yoy": eps_yoy}

    clean = [mk("2024-10-27", 2.40, 50.0, -1.0, 51.5), mk("2023-10-29", 1.58, 20.0, 0.0, 20.0),
             mk("2023-07-30", 1.40, 15.0, 0.0, 15.0), mk("2023-04-30", 1.30, 10.0, 0.0, 10.0),
             mk("2022-10-30", 1.20, 5.0, 0.0, 5.0)]
    r1 = audit_rows("TEST", clean, "quarterly", use_network=False)
    hi1 = [x for x in r1 if x["level"] == "high"]
    print(f"  {'✅' if not hi1 else '❌'} 정상 시계열 오탐 없음"
          + ("" if not hi1 else f" — {hi1}"))
    ok = ok and not hi1

    # 혼재 주입: 당기 EPS만 10:1 조정본이라 eps_yoy가 10배 부풀려진 상태
    #   (순이익·주식수는 분할과 무관하므로 그대로 → 항등식이 정확히 10배 깨진다)
    dirty = [dict(x) for x in clean]
    dirty[0]["eps_yoy"] = (1 + 51.5 / 100) * 10 * 100 - 100      # ×10 왜곡
    r2 = audit_rows("NVDA", dirty, "quarterly", use_network=True)   # NVDA는 2024-06 실제 분할
    hi2 = [x for x in r2 if x["kind"] == "split_scale_mix"]
    caught = bool(hi2)
    print(f"  {'✅' if caught else '❌'} 10배 스케일 혼재 적발"
          + (f" — 이격 {hi2[0]['gap']}배" if caught else " ← 가드가 무력하다"))
    ok = ok and caught

    # 분할이 없는 종목이면 같은 왜곡도 high로 올리지 않는다(경계 대조 규율)
    r3 = audit_rows("MSFT", dirty, "quarterly", use_network=True)   # MSFT는 2003년 이후 분할 없음
    hi3 = [x for x in r3 if x["kind"] == "split_scale_mix"]
    print(f"  {'✅' if not hi3 else '❌'} 분할 없는 종목엔 high 미부여(크기만으로 단정하지 않음)")
    ok = ok and not hi3

    # 오프라인 경로(= validate_report가 쓰는 조건) — 분할 이벤트 조회 없이도 표면화되는가.
    #   high는 이벤트 확인이 필요해 오프라인에선 구조적으로 못 뜬다 → validate는 조건을 낮춰
    #   "이격이 분할비율에 근접"만으로 WARN을 낸다. 그 경로가 실제로 잡는지 여기서 고정한다.
    r4 = audit_rows("OFFLINE", dirty, "quarterly", use_network=False)
    surfaced = [x for x in r4
                if x["level"] == "high"
                or (x["kind"] == "yoy_identity_gap" and near_split_ratio(x["gap"]))]
    print(f"  {'✅' if surfaced else '❌'} 오프라인(validate 조건)에서도 표면화"
          + (f" — 이격 {surfaced[0]['gap']}배 → 분할비율 {near_split_ratio(surfaced[0]['gap'])} 근접"
             if surfaced else " ← 게이트가 조용히 아무것도 안 잡는다"))
    ok = ok and bool(surfaced)

    print("-" * 78)
    print("✅ 통과 — 가드가 실제로 작동한다" if ok else "❌ 실패 — 가드를 고칠 것")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="주식분할 스케일 혼재 가드 — EPS 항등식 검산")
    ap.add_argument("--ticker", help="한 종목만")
    ap.add_argument("--no-network", action="store_true",
                    help="분할 이벤트 조회 없이 항등식만(오프라인)")
    ap.add_argument("--selftest", action="store_true",
                    help="음성 테스트 — 일부러 스케일 혼재를 심어 잡히는지 확인")
    ap.add_argument("--json", action="store_true", help="기계 출력")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if not os.path.exists(FIN):
        print(f"[split_guard] {FIN} 없음 — financials.py를 먼저 돌릴 것")
        return 0
    r = audit_all(only=a.ticker, use_network=not a.no_network)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 1 if r["high"] else 0

    print("주식분할 스케일 혼재 가드 — (1+eps_yoy) == (1+ni_yoy)/(1+shares_yoy)")
    print("=" * 84)
    if not r["flagged"]:
        print(f"✅ 이격 없음 — {r['checked_rows']}행 전부 항등식 정합")
        return 0
    for tk, flags in sorted(r["flagged"].items()):
        for x in flags:
            icon = {"high": "🔴", "low": "·", "info": "·"}[x["level"]]
            print(f"  {icon} {tk:<11}[{x['period'][:4]}] {x['end']}  이격 {x['gap']}배  {x['kind']}")
            print(f"       └ {x['msg']}")
    print("-" * 84)
    print(f"  검사 {r['checked_rows']}행 · 🔴 스케일혼재 {r['high']} · 정보성 이격 {r['low']} · 보류 {r['info']}")
    if r["high"]:
        print("  ⚠️ 🔴은 eps_yoy·shares_yoy가 왜곡됐을 수 있다 — C축·A축 채점과 dilution 플래그에서 제외할 것")
        return 1
    print("  ✅ 스케일 혼재 없음 (정보성 이격은 적자·증자·반올림 등 다른 원인)")
    return 0


if __name__ == "__main__":
    import urllib.parse  # noqa: E402  (splits에서만 사용)
    raise SystemExit(main())
