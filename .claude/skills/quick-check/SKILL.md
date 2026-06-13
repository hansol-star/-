---
name: quick-check
description: 전체 보고서 없이 빠른 포트폴리오 점검. 사용자가 "빠른 점검", "퀵체크", "지금 시세", "지금 손익", "트리거 점검", "지금 뭐 사야 돼", "매수존 왔어?"라고 하거나, 폰 가용 17:30~18:00 거래창에서 즉시 판단이 필요할 때 사용한다. 평가손익 + 매수존/안전핀 트리거 + 핵심 시세만 30초 안에 보여준다. 무거운 데스크 파이프라인(보고서)은 돌리지 않는다.
---

# Quick Check — 즉석 포트폴리오 점검

정훈의 **폰 가용 17:30~20:50 KST**, 특히 국내 실시간 거래창 **17:30~18:00**에
"지금 뭘 눌러야 하나"를 30초 안에 답하는 경량 점검. 전체 보고서(portfolio-desk 스킬)와 달리
서브에이전트·경제사냥꾼·웹검색을 돌리지 않고, **검증된 무키 스크립트만** 실행한다.

## 실행 (프로젝트 루트에서)

```bash
# 1) 실시간 평가손익 (원가 대비 수익률 + 합계)
python3 .claude/skills/portfolio-desk/scripts/pnl.py

# 2) 매수존·안전핀·이벤트 트리거 점검 (🔴발동 / 🟢대기 / 📅이벤트)
python3 .claude/skills/portfolio-desk/scripts/triggers.py
```

필요 시 추가:
```bash
# 핵심 시세만 빠르게 (지수·환율 또는 특정 종목)
python3 .claude/skills/portfolio-desk/scripts/market_data.py --group index
python3 .claude/skills/portfolio-desk/scripts/market_data.py --tickers 005930.KS,035420.KS
# 목표주가 괴리 빠른 확인
python3 .claude/skills/portfolio-desk/scripts/consensus.py --tickers META,AVGO
```

## 출력 형식 (간결)

1. **🔴 발동 트리거가 있으면 맨 위에** — 무엇을, 얼마에, 왜(룰 근거). 폰 거래창 안에 실행 가능한지(시간) 명시.
2. **손익 한 줄 요약** — 총 자산 / 주식 평가손익 합계 / 눈에 띄는 종목.
3. **🟢 임박 트리거** — 매수존까지 거리(%), 근접한 것만.
4. 토스 키를 같이 주면 `toss_snapshot.py`로 실제 보유·현금 교차확인.

## 규약 (보고서와 동일하게 지킬 것)

- **투자 자문 아님.** 트리거 발동은 룰 충족 알림일 뿐, 실행은 정훈 판단.
- 매수 안전핀: 코스피 7,500 하회 시 잔여 트랜치 전면 동결(triggers.py가 표시).
- 추격매수 금지. 분수주=시장가/정수주=지정가. 야간 지표는 당일 밤 트리거 금지.
- 빠른 점검에서 영구 변경(매매 체결 등)이 확인되면 정훈에게 `portfolio.json`/master.md 갱신을 제안.
- 더 깊은 분석이 필요하면 "보고서"로 전체 파이프라인 안내.
