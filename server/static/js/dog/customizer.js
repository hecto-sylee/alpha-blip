// dog/customizer.js — 강아지 커스터마이저 UI.
//
// v4: 외형이 견종 스프라이트로 구워져 있어, 미세 토글(색/귀/다리/꼬리/무늬)은
// 더 이상 룩을 바꾸지 못한다. 그래서 "견종 갤러리 + 포즈"로 단순화했다.
// 악세 꾸미기는 상점(shop.js)에서 포인트로 장착한다.
// 온보딩(pet.js)·프로필 편집에서 공유. 변경 시 onChange(appearance)로 통보.
//
// buildCustomizer(initial, { onChange, onBreedPick }) → { el, getAppearance, applyBreed }

import { el } from "../ui.js";
import { dogSVG, ensureDogStyles } from "./render.js";
import { BREEDS, BREED_KEYS, appearanceForBreed } from "./params.js";

const POSES = [["front", "정면"], ["side", "걷기"], ["sit", "앉기"]];

export function buildCustomizer(initial, { onChange, onBreedPick } = {}) {
  ensureDogStyles();
  const app = { ...appearanceForBreed("mix"), ...(initial || {}) };
  let pose = "front";

  const preview = el("div.cz-preview");
  const emit = () => {
    preview.innerHTML = dogSVG(app, { pose, size: 140, anim: true });
    onChange && onChange({ ...app });
  };

  // 포즈 토글(멀티포즈 자랑)
  const poseRow = el("div.cz-chips.cz-pose");
  POSES.forEach(([v, lab]) => {
    const c = el("span.cz-chip" + (v === pose ? ".on" : ""), { text: lab });
    c.addEventListener("click", () => {
      pose = v;
      poseRow.querySelectorAll(".cz-chip").forEach((n) => n.classList.toggle("on", n.textContent === lab));
      emit();
    });
    poseRow.append(c);
  });

  // 견종 갤러리(상시 표시 — 이제 메인 컨트롤)
  const gallery = el("div.cz-gallery");
  function paintGallery() {
    gallery.querySelectorAll(".cz-breed").forEach((b) => b.classList.toggle("on", b.dataset.k === app.breed));
  }
  BREED_KEYS.forEach((k) => {
    const cell = el("button.cz-breed" + (k === app.breed ? ".on" : ""), { type: "button", dataset: { k } });
    cell.innerHTML = dogSVG(appearanceForBreed(k), { pose: "front", size: 50, anim: false });
    cell.append(el("small", { text: BREEDS[k].ko }));
    cell.addEventListener("click", () => {
      // 견종만 교체하고 장착 악세(equipped)는 유지
      const eq = app.equipped;
      Object.assign(app, appearanceForBreed(k));
      if (eq) app.equipped = eq;
      paintGallery();
      emit();
      onBreedPick && onBreedPick(k, BREEDS[k].ko);
    });
    gallery.append(cell);
  });

  const root = el("div.cz-root", {}, [
    el("div.cz-stage", {}, [preview, poseRow]),
    el("div.cz-label", { text: "견종 고르기" }),
    gallery,
    el("p.cz-hint", { text: "꾸미기 아이템은 상점에서 포인트로 장착할 수 있어요 🦴" }),
  ]);

  emit();
  return {
    el: root,
    getAppearance: () => ({ ...app }),
    // 견종 텍스트 입력과 동기화: 그 견종 기본 외형으로 맞춤(프리뷰가 입력을 따라감).
    applyBreed: (key) => {
      const eq = app.equipped;
      Object.assign(app, appearanceForBreed(key));
      if (eq) app.equipped = eq;
      paintGallery();
      emit();
    },
  };
}
