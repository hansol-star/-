#!/usr/bin/env python3
"""insider_us.py — 미국 보유종목 내부자 매매(SEC Form 4) · 무키 · stdlib only

정훈 지시(2026-07-30 "다 하자"). `docs/data_coverage.md` §3 **미보유 레이어 우선순위 7번**.
국내는 `dart_disclosure.py --insider`(elestock)로 덮었는데 **미국 10종목은 사각지대**였다 —
경영진·10% 주주의 실제 매매가 EDGAR에 전부 공개돼 있는데 우리는 한 번도 안 봤다.

■ Form 4가 무엇을 말해주나
   경영진의 **자기 돈 매매**는 가이던스보다 정직한 신호로 취급된다(내부자 매수의 초과수익은
   문헌에서 반복 확인된 소수 이상현상 중 하나).
   ⚠️ **단 방향 해석에 함정이 있다**:
     - 매도(S)는 대부분 **10b5-1 사전약정·스톡옵션 행사 후 즉시매도·세금납부용**이라
       비관 신호가 아니다. `is_10b5_1` 플래그로 분리한다.
     - 매수(P)는 훨씬 드물고 재량적이라 **의미가 크다**.
   따라서 이 스크립트는 순매수/순매도 총량이 아니라 **'재량적 공개시장 매수(P)'를 따로 센다.**

■ 경보 전용 — 매수·매도 자동발동 아님. `dart_disclosure`·`vol_gauge`와 같은 규율.

SEC 요구: User-Agent에 연락처. 요청 10/초 제한 → 페이싱 내장.

사용:
  python3 insider_us.py                 # 보유 미국주 최근 90일
  python3 insider_us.py --days 180
  python3 insider_us.py --tickers NVDA,MU
  python3 insider_us.py --save          # data/app/insider_us.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "data", "app", "insider_us.json")

# VOO(ETF)는 내부자 개념이 없다. TSLA는 7/7 매도 → 제외.
US = ["NVDA", "MU", "AAPL", "MSFT", "ANET", "AVGO", "GOOGL", "META", "ORCL"]

# ⚠️ SEC는 **연락처가 든 User-Agent**를 요구한다 — 없으면 전 요청 403.
#    (7/30 실측: 자체 UA로 9/9종목 403 → edgar_facts의 검증된 클라이언트 재사용으로 해결.)
#    HTTP 클라이언트를 새로 만들지 말고 이미 도는 것을 쓴다.
import edgar_facts as _E
import cli_common

_last = [0.0]


def _get(url: str) -> bytes:
    """SEC 10 req/s 제한 준수 — edgar_facts._get(UA·gzip·재시도 내장) 위에 페이싱만 얹는다."""
    gap = time.time() - _last[0]
    if gap < 0.15:
        time.sleep(0.15 - gap)
    try:
        return _E._get(url)
    finally:
        _last[0] = time.time()


# ─────────────────────────────────────────── Form 4 파싱
#
# ownershipDocument XML은 스키마가 단순해 정규식으로 충분하다(외부 의존성 금지 원칙).
# 필요한 것만 뽑는다: 신고인·직위·거래일·코드·수량·단가·거래후 보유량·10b5-1 여부.

def _tag(x: str, name: str):
    m = re.search(rf"<{name}>\s*(?:<value>)?\s*([^<]*)", x)
    return m.group(1).strip() if m else None


def _f(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def parse_form4(xml: str) -> dict | None:
    owner = _tag(xml, "rptOwnerName")
    officer = _tag(xml, "officerTitle")
    is_dir = (_tag(xml, "isDirector") or "0") in ("1", "true")
    is_off = (_tag(xml, "isOfficer") or "0") in ("1", "true")
    is_ten = (_tag(xml, "isTenPercentOwner") or "0") in ("1", "true")
    # 10b5-1 사전약정 여부 — 매도 해석의 핵심 분기
    plan = bool(re.search(r"(aff10b5One|Rule 10b5-1|10b5-1)", xml, re.I))

    txs = []
    for blk in re.findall(r"<nonDerivativeTransaction>(.*?)</nonDerivativeTransaction>", xml, re.S):
        code = _tag(blk, "transactionCode")
        shares = _f(_tag(blk, "transactionShares"))
        price = _f(_tag(blk, "transactionPricePerShare"))
        ad = _tag(blk, "transactionAcquiredDisposedCode")
        date = _tag(blk, "transactionDate")
        after = _f(_tag(blk, "sharesOwnedFollowingTransaction"))
        if shares is None:
            continue
        txs.append({"code": code, "shares": shares, "price": price,
                    "ad": ad, "date": date, "after": after,
                    "value": (shares * price) if (price and shares) else None})
    if not txs:
        return None
    return {"owner": owner, "title": officer,
            "role": ("이사" if is_dir else "") + ("·임원" if is_off else "") + ("·10%주주" if is_ten else ""),
            "plan_10b5_1": plan, "tx": txs}


def filings(ticker: str, days: int, cap: int = 40) -> list[dict]:
    cik = _E.cik_map().get(ticker.upper())
    if not cik:
        return []
    sub = json.loads(_get(f"https://data.sec.gov/submissions/CIK{cik}.json").decode())
    rec = sub.get("filings", {}).get("recent", {})
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    out = []
    forms = rec.get("form", [])
    for i, form in enumerate(forms):
        if form != "4":
            continue
        fdate = rec["filingDate"][i]
        if fdate < cutoff:
            break                      # recent는 최신순 → 컷오프 넘으면 종료
        if len(out) >= cap:
            break
        acc = rec["accessionNumber"][i].replace("-", "")
        # ⚠️ primaryDocument는 XSL로 렌더링된 **HTML**을 가리킨다
        #    (예: "xslF345X06/wk-form4_178.xml" → 사람이 볼 화면).
        #    앞의 xsl 디렉터리를 벗겨야 파싱 가능한 **원본 XML**이 나온다.
        #    (7/30: 이걸 안 벗겨 nonDerivativeTransaction 0개 → 전 종목 '신고 0건'으로 보였다.)
        doc = rec["primaryDocument"][i].split("/")[-1]
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
        try:
            xml = _get(url).decode("utf-8", "replace")
        except Exception:
            continue
        p = parse_form4(xml)
        if p:
            p["filed"] = fdate
            p["url"] = url
            out.append(p)
    return out


def summarize(ticker: str, rows: list[dict]) -> dict:
    """재량적 매수(P)와 그 외를 분리 집계 — 총량만 보면 오독한다."""
    buy_p, sell_s, other = [], [], []
    for r in rows:
        for t in r["tx"]:
            item = dict(t, owner=r["owner"], title=r["title"], role=r["role"],
                        plan=r["plan_10b5_1"], url=r["url"])
            if t["code"] == "P":
                buy_p.append(item)
            elif t["code"] == "S":
                sell_s.append(item)
            else:
                other.append(item)     # A=수여, M=옵션행사, F=세금납부 원천징수 등
    val = lambda xs: sum(x["value"] or 0 for x in xs)
    return {
        "ticker": ticker, "filings": len(rows),
        "buy_open_market": {"n": len(buy_p), "shares": sum(x["shares"] for x in buy_p), "value": val(buy_p)},
        "sell_open_market": {"n": len(sell_s), "shares": sum(x["shares"] for x in sell_s), "value": val(sell_s),
                             "n_10b5_1": sum(1 for x in sell_s if x["plan"])},
        "other_grants_exercises": {"n": len(other), "shares": sum(x["shares"] for x in other)},
        "top_buys": sorted(buy_p, key=lambda x: -(x["value"] or 0))[:3],
        "top_sells": sorted(sell_s, key=lambda x: -(x["value"] or 0))[:3],
    }


def _money(v):
    if not v:
        return "-"
    return f"${v/1e6:,.1f}M" if v >= 1e6 else f"${v:,.0f}"


def render(sums: list[dict], days: int, failed: list | None = None):
    print(f"\n👤 미국 내부자 매매 (SEC Form 4) — 최근 {days}일")
    print("   해석 규율: **매도(S)는 대부분 10b5-1 사전약정·옵션행사 연계라 비관 신호가 아니다.**")
    print("             재량적 **공개시장 매수(P)**가 드물고 의미가 크다 — 그것만 따로 센다.\n")
    print(f"   {'종목':<7}{'신고':>5}{'매수P':>7}{'매수액':>11}{'매도S':>7}{'매도액':>11}{'(중 10b5-1)':>12}")
    for s in sums:
        b, sl = s["buy_open_market"], s["sell_open_market"]
        print(f"   {s['ticker']:<7}{s['filings']:>5}{b['n']:>7}{_money(b['value']):>11}"
              f"{sl['n']:>7}{_money(sl['value']):>11}{sl['n_10b5_1']:>12}")
    for s in sums:
        if not s["top_buys"]:
            continue
        print(f"\n   🟢 {s['ticker']} 재량적 매수:")
        for x in s["top_buys"]:
            print(f"      {x['date']} {x['owner']} ({x['role'] or x['title'] or '-'}) "
                  f"{x['shares']:,.0f}주 @ ${x['price'] or 0:,.2f} = {_money(x['value'])}")
    # ⚠️ 수집 실패를 '0건'으로 보고하면 안 된다 — 없는 것과 못 본 것은 다르다.
    #    (7/30 실측 버그: 9종목 전부 403인데 "재량적 매수 0건 — 이것도 결론"을 출력했다.)
    if failed:
        print(f"\n   ❌ 수집 실패 {len(failed)}종목 — 아래 집계는 **불완전**하다. '0건'으로 읽지 말 것:")
        for t, why in failed:
            print(f"      {t}: {why}")
    tot_b = sum(s["buy_open_market"]["n"] for s in sums)
    if not tot_b and not failed:
        print("\n   🔎 재량적 공개시장 매수 **0건** — 이것도 결론이다.")
        print("      크래시 국면에서 경영진이 자사주를 사지 않았다는 사실은 그 자체로 정보다")
        print("      (다만 실적발표 전후 블랙아웃 기간이면 살 수 없다 — 실적일정과 교차확인 필요).")


# ── 5% 대량보유(Schedule 13D/13G) ────────────────────────────────────────────
# `docs/data_coverage.md §3 #7b` 해소 (2026-08-01). 국내 `dart_disclosure.py --major`
# (majorstock 5% 대량보유)와 **같은 문법**이 되도록 여기에 붙였다 — 국내/미국 대칭.
#
# ★ 착수 전 판별에서 걸린 함정 (§4b "0은 결론이 아니라 가설"의 교과서 사례):
#   `browse-edgar?type=SC+13`으로 조회하면 NVDA 최신 건이 **2024-07-18**로 나온다.
#   "최근 대량보유 신고 없음"으로 결론냈으면 완전한 오보였다 — 실제로는 SEC가 폼 타입
#   명칭을 **`SC 13G` → `SCHEDULE 13G`**로 바꿨을 뿐이고, NVDA는 **2026-07-20**에도
#   신고가 들어와 있다(21건 보유). 낡은 폼 이름으로 질의하면 조용히 잘려나간다.
#   ⇒ 두 표기를 **모두** 받는다.
MAJOR_FORMS = re.compile(r"^(?:SC 13|SCHEDULE 13)[DG]", re.I)

# ★두 번째 함정: 발행사 submissions 피드에는 **방향이 다른 두 종류**가 섞여 있다.
#   ① 남이 우리 종목을 5% 취득 (SUBJECT = 우리 회사)  ← 지분 감시의 본래 목적
#   ② 우리 회사가 남을 5% 취득 (FILED BY = 우리 회사) ← 전략적 지분투자
#   실제로 NVDA의 2026-07-20 SCHEDULE 13G는 **NVIDIA가 Nebius(구 Yandex) 지분을 신고**한
#   건이었다. 이걸 "NVDA 대량보유 신고"로 세면 정반대로 읽힌다.
#   ⇒ index-headers에서 SUBJECT/FILED BY를 읽어 **방향을 라벨링**한다.
_HDR_SUBJ = re.compile(r"SUBJECT COMPANY:.*?COMPANY CONFORMED NAME:\s*([^\n\r]+)", re.S | re.I)
_HDR_FILER = re.compile(r"FILED BY:.*?COMPANY CONFORMED NAME:\s*([^\n\r]+)", re.S | re.I)


def _parties(cik: int, acc: str) -> tuple[str, str]:
    """(subject, filed_by) — 실패 시 빈 문자열(부재로 단정하지 않기 위해 구분 가능하게)."""
    url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/"
           f"{acc}-index-headers.html")
    try:
        raw = re.sub(r"<[^>]+>", " ", _get(url).decode("utf-8", "replace"))
    except Exception:
        return "", ""
    s = _HDR_SUBJ.search(raw)
    f = _HDR_FILER.search(raw)
    return (s.group(1).strip() if s else "", f.group(1).strip() if f else "")


def _norm(name: str) -> str:
    """회사명 비교용 정규화 — 'NVIDIA CORP' vs 'NVIDIA Corporation' 같은 표기차 흡수."""
    n = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    for suf in ("corporation", "corp", "incorporated", "inc", "company", "co", "plc", "ltd"):
        if n.endswith(suf):
            n = n[: -len(suf)]
            break
    return n


def major_holders(ticker: str, days: int, cap: int = 30) -> dict:
    """13D/13G = 5% 이상 대량보유 신고. 13D는 **경영참여 목적**(행동주의), 13G는 단순투자."""
    cik = _E.cik_map().get(ticker.upper())
    if not cik:
        return {"ticker": ticker, "error": "CIK 없음"}
    sub = json.loads(_get(f"https://data.sec.gov/submissions/CIK{cik}.json").decode())
    issuer_key = _norm(sub.get("name", ""))
    rec = sub.get("filings", {}).get("recent", {})
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    rows = []
    for i, form in enumerate(rec.get("form", [])):
        if not MAJOR_FORMS.match(form or ""):
            continue
        fdate = rec["filingDate"][i]
        if fdate < cutoff:
            continue
        if len(rows) >= cap:
            break
        acc = rec["accessionNumber"][i]
        subject, filer = _parties(int(cik), acc)
        # 방향 판정 — 신고자(FILED BY)가 발행사 자신이면 '취득'(우리가 남의 지분을 신고),
        #             아니면 '피취득'(남이 우리 지분을 신고). 판별 실패는 '미상'으로 남긴다.
        if filer:
            direction = "취득" if _norm(filer) == issuer_key else "피취득"
        else:
            direction = "미상"
        rows.append({
            "form": form, "filed": fdate,
            "amend": form.rstrip().endswith("/A"),
            # 13D = 경영참여 목적 → 행동주의 가능성. 13G = 수동적 투자(패시브 대형기관 다수)
            "activist": bool(re.search(r"13D", form, re.I)),
            "direction": direction, "subject": subject, "filer": filer,
            "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/"
                   f"{acc}-index.htm",
        })
    rows.sort(key=lambda r: r["filed"], reverse=True)
    inbound = [r for r in rows if r["direction"] != "취득"]
    return {"ticker": ticker.upper(), "n": len(rows), "n_inbound": len(inbound),
            "n_activist": sum(1 for r in inbound if r["activist"]), "rows": rows}


def render_major(res: list[dict], days: int):
    print(f"\n🏛️ 미국 5% 대량보유 신고 (Schedule 13D/13G) — 최근 {days}일")
    print("   13D = **경영참여 목적**(행동주의 가능) · 13G = 단순투자(패시브 대형기관 다수)")
    print("   ⚠️ 대부분은 Vanguard·BlackRock 등 인덱스 자금의 정기 신고다 — 13D가 아니면 과잉해석 금지.")
    print("   ⚠️ **방향 주의**: '피취득'=남이 우리 종목을 5% 취득 / '취득'=우리 회사가 남을 5% 취득")
    print("      (NVDA의 13G 상당수는 후자 — 엔비디아가 타사 지분을 신고한 건이다. 섞어 읽지 말 것.)\n")
    for r in res:
        if r.get("error"):
            print(f"   🚨 {r['ticker']:<7} 수집 실패 — {r['error']} (← '신고 없음'이 아니다)")
            continue
        mark = f"  🔴 13D {r['n_activist']}건" if r["n_activist"] else ""
        out = f"피취득 {r['n_inbound']}"
        if r["n"] - r["n_inbound"]:
            out += f" · 취득 {r['n'] - r['n_inbound']}"
        print(f"   {r['ticker']:<7} {r['n']:>2}건 ({out}){mark}")
        for x in r["rows"][:3]:
            kind = "13D(경영참여)" if x["activist"] else "13G(단순투자)"
            who = x["filer"] if x["direction"] != "취득" else f"→ {x['subject']}"
            print(f"      · {x['filed']} [{x['direction']}] {kind}{'/정정' if x['amend'] else ''} "
                  f"{who[:38]}")
            print(f"         {x['url']}")


def main():
    ap = argparse.ArgumentParser(description="미국 내부자 매매 Form 4 (조회 전용·경보 전용)")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--tickers", help="쉼표·공백구분(생략 시 보유 미국주)")
    ap.add_argument("--cap", type=int, default=40, help="종목당 최대 신고서 수(SEC 부하 보호)")
    ap.add_argument("--major", action="store_true",
                    help="5%% 대량보유 13D/13G (국내 dart_disclosure.py --major와 같은 문법)")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()

    tickers = [t.strip().upper() for t in cli_common.split_tickers(a.tickers)] if a.tickers else US

    if a.major:
        res = []
        for t in tickers:
            try:
                res.append(major_holders(t, a.days))
            except Exception as e:
                res.append({"ticker": t, "error": f"{type(e).__name__} {str(e)[:50]}"})
        render_major(res, a.days)
        if a.save:
            os.makedirs(os.path.dirname(OUT), exist_ok=True)
            path = OUT.replace("insider_us.json", "major_holders_us.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"updated": dt.date.today().isoformat(), "days": a.days, "rows": res},
                          f, ensure_ascii=False, indent=1)
            print(f"\n저장: {path}")
        return 1 if any(r.get("error") for r in res) else 0
    sums, failed = [], []
    for t in tickers:
        try:
            sums.append(summarize(t, filings(t, a.days, a.cap)))
        except Exception as e:
            failed.append((t, f"{type(e).__name__} {str(e)[:60]}"))
            print(f"  ⚠️ {t}: {type(e).__name__} {str(e)[:60]}", file=sys.stderr)
    render(sums, a.days, failed)

    if a.save:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"updated": dt.date.today().isoformat(), "days": a.days,
                       "note": "경보 전용 — 매도는 10b5-1 사전약정이 대부분. 재량적 매수(P)가 신호.",
                       "failed": [{"ticker": t, "error": w} for t, w in failed],
                       "stocks": sums}, f, ensure_ascii=False, indent=1)
        print(f"\n💾 {os.path.relpath(OUT, ROOT)} 저장")
    print()


if __name__ == "__main__":
    main()
