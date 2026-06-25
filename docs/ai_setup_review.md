# 주식 AI 세팅 리뷰 & 디벨롭 로드맵

> 외부 SOTA 트레이딩 AI 프레임워크를 객관적으로 공부해 정훈 세팅과 대조하고, 검증된 패턴 중
> **우리에게 실제로 부족한 것**만 골라 개선 로드맵으로 정리했다. (2026-06-23)

---

## 1. 참고한 외부 세팅 (객관 레퍼런스)

| 프레임워크 | 핵심 구조 | 우리가 배울 점 |
|---|---|---|
| **TradingAgents** (Tauric Research, ICML'25) | 애널리스트(펀더·센티·뉴스·기술) → 강세/신중 **디베이트** → 트레이더 → **리스크팀** → 펀드매니저. + **reflective agent**(회고)·memory | 우리 구조의 원본. **reflection을 자동 루프**로 돌리는 게 성능 차별점 |
| **virattt/ai-hedge-fund** (GitHub 인기) | **투자 거장 페르소나 14**(버핏·멍거·버리·드러켄밀러·우드·린치·그레이엄·탈렙…) + 밸류/센티/펀더/기술 4 + **Risk Manager(포지션 한도 계산)** + Portfolio Manager + **백테스터** | ①페르소나=다중 렌즈 디베이트 ②리스크매니저가 **포지션 한도를 정량 계산** ③**백테스트 내장** |
| **FinMem / FinAgent** (AAAI) | Profiling(성격) + **계층적 메모리(layered memory)** + Decision. reflection-driven, 환각 억제, 백테스트 우위 | **메모리 계층화 + 회고가 곧 성능**. 메모리를 '검색 가능한 구조'로 |
| 가드레일 베스트프랙티스 (프로덕션) | **직무 분리**(단계별 권한 분리), AI를 "수습 중인 주니어 = 신뢰 못 할 제안자"로 취급, 단계마다 신뢰 획득·상시 감독 | 룰을 **산문이 아니라 기계로 강제** |

출처: [TradingAgents arXiv 2412.20138](https://arxiv.org/abs/2412.20138) · [github.com/TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) · [github.com/virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) · [FinMem arXiv 2311.13743](https://arxiv.org/abs/2311.13743)

---

## 2. 대조 — 정훈 세팅은 이미 어디까지 와 있나

정훈 세팅은 **TradingAgents 패턴을 1인 포트폴리오에 정밀 이식**한 보기 드물게 성숙한 구조다.

| SOTA 요소 | 정훈 세팅 현황 | 판정 |
|---|---|---|
| 애널리스트 다부서 병렬 | 지역축(국·미) + 섹터축 3 + 매크로·리서치 = 8 데스크 병렬 | ✅ 충실 |
| 강세/신중 디베이트 | SKILL §2b — PM이 bull/bear 1단락씩 맞세움 | ✅ |
| 리스크 매니저(브레이크) | risk-desk + triggers.py(안전핀·매수존) | ✅ |
| 펀드매니저 최종판단 | PM 종합 | ✅ |
| 검증된 방법론 렌즈 | CANSLIM·미너비니·드러켄밀러 → 0~100 스코어 | ✅ (페르소나 대신 통합 스코어) |
| 메모리/연속성 | STATE SNAPSHOT·master §9 결정로그·hunter_log 시계열·git | ✅ 강함 |
| **reflection(회고) 자동 루프** | self-review 스킬 **있으나 산문·수동·비정량** | ⚠️ **갭** |
| **콜 후행 백테스트** | 없음 (call_scorecard.md도 미생성) | ❌ **갭** |
| **룰의 기계 강제** | validate_report.py 게이트는 **손으로** 돌려야 함, 연속성 머지도 수동 | ⚠️ **갭** |
| 리스크매니저 **정량 포지션 사이징** | 3분할 트랜치(산문) — 한도 계산식 없음 | ⚠️ 약함 |

**결론**: 분석·디베이트·리스크 구조는 SOTA급. 부족한 건 **회고를 정량·자동으로 닫는 루프**와 **룰의 기계 강제**다.

---

## 3. 디벨롭 로드맵 (우선순위)

### ✅ 이번에 구현 — ① 콜 캘리브레이션 채점기 (reflection 정량화)
FinMem·TradingAgents가 성능 차별점으로 꼽는 "reflection 자동 루프"를 우리 데이터로 구현.
- **통찰**: `data/app/stocks.json`의 **git 히스토리 = 구조화된 콜(별점·스코어·목표·매수존)의 시계열**. 별도 로깅 인프라 없이 git이 이미 원장.
- **산출물**: `scripts/score_calls.py` + `data/app/calls_log.jsonl`(원장).
  - `--backfill`: git 히스토리에서 원장 재생성 (이미 64콜 백필됨).
  - `--append`: 매 보고서 현재 콜 1스냅샷 누적.
  - (인자 없음): 별점 버킷별 **평균 전진수익률 + 방향 적중률 + 매수존 진입률 + 목표 터치율**, 그리고 **별점 역전·과신 편향 자동 플래그**.
- **self-review 연동**: 콜 점검 시 이 스코어를 베이스로 사람이 캘리브레이션(자동 변경 ❌).
- 첫 채점 예시(6/20~23, 폭락장 노이즈 큼): ⭐5(−2.73%) > ⭐2(−7.63%) — 고확신 콜이 셀오프에서 덜 빠짐(정상 신호). ⭐5<⭐4 미세역전은 점검 후보로 플래그.

### ✅ 구현됨 — ② 룰의 기계 강제 (가드레일 베스트프랙티스 · 2026-06-24 적용)
`validate_report.py`(완료게이트)·main 머지(연속성)를 *기억해서* 돌리던 걸 하네스가 강제하도록
`.claude/settings.json`을 신설했다(정훈 승인 후 적용). 권한 allowlist(루틴 스크립트·읽기전용 git 무프롬프트)
+ **Stop 훅**(`.claude/hooks/validate-on-stop.sh`: 보고서/정본 변경 시 validate 자동실행). 아래는 적용된 형태:

```jsonc
// .claude/settings.json (제안)
{
  "permissions": {
    "allow": [
      "Bash(python3 .claude/skills/portfolio-desk/scripts/*.py:*)",  // 루틴 스크립트 권한팝업 제거
      "Bash(git fetch:*)", "Bash(git log:*)", "Bash(git show:*)",
      "Bash(git status:*)", "Bash(git diff:*)", "Bash(git ls-tree:*)",
      "WebSearch", "Read", "Glob", "Grep"
    ]
  },
  "hooks": {
    // Stop 훅: 보고서/정본 변경이 있으면 validate_report.py를 자동 실행해 결과를 항상 노출
    // (FAIL인 채로 '다 됐다' 선언 방지). 변경 없으면 침묵. 비차단 권장.
    "Stop": [{ "matcher": "", "hooks": [
      { "type": "command", "command": ".claude/hooks/validate-on-stop.sh" }
    ]}]
  }
}
```
→ **효과**: 권한팝업↓(마찰 제거) + 완료게이트가 산문 규칙에서 **기계 게이트**로 승격. 승인하면 훅 스크립트까지 만들어 넣는다.

### ✅ 구현됨 — ③ 리스크매니저 정량 포지션 사이징 (2026-06-24)
ai-hedge-fund의 Risk Manager처럼 트랜치 크기를 **현금·안전핀 버퍼·집중도 계산식**으로. `triggers.py`에 추가:
- `recommend_tranche()`: 코스피 안전핀(7,500) 버퍼로 다음 트랜치 규모 스케일. **하회 시 0(전면 동결)**, 버퍼<5% 절반, 정상이면 계획대로 3분할. → "이번 트랜치 권장 금액 + 1회 분할액" 출력.
- `concentration()`: 보유 실시간 평가비중 + **단일종목 25% 상한** 초과 자동 플래그(추가매수 금지·트림 후보).
- `python3 triggers.py` 끝에 **## 포지션 사이징** 패널 자동 출력(`--no-size`로 생략, `--json` 지원).
- 검증(6/24 라이브): 코스피 8,471·버퍼 +12.9% → 1차 235,000원(3분할 ≈78,333원), NVDA 20.9% 비중 1위(상한 내). 산문 "3분할"이 **숫자**가 됨.

### 📋 제안 — ④ 메모리 검색 구조화 (낮은 우선순위)
master §9 결정로그·hunter_log가 산문 → 보고서 시작 시 **관련 결정만 키워드로 끌어오는** 인덱스(`decisions.jsonl`). FinMem의 layered memory 착안. 규모 커지면 도입.

---

## 4. 일부러 **안** 가져온 것 (정훈 세팅에 안 맞음)

- **거장 페르소나 14종 분리**: 우리는 이미 3개 방법론을 통합 스코어로 녹였다. 1인 포트폴리오에 14 페르소나는 과잉·토큰낭비. 통합 스코어 유지가 맞다.
- **자동매매/주문 실행**: 정훈 룰(토스 조회전용·폰 거래창·추격금지)과 정면충돌. 분석 보조에서 멈춘다. (가드레일 best-practice도 "감독 없는 실행 금지")
- **암호화폐·고빈도**: 포트폴리오 범위 밖.

---

*요약: 우리 분석·디베이트·리스크 골격은 이미 SOTA급. 이번 디벨롭의 핵심은 **회고를 정량·자동으로 닫는 루프(①)**. ②~④는 승인 시 순차 적용.*
