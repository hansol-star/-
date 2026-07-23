# 🧰 도구·세팅 평가 로그 (dev tooling evaluations)

> 정훈이 공유하거나 우리가 발견한 **외부 도구·세팅·방법론**을 우리 데스크에 맞는지 평가한 기록.
> 최신이 맨 위(prepend). 각 항목 = 무엇 · 우리 fit · **[채택/기각/보류]** · 근거.
> 영상·전문가 콘텐츠 = `study_log.md` / 경제사냥꾼 = `hunter_log.md`. 여기는 **도구/세팅** 전용.
> 목적: "제자리 안 머물고 계속 나아지되, 안 맞는 도구는 짐" — 성장의 기록이자 재평가 트리거.

---

## 2026-07-23 — SEC EDGAR 13F 대가 흐름 수집기 (`guru_flows.py`, 자체 stdlib) · [채택]

**계기**: 정훈 지시 "워런버핏 같은 주식 대가들의 흐름도 알아보자 — 데이터 무겁게 다 가져와 그들이 그렇게 결정하는 '이유'를 보고 참고하자." §10 #5 '큰손 13F 회전'이 v33~ 수동 방치돼 있던 걸 기계화.

**후보 비교**:
- **SEC EDGAR 직접**(data.sec.gov/submissions + Archives info-table XML) — 무키·stdlib·정본·이식가능. 13F는 분기말 후 ~45일 지연. **[채택]**
- WhaleWisdom/Dataroma 집계 스크래핑 — 편하나 3rd-party·단일출처·비이식. **[기각]** (플레이북 §1a 단일출처 금지·§1b 공식소스 검증 원칙과 상충)
- ai-hedge-fund 페르소나 에이전트(버핏·멍거·버리 '연기') — **[기각·재확인]** study_log 2026-07-02에서 이미 기각(채점 렌즈로 흡수·과설계). 우리 것은 페르소나 연기가 아니라 **실보유변동 데이터 + 이유 분석**.

**채택 = 하이브리드**: EDGAR = **팩트 정본**(무엇·얼마·다분기 궤적·우리 겹침) + guru-flow-desk가 외신·주주서한·sell-side로 '**왜**'와 '**우리 참고점**' 보강.

