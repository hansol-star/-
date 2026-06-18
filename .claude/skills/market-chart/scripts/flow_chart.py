#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flow_chart.py — 외국인/기관 일별 순매수·순매도 + 지수 한국어 차트 생성기 (재사용)

- 한글 폰트(NanumGothic 등) 자동 탐지·등록 → 라벨 한글 깨짐 방지.
- 종가 기준 막대(매수=초록/매도=빨강) + 특정일 '장중 vs 종가' 반전 빗금 표시 + 지수 보조축 라인.
- 데이터는 JSON으로 주입 가능(없으면 내장 기본=2026-06 외인 코스피 시리즈).

사용:
  python3 flow_chart.py [데이터.json] [출력.png]
  # 인자 없으면: 내장 2026-06 데이터 → docs/research/foreign_flow_2026-06.png

JSON 스키마(예):
{
  "title": "외국인 코스피 일별 순매수 / 순매도 (2026년 6월)",
  "subtitle": "최근 5거래일 = 순매수 4일(6/12·15·16·18) vs 순매도 1일(6/17)",
  "unit": "조원",
  "y_label": "외국인 순매수(+) / 순매도(-)  [조원]",
  "index_label": "코스피 종가",
  "footnote": "...",
  "rows": [
    {"date":"6/12\n(금)", "close_flow":2.10, "index":8123.62, "intraday_flow":null}
  ]
}
"""
import sys, os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch
import numpy as np


def set_korean_font():
    """NanumGothic 등 한글 폰트 자동 등록. 없으면 경고 후 기본 폰트."""
    prefer = ["NanumGothic", "NanumBarunGothic", "NanumSquare",
              "Noto Sans CJK KR", "Noto Sans KR", "Malgun Gothic", "AppleGothic"]
    avail = {f.name for f in fm.fontManager.ttflist}
    for name in prefer:
        if name in avail:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False  # 마이너스 깨짐 방지
            return name
    # 경로로 직접 등록 시도
    for path in ["/usr/share/fonts/truetype/nanum/NanumGothic.ttf"]:
        if os.path.exists(path):
            fm.fontManager.addfont(path)
            plt.rcParams["font.family"] = fm.FontProperties(fname=path).get_name()
            plt.rcParams["axes.unicode_minus"] = False
            return plt.rcParams["font.family"]
    plt.rcParams["axes.unicode_minus"] = False
    print("⚠️ 한글 폰트 못 찾음 — 라벨이 깨질 수 있음", file=sys.stderr)
    return None


# ── 내장 기본 데이터: 2026-06 외국인 코스피 일별 순매수(종가, 조원) ──
DEFAULT = {
    "title": "외국인 코스피 일별 순매수 / 순매도 (2026년 6월)",
    "subtitle": "최근 5거래일 = 순매수 4일(6/12·15·16·18)  vs  순매도 1일(6/17)   "
                "·   직전 24거래일 연속 순매도 -75.6조 ('셀 코리아')",
    "y_label": "외국인 순매수(+) / 순매도(-)   [조원]",
    "index_label": "코스피 종가",
    "footnote": "종가 기준(KRX·언론 교차검증): 6/12 +2.10 | 6/15 약+1.1 | 6/16 +1.53 | "
                "6/17 -0.99 | 6/18 +1.29(장중 -0.95).  6/12~18 누적 ≈ +5.0조.  "
                "장중·종가 부호 갈린 날 = 6/18 단 하루.  *투자 자문 아님",
    "rows": [
        {"date": "6/12\n(금)", "close_flow": 2.10, "index": 8123.62, "intraday_flow": None},
        {"date": "6/15\n(월)", "close_flow": 1.10, "index": 8545.98, "intraday_flow": None},
        {"date": "6/16\n(화)", "close_flow": 1.53, "index": 8726.60, "intraday_flow": None},
        {"date": "6/17\n(수)", "close_flow": -0.99, "index": 8864.24, "intraday_flow": None},
        {"date": "6/18\n(목)", "close_flow": 1.29, "index": 9063.84, "intraday_flow": -0.95},
    ],
}

GREEN, RED, BLUE = "#2e9e5b", "#d6443c", "#2b5fb0"
GREEN_D, RED_D, BLUE_D = "#1d6b3f", "#a3271f", "#21407a"


def make_chart(cfg, out_path):
    set_korean_font()
    rows = cfg["rows"]
    dates = [r["date"] for r in rows]
    close = [r["close_flow"] for r in rows]
    index = [r["index"] for r in rows]
    x = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(12, 6.8))
    colors = [GREEN if v >= 0 else RED for v in close]
    ax.bar(x, close, width=0.52, color=colors, zorder=3, edgecolor="white", linewidth=0.8)

    for xi, v in zip(x, close):
        ax.text(xi, v + (0.11 if v >= 0 else -0.11), f"{v:+.2f}조",
                ha="center", va="bottom" if v >= 0 else "top",
                fontsize=12, fontweight="bold", color=GREEN_D if v >= 0 else RED_D)

    # 장중 반전(빗금) 표시
    for xi, r in zip(x, rows):
        intr = r.get("intraday_flow")
        if intr is not None:
            ax.bar(xi, intr, width=0.52, color="none", edgecolor=RED,
                   hatch="////", linewidth=1.4, zorder=2)
            ax.annotate(f"{r['date'].splitlines()[0]} 장중 {intr:+.2f}조 매도\n→ 종가 {r['close_flow']:+.2f}조 매수\n(막판 반전)",
                        xy=(xi, intr), xytext=(xi - 0.05, intr - 1.15),
                        fontsize=10, color=RED_D, ha="center", fontweight="bold",
                        arrowprops=dict(arrowstyle="->", color=RED_D, lw=1.4))

    ax.axhline(0, color="#444", lw=1.0, zorder=4)
    ax.set_ylabel(cfg["y_label"], fontsize=12.5)
    lo = min(min(close), min([r.get("intraday_flow") or 0 for r in rows])) - 1.3
    hi = max(close) + 0.9
    ax.set_ylim(lo, hi)
    ax.set_xticks(x); ax.set_xticklabels(dates, fontsize=11)
    ax.set_axisbelow(True); ax.grid(axis="y", ls=":", color="#bbb", zorder=0)

    # 지수 보조축
    ax2 = ax.twinx()
    ax2.plot(x, index, "-o", color=BLUE, lw=2.3, ms=8, zorder=5)
    for xi, k in zip(x, index):
        ax2.text(xi, k + (hi - lo) * 6, f"{k:,.0f}", ha="center",
                 fontsize=9.5, color=BLUE_D, fontweight="bold")
    ax2.set_ylabel(cfg["index_label"], fontsize=12.5, color=BLUE_D)
    ax2.tick_params(axis="y", colors=BLUE_D)
    krange = max(index) - min(index)
    ax2.set_ylim(min(index) - krange * 0.5, max(index) + krange * 0.7)

    ax.set_title(cfg["title"], fontsize=15, fontweight="bold", pad=26)
    ax.text(0.5, 1.045, cfg["subtitle"], transform=ax.transAxes,
            ha="center", fontsize=10.5, color="#333")

    legend = [Patch(fc=GREEN, label="외국인 순매수 (종가)"),
              Patch(fc=RED, label="외국인 순매도 (종가)"),
              Patch(fc="none", ec=RED, hatch="////", label="장중 매도(반전 전)"),
              plt.Line2D([0], [0], color=BLUE, marker="o", label="코스피 종가(우축)")]
    ax.legend(handles=legend, loc="upper left", fontsize=10, framealpha=0.95)

    fig.text(0.5, 0.005, cfg["footnote"], ha="center", fontsize=8.6, color="#555")
    plt.tight_layout(rect=[0, 0.025, 1, 0.99])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print("saved", out_path)


if __name__ == "__main__":
    cfg = DEFAULT
    out = "docs/research/foreign_flow_2026-06.png"
    args = [a for a in sys.argv[1:]]
    if args and args[0].endswith(".json"):
        with open(args[0], encoding="utf-8") as f:
            cfg = json.load(f)
        args = args[1:]
    if args:
        out = args[0]
    make_chart(cfg, out)
