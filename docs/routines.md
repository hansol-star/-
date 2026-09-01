# 정훈 증권 — 루틴(스케줄) 정본

> 무인 실행 프롬프트 모음. **이 문서가 루틴 프롬프트의 source of truth이며, 이제 실행물 그 자체다** —
> ★[9/1 경로 B] 런처(`.claude/routines/run_routine.ps1`)가 매 실행마다 `routine_prompts.py`로 아래 코드블록을
> **직접 읽어** `claude -p`에 넣는다. 舊 웹 Routines는 앱에 붙여둔 **사본**이 돌아서, 이 문서를 고쳐도
> 실제 루틴은 안 바뀌었다(8/6 확인된 제약). 그 괴리가 이 전환으로 사라졌다 — 문서를 고치면 다음 실행부터 반영된다.
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
- `python3 .claude/skills/portfolio-desk/scripts/kst_now.py` 로 오늘 날짜 확인 → 오늘자 블록을 쌓는다.
- research-feed 스킬/에이전트로 3채널(경제사냥꾼·수페TV·지식인사이드) 신규 영상 탐색·자막 추출 (경제사냥꾼 일 7~8편·저녁 몰림 → --max 10):
    python3 .claude/skills/portfolio-desk/scripts/hunter_latest.py --fetch --max 10
    python3 .claude/skills/portfolio-desk/scripts/hunter_latest.py --channel supe --fetch --max 3
    python3 .claude/skills/portfolio-desk/scripts/hunter_latest.py --channel jisik --fetch --max 3
- ★[8/30] **자막 원문 소급 회수 — 1회성 완료(432/432)**. 아래는 결손 발생 시에만:
    python3 .claude/skills/portfolio-desk/scripts/hunter_latest.py --archive-backfill 50
  배경 = 舊 기본 저장경로가 `/tmp`(세션 종료 시 소멸) + `.gitignore`가 `**/hunter_yt/`를 막아
  **두 겹으로** 유실됐고, 아카이브 441편 중 자막 원문이 **0편** 남아 있었다(8/30 발견).
  경로는 이제 `data/transcripts/hunter/`(레포 내·커밋됨)이고 신규분은 자동 영구 저장된다.
  ⚠️ **하루 20편 배선은 폐기**(정훈 지적 "매일 20편씩? 굳이 지금 최대한 해"). 실측 속도가
  **10~18초/편**이라 432편을 **약 80분에 일괄 회수**했다 — 3주로 나눌 이유가 없었다.
  내가 429 페이싱을 근거 없이 보수적으로 추정한 것이 원인. **추정으로 배치 크기를 정하지 말고
  먼저 실측할 것.**
  ⚠️ 진척은 `validate_report.check_transcript_persistence()`가 WARN으로 상시 보고한다.
  → 오늘/어제 필터 = 전날 저녁 배치(~5) + 밤 + 오늘 아침(~3) ≈ 8편. 이미 캐시(hunter.json latest_videos)에 있는 ID는 건너뛴다(디둡, 재분석 X).
