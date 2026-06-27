// screens/home_map.js — 홈 idle 지도 (담당: W1, 라우트 #/home)
//
// 손그림 이미지1 → idle 홈. 산책 세션 미시작 상태의 전체화면 지도.
//  - "오늘의 퀘스트" 배너 없음(퀘스트는 산책중으로 이동).
//  - 축척 확대 + 본인이 화면 중앙에 빨간 마커(탭 가능).
//  - 주변 사용자 = 강아지 캐릭터 핀만(이름/거리 메타 칩 제거).
//  - 마커 탭 → 가운데 팝업(centerModal) 프로필 + CTA.
//      · 타 강아지 → [같이 산책하기] → 본인 walk session 보장 → POST /match-requests → #/matching/:id
//      · 본인 강아지 → [산책하기] → walk session 시작 + clearWalkClips → #/walk
//
// 공용 파일은 수정하지 않는다. 화면 전용 스타일은 app.css 끝 `/* === W1: home-map === */`.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, onLeave, icon, centerModal } from "../ui.js";
import { navigate } from "../router.js";
import * as poll from "../polling.js";
import { getOnce, watch, fmtDistance } from "../geo.js";
import { petCharacterEl } from "../character.js";

// idle 홈은 산책중보다 더 가깝게(축척 확대) — 내 주변 강아지가 잘 보이도록.
const HOME_ZOOM = 16.5;
const NEARBY_RADIUS = 1000;

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

export async function homeMapScreen() {
  setTab("home"); // idle 홈은 탭바 표시

  // 내 펫(본인 마커 캐릭터 + walk 시작에 필요)
  let myPet = null;
  try { myPet = (await api.get("/auth/me")).pets?.[0] || null; } catch (_) {}

  // 위치: 핀(override) > 데모 > GPS. idle이라 walk session 불필요.
  const demo = store.demo;
  const override = store.override;
  let here;
  if (override) {
    here = { lat: override.lat, lng: override.lng, accuracy: 0 };
  } else if (demo) {
    here = { lat: demo.lat, lng: demo.lng, accuracy: 0 };
  } else {
    try {
      here = await getOnce();
    } catch (code) {
      return renderDenied(code);
    }
  }
  const fixedLoc = !!(override || demo); // 고정 위치 → GPS watch 비활성

  // --- DOM scaffold (idle: 퀘스트/종료/카운트 HUD 없음) ---
  const mapEl = el("div", { id: "walk-map" });
  const fallback = el("div.map-fallback.hidden", { id: "walk-fallback" }, [
    el("div.radar", {}, [el("div.me", {}, [icon("map-pin")])]),
    el("p.center.sub", { text: "지도를 불러올 수 없어 목록으로 표시해요." }),
    el("div", { id: "fallback-list", class: "stack" }),
  ]);
  const pinBtn = el("button.pin-btn", { id: "pin-btn", type: "button" }, ["📍 위치 옮기기"]);
  const clearBtn = override
    ? el("button.coord-clear.pin-clear", { text: "GPS", title: "핀 해제(실제 위치로)", onclick: () => { store.setOverride(null); location.reload(); } })
    : null;
  const screen = el("div.map-screen.home-map-screen", {}, [mapEl, fallback, pinBtn, clearBtn].filter(Boolean));
  mount(screen);

  const view = document.getElementById("view");
  view?.classList.add("home-map-view");
  onLeave(() => view?.classList.remove("home-map-view"));

  // --- map init (graceful fallback if WebGL/MapLibre unavailable) ---
  const ctx = { map: null, markers: new Map(), here, demo, myPet, useFallback: false };
  initMap(ctx, mapEl, fallback);

  // 데모: 목업 강아지 마커를 직접 그린다(idle에선 내 위치 broadcast 안 함 → nearby 누락 대비).
  addDemoPeerMarker(ctx);

  // --- 핀 찍기(실제 위치 대신 수동 지정) ---
  let pinMode = false;
  const setPin = (lng, lat) => {
    ctx.here = { lat, lng, accuracy: 0 };
    store.setOverride({ lat, lng });
    updateMe(ctx); recenter(ctx);
    Promise.resolve(refreshNearby(ctx)).catch(() => {});
    toast("이 위치로 옮겼어요 📍", "ok");
  };
  pinBtn.addEventListener("click", () => {
    if (!ctx.map) {
      const v = prompt("위치 (위도, 경도)", `${ctx.here.lat.toFixed(5)}, ${ctx.here.lng.toFixed(5)}`);
      if (v) { const [la, ln] = v.split(",").map((s) => parseFloat(s.trim())); if (isFinite(la) && isFinite(ln)) setPin(ln, la); }
      return;
    }
    pinMode = !pinMode;
    pinBtn.classList.toggle("on", pinMode);
    pinBtn.textContent = pinMode ? "지도를 탭하세요" : "📍 위치 옮기기";
    mapEl.style.cursor = pinMode ? "crosshair" : "";
  });
  if (ctx.map) ctx.map.on("click", (e) => {
    if (!pinMode) return;
    pinMode = false; pinBtn.classList.remove("on"); pinBtn.textContent = "📍 위치 옮기기"; mapEl.style.cursor = "";
    setPin(e.lngLat.lng, e.lngLat.lat);
  });

  // --- 위치 추적: 고정(핀/데모)이면 watch 안 함, 아니면 watch → recenter ---
  if (!fixedLoc) {
    const stopWatch = watch(
      (pos) => {
        ctx.here = pos;
        updateMe(ctx);
        recenter(ctx);
      },
      () => {}
    );
    onLeave(stopWatch);
  }

  // --- nearby 폴링(강아지 캐릭터 핀만) ---
  poll.start("home-nearby", () => refreshNearby(ctx), 3000);
  onLeave(() => poll.stop("home-nearby"));
}

