// screens/camera.js — 가로 카메라 촬영 (담당: W4, 라우트 #/camera)
// W0 스텁: 시그니처만 고정. W4가 이 파일을 통째로 구현한다. (query.mission, query.quest)
import { el, mount, setTab } from "../ui.js";

export async function cameraScreen(_p, query) {
  setTab(null); // 몰입 모드
  mount(el("div.stack", {}, [el("h1.h1", { text: "W4 · 카메라 준비 중" })]));
}