- 영상별 핵심주장 → [검증/정정/미확인] 태깅(미확인 최소화 = 추가 WebSearch 2~3회 교차검증), 종목 추천+발동조건은 setups로 분해.
- **깊이 티어링(고volume 일 예산 관리)**: 종목 콜·setups 있는 영상 = 풀 분석·교차검증 / 순수 매크로 리캡·중복·쇼츠 = 1~2줄 요약. 단 전부 [검증/정정/미확인] 태깅·로깅은 유지(제목만 로깅 금지).
- **[8/22 상시 · 정훈 승인 · ★9/1 고해상도 배선] 화면 교차검증**:
  **⓵ 표적 검증(주 경로) = `yt_frames.py <ID> --hires --at <시각>`** — 자막에서 수치·차트 주장이 나온
  **그 시점 1장**을 720p로 받아 Read로 판독한다. 3~4초·1장 ≈1,500~2,500토큰.
  **⓶ 훑어보기 = `--hires --count 4`**(영상 전체 균등분할) 또는 값싼 스토리보드 `--sheets 1`.
  ★[9/1] 로컬 이전으로 yt-dlp 스트림이 열려 고해상도 경로가 살아났다. **쇼츠도 이제 읽힌다** —
  舊 스토리보드는 쇼츠 타일이 50×90이라 판독 불가였고 채널 업로드 상당수가 쇼츠였다.
  실측: 720×1280에서 삽화 속 작은 영문 표제까지 판독.
  **표적** = ①[정정] 이력 있는 영상 ②수치·차트 주장인데 웹서치가 갈리는 영상 ③자막 실패 영상.
  **상한 = 1회 실행당 2편 · 편당 2장.** 판독분은 [화면확인] 태그.
  ⚠️ 화면은 자막의 **보조 축**이고 그 자체로 2차 출처다 — 수치는 1차 출처와 교차한다.
  ★ 8/22 첫 실증에서 잡힌 오차는 **채널이 아니라 우리 전사 오차**였다(삼성 영업활동현금흐름
  로그 105.1조 ↔ 화면 원문 105조 8,800억) — **화면은 우리 요약도 검사한다.**
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
- 0단계 실측: `python3 .claude/skills/portfolio-desk/scripts/kst_now.py` + market_data.py 로 오늘 날짜·요일·장상태 확정(직전 보고서 서사에 끌리지 말 것).
- 0단계 가드: python3 .claude/skills/portfolio-desk/scripts/report_guard.py --start --kind R2 --version {오늘 번호} (running 마커 = 저녁 R4가 '막혔나' 판정할 신호. 첫 액션).
- 컨텍스트 복원: 최신 report STATE SNAPSHOT + decisions.py.
- ⚡ 영상: 오늘자 R1 프리페치 캐시(hunter_log.md·feeds_log.md 맨 위 블록 + hunter.json·feeds.json setups)를 읽어 리서치 피드·조건 트래커를 채운다. **3채널 풀 재추출 금지.** 단 R1(10:00) 이후 신규 업로드는 싸게 델타로 잡는다 = hunter_latest.py(--fetch 없이 RSS 목록만) 3채널 → 캐시에 없는 신규 ID만 `--ids <신규> --fetch`로 추가 태깅(보통 2~4편, 오후분). 오늘자 캐시가 없으면(R1 실패) 폴백으로 경제사냥꾼 1채널만 경량 인라인(SKILL §2c).
- 첫 실행 단계 = 전일 밤 미국 지정가 예약 체결 점검(체결이면 portfolio.json·tasks.json·master.md 갱신) + 전일 밤 21:30발 지표(NFP·CPI 등) 반영.
- **이벤트 캘린더** [7/20]: `event_calendar.py --within 45` = 보유 실적일 + FOMC·CPI·금통위 D-day → §3 매크로/§9 할일에 '지켜볼 것'으로 반영, 폰창 밖 이벤트는 사전 조건부 룰·예약주문 베이킹.
- **[8/5 배선] 신규 3종** — SKILL §0-2c·§2 수집단계에 상세. 여기선 실행 순서만:
  · `memory_recall.py <종목>` = **⭐2 이하 보유 필수** + 그날 오더 나가는 종목(3~5회, 전 종목 순회 금지).
    🟠 열린 아젠다가 뜨면 이번 보고서에서 상태 갱신. 불리한 항목 건너뛰지 말 것.
  · `edgar_search.py --events --days 30` = 미국 8-K item 스트림(`dart_disclosure`의 미국 짝). 🚨critical은 본문 노출.
    `--q "문구"` 전문검색은 **트리거 게이트**(논지를 1차 문서로 확정할 때만 — 습관적 호출 금지).
  · `peer_compare.py` = **반드시 `financials.py --all --save` 다음**(먼저 돌리면 어제 숫자로 순위를 매긴다).
    두 렌즈가 갈리는 지점만 보고서에 쓴다. [8/6] 워치 편입으로 n이 커졌으나(전력 3→10·반도체 5→10)
    **그룹은 경제적 동질 피어가 아니라 데스크 담당 범위**다 — "업종 내 위치"가 아니라
    "우리 커버리지 안 순위"로 서술할 것. 피어 재무 갱신은 R3(`--with-peers`) 담당.
  ⚠️ 셋 다 **측정·탐색·읽기 전용 — 별점·스코어·트랜치 어떤 룰도 바꾸지 않는다.**
