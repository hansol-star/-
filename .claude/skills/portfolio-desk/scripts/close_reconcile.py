#!/usr/bin/env python3
"""close_reconcile.py — 국내 마감 대사 자동화 (외인 수급 확정 · 코스피 낙폭 확정)

★[2026-10-12 신설 — 정훈 "이런 걸 계속 자동으로 요청하게 말고 너가 완성시켜봐"]

왜 만들었나:
  장중에 쓴 보고서는 수급·낙폭을 '잠정'으로 적고 "마감 후 대사"를 할 일로 남겼다(t1012-1·t1012-2 유형).
  그 할 일은 사람이 "대사해줘"라고 해야만 돌았고, flows.json엔 **'잠정 — KRX 확정 대사 필요'가
  9/22 이후 7거래일째 그대로** 쌓여 있었다. 요청해야 도는 대사는 대사가 아니다.

하는 일 (토큰 0 · 네트워크 = 네이버·Yahoo 무키 + ⑥만 토스 Open API 조회 전용 · 토스 키가 없으면 ⑥은 건너뛰고 메모로 남긴다):
  ① 코스피·코스닥 당일 투자자별 순매수(억원)를 받아 flows.json 당일 행을 upsert
     · 1차(16:10) = '잠정' / 2차(20:10, 애프터마켓 종료 뒤) = 1차와 대조해 '확정'
     · 사람이 매체 교차로 적은 행([마감 확정 — …매체…])은 **덮지 않고** 수치만 대조해 차이를 남긴다
  ② ^KS11·^KQ11 일봉 캐시 갱신 → 종가·고점대비 낙폭 확정
  ③ 외인 연속 순매도/순매수 일수 재계산
  ④ data/app/close_recon.json에 결과 기록(보고서·브리핑이 읽는 정본) · 시장 누적(market_flows.jsonl) 갱신
  ⑤ --commit이면 자기 파일만 커밋·푸시(작업트리의 다른 변경은 건드리지 않는다)
  ⑥ [10/13] 국내 보유·워치 일봉 재수집 + 최근 7거래일 캐시를 토스 1분봉(KRX 정규장 종가)과 대조
     · 읽기 전용 — 고치지 않는다. 불일치·**감사를 못 돌린 것**·본 게 거의 없는 것 모두 notes로 올라가 WARN이 된다
     · ①~④를 저장한 뒤에 돈다 — 토스가 늦어 스케줄러 제한시간(10분)에 걸려도 수급·낙폭 대사는 남는다
  ⑦ [10/19] 국내 개별종목 밖 캐시(美 종목·지수·매크로)의 최근 30일을 Yahoo 일봉 종가와 대조(읽기 전용)
     · ^VIX·MU·ORCL 등 73행에 장중값이 굳어 있었다(7/21~8/5 · 개정창 upsert 8/13 이전) — 아무도 다시 안 봤다
     · 개정창(7일) 밖의 불일치 = 굳은 값 → 메모. 창 안은 다음 갱신이 덮으니 건수만 남긴다. 고치는 건 --fix(수동)

★[10/19] 외인 수급은 **KRX 정규장 기준**으로 판정한다(게이트②).
  9/14 애프터마켓(16:00~20:00) 뒤 네이버 시장 수급은 마감 뒤에도 계속 바뀐다 — 10/19 16:10 -323억 → 20:10 +947억.
  · 16:40 전 캡처 = `regular`(정규장 근사 — 애프터 시작 뒤 수 분이 섞일 수 있다 · 10/19 KRX 마감 보도 -364억과 41억 차)
  · 그 뒤 캡처 = `integrated`(정규장+애프터 통합 · 19:55 뒤면 최종)
  · flows.json 행: 대표값(foreign·inst·indiv) = 정규장 값(없으면 통합값) · `basis`가 어느 쪽인지 적는다 · 두 캡처는 하위 필드로 남긴다
  · 정규장 캡처가 없는 날 = 게이트② '판정 보류'(flow_trend.gate_value — |외인| ≥ 3,000억이면 부호만 인정)
  · '확정' = 정규장 캡처 + 애프터 종료 뒤 통합 캡처가 둘 다 있다. 두 값이 다른 건 애프터마켓이지 불안정이 아니다

안 하는 일:
  · KRX 원본 대조 — KRX 정보데이터시스템은 세션 가드로 막혀 있다(8/31 실측). 그래서 '확정'의 정의는
    **"마감 후 두 시점의 네이버 값이 일치"**다. KRX 원본과 같다는 보증이 아니다 → 출처에 그렇게 적는다.
  · 룰 판정·주문 — 측정 전용.

사용:
  close_reconcile.py                 # 대사만(파일 갱신)
  close_reconcile.py --commit        # + 자기 파일 커밋·푸시 (스케줄러용)
  close_reconcile.py --status        # 마지막 결과 한 줄
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, *([os.pardir] * 4)))
APP = os.path.join(ROOT, "data", "app")
HIST = os.path.join(ROOT, "data", "history")
FLOWS = os.path.join(APP, "flows.json")
RECON = os.path.join(APP, "close_recon.json")
KST = dt.timezone(dt.timedelta(hours=9))
AUTO_TAG = "[자동 대사"            # 이 접두로 시작하는 note만 이 스크립트가 덮어쓴다
STABLE_PCT = 1.0                   # 수기 확정값과 정규장 캡처의 차이가 이 %(또는 50억) 이내면 '일치'
REGULAR_UNTIL = "16:40"            # 이 시각(HH:MM) 전 캡처 = 정규장 근사 · 이후 = 정규장+애프터마켓 통합
FINAL_FROM = "19:55"               # 애프터마켓(~20:00)이 끝난 뒤 = 그날 통합 최종
YAUDIT_DAYS = 30                   # Yahoo 감사 창(일) — 장중값 고착은 개정창(7일) 밖에서 난다
YAUDIT_MAX_SEC = 120
REVISE_DAYS = 7                    # = history_backfill.REVISE_WINDOW_DAYS — 이 안의 불일치는 다음 갱신이 덮는다
OWN_FILES = ["data/app/flows.json", "data/app/close_recon.json",
             "data/history/market_flows.jsonl", "data/history/_KS11.csv",
             "data/history/_KQ11.csv", "data/history/_manifest.json"]

# 스케줄러 JD-close-reconcile의 ExecutionTimeLimit = 10분. 하위 작업 제한시간을 그냥 더하면 120+420+300 = 840초라
# 느린 날엔 커밋 전에 프로세스가 죽는다 → 전체 예산을 두고 남은 시간 안에서만 돌린다.
BUDGET_SEC = 540
AUDIT_MAX_SEC = 150
REFRESH_FAIL = "일봉 갱신"          # refresh_index()가 만드는 실패 메모의 표지(실패·시간 초과 공통)
MISMATCH_NOTES = 6                 # 불일치를 메모로 올리는 최대 건수 — 넘으면 총건수를 한 줄 더 적는다
AUDIT_PENDING = ("일봉 캐시 ↔ 토스 감사 미완 — 대사를 저장한 뒤 감사가 끝나기 전에 실행이 끊겼다"
                 "(PC 절전·종료·제한시간) · `history_backfill.py --audit 7`로 직접 확인")
YAUDIT_PENDING = ("일봉 캐시 ↔ Yahoo 감사 미완 — 토스 감사 뒤 Yahoo 감사가 끝나기 전에 실행이 끊겼다"
                  f"(PC 절전·종료·제한시간) · `history_backfill.py --audit-yahoo {YAUDIT_DAYS}`로 직접 확인")
_T0 = time.monotonic()

sys.path.insert(0, _HERE)


def _left(reserve: float = 0) -> float:
    """남은 시간 예산(초). reserve = 뒤에 올 작업 몫으로 남겨둘 시간."""
    return max(0.0, BUDGET_SEC - (time.monotonic() - _T0) - reserve)


def now() -> dt.datetime:
    return dt.datetime.now(KST)


def _load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return d


def _dump(p, o):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(o, f, ensure_ascii=False, indent=1)
        f.write("\n")


def index_series(sym_file: str) -> list[tuple[str, float]]:
    out = []
    try:
        with open(os.path.join(HIST, sym_file), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    out.append((r["date"], float(r["close"])))
                except (KeyError, ValueError):
                    continue
    except OSError:
        pass
    return out


def kr_symbols() -> list[str]:
    """보유·워치 + **채점 꼬리가 남은 퇴출 워치**의 국내 종목(.KS/.KQ). 유니버스 정본 = market_data.
    퇴출 워치(RETIRED_WATCH)를 빼면 그 종목의 장중값이 굳는다 — 워치 콜 채점이 그 캐시를 읽는다(10/3 교훈)."""
    try:
        import market_data as md
        seen, out = set(), []
        pool = [md.GROUPS.get(g, []) for g in ("holdings", "watchlist")] + [getattr(md, "RETIRED_WATCH", [])]
        for grp in pool:
            for _, sym in grp:
                if sym.upper().endswith((".KS", ".KQ")) and sym not in seen:
                    seen.add(sym)
                    out.append(sym)
        return out
    except Exception:  # noqa: BLE001 — 종목 목록을 못 읽어도 지수 대사는 돈다
        return []


def own_files() -> list[str]:
    return OWN_FILES + [f"data/history/{s}.csv" for s in kr_symbols()] + ["data/history/_gapfill.jsonl"]


def _child_env() -> dict:
    """하위 파이썬의 출력 인코딩을 UTF-8로 못박는다 — 환경에 따라 cp949로 나오면 capture가 깨져 stdout이 None이 된다."""
    return {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def refresh_index() -> list[str]:
    """지수 + 국내 보유·워치 일봉을 마감 뒤 다시 받는다 → **실패 메모 목록**(정상이면 빈 리스트).

    ★[10/14 검토] 하위 프로세스의 종료코드를 안 봤다 — history_backfill이 예외로 죽어도(예: 손으로 고친 원장이
      깨져서) 여기선 아무 일 없던 것처럼 넘어갔고 종목 캐시 갱신만 조용히 멈췄다. 실패는 메모로 올린다.

    ★[2026-10-13] 지수만 갱신하고 있어 **종목 행은 장중에 쓴 값이 그대로 남았다**(10/12 삼성 257,000 ↔
      종가 250,500). 장중 보고서 세션이 쓴 당일 행을 같은 날 마감 뒤 확정 종가로 바꾸는 주체가 없었다.
      history_backfill의 개정창 upsert + 결측 봉 보정이 여기서 매일 16:10·20:10에 돈다.
    """
    hb = os.path.join(_HERE, "history_backfill.py")
    # 지수가 먼저다 — 낙폭·수급 대사는 지수만 있으면 돈다. 종목은 따로 돌리고, 늦거나 죽어도 대사를 막지 않는다
    # (한 호출로 묶으면 종목 20여 개 중 하나가 걸려 타임아웃이 날 때 지수 대사까지 같이 죽는다).
    notes: list[str] = []

    def run(what: str, symbols: str, timeout: float) -> None:
        try:
            r = subprocess.run([sys.executable, hb, "--symbols", symbols, "--pace", "0.6"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               env=_child_env(), timeout=timeout)
        except subprocess.TimeoutExpired:
            notes.append(f"{what} 일봉 갱신 시간 초과({timeout:.0f}초) — 캐시가 어제 값일 수 있다(다음 실행에서 다시 받는다)")
            return
        if r.returncode != 0:
            last = ((r.stderr or "").strip().splitlines() or ["(출력 없음)"])[-1][:160]
            notes.append(f"{what} 일봉 갱신 실패(종료코드 {r.returncode}) — {last} · `history_backfill.py --symbols …`로 재현")

    run("지수", "^KS11,^KQ11", 120)
    syms = kr_symbols()
    if syms:
        # 뒤에 올 수급 대사·감사·커밋 몫(180초)을 남기고 돌린다. 늦거나 죽어도 지수 대사는 계속한다.
        run("종목", ",".join(syms), max(30.0, min(420.0, _left(reserve=180))))
    for n in notes:
        print("  ⚠️ " + n)
    return notes


def audit_history(days: int = 7, timeout: float = AUDIT_MAX_SEC) -> dict:
    """갱신한 일봉 캐시를 **토스 KRX 종가와 대조**한다(읽기 전용) → history_backfill.audit_kr 결과.

    ★[2026-10-13 정훈 "토스로 보면 되는 거 아닌가"] 결측 봉 보정은 Yahoo가 봉을 비울 때만 돈다.
      Yahoo가 준 값이 틀렸거나 개정창이 지난 장중값은 이 대조가 아니면 아무도 안 본다.
      고치지는 않는다 — 결과는 attach_audit이 close_recon.json 메모로 올려 validate_report가 WARN으로 띄운다.
    **항상 dict를 돌려준다** — 못 돌렸으면 {"error": 이유}. None으로 뭉개면 호출자가 '불일치 없음'과 구별하지 못한다
    (첫 판이 그랬다: 시간 초과·출력 파싱 실패가 아무 흔적 없이 사라졌다).
    """
    if timeout < 20:
        return {"error": "시간 예산 부족 — 감사 생략(일봉 갱신이 오래 걸렸다)"}
    try:
        r = subprocess.run([sys.executable, os.path.join(_HERE, "history_backfill.py"),
                            "--audit", str(days), "--json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=_child_env(), timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": f"시간 초과({timeout:.0f}초) — 토스 응답 지연"}
    except OSError as e:
        return {"error": f"실행 실패({type(e).__name__})"}
    try:
        res = json.loads(r.stdout or "")
    except ValueError:
        return {"error": f"출력 파싱 실패(종료코드 {r.returncode})"}
    return res if isinstance(res, dict) else {"error": "출력 형식 이상(dict 아님)"}


def attach_audit(out: dict, audit: dict) -> None:
    """감사 결과를 대사 기록에 붙인다. **못 본 것도 메모로 올린다** — 빠뜨리면 '불일치 없음'으로 읽힌다.

    메모가 되는 것(= check_close_recon WARN): ① 불일치 ② 감사를 못 돌림(키 없음 · 토큰 발급 실패 · 시간 초과 · 파싱 실패)
      ③ 돌았는데 한 건도 대조 못 함 ④ 미확인이 전체의 20% 이상(토큰이 중간에 죽거나 서명이 바뀐 것 — 평소 0건이다)
      ⑤ 보정 원장(_gapfill.jsonl)에 못 읽은 줄이 있음(cp949·UTF-16 재저장 — 감사가 고친 값의 고정이 풀린다).
    """
    ha = {k: audit.get(k) for k in ("days", "checked", "unresolved", "adjusted", "error", "no_key", "ledger_bad")}
    ha["mismatch"] = (audit.get("mismatch") or [])[:20]
    out["history_audit"] = ha
    notes = out.setdefault("notes", [])
    if audit.get("ledger_bad"):
        notes.append(f"보정 원장(_gapfill.jsonl)에 못 읽은 줄 {audit['ledger_bad']}개 — UTF-8로 저장됐는지 확인"
                     "(감사가 고친 값의 고정이 풀렸을 수 있다)")
    if audit.get("error"):
        notes.append(f"일봉 캐시 ↔ 토스 감사 미실행 — {audit['error']}")
        return
    checked, unres = audit.get("checked") or 0, audit.get("unresolved") or 0
    if not checked:
        notes.append(f"일봉 캐시 ↔ 토스 감사가 한 건도 대조하지 못했다(미확인 {unres}건) — '불일치 없음'이 아니다 · 토스 응답 확인")
    elif unres * 5 >= checked + unres:
        notes.append(f"일봉 캐시 ↔ 토스 감사: 미확인 {unres}건 / 대조 {checked}건 — 못 본 날이 많다"
                     "(토큰 만료·응답 지연·단일가 서명 변경 확인 · `history_backfill.py --audit 7`)")
    mm = audit.get("mismatch") or []
    for m in mm[:MISMATCH_NOTES]:
        notes.append(f"일봉 캐시 ≠ 토스 KRX 종가 — {m['symbol']} {m['date']} 캐시 {m['cached']:,.0f} ↔ "
                     f"토스 {m['toss']:,.0f}({m['pct']:+.2f}%) · `history_backfill.py --audit 7`로 확인 후 --fix(수동)")
    if len(mm) > MISMATCH_NOTES:       # 장중값이 전 종목에 굳으면 18건이 한꺼번에 난다 — 6줄만 보이고 끝이면 나머지가 없는 줄 안다
        notes.append(f"일봉 캐시 ≠ 토스 KRX 종가 — 외 {len(mm) - MISMATCH_NOTES}건(총 {len(mm)}건) · "
                     "`history_backfill.py --audit 7`로 전체 확인")


def audit_yahoo_cache(days: int = YAUDIT_DAYS, max_sec: float = YAUDIT_MAX_SEC) -> dict:
    """국내 개별종목 밖 캐시(美·지수·매크로)를 **Yahoo 일봉 종가와 대조**한다(읽기 전용) → history_backfill.audit_yahoo 결과.

    ★[2026-10-19] ^VIX 캐시의 장중값(7/30 19.38 ↔ 종가 17.09)이 정본 '저점 VIX 19.4'로 석 달을 갔고, 같은 날들에
      美 종목·지수 73행이 같이 굳어 있었다. 토스 감사(⑥)는 국내만 본다 — 나머지는 이 대조가 아니면 아무도 안 본다.
    자식에겐 --max-sec(예산 − 10초)을 넘긴다 — 시간이 모자라면 못 본 심볼을 skipped로 돌려주고 끝난다(통째로 죽지 않게).
    **항상 dict를 돌려준다** — 못 돌렸으면 {"error": 이유}(audit_history와 같은 규약).
    """
    if max_sec < 20:
        return {"error": "시간 예산 부족 — Yahoo 감사 생략(앞 단계가 오래 걸렸다)"}
    try:
        r = subprocess.run([sys.executable, os.path.join(_HERE, "history_backfill.py"),
                            "--audit-yahoo", str(days), "--json", "--pace", "0.3",
                            "--max-sec", str(int(max_sec - 10))],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=_child_env(), timeout=max_sec)
    except subprocess.TimeoutExpired:
        return {"error": f"시간 초과({max_sec:.0f}초) — Yahoo 응답 지연"}
    except OSError as e:
        return {"error": f"실행 실패({type(e).__name__})"}
    try:
        res = json.loads(r.stdout or "")
    except ValueError:
        return {"error": f"출력 파싱 실패(종료코드 {r.returncode})"}
    return res if isinstance(res, dict) else {"error": "출력 형식 이상(dict 아님)"}


def _px(v) -> str:
    return "?" if v is None else f"{v:,.2f}"


def attach_yahoo_audit(out: dict, res: dict, today: str | None = None) -> None:
    """Yahoo 감사 결과를 대사 기록에 붙인다. **못 본 것도 메모로 올린다**(attach_audit과 같은 규약).

    메모가 되는 것(= check_close_recon WARN): ① 개정창(7일) 밖 불일치 = 굳은 값 ② 과거 시계열 재조정(--refresh 필요)
      ③ 개정창 밖 구멍·캐시에만 있는 날짜 ④ 감사를 못 돌림 ⑤ 한 건도 대조 못 함 ⑥ 응답 없는 심볼 ⑦ 시간 예산으로 못 본 심볼.
    개정창 안 불일치는 메모가 아니다 — 다음 증분 갱신(개정창 upsert)이 덮는다. 7일을 넘기면 ①로 올라온다.
    """
    today = today or out.get("date") or now().strftime("%Y-%m-%d")
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=REVISE_DAYS)).isoformat()
    mm = res.get("mismatch") or []
    stuck = [m for m in mm if m.get("date", "") < cutoff]
    old = lambda xs: [x for x in xs or [] if x.get("date", "") < cutoff]          # noqa: E731
    miss, extra = old(res.get("missing")), old(res.get("extra"))
    ya = {k: res.get(k) for k in ("days", "symbols", "checked", "pending", "unverifiable", "error")}
    ya.update({"stuck": stuck[:20], "recent_mismatch": len(mm) - len(stuck), "rescaled": res.get("rescaled") or [],
               "missing_old": len(miss), "extra_old": len(extra), "errors": res.get("errors") or [],
               "skipped": len(res.get("skipped") or [])})
    out["yahoo_audit"] = ya
    notes = out.setdefault("notes", [])
    days = res.get("days") or YAUDIT_DAYS
    if res.get("error"):
        notes.append(f"일봉 캐시 ↔ Yahoo 감사 미실행 — {res['error']}")
        return
    if not res.get("checked"):
        notes.append("일봉 캐시 ↔ Yahoo 감사가 한 건도 대조하지 못했다 — '불일치 없음'이 아니다 · Yahoo 응답 확인")
    for m in stuck[:MISMATCH_NOTES]:
        notes.append(f"일봉 캐시 ≠ Yahoo 종가(개정창 밖 = 굳은 값) — {m['symbol']} {m['date']} 캐시 {_px(m.get('cached'))} ↔ "
                     f"Yahoo {_px(m.get('yahoo'))}({(m.get('pct') or 0):+.2f}%) · "
                     f"`history_backfill.py --audit-yahoo {days}`로 확인 후 --fix(수동)")
    if len(stuck) > MISMATCH_NOTES:
        notes.append(f"일봉 캐시 ≠ Yahoo 종가 — 외 {len(stuck) - MISMATCH_NOTES}건(총 {len(stuck)}건) · "
                     f"`history_backfill.py --audit-yahoo {days}`로 전체 확인")
    for r in ya["rescaled"]:
        notes.append(f"{r.get('symbol')} 캐시 과거 구간이 Yahoo와 배율 {r.get('ratio')}로 어긋남({r.get('from')}~{r.get('to')} "
                     f"{r.get('n')}일) — Yahoo 소급 재조정(분할·연속선물 재기준) · "
                     f"`history_backfill.py --refresh --symbols {r.get('symbol')}`(수동)")
    if miss or extra:
        notes.append(f"일봉 캐시 날짜 불일치(개정창 밖) — 캐시 구멍 {len(miss)}건 · 캐시에만 있는 날짜 {len(extra)}건 "
                     f"(예: {', '.join(x['symbol'] + ' ' + x['date'] for x in (miss + extra)[:3])}) · "
                     f"`history_backfill.py --audit-yahoo {days}`로 확인")
    if ya["errors"]:
        notes.append(f"Yahoo 감사: {len(ya['errors'])}심볼 응답 없음({', '.join(ya['errors'][:5])}) — 못 본 것이지 일치가 아니다")
    if ya["skipped"]:
        notes.append(f"Yahoo 감사: 시간 예산으로 {ya['skipped']}심볼 미감사 — 다음 실행에서 본다")


def carry_notes(o: dict) -> list[str]:
    """대사를 못 한 실행(휴장 판정·수급 미수신)의 **일봉 갱신 실패** 메모를 기존 기록에 덧붙인다 → 덧붙인 메모.

    ★[10/14 3차 검토] 지수 갱신이 죽으면 ^KS11에 오늘 봉이 없어 '휴장이거나 마감 전'으로 끝나는데, 그 실행은 기록을
      안 바꾸므로 진짜 원인(갱신 실패)이 화면에만 찍히고 사라졌다. 검증기는 하루 늦게 'PC 전원·스케줄러 확인'이라는
      틀린 원인을 낸다. 기존 대사 값은 그대로 두고 메모만 얹는다(같은 문장은 최신 실행 것 하나만 남긴다).
    휴장·마감 전 안내 자체는 옮기지 않는다 — 공휴일마다 뜨는 정상 메모다.
    """
    fails = [n for n in o.get("notes") or [] if REFRESH_FAIL in n]
    rec = _load(RECON)
    if not fails or not isinstance(rec, dict):
        return []
    kept = [n for n in rec.get("notes") or [] if not any(n.endswith(f) for f in fails)]
    add = [f"[{o.get('run_at')} 실행 · 대사 못 함({o.get('status')})] {f}" for f in fails]
    rec["notes"] = kept + add
    _dump(RECON, rec)
    return add


def streak(series: list[dict]) -> dict:
    """외인 연속 순매도/순매수 — **게이트② 기준(정규장) 값**으로 센다(flow_trend.compute_trend · gate_value).

    null은 끊지 않고 건너뛴다(미확정일이 연속을 지우지 않게 — 舊 규칙 유지). 기준 미상 행에서 멈추면 하한(lower_bound).
    최신 행이 기준 미상이면 side = '보류'(연속을 세지 않는다).
    """
    import flow_trend as FT
    t = FT.compute_trend(series)
    if t.get("error"):
        return {"days": 0, "side": "?", "cum_eok": 0, "lower_bound": False, "gate2": None, "basis": None}
    g = t["gate2"]
    if t["direction"] == "판정 보류":
        return {"days": 0, "side": "보류", "cum_eok": 0, "lower_bound": True, "gate2": None,
                "basis": "hold", "reason": g.get("reason")}
    n = t["streak"]
    vals = [v for v, k in (FT.gate_value(s) for s in series) if v is not None]
    return {"days": n, "side": t["direction"][1:], "cum_eok": sum(vals[-n:]) if n else 0,
            "lower_bound": t["streak_lower_bound"], "gate2": g["met"], "basis": t["basis"], "reason": g.get("reason")}


def _phase(at: str) -> str:
    """캡처 시각(HH:MM) → regular(정규장 근사) | integrated(정규장+애프터마켓 통합)."""
    return "regular" if at < REGULAR_UNTIL else "integrated"


def _cap(m: dict, at: str) -> dict:
    """네이버 시장 수급 한 번의 캡처 — 값 + 시각 + 출처(어느 기준인지)."""
    c = {"foreign": m["foreign"], "inst": m["inst"], "indiv": m["indiv"], "at": at}
    if _phase(at) == "regular":
        c["src"] = f"네이버 시장수급 {at} — 정규장 근사(16:00 애프터마켓 시작 뒤 수 분이 섞일 수 있다) · KRX 원본 미대조"
    else:
        c["final"] = at >= FINAL_FROM
        c["src"] = (f"네이버 시장수급 {at} — 정규장+애프터마켓 통합"
                    + ("(애프터 종료 뒤 최종)" if c["final"] else "(애프터 진행 중 중간값)") + " · KRX 원본 미대조")
    return c


def reconcile(today: str | None = None) -> dict:
    import naver_flows as NF
    t = now()
    today = today or t.strftime("%Y-%m-%d")
    out: dict = {"date": today, "run_at": t.strftime("%Y-%m-%d %H:%M"), "status": "ok", "notes": []}

    refresh_notes = refresh_index()
    ks, kq = index_series("_KS11.csv"), index_series("_KQ11.csv")
    if not ks or ks[-1][0] != today:
        out.update({"status": "no_session",
                    "notes": refresh_notes + [f"^KS11 마지막 일봉 {ks[-1][0] if ks else '없음'} ≠ {today} — 휴장이거나 마감 전"]})
        return out
    out["notes"] = refresh_notes + out["notes"]
    close, prev = ks[-1][1], ks[-2][1]
    peak_d, peak = max(ks, key=lambda x: x[1])
    out["kospi"] = {"close": round(close, 2), "pct": round((close / prev - 1) * 100, 2),
                    "peak": round(peak, 2), "peak_date": peak_d,
                    "dd_pct": round((close / peak - 1) * 100, 2)}
    if kq and kq[-1][0] == today:
        out["kosdaq"] = {"close": round(kq[-1][1], 2), "pct": round((kq[-1][1] / kq[-2][1] - 1) * 100, 2)}

    m = NF.market("KOSPI")
    if not m or m.get("date") != today or m.get("foreign") is None:
        out["status"] = "flows_missing"
        out["notes"].append(f"네이버 시장 수급이 {today}분을 안 준다({(m or {}).get('date')}) — 다음 실행에서 재시도")
        return out
    at = t.strftime("%H:%M")
    phase = _phase(at)
    try:
        NF.append_market(basis=phase)
    except Exception:  # noqa: BLE001 — 누적 실패가 대사를 막지 않는다
        pass

    fl = _load(FLOWS, {}) or {}
    series = fl.setdefault("series", [])
    row = next((s for s in series if s.get("date") == today), None)
    prior = (_load(RECON, {}) or {})
    same = prior.get("date") == today
    cur = _cap(m, at)

    # 그날 정규장 캡처 = **가장 이른 것**(늦을수록 애프터가 더 섞인다) · 통합 캡처 = 가장 늦은 것(최종에 가깝다).
    #   대사 기록 → flows.json 행 → 舊 기록의 first(16:40 전이면 정규장) 순으로 찾는다.
    reg = (prior.get("regular") if same else None) or (row or {}).get("regular")
    if not reg and same and (prior.get("first") or {}).get("at", "99") < REGULAR_UNTIL:
        reg = prior["first"]
    integ = (prior.get("integrated") if same else None) or (row or {}).get("integrated")
    if phase == "regular":
        if not reg or str(reg.get("at", "99")) > at:
            reg = cur
    else:
        integ = cur
    final = bool(integ) and str(integ.get("at", "")) >= FINAL_FROM
    if reg and final:
        grade = "확정"
    elif reg:
        grade = "잠정(1차)"
    elif final:
        grade = "통합만(정규장 캡처 없음)"
    else:
        grade = "잠정(통합 중간값 · 정규장 캡처 없음)"
    gate, basis = (reg, "regular") if reg else (integ, "integrated")
    out.update({"first": reg or integ, "flows": gate, "regular": reg, "integrated": integ,
                "basis": basis, "grade": grade})
    if not reg:
        out["notes"].append("정규장 캡처 없음(16:10 실행 누락) — 게이트②는 이날 |외인| ≥ 3,000억일 때만 부호를 인정하고 "
                            "아니면 '판정 보류' · 매체 마감시황(정규장)으로 수기 보충하면 basis=regular로 적는다")
    if reg and final:
        out["after_market_foreign"] = integ["foreign"] - reg["foreign"]      # 애프터마켓이 옮긴 외인 값(실측 누적용)
        if (reg["foreign"] < 0) != (integ["foreign"] < 0):
            out["notes"].append(f"정규장 외인 {reg['foreign']:+,}억({reg['at']}) ↔ 통합 {integ['foreign']:+,}억({integ['at']}) "
                                "— 애프터마켓이 부호를 바꿨다 · 게이트②는 정규장 기준으로 판정")

    k = out["kospi"]
    tag = f"정규장 기준({reg['at']} 캡처)" if reg else "통합 기준 — 정규장 캡처 없음"
    auto_note = (f"{AUTO_TAG} {t.strftime('%m/%d %H:%M')} · {grade} · {tag} · 네이버 시장수급 — KRX 원본 미대조] "
                 f"코스피 {k['close']:,.2f}({k['pct']:+.2f}%) · 고점대비 {k['dd_pct']:+.1f}%"
                 + (f" · 통합({integ['at']}) 외인 {integ['foreign']:+,}억" if reg and integ else ""))
    vals = {"foreign": gate["foreign"], "inst": gate["inst"], "indiv": gate["indiv"]}
    subs = {key: v for key, v in (("regular", reg), ("integrated", integ)) if v}
    if row is None:
        series.append({"date": today, **vals, "basis": basis, **subs, "note": auto_note})
        out["flows_action"] = "added"
    elif str(row.get("note", "")).startswith(AUTO_TAG) or "잠정" in str(row.get("note", ""))[:12]:
        row.update(vals)
        row.update(subs)
        row["basis"] = basis
        row["note"] = auto_note + (" | " + row["note"] if not str(row.get("note", "")).startswith(AUTO_TAG) else "")
        out["flows_action"] = "updated"
    else:                                   # 사람이 매체 교차로 적은 행 — 대표값은 덮지 않고 캡처만 옆에 둔다
        row.update(subs)
        out["flows_action"] = "kept_manual"
        if reg:                             # 매체 마감시황은 정규장 값이다 — 통합 캡처와 비교하면 애프터를 차이로 오인한다
            d = abs((row.get("foreign") or 0) - reg["foreign"])
            if d > max(50, abs(reg["foreign"]) * STABLE_PCT / 100):
                out["notes"].append(f"수기 확정값 {row.get('foreign'):+,}억 vs 네이버 정규장 {reg['foreign']:+,}억({reg['at']}) "
                                    f"= {d:,}억 차 — 확인 필요")
        if row.get("basis") not in ("regular", "integrated", "unverified"):
            out["notes"].append(f"수기 행 {today}에 basis가 없다 — 매체 마감시황이면 \"regular\"로 적는다(없으면 게이트②가 "
                                "네이버 정규장 캡처를 읽는다)")
    series.sort(key=lambda s: s.get("date", ""))
    fl["updated"] = today
    _dump(FLOWS, fl)

    out["streak"] = streak(series)
    out["pending_nulls"] = [s["date"] for s in series[-30:] if s.get("foreign") is None]
    return out


def commit(msg: str) -> str:
    """자기 파일만 **origin/main 위에** 커밋해 올린다(git_sync).

    ★[2026-10-16] 舊 = 로컬에 커밋 → origin/main이 앞서 있으면 *"푸시 보류(다음 세션이 합친다)"*.
      클라우드 keyless 시세 갱신이 하루 두 번 origin에 커밋하므로 이 분기가 사실상 매번 탔고,
      10/15~10/16 대사 4커밋(코스피 -7.57% 신저점 · 외인 -3.7조 · 13일 연속 끝)이 로컬에만 쌓였다.
      다음 세션은 합치지 않았다 — 로컬 main이 갈라져 R2 런처 ff도 매일 exit 128로 실패했다.
    """
    import git_sync
    ex = [f for f in own_files() if os.path.exists(os.path.join(ROOT, f))]
    return git_sync.describe(git_sync.publish(ROOT, ex, msg))


def line(o: dict) -> str:
    if o.get("status") != "ok":
        return f"마감 대사 {o.get('date')}: {o.get('status')} — {'; '.join(o.get('notes') or [])}"
    k, f, s = o["kospi"], o["flows"], o["streak"]
    basis = o.get("basis")
    tag = {"regular": f"정규장 {f.get('at', '')}", "integrated": f"통합 {f.get('at', '')} · 정규장 없음"}.get(basis, "")
    integ = o.get("integrated") if basis == "regular" else None
    if s.get("side") == "보류":
        st = "외인 연속 = 판정 보류(정규장 기준 값 없음)"
    else:
        st = (f"외인 {s['days']}거래일{' 이상' if s.get('lower_bound') else ''} 연속 순{s['side']}"
              f"(누적 {s['cum_eok'] / 10000:+.2f}조)")
    g2 = {True: "충족", False: "미충족", None: "판정 보류"}.get(s.get("gate2"), "판정 보류") if "gate2" in s else None
    return (f"마감 대사 {o['date']} [{o['grade']} · {o['run_at'][-5:]}] 코스피 {k['close']:,.2f}({k['pct']:+.2f}%) · "
            f"고점({k['peak_date']} {k['peak']:,.0f}) 대비 {k['dd_pct']:+.1f}% · 외인 {f['foreign']:+,}억"
            + (f"[{tag}]" if tag else "")
            + f" (기관 {f['inst']:+,} · 개인 {f['indiv']:+,})"
            + (f" · 통합({integ['at']}) 외인 {integ['foreign']:+,}억" if integ else "")
            + f" · {st}" + (f" · 게이트② {g2}" if g2 else "")
            + ("".join(f"\n  ⚠️ {n}" for n in o.get("notes") or [])))


def main() -> int:
    ap = argparse.ArgumentParser(description="국내 마감 대사 자동화 — 외인 수급·코스피 낙폭 확정 (측정 전용)")
    ap.add_argument("--commit", action="store_true", help="자기 파일만 커밋·푸시(스케줄러용)")
    ap.add_argument("--status", action="store_true", help="마지막 결과 한 줄만")
    ap.add_argument("--date", help="대사 대상일(YYYY-MM-DD · 기본 오늘 KST)")
    ap.add_argument("--selftest", action="store_true", help="감사 결과를 메모로 올리는 배선 자가검증(오프라인)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.status:
        o = _load(RECON)
        print(line(o) if o else "마감 대사 기록 없음")
        return 0
    if now().weekday() >= 5 and not a.date:
        print("주말 — 대사 없음")
        return 0
    o = reconcile(a.date)
    if o.get("status") == "ok":
        # 감사는 본 대사를 저장한 **뒤에** 돈다 — 토스가 늦어 스케줄러 제한시간에 걸려도 수급·낙폭 대사는 디스크에 남는다.
        # 먼저 저장하는 기록엔 '감사 미완'을 적어 둔다 — 감사 도중 끊기면 그게 남고, 끝나면 결과로 바뀐다
        #   (안 적으면 끊긴 실행이 '전부 일치'한 날과 똑같이 보이고, 16:10의 감사 메모도 20:10 저장에 지워진다).
        o["notes"].append(AUDIT_PENDING)
        o["history_audit"] = {"error": "미완"}
        _dump(RECON, o)
        o["notes"].remove(AUDIT_PENDING)
        attach_audit(o, audit_history(timeout=min(AUDIT_MAX_SEC, _left(reserve=60))))
        # Yahoo 감사(⑦)는 토스 감사 뒤 — 국내 대사가 우선이다. 끊기면 그 사실이 남게 같은 방식으로 표지를 먼저 저장한다
        o["notes"].append(YAUDIT_PENDING)
        o["yahoo_audit"] = {"error": "미완"}
        _dump(RECON, o)
        o["notes"].remove(YAUDIT_PENDING)
        attach_yahoo_audit(o, audit_yahoo_cache(max_sec=min(YAUDIT_MAX_SEC, _left(reserve=40))))
        _dump(RECON, o)
    elif not os.path.exists(RECON):
        _dump(RECON, o)
    else:
        for n in carry_notes(o):
            print("  ⚠️ 기록에 남김: " + n)
    print(line(o))
    if a.commit and o.get("status") == "ok":
        s = o["streak"]
        st = "연속 판정 보류" if s.get("side") == "보류" else f"{s['days']}일 연속 순{s['side']}"
        print("  git:", commit(f"마감 대사 자동 {o['date']} [{o['grade']}] — 코스피 {o['kospi']['close']:,.2f}"
                               f"·외인 {o['flows']['foreign']:+,}억({'정규장' if o.get('basis') == 'regular' else '통합'})"
                               f"·{st}"))
    return 0


def selftest() -> int:
    """감사가 **못 본 것**을 메모로 올리는가(네트워크 없음). 조용한 실패가 '불일치 없음'으로 읽히던 자리다."""
    global _T0, RECON, FLOWS, reconcile, audit_history, audit_yahoo_cache, kr_symbols, refresh_index, index_series, now
    import contextlib
    import io
    import tempfile
    fails = []

    def ok(name, cond):
        if not cond:
            fails.append(name)
        print(f"  {'✅' if cond else '❌'} {name}")

    def notes(audit):
        o = {"notes": []}
        attach_audit(o, audit)
        return o

    clean = notes({"days": 7, "checked": 126, "unresolved": 0, "adjusted": 1, "mismatch": [], "error": None})
    ok("전부 일치 = 메모 없음 · 요약은 남는다", not clean["notes"] and clean["history_audit"]["checked"] == 126)
    mm = notes({"days": 7, "checked": 126, "unresolved": 0, "error": None, "mismatch": [
        {"symbol": "005930.KS", "date": "2026-10-12", "cached": 257000.0, "toss": 250500.0, "pct": 2.59}]})
    ok("불일치 = 메모(종목·날짜·두 값)", len(mm["notes"]) == 1 and "005930.KS" in mm["notes"][0] and "250,500" in mm["notes"][0])
    nokey = notes({"error": "토스 키 없음(TOSS_CLIENT_ID/SECRET)", "no_key": True})
    ok("키 없음 = '미실행' 메모(조용히 건너뛰지 않는다)", len(nokey["notes"]) == 1 and "미실행" in nokey["notes"][0]
       and nokey["history_audit"]["no_key"] is True)
    tok = notes({"error": "토스 토큰 발급 실패 — 키는 있다(IP 허용목록·키 만료·토스 장애 확인)", "no_key": False})
    ok("토큰 발급 실패 = '미실행' 메모 + 키 없음과 구별된다",
       "토큰 발급 실패" in tok["notes"][0] and tok["history_audit"]["no_key"] is False)
    zero = notes({"checked": 0, "unresolved": 0, "mismatch": [], "error": None})["notes"]
    ok("한 건도 대조 못 함 = '한 건도' 메모('불일치 없음'이 아니다)", len(zero) == 1 and "한 건도" in zero[0])
    allun = notes({"checked": 0, "unresolved": 126, "mismatch": [], "error": None})["notes"]
    ok("전부 미확인(0건 대조·126건 미확인) = '한 건도' 메모에 미확인 건수", len(allun) == 1 and "한 건도" in allun[0]
       and "126" in allun[0])
    ok("미확인이 20% 이상 = 메모", len(notes({"checked": 60, "unresolved": 66, "mismatch": [], "error": None})["notes"]) == 1
       and len(notes({"checked": 100, "unresolved": 25, "mismatch": [], "error": None})["notes"]) == 1)
    ok("미확인이 소수(수능일 하루 = 18/126)면 메모 없음",
       not notes({"checked": 108, "unresolved": 18, "mismatch": [], "error": None})["notes"])
    many = notes({"checked": 126, "unresolved": 0, "error": None, "mismatch": [
        {"symbol": f"00000{i}.KS", "date": "2026-10-12", "cached": 257000.0, "toss": 250500.0, "pct": 2.59}
        for i in range(8)]})["notes"]
    ok("불일치가 6건을 넘으면 '외 N건(총 M건)'을 한 줄 더 적는다", len(many) == 7 and "외 2건(총 8건)" in many[-1])
    lb = notes({"checked": 126, "unresolved": 0, "mismatch": [], "error": None, "ledger_bad": 3})
    lbe = notes({"error": "토스 키 없음(TOSS_CLIENT_ID/SECRET)", "no_key": True, "ledger_bad": 3})
    ok("보정 원장에 못 읽은 줄이 있으면 메모(감사를 못 돌린 날에도)",
       len(lb["notes"]) == 1 and "3개" in lb["notes"][0] and lb["history_audit"]["ledger_bad"] == 3
       and len(lbe["notes"]) == 2 and "못 읽은 줄" in lbe["notes"][0])

    # ★[10/19] Yahoo 감사(⑦) — 개정창 밖 불일치·재조정·구멍·못 본 것이 메모로 올라가는가
    def ynotes(res, today="2026-10-19"):
        o = {"notes": [], "date": today}
        attach_yahoo_audit(o, res, today)
        return o
    base = {"days": 30, "symbols": 55, "checked": 1100, "mismatch": [], "rescaled": [], "missing": [], "extra": [],
            "errors": [], "skipped": [], "error": None}
    yc = ynotes(base)
    ok("Yahoo 감사 전부 일치 = 메모 없음 · 요약은 남는다", not yc["notes"] and yc["yahoo_audit"]["checked"] == 1100)
    ys = ynotes(dict(base, mismatch=[{"symbol": "^VIX", "date": "2026-07-30", "cached": 19.38, "yahoo": 17.09, "pct": 13.4},
                                     {"symbol": "MU", "date": "2026-10-16", "cached": 210.0, "yahoo": 211.0, "pct": -0.47}]))
    ok("개정창 밖 불일치 = 메모(굳은 값·두 값) · 창 안은 건수만(다음 갱신이 덮는다)",
       len(ys["notes"]) == 1 and "^VIX 2026-07-30" in ys["notes"][0] and "17.09" in ys["notes"][0]
       and ys["yahoo_audit"]["recent_mismatch"] == 1)
    yr = ynotes(dict(base, rescaled=[{"symbol": "GC=F", "ratio": 0.9951, "n": 216, "run": 48,
                                      "from": "2025-09-15", "to": "2026-09-08"}]))
    ok("과거 구간 재조정 = --refresh 안내 메모", len(yr["notes"]) == 1 and "--refresh --symbols GC=F" in yr["notes"][0])
    ye = ynotes({"error": "시간 초과(120초) — Yahoo 응답 지연"})
    ok("Yahoo 감사를 못 돌림 = '미실행' 메모", len(ye["notes"]) == 1 and "미실행" in ye["notes"][0])
    ok("Yahoo 감사 0건 대조 = '한 건도' 메모", any("한 건도" in n for n in ynotes(dict(base, checked=0))["notes"]))
    yk = ynotes(dict(base, errors=["^VIX", "GC=F"], skipped=["A", "B", "C"]))
    ok("응답 없는 심볼·시간 예산으로 못 본 심볼 = 각각 메모", len(yk["notes"]) == 2 and "2심볼" in yk["notes"][0]
       and "3심볼" in yk["notes"][1])
    ym = ynotes(dict(base, missing=[{"symbol": "BTC-USD", "date": "2026-07-31", "yahoo": 1.0},
                                    {"symbol": "BTC-USD", "date": "2026-10-17", "yahoo": 1.0}]))
    ok("개정창 밖 구멍만 메모(창 안 구멍은 다음 갱신 몫)", len(ym["notes"]) == 1 and "구멍 1건" in ym["notes"][0])

    # audit_history는 실패해도 None이 아니라 이유를 돌려준다
    keep_run, keep_t0 = subprocess.run, _T0
    keep_fn = (RECON, reconcile, audit_history, kr_symbols, sys.argv)
    keep_fn2 = (FLOWS, audit_yahoo_cache, now, refresh_index, index_series)
    called = []
    try:
        # 가드가 빠지면 실제 하위 프로세스(토스 호출)가 나간다 → 먼저 '불리면 기록'으로 막고 시작한다
        subprocess.run = lambda *a, **k: called.append(a) or subprocess.CompletedProcess(a, 0, stdout="{}", stderr="")
        ok("시간 예산이 없으면 감사를 생략하고 이유를 남긴다(하위 프로세스 미호출)",
           "시간 예산" in audit_history(timeout=5)["error"] and not called)

        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="x", timeout=k.get("timeout", 0))
        subprocess.run = boom
        ok("시간 초과 = 이유가 남는다(None 아님)", "시간 초과" in audit_history(timeout=60)["error"])
        subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, 1, stdout="Traceback …", stderr="")
        ok("출력이 JSON이 아니면 = 파싱 실패(종료코드 포함)", "파싱 실패(종료코드 1)" in audit_history(timeout=60)["error"])
        subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout='{"checked": 3, "mismatch": []}', stderr="")
        ok("정상 출력은 그대로 통과", audit_history(timeout=60) == {"checked": 3, "mismatch": []})
        subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=None, stderr=None)
        ok("출력이 None(인코딩 깨짐)이어도 예외가 아니라 이유", "파싱 실패" in audit_history(timeout=60)["error"])
        cmds = []
        subprocess.run = lambda *a, **k: cmds.append(list(a[0])) or subprocess.CompletedProcess(       # noqa: E731
            a, 0, stdout='{"checked": 5}', stderr="")
        yy = audit_yahoo_cache(max_sec=100)
        ok("Yahoo 감사: 읽기 전용(--fix 없음) · 자식에 예산(--max-sec 90) 전달 · 정상 출력 통과",
           yy == {"checked": 5} and "--fix" not in cmds[-1] and cmds[-1][cmds[-1].index("--max-sec") + 1] == "90")
        n_before = len(cmds)
        ok("Yahoo 감사: 예산이 모자라면 생략(하위 프로세스 미호출)",
           "시간 예산" in audit_yahoo_cache(max_sec=5)["error"] and len(cmds) == n_before)
        subprocess.run = boom
        ok("Yahoo 감사: 시간 초과 = 이유가 남는다", "시간 초과" in audit_yahoo_cache(max_sec=60)["error"])

        # 일봉 갱신 실패(비정상 종료·시간 초과)가 메모로 돌아오는가
        kr_symbols = lambda: ["005930.KS"]                                                    # noqa: E731
        subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, 1, stdout="", stderr="Traceback\nAttributeError: x")
        with contextlib.redirect_stdout(io.StringIO()):
            bad = refresh_index()
        ok("일봉 갱신이 비정상 종료하면 지수·종목 각각 메모(종료코드·마지막 줄)",
           len(bad) == 2 and "종료코드 1" in bad[0] and "AttributeError" in bad[1])
        subprocess.run = boom
        with contextlib.redirect_stdout(io.StringIO()):
            slow = refresh_index()
        ok("일봉 갱신 시간 초과도 메모", len(slow) == 2 and all("시간 초과" in n for n in slow))
        subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="", stderr="")
        with contextlib.redirect_stdout(io.StringIO()):
            fine = refresh_index()
        ok("정상 종료면 메모 없음", fine == [])

        # 갱신 실패 메모가 대사 기록에 실리는가 — 수급 미수신 경로(지수 봉은 있음)와 휴장 경로(지수 봉 없음) 둘 다
        import naver_flows as _NF
        keep_rec = (refresh_index, index_series, _NF.market)
        try:
            refresh_index = lambda: ["종목 일봉 갱신 실패(종료코드 1)"]                         # noqa: E731
            _NF.market = lambda *a, **k: None                                                 # noqa: E731
            index_series = lambda f: [("2026-10-12", 100.0), ("2026-10-13", 95.0)]            # noqa: E731
            r_flow = reconcile("2026-10-13")
            index_series = lambda f: [("2026-10-12", 100.0)]                                  # noqa: E731
            r_none = reconcile("2026-10-13")
        finally:
            refresh_index, index_series, _NF.market = keep_rec
        ok("갱신 실패 메모가 대사 기록에 실린다(수급 미수신·휴장 경로 모두)",
           r_flow["status"] == "flows_missing" and "종료코드 1" in r_flow["notes"][0] and len(r_flow["notes"]) == 2
           and r_none["status"] == "no_session" and "종료코드 1" in r_none["notes"][0] and len(r_none["notes"]) == 2)

        # main 배선 — 본 대사 저장 → 감사 → 다시 저장. 감사 호출이나 뒤 저장이 빠지면 메모가 파일에 안 남는다
        with tempfile.TemporaryDirectory() as td:
            RECON = os.path.join(td, "close_recon.json")
            reconcile = lambda d=None: {"date": d, "run_at": d + " 20:10", "status": "ok", "notes": [],      # noqa: E731
                                        "grade": "확정", "kospi": {"close": 1.0, "pct": 0.0, "peak": 1.0,
                                                                   "peak_date": d, "dd_pct": 0.0},
                                        "flows": {"foreign": 0, "inst": 0, "indiv": 0},
                                        "streak": {"days": 0, "side": "?", "cum_eok": 0}}
            audit_history = lambda **k: {"error": "토스 토큰 발급 실패 — 키는 있다", "no_key": False}   # noqa: E731
            audit_yahoo_cache = lambda **k: dict(base)                                                 # noqa: E731
            sys.argv = ["close_reconcile.py", "--date", "2026-10-13"]
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                main()
            saved = _load(RECON, {}) or {}
            # 감사 도중 실행이 끊기면(절전·종료) '감사 미완'이 디스크에 남는다 — 끝까지 가면 그 표지는 지워진다
            done_clean = (AUDIT_PENDING not in (saved.get("notes") or []) and YAUDIT_PENDING not in (saved.get("notes") or [])
                          and "yahoo_audit" in saved)

            def cut(**k):
                raise KeyboardInterrupt
            audit_history = cut
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    main()
            except KeyboardInterrupt:
                pass
            half = _load(RECON, {}) or {}
            audit_history = lambda **k: {"days": 7, "checked": 126, "unresolved": 0, "mismatch": [], "error": None}  # noqa: E731
            audit_yahoo_cache = cut
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    main()
            except KeyboardInterrupt:
                pass
            yhalf = _load(RECON, {}) or {}
            # 대사를 못 한 실행의 갱신 실패 메모는 기존 기록에 얹힌다(대사 값은 그대로 · 휴장 안내는 안 옮긴다 · 반복해도 한 줄)
            _dump(RECON, {"date": "2026-10-12", "status": "ok", "grade": "확정", "notes": ["앞선 메모"]})
            reconcile = lambda d=None: {"date": d, "run_at": d + " 16:10", "status": "no_session", "notes": [     # noqa: E731
                "지수 일봉 갱신 실패(종료코드 1) — AttributeError: x", "^KS11 마지막 일봉 2026-10-12 ≠ 2026-10-13 — 휴장이거나 마감 전"]}
            with contextlib.redirect_stdout(io.StringIO()) as buf2:
                main()
                main()
            carried = _load(RECON, {}) or {}
            reconcile = lambda d=None: {"date": d, "run_at": d + " 16:10", "status": "no_session", "notes": [     # noqa: E731
                "^KS11 마지막 일봉 2026-10-12 ≠ 2026-10-13 — 휴장이거나 마감 전"]}
            with contextlib.redirect_stdout(io.StringIO()):
                main()
            holiday = _load(RECON, {}) or {}
        ok("main: 감사를 못 돌린 사실이 close_recon.json에 저장되고 화면에도 나온다",
           (saved.get("history_audit") or {}).get("error") and any("미실행" in n for n in saved.get("notes") or [])
           and "미실행" in buf.getvalue())
        ok("main: 감사 도중 끊기면 '감사 미완'이 기록에 남고, 끝까지 가면 지워진다",
           done_clean and AUDIT_PENDING in (half.get("notes") or []) and half.get("status") == "ok")
        cn = carried.get("notes") or []
        ok("main: 대사를 못 한 날의 일봉 갱신 실패가 기존 기록에 얹힌다(대사 값 유지 · 휴장 안내 제외 · 두 번 돌려도 한 줄)",
           carried.get("date") == "2026-10-12" and cn[0] == "앞선 메모" and len(cn) == 2 and "종료코드 1" in cn[1]
           and "no_session" in cn[1] and "기록에 남김" in buf2.getvalue())
        ok("main: 갱신 실패가 없는 휴장일은 기록을 건드리지 않는다", holiday == carried)
        ok("main: Yahoo 감사 도중 끊기면 'Yahoo 감사 미완'이 남는다(토스 감사 결과는 이미 저장)",
           YAUDIT_PENDING in (yhalf.get("notes") or []) and AUDIT_PENDING not in (yhalf.get("notes") or [])
           and (yhalf.get("history_audit") or {}).get("checked") == 126)

        # ★[10/19] 외인 수급 기준 — 16:10 = 정규장 · 20:10 = 통합. 대표값·게이트②는 정규장이다
        reconcile = keep_fn[1]
        basis_calls = []
        keep_nf = (_NF.market, _NF.append_market)
        _NF.append_market = lambda basis=None: basis_calls.append(basis) or ""                        # noqa: E731
        refresh_index = lambda: []                                                                    # noqa: E731
        index_series = lambda f: [("2026-10-16", 5668.05), ("2026-10-19", 5768.01)]                   # noqa: E731

        def run_at(hm, fv):
            global now
            h, mi = map(int, hm.split(":"))
            now = lambda: dt.datetime(2026, 10, 19, h, mi, tzinfo=KST)                                # noqa: E731
            _NF.market = lambda *a, **k: {"date": "2026-10-19", "foreign": fv, "inst": 1, "indiv": 2}  # noqa: E731
            o = reconcile("2026-10-19")
            _dump(RECON, o)                 # main()이 하는 저장 — 다음 실행이 같은 날 기록을 읽는다
            return o

        def seed(rows):
            _dump(FLOWS, {"series": [{"date": "2026-10-15", "foreign": -36537, "inst": 0, "indiv": 0, "basis": "regular"},
                                     {"date": "2026-10-16", "foreign": 3446, "inst": 0, "indiv": 0, "basis": "regular"}]
                          + rows})
            if os.path.exists(RECON):
                os.remove(RECON)

        def row19():
            return next(x for x in (_load(FLOWS) or {})["series"] if x["date"] == "2026-10-19")
        try:
            with tempfile.TemporaryDirectory() as td:
                FLOWS, RECON = os.path.join(td, "flows.json"), os.path.join(td, "close_recon.json")
                seed([])
                with contextlib.redirect_stdout(io.StringIO()):
                    r1 = run_at("16:10", -323)
                    r1b = run_at("16:25", -100)
                    r2 = run_at("20:10", 947)
                rw = row19()
                ok("16:10 = 정규장 캡처 · 잠정(1차) · 시장 누적에도 기준이 넘어간다",
                   r1["grade"] == "잠정(1차)" and r1["basis"] == "regular" and r1["flows"]["foreign"] == -323
                   and basis_calls[:1] == ["regular"])
                ok("정규장 재캡처(16:25)는 가장 이른 16:10을 지킨다", r1b["regular"]["at"] == "16:10"
                   and r1b["flows"]["foreign"] == -323)
                ok("20:10 = 통합 최종 → '확정' · 대표값은 정규장 -323억 · 통합 +947억은 옆에 · 애프터 이동 +1,270억",
                   r2["grade"] == "확정" and r2["flows"]["foreign"] == -323 and r2["integrated"]["foreign"] == 947
                   and r2["after_market_foreign"] == 1270 and basis_calls == ["regular", "regular", "integrated"])
                ok("애프터마켓이 부호를 바꾸면 메모(게이트②는 정규장 기준)", any("부호를 바꿨다" in n for n in r2["notes"]))
                ok("연속·게이트②는 정규장으로 센다(10/16 +3,446 → 10/19 -323 = 순매도 1일 · 미충족)",
                   r2["streak"]["side"] == "매도" and r2["streak"]["days"] == 1 and r2["streak"]["gate2"] is False)
                ok("flows.json 행: 대표값 = 정규장 · basis · 두 캡처 · 자동 메모",
                   rw["foreign"] == -323 and rw["basis"] == "regular" and rw["regular"]["at"] == "16:10"
                   and rw["integrated"]["at"] == "20:10" and rw["note"].startswith(AUTO_TAG) and "정규장 기준(16:10" in rw["note"])
                ln = line(dict(r2, status="ok"))
                ok("한 줄 요약에 기준·통합값·게이트②가 나온다", "정규장 16:10" in ln and "통합(20:10) 외인 +947억" in ln
                   and "게이트② 미충족" in ln)

                seed([])
                with contextlib.redirect_stdout(io.StringIO()):
                    r3 = run_at("20:10", 947)
                ok("16:10을 놓친 날 = '통합만' · 정규장 캡처 없음 메모 · 연속·게이트② 판정 보류",
                   r3["grade"] == "통합만(정규장 캡처 없음)" and r3["basis"] == "integrated"
                   and any("정규장 캡처 없음" in n for n in r3["notes"]) and r3["streak"]["side"] == "보류"
                   and "판정 보류" in line(dict(r3, status="ok")))

                seed([{"date": "2026-10-19", "foreign": -364, "inst": 1, "indiv": 2, "basis": "regular",
                       "note": "[마감 확정 — 매체 마감시황] 외인 -364억"}])
                with contextlib.redirect_stdout(io.StringIO()):
                    m1 = run_at("16:10", -323)
                    m2 = run_at("20:10", 947)
                rw = row19()
                ok("수기 행은 대표값을 덮지 않고 캡처만 옆에 둔다 · 통합값과 비교해 '차이'를 내지 않는다",
                   m2["flows_action"] == "kept_manual" and rw["foreign"] == -364 and rw["regular"]["at"] == "16:10"
                   and rw["integrated"]["foreign"] == 947 and not any("수기 확정값" in n for n in m1["notes"] + m2["notes"]))

                seed([{"date": "2026-10-19", "foreign": 947, "inst": 1, "indiv": 2,
                       "note": AUTO_TAG + " 10/19 20:10 · 잠정(값 변동) · 네이버 시장수급 — KRX 원본 미대조] 舊"}])
                _dump(RECON, {"date": "2026-10-19", "first": {"foreign": -323, "inst": 1, "indiv": 2, "at": "16:10"},
                              "flows": {"foreign": 947, "inst": 1, "indiv": 2, "at": "20:10"}})
                with contextlib.redirect_stdout(io.StringIO()):
                    lg = run_at("20:12", 950)
                ok("舊 기록(first 16:10 · regular 필드 없음)의 1차는 정규장으로 이어받는다",
                   lg["grade"] == "확정" and lg["flows"]["foreign"] == -323 and row19()["foreign"] == -323)
        finally:
            _NF.market, _NF.append_market = keep_nf
        RECON, reconcile, audit_history, kr_symbols, sys.argv = keep_fn
        _T0 = time.monotonic() - (BUDGET_SEC - 30)
        ok("예산이 30초 남으면 감사 몫(60초 예비)은 0 → 생략", _left(reserve=60) == 0
           and "시간 예산" in audit_history(timeout=min(AUDIT_MAX_SEC, _left(reserve=60)))["error"])
    finally:
        subprocess.run, _T0 = keep_run, keep_t0
        RECON, reconcile, audit_history, kr_symbols, sys.argv = keep_fn
        FLOWS, audit_yahoo_cache, now, refresh_index, index_series = keep_fn2

    print(f"\n{'✅ SELFTEST PASS' if not fails else '❌ SELFTEST FAIL: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
