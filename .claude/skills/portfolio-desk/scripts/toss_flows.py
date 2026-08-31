#!/usr/bin/env python3
"""toss_flows.py — 국내 종목 수급 4축 (토스 Open API) [2026-08-31 신설]

왜 필요한가
────────────────────────────────────────────────────────────────
공매도·대차 관측 축은 **KRX가 세션 가드로 막아** 계속 비어 있었다.
8/31 로컬 실측에서 그 진단이 확정됐다 — 포털 HTML은 200인데
`getJsonData.cmd`만 400 `LOGOUT`. IP가 아니라 세션 가드라 이전해도 안 열린다.
그래서 정본에서 "로컬 가면 열린다"를 지우고 축을 포기했는데,
**토스 Open API가 그걸 KRX보다 더 많이 준다**는 걸 같은 날 확인했다.

주는 것 4축 (전부 국내 종목·T+1 반영·최신은 전 영업일 기준)
  ① 공매도   /stocks/{code}/short-selling      거래량·거래대금·**비중**
  ② 대차거래 /stocks/{code}/securities-lending 체결·상환·**잔고**(기관 간)
  ③ 신용거래 /stocks/{code}/credit-trades      신용융자 + **신용대주**(개인 공매도)
  ④ 투자자별 /stocks/{code}/investor-trading   개인·외국인·기관 + **기관 7분류**
                                               (금융투자·보험·투신·사모·은행·기타금융·연기금)

④는 그동안 네이버·뉴스로 긁던 축의 **1차 출처 대체재**다. 특히 기관 7분류는
"기관 순매도"를 연기금인지 사모인지로 갈라준다 — 뭉뚱그리면 해석이 안 된다.

⚠️ **측정 전용.** 안전핀·트랜치·별점 어떤 룰도 바꾸지 않는다. `vol_gauge`·
   `naver_sentiment`와 같은 층위다. 비중 %ile은 그 둘과 **같은 %ile 문법**을 쓴다.
⚠️ **조회 전용.** 요청은 전부 toss_snapshot.req 를 거치고, 거기 `_assert_readonly()`가
   GET + POST /oauth2/token 외를 예외로 막는다(주문 차단 가드 재사용).
⚠️ 데이터 적시성 = **T+1**. 장중에 부르면 최신 행이 전 영업일이거나, 당일 행이
   장 마감 직후(15:30~) 갱신된다. `updatedAt`을 항상 같이 본다.

사용법
  python3 toss_flows.py                    # 보유5 + 워치 요약
  python3 toss_flows.py --codes 005930,000660
  python3 toss_flows.py --save             # data/app/toss_flows.json 저장
  python3 toss_flows.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(REPO, "data", "app", "toss_flows.json")
sys.path.insert(0, HERE)

# 보유 국내 5 + 국내 워치. 토스는 접미사 없는 6자리 코드를 쓴다.
HOLDINGS = [("005930", "삼성전자"), ("066570", "LG전자"), ("454910", "두산로보틱스"),
            ("005380", "현대차"), ("035420", "NAVER")]
WATCH = [("000660", "SK하이닉스"), ("240810", "원익IPS"), ("095610", "테스"),
         ("034020", "두산에너빌리티"), ("009150", "삼성전기"), ("096770", "SK이노베이션")]

PACE = 0.35   # 초. STOCK_TRADING_TREND 레이트리밋 회피(셸 sleep은 이 환경에서 막힘 → time.sleep)


def _client():
    """토큰 발급. 키는 환경변수(로컬 저장 — 정훈 8/31 승인, 주문 가드 전제)."""
    from toss_snapshot import req, make_ctx
    cid = os.environ.get("TOSS_CLIENT_ID")
    sec = os.environ.get("TOSS_CLIENT_SECRET")
    if not cid or not sec:
        raise SystemExit("TOSS_CLIENT_ID / TOSS_CLIENT_SECRET 환경변수가 없다 "
                         "(토스증권 WTS > 설정 > Open API · IP 허용목록 등록 필요)")
    ctx = make_ctx(False)
    tok = req("POST", "/oauth2/token", ctx, form=True, data={
        "grant_type": "client_credentials", "client_id": cid, "client_secret": sec})
    if not tok or "access_token" not in tok:
        raise SystemExit("토큰 발급 실패 — 키 또는 IP 허용목록 확인 "
                         "(403 access_denied면 공인 IP가 바뀐 것)")
    return ctx, {"Authorization": "Bearer " + tok["access_token"]}


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pct_rank(series: list[float], x: float) -> float | None:
    """x가 series 안에서 몇 %ile인지. vol_gauge·naver_sentiment와 같은 문법."""
    s = [v for v in series if v is not None]
    if len(s) < 5 or x is None:
        return None
    return round(sum(1 for v in s if v <= x) / len(s) * 100, 1)


def fetch_one(ctx, auth, code: str, label: str, count: int) -> dict:
    from toss_snapshot import req

    out = {"code": code, "label": label}

    def get(path):
        time.sleep(PACE)
        r = req("GET", path, ctx, headers=auth)
        return ((r or {}).get("result") or {}).get("records") or []

    # ① 공매도
    ss = get(f"/api/v1/stocks/{code}/short-selling?count={count}")
    if ss:
        rates = [_f(r.get("shortSellingVolumeRate")) for r in ss]
        latest = ss[0]
        out["short"] = {
            "date": latest.get("date"), "updated_at": latest.get("updatedAt"),
            "volume": _f(latest.get("shortSellingVolume")),
            "rate": _f(latest.get("shortSellingVolumeRate")),
            "avg_rate": round(sum(v for v in rates if v is not None)
                              / max(1, len([v for v in rates if v is not None])), 5),
            "pctile": _pct_rank(rates, _f(latest.get("shortSellingVolumeRate"))),
            "n": len(ss),
        }
    # ② 대차
    sl = get(f"/api/v1/stocks/{code}/securities-lending?count={count}")
    if sl:
        bal = [_f(r.get("balanceQuantity")) for r in sl]
        out["lending"] = {
            "date": sl[0].get("date"),
            "balance": bal[0],
            "chg_vs_prev": (bal[0] - bal[1]) if len(bal) > 1 and None not in bal[:2] else None,
            "pctile": _pct_rank(bal, bal[0]),
            "execution": _f(sl[0].get("executionQuantity")),
            "repayment": _f(sl[0].get("repaymentQuantity")),
            "n": len(sl),
        }
    # ③ 신용 (융자·대주)
    ct = get(f"/api/v1/stocks/{code}/credit-trades?count={count}")
    if ct:
        top = ct[0]
        ml = top.get("marginLoan") or {}
        st = top.get("stockLoan") or {}
        out["credit"] = {
            "date": top.get("date"),
            "margin_balance": _f(ml.get("balanceQuantity")),
            "stock_loan_balance": _f(st.get("balanceQuantity")),   # 신용대주 = 개인 공매도
        }
    # ④ 투자자별
    it = get(f"/api/v1/stocks/{code}/investor-trading?count={count}")
    if it:
        def net(rows, key):
            tot = 0.0
            for r in rows:
                v = _f((r.get(key) or {}).get("netBuyVolume"))
                if v is not None:
                    tot += v
            return tot
        d5 = it[:5]
        bd = (it[0].get("institution") or {}).get("breakdown") or {}
        out["investors"] = {
            "date": it[0].get("date"), "updated_at": it[0].get("updatedAt"),
            "today": {k: _f((it[0].get(k) or {}).get("netBuyVolume"))
                      for k in ("individual", "foreigner", "institution")},
            "net5": {k: net(d5, k) for k in ("individual", "foreigner", "institution")},
            "inst_breakdown_today": {k: _f((v or {}).get("netBuyVolume")) for k, v in bd.items()},
            "n": len(it),
        }
    return out


def render(rows: list[dict]) -> None:
    print("── 국내 수급 4축 (토스 Open API · T+1) ──")
    print("%-12s %8s %8s %7s %13s %12s %12s"
          % ("종목", "공매도%", "20d평균", "%ile", "대차잔고", "외인5d", "기관5d"))
    print("-" * 82)
    for r in rows:
        s = r.get("short") or {}
        l = r.get("lending") or {}
        i = r.get("investors") or {}
        n5 = i.get("net5") or {}

        def pct(v):
            return f"{v * 100:.2f}" if v is not None else "-"

        def big(v):
            return f"{v / 10000:,.1f}만" if v is not None else "-"
        print("%-12s %8s %8s %7s %13s %12s %12s" % (
            r["label"][:12], pct(s.get("rate")), pct(s.get("avg_rate")),
            (f"{s['pctile']:.0f}" if s.get("pctile") is not None else "-"),
            big(l.get("balance")), big(n5.get("foreigner")), big(n5.get("institution"))))
    print()
    # 눈에 띄는 것만 짚는다 — 측정 전용이므로 '경보'가 아니라 '관찰'로 쓴다
    for r in rows:
        s = r.get("short") or {}
        if s.get("pctile") is not None and s["pctile"] >= 90 and s.get("rate"):
            print(f"  ▸ {r['label']}: 공매도 비중 {s['rate'] * 100:.2f}% = "
                  f"최근 {s['n']}일 중 {s['pctile']:.0f}%ile (평균 {s['avg_rate'] * 100:.2f}%)")
        i = r.get("investors") or {}
        bd = i.get("inst_breakdown_today") or {}
        inst = (i.get("today") or {}).get("institution")
        # ⚠️ 임계 없이 찍으면 "bank -0.0만주" 같은 잡음이 매 종목 나온다(8/31 초판).
        #    기관이 실제로 순매도이고, 주도 분류가 그 절반 이상을 설명할 때만 짚는다.
        if bd and inst is not None and inst < -10000:
            worst = sorted(bd.items(), key=lambda kv: (kv[1] if kv[1] is not None else 0))[:1]
            if worst and worst[0][1] is not None and worst[0][1] <= inst * 0.3:
                share = worst[0][1] / inst * 100
                print(f"  ▸ {r['label']}: 기관 순매도 {inst / 10000:,.1f}만주 — "
                      f"주도 {worst[0][0]} {worst[0][1] / 10000:,.1f}만주({share:.0f}%)")
    print("\n⚠️ 측정 전용 — 어떤 룰(안전핀·트랜치·별점)도 이 수치로 바꾸지 않는다.")
    print("⚠️ T+1 반영 — 당일 행은 장 마감(15:30) 직후 갱신된다. updated_at 확인.")


def main() -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

    ap = argparse.ArgumentParser(description="국내 수급 4축 — 공매도·대차·신용·투자자별 (토스, 조회 전용)")
    ap.add_argument("--codes", help="쉼표 구분 6자리 코드(기본: 보유5+워치)")
    ap.add_argument("--holdings-only", action="store_true", help="보유 5종목만")
    ap.add_argument("--count", type=int, default=20, help="종목당 조회 일수(최대 100)")
    ap.add_argument("--save", action="store_true", help=f"{os.path.relpath(OUT, REPO)} 저장")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.codes:
        targets = [(c.strip(), c.strip()) for c in args.codes.split(",") if c.strip()]
    else:
        targets = HOLDINGS if args.holdings_only else HOLDINGS + WATCH

    ctx, auth = _client()
    rows = []
    for code, label in targets:
        try:
            rows.append(fetch_one(ctx, auth, code, label, min(args.count, 100)))
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] {label}({code}) 실패: {type(e).__name__} {e}", file=sys.stderr)

    payload = {"as_of": time.strftime("%Y-%m-%d %H:%M KST"), "source": "토스 Open API (조회 전용)",
               "caveat": "측정 전용 · T+1 반영 · 룰 변경 금지", "rows": rows}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        render(rows)
    if args.save:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        print(f"\n저장: {os.path.relpath(OUT, REPO)} ({len(rows)}종목)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