- **[8/5] 폭풍 %ile 정본 = `vol_gauge.py`.** 하드플로어(S&P ≥70%ile)·항복 가산 판정에 **`garch` 값을 인용하지 말 것** — 8/1~8/4 보고서 4회 연속으로 garch 값을 하드플로어에 인용해 판정이 갈렸다. `garch`는 선행 대조·발산 경보(|두 %ile 차이| ≥20p = 국면 전환) 전용.
- 데스크 병렬(리서치 제외 최대 7 — 지역2+매크로+리스크 항상, 섹터 3종 = 트리거 게이트: ±5%·실적 D-7·테마뉴스·정훈 지목 없으면 지역데스크 시세로 갈음) → 강세/신중 디베이트 → PM 종합.
- 주간 첫 보고서면 self-review는 R3(주말)에서 청산되므로 평일 중복 X. 단 R3 누락 주면 맨 먼저 self-review.
- 보유15+워치 풀표(별점·스코어·매수존·트림)·지정가 오더북·PM 사견·tasks.json 동기화. 오늘의 이슈 4개는 전부 자동 심층(선택 대기 X).
- build_app_data → validate_report(FAIL 자가교정) → **rule_tracker.py --snapshot**([8/6] 룰1 사다리 원장 매일 append — RESET 정책상 매일 재계산이 전제. 7/30~8/5 7일 정지 재발방지, validate가 FAIL로 감시) → score_calls --append → snapshot.py → **market_log.py**([7/20] 오늘 시세 시계열 append, once-per-day 가드) → **build_dashboard.py**([7/20] output/dashboard.html 재생성 → Artifact 툴 있으면 `data/app/dashboard_url.txt`의 URL로 재발행해 링크 유지) → **report_guard.py --done**(validate PASS 뒤 완료 마커) → 커밋(data/app/report_run.json + data/timeseries 포함) → git push origin HEAD:main(ff, 자동). 추측 금지·미확인 명시.
```

### R3. 주말 캘리브레이션 + 리뷰 (토 09:00) — 콜 후행검증
콜 캘리브레이션을 독립 루틴으로 분리(주간 첫 보고서 끼워넣기는 자꾸 누락됨 — 6/22 실제 누락). 주말 폰 풀가용창(09:00~)에 캘리브레이션 부채를 매주 청산. 풀 데스크 X. 주말은 신규영상 적어 영상은 경량 인라인.

```
self-review 스킬로 주간 콜 캘리브레이션을 돌려줘 (무인 루틴 — 선택지 띄우고 멈추지 말 것).
- 🔓 **[9/1 해소] 프롬프트 수정 제약은 사라졌다** — 舊 R1·R2·R3는 `http_api` 트리거라 `update_trigger`가 거부됐고
  (8/6 실측), 그래서 *"루틴 최신화의 정석 = 스킬·에이전트 파일을 고친다"*는 우회로가 정본이었다.
  **로컬 경로 B에선 런처가 이 문서를 매 실행 직접 읽으므로 프롬프트를 여기서 고치면 그대로 반영된다.**
  ⚠️ 그 대가 = **이 문서가 깨지면 루틴이 깨진다.** 코드블록 구조를 바꿨으면
  `python3 .claude/skills/portfolio-desk/scripts/routine_prompts.py --check`로 5종 추출을 확인할 것.
  (스킬·에이전트 파일을 고치는 우회로도 여전히 유효하고, 여러 루틴에 공통으로 걸리는 변경은 그쪽이 낫다.)
