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
import argparse, json, os, re, subprocess, sys
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
# ★[8/22 전면 수정] 8/22 감사에서 오미션 검출이 2건뿐이라 "no_sell 트랙이 비었다"고 진단했는데,
#   실제 원인은 **트랙 부재가 아니라 ①키워드 미스매치 ②분류 오류** 둘이었다.
#     ① 실제 표기는 "물타기 **영구**금지"·"추가매수 **영구**금지"·"신규매수 **금지**"인데
#        키워드는 "물타기 금지"·"신규매수 **안함**"이라 **한 건도 안 걸렸다**
#        (= 8/12 "쓰는 쪽과 읽는 쪽이 갈리면 데이터가 조용히 사라진다"의 재현).
#     ② **"물타기 금지"가 NO_SELL_KW에 들어 있었다** — 물타기(추가매수) 금지는 '안 판다'가
#        아니라 **'안 산다'**다. 분류가 반대로 박혀 no_buy 집계도 같이 오염됐다.
#   ⇒ 문자열 상수 대신 **정규식**으로 바꿔 표기 변형(영구·永久·공백 유무)을 흡수한다.
# ★[10/14] 같은 실패가 세 번째로 났다 — 10/13에 MU 카드를 "룰4 = 홀딩"에서 "첫 둔화 = 중립(보유 유지·증액 없음)"으로
#   바꾸자 (no_buy, no_sell)이 (None, '홀딩') → (None, None)이 됐다. '안 판다·안 늘린다'는 결정(d243)인데
#   이 사전에 그 표현이 없어서, MU가 더 빠져도 그 결정의 반사실 채점 행이 생기지 않을 뻔했다(검토에서 발견).
#   ⇒ "보유 유지"·"잔여 보유"·"보유(d210 …" 꼴(안 판다)을 넣고, 사전을 `--selftest`로 못박는다.
#   카드 문구를 새로 쓸 때는 이 사전에 걸리는지 `--selftest`의 문구 목록에 같이 넣을 것.
#   ("— 보유(d211). …" 꼴은 3차 검토에서 추가 — 현대차·ORCL이 같은 d210/d211 보유 결정인데 안 읽히고 있었다.)
# ⚠️ **알려진 한계 — 결정일 귀속**: analyze()는 종목의 **첫 등장일**(= 3개월 창의 시작)에 **지금 카드의 신호**를 붙인다.
#   그래서 최근에 생긴 신호가 석 달 전 결정처럼 채점된다. "증액 없음"(안 늘린다)을 NO_BUY에 넣었더니 MU에
#   "관망 후 -25% 하락 = 안 사길 잘함"이 찍혔다 — 그 구간(7월)엔 MU를 실제로 더 사고 있었다(증액 종료 8/29).
#   ⇒ '증액 없음' 계열은 **넣지 않는다**. 신호가 시작된 날을 결정일로 쓰도록 고친 뒤에 넣을 것(별도 과제).
#   같은 이유로 '놓친매도'의 결정일도 그 보유 결정이 내려진 날이 아니라 창의 시작일이다 — 날짜가 아니라 '안 팔았다'는 사실로 읽는다.
NO_BUY_RE = re.compile(
    r"관망|보류|추격\s*금지|진입\s*금지|"
    r"(물타기|추가\s*매수|추가매수|신규\s*매수|신규매수|신규\s*자금)\s*(영구)?\s*(금지|안함|제외)|"
    r"봉인|매수후보\s*아님|신규자금\s*영구제외")
NO_SELL_RE = re.compile(
    r"홀딩|홀드|인내|장기\s*보유|보유\s*유지|잔여\s*보유|보유\s*\(d\d+|"
    r"패닉셀\s*금지|손절선\s*(없음|영구\s*폐기)|정리후보|"
    r"트림\s*(실익없음|보류)|잔여\s*(절반\s*)?홀딩")
# 하위호환(다른 스크립트가 import할 수 있음)
NO_BUY_KW = ("관망", "보류", "추격 금지", "추격금지", "진입금지", "진입 금지")
NO_SELL_KW = ("홀딩", "인내", "손절선 없음", "정리후보")

