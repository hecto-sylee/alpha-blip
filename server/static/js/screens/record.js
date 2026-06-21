// screens/record.js — SCR-20 기록 작성 에디터 (F-10). M3 Expressive.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, onLeave, reducedMotion, settleCardToCalendar, announceUnlocks } from "../ui.js";
import { navigate } from "../router.js";
import { openCamera, record as recordClip, stopStream, mediaSupported, CLIP_MS } from "../media.js";

const DRAFT_KEY = "blip_record_draft";

function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export async function recordScreen(_params, query = {}) {
  setTab("diary");

  // 오늘의 퀘스트(있으면 미션별 촬영 + 자동 연결)
  let today = null;
  try { today = await api.get("/quests/today?scope=user"); } catch (_) {}
  const quest = today && today.locked ? today.quest : null;
  const dailyQuestId = today && today.locked ? today.daily_quest_id : null;

  // 내 방 목록 (방 공유용)
  let rooms = [];
  try { rooms = (await api.get("/rooms")).rooms || []; } catch (_) {}

  // 드래프트 복원
  let draft = {};
  try { draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || "{}"); } catch (_) {}

  // 방에서 "기록 올리기" 또는 데모 플로우로 들어오면 방 공유로 프리셋
  const demo = store.demo;
  const demoRoomId = demo?.roomId && rooms.some((r) => r.room_id === demo.roomId) ? demo.roomId : null;
  const presetRoom = query.room || demoRoomId || null;
  const state = {
    clips: [],                        // {clip_id, mission_id, durationMs, url}
    text: draft.text || "",
    visibility: presetRoom ? "room" : (draft.visibility || store.settings.defaultVisibility || "diary"),
    roomId: presetRoom || draft.roomId || (rooms[0] && rooms[0].room_id) || null,
    walkId: query.walk || null,
    matchId: query.match || null,
    stream: null,
    recording: false,
  };

  const saveDraft = () => localStorage.setItem(DRAFT_KEY, JSON.stringify({ text: state.text, visibility: state.visibility, roomId: state.roomId }));

  // ---- camera ----
  const camBox = el("div.cam-box", { id: "cam-box" }, [el("div.muted", { text: "카메라 준비 중…" })]);
  const recRing = el("div.rec-ring", { id: "rec-ring", title: "2초 촬영" }, [el("div.dot2")]);
  let curMissionId = null; // 다음 촬영에 태깅할 미션

  async function initCamera() {
    if (!mediaSupported()) return camDenied("이 브라우저는 카메라를 지원하지 않아요.");
    try {
      state.stream = await openCamera();
      camBox.innerHTML = "";
      const v = el("video", { id: "cam-video", autoplay: "", muted: "", playsinline: "" });
      v.muted = true; v.srcObject = state.stream;
      camBox.append(v, recRing);
    } catch (code) {
      camDenied(code === "denied" ? "카메라·마이크 권한이 거부됐어요. 권한을 허용해 주세요." : "카메라를 열 수 없어요.");
    }
  }
  function camDenied(msg) {
    camBox.classList.add("denied");
    camBox.innerHTML = "";
    camBox.append(el("div.center", {}, [el("div", { style: "font-size:2rem", text: "📷" }), el("p.sub", { text: msg })]));
  }

  recRing.addEventListener("click", () => doRecord(curMissionId));

  async function doRecord(missionId) {
    if (state.recording || !state.stream) return;
    state.recording = true;
    recRing.classList.add("recording");
    const count = el("div.rec-count", { id: "rec-count", text: "2.0" });
    camBox.append(count);
    try {
      const { blob, durationMs } = await recordClip(state.stream, {
        onTick: (left) => { count.textContent = (left / 1000).toFixed(1); },
      });
      count.remove();
      // 업로드
      const form = new FormData();
      form.append("file", blob, "clip.webm");
      form.append("duration_ms", String(CLIP_MS));
      form.append("order", String(state.clips.length));
      if (missionId) form.append("mission_id", missionId);
      const res = await api.upload("/clips/upload", form);
      const url = await api.blobUrl(`/clips/${res.clip_id}/stream`).catch(() => null);
      state.clips.push({ clip_id: res.clip_id, mission_id: missionId, durationMs, url });
      renderClips();
      markMissionDone(missionId);
      toast("2초 클립 촬영 완료 🎬", "ok");
    } catch (e) {
      toast(typeof e === "string" ? "녹화에 실패했어요" : (e.message || "업로드 실패"), "err");
    } finally {
      state.recording = false;
      recRing.classList.remove("recording");
    }
  }

  // ---- clip strip ----
  const clipStrip = el("div.clip-strip", { id: "clip-strip" });
  function renderClips() {
    clipStrip.innerHTML = "";
    if (!state.clips.length) {
      clipStrip.append(el("p.sub", { text: "아직 담은 클립이 없어요. 카메라의 동그란 버튼으로 2초를 담아요." }));
      return;
    }
    state.clips.forEach((c, i) => {
      const chip = el("div.clip-chip", { dataset: { clipId: c.clip_id } });
      if (c.url) { const v = el("video", { src: c.url, muted: "", playsinline: "" }); v.muted = true; chip.append(v); }
      else chip.append(el("span", { text: "🎬" }));
      chip.append(el("span.len", { text: "2s" }));
      const x = el("span.x", { text: "✕" });
      x.addEventListener("click", (e) => {
        e.stopPropagation();
        state.clips.splice(i, 1);
        renderClips();
      });
      chip.append(x);
      clipStrip.append(chip);
    });
  }

  // ---- missions (촬영 태깅) ----
  const missionWrap = el("div.stack");
  function renderMissions() {
    missionWrap.innerHTML = "";
    if (!quest) return;
    missionWrap.append(el("div.h2", { text: `🎯 ${quest.title}` }));
    (quest.missions || []).forEach((m) => {
      const done = state.clips.some((c) => c.mission_id === m.id);
      const row = el("div.mission-row" + (done ? ".done" : ""), { dataset: { mid: m.id } }, [
        el("div.ord", { text: done ? "✓" : String(m.order) }),
        el("div", { style: "flex:1" }, [
          el("div.m-title", { text: m.title }),
          m.hint && el("div.m-hint", { text: m.hint }),
        ]),
        el("button.btn", { text: done ? "다시" : "촬영", onclick: () => { curMissionId = m.id; doRecord(m.id); } }),
      ]);
      missionWrap.append(row);
    });
  }
  function markMissionDone() { renderMissions(); }

  // ---- visibility ----
  const visSeg = el("div.seg", { id: "vis-seg" });
  [["diary", "📔 일기"], ["room", "👥 방 공유"]].forEach(([val, label]) => {
    const o = el("div.opt" + (val === state.visibility ? ".sel" : ""), { text: label, dataset: { val } });
    o.addEventListener("click", () => {
      if (val === "room" && !rooms.length) { toast("먼저 방에 참여해 주세요 (기록 탭)", "err"); return; }
      state.visibility = val; saveDraft();
      visSeg.querySelectorAll(".opt").forEach((n) => n.classList.remove("sel"));
      o.classList.add("sel");
      roomSelect.style.display = val === "room" ? "block" : "none";
    });
    visSeg.append(o);
  });
  const roomSelect = el("select.select", { id: "room-select", style: state.visibility === "room" ? "" : "display:none" },
    rooms.map((r) => el("option", { value: r.room_id, text: r.name })));
  if (state.roomId) roomSelect.value = state.roomId;
  roomSelect.addEventListener("change", () => { state.roomId = roomSelect.value; saveDraft(); });

  // ---- text ----
  const textArea = el("textarea.input", { id: "record-text", placeholder: "오늘 산책은 어땠나요? (선택)" });
  textArea.value = state.text;
  textArea.addEventListener("input", () => { state.text = textArea.value; saveDraft(); });

  // ---- save ----
  const cta = el("button.cta", { id: "save-record", text: "기록 저장" });
  cta.addEventListener("click", saveRecord);

  async function saveRecord() {
    cta.disabled = true; cta.textContent = "저장 중…";
    const payload = {
      visibility: state.visibility,
      walked_at: todayStr(),
      text: state.text.trim() || null,
      clip_ids: state.clips.map((c) => c.clip_id),
      daily_quest_id: dailyQuestId,
    };
    if (state.walkId) payload.walk_session_id = state.walkId;
    if (state.matchId) payload.match_session_id = state.matchId;
    if (state.visibility === "room") payload.room_id = state.roomId;
    try {
      const res = await api.post("/records", payload);
      localStorage.removeItem(DRAFT_KEY);
      if (demo) store.clearDemo();
      stopStream(state.stream);
      toast("기록을 저장했어요 📔", "ok");
      announceUnlocks(res?.unlocked); // 새로 달성한 업적 뱃지 알림
      // 카드가 캘린더로 안착하는 모션 후 다이어리로
      sessionStorage.setItem("blip_record_saved_motion", "1");
      if (!reducedMotion()) {
        await settleCardToCalendar(document.querySelector("#record-editor .card"));
      }
      navigate("/diary?saved=1");
    } catch (e) {
      toast(e.message || "저장 실패", "err");
      cta.disabled = false; cta.textContent = "기록 저장";
    }
  }

  onLeave(() => stopStream(state.stream));

  mount(
    el("div.stack", { id: "record-editor" }, [
      el("h1.h1", { text: "산책 기록" }),
      el("div.card", {}, [
        el("div.row", {}, [el("span", { text: "📅" }), el("span", { text: todayStr() }), el("span.spacer"), el("span.sub", { text: state.matchId ? "함께 산책" : "혼자 산책" })]),
      ]),
      camBox,
      el("div.h2", { text: "담은 클립" }),
      clipStrip,
      missionWrap,
      el("div.field", {}, [el("label", { text: "공개 범위" }), visSeg, roomSelect]),
      el("div.field", {}, [el("label", { text: "메모" }), textArea]),
      cta,
      el("div", { style: "height:8px" }),
    ])
  );

  renderClips();
  renderMissions();
  initCamera();
}
