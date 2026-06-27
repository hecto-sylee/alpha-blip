// screens/walking.js — 산책 중 HUD (담당: W2, 라우트 #/walk)
// 활성 산책(혼자/매칭 공통): 지도 + 상단 투명 퀘스트박스(미션 ≤2, 지도 가림 없음)
//   + 좌하단 일반촬영(→#/camera) + 우하단 통화종료(phone-off → 종료/기록).
// 진입: 오늘 퀘스트 자동확보(없으면 후보 1개 자동 select). 카메라 복귀 시 store.walkClips로 완료 갱신.
// 매칭 진입은 #/walk?match=<id>, 혼자는 #/walk. 종료 분기만 다름.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, onLeave, icon } from "../ui.js";
import { navigate } from "../router.js";
import { getOnce } from "../geo.js";
import { petCharacterEl } from "../character.js";

const OSM_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

// 산책중 화면 전용 로컬 영속 키 (store.js/공용 키는 건드리지 않는다 — 새로고침/카메라 복귀 내성용).
const MATCH_KEY = "blip_walk_match";    // 매칭 산책의 match_session_id
const START_KEY = "blip_walk_started";  // 산책 시작 시각(ms) — 종료 시 duration 계산
const readMatch = () => localStorage.getItem(MATCH_KEY) || null;
const writeMatch = (id) => { if (id) localStorage.setItem(MATCH_KEY, id); };
const clearMatch = () => localStorage.removeItem(MATCH_KEY);

function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export async function walkingScreen(_params, query = {}) {
  setTab(null); // 몰입 모드

  // --- 진입 출처: 매칭(?match=) vs 혼자. 카메라 복귀(#/walk)에도 유지되도록 영속화. ---
  const matchId = query.match || readMatch();
  if (query.match) writeMatch(query.match);

  let myPet = null;
  try { myPet = (await api.get("/auth/me")).pets?.[0] || null; } catch (_) {}

  // --- 위치 확보 (데모면 고정 좌표, 아니면 GPS) ---
  const demo = store.demo;
  let here;
  if (demo) {
    here = { lat: demo.lat, lng: demo.lng, accuracy: 0 };
  } else {
    try { here = await getOnce(); }
    catch (code) { return renderDenied(code); }
  }

  // --- 산책 세션 확보: 혼자면 없으면 start. 매칭은 match_session이 주체이므로 기존 walkId만 활용. ---
  let walkId = store.walkId;
  if (!matchId && !walkId) {
    const petId = store.petId;
    if (!petId) { toast("반려동물을 먼저 등록해 주세요", "err"); navigate("/onboard-pet"); return; }
    try {
      const res = await api.post("/walks/start", { pet_id: petId, latitude: here.lat, longitude: here.lng });
      walkId = res.walk_session_id;
      store.setWalkId(walkId);
    } catch (e) {
      toast(e.message || "산책을 시작하지 못했어요", "err");
      navigate("/home");
      return;
    }
  }
  if (!localStorage.getItem(START_KEY)) localStorage.setItem(START_KEY, String(Date.now()));

  // --- 오늘 퀘스트 자동 확보 (picker 폐기): today → 없으면 candidates 1개 자동 select ---
  const { dailyQuestId, missions } = await ensureQuest();

  // --- DOM scaffold ---
  const mapEl = el("div", { id: "walk-map" });
  const fallback = el("div.map-fallback.hidden", { id: "walk-fallback" }, [
    el("div.radar", {}, [el("div.me", {}, [icon("map-pin")])]),
    el("p.center.sub", { text: "지도를 불러올 수 없어 현재 위치만 표시해요." }),
  ]);

  const live = el("div.walk-live", {}, [
    el("span.dotlive"),
    el("span", { text: matchId ? "동행 산책 중" : (demo ? "데모 산책 중" : "산책 중") }),
  ]);
  const questsEl = el("div.walk-quests", { id: "walk-quests" });
  const overlaysTop = el("div.walk-overlays-top", {}, [live, questsEl]);

  const shootBtn = el("button.walk-fab.left", {
    id: "walk-shoot", type: "button", "aria-label": "일반 촬영",
    onclick: () => navigate("/camera"),
  }, [icon("camera")]);
  const endBtn = el("button.walk-fab.right", {
    id: "walk-end", type: "button", "aria-label": "통화 종료",
  }, [icon("phone-off")]);

  const demoPeerLayer = el("div", { id: "demo-peer-layer" });
  const screen = el("div.map-screen", {}, [mapEl, fallback, demoPeerLayer, overlaysTop, shootBtn, endBtn]);
  mount(screen);
  document.getElementById("view")?.classList.add("walk-view");
  onLeave(() => document.getElementById("view")?.classList.remove("walk-view"));

  // --- 퀘스트 박스 렌더 + 완료 상태 (store.walkClips 의 mission_id 존재 여부) ---
  renderQuests(questsEl, missions, dailyQuestId);

  // --- 지도 초기화 (WebGL/MapLibre 불가 시 graceful fallback) ---
  const ctx = { map: null, here, useFallback: false, demo, myPet };
  initMap(ctx, mapEl, fallback);
  addDemoPeerMarker(ctx, demoPeerLayer);
  frameDemo(ctx);

  // 혼자 산책: 현재 위치 1회 PATCH (데모/단발). 매칭은 매칭화면(W3) 책임이라 생략.
  if (walkId && demo) {
    try { await api.patch(`/walks/${walkId}/location`, { latitude: here.lat, longitude: here.lng }); } catch (_) {}
  }

  // --- 우하단 통화종료 → 종료 상태 → 누적 클립으로 기록 생성 → #/diary ---
  endBtn.addEventListener("click", async () => {
    if (endBtn.disabled) return;
    endBtn.disabled = true; shootBtn.disabled = true;
    try {
      const startMs = Number(localStorage.getItem(START_KEY)) || Date.now();
      const mins = Math.max(0, Math.round((Date.now() - startMs) / 60000));

      // 매칭이면 match-session end, 혼자면 walk end
      if (matchId) await api.post(`/match-sessions/${matchId}/end`, { duration_minutes: mins });
      else if (walkId) await api.post(`/walks/${walkId}/end`, {});

      // 누적 클립 1개의 Record로 번들 (visibility 항상 diary — 방 공유 제거)
      const clip_ids = store.walkClips.map((c) => c.clip_id).filter(Boolean);
      const payload = { visibility: "diary", walked_at: todayStr(), clip_ids, daily_quest_id: dailyQuestId };
      if (matchId) payload.match_session_id = matchId; else payload.walk_session_id = walkId;
      const rec = await api.post("/records", payload);
      if (rec?.points_awarded) toast(`🦴 +${rec.points_awarded} 포인트! (보유 ${rec.points})`, "ok");

      store.clearWalkClips();
      store.setWalkId(null);
      clearMatch();
      localStorage.removeItem(START_KEY);
      toast("산책을 기록했어요", "ok", "paw-print");
      navigate("/diary?saved=1");
    } catch (e) {
      endBtn.disabled = false; shootBtn.disabled = false;
      toast(e.message || "기록 저장에 실패했어요", "err");
    }
  });
}

