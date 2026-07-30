# 정훈 증권 — 루틴(스케줄) 정본

> Claude Code **Routines**(구독)에 등록하는 무인 실행 프롬프트 모음. 이 문서가 루틴 프롬프트의 source of truth다.
> 루틴은 무인(보는 사람 없음) → **선택지 띄우고 멈추지 말 것**, 머지·푸시까지 스스로 완결(CLAUDE.md 연속성 규약).
> 시각은 KST. 정훈 폰 가용 = 평일 17:30~20:50 / 주말 09:00~20:50.

---

## ⚡ 왜 이 구조인가 — 5시간 롤링 리셋 정렬 [2026-07-11 정훈 지시 "토큰 초기화 고려"]

토큰 한도는 **첫 사용부터 5시간 롤링으로 리셋**된다. 두 무거운 세션이 **같은 창에 겹치면 예산이 고갈**돼 보고서가 완주하지 못한다(정훈: "보고서 한번 작성도 못하냐"). 그래서:
- **가장 무겁고 시간-무관한 블록 = 유튜브 3채널 영상 자막 분석**을 **선행 프리페치 루틴(R1)**으로 떼어내 별도 창에 격리한다.
- **메인 보고서(R2)는 프리페치보다 6시간 뒤**에 둔다 → R1이 연 창(10:00~15:00)이 만료된 뒤 시작 = **신선한 풀 예산 창**에서 보고서가 돈다.
- 메인 보고서는 R1이 남긴 캐시(hunter_log·feeds_log·hunter.json·feeds.json)만 읽고 **영상 자막을 재추출하지 않는다**(가장 큰 인라인 절감). 보고서 데이터는 신선도 때문에 두 패스로 쪼개지 않는다 — 영상만 분리가 정답.

**그래도 R2가 토큰에 막히면 → 저녁 재시도 파수꾼(R4)이 리셋 후 완주시킨다 [2026-07-16 정훈 지시 "토큰으로 막힐 때 리셋 이후 자동 재실행"].**
원천 제약: ①토큰이 완전 소진된 세션은 도구 호출·트리거 등록조차 못 하고 죽는다 → "막힌 그 세션이 스스로 재예약"은 불가능. ②무인 루틴 세션에선 트리거 등록 API가 승인 게이트에 막힌다. ⇒ 작동하는 유일한 길 = **미리 등록해둔 저녁 재시도 루틴이 리셋된 신선 창에서 '오늘 보고서 났나?'를 싸게 판정(`report_guard.py --check`)하고, 안 났으면 그때 풀 보고서를 낸다.** 5시간 롤링 리셋을 '시간 간격'으로 넘기는 구조(자세히 = R4).

---

## 현행 루틴 (3) — [2026-07-11 재설계: 영상 프리페치 + 신선창 보고서 + 주말 캘리브레이션]

### R1. 영상 리서치 프리페치 (평일 10:00) ⭐신규 — 영상 전용, 메인에서 분리
목적 = 무거운 3채널 영상 자막 분석을 메인 보고서보다 **6시간 앞선 별도 리셋 창**에서 끝내 캐시에 저장. 메인은 이 캐시만 읽는다.
**볼륨(실측)**: 경제사냥꾼 일 7~8편(저녁 19~23시 ~4-5편 몰림) / 수페 주 2~3편 / 지식인 필터후 ~1편. R1(10:00)이 **전날 저녁 배치 + 오늘 아침**을 잡고(오늘/어제 필터), 그날 오후분은 R2 델타, **그날 저녁 배치는 다음날 R1**이 커버.
→ 산출: `hunter_log.md`·`feeds_log.md`(맨 위 오늘자 블록 prepend) + `hunter.json`·`feeds.json`(latest_videos·track_record·setups) + build_app_data → 커밋·main 푸시.

