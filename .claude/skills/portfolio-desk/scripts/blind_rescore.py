#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blind_rescore.py — 블라인드 재채점 패킷 (측정 전용 · 어떤 룰·별점도 자동으로 바꾸지 않는다)

★[2026-09-30 신설 — 정훈 승인 TASK J]

[왜 만들었나 — 채점자가 답을 알고 채점한다]
우리 데스크는 종목을 채점할 때 **이름·보유 여부·직전 별점을 전부 알고** 채점한다.
LLM은 첫 판단에 매달린다(arXiv 2507.20957 — 확증 편향). 그러면 ⭐5 종목은 ⭐5로 남고,
'우리가 들고 있다'는 사실이 점수에 스며든다(보유 프리미엄). 외부 선례 ai-hedge-fund도
에이전트 프롬프트를 블라인드로 돌린다.
⇒ 이름·티커·지역·통화·절대규모·섹터·회계연도 날짜를 지운 **비율만의 패킷**을 만들어
   별도 채점자에게 주고, 그 점수를 현행 스코어와 나란히 놓는다. |Δ|가 큰 종목이
   **앵커링 의심 목록**이다.

[무엇을 넣고 무엇을 빼나]
  넣는다: 최근 3개 회계연도(FY-0/FY-1/FY-2) 마진·ROE·성장률·재고 대 매출·희석·레버리지,
          최근 분기(상대 월차 lag_m만), EPS 리비전·컨센 상승여력(있을 때), P/E(있을 때),
          가격 추세(MA50/MA200·52주 고점 대비·3M/12M).
  뺀다:   이름·티커·지역·통화·절대 매출/시총·섹터 단어·회계연도 종료일(달력이 신원을 흘린다).
  → 빌드 끝에 **누출 스캔**을 돌려 이름·티커·통화 토큰이 한 개라도 남으면 실패한다(exit 2).

[매핑은 레포 밖에 둔다]
채점자는 레포를 읽을 수 있다. id→티커 매핑이 레포 안에 있으면 블라인드가 아니다.
⇒ 매핑 경로가 레포 안이면 **쓰기를 거부**한다.

⚠️ 한계 — 반드시 같이 읽을 것
  · 숫자 자체가 신원을 흘린다(영업마진 60%·EPS +1,356%는 사실상 지문). 그래서 채점자에게
    `recognized`를 정직하게 적게 하고, 인식한 패킷과 못 한 패킷의 Δ를 따로 본다.
  · 블라인드 점수엔 해자·촉매·경영진·규제 같은 정성 정보가 없다 → **점검 도구이지 대체물이 아니다.**
  · 정보가 비대칭이다: EPS 리비전은 보유 종목만, 컨센은 미국 종목만 있다.
  · |Δ|≥15는 **재검토 신호**다. 스코어 변경은 여전히 PM 판단·보고서 사안이다.

사용:
  python .claude/skills/portfolio-desk/scripts/blind_rescore.py --build [--date 2026-09-30] [--mapping-out PATH]
  python .claude/skills/portfolio-desk/scripts/blind_rescore.py --compare RESULTS.json [--mapping PATH] [--out MD]
  python .claude/skills/portfolio-desk/scripts/blind_rescore.py --selftest   # 가드 자가검증(파일 안 씀)