// --- 퀘스트 확보 ---------------------------------------------------------------
async function ensureQuest() {
  try {
    const today = await api.get("/quests/today?scope=user");
    if (today && today.quest && today.daily_quest_id) {
      return { dailyQuestId: today.daily_quest_id, missions: today.quest.missions || [] };
    }
    // 미선택 → 후보 1개 자동 select
    const cand = await api.get("/quests/candidates?scope=user");
    const first = (cand.candidates || [])[0];
    if (!first) return { dailyQuestId: null, missions: [] };
    if (cand.locked) {
      // 이미 잠겨있는데 today 가 못 잡은 경우 → 후보의 미션만 노출
      return { dailyQuestId: null, missions: first.missions || [] };
    }
    const sel = await api.post("/quests/select", {
      scope: "user", scope_id: store.userId,
      quest_template_id: first.quest_template_id, quest_date: todayStr(),
    });
    return { dailyQuestId: sel.daily_quest_id, missions: first.missions || [] };
  } catch (_) {
    return { dailyQuestId: null, missions: [] };
  }
}

// --- 퀘스트 박스 (상단 투명 오버레이) ------------------------------------------
function questDoneSet() {
  return new Set(store.walkClips.map((c) => c.mission_id).filter(Boolean));
}

function renderQuests(container, missions, _dailyQuestId) {
  container.innerHTML = "";
  const done = questDoneSet();
  const list = (missions || []).slice(0, 2); // 미션 최대 2개만
  for (const m of list) {
    const isDone = done.has(m.id);
    const box = el("button.walk-quest" + (isDone ? ".done" : ""), {
      type: "button",
      dataset: { mission: m.id, quest: m.title, done: isDone ? "1" : "0" },
      onclick: () => navigate(`/camera?mission=${encodeURIComponent(m.id)}&quest=${encodeURIComponent(m.title)}`),
    }, [
      el("span.wq-ic", {}, [icon(isDone ? "check" : "camera")]),
      el("span.wq-title", { text: m.title }),
    ]);
    container.append(box);
  }
}

