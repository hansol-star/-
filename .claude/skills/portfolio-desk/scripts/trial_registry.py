#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trial_registry.py — 룰 검정 시행 원장 + 다중검정 보정 (stdlib·무네트워크·측정 전용)

[왜 — 2026-09-30 2차 외부 리서치 H · 정훈 "새로 찾은 우리 결함과 조치 실시"]
7/30~9/30 동안 룰 변경 가설을 10개 넘게 검정했고(변형까지 치면 수십 개) 그중 몇 개를 채택했다.
그런데 **몇 번 시도했는지 기록한 곳도, 그 횟수만큼 기준을 올린 적도 없다.** 20번 던지면 한 번은
p<0.05가 우연으로 나온다(Bailey·López de Prado 2014 Deflated Sharpe · Holm 1979 · Benjamini-Hochberg 1995 ·
bettyguo/agent-backtest-lab이 시행 수 보고를 필수로 둔다).

설계:
  · 원장 = data/research/trials.jsonl (1줄 = 검정 1건). --backfill이 7/30~9/30 검정을 소급 기록한다.
  · 대표 p = ③ 횡단면(시장 수 부호검정) 정확 단측 이항 p. ③이 없으면 ②(에피소드), 둘 다 없으면 null.
    ⚠️ 에피소드 6개짜리 ②는 최소 p가 0.0156이라 가족 크기 4 이상이면 **Holm을 절대 통과 못 한다** —
       보정 판정은 사실상 ③이 짊어진다. 그래서 ③(시장 수)을 대표로 쓴다.
  · 보정 = Holm(가족별·전체) + BH(FDR). 판정 기준 = Holm 보정 p < 0.05.
  · 이항 p는 독립 가정이다 — 시장들이 같은 세계 위기를 공유하므로 **실제 불확실성은 더 크다**(보정 후에도 낙관 쪽).

사용:
  python trial_registry.py --backfill          # 소급 원장 작성(덮어씀)
  python trial_registry.py --list              # 원장 + Holm·BH 보정 판정
  python trial_registry.py --family rule1      # 한 가족만
  python trial_registry.py --add '{"id":..., "family":..., "k":18, "n":21, ...}'   # 새 검정은 **돌리기 전에** 등록
  python trial_registry.py --sign 18 21        # 단측 이항 p
  python trial_registry.py --dsr 1.2 20 756 -0.3 5   # Deflated Sharpe(연율 SR, 시행 수, 관측 수, 왜도, 첨도)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics as st
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *([os.pardir] * 4)))
REG = os.path.join(ROOT, "data", "research", "trials.jsonl")
ALPHA = 0.05


