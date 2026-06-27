// screens/camera.js — 2초 촬영 (W4, 라우트 #/camera). 산책 중 클립 촬영 → store.walkClips.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, onLeave, icon } from "../ui.js";
import { navigate } from "../router.js";
import { openCamera, record as recordClip, stopStream, mediaSupported, CLIP_MS } from "../media.js";

function backBtn() { return el("button.btn.ghost", { text: "← 돌아가기", onclick: () => navigate("/walk") }); }

export async function cameraScreen(_p, query = {}) {
  setTab(null); // 몰입 모드
  const missionId = query.mission || null;
  const questTitle = query.quest ? decodeURIComponent(query.quest) : "오늘의 순간";

  if (!mediaSupported()) {
    mount(el("div.stack.center", {}, [el("h1.h1", { text: "카메라를 쓸 수 없어요" }),
      el("p.sub", { text: "HTTPS 또는 localhost에서 카메라 권한이 필요해요." }), backBtn()]));
    return;
  }
  let stream;
  try { stream = await openCamera(); }
  catch (e) {
    mount(el("div.stack.center", {}, [el("h1.h1", { text: e === "denied" ? "카메라 권한이 필요해요" : "카메라를 열 수 없어요" }),
      el("p.sub", { text: "브라우저 권한을 허용해 주세요." }), backBtn()]));
    return;
  }
  onLeave(() => stopStream(stream));

  const video = el("video.cap-video", { autoplay: "", playsinline: "", muted: "" });
  video.muted = true; video.srcObject = stream;
  const count = el("div.cap-count", { text: "" });
  const recBtn = el("button.cta.big", { id: "cam-rec", text: "2초 찍기" });
  let busy = false;
  recBtn.addEventListener("click", async () => {
    if (busy) return;
    busy = true; recBtn.disabled = true; recBtn.textContent = "촬영 중…";
    try {
      const { blob } = await recordClip(stream, { onTick: (l) => { count.textContent = (l / 1000).toFixed(1); } });
      count.textContent = "";
      const form = new FormData();
      form.append("file", blob, "clip.webm");
      form.append("duration_ms", String(CLIP_MS));
      form.append("order", String(store.walkClips.length));
      if (missionId) form.append("mission_id", missionId);
      const res = await api.upload("/clips/upload", form);
      store.addWalkClip({ clip_id: res.clip_id, mission_id: missionId, order: store.walkClips.length });
      toast("2초 클립 찍었어요!", "ok", "camera");
      navigate("/walk");
    } catch (e) {
      console.error("[camera] capture/upload failed:", e);
      toast(typeof e === "string" ? "녹화에 실패했어요" : (e.message || "업로드 실패"), "err");
      recBtn.disabled = false; recBtn.textContent = "2초 찍기"; busy = false;
    }
  });

  mount(el("div.cap-screen", {}, [
    el("div.cap-quest", {}, [icon("camera"), " ", questTitle]),
    el("div.cap-stage", {}, [video, count]),
    el("div.cap-foot", {}, [recBtn, el("button.btn.ghost", { text: "취소", onclick: () => navigate("/walk") })]),
  ]));
}
