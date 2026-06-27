// dog/customizer.js — 강아지 커스터마이저 UI.
//
// 라이브 프리뷰 + 견종 갤러리(토글) + 커마 패널(색/배색/무늬/귀/다리/꼬리/주둥이).
// 온보딩(pet.js)과 프로필 편집에서 공유. 변경 시 onChange(appearance)로 통보.
//
// buildCustomizer(initial, { onChange, onBreedPick }) → { el, getAppearance }

import { el } from "../ui.js";
import { dogSVG, ensureDogStyles } from "./render.js";
import {
  BREEDS, BREED_KEYS, EARS, TAILS, LEGS, SNOUTS, PATTERNS,
  COAT_SWATCHES, PATTERN_SWATCHES, appearanceForBreed,
} from "./params.js";

const L_EARS = { floppy: "접힌귀", perky: "쫑긋", perkyBig: "큰쫑긋", folded: "폴드" };
const L_TAILS = { curl: "말린", plume: "풍성", pom: "방울", short: "짧은", long: "긴", thin: "얇은" };
const L_LEGS = { long: "긴 다리", normal: "보통", short: "짧은", tiny: "아주 짧은" };
const L_PAT = { solid: "단색", patch: "얼룩", spots: "점박이", saddle: "등무늬", socks: "양말발" };
const L_SNOUT = { short: "납작코", med: "보통", long: "길쭉코" };
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
    c.addEventListener("click", () => { pose = v; poseRow.querySelectorAll(".cz-chip").forEach(n => n.classList.toggle("on", n.textContent === lab)); emit(); });
    poseRow.append(c);
  });

  // --- 컨트롤 빌더들 ---
  function optionField(title, options, key) {
    const chips = el("div.cz-chips");
    const paint = () => {
      chips.innerHTML = "";
      options.forEach(([v, lab]) => {
        const c = el("span.cz-chip" + (v === app[key] ? ".on" : ""), { text: lab });
        c.addEventListener("click", () => { app[key] = v; paint(); emit(); });
        chips.append(c);
      });
    };
    paint();
    return el("div.cz-field", {}, [el("div.cz-label", { text: title }), chips]);
  }

  function colorField(title, swatches, key) {
    const swWrap = el("div.cz-chips");
    const free = el("input.cz-color", { type: "color" });
    const paint = () => {
      swWrap.innerHTML = "";
      swatches.forEach((co) => {
        const s = el("span.cz-sw" + (co.toLowerCase() === String(app[key]).toLowerCase() ? ".on" : ""), {});
        s.style.background = co; s.title = co;
        s.addEventListener("click", () => { app[key] = co; free.value = co; paint(); emit(); });
        swWrap.append(s);
      });
    };
    free.value = /^#[0-9a-f]{6}$/i.test(app[key] || "") ? app[key] : "#ffffff";
    free.addEventListener("input", () => { app[key] = free.value; paint(); emit(); });
    paint();
    return el("div.cz-field", {}, [el("div.cz-label", { text: title }), el("div.cz-row", {}, [swWrap, free])]);
  }

  // 커마 패널(접힘) — 컨트롤은 app 기준으로 다시 그릴 수 있게 host에 모음
  const panelHost = el("div.cz-controls");
  function rebuildControls() {
    panelHost.innerHTML = "";
    panelHost.append(
      colorField("털색", COAT_SWATCHES, "coat"),
      colorField("배색(배·얼굴)", COAT_SWATCHES.concat(PATTERN_SWATCHES), "belly"),
      optionField("무늬", PATTERNS.map((p) => [p, L_PAT[p]]), "pattern"),
      colorField("무늬색", PATTERN_SWATCHES, "patternColor"),
      optionField("귀", EARS.map((e) => [e, L_EARS[e]]), "ears"),
      optionField("다리", LEGS.map((l) => [l, L_LEGS[l]]), "legs"),
      optionField("꼬리", TAILS.map((t) => [t, L_TAILS[t]]), "tail"),
      optionField("주둥이", SNOUTS.map((s) => [s, L_SNOUT[s]]), "snout"),
    );
  }
  rebuildControls();

  // 견종 갤러리(토글)
  const gallery = el("div.cz-gallery.hidden");
  function paintGallery() {
    gallery.querySelectorAll(".cz-breed").forEach((b) => b.classList.toggle("on", b.dataset.k === app.breed));
  }
  BREED_KEYS.forEach((k) => {
    const cell = el("button.cz-breed" + (k === app.breed ? ".on" : ""), { type: "button", dataset: { k } });
    cell.innerHTML = dogSVG(appearanceForBreed(k), { pose: "front", size: 50, anim: false });
    cell.append(el("small", { text: BREEDS[k].ko }));
    cell.addEventListener("click", () => {
      Object.assign(app, appearanceForBreed(k));
      rebuildControls(); paintGallery(); emit();
      onBreedPick && onBreedPick(k, BREEDS[k].ko);
    });
    gallery.append(cell);
  });

  const galleryToggle = el("button.cz-toggle", { type: "button", text: "견종 고르기  ▾" });
  galleryToggle.addEventListener("click", () => {
    gallery.classList.toggle("hidden");
    galleryToggle.textContent = gallery.classList.contains("hidden") ? "견종 고르기  ▾" : "견종 접기  ▴";
  });

  const panelToggle = el("button.cz-toggle", { type: "button", text: "커스터마이징  ▾" });
  panelToggle.addEventListener("click", () => {
    panelHost.classList.toggle("hidden");
    panelToggle.textContent = panelHost.classList.contains("hidden") ? "커스터마이징  ▾" : "커스터마이징 접기  ▴";
  });
  panelHost.classList.add("hidden"); // 기본 접힘(요청: 숨겨뒀다가 펼침)

  const root = el("div.cz-root", {}, [
    el("div.cz-stage", {}, [preview, poseRow]),
    galleryToggle, gallery,
    panelToggle, panelHost,
  ]);

  emit();
  return {
    el: root,
    getAppearance: () => ({ ...app }),
    // 견종 텍스트 입력과 동기화: 그 견종 기본 외형으로 맞춤(프리뷰가 입력을 따라감).
    applyBreed: (key) => { Object.assign(app, appearanceForBreed(key)); rebuildControls(); paintGallery(); emit(); },
  };
}
