# 정훈 증권 — 루틴(스케줄) 정본

> Claude Code **Routines**(구독)에 등록하는 무인 실행 프롬프트 모음. 이 문서가 루틴 프롬프트의 source of truth다.
> 루틴은 무인(보는 사람 없음) → **선택지 띄우고 멈추지 말 것**, 머지·푸시까지 스스로 완결(CLAUDE.md 연속성 규약).
> 시각은 KST. 정훈 폰 가용 = 평일 17:30~20:50 / 주말 09:00~20:50.

---

## 현행 루틴 (2) — [7/2 정훈 확정: "아침 + 17:30 두 개만, 밤은 대화로"]

### R1. 아침 풀 브리핑 (평일 06:00~07:00경)
하루 중 가장 상세. 간밤 미장 마감 종합 + 매크로 + 경제사냥꾼 + 국장 개장 전 전략 + 폰창 집행 후보.
**+ [7/2 R3 폐지로 이관] 전일 미국 지정가 예약 체결 점검(체결/미체결·평단) + 전일 밤 지표(NFP·CPI 등 21:30발) 반영.**
→ 산출: `report_v{N}` (보유16 풀표 + STATE SNAPSHOT). 영구변경 시 master.md·portfolio.json. data/app → build_app_data → main 푸시.

```
보고서 (아침 풀 브리핑 — 무인 루틴, 선택지 띄우고 멈추지 말 것).
- portfolio-desk 스킬 풀 파이프라인: 최신 report STATE SNAPSHOT + decisions.py로 컨텍스트 복원 → 8데스크 병렬 → 강세/신중 디베이트 → PM 종합.
- 주간 첫 보고서면 self-review를 맨 먼저(캘리브레이션 부채 금지) → call_scorecard.md prepend.
- 전일 17:30 미국 지정가 예약 체결 점검(체결이면 portfolio.json·tasks.json·master.md 갱신) + 전일 밤 21:30발 지표(NFP·CPI 등) 결과 반영.
- 보유16+워치 풀표(별점·스코어·매수존·트림)·지정가 오더북·PM 사견·tasks.json 동기화. 오늘의 이슈 4개는 전부 자동 심층(선택 대기 X).
- build_app_data → validate_report(FAIL 자가교정) → score_calls --append → snapshot.py → 커밋 → main ff 머지·푸시(자동). 추측 금지·미확인 명시.
```

### R2. 폰창 집행 지시서 (평일 17:00~17:30경)
풀 데스크 X, 행동 중심. 아침 report 이어받기. 국장 종가 + 수급(flows) + triggers 점검.
→ 토스 집행안 2블록: (A)국내 시간외 17:30~18:00 살/팔 (B)미국 지정가 예약(20:50 전→22:30 집행).
→ 산출: report addendum + data/app 갱신 → main 푸시.

```
폰창 집행 지시서 (평일 17:00~17:30 — 무인 루틴, 행동 중심·풀데스크 X·선택지 띄우지 말 것).
- 아침 report 이어받기: 국장 종가 + flows 수급 + triggers.py 점검(매수존·안전핀·이벤트).
- 토스 집행안 2블록: (A)국내 시간외 17:30~18:00 정수 N주 지정가 살/팔 (B)미국 20:50 전 지정가 예약(22:30 자동집행). 가격조건은 portfolio.json alerts·tasks.json orders에 등록.
- 산출 = report addendum + tasks.json orders 갱신 → build_app_data → validate_report → 커밋 → main ff 머지·푸시(자동).
```

### 🌙 밤 = 대화형 최종정리 (스케줄 없음 — R3 폐지, 7/2 정훈 확정)
**구 R3(야간 점검 22:30~23:30) 폐지.** 근거: 폰 가용이 20:50에 끝나 야간 산출물은 실시간 독자가 없고, 미국
체결 점검·야간 지표·미장 개장초 요약은 다음날 R1(미장 마감 후)이 전부 커버 — 중복이었다. R3 담당 업무 이관:
미국 예약 체결 점검·밤 지표 반영·야간 STATE SNAPSHOT → **R1 아침**.

밤에 정훈이 대화를 열면(의무 아님·정훈이 원할 때만) **PM은 이렇게 응대한다**:
- **스코프 = 라이트 대화**: quick-check 수준(시세·트리거·평가손익) + 하루 정리 + 내일 준비 얘기. **풀 데스크 파이프라인·새 보고서 버전 금지**(필요하면 정훈이 "보고서"라고 명시 요청).
- **정본 반영은 함**: 대화 중 결정·체크("오늘 1번 했어"·"META 예약 걸었어")·영구 변경은 기존 규약대로 tasks.json/portfolio.json/master.md 갱신 → build_app_data → 커밋·main 푸시. 앱 4파일 동기화 의무는 밤 대화 세션에도 동일(7/2 교정).
- 산출물이 남을 분량이면 report **부록**(`report_v{N}_night_{날짜}.md`)으로 — 새 번호 아님.

---

## 신규 루틴 (제안 — 2026-06-25)

### R4. 주말 캘리브레이션 (토 09:00) ⭐신설
**목적**: 콜 후행검증을 독립 루틴으로 분리. 지금은 "주간 첫 보고서에 끼워넣기"라 자꾸 누락됨
(6/22 실제 누락 기록). 주말 풀가용창(09:00~)에 캘리브레이션 부채를 매주 청산한다.

```
self-review 스킬로 주간 콜 캘리브레이션을 돌려줘 (무인 루틴 — 선택지 띄우고 멈추지 말 것).
- score_calls.py --backfill 후 score_calls.py 로 별점버킷 평균전진%·방향적중·매수존 진입률·목표터치율 + 편향 플래그 산출.
- 지난 1주(또는 직전 캘리브레이션 이후) 콜 vs 실제 비교: 별점 캘리브레이션(⭐4~5 vs ⭐1~2 순서), 매수존 적중,
  목표가 방향성, 경제사냥꾼 [정정] 비율.
- docs/research/call_scorecard.md 맨 위에 이번 주 스코어카드 prepend.
- 체계적 편향(별점 쏠림·순서 역전·반복 빗나감) 발견 시 stock-deepdive 방법론/holdings_outlook 전망 교정안을
  '제안'으로 적되 자동 변경 ❌(확정은 정훈). 검증된 사실오류만 master.md §7 영구교정.
- 결과론 함정 주의(단기 노이즈로 과벌 금지, 표본·기간 명시).
- 커밋·main 푸시까지 자동 완결. 추측 금지, 미확인 명시.
```

---

## 백업 자동화 (`.github/workflows/`)
- `daily-report.yml` — 수동(workflow_dispatch)만. Routines 전환 후 백업용.
- `refresh-prices.yml` — 평일 17:25·05:30 KST cron, 키 0, Yahoo 시세만 → app/data.js.
- `deploy-app.yml` — app/** main push 시 GitHub Pages 배포.
