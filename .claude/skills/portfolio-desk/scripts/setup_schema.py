#!/usr/bin/env python3
"""setup_schema.py — 경제사냥꾼 조건 트래커(setups) 스키마 정규화·감사

배경 [8/6 시스템 감사 → 8/7 정훈 승인 "스키마 개편해줘"]:
정훈 6/28 지시는 *"조건 ~75%+ 충족 & 가격존 진입 시 지정가 매수/매도 발동"* 인데,
8/6 감사에서 **그 75%를 아무도 계산하지 않고 있었다**는 게 드러났다. 실측 결손 4종:

  ① `updated` 필드 0/19 — stale 판정 자체가 불가("stale 방치 금지" 규칙이 집행 불능)
  ② `met_pct` 기계필드 없음 — 상태가 label/status의 한글 산문("추적중(3/4 met …)")
  ③ orders 26건 전부 `setup_id` 없음 — 셋업과 오더가 별개 우주(= 8/2 "산문 8~9회 vs
     오더 0회"와 같은 구조의 재발. 오더북에 들어간 것만 집행된다)
  ④ 조건 원문에 결과를 덮어씀(73개 중 21개 ≈ 30%) — 결정 시점 원문이 소실돼
     트랙레코드 정직성이 훼손. 논문 용어로 **Oracle Fallacy**(arXiv 2605.19337):
     사후 결과가 섞인 기록을 회수하면 회고가 오염된다. memory_recall이 이걸 끌어올린다.

이 스크립트가 하는 일:
  --migrate   기존 hunter.json setups를 새 스키마로 승격(멱등·비파괴)
  --check     감사만: stale·기한경과 미채점·발동권(≥75%) 미배선 오더
  --dry-run   --migrate와 함께 쓰면 바꿀 내용만 출력하고 저장 안 함

새 스키마 (setup):
  id, ticker, label, thesis, action, note        (기존 유지)
  status      : 기계값 — watching|armed|fired|done|dropped
  status_note : 기존 한글 산문 상태(사람용, 자유서술)
  updated     : YYYY-MM-DD  ← 마지막 갱신일(신설·필수)
  met_pct     : 0~100 정수  ← conditions에서 자동 계산(신설·파생값)
  order_ids   : [str]       ← 이 셋업에서 나간 tasks.json orders id(신설)
새 스키마 (condition):
  text     : **불변**. 결정 시점 원문. 사후 수정 금지.
  met      : bool
  outcome  : 결과 서술(사후 갱신은 전부 여기로). 없으면 null
  resolved : YYYY-MM-DD | null — 채점된 날
  due      : YYYY-MM-DD | null — 기한(있으면 경과 시 미채점 경보)
tasks.json order: `setup_id` (신설·null 허용)

⚠️ 측정·정규화 전용 — 별점·트랜치·안전핀 어떤 룰도 바꾸지 않는다. 자동 매매 아님.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
HUNTER = os.path.join(ROOT, "data/app/hunter.json")
TASKS = os.path.join(ROOT, "data/app/tasks.json")

STATUS_VALUES = ("watching", "armed", "fired", "done", "dropped")

# 조건 원문에 덮어쓴 '결과'를 분리하는 마커.
# 원문과 결과 사이 구분자는 실데이터상 ' — ' 또는 ' : ' 뒤에 아래 토큰이 온다.
_OUTCOME_TOKENS = r"(?:✅|❌|🚨|부분충족|미충족|충족|확정|재악화|실제|\[\d{1,2}/\d{1,2}\s*갱신\]|\[신규)"
_SPLIT_RE = re.compile(r"\s+[—–]\s+(?=" + _OUTCOME_TOKENS + ")")

# 조건문 안의 날짜(기한) 추출: "8/26 CEO 인베스터데이", "7/29~30 컨퍼런스콜"
_DUE_RE = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])")


def today_kst() -> dt.date:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).date()


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _save(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def split_outcome(text: str):
    """조건 원문에서 사후 덧붙은 결과를 분리 → (원문, 결과|None).

    보수적으로 간다: 마커가 명확할 때만 자른다. 애매하면 통째로 원문 유지.
    원본 문자열은 호출측이 `_raw`에 보존하므로 정보 손실은 없다.
    """
    if not isinstance(text, str):
        return text, None
    parts = _SPLIT_RE.split(text, maxsplit=1)
    if len(parts) == 2 and len(parts[0].strip()) >= 8:
        return parts[0].strip(), parts[1].strip()
    return text, None


def infer_due(text: str, anchor: dt.date):
    """조건문 안 'M/D'를 기한으로 해석. anchor(셋업 생성일) 이후 가장 이른 날짜."""
    if not isinstance(text, str):
        return None
    best = None
    for mm, dd in _DUE_RE.findall(text):
        try:
            m, d = int(mm), int(dd)
            if not (1 <= m <= 12 and 1 <= d <= 31):
                continue
            cand = dt.date(anchor.year, m, d)
            if cand < anchor - dt.timedelta(days=180):
                cand = dt.date(anchor.year + 1, m, d)
        except ValueError:
            continue
        if best is None or cand < best:
            best = cand
    return best.isoformat() if best else None


def setup_anchor(s: dict) -> dt.date:
    """셋업 생성일. ① id 꼬리 MMDD(setup-…-0728) ② note/thesis 맨 앞 [M/D] 태그
    ③ 그래도 없으면 오늘.

    ②가 필요한 이유: id 없는 셋업에 오늘 날짜로 id를 지어주면 7/12에 만든 셋업이
    `setup-SPCX-0807`이 돼 이력이 왜곡된다(실측 1건).
    """
    m = re.search(r"-(\d{2})(\d{2})$", str(s.get("id") or ""))
    if m:
        try:
            return dt.date(today_kst().year, int(m.group(1)), int(m.group(2)))
        except ValueError:
            pass
    blob = f"{s.get('note') or ''} {s.get('thesis') or ''}"
    tag = re.search(r"[\[(](\d{1,2})/(\d{1,2})", blob)
    if tag:
        try:
            return dt.date(today_kst().year, int(tag.group(1)), int(tag.group(2)))
        except ValueError:
            pass
    return today_kst()


def last_activity(s: dict, anchor: dt.date) -> str:
    """셋업의 **실제** 마지막 갱신일을 텍스트 증거에서 복원한다.

    ⚠️ [8/7 자가교정] 초판 migrate가 `updated`를 전부 오늘로 찍었다 —
    그러면 20개 셋업이 일제히 '방금 갱신됨'이 돼 **stale 검출이 14일간 무력화**된다.
    (감사 도구를 만들면서 감사 대상을 리셋해버린 셈.)
    ⇒ note·outcome·status에 박힌 `[M/D 갱신]`·`[M/D 신규]` 태그 중 **가장 늦은 날짜**를
    쓰고, 증거가 없으면 셋업 생성일(anchor)로 둔다. 미래 날짜는 버린다.
    """
    today = today_kst()
    blob = " ".join([
        str(s.get("note") or ""), str(s.get("status") or ""), str(s.get("label") or ""),
        *[str(c.get("outcome") or "") for c in (s.get("conditions") or [])],
    ])
    best = anchor
    for mm, dd in re.findall(r"[\[(](\d{1,2})/(\d{1,2})", blob):
        try:
            cand = dt.date(today.year, int(mm), int(dd))
        except ValueError:
            continue
        if cand <= today and cand > best:
            best = cand
    return min(best, today).isoformat()


def calc_met_pct(conds) -> int:
    conds = conds or []
    if not conds:
        return 0
    return round(100 * sum(1 for c in conds if c.get("met")) / len(conds))


def normalize_status(s: dict, met_pct: int) -> str:
    """기존 한글 상태 산문 → 기계값.

    ⚠️ [8/7 실측 교훈] **`note`는 절대 읽지 않는다.** note는 긴 산문이라 상태어가
    우연히·심지어 **반대 뜻으로** 박혀 있다(실측: twlo/하이닉스ADR note의
    *"발동 셋업 아님"*, 엔캐리 note의 *"등록완료"*, 현대차로봇 note의 *"발주→계약"*).
    초안이 note까지 읽어서 **활성 셋업 3개를 done으로 오판**했다 — done은 감사에서
    제외되므로 그대로 두면 감시가 조용히 꺼진다.
    ⇒ 상태의 정본은 `status`·`status_note`·`label` 셋뿐. 부정형("아님")이면 무시한다.

    ⚠️ [8/7 2차 자가교정] `status_note`를 빼먹으면 **재실행 시 상태가 소실된다** —
    1회차가 status를 기계값("fired")으로 덮고 원문을 status_note로 옮기므로,
    2회차 blob에 한글 마커가 사라져 met_pct 폴백으로 강등된다(실측: 메모리코어
    fired→armed, 조선cpsp done→watching). status_note는 불변이라 이걸 읽으면 멱등해진다.
    """
    blob = " ".join(str(s.get(k) or "") for k in ("status", "status_note", "label"))

    def hit(pat):
        for m in re.finditer(pat, blob):
            tail = blob[m.end():m.end() + 6]
            if "아님" in tail or "아닌" in tail:      # "발동 셋업 아님" 류 부정
                continue
            return True
        return False

    if hit(r"폐기|대체됨|드롭"):
        return "dropped"
    if hit(r"완료|종결"):
        return "done"
    if hit(r"체결"):
        return "fired"
    if hit(r"임박|점등") or met_pct >= 75:
        return "armed"
    return "watching"


# 관찰 전용 셋업(오더를 내지 않는 것)을 표시하는 문구 — ≥75% 오더 배선 검사에서 제외.
_OBSERVE_RE = re.compile(r"관찰용|관찰 격상|발동 셋업 아님|매수 트리거 아님|미보유·비워치")


def infer_actionable(s: dict) -> bool:
    blob = " ".join(str(s.get(k) or "") for k in ("status", "label", "note"))
    return not bool(_OBSERVE_RE.search(blob))


# ── 마이그레이션 ─────────────────────────────────────────────────────────
def migrate(dry=False):
    hu = _load(HUNTER)
    setups = hu.get("setups") or []
    today = today_kst().isoformat()
    changes = []

    for s in setups:
        anchor = setup_anchor(s)
        before = json.dumps(s, ensure_ascii=False, sort_keys=True)
        local = []                                   # 이 셋업의 변경 로그(헤더 뒤에 붙인다)

        # id 없는 셋업은 감사에서 식별 불가 → ticker+생성일로 생성
        if not s.get("id"):
            s["id"] = f"setup-{s.get('ticker') or 'unknown'}-{anchor.strftime('%m%d')}"
            local.append(f"    · id 신설: {s['id']}")

        # 조건: 원문 불변화 + outcome 분리 + due 추론
        for c in s.get("conditions") or []:
            if "_raw" not in c:                     # 최초 1회만 원본 보존
                c["_raw"] = c.get("text")
            if c.get("outcome") is None:
                orig, outcome = split_outcome(c.get("text"))
                if outcome:
                    c["text"] = orig
                    c["outcome"] = outcome
                    local.append(f"    · 조건 분리: {orig[:44]}… ⇢ outcome «{outcome[:40]}…»")
                else:
                    c.setdefault("outcome", None)
            c.setdefault("resolved", today if c.get("met") else None)
            if "due" not in c:
                c["due"] = infer_due(c.get("_raw") or c.get("text"), anchor)
            c.pop("desc", None) if c.get("desc") is None else None

        met_pct = calc_met_pct(s.get("conditions"))
        # status: 기존 산문은 status_note로 이관하고 status는 기계값으로
        old_status = s.get("status")
        if isinstance(old_status, str) and old_status not in STATUS_VALUES:
            s.setdefault("status_note", old_status)
        s["status"] = normalize_status(s, met_pct)
        s["met_pct"] = met_pct
        # updated: 마이그레이션 1회에 한해 텍스트 증거에서 실제 갱신일을 복원한다.
        # (_updated_backfilled 마커로 멱등 — 이후엔 사람/데스크가 갱신할 때만 바뀐다)
        if not s.get("_updated_backfilled"):
            s["updated"] = last_activity(s, anchor)
            s["_updated_backfilled"] = True
        s.setdefault("order_ids", [])
        s.setdefault("actionable", infer_actionable(s))
        s.pop("source", None) if s.get("source") is None else None

        if json.dumps(s, ensure_ascii=False, sort_keys=True) != before:
            obs = "" if s["actionable"] else " [관찰전용]"
            changes.append(f"  [{s['id']}] status={s['status']} met_pct={met_pct}%{obs}")
            changes.extend(local)

    # tasks.json orders: setup_id 필드 신설(null 허용)
    tk = _load(TASKS)
    n_order = 0
    for o in tk.get("orders") or []:
        if "setup_id" not in o:
            o["setup_id"] = None
            n_order += 1

    print(f"■ setups {len(setups)}개 정규화 · orders {n_order}건에 setup_id 필드 신설")
    for ln in changes[:60]:
        print(ln)
    if len(changes) > 60:
        print(f"    … 외 {len(changes)-60}건")

    if dry:
        print("\n(--dry-run: 저장 안 함)")
        return 0
    _save(HUNTER, hu)
    _save(TASKS, tk)
    print(f"\n💾 {os.path.relpath(HUNTER, ROOT)} · {os.path.relpath(TASKS, ROOT)} 저장")
    return 0


# ── 감사 ────────────────────────────────────────────────────────────────
def check(stale_days=14, quiet=False):
    """감사 결과를 (fails, warns)로 반환. validate_report가 이걸 재사용한다."""
    fails, warns = [], []
    if not os.path.exists(HUNTER):
        return fails, warns
    hu = _load(HUNTER)
    setups = hu.get("setups") or []
    tk = _load(TASKS) if os.path.exists(TASKS) else {}
    orders = tk.get("orders") or []
    order_ids = {str(o.get("id")) for o in orders if o.get("id")}
    linked = {str(o.get("setup_id")) for o in orders if o.get("setup_id")}
    today = today_kst()

    for s in setups:
        sid = s.get("id", "?")
        if s.get("status") in ("done", "dropped"):
            continue

        # ① 스키마 필수 필드
        for k in ("updated", "met_pct", "status"):
            if s.get(k) is None:
                fails.append(f"setup[{sid}]: 필수 필드 '{k}' 없음 — setup_schema.py --migrate")
        if s.get("status") and s["status"] not in STATUS_VALUES:
            fails.append(f"setup[{sid}]: status '{s['status']}' 비표준 (허용 {STATUS_VALUES})")

        # ② met_pct 재계산 정합
        actual = calc_met_pct(s.get("conditions"))
        if s.get("met_pct") is not None and s["met_pct"] != actual:
            fails.append(f"setup[{sid}]: met_pct {s['met_pct']}% ≠ 실제 {actual}% — 재계산 필요")

        # ③ stale
        upd = s.get("updated")
        if upd:
            try:
                gap = (today - dt.date.fromisoformat(upd)).days
                if gap >= stale_days:
                    warns.append(f"setup[{sid}]: {gap}일 미갱신(updated={upd}) — "
                                 "조건/논지 재검토 또는 done·dropped 처리")
            except ValueError:
                fails.append(f"setup[{sid}]: updated '{upd}' 날짜형식 아님")

        # ④ 기한 경과 미채점
        for c in s.get("conditions") or []:
            due = c.get("due")
            if due and not c.get("met") and not c.get("outcome"):
                try:
                    if dt.date.fromisoformat(due) < today:
                        warns.append(
                            f"setup[{sid}]: 기한 경과 미채점(due={due}) — "
                            f"«{str(c.get('text'))[:40]}…» 결과를 outcome에 기록할 것")
                except ValueError:
                    pass

        # ⑤ 발동권(≥75%)인데 오더 미배선 ← 정훈 6/28 지시의 기계화
        #    관찰 전용 셋업(actionable=false)은 애초에 오더를 안 내므로 제외.
        if actual >= 75 and s.get("status") != "fired" and s.get("actionable", True):
            ids = [i for i in (s.get("order_ids") or []) if i in order_ids]
            if not ids and sid not in linked:
                warns.append(
                    f"🎯 setup[{sid}]: 조건 {actual}% 충족(≥75%)인데 연결된 오더 없음 — "
                    "지정가 오더를 tasks.json에 등록하거나, 발동 안 하는 이유를 note에 남길 것")

        # ⑥ order_ids 무결성
        for oid in s.get("order_ids") or []:
            if oid not in order_ids:
                warns.append(f"setup[{sid}]: order_ids '{oid}'가 tasks.json에 없음")

    if not quiet:
        print("=" * 62)
        print("  셋업 조건 트래커 감사 (setup_schema.py --check)")
        print("=" * 62)
        act = [s for s in setups if s.get("status") not in ("done", "dropped")]
        print(f"\n활성 셋업 {len(act)}/{len(setups)}개 · 오더 연결 {len(linked)}건\n")
        for s in sorted(act, key=lambda x: -(x.get("met_pct") or 0)):
            mark = "🎯" if (s.get("met_pct") or 0) >= 75 else "  "
            print(f" {mark} {str(s.get('met_pct') or 0):>3}%  [{s.get('status'):8s}] "
                  f"{str(s.get('id'))[:42]:44s} upd={s.get('updated')}")
        if fails:
            print(f"\n❌ FAIL {len(fails)}")
            for m in fails:
                print(f"   ❌ {m}")
        if warns:
            print(f"\n⚠️  WARN {len(warns)}")
            for m in warns:
                print(f"   ⚠️  {m}")
        if not fails and not warns:
            print("\n✅ 결손 없음.")
        print()
    return fails, warns


def link(setup_id: str, order_id: str):
    """셋업 ↔ 오더 양방향 연결. 오더북에 들어간 것만 집행된다(8/2 교훈)."""
    hu, tk = _load(HUNTER), _load(TASKS)
    s = next((x for x in hu.get("setups") or [] if x.get("id") == setup_id), None)
    o = next((x for x in tk.get("orders") or [] if str(x.get("id")) == order_id), None)
    if not s:
        print(f"❌ setup '{setup_id}' 없음"); return 1
    if not o:
        print(f"❌ order '{order_id}' 없음"); return 1
    o["setup_id"] = setup_id
    s.setdefault("order_ids", [])
    if order_id not in s["order_ids"]:
        s["order_ids"].append(order_id)
    s["updated"] = today_kst().isoformat()
    _save(HUNTER, hu); _save(TASKS, tk)
    print(f"🔗 {setup_id} ↔ {order_id} 연결")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--migrate", action="store_true", help="새 스키마로 승격(멱등·비파괴)")
    ap.add_argument("--link", nargs=2, metavar=("SETUP_ID", "ORDER_ID"),
                    help="셋업↔오더 연결 (예: --link setup-ktg-0626 o-ktg-1)")
    ap.add_argument("--dry-run", action="store_true", help="--migrate와 함께: 저장 안 함")
    ap.add_argument("--check", action="store_true", help="감사만 수행")
    ap.add_argument("--stale-days", type=int, default=14, help="미갱신 경고 임계(기본 14일)")
    a = ap.parse_args()

    if a.link:
        return link(a.link[0], a.link[1])
    if a.migrate:
        return migrate(dry=a.dry_run)
    fails, _ = check(stale_days=a.stale_days)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
