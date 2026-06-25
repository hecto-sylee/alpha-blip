// screens/pet_diary.js — 펫일기 작성/상세 (담당: W6, 라우트 #/pet-diary/new · #/pet-diary/:id)
// W0 스텁: 시그니처만 고정. W6가 이 파일을 통째로 구현한다.
import { el, mount, setTab } from "../ui.js";

export async function petDiaryNewScreen(_p, query) {
  setTab("diary");
  mount(el("div.stack", {}, [el("h1.h1", { text: "W6 · 펫일기 작성 준비 중" })]));
}

export async function petDiaryViewScreen(params) {
  setTab("diary");
  mount(el("div.stack", {}, [el("h1.h1", { text: "W6 · 펫일기 상세 준비 중" })]));
}
