#!/usr/bin/env python3
"""trim_limit_test.py — 트림 지정가 실측: '현재가 +k% 지정가를 N거래일 매일 재등록' vs '지금 시장가' vs '홀드'

■ 왜 만들었나 [2026-09-23 · 정훈 "정말 매도 가격들 그게 맞아? 객관적인 수치로 확인해서 알려주는거야?"]
   현대차 470,000→400,000원 하향을 권고하면서 근거를 '도달 확률(GBM)'과 '추세 꺾임'으로 댔다.
   도달 확률은 가격이 체결될지만 말하고, **그 가격이 시장가·홀드보다 나은지**는 말하지 않는다.
   → 국내 18종목(2000~) 일봉에서 지금과 같은 차트 국면이었던 날을 모아 세 전략의 결과를 직접 잰다.

■ 방법
   국면: HD(현대차형) = 종가<MA200·MA50<MA200·종가/MA50 -15~-5%·52주고점 -30% 이하
         DR(두산로보형) = MA50<MA200·종가/MA50 -3~+8%·종가/MA200 -10% 이하 · ALL = 필터 없음(대조군)
   전략: 결정일 t 종가 C 기준 L=C(1+k) 지정가를 t+1..t+N 매일 재등록 — 고가≥L이면 max(L, 시가)에 체결,
         대금은 체결일 종가부터 벤치(현금·코스피·S&P500 원화환산)에 투자 / 미체결이면 t+N까지 보유.
         시장가 = t+1 시가 매도 → 벤치 보유. 모두 C로 정규화.
   집계: 풀링(일 단위) 평균·중앙 + 에피소드(같은 종목 45일 공백 시 분리) 가중 + 종목별 부호.
   룩어헤드: MA·52주고점은 t까지만 쓴다. 체결·평가는 t+1 이후.

■ ⚠️ 한계
   · **생존 편향** — 표본은 지금 우리가 추적하는 18종목(살아남은 대형주)이라 '홀드'가 유리하게 나온다.
   · 가격 국면만 본다. 룰2(펀더 훼손)·이익전망은 입력에 없다 — **매도 여부가 아니라 매도 방식**을 답한다.
   · 9/14 애프터마켓(16:00~20:00) 이전 데이터라 체결률은 보수적이다.
   · 측정 전용 — 어떤 룰도 바꾸지 않는다.

사용:
  python trim_limit_test.py            # N=24(9/23→10/29 3Q 실적)
  python trim_limit_test.py --n 60
  python trim_limit_test.py --boot     # 에피소드 부트스트랩 95% CI(HD·DR × 코스피·S&P원화)
정본 결과 = docs/research/trim_limit_test_2026-09-23.md
"""
from __future__ import annotations
import argparse
import csv
import glob
import os
import random
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DATA = os.path.join(ROOT, "data")
KS = [2, 4, 6, 8, 10, 12, 15, 20, 25, 30]
STATES = {
    "HD": lambda c, m50, m200, h252: c < m200 and m50 < m200 and -0.15 <= c / m50 - 1 <= -0.05 and c / h252 - 1 <= -0.30,
    "DR": lambda c, m50, m200, h252: m50 < m200 and -0.03 <= c / m50 - 1 <= 0.08 and c / m200 - 1 <= -0.10,
    "ALL": lambda c, m50, m200, h252: True,
}


def _rd(p, cols):
    out = []
    for r in csv.DictReader(open(p, encoding="utf-8")):
        try:
            out.append((r["date"],) + tuple(float(r[c]) for c in cols))
        except (KeyError, TypeError, ValueError):
            pass
    return out


def _asof(m, keys):
    ks = sorted(m); j = 0; last = None; out = {}
    for d in sorted(keys):
        while j < len(ks) and ks[j] <= d:
            last = m[ks[j]]; j += 1
        out[d] = last
    return out


