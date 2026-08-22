#!/usr/bin/env node
// web_shot.cjs — 웹페이지를 PNG로 캡처한다(에이전트가 Read로 '화면을 보는' 경로).
// 호출: node web_shot.cjs '<옵션JSON>'   → 마지막 줄에 JSON {path,title,w,h}
//
// [8/22 실측 — 웹(데이터센터 IP)]
//  - Chromium 자체 네트워킹은 egress 게이트웨이와 TLS가 안 맞음 → 모든 요청을 Node fetch로
//    라우팅(browser_captions.cjs와 동일 패턴). 네이버금융 실측 200·판독 OK.
//  - ⚠️ YouTube watch 페이지는 reCAPTCHA 벽(재생 프레임 캡처 불가). 영상 프레임은
//    이 경로로도 안 된다 — 썸네일(i.ytimg.com)만 열린다.
const { chromium } = require('playwright');

function findChrome() {
  const fs = require('fs');
  const base = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  try {
    const dir = fs.readdirSync(base).find((d) => /^chromium-\d+$/.test(d));
    if (dir) return `${base}/${dir}/chrome-linux/chrome`;
  } catch {}
  return undefined;
}

async function routeThroughNode(ctx) {
  await ctx.route('**/*', async (route) => {
    const req = route.request();
    // ★[8/22] 로컬(file://·localhost·127.0.0.1)은 Node fetch로 라우팅하면 안 된다 —
    //   fetch가 file 스킴을 못 열어 페이지 자체가 실패한다(우리 앱 app/index.html 캡처 시 발견).
    //   프록시는 외부 호스트에만 필요하므로 로컬은 Chromium이 직접 처리하게 넘긴다.
    const u = req.url();
    if (/^file:|^https?:\/\/(localhost|127\.0\.0\.1)(:|\/)/.test(u)) return route.continue();
    if (req.resourceType() === 'font') return route.abort();
    try {
      const res = await fetch(req.url(), {
        method: req.method(),
        headers: req.headers(),
        body: ['GET', 'HEAD'].includes(req.method()) ? undefined : req.postDataBuffer(),
        redirect: 'follow',
      });
      await route.fulfill({
        status: res.status,
        headers: Object.fromEntries(res.headers),
        body: Buffer.from(await res.arrayBuffer()),
      });
    } catch {
      try { await route.abort(); } catch {}
    }
  });
}

(async () => {
  const o = JSON.parse(process.argv[2] || '{}');
  const browser = await chromium.launch({ executablePath: findChrome(), args: ['--no-sandbox'] });
  const ctx = await browser.newContext({
    viewport: { width: o.width || 1280, height: o.height || 900 },
    deviceScaleFactor: o.scale || 1,
    locale: 'ko-KR',
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
             + '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  });
  if (process.env.HTTPS_PROXY || process.env.https_proxy) await routeThroughNode(ctx);
  const page = await ctx.newPage();
  try {
    await page.goto(o.url, { waitUntil: 'domcontentloaded', timeout: (o.timeout || 60) * 1000 });
    await page.waitForTimeout((o.wait ?? 3) * 1000);
    let target = page;
    if (o.selector) {
      const el = await page.$(o.selector);
      if (!el) throw new Error(`selector 미발견: ${o.selector}`);
      target = el;
    }
    await target.screenshot({ path: o.out, fullPage: o.selector ? undefined : !!o.full });
    const title = await page.title();
    console.log(JSON.stringify({ path: o.out, title, ok: true }));
  } catch (e) {
    console.log(JSON.stringify({ ok: false, error: String(e.message).slice(0, 300) }));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
