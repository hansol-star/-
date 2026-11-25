#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
desk_gate.py — 오늘 **어느 섹터 데스크를 띄울 것인가**를 기계가 판정한다 (stdlib + market_data)

[왜 만들었나 — 2026-09-09 정훈 지시 "데스크 구조도 지금 해줘"]
SKILL.md에 트리거 게이트가 **문장으로는** 있었다:
    "섹터 데스크 3종은 ①담당 종목 당일 ±5% ②실적·이벤트 D-7 ③테마 뉴스 ④정훈 지목
     중 하나라도 충족 시 호출. 없으면 지역 데스크 시세로 갈음."
그런데 **아무도 그걸 계산하지 않았다.** 9/9에 나는 "주간 첫 보고서니까"로 7개를 전부 띄웠고,
세션 한도로 4개가 죽어 **두 번** 띄웠다. 데스크 하나가 평균 13만 토큰이니 그날만 150만 토큰이다.

8/2 원칙의 재현이다 — *"오더북에 들어간 것만 집행된다"* → **계산되지 않는 게이트는 게이트가 아니다.**

[무엇을 판정하나]
  ±5% 룰   : 담당 보유·워치 종목의 당일 등락 (market_data 실시세)
  실적 D-7 : event_calendar 의 earnings (담당 종목만)
  → 둘 다 없으면 **SKIP 권고**. 테마 뉴스·정훈 지목은 사람만 아는 것이라 **PM이 --force 로 덮는다.**

⚠️ **권고지 강제가 아니다.** 큰 장세 변화·주간 첫 보고서엔 PM이 전체 호출을 택할 수 있다 —
   다만 그때도 **이 출력을 보고 의식적으로 덮은 것**이어야 한다(오늘처럼 습관으로 전부 띄우지 말고).
⚠️ 지역(kr·us)·매크로·리스크 4개는 **항상 호출**이라 이 게이트의 대상이 아니다.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys

_HERE = os.path.abspath(__file__)
SCRIPTS = os.path.dirname(_HERE)
ROOT = os.path.abspath(os.path.join(_HERE, *([os.pardir] * 5)))

# 섹터 데스크 담당 범위.
# ★[2026-11-22 감사 A7] 정본 = portfolio.json 각 보유·워치 항목의 `desk` 필드(market_data.desk_members).
#   舊 손 복사 목록은 "바뀌면 같이 고칠 것" 주석만 있었고 실제로 안 고쳐졌다 — 11/20 매도한
#   두산로보·현대차·NAVER, 9/23 매도한 AAPL·META가 담당으로 남고(MSFT는 두 번), SPCX는 빠졌다.
#   이제 portfolio.json을 고치면 게이트가 따라온다. 아래 리터럴은 portfolio.json을 못 읽을 때만 쓰는 폴백이다
#   (11/22 기준 desk 필드와 같은 값 — 폴백이 쓰이면 stderr에 경고한다).
_SECTOR_FALLBACK = {
    "semi-ai-desk": ["005930.KS", "NVDA", "MU", "AVGO",
                     "009150.KS", "000660.KS", "AMD", "TSM", "CDNS", "ANET", "LRCX"],
    "power-physical-desk": ["066570.KS", "GEV", "033780.KS", "VRT", "LLY", "BRK-B", "068270.KS"],
    "bigtech-platform-desk": ["GOOGL", "ORCL", "SPCX", "MSFT"],
}


def _sector() -> dict:
    try:
        sys.path.insert(0, SCRIPTS)
        import market_data as _md
        out = {f"{d}-desk": _md.desk_members(d) for d in _md.DESKS}
        if any(out.values()):
            return out
        print("[warn] portfolio.json desk 필드가 비었다 — 내장 폴백 목록을 쓴다", file=sys.stderr)
    except Exception as e:                                        # noqa: BLE001
        print(f"[warn] market_data 데스크 정본 로드 실패 — 내장 폴백 목록을 쓴다: {e}", file=sys.stderr)
    return {k: list(v) for k, v in _SECTOR_FALLBACK.items()}


SECTOR = _sector()
MOVE_PCT = 5.0
EARN_DAYS = 7


def _quotes() -> dict:
    """market_data --group all --json → {symbol: change_pct}"""
    out = {}
    for grp in ("holdings", "watchlist"):
        try:
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "market_data.py"),
                                "--group", grp, "--json"],
                               capture_output=True, text=True, encoding="utf-8", timeout=600)
            for row in json.loads(r.stdout or "[]"):
                if row.get("change_pct") is not None:
                    out[row["symbol"]] = float(row["change_pct"])
        except Exception as e:                                    # noqa: BLE001
            print(f"[warn] 시세 {grp} 실패 — 그 그룹은 ±5% 판정 불가: {e}", file=sys.stderr)
    return out