**검증(플레이북 §1b 3단 통과)**: ①공식 docs 확인(data.sec.gov 제출목록 JSON·Archives info-table XML 스키마) ②실호출 스모크 = 버크셔 CIK 0001067983 다분기 실수집 성공(2026Q1 90종목·$263.1B, 알파벳 +224%·애플 홀드 확인) ③출처 명기(guru_flows.json `sources`에 accession#). **하네스**: selfcheck GATE PASS(compile/import + validate_report check_guru).

**설계 교훈(기록)**: ①**13F value 단위가 파일러마다 다름**(Berkshire=달러 vs Duquesne=천달러, SEC 2023 규칙 불구) → filingDate 추정 폐기, **내재가격(value/shares) 중앙값<$1이면 ×1000** 자동판정(`_autoscale_value`) ②정정(13F-HR/A)이 부분 보유(예: confidential 4종목)만 담을 수 있음 → **원본 13F-HR 우선**(안 그러면 애플이 0주로 사라지는 버그) ③filing 순서 ≠ 분기 순서 → report_date 정렬 ④`--emit`은 팩트만 갱신·데스크 서사 병합 보존 ⑤**집계매체 분기 오귀속**(테퍼 'Q1 알파벳 +29%'는 실은 Q4) → EDGAR 원본 주식수로 방향·분기 대사 ⑥옵션중심 파일러(Scion/버리)는 holdings 비어도 infoTable 봤으면 유효 스냅샷 반환(풋 시그널 보존).

**[7/23 6인 확장]**: 시각이 갈리는 6대가(버핏·버리·드러켄밀러·애크먼·테퍼·로엡, Bridgewater류 700+종목 분산은 '왜' 부재로 제외) + build_app_data가 **우리 보유종목 축 consensus 교차정리** 산출. 크로스 결과 = GOOGL 분열(2매수 3매도)·NVDA 광범축소·MU/AVGO 축적 — **분열 종목은 과신 견제 신호**로 활용.

**배선**: `guru_flows.py`(6대가) → `data/app/guru_flows.json` → build_app_data(consensus) → 앱 #gurus 화면·종목 상세 대가라인 + guru-flow-desk 보고서 섹션. 트리거-게이트(분기 cadence).

---

## 2026-07-20 — "7개 자동화 부서" 42스킬 팩 (hongik.man) · 정훈 공유 인스타

**출처**: 인스타 캐러셀 8장(hongik.man "클로드 하나로 회사 전체를 돌린다면"). claude code 밑에 7부서 42스킬 무료 팩.

**부서별 스킬 + 우리 1인 투자 데스크 fit**:
- **개발**: Superpowers·**verification**(완료 전 실행확인)·**systematic-debug**(근본원인)·Context7(최신 공식문서)·**Skill Creator**·MCP Builder → verification/skill-creator/systematic-debug는 **우리가 이미 보유**(verify 스킬·selfcheck·skill-creator). Context7=보류(우린 stdlib 위주). MCP Builder=기각(스크립트 씀).
- **재무(CFO)**: **dcf-model**(내재가치)·**comps-analysis**(피어 상대가치)·3-statements·lbo-model·pitch-deck·**finance_skills**(밸류·포트폴리오 81종 팩) → **여기가 유일하게 진짜 관련.** dcf/comps=우리 갈망하던 자체 밸류. 3-statements·lbo·pitch=IB용, 기각.
- **운영**: **xlsx**(엑셀)·incident-postmortem(사고회고)·sop-builder·business-case·launch-runbook·internal-comms → xlsx=**built-in 보유**(포트폴리오 엑셀 내보내기 가능). postmortem=우리 self-review·미스무브 회고가 이미 그 역할. 나머지 회사운영용 기각.
- **법무**: contract-review·ai-legal-claude·legal-risks·compliance·**docx**·sql-queries → docx=**built-in 보유**. sql=기각(우린 JSON/jsonl). 나머지 법무=무관 기각.
- **디자인**: ui-ux-pro-max·taste-skill·frontend-design·web-artifacts·canvas-design·algorithmic-art → 전부 웹디자인, 우린 차트만(dataviz+chart_style 보유). 기각.
- **마케팅·소셜**: SEO·광고·블로그·이메일·영상 12종 → 1인 투자 데스크와 **전면 무관, 전부 기각**.

**PM 종합 → [1개만 진짜 추가 후보: 자체 밸류에이션]**
- 42개 중 41개는 '회사 운영'용이거나 우리가 이미 보유. **유일한 실질 빈틈 = dcf-model + comps-analysis**(자체 내재가치·피어 상대가치).
- 왜 값진가: 지금 우리 0~100 스코어는 FMP 하드넘버 + **증권사 컨센서스 목표가**에 기댐. 자체 DCF/comps가 있으면 **'우리 숫자 vs sell-side' 교차검증**이 생김 → CLAUDE.md "증권사 우선하되 과신 견제" 철학에 정확히 부합.
- ⚠️ 단, hongik.man 팩을 통째 설치 X. ①출처·코드 미검증 3rd-party ②DCF는 성장·WACC·터미널 가정에 극도로 민감(AI 슈퍼사이클 고성장주엔 특히) → **우리가 FMP 데이터 재사용해 경량 `valuation.py`로 직접 만드는 게 맞음**(stdlib·포터블·가정 투명). "덜어내라·내 워크플로를 도구로" 교훈대로.
- 나머지(verification·xlsx·docx·skill-creator·systematic-debug)는 이미 보유 → 배선/활용만 하면 됨(신규 설치 불요).

**출처**: 유튜브 `5rbzj5IUA78`("클로드 스킬 100개 써봤는데 진짜는 이 6개", 2026-07-10, 10:18, 조회 2.9만). 자동생성 자막(수치·고유명사 오독 가능).

**핵심 메시지(채택)**: "많이 까는 게 아니라 **잘 덜어내는 게 핵심**. 화려한 것 말고 **계속 손이 가는 것만** 남겨라. 스킬 = 같은 말 반복 대신 **내 워크플로를 도구에 정리해 심는 것.**" → 우리가 Graphify 기각하고 맞는 것만 얹은 철학과 동일. 이 메타교훈이 6개 스킬보다 더 값짐.

**6개 스킬 우리 데스크 fit 채점** (연구·보고 데스크 = Python 스크립트+마크다운+스킬, 토큰예산 민감):

| 스킬 | 무엇 | 우리 fit | 판정 |
|---|---|---|---|
| **Ponytail** (DietrichGebert) | "제일 게으른 시니어" — 코딩 전 '존재해야 하나/이미 있나/한 줄로 되나' 게이트, 과설계·토큰 절감 | 방금 우리가 earnings·charts 중복확인한 그 규율. `dev_workflow.md` 재사용체크에 이미 반영 | **부분채택**(원칙 채택·스킬설치는 선택) |
| **Caveman** (JuliusBrussee) | 출력을 원시인처럼 짧게, CLAUDE.md 압축 | ⚠️ 출력 축약 = 정훈 "풀표·상세보고" 요구와 **정면충돌**. CLAUDE.md 압축은 룰·톤·교정 뭉개질 위험 | **기각** |
| **Taste Skill** (Leonxlnx) | 안티슬롭 웹디자인(랜딩페이지 취향) | 우린 랜딩페이지 안 만듦. 차트 취향은 dataviz+chart_style로 이미 커버 | **기각** |
| **Matt Pocock skills** (mattpocock) | grill-me(코딩 전 취조)·작은 조합형 스킬·핸드오프 | grill-me=우리 AskUserQuestion·"확장 전 묻기" 이미 실천. 핸드오프=dev_handoff.md 있음 | **부분채택**(원칙 이미 보유) |
| **ECC** (affaan-m) | 해커톤 우승자 10개월 세팅 통째 = 설치용 아니라 '카탈로그' | 우리 세팅 이미 성숙. 아이디어(메모리·보안스캔) 참고용 구경만 | **보류**(가끔 아이디어 채굴) |
| **last30days** (mvanhorn) | 주제 던지면 Reddit·X·유튜브 최근30일 병렬검색→점수→브리핑 | 리테일 심리/테마 리서치에 흥미로움(예 "NVDA 30일 여론"). ⚠️쿠키 보안주의 + 기존 WebSearch·naver_data·research-feed와 중복 | **보류**(보안·중복 검토 후) |
| +보너스 **Superpowers** (obra) | 발표자 개인 베스트 | 미평가 — 나중에 살펴볼 후보 | 노트 |

**PM 종합**: 6개 대부분은 **일반 개발·웹빌딩용**이라 리서치 데스크엔 안 맞음(Graphify와 같은 결론). 눈에 띄는 둘 = Ponytail(과설계 방지·이미 원칙 보유)·last30days(여론 리서치·보안검토 후). **지금 당장 설치할 슬램덩크는 없음.** 진짜 소득 = "덜어내라·손 가는 것만" 메타교훈을 우리 성장 규율로 재확인한 것. 정훈이 특정 스킬 시범설치 원하면 그때 개별 검토.

## 2026-07-19 — Graphify (코드 지식 그래프 도구) · 정훈 공유(Notion PDF)

**무엇**: 코드의 함수·클래스·호출관계를 tree-sitter AST로 로컬 분석해 지식 그래프
(`graph.json`)로 만들어두는 도구. Claude Code가 파일을 다 훑기 전에 그래프에서 관련
범위부터 좁혀 토큰을 아끼자는 것. `uv tool install graphifyy` → `/graphify .` →
`query`/`path`/`explain`. 관계에 `EXTRACTED/INFERRED/AMBIGUOUS` 신뢰도 태그.
자료 원문 텍스트 = `docs/research/inbox/`(read_doc.py 추출본).

**우리 fit 판정 → [기각(현시점)·재평가 트리거 설정]**

| 항목 | 우리 레포 실측 | Graphify가 빛나는 조건 |
|---|---|---|
| 코드 규모 | .py 23개 / 약 5,000줄, 최대 563줄 | 52파일+ 대형·복잡 호출그래프 |
| 코드 성격 | 대부분 독립 CLI 스크립트(서로 거의 안 부름) | 깊은 호출체인(OOP) |
| 실제 덩치 | .md 111개(리포트 71+docs), CLAUDE.md 34KB | 코드 그래프 |

- Graphify가 없앤다는 "넓은 검색→여러 파일 열기" 낭비가 우리 코드엔 거의 없음(23개 느슨한 스크립트 → Grep/Glob 한 방).
- 우리 진짜 토큰 부담(①34KB CLAUDE.md 상시 로드 ②71개 리포트 ③영상 자막)은 셋 다 Graphify가 못 건드림.
- Graphify PDF **자체가 정직**: "70% 절감 보장은 근거 없다", 6파일 소형≈1배·52파일=71.5배 → 우리는 "≈1배" 구간.
- PM 견제 관점: 좋은 도구지만 우리가 아직 그 도구가 필요한 크기·구조가 아님.

**재평가 트리거**: 스크립트가 **40~50개 넘고 서로 import로 얽히기 시작**하면 그때 값어치 생김 → 재검토.

**그래도 남긴 것(도구는 기각, 아이디어는 채택)**:
1. **"그래프/인덱스 먼저, 원문은 근거 필요할 때만"** 순서 원칙 — 우리는 이미 Grep/Glob + `selfcheck`·`validate`로 유사 실천. 강화 방향으로 계속.
2. **신뢰도 태깅**(EXTRACTED/INFERRED) — 우리 [검증/정정/미확인] 3분류와 같은 철학, 이미 채택 중.
3. **자기 사용량 실측 후 판단** — 도입 전후 토큰 재기. 우리 R1/R2 분리·report_guard와 같은 결.
