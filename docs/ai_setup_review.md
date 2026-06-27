# 주식 AI 세팅 리뷰 & 디벨롭 로드맵

> 외부 SOTA 트레이딩/리서치 AI를 폭넓게 공부해 정훈 세팅과 대조하고, 검증된 패턴 중
> **우리에게 실제로 부족한 것**만 골라 적용한다. (최초 2026-06-23 · **확장 갱신 2026-06-27**)
> 투자 자문 아님 — 분석 참고.

---

## 1. 참고한 외부 레퍼런스 (2026-06-27 폭넓게 확장)

| 레퍼런스 | 핵심 구조/아이디어 | 우리가 배울 점 |
|---|---|---|
| **TradingAgents** (Tauric, ICML'25 → v0.3.0 2026-06) | 애널리스트(펀더·센티·뉴스·기술)→강세/신중 **디베이트**→트레이더→**리스크팀**→펀드매니저 + reflection·memory. 최근판: **structured-output 에이전트·persistent decision log**(v0.2.4)·**grounded Sentiment**(v0.2.5)·**verified data contract + CI gate**(v0.3.0) | 우리 구조의 원본. 신규판이 우리 갭을 정조준 — **결정로그 구조화·검증 게이트** |
| **virattt/ai-hedge-fund** (GitHub ~45k★) | 투자거장 페르소나 + 밸류/센티/펀더/기술 + **Risk Manager(포지션 한도 계산)** + Portfolio Manager + **백테스터**(Sharpe·maxDD·누적수익) | 리스크매니저 정량 사이징·**백테스트 지표**. 단 "거래는 시뮬레이션만"(실집행 금지) |
| **ContestTrade** (arXiv 2508.00554, FinStep-AI) | **내부 콘테스트**: 에이전트를 실시장 피드백으로 실시간 채점·랭킹, **상위 출력만 채택**. Data팀이 대용량→압축 텍스트팩터(컨텍스트 절약) | "콜 스코어카드 = 우리식 시장피드백 랭킹"(B1 강화 근거). 컨텍스트 압축 |
| **FinRobot / FinGPT / FinAgent** (AI4Finance) | 4계층 에이전트 플랫폼·CoT·멀티모달·금융 LLM 파인튜닝 | 1인·분석전용엔 플랫폼/파인튜닝 과잉. 사상만 차용 |
| **예측 캘리브레이션 연구** (ForecastBench·arXiv 2507.04562·2511.18394) | LLM 예측 **1순위 실패 = 과신**. **Brier/log proper scoring**으로 신뢰도↔실측정확도 정렬(상위 LLM Brier~0.13 vs 슈퍼포캐스터 0.02). 경제·금융이 정치보다 약함. **앙상블(중앙값)이 과신 완화** | **별점=확신도인데 proper 캘리브레이션 점수가 없었음** → B1로 도입 |
| **InvestorBench** (ACL'25) | 주식·ETF·크립토 의사결정 벤치마크. 희소·고위험서 LLM 환각 | 벤치마크식 **후행평가** 사상(우리 calls_log·hunter_log = 자체 벤치) |
| **Anthropic "Building Effective Agents"** | 5패턴: 프롬프트체이닝·라우팅·**병렬화**·**오케스트레이터-워커**·**평가자-최적화자**. "가장 단순한 패턴으로 평가 통과시켜라" | 우리 구조를 5패턴에 매핑(§2) → 약한 고리 식별 |
| **Anthropic "멀티에이전트: 언제/언제 안 쓰나"** | 멀티에이전트 ≈ **토큰 15배**. (a)컨텍스트 오염 (b)병렬 가능 (c)특화가 도구선택 개선 — 이 3경우만 이득. 공유컨텍스트·강결합이면 부적합 | 8데스크 풀팬아웃의 **비용 규율 명문화**(§3) |
| **금융 환각 가드레일** (Claude for Fin·dual-model·watchdog) | 출처링크(RAG 환각 −45~65%)·**구조화 출력이 환각면적 축소**·생성/검증 분리·워치독 에이전트 | 결정/채널주장 **구조화**(B2·B3)·validate_report=결정적 검증자(보유) |

출처: [TradingAgents](https://github.com/TauricResearch/TradingAgents) · [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) · [ContestTrade](https://arxiv.org/abs/2508.00554) · [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) · [ForecastBench/calibration](https://arxiv.org/abs/2507.04562) · [InvestorBench](https://aclanthology.org/2025.acl-long.126/) · [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) · [멀티에이전트 언제 쓰나](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)

---

## 2. 우리 구조 ↔ Anthropic 5패턴 매핑 (약한 고리 찾기)

| Anthropic 패턴 | 정훈 세팅 대응 | 판정 |
|---|---|---|
| 병렬화(Parallelization) | 8데스크 동시 호출(지역2+섹터3+매크로+리서치+리스크) | ✅ 충실 |
| 오케스트레이터-워커 | PM이 데스크 분배·종합 후 최종판단 | ✅ |
| 라우팅 | 요청별 스킬 분기(보고서/quick-check/self-review/deepdive) | ✅ |
| 프롬프트 체이닝 | 데이터수집→스코어→디베이트→종합 단계 | ✅ |
| **평가자-최적화자** | **validate_report.py(결정적)+self-review(회고)+Stop훅** = 생성→평가 루프. 단 '평가→자동 재생성(optimize)'은 사람이 닫음 | ⚠️ 부분(의도적 — 자동변경 금지룰) |

**대조 표 — SOTA 요소 현황(2026-06-27)**

| SOTA 요소 | 정훈 세팅 | 판정 |
|---|---|---|
| 애널리스트 다부서 병렬 | 8데스크 | ✅ |
| 강세/신중 디베이트 | SKILL §2b bull/bear | ✅ |
| 리스크매니저(브레이크)+정량 사이징 | risk-desk + triggers.py(안전핀버퍼·집중도·트랜치) | ✅ |
| 검증된 방법론 렌즈 | CANSLIM·미너비니·드러켄밀러 → 0~100 스코어 | ✅ |
| 메모리/연속성 | STATE SNAPSHOT·git·hunter_log·**decisions.jsonl(신규)** | ✅ 강함 |
| reflection 정량 루프 | score_calls.py + **Brier 캘리브레이션(신규)** | ✅ |
| **콜 캘리브레이션(proper scoring)** | **Brier·버킷 갭·과신 플래그(B1 신규)** | ✅ (신규) |
| 소스 신뢰도 정량 추적 | **hunter_score.py(B3 신규)** | ✅ (신규) |
| 룰의 기계 강제 | settings.json 권한 + Stop훅 + validate_report | ✅ |
| 포트폴리오 백테스터(Sharpe/maxDD) | 없음 — calls_log 콜단위 후행평가로 대체 | 📋 의도적 미도입(§5) |

---

## 3. 비용 규율 (멀티에이전트 = 토큰 15배 · 2026-06-27 명문화)

Anthropic: 멀티에이전트는 단일대비 **토큰 ~15배**, 가치 높고 병렬·특화일 때만 정당화. 우리는 8데스크 전부 opus 4.8.
→ **풀팬아웃은 고가치에만, 경량은 분기한다**(이미 구조엔 있음 — 명문화):
- **일일 풀보고서 / 큰 장세 / 이슈 심층** = 8데스크 풀팬아웃(고가치·병렬·특화 = 3조건 충족 → 정당).
- **빠른 점검·시세·트리거·"지금 뭐 사" / 폰창 즉답** = `quick-check` 스킬(데스크 안 돌림).
- **단일 종목** = `stock-deepdive`(해당 섹터 1~2데스크만).
- **콜 점검·캘리브레이션** = `self-review`(데스크 없이 score_calls·hunter_score).
- 모델 다운그레이드(Sonnet)는 여전히 기각(결정 d2 — 품질 우선). 비용 규율은 **모델이 아니라 '언제 풀팬아웃하나'로** 관리.

---

## 4. 디벨롭 로드맵 — 적용 현황

**기반(2026-06-23~24 적용·요약)**: ①콜 채점기 `score_calls.py`+`calls_log.jsonl` ②룰 기계강제 `settings.json`+Stop훅 ③정량 포지션사이징 `triggers.py`.

**2026-06-27 신규 적용 (외부 폭넓은 조사 결과)**:
- **B1 — 콜 캘리브레이션 proper scoring** (`score_calls.py` 업그레이드): 별점→내재확률 + **Brier** + 버킷별 '표현확신 vs 실제상승률' 갭 → 과신/과소를 숫자로. *근거: 예측연구의 과신=1순위 실패 + ContestTrade 시장피드백 랭킹.* (첫 채점 Brier 0.381 = 6월말 폭락구간 상승콜 과신 정직 플래그.)
- **B2 — 구조화 결정 메모리** (`data/app/decisions.jsonl` + `decisions.py`): master §9/§10 산문의 **기계 검색 인덱스**. `query <키워드>`로 세션 시작 시 관련 결정만 끌어옴. *근거: 에이전트 메모리 연구 + persistent decision log + 구조화=환각축소.*
- **B3 — 채널 트랙레코드 채점기** (`hunter_score.py`): hunter_log의 [검증/정정/미확인]을 자동 집계(누적 정정률 13%·검증 46%). *근거: grounded sentiment·소스 신뢰도 정량화.* self-review §3을 수동→기계.

**📋 다음 후보(낮은 우선순위)**: 평가자-최적화자 루프의 '자동 재생성'은 자동변경 금지룰과 충돌 → 보류. 포트폴리오 백테스터는 §5.

---

## 5. 일부러 **안** 가져온 것 (정훈 세팅에 안 맞음 — 2026-06-27 확장)

- **자동매매/주문 실행**: 토스 조회전용·폰 거래창·추격금지와 정면충돌. 가드레일 best-practice도 "감독 없는 실행 금지". 분석 보조에서 멈춘다.
- **거장 페르소나 14종 분리**: 3개 방법론을 통합 스코어로 이미 녹임. 1인 포트폴리오에 14페르소나=토큰낭비.
- **무거운 포트폴리오 백테스터(Sharpe/maxDD 엔진)**: 16종목 장기보유 코어엔 과잉. **콜단위 후행평가(calls_log + Brier)**가 우리 의사결정(별점·매수존)에 더 직결.
- **GitHub Actions CI 게이트**: Stop훅이 이미 로컬 강제 + 12월 로컬 머신 이전 예정 → 한계효용 낮음. 보류.
- **다중모델 앙상블**(과신완화엔 유효): opus 4.8 단일 품질 우선(d2)·1인 비용. Bull/Bear 디베이트가 단일모델 내 유사 효과.
- **크립토·고빈도**: 포트폴리오 범위 밖.

---

*요약: 분석·디베이트·리스크·연속성 골격은 SOTA급. 2026-06-27 디벨롭의 핵심은 외부 폭넓은 조사에서 길어 올린 **(B1)콜 과신의 정량 감시 + (B2)결정 메모리 구조화 + (B3)소스 신뢰도 추적**. 자동매매·페르소나·무거운 백테스터·CI·앙상블은 근거를 갖고 의도적 제외.*