// ---------------- map ----------------
function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl") || c.getContext("experimental-webgl")));
  } catch (_) { return false; }
}

function initMap(ctx, mapEl, fallback) {
  if (typeof window.maplibregl === "undefined" || !webglAvailable()) {
    enableFallback(ctx, fallback);
    return;
  }
  try {
    ctx.map = new maplibregl.Map({
      container: mapEl,
      style: OSM_STYLE,
      center: [ctx.here.lng, ctx.here.lat],
      zoom: HOME_ZOOM,
      attributionControl: true,
    });
    ctx.map.on("error", () => {}); // 타일 에러는 흐름을 깨지 않음
    ctx.map.on("load", () => { updateMe(ctx); recenter(ctx); });
    updateMe(ctx);
  } catch (_) {
    enableFallback(ctx, fallback);
  }
}

function enableFallback(ctx, fallback) {
  ctx.useFallback = true;
  fallback.classList.remove("hidden");
}

// 본인 마커: 빨간 도트(+ 내 강아지 캐릭터). 화면 중앙(내 좌표)에 유지. 탭 → 본인 팝업.
function updateMe(ctx) {
  if (!ctx.map) return;
  if (!ctx._me) {
    const meEl = el(
      "div.me-marker.red" + (ctx.myPet ? ".has-char" : ""),
      { id: "me-marker", role: "button", "aria-label": "내 강아지", title: "내 강아지" }
    );
    if (ctx.myPet) meEl.append(petCharacterEl(ctx.myPet, { size: 40 }));
    meEl.addEventListener("click", () => openMineModal(ctx));
    ctx._me = new maplibregl.Marker({ element: meEl });
  }
  ctx._me.setLngLat([ctx.here.lng, ctx.here.lat]).addTo(ctx.map);
}

function recenter(ctx) {
  if (!ctx.map) return;
  const go = () => { try { ctx.map.easeTo({ center: [ctx.here.lng, ctx.here.lat], zoom: HOME_ZOOM, duration: 300 }); } catch (_) {} };
  if (ctx.map.loaded()) go(); else ctx.map.on("load", go);
}

// ---------------- nearby (강아지 캐릭터 핀만) ----------------
async function refreshNearby(ctx) {
  const res = await api.get(`/nearby/dogs?latitude=${ctx.here.lat}&longitude=${ctx.here.lng}&radius_meters=${NEARBY_RADIUS}`);
  const dogs = res.dogs || [];
  const myWs = store.walkId;

  const seen = new Set();
  for (const dog of dogs) {
    if (myWs && dog.walk_session_id === myWs) continue; // 혹시 본인 세션이 섞이면 제외
    seen.add(dog.walk_session_id);
    if (ctx.markers.has(dog.walk_session_id)) continue;
    placeDog(ctx, dog, false);
  }

  // 사라진 친구 정리(데모 마커는 유지)
  for (const [ws, m] of ctx.markers) {
    if (m.demo || seen.has(ws)) continue;
    m.marker?.remove();
    m.pin?.remove();
    ctx.markers.delete(ws);
  }
}

