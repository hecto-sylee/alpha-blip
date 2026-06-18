// polling.js — 주기 조회 유틸 (실시간 대신 폴링: 요청 수신 / 방 갱신)
const timers = new Map();

// start(key, fn, interval): fn은 async. 같은 key 재등록 시 기존 것 정리.
export function start(key, fn, interval = 3000) {
  stop(key);
  let stopped = false;
  const tick = async () => {
    if (stopped) return;
    try { await fn(); } catch (_) { /* 폴링 에러는 조용히 무시 */ }
    if (!stopped) timers.set(key, setTimeout(tick, interval));
  };
  tick();
  return () => stop(key);
}

export function stop(key) {
  const t = timers.get(key);
  if (t) { clearTimeout(t); timers.delete(key); }
}

export function stopAll() {
  for (const t of timers.values()) clearTimeout(t);
  timers.clear();
}
