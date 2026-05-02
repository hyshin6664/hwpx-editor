// Solbox Docs SW — index.html 은 항상 네트워크 우선(새 버전 즉시 반영), 그 외만 cache-first
const CACHE = 'solbox-docs-v5';
const ASSETS = ['./manifest.json', './icon-192.svg', './icon-512.svg', './voice-worker.js'];
// Moonshine 모델 + transformers.js + VAD 는 Range request 를 자주 쓰므로 별도 캐시
const MOONSHINE_CACHE = 'solbox-moonshine-v1';

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).catch(()=>{}));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim()).then(async () => {
      // 새 SW 활성화 직후 모든 컨트롤된 클라이언트에게 강제 새로고침 메시지 발송
      // (구버전 page 가 controllerchange 리스너 없어서 자동 reload 못 하는 케이스 커버)
      try {
        const list = await self.clients.matchAll({ type: 'window' });
        list.forEach(c => { try { c.postMessage({ type: 'SW_FORCE_RELOAD' }); } catch(_){} });
      } catch(_){}
    })
  );
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
  // Moonshine 모델 / transformers.js / VAD (cdn.jsdelivr 또는 huggingface.co) — 별도 캐시 cache-first
  // 첫 다운로드 후 영구 캐싱 (50MB 모델은 한 번만 받음)
  if (/cdn\.jsdelivr\.net.*(transformers|moonshine|vad-web|onnxruntime)/.test(req.url)
      || /huggingface\.co.*moonshine/.test(req.url)) {
    e.respondWith(
      caches.open(MOONSHINE_CACHE).then(cache =>
        cache.match(req).then(cached => cached || fetch(req).then(res => {
          // ok response 만 캐싱 (range request 의 partial 206 는 제외)
          if (res.ok && res.status === 200) cache.put(req, res.clone()).catch(()=>{});
          return res;
        }))
      )
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
