# Market Chart — 한국어 수급·시세 그래프 생성기

정훈에게 보여줄 **수급/시세 그래프를 한국어 라벨로** 깔끔하게 만든다.
숫자만 나열하지 말고 "표나 그래프로 보여줘"라는 요청, 외국인/기관 일별 순매수·순매도 추이,
지수 흐름, 종목 비교 등을 **시각화**할 때 사용. (투자 자문 아님 — 분석 참고.)

## 언제 쓰나
- "외인 며칠 매수 며칠 매도인지 그래프로", "수급 추이 그려줘", "코스피 흐름 차트로", "표나 그래프로" 등.
- 일일 보고서(portfolio-desk)에서 수급 반전·지수 돌파 등 **시각적 강조가 필요한 국면**.

## 핵심: 한글 폰트 (깨짐 방지)
- 컨테이너에 NanumGothic이 없으면 먼저 설치:
  ```bash
  apt-get install -y fonts-nanum 2>/dev/null || \
  curl -sL -o /usr/share/fonts/truetype/nanum/NanumGothic.ttf \
    https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf
  fc-cache -f
  ```
- `flow_chart.py`의 `set_korean_font()`가 NanumGothic→BarunGothic→Noto 순으로 자동 등록.
- ⚠️ **유니코드 마이너스(− U+2212)는 NanumGothic에 없다 → 반드시 ASCII 하이픈(-) 사용.**
  `axes.unicode_minus=False`로 축 눈금은 처리되나, 라벨/주석 문자열엔 직접 `-`를 쓸 것.
- matplotlib 미설치 시: `pip install matplotlib`.

## 스크립트
```bash
# 기본(내장 2026-06 외인 코스피 시리즈) → docs/research/foreign_flow_2026-06.png
python3 .claude/skills/market-chart/scripts/flow_chart.py

# 데이터 주입 + 출력경로 지정
python3 .claude/skills/market-chart/scripts/flow_chart.py mydata.json docs/research/out.png
```

### flow_chart.py — 일별 순매수/순매도 + 지수 콤보차트
- 막대: 종가 기준 순매수(초록)/순매도(빨강), 값 라벨(`+1.53조`).
- **장중 vs 종가 반전**: `intraday_flow` 주면 빗금 막대 + 화살표 주석(예: 6/18 장중 매도→종가 매수).
- 보조축: 지수(코스피 등) 종가 라인.
- JSON 스키마: `title·subtitle·y_label·index_label·footnote·rows[{date, close_flow, index, intraday_flow}]`.
  (date는 `"6/18\n(목)"`처럼 줄바꿈 허용. 단위 조원 기준.)

## 데이터 수집 원칙 (차트 신뢰도)
- 수급 수치는 **종가 확정치**를 KRX/언론 **복수 출처 교차검증** 후 입력. 장중치와 종가가 갈리면 둘 다 표기.
- 외인 = 코스피 메인 엔진(핵심 신호). 일별 순매수/매도 연속일수·누적액을 정확히.
- 불확실하면 라벨에 "약/추정" 명시(예: 6/15 약+1.1조).

## 산출물
- PNG를 `docs/research/`에 저장 → 보고서에 첨부하거나 SendUserFile로 정훈에게 전송.
- 차트 생성·갱신 시 git 커밋(연속성). 데이터 출처를 footnote에 남길 것.