"""
import argparse
import csv
import json
import math
import os
import random
import re
import sys
import tempfile
from datetime import date as _date, datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
APP = os.path.join(ROOT, "data", "app")
HIST = os.path.join(ROOT, "data", "history")
BLIND_DIR = os.path.join(ROOT, "data", "research", "blind")
DOCS_RESEARCH = os.path.join(ROOT, "docs", "research")
SKILL_DEEPDIVE = os.path.join(ROOT, ".claude", "skills", "stock-deepdive", "SKILL.md")

KST = timezone(timedelta(hours=9), "KST")
ETFS = {"VOO", "SPY", "QQQ", "IVV", "VTI"}   # ETF는 재무제표 채점 대상이 아니다
FLAG_BIG = 15                                  # |Δ| 재검토 문턱
PE_SANE = (2.5, 400.0)                         # 밖이면 단위·통화 불일치 의심 → 버린다(TSM ADR=TWD EPS 실측)

# 누출 스캔용 일반 토큰 — 지역·통화·거래소는 이름이 없어도 신원을 절반 흘린다.
GENERIC_LEAK = r"\b(KRW|USD|TWD|KR|US|KOSPI|KOSDAQ|NASDAQ|NYSE|ADR|KS|KQ)\b"


def _recog(v) -> bool:
    """채점자 보고를 bool로. 워크플로 스키마는 'none'/'guess'/'confident' 문자열을 쓴다 —
    bool('none')이 True가 되어 미인식 3건이 '인식'으로 잡혔다(9/30 첫 실행)."""
    if isinstance(v, str):
        return v.strip().lower() in ("guess", "confident", "true", "yes", "y")
    return bool(v)


def kst_today():
    return datetime.now(KST).strftime("%Y-%m-%d")


def default_mapping_path(d):
    # 레포 밖 OS 임시 폴더 — 채점 서브에이전트가 레포를 뒤져도 못 찾게.
    return os.path.join(tempfile.gettempdir(), "portfolio_desk_blind", f"blind_mapping_{d}.json")


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _inside_repo(path):
    a = os.path.normcase(os.path.realpath(path))
    r = os.path.normcase(os.path.realpath(ROOT))
    try:
        return os.path.commonpath([a, r]) == r
    except ValueError:        # 다른 드라이브 = 레포 밖
        return False


def _r(x, nd=1):
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return round(x, nd)


def _pct(frac, nd=1):
    """financials.json의 마진·ROE는 소수(0.60) — 패킷은 전부 % 단위로 통일한다."""
    return None if frac is None else _r(float(frac) * 100, nd)


def _d(s):
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


# ───────────────────────── 후보 ─────────────────────────
def candidates():
    """보유(ETF 제외) + 활성 워치 중 financials.json에 재무가 있는 종목."""
    st = _load(os.path.join(APP, "stocks.json"))
    fin = _load(os.path.join(APP, "financials.json")).get("stocks", {})
    out, skipped = [], []
    for grp, key in (("holding", "stocks"), ("watch", "watchlist")):
        for tk, s in (st.get(key) or {}).items():
            if tk in ETFS:
                skipped.append((tk, "ETF"))
                continue
            if tk not in fin or not fin[tk].get("annual"):
                skipped.append((tk, "financials.json 미수록"))
                continue
            out.append({"ticker": tk, "group": grp,
                        "label": s.get("label") or s.get("name") or fin[tk].get("name") or tk,
                        "score": s.get("score"), "stars": s.get("stars")})
    return out, skipped, st, fin


# ───────────────────────── 가격 추세 ─────────────────────────
def load_closes(tk):
    p = os.path.join(HIST, tk.replace("^", "_") + ".csv")
    if not os.path.exists(p):
        return []
    rows = []
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                c = float(r["close"])
            except (KeyError, TypeError, ValueError):
                continue
            if c > 0:
                rows.append(c)
    return rows


def price_trend(closes):
    if len(closes) < 60:
        return {}, None
    px = closes[-1]
    ma = lambda n, end=None: (sum(closes[-n:] if end is None else closes[-n - end:-end]) / n) \
        if len(closes) >= n + (end or 0) else None
    ma50, ma200 = ma(50), ma(200)
    ma200_prev = ma(200, 21)
    w = closes[-252:]
    hi, lo = max(w), min(w)
    ret = lambda n: (px / closes[-1 - n] - 1) * 100 if len(closes) > n else None
    t = {
        "price_vs_ma50_pct": _r((px / ma50 - 1) * 100) if ma50 else None,
        "price_vs_ma200_pct": _r((px / ma200 - 1) * 100) if ma200 else None,
        "ma50_vs_ma200_pct": _r((ma50 / ma200 - 1) * 100) if (ma50 and ma200) else None,
        "ma200_slope_1m_pct": _r((ma200 / ma200_prev - 1) * 100, 2) if (ma200 and ma200_prev) else None,
        "pct_from_52w_high": _r((px / hi - 1) * 100),
        "pct_above_52w_low": _r((px / lo - 1) * 100),
        "ret_3m_pct": _r(ret(63)),
        "ret_12m_pct": _r(ret(252)),
    }
    return t, px


# ───────────────────────── 밸류 ─────────────────────────
def _consecutive(qs):
    return all(80 <= (_d(qs[i]["end"]) - _d(qs[i + 1]["end"])).days <= 100 for i in range(len(qs) - 1))


def ttm_eps(e):
    """TTM EPS — ①연속 4분기 합 ②FY-0 + (이후 분기) − (전년 동기) 롤포워드. 둘 다 안 되면 None.
    EDGAR는 Q4 단독 분기를, 국내 Yahoo는 Q4·전년 Q1을 자주 비워서 ①만으론 대부분 실패한다."""
    qs = sorted([q for q in e.get("quarterly") or [] if q.get("eps_diluted") is not None],
                key=lambda q: q["end"], reverse=True)
    if len(qs) >= 4 and _consecutive(qs[:4]):
        return sum(q["eps_diluted"] for q in qs[:4]), "TTM(연속 4분기)"
    ann = [a for a in e.get("annual") or [] if a.get("eps_diluted") is not None]
    if not ann:
        return None, None
    fy0 = ann[0]
    after = [q for q in qs if _d(q["end"]) > _d(fy0["end"])]
    prior = []
    for q in after:
        tgt = _d(q["end"]) - timedelta(days=364)
        m = [p for p in qs if abs((_d(p["end"]) - tgt).days) <= 20]
        if not m:
            return None, None
        prior.append(m[0])
    return fy0["eps_diluted"] + sum(q["eps_diluted"] for q in after) - sum(p["eps_diluted"] for p in prior), \
        ("TTM(FY-0 롤포워드)" if after else "TTM(FY-0 직후)")


def _pe(px, eps):
    if px is None or eps is None:
        return None, None
    if eps <= 0:
        return None, "적자"
    pe = px / eps
    if pe > PE_SANE[1]:
        return f">{PE_SANE[1]:.0f}", None          # 이익이 미미한 진짜 고P/E — 버리지 않고 상한 표기
    if pe < PE_SANE[0]:
        return None, "산출 불가(데이터 정합 실패)"  # 가격·EPS 단위 불일치(외화 EPS 등) 의심
    return _r(pe), None


def valuation(e, px, rev_row):
    v, notes = {}, []
    if rev_row and rev_row.get("cur") is not None:
        pe, why = _pe(px, rev_row["cur"])
        v["pe_fwd_next_fy"] = pe
        if why:
            notes.append(f"선행 P/E {why}")
    eps, basis = ttm_eps(e)
    if eps is not None:
        pe, why = _pe(px, eps)
        v["pe_ttm"] = pe
        if why:
            notes.append(f"TTM P/E {why}")
    else:
        ann = [a for a in e.get("annual") or [] if a.get("eps_diluted") is not None]
        if ann:
            pe, why = _pe(px, ann[0]["eps_diluted"])
            v["pe_fy0"] = pe
            basis = "FY-0 EPS(TTM 산출 불가)"
            if why:
                notes.append(f"FY-0 P/E {why}")
    qs = sorted([q for q in e.get("quarterly") or [] if q.get("eps_diluted") is not None],
                key=lambda q: q["end"], reverse=True)
    if qs:
        pe, why = _pe(px, qs[0]["eps_diluted"] * 4)
        v["pe_runrate_q0x4"] = pe
        if why:
            notes.append(f"런레이트 P/E {why}")
    if basis:
        v["pe_trailing_basis"] = basis
    return {k: x for k, x in v.items() if x is not None}, notes


# ───────────────────────── 패킷 ─────────────────────────
ANNUAL_KEYS = [("op_margin_pct", "op_margin", True), ("gross_margin_pct", "gross_margin", True),
               ("fcf_margin_pct", "fcf_margin", True), ("roe_pct", "roe", True),
               ("revenue_yoy_pct", "revenue_yoy", False), ("eps_yoy_pct", "eps_yoy", False),
               ("inventory_yoy_pct", "inventory_yoy", False), ("shares_yoy_pct", "shares_yoy", False)]


def annual_block(a):
    b = {}
    for out, src, frac in ANNUAL_KEYS:
        b[out] = _pct(a.get(src)) if frac else _r(a.get(src))
    b["eps_positive"] = (a["eps_diluted"] > 0) if a.get("eps_diluted") is not None else None
    if a.get("inventory_yoy") is not None and a.get("revenue_yoy") is not None:
        b["inv_minus_rev_yoy_pp"] = _r(a["inventory_yoy"] - a["revenue_yoy"])
    b["debt_to_equity"] = _r(a.get("debt_to_equity"), 2)
    b["current_ratio"] = _r(a.get("current_ratio"), 2)
    if a.get("net_cash") is not None and a.get("assets"):
        b["net_cash_to_assets_pct"] = _r(a["net_cash"] / a["assets"] * 100)
        b["net_cash_sign"] = "+" if a["net_cash"] >= 0 else "-"
    return {k: x for k, x in b.items() if x is not None}


def quarterly_block(e):
    qs = sorted(e.get("quarterly") or [], key=lambda q: q["end"], reverse=True)
    qs = [q for q in qs if any(q.get(k) is not None for k in ("op_margin", "gross_margin", "revenue_yoy"))]
    if not qs:
        return [], {}
    q0 = _d(qs[0]["end"])
    out = []
    for q in qs[:4]:
        lag = round((q0 - _d(q["end"])).days / 30.44)       # 상대 월차만 — 달력은 신원을 흘린다
        b = {"lag_m": lag,
             "gross_margin_pct": _pct(q.get("gross_margin")), "op_margin_pct": _pct(q.get("op_margin")),
             "fcf_margin_pct": _pct(q.get("fcf_margin")),
             "revenue_yoy_pct": _r(q.get("revenue_yoy")), "eps_yoy_pct": _r(q.get("eps_yoy")),
             "inventory_yoy_pct": _r(q.get("inventory_yoy")),
             "eps_positive": (q["eps_diluted"] > 0) if q.get("eps_diluted") is not None else None}
        out.append({k: x for k, x in b.items() if x is not None})
    trend = {}
    yo = [q for q in qs if 340 <= (q0 - _d(q["end"])).days <= 390]
    if yo and qs[0].get("op_margin") is not None and yo[0].get("op_margin") is not None:
        trend["q0_op_margin_yoy_pp"] = _r((qs[0]["op_margin"] - yo[0]["op_margin"]) * 100)
    return out, trend


def build_packet(pid, c, fin, rev_rows, cons_rows):
    tk = c["ticker"]
    e = fin[tk]
    ann = sorted(e.get("annual") or [], key=lambda a: a["end"], reverse=True)[:3]
    closes = load_closes(tk)
    trend, px = price_trend(closes)
    rev = rev_rows.get(tk)
    val, vnotes = valuation(e, px, rev)
    q, qtrend = quarterly_block(e)
    fwd = {}
    if rev and rev.get("status") == "ok":
        fwd["eps_revision"] = {"score": _r(rev.get("score")), "band": rev.get("band"),
                               "chg_30d_pct": _r(rev.get("chg_30d")), "chg_90d_pct": _r(rev.get("chg_90d")),
                               "breadth": _r(rev.get("breadth"), 2)}
    cr = cons_rows.get(tk)
    if cr and cr.get("gap_pct") is not None:
        fwd["consensus_upside_pct"] = _r(cr["gap_pct"])
    notes = list(vnotes)
    if not trend:
        notes.append("가격 이력 부족 — 추세 지표 없음")
    if not fwd:
        notes.append("EPS 리비전·컨센 데이터 없음(중립 처리)")
    return {
        "id": pid,
        "annual": {f"FY-{i}": annual_block(a) for i, a in enumerate(ann)},
        "quarterly": q,
        "quarter_trend": qtrend,
        "forward": fwd,
        "valuation": val,
        "price_trend": trend,
        "flags": sorted({f["code"] for f in e.get("flags") or [] if f.get("code") and f["code"] != "source_conflict"}),
        "data_notes": notes,
    }


def leak_tokens(c, fin):
    tk = c["ticker"]
    toks = {tk, tk.split(".")[0]}
    for nm in (c.get("label"), (fin.get(tk) or {}).get("name")):
        if nm and nm != tk:
            toks.add(nm)
            first = re.split(r"[\s(]", nm)[0]
            if len(first) >= 3:
                toks.add(first)
    return {t for t in toks if t}


def leak_scan(packets, cands, fin):
    """패킷에 이름·티커·통화가 남았는지 — 한 개라도 있으면 블라인드가 아니다."""
    hits = []
    blob = {p["id"]: json.dumps(p, ensure_ascii=False) for p in packets}
    for pid, s in blob.items():
        m = re.findall(GENERIC_LEAK, s)
        if m:
            hits.append((pid, "generic", sorted(set(m))))
    for c in cands:
        for t in leak_tokens(c, fin):
            pat = r"\b" + re.escape(t) + r"\b" if re.fullmatch(r"[A-Za-z]{1,4}", t) else re.escape(t)
            for pid, s in blob.items():
                if re.search(pat, s, flags=0 if t.isupper() else re.I):
                    hits.append((pid, c["ticker"], t))
    return hits


RUBRIC_HEAD = """# 블라인드 재채점 루브릭 (compact · 0~100)

