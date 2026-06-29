#!/usr/bin/env python3
"""
charts.py — 포트폴리오 시각화 (matplotlib PNG).

  1) 비중 파이차트 (KRW 환산 평가액 기준)
  2) 종목별 수익률 막대 (원가 대비 %)

pnl.py의 평가 결과를 그림으로. 보고서에 첨부하거나 SendUserFile로 공유.
한글 폰트가 없는 환경이 많아 라벨은 ASCII(티커)로 표기 — 본문 표가 한글명을 담당.

사용:
  python3 charts.py                 # output/charts/ 에 PNG 2개 생성, 경로 출력
  python3 charts.py --outdir DIR
"""
from __future__ import annotations

import argparse
import os

try:
    import matplotlib
    matplotlib.use("Agg")  # 헤드리스
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except ImportError:  # 웹/헤드리스에 matplotlib 없으면 차트는 스킵 (로컬 머신 이전 후 활성)
    HAVE_MPL = False

from pnl import load_cfg, eval_positions, fx_usdkrw


# 한글 폰트 없는 환경용 — 국내 종목 영문 라벨 (차트 가독성)
ROMAN = {
    "005930.KS": "Samsung", "066570.KS": "LG Elec", "454910.KS": "Doosan Robo",
    "005380.KS": "Hyundai", "035420.KS": "NAVER", "240810.KQ": "Wonik IPS",
    "095610.KQ": "Tes", "034020.KS": "Doosan Enerb", "096770.KS": "SK Innov",
}


def ascii_name(label: str, ticker: str) -> str:
    if label.isascii():
        return label
    return ROMAN.get(ticker, ticker.split(".")[0])


def main() -> int:
    ap = argparse.ArgumentParser(description="포트폴리오 차트 (matplotlib)")
    ap.add_argument("--outdir", default=os.path.join("output", "charts"))
    args = ap.parse_args()
    if not HAVE_MPL:
        print("⚠️ matplotlib 미설치 — 차트 스킵 (로컬 머신 이전 후 활성: pip install matplotlib)")
        return 0
    os.makedirs(args.outdir, exist_ok=True)

    cfg = load_cfg()
    fx = fx_usdkrw() or 0
    kr = eval_positions(cfg["holdings"]["kr"])
    us = eval_positions(cfg["holdings"]["us"])

    # KRW 환산 평가액 + 수익률 수집
    names, values, rets = [], [], []
    for r in kr:
        if r["value"] is None:
            continue
        names.append(ascii_name(r["label"], r["ticker"]))
        values.append(r["value"])
        rets.append(r["ret_pct"])
    for r in us:
        if r["value"] is None:
            continue
        names.append(ascii_name(r["label"], r["ticker"]))
        values.append(r["value"] * fx)
        rets.append(r["ret_pct"])

    cash = cfg.get("cash_krw", 0)

    # ── 1) 비중 파이 ──────────────────────────────────────────
    pie_labels = names + ["CASH"]
    pie_vals = values + [cash]
    fig1, ax1 = plt.subplots(figsize=(8, 8))
    ax1.pie(pie_vals, labels=pie_labels, autopct="%1.1f%%", startangle=90,
            textprops={"fontsize": 8}, pctdistance=0.82)
    ax1.set_title("Portfolio Allocation (KRW-converted, incl. cash)", fontsize=12)
    pie_path = os.path.join(args.outdir, "allocation_pie.png")
    fig1.tight_layout(); fig1.savefig(pie_path, dpi=120); plt.close(fig1)

    # ── 2) 수익률 막대 ────────────────────────────────────────
    order = sorted(range(len(names)), key=lambda i: rets[i])
    on = [names[i] for i in order]; orr = [rets[i] for i in order]
    colors = ["#d64545" if v < 0 else "#3a9d57" for v in orr]
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    bars = ax2.barh(on, orr, color=colors)
    ax2.axvline(0, color="#333", linewidth=0.8)
    ax2.set_xlabel("Return vs cost (%)")
    ax2.set_title("Per-position Return", fontsize=12)
    for b, v in zip(bars, orr):
        ax2.text(v + (0.4 if v >= 0 else -0.4), b.get_y() + b.get_height()/2,
                 f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right", fontsize=7)
    bar_path = os.path.join(args.outdir, "returns_bar.png")
    fig2.tight_layout(); fig2.savefig(bar_path, dpi=120); plt.close(fig2)

    print(pie_path)
    print(bar_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