// 데모 목업 강아지(고정 좌표) — 기존 demo 컨텍스트 재사용.
function addDemoPeerMarker(ctx) {
  const demo = ctx.demo;
  if (!demo?.mockSessionId || ctx.markers.has(demo.mockSessionId)) return;
  const hasCoord = typeof demo.mockLat === "number" && typeof demo.mockLng === "number";
  const pet = demo.mockPet || { name: "테헤란로 망고", breed: "비숑", personality_tags: ["데모"] };
  const dog = {
    walk_session_id: demo.mockSessionId,
    pet: { ...pet, name: pet.name || "테헤란로 망고" },
    approximate_location: hasCoord ? { latitude: demo.mockLat, longitude: demo.mockLng } : null,
    distance_meters: hasCoord
      ? Math.round(metersBetween(ctx.here.lat, ctx.here.lng, demo.mockLat, demo.mockLng))
      : 80,
    is_demo: true,
  };
  placeDog(ctx, dog, true);
}

// 강아지 캐릭터 핀 1개를 지도(또는 fallback 리스트)에 배치한다.
function placeDog(ctx, dog, isDemo) {
  const hasCoord = dog.approximate_location
    && typeof dog.approximate_location.longitude === "number"
    && typeof dog.approximate_location.latitude === "number";
  const pin = dogPin(dog, () => openPeerModal(ctx, dog));

  if (ctx.map && !ctx.useFallback && hasCoord) {
    const place = () => {
      const marker = placePinMarker(ctx, pin, dog.approximate_location.longitude, dog.approximate_location.latitude);
      ctx.markers.set(dog.walk_session_id, { pin, marker, demo: isDemo });
    };
    if (ctx.map.loaded()) place(); else ctx.map.on("load", place);
    if (!ctx.markers.has(dog.walk_session_id)) ctx.markers.set(dog.walk_session_id, { pin, marker: null, demo: isDemo });
  } else {
    const list = document.getElementById("fallback-list");
    if (list) list.append(pin);
    ctx.markers.set(dog.walk_session_id, { pin, marker: null, demo: isDemo });
  }
}

// 강아지 캐릭터 핀 — 이름/거리 메타 칩 없이 캐릭터만(요구 #2).
function dogPin(dog, onTap) {
  const pet = dog.pet || {};
  return el(
    "div.dog-pin" + (dog.is_demo ? ".demo" : ""),
    {
      dataset: { ws: dog.walk_session_id },
      role: "button",
      "aria-label": `${pet.name || "강아지"} 프로필 보기`,
      onclick: onTap,
    },
    [el("div.dog-pin-face", {}, [petCharacterEl(pet, { size: 40 })])]
  );
}

// marker-pop 애니메이션이 transform:none으로 끝나며 maplibre 위치 transform을
// 덮어쓰지 않도록 래퍼 div를 끼운다(maplibre는 래퍼, 애니메이션은 안쪽 핀).
function placePinMarker(ctx, pin, lng, lat) {
  const wrap = el("div.marker-wrap", {});
  wrap.appendChild(pin);
  return new maplibregl.Marker({ element: wrap, anchor: "bottom" })
    .setLngLat([lng, lat])
    .addTo(ctx.map);
}

// ---------------- center modals ----------------
// 타 강아지: [같이 산책하기] → 본인 walk session 보장 → POST /match-requests → #/matching/:id
function openPeerModal(ctx, dog) {
  const pet = dog.pet || {};
  centerModal((close) => {
    const cta = el("button.cta", { id: "peer-walk-together", type: "button", text: "같이 산책하기" });
    cta.addEventListener("click", async () => {
      cta.disabled = true; cta.textContent = "요청 보내는 중…";
      try {
        await ensureMyWalkSession(ctx); // O1: idle에선 요청 전 본인 세션 보장
        const res = await api.post("/match-requests", { receiver_walk_session_id: dog.walk_session_id });
        close();
        navigate(`/matching/${res.match_request_id}`);
      } catch (e) {
        toast(e.message || "요청을 보내지 못했어요", "err");
        cta.disabled = false; cta.textContent = "같이 산책하기";
      }
    });
    return profileCard(pet, {
      subtitle: `${pet.breed || "견종 미상"} · ${fmtDistance(dog.distance_meters) || "근처"} 근처`,
      cta,
    });
  });
}