- 🎬 **[8/12 신설] 영상 수집 구조 개편 — `--max` 상한 폐지 방향**: 8/12 API 감사에서 **커버리지 73%·구조적 누락 86건** 확인.
  원인 ①R1 평일만 실행(누락 28%가 주말) ②`--max 10` 상한 + 저녁 몰림(39%가 17시 이후) —
  SKILL의 *'저녁분은 다음날 R1이 커버'* 전제가 **다음날도 10편 상한**이라 깨져 있었다(누락이 월·화에 집중된 게 증거).
  ⇒ **`hunter_latest.py --catchup`**(신설) = 고정 N편이 아니라 **아카이브 최신 날짜 이후 전량** 수집.
  월요일이면 금~일 3일치가 통째로 들어온다. **API 키 필요**(RSS·스크레이프는 최신 N편만 보여줘 원리적으로 불가).
  키 없으면 자동으로 기존 폴백 → 루틴이 깨지지 않는다.
- 🔍 **[8/12 신설] 주간 누락 감사 = `hunter_audit.py --days 14 --save`** (R3 토요일에 배선).
  아카이브 vs 실제 업로드를 대조해 커버리지·구조적 누락·요일/시간 편중을 낸다.
  ⚠️ **이 감사는 API 없이는 원리적으로 불가능하다** — 그래서 8/12까지 구멍을 *알 방법 자체가 없었다*.
  구조적 누락이 잡히면 R1 설정을 의심할 것.
- 🩺 **[8/12 신설] API 생존 점검 = `api_health.py --quiet`** — 외부 소스 13종 실호출.
  ★[9/1] `--quiet` = 정상 소스는 숨기고 **실패·미설정·합계만**(§dev_workflow §1c). ⚪미설정은 quiet에서도 나온다 —
  "폴백으로 돌고 있다"는 뜻이라 조용히 낡을 수 있는 축이기 때문이다.
  CLAUDE.md 교훈('외부 API는 말없이 죽는다')의 실행 도구. R3 주간 + 장애 의심 시 수시.
  ⚠️ 점검 도구는 **본 스크립트의 함수를 재사용**해야 한다 — 초판이 다른 엔드포인트를 때려 위양성 4건을 냈다.
- 📌 **[8/12 신설] 당일 지시 채널 = `data/app/session_directive.json`** — 위 제약의 실무 해법. 정훈이 대화 세션에서 "오늘만 이렇게 해줘"라고 하면 이 파일에 적고, **SessionStart 훅**(`.claude/hooks/session-start.sh`)이 `date`가 오늘(KST)일 때만 그 지시를 모든 세션(무인 루틴 포함) 시작 컨텍스트에 주입한다. 날짜가 지나면 자동 만료 = 지우는 걸 잊어도 다음날 루틴을 오염시키지 않는다. 필드 = `date`(YYYY-MM-DD·KST) · `scope`(대상 세션) · `text`(지시 본문) · `issued_by` · `issued_at`. **첫 사용 = 8/12** ("16:00 R2는 새 번호 말고 v73을 디벨롭하라").
- ⚠️[8/6] `--backfill` 전에 **`git fetch --unshallow origin`** 먼저 — 원격 세션은 얕은 클론(실측 3일치)이라 그대로 돌리면 원장이 잘린다(8/6 실측: 135콜 중 75콜 소실 예정이었음). 백필은 이제 기존 원장과 **병합**하고 얕으면 중단한다(--force로만 강행).
- score_calls.py --backfill 후 score_calls.py 로 별점버킷 평균전진%·방향적중·매수존 진입률·목표터치율 + 편향 플래그 산출.
- 지난 1주(또는 직전 캘리브레이션 이후) 콜 vs 실제 비교: 별점 캘리브레이션(⭐4~5 vs ⭐1~2 순서), 매수존 적중,
  목표가 방향성, 경제사냥꾼 [정정] 비율.
- docs/research/call_scorecard.md 맨 위에 이번 주 스코어카드 prepend.
- 미스무브 회고(self-review §6): missed_moves.py 로 놓친 매수/매도(오미션)·good_inaction·반복 패턴 산출
  → 검증한 케이스만 missed_moves.jsonl append + docs/research/hindsight_log.md 맨 위 회고 블록 prepend
  (결과론 함정 경계 — 히스토리 짧으면 noise, good_inaction으로 무행동 편향 균형). 반복 편향은 desk_playbook §2/§3 반영 제안.
