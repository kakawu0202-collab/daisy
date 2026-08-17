// Service Worker — pass-through mode (no caching)
// Purpose: eliminate stale cache issues. Everything goes to network.
const CACHE_NAME = 'scos-pass-through-v1';

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k)))).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  // Pass through — never cache, never serve stale
  event.respondWith(fetch(event.request));
});

self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'Yumin K1';
  const options = {
    body: data.body || 'K1 data updated',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    tag: 'yumin-data-update',
    renotify: true,
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(clientList => {
      for (const client of clientList) {
        if (client.url && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow('/');
    })
  );
});
