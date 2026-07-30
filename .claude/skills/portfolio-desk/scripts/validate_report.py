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
import argparse, json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# 보유 15종목 정본 (티커 → 보고서 본문에서 찾을 별칭들). 변동 시 여기 + master.md 동시 갱신. [7/7 TSLA 전량 매도 → 제외]
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

# ── A. stocks.json: 보유 전종목(len(HOLDINGS)) 완전성 + 컬럼 + 별점↔스코어 ──────────
def check_stocks():
    d = load("data/app/stocks.json")
    if not d: return
    s = d.get("stocks", {})
    keys = set(s.keys())
    miss, extra = set(HOLDINGS) - keys, keys - set(HOLDINGS)
    if miss:  fail(f"stocks.json 보유종목 누락: {sorted(miss)}")
    if extra: fail(f"stocks.json 미지정 종목: {sorted(extra)}")
    if len(s) != len(HOLDINGS):
        fail(f"stocks.json 보유 {len(s)}종목 ({len(HOLDINGS)} 아님)")
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
            # ±2 이상 벌어지면 재점검 필요 → WARN. 모멘텀주(454910)는 score가 낮아 자동 ±1 수렴.
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

def _report_file_times():
    """docs/reports 내 report_v* 파일별 '유효 시각'(epoch).
    [7/13 교정] fresh clone은 모든 파일 mtime이 클론 시각으로 뭉개져 mtime 비교가
    비결정적(v47 본편·시나리오 부록이 같은 커밋인데 가짜 FAIL 난 실사고) → 정본 시각 = git
    최종 커밋시각. 단 워킹트리에서 수정/미추적인 파일(방금 쓴 새 보고서 — validate는 커밋 전
    실행이 정상 플로우)은 mtime이 진실. git 불가 환경이면 전부 mtime 폴백(구 동작)."""
    rdir = os.path.join(ROOT, "docs/reports")
    files = [f for f in os.listdir(rdir) if re.match(r"report_v\d+_", f)]
    commit_t, dirty = {}, None
    try:
        log = subprocess.run(["git", "-C", ROOT, "log", "--pretty=%ct", "--name-only",
                              "--", "docs/reports"], capture_output=True, text=True, timeout=30)
        if log.returncode == 0:
            cur = None
            for line in log.stdout.splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.isdigit():
                    cur = int(s)
                elif cur is not None:
                    commit_t.setdefault(os.path.basename(s), cur)  # log는 최신순 → 첫 값 = 최종 커밋
        st = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", "docs/reports"],
                            capture_output=True, text=True, timeout=30)
        if st.returncode == 0:
            dirty = {os.path.basename(l[3:].split(" -> ")[-1].strip().strip('"'))
                     for l in st.stdout.splitlines() if len(l) > 3}
    except Exception:
        commit_t, dirty = {}, None
    eff = {}
    for f in files:
        if f in commit_t and (dirty is not None and f not in dirty):
            eff[f] = commit_t[f]
        else:
            try:
                eff[f] = os.path.getmtime(os.path.join(rdir, f))
            except OSError:
                eff[f] = 0
    return eff

def newest_report_files():
    """최신 보고서 '파일 집합'(버전+유효시각 최댓값) — intra-version stale 감지용.
    같은 커밋으로 함께 들어온 파일들(본편+부록 등 동시각 tie)은 같은 세션 산출물이므로
    집합으로 취급: source_report가 집합의 어느 멤버를 가리켜도 stale 아님."""
    eff = _report_file_times()
    if not eff:
        return []
    key = lambda f: (ver(f) or 0, eff[f])
    top = max(key(f) for f in eff)
    return sorted(f for f in eff if key(f) == top)

def newest_report_file():
    """최신 보고서 파일 1개(집합 대표 — 날짜 추출 등 단일값 용도)."""
    fs = newest_report_files()
    return fs[-1] if fs else None