// 본인 강아지: [산책하기] → walk session 시작 + clearWalkClips → #/walk
function openMineModal(ctx) {
  const pet = ctx.myPet;
  centerModal((close) => {
    const cta = el("button.cta", { id: "mine-start-walk", type: "button", text: "산책하기" });
    cta.addEventListener("click", async () => {
      cta.disabled = true; cta.textContent = "산책 준비 중…";
      try {
        await ensureMyWalkSession(ctx);
        store.clearWalkClips(); // 새 산책 시작 → 누적 클립 초기화
        close();
        navigate("/walk");
      } catch (e) {
        toast(e.message || "산책을 시작하지 못했어요", "err");
        cta.disabled = false; cta.textContent = "산책하기";
      }
    });
    return profileCard(pet || { name: "내 강아지" }, {
      subtitle: pet?.breed || "오늘도 가볍게 한 바퀴",
      mine: true,
      cta,
    });
  });
}

// 공통 프로필 카드(듀오링고 입체 카드 — 인라인 스타일 금지, app.css 클래스 사용).
function profileCard(pet, { subtitle, cta, mine = false }) {
  const tags = (pet.personality_tags || []).slice(0, 6).map((t) => el("span.chip", { text: t }));
  return el("div.stack.center.cm-profile" + (mine ? ".mine" : ""), { id: "cm-profile" }, [
    el("div.cm-char", {}, [petCharacterEl(pet, { size: 96 })]),
    el("div.title.center", { text: pet.name || "강아지" }),
    el("div.sub.center", { text: subtitle }),
    (pet.size || tags.length) && el("div.row.wrap.gap-sm.center.cm-tags", {}, [
      pet.size && el("span.chip.on", { text: sizeLabel(pet.size) }),
      ...tags,
    ]),
    pet.caution_notes && el("p.sub.center.cm-caution", {}, [icon("triangle-alert"), ` ${pet.caution_notes}`]),
    cta,
  ]);
}

function sizeLabel(s) { return { small: "소형", medium: "중형", large: "대형" }[s] || s; }

// ---------------- walk session 보장 ----------------
async function ensureMyWalkSession(ctx) {
  let walkId = store.walkId;
  if (walkId) return walkId;
  const petId = store.petId || ctx.myPet?.id;
  if (!petId) {
    toast("반려동물을 먼저 등록해 주세요", "err");
    navigate("/onboard-pet");
    throw new Error("no pet");
  }
  const res = await api.post("/walks/start", {
    pet_id: petId,
    latitude: ctx.here.lat,
    longitude: ctx.here.lng,
  });
  walkId = res.walk_session_id;
  store.setWalkId(walkId);
  return walkId;
}

// ---------------- helpers ----------------
function metersBetween(aLat, aLng, bLat, bLng) {
  const R = 6371000, rad = Math.PI / 180;
  const dLat = (bLat - aLat) * rad, dLng = (bLng - aLng) * rad;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(aLat * rad) * Math.cos(bLat * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

function renderDenied(code) {
  setTab("home");
  const msg =
    code === "denied" ? "위치 권한이 거부됐어요. 지도를 보려면 위치 접근을 허용해 주세요."
    : code === "unsupported" ? "이 브라우저는 위치를 지원하지 않아요."
    : "위치를 확인하지 못했어요. 잠시 후 다시 시도해 주세요.";
  mount(
    el("div.stack", {}, [
      el("h1.h1", { text: "홈 지도" }),
      el("div.empty", {}, [
        el("div.big", {}, [icon("map-pin")]),
        el("p", { text: msg }),
      ]),
      el("button.cta", { text: "다시 시도", onclick: () => navigate("/home") }),
    ])
  );
}