```
영상 리서치 프리페치 (무인 루틴 — research-feed 전용, 보고서 작성 아님, 선택지 띄우고 멈추지 말 것).
- TZ=Asia/Seoul date 로 오늘 날짜 확인 → 오늘자 블록을 쌓는다.
- research-feed 스킬/에이전트로 3채널(경제사냥꾼·수페TV·지식인사이드) 신규 영상 탐색·자막 추출 (경제사냥꾼 일 7~8편·저녁 몰림 → --max 10):
    python3 .claude/skills/portfolio-desk/scripts/hunter_latest.py --fetch --max 10
    python3 .claude/skills/portfolio-desk/scripts/hunter_latest.py --channel supe --fetch --max 3
    python3 .claude/skills/portfolio-desk/scripts/hunter_latest.py --channel jisik --fetch --max 3
  → 오늘/어제 필터 = 전날 저녁 배치(~5) + 밤 + 오늘 아침(~3) ≈ 8편. 이미 캐시(hunter.json latest_videos)에 있는 ID는 건너뛴다(디둡, 재분석 X).
- 영상별 핵심주장 → [검증/정정/미확인] 태깅(미확인 최소화 = 추가 WebSearch 2~3회 교차검증), 종목 추천+발동조건은 setups로 분해.
- **깊이 티어링(고volume 일 예산 관리)**: 종목 콜·setups 있는 영상 = 풀 분석·교차검증 / 순수 매크로 리캡·중복·쇼츠 = 1~2줄 요약. 단 전부 [검증/정정/미확인] 태깅·로깅은 유지(제목만 로깅 금지).
- 정본 기록(메인 보고서가 읽을 캐시):
    · docs/research/hunter_log.md (경제사냥꾼) / docs/research/feeds_log.md (수페TV·지식인사이드) 맨 위 오늘자 날짜스탬프 블록 prepend.
    · data/app/hunter.json (latest_videos·track_record 최신 prepend·headline·themes·setups) / data/app/feeds.json (수페·지식인 — hunter와 안 섞음).
    · 요약 필드명 = summary(필수). 신규 영상 0편이면 "신규 없음"만 기록하고 파일 손 안 대도 됨.
- python3 .claude/skills/portfolio-desk/scripts/build_app_data.py → 커밋 → git push origin HEAD:main (ff, 연속성 규약).
- 보고서 파일(report_v*)은 만들지 않는다. 이건 데이터 프리페치 전용.
```

### R2. 메인 풀 보고서 (평일 16:00) — 신선 창에서 하루 1회 종합
하루 중 유일한 풀 보고서. R1 프리페치 창(10:00~15:00) 만료 후 시작 = 신선한 예산. **영상은 R1 캐시 소비**(재추출 X). 완료 ~16:45 → 17:30 폰창에 대기 = "메인 다 완료". 최종 flows·집행은 정훈 17:30 대화 세션서 탑업.
> [7/14] SessionStart 훅이 모든 세션(루틴 포함) 시작 시 KST 날짜·장상태·최신 보고서 버전을 자동 주입 — R2 0단계 실측과 이중 안전망(프롬프트 변경·재등록 불필요).
→ 산출: `report_v{N}` (보유15 풀표 + 지정가 오더북 + PM 사견 + STATE SNAPSHOT). 영구변경 시 master.md·portfolio.json. data/app → build_app_data → main 푸시.