> 생성: `blind_rescore.py --build` · 원문 = `.claude/skills/stock-deepdive/SKILL.md` 「검증된 방법론 체크리스트」(아래 발췌).
> 이 루브릭은 **패킷에 든 숫자만으로** 채점하도록 원문을 압축한 것이다.

## 채점자 규칙 (반드시)
1. **패킷의 숫자만** 쓴다. 웹 검색·레포 탐색·다른 파일 열람 금지. 회사를 맞히려 하지 말 것.
2. 숫자를 보고 회사가 떠올랐으면 **숨기지 말고** `recognized: true`, `guess`에 추정을 적는다.
   (인식 여부는 결함이 아니라 측정값이다 — 인식한 패킷은 따로 분석한다.)
3. 단위: `*_pct` = %, `*_pp` = %p, `lag_m` = 최신 분기로부터 개월 수, `FY-0` = 최근 회계연도.
4. 결측 항목은 **중립 점수**(해당 축 만점의 절반)로 둔다 — 결측을 벌점으로 쓰지 않는다.
5. 별점은 스코어 밴드로 고정: **85~100=⭐5 / 70~84=⭐4 / 55~69=⭐3 / 40~54=⭐2 / <40=⭐1.**

## 축과 배점 (합 100)

### A. 펀더멘털 — CANSLIM C·A + 이익의 질 (55점)
| 항목 | 배점 | 기준 |
|---|---|---|
| C 최근 분기 EPS YoY | 15 | ≥+50% 15 · +25~50 12 · +10~25 8 · 0~10 4 · 음수/적자 0 (적자 축소는 최대 4) |
| A 연간 EPS 추세(FY-2→FY-0) | 12 | 3년 흑자·증가 + FY-0 ≥+25% 12 · 증가 2/3 8 · 혼조 4 · 적자 지속 0 |
| 마진 방향 | 10 | 분기 영업마진 확대(`q0_op_margin_yoy_pp`>0, FY 마진 상승) 10 · 보합 5 · 축소 0 · 적자폭 축소는 최대 5 |
| FCF·이익의 질 | 10 | FCF 마진 ≥15% 10 · 5~15 7 · 0~5 4 · 음수 0. **재고 YoY − 매출 YoY ≥ +20%p면 −3**, 희석(`shares_yoy_pct` > +3%) −2 |
| 재무건전성 | 8 | 순현금 + D/E<0.5 8 · 순부채지만 D/E<1 5 · D/E 1~2 2 · D/E>2 또는 유동비율<1 0 |

