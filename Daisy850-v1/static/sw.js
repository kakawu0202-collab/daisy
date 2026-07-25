// Service Worker for 850 Toolbox PWA
// Strategy: Network First for data, Cache First for static assets

const CACHE_NAME = '850tb-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/k1.html',
  '/shipped.html',
  '/sort.html',
  '/fga870.html',
  '/offline.html',
  '/app.js',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
];

// ── Install: pre-cache static shell ──────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('[SW] Pre-caching app shell...');
      return cache.addAll(STATIC_ASSETS).catch(err => {
        console.warn('[SW] Some assets failed to pre-cache:', err);
      });
    })
  );
  self.skipWaiting();
});

// ── Activate: clean old caches ───────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// ── Fetch: smart strategy per resource type ──────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // API calls: Network First, fallback to cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  // HTML pages: Network First (always get latest version)
  if (url.pathname.endsWith('.html') || url.pathname === '/' || STATIC_ASSETS.some(a => url.pathname.endsWith(a) && a.endsWith('.html'))) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  // Static assets (JS, CSS, icons): Cache First with background update
  if (STATIC_ASSETS.some(a => url.pathname.endsWith(a) || url.pathname === a)) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // CDN scripts (Chart.js etc): Cache First
  if (url.hostname.includes('cdn.jsdelivr.net') || url.hostname.includes('cdnjs.cloudflare.com')) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // Everything else: Network First
  event.respondWith(networkFirst(event.request));
});

// ── Network First helper ─────────────────────────────────────
function networkFirst(request) {
  return fetch(request)
    .then(response => {
      if (!response || response.status !== 200) return response;
      const cloned = response.clone();
      caches.open(CACHE_NAME).then(cache => cache.put(request, cloned));
      return response;
    })
    .catch(() => {
      return caches.match(request).then(cached => {
        return cached || caches.match('/offline.html');
      });
    });
}

// ── Cache First helper ───────────────────────────────────────
function cacheFirst(request) {
  return caches.match(request).then(cached => {
    if (cached) {
      // Background update
      fetch(request).then(response => {
        if (response && response.status === 200) {
          caches.open(CACHE_NAME).then(cache => cache.put(request, response));
        }
      }).catch(() => {});
      return cached;
    }
    return networkFirst(request);
  });
}

// ── Push notification (future: data update alerts) ───────────
self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || '850 Toolbox';
  const options = {
    body: data.body || '数据已更新',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    tag: 'data-update',
    renotify: true
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(clientList => {
      for (const client of clientList) {
        if (client.url && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow('/');
    })
  );
});
