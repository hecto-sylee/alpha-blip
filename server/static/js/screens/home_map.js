// screens/home_map.js — 홈 idle 지도 (담당: W1, 라우트 #/home)
// W0 스텁: 시그니처만 고정. W1이 이 파일을 통째로 구현한다.
import { el, mount, setTab } from "../ui.js";

export async function homeMapScreen() {
  setTab("home");
  mount(el("div.stack", {}, [el("h1.h1", { text: "W1 · 홈 지도 준비 중" })]));
}
