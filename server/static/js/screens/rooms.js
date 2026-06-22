// screens/rooms.js — 방 탭 (R1): 로그 피드 랜딩 · SCR-24 방 생성 · SCR-26 참여 (F-11)
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, loading, staggerMotion } from "../ui.js";
import { navigate } from "../router.js";
import { petCharacterEl } from "../character.js";

const MODE_LABEL = { walk_friend: "🐕 산책 친구", family: "👨‍👩‍👧 가족" };

function fmtWhen(rec) {
  if (rec.walked_at) return rec.walked_at;
  const t = rec.created_at ? new Date(rec.created_at) : null;
  if (!t || isNaN(t)) return "";
  return `${t.getMonth() + 1}월 ${t.getDate()}일`;
}

// ---------------- 방 탭 랜딩 = 셋로그풍 로그 피드 ----------------
export async function roomsListScreen() {
  setTab("room");
  loading();

  let rooms = [];
  try { rooms = (await api.get("/rooms")).rooms || []; }
  catch (e) { toast(e.message || "방 목록을 불러오지 못했어요", "err"); }

  // 하단 진입 버튼 (스모크/IA 안정 위해 id 유지)
  const createBtn = el("button.cta", { id: "room-create-cta", text: "+ 방 만들기", onclick: () => navigate("/rooms/new") });
  const joinBtn = el("button.btn", { id: "room-join-cta", text: "코드로 참여", onclick: () => navigate("/rooms/join") });

  const pending = store.pendingJoin
    ? el("div.banner", { onclick: () => navigate("/rooms/join") }, [
        el("span", { text: "🔗" }),
        el("span", { text: `초대 코드 ${store.pendingJoin} 로 참여하기` }),
      ])
    : null;

  const header = el("div.row", {}, [el("h1.h1", { text: "방" }), el("span.spacer")]);

  // 방이 없으면 빈 상태 + CTA
  if (!rooms.length) {
    mount(
      el("div.stack", {}, [
        header,
        pending,
        el("div.empty", {}, [
          el("div.big", { text: "🏠" }),
          el("p", { text: "아직 참여한 방이 없어요." }),
          el("p.sub", { text: "방을 만들거나 코드로 참여해 펫 로그를 함께 쌓아보세요." }),
        ]),
        el("div", { style: "height:4px" }),
        createBtn,
        joinBtn,
      ])
    );
    return;
  }

  // 각 방의 타임라인을 받아 최신순 병합 (클라이언트 통합 피드)
  let details = [];
  try {
    details = await Promise.all(rooms.map((r) => api.get(`/rooms/${r.room_id}`).catch(() => null)));
  } catch (_) { /* 개별 실패는 무시하고 받은 것만 */ }

  const feed = [];
  details.forEach((d) => {
    if (!d) return;
    (d.timeline || []).forEach((rec) => feed.push({ rec, room: d }));
  });
  feed.sort((a, b) => (String(a.rec.created_at) < String(b.rec.created_at) ? 1 : -1));

  const state = { filter: "all" };
  const chipRow = el("div.row", { id: "room-filter", style: "overflow-x:auto; padding:2px 0; flex-wrap:nowrap" });
  const feedWrap = el("div.stack", { id: "room-feed" });

  function renderChips() {
    chipRow.innerHTML = "";
    const all = el("span.chip" + (state.filter === "all" ? ".on" : ""), {
      text: "전체", dataset: { filter: "all" },
      onclick: () => { state.filter = "all"; renderChips(); renderFeed(); },
    });
    chipRow.append(all);
    rooms.forEach((r) => {
      const c = el("span.chip" + (state.filter === r.room_id ? ".on" : ""), {
        text: r.name, dataset: { filter: r.room_id }, style: "white-space:nowrap",
        onclick: () => { state.filter = r.room_id; renderChips(); renderFeed(); },
      });
      chipRow.append(c);
    });
  }

  function renderFeed() {
    feedWrap.innerHTML = "";
    const items = feed.filter((f) => state.filter === "all" || f.room.room_id === state.filter);
    if (!items.length) {
      feedWrap.append(
        el("div.empty", {}, [
          el("div.big", { text: "📸" }),
          el("p", { text: "아직 공유된 로그가 없어요." }),
          el("p.sub", { text: "방에 첫 기록을 올려보세요." }),
        ])
      );
      return;
    }
    items.forEach((f) => feedWrap.append(feedCard(f.rec, f.room)));
    if (feedWrap.isConnected) {
      requestAnimationFrame(() => staggerMotion(feedWrap.querySelectorAll(".tl-item"), { y: -14, each: 0.045 }));
    }
  }

  renderChips();
  renderFeed();

  mount(
    el("div.stack", {}, [
      header,
      pending,
      chipRow,
      feedWrap,
      el("div", { style: "height:4px" }),
      createBtn,
      joinBtn,
    ])
  );
  requestAnimationFrame(() => staggerMotion(feedWrap.querySelectorAll(".tl-item"), { y: -14, each: 0.045 }));
}

