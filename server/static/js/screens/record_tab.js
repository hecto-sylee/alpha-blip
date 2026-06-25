// screens/record_tab.js — 기록 탭 재설계 (담당: W5, 라우트 #/diary)
// W0 스텁: 시그니처만 고정. W5가 이 파일을 통째로 구현한다. (query.date?)
import { el, mount, setTab } from "../ui.js";

export async function recordTabScreen(_p, query) {
  setTab("diary");
  mount(el("div.stack", {}, [el("h1.h1", { text: "W5 · 기록 탭 준비 중" })]));
}
