#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory_recall.py — 종목·주제별 기억 통합 회수 (계층 기억 + 회수) [2026-08-05 신설]

■ 왜 만들었나
우리 기억은 **네 군데에 흩어져 있고, 서로를 모른다**:
  · decisions.jsonl    — 왜 그렇게 결정했나(기각안 포함)
  · calls_log.jsonl    — 그때 별점·스코어·목표가·매수존을 뭐라 했나
  · missed_moves.jsonl — 안 사서/안 팔아서 놓친 것(반사실 채점·교훈)
  · hindsight/hunter   — 회고 산문·채널 조건 트래커
"MU 3차 트랜치" 하나를 판단하려면 네 파일을 각각 열어 눈으로 뒤져야 했다.
그래서 실제로 **놓친다** — 8/2에 확인된 구멍(⭐2 종목 트림이 산문엔 8~9회, 오더엔 0회)도
"과거에 같은 말을 몇 번 했는지"가 한 화면에 안 모여서 생긴 일이다.

금융 에이전트 문헌(FinMem·FinAgent)이 공통으로 말하는 건 **계층 기억 + 회수**다:
기억을 쌓기만 하지 말고, **지금 상황에 관련된 것만 점수 매겨 끌어올려라**. 우리는 이미
쌓는 쪽(4개 원장)은 갖췄으나 **끌어올리는 쪽이 없었다.** 이 스크립트가 그 회수부다.

■ 회수 점수 = 관련성 × 최신성 × 중요도  (FinMem 3요소를 우리 원장에 맞춘 것)
  · 관련성(relevance): 질의어가 티커·주제·근거·태그 어디에 걸렸나 (필드별 가중)
  · 최신성(recency)  : 반감기 90일 지수감쇠 — 오래된 판단은 자동으로 뒤로 밀린다
  · 중요도(importance): 원장 종류·상태로 준 고정 가중
      열린 아젠다(status=open) > 종결 결정 > 검증된 미스무브 > 일반 콜
  ⚠️ 이 점수는 **읽을 순서**일 뿐이다. 점수가 높다고 그 판단이 옳았다는 뜻이 전혀 아니다.

■ 규율
  · **읽기 전용 — 원장을 고치지 않는다.** 별점·스코어·트랜치 어떤 룰도 바꾸지 않는다.
  · 회수는 **검색이지 요약이 아니다.** 원문을 그대로 보여주고, 해석은 PM이 한다.
  · 반대 증거를 숨기지 않는다 — 같은 종목의 **틀린 콜·기각된 대안**도 같이 끌어올린다
    (확증편향 방지. CLAUDE.md "신뢰-견제 균형"의 기계판).

■ 사용
  memory_recall.py MU                    # MU 관련 기억 전부(원장 4종 통합)
  memory_recall.py 트랜치 --limit 15      # 주제어로
  memory_recall.py 현대차 --since 2026-07-01
  memory_recall.py MU --json

데이터: data/app/{decisions,calls_log,missed_moves,rule_log}.jsonl. 네트워크 없음·stdlib만.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
APP = os.path.join(ROOT, "data", "app")

HALF_LIFE_DAYS = 90.0  # 최신성 반감기

# 원장별 고정 중요도. 열린 아젠다가 가장 위로 오게 한다(아직 안 끝난 고민이므로).
KIND_WEIGHT = {
    "decision_open": 1.6,
    "decision_closed": 1.2,
    "missed_verified": 1.3,
    "missed": 1.0,
    "call": 0.8,
    "rule": 0.9,
}

# 티커 ↔ 한글명 (질의어가 어느 쪽으로 들어와도 걸리게)
ALIAS = {
    "005930.KS": ["삼성전자", "삼성", "005930"],
    "066570.KS": ["LG전자", "엘지전자", "066570"],
    "454910.KS": ["두산로보틱스", "두산로보", "454910"],
    "005380.KS": ["현대차", "현대자동차", "005380"],
    "035420.KS": ["NAVER", "네이버", "035420"],
}


