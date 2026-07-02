# 정훈 증권 — 세팅 한눈에 (Config Overview)

> 이 레포(`정훈 PORTFOLIO DESK`)의 전체 설정을 한 파일로 요약. 흩어진 설정(CLAUDE.md·에이전트·스킬·스크립트·자동화)의 지도.
> 상세 규약은 `CLAUDE.md`·`docs/master.md`·각 `SKILL.md`가 정본. 이 문서는 인덱스다.

---

## 0. 한 줄 요약

정훈 1인 전속 사설 증권사. 메인 Claude(=PM)가 **8개 서브에이전트 데스크**를 병렬로 굴려
**일일 포트폴리오 보고서**를 만들고, 결과를 `docs/reports/`·`data/app/`에 저장→git 커밋→main 머지로 연속성을 유지한다.
폰 앱(GitHub Pages)으로 시세·손익·할일을 본다.

- **`.claude/settings.json` 있음** [2026-06-24] — 권한 allowlist(루틴 스크립트·읽기전용 git 무프롬프트) + **Stop 훅**(`.claude/hooks/validate-on-stop.sh`: 보고서/정본 변경 시 `validate_report.py` 자동실행). `.mcp.json`은 없음(웹 하네스 기본 MCP 사용).
- 운영 정책은 전부 **CLAUDE.md(상시지침)** 와 **스킬 문서**로 표현된다.

---

## 1. 핵심 설정 파일

| 파일 | 역할 |
|---|---|
| `CLAUDE.md` | **상시 지침(매 세션 자동 로드).** 정체성·역할·리스크룰·운영제약·톤·연속성 규약·영구교정. 최우선 정본. |
| `docs/master.md` | 데이터·원가 고정·룰·워치리스트·일정·결정 메모리(§9)의 source of truth. |
| `docs/holdings_outlook.md` | 종목별 전망·별점/스코어 상세. |
| `README.md` | 레포 외부용 설명. |
| `.claude/settings.json` | 권한 allowlist + Stop 훅(validate 자동실행). 룰의 기계 강제. |

---

## 2. 서브에이전트 데스크 (`.claude/agents/`) — 전부 opus 4.8

TradingAgents 패턴(애널리스트→강세/신중 디베이트→리스크매니저→PM)을 정훈 포트폴리오에 맞춘 병렬 구조.

**지역축**
- `kr-market-desk.md` — 코스피·코스닥·국내 수급·특징주 + 국내 보유 5 시세
- `us-market-desk.md` — S&P·나스닥·다우·필반·위험선호 + 미국 보유 11 시세

**섹터축(지역 교차)**
- `semi-ai-desk.md` — 반도체·AI인프라 (삼성·NVDA·MU·AVGO·ANET / 원익IPS·테스·삼성전기·SK하이닉스·STM)
- `power-physical-desk.md` — 전력·인프라·피지컬AI (LG전자·두산로보·현대차·TSLA / 두산E·GEV·SK이노·방산조선)
- `bigtech-platform-desk.md` — 빅테크·플랫폼 (META·MSFT·AAPL·GOOGL·ORCL·NAVER / TMUS·SPCX)

**매크로·리서치·리스크**
- `macro-desk.md` — 환율·금리·물가·고용 지표와 시장 영향
- `research-feed.md` — 경제사냥꾼 유튜브 영상/쇼츠 자동 탐색·정리([검증/정정/미확인] 분류)
- `risk-desk.md` — 안전핀·트랜치·트리거·집중도 감시, 신중(bear) 관점. PM의 브레이크.

→ **PM(메인 Claude)** 이 위 입력을 종합해 최종 판단. 무게는 PM 종합에.

---

## 3. 스킬 (`.claude/skills/`)

| 스킬 | 트리거 | 하는 일 |
|---|---|---|
| `portfolio-desk` | "보고서"·"분석해줘"·"오늘 시장"·"브리핑" | 데스크 병렬 호출→종합 보고서 생성·저장·커밋 (메인 파이프라인) |
| `quick-check` | "빠른 점검"·"지금 시세/손익"·"매수존 왔어?" | 보고서 없이 30초 손익+트리거+시세 |
| `self-review` | "콜 점검"·"내 분석 맞았어?"·"자가검증" | 과거 콜 후행검증·캘리브레이션 |
| `stock-deepdive` | "OOO 딥다이브"·"OOO 살까말까" | 단일 종목 정밀 분석 |
| `market-chart` | 차트 요청 | 한국어 수급·시세 그래프 생성 |
| `youtube-watch` | 유튜브 링크·"이 영상 봐줘" | 영상 자막·메타·댓글 추출·분석 |

---

## 4. 스크립트 (`.claude/skills/portfolio-desk/scripts/`) — 전부 stdlib, 포터블

