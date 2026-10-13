#!/usr/bin/env python3
"""close_reconcile.py — 국내 마감 대사 자동화 (외인 수급 확정 · 코스피 낙폭 확정)

★[2026-10-12 신설 — 정훈 "이런 걸 계속 자동으로 요청하게 말고 너가 완성시켜봐"]

왜 만들었나:
  장중에 쓴 보고서는 수급·낙폭을 '잠정'으로 적고 "마감 후 대사"를 할 일로 남겼다(t1012-1·t1012-2 유형).
  그 할 일은 사람이 "대사해줘"라고 해야만 돌았고, flows.json엔 **'잠정 — KRX 확정 대사 필요'가
  9/22 이후 7거래일째 그대로** 쌓여 있었다. 요청해야 도는 대사는 대사가 아니다.

하는 일 (토큰 0 · 네트워크 = 네이버·Yahoo 무키):
  ① 코스피·코스닥 당일 투자자별 순매수(억원)를 받아 flows.json 당일 행을 upsert
     · 1차(16:10) = '잠정' / 2차(20:10, 애프터마켓 종료 뒤) = 1차와 대조해 '확정'
     · 사람이 매체 교차로 적은 행([마감 확정 — …매체…])은 **덮지 않고** 수치만 대조해 차이를 남긴다
  ② ^KS11·^KQ11 일봉 캐시 갱신 → 종가·고점대비 낙폭 확정
  ③ 외인 연속 순매도/순매수 일수 재계산
  ④ data/app/close_recon.json에 결과 기록(보고서·브리핑이 읽는 정본) · 시장 누적(market_flows.jsonl) 갱신
  ⑤ --commit이면 자기 파일만 커밋·푸시(작업트리의 다른 변경은 건드리지 않는다)

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

sys.path.insert(0, _HERE)


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


def refresh_index() -> None:
    """지수 + 국내 보유·워치 일봉을 마감 뒤 다시 받는다.

    ★[2026-10-13] 지수만 갱신하고 있어 **종목 행은 장중에 쓴 값이 그대로 남았다**(10/12 삼성 257,000 ↔
      종가 250,500). 장중 보고서 세션이 쓴 당일 행을 같은 날 마감 뒤 확정 종가로 바꾸는 주체가 없었다.
      history_backfill의 개정창 upsert + 결측 봉 보정이 여기서 매일 16:10·20:10에 돈다.
    """
    hb = os.path.join(_HERE, "history_backfill.py")
    # 지수가 먼저다 — 낙폭·수급 대사는 지수만 있으면 돈다. 종목은 따로 돌리고, 늦거나 죽어도 대사를 막지 않는다
    # (한 호출로 묶으면 종목 20여 개 중 하나가 걸려 타임아웃이 날 때 지수 대사까지 같이 죽는다).
    subprocess.run([sys.executable, hb, "--symbols", "^KS11,^KQ11", "--pace", "0.6"],
                   capture_output=True, text=True, timeout=120)
    syms = kr_symbols()
    if not syms:
        return
    try:
        subprocess.run([sys.executable, hb, "--symbols", ",".join(syms), "--pace", "0.6"],
                       capture_output=True, text=True, timeout=420)
    except subprocess.TimeoutExpired:
        print("  ⚠️ 종목 일봉 갱신 시간 초과 — 지수 대사는 계속한다(종목은 다음 실행에서 다시 받는다)")


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

    refresh_index()
    ks, kq = index_series("_KS11.csv"), index_series("_KQ11.csv")
    if not ks or ks[-1][0] != today:
        out.update({"status": "no_session",
                    "notes": [f"^KS11 마지막 일봉 {ks[-1][0] if ks else '없음'} ≠ {today} — 휴장이거나 마감 전"]})
        return out
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
    def git(*a):
        return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True, timeout=120)
    ex = [f for f in own_files() if os.path.exists(os.path.join(ROOT, f))]
    git("add", "--", *ex)
    if git("diff", "--cached", "--quiet").returncode == 0:
        return "변경 없음"
    if git("commit", "-q", "-m", msg, "--", *ex).returncode != 0:
        return "커밋 실패"
    git("fetch", "-q", "origin", "main")
    if git("merge-base", "--is-ancestor", "origin/main", "HEAD").returncode != 0:
        return "커밋만 함 — origin/main이 앞서 있어 푸시 보류(다음 세션이 합친다)"
    return "푸시 완료" if git("push", "-q", "origin", "HEAD:main").returncode == 0 else "커밋만 함 — 푸시 실패"


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
    a = ap.parse_args()
    if a.status:
        o = _load(RECON)
        print(line(o) if o else "마감 대사 기록 없음")
        return 0
    if now().weekday() >= 5 and not a.date:
        print("주말 — 대사 없음")
        return 0
    o = reconcile(a.date)
    if o.get("status") == "ok" or not os.path.exists(RECON):
        _dump(RECON, o)
    print(line(o))
    if a.commit and o.get("status") == "ok":
        print("  git:", commit(f"마감 대사 자동 {o['date']} [{o['grade']}] — 코스피 {o['kospi']['close']:,.2f}"
                               f"·외인 {o['flows']['foreign']:+,}억·{o['streak']['days']}일 연속"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