def check_versions(latest):
    if latest is None:
        warn("docs/reports/ 에 report_v*.md 없음"); return
    newest_set = newest_report_files()
    st = load("data/app/stocks.json")
    if st and ver(st.get("source_report")) and ver(st.get("source_report")) < latest:
        fail(f"stocks.json source_report=v{ver(st.get('source_report'))} < 최신 v{latest} (정본 stale)")
    # [7/2 신설·7/13 git시각 교정] intra-version stale: v번호는 같아도 같은 날 아침→EXEC 등
    # 최신 '파일 집합'에 없으면 FAIL. (v37 아침 서사가 EXEC 폭락 뒤에도 앱에 남았던 사고 재발 방지)
    elif st and newest_set:
        sr_base = os.path.basename(st.get("source_report") or "")
        if ver(sr_base) == latest and sr_base not in newest_set:
            fail(f"stocks.json source_report={sr_base} ≠ 최신 파일 {'/'.join(newest_set)} "
                 f"(같은 v{latest} 내 stale — EXEC/밤 대화 등 부록 세션도 stocks.json 동기화 의무)")
    tk = load("data/app/tasks.json")
    if tk and ver(tk.get("source_report")) and ver(tk.get("source_report")) < latest:
        warn(f"tasks.json source_report=v{ver(tk.get('source_report'))} < 최신 v{latest}")
    elif tk and newest_set:
        tk_base = os.path.basename(tk.get("source_report") or "")
        if ver(tk_base) == latest and tk_base not in newest_set:
            warn(f"tasks.json source_report={tk_base} ≠ 최신 파일 {'/'.join(newest_set)} (intra-version stale)")
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

