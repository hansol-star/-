#!/usr/bin/env node
// 경제사냥꾼 자막 폴백: 실제 Chromium으로 watch 페이지를 열어 자막을 확보한다.
// 사용: node browser_captions.cjs <videoId>   → 마지막 줄에 JSON {title,date,text} 출력
//
// [7/2 실측 메모 — 웹(프록시) 환경]
//  - Chromium 자체 네트워킹은 egress 게이트웨이와 TLS가 안 맞아 실패
//    → HTTPS_PROXY 감지 시 모든 요청을 Node fetch로 라우팅(아래 route 인터셉션)하면
//      페이지 로드·봇체크 통과·메타데이터 확보까지 정상 (실측 OK).
//  - 단 웹 환경에선 watch 페이지 caption URL이 pot 토큰을 요구해 텍스트가 빈 응답일 수 있음.
//    이 스크립트는 ①페이지 내 직접 fetch ②CC 켜고 플레이어 요청 스니핑 순으로 시도한다.
//  - 로컬(주거 IP, 12월 이전 후): 프록시 없음 → 라우팅 불필요, pot 요구도 드묾 → 완전 동작 예상.
//  - 요구: playwright 모듈(전역이면 NODE_PATH=/opt/node22/lib/node_modules),
//          NODE_USE_ENV_PROXY=1, NODE_EXTRA_CA_CERTS=<프록시 CA>(웹 환경만).
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
  // Chromium 네트워킹 대신 Node fetch 사용 (undici가 HTTPS_PROXY/CA 환경변수를 읽음)
  await ctx.route('**/*', async (route) => {
    const req = route.request();
    if (['image', 'font'].includes(req.resourceType())) return route.abort();
    try {
      const resp = await fetch(req.url(), {
        method: req.method(), headers: req.headers(),
        body: req.postDataBuffer() || undefined, redirect: 'manual',
      });
      const body = Buffer.from(await resp.arrayBuffer());
      const headers = {};
      resp.headers.forEach((v, k) => {
        if (!['content-encoding', 'transfer-encoding', 'content-length'].includes(k)) headers[k] = v;
      });
      await route.fulfill({ status: resp.status, headers, body });
    } catch { try { await route.abort(); } catch {} }
  });
}

function parseTimedtext(raw) {
  let text = '';
  if (!raw) return text;
  if (raw.trim().startsWith('{')) {
    const d = JSON.parse(raw);
    text = (d.events || []).filter((e) => e.segs)
      .map((e) => e.segs.map((s) => s.utf8 || '').join('')).join(' ');
  } else {
    const segs = raw.match(/<s[^>]*>([^<]*)<\/s>/g) || raw.match(/<p[^>]*>([^<]*)<\/p>/g) || [];
    text = segs.map((s) => s.replace(/<[^>]+>/g, '')).join(' ');
  }
  return text.replace(/\s+/g, ' ').trim();
}

(async () => {
  const vid = process.argv[2];
  if (!vid) { console.error('usage: node browser_captions.cjs <videoId>'); process.exit(2); }
  const browser = await chromium.launch({
    args: ['--no-sandbox', '--autoplay-policy=no-user-gesture-required'],
    executablePath: findChrome(),
  });
  try {
    const ctx = await browser.newContext({ locale: 'ko-KR' });
    if (process.env.HTTPS_PROXY) await routeThroughNode(ctx);
    const page = await ctx.newPage();
    let sniffed = null;
    page.on('response', async (r) => {
      if (r.url().includes('/api/timedtext') && !sniffed) {
        try { const t = await r.text(); if (t && t.length > 100) sniffed = t; } catch {}
      }
    });
    await page.goto(`https://www.youtube.com/watch?v=${vid}`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(4000);
    const pr = await page.evaluate(() => {
      const p = window.ytInitialPlayerResponse || {};
      const tr = (((p.captions || {}).playerCaptionsTracklistRenderer || {}).captionTracks || [])
        .map((t) => ({ lang: t.languageCode, url: t.baseUrl }));
      return {
        title: (p.videoDetails || {}).title || '',
        date: ((p.microformat || {}).playerMicroformatRenderer || {}).publishDate || '',
        tracks: tr,
      };
    });
    let raw = '';
    if (pr.tracks.length) {
      const track = pr.tracks.find((t) => t.lang === 'ko') || pr.tracks[0];
      raw = await page.evaluate(async (u) => (await fetch(u + '&fmt=json3')).text(), track.url);
    }
    if (!raw || raw.length < 100) {
      // 플레이어가 pot을 붙여 직접 요청하도록 재생+CC 시도 후 스니핑
      try { await page.click('button.ytp-large-play-button', { timeout: 5000 }); } catch {}
      try { await page.keyboard.press('k'); } catch {}
      try { await page.click('button.ytp-subtitles-button', { timeout: 8000 }); } catch {}
      for (let i = 0; i < 15 && !sniffed; i++) await page.waitForTimeout(1000);
      raw = sniffed || raw;
    }
    console.log(JSON.stringify({ title: pr.title, date: pr.date, text: parseTimedtext(raw) }));
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error(e.message); process.exit(1); });
