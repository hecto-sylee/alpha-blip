// screens/walking.js — 산책 중 HUD (담당: W2, 라우트 #/walk)
// W0 스텁: 시그니처만 고정. W2가 이 파일을 통째로 구현한다.
import { el, mount, setTab } from "../ui.js";

export async function walkingScreen() {
  setTab(null); // 몰입 모드
  mount(el("div.stack", {}, [el("h1.h1", { text: "W2 · 산책 중 준비 중" })]));
}
