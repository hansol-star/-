#!/usr/bin/env python3
"""ma_board.py — 이동평균선 보드 (5·20·60·120일선, 무키·stdlib)

정훈 지시(2026-08-04): "우리 주식들 차트로 해서 이동평균선, 5일 20일 60일 120일 그거 하자."

한국식 4대 이평선을 보유 전종목 + 지수에 대해 계산하고, 배열 상태·이격도·크로스를
판정한다. matplotlib·폰트 설치 없이 **SVG를 직접 생성**하므로 웹/로컬 어디서나 동일하게
돈다(한글은 뷰어 브라우저 폰트로 렌더 → 깨짐 없음).

  python3 ma_board.py                    # 보유 15 + 지수 표
  python3 ma_board.py --tickers AAPL,MU  # 특정 종목만
  python3 ma_board.py --indexes          # 지수 포함
  python3 ma_board.py --svg out/         # 종목별 SVG 차트 저장
  python3 ma_board.py --html board.html  # 카드형 HTML 보드(아티팩트용)
  python3 ma_board.py --save             # data/app/ma_board.json 갱신
  python3 ma_board.py --json

판정 규칙(한국 시장 관습):
  정배열   5>20>60>120  = 상승추세 정렬
  역배열   5<20<60<120  = 하락추세 정렬
  이격도   (현재가/이평선 - 1)*100 — 양수면 이평선 위
  골든크로스 단기선이 장기선을 상향 돌파(최근 10거래일 내)
  데드크로스 그 반대

⚠️ 측정 전용 — 별점·스코어·안전핀·트랜치 어떤 룰도 바꾸지 않는다. 이평선은 후행 지표다.
⚠️ Yahoo 일봉에 결측일이 있으면 그 날이 통째로 빠진 채 창이 밀린다(d66과 같은 뿌리).
   결측 개수를 gaps로 병기하니 값이 이상하면 먼저 그걸 볼 것.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
WINDOWS = (5, 20, 60, 120)
# 이평선 색 — 짧은 선일수록 따뜻한 색(금융 관습), 대비는 라이트/다크 양쪽에서 확보
MA_COLORS = {5: "#e8590c", 20: "#2f9e44", 60: "#1971c2", 120: "#862e9c"}


def fetch_closes(symbol: str, rng: str = "2y", timeout: float = 15.0):
    """일봉 종가 시계열. (dates, closes, currency, gaps) — 결측일은 버리고 개수만 센다."""
    url = YAHOO.format(sym=urllib.request.quote(symbol)) + f"?interval=1d&range={rng}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
        return None, None, None, str(e)
    try:
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        quote = res["indicators"]["quote"][0]
        closes_raw = quote["close"]
        cur = res["meta"].get("currency")
    except (KeyError, IndexError, TypeError):
        return None, None, None, "no data"
    import datetime as dt
    dates, closes, gaps = [], [], 0
    for t, c in zip(ts, closes_raw):
        if c is None:
            gaps += 1
            continue
        dates.append(dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"))
        closes.append(float(c))
    return dates, closes, cur, gaps


def sma_last(closes, n):
    if len(closes) < n:
        return None
    return sum(closes[-n:]) / n


def sma_series(closes, n):
    """각 시점의 n일 단순이동평균 (앞쪽 n-1개는 None)."""
    out, run = [], 0.0
    for i, c in enumerate(closes):
        run += c
        if i >= n:
            run -= closes[i - n]
        out.append(run / n if i >= n - 1 else None)
    return out


def detect_cross(closes, short_n, long_n, lookback=10):
    """최근 lookback 거래일 내 골든/데드 크로스. (kind, days_ago) 또는 (None, None)."""
    s, l = sma_series(closes, short_n), sma_series(closes, long_n)
    n = len(closes)
    for back in range(1, min(lookback, n - 1) + 1):
        i, j = n - back, n - back - 1
        if None in (s[i], l[i], s[j], l[j]):
            continue
        if s[j] <= l[j] and s[i] > l[i]:
            return "golden", back - 1
        if s[j] >= l[j] and s[i] < l[i]:
            return "dead", back - 1
    return None, None


def analyze(label, symbol):
    dates, closes, cur, gaps = fetch_closes(symbol)
    if not closes:
        return {"label": label, "symbol": symbol, "error": gaps or "fetch failed"}
    price = closes[-1]
    mas = {n: sma_last(closes, n) for n in WINDOWS}
    disp = {n: (round((price / mas[n] - 1) * 100, 2) if mas[n] else None) for n in WINDOWS}
    vals = [mas[n] for n in WINDOWS]
    if all(v is not None for v in vals):
        if vals[0] > vals[1] > vals[2] > vals[3]:
            align = "정배열"
        elif vals[0] < vals[1] < vals[2] < vals[3]:
            align = "역배열"
        else:
            align = "혼조"
    else:
        align = "데이터부족"
    above = sum(1 for n in WINDOWS if mas[n] and price > mas[n])
    c520, d520 = detect_cross(closes, 5, 20)
    c2060, d2060 = detect_cross(closes, 20, 60)
    return {
        "label": label, "symbol": symbol, "currency": cur, "price": round(price, 4),
        "as_of": dates[-1], "bars": len(closes), "gaps": gaps,
        "ma": {str(n): (round(mas[n], 4) if mas[n] else None) for n in WINDOWS},
        "disparity": {str(n): disp[n] for n in WINDOWS},
        "align": align, "above_count": above,
        "cross_5_20": {"kind": c520, "days_ago": d520},
        "cross_20_60": {"kind": c2060, "days_ago": d2060},
        "closes": [round(c, 4) for c in closes[-150:]],
        "dates": dates[-150:],
    }


# ── SVG ──────────────────────────────────────────────────────────────────────
def svg_chart(rec, width=560, height=230, pad=6, cost=None):
    """종가 + 4대 이평선. 마지막 120거래일 구간만 그린다(이평선이 살아있는 구간).

    cost를 주면 정훈의 실제 평단을 점선 수평선으로 얹는다 — 이평선 위치와 내 원가를
    한 화면에서 같이 읽으라고 붙인 것(보유 종목 전용, 지수는 None)."""
    closes_all = rec.get("closes") or []
    if len(closes_all) < 5:
        return f'<svg viewBox="0 0 {width} {height}"></svg>'
    # 이평선은 전체 시계열로 계산해야 정확 → 여기서는 저장된 150개로 근사 계산하되
    # 120일선은 앞 120개를 소모하므로 마지막 30개 구간만 유효. 표시 구간을 그에 맞춘다.
    series = {n: sma_series(closes_all, n) for n in WINDOWS}
    show = min(len(closes_all), 120)
    lo_i = len(closes_all) - show
    xs = closes_all[lo_i:]
    pts = [xs] + [[v for v in series[n][lo_i:]] for n in WINDOWS]
    flat = [v for arr in pts for v in arr if v is not None]
    if cost:
        flat.append(float(cost))
    lo, hi = min(flat), max(flat)
    if hi == lo:
        hi = lo + 1
    rng = hi - lo
    lo -= rng * 0.06
    hi += rng * 0.06

    def X(i):
        return pad + i * (width - 2 * pad) / max(len(xs) - 1, 1)

    def Y(v):
        return height - pad - (v - lo) * (height - 2 * pad) / (hi - lo)

    out = [f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
           f'role="img" aria-label="{rec["label"]} 이동평균선 차트">']
    # 종가 영역 + 선
    area = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(xs))
    out.append(f'<polygon points="{X(0):.1f},{height-pad} {area} {X(len(xs)-1):.1f},{height-pad}" '
               f'fill="currentColor" opacity="0.07"/>')
    out.append(f'<polyline points="{area}" fill="none" stroke="currentColor" '
               f'stroke-width="1.6" opacity="0.55"/>')
    # 이평선
    for n in WINDOWS:
        seg, cur_pts = [], []
        for i, v in enumerate(series[n][lo_i:]):
            if v is None:
                if len(cur_pts) > 1:
                    seg.append(cur_pts)
                cur_pts = []
            else:
                cur_pts.append(f"{X(i):.1f},{Y(v):.1f}")
        if len(cur_pts) > 1:
            seg.append(cur_pts)
        for s in seg:
            out.append(f'<polyline points="{" ".join(s)}" fill="none" '
                       f'stroke="{MA_COLORS[n]}" stroke-width="1.8" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>')
    if cost and lo <= float(cost) <= hi:
        cy = Y(float(cost))
        out.append(f'<line x1="{pad}" y1="{cy:.1f}" x2="{width-pad}" y2="{cy:.1f}" '
                   f'stroke="currentColor" stroke-width="1.2" stroke-dasharray="5 4" '
                   f'opacity="0.55"/>')
    out.append("</svg>")
    return "".join(out)


def fmt(v, cur):
    if v is None:
        return "—"
    return f"{v:,.0f}" if cur == "KRW" else f"{v:,.2f}"


def print_table(recs):
    print("\n" + "=" * 92)
    print("  이동평균선 보드 — 5·20·60·120일선 (ma_board.py · 측정 전용)")
    print("=" * 92)
    hdr = f'{"종목":<14}{"현재가":>12}{"5일":>11}{"20일":>11}{"60일":>11}{"120일":>11}  {"배열":<8}위'
    print(hdr)
    print("-" * 92)
    for r in recs:
        if r.get("error"):
            print(f'{r["label"]:<14}  ⚠️ {r["error"]}')
            continue
        cur = r.get("currency")
        m = r["ma"]
        print(f'{r["label"]:<14}{fmt(r["price"],cur):>12}'
              f'{fmt(m["5"],cur):>11}{fmt(m["20"],cur):>11}'
              f'{fmt(m["60"],cur):>11}{fmt(m["120"],cur):>11}'
              f'  {r["align"]:<8}{r["above_count"]}/4')
    print("-" * 92)
    print("※ 이평선은 후행 지표 — 측정 전용이며 별점·스코어·안전핀·트랜치를 바꾸지 않는다.\n")


def load_universe(include_index=False):
    p = os.path.join(HERE, "..", "portfolio.json")
    uni = []
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        for grp in ("kr", "us"):
            for h in d.get("holdings", {}).get(grp, []):
                uni.append((h["label"], h["ticker"]))
    if include_index:
        uni += [("코스피", "^KS11"), ("코스닥", "^KQ11"),
                ("S&P500", "^GSPC"), ("나스닥", "^IXIC"), ("필라델피아반도체", "^SOX")]
    return uni


def main():
    ap = argparse.ArgumentParser(description="이동평균선 보드 (5·20·60·120일선)")
    ap.add_argument("--tickers", help="쉼표구분 심볼 직접 지정")
    ap.add_argument("--indexes", action="store_true", help="지수 포함")
    ap.add_argument("--svg", help="종목별 SVG를 이 디렉터리에 저장")
    ap.add_argument("--html", help="카드형 HTML 보드를 이 경로에 저장")
    ap.add_argument("--save", action="store_true", help="data/app/ma_board.json 갱신")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.tickers:
        uni = [(t.strip(), t.strip()) for t in a.tickers.replace(" ", ",").split(",") if t.strip()]
    else:
        uni = load_universe(a.indexes)

    recs = [analyze(lbl, sym) for lbl, sym in uni]

    if a.svg:
        os.makedirs(a.svg, exist_ok=True)
        for r in recs:
            if not r.get("error"):
                safe = r["symbol"].replace("^", "idx_").replace(".", "_")
                with open(os.path.join(a.svg, f"{safe}.svg"), "w", encoding="utf-8") as f:
                    f.write(svg_chart(r))
        print(f"SVG 저장 → {a.svg}")

    if a.html:
        with open(a.html, "w", encoding="utf-8") as f:
            f.write(render_html(recs))
        print(f"HTML 저장 → {a.html}")

    if a.save:
        out = os.path.join(ROOT, "data/app/ma_board.json")
        slim = [{k: v for k, v in r.items() if k not in ("closes", "dates")} for r in recs]
        json.dump({"updated": recs[0].get("as_of") if recs else None, "stocks": slim},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"저장 → {out}")

    if a.json:
        print(json.dumps(recs, ensure_ascii=False, indent=1))
    else:
        print_table(recs)
    return 0


def render_html(recs):
    """카드형 보드 (아티팩트용 조각 — <body> 내부 내용만)."""
    cards = []
    for r in recs:
        if r.get("error"):
            continue
        cur = r.get("currency")
        badge = {"정배열": "up", "역배열": "down", "혼조": "mix"}.get(r["align"], "mix")
        rows = "".join(
            f'<tr><td><i style="background:{MA_COLORS[n]}"></i>{n}일선</td>'
            f'<td class="num">{fmt(r["ma"][str(n)], cur)}</td>'
            f'<td class="num {"pos" if (r["disparity"][str(n)] or 0) >= 0 else "neg"}">'
            f'{"+" if (r["disparity"][str(n)] or 0) >= 0 else ""}'
            f'{r["disparity"][str(n)] if r["disparity"][str(n)] is not None else "—"}%</td></tr>'
            for n in WINDOWS)
        cross = []
        for key, lab in (("cross_5_20", "5·20"), ("cross_20_60", "20·60")):
            c = r[key]
            if c["kind"]:
                nm = "골든크로스" if c["kind"] == "golden" else "데드크로스"
                ago = "오늘" if c["days_ago"] == 0 else f"{c['days_ago']}일 전"
                cross.append(f'<span class="cross {c["kind"]}">{lab} {nm} · {ago}</span>')
        cards.append(f'''<article class="card">
<header><h3>{r["label"]}</h3><span class="badge {badge}">{r["align"]}</span></header>
<div class="price">{fmt(r["price"], cur)}<small> · 이평선 위 {r["above_count"]}/4</small></div>
<div class="chart">{svg_chart(r)}</div>
<table>{rows}</table>
<div class="crosses">{"".join(cross) or '<span class="cross none">최근 10일 내 크로스 없음</span>'}</div>
</article>''')
    return "\n".join(cards)


if __name__ == "__main__":
    sys.exit(main())
