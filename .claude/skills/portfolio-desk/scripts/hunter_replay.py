#!/usr/bin/env python3
"""hunter_replay.py — 경제사냥꾼 아카이브 648편 전수 재분석 (stdlib only·측정 전용)

왜 있나 [2026-08-30 신설 · 정훈 지시 "축적된 모든 영상 자료 다시 분석해보자"]
────────────────────────────────────────────────────────────────────────
우리는 3개월간 채널 영상 648편을 쌓았고 그중 **328편에 티커가, 644편에 판정이** 붙어 있다.
그런데 지금까지 이 원장으로 한 일은 `hunter_score.py`의 **판정 개수 세기**뿐이었다 —
*"채널을 얼마나 신뢰할 것인가"* 를 **가격으로 검정한 적이 한 번도 없다.**
(CLAUDE.md는 '신뢰-견제 균형'을 지시하는데, 그 균형점을 정할 근거가 산문뿐이었다.)

⚠️ **원문 자막은 남아 있지 않다.** `/tmp/hunter_yt`는 세션마다 초기화되고 아카이브엔
   요약(takeaway)만 있다. 그래서 이 도구는 **자막 재분석이 아니라 메타데이터 재분석**이다.
   재추출은 innertube 429 페이싱(편당 40~90초)으로 648편 ≈ 9~16시간이라 별도 배치가 필요하다.

세 축(전부 룩어헤드 없음 — 언급일 t의 종가 기준 forward만 본다):
  ① **언급 → forward 알파**: 채널이 종목을 다룬 날 이후 5/20거래일 벤치마크 초과수익.
     종목 클러스터 보정(종목 1개 = 1표) + 종목 단위 부트스트랩 CI. star_validate와 같은 문법.
  ② **언급 스파이크 → forward 알파**: 그 종목의 최근 언급 밀도가 평소보다 급증한 날만.
     문헌 배경 = GSVI(검색량 기반 관심도) — *개인 주도 시장에서 관심 급증은 이후 초과수익을
     되돌리는 경향*. 우리 `naver_sentiment`가 검색량으로 재는 것을 **채널 언급량**으로 잰다.
  ③ **판정·테마 시계열**: 월별 [검증/정정/미확인] 비율과 테마 부침.

⚠️ **측정 전용 — 별점·스코어·트랜치 어떤 룰도 바꾸지 않는다.** 채널 단독 근거 매수 금지는 그대로.
⚠️ 언급은 **방향(강세/약세)이 아니다.** 아카이브에 방향 필드가 없어 '다뤘다' 이상을 주장할 수 없다.
   음(-)의 알파가 나와도 '채널이 틀렸다'가 아니라 '다룬 뒤 되돌렸다'까지만 읽는다.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ARCHIVE = os.path.join(ROOT, "data/app/hunter_archive.json")
HIST = os.path.join(ROOT, "data/history")
BENCH_KR, BENCH_US = "_KS11", "VOO"
ETF = {"VOO"}

_cache: dict[str, dict] = {}


def series(sym: str):
    key = sym.replace("^", "_")
    if key in _cache:
        return _cache[key]
    path = os.path.join(HIST, f"{key}.csv")
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if rows:
            dk = next((k for k in rows[0] if k.lower() in ("date", "날짜")), None)
            ck = next((k for k in rows[0] if k.lower() in ("close", "adj_close", "종가")), None)
            if dk and ck:
                for r in rows:
                    try:
                        out[r[dk]] = float(r[ck])
                    except (TypeError, ValueError):
                        continue
    _cache[key] = out
    return out


def fwd(sym: str, d0: str, horizon: int):
    """d0 이후 첫 거래일 종가 → horizon 거래일 뒤 종가 수익률(%)."""
    s = series(sym)
    if not s:
        return None
    days = sorted(s)
    lo = next((i for i, d in enumerate(days) if d >= d0), None)
    if lo is None or lo + horizon >= len(days):
        return None
    p0, p1 = s[days[lo]], s[days[lo + horizon]]
    return (p1 / p0 - 1) * 100 if p0 else None


def bench_of(t: str):
    if t in ETF or t.startswith("^"):
        return None
    return BENCH_KR if t.endswith((".KS", ".KQ")) else BENCH_US


def load_rows():
    with open(ARCHIVE, encoding="utf-8") as f:
        vids = (json.load(f) or {}).get("videos") or []
    out = []
    for v in vids:
        d, tk = v.get("date"), v.get("tickers")
        if not d or not tk:
            continue
        if isinstance(tk, str):
            tk = [x.strip() for x in tk.split(",") if x.strip()]
        for t in tk:
            if t and not t.startswith("^"):
                out.append((d, t, v.get("verdict"), v.get("theme"), v.get("title")))
    return out


def cluster(pairs, boot=2000, seed=7):
    """[(ticker, alpha)] → 종목 평균 후 버킷 평균 + 종목 단위 부트스트랩 CI."""
    by = defaultdict(list)
    for t, a in pairs:
        by[t].append(a)
    if not by:
        return None
    means = {t: st.fmean(v) for t, v in by.items()}
    keys = sorted(means)
    point = st.fmean(means.values())
    if len(keys) < 3:
        return {"mean": point, "lo": None, "hi": None, "n": len(pairs), "nt": len(keys),
                "per": means}
    rnd = random.Random(seed)
    samp = sorted(st.fmean([means[rnd.choice(keys)] for _ in keys]) for _ in range(boot))
    return {"mean": point, "lo": samp[int(.025 * boot)], "hi": samp[int(.975 * boot)],
            "n": len(pairs), "nt": len(keys), "per": means}


def fmt(r):
    if not r:
        return "판정 불가"
    ci = f"  [{r['lo']:+.2f}, {r['hi']:+.2f}]" if r["lo"] is not None else "  (CI 불가)"
    return f"{r['mean']:+6.2f}%{ci}   n={r['n']}·종목 {r['nt']}"


def main() -> int:
    ap = argparse.ArgumentParser(description="경제사냥꾼 아카이브 전수 재분석 (측정 전용)")
    ap.add_argument("--horizons", default="5,20", help="전진 거래일 (기본 5,20)")
    ap.add_argument("--spike", type=float, default=2.0,
                    help="언급 스파이크 배수 — 직전 30일 평균 대비 (기본 2.0)")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rows = load_rows()
    print("=" * 78)
    print("  경제사냥꾼 아카이브 전수 재분석 — hunter_replay.py")
    print("=" * 78)
    dates = sorted({d for d, *_ in rows})
    print(f"\n티커 부착 언급 {len(rows)}건 · 고유 종목 {len({t for _, t, *_ in rows})}개 · "
          f"기간 {dates[0]} ~ {dates[-1]}")
    print("⚠️ 언급은 **방향이 아니다**(아카이브에 강세/약세 필드 없음) — '다뤘다'까지만 읽을 것.")

    # 언급 밀도(스파이크 판정용) — 종목별 날짜 리스트
    by_t = defaultdict(list)
    for d, t, *_ in rows:
        by_t[t].append(d)
    for t in by_t:
        by_t[t].sort()

    out = {"horizons": {}}
    for h in [int(x) for x in a.horizons.split(",")]:
        allp, spikep = [], []
        for d, t, *_ in rows:
            b = bench_of(t)
            if not b:
                continue
            r, rb = fwd(t, d, h), fwd(b, d, h)
            if r is None or rb is None:
                continue
            alpha = r - rb
            allp.append((t, alpha))
            # 스파이크 = 직전 30일 언급수가 그 종목 평소(전체기간 30일 환산) 대비 배수 이상
            # ★[8/30 버그수정] 초판은 base = (전체 언급수 × 30 / 전체기간)으로 잡았는데,
            #   전체기간이 3개월이라 base가 최근 30일 언급수와 거의 같아져 **조건이 영원히
            #   안 걸렸다**(스파이크 표본 0 → '판정 불가'가 데이터 탓처럼 보였다).
            #   가드 없는 폴백과 같은 침묵 실패 → **직전 30일 vs 그 이전 30~90일의 30일 환산**으로 교체.
            hist = [x for x in by_t[t] if x < d]
            if len(hist) >= 5:
                recent = sum(1 for x in hist if x >= _shift(d, 30))
                prior = [x for x in hist if _shift(d, 90) <= x < _shift(d, 30)]
                base = len(prior) / 2.0            # 60일치 → 30일 환산
                if base >= 0.5 and recent >= a.spike * base:
                    spikep.append((t, alpha))
        ra, rs = cluster(allp, a.boot), cluster(spikep, a.boot)
        out["horizons"][h] = {"all": ra, "spike": rs}
        print("\n" + "=" * 78)
        print(f"  전진 +{h} 거래일")
        print("=" * 78)
        print(f"  ① 언급 전체        알파 {fmt(ra)}")
        print(f"  ② 언급 스파이크(×{a.spike:g})  알파 {fmt(rs)}")
        if ra and rs and ra["lo"] is not None and rs["lo"] is not None:
            d_ = rs["mean"] - ra["mean"]
            print(f"     ↳ 스파이크 − 전체 = {d_:+.2f}%p "
                  f"({'관심 급증 후 되돌림 방향' if d_ < 0 else '관심 급증이 오히려 우호'})")
        if ra and ra["per"]:
            top = sorted(ra["per"].items(), key=lambda kv: -kv[1])
            print("     ↳ 종목별 상위:", " · ".join(f"{k} {v:+.1f}%" for k, v in top[:4]))
            print("     ↳ 종목별 하위:", " · ".join(f"{k} {v:+.1f}%" for k, v in top[-4:]))

    # ③ 판정·테마 시계열
    print("\n" + "=" * 78)
    print("  ③ 판정·테마 시계열 (아카이브 전체)")
    print("=" * 78)
    with open(ARCHIVE, encoding="utf-8") as f:
        vids = (json.load(f) or {}).get("videos") or []
    mon = defaultdict(lambda: defaultdict(int))
    for v in vids:
        d = v.get("date") or ""
        if len(d) < 7:
            continue
        ver = str(v.get("verdict") or "")
        k = ("정정" if "정정" in ver else "미확인" if "미확인" in ver
             else "검증" if "검증" in ver else "기타")
        mon[d[:7]][k] += 1
    print(f"\n  {'월':<9}{'검증':>6}{'정정':>6}{'미확인':>7}{'기타':>6}{'검증률':>8}")
    for m in sorted(mon):
        c = mon[m]
        judged = c["검증"] + c["정정"] + c["미확인"]
        rate = f"{c['검증'] / judged * 100:.0f}%" if judged else "—"
        print(f"  {m:<9}{c['검증']:>6}{c['정정']:>6}{c['미확인']:>7}{c['기타']:>6}{rate:>8}")
    print("\n  ⚠️ 분모 = 판정 확정분만(기타=미채점·일반 콘텐츠 제외). 8/12 '분모를 의심하라' 준수.")

    th = defaultdict(lambda: defaultdict(int))
    for v in vids:
        t, d = v.get("theme"), v.get("date") or ""
        if t and len(d) >= 7:
            th[t][d[:7]] += 1
    if th:
        print(f"\n  테마 부침 (상위 8):")
        for t, c in sorted(th.items(), key=lambda kv: -sum(kv[1].values()))[:8]:
            trail = " ".join(f"{m[5:]}:{n}" for m, n in sorted(c.items()))
            print(f"    {str(t)[:22]:<24} {sum(c.values()):>3}편   {trail}")

    print("\n※ 측정 전용 — 어떤 룰도 바꾸지 않는다. 채널 단독 근거 매수 금지는 그대로.\n")
    if a.json:
        print(json.dumps(out, ensure_ascii=False, default=str, indent=1))
    return 0


def _dnum(d: str) -> int:
    y, m, dd = (int(x) for x in d.split("-"))
    return y * 372 + m * 31 + dd


def _shift(d: str, days: int) -> str:
    import datetime as _dt
    y, m, dd = (int(x) for x in d.split("-"))
    return (_dt.date(y, m, dd) - _dt.timedelta(days=days)).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
