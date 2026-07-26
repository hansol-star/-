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

Anthropic: 멀티에이전트는 단일대비 **토큰 ~15배**, 가치 높고 병렬·특화일 때만 정당화. ~~우리는 8데스크 전부 opus 4.8~~ **[7/4 개정: 경량 5개=sonnet/섹터 3개=opus → 7/15 재개정: 8개 전부 sonnet(=Sonnet 5, 6/29 출시 — 소넷 가격에 최상위급) — 품질 저하 시 섹터 3개 opus 롤백 조건부]**.
→ **풀팬아웃은 고가치에만, 경량은 분기한다**(이미 구조엔 있음 — 명문화):
- **일일 풀보고서 / 큰 장세 / 이슈 심층** = 8데스크 풀팬아웃(고가치·병렬·특화 = 3조건 충족 → 정당).
- **빠른 점검·시세·트리거·"지금 뭐 사" / 폰창 즉답** = `quick-check` 스킬(데스크 안 돌림).
- **단일 종목** = `stock-deepdive`(해당 섹터 1~2데스크만).
- **콜 점검·캘리브레이션** = `self-review`(데스크 없이 score_calls·hunter_score).
- ~~모델 다운그레이드(Sonnet)는 여전히 기각(결정 d2 — 품질 우선)~~ **[7/4 부분 개정]**: 경량 5개=sonnet/섹터 3개=opus. **[7/15 재개정]**: Sonnet 5 출시(6/29)로 '다운그레이드' 전제 자체가 소멸(소넷 가격에 최상위급 성능) → 섹터 3개도 sonnet 전환. d2의 '품질 우선'은 R3 주간 캘리브레이션의 품질 감시 + opus 롤백 조건으로 유지. '언제 풀팬아웃하나'(위 분기)와 함께 이중 규율.

---

## 4. 디벨롭 로드맵 — 적용 현황

**기반(2026-06-23~24 적용·요약)**: ①콜 채점기 `score_calls.py`+`calls_log.jsonl` ②룰 기계강제 `settings.json`+Stop훅 ③정량 포지션사이징 `triggers.py`.

**2026-06-27 신규 적용 (외부 폭넓은 조사 결과)**:
- **B1 — 콜 캘리브레이션 proper scoring** (`score_calls.py` 업그레이드): 별점→내재확률 + **Brier** + 버킷별 '표현확신 vs 실제상승률' 갭 → 과신/과소를 숫자로. *근거: 예측연구의 과신=1순위 실패 + ContestTrade 시장피드백 랭킹.* (첫 채점 Brier 0.381 = 6월말 폭락구간 상승콜 과신 정직 플래그.)
- **B2 — 구조화 결정 메모리** (`data/app/decisions.jsonl` + `decisions.py`): master §9/§10 산문의 **기계 검색 인덱스**. `query <키워드>`로 세션 시작 시 관련 결정만 끌어옴. *근거: 에이전트 메모리 연구 + persistent decision log + 구조화=환각축소.*
- **B3 — 채널 트랙레코드 채점기** (`hunter_score.py`): hunter_log의 [검증/정정/미확인]을 자동 집계(누적 정정률 13%·검증 46%). *근거: grounded sentiment·소스 신뢰도 정량화.* self-review §3을 수동→기계.

**2026-07-13 시스템 전면 점검 (B4 — 하네스 견고화)**: 전 스크립트 스모크·정합 감사에서 잡은 결함 일괄 수정 —
① `validate_report.py` 최신 보고서 판정을 **mtime→git 커밋시각**으로(fresh clone은 mtime이 전부 클론 시각으로 뭉개져 비결정 — v47 본편·부록 동일 커밋인데 가짜 FAIL 난 실사고. 같은 커밋 파일들은 tie-set으로 어느 쪽을 source_report로 가리켜도 통과, 미커밋 새 보고서는 mtime 폴백으로 여전히 감지).
② Stop 훅 판정 grep "FAIL" → **exit code**(통과 문구 "✅ FAIL 없음"에 오탐하던 버그).
③ **날짜·시각 KST 고정**: build_app_data(generated_at이 UTC 시각에 KST 라벨 — 앱 헤더 9시간 오표기)·snapshot(거래일 귀속 = KST−9h 명시, 05:30 크론 전일 귀속을 규칙으로 고정)·decisions/score_calls/missed_moves/earnings/triggers의 today() 전부 KST — 12월 로컬(KST) 이전 후에도 동작 동일.
④ 신규 가드 2: pm_view 신선도 WARN(≥1일 — PM 사견 매 보고서 필수인데 앱 4파일 의무에 빠져 있던 구멍) + app/data.js↔stocks.json source_report 대조(빌드 재실행 누락 감지).
⑤ 문서 모순 청산: 한은 점도표 옛 문구(master §7·SKILL §3b), 보유16→전종목(CLAUDE.md·SKILL), 3개→8개 데스크(SKILL 서두), 全opus·舊루틴(config_overview·본 문서).

