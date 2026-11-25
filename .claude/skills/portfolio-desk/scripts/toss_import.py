#!/usr/bin/env python3
"""toss_import.py — 토스 체결 이력 -> 체결 원장(trades.jsonl) 재구성 [2026-08-31 신설]

왜 필요한가
────────────────────────────────────────────────────────────────
8/23에 원장을 정본으로 세웠지만 재료가 반쪽이었다:
  · 체결(buy/sell) 12건  = 데스크 착수(6/13) 이후 산문에서 복원한 것
  · opening 기초잔고      = 그 이전 보유분을 "이미 있던 것"으로 뭉갠 것
  · closed 31건          = 토스 **실현손익 화면** 스크린샷에서 옮긴 것.
                           화면이 주수·단가를 안 줘서 실현액만 기록했다.
그래서 **현재 보유분의 취득일·취득단가·취득환율이 전부 미상**이었고
(`fx_cost_coverage` 13.3%), `us_avg_fx_cost`는 추정치 1,456.5원이었다.

8/31 토스 Open API 연결로 **체결 286건(2024-07-08~)** 원본이 들어왔다.
체결가·수량·수수료·세금·체결시각·통화가 전부 있다 -> 추정이 실측으로 바뀐다.

무엇을 하나
  ① 토스 주문이력 JSON(toss_snapshot.py --orders)을 원장 스키마로 변환
  ② 재생 결과를 **토스 보유 API와 대조**(수량·평단) — 이게 검증 게이트다
  ③ --write 로만 원장을 갈아끼운다(기본은 dry-run). 기존 원장은 .bak 로 백업

⚠️ 왜 opening/closed 를 버리는가
  새 체결이 2024-07-08부터 전 구간을 덮으므로, opening(기초잔고)과
  closed(실현손익만 기록)를 같이 두면 **실현손익이 이중 계상**된다.
  실현손익은 이제 체결에서 직접 계산된다.

⚠️ 환율은 여전히 근사다 — fx_rate는 체결일 **시장 종가**(trades.fx_on)이지
   토스가 실제 적용한 환율이 아니다(스프레드·체결시각 차이). 다만 舊 "오늘 환율로
   전 구간 환산"보다는 훨씬 정확하다. fx_source에 근거를 남긴다.

사용법
  python3 toss_snapshot.py --orders > orders.json
  python3 toss_import.py --orders orders.json              # dry-run(대조만)
  python3 toss_import.py --orders orders.json --write      # 원장 교체
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
LEDGER = os.path.join(REPO, "data", "app", "trades.jsonl")
sys.path.insert(0, HERE)

QTY_TOL = 1e-6

# 국내 6자리 코드 -> 우리 표기(접미사 포함).
# ⚠️ 접미사가 다르면 다른 회사다(7/30 사고) — market_data.py 기준과 일치시킬 것.
# ★[2026-11-22 감사 A11] 아래 손 목록은 **시드**일 뿐이다. 舊엔 이것만 봐서 국내 워치(삼성전기 009150·
#   KT&G 033780·셀트리온 068270)를 사는 날 원장 수입이 [중단]됐다(fail-closed라 안전하지만 체결 원장 공백 경로 —
#   10/22 ANET 7일 누락과 같은 꼴). 이제 kr_suffix()가 정본(portfolio.json 보유·워치·퇴역 워치 + 체결 원장)에서
#   접미사를 만들어 이 시드와 합친다. 같은 코드가 .KS·.KQ로 갈리면 중단, 정본 어디에도 없는 코드(유니버스 밖 체결)도
#   계속 중단한다 — 접미사를 찍어서 넣지 않는다.
KR_SUFFIX = {
    "000660": ".KS",   # SK하이닉스
    "005380": ".KS",   # 현대차
    "005930": ".KS",   # 삼성전자
    "034020": ".KS",   # 두산에너빌리티
    "035420": ".KS",   # NAVER
    "035720": ".KS",   # 카카오
    "066570": ".KS",   # LG전자
    "122870": ".KQ",   # 와이지엔터테인먼트 (코스닥)
    "454910": ".KS",   # 두산로보틱스
}
# 토스 표기 -> 우리 표기 (미국)
US_ALIAS = {"BRK.B": "BRK-B"}

_KR_MAP: dict[str, str] | None = None


def kr_suffix(portfolio: str | None = None, ledger: str | None = None) -> dict[str, str]:
    """정본 파생 맵 ∪ 시드(KR_SUFFIX). 둘이 같은 코드에서 갈리면 SystemExit(어느 쪽이 맞는지 기계가 고르지 않는다).
    market_data를 못 읽으면 시드만 쓴다(경고) — 그때 모르는 코드는 지금처럼 중단된다."""
    derived: dict[str, str] = {}
    try:
        import market_data as _md
        derived = _md.kr_suffix_map(portfolio, ledger)
    except ValueError as e:
        raise SystemExit(f"[중단] 국내 접미사 정본이 갈린다 — {e}")
    except Exception as e:                                 # noqa: BLE001
        print(f"⚠️ 국내 접미사 정본(market_data.kr_suffix_map) 로드 실패 — 시드 목록만 쓴다: {e}", file=sys.stderr)
    bad = {c: (KR_SUFFIX[c], v) for c, v in derived.items() if c in KR_SUFFIX and KR_SUFFIX[c] != v}
    if bad:
        raise SystemExit(f"[중단] 시드 KR_SUFFIX와 정본의 접미사가 갈린다 — {bad} (7/30 사고 유형 · 원문 확인 후 한쪽을 고칠 것)")
    return {**KR_SUFFIX, **derived}


def to_ticker(symbol: str, country: str) -> str:
    global _KR_MAP
    if country == "KR" or (symbol.isdigit() and len(symbol) == 6):
        if _KR_MAP is None:
            _KR_MAP = kr_suffix()
        suf = _KR_MAP.get(symbol)
        if suf is None:
            raise SystemExit(
                f"[중단] 국내 종목 {symbol} 의 접미사를 모른다. portfolio.json(보유·워치·watch_retired)에 "
                "정확한 티커로 등록하거나 KR_SUFFIX 시드에 넣을 것 — "
                "접미사를 찍어서 넣으면 남의 종목을 담는다(7/30 사고)."
            )
        return symbol + suf
    return US_ALIAS.get(symbol, symbol)


def selftest() -> int:
    """★[2026-11-22 감사 A11] 오프라인 — 임시 portfolio·원장을 심어 접미사 맵을 검증한다."""
    import tempfile
    global _KR_MAP
    ok = True

    def check(cond, label):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  {'✅' if cond else '❌'} {label}")

    print("toss_import 자가검증 — 국내 접미사 = 정본 파생")
    keep = _KR_MAP
    try:
        with tempfile.TemporaryDirectory() as td:
            pp, lp = os.path.join(td, "p.json"), os.path.join(td, "t.jsonl")
            pf = {"holdings": {"kr": [{"label": "삼성전자", "ticker": "005930.KS"}], "us": []},
                  "watchlist": [{"label": "KT&G", "ticker": "033780.KS"}, {"label": "셀트리온", "ticker": "068270.KS"},
                                {"label": "삼성전기", "ticker": "009150.KS"}],
                  "watch_retired": [{"label": "원익IPS", "ticker": "240810.KQ"}]}
            with open(pp, "w", encoding="utf-8") as f:
                json.dump(pf, f, ensure_ascii=False)
            with open(lp, "w", encoding="utf-8") as f:
                f.write(json.dumps({"date": "2026-01-02", "ticker": "122870.KQ", "label": "122870",
                                    "side": "buy", "shares": 1}) + "\n")
            _KR_MAP = kr_suffix(pp, lp)
            check(to_ticker("068270", "KR") == "068270.KS" and to_ticker("033780", "KR") == "033780.KS"
                  and to_ticker("009150", "KR") == "009150.KS", "국내 워치 3종(셀트리온·KT&G·삼성전기)을 사도 수입이 멈추지 않는다")
            check(to_ticker("240810", "KR") == "240810.KQ", "퇴역 워치 .KQ 접미사 그대로(원익IPS)")
            check(to_ticker("BRK.B", "US") == "BRK-B" and to_ticker("NVDA", "US") == "NVDA", "미국 표기 그대로")
            try:
                to_ticker("999999", "KR")
                check(False, "유니버스 밖 국내 코드는 중단")
            except SystemExit:
                check(True, "유니버스 밖 국내 코드는 계속 중단(접미사를 찍지 않는다)")
            with open(lp, "a", encoding="utf-8") as f:
                f.write(json.dumps({"date": "2026-11-21", "ticker": "033780.KQ", "side": "buy", "shares": 1}) + "\n")
            try:
                kr_suffix(pp, lp)
                check(False, "같은 코드가 .KS·.KQ로 갈리면 중단")
            except SystemExit:
                check(True, "같은 코드가 .KS·.KQ로 갈리면 중단")
            pf["watchlist"].append({"label": "가짜", "ticker": "122870.KS"})     # 시드(.KQ)와 정본(.KS) 충돌
            with open(pp, "w", encoding="utf-8") as f:
                json.dump(pf, f, ensure_ascii=False)
            with open(lp, "w", encoding="utf-8") as f:
                f.write("")
            try:
                kr_suffix(pp, lp)
                check(False, "시드와 정본이 갈리면 중단")
            except SystemExit:
                check(True, "시드와 정본이 갈리면 중단")
        _KR_MAP = None
        real = kr_suffix()
        check(all(real.get(c) == v for c, v in KR_SUFFIX.items()), "실제 정본 = 시드와 충돌 없음")
        check(all(c in real for c in ("009150", "033780", "068270")), "실제 정본에 국내 워치 3종 접미사가 있다")
    finally:
        _KR_MAP = keep
    print("✅ 통과" if ok else "❌ 실패")
    return 0 if ok else 1


def convert(orders: list[dict], src_note: str) -> list[dict]:
    """토스 체결 -> 원장 행. orderId로 중복 제거."""
    from trades import fx_on

    seen: set[str] = set()
    rows: list[dict] = []
    for o in orders:
        if o.get("status") != "FILLED":
            continue
        oid = o.get("orderId") or ""
        if oid in seen:
            continue
        seen.add(oid)
        ex = o.get("execution") or {}
        sh = float(ex.get("filledQuantity") or 0)
        if sh <= 0:
            continue
        # 체결 시각이 정본. 없으면 주문 시각으로 내려간다(둘 다 KST 오프셋 포함).
        stamp = ex.get("filledAt") or o.get("orderedAt") or ""
        date = stamp[:10]
        cur = o.get("currency") or "KRW"
        row = {
            "date": date,
            "ticker": to_ticker(o.get("symbol", ""), o.get("marketCountry", "")),
            "label": o.get("symbol"),
            "side": "buy" if o.get("side") == "BUY" else "sell",
            "shares": sh,
            "price": float(ex.get("averageFilledPrice") or 0) or None,
            "amount": float(ex.get("filledAmount") or 0),
            "currency": cur,
            "fee": float(ex.get("commission") or 0),
            "tax": float(ex.get("tax") or 0),
            "order_id": oid,
            "filled_at": stamp,
            "source": src_note,
        }
        if cur == "USD":
            fx, fxs = fx_on(date)
            row["fx_rate"] = fx
            row["fx_source"] = fxs or "unknown"
        else:
            row["fx_rate"] = 1.0
            row["fx_source"] = "krw"
        rows.append(row)
    rows.sort(key=lambda r: (r["date"], r.get("filled_at") or "", r["ticker"]))
    return rows


def residual_rows(rows: list[dict], truth: dict, first_date: str) -> list[dict]:
    """주문 이력으로 설명 안 되는 보유분을 **별도 종류(opening)**로 명시한다.

    왜 필요한가 [8/31]: AAPL 체결 27건을 다 더하면 순수량이 **-0.005488주**로 음수다.
    물리적으로 불가능하다 = 주문 이력에 없는 취득 경로가 있다는 뜻이다
    (토스 주식 선물·이벤트 리워드 등은 /api/v1/orders에 안 잡힌다).
    symbol 필터로 재조회해도 같은 27건이라 **페이징 누락이 아님을 확인**했다.

    ⚠️ 이걸 체결(buy)로 위장하면 "언제 얼마에 샀다"는 없는 사실을 만드는 것이다.
       side="opening"(기초 보유분)으로 두고, 단가는 **토스가 보고하는 현재 평단**을
       대용치로 쓴다(관측이 아니라 대용치임을 note에 박는다).
    """
    from trades import replay
    book = replay(rows)

    # 목표 수량 = 현재 보유(truth)면 그 값, 청산된 종목이면 0.
    # ⚠️ 초판은 truth만 돌아서 **청산 종목의 결손을 놓쳤다** — TSLA가 -0.007012로 남아
    #    trades --reconcile이 FAIL했다. 보유 목록에 없는 종목이야말로 대조에서 빠지기 쉽다.
    targets: dict[str, tuple[float, float | None, str | None]] = {}
    for tk, (t_sh, t_av, name) in truth.items():
        targets[tk] = (t_sh, t_av, name)
    for tk, pos in book.items():
        if tk not in targets and float(pos.get("shares") or 0) < -1e-6:
            targets[tk] = (0.0, None, pos.get("label"))

    def _avg_buy(tk: str) -> float:
        """그 종목 매수 체결의 금액가중 평균가 — 청산 종목의 대용 단가."""
        amt = sum(float(r.get("amount") or 0) for r in rows
                  if r["ticker"] == tk and r["side"] == "buy")
        sh = sum(float(r.get("shares") or 0) for r in rows
                 if r["ticker"] == tk and r["side"] == "buy")
        return (amt / sh) if sh else 0.0

    out = []
    for tk, (t_sh, t_av, name) in sorted(targets.items()):
        b_sh = float(book.get(tk, {}).get("shares") or 0)
        gap = t_sh - b_sh
        if abs(gap) < 1e-6:
            continue
        if gap < 0:
            print(f"  ⚠️ {tk}: 재생이 목표보다 {-gap:.6f}주 많다 — 매도 누락 의심. 자동 보정 안 함.")
            continue
        if t_av is None:
            t_av = _avg_buy(tk)
        out.append({
            "date": first_date,
            "ticker": tk,
            "label": name,
            "side": "opening",
            "shares": round(gap, 8),
            "price": t_av,
            "amount": round(gap * t_av, 6),
            "currency": "USD" if not tk[:1].isdigit() else "KRW",
            "fee": 0.0, "tax": 0.0,
            "fx_rate": None, "fx_source": "unknown",
            "source": "대사 잔차 — 토스 주문이력(GET /api/v1/orders)으로 설명되지 않는 보유분",
            "note": ("주문 외 취득 경로 추정(주식 선물·이벤트 등). 체결이 아니므로 buy로 쓰지 않는다. "
                     "단가는 대용치(보유중=토스 보고 평단 / 청산=자기 매수 가중평균)이지 관측된 취득가가 아니다."),
            "derived": True,
        })
        print(f"  ▸ 잔차 보정: {tk} {gap:+.6f}주 (opening, 단가 대용 {t_av})")
    return out


def toss_positions(snapshot: dict) -> dict:
    """토스 보유 API 응답 -> {ticker: (수량, 평단)}"""
    out = {}
    for i in ((snapshot.get("result") or {}).get("items") or []):
        tk = to_ticker(i.get("symbol", ""), i.get("marketCountry", ""))
        out[tk] = (float(i.get("quantity") or 0),
                   float(i.get("averagePurchasePrice") or 0),
                   i.get("name"))
    return out


def compare(book: dict, truth: dict) -> tuple[list[str], int, int]:
    """재생 결과 vs 토스 실보유. 이 대조가 임포트의 검증 게이트다."""
    lines, ok, bad = [], 0, 0
    tickers = sorted(set(book) | set(truth))
    lines.append("%-11s %-14s %14s %14s %12s %12s  %s"
                 % ("티커", "이름", "재생수량", "토스수량", "재생평단", "토스평단", "판정"))
    lines.append("-" * 108)
    for tk in tickers:
        b = book.get(tk)
        t = truth.get(tk)
        b_sh = float(b["shares"]) if b else 0.0
        b_av = float(b["avg_cost"]) if b else 0.0
        if not t:
            if b_sh <= QTY_TOL:
                continue   # 양쪽 다 0 = 청산 완료, 정상
            lines.append("%-11s %-14s %14.6f %14s %12.2f %12s  ❌ 토스엔 없음"
                         % (tk, (b or {}).get("label", ""), b_sh, "-", b_av, "-"))
            bad += 1
            continue
        t_sh, t_av, name = t
        # 수량은 사실상 정확히 맞아야 하고, 평단은 반올림·수수료 처리로 소폭 차이 가능
        sh_ok = abs(b_sh - t_sh) < 1e-4
        av_ok = (abs(b_av - t_av) / t_av < 0.01) if t_av else True
        mark = "✅" if (sh_ok and av_ok) else ("⚠️ 평단차" if sh_ok else "❌ 수량불일치")
        if sh_ok and av_ok:
            ok += 1
        else:
            bad += 1
        lines.append("%-11s %-14s %14.6f %14.6f %12.2f %12.2f  %s"
                     % (tk, (name or "")[:14], b_sh, t_sh, b_av, t_av, mark))
    return lines, ok, bad


def main() -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

    ap = argparse.ArgumentParser(description="토스 체결 이력 -> 체결 원장 재구성")
    ap.add_argument("--orders", help="toss_snapshot.py --orders 출력 JSON (필수 — --selftest 제외)")
    ap.add_argument("--holdings", help="보유 대조용 JSON(없으면 대조 생략)")
    ap.add_argument("--write", action="store_true", help="원장을 실제로 교체(기본 dry-run)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="오프라인 자가검증 — 국내 접미사 맵(정본 파생)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.orders:
        ap.error("--orders가 필요하다")

    with open(args.orders, encoding="utf-8") as f:
        payload = json.load(f)
    orders = payload.get("orders") if isinstance(payload, dict) else payload
    src = ("토스 Open API GET /api/v1/orders?status=CLOSED "
           "(2026-08-31 수집, 조회 전용 · orderId 단위 원본 체결)")
    rows = convert(orders, src)
    print(f"■ 변환: 체결 {len(rows)}행 · 기간 {rows[0]['date']} ~ {rows[-1]['date']}")
    n_fx = sum(1 for r in rows if r["currency"] == "USD" and r.get("fx_rate"))
    n_usd = sum(1 for r in rows if r["currency"] == "USD")
    print(f"  환율 매칭 {n_fx}/{n_usd} USD 체결 (체결일 시장 종가 — 토스 적용환율 아님)")

    from trades import replay

    if args.holdings:
        with open(args.holdings, encoding="utf-8") as f:
            truth = toss_positions(json.load(f))
        extra = residual_rows(rows, truth, rows[0]["date"])
        if extra:
            rows = sorted(rows + extra,
                          key=lambda r: (r["date"], 0 if r["side"] == "opening" else 1,
                                         r.get("filled_at") or "", r["ticker"]))
        book = replay(rows)
        lines, ok, bad = compare(book, truth)
        print("\n■ 재생 결과 vs 토스 실보유 (검증 게이트)")
        print("\n".join(lines))
        print(f"\n  일치 {ok} · 불일치 {bad}")
        if bad:
            print("\n🔴 불일치가 있다 — 원장을 갈아끼우지 않는다. 원인부터 밝힐 것.")
            if args.write:
                return 1

    if not args.write:
        print("\n(dry-run — 원장은 안 건드렸다. 교체하려면 --write)")
        return 0

    if os.path.exists(LEDGER):
        bak = LEDGER + ".bak"
        shutil.copy2(LEDGER, bak)
        print(f"\n백업: {os.path.basename(bak)}")
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as f:
        f.write("// 체결 원장 — 정본. 토스 Open API 체결 이력에서 재구성 (2026-08-31).\n")
        f.write("// opening/closed 행은 폐기: 새 체결이 2024-07-08부터 전 구간을 덮으므로\n")
        f.write("// 같이 두면 실현손익이 이중 계상된다.\n")
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"원장 교체 완료: {len(rows)}행")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
