// character.js — 펫별 "고정" 캐릭터(강아지 마스코트).
//
// v3: 디멘셔널 픽셀 강아지로 교체. 실제 렌더는 dog/ 모듈이 담당하고 이 파일은
// 기존 공개 API(petCharacterEl / mountPetCharacter)를 유지하는 얇은 어댑터다.
//   - 외형(색·무늬·귀·다리·꼬리·장착)은 resolveAppearance(pet)가 결정
//     · pet.appearance_json 이 있으면 그것이 우선(커스터마이저 결과)
//     · 없으면 견종 + pet.id 해시로 유도 → 레거시 펫도 항상 같은 모습
//   - idle 모션(숨·꼬리·갸웃)은 dog/render.js가 주입하는 CSS(steps)로 처리.
// 호출부는 그대로(div.bp-char 래퍼 + 기존 .has-char 사이징 CSS 재사용).

import { resolveAppearance } from "./dog/params.js";
import { dogSVG, ensureDogStyles } from "./dog/render.js";

// 호환용: 일부 코드가 참조할 수 있는 외형 파라미터 추출기.
export function petVisualParams(pet) {
  return resolveAppearance(pet);
}

// el() 자식으로 바로 넣을 수 있는 캐릭터 노드.
// opts: { size=64, pose="front", anim=true }
export function petCharacterEl(pet, { size = 64, pose = "front", anim = true } = {}) {
  ensureDogStyles();
  const a = resolveAppearance(pet);
  const wrap = document.createElement("div");
  wrap.className = `bp-char lp-mood-${a.mood}`;
  wrap.style.width = `${size}px`;
  wrap.style.height = `${size}px`;
  wrap.setAttribute("role", "img");
  wrap.setAttribute("aria-label", `${pet?.name || "반려동물"} 캐릭터`);
  wrap.innerHTML = dogSVG(a, { pose, size, anim });
  return wrap;
}

// 기존 컨테이너(예: .pet-avatar)에 캐릭터를 채운다.
export function mountPetCharacter(container, pet, opts = {}) {
  if (!container) return null;
  container.innerHTML = "";
  const node = petCharacterEl(pet, opts);
  container.append(node);
  return node;
}
