# 🛠️ 데스크 개발 워크플로 (dev 품질 게이트)

> 코드/시스템 작업(스크립트·에이전트·플레이북·정본 문서 변경)의 **상시 절차**.
> 투자 보고서 파이프라인은 `portfolio-desk` 스킬, 세션 간 인수인계는 `dev_handoff.md`.
> 목적 = "빌더 자가채점 대신 기계 게이트" — '다 됐다' 선언 전 답안지를 돌린다.

## 왜 필요한가

스크립트 23개 + 정본 JSON/문서인데, 정본 스크립트(`validate_report`·`build_app_data`·
`market_data`…)를 수정하다 **문법·임포트 하나 깨지면 다음 루틴이 조용히 정본 데이터를 망친다.**
루틴은 무인이라 사람이 못 잡는다 → 커밋·머지 전에 기계가 잡아야 한다.

## 1) 커밋·머지 전 필수 — selfcheck 게이트

```bash
python3 .claude/skills/portfolio-desk/scripts/selfcheck.py
```

- **compile**: 모든 스크립트 py_compile (문법·들여쓰기)
- **import**: 각 스크립트 서브프로세스 임포트 — 모듈 최상위 실행 오류(임포트·NameError) 적발.
  스크립트 자기 폴더를 sys.path에 넣어 `import market_data` 같은 형제 임포트를 정확히 재현(오탐 없음).
- **--help** [8/2 신설]: 각 스크립트를 `--help`로 실제 실행해 **argparse 파서 구성**을 검증.
  compile·import는 `if __name__ == "__main__":` **안쪽을 절대 실행하지 않는다** — 그래서 파서를
  만들 때만 터지는 결함이 두 단계를 다 통과했다. 실제로 `dart_disclosure`·`history_analysis`·
  `naver_sentiment` 3개가 help 문자열의 미이스케이프 `%` 때문에 `--help`에서 죽는 채로
  게이트를 통과하고 있었다(8/2 오디텍 조사 중 발견). argparse 미사용 스크립트는 자동 제외.
  ⚠️ **help 문자열에 리터럴 `%`를 쓸 땐 반드시 `%%`** (`5%%` · `%%ile` · `절대%%`).
- **validate**: `validate_report.py`(보고서 풀표·별점/스코어 밴드·정본 버전 stale) 실행.
- **종료코드 0 = GATE PASS** 여야 커밋·머지. `--json`(파이프라인)·`--no-validate`(코드만 빠르게)·
  `--no-cli`(--help 단계 생략) 지원.

## 2) 로직 변경이면 추가로 — /code-review · /verify

selfcheck는 "깨졌나"(문법·임포트·정본 규칙)를 본다. **동작이 맞나**는 별개다.

- **로직·계산·데이터 파싱을 바꿨으면** `/code-review`(정확성 버그 헌팅) 한 번.
- **런타임 동작을 바꿨으면**(새 CLI 플래그·출력 포맷·API 경로) `/verify` 또는 직접 실행해 눈으로 확인.
  - 예: `market_data.py --group holdings`가 실제 시세를 뽑는지, `event_calendar.py`가 D-day를 맞게 정렬하는지.
- 테스트만 고쳤거나 문서만 바꿨으면 이 단계 생략 가능.

## 3) 연속성 — main ff 머지 (CLAUDE.md 표준 절차)

dev 작업도 정훈 상시 승인분(7/19) — 완료 시 자동 반영. feature 브랜치에만 두면 다음 세션(main 클론)이 못 본다.

```bash
git add -A && git commit -m "..."
git fetch origin main
git merge-base --is-ancestor origin/main HEAD   # ff 가능 확인
git push origin HEAD:main HEAD:claude/<작업브랜치>
```

로컬 `main` 브랜치는 건드리지 않는다(체크아웃 금지). ff 불가면 `git rebase origin/main` 후 재시도.

## 체크리스트 (완료 선언 전)

- [ ] `selfcheck.py` → **GATE PASS**
- [ ] 로직 변경 시 `/code-review` 통과 / 동작 변경 시 실행 확인
- [ ] 새 스크립트면 docstring(용도·사용법·데이터소스)·stdlib 우선(포터블)
- [ ] 정본 변경(보유·룰·워치·스키마)이면 `docs/master.md`·관련 정본도 갱신
- [ ] `dev_handoff.md`에 완료 항목 append (다음 세션 인수인계)
- [ ] main ff 머지·푸시
