# 🧰 도구·세팅 평가 로그 (dev tooling evaluations)

> 정훈이 공유하거나 우리가 발견한 **외부 도구·세팅·방법론**을 우리 데스크에 맞는지 평가한 기록.
> 최신이 맨 위(prepend). 각 항목 = 무엇 · 우리 fit · **[채택/기각/보류]** · 근거.
> 영상·전문가 콘텐츠 = `study_log.md` / 경제사냥꾼 = `hunter_log.md`. 여기는 **도구/세팅** 전용.
> 목적: "제자리 안 머물고 계속 나아지되, 안 맞는 도구는 짐" — 성장의 기록이자 재평가 트리거.

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
