#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory_embed.py — 기억 의미검색 인덱스 (bge-m3) [2026-09-01 신설 · 정훈 승인]

■ 왜 만들었나
`memory_recall.py`(8/5)는 **문자열 매칭 + 최신성**으로만 회수한다. 그래서
"메모리 정점을 언제 판정하기로 했더라" 같은 질의는 **그 단어가 안 박힌 기록을 못 찾는다.**
쌓는 쪽(원장 4종·보고서 110편·hunter 656건)은 갖췄는데 끌어올리는 쪽이 어휘에 묶여 있었다.

■ 무엇을 인덱싱하나 — **산문만. 숫자 스냅샷은 안 건다.**
  · decisions.jsonl    184건  (topic·decision·rationale·rejected)
  · missed_moves.jsonl  44건  (signal·rationale·lesson)
  · hunter_archive     656건  (title·takeaway·theme·verdict)
  · docs/reports/*.md  110편  → 마크다운 heading 단위 청크
  ✂️ **제외**: calls_log(949건)·rule_log(21건) — 티커·별점·목표가 같은 **수치 스냅샷**이라
     의미검색에 걸어봐야 노이즈만 는다. 그쪽은 기존 구조적 매칭이 이미 정확히 처리한다.
     (CLAUDE.md: calls_log는 종목×보고서 스냅샷 복제라 유효 n이 콜 수가 아니라 종목 수다.)

■ 규율 — memory_recall의 3원칙을 그대로 승계한다
  · **랭킹 전용.** 점수는 **읽을 순서**일 뿐이다. 룰·별점·트랜치 어떤 판정도 바꾸지 않는다.
  · **확증편향 방지.** 의미검색은 질의와 *닮은 것*만 올리는 성질이 있어, 놔두면
    "같은 종목의 틀린 콜·기각된 대안도 같이 끌어올린다"는 원설계를 깨뜨린다.
    ⇒ `--contra K`로 **반대 증거 슬롯을 강제 확보**한다(기각안 있는 결정 · verdict=miss 미스무브 ·
      채널 [정정] 건). 상위권이 전부 '내 생각과 맞는 기억'으로 차는 것을 구조적으로 막는다.
  · **읽기 전용.** 원장을 고치지 않는다. 인덱스는 파생물이라 언제든 재생성 가능하다.

■ 모델
  BAAI/bge-m3 (568M·1024차원·다국어). 정훈 9/1 지시 "더 정확한 거로".
  CPU로 돈다(이 머신 GTX 1060 6GB는 배치 인덱싱에 이득이 크지 않다 — 필요하면 --device cuda).
  ⚠️ 첫 실행 시 모델을 내려받는다(~2.2GB, HuggingFace 캐시).

■ 사용
  memory_embed.py --build              # 인덱스 생성/갱신
  memory_embed.py --query "메모리 정점 판정" --limit 10
  memory_embed.py --status             # 인덱스 신선도(원장 대비)
  memory_embed.py --query "..." --json # memory_recall이 소비하는 형식

인덱스: data/cache/memory_index.npz + .meta.json (gitignore — 파생물)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
APP = os.path.join(ROOT, "data", "app")
CACHE = os.path.join(ROOT, "data", "cache")
IDX = os.path.join(CACHE, "memory_index.npz")
META = os.path.join(CACHE, "memory_index.meta.json")
MODEL = "BAAI/bge-m3"

CHUNK = 1100          # 보고서 청크 상한(자) — bge-m3는 8k까지 받지만 회수 단위는 짧을수록 정확
OVERLAP = 150


def _jsonl(name):
    p = os.path.join(APP, name)
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:                              # noqa: BLE001
                    continue
    return out


def _chunks(text, size=CHUNK, overlap=OVERLAP):
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= size:
        return [text] if text else []
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + size])
        i += size - overlap
    return out


def build_corpus():
    """(text, meta) 목록. meta엔 원문으로 되돌아갈 좌표와 contra 플래그가 들어간다."""
    docs = []

    for r in _jsonl("decisions.jsonl"):
        body = " / ".join(str(x) for x in
                          [r.get("topic"), r.get("decision"), r.get("rationale"),
                           r.get("rejected"), r.get("tags")] if x)
        if not body.strip():
            continue
        docs.append((body, {
            "src": "decisions", "id": r.get("id"), "date": str(r.get("date", ""))[:10],
            "headline": r.get("topic", ""), "status": r.get("status"),
            # 기각안이 적힌 결정 = "가지 않은 길"의 기록 → 반대 증거 슬롯 후보
            "contra": bool(r.get("rejected")),
        }))

    for r in _jsonl("missed_moves.jsonl"):
        body = " / ".join(str(x) for x in
                          [r.get("ticker"), r.get("decision_type"), r.get("signal"),
                           r.get("rationale"), r.get("lesson")] if x)
        if not body.strip():
            continue
        docs.append((body, {
            "src": "missed", "id": r.get("id"), "date": str(r.get("date", ""))[:10],
            "headline": f"{r.get('ticker')} {r.get('decision_type')} -> {r.get('verdict') or '미채점'}",
            "verdict": r.get("verdict"),
            # verdict=miss = **우리가 틀렸던 판단**. 확증편향 방지의 핵심 표본이다.
            "contra": r.get("verdict") == "miss",
        }))

    hp = os.path.join(APP, "hunter_archive.json")
    if os.path.exists(hp):
        try:
            vids = json.load(open(hp, encoding="utf-8")).get("videos") or []
        except Exception:                                      # noqa: BLE001
            vids = []
        for v in vids:
            body = " / ".join(str(x) for x in
                              [v.get("title"), v.get("takeaway"), v.get("theme"),
                               v.get("tickers")] if x)
            if not body.strip():
                continue
            vd = str(v.get("verdict") or "")
            docs.append((body, {
                "src": "hunter", "id": v.get("id"), "date": str(v.get("date", ""))[:10],
                "headline": (v.get("title") or "")[:80], "verdict": vd or None,
                # [정정] = 채널이 틀렸던 건. 채널 과신을 견제하는 표본.
                "contra": "정정" in vd,
            }))

    for p in sorted(glob.glob(os.path.join(ROOT, "docs", "reports", "report_v*.md"))):
        base = os.path.basename(p)
        m = re.search(r"(\d{4}-\d{2}-\d{2})", base)
        d = m.group(1) if m else ""
        try:
            raw = open(p, encoding="utf-8").read()
        except Exception:                                      # noqa: BLE001
            continue
        # heading 단위로 먼저 자른 뒤 길면 추가 분할 — 문맥 경계를 살린다
        parts = re.split(r"\n(?=#{1,3} )", raw)
        for part in parts:
            head = part.lstrip("#").strip().split("\n", 1)[0][:70]
            for ch in _chunks(part):
                docs.append((ch, {"src": "report", "id": base, "date": d,
                                  "headline": head, "contra": False}))
    return docs


def meta_path(root=None):
    """인덱스 메타 경로. **root를 받는 이유** = 가드 주입 테스트가 임시 ROOT로 검증하려면
    모듈 상수(절대경로)에 묶여 있으면 안 된다(9/1 실측 — 첫 등록이 이것 때문에 실패했다)."""
    return META if root is None else os.path.join(root, "data", "cache", "memory_index.meta.json")


def _fingerprint(root=None):
    """원장 상태 지문 — 인덱스가 낡았는지 판정하는 근거."""
    root = root or ROOT
    app = os.path.join(root, "data", "app")
    fp = {}
    for n in ("decisions.jsonl", "missed_moves.jsonl", "hunter_archive.json"):
        p = os.path.join(app, n)
        fp[n] = os.path.getsize(p) if os.path.exists(p) else 0
    reports = sorted(glob.glob(os.path.join(root, "docs", "reports", "report_v*.md")))
    fp["reports_n"] = len(reports)
    fp["reports_bytes"] = sum(os.path.getsize(x) for x in reports)
    fp["hash"] = hashlib.sha1(json.dumps(fp, sort_keys=True).encode()).hexdigest()[:12]
    return fp


def _model(device=None):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        sys.exit("sentence-transformers 미설치 — pip install sentence-transformers\n"
                 "   (의존성 정책 예외: 정훈 9/1 승인. 없으면 memory_recall은 "
                 "키워드 경로로만 동작하며 그 사실을 출력한다)")
    return SentenceTransformer(MODEL, device=device)


def build(device=None, quiet=False):
    import numpy as np
    docs = build_corpus()
    if not docs:
        sys.exit("인덱싱할 문서가 없다 — 원장 경로 확인")
    texts = [t for t, _ in docs]
    metas = [m for _, m in docs]
    if not quiet:
        by = {}
        for m in metas:
            by[m["src"]] = by.get(m["src"], 0) + 1
        print(f"코퍼스 {len(texts):,}청크 — " + " · ".join(f"{k} {v}" for k, v in sorted(by.items())))
        print(f"모델 로딩 {MODEL} (첫 실행이면 ~2.2GB 다운로드)...")
    mdl = _model(device)
    emb = mdl.encode(texts, batch_size=16, normalize_embeddings=True,
                     show_progress_bar=not quiet, convert_to_numpy=True)
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(IDX, emb=emb.astype("float16"))
    json.dump({"model": MODEL, "n": len(texts), "dim": int(emb.shape[1]),
               "metas": metas, "texts": [t[:400] for t in texts],
               "fingerprint": _fingerprint()},
              open(META, "w", encoding="utf-8"), ensure_ascii=False)
    if not quiet:
        print(f"인덱스 저장 — {len(texts):,}청크 x {emb.shape[1]}차원 "
              f"({os.path.getsize(IDX)/1e6:.1f}MB) -> {IDX}")
    return 0


def load():
    import numpy as np
    if not (os.path.exists(IDX) and os.path.exists(META)):
        return None, None
    meta = json.load(open(META, encoding="utf-8"))
    emb = np.load(IDX)["emb"].astype("float32")
    return emb, meta


def status(as_json=False):
    emb, meta = load()
    cur = _fingerprint()
    if meta is None:
        st = {"exists": False, "stale": True, "reason": "인덱스 없음 — memory_embed.py --build"}
    else:
        old = meta.get("fingerprint", {})
        stale = old.get("hash") != cur["hash"]
        st = {"exists": True, "stale": stale, "n": meta.get("n"),
              "model": meta.get("model"),
              "reason": ("원장이 인덱스보다 새롭다 — --build로 갱신"
                         f" (보고서 {old.get('reports_n')}->{cur['reports_n']}편)"
                         if stale else "최신")}
    if as_json:
        print(json.dumps(st, ensure_ascii=False))
    else:
        icon = "OK" if (st["exists"] and not st["stale"]) else "STALE"
        print(f"[{icon}] 의미검색 인덱스 — {st['reason']}"
              + (f" · {st.get('n'):,}청크 · {st.get('model')}" if st["exists"] else ""))
    return 0 if (st["exists"] and not st["stale"]) else 1


class NotIndexed(RuntimeError):
    """인덱스가 없다 = **검색을 못 했다**. '결과 0건'과 절대 같지 않다.

    memory_recall이 이 예외를 잡아 "의미검색 미수행"을 화면에 명시한다 —
    빈 리스트로 내리면 호출자가 '관련 기억이 없다'로 오독한다
    (8/22 "가드 없는 폴백은 침묵보다 나쁘다").
    """


def search(q, limit=10, contra=2, device=None):
    """의미검색 결과를 **반환**한다(출력 없음). memory_recall이 이걸 쓴다."""
    import numpy as np
    emb, meta = load()
    if emb is None:
        raise NotIndexed("인덱스 없음 — memory_embed.py --build 필요")
    qv = _model(device).encode([q], normalize_embeddings=True, convert_to_numpy=True)[0]
    sims = emb @ qv.astype("float32")
    order = np.argsort(-sims)

    metas, texts = meta["metas"], meta["texts"]
    picked, seen = [], set()
    for i in order:
        i = int(i)
        key = (metas[i]["src"], metas[i].get("id"), metas[i].get("headline"))
        if key in seen:
            continue
        seen.add(key)
        picked.append(i)
        if len(picked) >= limit:
            break

    # 반대 증거 슬롯 — 상위권이 '내 생각과 맞는 기억'으로만 차는 걸 막는다
    if contra > 0:
        have = sum(1 for i in picked if metas[i].get("contra"))
        need = max(0, contra - have)
        if need:
            for i in order:
                i = int(i)
                if need <= 0:
                    break
                if i in picked or not metas[i].get("contra"):
                    continue
                picked.append(i)
                need -= 1

    return [{"score": round(float(sims[i]), 4), "src": metas[i]["src"],
             "id": metas[i].get("id"), "date": metas[i].get("date"),
             "headline": metas[i].get("headline"), "contra": bool(metas[i].get("contra")),
             "text": texts[i]} for i in picked]


def query(q, limit=10, contra=2, device=None, as_json=False):
    try:
        hits = search(q, limit, contra, device)
    except NotIndexed as e:
        # 조용히 빈 결과를 주지 않는다 — "찾은 게 없다"와 "찾아보지 못했다"는 다르다.
        if as_json:
            print(json.dumps({"error": str(e), "hits": []}, ensure_ascii=False))
        else:
            print(f"[미수행] {e} (의미검색 안 함)", file=sys.stderr)
        return 3
    if as_json:
        print(json.dumps({"query": q, "hits": hits}, ensure_ascii=False, indent=1))
        return 0
    LBL = {"decisions": "결정", "missed": "미스무브", "hunter": "채널", "report": "보고서"}
    print(f"의미검색 <{q}> — {len(hits)}건 (* = 반대 증거 슬롯)")
    print("=" * 78)
    for h in hits:
        flag = " *" if h["contra"] else ""
        print(f"  {h['score']:.3f} {LBL.get(h['src'], h['src']):<8} {h['date']}{flag}  {h['headline']}")
        print(f"        {h['text'][:160].replace(chr(10), ' ')}")
    print("\n주의: 점수는 **읽을 순서**일 뿐 그 판단이 옳았다는 뜻이 아니다.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="기억 의미검색 인덱스 (bge-m3) — 랭킹 전용")
    ap.add_argument("--build", action="store_true", help="인덱스 생성/갱신")
    ap.add_argument("--query", help="의미검색 질의")
    ap.add_argument("--status", action="store_true", help="인덱스 신선도")
    ap.add_argument("--limit", type=int, default=10, help="표시 건수")
    ap.add_argument("--contra", type=int, default=2,
                    help="반대 증거(기각안·miss·정정) 최소 확보 건수 (기본 2·0이면 끔)")
    ap.add_argument("--device", help="cpu / cuda (기본 자동)")
    ap.add_argument("--json", action="store_true", help="기계 소비용")
    ap.add_argument("-q", "--quiet", action="store_true", help="진행 표시 없이")
    a = ap.parse_args()
    if a.build:
        return build(a.device, a.quiet)
    if a.status:
        return status(a.json)
    if a.query:
        return query(a.query, a.limit, a.contra, a.device, a.json)
    ap.error("--build · --query · --status 중 하나가 필요하다")


if __name__ == "__main__":
    sys.exit(main())