def _earnings(days: int) -> dict:
    """event_calendar 에서 D-{days} 이내 실적 → {symbol: 'D-n'}"""
    out = {}
    try:
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "event_calendar.py"),
                            "--within", str(days)],
                           capture_output=True, text=True, encoding="utf-8", timeout=600)
        for line in (r.stdout or "").splitlines():
            if "💵" not in line:
                continue
            import re
            dm = re.search(r"D-(\d+)", line)
            sm = re.search(r"\d{4}-\d{2}-\d{2}\s+([A-Z0-9.]+)", line)
            if dm and sm:
                out[sm.group(1)] = f"D-{dm.group(1)}"
    except Exception as e:                                        # noqa: BLE001
        print(f"[warn] 실적 캘린더 실패 — D-7 판정 불가: {e}", file=sys.stderr)
    return out


def selftest() -> int:
    """★[2026-11-22 감사 A7] 담당 범위 = portfolio.json 현재 보유·워치의 desk 필드.
    舊 리터럴(매도 5종목 잔존·MSFT 중복·SPCX 누락)은 아래 세 검사에 모두 걸린다."""
    import market_data as _md
    ok = True

    def check(cond, label, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  {'✅' if cond else '❌'} {label}" + (f" — {detail}" if detail and not cond else ""))

    print("desk_gate 자가검증 — 섹터 데스크 담당 범위 ↔ portfolio.json desk 정본")
    live = set(_md.held_tickers()) | {s for _, s in _md.WATCHLIST}
    allsyms = [s for v in SECTOR.values() for s in v]
    check(len(allsyms) == len(set(allsyms)), "중복 없음(한 종목 = 한 데스크)",
          str(sorted({s for s in allsyms if allsyms.count(s) > 1})))
    check(set(allsyms) <= live, "담당 = 현재 보유·워치뿐(매도·제외 종목 없음)", str(sorted(set(allsyms) - live)))
    dm = _md.desk_map()
    want = {t for t, d in dm.items() if d}
    check(set(allsyms) == want, "desk 필드가 있는 모든 비ETF 종목이 어느 데스크엔가 있다",
          f"빠짐 {sorted(want - set(allsyms))} · 남음 {sorted(set(allsyms) - want)}")
    check("SPCX" not in dm or "SPCX" in SECTOR.get("bigtech-platform-desk", []),
          "SPCX(보유) = 빅테크·플랫폼 데스크")
    keep = _md.desk_members
    try:
        _md.desk_members = lambda *a, **k: []
        fb = _sector()
    finally:
        _md.desk_members = keep
    check(fb == _SECTOR_FALLBACK, "portfolio.json desk가 비면 내장 폴백(경고와 함께)")
    print("✅ 통과" if ok else "❌ 실패")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="섹터 데스크 스폰 게이트 (권고)")
    ap.add_argument("--move", type=float, default=MOVE_PCT, help=f"±%% 임계(기본 {MOVE_PCT})")
    ap.add_argument("--days", type=int, default=EARN_DAYS, help=f"실적 D-n(기본 {EARN_DAYS})")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true",
                    help="오프라인 자가검증 — 담당 범위가 portfolio.json desk 정본과 같은가(네트워크 없음)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    px, earn = _quotes(), _earnings(a.days)
    res = {}
    for desk, syms in SECTOR.items():
        moves = [(s, px[s]) for s in syms if s in px and abs(px[s]) >= a.move]
        earns = [(s, earn[s]) for s in syms if s in earn]
        res[desk] = {"spawn": bool(moves or earns),
                     "moves": sorted(moves, key=lambda x: -abs(x[1])),
                     "earnings": earns,
                     "covered": sum(1 for s in syms if s in px), "total": len(syms)}

    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0

    print("═══ 섹터 데스크 스폰 게이트 (권고 — PM이 덮을 수 있다) ═══")
    print(f"  기준: 담당 종목 당일 ±{a.move:.0f}% 또는 실적 D-{a.days} 이내\n")
    for desk, r in res.items():
        mark = "🟢 스폰 권고" if r["spawn"] else "⚪ SKIP 권고"
        print(f"{mark}  {desk}   (시세 확보 {r['covered']}/{r['total']})")
        for s, p in r["moves"][:4]:
            print(f"      ±{a.move:.0f}%  {s} {p:+.2f}%")
        for s, d in r["earnings"][:4]:
            print(f"      실적   {s} {d}")
        if not r["spawn"]:
            print("      → 지역 데스크 시세로 갈음. 띄우면 약 13만 토큰이 그냥 나간다.")
    n = sum(1 for r in res.values() if r["spawn"])
    print(f"\n  권고: 섹터 {n}/3 스폰  (지역2+매크로+리스크 4개는 항상 별도)")
    print("  ⚠️ 테마 뉴스·정훈 지목은 기계가 모른다 — 있으면 PM이 덮을 것.")
    print("  ⚠️ 주간 첫 보고서·큰 장세 변화엔 전체 호출도 가능하나, **이 출력을 보고 의식적으로** 덮을 것.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