### B. 추세 — 미너비니 추세템플릿 + 오닐 N·L (25점)
| 항목 | 배점 | 기준 |
|---|---|---|
| 정배열 | 10 | 가격>MA50>MA200 **그리고** MA200 상승(`ma200_slope_1m_pct`>0) 10 · 둘 중 하나 5 · 역배열 0 |
| 52주 고점 근접 | 8 | −10% 이내 8 · −10~−25 5 · −25~−40 2 · 그 아래 0 |
| 상대강도 대용(12M 수익률) | 7 | ≥+50% 7 · +20~50 5 · 0~20 3 · 음수 0. 3M ≤ −20%면 −2 |

### C. 전망·가격 규율 — 드러켄밀러식 방향 + 밸류 (20점)
| 항목 | 배점 | 기준 |
|---|---|---|
| EPS 리비전 점수(−100~+100) | 8 | ≥+50 8 · +20~50 6 · −20~+20 4 · −50~−20 2 · ≤−50 0 · 없음 4 |
| 컨센 상승여력 | 6 | ≥+40% 6 · +20~40 5 · +5~20 3 · <+5% 1 · 없음 3 |
| 밸류 대 성장(PEG 근사 = P/E ÷ EPS 성장률) | 6 | PEG<1 6 · 1~2 4 · >2 2 · 적자 0 · 없음 3. 마진 사상 최고권 + P/E 극저(<8)는 **사이클 정점 의심 −2** |

> **M(시장 방향)·I(기관 매집)·S(수급)**는 패킷에 없다 — 전 종목 공통이거나 신원을 흘리는 정보라 뺐다. 채점하지 않는다.
> 정성 요소(해자·촉매·경영진·규제)도 없다. **이 점수는 현행 스코어의 점검용이지 대체물이 아니다.**