| 스크립트 | 역할 |
|---|---|
| `market_data.py` | Yahoo 무키 시세·환율·지수 (1차 소스, 키 불필요) |
| `toss_snapshot.py` | 토스 Open API **조회 전용** 실보유·현금 (주문 API 금지) |
| `fundamentals.py` | FMP API 미국주 펀더멘털 (스코어 하드넘버, `FMP_API_KEY`) |
| `consensus.py` | 증권사/IB 컨센서스 |
| `earnings.py` | 실적 일정 |
| `pnl.py` | 평가손익 계산 |
| `triggers.py` | 매수존/안전핀/이벤트 트리거 점검 |
| `snapshot.py` | 일별 스냅샷 저장 |
| `charts.py` | 차트 생성 |
| `hunter_latest.py` | 경제사냥꾼 최신 영상 탐색 |
| `build_app_data.py` | 폰 앱용 `app/data.js`·`data/app/*.json` 재생성 |
| `validate_report.py` | **완료검증 게이트** — 보유16·풀표 컬럼·별점↔스코어 밴드·정본 버전 stale 검사(FAIL 0 확인 후 커밋) |

---

## 5. 데이터·산출물

- **보고서**: `docs/reports/report_v{N}_{날짜}.md` (정본 = `docs/reports/`에서 가장 높은 `report_v*` — 현재 **v37**·2026-07-02). 끝에 STATE SNAPSHOT 블록. ※이 버전 토큰은 `validate_report.py`가 stale 검사.
- **포트폴리오 정본**: `.claude/skills/portfolio-desk/portfolio.json` (수량·현금·원가)
- **앱 데이터**: `data/app/{stocks,tasks,flows,hunter,hunter_archive}.json` → `build_app_data.py` → `app/data.js`
- **계획·할일·매수추적**: `data/app/tasks.json` (앱 #plan 화면 정본, 채팅 기반으로 갱신)
- **리서치 누적**: `docs/research/hunter_log.md`(경제사냥꾼 시계열)·`bubble_watch.md`
- **스냅샷**: `data/snapshots/{날짜}.json`

---

## 6. 루틴 & 자동화

**Claude Code Routines(구독·무인)** — 프롬프트 정본 = `docs/routines.md`:
- R1 아침 풀 브리핑(평일) · R2 폰창 집행 지시서(평일) · R3 야간 점검(평일) · **R4 주말 캘리브레이션(토 09:00, self-review)**.

**백업 자동화 (`.github/workflows/`)**:

| 워크플로 | 트리거 | 키 | 비고 |
|---|---|---|---|
| `daily-report.yml` | **수동(`workflow_dispatch`)만** — schedule 비활성 | `ANTHROPIC_API_KEY`(+토스 선택) | 일일 보고서는 Claude Code **Routines**(구독)로 전환됨. 이건 백업용. |
| `refresh-prices.yml` | 평일 17:25·05:30 KST cron | **키 0** | LLM 없이 Yahoo 시세만 긁어 `app/data.js` 갱신 (비용 0) |
| `deploy-app.yml` | `app/**` main push | — | 앱을 GitHub Pages로 자동 배포 |

> ⚠️ schedule cron은 워크플로가 **main에 있어야** 작동한다(연속성 규약과 직결).

---

## 7. 데이터 소스 우선순위 (개방형)

토스 API 실데이터 > 당일 스크린샷 > Yahoo 무키 시세 > 최신 보고서 스냅샷 > 마스터문서

- 시세/환율/지수 = `market_data.py`(Yahoo, 무키)
- 실보유/현금 = 토스 Open API(조회 전용) 또는 스크린샷
- 미국 펀더멘털 = FMP(일부 종목 402 → WebSearch 폴백)
- 뉴스/컨센서스 = WebSearch/WebFetch, **증권사 sell-side + 외신 우선**, 단일 출처 금지
- 경제사냥꾼 영상 = 방향성 채택·숫자 교차검증, [검증/정정/미확인] 분류

---

## 8. 고정 룰 (요약 — 정본은 CLAUDE.md)

- **리스크룰**: ①코스피 7,500 하회 시 잔여 트랜치 동결 ②LG전자 손절선 폐기(펀더 훼손 시만) ③추격매수 금지 ④레버리지·신용 없음
- **운영제약**: 폰 17:30~20:50 KST만. 국내 실시간 거래창 17:30~18:00. 미국은 20:50 전 지정가 예약. 토스 국내=정수 1주↑, 미국=소수점 가능.
- **보고서 규약**: 보유16+워치 풀표(별점·스코어·매수존·매도/트림 컬럼) 채팅에도 항상 출력. 디스클레이머는 파일 끝 1회만.
- **연속성**: 매 보고서 끝 main 머지·푸시 자동(묻지 않음). 다음 세션은 main 클론으로 복원.
- **스코어↔별점 밴드**: 85~100=⭐5 / 70~84=⭐4 / 55~69=⭐3 / 40~54=⭐2 / <40=⭐1

---

## 9. 실행 환경

- 현재 = **Claude Code 웹(클라우드 원격)**. 데이터센터 IP — Yahoo·웹검색 정상, 유튜브 봇차단 가능성(폴백 준비).
- 12월경 로컬 머신 이전 예정(주거용 IP). 스크립트 stdlib만 써서 그대로 이식.
- 글로벌 하네스 훅(`~/.claude/`의 stop-hook·git-identity 등)은 웹 환경 제공분이며 레포 설정 아님.

---

*이 문서는 인덱스/요약이다. 충돌 시 CLAUDE.md·master.md·각 SKILL.md가 우선.*
