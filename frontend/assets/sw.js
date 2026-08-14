/* Service worker v32: ID+EPP alternado */
const CACHE = "vigiepp-shell-v32";
const ASSETS = ["/assets/styles.css?v=32", "/assets/app.js?v=32", "/assets/favicon.png", "/assets/manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
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
  if (url.pathname === "/" || url.pathname.endsWith(".html")) {
    event.respondWith(fetch(req));
    return;
  }
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok && url.pathname.startsWith("/assets/")) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() =>
        caches.match(req).then((hit) => {
          if (hit) return hit;
          return new Response("VigiEPP offline", {
            status: 503,
            headers: { "Content-Type": "text/plain; charset=utf-8" },
          });
        })
      )
  );
});
