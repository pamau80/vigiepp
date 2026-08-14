/* Service worker: shell cache + fallback offline (sin API) */
const CACHE = "vigiepp-shell-v24";
const SHELL = ["/", "/assets/styles.css", "/assets/app.js", "/assets/favicon.png", "/assets/manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.pathname.startsWith("/api/")) return;
  event.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        if (res.ok && (url.pathname === "/" || url.pathname.startsWith("/assets/"))) {
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() =>
        caches.match(req).then((hit) => hit || caches.match("/")).then((fallback) => {
          if (fallback) return fallback;
          return new Response("VigiEPP offline", {
            status: 503,
            headers: { "Content-Type": "text/plain; charset=utf-8" },
          });
        })
      )
  );
});