- **[8/6] 피어 재무 주간 갱신**: `python3 .claude/skills/portfolio-desk/scripts/financials.py --with-peers --save`
- **★[8/30] 데이터 자산 주간 갱신** — 받아온 걸 남기는 축(정훈 지시 "n개년치 다 저장"):
    python3 .claude/skills/portfolio-desk/scripts/ohlcv_backfill.py            # 주가 OHLCV 41종목(상장 이래)
    python3 .claude/skills/portfolio-desk/scripts/ohlcv_backfill.py --stats    # 현황만 볼 때
  재무 원본은 위 `financials.py --save`가 자동으로 `data/financials/<TICKER>.json`에 **전 시계열**을 남긴다
  (舊엔 app 요약 5기/8기만 남기고 나머지를 버렸다 — 주석은 저장한다고 적혀 있었으나 실제로는 안 했다).
  ⚠️ 국내 재무 심화(DART 2015~)는 상장·정정 이슈가 없으면 **분기 1회면 충분**:
    python3 .claude/skills/portfolio-desk/scripts/dart_facts.py --code 005930 --years 2015,...,2025 --json
  ⚠️ 보유량 감소는 `validate_report.check_data_archive()`가 WARN으로 잡는다.
  → `peer_compare.py`가 쓰는 워치 종목(SK하이닉스·삼성전기·두산에너빌·한화에어로 등 13종) 재무를 채운다.
  **매일 도는 R2엔 붙이지 않는다**(국내 1종목 1~2분 = 완주 예산 잠식). 피어 펀더는 분기 단위로 바뀌므로 주 1회로 충분.
  저장은 **병합**이라 보유 14종목 데이터를 덮어쓰지 않는다.
- **룰 추적 (self-review §8 · 7/30 신설 — 개정 룰은 검증된 적이 없다)**:
  ① `python3 .claude/skills/portfolio-desk/scripts/rule_tracker.py --snapshot` (원장 append)
  ② `python3 .claude/skills/portfolio-desk/scripts/rule_tracker.py --score` (누적 후행검증)
  ③ 표본 <40이면 판정 보류가 정상 — 대신 `--backfill`(29년 소급)로 방향 감각을 확인한다.
  ④ 항복 가산 검증 = `capitulation_validate.py`(네이버 2016~ 실측 + VIX 36년 프록시 2경로).
     ⚠️ **해금 구간(낙폭 ≤ -25%)에서만 판정**한다 — 전 구간으로 보면 결론이 뒤집힌다(7/30 실측).
  ⑤ 편향이 보이면 **개정 '제안'만** 기록(자동 변경 ❌·확정은 정훈). 제안은 master §9에 후보로 남긴다.
- **[8/24 신설] 손익비 추이 + 가드·배선 주간 점검** (self-review §0·§7에 심어둠 — 프롬프트 수정 불요):
  ① `trades.py --realized` = 손익비·기대값 추이. **승률이 올라도 손익비가 안 오르면 편향은 그대로다.**
     ⚠️ 집계를 보면 **시점부터 가른다** — 8/24에 손익비 0.81로 *"룰4가 조기 익절을 제도화했다"* 가설을
     세웠다가 시점 분해에서 반증됐다(40건이 룰4보다 먼저·룰4 이후는 평균이익 +23.0%로 개선). d142 종결.
     **재검증 트리거(d143)**: 룰4 이후 실현 **20건** 도달 시 재판정(현재 5건 = 유보).
  ② `guard_selftest.py --coverage` = 음성테스트 없는 가드(= 초록불 진위 미확인). 9/1 기준 22/39.
     ⚠️ 등록 우선순위 = **실사고가 있었던 가드**부터. 남은 최대 결핍은 `check_trade_ledger`(체결 원장 대사)로,
     픽스처에 trades.py 실행이 필요해 아직 미등록이다 — 돈이 걸린 유일한 무검증 가드다.
  ③ `wiring_audit.py --features` = 스크립트는 불리는데 그 **기능**은 안 불리는 것. 현재 25건.
     ⚠️ 늘었으면 **새로 만든 기능이 판단에 안 흘러가고 있다는 뜻**이다(8/24 손익비가 그랬다).
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

