// screens/matching.js — 산책 매칭 만남 게이트 (담당: W3, 라우트 #/matching/:id)
//
// 요청자·수락자 모두 이 화면으로 온다(통합). 흐름:
//   GET /match-requests/:id 폴링 → accepted+session 이면 만남 단계로.
//   수락 시점부터 양쪽의 '실제 위치'를 서로에게 표시:
//     · 내 위치 = GPS watch(실시간) → 내 walk 세션에 broadcast(PATCH /walks/{id}/location)
//     · 상대 위치 = GET /match-sessions/:id 의 partner_lat/lng 폴링
//   (임의/핀 위치·시뮬레이션 이동 없음)
//   [만났습니다] → 내 met 표시. 요청자·수락자 둘 다 누르면(both_met) → /walk?match=sid (퀘스트 페이지).
//   [산책 종료] → 세션 종료 → 홈.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, onLeave, icon, celebrate } from "../ui.js";
import { navigate } from "../router.js";
import * as poll from "../polling.js";
import { getOnce, watch } from "../geo.js";
import { petCharacterEl } from "../character.js";

const OSM_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
        "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
        "https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
      ],
      tileSize: 256,
      attribution: "© OpenStreetMap © CARTO",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

const STATUS_POLL_MS = 2000;
const LOC_POLL_MS = 2000;
const FOOT_MAX = 24;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

export async function matchingScreen(params) {
  setTab(null);
  const reqId = params.id; // = match_request_id

  let myPet = null;
  try { myPet = (await api.get("/auth/me")).pets?.[0] || null; } catch (_) {}

  // 시작 좌표 = 실제 GPS(핀/데모 무시). 헤드리스/거부 시에만 폴백.
  const start = await resolveStart();

  const statusText = el("span.strong", { id: "w3-status", text: "상대의 수락을 기다리는 중…" });
  const hintText = el("span", { id: "w3-hint-text", text: "요청을 보냈어요. 상대가 수락하면 함께 걸어요." });
  const cta = el("button.cta", { id: "w3-cta", text: "수락 대기 중…", disabled: true });
  const endBtn = el("button.btn.danger", { id: "w3-end", text: "산책 종료", disabled: true });

  const mapEl = el("div.w3-map", { id: "w3-map" });
  const fallback = el("div.w3-fallback.hidden", { id: "w3-fallback" });
  const top = el("div.w3-top", {}, [el("span.dotlive"), statusText]);
  const bottom = el("div.w3-bottom", {}, [
    el("div.w3-hint", {}, [icon("footprints"), hintText]),
    cta,
    endBtn,
  ]);
  const screen = el("div.map-screen", {}, [mapEl, fallback, top, bottom]);
  mount(screen);

  document.getElementById("view")?.classList.add("walk-view");
  onLeave(() => document.getElementById("view")?.classList.remove("walk-view"));

  const ctx = {
    map: null, fallback, useFallback: false,
    reqId, sessionId: null, proceeding: false,
    myPet, partnerPet: null,
    me: { ...start.me },
    partner: null,
    meEntity: null, partnerEntity: null,
    footprints: [], fbBounds: null,
    stopMine: null,
  };

  initMap(ctx, mapEl);
  placeMe(ctx);

  const stopAll = () => {
    poll.stop("w3-match-status"); poll.stop("w3-loc"); poll.stop("w3-met");
    if (ctx.stopMine) { ctx.stopMine(); ctx.stopMine = null; }
  };

  // --- 요청 상태 폴링 ---
  poll.start("w3-match-status", async () => {
    let r;
    try { r = await api.get(`/match-requests/${reqId}`); } catch { return; }
    if (r.status === "accepted" && r.match_session_id) {
      poll.stop("w3-match-status");
      await onAccepted(ctx, r.match_session_id);
    } else if (["rejected", "expired", "cancelled"].includes(r.status)) {
      poll.stop("w3-match-status");
      const msg = r.status === "rejected" ? "상대가 요청을 거절했어요"
        : r.status === "expired" ? "요청이 만료됐어요" : "요청이 취소됐어요";
      toast(msg);
      navigate("/home");
    }
  }, STATUS_POLL_MS);

  // --- 만남 게이트: [만났습니다] → 양쪽 met이면 퀘스트 페이지 ---
  function proceedToQuest() {
    if (ctx.proceeding) return;
    ctx.proceeding = true;
    stopAll();
    store.clearWalkClips();
    try { celebrate(ctx.myPet); } catch (_) {}
    setTimeout(() => navigate(`/walk?match=${ctx.sessionId}`), 500);
  }

  cta.addEventListener("click", async () => {
    if (!ctx.sessionId || ctx.proceeding) return;
    cta.disabled = true; cta.textContent = "확인 중…";
    try {
      const s = await api.post(`/match-sessions/${ctx.sessionId}/met`, {});
      if (s.both_met) { proceedToQuest(); return; }
      cta.textContent = "상대를 기다려요…";
      const st = document.getElementById("w3-status");
      if (st) st.textContent = "만났어요! 상대가 누르면 시작해요";
      poll.start("w3-met", async () => {
        try {
          const r = await api.get(`/match-sessions/${ctx.sessionId}`);
          if (r.both_met) { poll.stop("w3-met"); proceedToQuest(); }
        } catch (_) {}
      }, STATUS_POLL_MS);
    } catch (e) {
      toast(e.message || "실패했어요", "err");
      cta.disabled = false; cta.textContent = "만났습니다";
    }
  });

  endBtn.addEventListener("click", async () => {
    if (ctx.proceeding) return;
    endBtn.disabled = true;
    try { if (ctx.sessionId) await api.post(`/match-sessions/${ctx.sessionId}/end`, {}); } catch (_) {}
    stopAll();
    store.setWalkId(null);
    toast("산책을 종료했어요");
    navigate("/home");
  });

  onLeave(stopAll);
}

