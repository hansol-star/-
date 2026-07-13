#!/usr/bin/env python3
"""missed_moves.py — 결정 후행회고: 안 산/안 판 결정의 반사실(counterfactual) 채점

배경: self-review(score_calls.py)는 **내가 실제로 내린 콜**(별점·목표가·매수존)이 맞았나만 채점한다.
그러나 실전 손익의 절반은 **하지 않은 행동**에서 난다 — "관망·보류·홀딩·추격 금지"라고 판단했는데
그 뒤 크게 오르거나(놓친 매수) 내린(놓친 매도/트림) 종목. 워치에만 두고 안 들어갔는데 급등한 종목.
이 **누락(omission)**은 지금 어떤 스크립트도 추적하지 않는다 → 이 스크립트가 그 사각을 채운다.

핵심 통찰(score_calls와 동일): data/app/stocks.json 의 git 히스토리 = 결정의 시계열.
각 종목이 처음 관측된 시점(관망/홀딩/워치 등록)을 '결정 시점'으로 잡고, 그 이후 Yahoo 시세 경로에서
최고 상승(fwd_max)·최저 하락(fwd_min)을 뽑아 "그때 샀으면/팔았으면"을 정량화한다.

  python3 missed_moves.py                    # 놓친 매수·매도 후보 + 반복 패턴(콘솔 표)
  python3 missed_moves.py --min-move 20      # 임계값 조정(기본 15%)
  python3 missed_moves.py --since 2026-06-20 # 결정 시점 하한(그 이후 등록분만)
  python3 missed_moves.py --json             # 기계가독(에이전트가 검증 후 missed_moves.jsonl 기입)

의존성 없음(stdlib + score_calls.py 재사용). 시세는 Yahoo 무키 일봉(네트워크 필요).
FAIL 안 냄 — 회고·캘리브레이션 보조. 원장 기입·교훈 확정은 사람(에이전트) 판단(자동 변경 ❌).
※ 결과론 함정 경계: 표본·기간(horizon) 명시, 단기 노이즈(noise)와 진짜 미스(miss) 구분,
  '올바른 무행동(good_inaction)'도 함께 집계해 무행동이 운인지 실력인지 균형있게 본다.
"""
import argparse, json, os, re, sys
from datetime import datetime, date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)

# score_calls의 검증된 프리미티브 재사용(DRY): git 타임머신 + Yahoo 시세 경로 + 가격 레벨 추출
from score_calls import (today_kst, series, close_on_or_after, path_from,
                         git_commits, stocks_at)

STOCKS_REL = "data/app/stocks.json"
DECISIONS_REL = "data/app/decisions.jsonl"
LEDGER_REL = "data/app/missed_moves.jsonl"
ETF = {"VOO"}

# ── 결정 시그널 사전 ──────────────────────────────────────────────────────
# 안 사는(매수 누락) 판단 vs 안 파는(매도 누락) 판단을 텍스트에서 뽑는다.
NO_BUY_KW = ("관망", "보류", "추격 금지", "추격금지", "진입금지", "진입 금지", "신규매수 안함", "신규 보류")
NO_SELL_KW = ("홀딩", "물타기 금지", "물타기금지", "패닉셀 금지", "패닉셀금지",
              "손절선 없음", "손절선 영구 폐기", "인내", "정리후보")

# ── 클러스터(반복 편향 집계용) ────────────────────────────────────────────
CLUSTER = {
    "메모리·AI하드웨어": {"005930.KS", "000660.KS", "MU", "AVGO", "ANET",
                          "240810.KQ", "095610.KQ", "STM", "005070.KS"},
    "국내수급민감 대형": {"005930.KS", "000660.KS", "005380.KS", "035420.KS"},
    "급등주·모멘텀":     {"454910.KS", "TSLA", "SPCX", "IONQ", "PLTR", "IBM"},
    "전력·피지컬AI":     {"066570.KS", "GEV", "034020.KS", "011070.KS",
                          "042660.KS", "096770.KS", "012450.KS", "010140.KS", "329180.KS"},
    "빅테크·플랫폼":     {"META", "MSFT", "AAPL", "GOOGL", "ORCL", "NAVER",
                          "035420.KS", "TMUS", "033780.KS"},
}
def clusters_of(ticker):
    tags = [name for name, mem in CLUSTER.items() if ticker in mem]
    return tags or ["기타"]