### R4. 토큰-리셋 재시도 파수꾼 (평일 **20:00** + 21:15) ⭐신규 [2026-07-16 정훈 지시 · ★8/27 R4a 시각 개정]
목적 = **16:00 R2가 5시간 롤링 토큰 한도에 막혀 보고서를 못 냈을 때, 리셋된 신선 창에서 자동으로 완주시킨다.**
막힌 세션은 스스로 재예약을 못 하므로(원천 제약, 위 §왜 이 구조인가 참조) **미리 등록해둔 파수꾼**이 저녁에 깨어나 판정한다.
두 시각인 이유: **20:00** = 오후(16시 전) 대화가 창을 미리 먹어 리셋이 저녁(≈19:30)에 풀리는 케이스 + 정훈 폰창(17:30~20:50) 안이라 실시간 확인. **21:15** = "R2가 신선한 16시 창을 혼자 다 태운" 케이스 — 이땐 16시 창이 리셋(~21:00)된 직후라야 완주 가능.

> **🚨[8/27 실측 개정 — 舊 18:30은 구조적으로 무력했다]** 8/27에 R1·R2·R4a **세 루틴이 전부** `"You've hit your session limit"`로 죽었다(R1 01:08 UTC·R2 07:22 UTC 18분 소진 후·R4a 09:36 UTC). 문제는 R4a다 — **18:30 KST(09:30 UTC)은 R2(16:00 KST)가 태운 바로 그 5시간 창 안**이라(그날 리셋 10:30 UTC = 19:30 KST), *R2가 토큰에 막혀 죽는 순간 파수꾼도 같은 이유로 죽는다.* **파수꾼이 존재 이유인 상황에서만 발동 불가**였다. ⇒ **R4a를 20:00 KST(`0 11 * * 1-5`)로 이동.** 이제 두 파수꾼이 서로 다른 창을 덮는다: R4a=오전 대화가 연 창의 리셋(≈19:30) 직후 / R4b=R2가 16:00에 연 창의 리셋(≈21:00) 직후.
> **교훈(8/22·8/23 계열)**: 폴백을 "다른 시각"에 두는 것으로는 부족하다 — **원인이 공유 자원(토큰 창)이면 폴백도 그 자원을 공유하는지**를 봐야 한다. 시각이 다른 것과 창이 다른 것은 다르다.
> ⚠️ **남은 근본 문제는 스케줄이 아니라 예산이다.** 대화형 세션과 무인 루틴이 같은 5시간 롤링 예산을 쓴다 — 정훈과 길게 작업한 날은 루틴이 굶는다. 8/27엔 정훈이 직접 요청해 v86을 대화형으로 냈기에 표가 안 났을 뿐, **아무도 요청하지 않은 날이면 보고서가 통째로 없다.**
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
- build_app_data → validate_report(FAIL 자가교정) → **rule_tracker.py --snapshot**([8/6] 룰1 원장 매일 append) → snapshot.py → market_log.py(once-per-day 가드) → report_guard.py --done → 커밋(report_run.json + data/timeseries 포함) → git push origin HEAD:main(ff, 자동).
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

## 실제 스케줄 등록 — ★[2026-09-01] 웹 Routines → 로컬 작업 스케줄러 (경로 B)

정훈 지시 *"무인 다 로컬로 빼자"*. 배경 = 8/31 로컬 이전으로 yt-dlp 스트림·자막(429 우회)이 열렸는데
**그 이득이 가장 큰 R1이 웹에서 돌아 열린 경로에 닿지 못하고 있었다.**

