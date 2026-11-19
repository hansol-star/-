"""pct_exit_test.py — 매수가 대비 +X% 익절 / -Y% 손절 룰 검정 (측정 전용 · 룰 변경 없음)

계기: 정훈 11/19 "+몇% 하락 몇% 되면 팔고 정리하는 기준을 정해두자"
시행 원장: trial_registry id = pct_exit_rule (돌리기 전 등록 · 변형 24)

방법
- 표본 A(종목): data/history의 국내·미국 단일종목. 매월 첫 거래일에 1단위 매수했다고 놓고 H거래일 추적.
  · 룰: 종가가 매수가 ×(1+TP) 이상 또는 ×(1−SL) 이하인 첫날 종가에 매도 → 남은 기간은 그 시장 지수에 재투자
    (국내 .KS = 코스피 · .KQ = 코스닥 · 미국 = S&P500). 왕복 비용 국내 0.30% · 미국 0.10%.
  · 대조: 같은 날 사서 H일 보유.
- 표본 B(지수): 18개 지수에 같은 룰 · 청산 후 현금 연 3%. 생존 편향이 종목보다 작다.
- 판정(8/5 절차): ①집계(풀링 평균·중앙) ②진입연도 에피소드(연도별 평균 차이의 부호) ③횡단면(종목별 평균 차이 > 0인 비율 · 단측 이항 p) → Holm 보정(변형 24개).
⚠️ 한계: 표본 A는 지금 추적 중인 살아남은 종목이다(생존 편향 → 홀드에 유리, 손절에 불리).
          종가 체결 가정(갭 하락은 더 나쁘게 체결된다 → 손절에 유리하게 잡힘).
"""
import argparse, bisect, csv, json, math, os, statistics as st
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
HIST = os.path.join(ROOT, 'data', 'history')
SKIP = {'BTC-USD', 'BZ_F', 'CL_F', 'DX-Y.NYB', 'GC_F', 'KRW_X', 'VOO', '000001.SS', 'XU100.IS', 'SPCX', 'GEV'}
INDEXES = ['_KS11', '_KQ11', '_N225', '_HSI', '_TWII', '_BVSP', '_MXX', '_JKSE', '_KLSE', '_BSESN',
           '_GDAXI', '_FTSE', '_STOXX50E', '_AXJO', '_GSPTSE', '_TA125.TA', '_IXIC', '_GSPC']
TPS = [0.10, 0.20, 0.30, 0.50]
SLS = [0.10, 0.15, 0.20, 0.30]


def load(name):
    p = os.path.join(HIST, name + '.csv')
    out = []
    with open(p, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                c = float(r['close'])
            except (TypeError, ValueError):
                continue
            if c > 0:
                out.append((r['date'], c))
    return out


def variants():
    v = [(tp, None) for tp in TPS] + [(None, sl) for sl in SLS] + [(tp, sl) for tp in TPS for sl in SLS]
    return v


def label(v):
    tp, sl = v
    a = f'+{int(tp*100)}%' if tp else '—'
    b = f'-{int(sl*100)}%' if sl else '—'
    return f'익절 {a} / 손절 {b}'


def month_starts(dates, last_ok):
    out, seen = [], set()
    for i, d in enumerate(dates[:last_ok + 1]):
        ym = d[:7]
        if ym not in seen:
            seen.add(ym)
            out.append(i)
    return out


def binom_p(k, n):
    """단측 P(X>=k), p=0.5"""
    if n == 0:
        return 1.0
    return sum(math.comb(n, j) for j in range(k, n + 1)) / 2 ** n


def holm(ps):
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj = [0.0] * m
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * ps[i]))
        adj[i] = run
    return adj


def run_series(px, bench_fn, cost, H, vs):
    """px: [(date, close)] · bench_fn(d0, d1) -> 재투자 수익 배수"""
    dates = [d for d, _ in px]
    closes = [c for _, c in px]
    if len(px) < H + 30:
        return []
    rows = []
    for i in month_starts(dates, len(px) - H - 1):
        p0 = closes[i]
        end = i + H
        hold = closes[end] / p0 - 1
        rec = {'date': dates[i], 'hold': hold, 'rule': {}}
        for v in vs:
            tp, sl = v
            hit = None
            for t in range(i + 1, end + 1):
                r = closes[t] / p0
                if (tp and r >= 1 + tp) or (sl and r <= 1 - sl):
                    hit = t
                    break
            if hit is None:
                rec['rule'][v] = (hold, False)
            else:
                g = closes[hit] / p0 * (1 - cost) * bench_fn(dates[hit], dates[end]) - 1
                rec['rule'][v] = (g, True)
        rows.append(rec)
    return rows