# ── E. 보고서 파일(선택): 디스클레이머 1회·STATE SNAPSHOT·보유 전종목 등장 ──────
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
    ② hunter_log.md 날짜 vs hunter_archive.json 날짜 비교 → 로그에만 있는 날짜=아카이브 정체 FAIL.
       [7/4 격상] latest_videos는 커버로 치지 않는다 — 앱 '전체 영상 아카이브' 화면은
       archive만 읽으므로 latest에만 있으면 화면에서 통째로 빠진다(7/3 정체 재발 원인).
       build_app_data.py가 latest→archive 자동 롤오버하므로 빌드만 돌리면 해소."""
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

    # 커버리지 갭: 로그 날짜가 hunter_archive.json에 실제 반영됐는지 (latest는 커버 아님)
    log_path = os.path.join(ROOT, "docs/research/hunter_log.md")
    if os.path.exists(log_path):
        txt = open(log_path, encoding="utf-8").read()
        log_dates = set(re.findall(r"^#{2,3}\s+(\d{4}-\d{2}-\d{2})", txt, re.M))
        latest_dates = {v.get("date") for v in lv if v.get("date")}
        arch_dates = set()
        if isinstance(arch, dict):
            arch_dates = {v.get("date") for v in arch.get("videos", []) if v.get("date")}
        # 내부 구멍(=앱 최신일보다 오래됐는데 빠진 날짜)만 대상.
        # 로그 헤더가 브리핑 날짜(영상 업로드일보다 하루 뒤)인 경우가 있어
        # (archive ∪ latest) 최신일보다 '새로운' 로그 날짜는 오탐이므로 제외.
        all_dates = arch_dates | latest_dates
        if all_dates:
            newest = max(all_dates)
            missing = sorted(d for d in log_dates if d not in arch_dates and d <= newest)
            if missing:
                fail(f"hunter 아카이브 정체(로그엔 있으나 hunter_archive.json 미반영): {missing}"
                     " — build_app_data.py 실행 시 latest→archive 자동 롤오버로 해소")

    # 스키마 게이트 [7/4 실사고]: tickers가 문자열이면 앱 renderArchive가 forEach에서
    # 크래시 → 화면 전체 "데이터 로딩 중" 멈춤. 빌드가 자동 교정하므로 FAIL=빌드 미실행 신호.
    if isinstance(arch, dict):
        bad = [str(v.get("title", "?"))[:28] for v in arch.get("videos", [])
               if not isinstance(v.get("tickers"), list)]
        if bad:
            fail(f"hunter_archive tickers 비리스트 {len(bad)}건(앱 아카이브 화면 크래시): {bad[:3]}"
                 " — build_app_data.py 실행하면 자동 교정")

def check_feeds():
    """[7/7 신설] 외부 채널(수페TV·지식인사이드) feeds.json 게이트 — 신규라 WARN 수준.
    안정화(2~3주) 후 check_hunter처럼 FAIL 승격 검토."""
    fd = load("data/app/feeds.json")
    if not fd:
        return
    for slug, ch in (fd.get("channels") or {}).items():
        name = ch.get("name", slug)
        for i, v in enumerate(ch.get("latest_videos", [])):
            if not (v.get("summary") or "").strip() and not (v.get("note") or "").strip():
                warn(f"feeds[{name}] latest_videos '{v.get('title', f'#{i}')}': summary 없음 — 앱 빈칸")
            if not isinstance(v.get("tickers", []), list):
                warn(f"feeds[{name}] '{v.get('title', '?')[:28]}': tickers 비리스트 — 리스트로 교정할 것")


def check_guru():
    """[7/23 신설] 대가 13F 흐름 guru_flows.json 게이트 — 분기 cadence라 WARN 수준
    (13F는 분기말 후 ~45일 지연 → 일일 보고서를 FAIL로 막지 않는다). 파일 없으면 스킵(옵션 피드).
    구조·필수필드·액션값·과도 staleness만 점검."""
    import datetime as _dt
    p = os.path.join(ROOT, "data/app/guru_flows.json")
    if not os.path.exists(p):
        return
    try:
        gf = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        warn(f"guru_flows.json JSON 파싱 실패: {e}"); return
    gurus = gf.get("gurus") or {}
    if not isinstance(gurus, dict) or not gurus:
        warn("guru_flows.json: gurus 비어있음 — guru_flows.py --emit 실행 필요"); return
    valid = {"NEW", "ADD", "TRIM", "EXIT", "HOLD"}
    for slug, g in gurus.items():
        if g.get("error"):
            warn(f"guru_flows[{slug}]: 수집 오류 — {g['error']}"); continue
        for fld in ("name", "quarter"):
            if not str(g.get(fld) or "").strip():
                warn(f"guru_flows[{slug}]: {fld} 없음")
        if not isinstance(g.get("moves", []), list):
            warn(f"guru_flows[{slug}]: moves 비리스트")
        if not isinstance(g.get("overlap_with_holdings", []), list):
            warn(f"guru_flows[{slug}]: overlap_with_holdings 비리스트")
        for m in (g.get("moves") or []):
            if m.get("action") not in valid:
                warn(f"guru_flows[{slug}] move '{str(m.get('issuer', '?'))[:20]}': 액션값 이상 ({m.get('action')})")
                break
    upd = gf.get("updated")
    if upd:
        try:
            gap = (_dt.date.today() - _dt.date.fromisoformat(upd)).days
            if gap > 120:
                warn(f"guru_flows.json {gap}일 경과 — 새 13F 공시창 지났을 수 있음(guru_flows.py --emit + 데스크 갱신)")
        except Exception:
            pass


# ── G. [7/2 신설] 신선도·정합 sanity: forecast 레인지 vs 실시세 · pm_view/decisions 날짜 ──
def check_freshness(latest):
    import datetime as _dt
    # 최신 보고서 날짜(파일명 YYYY-MM-DD)
    nf = newest_report_file() or ""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", nf)
    rep_date = m.group(1) if m else None

    # pm_view.json 오래됨 [7/13 강화: 3일→1일 — PM 사견은 매 보고서 필수(6/28 규약)인데
    # 앱 4파일 동기화 의무에 pm_view가 빠져 v47서 하루 stale 방치된 구멍]
    pv = load("data/app/pm_view.json")
    if pv and rep_date and pv.get("updated"):
        try:
            gap = (_dt.date.fromisoformat(rep_date) - _dt.date.fromisoformat(pv["updated"])).days
            if gap >= 1:
                warn(f"pm_view.json updated={pv['updated']} < 최신 보고서 {rep_date} "
                     f"({gap}일 stale — PM 사견은 매 보고서 필수, 앱 #pmview 동기화 누락)")
        except ValueError:
            pass

    # [7/12 신설] tasks.json 신선도 — R2가 outlook·index_forecast·할일 갱신을 빠뜨리는 사고 재발방지.
    # (v46서 as_of/source_report만 바꾸고 내용은 v45 7/9 상태로 남았는데 통과된 구멍. §3b 매 보고서 동기화 의무 = updated는 보고서 날짜와 같아야.)
    tk_fr = load("data/app/tasks.json")
    if tk_fr and rep_date and tk_fr.get("updated"):
        try:
            gap = (_dt.date.fromisoformat(rep_date) - _dt.date.fromisoformat(tk_fr["updated"])).days
            if gap >= 1:
                fail(f"tasks.json updated={tk_fr['updated']} < 최신 보고서 {rep_date} "
                     f"({gap}일 stale — outlook·index_forecast·할일 갱신 누락 의심. §3b 매 보고서 동기화 의무)")
        except ValueError:
            pass
    # index_forecast 코스피 ref vs flows 최신 종가 (updated는 갱신했지만 forecast 숫자를 안 고친 내용-stale 감지)
    fl_fr = load("data/app/flows.json")
    if tk_fr and fl_fr:
        ser = fl_fr.get("series") or []
        kospi_close = None
        if ser:
            mm = re.search(r"코스피\s*([\d,]+(?:\.\d+)?)", ser[-1].get("note") or "")
            if mm:
                try: kospi_close = float(mm.group(1).replace(",", ""))
                except ValueError: pass
        if kospi_close:
            for fc in (tk_fr.get("index_forecast") or []):
                if "코스피" in (fc.get("name") or ""):
                    ref = fc.get("ref")
                    if isinstance(ref, (int, float)) and abs(ref - kospi_close) / kospi_close > 0.03:
                        warn(f"tasks.json index_forecast 코스피 ref={ref:,} ≠ flows 최신 종가 {kospi_close:,.0f} "
                             f"(>3% 이격 — forecast 갱신 누락 의심)")
                    break

    # decisions.jsonl 최근성 (최신 보고서 날짜 엔트리 부재 = WARN)
    dp = os.path.join(ROOT, "data/app/decisions.jsonl")
    if os.path.exists(dp) and rep_date:
        dates = re.findall(r'"date":\s*"(\d{4}-\d{2}-\d{2})"', open(dp, encoding="utf-8").read())
        if dates and max(dates) < rep_date:
            warn(f"decisions.jsonl 최신 엔트리={max(dates)} < 보고서 {rep_date} — 당일 결정 기록 없음")

    # forecast.week 레인지 vs 실시세 (app/data.js 빌드 결과 기준 — 없으면 생략)
    dj = os.path.join(ROOT, "app/data.js")
    sj = load("data/app/stocks.json")
    if os.path.exists(dj) and sj:
        try:
            raw = open(dj, encoding="utf-8").read()
            payload = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
            # [7/13 신설] 빌드 stale: stocks.json을 고치고 build_app_data.py 재실행을 빠뜨리면
            # 앱(data.js)이 옛 서사를 노출 — source_report 대조로 감지.
            sr_app = os.path.basename(payload.get("source_report") or "")
            sr_st = os.path.basename(sj.get("source_report") or "")
            if sr_app and sr_st and sr_app != sr_st:
                warn(f"app/data.js source_report={sr_app} ≠ stocks.json {sr_st} "
                     "— build_app_data.py 재실행 누락(빌드 stale)")
            prices = {h.get("ticker"): h.get("price") for h in payload.get("holdings", [])}
            for t, v in sj.get("stocks", {}).items():
                wk = ((v.get("forecast") or {}).get("week") or {})
                lo, hi, px = wk.get("low"), wk.get("high"), prices.get(t)
                if all(isinstance(x, (int, float)) for x in (lo, hi, px)) and not (lo * 0.97 <= px <= hi * 1.03):
                    warn(f"{t}: 현재가 {px:,.0f}이 forecast.week {lo:,.0f}~{hi:,.0f} 밖 — 전망 재산정 필요")
        except Exception:
            pass

def check_financials(latest=None):
    """재무제표 **데이터 레이어**의 결손 검사 — [7/30 신설, docs/data_coverage.md §0]

    ⚠️ 이 검사가 없어서 사고가 났다. 기존 게이트는 '보고서'의 완결성(풀표·컬럼·별점 밴드)만
    봤고 '데이터 레이어'의 결손은 안 봤다 → 보유 15종목 재무제표가 **0건**인 채로 두 달간
    매일 FAIL 0으로 통과했다. 게이트가 있다는 사실이 오히려 다 갖췄다는 착각을 줬다.
    앞으로 재무제표가 비면 보고서를 못 낸다.
    """
    p = os.path.join(ROOT, "data", "app", "financials.json")
    if not os.path.exists(p):
        fail("financials.json 없음 — `python3 financials.py --all --save` 실행 필요"
             " (보유 종목 재무제표 = 스코어의 하드넘버 근거)")
        return
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        fail(f"financials.json 파싱 실패: {str(e)[:60]}")
        return

    stocks = d.get("stocks") or {}
    # 접미사(.KS/.KQ) 차이를 흡수해 6자리 코드·티커 기준으로 대조
    have = {k.split(".")[0] for k in stocks}
    need = {t.split(".")[0] for t in HOLDINGS if t not in ETF_NO_SCORE}
    missing = sorted(need - have)
    if missing:
        fail(f"재무제표 미커버 {len(missing)}종목: {', '.join(missing)}"
             f" — financials.py 재실행 또는 소스 폴백 점검")

    # 3표가 실제로 들어왔는지(껍데기만 있는 레코드 적발)
    for t, r in stocks.items():
        a = (r.get("annual") or [{}])[0] if r.get("annual") else {}
        if not a:
            warn(f"{t} 연간 재무제표 비어 있음")
            continue
        if a.get("assets") is None and a.get("revenue") is None:
            warn(f"{t} 손익·재무상태 둘 다 결측 — 소스 확인")

    # 신선도: 최신 보고서 날짜보다 오래되면 그날 상태가 아님(7/12 tasks.json stale과 같은 유형)
    if latest:
        rel = latest_report_path(latest)
        m = re.search(r"(\d{4}-\d{2}-\d{2})", rel or "")
        if m and (d.get("updated") or "") < m.group(1):
            warn(f"financials.json updated={d.get('updated')} < 보고서 {m.group(1)}"
                 f" — 재무 갱신 없이 보고서만 새로 남")

    # 스코어 근거: PM이 손으로 쓴 score와 데이터 서브스코어의 이격
    sp = os.path.join(ROOT, "data", "app", "stocks.json")
    if os.path.exists(sp):
        try:
            with open(sp, encoding="utf-8") as f:
                sj = json.load(f)
        except Exception:
            sj = {}
        src = sj.get("stocks") if isinstance(sj.get("stocks"), dict) else sj
        for t, r in stocks.items():
            sub = r.get("fund_subscore")
            if sub is None:
                continue
            ent = (src or {}).get(t) or (src or {}).get(t.split(".")[0]) or {}
            sc = ent.get("score") if isinstance(ent, dict) else None
            if isinstance(sc, (int, float)) and abs(sc - sub) >= 25:
                warn(f"{t} 스코어 {sc} vs 펀더 서브스코어 {sub} (이격 {abs(sc-sub):.0f})"
                     f" — N·L·M 가감분으로 설명되는지 근거 명시 필요")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="검사할 보고서 .md (생략 시 최신 자동)")
    ap.add_argument("--no-report", action="store_true", help="보고서 파일 검사 생략")
    a = ap.parse_args()

    check_stocks(); check_flows(); check_tasks(); check_consistency(); check_hunter(); check_feeds(); check_guru()
    latest = latest_version(); check_versions(latest); check_freshness(latest)
    check_financials(latest)
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
        print("\n✅ 완벽 — 보유 전종목·컬럼·별점/스코어·정본 버전 전부 정합. 커밋 OK.")
    elif not FAILS:
        print(f"\n✅ FAIL 없음 — 커밋 OK (WARN {len(WARNS)}건은 판단).")
    print()
    sys.exit(1 if FAILS else 0)

if __name__ == "__main__":
    main()