### 구성
| 조각 | 파일 | 역할 |
|---|---|---|
| 프롬프트 정본 | `docs/routines.md` (이 문서) | 아래 각 루틴 코드블록 = 실행 프롬프트 그 자체 |
| 추출기 | `.claude/skills/portfolio-desk/scripts/routine_prompts.py` | 문서 → 프롬프트(`--check`로 5종 검사) |
| 런처 | `.claude/routines/run_routine.ps1` | 토스 키 제거 · PATH/인코딩 고정 · 실행 · 로그/상태/알림 |
| 등록기 | `.claude/routines/register_tasks.ps1` | 작업 스케줄러 5개 등록(`-Unregister`로 해제) |
| 감시 | `validate_report.check_routine_health()` | 상태파일을 읽어 **실패·정지를 WARN으로 노출** |

### 등록된 작업 (`\JeonghunDesk\` · KST = 머신 로컬시각)
| 루틴 | 작업 이름 | KST | 요일 |
|---|---|---|---|
| R1 | `JD-R1-video-prefetch` | 10:00 | 평일 |
| R2 | `JD-R2-main-report` | 16:00 | 평일 |
| R3 | `JD-R3-calibration` | 09:00 | 토 |
| R4a | `JD-R4a-retry-2000` | 20:00 | 평일 |
| R4b | `JD-R4b-retry-2115` | 21:15 | 평일 |

확인·수동실행:
```
Get-ScheduledTask -TaskPath '\JeonghunDesk\' | Format-Table TaskName,State
Start-ScheduledTask -TaskPath '\JeonghunDesk\' -TaskName JD-R2-main-report
powershell -ExecutionPolicy Bypass -File .claude/routines/run_routine.ps1 -Kind r2 -DryRun
```

### 이 전환이 지는 4가지 책임 — 웹 Routines가 공짜로 주던 것들
1. **자격증명 격리** — 토스 키를 8/31에 사용자 환경변수로 저장했으므로 스케줄러 자식 프로세스가 **그대로 상속**한다.
   런처가 `TOSS_CLIENT_ID`/`TOSS_CLIENT_SECRET`를 **명시적으로 제거**한 뒤 `claude`를 띄운다
   (CLAUDE.md 운영제약 = 사람이 안 보는 세션에 매매 권한을 주지 않는다). 실행 로그에 제거 사실이 매번 남는다.
2. **실패 가시화** — 웹은 실패가 대시보드에 남았다. 로컬은 아무 데도 안 남는다(§3 경로 B 단점).
   ⇒ 런처가 `data/logs/routines/last_status.json`에 verdict를 남기고,
   `validate_report`가 그걸 읽어 **실패·3일 이상 정지**를 WARN으로 올린다. 로그는 커밋 안 함(.gitignore).
3. **시각 정합** — KST는 UTC+9 고정으로 계산한다(`kst_now.py`와 같은 규약). 로컬 시계 설정에 기대지 않는다.
4. **놓친 실행 따라잡기** — `StartWhenAvailable`·`WakeToRun`. 절전이면 깨워서 돌리고, 시각을 놓쳤으면 깨어난 직후 실행.
   ⚠️ **전원이 꺼져 있으면 불가능하다** — 이게 경로 B의 물리적 한계이고, 웹 대비 유일한 실질 후퇴다.

### ⚠️ 사람이 해야 하는 3가지 (에이전트가 못 함)
1. **로그인 + 워크스페이스 신뢰** — 레포에서 `claude`를 대화형으로 1회 실행 → `/login` + 신뢰 대화상자 수락.
   안 하면 모든 루틴이 `NOT_LOGGED_IN`으로 끝난다(실측). 신뢰를 수락해야 `.claude/settings.json`의
   허용목록이 적용된다 — 안 그러면 매 실행이 권한에 막힌다. ✅ 9/1 수락 확인.
   **1b. ★git 쓰기 권한 — 에이전트가 못 여는 유일한 항목.** `.claude/settings.json`은 **대화형 세션에서도
   에이전트가 쓸 수 없다**(자기 권한 상향 방지 가드가 Bash·Edit 양쪽을 막는다 — 9/1 실측).
   `permissions.allow`에 `git add`·`git commit`·`git push origin HEAD:*`·`git merge-base`·`git rebase origin/main`이
   없으면 **모든 루틴이 일만 하고 커밋을 못 한다**(9/1 R1 실측). 정훈이 직접 넣어야 한다.
   ⚠️ allow는 **접두사 매칭**이라 뒤에 붙는 `--force`를 못 막는다 ⇒ `.claude/hooks/git-write-guard.sh`가
   인자 순서와 무관하게 force push·`reset --hard`·`clean -f`·`checkout main`을 차단한다(음성테스트 11/11).
