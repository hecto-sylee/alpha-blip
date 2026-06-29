// screens/camera.js — W4 카메라 촬영 (세로 기준, 회전/가로변환 없음).
// 라우트 #/camera, setTab(null). ?quest 있으면 상단 한 줄.
// 촬영(2초 클립) → POST /clips/upload → store.addWalkClip → #/walk 복귀.
//
// 방향 정책(세로 통일): 폰 자연스러운 세로 그대로 촬영한다. 가로 강제잠금/회전 없음.
// 카메라 피드를 회전 없이 720×1280 캔버스에 cover-fit → 항상 똑바로 선 세로 9:16로 녹화.
// (솔로·듀얼 동일. 듀얼 합성은 서버가 두 세로 영상을 상/하로 합친다.)
// 미리보기 = 캔버스(녹화본 그대로)라 보이는 대로 찍힌다.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, onLeave, icon } from "../ui.js";
import { navigate } from "../router.js";
import { openCamera, record as recordClip, stopStream, mediaSupported, CLIP_MS } from "../media.js";

export async function cameraScreen(_params, query = {}) {
  setTab(null);

  const mission = query.mission || null;
  const quest = query.quest || null;
  // 듀얼(매칭)=반쪽(720×640)으로 촬영 → 합성 시 상/하로 합쳐져 9:16. "반으로 찍고 결과도 반".
  // 솔로=세로 풀(720×1280).
  const dual = !!(query && query.dual === "1");
  // 듀얼 합성 위치(top=요청자/bottom=수락자). 알면 프리뷰를 그 칸에 배치(중앙 아님).
  const half = dual ? (query.half === "bottom" ? "bottom" : query.half === "top" ? "top" : null) : null;
  const OUT_W = 720, OUT_H = dual ? 640 : 1280;
  const state = { stream: null, recording: false, raf: 0 };

  // 숨긴 원본 비디오 + 보이는 캔버스(미리보기 = 녹화본)
  const video = el("video", { id: "cam-video", autoplay: "", muted: "", playsinline: "" });
  video.muted = true;
  // display:none 이면 iOS가 디코딩을 멈춰 캔버스가 빈 프레임이 됨 → 캔버스 뒤에 opacity:0 으로 숨김(렌더 유지)
  video.style.cssText = "position:absolute; inset:0; width:100%; height:100%; opacity:0; pointer-events:none;";
  const canvas = el("canvas.cam-canvas", { id: "cam-canvas", width: OUT_W, height: OUT_H });
  const ctx = canvas.getContext("2d");

  const stage = el("div.cam-stage", { id: "cam-stage" }, [video, canvas]);
  // 듀얼: 내 칸 반대쪽에 '상대 영상 자리' 플레이스홀더(합성될 모습 미리보기) + 분할선
  const otherHalf = half
    ? el("div.cam-otherhalf", {}, [
        el("div.cam-otherhalf-inner", {}, [icon("user"), el("span", { text: "상대 영상 자리" })]),
      ])
    : null;

  // 매 프레임: 회전 없이 cover-fit 으로 캔버스에 그림(세로 9:16 출력)
  function drawFrame() {
    const vw = video.videoWidth, vh = video.videoHeight;
    if (vw && vh) {
      const s = Math.max(OUT_W / vw, OUT_H / vh); // cover
      const dw = vw * s, dh = vh * s;
      ctx.drawImage(video, (OUT_W - dw) / 2, (OUT_H - dh) / 2, dw, dh);
    }
    state.raf = requestAnimationFrame(drawFrame);
  }

  // ---- 상단/하단 컨트롤 ----
  const closeBtn = el("button.cam-close", { id: "cam-close", "aria-label": "촬영 취소" }, [icon("x")]);
  closeBtn.addEventListener("click", () => navigate("/walk"));

  const questBar = quest
    ? el("div.cam-quest", { id: "cam-quest" }, [icon("target"), el("span.cam-quest-text", { text: quest })])
    : null;

  const topBar = el("div.cam-top", {}, [questBar || el("span.spacer"), closeBtn]);

  const shootBtn = el("button.cam-shoot", { id: "cam-shoot", "aria-label": "촬영" }, [el("span.cam-shoot-dot")]);
  shootBtn.addEventListener("click", () => doRecord());
  const bottomBar = el("div.cam-bottom", {}, [shootBtn]);

  const screenEl = el(
    "div.camera-screen" + (half ? `.dual-half.half-${half}` : ""),
    { id: "camera-screen" },
    [stage, otherHalf, topBar, bottomBar].filter(Boolean)
  );

  // ---- 카메라 초기화 ----
  async function initCamera() {
    if (!mediaSupported()) return camError("이 브라우저는 카메라를 지원하지 않아요.");
    try {
      state.stream = await openCamera();
      video.srcObject = state.stream;
      await video.play().catch(() => {});
      state.raf = requestAnimationFrame(drawFrame);
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
        canvas, // 회전 없는 세로 캔버스를 녹화
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
      navigate("/walk");
    } catch (e) {
      count.remove();
      toast(typeof e === "string" ? "녹화에 실패했어요" : (e.message || "업로드 실패"), "err");
      shootBtn.classList.remove("recording");
      state.recording = false;
    }
  }

  mount(el("div.cam-host"));
  onLeave(() => { cancelAnimationFrame(state.raf); stopStream(state.stream); });
  document.getElementById("overlay-root").append(screenEl);
  initCamera();
}