```
보고서 (메인 풀 브리핑 — 무인 루틴, 선택지 띄우고 멈추지 말 것).
- 0단계 실측: TZ=Asia/Seoul date + market_data.py 로 오늘 날짜·요일·장상태 확정(직전 보고서 서사에 끌리지 말 것).
- 0단계 가드: python3 .claude/skills/portfolio-desk/scripts/report_guard.py --start --kind R2 --version {오늘 번호} (running 마커 = 저녁 R4가 '막혔나' 판정할 신호. 첫 액션).
- 컨텍스트 복원: 최신 report STATE SNAPSHOT + decisions.py.
- ⚡ 영상: 오늘자 R1 프리페치 캐시(hunter_log.md·feeds_log.md 맨 위 블록 + hunter.json·feeds.json setups)를 읽어 리서치 피드·조건 트래커를 채운다. **3채널 풀 재추출 금지.** 단 R1(10:00) 이후 신규 업로드는 싸게 델타로 잡는다 = hunter_latest.py(--fetch 없이 RSS 목록만) 3채널 → 캐시에 없는 신규 ID만 `--ids <신규> --fetch`로 추가 태깅(보통 2~4편, 오후분). 오늘자 캐시가 없으면(R1 실패) 폴백으로 경제사냥꾼 1채널만 경량 인라인(SKILL §2c).
- 첫 실행 단계 = 전일 밤 미국 지정가 예약 체결 점검(체결이면 portfolio.json·tasks.json·master.md 갱신) + 전일 밤 21:30발 지표(NFP·CPI 등) 반영.
- **이벤트 캘린더** [7/20]: `event_calendar.py --within 45` = 보유 실적일 + FOMC·CPI·금통위 D-day → §3 매크로/§9 할일에 '지켜볼 것'으로 반영, 폰창 밖 이벤트는 사전 조건부 룰·예약주문 베이킹.
- 데스크 병렬(리서치 제외 최대 7 — 지역2+매크로+리스크 항상, 섹터 3종 = 트리거 게이트: ±5%·실적 D-7·테마뉴스·정훈 지목 없으면 지역데스크 시세로 갈음) → 강세/신중 디베이트 → PM 종합.
- 주간 첫 보고서면 self-review는 R3(주말)에서 청산되므로 평일 중복 X. 단 R3 누락 주면 맨 먼저 self-review.
- 보유15+워치 풀표(별점·스코어·매수존·트림)·지정가 오더북·PM 사견·tasks.json 동기화. 오늘의 이슈 4개는 전부 자동 심층(선택 대기 X).
- build_app_data → validate_report(FAIL 자가교정) → score_calls --append → snapshot.py → **market_log.py**([7/20] 오늘 시세 시계열 append, once-per-day 가드) → **build_dashboard.py**([7/20] output/dashboard.html 재생성 → Artifact 툴 있으면 `data/app/dashboard_url.txt`의 URL로 재발행해 링크 유지) → **report_guard.py --done**(validate PASS 뒤 완료 마커) → 커밋(data/app/report_run.json + data/timeseries 포함) → git push origin HEAD:main(ff, 자동). 추측 금지·미확인 명시.
```

### R3. 주말 캘리브레이션 + 리뷰 (토 09:00) — 콜 후행검증
콜 캘리브레이션을 독립 루틴으로 분리(주간 첫 보고서 끼워넣기는 자꾸 누락됨 — 6/22 실제 누락). 주말 폰 풀가용창(09:00~)에 캘리브레이션 부채를 매주 청산. 풀 데스크 X. 주말은 신규영상 적어 영상은 경량 인라인.

