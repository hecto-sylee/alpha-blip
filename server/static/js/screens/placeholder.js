// screens/placeholder.js — 다음 FE goal에서 구현될 화면의 임시 자리.
import { el, mount, setTab } from "../ui.js";

export function placeholder(title, tab, note) {
  return async () => {
    setTab(tab || null);
    mount(
      el("div.stack", {}, [
        el("h1.h1", { text: title }),
        el("div.empty", {}, [
          el("div.big", { text: "🚧" }),
          el("p", { text: note || "이 화면은 다음 단계에서 구현됩니다." }),
        ]),
      ])
    );
  };
}
