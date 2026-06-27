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
  decisions.py close <id>            # 아젠다(open) → 결정 종결(closed) 이관 표시
  decisions.py list                  # 전체 1줄 요약

의존성 없음(stdlib). 자동 변경 없음 — 결정 정본은 사람이 master에도 함께 적는다.
"""
import argparse, json, os, sys, re
from datetime import date

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
    with open(LEDGER, "w", encoding="utf-8") as f:
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
    return "\n".join(lines)


def cmd_open(rows):
    op = [r for r in rows if r.get("status") == "open"]
    op = sorted(op, key=lambda r: r.get("date", ""))
    print(f"\n열린 전략 아젠다 / 미결 결정 {len(op)}건 (status=open) — 세션 시작 시 먼저 상기\n")
    for r in op:
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
        "date": a.date or date.today().isoformat(),
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


def cmd_close(rows, did):
    for r in rows:
        if str(r.get("id")) == did:
            r["status"] = "closed"
            save(rows)
            print(f"✅ {did} 종결(closed) 처리:\n" + show(r))
            return
    print(f"id {did} 없음. (decisions.py list 로 확인)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    q = sub.add_parser("query"); q.add_argument("terms", nargs="+")
    c = sub.add_parser("close"); c.add_argument("id")
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
        cmd_close(rows, a.id)
    elif a.cmd == "list":
        for r in sorted(rows, key=lambda r: r.get("date", ""), reverse=True):
            print(show(r, full=False))
    else:
        cmd_open(rows)


if __name__ == "__main__":
    main()
