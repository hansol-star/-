# 🔧 개발 핸드오프 (다음 세션이 이어받는 메모)

> 이건 **투자 보고서가 아니라 데스크 시스템(코드·연동) 작업**의 세션 간 인수인계 메모다.
> 새 세션은 이 대화 기억이 없으니 여기부터 읽고 이어간다. 완료 항목은 체크·삭제, 새 항목은 append.
> (투자 상태·시세·오더는 여전히 `docs/reports` 최신 STATE SNAPSHOT + `tasks.json`이 정본)

## 📌 다음 세션 첫 단계 (필수)
1. **env 키 주입 확인** — 정훈이 클라우드 환경변수에 아래 3개를 등록함(2026-07-19, "새 세션부터 적용"). 새 세션이면 주입됐을 것:
   ```
   FMP_API_KEY, NAVER_NCP_KEY_ID, NAVER_NCP_KEY
   ```
   확인: `for k in FMP_API_KEY NAVER_NCP_KEY_ID NAVER_NCP_KEY; do [ -n "${!k}" ] && echo "$k 있음" || echo "$k 없음"; done`
   - 다 "있음"이면 → 지속 연동 성공(정훈에게 확정 보고). "없음"이면 → 환경변수 형식(`이름=값` 한 줄씩) 재점검 안내.

## ✅ 이번 세션(7/18~19)에 완료·푸시된 것
- **`naver_data.py` 신설**(`.claude/skills/portfolio-desk/scripts/`) — 네이버 오픈API(NCP API HUB) 조회전용, stdlib.
  - 뉴스: `GET naverapihub.apigw.ntruss.com/search/v1/news` ✅ 실측 200
  - 검색어트렌드: `POST naverapihub.apigw.ntruss.com/search-trend/v1/search` ✅ 실측 200 (레거시 naveropenapi/datalab 아님 — 401 함정 주의)
  - 헤더 `X-NCP-APIGW-API-KEY-ID`/`X-NCP-APIGW-API-KEY`, 키는 env 전용. US 데이터센터 IP에서 지역차단 없음 확인.
- **영상학습 4편** → `docs/research/study_log.md` 2026-07-18 (종합 제안 포함).
- **조건부 오더 등록**: NAVER 정리(외인전환+205,000 청산)·ANET $189 트림 — tasks.json orders + portfolio.json alerts.
- **7/17 체결 반영**: GOOGL $345 GTC 1주(평단 $358.01)·VOO 적립 1회차(1.06863주). 현금 KRW 421,006·USD $0.00.
- **R3 주말 캘리브레이션** 완료(스코어카드 5회차, ⭐5·⭐4 vs ⭐3 역전 재발·Brier 0.417 과신).

## ✅ 이번 세션(7/19)에 완료된 것
- **[FMP] `fundamentals.py` stable 마이그레이션 실검증 완료**(branch `claude/fmp-fundamentals-migration-c0zgyn`).
  - 코드는 이미 7/14(a62ed59)부터 `/stable/*`를 향하고 있었으나 **유효 키 부재로 미검증** 상태였음(핸드오프가 이걸 "TODO"로 남긴 것). v3 잔재는 레포 어디에도 없음.
  - env 키 주입 후 실측: **6종목 정상 수신**(NVDA·AAPL·MSFT·TSLA·GOOGL·META) — 매출·EPS·마진·PE·ROE·FCF 전 필드 OK.
  - **MU·VOO·ANET·AVGO·ORCL = 402**(무료 stable 플랜 심볼 화이트리스트 밖, quote부터 막힘) → 이 5종목만 WebSearch 폴백. CLAUDE.md 기록과 일치, **버그 아님·정상**.
  - 반영: 도크스트링에 실검증 상태·402 화이트리스트 명기, `FMP_402_TICKERS` 상수 추가(호출은 안 막음 — 플랜 업그레이드 시 자동 수신), 출력 폴백 안내 US 402 종목까지 확장.
- **[네이버] `naver_data.py` 국장 데스크 연결 완료**(뉴스·검색어트렌드 7/19 실측 200).
  - `kr-market-desk.md` Task 2에 배선: 뉴스=국내 원문 1차(WebSearch 보강)·검색어트렌드=리테일 심리/역발상 게이지(선택). 반환 포맷에 심리 라인 추가.
  - `desk_playbook.md` §3 kr-market-desk + `CLAUDE.md` 데이터 소스에 등록. ⚠️트렌드 상대정규화(심리 키워드 단독 그룹)·키 없으면 WebSearch 폴백·'정황' 기사 마감 전 미채택 규칙 명시.
