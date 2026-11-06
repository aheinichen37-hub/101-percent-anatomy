/* 101% Anatomy service worker (v2.6).
   Keeps the app shell so the home-screen icon opens without a connection.
   The page itself is network-first, so a new version is never shadowed by an old cache.
   Figures are deliberately NOT cached: 500+ images would crowd the device's storage,
   and crowded storage is what gets a save evicted. */
const CACHE = "anat101-shell-v2.6";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", e => e.waitUntil((async () => {
  const keys = await caches.keys();
  await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
  await self.clients.claim();
})()));

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  let url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== location.origin) return;          // fonts and the like: straight to the network
  if (url.pathname.includes("/figs/")) return;         // see note above

  if (req.mode === "navigate" || req.destination === "document") {
    e.respondWith((async () => {
      try {
        const res = await fetch(req);
        if (res && res.ok) (await caches.open(CACHE)).put(req, res.clone());
        return res;
      } catch (err) {
        const c = await caches.open(CACHE);
        return (await c.match(req)) || (await c.match("index.html")) || Response.error();
      }
    })());
    return;
  }

  e.respondWith((async () => {
    const c = await caches.open(CACHE);
    const hit = await c.match(req);
    if (hit) return hit;
    try {
      const res = await fetch(req);
      if (res && res.ok && res.type === "basic") c.put(req, res.clone());
      return res;
    } catch (err) {
      return Response.error();
    }
  })());
});
