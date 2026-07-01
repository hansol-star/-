#!/usr/bin/env python3
"""
validate_report.py — 보고서 '완료의 정의' 게이트 (하네스 엔지니어링: 검증을 명령어로)

커밋·main 머지 전에 한 줄로 돌려 산출물이 '진짜 완성'인지 기계로 검사한다.
빌더(PM)가 눈으로 자가채점하던 완성도 점검을 독립 검사기로 분리한 것 —
풀표 누락·컬럼 빠짐·별점↔스코어 어긋남·정본 stale을 사람 대신 기계가 잡는다.
(만든 역할 ≠ 검사 역할. AI가 '다 됐다' 선언하기 전의 답안지.)

  python3 .claude/skills/portfolio-desk/scripts/validate_report.py
  python3 .claude/skills/portfolio-desk/scripts/validate_report.py --report docs/reports/report_v26_2026-06-22.md

FAIL(❌, exit 1) = 반드시 고치고 커밋.  WARN(⚠️, exit 0) = 눈으로 확인.
의존성 없음(stdlib). 정본 = data/app/{stocks,flows,tasks}.json · CLAUDE.md · docs/reports/.
"""
import argparse, json, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# 보유 16종목 정본 (티커 → 보고서 본문에서 찾을 별칭들). 변동 시 여기 + master.md 동시 갱신.
HOLDINGS = {
    "005930.KS": ["삼성전자", "삼성"],
    "066570.KS": ["LG전자"],
    "454910.KS": ["두산로보", "두산로보틱스"],
    "005380.KS": ["현대차"],
    "035420.KS": ["NAVER", "네이버"],
    "NVDA": ["NVDA", "엔비디아"],
    "META": ["META", "메타"],
    "VOO": ["VOO"],
    "MSFT": ["MSFT", "마이크로소프트"],
    "AAPL": ["AAPL", "애플"],
    "GOOGL": ["GOOGL", "구글", "알파벳"],
    "TSLA": ["TSLA", "테슬라"],
    "ORCL": ["ORCL", "오라클"],
    "ANET": ["ANET", "아리스타"],
    "MU": ["MU", "마이크론"],
    "AVGO": ["AVGO", "브로드컴"],
}
ETF_NO_SCORE = {"VOO"}                 # ETF = 0~100 스코어 제외(null 허용)
REQUIRED_COLS = ["stars", "target", "buy_zone", "trim", "comment"]  # +score(ETF 외)

FAILS, WARNS = [], []
def fail(m): FAILS.append(m)
def warn(m): WARNS.append(m)

