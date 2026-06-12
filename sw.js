// 律连全球 PWA Service Worker
// 策略：HTML 页面"网络优先"（在线总是最新，离线回退缓存）；其它静态资源"缓存优先"（快）。
const CACHE = 'igloballaw-v2';
const ASSETS = [
  'index.html','international.html','domestic.html','psychology.html','daily-report.html','manifest.json'
];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).catch(()=>{}));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if(req.method !== 'GET') return;
  const isHTML = req.mode === 'navigate' || (req.headers.get('accept')||'').includes('text/html');
  if(isHTML){
    // 网络优先：在线拿最新页面并更新缓存；断网时回退缓存
    e.respondWith(
      fetch(req).then(resp => {
        const copy = resp.clone();
        caches.open(CACHE).then(c => c.put(req, copy)).catch(()=>{});
        return resp;
      }).catch(()=> caches.match(req).then(r => r || caches.match('index.html')))
    );
  } else {
    // 其它资源：缓存优先（速度快），无缓存再走网络
    e.respondWith(
      caches.match(req).then(cached => cached || fetch(req).then(resp => {
        const copy = resp.clone();
        caches.open(CACHE).then(c => c.put(req, copy)).catch(()=>{});
        return resp;
      }).catch(()=>cached))
    );
  }
});
