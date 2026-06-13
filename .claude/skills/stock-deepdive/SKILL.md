---
name: stock-deepdive
description: 특정 종목 하나를 정밀 분석. 사용자가 "OOO 딥다이브", "OOO 자세히 분석해줘", "OOO 살까 말까", "이 종목 분석", "OOO 들어가도 돼?"처럼 단일 종목의 심층 분석(시세·밸류·애널리스트 컨센서스·실적일정·뉴스·차트)을 요청할 때 사용한다. 전체 포트폴리오 보고서가 아니라 한 종목에 집중한다.
---

# Stock Deep-Dive — 단일 종목 정밀 분석

한 종목을 시세·컨센서스·실적·뉴스·포지션 관점에서 깊게 본다. 투자 자문 아님 — 분석 참고, 결정은 정훈.

## 입력 해석

종목명 → 티커 변환. 보유/워치면 `portfolio.json`에 티커가 있다. 새 종목이면 추정 티커 확인
(국내 6자리+`.KS`/`.KQ`, 미국 심볼). 애매하면 정훈에게 확인.

## 수집 (프로젝트 루트에서)

```bash
TICKER=NVDA   # 예시
python3 .claude/skills/portfolio-desk/scripts/market_data.py --tickers $TICKER   # 현재가·등락
python3 .claude/skills/portfolio-desk/scripts/consensus.py  --tickers $TICKER    # 목표주가·의견·괴리
python3 .claude/skills/portfolio-desk/scripts/earnings.py   --tickers $TICKER    # 다음 실적일
```
- 보유 종목이면 `pnl.py` 출력에서 해당 종목의 평가손익도 인용.
- 뉴스·촉매·리스크: **WebSearch** — "[종목] news catalyst [날짜]", "[종목] 목표주가" (한국 증권사 컨센서스 보강).
- 경제사냥꾼이 다룬 종목이면 `hunter_latest.py` 결과나 youtube-watch로 해당 영상 교차참조.
- 차트가 필요하면 `charts.py`(포트폴리오 전체) 또는 종목 시세를 표로.

## 출력 형식

```
# 딥다이브 — {종목} ({티커})
## 한 줄 결론 + ⭐(1~5)
## 1. 현재 위치       현재가·등락·52주 위치, (보유면) 내 평단·수익률
## 2. 밸류·컨센서스    애널리스트 목표(평균/고/저)·의견·#·현재가 대비 괴리(±30% 플래그)
## 3. 촉매 & 리스크    강세 논지 / 약세 논지 양쪽 병기 (검증된 사실 위주)
## 4. 실적·일정        다음 실적일(D-N), 관련 매크로 이벤트
## 5. 포지션 관점      신규/추가매수/홀딩/트림 + 매수존·근거. 내 룰(추격금지·안전핀·트랜치)과 연결
```

## 규약

- 검증 안 된 수치는 "미확인". 자동자막·단일출처는 교차검증.
- 강세·신중 양쪽 시각 병기. 추격매수 금지·안전핀(코스피 7,500)·폰 가용시간 룰 반영.
- 새로 보유에 편입/제외가 결정되면 `portfolio.json` + `docs/master.md` 갱신 제안.
- 더 넓은 시장 맥락이 필요하면 "보고서"(portfolio-desk)로 연결.
