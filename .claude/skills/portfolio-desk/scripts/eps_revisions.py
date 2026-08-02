#!/usr/bin/env python3
"""eps_revisions.py — 애널리스트 EPS 추정치 리비전 추세 (Yahoo earningsTrend, 무키·stdlib)

`docs/data_coverage.md §3 #3` 결손 해소 (2026-08-01 신설).
그 문서가 이 레이어를 이렇게 적어뒀다: *"목표가 레벨은 있지만 추정치가 오르는 중인지
내리는 중인지가 없다. 오닐 CANSLIM의 실질 동력."*

우리가 이미 가진 컨센서스 축과의 차이:
  · consensus.py  = **목표주가 레벨**(지금 얼마로 보나)      → 상방 여력
  · valuation.py  = **밸류에이션**(그 값이 비싼가)           → 선반영 판정
  · 이 스크립트   = **추정치의 1차 미분**(전망이 어느 쪽으로 움직이나) → 방향

레벨은 이미 가격에 반영돼 있을 수 있지만, **리비전은 정보가 도착하는 속도**를 본다.
CANSLIM의 C(당기)·A(연간)가 *과거 실적*인 데 반해 리비전은 *미래 추정의 변화*라 선행 축이다.

⚠️ **측정 전용 — 별점·스코어·트랜치·안전핀 어떤 룰도 이 숫자가 바꾸지 않는다.**
   (naver_sentiment.py·vol_gauge.py와 같은 등급. 매수 트리거 아님.)
   근거: Yahoo는 **현재 스냅샷만** 주고 과거 시계열을 주지 않는다 → 낙폭 구간 층화 검증이
   불가능하다. 2026-07-30에 폭풍 감산·항복 가산이 **평시와 크래시에서 방향이 반대**였음이
   드러난 이상(dev_handoff "지표는 국면별로 의미가 뒤집힌다"), 미검증 신호를 룰에 넣지 않는다.
   ⇒ 지금 할 일은 **원장 누적 개시**. 표본이 쌓이면 R3에서 층화 검증 후 승격 여부를 재논의한다.

⚠️ 점수는 **부호 있는 -100~+100**이다. 별점 밴드(0~100, 85~100=⭐5)와 **다른 축**이므로
   섞어 쓰지 말 것. 혼동을 막으려고 일부러 다른 스케일을 썼다.

산출(기간 0q/+1q/0y/+1y 각각):
  ① epsTrend  — 현재 / 7일 / 30일 / 60일 / 90일 전 추정치 → 변화율
  ② epsRevisions — 최근 7·30일 상향/하향 애널리스트 수 → **브레드스(만장일치 여부)**
  ③ 모멘텀 점수(-100~+100) = 드리프트(90일 변화율)와 브레드스의 결합

사용:
  python3 eps_revisions.py                  # 보유 전종목 +1y 요약표
  python3 eps_revisions.py --all            # 보유 + 워치
  python3 eps_revisions.py --period 0y      # 기간 지정 (0q/+1q/0y/+1y)
  python3 eps_revisions.py --detail MU      # 한 종목 전 기간 상세
  python3 eps_revisions.py --save           # data/app/eps_revisions.json + 이력 원장
  python3 eps_revisions.py --json

무키(Yahoo crumb) — consensus.py의 인증 플로우를 그대로 재사용한다(earnings.py와 동일 패턴).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consensus import _opener, get_crumb  # crumb 플로우 재사용 (earnings.py:21과 동일)
import cli_common

KST = datetime.timezone(datetime.timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "..", "..", "..", "..", "data", "app", "eps_revisions.json")

PERIODS = ["0q", "+1q", "0y", "+1y"]
PERIOD_LABEL = {"0q": "당분기", "+1q": "다음분기", "0y": "당해년", "+1y": "내년"}

# 결과 상태 — ★ 실패(FAIL)와 부재(NO_DATA)를 반드시 구분한다.
#   data_coverage.md §4b: "0은 결론이 아니라 가설이다. 실패와 부재를 코드에서 구분해 출력할 것."
#   (2026-07-30 Form 4 사고 = 9/9 종목 수집 실패를 '재량적 매수 0건'으로 보고했다.)
OK, NO_DATA, FAIL = "ok", "no_data", "fail"


def _universe(include_watch: bool):
    """티커의 정본 = portfolio.json (market_data.py가 미러). 접미사를 절대 손대지 않는다.
    ★2026-07-30 사고: 두산로보 접미사를 .KQ로 바꿔 잡아 코스닥 '남의 회사' 재무를 담았다."""
    try:
        import market_data as md
        pairs = list(md.HOLDINGS_KR) + list(md.HOLDINGS_US)
        if include_watch:
            pairs += list(md.WATCHLIST)
        return pairs
    except Exception as e:
        sys.exit("[eps_revisions] market_data.py 유니버스 로드 실패: %s" % e)


def _raw(node, key):
    v = (node or {}).get(key)
    if isinstance(v, dict):
        return v.get("raw")
    return v


def fetch_trend(op, crumb, symbol, retries=2):
    """earningsTrend 조회 → {period: {...}} 또는 상태 표시.

    404/빈 trend = **부재**(ETF·애널리스트 미커버). 네트워크·인증 오류 = **실패**.
    이 둘을 같은 값으로 뭉개면 커버리지 통계가 거짓말을 한다.
    """
    url = ("https://query1.finance.yahoo.com/v10/finance/quoteSummary/%s"
           "?modules=earningsTrend&crumb=%s" % (symbol, urllib.request.quote(crumb)))
    last = ""
    for attempt in range(retries + 1):
        try:
            with op.open(url, timeout=15) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # ETF 등 — 애널리스트 추정치가 애초에 존재하지 않는다.
                return {"status": NO_DATA, "reason": "커버리지 없음(ETF 등, HTTP 404)"}
            last = "HTTP %s" % e.code
        except Exception as e:
            last = "%s %s" % (type(e).__name__, str(e)[:40])
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    else:
        return {"status": FAIL, "reason": last or "unknown"}

    try:
        res = data["quoteSummary"]["result"]
        trend = (res[0] if res else {}).get("earningsTrend", {}).get("trend", [])
    except (KeyError, IndexError, TypeError):
        return {"status": FAIL, "reason": "응답 구조 예상 밖"}
    if not trend:
        return {"status": NO_DATA, "reason": "추정치 없음(빈 trend)"}

    out = {}
    for t in trend:
        p = t.get("period")
        if p not in PERIODS:
            continue
        et, rev = t.get("epsTrend") or {}, t.get("epsRevisions") or {}
        out[p] = {
            "end_date": t.get("endDate"),
            "n_analysts": _raw(t.get("earningsEstimate"), "numberOfAnalysts"),
            "cur": _raw(et, "current"),
            "d7": _raw(et, "7daysAgo"),
            "d30": _raw(et, "30daysAgo"),
            "d60": _raw(et, "60daysAgo"),
            "d90": _raw(et, "90daysAgo"),
            "up7": _raw(rev, "upLast7days"),
            "down7": _raw(rev, "downLast7days"),
            "up30": _raw(rev, "upLast30days"),
            "down30": _raw(rev, "downLast30days"),
        }
    if not out:
        return {"status": NO_DATA, "reason": "해당 기간 추정치 없음"}
    return {"status": OK, "periods": out}


def pct_change(cur, ago):
    """추정치 변화율. 적자 종목(음수 EPS)도 방향이 맞도록 분모에 절대값을 쓴다.
    예: 두산로보 -174 → -307 이면 (-307-(-174))/174 = -76.2% (악화)."""
    if cur is None or ago is None or ago == 0:
        return None
    return round((cur - ago) / abs(ago) * 100, 1)


def breadth(up, down):
    """상향/하향 애널리스트 수의 브레드스 -1.0~+1.0.
    None은 Yahoo가 '0건'일 때 자주 내보내는 값이라 0으로 본다. 단 둘 다 None이면 데이터 없음."""
    if up is None and down is None:
        return None, 0
    u, d = up or 0, down or 0
    if u + d == 0:
        return None, 0          # 리비전 자체가 정지 — 0.0(중립)과 구분한다
    return round((u - d) / (u + d), 3), u + d


SHRINK_K = 4.0  # 브레드스 축소 상수 — n=1이면 20%만, n=30이면 88% 반영


def momentum(drift_90d, brd, n_rev=0):
    """리비전 모멘텀 -100~+100 (★별점 0~100 밴드와 다른 축 — 섞지 말 것).

    드리프트(추정치가 얼마나 움직였나)와 브레드스(합의가 얼마나 한쪽인가)를 반반 섞는다.
    한쪽만 크면 과신 위험: 소수 애널리스트의 큰 상향(드리프트↑·브레드스 약)과
    다수의 소폭 상향(드리프트 약·브레드스↑)은 성격이 다르다.

    ★브레드스는 **표본 수로 축소(shrinkage)** 한다: brd × n/(n+4).
      첫 구현은 이걸 빠뜨려서 **KT&G가 애널리스트 1명 상향만으로 '강한상향'(+57.7)**,
      두산에너빌리티는 90일 추정치가 +3.6% 올랐는데도 3명 하향에 눌려 '하향'(-46.4)이 됐다.
      n=1의 만장일치(±1.0)와 n=30의 만장일치(MU)를 같은 무게로 쓰면 안 된다 —
      `drawdown_history.py` 기저율 규율("표본 수 항상 병기")의 같은 원칙이다.
    """
    parts, weights = [], []
    if drift_90d is not None:
        parts.append(max(-100.0, min(100.0, drift_90d * 2.0)))  # ±50% → ±100 포화
        weights.append(0.5)
    if brd is not None and n_rev:
        parts.append(brd * 100.0 * (n_rev / (n_rev + SHRINK_K)))
        weights.append(0.5)
    if not parts:
        return None
    return round(sum(p * w for p, w in zip(parts, weights)) / sum(weights), 1)


def band(score):
    if score is None:
        return "데이터없음"
    if score >= 50:
        return "강한상향"
    if score >= 15:
        return "상향"
    if score > -15:
        return "중립"
    if score > -50:
        return "하향"
    return "강한하향"


def summarize(name, symbol, res, period):
    row = {"name": name, "symbol": symbol, "period": period, "status": res["status"]}
    if res["status"] != OK:
        row["reason"] = res.get("reason", "")
        return row
    p = res["periods"].get(period)
    if not p:
        row["status"] = NO_DATA
        row["reason"] = "%s 기간 없음" % period
        return row
    brd, n_rev = breadth(p.get("up30"), p.get("down30"))
    d90 = pct_change(p.get("cur"), p.get("d90"))
    row.update({
        "end_date": p.get("end_date"), "n_analysts": p.get("n_analysts"),
        "cur": p.get("cur"),
        "chg_7d": pct_change(p.get("cur"), p.get("d7")),
        "chg_30d": pct_change(p.get("cur"), p.get("d30")),
        "chg_90d": d90,
        "up30": p.get("up30"), "down30": p.get("down30"),
        "breadth": brd, "n_revisions": n_rev,
        "score": momentum(d90, brd, n_rev),
    })
    row["band"] = band(row["score"])
    return row


def _fmt_pct(v):
    return "  —  " if v is None else "%+6.1f%%" % v


def print_table(rows, period):
    print("── EPS 추정치 리비전 · %s(%s) — 90일 변화 내림차순" % (PERIOD_LABEL.get(period, period), period))
    print("   %-14s %8s %8s %8s  %7s %4s %7s  %s"
          % ("종목", "7일", "30일", "90일", "상/하30", "표본", "점수", "등급"))
    ok = [r for r in rows if r["status"] == OK]
    ok.sort(key=lambda r: (r.get("chg_90d") is None, -(r.get("chg_90d") or 0)))
    for r in ok:
        ud = "%s/%s" % (r.get("up30") if r.get("up30") is not None else "-",
                        r.get("down30") if r.get("down30") is not None else "-")
        sc = "  —  " if r["score"] is None else "%+6.1f" % r["score"]
        n = r.get("n_revisions") or 0
        # 표본 수 병기 — n<5는 신뢰구간이 넓다는 표시(drawdown 기저율 규율과 동일)
        print("   %-14s %8s %8s %8s  %7s %4s %7s  %s%s"
              % (r["name"][:14], _fmt_pct(r.get("chg_7d")), _fmt_pct(r.get("chg_30d")),
                 _fmt_pct(r.get("chg_90d")), ud, n or "-", sc, r["band"],
                 " ⚠️표본희박" if 0 < n < 5 else ""))

    nod = [r for r in rows if r["status"] == NO_DATA]
    bad = [r for r in rows if r["status"] == FAIL]
    if nod:
        print("\n   · 데이터 부재(정상): " + ", ".join("%s(%s)" % (r["name"], r["reason"]) for r in nod))
    if bad:
        print("\n   🚨 수집 실패 — 이건 '리비전 없음'이 아니라 '못 봤음'이다:")
        for r in bad:
            print("      · %-10s %s" % (r["name"], r["reason"]))
    print("\n   수집 %d/%d (부재 %d · 실패 %d)" % (len(ok), len(rows), len(nod), len(bad)))


def print_detail(name, symbol, res):
    print("── %s (%s) 전 기간 상세" % (name, symbol))
    if res["status"] != OK:
        print("   %s — %s" % (res["status"], res.get("reason")))
        return
    print("   %-8s %-12s %10s %8s %8s %8s  %s" % ("기간", "종료", "현재", "30일변화", "90일변화", "상/하30", "등급"))
    for p in PERIODS:
        d = res["periods"].get(p)
        if not d:
            continue
        brd, n_rev = breadth(d.get("up30"), d.get("down30"))
        d90 = pct_change(d.get("cur"), d.get("d90"))
        sc = momentum(d90, brd, n_rev)
        cur = d.get("cur")
        # 국내는 EPS가 원 단위로 수만~수십만이라 자릿수 구분이 필요하다(삼성 65,888원 vs MU $153.74)
        cur_s = "—" if cur is None else (format(cur, ",.2f") if abs(cur) < 10000 else format(cur, ",.0f"))
        print("   %-8s %-12s %10s %8s %8s %8s  %s"
              % (PERIOD_LABEL.get(p, p), (d.get("end_date") or "")[:10], cur_s,
                 _fmt_pct(pct_change(d.get("cur"), d.get("d30"))), _fmt_pct(d90),
                 "%s/%s" % (d.get("up30"), d.get("down30")), band(sc)))


def _load_store():
    try:
        with open(os.path.abspath(STORE), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"note": "애널리스트 EPS 추정치 리비전 시계열 (eps_revisions.py --save). "
                        "측정 전용 — 별점·스코어·룰 미반영.",
                "history": []}


def save(rows, period, keep=200):
    """Yahoo는 현재 스냅샷만 주므로 **지금부터 쌓아야 시계열이 생긴다**
    (sentiment_history.json과 같은 누적 사상)."""
    today = datetime.datetime.now(KST).strftime("%Y-%m-%d")
    record = {"date": today, "period": period,
              "rows": [{k: r.get(k) for k in
                        ("name", "symbol", "status", "cur", "chg_7d", "chg_30d", "chg_90d",
                         "up30", "down30", "breadth", "score", "band")} for r in rows]}
    st = _load_store()
    hist = [h for h in st.get("history", [])
            if not (h.get("date") == today and h.get("period") == period)]
    hist.append(record)
    hist.sort(key=lambda h: (h.get("date", ""), h.get("period", "")))
    st["history"] = hist[-keep:]
    st["updated"] = today
    st["latest"] = record
    path = os.path.abspath(STORE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="EPS 추정치 리비전 추세 (Yahoo 무키)")
    ap.add_argument("--all", action="store_true", help="보유 + 워치리스트")
    ap.add_argument("--period", default="+1y", choices=PERIODS, help="기본 +1y(내년)")
    ap.add_argument("--detail", help="한 종목 전 기간 상세 (심볼 또는 표기명)")
    ap.add_argument("--tickers", help="쉼표·공백구분 심볼 직접 지정")
    ap.add_argument("--save", action="store_true", help="data/app/eps_revisions.json 누적")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    op = _opener()
    crumb = get_crumb(op)
    if not crumb:
        print("crumb 발급 실패 — Yahoo 인증 거부. 잠시 후 재시도 권장(수집 실패이지 '리비전 없음' 아님).")
        return 2

    if args.tickers:
        pairs = [(s.strip(), s.strip()) for s in cli_common.split_tickers(args.tickers) if s.strip()]
    else:
        pairs = _universe(args.all or bool(args.detail))

    if args.detail:
        key = args.detail.strip().lower()
        match = [(n, s) for n, s in pairs if key in (n.lower(), s.lower())]
        if not match:
            return int(bool(sys.stderr.write("해당 종목 없음: %s\n" % args.detail))) or 2
        name, sym = match[0]
        res = fetch_trend(op, crumb, sym)
        if args.json:
            print(json.dumps({"name": name, "symbol": sym, "result": res}, ensure_ascii=False, indent=1))
        else:
            print_detail(name, sym, res)
        return 0

    rows = []
    for i, (name, sym) in enumerate(pairs):
        res = fetch_trend(op, crumb, sym)
        rows.append(summarize(name, sym, res, args.period))
        if i < len(pairs) - 1:
            time.sleep(0.5)  # Yahoo 페이싱

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        stamp = datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
        print("EPS 추정치 리비전 (Yahoo earningsTrend · 무키 · 조회 %s)\n" % stamp)
        print_table(rows, args.period)
        print("\n※ 측정 전용 — 별점·스코어·트랜치·안전핀 어떤 룰도 바꾸지 않는다(매수 트리거 아님).")
        print("※ 점수는 부호 있는 -100~+100. 별점 밴드(0~100)와 다른 축이므로 섞어 쓰지 말 것.")
        print("※ 과거 시계열은 Yahoo가 주지 않는다 → --save로 오늘부터 누적해야 층화 검증이 가능해진다.")

    if args.save:
        print("\n저장: %s" % save(rows, args.period))

    # 수집 실패가 있으면 비-0 종료 — 조용한 결손 방지
    return 1 if any(r["status"] == FAIL for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
