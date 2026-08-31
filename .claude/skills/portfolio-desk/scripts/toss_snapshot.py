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

[8/31 신설 — 주문 차단 가드]
  舊 안전장치는 "주문 API 절대 호출 금지"라는 **문장 한 줄**뿐이었다. 8/27 오류감사에서
  확인된 그대로 — 가드 없는 교훈은 재발하고, 가드가 붙은 클래스만 멈췄다.
  키를 로컬에 저장하기로 한 이상(정훈 8/31 승인) 그 문장을 **장치**로 바꾼다.

  토스 자격증명은 **매매가 가능하다**: POST /api/v1/orders(주문 생성)·/cancel·/modify,
  POST·DELETE /api/v1/conditional-orders(조건주문). 조회 전용 스코프 옵션은 문서에 없다.
  ⇒ `_assert_readonly()`가 req() 진입부에서 **GET과 POST /oauth2/token 외 전부 거부**한다.
    (GET /api/v1/orders = 주문 *이력* 조회라 허용 — 매수 이력 원장 채우기에 필요)
  ⇒ 거부는 예외(OrderApiBlocked)로 올린다. 반환값으로 내리면 조용히 삼켜진다.
  ⇒ `--selftest`로 실제 주문 호출을 심어 막히는지 검증한다(guard_selftest 등록).
--------------------------------------------------------------------------------
"""
import argparse, json, os, sys, urllib.request, urllib.parse, urllib.error, ssl

BASE = "https://openapi.tossinvest.com"


def _decode_body(raw: bytes) -> str:
    """gzip/deflate/평문 어느 쪽이든 사람이 읽을 문자열로."""
    import gzip as _gz, zlib as _zl
    for f in (_gz.decompress, lambda b: _zl.decompress(b, -15), lambda b: b):
        try:
            return f(raw).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            continue
    return repr(raw[:200])


def make_ctx(insecure: bool):
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


class OrderApiBlocked(RuntimeError):
    """주문 계열 호출 시도 — 절대 나가면 안 된다."""


# 인증 목적의 유일한 예외. 그 외 비-GET은 전부 차단.
_AUTH_POST = "/oauth2/token"


def _assert_readonly(method: str, path: str) -> None:
    """조회 전용 불변식. req() 진입부에서 호출되며 네트워크보다 먼저 판정한다."""
    m = (method or "").upper()
    # 쿼리스트링·대소문자·중복 슬래시로 우회되지 않게 정규화
    base = (path or "").split("?", 1)[0].split("#", 1)[0]
    while "//" in base:
        base = base.replace("//", "/")
    base = base.rstrip("/").lower() or "/"
    if m == "GET":
        return
    if m == "POST" and base == _AUTH_POST:
        return
    raise OrderApiBlocked(
        f"차단: {m} {path} — 이 스크립트는 조회 전용이다. "
        f"허용 = GET 전체 + POST {_AUTH_POST} 뿐. "
        "주문·조건주문 호출은 코드 레벨에서 금지돼 있다(정훈 영구 룰)."
    )


def req(method, path, ctx, headers=None, data=None, form=False):
    _assert_readonly(method, path)
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
        # 토스는 오류 본문도 gzip으로 준다 — 그냥 decode()하면 에러 처리기 자신이 죽어서
        # 정작 원인 메시지를 못 본다(8/31 실측: UnicodeDecodeError 0x8b = gzip 매직).
        err = _decode_body(e.read())[:500]
        print(f"[HTTP {e.code}] {method} {path}: {err}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERR] {method} {path}: {e}", file=sys.stderr)
        return None


def _selftest() -> int:
    """가드가 '있다'가 아니라 '이 사례를 잡는가'를 확인한다 (8/23 규약).
    네트워크를 타기 전에 raise 되므로 키 없이 검증된다."""
    must_block = [
        ("POST", "/api/v1/orders"),                        # 주문 생성
        ("POST", "/api/v1/orders/abc123/cancel"),          # 주문 취소
        ("POST", "/api/v1/orders/abc123/modify"),          # 주문 정정
        ("POST", "/api/v1/conditional-orders"),            # 조건주문 생성
        ("DELETE", "/api/v1/conditional-orders/xyz"),      # 조건주문 취소
        ("POST", "/api/v1/conditional-orders/xyz/modify"),
        ("PUT", "/api/v1/orders"),
        ("PATCH", "/api/v1/orders"),
        ("post", "/api/v1/ORDERS"),                        # 대소문자 우회
        ("POST", "/api/v1//orders"),                       # 중복 슬래시 우회
        ("POST", "/api/v1/orders?x=1"),                    # 쿼리 우회
        ("POST", "/api/v1/orders/"),                       # 후행 슬래시 우회
        ("POST", "/oauth2/token/../api/v1/orders"),        # 경로 트릭
    ]
    must_pass = [
        ("GET", "/api/v1/accounts"),
        ("GET", "/api/v1/holdings"),
        ("GET", "/api/v1/orders"),                         # 주문 *이력* 조회는 허용
        ("GET", "/api/v1/orders?status=CLOSED&limit=100"),
        ("GET", "/api/v1/stocks/005930/short-selling"),
        ("POST", "/oauth2/token"),                         # 인증만 예외
    ]
    fails = []
    for m, path in must_block:
        try:
            _assert_readonly(m, path)
            fails.append(f"  ❌ 통과시킴(막았어야 함): {m} {path}")
        except OrderApiBlocked:
            pass
    for m, path in must_pass:
        try:
            _assert_readonly(m, path)
        except OrderApiBlocked:
            fails.append(f"  ❌ 막음(통과시켰어야 함): {m} {path}")
    print(f"■ 토스 주문 차단 가드 자가검증 — 차단 {len(must_block)}건 · 허용 {len(must_pass)}건")
    if fails:
        print(chr(10).join(fails))
        print("🔴 FAIL — 가드가 뚫린다. 키를 쓰지 말 것.")
        return 1
    print("✅ PASS — 주문 계열 전부 차단, 조회 경로 전부 통과")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default=os.environ.get("TOSS_CLIENT_ID"))
    ap.add_argument("--secret", default=os.environ.get("TOSS_CLIENT_SECRET"))
    ap.add_argument("--raw", action="store_true", help="원본 JSON 전체 출력")
    ap.add_argument("--insecure", action="store_true",
                    help="자가서명 인증서 프록시 뒤일 때만: TLS 검증 끔(보안 저하)")
    ap.add_argument("--selftest", action="store_true",
                    help="주문 차단 가드 자가검증(네트워크·키 불필요)")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()
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
    raise SystemExit(main() or 0)
