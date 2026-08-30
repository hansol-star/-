#!/usr/bin/env python3
"""hunter_stance.py — 자막에서 종목별 '논조(강세/약세)'를 뽑아 방향 있는 콜을 검정한다.

왜 있나 [2026-08-30 신설 · 자막 432편 전량 회수 직후]
──────────────────────────────────────────────────────────
`hunter_replay.py`(같은 날 신설)는 채널 **언급**의 forward 알파를 쟀지만 거기엔 결정적 한계가
있었다 — *"아카이브에 방향(강세/약세) 필드가 없어 '다뤘다' 이상을 주장할 수 없다"*.
그래서 결과(언급 알파 +0.61%·CI 0 포함)를 **"채널이 틀렸다"로 읽을 수 없었다.**

자막 원문이 확보되면서 그 한계가 풀린다. 이 도구는 종목명 주변 문맥에서 **방향 어휘**를 세어
논조를 ①강세 ②약세 ③중립으로 분류하고, **강세 콜만 골라 forward 알파**를 잰다.
그래야 비로소 *"채널 말대로 샀으면 어땠나"* 라는 질문에 답할 수 있다.

방법:
  · 종목명(한글명·티커) 매치 위치의 **±윈도우**에서 강세/약세 어휘 빈도를 센다.
  · (강세−약세) 부호로 논조 결정. 동수·0이면 중립(제외).
  · 종목 클러스터 보정 + 종목 단위 부트스트랩 CI (star_validate·hunter_replay와 같은 문법).

⚠️ **키워드 방식은 거칠다.** 반어("좋다고들 하는데")·조건문("빠지면 기회")·타 종목 비교를
   구분하지 못한다. 그래서 이 도구는 **정확도 표본검사(`--sample`)를 같이 제공**하고,
   결과는 *"거친 방향 대리지표"* 이상으로 주장하지 않는다.
⚠️ **측정 전용.** 채널 단독 근거 매수 금지(CLAUDE.md 신뢰-견제 균형)는 그대로다.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import re
import statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
TDIR = os.path.join(ROOT, "data/transcripts/hunter")
ARCHIVE = os.path.join(ROOT, "data/app/hunter_archive.json")
HIST = os.path.join(ROOT, "data/history")

# 우리 보유·워치 축의 종목만 본다 — 채널이 스치듯 언급하는 잡종목까지 넣으면 신호가 희석된다.
NAMES = {
    "005930.KS": ["삼성전자", "삼전"], "000660.KS": ["하이닉스", "sk하이닉스", "닉스"],
    "005380.KS": ["현대차"], "066570.KS": ["lg전자"], "035420.KS": ["네이버", "naver"],
    "454910.KS": ["두산로보"], "042660.KS": ["한화오션"], "009150.KS": ["삼성전기"],
    "034020.KS": ["두산에너빌리티", "두산에너"], "207940.KS": ["삼성바이오"],
    "240810.KQ": ["원익"], "095610.KQ": ["테스"], "033780.KS": ["kt&g", "케이티앤지"],
    "NVDA": ["엔비디아"], "MU": ["마이크론"], "AAPL": ["애플"], "MSFT": ["마이크로소프트"],
    "GOOGL": ["구글", "알파벳"], "META": ["메타"], "AVGO": ["브로드컴"], "TSLA": ["테슬라"],
    "ORCL": ["오라클"], "AMD": ["amd"], "IONQ": ["아이온큐"], "SPCX": ["스페이스x", "스페이스엑스"],
}
BULL = ["기회", "저점", "매수", "담", "반등", "상승", "오를", "오른다", "좋", "강세", "수혜",
        "실적 개선", "저평가", "바닥", "회복", "긍정", "호재", "성장", "유망"]
BEAR = ["위험", "조심", "주의", "하락", "빠질", "빠진다", "고점", "거품", "경고", "우려",
        "부담", "악재", "매도", "팔", "손절", "약세", "둔화", "쇼크", "폭락"]

_cache: dict[str, dict] = {}


def series(sym: str):
    key = sym.replace("^", "_")
    if key in _cache:
        return _cache[key]
    path = os.path.join(HIST, f"{key}.csv")
    out = {}
    if os.path.exists(path):
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        if rows:
            dk = next((k for k in rows[0] if k.lower() in ("date", "날짜")), None)
            ck = next((k for k in rows[0] if k.lower() in ("close", "adj_close", "종가")), None)
            if dk and ck:
                for r in rows:
                    try:
                        out[r[dk]] = float(r[ck])
                    except (TypeError, ValueError):
                        pass
    _cache[key] = out
    return out


def fwd(sym: str, d0: str, h: int):
    s = series(sym)
    if not s:
        return None
    days = sorted(s)
    lo = next((i for i, d in enumerate(days) if d >= d0), None)
    if lo is None or lo + h >= len(days):
        return None
    p0, p1 = s[days[lo]], s[days[lo + h]]
    return (p1 / p0 - 1) * 100 if p0 else None


def bench_of(t: str):
    return "_KS11" if t.endswith((".KS", ".KQ")) else "VOO"


def stance_of(text: str, keys: list[str], win: int):
    """종목명 주변 ±win자에서 (강세어 수, 약세어 수)."""
    low = text.lower()
    b = s = 0
    hit = 0
    for k in keys:
        for m in re.finditer(re.escape(k.lower()), low):
            hit += 1
            seg = low[max(0, m.start() - win): m.end() + win]
            b += sum(seg.count(w) for w in BULL)
            s += sum(seg.count(w) for w in BEAR)
    return b, s, hit


def cluster(pairs, boot=2000, seed=11):
    by = defaultdict(list)
    for t, a in pairs:
        by[t].append(a)
    if not by:
        return None
    means = {t: st.fmean(v) for t, v in by.items()}
    keys = sorted(means)
    point = st.fmean(means.values())
    if len(keys) < 3:
        return {"mean": point, "lo": None, "hi": None, "n": len(pairs), "nt": len(keys), "per": means}
    rnd = random.Random(seed)
    samp = sorted(st.fmean([means[rnd.choice(keys)] for _ in keys]) for _ in range(boot))
    return {"mean": point, "lo": samp[int(.025 * boot)], "hi": samp[int(.975 * boot)],
            "n": len(pairs), "nt": len(keys), "per": means}


def fmt(r):
    if not r:
        return "판정 불가(표본 없음)"
    ci = f"  [{r['lo']:+.2f}, {r['hi']:+.2f}]" if r["lo"] is not None else "  (CI 불가)"
    return f"{r['mean']:+6.2f}%{ci}   n={r['n']}·종목 {r['nt']}"


def main() -> int:
    ap = argparse.ArgumentParser(description="자막 논조 → 방향 있는 콜 검정 (측정 전용)")
    ap.add_argument("--horizons", default="5,20")
    ap.add_argument("--window", type=int, default=180, help="종목명 주변 문맥 폭(자)")
    ap.add_argument("--margin", type=int, default=2, help="강세-약세 차이가 이 값 이상일 때만 채택")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--sample", type=int, default=0, help="논조 판정 표본 N건 출력(정확도 눈검사)")
    a = ap.parse_args()

    arch = {v["id"]: v for v in json.load(open(ARCHIVE, encoding="utf-8"))["videos"] if v.get("id")}
    recs = []
    for fn in os.listdir(TDIR):
        if not fn.endswith(".md"):
            continue
        vid = fn[:-3]
        meta = arch.get(vid)
        if not meta or not meta.get("date"):
            continue
        raw = open(os.path.join(TDIR, fn), encoding="utf-8").read()
        i = raw.find("## 트랜스크립트")
        body = raw[i + len("## 트랜스크립트"):] if i >= 0 else raw
        for tk, keys in NAMES.items():
            b, s, hit = stance_of(body, keys, a.window)
            if not hit:
                continue
            recs.append({"vid": vid, "date": meta["date"], "ticker": tk,
                         "bull": b, "bear": s, "hits": hit, "title": meta.get("title", "")})

    print("=" * 78)
    print("  자막 논조 검정 — hunter_stance.py  (강세 콜만 골라 forward 알파)")
    print("=" * 78)
    dates = sorted({r["date"] for r in recs})
    print(f"\n자막 {len([f for f in os.listdir(TDIR) if f.endswith('.md')])}편에서 "
          f"종목 언급 {len(recs)}건 · 고유 종목 {len({r['ticker'] for r in recs})}개 · "
          f"{dates[0]} ~ {dates[-1]}")

    bull = [r for r in recs if r["bull"] - r["bear"] >= a.margin]
    bear = [r for r in recs if r["bear"] - r["bull"] >= a.margin]
    neut = len(recs) - len(bull) - len(bear)
    print(f"논조 분류(margin≥{a.margin}): 강세 {len(bull)} · 약세 {len(bear)} · 중립/애매 {neut}")

    if a.sample:
        print(f"\n── 판정 표본 {a.sample}건 (키워드 방식 정확도 눈검사) ──")
        for r in (bull[:a.sample // 2] + bear[:a.sample - a.sample // 2]):
            tag = "강세" if r["bull"] > r["bear"] else "약세"
            print(f"  [{tag}] {r['date']} {r['ticker']:<10} 강{r['bull']}/약{r['bear']} · {r['title'][:40]}")

    for h in [int(x) for x in a.horizons.split(",")]:
        def alpha(rows):
            out = []
            for r in rows:
                fr, br = fwd(r["ticker"], r["date"], h), fwd(bench_of(r["ticker"]), r["date"], h)
                if fr is not None and br is not None:
                    out.append((r["ticker"], fr - br))
            return out
        rb, rs, ra = cluster(alpha(bull), a.boot), cluster(alpha(bear), a.boot), cluster(alpha(recs), a.boot)
        print("\n" + "=" * 78)
        print(f"  전진 +{h} 거래일")
        print("=" * 78)
        print(f"  ⓐ 강세 논조   알파 {fmt(rb)}")
        print(f"  ⓑ 약세 논조   알파 {fmt(rs)}")
        print(f"  ⓒ 전체 언급   알파 {fmt(ra)}   ← hunter_replay와 같은 축(대조군)")
        if rb and rs:
            print(f"     ↳ 강세−약세 = {rb['mean'] - rs['mean']:+.2f}%p "
                  f"({'방향 판별력 있음(양수)' if rb['mean'] > rs['mean'] else '역방향(음수) — 반대로 읽어야'})")

    print("\n⚠️ 키워드 논조는 **거친 대리지표**다 — 반어·조건문·비교문을 구분 못 한다.")
    print("⚠️ 측정 전용. 채널 단독 근거 매수 금지는 그대로.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