def main():
    ap = argparse.ArgumentParser(description='+X% 익절 / -Y% 손절 룰 검정 (측정 전용)')
    ap.add_argument('--horizon', type=int, default=252, help='거래일 (기본 252 = 12M)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    H = a.horizon
    vs = variants()

    bench = {k: load(k) for k in ('_KS11', '_KQ11', '_GSPC')}
    bdates = {k: [d for d, _ in v] for k, v in bench.items()}

    def bfn(key):
        s, ds = bench[key], bdates[key]

        def f(d0, d1):
            i = max(0, bisect.bisect_right(ds, d0) - 1)
            j = max(0, bisect.bisect_right(ds, d1) - 1)
            return s[j][1] / s[i][1]
        return f

    names = sorted(n[:-4] for n in os.listdir(HIST) if n.endswith('.csv') and not n.startswith('_'))
    names = [n for n in names if n not in SKIP]
    stock_rows = {}
    for n in names:
        if n.endswith('.KQ'):
            key, cost = '_KQ11', 0.003
        elif n.endswith('.KS'):
            key, cost = '_KS11', 0.003
        else:
            key, cost = '_GSPC', 0.001
        rows = run_series(load(n), bfn(key), cost, H, vs)
        if len(rows) >= 12:
            stock_rows[n] = rows

    cash = (1.03) ** (1 / 252)

    def cash_fn_factory(px):
        ds = [d for d, _ in px]

        def f(d0, d1):
            i = bisect.bisect_left(ds, d0)
            j = bisect.bisect_left(ds, d1)
            return cash ** max(0, j - i)
        return f

    idx_rows = {}
    for n in INDEXES:
        px = load(n)
        rows = run_series(px, cash_fn_factory(px), 0.001, H, vs)
        if len(rows) >= 12:
            idx_rows[n] = rows

    def summarize(universe):
        out = []
        for v in vs:
            pooled, per_unit, per_year, hits = [], [], defaultdict(list), 0
            n_all = 0
            for name, rows in universe.items():
                diffs = []
                for r in rows:
                    g, hit = r['rule'][v]
                    d = g - r['hold']
                    diffs.append(d)
                    pooled.append(d)
                    per_year[r['date'][:4]].append(d)
                    hits += hit
                    n_all += 1
                per_unit.append(st.mean(diffs))
            k = sum(x > 0 for x in per_unit)
            ky = sum(st.mean(x) > 0 for x in per_year.values())
            out.append({'variant': label(v), 'tp': v[0], 'sl': v[1],
                        'mean': st.mean(pooled) * 100, 'median': st.median(pooled) * 100,
                        'hit_rate': hits / n_all * 100,
                        'units_pos': k, 'units': len(per_unit), 'p': binom_p(k, len(per_unit)),
                        'years_pos': ky, 'years': len(per_year)})
        adj = holm([r['p'] for r in out])
        for r, h in zip(out, adj):
            r['holm'] = h
        return out

    res = {'horizon': H,
           'stocks': {'n': len(stock_rows), 'names': sorted(stock_rows), 'rows': summarize(stock_rows)},
           'indexes': {'n': len(idx_rows), 'names': sorted(idx_rows), 'rows': summarize(idx_rows)}}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return
    for key, title in (('stocks', f'표본 A — 단일종목 {res["stocks"]["n"]}개 (청산 후 그 시장 지수 재투자)'),
                       ('indexes', f'표본 B — 지수 {res["indexes"]["n"]}개 (청산 후 현금 연 3%)')):
        print(f'\n== {title} · 지평 {H}거래일 · 룰 − 보유 (%p) ==')
        print(f'{"변형":<22}{"평균":>7}{"중앙":>7}{"발동률":>7}  {"③횡단면":>9}{"②연도":>9}{"Holm p":>8}')
        for r in res[key]['rows']:
            print(f'{r["variant"]:<22}{r["mean"]:>+7.2f}{r["median"]:>+7.2f}{r["hit_rate"]:>6.0f}%  '
                  f'{r["units_pos"]:>4}/{r["units"]:<4}{r["years_pos"]:>4}/{r["years"]:<4}{r["holm"]:>8.3f}')
    print('\n※ 측정 전용 — 어떤 룰도 바꾸지 않는다. 채택 요건 = ①②③ 통과 + Holm p<0.05 + 대조군.')


if __name__ == '__main__':
    main()
