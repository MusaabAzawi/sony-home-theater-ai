/**
 * SonyHub Service Worker - v1.0.0
 * Provides offline caching, high-speed app shell loading,
 * stale-while-revalidate for CDN libraries, and network-first bypass for local hardware APIs.
 */

const CACHE_NAME = 'sonyhub-v1';

// Core Application Shell assets to cache immediately upon installation
const PRECACHE_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon.svg'
];

// Domains and URL patterns designated for Stale-While-Revalidate caching (CDNs & Fonts)
const CDN_ORIGINS = [
  'cdn.tailwindcss.com',
  'cdn.jsdelivr.net',
  'unpkg.com',
  'fonts.googleapis.com',
  'fonts.gstatic.com',
  'images.unsplash.com'
];

/**
 * INSTALL EVENT
 * Pre-caches the core application shell for instant standalone launches on iPhone and TV.
 */
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SonyHub SW] Pre-caching core application shell assets...');
        return cache.addAll(PRECACHE_ASSETS);
      })
      .then(() => {
        // Activate immediately without waiting for existing tabs to close
        return self.skipWaiting();
      })
      .catch((error) => {
        console.warn('[SonyHub SW] Pre-cache warning:', error);
      })
  );
});

/**
 * ACTIVATE EVENT
 * Cleans up legacy cache versions and claims active client windows.
 */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SonyHub SW] Purging obsolete cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SonyHub SW] SonyHub Service Worker activated and claimed clients.');
      return self.clients.claim();
    })
  );
});

/**
 * FETCH EVENT
 * Routes requests based on target URL and resource type:
 * 1. Hardware/AI API calls (ports 8000, 8001, /ir/, /health, /recommend) -> Network-first (NEVER cache mutating commands)
 * 2. Third-party CDN libraries and assets -> Stale-While-Revalidate
 * 3. Local App Shell (HTML, Manifest, SVG) -> Cache-First with Network fallback
 */
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Bypass non-GET requests (e.g. POST to IR daemon or Spotify actions)
  if (request.method !== 'GET') {
    return;
  }

  // 1. HARDWARE & AI API ROUTING (localhost:8000, localhost:8001, IR endpoints)
  // Strategy: Network-first. Mutating commands or real-time measurements must never serve stale caches.
  const isApiRequest =
    url.port === '8000' ||
    url.port === '8001' ||
    url.pathname.startsWith('/ir/') ||
    url.pathname.startsWith('/recommend') ||
    url.pathname.startsWith('/health') ||
    url.pathname.startsWith('/status');

  if (isApiRequest) {
    event.respondWith(
      fetch(request)
        .catch(() => {
          // If offline or hardware daemon not running, return JSON fallback
          return new Response(
            JSON.stringify({
              status: 'offline',
              message: 'Local hardware daemon is currently unreachable.'
            }),
            {
              status: 503,
              headers: { 'Content-Type': 'application/json' }
            }
          );
        })
    );
    return;
  }

  // 2. THIRD-PARTY CDN RESOURCES (Tailwind, Lucide, Alpine, Google Fonts, Unsplash)
  // Strategy: Stale-While-Revalidate (serve fast from cache, update in background)
  const isCdn = CDN_ORIGINS.some((origin) => url.hostname.includes(origin));

  if (isCdn) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.match(request).then((cachedResponse) => {
          const fetchPromise = fetch(request)
            .then((networkResponse) => {
              if (networkResponse && networkResponse.status === 200) {
                cache.put(request, networkResponse.clone());
              }
              return networkResponse;
            })
            .catch(() => cachedResponse);

          return cachedResponse || fetchPromise;
        });
      })
    );
    return;
  }

  // 3. CORE APP SHELL & LOCAL STATIC ASSETS
  // Strategy: Cache-first with network fallback
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(request)
        .then((networkResponse) => {
          // Cache successful GET responses for local static files
          if (
            networkResponse &&
            networkResponse.status === 200 &&
            networkResponse.type === 'basic'
          ) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // If completely offline and looking for navigation, return cached index.html
          if (request.mode === 'navigate') {
            return caches.match('./index.html');
          }
        });
    })
  );
});
