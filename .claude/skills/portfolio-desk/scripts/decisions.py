#!/usr/bin/env python3
"""decisions.py — 구조화 결정 메모리 (Agent Memory · 검색 가능 인덱스)

배경(외부 레퍼런스): 2025~26 에이전트 메모리 연구·TradingAgents v0.2.4(persistent decision
log)·금융 환각 가드레일이 공통으로 가리키는 것 = "결정·근거를 산문이 아니라 **검색 가능한
구조**로 외부화하라(구조화 출력이 환각면적을 줄인다)". 세션이 바뀌면 끊기는 '왜 그렇게
결정했나'의 맥락을, master §9 결정로그·§10 전략아젠다의 *사람용 산문*과 별개로 **기계 인덱스**로
둔다. calls_log.jsonl ↔ score_calls 관계와 같은 이중구조(산문=사람 정본, jsonl=기계 검색).

  decisions.py                       # status=open 전부 (= 전략 아젠다 빠른 조회)
  decisions.py query <키워드> [...]   # topic/decision/rationale/tags 부분일치(open+closed)
  decisions.py add --topic .. --decision .. [--date YYYY-MM-DD] [--rationale ..]
                  [--rejected ..] [--tags a,b] [--status open|closed] [--refs ..]
  decisions.py close <id> [--resolution 사유] [--by d223,커밋] [--date YYYY-MM-DD]
                                     # 아젠다(open) → 결정 종결(closed). 사유는 같은 행에 남긴다
  decisions.py note <id> --current 현재상태 [--ask 정훈에게_물을_것]
                                     # 열린 결정의 현재 상태 갱신(current·current_as_of)
  decisions.py list                  # 전체 1줄 요약

의존성 없음(stdlib). 자동 변경 없음 — 결정 정본은 사람이 master에도 함께 적는다.

★[11/7 트리아지] 종결 사유는 **같은 행의 필드**에 둔다(9/29 관례: closed·resolution·superseded_by).
  같은 id로 사유 행을 따로 append하지 않는다 — close가 첫 매칭 행만 닫고 id 조회가 갈라진다.
  `ask`가 있는 열린 행 = 정훈 판단 필요 → 목록 맨 위에 따로 보여준다.
"""
import argparse, json, os, sys, re
from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def today_kst() -> date:
    """[7/13] 날짜는 항상 KST 실측 — UTC 컨테이너에서 00~09시 KST에 하루 밀리는 것 방지."""
    return datetime.now(KST).date()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
LEDGER = os.path.join(ROOT, "data", "app", "decisions.jsonl")


def load():
    if not os.path.exists(LEDGER):
        return []
    return [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]


def save(rows):
    rows = sorted(rows, key=lambda r: (r.get("status") != "open", r.get("date", "")), reverse=False)
    # open 먼저(아젠다), 그 안에서 날짜 오름차순 → 출력은 별도 정렬. 저장은 안정적으로.
    rows = sorted(rows, key=lambda r: r.get("date", ""))
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    # newline="\n": 윈도우 텍스트 모드가 CRLF로 쓰면 워킹트리 전체가 바뀐 것처럼 보인다(.gitattributes eol=lf)
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def next_id(rows):
    nums = [int(m.group(1)) for r in rows
            if (m := re.match(r"d(\d+)$", str(r.get("id", ""))))]
    return f"d{(max(nums) + 1) if nums else 1}"


def show(r, full=True):
    icon = "🟢열림" if r.get("status") == "open" else "⚪종결"
    head = f"[{r.get('id','?')}] {icon} {r.get('date','')}  {r.get('topic','')}"
    if not full:
        return head
    lines = [head, f"   결정/상태: {r.get('decision','')}"]
    if r.get("rationale"):
        lines.append(f"   근거: {r['rationale']}")
    if r.get("rejected"):
        lines.append(f"   기각/대안: {r['rejected']}")
    if r.get("tags"):
        lines.append(f"   태그: {', '.join(r['tags'])}")
    if r.get("refs"):
        lines.append(f"   참조: {r['refs']}")
    if r.get("current"):
        lines.append(f"   현재({r.get('current_as_of', '?')}): {r['current']}")
    if r.get("ask") and r.get("status") == "open":
        lines.append(f"   ❓정훈 판단: {r['ask']}")
    if r.get("status") != "open" and (r.get("resolution") or r.get("closed_note")):
        when = r.get("closed") or r.get("closed_at") or "?"
        by = f" ← {r['superseded_by']}" if r.get("superseded_by") else ""
        lines.append(f"   종결({when}){by}: {r.get('resolution') or r.get('closed_note')}")
    return "\n".join(lines)


