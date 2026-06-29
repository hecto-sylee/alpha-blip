// screens/camera.js — W4 카메라 촬영 (가로 몰입). 스펙: docs/v2_redesign/14_W4_camera.md
// 라우트 #/camera, setTab(null). ?quest 있으면 상단 한 줄, 없으면 미표기.
// 촬영(2초 클립) → POST /clips/upload → store.addWalkClip → #/walk 복귀.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, onLeave, icon } from "../ui.js";
import { navigate } from "../router.js";
import { openCamera, record as recordClip, stopStream, mediaSupported, CLIP_MS } from "../media.js";

// query.mission = 미션 id(클립 태깅), query.quest = 퀘스트 한 줄 텍스트
export async function cameraScreen(_params, query = {}) {
  setTab(null); // 몰입 모드 — 탭바 숨김

  const mission = query.mission || null; // 업로드 폼 mission_id 태깅용
  const quest = query.quest || null;     // 상단 퀘스트 한 줄(있을 때만)

  const state = { stream: null, recording: false };

  // ---- 가로 전체화면 스캐폴드 ----
  const video = el("video.cam-preview", { id: "cam-video", autoplay: "", muted: "", playsinline: "" });
  video.muted = true; // 속성만으론 일부 브라우저가 무시 → 프로퍼티로도 보장

  const stage = el("div.cam-stage", { id: "cam-stage" }, [video]);

  // 상단: (좌) 퀘스트 한 줄 — 있을 때만 / (우) 닫기 X
  const closeBtn = el("button.cam-close", { id: "cam-close", "aria-label": "촬영 취소" }, [icon("x")]);
  closeBtn.addEventListener("click", () => navigate("/walk")); // 취소 → 산책 중 복귀

  const questBar = quest
    ? el("div.cam-quest", { id: "cam-quest" }, [icon("target"), el("span.cam-quest-text", { text: quest })])
    : null;

  const topBar = el("div.cam-top", {}, [
    questBar || el("span.spacer"), // 퀘스트 없으면 빈 영역(미표기)
    closeBtn,
  ]);

  // 하단 중앙: 촬영 버튼(둥근 큰 입체 버튼)
  const shootBtn = el("button.cam-shoot", { id: "cam-shoot", "aria-label": "촬영" }, [el("span.cam-shoot-dot")]);
  shootBtn.addEventListener("click", () => doRecord());
  const bottomBar = el("div.cam-bottom", {}, [shootBtn]);

  const screenEl = el("div.camera-screen.landscape", { id: "camera-screen" }, [stage, topBar, bottomBar]);

  // ---- 카메라 초기화 ----
  async function initCamera() {
    if (!mediaSupported()) return camError("이 브라우저는 카메라를 지원하지 않아요.");
    try {
      state.stream = await openCamera();
      video.srcObject = state.stream;
    } catch (code) {
      camError(code === "denied" ? "카메라·마이크 권한이 거부됐어요." : "카메라를 열 수 없어요.");
    }
  }
  function camError(msg) {
    stage.classList.add("denied");
    stage.innerHTML = "";
    stage.append(el("div.cam-error", {}, [icon("camera-off"), el("p", { text: msg })]));
    shootBtn.disabled = true;
  }

  // ---- 촬영 → 업로드 → 누적 → 복귀 ----
  async function doRecord() {
    if (state.recording || !state.stream) return;
    state.recording = true;
    shootBtn.classList.add("recording");
    const count = el("div.cam-count", { id: "cam-count", text: "2.0" });
    stage.append(count);
    try {
      const { blob } = await recordClip(state.stream, {
        onTick: (left) => { count.textContent = (left / 1000).toFixed(1); },
      });
      count.remove();

      const form = new FormData();
      form.append("file", blob, "clip.webm");
      form.append("duration_ms", String(CLIP_MS));
      form.append("order", String(store.walkClips.length));
      if (mission) form.append("mission_id", mission);
      const { clip_id } = await api.upload("/clips/upload", form);

      store.addWalkClip({ clip_id, mission_id: mission || null, order: store.walkClips.length });
      toast("클립을 담았어요", "ok", "film");
      stopStream(state.stream);
      navigate("/walk"); // 미종료 → 산책 중 복귀 (W2가 퀘스트 완료 갱신)
    } catch (e) {
      count.remove();
      toast(typeof e === "string" ? "녹화에 실패했어요" : (e.message || "업로드 실패"), "err");
      shootBtn.classList.remove("recording");
      state.recording = false;
    }
  }

  // mount()로 이전 화면/오버레이를 정리하고 생명주기에 진입(빈 호스트 뷰).
  // 카메라는 변형(transform)이 걸린 .screen 래퍼 안에 두면 position:fixed의 컨테이닝 블록이
  // 래퍼로 바뀌어 전체화면이 깨진다 → overlay-root(뷰포트 기준)에 직접 띄운다(시트/셀러브레이트와 동일).
  mount(el("div.cam-host"));
  onLeave(() => stopStream(state.stream)); // 다음 화면 mount 시 스트림 정리(기존 패턴)
  document.getElementById("overlay-root").append(screenEl);
  initCamera();
}
