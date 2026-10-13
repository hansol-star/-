#!/usr/bin/env python3
"""
macro_data.py — 무키(無key) 매크로 하드넘버 수집기 (FRED CSV + Polymarket)

매크로 데스크가 WebSearch 추정 대신 인용할 수 있는 검증된 숫자를 키 없이 가져온다.
표준 라이브러리만 사용 — pip 불필요, 로컬 이전 시 그대로 이식.
(착안: TradingAgents v0.3.0이 FRED·Polymarket을 데이터 벤더로 편입 — 2026-07-14 B5 라운드)

데이터 소스:
  - FRED fredgraph.csv (세인트루이스 연준, 무키 공개 CSV)
  - Polymarket gamma API (무키 조회 전용) — 이벤트 내재확률 참고용

사용법:
  python3 macro_data.py                    # FRED 핵심 지표 표 (금리·CPI·VIX·유가·달러)
  python3 macro_data.py --json             # JSON 출력 (데스크/파이프라인용)
  python3 macro_data.py --series DGS10,VIXCLS
  python3 macro_data.py --polymarket fed   # Polymarket에서 'fed' 포함 활성 마켓 확률
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={cosd}"
POLY_API = ("https://gamma-api.polymarket.com/markets"
            "?closed=false&limit=200&order=volumeNum&ascending=false")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
KST = timezone(timedelta(hours=9))

# id: (라벨, 단위, 주기)  — 주기 m=월간(YoY 계산용), d=일간
SERIES = {
    "DGS10":     ("미국채 10Y", "%", "d"),
    "DGS2":      ("미국채 2Y", "%", "d"),
    "DFII10":    ("미 10Y 실질금리(TIPS)", "%", "d"),
    "T10YIE":    ("10Y 기대인플레(BEI)", "%", "d"),
    "EFFR":      ("실효 연방기금금리", "%", "d"),
    "VIXCLS":    ("VIX", "", "d"),
    "DCOILWTICO": ("WTI 유가", "$", "d"),
    "DTWEXBGS":  ("달러지수(광의)", "", "d"),
    "CPIAUCSL":  ("미 CPI(지수→YoY 계산)", "", "m"),
    "UNRATE":    ("미 실업률", "%", "m"),
}


def http(url: str, timeout: int = 20) -> str:
    # curl 우선(기본 UA 그대로): FRED(Akamai)는 파이썬 TLS를 스톨시키고, 브라우저 UA를 단
    # curl도 차단한다(UA↔TLS 핑거프린트 불일치 탐지 — 7/14 실측). curl 기본 UA만 통과.
    # curl은 리눅스·맥 기본 탑재라 로컬 이전에도 포터블.
    if shutil.which("curl"):
        out = subprocess.run(
            ["curl", "-sSL", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def fetch_series(sid: str):
    """FRED CSV → [(date, float), ...] (결측 '.' 제거, 최근 ~18개월).

    월간 YoY는 '직전 관측의 12개월 전'까지 필요하다 — 발표 지연 2개월 + 13개월 = 15개월이라
    480일(15.8개월)은 여유가 없었다. 560일로 늘린다.
    """
    cosd = (datetime.now(KST) - timedelta(days=560)).strftime("%Y-%m-%d")
    raw = http(FRED_CSV.format(sid=sid, cosd=cosd))
    rows = []
    for line in raw.strip().splitlines()[1:]:
        parts = line.split(",")
        if len(parts) != 2 or parts[1].strip() in (".", ""):
            continue
        try:
            rows.append((parts[0].strip(), float(parts[1])))
        except ValueError:
            continue
    return rows


def yoy_by_date(rows, idx: int = -1):
    """rows[idx]를 **날짜로 찾은 정확히 12개월 전 관측**과 비교 → (YoY %, 기준월). 없으면 (None, 기준월).

    ★[2026-10-13 수정] 舊 코드는 위치(rows[-13])로 12개월 전을 집었다. FRED CPIAUCSL에 2025-10 관측이
      없어(결측 '.') 시계열이 한 칸 짧았고, rows[-13]은 **13개월 전**을 가리켰다 — 2026-08 CPI가
      3.71%로 찍혔는데 실제 전년비는 3.35%(공식 3.4%)다. 컨센 3.6~3.7%인 9월 CPI를 '이미 그 수준'으로
      읽게 만드는 오차였다. 위치는 결측 하나에 조용히 틀리므로 날짜로 맞춘다 — 못 맞추면 값을 내지 않는다.
    """
    d, v = rows[idx]
    want = f"{int(d[:4]) - 1:04d}-{d[5:7]}"
    for bd, bv in rows:
        if bd[:7] == want and bv:
            return round((v / bv - 1) * 100, 2), want
    return None, want


def collect(series_ids):
    out, errors = {}, []
    for sid in series_ids:
        label, unit, freq = SERIES[sid]
        try:
            rows = fetch_series(sid)
        except Exception as ex:
            errors.append(f"{sid}: {ex}")
            continue
        if not rows:
            errors.append(f"{sid}: 데이터 없음")
            continue
        d, v = rows[-1]
        pd_, pv = rows[-2] if len(rows) >= 2 else (None, None)
        item = {"label": label, "unit": unit, "date": d, "value": v,
                "prev": pv, "prev_date": pd_, "delta": round(v - pv, 4) if pv is not None else None}
        # CPI 지수는 12개월 전 대비 YoY로 환산 — 날짜로 맞춘다(yoy_by_date)
        if sid == "CPIAUCSL":
            item["yoy_pct"], item["yoy_base"] = yoy_by_date(rows, -1)
            if item["yoy_pct"] is None:
                item["yoy_note"] = f"미산출 — 12개월 전({item['yoy_base']}) 관측 결측 · BLS 공식치를 쓸 것"
            item["prev_yoy_pct"], item["prev_yoy_base"] = (
                yoy_by_date(rows, -2) if len(rows) >= 2 else (None, None))
        out[sid] = item
    # 파생: 2s10s 스프레드 (bp)
    if "DGS10" in out and "DGS2" in out:
        sp = (out["DGS10"]["value"] - out["DGS2"]["value"]) * 100
        out["_2s10s"] = {"label": "2s10s 스프레드", "unit": "bp",
                         "date": out["DGS10"]["date"], "value": round(sp, 1),
                         "prev": None, "delta": None}
    return out, errors


def fmt_table(data, errors):
    print(f"매크로 하드넘버 (FRED 무키 · 조회 {datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')})")
    print(f"{'지표':<22}{'값':>10}  {'전기':>10}  {'기준일':>12}")
    for sid, it in data.items():
        val = f"{it['value']:.2f}{it['unit']}"
        if "yoy_pct" in it:
            prev_yoy = it.get("prev_yoy_pct")
            val = f"YoY {it['yoy_pct']:.2f}%" if it["yoy_pct"] is not None else "YoY 미산출"
            it_prev = f"{prev_yoy:.2f}%" if prev_yoy is not None else "-"
            print(f"{it['label']:<22}{val:>10}  {it_prev:>10}  {it['date']:>12}")
            if it.get("yoy_note"):
                print(f"   ⚠️ {it['yoy_note']}")
            continue
        prev = f"{it['prev']:.2f}" if it.get("prev") is not None else "-"
        print(f"{it['label']:<22}{val:>10}  {prev:>10}  {it['date']:>12}")
    if errors:
        print("\n[미수신]", "; ".join(errors))
    print("\n※ FRED 일간 시계열은 1영업일 지연이 정상. 당일 장중값은 market_data.py·WebSearch로 보완.")


def polymarket(keyword: str, top: int = 8):
    """Polymarket 활성 마켓에서 키워드 매칭 상위 확률 출력 (참고용 내재확률)."""
    try:
        markets = json.loads(http(POLY_API, timeout=25))
    except Exception as ex:
        print(f"[오류] Polymarket 조회 실패: {ex}", file=sys.stderr)
        return []
    kw = keyword.lower()
    hits = []
    for m in markets:
        q = m.get("question", "")
        if kw not in q.lower():
            continue
        try:
            outcomes = json.loads(m.get("outcomes", "[]"))
            prices = [float(p) for p in json.loads(m.get("outcomePrices", "[]"))]
        except Exception:
            outcomes, prices = [], []
        hits.append({
            "question": q,
            "odds": {o: round(p * 100, 1) for o, p in zip(outcomes, prices)},
            "volume_usd": round(float(m.get("volumeNum") or 0)),
            "end": (m.get("endDate") or "")[:10],
        })
    hits.sort(key=lambda h: -h["volume_usd"])
    return hits[:top]


def selftest() -> int:
    """결측월이 낀 시계열에서 YoY가 12개월 전을 정확히 집는지(네트워크 없음)."""
    fails = []

    def ok(name, cond):
        if not cond:
            fails.append(name)
        print(f"  {'✅' if cond else '❌'} {name}")

    # 2025-06 ~ 2026-08, 매월 +1 — 2025-10 관측 결측(실제 FRED CPIAUCSL과 같은 모양)
    months = [(2025, m) for m in range(6, 13)] + [(2026, m) for m in range(1, 9)]
    rows = [(f"{y}-{m:02d}-01", 300.0 + i) for i, (y, m) in enumerate(months) if (y, m) != (2025, 10)]
    yoy, base = yoy_by_date(rows, -1)
    old = round((rows[-1][1] / rows[-13][1] - 1) * 100, 2)          # 舊 위치 기반
    ok("2026-08의 기준월은 2025-08", base == "2025-08")
    ok("YoY = 314/302 − 1 = 3.97%", yoy == round((314 / 302 - 1) * 100, 2))
    ok("舊 위치 기반 계산은 13개월 전(2025-07)을 집어 과대(사고 재현)", old > yoy and rows[-13][0][:7] == "2025-07")
    pyoy, pbase = yoy_by_date(rows, -2)
    ok("직전월도 날짜로(2026-07 ↔ 2025-07)", pbase == "2025-07" and pyoy == round((313 / 301 - 1) * 100, 2))
    rows2 = rows + [("2026-09-01", 315.0), ("2026-10-01", 316.0)]
    ok("12개월 전이 결측이면 값을 내지 않는다(2026-10 ↔ 2025-10)", yoy_by_date(rows2, -1) == (None, "2025-10"))
    print()
    print("✅ SELFTEST PASS" if not fails else "❌ SELFTEST FAIL: " + ", ".join(fails))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="YoY 날짜 매칭 자가검증(오프라인)")
    ap.add_argument("--series", help="쉼표구분 FRED 시리즈 ID (기본 전체)")
    ap.add_argument("--polymarket", metavar="KEYWORD",
                    help="Polymarket 활성 마켓 키워드 검색 (예: fed, recession, tariff)")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if args.polymarket:
        hits = polymarket(args.polymarket)
        if args.json:
            print(json.dumps(hits, ensure_ascii=False, indent=1))
        else:
            print(f"Polymarket '{args.polymarket}' 활성 마켓 (거래량순 · 내재확률 참고용, 정본 아님)")
            for h in hits:
                odds = " / ".join(f"{o} {p}%" for o, p in h["odds"].items())
                print(f"- {h['question']} → {odds}  (V ${h['volume_usd']:,} · ~{h['end']})")
            if not hits:
                print("- 매칭 없음 (상위 200 거래량 마켓 내)")
        return

    ids = [s.strip().upper() for s in args.series.split(",")] if args.series else list(SERIES)
    bad = [s for s in ids if s not in SERIES]
    if bad:
        sys.exit(f"알 수 없는 시리즈: {bad} (지원: {', '.join(SERIES)})")
    data, errors = collect(ids)
    if args.json:
        print(json.dumps({"as_of_kst": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
                          "data": data, "errors": errors}, ensure_ascii=False, indent=1))
    else:
        fmt_table(data, errors)


if __name__ == "__main__":
    main()
