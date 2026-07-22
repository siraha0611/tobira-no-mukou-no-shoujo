// 『扉のむこうの少女』Service Worker
// ねらい: 展示(iPad単体)で一度開いたら、会場にネットが無くてもアプリの殻が開けるようにする。
// 方針: ページ(ナビゲーション)はネット優先→失敗時にキャッシュ退避。
//       /start /turn /letter /survey /tts などのAPIは一切さわらない(素通し)。
const CACHE = 'door-shell-v1';
const SHELL = ['/', '/sw.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  // ページ本体だけ面倒を見る(クエリ ?mode=exhibit などが付いていても殻は '/' と同じ)
  const isShell = req.mode === 'navigate' || url.pathname === '/' || url.pathname === '/index.html';
  if (!isShell) return;
  e.respondWith((async () => {
    try {
      const res = await fetch(req);
      if (res && res.ok) {
        const c = await caches.open(CACHE);
        c.put('/', res.clone()); // 最新の殻を覚え直す
      }
      return res;
    } catch (_) {
      const hit = await caches.match('/');
      if (hit) return hit;
      throw _;
    }
  })());
});