**2026-07-14 신기능 라운드 (B5 — 정훈 지시 "새로 올라온 좋은 기능 찾아 적용")**: GitHub·공식 체인지로그·플러그인 마켓플레이스·MCP 생태계 조사 후 적용 —
- **B5a — SessionStart 훅 = 세션 실측 앵커** (`.claude/hooks/session-start.sh` + settings.json 등록): 세션이 열릴 때마다 KST 날짜·요일·시각, KRX/미장 세션 상태(스케줄 계산·공휴일 미반영 명시), 최신 report_v와 다음 버전 번호, 급락 TF ACTIVE, 폰 가용 여부를 additionalContext로 자동 주입. **★7/6 날짜 앵커링 영구교정의 기계화** — 오프라인·결정적(<1초)·실패 시 조용히 통과. 루틴(무인) 세션에도 자동 적용.
- **B5b — `macro_data.py` 무키 매크로 하드넘버** (FRED CSV + Polymarket, stdlib+curl): TradingAgents v0.3.0/0.3.1이 FRED·Polymarket을 데이터 벤더로 편입한 것을 우리식으로 이식. 미국채 10Y/2Y·2s10s·실질금리(TIPS)·기대인플레(BEI)·EFFR·VIX·WTI·달러지수·CPI YoY·실업률 11지표 — macro-desk 금리·물가 서술의 하드넘버 정본, risk-desk VIX/커브 스트레스 게이지. `--polymarket`은 이벤트 내재확률 참고(실측: 7월 FOMC 동결 93.5%). **실측 교훈**: FRED(Akamai)는 파이썬 TLS도, 브라우저 UA를 단 curl도 차단(UA↔TLS 핑거프린트 불일치 탐지) → curl 기본 UA 우선 경로로 해결.
- **B5c — `hunter_latest.py` srv3 자막 폴백**: 유튜브 json3 포맷 이상(2026 상반기 다수 보고) 시 같은 트랙을 srv3 XML로 재시도 — parse_timedtext는 이미 양쪽 지원, 요청부만 보강.
- **B5d — 낡은 오류 청소**: macro-desk.md에 잔존한 "한은 점도표 없음"(7/7 정정사항) 제거, 한은 점도표(2026.2 신설·2/5/8/11월 공개) 반영.

**보류 3건의 정훈 결정 [7/15 확정 — "추천대로 가자"]**: ①**섹터 3개 데스크 opus→Sonnet 5 전환 승인**(8개 전 데스크 = sonnet 별칭, R3 주간 캘리브레이션에서 별점·스코어 품질 저하 감지 시 opus 롤백 조건부) ②**settings.json allowlist 추가 승인**(macro_data·flow_trend·missed_moves·date — 무인 루틴 권한 프롬프트 차단 방지) ③**finance 플러그인 보류**(커스텀 스킬과 중복·간섭 리스크).