// 시작 좌표 = 실제 GPS. (핀/데모 무시 — 매칭 후엔 서로 실제 위치를 본다)
async function resolveStart() {
  try {
    const pos = await getOnce();
    return { me: { lat: pos.lat, lng: pos.lng } };
  } catch (_) {
    return { me: { lat: 37.5009, lng: 127.0398 } }; // 헤드리스/권한거부 폴백(화면만)
  }
}

function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl") || c.getContext("experimental-webgl")));
  } catch (_) { return false; }
}

function initMap(ctx, mapEl) {
  if (typeof window.maplibregl === "undefined" || !webglAvailable()) {
    ctx.useFallback = true;
    ctx.fallback.classList.remove("hidden");
    return;
  }
  try {
    ctx.map = new maplibregl.Map({
      container: mapEl, style: OSM_STYLE,
      center: [ctx.me.lng, ctx.me.lat], zoom: 16, attributionControl: true,
    });
    ctx.map.on("error", () => {});
    ctx.map.on("load", () => { placeMe(ctx); if (ctx.partner) placePartner(ctx); });
  } catch (_) {
    ctx.useFallback = true;
    ctx.fallback.classList.remove("hidden");
  }
}

// 세션 확보: 상대 프로필+실위치 로드 → 실시간 위치 동기화 시작 + CTA 활성.
async function onAccepted(ctx, sessionId) {
  if (ctx.sessionId) return;
  ctx.sessionId = sessionId;

  let partnerNick = "친구", s = null;
  try {
    s = await api.get(`/match-sessions/${sessionId}`);
    partnerNick = s.partner?.nickname || "친구";
    ctx.partnerPet = s.partner?.pet || null;
  } catch (_) {}
  if (!ctx.partnerPet) ctx.partnerPet = { name: partnerNick };

  if (s && typeof s.partner_lat === "number" && typeof s.partner_lng === "number") {
    ctx.partner = { lat: s.partner_lat, lng: s.partner_lng };
    setBounds(ctx);
    placeMe(ctx); placePartner(ctx); fitBoth(ctx);
  }

  const st = document.getElementById("w3-status");
  if (st) st.textContent = `${partnerNick}님과 만나는 중…`;
  const ht = document.getElementById("w3-hint-text");
  if (ht) ht.textContent = "실제로 만나면 [만났습니다]를 눌러요. 둘 다 누르면 퀘스트가 열려요.";
  const cta = document.getElementById("w3-cta");
  if (cta) { cta.disabled = false; cta.textContent = "만났습니다"; }
  const eb = document.getElementById("w3-end");
  if (eb) eb.disabled = false;

  // 내 실시간 위치: GPS watch → 내 마커 갱신 + walk 세션에 broadcast(상대가 폴링으로 봄)
  ctx.stopMine = watch((pos) => {
    ctx.me = { lat: pos.lat, lng: pos.lng };
    dropFoot(ctx, ctx.me.lat, ctx.me.lng, "me");
    moveEntity(ctx.meEntity, ctx.me);
    broadcastMe(store.walkId, ctx.me.lat, ctx.me.lng);
  }, () => {});

  // 상대 실시간 위치: 세션 폴링 → 상대 마커 갱신
  poll.start("w3-loc", async () => {
    try {
      const r = await api.get(`/match-sessions/${ctx.sessionId}`);
      if (typeof r.partner_lat === "number" && typeof r.partner_lng === "number") {
        ctx.partner = { lat: r.partner_lat, lng: r.partner_lng };
        if (!ctx.partnerEntity) { setBounds(ctx); placePartner(ctx); fitBoth(ctx); }
        else { dropFoot(ctx, ctx.partner.lat, ctx.partner.lng, "partner"); moveEntity(ctx.partnerEntity, ctx.partner); }
      }
    } catch (_) {}
  }, LOC_POLL_MS);
}

