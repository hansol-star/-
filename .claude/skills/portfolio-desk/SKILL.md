---
name: portfolio-desk
description: 정훈의 일일 투자 포트폴리오 보고서 생성 파이프라인. 사용자가 "보고서", "분석해줘", "오늘 시장", "브리핑"이라고 하거나 경제사냥꾼 영상 분석, 보유종목 점검, 현금 배분, CPI/FOMC 대응을 요청하면 반드시 이 스킬을 따른다. PM이 8개 서브에이전트 데스크(지역2·섹터3·매크로·리서치·리스크)를 병렬 호출해 종합하고, 보고서를 docs/reports/에 저장·git 커밋한다. 토스 조회·경제사냥꾼 탐색·세션 연속성 규칙 포함.
---

# Portfolio Desk — 정훈 일일 투자 보고서 파이프라인 (PM 오케스트레이션)

너는 **PM(메인 에이전트)**이다. 9개 데스크(지역2·섹터3·매크로·리서치·리스크·대가흐름 — 섹터 3종·대가흐름은 트리거 게이트, 리서치는 R1 캐시)를 **병렬 서브에이전트**로 돌려 입력을 모으고,
정훈의 실제 보유·룰에 비춰 최종 종합한다. **무게는 PM 종합에.**
투자 자문 아님 — 모든 레벨(목표가·매수존·별점)은 분석 참고, 최종 결정은 정훈. 보고서에 명시.

## 0. 컨텍스트 복원 (보고서 요청 시 항상 먼저)

00. **⚠️⚠️ 오늘 날짜·장 상태부터 실측 [2026-07-06 신설 — 날짜 하루 밀림 재발방지, 최우선 0단계]**: 직전 보고서의 서사('주말'·'다음 세션=…')보다 **먼저 실제 오늘을 확정**한다. 보고서 내부 표기에서 오늘을 추론하면 하루씩 밀린다(7/6 실제 사고).
   ```bash
   TZ=Asia/Seoul date '+%Y-%m-%d %H:%M %A'                          # 실제 KST 날짜·요일·시각 (시스템 currentDate와 대조)
   python3 .claude/skills/portfolio-desk/scripts/market_data.py     # 지수 실시세 → 코스피가 '장중 등락'이면 평일 개장·'종가 고정(전일과 동일)'이면 휴장
   ```
   - **시스템 currentDate + 실시세 = 날짜의 정본.** 직전 보고서의 '오늘/다음 세션' 문구는 참조용(작성 시점 기준이라 이미 지났을 수 있음).
   - 코스피/미장 지수가 **실시간으로 움직이면 그날은 개장일**(평일) → 프로즌 종가 재사용 금지, 그날 시세로 갱신. **휴장 단정 전에 반드시 실시세로 확인.**
   - **새 거래일이면 새 번호 보고서(v+1)** — 직전 보고서에 부록으로 덧붙이지 말 것(부록은 같은 날 보조 산출에만). 판단 = 이 0단계의 실측 날짜 기준.
0. **⚠️ 버전 충돌 방지 [2026-06-17 추가]**: 다른 세션이 같은 날/번호로 보고서를 만들었을 수 있다 → **먼저 원격 최신을 가져와 확인.**
   ```bash
   git fetch origin main 2>/dev/null; git log origin/main --oneline -3
   git ls-tree origin/main docs/reports/ | grep -oE 'report_v[0-9]+' | sort -u | tail -3
   ```
   로컬보다 origin/main이 앞서면 작업 브랜치에서 `git rebase origin/main`으로 정합 후 시작(로컬 `main` 브랜치는 unrelated 히스토리일 수 있어 체크아웃 금지). **새 보고서 번호 = origin 최신 버전 +1**(같은 날이라도 번호 겹치면 안 됨). 끝의 main 반영은 `git push origin HEAD:main` ref 직접 ff(연속성 규약 — CLAUDE.md 표준 절차).
1. `docs/reports/`에서 **가장 높은 버전 보고서**(`report_v*.md`)를 Read → STATE SNAPSHOT이 직전 상태.
   ```bash
   ls docs/reports/ | grep -E 'report_v[0-9]+' | sort -t v -k2 -n | tail -1
   ```
2. `docs/master.md` Read → 원가 고정·룰·워치리스트·일정의 source of truth.
2b. **결정 메모리 기계검색** — master §9(결정로그)·§10(전략 아젠다)은 사람용 산문 정본, 아래는 그 **기계 인덱스**(검색 가능 = 세션마다 손으로 안 훑어도 됨):
   ```bash
   python3 .claude/skills/portfolio-desk/scripts/decisions.py            # 열린 아젠다·미결 결정 전부 상기
   python3 .claude/skills/portfolio-desk/scripts/decisions.py query 외인  # 지금 작업 관련 결정만 끌어오기
   ```
   새 결정·기각안이 생기면 `decisions.py add ...`로 원장에 + master §9/§10 산문에도 함께 적는다(이중정본).
2c. **🧠 기억 통합 회수 [8/5 신설 — 배선 8/5]** — `decisions.py`는 **결정 원장 하나만** 본다. 우리 기억은
   결정·콜·미스무브·룰 **네 군데**에 흩어져 있고, 그게 8/2에 확인된 구멍(⭐2 트림이 산문 8~9회 vs 오더 0회)의
   **인지적 원인**이었다 — "과거에 같은 말을 몇 번 했는지"가 한 화면에 안 모였다.
   ```bash
   # ⭐2 이하 보유는 필수 (영구교정 8/2 '관망은 결정이 아니다'와 짝) — 반복 미집행을 눈에 보이게
   python3 .claude/skills/portfolio-desk/scripts/memory_recall.py 현대차 --limit 8
   python3 .claude/skills/portfolio-desk/scripts/memory_recall.py 두산로보 --limit 8
   # 그날 액션 임박 종목·쟁점만 추가로 (전 종목 호출 금지 — 컨텍스트만 먹는다)
   python3 .claude/skills/portfolio-desk/scripts/memory_recall.py MU --limit 8
   ```
   - **읽는 법**: 점수 = 관련성 × 최신성(반감기 90일) × 원장가중. **읽을 순서일 뿐 옳았다는 뜻이 아니다.**
   - **🟠 열린 아젠다가 뜨면 이번 보고서에서 상태를 갱신**한다(방치하면 §10 아젠다가 stale해진다).
   - **틀린 콜·기각된 대안도 같이 올라온다** — 그게 확증편향 방지 장치이므로 **불리한 항목을 건너뛰지 말 것**.
   - 전 종목 순회는 금지. **⭐2 이하 + 그날 오더 나가는 종목**으로 한정(보통 3~5회 호출).