def run(n: int) -> dict:
    ks11 = {d: c for d, c in _rd(os.path.join(DATA, "history", "_KS11.csv"), ["close"])}
    spx = {d: c for d, c in _rd(os.path.join(DATA, "history", "_GSPC.csv"), ["close"])}
    fx = {d: c for d, c in _rd(os.path.join(DATA, "history", "KRW_X.csv"), ["close"])}
    res = {s: [] for s in STATES}
    for p in sorted(glob.glob(os.path.join(DATA, "history_ohlcv", "*.K[SQ].csv"))):
        tk = os.path.basename(p)[:-4]
        rows = [r for r in _rd(p, ["open", "high", "low", "close"]) if r[4] > 0 and r[2] > 0]
        ds = [r[0] for r in rows]
        km, sm, fm = _asof(ks11, ds), _asof(spx, ds), _asof(fx, ds)
        B = {"cash": {d: 1.0 for d in ds}, "kospi": km,
             "spxkrw": {d: (sm[d] * fm[d] if sm[d] and fm[d] else None) for d in ds}}
        cl = [r[4] for r in rows]
        for t in range(252, len(rows) - n - 1):
            c = cl[t]; m50 = sum(cl[t - 49:t + 1]) / 50; m200 = sum(cl[t - 199:t + 1]) / 200
            h252 = max(r[2] for r in rows[t - 251:t + 1])
            tags = [s for s, f in STATES.items() if f(c, m50, m200, h252)]
            if not tags:
                continue
            T = t + n; out = {}
            for bn, bm in B.items():
                if bm[ds[t + 1]] is None or bm[ds[T]] is None:
                    continue
                now = rows[t + 1][1] * bm[ds[T]] / bm[ds[t + 1]] / c
                hold = cl[T] / c
                dk = {}
                for k in KS:
                    L = c * (1 + k / 100); v = None; fill = None
                    for f in range(t + 1, T + 1):
                        if rows[f][2] >= L:
                            if bm[ds[f]]:
                                v = max(L, rows[f][1]) * bm[ds[T]] / bm[ds[f]] / c
                            fill = f - t
                            break
                    if v is None:
                        v = hold
                    dk[k] = (v - now, fill)
                out[bn] = (now, hold, dk)
            for s in tags:
                res[s].append((tk, ds[t], out))
    return res


def episodes(rs):
    ep, last, eid = {}, {}, {}
    for tk, d, o in rs:
        y, m, dd = map(int, d.split("-")); ordv = y * 372 + m * 31 + dd
        if tk not in last or ordv - last[tk] > 45:
            eid[tk] = eid.get(tk, 0) + 1
        last[tk] = ordv
        ep.setdefault((tk, eid[tk]), []).append(o)
    return ep


def report(res, n):
    for s, rs in res.items():
        print(f"\n==== 국면 {s} · N={n}거래일 · 표본 {len(rs)}일 · 종목 {len(set(r[0] for r in rs))}")
        for bn in ("cash", "kospi", "spxkrw"):
            sub = [o[bn] for _, _, o in rs if bn in o]
            if not sub:
                continue
            eps = episodes([(tk, d, o[bn]) for tk, d, o in rs if bn in o])
            hd = [(h - w) * 100 for w, h, _ in sub]
            print(f"  [{bn}] 에피소드 {len(eps)} | 홀드−시장가 평균 {st.mean(hd):+.2f}%p 중앙 {st.median(hd):+.2f}")
            for k in KS:
                dv = [x[2][k][0] * 100 for x in sub]
                fr = sum(x[2][k][1] is not None for x in sub) / len(sub)
                epm = [st.mean(x[2][k][0] * 100 for x in v) for v in eps.values()]
                print(f"    +{k:>2}%: 체결 {fr * 100:5.1f}% | 시장가 대비 평균 {st.mean(dv):+6.2f}%p 중앙 {st.median(dv):+6.2f}"
                      f" | 에피소드 우위 {sum(x > 0 for x in epm)}/{len(epm)}")


def boot(res, reps=2000, seed=7):
    random.seed(seed)
    for s in ("HD", "DR"):
        for bn in ("kospi", "spxkrw"):
            E = list(episodes([(tk, d, o[bn]) for tk, d, o in res[s] if bn in o]).values())

            def ci(fn):
                vals = [st.mean(fn(x) for x in v) for v in E]
                bs = sorted(st.mean(random.choice(vals) for _ in vals) for _ in range(reps))
                return f"{st.mean(vals):+.2f} [{bs[int(reps * .025)]:+.2f}, {bs[int(reps * .975)]:+.2f}]"
            print(f"\n{s} × {bn} · 에피소드 {len(E)}")
            print(f"  홀드−시장가 {ci(lambda x: (x[1] - x[0]) * 100)}")
            for k in (8, 10, 12, 30):
                print(f"  +{k}% vs 시장가 {ci(lambda x, k=k: x[2][k][0] * 100)} · vs 홀드 "
                      f"{ci(lambda x, k=k: (x[2][k][0] - (x[1] - x[0])) * 100)}")


def main():
    ap = argparse.ArgumentParser(description="트림 지정가 실측 — +k%% 지정가 vs 시장가 vs 홀드 (측정 전용)")
    ap.add_argument("--n", type=int, default=24, help="지평 거래일(기본 24 = 9/23→10/29)")
    ap.add_argument("--boot", action="store_true", help="에피소드 부트스트랩 95%% CI")
    a = ap.parse_args()
    res = run(a.n)
    boot(res) if a.boot else report(res, a.n)


if __name__ == "__main__":
    main()
