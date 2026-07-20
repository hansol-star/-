#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_dashboard.py — 포트폴리오 대시보드 HTML 생성기 (Artifact 발행용).

app/data.js(build_app_data 산출) + vol_gauge 폭풍점수를 뽑아 자체완결 HTML
대시보드로 렌더한다. matplotlib PNG(웹세션 미표시)를 대체하는 '고급' 시각화 —
히어로 KPI·안전핀·보유 비중 도넛·원가대비 수익률 발산 바·보유표(스파클라인·별점·
스코어·폭풍 pill)·지수. 다크/라이트 자동 대응. 앱과 같은 토스 디자인 토큰.

산출 HTML을 Artifact 툴로 발행하면 claude.ai 사이드패널에서 열람·공유 가능.
템플릿 = assets/dashboard_template.html(__DASH__ placeholder에 데이터 주입).

사용:
  python3 build_dashboard.py                 # → output/dashboard.html (경로 출력)
  python3 build_dashboard.py --out PATH
  python3 build_dashboard.py --no-vol         # 폭풍점수 생략(네트워크 절약·빠름)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DATA_JS = os.path.join(REPO, "app", "data.js")
TEMPLATE = os.path.join(HERE, "..", "assets", "dashboard_template.html")


def load_app_data() -> dict:
    with open(DATA_JS, encoding="utf-8") as f:
        js = f.read()
    m = re.search(r"window\.APP_DATA\s*=\s*(\{.*\})\s*;?\s*$", js, re.S)
    if not m:
        raise SystemExit("app/data.js 파싱 실패 — build_app_data.py 먼저 실행")
    return json.loads(m.group(1))


def storm_map(no_vol: bool) -> dict:
    """vol_gauge.py --json → {symbol: {storm, regime, rv}}. 실패/생략 시 빈 dict."""
    if no_vol:
        return {}
    vp = os.path.join(HERE, "vol_gauge.py")
    if not os.path.exists(vp):
        return {}
    try:
        r = subprocess.run([sys.executable, vp, "--json"], capture_output=True,
                           text=True, timeout=200, cwd=REPO)
        rows = json.loads(r.stdout)
    except Exception:
        return {}
    return {x["symbol"]: {"storm": x.get("storm_pct"), "regime": x.get("regime")}
            for x in rows if isinstance(x, dict) and x.get("symbol")}


def build_payload(app: dict, storm: dict) -> dict:
    def hpick(h):
        d = {k: h.get(k) for k in ("label", "ticker", "region", "currency", "price",
                                   "change_pct", "pnl_pct", "value_krw", "stars",
                                   "score", "spark", "outlook")}
        s = storm.get(h.get("ticker"))
        if s:
            d["storm"] = s["storm"]; d["regime"] = s["regime"]
        return d

    ks = storm.get("^KS11", {})
    indices = []
    for i in app.get("indices", []):
        row = dict(i)
        s = storm.get(i.get("ticker"))
        if s:
            row["storm"] = s["storm"]; row["regime"] = s["regime"]
        indices.append(row)

    return {
        "as_of": app.get("as_of"), "generated_at": app.get("generated_at"),
        "source_report": app.get("source_report"),
        "totals": app.get("totals"), "fx": app.get("fx"), "safety": app.get("safety"),
        "indices": indices,
        "holdings": [hpick(h) for h in app.get("holdings", [])],
        "kospi_storm": ks.get("storm"), "kospi_regime": ks.get("regime"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="포트폴리오 대시보드 HTML 생성기")
    ap.add_argument("--out", default=os.path.join(REPO, "output", "dashboard.html"))
    ap.add_argument("--no-vol", action="store_true", help="폭풍점수(vol_gauge) 생략")
    args = ap.parse_args()

    if not os.path.exists(TEMPLATE):
        raise SystemExit(f"템플릿 없음: {TEMPLATE}")
    app = load_app_data()
    payload = build_payload(app, storm_map(args.no_vol))

    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    if "__DASH__" not in html:
        raise SystemExit("템플릿에 __DASH__ placeholder 없음")
    final = html.replace("__DASH__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(final)
    n_storm = sum(1 for h in payload["holdings"] if "storm" in h)
    print(f"✅ {os.path.relpath(args.out, REPO)} 생성 "
          f"(보유 {len(payload['holdings'])}·폭풍 {n_storm}·지수 {len(payload['indices'])})")
    print("   → Artifact 툴로 발행하면 사이드패널에서 열람. content-only(doctype 없음).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
