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
import sys

try:
    import matplotlib
    matplotlib.use("Agg")  # 헤드리스
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except ImportError:  # 웹/헤드리스에 matplotlib 없으면 차트는 스킵 (로컬 머신 이전 후 활성)
    HAVE_MPL = False

from pnl import load_cfg, eval_positions, fx_usdkrw

# 공통 스타일 정본(dataviz 검증 팔레트·한글폰트) — market-chart/scripts/chart_style.
_CS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "..", "market-chart", "scripts"))
sys.path.insert(0, _CS_DIR)
try:
    import chart_style as CS
except ImportError:  # 폴백: 스타일 모듈 못 찾아도 차트는 생성(기본 색)
    CS = None


# 한글 폰트 없는 환경용 — 국내 종목 영문 라벨 (차트 가독성 폴백)
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

    # 공통 스타일: 한글 폰트 등록(있으면 한글 라벨, 없으면 ASCII 폴백) + recessive rcParams
    use_kr = False
    if CS is not None:
        use_kr = CS.set_korean_font() is not None
        CS.apply_base_style()
    POS = CS.POS if CS else "#2e9e5b"
    NEG = CS.NEG if CS else "#d6443c"

    def disp(label, ticker):
        return label if use_kr else ascii_name(label, ticker)

    cfg = load_cfg()
    fx = fx_usdkrw() or 0
    kr = eval_positions(cfg["holdings"]["kr"])
    us = eval_positions(cfg["holdings"]["us"])

    # KRW 환산 평가액 + 수익률 수집
    names, values, rets = [], [], []
    for r in kr:
        if r["value"] is None:
            continue
        names.append(disp(r["label"], r["ticker"]))
        values.append(r["value"])
        rets.append(r["ret_pct"])
    for r in us:
        if r["value"] is None:
            continue
        names.append(disp(r["label"], r["ticker"]))
        values.append(r["value"] * fx)
        rets.append(r["ret_pct"])

    cash = cfg.get("cash_krw", 0)
    cash_label = "현금" if use_kr else "CASH"

    # ── 1) 비중 파이 (dataviz: 3% 미만은 '기타' 병합·고정순서 팔레트) ──────
    hold_labels, hold_vals = (CS.merge_small(names, values, 3.0,
                              "기타" if use_kr else "ETC") if CS else (names, values))
    pie_labels = hold_labels + [cash_label]
    pie_vals = hold_vals + [cash]
    if CS:
        other_l = "기타" if use_kr else "ETC"
        pie_colors = []
        ci = 0
        for lab in hold_labels:
            if lab == other_l:
                pie_colors.append(CS.OTHER_GREY)
            else:
                pie_colors.append(CS.CATEGORICAL[ci % len(CS.CATEGORICAL)]); ci += 1
        pie_colors.append("#b8b8b3")  # 현금 = 중립 회색
    else:
        pie_colors = None
    title1 = ("포트폴리오 비중 (KRW 환산·현금 포함)" if use_kr
              else "Portfolio Allocation (KRW-converted, incl. cash)")
    fig1, ax1 = plt.subplots(figsize=(8, 8))
    ax1.pie(pie_vals, labels=pie_labels, autopct="%1.1f%%", startangle=90,
            colors=pie_colors, textprops={"fontsize": 9},
            wedgeprops={"edgecolor": "white", "linewidth": 1.5}, pctdistance=0.82)
    ax1.set_title(title1, fontsize=13, fontweight="bold")
    pie_path = os.path.join(args.outdir, "allocation_pie.png")
    fig1.tight_layout(); fig1.savefig(pie_path, dpi=120); plt.close(fig1)

    # ── 2) 수익률 막대 (발산: 수익 초록/손실 빨강 + 직접 라벨) ──────────────
    order = sorted(range(len(names)), key=lambda i: rets[i])
    on = [names[i] for i in order]; orr = [rets[i] for i in order]
    colors = [NEG if v < 0 else POS for v in orr]
    title2 = "종목별 수익률 (원가 대비)" if use_kr else "Per-position Return"
    xlab = "원가 대비 수익률 (%)" if use_kr else "Return vs cost (%)"
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    bars = ax2.barh(on, orr, color=colors)
    ax2.axvline(0, color=(CS.INK_2 if CS else "#333"), linewidth=1.0)
    ax2.set_xlabel(xlab)
    ax2.set_title(title2, fontsize=13, fontweight="bold")
    ax2.grid(axis="x", ls=":", color="#dddddd", zorder=0); ax2.set_axisbelow(True)
    for b, v in zip(bars, orr):
        ax2.text(v + (0.4 if v >= 0 else -0.4), b.get_y() + b.get_height()/2,
                 f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right",
                 fontsize=8, color=(CS.POS_D if v >= 0 else CS.NEG_D) if CS else "#333")
    bar_path = os.path.join(args.outdir, "returns_bar.png")
    fig2.tight_layout(); fig2.savefig(bar_path, dpi=120); plt.close(fig2)

    print(pie_path)
    print(bar_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
