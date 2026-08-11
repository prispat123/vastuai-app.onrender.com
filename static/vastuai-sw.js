const CACHE = 'vastuai-pwa-assets-v1';
const ASSETS = [
  '/app/static/manifest.webmanifest',
  '/app/static/vastuai-192.png',
  '/app/static/vastuai-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (!url.pathname.startsWith('/app/static/')) return;
  event.respondWith(
    caches.match(event.request).then(hit => hit || fetch(event.request))
  );
});
