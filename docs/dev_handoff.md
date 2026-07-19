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

## ⏳ 다음 세션 TODO (정훈 승인/큐 완료 — 연습 겸 하나씩)
1. **[FMP] `fundamentals.py` v3→stable 마이그레이션** ★먼저 추천
   - FMP가 레거시 `/api/v3/*` 엔드포인트 폐기(403 "Legacy Endpoint"). 키는 유효 — 신형 `/stable/*`는 200 확인(`stable/quote?symbol=NVDA` → NVDA $202.81).
   - `fundamentals.py`가 v3 쓰면 stable로 교체 → 미국주 펀더 하드넘버(매출·EPS·마진·FCF) 부활(현재 WebSearch 폴백 중).
2. **[네이버] `naver_data.py`를 국장 데스크에 연결**
   - 뉴스 = kr-market-desk 국내 뉴스 소스(US 리전 WebSearch 대체·보강).
   - 검색어트렌드 = 리테일 관심/심리 게이지(개인 수급·"공포에 사라" 역발상 신호). 심리 키워드는 자기 그룹 단독 조회(정규화 주의).
3. **[신규] `vol_gauge.py` 설계·구현** (정훈 승인됨)
   - study_log.md 2026-07-18 ④(GARCH) 참조. Yahoo OHLC로 실현변동성 + 작년대비 백분위("폭풍 점수"). 크래시 TF 안전핀을 "7,500 이진 동결"→"변동성 백분위로 트랜치 연속 스케일"로 정밀화. stdlib·MCP 안 씀.

## 🗒️ 메모
- 토스 매매키는 **환경변수 금지**(세션마다 수동·조회전용). 위 3개는 조회전용이라 env 등록 OK(1인 전용 환경).
- 이 파일은 TODO 다 소진되면 삭제하거나 완료 로그로 정리.
