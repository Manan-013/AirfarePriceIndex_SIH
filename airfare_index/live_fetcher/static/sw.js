/**
 * AeroDex — Real-Time Airfare Price Index
 * Progressive Web App Service Worker
 * Version: aerodex-pwa-v1.0.0
 */

const CACHE_NAME = 'aerodex-static-v2';
const API_CACHE_NAME = 'aerodex-api-v2';

const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/logo.png',
  '/favicon.ico',
  '/icon-192x192.png',
  '/icon-512x512.png',
  '/icon-maskable-192x192.png',
  '/icon-maskable-512x512.png',
  '/apple-touch-icon.png'
];

// Install: Cache essential app shell assets individually
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      console.log('[AeroDex PWA] Precaching core application shell (v2)');
      for (const asset of PRECACHE_ASSETS) {
        try {
          await cache.add(asset);
        } catch (err) {
          console.warn('[AeroDex PWA] Precache warning for', asset, err);
        }
      }
    }).then(() => self.skipWaiting())
  );
});

// Activate: Purge obsolete caches and claim clients immediately
self.addEventListener('activate', (event) => {
  const currentCaches = [CACHE_NAME, API_CACHE_NAME];
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (!currentCaches.includes(key)) {
            console.log('[AeroDex PWA] Removing outdated cache:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: Network-First for APIs, Cache-First with Background Revalidation for Assets
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignore non-GET requests
  if (request.method !== 'GET') return;

  // CRITICAL: NEVER intercept cross-origin third-party requests (e.g. Tailwind CDN, Chart.js CDN, Google Fonts).
  // Intercepting external CDNs causes CORS/opaque response failures and 503 errors on modern phones (e.g. Samsung Galaxy S24).
  if (url.origin !== self.location.origin) {
    return;
  }

  // 1. Dynamic API Endpoints: Network-First with Cache Fallback
  if (url.pathname.startsWith('/api/v1/')) {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseClone = networkResponse.clone();
            caches.open(API_CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return networkResponse;
        })
        .catch(async () => {
          const cached = await caches.match(request);
          if (cached) {
            return cached;
          }
          return new Response(
            JSON.stringify({
              status: 'OFFLINE',
              offline: true,
              message: 'Offline mode active. Real-time background feed will resume when internet reconnects.',
              timestamp: new Date().toLocaleTimeString()
            }),
            {
              headers: { 'Content-Type': 'application/json' },
              status: 200
            }
          );
        })
    );
    return;
  }

  // 2. Static Assets & Navigation (App Shell)
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        // Fetch in background to update cache
        fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            caches.open(CACHE_NAME).then((cache) => cache.put(request, networkResponse));
          }
        }).catch(() => {});
        return cachedResponse;
      }

      // Not in cache, try network
      return fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, responseToCache));
          }
          return networkResponse;
        })
        .catch(async () => {
          // If offline and navigation request, return cached root or index.html
          if (request.mode === 'navigate') {
            const cachedIndex = (await caches.match('/')) || (await caches.match('/index.html'));
            if (cachedIndex) return cachedIndex;
          }
          if (request.destination === 'image' || request.destination === 'font' || request.destination === 'style' || request.destination === 'script') {
            return new Response('', { status: 404, statusText: 'Not Found' });
          }
          return new Response('Offline', { status: 503, statusText: 'Offline' });
        });
    })
  );
});