3. (CLAUDE.md는 세션 시작 시 자동 로드되므로 따로 읽지 않아도 됨.)
4. 충돌 시 우선순위: **토스 API 실데이터 > 당일 스크린샷 > Yahoo 무키 시세 > 최신 보고서 STATE SNAPSHOT > 마스터문서**.
5. **⚡ 영상 캐시 확인 [2026-07-11]**: `docs/research/hunter_log.md`·`feeds_log.md` 맨 위 블록이 **오늘자**면 R1 프리페치가 이미 3채널 분석을 끝낸 것 → 메인은 그 캐시만 소비하고 자막을 재추출하지 않는다(§2c 신선도 가드). 오늘자 아니면 §2c 폴백.
6. **🚨 급락 TF 가드 [2026-07-13 신설]**: `docs/crash_tf.md`의 STATUS가 **ACTIVE**면 급락 국면 — 보고서에 **"TF 상황판" 섹션 필수**(crash_tf §1 상황판을 그 세션 데이터로 갱신 + §5 해제 3중 게이트 판정, 판정은 기계값 우선 = `market_data --group index/fx/oil`·`flow_trend.py`·`triggers.py`). 래더(§2)·시나리오(§3)에 없는 신규 매수 판단을 만들지 않는다. RELEASED면 이 단계 생략.
7. **📈 기술·변동성 레이어 [2026-07-21 신설 — 측정 전용, 룰 불변]**: 펀더·수급·매크로 옆에 붙는 '타이밍·리스크 보조 렌즈'. 지수 + 보유에 대해 아래를 수집단계에서 돌려 보고서 표·TF 상황판에 반영(별점·매수존 정본은 여전히 펀더).
   ```bash
   python3 .claude/skills/portfolio-desk/scripts/history_backfill.py             # 상장이래 전 일봉 증분 갱신(캐시 data/history/ — 오늘 tail만 append, 가벼움)
   python3 .claude/skills/portfolio-desk/scripts/garch.py                        # GARCH(1,1) '내일' 선행 변동성 예측(연율%·폭풍%ile·국면) — vol_gauge(후행 RV)의 선행 짝
   python3 .claude/skills/portfolio-desk/scripts/chart_read.py --holdings        # 기술 리드 v2(프로 5기둥): 추세·스테이지·일목·ADX / RSI·MACD·스토캐·다이버전스 / BB·ATR·스퀴즈 / OBV·MFI / 지지저항·피보·VCP·미너비니·RS — 13신호 컨플루언스(방법론 = docs/research/ta_methodology.md)
   python3 .claude/skills/portfolio-desk/scripts/vol_gauge.py                    # 후행 실현변동성·EWMA·폭풍 점수(1년 백분위)
   python3 .claude/skills/portfolio-desk/scripts/vol_sizing.py                   # 변동성 타겟 트랜치 사이징 제안(7,500 하드플로어+폭풍%ile 연속감산·제안 전용·자동집행 아님)
   python3 .claude/skills/portfolio-desk/scripts/history_analysis.py --symbol ^KS11  # (TF/주간) 변동성 군집·크래시 카탈로그·수십년 백분위 컨텍스트
   ```
   - **후행 vs 선행 대조**: vol_gauge = "어제까지 얼마나 격렬했나", garch = "내일 얼마나 격렬할까(평균회귀)". 둘 다 보면 폭풍 정점·완화 국면 판독. 팻테일 필요시 `garch.py --student-t`(ν).
   - **사이징 제안**: vol_sizing이 다음 트랜치 배수를 제안. ⚠️ **[8/5 정정]** 舊 서술 *"7,500 안전핀 하드플로어 위 폭풍%ile 연속 감산"*은 **7/30 개정으로 폐기** — 하드플로어는 **S&P500 폭풍 ≥70%ile**로 바뀌었고 **폭풍 금액 감산은 전면 폐지**(폭풍은 분할 횟수만 바꾼다). 상한 정본 = `tranche_rules.py`. **제안 전용 — 코어 청산/손절 신호 아님, 자동집행 아님, 최종 결정 정훈.**
   - **크로스에셋**: `garch.py --tickers ^N225,^HSI,000001.SS,^VIX,GC=F`로 북아시아·매크로 동반 여부 확인(디커플링 판정 — 지금 국장 폭풍이 순수 국지인지 아시아 동반인지).
   - **스냅샷 자동 태깅**: `snapshot.py`가 이제 보유별 GARCH예측·폭풍%ile·차트바이어스·RSI·구조를 스냅샷에 박는다 → 이슈 시점 차트 상태가 시계열로 축적(`--no-state`로 생략). 과거 스냅샷은 `snapshot_state_backfill.py`로 point-in-time 소급(미래참조 없음). 정본 분석 = `docs/research/history_analysis.md`.
   - **국내 정성 크로스체크**: `naver_data.py --news "<종목/이슈>"`·`--trend`(NCP 키 정훈 제공)로 폭풍의 촉매·리테일 심리를 정량 옆에 병기(정량 국면 ↔ 정성 촉매 수렴 확인).
   - **★수급 자동 수집 [7/21 신설 — 수동 WebSearch 탈출]**: `naver_flows.py`(네이버 무키 JSON) — ①시장전체 코스피·코스닥 외인/기관/개인 순매수(억원, flows.json이 손으로 적던 값 자동화) ②종목별 외인/기관/개인 순매수·외인보유율(하닉 매도중단 트리거 감시). KRX 공식 API는 데이터센터 IP서 400/LOGOUT로 막혀 네이버로 우회. `--flows-line`=flows.json series 형식 출력. 국장 데스크가 Task에서 이걸로 수급 확정(WebSearch는 KRX 확정 대사·백업).

## 1. 실제 보유·현금 — 토스증권 (선택)

정훈이 채팅에 `client_id`/`client_secret`을 주면:
```bash
python3 .claude/skills/portfolio-desk/scripts/toss_snapshot.py --id <id> --secret <secret>
```
- 출력: 계좌별 보유(수량·평단·현재가·평가손익) + 매수가능금액(현금) + 환율.
- **주문 API 절대 호출 금지. 조회 GET 전용.** 키는 저장하지 않는다.
- 키 미제공 시 폴백: `docs/screenshots/` 계좌 스크린샷 + Yahoo 무키 시세 + 직전 스냅샷 기준선.

## 2. 데스크 병렬 실행 (핵심)

구조는 업계 표준 **TradingAgents**(애널리스트 → 강세/신중 디베이트 → 리스크 매니저 → 펀드매니저=PM) 패턴을
정훈 포트폴리오에 맞춘 것이다. 서브에이전트를 **한 메시지에서 동시 호출**(Agent 툴 병렬)해 데이터를 모은다.

**지역축 데스크 (지수·수급·시세)**
- **kr-market-desk** (국장): 코스피·코스닥·외국인/기관/연기금 수급·국내 특징주 + 국내 보유 5 + 국내 워치 시세
- **us-market-desk** (미장): S&P·나스닥·다우·필반·위험선호·미 특징주 + 미국 보유 11 + 미 워치 시세

**섹터축 데스크 (테마·펀더멘털·컨센서스, 지역 교차)**
- **semi-ai-desk** (반도체·AI인프라): 삼성전자·NVDA·MU·AVGO·ANET / 원익IPS·테스·삼성전기·SK하이닉스·STM
- **power-physical-desk** (전력·인프라·피지컬AI): LG전자·두산로보·현대차·TSLA / 두산E·GEV·SK이노·방산조선
- **bigtech-platform-desk** (빅테크·플랫폼): META·MSFT·AAPL·GOOGL·ORCL·NAVER / TMUS·SPCX