// 피드 카드: 방이름·작성자·시간·클립·텍스트·반응 집계, 탭 시 방 상세로
function feedCard(rec, room) {
  const author = (room.members || []).find((m) => m.user_id === rec.user_id);

  const clips = el("div.tl-clips", {});
  if (rec.clips && rec.clips.length) {
    rec.clips.forEach((c) => {
      const chip = el("div.clip-chip", { dataset: { clipId: c.id } });
      chip.append(el("span", { text: "🎬" }));
      clips.append(chip);
      (async () => {
        try {
          const url = await api.blobUrl(c.stream_url.replace("/api", ""));
          chip.innerHTML = "";
          const v = el("video", { src: url, playsinline: "", muted: "" }); v.muted = true;
          chip.append(v);
        } catch (_) {}
      })();
    });
  }

  const rxSummary = (rec.reactions || []).filter((r) => r.count > 0);
  const rxBar = rxSummary.length
    ? el("div.rx-bar", {}, rxSummary.map((r) => el("span.chip", { text: `${r.emoji} ${r.count}` })))
    : null;

  return el(
    "div.card.tl-item",
    { dataset: { rid: rec.id, roomId: room.room_id }, style: "cursor:pointer", onclick: () => navigate(`/room/${room.room_id}`) },
    [
      el("div.tl-head", {}, [
        el("div.av.has-char", {}, [petCharacterEl((author && author.pet) || { id: rec.user_id, name: author ? author.nickname : "멤버" }, { size: 36 })]),
        el("div", {}, [
          el("div", { style: "font-weight:800", text: author ? author.nickname : "멤버" }),
          el("div.sub", {}, [el("span.chip.on", { text: room.name }), el("span", { text: `  ${fmtWhen(rec)}` })]),
        ]),
      ]),
      rec.text ? el("p", { text: rec.text }) : null,
      rec.clips && rec.clips.length ? clips : null,
      rxBar,
    ]
  );
}

// ---------------- SCR-24 방 생성 ----------------
export async function roomCreateScreen() {
  setTab("room");
  const state = { name: "", mode: "walk_friend" };

  const nameI = el("input.input", { id: "room-name", placeholder: "방 이름 (예: 동네 산책팟)" });
  const cta = el("button.cta", { id: "create-confirm", text: "방 만들기", disabled: true });
  nameI.addEventListener("input", () => { state.name = nameI.value; cta.disabled = !state.name.trim(); });

  const modeSeg = el("div.seg", { id: "mode-seg" });
  [["walk_friend", "🐕 산책 친구"], ["family", "👨‍👩‍👧 가족"]].forEach(([val, label]) => {
    const o = el("div.opt" + (val === state.mode ? ".sel" : ""), { text: label, dataset: { val } });
    o.addEventListener("click", () => {
      state.mode = val;
      modeSeg.querySelectorAll(".opt").forEach((n) => n.classList.remove("sel"));
      o.classList.add("sel");
    });
    modeSeg.append(o);
  });

  cta.addEventListener("click", async () => {
    cta.disabled = true; cta.textContent = "만드는 중…";
    try {
      const res = await api.post("/rooms", { name: state.name.trim(), mode: state.mode });
      toast("방을 만들었어요 🎉", "ok");
      navigate(`/room/${res.room_id}`);
    } catch (e) {
      toast(e.message || "생성 실패", "err");
      cta.disabled = false; cta.textContent = "방 만들기";
    }
  });

  mount(
    el("div.stack", {}, [
      el("button.btn.ghost", { text: "← 방", onclick: () => navigate("/rooms") }),
      el("h1.h1", { text: "새 방 만들기" }),
      el("div.field", {}, [el("label", { html: "방 이름 <span class='req'>*</span>" }), nameI]),
      el("div.field", {}, [el("label", { text: "모드" }), modeSeg]),
      cta,
    ])
  );
}

// ---------------- SCR-26 방 참여 (코드) ----------------
export async function roomJoinScreen(_params, query = {}) {
  setTab("room");
  const prefill = (query.code || store.pendingJoin || "").toUpperCase();

  const codeI = el("input.input.code-input", { id: "join-code", placeholder: "ABC123", maxlength: "6", value: prefill });
  const cta = el("button.cta", { id: "join-confirm", text: "참여하기" });
  const preview = el("div", { id: "join-preview" });

  cta.addEventListener("click", async () => {
    const code = codeI.value.trim().toUpperCase();
    if (code.length !== 6) { toast("6자리 코드를 입력해 주세요", "err"); return; }
    cta.disabled = true; cta.textContent = "확인 중…";
    try {
      const room = await api.get(`/rooms/code/${code}`);
      await api.post(`/rooms/${room.room_id}/join`, {});
      store.clearPendingJoin();
      toast(`'${room.name}' 방에 참여했어요`, "ok");
      navigate(`/room/${room.room_id}`);
    } catch (e) {
      toast(e.status === 404 ? "코드에 해당하는 방이 없어요" : (e.message || "참여 실패"), "err");
      cta.disabled = false; cta.textContent = "참여하기";
    }
  });

  mount(
    el("div.stack", {}, [
      el("button.btn.ghost", { text: "← 방", onclick: () => navigate("/rooms") }),
      el("h1.h1", { text: "코드로 참여" }),
      el("p.sub", { text: "친구에게 받은 6자리 참여 코드를 입력해요." }),
      el("div.field", {}, [el("label", { text: "참여 코드" }), codeI]),
      preview,
      cta,
    ])
  );

  setTimeout(() => codeI.focus(), 50);
}