def sig_from(v, is_watch):
    """종목 스냅샷 → 결정 시그널. (no_buy, no_sell, label, rule_blocked)"""
    bz = str(v.get("buy_zone") or "")
    trim = str(v.get("trim") or "")
    comment = str(v.get("comment") or "")
    text = " ".join([bz, trim, comment])
    rule_blocked = ("진입금지" in text) or ("진입 금지" in text) or ("상장 전" in text)
    if is_watch:
        # 워치 = 미보유 후보. 룰차단(상장 전 등)만 아니면 '안 산' 결정으로 본다.
        label = "워치미진입(룰차단)" if rule_blocked else "워치미진입"
        return (True, False, label, rule_blocked)
    no_buy = any(k in text for k in NO_BUY_KW)
    no_sell = any(k in text for k in NO_SELL_KW)
    # 라벨 = 대표 시그널(표시용)
    label = (bz.strip()[:14] or trim.strip()[:14] or "—")
    return (no_buy, no_sell, label, rule_blocked)


def build_history(since):
    """git 히스토리 순회 → 종목별 {first_date, first_val, last_val, is_watch}."""
    hist = {}
    for h, dt in reversed(git_commits()):        # 과거→현재
        if since and dt < since:
            continue
        sj = stocks_at(h)
        if not sj:
            continue
        buckets = [("stocks", False), ("watchlist", True)]
        for key, is_watch in buckets:
            for tk, v in (sj.get(key) or {}).items():
                if tk in ETF:
                    continue
                rec = hist.setdefault(tk, {"first_date": dt, "is_watch": is_watch,
                                            "first_val": v})
                # 워치→보유 승격 시 최종 상태는 보유로 갱신
                rec["last_val"] = v
                rec["last_is_watch"] = is_watch
    return hist


def analyze(min_move, since):
    hist = build_history(since)
    today = today_kst()  # [7/13] KST 실측 (score_calls 공용 헬퍼)
    rows, net_err = [], []
    for tk, rec in hist.items():
        d0 = rec["first_date"]
        ser = series(tk)
        if "__error__" in ser:
            net_err.append(tk); continue
        ref = close_on_or_after(ser, d0)
        path_days = [k for k in sorted(ser) if not k.startswith("__") and k >= d0]
        path = [ser[k] for k in path_days]
        if not ref or not path:
            continue
        pnow = path[-1]
        pmax, pmin = max(path), min(path)
        fwd_max = (pmax - ref) / ref * 100
        fwd_min = (pmin - ref) / ref * 100
        fwd_now = (pnow - ref) / ref * 100
        peak_date = path_days[path.index(pmax)]
        trough_date = path_days[path.index(pmin)]
        horizon = (today - datetime.fromisoformat(d0).date()).days

        is_watch = rec.get("last_is_watch", rec["is_watch"])
        no_buy, no_sell, label, blocked = sig_from(rec.get("last_val", rec["first_val"]), is_watch)

        cand = {
            "ticker": tk, "decision_at": d0, "horizon_d": horizon,
            "ref_price": round(ref, 2), "signal": label, "is_watch": is_watch,
            "rule_blocked": blocked, "fwd_max": round(fwd_max, 1),
            "fwd_min": round(fwd_min, 1), "fwd_now": round(fwd_now, 1),
            "peak_date": peak_date, "trough_date": trough_date,
            "clusters": clusters_of(tk),
        }
        # 분류: 안 샀는데 급등 / 안 팔았는데 급락 / 올바른 무행동
        if no_buy and fwd_max >= min_move:
            rows.append({**cand, "type": "놓친매수", "severity": round(fwd_max, 1),
                         "note": f"{d0} {label} → {peak_date} +{fwd_max:.0f}% 고점"})
        if no_sell and fwd_min <= -min_move:
            rows.append({**cand, "type": "놓친매도", "severity": round(abs(fwd_min), 1),
                         "note": f"{d0} {label} → {trough_date} {fwd_min:.0f}% 저점"})
        # 올바른 무행동(결과론 함정 견제): 관망했는데 실제 빠짐 / 홀딩했는데 실제 오름
        if no_buy and fwd_min <= -min_move and fwd_max < min_move:
            rows.append({**cand, "type": "잘참음", "severity": round(abs(fwd_min), 1),
                         "note": f"관망 후 {fwd_min:.0f}% 하락 = 안 사길 잘함"})
        elif no_sell and fwd_now >= min_move:
            rows.append({**cand, "type": "잘홀딩", "severity": round(fwd_now, 1),
                         "note": f"홀딩 유지 후 현재 +{fwd_now:.0f}% = 안 팔길 잘함"})
    return rows, sorted(set(net_err))


