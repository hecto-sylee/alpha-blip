// screens/matching.js — 산책 매칭중 + 발자국 트래킹 (담당: W3, 라우트 #/matching/:id)
//
// 흐름:
//   진입 직후 GET /match-requests/:id 폴링(구 match.js requestWaitScreen 이식).
//     · accepted + match_session_id → 세션 확보(상대 표시, [매칭 성공] 활성)
//     · rejected/expired/cancelled  → 토스트 + #/home
//   지도엔 본인(빨강) + 상대(강아지 캐릭터 핀) 둘만. nearby 폴링은 하지 않는다.
//   발자국은 프론트 시뮬레이션: 폴링 틱마다 직전 위치에 paw-print 마커를 누적
//   (최근 N개만 유지, 오래된 것은 옅게). 백엔드 변경 없음(D4).
//   [매칭 성공] → store.clearWalkClips() → navigate(`/walk?match=<sid>`) 로 산책중에 인계.
//
// 데모 목업은 자동 수락(matches.py: receiver.is_mock 이면 create_request 에서 즉시 accept)
// → 첫 폴링 틱에 바로 세션 단계로 들어간다.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, onLeave, icon, celebrate } from "../ui.js";
import { navigate } from "../router.js";
import * as poll from "../polling.js";
import { getOnce } from "../geo.js";
import { petCharacterEl } from "../character.js";

// 기존 산책 지도와 동일한 OSM 래스터 스타일(외부 타일).
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

const STATUS_POLL_MS = 2000; // 요청 상태 폴링 주기
const FOOT_TICK_MS = 1200;   // 발자국/접근 시뮬 주기
const FOOT_MAX = 24;         // 누적 발자국 최대(둘 합산) — 넘으면 오래된 것 제거

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const lerp = (a, b, t) => ({ lat: a.lat + (b.lat - a.lat) * t, lng: a.lng + (b.lng - a.lng) * t });

export async function matchingScreen(params) {
  setTab(null); // 몰입 모드
  const reqId = params.id; // = match_request_id

  // 본인 펫(축하 모션/대비용). 실패해도 화면은 그린다.
  let myPet = null;
  try { myPet = (await api.get("/auth/me")).pets?.[0] || null; } catch (_) {}

  // 시작 좌표: 데모면 데모 원점, 아니면 GPS 1회(헤드리스는 주입 좌표).
  const start = await resolveStart();

  // --- DOM scaffold ---
  const statusText = el("span.strong", { id: "w3-status", text: "상대의 수락을 기다리는 중…" });
  const hintText = el("span", { id: "w3-hint-text", text: "요청을 보냈어요. 상대가 수락하면 함께 걸어요." });
  const cta = el("button.cta", { id: "w3-cta", text: "수락 대기 중…", disabled: true });

  const mapEl = el("div.w3-map", { id: "w3-map" });
  const fallback = el("div.w3-fallback.hidden", { id: "w3-fallback" });
  const top = el("div.w3-top", {}, [el("span.dotlive"), statusText]);
  const bottom = el("div.w3-bottom", {}, [
    el("div.w3-hint", {}, [icon("footprints"), hintText]),
    cta,
  ]);
  const screen = el("div.map-screen", {}, [mapEl, fallback, top, bottom]);
  mount(screen);

  // 매칭 지도도 한 화면을 꽉 채운다(홈/산책과 동일한 컨테이너 규약).
  document.getElementById("view")?.classList.add("walk-view");
  onLeave(() => document.getElementById("view")?.classList.remove("walk-view"));

  // --- 화면 상태 ---
  const ctx = {
    map: null,
    fallback,
    useFallback: false,
    reqId,
    sessionId: null,
    proceeding: false,
    myPet,
    partnerPet: null,
    me: { ...start.me },
    partner: null,                     // 세션 확보 후 현재 상대 좌표
    partnerStart: start.partnerStart,  // 데모 고정 좌표(있으면)
    demo: start.demo,
    meEntity: null,
    partnerEntity: null,
    footprints: [],
    fbBounds: null,
  };

  initMap(ctx, mapEl);
  placeMe(ctx);

  // --- 요청 상태 폴링 (구 requestWaitScreen 로직 이식) ---
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

  // --- [매칭 성공] → 산책중으로 인계 ---
  cta.addEventListener("click", () => {
    if (!ctx.sessionId || ctx.proceeding) return;
    ctx.proceeding = true;
    poll.stop("w3-match-status");
    poll.stop("w3-footsteps");
    store.clearWalkClips();                 // 새 산책 클립 누적을 깨끗이 시작
    try { celebrate(ctx.myPet); } catch (_) {}
    setTimeout(() => navigate(`/walk?match=${ctx.sessionId}`), 500);
  });

  onLeave(() => {
    poll.stop("w3-match-status");
    poll.stop("w3-footsteps");
  });
}

