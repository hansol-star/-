/* 정훈 증권 PWA 서비스워커 — 앱 셸 캐시 + 오프라인 동작.
   data.js는 네트워크 우선(최신 시세) → 실패 시 캐시. 셸은 캐시 우선. */
var CACHE = "jh-portfolio-202609211827";
var SHELL = [
  "./index.html",
  "./style.css",
  "./app.js",
  "./manifest.webmanifest",
  "./icons/icon-180.png",
  "./icons/icon-192.png",
  "./icons/icon-512.png"
];

// ★[9/21] 셸을 { cache: "reload" }로 받는다 — 기본 addAll은 **브라우저 HTTP 캐시**를 거쳐서,
//   CACHE 버전이 바뀌어도 옛 app.js가 새 캐시에 그대로 들어갈 수 있었다(버전 bump가 무력화).
//   9/21 로컬 미리보기에서 실측: 버전은 새것인데 셸은 수정 전 app.js였다.
self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) {
    return c.addAll(SHELL.map(function (u) { return new Request(u, { cache: "reload" }); }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  var url = e.request.url;
  // data.js: 네트워크 우선(최신 시세), 실패 시 캐시
  if (url.indexOf("data.js") !== -1) {
    e.respondWith(
      fetch(e.request).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        return res;
      }).catch(function () { return caches.match(e.request); })
    );
    return;
  }
  // 그 외: 캐시 우선 → 네트워크 폴백
  e.respondWith(caches.match(e.request).then(function (cached) {
    return cached || fetch(e.request).then(function (res) {
      var copy = res.clone();
      caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
      return res;
    });
  }));
});
