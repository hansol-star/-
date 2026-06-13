# 정훈 PORTFOLIO DESK

Claude Code 기반 일일 투자 분석 데스크. claude.ai 프로젝트에서 이관 → **서브에이전트 병렬 데스크 + 무키 데이터 + git 연속성**으로 새로 설계.

## 빠른 시작

세션 안에서:

```
보고서
```

→ portfolio-desk 파이프라인이 발동: ① 최신 보고서 + master.md 복원 → ② 시장/매크로/리서치 데스크 병렬 수집
→ ③ PM 종합 → ④ `docs/reports/report_v{N}_{날짜}.md` 저장 + git 커밋 → ⑤ 본문 + STATE SNAPSHOT 출력.

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
  agents/                          서브에이전트 병렬 데스크
    market-desk.md / macro-desk.md / research-feed.md
  skills/
    portfolio-desk/
      SKILL.md                     PM 오케스트레이션 파이프라인
      portfolio.json               보유·원가·alerts 기계 정본 (master.md 미러)
      scripts/market_data.py       Yahoo 무키 시세/환율 (무의존)
      scripts/pnl.py               실시간 평가손익 + 합계 (원가 대비 수익률)
      scripts/consensus.py         애널리스트 목표주가 + ±30% 괴리 플래그
      scripts/triggers.py          매수존·안전핀·이벤트 트리거 실시간 점검
      scripts/toss_snapshot.py     토스 실데이터 (조회 전용)
      scripts/hunter_latest.py     경제사냥꾼 자동 탐색
    quick-check/SKILL.md           폰 거래창용 즉석 점검 (손익+트리거, 보고서 없이)
    youtube-watch/SKILL.md         유튜브 링크 → 자막·메타
```

## 빠른 점검 (폰 거래창 17:30~18:00)

전체 보고서가 필요 없을 땐:

```
빠른 점검     (또는 "퀵체크", "지금 손익", "트리거 점검")
```

→ `quick-check` 스킬이 평가손익 + 매수존/안전핀 트리거만 30초 안에. 🔴발동 트리거가 있으면 맨 위에 표시.

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
