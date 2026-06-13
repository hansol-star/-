#!/usr/bin/env python3
"""토스증권 Open API — 계좌/보유종목/현금 스냅샷 (조회 전용, 주문 API 절대 미사용).

사전 조건: 정훈이 토스증권 PC 웹(WTS) > 설정 > Open API에서 발급한
client_id / client_secret 을 채팅에 제공해야 함. 키는 저장하지 않는다.

사용:
  python3 toss_snapshot.py --id CLIENT_ID --secret CLIENT_SECRET
  (또는 환경변수 TOSS_CLIENT_ID / TOSS_CLIENT_SECRET)

API: https://openapi.tossinvest.com  (OAuth2 Client Credentials)
- POST /oauth2/token                  토큰 발급
- GET  /api/v1/accounts               계좌 목록
- GET  /api/v1/holdings               보유 주식 (X-Tossinvest-Account 헤더 필요)
- GET  /api/v1/buying-power           매수가능금액=현금 (X-Tossinvest-Account 헤더 필요)
- GET  /api/v1/exchange-rate          환율
문서: https://openapi.tossinvest.com/openapi-docs/latest/api-reference/README.md
스키마 불일치 시 위 문서를 curl로 재확인할 것.

--------------------------------------------------------------------------------
[Claude Code 로컬 적응판]
  * 기본 TLS 검증 ON.  원본(샌드박스)은 이그레스 프록시의 자가서명 인증서 때문에
    CERT_NONE 으로 검증을 껐었지만, 네 로컬 머신은 토스의 정식 인증서를 직접 보므로
    검증을 켜는 게 맞다(보안상 권장).  회사망 등 프록시 뒤에서 인증서 에러가 나면
    --insecure 로만 끌 것.
  * !! 주문(POST/PUT) 엔드포인트는 이 스크립트에 의도적으로 없음. 조회 GET 전용. !!
--------------------------------------------------------------------------------
"""
import argparse, json, os, sys, urllib.request, urllib.parse, urllib.error, ssl

BASE = "https://openapi.tossinvest.com"


def make_ctx(insecure: bool):
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def req(method, path, ctx, headers=None, data=None, form=False):
    url = BASE + path
    if data is not None:
        body = urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
    else:
        body = None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Accept", "application/json")
    if form:
        r.add_header("Content-Type", "application/x-www-form-urlencoded")
    for k, v in (headers or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, context=ctx, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:500]
        print(f"[HTTP {e.code}] {method} {path}: {err}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERR] {method} {path}: {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default=os.environ.get("TOSS_CLIENT_ID"))
    ap.add_argument("--secret", default=os.environ.get("TOSS_CLIENT_SECRET"))
    ap.add_argument("--raw", action="store_true", help="원본 JSON 전체 출력")
    ap.add_argument("--insecure", action="store_true",
                    help="자가서명 인증서 프록시 뒤일 때만: TLS 검증 끔(보안 저하)")
    args = ap.parse_args()
    if not args.id or not args.secret:
        sys.exit("client_id/secret 필요 — 토스증권 WTS > 설정 > Open API에서 발급")

    ctx = make_ctx(args.insecure)

    tok = req("POST", "/oauth2/token", ctx, form=True, data={
        "grant_type": "client_credentials",
        "client_id": args.id, "client_secret": args.secret})
    if not tok or "access_token" not in tok:
        sys.exit("토큰 발급 실패 — 키 확인 또는 Open API 정식 오픈 여부 확인 필요")
    auth = {"Authorization": f"Bearer {tok['access_token']}"}

    fx = req("GET", "/api/v1/exchange-rate", ctx, headers=auth)
    accounts = req("GET", "/api/v1/accounts", ctx, headers=auth)
    if args.raw:
        print(json.dumps({"fx": fx, "accounts": accounts}, ensure_ascii=False, indent=1))
    acc_list = (accounts or {}).get("result") or (accounts or {}).get("accounts") or accounts or []
    if isinstance(acc_list, dict):
        acc_list = acc_list.get("accounts", [acc_list])
    print(f"\n=== 토스증권 스냅샷 ===\n환율: {json.dumps(fx, ensure_ascii=False)[:200]}")

    for acc in acc_list if isinstance(acc_list, list) else []:
        acc_no = acc.get("accountNo") or acc.get("account_no") or acc.get("id") or ""
        h = dict(auth); h["X-Tossinvest-Account"] = str(acc_no)
        holdings = req("GET", "/api/v1/holdings", ctx, headers=h)
        power = req("GET", "/api/v1/buying-power", ctx, headers=h)
        print(f"\n--- 계좌 {acc_no} ({acc.get('name', '')}) ---")
        print("매수가능금액:", json.dumps(power, ensure_ascii=False)[:300])
        print("보유종목:", json.dumps(holdings, ensure_ascii=False, indent=1)[:4000])
    print("\n※ 조회 전용 스크립트. 주문 API는 호출하지 않음.")


if __name__ == "__main__":
    main()
