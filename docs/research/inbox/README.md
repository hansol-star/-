# 📥 자료 인박스 (incoming materials)

정훈이 주는 **PDF·리서치 리포트·문서**를 텍스트로 뽑아 임시 보관하는 곳.

## 쓰는 법
```bash
# 업로드/외부 PDF → 텍스트 추출 후 여기 저장
python3 .claude/skills/portfolio-desk/scripts/read_doc.py <파일.pdf> --save
```
- `read_doc.py`가 poppler 없이 텍스트 레이어를 직접 추출(웹 컨테이너 대응·자기치유).
- 스캔본(이미지 PDF)은 텍스트가 없으니 Read 툴 시각인식으로.

## 원칙
- 여기 파일은 **작업용 임시 텍스트** — 원자료 백업이 아니다.
- 자료에서 **배운 것·판단**은 성격에 맞는 정본에 옮긴다:
  - 도구·세팅 평가 → `docs/research/tooling_log.md`
  - 영상·전문가 콘텐츠 → `docs/research/study_log.md`
  - 종목 리서치 수치 → 해당 보고서·`stocks.json`
- 민감자료(계좌 전체·개인키)는 넣지 말 것(`.gitignore` 확인).