```
self-review 스킬로 주간 콜 캘리브레이션을 돌려줘 (무인 루틴 — 선택지 띄우고 멈추지 말 것).
- score_calls.py --backfill 후 score_calls.py 로 별점버킷 평균전진%·방향적중·매수존 진입률·목표터치율 + 편향 플래그 산출.
- 지난 1주(또는 직전 캘리브레이션 이후) 콜 vs 실제 비교: 별점 캘리브레이션(⭐4~5 vs ⭐1~2 순서), 매수존 적중,
  목표가 방향성, 경제사냥꾼 [정정] 비율.
- docs/research/call_scorecard.md 맨 위에 이번 주 스코어카드 prepend.
- 미스무브 회고(self-review §6): missed_moves.py 로 놓친 매수/매도(오미션)·good_inaction·반복 패턴 산출
  → 검증한 케이스만 missed_moves.jsonl append + docs/research/hindsight_log.md 맨 위 회고 블록 prepend
  (결과론 함정 경계 — 히스토리 짧으면 noise, good_inaction으로 무행동 편향 균형). 반복 편향은 desk_playbook §2/§3 반영 제안.
- **룰 추적 (self-review §8 · 7/30 신설 — 개정 룰은 검증된 적이 없다)**:
  ① `python3 .claude/skills/portfolio-desk/scripts/rule_tracker.py --snapshot` (원장 append)
  ② `python3 .claude/skills/portfolio-desk/scripts/rule_tracker.py --score` (누적 후행검증)
  ③ 표본 <40이면 판정 보류가 정상 — 대신 `--backfill`(29년 소급)로 방향 감각을 확인한다.
  ④ 편향이 보이면 **개정 '제안'만** 기록(자동 변경 ❌·확정은 정훈). 제안은 master §9에 후보로 남긴다.
- **역량 감사 (self-review §7 · 7/30 신설 — 이 단계를 빼지 말 것)**: 콜 채점은 *우리가 낸 답*만 검사한다.
  *애초에 못 낸 답*은 이 감사가 아니면 영원히 안 보인다(재무제표 2개월 0건 사고의 구조적 원인).
  ① `python3 .claude/skills/portfolio-desk/scripts/validate_report.py --coverage` → 레이어 결손·stale FAIL/WARN 처리.
  ② 지난 주 "데이터가 없어서 못 답한 질문" 로그를 모은다 — 그게 곧 빠진 레이어다.
  ③ `docs/data_coverage.md` §3 미보유 목록 우선순위 재평가(막혔던 소스가 열렸을 수 있다) + §2 표 갱신.
  ④ 새 결손을 찾으면 §3에 추가하고, 실현 가능한 것은 그 주 dev 작업으로 제안.
- 체계적 편향(별점 쏠림·순서 역전·반복 빗나감) 발견 시 stock-deepdive 방법론/holdings_outlook 전망 교정안을
  '제안'으로 적되 자동 변경 ❌(확정은 정훈). 검증된 사실오류만 master.md §7 영구교정.
- 결과론 함정 주의(단기 노이즈로 과벌 금지, 표본·기간 명시).
- 커밋·main 푸시까지 자동 완결. 추측 금지, 미확인 명시.
```

### R4. 토큰-리셋 재시도 파수꾼 (평일 18:30 + 21:15) ⭐신규 [2026-07-16 정훈 지시]
목적 = **16:00 R2가 5시간 롤링 토큰 한도에 막혀 보고서를 못 냈을 때, 리셋된 신선 창에서 자동으로 완주시킨다.**
막힌 세션은 스스로 재예약을 못 하므로(원천 제약, 위 §왜 이 구조인가 참조) **미리 등록해둔 파수꾼**이 저녁에 깨어나 판정한다.
두 시각인 이유: **18:30** = 오후(16시 전) 대화가 창을 미리 먹어 리셋이 저녁에 풀리는 케이스 조기 캐치 + 정훈 폰창(17:30~20:50) 안이라 실시간 확인. **21:15** = "R2가 신선한 16시 창을 혼자 다 태운" 케이스 — 이땐 16시 창이 리셋(~21:00)된 직후라야 완주 가능.
**핵심: 이미 보고서가 났으면 거의 0토큰으로 즉시 종료**(파수꾼이 매일 헛돌아도 비용 미미). 안 났을 때만 풀 보고서.