2. **웹 Routines 5개 끄기** — 안 끄면 웹·로컬이 같은 보고서를 두 번 낸다(푸시 충돌).
3. **절전 정책** — 10:00·16:00·20:00·21:15에 머신이 깨어 있어야 한다. `WakeToRun`은 절전은 깨우지만 종료는 못 깨운다.
   ⚠️ **9/1 실측: `WakeToRun=True`·wake timer(AC/DC 둘 다 1)인데도 안 깼다.** R1 10:00 예약 → 04:27 절전 →
   11:57 복귀 → **12:00 지각 실행**(StartWhenAvailable). 최대 절전(하이버네이트) 진입 시 wake timer 불발로
   추정하나 **미확정**. 지각은 이제 `late_min`으로 기록·WARN되지만 **감지일 뿐 해결이 아니다.**

### 알림 — ★[9/1 해소] 폰 푸시 = `notify.py`(텔레그램)
舊 서술("대체되지 않는다·인정된 후퇴")은 9/1에 해소됐다. 웹 R2/R4의 **push ON**을 대체하는 이유는
편의가 아니다 — 정훈 폰창(평일 17:30~20:50)은 **국내 시간외단일가(~18:00)와 겹치는 유일한 실시간 거래창**인데,
16:00 R2가 오더북을 내도 앱을 직접 열어야만 알 수 있었다. 윈도우 토스트는 **PC 앞에 있을 때만** 보인다.

- **경로**: `notify.py` — 텔레그램 봇 API(무료·stdlib urllib·서버 불요). 런처가 매 루틴 종료 시 호출한다.
- **내용**: 판정 아이콘 + 소요시간 + (지각/미커밋 있으면 그 사실) + **OK일 때 대기 오더 요약**
  (최근 14일 · 미체결분만 — 상태만으로 거르면 6~7월 잔재까지 23건이 딸려와 노이즈가 된다).
- **키**: `TELEGRAM_BOT_TOKEN` · `TELEGRAM_CHAT_ID`. ⚠️ **알림 전송 전용이라 계좌 권한이 없다** —
  토스 키와 달리 무인 세션에 노출해도 매매 위험이 없으므로 런처의 §토스 스크럽 대상이 아니다.
- ⚠️ **미설정이면 exit 3으로 미발송을 분명히 말한다**(런처 로그에 남는다).
  성공한 척하는 폴백을 만들지 않는다 — 8/22 *"가드 없는 폴백은 침묵보다 나쁘다"*.
- 확인: `python3 .claude/skills/portfolio-desk/scripts/notify.py --check` ·
  본문 미리보기 `--orders --dry-run`

### 판정 — 런처는 '말'이 아니라 '워킹트리'를 본다 [9/1 신설]
`run_routine.ps1`이 매 실행 끝에 `git status --porcelain`을 보고, 비어 있지 않으면 **`verdict=UNCOMMITTED`**로 찍는다.
9/1 R1이 영상 6편을 분석해놓고 커밋을 못 했는데 **`verdict=OK`로 기록된** 사고 때문이다 —
런처의 영어 정규식(`permission denied` 등)이 모델의 **한국어 산문** 설명을 못 잡았다.
같이 기록되는 필드: `uncommitted`(건수) · `scheduled`(예정시각) · `late_min`(지각 분).
`validate_report.check_routine_health()`가 이 셋을 읽어 WARN으로 올린다.

## 백업 자동화 (`.github/workflows/`) — 루틴과 별개, 유지
- `daily-report.yml` — 수동(workflow_dispatch)만. Routines 백업용.
- `refresh-prices.yml` — 평일 17:25·05:30 KST cron, 키 0, Yahoo 시세만 → app/data.js.
- `deploy-app.yml` — app/** main push 시 GitHub Pages 배포.
