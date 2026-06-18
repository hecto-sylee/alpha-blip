// screens/pet.js — SCR-02 반려동물 등록 / SCR-31 수정 (F-02)
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab } from "../ui.js";
import { navigate } from "../router.js";

const SIZES = [["small", "소형"], ["medium", "중형"], ["large", "대형"]];
const GENDERS = [["male", "남아"], ["female", "여아"]];
const TAGS = ["활발함", "온순함", "겁많음", "사람좋아", "강아지좋아", "호기심", "장난꾸러기", "차분함"];
const STYLES = [["slow", "느긋"], ["normal", "보통"], ["fast", "빠름"]];

export async function petScreen(params = {}) {
  const editId = params.id || null;
  setTab(editId ? "my" : null);

  let pet = null;
  if (editId) {
    try { pet = await api.get(`/pets/${editId}`); }
    catch (e) { toast(e.message, "err"); }
  }

  const state = {
    name: pet?.name || "",
    breed: pet?.breed || "",
    size: pet?.size || "",
    gender: pet?.gender || "",
    age_months: pet?.age_months ?? "",
    walk_style: pet?.walk_style || "normal",
    is_neutered: pet?.is_neutered ?? false,
    tags: new Set(pet?.personality_tags || []),
    caution_notes: pet?.caution_notes || "",
  };

  const cta = el("button.cta", { id: "pet-cta", text: editId ? "저장" : "등록하고 시작하기" });

  const validate = () => {
    // 필수: 이름·견종·크기·성격태그 최소 1
    const ok = state.name.trim() && state.breed.trim() && state.size && state.tags.size >= 1;
    cta.disabled = !ok;
    return ok;
  };

  const nameI = el("input.input", { id: "pet-name", value: state.name, placeholder: "이름" });
  nameI.addEventListener("input", () => { state.name = nameI.value; validate(); });

  const breedI = el("input.input", { id: "pet-breed", value: state.breed, placeholder: "예: 푸들" });
  breedI.addEventListener("input", () => { state.breed = breedI.value; validate(); });

  const ageI = el("input.input", { id: "pet-age", type: "number", min: "0", value: state.age_months, placeholder: "개월 수" });
  ageI.addEventListener("input", () => { state.age_months = ageI.value; });

  const sizeSeg = seg("pet-size", SIZES, state.size, (v) => { state.size = v; validate(); });
  const genderSeg = seg("pet-gender", GENDERS, state.gender, (v) => { state.gender = v; });
  const styleSeg = seg("pet-style", STYLES, state.walk_style, (v) => { state.walk_style = v; });

  const tagsWrap = el("div.tags", { id: "pet-tags" },
    TAGS.map((t) => {
      const node = el("span.tag" + (state.tags.has(t) ? ".sel" : ""), { text: t });
      node.addEventListener("click", () => {
        if (state.tags.has(t)) { state.tags.delete(t); node.classList.remove("sel"); }
        else { state.tags.add(t); node.classList.add("sel"); }
        validate();
      });
      return node;
    })
  );

  const neuter = el("label.row", { style: "cursor:pointer" }, [
    (() => {
      const c = el("input", { type: "checkbox", id: "pet-neuter" });
      c.checked = !!state.is_neutered;
      c.addEventListener("change", () => (state.is_neutered = c.checked));
      return c;
    })(),
    el("span", { text: "중성화 완료" }),
  ]);

  const notesI = el("textarea.input", { id: "pet-notes", placeholder: "주의사항 (선택)", html: "" });
  notesI.value = state.caution_notes;
  notesI.addEventListener("input", () => (state.caution_notes = notesI.value));

  cta.addEventListener("click", async () => {
    if (!validate()) return;
    cta.disabled = true; cta.textContent = "저장 중…";
    const payload = {
      name: state.name.trim(),
      breed: state.breed.trim(),
      size: state.size,
      gender: state.gender || null,
      age_months: state.age_months === "" ? null : Number(state.age_months),
      walk_style: state.walk_style,
      is_neutered: state.is_neutered,
      personality_tags: [...state.tags],
      caution_notes: state.caution_notes.trim() || null,
    };
    try {
      if (editId) {
        await api.patch(`/pets/${editId}`, payload);
        toast("저장했어요", "ok");
        navigate("/my");
      } else {
        const res = await api.post("/pets", payload);
        store.setPetId(res.pet_id);
        toast("등록 완료! 🐾", "ok");
        navigate("/home");
      }
    } catch (e) {
      toast(e.message || "저장 실패", "err");
      cta.disabled = false; cta.textContent = editId ? "저장" : "등록하고 시작하기";
    }
  });

  mount(
    el("div.stack", {}, [
      el("h1.h1", { text: editId ? "프로필 수정" : "우리 강아지 소개" }),
      el("p.sub", { text: "이름 · 견종 · 크기 · 성격은 꼭 필요해요." }),
      field("이름", true, nameI),
      field("견종", true, breedI),
      field("크기", true, sizeSeg),
      field("성격 (1개 이상)", true, tagsWrap),
      field("성별", false, genderSeg),
      field("나이", false, ageI),
      field("산책 스타일", false, styleSeg),
      el("div.card", {}, [neuter]),
      field("주의사항", false, notesI),
      cta,
      el("div", { style: "height:8px" }),
    ])
  );

  validate();
}

function field(label, required, control) {
  return el("div.field", {}, [
    el("label", { html: `${label}${required ? " <span class='req'>*</span>" : ""}` }),
    control,
  ]);
}

function seg(id, opts, selected, onPick) {
  const wrap = el("div.seg", { id });
  opts.forEach(([val, label]) => {
    const o = el("div.opt" + (val === selected ? ".sel" : ""), { text: label, dataset: { val } });
    o.addEventListener("click", () => {
      wrap.querySelectorAll(".opt").forEach((n) => n.classList.remove("sel"));
      o.classList.add("sel");
      onPick(val);
    });
    wrap.append(o);
  });
  return wrap;
}
