// store.js — localStorage 세션 (04_frontend_spec.md 클라이언트 상태)
const KEYS = {
  token: "auth_token",
  userId: "user_id",
  petId: "pet_id",
  walk: "active_walk_session_id",
  settings: "settings",
  pendingJoin: "blip_pending_join",
  demo: "blip_demo_context",
  walkClips: "blip_walk_clips", // W4 브리지 (원래 W0 소유 — 미머지로 임시 추가, W0 머지 시 대체)
};

const DEFAULT_SETTINGS = {
  locationVisible: true,      // 위치 공유
  approximate: true,          // 대략적 위치 표시
  hideHome: false,            // 집 주변 비공개
  defaultVisibility: "diary", // 기록 기본 공개범위
};

export const store = {
  get token() { return localStorage.getItem(KEYS.token); },
  get userId() { return localStorage.getItem(KEYS.userId); },
  get petId() { return localStorage.getItem(KEYS.petId); },
  get walkId() { return localStorage.getItem(KEYS.walk); },
  get demo() {
    try { return JSON.parse(localStorage.getItem(KEYS.demo) || "null"); }
    catch { return null; }
  },

  setSession(userId, token) {
    localStorage.setItem(KEYS.userId, userId);
    localStorage.setItem(KEYS.token, token);
  },
  setPetId(id) { if (id) localStorage.setItem(KEYS.petId, id); },
  setWalkId(id) {
    if (id) localStorage.setItem(KEYS.walk, id);
    else localStorage.removeItem(KEYS.walk);
  },
  setDemo(data) {
    if (data) localStorage.setItem(KEYS.demo, JSON.stringify(data));
    else localStorage.removeItem(KEYS.demo);
  },
  clearDemo() { localStorage.removeItem(KEYS.demo); },

  get settings() {
    try { return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(KEYS.settings) || "{}") }; }
    catch { return { ...DEFAULT_SETTINGS }; }
  },
  setSettings(patch) {
    const next = { ...this.settings, ...patch };
    localStorage.setItem(KEYS.settings, JSON.stringify(next));
    return next;
  },

  get pendingJoin() { return localStorage.getItem(KEYS.pendingJoin); },
  setPendingJoin(code) { if (code) localStorage.setItem(KEYS.pendingJoin, code); },
  clearPendingJoin() { localStorage.removeItem(KEYS.pendingJoin); },

  // W4 브리지 (원래 W0 소유 — 미머지로 임시 추가). 산책 중 촬영 클립 누적/복원.
  // clip: { clip_id, mission_id|null, order }
  get walkClips() { try { return JSON.parse(localStorage.getItem(KEYS.walkClips) || "[]"); } catch { return []; } },
  addWalkClip(c) { const l = this.walkClips; l.push(c); localStorage.setItem(KEYS.walkClips, JSON.stringify(l)); },
  clearWalkClips() { localStorage.removeItem(KEYS.walkClips); },

  get isAuthed() { return !!this.token; },

  logout() {
    Object.values(KEYS).forEach((k) => localStorage.removeItem(k));
  },
};
