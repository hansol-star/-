#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cli_common.py — 데스크 스크립트 공용 CLI 헬퍼 (stdlib 전용)

왜 있나 [8/2 신설] — 오디텍(080520) 조사에서 도구 호출 20여 회 중 2회가
'종목을 어떻게 지정하는가'에서 깨졌다. 원인은 두 가지 표류였다:

  ① 인자 이름이 6종으로 갈라짐
     --tickers(20개) / --symbol(4) / --symbols(2) / --code(5) / --codes(1) / --ticker(1)
     → drawdown_history.py --tickers 가 거부됨. 어느 스크립트가 뭘 받는지 외울 수 없다.
  ② 구분자가 쉼표 전용
     → market_data.py --tickers ^KS11 ^KQ11 이 거부됨(공백 구분).

여기서 이름을 통일하는 게 아니라 **--tickers 를 어디서나 통하는 별칭**으로 깔고,
구분자를 쉼표·공백 모두 받게 한다. 기존 인자명은 그대로 살아 있으므로
과거 호출·문서·에이전트 파일은 전부 그대로 동작한다(순수 additive).
"""
from __future__ import annotations

import re

_SEP = re.compile(r"[,\s]+")


def split_tickers(value) -> list[str]:
    """'A,B' · 'A B' · 'A, B' · ['A','B'] · None → ['A','B'] / []

    쉼표 전용이던 파싱을 공백까지 받게 넓힌 것. 셸에서 따옴표로 묶어 넘긴
    '^KS11 ^KQ11' 같은 입력이 통째로 한 심볼로 잡히던 걸 막는다.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for v in value:
            parts.extend(split_tickers(v))
        return parts
    return [t for t in _SEP.split(str(value).strip()) if t]


def add_tickers(ap, *names, help: str = "", **kw):
    """종목 지정 인자를 등록하면서 --tickers 별칭을 항상 함께 깐다.

        add_tickers(ap, "--symbol", help="한 종목만 상세")
        → --symbol 로도, --tickers 로도 받는다 (dest 는 첫 이름 = symbol 유지)

    dest가 바뀌지 않으므로 호출부(args.symbol)를 건드릴 필요가 없다.
    """
    names = tuple(names) or ("--tickers",)
    opts = list(names) + (["--tickers"] if "--tickers" not in names else [])
    if help:
        # argparse는 help 문자열을 %-포매팅한다 — 리터럴 %는 반드시 %%로.
        # (미이스케이프 %가 --help를 죽인 사고가 2026-08-02에 3건 있었다.)
        kw["help"] = help
    return ap.add_argument(*opts, **kw)