## 출력 형식 (JSON 배열 하나 — 이 외 텍스트 금지)
```json
[
  {"id": "P01", "score": 72, "star": 4,
   "rationale": "분기 EPS +60%·마진 확대, 정배열이나 고점 -18%. FCF 마진 22%. 리비전 없음(중립).",
   "recognized": false, "guess": null}
]
```
- `score` 정수 0~100 · `star` 1~5(밴드와 일치) · `rationale` 한국어 1~2문장, 패킷 수치 인용
- `recognized` true/false · `guess` 추정 회사명 또는 null

---

## 원문 발췌 — stock-deepdive 「검증된 방법론 체크리스트」
"""


def rubric_text():
    excerpt = "(원문을 찾지 못했다 — stock-deepdive/SKILL.md 경로 확인)"
    if os.path.exists(SKILL_DEEPDIVE):
        with open(SKILL_DEEPDIVE, encoding="utf-8") as f:
            txt = f.read()
        m = re.search(r"## 검증된 방법론 체크리스트.*?(?=\n## )", txt, flags=re.S)
        if m:
            excerpt = "\n".join("> " + ln if ln.strip() else ">" for ln in m.group(0).splitlines())
    return RUBRIC_HEAD + "\n" + excerpt + "\n"


def make_packets(d):
    cands, skipped, _st, fin = candidates()
    rev = _load(os.path.join(APP, "eps_revisions.json")) if os.path.exists(os.path.join(APP, "eps_revisions.json")) else {}
    rev_rows = {r["symbol"]: r for r in (rev.get("latest") or {}).get("rows", []) if r.get("status") == "ok"}
    cons = _load(os.path.join(APP, "consensus.json")) if os.path.exists(os.path.join(APP, "consensus.json")) else {}
    cons_rows = {r["symbol"]: r for r in cons.get("rows", []) if "error" not in r}

    # 결정적 셔플 — 같은 날짜면 같은 id(재현 가능), 날짜가 바뀌면 순서가 바뀐다(학습 방지).
    order = sorted(cands, key=lambda c: c["ticker"])
    random.Random(f"blind-rescore-{d}").shuffle(order)
    packets, mapping = [], {}
    for i, c in enumerate(order, 1):
        pid = f"P{i:02d}"
        packets.append(build_packet(pid, c, fin, rev_rows, cons_rows))
        mapping[pid] = {"ticker": c["ticker"], "label": c["label"], "group": c["group"]}
    return order, packets, mapping, skipped, fin


def cmd_selftest():
    """가드가 실제로 잡는지 — 위반을 심어 확인한다(초록불 ≠ 위반 없음, 8/22·8/23 교훈).
    파일은 하나도 쓰지 않는다."""
    import copy
    fails = []
    order, packets, _m, _s, fin = make_packets(kst_today())
    if not packets:
        fails.append("패킷 0개 — 후보 수집 실패")
    clean = leak_scan(packets, order, fin)
    if clean:
        fails.append(f"깨끗해야 할 패킷에서 누출 탐지(오탐): {clean[:3]}")
    if packets and order:
        c = order[0]
        plants = [c["ticker"].split(".")[0], "KRW", "USD", c["label"]]
        for tok in plants:
            q = copy.deepcopy(packets)
            q[-1]["data_notes"].append(f"x {tok} x")
            if not leak_scan(q, order, fin):
                fails.append(f"심은 토큰 '{tok}'을 못 잡았다")
    if not _inside_repo(os.path.join(ROOT, "data", "research", "blind", "m.json")):
        fails.append("레포 안 매핑 경로를 레포 밖으로 오판")
    if _inside_repo(os.path.join(tempfile.gettempdir(), "portfolio_desk_blind", "m.json")):
        fails.append("OS 임시폴더를 레포 안으로 오판")
    if _pe(100.0, -1.0) != (None, "적자"):
        fails.append("적자 EPS P/E 처리 오류")
    if _pe(456.9, 136.25 * 4)[0] is not None:
        fails.append("단위 불일치 P/E(<2.5배)를 통과시켰다")
    if _pe(100.0, 0.1)[0] != ">400":
        fails.append("초고 P/E 상한 표기 오류")
    if fails:
        print("❌ blind_rescore selftest 실패:\n  - " + "\n  - ".join(fails))
        return 1
    print(f"✅ blind_rescore selftest — 패킷 {len(packets)}개 무누출 · 심은 누출 4종 적발 · 레포 경로 가드 · P/E 경계 3종")
    return 0


def cmd_build(args):
    d = args.date
    order, packets, mapping, skipped, fin = make_packets(d)

    hits = leak_scan(packets, order, fin)
    if hits:
        print("❌ 누출 스캔 실패 — 패킷에 신원 토큰이 남았다. 아무것도 쓰지 않는다:", file=sys.stderr)
        for h in hits[:30]:
            print("   ", h, file=sys.stderr)
        return 2

    mpath = args.mapping_out or default_mapping_path(d)
    if _inside_repo(mpath):
        print(f"❌ 매핑 경로가 레포 안이다 — 채점자가 읽을 수 있어 블라인드가 깨진다: {mpath}", file=sys.stderr)
        return 2

    os.makedirs(BLIND_DIR, exist_ok=True)
    ppath = os.path.join(BLIND_DIR, f"packets_{d}.json")
    rpath = os.path.join(BLIND_DIR, "rubric.md")
    doc = {
        "date": d,
        "n": len(packets),
        "rubric": os.path.relpath(rpath, ROOT).replace("\\", "/"),
        "instructions": "비율·추세만 담긴 익명 패킷. 이름·티커·지역·통화·절대규모·섹터·회계연도 날짜는 제거했다. "
                        "rubric.md의 규칙대로 패킷 숫자만으로 0~100 채점하고 JSON 배열로 답한다. 회사를 맞히려 하지 말 것 — "
                        "떠올랐다면 recognized=true로 정직하게 적는다.",
        "units": {"*_pct": "%", "*_pp": "%p", "lag_m": "최신 분기로부터 개월", "FY-0": "최근 회계연도",
                  "debt_to_equity": "배", "current_ratio": "배", "pe_*": "배"},
        "packets": packets,
    }
    with open(ppath, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    with open(rpath, "w", encoding="utf-8") as f:
        f.write(rubric_text())
    os.makedirs(os.path.dirname(os.path.abspath(mpath)), exist_ok=True)
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump({"date": d, "seed": f"blind-rescore-{d}", "packets": os.path.relpath(ppath, ROOT).replace("\\", "/"),
                   "map": mapping}, f, ensure_ascii=False, indent=1)

    print(f"✅ 패킷 {len(packets)}개 (보유 {sum(1 for c in order if c['group']=='holding')} · "
          f"워치 {sum(1 for c in order if c['group']=='watch')}) · 누출 스캔 통과")
    print(f"   packets = {ppath}")
    print(f"   rubric  = {rpath}")
    print(f"   mapping = {mpath}  (레포 밖 — 채점자에게 주지 말 것)")
    print(f"   ids     = {', '.join(p['id'] for p in packets)}")
    if skipped:
        print("   제외: " + " · ".join(f"{t}({why})" for t, why in skipped))
    return 0


# ───────────────────────── 비교 ─────────────────────────
def band_star(s):
    return 5 if s >= 85 else 4 if s >= 70 else 3 if s >= 55 else 2 if s >= 40 else 1


def pearson(x, y):
    n = len(x)
    if n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def _ranks(v):
    idx = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and v[idx[j + 1]] == v[idx[i]]:
            j += 1
        for k in range(i, j + 1):
            r[idx[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    return pearson(_ranks(x), _ranks(y)) if len(x) >= 3 else None


def _mean(v):
    return sum(v) / len(v) if v else None


def _fmt(x, nd=1, sign=False):
    if x is None:
        return "—"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def _guess_ok(guess, m):
    if not guess:
        return False
    g = str(guess).lower()
    toks = {m["ticker"].lower(), m["ticker"].split(".")[0].lower(), (m.get("label") or "").lower()}
    return any(t and (t in g or g in t) for t in toks if len(t) >= 2)


def cmd_compare(args):
    res = _load(args.compare)
    if isinstance(res, dict):
        res = res.get("results") or res.get("scores") or []
    mpath = args.mapping or default_mapping_path(args.date)
    if not os.path.exists(mpath):
        print(f"❌ 매핑 파일 없음: {mpath} (--mapping으로 지정)", file=sys.stderr)
        return 2
    mp = _load(mpath)
    mapping, d = mp["map"], mp.get("date", args.date)
    st = _load(os.path.join(APP, "stocks.json"))
    cur = {}
    for key in ("stocks", "watchlist"):
        for tk, s in (st.get(key) or {}).items():
            cur[tk] = s

    rows, unknown = [], []
    for r in res:
        pid = r.get("id")
        if pid not in mapping:
            unknown.append(pid)
            continue
        m = mapping[pid]
        s = cur.get(m["ticker"], {})
        try:
            bs = float(r.get("score"))
        except (TypeError, ValueError):
            unknown.append(pid)
            continue
        cs = s.get("score")
        rows.append({
            "id": pid, "ticker": m["ticker"], "label": m.get("label"), "group": m["group"],
            "cur_score": cs, "cur_star": s.get("stars"),
            "blind_score": bs, "blind_star": r.get("star") or band_star(bs),
            "band_star": band_star(bs), "delta": (bs - cs) if cs is not None else None,
            "recognized": _recog(r.get("recognized")), "guess": r.get("guess"),
            "guess_correct": _guess_ok(r.get("guess"), m), "rationale": r.get("rationale", ""),
        })
    missing = sorted(set(mapping) - {r["id"] for r in rows})
    both = [r for r in rows if r["delta"] is not None]
    xs = [r["cur_score"] for r in both]
    ys = [r["blind_score"] for r in both]
    pr, sr = pearson(xs, ys), spearman(xs, ys)
    big = sorted([r for r in both if abs(r["delta"]) >= FLAG_BIG], key=lambda r: -abs(r["delta"]))
    grp = {g: [r["delta"] for r in both if r["group"] == g] for g in ("holding", "watch")}
    rec = [abs(r["delta"]) for r in both if r["recognized"] or r["guess_correct"]]
    unrec = [abs(r["delta"]) for r in both if not (r["recognized"] or r["guess_correct"])]
    star_same = sum(1 for r in both if r["cur_star"] == r["band_star"])
    star_1 = sum(1 for r in both if r["cur_star"] is not None and abs(r["cur_star"] - r["band_star"]) <= 1)
    star_mismatch = [r["id"] for r in rows if r["blind_star"] != r["band_star"]]

    # ── 콘솔 표
    print(f"블라인드 재채점 비교 — {d} · n={len(both)} (매핑 {len(mapping)})")
    print(f"{'id':<4} {'ticker':<10} {'grp':<7} {'현행':>6} {'블라인드':>8} {'Δ':>6}  인식  플래그")
    for r in sorted(both, key=lambda r: -abs(r["delta"])):
        print(f"{r['id']:<4} {r['ticker']:<10} {r['group']:<7} {r['cur_score']:>4}⭐{r['cur_star']} "
              f"{r['blind_score']:>6.0f}⭐{r['band_star']} {r['delta']:>+6.0f}  "
              f"{'Y' if (r['recognized'] or r['guess_correct']) else '-':<4}  {'⚠️|Δ|≥15' if abs(r['delta']) >= FLAG_BIG else ''}")
    print(f"상관: Pearson {_fmt(pr, 2)} · Spearman {_fmt(sr, 2)} · 평균Δ {_fmt(_mean([r['delta'] for r in both]), 1, True)}")
    print(f"평균Δ 보유 {_fmt(_mean(grp['holding']), 1, True)} (n={len(grp['holding'])}) · "
          f"워치 {_fmt(_mean(grp['watch']), 1, True)} (n={len(grp['watch'])})")
    print(f"평균|Δ| 인식 {_fmt(_mean(rec))} (n={len(rec)}) · 미인식 {_fmt(_mean(unrec))} (n={len(unrec)})")
    if unknown or missing:
        print(f"⚠️ 매핑 밖 id {unknown} · 결과 누락 id {missing}")

    # ── 결과 원장(레포 · 채점 이후에만 생성되므로 블라인드를 깨지 않는다)
    os.makedirs(BLIND_DIR, exist_ok=True)
    jpath = args.results_out or os.path.join(BLIND_DIR, f"results_{d}.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump({"date": d, "n": len(both), "pearson": pr, "spearman": sr, "rows": rows}, f,
                  ensure_ascii=False, indent=1)

    # ── 문서
    out = args.out or os.path.join(DOCS_RESEARCH, f"blind_rescore_{d}.md")
    hd, wd = _mean(grp["holding"]), _mean(grp["watch"])
    own_gap = (wd - hd) if (hd is not None and wd is not None) else None
    L = []
    L.append(f"# 블라인드 재채점 — {d}\n")
    L.append("> 측정 전용. **어떤 스코어·별점·룰도 자동으로 바꾸지 않는다.** |Δ|≥15는 다음 보고서 PM 재검토 대상일 뿐이다.\n")
    L.append("## 결론\n")
    L.append(f"- 표본 **{len(both)}종목**(보유 {len(grp['holding'])} · 워치 {len(grp['watch'])}). "
             f"현행 vs 블라인드 상관 Pearson **{_fmt(pr, 2)}** · Spearman **{_fmt(sr, 2)}**.")
    L.append(f"- 별점 일치 {star_same}/{len(both)} · ±1칸 이내 {star_1}/{len(both)}. |Δ|≥{FLAG_BIG} **{len(big)}종목**.")
    if own_gap is not None:
        L.append(f"- 평균 Δ(블라인드−현행): 보유 **{_fmt(hd, 1, True)}** vs 워치 **{_fmt(wd, 1, True)}** → "
                 f"보유 프리미엄 추정 **{_fmt(own_gap, 1, True)}p** "
                 f"({'보유를 더 후하게 채점하고 있을 가능성' if own_gap > 3 else '보유 편향 신호 약함' if own_gap > -3 else '오히려 보유를 박하게 채점'}).")
    if rec and unrec:
        L.append(f"- 평균 |Δ|: 인식 패킷 **{_fmt(_mean(rec))}**(n={len(rec)}) vs 미인식 **{_fmt(_mean(unrec))}**(n={len(unrec)}) — "
                 f"{'인식한 쪽이 덜 벌어진다 = 신원을 알면 우리 점수 쪽으로 끌린다(블라인드가 일부 깨졌다는 뜻)' if _mean(rec) < _mean(unrec) else '인식 여부로 드리프트가 줄지 않았다'}.")
    elif not rec:
        L.append("- 채점자가 인식했다고 답한 패킷이 없다(정직성은 검증 불가 — 한계 참조).")
    L.append("\n## 종목별 (|Δ| 큰 순)\n")
    L.append("| id | 종목 | 구분 | 현행 | 블라인드 | Δ | 인식 | 블라인드 근거 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in sorted(both, key=lambda r: -abs(r["delta"])):
        flag = " ⚠️" if abs(r["delta"]) >= FLAG_BIG else ""
        recog = ("✅" if r["guess_correct"] else "Y") if (r["recognized"] or r["guess_correct"]) else "—"
        rat = str(r["rationale"]).replace("|", "/").replace("\n", " ")
        L.append(f"| {r['id']} | {r['label']} ({r['ticker']}) | {'보유' if r['group']=='holding' else '워치'} | "
                 f"{r['cur_score']} ⭐{r['cur_star']} | {r['blind_score']:.0f} ⭐{r['band_star']} | "
                 f"**{r['delta']:+.0f}**{flag} | {recog} | {rat} |")
    if big:
        L.append("\n## 재검토 목록 (|Δ|≥15)\n")
        for r in big:
            side = "현행이 블라인드보다 높다 → 이름·보유·직전 별점이 점수를 떠받치고 있는지" if r["delta"] < 0 \
                else "현행이 블라인드보다 낮다 → 정성 감점(룰2·집중도·모멘텀 분류 등)이 숫자보다 과한지"
            L.append(f"- **{r['label']}** {r['cur_score']}→{r['blind_score']:.0f} ({r['delta']:+.0f}) — {side} 확인.")
    L.append("\n## 방법\n")
    L.append("- 도구: `blind_rescore.py --build` → 익명 패킷 `data/research/blind/packets_{d}.json` + 루브릭 `data/research/blind/rubric.md`; "
             "채점 결과 JSON → `blind_rescore.py --compare`.".replace("{d}", d))
    L.append("- 대상: 보유(ETF 제외) + 활성 워치 중 `financials.json`에 재무가 있는 종목. "
             "재무 미수록 워치(CDNS·ISRG·AMD·KT&G 등)는 빠졌다.")
    L.append("- 패킷에 **넣은 것**: FY-0/1/2 영업·매출총·FCF 마진, ROE, 매출·EPS·재고·주식수 YoY, 재고−매출 격차, D/E, 유동비율, "
             "순현금/자산; 최근 4개 분기(상대 월차 `lag_m`만); EPS 리비전(보유만)·컨센 상승여력(미국만); P/E(선행·TTM·런레이트); "
             "가격 추세(MA50/MA200·MA200 기울기·52주 고점/저점·3M/12M).")
    L.append("- **뺀 것**: 이름·티커·지역·통화·절대 매출/시총·섹터 단어·회계연도 종료일·애널리스트 수·데이터 출처 충돌 플래그. "
             "빌드 시 누출 스캔(이름·티커·통화 토큰)이 통과해야 파일을 쓴다.")
    L.append(f"- id 순서: 날짜 시드 결정적 셔플(`blind-rescore-{d}`). 매핑은 **레포 밖** 임시 폴더에만 있다(레포 안 경로는 거부).")
    L.append("- 루브릭: stock-deepdive 「검증된 방법론 체크리스트」 압축 — 펀더 55(CANSLIM C·A·마진·FCF·재무) · "
             "추세 25(미너비니 정배열·52주 고점·12M) · 전망/밸류 20(리비전·컨센·PEG). 밴드 85/70/55/40.")
    L.append("\n## 한계 — 같이 읽을 것\n")
    L.append("- **숫자가 신원을 흘린다.** 극단값(영업마진 60%대·EPS +1,000%대·적자 로봇 기업의 마이너스 마진)은 사실상 지문이다. "
             "그래서 `recognized`를 받아 따로 봤지만, 채점자가 인식을 정직하게 보고했는지는 검증할 수 없다.")
    L.append("- **블라인드 점수엔 정성 정보가 없다** — 해자·촉매·경영진·규제·수주 공시·집중도는 패킷에 없다. "
             "현행 스코어는 펀더 서브스코어에 PM의 정성 가감을 얹은 값이라 **Δ의 일부는 설계상 당연하다.** 이 도구는 점검이지 대체물이 아니다.")
    L.append("- **정보 비대칭**: EPS 리비전·선행 P/E는 보유 종목만, 컨센 상승여력은 미국 종목만 있다. "
             "블라인드 채점자는 결측을 중립으로 두지만, 이 비대칭 자체가 '보유/미국'을 흘릴 수 있다.")
    L.append("- **M(시장 방향)·I·S를 채점하지 않는다** — 지역을 지웠기 때문이다. 코스피 급락 국면의 국내 종목은 추세 축에서만 불리하게 잡힌다.")
    L.append("- **n이 작고 채점자 1회분이다.** 같은 패킷을 다른 채점자·다른 날 셔플로 반복해야 분산을 알 수 있다. 상관 하나로 결론 내지 말 것.")
    L.append("- 재무 원천 한계 승계: 국내는 Q4 단독 분기·전년 Q1이 비어 TTM P/E 대신 FY-0/런레이트 P/E를 쓴 종목이 있다; "
             "단위가 안 맞는 P/E(예: 외화 EPS vs 달러 가격)는 정합 범위 밖이라 버렸다.")
    if unknown or missing:
        L.append(f"\n> ⚠️ 매핑 밖 id {unknown} · 결과 누락 id {missing}")
    L.append("")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"📝 {out}\n📦 {jpath}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="블라인드 재채점 — 익명 비율 패킷 생성(--build)과 현행 스코어 대조(--compare). 측정 전용.")
    ap.add_argument("--build", action="store_true", help="익명 패킷·루브릭·레포 밖 매핑 생성")
    ap.add_argument("--compare", metavar="RESULTS_JSON", help="채점 결과 JSON(list of {id,score,star,rationale,recognized,guess})")
    ap.add_argument("--date", default=kst_today(), help="패킷 날짜·셔플 시드 (기본 오늘 KST)")
    ap.add_argument("--mapping-out", help="--build: 매핑 저장 경로(레포 밖이어야 함, 기본 OS 임시폴더)")
    ap.add_argument("--mapping", help="--compare: 매핑 파일 경로(기본 = --build 기본 경로)")
    ap.add_argument("--out", help="--compare: 문서 경로(기본 docs/research/blind_rescore_<date>.md)")
    ap.add_argument("--results-out", help="--compare: 조인 결과 JSON 경로(기본 data/research/blind/results_<date>.json)")
    ap.add_argument("--selftest", action="store_true", help="누출 스캔·레포 경로 가드·P/E 경계를 위반을 심어 검증(파일 안 씀)")
    args = ap.parse_args()
    if args.selftest:
        return cmd_selftest()
    if args.build:
        return cmd_build(args)
    if args.compare:
        return cmd_compare(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
