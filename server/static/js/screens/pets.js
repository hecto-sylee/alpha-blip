// screens/pets.js — 반려동물 리스트. 펫마다 고정 캐릭터를 보여주고, 탭하면 수정.
import { api } from "../api.js";
import { el, mount, toast, setTab, loading } from "../ui.js";
import { navigate } from "../router.js";
import { petCharacterEl } from "../character.js";

const SIZE_LABEL = { small: "소형", medium: "중형", large: "대형" };

export async function petsScreen() {
  setTab("my");
  loading();

  let pets = [];
  try {
    pets = (await api.get("/pets")).pets || [];
  } catch (e) {
    toast(e.message || "불러오기 실패", "err");
  }

  const addBtn = el("button.btn.secondary.pets-add", {
    text: "＋ 반려동물 추가",
    onclick: () => navigate("/onboard-pet"),
  });

  const body = pets.length
    ? el("div.stack", {}, pets.map(petRow))
    : el("div.card", {}, [
        el("p", { text: "아직 등록한 반려동물이 없어요." }),
        el("button.btn", { text: "등록하기", onclick: () => navigate("/onboard-pet") }),
      ]);

  mount(
    el("div.stack", {}, [
      el("button.btn.ghost", { text: "← 마이", onclick: () => navigate("/my") }),
      el("h1.h1", { text: "반려동물" }),
      body,
      pets.length ? addBtn : null,
      el("div", { style: "height:8px" }),
    ])
  );
}

function petRow(pet) {
  const tags = (pet.personality_tags || []).slice(0, 3);
  const chips = [
    pet.size ? el("span.mini-chip", { text: SIZE_LABEL[pet.size] || pet.size }) : null,
    ...tags.map((t) => el("span.mini-chip.soft", { text: t })),
  ].filter(Boolean);

  return el(
    "div.card.tappable.pet-row",
    { onclick: () => navigate(`/pet/${pet.id}`) },
    [
      el("div.pet-row-char", {}, [petCharacterEl(pet, { size: 60 })]),
      el("div.pet-row-info", {}, [
        el("div.pet-row-name", { text: pet.name }),
        el("div.sub", { text: pet.breed || "견종 미입력" }),
        chips.length ? el("div.pet-row-tags", {}, chips) : null,
      ]),
      el("span.chev", { text: "›" }),
    ]
  );
}