# ── 클러스터(반복 편향 집계용) ────────────────────────────────────────────
CLUSTER = {
    "메모리·AI하드웨어": {"005930.KS", "000660.KS", "MU", "AVGO", "ANET",
                          "240810.KQ", "095610.KQ", "STM", "005070.KS", "TSM", "AMAT", "CDNS"},
    "국내수급민감 대형": {"005930.KS", "000660.KS", "005380.KS", "035420.KS"},
    "급등주·모멘텀":     {"454910.KS", "TSLA", "SPCX", "IONQ", "PLTR", "IBM"},
    "전력·피지컬AI":     {"066570.KS", "GEV", "034020.KS", "011070.KS",
                          "042660.KS", "096770.KS", "012450.KS", "010140.KS", "329180.KS",
                          "ISRG"},
    "빅테크·플랫폼":     {"META", "MSFT", "AAPL", "GOOGL", "ORCL", "NAVER",
                          "035420.KS", "TMUS", "033780.KS"}  # TMUS = 10/12 d239 워치 제외(사후 추적용 매핑 유지),
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
    no_buy = bool(NO_BUY_RE.search(text))
    no_sell = bool(NO_SELL_RE.search(text))
    # 라벨 = 대표 시그널(표시용)
    label = (bz.strip()[:14] or trim.strip()[:14] or "—")
    return (no_buy, no_sell, label, rule_blocked)


def _ensure_full_history():
    """★[8/22] shallow clone이면 이 도구는 **조용히 잘린 범위만** 본다.

    8/22 실측: 세션 클론이 shallow라 커밋 61개(8/14~)뿐이었고 stocks.json 이력이 11개였다
    → 오미션 검출이 **2건**. `git fetch --unshallow` 후 658커밋·이력 133개가 되자
    **놓친 매수 7건·놓친 매도 2건**이 드러났다(PLTR +51%·ANET +21%·META +21% 등).
    즉 "오미션이 없다"는 결론 자체가 **클론 깊이의 산물**이었다.
    ⇒ 사람 기억(validate WARN)에 맡기지 않고 도구가 직접 확인·복구한다.

    → 복구에 실패해 **잘린 이력으로 채점하게 됐으면** 그 이유(문자열), 아니면 None. 호출자가 결과에 싣는다.
    ★[10/14 4차 검토] fetch의 종료코드를 안 봤다 — origin 접속 실패·인증 거부(종료코드 128)여도 '히스토리를 복구한다'만
      찍고 잘린 이력으로 채점했다(8/22와 같은 결론이 조용히 다시 나온다). 종료코드와 복구 뒤 상태를 둘 다 본다."""
    def is_shallow():
        r = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30, cwd=ROOT)
        return (r.stdout or "").strip() == "true"
    try:
        if not is_shallow():
            return None
    except (OSError, subprocess.SubprocessError):
        # ★[10/14] 여기가 `except Exception`이라 NameError(subprocess 미임포트 · REPO 미정의)가 8/22부터 삼켜졌다 —
        #   shallow clone 복구가 한 번도 돈 적이 없다. git 실행 실패만 넘긴다.
        return None
    print("[INFO] shallow clone 감지 — 히스토리를 복구한다(git fetch --unshallow). "
          "이걸 안 하면 잘린 범위만 보고 '오미션 없음'이라는 틀린 결론이 나온다.",
          file=sys.stderr)
    why = None
    try:
        f = subprocess.run(["git", "fetch", "--unshallow", "origin"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600, cwd=ROOT)
        if f.returncode != 0 or is_shallow():
            last = ((f.stderr or "").strip().splitlines() or ["(출력 없음)"])[-1][:100]
            why = f"종료코드 {f.returncode} · {last}"
    except (OSError, subprocess.SubprocessError) as ex:
        why = f"{type(ex).__name__}: {str(ex)[:60]}"
    if why:
        print(f"[WARN] unshallow 실패({why}) — 결과가 잘린 범위 기준임을 감안할 것.", file=sys.stderr)
    return why


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
        # ★[8/14] 집행가능성 판정 — 놓친매수에만 적용(매도는 현금 제약과 무관하다)
        blk, blk_why = executability(_SNAPS, d0, tk, ref)
        cand["blocked_exec"] = blk
        cand["blocked_why"] = blk_why

        # 분류: 안 샀는데 급등 / 안 팔았는데 급락 / 올바른 무행동
        if no_buy and fwd_max >= min_move:
            rows.append({**cand,
                         "type": "집행불가" if blk else "놓친매수",
                         "severity": round(fwd_max, 1),
                         "note": (f"{d0} {label} → {peak_date} +{fwd_max:.0f}% 고점"
                                  + (f" · ⛔{blk_why}" if blk else ""))})
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


# ─────────────────────────────────────────────────────────────────────
# ★[8/14 신설·정훈 승인] 집행가능성 게이트 — "놓쳤다"와 "못 샀다"를 가른다.
#
# 배경(9회차 캘리브레이션): 8/14 미스 4건(삼성전기 +22%·원익IPS +22%·LG이노텍 +18%·
# SK하이닉스 +16%)이 전부 8/8 워치미진입으로 잡혔는데, 그 기간 내내
# **사다리 허용액 0원 + 하드플로어 발동**이라 진입이 물리적으로 불가능했다.
# 이 원장의 반사실은 "샀다면 어땠나"인데 **살 수 없었으면 반사실 자체가 성립하지 않는다.**
# 제약을 판단 실패로 세면 오미션 지표가 부풀고, 거기서 잘못된 교훈이 나온다.
#
# 판정 2단계(둘 중 하나라도 걸리면 blocked):
#   ① 그날 룰1 허용액이 0원(rule_log.jsonl `allowed_krw` / `halted`)
#   ② 국내 종목인데 **1주 가격 > 그날 가용현금** (토스 국내 소수점 미지원)
# 원장이 그날짜를 못 덮으면 **판정 보류(None)** — 없는 근거로 miss를 지우지 않는다.
_RULE_LOG = os.path.join(ROOT, "data", "app", "rule_log.jsonl")


def _rule_snapshots():
    path = _RULE_LOG or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "..", "..", "data", "app", "rule_log.jsonl")
    out = {}
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    d = json.loads(ln)
                except Exception:
                    continue
                if d.get("date"):
                    out[d["date"]] = d
    except Exception:
        return {}
    return out


