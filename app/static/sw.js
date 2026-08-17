/* Network-first service worker: always prefer fresh content, fall back to
   cache so the app shell still opens offline. API calls are never cached. */
const CACHE = "menu-alchemist-v4";
const SHELL = [
  "/",
  "/styles.css",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/app.js",
  "/api.js",
  "/connection.js",
  "/paneco.js",
  "/photo-picker.js",
  "/render.js",
  "/router.js",
  "/state.js",
  "/ui.js",
  "/views/analyze.js",
  "/views/auth.js",
  "/views/bar.js",
  "/views/classics.js",
  "/views/favorites.js",
  "/views/tutorial.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.pathname.startsWith("/api/")) return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((c) => c.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request, { ignoreSearch: true }))
  );
});
