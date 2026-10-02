// Минимальный service worker.
// Кэширует index.html и manifest.json.
// Pyodide (~25 МБ) НЕ кэшируется — iOS Safari сам кэширует CDN.

const CACHE = "polilog-v1";
const ASSETS = ["./index.html", "./manifest.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (e) => {
  e.respondWith(
    caches.match(e.request).then((r) => r || fetch(e.request))
  );
});