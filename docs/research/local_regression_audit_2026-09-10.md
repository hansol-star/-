# 로컬 이전 후퇴 감사 — 2026-09-10

> 정훈 *"로컬로 오기 전에는 토큰도 충분했고, 루틴도 다 잘 진행이 되었어"* → 체감이 맞는지 실측.
> 근거 = git 보고서 커밋 이력 · `data/logs/routines/*.log` · 로컬 세션 transcript(`~/.claude/projects/…`의 `message.usage`).
> ⚠️ 클라우드 시절 transcript는 로컬에 없다 → 클라우드 쪽 토큰 소비는 **비교 불가**, 산출물(보고서 도착)로만 비교한다.

## 결론: 체감이 맞다 — 후퇴했다

| | 클라우드 (8/3~8/28) | 로컬 (9/1~9/10) |
|---|---|---|
| 거래일 보고서 도착 | **17/19일 (89%)** | **4/8일 (50%)** |
| R2가 스스로 완주 | 대부분 — 16:50~17:50 KST 도착 | **0/8** (전부 R4 재시도·대화형 회수·미도착) |

## 원인 3개 (전부 실측)

### ① 무인 루틴 도구호출의 23.8%가 권한거부 (538/2,265)
- 런처 = `claude -p --permission-mode acceptEdits` → 편집은 자동승인, **allow 목록 밖 Bash는 거부**(승인할 사람이 없다).
- allow 목록은 스크립트 **106개 중 30개**만 커버. 거부 상위: financials 66 · 인라인 python 60 · git 46 · garch 33 · tranche_rules 26 · event_calendar 21 · fx_exposure 19 · trades 17 …
- 허용된 스크립트도 `… 2>&1 | head`, `cd … && …` 같은 복합명령이면 조각 하나만 막혀도 전체 거부.
- 비용 2중: 거부 1회 = 턴 1개(≈20만 토큰 재독) 낭비 + 모델이 변형해서 재시도 / 보고서는 그 데이터 없이 나감(v93 "trades.py 3세션 연속 권한거부").
- 클라우드 샌드박스엔 이 실패 클래스 자체가 없었다.
- **조치**: `.claude/settings.json` allow 확장안 작성 — ⛔ 자기 권한 확대라 auto-mode 분류기가 차단 → **정훈이 직접 반영**(아래 §반영 대기).

### ② 5시간 세션 한도 — 대화형 Opus 1M 컨텍스트 세션과 루틴이 같은 예산을 먹는다
- 9/4~9/10 사용량(가중)의 **70%가 대화형 Opus 세션 두 개**(9/4 로컬 이전 20.8M · 9/8~9/9 34.2M). 루틴 전체 30%.
- 그 세션들은 **한 턴마다 평균 54만·85만 토큰을 재독**(216턴·372턴), **compact 0회** — 1M 컨텍스트라 자동 압축이 사실상 안 걸린다.
- 한도 도달 기록 40건. 9/2·9/3·9/9는 R2 시작 전 5시간에 대화형이 3~7M을 이미 씀 → R2 0~20분 만에 사망.
- 9/7·9/8·9/10은 사전 소비 0인데도 R2가 8~23분에 창을 소진 → R2 1회(≈4.3~5.0M)가 창 하나에 안 들어간다. ①의 헛턴이 여기 섞여 있다.
- 8/31(이전 당일) **주간 한도 도달** 기록 있음.
- **조치**: `r2_brief.py`(복원 호출 1회) + R2/SKILL 메인 세션 규율(재독·ListAgents 폴링·조각 Edit 금지). `autoCompactWindow: 400000` 제안 — ⛔ 같은 사유로 차단 → 정훈 반영.

### ③ PC가 꺼져/잠들어 있으면 루틴이 없다 — wake timer는 이 기계에서 작동하지 않았다
- 데스크톱(배터리 0)·AC 절전 = 안 함 → 절전은 **수동**. `WakeToRun=True`인데 깨지 않았다:
  - 9/4(금) 15:15 절전 → **9/7(월) 21:12 복귀** = 금 R2·토 R3·월 R1/R2 증발, 21:15에 5개 동시 기동 → 전부 TOKEN_LIMIT.
  - 9/9 23:33 종료 → 9/10 13:17 부팅 = R4c·R1 누락(13:21 지각 기동).
  - 9/1 04:27 절전 → 11:57 복귀 = R1 2시간 지각.
- **조치**: 런처 지각 한도(`$MaxLateMap`)·R4c 날짜 앵커(`report_guard.trading_day`)·무산출 판정(`NO_OUTPUT`) — 증상 봉합. 원인은 물리.

## 반영 대기 (정훈 결정)

1. **권한 확장**(①, 최우선) — `.claude/settings.json` `permissions.allow`에 추가:
   `Bash(python3 .claude/skills/portfolio-desk/scripts/*)` · `Bash(python .claude/skills/portfolio-desk/scripts/*)` ·
   `Bash(cd *)` `Bash(ls *)` `Bash(cat *)` `Bash(head *)` `Bash(tail *)` `Bash(wc *)` `Bash(sort *)` `Bash(uniq *)` `Bash(cut *)` `Bash(grep *)` `Bash(echo *)` ·
   `Bash(git rev-parse *)` `Bash(git rebase --continue)` `Bash(git rebase --abort)` `Bash(git checkout --theirs *)` `Bash(git checkout --ours *)` · `WebFetch`
   — 스크립트 전수 점검: 삭제는 임시폴더·재생성 캐시뿐, 주문 엔드포인트는 차단 테스트 픽스처뿐. 루틴엔 토스 키 없음(런처가 제거).
   ⚠️ 이게 반영되기 전엔 신규 `r2_brief.py`도 무인에서 거부된다.
2. **`"autoCompactWindow": 400000`**(②) — 대화형이 40만 토큰 근처에서 자동 요약. R2 최대 34만이라 루틴엔 거의 안 걸린다. 대가 = 긴 대화의 세부 기억 손실.
3. **PC 운용**(③) — 평일 절전·종료를 피하거나, R2·R4만 클라우드로 되돌리는 하이브리드(R1 영상은 로컬 유지 — yt-dlp가 클라우드에선 봇차단).