def executability(snaps, decision_date, ticker, ref_price):
    """(blocked: bool|None, reason: str) — None = 원장 미커버로 판정 보류."""
    if not snaps:
        return None, "원장 없음"
    days = sorted(snaps)
    prior = [d for d in days if d <= decision_date]
    if not prior:
        return None, "원장이 결정일을 못 덮음"
    snap = snaps[prior[-1]]
    allowed = snap.get("allowed_krw")
    if snap.get("halted") or (allowed is not None and allowed <= 0):
        return True, f"룰1 허용액 0원({prior[-1]} 기준" + (" ·하드플로어" if snap.get("halted") else "") + ")"
    cash = snap.get("cash")
    if allowed is not None and str(ticker).endswith((".KS", ".KQ")) and ref_price:
        if ref_price > allowed:
            return True, (f"국내 1주 {ref_price:,.0f}원 > 그날 허용액 {allowed:,.0f}원"
                          f"{'' if cash is None else f' (가용현금 {cash:,.0f}원)'} · 소수점 불가")
    return False, "집행 가능했음"


_SNAPS = _rule_snapshots()


def report(rows, net_err, min_move):
    print("\n" + "=" * 68)
    print(f"  결정 후행회고 — missed_moves.py  (임계 ±{min_move}%)")
    print("=" * 68)
    if not rows:
        print("\n임계 초과 미스무브 없음(또는 채점 성숙 콜 부족). 원장은 계속 누적됨.")
        if net_err:
            print(f"시세 조회 실패: {net_err}")
        return

    order = {"놓친매수": 0, "놓친매도": 1, "집행불가": 2, "잘참음": 3, "잘홀딩": 4}
    for typ in ("놓친매수", "놓친매도", "집행불가", "잘참음", "잘홀딩"):
        sub = sorted([r for r in rows if r["type"] == typ],
                     key=lambda r: -r["severity"])
        if not sub:
            continue
        head = {"놓친매수": "🔺 놓친 매수 (안 샀는데 급등 — '그때 살걸')",
                "집행불가": "⛔ 집행 불가였음 (급등했으나 살 수 없었다 — miss 아님·반사실 미성립)",
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
    # ★[9/26 R3] 舊 구조는 종목별로 모은 줄을 **평평하게 이어붙인 뒤 [:12]로 잘라서**,
    #   매칭이 많은 한 종목이 12줄을 전부 먹고 나머지 종목의 반사실을 통째로 가렸다.
    #   9/26 실측: 놓친매수 10종목(PLTR +70%·096770 +64%·MSFT +38% …)이 잡혔는데
    #   출력 12줄이 **전부 META**였다 — 가장 크게 놓친 종목들의 '그때 기각한 대안'을
    #   한 줄도 못 봤다. 반사실 재검토가 이 블록의 존재 이유인데 그게 안 보이면 블록이 헛돈다.
    #   ⇒ 종목별로 최신 기각부터 담고 **라운드로빈**으로 섞어 모든 종목이 최소 1줄을 받게 한다.
    REJ_MAX = 12
    per_tk = {}
    for r in miss:
        tk = r["ticker"]
        if tk in per_tk:
            continue
        seen, bucket = set(), []
        for rj in match_rejected(tk):
            if rj["date"] in seen:
                continue
            seen.add(rj["date"])
            bucket.append(rj)
        bucket.sort(key=lambda x: str(x.get("date") or ""), reverse=True)  # 최신 기각 먼저
        if bucket:
            per_tk[tk] = bucket
    lines = []
    depth = 0
    while per_tk and len(lines) < REJ_MAX:
        progressed = False
        for tk in list(per_tk):
            if depth < len(per_tk[tk]) and len(lines) < REJ_MAX:
                rj = per_tk[tk][depth]
                lines.append(f"  {tk} · {rj['date']} 기각: {rj['rejected'][:60]}")
                progressed = True
        if not progressed:
            break
        depth += 1
    if lines:
        total = sum(len(v) for v in per_tk.values())
        print("\n— 그때 기각한 대안(decisions.jsonl) — 반사실로 재검토 —")
        for l in lines:
            print(l)
        if total > len(lines):
            print(f"  … 종목 {len(per_tk)}개 · 기각 {total}건 중 {len(lines)}건 표시"
                  f"(종목별 최신부터 라운드로빈)")

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
    ap.add_argument("--selftest", action="store_true", help="결정 시그널 사전 자가검증(오프라인 · git·시세 안 봄)")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    truncated = _ensure_full_history()
    rows, net_err = analyze(a.min_move, a.since)
    if a.json:
        print(json.dumps({"min_move": a.min_move, "since": a.since,
                          "candidates": rows, "net_err": net_err, "history_truncated": truncated},
                         ensure_ascii=False, indent=1))
    else:
        if truncated:
            print(f"⚠️ 이력이 잘려 있다(shallow clone · 복구 실패: {truncated}) — 아래 결과는 잘린 범위 기준이다. "
                  "'오미션 없음'으로 읽지 말 것.")
        report(rows, net_err, a.min_move)


def selftest() -> int:
    """결정 시그널 사전이 실제 카드 문구를 읽는가. 쓰는 쪽(카드)과 읽는 쪽(이 사전)이 갈리면 결정이 조용히 사라진다."""
    fails = []

    def ok(name, cond):
        if not cond:
            fails.append(name)
        print(f"  {'✅' if cond else '❌'} {name}")

    def sig(buy_zone="", trim="", comment=""):
        nb, ns, _, _ = sig_from({"buy_zone": buy_zone, "trim": trim, "comment": comment}, False)
        return nb, ns

    # 실제 카드에서 가져온 문구들
    ok("d243 MU 카드(첫 둔화 = 중립 · 보유 유지·증액 없음) = 안 판다(안 늘린다는 결정일 귀속 한계로 아직 안 읽는다)",
       sig(buy_zone="—", trim="잔여 보유(d210 9/23: 가격 < 목표 밴드 하단 · 마진 첫 둔화 = 중립(d243 10/13))",
           comment="룰4 = **첫 둔화 = 중립(보유 유지·증액 없음 · d243 10/13 정훈 승인)** — 하락 전환 아님") == (False, True))
    ok("'— 보유(d211). …' · '— 보유(d210 9/23: …)' 꼴도 안 판다(현대차·ORCL 카드)",
       sig(trim="— 보유(d211). 3Q 영업마진 ≥5.43% 보유 / 미만이면 반등 지정가 정리 … 등록 없음") == (False, True)
       and sig(trim="— 보유(d210 9/23: 가격 < 목표 밴드 하단)") == (False, True))
    ok("'보유'만으로는 안 걸린다(보유 12종목 · 보유 비중 · 장기보유는 별도 패턴)",
       sig(comment="보유 12종목 · 보유 비중 16.3%") == (False, False))
    ok("'보유 유지'만 있어도 안 판다", sig(comment="중립 — 보유 유지") == (False, True))
    ok("'잔여 보유'도 안 판다", sig(trim="잔여 보유") == (False, True))
    ok("'증액 없음'·'증액 종료'는 아직 '안 산다'로 읽지 않는다(결정일 귀속을 고친 뒤 넣는다 — 지금 넣으면 소급 채점된다)",
       all(sig(comment=c) == (False, False) for c in ("증액 없음", "증액 금지", "증액  종료")))
    ok("舊 표기는 그대로 읽는다(홀딩 · 물타기 영구금지 · 추가매수 영구금지 · 신규매수 금지 · 관망)",
       sig(comment="룰4 = 홀딩") == (False, True) and sig(buy_zone="물타기 영구금지") == (True, False)
       and sig(buy_zone="추가매수 영구금지") == (True, False) and sig(buy_zone="신규매수 금지") == (True, False)
       and sig(buy_zone="관망") == (True, False))
    ok("'물타기 금지'는 안 사는 것이지 안 파는 것이 아니다(8/22 분류 오류 재발 방지)",
       sig(buy_zone="물타기 금지") == (True, False))
    ok("결정 문구가 없는 카드는 시그널 없음(가격대·숫자만)",
       sig(buy_zone="$880~900 눌림", trim="$1,400 일부 익절", comment="FQ4 매출 $54.23B") == (False, False))
    ok("워치 = 미보유 후보는 문구와 무관하게 '안 산' 결정",
       sig_from({"buy_zone": "$180~190"}, True)[:2] == (True, False))

    calls = []
    keep_run = subprocess.run

    state = {"shallow": ["true", "false"], "fetch_rc": 0}     # rev-parse가 차례로 내는 답 · fetch 종료코드

    def fake_git(cmd, **k):
        calls.append((cmd, k.get("cwd")))
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=state["shallow"].pop(0) + "\n", stderr="")
        return subprocess.CompletedProcess(cmd, state["fetch_rc"], stdout="",
                                           stderr="" if not state["fetch_rc"] else "fatal: 'origin' does not appear to be a git repository")
    import contextlib
    import io
    try:
        subprocess.run = fake_git
        with contextlib.redirect_stderr(io.StringIO()) as e_ok:
            r_ok = _ensure_full_history()
        n_ok = [c[0][1] for c in calls]
        state.update(shallow=["true", "true"], fetch_rc=128)
        with contextlib.redirect_stderr(io.StringIO()) as e_fail:
            r_fail = _ensure_full_history()
        state.update(shallow=["true", "true"], fetch_rc=0)       # fetch는 0인데 여전히 shallow(부분 복구)
        with contextlib.redirect_stderr(io.StringIO()):
            r_still = _ensure_full_history()
        state.update(shallow=["false"], fetch_rc=0)
        del calls[:]
        r_full = _ensure_full_history()
        n_full = [c[0][1] for c in calls]
    finally:
        subprocess.run = keep_run
    ok("shallow clone이면 복구(git fetch --unshallow)를 실제로 부른다 — 레포 루트에서(8/22부터 NameError로 안 돌았다)",
       n_ok == ["rev-parse", "fetch", "rev-parse"] and r_ok is None and "WARN" not in e_ok.getvalue())
    ok("복구 실패(fetch 종료코드 128)는 WARN + 이유를 돌려준다 — '복구한다'만 찍고 넘어가지 않는다",
       r_fail and "128" in r_fail and "WARN" in e_fail.getvalue())
    ok("fetch가 0이어도 여전히 shallow면 실패로 본다", bool(r_still))
    ok("전체 이력이면 아무것도 하지 않는다(fetch 미호출)", r_full is None and n_full == ["rev-parse"])

    print(f"\n{'✅ SELFTEST PASS' if not fails else '❌ SELFTEST FAIL: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    main()
