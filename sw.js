// ElderSOS Service Worker for PWA Support and Offline Resilience
const CACHE_NAME = 'eldersos-spa-v2';
const STATIC_ASSETS = [
  '/',
  '/static/index.html',
  '/static/style.css',
  '/static/script.js',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // API calls: always network, never cache
  if (url.pathname.startsWith('/api/')) return;

  // Navigation requests: network-first, fallback to index.html for SPA
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match('/static/index.html').then((cached) => {
          return cached || new Response(
            `<!DOCTYPE html>
            <html lang="en"><head><meta charset="utf-8"><title>ElderSOS - Offline</title>
            <link rel="stylesheet" href="/static/style.css"></head>
            <body style="padding:24px;text-align:center;">
              <div class="card" style="max-width:600px;margin:40px auto;">
                <h1 style="color:#c92a2a;font-size:2rem;">📵 Offline Mode</h1>
                <p style="font-size:1.2rem;margin:16px 0;">
                  You appear to be offline. In an emergency, please use your phone keypad immediately:
                </p>
                <a href="tel:112" style="display:block;background:#c92a2a;color:#fff;padding:20px;font-size:1.5rem;border-radius:12px;margin-top:16px;text-decoration:none;font-weight:900;">
                  🚨 Call 112 (National Emergency)
                </a>
              </div>
            </body></html>`,
            { headers: { 'Content-Type': 'text/html' } }
          );
        });
      })
    );
    return;
  }

  // Static assets: cache-first, update in background
  if (url.pathname.startsWith('/static/') || url.pathname === '/manifest.json') {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        const fetchPromise = fetch(event.request).then((networkResponse) => {
          if (networkResponse.status === 200) {
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, networkResponse.clone()));
          }
          return networkResponse;
        });
        return cachedResponse || fetchPromise;
      })
    );
  }
});