// 시작 좌표/모드 결정.
async function resolveStart() {
  const demo = store.demo;
  if (demo && typeof demo.lat === "number" && typeof demo.lng === "number") {
    return {
      me: { lat: demo.lat, lng: demo.lng },
      partnerStart:
        typeof demo.mockLat === "number" && typeof demo.mockLng === "number"
          ? { lat: demo.mockLat, lng: demo.mockLng }
          : null,
      demo: true,
    };
  }
  try {
    const pos = await getOnce();
    return { me: { lat: pos.lat, lng: pos.lng }, partnerStart: null, demo: false };
  } catch (_) {
    // 헤드리스/권한 거부 — 데모 원점(큰길타워)으로 폴백해 화면은 그려준다.
    return { me: { lat: 37.5009, lng: 127.0398 }, partnerStart: null, demo: false };
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
      container: mapEl,
      style: OSM_STYLE,
      center: [ctx.me.lng, ctx.me.lat],
      zoom: 16,
      attributionControl: true,
    });
    ctx.map.on("error", () => {}); // 타일 에러는 흐름을 깨지 않음
    ctx.map.on("load", () => { placeMe(ctx); if (ctx.partner) placePartner(ctx); });
  } catch (_) {
    ctx.useFallback = true;
    ctx.fallback.classList.remove("hidden");
  }
}

// 세션 확보: 상대 프로필 로드 → 상대 마커 + 발자국 시뮬 시작 + CTA 활성.
async function onAccepted(ctx, sessionId) {
  if (ctx.sessionId) return;
  ctx.sessionId = sessionId;

  let partnerNick = "친구";
  try {
    const s = await api.get(`/match-sessions/${sessionId}`);
    partnerNick = s.partner?.nickname || "친구";
    ctx.partnerPet = s.partner?.pet || null;
  } catch (_) {}
  if (!ctx.partnerPet) ctx.partnerPet = { name: partnerNick };

  // 상대 시작 좌표: 데모 고정 좌표 또는 본인 북동쪽 ~200m.
  ctx.partner = ctx.partnerStart
    ? { ...ctx.partnerStart }
    : { lat: ctx.me.lat + 0.0016, lng: ctx.me.lng + 0.0017 };

  // 폴백 투영용 경계(본인+상대 시작점 + 여유).
  const pad = 0.0008;
  ctx.fbBounds = {
    minLat: Math.min(ctx.me.lat, ctx.partner.lat) - pad,
    maxLat: Math.max(ctx.me.lat, ctx.partner.lat) + pad,
    minLng: Math.min(ctx.me.lng, ctx.partner.lng) - pad,
    maxLng: Math.max(ctx.me.lng, ctx.partner.lng) + pad,
  };

  placeMe(ctx); // 폴백 좌표가 경계와 함께 다시 잡히도록 보강
  placePartner(ctx);
  fitBoth(ctx);

  const st = document.getElementById("w3-status");
  if (st) st.textContent = `${partnerNick}님이 다가오고 있어요`;
  const ht = document.getElementById("w3-hint-text");
  if (ht) ht.textContent = "발자국을 따라 가까워지는 중 — 만나면 매칭을 확정해요.";
  const cta = document.getElementById("w3-cta");
  if (cta) { cta.disabled = false; cta.textContent = "매칭 성공"; }

  // 발자국 트래킹 시뮬 — 틱마다 직전 위치에 발자국을 떨구고 서로 가까워진다.
  poll.start("w3-footsteps", () => footTick(ctx), FOOT_TICK_MS);
}

function footTick(ctx) {
  if (!ctx.partner) return;
  // 직전(=현재) 위치에 발자국을 남긴다.
  dropFoot(ctx, ctx.me.lat, ctx.me.lng, "me");
  dropFoot(ctx, ctx.partner.lat, ctx.partner.lng, "partner");

  // 서로 가까워진다(상대가 더 적극적으로 접근).
  const partnerPrev = { ...ctx.partner };
  ctx.partner = lerp(ctx.partner, ctx.me, 0.18);
  ctx.me = lerp(ctx.me, partnerPrev, 0.05);

  moveEntity(ctx.meEntity, ctx.me);
  moveEntity(ctx.partnerEntity, ctx.partner);
}

function dropFoot(ctx, lat, lng, kind) {
  const node = el("div.w3-foot" + (kind === "partner" ? ".partner" : ""), {}, [icon("paw-print")]);
  const entity = makeEntity(ctx, node, lat, lng);
  ctx.footprints.push(entity);
  while (ctx.footprints.length > FOOT_MAX) ctx.footprints.shift().remove();
  // 오래된 발자국일수록 옅게(trail fade).
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
  // 지도 마커는 transform을 maplibre가 제어하므로 pop 애니메이션은 안쪽 노드에만 둔다.
  const outer = ctx.map ? el("div.w3-pwrap", {}, [inner]) : inner;
  ctx.partnerEntity = makeEntity(ctx, outer, ctx.partner.lat, ctx.partner.lng);
}

// 좌표에 노드를 배치하고 move/remove 핸들을 돌려준다(지도/폴백 공용).
function makeEntity(ctx, node, lat, lng) {
  if (ctx.map) {
    const m = new maplibregl.Marker({ element: node, anchor: "center" }).setLngLat([lng, lat]).addTo(ctx.map);
    return { node, move: (la, ln) => m.setLngLat([ln, la]), remove: () => m.remove() };
  }
  fbPlace(ctx, node, lat, lng);
  return { node, move: (la, ln) => fbPlace(ctx, node, la, ln), remove: () => node.remove() };
}

function moveEntity(entity, pos) { if (entity) entity.move(pos.lat, pos.lng); }

// 폴백(WebGL 불가): 경계 박스 내 비율로 절대배치.
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