// --- 지도 (walk.js 레이어 재사용) ----------------------------------------------
function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl") || c.getContext("experimental-webgl")));
  } catch (_) { return false; }
}

function initMap(ctx, mapEl, fallback) {
  if (typeof window.maplibregl === "undefined" || !webglAvailable()) { enableFallback(ctx, fallback); return; }
  try {
    ctx.map = new maplibregl.Map({
      container: mapEl,
      style: OSM_STYLE,
      center: [ctx.here.lng, ctx.here.lat],
      zoom: 16,
      attributionControl: true,
    });
    ctx.map.on("error", () => {}); // 타일 오류는 흐름을 막지 않음
    ctx.map.on("load", () => updateMe(ctx));
    updateMe(ctx);
  } catch (_) {
    enableFallback(ctx, fallback);
  }
}

function enableFallback(ctx, fallback) {
  ctx.useFallback = true;
  fallback.classList.remove("hidden");
}

function updateMe(ctx) {
  if (!ctx.map) return;
  if (!ctx._me) {
    const meEl = el("div.me-marker" + (ctx.myPet ? ".has-char" : ""), { id: "me-marker" });
    if (ctx.myPet) meEl.append(petCharacterEl(ctx.myPet, { size: 40 }));
    ctx._me = new maplibregl.Marker({ element: meEl });
  }
  ctx._me.setLngLat([ctx.here.lng, ctx.here.lat]).addTo(ctx.map);
}

function metersBetween(aLat, aLng, bLat, bLng) {
  const R = 6371000, rad = Math.PI / 180;
  const dLat = (bLat - aLat) * rad, dLng = (bLng - aLng) * rad;
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(aLat * rad) * Math.cos(bLat * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

// 데모/매칭 동행 상대 마커 (지도가 살아있으면 지리적 고정, 아니면 오버레이 칩)
function addDemoPeerMarker(ctx, layer) {
  const demo = ctx.demo;
  if (!demo?.mockSessionId) return;
  const pet = demo.mockPet || { name: "테헤란로 망고", breed: "비숑", personality_tags: ["데모"] };
  const hasCoord = typeof demo.mockLat === "number" && typeof demo.mockLng === "number";
  const dist = hasCoord ? Math.round(metersBetween(ctx.here.lat, ctx.here.lng, demo.mockLat, demo.mockLng)) : 80;
  const chip = el("div.dog-marker.demo-peer-marker", { dataset: { ws: demo.mockSessionId } }, [
    el("div.face", {}, [petCharacterEl(pet, { size: 34 })]),
    el("div.meta", {}, [
      el("div.nm", { text: pet.name || "친구" }),
      el("div.ds", { text: `${dist}m` }),
    ]),
  ]);
  chip.setAttribute("aria-label", "동행 상대");
  if (ctx.map && !ctx.useFallback && hasCoord) {
    const place = () => new maplibregl.Marker({ element: chip, anchor: "bottom" })
      .setLngLat([demo.mockLng, demo.mockLat]).addTo(ctx.map);
    if (ctx.map.loaded()) place(); else ctx.map.on("load", place);
  } else {
    layer?.append(chip);
  }
}

function frameDemo(ctx) {
  if (!ctx.map || !ctx.demo || ctx.useFallback) return;
  const center = [ctx.here.lng, ctx.here.lat];
  const apply = () => { try { ctx.map.jumpTo({ center, zoom: 16 }); } catch (_) {} };
  if (ctx.map.loaded()) apply(); else ctx.map.on("load", apply);
}

function renderDenied(code) {
  setTab(null);
  const msg =
    code === "denied" ? "위치 권한이 거부됐어요. 산책 지도를 보려면 위치 접근을 허용해 주세요."
    : code === "unsupported" ? "이 브라우저는 위치를 지원하지 않아요."
    : "위치를 확인하지 못했어요. 잠시 후 다시 시도해 주세요.";
  mount(
    el("div.stack", {}, [
      el("h1.h1", { text: "산책 중" }),
      el("div.empty", {}, [el("div.big", {}, [icon("map-pin")]), el("p", { text: msg })]),
      el("button.cta", { text: "다시 시도", onclick: () => navigate("/walk") }),
      el("button.btn.ghost", { text: "홈으로", onclick: () => navigate("/home") }),
    ])
  );
}