def load(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        fail(f"{rel} 없음 (정본 파일 누락)"); return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception as e:
        fail(f"{rel} JSON 파싱 실패: {e}"); return None

def band_star(score):
    return 5 if score >= 85 else 4 if score >= 70 else 3 if score >= 55 else 2 if score >= 40 else 1

def ver(name):
    m = re.search(r"report_v(\d+)", name or "")
    return int(m.group(1)) if m else None

# ── A. stocks.json: 16종목 완전성 + 컬럼 + 별점↔스코어 ──────────────────────
def check_stocks():
    d = load("data/app/stocks.json")
    if not d: return
    s = d.get("stocks", {})
    keys = set(s.keys())
    miss, extra = set(HOLDINGS) - keys, keys - set(HOLDINGS)
    if miss:  fail(f"stocks.json 보유종목 누락: {sorted(miss)}")
    if extra: fail(f"stocks.json 미지정 종목: {sorted(extra)}")
    if len(s) != 16:
        fail(f"stocks.json 보유 {len(s)}종목 (16 아님)")
    for t, v in s.items():
        for c in REQUIRED_COLS:
            val = v.get(c)
            if val in (None, "", []):
                fail(f"{t}: '{c}' 컬럼 비어있음 (풀표 컬럼 누락)")
        st = v.get("stars")
        if not (isinstance(st, int) and 1 <= st <= 5):
            fail(f"{t}: stars={st!r} (1~5 정수 아님)")
        sc = v.get("score")
        if t in ETF_NO_SCORE:
            continue
        if not (isinstance(sc, int) and 0 <= sc <= 100):
            fail(f"{t}: score={sc!r} (0~100 정수 아님 · ETF만 null 허용)"); continue
        if isinstance(st, int):
            exp = band_star(sc)
            # 정성가중: 별점은 score밴드 ±1 이내 허용(코어 확신·리스크 보수·모멘텀 가점).
            # ±2 이상 벌어지면 재점검 필요 → WARN. 모멘텀주(454910·TSLA)는 score가 낮아 자동 ±1 수렴.
            if abs(st - exp) >= 2:
                warn(f"{t}: ⭐{st} vs score {sc}→밴드 ⭐{exp} ±2 이상 어긋남 — 근거 재점검")
    if not d.get("as_of"):        warn("stocks.json: as_of 비어있음")
    if not d.get("source_report"): warn("stocks.json: source_report 비어있음")

# ── B. flows.json: 추측 수치 금지(미확인=null) ────────────────────────────
def check_flows():
    d = load("data/app/flows.json")
    if not d: return
    ser = d.get("series")
    if not isinstance(ser, list) or not ser:
        fail("flows.json: series 비어있음"); return
    for e in ser:
        if not e.get("date"):
            fail("flows.json: date 없는 항목")
        for k in ("foreign", "inst", "indiv"):
            x = e.get(k, None)
            if x is not None and not isinstance(x, (int, float)):
                fail(f"flows.json {e.get('date')}: {k}={x!r} (숫자/ null 만 — 추측 문자열 금지)")
    if not d.get("updated"): warn("flows.json: updated 비어있음")

# ── C. tasks.json: source_report 실존 ────────────────────────────────────
def check_tasks():
    d = load("data/app/tasks.json")
    if not d: return
    sr = d.get("source_report")
    if not sr:
        warn("tasks.json: source_report 비어있음")
    elif not os.path.exists(os.path.join(ROOT, sr)):
        fail(f"tasks.json: source_report 파일 없음 → {sr}")
    if not d.get("as_of"): warn("tasks.json: as_of 비어있음")

# ── D. 버전 정합: CLAUDE.md/stocks/tasks 가 최신 보고서를 가리키는가(stale 방지) ─
def latest_version():
    rdir = os.path.join(ROOT, "docs/reports")
    vs = [ver(f) for f in os.listdir(rdir) if re.match(r"report_v\d+", f)]
    vs = [v for v in vs if v is not None]
    return (max(vs) if vs else None)

def check_versions(latest):
    if latest is None:
        warn("docs/reports/ 에 report_v*.md 없음"); return
    st = load("data/app/stocks.json")
    if st and ver(st.get("source_report")) and ver(st.get("source_report")) < latest:
        fail(f"stocks.json source_report=v{ver(st.get('source_report'))} < 최신 v{latest} (정본 stale)")
    tk = load("data/app/tasks.json")
    if tk and ver(tk.get("source_report")) and ver(tk.get("source_report")) < latest:
        warn(f"tasks.json source_report=v{ver(tk.get('source_report'))} < 최신 v{latest}")
    # CLAUDE.md (자동로드 지도). 한/영 하이브리드 토큰 모두 인식.
    cp = os.path.join(ROOT, "CLAUDE.md")
    if os.path.exists(cp):
        txt = open(cp, encoding="utf-8").read()
        m = (re.search(r"최신[^\n]*?v(\d+)", txt) or re.search(r"현재[^\n]*?\bv(\d+)\b", txt)
             or re.search(r"(?:latest|current)[^\n]*?\bv(\d+)\b", txt, re.I))
        if m and int(m.group(1)) < latest:
            fail(f"CLAUDE.md 현재상태 = v{m.group(1)} < 최신 v{latest} (지도가 stale — 새 세션이 옛 상태로 출발)")
        elif not m:
            warn("CLAUDE.md 에서 현재 버전 토큰을 못 찾음 (검증 생략)")
    # config_overview.md (인덱스/지도). v28→v31 stale 재발 방지 [2026-06-25].
    op = os.path.join(ROOT, "docs/config_overview.md")
    if os.path.exists(op):
        otxt = open(op, encoding="utf-8").read()
        om = re.search(r"현재[^\n]*?\bv(\d+)\b", otxt) or re.search(r"정본[^\n]*?\bv(\d+)\b", otxt)
        if om and int(om.group(1)) < latest:
            fail(f"config_overview.md 정본 = v{om.group(1)} < 최신 v{latest} (인덱스 stale)")

# ── E. 보고서 파일(선택): 디스클레이머 1회·STATE SNAPSHOT·16종목 등장 ──────
def latest_report_path(latest):
    rdir = os.path.join(ROOT, "docs/reports")
    cands = [f for f in os.listdir(rdir) if re.match(rf"report_v{latest}_", f)]
    return os.path.join("docs/reports", sorted(cands)[0]) if cands else None

def check_report(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        fail(f"보고서 파일 없음: {rel}"); return
    txt = open(p, encoding="utf-8").read()
    dc = len(re.findall(r"투자\s*자문\s*아님", txt))
    if dc > 1:
        warn(f"{rel}: 디스클레이머 '투자 자문 아님' {dc}회 (파일 끝 1회만 — 정훈 지적)")
    if "STATE SNAPSHOT" not in txt:
        fail(f"{rel}: STATE SNAPSHOT 블록 없음 (연속성 백본 누락)")
    absent = [t for t, al in HOLDINGS.items()
              if not any(a in txt for a in al) and t not in txt]
    if absent:
        warn(f"{rel}: 본문에 안 보이는 보유종목 {absent} (풀표 누락 가능 — 확인)")

# ── F. 정본 일관성: portfolio.json(원가·trigger 기계정본) ↔ stocks.json(앱 정본) ─
def check_consistency():
    pf = load(".claude/skills/portfolio-desk/portfolio.json")
    sj = load("data/app/stocks.json")
    if not pf or not sj:
        return
    flat = pf.get("holdings", {}).get("kr", []) + pf.get("holdings", {}).get("us", [])
    pf_tk = {x.get("ticker") for x in flat}
    sj_tk = set(sj.get("stocks", {}).keys())
    if pf_tk - sj_tk:
        fail(f"portfolio.json holdings에만(stocks 누락): {sorted(pf_tk - sj_tk)}")
    if sj_tk - pf_tk:
        fail(f"stocks.json에만(portfolio holdings 누락): {sorted(sj_tk - pf_tk)} — pnl·trigger가 못 봄")
    for x in flat:
        if not x.get("cost"):
            fail(f"portfolio.json {x.get('ticker')}: cost(원가) 없음 — 수익률 정본 누락")
    pf_w = {x.get("ticker") for x in pf.get("watchlist", [])}
    sjw = sj.get("watchlist", {})
    sj_w = set(sjw.keys()) if isinstance(sjw, dict) else {x.get("ticker") for x in sjw}
    if pf_w != sj_w:
        warn(f"워치 불일치 portfolio↔stocks: portfolio만 {sorted(pf_w - sj_w)} / stocks만 {sorted(sj_w - pf_w)}")

def check_hunter():
    """경제사냥꾼 앱 데이터 동기화 게이트.
    ① latest_videos 요약 필드(summary) 누락 = 앱 상세 '—' 빈칸 → FAIL/WARN.
    ② hunter_log.md 날짜 vs (archive ∪ latest) 날짜 비교 → 로그에만 있는 날짜=백필 누락 WARN."""
    hu = load("data/app/hunter.json")
    arch = load("data/app/hunter_archive.json")
    if not hu:
        return
    lv = hu.get("latest_videos", [])
    for i, v in enumerate(lv):
        has_sum = bool((v.get("summary") or "").strip())
        has_note = bool((v.get("note") or "").strip())
        title = v.get("title", f"#{i}")
        if not has_sum and not has_note:
            fail(f"hunter latest_videos '{title}': 요약(summary) 없음 — 앱 상세가 '—' 빈칸")
        elif not has_sum and has_note:
            warn(f"hunter latest_videos '{title}': 정본 키는 'summary'인데 'note'로 들어옴 — summary로 교정 권고")

    # 커버리지 갭: 로그 날짜가 앱(archive+latest)에 반영됐는지
    log_path = os.path.join(ROOT, "docs/research/hunter_log.md")
    if os.path.exists(log_path):
        txt = open(log_path, encoding="utf-8").read()
        log_dates = set(re.findall(r"^#{2,3}\s+(\d{4}-\d{2}-\d{2})", txt, re.M))
        app_dates = {v.get("date") for v in lv}
        if isinstance(arch, dict):
            app_dates |= {v.get("date") for v in arch.get("videos", [])}
        app_dates = {d for d in app_dates if d}
        # 내부 구멍(=앱 최신일보다 오래됐는데 빠진 날짜)만 백필 대상.
        # 로그 헤더가 브리핑 날짜(영상 업로드일보다 하루 뒤)인 경우가 있어
        # 앱 최신일보다 '새로운' 로그 날짜는 오탐이므로 제외.
        if app_dates:
            newest = max(app_dates)
            missing = sorted(d for d in log_dates if d not in app_dates and d <= newest)
            if missing:
                warn(f"hunter 아카이브 백필 필요(로그엔 있으나 앱 미반영): {missing}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="검사할 보고서 .md (생략 시 최신 자동)")
    ap.add_argument("--no-report", action="store_true", help="보고서 파일 검사 생략")
    a = ap.parse_args()

    check_stocks(); check_flows(); check_tasks(); check_consistency(); check_hunter()
    latest = latest_version(); check_versions(latest)
    if not a.no_report:
        rel = a.report or (latest_report_path(latest) if latest else None)
        if rel: check_report(rel)

    print("\n" + "=" * 56)
    print("  보고서 완료-검증 (validate_report.py)")
    print("=" * 56)
    if FAILS:
        print(f"\n❌ FAIL {len(FAILS)} — 고치고 커밋:")
        for m in FAILS: print(f"   ❌ {m}")
    if WARNS:
        print(f"\n⚠️  WARN {len(WARNS)} — 눈으로 확인:")
        for m in WARNS: print(f"   ⚠️  {m}")
    if not FAILS and not WARNS:
        print("\n✅ 완벽 — 보유16·컬럼·별점/스코어·정본 버전 전부 정합. 커밋 OK.")
    elif not FAILS:
        print(f"\n✅ FAIL 없음 — 커밋 OK (WARN {len(WARNS)}건은 판단).")
    print()
    sys.exit(1 if FAILS else 0)

if __name__ == "__main__":
    main()
