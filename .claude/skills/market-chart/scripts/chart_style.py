#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chart_style.py — 데스크 차트 공통 스타일 (dataviz 원칙 · 검증 팔레트).

flow_chart.py·charts.py가 공유하는 색·폰트·타이포 단일 정본. "AI 슬롭" 회피 +
색맹 안전성을 눈대중이 아니라 검증으로 보장한다.

팔레트 근거(dataviz 스킬 validate_palette.js, 2026-07-19 실측):
  CATEGORICAL 8색 light 모드 → Lightness/Chroma/CVD분리/정상시야 전부 PASS
  (대비 WARN 3색은 '직접 라벨 있으면 해소' — 우리 차트는 항상 값 라벨/범례 있음).

의미별 색 배정(dataviz "color by job"):
  - 발산(diverging) = 매수/수익 POS(초록) vs 매도/손실 NEG(빨강). 금융 관습 유지.
    부호·값라벨·0선 기준 위/아래 = 3중 중복부호화 → 색맹도 식별 가능(색 단독 아님).
  - 카테고리컬(identity) = 비중 파이 등 → CATEGORICAL 고정순서(순환 금지, 8색 초과는 '기타' 병합).
  - 중립(neutral) = 지수 라인·격자·텍스트 = INK 계열(시리즈색 아님).

⚠️ dataviz 비협상 규칙 중 'dual-axis 금지'는 flow_chart의 수급+지수 콤보차트가
   금융 관습이자 정훈이 쓰는 뷰라 의도적으로 예외(보조축 유지). 나머지는 준수.
"""
from __future__ import annotations

import os
import sys

# ── 표면·텍스트(중립 잉크) ──────────────────────────────
SURFACE = "#fcfcfb"
INK = "#0b0b0b"        # text-primary
INK_2 = "#52514e"      # text-secondary (격자·부제·footnote)

# ── 발산: 매수/수익(초록) vs 매도/손실(빨강) — 기존 flow_chart 톤 유지 ──
POS, NEG = "#2e9e5b", "#d6443c"
POS_D, NEG_D = "#1d6b3f", "#a3271f"     # 값 라벨용 진한 톤

# ── 지수/보조 라인 = 중립 남색 액센트(상태색 아님) ──
INDEX_LINE, INDEX_LINE_D = "#2b5fb0", "#21407a"

# ── 카테고리컬(검증 통과·고정순서) — 파이/멀티시리즈 identity ──
CATEGORICAL = ["#2a78d6", "#008300", "#e87ba4", "#eda100",
               "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"]
OTHER_GREY = "#9a9a95"  # '기타' 슬라이스


def set_korean_font():
    """NanumGothic 등 한글 폰트 자동 등록. 없으면 None(호출측이 ASCII 폴백)."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
    except ImportError:
        return None
    prefer = ["NanumGothic", "NanumBarunGothic", "NanumSquare",
              "Noto Sans CJK KR", "Noto Sans KR", "Malgun Gothic", "AppleGothic"]
    avail = {f.name for f in fm.fontManager.ttflist}
    for name in prefer:
        if name in avail:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False
            return name
    for path in ["/usr/share/fonts/truetype/nanum/NanumGothic.ttf"]:
        if os.path.exists(path):
            fm.fontManager.addfont(path)
            plt.rcParams["font.family"] = fm.FontProperties(fname=path).get_name()
            plt.rcParams["axes.unicode_minus"] = False
            return plt.rcParams["font.family"]
    plt.rcParams["axes.unicode_minus"] = False
    print("⚠️ 한글 폰트 못 찾음 — 라벨 ASCII 폴백 권장", file=sys.stderr)
    return None


def apply_base_style():
    """공통 rcParams: 표면색·격자는 recessive(옅은 점선)·스파인 정리·유니코드 마이너스 off."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    plt.rcParams.update({
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#cccccc",
        "axes.grid": False,
        "grid.color": "#dddddd",
        "grid.linestyle": ":",
        "grid.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
    })


def merge_small(labels, values, threshold_pct=3.0, other_label="기타"):
    """작은 조각을 '기타'로 병합(dataviz: 8색 초과 identity 금지). 큰 것부터 정렬.
    반환 (labels, values) — 파이에 바로. other는 항상 마지막."""
    total = sum(v for v in values if v) or 1.0
    keep, other = [], 0.0
    for lab, val in sorted(zip(labels, values), key=lambda t: -(t[1] or 0)):
        if (val or 0) / total * 100 >= threshold_pct:
            keep.append((lab, val))
        else:
            other += (val or 0)
    out_l = [l for l, _ in keep]
    out_v = [v for _, v in keep]
    if other > 0:
        out_l.append(other_label)
        out_v.append(other)
    return out_l, out_v


def categorical(n):
    """앞 n색(고정순서). n>8이면 8색까지만(초과분은 호출측이 merge_small로 병합할 것)."""
    return (CATEGORICAL * ((n // len(CATEGORICAL)) + 1))[:n]
