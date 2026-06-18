// screens/quest.js — SCR-27 오늘의 퀘스트 (F-12). M3 Expressive.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, loading, staggerMotion } from "../ui.js";
import { navigate } from "../router.js";

function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export async function questScreen() {
  setTab("walk");
  loading();
  let data;
  try {
    data = await api.get("/quests/candidates?scope=user");
  } catch (e) {
    toast(e.message || "퀘스트를 불러오지 못했어요", "err");
    navigate("/home");
    return;
  }

  if (data.locked && data.candidates.length) {
    return renderLocked(data.candidates[0]);
  }
  renderPicker(data.candidates || []);
}

function renderPicker(candidates) {
  let selected = null;
  const cta = el("button.cta", { id: "quest-confirm", text: "이 퀘스트로 시작", disabled: true });

  const cards = candidates.map((q) => {
    const card = el("div.quest-card", { dataset: { qt: q.quest_template_id } }, [
      el("div.q-title", { text: q.title }),
      el("div.q-desc", { text: q.description || "" }),
      el("div.row", { style: "flex-wrap:wrap;gap:6px;margin-top:10px" },
        (q.missions || []).map((m) => el("span.chip", { text: m.title }))),
    ]);
    card.addEventListener("click", () => {
      selected = q;
      document.querySelectorAll(".quest-card").forEach((c) => c.classList.remove("sel"));
      card.classList.add("sel");
      cta.disabled = false;
    });
    return card;
  });

  cta.addEventListener("click", async () => {
    if (!selected) return;
    cta.disabled = true; cta.textContent = "선택 중…";
    try {
      await api.post("/quests/select", {
        scope: "user",
        scope_id: store.userId,
        quest_template_id: selected.quest_template_id,
        quest_date: todayStr(),
      });
      toast("오늘의 퀘스트를 정했어요 🎯", "ok");
      renderLocked(selected);
    } catch (e) {
      toast(e.message || "선택에 실패했어요", "err");
      cta.disabled = false; cta.textContent = "이 퀘스트로 시작";
    }
  });

  mount(
    el("div.stack", {}, [
      el("h1.h1", { text: "오늘의 퀘스트" }),
      el("p.sub", { text: "오늘 산책에서 담아볼 주제를 하나 골라요. (하루 1개)" }),
      ...(cards.length ? cards : [el("div.empty", {}, [el("div.big", { text: "🎯" }), el("p", { text: "후보 퀘스트가 없어요" })])]),
      el("div", { style: "height:4px" }),
      cta,
    ])
  );
  requestAnimationFrame(() => staggerMotion(cards, { y: 16, each: 0.055 }));
}

function renderLocked(quest) {
  setTab("walk");
  const missions = (quest.missions || []).map((m) =>
    el("div.mission-row", { dataset: { mid: m.id } }, [
      el("div.ord", { text: String(m.order) }),
      el("div", {}, [
        el("div.m-title", { text: m.title }),
        m.hint && el("div.m-hint", { text: m.hint }),
      ]),
    ])
  );

  const cta = el("button.cta", { id: "go-record", text: "📸 기록하기" });
  cta.addEventListener("click", () => navigate("/record"));

  mount(
    el("div.stack", { id: "quest-locked" }, [
      el("div.badge", { text: "🔒 오늘의 퀘스트 (변경 불가)" }),
      el("h1.h1", { text: quest.title }),
      el("p.sub", { text: quest.description || "" }),
      el("div.h2", { text: "지금 찍어볼 순간" }),
      ...missions,
      el("div", { style: "height:4px" }),
      cta,
    ])
  );
}
