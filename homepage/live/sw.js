// Sahyog Setu service worker (2026-09-20, PWA install support).
//
// Network-first for everything, cache only as an offline fallback -- NOT
// cache-first. This is a live government-schemes content site (scheme
// details, eligibility info, helplines/documents/portals listings) that
// changes over time; a cache-first worker risks an installed PWA showing
// stale scheme information indefinitely. Every request here always tries
// the network first; the cache is only ever read when the network
// genuinely fails (offline), which is a strictly additive capability.
//
// /api/, /admin/, /accounts/ and any non-GET request are never cached or
// intercepted at all -- those are the Django-backed dynamic/authenticated
// routes (see NGINX_CONFIG_REFERENCE_sahyogsetu.conf), never static
// content the React SPA shell can safely stand in for offline.

const CACHE_NAME = 'sahyogsetu-shell-v1';
const SHELL_URLS = [
  '/',
  '/manifest.json',
  '/logo192.png',
  '/logo512.png',
];
const NEVER_CACHE_PREFIXES = ['/api/', '/admin/', '/accounts/', '/quizzes', '/quiz'];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_URLS)).catch(() => {})
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // never intercept cross-origin (CDN css/js, GTM, etc.)
  if (NEVER_CACHE_PREFIXES.some((p) => url.pathname.startsWith(p))) return;

  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() => caches.match(req).then((cached) => cached || caches.match('/')))
  );
});
