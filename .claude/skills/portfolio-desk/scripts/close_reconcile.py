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
STABLE_PCT = 1.0                   # 1·2차 외인 값 차이가 이 %(또는 50억) 이내면 '일치'
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


def streak(series: list[dict]) -> tuple[int, str]:
    """끝에서부터 같은 부호가 이어진 거래일 수. null은 끊지 않고 건너뛴다(미확정일이 연속을 지우지 않게)."""
    n, sign = 0, None
    for s in reversed(series):
        v = s.get("foreign")
        if v is None:
            continue
        sg = "매도" if v < 0 else "매수"
        if sign is None:
            sign = sg
        if sg != sign:
            break
        n += 1
    return n, sign or "?"


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
    try:
        NF.append_market()
    except Exception:  # noqa: BLE001 — 누적 실패가 대사를 막지 않는다
        pass

    fl = _load(FLOWS, {}) or {}
    series = fl.setdefault("series", [])
    row = next((s for s in series if s.get("date") == today), None)
    prior = (_load(RECON, {}) or {})
    first = prior.get("first") if prior.get("date") == today else None
    cur = {"foreign": m["foreign"], "inst": m["inst"], "indiv": m["indiv"], "at": t.strftime("%H:%M")}
    after_close = t.hour >= 20 or (t.hour == 19 and t.minute >= 55)

    if first and first.get("at") != cur["at"]:
        diff = abs(cur["foreign"] - first["foreign"])
        stable = diff <= max(50, abs(first["foreign"]) * STABLE_PCT / 100)
        grade = "확정" if (stable and after_close) else ("잠정(재조회 일치)" if stable else "잠정(값 변동)")
        if not stable:
            out["notes"].append(f"외인 1차 {first['foreign']:+,}억({first['at']}) → 이번 {cur['foreign']:+,}억 = {diff:,}억 차")
    else:
        first, grade = (first or cur), "잠정(1차)"
    out["first"], out["flows"], out["grade"] = first, cur, grade

    k = out["kospi"]
    auto_note = (f"{AUTO_TAG} {t.strftime('%m/%d %H:%M')} · {grade} · 네이버 시장수급 — KRX 원본 미대조] "
                 f"코스피 {k['close']:,.2f}({k['pct']:+.2f}%) · 고점대비 {k['dd_pct']:+.1f}%")
    if row is None:
        series.append({"date": today, "foreign": cur["foreign"], "inst": cur["inst"],
                       "indiv": cur["indiv"], "note": auto_note})
        out["flows_action"] = "added"
    elif str(row.get("note", "")).startswith(AUTO_TAG) or "잠정" in str(row.get("note", ""))[:12]:
        row.update({"foreign": cur["foreign"], "inst": cur["inst"], "indiv": cur["indiv"]})
        row["note"] = auto_note + (" | " + row["note"] if not str(row.get("note", "")).startswith(AUTO_TAG) else "")
        out["flows_action"] = "updated"
    else:                                   # 사람이 매체 교차로 적은 행 — 덮지 않는다
        d = abs((row.get("foreign") or 0) - cur["foreign"])
        out["flows_action"] = "kept_manual"
        if d > max(50, abs(cur["foreign"]) * STABLE_PCT / 100):
            out["notes"].append(f"수기 확정값 {row.get('foreign'):+,}억 vs 네이버 {cur['foreign']:+,}억 = {d:,}억 차 — 확인 필요")
    series.sort(key=lambda s: s.get("date", ""))
    fl["updated"] = today
    _dump(FLOWS, fl)

    n, sg = streak(series)
    out["streak"] = {"days": n, "side": sg}
    cum = sum(s["foreign"] for s in series[-n:] if s.get("foreign") is not None) if n else 0
    out["streak"]["cum_eok"] = cum
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
    return (f"마감 대사 {o['date']} [{o['grade']} · {o['run_at'][-5:]}] 코스피 {k['close']:,.2f}({k['pct']:+.2f}%) · "
            f"고점({k['peak_date']} {k['peak']:,.0f}) 대비 {k['dd_pct']:+.1f}% · 외인 {f['foreign']:+,}억 "
            f"(기관 {f['inst']:+,} · 개인 {f['indiv']:+,}) · 외인 {s['days']}거래일 연속 순{s['side']}"
            f"(누적 {s['cum_eok'] / 10000:+.2f}조)"
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
        _dump(RECON, o)
    elif not os.path.exists(RECON):
        _dump(RECON, o)
    else:
        for n in carry_notes(o):
            print("  ⚠️ 기록에 남김: " + n)
    print(line(o))
    if a.commit and o.get("status") == "ok":
        print("  git:", commit(f"마감 대사 자동 {o['date']} [{o['grade']}] — 코스피 {o['kospi']['close']:,.2f}"
                               f"·외인 {o['flows']['foreign']:+,}억·{o['streak']['days']}일 연속"))
    return 0


def selftest() -> int:
    """감사가 **못 본 것**을 메모로 올리는가(네트워크 없음). 조용한 실패가 '불일치 없음'으로 읽히던 자리다."""
    global _T0, RECON, reconcile, audit_history, kr_symbols, refresh_index, index_series
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

    # audit_history는 실패해도 None이 아니라 이유를 돌려준다
    keep_run, keep_t0 = subprocess.run, _T0
    keep_fn = (RECON, reconcile, audit_history, kr_symbols, sys.argv)
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
            sys.argv = ["close_reconcile.py", "--date", "2026-10-13"]
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                main()
            saved = _load(RECON, {}) or {}
            # 감사 도중 실행이 끊기면(절전·종료) '감사 미완'이 디스크에 남는다 — 끝까지 가면 그 표지는 지워진다
            done_clean = AUDIT_PENDING not in (saved.get("notes") or [])

            def cut(**k):
                raise KeyboardInterrupt
            audit_history = cut
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    main()
            except KeyboardInterrupt:
                pass
            half = _load(RECON, {}) or {}
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
        RECON, reconcile, audit_history, kr_symbols, sys.argv = keep_fn
        _T0 = time.monotonic() - (BUDGET_SEC - 30)
        ok("예산이 30초 남으면 감사 몫(60초 예비)은 0 → 생략", _left(reserve=60) == 0
           and "시간 예산" in audit_history(timeout=min(AUDIT_MAX_SEC, _left(reserve=60)))["error"])
    finally:
        subprocess.run, _T0 = keep_run, keep_t0
        RECON, reconcile, audit_history, kr_symbols, sys.argv = keep_fn

    print(f"\n{'✅ SELFTEST PASS' if not fails else '❌ SELFTEST FAIL: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
