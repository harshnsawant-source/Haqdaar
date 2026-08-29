/*
 * Haqdaar service worker.
 *
 * Offline is part of the pitch, not packaging: the citizen this is built for is at a
 * Panchayat or CSC on a bad connection. So this actually caches, and the honesty rules
 * that govern the engine govern it too.
 *
 * Two caches, deliberately different:
 *
 *   SHELL  — app shell, precached on install, cache-first. The app opens with no
 *            network at all.
 *   DATA   — /api responses, network-first with a cache fallback. Fresh when online,
 *            last-known when not.
 *
 * WHY NETWORK-FIRST FOR DATA, AND WHY IT IS STAMPED:
 * A cached verdict can go stale in a way that matters — a rule may be amended after we
 * served it (that is exactly what T5 exists to flag). Serving a cached card silently
 * would be the UI telling a citizen something the engine would no longer say. So a
 * cached response is stamped with `x-haqdaar-offline` and the age it was stored, and
 * the UI must show that it is looking at a stored answer. Never present cached as live.
 */

const VERSION = 'v1';
const SHELL_CACHE = `haqdaar-shell-${VERSION}`;
const DATA_CACHE = `haqdaar-data-${VERSION}`;

const SHELL_ASSETS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/icon.svg',
  '/icon-192.png',
  '/icon-512.png',
  '/icon-maskable-512.png',
];

/*
 * The persona list is part of the usable shell, not incidental data. Without it the
 * app opens offline to an empty screen with nothing to tap — the shell technically
 * loaded and the product is unusable. Warm it on install.
 */
const WARM_DATA = ['/api/personas'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    Promise.all([
      caches
        .open(SHELL_CACHE)
        // Individually, so one missing asset cannot fail the whole install.
        .then((cache) => Promise.allSettled(SHELL_ASSETS.map((a) => cache.add(a)))),
      caches
        .open(DATA_CACHE)
        .then((cache) => Promise.allSettled(WARM_DATA.map((a) => cache.add(a)))),
    ]).then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k !== SHELL_CACHE && k !== DATA_CACHE)
            .map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

/** Stamp a cached response so the UI can never mistake it for a live one. */
function markOffline(response, storedAt) {
  const headers = new Headers(response.headers);
  headers.set('x-haqdaar-offline', '1');
  if (storedAt) headers.set('x-haqdaar-stored-at', storedAt);
  return response
    .clone()
    .blob()
    .then(
      (body) =>
        new Response(body, {
          status: response.status,
          statusText: response.statusText,
          headers,
        }),
    );
}

async function networkFirst(request) {
  const cache = await caches.open(DATA_CACHE);
  try {
    const fresh = await fetch(request);

    // A dead engine behind the dev proxy answers 5xx rather than throwing, and at a
    // Panchayat "the box is unreachable" is at least as likely as "the phone has no
    // signal". Both are the same thing to the citizen, so both fall back to the
    // stored answer — stamped, never passed off as live.
    if (fresh.status >= 500) {
      const cached = await cache.match(request);
      if (cached) {
        return markOffline(cached, cached.headers.get('x-haqdaar-stored-at'));
      }
      return fresh;
    }

    if (fresh.ok) {
      const stamped = new Headers(fresh.headers);
      stamped.set('x-haqdaar-stored-at', new Date().toISOString());
      const body = await fresh.clone().blob();
      await cache.put(
        request,
        new Response(body, {
          status: fresh.status,
          statusText: fresh.statusText,
          headers: stamped,
        }),
      );
    }
    return fresh;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return markOffline(cached, cached.headers.get('x-haqdaar-stored-at'));
    // Nothing cached and no network. Say so plainly; do not invent a verdict.
    return new Response(
      JSON.stringify({ offline: true, cards: [], detail: 'no stored answer' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } },
    );
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const fresh = await fetch(request);
  if (fresh.ok && new URL(request.url).origin === self.location.origin) {
    const cache = await caches.open(SHELL_CACHE);
    cache.put(request, fresh.clone());
  }
  return fresh;
}

/*
 * PURGE. On a shared Panchayat or CSC laptop the next citizen must not be able to
 * reload and read the previous one's schemes, documents and gaps. The page asks for
 * this when a session ends or a different person is selected; it drops every cached
 * verdict and every extracted field while leaving the app shell installed, so the
 * device stays usable offline without carrying anyone's data forward.
 */
self.addEventListener('message', (event) => {
  if (!event.data || event.data.type !== 'haqdaar:purge') return;
  event.waitUntil(
    caches
      .delete(DATA_CACHE)
      .then(() => caches.open(DATA_CACHE))
      // Re-warm only the persona list: it is not citizen data, and without it the
      // app opens offline to an empty screen.
      .then((cache) => Promise.allSettled(WARM_DATA.map((a) => cache.add(a))))
      .then(() => {
        if (event.source) event.source.postMessage({ type: 'haqdaar:purged' });
      }),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // SPA navigations fall back to the cached shell so the app opens offline.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match('/index.html').then((r) => r || caches.match('/')),
      ),
    );
    return;
  }

  event.respondWith(cacheFirst(request));
});