**2026-07-26 신규 라운드 (B6 — 정훈 지시 "다양한 곳에서 자료 찾아보면서 네이버api·유튜브도")**: 외부 문헌(검색량-투자자관심 연구)·Claude Code 공식 체인지로그·네이버 API 실측·유튜브 채널 자막을 함께 돌려 적용 —
- **B6a — `naver_sentiment.py` = 한국판 GSVI(리테일 심리 게이지)**: 검색량 기반 투자자 관심도 문헌(Financial Innovation 2023 systematic review·Cogent Econ. 2021 — **개인 주도 시장일수록 관심 급증 뒤 초과수익이 되돌아온다**)을 네이버 검색어트렌드로 이식. 산출 = 심리 3그룹(공포·항복·유입) **1년 %ile** + 보유 국내 5종목 **관심도 %ile** + **뉴스 버즈**(24/72h 기사수). 설계 핵심 2가지: ①**vol_gauge의 폭풍 %ile과 같은 %ile 문법**으로 맞춰 "가격이 격렬한가(폭풍) × 개인이 항복했는가(심리)"를 교차확인 가능하게 함 = "공포에 사라"의 정량 게이지 ②트렌드 ratio가 **1콜 내부에서만 정규화**되는 한계를 **1년치를 한 콜로 받아 그 안에서 %ile을 뽑는** 방식으로 우회(콜 간 비교 성립). **측정 전용 — 룰 불변**(vol_gauge와 동일 규율). 첫 실측(7/26): 공포 55.3%ile·**항복 75.9%ile(고조)**·유입 25.8%ile(무관심) = 반대매매·손절 검색이 붙는데 신규 유입은 죽은 국면. 종목 관심도는 삼성전자 72.3·LG전자 78.7·두산로보 70.4·현대차 55.7·NAVER 70.6%ile.
- **B6b — 유튜브 수집 파이프라인 2건 교정(실측 기반)**: ①**지식인사이드 제목필터 오설계** — 舊 필터가 시리즈명(`지식인클래스|지식선발대`)을 '금융 전용'으로 보고 통과시켜 비투자 회차(커리어·한글사·유럽여행) 자막을 3회 낭비(feeds_log 7/21·7/22·7/24 실측). 시리즈명을 통과 키워드에서 빼고 `title_exclude`로 차단하되, **강한 투자 키워드(HARD_KW: 종목명·증시 용어)가 있으면 오차단 방지로 통과**시키는 2단 구조로 교체 — 회귀 7케이스 PASS(실채널 재조회로 4편 정상 차단 확인). ②**월요일 주말 유실 구조** — R1은 평일 10:00·수집창 '전일~오늘'이라 **토요일 업로드가 월요일 창 밖으로 떨어진다**(지금껏 주말 보고서 세션이 우연히 메워옴). 월요일은 창을 3일로 자동 확장(`--since-days`로 수동 조정 가능).
- **B6c — 무인 루틴 권한 구멍 메움**: `settings.json` allowlist에 naver_data·naver_sentiment·naver_flows·naver_value·vol_gauge·vol_sizing·selfcheck 8개 추가(등록돼 있지 않아 무인 루틴에서 권한 프롬프트로 멈출 수 있던 스크립트들).
- **B6d — 외부 채널 2편 풀분석에서 건진 것**(feeds_log 7/26): ①**반도체 마진 추세 = 정점 판정축**이라는 우리 룰(master §10-2)이 윤지호 평론가의 "매출총이익률 80%대→5·60%대 하락이 조정 신호"와 **독립 교차확인** ②**피지컬AI 3조건 체크리스트**(인건비 대비 저렴·노동력 부족·투입 자리 → 미·중·한만 충족, 단 중국 저가형 침투는 역풍)를 power-physical-desk 상시 체크리스트로 편입 ③**토스가 AI 자동주문 API를 내기 시작**했으나 업계 인사도 "리스크 때문에 주문은 안 맡긴다" = 우리 **조회 전용 룰의 외부 지지 근거** ④MS Work Trend Index 2026의 '프론티어' 습관(일부러 AI를 안 쓰는 시간 + 답변 상시 의심 = **인지적 부채** 경고) = PM의 신뢰-견제 균형 규칙과 같은 결론.

**📌 정훈 결정 대기 (7/26 조사분)**: **Opus 5 출시**(claude-opus-5 = 현 Opus 기본, 1M 컨텍스트, fast mode $10/$50). 7/15 결정("8개 데스크 전부 sonnet, 품질 저하 시 섹터 3개 opus 롤백")의 **롤백 목적지가 이제 Opus 5**다 — 지금 롤백할지는 R3 주간 캘리브레이션의 품질 신호를 보고 정훈이 정할 사안이라 **자동 변경하지 않음**(모델 정책은 정훈 승인 사항).

**조사했으나 즉시 적용 안 한 것(7/14·근거 포함)**:
- **Anthropic 공식 finance 플러그인**(knowledge-work 마켓플레이스): 보류 확정(7/15) — 우리 커스텀 스킬과 중복 가능성.
- **fallbackModel 체인**(6월, 최대 3개 폴백): 웹 하네스에선 모델이 세션 고정이라 미적용 — 12월 로컬 이전 시 재검토.
- **중첩 서브에이전트(5레벨)·동적 워크플로(수백 에이전트)**: 8데스크 1레벨 팬아웃에 과잉 — 비용규율(§3) 위배.
- **금융 MCP 서버**(Yahoo/FMP/Shibui 등): 기존 stdlib 스크립트와 기능 중복, 무의존 포터빌리티(12월 이전) 우선 → 기각.
- **ai-hedge-fund 상시 펀드화·백테스터**: §5 기존 기각 유지(콜단위 후행평가가 더 직결).
- **파라미터 단위 권한 룰**(`Tool(param:value)`, 6월): 현 allowlist로 충분, 필요 시 도입.

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