def sign_p(k: int, n: int) -> float:
    """H0 p=0.5에서 n번 중 k번 이상 성공할 확률(정확 단측)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def _ncdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _ninv(p: float) -> float:
    lo, hi = -10.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _ncdf(mid) < p else (lo, mid)
    return (lo + hi) / 2


def dsr(sr: float, n_trials: int, t_obs: int, skew: float = 0.0, kurt: float = 3.0, sr_var: float | None = None) -> float:
    """Deflated Sharpe Ratio(Bailey·López de Prado 2014) — 관측 단위 SR 기준 확률값.
    sr = 관측 단위(예: 일간) Sharpe. sr_var = 시행들 사이 SR 분산(없으면 1/t_obs 근사)."""
    v = sr_var if sr_var is not None else 1.0 / t_obs
    g = 0.5772156649
    sr0 = math.sqrt(v) * ((1 - g) * _ninv(1 - 1 / n_trials) + g * _ninv(1 - 1 / (n_trials * math.e)))
    den = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr ** 2))
    return _ncdf((sr - sr0) * math.sqrt(t_obs - 1) / den)


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj, run = [0.0] * m, 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * ps[i]))
        adj[i] = run
    return adj


def bh(ps: list[float]) -> list[float]:
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i], reverse=True)
    adj, run = [0.0] * m, 1.0
    for r, i in enumerate(order):
        run = min(run, ps[i] * m / (m - r))
        adj[i] = run
    return adj


# ── 소급 원장 (근거 = docs/research/* · CLAUDE.md 룰1 서술 · 오늘 실행 결과) ──────────────────
# k/n = 가설 방향 우위 시장 수(③) · ek/en = 에피소드(②). 가설 방향 = "제안된 변경이 낫다".
BACKFILL = [
    dict(id="storm_cut_repeal", date="2026-07-30", family="rule1", decision="7/30 룰1 2차 개정",
         hypothesis="폭풍 금액 감산이 역효과 — 폐지가 낫다", variants=4, k=4, n=4, level="②해금 4단계(11지수 풀링)",
         adopted=True, note="시장별 ③ 집계가 없다 — 11개 지수 풀링 17,946표본에서 해금 4단계 전부 같은 방향(4/4)을 대표값으로 쓴다"),
    dict(id="ratchet_reset", date="2026-07-31", family="rule1", decision="7/31 RESET 확정",
         hypothesis="해금은 현재 낙폭으로 매일 재계산(RESET)이 래칫보다 낫다", variants=2, k=3, n=3, level="②낙폭 구간 3개(11지수)",
         adopted=True, note="구간가중 -0.61%p · 시장별 ③ 없음"),
    dict(id="floor_exemption", date="2026-08-05", family="rule1", decision="§4b 기각",
         hypothesis="붕괴 구간에선 하드플로어 면제가 낫다", variants=1, k=5, n=10, level="③10지수",
         adopted=False, note="집계 +9.5%p는 IMF 1개가 만든 것"),
    dict(id="kr_only_floor", date="2026-08-05", family="rule1", decision="§4c 기각",
         hypothesis="국내 전용 플로어가 낫다", variants=1, k=7, n=17, level="③17시장",
         adopted=False, note="에피소드 188개로 확대 · 코스피 vs 코스닥 반대"),
    dict(id="d0_step", date="2026-09-09", family="rule1", decision="D0 신설(정훈 승인)",
         hypothesis="-20~-25% 구간도 12M 상승 기대", variants=1, k=18, n=21, ek=6, en=6, level="③21시장·②6에피소드",
         adopted=True, note="기저율 질문('사도 되나') — '어떻게 넣나'(사다리 vs 분할)는 검정 안 함"),
    dict(id="us_track_p3", date="2026-09-21", family="us_track", decision="d205",
         hypothesis="달러는 3회 균등 분할(P3)이 코스피 게이트(G)보다 낫다", variants=2, k=19, n=19, ek=6, en=6, level="③19시장",
         adopted=True, note="사전등록 ② 정의는 24/38(63%)로 미통과 — 두 결과 모두 기록"),
    dict(id="sp_ladder_SL", date="2026-09-22", family="us_track", decision="d208 기각",
         hypothesis="미국 트랙에 S&P 낙폭 사다리", variants=10, k=7, n=20, level="③20시장",
         adopted=False, note="변형 약 20개 중 대표 2개만 기록 — 나머지 변형 수는 variants에 반영"),
    dict(id="sp_accel_PA", date="2026-09-22", family="us_track", decision="d208 — 통과했지만 대조군에 짐",
         hypothesis="분할 중 -10%면 가속", variants=10, k=19, n=20, ek=10, en=11, level="③20시장",
         adopted=False, note="낙폭 없이 빨리 산 대조군이 더 컸다(드리프트) — 9/22 대조군 원칙의 발단"),
    dict(id="trim_limit_hold", date="2026-09-23", family="sell_rule", decision="d210",
         hypothesis="가격 추세는 매도 근거가 아니다(홀드 > 시장가 매도)", variants=3, k=None, n=None, level="단일 국면",
         adopted=True, note="시장 간 재현 없음 — 홀드 +4.95%p는 한 국면·소수 종목"),
    dict(id="risk_cap_30", date="2026-09-30", family="sizing", decision="d221 기각",
         hypothesis="단일종목 위험기여 ≤30% 상한", variants=3, k=None, n=None, level="KR·US 2시장(부호 갈림)",
         adopted=False, note="Sharpe≈0 · 대조군과 차이 없음"),
    dict(id="ladder_vs_dca6", date="2026-09-30", family="rule1", decision="제안(정훈 승인 대기)",
         hypothesis="같은 원화를 6개월 균등 분할(DCA6)이 현행 사다리(LF)보다 낫다", variants=7, k=20, n=22, ek=5, en=6,
         level="③22시장·②6에피소드", adopted=False,
         note="ladder_dca_test.py 사전등록 판정 REPLACE→DCA6 · LAG1·LF12·LR 변형도 REPLACE · 손익분기 현금금리 8.8~10%"),
    dict(id="star_alpha", date="2026-09-14", family="stars", decision="측정(룰 아님)",
         hypothesis="별점이 forward 알파를 예측", variants=4, k=None, n=None, level="CI 0/3",
         adopted=False, note="star_validate 부트스트랩 CI 전부 0 포함 = 무판정"),
]


def rep_p(t: dict):
    if t.get("k") is not None and t.get("n"):
        return sign_p(int(t["k"]), int(t["n"]))
    if t.get("ek") is not None and t.get("en"):
        return sign_p(int(t["ek"]), int(t["en"]))
    return None


def load() -> list[dict]:
    if not os.path.exists(REG):
        return []
    out = []
    for ln in open(REG, encoding="utf-8"):
        ln = ln.strip()
        if ln and not ln.startswith("//"):
            out.append(json.loads(ln))
    return out


def save(rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(REG), exist_ok=True)
    with open(REG, "w", encoding="utf-8", newline="\n") as f:
        f.write("// 룰 검정 시행 원장 — trial_registry.py. 새 검정은 돌리기 전에 --add로 등록한다(사후 선별 방지).\n")
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def judge(rows: list[dict]) -> list[dict]:
    with_p = [(i, rep_p(r)) for i, r in enumerate(rows)]
    idx = [i for i, p in with_p if p is not None]
    ps = [p for _, p in with_p if p is not None]
    h_all, b_all = holm(ps), bh(ps)
    out = [dict(r, p=None, holm_all=None, bh_all=None, holm_fam=None) for r in rows]
    for j, i in enumerate(idx):
        out[i].update(p=ps[j], holm_all=h_all[j], bh_all=b_all[j])
    for fam in {r["family"] for r in rows}:
        fi = [i for i in idx if rows[i]["family"] == fam]
        for i, a in zip(fi, holm([out[i]["p"] for i in fi])):
            out[i]["holm_fam"] = a
    for r in out:
        if r["p"] is None:
            r["verdict"] = "판정불가(시장 간 재현 없음)"
        elif r["holm_all"] < ALPHA:
            r["verdict"] = "보정 후 유의"
        elif r["holm_fam"] < ALPHA:
            r["verdict"] = "가족 내에서만 유의"
        else:
            r["verdict"] = "보정 후 비유의"
        if r.get("adopted") and r["verdict"] != "보정 후 유의":
            r["verdict"] += " ⚠️채택된 룰 — 근거 취약"
    return out


def show(rows: list[dict], family: str | None = None) -> None:
    res = [r for r in judge(rows) if not family or r["family"] == family]
    m = sum(1 for r in judge(rows) if r["p"] is not None)
    print(f"룰 검정 원장 {len(rows)}건 · p 산출 {m}건 · 변형 합계 {sum(r.get('variants') or 1 for r in rows)}개 · 기준 Holm p<{ALPHA}")
    print(f"{'id':<18}{'날짜':<11}{'가족':<10}{'채택':<4}{'근거':<16}{'p':>9}{'Holm전체':>10}{'Holm가족':>10}{'BH':>9}  판정")
    f = lambda x: "—" if x is None else (f"{x:.1e}" if x < 1e-3 else f"{x:.4f}")
    for r in res:
        kn = f"{r['k']}/{r['n']}" if r.get("k") is not None else (f"②{r['ek']}/{r['en']}" if r.get("ek") is not None else "—")
        print(f"{r['id']:<18}{r['date']:<11}{r['family']:<10}{'Y' if r.get('adopted') else '-':<4}{kn:<16}"
              f"{f(r['p']):>9}{f(r['holm_all']):>10}{f(r['holm_fam']):>10}{f(r['bh_all']):>9}  {r['verdict']}")
    print("⚠️ 이항 p는 시장 독립을 가정한다 — 같은 세계 위기를 공유하므로 실제 불확실성은 더 크다.")


def main() -> int:
    ap = argparse.ArgumentParser(description="룰 검정 시행 원장 + 다중검정 보정(Holm·BH·DSR) — 측정 전용")
    ap.add_argument("--backfill", action="store_true", help="7/30~9/30 검정을 소급 기록(원장 덮어씀)")
    ap.add_argument("--list", action="store_true", help="원장 + 보정 판정")
    ap.add_argument("--family", help="한 가족만 표시")
    ap.add_argument("--add", metavar="JSON", help="검정 1건 추가(돌리기 전에 등록)")
    ap.add_argument("--sign", nargs=2, type=int, metavar=("K", "N"), help="단측 이항 p")
    ap.add_argument("--dsr", nargs=5, type=float, metavar=("SR", "TRIALS", "T", "SKEW", "KURT"),
                    help="Deflated Sharpe(관측 단위 SR)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.sign:
        print(f"{sign_p(*a.sign):.6g}")
        return 0
    if a.dsr:
        sr, n, t, sk, ku = a.dsr
        print(f"DSR = {dsr(sr, int(n), int(t), sk, ku):.4f}")
        return 0
    if a.backfill:
        save(BACKFILL)
        print(f"소급 기록 {len(BACKFILL)}건 → {os.path.relpath(REG, ROOT)}")
    if a.add:
        rows = load()
        t = json.loads(a.add)
        if not {"id", "date", "family", "hypothesis"} <= set(t):
            print("id·date·family·hypothesis 필수", file=sys.stderr)
            return 2
        rows.append(t)
        save(rows)
    rows = load()
    if a.json:
        print(json.dumps(judge(rows), ensure_ascii=False, indent=1))
    elif a.list or a.family or a.backfill or a.add:
        show(rows, a.family)
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
