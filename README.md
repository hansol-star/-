# 정훈 PORTFOLIO DESK

Claude Code 기반 일일 투자 분석 데스크. claude.ai 프로젝트에서 이관 → **서브에이전트 병렬 데스크 + 무키 데이터 + git 연속성**으로 새로 설계.

## 빠른 시작

세션 안에서:

```
보고서
```

→ portfolio-desk 파이프라인이 발동: ① 최신 보고서 + master.md 복원 → ② 데스크 병렬 수집(국장·미장 + 섹터3 + 매크로·리서치·리스크)
→ ③ 강세 vs 신중 디베이트 → ④ PM 종합 → ⑤ `docs/reports/report_v{N}_{날짜}.md` 저장 + git 커밋 → ⑥ 본문 + STATE SNAPSHOT 출력.

토스 실데이터를 쓰려면 키를 같이 주면 된다(저장 안 함):

```
보고서. 토스 키 client_id=xxxx client_secret=yyyy
```

키 없어도 **Yahoo 무키 시세**(`market_data.py`)로 시세·환율·지수는 전부 채워진다.

## 구조

```
CLAUDE.md                          상시 지침 (역할·리스크룰·연속성)
docs/
  master.md                        영구기준 (원가·룰·워치리스트·일정)
  reports/report_v{N}_{날짜}.md     일일 보고서 (git 버전관리)
  screenshots/                     계좌 스크린샷 (토스 키 없을 때 폴백)
.claude/
  agents/                          서브에이전트 병렬 데스크 (전부 opus 4.8)
    kr-market-desk.md              국장 — 코스피·코스닥·수급·국내 시세
    us-market-desk.md              미장 — S&P·나스닥·필반·미국 시세
    semi-ai-desk.md                섹터 — 반도체·AI인프라
    power-physical-desk.md         섹터 — 전력·인프라·피지컬AI
    bigtech-platform-desk.md       섹터 — 빅테크·플랫폼
    macro-desk.md                  환율·금리·지표·이벤트
    research-feed.md               경제사냥꾼 영상 [검증/정정/미확인]
    risk-desk.md                   리스크 매니저 — 안전핀·트랜치·트리거·신중 관점
  skills/
    portfolio-desk/
      SKILL.md                     PM 오케스트레이션 파이프라인
      portfolio.json               보유·원가·alerts 기계 정본 (master.md 미러)
      scripts/market_data.py       Yahoo 무키 시세/환율 (무의존)
      scripts/pnl.py               실시간 평가손익 + 합계 (원가 대비 수익률)
      scripts/consensus.py         애널리스트 목표주가 + ±30% 괴리 플래그
      scripts/triggers.py          매수존·안전핀·이벤트 트리거 실시간 점검
      scripts/earnings.py          보유·워치 실적 발표일 추적
      scripts/charts.py            비중 파이 + 수익률 막대 PNG
      scripts/snapshot.py          일별 손익 캐시 → 전일대비
      scripts/toss_snapshot.py     토스 실데이터 (조회 전용)
      scripts/hunter_latest.py     경제사냥꾼 자동 탐색
    quick-check/SKILL.md           폰 거래창용 즉석 점검 (손익+트리거, 보고서 없이)
    stock-deepdive/SKILL.md        단일 종목 정밀 분석 (시세·컨센서스·실적·뉴스)
    youtube-watch/SKILL.md         유튜브 링크 → 자막·메타
data/snapshots/                    일별 손익 스냅샷 (시계열, 커밋됨)
```

## 빠른 점검 (폰 거래창 17:30~18:00)

전체 보고서가 필요 없을 땐:

```
빠른 점검     (또는 "퀵체크", "지금 손익", "트리거 점검")
```

→ `quick-check` 스킬이 평가손익 + 매수존/안전핀 트리거만 30초 안에. 🔴발동 트리거가 있으면 맨 위에 표시.

## 📱 포트폴리오 앱 (폰에서 종목별 조회)

매일 자동 분석 결과를 **앱처럼** 본다. 홈에 총자산·당일손익·코스피 안전핀·발동 트리거·보유 16+워치 리스트가 뜨고,
**종목을 누르면** 현재가·평가손익·목표가·매수존·트림·⭐별점·최근 이슈(날짜·[검증/정정/미확인])가 상세로 펼쳐진다.

```
app/
  index.html     정적 SPA (백엔드·키 불필요, 폰 우선 다크 UI)
  app.js         홈/상세 라우팅·렌더
  style.css      스타일
  data.js        자동 생성물 (window.APP_DATA) — 직접 수정 금지
data/app/
  stocks.json    종목별 분석 정본 (별점·목표·매수존·트림·이슈) — 보고서가 갱신
.claude/skills/portfolio-desk/scripts/
  build_app_data.py   portfolio.json + stocks.json + Yahoo 시세 → app/data.js 빌드
```

**데이터 갱신** (보고서 돌리면 자동으로 같이 됨):

```bash
python3 .claude/skills/portfolio-desk/scripts/build_app_data.py   # 실시간 시세로 빌드
# 네트워크 차단 시:  python3 ... build_app_data.py --offline
```

**폰에서 열기** — GitHub Pages 배포(1회 설정): 레포 **Settings > Pages > Source = "GitHub Actions"** 로 바꾸면
`deploy-app.yml`이 main 푸시마다(=매일 자동 보고서 커밋 포함) 앱을 재배포한다.
배포 URL을 폰 브라우저에서 열고 **"홈 화면에 추가"** 하면 앱 아이콘처럼 쓸 수 있다.
로컬에서 바로 보려면 `app/index.html`을 브라우저로 열어도 된다(`data.js` 인라인이라 파일만으로 동작).

**매일 자동**: `daily-report.yml`이 매 평일 17:20 KST에 보고서를 생성→`stocks.json`·`data.js` 갱신→커밋,
이어서 `deploy-app.yml`이 앱을 재배포. (Anthropic API 키 시크릿 1회 설정 필요 — 워크플로 상단 주석 참고.)

## 데이터 소스

| 용도 | 소스 | 키 |
|---|---|---|
| 시세·환율·지수 | Yahoo Finance (`market_data.py`) | 불필요 |
| 실제 보유·현금 | 토스 Open API (조회 전용) / 스크린샷 | 토스 키(선택) |
| 뉴스·수급·컨센서스 | WebSearch / WebFetch | 불필요 |
| 경제사냥꾼 영상 | yt-dlp (`hunter_latest.py`) | 불필요 |

## 환경

- **현재 = Claude Code 웹**(데이터센터 IP). Yahoo·웹검색 정상. 유튜브는 봇차단 가능 → 폴백 체인.
- **12월경 로컬 머신 이전 예정**(주거용 IP). 스크립트는 stdlib만 써서 그대로 이식.

**투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.**
