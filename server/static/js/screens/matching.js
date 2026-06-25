// screens/matching.js — 산책 매칭중 + 발자국 (담당: W3, 라우트 #/matching/:id)
// W0 스텁: 시그니처만 고정. W3가 이 파일을 통째로 구현한다. (params.id)
import { el, mount, setTab } from "../ui.js";

export async function matchingScreen(params) {
  setTab(null); // 몰입 모드
  mount(el("div.stack", {}, [el("h1.h1", { text: "W3 · 매칭중 준비 중" })]));
}