def cmd_open(rows):
    op = [r for r in rows if r.get("status") == "open"]
    op = sorted(op, key=lambda r: r.get("date", ""))
    ask = [r for r in op if r.get("ask")]
    rest = [r for r in op if not r.get("ask")]
    print(f"\n열린 전략 아젠다 / 미결 결정 {len(op)}건 (status=open · 정훈 판단 필요 {len(ask)}건)"
          f" — 세션 시작 시 먼저 상기\n")
    if ask:
        print("── ❓ 정훈 판단 필요 ──\n")
        for r in ask:
            print(show(r) + "\n")
        print("── 살아 있는 아젠다 ──\n")
    for r in rest:
        print(show(r) + "\n")
    print("※ 정본은 master §9/§10. 이건 기계 검색 인덱스 — query <키워드>로 관련 결정만 끌어오기.")


def cmd_query(rows, terms):
    kws = [t.lower() for t in terms]
    def hit(r):
        blob = " ".join(str(r.get(k, "")) for k in
                        ("topic", "decision", "rationale", "rejected", "refs")).lower()
        blob += " " + " ".join(r.get("tags", [])).lower()
        return all(k in blob for k in kws)
    found = sorted([r for r in rows if hit(r)], key=lambda r: r.get("date", ""), reverse=True)
    print(f"\n'{' '.join(terms)}' 매칭 결정 {len(found)}건 (최신순)\n")
    for r in found:
        print(show(r) + "\n")
    if not found:
        print("  매칭 없음. (태그·키워드 점검 또는 add로 신규 결정 기록)")


def cmd_add(a, rows):
    rec = {
        "id": next_id(rows),
        "date": a.date or today_kst().isoformat(),
        "topic": a.topic,
        "decision": a.decision,
        "rationale": a.rationale or "",
        "rejected": a.rejected or "",
        "status": a.status,
        "tags": [t.strip() for t in (a.tags or "").split(",") if t.strip()],
        "refs": a.refs or "",
    }
    rows.append(rec)
    save(rows)
    print("✅ 추가:\n" + show(rec))


def _find(rows, did):
    hits = [r for r in rows if str(r.get("id")) == did]
    if len(hits) > 1:
        print(f"⚠️ id {did}가 {len(hits)}행 — 첫 행만 다룬다(id 충돌은 손으로 정리할 것)")
    return hits[0] if hits else None


def cmd_close(rows, did, resolution=None, by=None, when=None):
    r = _find(rows, did)
    if r is None:
        print(f"id {did} 없음. (decisions.py list 로 확인)")
        return
    r["status"] = "closed"
    if resolution:
        r["closed"] = when or today_kst().isoformat()
        r["resolution"] = resolution
        if by:
            r["superseded_by"] = by
        r.pop("ask", None)
    save(rows)
    print(f"✅ {did} 종결(closed) 처리:\n" + show(r))


def cmd_note(rows, did, current, ask=None, when=None):
    r = _find(rows, did)
    if r is None:
        print(f"id {did} 없음. (decisions.py list 로 확인)")
        return
    if r.get("status") != "open":
        print(f"⚠️ {did}는 이미 종결 — note는 열린 결정에만 쓴다")
        return
    r["current"] = current
    r["current_as_of"] = when or today_kst().isoformat()
    if ask:
        r["ask"] = ask
    save(rows)
    print(f"✅ {did} 현재 상태 갱신:\n" + show(r))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    q = sub.add_parser("query"); q.add_argument("terms", nargs="+")
    c = sub.add_parser("close"); c.add_argument("id")
    c.add_argument("--resolution", help="종결 사유(근거) — 같은 행 resolution 필드")
    c.add_argument("--by", help="대체·흡수한 결정 id나 커밋(예: d223, e951ec12)")
    c.add_argument("--date", help="종결일(기본 = 오늘 KST)")
    n = sub.add_parser("note"); n.add_argument("id")
    n.add_argument("--current", required=True, help="현재 상태 한 줄")
    n.add_argument("--ask", help="정훈에게 물을 것(있으면 '정훈 판단 필요'로 맨 위에 표시)")
    n.add_argument("--date", help="기준일(기본 = 오늘 KST)")
    ad = sub.add_parser("add")
    ad.add_argument("--date"); ad.add_argument("--topic", required=True)
    ad.add_argument("--decision", required=True); ad.add_argument("--rationale")
    ad.add_argument("--rejected"); ad.add_argument("--tags")
    ad.add_argument("--status", default="open", choices=["open", "closed"])
    ad.add_argument("--refs")
    a = ap.parse_args()
    rows = load()

    if a.cmd == "query":
        cmd_query(rows, a.terms)
    elif a.cmd == "add":
        cmd_add(a, rows)
    elif a.cmd == "close":
        cmd_close(rows, a.id, a.resolution, a.by, a.date)
    elif a.cmd == "note":
        cmd_note(rows, a.id, a.current, a.ask, a.date)
    elif a.cmd == "list":
        for r in sorted(rows, key=lambda r: r.get("date", ""), reverse=True):
            print(show(r, full=False))
    else:
        cmd_open(rows)


if __name__ == "__main__":
    main()