```
보고서 토큰-리셋 재시도 파수꾼 (무인 루틴 — 선택지 띄우고 멈추지 말 것, 보통은 아무것도 안 하고 끝남).
- 첫 액션: python3 .claude/skills/portfolio-desk/scripts/report_guard.py --check
    · exit 0 (= 오늘 풀 보고서 이미 완료) → 여기서 즉시 종료. 커밋·푸시·메시지 아무것도 하지 말 것. 끝.
    · exit 1 (= 오늘 16:00 R2가 토큰에 막혀 못 냄) → 아래로 진행(지금이 리셋된 신선 창).
- report_guard.py --start --kind R4 --version {오늘 번호} 로 재시도 시작 마커 기록.
- R2(메인 풀 보고서) 루틴을 그대로 수행해 오늘 보고서를 낸다. 단 이 세션이 도는 이유 자체가 '직전 실행이
  예산에 막혔음'이므로 **완주(= 완결된 validate PASS 보고서 1개 산출)를 최우선**으로 둔다:
    · 섹터 3개 데스크는 트리거 게이트에 걸린 것만(없으면 지역데스크 시세로 갈음), 영상은 오늘자 R1 캐시 소비(재추출 X).
    · 예산이 빠듯하면 '오늘의 이슈' 심층 4개 중 우선순위 낮은 건 1~2줄로 압축해도 됨(품질 < 완주). 보유15 풀표·오더북·PM 사견·STATE SNAPSHOT은 생략 금지.
- build_app_data → validate_report(FAIL 자가교정) → snapshot.py → market_log.py(once-per-day 가드) → report_guard.py --done → 커밋(report_run.json + data/timeseries 포함) → git push origin HEAD:main(ff, 자동).
- 21:15 세션은 정훈 폰창(20:50) 밖 = 무인 완주용. 보고서를 내고 push 알림만 남긴다(집행은 다음 폰창/예약주문).
```

## 🔄 동적 재개 트리거 (self-arm / disarm) — [2026-07-16 정훈 제안]

무거운 세션(보고서·대화형 풀작업)을 **시작할 때 '재개 원샷 트리거'를 미리 걸어두고, 안 막히고 완주하면 스스로 삭제**한다. 막히면 트리거가 남아 리셋 시각에 발동해 이어받는다. 정훈: "대화할 때든 정해진 루틴이든, 무조건 재개 루틴을 만들고 토큰 안 막히고 진행되면 그 루틴을 다시 제거." R4 고정 파수꾼(cron)과 목적은 같으나, 이쪽은 **아무 때나 시작하는 대화 세션까지 커버**하고 **성공 시 빈 세션조차 안 뜬다**(리셋 추정시각 정확 겨냥).

**절차 (PM이 수행 — 트리거 생성/삭제는 MCP 도구라 스크립트가 아닌 PM이 호출):**
1. **시작**: `report_guard.py --start --kind R2 --version {N}` → `reset_est`(첫사용+5h) 출력.
2. **arm**: `create_trigger(run_once_at=reset_est, create_new_session_on_fire=true, prompt=R4 파수꾼 프롬프트, notifications push ON)` → 반환된 `id`를 `report_guard.py --set-trigger <id>`로 마커에 보관.
3. **작업**: 보고서 파이프라인 진행.
4a. **완주(안 막힘)**: `report_guard.py --done` → `report_guard.py --get-trigger`로 id 조회 → **`delete_trigger(id)`로 disarm**(불필요해진 재개 트리거 제거).
4b. **토큰 막힘**: 4a에 도달 못 함 → 트리거가 `reset_est`에 발동 → 재개 세션이 `--check`(미완)→완주. 자기 재개 트리거는 원샷이라 발동과 함께 소멸(추가 disarm 불필요).

**⚠️ 제약 — 어디서 되나:**
- **대화형/권한 승인되는 세션**(정훈 폰창 대화 등): 트리거 도구 권한이 통과 → self-arm/disarm 정상. **정규 파수꾼이 못 잡는 대화 세션은 이 방식이 정답.**
- **무인 루틴(R2) 세션**: 트리거 도구 권한이 불안정(승인 게이트·MCP 연결 흔들림 실측 확인) → self-arm이 실패할 수 있다. 이 경우 **R4a/R4b 고정 파수꾼이 폴백**으로 커버(성공한 날은 `--check`로 즉시 종료라 부담 미미). 무인에서 self-arm이 검증되면 R2도 arm/disarm으로 승격.

> 요약: **대화 세션 = 동적 self-arm/disarm**(정확·성공시 0비용) / **정규 R2 = 고정 파수꾼 폴백**(권한 안정성). 둘 다 `report_guard`가 완주 여부의 단일 정본.

