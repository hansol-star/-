#!/usr/bin/env python3
"""guard_selftest.py — **가드가 실제로 위반을 잡는지** 검증하는 메타 가드 (stdlib only)

■ 왜 필요한가 [8/24 정훈 지시 *"가드가 실제로 도는지 확인하는 절차도 만들어줘"*]

   같은 실패가 **세 번** 반복됐다. 전부 "가드는 초록불인데 실제로는 아무것도 안 잡던" 형태다:
     · 8/23 `check_repealed_rules` — **7주간 초록불**이었는데 손으로 찾아보니 폐기된 7,500 안전핀이
       세 군데에 현행처럼 살아 있었다. 원인은 룰이 아니라 탐지기의 사각(정규식 창 20자·스캔 목록 1개).
     · 8/24 `lookahead_guard` — 첫 실행의 위반 1건이 대상 코드가 아니라 **가드 자신의 픽스처 버그**였다.
     · 8/24 `split_guard` — `validate`를 오프라인으로 걸어 `high`가 **구조적으로 뜰 수 없는** 상태였다.

   ⇒ **초록불은 "위반이 없다"가 아니라 "탐지기가 그 형태를 안 본다"는 뜻일 수 있다.**
     그동안 우리는 이걸 매번 **손으로**(git stash로 위반을 되돌려 넣어) 확인했고, 그 확인은
     주석에만 남아 **재실행이 불가능**했다. 이 파일이 그 절차를 기계로 고정한다.

■ 방법 — 위반을 심고 잡히는지 본다 (mutation testing의 축소판)

   ① **서브프로세스형** — 자체 음성 테스트를 가진 가드는 그것을 실행한다.
   ② **주입형** — 임시 ROOT에 **위반 파일**을 만들고 `validate_report`의 check를 돌려
      기대한 FAIL/WARN이 나오는지 본다. 그리고 **정상 파일**로도 돌려 **오탐이 없는지** 본다.
      두 방향을 모두 봐야 한다 — 무조건 잡는 가드는 무조건 통과하는 가드만큼 쓸모없다.
      판정은 `expect_pattern` 정규식으로 한다(파일 부재 등 부수 실패에 흔들리지 않게).
   ③ **커버리지** — 음성 테스트가 **없는** 가드를 목록으로 드러낸다. 이게 결핍 목록이다.

■ ⚠️ 한계 (과장하지 않기)
   · 여기 통과 = "이 가드가 **이 형태의** 위반을 잡는다"일 뿐. 다른 형태의 사각은 여전히 있을 수 있다.
     8/23 사고가 정확히 그것이었다 — 한글 문구는 잡았지만 영문 서술은 못 잡았다.
   · 그래서 **새 사고가 나면 그 사례를 여기에 픽스처로 추가**하는 것이 이 파일의 사용법이다.
   · 커버리지 숫자를 성취로 읽지 말 것. 미등록 가드가 훨씬 많다.

사용:
  python3 guard_selftest.py            # 전체 (exit 1 = 가드가 무력)
  python3 guard_selftest.py --coverage # 커버리지 표만
  python3 guard_selftest.py --json
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


# ── ① 서브프로세스형 (자체 음성 테스트를 가진 가드) ─────────────────────
SUBPROCESS_TESTS = [
    ("lookahead_guard.py", ["--negative"], "룩어헤드 접두사 불변성 — 심어둔 미래참조 3종 적발"),
    ("split_guard.py", ["--selftest"], "분할 스케일 혼재 — 10배 왜곡 적발 + 오프라인 경로"),
    ("wiring_audit.py", ["--selftest"], "기능 단위 배선 — 걷어낸 기능 적발 + 동명 플래그 오인 방지"),
    ("toss_snapshot.py", ["--selftest"], "토스 주문 차단 — 매매 가능 자격증명의 조회 전용 불변식(우회 4종 포함)"),
]


def run_subprocess_tests() -> list[dict]:
    out = []
    for script, args, desc in SUBPROCESS_TESTS:
        p = os.path.join(HERE, script)
        if not os.path.exists(p):
            out.append({"guard": script, "ok": None, "desc": desc, "msg": "스크립트 없음"})
            continue
        try:
            r = subprocess.run([sys.executable, p] + args, capture_output=True,
                               text=True, timeout=180, cwd=REPO)
            ok = r.returncode == 0
            msg = "" if ok else (r.stdout or r.stderr or "")[-400:]
        except subprocess.TimeoutExpired:
            ok, msg = False, "timeout"
        out.append({"guard": f"{script} {' '.join(args)}", "ok": ok, "desc": desc, "msg": msg})
    return out


# ── ② 주입형 (임시 ROOT에 위반을 심는다) ────────────────────────────────
SAFE_CLAUDE = (
    "# CLAUDE.md\n\n"
    "- 최신 보고서 = `docs/reports/`에서 가장 높은 `report_v*.md`(현재 **v83**·2026-08-24).\n"
    "- 매수 안전핀: 낙폭 사다리(`tranche_rules.py`)로 판정한다. 하드플로어 = S&P500 폭풍 ≥70%ile.\n"
)
VIOLATING_CLAUDE = (
    "# CLAUDE.md\n\n"
    "- 최신 보고서 = `docs/reports/`에서 가장 높은 `report_v*.md`(현재 **v83**·2026-08-24).\n"
    "- **매수 안전핀 — 코스피 종가가 7,500을 하회하면 신규 매수 전면 동결(0원).**\n"
)

RISK_SPEC = """## Return format (to PM)
```
## 리스크 데스크
- 🚦 트리거 상태: {...}
- ⚖️ 손익비: {...}
```
"""

HIST_LG = "date,close\n2026-08-11,181700.0\n"   # 8/12 사고 당시 전일 종가

# 2026-08-27 신설 3가드가 쓰는 픽스처 보고서 경로(파일명에서 날짜를 파싱하므로 형식 고정)
RPT = "docs/reports/report_v99_2026-08-27.md"

# 픽스처의 날짜는 "오늘"이어야 한다 — check_routine_health는 3일 이상 정지도 WARN으로 잡으므로
# 고정 날짜를 쓰면 clean 픽스처가 시간이 지나며 저절로 위반이 된다(자기부패 픽스처).
def _DAYS_AGO(n: int) -> str:
    """픽스처용 상대 날짜 — 고정 날짜를 쓰면 시간이 지나며 clean이 저절로 위반이 된다."""
    return (datetime.date.today() - datetime.timedelta(days=n)).isoformat()


def _LINES(*rows: str) -> str:
    return "\n".join(rows) + "\n"


def _CSV(day: str) -> str:
    return _LINES("date,open,high,low,close", day + ",1,1,1,1")


_TRIM_REPORT = _LINES("# v99", "- 삼성전자 트림 검토", "- 삼성전자 일부 매도 고려",
                      "- 삼성전자 트림 시점 재검토")


_ARCHIVE_OK = {f"data/financials/T{i}.json": "{}" for i in range(20)}
_ARCHIVE_OK.update({f"data/history_ohlcv/T{i}.csv": "d" for i in range(40)})
_ARCHIVE_OK.update({f"data/history/T{i}.csv": "d" for i in range(40)})


_TODAY_KST = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")

INJECTION_TESTS = [
    {
        "name": "check_canonical_facts",
        "desc": "\ubb38\uc11c\uc758 \ud575\uc2ec \uc218\uce58\uac00 \uc815\ubcf8 \uc6d0\uc7a5\uacfc \uc5b4\uae0b\ub098\uba74 \uc7a1\ub294\uac00",
        "why": "7/29 CXMT \uc810\uc720\uc728 \uc624\ub958(\ubb38\uc11c ~11% vs \uc2e4\uc81c 7%)\uac00 5\uc8fc\uac04 \uc138 \ubb38\uc11c\uc5d0 \uc0b4\uc544 \uc788\uc5c8\uace0, "
               "\uc7a1\uc740 \uac83\uc740 \uc6b0\ub9ac \uac00\ub4dc\uac00 \uc544\ub2c8\ub77c \uc720\ud29c\ube0c \ucc44\ub110\uc774\uc5c8\ub2e4. '\uc22b\uc790 \uc790\uccb4\uac00 \ud2c0\ub838\ub294\uc9c0'\ub97c \ubcf4\ub294 \uc7a5\uce58\uac00 0\uac1c\uc600\ub2e4",
        "pattern": r"\uc218\uce58 \uc815\ubcf8 \ubd88\uc77c\uce58",
        "violate": {'data/app/facts.json': '{"facts": [{"key": "cxmt_dram_share", "label": "CXMT D램 점유율", "value": 7.0, "unit": "%", "tolerance": 0.6, "basis": "매출 기준", "asof": "2026-Q2", "source": "Counterpoint", "verified_on": "2026-08-30", "recheck_days": 120, "pattern": "(?:CXMT|창신메모리)(?:는|가|의|\\\\s)*\\\\**(\\\\d{1,2}(?:\\\\.\\\\d)?)\\\\s*%"}]}', 'CLAUDE.md': '# CLAUDE.md\n\nCXMT 점유율은 세계 4위로 CXMT 11% 수준이다.\n'},
        "clean":   {'data/app/facts.json': '{"facts": [{"key": "cxmt_dram_share", "label": "CXMT D램 점유율", "value": 7.0, "unit": "%", "tolerance": 0.6, "basis": "매출 기준", "asof": "2026-Q2", "source": "Counterpoint", "verified_on": "2026-08-30", "recheck_days": 120, "pattern": "(?:CXMT|창신메모리)(?:는|가|의|\\\\s)*\\\\**(\\\\d{1,2}(?:\\\\.\\\\d)?)\\\\s*%"}]}', 'CLAUDE.md': '# CLAUDE.md\n\nCXMT 점유율은 세계 4위로 CXMT 7% 수준이다.\n'},
        "args": (),
    },

    {
        "name": "check_tasks",
        "desc": "tasks.json이 존재하지 않는 보고서를 가리키면 잡는가",
        "why": "source_report는 앱 #plan 화면이 '어느 보고서 기준인가'를 말하는 유일한 근거다. "
               "존재하지 않는 파일을 가리키면 앱은 멀쩡해 보이는데 근거가 없는 상태가 된다 "
               "(7/2 intra-version stale 사고의 같은 계열)",
        "pattern": "source_report 파일 없음",
        "violate": {"data/app/tasks.json": json.dumps(
            {"source_report": "docs/reports/report_v404_2026-01-01.md", "as_of": "16:05"},
            ensure_ascii=False)},
        "clean": {
            "docs/reports/report_v99_2026-08-25.md": "# v99",
            "data/app/tasks.json": json.dumps(
                {"source_report": "docs/reports/report_v99_2026-08-25.md", "as_of": "16:05"},
                ensure_ascii=False),
        },
        "args": (),
    },

    {
        "name": "check_freshness",
        "desc": "tasks.json이 최신 보고서보다 낡으면 잡는가",
        "why": "7/12 실사고 — v46 R2가 stocks·hunter·flows는 갱신하고 tasks.json은 as_of/source_report "
               "스탬프만 바꾼 채 내용은 v45(7/9) 상태로 뒀다. 앱 #plan 화면이 '오늘 7/9 미장 개장' 같은 "
               "옛 정보를 노출했고, 舊 check_tasks는 source_report 존재만 봐서 통과시켰다 — "
               "스탬프만 갱신하는 stale을 잡는 것이 이 검사다",
        "pattern": "tasks.json updated",
        "violate": {
            "docs/reports/report_v99_2026-08-25.md": "# v99",
            "data/app/tasks.json": json.dumps({"updated": "2026-08-20"}, ensure_ascii=False),
        },
        "clean": {
            "docs/reports/report_v99_2026-08-25.md": "# v99",
            "data/app/tasks.json": json.dumps({"updated": "2026-08-25"}, ensure_ascii=False),
        },
        "args": (99,),
    },

    {
        "name": "check_flows",
        "desc": "수급 원장에 숫자 대신 추측 문자열이 들어가면 잡는가",
        "why": "수급 수치는 '순매도 우위' 같은 산문으로 적히는 순간 계산에서 빠지고 추세 판정이 죽는다. "
               "CLAUDE.md 상시 원칙(추측 금지·미확인 명시)을 원장 층위에서 기계로 강제한다",
        "pattern": "추측 문자열 금지",
        "violate": {"data/app/flows.json": json.dumps(
            {"updated": "2026-08-25",
             "series": [{"date": "2026-08-25", "foreign": "순매도 우위"}]}, ensure_ascii=False)},
        "clean": {"data/app/flows.json": json.dumps(
            {"updated": "2026-08-25",
             "series": [{"date": "2026-08-25", "foreign": -1234}]}, ensure_ascii=False)},
        "args": (),
    },

    {
        "name": "check_rule_ledger",
        "desc": "룰1 사다리 원장이 보고서 날짜보다 뒤처지면 잡는가",
        "why": "8/6 실사고 — 원장이 7/30 1건에서 멈춰 있었고, 그 1건이 말하는 상태"
               "(해금 35%·상한 282,438원·halted=false)와 8/6 실제(해금 15%·상한 0원·halted=true)가 "
               "정반대였다. 룰1은 7/31 RESET 정책상 매일 재계산이 전제라 원장이 멈추면 "
               "self-review 룰 추적이 통째로 옛 상태를 본다",
        "pattern": "rule_log 최신",
        "violate": {
            "docs/reports/report_v99_2026-08-25.md": "# v99",
            "data/app/rule_log.jsonl": _LINES(json.dumps({"date": "2026-08-01"})),
        },
        "clean": {
            "docs/reports/report_v99_2026-08-25.md": "# v99",
            "data/app/rule_log.jsonl": _LINES(json.dumps({"date": "2026-08-25"})),
        },
        "args": (99,),
    },

    {
        "name": "check_data_archive",
        "desc": "받아온 원본 데이터 자산이 사라지거나 줄면 잡는가",
        "why": "8/30 정훈 지시 '데이터는 다 저장해두라고 했잖아'. 舊엔 app 요약 5기/8기만 남기고 "
               "나머지를 버렸다 — 주석은 저장한다고 적혀 있었으나 실제로는 안 했다. "
               "받아온 걸 남기는 축이 조용히 비면 소급 분석이 통째로 불가능해진다",
        "pattern": "데이터 자산",
        "violate": {"docs/reports/report_v99_2026-08-25.md": "# v99"},
        "clean": _ARCHIVE_OK,
        "args": (),
    },

    {
        "name": "check_history_cache",
        "desc": "일봉 캐시가 정지되면 잡는가",
        "why": "8/12 실사고 — 67/70종목이 최대 8일 정지였고 그 캐시로 계산한 상한가가 4,000원 틀려 "
               "LG전자 오더 경고가 어긋났다. vol_gauge·하드플로어·가격밴드가 전부 이 캐시를 읽으므로 "
               "낡으면 룰 판정이 낡은 값으로 나온다",
        "pattern": "history 캐시 정지",
        "violate": {
            ".claude/skills/portfolio-desk/portfolio.json":
                json.dumps({"holdings": {"kr": [{"ticker": "005930.KS"}]}}, ensure_ascii=False),
            "data/history/005930.KS.csv": _CSV(_DAYS_AGO(30)),
        },
        "clean": {
            ".claude/skills/portfolio-desk/portfolio.json":
                json.dumps({"holdings": {"kr": [{"ticker": "005930.KS"}]}}, ensure_ascii=False),
            "data/history/005930.KS.csv": _CSV(_DAYS_AGO(0)),
        },
        "args": (),
    },

    {
        "name": "check_transcript_persistence",
        "desc": "자막 기본 저장 경로가 임시 디렉터리로 되돌아가면 잡는가",
        "why": "8/30 실사고 — hunter_latest.OUTDIR 기본값이 gettempdir이라 세션이 끝나면 자막이 사라졌고 "
               "gitignore가 겹쳐 두 겹으로 막혔다. 아카이브 648편 중 원문 자막이 0편 남아 "
               "전수 재분석이 메타데이터로 제한됐다. 편의로 되돌리면 다음 세션부터 조용히 다시 사라진다",
        "pattern": "자막 저장 경로 회귀",
        "violate": {".claude/skills/portfolio-desk/scripts/hunter_latest.py":
                    _LINES('import os, tempfile',
                           'OUTDIR = os.environ.get("HUNTER_OUTDIR", tempfile.gettempdir())')},
        "clean": {".claude/skills/portfolio-desk/scripts/hunter_latest.py":
                  _LINES('import os',
                         'OUTDIR = os.environ.get("HUNTER_OUTDIR", _REPO_TRANSCRIPTS)')},
        "args": (),
    },

    {
        "name": "check_pending_decisions",
        "desc": "정훈 결정 대기가 14일 넘게 방치되면 잡는가",
        "why": "d21(GOOGL 재배치 지정가 상향)이 7/7부터 26일째 미결이었다. "
               "대기 항목은 아무도 재촉하지 않으면 영원히 대기한다 — 결정 큐에 SLA를 건다",
        "pattern": "결정 대기",
        "violate": {"data/app/decisions.jsonl": _LINES(json.dumps(
            {"id": "d99", "date": "2026-08-01", "topic": "테스트 안건", "status": "결정 대기"},
            ensure_ascii=False))},
        "clean": {"data/app/decisions.jsonl": _LINES(json.dumps(
            {"id": "d99", "date": "2026-08-29", "topic": "테스트 안건", "status": "결정 대기"},
            ensure_ascii=False))},
        "args": (datetime.date(2026, 8, 30),),
    },

    {
        "name": "check_prose_order_link",
        "desc": "보고서 산문이 트림을 3회 이상 논하는데 orders에 없으면 잡는가",
        "why": "8/2 실측 — 7주 손실의 68.7%가 별점2 두 종목에서 났는데 보고서 산문엔 트림이 8~9회 "
               "등장하고 tasks.json orders엔 0회였다(git log -S). 체결된 7건은 전부 orders 경유. "
               "오더북에 들어간 것만 집행된다 — 산문에 남은 판단은 증발한다",
        "pattern": "orders 미등록",
        "violate": {
            "data/app/tasks.json": json.dumps({"orders": []}, ensure_ascii=False),
            "docs/reports/report_v99_2026-08-25.md": _TRIM_REPORT,
        },
        "clean": {
            "data/app/tasks.json": json.dumps(
                {"orders": [{"ticker": "005930.KS", "action": "트림 지정가"}]}, ensure_ascii=False),
            "docs/reports/report_v99_2026-08-25.md": _TRIM_REPORT,
        },
        "args": ("docs/reports/report_v99_2026-08-25.md",),
    },

    {
        "name": "check_routine_health",
        "desc": "무인 루틴이 실패했거나 오래 안 돌았으면 잡는가",
        "why": "9/1 무인 루틴을 웹 Routines에서 윈도우 작업 스케줄러로 옮겼다(경로 B). "
               "웹은 실패가 대시보드에 남았지만 로컬은 아무 데도 안 남는다 — "
               "local_migration §3이 경로 B의 단점으로 콕 집어 적어둔 '실패가 조용하다'가 이것이다. "
               "런처가 남기는 last_status.json을 읽는 이 검사가 유일한 감시자다. "
               "★9/1 실측: R1이 영상 6편을 분석해놓고 커밋을 못 했는데 verdict=OK로 찍혔다 — "
               "런처의 영어 정규식(permission denied 등)이 한국어 산문 설명을 못 잡았다. "
               "⇒ 판정을 '말'에서 '워킹트리(git status)'로 옮겼고 이 케이스가 그걸 지킨다",
        "pattern": r"무인 루틴",
        # ★[9/1] 픽스처를 **실제로 일어난 사고**로 교체했다. 舊 픽스처(NOT_LOGGED_IN)는
        #   verdict!=OK 한 줄이면 잡히는 쉬운 형태였고, 정작 그날 새어나간 건
        #   "exit 0 · verdict OK · 로그도 정상인데 커밋만 못 한" 조용한 실패였다.
        #   가드는 잡기 쉬운 걸로 시험하면 안 된다 — 실제로 통과당한 형태로 시험한다.
        "violate": {'data/logs/routines/last_status.json':
                    '{"kind":"r1","verdict":"UNCOMMITTED","exit_code":0,'
                    '"kst":"' + _TODAY_KST + ' 12:08:06","minutes":7,"log":"x",'
                    '"uncommitted":11,"scheduled":"10:00","late_min":120}'},
        "clean":   {'data/logs/routines/last_status.json':
                    '{"kind":"r2","verdict":"OK","exit_code":0,'
                    '"kst":"' + _TODAY_KST + ' 16:45:00","minutes":41,"log":"x",'
                    '"uncommitted":0,"scheduled":"16:00","late_min":0}'},
        "args": (),
    },

    {
        "name": "check_memory_index",
        "desc": "의미검색 인덱스가 원장보다 낡으면 잡는가",
        "why": "9/1 신설. memory_embed 인덱스는 파생물이라 원장이 늘어도 안 따라오는데 "
               "회수는 **성공한 것처럼 보인다**(옛 인덱스에서 그럴듯한 결과가 나온다). "
               "사라지는 게 하필 **최근 기억**이라 오늘 내린 결정이 회수에서 통째로 빠진다 — "
               "8/12 '쓰는 쪽과 읽는 쪽이 갈리면 데이터는 조용히 사라진다'의 인덱스판",
        "pattern": r"의미검색 인덱스",
        # 지문 해시가 안 맞는 인덱스 = 낡은 인덱스
        "violate": {'data/cache/memory_index.meta.json':
                    '{"model":"BAAI/bge-m3","n":10,"dim":1024,"metas":[],"texts":[],'
                    '"fingerprint":{"hash":"deadbeefcafe","reports_n":1}}',
                    'data/cache/memory_index.npz': 'x'},
        # clean = 인덱스가 **그 ROOT의 원장과 일치**하는 상태.
        # 빈 임시 ROOT의 지문 해시(43e774664ee2)를 박아둔다 — _fingerprint가 결정적이라 안정적이다.
        # ⚠️ _fingerprint 계산식을 바꾸면 이 해시도 같이 갱신해야 한다(안 하면 이 케이스가 먼저 깨져 알려준다).
        "clean": {'data/cache/memory_index.meta.json':
                  '{"model":"BAAI/bge-m3","n":10,"dim":1024,"metas":[],"texts":[],'
                  '"fingerprint":{"decisions.jsonl":0,"missed_moves.jsonl":0,'
                  '"hunter_archive.json":0,"reports_n":0,"reports_bytes":0,'
                  '"hash":"43e774664ee2"}}'},
        "args": (),
    },

    {
        "name": "check_allocation_band",
        "desc": "\uad6d\ub0b4\uc8fc \ube44\uc911\uc774 \ubaa9\ud45c \ubc34\ub4dc(18~22%)\ub97c \ubc97\uc5b4\ub098\uba74 \uc7a1\ub294\uac00",
        "why": "8/30 \uc2e0\uc124 \ub8f06. \uc774 \ub8f0\uc774 \uc0dd\uae30\uae30 \uc804\uae4c\uc9c0 \uad6d\ub0b4 28.7%\ub294 \ub204\uac00 \uc815\ud55c \uac12\uc774 \uc544\ub2c8\ub77c "
               "\uc6b0\uc5f0\ud788 \uadf8\ub807\uac8c \ub41c \uac12\uc774\uc5c8\ub2e4. \uadf8\ub7f0\ub370 \ub370\uc2a4\ud06c \uae30\uac04 \uc190\uc2e4\uc758 \uc2e4\uccb4\uac00 \uac70\uae30\uc600\ub2e4 \u2014 "
               "\uad6d\ub0b4 23.6%\u00d7\ucf54\uc2a4\ud53c -20.56% = -4.85%p. \uc704\ud5d8 \uae30\uc900\uc73c\ub85c\ub294 \ube44\uc911 28.7%\uac00 \ud3ec\ud2b8 \uc704\ud5d8\uc758 60.2%\ub97c \ub9cc\ub4e4\uc5c8\ub2e4",
        "pattern": r"\ubc30\ubd84 \ubc34\ub4dc \uc774\ud0c8",
        "violate": {'app/data.js': 'window.DATA = {"holdings": [{"label":"\\uc0bc\\uc131","ticker":"005930.KS","region":"kr","value_krw":30},{"label":"NVDA","ticker":"NVDA","region":"us","value_krw":70}]};'},
        "clean": {'app/data.js': 'window.DATA = {"holdings": [{"label":"\\uc0bc\\uc131","ticker":"005930.KS","region":"kr","value_krw":20},{"label":"NVDA","ticker":"NVDA","region":"us","value_krw":80}]};'},
        "args": (),
    },

    {
        "name": "check_star_prob_monotonic",
        "desc": "별점→확신확률 매핑이 비단조면 잡는가",
        "why": "8/22 재보정이 ⭐2를 0.32→0.50으로 올려 ⭐2(0.50) > ⭐3(0.45)의 비단조를 만들었다. "
               "근거였던 '⭐2 실측 상승 62%'의 정체는 8/29 star_validate ③횡단면에서 "
               "**NAVER 단일 종목(+22.2%·n33)의 낙폭과대 반등**으로 드러났다 = 오염 표본. "
               "그리고 그 비단조 매핑 위에서 나온 Brier 0.249를 PM이 '별점은 동전던지기'로 "
               "인용했다(8/29). 순서 척도 위의 proper scoring rule은 단조성이 전제다",
        "pattern": r"STAR_PROB 비단조",
        "violate": {".claude/skills/portfolio-desk/scripts/score_calls.py":
            "STAR_PROB = {5: 0.65, 4: 0.60, 3: 0.45, 2: 0.50, 1: 0.17}\n"},
        "clean": {".claude/skills/portfolio-desk/scripts/score_calls.py":
            "STAR_PROB = {5: 0.65, 4: 0.60, 3: 0.45, 2: 0.38, 1: 0.17}\n"},
        "args": (),
    },

    {
        "name": "check_verdict_grounding",
        "desc": "[정정]이 확정 사실이 아니라 경쟁 전망(설문·컨센서스)에만 기대면 잡는가",
        "why": "8/27 실사고 — 경제사냥꾼의 금통위 인상 전망을 채권전문가 설문(80% 동결)을 "
               "근거로 [정정] 처리했는데 그날 오후 한은이 실제로 3.00%로 인상했다. "
               "컨센서스는 사실이 아니다. 같은 오류가 6/22·6/24·7/2·7/3·7/6·8/1에도 있었고 "
               "**가드가 없어 4개월간 그대로 재발**했다",
        "pattern": r"대립·미결|전망·설문에만|아직 오지 않은 날짜",
        "violate": {RPT:
            "STATE SNAPSHOT\n\n경제사냥꾼은 한은 금통위가 인상을 전망한다고 했다.\n"
            "그러나 채권전문가 설문은 80%가 동결을 예상하므로 배치된다 — **[정정]**.\n"},
        "clean": {RPT:
            "STATE SNAPSHOT\n\n한은 금통위가 2.75%→3.00% 인상을 의결했다(6인 찬성). "
            "채널 방향이 맞았고 내 설문 근거가 빗나갔다 — **[정정]** 철회.\n"},
        "args": (RPT,),
    },
    {
        "name": "check_magnitude_sanity",
        "desc": "bp/%p 변동폭을 절대수준 없이 쓰면 잡는가",
        "why": "7/28 실사고 — 엔비디아 CDS를 '4~5%p 상승'으로 적었으나 실제는 +14bp→82bp로 "
               "**크기가 30배 과장**됐다. %(변화율)과 %p(절대폭) 혼동. "
               "단위·자릿수 오류는 영구교정 최다(16건·5/7~8/23 상시 재발)인데 가드가 없었다",
        "pattern": r"절대수준 병기 없음|자릿수 sanity|형식\(LOI",
        "violate": {RPT: "STATE SNAPSHOT\n\n엔비디아 CDS가 4~5%p 상승했다.\n"},
        "clean": {RPT: "STATE SNAPSHOT\n\n엔비디아 CDS는 +14bp 상승해 82bp가 됐다(5년물).\n"},
        "args": (RPT,),
    },
    {
        "name": "check_primary_source",
        "desc": "큰 계약 금액이 1차 출처 표지 없이 서술되면 잡는가",
        "why": "7/29 CXMT·7/26 SK 사고의 구조 — 2차 매체는 합계와 단독, 그룹과 계열사를 섞는다. "
               "큰 숫자일수록 회사 공식 뉴스룸·공시 원문까지 내려가야 한다",
        "pattern": r"1차 출처 표지 없음",
        "violate": {RPT:
            "STATE SNAPSHOT\n\nSK하이닉스-엔비디아 $7,500억 5년 HBM 공급계약 보도가 나왔다.\n"},
        "clean": {RPT:
            "STATE SNAPSHOT\n\nSK그룹-엔비디아 $5,000억+ LOI다. 회사 공식 뉴스룸 원문으로 확인했다.\n"},
        "args": (RPT,),
    },
    {
        "name": "check_repealed_rules",
        "desc": "폐기된 룰(7,500 안전핀)이 정본에 살아 있으면 잡는가",
        "why": "8/23 실사고 — 7주간 초록불인 채 세 군데에 현행처럼 살아 있었다",
        "pattern": r"7[,.]?500|안전핀|폐기",
        "violate": {"CLAUDE.md": VIOLATING_CLAUDE},
        "clean": {"CLAUDE.md": SAFE_CLAUDE},
        "args": (),
    },
    {
        "name": "check_versions",
        "desc": "정본(stocks.json)이 옛 보고서를 가리키면 stale로 잡는가",
        "why": "정본 stale은 앱·데스크가 옛 상태로 판단하게 만든다",
        "pattern": r"stale|source_report",
        "violate": {
            "docs/reports/report_v83_2026-08-24.md": "# v83\n",
            "data/app/stocks.json": json.dumps({"source_report": "report_v80_2026-08-21.md"}),
        },
        "clean": {
            "docs/reports/report_v83_2026-08-24.md": "# v83\n",
            "data/app/stocks.json": json.dumps({"source_report": "report_v83_2026-08-24.md"}),
        },
        "args": (83,),
    },
    {
        "name": "check_low_star_action",
        "desc": "⭐2 이하 보유가 '관망'으로 방치되면 잡는가",
        "why": "8/2 실사고 — 보고서 산문엔 트림이 8~9회 등장했는데 orders 등록은 0회였고, "
               "7주 손실의 68.7%가 그 두 종목(⭐2)에서 났다",
        "pattern": r"무결정 방치|관망",
        "violate": {
            "data/app/stocks.json": json.dumps(
                {"stocks": {"005380.KS": {"stars": 2, "trim": "관망"}}}, ensure_ascii=False),
            "data/app/tasks.json": json.dumps({"orders": []}),
        },
        "clean": {
            "data/app/stocks.json": json.dumps(
                {"stocks": {"005380.KS": {"stars": 2, "trim": "470,000원 1주 트림 지정가"}}},
                ensure_ascii=False),
            "data/app/tasks.json": json.dumps({"orders": [{"ticker": "005380.KS"}]}),
        },
        "args": (),
    },
    {
        "name": "check_kr_price_band",
        "desc": "국내 지정가가 당일 가격제한폭(±30%)을 넘으면 잡는가",
        "why": "8/12 실사고 — LG전자 익절 지정가 240,000원이 상한가 236,000원(전일종가 181,700×1.3)을 "
               "초과해 주문 자체가 접수 거부됐다. 판단은 맞았는데 물리적 접수 가능성을 아무도 안 봤다",
        "pattern": r"제한폭|상한|밴드|price_band|접수",
        "violate": {
            "data/history/066570.KS.csv": HIST_LG,
            "data/app/tasks.json": json.dumps(
                {"orders": [{"ticker": "066570.KS", "price": 240000,
                             "action": "트림 지정가", "status": "대기"}]}, ensure_ascii=False),
        },
        "clean": {
            "data/history/066570.KS.csv": HIST_LG,
            "data/app/tasks.json": json.dumps(
                # ⚠️ clean 가격은 **정규장 ±30%와 시간외 ±10%를 둘 다** 통과해야 한다.
                #   230,000원으로 잡았다가 시간외 밴드(181,700×1.1=199,870) 초과로 정당한 WARN이
                #   떠서 '오탐'으로 오판했다 — 또 픽스처 문제였다(8/24 세 번째).
                {"orders": [{"ticker": "066570.KS", "price": 195000,
                             "action": "트림 지정가", "status": "대기"}]}, ensure_ascii=False),
        },
        "args": (),
    },
    {
        "name": "check_order_feasibility",
        "desc": "국내 오더에 분수주가 들어가면 잡는가 (토스는 국내 분수주 미지원)",
        "why": "8/1 실사고 — AAPL 25% 트림을 지정가로 적었는데 0.2556주라 분수주 지정가가 원천 불가였다. "
               "국내는 분수주 자체가 미지원이라 1주 미만 계획은 성립조차 안 한다(6/21 교정)",
        "pattern": r"실행불가|분수주|정수 1주",
        "violate": {
            "data/app/tasks.json": json.dumps(
                {"orders": [{"ticker": "005930.KS", "shares": 0.4,
                             "action": "매수 지정가", "status": "대기"}]}, ensure_ascii=False),
            ".claude/skills/portfolio-desk/portfolio.json": json.dumps(
                # ⚠️ portfolio.json의 holdings는 **지역별 dict**다({"kr":[...], "us":[...]}).
                #   리스트로 줬다가 AttributeError로 죽어 "못 잡는다"로 오판했다 — 픽스처 문제였다.
                {"holdings": {"kr": [{"ticker": "005930.KS", "shares": 1}]}}, ensure_ascii=False),
        },
        "clean": {
            "data/app/tasks.json": json.dumps(
                {"orders": [{"ticker": "005930.KS", "shares": 1,
                             "action": "매수 지정가", "status": "대기"}]}, ensure_ascii=False),
            ".claude/skills/portfolio-desk/portfolio.json": json.dumps(
                {"holdings": {"kr": [{"ticker": "005930.KS", "shares": 1}]}}, ensure_ascii=False),
        },
        "args": (),
    },
    {
        "name": "check_desk_output_items",
        "desc": "리스크 데스크 Return format 항목이 보고서 산출물에 없으면 잡는가",
        "why": "8/25 실사고 — 8/24 23:30에 손익비를 risk-desk에 배선했는데 17시간 뒤 돌아간 R2(v84)가 "
               "그 항목만 빠뜨렸다. 같은 Task의 --reconcile은 보고했으니 스폰은 됐다. "
               "wiring_audit은 '지시층에 텍스트가 있다'까지만 본다 — 배선→실행→**산출**의 마지막 칸이 비어 있었다",
        "pattern": r"산출 누락",
        "violate": {
            ".claude/agents/risk-desk.md": RISK_SPEC,
            "docs/reports/report_v99_2026-08-25.md": "# v99\n\n## 9. 리스크 데스크\n- 트리거 상태: D1 해금\n",
        },
        "clean": {
            ".claude/agents/risk-desk.md": RISK_SPEC,
            "docs/reports/report_v99_2026-08-25.md":
                "# v99\n\n## 9. 리스크 데스크\n- 트리거 상태: D1 해금\n- ⚖️ 손익비 1.13\n",
        },
        "args": ("docs/reports/report_v99_2026-08-25.md",),
    },
]


def _make_root(files: dict[str, str]) -> str:
    tmp = tempfile.mkdtemp(prefix="guard_selftest_")
    for rel, body in files.items():
        p = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
    return tmp


def _run_check(check_name: str, files: dict, args: tuple) -> list[str]:
    """임시 ROOT에서 check 하나를 돌리고 FAIL+WARN 메시지를 돌려준다."""
    import validate_report as V
    tmp = _make_root(files)
    old_root = V.ROOT
    old_fails, old_warns = list(V.FAILS), list(V.WARNS)
    try:
        V.ROOT = tmp
        V.FAILS.clear()
        V.WARNS.clear()
        fn = getattr(V, check_name, None)
        if fn is None:
            return ["__MISSING__"]
        try:
            fn(*args)
        except Exception as e:                     # 가드가 죽는 것도 결함이다
            return [f"__EXCEPTION__ {type(e).__name__}: {e}"]
        return list(V.FAILS) + list(V.WARNS)
    finally:
        V.ROOT = old_root
        V.FAILS.clear(); V.FAILS.extend(old_fails)
        V.WARNS.clear(); V.WARNS.extend(old_warns)
        shutil.rmtree(tmp, ignore_errors=True)


def run_injection_tests() -> list[dict]:
    out = []
    for t in INJECTION_TESTS:
        rx = re.compile(t["pattern"])
        got_v = _run_check(t["name"], t["violate"], t["args"])
        got_c = _run_check(t["name"], t["clean"], t["args"])
        if got_v == ["__MISSING__"]:
            out.append({"guard": t["name"], "ok": None, "desc": t["desc"],
                        "msg": "validate_report에 해당 check 없음(이름 변경?)"})
            continue
        caught = any(rx.search(m) for m in got_v)
        false_pos = any(rx.search(m) for m in got_c)
        ok = caught and not false_pos
        msg = ""
        if not caught:
            msg = "위반을 심었는데 못 잡는다 ← 가드가 무력하다"
        elif false_pos:
            msg = f"정상 데이터를 위반으로 오판: {[m for m in got_c if rx.search(m)][:1]}"
        out.append({"guard": t["name"], "ok": ok, "desc": t["desc"], "why": t["why"],
                    "caught": caught, "false_positive": false_pos, "msg": msg})
    return out


# ── ③ 커버리지 — 음성 테스트가 없는 가드를 드러낸다 ──────────────────────
def coverage() -> dict:
    try:
        import validate_report as V
    except Exception:
        return {"checks": [], "covered": [], "uncovered": []}
    checks = sorted(n for n in dir(V) if n.startswith("check_") and callable(getattr(V, n)))
    covered = {t["name"] for t in INJECTION_TESTS}
    return {"checks": checks, "covered": sorted(covered),
            "uncovered": [c for c in checks if c not in covered]}


def selftest() -> int:
    """이 메타 가드 자신을 검증한다 — **무력한 가드를 실제로 ❌로 잡는가.**

    ★ 이 단계가 없으면 `guard_selftest` 자신이 정확히 그 세 번째 사례가 된다
      ("돌지만 아무것도 못 잡는 도구"). 무력화 두 종류를 주입한다:
        ① **아무것도 안 잡는 가드**(no-op) → ❌ 여야 한다
        ② **무조건 잡는 가드**(항상 fail) → 정상 데이터에서도 걸리므로 ❌ 여야 한다
      ②가 중요하다 — 무조건 잡는 가드는 무조건 통과하는 가드만큼 쓸모없는데,
      '위반을 잡았는가'만 보면 통과해버린다.
    """
    import validate_report as V
    print("guard_selftest 음성 테스트 — 무력한 가드를 ❌로 잡아내면 성공")
    print("=" * 78)
    ok = True

    target_t = INJECTION_TESTS[0]
    target = target_t["name"]
    orig = getattr(V, target)

    # ★[9/1 수정] 주입 메시지를 **하드코딩하지 않는다.**
    #   舊 코드는 `V.fail("7,500 안전핀 위반 (무조건)")`을 심고 그게 오탐으로 잡히길 기대했다 —
    #   INJECTION_TESTS[0]이 check_repealed_rules(패턴에 '7,500' 포함)였을 때만 성립하는 가정이다.
    #   그 뒤 목록 앞에 다른 테스트가 들어가 [0]이 check_canonical_facts로 바뀌자
    #   주입 메시지가 그 가드의 패턴('수치 정본 불일치')과 안 맞아 false_positive=False가 됐고,
    #   **테스트 ②가 계속 ❌인 채로 방치됐다**(게이트는 --selftest를 안 부르므로 아무도 못 봤다).
    #   ⇒ 대상 가드가 실제로 내는 위반 메시지를 뽑아 쓴다. 목록이 바뀌어도 따라간다.
    _rx = re.compile(target_t["pattern"])
    _real = [m for m in _run_check(target, target_t["violate"], target_t["args"])
             if _rx.search(m)]
    if not _real:
        print(f"  ❌ 픽스처 결함 — {target}의 violate가 패턴에 맞는 메시지를 안 낸다. "
              f"이 상태로는 메타 검증이 성립하지 않는다")
        return 1
    _always_msg = _real[0]

    # ① no-op — 위반을 심어도 아무 말이 없다
    setattr(V, target, lambda *a, **k: None)
    r = [x for x in run_injection_tests() if x["guard"] == target][0]
    caught_noop = r["ok"] is False and not r["caught"]
    print(f"  {'✅' if caught_noop else '❌'} 아무것도 안 잡는 가드(no-op)를 적발"
          + ("" if caught_noop else " ← 메타 가드가 무력하다"))
    ok = ok and caught_noop

    # ② 무조건 fail — 정상 데이터에서도 걸린다
    setattr(V, target, lambda *a, **k: V.fail(_always_msg))
    r = [x for x in run_injection_tests() if x["guard"] == target][0]
    caught_always = r["ok"] is False and r["false_positive"]
    print(f"  {'✅' if caught_always else '❌'} 무조건 잡는 가드(오탐)를 적발"
          + ("" if caught_always else " ← 위반 적발만 보고 오탐을 놓쳤다"))
    ok = ok and caught_always

    # ③ 원복 후 정상 통과 확인
    setattr(V, target, orig)
    r = [x for x in run_injection_tests() if x["guard"] == target][0]
    print(f"  {'✅' if r['ok'] else '❌'} 원복 후 정상 통과")
    ok = ok and bool(r["ok"])

    # ④ 가드가 예외로 죽으면 그것도 결함으로 잡는가
    setattr(V, target, lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = [x for x in run_injection_tests() if x["guard"] == target][0]
    caught_exc = r["ok"] is False
    print(f"  {'✅' if caught_exc else '❌'} 예외로 죽는 가드를 적발")
    ok = ok and caught_exc
    setattr(V, target, orig)

    print("-" * 78)
    print("✅ 통과 — 메타 가드가 실제로 작동한다" if ok else "❌ 실패 — guard_selftest를 고칠 것")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="가드가 실제로 위반을 잡는지 검증하는 메타 가드")
    ap.add_argument("--coverage", action="store_true", help="커버리지 표만 출력")
    ap.add_argument("--selftest", action="store_true",
                    help="이 메타 가드 자신을 검증(무력한 가드를 잡는지)")
    ap.add_argument("--json", action="store_true", help="기계 출력")
    ap.add_argument("-q", "--quiet", action="store_true",
                    help="통과한 가드는 숨기고 실패·미실행·커버리지만 (규약: docs/dev_workflow.md §1c)")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    cov = coverage()
    if a.coverage and not a.json:
        print("가드 음성테스트 커버리지 — validate_report.check_*")
        print("=" * 78)
        for c in cov["checks"]:
            mark = "✅ 음성테스트 있음" if c in cov["covered"] else "· 미등록"
            print(f"  {mark:<20} {c}")
        print("-" * 78)
        print(f"  {len(cov['covered'])}/{len(cov['checks'])} 등록 — **미등록 {len(cov['uncovered'])}개가 결핍 목록이다**")
        print("  ⚠️ 커버리지를 성취로 읽지 말 것. 새 사고가 나면 그 사례를 INJECTION_TESTS에 추가한다.")
        return 0

    subs = run_subprocess_tests()
    injs = run_injection_tests()
    rows = subs + injs
    fails = [r for r in rows if r["ok"] is False]

    if a.json:
        print(json.dumps({"results": rows, "coverage": cov,
                          "failed": len(fails)}, ensure_ascii=False, indent=1))
        return 1 if fails else 0

    print("가드 자가검증 — 위반을 심고 **실제로 잡는지** 본다")
    print("=" * 78)
    # `--quiet` 규약 [9/1]: 통과한 가드만 숨긴다.
    #   ⚠️ ok is None = **실행되지 않은 가드**다. quiet에서도 반드시 보인다 —
    #      안 돈 가드를 통과한 가드처럼 보이게 하는 순간 이 도구의 존재 이유가 무너진다.
    _n_skip = sum(1 for r in rows if r["ok"] is None)
    if a.quiet:
        print(f"  가드 {len(rows)}개 — 실패 {len(fails)} · 미실행 {_n_skip} · "
              f"통과 {len(rows) - len(fails) - _n_skip}(숨김)")
        for r in rows:
            if r["ok"] is True:
                continue
            icon = "·" if r["ok"] is None else "❌"
            print(f"  {icon} {r['guard']} — {r['desc']}"
                  + ("  ← 실행 안 됨" if r["ok"] is None else ""))
            if r["msg"]:
                print(f"       └ {r['msg']}")
    else:
        print("\n■ 자체 음성 테스트를 가진 가드")
        for r in subs:
            icon = "·" if r["ok"] is None else ("✅" if r["ok"] else "❌")
            print(f"  {icon} {r['guard']}")
            print(f"       {r['desc']}")
            if r["msg"]:
                print(f"       └ {r['msg']}")
        print("\n■ 주입 테스트 (임시 ROOT에 위반을 심는다)")
        for r in injs:
            icon = "·" if r["ok"] is None else ("✅" if r["ok"] else "❌")
            print(f"  {icon} {r['guard']} — {r['desc']}")
            if r.get("why"):
                print(f"       근거: {r['why']}")
            if r.get("ok") is not None:
                print(f"       위반 적발 {'O' if r['caught'] else 'X'} · 정상 오탐 "
                      f"{'있음' if r['false_positive'] else '없음'}")
            if r["msg"]:
                print(f"       └ {r['msg']}")

    print("\n" + "-" * 78)
    print(f"  커버리지: validate_report check {len(cov['checks'])}개 중 "
          f"주입 테스트 등록 **{len(cov['covered'])}개** · 미등록 {len(cov['uncovered'])}개")
    print("  ⚠️ 미등록이 훨씬 많다 — 이 숫자는 성취가 아니라 **결핍 목록**이다"
          " (`--coverage`로 전체 목록).")
    if fails:
        print(f"\n❌ 무력한 가드 {len(fails)}건 — 가드를 고칠 것(초록불이 거짓이 된다)")
        return 1
    print("\n✅ 등록된 가드 전부 실제로 위반을 잡는다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
