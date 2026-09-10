"""보고서 세션 컨텍스트 브리프 — 복원 단계를 호출 1번으로. (읽기 전용)

★[2026-09-10 신설] 왜 필요한가 — 9/10 R2 실측.
  어제(9/9) 데스크 쪽을 절반으로 줄였는데(서브에이전트 2.77M → 1.37M) R2 합계는 -9%에 그쳤다.
  **메인 세션이 59턴 → 94턴으로 늘어 절감분을 도로 먹었다.** 턴마다 평균 23만 토큰을 다시 읽으므로
  메인의 턴 하나가 곧 비용이다. 늘어난 턴의 정체:
    · 직전 보고서 **전문** Read(2만 자) — 필요한 건 STATE SNAPSHOT뿐
    · tasks.json **전체** Read(3만 자) — 오더 43건 중 활성은 소수, 나머지는 종결 이력
    · stocks.json 5회 · master.md 4회 **반복** Read
  ⇒ 복원에 필요한 것만 한 화면으로 뽑는다. 원본 파일은 **수정할 때만** 해당 구간을 연다.

출력:
  ① 직전 보고서 STATE SNAPSHOT (전문 아님)
  ② tasks.json — 미완 할일(today/week/month) + **활성 오더만**(종결·폐기·체결 제외)
  ③ 보유 14 + 워치 — 별점·스코어·목표·매수존·트림 한 줄씩 (코멘트·이슈 이력 제외)

사용:
  python3 .claude/skills/portfolio-desk/scripts/r2_brief.py
  python3 .claude/skills/portfolio-desk/scripts/r2_brief.py --no-watch     # 워치 생략
  python3 .claude/skills/portfolio-desk/scripts/r2_brief.py --all-orders   # 종결 오더까지
"""
import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
REPORTS = os.path.join(ROOT, "docs", "reports")
TASKS = os.path.join(ROOT, "data", "app", "tasks.json")
STOCKS = os.path.join(ROOT, "data", "app", "stocks.json")

# 오더 status는 자유 서술이다 — 첫머리 표지로 종결을 가른다. 애매하면 **활성으로 남긴다**
# (활성을 종결로 오판해 숨기는 쪽이 반대보다 위험하다 — 8/2 '산문에만 있던 오더' 교훈).
CLOSED = re.compile(r"^\s*(✅|⚪|🟢|❌|체결|폐기|확인 완료|\*\*체결)")


def _clip(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    s = s.replace("**", "")
    return s if len(s) <= n else s[: n - 1] + "…"


def latest_report():
    best = None
    for p in glob.glob(os.path.join(REPORTS, "report_v*.md")):
        m = re.match(r"report_v(\d+)(?:\.(\d+))?_(\d{4}-\d{2}-\d{2})\.md$", os.path.basename(p))
        if not m:
            continue  # _night 등 부록 제외
        key = (int(m.group(1)), int(m.group(2) or 0))
        if best is None or key > best[0]:
            best = (key, p)
    return best[1] if best else None


def snapshot_block(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    start = next((i for i, l in enumerate(lines) if "STATE SNAPSHOT" in l and l.lstrip().startswith("[")), None)
    if start is None:
        start = next((i for i, l in enumerate(lines) if "STATE SNAPSHOT" in l), None)
    if start is None:
        return None
    out = []
    for l in lines[start:]:
        if l.startswith("*투자 자문 아님"):
            break
        out.append(l)
    return "\n".join(out).rstrip()


def main():
    ap = argparse.ArgumentParser(description="보고서 세션 컨텍스트 브리프(읽기 전용)")
    ap.add_argument("--no-watch", action="store_true", help="워치리스트 생략")
    ap.add_argument("--all-orders", action="store_true", help="종결 오더까지 출력")
    a = ap.parse_args()

    rp = latest_report()
    print("=" * 72)
    print(f"① 직전 보고서: {os.path.relpath(rp, ROOT) if rp else '없음'}")
    print("=" * 72)
    snap = snapshot_block(rp) if rp else None
    print(snap or "⚠️ STATE SNAPSHOT 블록을 못 찾음 — 보고서 끝부분을 직접 열 것")

    try:
        t = json.load(open(TASKS, encoding="utf-8"))
    except Exception as e:
        t = None
        print(f"\n⚠️ tasks.json 읽기 실패: {e}")
    if t:
        print("\n" + "=" * 72)
        print(f"② tasks.json (updated {t.get('updated')} · as_of {t.get('as_of')} · 원천 {t.get('source_report')})")
        print("=" * 72)
        if t.get("today_note"):
            print("메모:", _clip(t["today_note"], 220))
        for bucket, items in (t.get("tasks") or {}).items():
            open_items = [x for x in items if not x.get("done")]
            print(f"[{bucket}] 미완 {len(open_items)}/{len(items)}")
            for x in open_items:
                print(f"   - {x.get('id')}: {_clip(x.get('text'), 150)}")
        orders = t.get("orders") or []
        act = orders if a.all_orders else [o for o in orders if not CLOSED.match(str(o.get("status", "")))]
        print(f"[orders] {'전체' if a.all_orders else '활성'} {len(act)}/{len(orders)}건"
              f"{'' if a.all_orders else ' (종결·체결·폐기 숨김 — --all-orders)'}")
        for o in act:
            px = o.get("price")
            qty = o.get("shares")
            amt = o.get("amount_krw")
            spec = " · ".join(str(v) for v in (f"@{px}" if px not in (None, "") else None,
                                               (f"{qty}주" if isinstance(qty, (int, float)) else _clip(qty, 30))
                                               if qty not in (None, "") else None,
                                               f"{amt:,}원" if isinstance(amt, (int, float)) else None) if v)
            print(f"   - {o.get('id')} | {o.get('ticker')} {o.get('action')} {spec} | {o.get('date')}")
            print(f"       상태: {_clip(o.get('status'), 140)}")

    try:
        s = json.load(open(STOCKS, encoding="utf-8"))
    except Exception as e:
        s = None
        print(f"\n⚠️ stocks.json 읽기 실패: {e}")
    if s:
        print("\n" + "=" * 72)
        print(f"③ 종목 등급 (stocks.json as_of {s.get('as_of')}) — 별점·스코어·목표·매수존·트림")
        print("=" * 72)
        for tk, e in (s.get("stocks") or {}).items():
            print(f"{tk:10s} ⭐{e.get('stars')} {e.get('score')} [{e.get('outlook','')}] 목표 {_clip(e.get('target'), 48)}")
            print(f"{'':10s} 매수존 {_clip(e.get('buy_zone'), 110)}")
            print(f"{'':10s} 트림 {_clip(e.get('trim'), 110)}")
        if not a.no_watch:
            wl = s.get("watchlist") or {}
            print(f"-- 워치 {len(wl)}")
            for tk, e in wl.items():
                print(f"{tk:10s} ⭐{e.get('stars')} {e.get('score')} {_clip(e.get('label'), 14)} "
                      f"목표 {_clip(e.get('target'), 40)} · 가격 {e.get('price')}")

    print("\n※ 원본 파일은 **수정할 때만** 해당 구간을 연다(offset/limit·Grep). 같은 파일 재독 금지.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