---

### 🌙 밤 = 대화형 최종정리 (스케줄 없음)
폰 가용이 20:50에 끝나 야간 산출물은 실시간 독자가 없다. 밤에 정훈이 대화를 열면(의무 아님·정훈이 원할 때만) **PM은 이렇게 응대한다**:
- **스코프 = 라이트 대화**: quick-check 수준(시세·트리거·평가손익) + 하루 정리 + 내일 준비 얘기. **풀 데스크 파이프라인·새 보고서 버전 금지**(필요하면 정훈이 "보고서"라고 명시 요청).
- **정본 반영은 함**: 대화 중 결정·체크("오늘 1번 했어"·"META 예약 걸었어")·영구 변경은 기존 규약대로 tasks.json/portfolio.json/master.md 갱신 → build_app_data → 커밋·main 푸시. 앱 4파일 동기화 의무는 밤 대화 세션에도 동일(7/2 교정).
- 산출물이 남을 분량이면 report **부록**(`report_v{N}_night_{날짜}.md`)으로 — 새 번호 아님.

---

## 실제 스케줄 등록 (Claude Code Routines · 앱 등록 설정값)

**공통 설정 (3개 동일)** — 앱(Routines/예약)에서 등록 시:
- **세션 유형** = `매 발동마다 새 세션`(create_new_session_on_fire=true). 이전 세션 이어받기 X.
- **환경/레포** = `hansol-star/-`.
- **시각** = KST. 앱이 로컬시각 선택이면 아래 KST 그대로, raw cron(UTC) 칸이면 UTC 값(KST−9).
- **등록 전 삭제**: 구 `아침 06:00`·`17:00 EXEC` 두 루틴 제거.

| 루틴 | 이름 | KST | cron(UTC) | 완료 알림 | 프롬프트 정본 |
|---|---|---|---|---|---|
| R1 | 영상 리서치 프리페치 | 평일 10:00 | `0 1 * * 1-5` | **OFF**(캐시만 쌓음) | 위 R1 코드블록 |
| R2 | 메인 풀 보고서 | 평일 16:00 | `0 7 * * 1-5` | **push ON**(17:30 폰창 확인) | 위 R2 코드블록 |
| R3 | 주말 캘리브레이션 | 토 09:00 | `0 0 * * 6` | 선택 | 위 R3 코드블록 |
| R4a | 토큰-리셋 재시도 ① | 평일 18:30 | `30 9 * * 1-5` | **push ON**(재시도로 냈을 때 알림) | 위 R4 코드블록 |
| R4b | 토큰-리셋 재시도 ② | 평일 21:15 | `15 12 * * 1-5` | **push ON**(무인 완주 알림) | 위 R4 코드블록 |

> 프롬프트 정본 = 위 각 루틴의 코드블록. 시간·프롬프트 변경 시 이 문서를 먼저 고치고 트리거를 재등록한다.
> **R4a·R4b는 프롬프트가 동일**(같은 R4 코드블록) — cron만 다르게 두 개 등록. 둘 다 이미 보고서가 났으면 거의 0토큰으로 즉시 끝나므로 헛돌아도 무해.
> ⚠️ 무인 세션에선 트리거 등록 API가 승인 게이트에 막힘(등록 불가 확인) → **정훈이 앱에서 직접, 또는 대화형 세션에서 "루틴 등록해줘".**
> 폐지: 구 R1 아침 06:00 풀브리핑(→16:00 이동), 구 R2 17:00 exec 전용(→16:00 오더북+17:30 대화 흡수), 구 R3 야간(7/2 폐지).

---

## 백업 자동화 (`.github/workflows/`) — 루틴과 별개, 유지
- `daily-report.yml` — 수동(workflow_dispatch)만. Routines 백업용.
- `refresh-prices.yml` — 평일 17:25·05:30 KST cron, 키 0, Yahoo 시세만 → app/data.js.
- `deploy-app.yml` — app/** main push 시 GitHub Pages 배포.
