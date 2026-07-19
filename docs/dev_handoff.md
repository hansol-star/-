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

## ⏳ 다음 세션 TODO (정훈 승인/큐 완료 — 연습 겸 하나씩)
3. **[신규] `vol_gauge.py` 설계·구현** (정훈 승인됨)
   - study_log.md 2026-07-18 ④(GARCH) 참조. Yahoo OHLC로 실현변동성 + 작년대비 백분위("폭풍 점수"). 크래시 TF 안전핀을 "7,500 이진 동결"→"변동성 백분위로 트랜치 연속 스케일"로 정밀화. stdlib·MCP 안 씀.

## 🗒️ 메모
- 토스 매매키는 **환경변수 금지**(세션마다 수동·조회전용). 위 3개는 조회전용이라 env 등록 OK(1인 전용 환경).
- 이 파일은 TODO 다 소진되면 삭제하거나 완료 로그로 정리.
