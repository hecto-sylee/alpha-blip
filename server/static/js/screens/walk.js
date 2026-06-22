// screens/walk.js — SCR-11 산책 지도 (F-01). 챙키 지도 레이어.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, onLeave, icon } from "../ui.js";
import { navigate } from "../router.js";
import * as poll from "../polling.js";
import { getOnce, watch, fmtDistance } from "../geo.js";
import { openPreview } from "./match.js";
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

export async function walkScreen() {
  setTab(null);

  let myPet = null;
  try { myPet = (await api.get("/auth/me")).pets?.[0] || null; } catch (_) {}

  const demo = store.demo;
  let here;
  if (demo) {
    here = { lat: demo.lat, lng: demo.lng, accuracy: 0 };
  } else {
    // 위치 권한 먼저 확보
    try {
      here = await getOnce();
    } catch (code) {
      return renderDenied(code);
    }
  }

  // 산책 세션 확보 (없으면 시작)
  let walkId = store.walkId;
  if (!walkId) {
    try {
      const petId = store.petId;
      if (!petId) { toast("반려동물을 먼저 등록해 주세요", "err"); navigate("/onboard-pet"); return; }
      const res = await api.post("/walks/start", { pet_id: petId, latitude: here.lat, longitude: here.lng });
      walkId = res.walk_session_id;
      store.setWalkId(walkId);
    } catch (e) {
      toast(e.message || "산책을 시작하지 못했어요", "err");
      navigate("/home");
      return;
    }
  }

  // --- DOM scaffold ---
  const mapEl = el("div", { id: "walk-map" });
  const countEl = el("span.count", { id: "nearby-count", text: "주변을 살펴보는 중…" });

  const top = el("div.walk-top", {}, [
    el("span.dotlive"),
    el("span.strong", { text: demo ? "데모 산책 중" : "산책 중" }),
    el("span.spacer"),
    el("span.sub", { id: "walk-coord", text: "" }),
  ]);

  const questBanner = el("div.quest-banner", { id: "quest-banner", onclick: () => navigate("/quest") }, [
    icon("target", { cls: "q-ic" }),
    el("div", {}, [
      el("div.strong", { text: "오늘의 퀘스트" }),
      el("div.sub", { id: "quest-text", text: "탭해서 오늘 찍어볼 순간을 정해요" }),
    ]),
  ]);

  const endBtn = el("button.cta", { id: "end-walk", text: "산책 종료" });
  const bottom = el("div.walk-bottom", {}, [
    el("div.stack.gap-sm", {}, [
      el("div.row", {}, [icon("paw-print"), countEl]),
      endBtn,
    ]),
  ]);

  const fallback = el("div.map-fallback.hidden", { id: "walk-fallback" }, [
    el("div.radar", {}, [el("div.me", {}, [icon("map-pin")])]),
    el("p.center.sub", { text: "지도를 불러올 수 없어 목록으로 표시해요." }),
    el("div", { id: "fallback-list", class: "stack" }),
  ]);
  const demoPeerLayer = el("div", { id: "demo-peer-layer" });

  const overlaysTop = el("div.walk-overlays-top", {}, [top, questBanner]);
  const screen = el("div.map-screen", {}, [mapEl, fallback, demoPeerLayer, overlaysTop, bottom]);
  mount(screen);
  document.getElementById("view")?.classList.add("walk-view");
  onLeave(() => document.getElementById("view")?.classList.remove("walk-view"));

  // --- map init (graceful fallback if WebGL/MapLibre unavailable) ---
  const ctx = { map: null, markers: new Map(), here, walkId, useFallback: false, demo, myPet };
  initMap(ctx, mapEl, fallback);
  addDemoPeerMarker(ctx, demoPeerLayer);
  frameDemo(ctx);

  document.getElementById("walk-coord").textContent = `${here.lat.toFixed(4)}, ${here.lng.toFixed(4)}`;

  // --- watchPosition → PATCH location ---
  if (demo) {
    try { await api.patch(`/walks/${ctx.walkId}/location`, { latitude: here.lat, longitude: here.lng }); } catch (_) {}
    updateMe(ctx);
  } else {
    const stopWatch = watch(
      async (pos) => {
        ctx.here = pos;
        try { await api.patch(`/walks/${ctx.walkId}/location`, { latitude: pos.lat, longitude: pos.lng }); } catch (_) {}
        updateMe(ctx);
        const c = document.getElementById("walk-coord");
        if (c) c.textContent = `${pos.lat.toFixed(4)}, ${pos.lng.toFixed(4)}`;
      },
      () => {}
    );
    onLeave(stopWatch);
  }

  // --- quest banner (오늘의 퀘스트 미션) ---
  loadQuestBanner();

  // --- nearby polling ---
  poll.start("nearby", () => refreshNearby(ctx), 3000);

  // --- end walk ---
  endBtn.addEventListener("click", async () => {
    endBtn.disabled = true; endBtn.textContent = "종료 중…";
    try {
      await api.post(`/walks/${ctx.walkId}/end`, {});
    } catch (_) {}
    const endedId = ctx.walkId;
    store.setWalkId(null);
    poll.stop("nearby");
    toast("산책을 마쳤어요", "ok", "paw-print");
    // SCR-20 기록 에디터로 (혼자 산책 출처 연결)
    navigate(`/record?walk=${endedId}`);
  });
}

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
      zoom: 15,
      attributionControl: true,
    });
    ctx.map.on("error", () => {}); // tile errors shouldn't break flow
    ctx.map.on("load", () => updateMe(ctx));
    // WebGL이 죽으면 load가 안 옴 → 안전망
    setTimeout(() => { if (ctx.map && !ctx.map.loaded() && !ctx.useFallback) { /* still ok */ } }, 1500);
    updateMe(ctx);
  } catch (e) {
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

async function refreshNearby(ctx) {
  const radius = 1000;
  const res = await api.get(`/nearby/dogs?latitude=${ctx.here.lat}&longitude=${ctx.here.lng}&radius_meters=${radius}`);
  const dogs = res.dogs || [];
  const countEl = document.getElementById("nearby-count");
  if (countEl) countEl.textContent = dogs.length ? `근처에 ${dogs.length}마리의 친구가 있어요` : "아직 근처에 친구가 없어요";

  const seen = new Set();
  for (const dog of dogs) {
    seen.add(dog.walk_session_id);
    if (ctx.markers.has(dog.walk_session_id)) continue;
    const chip = dogMarker(dog, () => openPreview(dog, ctx));
    if (ctx.useFallback || !ctx.map) {
      const list = document.getElementById("fallback-list");
      if (list) list.append(chip);
      ctx.markers.set(dog.walk_session_id, { chip, marker: null });
    } else {
      const marker = placeChipMarker(
        ctx, chip, dog.approximate_location.longitude, dog.approximate_location.latitude
      );
      ctx.markers.set(dog.walk_session_id, { chip, marker });
    }
  }
  // 사라진 친구 정리
  for (const [ws, m] of ctx.markers) {
    if (!seen.has(ws)) {
      if (m.demo) continue;
      m.marker?.remove();
      m.chip?.remove();
      ctx.markers.delete(ws);
    }
  }
}

// maplibre 마커로 칩을 배치한다. 칩의 marker-pop 애니메이션이 transform:none(both)으로
// 끝나며 maplibre의 위치 transform을 덮어쓰는 문제를 피하려고 래퍼 div를 끼운다.
// (maplibre는 래퍼에 transform, 애니메이션은 안쪽 칩에만 적용)
function placeChipMarker(ctx, chip, lng, lat) {
  const wrap = el("div.marker-wrap", {});
  wrap.appendChild(chip);
  return new maplibregl.Marker({ element: wrap, anchor: "bottom" })
    .setLngLat([lng, lat])
    .addTo(ctx.map);
}

function dogMarker(dog, onTap) {
  const pet = dog.pet || {};
  return el(
    "div.dog-marker" + (dog.is_demo ? ".demo-peer-marker" : ""),
    { dataset: { ws: dog.walk_session_id }, onclick: onTap },
    [
      el("div.face", {}, [petCharacterEl(pet, { size: 34 })]),
      el("div.meta", {}, [
        el("div.nm", { text: pet.name || "강아지" }),
        el("div.ds", { text: fmtDistance(dog.distance_meters) }),
      ]),
    ]
  );
}

// 데모: 내 위치(데모 원점)를 중심으로 잡아 주변 더미 친구(망고·초코·콩)가
// 한 화면에 고르게 들어오게 한다. (마커는 각자 고정 좌표 그대로, 화면만 맞춤)
function frameDemo(ctx) {
  if (!ctx.map || !ctx.demo || ctx.useFallback) return;
  const center = [ctx.here.lng, ctx.here.lat];
  const apply = () => { try { ctx.map.jumpTo({ center, zoom: 15 }); } catch (_) {} };
  if (ctx.map.loaded()) apply(); else ctx.map.on("load", apply);
}

function metersBetween(aLat, aLng, bLat, bLng) {
  const R = 6371000, rad = Math.PI / 180;
  const dLat = (bLat - aLat) * rad, dLng = (bLng - aLng) * rad;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(aLat * rad) * Math.cos(bLat * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

function addDemoPeerMarker(ctx, layer) {
  const demo = ctx.demo;
  if (!demo?.mockSessionId || ctx.markers.has(demo.mockSessionId)) return;
  const pet = demo.mockPet || { name: "테헤란로 망고", breed: "비숑", personality_tags: ["데모"] };
  const hasCoord = typeof demo.mockLat === "number" && typeof demo.mockLng === "number";
  const dog = {
    walk_session_id: demo.mockSessionId,
    pet: { ...pet, name: pet.name || "테헤란로 망고" },
    approximate_location: hasCoord
      ? { latitude: demo.mockLat, longitude: demo.mockLng }
      : null,
    distance_meters: hasCoord
      ? Math.round(metersBetween(ctx.here.lat, ctx.here.lng, demo.mockLat, demo.mockLng))
      : 80,
    is_demo: true,
  };
  const chip = dogMarker(dog, () => openPreview(dog, ctx));
  chip.setAttribute("aria-label", "데모 상대 사용자");
  // 지도가 살아 있으면 고정 좌표에 지리적 마커로 박는다(지도를 움직여도 그 지점에 고정).
  if (ctx.map && !ctx.useFallback && hasCoord) {
    // 스타일 load 이후에 추가해야 jumpTo 등 카메라 변경에 맞춰 정상 투영된다.
    const place = () => placeChipMarker(ctx, chip, demo.mockLng, demo.mockLat);
    if (ctx.map.loaded()) place(); else ctx.map.on("load", place);
    ctx.markers.set(demo.mockSessionId, { chip, marker: true, demo: true });
  } else {
    // 폴백(WebGL 불가): 떠다니는 오버레이 칩으로 표시.
    layer?.append(chip);
    ctx.markers.set(demo.mockSessionId, { chip, marker: null, demo: true });
  }
}

async function loadQuestBanner() {
  try {
    const t = await api.get("/quests/today?scope=user");
    const txt = document.getElementById("quest-text");
    if (!txt) return;
    if (t.locked && t.quest) {
      const m = (t.quest.missions || [])[0];
      txt.textContent = m ? `지금 찍어볼 순간: ${m.title}` : t.quest.title;
    } else {
      txt.textContent = "탭해서 오늘 찍어볼 순간을 정해요";
    }
  } catch (_) {}
}

function renderDenied(code) {
  setTab(null);
  const msg =
    code === "denied" ? "위치 권한이 거부됐어요. 산책 지도를 보려면 위치 접근을 허용해 주세요."
    : code === "unsupported" ? "이 브라우저는 위치를 지원하지 않아요."
    : "위치를 확인하지 못했어요. 잠시 후 다시 시도해 주세요.";
  mount(
    el("div.stack", {}, [
      el("h1.h1", { text: "산책 지도" }),
      el("div.empty", {}, [
        el("div.big", {}, [icon("map-pin")]),
        el("p", { text: msg }),
      ]),
      el("button.cta", { text: "다시 시도", onclick: () => navigate("/walk") }),
      el("button.btn.ghost", { text: "홈으로", onclick: () => navigate("/home") }),
    ])
  );
}
