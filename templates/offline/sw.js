// Scope is /offline/ only. Never cache server-rendered catalogue or private HTML.
const CACHE = 'rumi-library-offline-shell-{{ version }}';
const ASSETS = {{ assets_json|safe }};
const ALLOWED = new Set(ASSETS.map(path => new URL(path, self.location.origin).href));
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    try {
      for (const path of ASSETS) {
        const request = new Request(path, {credentials: 'omit', cache: 'reload'});
        const response = await fetch(request);
        if (!response.ok || response.redirected) throw new Error('Offline asset unavailable');
        await cache.put(request, response);
      }
    } catch (error) { await caches.delete(CACHE); throw error; }
  })());
  // No skipWaiting: an update waits for old offline tabs to close.
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith('rumi-library-offline-shell-') && name !== CACHE) await caches.delete(name);
    }
  })());
  // No clients.claim or forced reload, especially on pages with unsaved work.
});
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return; // No mutation queue or replay.
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  const shell = url.pathname === '/offline/' && request.mode === 'navigate';
  const key = shell ? new URL('/offline/', self.location.origin).href : request.url;
  if (!ALLOWED.has(key)) return; // Snapshot, private APIs, admin and login stay network-only.
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    return (await cache.match(key, {ignoreVary: true})) || fetch(new Request(key, {credentials: 'omit'}));
  })());
});