let _lastMatchBcast = 0;
async function broadcastMe(walkId, lat, lng) {
  if (!walkId) return;
  const now = Date.now();
  if (now - _lastMatchBcast < 4000) return; // 매 GPS 틱마다가 아니라 최소 4초 간격
  _lastMatchBcast = now;
  try { await api.patch(`/walks/${walkId}/location`, { latitude: lat, longitude: lng }); } catch (_) {}
}

function setBounds(ctx) {
  if (!ctx.partner) return;
  const pad = 0.0008;
  ctx.fbBounds = {
    minLat: Math.min(ctx.me.lat, ctx.partner.lat) - pad,
    maxLat: Math.max(ctx.me.lat, ctx.partner.lat) + pad,
    minLng: Math.min(ctx.me.lng, ctx.partner.lng) - pad,
    maxLng: Math.max(ctx.me.lng, ctx.partner.lng) + pad,
  };
}

function dropFoot(ctx, lat, lng, kind) {
  const node = el("div.w3-foot" + (kind === "partner" ? ".partner" : ""), {}, [icon("paw-print")]);
  const entity = makeEntity(ctx, node, lat, lng);
  ctx.footprints.push(entity);
  while (ctx.footprints.length > FOOT_MAX) ctx.footprints.shift().remove();
  const n = ctx.footprints.length;
  ctx.footprints.forEach((f, i) => {
    const age = n - 1 - i;
    f.node.classList.remove("fade-1", "fade-2", "fade-3");
    if (age >= 12) f.node.classList.add("fade-3");
    else if (age >= 8) f.node.classList.add("fade-2");
    else if (age >= 4) f.node.classList.add("fade-1");
  });
}

function placeMe(ctx) {
  if (ctx.meEntity) { moveEntity(ctx.meEntity, ctx.me); return; }
  const node = el("div.w3-me", { id: "w3-me" });
  ctx.meEntity = makeEntity(ctx, node, ctx.me.lat, ctx.me.lng);
}

function placePartner(ctx) {
  if (ctx.partnerEntity || !ctx.partner) return;
  const inner = el("div.w3-partner", { id: "w3-partner" }, [petCharacterEl(ctx.partnerPet, { size: 38 })]);
  const outer = ctx.map ? el("div.w3-pwrap", {}, [inner]) : inner;
  ctx.partnerEntity = makeEntity(ctx, outer, ctx.partner.lat, ctx.partner.lng);
}

function makeEntity(ctx, node, lat, lng) {
  if (ctx.map) {
    const m = new maplibregl.Marker({ element: node, anchor: "center" }).setLngLat([lng, lat]).addTo(ctx.map);
    return { node, move: (la, ln) => m.setLngLat([ln, la]), remove: () => m.remove() };
  }
  fbPlace(ctx, node, lat, lng);
  return { node, move: (la, ln) => fbPlace(ctx, node, la, ln), remove: () => node.remove() };
}

function moveEntity(entity, pos) { if (entity) entity.move(pos.lat, pos.lng); }

function fbPlace(ctx, node, lat, lng) {
  const b = ctx.fbBounds;
  let topPct = 50, leftPct = 50;
  if (b) {
    topPct = clamp(((b.maxLat - lat) / (b.maxLat - b.minLat)) * 100, 4, 96);
    leftPct = clamp(((lng - b.minLng) / (b.maxLng - b.minLng)) * 100, 4, 96);
  }
  node.style.top = topPct + "%";
  node.style.left = leftPct + "%";
  if (node.parentNode !== ctx.fallback) ctx.fallback.append(node);
  return node;
}

function fitBoth(ctx) {
  if (!ctx.map || !ctx.partner) return;
  const apply = () => {
    try {
      ctx.map.fitBounds(
        [
          [Math.min(ctx.me.lng, ctx.partner.lng), Math.min(ctx.me.lat, ctx.partner.lat)],
          [Math.max(ctx.me.lng, ctx.partner.lng), Math.max(ctx.me.lat, ctx.partner.lat)],
        ],
        { padding: 90, maxZoom: 16, duration: 500 }
      );
    } catch (_) {}
  };
  if (ctx.map.loaded()) apply(); else ctx.map.on("load", apply);
}