- **[신규] `vol_gauge.py` 측정 도구 완성·검증**(stdlib·포터블, Yahoo OHLC 무키). study_log 2026-07-18 ④(GARCH) 근거.
  - 산출: 실현변동성(RV20·연율)·EWMA(0.94, 군집반영)·**폭풍 점수**(오늘 RV의 최근1년 백분위)·1년 레인지. 유니버스=market_data 재사용(portfolio.json 정본).
  - 7/19 실측: 코스피 폭풍 98%ile=극단(RV 79.8%·1년중앙 30.5%), 삼성전자 99.6·AAPL 97.6·META 95.2·ANET 93.7 = 크래시 국면 정량 확인. `--index-only`(2콜)·`--tickers`·`--json` 옵션.
  - ⚠️ **crash_tf.md 미배선**(위 '정훈 결정 대기' 참조 — 매핑 승인 후).

## ✅ 이번 세션(7/19 밤)에 완료된 것 — "좋은 스킬 세팅·성장" 배치(정훈 지시)
> 정훈이 Graphify(코드 지식그래프 도구) 공유 → 우리 레포엔 fit 낮아 **[기각·재평가 트리거]**(근거 `docs/research/tooling_log.md`), 대신 진짜 빈틈 4개 + 데이터 축적을 신설. 전부 `selfcheck` GATE PASS·렌더 검증.
- **A. 품질 게이트 `selfcheck.py` 신설** — 스크립트 24개 compile+import 스모크 + validate_report 통합. dev 커밋·머지 전 기계 게이트. 워크플로 `docs/dev_workflow.md`, CLAUDE.md 하네스② 갱신.
- **C. 문서 파이프라인 `read_doc.py` 신설** — poppler 없이 PDF 텍스트 추출(자기치유: cffi 깨짐 자동복구). `docs/research/inbox/` 컨벤션. Graphify PDF 원문+학습노트(`tooling_log.md`) 저장.
- **시장 시계열 `market_log.py` 신설** — 지수·환율·보유·워치 라이브를 `data/timeseries/quotes.jsonl`에 일별 append + `--query`추세조회. 기존 snapshot 20일치 백필(320행). snapshot=손익회계 / market_log=시세추세, 분업.
- **B. 이벤트 캘린더 `event_calendar.py` 신설** — earnings.py(실적) + `data/app/macro_events.json`(FOMC·CPI·금통위, WebSearch 검증) 병합 D-day 뷰·폰창밖 플래그. SKILL §2 배선.
- **D. 시각화 `chart_style.py` 신설** — dataviz 검증팔레트(validate_palette.js PASS)·한글폰트·recessive 스타일 공통정본. flow_chart 중앙화(출력불변)·charts.py 업그레이드(한글라벨·8색 고정순서·3%↓'기타'병합·발산색). 3종 렌더 확인.

## ⏳ 다음 세션 TODO
- (선택) **market_log 일별 자동화** — R2 루틴/보고서 파이프라인에 `market_log.py` 1줄 추가해 매일 시세 축적(현재는 수동/이번세션 1회 기록). 정훈 확인 후 배선.
- (선택) **macro_events.json 주간 검증** — macro-desk가 지나간 이벤트 제거·새 분기 일정 WebSearch 추가(현재 7/29~12/9 확정분 seed).

## ✅ 정훈 결정 완료
- **[vol_gauge] 폭풍→트랜치 매핑 = 온건 스케일 승인(7/19)** → crash_tf §6-6에 배선 완료(7,500 이진 플로어 하드 유지, <75%=100%·경계=75%·폭풍=50%·극단=25% 감산). §1 갱신 명령에 vol_gauge --index-only 추가·상황판 폭풍점수 표기 의무화. CLAUDE.md 데이터소스·desk_playbook §3 risk-desk 등록.

## 🗒️ 메모
- 토스 매매키는 **환경변수 금지**(세션마다 수동·조회전용). 위 3개는 조회전용이라 env 등록 OK(1인 전용 환경).
- 이 파일은 TODO 다 소진되면 삭제하거나 완료 로그로 정리.