def _read_jsonl(name):
    path = os.path.join(APP, name)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # 깨진 줄 하나가 회수 전체를 막지 않게
    return out


def _expand(query):
    """질의어 확장 — 티커↔한글명 양방향."""
    q = query.strip()
    terms = {q.lower()}
    for tk, names in ALIAS.items():
        pool = [tk, tk.split(".")[0]] + names
        if any(q.lower() == p.lower() for p in pool):
            terms.update(p.lower() for p in pool)
    return terms


def _match(terms, weighted_fields):
    """필드별 가중 관련성. weighted_fields = [(텍스트, 가중치), ...]"""
    score = 0.0
    hits = []
    for text, w in weighted_fields:
        if not text:
            continue
        low = str(text).lower()
        for t in terms:
            if t and t in low:
                score += w
                hits.append(t)
                break
    return score, hits


def _recency(datestr, today):
    """반감기 90일 지수감쇠. 날짜 불명이면 중립값 0.5."""
    try:
        d = datetime.strptime(str(datestr)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0.5
    days = max(0, (today - d).days)
    return math.pow(0.5, days / HALF_LIFE_DAYS)


def collect(query, since=None, today=None):
    today = today or date.today()
    terms = _expand(query)
    items = []

    for r in _read_jsonl("decisions.jsonl"):
        rel, hits = _match(terms, [(r.get("topic"), 3.0), (r.get("decision"), 2.0),
                                   (r.get("rationale"), 1.0), (r.get("tags"), 1.5),
                                   (r.get("rejected"), 1.0)])
        if rel <= 0:
            continue
        open_ = (r.get("status") == "open")
        items.append({
            "kind": "decision_open" if open_ else "decision_closed",
            "date": r.get("date", ""), "rel": rel, "id": r.get("id"),
            "headline": r.get("topic", ""),
            "body": r.get("decision", ""),
            "extra": {"근거": r.get("rationale"), "기각안": r.get("rejected"),
                      "상태": r.get("status")},
            "hits": hits,
        })

    for r in _read_jsonl("calls_log.jsonl"):
        rel, hits = _match(terms, [(r.get("ticker"), 3.0), (r.get("source_report"), 0.5)])
        if rel <= 0:
            continue
        items.append({
            "kind": "call", "date": r.get("date", ""), "rel": rel, "id": None,
            "headline": f"{r.get('ticker')} ⭐{r.get('stars')} · 스코어 {r.get('score')}",
            "body": f"목표 {r.get('target')} · 매수존 {r.get('buy_zone')}",
            "extra": {"출처": r.get("source_report")}, "hits": hits,
        })

    for r in _read_jsonl("missed_moves.jsonl"):
        rel, hits = _match(terms, [(r.get("ticker"), 3.0), (r.get("signal"), 1.5),
                                   (r.get("rationale"), 1.0), (r.get("lesson"), 1.5),
                                   (r.get("cluster_tag"), 1.0)])
        if rel <= 0:
            continue
        verified = bool(r.get("verdict"))
        items.append({
            "kind": "missed_verified" if verified else "missed",
            "date": r.get("date", ""), "rel": rel, "id": r.get("id"),
            "headline": f"{r.get('ticker')} {r.get('decision_type')} → {r.get('verdict') or '미채점'}"
                        f" ({r.get('move_pct')}% / {r.get('horizon')})",
            "body": r.get("lesson") or r.get("rationale") or "",
            "extra": {"신호": r.get("signal"), "기준가": r.get("ref_price"),
                      "묶음": r.get("cluster_tag")}, "hits": hits,
        })

    for r in _read_jsonl("rule_log.jsonl"):
        rel, hits = _match(terms, [(json.dumps(r, ensure_ascii=False), 1.0)])
        if rel <= 0:
            continue
        items.append({
            "kind": "rule", "date": r.get("date", ""), "rel": rel, "id": None,
            "headline": f"룰 스냅샷 — 코스피 {r.get('kospi')} · 낙폭 {r.get('dd_pct')}%",
            "body": f"해금 {r.get('unlocked_ratio')} · 상한 {r.get('allowed_krw')}원"
                    f" · 정지 {r.get('halted')}",
            "extra": {"폭풍%ile": r.get("storm_pct"), "rule2": r.get("rule2")}, "hits": hits,
        })

    if since:
        items = [i for i in items if str(i["date"])[:10] >= since]

    for i in items:
        i["recency"] = _recency(i["date"], today)
        i["weight"] = KIND_WEIGHT.get(i["kind"], 1.0)
        i["score"] = round(i["rel"] * i["recency"] * i["weight"], 3)
    # 점수 내림차순, 동점이면 최신 우선.
    # (파이썬 sort는 안정정렬 → 날짜로 먼저 정렬한 순서가 동점 안에서 보존된다)
    items.sort(key=lambda x: str(x["date"]), reverse=True)
    items.sort(key=lambda x: -x["score"])
    return items


KIND_LABEL = {
    "decision_open": "🟠 열린 아젠다", "decision_closed": "🔵 결정(종결)",
    "missed_verified": "🟣 미스무브(검증)", "missed": "🟣 미스무브",
    "call": "⚪ 과거 콜", "rule": "🟤 룰 스냅샷",
}


def main():
    ap = argparse.ArgumentParser(
        description="종목·주제별 기억 통합 회수 — 결정·콜·미스무브·룰 원장을 한 번에 (읽기 전용)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="예) memory_recall.py MU\n    memory_recall.py 트랜치 --limit 15")
    ap.add_argument("query", help="티커(MU·005380.KS·현대차) 또는 주제어(트랜치·안전핀)")
    ap.add_argument("--limit", type=int, default=12, help="표시 건수(기본 12)")
    ap.add_argument("--since", help="이 날짜 이후만 YYYY-MM-DD")
    ap.add_argument("--kind", choices=sorted(set(k.split("_")[0] for k in KIND_WEIGHT)),
                    help="원장 종류로 필터 (decision·missed·call·rule)")
    ap.add_argument("--json", action="store_true", help="기계 소비용 JSON")
    args = ap.parse_args()

    items = collect(args.query, since=args.since)
    if args.kind:
        items = [i for i in items if i["kind"].split("_")[0] == args.kind]
    shown = items[:args.limit]

    if args.json:
        print(json.dumps({"query": args.query, "total": len(items), "items": shown},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"\n🧠 기억 회수 — \"{args.query}\"  (총 {len(items)}건 중 상위 {len(shown)})")
    print("   점수 = 관련성 × 최신성(반감기 90일) × 원장가중. **읽을 순서일 뿐 — 옳았다는 뜻이 아니다.**")
    if not shown:
        print("\n   해당 없음. ※'없음'도 결론 — 이 종목·주제로 남긴 판단 기록이 아직 없다.")
        return 0

    counts = {}
    for i in items:
        counts[i["kind"]] = counts.get(i["kind"], 0) + 1
    print("   구성: " + " · ".join(f"{KIND_LABEL.get(k, k)} {v}" for k, v in
                                 sorted(counts.items(), key=lambda x: -x[1])))
    print()
    for i in shown:
        print(f"  [{i['score']:>5}] {KIND_LABEL.get(i['kind'], i['kind'])}  {i['date']}"
              f"{'  #' + str(i['id']) if i.get('id') else ''}")
        print(f"      {i['headline']}")
        if i["body"]:
            print(f"      {str(i['body'])[:200]}")
        for k, v in (i["extra"] or {}).items():
            if v:
                print(f"        · {k}: {str(v)[:160]}")
        print()

    open_n = counts.get("decision_open", 0)
    if open_n:
        print(f"   ⚠️ 열린 아젠다 {open_n}건 — 아직 결론 안 난 고민이다. 이번 판단에서 갱신할 것.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
