// Solbox Docs SW — index.html 은 항상 네트워크 우선(새 버전 즉시 반영), 그 외만 cache-first
const CACHE = 'solbox-docs-v4';
const ASSETS = ['./manifest.json', './icon-192.svg', './icon-512.svg'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).catch(()=>{}));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return; // CDN 패스

  // index.html / 루트 / HTML — network-first (항상 최신)
  const isHtml = url.pathname.endsWith('/') || url.pathname.endsWith('/index.html') || req.destination === 'document';
  if (isHtml) {
    e.respondWith(
      fetch(req).then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy)).catch(()=>{});
        return res;
      }).catch(() => caches.match(req).then(c => c || caches.match('./index.html')))
    );
    return;
  }
  // 그 외 (manifest, sw.js, 정적 자원) — cache-first
  e.respondWith(
    caches.match(req).then(cached => cached || fetch(req).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(req, copy)).catch(()=>{});
      return res;
    }).catch(() => null))
  );
});