**매크로·리서치·리스크 데스크**
- **macro-desk**: 환율·금리·지표·유가·이벤트 캘린더
- **research-feed** ⚡ **[2026-07-11 분리 — 토큰 절감]**: 추적 채널 3개(경제사냥꾼 + 수페TV·지식인사이드) 자막 분석은 **메인 보고서에서 재호출하지 않는다.** 이건 **R1 영상 프리페치 루틴(평일 10:00, 별도 리셋 창)**이 미리 돌려 캐시에 저장한다(routines.md R1). **메인 보고서(R2)는 오늘자 캐시만 소비** = §2c 신선도 가드 참조. 프리페치가 하는 일(정본): 신규 영상 탐색·자막 + [검증/정정/미확인] 분류 → **경제사냥꾼은 `docs/research/hunter_log.md` / 외부 2채널은 `docs/research/feeds_log.md` 맨 위에 누적 기록**(서로 안 섞음). **⚠️[6/28] 미확인 최소화**: [미확인] 태깅 전 추가 WebSearch 2~3회 교차검증, 승격·범위추정·"N개 출처 시도" 명시. **채널 추천 종목+발동조건은 `setups`(경제사냥꾼=`hunter.json`/외부=`feeds.json`)로 누적** → 조건 충족 시 매수/매도 발동(§7c).
- **risk-desk** (리스크 매니저): 안전핀·트랜치·트리거(`triggers.py`)·집중도·신중(bear) 관점 — PM의 브레이크
- **guru-flow-desk** (대가 흐름) **[7/23 신설·6인]**: 주식 대가 6인(버핏·버리·드러켄밀러·애크먼·테퍼·로엡) 13F 보유변동을 SEC EDGAR 무키(`guru_flows.py`)로 수집 + 그 결정의 '**이유**'를 외신·주주서한·sell-side로 캐 **우리 참고점**(종목별 consensus)으로 번역 → `data/app/guru_flows.json` 캐시. **트리거-게이트**(분기 cadence, 아래 §트리거). **메인 보고서는 캐시만 소비**(research-feed 패턴), 데스크 스폰은 13F 공시창·stale·정훈 요청 시만. ⚠️지연(45일) 확증 렌즈, 매수 트리거 아님.

