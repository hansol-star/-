/* 정훈 증권 PWA 서비스워커 — 앱 셸 캐시 + 오프라인 동작.
   ★[9/21 리디자인] 세 갈래:
     · live.json  = 실시간 시세 → 항상 네트워크(no-store). 실패 시에만 마지막 사본(오프라인 표시용)
     · data.js    = 분석 정본   → 네트워크 우선, 실패 시 캐시
     · 웹폰트     = Google Fonts → 별도 캐시, 캐시 우선(한 번 받으면 오프라인에서도 같은 글꼴)
     · 그 외 셸   = 캐시 우선 */
var CACHE = "jh-portfolio-202609212157";
var FONTS = "jh-fonts-v1";
var SHELL = [
  "./index.html",
  "./style.css",
  "./app.js",
  "./manifest.webmanifest",
  "./icons/icon-180.png",
  "./icons/icon-192.png",
  "./icons/icon-512.png"
];

// 셸을 { cache: "reload" }로 받는다 — 기본 addAll은 브라우저 HTTP 캐시를 거쳐서,
//   CACHE 버전이 바뀌어도 옛 app.js가 새 캐시에 그대로 들어갈 수 있었다(9/21 실측).
self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) {
    return c.addAll(SHELL.map(function (u) { return new Request(u, { cache: "reload" }); }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE && k !== FONTS; }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

function networkFirst(req, key) {
  return fetch(req).then(function (res) {
    if (res && res.ok) { var copy = res.clone(); caches.open(CACHE).then(function (c) { c.put(key || req, copy); }); }
    return res;
  }).catch(function () { return caches.match(key || req); });
}

self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  var url = e.request.url;
  // 실시간 시세: 캐시 키는 쿼리(?t=) 없는 주소 하나 — 사본이 쌓이지 않게
  if (url.indexOf("live.json") !== -1) {
    e.respondWith(networkFirst(new Request(url, { cache: "no-store" }), url.split("?")[0]));
    return;
  }
  if (url.indexOf("data.js") !== -1) { e.respondWith(networkFirst(e.request)); return; }
  if (url.indexOf("fonts.googleapis.com") !== -1 || url.indexOf("fonts.gstatic.com") !== -1) {
    e.respondWith(caches.open(FONTS).then(function (c) {
      return c.match(e.request).then(function (hit) {
        return hit || fetch(e.request).then(function (res) { if (res && (res.ok || res.type === "opaque")) c.put(e.request, res.clone()); return res; });
      });
    }));
    return;
  }
  e.respondWith(caches.match(e.request).then(function (cached) {
    return cached || fetch(e.request).then(function (res) {
      if (res && res.ok && url.indexOf(self.location.origin) === 0) { var copy = res.clone(); caches.open(CACHE).then(function (c) { c.put(e.request, copy); }); }
      return res;
    });
  }));
});