def match_rejected(ticker):
    """decisions.jsonl에서 이 종목이 언급된 '기각된 대안'을 찾아 병기(반사실 힌트)."""
    p = os.path.join(ROOT, DECISIONS_REL)
    if not os.path.exists(p):
        return []
    out = []
    base = ticker.split(".")[0]
    for ln in open(p, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        blob = " ".join(str(d.get(k, "")) for k in ("topic", "decision", "rejected"))
        if base and base in blob and d.get("rejected"):
            out.append({"date": d.get("date"), "rejected": d.get("rejected")})
    return out


def report(rows, net_err, min_move):
    print("\n" + "=" * 68)
    print(f"  결정 후행회고 — missed_moves.py  (임계 ±{min_move}%)")
    print("=" * 68)
    if not rows:
        print("\n임계 초과 미스무브 없음(또는 채점 성숙 콜 부족). 원장은 계속 누적됨.")
        if net_err:
            print(f"시세 조회 실패: {net_err}")
        return

    order = {"놓친매수": 0, "놓친매도": 1, "잘참음": 2, "잘홀딩": 3}
    for typ in ("놓친매수", "놓친매도", "잘참음", "잘홀딩"):
        sub = sorted([r for r in rows if r["type"] == typ],
                     key=lambda r: -r["severity"])
        if not sub:
            continue
        head = {"놓친매수": "🔺 놓친 매수 (안 샀는데 급등 — '그때 살걸')",
                "놓친매도": "🔻 놓친 매도/트림 (안 팔았는데 급락 — '그때 팔걸')",
                "잘참음": "✅ 올바른 무행동 — 관망 후 하락(안 사길 잘함)",
                "잘홀딩": "✅ 올바른 무행동 — 홀딩 후 상승(안 팔길 잘함)"}[typ]
        print(f"\n{head}")
        print(f"  {'종목':<12}{'결정':<9}{'기간':>5}{'최고%':>8}{'최저%':>8}{'현재%':>8}  근거")
        for r in sub:
            print(f"  {r['ticker']:<12}{r['signal'][:8]:<9}{r['horizon_d']:>4}d"
                  f"{r['fwd_max']:>+8.0f}{r['fwd_min']:>+8.0f}{r['fwd_now']:>+8.0f}  {r['note']}")

    # ── 반복 패턴·편향 집계(클러스터별 미스 카운트) ──────────────────────
    print("\n— 반복 패턴·편향 (클러스터별 미스 집계) —")
    miss = [r for r in rows if r["type"] in ("놓친매수", "놓친매도")]
    ccount = {}
    for r in miss:
        for c in r["clusters"]:
            ccount.setdefault(c, {"놓친매수": 0, "놓친매도": 0})
            ccount[c][r["type"]] += 1
    for c, d in sorted(ccount.items(), key=lambda x: -(x[1]["놓친매수"] + x[1]["놓친매도"])):
        print(f"  {c:<18} 놓친매수 {d['놓친매수']} · 놓친매도 {d['놓친매도']}")

    # 기각된 대안 병기(반사실 힌트)
    rej_shown = set()
    lines = []
    for r in miss:
        for rj in match_rejected(r["ticker"]):
            key = (r["ticker"], rj["date"])
            if key in rej_shown:
                continue
            rej_shown.add(key)
            lines.append(f"  {r['ticker']} · {rj['date']} 기각: {rj['rejected'][:60]}")
    if lines:
        print("\n— 그때 기각한 대안(decisions.jsonl) — 반사실로 재검토 —")
        for l in lines[:12]:
            print(l)

    if net_err:
        print(f"\n  시세 조회 실패(회고 제외): {net_err}")
    print("\n※ 결과론 함정 경계 — 표본·기간 명시, noise vs miss 구분. 자동 변경 없음(교정은 사람 판단).")
    print("※ 검증 후 missed_moves.jsonl 기입 + hindsight_log.md 회고 블록 prepend(self-review Step 6).\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-move", type=float, default=15.0, help="미스 임계 %% (기본 15)")
    ap.add_argument("--since", type=str, default=None, help="결정 시점 하한 YYYY-MM-DD")
    ap.add_argument("--json", action="store_true", help="기계가독 출력")
    a = ap.parse_args()
    rows, net_err = analyze(a.min_move, a.since)
    if a.json:
        print(json.dumps({"min_move": a.min_move, "since": a.since,
                          "candidates": rows, "net_err": net_err},
                         ensure_ascii=False, indent=1))
    else:
        report(rows, net_err, a.min_move)


if __name__ == "__main__":
    main()
