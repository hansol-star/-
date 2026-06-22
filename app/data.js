// 자동 생성 — build_app_data.py. 직접 수정 금지.
window.APP_DATA = {
  "generated_at": "2026-06-22 08:45 KST",
  "as_of": "KR 6/22 종가 확정 / US 6/18 종가 (오늘밤 22:30 재개=선물 하락출발 · v25 부록 집행 지시서)",
  "source_report": "docs/reports/report_v25b_2026-06-22_exec.md (v25 부록)",
  "offline": false,
  "fx": {
    "usdkrw": 1539.71
  },
  "totals": {
    "assets_krw": 8528001,
    "stocks_value_krw": 7903230,
    "cash_krw": 624771,
    "day_change_krw": 69954,
    "day_change_pct": 0.89,
    "total_pnl_krw": 602303,
    "total_pnl_pct": 8.25
  },
  "safety": {
    "pin": 7500,
    "level2": 8000,
    "price": 9114.55,
    "change_pct": 0.69,
    "status": "ok"
  },
  "indices": [
    {
      "label": "코스피",
      "ticker": "^KS11",
      "price": 9114.55,
      "change_pct": 0.69
    },
    {
      "label": "코스닥",
      "ticker": "^KQ11",
      "price": 968.4,
      "change_pct": 0.19
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
      "price": 9114.55,
      "fired": false
    },
    {
      "id": "코스피 2차 트랜치",
      "ticker": "^KS11",
      "cond": "below",
      "when": null,
      "action": "2차 ~20만 분할 투입 (이란 결렬 동반 시)",
      "price": 9114.55,
      "fired": false
    },
    {
      "id": "NAVER 1차 매수존",
      "ticker": "035420.KS",
      "cond": "between",
      "when": null,
      "action": "국장=정수주만(소수점 불가) → 최소 1주 ≈229,500원. 정리후보+외인매도라 보류 우선, 매수해도 6/22 외인 재유입 확인 후 정수 1주 지정가",
      "price": 222000.0,
      "fired": false
    },
    {
      "id": "삼성전자 1차 매수존",
      "ticker": "005930.KS",
      "cond": "between",
      "when": null,
      "action": "1차 트랜치 대안",
      "price": 353500.0,
      "fired": false
    },
    {
      "id": "두산에너빌리티 10만 돌파",
      "ticker": "034020.KS",
      "cond": "above",
      "when": null,
      "action": "대미투자 원전 수혜 — 10만 돌파 시 비중 검토",
      "price": 94200.0,
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
      "id": "MU 실적 절반 차익 (KST 6/25 새벽)",
      "ticker": "EVENT",
      "cond": "event",
      "when": "美 6/24(수) 장마감 후 = KST 6/25(목) 새벽 ~05:30 (6/23 저녁 베이킹)",
      "action": "+51% 고평가·컨센 상회기대(sold out)·집중도 완화 → 절반(0.02주) 차익 조건부 예약(폰 미가용 → 6/23 저녁 사전 베이킹, 미장 소수점 시장가)",
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
      "price": 353500.0,
      "change_pct": -0.14,
      "value_krw": 707000,
      "pnl_pct": 34.41,
      "pnl_krw": 181000,
      "outlook": "core",
      "stars": 5,
      "score": 87,
      "target": "480,000~530,000원 (KB 53만·미래 48만)",
      "buy_zone": "295,000~305,000원 (현재가 위 — 눌림 대기)",
      "trim": "보류",
      "forecast": {
        "week": {
          "low": 335000,
          "high": 372000,
          "dir": "→",
          "note": "6/25 메모리 시험주간 직결. 외인 수급 변수."
        },
        "month": {
          "low": 325000,
          "high": 420000,
          "dir": "↑",
          "note": "HBM 매출 3배·일반DRAM +90% 레버리지 실적 검증 시 48~53만 목표 진입."
        }
      },
      "comment": "사이클 중반·일반DRAM 판가 +90% 레버리지. HBM4 엔비디아·AMD 인증, 2월 양산. 마이클 버리 유형장부가 매수론(검증).",
      "issues": [
        {
          "date": "2026-06-22",
          "tag": "검증",
          "text": "경제사냥꾼①: 마이클 버리 '삼성 주당 유형장부가 닿으면 매수'·1Q 영업익 57.2조 역대최대·HBM4 2026 솔드아웃·2027 공급부족(검증). 코어 강세론 정합. ⚠️ '美정부 다음 지분 후보' 설은 미확인(시장추측)."
        },
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
      "price": 227500.0,
      "change_pct": 7.57,
      "value_krw": 227500,
      "pnl_pct": 46.59,
      "pnl_krw": 72300,
      "outlook": "core",
      "stars": 4,
      "score": 63,
      "target": "컨센 초과 (12~23만 이미 상회)",
      "buy_zone": "홀딩 (추가매수 보류)",
      "trim": "손절선 없음 — 펀더 훼손 시에만 매도 검토",
      "forecast": {
        "week": {
          "low": 200000,
          "high": 221000,
          "dir": "→",
          "note": "1주뿐 분할불가, 박스권 홀딩."
        },
        "month": {
          "low": 193000,
          "high": 238000,
          "dir": "↑",
          "note": "냉각CDU·NVIDIA DSX 모멘텀, 영업익 +40% 증익 확인 시 23만+."
        }
      },
      "comment": "그룹 동반 차익실현·펀더 무손상=홀딩. 냉각 CDU·NVIDIA DSX 동맹. 자사주 2,000억(2조 아님·정정). 7/23 실적 분수령. 보유 1주뿐 → 분할 트림 불가.",
      "issues": [
        {
          "date": "2026-06-22",
          "tag": "검증",
          "text": "6/22 종가 227,500원(+7.57%) = 보유 최강세. 그룹 동반 차익실현 낙폭(6/19 −7.44%) 되돌림 반등. 보유 1주뿐 분할 트림 불가→코어 홀딩."
        },
        {
          "date": "2026-06-22",
          "tag": "정정",
          "text": "경제사냥꾼⑦ 자사주 '2조원'은 10배 과장 — 실제 2027까지 2,000억·2026 결의 1,000억 중 ~50%(businesspost). 방향(43만→21만 반토막·냉각CDU·로봇 액추에이터·7/23 분수령)은 검증. 2,000억으로 정정 인용."
        },
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
      "price": 100400.0,
      "change_pct": -1.38,
      "value_krw": 100400,
      "pnl_pct": 0.4,
      "pnl_krw": 400,
      "outlook": "momentum",
      "stars": 2,
      "score": 17,
      "target": "분산 큼 (컨센 109k ~ 극단 300k)",
      "buy_zone": "관망",
      "trim": "모멘텀 — 큰 갭업 시 차익",
      "forecast": {
        "week": {
          "low": 90000,
          "high": 116000,
          "dir": "→",
          "note": "모멘텀주=변동성 큼. 갭업 시 차익 대상."
        },
        "month": {
          "low": 83000,
          "high": 135000,
          "dir": "→",
          "note": "적자·고PSR=데이터 취약. 테마 강세 의존, 코어 아님."
        }
      },
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
      "price": 581000.0,
      "change_pct": -5.22,
      "value_krw": 581000,
      "pnl_pct": -7.78,
      "pnl_krw": -49000,
      "outlook": "hold",
      "stars": 3,
      "score": 47,
      "target": "600,000원 (공격 800,000원)",
      "buy_zone": "관망",
      "trim": "—",
      "forecast": {
        "week": {
          "low": 590000,
          "high": 632000,
          "dir": "→",
          "note": "PER 10.8 저평가 방어적."
        },
        "month": {
          "low": 575000,
          "high": 690000,
          "dir": "↑",
          "note": "로보틱스 옵션·저밸류. 관세·EV 리스크가 상단 제약, 80만은 공격목표."
        }
      },
      "comment": "BD 풋옵션 7/20·삼성 지분설. 보스턴다이내믹스 휴머노이드(아틀라스 2028). 6/22 비반도체 로테이션 약세 −5%대. 본업 관세·EV 리스크.",
      "issues": [
        {
          "date": "2026-06-22",
          "tag": "검증",
          "text": "6/22 종가 581,000원(−5%대 급락, Yahoo −5.22%/기사 ~602k −5.79%). 반도체 쏠림장 비반도체·2차전지 로테이션 약세. 보유 1주 홀딩(관망), 종가 토스 확정 권고."
        },
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
      "price": 222000.0,
      "change_pct": -3.27,
      "value_krw": 222000,
      "pnl_pct": -11.38,
      "pnl_krw": -28500,
      "outlook": "trim_candidate",
      "stars": 2,
      "score": 51,
      "target": "~300,000원 (메리츠 410,000원)",
      "buy_zone": "225,000~235,000원 (종가 222k = 존 아래 이탈)",
      "trim": "정리후보",
      "forecast": {
        "week": {
          "low": 218000,
          "high": 248000,
          "dir": "→",
          "note": "6/22 외인 매도 지속 여부가 키. 확인 전 진입금지."
        },
        "month": {
          "low": 210000,
          "high": 280000,
          "dir": "→",
          "note": "PER20 저평가나 +12% 안정성장. 외인 복귀 시 30만(메리츠 41만)."
        }
      },
      "comment": "6/22 매수 보류 확정 — 외인 재유입 분수령 실패(2일연속 −2.55조)+종가 222,000원으로 매수존 이탈+정리후보. 3중 미충족. 외인 재유입 재확인 시 재검토. ⚠️국장 소수점 불가→최소 1주.",
      "issues": [
        {
          "date": "2026-06-22",
          "tag": "검증",
          "text": "종가 222,000원(−3.27%) = 매수존(225~235k) 아래로 이탈. 외인 6/22 −2.55조 순매도(2일연속, 분수령 실패) → NAVER 1차 매수 보류 확정(존 이탈+외인이탈+정리후보 3중)."
        },
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "229,500원 = 매수존 진입(유일 발동). 단 정리후보 + 외인 순매도 전환 → 6/22 확인 전 보류. ⚠️국장 소수점 불가 → 1주 ≈229,500원이 최소(소액 10만원 매수 불가)."
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
      "value_krw": 1666841,
      "pnl_pct": 5.6,
      "pnl_krw": 173749,
      "outlook": "core",
      "stars": 5,
      "score": 100,
      "target": "$298.93 (+45.7%)",
      "buy_zone": "눌림",
      "trim": "비중관리 (이미 최대 비중)",
      "forecast": {
        "week": {
          "low": 200,
          "high": 226,
          "dir": "↑",
          "note": "실적 8/26 멀어 모멘텀·필반 강세 추종."
        },
        "month": {
          "low": 192,
          "high": 255,
          "dir": "↑",
          "note": "분기EPS +212%·PEG0.49. 목표 $298(+42%) 상방. 최대비중→신규절제."
        }
      },
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
      "value_krw": 1003499,
      "pnl_pct": -8.95,
      "pnl_krw": -39113,
      "outlook": "core",
      "stars": 4,
      "score": 75,
      "target": "$827.32 (+45.9%)",
      "buy_zone": "실적확인 (7/29 전 보류)",
      "trim": "—",
      "forecast": {
        "week": {
          "low": 555,
          "high": 607,
          "dir": "↑",
          "note": "낙폭 깊음=저가매력. 3차 트랜치 1순위 후보."
        },
        "month": {
          "low": 538,
          "high": 700,
          "dir": "↑",
          "note": "분기EPS+60%·저PE20.6. 목표 $827(+43%🎯), 7/29 실적이 재개 조건."
        }
      },
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
      "value_krw": 1028536,
      "pnl_pct": 6.62,
      "pnl_krw": 115974,
      "outlook": "core",
      "stars": 4,
      "score": null,
      "target": "— (ETF)",
      "buy_zone": "적립",
      "trim": "—",
      "forecast": {
        "week": {
          "low": 675,
          "high": 706,
          "dir": "↑",
          "note": "S&P500 시장β. 위험선호 회복 추종."
        },
        "month": {
          "low": 663,
          "high": 742,
          "dir": "↑",
          "note": "분산형 코어. 적립 대상, PCE가 단기 변수."
        }
      },
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
      "value_krw": 842952,
      "pnl_pct": -7.51,
      "pnl_krw": -19178,
      "outlook": "core",
      "stars": 4,
      "score": 66,
      "target": "$561.39 (+43.7%)",
      "buy_zone": "눌림",
      "trim": "—",
      "forecast": {
        "week": {
          "low": 365,
          "high": 396,
          "dir": "↑",
          "note": "안정 컴파운더. 실적 7/29."
        },
        "month": {
          "low": 355,
          "high": 450,
          "dir": "↑",
          "note": "매출+15%·순마진39%. 목표 $561(+48%🎯) 상방 최대."
        }
      },
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
      "value_krw": 928009,
      "pnl_pct": 15.89,
      "pnl_krw": 170544,
      "outlook": "hold",
      "stars": 3,
      "score": 58,
      "target": "$312.72 (+7.4%)",
      "buy_zone": "목표근접",
      "trim": "트림 1순위 후보",
      "forecast": {
        "week": {
          "low": 288,
          "high": 309,
          "dir": "→",
          "note": "목표 근접(+5%). 트림 1순위(분수주라 실효 낮음)."
        },
        "month": {
          "low": 280,
          "high": 318,
          "dir": "→",
          "note": "매출 +6.4% 둔화·PE36. 상방 제한적."
        }
      },
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
      "value_krw": 248200,
      "pnl_pct": -5.08,
      "pnl_krw": 846,
      "outlook": "core",
      "stars": 5,
      "score": 91,
      "target": "$432.83 (+20.3%)",
      "buy_zone": "눌림",
      "trim": "—",
      "forecast": {
        "week": {
          "low": 354,
          "high": 386,
          "dir": "↑",
          "note": "Cloud·Gemini 모멘텀."
        },
        "month": {
          "low": 345,
          "high": 422,
          "dir": "↑",
          "note": "분기EPS+82%·PEG0.81. 목표 $432(+18%)."
        }
      },
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
      "value_krw": 97249,
      "pnl_pct": -5.21,
      "pnl_krw": 198,
      "outlook": "hold",
      "stars": 2,
      "score": 18,
      "target": "$420.55 (ARK 2029 $2,600)",
      "buy_zone": "관망",
      "trim": "—",
      "forecast": {
        "week": {
          "low": 378,
          "high": 426,
          "dir": "→",
          "note": "펀더 최하=모멘텀. 변동성 큼, 갭업 차익 대상."
        },
        "month": {
          "low": 358,
          "high": 465,
          "dir": "→",
          "note": "이익−47%·PE334. 로보택시·Optimus 기대 의존, 코어 아님."
        }
      },
      "comment": "캐시우드 강세론 but 우드 본인 차익매도 중. SpaceX 합병설(NYT). Optimus 7~8월 생산. 목표 거의 도달.",
      "issues": [
        {
          "date": "2026-06-22",
          "tag": "검증·일부정정",
          "text": "경제사냥꾼③: NYT 보도 SpaceX+테슬라 합병 가능·Ives 80~90% 확률·텍사스 법인+2/3 주주찬성(검증). ⚠️ 합병가치 '$4조'는 과장 → 실제 ~$3.4조(Fortune). 테슬라株→합병 신주 전환·머스크 지배력 유지."
        },
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
      "value_krw": 61061,
      "pnl_pct": -20.61,
      "pnl_krw": -11691,
      "outlook": "hold",
      "stars": 3,
      "score": 71,
      "target": "$252.64 (+38.7%)",
      "buy_zone": "눌림",
      "trim": "패닉셀 금지",
      "forecast": {
        "week": {
          "low": 175,
          "high": 196,
          "dir": "→",
          "note": "최대 평가손(−20.6%). 신규보류."
        },
        "month": {
          "low": 164,
          "high": 230,
          "dir": "→",
          "note": "OCI+93%나 OpenAI 집중 리스크. 목표 $252(+37%🎯)지만 관망."
        }
      },
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
      "value_krw": 74063,
      "pnl_pct": 4.69,
      "pnl_krw": 7141,
      "outlook": "core",
      "stars": 4,
      "score": 78,
      "target": "$189.13 (+15.9%)",
      "buy_zone": "홀딩",
      "trim": "—",
      "forecast": {
        "week": {
          "low": 160,
          "high": 180,
          "dir": "→",
          "note": "AI fabric 수요. 실적 8/4."
        },
        "month": {
          "low": 154,
          "high": 192,
          "dir": "↑",
          "note": "매출+35%·ROE32%. 목표 $189(+11%)."
        }
      },
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
      "value_krw": 69841,
      "pnl_pct": 51.4,
      "pnl_krw": 26204,
      "outlook": "core",
      "stars": 5,
      "score": 99,
      "target": "$1,200~1,500 (도이체방크 $1,500·씨티 $1,200, 6/17 상향)",
      "buy_zone": "6/25 실적(목 새벽)",
      "trim": "절반 차익 (6/23 베이킹)",
      "forecast": {
        "week": {
          "low": 1040,
          "high": 1260,
          "dir": "↑",
          "note": "⚠️6/25 새벽 실적 = 양방향 변동성 폭탄. 절반차익 베이킹."
        },
        "month": {
          "low": 920,
          "high": 1430,
          "dir": "→",
          "note": "매출+196%·fwdPE16 강세 vs 시클리컬 정점 우려. DB $1,500 vs 절반차익 택1."
        }
      },
      "comment": "+51.4% 평가익. 회사 가이드 매출 $33.5B·GM~81%·EPS$19.15 < Street 컨센($34.5B·$19.8)=비트 기대 선반영. 목표가 Stifel $1,500·Wedbush $1,300·RBC $1,200(평균 $755~1,202 분산=정점패턴). GM 81% 유지가 사이클 건강도 핵심. 6/25(목) 새벽 실적, 6/23 저녁 폰창서 절반(0.02주) 시장가 베이킹.",
      "issues": [
        {
          "date": "2026-06-22",
          "tag": "검증",
          "text": "실적 확정 = 美 6/24(수) 16:00 ET 장마감 후 = KST 6/25 새벽 ~05:00(콜 06:00). 회사 가이드 매출 $33.5B±0.75·GM~81%·non-GAAP EPS $19.15 < Street 컨센 = 비트 선반영. 현재가가 다수 평균 TP 상회 → sell-the-news 헤지로 절반차익 합리. GM 81% 유지 여부가 핵심 시그널."
        },
        {
          "date": "2026-06-21",
          "tag": "검증",
          "text": "캘린더 확정: MU 실적 美 6/24(수) 장마감 후 = KST 6/25 새벽 + 美 5월 PCE 6/25 밤 21:30 KST → 둘 다 KST 6/25 목 더블 분수령(research-feed '하루시차' 플래그는 PM 교차검증 결과 오인). 절반차익 6/23 저녁 사전 베이킹."
        },
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
      "value_krw": 45081,
      "pnl_pct": -2.31,
      "pnl_krw": 1430,
      "outlook": "hold",
      "stars": 4,
      "score": 83,
      "target": "$522.06 (+36.6%)",
      "buy_zone": "조정주",
      "trim": "물타기 후보",
      "forecast": {
        "week": {
          "low": 394,
          "high": 436,
          "dir": "↑",
          "note": "평단 근접·AI매출 +143%. 3차 트랜치 후보."
        },
        "month": {
          "low": 382,
          "high": 500,
          "dir": "↑",
          "note": "순마진39%·ROE37%. 목표 $522(+27%)."
        }
      },
      "comment": "ASIC, 평단(421) 근접 물타기 후보. AI매출 Q3 +200%+. 앤트로픽 차세대칩 계약(검증). 6/18 FOMC 매파로 3차 동결.",
      "issues": [
        {
          "date": "2026-06-22",
          "tag": "검증",
          "text": "경제사냥꾼②: 앤트로픽($965B·10월 상장) 차세대 AI칩을 구글과 함께 브로드컴이 수주(검증) → AVGO 커스텀 ASIC 수혜 논지 보강. 단 3차 트랜치 FOMC 매파로 동결 중."
        },
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
      "price": 2919000.0,
      "change_pct": 5.61,
      "stars": 4,
      "score": null,
      "target": "Strong Buy",
      "forecast": null,
      "comment": "🏆 6/22 시총 1위 등극(2,919,000 +5.61%, 25년만 삼성 추월). ADR SEC 6월 넷째주(정식승인 미발표)·메리츠 8월 상장 목표 295만·HBM 57%·27년 PER 6.9배. 상장 전 진입금지(영구교정)·반도체 추격금지.",
      "issues": [
        {
          "date": "2026-06-22",
          "tag": "검증",
          "text": "6/22 종가 2,919,000원(+5.61%) 시총 2,080조 = 삼성전자(2,067조 보통주) 첫 추월, 약 25년 만 시총 1위. 반도체 슈퍼사이클+ADR 기대 촉매. ADR 정식 SEC 승인 헤드라인은 아직 미발표(메리츠 8월·목표 295만). 상장 전 진입금지."
        },
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
      "price": 2228000.0,
      "change_pct": -1.85,
      "stars": 3,
      "score": null,
      "target": "KB 3,000,000원 (220만→상향)",
      "forecast": null,
      "comment": "🔥 MLCC·기판 초호황 + 중일 희토류 반사이익 + 무라타發 MLCC 8년만 슈퍼사이클 테마. PER 180배 — 눌림 관찰, 추격금지.",
      "issues": [
        {
          "date": "2026-06-22",
          "tag": "검증",
          "text": "경제사냥꾼③: 한울반도체-무라타 MLCC 마운터 MOU(2연상한)發 'MLCC 8년만 슈퍼사이클'·무라타/삼성전기 가동률 90%+·AI서버 MLCC 28,000개·납기 10→24주(방향성 검증) → 삼성전기 강세 논거 보강. ⚠️6/22 종가 미수신(미확인)."
        },
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
      "score": null,
      "target": "$1,211.72 (Bernstein $1,206)",
      "forecast": null,
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
      "price": 94200.0,
      "change_pct": -3.78,
      "stars": 3,
      "score": null,
      "target": "135,000~165,000원",
      "forecast": null,
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
      "price": 1130000.0,
      "change_pct": -1.31,
      "stars": 3,
      "score": null,
      "target": "KB 1,600,000원",
      "forecast": null,
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
      "price": 116500.0,
      "change_pct": -9.27,
      "stars": 3,
      "score": null,
      "target": "—",
      "forecast": null,
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
      "score": null,
      "target": "$63~$190 (분산)",
      "forecast": null,
      "comment": "6/26 MSCI/Russell 편입 vs 8월 첫 20% 락업 언락. 테슬라 합병설(NYT)=새 변수. 추격금지.",
      "issues": [
        {
          "date": "2026-06-22",
          "tag": "검증·일부정정",
          "text": "경제사냥꾼③: NYT SpaceX+테슬라 합병설(Ives 80~90%)=테슬라株로 SpaceX 우회노출 가능성 새 변수. 합병가치 '$4조'는 과장→~$3.4조(Fortune)."
        },
        {
          "date": "2026-06-20",
          "tag": "검증",
          "text": "6/26 MSCI/Russell 편입 메커닉 vs 8월 첫 20% 락업 언락 — 변동성 주의."
        }
      ]
    },
    {
      "label": "KT&G",
      "ticker": "033780.KS",
      "currency": "KRW",
      "price": 174900.0,
      "change_pct": -2.83,
      "stars": 3,
      "score": null,
      "target": "DS증권 240,000원",
      "forecast": null,
      "comment": "🆕 신규 워치 후보(경제사냥꾼⑥ 정확도 최고). 외인 51.24%·블랙록 6.15%·해외궐련 +56%·주주환원 3.7조·자사주 9.5% 소각. 디펜시브 배당+해외성장=AI 쏠림장 분산. 정식 편입 전 딥다이브 검토.",
      "issues": [
        {
          "date": "2026-06-22",
          "tag": "검증",
          "text": "경제사냥꾼⑥[정확도 최고·무오차]: 외인 51.24%(블랙록 6.15%·캐피털 7.21%)·1Q 영익 3,645억(+27.6%)·해외궐련 +24.6%/영익 +56.1%·NGP 2,793억→8,900억·DS 목표 24만. 신규 워치 후보 검토."
        }
      ]
    },
    {
      "label": "원익IPS",
      "ticker": "240810.KQ",
      "currency": "KRW",
      "price": 172500.0,
      "change_pct": 10.58,
      "stars": 3,
      "score": null,
      "target": "눌림 130,000~150,000원 검토",
      "forecast": null,
      "comment": "반도체 소부장(증착장비). 삼성·하이닉스 증설 수혜. 매수존 무효 — 눌림 분할 관찰. ⚠️Yahoo 시세 보고서값과 불일치 이력 → 인용 전 교차검증.",
      "issues": [
        {
          "date": "2026-06-14",
          "tag": "검증",
          "text": "티커 .KS→.KQ(코스닥) 정정."
        }
      ]
    },
    {
      "label": "테스",
      "ticker": "095610.KQ",
      "currency": "KRW",
      "price": 183400.0,
      "change_pct": 10.35,
      "stars": 3,
      "score": null,
      "target": "눌림 대기",
      "forecast": null,
      "comment": "반도체 소부장(식각·증착). 소부장 로테이션 수혜, 원익IPS 대비 덜 과열. ⚠️Yahoo 시세 교차검증 필요.",
      "issues": [
        {
          "date": "2026-06-14",
          "tag": "검증",
          "text": "티커 .KS→.KQ(코스닥) 정정."
        }
      ]
    },
    {
      "label": "SK이노베이션",
      "ticker": "096770.KS",
      "currency": "KRW",
      "price": 100200.0,
      "change_pct": -2.15,
      "stars": 3,
      "score": null,
      "target": "—",
      "forecast": null,
      "comment": "AI 전력난 SMR 테마(테라파워 2대주주·메타 원전 8기 협력설). 단 SK온 적자·정유 변동성 리스크. 6/14 신규 후보.",
      "issues": [
        {
          "date": "2026-06-14",
          "tag": "미확인",
          "text": "테라파워 지분·메타 원전 협력 단일출처 → 교차검증 필요."
        }
      ]
    },
    {
      "label": "한화에어로",
      "ticker": "012450.KS",
      "currency": "KRW",
      "price": 1125000.0,
      "change_pct": 0.27,
      "stars": 4,
      "score": null,
      "target": "—",
      "forecast": null,
      "comment": "대미투자 방산·조선 직결. 한화가 KAI 9.04% 2대주주(6/17). 재활성 워치. 단 유상증자 희석 리스크 병기.",
      "issues": [
        {
          "date": "2026-06-18",
          "tag": "정정",
          "text": "경제사냥꾼 자막 '김승현'→실제 김승연 회장(이름 오타), 지분·경영참여는 일치."
        }
      ]
    },
    {
      "label": "삼성중공업",
      "ticker": "010140.KS",
      "currency": "KRW",
      "price": 26200.0,
      "change_pct": -4.9,
      "stars": 3,
      "score": null,
      "target": "—",
      "forecast": null,
      "comment": "대미투자 조선 바스켓. 시행 후 수주 소화 관찰.",
      "issues": []
    },
    {
      "label": "HD현대중공업",
      "ticker": "329180.KS",
      "currency": "KRW",
      "price": 636000.0,
      "change_pct": -4.65,
      "stars": 3,
      "score": null,
      "target": "—",
      "forecast": null,
      "comment": "대미투자 조선 바스켓. 함정·상선 수주 모멘텀. 시행 후 소화 관찰.",
      "issues": []
    },
    {
      "label": "T-Mobile",
      "ticker": "TMUS",
      "currency": "USD",
      "price": 181.67,
      "change_pct": 0.2,
      "stars": 3,
      "score": null,
      "target": "—",
      "forecast": null,
      "comment": "스타링크 D2C(다이렉트-투-셀) 위성통신 테마. 통신 안정성 + 위성 옵션.",
      "issues": []
    },
    {
      "label": "STMicro",
      "ticker": "STM",
      "currency": "USD",
      "price": 78.39,
      "change_pct": 6.86,
      "stars": 2,
      "score": null,
      "target": "—",
      "forecast": null,
      "comment": "차량용·아날로그 반도체. 약세 지속, 후순위. 사이클 회복 확인 전 관망.",
      "issues": []
    },
    {
      "label": "팔란티어",
      "ticker": "PLTR",
      "currency": "USD",
      "price": 128.47,
      "change_pct": -1.65,
      "stars": 3,
      "score": null,
      "target": "$185~200 (+42~53%)",
      "forecast": null,
      "comment": "AI 소프트웨어 대장(딥다이브 6/18). 고점 -16%·Rule of 40 145%·FCF $4.2B 흑자=준코어. 단 PSR 60~67x(S&P 최고축)·Karp 매도·FOMC 베타 매우 높음(매파에 가장 먼저 디레이팅). 추격금지 — $110~120 눌림 분할만.",
      "issues": [
        {
          "date": "2026-06-18",
          "tag": "미확인",
          "text": "PSR 60~67x 고밸류·Karp 본인 매도 → 매파 국면 리스크. 컨센 목표 $185~200."
        }
      ]
    }
  ],
  "tranches": [
    {
      "id": "1차",
      "amount_krw": 235000,
      "executed": false,
      "trigger": "국장=정수 1주만(소수점 불가). NAVER 1주(≈229,500, 225~235k) — 단 정리후보라 6/22 외인 재유입 확인 시에만, 아니면 보류. 삼성은 1주 ≈305k+ 별도 필요(현재 354k라 한참 위·눌림 대기)."
    },
    {
      "id": "2차",
      "amount_krw": 200000,
      "executed": false,
      "trigger": "이란 결렬 + 코스피 8,000 하회. 국장은 1주 단위(두산로보 ≈101,800·LG전자 ≈211,500), 미장은 소수점 분할."
    },
    {
      "id": "3차",
      "amount_krw": 189771,
      "executed": false,
      "trigger": "🔴 FOMC 6/18 매파 확정으로 전면 보류. 재개 조건 = 비둘기 전환 / META 7/29 실적 확인 / 외인 순매수 복귀 중 하나. 재개 시 미장 META·AVGO 소수점 예약(시장가). 1·2·3차 합 = 624,771원(현금 전액)."
    }
  ],
  "fx_history": {
    "dates": [
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
      "2026-06-22"
    ],
    "closes": [
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
      1539.71
    ]
  },
  "kospi_history": {
    "dates": [
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
      "2026-06-19",
      "2026-06-22"
    ],
    "closes": [
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
      9052.42,
      9114.55
    ]
  },
  "hunter": {
    "_comment": "경제사냥꾼 분석 앱 정본. 보고서마다 research-feed/PM이 docs/research/hunter_log.md 갱신 시 여기 latest_videos(최신순 prepend)·track_record(최신 prepend)·themes도 함께 갱신 후 build_app_data.py 재실행. 앱에서 영상 목록을 누르면 상세 화면(#video/<id>)으로 들어간다. 각 영상 필드: date·title·tag(검증분류)·tickers(언급 종목, 앱에서 종목 상세로 링크) + summary(요약, 필수) + 선택 상세필드 points(핵심 포인트 배열)·mentions(언급 — 종목·인물·기관 서술)·references(참고 — 출처/기관 배열)·caveats(주의·미확인·과장 배열)·link(영상 URL). 선택필드는 있으면 상세화면에 표시, 없으면 생략. id는 없으면 앱이 목록 순번으로 라우팅.",
    "updated": "2026-06-22 (낮 신규 3편 반영)",
    "source": "docs/research/hunter_log.md",
    "channel_note": "테마·방향성은 빠르고 유용(로봇·AI전력·종전 등 선제 포착). 단 구체 수치는 자막오류·과장 잦음 → 방향성은 채택하되 숫자는 교차검증. 트랙레코드 개선세. ✅6/22 신규 3편(낮)도 자막 정상 확보, 수치 과장 이번엔 양호.",
    "headline": "6/22 낮 신규 3편 = 정훈 대기 트리거(외인·MU·PCE) 방향성 재확인. ①국민연금 6월 매도=리밸런싱 유예 종료, 7월 룰 재적용→월 7~8조 재개(바클레이즈)·받침대=빚투 38조 사상최고[검증] ②6/22 포인트=미·이란 회담·6/25 PCE·MU 컨센 $34.4B/$19.7[검증] ③한울반도체(자막 '하늘' 오류)-무라타 MLCC MOU 2연상한=삼성전기 테마 보강[검증]. ⚠️신규 리스크 모니터=7월 국민연금 받침대 제거·빚투 반대매매 도미노.",
    "latest_videos": [
      {
        "id": "nps-sells-kospi-9000",
        "date": "2026-06-22",
        "title": "국민연금이 코스피 9000에서 주식 팔아치운 진짜 이유",
        "tag": "검증·일부미확인",
        "tickers": [],
        "summary": "국민연금 6월 한국주식 매도 = 펀더 이탈 아닌 리밸런싱 유예(6월말 종료)→7월 룰 재적용 전 기계적 비중축소. [검증] 국내주식 목표비중 14.9→20.8% 상향(복지부 5/28)·바클레이즈 '7월부터 월 7~8조 리밸런싱 재개→변동성 정상화'. 진짜 변수=그 물량을 외인이 받나 vs 빚투 38조(신용융자 사상최고)가 받나. [미확인] 연기금 주간매도 1,970억→1.2조 6배·외인 100조 매도에도 보유비중 40%대 상승은 자막단독. 정훈 외인 분수령·안전핀 직결 — 7월=외인 흡수력 시험대, 빚투 38조=반대매매 도미노 리스크.",
        "points": [
          "[검증] 국민연금 국내주식 목표비중 14.9→20.8% 상향(복지부/기금위 5/28)",
          "[검증] 바클레이즈: 7월부터 월 7~8조 리밸런싱 재개→코스피 변동성 정상화",
          "받침대=개인 빚투 38조 사상최고 → 7월 받침대 제거 시 반대매매 도미노 리스크"
        ],
        "mentions": "국민연금·외국인·신용융자(빚투). 코스피 수급 구조.",
        "references": [
          "정책브리핑(목표비중 20.8%)",
          "이코노미트리뷴/investing.com(바클레이즈 7~8조)",
          "머니투데이(170조 매도 회피)"
        ],
        "caveats": [
          "연기금 주간 매도 절대수치 6배는 자막단독(방향만 채택)",
          "외인 보유비중 40%대 상승 수치 미확인",
          "7월 재개는 시나리오(채널도 단서)"
        ]
      },
      {
        "id": "0622-invest-points",
        "date": "2026-06-22",
        "title": "6월 22일 투자자가 꼭 알아야 하는 투자 포인트(쇼츠)",
        "tag": "검증·일부미확인",
        "tickers": [
          "MU"
        ],
        "summary": "미·이란 1차 회담(스위스) 진행·호르무즈 개방 '상당한 진전' but 해석 충돌·트럼프 '통행료' 경고. 원달러 야간 1,540 돌파. [검증] 6/25 밤 21:30 美 PCE·MU 컨센 매출 $34.4B/EPS $19.7(골드만 $37.6B/$22.07/GM83.4% 상회전망). ⚠️MU 발표일 다수매체 6/24(美) = KST 6/25 새벽. 정훈 트리거(MU 절반차익 베이킹·PCE 분수령)와 정확 일치 — 21:30 PCE는 폰 미가용→사전 베이킹.",
        "points": [
          "[검증] 6/25 밤 美 PCE·MU 실적(美 6/24 장후=KST 6/25 새벽) = 더블 분수령",
          "[검증] MU 컨센 매출 $34.4B·EPS $19.7(골드만 상회 $37.6B/$22.07)",
          "[미확인] 미·이란 호르무즈 회담 진전/충돌·원달러 1,540 돌파 틱"
        ],
        "mentions": "마이크론(MU)·미국 PCE·미·이란 회담·원달러.",
        "references": [
          "TradingKey(MU Q3 프리뷰)",
          "이데일리(골드만 MU 전망)"
        ],
        "caveats": [
          "미·이란 지정학은 본 탐색서 미교차(매크로 데스크 확인)",
          "원달러 정확 틱 시세 데스크 확인"
        ]
      },
      {
        "id": "kosdaq-leader-hanwool",
        "date": "2026-06-22",
        "title": "코스닥 주도주로 떠오르는 종목 정체(쇼츠)",
        "tag": "검증·정정",
        "tickers": [
          "009150.KS"
        ],
        "summary": "⚠️[정정] 자막 '하늘 반도체'→실제 한울반도체(코스닥). 日 무라타와 고성능 MLCC 마운터 설비 MOU→2거래일 연속 상한가(17,820원). [검증] MOU·2연상한·무라타 800억엔 증설 사실(서울경제/디일렉/뉴시스). MLCC 8년만 슈퍼사이클·무라타/삼성전기 가동률 90%+(방향성 검증, AI서버 28,000개·납기 24주 등 수치는 자막단독). '삼성전기 아닌 한울 선택=삼성전기는 무라타 경쟁사, 한울은 장비사' 논리 타당. → 삼성전기(워치) MLCC 테마 보강. 한울은 보유/워치 아님·1Q 영업손실 42억=추격 부적합(룰3).",
        "points": [
          "[정정] 종목명 자막 '하늘'→실제 한울반도체(코스닥)",
          "[검증] 한울-무라타 MLCC 마운터 MOU→2연상한, MLCC 8년만 슈퍼사이클",
          "→ 삼성전기(워치) 테마 보강. 한울은 추격 부적합(MOU 평가단계·1Q 적자)"
        ],
        "mentions": "한울반도체·무라타·삼성전기(009150). MLCC 슈퍼사이클.",
        "references": [
          "서울경제/EBN(한울-무라타 MOU·2연상한)"
        ],
        "caveats": [
          "MLCC 28,000개·납기 24주 등 수치 자막단독",
          "한울 MOU=평가 시작 단계, 정식 공급계약 아님"
        ]
      },
      {
        "id": "samsung-burry-cheapest-buy",
        "date": "2026-06-21",
        "title": "월가가 삼성전자 가장 쌀 때 사는 법",
        "tag": "검증",
        "tickers": [
          "005930.KS"
        ],
        "summary": "마이클 버리 매수기준 = 삼성 '주당 유형자산가치(tangible BVPS)' 닿으면 매수, 안 파는 것도 방법. [검증] 30년간 그 선 8회 모두 매수기회·1998 바닥부터 470배(연24.6%)·1Q 영업익 57.2조 역대최대·HBM4 2026 솔드아웃·2027 공급부족 심화 — 전부 사실(디일렉/theguru 교차검증). 우리 데스크 삼성 코어 강세론(⭐5/87)과 정합.",
        "points": [
          "마이클 버리: 삼성 주당 유형장부가 닿을 때 매수·30년 8회 모두 기회",
          "[검증] 1998 바닥부터 470배(연24.6%)·1Q 영업익 57.2조 역대최대",
          "[검증] HBM4 2026 솔드아웃·2027 공급부족 → 메모리 슈퍼사이클"
        ],
        "mentions": "삼성전자(005930)·마이클 버리. 유형장부가 매수전략.",
        "references": [
          "디일렉(삼성 1Q 컨콜)",
          "theguru(버리 삼성)"
        ],
        "caveats": [
          "버리 본인 현 포지션은 미공개 — 과거 전략론 인용"
        ]
      },
      {
        "id": "anthropic-ipo-beneficiaries",
        "date": "2026-06-20",
        "title": "월가가 미리 줍는 앤트로픽 상장 수혜주",
        "tag": "검증·일부정정",
        "tickers": [
          "AVGO"
        ],
        "summary": "앤트로픽 기업가치 $965B(5월 오픈AI 역전)·10월 나스닥 상장 예정(6/1 S-1 비공개 제출). 직접투자 불가→수혜 3종: 아마존(AWS+$80억·Trainium 5GW)·브로드컴(구글/앤트로픽 차세대칩 계약)·SKT. [검증] $965B·상장 타깃·아마존 $80억·브로드컴 TPU 계약 사실. [정정] SKT 지분 '조단위 평가'는 추정 — 실제 SKT 약 0.3%·장부가 ~1.3조원(채널도 추정 명시). → AVGO 커스텀 ASIC 수혜 논지 보강.",
        "points": [
          "앤트로픽 $965B·10월 나스닥 상장→직접투자 불가, 수혜주 우회",
          "[검증] 브로드컴 구글/앤트로픽 차세대 AI칩 계약 = AVGO ASIC 수혜",
          "[정정] SKT 지분 '조단위'→실제 ~1.3조(0.3%), 추정값"
        ],
        "mentions": "브로드컴(AVGO)·아마존·SK텔레콤. 앤트로픽 상장 우회노출.",
        "references": [
          "TechTimes(앤트로픽 $965B·SKT)"
        ],
        "caveats": [
          "SKT 지분 평가는 추정·미공개",
          "앤트로픽 상장일 10월은 타깃(확정 아님)"
        ]
      },
      {
        "id": "spacex-tesla-merger",
        "date": "2026-06-21",
        "title": "스페이스X+테슬라 합병, 투자자 필독",
        "tag": "검증·일부정정",
        "tickers": [
          "TSLA",
          "SPCX"
        ],
        "summary": "NYT 보도 — 머스크 다음 행보=SpaceX·테슬라 초대형 합병 가능. [검증] NYT 합병보도·텍사스 법인·2/3 주주찬성 요건·솔라시티 소송 선례 사실, Wedbush Ives 합병확률 80~90%. [정정] 합병가치 '6,100조(≈$4조)'는 과장 — Fortune 추정 ~$3.4조. 테슬라株→합병 신주 전환·머스크 지배력 유지. SpaceX 워치 종목엔 '합병=테슬라株 우회노출' 새 변수.",
        "points": [
          "[검증] NYT 합병 보도·텍사스 법인·2/3 주주찬성·Ives 80~90% 확률",
          "[정정] 합병가치 '$4조/6,100조'→실제 ~$3.4조(Fortune)",
          "SpaceX 워치=테슬라株 우회노출 가능성 새 변수"
        ],
        "mentions": "테슬라(TSLA)·SpaceX·일론 머스크. NYT 합병 보도.",
        "references": [
          "Fortune(SpaceX-Tesla $3.4T 합병 확률)"
        ],
        "caveats": [
          "합병 확정 아님 — 보도·확률 단계",
          "합병가치 채널 과장($4조 vs $3.4조)"
        ]
      },
      {
        "id": "trump-govt-stakes-next-samsung",
        "date": "2026-06-21",
        "title": "트럼프가 주식 사준 회사들·다음은 삼성/하이닉스",
        "tag": "검증·일부미확인",
        "tickers": [
          "005930.KS",
          "000660.KS",
          "042660.KS"
        ],
        "summary": "美정부 주주참여 사례: 인텔 9.9%($89억·주당$20.47, 지분가치 $500억+)·MP머티리얼즈 국방부 15%·US스틸 골든셰어·양자컴 9곳 $20억·글로벌파운드리 1%. 한국 첫 케이스=고려아연(테네시 11조 제련소·JV 국방부 40.1%·간접 ~10%·발표일 +27% 신고가). [검증] 인텔·고려아연·MP머티리얼즈 디테일 전부 사실. [미확인] '삼성·SK하이닉스가 다음 정부지분 후보'=시장추측·확정근거 없음(방향성만). 한화오션=필라델피아 조선(자기돈 투자, 정부지분과 구분).",
        "points": [
          "[검증] 美정부 지분 인텔 9.9%($89억)·고려아연 테네시 JV 국방부 40.1%",
          "[미확인] '삼성·SK하이닉스 다음 후보'=시장추측, 단정 금지",
          "한화오션 필라델피아 조선 = 美투자 명단(정부지분과 구분 필요)"
        ],
        "mentions": "삼성전자·SK하이닉스·고려아연·인텔·한화오션. 美정부 지분참여.",
        "references": [
          "한국경제(고려아연 테네시)",
          "서울경제(고려아연 美지분10%)",
          "글로벌이코노믹(인텔 9.9%)"
        ],
        "caveats": [
          "'삼성·하이닉스 다음 후보'는 예단 — 미확인",
          "정부지분(인텔·고려아연) vs 자기돈투자(한화오션) 혼동 금지"
        ]
      },
      {
        "id": "trump-next-target-cuba",
        "date": "2026-06-21",
        "title": "트럼프가 이란 다음 콕 집은 나라 = 쿠바",
        "tag": "미확인",
        "tickers": [
          "012450.KS"
        ],
        "summary": "1월 베네수엘라 마두로 체포로 쿠바 기름줄(80~90% 베네수산) 차단→5월 제재폭증·6/4 디아스카넬 직접제재·6/10 관타나모 군사압박·6/11 큐펫 제재. 베네수엘라/이란 각본 판박이. '전쟁시대 돈은 기름이 아니라 방산으로'. [미확인] 쿠바 제재 타임라인은 개별 사실이나 '쿠바=다음 전쟁 타깃'은 채널 시나리오·예단(채널도 '안 터질 수도' 명시). 방향성: 방산 테마 지지(한화에어로 워치 동행).",
        "points": [
          "[미확인] '쿠바=다음 전쟁 타깃'은 예단(채널 면피멘트 부가)",
          "방향성: '돈은 방산으로' = 방산 워치 논지 동행"
        ],
        "mentions": "한화에어로(012450)·방산테마·쿠바 제재.",
        "references": [],
        "caveats": [
          "'쿠바=다음전쟁'은 시나리오 예단, 투자판단 근거 약함"
        ]
      },
      {
        "id": "ktng-foreign-buying",
        "date": "2026-06-21",
        "title": "월가가 공격 매수하는 의외의 한국주 = KT&G",
        "tag": "검증",
        "tickers": [
          "033780.KS"
        ],
        "summary": "외인 지분 51%+ 돌파(블랙록 6.15%·캐피털 7.21%). 1Q 매출 1.7036조·영업익 3,645억(+14.3%/+27.6%), 해외궐련 +24.6%/영업익 +56.1%. 2024~27 주주환원 3.7조+α·자사주 9.5% 전량소각·NGP 매출 2,793억→8,900억 목표. DS증권 목표 24만원. [검증] 수치 거의 무오차 — 이번 7편 중 정확도 최고. 디펜시브 배당+해외성장=AI 쏠림장 분산 후보 → 신규 워치 검토.",
        "points": [
          "[검증] 외인 51.24%·블랙록 6.15%·캐피털 7.21% (수치 무오차)",
          "[검증] 1Q 영익 3,645억(+27.6%)·해외궐련 영익 +56.1%",
          "주주환원 3.7조·자사주 9.5% 소각·DS 목표 24만 → 신규 워치 후보"
        ],
        "mentions": "KT&G(033780). 외인 매수·디펜시브 배당·해외 NGP 성장.",
        "references": [
          "한국경제(KT&G 외인51%·블랙록)"
        ],
        "caveats": [
          "담배 규제·NGP 경쟁 리스크는 별도 점검 필요"
        ]
      },
      {
        "id": "lg-electronics-subscriber-analysis",
        "date": "2026-06-20",
        "title": "구독자 전용 LG전자 분석",
        "tag": "검증·정정",
        "tickers": [
          "066570.KS"
        ],
        "summary": "43만원→21만원 반토막, 테마(로봇)가 실적검증 요구 구간 진입. 3대 무기: ①AI데이터센터 냉각(칠러·CDU) ②로봇 액추에이터(연 4,500만대 모터경험) ③B2B솔루션. 7/23 실적이 분수령. [검증] 주가 반토막·데이터센터 냉각·로봇 액추에이터 방향 사실. [정정] 자사주 규모 10배 과장 — 채널 '2027까지 2조원·올해 1조 중 절반'이나 실제 '2027까지 2,000억원·2026 결의 1,000억원 중 약 50% 완료'(businesspost). 정훈 보고 시 2,000억으로 정정 인용.",
        "points": [
          "[검증] 43만→21만 반토막·냉각CDU·로봇 액추에이터·7/23 분수령",
          "[정정] 자사주 '2조원' → 실제 2,000억(10배 과장·자막 단위오류)"
        ],
        "mentions": "LG전자(066570). 냉각CDU·로봇 액추에이터·자사주.",
        "references": [
          "businesspost(LG전자 자사주)"
        ],
        "caveats": [
          "자사주 규모 10배 과장 — 반드시 2,000억으로 정정 인용"
        ]
      },
      {
        "id": "trump-korea-next-beneficiaries",
        "date": "2026-06-21",
        "title": "트럼프 밀어주기 다음 후보가 될 수 있다는 '한국 주식'들",
        "tag": "검증·일부미확인",
        "tickers": [],
        "summary": "⚠️자막 봇차단 — 제목·메타+WebSearch 교차검증만(본문 수치 미확보). 트럼프 2기 우호 '다음 한국 수혜군' = 정황상 조선·방산·우주. [검증]트럼프 트레이딩으로 한화오션(필리조선소 인수·美 핵잠 SSN 필라델피아 건조 참여)·한화에어로가 부상, 조선은 미·중 해양패권 경쟁서 한국이 사실상 유일 전략 파트너=관세 무풍지대 평가. [미확인]채널이 지목한 구체 '다음 후보 종목 명단'·수치는 미확보. 워치 한화오션·한화에어로·SpaceX(우주) 직결 — 단 테마성 강해 추격금지(룰3), 국장 진입은 정수 1주 이상 지정가.",
        "points": [
          "트럼프 우호 '다음 한국 수혜군' = 조선·방산·우주 테마(제목 기반 추정)",
          "[검증] 한화오션(美 필리조선소·핵잠 건조)·한화에어로 = '트럼프 트레이딩' 부상, 조선은 한국이 사실상 유일 전략 파트너",
          "[미확인] 구체 '다음 후보 종목 명단'·수치는 자막 미확보",
          "워치 한화오션·한화에어로·SpaceX 직결 — 추격금지(테마성), 정수 1주 이상 지정가"
        ],
        "mentions": "한화오션(042660)·한화에어로(012450)·SpaceX. 트럼프 조선·방산·우주 정책 수혜.",
        "references": [
          "한국경제(방산·조선 트럼프 수혜)"
        ],
        "caveats": [
          "자막 봇차단으로 본문 구체 종목·수치 미확보 — 방향성만 채택",
          "트럼프 관세정책 변덕 리스크 상존, 테마 추격 금지(룰3)"
        ]
      },
      {
        "id": "skhynix-adr-beneficiaries-shorts",
        "date": "2026-06-21",
        "title": "월가가 줍고 있는 하이닉스 미국 '상장' 수혜주 정체 (쇼츠)",
        "tag": "검증·일부미확인",
        "tickers": [
          "000660.KS",
          "MU"
        ],
        "summary": "⚠️자막 봇차단 — 제목·메타+WebSearch 교차검증만. SK하이닉스 美 ADR 상장 임박, 월가 선매수 논지. [검증]SEC 6월 넷째 주(22~26) 승인 가능성·NDR 완료, 실상장 7월 중하순~8월 중순, 규모 ~$270억(≈40조). 수혜 메커니즘=나스닥·SOX(필반) 편입 시 보유 MU 등 패시브 펀드 리밸런싱 수요(증권업계 동일 논지). [미확인]채널 지목 구체 '수혜주' 종목·수치 미확보. 우리 트리거 '6/22 SK하이닉스 SEC=강세 분수령'과 정합하되, 승인일은 주(週) 단위로 보정 권고.",
        "points": [
          "SK하이닉스 美 ADR 상장 임박, 월가 선매수 논지",
          "[검증] SEC 6월 넷째주(22~26) 승인 가능성·실상장 7~8월·규모 ~40조",
          "[검증] SOX(필반) 편입 시 보유 MU 등 패시브 리밸런싱 수요 발생",
          "[미확인] 구체 '수혜주' 명단 미확보 → 승인일은 주 단위로 보정"
        ],
        "mentions": "SK하이닉스(000660)·마이크론(MU). 美 ADR·SEC·나스닥·SOX 패시브 리밸런싱.",
        "references": [
          "인베스트조선",
          "이데일리",
          "이코노미트리뷴"
        ],
        "caveats": [
          "자막 봇차단 — 본문 수치 미확보, 방향성만",
          "SEC 승인 시점 '6월 넷째주'는 보도 기반 가변(우리 STATE '6/22'는 주 단위로 완화)"
        ]
      },
      {
        "id": "nextweek-points-0622-shorts",
        "date": "2026-06-21",
        "title": "다음주 '투자' 포인트 (06.22~06.26) (쇼츠)",
        "tag": "검증·일부정정",
        "tickers": [
          "MU",
          "^KS11"
        ],
        "summary": "⚠️자막 봇차단 — 제목·메타+WebSearch 교차검증만. 다음주 체크포인트 요약. [검증]MU 실적 6/24(현지) 장마감 후=KST 6/25 새벽, 美 5월 PCE 6/25(현지)·美 1Q GDP 최종치 6/25. [확정]research-feed의 'MU·PCE KST 하루시차' 우려는 PM 교차검증 결과 오인 — PCE는 美 아침 8:30 ET 발표=21:30 KST 같은 날 → MU 새벽+PCE 밤 둘 다 KST 6/25 목. 운영제약상 PCE(21:30)는 폰 미가용 → 6/24 20:50 전 사전 베이킹 필요.",
        "points": [
          "다음주 6/22~26 핵심 = MU 실적·美 PCE·1Q GDP 최종",
          "[검증] MU = 美 6/24 장마감 후 = KST 6/25 새벽",
          "[확정] PCE = 美 6/25 아침 8:30 ET = KST 6/25 21:30 밤 → MU와 같은 KST 6/25 목('하루시차'는 오인)",
          "PCE는 폰 미가용 시간 → 6/24 20:50 전 예약 베이킹 필수"
        ],
        "mentions": "마이크론(MU)·코스피(^KS11). 美 PCE·1Q GDP·MU 실적.",
        "references": [
          "파이낸셜뉴스",
          "서울경제",
          "BEA(PCE 8:30 ET)"
        ],
        "caveats": [
          "자막 봇차단 — 본문 미확보, 일정 교차검증만",
          "research-feed 'KST 하루시차' 플래그는 오인(PCE 밤 발표 가정) → PM 정정"
        ]
      },
      {
        "id": "lg-elec-cooling-robot",
        "date": "2026-06-20",
        "title": "경제사냥꾼 구독자 전용 종목 분석 : LG전자 (신규 쇼츠)",
        "tag": "검증·일부미확인",
        "tickers": [
          "066570.KS"
        ],
        "summary": "★보유 LG전자 직결. 고점 43만원대→21만원대 반토막. 하락 이유=로봇 기대감 선반영, 이제 '테마 아닌 숫자(수주·영업이익)'를 요구하는 구간. 3대 무기 ①AI 데이터센터 냉각(에어컨 공조기술→칠러·냉각수 분배=엔비디아가 머리면 LG는 그 머리 식히는 장치) ②로봇 액추에이터(연 4,500만대 모터 경험→로봇 관절, 완제품 승자 무관 부품은 필수) ③B2B 솔루션(美 정부기관 TAA 인증 디스플레이·클라우드 구독화)+리퍼비시 순환 플랫폼. 2027까지 자사주 ~2조(올해 1조 중 절반 집행)[미확인]. 7/23 실적 전까지 냉각 수주·액추에이터 외부고객 '실제 숫자' 확인이 관건.",
        "points": [
          "고점 43만원대 → 현 21만원대 반토막. 로봇 테마 기대감이 선반영됐다가 '숫자(수주·영업이익) 요구' 구간 진입",
          "무기①: AI 데이터센터 냉각 — 에어컨 공조기술을 칠러·냉각수 분배로 확장(엔비디아의 '열'을 식히는 장치)",
          "무기②: 로봇 액추에이터 — 연 4,500만대 모터 생산 경험을 로봇 관절로(완제품 승자와 무관하게 부품은 필수)",
          "무기③: B2B 솔루션 — 美 정부 TAA 인증 디스플레이·클라우드 구독화 + 리퍼비시 순환 플랫폼",
          "7/23 실적 발표 전까지 냉각 수주·액추에이터 외부 고객사가 실제 숫자로 찍히는지가 재평가 키"
        ],
        "mentions": "LG전자(066570). AI 데이터센터 냉각(칠러·냉각수 분배)·로봇 액추에이터·B2B 솔루션·리퍼비시 순환플랫폼. 엔비디아 AI 서버 발열 테마와 연결.",
        "references": [
          "LG전자 IR(자사주·7/23 실적)"
        ],
        "caveats": [
          "주가 43만→21만·연 4,500만대 모터·자사주 2조 등 수치는 채널 단일출처 → 교차검증 필요(미확인)",
          "냉각 수주·액추에이터 외부 고객사 '실제 숫자'가 안 찍히면 재평가 지연 — 7/23 실적 확인",
          "정훈 룰2(LG전자 손절선 폐기·NVIDIA 냉각 인증 훼손 시에만 매도 검토)와 본 영상 '냉각=핵심 무기' 프레임은 정합. 평단 155,200원 대비로는 아직 위"
        ]
      },
      {
        "id": "anthropic-ipo-proxies",
        "date": "2026-06-20",
        "title": "월가에서 미리 줍고있다는 엔트로픽(Anthropic) 상장 수혜주 정체 (신규 쇼츠)",
        "tag": "검증·일부미확인",
        "tickers": [
          "AVGO",
          "GOOGL"
        ],
        "summary": "Anthropic(클로드 개발사) 기업가치 ~$9,650억(약 1,460조)·5월 OpenAI 역전·빠르면 10월 나스닥 상장설[미확인]. 비상장이라 직접 못 사니 '돈이 흐르는' 프록시 3종: ①아마존 AMZN($80억≈12조 투자 최대주주, 4월 트레이니엄 최대 5GW 계약 — 지분+클라우드+자체칩 3방향) ②★브로드컴 AVGO(4월 엔트로픽+구글+브로드컴 차세대 AI칩 인프라 계약, AI매출 2024 $122억→2027 3배+ 전망) ③SK텔레콤(2023 $1억 투자·통신사 전용 AI 공동개발, 日NTT·대만 청화텔레콤과 AI펀드 추가투자, 지분가치 조단위 추정[미확정]). 트리거=엔트로픽 IPO 일정·공모가 범위 공식화. ★보유 AVGO 직결, GOOGL도 칩 인프라 파트너.",
        "points": [
          "Anthropic 비상장 → 직접 매수 불가, '돈이 흐르는' 프록시로 접근하라는 논지",
          "프록시①: 아마존(AMZN) — $80억(약 12조) 투자 최대주주 + 트레이니엄 5GW 계약(4월), 지분·클라우드·자체칩 3방향",
          "프록시②: ★브로드컴(AVGO) — 엔트로픽+구글+브로드컴 차세대 AI칩 인프라 계약(4월), AI매출 2024 $122억→2027 3배+ 전망",
          "프록시③: SK텔레콤 — 2023 $1억 투자·통신사 전용 AI 공동개발, NTT·청화텔레콤과 AI펀드 추가투자",
          "트리거 = 엔트로픽 IPO 일정·공모가 범위가 공식화되는 순간 세 종목 반응 관찰"
        ],
        "mentions": "Anthropic(엔트로픽·클로드)·아마존(AMZN)·★브로드컴(AVGO)·구글(GOOGL)·SK텔레콤(017670). AI 칩 인프라·클라우드.",
        "references": [
          "아마존 Anthropic 투자 공시",
          "Broadcom AI 매출 가이던스"
        ],
        "caveats": [
          "Anthropic 기업가치 $9,650억·10월 나스닥 상장은 미확인 — IPO는 시장 상황에 따라 지연 가능",
          "SK텔레콤 지분율·평가액 미공개 → '조단위'는 추정치(확정 아님), 유심 보안사고 회복 과정도 체크",
          "★보유 AVGO·GOOGL엔 엔트로픽 IPO가 새 모멘텀 앵글이나, 직접 수혜 크기는 미검증"
        ]
      },
      {
        "id": "battery-ess-rebound",
        "date": "2026-06-20",
        "title": "월가가 보고 있다는 '2차전지' 반등 시나리오 (+종목) (신규 쇼츠)",
        "tag": "검증·방향",
        "tickers": [],
        "summary": "2차전지 소외(포스코홀딩스·삼성SDI·에코프로 하락). 원인=美 전기차 둔화→한국 배터리 점유율 15.6%, 중국 7곳 72%(LFP 저가공세). 월가 반등 앵글=전기차가 아니라 ESS(AI 데이터센터 전력 저장). 모건스탠리 'AI 전력난 해법=가스·원전과 같은 급으로 배터리 저장' 지목, 바클레이즈 AI인프라 400곳 분석해 美 ESS 대장주 순위화. BNEF 글로벌 ESS 신규설치 2025 247GWh→누적 2035 7.3TWh(~8배)[미확인]. 종목: LG에너지솔루션(美 ESS 탈중국 수혜)·포스코홀딩스(리튬·양극재)·삼성SDI(전고체). 전부 미보유 — AI 전력 테마 시야용(보유 GEV·워치 두산E와 인접).",
        "points": [
          "전기차 둔화로 2차전지 소외 — 한국 점유율 15.6% vs 중국 7곳 72%(LFP 저가공세)",
          "월가 반등 앵글 = 전기차가 아닌 ESS(AI 데이터센터 전력 저장). 모건스탠리·바클레이즈가 AI 인프라 밸류체인으로 격상",
          "BNEF: 글로벌 ESS 2025 신규 247GWh → 2035 누적 7.3TWh(~8배) [미확인]",
          "종목: LG에너지솔루션(美 ESS 탈중국)·포스코홀딩스(리튬·양극재)·삼성SDI(전고체) — 전부 미보유"
        ],
        "mentions": "LG에너지솔루션(373220)·포스코홀딩스(005490)·삼성SDI(006400)·에코프로. ESS·AI 데이터센터 전력. 모건스탠리·바클레이즈·BNEF.",
        "references": [
          "모건스탠리(AI 전력 해법)",
          "바클레이즈(美 ESS 순위)",
          "BNEF(ESS 설치 전망)"
        ],
        "caveats": [
          "ESS 설치량(247GWh·7.3TWh)·점유율 수치는 단일출처 방향성 → 교차검증 필요",
          "2차전지엔 적자·증자 부담 중소형주 많음 — 뉴스 하나로 추격 금지",
          "보유·워치 비포함. AI 전력 테마(GEV·두산E) 시야 보강용"
        ]
      },
      {
        "id": "korea-zinc-critical-minerals",
        "date": "2026-06-20",
        "title": "트럼프 수혜주 '고려아연' 폭락 진짜 이유 (신규 쇼츠)",
        "tag": "검증·일부미확인",
        "tickers": [],
        "summary": "고려아연 218만→120만 근처 반토막. 하락 이유=실적+원자재 가격+美 핵심광물 기대+경영권 분쟁(영풍·MBK vs 경영진) 프리미엄이 한꺼번에 붙었다가, 분쟁 장기화가 '비용 우려'로 전환되며 되돌림. 美 테네시 '프로젝트 크루서블' $74억(~11조) 통합 재련소(게르마늄·갈륨·안티모니 탈중국), Fast-41 패스트트랙 지정·부지 실사 단계[방향]. 리스크=美 민주당 진상조사 요구, 경영권 분쟁 워싱턴 로비전. 체크3=①실적 피크아웃 여부 ②분쟁 희석 없이 정리 ③11조 美 프로젝트 본사 부담. 미보유 — 트럼프 핵심광물 공급망 테마 시야용.",
        "points": [
          "주가 218만 → 120만 근처 반토막 — 실적+원자재+美 기대+경영권 분쟁 프리미엄 동시 소멸",
          "경영권 분쟁(영풍·MBK vs 경영진) 장기화 = 처음엔 주가 상방, 길어지자 비용 우려로 하방 전환",
          "美 테네시 '프로젝트 크루서블' $74억(~11조) 재련소 — 게르마늄·갈륨·안티모니 탈중국, Fast-41 패스트트랙",
          "리스크 = 美 민주당 진상조사 요구 + 경영권 분쟁 워싱턴 로비전(정치 리스크 동반)"
        ],
        "mentions": "고려아연(010130)·영풍·MBK. 트럼프 핵심광물 공급망(게르마늄·갈륨·안티모니)·美 전쟁부·상무부.",
        "references": [
          "美 Fast-41 지정 보도",
          "고려아연 경영권 분쟁 보도"
        ],
        "caveats": [
          "프로젝트 크루서블 $74억·Fast-41·부지 실사는 단일출처 → 교차검증 필요(미확인)",
          "정치 리스크(민주당 진상조사)+경영권 분쟁 = 트럼프 수혜와 동시에 변동성 키움",
          "미보유 — 트럼프 핵심광물 테마 시야용 참고만"
        ]
      },
      {
        "id": "jeju-semi-lpddr",
        "date": "2026-06-20",
        "title": "SK하이닉스 'AI 메모리' 수혜주 = 제주반도체 (신규 쇼츠)",
        "tag": "검증·일부정정",
        "tickers": [
          "000660.KS",
          "005930.KS"
        ],
        "summary": "대기업 HBM 집중→저전력 레거시 메모리(LPDDR) 빈자리→제주반도체(080220)가 하이닉스와 메움. LPDDR4X 하이닉스 팹 생산·LPDDR5 2030 양산(검증). 1Q 영업익 671억·이익률 37%·매출 1,805억(+273%)·1년 10배·시총 3.6조(검증). 단 '하이닉스 파운드리 진출' 과대해석 주의(하이닉스=레거시 웨이퍼 공급 입장)·퀄컴/미디어텍 인증·수출+912%는 미확인. 중국 비중 72.9%(검증)=핵심 리스크. ★제주반도체 보유·워치 비포함=추격 대상 아님, 온디바이스 AI(LPDDR) 테마 시야·하이닉스 생태계 보강용.",
        "points": [
          "대기업이 HBM에 집중하며 비는 저전력 레거시 메모리(LPDDR) 자리를 제주반도체가 SK하이닉스와 함께 메우는 구도",
          "LPDDR4X는 하이닉스 팹에서 생산, LPDDR5는 2030 양산 목표 (검증)",
          "1Q 영업익 671억·영업이익률 37%·매출 1,805억(+273% YoY)·주가 1년 10배·시총 3.6조 (검증)",
          "중국 매출 비중 72.9% = 미·중 반도체 갈등 직격 핵심 리스크 (검증)"
        ],
        "mentions": "제주반도체(080220)·SK하이닉스(000660)·삼성전자(005930). 온디바이스 AI / LPDDR 레거시 메모리 테마.",
        "references": [
          "디일렉",
          "와이즈리포트"
        ],
        "caveats": [
          "'하이닉스 파운드리 진출' 프레임은 과대 — 하이닉스는 레거시 웨이퍼 공급 입장",
          "퀄컴·미디어텍 인증, 수출 +912% 수치는 미확인 → 교차검증 필요",
          "제주반도체는 보유·워치 비포함 = 추격 대상 아님. 테마 시야·하이닉스 생태계 보강용으로만 참고"
        ]
      },
      {
        "id": "kospi-9000-nextweek",
        "date": "2026-06-20",
        "title": "코스피 9,000시대 '다음주' 투자 포인트 (주간전망)",
        "tag": "검증",
        "tickers": [
          "005930.KS",
          "000660.KS",
          "MU",
          "^KS11"
        ],
        "summary": "코스피 9,300 돌파했지만 6/18 9천 첫날 상승 98개·하락 806개 = 반도체(삼성·하이닉스) 두 종목 착시. 다음주 캘린더: 6/22 SK하이닉스 美 SEC 승인 가능성 / 6/23 글로벌PMI·MSCI검토 / 6/25(목)=분수령: 새벽 MU 실적(매출보다 총이익률·장기계약 가시성)+밤 美 PCE / 6/26 미시간·러셀. 체크3=MU장기계약·PCE·하이닉스美상장. '완판보다 진짜수요 vs 사재기 봐라'=추격금지 정합.",
        "points": [
          "코스피 9,300 돌파지만 6/18 상승 98 vs 하락 806 → 삼성·하이닉스 두 종목 착시 (쏠림 경고)",
          "다음주 분수령 = 6/25(목) 새벽 MU 실적 + 밤 美 PCE",
          "MU는 매출보다 총이익률·장기계약 가시성을 봐야 한다",
          "체크 3가지: ①MU 장기계약 ②美 PCE ③SK하이닉스 美 상장",
          "'완판보다 진짜수요 vs 사재기를 봐라' = 추격금지 원칙과 정합"
        ],
        "mentions": "코스피(^KS11)·삼성전자(005930)·SK하이닉스(000660)·마이크론(MU). 매크로 이벤트: 美 PCE·글로벌 PMI·MSCI 검토·미시간·러셀.",
        "references": [
          "MSCI 6/23 검토",
          "美 PCE(6/25)"
        ],
        "caveats": [
          "주간 캘린더 일정은 가이던스 — 실제 발표·승인 시점 변동 가능"
        ]
      },
      {
        "id": "mu-target-1500",
        "date": "2026-06-20",
        "title": "목표가 $1,500 제2의 엔비디아 = 마이크론",
        "tag": "검증",
        "tickers": [
          "MU",
          "005930.KS",
          "000660.KS"
        ],
        "summary": "도이체방크 MU $1,000→$1,500(+50%, 6/17 BUY)·씨티 $840→$1,200·TD코웬 $1,500(전부 검증). 직전분기 매출 $238억(예상 $200억)·EPS +30%상회. DRAM 품귀 2028까지(DB). MU=메모리 3등, HBM 엔비디아 발주 2/3 SK하이닉스 → '3등 $1,500 만든 급등기가 1·2등엔 더 세게'. 옵션시장 실적주 ±17% 베팅, 저점比 10배+ 미스 시 급락 리스크. 6/24 MU=한국 메모리 풍향계.",
        "points": [
          "도이체방크 MU $1,000→$1,500(+50%, 6/17 BUY) / 씨티 $840→$1,200 / TD코웬 $1,500 (전부 검증)",
          "직전분기 매출 $238억(예상 $200억)·EPS 예상 +30% 상회",
          "DRAM 품귀 2028까지 지속 전망 (도이체방크)",
          "메모리 3등 MU를 $1,500 만든 급등기 → 1·2등 삼성·하이닉스엔 더 강하게 작용한다는 논지",
          "옵션시장은 실적 ±17% 베팅 — 저점比 10배+ 상태라 미스 시 급락 리스크"
        ],
        "mentions": "마이크론(MU)·삼성전자(005930)·SK하이닉스(000660)·엔비디아. 6/24(현지 6/25 새벽) MU 실적 = 한국 메모리 풍향계.",
        "references": [
          "도이체방크(Weathers, 6/17 BUY)",
          "씨티",
          "TD코웬",
          "Investing.com",
          "SeekingAlpha"
        ],
        "caveats": [
          "저점 대비 10배+ 급등 상태 → 실적 미스 시 급락 리스크",
          "목표가는 sell-side 추정 — 실현 보장 아님"
        ]
      },
      {
        "id": "samsung-cnt-dividend",
        "date": "2026-06-20",
        "title": "정부 밀어줄 고배당주 = 삼성물산",
        "tag": "미확인",
        "tickers": [
          "005930.KS"
        ],
        "summary": "정부 고배당 분리과세 정책→배당확대 기업 자금몰림. 삼성물산=삼성전자·삼성생명 지분 '현금통로'. DS투자증권 올해 DPS +720% 23,500원·내년 4만원대(단일출처 미확인). SMR(에스토니아)·삼성 평택 하이테크 수주 엮임. 삼성물산 미보유 — 정책 테마 참고만.",
        "points": [
          "정부 고배당 분리과세 정책 → 배당확대 기업으로 자금 유입 기대",
          "삼성물산 = 삼성전자·삼성생명 지분 보유한 그룹 '현금통로'",
          "SMR(에스토니아)·삼성 평택 하이테크 수주 테마와 엮임"
        ],
        "mentions": "삼성물산·삼성전자(005930)·삼성생명. DS투자증권 배당 전망.",
        "references": [
          "DS투자증권 (단일출처)"
        ],
        "caveats": [
          "DPS +720% 23,500원·내년 4만원대는 단일출처 미확인 → 교차검증 필요",
          "삼성물산 미보유 — 정책 테마 시야용 참고만"
        ]
      },
      {
        "id": "arm-softbank-flywheel",
        "date": "2026-06-19",
        "title": "젠슨황 61조 들고도 못 산 반도체 독점기업 (ARM)",
        "tag": "검증",
        "tickers": [
          "MU",
          "000660.KS"
        ],
        "summary": "SoftBank ARM 담보 레버리지 플라이휠(~$185억→OpenAI $300억→스타게이트 $5,000억). 손정의 NVDA 전량매도. ARM PER 500배 vs 하이닉스 6~7배·MU 10배 = MU·하이닉스 '가장 싼 AI 길목주'.",
        "points": [
          "SoftBank의 ARM 담보 레버리지 플라이휠: ~$185억 → OpenAI $300억 → 스타게이트 $5,000억",
          "손정의가 NVDA 지분 전량 매도 (검증)",
          "밸류 비교: ARM PER ~500배 vs SK하이닉스 6~7배·MU 10배 → MU·하이닉스가 '가장 싼 AI 길목주'"
        ],
        "mentions": "ARM·SoftBank(손정의)·OpenAI·스타게이트·엔비디아(NVDA)·마이크론(MU)·SK하이닉스(000660).",
        "references": [
          "Reuters (손정의 NVDA 매도)"
        ],
        "caveats": [
          "PER 500배 vs 6~7배 단순비교는 사업모델 차이 무시 — 방향성만 채택"
        ]
      },
      {
        "id": "samsung-national-stock",
        "date": "2026-06-19",
        "title": "삼성그룹이 국민기업인 진짜 이유 ★국장",
        "tag": "검증",
        "tickers": [
          "005930.KS"
        ],
        "summary": "삼성+하이닉스 시총 54%(우선주 57%). 외인 한달 50~57조 순매도→개인 40조 흡수. 진짜 돈=일반 DRAM 판가 +90%(트렌드포스). 하나證 삼성 2Q 92조(가장 공격적). 2028 증설→공급과잉 경고.",
        "points": [
          "삼성+하이닉스가 코스피 시총 54%(우선주 포함 57%) = 쏠림 구조",
          "외인 한 달 50~57조 순매도를 개인 40조가 흡수",
          "실적 동력 = 일반 DRAM 판가 +90% (트렌드포스)",
          "하나증권 삼성 2Q 영업익 92조 = 가장 공격적 추정"
        ],
        "mentions": "삼성전자(005930)·SK하이닉스. 수급: 외국인·개인. 트렌드포스 DRAM 판가, 하나증권 실적 추정.",
        "references": [
          "트렌드포스(DRAM 판가)",
          "하나증권(2Q 추정)"
        ],
        "caveats": [
          "2028 증설발 공급과잉 경고 = 사이클 후반 리스크",
          "하나證 92조는 컨센 상단의 공격적 추정"
        ]
      },
      {
        "id": "skhynix-us-listing",
        "date": "2026-06-19",
        "title": "SK하이닉스 美상장 영향 ★워치",
        "tag": "검증",
        "tickers": [
          "000660.KS"
        ],
        "summary": "ADR SEC 승인 6/22주·8월 거래·조달 최대 $14B·HBM 57%·27년 PER ~6.9배. 밤사이 나스닥서 가격 선결정→코스피 변동성 수입 = 보유 삼성·NVDA·MU 동조성 심화.",
        "points": [
          "SK하이닉스 ADR SEC 승인 6/22주 예상·8월 거래 개시·조달 최대 $14B",
          "HBM 매출 비중 57%·27년 PER ~6.9배",
          "밤사이 나스닥에서 가격 선결정 → 코스피로 변동성 수입",
          "보유 삼성·NVDA·MU와 동조성 심화 (포트 리스크 집중)"
        ],
        "mentions": "SK하이닉스(000660)·삼성전자·엔비디아(NVDA)·마이크론(MU). 나스닥 ADR 상장.",
        "references": [
          "Reuters",
          "CNBC"
        ],
        "caveats": [
          "SEC 승인·상장 시점은 가이던스 — 지연 가능"
        ]
      },
      {
        "id": "tesla-ark-6x",
        "date": "2026-06-19",
        "title": "테슬라 6배 갈 수 있다 (캐시우드)",
        "tag": "검증·시점",
        "tickers": [
          "TSLA"
        ],
        "summary": "ARK 2029 목표 $2,600·로보택시가 가치 90%. 머스크 의결권 ~19.9%. 단 우드 본인 최근 TSLA 일부 차익매도 중인 점 영상 미언급.",
        "points": [
          "ARK 2029 테슬라 목표 $2,600 (현재比 ~6배)",
          "목표가의 가치 90%가 로보택시에서 나온다는 가정",
          "머스크 의결권 ~19.9%"
        ],
        "mentions": "테슬라(TSLA)·캐시 우드/ARK·일론 머스크. 로보택시 테마.",
        "references": [
          "ARK Invest 2029 모델"
        ],
        "caveats": [
          "가치의 90%가 로보택시 = 상용화·규제에 절대적으로 의존하는 강한 가정",
          "우드 본인이 최근 TSLA 일부 차익매도 중인 점을 영상이 미언급 (시점 편향)"
        ]
      },
      {
        "id": "g7-korea-semi",
        "date": "2026-06-19",
        "title": "G7 정상회의 → 한국 반도체 호재",
        "tag": "검증",
        "tickers": [
          "005930.KS",
          "NVDA",
          "000660.KS"
        ],
        "summary": "G7서 美 앤스로픽 AI모델 수출통제(첫 AI모델 금수). '믿을 나라끼리' 반도체 동맹→HBM 독점 한국 몸값↑. 양날=對중국 시장 포기 부담.",
        "points": [
          "G7에서 美 앤스로픽 AI모델 수출통제 = 첫 'AI 모델' 금수 (검증)",
          "'믿을 나라끼리' 반도체 동맹 강화 → HBM 독점 한국 몸값 상승",
          "양날의 검 = 對중국 시장 포기 부담"
        ],
        "mentions": "삼성전자(005930)·SK하이닉스(000660)·엔비디아(NVDA)·앤스로픽. G7·AI 수출통제 정책.",
        "references": [
          "Al Jazeera (6/19)"
        ],
        "caveats": [
          "對중국 매출 비중 큰 종목엔 동맹 강화가 역풍일 수 있음"
        ]
      }
    ],
    "track_record": [
      {
        "date": "6/22(v25)",
        "claim": "KT&G 외인 51.24%·블랙록 6.15%·캐피털 7.21%·1Q 영익 3,645억(+27.6%)·해외궐련 +56.1%",
        "actual": "수치 거의 무오차 (한경 교차검증) — 이번 7편 중 정확도 최고. 신규 워치 후보",
        "verdict": "검증(우수)"
      },
      {
        "date": "6/22(v25)",
        "claim": "LG전자 자사주 '2조원(올해 1조 중 절반)'",
        "actual": "10배 과장 — 실제 2027까지 2,000억·2026 결의 1,000억 중 ~50%(businesspost). 단위(조/억) 오류",
        "verdict": "정정(과장)"
      },
      {
        "date": "6/22(v25)",
        "claim": "SpaceX+테슬라 합병가치 '$4조/6,100조'",
        "actual": "NYT 합병보도·Ives 80~90%는 검증, 단 가치는 과장 — Fortune ~$3.4조",
        "verdict": "검증·일부정정"
      },
      {
        "date": "6/22(v25)",
        "claim": "美정부 지분 인텔 9.9%($89억)·고려아연 테네시 → 삼성·하이닉스 다음 후보",
        "actual": "인텔·고려아연 하드넘버 정확(검증), 단 '삼성·하이닉스 다음 정부지분 후보'는 시장추측·확정근거 없음",
        "verdict": "검증·일부미확인"
      },
      {
        "date": "6/22(v25)",
        "claim": "마이클 버리 삼성 유형장부가 매수론·1Q 영익 57.2조·HBM4 솔드아웃",
        "actual": "전부 사실(디일렉/theguru) — 삼성 코어 강세론 정합",
        "verdict": "검증"
      },
      {
        "date": "6/21",
        "claim": "트럼프 다음 한국 수혜 = 조선·방산·우주",
        "actual": "방향 일치 — 한화오션(美 핵잠)·한화에어로 '트럼프 트레이딩' 부상(한경). 구체 종목명단·수치는 자막 봇차단으로 미확보",
        "verdict": "검증·일부미확인"
      },
      {
        "date": "6/21",
        "claim": "SK하이닉스 美 ADR 임박, SOX 편입 시 MU 패시브 수혜",
        "actual": "일치 — SEC 6월 넷째주 가능성·실상장 7~8월·~40조(인베스트조선/이데일리). 단 '6/22 승인' 단정은 주 단위로 완화",
        "verdict": "검증·일부정정"
      },
      {
        "date": "6/21",
        "claim": "다음주 MU·PCE 캘린더(research-feed 'KST 하루시차' 우려)",
        "actual": "PM 교차검증 = 하루시차는 오인. PCE는 美 아침 8:30 ET=21:30 KST 같은 날 → MU 새벽+PCE 밤 둘 다 KST 6/25 목",
        "verdict": "정정(PM)"
      },
      {
        "date": "6/20",
        "claim": "LG전자 데이터센터 냉각(칠러)·로봇 액추에이터·B2B로 사업축 전환, 주가 43만→21만 반토막",
        "actual": "사업 방향(데이터센터 칠러·로봇 부품 확장)은 일치, 단 43만→21만·연 4,500만대 모터·자사주 2조 등 수치는 단일출처 → 7/23 실적으로 검증 필요",
        "verdict": "검증·일부미확인"
      },
      {
        "date": "6/20",
        "claim": "아마존 엔트로픽 $80억 최대주주·트레이니엄 5GW, 엔트로픽 가치 $9,650억·10월 나스닥 상장",
        "actual": "아마존 Anthropic $80억 투자·트레이니엄 협력 방향 일치, 단 기업가치 $9,650억·10월 상장은 미확인(추정)",
        "verdict": "검증·일부미확인"
      },
      {
        "date": "6/20",
        "claim": "SK텔레콤 엔트로픽 2023 $1억 투자·지분가치 조단위",
        "actual": "$1억 투자·통신 AI 협력 방향 일치, '조단위 평가'는 미공개 추정치(확정 아님)",
        "verdict": "검증·근사"
      },
      {
        "date": "6/20",
        "claim": "고려아연 美 프로젝트 크루서블 $74억(11조)·Fast-41 지정, 경영권 분쟁(영풍·MBK)으로 218만→120만",
        "actual": "경영권 분쟁·美 핵심광물 협력 방향 일치, $74억 규모·Fast-41 지정·부지 실사는 단일출처 미확인",
        "verdict": "검증·일부미확인"
      },
      {
        "date": "6/20",
        "claim": "제주반도체 1Q 영업익 671억·이익률 37%·시총 3.6조·LPDDR4X 하이닉스 팹 생산",
        "actual": "일치 (디일렉·와이즈리포트). 단 '하이닉스 파운드리 진출' 프레임은 과대(하이닉스=레거시 웨이퍼 공급 입장)·퀄컴/미디어텍 인증·수출+912%는 미확인",
        "verdict": "검증·일부정정"
      },
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
      "코리아 디스카운트 해소 = 하이닉스 美 ADR·MSCI(6/23 검토)·정부 배당정책",
      "온디바이스 AI = 저전력 레거시 메모리(LPDDR) 수혜 축 (제주반도체·하이닉스 생태계)",
      "AI 전력저장 ESS = 2차전지 반등 앵글(전기차 아닌 데이터센터 전력), 모건스탠리·바클레이즈 밸류체인 격상",
      "엔트로픽(Anthropic) IPO 프록시 = 아마존·★브로드컴(AVGO)·SK텔레콤",
      "LG전자 = 테마(로봇)→숫자(냉각 수주·액추에이터 고객) 검증 구간, 7/23 실적 분수령",
      "트럼프 핵심광물 공급망 = 고려아연(美 재련소·탈중국), 단 경영권 분쟁·정치 리스크 동반",
      "로봇/피지컬AI·AI전력·SMR (현대차·두산로보·두산E·GEV)"
    ],
    "scorecard": {
      "buckets": {
        "정확": 27,
        "근사": 4,
        "시점": 2,
        "미확인": 5,
        "정정": 6,
        "과장": 0
      },
      "total": 44,
      "accuracy_pct": 70
    }
  },
  "hunter_archive": [
    {
      "date": "2026-06-20",
      "title": "구독자 전용 종목 분석: LG전자",
      "theme": "보유·로봇·데이터센터 냉각",
      "tickers": [
        "066570.KS"
      ],
      "verdict": "검증·일부미확인",
      "takeaway": "고점 43만→21만 반토막, 테마→숫자(수주·영업이익) 검증 구간. 무기=①데이터센터 냉각(칠러) ②로봇 액추에이터 ③B2B. 7/23 실적 분수령. ★보유 LG전자 냉각 thesis 보강.",
      "views": 12718
    },
    {
      "date": "2026-06-20",
      "title": "엔트로픽(Anthropic) 상장 수혜주 정체",
      "theme": "AI 인프라·IPO 프록시",
      "tickers": [
        "AVGO",
        "GOOGL"
      ],
      "verdict": "검증·일부미확인",
      "takeaway": "Anthropic 비상장→프록시 3종: 아마존(최대주주 $80억)·★브로드컴(AVGO, AI칩 인프라 계약)·SK텔레콤($1억 투자). 트리거=IPO 일정 공식화. ★보유 AVGO·GOOGL 새 앵글.",
      "views": 10394
    },
    {
      "date": "2026-06-20",
      "title": "월가가 보는 '2차전지' 반등 시나리오(+종목)",
      "theme": "AI 전력·ESS",
      "tickers": [],
      "verdict": "검증·방향",
      "takeaway": "반등 앵글=전기차 아닌 ESS(AI 데이터센터 전력저장). 모건스탠리·바클레이즈가 AI 밸류체인 격상. 종목=LG엔솔·포스코홀딩스·삼성SDI(미보유). AI 전력 테마 시야.",
      "views": 40778
    },
    {
      "date": "2026-06-20",
      "title": "트럼프 수혜주 '고려아연' 폭락 진짜 이유",
      "theme": "트럼프 핵심광물",
      "tickers": [],
      "verdict": "검증·일부미확인",
      "takeaway": "218만→120만 반토막. 美 테네시 재련소 $74억(11조)·Fast-41[미확인]+경영권 분쟁(영풍·MBK) 프리미엄 소멸. 미보유 테마 시야.",
      "views": 38615
    },
    {
      "date": "2026-06-20",
      "title": "SK하이닉스 'AI 메모리' 수혜주 = 제주반도체",
      "theme": "온디바이스 AI·LPDDR",
      "tickers": [
        "000660.KS",
        "005930.KS"
      ],
      "verdict": "검증·일부정정",
      "takeaway": "대기업 HBM 집중→LPDDR 빈자리 제주반도체. 1Q 영업익 671억·이익률 37%·시총 3.6조[검증]. '하이닉스 파운드리 진출'은 과대. 중국 비중 72.9% 리스크. 미보유.",
      "views": 53295
    },
    {
      "date": "2026-06-20",
      "title": "코스피 9,000시대 '다음주' 투자 포인트",
      "theme": "주간전망",
      "tickers": [
        "005930.KS",
        "000660.KS",
        "MU",
        "^KS11"
      ],
      "verdict": "검증",
      "takeaway": "코스피 9천=삼성·하이닉스 두 종목 착시(6/18 상승98 vs 하락806). 6/25 MU 실적+PCE 분수령. 추격금지 정합.",
      "views": null
    },
    {
      "date": "2026-06-20",
      "title": "목표가 $1,500 제2의 엔비디아 = 마이크론",
      "theme": "메모리 슈퍼사이클",
      "tickers": [
        "MU",
        "005930.KS",
        "000660.KS"
      ],
      "verdict": "검증",
      "takeaway": "도이체방크 $1,500·씨티 $1,200·TD코웬 $1,500. DRAM 품귀 2028까지. 6/24 MU=한국 메모리 풍향계. ★보유 MU 직결.",
      "views": null
    },
    {
      "date": "2026-06-20",
      "title": "정부 밀어줄 고배당주 = 삼성물산",
      "theme": "정책 배당",
      "tickers": [
        "005930.KS"
      ],
      "verdict": "미확인",
      "takeaway": "고배당 분리과세 정책 수혜, 삼성물산=그룹 현금통로. DS투자 DPS +720%[단일출처 미확인]. 미보유 참고만.",
      "views": null
    },
    {
      "date": "2026-06-19",
      "title": "젠슨황 61조 들고도 못 산 반도체 독점기업 (ARM)",
      "theme": "AI 길목·밸류",
      "tickers": [
        "MU",
        "000660.KS"
      ],
      "verdict": "검증·근사",
      "takeaway": "SoftBank ARM 담보 레버리지 플라이휠(~$185억→OpenAI→스타게이트). 손정의 NVDA 전량매도[검증]. ARM PER 500배 vs MU 10배=MU·하이닉스 싼 길목.",
      "views": null
    },
    {
      "date": "2026-06-19",
      "title": "인텔+애플 협력 = 한국 반도체 호재",
      "theme": "파운드리",
      "tickers": [
        "005930.KS",
        "NVDA"
      ],
      "verdict": "미확인",
      "takeaway": "트럼프 애플-인텔 파운드리·테라팹 연계[딜 골격 검증]. 수혜 HPSP·한미반도체 납품은 미확인. 삼성 파운드리엔 양날.",
      "views": null
    },
    {
      "date": "2026-06-19",
      "title": "오늘 코스피 갑자기 하락한 진짜 이유",
      "theme": "수급·지정학",
      "tickers": [
        "^KS11"
      ],
      "verdict": "검증",
      "takeaway": "9,385 신고가→-500p 급락. 원인=벤스 스위스행 연기·호르무즈 합의 흔들+반도체 차익+美 휴장·세마녀. 추격금지 정합.",
      "views": null
    },
    {
      "date": "2026-06-19",
      "title": "삼성그룹이 국민기업인 진짜 이유",
      "theme": "사이클·수급",
      "tickers": [
        "005930.KS"
      ],
      "verdict": "검증",
      "takeaway": "삼성+하이닉스 시총 54%(우선주 57%). 외인 한달 50~57조 순매도→개인 40조 흡수. 진짜 돈=일반 DRAM +90%. 2028 공급과잉 경고. ★보유 삼성.",
      "views": null
    },
    {
      "date": "2026-06-19",
      "title": "SK하이닉스 美상장 영향",
      "theme": "상장·동조성",
      "tickers": [
        "000660.KS"
      ],
      "verdict": "검증",
      "takeaway": "ADR SEC 승인 6/22주·8월 거래·조달 $14B·HBM 57%·27년 PER 6.9배. 나스닥 가격 선결정→코스피 변동성 수입. ★워치.",
      "views": null
    },
    {
      "date": "2026-06-19",
      "title": "테슬라 6배 갈 수 있다 (캐시우드)",
      "theme": "로보택시",
      "tickers": [
        "TSLA"
      ],
      "verdict": "검증·시점",
      "takeaway": "ARK 2029 목표 $2,600·로보택시 가치 90%·머스크 의결권 19.9%. 단 우드 본인 TSLA 일부 차익매도 미언급. ★보유 TSLA.",
      "views": null
    },
    {
      "date": "2026-06-19",
      "title": "G7 정상회의 → 한국 반도체 호재",
      "theme": "정책·동맹",
      "tickers": [
        "005930.KS",
        "NVDA",
        "000660.KS"
      ],
      "verdict": "검증",
      "takeaway": "G7서 美 앤스로픽 AI모델 수출통제(첫 AI금수)[검증]. 믿을나라끼리 반도체 동맹→HBM 한국 몸값↑. 양날=對중국 부담.",
      "views": null
    },
    {
      "date": "2026-06-19",
      "title": "케빈 워시 첫 FOMC 전부 뜯었다",
      "theme": "FOMC·금리",
      "tickers": [
        "NVDA",
        "MU",
        "AVGO"
      ],
      "verdict": "검증",
      "takeaway": "동결·점도표 3.4→3.8·매파 시점/인하 방향 불변[검증]. '반도체만 생존'은 6/17 한정→6/18 SOX +6% 되돌림. 유가 과장 정정.",
      "views": null
    },
    {
      "date": "2026-06-19",
      "title": "MSCI 코스피 역대급 상승장",
      "theme": "수급·MSCI",
      "tickers": [
        "^KS11"
      ],
      "verdict": "검증",
      "takeaway": "MSCI 6/24 시장분류·외환개혁 7/6. 대형 반도체 수혜·중소형 양극화→6/19 현실화(코스닥 -6.33%·LG이노텍 -10.76%). 44조 유입 등은 미확인.",
      "views": null
    },
    {
      "date": "2026-06-18",
      "title": "6/18 투자 포인트 (FOMC 직후)",
      "theme": "FOMC",
      "tickers": [
        "^KS11"
      ],
      "verdict": "검증",
      "takeaway": "FOMC 동결·점도표 3.4→3.8·18명중 9명 인상·워시 점 미기재·성명 130단어[전부 검증]. 메타 -5% vs 필반 +1%(반도체 피신).",
      "views": null
    },
    {
      "date": "2026-06-18",
      "title": "현대차 폭락 진짜 이유",
      "theme": "보유·로봇",
      "tickers": [
        "005380.KS"
      ],
      "verdict": "검증",
      "takeaway": "올해 +150% 후 6월 -18%. 삼성 보스턴다이내믹스 지분인수·이달말 풋옵션[검증, TheBell]. 보스턴 첫 가격표가 분기점·추격금지. ★보유.",
      "views": null
    },
    {
      "date": "2026-06-18",
      "title": "신현송 한은총재 한국경제",
      "theme": "금리·국장",
      "tickers": [
        "^KS11"
      ],
      "verdict": "검증",
      "takeaway": "7/16 금통위 2.50→2.75% 인상 전망·시장 연내 2회[검증]. 인하기→인상기 전환+외인복귀+환율 1500하회=코리아디스카운트 해소.",
      "views": null
    },
    {
      "date": "2026-06-18",
      "title": "FAB10/펩텐의 정체",
      "theme": "쏠림 온도계",
      "tickers": [],
      "verdict": "검증",
      "takeaway": "M7→PEPTEN(+스페이스X·오픈AI·앤스로픽). 상위10=S&P 약 40%(닷컴 41 다음). 집중도 리스크=정훈 M7 다수보유 동반변동 유의.",
      "views": null
    },
    {
      "date": "2026-06-18",
      "title": "ETF 수익률 비밀",
      "theme": "레버리지 경고",
      "tickers": [
        "005930.KS"
      ],
      "verdict": "미확인",
      "takeaway": "단일종목 2배 레버리지 ETF 괴리율 90%[미확인]. 분산형(코스피200·S&P500=VOO)이 안전 도구. 괴리율·LP 자리비움 회피.",
      "views": null
    },
    {
      "date": "2026-06-18",
      "title": "NVDA $25B 채권 → 삼전+닉스 호재",
      "theme": "AI 수요",
      "tickers": [
        "NVDA",
        "000660.KS"
      ],
      "verdict": "정정",
      "takeaway": "$25B·주문 $85B·30년물[검증]. 루빈 HBM4 70% 하이닉스. '하이닉스 영업익 100조'→실제 컨센 250조[정정, 순현금 혼동].",
      "views": null
    },
    {
      "date": "2026-06-18",
      "title": "SK하이닉스 뉴스 3가지 (최다뷰)",
      "theme": "모멘텀",
      "tickers": [
        "000660.KS"
      ],
      "verdict": "검증·미확인",
      "takeaway": "인디애나 보조금 $458M·양산 2028 하반기[검증]. SK그룹 시총·학력제한 폐지는 미확인. 환원 100조 보도. 워치 최강모멘텀.",
      "views": 121000
    },
    {
      "date": "2026-06-18",
      "title": "한국판 머스크(한화 김승연) KAI 콕",
      "theme": "방산",
      "tickers": [],
      "verdict": "정정",
      "takeaway": "한화 KAI 9.04% 2대주주·경영참여[검증]. 자막 '김승현'→실제 김승연[정정]. 워치 한화에어로 간접연관. 증자 희석 리스크.",
      "views": null
    },
    {
      "date": "2026-06-18",
      "title": "美+日 100조 SMR → 한국 원전주",
      "theme": "원전·SMR",
      "tickers": [],
      "verdict": "정정",
      "takeaway": "日 대미 100조 SMR·뉴스케일 $25B[검증]. 진짜 수혜=두산에너빌리티(공급망). 자막 '두산로보틸리티'=치명 오류[정정]. ★워치 두산E.",
      "views": null
    },
    {
      "date": "2026-06-18",
      "title": "스페이스X 매수 타이밍",
      "theme": "우주",
      "tickers": [],
      "verdict": "검증",
      "takeaway": "목표가 $63~$190(CFRA·모닝스타·오펜하이머)[검증, v17 과장 $330 사라짐]. 6월말 지수편입+8월 락업해제 주시. ★워치 SPCX.",
      "views": null
    },
    {
      "date": "2026-06-18",
      "title": "미국 뉴스 3가지 (FOMC 전)",
      "theme": "매크로",
      "tickers": [],
      "verdict": "미확인",
      "takeaway": "호르무즈 리스크 가격표. 마이크 버리 SpaceX 매도시각(적자 $49억)·한국개미 1.23조 순매수[미확인]. SpaceX 양면 디베이트 소재.",
      "views": null
    },
    {
      "date": "2026-06-17",
      "title": "엔비디아 37조 빚투가 역대급 호재",
      "theme": "AI 수요",
      "tickers": [
        "NVDA"
      ],
      "verdict": "검증",
      "takeaway": "NVDA $25B 채권·주문 $85B(>3배)·30년물 +65bp·무디스 AA1[전부 검증, WSJ/SEC]. 4대 리스크 균형 제시. 수치정확도 우수.",
      "views": null
    },
    {
      "date": "2026-06-17",
      "title": "6/19 美-이란 종전 후 주가추세",
      "theme": "종전",
      "tickers": [],
      "verdict": "검증·방향",
      "takeaway": "종전 수혜=돈 흐름 순서(유가↓→항공·화학→은행→해운→건설). $300B 재건기금=걸프·민간 펀딩. '옥석 구분 구간'·추격경계.",
      "views": null
    },
    {
      "date": "2026-06-17",
      "title": "이재용 AI시대 새 사업 (AX)",
      "theme": "삼성 AX",
      "tickers": [
        "005930.KS"
      ],
      "verdict": "검증",
      "takeaway": "삼성 67개 전 관계사 AI 전면도입(AX) 6월 본격화[검증]. ★보유 삼성 장기 시야.",
      "views": null
    },
    {
      "date": "2026-06-17",
      "title": "연준이 다시 금리 인하할 수 있는 이유",
      "theme": "금리",
      "tickers": [],
      "verdict": "검증",
      "takeaway": "5월 CPI 4.2%의 60%+가 에너지(근원 2.9%). 동결+easing 삭제(매파 포장)이나 방향 인하→신흥국 유입 호재. core PPI 4.9% 언급=실제 5.1%[정정].",
      "views": null
    },
    {
      "date": "2026-06-17",
      "title": "Warsh 첫 FOMC가 방향 결정",
      "theme": "FOMC 예고",
      "tickers": [],
      "verdict": "검증",
      "takeaway": "FOMC 동결 97~98%·성명서 '추가 조정' 삭제 여부·점도표 관전. 연내 인상확률 79→61%. 점도표 매파/워시 강성 시 변동성↑[적중].",
      "views": null
    },
    {
      "date": "2026-06-17",
      "title": "은행들 채무탕감 서두르는 이유",
      "theme": "정책",
      "tickers": [],
      "verdict": "검증·방향",
      "takeaway": "한국형 배드뱅크(7년+연체·5천만원 이하) 확대[방향].",
      "views": null
    },
    {
      "date": "2026-06-17",
      "title": "스페이스X 2배 가능",
      "theme": "우주",
      "tickers": [],
      "verdict": "정정",
      "takeaway": "공모 $135→첫날 $160(+19%). 오펜하이머 $190·모닝스타 $63[검증]. '뉴스트리트 $330(2배)'=실제 $165[정정]. 지수편입 패시브 수급 강세논리.",
      "views": null
    },
    {
      "date": "2026-06-17",
      "title": "엔캐리 청산 신호",
      "theme": "매크로",
      "tickers": [],
      "verdict": "검증",
      "takeaway": "BOJ 0.75→1.0%(약 30년만 최고). 2024.8.5 트라우마 환기. 단 예고된 인상·점진→'서서히 조임'. 달러엔 160 하회 관전.",
      "views": null
    },
    {
      "date": "2026-06-17",
      "title": "6/17 오늘 투자 포인트",
      "theme": "일일",
      "tickers": [
        "^KS11"
      ],
      "verdict": "검증·시점",
      "takeaway": "이란 MOU·건설 급등(+7%)·필반 -5.7% vs 다우 ATH=순환매. '외인 3거래일 순매수'→6/17 종가엔 -9,923억 순매도 전환[시점변화].",
      "views": null
    },
    {
      "date": "2026-06-15",
      "title": "종전 이후 돈의 방향",
      "theme": "종전",
      "tickers": [
        "NVDA",
        "MU",
        "005930.KS"
      ],
      "verdict": "검증",
      "takeaway": "종전=리스크프리미엄 제거→성장주·반도체로 자금 이동. 이란 6/19 서명·유가 -3%·SpaceX $160.95[검증]. NVDA·MU·삼성 강세 보강.",
      "views": null
    },
    {
      "date": "2026-06-15",
      "title": "종전 수혜주",
      "theme": "종전",
      "tickers": [],
      "verdict": "정정",
      "takeaway": "항공 수혜·정유 역수혜·반도체. '골드만 코스피 12,000'은 자막오류→실제 9,000(시티 8,500)[정정].",
      "views": null
    },
    {
      "date": "2026-06-15",
      "title": "최태원 이혼 → 하이닉스",
      "theme": "지배구조",
      "tickers": [
        "000660.KS"
      ],
      "verdict": "미확인",
      "takeaway": "재산분할 시 지분매각 우려[미확인]. 미보유라 영향 낮음.",
      "views": null
    },
    {
      "date": "2026-06-14",
      "title": "월가가 5년 안에 한국 먹여살릴 다음 산업 = 로봇/피지컬AI",
      "theme": "로봇·피지컬AI",
      "tickers": [
        "005380.KS",
        "454910.KS"
      ],
      "verdict": "검증",
      "takeaway": "골드만 휴머노이드 2035 $380억(6배 상향)·HL만도 목표 109k→상한가[검증]. 한국 로봇밀도 1위[검증]·2~4위 순위[정정]. ★보유 현대차·두산로보.",
      "views": null
    },
    {
      "date": "2026-06-14",
      "title": "삼전·닉스 3배 레버리지 LSE 상장",
      "theme": "레버리지",
      "tickers": [
        "005930.KS",
        "000660.KS"
      ],
      "verdict": "검증",
      "takeaway": "단일종목 3배 ETP 글로벌 최초, 원화선물 통해 코스피 변동성 전이 가능→본주·분산이 안전.",
      "views": null
    },
    {
      "date": "2026-06-14",
      "title": "SpaceX ETF TOP3",
      "theme": "우주",
      "tickers": [],
      "verdict": "검증·미확인",
      "takeaway": "SPCX $135 공모·$750억 조달[검증]. ETF 티커[미확인]. ★워치 SPCX.",
      "views": null
    },
    {
      "date": "2026-06-13",
      "title": "다음 주(6/15~19) 진짜 포인트",
      "theme": "주간전망",
      "tickers": [],
      "verdict": "검증",
      "takeaway": "FOMC 점도표+워시 데뷔·BOJ·네마녀·대미투자법 클러스터[검증]. BOJ '인상확률 94%'[과장]. 대미투자 원전 거론(확정 아님) 신중.",
      "views": null
    }
  ],
  "flows": {
    "_comment": "코스피 투자자별 순매수(억원). 보고서에 문서화된 확정값만 시드. 보고서마다 kr-market-desk가 당일 외인/기관/개인 확정 시 series에 prepend(최신은 뒤). 추측 금지 — 미확인 일자는 null.",
    "updated": "2026-06-22",
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
      },
      {
        "date": "2026-06-22",
        "foreign": -25463,
        "inst": 3038,
        "indiv": 21505,
        "note": "외인 2거래일 연속 순매도(−2.55조, 통상치 2배+ → FTSE/MSCI 리밸런싱 추정·배경 미확인). 개인 +2.15조 전량소화·SK하이닉스 주도 반도체 쏠림으로 코스피 9,114.55 종가 사상최고. 외인 재유입 분수령=실패(신중)"
      }
    ]
  },
  "reports": [
    {
      "id": "report_v25b_2026-06-22_exec",
      "file": "docs/reports/report_v25b_2026-06-22_exec.md",
      "title": "정훈 PORTFOLIO DESK · v25 부록(Addendum) · 2026-06-22 (월) — 폰 거래창 집행 지시서",
      "date": "2026-06-22",
      "version": 25,
      "kind": "보고서",
      "preview": "[STATE SNAPSHOT v25b(부록) 2026-06-22]",
      "content": "# 정훈 PORTFOLIO DESK · v25 부록(Addendum) · 2026-06-22 (월) — 폰 거래창 집행 지시서\n\n> v25 아침 풀브리핑 이어받기. **국장 마감 확정치 기준 '지금 뭘 누를지' 행동 중심.** 풀 데스크 X.\n> 데이터: **KR 6/22(월) 종가 확정 / US 6/18 종가(오늘밤 22:30 재개=선물 하락) / USD-KRW 1,538.84**\n> 폰 가용 **17:30~20:50 KST**. 국내 실시간 거래창 = 시간외단일가 **17:30~18:00**.\n\n---\n\n## 0. 🎯 한 줄 집행 결론\n\n**오늘 폰창 = 관망(살 것·팔 것 없음).** 아침 보고서가 \"강세 분수령\"으로 지목한 **외인 재유입은 실패** — 외인 6/22 **−2조5,463억 순매도(2거래일 연속)**. NAVER 1차 매수 조건(외인 재유입 확인) **미충족 → 보류 확정.** 미국은 오늘밤 재개 갭(룰7)·3차 동결로 신규 예약 없음. MU 절반차익 베이킹은 **내일(6/23) 저녁.**\n\n---\n\n## 1. 국장 종가 종합 (6/22 월, 확정)\n\n- **코스피 9,114.55 (+0.69%, +62.13p) — 종가 사상 최고 / 코스닥 968.40 (+0.19%).** 장초반 8,950선(−1.08%)까지 밀렸다가 SK하이닉스 주도 반도체 강세로 반전.\n- **🔑 외국인 코스피 −2조5,463억 순매도(개인 +2조1,505억·기관 +3,038억).** 6/19(−3,800억)에 이어 **2거래일 연속 순매도.** 규모가 통상치(약 1조)의 2배+ → **FTSE/MSCI 리밸런싱·만기 청산 추정이나 배경은 기사 미명시(미확인).**\n  - **역설 = 외인 대량매도에도 지수 최고치.** 매도 물량을 **개인(+2.15조)·기관이 전량 소화**, SK하이닉스 쏠림이 지수를 끌어올림. → **\"외인=메인 엔진\" 핵심 신호는 흔들린 상태(신중 가중). 분수령은 6/23 이후 재확인.**\n- **🏆 SK하이닉스 시총 1위 등극 — 약 25년 만에 삼성전자 첫 추월.** 종가 **2,919,000원(+5.61%)**, 시총 2,080조 vs 삼성 2,067조(보통주 기준). 반도체 슈퍼사이클 + ADR 기대 촉매. *(삼성 우선주 포함 시 삼성그룹 우위.)*\n- **SK하이닉스 美 ADR**: 6/22 시점 **SEC 정식 승인 헤드라인 아직 미발표**(6월 넷째주 승인 가능성 보도). 메리츠 8월 상장·목표 295만원. 시장은 선반영 중.\n- **로테이션**: 반도체 대형주+장비(원익IPS +10.58%·테스 +10.35%) 쏠림 강세 / 현대차·2차전지·보험 약세.\n\n### 국내 보유·워치 종가 (6/22 확정)\n| 종목 | 종가 | 당일 | 비고 |\n|---|---|---|---|\n| **삼성전자** 005930 | 353,500원 | −0.14% | SK하이닉스에 시총 1위 내줌 |\n| **LG전자** 066570 | **227,500원** | **+7.57%** | 보유 최강세(그룹 차익 되돌림 반등) |\n| **두산로보** 454910 | 100,400원 | −1.38% | 모멘텀, 관망 |\n| **현대차** 005380 | 581,000원* | **−5%대 급락** | 비반도체 로테이션 약세 (*Yahoo 581k / 기사 ~602k −5.79%, 방향 일치·종가 토스 확정 권고) |\n| **NAVER** 035420 | 222,000원 | −3.27% | **매수존(225~235k) 아래로 이탈** |\n| SK하이닉스 000660 | 2,919,000원 | +5.61% | 시총 1위·ADR 촉매 |\n| 두산에너빌리티 034020 | 94,200원 | −3.78% | 10만 하회, 추격금지 |\n| 원익IPS 240810.KQ | 172,500원 | +10.58% | 장비 급등(추격금지) |\n| 테스 095610.KQ | 183,400원 | +10.35% | 장비 급등(추격금지) |\n\n> ⚠️ 삼성전기·LG이노텍·한화오션·한화에어로·KT&G = market_data 미수신 → **6/22 종가 미확인**(인용 전 재조회).\n\n## 2. 트리거 점검 (triggers.py)\n\n- 🟢 **안전핀 코스피 7,500**: 현 9,115 = **+21.5% 버퍼, 비발동.** (2차 8,000도 +13.9% 미달.)\n- 🟡 **NAVER 매수존 225~235k**: 종가 **222,000원 = 매수존 아래로 이탈.** + 정리후보 + **외인 재유입 조건 실패** → **3중으로 매수 보류.**\n- 🟢 두산에너빌리티 10만 돌파: 94,200원, 미발동(추격금지).\n- 📅 **FOMC 3차 트랜치**: 매파 확정 → **동결 유지**(비둘기 전환/META 7/29/외인 복귀 중 하나까지).\n- 📅 **MU 절반차익**: 6/25 새벽 실적 → **6/23(내일) 저녁 폰창 사전 베이킹**(오늘 아님).\n\n**→ 발동된 매수 트리거 없음. 안전핀도 비발동(지수 최고치). 신규 집행 명분 0.**\n\n---\n\n## 3. ★ 토스 집행안 — 2블록\n\n### (A) 국내 시간외단일가 17:30~18:00 → **관망(무집행)**\n\n| 종목 | 액션 | 이유 |\n|---|---|---|\n| **NAVER** | 🚫 **매수 보류** | 외인 재유입 분수령 실패(2일연속 −2.55조)·종가 222k로 매수존 이탈·정리후보. 3중 미충족 |\n| 삼성전자·LG전자·두산로보·현대차 | ✅ **전량 홀딩** | 신규 매수/트림 명분 없음. LG전자 +7.57% 강세나 보유 1주=분할 트림 불가, 코어 홀딩 |\n| 워치(SK하이닉스 등) | 🚫 **진입 안 함** | SK하이닉스 ADR 상장 전 진입금지(영구교정)·반도체 +5~10% 추격금지(룰4) |\n\n> **국내 시간외 결론: 누를 것 없음.** 현금 624,771원 전액 보존. 국장은 소수점 불가 → 소액 매수도 성립 안 함.\n\n### (B) 미국 지정가 예약 (20:50 전 세팅 → 22:30 자동집행) → **예약 없음**\n\n- **오늘밤 美 재개 = 하락 출발 + 누적 갭**: 선물 S&P −0.74%·나스닥 −1.20%·VIX 16.78. 금 6/19 준틴스 휴장+주말 → **이틀+주말 뉴스 한꺼번에 반영 = 시초 변동성.** → **룰7(동시휴장 갭) 신규 진입 보류.**\n- **3차 트랜치(META·AVGO)**: FOMC 매파로 **동결 유지.** 오늘 예약 안 함.\n- **MU 절반차익**: 실적 = 美 6/24 장마감 후 = **KST 6/25 새벽**(폰 미가용). 베이킹은 **내일 6/23 저녁 폰창**에 소수점(시장가) 절반(약 0.02주) 예약. **오늘 아님.**\n- **오늘밤 야간 이벤트 없음**(MU·PCE 모두 6/25) → **조건부 베이킹 대상 없음.**\n\n> **미국 예약 결론: 신규 예약 0건.** 보유 11종목 홀딩. 재개 갭은 구경만.\n\n---\n\n## 4. 강세 / 신중 한 줄\n\n- **강세**: 외인이 −2.55조 던졌는데도 개인·기관이 전량 받아 코스피 종가 신고가 — 국내 수급 체력 확인. SK하이닉스 시총 1위·ADR 임박 = 코리아 디스카운트 해소 서사 진행. MU 슈퍼사이클(GM 81%·sold out) 그대로.\n- **신중**: 외인 2일연속 대량 순매도 = \"외인=엔진\" 신호 균열. **받침대가 개인 빚투 38조(사상최고)·연기금**인데 **7월 국민연금 리밸런싱 재개 시 그 받침대 제거**(경제사냥꾼① 검증) → 7월이 외인 흡수력 진짜 시험대. 오늘밤 美 재개 갭·이란 재긴장·유가 반등도 그대로. **베팅 늘릴 구간 아님.**\n\n## 5. 경제사냥꾼 6/22 신규 3편 (자막 확보 ✅)\n\n| # | 영상 | 핵심 | 분류 | 연결 |\n|---|---|---|---|---|\n| ① | 국민연금 코스피 9천서 매도 진짜이유 | 6월 리밸런싱 유예 종료→7월 룰 재적용 기계적 매도. 국내목표비중 14.9→20.8% 상향(검증)·바클레이즈 7월 월 7~8조 재개(검증). **받침대=빚투 38조 사상최고** | [검증]/일부[미확인] | 외인 분수령·안전핀 직결. **7월=외인 흡수력 시험대** |\n| ② | 6/22 투자 포인트(쇼츠) | 미·이란 스위스 회담 진전·충돌, 원달러 야간 1,540 돌파, 6/25 PCE·MU 컨센 매출$34.4B·EPS$19.7 | [검증]/[미확인] | MU 베이킹·PCE 트리거 정합 |\n| ③ | 코스닥 주도주 정체(쇼츠) | **한울반도체**(자막 '하늘'은 오류)-무라타 MLCC 마운터 MOU 2연상한. MLCC 8년만 슈퍼사이클·무라타/삼성전기 가동률 90%+ | [검증]/일부[미확인] | **삼성전기(워치) 테마 보강.** 한울은 추격 부적합(룰3) |\n\n- **종합**: 3편 모두 정훈 대기 트리거(외인·MU·PCE) **방향성 재확인** 성격, 신규 액션 트리거 없음. 수치 과장 이번엔 양호. **신규 리스크 모니터 = 빚투 38조 반대매매 도미노 + 7월 국민연금 받침대 제거.**\n\n---\n\n## 6. 평가손익·현금 (원가 고정 기준, 6/22 종가)\n\n- **국내 +176,200원** / **미국 +$67.50(≈+103,875원)** → 주식 합 **+280,075원**(환차익 미반영). 환차익 반영 추정 ≈ **+598,876원**.\n- **현금 624,771원**(트랜치 3분할 전부 미집행, 전액 보존). 총자산 ≈ **8,524,574원**. *(실손익 정본 = 토스.)*\n\n---\n\n[STATE SNAPSHOT v25b(부록) 2026-06-22]\n집행: **오늘 폰창 관망 — 국내 시간외 무집행·미국 예약 0건.** NAVER 1차 매수 보류 확정(외인 재유입 실패+매수존 이탈+정리후보 3중).\n국장 종가: 코스피 9,114.55(+0.69%, 사상최고)·코스닥 968.40(+0.19%). **외인 −2조5,463억(2일연속 순매도)·개인 +2.15조·기관 +3,038억.** SK하이닉스 시총 1위 등극(2,919,000 +5.61%, 25년만 삼성 추월).\n보유변동: 없음. 현금 624,771원 전액 보존.\n미장: 오늘밤 22:30 재개 = 선물 S&P −0.74%·나스닥 −1.20%·VIX 16.78 하락출발. 룰7 신규진입 보류, 3차 동결.\n신규: 경제사냥꾼 6/22 3편(국민연금 7월 받침대 제거·빚투 38조 / MU·PCE 정합 / 한울반도체-무라타 MLCC=삼성전기 보강).\n대기 트리거: ①외인 재유입 6/23+ 재확인(분수령 1차 실패) ②6/23 저녁 MU 절반차익 베이킹 ③6/25 MU실적+PCE 더블 ④안전핀 7,500(현 9,115, 비발동) ⑤7월 국민연금 리밸런싱 재개(받침대 제거 주시)\n영구교정: 없음(v25 이란·LG전자 자사주 정정 유효).\n다음: v26(다음 풀브리핑) / 내일 6/23 저녁 = MU 베이킹 실집행일.\n\n*투자 자문 아님 · 모든 레벨은 분석 참고 · 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v25_2026-06-22",
      "file": "docs/reports/report_v25_2026-06-22.md",
      "title": "정훈 PORTFOLIO DESK · v25 · 2026-06-22 (월) 아침 풀 브리핑",
      "date": "2026-06-22",
      "version": 25,
      "kind": "보고서",
      "preview": "보유 정량 지형 (스코어순)",
      "content": "# 정훈 PORTFOLIO DESK · v25 · 2026-06-22 (월) 아침 풀 브리핑\n\n> 데이터: **US=6/18(목) 종가(6/19 준틴스 휴장 → 간밤 美 세션 없음) / KR=6/22(월) 개장 직후 잠정 / USD-KRW 1,530.36**\n> 이번 버전 핵심 = **① 오늘밤 美 재개(선물 하락·갭) 셋업 ② 이란 재긴장(메모 \"휴전 완료\"와 상충 → 교정) ③ 6/22 외인 재유입 = 강세 분수령(장중 미확정·마감 후 확정) ④ 경제사냥꾼 신규 7편 자막 전량 확보 ⑤ 오늘 폰 거래창 집행 후보.**\n\n## 변경점 (v24 대비)\n\n- 🕐 **오늘은 거래일(월)**: 국장 09:00 개장 중, 미장은 **오늘밤 22:30 KST 재개**(금 6/19 준틴스 휴장 + 주말 → 간밤 美 거래 없음, 6/18 종가가 마지막). v24의 \"거래 0건\"에서 → **폰 거래창(17:30~20:50) 가동.**\n- 🔴 **오늘밤 美 재개 = 하락 출발 셋업**: 일요일밤 美 선물 S&P −0.74%·나스닥 −1.20%·다우 −0.49%·러셀 −0.91%, **VIX 16.78(+2.3%).** 6/18 SOX +6.42% 신고가가 **시초 되돌림** 위험(휴장 이틀+주말 누적 갭).\n- ⚠️ **이란 재긴장 → 영구교정**: 메모 \"이란 휴전 MOU 전자서명 완료(유가 $65)\"와 **외신이 상충** — 트럼프 추가 군사행동 경고·밴스 부통령 스위스 협상 개시·유가 반등(WTI ~$78 +3%·브렌트 $80~81). **\"휴전 완료\" 단정 금지, '재긴장·미확정' 국면.** (2차 트랜치 트리거 \"이란 결렬\" 조건도 재검토 대상.)\n- 🔑 **6/22 외인 재유입 = 강세 분수령(장중 미확정)**: 6/19 외인 −3,800억 순매도(FTSE 리밸런싱) 후 복귀 여부 = 핵심 신호. 데이터센터 IP·장초반이라 **수급 집계 장중 미확정 → 마감 후 확정.**\n- 🎬 **경제사냥꾼 신규 7편 자막 전량 확보**(tv 클라이언트 우회 성공 — v24 봇차단 개선). 신규 쇼츠 6편 + 트럼프 영상 자막 보강. **KT&G = 신규 워치 후보 검토.** ⚠️ LG전자 자사주 \"2조원\"은 **10배 과장 → 실제 2,000억**(정정).\n- 📅 **MSCI 연례 시장분류 = 6/23 발표**(macro 교차검증). MU 실적 = **美 6/24 16:00 ET 장마감 후 = KST 6/25 새벽 ~05:00 확정**(외신 \"6/24\"는 美 발표일 기준).\n- 시세·보유·현금(624,771원)·스코어·별점 **무변동**(美 신규 세션 없음, US 6/18 종가 유효 / KR 6/22 잠정).\n\n---\n\n## 1. 시장 — 국장 / 미장\n\n### 🇰🇷 국장 (6/22 월 개장 직후 · 잠정)\n- **오늘의 분수령 = 외인 재유입 여부.** 6/19 외인 −3,800억(FTSE 리밸런싱 기계적 매물) → 6/22 복귀 시 강세 재확인 / 재차 순매도 시 \"외인=엔진\" 논지 약화 신중경보. **장초반 수급 집계 장중 미확정**(데이터센터 IP 한계) → **마감 후 KRX 확정 필요.**\n- **반도체 내 차별화 출발**: SK하이닉스 +2.94%(ADR 기대)·삼성전기 +3.18% 강세 vs 삼성전자 −2.34%·소부장(원익IPS −4.41%·테스 −5.62%) 차익. 현대차 +2.0%가 지수 방어.\n- **LG그룹주 차익 출회 지속**: LG전자·LG이노텍 6/19 낙폭(−7.44%/−10.76%) 반영 — ⚠️ Yahoo prev_close가 6/19 기준이라 **6/22 자체 일중 등락은 마감 후 재검증**(미확정).\n- **SK하이닉스 美 ADR**: 복수 보도(메리츠·인베스트조선·이데일리 일치) — **SEC 6월 넷째 주(6/22 주) 승인 가능성, 실상장 7~8월, 규모 ~$140억(≈21조).** 승인 헤드라인 = 코리아 디스카운트 해소 촉매.\n- ⚠️ 코스피·코스닥 6/22 실시간 지수는 Yahoo 미반영(9,052·코스닥 −6.33%는 각각 6/19 종가/오류값) → **6/22 지수 잠정 미확인, 마감 후 확정.**\n\n### 🇺🇸 미장 (간밤 신규 세션 없음 / 6/18 종가 + 오늘밤 재개 셋업)\n- **⚠️ 금 6/19 준틴스 전체 휴장 + 주말 → 간밤(일→월) 美 거래 부재. 유효 종가 = 6/18(목).** market_data.py 반환값도 전부 6/18 종가.\n- **6/18 종가 = FOMC 매파 셀오프 완전 되돌림 확인**: S&P 7,500.58(+1.08%)·나스닥 26,517.93(+1.91%)·다우 51,564.70(+0.14%)·**SOX 14,341.78(+6.42% 신고가)**. Intel+Apple 협업 칩 랠리 촉매, **반도체 단독 주도**(다우 +0.14% 구경제 소외).\n- **오늘밤(월 22:30 KST) 재개 = 하락 출발 + 누적 갭**: 선물 S&P −0.74%·나스닥 −1.20%(반도체 차익)·VIX 16.78. 트럼프 이란 군사압박 → 유가 반등·금 −2%. **휴장 이틀+주말 뉴스 한꺼번에 반영 = 시초 변동성 확대 주의.**\n\n| 지수 | 6/18 종가 | 6/18 등락 | 오늘밤 선물(잠정) |\n|---|---|---|---|\n| S&P500 | 7,500.58 | +1.08% | 🔴 −0.74% |\n| 나스닥 | 26,517.93 | +1.91% | 🔴 −1.20% |\n| 다우 | 51,564.70 | +0.14% | 🔴 −0.49% |\n| 필라델피아반도체(SOX) | 14,341.78 | +6.42%(신고가) | (반도체 차익 되돌림 위험) |\n\n## 2. 섹터 — 반도체·AI (이번주 핵심: MU 6/25 새벽)\n\n- **MU 실적 = 이번주 최대 이벤트.** $1,133.99(원가 +51.4%). **美 6/24(수) 장마감 16:00 ET = KST 6/25(목) 새벽 ~05:00**(컨퍼런스콜 06:00경, 폰 미가용). 회사 가이드 매출 $33.5B±0.75·GM ~81%·non-GAAP EPS $19.15±0.40 < Street 컨센(매출 $34.5~34.7B·EPS $19.7~20.0) = **비트 기대 선반영.** HBM \"next several quarters sold out\"·HBM4 NVIDIA/AMD 인증 완료. **GM 81% 유지 여부 = 사이클 건강도 핵심 시그널.** 목표가 줄상향(Stifel $1,500·Wedbush $1,300·RBC $1,200·MS $1,050) but 평균 TP 출처별 $755~1,202 분산 = 사이클 정점 패턴. → 현재가가 다수 평균 TP 상회 = **sell-the-news 헤지로 절반차익 합리(6/23 저녁 베이킹).**\n- **삼성전자**(6/22 −2.34%): HBM4 NVIDIA Rubin qual 통과(3사)·AMD MI400 공급·일반DRAM 판가 1Q +90~95%/2Q +58~63%(TrendForce). 단 Rubin HBM4 점유율 25~30%로 SK하이닉스(60~70%) 후순위. ⭐5/87 유지.\n- **NVDA**(스코어100)·**AVGO**(83)·**ANET**(78): 6/18 종가 유지. ANET 목표 줄상향(KeyBanc·TD Cowen $200), 단 AVGO 칩 공급이 26년 출하 제약. 오늘밤 선물 −1.2% → 반도체 시초 약세 가능.\n- **워치**: SK하이닉스(ADR·HBM 58%·PER 6~7배 vs 필반 27배 = 밸류 디스카운트)·삼성전기(MLCC 초호황·PER 과열)·원익IPS(키움 TP 16만, 26E 영익 +199%)·테스.\n- ⚠️ **집중도 = 최대 리스크**: 보유 MU+삼성 + 워치 SK하이닉스 = DRAM/HBM **단일 사이클 3중 노출.** 6/25 MU 1건이 국장 삼성·하이닉스 동반 갭 유발 가능.\n\n## 3. 매크로 데스크\n\n- **환율**: USD/KRW **1,530.36**(6/19 1,529.89 대비 보합). DXY 100.7 부근. 약원화 지속 = 6/22 외인 재유입엔 미풍.\n- **금리**: 美10Y 4.46~4.50%(6/18 기준). FOMC 매파 동결(점도표 2026 3.4→3.8). **CME FedWatch: 연내 인상 확률 ~77%**(한 달 전 24%), 10월 25bp 1회 프라이싱.\n- **유가**: ⚠️ **출처 충돌·미확인** — 6/19 종가 브렌트 $80.57·WTI $77.54(美-이란 회담 무산 반등). 6/20 호르무즈 봉쇄 선언 vs 별도 출처 \"재개통·디스럽션 종료\". **메모의 \"$65\"는 외신 미확인** → 근시일 레인지 $75~$82 추정. 에너지가 PCE 상방 압력.\n- **한국**: 한은 **7/16 금통위 2.50→2.75% 인상 전망**(5월 CPI +3.1% 2024.3來 최고·유가 상방). ※ 한은은 점도표 발표 안 함.\n\n### 이벤트 캘린더 (오늘~6/26 · KST · 폰 가용 17:30~20:50)\n| 날짜 | 이벤트 | KST 시각 | 폰 |\n|---|---|---|---|\n| 6/22(월) | 국장 외인 재유입 분수령 / SK하이닉스 SEC 주 / 美 재개(갭) | 09:00~ / 22:30 | 17:30~18:00 단일가만 |\n| 6/23(화) 새벽 | **MSCI 연례 시장분류 발표**(한국 선진국 관찰대상) | 새벽 | ❌ |\n| **6/23(화) 저녁** | **MU 절반차익 사전 베이킹**(폰 가용창, 소수점 시장가) | 17:30~20:50 | ✅ |\n| 6/25(목) 새벽 | **MU 실적**(美 6/24 장마감 후 ~05:00) | 새벽 | ❌ |\n| 6/25(목) 밤 | **美 5월 PCE**(8:30 ET) — 연준 선호 물가 + 1Q GDP 확정 | **21:30** | ❌ 당일 대응 불가 |\n| 6/26(금) | SPCX MSCI/Russell 편입 메커닉 | 장마감후 | — |\n| 7/16(목) | 한은 금통위(2.50→2.75 전망) | — | — |\n\n## 4. 리서치 피드 — 경제사냥꾼 신규 7편 (자막 전량 확보 ✅)\n\n> v24 봇차단(미확보) → **이번엔 tv 클라이언트로 한국어 자막 전량 확보.** 신규 쇼츠 6편(6/20~21) + 트럼프 영상 자막 보강. 수치 전부 WebSearch 교차검증.\n\n| # | 영상(쇼츠) | 핵심 | 분류 | 종목 |\n|---|---|---|---|---|\n| ① | 삼성 가장 쌀 때 사는 법(6/21) | 마이클 버리 \"주당 유형장부가 닿으면 매수\"·1Q 영업익 57.2조 역대최대·HBM4 솔드아웃 | **[검증]** | 삼성전자(보유) |\n| ② | 앤트로픽 상장 수혜주(6/20) | 앤트로픽 $965B·10월 나스닥 상장→수혜 아마존·브로드컴·SKT | [검증] / **[정정]** SKT 지분 \"조단위\"→실제 ~1.3조(0.3%) | AVGO(보유)·SKT |\n| ③ | 스페이스X+테슬라 합병(6/21) | NYT 보도 합병설·Ives 확률 80~90%·텍사스 법인 | [검증] / **[정정]** \"$4조/6,100조\"→실제 ~$3.4조 | TSLA·SpaceX |\n| ④ | 트럼프 주식 사준 회사·다음 삼성/하이닉스(6/21) | 美정부 지분 인텔 9.9%($89억)·고려아연 테네시·MP머티리얼즈 | [검증] / **[미확인]** \"삼성·하이닉스 다음 후보\" = 추측 | 삼성·SK하이닉스·한화오션 |\n| ⑤ | 트럼프 다음 타깃=쿠바(6/21) | 베네수→쿠바 제재 판박이·\"돈은 방산으로\" | **[미확인]** 예단(채널도 면피멘트) | 한화에어로·방산 |\n| ⑥ | 월가 매수 의외의 한국주=KT&G(6/21) | 외인 51.24%·블랙록 6.15%·1Q 영익 3,645억(+27.6%)·해외궐련 +56% | **[검증]** 수치 거의 무오차(최고 정확도) | KT&G(신규 워치 후보) |\n| ⑦ | 구독자전용 LG전자 분석(6/20) | 43만→21만 반토막·냉각CDU·로봇 액추에이터·7/23 분수령 | [검증] / **[정정]** 자사주 \"2조\"→실제 **2,000억(10배 과장)** | LG전자(보유) |\n\n- **트랙레코드**: ⑥ KT&G 수치 무오차(이번 최고 정확도), ①④ 하드넘버 정확. **반복 과장 패턴 재확인** — ③ 합병가치·⑦ 자사주 단위(조/억) 과장. ④⑤ 예단은 [미확인].\n- **보유 연결**: AVGO = 앤트로픽-구글-브로드컴 차세대칩 계약(검증) → ASIC 수혜 보강. TSLA·SpaceX = 합병설 실체 있으나 가치 과장 주의. **LG전자 자사주 = 반드시 2,000억으로 정정 인용.**\n\n## 5. 리스크 데스크 — 신중(bear) + 룰 점검\n\n- **🚦 트리거**: 안전핀 코스피 7,500까지 **+20.7% 버퍼**(현 9,052, 비발동)·2차 8,000도 +13.2% 미달. NAVER 229,500 = 매수존 **발동**(정리후보+외인매도 → 6/22 외인 확인 후 정수 1주). FOMC 매파 → **3차 트랜치 동결**(비둘기/META 7/29/외인복귀 중 하나까지).\n- **🚨 경보(위반 없음, 근접 강제)**: ⚠️ 룰7(동시휴장 갭) — 오늘밤 美 재개 = 누적 갭 + 선물 약세 → **반도체·신규 진입 당일 금지.** ⚠️ 룰5(야간 트리거 금지) — 6/25 PCE(밤)·MU(새벽) 폰 미가용 → **6/23 저녁 사전 베이킹 필수.** ⚠️ 메모 정합성 — \"이란 휴전 완료\" vs 재긴장 = 상충, 시나리오 재검토.\n- **집중도**: 삼성·NVDA·MU·AVGO·ANET 5종 동일 AI/메모리 사이클 = 6/25 MU 1건 동시충격(상관폭탄). MU +51% 단일 변동성. → 절반차익 베이킹이 유일 사전 완화책.\n- **신중 관점**: 표면 강세(필반 신고가·코스피 9,052)는 **6/18 종가에 갇힌 낙관.** 실시간은 반대 — 美 선물 약세·VIX 반등·이란 재긴장·유가 프리미엄 복원·6/19 외인 매도. **강세 전제(외인 복귀+지정학 안정+반도체 모멘텀) 셋 다 흔들리는 구간** → 베팅 늘릴 때 아님, 갭 소화·외인 방향 확인 후 진입. 현금 동결 유지가 정답.\n\n## 6. 강세 vs 신중 디베이트\n\n- **강세(bull)**: AI/반도체 코어 5종 스코어 83~100 정량 압도. MU HBM 슈퍼사이클(GM 81%·sold out)·삼성 HBM4 인증·일반DRAM +90%. SK하이닉스 ADR 임박 = 코리아 디스카운트 해소. 경제사냥꾼 ①(버리 삼성)·②(앤트로픽 AVGO) 코어 강세론 보강. 외인 6/19 매도는 FTSE 기계적 → 6/22 복귀 시 추세 재확인.\n- **신중(bear)**: 오늘밤 美 선물 −1.2%(반도체 차익) + SOX 신고가 되돌림 + 누적 갭. 이란 재긴장·유가 반등 = 지정학 프리미엄 복원(메모 \"휴전 완료\" 오류). 6/22 외인 미확정 + 6/25 MU+PCE 야간 더블이벤트가 단일주 변동성 응축. 집중도(코어 5종 한 사이클). FOMC 매파·DXY 고점은 고밸류 반도체 구조 역풍 그대로.\n- **PM 저울질**: **코어 홀딩 유지·현금 보존이 정답.** 오늘 거래창은 사실상 관망 — 신규 진입은 6/22 외인 확인 + 美 재개 갭 소화까지 보류, 추격금지(룰4·7). MU만 6/23 저녁 절반차익 베이킹으로 sell-the-news 헤지.\n\n## 7. PM 종합 (최종)\n\n**오늘 한 줄: 거래창은 열렸지만 사실상 관망 — 외인 재유입 미확정 + 오늘밤 美 재개 갭(선물 −1.2%) + 이란 재긴장 3중 불확실 → 신규 진입 보류, 코어 홀딩·현금 동결.** 진짜 일정은 **6/23(화) 저녁 MU 절반차익 베이킹**(폰 가용창)과 **6/25(목) MU 실적(새벽)+PCE(밤) 더블 분수령.** 스코어·별점·보유·현금 전부 무변동(美 신규 세션 없음).\n\n### 보유 16종목 — 별점 + 정량 스코어 (US 6/18 종가 / KR 6/22 잠정)\n> 환산: 85+⭐5 / 70~84⭐4 / 55~69⭐3 / 40~54⭐2 / <40⭐1. 스코어 = 정량(0~100). US 신규 세션 없어 무변동.\n\n| 종목 | 현재가 | 원가대비 | 목표가 | 매수존 | 트림/매도 | ⭐ | 스코어 | 근거 |\n|---|---|---|---|---|---|---|---|---|\n| 삼성전자 | 354,000원 | +34.6% | 48~53만 | 295~305k 눌림 | 보류 | ⭐⭐⭐⭐⭐ | **87** | 영업익 +290%·HBM4 인증·일반DRAM +90%. 버리 매수논지(검증) |\n| LG전자 | 211,500원 | +36.3% | 컨센 초과 | 홀딩 | 손절선 없음 | ⭐⭐⭐⭐ | **63** | 영업익 +40%·냉각CDU. 자사주 2,000억(2조 아님·정정). 7/23 분수령 |\n| 두산로보 | 101,800원 | +1.8% | 109k~ 분산 | 관망 | 모멘텀 차익 | ⭐⭐ | **17** | 영업손실 595억·PSR 219배. 적자=모멘텀 |\n| 현대차 | 613,000원 | −2.7% | 60만(공격 80만) | 관망 | — | ⭐⭐⭐ | **47** | PER 10.8 저평가나 성장둔화. BD 풋옵션 7/20 |\n| NAVER | 229,500원 | −8.4% | ~30만(메리츠 41만) | 225~235k(🔴발동·**6/22 외인확인 전 진입금지**) | 정리후보 | ⭐⭐ | **51** | PER20 저평가나 +12% 안정성장·랠리소외·외인매도 |\n| NVDA | $210.69 | +5.6% | $298.93 | 눌림 | 비중관리 | ⭐⭐⭐⭐⭐ | **100** | 분기EPS +212%·순마진63%·PEG0.49. Rubin HBM4 |\n| MU | $1,133.99 | +51.4% | $1,200~1,500 | 6/25 실적 | **절반차익(6/23 저녁 베이킹)** | ⭐⭐⭐⭐⭐ | **99** | 매출+196%·GM81%·HBM sold out. ⚠️시클리컬 정점·sell-the-news |\n| GOOGL | $368.03 | −5.1% | $432.83 | 눌림 | — | ⭐⭐⭐⭐⭐ | **91** | 분기EPS+82%·Cloud+63%·PEG0.81 |\n| AVGO | $411.35 | −2.3% | $522.06 | 조정주 | 물타기 후보 | ⭐⭐⭐⭐ | **83** | AI매출+143%·앤트로픽 차세대칩(검증). 3차 동결 |\n| ANET | $169.67 | +4.7% | $189.13 | 홀딩 | — | ⭐⭐⭐⭐ | **78** | 매출+35%·목표 줄상향($200). AVGO 칩 공급 제약 |\n| META | $577.22 | −9.0% | $827.32 | 실적확인(7/29) | — | ⭐⭐⭐⭐ | **75** | 분기EPS+60%·저PE20.6. 3차 트랜치 1순위 |\n| ORCL | $184.29 | −20.6% | $252.64 | 눌림 | 패닉셀 금지 | ⭐⭐⭐ | **71** | 클라우드+39%·EPS+27%. OpenAI 54% 집중 |\n| MSFT | $379.40 | −7.5% | $561.39 | 눌림 | — | ⭐⭐⭐⭐ | **66** | 매출+15%·Azure+40%·상방 최대 |\n| AAPL | $298.01 | +15.9% | $312.72 | 목표근접 | 트림 1순위 | ⭐⭐⭐ | **58** | 매출+6.4% 둔화·PE36·목표 근접 |\n| TSLA | $400.49 | −5.2% | $420.55 | 관망 | — | ⭐⭐ | **18** | 이익−47%·PE334. 합병설(NYT)·모멘텀 종목 |\n| VOO | $688.11 | +6.6% | — | 적립 | — | ⭐⭐⭐⭐ | **N/A** | S&P500 ETF, 시장β |\n\n**평가손익(원가 고정 기준)**: 국내 +202,100원 / 미국 +$67.50(≈+103,344원) → 주식 합 **+305,444원**(환차익 미반영). 환차익 반영 추정 ≈ **+593,774원**. 현금 **624,771원**. 총자산 ≈ **8,519,472원**. (실손익 정본은 토스)\n\n```\n보유 정량 지형 (스코어순)\nNVDA 100 · MU 99 · GOOGL 91 · 삼성 87 · AVGO 83 · ANET 78 · META 75 · ORCL 71  ← AI/반도체 코어 압도\nMSFT 66 · LG전자 63 · AAPL 58 · NAVER 51 · 현대차 47  ← 안정·가치군\n두산로보 17 · TSLA 18  ← 모멘텀(펀더 취약)\n```\n\n### 워치리스트 (활성)\n| 종목 | 현재가 | ⭐ | 콕 |\n|---|---|---|---|\n| SK하이닉스 | 2,764,000원 | ⭐4 | **SEC ADR 승인 6월 넷째주(22~26)·실상장 7~8월·~21조.** HBM 58%·PER 6~7배. 상장 전 진입금지(영구교정) |\n| 삼성전기 | 2,270,000원 | ⭐3 | MLCC·기판 초호황. PER 180배=추격금지 |\n| 두산에너빌리티 | 97,900원 | ⭐3 | 10만 하회, SMR 수혜, 추격금지 |\n| LG이노텍 | 1,145,000원 | ⭐3 | FC-BGA 구조적 공급부족. 그룹 급락이나 긍정 |\n| GE Vernova | $1,109.73 | ⭐4 | 워치 유일 매수검토(소액·갭 소화 후)·백로그 $163B |\n| 한화오션 | 128,400원 | ⭐3 | 트럼프 조선(필라델피아·핵잠). 공시 확인 전 추격위험 |\n| 한화에어로 | 1,122,000원 | ⭐4 | 대미투자 방산. 차익 소화 중 |\n| SpaceX | $185.00 | ⭐3 | 6/26 MSCI/Russell vs 8월 락업. **테슬라 합병설(NYT) 새 변수** |\n| **KT&G** 🆕 | (신규 검토) | — | 경제사냥꾼⑥ [검증·정확도 최고]: 외인 51%·블랙록 6.15%·해외궐련 +56%·DS목표 24만. 워치 편입 검토 후보 |\n\n### 제안 액션\n- **국내(시간외 17:30~18:00)**: NAVER 정수 1주(≈229,500원 지정가) — **단 6/22 외인 재유입 확인 시에만**(정리후보+외인매도라 미확정이면 보류). 그 외 신규 매수 전부 대기, 추격금지.\n- **미국(20:50 전 예약)**: 오늘밤 美 재개 = 선물 −1.2%·누적 갭 → **신규 진입 보류**(룰7). 3차 트랜치(META·AVGO) 동결. MU 절반차익은 **오늘 아님 → 6/23 저녁** 베이킹.\n- **결론: 오늘 거래창 = 사실상 관망.** NAVER만 조건부, 나머지 홀딩·현금 동결.\n\n### 현금 배분 (624,771원, 3분할 전부 미집행)\n- 🅰️ **관망(룰 정합·추천)**: 6/22 외인 재유입 + 美 재개 갭 소화 확인까지 전액 보류. 확인되면 1차 = NAVER 정수 1주 또는 삼성 295~305k존.\n- 🅱️ **공격**: 6/22 장중 외인 강한 순매수 + SK하이닉스 SEC 호재 동시 시 1차 즉시 집행(시간외창). 단 추격갭 회피.\n\n### 지켜볼 것 (2주)\n- **6/22(월)**: 외인 재유입(마감 확정) / SK하이닉스 SEC / 오늘밤 美 재개 갭\n- **6/23(화) 새벽**: MSCI 시장분류 발표 / **저녁: MU 절반차익 베이킹**(폰창)\n- **6/25(목)**: MU 실적(새벽) + 美 PCE(밤 21:30) = 더블 분수령. 폰 미가용 → 6/24 20:50 전 베이킹\n- **상시**: 안전핀 코스피 7,500(현 9,052, 비발동) / 이란 재긴장·유가\n\n## 8. 오늘의 이슈 선택지\n1. **6/22 외인 재유입 시나리오** — 복귀/이탈별 코스피·삼성·SK하이닉스 대응 + 오늘밤 美 재개 갭 연동\n2. **MU 6/23 저녁 베이킹 플랜** — 절반 0.02주 시장가 예약 절차 + 인라인/비트/미스 3시나리오 + GM 81% 체크포인트\n3. **이란 재긴장 재평가** — \"휴전 완료\" 정정 후 유가·DXY·2차 트랜치 트리거 시나리오\n4. **KT&G 워치 편입 검토** — 경제사냥꾼⑥ 펀더(외인51%·해외궐련+56%·주주환원) 딥다이브 + 진입조건\n\n---\n\n[STATE SNAPSHOT v25 2026-06-22]\n현금: 624,771원 (트랜치 전부 미집행 — 6/22 외인확인+美 재개 갭 소화 대기·3차 FOMC 매파 동결)\n보유변동: 없음 (美 신규 세션 없음=6/18 종가 유효 / KR 6/22 잠정)\n오늘 거래창(17:30~20:50): 사실상 관망. 국내 시간외=NAVER 정수1주(외인확인 시만, 미확정 보류). 미국=신규진입 보류(재개 갭·룰7), MU 베이킹은 6/23 저녁. 추격금지.\n신규: 경제사냥꾼 7편 자막 전량 확보. KT&G 신규 워치 후보. LG전자 자사주 2,000억(2조 과장 정정).\n미장: 간밤 세션 없음(6/19 준틴스 휴장). 오늘밤 22:30 재개 = 선물 S&P −0.74%·나스닥 −1.20%·VIX 16.78 하락출발.\n캘린더: MSCI 6/23 발표 / MU 6/25 새벽 + PCE 6/25 밤(21:30) 더블 분수령 / SK하이닉스 SEC 6월 넷째주.\n워치리스트(활성): SK하이닉스·삼성전기·두산에너빌리티·LG이노텍·GEV·한화오션·한화에어로·SpaceX (+KT&G 검토)\n대기 트리거: ①6/22 외인 재유입(마감 확정) ②6/23 저녁 MU 절반차익 베이킹 ③6/25 MU실적+PCE 더블 ④안전핀 7,500\n영구교정: ⚠️ \"이란 휴전 MOU 전자서명 완료\" → 외신 상충(트럼프 군사압박·밴스 스위스 협상·유가 반등 $77~82) = '재긴장·미확정'으로 완화. 유가 \"$65\"는 미확인($75~82). / LG전자 자사주 2조→2,000억(경제사냥꾼 10배 과장).\n다음 버전: v26\n\n*투자 자문 아님 · 모든 레벨은 분석 참고 · 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v24_2026-06-21",
      "file": "docs/reports/report_v24_2026-06-21.md",
      "title": "정훈 PORTFOLIO DESK · v24 · 2026-06-21 (일) 저녁",
      "date": "2026-06-21",
      "version": 24,
      "kind": "보고서",
      "preview": "보유 정량 지형 (스코어순)",
      "content": "# 정훈 PORTFOLIO DESK · v24 · 2026-06-21 (일) 저녁\n\n> 데이터: **US=6/18(목) 종가 / KR=6/19(금) 마감 / USD-KRW 1,529.89** — 6/20·6/21 주말 휴장 → **시세 v23 프로즌.**\n> 이번 버전 핵심 = **① 시장 개장 타이밍 정리(오늘 할 일) ② 경제사냥꾼 주말 신규 4편 ③ 6/25 더블 분수령(MU+PCE) 캘린더 재확정.**\n\n## 변경점 (v23 대비)\n\n- 🕐 **개장 타이밍 명확화 [정훈 질문]**: 오늘은 일요일 저녁 20시대 → **오늘 밤 거래 시장 0개.** 미장은 **내일밤(월 22:30 KST)**, 국장은 **내일 아침(월 09:00 KST)**. **오늘 실행할 거래 없음.**\n- 🎬 **경제사냥꾼 주말 신규 4편**(영상 2 + 쇼츠 2) — 방향성 전부 우리 데스크 뷰와 정합(코스피 9000·SK하이닉스 ADR·다음주 MU/PCE/MSCI). ⚠️ 자막 봇차단으로 본문 수치 미확보 → 제목·메타+WebSearch 교차검증만.\n- ✅ **6/25 캘린더 재확정**: research-feed가 \"MU·PCE KST 하루 시차\" 플래그 → **직접 교차검증 결과 오인.** PCE는 美 아침 8:30 ET 발표 = **21:30 KST 같은 날** → MU(6/25 새벽)+PCE(6/25 밤) **둘 다 KST 6/25 목** 확정. 마스터 캘린더 유효.\n- 🔧 **SK하이닉스 SEC 일정 보정**: \"6/22 승인\"→ **\"6월 넷째 주(22~26) 승인 가능성·실상장 7~8월\"**(웹 교차검증).\n- 시세·보유·현금(624,771원)·스코어·별점 **무변동**(주말 휴장, v23 유효).\n\n---\n\n## 🕐 오늘(6/21 일) 할 일 — 거래 0건\n\n| 시장 | 다음 개장 | 비고 |\n|---|---|---|\n| 🇰🇷 국장 (KRX) | **내일 아침 월 6/22 09:00 KST** | 외인 재유입 재검증 = 강세 분수령 |\n| 🇺🇸 미장 (NYSE/NASDAQ) | **내일밤 월 6/22 22:30 KST** → 화 05:00 | 오늘(일) 밤 아님. FOMC 매파 2차 소화 갭 |\n\n- **오늘 밤 실행할 거래 = 없음.** 일요일이라 미장도 안 열리고(미장은 토·일 휴장 → 다음은 월요일 미국 낮 = 한국 월요일 밤), 국장도 휴장. 폰 들고 할 게 없다.\n- **MU 절반차익 베이킹도 오늘 아님 → 6/23(화) 저녁.** 오늘 미리 예약 걸 필요 없음(6/24 야간 실적 대비라 6/23 저녁이 적기).\n- 오늘은 **월요일 아침 시나리오만 머리에 정리**: 외인 순매수 복귀 확인되면 NAVER 정수 1주(≈229,500원) 검토, 아니면 보류. 그 외 신규 매수 전부 대기.\n\n---\n\n## 보유 16종목 — 별점 + 정량 스코어 (v23 프로즌)\n\n> 별점 = 스코어 기반 재정렬(6/21 적용). 스코어 = 정량(0~100). 환산: 85+⭐5 / 70~84⭐4 / 55~69⭐3 / 40~54⭐2 / <40⭐1.\n\n| 종목 | 현재가 | 원가대비 | 목표가 | 매수존 | 트림/매도 | ⭐ | 스코어 | 근거(하드넘버) |\n|---|---|---|---|---|---|---|---|---|\n| 삼성전자 | 354,000원 | +34.6% | 48~53만 | 295~305k 눌림 | 보류 | ⭐⭐⭐⭐⭐ | **87** | 영업익 +290%(기저)·HBM매출 3배·일반DRAM+90%. 실행검증 관건 |\n| LG전자 | 211,500원 | +36.3% | 컨센 초과 | 홀딩 | 손절선 없음 | ⭐⭐⭐⭐ | **63** | 영업익 +40%(3년만 증익)·매출+3%·현재가 컨센초과. 냉각DSX 정성가점 |\n| 두산로보 | 101,800원 | +1.8% | 109k~ 분산 | 관망 | 모멘텀 차익 | ⭐⭐ | **17** | 2025 영업손실 595억(사상최대)·PSR 13~219배. 적자=모멘텀 종목 |\n| 현대차 | 613,000원 | −2.7% | 60만(공격 80만) | 관망 | — | ⭐⭐⭐ | **47** | PER 10.8 저평가나 성장 둔화(관세·EV). 로보틱스 옵션 정성 |\n| NAVER | 229,500원 | −8.4% | ~30만 | 225~235k(🔴존·**6/22 외인확인 전 진입금지**) | 정리후보 | ⭐⭐ | **51** | 1Q 사상최대·PER20 저평가나 +12% 안정성장·랠리소외·외인매도 |\n| NVDA | $210.69 | +5.6% | $298.93 | 눌림 | 비중관리 | ⭐⭐⭐⭐⭐ | **100** | 분기EPS +212%·매출+65%·순마진63%·ROE112%·PEG0.49 |\n| MU | $1,133.99 | +51.4% | $1,200~1,500 | 6/25 실적 | **절반차익(6/23 저녁 베이킹)** | ⭐⭐⭐⭐⭐ | **99** | 매출+196%·순마진58%·fwdPE16·DRAM슈퍼사이클. ⚠️시클리컬 정점 |\n| GOOGL | $368.03 | −5.1% | $432.83 | 눌림 | — | ⭐⭐⭐⭐⭐ | **91** | 분기EPS +82%·순마진38%·ROE39%·PEG0.81 |\n| AVGO | $411.35 | −2.3% | $522.06 | 조정주 | 물타기 후보 | ⭐⭐⭐⭐ | **83** | 매출+48%·AI매출+143%·순마진39%·ROE37%·PE63 |\n| ANET | $169.67 | +4.7% | $189.13 | 홀딩 | — | ⭐⭐⭐⭐ | **78** | 매출+35%·분기EPS+34%·순마진38%·ROE32%·PE59 |\n| META | $577.22 | −9.0% | $827.32 | 실적확인(7/29) | — | ⭐⭐⭐⭐ | **75** | 분기EPS+60%·순마진33%·저PE20.6. 연간EPS 기저효과 |\n| ORCL | $184.29 | −20.6% | $252.64 | 눌림 | 패닉셀 금지 | ⭐⭐⭐ | **71** | 클라우드+39%(OCI+93%)·EPS+27%·PE32. OpenAI집중 리스크 |\n| MSFT | $379.40 | −7.5% | $561.39 | 눌림 | — | ⭐⭐⭐⭐ | **66** | 매출+15%·순마진39%·PEG1.45. 안정 컴파운더 |\n| AAPL | $298.01 | +15.9% | $312.72 | 목표근접 | 트림 1순위 | ⭐⭐⭐ | **58** | 매출+6.4% 둔화·PE36·ROE147%(자사주). 목표 근접 |\n| TSLA | $400.49 | −5.2% | $420.55 | 관망 | — | ⭐⭐ | **18** | 이익−47%·매출−3%·PE334. **펀더 최하=모멘텀/내러티브 종목** |\n| VOO | $688.11 | +6.6% | — | 적립 | — | ⭐⭐⭐⭐ | **N/A** | S&P500 ETF, 개별 펀더 채점 제외(시장β) |\n\n**평가손익(원가 고정 기준)**: 국내 +202,100원 / 미국 +$67.50(≈+103,271원) → 주식 합 **+305,371원**(환차익 미반영). 환차익 반영 추정 ≈ **+589,520원**. 현금 **624,771원**. 총자산 ≈ **8,515,217원**. (실손익 정본은 토스)\n\n```\n보유 정량 지형 (스코어순)\nNVDA 100 · MU 99 · GOOGL 91 · 삼성 87 · AVGO 83 · ANET 78 · META 75 · ORCL 71  ← AI/반도체 코어 압도\nMSFT 66 · LG전자 63 · AAPL 58 · NAVER 51 · 현대차 47  ← 안정·가치군\n두산로보 17 · TSLA 18  ← 모멘텀(펀더 취약)\n```\n\n## 워치리스트 (활성)\n\n| 종목 | 현재가 | 콕 |\n|---|---|---|\n| SK하이닉스 | 2,764,000원 | **美 SEC ADR 승인 6월 넷째주(22~26) 가능성·실상장 7~8월·규모 ~40조.** SOX 편입 시 MU 패시브 리밸 수혜 연동 |\n| 삼성전기 | 2,270,000원 | MLCC·FC-BGA 초호황, KB 목표 300만 상향. PER 180배=추격금지 |\n| 두산에너빌리티 | 97,900원 | 10만 하회, SMR 수혜, 추격금지 |\n| LG이노텍 | 1,145,000원 | FC-BGA 구조적 공급부족, 그룹 동반급락이나 긍정 |\n| GE Vernova | $1,109.73 | 워치 유일 매수검토(소액·갭 소화 후) |\n| 한화오션 | 128,400원 | **트럼프 조선 수혜 부각(경제사냥꾼 6/21)**, 공시 확인 전 추격위험 |\n| 한화에어로 | 1,122,000원 | **대미투자 방산 '트럼프 트레이딩'**, 차익 소화 중 |\n| SpaceX | $185.00 | 우주 테마·6/26 러셀 vs 8월 락업 |\n\n## 4. 리서치 피드 — 경제사냥꾼 주말 신규 4편 (6/20~6/21)\n\n> ⚠️ 자막 봇차단(데이터센터 IP) → 제목·메타+WebSearch 교차검증만. 본문 구체 수치는 미확보(한계 명시). 방향성만 채택.\n\n| # | 영상(업로드) | 핵심(제목 기반) | 분류 | 정훈 종목 연결 |\n|---|---|---|---|---|\n| ① | \"트럼프 밀어주기 다음 후보 한국 주식\" (6/21) | 트럼프 우호 조선·방산·우주 테마 | [검증]방향 / [미확인]종목명단 | 한화오션·한화에어로·SpaceX(워치) |\n| ② | \"코스피 9000시대, 다음주 투자 포인트\" (6/20) | 9000 안착 시험 + MU·PCE·MSCI | [검증]일정 / [정정]외인 | 삼성·SK하이닉스 |\n| ③ | 쇼츠 \"월가 줍는 하이닉스 美상장 수혜주\" (6/21) | SK하이닉스 ADR 임박·패시브 수혜 | [검증]방향 / [미확인]수혜주 | SK하이닉스·MU |\n| ④ | 쇼츠 \"다음주 투자 포인트 6/22~26\" (6/21) | MU 6/24·PCE 6/25 캘린더 | [검증/정정] | MU·전체 |\n\n- **[정정] \"외인 지속 매수\" 뉘앙스 부정확**: 5월 외인 코스피 44조 순매도(개인 45조 방어)·6/19 FTSE 리밸런싱發 순매도 전환 = 외인 수급 변동성 큼. **\"외인이 계속 사고 있다\"식 단정 금지 → 6/22 재유입 여부가 진짜 분수령**(우리 대기 트리거와 일치).\n- **[확정] MU·PCE 캘린더**: research-feed의 \"KST 하루 시차\" 플래그는 **오인**(PCE를 밤 발표로 가정). PCE는 美 8:30 ET = **21:30 KST 같은 날** → **MU 6/25 새벽 + PCE 6/25 밤, 둘 다 KST 6/25 목** 확정.\n- 채널 방향성 트랙레코드 양호(핵심 이슈 정확히 짚음), 단 자막 미확보로 이번엔 구체 수치 반영 보류.\n\n## 5. 매크로·리스크 (주말 무변동)\n\n- **매크로**: USD-KRW 1,529.89·DXY 100.79·美10Y 4.44%(전부 금요일 종가 유효, 주말 무변동). 연준 매파 동결(점도표 3.4→3.8, CME 연내 인상 ~70%·첫 인상 10월 시야). 유가 브렌트 ~$80·WTI ~$77(이란 6/19 협상 중단 교착, 주간 −8%대).\n- **리스크**: 안전핀 코스피 9,052 vs 7,500 = +20.7% 버퍼(비발동). **집중도 경보** — 삼성·NVDA·MU·AVGO·ANET 5종목 동일 AI/메모리 사이클 = 6/25 MU 실적 1건이 동시 충격(상관 폭탄). 6/22 미장 = 주말 누적 휴장 갭 리스크.\n\n## 6. 강세 vs 신중 디베이트\n\n- **강세(bull)**: 보유 AI/반도체 코어 5종 스코어 83~100으로 정량 압도. 미장 FOMC 셀오프 완전 되돌림(필반 +6.4%)·AI 모멘텀 우위. 코스피 9000 안착·SK하이닉스 ADR 임박 = 코리아 디스카운트 해소 촉매. MU 슈퍼사이클이 6/25로 시험대.\n- **신중(bear)**: 외인 수급 변동성(5월 44조 매도·6/19 순매도 전환) = \"외인=엔진\" 1차 균열, 6/22 복귀 미확인. 집중도 리스크(코어 5종 한 사이클). FOMC 매파 점도표·DXY 1년 고점은 고밸류 반도체 구조 역풍 그대로(증시-금리 디커플링). 6/25 MU+PCE 더블 이벤트가 야간이라 당일 대응 불가.\n- **PM 저울질**: 코어 홀딩 유지·현금 보존이 정답. 신규 진입은 6/22 외인 확인까지 보류, 추격 금지. MU만 6/23 저녁 절반차익 베이킹으로 sell-the-news 헤지.\n\n## 7. PM 종합\n\n**오늘(일 저녁)은 할 게 없다 — 거래 시장이 안 열린다.** 미장은 내일밤(월 22:30 KST), 국장은 내일 아침(월 09:00). 오늘은 월요일 시나리오만 머리에 넣고 쉬면 된다. 이번주 진짜 일정은 **6/22(월) 외인 재유입 = 강세 분수령**, **6/23(화) 저녁 MU 절반차익 베이킹**(폰 가용창), **6/25(목) MU 실적 새벽 + PCE 밤 = 더블 분수령**. 경제사냥꾼 주말 4편은 전부 우리 뷰와 정합(코스피 9000·SK하이닉스 ADR·다음주 분수령) — 다만 \"외인 지속 매수\" 뉘앙스만 정정(6/22 재유입이 진짜 분수령). 스코어·별점·보유·현금 전부 v23 유지.\n\n### 현금 배분 (624,771원, 3분할 전부 미집행)\n- 🅰️ **관망(룰 정합·추천)**: 6/22 외인 재유입 확인까지 전액 보류. 확인되면 1차 = NAVER 정수 1주(≈229,500원) 또는 삼성 295~305k존. 미확인이면 동결.\n- 🅱️ **공격**: 6/22 장중 외인 강한 순매수 + SK하이닉스 SEC 호재 시 1차 즉시 집행. 단 추격갭 회피, 시간외 17:30~18:00창 활용.\n\n### 지켜볼 것 (2주)\n- **6/22(월)**: 국장 외인 재유입 재검증 / SK하이닉스 SEC 승인(넷째주 가능성) / 미장 누적 휴장 갭\n- **6/23(화) 저녁**: MU 절반차익 사전 베이킹(소수점=시장가, 절반 0.02주)\n- **6/23~24**: MSCI 시장분류 검토(한국 선진국 관찰대상)\n- **6/25(목)**: MU 실적(새벽 ~05:30) + 美 5월 PCE(밤 21:30) = 더블 분수령. 둘 다 폰 미가용 → 6/24 20:50 전 예약 베이킹\n- **상시**: 안전핀 코스피 7,500(현 9,052, 비발동)\n\n## 8. 오늘의 이슈 선택지\n\n1. **6/22 외인 재유입 시나리오** — 복귀/이탈 각각 코스피·삼성·SK하이닉스 대응 룰 디테일\n2. **MU 6/23 저녁 베이킹 플랜** — 절반차익 0.02주 시장가 예약 구체 절차 + 인라인/비트/미스 3시나리오\n3. **트럼프 조선·방산·우주 테마**(경제사냥꾼①) — 한화오션·한화에어로·SpaceX 워치 진입 조건 심층\n4. **SK하이닉스 ADR 상장 플레이** — SOX 리밸 시 보유 MU 수급 영향 + 토스 소수점 적립 경로\n\n---\n\n[STATE SNAPSHOT v24 2026-06-21]\n현금: 624,771원 (트랜치 전부 미집행, v23 유지 — 6/22 외인확인 대기·3차 FOMC 매파 보류)\n보유변동: 없음 (주말 연속 휴장, 시세 v23 프로즌)\n오늘 할 일: 거래 0건 (미장=내일밤 월 22:30 KST 개장 / 국장=내일 아침 월 09:00). 오늘 밤 실행 없음, 월요일 시나리오만 정리.\n신규: 경제사냥꾼 주말 4편(트럼프 조선방산·코스피9000·SK하이닉스ADR·다음주포인트) 방향성 정합, 자막 미확보로 수치 보류. \"외인 지속매수\" 정정.\n캘린더 확정: MU 6/25 새벽 + PCE 6/25 밤(21:30 KST) = 둘 다 KST 6/25 목(research-feed \"하루시차\" 플래그는 오인). SK하이닉스 SEC = 6월 넷째주 가능성·실상장 7~8월.\n워치리스트(활성): SK하이닉스·삼성전기·두산에너빌리티·LG이노텍·GEV·한화오션·한화에어로·SpaceX\n대기 트리거: ①6/22 외인 재유입+SK하이닉스 SEC ②6/23 저녁 MU 절반차익 베이킹 ③6/25 MU실적(새벽)+PCE(밤) 더블 분수령 ④안전핀 7,500\n영구교정: 없음 (캘린더는 마스터 유효 재확인)\n다음 버전: v25\n\n*투자 자문 아님 · 모든 레벨은 분석 참고 · 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v23_2026-06-21",
      "file": "docs/reports/report_v23_2026-06-21.md",
      "title": "정훈 PORTFOLIO DESK · v23 · 2026-06-21 (일)",
      "date": "2026-06-21",
      "version": 23,
      "kind": "보고서",
      "preview": "보유 정량 지형 (스코어순)",
      "content": "# 정훈 PORTFOLIO DESK · v23 · 2026-06-21 (일)\n\n> 데이터: **US=6/18(목) 종가 / KR=6/19(금) 마감 / USD-KRW 1,529.89** — 6/20 토·6/21 일 **연속 휴장 → 시세 v22 프로즌.**\n> **이번 버전 핵심 = 0~100 정량 스코어 16종목 전체 정식 산출·적용**(6/20 도입 결정의 표 반영). 미국 11종목=**FMP 하드넘버**, 국내 5종목=**증권사 컨센서스 WebSearch**, VOO=ETF(채점 제외).\n> 시세·매크로·리서치·리스크는 v22 대비 **무변동**(주말 휴장). 신규 = 스코어 + 펀더 인프라(fundamentals.py) 정비.\n\n## 변경점 (v22 대비)\n\n- 🆕 **정량 스코어(0~100) 16종목 전체 산출** — 별점의 하드넘버 근거화. 채점식: **C(분기EPS)25 + A(연간EPS)20 + 매출15 + 퀄리티(순마진·ROE)25 + 밸류(PEG)15**. (오닐 CANSLIM + 미너비니 + 드러켄밀러 렌즈)\n- 🔧 **`fundamentals.py` 버그 4개 수정** — netMargin(`_pct` 오용→`netProfitMarginTTM`), PE(`/quote` 누락→`priceToEarningsRatioTTM`), ROE↔FCF 엔드포인트 뒤바뀜 정정. **콜 수 증가 0.** main 반영 완료.\n- ⚠️ **FMP 무료 = 심볼 화이트리스트 확인** — 미국주 중 **MU·VOO·ANET·AVGO·ORCL은 quote 402** → WebSearch 폴백. NVDA·AAPL·MSFT·TSLA·GOOGL·META만 직수신.\n- 시세·보유·현금(624,771원)·매크로·트리거 **무변동**(주말 휴장, v22 유효).\n\n---\n\n## 보유 16종목 — 별점 + 정량 스코어(신규)\n\n> 별점 = **스코어 기반 재정렬(6/21 적용, 아래 '별점 재정렬' 섹션 참조)**. **스코어 = 정량(0~100)**. 환산: 85+⭐5 / 70~84⭐4 / 55~69⭐3 / 40~54⭐2 / <40⭐1. 별점이 환산과 다른 종목은 정성요인 ±1(괴리 코멘트 명시).\n\n| 종목 | 현재가 | 원가대비 | 목표가 | 매수존 | 트림/매도 | ⭐ | **스코어** | 근거(하드넘버) |\n|---|---|---|---|---|---|---|---|---|\n| 삼성전자 | 354,000원 | +34.6% | 48~53만 | 295~305k 눌림 | 보류 | ⭐⭐⭐⭐⭐ | **87** | 영업익 +290%(기저)·HBM매출 3배·일반DRAM+90%. 실행검증 관건 |\n| LG전자 | 211,500원 | +36.3% | 컨센 초과 | 홀딩 | 손절선 없음 | ⭐⭐⭐⭐ | **63** | 영업익 +40%(3년만 증익)나 매출 +3%·현재가 컨센초과. 냉각DSX 정성가점 |\n| 두산로보 | 101,800원 | +1.8% | 109k~ 분산 | 관망 | 모멘텀 차익 | ⭐⭐ | **17** | 2025 영업손실 595억(사상최대)·PSR 13~219배. 적자=모멘텀 종목 |\n| 현대차 | 613,000원 | −2.7% | 60만(공격 80만) | 관망 | — | ⭐⭐⭐ | **47** | PER 10.8 저평가나 성장 둔(관세·EV). 로보틱스 옵션 정성 |\n| NAVER | 229,500원 | −8.4% | ~30만 | 225~235k(존🔴·**6/22 외인확인 전 진입금지**) | 정리후보 | ⭐⭐ | **51** | 1Q 사상최대·PER20 저평가나 +12% 안정성장·랠리소외·외인매도 |\n| NVDA | $210.69 | +5.6% | $298.93 | 눌림 | 비중관리 | ⭐⭐⭐⭐⭐ | **100** | 분기EPS +212%·매출+65%·순마진63%·ROE112%·PEG0.49 |\n| MU | $1,133.99 | +51.4% | $1,200~1,500 | 6/25 실적 | 절반차익(6/23) | ⭐⭐⭐⭐⭐ | **99** | 매출+196%·순마진58%·fwdPE16·DRAM슈퍼사이클. ⚠️시클리컬 정점 |\n| GOOGL | $368.03 | −5.1% | $432.83 | 눌림 | — | ⭐⭐⭐⭐⭐ | **91** | 분기EPS +82%·순마진38%·ROE39%·PEG0.81 |\n| AVGO | $411.35 | −2.3% | $522.06 | 조정주 | 물타기 후보 | ⭐⭐⭐⭐ | **83** | 매출+48%·AI매출+143%·순마진39%·ROE37%·PE63 |\n| ANET | $169.67 | +4.7% | $189.13 | 홀딩 | — | ⭐⭐⭐⭐ | **78** | 매출+35%·분기EPS+34%·순마진38%·ROE32%·PE59 |\n| META | $577.22 | −9.0% | $827.32 | 실적확인 | — | ⭐⭐⭐⭐ | **75** | 분기EPS+60%·순마진33%·저PE20.6. 연간EPS 기저효과 |\n| ORCL | $184.29 | −20.6% | $252.64 | 눌림 | 패닉셀 금지 | ⭐⭐⭐ | **71** | 클라우드+39%(OCI+93%)·EPS+27%·PE32. OpenAI집중 리스크 |\n| MSFT | $379.40 | −7.5% | $561.39 | 눌림 | — | ⭐⭐⭐⭐ | **66** | 매출+15%·순마진39%·PEG1.45. 안정 컴파운더 |\n| AAPL | $298.01 | +15.9% | $312.72 | 목표근접 | 트림 1순위 | ⭐⭐⭐ | **58** | 매출+6.4% 둔화·PE36·ROE147%(자사주). 목표 근접 |\n| TSLA | $400.49 | −5.2% | $420.55 | 관망 | — | ⭐⭐ | **18** | 이익−47%·매출−3%·PE334. **펀더 최하=모멘텀/내러티브 종목** |\n| VOO | $688.11 | +6.6% | — | 적립 | — | ⭐⭐⭐⭐ | **N/A** | S&P500 ETF, 개별 펀더 채점 대상 아님(시장β) |\n\n```\n보유 정량 지형 (스코어순)\nNVDA 100 · MU 99 · GOOGL 91 · 삼성 87 · AVGO 83 · ANET 78 · META 75 · ORCL 71  ← AI/반도체 코어 압도\nMSFT 66 · LG전자 63 · AAPL 58 · NAVER 51 · 현대차 47  ← 안정·가치군\n두산로보 17 · TSLA 18  ← 모멘텀(펀더 취약)\n```\n\n## 별점 재정렬 (스코어 기반 적용 — 6/21, 정훈 위임)\n\n> 정훈 위임(\"최근 수정 바탕 너가 판단해 적용\"). 별점 = 스코어 환산 기본 + 명확한 정성요인 ±1. **데이터 우선 철학 → 모멘텀 프리미엄은 +1 상한**(과대평가 차단).\n\n- **상향 적용**: **MU·GOOGL·삼성전자 → ⭐5**(스코어 99·91·87), **AVGO → ⭐4**(83). 펀더 하드넘버 반영.\n- **하향 적용**: **TSLA ⭐3 → ⭐2**. 펀더 스코어 18=⭐1이나 로보택시/Optimus 모멘텀 +1만 인정.\n- **정성 ±1 유지**: MSFT(66, +안정컴파운더=⭐4) · ORCL(71, −OpenAI집중·−20%손실=⭐3) · LG전자(63, +냉각DSX·전략홀딩=⭐4) · 현대차(47, +저PER·로보틱스=⭐3) · 두산로보(17, +모멘텀=⭐2) · NAVER(51=⭐2) · AAPL(58=⭐3).\n- **VOO** = ETF(시장β ⭐4, 개별 펀더 채점 제외).\n\n## 매크로·리스크·이벤트 (v22 계승 — 주말 무변동)\n\n- **매크로**: DXY 100.81(YTD 최고)·美 10Y 4.44%·금 $4,153. FOMC 매파(점도표 3.4→3.8) = 고밸류 반도체 역풍. 이란 6/17 MOU 서명·6/19 후속협상 중단(유가 ~$79). USD-KRW 1,529.89.\n- **리스크**: 안전핀 코스피 9,052 vs 7,500 = +20.7% 버퍼(비발동). **집중도 경보** — 삼성·NVDA·MU·AVGO·ANET 5종목 동일 AI/메모리 사이클 = 6/25 MU 실적 1건이 동시 충격(상관 폭탄).\n- **다음주 이벤트**: 6/22(월) 외인 재유입 + SK하이닉스 美 SEC 승인 = 강세 분수령 / **6/23(화) 저녁 MU 절반차익 베이킹** + MSCI 검토(새벽) / **6/25(목) 분수령 = MU 실적(새벽) + 美 5월 PCE(밤 21:30)**.\n\n## 워치리스트 (활성 — v22 유지)\n\n| 종목 | 현재가 | 콕 |\n|---|---|---|\n| SK하이닉스 | 2,764,000원 | 6/22주 美 SEC 승인=코리아 디스카운트 해소. HBM 발주 2/3 |\n| 삼성전기 | 2,270,000원 | MLCC·FC-BGA 초호황, PER 180배 과열=추격금지 |\n| 두산에너빌리티 | 97,900원 | 10만 하회, SMR 진짜수혜, 추격금지 |\n| LG이노텍 | 1,145,000원 | FC-BGA, 그룹 동반 급락이나 구조적 공급부족 긍정 |\n| GE Vernova | $1,109.73 | 워치 유일 매수검토(소액·갭 소화 후) |\n| 한화오션 | 128,400원 | 조선 슈퍼사이클, 공시 확인 전 추격위험 |\n| 한화에어로 | 1,122,000원 | 대미투자 방산, 차익 소화 중 |\n| SpaceX | $185.00 | 6/26 러셀 vs 8월 락업 |\n\n> 워치 정량 스코어는 다음 풀 보고서에서 확장(이번엔 보유 16종목 우선).\n\n## PM 종합\n\n스코어 정식 도입으로 **보유 포트 정량 지형이 처음으로 수치화**됐다. AI/반도체 코어(NVDA·MU·GOOGL·삼성·AVGO)가 83~100으로 압도 — 강세론의 정량 뒷받침. 동시에 **집중도 리스크도 수치로 확인**(상위 5개가 한 사이클). TSLA·두산로보는 펀더 <20 = 모멘텀 트레이딩 대상임이 명확. 액션은 v22 유지(**코어 홀딩·현금 62만 보존·6/23 저녁 MU 절반차익 베이킹**). **별점 스코어 기반 재정렬 적용**(정훈 위임) — MU·GOOGL·삼성 ⭐5↑, AVGO ⭐4↑, TSLA ⭐2↓. 데이터 우선 철학대로 모멘텀 프리미엄 +1 상한.\n\n---\n\n[STATE SNAPSHOT v23 2026-06-21]\n현금: 624,771원 (트랜치 전부 미집행, v22 유지 — 3차 FOMC 매파 보류·NAVER 6/22 외인확인 대기)\n보유변동: 없음 (주말 연속 휴장)\n신규: **0~100 정량 스코어 16종목 전체 산출**(미국=FMP 하드넘버, 국내=증권사 컨센, VOO=ETF제외). fundamentals.py 버그 4개 수정 + FMP 무료 심볼제한(MU·VOO·ANET·AVGO·ORCL 402→WebSearch) main 반영.\n스코어: NVDA100·MU99·GOOGL91·삼성87·AVGO83·ANET78·META75·ORCL71·MSFT66·LG전자63·AAPL58·NAVER51·현대차47·TSLA18·두산로보17 / VOO N/A\n별점 재정렬 적용(6/21·정훈 위임): MU·GOOGL·삼성→⭐5↑, AVGO→⭐4↑, TSLA→⭐2↓. 정성±1: MSFT⭐4·ORCL⭐3·LG전자⭐4·현대차⭐3·두산로보⭐2·NAVER⭐2·AAPL⭐3. VOO=ETF시장β.\n워치리스트(활성): SK하이닉스·삼성전기·두산에너빌리티·LG이노텍·GEV·한화오션·한화에어로·SpaceX\n대기 트리거: ①6/22 외인 재유입+SK하이닉스 SEC 승인 ②6/23 저녁 MU 절반차익 베이킹+MSCI ③6/25 새벽 MU 실적+밤 PCE(분수령) ④안전핀 7,500\n다음 버전: v24\n\n*투자 자문 아님 · 모든 레벨은 분석 참고 · 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v22_2026-06-20",
      "file": "docs/reports/report_v22_2026-06-20.md",
      "title": "정훈 PORTFOLIO DESK · v22 · 2026-06-20 (토·아침 풀 브리핑)",
      "date": "2026-06-20",
      "version": 22,
      "kind": "보고서",
      "preview": "💡 핵심 액션 (다음주 = 시험 주간, 오늘은 거래창 없음)",
      "content": "# 정훈 PORTFOLIO DESK · v22 · 2026-06-20 (토·아침 풀 브리핑)\n\n> 데이터: **US=6/18(목) 종가**(6/19 美 준틴스 휴장·6/20 주말 → 간밤 신규 미장 세션 없음) / **KR=6/19(금) 마감** / USD/KRW 1,529.89.\n> 시세는 휴장으로 v21과 동일(프로즌). **신규 입력 = ①매크로(FOMC 매파 후 달러·금리·유가·이란) ②경제사냥꾼 신규 쇼츠 1편 ③다음주 이벤트 클러스터 집행 사전준비.**\n> ⚠️ **오늘(토) 거래창 없음** — KRX 시간외·미장 모두 휴장. 아래 '집행 후보'는 **다음주(6/22~) 폰 거래창용 사전 베이킹**이다.\n> 투자 자문 아님 · 최종 결정은 정훈.\n\n## 변경점 (직전 v21 대비)\n- 📊 **매크로 신규 확정**: FOMC 매파(6/18) 후 **DXY 100.81(YTD 최고)·美 10년물 4.44%·2년물 4.20%·금 $4,153(−1.3%)**. 달러·단기금리 상방 = 고밸류 반도체 역풍.\n- 🛢️ **이란**: 6/17 美-이란 **MOU 서명 확정**(60일 휴전·호르무즈 자유통항) → 유가 진정(브렌트 ~$79.6/WTI ~$78). **단 6/19 스위스 후속협상 중단** → 영구합의 미정, 6/22 갭 변수 잔존.\n- 🗓️ **다음주 매크로 정렬**: 中 LPR은 **6/20 이미 동결 발표**(6/22 별도 아님) / **MSCI 시장분류 검토 6/23(화) 새벽** / **美 5월 PCE 6/25(목) 21:30**(코어 컨센 ~2.9% [미확인]).\n- 🎬 **경제사냥꾼 신규 1편**: \"SK하이닉스 AI메모리 수혜주 = **제주반도체**\"(6/20 쇼츠). 영업익 671억·이익률 37%·시총 3.6조 [검증]. **단 정훈 보유·워치 비포함 → 추격 대상 아님, 온디바이스 AI(LPDDR) 테마 시야용.**\n- 시세·보유·현금 변동 없음(휴장).\n\n---\n\n## 1. 시장 — 미장(간밤 부재) / 국장\n\n**미장 (6/18 종가 = 최신, 6/19~20 휴장):** FOMC 매파 셀오프를 **당일 완전 되돌림**. S&P **7,500.58(+1.08%)**·나스닥 **26,517.93(+1.91%)**·다우 51,564.70(+0.14%)·**필반 14,341.78(+6.42%)**. 위험선호 = **반도체 주도 강세**(필반 +6.4%가 지수 견인, MU +8.7%·AVGO +4.7%·NVDA +3.0%·STM +6.9%). 매파에도 AI 반도체로 자금 쏠림 = \"금리보다 사이클\" 베팅. **단 6/19~20 휴장으로 매파 점도표 충격의 2차 소화는 6/22(월) 재개장 때 확인 필요**(달러·금리 상방이 반도체에 시차 역풍 가능).\n\n**국장 (6/19 마감):** 코스피 **9,052(−0.13%, 첫 숨고르기)**, 코스닥 967(−6.33% 급락). **외인 6/19 −3,800억 순매도 전환**(FTSE 리밸런싱 영향), 기관 −1.23조, **개인 +1.65조 흡수**. → 6/18 외인 +1.28조 복귀 후 하루 만에 재이탈 = **6/22 재유입이 강세 지속의 분수령**(외인 = 코스피 메인 엔진). LG그룹 동반 차익(LG전자 −7.44%·LG이노텍 −10.76%), 워치 소부장도 약세(원익IPS −4.41%·테스 −5.62%·한화에어로 −5.63%).\n\n## 3. 매크로 데스크 (6/20 토)\n\n- **달러·금리 강세 지속**: DXY **100.81**(주간 +1.0%, YTD 최고)·10Y **4.44%**·2Y **4.20%**(매파 점도표 2026 3.4→3.8 반영, Warsh 첫 FOMC 완화문구 삭제·9명 추가인상 시사)·금 **$4,153**(−1.3%). [✅교차검증]\n- **유가**: 브렌트 8월물 **~$79.6**·WTI **~$78**. 호르무즈 재개통(목 ~1천만 배럴, 사우디 탱커 첫 이동)으로 하락 압력 ↔ 스위스 美-이란 후속협상 중단으로 되돌림. CPI 에너지 경로엔 디스인플레 우호. [교차검증]\n- **이란 MOU**: **6/17 서명 확정**(12일전쟁 종식·60일 휴전·호르무즈 자유통항). 단 **6/19 후속협상 중단** → 영구합의 미정. 6/22 갭 = 유가하향·위험선호 우호가 베이스, 결렬 헤드라인 시 유가 재반등 리스크. [교차검증]\n- **환율 1,530**: USD/KRW **1,529.89(−0.59%)** 원화 강세 지속(코스피 최고권·외인 유입·7월 원화 24h 거래·MSCI 기대) ↔ FOMC 매파 DXY 강세는 역풍. **외인 수급이 매파 달러강세를 상쇄 중인 구도** — 미국주 원화환산은 강세분만큼 소폭 희석.\n\n**다음주 매크로 캘린더 (KST):**\n\n| 날짜 | 이벤트 | 컨센/관전 | KST | 폰 |\n|---|---|---|---|---|\n| 6/22(월) | 中 LPR(1년3.00%/5년3.50%) | **6/20 이미 동결 발표** → 별도 이벤트 아님 | 오전 | ✅ |\n| 6/22(월) | 美 재개장 갭 / SK하이닉스 美 SEC 승인 주 | 매파 2차소화 + 외인 재유입 재검증 | 22:30 | ❌야간 |\n| 6/23(화) | 글로벌 6월 Flash PMI(獨·유로·英·美) | 美 50선 분기점 | 美 22:45 | ❌야간 |\n| **6/23(화)** | **MSCI 연례 시장분류 검토** | **韓 워치리스트 등재 여부**(외인 수급 핵심) | 韓 새벽 06:00경 | ⚠️장전 |\n| 6/24(수) | 美 5월 신규주택판매·FedEx 실적·호주 CPI | — | — | — |\n| **6/25(목)** | **분수령 — MU 실적(美 6/24 장후=韓 새벽) + 美 5월 PCE** | 코어 PCE 컨센 **~2.9% YoY/+0.2% MoM [미확인]** | PCE **21:30** | ❌**야간** |\n| 6/26(금) | 미시간 소비심리·도쿄물가·러셀 리밸런싱 | — | — | ✅오전 |\n| 7/16(목) | 한은 금통위(2.50→2.75% 전망) | — | 오전 | ✅ |\n\n## 4. 리서치 피드 — 경제사냥꾼 (v21 이후 신규 1편)\n\n> v21이 6/20 신규 3편(주간전망 롱폼·MU $1,500·삼성물산 고배당)을 이미 분석. 그 이후 채널 재탐색 → **진짜 신규는 쇼츠 1편**(나머지는 중복 또는 6/19 구영상). 자막 전량 정상 확보(봇차단 폴백 web→tv→mweb 성공).\n\n**신규 쇼츠 \"SK하이닉스 AI메모리 수혜주 = 제주반도체(080220)\" (6/20, 2:50)**\n- 논지: 대기업이 HBM·첨단D램에 자원 몰수 → **저전력 레거시 메모리(LPDDR) 빈자리** → 제주반도체가 하이닉스와 메움. (말미 \"추격매수 권유 아님\" 자진경고)\n- **제주반도체 LPDDR4X를 SK하이닉스 팹서 생산·LPDDR5 2030 양산 추진** [✅검증, 디일렉]. **단 정정**: 하이닉스는 \"파운드리 위탁 아닌 레거시 스페셜티 웨이퍼 공급\" 입장 ↔ 제주는 \"100% 자체설계 위탁생산\" 주장 → \"하이닉스 파운드리 진출\" **과대해석 주의**.\n- **1Q 영업익 671억·이익률 37%·매출 1,805억(+273%)** [✅검증, 숫자 정확]. **1년 10배·시총 3.6조(코스닥 26위)** [✅검증].\n- \"퀄컴·미디어텍 인증 둘 다 국내유일\" [⚠️미확인/일부정정 — 웹은 \"삼성·퀄컴 LPDDR5x 인증 막바지\"]. 수출 +912% [미확인]. **중국 매출 비중 72.9%** [✅검증 = 핵심 리스크].\n- **정훈 직결**: SK하이닉스(워치) 생태계 모멘텀 보강 재료(+ 6/22주 美 상장 승인). **제주반도체 자체는 보유·워치 비포함 + 1년10배 선반영 + 중국 72.9% 의존 → 추격금지·집중도 룰상 신규진입 부적합. \"온디바이스 AI 저전력메모리(LPDDR)\" 테마 시야로만 기록.**\n\n## 5. 리스크 데스크 (신중=bear)\n\n- 🚦 **트리거**: 안전핀 코스피 9,052 vs 7,500 = **+20.7% 버퍼**(동결 비발동). 2차(8,000)까지 +13.2%.\n- 🚨 **NAVER 트리거 모순 경보**: triggers.py가 NAVER 1차 매수존(229,500/존 225~235k) **기계적 발동** — 그러나 동일 종목이 **트림란 \"정리후보\"·⭐⭐·외인 순매도 전환** 상태. **\"정리후보를 매수\"는 논리충돌**(스크립트는 가격존만 보고 펀더·수급 모름). → **6/22 외인 재유입 미확인 시 NAVER 신규진입 금지.** 발동 트리거를 실행신호로 오독 금지.\n- 🚨 **추격금지 환기**: 코스피 9,052 = 16거래일 +1,000p 과속·반도체 2종목 착시. 이벤트 클러스터(6/22~26) 진입 전 신규매수 회피 = 룰3 정합. (현금 전액 보존 = 위반 없음)\n- **집중도 리스크 심각**: 보유 측 삼성·NVDA·MU·AVGO·ANET **5종목**이 동일 AI/메모리 사이클. 워치(하이닉스·삼성전기·원익IPS·테스·LG이노텍)까지 더하면 **코어가 사실상 단일 테마**. **6/25 MU 실적 1건이 삼성+하이닉스+MU+AVGO를 동시에 흔드는 상관 폭탄** — 분산처럼 보이나 한 베팅.\n- **MU +51.4% 미실현 차익**: 옵션 ±17% 변동성 베팅·\"sold out\"·$1,500 선반영 → 미스 시 급락 전염. 절반 차익 = 집중도 완화상 합리(단 DB·씨티 상향이 홀딩 명분도 강화 → 택1은 정훈).\n- **bear 1단락**: 코스피 9,052는 과속이고 동력이 반도체 2종목 착시에 의존. 최대 약화요인 = **6/19 외인 순매도 재전환**(메인 엔진이 한 번 멈춤) → 6/22 재유입 실패 시 강세 논지 급속 훼손. 매크로 측 **FOMC 매파 확정**(점도표 3.4→3.8)으로 금리·DXY 상방이 고밸류 반도체에 직접 역풍이고, **6/25 PCE 재가속 시 인하기대 추가 후퇴**. 동시에 AI 수요의 質(MU \"sold out\"이 진짜수요 vs 사재기·이중주문)이 6/25 실적의 장기계약·선급금 가시성에서 첫 검증대에 오른다. **상방은 이미 가격에, 하방만 미반영 — 비대칭적으로 신중해야 할 주간.**\n\n## 6. 강세 vs 신중 디베이트\n\n**강세(bull):** 필반 6/18 +6.4%가 보여주듯 시장은 매파에도 \"금리보다 AI 사이클\"에 베팅 중. MU 도이체방크 $1,500(+50%)·씨티 $1,200 상향은 [✅검증]됐고 DRAM 부족이 2028+까지 = 메모리 판 전체 재평가 → 삼성·하이닉스로 전이. 이란 휴전·유가 진정·원화 강세·SK하이닉스 美 상장(코리아 디스카운트 해소)이 코스피 9천을 떠받친다. 코어 홀딩 유지가 정석.\n\n**신중(bear):** 위 리스크 데스크 요약대로 — 외인 재이탈, 매파 금리 역풍, MU 실적이 처음 검증대, 반도체 단일테마 쏠림. 다음주는 하방만 미반영. 추격 대신 차익·확인.\n\n**→ PM 저울질:** 코어는 그대로(AI 슈퍼사이클 강세 유지), 단 **신규 매수는 동결·MU 절반차익 베이킹으로 집중도 한 단계 덜어두기**가 비대칭 리스크에 맞는 균형. 무게는 \"확인 후 행동\".\n\n---\n\n## 7. PM 종합 (최종)\n\n**오늘의 한 줄:** 주말 프로즌. 간밤 신규 미장은 없고(준틴스+주말), 새 정보는 **매크로(매파 달러·금리 강세 + 이란 휴전 서명되었으나 후속 불안)**와 **다음주 이벤트 클러스터(6/23 MSCI·6/25 새벽 MU+밤 PCE)**다. 정훈 룰과 정확히 정합 — **코어 홀딩·현금 62만 전액 보존·6/23(화) 저녁 폰창에서 MU 절반차익 베이킹 사전 세팅**. 9천 착시·과속·외인 확인 전 추격 금지.\n\n### 보유 16종목 (현재가 = 6/19 KR / 6/18 US, 휴장 동일)\n\n| 종목 | 현재가 | 당일 | 원가대비 | 목표가 | 매수존 | 트림/매도 | ⭐ | 코멘트 |\n|---|---|---|---|---|---|---|---|---|\n| 삼성전자 | 354,000원 | −2.34% | **+34.6%** | 480,000~530,000원 | 295,000~305,000원(눌림 대기) | 보류 | ⭐⭐⭐⭐ | 일반DRAM +90%·HBM4 인증. 다음주 메모리 시험주간 직결 |\n| LG전자 | 211,500원 | −7.44% | **+36.3%** | 컨센 초과 | 홀딩 | 손절선 없음 | ⭐⭐⭐⭐ | 그룹 동반 차익(−7.4%), 펀더 무손상=홀딩·투매금지 |\n| 두산로보틱스 | 101,800원 | −0.88% | +1.8% | 분산 큼(109k~) | 관망 | 모멘텀 차익 | ⭐⭐ | PSR 219배 데이터 취약, 추격금지 |\n| 현대차 | 613,000원 | +2.00% | −2.7% | 600,000원(공격 800,000원) | 관망 | — | ⭐⭐⭐ | BD 풋옵션 7/20·삼성 지분설(미확인) |\n| NAVER | 229,500원 | −2.34% | −8.4% | ~300,000원(메리츠 410,000원) | **225,000~235,000원(존 발동🔴)** | 정리후보 | ⭐⭐ | ⚠️존 발동했으나 정리후보+외인 매도 → **6/22 외인 확인까지 진입 금지** |\n| NVDA | $210.69 | +2.95% | +5.6% | $298.93 | 눌림 | 비중관리 | ⭐⭐⭐⭐⭐ | Rubin HBM4·필반 견인주 |\n| META | $577.22 | +1.70% | −9.0% | $827.32 | 실적확인 | — | ⭐⭐⭐⭐ | 7/29 실적 전 보류 |\n| VOO | $688.11 | +0.98% | +6.6% | — | 적립 | — | ⭐⭐⭐⭐ | 분산형 코어 |\n| MSFT | $379.40 | +0.13% | −7.5% | $561.39 | 눌림 | — | ⭐⭐⭐⭐ | 상방 최대(+48%) |\n| AAPL | $298.01 | +0.70% | **+15.9%** | $312.72 | 목표근접 | **트림 1순위** | ⭐⭐⭐ | 금리방어·목표 근접 |\n| GOOGL | $368.03 | +1.17% | −5.1% | $432.83 | 눌림 | — | ⭐⭐⭐⭐ | Cloud·Gemini |\n| TSLA | $400.49 | +1.04% | −5.2% | $420.55(ARK $2,600) | 관망 | — | ⭐⭐⭐ | 우드 차익매도 중 |\n| ORCL | $184.29 | +0.41% | **−20.6%** | $252.64 | 눌림 | 패닉셀 금지 | ⭐⭐⭐ | OpenAI 54% 집중 우려 |\n| ANET | $169.67 | +2.87% | +4.7% | $189.13 | 홀딩 | — | ⭐⭐⭐⭐ | AI 네트워크 |\n| MU | $1,133.99 | +8.70% | **+51.4%** | **$1,200~1,500(DB·씨티 상향)** | **6/25 실적** | **절반 차익(6/23 베이킹)** | ⭐⭐⭐⭐ | DB $1,500·6/25 새벽=한국 메모리 풍향계·옵션 ±17% |\n| AVGO | $411.35 | +4.70% | −2.3% | $522.06 | 조정주 | 물타기 후보 | ⭐⭐⭐ | ASIC·평단 근접 |\n\n```\n💡 핵심 액션 (다음주 = 시험 주간, 오늘은 거래창 없음)\n1. 🔴 MU(+51.4%) — 6/25 새벽 실적=한국 메모리 풍향계. 목표보다 ①총이익률 ②장기계약 가시성.\n   → 6/23(화) 저녁 폰창서 절반(0.02주) 시장가 매도 베이킹 OR 전량 홀딩 택1 (DB $1,500=홀딩 명분도 강화).\n2. 🟡 6/22(월) 외인 재유입 + SK하이닉스 美 SEC 승인 = 강세 분수령. 확인 전 신규진입 보류.\n3. ✋ 추격금지 — 9천=2종목 착시·16거래일 +1,000p 과속. 매파 달러·금리 역풍 잔존.\n4. 💵 현금 624,771원 전액 보존(관망). NAVER는 ⚠️**국장 소수점 불가 → 최소 1주(≈229,500원)** — '소액 10만원'은 성립 불가. 정리후보+외인매도라 보류, 매수해도 6/22 외인 확인 후 **정수 1주 지정가**.\n```\n\n### 워치리스트 (활성)\n\n| 종목 | 현재가 | 당일 | 목표 | 콕 |\n|---|---|---|---|---|\n| SK하이닉스 | 2,764,000원 | +2.94% | Strong Buy(평균 258.7만) | 6/22주 美 SEC 승인=코리아 디스카운트 해소 신호. HBM 발주 2/3. 신규 쇼츠도 생태계 보강 |\n| 삼성전기 | 2,270,000원 | +3.18% | KB 300만 | MLCC·FC-BGA 초호황. PER 180배 과열=추격금지 |\n| 두산에너빌리티 | 97,900원 | −1.71% | 135,000~165,000원 | 10만 하회. SMR 진짜수혜, 추격금지 |\n| LG이노텍 | 1,145,000원 | −10.76% | KB 160만 | FC-BGA, 그룹 동반 급락(−10.8%)이나 구조적 공급부족 긍정 |\n| GE Vernova | $1,109.73 | +5.80% | $1,211.72 | 워치 유일 매수검토(소액·갭 소화 후) |\n| 한화오션 | 128,400원 | +2.64% | — | 조선 슈퍼사이클, 공시 확인 전 추격위험 |\n| 한화에어로 | 1,122,000원 | −5.63% | — | 대미투자 방산, 차익 소화 중 |\n| SpaceX | $185.00 | −3.56% | $63~$190 | 6/26 러셀 vs 8월 락업 |\n\n### 제안 액션\n- **홀딩(코어 전부):** 삼성·LG전자·NVDA·MSFT·GOOGL·ANET·VOO·META — AI 슈퍼사이클 강세 유지, 신규정보로 논지 무손상.\n- **차익 후보:** ①**MU 절반**(6/23 저녁 베이킹·집중도 완화) — 신중. ②**AAPL 트림 1순위**(목표 $312 근접·+15.9%) — 단 1주 미만 분수주라 실효성 낮음, 관망 가능.\n- **관망/금지:** NAVER(존 발동했으나 정리후보+외인 미확인 → 6/22까지 금지), 두산로보(모멘텀), 추격 일체 금지.\n\n### 현금 배분 (624,771원, 3분할 미집행)\n- **🅰️ 관망 (룰 정합·추천):** 외인 6/19 순매도 전환 + 6/22 매파 2차소화 갭 + 이벤트 클러스터 → **전액 보존.** MU 6/23 저녁 절반차익 베이킹만 능동 액션.\n- **🅱️ 공격:** 6/22 외인 재유입 + 코스피 9천 사수 확인 시에만 NAVER **정수 1주(≈229,500원) 지정가**(225~235k 하단). ⚠️국장 소수점 불가 → '소액 10만원'은 불가, 최소 단위가 1주. 그 전엔 집행 없음.\n\n### ★ 다음주 폰 거래창(17:30~20:50) 집행 후보 — 사전 준비\n\n> 오늘(토)은 거래창 없음. 아래는 **다음주 폰 가용시간용** 사전 정리. 추격금지·안전핀(코스피 7,500) 준수.\n\n**① 국내 시간외단일가(16:00~18:00, 폰 겹침 17:30~18:00) — 살/팔 후보**\n| 구분 | 종목 | 조건 | 비고 |\n|---|---|---|---|\n| 살 | NAVER | 225,000~235,000원 + **6/22 외인 순매수 재전환 확인 시에만** **정수 1주(≈229,500원) 지정가** | ⚠️국장 소수점 불가(소액 10만원 ✗). 미확인 시 집행 금지(정리후보) |\n| 팔 | — | 국내 보유 트림 후보 없음(삼성·LG전자 홀딩) | — |\n| 관망 | SK하이닉스·삼성전기 | 추격금지, 美 상장 승인·눌림 대기 | 워치 |\n\n**② 미국 지정가/소수점 예약 후보 (20:50 전 예약 → 22:30 자동집행)**\n| 구분 | 종목 | 예약 방식 | 예약가/수량 | 트리거 |\n|---|---|---|---|---|\n| 팔(차익) | **MU** | 소수점=시장가 | 절반 **0.02주** 시장가 | **6/23(화) 저녁 베이킹** — 6/25 새벽 실적 전. 정훈 절반/홀딩 택1 |\n| 살 | GE Vernova | 정수주 지정가 | 갭 소화 후 소액·지정가 | 워치 유일 매수검토, 서두르지 않음 |\n| 보류 | META·AVGO | — | 3차 트랜치 | FOMC 🔴매파 → 전면 보류(비둘기 전환/META 7/29 실적/외인 복귀 중 하나까지) |\n\n⚠️ MU 소수점=시장가 체결(지정가 아님) → 6/25 갭 변동 노출. 절반차익은 \"집중도 완화\" 목적, 홀딩은 \"DB $1,500 명분\" — **택1은 정훈**.\n\n### 지켜볼 것 (2주 캘린더)\n| 날짜 | 이벤트 | 폰 | 대응 |\n|---|---|---|---|\n| **6/22(월)** | 美 재개장 갭(매파 2차소화) / **외인 재유입 재검증** / SK하이닉스 SEC 승인 주 | ❌야간 | 외인 = 강세 분수령. 확인 전 신규 보류 |\n| **6/23(화) 저녁** | **MU 절반차익 사전 베이킹** + 글로벌 PMI / **MSCI 검토(새벽)** | ✅ | 폰창 능동 액션 |\n| 6/24(수) | 美 신규주택·FedEx·호주 CPI | — | — |\n| **6/25(목)** | **분수령 — MU 실적(새벽) + 美 PCE(21:30 밤)** | ❌야간 | 사전 베이킹으로 대응(당일밤 트리거 금지) |\n| 6/26(금) | 미시간 소비심리·러셀 리밸런싱 | ✅오전 | 확인 |\n| 7/16(목) | 한은 금통위(2.50→2.75% 전망) | ✅오전 | — |\n\n## 8. 오늘의 이슈 선택지\n1. **MU 절반차익 vs 전량 홀딩** — DB $1,500 상향(홀딩 명분) vs 옵션 ±17%·집중도(차익 명분). 6/23 베이킹 전 최종 결정 프레임 심층.\n2. **6/22 외인 재유입 시나리오** — FTSE 리밸런싱 일시효과인지 매파 달러발 셀코리아 재개인지, 코스피 9천 사수 조건.\n3. **반도체 집중도 관리** — 삼성+MU+NVDA+AVGO+ANET+워치 메모리 쏠림을 어떻게 덜까(상관 폭탄 6/25).\n4. **온디바이스 AI(LPDDR) 테마** — 제주반도체발 레거시 메모리 수혜 축, 정훈 보유(삼성)·워치(하이닉스)에 주는 함의.\n\n→ 번호로 답하면 그 항목만 다음 메시지에서 상세 분석.\n\n---\n\n[STATE SNAPSHOT v22 2026-06-20]\n현금: 624,771원 (트랜치 1차/2차/3차 전부 미집행 — 3차 FOMC 매파 보류, 1차 NAVER 존 발동했으나 정리후보+외인 순매도→6/22 재유입 확인까지 보류)\n보유변동: 없음 (주말 휴장, 간밤 미장도 준틴스 휴장)\n워치리스트(활성): SK하이닉스·삼성전기·두산에너빌리티·LG이노텍·GEV·한화오션·한화에어로·SpaceX\n대기 트리거: ①6/22 외인 재유입+매파 2차소화+SK하이닉스 美 SEC 승인 ②6/23 저녁 MU 절반차익 베이킹+MSCI 검토 ③6/25 새벽 MU 실적+밤 PCE(분수령) ④코스피 안전핀 7,500\n영구교정: 매크로 신규 — FOMC 후 DXY 100.81/10Y 4.44%/2Y 4.20%/금 $4,153 [검증], 이란 6/17 MOU 서명·6/19 스위스 후속협상 중단 [검증], 中 LPR 6/20 동결발표(6/22 별도 아님) [검증], MSCI 검토 6/23 [유력]. 경제사냥꾼 신규 = 제주반도체(080220) 1Q 영업익 671억·37%·시총 3.6조 [검증], '하이닉스 파운드리 진출' 프레임·퀄컴/미디어텍 인증·수출+912%는 [미확인/일부정정]. 제주반도체 보유·워치 비포함=추격 대상 아님.\n다음 버전: v23\n\n*투자 자문 아님 · 모든 레벨은 분석 참고 · 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v21_2026-06-20",
      "file": "docs/reports/report_v21_2026-06-20.md",
      "title": "정훈 PORTFOLIO DESK · v21 · 2026-06-20 (주말·휴장)",
      "date": "2026-06-20",
      "version": 21,
      "kind": "보고서",
      "preview": "💡 핵심 액션 (다음주 = 시험 주간)",
      "content": "# 정훈 PORTFOLIO DESK · v21 · 2026-06-20 (주말·휴장)\n\n> 데이터: KR=6/19 마감 / US=6/18 종가 (6/19 준틴스·6/20 주말 휴장) / USD/KRW ~1,530.\n> **이번 보고서 = 정훈 요청 \"경제사냥꾼 최신 영상까지 다 보고 최신화\"** → 6/20 주말 신규 **3편 자막 전량 확보·교차검증**. 시세는 v20과 동일(휴장).\n> 투자 자문 아님 · 최종 결정은 정훈.\n\n## 변경점 (직전 v20 대비)\n- 🎬 **경제사냥꾼 6/20 신규 3편 반영**(주간전망 롱폼 + 쇼츠 2). 핵심 = **다음주(6/22~26)=반도체 호황 진위 '시험 주간'**, 분수령 **6/25(목) 새벽 MU 실적 + 밤 美 PCE**.\n- 📈 **MU 목표가 상향 교차검증 완료**: 도이체방크 **$1,000→$1,500(+50%, 6/17 BUY)**, 씨티 $840→$1,200, TD코웬 $1,500 [✅검증]. → 정훈 6/24(실은 6/25 새벽) 절반차익 트리거 명분 강화.\n- 시세·보유·현금 변동 없음(휴장).\n\n---\n\n## 4. 리서치 피드 — 경제사냥꾼 6/20 신규 3편 (자막 전량 확보)\n\n> 채널 특성: 방향성 우수·수치 교차검증 필수. 이번 회차 트랙레코드 **개선세 지속**(MU 목표 정확 인용·리스크 자진 병기).\n\n**① \"코스피 9,000시대 '다음주' 투자 포인트\" (14:52, ★주간전망)**\n- 코스피 9,300 돌파했으나 **6/18 9천 첫 돌파일 상승 98개 vs 하락 806개** = 지수만 잔치, **반도체(삼성·하이닉스) 두 종목이 끌어올린 착시** [검증·방향]. 6/18 외인 **+1.2조 순매수**(개인·기관 매도)가 상승 주체 [검증, v20 일치].\n- **다음주 캘린더(6/22~26)**:\n\n| 날짜 | 핵심 이벤트 | 별점 |\n|---|---|---|\n| 6/22(월) | 中 LPR(동결전망) + **SK하이닉스 美 SEC 승인 가능성(이번주)** = 코리아 디스카운트 해소 신호탄 | ⭐⭐⭐ |\n| 6/23(화) | 글로벌 6월 PMI(미 화밤 22:45)·서울 CLSA포럼(삼성 참석)·**MSCI 시장분류 검토**(화밤~수새벽) | ⭐⭐⭐ |\n| 6/24(수) | 미 5월 신규주택판매·FedEx 실적 (밤=목새벽 MU) | ⭐⭐ |\n| **6/25(목)** | **분수령 — 새벽 MU 실적 + 밤 美 5월 PCE(연준 핵심물가)** | ⭐⭐⭐⭐⭐ |\n| 6/26(금) | 미시간 소비심리·도쿄물가·(토새벽) 러셀 리밸런싱 | ⭐⭐ |\n\n- **체크포인트 3**: ①MU 장기계약·선급금 가시성(매출보다 중요, 진짜수요 vs 사재기) ②목 PCE(금리=반도체 한 몸) ③하이닉스 美상장 승인.\n- **리스크 4**: 반도체 쏠림 · 과속(8천 5/26→9천 16거래일) · 외인 매수 지속 여부 · 이란 휴전(초기합의·60일) 되돌림.\n- ⚠️ 하이닉스 \"1Q 영업이익률 72%\" 수치는 **과장 의심[미확인]**.\n\n**② \"목표가 $1,500 제2의 엔비디아 = 마이크론\" (2:59, ★보유 MU)**\n- **도이체방크 $1,000→$1,500(+50%)·씨티 $840→$1,200·타 IB $1,500~1,600** [✅검증, DB 6/17 Weathers BUY·TD코웬 $1,500, DRAM 부족 2028+]. 직전분기 매출 $238억(예상 $200억)·순익 $138억·EPS +30%상회 [검증·근사].\n- MU=메모리 3등, 1·2등=삼성·하이닉스, **HBM 엔비디아 발주 2/3 SK하이닉스** → \"3등을 $1,500 만든 급등기가 1·2등엔 더 세게\" [방향]. 가이던스 매출 $335억·옵션시장 ±17% 베팅·저점比 10배+ 미스 시 급락 리스크 자진 경고.\n- 노무라 코스피 1.1만·하이닉스 400만·삼성 59만 [미확인·단일출처].\n- **★보유 MU·삼성 + 워치 하이닉스 직결: 6/25 MU=한국 메모리 풍향계.**\n\n**③ \"정부 밀어줄 고배당주 = 삼성물산\" (2:28)**\n- 정부 **고배당 분리과세** → 배당확대 기업 자금몰림. 삼성물산=삼성전자·삼성생명 지분 '현금통로'. DS투자증권 올해 DPS +720% 23,500원·내년 4만원대 [미확인·단일출처]. SMR(에스토니아 법안)·삼성 평택 하이테크 수주 엮임. **삼성물산 미보유 — 정책 테마 참고만.**\n\n**교차검증 추가**: 구글+블랙스톤 $250억 AI 인프라 JV → 5/19 발표·$5B 지분·TPU [검증·시점, 신규 아님].\n\n---\n\n## 7. PM 종합\n\n**오늘의 한 줄**: 휴장 주말. 경제사냥꾼이 짚은 **다음주 = 반도체 호황 진위 시험 주간**이 정훈 룰(6/24 MU 절반차익·추격금지·외인 확인)과 정확히 맞물린다. **MU $1,500 상향은 검증됐고**, 6/25 새벽 실적+PCE가 분수령. 코어 홀딩·현금 보존·6/23 저녁 베이킹 정석.\n\n### 보유 16종목 (현재가=6/19 KR / 6/18 US, 휴장 동일)\n\n| 종목 | 현재가 | 당일 | 원가대비 | 목표가 | 매수존 | 트림/매도 | ⭐ | 코멘트 |\n|---|---|---|---|---|---|---|---|---|\n| 삼성전자 | 354,000원 | −2.34% | **+34.6%** | 480,000~530,000원 | 295,000~305,000원(이탈) | 보류 | ⭐⭐⭐⭐ | 다음주 메모리 시험주간 직결·일반DRAM +90% |\n| LG전자 | 211,500원 | −7.44% | **+36.3%** | 컨센 초과 | 홀딩 | 손절선 없음 | ⭐⭐⭐⭐ | 그룹 동반 차익·펀더 무손상=홀딩 |\n| 두산로보틱스 | 101,800원 | −0.88% | +1.8% | 분산 큼 | 관망 | 모멘텀 | ⭐⭐ | 모멘텀, 추격금지 |\n| 현대차 | 613,000원 | +2.00% | −2.7% | 600,000원(공격 800,000원) | 관망 | — | ⭐⭐⭐ | BD 풋옵션 7/20·삼성 지분설(미확인) |\n| NAVER | 229,500원 | −2.34% | −8.4% | ~300,000원 | **225,000~235,000원(진입🔴)** | 정리후보 | ⭐⭐ | 매수존 발동 but 6/22 외인 확인 대기 |\n| NVDA | $210.69 | +2.95% | +5.6% | $298.93 | 눌림 | 비중관리 | ⭐⭐⭐⭐⭐ | Rubin HBM4·테라팹 |\n| META | $577.22 | +1.70% | −9.0% | $827.32 | 실적확인 | — | ⭐⭐⭐⭐ | 7/29 전 보류 |\n| VOO | $688.11 | +0.98% | +6.6% | — | 적립 | — | ⭐⭐⭐⭐ | 분산형 코어 |\n| MSFT | $379.40 | +0.13% | −7.5% | $561.39 | 눌림 | — | ⭐⭐⭐⭐ | 상방 최대(+48%) |\n| AAPL | $298.01 | +0.70% | **+15.9%** | $312.72 | 목표근접 | **트림 1순위** | ⭐⭐⭐ | 금리방어·인텔딜 당사자 |\n| GOOGL | $368.03 | +1.17% | −5.1% | $432.83 | 눌림 | — | ⭐⭐⭐⭐ | Cloud·Gemini |\n| TSLA | $400.49 | +1.04% | −5.2% | $420.55 (ARK $2,600) | 관망 | — | ⭐⭐⭐ | 우드 차익매도 중 |\n| ORCL | $184.29 | +0.41% | **−20.6%** | $252.64 | 눌림 | 패닉셀 금지 | ⭐⭐⭐ | OpenAI 54% 집중 |\n| ANET | $169.67 | +2.87% | +4.7% | $189.13 | 홀딩 | — | ⭐⭐⭐⭐ | AI 네트워크 |\n| MU | $1,133.99 | +8.70% | **+51.4%** | **$1,200~1,500(DB·씨티 상향)** | **6/25 실적** | **절반 차익** | ⭐⭐⭐⭐ | DB $1,500·6/25 새벽=한국 메모리 풍향계 |\n| AVGO | $411.35 | +4.70% | −2.3% | $522.06 | 조정주 | 물타기 후보 | ⭐⭐⭐ | ASIC·평단 근접 |\n\n```\n💡 핵심 액션 (다음주 = 시험 주간)\n1. 🔴 MU(+51.4%) — 6/25(목) 새벽 실적 = 한국 메모리 풍향계. 목표보다 ①총이익률 ②장기계약 가시성.\n   → 6/23(화) 저녁 폰창에서 절반(0.02주) 시장가 매도 베이킹 OR 전량 홀딩 택1. (DB $1,500 상향=홀딩 명분도 강화 → 정훈 택)\n2. 🟡 6/22(월) 외인 재유입 + SK하이닉스 美 SEC 승인 여부 = 강세 분수령. 확인 전 신규진입 보류.\n3. ✋ 추격금지 — 9천은 두 종목 착시·과속(16거래일 +1,000p). \"좋은 기업 ≠ 좋은 가격.\"\n4. 💵 현금 624,771원 전액 보존(관망). NAVER 매수존도 6/22 외인 확인 후 소액만.\n```\n\n### 워치리스트 (활성)\n| 종목 | 현재가 | 목표 | 콕 |\n|---|---|---|---|\n| SK하이닉스 | 2,764,000원 | Strong Buy | 6/22주 美 SEC 승인=코리아 디스카운트 해소 신호. HBM 발주 2/3. ⚠️노무라 400만·이익률 72%는 미확인 |\n| 삼성전기 | 2,270,000원 | KB 3,000,000원 | MLCC·기판 초호황+희토류 반사이익 |\n| GE Vernova | $1,109.73 | $1,211.72 | 워치 유일 매수검토(소액·갭 소화 후) |\n| 두산에너빌리티 | 97,900원 | 135,000~165,000원 | 10만 하회, 추격금지·SMR 진짜수혜 |\n| LG이노텍 | 1,145,000원 | KB 1,600,000원 | FC-BGA, 그룹 동반 급락이나 성장성 긍정 |\n| 한화오션 | 128,400원 | — | 조선 슈퍼사이클, 공시 확인 전 추격위험 |\n| SpaceX | $185.00 | $63~$190 | 6/26 MSCI vs 8월 락업 |\n\n### 현금 배분 (624,771원, 3분할 미집행)\n- **🅰️ 관망 (룰 정합·추천)**: 외인 6/19 순매도 전환 + 6/22 갭 + 다음주 이벤트 클러스터 → **전액 보존.** MU 6/23 저녁 절반차익 베이킹만 능동 액션.\n- **🅱️ 공격**: 6/22 외인 재유입 + 코스피 9천 사수 확인 시에만 NAVER 소액 100,000원(225~235k 하단).\n\n### 2주 일정 (폰 가용 17:30~20:50 KST)\n| 날짜 | 이벤트 | 폰 |\n|---|---|---|\n| 6/22(월) | 美 재개 갭 / SK하이닉스 ADR SEC 승인 주 / **외인 재유입 재검증** | ❌야간 |\n| **6/23(화) 저녁** | **MU 절반차익 사전 베이킹** + 글로벌 PMI·MSCI 검토 | ✅ |\n| **6/25(목)** | **분수령 — 새벽 MU 실적 + 밤 美 PCE** | ❌야간(베이킹) |\n| 6/26(금) | 미시간 소비심리·러셀 리밸런싱 | ✅오전 |\n| 7/16(목) | 한은 금통위(2.50→2.75% 전망) | ✅오전 |\n\n## 🎯 결론\n**경제사냥꾼 6/20 3편이 한목소리로 \"다음주(6/22~26)가 코스피 9천=반도체 한 기둥이 진짜인지 세계가 동시 검증하는 주간\"이라 짚었고, MU 도이체방크 $1,500 상향은 교차검증으로 사실 확인됐다.** 이건 정훈의 6/24(정확히는 6/25 새벽) MU 절반차익 트리거와 정확히 정합 — 단 DB·씨티 목표 상향이 \"전량 홀딩\" 명분도 동시에 강화하니 6/23 저녁 폰창에서 정훈이 절반/홀딩 택1. 💪 코어는 그대로, 현금 62만 전액 보존, 9천 착시·과속·외인 확인 전 추격 금지. 다음주는 MU·PCE·하이닉스 美상장이 한 주에 몰린 이벤트 클러스터 — **추격 대신 베이킹과 확인.**\n\n---\n\n[STATE SNAPSHOT v21 2026-06-20]\n현금: 624,771원 (트랜치 1차/2차/3차 전부 미집행 — 3차 FOMC 매파 보류, 1차 NAVER 매수존 발동했으나 정리후보+외인 순매도→6/22 재유입 확인까지 보류)\n보유변동: 없음 (주말 휴장)\n워치리스트(활성): SK하이닉스·삼성전기·GEV·두산에너빌리티·LG이노텍·한화오션·SpaceX\n대기 트리거: ①6/22 외인 재유입+SK하이닉스 美 SEC 승인 ②6/23 저녁 MU 절반차익 베이킹 ③6/25 새벽 MU 실적+밤 PCE(분수령) ④코스피 안전핀 7,500\n영구교정: 경제사냥꾼 6/20 신규 — MU 도이체방크 $1,500 상향 [검증], 구글+블랙스톤 $25B JV는 5/19 발표(신규 아님). 하이닉스 영업이익률 72%·노무라 코스피 1.1만은 [미확인].\n다음 버전: v22\n\n*투자 자문 아님 · 모든 레벨은 분석 참고 · 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v20_addendum_2026-06-20",
      "file": "docs/reports/report_v20_addendum_2026-06-20.md",
      "title": "정훈 PORTFOLIO DESK · v20 부록 · 2026-06-20 — 이슈 4개 심층",
      "date": "2026-06-20",
      "version": 20,
      "kind": "보고서",
      "preview": "SoftBank ──(ARM 지분 90% 담보)── 대출한도 ~$185억 확대",
      "content": "# 정훈 PORTFOLIO DESK · v20 부록 · 2026-06-20 — 이슈 4개 심층\n\n> 본문 `report_v20_2026-06-20.md`의 §8 이슈 선택지 4개 전부 심층. 투자 자문 아님, 최종 결정은 정훈.\n\n---\n\n## 이슈 1 — 6/24 MU 실적 베이킹 매뉴얼 확정\n\n**일정·제약**: MU 회계 Q3 실적 = **6/24(수) 美 장 마감 후**(KST 6/25 새벽) → **정훈 폰 미가용(17:30~20:50 밖)** → **6/23(화) 저녁 폰창에서 사전 베이킹 필수.** 토스 미국 소수점 = 시장가만(지정가 불가)이나 0.04주는 분수주 시장가 매도 예약 가능.\n\n**숫자 정리**:\n| 항목 | 값 |\n|---|---|\n| 회사 가이드 | 매출 $33.5B(±$750M) · EPS $19.15 · GM ~81% |\n| Street 컨센 | 매출 ~$34.8B · EPS ~$19.82 (애널 레인지 $33.7B~$40.9B = 매우 넓음) |\n| 현 주가/원가 | $1,133.99 / $749 → **+51.4%** |\n| 목표가 이원화 | 구컨센 ~$612 ↔ 신컨센 UBS $1,625·Stifel $1,500·Wedbush $1,300·TD Cowen $1,500·Citi/RBC $1,200·MS $1,050 |\n- → **회사 보수 가이드 < Street 컨센 = 인라인~비트 베이스라인**(beat 기대 이미 주가에 내재). 현주가 > 다수 목표 = **이미 강세 하우스로 리프라이싱**.\n\n**⚠️ 포지션 실익(중요)**: MU 보유 = **0.04주, 평가액 ≈ $45(약 6.9만원)**. 절반 차익 = 0.02주 ≈ **$22(약 3.4만원)**. **금액 임팩트는 미미** → 이번 절반차익의 본질은 손익이 아니라 **①집중도(HBM 6중 쏠림) 완화 규율 ②\"고평가+이벤트 전 절반 빼기\" 디시플린 훈련**이다.\n\n**시나리오 (메모리 실적 통상 ±8~12% 갭, MU 옵션 IV 구체치 미확인)**:\n| 결과 | 주가 반응 | 홀딩분(0.02주) 영향 |\n|---|---|---|\n| **비트 + 가이드 상향**(HBM ASP↑) | +10%↑ | 탈순환주 내러티브 강화, 홀딩분 추가수혜 |\n| **인라인**(컨센 부합) | −5~10%(sell-the-news) | 절반 차익이 보호 |\n| **미스/가이드 실망** | −10%↑ | 선반영분 큰 되돌림, 절반 차익이 헤지 |\n\n**경제사냥꾼 7편 정합**: 채널 ①(ARM)·④(삼성)가 공통으로 **\"6/24 MU가 AI수요 진위 분수령\"**·\"ARM PER 500배 옆에서 MU 10배 = AI 길목주 중 가장 싼 구간\"이라 짚음 → **펀더 베이스는 강세, 단 단기 sell-the-news 리스크는 별개**. 채널 \"일반 DRAM 판가 +90%\"는 MU에도 직접 호재(HBM 외 레거시 DRAM 레버리지).\n\n**🎯 결론 — 6/23 저녁 택1 (PM 권고: 규율상 절반차익 약간 우위)**:\n- **(A) 절반차익 베이킹** ✅추천: 6/23 저녁 0.02주 시장가 매도 예약. 인라인 sell-the-news 헤지 + 비트 시 잔여 0.02주 수혜의 비대칭 + 집중도 완화. **금액 작아도 \"고평가에서 절반 빼는 디시플린\"이 핵심.**\n- **(B) 전량 홀딩**: 슈퍼사이클 베팅·금액 작아 변동성 감내. 채널 강세 프레임에 베팅 시 합리.\n- ⛔ **하지 말 것**: 6/24 당일 밤 수동 대응(폰 미가용·당일 밤 트리거 금지 룰), 실적 전 추가매수(추격).\n\n---\n\n## 이슈 2 — 외인 순매도 = 추세인가 FTSE 기계적인가?\n\n**현상(확정)**: 6/19 외인 코스피 **≈−3,800억 순매도**(서경 −3,647·fn −3,884·ddaily −3,523 수렴), 기관 −1.23조·개인 +1.65조. v19까지 외인은 6/12~16 순매수(엔진)였고 6/17 −9,924억(1일)→6/18 +1.28조 복귀였음 → **6/19 다시 순매도 = 5거래일 중 순매도 2일.**\n\n**성격 판별 — \"기계적 vs 추세\" 양면**:\n| 기계적(일회성) 근거 | 추세(구조) 근거 |\n|---|---|\n| **FTSE 지수 정기 리밸런싱**(6월 분기 리뷰) 장 막판 매물 — 코스피 비중조정 | 경제사냥꾼 ④: **외인 한달 50~57조 순매도→개인 40조 받아냄** = 한 달 누적 매도 추세 |\n| **코스닥은 외인 +4,873억 순매수**(코스피→코스닥 직접 로테이션 아닌 비중조정) | 코스피 사상최고권(9천)·환율 1,530 = 외인 환차익 실현 유인 |\n| 매도가 펀더 훼손 종목 아닌 지수 비중 기계적 | 개인이 받는 구도 = 통상 랠리 후반 신호 |\n\n**핵심 스위치 — 6/22 확인법**: KRX 투자자별 매매동향(data.krx.co.kr) →\n- ✅ **외인 순매수 재전환** = 6/19은 FTSE 일회성, \"엔진\" 복귀 = 강세 유지\n- 🔴 **외인 순매도 지속(2일째)** = \"외인=메인엔진\" 신호 약화 = 신중 가중\n- ⚖️ 보합/소액 = 판단 보류, 6/24 MU·MSCI 후 재평가\n\n**강세 논지 하향 임계치(누적)**: **외인 2~3거래일 연속 순매도 + 코스피 8,000 하회 동반** 시 강세 비중 하향. 현재는 코스피 9,052(미충족)·외인 순매도 비연속(6/18 매수 끼임) → **아직 옐로카드, 레드 아님.**\n\n**🎯 결론**: **6/19 순매도는 \"FTSE 기계적\" 무게가 더 크나(코스닥 외인 매수가 방증), \"엔진 균열\" 경계 신호로 인지.** 6/22 외인 종가가 일회성/추세 확정 분수령 — **확인 전 신규 진입 보류(NAVER 포함), 보유는 홀딩.** 6/22가 순매도 2일째면 강세 비중 점진 하향 검토.\n\n---\n\n## 이슈 3 — SK하이닉스 ADR(6/22주)이 보유 삼성·NVDA·MU에 미치는 영향\n\n**팩트(경제사냥꾼 ⑤ + 외신 검증)**: SK하이닉스 **NYSE/NASDAQ 정식 ADR 상장 추진** — SEC 승인 **6/22주 거론**, 빠르면 **8월 거래**, 조달 **최대 $14B**, HBM 점유 **57% 세계 1위**, 모건 27년 fwd PER **~6.9배 vs 필반 27배**(코리아·메모리 디스카운트). 현재는 OTC 비후원 ADR 'HXSCL'(저유동성·소수점 불가)뿐.\n\n**보유 종목별 영향**:\n| 보유 | 영향 | 방향 |\n|---|---|---|\n| **삼성전자** | ⑤ \"삼성 프리미엄 일부 잠식\" 경고 — 글로벌 투자자가 HBM 1위 하이닉스에 직접 접근 가능해지면 HBM 대표주 지위 일부 이전. 단 삼성은 HBM4 Rubin+AMD 지명으로 '26 점유 회복 중 | 🟡 약한 신중(경쟁 가시성↑) |\n| **NVDA** | 하이닉스 = NVDA Rubin HBM4 54~70% 공급사. 하이닉스 美상장 = HBM 공급망 자본 확충·증설 가속 = NVDA 공급 안정 | 🟢 간접 호재 |\n| **MU** | ⑤ \"메모리 디스카운트 해소\" 내러티브 = MU도 같은 HBM 3사 = **동반 리레이팅 가능**(하이닉스 PER 6.9배 부각 시 MU 10배도 정당화). 6/24 MU 실적과 6/22주 ADR이 **같은 주 HBM 모멘텀 클러스터** | 🟢 동조 호재 |\n\n**⚠️ 새 리스크 — \"밤사이 변동성 수입\"**: ⑤ 핵심 = ADR 상장 후 **하이닉스 가격이 밤사이 나스닥에서 먼저 결정→다음날 코스피 개장에 반영**. 보유 삼성·NVDA·MU + 코스피의 **동조성 심화** = 정훈 트리거(코스피 안전핀·매수존)가 美 야간 HBM 흐름에 더 민감해짐. 폰 미가용 야간 변동성 비대칭 연동.\n\n**🎯 결론**: **HBM 3사 동반 리레이팅 = 보유 삼성·NVDA·MU에 중장기 순호재**(메모리 디스카운트 해소 내러티브). 단 ①삼성 프리미엄 일부 잠식 ②코스피-나스닥 동조성 심화(야간 변동성)는 모니터. **액션은 없음** — 추격금지(목표 +50% 초과·상장 전 OTC 소수점 비추), **정식 상장(8월) 후 토스 美 소수점 소액 적립 검토**가 정공법. 6/22 SEC 클리어런스 뉴스만 트래킹.\n\n---\n\n## 이슈 4 — ARM 레버리지 플라이휠 = AI 버블 신호인가?\n\n**구조(경제사냥꾼 ① + Reuters 검증)**: \n```\nSoftBank ──(ARM 지분 90% 담보)──> 대출한도 ~$185억 확대\n    │                                    │\n    └──> OpenAI 투자 ~$300억 <───────────┘\n             │\n             └──> Stargate(데이터센터) $5,000억 약정\n                      │\n                      └──> AI 칩·인프라 수요 → ARM 라이선스↑ → ARM 주가↑ → 담보가치↑ → (순환)\n```\n손정의 NVDA 지분 **전량 매도**(현금 확보)→ARM·OpenAI에 집중. ARM PSR 90배·**PER 500배** vs MU 10배·하이닉스 6~7배.\n\n**버블 신호인가 — 양면**:\n| 🔴 버블 우려 | 🟢 반론 |\n|---|---|\n| 담보(ARM주가)-대출-투자가 **자기참조 순환** = 주가 하락 시 담보가치↓→마진콜→연쇄 디레버리징 위험 | ARM은 실제 현금흐름(스마트폰칩 99%·라이선스) 있는 우량주, 닷컴 무수익과 다름 |\n| ARM PER 500배 = 완벽한 성장 선반영, 실망 시 급락 | SoftBank 차입은 ARM 지분의 일부만 담보(전량 아님), 즉시 마진콜 구간 아님 |\n| OpenAI·Stargate 약정은 **미래 현금**(아직 미실현) | NVDA·MSFT·Oracle 등 실제 capex 집행 중 = 수요는 실재 |\n\n**보유 종목 집중도 점검(핵심)**: 정훈 포트는 이 플라이휠과 **간접 연결**:\n- **NVDA**(코어) — AI 칩 수요 = 플라이휠 최종 수혜. 단 손정의 전량매도는 \"밸류 부담\" 시그널일 수도(단일 투자자 판단).\n- **MSFT·META·ORCL**(보유) — AI capex 집행 주체. capex 사이클 둔화 시 동반 조정.\n- **MU·AVGO·ANET·삼성**(코어) — AI 인프라 공급. 수요 지속에 베팅.\n- → **포트 16종목 중 사실상 10+종목이 \"AI 인프라 수요 지속\"이라는 단일 매크로 가정에 연동.** ARM 플라이휠이 깨지면(OpenAI 자금난·Stargate 지연) **동반 변동.**\n\n**🎯 결론**: **\"버블 vs 실수요\"는 6/24 MU가 1차 리트머스**(채널도 동일 지적) — MU 실적이 HBM 실수요를 확인하면 플라이휠 펀더 뒷받침, 실망하면 버블 우려 부각. **정훈 액션: ①집중도 인지(AI 단일 가정 10+종목)가 MU 절반차익·현금 보존의 근거 강화 ②ARM 직접 진입은 비대상(PER 500배·추격금지) ③모니터 지표 = OpenAI 자금조달 진행·Stargate 착공·빅테크 capex 가이던스(7/29 삼성·META·MSFT 실적).** 버블 신호로 단정하기엔 실 capex가 받치지만, **\"단일 매크로 가정 과집중\"은 분명한 구조적 리스크** → 분산(전력·피지컬AI·VOO)과 현금이 헤지.\n\n---\n\n*투자 자문 아님. 모든 레벨은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v20_2026-06-20",
      "file": "docs/reports/report_v20_2026-06-20.md",
      "title": "정훈 PORTFOLIO DESK · v20 · 2026-06-20",
      "date": "2026-06-20",
      "version": 20,
      "kind": "보고서",
      "preview": "1. 6/24 MU 실적 베이킹 매뉴얼 확정 — 절반차익(+51%) vs 전량홀딩, 비트/인라인/미스별 주가(컨센 이원화 $612 vs $1,200~1,500), 6/23 저녁 소수점 시장가 예약 구체화. 경제사냥꾼 7편 \"AI수요 분수령\" 프레임 반",
      "content": "# 정훈 PORTFOLIO DESK · v20 · 2026-06-20\n\n> 투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.\n> **데이터 기준**: KR=**6/19 마감**(주말 미변동) / US=**6/18 종가**(6/19 美 준틴스 휴장·6/20 주말 → 미국 시세 갱신 없음) / USD/KRW **~1,530**. 6개 데스크(지역2·매크로·리서치·리스크 + 정량스크립트3) 종합.\n> ⚠️ 이번 보고서 = **정훈 강조 \"경제사냥꾼 꼭 검토\"** → 신규 7편 자막 전량 확보 심층(§4) + **v19 미확인이던 6/19 외인 수급 확정**(순매도 전환) + **코스닥 정정**.\n\n---\n\n## 변경점 (직전 v19 대비)\n\n- **🔴 [분수령 답] 6/19 외인 코스피 순매도 전환 확정** — v19에서 \"미확인 → 6/22 분수령\"이라던 6/19 당일 수급이 확정됐다. **외인 코스피 약 −3,800억대 순매도**(서경 −3,647·fn −3,884·ddaily −3,523 다수 수렴, 잠정 −9,831억은 폐기), **기관 −1.23조·개인 +1.65조.** **외인 순매수 행진 종료.** 단 배경이 **FTSE 지수 리밸런싱 장 막판 기계적 매물**(코스닥은 외인 +4,873억 순매수) → 펀더 훼손 아닌 기계적 성격, **추세 훼손 단정은 일러 6/22 재유입 여부가 진짜 확인선.**\n- **🔧 [영구정정] 코스닥 6/19 = −3.43%**(34.34p↓, 6거래일 만 1,000선 붕괴). **v19의 −6.33%는 Yahoo prev_close 오류** → 확정치 −3.43%로 정정(코스피 −0.13%는 일치). 디커플링은 여전하나 폭락 강도는 v19 서술보다 완만.\n- **🔧 [정정검토] MSCI 발표일 6/24 → 6/23(전후)** — 매크로 데스크: 시장**접근성 점수는 6/18 선공개**(마이너스 18→17개·1개 개선), **연례 시장분류 발표는 6/23(한국 새벽 추정)**. v19 \"6/24 05:30\"에서 정정 검토(MU 실적 6/24와는 별도일). *날짜는 6/23~24 클러스터로 인지, 최종 6/22 재확인.*\n- **🟢 경제사냥꾼 신규 7편 전체 분석**(§4) — ARM 레버리지 플라이휠·삼성그룹 \"국민기업\" 사이클론·SK하이닉스 ADR·Intel+Apple 테라팹·캐시우드 TSLA·G7 앤스로픽 AI금수·삼성전기 KB 300만원. **공통 메시지: \"6/24 MU = AI수요 진위 분수령\"**(정훈 절반차익 트리거와 정확히 정합).\n- **시세 미변동**: 주말+美 휴장으로 보유 16종목 가격은 v19와 동일(평가손익 ≈ +305,371원, 환차익 반영 ≈ +589,520원).\n\n---\n\n## 1. 시장 — 국장 / 미장\n\n### 국장 (6/19 마감, 주말 미변동)\n- **코스피 9,052.42(−0.13%)** — 장중 사상최고 **9,385.59** 찍고 **−553p 급반락**, 9천 방어(시총 첫 8,000조 돌파). **코스닥 966.59(−3.43%, 이틀째 급락·1,000선 붕괴).** 급반락 트리거 = ①벤스 부통령 스위스행 연기·이란 불참(호르무즈 60일 합의 흔들) ②반도체 쏠림 차익실현 ③美 휴장·세마녀.\n- **🔑 6/19 수급(확정)**: **외인 코스피 ≈ −3,800억 순매도(순매수 행진 종료)** / 기관 −1.23조 / 개인 +1.65조. **코스닥은 외인 +4,873억 순매수**(FTSE 리밸런싱이 코스피→코스닥 비중조정). → **기계적 매물 성격이나 \"외인=메인엔진\" 신호 1차 균열** = 신중 가중. **6/22 외인 재유입이 강세 논지 진짜 분수령.**\n- 디커플링 지속: **코스피 상승 115 vs 하락 787(86% 하락)** — 반도체 대형주(삼성·SK하이닉스·삼성전기) 독주 vs 중소형/코스닥 소외. SK하이닉스 사상최고 경신. 예외 선전: 현대차 +2.00%·한화오션 +2.64%.\n\n| 국내 보유 | 티커 | 현재가 | 당일(6/19) | 원가대비 |\n|---|---|---|---|---|\n| 삼성전자 | 005930.KS | 354,000 | −2.34% | **+34.6%** |\n| LG전자 | 066570.KS | 211,500 | **−7.44%** | **+36.3%** |\n| 두산로보틱스 | 454910.KS | 101,800 | −0.88% | +1.8% |\n| 현대차 | 005380.KS | 613,000 | **+2.00%** | −2.7% |\n| NAVER | 035420.KS | 229,500 | −2.34% | −8.4% |\n\n### 미장 (6/18 종가 — 6/19 준틴스 휴장 + 6/20 주말)\n- **S&P500 7,500.58(+1.08% 신고가권) · 나스닥 26,517.93(+1.91%) · 다우 51,564.70(+0.14%) · 필반(SOX) 14,341.78(+6.42% 폭등).** FOMC 매파 셀오프(6/17) 완전 되돌림 — **반도체·메모리 단독 주도**(다우 +0.14% 구경제 소외). **6/22(월) 재개장 갭 리스크**: 매파 점도표 누적 소화 미완 + 3거래일 휴장 + 칩랠리 과열.\n- **MU +8.70%가 엔진**(6/24 실적 D-4). 목표가 폭증 러시(Stifel $550→$1,500·Wedbush $550→$1,300·Rosenblatt $600→$1,200, 전부 Buy) ↔ 컨센 평균은 더 낮음 = 강세 하우스 선반영.\n\n| 미국 보유 | 현재가($) | 당일(6/18) | 원가대비($) |\n|---|---|---|---|\n| NVDA | 210.69 | +2.95% | +5.6% |\n| META | 577.22 | +1.70% | **−9.0%** |\n| VOO | 688.11 | +0.98% | +6.6% |\n| MSFT | 379.40 | +0.13% | −7.5% |\n| AAPL | 298.01 | +0.70% | **+15.9%** |\n| GOOGL | 368.03 | +1.17% | −5.1% |\n| TSLA | 400.49 | +1.04% | −5.2% |\n| ORCL | 184.29 | +0.41% | **−20.6%** |\n| ANET | 169.67 | +2.87% | +4.7% |\n| MU | 1,133.99 | **+8.70%** | **+51.4%** |\n| AVGO | 411.35 | **+4.70%** | −2.3% |\n\n---\n\n## 2. 섹터 — (주말·시세 미변동 → 지역 데스크 시세로 갈음, 신규 트리거 없음)\n\n> 6/20 주말·美 휴장으로 섹터 데스크 별도 호출 없음(v19 분석 유효). 단 경제사냥꾼발 신규 테마 3종을 §4·§7에 반영: **①SK하이닉스 ADR(6/22주 SEC) — 코스피-나스닥 동조성 심화 ②Intel+Apple 테라팹 — 삼성 파운드리 양날 ③삼성전기 KB 300만원 상향**. MU 6/24 실적(반도체)·MSCI 6/23(국장)이 다음 주 핵심.\n\n---\n\n## 3. 매크로 데스크\n\n- **USD/KRW ~1,530(무키 1,529.89, −0.59%)** — 1,500 여전히 미하회. 원화 소폭 강세(FOMC 매파 진정+MSCI 기대 외인) but 1,520~1,530 고착 = 미국주 환산단가 부담 지속.\n- **금리**: FOMC 매파 \"hawkish hold\" 소화 — 점도표 2026 중간값 **3.4→3.8%**(위원 절반 연내 인상). **10년물 4.45~4.49% · 2년물 ~4.2%대(상방편향) · DXY ~100.8~101(1년 고점권).** 채권·달러 모두 지지 = EM·원화 역풍 잔존. (한은은 점도표 없음 — 연준 전용.)\n- **유가**: 브렌트 **~$80** · WTI **~$77로 반등** — 호르무즈 통항 정상화로 주간 급락했으나 **美-이란 스위스 회담 취소→리스크프리미엄 재유입**(추가 진전 아닌 불확실성 재부각). CPI 에너지 경로엔 여전히 우호(고점 대비 진정). 다음 美 CPI/PPI = **7/14·7/15 21:30 KST**(2주 내 없음).\n- **엔캐리**: USD/JPY ~161(BOJ 1.0% vs Fed 3.50~3.75%, 정책차 250~275bp). 점진 unwind, 6/19 무탈하나 6/22 갭과 겹치면 변동성 주시.\n- **⚠️ MSCI 정정**: 접근성 점수 **6/18 선공개**(마이너스 18→17개), 시장분류 발표 **6/23(전후)**. 기대 = **관찰대상(watch list) 등재**(승격 자체 아님, 정식 편입은 2027~2028) → 6/23은 \"선반영 해소\" 변동성 구간 = **추격금지 적용**.\n\n---\n\n## 4. 리서치 피드 — 경제사냥꾼 (★정훈 강조 · 신규 7편 자막 전량 확보)\n\n> v19에서 SSL 차단으로 못 봤던 6/19 쇼츠 5편 + 신규 롱폼 2편(ARM·삼성그룹) **ko 자막 전량 추출 성공**(폴백+insecure 재시도 우회). 트랙레코드 **개선세 지속**(과장 자진경계·양면제시). 누적 로그 `docs/research/hunter_log.md` 갱신 완료.\n\n| # | 영상 | 핵심 주장 | 분류 |\n|---|---|---|---|\n| ① | **ARM \"젠슨황 61조 들고도 못 산 독점기업\"** | NVDA ARM 인수 무산→2023 독립. **SoftBank ARM담보 대출한도 ~$185억→OpenAI($300억)·스타게이트($5,000억) \"레버리지 플라이휠\"**. 손정의 NVDA 전량매도. ARM PER 500배 vs MU 10배·하이닉스 6~7배. **6/24 MU=AI수요 분수령** | **[검증]** 핵심 일치(한도 영상 \"$200억\"은 근사). 밸류 대비 = **보유 MU·워치 하이닉스 저평가 부각=강세 보강** |\n| ② | **인텔+애플 협력=한국 반도체 호재** | 트럼프 애플-인텔 파운드리·정부 인텔 10%지분·NVDA·머스크 **테라팹**. 수혜 HPSP·한미반도체 | **딜 골격 [검증]**(CNBC/Tom's, 애플·인텔 공식 미확인) / 장비주 납품 **[미확인]**. **삼성 파운드리 양날, NVDA 호재** |\n| ③ | **오늘 코스피 급락 진짜 이유** | 9,385 신고가→−500p 급락·시총 8,000조. 원인=벤스 스위스행 연기(호르무즈 흔들)+반도체 차익+美휴장 세마녀. \"레버리지 줄여라\" | **[검증·방향]** 6/19 급반락 일치. **추격금지·안전핀 룰 정합** |\n| ④ | **삼성그룹 \"국민기업\"** ★국장 | 삼성+하이닉스 시총 54%(우선주 57%). **외인 한달 50~57조 순매도→개인 40조 매수**. 진짜 돈=**일반 DRAM 판가 +90%(트렌드포스)**. 하나證 삼성 2Q 92조(공격적). 2028 증설→공급과잉 경고 | **[검증]** 다수 일치. 92조 \"가장 공격적\" **자진 단서=트랙 개선**. **★보유 삼성 직결: 사이클 위치론** |\n| ⑤ | **SK하이닉스 美상장 영향** ★워치 | **ADR SEC 승인 6/22주·8월 거래·조달 $14B·HBM 57%·27년 PER ~6.9배 vs 필반 27배**. 밤사이 나스닥 가격선결정→코스피 변동성 수입 | **[검증]** 전부 일치(Reuters/CNBC). **보유 삼성·NVDA·MU와 코스피 동조성 심화** |\n| ⑥ | **테슬라 6배 ($2,600)** 캐시우드 | ARK 2029 목표 $2,600(현가 6배)·로보택시 가치 90%. 머스크 의결권 19.9% | **[검증·시점]**(ARK base는 $4,600 더 공격적). **단 우드 최근 TSLA 차익매도 중인 점 영상 미언급**. ★보유 TSLA |\n| ⑦ | **G7→한국 반도체 호재** | G7서 美 **앤스로픽 AI모델 수출통제(첫 AI금수)**·마크롱 반발. \"믿을나라끼리\" 반도체동맹→HBM 한국 몸값↑ | **[검증]**(Al Jazeera 6/19). ★보유 삼성·NVDA+워치 하이닉스 수혜 프레임 |\n\n**+추가 교차검증**: **삼성전기(워치) KB 목표 220만→300만원(+36%) 상향 확정** — MLCC·기판 초호황 + **중일 희토류 갈등→일본 MLCC 차질 반사이익**(워치 활성 강화, 단 고점 추격 경계).\n\n> **채널 오늘 시각**: \"코스피 9,000=삼성·하이닉스 두 종목(57%)이 만든 착시, 봐야 할 건 ①사이클 위치 ②돈의 흐름 순서 ③美 의존 구조.\" 거시는 **\"6/24 MU가 AI수요 말잔치냐 실제 현금이냐 분수령\"**(정훈 절반차익 트리거와 정확히 일치), 지정학은 \"G7 AI금수→HBM 한국 몸값↑.\" **6/19 오후 급락을 실시간 반영해 \"고점추격·레버리지 경계\"로 톤다운 = 정훈 추격금지·안전핀 룰과 정합.**\n\n---\n\n## 5. 리스크 데스크 (신중/bear)\n\n- **🚦 트리거**: 안전핀 7,500 **미발동**(현 9,052, +20.7% 여유) / 2차 8,000(+13.2%) 대기 / 삼성 매수존 295~305k(현 354k, +16% 위) / 두산E 10만(현 97,900, −2.1% 근접·추격금지) / **🔴 NAVER 1차 매수존(229,500∈225~235k) = 유일 발동** / FOMC 3차 트랜치 = **매파 보류 확정**.\n- **🚨 위반 없음 / 룰3(추격매수 금지) 고강도 적용일**: 코스피 9천·MU +51%·SOX +6.42% = 전형적 FOMO 클러스터. **매파 확정 상태의 위험자산 급반등 = 기술적 되돌림**(점도표 인상·DXY 100.8·2년물 그대로) → 현금 624,771원 전액 동결 정당. 레버리지 0건.\n- **🔴 [신규] 외인 순매도 전환 = bear 가중**: v19 \"외인 엔진\"이 6/19 −3,800억 순매도로 1차 균열(FTSE 기계적이라 단정은 일러도 모멘텀 신호). + 경제사냥꾼 ④가 짚은 **\"외인 한달 50~57조 순매도→개인 40조 받아냄\"** = 수급 주체 개인 이동 = 후반부 신호 가능성. **6/22 외인 재유입이 진짜 확인선.**\n- **🔴 집중도(사실상 단일 포지션)**: AI 메모리/HBM **6중 쏠림**(삼성·NVDA·MU·AVGO·SK하이닉스·삼성전기) + 미국 11종목 단일 원/달러 환노출. **MU +51%로 비중 자동 확대 → 6/24 단일 야간 이벤트(폰 미가용)에 비대칭 연동.** + 경제사냥꾼 ①의 **ARM 레버리지 플라이휠**(SoftBank-OpenAI-Stargate) = NVDA·MSFT·META 동반 변동 리스크. **MU 절반차익 = 집중도 완화 유일 능동 수단.**\n- **bear 핵심**: 강세론 최대 약점 = **상승의 질.** 코스피 9천은 시총 4사 59.6%·상승 115 vs 하락 787·코스닥 −3.43%가 보여주듯 반도체 4종목이 떠받친 극단 디커플링. 美 SOX +6.42%는 매파 셀오프의 기술적 되돌림. **외인 6/19 순매도 전환 + 6/22 美 재개장 갭 + 호르무즈 회담 취소 재부각 = 4일 급등의 되돌림 방아쇠.** 경제사냥꾼이 부추기는 FOMO 테마(하이닉스 ADR·조선 슈퍼사이클·캐시우드 TSLA·삼성전기 +740%)는 전부 **룰3 추격금지 대상** — 방향성은 채택, 당일 진입은 회피.\n\n---\n\n## 6. 강세 vs 신중 디베이트\n\n**강세(bull)**: FOMC 매파는 1일천하 — 6/18 SOX +6.42%·MU +8.70%·AVGO +4.70%로 셀오프 완전 되돌림. MU 목표 $1,200~1,500 상향 러시·HBM sold out = 탈순환주 리프라이싱. 경제사냥꾼이 짚듯 **ARM PER 500배 옆에서 MU 10배·하이닉스 6~7배 = AI 길목주 중 가장 싼 구간**, 일반 DRAM 판가 +90%, G7 AI금수→HBM 한국 몸값↑, SK하이닉스 ADR(필반 편입 기대). MSCI 관찰대상 등재 기대 = 코스피 2년 체질개선 흐름. 코어 견조(MU +51%·삼성 +35%·LG전자 +36%·AAPL +16%).\n\n**신중(bear)**: 코스피 9천은 두 종목(57%)이 만든 착시 — 상승 115 vs 하락 787·코스닥 1,000선 붕괴. **외인 6/19 순매도 전환(엔진 1차 균열) + 외인 한달 50~57조 순매도를 개인이 받는 구도 = 수급 주체 약화.** SOX 반등은 기술적 되돌림(점도표 인상·DXY 100.8 그대로). AI 메모리 단일 테마+단일 환노출 과집중(MU +51%로 6/24 비대칭 연동) + ARM 레버리지 플라이휠 순환 리스크. 6/22 갭·호르무즈 회담 취소·MSCI 6/23 선반영 해소가 되돌림 방아쇠.\n\n**PM 저울질**: 코어 강세 논지(AI 슈퍼사이클·MU 길목주 저평가)는 **유지**. 단 **외인 순매도 전환으로 \"상승의 질\" 신중 가중** — 6/19 분수령이 (기계적이지만) 순매도로 찍힌 만큼 **6/22 외인 재유입 확인이 강세 논지 갱신 조건.** 추격 금지·현금 보존·이벤트 확인이 정석. (무게는 PM 종합 §7.)\n\n---\n\n## 7. PM 종합 (최종)\n\n### 🎯 오늘의 한 줄 결론\n**경제사냥꾼 7편 공통 결론 = \"6/24 MU가 AI수요 진위 분수령\"으로 정훈 절반차익 트리거와 정확히 일치. v19 미확인이던 6/19 외인 수급은 순매도 전환(−3,800억, FTSE 기계적)으로 찍혀 강세 엔진에 1차 균열 — 추격 금지·현금 62만원 전액 보존, NAVER 매수존조차 6/22 외인 재유입 확인 후. MU 6/24 절반차익(6/23 저녁 베이킹)이 유일한 능동 액션. 다음 주 = MU 6/24·MSCI 6/23·SK하이닉스 ADR 6/22주·美 재개장 갭 클러스터.**\n\n### 보유 16종목\n\n| 종목 | 현재가 | 당일 | 원가대비 | 목표가(컨센) | 상방 | 매수존 | 매도/트림 | ⭐ | 한줄 |\n|---|---|---|---|---|---|---|---|---|---|\n| 삼성전자 | 354,000 | −2.34% | +34.6% | 48~53만(KB/미래) | +36~50% | 295~305k(이탈) | 트림보류 | ⭐⭐⭐⭐ | 사이클 중반·일반DRAM +90% 레버리지, 코어 |\n| LG전자 | 211,500 | −7.44% | +36.3% | 컨센 초과 | — | 홀딩 | 손절선 없음 | ⭐⭐⭐⭐ | 그룹 동반 차익실현·펀더 무손상=홀딩 |\n| 두산로보틱스 | 101,800 | −0.88% | +1.8% | 극단분산 | — | 관망 | 모멘텀 | ⭐⭐ | 전일 −15% 모멘텀, 추격금지 |\n| 현대차 | 613,000 | +2.00% | −2.7% | 60만(공격 80만) | +0~30% | 관망 | — | ⭐⭐⭐ | BD 풋옵션 7/20·삼성 지분설, 반등 |\n| NAVER | 229,500 | −2.34% | −8.4% | ~30만(메리츠 41만) | +31% | **225~235k(진입🔴)** | 정리후보 | ⭐⭐ | 매수존 진입 but 정리후보=소액/6/22 대기 |\n| NVDA | $210.69 | +2.95% | +5.6% | $298.93 | +41.9% | 눌림 | 비중관리 | ⭐⭐⭐⭐⭐ | Rubin HBM4 3사인증·테라팹 호재, 코어 |\n| META | $577.22 | +1.70% | −9.0% | $827.32 | +43.3% | 실적확인 | — | ⭐⭐⭐⭐ | 고유악재 회복(노이즈), 7/29 전 보류 |\n| VOO | $688.11 | +0.98% | +6.6% | — | — | 적립 | — | ⭐⭐⭐⭐ | 분산형 코어(채널도 '안전') |\n| MSFT | $379.40 | +0.13% | −7.5% | $561.39 | +48.0% | 눌림 | — | ⭐⭐⭐⭐ | 상방 최대, 6/18 빅테크 중 소외 |\n| AAPL | $298.01 | +0.70% | +15.9% | $312.72 | +4.9% | 목표근접 | **트림 1순위** | ⭐⭐⭐ | 금리방어·인텔딜 협력 당사자 |\n| GOOGL | $368.03 | +1.17% | −5.1% | $432.83 | +17.6% | 눌림 | — | ⭐⭐⭐⭐ | Cloud·Gemini, 반독점 노이즈 |\n| TSLA | $400.49 | +1.04% | −5.2% | $420.55(ARK 2029 $2,600) | +5.0% | 관망 | — | ⭐⭐⭐ | 캐시우드 강세 but 우드 차익매도 중, 균형 |\n| ORCL | $184.29 | +0.41% | −20.6% | $252.64 | +37.1% | 눌림 | 패닉셀 금지 | ⭐⭐⭐ | RPO $638B 백로그, OpenAI 54% 집중 |\n| ANET | $169.67 | +2.87% | +4.7% | $189.13 | +11.5% | 홀딩 | — | ⭐⭐⭐⭐ | AI 네트워크, 목표 상향 |\n| MU | $1,133.99 | +8.70% | +51.4% | $879→상향중($1,200~1,500) | (리프라이싱) | **6/24 실적** | **절반 차익** | ⭐⭐⭐⭐ | 채널 \"AI수요 분수령\", +51% 6/24 절반차익 |\n| AVGO | $411.35 | +4.70% | −2.3% | $522.06 | +26.9% | 조정주 | 물타기 후보 | ⭐⭐⭐ | ASIC, 평단 근접 물타기후보 |\n\n> 컨센 ±30% 괴리(상방): NVDA·META·MSFT·AVGO·ORCL = 🟢. MU는 목표 급상향 진행형(구컨센 $612 vs 신컨센 $1,200~1,500 이원화) → \"주가>목표\"는 리프라이싱(6/24 실적이 분기점, 절반 차익).\n\n### 워치리스트 (활성)\n| 종목 | 현재가 | 당일 | 목표(컨센) | 비고 |\n|---|---|---|---|---|\n| **SK하이닉스** | 2,764,000 | **+2.94%** | Strong Buy | 🔥 **ADR SEC 승인 6/22주·8월 거래·조달 $14B·27년 PER ~6.9배 vs 필반 27배.** 사상최고. 목표 +50%초과=추격 부적합, ADR 상장 후 美 소수점 적립 검토 |\n| **삼성전기** | 2,270,000 | **+3.18%** | **KB 300만(220만→상향)** | 🔥 MLCC·기판 초호황+중일 희토류 반사이익. PER 과열·추격금지, 워치 활성 |\n| **GE Vernova** | $1,109.73 | +5.80% | $1,211.72(+9.2%) | Bernstein 매수개시 $1,206·수주+71%. 워치 유일 매수검토(소액·갭 소화 후) |\n| 두산에너빌리티 | 97,900 | −1.71% | 13.5~16.5만 | 10만 하회, 추격금지. SMR 진짜수혜, 93~95k 눌림 소액만 |\n| LG이노텍 | 1,145,000 | **−10.76%** | KB 160만 유지 | FC-BGA, 그룹 동반 급락이나 sell-side 성장성 긍정. 안정화·실적 후 소액 |\n| 원익IPS/테스 | 156,000/166,200 | −4.41%/−5.62% | — | 소부장 차익실현(.KQ 코스닥) |\n| SK이노 | 102,400 | −1.06% | — | SMR(테라파워 2대주주) |\n| 한화에어로/조선 | 1,122,000/한화오션 128,400 | −5.63%/+2.64% | — | 방산 펀더 견조하나 과열 / 조선 슈퍼사이클(채널), 공시 확인 전 추격위험 |\n| STM/TMUS/SPCX | $78.39/$181.67/$185.00 | +6.86%/+0.20%/−3.56% | STM $64(−18%)/TMUS $260.81/SPCX $188 | STM 컨센 하향=보류 / SPCX 6/26 MSCI·7월초 나스닥100 vs 8월 락업 |\n\n### 제안 액션\n- **관망 디폴트** — 매수존 진입 NAVER 외 전 종목 위 이탈 + **외인 6/19 순매도 전환** + 6/22 갭 리스크. **현금 624,771원 전액 보존.**\n- **NAVER 1차 트랜치**: 매수존(225~235k) 진입 발동이나 **정리후보 + 외인 순매도 전환** → **6/22 외인 재유입 확인까지 보류** 권고(집행 시 소액 10만 하단만). 코어 우선순위 META.\n- **🔴 3차 트랜치(META·AVGO) = 매파로 보류 유지.** 오늘 저녁 폰창에 **보유분 투매 금지**(LG전자·LG이노텍 급락=그룹 차익실현, 펀더 무손상).\n- **6/24 MU 실적(야간) 절반 차익 = 6/23 저녁 사전 베이킹 필수**(폰 미가용). 경제사냥꾼 7편 공통 \"AI수요 분수령\" 프레임과 정합. 소수점 시장가 조건부 예약. *단 MU 보유 0.04주·평가 ~$45 = 금액 미미 → 본질은 집중도 완화·디시플린 훈련(전량 홀딩도 합리, 6/23 택1).*\n- **추격 금지**: SK하이닉스 ADR·삼성전기·조선·캐시우드 TSLA — 경제사냥꾼이 부추기는 FOMO 테마 전부 룰3 대상(방향성만 채택). GEV만 워치 중 소액 검토(갭 소화 후).\n- **6/22 외인 종가 = 강세 논지 갱신 분수령**(순매도 일회성 FTSE 기계적이었는지 vs 추세 전환인지 확정).\n\n### 현금 배분 플랜 (624,771원, 3분할 미집행)\n- **1차 ~12.5만**: NAVER 225~235k **진입 발동** but 정리후보+외인 순매도 → **6/22 외인 재유입 후 소액**, 또는 삼성 295~305k(현 354k, 멀음) 눌림 대기.\n- **2차 ~20만**: 코스피 8,000 하회 + 이벤트 악재 동반 시(현 9,052, 미도달).\n- **3차 ~22.5만**: 🔴 **FOMC 매파로 보류 유지.** 비둘기 전환·META 7/29 실적·외인 복귀 추세 중 하나까지 동결.\n- ⚠️ GEV 소액 소수점(갭 소화 후)은 트랜치 본예산과 분리, 편입 시 승인 필요.\n\n### 지켜볼 것 (2주 캘린더)\n| 날짜(KST) | 이벤트 | 폰 |\n|---|---|---|\n| 6/22(월) | 美 재개(갭 리스크) / **SK하이닉스 ADR SEC 클리어런스 주** / **외인 재유입 재검증(강세 분수령)** | ❌야간 |\n| **6/23(화) 저녁** | **MU 절반 차익 사전 베이킹**(6/24 야간 실적용) | ✅ |\n| **6/23(화)~24** | **MSCI 연례 시장분류 발표**(한국 선진국 관찰대상국, 날짜 6/22 재확인) | ❌야간 |\n| **6/24(수)** | **MU 실적**(절반 차익, \"AI수요 분수령\") | ❌야간 |\n| 6/26(금) | SPCX MSCI·Russell 편입 메커닉 | — |\n| 7/6(월) | 외환시장 원/달러 24시간 확대(MSCI 핵심 숙제) | — |\n| 7/14~15 | 美 6월 CPI(7/14)·PPI(7/15) 21:30 KST | ❌야간(베이킹) |\n| **7/16(목)** | **한은 금통위(2.50→2.75% 인상 전망)** | ✅오전 |\n| 7/22~30 | 美 실적(TSLA·GEV·TMUS 7/22, GOOGL 7/23, LG전자 7/24, 삼성·META·MSFT 7/29, AAPL 7/30) | — |\n\n---\n\n## 8. 오늘의 이슈 선택지\n1. **6/24 MU 실적 베이킹 매뉴얼 확정** — 절반차익(+51%) vs 전량홀딩, 비트/인라인/미스별 주가(컨센 이원화 $612 vs $1,200~1,500), 6/23 저녁 소수점 시장가 예약 구체화. 경제사냥꾼 7편 \"AI수요 분수령\" 프레임 반영.\n2. **외인 순매도 전환 = 추세인가 FTSE 기계적인가?** — 6/19 −3,800억의 성격, 외인 한달 50~57조 순매도를 개인이 받는 구도의 의미, 6/22 재유입 확인법, 강세 논지 하향 임계치.\n3. **SK하이닉스 ADR(6/22주) = 보유 삼성·NVDA·MU에 미치는 영향** — 코스피-나스닥 동조성 심화, \"삼성 프리미엄 잠식\" 경고 신뢰도, 8월 상장 시 美 소수점 적립 전략.\n4. **ARM 레버리지 플라이휠 = AI 버블 신호인가?** — SoftBank-ARM-OpenAI-Stargate 순환구조, ARM PER 500배 vs MU 10배 함의, 보유 NVDA·MSFT·META 집중도 리스크 점검.\n\n---\n\n## STATE SNAPSHOT\n```\n[STATE SNAPSHOT v20 2026-06-20]\n현금: 624,771원 (트랜치 1차/2차/3차 전부 미집행 — 3차 FOMC 매파 보류, 1차 NAVER 매수존 발동했으나 정리후보+외인 순매도→6/22 재유입 확인까지 보류)\n보유변동: 없음 (16종목 유지)\n시세기준: KR=6/19 마감(코스피 9,052.42 −0.13%, 장중 9,385 신고가→급반락 / 코스닥 966.59 −3.43% 정정) / US=6/18 종가(6/19 준틴스+6/20 주말 휴장) / USD/KRW ~1,530\n총자산: 8,515,217원 · 주식손익 +305,371(환차익 미반영) / 환차익 반영 ≈ +589,520원 (정확값은 토스 정본)\n오늘 할 일: 추격금지·현금 전액 보존 / 보유분 투매 금지 / NAVER 매수존→6/22 외인 재유입 확인까지 보류 / MU 6/24 절반차익 6/23 저녁 베이킹 / 경제사냥꾼 FOMO 테마(하이닉스 ADR·삼성전기·조선·TSLA) 추격금지\n수급경보: 🔴 6/19 외인 코스피 순매도 전환 확정(≈−3,800억, FTSE 리밸런싱 기계적·코스닥은 외인 +4,873억). 외인 순매수 행진 종료 = \"엔진\" 1차 균열. 6/22 재유입이 강세 논지 진짜 분수령\nFOMC 후속: 🟢 매파 셀오프 \"1일천하\"(6/18 SOX +6.42% 되돌림) but 점도표 인상·DXY 100.8·2년물 그대로 = 기술적 되돌림\n워치리스트(활성): SK하이닉스(ADR 6/22주 SEC)·삼성전기(KB 300만)·GE Vernova(매수검토)·두산에너빌리티·LG이노텍·원익IPS·테스·SK이노·한화에어로·한화오션·STM·TMUS·SPCX\n대기 트리거:\n  ① 3차 트랜치 = 🔴매파로 보류 유지\n  ② 6/24 MU 실적 → 절반 차익(6/23 저녁 베이킹, 경제사냥꾼 \"AI수요 분수령\")\n  ③ 6/22 美 재개 갭 + SK하이닉스 ADR SEC 클리어런스 주 + 외인 재유입 재검증\n  ④ NAVER 1차 매수존(225~235k) 발동 — 정리후보·외인 순매도라 6/22 확인 후 소액만\n  ⑤ MSCI 6/23(전후) 시장분류 발표(한국 선진국 관찰대상국) — 날짜 6/22 재확인 / 외환개혁 7/6\n  ⑥ 한은 7/16 금통위 2.50→2.75% 인상 전망\n영구교정(신규):\n  - 코스닥 6/19 = −3.43%(34.34p↓) 확정. v19의 −6.33%는 Yahoo prev_close 오류 → 정정\n  - 6/19 외인 코스피 순매도 전환 ≈−3,800억(서경 −3,647·fn −3,884·ddaily −3,523 수렴, 잠정 −9,831억 폐기), 기관 −1.23조·개인 +1.65조 / 코스닥 외인 +4,873억(FTSE 리밸런싱)\n  - 코스피 6/19 장중 사상최고 9,385.59→−553p 급반락 9,052 방어, 시총 첫 8,000조 돌파\n  - MSCI 발표일 정정 검토: 6/24 → 6/23(전후), 접근성 점수 6/18 선공개(마이너스 18→17개). 관찰대상 등재 기대(승격 아님, 정식 편입 2027~2028). 6/22 최종 재확인\n  - 경제사냥꾼 6/19 신규 7편 자막 전량 확보(v19 SSL 차단 우회 성공): ARM 레버리지 플라이휠(SoftBank 대출한도 ~$185억·OpenAI $300억·스타게이트 $5,000억)·손정의 NVDA 전량매도 / SK하이닉스 ADR(SEC 6/22주·$14B·27년 PER 6.9배) / Intel+Apple 테라팹(딜 검증·장비주 납품 미확인) / 삼성그룹 시총 57%·일반DRAM +90%·외인 50~57조 순매도 / 캐시우드 TSLA $2,600(2029)·우드 차익매도 중 / G7 앤스로픽 AI수출통제(Al Jazeera 검증)\n  - 삼성전기 KB 목표 220만→300만원 상향(MLCC·중일 희토류 반사이익)\n  - 채널 공통 메시지 \"6/24 MU=AI수요 진위 분수령\"=정훈 절반차익 트리거와 정합. 트랙레코드 개선세 지속(과장 자진경계)\n리서치: 경제사냥꾼 신규 7편 전량 자막 확보·심층 분석 완료(hunter_log 갱신). 12월 로컬 이전 시 안정화 기대\n다음 버전: v21\n```\n\n*투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "holdings_final_2026-06-20",
      "file": "docs/reports/holdings_final_2026-06-20.md",
      "title": "🏁 정훈 최종보고 · 2026-06-20 (주말) · v20",
      "date": "2026-06-20",
      "version": null,
      "kind": "보유확정",
      "preview": "💡 핵심 액션 4개 (표 위 콕)",
      "content": "# 🏁 정훈 최종보고 · 2026-06-20 (주말) · v20\n\n> 데이터: KR=**6/19 마감** / US=**6/18 종가**(6/19 준틴스·6/20 주말 휴장) / USD/KRW **~1,530**.\n> ⭐ 정훈 강조 **\"경제사냥꾼 꼭 검토\"** — 신규 7편 자막 전량 확보(§아래 박스). 핵심 한 줄: **\"6/24 MU = AI수요 진위 분수령\"**(절반차익 트리거와 정합).\n> 투자 자문 아님 · 최종 결정은 정훈.\n\n---\n\n## ① 보유 16종목\n\n| 종목 | 현재가 | 당일 | 원가대비 | 목표가 | 매수존 | 트림/매도 | ⭐ | 코멘트 |\n|---|---|---|---|---|---|---|---|---|\n| 삼성전자 | 354,000원 | −2.34% | **+34.6%** | 480,000~530,000원 | 295,000~305,000원(이탈) | 보류 | ⭐⭐⭐⭐ | 사이클 중반·일반DRAM 판가 +90% 레버리지 |\n| LG전자 | 211,500원 | −7.44% | **+36.3%** | 컨센 초과 | 홀딩 | 손절선 없음 | ⭐⭐⭐⭐ | 그룹 동반 차익실현·펀더 무손상=홀딩 |\n| 두산로보틱스 | 101,800원 | −0.88% | +1.8% | 분산 큼 | 관망 | 모멘텀 | ⭐⭐ | 전일 −15% 모멘텀, 추격금지 |\n| 현대차 | 613,000원 | +2.00% | −2.7% | 600,000원(공격 800,000원) | 관망 | — | ⭐⭐⭐ | BD 풋옵션 7/20·삼성 지분설, 반등 |\n| NAVER | 229,500원 | −2.34% | −8.4% | ~300,000원(메리츠 410,000원) | **225,000~235,000원(진입🔴)** | 정리후보 | ⭐⭐ | 매수존 but 정리후보=6/22 대기·소액 |\n| NVDA | $210.69 | +2.95% | +5.6% | $298.93 | 눌림 | 비중관리 | ⭐⭐⭐⭐⭐ | Rubin HBM4 3사인증·테라팹 호재 |\n| META | $577.22 | +1.70% | −9.0% | $827.32 | 실적확인 | — | ⭐⭐⭐⭐ | 고유악재 회복(노이즈), 7/29 전 보류 |\n| VOO | $688.11 | +0.98% | +6.6% | — | 적립 | — | ⭐⭐⭐⭐ | 분산형 코어 |\n| MSFT | $379.40 | +0.13% | −7.5% | $561.39 | 눌림 | — | ⭐⭐⭐⭐ | 상방 최대(+48%), 6/18 소외 |\n| AAPL | $298.01 | +0.70% | **+15.9%** | $312.72 | 목표근접 | **트림 1순위** | ⭐⭐⭐ | 금리방어·인텔딜 협력 당사자 |\n| GOOGL | $368.03 | +1.17% | −5.1% | $432.83 | 눌림 | — | ⭐⭐⭐⭐ | Cloud·Gemini, 반독점 노이즈 |\n| TSLA | $400.49 | +1.04% | −5.2% | $420.55 (ARK 2029 $2,600) | 관망 | — | ⭐⭐⭐ | 캐시우드 강세 but 우드 차익매도 중 |\n| ORCL | $184.29 | +0.41% | **−20.6%** | $252.64 | 눌림 | 패닉셀 금지 | ⭐⭐⭐ | RPO $638B 백로그, OpenAI 54% |\n| ANET | $169.67 | +2.87% | +4.7% | $189.13 | 홀딩 | — | ⭐⭐⭐⭐ | AI 네트워크, 목표 상향 |\n| MU | $1,133.99 | +8.70% | **+51.4%** | $1,200~1,500(상향중) | **6/24 실적** | **절반 차익** | ⭐⭐⭐⭐ | 채널 \"AI수요 분수령\", 6/24 절반차익 |\n| AVGO | $411.35 | +4.70% | −2.3% | $522.06 | 조정주 | 물타기 후보 | ⭐⭐⭐ | ASIC, 평단 근접 물타기후보 |\n\n```\n💡 핵심 액션 4개 (표 위 콕)\n1. 🔴 MU(+51.4%) — 6/24 야간 실적 = 경제사냥꾼 7편 공통 \"AI수요 진위 분수령\".\n   → 6/23(화) 저녁 폰창에서 절반(0.02주) 시장가 매도 베이킹 OR 전량 홀딩 택1.\n   (보유 0.04주·평가 ~45,000원이라 금액은 미미 → 본질은 집중도 완화·디시플린)\n2. 🛑 LG전자(−7.44%)·LG이노텍(−10.76%) — 그룹 동반 차익실현, 펀더 무손상.\n   → 손절선 없음·투매 절대 금지. 추가매수도 보류(떨어지는 칼날, 외인 확인 후).\n3. 🟡 NAVER 229,500원 = 매수존 진입(유일 발동) but 정리후보 + 외인 순매도 전환.\n   → 6/22 외인 재유입 확인까지 보류. 집행 시 소액 100,000원(하단)만.\n4. ✋ AAPL(+15.9%) 트림 1순위 후보 — 목표 근접·금리방어. 단 인텔딜 협력 당사자라 관망.\n```\n\n---\n\n## ② 워치리스트 (활성)\n\n| 종목 | 현재가 | 당일 | 목표 | 콕 |\n|---|---|---|---|---|\n| **SK하이닉스** | 2,764,000원 | +2.94% | Strong Buy | 🔥 **ADR SEC 승인 6/22주·8월 거래·조달 $14B·HBM 57%·27년 PER 6.9배** |\n| **삼성전기** | 2,270,000원 | +3.18% | **KB 3,000,000원**(220만→상향) | 🔥 MLCC·기판 초호황 + 중일 희토류 반사이익 |\n| **GE Vernova** | $1,109.73 | +5.80% | $1,211.72 | 워치 유일 매수검토(소액·갭 소화 후), Bernstein $1,206·수주+71% |\n| 두산에너빌리티 | 97,900원 | −1.71% | 135,000~165,000원 | 10만 하회, 추격금지. SMR 진짜수혜 |\n| LG이노텍 | 1,145,000원 | −10.76% | KB 1,600,000원 | FC-BGA, 그룹 동반 급락이나 성장성 긍정 |\n| 한화오션 | 128,400원 | +2.64% | — | 조선 슈퍼사이클(채널), 공시 확인 전 추격위험 |\n| STM/TMUS/SPCX | $78.39/$181.67/$185.00 | +6.86%/+0.20%/−3.56% | — | STM 보류 / SPCX 6/26 MSCI vs 8월 락업 |\n\n```\n🎬 경제사냥꾼 6/19 신규 7편 — 자막 전량 확보(v19 차단 우회 성공)\n① ARM \"젠슨황도 못 산 기업\": SoftBank 레버리지 플라이휠(ARM담보 ~$185억→OpenAI $300억\n   →스타게이트 $5,000억), 손정의 NVDA 전량매도. ARM PER 500배 vs MU 10배·하이닉스 6~7배\n   = 보유 MU·워치 하이닉스 \"가장 싼 AI 길목주\" 부각 [검증]\n② Intel+Apple 테라팹 딜 [골격 검증] — 삼성 파운드리 양날, NVDA 호재\n③ 코스피 급락 진짜 이유: 호르무즈 회담 연기+반도체 차익+세마녀, \"레버리지 줄여라\" [검증]\n④ ★삼성그룹 \"국민기업\": 시총 57%·외인 한달 50~57조 순매도→개인 40조 매수·일반DRAM +90%\n   ·하나證 삼성 2Q 92조(가장 공격적) [검증]\n⑤ ★SK하이닉스 ADR: 밤사이 나스닥 가격선결정→코스피 변동성 수입 [검증]\n⑥ 캐시우드 TSLA $2,600(2029) — 단 우드 본인은 TSLA 차익매도 중(영상 미언급) [검증·시점]\n⑦ G7 美 앤스로픽 AI수출통제→HBM 한국 몸값↑ [검증, Al Jazeera]\n→ 채널 공통: \"6/24 MU = AI수요 말잔치냐 실제 현금이냐 분수령\". 6/19 급락 반영해 \"고점추격·\n   레버리지 경계\"로 톤다운 = 정훈 추격금지·안전핀 룰 정합. 트랙레코드 개선세 지속.\n```\n\n---\n\n## ③ 현금 배분 (624,771원, 3분할 미집행)\n\n**🅰️ 관망 (룰 정합·추천)** — 외인 6/19 순매도 전환 + 6/22 갭 리스크 → **전액 보존.**\n- NAVER 매수존 발동했으나 정리후보 → 6/22 외인 재유입 확인까지 보류.\n- 3차 트랜치(META·AVGO) = FOMC 매파로 동결 유지.\n- MU 6/24 절반차익(6/23 베이킹)만 능동 액션.\n\n**🅱️ 공격** — 6/22 외인 재유입 확인 + 코스피 9천 사수 전제 시에만.\n- NAVER 1차 **소액 100,000원**(225,000~235,000원, 정리후보 인지 후 조건부).\n- 잔여 524,771원은 삼성 295,000~305,000원 눌림 or 코스피 8,000 하회 대기.\n- ⚠️ GEV 소액 소수점은 갭 소화 후·본예산 분리(편입 시 승인).\n\n---\n\n## ④ 2주 일정 (폰 가용 17:30~20:50 KST)\n\n| 날짜 | 이벤트 | 폰 |\n|---|---|---|\n| 6/22(월) | 美 재개 갭 / SK하이닉스 ADR SEC 클리어런스 주 / **외인 재유입 재검증(강세 분수령)** | ❌야간 |\n| **6/23(화) 저녁** | **MU 절반차익 사전 베이킹** | ✅ |\n| 6/23~24 | **MSCI 시장분류 발표**(한국 관찰대상국, 날짜 6/22 재확인) | ❌야간 |\n| **6/24(수)** | **MU 실적**(\"AI수요 분수령\") | ❌야간 |\n| 7/6(월) | 외환시장 원/달러 24시간 확대 | — |\n| 7/14~15 | 美 6월 CPI·PPI 21:30 KST(베이킹) | ❌야간 |\n| **7/16(목)** | 한은 금통위(2.50→2.75% 전망) | ✅오전 |\n\n---\n\n## ⑤ 월말 목표 + 전략 3 + 오늘 할 것\n\n**월말(6/30) 목표**: 현금 룰 디시플린 유지(추격 0건) + MU 6/24 절반차익으로 집중도 1단계 완화 + 외인 추세 재확인 후에만 1차 트랜치.\n\n**전략 3**:\n1. **코어는 손대지 않는다** — AI 슈퍼사이클 베팅(삼성·NVDA·MU·META·MSFT) 홀딩. \"산 이유가 살아있나\"가 매도 기준이지 가격이 아님. LG전자 그룹 차익실현은 펀더 아님 → 투매 금지.\n2. **외인이 엔진 — 6/22를 본다** — 6/19 순매도는 FTSE 기계적일 수 있으나 \"엔진 균열\" 신호. 재유입 확인 전 신규 진입 보류.\n3. **경제사냥꾼 FOMO는 방향만, 가격은 추격 안 함** — 하이닉스 ADR·삼성전기·조선·캐시우드 TSLA 전부 룰3 대상. \"좋은 기업 ≠ 좋은 가격.\"\n\n**오늘(주말) 할 것**:\n- 보유 점검만, 매매 없음(시장 휴장). 6/23 저녁 MU 베이킹·6/22 외인 확인 알람.\n- LG전자/LG이노텍 급락에 흔들리지 않기(펀더 무손상 = 홀딩).\n\n---\n\n## 🎯 결론\n**경제사냥꾼 7편이 한목소리로 \"6/24 MU가 AI수요 진짜 분수령\"이라 짚었고, 이건 정훈의 절반차익 트리거와 정확히 맞는다. 동시에 v19 미확정이던 6/19 외인 수급이 순매도 전환(−3,800억)으로 찍혀 강세 엔진에 1차 균열 — 기계적(FTSE)일 수 있으나 6/22 재유입 확인 전엔 신중. 💪 코어는 그대로 들고 가되, 현금 62만원은 전액 지키고, NAVER 매수존조차 6/22 외인 확인 후. 다음 주는 MU 6/24·MSCI 6/23·하이닉스 ADR 6/22주·美 재개장 갭이 한 주에 몰린 이벤트 클러스터 — 추격 대신 베이킹과 확인으로 간다.**\n\n*투자 자문 아님 · 모든 레벨은 분석 참고 · 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v19_addendum_2026-06-19",
      "file": "docs/reports/report_v19_addendum_2026-06-19.md",
      "title": "정훈 PORTFOLIO DESK · v19 부록 · 2026-06-19 — 이슈 4개 심층 분석",
      "date": "2026-06-19",
      "version": 19,
      "kind": "보고서",
      "preview": "🎯 결론: 쏠림 자체는 옐로카드(취약성↑)이나 매도 신호는 아직 아님. \"외인 엔진 + 반도체 실적\"이 받치는 한 디커플링은 강세장의 모습일 수도. 6/22 외인 종가 + 6/24 MU/MSCI가 분수령. 신규 진입은 그때까지 보류, 보유는 홀딩.",
      "content": "# 정훈 PORTFOLIO DESK · v19 부록 · 2026-06-19 — 이슈 4개 심층 분석\n\n> 본문 `report_v19_2026-06-19.md`의 §8 이슈 선택지 4개 전부 심층. 투자 자문 아님, 최종 결정은 정훈.\n\n---\n\n## 이슈 1 — MU 6/24 실적 베이킹 매뉴얼 (절반차익 vs 전량홀딩)\n\n**일정·제약**: MU 회계 Q3 실적 = **6/24(수) 美 장 마감 후**(KST 6/25 새벽) → **정훈 폰 미가용(17:30~20:50 밖)** → **6/23(화) 저녁 폰창에서 사전 베이킹 필수.**\n\n**숫자 정리**:\n- 회사 가이드: 매출 **$33.5B(±$750M)** · EPS **$19.15** · GM ~81%\n- Street 컨센: 매출 **~$34.8B** · EPS **~$19.82** (애널 레인지 $33.7B~$40.9B = 매우 넓음, 슈퍼사이클 불확실성)\n- → **회사 보수 가이드 < Street 컨센 = 인라인~비트 베이스라인** (beat 기대가 이미 주가에 내재)\n- 현 주가 **$1,133.99**, 원가 $749 → **+51.4%**. **목표가 이원화: 구컨센 ~$612 vs 신컨센 UBS $1,625·TD Cowen $1,500·Citi/RBC $1,200·MS $1,050** (골드만 ~$400은 구목표 추정·미확인)\n\n**⚠️ 포지션 실익 점검(중요)**: MU 보유 = **0.04주, 평가액 ≈ $45**. 절반 차익 = 0.02주 ≈ **$22(약 3.4만원)**. **금액 임팩트는 미미** → 이번 절반차익의 본질은 **손익이 아니라 ①집중도(HBM 6중 쏠림) 완화 규율 ②\"고평가+이벤트 전 절반 빼기\" 디시플린 훈련**이다. 소액이라 전량 홀딩(슈퍼사이클 베팅)도 합리적 선택.\n\n**시나리오 (메모리 실적 통상 ±8~12% 갭, MU 옵션 IV 구체치는 미확인)**:\n| 결과 | 주가 반응 | 홀딩분 영향 |\n|---|---|---|\n| **비트 + 가이드 상향**(HBM ASP 추가↑) | +10%↑ | 탈순환주 내러티브 강화, 홀딩분 추가수혜 |\n| **인라인**(컨센 부합) | −5~10%(sell-the-news) | 절반 차익이 보호 |\n| **미스/가이드 실망** | −10%↑ | 선반영분 큰 되돌림, 절반 차익이 헤지 |\n\n**베이킹 실행안 (6/23 저녁)**: 토스 미국 소수점 = **시장가만**(지정가 불가) → 실적 갭 변동에 노출. 0.04주는 분수주 시장가 매도 가능.\n- **PM 권고(규율 우위)**: 6/23 저녁 **절반(0.02주) 시장가 매도 예약 베이킹** + 절반 홀딩. 인라인 sell-the-news 헤지 + 비트 시 잔여 수혜의 비대칭.\n- **대안(소액이라 단순화)**: 전량 홀딩 후 6/25~26 폰창에서 수동 판단. 금액이 작아 베이킹 안 해도 리스크 제한적.\n- 🎯 **결론**: 절반차익 베이킹이 규율상 약간 우위(집중도·디시플린). 단 절대금액이 작아 정훈이 \"슈퍼사이클 전량 홀딩\"을 택해도 무방. **6/23 저녁 둘 중 택1 결정.**\n\n---\n\n## 이슈 2 — 코스피 디커플링 = 신중 신호인가?\n\n**현상**: 코스피 9,052(−0.13%) 사수 but **시총 4사(삼성·SK하이닉스·SK스퀘어·삼성전기) 비중 59.6%(5월말比 +4.27%p)**, **상승 109 vs 하락 791종목**, **코스닥 −6.33%**. 지수는 신고가권인데 종목 80%는 하락.\n\n**양면 해석**:\n- **신중(쏠림=후반부 신호)**: 폭 좁은 상승은 역사적으로 랠리 후반 특징. 반도체 4종목에 의존 → 그 4종목 조정 시 지수 급락 취약. 6/19 코스닥·중소형 폭락은 지수 밑 매물 출회의 증거.\n- **강세(주도주 장세)**: AI 슈퍼사이클 초입의 대형 반도체 집중은 **펀더 기반 쏠림**(MU 6/24·삼성 7/29 실적이 검증대). **MSCI 선진국 편입 메커니즘 = 구조적으로 대형 반도체 수혜·중소형 탈락**(양극화는 일시현상 아닌 추세). 외인 엔진(6/18 +1.28조)이 받쳐주면 지속 가능.\n\n**외인 6/22 확인법(핵심 스위치)**: KRX 투자자별 매매동향(data.krx.co.kr) → ①외인 순매수 지속(코스피) = 강세 유지 ②순매도 재전환 = \"외인=메인엔진\" 신호 약화 = 신중.\n\n**강세 논지 하향 임계치**: **외인 2~3거래일 연속 순매도 + 코스피 8,000 하회 동반** 시 강세 비중 하향. 현재는 둘 다 미충족(9,052·6/18 순매수).\n\n🎯 **결론**: **쏠림 자체는 옐로카드(취약성↑)이나 매도 신호는 아직 아님.** \"외인 엔진 + 반도체 실적\"이 받치는 한 디커플링은 강세장의 모습일 수도. **6/22 외인 종가 + 6/24 MU/MSCI가 분수령.** 신규 진입은 그때까지 보류, 보유는 홀딩.\n\n---\n\n## 이슈 3 — LG전자/LG이노텍 급락 = 매수기회 vs 회피?\n\n**원인 진단(확정)**: ①**LG그룹 전반 동반 차익실현**(LG −7.21%·LG CNS −6.85%·LG헬로비전 −13.56%) ②로봇/피지컬AI 테마 차익실현 폭탄(두산로보 전일 −15%·현대차 전일 −9%) ③LG전자 5/20~6/2 **2주 +117% 폭등의 되돌림.** → **종목 고유 악재 아님, 펀더 무손상.** NVIDIA 냉각(CDU 액냉)·DSX 협력은 현재진행형, **인증 취소·수주 철회 보도 없음**(외신·국내 미확인).\n\n**LG전자(보유)**:\n- 룰: 손절선 영구 폐기, **펀더 훼손 시에만 매도** → **홀딩 유지, 투매 금지**(원가 대비 여전히 +36.3%).\n- 모니터 포인트: **NVIDIA CDU 인증 결과·DSX 데이터센터 액냉 수주.** 인증 통과 시 재평가 촉매.\n- 추가매수?: 추격금지 + 현금 트랜치 룰상 **지금 추격 비권장.** 그룹 차익실현 안정화 + 외인 확인 후, 더 깊은 눌림(2주 +117% 되돌림 더 진행 시)에서 코어 비중 확대 고려. **떨어지는 칼날 잡지 말 것.**\n\n**LG이노텍(워치)**:\n- KB 목표 **1,600,000원 유지**(현 1,145,000 대비 +40%) — FC-BGA(AI 기판) 공급병목 구조적, 성장성 긍정 유지. 단 PER~60배 부담.\n- 정훈 룰: **추격 아닌 관찰**(증설 실행력·수율이 관건). −10.76% 급락은 그룹 동반이지 펀더 아님 → 워치 잔류, 안정화·실적 확인 후 소액 검토.\n\n🎯 **결론**: **보유 LG전자 = 홀딩(투매 절대 금지), 신규 추가는 안정화 후.** LG이노텍 = 워치 관찰 유지. **둘 다 \"급락 = 펀더 훼손\"이 아니므로 패닉 금지**, 단 추격매수도 금지(눌림 더 확인).\n\n---\n\n## 이슈 4 — NAVER 매수존 1차 트랜치 집행 여부\n\n**상황**: NAVER 229,500원 = **1차 매수존(225,000~235,000원) 진입**(triggers.py 유일 발동). 1차 트랜치 ~125,000원.\n\n**찬성(집행) 논거**:\n- 매수존 진입 = 룰상 1차 트랜치 발동 조건 충족(추격 아닌 눌림).\n- **두나무 합병**(NAVER파이낸셜 100% 자회사화, 교환비 1:2.54, 9월)·디지털자산법 2단계 수혜 = 촉매. **메리츠 목표 410,000원(+44.9% 상향)**·하나 320,000원.\n- 원가 대비 −8.4% = 평단 낮추기 기회.\n\n**반대(보류) 논거**:\n- NAVER = master상 **\"플랫폼주 신뢰 낮음·정리 후보 상시 검토\"** 종목. **6/15 랠리에서 +0.4% 소외**(주도축 아님, 커머스주).\n- 디커플링 장세에서 **정리후보에 첫 트랜치 = 논리 충돌**(리스크 데스크 지적). 코어(META·삼성) 우선순위.\n- 외인 6/19 미확인 + 6/22 갭 리스크 = 진입 타이밍 불확실.\n\n🎯 **결론(리스크 데스크 정합)**: **6/22 외인 추세 확인까지 1일 보류 권고.**\n- 외인 순매수 지속 확인 시 → 1차 **소액(10만 하단)만**, 두나무 합병(9월) 촉매까지 보유 전제.\n- 외인 순매도 전환 시 → 보류(현금 보존), 삼성 295~305k 눌림 대기로 코어 전환.\n- 추격 아닌 눌림이라 \"금지\"는 아니나, **\"신뢰 낮은 종목에 첫 트랜치\"임을 명시 인지** 후 소액·조건부로만.\n\n---\n\n*투자 자문 아님. 모든 레벨은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v19_2026-06-19",
      "file": "docs/reports/report_v19_2026-06-19.md",
      "title": "정훈 PORTFOLIO DESK · v19 · 2026-06-19",
      "date": "2026-06-19",
      "version": 19,
      "kind": "보고서",
      "preview": "1. MU 6/24 실적 베이킹 매뉴얼 — 절반 차익(+51%) vs 전량 홀딩, 비트/인라인/미스별 주가 반응(컨센 이원화 $612 vs $1,200~1,625), 6/23 저녁 소수점 시장가 조건부 예약 구체화. MSCI 6/24 동시 D-day ",
      "content": "# 정훈 PORTFOLIO DESK · v19 · 2026-06-19\n\n> 투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.\n> 시세 기준: **KR=6/19 마감** / **US=6/18 종가**(6/19 美 준틴스 전체 휴장 → 미국 시세 갱신 없음) / USD/KRW **1,526.13**. 8개 데스크(지역2·섹터3·매크로·리서치·리스크 + 정량스크립트4) 종합.\n> ⚠️ 오늘의 그림 = **\"FOMC 매파 1일천하\"**(6/18 美 반도체 폭등으로 셀오프 완전 되돌림) + **코스피 디커플링 극단화**(반도체만 9천 사수, 코스닥 −6.33% 폭락).\n\n---\n\n## 변경점 (직전 v18 / 6/18 대비)\n\n- **🟢 FOMC 매파 셀오프 = 1일천하** — 6/17 매파 충격(META −5.44%·나스닥 −1.34%) → **6/18 미국장 완전 되돌림: SOX +6.42%·MU +8.70%·AVGO +4.70%·NVDA +2.95%·META +1.70% 회복.** Intel+Apple 협업 딜이 칩 랠리 촉매. **점도표 인상 전환·2년물·DXY 100.72는 그대로 = 매크로 매파를 AI 칩 모멘텀이 뚫은 구도**(증시-금리 디커플링). 단 **6/19 美 준틴스 휴장 → 6/22(월) 재검증 전 데이터**.\n- **🔴 MU +8.70% → 원가대비 +51.40%** (6/24 실적 D-5). 월가 목표가 일제 상향($1,200~$1,625) 진행형 = HBM 2026 sold out 리프라이싱. **절반 차익 논지 더 강화**(집중도 완화 + 인라인 리스크 헤지).\n- **🔴 코스피 디커플링 극단화** — 코스피 **9,052.42(−0.13%, 4일 급등 후 첫 숨고르기)** 사수하나 **시총 4사 59.6%·상승 109 vs 하락 791종목.** **코스닥 966.59(−6.33% 폭락, 1,000선 재이탈).** \"기승전 반도체\" 쏠림 심화.\n- **🔴 LG전자 −7.44%(211,500) + LG이노텍 −10.76% 급락** — **LG그룹 전반 동반 차익실현**(LG −7.21%·LG CNS −6.85%·LG헬로비전 −13.56%) + 로봇주 차익실현 폭탄(두산로보 전일 −15%·현대차 전일 −9%). **NVIDIA 냉각(CDU) 인증 취소 등 펀더멘털 훼손 뉴스 없음** → 룰대로 LG전자 홀딩(원가 대비 +36.28%). 원가대비는 +46.9%→+36.28%로 축소.\n- **🟢 NAVER 229,500 = 1차 매수존(225~235k) 진입** — triggers.py 유일 발동. 단 정리후보 + 디커플링 장세 → 신중(아래 §5·§7).\n- **🆕 MSCI 6/24 05:30 연례 시장분류 발표**(한국 선진국 관찰대상국 등재 여부) — **MU 실적과 동일 D-day군**. 6/19 새벽 접근성 점수 선공개. 외환개혁(7/6 원/달러 24시간 확대) = 핵심 숙제.\n- **유가·이란**: 브렌트 **$78 하회**·WTI **~$65**(3월來 최저). 이란 휴전 MOU는 **전자서명 완료 → 6/19 스위스 별도 서명식 없음**(외신 정정).\n\n---\n\n## 1. 시장 — 국장 / 미장\n\n### 국장 (6/19 마감)\n- **코스피 9,052.42(−0.13%)** — 4일 급등(6/18 첫 9,000 마감 9,063.84) 후 **첫 숨고르기**. SK하이닉스(+2.94%, HBM4E 12단 샘플)·삼성전기(+3.18%) 반도체가 떠받쳐 보합 사수. **코스닥 966.59(−6.33% 폭락) = 디커플링 극단화**(상승 109 vs 하락 791, 시총 4사 비중 59.6% = 5월말比 +4.27%p).\n- **🔑 외인 수급**: 6/18 종가 외인 코스피 **+1.28조 순매수 복귀 확인**(v18 정정 일치). **6/19 당일 외인·기관·연기금 확정 금액 = 미확인**(공개 출처 미확보) — 지수 보합·반도체만 강세 양극화 패턴상 **외인 반도체 집중매수·코스닥 매도 정황(교차검증 필요)**. **익일 KRX 투자자별 데이터로 6/22 추세 재검증**(추세 확인 보류).\n- 섹터: 반도체(SK하이닉스·삼성전기·삼성전자 시총주) **독주** vs IT부품(LG이노텍 −10.76%·원익IPS −4.41%·테스 −5.62%)·방산(한화에어로 −5.63%)·LG그룹·코스닥 전반 **광범위 차익실현**. 예외 선전: 현대차 +2.00%·한화오션 +2.64%.\n\n| 국내 보유 | 티커 | 현재가 | 당일 | 원가대비 |\n|---|---|---|---|---|\n| 삼성전자 | 005930.KS | 354,000 | −2.34% | **+34.6%** |\n| LG전자 | 066570.KS | 211,500 | **−7.44%** | **+36.3%** |\n| 두산로보틱스 | 454910.KS | 101,800 | −0.88% | +1.8% |\n| 현대차 | 005380.KS | 613,000 | **+2.00%** | −2.7% |\n| NAVER | 035420.KS | 229,500 | −2.34% | −8.4% |\n\n### 미장 (6/18 종가 — 6/19 준틴스 휴장)\n- **S&P500 7,500.58(+1.08%) · 나스닥 26,517.93(+1.91%) · 다우 51,564.70(+0.14%) · 필반(SOX) 14,341.78(+6.42% 폭등).** **FOMC 매파 셀오프(6/17) 완전 되돌림** — 단 위험선호 광범위 재점화 아닌 **반도체·메모리 단독 주도**(다우 +0.14% 구경제 소외). 채권금리·DXY 매크로 역풍 그대로 깔린 채 칩 랠리가 뚫은 구도.\n- **MU +8.70%가 엔진**(6/24 실적 D-5, HBM sold out·목표가 상향). META +1.70% 회복(6/17 고유악재 후 1차 안정화). MSFT(+0.13%)·ORCL(+0.41%) 소외.\n\n| 미국 보유 | 현재가($) | 당일 | 원가대비($) |\n|---|---|---|---|\n| NVDA | 210.69 | +2.95% | +5.6% |\n| META | 577.22 | +1.70% | **−9.0%** |\n| VOO | 688.11 | +0.98% | +6.6% |\n| MSFT | 379.40 | +0.13% | −7.5% |\n| AAPL | 298.01 | +0.70% | **+15.9%** |\n| GOOGL | 368.03 | +1.17% | −5.1% |\n| TSLA | 400.49 | +1.04% | −5.2% |\n| ORCL | 184.29 | +0.41% | **−20.6%** |\n| ANET | 169.67 | +2.87% | +4.7% |\n| MU | 1,133.99 | **+8.70%** | **+51.4%** |\n| AVGO | 411.35 | **+4.70%** | −2.3% |\n\n---\n\n## 2. 섹터 — 반도체AI / 전력·피지컬 / 빅테크\n\n### 반도체·AI인프라 (MU 6/24 실적 D-5)\n- **MU 플레이북 갱신**: 회사가이드 매출 $33.5B·EPS $19.15 vs Street 컨센 매출 ~$34.8B·EPS $19.82(레인지 $33.7B~$40.9B, 매우 넓음) = **인라인~비트 베이스라인.** 목표가 상향 러시(UBS **$1,625**·TD Cowen $1,500·Citi $1,200·RBC $1,200·MS $1,050) ↔ 구컨센 ~$612 = **컨센 이원화, 실적이 분기점.** 현주가 $1,134 > 다수 목표 = **이미 강세 하우스로 리프라이싱.** **PM 절반차익(+51%)+절반홀딩 = 비대칭 헤지 견고**(①비트+가이드상향→홀딩분 수혜 ②인라인→sell-the-news ③미스→선반영 되돌림 큼). *옵션 IV 구체치 미확인.*\n- **삼성전자**: NVDA Rubin용 HBM4 인증 통과+AMD MI400 지명(단 Rubin 점유율 SK하이닉스 60~70% > 삼성 25~30% > MU), 6/19 −2.34% 차익실현. '26 HBM 점유율 회복 전망.\n- **AVGO**(평단 −2.31%, 물타기 후보): HSBC $450→$600·JPM $500→$580 상향, ASIC(XPU) 2H FY26 가속, 컨센 ~$522. **메모리와 다른 AI 수혜축 = 물타기 시 분산효과.**\n- **⚠️ 한국 반도체 과열**: 삼성전기 PER~103배(미확인)·SK하이닉스 목표 +50% 초과 = 추격금지 룰3 대상. **SK하이닉스 ADR SEC 클리어런스 6/22주**(상장 8월→7월 앞당김 관측, 조달 $10~14B 오버행).\n\n### 전력·인프라·피지컬AI (LG전자 −7.44% 급락 진단)\n- **🔴 LG전자 211,500(−7.44%) = 펀더 무손상, 차익실현/순환매 이탈로 판별.** 5/20 18.1만→6/2 39.25만 2주 +117% 폭등의 되돌림 + **LG그룹 전반 동반 약세**(LG −7.21%·LG CNS −6.85%·LG헬로비전 −13.56%) + 로봇주 차익실현 폭탄(두산로보 전일 −15%). **NVIDIA 냉각(CDU 액냉) 인증 취소·수주 철회 보도는 외신·국내 어디서도 미확인**(협력 현재진행형). **정훈 영구룰: 손절선 폐기·홀딩**(원가 대비 +36.3%), NVIDIA CDU 인증 결과만 모니터.\n- **🟢 GEV $1,109.73(+5.80%) = 워치 유일 매수검토**: Bernstein 신규 Outperform **$1,206**(수주 +71%·백로그 $163B·서비스 55%+). 컨센 ~$1,212(34개사 Buy) ↔ Jefferies $1,350→$1,210 하향(밸류부담). **\"미국판 두산E\" 소액 소수점 진입 타당(추격금지 — 당일 +5.8% 갭 소화 후).**\n- **현대차 613,000(+2.00% 반등)**: 보스턴다이내믹스 SoftBank 풋옵션 **7/20 시한**(잔여 9.5~10%)·삼성전자 지분인수 후보설. 첫 가격표가 로봇 밸류 분기점.\n- 두산E 97,900(−1.71%, 10만 하회·모멘텀·추격금지)·한화에어로 −5.63%(2Q 방산 영익 +1,089% 펀더 견조하나 과열 되돌림)·조선 혼조(한화오션 +2.64%/HD현대중 −2.49%). 대미투자 1호 프로젝트 7월 이연. TSLA Optimus 7~8월.\n\n### 빅테크·플랫폼 (FOMC 소화 후 반등)\n- **META \"구조훼손 vs 노이즈\" = 노이즈 무게**: 6/17 −5.44% 고유악재(AI총괄 Emily Dalton Smith 이탈·Section230 면책 첫 균열) → 6/18 +1.70% 안정화. 광고 엔진 무손상·**Forward P/E 매그7 최저권 = 저가매력** ↔ **7/29 Q2 실적 전 풀사이즈 진입은 이벤트리스크**(소수점 분할만). 컨센 목표 $827.32(+43.3%).\n- **MSFT** 상방 최대(컨센 +48%, Azure 39~40% 가이던스) but 6/18 빅테크 중 최소 반등(소외). **GOOGL**(+17.6%, Cloud·Gemini, 반독점 노이즈). **AAPL**(+4.9% 목표근접·금리방어·WWDC 후 목표 상향 → **부분 트림 1순위**). **ORCL** 최대손실(−20.6%)이나 **RPO $638B(+363% YoY) 백로그 생존 = 패닉셀 금지**(OpenAI 의존 54% 집중 모니터링).\n- **NAVER 229,500 매수존 진입**: 두나무 합병(교환비 1:2.54, 9월)·메리츠 목표 410,000 상향 ↔ 플랫폼 신뢰 낮음·정리후보. **1차 트랜치 적격성은 코어(META) 우선**(아래 §7).\n- 워치: SPCX −3.56%(칩랠리 소외, **6/26 Russell·MSCI 편입/7월초 나스닥100 편입** 강제매수 vs 8월 락업 28% 언락 양방향, 추격금지) / TMUS +0.20%(T-Satellite 스타링크 D2C 7/23 출시).\n\n---\n\n## 3. 매크로 데스크\n\n- **환율 USD/KRW 1,526.13(−0.83%, 전일 1,538.91)** — FOMC 매파 달러강세에도 원화 강세 되돌림(6/18 칩랠리·외인 위험선호 동반). **1,500 하회는 미달**, 1,520대. 원화 강세 = 외인 환차손 압력 완화(수급 우호), 단 미국주 원화환산 평가액 −0.8%.\n- **금리**: 6/18 FOMC 매파 동결(3.50~3.75%, 12-0), 점도표 2026 3.4→3.8%(9/18 인상), 코어PCE 2.7→3.6% 상향. **2년물 ~4.2%·10년물 ~4.44~4.50%·DXY 100.72(2025.5來 최고).** 단 6/18 칩랠리로 셀오프 되돌림 = \"higher for longer\"보다 AI 칩 모멘텀 우위(증시-금리 디커플링). *2년물/10년물 정밀 종가는 미확인(레인지만).*\n- **유가·이란**: 브렌트 **$78 하회**·WTI **~$65**(3월來 최저, 4월 고점比 −38%). 이란 MOU **전자서명 완료 → 6/19 별도 서명식 없음**(외신 정정). 호르무즈 재통항·제재 해제 → **유가 디스인플레 경로 강화**(CPI 에너지 하방). 다음 美 CPI/PPI는 7월 중순(2주 내 없음).\n- **6/19 美 준틴스 전체 휴장**(유동성 공백) → **6/22(월) 재개장 갭 리스크**(휴장 누적 + 매파 점도표 소화). 엔캐리(BOJ 1.0%·USD/JPY 160 부근) 잔존 — 6/22 갭과 겹치면 변동성 증폭 주시. **한은 7/16 금통위 2.50→2.75% 인상 전망**(신현송 매파). 한국은행은 점도표 발표 안 함(연준 전용).\n\n---\n\n## 4. 리서치 피드 (경제사냥꾼 — 롱폼 2편 자막 확보, 쇼츠 5편 봇차단)\n\n> 6/18 롱폼 2편(FOMC편·MSCI편) ko자막 확보. **6/19 쇼츠 5편은 자동자막 부재 + 샌드박스 SSL 차단으로 자막 미확보**(제목만 트래킹, 12월 로컬 이전 시 재확보). 누적 로그 `docs/research/hunter_log.md` 갱신 완료.\n\n| 영상 | 핵심 주장 | 분류 |\n|---|---|---|\n| **6/18 \"케빈 워시 첫 FOMC 전부 뜯었다\"** | 만장일치 동결·점도표 3.4→3.8(9명 인상)·PCE 2.7→3.6 / \"시점은 매파, 방향은 인하 불변\" / 돈은 달러·장기채·반도체로 대피 | **[검증]** 점도표·PCE·동결 전부 일치(CNBC/StockTitan) |\n| ↳ \"FOMC 후 SOX +1.4% 반도체만 생존\" | — | **🔧[정정·시점]** 이는 **6/17 당일 한정**. **6/18은 SOX +6%대 신고가로 완전 되돌림** = \"매파 1일천하\". 보유 NVDA·MU·AVGO엔 오히려 호재 |\n| ↳ 유가 \"WTI 70달러대 중후반\" | — | **🔧[정정]** 실제 **~$65**(과장/자막오류). 디스인플레 명분 오히려 강화 |\n| **6/18 \"MSCI 코스피 역대급 상승장\"** ★국장 | MSCI **6/24 05:30 시장분류 발표**·6/19 새벽 접근성 점수 / 44조 유입은 단일 증권사 가정(타사 −29조) / 진짜 알맹이=외환개혁(7/6 24시간) / 대형 반도체 수혜·중소형 강제탈락 양극화 | **[검증]** 6/24 발표·외환개혁 일치 / **[미확인]** +44조·−29조·60% 확률·\"승격 1년후 −24.6%\"는 단일출처 |\n| ↳ \"대형주 쏠림·중소형 소외 양극화\" | — | **[검증·현실화]** 6/19 코스닥 −6.33%·LG이노텍 −10.76%·LG전자 −7.44% = MSCI 양극화 프레임 현실 장면 |\n| **6/19 쇼츠 5편**(자막 미확보) | SK하이닉스 美상장★ / Intel+Apple 한국반도체 기회★ / 6/19 투자포인트 / 캐시우드 주도주 / 조선 슈퍼사이클★ | [미확보] 제목만 트래킹 |\n\n> **채널 오늘 시각**: ①FOMC = \"시점(단기 매파) vs 방향(장기 인하)\" 분리 프레임(정훈 트리거 설계와 정합, 단 6/18 반도체 신고가는 영상이 못 담은 최신 사실) ②코스피 9000 = MSCI 기대+반도체 슈퍼사이클 \"2년짜리 기대감 랠리 출발선\"(장기보유 철학 정합, 단 양극화 경고가 6/19 현실화). 신규 테마 = **MSCI 6/24·외환개혁 7/6·Intel-Apple 딜(삼성 파운드리 함의)**.\n\n---\n\n## 5. 리스크 데스크 (신중/bear)\n\n- **🚦 트리거**: 안전핀 7,500 **미발동**(현 9,052, +20.7% 여유) / 2차 8,000(+13.2%)·삼성 매수존 295~305k(현 354k, +16% 위) 대기 / 두산E 10만(현 97,900, −2.1% 근접·추격금지) / **🔴 NAVER 1차 매수존 진입(229,500) = 유일 발동** / FOMC 3차 트랜치 = **매파 보류 확정**.\n- **🚨 위반 없음 / 룰3(추격매수 금지) 고강도 적용일**: 코스피 9천·MU +51%·SOX +6.42%·MU당일 +8.70% = 전형적 FOMO 헤드라인 클러스터. **FOMC 매파 확정 상태의 위험자산 급반등 = 셀오프 되돌림(technical)이지 매크로 개선 아님** → **현금 624,771원 전액 동결 정당.**\n- **🔴 집중도(사실상 단일 포지션)**: AI 메모리/HBM **6중 쏠림**(삼성·NVDA·MU·AVGO·SK하이닉스·삼성전기) + 미국 11종목 단일 원/달러 환노출. **MU +51%로 비중 자동 확대 → 6/24 단일 야간 이벤트(폰 미가용)에 포트 변동성 비대칭 연동.** **MU 절반차익 = 집중도 완화의 유일한 능동 수단.**\n- **NAVER 매수존 단서**: 발동(229,500 ∈ 225~235k)은 룰상 유효하나 NAVER는 **\"플랫폼 신뢰 낮음·정리 후보\"** 종목, 디커플링 장세에 정리후보 첫 트랜치는 논리 충돌 → (a) 소액(10만 하단)만 or (b) **6/22 외인 추세 확인까지 1일 보류** 권고.\n- **bear 핵심**: 오늘 강세론 최대 약점 = **상승의 질.** 코스피 9천은 시총 4사 59.6%·상승 109 vs 하락 791이 보여주듯 **반도체 4종목이 떠받친 극단 디커플링**, 코스닥 −6.33%·LG전자 −7.44%·LG이노텍 −10.76%·두산로보 −15%는 지수 밑 광범위 차익실현 진행(펀더 무손상이나 수급 피로). 美 SOX +6.42%는 매파 셀오프의 **기술적 되돌림**이지 통화환경 개선 아님(점도표 인상 전환·2년물 그대로). 외인 6/18 +1.28조 복귀했으나 **6/19 미확인 + 준틴스 휴장 = 추세 확인 6/22 보류.** **레버리지 없는 4종목 지수 + 미확인 수급 + 매파 매크로 위에서 사상최고가 추격이 최대 리스크.**\n\n---\n\n## 6. 강세 vs 신중 디베이트\n\n**강세(bull)**: FOMC 매파 충격은 1일천하 — 6/18 SOX +6.42%·MU +8.70%·AVGO +4.70%로 셀오프 완전 되돌림, AI 칩 모멘텀이 매크로 매파를 뚫음(Intel+Apple 딜 촉매). MU 목표가 $1,200~1,625 상향 러시·HBM 2026 sold out = 탈순환주 리프라이싱. 삼성 HBM4 Rubin+AMD 지명, SK하이닉스 ADR 7월 앞당김. 컨센 대부분 +30~48% 상방(NVDA·META·MSFT·AVGO·ORCL·TMUS). MU +51%·AAPL +16%·삼성 +35%·LG전자 +36% 코어 견조. 원화 강세(1,526)·유가 $65·MSCI 6/24 선진국 기대 = 코스피 2년 랠리 출발선. 환차익 반영 주식손익 ≈ +57.6만원.\n\n**신중(bear)**: 코스피 9천은 반도체 4종목(시총 59.6%)이 떠받친 극단 디커플링 — 코스닥 −6.33%·LG전자/LG이노텍/두산로보 동반 급락은 지수 밑 광범위 차익실현 진행. SOX 반등은 기술적 되돌림이지 매크로 개선 아님(점도표 인상 전환·DXY 100.72·2년물 그대로). AI 메모리 단일 테마+단일 환노출 과집중(MU +51%로 6/24 단일 이벤트 비대칭 연동). 외인 6/18 +1.28조 복귀했으나 6/19 미확인+준틴스 휴장으로 추세 확인 보류. MSCI 6/24·MU 6/24·6/22 갭 리스크·이란 서명 클러스터가 4일 +11.6% 급등의 되돌림 방아쇠.\n\n**PM 저울질**: 코어 강세 논지(AI 슈퍼사이클·매파 1일천하)는 **회복 우위**로 본다. 단 **상승의 질(디커플링)·미확인 외인 수급·6/22 갭 = 추격 금지·현금 보존·이벤트 확인이 정석.** 신규 진입은 매수존 진입한 NAVER조차 6/22 외인 확인 후. (무게는 PM 종합 §7.)\n\n---\n\n## 7. PM 종합 (최종)\n\n### 🎯 오늘의 한 줄 결론\n**FOMC 매파는 1일천하 — 6/18 반도체 폭등으로 AI 코어 재확인(MU +51%). 그러나 코스피 9천은 반도체 4종목이 떠받친 극단 디커플링이고 외인 6/19 수급은 미확인. 추격 금지·현금 62만원 전액 보존, NAVER 매수존조차 6/22 외인 확인 후. MU 6/24 절반차익(6/23 베이킹)이 유일한 능동 액션.**\n\n### 보유 16종목\n\n| 종목 | 현재가 | 당일 | 원가대비 | 목표가(컨센) | 상방 | 매수존 | 매도/트림 | ⭐ | 한줄 |\n|---|---|---|---|---|---|---|---|---|---|\n| 삼성전자 | 354,000 | −2.34% | +34.6% | 48~53만(KB/미래) | +36~50% | 295~305k(이탈) | 트림보류 | ⭐⭐⭐⭐ | HBM4 Rubin+AMD, 숨고르기, 코어 |\n| LG전자 | 211,500 | −7.44% | +36.3% | 컨센 초과 | — | 홀딩 | 손절선 없음 | ⭐⭐⭐⭐ | 그룹 동반 차익실현·펀더 무손상=홀딩 |\n| 두산로보틱스 | 101,800 | −0.88% | +1.8% | 극단분산 | — | 관망 | 모멘텀 | ⭐⭐ | 전일 −15% 모멘텀, 추격금지 |\n| 현대차 | 613,000 | +2.00% | −2.7% | 60만(공격 80만) | +0~30% | 관망 | — | ⭐⭐⭐ | BD 풋옵션 7/20·삼성 지분설, 반등 |\n| NAVER | 229,500 | −2.34% | −8.4% | ~30만(메리츠 41만) | +31% | **225~235k(진입🔴)** | 정리후보 | ⭐⭐ | 매수존 진입 but 정리후보=소액/6/22 대기 |\n| NVDA | $210.69 | +2.95% | +5.6% | $298.93 | +41.9% | 눌림 | 비중관리 | ⭐⭐⭐⭐⭐ | Rubin HBM4 3사인증, 코어 |\n| META | $577.22 | +1.70% | −9.0% | $827.32 | +43.3% | 실적확인 | — | ⭐⭐⭐⭐ | 고유악재 회복(노이즈), 7/29 전 보류 |\n| VOO | $688.11 | +0.98% | +6.6% | — | — | 적립 | — | ⭐⭐⭐⭐ | 분산형 코어(채널도 '안전') |\n| MSFT | $379.40 | +0.13% | −7.5% | $561.39 | +48.0% | 눌림 | — | ⭐⭐⭐⭐ | 상방 최대, 6/18 빅테크 중 소외 |\n| AAPL | $298.01 | +0.70% | +15.9% | $312.72 | +4.9% | 목표근접 | **트림 1순위** | ⭐⭐⭐ | 금리방어·WWDC 후 목표상향 |\n| GOOGL | $368.03 | +1.17% | −5.1% | $432.83 | +17.6% | 눌림 | — | ⭐⭐⭐⭐ | Cloud·Gemini, 반독점 노이즈 |\n| TSLA | $400.49 | +1.04% | −5.2% | $420.55 | +5.0% | 관망 | — | ⭐⭐⭐ | Optimus 7~8월, 상방 제한 |\n| ORCL | $184.29 | +0.41% | −20.6% | $252.64 | +37.1% | 눌림 | 패닉셀 금지 | ⭐⭐⭐ | RPO $638B 백로그, OpenAI 54% 집중 |\n| ANET | $169.67 | +2.87% | +4.7% | $189.13 | +11.5% | 홀딩 | — | ⭐⭐⭐⭐ | AI 네트워크, 목표 상향 |\n| MU | $1,133.99 | +8.70% | +51.4% | $879(−22%)→상향중 | (리프라이싱) | **6/24 실적** | **절반 차익** | ⭐⭐⭐⭐ | sold out, +51% 6/24 절반차익 |\n| AVGO | $411.35 | +4.70% | −2.3% | $522.06 | +26.9% | 조정주 | 물타기 후보 | ⭐⭐⭐ | ASIC, 평단 근접 물타기후보 |\n\n> 컨센 ±30% 괴리(상방): NVDA·META·MSFT·AVGO·ORCL·TMUS = 🟢. MU는 목표 급상향 진행형(구컨센 $612 vs 신컨센 $1,200~1,625 이원화) → \"주가>목표\"는 리프라이싱(6/24 실적이 분기점, 절반 차익).\n\n### 워치리스트 (활성)\n| 종목 | 현재가 | 당일 | 목표(컨센) | 비고 |\n|---|---|---|---|---|\n| **GE Vernova** | $1,109.73 | +5.80% | $1,211.72(+9.2%) | 🟢 **Bernstein 매수개시 $1,206**·수주+71%. 워치 유일 매수검토(소액 소수점·갭 소화 후) |\n| 두산에너빌리티 | 97,900 | −1.71% | 13.5~16.5만 | 10만 하회, **추격금지**. SMR 진짜수혜, 93~95k 눌림 소액만 |\n| SK하이닉스 | 2,764,000 | +2.94% | Strong Buy | HBM4E 12단, **ADR SEC 6/22주·7월 앞당김** 관측. 목표 +50%초과=추격 부적합 |\n| 삼성전기 | 2,270,000 | +3.18% | iM 230/DB 300만 | PER~103배 과열 최선두, 추격금지 |\n| LG이노텍 | 1,145,000 | **−10.76%** | KB 160만 유지 | FC-BGA, 그룹 동반 급락이나 sell-side 성장성 긍정 유지 |\n| 원익IPS/테스 | 156,000/166,200 | −4.41%/−5.62% | — | 소부장 차익실현(.KQ 코스닥) |\n| SK이노 | 102,400 | −1.06% | — | SMR(테라파워 2대주주) |\n| 한화에어로/조선3 | 1,122,000/— | −5.63% | — | 방산 펀더 견조하나 과열 되돌림, 한화-KAI |\n| STM/TMUS/SPCX | $78.39/$181.67/$185.00 | +6.86%/+0.20%/−3.56% | STM $64(−18%)/TMUS $260.81(+44%)/SPCX $188(+2%) | STM 컨센 하향=보류 / SPCX 6/26 MSCI·7월초 나스닥100 vs 8월 락업 |\n\n### 제안 액션\n- **관망 디폴트** — 매수존 진입 NAVER 외 전 종목 위 이탈 + 외인 6/19 미확인 + 6/22 갭 리스크. **현금 624,771원 전액 보존.**\n- **NAVER 1차 트랜치**: 매수존(225~235k) 진입 발동이나 **정리후보 + 디커플링** → **6/22 외인 추세 확인까지 1일 보류** 권고(집행 시 소액 10만 하단만). 코어 우선순위는 META.\n- **🔴 3차 트랜치(META·AVGO) = 매파로 보류 유지.** META 풀사이즈는 7/29 Q2 실적 후(소수점 분할은 가능). 오늘 저녁 폰창(17:30~20:50)에 **보유분 투매 금지**(LG전자·LG이노텍 급락은 그룹 차익실현이지 펀더 훼손 아님).\n- **6/24 MU 실적(야간) 절반 차익 = 6/23 저녁 사전 베이킹 필수**(폰 미가용). +51% 고밸류·집중도 완화·인라인 리스크 헤지. 소수점 시장가 조건부 예약.\n- **추격 금지**: 두산E·SK하이닉스·삼성전기. GEV만 워치 중 소액 검토(당일 +5.8% 갭 소화 후 눌림 분할).\n- **외인 6/22 종가 = 강세 논지 추세 분수령**(반도체 집중매수·코스닥 매도 정황 확정 여부).\n\n### 현금 배분 플랜 (624,771원, 3분할 미집행)\n- **1차 ~12.5만**: NAVER 225~235k **진입 발동** but 정리후보 → **6/22 외인 확인 후 소액**, 또는 삼성 295~305k(현 354k, 멀음) 눌림 대기.\n- **2차 ~20만**: 코스피 8,000 하회 + 이벤트 악재 동반 시(현 9,052, 미도달).\n- **3차 ~22.5만**: 🔴 **FOMC 매파로 보류 유지.** 비둘기 전환·META 7/29 실적·외인 복귀 추세 확인 중 하나까지 동결.\n- ⚠️ GEV 소액 소수점(갭 소화 후)·두산E 9만 초중반 1주는 트랜치 본예산과 분리, 편입 시 승인 필요.\n\n### 지켜볼 것 (2주 캘린더)\n| 날짜(KST) | 이벤트 | 폰 |\n|---|---|---|\n| **6/19(금) 저녁** | 폰창: 보유분 투매 금지·NAVER 6/22 보류 메모·외인 종가 확인 | ✅ |\n| 6/22(월) | 美 재개(갭 리스크) / **SK하이닉스 ADR SEC 클리어런스 주** / **외인 추세 재검증** | ❌야간 |\n| **6/23(화) 저녁** | **MU 절반 차익 사전 베이킹**(6/24 야간 실적용) | ✅ |\n| **6/24(수)** | **MU 실적**(절반 차익) + **MSCI 05:30 시장분류 발표**(한국 선진국 관찰대상국) | ❌야간 |\n| 6/26(금) | SPCX MSCI·Russell 편입 메커닉 | — |\n| 7/6(월) | 외환시장 원/달러 24시간 확대(MSCI 핵심 숙제) | — |\n| **7/16(목)** | **한은 금통위(2.50→2.75% 인상 전망, 신현송 매파)** | ✅오전 |\n| 7/22~30 | 美 실적(TSLA·GEV·TMUS 7/22, GOOGL 7/23, LG전자 7/24, 삼성·META·MSFT 7/29, AAPL 7/30) | — |\n\n---\n\n## 8. 오늘의 이슈 선택지\n1. **MU 6/24 실적 베이킹 매뉴얼** — 절반 차익(+51%) vs 전량 홀딩, 비트/인라인/미스별 주가 반응(컨센 이원화 $612 vs $1,200~1,625), 6/23 저녁 소수점 시장가 조건부 예약 구체화. MSCI 6/24 동시 D-day 고려.\n2. **코스피 디커플링 = 신중 신호인가?** — 반도체 4종목 59.6% 쏠림·코스닥 −6.33%·상승 109 vs 하락 791의 의미, MSCI 양극화 프레임, 외인 6/22 확인법, 강세 논지 하향 임계치.\n3. **LG전자/LG이노텍 급락 = 매수기회 vs 회피?** — 그룹 동반 차익실현(펀더 무손상) vs 추가 조정, LG전자 NVIDIA CDU 인증 모니터 포인트, LG이노텍 KB 160만 유지의 신뢰도.\n4. **NAVER 매수존 1차 트랜치 집행 여부** — 정리후보 vs 매수존(225~235k)·두나무 합병(9월)·메리츠 41만, 디커플링 장세 집행 타당성, 6/22 외인 확인 조건.\n\n---\n\n## STATE SNAPSHOT\n```\n[STATE SNAPSHOT v19 2026-06-19]\n현금: 624,771원 (트랜치 1차/2차/3차 전부 미집행 — 3차는 FOMC 매파로 보류 유지, 1차 NAVER 매수존 발동했으나 정리후보→6/22 외인 확인까지 보류 권고)\n보유변동: 없음 (16종목 유지)\n시세기준: KR=6/19 마감(코스피 9,052.42 −0.13% 첫 숨고르기 / 코스닥 966.59 −6.33% 폭락 디커플링) / US=6/18 종가(6/19 美 준틴스 휴장, SOX +6.42% 매파 셀오프 완전 되돌림) / USD/KRW 1,526.13\n총자산: 8,501,903원 · 주식손익 +305,143(환차익 미반영) / 환차익 반영 추정 ≈ +576,205원 (정확값은 토스 정본)\n오늘 할 일: 추격금지·현금 전액 보존 / 보유분 투매 금지(LG전자·LG이노텍 급락=그룹 차익실현, 펀더 무손상) / NAVER 매수존 발동→6/22 외인 확인까지 보류 / MU 6/24 절반차익 6/23 저녁 베이킹 / GEV 워치 소액 검토(갭 소화 후)\nFOMC 후속: 🟢 매파 셀오프 \"1일천하\" — 6/18 SOX +6.42%·MU +8.70%·AVGO +4.70%로 완전 되돌림(Intel+Apple 딜). 단 점도표 인상 전환·DXY 100.72·2년물 그대로 = 기술적 되돌림(매크로 개선 아님)\n수급경보: 🟡 외인 6/18 종가 +1.28조 순매수 복귀 확인 / 6/19 당일 외인 금액 미확인(준틴스 휴장) → 6/22 KRX 투자자별 데이터로 추세 재검증 필수\n워치리스트(활성): GE Vernova(매수검토·갭소화후)·두산에너빌리티(10만 하회)·SK하이닉스(ADR 6/22주)·삼성전기(과열)·LG이노텍(−10.76% 그룹 동반)·원익IPS·테스·SK이노·한화에어로·조선3·STM·TMUS·SPCX\n대기 트리거:\n  ① 3차 트랜치 = 🔴매파로 보류 유지(비둘기 전환·META 7/29 실적·외인 복귀 추세 중 하나까지 동결)\n  ② 6/24 MU 실적 → 절반 차익(6/23 저녁 베이킹, +51% 고평가·집중도 완화)\n  ③ 6/22 美 재개 갭 리스크 + SK하이닉스 ADR SEC 클리어런스 주 + 외인 추세 재검증\n  ④ NAVER 1차 매수존(225~235k) 발동 — 정리후보라 6/22 외인 확인 후 소액만\n  ⑤ MSCI 6/24 05:30 시장분류 발표(한국 선진국 관찰대상국 등재 여부) + 외환개혁 7/6\n  ⑥ 한은 7/16 금통위 2.50→2.75% 인상 전망\n영구교정(신규):\n  - FOMC 매파 셀오프 = \"1일천하\": 6/17 충격(META −5.44%·나스닥 −1.34%) → 6/18 완전 되돌림(SOX +6.42% 신고가·MU +8.70%·AVGO +4.70%·NVDA +2.95%·META +1.70%). Intel+Apple 협업 딜 촉매. 점도표/DXY/2년물은 그대로 = 기술적 되돌림\n  - 코스피 6/19 9,052.42(−0.13%) 첫 숨고르기 / 코스닥 966.59(−6.33% 폭락) 디커플링 극단(시총 4사 59.6%·상승109 vs 하락791)\n  - LG전자 6/19 −7.44%(211,500)·LG이노텍 −10.76% 급락 = LG그룹 전반 동반 차익실현(LG −7.21%·LG CNS −6.85%) + 로봇주 차익실현(두산로보 전일 −15%), NVIDIA CDU 인증 취소 등 펀더 훼손 뉴스 없음 → 룰대로 홀딩\n  - MU 원가대비 +51.4%($1,133.99), 6/24 실적 D-5. 목표 이원화(구컨센 $612 vs 신컨센 UBS $1,625·Citi/RBC $1,200·MS $1,050)\n  - 이란 휴전 MOU = 전자서명 완료(6/19 스위스 별도 서명식 없음), 브렌트 $78 하회·WTI ~$65, DXY 100.72(2025.5來 최고)\n  - 신규 이벤트: MSCI 6/24 05:30 연례 시장분류 발표(한국 선진국 관찰대상국)·6/19 새벽 접근성 점수·외환개혁 7/6 원/달러 24시간 확대\n  - 경제사냥꾼 정정: \"FOMC 후 SOX+1.4% 반도체만 생존\"=6/17 당일 한정(6/18 완전 되돌림) / 유가 \"70달러대 중후반\"=실제 ~$65 과장\n  - GEV Bernstein 매수개시 $1,206(수주+71%), 컨센 $1,211.72, Jefferies $1,210 하향 / 현대차 BD 풋옵션 7/20 시한·삼성 지분인수설 / SK하이닉스 ADR 8월→7월 앞당김 관측\n리서치: 경제사냥꾼 롱폼 2편(FOMC·MSCI) 자막확보·쇼츠 5편 봇차단 미확보(12월 로컬 이전 시 재확보)\n다음 버전: v20\n```\n\n*투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "holdings_final_2026-06-19",
      "file": "docs/reports/holdings_final_2026-06-19.md",
      "title": "🏁 정훈 최종보고 · 2026-06-19 (금)",
      "date": "2026-06-19",
      "version": null,
      "kind": "보유확정",
      "preview": "💎 핵심 액션 4개만 콕",
      "content": "# 🏁 정훈 최종보고 · 2026-06-19 (금)\n\n> KR=6/19 마감 / US=6/18 종가(6/19 美 준틴스 휴장) / USD/KRW 1,526.13 · 투자 자문 아님, 최종 결정은 정훈.\n> **한 줄: \"FOMC 매파는 1일천하(6/18 반도체 폭등) — 그러나 코스피 9천은 반도체 4종목이 떠받친 디커플링. 추격 금지·현금 62만원 보존, MU 6/24 절반차익만 능동.\"**\n\n---\n\n## ① 보유 16종목\n\n| 종목 | 현재가 | 당일 | 원가대비 | 목표가(컨센) | 매수존 | 매도/트림 | ⭐ |\n|---|---|---|---|---|---|---|---|\n| 삼성전자 | 354,000원 | −2.34% | **+34.6%** | 480,000~530,000원 | 295,000~305,000원(이탈) | 트림 보류 | ⭐⭐⭐⭐ |\n| LG전자 | 211,500원 | **−7.44%** | **+36.3%** | 컨센 초과 | 홀딩 | 손절선 없음 | ⭐⭐⭐⭐ |\n| 두산로보틱스 | 101,800원 | −0.88% | +1.8% | 극단 분산 | 관망 | 모멘텀 | ⭐⭐ |\n| 현대차 | 613,000원 | **+2.00%** | −2.7% | 600,000(공격 800,000) | 관망 | — | ⭐⭐⭐ |\n| NAVER | 229,500원 | −2.34% | −8.4% | ~300,000(메리츠 410,000) | **225,000~235,000원(진입🔴)** | 정리후보 | ⭐⭐ |\n| NVDA | $210.69 | +2.95% | +5.6% | $298.93 (+41.9%) | 눌림 | 비중관리 | ⭐⭐⭐⭐⭐ |\n| META | $577.22 | +1.70% | −9.0% | $827.32 (+43.3%) | 실적확인 | — | ⭐⭐⭐⭐ |\n| VOO | $688.11 | +0.98% | +6.6% | — | 적립 | — | ⭐⭐⭐⭐ |\n| MSFT | $379.40 | +0.13% | −7.5% | $561.39 (+48.0%) | 눌림 | — | ⭐⭐⭐⭐ |\n| AAPL | $298.01 | +0.70% | **+15.9%** | $312.72 (+4.9%) | 목표근접 | **트림 1순위** | ⭐⭐⭐ |\n| GOOGL | $368.03 | +1.17% | −5.1% | $432.83 (+17.6%) | 눌림 | — | ⭐⭐⭐⭐ |\n| TSLA | $400.49 | +1.04% | −5.2% | $420.55 (+5.0%) | 관망 | — | ⭐⭐⭐ |\n| ORCL | $184.29 | +0.41% | **−20.6%** | $252.64 (+37.1%) | 눌림 | 패닉셀 금지 | ⭐⭐⭐ |\n| ANET | $169.67 | +2.87% | +4.7% | $189.13 (+11.5%) | 홀딩 | — | ⭐⭐⭐⭐ |\n| MU | $1,133.99 | **+8.70%** | **+51.4%** | $879→상향중 | **6/24 실적** | **절반 차익** | ⭐⭐⭐⭐ |\n| AVGO | $411.35 | +4.70% | −2.3% | $522.06 (+26.9%) | 조정주 | 물타기 후보 | ⭐⭐⭐ |\n\n```\n💎 핵심 액션 4개만 콕\n① MU(+51.4%) — 6/24 실적(야간·폰 미가용) → 절반 차익을 6/23 저녁 소수점 시장가 조건부 예약으로 베이킹.\n   집중도(HBM 6중 쏠림) 완화 + 인라인 sell-the-news 헤지. 절반은 sold-out 슈퍼사이클 홀딩.\n② LG전자(−7.44%)·LG이노텍(−10.76%) — 급락의 정체 = LG그룹 전반 차익실현 + 로봇주 되돌림.\n   NVIDIA 냉각(CDU) 인증 취소 등 펀더 훼손 뉴스 '없음' → 룰대로 홀딩, 투매 금지. CDU 인증 결과만 모니터.\n③ AAPL(+15.9%) — 목표 근접·금리방어 입증 = 부분 트림 1순위 후보(다만 오늘은 관망, 매크로 악재 확인 시).\n④ 현금 624,771원 — 전액 보존. 추격금지(코스피 9천·MU+51%·SOX+6.42% = FOMO 헤드라인). 3차 트랜치 매파 보류 유지.\n```\n\n---\n\n## ② 워치리스트\n\n| 종목 | 현재가 | 당일 | 목표(컨센) | 액션 |\n|---|---|---|---|---|\n| **GE Vernova** | $1,109.73 | +5.80% | $1,211.72 (+9.2%) | 🟢 워치 유일 매수검토(Bernstein 매수개시 $1,206·수주+71%) |\n| 두산에너빌리티 | 97,900원 | −1.71% | 135,000~165,000원 | 10만 하회, 추격금지 |\n| SK하이닉스 | 2,764,000원 | +2.94% | Strong Buy | ADR SEC 6/22주·7월 앞당김 관측, 목표+50%초과=추격 부적합 |\n| 삼성전기 | 2,270,000원 | +3.18% | 2,300,000~3,000,000원 | PER~103배 과열, 추격금지 |\n| LG이노텍 | 1,145,000원 | **−10.76%** | KB 1,600,000원 유지 | 그룹 동반 급락, sell-side 성장성 긍정 유지 |\n| 원익IPS / 테스 | 156,000 / 166,200원 | −4.41% / −5.62% | — | 소부장 차익실현 |\n| SK이노 | 102,400원 | −1.06% | — | SMR(테라파워 2대주주) |\n| 한화에어로 / 조선3 | 1,122,000원 / — | −5.63% | — | 방산 펀더 견조하나 과열 되돌림 |\n| STM / TMUS / SPCX | $78.39 / $181.67 / $185.00 | +6.86% / +0.20% / −3.56% | $64 / $260.81 / $188 | STM 보류 / TMUS +44% 여력 / SPCX 6/26 MSCI vs 8월 락업 |\n\n```\n👀 워치 콕: GEV만 소액 소수점 검토(당일 +5.8% 갭 소화 후 눌림 분할, 트랜치 본예산과 분리·승인 필요).\n   두산E·SK하이닉스·삼성전기는 추격금지 알림만.\n```\n\n---\n\n## ③ 현금 배분 — 624,771원 (3분할 미집행)\n\n**🅰️ 관망 (룰 정합·추천)**\n- 1차 ~125,000원: NAVER 매수존(225,000~235,000원) 진입 발동했으나 **정리후보 + 디커플링 → 6/22 외인 추세 확인까지 보류.** 집행 시 소액 하단만.\n- 2차 ~200,000원: 코스피 8,000 하회 + 이벤트 악재 동반(현 9,052, 미도달).\n- 3차 ~225,000원: 🔴 FOMC 매파로 보류 유지.\n- → **결론: 6/22 외인 종가 확인 전까지 전액 보존이 정석.**\n\n**🅱️ 공격 (강세 회복 베팅)**\n- NAVER 매수존 1차 소액(~100,000원) 선집행 + GEV 소수점 ~50,000원(갭 소화 후).\n- 단 6/22 갭 리스크·외인 미확인·6/24 MU/MSCI 이벤트 클러스터 노출 → **추격금지 룰과 충돌, 비권장.**\n\n---\n\n## ④ 2주 일정 (KST)\n\n| 날짜 | 이벤트 | 폰 |\n|---|---|---|\n| **6/19 저녁** | 폰창: 투매 금지·NAVER 보류 메모·외인 종가 확인 | ✅ |\n| 6/22(월) | 美 재개(갭 리스크) / SK하이닉스 ADR SEC 주 / **외인 추세 재검증** | ❌야간 |\n| **6/23 저녁** | **MU 절반차익 사전 베이킹** | ✅ |\n| **6/24(수)** | **MU 실적 + MSCI 05:30 시장분류 발표**(한국 선진국 관찰대상국) | ❌야간 |\n| 7/6(월) | 외환시장 원/달러 24시간 확대(MSCI 숙제) | — |\n| **7/16(목)** | **한은 금통위 2.50→2.75% 인상 전망** | ✅오전 |\n| 7/22~30 | 美 실적(삼성·META·MSFT 7/29, AAPL 7/30 등) | — |\n\n---\n\n## ⑤ 월말 목표 + 전략 3 + 오늘 할 것\n\n**📅 6월말 목표**: 현금 62만원 룰 정합 보존 + MU 6/24 절반차익으로 집중도 완화 1건 실행 + 외인 추세(6/22) 재확인으로 강세/신중 판정.\n\n**🧭 전략 3**\n1. **\"산 이유가 살아있나\" 매도 디시플린** — LG전자(NVIDIA 협력)·MU(HBM sold out)·NVDA(Rubin) 논지 전부 생존 → 급락·고평가에도 코어 홀딩. AAPL만 목표근접 트림 1순위.\n2. **FAB10 렌즈(집중도)** — AI 메모리/HBM 6중 쏠림이 최대 약점. MU +51% 절반차익 = 유일한 능동적 분산 수단.\n3. **디커플링 경계** — 코스피 9천은 반도체 4종목(59.6%)이 떠받친 신고가. 외인 6/22 확인 전 신규 진입 보류.\n\n**✅ 오늘(6/19 저녁) 할 것**\n- [ ] 보유분 투매 금지(LG전자·LG이노텍 급락 = 그룹 차익실현, 펀더 무손상)\n- [ ] NAVER 매수존 발동 메모만 — 집행은 6/22 외인 확인 후\n- [ ] 외인 6/19 종가 수급 확인(KRX 투자자별, 가능 시)\n- [ ] MU 6/24 절반차익 → 6/23 저녁 베이킹 일정 리마인드\n- [ ] 3차 트랜치 \"예약 미입력\" 유지 확인(매파 보류)\n\n---\n\n## 🎯 결론\n\n**FOMC 매파는 하루천하였고 AI 반도체 코어는 6/18 폭등으로 재확인됐다(MU +51%). 하지만 코스피 9천의 속살은 반도체 4종목이 떠받친 극단 디커플링이고, 외인 6/19 수급은 준틴스 휴장으로 미확인이다. 지금은 사상최고가를 좇을 때가 아니라 현금 62만원을 지키고 6/22 외인 종가로 추세를 확인할 때. 능동 액션은 단 하나 — MU 6/24 절반차익 베이킹으로 집중도를 능동적으로 줄이는 것. 나머지는 홀딩과 관망. 💪**\n\n*투자 자문 아님. 모든 레벨은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v18_2026-06-18",
      "file": "docs/reports/report_v18_2026-06-18.md",
      "title": "정훈 PORTFOLIO DESK · v18 · 2026-06-18",
      "date": "2026-06-18",
      "version": 18,
      "kind": "보고서",
      "preview": "1. 6/24 MU 실적 베이킹 매뉴얼 — 절반 차익 vs 전량 홀딩 시나리오, 비트/인라인/미스별 주가 반응(±9.5% IV)과 6/23 저녁 사전 예약 구체화. 집중도 완화 관점.",
      "content": "# 정훈 PORTFOLIO DESK · v18 · 2026-06-18\n\n> 투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.\n> 시세 기준: **KR=6/18 마감** / **US=6/17 종가(FOMC 6/18 03:00 KST 직후 반응 반영)** / USD/KRW **1,521**. 9개 데스크(지역2·섹터3·매크로·리서치·리스크 + 정량스크립트4) 종합.\n> ⚠️ 오늘은 **FOMC 직후 + 코스피 9,000 첫 돌파 + 대미투자 특별법 시행 + 美 네마녀의날**이 겹친 대형 장세 분기일.\n\n---\n\n## 변경점 (직전 v17 / 6/17 대비)\n\n- **🔴 FOMC = 매파(Hawkish Hold) 확정** — 동결(3.50~3.75%, 12-0)이나 **점도표 2026 중앙값 3.4%→3.8% 상향**(18인 중 9인 연내 인상, 6인 2회+), 워시 본인 dot 거부, 성명서 130단어로 축소(easing bias 삭제), 코어 PCE 전망 2.7%→3.3%. **2년물 +16bp(4.216%)·10년물 +7bp(4.499%)·DXY 상승 = 판정 키 둘 다 매파.** → **3차 트랜치(META·AVGO) 전면 보류 확정**(베이킹 룰 🔴 분기).\n- **🟢 코스피 사상 첫 9,000 돌파** — 8,864(6/17) → **9,016~9,024(6/18, +1.7~1.8%, Yahoo 9,011/+1.66%), 4일째 사상최고.** 골드만 목표 9,000 도달(이미 12,000 추가 상향). 단 **\"기승전 반도체\"** 극단 쏠림.\n- **🔴 외국인 2거래일 연속 순매도** — 6/17(−9,997억)에 이어 **6/18도 −약 6천억~9,972억 순매도(출처별 차이)**. 개인(+5,100~7,800억) 단독으로 신고가 떠받침. **CLAUDE.md 핵심 신호(\"외인=메인 엔진\") 추세화 경보.**\n- **🔴 META −5.44%($567.58) = FOMC 아닌 종목 고유 악재** — AI 'AI for Work' 총괄 Emily Dalton Smith 부임 2개월 만 이탈(Reuters 단독) + 캘리포니아 중독소송 Section 230 면책 첫 돌파(KGM 평결 $6M·MDL 3047). **단 투자 논지(AI 광고 수익화) 엔진은 무손상 = 단기~약한 구조적 노이즈.**\n- **반도체 순환매 복귀** — 미 SOX +1.38%(MU +2.20%·AVGO +4.30%), 국내 삼성전기 +9.25%·SK하이닉스 +6.82%(사상 첫 260만)·삼성전자 +2.02%. 단 밸류 과열 경고(SK하이닉스 목표 +50% 초과).\n- **두산에너빌리티 10만 재돌파**(100,100), **대미투자 특별법 6/18 시행**(KUIC 출범)이나 1호 프로젝트 7월 이연으로 원전·조선 차익실현.\n\n---\n\n## 1. 시장 — 국장 / 미장\n\n### 국장 (6/18 마감)\n- **코스피 9,016~9,024(+1.7~1.8%, 국내 종합기사) / Yahoo 9,011.32(+1.66%) — 사상 첫 9,000 돌파, 4일째 사상최고.** 코스닥 **997.91(−3.30%, 1,000선 재이탈, 6일째 약세) — 디커플링 심화.**\n- **🔴 수급 = 신중 경보 유지**: 6/18 외인 **−약 6천억~9,972억 순매도(2거래일 연속)**, 개인 +5,100~7,800억 단독 지지, 기관 출처별 혼조(+1,566억~소폭 순매도). 외인 매도는 건설·금속(비반도체) 집중, 매수는 전기전자·반도체 = **종목 로테이션형 차익실현이되 메인 엔진(외인) 이탈 추세화.**\n- 섹터: **반도체 단독 독주**(삼성전기 +9.25%·SK하이닉스 +6.82%·LG이노텍 +4.89%) vs **나머지 일제 차익실현**(조선바스켓 한화오션 −6.01%·삼성중공업 −3.97%·HD현대중 −3.11%, 두산E −3.00%, SK이노 −4.95%, 현대차 −2.75%, 두산로보 −3.11%).\n\n| 국내 보유 | 티커 | 현재가 | 당일 | 원가대비 |\n|---|---|---|---|---|\n| 삼성전자 | 005930.KS | 353,500 | +2.02% | **+34.2%** |\n| LG전자 | 066570.KS | 228,500 | −2.56% | **+46.9%** |\n| 두산로보틱스 | 454910.KS | 102,900 | −3.11% | +2.9% |\n| 현대차 | 005380.KS | 601,000 | −2.59% | −4.6% |\n| NAVER | 035420.KS | 237,000 | −2.46% | −5.4% |\n\n### 미장 (6/17 종가 — FOMC 반응 반영)\n- **S&P500 7,420.10(−1.21%) · 나스닥 26,021.66(−1.34%) · 다우 51,492.55(−0.98%) · 필반(SOX) 13,477.07(+1.38%).** **매파 FOMC로 금리민감 메가캡 직격(MSFT −3.79%·GOOGL −2.53%·ORCL −2.55%) but 반도체는 전일 폭락 되돌림으로 역행 반등.**\n- **🔴 META −5.44%**는 FOMC가 아닌 종목 고유 악재(AI 임원 이탈+규제 패소)가 주범. 2년물 4.216%·10년물 4.499% 급등.\n\n| 미국 보유 | 현재가($) | 당일 | 원가대비($) |\n|---|---|---|---|\n| NVDA | 204.65 | −1.33% | +2.6% |\n| META | 567.58 | −5.44% | **−10.5%** |\n| VOO | 681.41 | −1.21% | +5.6% |\n| MSFT | 378.91 | −3.79% | −7.6% |\n| AAPL | 295.95 | −1.10% | **+15.1%** |\n| GOOGL | 363.79 | −2.53% | −6.2% |\n| TSLA | 396.38 | −2.05% | −6.2% |\n| ORCL | 183.53 | −2.55% | **−20.9%** |\n| ANET | 164.93 | −1.83% | +1.8% |\n| MU | 1,043.19 | **+2.20%** | **+39.3%** |\n| AVGO | 392.90 | **+4.30%** | −6.7% |\n\n---\n\n## 2. 섹터 — 반도체AI / 전력·피지컬 / 빅테크\n\n### 반도체·AI인프라 (MU 6/24 실적 D-6)\n- **MU 플레이북**: 회사 가이드 매출 $33.5B·EPS $19.15인데 **Street 컨센이 더 높음**($34.4~35B·$19.7~20.25) = beat 기대 내재, HBM \"2026 sold out\". 목표가 **빠르게 상향 중**(mean $850~891, Susquehanna $1,750·UBS $1,625·MS $1,050, 골드만만 ~$400) → \"주가 $1,043 > 목표\"는 정적 괴리가 아닌 **리프라이싱**. 포워드 PER 한자릿수~10배 = AI 반도체 중 밸류 최저축. **PM안(절반 차익+39%·절반 베팅) = 인라인 리스크 헤지로 합리.**\n- **삼성전자**: Rubin용 **HBM4 최종 qual 통과 + AMD MI400 주공급사 지명**(11.7Gb/s), '26 HBM 점유율 30% 회복 전망 → SK 독주에 균열, 3사 동시 수혜. NVDA $25B 채권($85B 주문)·Blackwell 완판·Rubin 2H.\n- **AVGO**: 6/3 Q3 AI 가이던스($16B vs 위스퍼 $17.2B)는 **눈높이 문제(ASIC 수요 둔화 아님)**, 6/4 8개+ 하우스 목표 상향(JPM $580·Jefferies $550·Goldman $525). 평단 아래 = 물타기 후보 sell-side 뒷받침.\n- **⚠️ 한국 반도체 과열**: 삼성전기 PER ~103배(5일째 급등·투자경고[미확인])·SK하이닉스 목표 +50% 초과 = **추격금지 정면 대상.** SK하이닉스 ADR SEC 클리어런스 6/22주, 8월 상장(조달 $9.6~14.4B 오버행).\n\n### 전력·인프라·피지컬AI (대미투자법 6/18 시행)\n- **대미투자 특별법 발동·KUIC(법정자본 2조) 출범** — $3,500억(에너지·AI·반도체 $2,000억+조선 $1,500억). **1호 프로젝트(루이지애나 LNG 유력 vs 신규 원전 병행) 7월 가닥** → 원전·조선·방산 **\"기대 소멸 후 차익실현\"**(재료 이연이지 소멸 아님).\n- **🟢 GEV +6.77%($1,048) = 워치 최강 펀더멘털**: Bernstein 신규 매수개시(Outperform $1,206), 1Q 수주 +71%·백로그 $163B. AI 전력 3종(가스터빈·원전·전력망) \"미국판 두산E\". 단 Jefferies는 $1,350→$1,210 하향(Buy 유지) = 밸류 부담 양 하우스 공통 인지. **소액 소수점 검토 적격(눌림 분할).**\n- 두산E 100,100(PER ~203배 모멘텀, X-energy SMR 16기, 목표 레인지 122k~165k 분산). 현대차 보스턴다이내믹스 SoftBank 풋옵션 **이달말 만기**(나스닥 상장 압박, KB 120만). TSLA Optimus 7월말~8월 양산.\n\n### 빅테크·플랫폼 (FOMC 매파 직격)\n- **META \"구조훼손 vs 노이즈\"**: 인재 이탈(Smith·앞서 LeCun 등 패턴)=약한 구조적 경고, Section 230 균열=꼬리리스크 확대이나 **분기 EPS 규모 아님**. 광고 엔진 무손상(노출 +19%·단가 +12%), **Forward P/E 19.4x = 매그7 최저**(시장이 'AI 패배자'로 가격책정). **결론=단기~약한 노이즈, 7/29 Q2 실적이 re-rating 전제.** JPM 유일 신중($725).\n- **MSFT** 상방 최대(+48.2%, Azure 무한 tailwind), **GOOGL**(+19%, Cloud·Gemini 견조, 반독점 노이즈), **AAPL**(+15% 평가익, 금리방어 입증·목표 근접 → **부분 트림 1순위**), **ORCL** 최대손실(−20.9%)이나 RPO 백로그 생존 = **패닉셀 금지**(OpenAI 47%·$300B 집중은 모니터링).\n\n---\n\n## 3. 매크로 데스크\n\n- **🔑 FOMC 6/18 = 🔴 매파 확정**: 동결(3.50~3.75%, 12-0), 점도표 2026 중앙값 **3.4%→3.8%**(9/18 인상), 워시 본인 dot 거부·성명 130단어·easing bias 삭제·코어 PCE 2.7%→3.3%. **2년물 +16bp(4.216%)·10년물 4.499%·DXY 상승 → META/AVGO 3차 보류.** SOX +1.38% 역행은 ASML·인텔 +4% AI 자체 모멘텀(매크로 매파 상쇄 아님).\n- **환율**: USD/KRW **1,520~1,521(원화 약세 고착)** — FOMC 매파 → 달러 강세 → 외인 환차손 압력↑. 단 미국분 원화환산은 +.\n- **유가·이란**: 브렌트 **$78.96(−5%, 3월來 최저)** — 이란 공급복귀·CPI 에너지 디스인플레 호재. 이란 휴전 MOU **6/19 스위스 서명 예정**(서명 전 = 결렬 시 유가 급반등 리스크).\n- **6/19 美 준틴스 전체 휴장**(유동성 공백) — 동시휴장 룰7(신규 진입 보류). 다음 CPI/PPI는 7월 중순(2주 내 없음). BOJ 1.0%·USD/JPY 160 고착(엔캐리 잔존). 한은 금통위 **7/16**(점도표 없음).\n\n---\n\n## 4. 리서치 피드 (경제사냥꾼 — 신규 11건 전량 자막 확보)\n\n> web_embedded 폴백으로 봇차단 없이 6/18분 2건 + 6/17분 9건 = **11건 전량 ko자막 확보.** 전 수치 외신·기관 교차검증. 트랙레코드 **이번 회차 매우 우수**(FOMC 전항목 적중).\n\n| 영상(신규) | 핵심 주장 | 분류 |\n|---|---|---|\n| **6/18 \"오늘 투자 포인트\"** | FOMC 동결·점도표 3.4→3.8·9/18 인상·워시 dot 미기재·성명 130단어 / 메타 −5%·나스닥 −1.3% vs 필반 +1%(반도체 피신) / 브렌트 $78·60일 무료통항 | **[검증]** 전항목(CNBC/NPR). v17 예고 적중 |\n| **6/18 \"현대차 폭락 진짜 이유\"** ★보유 | +150%후 6월 −18%(78만→60만대) / 보스턴다이나믹스 50~167조 미확정·**삼성 지분인수 보도(SB 10%, 이달말 풋옵션)** / \"첫 가격표가 분기점, 추격말라\" | **[검증]** 삼성-BD 보도(TheBell 6/16)·추격금지 합치 |\n| **6/17 \"신현송 한은총재\"** ★국장 | **7/16 금통위 2.50→2.75% 인상 전망**·시장 연내 2회 / 종전에도 물가 하반기 3% / \"인하기→인상기 판 전환, 외인복귀+환율1500하회=코리아디스카운트 해소\" | **[검증]** 7/16·물가(코리아타임스). 인상기 = 새 변수 |\n| **6/17 \"FAB10/PEPTEN\"** | M7→펩텐(+스페이스X·오픈AI·앤스로픽, 2개 비상장) / **상위10=S&P 약40%**(닷컴41·니프티40 다음) / \"쏠림 온도계\" | **[검증]** 집중도(P&I). 정훈 M7 다수보유 동반변동 유의 |\n| **6/17 \"NVDA $25B채권→삼전+닉스\"** ★보유·워치 | $25B·주문 $85B·AA·루빈 HBM4 70% 하이닉스 / \"하이닉스 영익 100조\" | **[검증]**+🔧 영익 **실제 250조**(순현금 100조 혼동 정정) |\n| **6/17 \"SK하이닉스 뉴스 3가지\"**(12.1만뷰) ★워치 | 인디애나 보조금 **$458M·양산 2028 하반기** / 주주환원 최대 100조 보도·영익 250조 | **[검증]**(NIST/Futu). 워치 최강 모멘텀 |\n| **6/17 \"美+日 100조 SMR→원전주\"** ★워치 | 일본 대미 100조 SMR·GE버노바+히타치 $40B / 진짜 수혜=**두산에너빌리티**(NuScale 공급망) / 대미투자공사 6/18 출범 | **[검증]**+🔧 자막 **\"두산로보틸리티\"=오류 → 두산에너빌리티** |\n| **6/17 \"스페이스X 매수 타이밍\"** ★워치 | 목표가 **$63~$190**(CFRA $115·모닝스타 $63·오펜하이머 $190) / 6월말 지수편입+8월~연말 락업 / \"좋은 기업≠좋은 가격\" | **[검증]** v17 \"$330 과장\" 사라짐·균형 개선(트랙레코드 호전) |\n| **6/17 \"ETF 수익률 비밀\"** | 단일종목 2배 레버리지 사고·괴리율 90% / **분산형(코스피200·S&P500=정훈 VOO)=안전 도구** | [검증·방향] VOO 우호 |\n| **6/17 \"한화 김승연 KAI 콕\"** | 한화 KAI 9.04% 2대주주·경영참여(한국판 머스크) | **[검증]**(뉴스1) 방산테마·한화에어로 간접 |\n| **6/17 \"미국 뉴스 3가지\"** | 마이크 버리 SpaceX 매도시각(적자 $49억)·한국개미 1.23조 순매수 | [미확인-방향] SpaceX 양면 |\n\n> **채널 오늘 시각**: \"FOMC = 인하냐 아닌 **인상공포 확대냐의 자리**\"(적중). \"외인복귀+환율1500하회+반도체실적 = 코리아디스카운트 해소\"(단 6/17~18 외인 순매도 전환은 촬영 후 발생, 채널 미반영). 신규 테마 = **①한은 7/16 인상 ②SMR=두산에너빌리티 ③방산=한화-KAI ④집중도(상위10=S&P40%)**. 누적 로그 `docs/research/hunter_log.md` 갱신 완료.\n\n---\n\n## 5. 리스크 데스크 (신중/bear)\n\n- **🚦 트리거**: 안전핀 7,500까지 **+20.2% 여유**(현 9,015) — \"안심이 아니라 4일 +10% 급등으로 키만 높아진 것\". 2차 8,000도 +12.7% 상회, **매수존 전부 위 이탈**(NAVER 237k vs 225~235k·삼성 353k vs 295~305k(+16%)). 🔴발동: 두산E 100,100(10만 재돌파, 워치라 보유영향 0·추격금지).\n- **🚨 고강도 경보 2건**: ①**추격매수 금지(룰3) — 현금 624,771원 동결.** 코스피 4일 폭등·삼성전기 +9.25%·SK하이닉스 +6.82%·\"매파에도 끄떡없네\" 도취 헤드라인 = 정확히 FOMO 트리거. ②**FOMC 매파 → 3차 트랜치 전면 보류 확정**(베이킹 STEP2 🔴). 비둘기 시나리오(예약 22.5만) 무효.\n- **🔴 집중도(사실상 단일 포지션)**: AI 메모리/HBM 6중 쏠림(삼성·NVDA·MU·AVGO·SK하이닉스·삼성전기) + 미국 11종목 단일 원/달러 환노출. 6/16 브로드컴 한 뉴스에 동반 급락 + 6/17 META·메가캡 동반 약세가 증명. **MU 6/24 절반 차익 = 집중도 완화의 유일한 능동 수단.**\n- **bear 핵심**: 강세론 최약 고리 = **\"엔진(외인) 이탈 + 미 메가캡 균열 + 단일 테마 과집중\"의 3중 결합.** 외인 2거래일 연속 순매도(추세화)로 코스피 9,000을 개인이 떠받치는 구조(개인 주도장 = 후반부 신호) + 매파 FOMC로 고밸류 AI주 되돌림 압력 + 6/19 준틴스 휴장·이란 서명·엔캐리 잔존 클러스터. **신고가 환호가 곧 가장 위험한 순간 — 오늘 폭등은 현금 62만원을 지킬 이유.**\n\n---\n\n## 6. 강세 vs 신중 디베이트\n\n**강세(bull)**: 코스피 사상 첫 9,000·4일째 신고가, 골드만 12,000 추가 상향(2026 EPS +300%·2028 삼성+하이닉스 합산 영익 1,000조). 매파 FOMC에도 반도체 순환매 복귀(SOX +1.38%·MU·AVGO 반등), 삼성 HBM4 Rubin qual 통과+AMD 지명 = 3사 동시 수혜. NVDA $25B 채권($85B 주문)·하이닉스 환원 100조·인디애나 $458M = AI capex 환류 견고. 컨센 대부분 +30~48% 상방(NVDA·META·MSFT·AVGO·ORCL·TMUS). MU +39%·AAPL +15%·삼성 +34%·LG전자 +47% 코어 수익 견조. 유가 $78·종전 6/19 서명 = 리스크프리미엄 제거.\n\n**신중(bear)**: 신고가 엔진이 외인→개인으로 교체(6/17~18 외인 2일 연속 순매도) = 메인 엔진 추세적 이탈. 매파 FOMC(점도표 인상 전환·2년물+DXY 상승)로 금리인하 트레이드 사망, 고밸류 AI주부터 되돌림 압력. 포트는 AI 메모리 단일 테마+단일 환노출 과집중(한 뉴스에 동반 급락 증명). 한은 7/16 인상까지 가세하면 국내 긴축 부담. 6/19 준틴스 휴장·이란 서명·엔캐리 3중 클러스터가 4일 +10% 급등의 되돌림 방아쇠. META 고유 악재(인재·소송) + 모든 매수존 위 이탈.\n\n**PM 저울질**: 코어 강세 논지(AI 슈퍼사이클)는 유지하되, **외인 2일 연속 이탈 + 매파 FOMC + 단일 테마 과집중 = 단기 신중 명백 우위.** 추격 금지·현금 전액 보존·이벤트 확인이 정석. (무게는 PM 종합 §7.)\n\n---\n\n## 7. PM 종합 (최종)\n\n### 🎯 오늘의 한 줄 결론\n**코스피 첫 9,000·4일째 신고가지만 엔진(외인)이 이틀째 빠지고 FOMC는 매파 — 3차 트랜치 보류 확정, 현금 62만원 전액 보존. 추격 금지가 오늘의 정답. 반도체 순환매는 우호적이나 매수존 전부 위 이탈 = 관망.**\n\n### 보유 16종목\n\n| 종목 | 현재가 | 원가대비 | 목표가(컨센) | 매수존 | ⭐ | 한줄 |\n|---|---|---|---|---|---|---|\n| 삼성전자 | 353,500 | +34.2% | 48~53만(KB/미래) | 295~305k(이탈) | ⭐⭐⭐⭐ | HBM4 Rubin qual+AMD 지명, 코어 |\n| LG전자 | 228,500 | +46.9% | 컨센 초과(홀딩) | 홀딩 | ⭐⭐⭐⭐ | 손절선 없음, 1주 분할불가 |\n| 두산로보틱스 | 102,900 | +2.9% | 극단분산 | 관망 | ⭐⭐ | 적자·PSR219배 모멘텀, 갭업차익 |\n| 현대차 | 601,000 | −4.6% | 60만(공격 80만) | 관망 | ⭐⭐⭐ | BD 첫 가격표(이달말 풋옵션)가 분기점 |\n| NAVER | 237,000 | −5.4% | ~30만 | 225~235k(근접) | ⭐⭐ | 정리후보, 두나무 편입(9월)까지 보유 |\n| NVDA | $204.65 | +2.6% | $298.93(+46%) | 눌림 | ⭐⭐⭐⭐⭐ | 채권호재·Rubin, 비중관리 |\n| META | $567.58 | −10.5% | $827.32(+46%) | 실적확인 | ⭐⭐⭐⭐ | 고유악재(노이즈), 7/29 실적 전 보류 |\n| VOO | $681.41 | +5.6% | — | 적립 | ⭐⭐⭐⭐ | 분산형 코어(채널도 '안전' 분류) |\n| MSFT | $378.91 | −7.6% | $561.39(+48%) | 눌림 | ⭐⭐⭐⭐ | 상방 최대, 금리민감 조정 |\n| AAPL | $295.95 | +15.1% | $312.72(+6%) | 목표근접 | ⭐⭐⭐ | 금리방어 입증, **부분 트림 1순위** |\n| GOOGL | $363.79 | −6.2% | $432.83(+19%) | 눌림 | ⭐⭐⭐⭐ | Cloud·Gemini 견조 |\n| TSLA | $396.38 | −6.2% | $420.55(+6%) | 관망 | ⭐⭐⭐ | Optimus 7~8월, 상방 제한 |\n| ORCL | $183.53 | −20.9% | $252.64(+38%) | 눌림 | ⭐⭐⭐ | 최대손실, RPO 생존=패닉셀 금지 |\n| ANET | $164.93 | +1.8% | $189.13(+15%) | 홀딩 | ⭐⭐⭐⭐ | AI 네트워크 |\n| MU | $1,043.19 | +39.3% | $879(−16%)→상향중 | **6/24 실적** | ⭐⭐⭐⭐ | 컨센 상회기대·sold out, 절반 차익 |\n| AVGO | $392.90 | −6.7% | $522.06(+33%) | 조정주 | ⭐⭐⭐ | 가이던스=눈높이 문제, 평단아래 물타기후보 |\n\n> 컨센 ±30% 괴리(상방): NVDA·META·MSFT·AVGO·ORCL·TMUS = 🟢. MU는 목표 급상향 진행형 → \"주가>목표\"는 리프라이싱(6/24 실적 후 절반 차익).\n\n### 워치리스트 (활성)\n| 종목 | 현재가 | 비고 |\n|---|---|---|\n| **GE Vernova** | $1,048.86 | 🟢 **Bernstein 매수개시 $1,206**·수주+71%. 워치 유일 매수검토(소액 소수점·눌림 분할) |\n| 두산에너빌리티 | 100,100 | 10만 재돌파, **추격금지**. SMR 진짜수혜(NuScale 공급망). 93~95k 눌림 1주 소액만 |\n| SK하이닉스 | 2,693,000 | +6.82% 사상 첫 260만, ADR 8월·목표 +50% 초과 = 추격 부적합 |\n| 삼성전기 | 2,220,000 | +9.25% 5일째·PER 103배 = 과열 최선두, 추격금지 |\n| LG이노텍 | 1,309,000 | +4.89% FC-BGA, 선행 41배 |\n| 원익IPS/테스 | 164,700/175,900 | 코스닥 약세 역행 강세, 소부장 온기 |\n| SK이노 | 103,600 | −4.95% SMR 되돌림(테라파워 지분 한수원 매각=간접테마) |\n| 한화에어로/조선3 | 1,198,000/— | 대미투자 차익실현, 한화-KAI 방산 |\n| STM/TMUS/SPCX | $73.36/$181.31/$191.82 | STM 컨센 하향(−12%)=보류 / SPCX 락업 8월(6/30 미확인) |\n\n### 제안 액션\n- **관망 디폴트** — 매수존 전부 위 이탈 + 외인 2일 연속 매도 + 매파 FOMC. 신규 진입 보류, **현금 624,771원 전액 보존.**\n- **🔴 3차 트랜치 = 매파 확정 → 전면 보류**(베이킹 룰). 오늘 저녁 폰창(17:30~20:50)에 **\"예약 미입력\" 확인 + 보유분 투매 금지**(META·AVGO·MSFT·GOOGL·ORCL은 흔들림이지 위험 아님). 안전핀 7,500 거리 재확인(+20%, 무관).\n- **6/24 MU 실적(야간) 절반 차익 = 6/23 저녁 사전 베이킹 필요**(폰 미가용). +39% 고밸류·집중도 완화·인라인 리스크 헤지로 정합.\n- **두산E·SK하이닉스·삼성전기 추격 금지** — 알림만, 되돌림 대기. GEV만 워치 중 소액 검토(눌림 분할).\n- **외인 6/19~다음 거래일 3일째 순매도 지속 여부 = 강세 논지 최종 분수령**(3일 연속이면 강세 비중 하향).\n\n### 현금 배분 플랜 (624,771원, 3분할 미집행)\n- **1차 ~12.5만**: NAVER 225~235k(현 237k, 근접) 또는 삼성 295~305k(현 353k, 멀음) **눌림 대기.**\n- **2차 ~20만**: 코스피 8,000 하회 + 이벤트 악재 동반 시(현 9,015, 미도달).\n- **3차 ~22.5만**: 🔴 **FOMC 매파로 보류 확정.** 비둘기 전환·META 7/29 실적 확인·외인 복귀 중 하나 전까지 동결.\n- ⚠️ 두산E 9만 초중반 되돌림 1주(~10만)·GEV 소액은 트랜치 본예산과 분리, 편입 시 승인 필요.\n\n### 지켜볼 것 (2주 캘린더)\n| 날짜(KST) | 이벤트 | 폰 |\n|---|---|---|\n| **6/18(목) 저녁** | 폰창: 3차 \"예약 미입력\" 확인·투매 금지·외인 종가 수급 | ✅ |\n| **6/19(금)** | 美 준틴스 전체 휴장(유동성 공백) / 이란 스위스 서명 | ⚠️야간 |\n| 6/22(월) | 美 재개 / SK하이닉스 ADR SEC 클리어런스 주 | ❌야간 |\n| **6/23(화) 저녁** | **MU 절반 차익 사전 베이킹**(6/24 야간 실적용) | ✅ |\n| **6/24(수)** | **MU 실적**(절반 차익) | ❌야간 |\n| 6/26(금) | SPCX MSCI 편입 메커닉(지수 수급) | — |\n| **7/16(목)** | **한은 금통위(2.50→2.75% 인상 전망)** | ✅ |\n| 7/22~30 | 美 실적 시즌(TSLA·GEV·TMUS 7/22, GOOGL 7/23, META·MSFT 7/29) | — |\n\n---\n\n## 8. 오늘의 이슈 선택지\n1. **6/24 MU 실적 베이킹 매뉴얼** — 절반 차익 vs 전량 홀딩 시나리오, 비트/인라인/미스별 주가 반응(±9.5% IV)과 6/23 저녁 사전 예약 구체화. 집중도 완화 관점.\n2. **외인 2일 연속 순매도 = 추세전환?** — 6/19~다음 거래일 3일째 판별법, 강세 논지 하향 임계치, 한은 7/16 인상이 외인 수급에 미칠 영향.\n3. **META 고유 악재 = 매수 기회 vs 회피?** — 인재 이탈·Section 230 소송의 구조성 재점검, Forward P/E 19.4x 저가매력 vs 7/29 실적 확인 후 진입 판단.\n4. **GE Vernova 워치→소액 편입 결정** — Bernstein 매수개시·수주+71% vs 밸류 부담(Jefferies 하향), \"미국판 두산E\" 소수점 진입 타이밍.\n\n---\n\n## STATE SNAPSHOT\n```\n[STATE SNAPSHOT v18 2026-06-18]\n현금: 624,771원 (트랜치 1차/2차/3차 전부 미집행 — 3차는 FOMC 매파로 보류 확정)\n보유변동: 없음 (16종목 유지)\n시세기준: KR=6/18 마감(코스피 종가 9,063.84 +2.25%, 첫 9,000 마감·4일째 사상최고 / ⚠️본문의 9,016·삼성 353,500은 장중치 → 종가 9,063.84·삼성 362,500 +4.62%) / US=6/17 종가(FOMC 반응) / USD/KRW 외환종가 1,527.1\n총자산: 8,398,313원 · 주식손익 +221,183(환차익 미반영) / 환차익 반영 추정 +472,616 · 전일(6/13)대비 +45,167 (※장중 시세 기준, 종가 반영 시 삼성 +4.62%로 상향)\n오늘 할 일: 3차 트랜치 룰상 보류(매파)이나 외인 순매수 복귀로 공격안 병행 검토(AVGO 물타기·MSFT·GEV 소액) / MU 6/24 절반차익 베이킹 / 추격금지(눌림 대기)\nFOMC 판정: 🔴 매파(Hawkish Hold) — 동결 3.50~3.75%(12-0), 점도표 2026 3.4→3.8%(9/18 인상), 워시 dot 거부·성명 130단어·easing bias 삭제, 2년물 4.216%·10년물 4.499%·DXY 상승\n수급경보: 🟢 [정정] 외인 6/18 종가 +1.28조~1.44조 순매수 복귀(본문 \"2일 연속 순매도\"는 장중치 오류) — 6/17 -9,997억은 1일 차익, 메인 엔진 재확인. 신중 경보 해제, 6/22 외인 지속 여부 확인\n워치리스트(활성): GE Vernova(매수검토)·두산에너빌리티(10만)·SK하이닉스(260만)·삼성전기(과열)·LG이노텍·원익IPS·테스·SK이노·한화에어로·조선3·STM·TMUS·SPCX\n대기 트리거:\n  ① 3차 트랜치 = 🔴매파로 보류 확정(비둘기 전환·META 7/29 실적·외인 복귀 중 하나까지 동결)\n  ② 6/24 MU 실적 → 절반 차익(6/23 저녁 베이킹 필요, +39% 고평가·집중도 완화)\n  ③ 6/19 준틴스 휴장+이란 스위스 서명 / 6/22 SK하이닉스 ADR SEC 주\n  ④ 외인 3일째 순매도 지속 여부 = 강세 논지 최종 분수령\n  ⑤ 한은 7/16 금통위 2.50→2.75% 인상 전망(신현송 매파)\n영구교정(신규):\n  - FOMC 6/18 = 매파 확정(점도표 2026 3.4→3.8%, 9/18 인상, 워시 본인 dot 거부, 성명 130단어, 코어PCE 2.7→3.3%)\n  - 코스피 6/18 사상 첫 9,000 마감(종가 9,063.84 +2.25%, 4일째 사상최고) / 코스닥 1,000.93(-3.01%) 디커플링 / 삼성전자 종가 362,500(+4.62%)·SK하이닉스 2,685,000(+6.51%)\n  - 🟢[정정] 외인 6/18 종가 +1.28조~1.44조 순매수 복귀(장중 순매도→오후 반전) — \"2일 연속 순매도\"는 장중치 오류, 메인 엔진 재확인\n  - META -5.44% = FOMC 아닌 종목 고유악재(AI임원 Smith 이탈+Section 230 소송 KGM $6M·MDL3047), 논지 무손상=노이즈\n  - 삼성 HBM4 Rubin 최종 qual 통과+AMD MI400 주공급사 지명(11.7Gb/s), '26 HBM 점유율 30% 회복 전망\n  - 경제사냥꾼 정정: 하이닉스 영업이익 \"100조\"→실제 컨센 250조(순현금과 혼동) / 자막 \"두산로보틸리티\"→두산에너빌리티 / \"김승현\"→김승연\n  - GEV Bernstein 매수개시 $1,206(수주+71%·백로그 $163B), Jefferies $1,210 하향(Buy유지)\n  - 대미투자 특별법 6/18 시행·KUIC 출범, 1호 프로젝트(LNG vs 원전) 7월 이연\n  - SPCX 락업 = 8월 첫 20% 언락(기존 '6/30'은 미확인), 6/26 MSCI·7월초 나스닥100 편입 메커닉\n  - 한은 7/16 금통위 2.50→2.75% 인상 전망(신현송 \"물가 하반기 3%\"·연내 2회 프라이싱)\n리서치: 경제사냥꾼 신규 11건(6/18분 2+6/17분 9) 전량 자막확보, 트랙레코드 우수(FOMC 적중)\n다음 버전: v19\n```\n\n*투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "holdings_final_2026-06-18_v2_aggressive",
      "file": "docs/reports/holdings_final_2026-06-18_v2_aggressive.md",
      "title": "🔥 정훈 종목 최종 보고 v18-공격형 — 2026-06-18",
      "date": "2026-06-18",
      "version": 2,
      "kind": "보유확정",
      "preview": "어제 \"외인 이탈\"이 신중의 1번 근거였는데 — 종가 까보니 외인이 +1.3조 순매수로 되받았다(개인이 던진 걸 외인이 받음). 메인 엔진 재확인 = 코스피 강세 회복. 단 미국은 FOMC 매파라 옥석은 가린다. 오늘은 현금 깔고 앉는 날이 아니라, ",
      "content": "# 🔥 정훈 종목 최종 보고 v18-공격형 — 2026-06-18\n> KR=6/18 종가(코스피 첫 9,000 마감) / US=6/17 종가(FOMC 매파) / 환율 1,527원 · 투자 자문 아님\n> 🎯 모드: **신중 해제 → 선별 공격.** \"장기투자지만 때론 공격적으로.\"\n\n## 🏆 한 줄 프레임 — **외인이 돌아왔다**\n어제 \"외인 이탈\"이 신중의 1번 근거였는데 — **종가 까보니 외인이 +1.3조 순매수로 되받았다(개인이 던진 걸 외인이 받음).** 메인 엔진 재확인 = **코스피 강세 회복.** 단 미국은 FOMC 매파라 옥석은 가린다. **오늘은 현금 깔고 앉는 날이 아니라, 깊게 빠진 우량 코어를 줍는 날.** 💪 무지성 추격은 금지, **역발상 분할**로 공격.\n\n---\n\n# 📈 코스피 9,000 — 거품인가, 시작인가?\n```\n종가 9,063.84 (+2.25%, 사상 첫 9,000 마감·4일째 신고가) / 6/12 8,123 → +11.6% 4거래일\n🟢 강세: 외인 +1.3조 순매수 복귀(메인엔진 재확인) · 골드만 목표 12,000(EPS+300%·\n        삼성+하이닉스 2028 영업익 1,000조) · 하나 10,380·KB 10,500·노무라 11,000 줄상향\n🔴 신중: '기승전 반도체' 극단 쏠림(상승 100 vs 하락 810) · 코스닥 -3.0% 디커플링 ·\n        VKOSPI 80(변동성 경고) · 환율 1,527 원화약세 · 비반도체(현대차·NAVER·LG전자) 역행\n판정: 강세 우위(외인 복귀가 결정타) — 단 '반도체 단독 강세'라 종목 선별 필수.\n      안전핀 7,500까지 -17% 여유. 다음 관문 = 6/22 외인 지속 + 6/24 MU·7/29 삼성 실적 검증.\n```\n\n---\n\n# 🔬 딥다이브 3종 (정훈 요청)\n\n## 🚗 테슬라 (TSLA) — 보유, $396.38 / −6.2% / ⭐⭐⭐\n```\n밸류: 시총 $1.49T·Fwd PER 184~215x = 자동차 아닌 '로보택시+옵티머스' 옵션값\n컨센: 평균 $402~421(여력 +1~6% = 사실상 중립) / 레인지 $123(Wells)~$600(Ives) 극단분열\n촉매: ①로보택시 오스틴 전역 무인확대 BUT 실차 ~20대(웨이모 3,000대·주 50만탑승 압도)\n      ②옵티머스 7월말~8월 양산·연말 첫 상업판매(초기 ~$3만, $2만은 장기목표)\n      ③Q2 인도 골드만 42만 상향 / 머스크 의결권 20%·SpaceX 합병설(Ives 80%)\n액션: 홀딩. 지금 물타기 X(여력 0·고점 되돌림). 옵티머스 양산 '실제 뉴스' 확인 후\n      $360~375 분할. 공격시 양산확인 즉시 $360~390 소량, 갭상승 당일은 회피.\n```\n\n## 🛰️ 스페이스X (SPCX) — 워치, $191.82 / ⭐⭐\n```\n밸류: 시총 $2.5T·PSR 94x(IPO밸류)~140x(현시총) = 트릴리언클럽 유일 극단치\n컨센: $63(모닝스타 Sell)~$310 극단분산. 오펜하이머 $190 '이미 도달' = 펀더기준 고평가\n촉매: 패시브 편입(FTSE 6/26·MSCI 6/29·나스닥100 ~7월초, $10~27조 강제매수) ↑\n      ⚠️락업 = 8월 첫 20% 언락('6/30설'은 오류 재확인) ↓ / xAI 적자 연 $4.9조\n버리(빅쇼트): 무포지션(\"IV 너무 비쌈, mid-$200 안정되면 숏 검토\") = 양날\n액션: 추격금지 정면대상(상장 7일차 급등). 6/26~7월 매수이벤트 vs 8월 락업 사이\n      변동성 극대 → 관망. IPO가 $135 되돌림 전 진입 보류.\n```\n\n## 🧠 팔란티어 (PLTR) — 신규 워치 편입, $130.63 / ⭐⭐⭐\n```\n밸류: 시총 $313B·PSR 60~67x(S&P 최고축)·Fwd PER 83~92x. '$156' 기사는 stale(고점 -16%)\n펀더: Q1 매출 +85%·미국 +104%·미상업 +133% / Rule of 40 = 145% / FCF $4.2조 흑자\n      → 적자 테마주 아님 = '준코어'(두산로보보다 한 수 위, NVDA 코어보단 아래)\n컨센: 평균 $185~200(+42~53%)·Ives $230 vs MS 신중 Equal-weight $205. Karp CEO 매도($1.2B)\n⚠️ FOMC 베타 매우 높음 → 매파엔 고밸류 SW가 가장 먼저·크게 디레이팅\n액션: 추격금지. $110~120 눌림 분할만(2027E 매출 ~32x 회귀존). 매파 소화 확인 후 1차.\n```\n> **PLTR vs SPCX = 질이 다르다**: PLTR은 흑자·FCF $4조·Rule of 40 145% '진짜 실적주'(눌림 줍기 가치), SPCX는 적자·DCF 정당화 불가 '순수 수급주'(진입 보류). **데이터 우선 원칙상 PLTR이 코어에 가깝다.**\n\n---\n\n# 1️⃣ 보유 16종목 (풀 표 — 종가 반영)\n> ⭐: ⭐⭐⭐⭐⭐ 최선호 / ⭐⭐⭐⭐ 코어강세 / ⭐⭐⭐ 홀딩 / ⭐⭐ 정리·모멘텀주의\n\n| 종목 | 현재가 | 당일 | 수익률 | 목표 | 여력 | 매수존 | 매도/트림 | ⭐ | 액션 |\n|---|---|---|---|---|---|---|---|---|---|\n| **NVDA** | $204.65 | −1.33% | +2.6% | $299 | +46% | $190대 눌림 | 비중관리 | ⭐⭐⭐⭐⭐ | 채권·Rubin, 홀딩 |\n| **AVGO** | $392.90 | **+4.30%** | −6.7% | $522 | **+33%** | **평단 $421↓ 지금** | 홀딩 | ⭐⭐⭐⭐ | **🔥공격 물타기 1순위** |\n| **MSFT** | $378.91 | −3.79% | −7.6% | $561 | **+48%** | **$360~378 지금** | 홀딩 | ⭐⭐⭐⭐ | **🔥공격 2순위(최대상방)** |\n| **MU** | $1,043 | +2.20% | **+39.3%** | $879→상향중 | 리프라이싱 | 6/24 후 | **절반차익(6/24)** | ⭐⭐⭐⭐ | sold out, 차익 베이킹 |\n| **META** | $567.58 | −5.44% | **−10.5%** | $827 | +46% | 7/29 실적후 | 홀딩·투매금지 | ⭐⭐⭐⭐ | 고유악재=노이즈, 보류 |\n| **GOOGL** | $363.79 | −2.53% | −6.2% | $433 | +19% | $350대 눌림 | 홀딩 | ⭐⭐⭐⭐ | Cloud·Gemini 견조 |\n| **ANET** | $164.93 | −1.83% | +1.8% | $189 | +15% | 홀딩 | 홀딩 | ⭐⭐⭐⭐ | AI 네트워크 |\n| **삼성전자** | 362,500원 | **+4.62%** | **+37.8%** | 480,000~530,000원 | +32~46% | 295,000~305,000원 | 코어홀딩 | ⭐⭐⭐⭐ | HBM4 qual통과+외인 최대매수 |\n| **LG전자** | 228,500원 | −2.56% | **+47.2%** | 컨센 초과 | — | 210,000~220,000원 | 펀더훼손시만 | ⭐⭐⭐⭐ | 손절선X·최대수익 |\n| **VOO** | $681.41 | −1.21% | +5.6% | 인덱스 | — | 상시 적립 | — | ⭐⭐⭐⭐ | 분산 코어 |\n| **AAPL** | $295.95 | −1.10% | **+15.1%** | $313 | +6% | 신규X | **부분트림 1순위** | ⭐⭐⭐ | 금리방어 입증·목표근접 |\n| **TSLA** | $396.38 | −2.05% | −6.2% | $421 | +6% | $360~375 | 홀딩 | ⭐⭐⭐ | 옵티머스 양산 대기 |\n| **ORCL** | $183.53 | −2.55% | **−20.9%** | $253 | +38% | 눌림(신규보류) | **패닉셀금지** | ⭐⭐⭐ | RPO 생존, 버텨 |\n| **현대차** | 601,000원 | −2.75% | −4.6% | 600,000(공격 800,000) | +33% | 580,000~600,000원 | 800,000원 트림 | ⭐⭐⭐ | BD 첫 가격표(이달말 풋옵션) |\n| **두산로보** | 102,700원 | −3.30% | +2.7% | 극단분산 | — | 관망 | 갭업차익 | ⭐⭐ | 적자·PSR219배 모멘텀 |\n| **NAVER** | 235,000원 | −3.49% | −6.2% | 약 300,000원 | +28% | 225,000~235,000원 | 반등시 정리 | ⭐⭐ | 랠리 소외·정리후보 |\n\n### 🔍 핵심 콕\n```\n🔥 AVGO — 공격 물타기 1순위\n$392.90 / 평단 $421 아래 / 컨센 $522(+33%) / 6/17 +4.30% 반등 시작\n가이던스 미스=눈높이 문제(ASIC 수요 멀쩡), 6/4 8개 하우스 목표상향(JPM $580·Goldman $525)\n→ 평단 낮추기 + 회복 초입 = '공포에 사라' 역발상 분할의 정석. 오늘 소수점 1차.\n```\n```\n🔥 MSFT — 공격 2순위\n$378.91 / 컨센 $561(+48% = 보유 중 최대 상방) / 금리 매파에 눌린 우량 컴파운더\nAzure 무한 tailwind·AI런레이트 $37B → 매파發 조정이 저가 기회. 오늘 소수점 1차.\n```\n```\n🟡 MU — 절반차익(6/24 D-6, 6/23 저녁 베이킹)\n+39.3% / \"2026 sold out\"+컨센이 가이던스 상회 / 인라인이면 차익조정(AVGO 학습)\n→ 절반 차익(+39% 확정·집중도 완화) + 절반 베팅. 6/24 저녁 폰창 0.02주 시장가 예약.\n```\n```\n🟢 ORCL — 패닉셀 금지(최대손실 -20.9%)\n산 이유(RPO $638B) 살아있음. OpenAI 47%·$300B 집중 희석 깨지면 그때. 던지지 마.\n```\n\n---\n\n# 2️⃣ 워치리스트 (풀 표 — PLTR 신규)\n\n| 종목 | 현재가 | 당일 | 목표 | 여력 | 매수존 | ⭐ | 지금 살까 |\n|---|---|---|---|---|---|---|---|\n| **GE Vernova** | $1,048.86 | +6.77% | $1,206 | +15% | 눌림 분할 | ⭐⭐⭐⭐ | ✅**편입검토**·Bernstein개시·FOMC무관 호재 |\n| **팔란티어(PLTR)** | $130.63 | −1.78% | $185~200 | +42~53% | $110~120 | ⭐⭐⭐ | 🆕준코어·Rule40 145% but PSR 60x·눌림만 |\n| **SK하이닉스** | 2,685,000원 | +6.51% | 1,800,000원 | −33% | 추격❌ | ⭐⭐⭐ | 외인 최대매수처·HBM4 but 목표 +50%초과 |\n| **삼성전기** | (장중)+8.27% | — | 2,300,000~3,000,000원 | — | 1,600,000~1,750,000원 | ⭐⭐⭐ | 소부장 대장 but 과열·PER 103배 |\n| **두산에너빌리티** | 99,600원 | −3.49% | 143,000원 | +44% | 93,000~95,000원 | ⭐⭐⭐ | 10만 재이탈·SMR 진짜수혜·눌림 1주 |\n| **LG이노텍** | 1,283,000원 | +2.80% | FC-BGA | — | 증설 관찰 | ⭐⭐⭐ | 선행 41배 |\n| **원익IPS** | 163,200원 | +0.93% | 160,000~180,000원 | 근접 | 125,000~130,000원 | ⭐⭐ | 소부장 |\n| **테스** | 176,100원 | +3.96% | 160,000~170,000원 | 초과 | 130,000원 | ⭐⭐ | 목표 초과 |\n| **한화에어로** | 1,189,000원 | −2.86% | 대미방산 | — | 소화 관찰 | ⭐⭐⭐ | 차익실현·KAI 방산 |\n| **조선바스켓** | 한화오션 125,100·삼성중공업 27,700·HD현대중 684,000 | −3~6% | 대미조선 | — | 소화 관찰 | ⭐⭐ | 1호 7월이연·차익 |\n| **SK이노베이션** | 103,500원 | −5.05% | 테마 | 미확정 | 관망 | ⭐⭐ | SMR 간접테마 |\n| **STM** | $73.36 | −1.60% | $64 | −15% | 보류 | ⭐⭐ | ❌컨센 하향 |\n| **T-Mobile** | $181.31 | −1.65% | $261 | +44% | $165 조정시 | ⭐⭐⭐ | T-Sat 7/23 |\n| **SpaceX** | $191.82 | −4.95% | $63~310 | 분산 | 추격❌ | ⭐⭐ | 락업 8월·관망 |\n\n---\n\n# 3️⃣ 💰 현금 624,771원 — 분할·룰7 반영 (정훈 피드백 6/18 정정)\n\n> ⚠️ **정정 배경**: ①**룰7(美·아시아 동시휴장 6/18~19 전후 신규 진입 보류)** — 6/19 준틴스 휴장이라 오늘 시장가 매수는 휴장 갭 노출=룰 위반. ②외인 +1.3조는 **종가 막판 반전**(장중은 순매도)이라 기계적 매수 가능성 → 6/22 확인 필요. ③'목표가보다 낮다'만으론 매수 근거 안 됨 — **하락 원인 분리 필수**(§아래). → 당일 3종목 380,000원 동시 매수는 과함, **단계적 분할로 정정.**\n\n## 하락 원인 분리 (매수 후보 선별의 핵심)\n| 종목 | 왜 떨어졌나 | 성격 | 판정 |\n|---|---|---|---|\n| **AVGO** | 6/3 Q3 AI 가이던스 눈높이 미스 | 일시적(AI +143%·고객 견조·8하우스 상향·+4.3% 반등) | ✅유일 깨끗 |\n| **MSFT** | 6/17 FOMC 매파(금리민감) | 일시적이나 매파 헤드윈드 잔존 | △더 눌릴 수 |\n| **ORCL** | OpenAI 집중·희석 | 구조적 | ❌버티기만 |\n| **META** | 고유악재+매파 | 구조적 오버행(7/29까지) | ❌매수 X |\n| **GEV** | **+6.77% 상승**(안 떨어짐) | 추격 대상 | ❌눌림 대기 |\n\n## ✅ 단계적 분할안 (확인·분할·이유 보고 산다)\n```\n오늘(6/18 폰창): 시장가 매수 0. 지정가 알림만 →\n   AVGO $380 · MSFT $365 · 삼성 305,000 · NAVER 225,000 · PLTR $118 · 두산E 94,000\n6/22(월, 준틴스 후): 외인 순매수 '지속' 확인 시 → AVGO 1차 소액 ~70,000원(눌림만, 추격 X)\n6/24 MU 실적 후: 결과 보고 2차(AVGO 추가 or MSFT)\nGEV·PLTR: 눌림 대기(GEV +6.77% 추격금지 / PLTR 매파 베타 커서 $110~120)\n🛡️ Dry powder 대부분 유지 / 6/24 MU 절반차익(0.02주) 베이킹은 유효\n```\n> '공격적으로'는 맞되, **매파+휴장+막판반전**이 겹친 오늘은 **알림 깔고 6/22부터 확인하며 분할**이 진짜 공격(안 죽는 공격). AVGO 하나가 유일하게 '일시적 이유로 빠진 평단 아래' 후보.\n\n---\n\n# 4️⃣ 📅 일정 (2주)\n| 날짜 | 이벤트 | 액션 |\n|---|---|---|\n| **6/18 저녁** | 폰창 | 🅱️ AVGO·MSFT·GEV 소수점 1차 예약 |\n| 6/19 | 美 준틴스 휴장/이란 서명 | 거래공백 |\n| **6/22(월)** | **외인 순매수 지속 확인** | 지속=강세 굳힘 / 재이탈=경보 |\n| **6/23 저녁** | **MU 베이킹** | 절반차익 예약 셋업 |\n| **6/24** | **MU 실적** | **절반 차익** |\n| 6/26~7월초 | SPCX 패시브 편입 | 관망 |\n| **7/16** | **한은 2.50→2.75% 인상 전망** | 원화·외인 양면 |\n| 7/22~30 | 美 실적(TSLA 7/22·삼성·META·MSFT 7/29) | 골드만 전망 검증 |\n\n---\n\n# 🔥 오늘은 이걸 합시다 (결정형 — 단계 분할, 룰7 반영)\n```\n✅ 1. 오늘(6/18 폰창): 시장가 매수 0 + 지정가 알림만 세팅\n      AVGO $380 · MSFT $365 · 삼성 305,000 · NAVER 225,000 · PLTR $118 · 두산E 94,000\n✅ 2. 6/22(월): 외인 순매수 '지속' 확인 시 → AVGO 1차 ~70,000원(눌림만, 추격 X)\n✅ 3. 6/23 저녁: MU 6/24 절반차익(0.02주) 베이킹 셋업\n✅ 4. 6/24 MU 실적 후: 결과 보고 2차(AVGO 추가 or MSFT)\n🛡️ 5. Dry powder 대부분 사수 — 매파+휴장 국면, 확인하며 분할\n🚫 추격금지: GEV(+6.77%)·SK하이닉스·삼성전기·두산E(10만 재이탈)·SPCX — 갭 당일 X\n```\n\n---\n\n# 🎯 결론\n> **외인이 종가엔 +1.3조 받쳤지만(장중은 매도→막판 반전), 미국은 매파다.** 그래서 '신중 끄고 다 산다'가 아니라 — **알림 깔고, 6/22 외인 지속 확인하고, 하락 이유가 일시적인 AVGO부터 분할로 줍는다.** ORCL·META는 구조적 오버행이라 매수 아님(버티기), GEV는 +6.77% 올라서 추격 금지. '공격적으로'는 **무지성 추격이 아니라, 이유 보고·확인하고·분할해서 안 죽고 오래 사는 공격.** 오늘 시장가 0, 6/22부터 시동. 💪\n\n---\n*투자 자문 아님. 모든 레벨은 분석 참고이며 최종 결정은 정훈. 미국주 소수점=시장가 체결(갭 변동 노출).*\n"
    },
    {
      "id": "holdings_final_2026-06-18",
      "file": "docs/reports/holdings_final_2026-06-18.md",
      "title": "📊 정훈 종목 최종 보고 — 보유 16 + 워치 (FOMC 매파 직후 · FAB10 + 매도 디시플린)",
      "date": "2026-06-18",
      "version": null,
      "kind": "보유확정",
      "preview": "$567.58 / −10.5% · 목표 $827 (+46%) · strongbuy(매도 0)",
      "content": "# 📊 정훈 종목 최종 보고 — 보유 16 + 워치 (FOMC 매파 직후 · FAB10 + 매도 디시플린)\n> KR=6/18 마감(코스피 첫 9,000 돌파) / US=6/17 종가(FOMC 반응) / 환율 1,521원 · 목표=consensus.py·증권사 · 투자 자문 아님\n\n## 🏆 한 줄 프레임\n**FOMC가 매파로 나왔다(점도표 인상 전환). 외인은 이틀째 빠지고, META는 고유 악재로 −5%.** 좇을 때가 아니라 **현금 지키고 정리할 때.** 정훈은 이미 AI 리더 8개(NVDA·META·MSFT·AAPL·GOOGL·TSLA·AVGO·MU)를 손에 쥐었다. 오늘 폭등(코스피 9,000)은 매수 근거가 아니라 **현금 624,771원을 지킬 이유.** 매도 기준 = *\"산 이유가 살아있나\"*.\n\n---\n\n# 1️⃣ 보유 16종목 (풀 표 — 축소 금지)\n\n> ⭐: ⭐⭐⭐⭐⭐ 최선호 코어 / ⭐⭐⭐⭐ 코어·강세 / ⭐⭐⭐ 홀딩·중립 / ⭐⭐ 정리·모멘텀 주의\n\n| 종목 | 현재가 | 당일 | 수익률 | 목표가 | 여력 | 매수존 | 매도/트림 | ⭐ | 액션·근거 |\n|---|---|---|---|---|---|---|---|---|---|\n| **NVDA** | $204.65 | −1.33% | +2.6% | $299 | +46% | $190대 눌림 | 비중관리(추가절제) | ⭐⭐⭐⭐⭐ | 채권호재·Blackwell완판·Rubin 2H |\n| **META** | $567.58 | −5.44% | **−10.5%** | $827 | +46% | 7/29 실적확인 후 | 홀딩·투매금지 | ⭐⭐⭐⭐ | 고유악재=노이즈, P/E 19.4x 매그7 최저 |\n| **MSFT** | $378.91 | −3.79% | −7.6% | $561 | **+48%** | $360~370 눌림 | 홀딩 | ⭐⭐⭐⭐ | 상방 최대, Azure 무한 tailwind |\n| **GOOGL** | $363.79 | −2.53% | −6.2% | $433 | +19% | $350대 눌림 | 홀딩 | ⭐⭐⭐⭐ | Cloud·Gemini 견조 |\n| **AVGO** | $392.90 | +4.30% | −6.7% | $522 | +33% | 평단 $421↓ 물타기(비둘기시) | 홀딩 | ⭐⭐⭐ | 가이던스=눈높이 문제, 8개하우스 상향 |\n| **MU** | $1,043 | +2.20% | **+39.3%** | $879→상향중 | 리프라이싱 | 6/24 실적 후 | **절반차익(6/24)** | ⭐⭐⭐⭐ | \"2026 sold out\", 집중도 완화 |\n| **AAPL** | $295.95 | −1.10% | +15.1% | $313 | +6% | 신규X(목표근접) | **부분트림 1순위** | ⭐⭐⭐ | 금리방어 입증(매파에 −1.1%만) |\n| **TSLA** | $396.38 | −2.05% | −6.2% | $421 | +6% | 관망 | $420 근접시 트림 | ⭐⭐⭐ | Optimus 7~8월, 상방제한 |\n| **ANET** | $164.93 | −1.83% | +1.8% | $189 | +15% | 홀딩 | 홀딩 | ⭐⭐⭐⭐ | AI 네트워크 |\n| **ORCL** | $183.53 | −2.55% | **−20.9%** | $253 | +38% | 눌림(신규보류) | **패닉셀금지** | ⭐⭐⭐ | 최대손실, RPO생존·OpenAI집중 모니터 |\n| **VOO** | $681.41 | −1.21% | +5.6% | 인덱스 | — | 상시 적립 | — | ⭐⭐⭐⭐ | 분산형 코어(채널도 '안전' 분류) |\n| **삼성전자** | 353,500원 | +2.02% | +34.2% | 480,000~530,000원 | +36~50% | 295,000~305,000원 | 코어홀딩(트림X) | ⭐⭐⭐⭐ | HBM4 Rubin qual통과+AMD 지명 |\n| **LG전자** | 228,500원 | −2.56% | **+46.9%** | 컨센 초과 | — | 210,000~220,000원 | 펀더훼손시만(1주 분할불가) | ⭐⭐⭐⭐ | 손절선 없음, 최대수익권 |\n| **현대차** | 601,000원 | −2.59% | −4.6% | 600,000원(공격 800,000) | +33% | 580,000~600,000원 | 800,000원 도달시 트림 | ⭐⭐⭐ | BD 첫 가격표(이달말 풋옵션)가 분기점 |\n| **두산로보** | 102,900원 | −3.11% | +2.9% | 극단분산 | — | 관망(10만 심리) | 갭업차익(모멘텀) | ⭐⭐ | 적자·PSR219배 테마주 |\n| **NAVER** | 237,000원 | −2.46% | −5.4% | 약 300,000원 | +27% | 225,000~235,000원 | 반등시 정리 | ⭐⭐ | 정리후보(두나무 9월까지 보유) |\n\n### 🔍 핵심 종목만 콕\n\n**🟡 META — FOMC 매파로 추가 보류 (가장 큰 변화)**\n```\n$567.58 / −10.5% · 목표 $827 (+46%) · strong_buy(매도 0)\n−5.44% 급락 = FOMC 아닌 고유악재(AI임원 이탈 + Section 230 소송)\n단 광고엔진 무손상·Forward P/E 19.4x(매그7 최저) = '흔들림이지 위험 아님'\n⚠️ 어제까진 비둘기시 추가 1순위였으나 → 매파 확정 + 고유악재로 보류\n액션: 추격·물타기 금지, 7/29 Q2 실적 or 악재진정 후 재논의 ⭐⭐⭐⭐\n```\n\n**🟡 MU — 절반 차익 1순위 (6/24 D-6, 6/23 저녁 베이킹)**\n```\n$1,043 / +39.3% · 컨센 $879 위지만 목표 급상향중(UBS $1,625·MS $1,050)\n\"2026 sold out\" + Street가 가이던스 상회 = beat 기대 / 단 인라인이면 차익실현 조정\n액션: 절반 차익(+39% 확정·집중도 완화) + 절반 실적 베팅 = 분할 정석 ⭐⭐⭐⭐\n※ 6/24 야간(폰 미가용) → 6/23 저녁 사전 예약 베이킹 필수\n```\n\n**🟢 ORCL — 패닉셀 금지(가장 중요)**\n```\n$183.53 / −20.9% (최대손실) · 목표 $253 (+38%)\n산 이유(RPO 백로그 $638B): 아직 살아있음 = '흔들림'\n⚠️ 최대손실이라 던지고픈 충동 = 처분효과. 가격 아닌 이유로!\n액션: 버티되 OpenAI 47%·$300B 집중 희석 깨지면 그때 정리. 신규보류 ⭐⭐⭐\n```\n\n**🟡 AAPL — 부분 트림 1순위 (신규)**\n```\n299원대 → $295.95 / +15.1% · 목표 $313 (+6%, 목표 근접)\nFOMC 매파에 −1.10%만 = 금리방어 입증. 상방 제한 + 최대수익권 미국주\n액션: 차익 일부 확보 검토(목표 근접·금리방어 완료). 코어 일부 유지 ⭐⭐⭐\n```\n\n> 나머지(NVDA 비중관리·MSFT/GOOGL/ANET/삼성 홀딩·LG 1주홀딩·TSLA/현대차 상방제한·두산로보 모멘텀·VOO 적립·AVGO 비둘기시 물타기)는 위 표 액션대로.\n\n---\n\n# 2️⃣ 워치리스트 (풀 표 — 축소 금지)\n\n| 종목 | 현재가 | 당일 | 목표가 | 여력 | 매수존 | ⭐ | 지금 살까·근거 |\n|---|---|---|---|---|---|---|---|\n| **GE Vernova** | $1,048.86 | +6.77% | $1,206~1,212 | +15% | 눌림 분할 | ⭐⭐⭐⭐ | ✅**워치 유일 매수검토**·Bernstein 개시·수주+71% |\n| **두산에너빌리티** | 100,100원 | −3.00% | 143,000원(122k~165k) | +43% | 93,000~95,000원 | ⭐⭐⭐ | ⏳10만 재돌파 추격금지, SMR 진짜수혜 |\n| **SK하이닉스** | 2,693,000원 | +6.82% | 1,800,000원 | **−33%** | 추격❌ | ⭐⭐⭐ | ❌사상최고·목표 +50%초과·ADR 8월 |\n| **삼성전기** | 2,220,000원 | +9.25% | 2,300,000~3,000,000원 | +4~35% | 1,600,000~1,750,000원 | ⭐⭐⭐ | ⏳5일급등·PER 103배 과열 |\n| **LG이노텍** | 1,309,000원 | +4.89% | FC-BGA | — | 증설 관찰 | ⭐⭐⭐ | ⏳선행 41배·구조적 공급부족 |\n| **원익IPS** | 164,700원 | +1.86% | 160,000~180,000원 | 근접 | 125,000~130,000원 | ⭐⭐ | ⏳코스닥 약세 역행 강세 |\n| **테스** | 175,900원 | +3.84% | 160,000~170,000원 | 초과 | 130,000원 | ⭐⭐ | ⏳목표 초과, 눌림 예약 |\n| **SK이노베이션** | 103,600원 | −4.95% | 테마 | 미확정 | 관망 | ⭐⭐ | ⏳SMR 간접테마化 |\n| **한화에어로** | 1,198,000원 | −2.12% | 대미방산 | — | 소화 관찰 | ⭐⭐⭐ | ⏳차익실현·한화 KAI 2대주주 |\n| **조선바스켓** | 한화오션 125,100·삼성중공업 27,800·HD현대중 685,000 | −3~6% | 대미조선 | — | 소화 관찰 | ⭐⭐ | ⏳1호 7월이연·차익실현 |\n| **STM** | $73.36 | −1.60% | **$64** | **−15%** | 보류 | ⭐⭐ | ❌sell-side 하향(채널 낙관과 상충) |\n| **T-Mobile** | $181.31 | −1.65% | $261 | +44% | $165 조정시 | ⭐⭐⭐ | ⏳T-Sat 7/23 론칭 |\n| **SpaceX(SPCX)** | $191.82 | −4.95% | $188 | −2% | 추격❌ | ⭐⭐ | ⏳락업 8월·\"비싼 구간\"(채널) |\n\n### 🔍 워치 콕\n- **✅ GE Vernova** — 워치 중 유일 매수 검토. AI전력 3종(가스터빈·원전·전력망) = 미국판 두산E, 백로그 $163B 역대최고·Bernstein 개시 $1,206. 단 Jefferies는 $1,210 하향(Buy유지)=밸류 부담 인지. **$50~100 소수점 소액, 갭당일 추격 말고 눌림 분할.** ⭐⭐⭐⭐\n- **❌ SK하이닉스** — 사상 첫 260만·목표(180만) **+50% 초과 = 가장 과열.** HBM4 펀더는 진짜지만 추격 부적합, ADR 8월 상장 대기. ⭐⭐⭐(펀더)/추격❌\n- **⏳ 두산에너빌리티** — SMR 진짜 수혜(NuScale 공급망, 자막 \"두산로보틸리티\"는 오류). KUIC 1호 7월·PER 203배=모멘텀. 93,000~95,000원 눌림 1주만, 100,000원 추격금지. ⭐⭐⭐\n\n---\n\n# 3️⃣ 💰 현금 624,771원 배분 — FOMC 매파 후 단일안\n\n## 🅰️ 보존안 (룰 정합·확정) ⭐\n```\n지금: 624,771원 전액 보존\n이유: ①매수존 전부 위 이탈 ②외인 2일 연속 순매도 ③FOMC 매파(점도표 인상)\n3차 트랜치(META·AVGO 22.5만): 🔴 매파 확정 → 전면 보류\n  베이킹 룰 그대로 — 비둘기였으면 META 1순위였으나 진입 안 한 게\n  결과적으로 META -5.44% 추가 낙폭 회피(룰3이 유리하게 작동)\n오늘 저녁 폰창(17:30~20:50): \"예약 미입력\" 확인 + 보유분 투매 금지만\n```\n\n## 🅱️ 참고용 — 그래도 사고 싶다면 (⚠️ 룰 위반 주의)\n```\n워치 GEV만 소액: 원화 → 달러 약 $70 환전(@1,521) → GEV 소수점 약 0.067주\n  (FOMC·종목 무관 고유호재·워치 유일 매수검토라 상대적 안전)\n⚠️ 그 외 전부 추격 — META/AVGO는 매파 노출, 두산E/삼성전기/하이닉스는 과열.\n   META는 7/29 실적, MU는 6/24 후 재평가 → 기다리는 게 정답\n```\n\n> 💡 **3차 트랜치 재개 조건** = 비둘기 전환 / META 7/29 실적 확인 / 외인 순매수 복귀 — 셋 중 하나.\n\n---\n\n# 4️⃣ 📅 핵심 일정 (2주)\n| 날짜 | 이벤트 | 대응 |\n|---|---|---|\n| **6/18(목) 저녁** | 폰창 | \"예약 미입력\"·투매금지·외인 종가 확인 |\n| 6/19(금) | 美 준틴스 휴장 / 이란 서명 | 거래공백·신규진입 보류 |\n| 6/22(월) | SK하이닉스 ADR SEC 주 | 모니터 |\n| **6/23(화) 저녁** | **MU 베이킹** | 절반차익 사전예약 |\n| **6/24(수)** | **MU 실적** | **절반 차익** |\n| 6/26(금) | SPCX MSCI 편입 | 수급 |\n| **7/16(목)** | **한은 금통위(2.50→2.75% 인상 전망)** | 국내 긴축 |\n\n---\n\n# 5️⃣ 📋 6월 말 목표 & 액션 플랜\n\n## 🎯 6월 말 목표 자산\n**현재 총자산: 8,398,313원** (전일 6/13 대비 +45,167원)\n- 미장: $3,877 × 1,521원 = **5,898,642원**\n- 국장: **1,874,900원**\n- 현금: **624,771원**\n\n| 목표 | 금액 | 필요 수익 | 현실성 |\n|---|---|---|---|\n| 🟢 현실 목표 | **8,600,000원** | +2.4% | 반도체 순환매·국장 강세면 도달 |\n| 🔥 도전 목표 | **9,000,000원** | **+7.2%(약 602,000원)** | META 반등 + MU 비트 + 환율 必 |\n\n> ⚠️ 솔직히: 매파 FOMC + 외인 이탈 국면에서 2주 +7.2%는 무리. **목표는 동기부여용 — 추격으로 맞추는 건 룰 위반.** 지금은 지키는 장.\n\n## 💡 6월 전략 핵심 3가지\n**1. FAB10 코어 유지 + 현금 보존** — 이미 AI 리더 8개 보유. 매파 FOMC 단기 조정은 장기 사이클(2028~29 피지컬AI)의 소음. 코어(NVDA·삼성·MSFT·META·VOO) 홀딩, 현금은 보존.\n**2. 집중도 완화** — AI 메모리 6중 쏠림(삼성·NVDA·MU·AVGO·하이닉스·삼성전기). MU 6/24 절반 차익이 집중도 줄이는 유일한 능동 수단. 새 메모리 베팅 추가 금지.\n**3. 정리 디시플린** — MU 절반차익 · AAPL 부분트림 검토 · NAVER 이유정리 · ORCL 패닉셀금지. *\"산 이유가 살아있나\"*로 판단.\n\n## ✅ 오늘 할 것\n- 국장: 전 종목 보유 유지, 추격금지(두산에너빌리티·SK하이닉스·삼성전기)\n- 미장: 전 종목 보유, **현금 보존·3차 트랜치 보류**, 추가매수 없음(폰창 \"예약 미입력\" 확인)\n- 외인 6/18 종가 수급 확인 → 3일째 순매도 여부 6/19 이후 추적\n\n---\n\n# 🎯 결론\n> **오늘은 사는 날이 아니라 지키는 날.** FOMC가 매파(점도표 인상 전환)로 나왔고, 외인은 이틀째 빠지고, META는 고유 악재로 −5%. 코스피 첫 9,000 돌파의 환호가 가장 위험한 순간이다. **3차 트랜치는 룰대로 보류 확정, 현금 624,771원 전액 보존.** 능동 액션은 딱 둘 — **MU 6/24 절반 차익(6/23 베이킹)**과 **AAPL 부분 트림 검토.** 워치에선 GEV만 소액, 나머지(하이닉스·삼성전기·두산E)는 전부 추격금지. META·MU는 기다리면 더 확신 갖고 살 수 있다 — **하루(혹은 실적 하나) 기다리는 게 추격 안 하는 길.** 💪\n\n---\n*투자 자문 아님. 모든 레벨은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "fomc_baking_2026-06-18",
      "file": "docs/reports/fomc_baking_2026-06-18.md",
      "title": "🔥 FOMC 6/18 사전 베이킹 — 조건부 실행 룰 (2026-06-17 확정)",
      "date": "2026-06-18",
      "version": null,
      "kind": "이벤트",
      "preview": "⚠️ 2년물↓인데 주가도↓ = \"성장둔화 우려형\" → 비둘기로 오독 금지. 신임의장 데뷔전 휩쏘 잦음 → 장중보다 종가·익일 안착으로 판단.",
      "content": "# 🔥 FOMC 6/18 사전 베이킹 — 조건부 실행 룰 (2026-06-17 확정)\n\n> **목적**: FOMC 발표 6/18 03:00 KST = 폰 가용(17:30~20:50) 밖 → 당일 밤 즉흥 대응 금지. **오늘 IF/THEN을 미리 굳혀** 6/18 저녁 폰 창에서 기계적으로 실행.\n> 대상 = **3차 트랜치 ~225,000원**(현금 624,771원 중). 투자 자문 아님 — 최종 결정 정훈.\n\n## 타임라인 (KST)\n- **6/18(목) 03:00** — FOMC 결정 + 워시 첫 회견 (취침 중, 대응 불가)\n- **6/18(목) 17:30~20:50** — 폰 창 ① 결과·시장반응 판독 ② 토스 소수점 예약 설정\n- **6/18(목) 22:30** — 미장 개장 → 예약분 1차 체결\n- **6/19(금)** — 美 준틴스 휴장 (거래 없음)\n- **6/22(월)** — 잔여분 집행·기록\n\n## 🧭 STEP 1 — 6/18 저녁 판독 (점도표보다 회견 톤 + 시장지표)\n**핵심키 = 美 2년물 + 달러인덱스(DXY).** (워시가 본인 dot 생략 가능 → 점도표만으론 판단 불가)\n\n| 판정 | 신호 (2개 이상 충족) |\n|---|---|\n| 🟢 **비둘기** | 2년물 ↓ · DXY ↓ · 나스닥/SOX ↑ · 회견 \"인하 여지 열림/AI 디스인플레\" |\n| 🟡 **중립** | 2년물·DXY 횡보 · 혼조 · \"데이터 의존\" 원론 |\n| 🔴 **매파** | 2년물 ↑ · DXY ↑ · SOX ↓ · \"추가 정책여지 닫힘/인상 테이블\" |\n\n⚠️ 2년물↓인데 주가도↓ = \"성장둔화 우려형\" → 비둘기로 오독 금지. 신임의장 데뷔전 휩쏘 잦음 → **장중보다 종가·익일 안착으로 판단.**\n\n## 🎯 STEP 2 — 판정별 예약 (토스 미국 소수점 = 금액 지정, 시장가 체결)\n\n참고 시세(6/16): META $600.21(1주≈90.8만), AVGO $376.71(1주≈57.0만), USD/KRW 1,513.\n\n| 판정 | 예약 액션 | 분할 |\n|---|---|---|\n| 🟢 **비둘기** | **META 13.5만 + AVGO 9만**(합 22.5만) 소수점 예약 | 네마녀·준틴스 변동성 → **절반(약 11만)만 6/18 밤, 절반 6/22** 소화 후 |\n| 🟡 **중립** | **META 11만만** 예약, 나머지 보류 | 1회 |\n| 🔴 **매파** | **예약 0 · 현금 624,771원 전액 보존** | — |\n\n- 우선순위 근거: META(컨센 +38%·낙폭 깊음·미보유→신규)·AVGO(컨센 +39%·평단 아래 물타기효과). 단 **AVGO는 6/3 가이던스 미스 진앙** → 비둘기 확정 시에만, 추격 아닌 조정주 매수로.\n- NVDA·ANET·ORCL은 이미 보유(중복) → 3차 대상 아님.\n\n## 🛡️ STEP 3 — 매파/패닉 시 방어 (영상 '패닉셀 금지' 적용)\n- 🔴 매파라도 **보유분 투매 금지** — \"가장 무서운 날 옆에 가장 좋은 날\". 산 이유 살아있는 종목(META·AVGO·MSFT·GOOGL·ORCL)은 흔들림이지 위험 아님.\n- 코스피 **7,500 안전핀** 거리 재점검(현 8,864, −15.4% 여유). 하회 시 잔여 트랜치 전면 동결.\n- 고베타 눌림이 깊으면 **추격 아닌 역발상 분할 메모만**(당일 밤 집행 금지).\n\n## ✅ 체크리스트 (6/18 저녁)\n- [ ] FOMC 결과·2년물·DXY·SOX 확인 → 🟢/🟡/🔴 판정\n- [ ] 판정별 토스 소수점 예약(또는 보류)\n- [ ] 코스피 종가·외인 수급(복귀 여부) 확인 → 강세 논지 재점검\n- [ ] 안전핀 7,500 거리 확인\n- [ ] 6/22 잔여 집행 메모\n\n---\n*투자 자문 아님. 모든 레벨은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v17_addendum_2026-06-17",
      "file": "docs/reports/report_v17_addendum_2026-06-17.md",
      "title": "v17 부록 · 2026-06-17 — 심층분석 ①~④ + 경제사냥꾼 자막 재추출",
      "date": "2026-06-17",
      "version": 17,
      "kind": "보고서",
      "preview": "삼성전기 YTD +571%, 다수 반도체 ETF에서 단일종목 30% 한도 초과(KODEX AI반도체TOP2 39.69%) → 패시브 신규자금 막힘 + 발빠른 기관 이미 비중 축소. 미 셀오프發 ETF 자금유출 시 한도초과 종목이 더 취약(상방 막힘·하",
      "content": "# v17 부록 · 2026-06-17 — 심층분석 ①~④ + 경제사냥꾼 자막 재추출\n\n> v17 본보고서 §8 선택지 4건 전부 심층화(macro·kr-market·semi-ai·power-physical 데스크) + 경제사냥꾼 자막 6건 전량 재확보(research-feed). **투자 자문 아님 — 최종 결정은 정훈.** 시세=6/17(KR)/6/16(US) 기준.\n\n---\n\n## ① 6/18 03:00 FOMC 워시 첫 회견 톤 판독 매뉴얼\n\n**핵심**: 동결 ~98% 확정, easing bias 문구 삭제→중립 전환 컨센. **워시 = 금리 비둘기(AI=구조적 디스인플레)·대차대조표 매파.** 시장 기대가 비둘기 쪽이라 **\"예상보다 매파\" 서프라이즈 리스크가 비대칭으로 큼.** 점도표는 워시 본인 dot 거부 가능 → **회견 톤이 dot보다 중요.**\n\n### 비둘기 vs 매파 체크리스트 (8항목, 🟢 5+ = 비둘기 / 🔴 3+ = 매파)\n| 항목 | 🟢 비둘기 | 🔴 매파 |\n|---|---|---|\n| 인플레 4.2% 평가 | \"에너지 일시적·core 2.9% 억제\" | \"광범위·끈적, 정책여지 닫힘\" |\n| 에너지/유가 | \"Hormuz 합의→공급회복 역기저\" | \"유가發 2차 파급\" |\n| easing bias | 삭제+\"인하여지 열림\" 구두보완 | 삭제+\"인상도 테이블\" |\n| AI 생산성 | \"structurally disinflationary\"(워시 시그니처) | AI 언급 회피 |\n| 노동시장 | \"둔화→완화 정당\" | \"견조→긴축 유지\" |\n| 관세 | \"일회성 레벨효과\" | \"지속 상방리스크\" |\n| 정책기조 | \"데이터 의존·인내\" | \"선제대응·신뢰회복\" |\n| 점도표 | \"dot 과대해석 말라\" | 중앙값 상향 강조 |\n\n### 시장 반응 역산 (정훈은 종가만 봄 → 6/19 아침 판독)\n**핵심 판독키 = 2년물 + 달러인덱스(DXY).** 둘 다 ↓ = 비둘기 신뢰 高 / 둘 다 ↑ = 매파. 단 2년물↓ + 주가↓이면 \"성장둔화 우려形\"이니 비둘기 오독 금지.\n\n| 지표 | 🟢 비둘기 | 🔴 매파 |\n|---|---|---|\n| 美 2년물(1차신호) | ↓ | ↑ |\n| 달러인덱스 | ↓ | ↑ |\n| 나스닥/SOX 선물 | ↑ | ↓ |\n| 금 | ↑ | ↓ |\n| USD/KRW | ↓(외인우호) | ↑ |\n\n### 🔧 META 집행일 정정 (중요)\n**본보고서 \"META 6/20(월) 집행\"은 날짜 오류.** 6/20은 **토요일**, 6/19는 **준틴스 휴장** → FOMC(6/18 새벽)와 META 집행 사이 거래일은 6/18(목) 하루뿐, **실제 집행 가능일 = 6/22(월).**\n- 비둘기 확정 시: 6/22(월) 폰가용창(20:50 전) META 소수점 22.5만(~0.25주) 지정가 예약 → 22:30 자동집행.\n- 매파/혼조(2년물↑ or DXY↑ or 🔴 3+): META 집행 전면 보류.\n\n**과거 사례**: 2018 파월 첫 회견 — dot은 비둘기였으나 화법이 매파로 해석돼 장중 반전. **신임 의장 데뷔전은 내용보다 뉘앙스에 과민반응** → 워시도 휩쏘 가능성 高, 발표 직후 1시간보다 **종가·익일 안착 레벨로 판단**(추격금지 룰 정합).\n\n---\n\n## ② 외국인 순매도 전환 점검 — '신중 경보 ON, 강세 하향 보류'\n\n**6/17 외인 ≈ −1조(−9,923~−9,999억) 순매도 전환**(6/13~16 3일 +4.85조 순매수 후), 기관 +5,777~5,819억·개인 +5,394~5,456억이 신고가 떠받침.\n\n### 매도 성격 = 차익실현 우세 (리스크오프 아님) [검증]\n- ① 직전 3일 +4.85조 폭매수 직후 되돌림(직전 산 종목 되판 트레이딩 패턴) ② **외인 1조 매도에도 코스피 +1.58% 신고가**(리스크오프면 동반 급락했어야) ③ 매도 집중 = **건설 −5.57%·금속·유통(비반도체)**, 매수 = **전기·전자 +2.75%** → 매도의 질 양호 ④ SK하이닉스 +5.84% 신고가는 기관·개인이 외인 차익 흡수.\n- 기술적 요인 점검: MSCI 5월 변경(5/30)·코스피200 변경(6/12반영·6/15효력) 모두 소화 완료 → **6/17 기계적 매도 아님 = 순수 차익실현.**\n\n### 일회성 vs 추세전환 판별 (현재 🟢 5 / 🔴 0)\n| 항목 | 추세전환🔴 | 일회성🟢 | 6/17 |\n|---|---|---|---|\n| 연속일수 | 3일+ | 1일 | 🟢 1일째 |\n| 누적액 | 3일 −2조+ | 직전매수 이내 | 🟢 +4.85조의 20%만 환원 |\n| 지수동조 | 매도+급락 | 매도+상승 | 🟢 신고가 |\n| 반도체매도 | SK·삼전 투매 | 비반도체 위주 | 🟢 건설·금속 |\n\n### 강세 논지 하향 임계치 (구체 기준)\n- 🟡 **주의(현 단계)**: 1일 매도 + 신고가 유지 → 강세 유지·모니터링.\n- 🟠 **하향 검토**: 2거래일 연속 순매도 + 2일 누적 −1.5조+ 또는 반도체로 매도 확산 → 신규진입 보류.\n- 🔴 **강세 하향(액션)**: 3거래일 연속 순매도 + 원/달러 급등 동조 + 코스피 8,600 하회 (3개 동시) → 현금 비중 유지·신규매수 동결.\n- **SK하이닉스 진입**: 외인 매도 전환은 진입 미룰 신호 아니나 트리거는 'ON'이 아닌 **'HOLD'** — **FOMC 비둘기 + 외인 6/18~19 복귀 2일 확인 후 지정가 분할**이 룰 정합(250만 돌파 직후 추격 회피).\n\n**한 줄**: 신중 경보는 켜되 강세 하향은 보류. **6/18 FOMC + 외인 복귀 2일 여부가 분기점.**\n\n---\n\n## ③ 미 메모리 셀오프 = 한국 선행 약세인가? — '구조적 디커플링 우세'\n\n### 🔧 사실관계 정정 (날짜)\n**브로드컴 Q3 가이던스 미스($16B vs 컨센 $17.2B, FY26 $56B 미상향)는 6/3 Q2 실적 때 사건.** 6/16 SOX −5.71%·MU −6.18% 동반 급락은 그 **여진(DRAM bloodbath 2차 충격)**이지 6/16 신규 AVGO 프린트가 아님. 본문 \"6/16 브로드컴 미스\"는 6/3 미스의 여진으로 정정.\n\n### 미스의 본질 = 기대 과열 + ASIC 전략 후퇴 (구조적 capex 둔화 신호 약함)\n- Q2 AI매출 $10.8B·총매출 $22.2B(+48% YoY) 호조, Q3 가이드 $16B도 +200% YoY. 문제는 ①FY26 $56B 미상향(천장 해석) ②Hock Tan \"풀시스템→커스텀 ASIC만\" 후퇴 ③\"구글 복수 칩공급사\" 발언 = AI capex 파편화·BOM 하향 우려.\n- **HBM 전이**: ASIC도 HBM 소비 → 직접 전이 제한적(강세). 단 \"하이퍼스케일러 BOM 하향\" 심리는 메모리 가격 파워에 균열 가능(신중).\n\n### MU/AVGO = 한국 선행지표인가 → 디커플링 우세\n- MU·SK하이닉스 고상관(둘 다 YTD +200%대)이나, **6/17 한국 역행은 HBM 별도 수급**: SK하이닉스 HBM4 점유율 54~70%(Rubin향)·\"2H26 HBM 공급부족 심화\" 명시 → +5.84% 신고가. MU 약세는 레거시 DRAM/NAND + 미 반도체 디리스킹 성격.\n- **결론**: 시차 추종(신중)보다 HBM 별도 사이클 디커플링(강세) 근거 우세. 단 \"구조적 디커플링 ≠ 단기 무상관\" — 일일 동조 재발 주의.\n\n### 6/24 MU 실적 시나리오 (보유 MU +36%)\n- 6/24 장마감 후. 회사 가이드 FQ3 매출 $33.5B±0.75, 비GAAP EPS $19.15±0.40, GM ~81%. 목표가 소스 편차 극심($866~$1,500) — **현재가 $1,020이 보수 컨센 목표 상회 = 밸류 부담.**\n- 🟢 서프라이즈(가이드 상회+2H HBM 부족 재확인): MU·삼성·SK 동반 랠리, 디커플링 강세 확정.\n- 🔴 쇼크(가이드 하회/레거시 DRAM 약세): 6/16 셀오프 재점화, 한국 \"다음날 따라빠짐\" 진짜 시험대.\n- **절반 차익 트리거**: +36% & 컨센 목표 상회 = 명분 충분. **실적 당일 진입 회피(추격금지), 실적 전/직후 분할 차익이 룰 정합.**\n\n### 삼성전기 패시브 수급 비대칭 [주의]\n삼성전기 YTD +571%, 다수 반도체 ETF에서 **단일종목 30% 한도 초과**(KODEX AI반도체TOP2 39.69%) → 패시브 신규자금 막힘 + 발빠른 기관 이미 비중 축소. **미 셀오프發 ETF 자금유출 시 한도초과 종목이 더 취약**(상방 막힘·하방 열림). **워치 신규진입 보류** 권고. 삼성전자는 HBM4 양산·HBM4E 샘플로 상대적 방어력.\n\n### NVDA — $25B 채권 vs SOX 셀오프 → 중기 호재 우세\n$25B 채권(주문 $85B 3배 초과, 30년물 +65bp 타이트닝) = 채권시장의 수십년 AI 베팅 신뢰. 6/16 −2.37%는 SOX 동반약세에 휩쓸린 것, 펀더 훼손 아님.\n\n**PM 집중도 경고**: 삼성·MU·SK하이닉스·삼성전기·AVGO·NVDA = HBM/메모리 단일테마 초집중. **6/24 MU가 공통 트리거** — 쇼크 시 보유·워치 동시 타격. 권고: ①MU 절반차익 분할 베이킹 ②삼성전기 신규 보류 ③SK하이닉스는 ADR 정식상장(8월) 전 추격 비추.\n\n---\n\n## ④ 두산에너빌리티 워치→보유 편입 결정 — '코어 아닌 모멘텀, 눌림 소액만'\n\n**6/17 103,200원(−0.10%), 10만 위 2~3일째 안착 — 단 개인 주도(외인·기관 차익실현) = '약한 안착'.**\n\n### KUIC 1호 = 기대 선반영 (실질 발표 7월)\n- 6/18 한미전략투자공사(자본 2조) 출범 **확정**. 단 **1호 프로젝트는 '7월 발표' 가닥**(산업장관 \"1호 언급 아직 이르다\"), 후보=루이지애나 LNG+신규원전, **두산E 선정 공식 미확인.** → 6/18 출범 갭 추격은 룰3 위배.\n\n### 밸류 = 장기이익 선반영 (전형적 모멘텀)\n- 2026E PER ~203배(미확인, 증권사별 편차)·PBR 7.7배. 미래에셋은 PER 아닌 **EV/EBITDA(2034F EBITDA 4.8조 할인)**로 목표 105k 산출 → **현 PER로 정당화 불가, 2030+ 이익 끌어쓴 값.**\n- 수주: 2025 14.7조 역대최대·2026 가이던스 13.3조·체코 5.6조·오만 두큼 5,300억(6/15). SMR 매출 램프 2026 0.2~0.3조→2030 3.3조 = **이익 실체 2027~2030 집중.**\n- 컨센 분산 극심: 미래에셋 105k(현재가 +1.7% 사실상 도달) ~ 상단 165k(+60%) → 낙관/신중 양극.\n\n### 편입 매뉴얼 — (b)눌림 1주 + (c)추격 보류 혼합\n| 항목 | 결정 |\n|---|---|\n| 현 103k 추격 | **보류**(룰3, 테마+개인 갭) |\n| 6/18 KUIC 출범 당일 | **진입 금지**(1호는 7월) |\n| 편입 방식 | 코어 아님 → **모멘텀 소액 1주만**, 트랜치 본예산과 분리 |\n| 진입 레벨 | **93~95k 1차 / 90k(6/12 지지) 2차** 눌림 대기 |\n| 예산 | 62만 중 **1주(~9.3만)만**, 잔여 53만은 반도체·전력 본예산 보존 |\n| 집행 | 정수 1주 = 시간외 17:30~18:00 지정가 예약 가능, 미체결 시 익일 재평가 |\n\n**분류: 모멘텀(테마·잘빠지기).** 코어 승격 전제 = 1호 실질발표(7월) + 외인 재유입 확인.\n\n---\n\n## 🎬 경제사냥꾼 자막 재추출 (6건 전량 확보 — 봇차단 우회 성공)\n\n**`web_embedded` 플레이어 클라이언트로 데이터센터 IP 봇차단 우회 성공.** 1차 실패분 전부 ko-orig 자동자막 완전 확보. (ios/android/tv=차단·DRM, mweb/web=자막 미노출, **web_embedded만 자막 트랙 제공** → 스크립트 CLIENT_CHAIN에 추가 권장.)\n\n| # | 영상 | 핵심 | 분류 |\n|---|---|---|---|\n| ① | **연준 다시 인하 가능**(롱폼) | 5월 CPI 4.2% 중 에너지 60%+·근원 2.9%·임금<물가 = 공급충격(수요견인 아님), 종전→유가 80달러대→물가 후행 둔화, 큰방향은 인하(UBS 늦어도 2027) | **[검증]** CPI/에너지. UBS·\"모르겠다 26%\"는 [미확인] |\n| ② | **6/19 종전 후 주가추세**(롱폼) | 돈흐름 순서 = 항공·화학→은행·무역금융→해운→건설(가장 늦음). \"추격구간 아닌 옥석구분\". 재건기금 $300B=걸프·민간펀딩(美직접 아님), SPR 1983년来 최저 | **[검증]** 펀딩구조. 추격경계론=룰 정합 |\n| ③ | **6/17 투자포인트**(쇼츠) | 건설 +7%·대우건설 ~+20%·DL이앤씨 2배 리포트·삼성E&A 최선호. **필반 −5.7% vs 다우 ATH = 붕괴 아닌 반도체→금융·산업재 순환매, HBM 무투매** | **[검증]**. ⚠️\"외인 3일 순매수\"는 촬영시점 — **6/17 종가 순매도 전환** [정정] |\n| ④ | **워시 첫 FOMC**(쇼츠) | 동결 97%, \"추가조정\" 문구 삭제·점도표 관전, 연내 인상확률 79→61% 하락 | **[검증]** |\n| ⑤ | **SpaceX 2배**(쇼츠) | 오펜하이머 $190·모닝스타 $63(밸류 절반)·나스닥100 조기편입 패시브 | **[검증]**. ⚠️\"뉴스트리트 $330\"=**실제 $165** [정정] |\n| ⑥ | **엔캐리 청산 신호**(쇼츠) | BOJ 1.0%(30년만 최고), JPY 공매도 9년래 최대. 단 2024.8과 달리 예고된 인상=서서히 조임 | **[검증/방향성]**. 안전핀·엔캐리 모니터 부합 |\n\n**🔧 정정 요약(채널 자막오류·과장)**: ⓐ NVDA 채권 제목 \"$27B\" → **$25B** ⓑ SpaceX 뉴스트리트 \"$330\" → **$165** ⓒ core PPI \"4.9%\" → **5.1%** YoY ⓓ \"외인 3일 순매수\" → **6/17 종가 순매도 전환**(개인·기관 주도). **방향성·테마(종전 순서론·순환매·인하론·엔캐리)는 전부 검증 통과** — 이번 회차 채널 방향성 양호, 구체수치만 일부 오류(평소 패턴).\n\n> 누적 로그 `docs/research/hunter_log.md` 트랙레코드 7행 추가 + 6/17 엔트리 자막 기반 전면 보강 완료.\n\n---\n\n*투자 자문 아님. 모든 레벨은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v17_2026-06-17",
      "file": "docs/reports/report_v17_2026-06-17.md",
      "title": "정훈 PORTFOLIO DESK · v17 · 2026-06-17",
      "date": "2026-06-17",
      "version": 17,
      "kind": "보고서",
      "preview": "1. 6/18 FOMC 회견 톤 판독 매뉴얼 — 워시가 점도표 생략 시 비둘기/매파를 무엇으로 가를지(회견 키워드·국채반응 기준) + META 6/20 집행 트리거 구체화.",
      "content": "# 정훈 PORTFOLIO DESK · v17 · 2026-06-17\n\n> 투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.\n> 시세 기준: **KR=6/17 마감** / **US=6/16 종가** / USD/KRW **1,513.45**. 8데스크(지역2·매크로·리서치·리스크 + 정량스크립트) 종합.\n> ⚠️ 버전: 어제(6/16)분이 v16(`report_v16_2026-06-16.md`)으로 main에 있어 오늘분은 **v17**.\n\n---\n\n## 변경점 (직전 v16 / 6/16 대비)\n\n- **🔴 외국인 순매도 전환** — 6/13~16 3거래일 연속 순매수(16일 +1.54조) 후 **6/17 외인 −9,997억 순매도 전환**. CLAUDE.md 핵심 신호(\"외인 = 코스피 메인 엔진\") 기준 **강세 논지 1차 근거 흔들림 = 신중 경보**.\n- **🔴 미국 반도체 셀오프** — 브로드컴 AI 가이던스 미스(Q3 ~$16B vs 컨센 $17.2B)로 **SOX −5.71%**, MU −6.18%·AVGO −4.37%·NVDA −2.37%·STM −5.57% 동반 급락. 내 메모리 라인 직격.\n- **코스피 3일 연속 사상최고** — 8,546(6/15) → 8,726.60(6/16,+2.11%) → **8,864.24(6/17,+1.58%)**. 단 6/17은 장초반 −1.39%(8,605)까지 급락 후 반등한 롤러코스터.\n- **6/16 BOJ 1.0% 인상 확정**(7-1 표결, 우에다 입원→우치다 대행). **엔캐리 청산 대혼란 미발생**(USD/JPY 160 위 유지).\n- **두산에너빌리티 10만 안착** — 103,200원, 10만 위 유지(추격금지 룰 유효).\n- 워치 SK하이닉스 **+5.84%(2,521,000)** 5연속 급등 — 외인 매도에도 기관 선취.\n\n---\n\n## 1. 시장 — 국장 / 미장\n\n### 국장 (6/17 마감)\n- **코스피 8,864.24(+1.58%) — 종가 사상 최고 3일째.** 코스닥 1,031.96(−0.20%, 4일째 차익소화·디커플링).\n- **수급 = 신중**: 6/17 외인 **−9,997억 순매도 전환**, 기관 +5,818억·개인 +5,394억이 신고가 떠받침. 외인 이탈이 일회성인지 추세전환인지 **6/18 FOMC 직후 재확인**이 분수령.\n- 섹터: 미·이란 종전 기대 + BOJ 충격 제한 → **방산·조선·금융·건설 강세**. 반도체는 미 셀오프 여진에도 **SK하이닉스 +5.84%**가 지수 견인, 삼성전자 +1.02%. 현대차 −3.44%·두산로보 −2.57%·SK이노 −3.11% 약세.\n\n| 국내 보유 | 티커 | 현재가 | 등락 | 원가대비 |\n|---|---|---|---|---|\n| 삼성전자 | 005930.KS | 346,500 | +1.02% | **+31.75%** |\n| LG전자 | 066570.KS | 234,500 | +0.21% | **+51.10%** |\n| 두산로보틱스 | 454910.KS | 106,200 | −2.57% | +6.20% |\n| 현대차 | 005380.KS | 618,000 | −3.44% | −1.90% |\n| NAVER | 035420.KS | 243,500 | +0.62% | −2.79% |\n\n### 미장 (6/16 종가)\n- **S&P 7,511.35(−0.57%) · 나스닥 26,376(−1.15%) · 다우 51,999.67(+0.64%) · 필반(SOX) 13,294(−5.71%).** FOMC 직전 위험회피·디펜시브 로테이션(다우만 +). VIX 16.1(과열 아님).\n- **반도체 직격**: MU −6.18%·AVGO −4.37%·NVDA −2.37%·ORCL −2.24%. 방어주 강세: META +1.13%·GOOGL +1.06%·AAPL +0.95%. 10년물 4.49%.\n\n| 미국 보유 | 현재가($) | 등락 | 원가대비($) |\n|---|---|---|---|\n| NVDA | 207.41 | −2.37% | +3.96% |\n| META | 600.21 | +1.13% | −5.33% |\n| VOO | 689.75 | −0.59% | +6.87% |\n| MSFT | 393.83 | −1.48% | −3.99% |\n| AAPL | 299.24 | +0.95% | **+16.37%** |\n| GOOGL | 373.25 | +1.06% | −3.73% |\n| TSLA | 404.66 | −1.58% | −4.22% |\n| ORCL | 188.33 | −2.24% | **−18.87%** |\n| ANET | 168.01 | −0.64% | +3.67% |\n| MU | 1,020.76 | −6.18% | **+36.28%** |\n| AVGO | 376.71 | −4.37% | −10.53% |\n\n---\n\n## 2. 섹터 (지역 데스크 교차 요약)\n\n- **반도체·AI인프라**: 브로드컴發 'sell-the-news'로 미 메모리/AI칩 일제 조정 — **MU −6.18%·AVGO −4.37%·STM −5.57%**. 단 국내는 **SK하이닉스 +5.84%**(HBM4 선취)로 역행, 미·한 디커플링. **MU/AVGO는 한국 메모리주 선행지표** → SK하이닉스·삼성전기 5연속 급등이 식기 시작한 테마 추격일 위험(리스크 데스크 경고).\n- **전력·피지컬AI**: 두산에너빌리티 103,200(10만 안착, 모멘텀 둔화 −0.10%), 조선바스켓 강세(한화오션 +3.02%·HD현대중 +1.29%), 한화에어로 +3.47%. 현대차·두산로보·SK이노는 차익·로테이션 약세.\n- **빅테크·플랫폼**: FOMC 직전 방어 매수처 — META·GOOGL·AAPL 플러스. 컨센 상방 큼(META +37.8%·MSFT +42.5%·TMUS +41.5%).\n\n---\n\n## 3. 매크로 데스크\n\n- **환율**: USD/KRW **1,513.45(+0.34%, 원화 약세)** — 외인 환차손 압력이나 미국분 원화 환산이익엔 +. USD/JPY 160 위 횡보.\n- **연준(6/18 03:00 KST)**: **동결 ~98%**(CME 98.4%, 4회 연속). 워시 첫 회견. 핵심 = 점도표 — 3월의 2026 인하 dot **삭제 컨센(매파)**, 단 **워시 본인 dot 제출 거부 가능성** → 판독을 점도표보다 **회견 톤** 중심으로. 한은은 점도표 없음.\n- **BOJ(6/16)**: 0.75→1.0% 인상 확정(7-1), 우치다 대행, 점진 추가인상 시사. 엔캐리 청산 미발생.\n- **유가·이란**: 브렌트 **$80 하회**(3월來 최저) — CPI 에너지 디스인플레 우호. 이란 휴전 MOU **6/19 스위스 서명** 예정. 다음 CPI/PPI는 **7월 중순**(2주 내 없음).\n\n---\n\n## 4. 리서치 피드 (경제사냥꾼 6/16~17)\n\n| 주장 | 분류 | 메모 |\n|---|---|---|\n| NVDA $25B 채권발행 = 전략적 호재(3배 초과청약 $85B, 무디스 AA1) | **[검증]** | 이례적 수치 정확. NVDA 코어 강세 보강 |\n| OpenAI 투자 $100B→$30B 축소 | **[미확인]** | 채널도 \"미확정\" 단서 부착 |\n| 6/19 美·이란 종전 서명 = 코스피 폭등 트리거 | **[검증]** | 종전→리스크프리미엄 제거 |\n| 삼성 67개 관계사 AI 전면도입(Gemini·ChatGPT·Claude) | **[검증]** | 삼성전자 긍정 모멘텀 |\n| 워시 첫 FOMC = 본인 점도표 생략, easing bias 삭제 | **[검증]** | 회견 톤 중심 판독 |\n| BOJ 1.0% 인상·엔캐리 청산 경고 | **[검증]** | 안전핀 7,500 감시 유지 |\n| SPCX 월가 2배 전망, street-high $227 (단 6/30 락업해제) | **[검증]** | 추격금지 대상 |\n\n> 채널 정확도 이번 회차 양호(NVDA 채권 숫자 전부 실측 일치). 누적 로그 `docs/research/hunter_log.md` 갱신 완료. ⚠️ 자막은 봇차단으로 1/4건만 추출, 나머지 메타+웹검색 재구성.\n\n---\n\n## 5. 리스크 데스크 (신중/bear)\n\n- **🚦 트리거**: 안전핀 7,500까지 **+18.2% 여유**(현 8,864). 2차 트랜치 8,000도 +10.8% 상회 → **매수존 전 구간 이탈**(NAVER 243,500 vs 225~235k / 삼성 346,500 vs 295~305k). **현금 3분할 = 매수존 위 대기, 추격 진입 불가가 정석.** 🔴발동: 두산E 103,200(10만 돌파, 추격금지).\n- **🚨 경보**: 룰 위반 없음. 단 **추격매수 금지(룰3) 근접 경보** — 코스피 3일 폭등·삼성전기 투자경고·SK하이닉스 5연속 급등 국면. FOMO로 미집행 현금 던지는 행위 차단.\n- **집중도**: AI 메모리 단일 테마 쏠림 심각 — 삼성·NVDA·MU·AVGO·SK하이닉스·삼성전기가 동일 HBM/AI capex 베팅 동승. 오늘 브로드컴 한 뉴스에 **MU·AVGO·STM·NVDA 동반 급락** = 분산이 아닌 사실상 단일 포지션 + 원/달러 단일 환노출.\n- **bear 핵심**: 강세론 최약 고리 = **'국내 신고가 vs 미국 메모리 균열' 디커플링**. 코스피 신고가는 외인이 아닌 기관·개인이 떠받친 장 — 외인 순매도 전환이 추세화하면 강세 논지 붕괴. MU/AVGO 선행지표가 식는 와중 SK하이닉스 급등은 추격일 수 있음. **6/18 FOMC 매파 점도표 → 6/19 준틴스 휴장(유동성 공백) → BOJ 엔캐리 잔존 3중 이벤트 구간**이 되돌림 방아쇠 가능. 신고가 도취보다 '과열 후 첫 충격' 대비.\n\n---\n\n## 6. 강세 vs 신중 디베이트\n\n**강세(bull)**: 코스피 3일 연속 사상최고, 미·이란 종전(6/19 서명)으로 리스크프리미엄 제거, BOJ 인상에도 엔캐리 청산 무난 통과. IB 코스피 목표 줄상향(골드만 9,000·NH/JP/노무라 10,000~11,000). NVDA $25B 채권은 AI capex 환류 호재, 컨센은 대부분 종목 +35~45% 상방(NVDA·META·MSFT·AVGO·TMUS strong_buy). AAPL +16.37%·MU +36%·LG전자 +51% 등 코어 수익 견조. 미 반도체 조정은 12개월 급등 후 건전한 숨고르기.\n\n**신중(bear)**: 신고가 엔진이 외인→기관·개인으로 교체(6/17 외인 −9,997억) = 메인 엔진 이탈. 미 SOX −5.71%·MU −6.18%·AVGO −4.37%는 sell-the-news로, **한국 메모리주의 선행 약세 신호**일 수 있음. 포트는 AI 메모리 단일 테마+단일 환노출에 과집중 — 한 뉴스에 동반 급락이 증명됨. 6/18 FOMC(매파 점도표)·6/19 준틴스 휴장·엔캐리 잔존 3중 구간이 2거래일 +10% 급등의 되돌림 트리거. 모든 매수존은 이미 위로 이탈.\n\n**PM 저울질**: 코어 강세 논지는 유지하되, **외인 매도 전환 + 미 메모리 균열 = 단기 신중 우위.** 추격 금지·현금 보존·FOMC 확인이 정석. (무게는 PM 종합 §7.)\n\n---\n\n## 7. PM 종합 (최종)\n\n### 🎯 오늘의 한 줄 결론\n**코스피 신고가 3일째지만 엔진(외인)이 빠지고 미 메모리가 균열 — 추격 금지·현금 보존, 6/18 FOMC 회견 톤 확인 후 판단. 오늘은 관망이 정석.**\n\n### 보유 16종목\n\n| 종목 | 현재가 | 원가대비 | 목표가(컨센) | 매수존 | ⭐ | 한줄 |\n|---|---|---|---|---|---|---|\n| 삼성전자 | 346,500 | +31.75% | — | 295~305k(이탈) | ⭐⭐⭐⭐ | HBM 코어, 외인 매수 수혜축 |\n| LG전자 | 234,500 | +51.10% | — | 홀딩 | ⭐⭐⭐⭐ | 최대수익, 손절선 없음 |\n| 두산로보틱스 | 106,200 | +6.20% | — | 관망 | ⭐⭐ | 모멘텀(적자·PSR고), 트레이딩 분류 |\n| 현대차 | 618,000 | −1.90% | — | 관망 | ⭐⭐⭐ | 로봇 베팅 vs 본업 리스크 |\n| NAVER | 243,500 | −2.79% | — | 225~235k(이탈) | ⭐⭐ | 정리후보 상시검토 |\n| NVDA | $207.41 | +3.96% | $298.93(+44%) | 눌림 | ⭐⭐⭐⭐⭐ | 채권호재, AI 코어 1순위 |\n| META | $600.21 | −5.33% | $827.32(+38%) | 조정주 재매수 | ⭐⭐⭐⭐ | FOMC 비둘기 시 소수점 후보 |\n| VOO | $689.75 | +6.87% | — | 적립 | ⭐⭐⭐⭐ | 인덱스 코어 |\n| MSFT | $393.83 | −3.99% | $561.39(+43%) | 눌림 | ⭐⭐⭐⭐ | 상방 큼, 조정 중 |\n| AAPL | $299.24 | +16.37% | $312.72(+5%) | 목표근접 | ⭐⭐⭐ | 방어주, 상방 제한 |\n| GOOGL | $373.25 | −3.73% | $432.83(+16%) | 눌림 | ⭐⭐⭐⭐ | 방어매수처 |\n| TSLA | $404.66 | −4.22% | $420.55(+4%) | 관망 | ⭐⭐⭐ | 상방 제한, 소액 |\n| ORCL | $188.33 | −18.87% | $252.64(+34%) | 눌림 | ⭐⭐⭐ | 최대손실, 컨센 상방 |\n| ANET | $168.01 | +3.67% | $189.13(+13%) | 홀딩 | ⭐⭐⭐⭐ | AI 네트워크 |\n| MU | $1,020.76 | +36.28% | $866.60(−15%) | **6/24 실적** | ⭐⭐⭐⭐ | 목표 상회, 실적 후 절반차익 검토 |\n| AVGO | $376.71 | −10.53% | $522.06(+39%) | 조정주 | ⭐⭐⭐ | 가이던스 미스 진앙, 갭당일 회피 |\n\n> 컨센 ±30% 괴리 플래그(상방): NVDA·META·MSFT·AVGO·ORCL·TMUS = 🟢. MU는 현재가가 목표 상회(−15%) = 6/24 실적 후 절반 차익 검토 신호.\n\n### 워치리스트 (활성)\n| 종목 | 현재가 | 비고 |\n|---|---|---|\n| 두산에너빌리티 | 103,200 | 10만 안착, **추격금지** — 9만 초중반 되돌림서 1주 지정가가 정석 |\n| SK하이닉스 | 2,521,000 | +5.84% 5연속↑, ADR 정식상장 8월(SEC 6/22주) 전 추격 비추 |\n| 삼성전기 | 2,032,000 | 투자경고, PER 200배 — 눌림 160~175만대 관찰 |\n| 원익IPS/테스 | 161,700/169,400 | 소부장, 눌림 관찰 |\n| SK이노 | 109,000 | SMR 테마, −3.11% |\n| 한화에어로/조선바스켓 | 1,224,000/— | 대미투자 방산·조선 강세 |\n| GEV/STM/TMUS/SPCX | $982/$74.55/$184/$201.80 | SPCX 6/30 락업해제 주의(추격금지) |\n\n### 제안 액션\n- **관망 디폴트** — 매수존 전부 위로 이탈 + 외인 매도 전환 + FOMC 임박. 신규 진입 보류, 현금 624,771원 보존.\n- **6/18 FOMC 사전 베이킹**(6/17 20:50 전, 폰 가용창): 야간 03:00 = 당일 대응 불가 → 조건부 룰만.\n  - 🟢 **비둘기**(회견 톤 완화·점도표 매파 아님): META 소수점 22.5만(~0.25주) **6/20(월) 수동집행**(6/19 준틴스 휴장 → 갭 소화 후 = 룰3 정합). AVGO는 −4.37% 급락 진앙 → 추격 아닌 조정주로만, 갭 당일 회피.\n  - 🔴 **매파**(2026 인하 dot 삭제·회견 매파): 3차 트랜치 **전면 보류**, 현금 보존, 안전핀 재점검.\n- **두산E·SK하이닉스·삼성전기 추격 금지** — 알림만, 되돌림 대기.\n- **외인 수급 6/18 재확인** — 순매도 추세화 시 강세 논지 하향, 순매수 복귀 시 SK하이닉스 선취 명분 재개.\n\n### 현금 배분 플랜 (624,771원, 3분할 미집행)\n- **1차 ~10–15만**: NAVER 225~235k 또는 삼성 295~305k **눌림 대기**(현재 둘 다 위).\n- **2차 ~20만**: 코스피 8,000 하회 + 이벤트 악재 동반 시. (현 8,864, 미도달)\n- **3차 ~22.5만**: FOMC 비둘기 확인 → META 소수점 6/20 집행. 매파면 보류.\n- ⚠️ 두산E 9만 초중반 되돌림 1주(~10만)는 트랜치 예산과 경합 — 편입 시 승인 필요.\n\n### 지켜볼 것 (2주 캘린더)\n| 날짜(KST) | 이벤트 | 폰 |\n|---|---|---|\n| **6/18(목) 03:00** | **FOMC+워시 회견+점도표** → 3차 판단(베이킹) | ❌야간 |\n| 6/19(금) | 美 준틴스 휴장(유동성 공백) / 이란 스위스 서명 | ⚠️ |\n| 6/20(월) | 비둘기 시 META 소수점 수동집행 | ✅ |\n| 6/22 주간 | SK하이닉스 ADR SEC 승인 가능성 | — |\n| 6/24(수) | **MU 실적** → 절반 차익 검토 | ❌야간 |\n| 7/16(목) | 한국은행 금통위 | ✅ |\n\n---\n\n## 8. 오늘의 이슈 선택지\n1. **6/18 FOMC 회견 톤 판독 매뉴얼** — 워시가 점도표 생략 시 비둘기/매파를 무엇으로 가를지(회견 키워드·국채반응 기준) + META 6/20 집행 트리거 구체화.\n2. **외인 순매도 전환 추세 점검** — 6/17 −9,997억이 일회성 vs 추세전환 판별법, 강세 논지 하향 임계치, 반도체 진입 타이밍 연동.\n3. **미 메모리 셀오프 = 한국 선행 약세?** — 브로드컴 가이던스 미스의 SK하이닉스·삼성전기·삼성전자 파급, 6/24 MU 실적 시나리오.\n4. **두산에너빌리티 워치→보유 편입 결정** — 10만 안착 vs 되돌림, 트랜치 예산 경합 정리.\n\n---\n\n## STATE SNAPSHOT\n```\n[STATE SNAPSHOT v17 2026-06-17]\n현금: 624,771원 (트랜치 1차/2차/3차 전부 미집행)\n보유변동: 없음 (16종목 유지)\n시세기준: KR=6/17 마감(코스피 8,864.24 +1.58%, 3일째 사상최고) / US=6/16 종가 / USD/KRW 1,513.45\n총자산: 8,527,797원 · 주식손익 +381,602(환차익 반영 추정 +602,099)\n오늘 할 일: 관망(매수존 전부 위 이탈)·신규진입 보류·현금 보존 / 추격금지(두산E·SK하이닉스·삼성전기) / 6/18 FOMC 조건부 베이킹\n수급경보: 🔴 6/17 외인 -9,997억 순매도 전환(3일 순매수 후) — 강세 논지 신중, 6/18 재확인\n워치리스트(활성): 두산에너빌리티(10만 안착)·SK하이닉스(+5.84%)·삼성전기(투자경고)·원익IPS·테스·SK이노·한화에어로·조선바스켓·GEV·STM·TMUS·SPCX\n대기 트리거:\n  ① 6/18 03:00 FOMC+점도표 → 🟢비둘기=META 소수점 6/20 집행 / 🔴매파=3차 보류\n  ② 6/19 준틴스 휴장(유동성공백) + 이란 스위스 서명\n  ③ 6/24 MU 실적 → 절반 차익 검토(목표 -15% 하회 상태)\n  ④ 두산E 10만 안착 → 추격금지, 9만초중반 되돌림 대기\n  ⑤ 외인 순매도 추세화 여부 = 강세 논지 분수령\n영구교정(신규):\n  - 6/16 BOJ 0.75→1.0% 인상 확정(7-1, 우에다 입원→우치다 대행), 엔캐리 청산 미발생(USD/JPY 160 위)\n  - 코스피 6/16 8,726.60(+2.11%)·6/17 8,864.24(+1.58%) 3일 연속 사상최고\n  - 6/17 외인 -9,997억 순매도 전환(6/13~16 3일 순매수, 16일 +1.54조 후)\n  - 미 SOX -5.71%(브로드컴 AI 가이던스 미스 Q3 ~$16B vs 컨센 $17.2B), MU -6.18%·AVGO -4.37%·STM -5.57%\n  - 브렌트 $80 하회(3월來 최저)\n  - 워시 본인 점도표 생략 가능 → FOMC 판독 회견 톤 중심\n  - NVDA $25B 채권발행(3배 초과청약 $85B, 무디스 AA1) = AI capex 환류 호재\n리서치: 경제사냥꾼 6/16~17 신규 7건 통합(NVDA 채권 자막 확보, 정확도 양호)\n다음 버전: v18\n```\n\n*투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "holdings_sell_discipline_2026-06-17",
      "file": "docs/reports/holdings_sell_discipline_2026-06-17.md",
      "title": "매도 디시플린 점검 — 보유 16종목 전체 적용 (2026-06-17)",
      "date": "2026-06-17",
      "version": null,
      "kind": "매도원칙",
      "preview": "각 종목: 산 이유 → 지금도 유효?(O/△/X) → 발동된 매도기준 → 판정.",
      "content": "# 매도 디시플린 점검 — 보유 16종목 전체 적용 (2026-06-17)\n\n> 출처 영상: 경제사냥꾼 **\"주식에서 '매도 시점'이 진짜 중요한 이유\"** (2026-06-16, 15:05) — 종목 추천 영상 아님, **매도 프레임워크** 영상.\n> 핵심 명제: **\"매도 = 고점 맞추기가 아니라, 내가 산 이유가 아직 살아있는지 확인하는 기술.\"** 가격이 아니라 '이유'를 본다.\n> 시세: KR=6/17 마감 / US=6/16 종가. 원가=master.md. **투자 자문 아님 — 최종 결정은 정훈.**\n\n---\n\n## 영상 요약 — 월가 매도 6기준 (Merrill/BofA·Fidelity·Morgan Stanley 2026 자료)\n\n| # | 기준 | 한 줄 |\n|---|---|---|\n| 1 | **투자 논리 깨짐** | 산 이유(수요·주문·이익률)가 틀렸을 때. **가격이 빠져서가 아니라 이유가 깨져서 판다** |\n| 2 | **비중 과대 → 리밸런싱** | 한 종목이 계좌를 흔들 만큼 커지면 좋은 종목이라도 일부 트림 |\n| 3 | **시나리오(재료) 소진** | 기대한 실적/이벤트가 이미 나왔고 주가에 반영됐으면 정리 (좋은 뉴스에 안 가면 = 선반영) |\n| 4 | **더 좋은 기회** | 기대수익 더 높은 곳으로 갈아타기 (손실 아니어도 OK) |\n| 5 | **경쟁·거시 환경 변화** | 회사는 그대로라도 금리·경기·원자재가 판을 바꾸면 |\n| 6 | **현금 필요(생활자금)** | 생활비로 투자하면 최악 타이밍에 강제 매도 |\n\n**추가 원칙 (영상 후반)**:\n- ⛔ **폭락 패닉셀 = 최악**: S&P 최고의 10일 놓치면 수익 반토막, \"가장 무서운 날 옆에 가장 좋은 날\". 코스피 6/8 −8% 서킷 → 6/9 반등 8,000 회복 사례.\n- ✅ **좋은 손절 = 성공 / 나쁜 익절 = 실패**: 판 가격이 아니라 **판 이유가 맞았는지**로 평가.\n- ✅ **분할 매도 = 후회 분산** (예: 1차 30% 확정 → 2차 30% 실적 확인 → 40% 장기논리 살아있으면 끌고가기).\n- ⚠️ **자동 손절(스톱) = 보험이지 방패 아님** (갭·휩쏘로 저점 체결 위험).\n- 📚 처분효과(Disposition Effect, Odean 1998): 수익은 빨리 팔고 손실은 오래 들고 가는 본능이 손해.\n\n> 💡 실전 질문 단 하나: **\"내가 이 주식을 처음 산 이유가 지금도 그대로인가?\"** → YES면 흔들려도 버티고, NO면 플러스든 마이너스든 정리 검토.\n\n---\n\n## 보유 16종목 매도 디시플린 매트릭스\n\n각 종목: **산 이유 → 지금도 유효?(O/△/X) → 발동된 매도기준 → 판정.**\n판정: 🟢홀딩(이유 살아있음) · 🟡분할트림(기준3/2 발동) · 🔴정리검토(이유 약함/기준4)\n\n### 국내 5\n\n| 종목 | 현재가/수익률 | 산 이유 | 유효? | 발동 기준 | 판정 |\n|---|---|---|---|---|---|\n| **삼성전자** | 346,500 / +31.75% | HBM4 엔비디아·AMD 인증·양산 | **O** | — | 🟢 **홀딩(코어)**. 이유 멀쩡 = 외인 매도·셀오프는 '흔들림'. 매수존 295~305k 눌림서 추가 |\n| **LG전자** | 234,500 / **+51.10%** | 액냉 CDU·NVIDIA DSX 동맹 | **O** | **③ 밸류 컨센 초과** | 🟡 **홀딩(트림 불가)**. 기준상 일부 트림 신호지만 **1주뿐 → 분할 불가**, 손절선 폐기 → 펀더 훼손 시에만 |\n| **두산로보** | 106,200 / +6.20% | 피지컬AI 순수플레이 | **△** | **① 데이터 취약**(적자·PSR219) | 🟡 **모멘텀 트레이딩**. 산 이유가 '실적'이 아닌 '테마' → 큰 갭업 시 분할 차익(기준3), 코어 아님 |\n| **현대차** | 618,000 / −1.90% | 보스턴다이내믹스 휴머노이드 | **O** | **⑤ 본업 관세·EV** | 🟢 **홀딩**. 로봇 이유 살아있음(아틀라스 2028), 본업은 환경리스크지 논리붕괴 아님. 80만 여지 |\n| **NAVER** | 243,500 / −2.79% | 플랫폼+젠슨황 AI팩토리 | **X** | **①④ 이유 약함+더좋은대안** | 🔴 **정리검토 1순위**. \"플랫폼 신뢰 낮음·랠리 소외\" = 산 이유 흔들림. **−2.79% 손실이라 못 파는 건 처분효과** — 이유로 판단 |\n\n### 미국 11\n\n| 종목 | 현재가/수익률 | 산 이유 | 유효? | 발동 기준 | 판정 |\n|---|---|---|---|---|---|\n| **NVDA** | $207.41 / +3.96% | AI 칩 1등·Rubin 2배 | **O** | **② 비중 최대** | 🟢 **홀딩(코어)**. $25B 채권=논리 강화. 단 이미 최대비중 → 신규추가 절제(기준2 인식) |\n| **META** | $600.21 / −5.33% | AI광고+구독, 목표 +38% | **O** | — | 🟢 **홀딩+매수1순위**. 손실이나 이유 멀쩡 = '흔들림'. 비둘기 시 3차 |\n| **MSFT** | $393.83 / −3.99% | Azure +40%·AI런레이트 | **O** | — | 🟢 **홀딩(컴파운더)**. 이유 견고, 손실은 흔들림 |\n| **GOOGL** | $373.25 / −3.73% | Cloud +63%·백로그 $460B | **O** | — | 🟢 **홀딩**. 반독점은 노이즈, 이유 살아있음 |\n| **ANET** | $168.01 / +3.67% | AI fabric $3.5B 상향 | **O** | — | 🟢 **홀딩**. AI 네트워크 논리 유지 |\n| **AVGO** | $376.71 / −10.53% | AI ASIC, AI매출 +200% | **△** | **① 가이던스 미스**(6/3) | 🟢 **홀딩**, 추가매수 신중. AI매출 성장=이유 살아있으나 FY26 가이던스 미상향=재료 약화. '흔들림/위험' 경계선 → 6/24 MU로 재확인 |\n| **AAPL** | $299.24 / **+16.37%** | (방어주) | **△** | **③ 목표 근접**(+5%)·Siri 한계 | 🟡 **분할 차익 후보**. 컨센 목표 거의 도달 + 자체LLM 한계 = 시나리오 상방 제한. 일부 트림 검토 |\n| **TSLA** | $404.66 / −4.22% | Optimus 7~8월 생산 | **O** | **③ 목표 근접**(+3.5%) | 🟢 **홀딩(소액)**. Optimus 재료 대기 중 = 시나리오 진행형, 소액이라 트림 실익 적음 |\n| **ORCL** | $188.33 / **−18.87%** | RPO $638B 클라우드 백로그 | **△** | **① 희석 우려** | 🟢 **홀딩(패닉셀 금지)**. **최대 손실이지만 RPO 백로그=산 이유 살아있음 = '흔들림'.** 단 OpenAI 집중·희석 논리가 깨지면 그때 정리(기준1). 신규매수는 보류 |\n| **MU** | $1,020.76 / **+36.28%** | HBM 슈퍼사이클 | **O** | **③ 재료 소진 임박**(목표 −15% 초과+6/24 실적) | 🟡 **분할 매도 1순위**. 현재가가 컨센 목표 초과 + 6/24 실적=재료 정점. **영상 분할 매도 정석: 절반 차익(+36% 확정), 절반 실적 베팅** |\n| **VOO** | $689.75 / +6.87% | S&P 코어 적립 | **O** | — | 🟢 **적립 홀딩**. 패닉셀 절대 금지 대상(영상 핵심 데이터) |\n\n---\n\n## 🎯 영상 적용 결론 — 액션 요약\n\n**1. 분할 매도(트림) 신호 = 기준3 '재료 소진'**\n- **MU (1순위)**: 현재가 컨센 목표 초과 + 6/24 실적 임박 → **절반 차익이 영상 분할매도 정석**(+36% 확정, 절반은 실적 베팅). 가장 명확.\n- **AAPL**: 컨센 목표 +5% 근접 + Siri 자체LLM 한계 → 상방 제한, 일부 트림 검토.\n- **두산로보**: 산 이유가 데이터 아닌 테마(적자·PSR219) → 큰 갭업 시 차익(모멘텀).\n- **LG전자**: 밸류 컨센 초과(+51%)지만 1주뿐이라 분할 불가 → 펀더 훼손 시에만.\n\n**2. 정리 검토 = 기준1·4 '이유 약함/더 좋은 대안'**\n- **NAVER (유일)**: 산 이유(플랫폼 신뢰)가 흔들림 + 반도체라는 더 좋은 대안 → **−2.79% 손실이라 못 파는 건 처분효과.** 가격 아닌 이유로 정리 검토.\n\n**3. 패닉셀 금지 = 손실이지만 '이유 살아있음' (영상 최重 메시지)**\n- **ORCL (−18.9%)·META (−5.3%)·AVGO (−10.5%)·MSFT·GOOGL**: 전부 손실이나 산 이유 멀쩡 = '흔들림이지 위험 아님'. **특히 ORCL 최대손실이라 던지고 싶은 충동이 처분효과** — RPO 백로그 살아있으면 버티고, 희석 논리 깨질 때 정리.\n- ⚠️ **6/18 FOMC 매파/엔캐리 변동성에 보유 전체를 던지지 말 것** — \"가장 무서운 날 옆에 가장 좋은 날\"(코스피 6/8→6/9 사례). 기준 따라 조정, 공포로 청산 금지.\n\n**4. 비중 과대 인식 = 기준2**\n- **NVDA**: 이미 최대 비중 → 좋은 종목이라도 신규 추가 절제(리밸런싱 인식).\n- 집중도 경고: 삼성·NVDA·MU·AVGO = HBM/메모리 단일테마 → 한 뉴스에 동반락(6/16 셀오프) = 사실상 단일 포지션. 6/24 MU가 공통 트리거.\n\n**5. 자동 손절(스톱) 신중**: LG전자 손절선 폐기 원칙과 정합 — 스톱은 보험이지 판단 대체 아님. 코어는 이벤트 확인형 트림/재진입(손절 트리거 아님).\n\n---\n\n### 영상 vs 정훈 룰 — 정합성 체크\n| 영상 원칙 | 정훈 기존 룰 | 정합 |\n|---|---|---|\n| 산 이유 점검 매도 | 코어=이벤트 확인형 트림/재진입(손절 아님) | ✅ 동일 |\n| 폭락 패닉셀 금지 | \"공포에 사라\"(역발상 분할) | ✅ 동일 |\n| 분할 매도 | MU 절반 차익·3분할 트랜치 | ✅ 동일 |\n| 더 좋은 기회 갈아타기 | NAVER 정리후보·현금 META/AVGO 집중 | ✅ 동일 |\n| 데이터로 산 이유 점검 | 데이터 우선 원칙(두산로보=모멘텀) | ✅ 동일 |\n\n→ **영상은 정훈의 기존 투자철학·룰을 외부 권위(월가 자료)로 재확인.** 새 충돌 룰 없음. 가장 실천적 변화는 **NAVER 정리검토 격상 + MU 절반차익 명확화 + ORCL 패닉셀 경계.**\n\n---\n\n*투자 자문 아님. 모든 레벨은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "holdings_final_2026-06-17",
      "file": "docs/reports/holdings_final_2026-06-17.md",
      "title": "📊 정훈 종목 최종 보고 — 보유 16 + 워치 (FAB10 + 매도 디시플린)",
      "date": "2026-06-17",
      "version": null,
      "kind": "보유확정",
      "preview": "월가가 갈아타는 FAB10(Mag7+SpaceX·OpenAI·Anthropic) / AI Big10(Mag7+AVGO·AMD·MU) — 정훈은 이미 그 리더 8개(NVDA·META·MSFT·AAPL·GOOGL·TSLA·AVGO·MU)를 손에 쥐고 있다",
      "content": "# 📊 정훈 종목 최종 보고 — 보유 16 + 워치 (FAB10 + 매도 디시플린)\n> KR=6/17 마감 / US=6/17 라이브 / 환율 1,515원 · 목표=consensus.py·증권사 · 투자 자문 아님\n\n## 🏆 한 줄 프레임\n월가가 갈아타는 **FAB10**(Mag7+SpaceX·OpenAI·Anthropic) / **AI Big10**(Mag7+AVGO·AMD·MU) — **정훈은 이미 그 리더 8개(NVDA·META·MSFT·AAPL·GOOGL·TSLA·AVGO·MU)를 손에 쥐고 있다.** 좇을 때가 아니라 정리할 때. 매도 기준 = *\"산 이유가 살아있나\"*.\n\n---\n\n# 1️⃣ 보유 16종목\n\n| 종목 | 현재가 | 수익률 | 목표가 | 상승여력 | FAB10 | 액션 |\n|---|---|---|---|---|---|---|\n| **NVDA** | $207.80 | +4.2% | $299 | +44% | 🏅대장 | 홀딩(비중관리) |\n| **META** | $585.33 | −7.7% | $827 | **+41%** | 🏅 | 🟢추가1순위 |\n| **MSFT** | $387.45 | −5.5% | $561 | **+45%** | 🏅 | 🟢홀딩+눌림추가 |\n| **GOOGL** | $366.60 | −5.4% | $433 | +18% | 🏅 | 🟢홀딩 |\n| **AVGO** | $394.42 | −6.3% | $522 | +32% | AI Big10 | 🟢신중추가 |\n| **MU** | $1,038 | **+38.6%** | $867 | **−16%** | AI Big10 | 🟡절반차익(6/24) |\n| **AAPL** | $300.31 | +16.8% | $313 | +4% | 🏅 | 🟡일부트림 |\n| **TSLA** | $401.10 | −5.1% | $421 | +5% | 🏅 | 🟡홀딩(상방제한) |\n| **ANET** | $165.83 | +2.3% | $189 | +14% | AI인프라 | 🟢홀딩 |\n| **ORCL** | $188.79 | **−18.7%** | $253 | +34% | AI인프라 | 🟢패닉셀금지 |\n| **VOO** | $691.02 | +7.1% | 인덱스 | — | — | 🟢적립 |\n| **삼성전자** | 346,500원 | +31.8% | 480,000~530,000원 | +38~53% | — | 홀딩 |\n| **LG전자** | 234,500원 | **+51.1%** | 120,000~230,000원(초과) | — | — | 🟡홀딩(1주·분할불가) |\n| **현대차** | 618,000원 | −1.9% | 600,000원(공격 800,000원) | +30% | — | 🟡홀딩 |\n| **두산로보** | 106,200원 | +6.2% | 극단분산 | — | — | 🟡모멘텀(갭업차익) |\n| **NAVER** | 243,500원 | −2.8% | 약 300,000원 | +23% | — | 🔴정리검토 |\n\n### 🔍 핵심 종목만 콕\n\n**🟢 META — 추가 1순위**\n```\n$585.33 / −7.7% · 목표 $827 (+41%) · strong_buy\n산 이유(AI광고+구독): 살아있음 → 손실은 '흔들림이지 위험 아님'\nFAB10 핵심인데 낙폭 가장 깊음 = 저가 매력\n액션: 6/18 🟢비둘기 시 소수점 추가 1순위 ⭐⭐⭐⭐⭐\n```\n\n**🟡 MU — 절반 차익 1순위**\n```\n$1,038 / +38.6% · 목표 $867 → 현재가가 이미 초과(−16%)\n6/24 실적 D-7 = 영상이 말한 '재료 정점'\n액션: 절반 차익 확정(+38%), 절반 실적 베팅 = 분할매도 정석 ⭐⭐⭐⭐\n```\n\n**🟢 ORCL — 패닉셀 금지(가장 중요)**\n```\n$188.79 / −18.7% (최대손실) · 목표 $253 (+34%)\n산 이유(RPO 백로그 $638B): 아직 살아있음 = '흔들림'\n⚠️ 최대손실이라 던지고픈 충동 = 처분효과. 가격 아닌 이유로!\n액션: 버티되 OpenAI 희석 논리 깨지면 그때 정리. 신규매수 보류 ⭐⭐⭐\n```\n\n**🔴 NAVER — 정리검토 1순위**\n```\n243,500원 / −2.8% · 목표 약 300,000원\n산 이유(플랫폼 신뢰) 흔들림 + 반도체라는 더 좋은 대안\n⚠️ 마이너스라 못 파는 게 처분효과. 이유가 약하면 정리 ⭐⭐\n```\n\n> 나머지(NVDA 비중관리·삼성/MSFT/GOOGL/ANET 홀딩·AAPL 일부트림·LG 1주홀딩·TSLA/현대차 상방제한·두산로보 모멘텀·VOO 적립·AVGO 신중추가)는 위 표 액션대로.\n\n---\n\n# 2️⃣ 워치리스트\n\n| 종목 | 현재가 | 목표가 | 상승여력 | 지금 살까 |\n|---|---|---|---|---|\n| **SK하이닉스** | 2,521,000원 | 2,580,000원 | +2% | ⏳ ADR 8월 대기·추격금지(+5.84%↑) |\n| **두산에너빌리티** | 103,200원 | 143,000원 | +38% | ⏳ 93,000~95,000원 눌림 예약 |\n| **삼성전기** | 2,032,000원 | 2,300,000~3,000,000원 | +13~48% | ⏳ 투자경고·1,600,000~1,750,000원 눌림 |\n| **원익IPS** | 161,700원 | 160,000~180,000원 | +0~11% | ⏳ 125,000~130,000원 눌림(반등중 추격주의) |\n| **테스** | 169,400원 | 160,000~170,000원 | 근접 | ⏳ 130,000원 예약 |\n| **SK이노베이션** | 109,000원 | 테마 | 미확정 | ⏳ 관망 |\n| **한화에어로** | 1,224,000원 | 대미방산 | — | ⏳ 6/18 시행후 소화 |\n| **조선바스켓** | 한화오션 133,100원·삼성중공업 28,950원·HD현대중공업 707,000원 | 대미조선 | — | ⏳ 소화 관찰 |\n| **LG이노텍** | 1,248,000원 | FC-BGA | — | ⏳ 증설실행 관찰(PER~60배) |\n| **GE Vernova** | $1,021 | $1,212 | +19% | ✅ 소액 소수점(미국판 두산E) |\n| **STM** | $75.00 | **$64** | **−15%** | ❌ ⚠️sell-side는 하향(채널 $90과 상충) |\n| **T-Mobile** | $183.76 | $261 | +42% | ⏳ 52주고가 근처·$165 조정시 |\n| **SpaceX(SPCX)** | $197.71 | $188 | −5% | ⏳ 6/30 락업·추격금지(채널 $330 과장) |\n\n### 🔍 워치 콕\n- **✅ GE Vernova** — 워치 중 유일 매수 검토. AI전력 3종(가스터빈·원전·전력망) = 미국판 두산E, 수주잔고 역대최고. $50~100 소수점 소액(FOMC 후 안전). ⭐⭐⭐⭐\n- **❌ STM** — ⚠️ 채널 \"$90·급락이 기회\"는 **sell-side 목표 $64와 정반대**. 차량반도체 수요둔화. 진입 보류. ⭐⭐\n- **⏳ 두산에너빌리티** — KUIC 1호 발표 7월·PER 203배 = 모멘텀. 93,000~95,000원 눌림 1주만, 100,000원 추격금지. ⭐⭐⭐\n\n---\n\n# 3️⃣ 💰 현금 624,771원 배분 — 두 가지 안\n\n## 🅰️ 관망안 (룰 정합·추천) ⭐\n```\n지금: 624,771원 전액 보존 (매수존 다 이탈 + 외인 매도 + FOMC 임박)\n6/18 03:00 FOMC 판정(2년물+달러인덱스):\n  🟢비둘기 → META 135,000원 + AVGO 90,000원 소수점 예약(절반 6/18밤/절반 6/22)\n  🟡중립  → META 110,000원만\n  🔴매파  → 0원, 현금 보존·안전핀 점검\n```\n\n## 🅱️ 공격안 (참고자료 스타일) ⚠️ 추격금지 위반 주의\n```\n지금 바로:\n  원화 → 달러 환전 약 $410 (@1,515)\n  달러: META $250(약 0.43주) + AVGO $150(약 0.38주) 즉시 소수점\n  원화: 두산에너빌리티 93,000~95,000원 눌림 1주 예약(약 93,000원)\n  잔여 현금 약 50,000원\n⚠️ AVGO 갭 변동·META FOMC 갭 노출 → '추격'에 해당.\n   FOMC 하루만 기다리면 같은 걸 더 확신 갖고 가능 → 🅰️ 권장\n```\n\n---\n\n# 4️⃣ 📅 핵심 일정 (2주)\n| 날짜 | 이벤트 | 대응 |\n|---|---|---|\n| **6/18(목) 03:00** | **FOMC + 워시 첫 회견** | 베이킹대로 판정→예약 |\n| 6/19(금) | 美 준틴스 휴장 | 거래공백 |\n| 6/22(월) | META 잔여 집행 | 비둘기 시 |\n| **6/24(수)** | **MU 실적** | **절반 차익** |\n| 7/16(목) | 한국은행 금통위(신현송 매파신중) | 국내 영향 |\n\n---\n\n# 5️⃣ 📋 6월 말 목표 & 액션 플랜\n\n## 🎯 6월 말 목표 자산\n**현재 총자산: 8,477,569원**\n- 미장: $3,931 × 1,515원 = **5,957,598원**\n- 국장: **1,895,200원**\n- 현금: **624,771원**\n\n| 목표 | 금액 | 필요 수익 | 현실성 |\n|---|---|---|---|\n| 🟢 현실 목표 | **8,700,000원** | +2.6% | 미장 소반등이면 도달 |\n| 🔥 도전 목표 | **9,000,000원** | **+6.2%(약 522,000원)** | META·NVDA 강반등 + 국장 모멘텀 必 |\n\n> ⚠️ 솔직히: 2주 +6.2%는 미장이 FOMC 비둘기로 강하게 튀어야 가능. **목표는 동기부여용 — 무리한 추격으로 맞추는 건 룰 위반.**\n\n## 💡 6월 전략 핵심 3가지\n**1. FAB10 코어 유지** — 이미 AI 리더 8개 보유. 장기 사이클(2028~29 피지컬AI) 단기 조정은 소음. 코어(NVDA·삼성·MSFT·META·VOO) 홀딩.\n**2. FOMC 현금 관리** — 624,771원은 FOMC 한 장 보고 투입. 비둘기면 손실 깊은 META·AVGO로 평단 낮추기, 매파면 보존. 지금 선투입(추격) 금지.\n**3. 정리 디시플린** — MU 절반차익 · NAVER 이유정리 · ORCL 패닉셀금지. *\"산 이유가 살아있나\"*로 판단.\n\n## ✅ 오늘 할 것\n- 국장: 전 종목 보유 유지, 추격금지(두산에너빌리티·SK하이닉스·삼성전기)\n- 미장: 전 종목 보유, 현금 보존, **추가매수 없음(FOMC 대기)**\n\n---\n\n# 🎯 결론\n> **정훈은 이미 FAB10 리더 8개를 손에 쥐고 있다. 지금은 새로 좇을 때가 아니라 정리할 때다.** MU 절반 차익(6/24 정점)·NAVER 손절 아닌 '이유 정리'·ORCL 패닉셀 금지가 핵심. 워치에선 GEV만 소액 검토, STM은 채널 낙관론 믿지 말 것(컨센 하향). 현금 624,771원은 내일 FOMC 한 장만 보고 META/AVGO로 — **하루 기다리는 게 추격 안 하는 길.** 💪\n\n---\n*투자 자문 아님. 모든 레벨은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v16_full_2026-06-16",
      "file": "docs/reports/report_v16_full_2026-06-16.md",
      "title": "📊 정훈 PORTFOLIO DESK — 일일 통합 보고서",
      "date": "2026-06-16",
      "version": 16,
      "kind": "보고서",
      "preview": "외인 3거래일 연속 순매수 + SOX +5.45% 폭등으로 포트는 호조다(총자산 ≈ 856만 / 환차익 포함 손익 ≈ +63.5만). 그러나 6/18 FOMC + 美 네마녀의날 + 준틴스 휴장이 겹치는 변동성 구간 직전 — 신규 매수보다 ①사전 조건부",
      "content": "# 📊 정훈 PORTFOLIO DESK — 일일 통합 보고서\n## v16 · 2026-06-16 (화) · 완전판\n\n> **투자 자문 아님.** 모든 목표가·매수존·별점·예약안은 분석 참고이며 최종 결정·집행은 정훈.\n> **데이터 기준**: 토스 계좌 스크린샷(6/16 17:34, 정본) + Yahoo 무키 라이브 + 웹 교차검증.\n> **우선순위**: 토스 실데이터 > 당일 스크린샷 > Yahoo 무키 > 최신 보고서 > 마스터문서.\n\n---\n\n## 🔑 오늘의 한 줄 결론\n\n외인 **3거래일 연속 순매수** + SOX **+5.45%** 폭등으로 포트는 호조다(**총자산 ≈ 856만 / 환차익 포함 손익 ≈ +63.5만**). 그러나 **6/18 FOMC + 美 네마녀의날 + 준틴스 휴장**이 겹치는 변동성 구간 직전 — **신규 매수보다 ①사전 조건부 예약 베이킹(6/17 저녁) + ②현금 62만 보존**이 정답. 빅테크 누적 약세(ORCL −17% 등)는 *보유 누적손익*일 뿐 오늘은 전 종목 동반 강세였다.\n\n---\n\n## ⚠️ 변경점 (직전 v15 대비)\n\n1. 🆕 **토스 계좌 스크린샷 2장(국내+해외) 확보** → 보유 손익 정본 갱신. **총자산 ≈ 8,561,205원**.\n2. ⚠️ **스크린샷 % 해석 정정**: 스크린샷의 종목별 %는 **당일 등락이 아니라 누적 보유수익률(총수익)**. 오늘 실제 장세는 전 종목 강세(코스피 +2.1%, SOX +5.45%, MU 당일 +10.8%). ORCL \"−16.5%\"는 평단 대비 누적손실(당일은 +4.6%)·MU \"+48.8%\"는 누적수익. **트림/물타기 판단 시 혼동 금지.**\n3. ✅ **BOJ 0.75→1.0% 인상 확정**(6/16, 7-1 가결, 31년래 최고). 엔/달러 160 부근 소폭 강세 그침 = **엔캐리 청산 패닉 없음** → 안전핀 미발동.\n4. 🔴 **두산에너빌리티 10만 재돌파**(103,300, 트리거 발동) — 추격금지 룰 적용.\n5. 🆕 **LG이노텍 워치리스트 정식 편입**(011070.KS) — FC-BGA(AI 기판) 구조적 공급부족 테마.\n\n---\n\n## 1️⃣ 시장 — 국장 / 미장\n\n### 🇰🇷 국장 (kr-market-desk)\n\n- **코스피 8,726.60 (+2.11%) / 코스닥 1,018.68 (+2.18%)** — 6/15 폭등(+5.2%) 후 **3거래일째 상승**, 8,700선 안착. 美·이란 종전 기대 + 유가 급락발 위험선호가 동력.\n- **🔑 외국인 3거래일 연속 순매수**(당일 외인 **+1.54조**·기관 **+0.85조**, 개인 −2.33조). 24거래일 '셀코리아'(~76조) 종료 후 삼성전자·SK하이닉스 등 **반도체 대형주 재매수**.\n- **→ 강세 유지·강화**: 외인 2일→3일 연속으로 코스피 메인 엔진 정상 작동, 반도체 선취 명분 강화. **단 개인이 매물 받는 구도 → 외인 매수 둔화 시 변동성. 4일째 지속 여부가 분기점.**\n- **섹터 로테이션**: 반도체 대형주(SK하이닉스 +4.1%·삼성전기 +2.5%) + **방산 폭등(한화에어로 +9.1%)** 주도. AI로봇·소부장(원익IPS **−10.5%**·테스 −4.4%·두산로보 −2.2%)은 차익실현 급락 = \"AI로봇→AI소부장→대형 반도체\"로 관심 이동(KB증권).\n\n**📋 국내 보유 5종목 (Yahoo 6/16 종가 · 토스 교차검증 정합)**\n\n| 종목 | 현재가 | 당일 등락 | 토스 정합 | 코멘트 |\n|---|---|---|---|---|\n| 삼성전자 (005930) | 343,000 | +1.78% | 343,000 ✅ | 외인 반도체 재매수 직접 수혜 |\n| LG전자 (066570) | 234,000 | −3.90% | 235,000 ✅(±1천) | 지수 강세 속 역행(워치), 누적 +51% 코어 |\n| 두산로보틱스 (454910) | 109,000 | −2.15% | 109,400 ✅ | AI로봇 모멘텀 차익실현 |\n| 현대차 (005380) | 640,000 | −1.08% | 640,000 ✅ | 보스턴다이내믹스 IPO 임박 |\n| NAVER (035420) | 242,000 | −2.42% | 242,000 ✅ | 정리 후보 상시 검토 |\n\n**📋 국내 워치 (Yahoo 6/16)**\n\n| 종목 | 현재가 | 당일 | 코멘트 |\n|---|---|---|---|\n| 두산에너빌리티 (034020) | 103,300 | +3.51% | **10만 재돌파 — 트리거 발동, 추격금지** |\n| SK하이닉스 (000660) | 2,382,000 | +4.11% | 외인 순매수 핵심 타깃, 당일 주도주 |\n| 삼성전기 (009150) | 2,048,000 | +2.45% | AI 소부장 대장, 반도체 동조 |\n| 한화에어로 (012450) | 1,183,000 | +9.13% | 방산 주도 폭등 |\n| 한화오션 (042660) | 129,200 | +4.70% | 조선바스켓 강세 |\n| 삼성중공업 (010140) | 28,100 | −1.92% | 조선 내 혼조 |\n| HD현대중공업 (329180) | 698,000 | −2.24% | 조선 내 차익실현 |\n| 원익IPS (240810.KQ) | 156,100 | −10.54% | 상한가 후 차익실현 급락 |\n| 테스 (095610.KQ) | 169,200 | −4.41% | 소부장 동반 약세 |\n| LG이노텍 (011070) 🆕 | 1,236,000 | +2.23% | FC-BGA AI 기판 신규 편입 |\n\n### 🇺🇸 미장 (us-market-desk, 6/15 마감 기준)\n\n- **S&P500 7,554.29 (+1.65%) / 나스닥 26,683.94 (+3.07%) / 다우 51,671.03 (+0.92%) / 필반 SOX 14,099.62 (+5.45%)** — 반도체가 랠리 견인. **VIX 17 하회**(전주 23+ 피크 대비 급락) = 명확한 리스크온. 미·이란 평화(호르무즈 개방·유가↓)가 동력.\n- **FOMC 선반영 비둘기 랠리** — 6/18 03:00 결정 앞두고 위험선호 확대. 정훈 폰 미가용 시간대 → 사전 조건부 예약만 유효.\n\n**📋 미국 보유 11종목 (Yahoo 6/15 마감 · 토스 6/16 교차검증)**\n\n| 종목 | 현재가($) | 당일 | 토스 정합 | 비고 |\n|---|---|---|---|---|\n| MU | 1,087.99 | **+10.84%** | 1,115.26 ✅ | HBM 완판, **6/24 실적** make-or-break |\n| NVDA | 212.45 | +3.54% | 211.48 ✅ | 반도체 랠리 견인 |\n| ANET | 169.09 | +3.58% | 168.12 ✅ | AI 네트워킹 강세 |\n| AVGO | 393.94 | +3.11% | 394.22 ✅ | 커스텀 ASIC 분산축 |\n| META | 593.48 | +4.67% | 593.54 ✅ | 빅테크 최강 반등 |\n| GOOGL | 369.35 | +2.69% | 368.06 ✅ | capex 베타 |\n| MSFT | 399.76 | +2.31% | 399.68 ✅ | Azure 방어 |\n| AAPL | 296.42 | +1.82% | 296.64 ✅ | 온디바이스 로테이션 |\n| VOO | 693.83 | +1.74% | 693.41 ✅ | 지수 코어 |\n| ORCL | 192.64 | +4.62% | 193.64 ✅ | capex 쇼크 후 반등, **누적 −17% 미회복** |\n| TSLA | 411.15 | +1.16% | 405.11 ✅ | 상대 약세 |\n\n---\n\n## 2️⃣ 섹터 — 반도체AI / 전력·피지컬 / 빅테크\n\n### 🔬 반도체·AI인프라 (semi-ai-desk)\n\n**테마 한 줄**: HBM 슈퍼사이클 **\"검증 국면\"** — Citi가 DRAM 업턴을 2027년까지 연장(MU 목표 $840), 삼성 HBM4 엔비디아 인증 통과·2월 양산 → **3사(SK하이닉스·삼성·MU) 동반 가격 인상**. 6/24 MU 실적이 사이클 \"진짜/고점\" 가늠자.\n\n| 종목 | 정훈 손익 | 모멘텀·뉴스 | 실적/이벤트 |\n|---|---|---|---|\n| **MU** | +45.3%($1,088) | 2026 HBM 전량 완판, DRAM 가격 인상. 가이던스 매출 ~$33.5B±0.75B, EPS ~$19.15, GM ~81% | **6/24 실적(D-8)** ← 절반 차익 검토 |\n| **삼성전자** | +30.4%(343,000) | HBM4 엔비디아/AMD 인증·2월 세계최초 양산. 6/8 젠슨황 서울회동→HBM4E·파운드리(LP40) | Q3 테일러팹 매출 반영 |\n| **NVDA** | +6.5% | Vera Rubin용 HBM4 멀티소싱(삼성·SK), 차세대 수요 견조 | — |\n| **AVGO** | −6.4% | 커스텀 ASIC(XPU) 매출 YoY **+106%**($8.4B), 시장 ~70% 점유(구글 TPU·메타 MTIA) | 메모리 비의존 분산축 |\n| **ANET** | +4.3% | 2026 AI 네트워킹 가이던스 $2.75B→**$3.25B 상향**, 하이퍼스케일러 capex 가속 | — |\n\n**컨센서스 / 괴리**: MU Citi 목표 **$840**(현재가 $1,088이 이미 초과 → 서프라이즈 선반영, 목표 추가 상향 없으면 −25% 고평가 플래그). Wall St Q3 EPS 컨센 $19.95(YoY +942%). **PM: MU 절반 차익(6/24 후)이 집중도 완화 1차 수단. 추격 아닌 차익 관점이 정합.**\n\n**워치**: SK하이닉스 미 ADR 정식상장 **8월 목표**(SEC 승인 **6/22주** 가능성, 조달 최대 $14B). 상장 전 OTC(HXSCL)/국장소수점 비추 → **8월 정식상장 후 진입**.\n\n### ⚡ 전력·인프라·피지컬AI (power-physical-desk)\n\n**테마 한 줄**: **대미투자특별법 6/18 시행 임박** — 원전(두산E)·조선(빅3)·SMR 동시 수혜, AI 전력난과 결합해 섹터 리레이팅 지속.\n\n| 종목 | 정훈 손익 | 분류 | 오늘 포인트 |\n|---|---|---|---|\n| **LG전자** | **+50.8%**(235k) | 코어 | **NVIDIA CDU 인증 최종 단계**(미확정 보도), 냉각용량 650kW→**1.4MW**, GRC·SK엔무브 협업, DCW 2026 HVAC. **펀더 훼손 없음 → 손절선 폐기 룰 유지** |\n| **두산로보틱스** | +9.0% | **모멘텀** | 협동로봇 글로벌 Top4, 옵티머스 양산 수혜이나 직접 수주 연결고리 미확인. 추격 경계 |\n| **현대차** | +1.6% | 코어 | 보스턴다이내믹스 IPO 임박(6월 풋옵션), KB 목표 **120만**·유진 100만 |\n| **TSLA** | −2.7% | 코어 | 옵티머스 생산 7월말~8월 초(6월 아님), 모델S/X 라인 전환 |\n\n**워치**: 두산에너빌리티 103,300(10만 재돌파), 2026 신규수주 목표 **13.4조** + 대미투자법 직접 수혜 / GE Vernova 가스터빈 백로그 **100GW 돌파**(1Q 수주 $18.3B +71%) / SK이노 테라파워 SMR / 조선 빅3+한화에어로 대미투자 조선 **$1,500억**(MASGA, 수익 100% 한국 귀속).\n\n### ☁️ 빅테크·플랫폼 (bigtech-platform-desk)\n\n**테마 한 줄**: 빅테크 누적 약세 = **\"AI capex 청구서\" 트레이드** — ORCL capex/차입 가이던스가 META·GOOGL·MSFT로 ROI 회의론 전염. 반면 AAPL은 \"저capex·온디바이스\" 안전자산 반사 수혜.\n\n| 종목 | 정훈 손익 | 배경 | 컨센 목표 | 실적 |\n|---|---|---|---|---|\n| **ORCL** | **−17%**($193) | Q4 호실적(RPO $638B/+363%·OCI +93%)에도 capex FY26 $55.7B→FY27 **$70B** + **$40B 차입** 부담 + 소송 probe | **$253.5(+38%)** | 9월경 |\n| **META** | −6.4%($593) | capex 가이 **$145B**(2배)에 ROI 회의, 컨센 큰 상방 | **$827(+39%)** | Q2 7월말 |\n| **GOOGL** | −4.7%($369) | capex 그룹 동반 매도, 펀더 견조 | $433(+17%) | Q2 7월말 |\n| **MSFT** | −2.6%($400) | CY26 capex ~$190B, Azure 수익화로 상대 방어 | $561(+40%) | Q4 7월말 |\n| **AAPL** | **+15.3%**($296) | WWDC Siri AI(Gemini)·온디바이스 → 로테이션 수혜 | $313(+5%) | Q3 7월말 |\n| **NAVER** | −3.4%(242k) | 52주 고점 −25%, AI 광고 수익화 하반기 대기, 커미션 압박 | — | Q2 8월초 |\n\n**워치**: SPCX 6/12 $135→$160.95(+19.2%), 나스닥100 패스트트랙 편입 ~7/1·락업 12월 만료(양방향) / TMUS 스타링크 D2C(신규 트리거 미확인).\n\n---\n\n## 3️⃣ 매크로 데스크 (macro-desk)\n\n- **환율 USD/KRW 1,506.48 (−0.62%, 원화 강세)** — 전일 1,515.87→절상. 외인 환차익 우호(순매수 흐름 정합). 美 보유주 원화 환산단가는 소폭 하향.\n- **금리 ① BOJ 6/16 0.75→1.0% 인상 확정**(7-1, Asada 동결 반대, 31년래 최고). 엔/달러 160 부근 소폭 강세 그침 = **엔캐리 청산 패닉 없음** → 안전핀(7,500) 미발동.\n- **금리 ② FOMC 6/18 03:00 동결 ~97%**(CME FedWatch) + **워시 의장 첫 회견** + 점도표. CPI 5월 **+4.2%**·core +2.9%·에너지 +23.5% = 매파 리스크(연내 1회 인상 확률 ~70%로 상승). **한은 점도표 없음**(연준 전용).\n- **지표·유가**: 다음 CPI = **7/14**(이번 사이클 밖). 유가 브렌트 **$84~87**, 이란 평화협정 6/19 스위스 서명 예정 → 서명 시 $80 하향 = CPI 에너지 경로 둔화 우호.\n\n### 📅 이벤트 캘린더 (2주)\n\n| 날짜(KST) | 이벤트 | 폰 가용 |\n|---|---|---|\n| 6/16(화) | **BOJ 1.0% 인상 (완료)** | 확인됨 |\n| **6/18(목) 03:00** | **FOMC 동결+점도표+워시 회견** / 대미투자법 시행 / 美 네마녀의날 / ACN 실적 | ❌ 야간 — **사전 예약 베이킹 필수** |\n| 6/19(금) | 美 준틴스 **휴장** / 이란 협정 서명 예정 / 워치 유예종목 자동 제외 마감 | 미국장 휴장 |\n| 6/22 주간 | SK하이닉스 미 ADR SEC 승인 가능성 | — |\n| 6/24(수) | **MU 실적** (절반 차익 검토) | ❌ 야간 |\n| 7/14(월) | 美 6월 CPI | ❌ 야간 |\n| 7/16(목) | 한국은행 금통위 | — |\n\n---\n\n## 4️⃣ 리서치 피드 — 경제사냥꾼 (research-feed)\n\n6/15~6/16 신규 영상 4 + 쇼츠 2 수집(봇차단 없음). 핵심 수치 전부 웹 교차검증.\n\n| 주장 | 분류 | 비고 |\n|---|---|---|\n| **[영상 Ixr9VLOrgIw]** FOMC 6/17(결정) 동결 98%+, 워시 첫 회의·점도표/가이던스 축소→중립 전환 | **[검증]** | 정훈 6/18 03:00 트리거 룰과 직결 |\n| 물가 4.2%는 유가發 공급인플레 → 호르무즈 재개 시 후행 둔화, 방향은 인하 | **[검증/보강]** | **단 시장 12월 인상 확률 42% 반영 — 단기 매파 리스크 = 안전핀 유지 근거** |\n| 이란 휴전 \"6/19 금요일 서명\" 특정 | **[정정주의]** | 실제 60일 휴전 MOU·호르무즈 30일내 개방, 트럼프 최종승인 단계. 특정일 미확인 |\n| SPCX 공모 $135→첫날 $160.95(+19.2%), 미래에셋 0주 배정 | **[검증]** | 마스터 영구교정과 일치. 락업·나스닥 조기편입 모니터 |\n| SPCX 미래에셋 본사 270만주 코너스톤 = \"골드만\" | **[정정]** | 실제 주체 **모건스탠리**(공동주관), 금감원 이해상충 조사 중 |\n| LG이노텍 2분기 영익 \"2,028억·18배\" | **[정정]** | 실제 KB 컨센 **1,787억·약 +15.7배**. 방향(역대급·1조클럽 복귀)은 검증 |\n| LG이노텍 FC-BGA = AI 기판 구조적 공급부족, 美 4개+ 고객 증설 요청 | **[검증]** | 🆕 **워치 정식 편입** — 추격 아닌 관찰(증설 실행력·수율 관건) |\n| G7 1년 테마(핵심광물·방산), 종전 기대 시 방산 차익실현 | **[방향성]** | 한화에어로·조선바스켓 단기 변동성 주의 |\n\n- **신규 입력 없는 항목**: BOJ 인상·두산E·SK이노 SMR·삼성/SK하이닉스 HBM·대미투자법(6/18)은 6/15~16 신규 영상에서 직접 다룬 콘텐츠 없음(G7 영상서 방산만 간접 언급).\n\n---\n\n## 5️⃣ 리스크 데스크 (risk-desk)\n\n- 🚦 **안전핀**: 코스피 8,727 vs 7,500 = **+16.4% 여유**. 동결 사유 없음.\n- 🚦 **2차 트랜치 게이트**(8,000): \"이란 결렬 + 8,000 하회\" 동시조건 → 현 시점 발동 불가.\n- 🟢 **매수존**: NAVER 242,000(존 225~235k 위 +3%)·삼성전자 343,000(존 295~305k 위 +12.5%) — **둘 다 매수존 위, 미진입.** 추격 금지.\n- 🔴 **두산E 10만빌리티 발동**(103,300, +3.3%) — 워치라 보유영향 없으나 추격금지.\n- **집중도 경고**: 메모리·AI 반도체가 **NVDA(최대비중)+MU+삼성** 3중 중첩, SK하이닉스 8월 상장 시 4중. 동반 급등은 동반 손실로도 온다. 미국 11종목 전부 **원/달러 단일 환노출**(평단환율 ~1,456)도 누적. **빅테크(META·MSFT·GOOGL·ORCL·AAPL)는 평단 부근 → 3차 트랜치를 빅테크에 쓰면 분산보다 집중도만 키울 수 있음.**\n- **신중(bear) 관점**: 코스피 8,700·SOX 14,000은 이틀 만의 외인 전환에 올라탄 **급등 직후 고점권**. ①BOJ 인상발 엔캐리 청산 ②FOMC 매파 시 밸류 비싼 AI·반도체(특히 +45% MU)부터 되돌림 ③외인 순매수 \"2~3일\"은 숏커버·리밸런싱 가능성 배제 못 함. 골드만 EPS +300%는 아직 전망. → **오늘 폭등은 매수 근거가 아니라 미집행 현금 62만원을 지킬 이유.**\n\n---\n\n## 6️⃣ 강세 vs 신중 디베이트\n\n- **🟢 강세**: 외인 3거래일 연속 순매수(누적 ~4.8조)로 코스피 메인 엔진 정상 가동, 반도체 선취 명분 강화. SOX +5.45%·MU HBM 완판으로 AI 메모리 슈퍼사이클 실수요 확인. BOJ 인상에도 엔캐리 무탈, 유가 급락 + FOMC 동결 우세 = 위험선호 지속. LG전자(+51%)·삼성(+30%)·MU(+45%) 코어가 포트를 끌어올림.\n- **🔴 신중**: 이틀 폭등 후 고점권, 외인 전환은 아직 추세 미확정(숏커버 가능성). FOMC 매파(워시 첫 회견·점도표)·6/18~19 네마녀+준틴스 유동성 공백이 겹치는 변동성 구간. 빅테크 capex ROI 회의(ORCL −17%)가 광범위. MU는 Citi 목표 초과 = 실적 서프라이즈 선반영. → **추격 자제, 현금 보존, 이벤트 확인 후 대응.**\n\n---\n\n## 7️⃣ PM 종합 (최종)\n\n### 📊 보유 16종목 (현재가=토스 6/16 / 수익률=원가 고정 / 목표·괴리=컨센)\n\n| 종목 | 현재가 | 수익률 | 컨센 목표 | 매수존 | ⭐ | 코멘트 |\n|---|---|---|---|---|---|---|\n| LG전자 | 235,000 | **+50.8%** | — | — | ⭐⭐⭐⭐⭐ | 최고 코어, CDU 인증 모멘텀, 손절선 폐기 유지 |\n| 삼성전자 | 343,000 | **+30.4%** | — | 295~305k | ⭐⭐⭐⭐ | HBM4 코어, 외인 순매수 직접 수혜 |\n| MU | $1,088 | **+45.3%** | $867 | — | ⭐⭐⭐⭐ | 6/24 실적·절반 차익 검토, 목표 초과 |\n| AAPL | $296 | +15.3% | $313 | — | ⭐⭐⭐ | 온디바이스 로테이션, 목표 근접 |\n| VOO | $694 | +7.5% | — | — | ⭐⭐⭐⭐ | 지수 코어 |\n| NVDA | $212 | +6.5% | $299 | — | ⭐⭐⭐⭐⭐ | AI 코어, 상방 +41% |\n| 두산로보 | 109,400 | +9.0% | — | — | ⭐⭐⭐(모멘텀) | 차익실현 식음, 트레이딩 대상 |\n| ANET | $169 | +4.3% | $189 | — | ⭐⭐⭐⭐ | AI 네트워킹 가이던스 상향 |\n| 현대차 | 640,000 | +1.6% | KB 120만 | — | ⭐⭐⭐ | BD 로봇 IPO 임박 |\n| TSLA | $411 | −2.7% | $421 | — | ⭐⭐⭐ | 옵티머스 7~8월 |\n| MSFT | $400 | −2.6% | $561 | — | ⭐⭐⭐⭐ | Azure 방어, 상방 큼 |\n| NAVER | 242,000 | −3.4% | — | 225~235k | ⭐⭐ | 정리 후보 상시 검토 |\n| GOOGL | $369 | −4.7% | $433 | — | ⭐⭐⭐⭐ | capex 베타 약세, 펀더 견조 |\n| META | $593 | −6.4% | $827 | — | ⭐⭐⭐⭐ | FOMC 비둘기 시 재매수 1순위 |\n| AVGO | $394 | −6.4% | $522 | — | ⭐⭐⭐⭐ | 커스텀 ASIC 분산축 |\n| ORCL | $194 | **−17.0%** | $253.5 | — | ⭐⭐⭐ | capex/차입 부담, 추격금지·소화 후 |\n\n### 💰 자산 합계 (원가 고정 기준선, 토스 실손익이 정본)\n\n| 항목 | 금액 |\n|---|---|\n| 국내 평가액 | 1,911,900원 (손익 +250,200, +15.0%) |\n| 미국 평가액 | $3,999.20 ≈ 6,025,434원 (손익 +$127.43) |\n| 현금 | 624,771원 + $1.11 |\n| **총자산** | **≈ 8,561,205원** |\n| 주식 평가손익(원가) | +441,299원 |\n| 주식 평가손익(환차익 반영, 평단환율 1,456.5) | **≈ +635,507원** |\n\n### 🎯 워치리스트 (활성)\n\n| 종목 | 현재가 | 코멘트 |\n|---|---|---|\n| 두산에너빌리티 | 103,300 | **10만 재돌파 트리거**, 대미투자법 수혜, 추격금지 |\n| SK하이닉스 | 2,382,000 | 외인 순매수 핵심, 미 ADR 8월 상장 — 상장 후 진입 |\n| 삼성전기 | 2,048,000 | AI 소부장 대장, 반도체 동조 |\n| 한화에어로 | 1,183,000 | 방산 +9% 폭등, 대미투자 직결 |\n| 조선바스켓 | 한화오션 129,200 외 | 대미투자 조선 $1,500억, 6/18 후 소화 |\n| 원익IPS/테스 | 156,100 / 169,200 | 소부장 차익실현, 눌림 관찰 |\n| GEV / SK이노 | $979 / — | AI 전력·SMR, 백로그 100GW |\n| SPCX / TMUS | $192.5 / $189 | 나스닥100 편입 ~7/1, 락업 12월 |\n| **LG이노텍** 🆕 | 1,236,000 | FC-BGA AI 기판 공급부족, 관찰 |\n\n### ✅ 제안 액션\n\n- **기본 = 홀딩 + 관망.** 오늘 신규 매수 없음(전 종목 매수존 위, 급등 직후 고점권 + 이벤트 직전).\n- **6/17(수) 17:30~20:50 사전 베이킹**: 3차 트랜치(~22.5만) 조건부 예약 — 🟢동결+중립 시 META·AVGO 소수점 / 🔴매파 시 보류.\n- **MU 6/24 실적 후 절반 차익** 검토(현재가 Citi 목표 초과, 집중도 완화).\n- **6/18~19 네마녀+준틴스**: 신규 미장 진입 회피, 예약분만 개장 직후 체결.\n\n### 💵 현금 배분 플랜 (잔액 624,771원, 3분할 전부 미집행)\n\n| 트랜치 | 한도 | 조건 | 현 상태 |\n|---|---|---|---|\n| 1차 | ~10~15만 | NAVER 225~235k 또는 삼성 295~305k 눌림 | 둘 다 존 위, 대기 |\n| 2차 | ~20만 | 코스피 8,000 하회 + 이란 결렬 | 미충족 |\n| 3차 | ~22.5만 | FOMC 확인 후 META·AVGO 소수점(비둘기)/보류(매파) | 6/17 베이킹 |\n\n### 👀 지켜볼 것\n\n1. **외인 4일째 순매수 지속 여부** (끊기면 강세 논지 약화 = 신중 전환).\n2. **6/18 03:00 FOMC** — 점도표·워시 톤 → 3차 트랜치 분기.\n3. **두산E 10만 안착 vs 되돌림** (추격금지).\n4. **MU 6/24 실적** → 절반 차익 판단.\n\n---\n\n## 8️⃣ 선택지 상세 분석 — ① ORCL ③ FOMC 예약 ④ 두산에너빌리티\n\n### ① ORCL −17% — 추가 하락 vs 매수기회?\n\n**현황**: 현재가 $192~194 / 평단 $232.12 / 보유 0.215주($41.66, 극소) / 누적 −17%.\n\n**왜 빠졌나 (펀더 훼손 아님 — capex 청구서 쇼크)**: 6/10 FY26 Q4 호실적(EPS $2.11 vs 컨센 $1.89 +11.6%, 매출 +21%, OCI +93%, **RPO $638B +363%**)에도 주가 −13% → **자금조달 부담**(capex FY26 $55.7B→FY27 **$70B**, **$40B 조달**($20B 주식), FY26 FCF **−$23.7B**, 감가상각 2배 $7.62B) + 소송 probe. 6/15 +6% 반등($194)했으나 누적 낙폭 미회복.\n\n**밸류·컨센**: 52명 평균 목표 **$251.66(+31% 상방)**, Buy 우위. 실적 후 다수 목표 유지/상향(Scotiabank만 $290→$241). 기술적 **$194 지지·$250 저항**.\n\n**PM 판단 — 지금 물타기 비권장(추격금지 룰3)**: 떨어지는 칼날 + FOMC 직전 + 현금은 트랜치로 묶임(ORCL 물타기는 3차 용도 아님). **보유분(극소) 홀딩, 알림만, FOMC 후 재평가.**\n\n| 단계 | 관심 레벨 | 조건 |\n|---|---|---|\n| 1차 관찰 | **$180~185** | FOMC·실적후폭풍 소화 + 일봉 안정(반등 추격 금지) |\n| 2차 | **$168~172** | 직전 갭 지지대 재테스트 |\n| 3차 | **$150~158** | 과매도·컨센 괴리 +60% 구간 |\n\n### ③ FOMC 6/18 03:00 — 3차 트랜치 사전 예약 세팅\n\n**전제**: 03:00 = 폰 미가용 → **6/17(수) 17:30~20:50 토스 미국주식 소수점(금액) 예약**만 가능. ⚠️ 소수점=**시장가 체결** → 6/18 개장(22:30) 갭 노출, **22:25~22:30 취소 불가**. 한도 ~225,000원 ≈ $149. META $593.48 / AVGO $393.94.\n\n| 시나리오 | 액션 |\n|---|---|\n| 🟢 **비둘기**(동결+\"추가조정\" 삭제→중립/점도표 완만) | **A(룰)**: META 115,000원(~0.128주) + AVGO 110,000원(~0.185주) / **B(분산 대안)**: META 115,000원 + ANET 110,000원(~0.43주, 비메모리 축). → **추천 A**(META 1순위, capex 눌림 최대·컨센 상방 +39%). 분산 신경 쓰이면 B |\n| ⚪ **중립 애매**(동결+점도표 소폭 매파) | **절반만**: META 115,000원만, 나머지 110,000원 현금 보존 |\n| 🔴 **매파**(점도표 상향/12월 인상 시그널 42%/워시 매파) | **전량 보류.** 현금 유지, 안전핀 감시 위임 |\n\n**6/17 저녁 체크리스트**: ①갭 변동 큼 인지 ②소수점=시장가 확인 ③META·AVGO 금액 입력 ④22:25~22:30 취소불가 ⑤매파 시 미입력.\n\n### ④ 두산에너빌리티 10만 재돌파 — 워치→진입 vs 추격금지\n\n**현황**: 103,300원(+3.5%, 10만 재돌파). 미보유(워치).\n\n**강세**: 2026 신규수주 목표 **13.4조**(체코 원전·가스터빈·웨스팅하우스 AP1000·테라파워/뉴스케일 SMR). 대미투자법 6/18 시행 = K-원전 자금줄. 증권사 평균 목표 **~143,000원**(하나 165k·IBK 160k / 미래에셋 105k 보수적), 평균 +38% 상방.\n\n**신중**: 52주 고점 139,200 대비 −25% 회복 중 = 변동성. 보수 목표(105k)는 현재가 바로 위. 6/18 갭 = 기대 선반영(\"1호 프로젝트 6월 발표 어렵다\") → 갭업 후 갭다운 리스크.\n\n**PM 판단 — 추격금지 유지(룰3·룰7), 진입 시나리오 베이킹**:\n- 10만 재돌파 당일·6/18 갭 **추격 금지**.\n- **진입 트리거**: ①6/18 소화 후 10만 **안착**(2~3일) ②눌림 **95,000~98,000원** 1차 소액 ③대미투자 1호 프로젝트 **구체 발표**(원전 확인) 시 비중 확대.\n- 수단: 국내 정수주 1주 지정가(시간외 17:30~18:00 또는 익일 정규장 예약). **모멘텀 아닌 정책·실적 코어 후보**로 분류 가능, 갭 추격만 회피.\n\n---\n\n## 📚 주요 출처\n\n- 국장: [코스피 8700선·외인 3일 순매수(이투데이)](https://www.etoday.co.kr/news/view/2594162) · [뉴스핌 마감시황](https://www.newspim.com/news/view/20260616000983)\n- 미장: [Oracle Q4 capex 쇼크(CNBC)](https://www.cnbc.com/2026/06/10/oracle-orcl-q4-earnings-report-2026.html) · [Micron 6/24 실적 프리뷰(TechTimes)](https://www.techtimes.com/articles/318228/20260611/micron-earnings-preview-june-24.htm)\n- 매크로: [BOJ 1% 인상(CNBC)](https://www.cnbc.com/2026/06/16/boj-rate-hike-historic-inflation.html) · [워시 첫 회의(FXStreet)](https://www.fxstreet.com/analysis/kevin-warsh-opens-first-fed-meeting-june-16-with-rate-hold-expected-202606151326) · [5월 CPI 4.2%(CNBC)](https://www.cnbc.com/2026/06/10/cpi-inflation-report-may-2026.html)\n- 반도체: [Citi MU 목표 $840(Watcher)](https://watcher.guru/news/micron-stock-is-falling-yet-citi-and-hsbc-increase-mu-price-targets) · [삼성 HBM4 인증(TechTimes)](https://www.techtimes.com/articles/318015/20260609/samsung-pursues-nvidia-hbm4e-supply.htm) · [SK하이닉스 ADR 8월(CryptoBriefing)](https://cryptobriefing.com/sk-hynix-us-listing-august/)\n- 전력: [LG전자 NVIDIA CDU(스페셜경제)](https://www.speconomy.com/news/articleView.html?idxno=414596) · [두산E SMR·가스터빈(비즈니스포스트)](https://www.businesspost.co.kr/BP?command=article_view&num=430560) · [대미투자법 6/18(시사저널e)](https://www.sisajournal-e.com/news/articleView.html?idxno=421741) · [GEV 100GW(Utility Dive)](https://www.utilitydive.com/news/ge-vernova-gas-turbine-backlog-hits-100-gw/818332/)\n- 빅테크: [ORCL 컨센 $253.5(stockanalysis)](https://stockanalysis.com/stocks/orcl/forecast/) · [META 목표 $825(public)](https://public.com/stocks/meta/forecast-price-target) · [SPCX 나스닥100·락업(tradingkey)](https://www.tradingkey.com/analysis/stocks/us-stocks/261958515-spacex-spcx-ipo.htm)\n- 리서치: [영상 Ixr9VLOrgIw 연준 인하 논지] · [LG이노텍 FC-BGA(한국경제)](https://www.hankyung.com/article/2026061556886) · [SPCX 미래에셋 0주(뉴스핌)](https://www.newspim.com/news/view/20260615001072)\n- 두산E 목표가: [미래에셋 105k 커버리지 개시](https://securities.miraeasset.com/bbs/download/2141595.pdf) · [IBK 160k(네이트)](https://news.nate.com/view/20260504n04672)\n\n---\n\n## 🗂️ STATE SNAPSHOT\n\n```\n[STATE SNAPSHOT v16 2026-06-16]\n총자산: ≈ 8,561,205원 (국내 1,911,900 + 미국 ~6,025,434 + 현금 624,771)\n주식 평가손익: +441,299원(원가기준) / 환차익 반영 ≈ +635,507원\n현금: 624,771원 + $1.11 (1차/2차/3차 전부 미집행)\n보유변동: 없음 (국내 5 + 미국 11)\n시장: 코스피 8,726.60(+2.11%, 외인 3일 연속 순매수) / SOX 14,100(+5.45%) / USD-KRW 1,506.5\n워치리스트(활성): 두산에너빌리티(10만 재돌파)·SK하이닉스·삼성전기·한화에어로·조선바스켓·원익IPS·테스·GEV·SK이노·SPCX·TMUS·LG이노텍(신규)\n대기 트리거: ①6/18 03:00 FOMC→3차 트랜치(동결 META·AVGO 소수점 예약/매파 보류, 6/17 저녁 베이킹) ②MU 6/24 실적→절반 차익 ③두산E 10만 안착 ④외인 4일째 지속 여부\n영구교정: BOJ 1.0% 인상 확정(6/16,7-1,엔캐리 무탈) / 토스 스크린샷 %=누적수익률(당일등락 아님) / ORCL capex쇼크 누적-17% / SPCX 270만주 코너스톤=모건스탠리(골드만 아님) / LG이노텍 2Q 영익 컨센 1,787억(채널 \"2,028억\" 정정)\n다음 버전: v17\n```\n\n---\n\n> **투자 자문 아님** — 모든 목표가·매수존·별점·예약안은 분석 참고이며 최종 결정·집행은 정훈.\n> 생성: 정훈 PORTFOLIO DESK (PM 오케스트레이션, 9개 데스크 병렬) · 2026-06-16\n"
    },
    {
      "id": "report_v16_addendum_2026-06-16",
      "file": "docs/reports/report_v16_addendum_2026-06-16.md",
      "title": "정훈 PORTFOLIO DESK · v16 부록 · 2026-06-16",
      "date": "2026-06-16",
      "version": 16,
      "kind": "보고서",
      "preview": "룰대로 빅테크 조정주 재매수. 단 리스크 데스크 집중도 경고(빅테크 5종 평단 부근 → 재매수 시 분산보다 집중↑) 반영해 2안 제시:",
      "content": "# 정훈 PORTFOLIO DESK · v16 부록 · 2026-06-16\n## 선택지 상세 분석 — ① ORCL ③ FOMC 예약 ④ 두산에너빌리티\n\n> 투자 자문 아님. 모든 레벨·예약안은 분석 참고이며 최종 결정·집행은 정훈.\n> 정훈 현금 624,771원(3분할 미집행), FX 1,506.66, 폰 가용 17:30~20:50 KST.\n\n---\n\n## ① ORCL −17% — 추가 하락 vs 매수기회? (capex/차입 딥다이브 + 분할매수 레벨)\n\n**현황**: 현재가 $192~194 / 정훈 평단 $232.12 / 보유 0.215주($41.66, 극소 비중) / 누적 −17%.\n\n**왜 빠졌나 (펀더 훼손 아님 — capex 청구서 쇼크)**\n- 6/10 FY26 Q4 **호실적**: EPS $2.11 vs 컨센 $1.89(+11.6% 비트), 매출 +21%, OCI(클라우드 인프라) +93%, **RPO(수주잔고) $638B(+363%)** = AI 클라우드 실수요는 실재.\n- 그런데 주가는 −13% → 이유는 **자금조달 부담**: capex FY26 $55.7B(가이 $50B 초과)→**FY27 $70B**, **$40B 신규 조달**($20B 주식 포함), FY26 **잉여현금흐름 −$23.7B**, 감가상각 2배($7.62B). + 주주 소송 firm probe.\n- 6/15 +6% 반등($194)했으나 6/10 고점 대비 누적 낙폭 미회복.\n\n**밸류·컨센**: 52명 평균 목표 **$251.66(+31% 상방)**, 의견 Buy 우위. 실적 후 다수는 목표가 **유지/상향**(Scotiabank만 $290→$241 하향). 기술적으로 **$194 지지 형성·$250 저항**.\n\n**양쪽 시각**\n- 🟢 매수기회론: RPO $638B·OCI +93% = 수요는 진짜, 컨센 목표 상방 +31%, $194 지지 형성. AI 클라우드 2~3위 사업자 리레이팅 여력.\n- 🔴 신중론: capex→차입 가속으로 **FCF 마이너스·금리 민감도 급등**, 소송 probe, 단기 바닥 미확인. ROI 회의가 META·GOOGL로 전염되는 섹터 테마의 진앙.\n\n**PM 판단 — 지금 물타기 비권장(추격금지 룰3)**\n- 떨어지는 칼날 + 6/18 FOMC 직전 + 정훈 현금은 트랜치로 묶임(ORCL 물타기는 3차 트랜치 용도 아님).\n- **단계적 관심 레벨**(신규자금 가정, 안정 확인 후 분할):\n  | 단계 | 레벨 | 조건 |\n  |---|---|---|\n  | 1차 관찰 | **$180~185** | FOMC·실적후폭풍 소화 + 일봉 안정(반등 추격 금지) |\n  | 2차 | **$168~172** | 직전 갭 지지대 재테스트 시 |\n  | 3차 | **$150~158** | 과매도·컨센 목표 괴리 +60% 구간 |\n- 보유분(극소)은 **홀딩**. 평단 $232 회복은 컨센 목표($251) 내라 장기 시야에선 비관 아님. **알림만 걸고 FOMC 후 재평가.**\n\n---\n\n## ③ FOMC 6/18 03:00 — 3차 트랜치 사전 예약 세팅 (비둘기/매파별)\n\n**전제**: FOMC 결정·워시 첫 회견은 **03:00 KST = 폰 미가용** → 당일 밤 실시간 대응 불가. **6/17(수) 17:30~20:50 사이에 토스 미국주식 소수점(금액) 예약**만이 방법. ⚠️ 소수점=**시장가 체결** → 6/18 개장(22:30) 갭에 체결가 노출. **22:25~22:30 취소 불가 구간** 유의.\n\n**3차 트랜치 한도 ~225,000원 ≈ $149.** 현재가 META $593.48 / AVGO $393.94.\n\n### 🟢 비둘기 (동결 + \"추가 조정\" 문구 삭제→중립 / 점도표 완만 / 워시 비둘기)\n룰대로 빅테크 조정주 재매수. **단 리스크 데스크 집중도 경고**(빅테크 5종 평단 부근 → 재매수 시 분산보다 집중↑) 반영해 2안 제시:\n| 안 | 배분 | 비고 |\n|---|---|---|\n| **A. 룰 그대로(빅테크)** | META **115,000원**(~$76, ~0.128주) + AVGO **110,000원**(~$73, ~0.185주) | 컨센 상방 META +39%·AVGO +33%, 둘 다 Strong Buy |\n| **B. 분산 대안** | META **115,000원** + **ANET 110,000원**(~$73, ~0.43주) | ANET은 AI 네트워킹·비메모리 축 → 집중도 완화. 가이던스 상향 모멘텀 |\n→ **추천: A로 가되 META에 약간 더 실어 1순위 처리**(capex 눌림이 가장 깊고 컨센 상방 최대). 분산이 더 신경 쓰이면 B.\n\n### ⚪ 중립 애매 (동결 + 점도표 소폭 매파 / 톤 혼조)\n- **절반만 집행**: META 115,000원만 예약, 나머지 110,000원 현금 보존 → 6/18~19 네마녀·준틴스 소화 후 판단.\n\n### 🔴 매파 (점도표 상향 / **12월 인상 시그널**(시장 42% 반영) / 워시 매파)\n- **전량 보류.** 밸류 비싼 AI·반도체부터 되돌림 → 현금 유지가 우위. 안전핀(7,500) 감시 위임.\n\n**예약 실행 체크리스트(6/17 저녁)**: ①FOMC 직전이라 갭 변동 큼 인지 ②소수점=시장가 확인 ③META·AVGO 금액 예약 입력 ④22:25~22:30 취소불가 숙지 ⑤매파 시 미입력(보류).\n\n---\n\n## ④ 두산에너빌리티 10만 재돌파 — 워치→진입 전환 vs 추격금지 유지\n\n**현황**: 103,300원(+3.5%, **10만 재돌파 트리거 발동**). 미보유(워치).\n\n**강세 근거**\n- 2026 신규수주 목표 **13.4조**(체코 원전 + 가스터빈 추가 + 웨스팅하우스 AP1000 + 테라파워·뉴스케일 SMR).\n- **대미투자특별법 6/18 시행** = K-원전 자금줄(한미전략투자공사). AI 전력난(가스터빈·SMR) 구조적 수혜.\n- 증권사 목표 상향: **평균 ~143,000원**(하나 165k·IBK 160k 최고 / 미래에셋 105k 보수적) — 현재가 대비 평균 +38% 상방.\n\n**신중 근거**\n- 52주 고점 139,200 대비 −25%에서 회복 중 = 변동성 큼. 미래에셋 등 보수 목표(105k)는 현재가 바로 위 → 단기 상방 제한적 견해도 존재.\n- **6/18 이벤트 갭 = 기대 선반영**(산업장관 \"1호 프로젝트 6월 발표 어렵다\") → 시행 당일 갭업 후 갭다운 리스크. 이란/중동 변수로 3월 10만 깨졌던 전례.\n\n**PM 판단 — 추격금지 유지(룰3·룰7), 단 진입 시나리오는 베이킹**\n- 10만 재돌파 당일·6/18 시행 갭 **추격 진입 금지**(소화 후 움직임 확인).\n- **진입 트리거(신규 편입 검토 조건)**: ①6/18 시행 이벤트 **소화 후** 10만 **안착**(2~3일 지지) ②눌림 **95,000~98,000원** 되돌림 시 1차 소액 ③대미투자 1호 프로젝트 **구체 발표**(원전 포함 확인) 시 비중 확대.\n- 집행 수단: 국내 정수주 1주 = 지정가 가능(폰 겹침 17:30~18:00 시간외 또는 익일 정규장 예약). **모멘텀 아닌 정책·실적 코어 후보**로 분류 가능하나, 갭 추격만 피하면 됨.\n\n---\n\n> 다음 액션: 1·3·4 중 추가로 파고들 항목 있으면 지시. FOMC 예약은 **6/17(수) 저녁**에 시나리오 확정 후 세팅 리마인드 예정.\n> 투자 자문 아님 — 최종 결정은 정훈.\n"
    },
    {
      "id": "report_v16_2026-06-16",
      "file": "docs/reports/report_v16_2026-06-16.md",
      "title": "정훈 PORTFOLIO DESK · v16 · 2026-06-16",
      "date": "2026-06-16",
      "version": 16,
      "kind": "보고서",
      "preview": "HBM 슈퍼사이클 \"검증 국면\". Citi가 DRAM 업턴 2027년까지 연장(MU 목표 $840), 삼성 HBM4 엔비디아 인증 통과·2월 양산 → 3사 동반 가격 인상.",
      "content": "# 정훈 PORTFOLIO DESK · v16 · 2026-06-16\n\n> 투자 자문 아님. 모든 목표가·매수존·별점은 분석 참고이며 최종 결정은 정훈.\n> 데이터 기준: 토스 계좌 스크린샷(6/16 17:34) = 정본 + Yahoo 무키 라이브 + 웹 교차검증.\n\n## 변경점 (직전 v15 대비)\n\n- 🆕 **토스 계좌 스크린샷 2장(국내+해외) 확보** → 보유 손익 정본 갱신. **총자산 ≈ 8,561,205원**(주식 평가손익 환차익 반영 시 ≈ +63.5만원).\n- ⚠️ **스크린샷 % 해석 정정**: 스크린샷의 종목별 %는 **당일 등락이 아니라 누적 보유수익률(총수익)**. 오늘 실제 장세는 전 종목 강세였다(코스피 +2.1%, SOX +5.45%, MU 당일 +10.8%). ORCL \"-16.5%\"는 평단 대비 누적손실이지 당일 급락이 아님(당일은 +4.6%).\n- ✅ **BOJ 0.75→1.0% 인상 확정**(6/16, 7-1 가결, 31년래 최고). 엔/달러 소폭 강세에 그쳐 **엔캐리 청산 패닉 신호 없음** — 안전핀 미발동.\n- 🔴 **두산에너빌리티 10만 재돌파(103,300, 트리거 발동)** — 추격금지 룰 적용.\n- 🆕 **워치 후보 부상: LG이노텍**(FC-BGA AI 기판 구조적 공급부족, 2분기 영익 컨센 1,787억 +15.7배). 추격 아닌 관찰.\n\n---\n\n## 1. 시장 — 국장 / 미장\n\n### 국장 (kr-market-desk)\n- **코스피 8,726.60(+2.11%) / 코스닥 1,018.68(+2.18%)** — 6/15 폭등(+5.2%) 후 3거래일째 상승, 8,700선 안착. 美·이란 종전 기대 + 유가 급락발 위험선호.\n- **🔑 외인 3거래일 연속 순매수**(당일 +1.54조·기관 +0.85조, 개인 -2.33조). 24거래일 '셀코리아'(~76조) 종료 후 삼성전자·SK하이닉스 등 반도체 대형주 재매수. → **강세 엔진 정상 작동, 단 4일째 지속이 분기점**(개인이 매물 받는 구도).\n- **로테이션**: 반도체 대형주(SK하이닉스 +4.1%·삼성전기 +2.5%)·**방산 폭등(한화에어로 +9.1%)** 주도. AI로봇·소부장(원익IPS **-10.5%**·테스 -4.4%·두산로보 -2.2%)은 차익실현 급락 = \"AI로봇→AI소부장→대형 반도체\"로 관심 이동.\n\n### 미장 (us-market-desk, 6/15 마감 기준)\n- **S&P 7,554(+1.65%) / 나스닥 26,684(+3.07%) / SOX 14,100(+5.45%)** — 반도체가 랠리 견인. VIX 17 하회(전주 23+ 대비 급락) = 명확한 리스크온. 미·이란 평화(호르무즈 개방·유가↓)가 동력.\n- **보유 연관**: MU 당일 +10.8%(HBM 완판)·NVDA +3.5%·AVGO +3.1%·ANET +3.6%, META +4.7%·GOOGL +2.7%. **ORCL +4.6% 반등**했으나 6/10 capex 쇼크 이후 누적 -17%대는 미회복.\n- **FOMC(6/18 03:00) 선반영 비둘기 랠리** — 정훈 폰 미가용 시간대 → 사전 조건부 예약만 유효.\n\n---\n\n## 2. 섹터 — 반도체AI / 전력·피지컬 / 빅테크\n\n### 반도체·AI인프라 (semi-ai-desk)\nHBM 슈퍼사이클 \"검증 국면\". Citi가 DRAM 업턴 2027년까지 연장(MU 목표 $840), 삼성 HBM4 엔비디아 인증 통과·2월 양산 → 3사 동반 가격 인상.\n- **MU(정훈 +45%·$1,088)**: 2026 HBM 전량 완판, **6/24 실적이 사이클 분수령**. 현재가가 이미 Citi 목표 $840 초과 → 서프라이즈 선반영 리스크. **절반 차익 검토(집중도 완화 1차 수단)**.\n- **삼성전자(+30%)**: HBM4 인증·양산, 젠슨황 서울회동 후 HBM4E·파운드리(LP40) 논의.\n- **AVGO(-6%)**: 커스텀 ASIC(XPU) +106% — 메모리 비의존 분산축. **ANET**: AI 네트워킹 가이던스 $2.75B→$3.25B 상향.\n\n### 전력·피지컬AI (power-physical-desk)\n**대미투자특별법 6/18 시행 임박** = 원전·조선·SMR 동시 수혜.\n- **LG전자(정훈 +51%·최고 수익 코어)**: NVIDIA CDU 인증 최종 단계 보도(미확정), 냉각용량 650kW→1.4MW. **펀더 훼손 신호 없음 → 손절선 폐기 룰 유지**.\n- **두산에너빌리티**: 103,300 **10만 재돌파**(트리거 발동), 2026 신규수주 목표 13.4조 + 대미투자법 직접 수혜. **추격금지 룰3 적용**.\n- **현대차(+1.6%)**: 보스턴다이내믹스 IPO 임박(6월 풋옵션), KB 목표 120만. **두산로보(+9%, 모멘텀)**: 협동로봇 모멘텀 식음. **TSLA(-2.7%)**: 옵티머스 7월말~8월 생산.\n- 조선 빅3 + 한화에어로: 대미투자 조선 $1,500억 직결(MASGA, 수익 100% 한국 귀속).\n\n### 빅테크·플랫폼 (bigtech-platform-desk)\n빅테크 보유분 누적 약세 = **\"AI capex 청구서\" 트레이드** — ORCL capex/차입 가이던스가 META·GOOGL·MSFT로 회의론 전염. 반면 AAPL은 \"저capex·온디바이스\" 안전자산 반사 수혜.\n- **ORCL(-17%·$193)**: Q4 호실적(RPO $638B/+363%·OCI +93%)에도 capex FY26 $55.7B→FY27 $70B + **$40B 차입** 부담. 컨센 목표 $253.5(상방 +38%)는 유지 — 펀더 아닌 밸류 리레이팅. **추격금지, 소화 후 판단**.\n- **META(-6%·$593)**: capex 가이 $145B에 ROI 회의, 컨센 $827(상방 +39%). **FOMC 비둘기 시 재매수 1순위**.\n- **AAPL(+15%·$296)**: WWDC Siri AI·온디바이스로 로테이션 수혜, 컨센 목표 $313 근접. **NAVER(-3%)**: 정리 후보 상시 검토 유지.\n\n---\n\n## 3. 매크로 데스크\n\n- **환율 USD/KRW 1,506.48(-0.62%, 원화 강세)** — 외인 환차익 우호(순매수 흐름 정합). 美 보유주 원화 환산단가는 소폭 하향.\n- **BOJ 6/16 0.75→1.0% 인상 확정**(7-1, 31년래 최고). 엔/달러 160 부근 소폭 강세 그침 = **엔캐리 청산 패닉 없음**. 안전핀 7,500 발동 사유 미발생.\n- **FOMC 6/18 03:00 동결 ~97%** + 워시 의장 첫 회견 + 점도표. CPI 5월 +4.2%·core +2.9%·에너지 +23.5% = 매파 리스크 상존(연내 1회 인상 확률 ~70%로 상승). **다음 CPI = 7/14**(이번 사이클 밖).\n- **유가 브렌트 $84~87**, 이란 평화협정 6/19 스위스 서명 예정 → 서명 시 $80 하향 = CPI 에너지 경로 둔화 우호.\n\n### 이벤트 캘린더 (2주)\n| 날짜(KST) | 이벤트 | 폰 가용 |\n|---|---|---|\n| 6/16(화) | **BOJ 1.0% 인상 (완료)** | 확인됨 |\n| **6/18(목) 03:00** | **FOMC 동결+점도표+워시 회견** / 대미투자법 시행 / 美 네마녀의날 | ❌ 야간 — 사전 예약 베이킹 필수 |\n| 6/19(금) | 美 준틴스 **휴장** / 이란 협정 서명 예정 / 워치 유예종목 자동 제외 마감 | 미국장 휴장 |\n| 6/22 주간 | SK하이닉스 미 ADR SEC 승인 가능성 | — |\n| 6/24(수) | **MU 실적** (절반 차익 검토) | ❌ 야간 |\n| 7/14(월) | 美 6월 CPI | ❌ 야간 |\n| 7/16(목) | 한국은행 금통위 | — |\n\n---\n\n## 4. 리서치 피드 (경제사냥꾼)\n\n6/15~6/16 신규 영상 4 + 쇼츠 2 수집(봇차단 없음). 핵심 수치는 전부 웹 교차검증.\n\n| 주장 | 분류 | 비고 |\n|---|---|---|\n| FOMC 6/17(결정) 동결 98%+, 워시 첫 회의·점도표/가이던스 축소→중립 전환 | **[검증]** | 정훈 6/18 03:00 트리거 룰과 직결 |\n| 물가 4.2%는 유가發 공급인플레 → 호르무즈 재개 시 후행 둔화, 방향은 인하 | **[검증/보강]** | **단 시장은 12월 인상 확률 42% 반영 — 단기 매파 리스크 = 안전핀 유지 근거** |\n| 이란 휴전 \"6/19 금요일 서명\" 특정 | **[정정주의]** | 실제 60일 휴전 MOU·호르무즈 30일내 개방, 트럼프 최종승인 단계. 특정일 미확인 |\n| SPCX 공모 $135→첫날 $160.95(+19.2%), 미래에셋 0주 배정 | **[검증]** | 마스터 영구교정과 일치. 락업·나스닥 조기편입 모니터 |\n| SPCX 미래에셋 본사 270만주 코너스톤 = \"골드만\" | **[정정]** | 실제 주체는 **모건스탠리**(공동주관), 금감원 이해상충 조사 중 |\n| LG이노텍 2분기 영업이익 \"2,028억·18배\" | **[정정]** | 실제 KB 컨센 **1,787억·약 +15.7배**. 방향(역대급·1조클럽 복귀)은 검증 |\n| LG이노텍 FC-BGA = AI 기판 구조적 공급부족, 美 4개+ 고객 증설 요청 | **[검증]** | 🆕 **반도체·AI 워치 후보** — AI 슈퍼사이클 코어 테마 직결, 추격 아닌 관찰 |\n| G7 1년 테마(핵심광물·방산), 종전 기대 시 방산 차익실현 | **[방향성]** | 한화에어로·조선바스켓 단기 변동성 주의 |\n\n- **신규 입력 없는 항목**: BOJ 인상·두산E·SK이노 SMR·삼성/SK하이닉스 HBM·대미투자법(6/18)은 6/15~16 신규 영상에서 직접 다룬 콘텐츠 없음.\n\n---\n\n## 5. 리스크 데스크\n\n- 🚦 **안전핀**: 코스피 8,727 vs 7,500 = **+16.4% 여유**. 동결 사유 없음. **2차 트랜치 게이트(8,000)**: \"이란 결렬 + 8,000 하회\" 동시조건 → 현 시점 발동 불가.\n- 🟢 **매수존**: NAVER 242,000(존 225~235k 위)·삼성전자 343,000(존 295~305k 위) — **둘 다 매수존 위, 미진입**. 추격 금지.\n- 🔴 **두산E 10만빌리티 발동**(103,300) — 워치라 보유영향 없으나 추격금지.\n- **집중도 경고**: 메모리·AI 반도체가 NVDA(최대비중)+MU+삼성 3중 중첩, SK하이닉스 8월 상장 시 4중. 동반 급등은 동반 손실로도 온다. 미국 11종목 전부 원/달러 단일 환노출도 누적. **빅테크(META·MSFT·GOOGL·ORCL·AAPL)는 평단 부근 → 3차 트랜치를 빅테크에 쓰면 분산보다 집중도만 키울 수 있음**.\n- **신중(bear)**: 코스피 8,700·SOX 14,000은 이틀 만의 외인 전환에 올라탄 급등 직후 고점권. ①BOJ 인상발 엔캐리 청산 ②FOMC 매파 시 밸류 비싼 AI·반도체(특히 +45% MU)부터 되돌림 ③외인 순매수 \"2~3일\"은 숏커버 가능성 배제 못 함. **오늘 폭등은 매수 근거가 아니라 미집행 현금 62만원을 지킬 이유.**\n\n---\n\n## 6. 강세 vs 신중 디베이트\n\n- **강세**: 외인 3거래일 연속 순매수(누적 ~4.8조)로 코스피 메인 엔진 정상 가동, 반도체 대형주 선취 명분 강화. SOX +5.45%·MU HBM 완판으로 AI 메모리 슈퍼사이클 실수요 확인. BOJ 인상에도 엔캐리 무탈, 유가 급락 + FOMC 동결 우세 = 위험선호 지속. LG전자(+51%)·삼성(+30%)·MU(+45%) 코어가 포트를 끌어올림.\n- **신중**: 이틀 폭등 후 고점권, 외인 전환은 아직 추세 미확정(숏커버 가능성). FOMC 매파(워시 첫 회견·점도표)·6/18~19 네마녀의날+준틴스 유동성 공백이 겹치는 변동성 구간. 빅테크 capex ROI 회의(ORCL -17%)가 광범위. MU는 Citi 목표 초과 = 실적 서프라이즈 선반영. → **추격 자제, 현금 보존, 이벤트 확인 후 대응.**\n\n---\n\n## 7. PM 종합 (최종)\n\n**오늘의 한 줄**: 외인 3일째 순매수 + SOX 폭등으로 포트는 호조(총자산 ≈ 856만, 환차익 포함 손익 ≈ +63.5만)지만, **6/18 FOMC·네마녀·준틴스 변동성 구간 직전 = 신규 진입보다 사전 예약 베이킹 + 현금 보존이 정답.** 스크린샷 %는 누적수익률이지 당일등락 아님 — 빅테크 약세는 \"보유 누적\"일 뿐 오늘은 동반 강세였다.\n\n### 보유 16종목 (현재가 = 토스 6/16 / 수익률 = 원가 고정 / 목표·괴리 = 컨센)\n| 종목 | 현재가 | 수익률 | 컨센 목표 | 매수존 | ⭐ | 코멘트 |\n|---|---|---|---|---|---|---|\n| LG전자 | 235,000 | **+50.8%** | — | — | ⭐⭐⭐⭐⭐ | 최고 코어, CDU 인증 모멘텀, 손절선 폐기 유지 |\n| 삼성전자 | 343,000 | **+30.4%** | — | 295~305k | ⭐⭐⭐⭐ | HBM4 코어, 외인 순매수 직접 수혜 |\n| MU | $1,088 | **+45.3%** | $867 | — | ⭐⭐⭐⭐ | 6/24 실적·절반 차익 검토, 목표 초과 |\n| AAPL | $296 | +15.3% | $313 | — | ⭐⭐⭐ | 온디바이스 로테이션, 목표 근접 |\n| VOO | $694 | +7.5% | — | — | ⭐⭐⭐⭐ | 지수 코어 |\n| NVDA | $212 | +6.5% | $299 | — | ⭐⭐⭐⭐⭐ | AI 코어, 상방 +41% |\n| 두산로보 | 109,400 | +9.0% | — | — | ⭐⭐⭐(모멘텀) | 차익실현 식음, 트레이딩 대상 |\n| ANET | $169 | +4.3% | $189 | — | ⭐⭐⭐⭐ | AI 네트워킹 가이던스 상향 |\n| 현대차 | 640,000 | +1.6% | KB 120만 | — | ⭐⭐⭐ | BD 로봇 IPO 임박 |\n| TSLA | $411 | -2.7% | $421 | — | ⭐⭐⭐ | 옵티머스 7~8월 |\n| MSFT | $400 | -2.6% | $561 | — | ⭐⭐⭐⭐ | Azure 방어, 상방 큼 |\n| NAVER | 242,000 | -3.4% | — | 225~235k | ⭐⭐ | 정리 후보 상시 검토 |\n| GOOGL | $369 | -4.7% | $433 | — | ⭐⭐⭐⭐ | capex 베타 약세, 펀더 견조 |\n| META | $593 | -6.4% | $827 | — | ⭐⭐⭐⭐ | FOMC 비둘기 시 재매수 1순위 |\n| AVGO | $394 | -6.4% | $522 | — | ⭐⭐⭐⭐ | 커스텀 ASIC 분산축 |\n| ORCL | $194 | **-17.0%** | $255 | — | ⭐⭐⭐ | capex/차입 부담, 추격금지·소화 후 |\n\n### 워치리스트 (활성)\n| 종목 | 현재가 | 코멘트 |\n|---|---|---|\n| 두산에너빌리티 | 103,300 | **10만 재돌파 트리거 발동**, 대미투자법 수혜, 추격금지 |\n| SK하이닉스 | 2,382,000 | 외인 순매수 핵심 타깃, 미 ADR 8월 상장(6/22주 SEC) — 상장 후 진입 |\n| 삼성전기 | 2,048,000 | AI 소부장 대장, 반도체 동조 |\n| 한화에어로 | 1,183,000 | 방산 +9% 폭등, 대미투자 직결 |\n| 조선바스켓 | 한화오션 129,200 외 | 대미투자 조선 $1,500억, 6/18 시행 후 소화 |\n| 원익IPS/테스 | 156,100 / 169,200 | 소부장 차익실현 -10%/-4%, 눌림 관찰 |\n| GEV / SK이노 | $979 / — | AI 전력·SMR, 백로그 100GW |\n| SPCX / TMUS | $192.5 / $189 | 나스닥100 편입 ~7/1 데드라인, 락업 12월 |\n\n### 제안 액션\n- **기본 = 홀딩 + 관망.** 오늘 신규 매수 없음(전 종목 매수존 위, 급등 직후 고점권 + 이벤트 직전).\n- **6/17(수) 17:30~20:50 사전 베이킹**: 3차 트랜치(~22.5만) **조건부 예약** — 🟢FOMC 동결+중립 시 META(~0.25주)·AVGO 소수점 시장가 예약 / 🔴매파 시 전량 보류. 새벽 실시간 대응 불가하니 예약 외 방법 없음.\n- **MU**: 6/24 실적 후 **절반 차익**으로 집중도 완화 검토(현재가 Citi 목표 초과). 실적 전 추격 금지.\n- **6/18~19 네마녀+준틴스**: 신규 미장 진입 회피, 예약분만 개장 직후 체결되게 설정.\n\n### 현금 배분 플랜 (잔액 624,771원, 3분할 전부 미집행)\n- **1차(~10~15만)**: NAVER 225~235k 또는 삼성 295~305k 눌림 시 — 현재 둘 다 존 위, 대기.\n- **2차(~20만)**: 코스피 8,000 하회 + 이란 결렬 동시 — 미충족.\n- **3차(~22.5만)**: FOMC 확인 후 META·AVGO 소수점 예약(비둘기) / 보류(매파). **빅테크 집중도 주의 — 분산 관점이면 ANET·GEV 등 비메모리 축도 고려.**\n\n### 지켜볼 것\n1. **외인 4일째 순매수 지속 여부**(끊기면 강세 논지 약화 = 신중 전환).\n2. **6/18 03:00 FOMC** — 점도표·워시 톤 → 3차 트랜치 분기.\n3. **두산E 10만 안착 vs 되돌림**(추격금지).\n4. **MU 6/24 실적** → 절반 차익 판단.\n\n---\n\n## 8. 오늘의 이슈 선택지 (번호로 답하면 그 항목 상세 분석)\n\n1. **ORCL -17% 손실 — 추가 하락 vs 매수기회?** capex/차입 쇼크 딥다이브 + 분할매수 레벨.\n2. **MU +45% 6/24 실적 플레이북** — 절반 차익 vs 홀딩, 컨센·시나리오별 대응.\n3. **FOMC 6/18 사전 예약 시나리오** — 비둘기/매파별 정확한 소수점 예약 세팅(META·AVGO 금액·레벨).\n4. **두산에너빌리티 10만 재돌파** — 워치→진입 전환 검토(대미투자법 6/18 연동) or 추격금지 유지.\n\n---\n\n## STATE SNAPSHOT\n\n```\n[STATE SNAPSHOT v16 2026-06-16]\n총자산: ≈ 8,561,205원 (국내 1,911,900 + 미국 ~6,025,434 + 현금 624,771)\n주식 평가손익: +441,299원(원가기준) / 환차익 반영 ≈ +635,507원\n현금: 624,771원 (1차/2차/3차 전부 미집행)\n보유변동: 없음 (국내 5 + 미국 11)\n시장: 코스피 8,726.60(+2.11%, 외인 3일 연속 순매수) / SOX 14,100(+5.45%) / USD-KRW 1,506.5\n워치리스트(활성): 두산에너빌리티(10만 재돌파)·SK하이닉스·삼성전기·한화에어로·조선바스켓·원익IPS·테스·GEV·SK이노·SPCX·TMUS\n대기 트리거: ①6/18 03:00 FOMC→3차 트랜치(동결 META·AVGO 소수점 예약/매파 보류, 6/17 저녁 베이킹) ②MU 6/24 실적→절반 차익 ③두산E 10만 안착 ④외인 4일째 지속 여부\n영구교정: BOJ 1.0% 인상 확정(6/16, 7-1, 엔캐리 무탈) / 토스 스크린샷 %=누적수익률(당일등락 아님) / ORCL capex쇼크 누적-17% / SPCX 270만주 코너스톤=모건스탠리(골드만 아님) / LG이노텍 2Q 영익 컨센 1,787억(채널 \"2,028억\" 정정)\n다음 버전: v17\n```\n\n> 투자 자문 아님 — 모든 레벨은 분석 참고, 최종 결정은 정훈.\n"
    },
    {
      "id": "report_v15_addendum_2026-06-15",
      "file": "docs/reports/report_v15_addendum_2026-06-15.md",
      "title": "v15 부록 · 2026-06-15 — 심층분석 ①~④",
      "date": "2026-06-15",
      "version": 15,
      "kind": "보고서",
      "preview": "",
      "content": "# v15 부록 · 2026-06-15 — 심층분석 ①~④\n\n> v15 본보고서 §8 선택지 4건 전부 심층화. 8데스크 중 macro·power-physical·semi-ai·risk 데스크가 각각 깊게 조사. **투자 자문 아님 — 최종 결정은 정훈.** 시세=6/15 기준, FOMC/BOJ 항목은 실측 환율·시세 채택.\n\n---\n\n## ① 6/16 BOJ 시나리오별 코스피·포트 영향\n\n**핵심 반전 — 우에다 총재 부재**: 우에다 간낭종 감염 입원 → **표결 불참·서면만, 회견은 우치다 부총재 대행** [검증]. 우치다는 2024.8 닛케이 폭락 직후 \"시장 불안정 시 인상 안 함\"으로 진정시킨 **비둘기 안전판** → 시나리오를 B/C로 기울이는 비대칭 요인.\n\n**발표 시각 (JST=KST, 시차 0)**: 금리결정 **~12:00**, 우치다 회견 **15:30~** — **둘 다 폰 가용(17:30~) 전 + KRX 정규장 마감(15:30) 전후**. 정훈 접속 시점엔 종가 반영 완료, **17:30~18:00 시간외단일가만 유일한 당일 거래창**(이미 소화된 가격). → 사전 베이킹.\n\n| 시나리오 | 확률(PM추정) | 엔(USD/JPY) | 코스피 | 포트 고베타(NVDA·MU·AVGO·ANET·삼성·두산로보) |\n|---|---|---|---|---|\n| **A 매파**(연내 2회·중립금리 상향) | 20~25% | →150~152 급강세 | **−5~−8%**(→7,860~8,120) | −8~−15% 동반조정 |\n| **B 중립**(점진·데이터의존) 기본 | 50~55% | →157~158 | −1~+2% 노이즈 | 영향 미미, 실적 우위 |\n| **C 비둘기**(우치다 시장안정) | 25~30% | 161+ 약세 | +1~+3% | 위험선호 지속 |\n\n**안전핀 7,500(현 8,546서 −12.2%)**: **B·C 도달 불가. A 단독도 거의 불가**(A최악 −8%여도 7,860 → 추가 −4.6% 더 필요). **BOJ 단독으론 안전핀 미성립** = \"BOJ만으로 패닉 동결할 필요 없음.\" 현 USD/JPY 160·**청산 징후 없음**, 2024.8은 인상서프라이즈+美침체공포+포지션극단 3중 트리거 동시였으나 지금은 인상이 컨센·美침체 신호 부재 → **재현 강도 더 약할 개연**.\n\n**PM 대응**: 결과는 폰 전 확정 → 당일 야간 트리거 금지, 다음날 아침 실행 베이킹. **A 발동 시 7,500 미도달이면 동결 아님 → 고베타 눌림은 3차 트랜치 역발상 분할 기회**(추격 아닌 눌림 확인 후). B=홀딩, C=추격금지 유지. 무헤지 원/달러는 A 리스크오프 시 USD/KRW 약세가 미국분 환산 방어.\n\n---\n\n## ② 두산에너빌리티 10만 돌파 플레이북\n\n**KUIC 1호 팩트체크 (가장 중요)**: 한미전략투자공사 **6/18 세종 출범·자본 2조는 확정**[검증], 그러나 **1호 프로젝트 발표는 김정관 산업장관(5/27) \"다음 달(6월) 어렵다\"** + 산업부(5/8) \"1호 내용·시기 정해진 바 없음, 추측성 보도 신중 요청\" [검증]. **두산E 선정도 정부 미확인.** → \"6/18=두산E 수혜 발표\" 기대는 과열, 10만 돌파는 출범 기대 선반영.\n\n**수주 가이던스 정정**: 회사 공식 **~10조대**, 보도된 **\"14.3조는 비공식 파이프라인 합산 — 확정수치 인용 금지** [정정]. 체코 5.6조(NSSS 4.9조+터빈 0.7조) 확정.\n\n**밸류 [고평가 명확]**: 시총 ~64조(코스피 7위), **2026E PER ~203배·PBR 7.7배**(FnGuide). SMR·원전·가스터빈 2027~2030 이익을 당겨 반영한 성장 프리미엄. 외인 지분 24.1%(올해 외인 순매수 1위).\n\n**컨센 평균 ~143,000(+43%)**: 하나 165k·IBK 160k·키움 158k·미래에셋 105k(보수 하단). 매수 우세, ±30% 괴리 아님.\n\n**플레이북 (추격금지 준수)**:\n| 시나리오 | 트리거 | 대응 |\n|---|---|---|\n| 10만 안착 | 10만 위 2거래일 종가 유지+거래량 | 당일 추격 금지, 안착 후 1주 소액 |\n| **되돌림(정석)** | **90,000~93,000**(6/12 지지) | **1차 분할 우선** — 시간외 17:30~18:00 정수 1주 지정가 예약 |\n| 1호 발표 | 정부 공식(6월 내 가능성 낮음) | 갭 당일 금지, 무산/지연 눌림을 매수기회로 |\n- **워치→보유 편입: 조건부 YES, 소액·되돌림 한정.** 10만 추격은 비추, 9만 초중반 1주 지정가가 정석. 단 현금 62만은 트랜치와 경합 → 예산 잠식 주의.\n\n---\n\n## ③ 삼성전기 폭등 해석 + 등락률 재확인\n\n**🔧 수치 확정: +16.63%(종가 1,999,000원)가 정답.** 뉴스 +11.79%/+12.78%는 **6/15 오전 9:35 장중 스냅샷** — 종가 아님. 오전 +12% → 장 후반 추가 상승 → 종가 +16.6%. 둘 다 맞고 시점 차이(모순 아님). 6/12 종가 1,714,000 검증. **6/15 투자경고종목 지정**(과열 신호).\n\n**폭등 이유**: 직접 촉매 = 5/20 **실리콘 캐패시터 1조5,570억 대형 공급계약**(AI 가속기용, 2027~2028). 구조적 = MLCC(가동률 90%+)·FC-BGA(공급부족)·실리콘캡 3축 동시. **단 수급 변수 중대 — \"패시브가 낳은 괴물\"**: 삼성전자·SK하이닉스 한도 채운 AI ETF가 잔여비중을 삼성전기로 기계매수, 5/19 98.7만→5/29 212.7만(열흘 2배)→하루 −14% 전례. 펀더멘털+패시브 혼재.\n\n**목표/밸류**: DB 300만·iM 230만·신한 200만·SK 200만. **후행 PER ~200배**(무라타 48배 대비 프리미엄), 단 iM은 성장 반영 **PEG 0.4배**로 저평가 반박 — 강세/신중 갈림.\n\n**판단: 워치 잔류·추격 금지·눌림 관찰.** +16.6% 종가급등+투자경고+PER 200배+패시브 의존 = 룰3(이벤트 갭 당일 진입 회피) 정면 해당(원익IPS·SPCX 동급). **눌림 160~175만대** 또는 5/29 고점 −20%대서 1차 관찰, 분할. ⚠️ 진입해도 삼성전자(보유)와 같은 ETF 수급 테마 동승 → 분산효과 제한.\n\n---\n\n## ④ 6/18 FOMC 3차 트랜치 실행 매뉴얼\n\n**🚨 실측 시세가 본보고서보다 높음**(META $587.60·AVGO $394·NVDA $210·환율 1,512) → 트랜치 가능성 더 빡빡.\n\n| 후보 | 1주 KRW | 3차 225k? | 전체현금 62만? | 괴리 | 비고 |\n|---|---|---|---|---|---|\n| NVDA | ~317,900 | ❌ | ✅(잔액 ~307k) | +45.7% | 이미 보유(중복) |\n| ANET | ~248,200 | ❌ | ✅ | +15.9% | 보유(중복) |\n| ORCL | ~287,180 | ❌ | ✅ | — | 보유(중복) |\n| AVGO | ~595,740 | ❌ | ✅(잔액 겨우 29k) | +36.6% | 보유, 현금 거의 소진 |\n| **META** | **~888,450** | ❌ | **❌ 26만 부족** | +45.9% | **미보유·1순위인데 전체현금으로도 1주 불가** |\n\n**핵심: 어떤 후보도 225k 정수주 1주 불가. META는 전체현금으로도 못 삼.** 트랜치 설계('META·AVGO 225k 재매수')와 현금·1주가·운영제약이 **구조적 불일치**.\n\n**실행 타임라인 — \"비둘기여도 6/20 집행\"(2영업일 지연)**:\n- 6/18 03:00 FOMC = 폰밖(취침) → 당일 밤 분수주 시장가 **금지**(룰).\n- 6/18 17:30~20:50 폰 가용 → 정수주 지정가 예약만, but META/AVGO 1주>트랜치 → 예약 무의미.\n- 6/18 22:30 미장+네마녀 / **6/19 준틴스 미장 휴장** → 분수주 수동집행 **6/20(월)**.\n\n| 점도표 | 액션 |\n|---|---|\n| **A 비둘기**(인하 유지/확대·완화톤) | 3차 발동, 단 META 분수주 22.5만(~0.25주) **6/20 수동집행**(갭 소화 후=룰3 정합) |\n| **B 중립** | 발동 조건이나 즉시성 없음 → 6/20 분수주 or 국내 전환 |\n| **C 매파/점도표 폐지** | **3차 보류·동결, 현금 보존, 안전핀 재점검.** 고괴리 META·AVGO가 최대 피해주(재매수=고점매수 역설) |\n\n**국내 전환 대안**(폰겹침 17:30~18:00): **두산E 2주(~20만)** 가능(단 트랜치 목적변경 승인 필요·②와 연계). 삼성은 1주(33.7만)도 트랜치 초과+매수존 미도달로 부적합.\n\n**PM 결론 — 정훈 택일 필요**: (a)분수주 6/20 수동집행 수용 (b)국내 두산E 전환 (c)트랜치 규모/대상 재정의. **공통: 비둘기든 매파든 즉시 집행 불가가 디폴트, 2영업일 지연을 '갭 소화 후 진입' 안전장치로 수용.**\n\n---\n\n*투자 자문 아님. 모든 레벨은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v15_2026-06-15",
      "file": "docs/reports/report_v15_2026-06-15.md",
      "title": "정훈 PORTFOLIO DESK · v15 · 2026-06-15 (월) · 최종 종합본",
      "date": "2026-06-15",
      "version": 15,
      "kind": "보고서",
      "preview": "→ 요약: 오늘은 \"손 떼고 관망\"이 정답. 진짜 결정은 내일 BOJ(6/16)·모레 FOMC(6/18) 본 뒤.",
      "content": "# 정훈 PORTFOLIO DESK · v15 · 2026-06-15 (월) · 최종 종합본\n\n> 8데스크 + 경제사냥꾼 6/14~15 신규 4건 통합한 **오늘의 최종판**(v14 대체). KR=6/15 라이브 / US=6/12 종가(미 6/15 밤 첫 거래). 작성 시각 ≈18:45 KST(폰 가용~20:50, KRX 마감). **투자 자문 아님 — 최종 결정은 정훈.**\n\n## 변경점 (v14 → v15)\n- 경제사냥꾼 6/14~15 **신규 4건 통합**(영상2+쇼츠2) + **IB 코스피 목표 줄상향** 강세 재료 추가.\n- **오늘 할 일(TO-DO) 섹션 신설** — 시간 맥락(폰 20:50, 미장 22:30) 반영.\n- 삼성전기 등락률 불일치(⚠️Yahoo +16.63% vs 뉴스 +11.79%) 플래그 유지.\n\n---\n\n## 1. 시장 — 국장 / 미장\n\n### 국장 (6/15 라이브)\n- **코스피 8,545.98(+5.20%) / 코스닥 1,034.03(+3.72%)** — 6/12(+4.63%)에 이어 **이틀째 폭등, 8,500 회복.** 동력: 미·이란 종전 MOU 타결(서명 6/19) → 유가 −4%대 → 위험선호. 상승 71.5% 확산형.\n- **🔑 외인 +1.03조(2거래일 연속 순매수) / 기관 +5,145억 / 개인 −1.48조.** '셀 코리아'(24일 ~75.9조) 종료·전환 지속 = 강세 신호(단 2일차, 누적 미미).\n- **특징주**: 삼성전기 폭등(⚠️+16.6%/+11.8% 정정필요)·두산E 99,800(장중 10만)·조선 +9~10%·현대차 +6.6%·SK하이닉스 +6.4%. **원익IPS −4.8%·테스 −2.9% 역행**(대형 반도체 쏠림). **NAVER +0.4% 소외**(커머스주, 주도축 아님).\n\n### 미장 (6/12 종가 — 미 6/15 밤 첫 거래, v16서 갱신)\n- **S&P 7,431.46(+0.50%)·나스닥 25,888.84·다우 51,202.26·SOX 13,371.47(+1.52%)** 리스크온. NVDA 보합(고점比 −25% 'AI 피로'), ANET +4.37%, SPCX 첫날 +19.2%.\n\n---\n\n## 2. 섹터 (미장·펀더멘털 v13~14 / 국내 6/15 갱신)\n- **반도체·AI인프라**: 삼성 HBM4 인증·양산, NVDA Rubin 2배, **MU 6/24 실적(D-9)** ±20% 슈퍼사이클 시험대, AVGO AI +200%+, ANET fabric $3.5B. 국내: 삼성전기 폭등·SK하이닉스 +6.4%(미ADR 8월). **⚠️메모리 4중첩 집중도.**\n- **전력·피지컬AI**: LG전자 +7.98%(냉각 동맹, +56.9% 최고효자)·현대차 로봇 재평가. **두산E 99,800 10만 돌파 but 추격금지**('1호 발표 어렵다'). 조선 +9~10%, GEV 목표 +29%.\n- **빅테크·플랫폼**: capex 일제 상향, ORCL −11.9%(OpenAI 집중) 경계. META 구독+괴리 +45.9%(FOMC 동결 시 3차 1순위), MSFT Azure +40%, GOOGL Cloud +63%. NAVER 6/15 소외.\n\n---\n\n## 3. 매크로\n- **환율 1,514.06(−0.24%)** 원화 소폭 강세(외인 우호). **BOJ 6/16(내일)** 1.0% 인상 컨센 — 매파 가이던스 강도가 엔캐리 청산 좌우. **FOMC 6/18 03:00**(야간) 동결 98%, 점도표+워시 회견 톤 관건. **유가 브렌트 ~$84**(이란 종전) → CPI 디스인플레 우호. 한은 6월=금융안정회의, 다음 7/16.\n\n---\n\n## 4. 리서치 피드 — 경제사냥꾼 (6/14~15 신규 4건)\n- **① 종전 이후 돈의 방향(6/15)**: 종전=리스크프리미엄 제거→성장주 이동. 이란 6/19 스위스 서명·유가 −3%·SpaceX $160.95(+19%) **[검증]**. → NVDA·MU·삼성 강세 보강.\n- **② 반도체 다음=로봇/피지컬AI(6/14)**: 골드만 **HL만도 목표 109,000원** 지목→상한가 **[검증]**. → 현대차·두산로보(보유) 수혜, \"기대 상한가=과열\" 추격금지 합치.\n- **③ 쇼츠 종전 수혜주(6/15)**: 항공 수혜·정유 역수혜·반도체. **🔧\"골드만 12,000\"은 자막오류→골드만 9,000/시티 8,500 [정정]**.\n- **④ 쇼츠 최태원 이혼→하이닉스(6/15)**: 지분매각 우려 **[미확인]**, 미보유라 영향 낮음.\n- **🟢 신규 강세 재료**: IB 코스피 목표 줄상향 — **골드만 9,000·시티 8,500·NH/JP모건/노무라 10,000~11,000**(현 8,546 대비 +5~29%). 단 \"실적 검증 전 선반영\" 단서.\n\n---\n\n## 5. 리스크 데스크 (Risk Manager · 6/15)\n- **🚦 트리거(발동 0)**: 안전핀 7,500까지 **+13.9%**(여유 최대) / 2차 8,000까지 +6.8% / **두산E 99,800=10만 −0.2% 코앞** / **매수존 삼성 −10.5%·NAVER −5.5%로 더 멀어짐 → 1차 기회 소멸.**\n- **🚨 경보**: 위반 0. ①두산E 10만 돌파=추격금지룰 충돌(되돌림만) ②6/18 네마녀+6/19 준틴스+FOMC 동시→신규진입 보류창 ③미 재매수 분수주 예약불가(정수주만).\n- **집중도**: 메모리·AI베타 4중첩 + 무헤지 환노출 → 엔캐리 청산 시 손익 증폭.\n- **신중(bear)**: **이틀 +10%는 추세 아닌 과열 분출.** 차익실현 쌓이는 구간에 6/16 BOJ + 6/18 FOMC 매파 = **엔캐리 청산 트리거 연속 대기.** 외인 2일 매수분은 청산 시 가장 먼저 빠질 약한 손. → **매수존 멀어짐=과열 회피로 수용, 현금 보존.**\n\n---\n\n## 6. 강세 vs 신중 디베이트\n**🟢 강세**: 외인 2일 연속 순매수로 '셀 코리아' 종료 + 환율 1,514 안정 + 유가 하락 = 매크로 3박자 우호. 랠리가 반도체·조선·방산·전력으로 확산(71.5%), **IB들도 코스피 목표를 9,000~11,000으로 줄상향.** 보유 LG전자(+56.9%)·삼성(+28.1%)·현대차가 동시 점화, 미국 핵심주 컨센은 여전히 +36~46% 상방.\n\n**🔴 신중**: 이틀 +10%는 과열 분출이고 **이란은 아직 서명 전(6/19)** — 헤드라인 선반영, 불발 시 되돌림. 결정적으로 **6/16 BOJ + 6/18 워시 매파 점도표가 엔캐리 청산을 연속 점화할 수 있는 구간.** 메모리·AI 4중첩+무헤지 환노출로 청산 충격에 최약체, 외인 2일 매수분이 먼저 빠진다. NAVER 소외(+0.4%)가 이 랠리=테마·수급 쏠림임을 보여줌. IB 목표 상향도 \"실적 검증 전 기대\"일 뿐.\n\n**⚖️ PM 저울질**: 방향은 강세(코어 전부 홀딩), 단 **이틀 급등 + 6/16~18 클러스터 직전 = 추격 최악 타이밍.** → **신규 진입 보류, 현금 보존, 액션은 BOJ·FOMC 통과 후 되돌림에서.**\n\n---\n\n## 7. PM 종합 (최종)\n\n**오늘의 한 줄 결론: 코스피 이틀 +10% 폭등 + IB 목표 상향으로 강세는 확인됐으나, 이란 미서명(6/19) + 내일 BOJ·모레 FOMC 엔캐리 청산 리스크가 비대칭 하방 → \"전 종목 홀딩 + 신규진입 보류 + 현금 62만 보존\"으로 이벤트 구간 통과. 추격 금지.**\n\n### ✅ 오늘 할 일 (6/15 월, 현재 ~18:45 KST · 폰 가용~20:50)\n| 시간/조건 | 할 일 | 근거 |\n|---|---|---|\n| **지금~20:50** | **아무것도 안 함 = 관망.** KRX 마감(시간외도 18:00 종료), 신규매수 없음 | 이틀 급등 과열 + 추격금지 |\n| **오늘 밤 22:30(미장)** | **신규 진입 금지.** 폰 밖 시간 + 분수주 시장가 예약불가 → 자동 트리거 금지룰 | 룰5·6 / 신규진입 보류 |\n| **두산E 10만 돌파해도** | **사지 마라.** 되돌림·1호 발표 확인 후에만 검토 | '1호 발표 어렵다' + 갭 추격 |\n| **현금 624,771원** | **그대로 보존**(드라이파우더). 분할 매수는 BOJ/FOMC 후 과매도에서 | \"공포에 사라\" 역발상 |\n| **확인만**(가능하면) | 외인 순매수 **3일째 지속 여부**(강세 논지 핵심) — 스크립트 조회실패라 수동 | 외인=코스피 엔진 |\n| **사전 베이킹(6/18용 메모)** | 목 17:30~20:50에 \"FOMC 동결+중립이면 META/AVGO 정수주 지정가 예약\" 준비. 분수주분은 6/20 수동 | FOMC 03:00 폰밖 |\n\n→ **요약: 오늘은 \"손 떼고 관망\"이 정답.** 진짜 결정은 내일 BOJ(6/16)·모레 FOMC(6/18) 본 뒤.\n\n### 보유 16종목 (KR=6/15 / US=6/12 · 원가대비 · 목표=컨센)\n| 종목 | 현재가 | 수익률 | 목표(컨센) | 매수존/액션 | ⭐ | 코멘트 |\n|---|---|---|---|---|---|---|\n| 삼성전자 | 337,000 | **+28.1%** | — | 295~305k(−10.5%) | ★★★★★ | HBM4·외인매수 상위, 추격금지 |\n| LG전자 | 243,500 | **+56.9%** | — | 홀딩 | ★★★★★ | 냉각 동맹 폭발, 손절선 폐기 |\n| 두산로보틱스 | 111,400 | +11.4% | — | 홀딩 | ★★★☆☆ | 로봇 테마(경제사냥꾼 ②) |\n| 현대차 | 647,000 | +2.7% | — | 홀딩 | ★★★★☆ | 보스턴다이내믹스 재평가 |\n| NAVER | 248,000 | −1.0% | ~302,000 | 225~235k(−5.5%) | ★★★☆☆ | 랠리 소외, 정리 후보 상시 |\n| NVDA | $205.19 | +2.9% | $298.93 **+45.7%** | 3차 후보 | ★★★★★ | Rubin 2배 |\n| META | $566.98 | −10.6% | $827.32 **+45.9%** | **3차 1순위** | ★★★★★ | 괴리 최대+구독 |\n| VOO | $681.95 | +5.7% | — | 코어 적립 | ★★★★☆ | S&P 코어 |\n| MSFT | $390.74 | −4.7% | $561.39 **+43.7%** | 홀딩 | ★★★★☆ | Azure +40% |\n| AAPL | $291.13 | +13.2% | $312.72 +7.4% | 홀딩 | ★★★★☆ | Siri=Gemini, 중국 |\n| GOOGL | $359.68 | −7.2% | $432.83 +20.3% | 홀딩 | ★★★★☆ | Cloud +63% |\n| TSLA | $406.43 | −3.8% | $420.55 +3.5% | 홀딩 | ★★★☆☆ | Optimus 촉매 |\n| ORCL | $184.13 | **−20.7%** | $255.38 +38.7% | 관망 | ★★★☆☆ | OpenAI 집중 리스크 |\n| ANET | $163.24 | +0.7% | $189.13 +15.9% | 홀딩 | ★★★★☆ | AI fabric 상향 |\n| MU | $981.61 | **+31.1%** | $828.73 −15.6% | **6/24 실적** | ★★★★☆ | 현재가>목표, 시험대 |\n| AVGO | $382.07 | −9.3% | $522.06 +36.6% | 3차 후보 | ★★★★★ | AI +200%+ |\n\n> 합계: **총자산 8,428,004원** · 주식손익 **+279,448원**(환차익 미반영) · 환차익 반영 **≈+502,307원** · 현금 624,771원 · 환율 1,514.06.\n\n### 워치리스트 (활성)\n| 종목 | 6/15 | 판단 |\n|---|---|---|\n| 두산에너빌리티 | 99,800(10만돌파) | 추격금지, 되돌림·1호발표 후 |\n| 삼성전기 | 1,999,000(⚠️정정필요) | 과열(PER180), 눌림만 |\n| SK하이닉스 | 2,288,000 | 미ADR 8월 대기, 추격금지 |\n| 원익IPS/테스 | −4.8%/−2.9% | 매수존 재평가 관찰 |\n| GEV | $940.66 | $1,216(+29%) 위성 |\n| 조선/한화에어로 | +9~10% | 6/18 후 소화 |\n| SK이노 | 112,700 | 후순위, PBR 1배 하회만 |\n| TMUS/SPCX/STM | — | SPCX 옵션 6/16 |\n\n### 현금 배분 플랜 (3분할, 전부 미집행)\n- **1차 ~12.5만**: NAVER 225~235k/삼성 295~305k — 이틀 급등으로 −5.5~10.5% 멀어짐(미도달).\n- **2차 ~20만**: 이란 결렬 + 코스피 8,000 하회(현 +6.8% 위).\n- **3차 ~22.5만**: FOMC 6/18 후 — 분수주 예약불가+03:00 폰밖 → 비둘기여도 6/20 집행, 정수주 지정가만 베이킹.\n\n### 지켜볼 것 (2주)\n| 일정(KST) | 내용 | 폰 |\n|---|---|---|\n| **6/16(화)** | **BOJ 1.0% 인상**(엔캐리) + FOMC 1일차 + SPCX 옵션 | △ |\n| **6/18(목) 03:00** | **FOMC+점도표+워시** → 3차 / 대미투자법 / 네마녀 / MU 옵션 | ✗ |\n| 6/19(금) | 美 준틴스 휴장 / **이란 스위스 서명** / 워치 유예 제외 | — |\n| 6/22 주간 | SK하이닉스 ADR SEC 승인 가능성 | — |\n| 6/24(수) | **MU 실적**(슈퍼사이클 시험대) | ✗ |\n| 7/16(목) | 한국은행 금통위 | ○ |\n\n---\n\n## 8. 오늘의 이슈 선택지\n1. **6/16 BOJ 시나리오별 코스피·내 포트 영향** (매파 강도별 엔캐리 청산 폭 + 안전핀 대응)\n2. **두산에너빌리티 10만 돌파 플레이북** (KUIC 1호 vs 발표 지연, 진입·되돌림 레벨)\n3. **삼성전기 폭등 해석 + 등락률 재확인** (모멘텀 vs PER 180배 과열)\n4. **6/18 FOMC 3차 트랜치 실행 매뉴얼** (비둘기/매파 × 정수주 베이킹 + 6/20 집행)\n\n---\n\n## STATE SNAPSHOT\n```\n[STATE SNAPSHOT v15 2026-06-15]\n현금: 624,771원 (트랜치 1차/2차/3차 전부 미집행)\n보유변동: 없음 (16종목 유지)\n시세기준: KR=6/15 라이브(코스피 8,545.98 +5.20%) / US=6/12 종가 / USD/KRW 1,514.06\n총자산: 8,428,004원 · 주식손익 +279,448(환차익 반영 +502,307)\n오늘 할 일: 관망(KRX 마감)·신규진입 보류·현금 보존 / 두산E 돌파 추격금지 / 6/18 FOMC 정수주 베이킹 준비\n워치리스트(활성): 두산에너빌리티(10만)·삼성전기(⚠️)·SK하이닉스·원익IPS·테스·GEV·조선·한화에어로·SK이노·TMUS·SPCX·STM\n대기 트리거:\n  ① 6/16 BOJ 1.0% → 엔캐리 청산 모니터(안전핀 7,500, +13.9%)\n  ② 6/18 03:00 FOMC+점도표 → 3차(비둘기=6/20 집행)\n  ③ 6/19 이란 스위스 서명(미서명=되돌림 리스크)\n  ④ 6/24 MU 실적\n  ⑤ 두산E 10만 돌파 → 추격금지\n영구교정(누적):\n  - 이란 MOU 6/14 타결·6/19 스위스 서명(주말 서명 아님)\n  - 6/15 코스피 +5.20% 이틀째, 외인 2일 연속 순매수(+1.03조)\n  - IB 코스피 목표: 골드만 9,000·시티 8,500·NH/JP모건/노무라 10,000~11,000(\"12,000\"은 자막오류)\n  - HL만도 골드만 목표 109,000원 상한가(로봇, 미보유)\n  - ⚠️ 삼성전기 6/15 등락률 불일치(Yahoo +16.63% vs 뉴스 +11.79%) 종가 재확인 필요\n리서치: 경제사냥꾼 6/14~15 신규 4건 통합 완료\n다음 버전: v16\n```\n\n*투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v14_2026-06-15",
      "file": "docs/reports/report_v14_2026-06-15.md",
      "title": "정훈 PORTFOLIO DESK · v14 · 2026-06-15 (월)",
      "date": "2026-06-15",
      "version": 14,
      "kind": "보고서",
      "preview": "번호로 답하면 그 항목만 심층:",
      "content": "# 정훈 PORTFOLIO DESK · v14 · 2026-06-15 (월)\n\n> 국장 6/15 라이브 세션 반영판. 국장·리스크·정량 신선 수집 / 미장·섹터·매크로·리서치는 v13(동일 미장 6/12 종가) 재사용. **투자 자문 아님 — 최종 결정은 정훈.**\n\n## 변경점 (직전 v13 대비)\n- **코스피 8,545.98 (+5.20%) — 이틀째 폭등, 8,500선 회복.** 외인 **2거래일 연속 순매수**(+1.03조), 기관 +5,145억, 개인 −1.48조.\n- **🔧 이란 MOU 정정**: 주말 서명 아님 → **6/14 협상 타결, 6/19 스위스 공식 서명 예정(당일 미집행)**. 트럼프 \"15일 서명 가능\" 발언은 타결로 갈음. → 갭업은 '서명 기대 선반영', 서명 전까지 되돌림 리스크 잔존.\n- **삼성전기 +16.63% 폭등**(v13 6/12 −5%서 급반전), **두산에너빌리티 99,800 장중 10만 돌파**, 조선 한화오션 +9.49%·HD현대중 +9.85%, 현대차 +6.59%, SK하이닉스 +6.42%.\n- **원익IPS −4.8%·테스 −2.85% 역행**(수급이 코스피 대형 반도체로 쏠려 코스닥 소부장 소외).\n- 보유·현금·트랜치 변동 없음. 미장은 6/12 종가 그대로(미 6/15 밤 첫 거래).\n- 총자산 8.35M→**8.43M**, 주식손익 +19만→**+28만**(환차익 반영 추정 **+50만**).\n\n---\n\n## 1. 시장 — 국장 / 미장\n\n### 국장 (kr-market-desk · 6/15 라이브)\n- **코스피 8,545.98(+5.20%, +422p) / 코스닥 1,034.03(+3.72%)** — 이틀 누적 +10%대. 동력: **미·이란 종전 MOU 타결**(서명 6/19) → 유가 −4%대 급락 → 위험선호 점화. 상승종목 71.5%(확산형 랠리).\n- **🔑 외인 +1.03조(2일 연속 순매수) / 기관 +5,145억 / 개인 −1.48조.** 24거래일 '셀 코리아'(~75.9조 순매도) 멈추고 **연속 매수 전환 = 강세 신호 지속** — 단 2일차, 누적은 아직 미미 → 추세 정착은 추가 확인.\n- **주도**: 반도체(삼성·SK하이닉스) + 종전 순환매(조선·방산·중동재건·항공) + 전력·원전. **특징주 삼성전기 +16.63%·두산E +7.20%(장중 10만)·조선 +9~10%.**\n- **NAVER 부진**: 지수 +5.2%에 **+0.4% 소외** — 랠리 주도축(반도체·조선·방산·전력)이 아닌 커머스주로 분류, 역대 최대 실적에도 멀티플 디스카운트 지속. 구조적 소외.\n\n### 미장 (us-market-desk · v13 재사용, 6/12 종가 — 변동 없음)\n- **S&P500 7,431.46(+0.50%) / 나스닥 25,888.84(+0.31%) / 다우 51,202.26(+0.70%) / SOX 13,371.47(+1.52%)** — 리스크온, VIX 17.68(단일출처). **NVDA +0.16% 보합**(고점比 −25% 'AI 피로'), ANET +4.37% 주도. SPCX 첫날 +19.2%.\n- 6/15 밤(KST) 미 정규장 재개 → v15에서 갱신. 6/18 FOMC·네마녀, 6/19 준틴스 휴장 클러스터 임박.\n\n---\n\n## 2. 섹터 (v13 재사용 — 미장·펀더멘털 변동 없음, 국내분만 6/15 갱신)\n\n### 반도체·AI인프라\n- **삼성전자** HBM4 NVIDIA/AMD 인증·2월 양산(11.7Gb/s), 6/15 외인 매수 상위. **NVDA** Rubin 출하 2배, UBS $275. **MU 6/24 실적(D-9)** 컨센 EPS $19.72·±20% — 슈퍼사이클 시험대. **AVGO** AI매출 Q3 +200%+. **ANET** AI fabric $3.5B 상향.\n- 국내 6/15: **삼성전기 +16.63% 폭등**(MLCC·FC-BGA AI소부장 대장, 목표 iM230/DB300만), **SK하이닉스 +6.42%**(미 ADR 8월·6/22주 SEC 승인 가능성). **원익IPS −4.8%·테스 −2.85% 역행**(대형 반도체 쏠림). **⚠️ 메모리 4중첩(삼성·NVDA·MU·SK하이닉스) 집중도.**\n\n### 전력·인프라·피지컬AI\n- **LG전자 +7.98%** 냉각 CDU·NVIDIA DSX 동맹 모멘텀 폭발(+56.9% 최고 효자, 손절선 폐기 유지). **현대차 +6.59%** 보스턴다이내믹스 로봇 재평가. **두산로보** Q1 매출 +189.7%·적자 지속.\n- **두산에너빌리티 99,800(+7.20%, 장중 10만 돌파)** — 2026 수주 14.3조, KUIC 1순위. **단 대미투자법 '1호 당월 발표 어렵다'(산업장관) → 돌파 추격금지.** 조선바스켓 +9~10%(美MRO 독식). **GEV** 목표 $1,216(+29%) AI전력 순수도 1위.\n\n### 빅테크·플랫폼\n- capex 일제 상향(MSFT $190B·GOOGL $180~190B·META $145B), **ORCL −11.9% 급락**(OpenAI 집중·희석)이 섹터 단기 경계. **META** 광고 견조+구독 출시(FOMC 동결 시 3차 1순위, 괴리 +45.9%). **MSFT** Azure +40%, **GOOGL** Cloud +63%. **AAPL** Siri=Gemini 구동·중국 리스크. **NAVER** 젠슨황 AI팩토리 호재에도 6/15 소외.\n\n---\n\n## 3. 매크로 데스크 (v13 재사용 + 6/15 환율 갱신)\n- **환율 USD/KRW 1,514.06(−0.24%)** — 1,510중반, v13 대비 소폭 원화 강세(외인 수급 우호 신호). 미국주 환산익 소폭 축소.\n- **BOJ 6/16(내일, 낮~오후)**: 0.75→**1.0% 인상 컨센 94%**(시장 72~88%), 연말 1.25% 기대. **매파 가이던스 강도가 엔캐리 청산 좌우.**\n- **FOMC 6/18 03:00(야간 대응불가)**: 동결 98%. 핵심 점도표+워시 첫 회견 톤, 2026 인하 0회 가격반영, 점도표 폐지 가능성 보도.\n- **유가 브렌트 ~$84(이란 종전 → 추가 하락)** → CPI 디스인플레 우호. 5월 PPI +6.5%·CPI 4.2%, 다음 7월 중순. 한은 6월=금융안정회의, 다음 7/16.\n\n---\n\n## 4. 리서치 피드 — 경제사냥꾼 (6/14~15 신규 4건 탐색 완료)\n- **① \"종전 합의 이후 돈의 방향\" (6/15)**: 종전=리스크 프리미엄 제거 → 원유·산유국에서 성장주·소비국으로 자금 이동. 이란 6/19 스위스 서명·호르무즈 개방 **[검증]**, 브렌트 $84·WTI $81 3% 하락 **[검증]**, SpaceX $160.95(+19%)·$750억 조달 **[검증]**. → NVDA·MU·삼성 코어 강세 논지 보강(유가↓→금리부담↓→AI 반도체 재평가).\n- **② \"반도체 다음=로봇/피지컬AI\" (6/14)**: 골드만 6/11 로보틱스 리포트에서 **HL만도 목표 109,000원** 지목 → 상한가(+30%) **[검증]**. 한국 로봇밀도 1위 **[미확인-IFR 원자료 확인 권장]**. → **현대차·두산로보(보유)** 직접 수혜, 단 \"매출 1% 미만 기대 상한가=과열\" → 추격금지룰 합치.\n- **③ 쇼츠 \"종전 수혜주\" (6/15)**: 항공(유가↓ 수혜)·정유(역수혜 마진압박 **[검증]**)·반도체(금리인하 기대). **🔧 \"골드만 목표 12,000\"은 자막 오류 → 정설은 골드만 9,000/시티 8,500 [정정]**.\n- **④ 쇼츠 \"최태원 이혼→하이닉스\" (6/15)**: 재산분할 시 SK 지배구조 지분매각 우려 **[미확인]**. SK하이닉스 미보유라 직접 영향 낮음(거버넌스 참고).\n- **🟢 신규 강세 재료**: IB 코스피 목표 줄상향 — **골드만 9,000·시티 8,500·NH/JP모건/노무라 10,000~11,000**(현 8,546 대비 +5~29% 상방). 단 \"실적 검증 전 기대 선반영\"(master §1) 단서 유효.\n\n---\n\n## 5. 리스크 데스크 (Risk Manager · 6/15 라이브)\n- **🚦 트리거(발동 0)**: 안전핀 7,500까지 **+13.9%**(여유 최대) / 2차 8,000까지 +6.8%(발동성 낮아짐) / **두산E 99,800 = 10만 −0.2% 코앞** / 매수존 **삼성 −10.5%·NAVER −5.5%로 더 멀어짐 → 1차 매수 기회 사실상 소멸.**\n- **🚨 경보**: 위반 0. ①**두산E 10만 돌파 = 추격금지룰 충돌** — '1호 발표 어렵다' 신중론 + 이틀 급등 직후 돌파는 전형적 이벤트 갭 추격 → **당일 진입 금지, 되돌림에서만**. ②6/18 네마녀+6/19 준틴스+FOMC 동시 → 신규진입 보류창. ③미 재매수 분수주 예약불가(정수주만 베이킹).\n- **집중도**: 메모리·AI베타 4중첩(+SK하이닉스 시 5중첩) 동조 하락 + 무헤지 환노출이 엔캐리 청산 시 손익 증폭.\n- **신중(bear)**: **이틀 +10%는 정상 추세가 아니라 숏커버·외인전환·이란 모멘텀의 압축 분출=과열.** 차익실현 매물 쌓이는 구간에 **6/16 BOJ + 6/18 FOMC 매파 = 엔캐리 청산 트리거 연속 대기.** 청산 시 외인 비중 높은 코스피가 가장 크게 되돌리고, 외인 순매수 전환분은 가장 먼저 빠질 '약한 손'. **→ 매수존이 멀어진 건 기회 상실이 아니라 과열 회피로 해석. 현금 보존·관망.**\n\n---\n\n## 6. 강세 vs 신중 디베이트\n\n**🟢 강세**: 외인이 2거래일 연속 순매수로 '셀 코리아'(24일 75.9조 매도)를 끊었고, 환율도 1,514로 안정되며 매크로 3박자(수급·환율·유가)가 동시에 우호로 돌아섰다. 이란 종전이 유가를 눌러 인플레·연준 부담을 덜고, 랠리가 반도체·조선·방산·전력으로 폭넓게 확산(상승 71.5%)됐다. 보유 LG전자(+56.9%)·삼성(+28.1%)·현대차(로봇 재평가)가 동시에 불을 뿜고, 미국 핵심주 컨센은 여전히 +36~46% 상방을 가리킨다.\n\n**🔴 신중**: 이틀 +10%는 추세가 아니라 과열 분출이다. **이란 MOU는 아직 서명 전(6/19)** — 헤드라인 기대만 선반영됐고 불발·지연 시 되돌림 빌미다. 결정적으로 **내일 6/16 BOJ 1.0%(+연말 1.25% 가이던스)와 6/18 워시 매파 점도표가 엔캐리 청산을 연속 점화할 수 있는 구간**이다. 내 포트는 메모리·AI베타 4중첩 + 무헤지 환노출로 청산 충격에 가장 취약하고, 외인 2일 매수분은 위험회피 시 가장 먼저 빠진다. NAVER의 소외(+0.4%)는 이 랠리가 펀더멘털이 아닌 테마·수급 쏠림임을 보여주는 단면이다.\n\n**⚖️ PM 저울질**: 방향은 강세(코어 홀딩 전부 유지)지만, **이틀 급등 + 6/16~18 이벤트 클러스터 직전 = 추격 최악 타이밍.** 강세 재료는 대부분 가격에 반영됐고 하방 비대칭이 크다. → **신규 진입 보류, 현금 62만 보존, 매수존 멀어짐은 과열 회피로 수용.** 액션은 BOJ·FOMC 통과 후 되돌림에서.\n\n---\n\n## 7. PM 종합 (최종)\n\n**오늘의 한 줄 결론: 코스피 이틀 +10% 폭등으로 강세 추세는 확인됐으나, 이란 서명 미집행(6/19) + 내일 BOJ·모레 FOMC 엔캐리 청산 리스크가 비대칭 하방 → \"전 종목 홀딩 + 신규진입 보류 + 현금 보존\"으로 과열·이벤트 구간을 통과. 추격 금지.**\n\n### 보유 16종목 (KR=6/15 라이브 / US=6/12 · 원가 대비 · 목표=컨센평균)\n| 종목 | 현재가 | 수익률 | 목표가(컨센) | 매수존/액션 | ⭐ | 코멘트 |\n|---|---|---|---|---|---|---|\n| 삼성전자 | 337,000 | **+28.1%** | — | 295~305k(−10.5%) | ★★★★★ | HBM4·외인매수 상위, 추격금지 |\n| LG전자 | 243,500 | **+56.9%** | — | 홀딩 | ★★★★★ | 냉각 동맹 폭발, 손절선 폐기 |\n| 두산로보틱스 | 111,400 | +11.4% | — | 홀딩 | ★★★☆☆ | 매출 급증·적자, 로봇 테마 |\n| 현대차 | 647,000 | +2.7% | — | 홀딩 | ★★★★☆ | 보스턴다이내믹스 재평가 +6.6% |\n| NAVER | 248,000 | −1.0% | ~302,000 | 225~235k(−5.5%) | ★★★☆☆ | 랠리 소외, 정리 후보 상시 |\n| NVDA | $205.19 | +2.9% | $298.93 **+45.7%** | 3차 후보 | ★★★★★ | Rubin 2배, strong_buy |\n| META | $566.98 | −10.6% | $827.32 **+45.9%** | **3차 1순위** | ★★★★★ | 괴리 최대+구독 수익화 |\n| VOO | $681.95 | +5.7% | — | 코어 적립 | ★★★★☆ | S&P 인덱스 코어 |\n| MSFT | $390.74 | −4.7% | $561.39 **+43.7%** | 홀딩 | ★★★★☆ | Azure +40%, capex 우려 |\n| AAPL | $291.13 | +13.2% | $312.72 +7.4% | 홀딩 | ★★★★☆ | Siri=Gemini, 중국 리스크 |\n| GOOGL | $359.68 | −7.2% | $432.83 +20.3% | 홀딩 | ★★★★☆ | Cloud +63%, 규제 노이즈 |\n| TSLA | $406.43 | −3.8% | $420.55 +3.5% | 홀딩 | ★★★☆☆ | Hold, Optimus 촉매 |\n| ORCL | $184.13 | **−20.7%** | $255.38 +38.7% | 관망 | ★★★☆☆ | OpenAI 집중 리스크 |\n| ANET | $163.24 | +0.7% | $189.13 +15.9% | 홀딩 | ★★★★☆ | AI fabric $3.5B 상향 |\n| MU | $981.61 | **+31.1%** | $828.73 −15.6% | **6/24 실적 D-9** | ★★★★☆ | 현재가>목표, 슈퍼사이클 시험대 |\n| AVGO | $382.07 | −9.3% | $522.06 +36.6% | 3차 후보 | ★★★★★ | AI매출 +200%+, strong_buy |\n\n> 합계: **총자산 8,428,004원** · 주식 평가손익 **+279,448원**(환차익 미반영) · 환차익 반영 추정 **≈+502,307원** · 현금 624,771원 · 환율 1,514.06.\n\n### 워치리스트 (활성)\n| 종목 | 6/15 | 메모 | 판단 |\n|---|---|---|---|\n| 두산에너빌리티 | 99,800(+7.2%) | 10만 장중 돌파, KUIC 1순위 | **돌파 추격금지**, 되돌림·1호발표 확인 후 |\n| 삼성전기 | 1,999,000(+16.6%⚠️) | AI소부장 대장 폭등 (⚠️Yahoo종가 +16.63% vs 뉴스 장중 +11.79% 불일치=정정필요) | 과열(PER 180배), 추격금지·눌림만 |\n| SK하이닉스 | 2,288,000(+6.4%) | 미 ADR 8월(6/22주?) | 정식상장 대기, 추격금지 |\n| 원익IPS/테스 | −4.8%/−2.9% | 코스닥 소부장 역행 | 매수존 재평가 관찰 |\n| GEV | $940.66 | $1,216(+29%) | AI전력 위성 포지션 |\n| 조선바스켓/한화에어로 | +9~10%/+0.6% | 美MRO·대미투자 | 6/18 후 소화 관찰 |\n| SK이노 | 112,700(+6.2%) | SMR 장기옵션 | 후순위, PBR 1배 하회만 |\n| TMUS / SPCX / STM | — | SPCX 옵션 6/16·나스닥100 | 관망 |\n\n### 제안 액션\n- **전 종목 홀딩.** 패닉·추격 모두 금지. **신규 진입 보류**(이틀 급등 과열 + BOJ/FOMC/네마녀/준틴스 클러스터).\n- **두산E 10만 돌파해도 당일 추격 금지** — '1호 발표 어렵다' + 갭 추격 패턴, 되돌림에서만 분할 검토.\n- **현금 624,771원 = 드라이파우더 보존.** BOJ·FOMC 통과 후 엔캐리 청산 과매도가 오면 분할(소화 후).\n\n### 현금 배분 플랜 (3분할, 전부 미집행)\n- **1차 ~12.5만**: NAVER 225~235k / 삼성 295~305k 눌림 — **이틀 급등으로 −5.5~10.5% 멀어짐, 당분간 미도달.**\n- **2차 ~20만**: 이란 결렬 + 코스피 8,000 하회(현 +6.8% 위).\n- **3차 ~22.5만**: FOMC 6/18 후. **단 분수주 예약불가+03:00 폰밖 → 비둘기여도 6/20 집행 / 매파면 보류. 정수주 지정가만 베이킹.**\n\n### 지켜볼 것 (2주 캘린더)\n| 일정(KST) | 내용 | 폰가용 |\n|---|---|---|\n| **6/16(화)** | **BOJ 1.0% 인상 결정**(엔캐리) + FOMC 1일차 + SPCX 옵션 개시 | △ 발표시각 |\n| **6/18(목) 03:00** | **FOMC+점도표+워시 회견** → 3차 / 대미투자법 시행 / 네마녀 / MU 옵션 | ✗ 야간 |\n| 6/19(금) | 美 준틴스 휴장 / **이란 MOU 스위스 서명 예정** / 워치 유예 제외 | — |\n| 6/22 주간 | SK하이닉스 미 ADR SEC 승인 가능성 | — |\n| 6/24(수) | **MU 실적**(슈퍼사이클 시험대) | ✗ 야간 |\n| 7/16(목) | 한국은행 금통위 | ○ |\n\n---\n\n## 8. 오늘의 이슈 선택지\n번호로 답하면 그 항목만 심층:\n1. **6/16 BOJ 시나리오별 코스피·내 포트 영향** (매파 가이던스 강도별 엔캐리 청산 폭 + 안전핀 대응)\n2. **두산에너빌리티 10만 돌파 플레이북** (KUIC 1호 vs '발표 지연' 신중, 진입 조건·되돌림 레벨)\n3. **삼성전기 +16.6% 폭등 해석** (AI소부장 모멘텀 vs PER 180배 과열, 워치 잔류/진입 여부)\n4. **6/18 FOMC 3차 트랜치 실행 매뉴얼** (비둘기/매파 × 정수주 베이킹 + 6/20 집행)\n\n---\n\n## STATE SNAPSHOT\n```\n[STATE SNAPSHOT v14 2026-06-15]\n현금: 624,771원 (트랜치 1차/2차/3차 전부 미집행)\n보유변동: 없음 (16종목 유지)\n시세기준: KR=6/15 라이브(코스피 8,545.98 +5.20%) / US=6/12 종가 / USD/KRW 1,514.06\n총자산: 8,428,004원 · 주식손익 +279,448(환차익 반영 +502,307)\n워치리스트(활성): 두산에너빌리티(10만돌파)·삼성전기(+16.6%)·SK하이닉스·원익IPS·테스·GEV·조선바스켓·한화에어로·SK이노·TMUS·SPCX·STM\n대기 트리거:\n  ① 6/16 BOJ 1.0% 인상 → 엔캐리 청산 모니터(안전핀 7,500, 현 +13.9%)\n  ② 6/18 03:00 FOMC+점도표 → 3차(비둘기=6/20 집행, 분수주 예약불가)\n  ③ 6/19 이란 MOU 스위스 서명 (타결됐으나 미서명 = 되돌림 리스크)\n  ④ 6/24 MU 실적 → 메모리 슈퍼사이클 시험대\n  ⑤ 두산E 10만 돌파 → 추격금지, 되돌림·1호발표 확인 후\n영구교정(신규):\n  - 이란 MOU = 6/14 협상 타결, 6/19 스위스 공식 서명 예정(주말 서명 아님). 트럼프 \"15일 서명\" = 타결 갈음\n  - 6/15 코스피 +5.20%(8,545.98) 이틀째 폭등, 외인 2거래일 연속 순매수(+1.03조)\n  - 삼성전기 6/15 +16.63%(6/12 −5%서 급반전), 두산E 99,800 장중 10만 돌파, 조선 +9~10%\n  - 원익IPS/테스 코스닥 소부장 6/15 역행 하락(−4.8%/−2.9%)\n  - IB 코스피 목표 줄상향: 골드만 9,000·시티 8,500·NH/JP모건/노무라 10,000~11,000 (경제사냥꾼 \"12,000\"은 자막오류 정정)\n  - HL만도 골드만 목표 109,000원 → 상한가(로봇 테마, 정훈 미보유)\n  - ⚠️ 삼성전기 6/15 등락률 불일치: Yahoo종가 +16.63% vs 뉴스 장중 +11.79% → 종가 재확인 필요\n리서치: 경제사냥꾼 6/14~15 신규 4건(영상2+쇼츠2) 탐색·분류 완료\n다음 버전: v15\n```\n\n*투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v13_2026-06-14",
      "file": "docs/reports/report_v13_2026-06-14.md",
      "title": "정훈 PORTFOLIO DESK · v13 · 2026-06-14 (토)",
      "date": "2026-06-14",
      "version": 13,
      "kind": "보고서",
      "preview": "번호로 답하면 그 항목만 다음에 심층:",
      "content": "# 정훈 PORTFOLIO DESK · v13 · 2026-06-14 (토)\n\n> 8데스크 풀가동 심층판(국장·미장·반도체AI·전력피지컬·빅테크·매크로·리서치·리스크). 시세=6/12 종가(주말 휴장). **투자 자문 아님 — 모든 레벨은 분석 참고, 최종 결정은 정훈.**\n\n## 변경점 (직전 v12 대비)\n- **데스크 구조 재편 첫 적용**: 시장 데스크 → 국장/미장 분리 + 섹터 3축 + 리스크 매니저 독립. TradingAgents 패턴(애널리스트→강세/신중 디베이트→리스크→PM).\n- **두산에너빌리티 고점 정합성 해소**: 52주 고점 **139,200** / 5월 12만원대 거래 사실 / 현재가 93,100 = 고점 대비 −25~33% 조정. (v12 부록 ⚠️재검증 → 확정)\n- **6/18 대미투자법 \"1호 프로젝트 당월 발표 어렵다\"(산업장관)** — 기대 선반영/갭다운 리스크 신규 플래그.\n- 보유·현금·트랜치 변동 없음(전부 미집행).\n\n---\n\n## 1. 시장 — 국장 / 미장\n\n### 국장 (kr-market-desk)\n- **코스피 8,123.62 (+4.63%, +359.67p) / 코스닥 1,029.05 (+3.22%)** — 6/12 종가, 8,100선 안착·올해 25번째 매수 사이드카.\n- **수급: 외인 +2.14조 / 기관 +2.32조 / 개인 −5.60조** (코스피). **🔑 외인 25거래일 만에 순매수 전환** — 매수 1·2위가 **SK하이닉스 +1.29조·삼성전자 +0.88조**로 반도체 집중. 단 **전환 첫날(연속 1일)** → 추세 vs 숏커버 후속 확인 필요. *연기금 개별·외인 누적액은 미확인.*\n- **특징주**: 반도체 소부장 초강세 — **원익IPS 상한가(+30%)**, 코스닥 8종 상한가. 방산·조선·원전 동반 강세.\n- **🚨 6/15(월) 개장 전 갭 변수 = 미·이란 종전 MOU**: 서명 시 유가 급락→위험선호↑(갭업 명분) ↔ 방산·조선 차익실현 압력 양면. **서명 불발/지연 시 갭다운**.\n\n### 미장 (us-market-desk)\n- **S&P500 7,431.46 (+0.50%) / 나스닥 25,888.84 (+0.31%) / 다우 51,202.26 (+0.70%) / SOX 13,371.47 (+1.52%)** — 6/12 마감, 리스크온. **VIX 17.68**(미확인·단일출처).\n- BofA \"에이전틱 AI=차세대 촉매\"로 칩 매수 회귀, **ANET +4.37%** 주도. **단 NVDA +0.16% 보합**(6월 고점 대비 −25%, 'AI 트레이드 피로' 논쟁). MU −1.43%·AVGO −0.91%·AAPL −1.52% 차별화. **SPCX 첫날 +19.2%($160.95)**.\n- 다음 주 **이벤트 클러스터(FOMC 6/18 03:00 + 네마녀 6/18 + 준틴스 휴장 6/19)** → 만기 롤오버 + 휴장 공백이 변동성 증폭 구조.\n\n---\n\n## 2. 섹터 — 반도체AI / 전력·피지컬 / 빅테크\n\n### 반도체·AI인프라 (semi-ai-desk)\n- **테마**: HBM4 양산 본격화 + 젠슨황 방한으로 \"한국 메모리=대체불가\" 재확인. NVIDIA Rubin 풀생산 진입 → HBM4 타이트.\n- **삼성전자**: HBM4 NVIDIA/AMD 인증 통과·2월 양산(11.7Gb/s 업계 최고), HBM4 점유율 28% 전망. **NVDA**: Q1 매출 $81.6B(+85%), Rubin 출하 2배, UBS 목표 $275. **MU**: **6/24 실적(D-10)** EPS 컨센 $19.72, 옵션 ±20% 반영. **AVGO**: AI매출 Q3 $16B(+200%+). **ANET**: AI fabric 타깃 $3.5B로 상향.\n- **SK하이닉스**(워치): 미 ADR 8월 목표·6/22주 SEC 승인 가능성, HBM4 NVIDIA 60~70% 확보. **원익IPS**(워치): 2026 영업익 +87.7% 전망이나 상한가 직후 추격금지.\n- **⚠️ 집중도 경고**: 삼성·MU·NVDA + 워치 SK하이닉스 = HBM/AI 단일 사이클 4중첩. **6/24 MU 실적이 \"슈퍼사이클 실재 vs 정점\" 1차 시험대**.\n\n### 전력·인프라·피지컬AI (power-physical-desk)\n- **테마**: 6/18 대미투자법 시행($3,500억)+KUIC(자본 2조) 출범 = 원전·SMR·조선 D-day. **단 \"1호 프로젝트 당월 발표 어렵다\"(산업장관) → 갭 경계.**\n- **LG전자**: DCW2026 CDU 1.4MW(2배↑)·NVIDIA DSX 프리패브 협력, 인증 훼손 신호 없음 → 손절선 폐기룰 유지. **현대차**: 보스턴다이내믹스 휴머노이드 양산 구체화(아틀라스 2028). **두산로보틱스**: Q1 매출 +189.7%이나 영업손실 지속. **TSLA**: Hold, Optimus 7~8월 생산 촉매.\n- **두산에너빌리티**(워치): 93,100(52주고 139,200, 고점比 −25~33% 조정), 2026 수주 14.3조, KUIC 1순위 후보, **10만 트리거 미달**. **GEV**: 목표 $1,216(+29%), 백로그 $1,630억 — AI전력 순수도 최상. **조선바스켓**: 美해군 MRO 4건 독식.\n- **순수도 순위**: GEV > 두산에너빌리티 > SK이노(옵션성). LG전자는 냉각(별도 트랙).\n\n### 빅테크·플랫폼 (bigtech-platform-desk)\n- **테마**: 하이퍼스케일러 capex 일제 상향(MSFT $190B·GOOGL $180~190B·META $145B) → \"지출은 신앙, 수익화는 검증\" 국면. **ORCL −11.9% 급락**(RPO $638B에도 OpenAI 집중·희석 우려)이 섹터 단기 조정 트리거.\n- **META**: 광고 견조(노출+19%·단가+12%) + **Meta One 구독 출시**로 수익화 전환. **MSFT**: Azure +40%cc, AI런레이트 $37B. **GOOGL**: Cloud +63%, 백로그 $460B+. **AAPL**: WWDC 신형 Siri를 **Gemini 구동**(자체 LLM 한계), 중국 리스크. **NAVER**: 젠슨황 방한 방문, GAK GW급 AI팩토리.\n- **SPCX**(워치): 옵션 6/16 개시·나스닥100 패스트엔트리(6월말~7월초) 수급 양방향, 추격금지.\n\n---\n\n## 3. 매크로 데스크 (macro-desk)\n- **환율 USD/KRW 1,517.89(+0.13%)** — 1,500중반 고착. 외인 환차손 부담 ↔ 미국주 환산익 방어. 1,500 하향 돌파 시 외인 우호 시그널.\n- **FOMC 6/18 03:00(야간 대응불가)**: 동결 98.2%. 핵심은 **점도표+워시 첫 회견 톤**. 시장은 2026 인하 0회(폴리마켓 57%) 가격반영, **점도표 폐지 가능성** 보도(변동성 재료).\n- **BOJ 6/16(낮~오후)**: 0.75→**1.0% 인상 컨센 94%**(≈30년래 최고), 연말 1.25% 기대 79%. **매파 가이던스 강도가 엔캐리 청산 좌우**.\n- **유가 브렌트 ~$86 8주 최저**(미·이란 휴전 기대) → CPI 에너지 디스인플레 우호. 5월 PPI +6.5%·CPI 4.2%, 다음 발표 7월 중순. **한은 6월=금융안정회의(금리 결정 없음), 다음 7/16.**\n\n---\n\n## 4. 리서치 피드 — 경제사냥꾼 (research-feed)\n*봇차단 우회 성공, 6/13~14 영상·쇼츠 4건. 수치 교차검증.*\n- **① \"반도체 다음 = 로봇/피지컬AI\" (6/14)**: 골드만 휴머노이드 2035 $380억(6배 상향) **[검증]**. 한국 로봇밀도 1,220대 1위 **[검증]**, 단 2~4위 순위·수치 **[정정]**(싱가포르 770·3위 중국·독일 429). HL만도 액추에이터 신사업 **[부분검증]**. → **현대차·두산로보** 직접 수혜, 단 \"완성형보다 부품 수주 공시 보라\"는 신중론 = 추격금지룰 합치.\n- **② \"다음 주 진짜 포인트\" (6/13)**: FOMC 점도표+워시 데뷔·BOJ·네마녀·대미투자법 클러스터 **[검증]**. BOJ 설문 \"94%\"는 **[정정]**(실제 72~88%). CPI 4.2% **[미확인]**(방향만). 대미투자 \"원전 거론(확정 아님)\"으로 채널이 정확히 신중 표현.\n- **③ 쇼츠 \"삼전·닉스 3배 레버리지 LSE 상장\" [검증]**: 단일종목 3배 ETP 글로벌 최초, 원화선물 통해 코스피 변동성 전이 가능 → 본주·분산이 구조적으로 안전(레버리지 사용 안 함 룰4 합치).\n- **④ 쇼츠 \"스페이스X ETF TOP3\" [검증/일부 미확인]**: SPCX $135 공모·$750억 조달·밸류 $1.75조. ETF 티커·비중은 자막 훼손으로 미확인.\n\n---\n\n## 5. 리스크 데스크 (Risk Manager · risk-desk)\n- **🚦 트리거 (발동 0, 전부 대기)**: 안전핀 7,500까지 **+8.3%(624p)** / 2차 8,000까지 **+1.5%(124p, 가장 근접)** / NAVER 매수존 +5.1%·삼성 +5.7% 위 / 두산E 10만까지 −6.9% / 이벤트 이란·FOMC·SK하이닉스ADR.\n- **🚨 경보(위반 0, 근접·구조 3건)**: ①8,000(2차)≠7,500(동결) 혼동 금지 — 8,000 하회는 '이란 결렬 동반 시 2차 투입', 전면 동결은 7,500 하회. ②원익IPS 상한가 추격금지 활성. ③**미 재매수 실행 제약**: 3차 225k로 NVDA·META·AVGO 1주 전부 부족 + 분수주=시장가라 예약 불가 + FOMC 03:00 폰 밖 → **\"비둘기=즉시 재매수\" 사실상 불가, 6/20(월) 집행으로 2영업일 지연**.\n- **집중도**: 메모리·AI베타 4중첩(삼성·NVDA·MU·SK하이닉스)이 단일 최대 리스크(상관 1 수렴). 미국 11종목 전부 단일 원/달러 노출(현 수익의 절반 이상이 환차익=약달러 베팅, 헤지 없음).\n- **신중(bear)**: BOJ(6/16)+워시 매파 점도표(6/18) **동시 진행 = 엔캐리 청산 채널**. 2024.8 재현 시 코스피 −8.8%면 **8,124→약 7,410 = 안전핀 7,500 하회** → 전면 동결로 묶인 채 V자 반등 초입을 폰 밖 시간에 놓치는 이중 불리. 외인 순매도 재전환이 강세 논지 첫 균열점.\n\n---\n\n## 6. 강세 vs 신중 디베이트\n\n**🟢 강세(Bull)**: 외인이 25거래일 만에 순매수로 전환하며 반도체 투톱(SK하이닉스·삼성)을 직접 쓸어담았다 — 코스피 메인 엔진이 다시 켜졌고 HBM4 슈퍼사이클은 젠슨황 방한·Rubin 풀생산으로 실수요가 재확인됐다. 컨센서스도 NVDA(+45.7%)·META(+45.9%)·MSFT(+43.7%)·AVGO(+36.6%) 등 핵심 보유주에 30~46% 상방을 가리키고, 유가 8주 최저는 CPI 경로를 눌러 연준 매파 톤을 상쇄한다. FOMC 동결은 거의 확실(98%)하고, 6/18 대미투자법은 원전·조선·로봇에 정책 모멘텀을 얹는다. 즉 **수급·테마·밸류·정책이 동시에 강세 쪽**이다.\n\n**🔴 신중(Bear)**: 외인 전환은 아직 **단 1일** — 위험회피 국면에서 가장 먼저 되감기는 자금이다. 진짜 꼬리리스크는 점도표가 아니라 **BOJ 1.0%(+연말 1.25% 가이던스)와 워시 매파 점도표가 6/16~18 겹치며 만드는 엔캐리 청산**이다. 2024.8처럼 −8.8% 충격이면 코스피는 안전핀(7,500)을 깨고, 내 포트는 메모리·AI베타 4중첩 + 무헤지 환노출로 동시 하락에 구조적으로 가장 취약하다. 게다가 코스피는 이미 +4.63%로 호재를 선반영했고, ORCL −11.9%가 보여준 'capex 인플레+수익화 검증' 피로가 빅테크 전반에 잠복한다. 6/18 1호 프로젝트는 '당월 발표 어렵다'는 신중론까지 나왔다.\n\n**⚖️ PM 저울질**: 방향은 강세(코어 홀딩 유지)지만 **이번 주는 진입보다 방어의 주간**이다. 강세 재료는 대부분 6/12에 이미 가격에 반영됐고, 6/16~18 이벤트 클러스터는 비대칭적으로 하방 변동성이 크다. → **신규 진입은 동시휴장 구간(6/18~20) 보류, 현금은 엔캐리 청산 과매도를 노린 드라이파우더로 대기.**\n\n---\n\n## 7. PM 종합 (최종)\n\n**오늘의 한 줄 결론: 강세 추세는 살아있되 6/16~18 BOJ·FOMC·네마녀 클러스터가 비대칭 하방 리스크 — \"코어 홀딩 + 신규진입 보류 + 안전핀/현금 대기\"로 방어하며 통과한다. 액션은 6/15 이란 헤드라인과 6/18 점도표 확인 후.**\n\n### 보유 16종목 (6/12 종가 · 원가 대비 · 목표=컨센평균)\n| 종목 | 현재가 | 수익률 | 목표가(컨센) | 매수존/액션 | ⭐ | 코멘트 |\n|---|---|---|---|---|---|---|\n| 삼성전자 | 322,500 | **+22.6%** | — (국내) | 1차존 295~305k | ★★★★★ | HBM4 인증·외인 매수 2위, 코어 |\n| LG전자 | 225,500 | **+45.3%** | — | 홀딩 | ★★★★★ | 냉각 동맹, 손절선 폐기 유지 |\n| 두산로보틱스 | 110,400 | +10.4% | — | 홀딩 | ★★★☆☆ | 매출 급증·적자 지속, 테마 기대 |\n| 현대차 | 607,000 | −3.7% | — | 홀딩 | ★★★★☆ | 보스턴다이내믹스 로봇 재평가 |\n| NAVER | 247,000 | −1.4% | ~302,000 | 1차존 225~235k | ★★★☆☆ | AI팩토리 호재 but 정리 후보 상시 |\n| NVDA | $205.19 | +2.9% | $298.93 **+45.7%** | 3차 후보 | ★★★★★ | Rubin 2배, strong_buy |\n| META | $566.98 | −10.6% | $827.32 **+45.9%** | **3차 1순위** | ★★★★★ | 괴리 최대+구독 수익화 |\n| VOO | $681.95 | +5.7% | — | 코어 적립 | ★★★★☆ | S&P 인덱스 코어 |\n| MSFT | $390.74 | −4.7% | $561.39 **+43.7%** | 홀딩 | ★★★★☆ | Azure +40%, capex $190B 우려 |\n| AAPL | $291.13 | +13.2% | $312.72 +7.4% | 홀딩 | ★★★★☆ | Siri=Gemini 구동, 중국 리스크 |\n| GOOGL | $359.68 | −7.2% | $432.83 +20.3% | 홀딩 | ★★★★☆ | Cloud +63%, 규제 노이즈 |\n| TSLA | $406.43 | −3.8% | $420.55 +3.5% | 홀딩 | ★★★☆☆ | Hold 컨센, Optimus 촉매 |\n| ORCL | $184.13 | **−20.7%** | $255.38 +38.7% | 관망 | ★★★☆☆ | −11.9% 급락, OpenAI 집중 리스크 |\n| ANET | $163.24 | +0.7% | $189.13 +15.9% | 홀딩 | ★★★★☆ | AI fabric $3.5B 상향 |\n| MU | $981.61 | **+31.1%** | $828.73 −15.6% | **6/24 실적 D-10** | ★★★★☆ | 현재가>목표=단기 부담, 실적 ±20% |\n| AVGO | $382.07 | −9.3% | $522.06 +36.6% | 3차 후보 | ★★★★★ | AI매출 +200%+, strong_buy |\n\n> 합계: **총자산 8,353,877원** · 주식 평가손익 **+190,491원**(환차익 미반영) · 환차익 반영 추정 **≈+428,179원**(약달러 +23.8만) · 현금 624,771원.\n> ⚠️ MU 목표주가 −15.6%(현재가가 컨센 상회) = 단기 밸류 부담, 6/24 실적이 분수령. ORCL은 평가손 −20.7% + 단일고객 집중 리스크로 비중확대 보류.\n\n### 워치리스트 (활성)\n| 종목 | 현재가 | 목표/메모 | 판단 |\n|---|---|---|---|\n| 두산에너빌리티 | 93,100 | 14.3조 수주, KUIC 1순위 | **10만 회복 or 9만초 눌림 분할**, AI전력 발전단 대표 |\n| GE Vernova | $940.66 | $1,216(+29%) | AI전력 순수도 1위, 위성 포지션 |\n| SK이노베이션 | 106,100 | SMR 장기옵션 | 관찰 유지·후순위, PBR 1배 하회 눌림만 |\n| SK하이닉스 | 2,150,000 | 미 ADR 8월(6/22주 승인?) | 정식상장 대기, 추격 금지 |\n| 원익IPS | 240810.KQ | 상한가 직후 | **추격금지·매수존 무효**(Yahoo값 미확인) |\n| 한화에어로/조선바스켓 | — | 대미투자·美MRO 독식 | 6/18 후 소화 관찰 |\n| 삼성전기 | 1,714,000 | PER 180배 | 눌림 관찰, 6/12 −5%(역행) |\n| 테스 / STM / TMUS / SPCX | — | 후순위/관망 | SPCX 옵션 6/16·나스닥100 편입 추적 |\n\n### 제안 액션\n- **전 종목 홀딩(코어 유지)**, **신규 진입 6/18~20 전면 보류**(네마녀+준틴스 동시휴장 룰). 패닉 매도 금지(매크로 이벤트성 변동성).\n- **이란 MOU(6/15 개장 전)**: 갭업 시 방산·조선 차익실현 압력 인지, **추격 금지**. 갭다운 시 안전핀(7,500)까지 거리만 모니터.\n- **현금 624,771원 = 드라이파우더**: 엔캐리 청산 과매도(공포)에서 분할 매수가 오히려 기회(\"공포에 사라\"), 단 소화 후 진입.\n\n### 현금 배분 플랜 (3분할, 잔액 624,771원 전부 미집행)\n- **1차 ~12.5만**: NAVER 225~235k 또는 삼성 295~305k 눌림 (현재 +5%대 위, 미도달).\n- **2차 ~20만**: 이란 결렬 + 코스피 8,000 하회 동시 (8,000까지 +1.5%).\n- **3차 ~22.5만**: FOMC 6/18 확인 후. **단 실행 제약: 225k로 미국 1주 부족 + 분수주 예약불가 + 03:00 폰 밖 → 비둘기여도 즉시 불가, 6/20 집행** 또는 국내 정수주(두산E 2주·삼성 시간외) 전환. **베이킹 필수**.\n\n### 지켜볼 것 (2주 캘린더)\n| 일정(KST) | 내용 | 폰가용 |\n|---|---|---|\n| 6/15(월) | 이란 MOU 서명 헤드라인 → 갭 / SPCX 2일차 | ○ |\n| 6/16(화) | **BOJ 1.0% 인상**(엔캐리) + FOMC 1일차 + SPCX 옵션 개시 | △ 발표시각 변동 |\n| **6/18(목) 03:00** | **FOMC+점도표+워시 회견** → 3차 판단 / 대미투자법 시행 / 네마녀 / MU 옵션 | ✗ 야간 |\n| 6/19(금) | 美 준틴스 휴장 / 워치 유예종목 자동 제외 | — |\n| 6/22 주간 | SK하이닉스 미 ADR SEC 승인 가능성 | — |\n| 6/24(수) | **MU 실적** (슈퍼사이클 시험대) | ✗ 야간(미장) |\n| 7/16(목) | 한국은행 금통위 | ○ |\n\n---\n\n## 8. 오늘의 이슈 선택지\n번호로 답하면 그 항목만 다음에 심층:\n1. **6/18 FOMC 시나리오별 3차 트랜치 실행 매뉴얼** (비둘기/매파/중립 × 미국1주 격상 vs 국내전환, 6/20 집행 베이킹문 포함)\n2. **엔캐리 청산 스트레스 테스트 업데이트** (BOJ 6/16 가이던스별 내 포트 −% 시뮬 + 안전핀 7,500 하회 대응 플로우)\n3. **MU 6/24 실적 프리뷰** (컨센 EPS $19.72·±20% 변동, \"슈퍼사이클 실재 vs 정점\" 체크포인트 + 삼성·SK하이닉스 전이)\n4. **두산에너빌리티 딥다이브** (고점比 −25~33% 조정 + KUIC 1호 후보 + 10만 트리거 진입 시나리오)\n\n---\n\n## STATE SNAPSHOT\n```\n[STATE SNAPSHOT v13 2026-06-14]\n현금: 624,771원 (트랜치 1차/2차/3차 전부 미집행)\n보유변동: 없음 (16종목 유지)\n시세기준: 6/12 종가 (주말 휴장) · 코스피 8,123.62 · USD/KRW 1,517.89\n워치리스트(활성): 두산에너빌리티·GEV·SK이노·SK하이닉스·원익IPS·테스·삼성전기·한화에어로·조선바스켓·TMUS·STM·SPCX\n대기 트리거:\n  ① 6/15 이란 MOU 서명 → 월요일 갭 방향\n  ② 6/16 BOJ 1.0% 인상 → 엔캐리 청산 모니터(안전핀 7,500)\n  ③ 6/18 03:00 FOMC+점도표 → 3차 판단(비둘기=6/20 집행, 분수주 예약불가 베이킹 필요)\n  ④ 6/24 MU 실적 → 메모리 슈퍼사이클 시험대\n영구교정(신규):\n  - 두산에너빌리티 52주 고점 139,200 / 현 93,100 = 고점比 −25~33% (보도 '신고가 123,900'은 현재가 아님, 정합 해소)\n  - 대미투자법 6/18 시행이나 '1호 프로젝트 당월 발표 어렵다'(산업장관) — 갭다운 리스크\n  - 로봇밀도 IFR: 한국 1,220대 1위 검증 / 2위 싱가포르 770·3위 중국·독일 429 (경제사냥꾼 순위 정정)\n  - BOJ 인상 확률: 경제사냥꾼 \"94%\"는 과장, 실제 설문 72~88%\n신규구조: 8데스크 체제 첫 보고서(국장·미장·섹터3·매크로·리서치·리스크), 전 데스크 opus 4.8\n다음 버전: v14\n```\n\n*투자 자문 아님. 모든 레벨(목표가·매수존·별점)은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v12_addendum_2026-06-14",
      "file": "docs/reports/report_v12_addendum_2026-06-14.md",
      "title": "v12 부록 · 2026-06-14 — 이슈 ①~④ 상세 분석",
      "date": "2026-06-14",
      "version": 12,
      "kind": "보고서",
      "preview": "→ 3차 225k로는 어떤 재매수 후보도 1주 정수주가 안 된다. 두 갈래만 남음:",
      "content": "# v12 부록 · 2026-06-14 — 이슈 ①~④ 상세 분석\n\n> v12 본보고서 §5 선택지 4건 전부 상세화. **투자 자문 아님 — 최종 결정은 정훈.** 수치는 6/12 종가·6월 보도 기준 스냅샷.\n\n---\n\n## ① 6/18 점도표 시나리오별 3차 트랜치 실행 매뉴얼\n\n**핵심 제약 재확인 (룰 6·7)**: 미장 개장 22:30은 폰 가용(17:30~20:50) **밖** → **정수주 지정가 예약**(20:50 전 설정 → 22:30 자동집행)만 무인 실행 가능. **분수주=시장가 전용이라 예약 불가.** 게다가 폰 가용 시간(17:30~20:50 KST = 美 04:30~07:50 ET)엔 **미국 정규장이 닫혀 있어** 분수주 시장가 매수 자체가 불가. → **재매수는 사실상 '정수주 1주 지정가 예약'만 길.**\n\n**돈 계산 (FX 1,518 기준, 3차 트랜치 225,000원)**:\n\n| 후보 | 현재가 | 1주 ≈ 원화 | 3차(225k)로 1주? |\n|---|---|---|---|\n| NVDA | $205.19 | ~311,500원 | ❌ 부족(86k 격상 필요) |\n| AVGO | $382.07 | ~580,000원 | ❌ |\n| META | $566.98 | ~860,600원 | ❌ |\n| ORCL | $184.13 | ~279,500원 | ❌(소폭 격상) |\n| ANET | $163.24 | ~247,800원 | ❌(소폭 격상) |\n\n→ **3차 225k로는 어떤 재매수 후보도 1주 정수주가 안 된다.** 두 갈래만 남음:\n\n**시나리오 A — 비둘기/중립 점도표 (동결+2026 인하 유지/추가)**: 성장주 재진입 GO.\n- **A-1 (미국 고수)**: **트랜치 격상** — 3차 225k + 현금 버퍼 ~86k = **NVDA 1주(~311k) 지정가 예약**. 목(6/18) 17:30~20:50 사이 지정가(예: $204~206) 걸어 22:30 집행. NVDA는 목표 괴리 +45.7%로 재매수 1순위 논리 가장 강함. (격상분 86k는 2차 트랜치에서 차용, 2차는 '이란 결렬+코스피 8,000 하회' 조건이라 당장 안 쓰임.)\n- **A-2 (국내 전환, 폰 시간 내 안전)**: 미장 예약이 부담스러우면 **정규장에서 거래되는 국내 정수주**로 전환. 225k로 가능: **두산에너빌리티 2주(~186k)** 또는 **SK이노베이션 2주(~212k)** — 둘 다 AI 전력난 테마(이슈③ 연결), 폰 가용 17:30~18:00 시간외단일가로 체결 가능.\n- **권장**: 미국 성장주 괴리(META +45.9%·NVDA +45.7%)가 더 크므로 **A-1(NVDA 1주 격상)**을 1순위, 예약 부담 시 A-2.\n\n**시나리오 B — 매파 점도표 (2026 인하 0회·워시 매파 회견)**: 재진입 보류.\n- **현금 전면 동결.** 성장주 차익실현 매물 출회 대비. 신규 진입 0.\n- **룰 7 동시휴장 구간(6/18 네마녀 + 6/19 준틴스 휴장) 신규진입 보류** 자동 적용 — 유동성 공백·변동성 방어.\n- 단 **코스피 7,500 안전핀**은 그대로(현재 8,124, -7.7% 버퍼). 7,500 하회 시 잔여 트랜치 전면 동결.\n\n**시나리오 C — 동결+점도표 중립이나 회견 톤 매파**: A와 B 사이 → **절반만**(NVDA 대신 국내 1주 또는 관망 1일 더). 회견(03:30~)은 폰 밖이므로 **당일 밤 트리거 금지**, 다음날 아침 소화 후 판단.\n\n> **베이킹할 예약문(목 20:50 전 세팅 예시, 비둘기 시)**: \"NVDA 지정가 $205 1주, 유효 당일\" → 22:30 자동집행. 체결 안 되면 자동 소멸(추격 안 함).\n\n---\n\n## ② SK이노베이션 딥다이브 — 워치 정식 편입?\n\n**현재가 106,100원 · 시총 ~19.7조(코스피 47위권) · PBR ~0.98배(장부가 부근).**\n\n| 항목 | 내용 | 분류 |\n|---|---|---|\n| 목표주가 | 평균 ~156,000원이나 **의견 양극화 극심**: IBK 200,000·iM 190,000(매수) ↔ 메리츠 125,000 ↔ **LS 97,000(매도)** | [검증] |\n| 1Q 실적 | 연결 영업익 **2.16조 흑자전환**(정유 SK에너지 1.28조 견인, 정제마진 개선) | [검증] |\n| SK온(배터리) | 5년 연속 적자, 1Q 영업손실 **3,492억**(적자 축소), 2026 연간 ~1.6조 손실 전망. **흑전 시점 2026 vs 2027 견해 대립** | [검증/미확인] |\n| SMR 테마 | 테라파워 지분 일부를 1월 **한수원에 ~600억(4천만달러) 양도**, 3사 SMR 공급망 협력. 테라파워 상업 SMR **완공 2030** | [검증] |\n| 메타 원전 | 메타-테라파워 참여 보도됨, **단 SK이노 실적 직접 기여 경로·시점 미확인** | [미확인] |\n\n**PM 판단**:\n- **강세 논거**: PBR 0.98로 자산가치 하단, 정유 턴어라운드 실적 가시화, SMR은 '공짜 옵션' 성격(주가에 거의 미반영).\n- **신중 논거**: SMR 실적 반영은 **2030+ 장기 옵션** — 경제사냥꾼 쇼츠의 '6년 뒤 AI 전력난 지배' 프레임 그대로(=단기 모멘텀 아님). SK온 적자가 매년 1조+ 갉아먹고 흑전 시점 불확실. 목표가 97k(매도)~200k(매수)로 **컨센서스 신뢰도 낮음**.\n- **결론**: **워치 '관찰 후보'로 유지(편입 OK), 단 추격 금지.** 정유 사이클주 + SMR 장기옵션 + SK온 리스크의 혼합이라, **두산에너빌리티(순수 원전 수혜)보다 후순위.** 진입한다면 PBR 1배 하회(=10만 초반) 눌림에서 소량, AI 전력 바스켓의 위성 포지션으로만. **단독 큰 비중 부적합.**\n\n---\n\n## ③ AI 전력난 테마 지도 — 원전·전력 밸류체인\n\n**테마 논지**: AI 데이터센터 폭증 → 전력 수요 구조적 급증 → ① 발전(원전·SMR·가스터빈) ② 송배전·전력기기 ③ 냉각. 정훈 포트에 이미 LG전자(냉각)·현대차(피지컬AI) 일부 노출, 여기에 발전단을 보강하는 그림.\n\n| 종목 | 밸류체인 위치 | 현재가 | 컨센/메모 | 정훈 포지션 |\n|---|---|---|---|---|\n| **두산에너빌리티** | 원전 주기기·SMR·가스터빈 | 93,100 | 목표 평균 **~152,000**(매수 다수), 2026 수주 가이던스 13.4조(원전 4.9조). 대미투자법 6/18 직접 수혜 | 워치 **1순위** |\n| **SK이노베이션** | SMR 지분(테라파워) | 106,100 | 목표 분산 97k~200k, SMR은 2030 장기옵션 | 워치 후보(후순위) |\n| **GE Vernova** | 가스터빈·전력기기(美) | $940.66 | 목표 $1,211(+28.8%), AI 전력 대표주 | 워치 |\n| **LG전자** | 액냉 CDU(데이터센터 냉각) | 225,500 | 보유 ★★★★★, NVIDIA DSX 인증 | **보유** |\n| (참고) 삼성전자 | HBM(AI 메모리) | 322,500 | 보유, 전력보다 연산단 | 보유 |\n\n**PM 종합**:\n- **순수도·실적 가시성 순위**: 두산에너빌리티 > GEV > SK이노(옵션성). **발전단 보강은 두산에너빌리티가 정석.**\n- **촉매 캘린더**: 6/18 대미투자법 시행(한미전략투자공사 출범) = 원전 테마 모멘텀. 단 두산에너빌리티는 이미 **10만 돌파 후 조정**(일부 보도 신고가 ~123,900 → 현 93,100, ⚠️**고점·현재가 정합성 재검증 필요**). 추격금지 룰상 **눌림(9만 초반 유지/10만 재돌파 확인)에서 분할**이 맞음.\n- **분산 주의**: 테마가 겹쳐 한쪽으로 쏠리면 AI-전력 단일 베팅이 과해짐. **발전단은 두산에너빌리티 1종으로 대표**시키고 SK이노/GEV는 위성으로만.\n\n---\n\n## ④ BOJ 1.0% 인상 → 엔캐리 청산 시 내 포트 스트레스 테스트\n\n**셋업**: BOJ 6/16 0.75→1.0% 인상 컨센서스 94%(검증). 1.0%는 **대체로 선반영** → 인상 자체보다 **'추가 인상 가이던스(연말 1.25%)의 매파 강도'**가 엔 방향·캐리청산을 좌우. 워시 첫 FOMC(6/18 매파 점도표 리스크)와 **6/16~18 동시 진행** = 미일 금리차 교차충격 구간.\n\n**내 포트의 취약점 (고AI베타·반도체 쏠림)**:\n- 미국: NVDA(최대비중)·MU·AVGO·ANET = 반도체/AI 인프라 고베타. 엔캐리 청산 = 글로벌 위험회피 + 엔펀딩 되감기 → **고밸류 성장주가 가장 먼저·크게 매도**.\n- 국내: 삼성전자(반도체)·두산로보틱스(고베타). 코스피는 엔캐리 청산 시 아시아 동반 충격 취약.\n- **즉, 내 포트는 엔캐리 청산에 구조적으로 민감한 구성.**\n\n**과거 사례 벤치마크**: 2024.8 BOJ 인상+캐리청산 → 닛케이 -12%·코스피 -8.8%(하루), 반도체 직격 → **단 수일~수주 내 대부분 회복**(V자). 장기 펀더멘털 훼손 아닌 **유동성/포지션 충격**이었음.\n\n**대응 (룰 기반, 패닉 금지)**:\n1. **손절 안 함** — 투자철학상 매크로 이벤트성 변동성엔 코어 홀딩 유지(특히 LG전자·삼성전자·NVDA).\n2. **안전핀 = 코스피 7,500 하회 시 잔여 트랜치 전면 동결**(현재 8,124, -7.7% 버퍼). 캐리청산이 7,500까지 밀면 신규매수 STOP·물타기 금지.\n3. **2차 트랜치(~20만)는 '이란 결렬 + 코스피 8,000 하회' 조건** — BOJ발 단독 하락은 트리거 아님. 8,000 하회해도 이란 결렬 동반 아니면 대기.\n4. **현금 624,771원 = 드라이파우더.** 캐리청산 후 과매도(공포)에서 분할 매수가 오히려 기회(\"공포에 사라\" 역발상) — 단 **추격금지·소화 후 진입**.\n5. **꼬리리스크 신호**: 엔/달러 급격 강세 + 닛케이 급락 동시 발생 시 = 청산 진행 신호. 폰 밖 시간(밤)이면 당일 대응 말고 다음날 아침 소화 후 판단.\n\n**결론**: 충격 발생 시 **단기 -8~12% 평가손 출렁임 각오하되 대응은 \"홀딩 + 안전핀 + 현금으로 과매도 분할\"**. 1.0%가 선반영이라 **깜짝 매파 가이던스만 없으면 충격은 제한적·일시적**일 가능성이 높음.\n\n---\n\n*투자 자문 아님. 모든 레벨은 분석 참고이며 최종 결정은 정훈.*\n"
    },
    {
      "id": "report_v12_2026-06-14",
      "file": "docs/reports/report_v12_2026-06-14.md",
      "title": "정훈 PORTFOLIO DESK · v12 · 2026-06-14 (일)",
      "date": "2026-06-14",
      "version": 12,
      "kind": "보고서",
      "preview": "1. 🌍 이란 '이슬라마바드 MOU' — 본문 타결+카메네이 승인까지 통과, 단 서명 타이밍 막판 신경전 [검증/미확인 혼재]: 14개항 합의문 본문은 타결, 이란 외무부 대변인은 \"6/14 서명은 아니다, 다만 수일 내 가능성은 배제 안 함\"으로 명",
      "content": "# 정훈 PORTFOLIO DESK · v12 · 2026-06-14 (일)\n\n> 작성 기준: 일요일 아침(KST) — 한국·미국 **주말 휴장**, 시세는 6/12(금) 종가 고정(Yahoo `market_data.py`). 직전 v11(6/13 토 저녁) 이후 **주말 증분(이란 MOU·매크로 셋업·신규 영상)** 중심 업데이트.\n> ⚠️ **이번 세션 토스 키 미제공** → 손익은 **원가기준(portfolio.json×Yahoo)**으로 보고. **토스 실손익(환차익 포함)이 정본** — v11 토스값 carry-forward(아래 ※). **투자 자문 아님 — 최종 결정은 정훈.**\n\n## 변경점 (v11 대비)\n\n1. **🌍 이란 '이슬라마바드 MOU' — 본문 타결+카메네이 승인까지 통과, 단 서명 타이밍 막판 신경전 [검증/미확인 혼재]**: 14개항 합의문 본문은 타결, 이란 외무부 대변인은 **\"6/14 서명은 아니다, 다만 수일 내 가능성은 배제 안 함\"**으로 명시 부인(디지털·원격 전자서명 고수). 트럼프·파키스탄측은 \"임박\" 주장. → **어느 출처도 '서명 완료' 확정보도 없음(미확인).** 합의 자체는 거의 됐으므로 큰 악재성 갭다운 가능성은 낮으나 **월요일 갭은 개장 직전 헤드라인 의존도 매우 높음.**\n2. **🔑 매크로 빅위크 셋업 정밀화**: ①**BOJ 0.75→1.0% 인상 94% = [검증 완료]**(v11 [미확인]→확정, Reuters 6/2~8 70명 중 66명, 1995년 이래 최고). ②**PPI 5월 +6.5% 신규 확인**(2022.11 이래 최고, MoM +1.1% 예상상회) → CPI 4.2%에 더해 **매파 점도표 리스크 보강.** ③**FOMC 동결 ~97%**, 워시 첫 점도표에서 **2026 인하 횟수 하향(중앙값 0회 가능성)** 리스크.\n3. **🛢️ 유가 급락 [검증]**: 브렌트 6/5 ~$97 → **6/12 $84~86(8주 최저, -4%+)**, 미·이란 휴전 임박 반영. CPI 에너지 경로엔 완화 요인(매파 압력 일부 상쇄).\n4. **🇰🇷 젠슨황 방한 후속 [검증]**: 마지막날 LG·현대차·NAVER 릴레이 방문, **정의선 '새만금 AI밸리' 투자 제안에 \"기꺼이 동참\" 화답**, SK-엔비디아 차세대 AI메모리·DC 협력. 단 **SPCX(스페이스X) 6/12 상장發 머스크 자금쏠림 → SK하이닉스 일시 눌림**(국내 반도체 단기 자금이탈 요인).\n5. **🎬 경제사냥꾼 신규(6/13 쇼츠) [검증 다수]**: **SK이노베이션 = AI 전력난 SMR 테마** — 빌게이츠 테라파워 2대 주주(검증), 메타 나트륨원전 최대 8기 입도선매·2030 완공(검증), 1Q 영업익 2.16조 흑전·SK온 적자 3,492억(검증). **워치 후보 신규 제안**(§4). 단 '장중 18% 급등' 등 일부 수치는 미확인.\n\n## 1. 시장 데스크 (6/12 마감, 주말 휴장)\n\n- **국내(6/12 종가 고정)**: 코스피 **8,123.62(+4.63%)**·코스닥 1,029(+3.22%). 외인 반도체 투톱 ~2조 순매수가 견인. 주말 증분 빅뉴스는 **이란 MOU 헤드라인**이 유일한 갭 변수. 시간외 시세 변동 없음(휴장).\n- **미국(6/12)**: S&P500 7,431(+0.5%)·나스닥 25,889(+0.31%)·필반 13,371(+1.52%). SPCX 상장 첫날 +19.2% $160.95(시총 ~$2.27조, TSMC 추월·글로벌 7위) — 머스크 자금쏠림이 반도체 단기 역풍.\n- **다음주 관전**: ①이란 MOU 서명 실현 = 월요일 갭 방향타 ②반도체 쏠림 지속 vs 조선·방산·전력기기 로테이션 확산 ③SPCX 상장 후 글로벌 자금 국내 반도체 환류 여부.\n\n## 2. 매크로 데스크 — 다음주 = 정책 빅위크\n\n- **FOMC (6/16~17 → 6/18 03:00 KST 결과+점도표+워시 첫 회견)**: 동결 **~97%**(타깃 3.50~3.75%). 핵심은 **워시 의장 첫 점도표** — CPI 4.2%·PPI 6.5% 반영 시 **2026 인하 횟수 하향(중앙값 0회 가능성)** = 매파 비대칭 리스크. 회견 톤이 변동성 핵심 트리거.\n- **BOJ (6/15~16, 결과 6/16)**: **0.75→1.0% 인상 컨센서스(설문 94%·스왑 80~96%) [검증]**, 연내 2회로 연말 1.25% 전망. 1.0%는 대체로 선반영이나 **워시 매파 점도표와 동시 진행(6/16~18) → 미일 금리차·엔 방향 교차충격 구간**, 깜짝 매파 가이던스 시 엔캐리 청산 꼬리리스크.\n- **지표·유가**: CPI 5월 **+4.2%**(코어 2.9%)·PPI 5월 **+6.5%**(MoM +1.1%) 둘 다 매파. 단 **유가 $84~86 급락**이 에너지 경로 완화. **향후 2주 신규 CPI/PPI 없음(7월 중순)** → 다음주는 순수 정책·유가·이란 헤드라인 장세.\n- **한국은행**: 다음주 회의 없음(기준 2.50%, 다음 7/16). **한은은 점도표 미발표(연준 전용 — 혼동 금지).**\n\n## 3. 리서치 피드 — 경제사냥꾼 (🎬 6/13~14 필터)\n\n> **6/14(일) 신규 업로드 미발견.** 6/13 \"다음주 투자포인트\"·삼성전기 7배·젠슨황 집착 3건은 **v11 기보고**. 아래는 v11 미수록 신규 쇼츠 2건.\n\n**① \"월가가 말하는 6년 뒤 'AI 전력난' 지배 한국 종목 = SK이노베이션\" (쇼츠, 6/13)** — 자막 전문 확보:\n- SK이노가 빌게이츠 **테라파워(美 첫 상업용 SMR) 2대 주주** → **[검증]** (2022년 SK㈜·SK이노 2.5억달러 투자, \"빌게이츠 다음 2대 투자자\").\n- 메타 나트륨원전 **최대 8기(2.8GW) 입도선매·2030 완공·한수원 지분 인수** → **[검증]**.\n- 1Q 영업익 **2.16조 흑전**, SK온 적자 **3,492억** → **[검증]**.\n- \"3월 SMR 승인 직후 장중 18% 급등\" → **[미확인]** (NRC 승인은 사실, 18% 수치 교차검증 실패 — 자동자막 단독신뢰 불가).\n- PM: **AI 전력난 + 원전 밸류체인 신규 앵글.** 보유 두산에너빌리티(원전)·LG전자(전력)와 테마 연결. 워치 후보 §4.\n\n**② \"'스페이스X' 대신 투자자들이 올라탄 종목\" (쇼츠, 6/13)** → **[미확인]** (자막 없음 — web→ios 폴백 전부 무자막. 제목상 SPCX 대체 수혜주 추정이나 지목종목·논거 미확보, 재구성 불가).\n\n> **한계**: 데이터센터 IP 봇차단으로 일반영상 자막 미확보(제목만), 쇼츠 ①만 자막 확보. 자동자막 수치는 교차검증 필수.\n\n## 4. PM 종합 (최종)\n\n**오늘의 한 줄**: 주말 사이 그림은 **\"매크로 매파 재료(PPI 6.5%·BOJ 인상·워시 점도표) ↔ 완화 재료(유가 급락·이란 휴전 임박)\"의 팽팽한 줄다리기.** 단일 분기점은 변함없이 **6/18 03:00 점도표.** **주말 현금 동결 유지, 월요일은 이란 헤드라인만 확인하고 관망 — 신규 진입 보류.**\n\n### 보유 16종목 (현재가=6/12종가 / 수익률=원가기준 pnl.py / 목표=美 consensus.py)\n\n| 국내 | 현재가 | 수익률(원가) | ⭐ | 코멘트 |\n|---|---|---|---|---|\n| LG전자 | 225,500 | **+45.30%** | ★★★★★ | 손절선 없음, 액냉 CDU·전력 |\n| 삼성전자 | 322,500 | +22.62% | ★★★★★ | 외인 순매수 1순위, 젠슨황 반도체 모멘텀 |\n| 두산로보틱스 | 110,400 | +10.40% | ★★★☆☆ | 피지컬 AI 순수 플레이 |\n| NAVER | 247,000 | -1.40% | ★★★★☆ | 225~235k 눌림 시 1차 트랜치 |\n| 현대차 | 607,000 | -3.65% | ★★★☆☆ | 새만금 AI밸리·로봇(젠슨황 화답), 본업은 환율 역풍 |\n\n| 미국 | 현재가 | 수익률 | 목표(평균) | 괴리 | ⭐ | 코멘트 |\n|---|---|---|---|---|---|---|\n| MU | $981.61 | **+31.06%** | $828.73 | -15.6% | ★★★★★ | **6/24 실적 D-10**, 목표 하회=코어홀딩 |\n| AAPL | $291.13 | +13.22% | $312.72 | +7.4% | ★★★★☆ | buy(43) 홀딩 |\n| VOO | $681.95 | +5.66% | (ETF) | — | ★★★★★ | 적립 |\n| NVDA | $205.19 | +2.85% | $298.93 | **+45.7%🟢** | ★★★★★ | 젠슨황 방한 모멘텀, 상방 큼 |\n| ANET | $163.24 | +0.72% | $189.13 | +15.9% | ★★★★☆ | 흑자전환 |\n| TSLA | $406.43 | -3.81% | $420.55 | +3.5% | ★★★☆☆ | SPCX 동반 |\n| MSFT | $390.74 | -4.74% | $561.39 | **+43.7%🟢** | ★★★★☆ | 홀딩 |\n| GOOGL | $359.68 | -7.23% | $432.83 | +20.3% | ★★★★☆ | TPU |\n| AVGO | $382.07 | -9.26% | $522.06 | **+36.6%🟢** | ★★★★☆ | FOMC 후 재매수 후보 |\n| META | $566.98 | -10.57% | $827.32 | **+45.9%🟢** | ★★★★☆ | 재매수 1순위 후보 |\n| ORCL | $184.13 | -20.67% | $255.38 | **+38.7%🟢** | ★★★☆☆ | 바닥 다지기 |\n\n> **손익 주의**: 원가기준 주식 평가손익 **+190,491원**(총자산 **8,353,877원**, 현금 624,771 포함). ※ **v11 토스 실손익은 +438,186원(+5.9%)** — 차이 ~25만원은 **미국 종목 매수시점 대비 원화 약세(환차익)**로, 원가기준 계산엔 안 잡힘. **토스 실데이터가 정본** — 정확한 실손익은 다음 세션에 토스 키/스크린샷 필요. 🟢=목표 +30%↑ 괴리.\n\n### 워치리스트 + 신규 후보\n\n| 종목 | 현재가 | 목표/괴리 | 상태 |\n|---|---|---|---|\n| **SK이노베이션 🆕** | — | (국내·미커버) | **신규 후보** — 테라파워 2대주주+메타 SMR, AI 전력난 테마(검증). 단 SK온 적자 리스크, 정유 변동성 |\n| 삼성전기 | 1,714,000 | (국내) | AI 소부장 대장주, 목표 230~300만 상향. PER 180배 과열 — 추격금지·눌림 관찰 |\n| 두산에너빌리티 | 93,100 | (국내) | **대미투자법 원전 수혜**, '십만빌리티' D-6.9%. SK이노 SMR 테마와 동반 |\n| TMUS | 189.10 | +37.9%🟢 | 스타링크 D2C |\n| GEV | 940.66 | +28.8% | AI 전력 |\n| SPCX | 160.95 | +1.9% (buy 5) | 신규 보류 — 머스크 자금쏠림이 반도체 역풍 |\n| STM | 77.30 | -17.6% | 후순위 |\n| 한화에어로/조선바스켓 | 1,078,000 / 한화오션 112,700·삼성중공업 26,900·HD현대중공업 650,000 | (국내) | 대미투자법 조선·방산, 6/18 시행 후 소화 관찰 |\n| 원익IPS·테스 ⚠️ | 36,750 / 22,000 | — | **티커 검증 필요**(Yahoo값 보고서값과 불일치 지속) |\n\n### 제안 액션\n- **홀딩 전 종목, 현금 동결 유지.** 트리거 0건 발동(코스피 8,124 = 안전핀 7,500 대비 +8.3%, NAVER 매수존 +5.1% 위, 삼성전자 매수존 +5.7% 위).\n- **6/18 점도표 시나리오 (3차 ~22.5만, 재확인)**: ①비둘기/중립 → **META·AVGO·NVDA**(목표 +37~46% 괴리) 재매수, 목 17:30~20:50 **정수주 지정가 예약** → 22:30 집행. ②매파 점도표 → 현금 유지, 성장주 차익실현 대비. **※분수주=시장가 전용이라 예약 불가, 3차 225k로 NVDA 1주(~31만) 부족 → 트랜치 격상 or 국내 전환** 필요.\n- **신중**: PPI 6.5% + 매파 점도표 + 네마녀의날(6/18) + 6/19 美 준틴스 휴장 유동성 공백이 한 주에 겹침 → **다음주 후반 변동성 확대 가능, 동시휴장 전후 신규진입 보류 룰 적용.**\n- **강세**: 유가 급락·이란 휴전 임박·외인 반도체 순매수 지속·젠슨황發 모멘텀은 코스피 강세 논지 유지. 양방향 다 열어두고 6/18 확인 후 대응.\n\n### 지켜볼 것 (2주 캘린더)\n- 6/15(월) 이란 MOU 서명 헤드라인 확인·관망 / **6/16(화) BOJ 결과(0.75→1.0% 유력)**·FOMC 1일차 / 6/17(수) 美 소매판매 / **6/18(목) 03:00 FOMC 점도표+워시 회견 / 대미투자법 시행 / 네마녀의날 / ACN 실적** / 6/19(금) **美 준틴스 휴장**(NYSE 휴장)\n- **6/24(수) MU 실적(D-10)**. 7/16 한국은행 금통위. (보유·워치 실적은 대부분 7월 말 집중 — earnings.py 참조)\n\n## 5. 오늘의 이슈 선택지 (번호 선택 → 상세)\n① **6/18 점도표 매파/비둘기 시나리오별 3차 트랜치 실행 매뉴얼** (정수주 지정가 예약·트랜치 격상 포함)\n② **SK이노베이션 딥다이브** — 워치 정식 편입? 테라파워·메타 SMR vs SK온 적자 (`/stock-deepdive SK이노베이션`)\n③ **AI 전력난 테마 지도** — 두산에너빌리티·SK이노·GEV·LG전자 묶어 원전·전력 밸류체인 정리\n④ **BOJ 1.0% 인상 → 엔캐리 청산 시 내 포트 스트레스 테스트** (반도체·성장주 영향)\n\n## STATE SNAPSHOT\n\n```\n[STATE SNAPSHOT v12 2026-06-14]\n계좌: 토스 키 미제공 → 원가기준 손익 보고(주식 +190,491원, 총자산 8,353,877원, 현금 624,771원).\n      ※정본=토스 실손익(v11 +438,186원/+5.9%, 환차익 ~25만 포함). 다음 세션 토스 키/스크린샷 필요.\n보유변동: 없음 (홀딩 전 종목, 현금 동결)\n워치리스트(활성): SK이노베이션(신규후보·AI전력난), 삼성전기, 두산에너빌리티(대미투자법 원전), TMUS, GEV, SPCX(보류), STM, 한화에어로/조선바스켓, 원익IPS·테스(⚠️티커)\n대기 트리거: 6/18 03:00 점도표→3차 집행(비둘기=META·AVGO·NVDA 재매수/매파=현금유지). 6/15 개장 전 이란 MOU 서명 헤드라인.\n신규검증: BOJ 0.75→1.0% 94%[검증완료]. PPI 5월 +6.5%(2022.11래 최고)[검증]. 유가 브렌트 $84~86 급락[검증]. SK이노 테라파워 2대주주+메타SMR[검증]. 정의선 새만금AI밸리 젠슨황 화답[검증]. 대미투자법 시행령 6/9 의결·6/18 발효·한미전략투자공사 2조원.\n미확인: 이란 MOU '서명 완료'(본문타결·카메네이승인은 검증, 서명 타이밍 미확정). SK이노 '장중18%급등'. SPCX 대체주 쇼츠(자막무).\n정정(미세): BOJ 회의는 6/15~16 2일(결과 6/16) — 직전 'BOJ 6/16'은 결과일 기준 맞음.\n다음 버전: v13\n```\n"
    },
    {
      "id": "report_v11_2026-06-13",
      "file": "docs/reports/report_v11_2026-06-13.md",
      "title": "정훈 PORTFOLIO DESK · v11 · 2026-06-13 (토)",
      "date": "2026-06-13",
      "version": 11,
      "kind": "보고서",
      "preview": "1. ✅ 실계좌 완전 동기화 (토스 스크린샷 검증): 보유 16종목·원금·현금 전부 portfolio.json과 일치. 현금 624,771원 + $1.11 확정. 내 투자 평가액 7,774,381원 (+438,186원, +5.9%), 총자산 ≈ 840",
      "content": "# 정훈 PORTFOLIO DESK · v11 · 2026-06-13 (토)\n\n> 작성 기준: 국내·미국 6/12(금) 마감. **계좌=토스 실스크린샷(정본, 19:26~19:29 KST)**, 시세=Yahoo, 손익=토스. **투자 자문 아님 — 최종 결정은 정훈.**\n> 🎬 이번 보고서는 **경제사냥꾼 영상 3건 자막 실제 추출**(ios 클라이언트로 웹 봇차단 우회 성공) 후 작성.\n\n## 변경점 (v10 대비)\n\n1. **✅ 실계좌 완전 동기화 (토스 스크린샷 검증)**: 보유 16종목·원금·현금 전부 portfolio.json과 일치. **현금 624,771원 + $1.11 확정.** 내 투자 평가액 **7,774,381원 (+438,186원, +5.9%)**, 총자산 ≈ **840만원**. 국내수익 +183,100원(11.0%).\n2. **✅ 경제사냥꾼 자막 추출 성공**: 웹 데이터센터 IP 봇차단을 **ios 플레이어 클라이언트**로 돌파 → 오늘(6/13) \"다음주 투자포인트\" 외 3건 전문 확보(스크립트에 영구 반영).\n3. **🔑 매크로 인플레 그림 충돌(v10 플래그) → 매파 리스크 쪽으로 수렴**: 경제사냥꾼도 독립적으로 **CPI 4.2%·중동 유가 자극·점도표 매파 리스크**를 지목 → v10의 \"에너지 쇼크/매파\" 해석을 2차 출처가 보강. **6/18 점도표가 다음주 최대 변수** 재확인.\n4. **신규 재료 [검증]**: **대미투자 특별법 6/18 시행**($3,500억, 원전·조선·방산 수혜 가능) — FOMC와 같은 날. **삼성전기** 증권가 목표 줄상향(iM 230만/DB 300만) — AI 소부장 로테이션 대표주, 워치 후보.\n5. **젠슨황 방한**(≠알트만): 알트만은 연기됐지만 젠슨황은 방한, SK하이닉스-엔비디아 AI DC 협력 발표 거론 → 반도체 대형주 모멘텀.\n\n## 1. 시장 데스크 (6/12 마감, 토요일 휴장)\n\n- **코스피 8,123.62 (+4.63%)** — 외인 +2.1조(25거래일만 순매수 전환)·기관 +2.4조 / 개인 -4.3조. 코스닥 1,029(+3.22%). AI 대형주→소부장 로테이션. *시간외(19시대) Toss 기준 삼성·LG·현대 소폭↑, **NAVER 242,500으로 −(알트만 연기 시간외 반영)***.\n- **미국 6/12**: S&P500 7,431(+0.5%)·나스닥 25,889(+0.31%)·필반 13,371(+1.52%). SPCX 첫날 +19.2% $160.95(공모 $135, 조달 ~$750억, 기업가치 ~$1.77조 = 사상 최대 IPO).\n\n## 2. 매크로 데스크\n\n- **환율 USD/KRW ~1,518**. 다음주 한국증시는 **국내 이벤트보다 美 점도표·환율·외국인 수급**에 좌우(경제사냥꾼도 동일 지적).\n- **FOMC 6/16~17 → 6/18 03:00 KST 결과 + 점도표(분기 1회) + 워시 첫 회견.** 동결 ~97%이나 **점도표 매파 여부가 핵심**. CPI 5월 +4.2%·중동 유가 자극으로 매파 리스크 상존.\n- **BOJ 6/16 회의 — 0.75%→1.0% 인상 전망(설문 94%, 1995년 이후 31년만)** [미확인—방향성 검증]. 엔캐리 청산 시 아시아 증시 단기 충격 가능.\n- 한국은행 회의 **다음주 없음**(기준 2.50%, 다음 7/16). 한은 점도표 미발표(연준 전용).\n\n## 3. 리서치 피드 — 경제사냥꾼 (🎬 자막 전문 추출)\n\n**① \"경제사냥꾼이 말하는 '다음 주' 진짜 투자 포인트\" (6/13, 약 16분, 자막 전문 확보)**\n6/15~19 날짜별 해부. 핵심 주장:\n- \"다음주 운명은 6/18 새벽 3시 FOMC **점도표**가 절반 이상 결정. 점도표 위로↑=성장주 부담, 아래로↓=반도체·성장주 탄력\" → **[검증]** (FOMC 6/18 03:00 KST·점도표 분기공개·워시 첫 회견 전부 일치).\n- \"5월 CPI +4.2%, 중동 유가 자극, 점도표 매파면 AI·반도체 차익실현\" → **[검증]** (CPI/PPI·유가 매크로와 일치).\n- \"BOJ 6/16 0.75→1.0% 인상 전망(94%), 엔캐리 청산 우려\" → **[미확인]** (방향성은 그럴듯, 94% 수치 미검증).\n- \"**6/18 대미투자 특별법 시행** — $3,500억(직접 $2,000억+조선 $1,500억), 한미전략투자공사 2조원, **원전 유력 거론**\" → **[검증]** (3/12 국회통과, 6/18 시행, 반도체·에너지·AI·조선·원전 — 한경·조세일보 일치).\n- \"6/18 美 선물옵션 동시만기(네마녀의날) — 6/19 美 준틴스 휴장이라 하루 앞당겨짐 + 6/19 中·홍콩·대만 단오절 휴장=유동성 공백\" → **[미확인]** (Juneteenth 6/19 휴장은 사실, 만기 앞당김·아시아 휴장 동시성은 미검증).\n- \"6/18 엑센추어(ACN) 실적=글로벌 AI 투자 가늠자\" → **[미확인]**.\n- 결론: \"초반(월화) 관망 → 중반(수목새벽) 방향결정 → 후반(금) 정리. 양쪽 다 열어두고 대응\" → 정훈의 **3차 트랜치(FOMC 후)·추격금지·안전핀** 룰과 **정확히 동일 철학**.\n\n**② 쇼츠 \"삼성전기 주가 7배 — 투자 포인트\" (6/13, 자막 확보)**\n- \"장중 219만원·한달 +150%(SK하이닉스보다 빠름)·코스피 시총 4위까지. 현재 PER **180배**=과열, 차익실현 매물. 단 증권가는 목표 상향 — **iM 230만·DB 300만**\" → **[검증]** (iM 180→230만 buy 박정하 'AI 부품 대장주', DB 160→300만 조현지 '내년 영업익 3조' — 비즈니스포스트·뉴시스 일치).\n- 논거: MLCC(AI서버 수요·단가↑), FC-BGA(매출 1.1조→2027 2.4조, 빅테크 공급처), 실리콘커패시터(1.6조 수주) → **[검증/미확인 혼재]** (사업부 방향 검증, 구체 수치는 증권사 추정).\n- PM 코멘트: **AI 소부장 로테이션 대표주.** PER 180배는 추격 부담이나 워치 편입해 눌림 관찰 가치. (워치 후보 §4).\n\n**③ 쇼츠 \"유독 한국인만 젠슨황에 집착하는 이유\" (6/13, 자막 확보)**\n- \"젠슨황 방한·이차 회동에 관련주 급등. 한국=엔비디아 AI 공급망·제조·로봇 실증거점. 단 **대만엔 1,500억달러(225조) 투자 약속하면서 한국엔 '협력'뿐**. 한국 정부는 2026 국가AI 2조800억으로 GPU 9,700장 확보 추진(차세대 포함)\" → **[검증/미확인 혼재]** (젠슨황 방한·SK하이닉스 협력 거론은 다수보도 방향 일치, 대만 $1,500억·한국 GPU 9,700장 구체수치는 미확인).\n- PM 코멘트: 보유 NVDA + 삼성전자·(워치)SK하이닉스 모멘텀. **알트만 방한 연기와 별개 인물** — 혼동 금지.\n\n(기타 오늘 쇼츠 3건: 월가 미래산업주/머스크 우주산업/환율급등 외국인 매수주 — 테마성, 요청 시 추가 분석)\n\n## 4. PM 종합 (최종)\n\n**오늘의 한 줄**: 실계좌 +5.9%(840만 자산) 확인. 다음주는 **6/18 점도표 단일 분기점** — 경제사냥꾼·매크로 데스크·내 트랜치 룰이 전부 한 곳을 가리킴. **주말 현금 동결, 6/18 새벽 결과로 3차 집행 판단.**\n\n### 보유 16종목 (토스 실손익 / 목표=美 consensus.py)\n\n| 국내 | 평단 | 수익률(토스) | ⭐ | 코멘트 |\n|---|---|---|---|---|\n| LG전자 | 155,200 | **+46.9%** | ★★★★★ | 손절선 없음, 액냉 CDU |\n| 삼성전자 | 263,000 | +23.3% | ★★★★★ | 외인 순매수 1순위, 젠슨황發 반도체 모멘텀 |\n| 두산로보틱스 | 100,000 | +10.3% | ★★★☆☆ | 소부장 로테이션 반대편 |\n| 현대차 | 630,000 | -2.3% | ★★★☆☆ | 원화 약세 역풍, 단 대미투자법 방산·조선 간접 |\n| NAVER | 250,500 | -3.1% | ★★★★☆ | **알트만 연기로 시간외 약세** — 225~235k 눌림 시 1차 |\n\n| 미국 | 평단 | 수익률 | 목표(평균) | 괴리 | ⭐ | 코멘트 |\n|---|---|---|---|---|---|---|\n| MU | $749.00 | **+31.0%** | $828.73 | -15.6% | ★★★★★ | 6/24 실적(D-11), 목표 하회 — 트림보다 코어홀딩 |\n| AAPL | $257.14 | +13.2% | $312.72 | +7.4% | ★★★★☆ | buy(43) 홀딩 |\n| VOO | $645.40 | +5.6% | (ETF) | — | ★★★★★ | 적립 |\n| NVDA | $199.51 | +2.8% | $298.93 | **+45.7%🟢** | ★★★★★ | 젠슨황 방한 모멘텀, 상방 큼 |\n| ANET | $162.07 | +0.7% | $189.13 | +15.9% | ★★★★☆ | 흑자전환 |\n| TSLA | $422.51 | -3.8% | $419.94 | +3.3% | ★★★☆☆ | SPCX 동반 |\n| MSFT | $410.20 | -4.7% | $561.39 | **+43.7%🟢** | ★★★★☆ | 홀딩 |\n| GOOGL | $387.73 | -7.2% | $432.83 | +20.3% | ★★★★☆ | TPU |\n| AVGO | $421.06 | -9.2% | $522.06 | **+36.6%🟢** | ★★★★☆ | FOMC 후 재매수 후보 |\n| META | $633.98 | -10.5% | $827.32 | **+45.9%🟢** | ★★★★☆ | 재매수 1순위 후보 |\n| ORCL | $232.12 | -20.6% | $255.95 | **+39.0%🟢** | ★★★☆☆ | 바닥 다지기 |\n\n> **총자산 ≈ 840만원** (주식 7,774,381 + 현금 624,771 + $1.11). 주식 +5.9%. 🟢=목표 +30%↑ 괴리.\n\n### 워치리스트 + 신규 후보\n\n| 종목 | 상태 |\n|---|---|\n| **삼성전기 (신규 후보)** | 🆕 AI 소부장 대장주, 증권가 목표 230~300만 상향. PER 180배 과열 — 추격금지, 눌림 관찰용 편입 검토 |\n| 두산에너빌리티 | 93,100, 원전 테마 — **대미투자법 원전 수혜** 가능, '십만빌리티' D-7% |\n| GEV / TMUS | 목표 +28.8%/+37.9%, AI 전력·스타링크 |\n| SPCX | $160.95, 매도의견(목표$139) — 신규 보류 |\n| 원익IPS·테스 ⚠️ | 티커 검증필요 |\n\n### 제안 액션\n- **홀딩 전 종목, 주말 현금 동결.** 트리거 0건(코스피 8,124 = 안전핀 7,500 대비 +8.3%, NAVER 매수존 -5.1% 위).\n- **6/18 점도표 시나리오 (3차 ~22.5만)**: ①비둘기/중립 → META·AVGO·NVDA(목표 +37~46% 괴리) 재매수, 목 17:30~20:50 지정가 예약 → 22:30 집행. ②매파 점도표 → 현금 유지, 성장주 차익실현 대비.\n- **신중**: 6/18 점도표 매파 + 네마녀의날 변동성 + 6/19 美 휴장 유동성 공백 겹침 → 다음주 후반 변동성 확대 가능.\n\n### 지켜볼 것 (다음주 캘린더)\n- 6/15(월) 관망 / 6/16(화) **BOJ**·FOMC 1일차 / 6/17(수) 美 소매판매 / **6/18(목) 03:00 FOMC 점도표+워시 / 대미투자법 시행 / 네마녀의날 / ACN 실적** / 6/19(금) **美 준틴스 휴장**\n- 6/24(수) **MU 실적(D-11)**. 7/16 한국은행 금통위.\n\n## 5. 오늘의 이슈 선택지 (번호 선택 → 상세)\n① 6/18 점도표 매파/비둘기 시나리오별 3차 트랜치 실행 매뉴얼(지정가 예약 포함)\n② **삼성전기 딥다이브** — 워치 편입? PER 180배 vs 목표 300만 (`/stock-deepdive 삼성전기`)\n③ 대미투자 특별법 수혜주 지도 — 원전(두산에너빌리티)·조선·방산\n④ 경제사냥꾼 \"다음주\" 영상 전체 요약 + 내 트랜치 룰 스트레스 테스트\n\n## STATE SNAPSHOT\n\n```\n[STATE SNAPSHOT v11 2026-06-13]\n계좌(토스 검증): 보유16+원금+현금 일치. 현금 624,771원+$1.11. 주식평가 7,774,381원(+5.9%). 총자산 ~840만.\n보유변동: 없음\n워치리스트(활성): 삼성전기(신규후보), 두산에너빌리티(대미투자법 원전), GEV, TMUS, SPCX(매도의견), STM, 원익IPS·테스(⚠️티커)\n대기 트리거: 6/18 03:00 점도표→3차 집행(비둘기=META·AVGO·NVDA 재매수 / 매파=현금유지). 주말 이란 서명.\n영구반영: ios 클라이언트로 경제사냥꾼 자막 추출 성공(웹 봇차단 우회, 스크립트 반영). 토스 현금 624,771+$1.11 확정.\n검증완료: 대미투자법 6/18 시행($3,500억). 삼성전기 목표 iM230/DB300만. CPI4.2%·점도표 매파리스크(2차출처 보강).\n미확인: BOJ 1.0%(94%), 네마녀의날 6/18 앞당김, ACN실적, 젠슨황 대만$1,500억·한국 GPU9,700장\n다음 버전: v12\n```\n"
    },
    {
      "id": "report_v10_2026-06-13",
      "file": "docs/reports/report_v10_2026-06-13.md",
      "title": "정훈 PORTFOLIO DESK · v10 · 2026-06-13 (토)",
      "date": "2026-06-13",
      "version": 10,
      "kind": "보고서",
      "preview": "1. ⚠️ 매크로 그림 발산 — 최우선 검증 포인트: v9는 \"브렌트 $85~89 2개월 최저·휘발유 하락·CPI 에너지 완화\"로 봤으나, 6/13 재검색은 상반된 그림 — 이란/호르무즈 에너지 쇼크로 5월 CPI +4.2% YoY(MoM +0.5%)",
      "content": "# 정훈 PORTFOLIO DESK · v10 · 2026-06-13 (토)\n\n> 작성 기준: 국내 6/12(금) 확정 종가 / 미국 6/12(금) 마감. 시세=Yahoo 무키(`market_data.py`), 수익률=`pnl.py`, 목표가=`consensus.py`, 트리거=`triggers.py`, 실적일=`earnings.py`. **투자 자문 아님 — 모든 레벨은 분석 참고, 최종 결정은 정훈.**\n> 🆕 Claude Code 신시스템 첫 보고서. 3개 데스크(시장·매크로·리서치) **병렬 수집** → PM 종합 → git 커밋.\n\n## 변경점 (v9 대비)\n\n1. **⚠️ 매크로 그림 발산 — 최우선 검증 포인트**: v9는 \"브렌트 $85~89 2개월 최저·휘발유 하락·CPI 에너지 완화\"로 봤으나, 6/13 재검색은 **상반된 그림** — 이란/호르무즈 에너지 쇼크로 **5월 CPI +4.2% YoY(MoM +0.5%)·코어 +2.9%·PPI +6.5%·브렌트 ~$95(EIA 6~7월 $105 전망)**. 두 내러티브가 충돌 → **FOMC(6/18) 전 반드시 교차검증**. 보수적으로 **매파 리스크 상존** 가정.\n2. **FOMC 6/16~17, 결과 6/18 03:00 KST** — 동결 컨센서스 97%(CME)지만 **점도표(SEP) 동시 공개** + 케빈 워시 신임 의장 첫 회의 → 인플레 반영 상향 여부가 최대 관전. 연내 인상 확률 ~70%로 급등(미확인, 출처 편차 큼).\n3. **알트만 방한 연기 재확인** [정정 유지] — NAVER·삼성 단기 모멘텀 소멸. NAVER 6/12 +10.27% 급등분 되돌림 주의.\n4. 보유·현금·워치 구성 변동 없음(6/12 저녁 매매 여부 미확인 — 알려주면 반영). 트리거 전부 미발동(아래 §4).\n5. **신규 도구**: 평가손익·목표주가·트리거·실적일·차트가 무키 스크립트로 자동화. 본 보고서 하단 차트 2종 첨부.\n\n## 1. 시장 데스크\n\n- **코스피 8,123.62 (+4.63%, +359.67p)** — 3거래일 만 8,000선 회복, 올해 25번째 매수 사이드카(장중 고가 ~8,434). 수급: **외국인 +2.1조(25거래일 만 순매수 전환)·기관 +2.4조 동반 / 개인 -4.3조**. 코스닥 1,029.4 (+3.22%) 천스닥 복귀. 동인: 미-이란 긴장 완화 위험선호 + 간밤 미 강세.\n- 섹터: AI 밸류체인 주도, **반도체 대형주(삼성 +7.86%)→AI 소부장 일부 로테이션**. 보유 NAVER +10.27%·삼성 +7.86%, 워치 두산에너빌리티 +5.08% 두드러짐.\n- **미국 6/12**: S&P500 7,431.46(+0.50%)·나스닥 25,888.84(+0.31%)·다우 51,202.26(+0.70%)·필반 13,371.47(+1.52%) 동반 상승. 견인차 **SPCX 상장 첫날 +19.2% $160.95**(사상 최대 IPO, 시총 ~$2조) + 미-이란 평화 기대. 메가캡 혼조(AAPL -1.52%, ANET +4.37%).\n\n## 2. 매크로 데스크\n\n- **환율 USD/KRW 1,518 (+0.13%)**: 원화 약세 지속 → 외인 매도·환차손 요인이나 미국주 보유분 원화환산엔 우호적.\n- **금리**: FOMC 동결 ~97%(CME). **워시 첫 회의 + 점도표 공개** — 에너지발 인플레 반영 상향 여부가 핵심. ※ **한은은 점도표 미발표(연준 전용)**. 다음 금통위 7/16.\n- **지표·유가 [검증 필요]**: 위 변경점 ①의 충돌. 매크로 데스크 재검색 = CPI +4.2%/PPI +6.5%/브렌트 ~$95(에너지 +23.5%·휘발유 +40.5%). **단 미-이란 종전 MOU 서명 시 호르무즈 개방→유가·인플레 급반락 가능(양방향)**. 기관 유가 전망 편차 큼(GS $85 base ~ $120+, JPM $60 base — 미확인).\n- **이벤트 캘린더(2주, 폰 17:30~20:50 KST 기준)**:\n\n| 날짜(KST) | 이벤트 | 폰 가용 |\n|---|---|---|\n| 6/16~17 | FOMC 회의(2일) | — |\n| **6/18(목) 03:00** | **FOMC 금리·점도표·회견** | **불가(야간) → 6/18 본장 갭 대응** |\n| 시점 미정 | 美·이란 MOU 서명 | 헤드라인 리스크 상시 |\n| 6/24(수) | **MU 실적 (D-11)** ⚡ | 발표시각 확인 요 |\n| 7/16(목) | 한국은행 금통위 | (2주 밖) |\n\n## 3. 리서치 피드 — 경제사냥꾼\n\n> ⚠️ **자막 추출 전면 실패(웹 데이터센터 IP 봇차단)** — `hunter_latest.py` web→tv→mweb 폴백 모두 막힘. 아래는 **제목+WebSearch 교차검증 기반 추정**(채널 실제 종목·수치는 미확인). **12월 로컬(주거용 IP) 이전 시 자막 정상화 예정.** 매매 근거로 단정 사용 금지.\n\n- **① \"알트먼 방한 진짜 이유\"(6/12)** → **[정정]** 6/12 알트만 방한 개인사정 연기(서울신문·FN). 영상 전제(방한) 무효화. OpenAI IPO 임박은 **[미확인]**.\n- **② \"머스크 계약 수혜주 5선 🇰🇷+🇺🇸\"(6/12)** → SpaceX 테마 강세 **[검증]**(美 우주株 시총 1년 ~3배, 블룸버그). 한국 5종목 명단 **[미확인]**(자막 부재). 보유 TSLA·워치 SPCX 직결.\n- **③ \"한국 투자자 저점매수 집착\"(6/12)** → 심리/내러티브성, 구체 주장 **[미확인]**. 정훈 룰(\"물타기 금지·트랜치 분할·코스피 7,500 안전핀\")이 '바닥매수' 충동의 가드레일.\n- **④ 쇼츠 \"월가가 사는 미래산업주\"(6/13)** → AI·우주 테마 강세 방향 **[검증]**, 구체 종목 **[미확인]**. 보유 NVDA·MU·AVGO·ANET, 워치 GEV·두산에너빌리티(AI 전력축) 테마 일치.\n- **⑤ 쇼츠 \"삼성 미 비상장 이유\"(6/13)** → 구조적 배경 **[검증]**(비용·규제·외인지분). 단기 가격영향 제한적.\n\n## 4. PM 종합 (최종)\n\n**오늘의 한 줄 결론**: 외인 복귀·SPCX 흥행·이란 완화로 추세는 위쪽이나, **윗꼬리 마감 + 매크로 인플레 그림 충돌 + FOMC 점도표 사흘 전** → **주말은 현금 그대로, 트리거 미발동 — 월요일 시나리오 대응.**\n\n### 보유 16종목 (수익률=원가 대비 `pnl.py` / 목표=美 `consensus.py`)\n\n| 국내 | 종가 | 수익률 | 매수존(눌림) | ⭐ | 코멘트 |\n|---|---|---|---|---|---|\n| LG전자 | 225,500 | **+45.3%** | 추가매수 비대상 | ★★★★★ | 손절선 없음, 액냉 CDU |\n| 삼성전자 | 322,500 | +22.6% | 295,000~305,000 | ★★★★★ | +7.9% 외인 순매수 1순위 |\n| 두산로보틱스 | 110,400 | +10.4% | 100,000 내외 | ★★★☆☆ | 소부장 로테이션 반대편, 추격금지 |\n| NAVER | 247,000 | -1.4% | 225,000~235,000 | ★★★★☆ | **알트만 연기로 모멘텀 소멸** — 되돌림 주의 |\n| 현대차 | 607,000 | -3.7% | 580,000~595,000 | ★★★☆☆ | 원화 약세 역풍, 관망 |\n\n| 미국 | 종가 | 수익률 | 목표(평균) | 괴리 | ⭐ | 코멘트 |\n|---|---|---|---|---|---|---|\n| MU | $981.61 | **+31.1%** | $828.73 | **-15.6%** | ★★★★★ | strong_buy(40)이나 목표 하회 — 6/24 실적(D-11) 주시 |\n| AAPL | $291.13 | +13.2% | $312.72 | +7.4% | ★★★★☆ | buy(43), 숨고르기 홀딩 |\n| VOO | $681.95 | +5.7% | (ETF) | — | ★★★★★ | 적립 지속 |\n| NVDA | $205.19 | +2.9% | $298.93 | **+45.7%** | ★★★★★ | strong_buy(59), 상방 큼 🟢 |\n| ANET | $163.24 | +0.7% | $189.13 | +15.9% | ★★★★☆ | strong_buy(27) 흑자전환 |\n| TSLA | $406.43 | -3.8% | $419.94 | +3.3% | ★★★☆☆ | buy(41), SPCX 동반 |\n| MSFT | $390.74 | -4.7% | $561.39 | **+43.7%** | ★★★★☆ | strong_buy(55) 🟢 |\n| GOOGL | $359.68 | -7.2% | $432.83 | +20.3% | ★★★★☆ | strong_buy(53) TPU 모멘텀 |\n| AVGO | $382.07 | -9.3% | $522.06 | **+36.6%** | ★★★★☆ | strong_buy(45) 🟢 FOMC 후 재매수 후보 |\n| META | $566.98 | -10.6% | $827.32 | **+45.9%** | ★★★★☆ | strong_buy(59) 🟢 재매수 1순위 후보 |\n| ORCL | $184.13 | -20.7% | $255.95 | **+39.0%** | ★★★☆☆ | buy(39) 바닥 다지기, 상방 여지 |\n\n> 🟢 = 목표주가 현재가 대비 +30% 이상 괴리(추가매수 검토 신호). MU는 목표 하회(-15.6%) → 차익 경계.\n> **총 자산(주식+현금) 8,353,877원 / 주식 평가손익 합계 +190,491원** (`pnl.py`, 환율 1,517.89). 국내 평가손익 +173,200원, 미국 +$11.39.\n\n### 워치리스트 (활성 7)\n\n| 종목 | 종가 | 목표/의견 | 상태 |\n|---|---|---|---|\n| 두산에너빌리티 | 93,100 (+5.1%) | — | 원전 테마 강세, '십만빌리티' D-7%(10만까지) |\n| GE Vernova | $940.66 (+3.7%) | $1,211.89 buy(33, +28.8%) | AI 전력 테마 재점화 |\n| T-Mobile | $189.10 (+1.8%) | $260.81 buy(26, +37.9%🟢) | 스타링크 D2C |\n| SPCX | $160.95 (+19.2%) | $139.33 **sell(3, -13.4%)** | 첫날 확정. 애널 소수·매도의견 — 신규진입 보류 |\n| STM | $77.30 (-1.1%) | $63.69 buy(14, -17.6%) | 약세 지속, 후순위 |\n| 원익IPS ⚠️ | 36,750 | — | ⚠️티커 검증필요(보고서값 183,300과 불일치), 매수존 무효 |\n| 테스 ⚠️ | 22,000 | — | ⚠️티커 검증필요(보고서값 182,200과 불일치) |\n\n유예(~6/19 언급 없으면 제외): 한화에어로, 카카오, VRT, TSM, Filtronic.\n\n### 제안 액션\n\n- **홀딩 전 종목, 주말 현금 동결.** `triggers.py` 결과 **발동 트리거 0건** — 코스피 8,124는 안전핀 7,500 대비 +8.3%, 2차 기준 8,000 대비 +1.5% 위. NAVER·삼성 1차 매수존도 각각 +5.1%/+5.7% 위(미진입).\n- **강세 시각**: 외인 복귀 + 이란 완화 + FOMC 동결이면 코스피 골드만 경로 유효. 미국 보유주 목표주가 괴리 큼(META·NVDA·MSFT·AVGO +37~46%).\n- **신중 시각**: 윗꼬리 마감·개인 4.3조 순매도·**인플레 그림 충돌(매파 점도표 리스크)** → 서명 무산·점도표 매파 시 급등분 되돌림 빠를 수 있음.\n- **SPCX 신규 보류 유지**: 애널 3인·매도의견 목표 $139·분수주 시장가 전용.\n\n### 현금 624,771원 트랜치 (전부 미집행, `triggers.py` 연동)\n\n- **1차 (10~15만)**: NAVER 225~235k 또는 삼성 295~305k 눌림 도달 시만. 현재 둘 다 매수존 위 → 보류. 월요일 갭업이면 집행 보류.\n- **2차 (~20만)**: 이란 서명 무산 + 코스피 8,000 하회 시. 현재 +1.5% 위.\n- **3차 (~22.5만)**: **6/18(목) 03:00 FOMC 확인 후.** 동결+중립(점도표 비매파) → META·AVGO 등 -9~-10% 조정주 재매수(목 17:30~20:50 지정가 예약 → 22:30 집행). 점도표 매파 서프라이즈 → 현금 유지.\n\n### 지켜볼 것 (2주 + 실적)\n\n- **6/13~14 주말**: 이란 MOU 서명 여부 → 월요일 갭 방향. **6/15(월)** SPCX 2일차.\n- **6/18(목) 03:00**: FOMC 점도표 → 3차 트랜치 + 인플레 그림 충돌 해소.\n- **6/24(수)**: **MU 실적(D-11)** — 보유 +31% 종목, 목표 하회 중이라 주목.\n- 7월 실적 클러스터: 7/22 TSLA·GEV·TMUS, 7/23 현대차·GOOGL·STM, 7/24 LG전자, 7/29 삼성·META·MSFT, 7/30 AAPL.\n- **7/16** 한국은행 금통위. 알트만 방한 새 일정(미정).\n\n## 5. 오늘의 이슈 선택지 (번호로 선택 → 상세 분석)\n\n① **매크로 인플레 그림 충돌 검증** — v9(유가 완화) vs v10(에너지 쇼크) 어느 게 맞나 + FOMC 점도표 시나리오별 대응\n② **MU 딥다이브** — +31% 보유주인데 목표가 -15.6% 하회, 6/24 실적 전 트림 vs 홀딩 (`/stock-deepdive MU`)\n③ SPCX 첫날 정밀 분석 + 나스닥100 편입 수급\n④ META·AVGO·NVDA 목표주가 +37~46% 괴리 — FOMC 후 3차 트랜치 재매수 우선순위\n\n## STATE SNAPSHOT\n\n```\n[STATE SNAPSHOT v10 2026-06-13]\n현금: 624,771원 (1차/2차/3차 전부 미집행 — 트리거 0건 발동, 6/12 저녁 매매 미확인)\n보유변동: 없음(가정). 총자산 8,353,877원 / 주식 평가손익 +190,491원 (snapshot 2026-06-13 기록)\n워치리스트(활성): 두산에너빌리티, GEV, TMUS, SPCX($160.95 sell의견), STM, 원익IPS·테스(⚠️티커검증필요)\n유예(~6/19): 한화에어로, 카카오, VRT, TSM, Filtronic\n대기 트리거: ①주말 이란 MOU 서명→월 갭 ②FOMC 6/18 03:00 점도표→3차 집행(동결+비매파=META·AVGO 재매수)\n영구교정/플래그: 매크로 인플레 그림 v9↔v10 충돌(검증 필요). 자막 추출 웹 IP 봇차단(로컬 이전 시 해소). 원익IPS·테스 Yahoo 티커 불일치.\n미국 목표주가 괴리 🟢(+30%↑): NVDA+45.7%·META+45.9%·MSFT+43.7%·AVGO+36.6%·ORCL+39.0% / MU 목표 -15.6% 하회\n다음 버전: v11\n```\n"
    }
  ],
  "outlook": [
    {
      "horizon": "오늘 (6/22 월) 마감",
      "tag": "관망·집행0",
      "dir": "→",
      "text": "폰창 관망 확정 — 살 것·팔 것 없음. 외인 재유입 분수령 실패(외인 −2.55조 2일연속 순매도)·NAVER 222k로 매수존 이탈 → NAVER 1차 매수 보류 확정. 미국 예약 0건(재개 갭·룰7·3차 동결). 단 코스피 9,114.55 종가 사상최고(개인+기관 흡수)·SK하이닉스 시총 1위 등극."
    },
    {
      "horizon": "내일 (6/23 화)",
      "tag": "베이킹·MSCI",
      "dir": "→",
      "text": "새벽 MSCI 연례 시장분류 발표(한국 선진국 관찰대상, 선반영 해소 변동성). ★저녁 폰창에서 MU 절반차익(0.02주) 사전 베이킹 — 6/25 새벽 실적 폰 미가용 대비. 오늘 분수령 실패 → 외인 방향 재확인."
    },
    {
      "horizon": "이번주 (6/22~26)",
      "tag": "이벤트 주간",
      "dir": "→",
      "text": "반도체 호황 '시험 주간'. 6/25(목) 더블 분수령 = MU 실적(새벽 ~05:00)+美 5월 PCE(밤 21:30). 둘 다 야간/새벽 폰 미가용 → 6/24 20:50 전 예약 베이킹. 외인 2일연속 매도 → 6/23+ 재유입 재확인이 추세 판가름. ⚠️신규: 7월 국민연금 리밸런싱 재개 시 받침대(개인 빚투 38조) 제거 리스크."
    },
    {
      "horizon": "이번달 (6월 잔여)",
      "tag": "관망·재개조건",
      "dir": "→",
      "text": "3차 트랜치(META·AVGO) FOMC 매파로 보류 중. 재개 조건 = 비둘기 전환 / META 7/29 실적 / 외인 순매수 복귀 중 하나. 안전핀 코스피 7,500(현 9,052, +20.7% 버퍼)."
    }
  ],
  "index_forecast": [
    {
      "name": "코스피",
      "ref": 9114.55,
      "low": 8900,
      "base": 9100,
      "high": 9350,
      "dir": "→",
      "note": "6/22 종가 사상최고(외인 −2.55조 던졌으나 개인+기관 흡수). 외인 2일연속 매도=신중, 6/23+ 재유입 재확인 전 추세 미확정. 7월 국민연금 받침대 제거 주시."
    },
    {
      "name": "나스닥",
      "ref": 26517.93,
      "low": 25900,
      "base": 26400,
      "high": 27000,
      "dir": "→",
      "note": "오늘밤 재개 선물 −1.2%(반도체 차익)·누적 갭. SOX 신고가 되돌림 위험. PCE(6/25)가 방향 결정."
    },
    {
      "name": "S&P500",
      "ref": 7500.58,
      "low": 7380,
      "base": 7480,
      "high": 7600,
      "dir": "→",
      "note": "재개 선물 −0.74%·VIX 16.78 반등. 이란 재긴장·유가 상방. 6/25 PCE 분수령."
    },
    {
      "name": "필라델피아반도체",
      "ref": 14341.78,
      "low": 13700,
      "base": 14200,
      "high": 15000,
      "dir": "→",
      "note": "6/18 +6.42% 신고가 후 오늘밤 시초 되돌림 위험. MU 6/25 실적이 섹터 분수령."
    }
  ],
  "tasks": {
    "today": [
      {
        "id": "t-0622-1",
        "text": "✅확인됨: 외인 코스피 6/22 −2조5,463억 순매도(2일연속)·개인 +2.15조·기관 +3,038억. 재유입 분수령 실패=신중 경보(단 지수는 흡수로 사상최고)",
        "done": true
      },
      {
        "id": "t-0622-2",
        "text": "✅결정: NAVER 1차 매수 보류 확정 — 외인 재유입 실패+종가 222k 매수존 이탈+정리후보 3중 미충족. 폰창 무집행",
        "done": true
      },
      {
        "id": "t-0622-3",
        "text": "오늘밤 22:30 美 재개 = 신규 진입 보류(선물 −1.2%·누적 갭·룰7). 3차 트랜치 동결 유지. 미국 예약 0건",
        "done": false
      },
      {
        "id": "t-0622-4",
        "text": "SK하이닉스 美 SEC ADR 승인 헤드라인 주시 — 6/22 시점 정식승인 미발표(메리츠 8월 상장·목표 295만). 단 시총 1위 등극",
        "done": false
      }
    ],
    "week": [
      {
        "id": "t-w-1",
        "text": "6/23(화) 새벽 MSCI 시장분류 발표 확인(한국 선진국 관찰대상)",
        "done": false
      },
      {
        "id": "t-w-2",
        "text": "★6/23(화) 저녁 폰창 MU 절반차익 사전 베이킹(소수점=시장가, 절반 0.02주)",
        "done": false
      },
      {
        "id": "t-w-3",
        "text": "6/24 20:50 전 6/25 MU 실적(새벽)+美 PCE(밤 21:30) 대응 예약주문 베이킹",
        "done": false
      },
      {
        "id": "t-w-4",
        "text": "안전핀 코스피 7,500 모니터링(현 9,052 — 비발동) + 이란 재긴장·유가 추적",
        "done": false
      }
    ],
    "month": [
      {
        "id": "t-m-1",
        "text": "3차 트랜치 재개 조건 점검(비둘기 전환 / META 7/29 / 외인 복귀)",
        "done": false
      },
      {
        "id": "t-m-2",
        "text": "트림 후보 점검 — AAPL(목표 근접) / MU(시클리컬 정점)",
        "done": false
      },
      {
        "id": "t-m-3",
        "text": "KT&G 신규 워치 후보 딥다이브 검토(디펜시브 분산)",
        "done": false
      }
    ]
  },
  "task_counts": {
    "today": {
      "done": 2,
      "total": 4
    },
    "week": {
      "done": 0,
      "total": 4
    },
    "month": {
      "done": 0,
      "total": 3
    }
  },
  "orders": [
    {
      "id": "o-naver-1",
      "label": "NAVER",
      "ticker": "035420.KS",
      "action": "매수",
      "status": "보류",
      "price": 229500,
      "shares": 1,
      "amount_krw": 229500,
      "date": "2026-06-22",
      "note": "1차 트랜치. 6/22 보류 확정 — 외인 재유입 분수령 실패(2일연속 −2.55조)+종가 222k로 매수존(225~235k) 이탈+정리후보. 3중 미충족. 외인 재유입 재확인 시 재검토."
    }
  ],
  "tasks_updated": "2026-06-22"
};
