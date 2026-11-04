#!/usr/bin/env python3
"""idea_inbox.py — 유니버스(보유+워치) 밖 신규 아이디어 수신함 [11/4 신설 · 정훈 승인 "둘 다 해"].

왜 있나
────────────────────────────────────────────────────────────
11/4 정훈 지적: *"왜 쿠팡·앤트로픽 상장·양자주가 우리 판단에 필요 없어? 우리도 새로 투자할 수 있잖아."*
실측해 보니 분석이 **보유·워치 26종목에 고정**돼 있었다.
  · hunter.json 383편 중 유니버스 밖 개별 종목이 걸린 영상이 극소수(TSLA 6·INTC 3 외 대부분 1회)
  · 8개 데스크 정의가 전부 '보유+워치' — 특징주는 시세만 적고 후보 판정을 한 적이 없다
  · diversify_candidates는 워치 안에서만 순위를 매긴다 · missed_moves는 우리가 결정한 종목만 잰다
⇒ 밖에서 들어온 이름이 **적히지도, 판정되지도, 사후 채점되지도 않았다.** 그 통로를 만든다.

흐름 (상태)
  new → screening → deepdive → watch_candidate → promoted(워치 편입 = 정훈 승인)
                 ↘ rejected(사유 필수 · 재검토 조건 있으면 next_check)
  · 출처: hunter(경제사냥꾼)·feeds(수페·지식인)·movers(미장·국장 특징주)·ipo·13f·desk
  · 각 아이디어는 ①보유 종목과의 연결(link_to_holdings) ②신규 후보 자격을 **둘 다** 판정한다.

⚠️ 측정·수집 전용 — 매수 트리거가 아니다. 룰1 미국 트랙 대상 순서·룰3 추격 금지·룰6 배분이 위에 그대로 있다.
   워치 편입·매수 대상 순서 편입은 딥다이브 뒤 **정훈 승인**.

사용법
  python idea_inbox.py --add-from feed.json --source hunter     # research-feed 산출(ideas 배열) 병합
  python idea_inbox.py --add --ticker IONQ --name 아이온큐 --market US --source hunter \
        --claim "..." --ref <video_id> [--link "GOOGL:Willow 양자칩"]
  python idea_inbox.py --triage IONQ --status rejected --note "펀더<20 모멘텀 · 공매도 증가" [--next-check 2027-01-31]
  python idea_inbox.py --list [--status new]
  python idea_inbox.py --report          # 보고서 「🔭 유니버스 밖」 섹션용 마크다운
  python idea_inbox.py --stale           # 7일 넘게 판정 안 된 new
  python idea_inbox.py --selftest
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *([os.pardir] * 4)))
STATUSES = ("new", "screening", "deepdive", "watch_candidate", "promoted", "rejected")
ACTIVE = ("new", "screening", "deepdive", "watch_candidate")
STALE_DAYS = 7


def _path(root: str = ROOT) -> str:
    return os.path.join(root, "data", "app", "idea_inbox.json")


def today() -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).date().isoformat()


def universe(root: str = ROOT) -> set[str]:
    try:
        s = json.load(open(os.path.join(root, "data", "app", "stocks.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    u = set(s.get("stocks", {}))
    w = s.get("watchlist") or []
    u |= {(x.get("ticker") if isinstance(x, dict) else x) for x in (w if isinstance(w, list) else w.keys())}
    return {x for x in u if x}


def load(root: str = ROOT) -> dict:
    p = _path(root)
    if not os.path.exists(p):
        return {"_comment": "유니버스 밖 신규 아이디어 수신함 — 정본 도구 idea_inbox.py (손으로 고치지 말 것)",
                "updated": None, "ideas": []}
    return json.load(open(p, encoding="utf-8"))


def save(d: dict, root: str = ROOT) -> None:
    d["updated"] = today()
    with open(_path(root), "w", encoding="utf-8", newline="") as w:
        w.write(json.dumps(d, ensure_ascii=False, indent=1))


def _key(t: str) -> str:
    return (t or "").strip().upper()


def add(d: dict, idea: dict, source: str, uni: set[str], day: str | None = None) -> str:
    """병합. 반환 = 'added' | 'merged' | 'in_universe' | 'invalid'."""
    day = day or today()
    tk = (idea.get("ticker") or "").strip()
    if not tk:
        return "invalid"
    if tk in uni:
        return "in_universe"
    src = {"date": idea.get("date") or day, "type": source, "ref": idea.get("video_id") or idea.get("ref"),
           "claim": idea.get("claim"), "verdict": idea.get("verdict")}
    links = idea.get("link_to_holdings") or []
    for x in d["ideas"]:
        if _key(x["ticker"]) == _key(tk):
            if not any(s.get("ref") == src["ref"] and s.get("type") == source for s in x["sources"]):
                x["sources"].append(src)
            have = {(l.get("ticker"), l.get("relation")) for l in x.get("link_to_holdings", [])}
            x.setdefault("link_to_holdings", []).extend(l for l in links if (l.get("ticker"), l.get("relation")) not in have)
            if x["status"] == "rejected" and x.get("next_check") and x["next_check"] <= day:
                x["status"] = "new"
                x.setdefault("history", []).append({"date": day, "status": "new", "note": "재검토일 도래 + 새 출처"})
            x["updated"] = day
            return "merged"
    d["ideas"].append({"ticker": tk, "name": idea.get("name"), "market": idea.get("market"),
                       "first_seen": day, "updated": day, "status": "new", "sources": [src],
                       "link_to_holdings": links, "first_take": idea.get("first_take"),
                       "note": None, "next_check": None, "history": []})
    return "added"


def triage(d: dict, tk: str, status: str, note: str, next_check: str | None = None, day: str | None = None) -> bool:
    if status not in STATUSES:
        raise SystemExit(f"상태는 {STATUSES} 중 하나")
    if status == "rejected" and not note:
        raise SystemExit("rejected는 사유(--note) 필수 — 왜 버렸는지 없으면 사후 채점이 안 된다")
    day = day or today()
    for x in d["ideas"]:
        if _key(x["ticker"]) == _key(tk):
            x["status"], x["note"], x["updated"] = status, note, day
            if next_check:
                x["next_check"] = next_check
            x.setdefault("history", []).append({"date": day, "status": status, "note": note})
            return True
    return False


def stale(d: dict, day: str | None = None) -> list[dict]:
    day = dt.date.fromisoformat(day or today())
    return [x for x in d.get("ideas", []) if x.get("status") == "new"
            and (day - dt.date.fromisoformat(x["first_seen"])).days > STALE_DAYS]


def report_md(d: dict) -> str:
    act = [x for x in d.get("ideas", []) if x.get("status") in ACTIVE]
    rej = [x for x in d.get("ideas", []) if x.get("status") == "rejected"]
    out = ["## 🔭 유니버스 밖 — 신규 아이디어 수신함",
           f"활성 {len(act)} · 기각 {len(rej)} · 미판정(new) {sum(x['status'] == 'new' for x in act)} "
           "(정본 `data/app/idea_inbox.json` · 측정 전용, 매수 트리거 아님)", "",
           "| 종목 | 상태 | 출처(최근) | 주장 | 보유 연결 | PM 판정 |", "|---|---|---|---|---|---|"]
    for x in sorted(act, key=lambda x: (ACTIVE.index(x["status"]), x["first_seen"]), reverse=False):
        s = x["sources"][-1]
        link = "; ".join(f"{l.get('ticker')}: {l.get('relation')}" for l in x.get("link_to_holdings", [])[:3]) or "—"
        out.append(f"| {x['ticker']} {x.get('name') or ''} | {x['status']} | {s.get('type')} {s.get('date')} "
                   f"(출처 {len(x['sources'])}) | {(s.get('claim') or '')[:70]} [{s.get('verdict') or '미확인'}] | "
                   f"{link} | {x.get('note') or x.get('first_take') or '미판정'} |")
    if rej:
        out += ["", "기각: " + " · ".join(f"{x['ticker']}({(x.get('note') or '')[:30]}"
                                          + (f" · 재검토 {x['next_check']}" if x.get("next_check") else "") + ")"
                                          for x in rej[-10:])]
    return "\n".join(out)


def selftest() -> int:
    d = {"ideas": []}
    uni = {"NVDA", "GOOGL"}
    assert add(d, {"ticker": "NVDA"}, "hunter", uni) == "in_universe"
    assert add(d, {"ticker": "IONQ", "claim": "a", "video_id": "v1"}, "hunter", uni, "2026-11-01") == "added"
    assert add(d, {"ticker": "ionq", "claim": "b", "video_id": "v2",
                   "link_to_holdings": [{"ticker": "GOOGL", "relation": "Willow"}]}, "hunter", uni, "2026-11-02") == "merged"
    assert len(d["ideas"]) == 1 and len(d["ideas"][0]["sources"]) == 2 and d["ideas"][0]["link_to_holdings"]
    assert add(d, {"ticker": "IONQ", "video_id": "v2"}, "hunter", uni, "2026-11-02") == "merged"
    assert len(d["ideas"][0]["sources"]) == 2, "같은 출처 중복"
    assert [x["ticker"] for x in stale(d, "2026-11-09")] == ["IONQ"] and not stale(d, "2026-11-08")
    try:
        triage(d, "IONQ", "rejected", "")
        raise AssertionError("사유 없는 기각 통과")
    except SystemExit:
        pass
    assert triage(d, "IONQ", "rejected", "모멘텀", "2026-12-01", "2026-11-03")
    assert not stale(d, "2026-12-31")
    add(d, {"ticker": "IONQ", "video_id": "v3"}, "hunter", uni, "2026-11-20")
    assert d["ideas"][0]["status"] == "rejected", "재검토일 전 부활"
    add(d, {"ticker": "IONQ", "video_id": "v4"}, "hunter", uni, "2026-12-02")
    assert d["ideas"][0]["status"] == "new", "재검토일 뒤 새 출처면 다시 new"
    assert "IONQ" in report_md(d)
    print("idea_inbox selftest OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="유니버스 밖 신규 아이디어 수신함")
    ap.add_argument("--add-from", help="research-feed 산출 JSON(ideas 배열)")
    ap.add_argument("--add", action="store_true")
    ap.add_argument("--ticker"); ap.add_argument("--name"); ap.add_argument("--market")
    ap.add_argument("--source", default="desk", help="hunter·feeds·movers·ipo·13f·desk")
    ap.add_argument("--claim"); ap.add_argument("--ref"); ap.add_argument("--verdict")
    ap.add_argument("--link", action="append", default=[], help='"보유티커:관계" (여러 번)')
    ap.add_argument("--first-take")
    ap.add_argument("--triage", metavar="TICKER")
    ap.add_argument("--status", help=f"{STATUSES}")
    ap.add_argument("--note"); ap.add_argument("--next-check")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--stale", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    d, uni = load(), universe()
    if a.add_from:
        raw = json.load(open(a.add_from, encoding="utf-8"))
        ideas = raw.get("ideas", raw) if isinstance(raw, dict) else raw
        res = [(i.get("ticker"), add(d, i, a.source, uni)) for i in ideas]
        save(d)
        for tk, r in res:
            print(f"{r:12} {tk}")
        return 0
    if a.add:
        links = [{"ticker": l.split(":", 1)[0], "relation": l.split(":", 1)[1] if ":" in l else ""} for l in a.link]
        r = add(d, {"ticker": a.ticker, "name": a.name, "market": a.market, "claim": a.claim, "ref": a.ref,
                    "verdict": a.verdict, "link_to_holdings": links, "first_take": a.first_take}, a.source, uni)
        save(d) if r in ("added", "merged") else None
        print(r)
        return 0
    if a.triage:
        if not triage(d, a.triage, a.status, a.note, a.next_check):
            print(f"{a.triage} 없음"); return 1
        save(d); print("ok"); return 0
    if a.stale:
        for x in stale(d):
            print(f"{x['ticker']} new since {x['first_seen']}")
        return 0
    if a.report:
        print(report_md(d)); return 0
    for x in d["ideas"]:
        if a.status and x["status"] != a.status:
            continue
        print(f"{x['status']:15} {x['ticker']:14} {x.get('name') or '':16} 출처 {len(x['sources'])} · {x['first_seen']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