각 데스크가 섹션을 반환하면 PM이 종합한다. (데스크는 파일을 쓰지 않음 — PM이 모아서 작성.)
**📖 [7/4] 공용 플레이북**: 전 데스크(현재 9개) agent 파일 전원 Tasks 0 = `docs/desk_playbook.md` Read(공통 소스지침·검증 규율 + 캘리브레이션 교훈 + 자기 데스크 누적 교훈). 소스 우선순위(6/16) 정본도 이 파일 §1(舊 agent 파일 중복 제거됨). PM도 종합 전 §2·§3 확인.
**[7/4 정훈 지시] 데스크별 모델 배분** — 지역(kr·us)+매크로+리스크+리서치 = **sonnet**(스크립트 정리·룰체크·태깅,
opus 불필요·토큰 절감) / 섹터 3개(semi-ai·power-physical·bigtech) = **opus**(테마 종합·컨센서스 판단, 별점·스코어에 직결).
**메인 보고서(R2)가 인라인 스폰하는 데스크 = 지역(kr·us)+매크로+리스크 4개(항상)**. **research-feed는 인라인 스폰 안 함 — R1 프리페치 캐시 소비**(§2c). 섹터 3종은 아래 트리거일 때만.
**섹터 데스크 3종(semi-ai·power-physical·bigtech)은 아래 트리거 중 하나라도 충족 시 호출** [2026-06-17 명시]:
- 담당 섹터 보유/워치 종목 중 **당일 ±5% 이상** 움직인 종목 있음
- 해당 섹터에 **실적·이벤트 임박**(D-7 이내, 예: MU 6/24 → semi-ai 호출)
- **테마 뉴스/촉매**(가이던스·정책·M&A 등) 발생
- 정훈이 그 섹터 종목을 **이슈 선택지로 지목**
→ 위 트리거 없는 섹터는 지역 데스크 시세로 갈음(별도 호출 생략). 전체 호출은 큰 장세 변화·주간 첫 보고서에만.
**대가 흐름 데스크(guru-flow-desk)도 트리거-게이트** [2026-07-23, `sonnet`]: ①분기 13F 공시창(Feb/May/Aug/Nov 중순, 다음 = 2026Q2 마감 ~8/14) ②`guru_flows.json` 120일+ stale ③정훈이 대가 흐름 지목 — 셋 중 하나면 스폰(`guru_flows.py --emit`으로 팩트 갱신 후 데스크가 외신·주주서한으로 '왜'를 채움). 그 외 매 보고서는 캐시된 `guru_flows.json`만 소비(앱 #gurus + 보고서 '대가 흐름' 섹션).

### 2a. 데스크 반환값 교차검증 (PM 필수 — §4 종합 전) [2026-06-22 신설]
데스크가 늘수록 같은 사실을 서로 다르게 보고하는 충돌이 생긴다(실제 사례: 미장 데스크 "MU 실적 6/24" vs 반도체AI 데스크 "KST 6/25 새벽" — 동일 사건의 표기 차이). PM은 종합 직전 **충돌 점검 1단계**를 반드시 거친다:
1. **날짜·시각**: 실적일·이벤트일이 데스크 간 일치하나? **미국 발표는 "美 현지일 + KST 환산"을 함께 표기**해 혼동 차단(예: MU = 美 6/24 마감 후 = KST 6/25 새벽).
2. **수치**: 같은 종목 시세·목표가·수급 숫자가 데스크 간 ±오차 범위인가? 어긋나면 **마감 확정값(국장/미장 지역 데스크) 우선**, 섹터 데스크 시세는 갈음.
3. **충돌 발견 시**: 둘 중 교차검증된 출처를 채택하고, **STATE SNAPSHOT 영구교정에 1줄 기록**(재발 방지). 미해소 충돌은 본문에 "[데스크 간 불일치]"로 명시하고 추측하지 않는다.

### 2b. 강세 vs 신중 디베이트 (PM 직접, TradingAgents 차용)
데스크 입력을 모은 뒤, PM은 §4 종합 전에 **강세(bull) 논지 vs 신중(bear) 논지**를 각 1단락으로 맞세운다.
신중 논지는 risk-desk 반환을 베이스로. 최종 액션은 두 논지를 저울질한 PM 판단(무게는 PM 종합에).

**🔁 reflection 주입 [7/4 채택 — TradingAgents 패턴, study_log]**: §7 종합 전 오늘 액션·이슈가 걸린 종목에 대해
`decisions.py query {종목}`으로 **과거 결정·기각 대안을 상기**하고, `desk_playbook.md` §2(캘리브레이션)·§3(데스크 교훈)을 확인한다.
주간 self-review(배치 후행채점)와 상보인 **매 보고서 상기 단계** — 같은 실수를 세션이 바뀌어도 반복하지 않기 위함.

PM은 추가로 **무키 분석 스크립트**를 직접 돌려 정량 데이터를 채운다 (프로젝트 루트에서):
```bash
python3 .claude/skills/portfolio-desk/scripts/pnl.py          # 평가손익 + 합계 (원가 대비 수익률)
python3 .claude/skills/portfolio-desk/scripts/consensus.py     # 애널리스트 목표주가 + ±30% 괴리 플래그
python3 .claude/skills/portfolio-desk/scripts/triggers.py      # 매수존·안전핀·이벤트 트리거 점검
python3 .claude/skills/portfolio-desk/scripts/event_calendar.py --within 45   # [7/19] 실적(earnings)+매크로(FOMC·CPI·금통위) 통합 D-day 캘린더 → §4 '지켜볼 것'. 폰창 밖 이벤트 자동 플래그
python3 .claude/skills/portfolio-desk/scripts/snapshot.py     # 일별 손익 스냅샷 저장(시계열) + 전일대비 → '변경점' 정량
python3 .claude/skills/portfolio-desk/scripts/market_log.py   # [7/19] 오늘 시세(지수·환율·보유·워치) 시계열 append(하루 1회). 추세조회: --query 코스피 --days 30
# (선택) charts.py — 비중/수익률 PNG(dataviz 검증팔레트·한글). matplotlib 있으면 생성·없으면 자동 스킵(웹). 로컬 이전 후 활성.
python3 .claude/skills/portfolio-desk/scripts/build_dashboard.py   # [7/20] data.js+폭풍점수 → 자체완결 HTML 대시보드(output/dashboard.html) → Artifact 툴로 발행하면 사이드패널 열람·공유. matplotlib PNG 대체(웹서도 뜸·다크대응). 템플릿=assets/dashboard_template.html
```
- **📋 국내 수시공시 (보유 KR 5종목 · [7/30 신설])** — 리스크룰 2 '펀더 훼손' 판정의 유일한 장치:
  ```bash
  python3 .claude/skills/portfolio-desk/scripts/dart_disclosure.py --days 7 --save
  python3 .claude/skills/portfolio-desk/scripts/dart_disclosure.py --insider   # 임원 보유증감 합산
  python3 .claude/skills/portfolio-desk/scripts/dart_disclosure.py --major     # 5% 대량보유(국민연금)
  ```
  🚨critical(훼손·희석·지배구조)은 **보고서 본문에 반드시 노출**. ⚠️ 자금용도가 '기타'처럼 모호하면
  **뉴스 교차검증까지 한 번 더** — DART는 사실의 1차 출처지만 **맥락의 1차 출처가 아니다**(7/30 실사고).
- **👤 미국 내부자 (Form 4 · 무키 · [7/30 신설])**:
  ```bash
  python3 .claude/skills/portfolio-desk/scripts/insider_us.py --days 90 --save
  ```
  **재량적 매수(P)만 신호**로 읽는다 — 매도(S)는 대부분 10b5-1 사전약정이라 비관 신호가 아니다.
- **📋 미국 수시공시 8-K (보유 US 9종목 · [8/5 신설·배선]) — `dart_disclosure`의 미국 짝**:
  ```bash
  python3 .claude/skills/portfolio-desk/scripts/edgar_search.py --events --days 30
  ```
  8-K는 **item 코드가 사건 종류를 말한다** → 제목 안 읽고도 분류된다(KR과 같은 중대성 3단 문법).
  🚨critical(**2.02 실적 · 1.01 중대계약 · 2.01 인수 · 3.02 희석 · 4.02 재무제표 신뢰불가**)은
  **보고서 본문에 반드시 노출**. ⚠️notable(5.02 임원·8.01 기타중요)은 맥락 있을 때만.
  ⚠️ item 코드는 **사건이 있었다는 사실**이지 내용이 아니다 — 논지를 바꿀 건이면 URL로 원문까지 내려갈 것.
- **🔎 공시 본문 검색 (트리거 게이트 · 매 보고서 아님) [8/5 신설·배선]**:
  ```bash
  python3 .claude/skills/portfolio-desk/scripts/edgar_search.py --q "HBM4" --forms 10-Q,10-K,8-K
  ```
  **언제 쓰나 = 논지를 1차 문서로 확정해야 할 때**(이게 이 도구의 존재 이유다):
  ① 매체·채널이 말한 표현이 **회사 공시에 실제로 있는지** 확인할 때 (7/29 CXMT형 받아쓰기 방지)
  ② 신기술·신제품 용어가 **어느 회사 공시에 언제부터** 등장했는지 (예: `HBM4` = MU 5건 / NVDA·AVGO 0건)
  ③ 계약·관세·리스크팩터 문구 변화 추적
  ⚠️ **히트는 "그 문구가 있다"는 사실일 뿐 맥락이 아니다** — 인용하려면 원문 URL을 열어 문장을 직접 읽고,
  7/26·7/28 정정룰(주체·범위·형식·단위 병기)을 적용한다. **매 보고서 습관적 호출 금지**(탐색 전용).
- **📐 낙폭·기저율 ([7/30 신설] · 주간 R3 또는 국면 전환 시)**:
  ```bash
  python3 .claude/skills/portfolio-desk/scripts/history_backfill.py          # 일봉 캐시 증분
  python3 .claude/skills/portfolio-desk/scripts/drawdown_history.py --indexes --save
  ```
  ⚠️ **기저율 규율**: ①표본 수 병기 ②깊이 단독 매수논거 금지 ③"승률 97%"≠"97% 확률".
  정본 = `docs/research/drawdown_study_2026-07-30.md`
- **🔄 stale 레이어 자동 갱신 (매 보고서 · 수집 단계 맨 앞) [8/10 신설·배선]**:
  ```bash
  python3 .claude/skills/portfolio-desk/scripts/refresh_stale.py   # 상한 레이어만 --save 재실행
  ```
  **왜 필요한가 — 8/10 배선 감사에서 드러난 구멍**: `eps_revisions.py`·`naver_sentiment.py`·`guidance.py`·
  `transcripts.py` 네 개가 **SKILL.md·routines.md 어디에도 없었다**(grep 0건). 8/1에 만들어 CLAUDE.md
  데이터 소스 절에 등재까지 해놓고 **아무 루틴도 호출하지 않았다** → `eps_revisions.json`이 9일 방치돼
  `--coverage` FAIL. 게이트는 **감시자**였을 뿐 **집행자**가 없었다.
  8/2 원칙의 데이터판이다: *"오더북에 들어간 것만 집행된다"* ⇒ **루틴에 배선된 것만 갱신된다.**
  · 신선한 날은 **네트워크 호출 0회**(R2 예산 무해) · stale한 것만 골라 돌린다.
  · 임계 = `허용 - 2일` → **게이트가 FAIL을 내기 전에** 손댄다(하루 걸러도 안 터짐).
  · 신선도 표는 `validate_report.COVERAGE_LAYERS`를 **import**해서 쓴다(두 벌로 두면 갈라진다).
  ⚠️ 루틴 프롬프트는 에이전트가 못 고친다(8/6 — `http_api` 트리거는 `update_trigger` 거부)
  ⇒ **이런 배선은 반드시 코드/스킬 쪽에 심는다.** 프롬프트 문구에 의존하는 방어는 무효.
- **📑 재무제표 3표 (보유 전종목 · 필수 · 무키) [7/29~30 신설]**:
  ```bash
  python3 .claude/skills/portfolio-desk/scripts/financials.py --all --save   # data/app/financials.json 갱신
  python3 .claude/skills/portfolio-desk/scripts/financials.py --flags        # 재무 경보만
  python3 .claude/skills/portfolio-desk/scripts/financials.py --score        # 펀더 서브스코어(0~100)
  ```
  **미국·국내 전부 하드넘버가 있다** — US=SEC EDGAR(1차·상장 이래) / KR=Yahoo+DART(1차). 舊 "국내는 FMP 미지원이라
  WebSearch" 서술은 **폐기(7/30)**. 0~100 스코어를 쓸 때 **펀더 서브스코어와 25점 이상 벌어지면 `validate_report.py`가
  WARN** — 그 이격을 N·L·M(촉매·주도주·시장방향) 가감분으로 반드시 설명할 것.
  ⚠️ 티커 접미사는 시장을 바꾼다(`454910.KS`=두산로보틱스 / `.KQ`=남의 종목). `market_data.py` 기준과 일치 필수.
- **📊 횡단면 상대비교 [8/5 신설·배선] — ⚠️ 반드시 위 `financials.py --all --save` 다음에 실행**
  (이 스크립트는 `financials.json`을 읽기만 한다. 먼저 돌리면 **어제 숫자로 순위를 매긴다**):
  ```bash
  python3 .claude/skills/portfolio-desk/scripts/peer_compare.py          # 3개 피어그룹 전부
  python3 .claude/skills/portfolio-desk/scripts/peer_compare.py --tickers 005380.KS   # 한 종목 상세
  ```
  `financials.py`가 종목을 **세로로**(자기 시계열) 본다면 이건 **가로로**(동종 대비) 본다.
  그동안 "이 종목 스코어가 낮은 게 **업종 특성인가 회사 문제인가**"를 우리 숫자로 못 갈라
  sell-side의 '업종 대비' 서술을 받아썼다 — 그 구멍을 메우는 축이다.
  - **두 렌즈가 갈리는 지점이 산출물이다**: 피어 백분위 ↔ 자기이력 백분위.
    · 피어 상위 ↔ 자기이력 하위 = **좋은 회사의 둔화 초입** → §5 리스크·트림 검토 입력
    · 피어 하위 ↔ 자기이력 상위 = **낮은 업종의 회복 국면** → 매수 논거의 보조(단독 근거 아님)
  - **섹터 데스크에 전달**: 해당 그룹 결과를 그 데스크 프롬프트에 넣어 '동종 대비' 서술의 근거로 쓴다.
  - ⚠️ **[8/6] 워치 종목을 편입해 n을 키웠다**(전력 3→10 · 반도체 5→10 · 빅테크 6→7).
    단 **n이 늘어도 비교가능성이 같이 늘지는 않는다** — 이 그룹은 *경제적 동질 피어*가 아니라
    **데스크 담당 범위**다(전력 = 전력기기+로봇+완성차+방산·조선 혼재).
    백분위를 "업종 내 위치"로 쓰지 말고 **"우리 커버리지 안에서의 순위"**로 서술한다.
    **비율만 비교**한다 — 통화가 섞여 절대금액 비교는 무의미.
  - 피어 재무는 **주간 R3에서 `financials.py --with-peers --save`**로 갱신(매일 R2엔 안 붙인다 —
    국내 1종목 1~2분이라 완주 예산을 갉아먹는다). 미수집 종목은 자동 제외되고 출력에 표기된다.
  - ⚠️ **측정 전용 — 별점·스코어·트랜치 어떤 룰도 바꾸지 않는다.**
- **미국주 TTM 파생(보조)**: 키가 있으면 `FMP_API_KEY=키 python3 .claude/skills/portfolio-desk/scripts/fundamentals.py`
  → 매출·EPS YoY·최근분기 EPS YoY·마진·FCF·PE. **무료플랜 402 종목(MU·VOO·ANET·AVGO·ORCL)은 EDGAR가 대체**하므로
  더 이상 WebSearch 폴백 대상이 아니다.
- **자체 밸류에이션(컨센서스 견제) [7/20]**: `FMP_API_KEY=키 python3 .claude/skills/portfolio-desk/scripts/valuation.py --tickers NVDA,MSFT [--comps]`
  → DCF 3시나리오(보수/기준/낙관) 내재가치 + 피어 P/E comps. **증권사 목표가(consensus.py)와 나란히 교차검증**("증권사 우선하되 과신 견제"의 정량 근거). ⚠️DCF는 가정 민감(가정 전부 출력·CLI 조정)·FCF 음수는 부적합 플래그. comps는 무료플랜 402 피어 많아 유효 피어<2면 신뢰불가 플래그. 키 없으면 `--demo`로 수학만.
- `pnl.py`/`consensus.py`/`triggers.py`는 모두 `portfolio.json`(원가·보유·alerts 정본)을 읽는다.
- **기관 컨센서스**: consensus.py가 美 종목 목표주가/의견을 무키로 채움(±30% 괴리 자동 플래그).
  국내 종목·미커버리지(ETF 등)는 WebSearch로 보강 — "[종목명] 목표주가 증권사".

### 2c. 영상 캐시 소비 + R1 이후 신규 델타 (신선도 가드) [2026-07-11 토큰 절감]
메인 보고서(R2)는 **유튜브 3채널을 통째로 재추출하지 않는다.** 무거운 3채널 풀 자막 분석은 **R1 영상 프리페치 루틴(평일 10:00, 별도 5시간 리셋 창)**이 이미 했다(routines.md). 단, R1(10:00) 이후 오후에 **추가 업로드된 영상은 놓치지 않게 싸게 델타로 잡는다.** 종합 순서:
1. **오늘자 캐시 확인**: `docs/research/hunter_log.md`·`docs/research/feeds_log.md` **맨 위 블록 날짜스탬프가 오늘**인지 + `data/app/hunter.json`·`feeds.json` `latest_videos`.
2. **신선하면(오늘자 있음) → 캐시 소비 + 델타 체크**:
   - 캐시를 읽어 §4 리서치 피드·§7c 조건 트래커를 채운다(setups met는 `flow_trend.py`·`triggers.py` 기계값과 대조).
   - **⚡ R1 이후 신규 영상 델타 (싸게)**: `hunter_latest.py`(**`--fetch` 없이** RSS 목록만 — 거의 무료) 3채널 실행 → 캐시 `latest_videos`에 **없는 ID(=R1 뒤 새로 올라온 것)**만 골라 **그것만** `hunter_latest.py --ids <신규ID> --fetch`(--channel 병기)로 자막 추출·태깅해 캐시/로그에 append. **보통 2~4편**(경제사냥꾼 오후 업로드; 저녁 배치는 R2 대상 아님 = 다음날 R1) → 인라인 부담 작음. **신규 없으면 그대로 진행.** 3채널 풀 재추출(--fetch --max 10…)은 금지.
   - 저녁(16:00 이후) 업로드분은 다음날 R1(오늘/어제 필터가 커버) 또는 밤 대화에서 on-demand(youtube-watch·`--ids`)로 잡는다.
★ **[8/12 정정] 위 '저녁 배치는 다음날 R1이 커버' 전제는 실제로 성립하지 않았다.** 다음날 R1도 `--max 10` 상한이라, 전날 저녁분 + 당일 아침분이 10편을 넘으면 넘친 만큼 영구 누락된다. API 감사 실측 = **커버리지 73%·구조적 누락 86건**(주말 28%·17시 이후 39%). ⇒ **`YOUTUBE_API_KEY`가 있으면 `hunter_latest.py --catchup`**(아카이브 최신 이후 전량)을 쓴다. 주간 누락 점검은 `hunter_audit.py --days 14`.
3. **폴백(오늘자 캐시 없음 = R1 실패·수동 세션)**: 경제사냥꾼 **1채널만** 경량 인라인(`hunter_latest.py --fetch --max 3`), 외부 2채널은 직전 캐시로 갈음하고 "R1 프리페치 미스 — 경량 폴백" 명시. 3채널 풀 인라인은 하지 않는다(토큰 폭증 원인).

## 3. 보고서 작성 — 형식 (순서 고정)

데스크별 3~5줄, 과압축 금지(근거 수치 유지), 마크다운 표 적극 활용.

```
# 정훈 PORTFOLIO DESK · v{N} · {YYYY-MM-DD}
## 변경점 (직전 대비)        ← 맨 위. 없으면 생략
## 1. 시장 — 국장 / 미장      ← kr-market-desk + us-market-desk
## 2. 섹터 — 반도체AI / 전력·피지컬 / 빅테크   ← 호출한 섹터 데스크만
## 3. 매크로 데스크
## 4. 리서치 피드             ← 영상별 핵심주장 → [검증/정정/미확인]. 없으면 "신규 입력 없음"
## 5. 리스크 데스크           ← 트리거·위반경보·집중도·신중(bear) 관점
## 6. 강세 vs 신중 디베이트   ← 각 1단락 맞세움 (TradingAgents 차용)
## 7. PM 종합 (최종)
   - 오늘의 한 줄 결론
   - 보유 전종목 표(현재 14 — 정본 = validate_report.py HOLDINGS·portfolio.json): 현재가 | 수익률(원가 대비, master.md 원가로 계산) | 목표가 | 매수존 | ⭐(1~5) | **스코어(0~100)** | 한줄코멘트
     - **스코어 = 정량 채점**(별점의 근거 숫자). 검증된 방법론 렌즈(오닐 CANSLIM·미너비니 추세템플릿·드러켄밀러 매크로)로 채점.
       환산 고정: **85~100=⭐5 / 70~84=⭐4 / 55~69=⭐3 / 40~54=⭐2 / <40=⭐1.** 별점↔스코어 어긋나면 근거 재점검.
       상세 채점 기준은 `stock-deepdive` 스킬의 "검증된 방법론 체크리스트" 참조(두 스킬 동일 기준 사용).
   - 워치리스트 표 (활성 종목만)
   - **🎯 지정가 오더북 (핵심·액션 임박만) [2026-06-28 정훈 지시]**: 서술형("눌림·관망") 말고 **실제 가격 지정가**로. 미니표 = 종목 | 액션(매수/트림) | **지정가(실제 원화·달러)** | 수량(정수/소수점) | 폰창 예약방식 | 발동조건 | **기대수익률(익절 후보가) [7/2 룰2 보강 — 매수 오더 필수 병기, 도달 시 일부 익절 디폴트 검토]**. 대상 = 그날 액션 임박 핵심 5~8종(예 AAPL 트림·NAVER/삼성 매수·GOOGL 재배치·META/AVGO 3차·두산E 돌파·SK ADR). 가격조건은 `portfolio.json` `alerts`에 미러(triggers.py 자동발동)·`tasks.json` `orders`에 `status:계획`으로 등록. 나머지 종목은 풀표 매수존/트림 컬럼으로 갈음.
   - 제안 액션 (매수/매도/홀딩/관망 + 근거, 강세·신중 양쪽 시각)
   - 현금 배분 플랜 (잔액 기준, 이벤트 연동, 3분할 원칙)
   - 지켜볼 것 (트리거·일정 캘린더 2주)
   - **🗣️ PM 사견 (매 보고서 필수) [2026-06-28 정훈 지시]**: 데이터·컨센 종합 **위에** PM 개인의 솔직한 한 표. ①**종합 1블록** = 시장 방향·전략·리스크에 대한 PM의 베팅 의견(애매한 양비론 금지, 결론 분명히) + ②**핵심종목 3~4개 PM 한줄**(이건 내가 어떻게 보나). "분석 참고·결정은 정훈"이되 PM은 견해를 숨기지 않는다.
## 7c. 채널 조건 트래커 (매 보고서 점검) [2026-06-28 신설 — 정훈: "정리만 말고 때 되면 매수/매도" · 7/7 채널 공통화]
   `hunter.json`의 `setups`(경제사냥꾼) **+ `feeds.json` 각 채널 `setups`(수페TV·지식인사이드)**를 매 보고서 점검: 셋업별 **조건 충족도**(예 3개 중 2개 met) + 가격존 도달 여부. **조건 ~75%+ 충족 & 가격존 진입 → 지정가 매수/매도 발동**(지정가 오더북·alerts에 등록). 비가격 조건(외인 매도중단·환율 꺾임 등)은 PM이 met를 갱신. 미충족이면 "추적중"으로 누적(영상 논지는 계속 기억).
   - **🤖 기계 판정 대조 의무 [2026-07-02 신설]**: met를 수기로만 찍지 말고 기계 평가와 대조 —
     ①**외인 수급 조건** = `python3 .claude/skills/portfolio-desk/scripts/flow_trend.py`(streak·5일 강도·전환단계) ②**환율 1,500·가격존·지수 지지** = `triggers.py`(KRW=X below 1500·between/below alerts·cond=flow 자동평가). 기계값과 수기 met가 어긋나면 기계값 우선으로 교정하고 note에 사유. 셋업 conditions 텍스트에 현재 기계값(예 "현 1,548")을 매 보고서 갱신.
   - **🔁 살아있는 추적 [정훈 강조]**: 매 보고서 **모든 신규 영상 빠짐없이** 반영 — 조건/논지 변경 시 갱신, 새 종목·이슈 전환 시 새 setup 추가·옛것 완료/폐기, status 전이. stale 방치 금지.
   - **⚖️ 교차검증 필수 [정훈 강조]**: 경제사냥꾼을 무조건 믿지 않는다 — 셋업 등록·발동 전 **기관 sell-side·외신으로 교차검증**한 펀더·가격으로 조건 재구성. 채널 vs 기관 갈리면 양쪽 병기·교차검증 우선, note에 출처차 명시.
   - **🧭 신뢰-견제 균형 [2026-06-28 정훈 지시]**: 정훈은 경제사냥꾼을 **꽤 신뢰하고 싶어함** → 채널 아이디어를 가볍게 무시하지 말고 **진지하게 비중 있게 채택·추적**(셋업 적극 등록). **단 PM은 그 신뢰의 과신 편향을 객관적으로 견제하는 브레이크**다: 틀린 콜·과장은 분명히 짚고(트랙레코드 정직히 — self-review와 연결), 채널 단독 근거 매수는 막고, 검증된 펀더가 어긋나면 "정훈이 신뢰해도 이건 신중" 의견을 낸다. 맹신도 무시도 아닌 **중간을 PM이 잡는다.**
## 8. 오늘의 이슈 선택지      ← §6
## 9. 계획·할일·매수추적       ← tasks.json 동기화 (아래 §3b)
## STATE SNAPSHOT             ← §5.4
```

### 3b. 계획·할일·매수추적 (`data/app/tasks.json` — 앱 #plan 화면 정본) [2026-06-21 신설]
정훈이 폰에서 **장 전망(시간축)·할일 체크·매수추적**을 보는 화면. 매 보고서에 동기화한다.
- **outlook**: 오늘/내일(월요일)/이번주/이번달 장 전망 한 줄씩(`tag`·`dir`(↑→↓)·`text`). 시세는 휴장이면 프로즌 명시.
- **index_forecast**: 코스피·나스닥·S&P·필반 예상 레인지(`ref`현재·`low`·`base`·`high`·`dir`·`note`·**`confidence`**). **`confidence` = `확정`(마감 종가·발표된 수치) / `추정`(선물·전망·미발표) [2026-06-22 신설]**: 추정값을 단정적으로 박지 말 것(실제 사례: 아침 미국 선물 "−1.2%" 추정을 단정 → 저녁 약보합으로 정정). 추정은 `note`에 "(추정)"·근거를 남기고, 정정되면 STATE SNAPSHOT 영구교정에 1줄.
- **종목 가격 예상**: `stocks.json` 각 종목 `forecast.week`/`forecast.month`(`low`·`high`·`dir`·`note`) — 목표가/매수존과 **별개의 단기 예측**.
- **tasks**: `today`/`week`/`month` 각 `{id, text, done}`. **체크 = 채팅 기반 정본**: 정훈이 "오늘 1번 했어" 하면 해당 `done=true`로 바꾸고 커밋. 앱에서도 할일을 탭으로 직접 체크 가능하나 이건 그 폰 localStorage 임시(다른 기기·다음 빌드엔 안 남음) — 영구·전기기 반영은 반드시 채팅→tasks.json `done=true`. 정본 `done=true`는 앱에서 잠금(✅고정).
- **orders(매수추적)**: `{id,label,ticker,action,status,price,shares,amount_krw,date,note}`. status = `계획`→`예약`→`체결`(또는 `취소`). 정훈이 "NAVER 1주 샀어"/"META 예약 걸었어" 하면 추가·상태변경하고, 체결이면 `portfolio.json` 보유수량·`master.md`도 함께 갱신.
- **루틴(무인) 시**: outlook/index_forecast/forecast/할일을 당일 상태로 새로 채워 넣는다(전망은 매일 바뀜). 완료된 할일은 다음날 자동 정리(done 지나간 today는 비우거나 week→완료처리).

고정 제약(항상 반영 — 상세는 CLAUDE.md / master.md):
- 정훈 폰 가용 **17:30~20:50 KST**. 야간 지표는 사전 조건부 룰로 베이킹, 당일 밤 트리거 금지.
- 토스 시간외단일가 16:00~18:00 → 정훈 겹침 17:30~18:00. 美 분수주=시장가/정수주=지정가.
- 한은 점도표 = **2026.2월부터 발표**(2·5·8·11월 공개, 연준과 별개 제도 — 7/7 정정, 비발표월 금통위엔 없음). LG전자 손절선 없음. 매수 안전핀 코스피 7,500 하회 시 트랜치 동결.

### ⭐ 정훈 선호 "최종보고" 형식 [2026-06-17 확정 — 매 보고서 이 느낌으로]
정훈은 위 데스크 분석을 다 돌린 뒤, **마지막에 아래 한 장짜리 "최종보고"를 항상 첨부**하길 원한다.
표본 = `docs/reports/holdings_final_2026-06-17.md`. 핵심 원칙:
1. **표 중심 + 핵심만 박스**: 보유 전종목·워치 전부 깔끔한 비교표 → 그 아래 액션 있는 핵심 3~4개만 ``` 박스 ```로 콕. (전 종목 풀박스 ❌ 너무 지저분, 표만 ❌ 너무 밋밋 → **표+선택 박스 하이브리드**가 정답.)
2. **단위는 실제 원화 전액**: "305k"·"48~53만" 금지 → **305,000원 / 480,000~530,000원** 식으로 전부 풀어쓴다.
3. **섹션 = ①보유16 표+핵심박스 ②워치 표+콕 ③현금 배분 2안(관망🅰️/공격🅱️) ④2주 일정 ⑤월말 목표+전략3+오늘할것 → 🎯결론**. ①~⑤를 **하나로 합친 한 흐름**(쪼개거나 축소 ❌).
4. **톤**: 이모지·강조·동기부여(💪) 살리되 수치는 검증. 결론은 "산 이유가 살아있나" 매도 디시플린 + FAB10 렌즈.
5. 현금 배분은 항상 **🅰️관망(룰 정합·추천) vs 🅱️공격** 2안 병기, 추격금지·FOMC 베이킹 반영.
→ 이 최종보고를 `docs/reports/holdings_final_{날짜}.md`로 저장하고 채팅에도 전문 출력.

## 4. 수익률 계산 (PM 직접)

`market_data.py` 현재가 × master.md 원가/수량으로 평가손익 계산. 환율은 fx 그룹값 사용.
토스 실데이터가 있으면 그게 우선(수량·평단·현금 정본).

## 5. 산출물 — 파일 저장 + git 커밋 (연속성)

1. 보고서를 **`docs/reports/report_v{N}_{날짜}.md`**로 Write. **버전 규칙 [2026-06-22 명확화 — v25→v25b→v26 인플레이션 방지]**:
   - **새 번호(v{N+1})** = 새 정보가 들어온 **독립 보고서**(종가 확정 후 재분석, 다음날 아침 브리핑 등). origin 최신 +1.
   - **`-r2`/`-r3` 덮기** = 같은 시점·같은 성격을 **수정/보강**(오타·수치 정정, 동일 장세 재작성). 새 번호 쓰지 말 것.
   - **`_addendum`/`_exec`/`_night` 등 접미사** = 본 보고서의 **부록**(집행 지시서·밤 대화 정리 등 보조 산출). 번호는 모(母)보고서와 동일. (`_nightcheck`는 R3 루틴 폐지[7/2 정훈 확정, routines.md]로 신규 생성 없음 — 과거 파일명으로만 존재.)
   - 하루에 풀 보고서 2회 이상이면 **장중=`-r2` 덮기 / 종가 확정 후만 새 번호** 원칙. 무인 루틴도 동일.
2. **영구 변경**(보유·원가·룰·워치리스트·정정)이 생기면 `docs/master.md` **및 `portfolio.json`**(기계 정본)을 둘 다 갱신.
2b. **📱 앱 데이터 갱신 (매 보고서 필수 — ⚠️[2026-07-02] EXEC·밤 대화·부록 세션도 예외 없음)** — 아래 정본들을 이번 보고서값으로 갱신. **[7/2 사고 재발 방지]**: v37 아침 서사(코스피 8,303 "존 근접")가 EXEC 폭락(7,648) 뒤에도 stocks.json에 남아 앱이 시세=폭락/서사=아침 분열 상태로 노출됐음 → `_exec`/`_night` 부록 세션도 **stocks(as_of·source_report·forecast·buy_zone·comment)·hunter·tasks·flows 4파일을 반드시 그 세션 상태로 동기화**하고 build 재실행. validate_report.py가 source_report **파일명 전체**를 최신 보고서 파일과 대조해 intra-version stale을 FAIL로 적발한다:
   - `data/app/stocks.json`: 종목별 `stars`·**`score`(0~100 정량점수, self-review가 후행검증)**·`target`·`buy_zone`·`trim`·`comment`·`issues`(최신 [검증/정정/미확인] 이슈 날짜와 함께 prepend)·`as_of`·`source_report`.
     - ⚠️ **`as_of` 실시각 필수 [2026-07-23 신설]**: `16:xx` 같은 **플레이스홀더 금지** — Task 0의 `TZ=Asia/Seoul date '+%H:%M'` 실제 분(minute)을 기입한다(stocks·tasks·pm_view·crash_tf §1 상황판 공통). 舊 습관적 `16:xx` 방치가 정본성 흠으로 지적됨(v58 정리 계기). 과거 프리즈된 보고서 .md는 소급 수정 안 함.
   - `data/app/hunter.json`: 경제사냥꾼 신규 영상(latest_videos)·트랙레코드(track_record 최신 prepend)·headline·themes — `docs/research/hunter_log.md`와 동기화.
     - ⚠️ **영상 요약 필드명 = `summary`(필수)**. `note`로 쓰면 앱 상세가 "—" 빈칸 됨(track_record의 `note`와 혼동 금지). build_app_data가 note→summary 폴백을 넣지만 정본은 항상 `summary`로 쓴다.
     - 🔁 **롤오버 [7/4 자동화]**: latest_videos는 최신 ~9편만 유지. 아카이브 이관은 **build_app_data.py가 자동 수행**(latest 중 archive에 없는 영상을 `hunter_archive.json` `videos` 맨 앞에 prepend, summary→takeaway 매핑, 중복 판정 = id·정규화 제목) — 수동 이관 불필요, **빌드만 돌리면 정체 없음**. validate_report.py는 로그↔archive 날짜 갭을 **FAIL**로 적발(latest에만 있는 날짜는 커버로 안 침 — 앱 '전체 영상 아카이브' 화면은 archive만 읽으므로. 6/20·7/3 정체 재발 원인 봉합).
   - `data/app/feeds.json` **[7/7 신설]**: 외부 채널(수페TV·지식인사이드) 신규 영상·트랙레코드·headline·setups — `docs/research/feeds_log.md`와 동기화. 요약 필드명 = `summary`(hunter와 동일). **경제사냥꾼(hunter.*)과 안 섞는다.** 신규 없으면 손 안 대도 됨(validate는 WARN 수준).
   - `data/app/flows.json`: 당일 코스피 외인/기관/개인 순매수(억원)를 series에 추가. **문서화·교차검증된 값만, 미확인은 null**(추측 금지).
   그 뒤 시세·시계열(환율·코스피)을 합쳐 앱 데이터를 빌드한다:
   ```bash
   python3 .claude/skills/portfolio-desk/scripts/build_app_data.py   # → app/data.js 생성
   ```
   이걸로 정훈의 포트폴리오 앱(`app/index.html`)이 최신 시세·손익·목표·이슈·차트·경제사냥꾼으로 갱신된다. (네트워크 차단 시 `--offline`.)
2c. **✅ 완료검증 게이트 (커밋 전 필수 — 하네스 ②: 검증을 명령어로)**:
   ```bash
   python3 .claude/skills/portfolio-desk/scripts/validate_report.py   # FAIL 0 이어야 커밋
   python3 .claude/skills/portfolio-desk/scripts/rule_tracker.py --snapshot  # [8/6] 룰1 사다리 원장 매일 append
   python3 .claude/skills/portfolio-desk/scripts/setup_schema.py --check      # [8/7] 셋업 트래커 감사(발동권·stale·기한경과)
   python3 .claude/skills/portfolio-desk/scripts/score_calls.py --append   # 이번 콜을 캘리브레이션 원장에 누적
   ```
   **[8/7 신설] 셋업 조건 트래커는 이제 기계가 센다.** `validate_report`가 `check_setups()`로
   ①스키마 결손(FAIL) ②stale 14일+ ③기한 경과 미채점 ④**발동권(≥75%) 도달인데 오더 미배선**을 잡는다.
   ④가 핵심 — 정훈 6/28 지시가 *"조건 75%+ 충족 시 지정가 발동"*인데 8/6 감사에서
   **그 75%를 아무도 계산하지 않고 있었다**(발동권 3개가 조용히 도달해 있었다).
   🎯 WARN이 뜨면 **오더를 내거나, 안 내는 이유를 setup note에 남긴다** — '관망'은 결정이 아니다(8/2 원칙).
   오더가 나가면 `setup_schema.py --link <setup_id> <order_id>`로 연결할 것.
   🔒 조건 원문(`conditions[].text`)은 **불변** — 결과는 `outcome`에 쓴다(원문 덮어쓰기 금지).

   **[8/6 신설] `rule_tracker.py --snapshot`은 매 보고서 필수다.** 룰1은 7/31 RESET 정책상
   *매일 재계산*이 전제인데 원장이 7/30 1건에서 7일 멈춰 있었고, 그 1건이 말하는 상태
   (해금 35%·상한 282,438원·halted=false)가 8/6 실제(해금 15%·상한 0원·하드플로어 halted)와
   **정반대**였다 — 원장을 읽는 self-review §8·rule_tracker --score가 통째로 옛 상태를 본다.
   `validate_report.check_rule_ledger`가 3일 이상 정지 시 FAIL로 잡는다.
   (`--append`로 calls_log.jsonl에 이번 보고서 콜 1스냅샷을 쌓아둔다 → self-review가 후행 채점. reflection 루프의 적립 단계.)
   빌더(PM) 자가채점 대신 기계가 **보유 전종목·풀표 컬럼(별점·스코어·목표·매수존·트림·코멘트)·별점↔스코어 밴드·flows 추측수치·정본 버전 stale**을 점검한다. **FAIL이 있으면 고치고 재실행**(풀표 누락·컬럼 빠짐 재발 방지). WARN(별점↔스코어 어긋남 등)은 근거 재점검 후 의도면 통과. CLAUDE.md '현재 상태' 버전 토큰도 이 검사 대상 → 새 보고서면 그 줄도 +1.
   - **🤖 루틴(무인 스케줄) 시**: FAIL이면 고쳐줄 사람이 없으니 **스스로 교정 후 재검증**(빈 컬럼 채움·stale 버전 갱신 등 자동수정 가능한 건 끝까지 고친다). 정성 판단이라 자동수정 불가한 WARN(별점↔스코어 등)은 **STATE SNAPSHOT에 한 줄 명기하고 그대로 머지** — 무인이라 보는 사람이 없으니 멈추는 것보다 '검증 결과를 안고 완결'이 낫다. 커밋 메시지 끝에 `[validate PASS]` 또는 `[validate WARN n]` 표기로 흔적을 남긴다.
3. **git 커밋**(연속성의 백본 — 구버전은 git 히스토리에 남으므로 archive 폴더 불필요):
   ```bash
   git add docs/ data/app/ app/data.js && git commit -m "보고서 v{N} {날짜}: {한줄요약}"
   ```
   정훈이 푸시를 원하면 `git push`. (자동 스케줄링 워크플로는 자동 커밋·푸시함.)
4. 보고서 끝 **STATE SNAPSHOT**을 (a) 파일 안에 포함 + (b) 채팅에도 출력:

```
[STATE SNAPSHOT v{N} {날짜}]
현금: {잔액}원 (트랜치 1차/2차/3차 집행여부)
보유변동: {매수/매도 내역 or 없음}
워치리스트(활성): {종목들}
대기 트리거: {예: FOMC 6/18 03:00 → 3차 집행 판단}
영구교정: {새 정정사항 or 없음}
다음 버전: v{N+1}
```

5. 채팅엔 보고서 본문 + 파일 경로(`docs/reports/report_v{N}_{날짜}.md`)를 알린다.

## 6. 이슈 선택지 (분량 절감)

본문은 압축하고, 당일 이슈 중 정훈이 궁금해할 3~4개를 **번호 목록**으로 제시 →
정훈이 번호로 답하면 그 항목만 다음 메시지에서 상세 분석.

## 7. 지속 개선 루프

- **자가 콜 검증 [self-review 스킬 — 주간 첫 보고서 필수, 생략 불가]**: **주간 첫 보고서**(월요일 또는 그 주 첫 풀 보고서)와 **큰 장세 변화 뒤**에는 `self-review`를 **반드시** 돌린다 — 과거 별점·스코어·목표가·매수존 콜이 실제로 맞았는지 후행검증하고 `docs/research/call_scorecard.md`에 누적·캘리브레이션. 편향(별점 쏠림·순서 역전)·반복 빗나감은 채점기준/전망 교정을 정훈에게 제안(자동 변경 ❌). **누락 방지 [2026-06-22 강화 — 6/22 주간 첫 보고서서 실제 누락]**: 주간 첫 보고서인데 self-review를 건너뛰었으면 **그 주 다음 보고서의 맨 첫 단계로 밀어서 반드시 수행**(캘리브레이션 부채로 남기지 말 것). 평일 2번째~ 보고서는 생략 가능.
- **📖 데스크 학습 루프 [7/4 신설 — `desk_playbook.md` §4]**: 매 보고서 PM 종합 후 "이번에 배운 것"이 있으면 플레이북 §3 해당 데스크에 0~3줄 append(날짜 태그, 없으면 생략). self-review는 §2 캘리브레이션 수치 갱신. 무인 루틴에서도 동일 수행(append는 자동 OK, **채점기준 변경은 여전히 정훈 승인**).
- 정훈의 피드백/선택 패턴이 반복되면 master.md/CLAUDE.md 영구 반영을 제안.
- 워치리스트: 1주간 미선택·미언급 종목은 제외 예고 → 다음 보고서에서 제외(유망하면 근거와 함께 잔류 제안).
- 사실 오류를 정훈이 지적하면 즉시 "영구교정"으로 STATE SNAPSHOT + master.md §7에 기록.
