// 자동 생성 — build_app_data.py. 직접 수정 금지.
window.APP_DATA = {
  "generated_at": "2026-06-20 08:54 KST",
  "as_of": "KR 6/19 마감 / US 6/18 종가 (6/20 주말·휴장 · 경제사냥꾼 6/20 신규 3편 반영)",
  "source_report": "docs/reports/report_v21_2026-06-20.md (v21)",
  "offline": false,
  "fx": {
    "usdkrw": 1529.89
  },
  "totals": {
    "assets_krw": 8515217,
    "stocks_value_krw": 7890446,
    "cash_krw": 624771,
    "day_change_krw": 66843,
    "day_change_pct": 0.85,
    "total_pnl_krw": 589520,
    "total_pnl_pct": 8.07
  },
  "safety": {
    "pin": 7500,
    "level2": 8000,
    "price": 9052.42,
    "change_pct": -0.13,
    "status": "ok"
  },
  "indices": [
    {
      "label": "코스피",
      "ticker": "^KS11",
      "price": 9052.42,
      "change_pct": -0.13
    },
    {
      "label": "코스닥",
      "ticker": "^KQ11",
      "price": 966.59,
      "change_pct": -6.33
    },
    {
      "label": "S&P500",
      "ticker": "^GSPC",
      "price": 7500.58,
      "change_pct": 1.08
    },
    {
      "label": "나스닥",
      "ticker": "^IXIC",
      "price": 26517.932,
      "change_pct": 1.91
    },
    {
      "label": "다우",
      "ticker": "^DJI",
      "price": 51564.7,
      "change_pct": 0.14
    },
    {
      "label": "필라델피아반도체",
      "ticker": "^SOX",
      "price": 14341.783,
      "change_pct": 6.42
    }
  ],
  "alerts": [
    {
      "id": "코스피 매수 안전핀",
      "ticker": "^KS11",
      "cond": "below",
      "when": null,
      "action": "잔여 트랜치 전면 동결·재평가 (물타기 금지)",
      "price": 9052.42,
      "fired": false
    },
    {
      "id": "코스피 2차 트랜치",
      "ticker": "^KS11",
      "cond": "below",
      "when": null,
      "action": "2차 ~20만 분할 투입 (이란 결렬 동반 시)",
      "price": 9052.42,
      "fired": false
    },
    {
      "id": "NAVER 1차 매수존",
      "ticker": "035420.KS",
      "cond": "between",
      "when": null,
      "action": "1차 트랜치 10~15만",
      "price": 229500.0,
      "fired": true
    },
    {
      "id": "삼성전자 1차 매수존",
      "ticker": "005930.KS",
      "cond": "between",
      "when": null,
      "action": "1차 트랜치 대안",
      "price": 354000.0,
      "fired": false
    },
    {
      "id": "두산에너빌리티 십만빌리티",
      "ticker": "034020.KS",
      "cond": "above",
      "when": null,
      "action": "대미투자 원전 수혜 — 10만 돌파 시 비중 검토",
      "price": 97900.0,
      "fired": false
    },
    {
      "id": "FOMC 3차 트랜치",
      "ticker": "EVENT",
      "cond": "event",
      "when": "2026-06-18 03:00 KST (결과: 🔴 매파 확정)",
      "action": "🔴 매파(점도표 2026 3.4→3.8·2년물+DXY↑) → 3차 전면 보류. 비둘기 전환/META 7/29 실적/외인 복귀 중 하나까지 동결",
      "price": null,
      "fired": null
    },
    {
      "id": "MU 6/24 실적 절반 차익",
      "ticker": "EVENT",
      "cond": "event",
      "when": "2026-06-24 야간 (6/23 저녁 베이킹)",
      "action": "+39% 고평가·컨센 상회기대(sold out)·집중도 완화 → 절반 차익 조건부 예약(폰 미가용 → 6/23 사전 베이킹)",
      "price": null,
      "fired": null
    },
    {
      "id": "이란 MOU 서명",
      "ticker": "EVENT",
      "cond": "event",
      "when": "2026-06-13~14 주말",
      "action": "서명/무산 → 월요일 갭 방향 결정",
      "price": null,
      "fired": null
    },
    {
      "id": "SK하이닉스 미 ADR 정식상장",
      "ticker": "EVENT",
      "cond": "event",
      "when": "2026-08 목표 (SEC 승인 6/22주 가능성)",
      "action": "NYSE/NASDAQ 정식상장 시 → 토스 미장 소수점으로 SK하이닉스 소액 적립 개시 검토. 상장 전엔 OTC HXSCL·국장소수점 비추(저유동성·일괄체결)",
      "price": null,
      "fired": null
    },
    {
      "id": "외국인 수급 연속성",
      "ticker": "SIGNAL",
      "cond": "signal",
      "when": "매 보고서",
      "action": "외인 순매수 연속 일수·누적액 추적(코스피 메인 엔진). ✅순매수 지속=강세 신호+반도체(SK하이닉스 등) 선취 명분↑ / 🔴순매도 재전환=강세 논지 약화 '신중' 경보. 국장 데스크(kr-market-desk)가 '코스피 마감 외국인 기관 [날짜]'로 수집",
      "price": null,
      "fired": null
    }
  ],
  "holdings": [
    {
      "label": "삼성전자",
      "ticker": "005930.KS",
      "region": "kr",
      "currency": "KRW",
      "shares": 2,
      "cost": 263000,
      "price": 354000.0,
      "change_pct": -2.34,
      "value_krw": 708000,
      "pnl_pct": 34.6,
      "pnl_krw": 182000,
      "outlook": "core",
      "stars": 4,
      "target": "480,000~530,000원 (KB 53만·미래 48만)",
      "buy_zone": "295,000~305,000원 (현재가 위 — 눌림 대기)",
      "trim": "보류",
      "comment": "사이클 중반·일반DRAM 판가 +90% 레버리지. HBM4 엔비디아·AMD 인증, 2월 양산.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "경제사냥꾼 주간전망: 다음주(6/22~26)=반도체 호황 진위 '시험 주간'. 코스피 9천=삼성·하이닉스 두 종목 착시(6/18 상승 98 vs 하락 806). 6/25 MU 실적+PCE가 분수령 → 삼성 직결."
        },
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "MU 도이체방크 $1,500 상향·DRAM 부족 2028까지 → 메모리 판 전체 재평가, 삼성 수혜 프레임(노무라 삼성 목표 59만은 단일출처 미확인)."
        },
        {
          "date": "2026-06-19",
          "tag": "검증",
          "text": "삼성그룹 '국민기업' — 시총 57%, 외인 한달 50~57조 순매도 → 개인 40조 매수. 하나證 2Q 92조(가장 공격적 전망)."
        },
        {
          "date": "2026-06-19",
          "tag": "검증",
          "text": "일반DRAM 판가 +90% — 메모리 사이클 중반, 실적 레버리지 본격화."
        },
        {
          "date": "2026-06-16",
          "tag": "검증",
          "text": "HBM4 엔비디아·AMD 인증 → 2026년 2월 양산 일정."
        }
      ]
    },
    {
      "label": "LG전자",
      "ticker": "066570.KS",
      "region": "kr",
      "currency": "KRW",
      "shares": 1,
      "cost": 155200,
      "price": 211500.0,
      "change_pct": -7.44,
      "value_krw": 211500,
      "pnl_pct": 36.28,
      "pnl_krw": 56300,
      "outlook": "core",
      "stars": 4,
      "target": "컨센 초과 (12~23만 이미 상회)",
      "buy_zone": "홀딩 (추가매수 보류)",
      "trim": "손절선 없음 — 펀더 훼손 시에만 매도 검토",
      "comment": "그룹 동반 차익실현·펀더 무손상=홀딩. 냉각 CDU·NVIDIA DSX 동맹. 보유 1주뿐 → 분할 트림 불가.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "당일 −7.44%. LG그룹(LG전자·LG이노텍) 동반 차익실현 — 펀더 무손상, 투매 금지."
        },
        {
          "date": "2026-06-16",
          "tag": "검증",
          "text": "냉각 CDU·NVIDIA DSX 데이터센터 동맹 — AI 전력·냉각 수혜."
        }
      ]
    },
    {
      "label": "두산로보틱스",
      "ticker": "454910.KS",
      "region": "kr",
      "currency": "KRW",
      "shares": 1,
      "cost": 100000,
      "price": 101800.0,
      "change_pct": -0.88,
      "value_krw": 101800,
      "pnl_pct": 1.8,
      "pnl_krw": 1800,
      "outlook": "momentum",
      "stars": 2,
      "target": "분산 큼 (컨센 109k ~ 극단 300k)",
      "buy_zone": "관망",
      "trim": "모멘텀 — 큰 갭업 시 차익",
      "comment": "전일 −15% 모멘텀, 추격금지. 2025 매출 330억(−29.6%)·영업손실 595억(사상최대)·PSR ~219배 = 데이터 취약 테마주.",
      "issues": [
        {
          "date": "2026-06-19",
          "tag": "검증",
          "text": "전일 −15% 변동성 — 코어 아닌 모멘텀, 추격금지."
        },
        {
          "date": "2026-06-15",
          "tag": "검증",
          "text": "2025 매출 330억(−29.6%)·영업손실 595억 사상최대·PSR ~219배 = 펀더 취약."
        }
      ]
    },
    {
      "label": "현대차",
      "ticker": "005380.KS",
      "region": "kr",
      "currency": "KRW",
      "shares": 1,
      "cost": 630000,
      "price": 613000.0,
      "change_pct": 2.0,
      "value_krw": 613000,
      "pnl_pct": -2.7,
      "pnl_krw": -17000,
      "outlook": "hold",
      "stars": 3,
      "target": "600,000원 (공격 800,000원)",
      "buy_zone": "관망",
      "trim": "—",
      "comment": "BD 풋옵션 7/20·삼성 지분설로 반등. 보스턴다이내믹스 휴머노이드(아틀라스 2028). 본업 관세·EV 리스크.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "미확인",
          "text": "삼성 지분 인수설 — 당일 +2.00% 반등 재료(미확인, 교차검증 필요)."
        },
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "보스턴다이내믹스 풋옵션 7/20 일정."
        }
      ]
    },
    {
      "label": "NAVER",
      "ticker": "035420.KS",
      "region": "kr",
      "currency": "KRW",
      "shares": 1,
      "cost": 250500,
      "price": 229500.0,
      "change_pct": -2.34,
      "value_krw": 229500,
      "pnl_pct": -8.38,
      "pnl_krw": -21000,
      "outlook": "trim_candidate",
      "stars": 2,
      "target": "~300,000원 (메리츠 410,000원)",
      "buy_zone": "225,000~235,000원 (진입 🔴 — 발동)",
      "trim": "정리후보",
      "comment": "매수존 진입했으나 정리후보 + 외인 순매도 전환 → 6/22 외인 재유입 확인까지 보류. 집행 시 소액 10만원만.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "229,500원 = 매수존 진입(유일 발동). 단 정리후보 + 외인 순매도 전환 → 6/22 확인 전 보류."
        },
        {
          "date": "2026-06-15",
          "tag": "검증",
          "text": "젠슨황 GAK AI팩토리. 단 6/15 랠리 소외(+0.4%)·플랫폼 신뢰 낮음."
        }
      ]
    },
    {
      "label": "NVDA",
      "ticker": "NVDA",
      "region": "us",
      "currency": "USD",
      "shares": 5.138203,
      "cost": 199.51,
      "price": 210.69,
      "change_pct": 2.95,
      "value_krw": 1656210,
      "pnl_pct": 5.6,
      "pnl_krw": 163118,
      "outlook": "core",
      "stars": 5,
      "target": "$298.93 (+45.7%)",
      "buy_zone": "눌림",
      "trim": "비중관리 (이미 최대 비중)",
      "comment": "Rubin HBM4 3사 인증·테라팹 호재. Q1 +85%, Rubin 2배. 이미 최대 비중 → 신규추가 절제.",
      "issues": [
        {
          "date": "2026-06-19",
          "tag": "검증",
          "text": "Rubin HBM4 3사(삼성·하이닉스·MU) 인증·테라팹 딜 호재."
        },
        {
          "date": "2026-06-19",
          "tag": "골격검증",
          "text": "Intel+Apple 테라팹 딜 — NVDA 호재(삼성 파운드리엔 양날)."
        }
      ]
    },
    {
      "label": "META",
      "ticker": "META",
      "region": "us",
      "currency": "USD",
      "shares": 1.129111,
      "cost": 633.98,
      "price": 577.22,
      "change_pct": 1.7,
      "value_krw": 997099,
      "pnl_pct": -8.95,
      "pnl_krw": -45513,
      "outlook": "core",
      "stars": 4,
      "target": "$827.32 (+45.9%)",
      "buy_zone": "실적확인 (7/29 전 보류)",
      "trim": "—",
      "comment": "고유악재 회복(노이즈). 괴리 최대+낙폭 깊음(저가 매력)+구독 수익화. 6/18 FOMC 매파로 3차 트랜치 동결.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "고유 악재 노이즈 회복세(+1.70%). 7/29 실적 전 신규진입 보류."
        },
        {
          "date": "2026-06-18",
          "tag": "검증",
          "text": "FOMC 매파 확정 → 3차 트랜치(META·AVGO) 동결 유지."
        }
      ]
    },
    {
      "label": "VOO",
      "ticker": "VOO",
      "region": "us",
      "currency": "USD",
      "shares": 0.970784,
      "cost": 645.4,
      "price": 688.11,
      "change_pct": 0.98,
      "value_krw": 1021976,
      "pnl_pct": 6.62,
      "pnl_krw": 109415,
      "outlook": "core",
      "stars": 4,
      "target": "— (ETF)",
      "buy_zone": "적립",
      "trim": "—",
      "comment": "S&P500 분산형 코어 적립.",
      "issues": [
        {
          "date": "2026-06-15",
          "tag": "검증",
          "text": "S&P 코어 적립 — 분산 효과."
        }
      ]
    },
    {
      "label": "MSFT",
      "ticker": "MSFT",
      "region": "us",
      "currency": "USD",
      "shares": 1.443,
      "cost": 410.2,
      "price": 379.4,
      "change_pct": 0.13,
      "value_krw": 837575,
      "pnl_pct": -7.51,
      "pnl_krw": -24554,
      "outlook": "core",
      "stars": 4,
      "target": "$561.39 (+43.7%)",
      "buy_zone": "눌림",
      "trim": "—",
      "comment": "상방 최대(+48%), 6/18 소외. Azure +40%, AI 런레이트 $37B, 안정 컴파운더.",
      "issues": [
        {
          "date": "2026-06-15",
          "tag": "검증",
          "text": "Azure +40%·AI 런레이트 $37B — 안정 컴파운더, 상방 여력 큼."
        }
      ]
    },
    {
      "label": "AAPL",
      "ticker": "AAPL",
      "region": "us",
      "currency": "USD",
      "shares": 2.022472,
      "cost": 257.14,
      "price": 298.01,
      "change_pct": 0.7,
      "value_krw": 922091,
      "pnl_pct": 15.89,
      "pnl_krw": 164625,
      "outlook": "hold",
      "stars": 3,
      "target": "$312.72 (+7.4%)",
      "buy_zone": "목표근접",
      "trim": "트림 1순위 후보",
      "comment": "금리방어·인텔딜 협력 당사자라 관망. 목표 근접. WWDC Siri=Gemini 구동(자체 LLM 한계)·중국 리스크.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "트림 1순위 후보 — 목표 근접·금리방어. 단 인텔딜 협력 당사자라 관망."
        },
        {
          "date": "2026-06-15",
          "tag": "검증",
          "text": "WWDC Siri=Gemini 구동(자체 LLM 한계)·중국 리스크."
        }
      ]
    },
    {
      "label": "GOOGL",
      "ticker": "GOOGL",
      "region": "us",
      "currency": "USD",
      "shares": 0.438006,
      "cost": 387.73,
      "price": 368.03,
      "change_pct": 1.17,
      "value_krw": 246617,
      "pnl_pct": -5.08,
      "pnl_krw": -737,
      "outlook": "core",
      "stars": 4,
      "target": "$432.83 (+20.3%)",
      "buy_zone": "눌림",
      "trim": "—",
      "comment": "Cloud·Gemini, 반독점 노이즈. Cloud +63%·백로그 $460B.",
      "issues": [
        {
          "date": "2026-06-15",
          "tag": "검증",
          "text": "Cloud +63%·백로그 $460B. 반독점 노이즈는 리스크."
        }
      ]
    },
    {
      "label": "TSLA",
      "ticker": "TSLA",
      "region": "us",
      "currency": "USD",
      "shares": 0.157708,
      "cost": 422.51,
      "price": 400.49,
      "change_pct": 1.04,
      "value_krw": 96629,
      "pnl_pct": -5.21,
      "pnl_krw": -423,
      "outlook": "hold",
      "stars": 3,
      "target": "$420.55 (ARK 2029 $2,600)",
      "buy_zone": "관망",
      "trim": "—",
      "comment": "캐시우드 강세론 but 우드 본인 차익매도 중. Optimus 7~8월 생산. 목표 거의 도달.",
      "issues": [
        {
          "date": "2026-06-19",
          "tag": "검증·시점",
          "text": "캐시우드 TSLA 2029 $2,600 목표 — 단 우드 본인은 TSLA 차익매도 중(영상 미언급)."
        }
      ]
    },
    {
      "label": "ORCL",
      "ticker": "ORCL",
      "region": "us",
      "currency": "USD",
      "shares": 0.21519,
      "cost": 232.12,
      "price": 184.29,
      "change_pct": 0.41,
      "value_krw": 60671,
      "pnl_pct": -20.61,
      "pnl_krw": -12081,
      "outlook": "hold",
      "stars": 3,
      "target": "$252.64 (+38.7%)",
      "buy_zone": "눌림",
      "trim": "패닉셀 금지",
      "comment": "RPO $638B 백로그, OpenAI 54% 집중. 최대 평가손(−20.6%) → 신규매수 보류·패닉셀 금지.",
      "issues": [
        {
          "date": "2026-06-15",
          "tag": "검증",
          "text": "RPO $638B but OpenAI 54% 집중·희석 우려 → 최대 손실, 신규매수 보류."
        }
      ]
    },
    {
      "label": "ANET",
      "ticker": "ANET",
      "region": "us",
      "currency": "USD",
      "shares": 0.283501,
      "cost": 162.07,
      "price": 169.67,
      "change_pct": 2.87,
      "value_krw": 73590,
      "pnl_pct": 4.69,
      "pnl_krw": 6668,
      "outlook": "core",
      "stars": 4,
      "target": "$189.13 (+15.9%)",
      "buy_zone": "홀딩",
      "trim": "—",
      "comment": "AI 네트워크 fabric, 목표 상향. AI fabric $3.5B 상향.",
      "issues": [
        {
          "date": "2026-06-15",
          "tag": "검증",
          "text": "AI fabric 매출 $3.5B 상향 — AI 네트워크 수혜."
        }
      ]
    },
    {
      "label": "MU",
      "ticker": "MU",
      "region": "us",
      "currency": "USD",
      "shares": 0.04,
      "cost": 749.0,
      "price": 1133.99,
      "change_pct": 8.7,
      "value_krw": 69395,
      "pnl_pct": 51.4,
      "pnl_krw": 25758,
      "outlook": "core",
      "stars": 4,
      "target": "$1,200~1,500 (도이체방크 $1,500·씨티 $1,200, 6/17 상향)",
      "buy_zone": "6/25 실적(목 새벽)",
      "trim": "절반 차익 (6/23 베이킹)",
      "comment": "+51.4% 평가익. 도이체방크 $1,500(+50%)·씨티 $1,200·TD코웬 $1,500. 6/25(목) 새벽 실적=한국 메모리 풍향계(매출보다 총이익률·장기계약 가시성). 6/23 저녁 폰창에서 절반(0.02주) 시장가 매도 베이킹 OR 전량 홀딩 택1.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "도이체방크 목표 $1,000→$1,500(+50%, 6/17 BUY)·씨티 $840→$1,200·TD코웬 $1,500. DRAM 부족 2028까지(DB)."
        },
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "경제사냥꾼: 6/25(목) 새벽 MU 실적 = 한국 메모리 풍향계. 매출보다 ①총이익률 81% 유지 ②장기계약·선급금 가시성을 봐라(진짜수요 vs 사재기). 옵션시장 ±17% 베팅·저점比 10배+ → 미스 시 급락 리스크."
        },
        {
          "date": "2026-06-19",
          "tag": "검증",
          "text": "경제사냥꾼 7편 공통: '6/24 MU 실적 = AI수요 말잔치냐 실제 현금이냐 분수령'."
        }
      ]
    },
    {
      "label": "AVGO",
      "ticker": "AVGO",
      "region": "us",
      "currency": "USD",
      "shares": 0.071177,
      "cost": 421.06,
      "price": 411.35,
      "change_pct": 4.7,
      "value_krw": 44793,
      "pnl_pct": -2.31,
      "pnl_krw": 1142,
      "outlook": "hold",
      "stars": 3,
      "target": "$522.06 (+36.6%)",
      "buy_zone": "조정주",
      "trim": "물타기 후보",
      "comment": "ASIC, 평단(421) 근접 물타기 후보. AI매출 Q3 +200%+. 6/18 FOMC 매파로 3차 동결.",
      "issues": [
        {
          "date": "2026-06-15",
          "tag": "검증",
          "text": "AI 매출 Q3 +200%+. 평단 아래 = 물타기 효과. 단 3차 트랜치 FOMC로 동결."
        }
      ]
    }
  ],
  "watchlist": [
    {
      "label": "SK하이닉스",
      "ticker": "000660.KS",
      "currency": "KRW",
      "price": 2764000.0,
      "change_pct": 2.94,
      "stars": 4,
      "target": "Strong Buy",
      "comment": "🔥 ADR SEC 승인 6/22주·8월 거래·조달 $14B·HBM 57%·27년 PER 6.9배. 상장 시 토스 미장소수점 적립 검토. 단 메모리 베팅 중복.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "경제사냥꾼: 6/22주 美 SEC 승인 여부 = '한국 자산 제값 찾기(코리아 디스카운트 해소)' 신호탄. HBM 엔비디아 발주 2/3 점유. ⚠️1Q 영업이익률 72%·노무라 목표 400만은 단일출처 미확인."
        },
        {
          "date": "2026-06-19",
          "tag": "검증",
          "text": "ADR: 밤사이 나스닥 가격선결정 → 코스피 변동성 수입. SEC 승인 6/22주 가능성."
        },
        {
          "date": "2026-06-19",
          "tag": "검증",
          "text": "ARM PER 500배 vs 하이닉스 6~7배 = '가장 싼 AI 길목주' 부각."
        }
      ]
    },
    {
      "label": "삼성전기",
      "ticker": "009150.KS",
      "currency": "KRW",
      "price": 2270000.0,
      "change_pct": 3.18,
      "stars": 3,
      "target": "KB 3,000,000원 (220만→상향)",
      "comment": "🔥 MLCC·기판 초호황 + 중일 희토류 반사이익. PER 180배 — 눌림 관찰, 추격금지.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "당일 +3.18%. MLCC·기판 초호황, KB 목표 300만 상향."
        }
      ]
    },
    {
      "label": "GE Vernova",
      "ticker": "GEV",
      "currency": "USD",
      "price": 1109.73,
      "change_pct": 5.8,
      "stars": 4,
      "target": "$1,211.72 (Bernstein $1,206)",
      "comment": "워치 유일 매수검토(소액·갭 소화 후). 1Q 수주 +71%·백로그 $163B. AI전력 '미국판 두산E'.",
      "issues": [
        {
          "date": "2026-06-18",
          "tag": "검증",
          "text": "Bernstein 매수개시 목표 $1,206·1Q 수주 +71%·백로그 $163B."
        }
      ]
    },
    {
      "label": "두산에너빌리티",
      "ticker": "034020.KS",
      "currency": "KRW",
      "price": 97900.0,
      "change_pct": -1.71,
      "stars": 3,
      "target": "135,000~165,000원",
      "comment": "10만 하회, 추격금지. SMR 진짜 수혜(가스터빈·원전). 10만 재돌파 트리거.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "97,900원 — 10만 하회. 추격금지, 10만 재돌파 트리거 대기."
        }
      ]
    },
    {
      "label": "LG이노텍",
      "ticker": "011070.KS",
      "currency": "KRW",
      "price": 1145000.0,
      "change_pct": -10.76,
      "stars": 3,
      "target": "KB 1,600,000원",
      "comment": "FC-BGA(AI 기판) 구조적 공급부족·美 4개+ 고객 증설 요청. 그룹 동반 급락이나 성장성 긍정.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "당일 −10.76% — LG그룹 동반 급락. 펀더 무손상, 성장성 긍정."
        },
        {
          "date": "2026-06-16",
          "tag": "검증",
          "text": "FC-BGA 2Q 영익 컨센 1,787억(+15.7배) — 구조적 공급부족."
        }
      ]
    },
    {
      "label": "한화오션",
      "ticker": "042660.KS",
      "currency": "KRW",
      "price": 128400.0,
      "change_pct": 2.64,
      "stars": 3,
      "target": "—",
      "comment": "조선 슈퍼사이클(채널). 공시 확인 전 추격위험. 대미투자 조선.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "미확인",
          "text": "조선 슈퍼사이클 채널 언급 — 공시 확인 전 추격 위험."
        }
      ]
    },
    {
      "label": "SpaceX",
      "ticker": "SPCX",
      "currency": "USD",
      "price": 185.0,
      "change_pct": -3.56,
      "stars": 3,
      "target": "$63~$190 (분산)",
      "comment": "6/26 MSCI 편입 vs 8월 첫 20% 락업 언락. 추격금지.",
      "issues": [
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "6/26 MSCI 편입 메커닉 vs 8월 첫 20% 락업 언락 — 변동성 주의."
        }
      ]
    }
  ],
  "tranches": [
    {
      "id": "1차",
      "amount_krw": 125000,
      "executed": false,
      "trigger": "NAVER 225~235k 또는 삼성 295~305k 눌림"
    },
    {
      "id": "2차",
      "amount_krw": 200000,
      "executed": false,
      "trigger": "이란 결렬 + 코스피 8,000 하회"
    },
    {
      "id": "3차",
      "amount_krw": 225000,
      "executed": false,
      "trigger": "🔴 FOMC 6/18 매파 확정으로 전면 보류. 재개 조건 = 비둘기 전환 / META 7/29 실적 확인 / 외인 순매수 복귀 중 하나"
    }
  ],
  "fx_history": {
    "dates": [
      "2026-05-18",
      "2026-05-19",
      "2026-05-20",
      "2026-05-21",
      "2026-05-24",
      "2026-05-25",
      "2026-05-26",
      "2026-05-27",
      "2026-05-28",
      "2026-05-31",
      "2026-06-01",
      "2026-06-02",
      "2026-06-03",
      "2026-06-04",
      "2026-06-07",
      "2026-06-08",
      "2026-06-09",
      "2026-06-10",
      "2026-06-11",
      "2026-06-14",
      "2026-06-15",
      "2026-06-16",
      "2026-06-17",
      "2026-06-18",
      "2026-06-19"
    ],
    "closes": [
      1492.32,
      1507.85,
      1499.77,
      1504.4,
      1512.83,
      1514.79,
      1505.44,
      1503.11,
      1495.29,
      1506.84,
      1511.27,
      1516.6,
      1530.11,
      1533.07,
      1554.48,
      1528.88,
      1525.81,
      1525.05,
      1517.38,
      1509.5,
      1513.31,
      1510.96,
      1525.42,
      1537.56,
      1529.89
    ]
  },
  "kospi_history": {
    "dates": [
      "2026-05-19",
      "2026-05-20",
      "2026-05-21",
      "2026-05-22",
      "2026-05-26",
      "2026-05-27",
      "2026-05-28",
      "2026-05-29",
      "2026-06-01",
      "2026-06-02",
      "2026-06-04",
      "2026-06-05",
      "2026-06-08",
      "2026-06-09",
      "2026-06-10",
      "2026-06-11",
      "2026-06-12",
      "2026-06-15",
      "2026-06-16",
      "2026-06-17",
      "2026-06-18",
      "2026-06-19"
    ],
    "closes": [
      7271.66,
      7208.95,
      7815.59,
      7847.71,
      8047.51,
      8228.7,
      8185.29,
      8476.15,
      8788.38,
      8801.49,
      8639.41,
      8160.59,
      7484.41,
      8096.93,
      7730.82,
      7763.95,
      8123.62,
      8545.98,
      8726.6,
      8864.24,
      9063.84,
      9052.42
    ]
  },
  "hunter": {
    "_comment": "경제사냥꾼 분석 앱 정본. 보고서마다 research-feed/PM이 docs/research/hunter_log.md 갱신 시 여기 latest_videos(최신순 prepend)·track_record(최신 prepend)·themes도 함께 갱신 후 build_app_data.py 재실행.",
    "updated": "2026-06-20",
    "source": "docs/research/hunter_log.md",
    "channel_note": "테마·방향성은 빠르고 유용(로봇·AI전력·종전 등 선제 포착). 단 구체 수치는 자막오류·과장 잦음 → 방향성은 채택하되 숫자는 교차검증. 트랙레코드 개선세.",
    "headline": "다음주(6/22~26) = 반도체 호황 진위 '시험 주간'. 분수령 6/25 새벽 MU 실적 + 밤 美 PCE. MU 도이체방크 $1,500 상향(검증)·6/24 절반차익 트리거와 정합",
    "latest_videos": [
      {
        "date": "2026-06-20",
        "title": "코스피 9,000시대 '다음주' 투자 포인트 (주간전망)",
        "tag": "검증",
        "tickers": [
          "005930.KS",
          "000660.KS",
          "MU",
          "^KS11"
        ],
        "summary": "코스피 9,300 돌파했지만 6/18 9천 첫날 상승 98개·하락 806개 = 반도체(삼성·하이닉스) 두 종목 착시. 다음주 캘린더: 6/22 SK하이닉스 美 SEC 승인 가능성 / 6/23 글로벌PMI·MSCI검토 / 6/25(목)=분수령: 새벽 MU 실적(매출보다 총이익률·장기계약 가시성)+밤 美 PCE / 6/26 미시간·러셀. 체크3=MU장기계약·PCE·하이닉스美상장. '완판보다 진짜수요 vs 사재기 봐라'=추격금지 정합."
      },
      {
        "date": "2026-06-20",
        "title": "목표가 $1,500 제2의 엔비디아 = 마이크론",
        "tag": "검증",
        "tickers": [
          "MU",
          "005930.KS",
          "000660.KS"
        ],
        "summary": "도이체방크 MU $1,000→$1,500(+50%, 6/17 BUY)·씨티 $840→$1,200·TD코웬 $1,500(전부 검증). 직전분기 매출 $238억(예상 $200억)·EPS +30%상회. DRAM 품귀 2028까지(DB). MU=메모리 3등, HBM 엔비디아 발주 2/3 SK하이닉스 → '3등 $1,500 만든 급등기가 1·2등엔 더 세게'. 옵션시장 실적주 ±17% 베팅, 저점比 10배+ 미스 시 급락 리스크. 6/24 MU=한국 메모리 풍향계."
      },
      {
        "date": "2026-06-20",
        "title": "정부 밀어줄 고배당주 = 삼성물산",
        "tag": "미확인",
        "tickers": [
          "005930.KS"
        ],
        "summary": "정부 고배당 분리과세 정책→배당확대 기업 자금몰림. 삼성물산=삼성전자·삼성생명 지분 '현금통로'. DS투자증권 올해 DPS +720% 23,500원·내년 4만원대(단일출처 미확인). SMR(에스토니아)·삼성 평택 하이테크 수주 엮임. 삼성물산 미보유 — 정책 테마 참고만."
      },
      {
        "date": "2026-06-19",
        "title": "젠슨황 61조 들고도 못 산 반도체 독점기업 (ARM)",
        "tag": "검증",
        "tickers": [
          "MU",
          "000660.KS"
        ],
        "summary": "SoftBank ARM 담보 레버리지 플라이휠(~$185억→OpenAI $300억→스타게이트 $5,000억). 손정의 NVDA 전량매도. ARM PER 500배 vs 하이닉스 6~7배·MU 10배 = MU·하이닉스 '가장 싼 AI 길목주'."
      },
      {
        "date": "2026-06-19",
        "title": "삼성그룹이 국민기업인 진짜 이유 ★국장",
        "tag": "검증",
        "tickers": [
          "005930.KS"
        ],
        "summary": "삼성+하이닉스 시총 54%(우선주 57%). 외인 한달 50~57조 순매도→개인 40조 흡수. 진짜 돈=일반 DRAM 판가 +90%(트렌드포스). 하나證 삼성 2Q 92조(가장 공격적). 2028 증설→공급과잉 경고."
      },
      {
        "date": "2026-06-19",
        "title": "SK하이닉스 美상장 영향 ★워치",
        "tag": "검증",
        "tickers": [
          "000660.KS"
        ],
        "summary": "ADR SEC 승인 6/22주·8월 거래·조달 최대 $14B·HBM 57%·27년 PER ~6.9배. 밤사이 나스닥서 가격 선결정→코스피 변동성 수입 = 보유 삼성·NVDA·MU 동조성 심화."
      },
      {
        "date": "2026-06-19",
        "title": "테슬라 6배 갈 수 있다 (캐시우드)",
        "tag": "검증·시점",
        "tickers": [
          "TSLA"
        ],
        "summary": "ARK 2029 목표 $2,600·로보택시가 가치 90%. 머스크 의결권 ~19.9%. 단 우드 본인 최근 TSLA 일부 차익매도 중인 점 영상 미언급."
      },
      {
        "date": "2026-06-19",
        "title": "G7 정상회의 → 한국 반도체 호재",
        "tag": "검증",
        "tickers": [
          "005930.KS",
          "NVDA",
          "000660.KS"
        ],
        "summary": "G7서 美 앤스로픽 AI모델 수출통제(첫 AI모델 금수). '믿을 나라끼리' 반도체 동맹→HBM 독점 한국 몸값↑. 양날=對중국 시장 포기 부담."
      }
    ],
    "track_record": [
      {
        "date": "6/20",
        "claim": "MU 도이체방크 목표 $1,000→$1,500(+50%)·씨티 $1,200",
        "actual": "일치 — DB 6/17 Weathers BUY·TD코웬 $1,500, DRAM 부족 2028+ (Investing/SeekingAlpha)",
        "verdict": "검증"
      },
      {
        "date": "6/20",
        "claim": "구글+블랙스톤 $250억(35조) AI 인프라 합작",
        "actual": "일치 — 5/19 발표, BS $5B 지분·레버리지 $25B·TPU. 단 신규 아닌 5월 뉴스",
        "verdict": "검증·시점"
      },
      {
        "date": "6/20",
        "claim": "SK하이닉스 1Q 영업이익률 72%·노무라 코스피 1.1만",
        "actual": "영업이익률 72% 비현실적 과장 의심·노무라 단일출처 → 교차검증 필요",
        "verdict": "미확인"
      },
      {
        "date": "6/19",
        "claim": "G7서 美 앤스로픽 AI모델 수출통제(첫 AI모델 금수)",
        "actual": "일치 (Al Jazeera 6/19)",
        "verdict": "검증"
      },
      {
        "date": "6/19",
        "claim": "SK하이닉스 ADR SEC 승인 6/22주·8월 상장·HBM 57%",
        "actual": "일치 (Reuters/CNBC, 조달 최대 $14B)",
        "verdict": "검증"
      },
      {
        "date": "6/19",
        "claim": "손정의 NVDA 지분 전량 매도",
        "actual": "일치 (Reuters)",
        "verdict": "검증"
      },
      {
        "date": "6/18",
        "claim": "FOMC 동결·점도표 3.4→3.8·워시 dot 미기재",
        "actual": "일치 (CNBC/NPR), v17 예고 적중",
        "verdict": "검증(우수)"
      },
      {
        "date": "6/17",
        "claim": "SK하이닉스 영업이익 '100조'",
        "actual": "실제 컨센 약 250조(순현금 100조와 혼동)",
        "verdict": "정정"
      },
      {
        "date": "6/17",
        "claim": "SMR 진짜수혜 '두산로보틸리티'",
        "actual": "실제 두산에너빌리티 — 자막 고유명사 오류",
        "verdict": "정정"
      },
      {
        "date": "6/15",
        "claim": "골드만 코스피 목표 12,000",
        "actual": "실제 골드만 9,000(시티 8,500)",
        "verdict": "자막오류"
      }
    ],
    "themes": [
      "다음주(6/22~26) = 반도체 호황 진위 시험 주간 (MU 6/25·PCE·하이닉스 美상장)",
      "메모리 슈퍼사이클 = DRAM 부족 2028까지, MU $1,500이 삼성·하이닉스로 흐름",
      "코스피 9천 = 반도체 두 종목 착시, 쏠림·과속 리스크 (추격·레버리지 금지)",
      "코리아 디스카운트 해소 = 하이닉스 美 ADR·MSCI·정부 배당정책",
      "로봇/피지컬AI·AI전력·SMR (현대차·두산로보·두산E·GEV)"
    ]
  },
  "flows": {
    "_comment": "코스피 투자자별 순매수(억원). 보고서에 문서화된 확정값만 시드. 보고서마다 kr-market-desk가 당일 외인/기관/개인 확정 시 series에 prepend(최신은 뒤). 추측 금지 — 미확인 일자는 null.",
    "updated": "2026-06-19",
    "unit": "억원",
    "market": "코스피",
    "series": [
      {
        "date": "2026-06-12",
        "foreign": 21400,
        "inst": 23200,
        "indiv": -56000,
        "note": "외인 25거래일만 순매수 전환, 코스피 8,123.62(+4.63%)"
      },
      {
        "date": "2026-06-15",
        "foreign": 10300,
        "inst": 5145,
        "indiv": -14800,
        "note": "2거래일 연속 순매수"
      },
      {
        "date": "2026-06-16",
        "foreign": 15400,
        "inst": 8500,
        "indiv": -23300,
        "note": "3거래일 연속 순매수, 반도체 대형주 재매수"
      },
      {
        "date": "2026-06-17",
        "foreign": -9997,
        "inst": 5818,
        "indiv": 5394,
        "note": "외인 순매도 전환(1일), 기관·개인이 신고가 떠받침"
      },
      {
        "date": "2026-06-18",
        "foreign": 12800,
        "inst": null,
        "indiv": null,
        "note": "외인 +1.28조 순매수 복귀(기관·개인 확정값 미확보)"
      },
      {
        "date": "2026-06-19",
        "foreign": -3800,
        "inst": -12300,
        "indiv": 16500,
        "note": "외인 순매도 전환(FTSE 리밸런싱), 개인 +1.65조 흡수. 6/22 재유입이 분수령"
      }
    ]
  }
};
