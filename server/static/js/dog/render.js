// dog/render.js — 강아지 렌더러 v4 (손으로 찍은 픽셀 스프라이트).
//
// v3까지의 절차생성(rect 조합)은 귀여움에 한계가 있어, 디자인 앱에서 한 땀씩 찍은
// 512×512 투명 PNG 스프라이트로 교체했다. 규격: docs/dog_asset_spec.md
//   · 강아지: /static/img/dogs/dog_{breed}_{pose}.png
//   · 악세 : /static/img/dogs/acc/acc_{key}.png  (정면 캔버스에 얹힌 위치 그대로)
// 외형(색/무늬/귀/다리/꼬리)은 스프라이트에 구워져 있으므로 breed가 룩을 결정하고,
// 장착 악세(equipped)만 레이어로 겹친다. 공개 API(dogSVG/ensureDogStyles)는 유지.

import { BREED_KEYS } from "./params.js";

const ASSET = "/static/img/dogs";

// side/sit 스프라이트가 있는 견종(나머지는 front로 폴백). docs 스펙 Tier1~2.
const POSE_FULL = new Set(["maltese", "shiba", "corgi", "golden", "poodle", "bichon", "dachshund", "mix"]);
// 악세 키(파일 acc_{key}.png 와 1:1). accessories.js 카탈로그와 동일.
const ACC_KEYS = new Set(["party_hat", "cap", "crown", "glasses", "sunglasses", "bandana", "bowtie", "scarf", "cape"]);

// --- 색 유틸(호환용 export — 일부 모듈이 참조할 수 있음) ----------------------
const _h2 = (h) => { h = String(h).replace("#", ""); if (h.length === 3) h = h.split("").map((c) => c + c).join(""); return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; };
const _c = (n) => Math.max(0, Math.min(255, Math.round(n)));
const _hex = (r, g, b) => "#" + [r, g, b].map((v) => _c(v).toString(16).padStart(2, "0")).join("");
export function lighten(hex, p) { const [r, g, b] = _h2(hex); return _hex(r + (255 - r) * p, g + (255 - g) * p, b + (255 - b) * p); }
export function darken(hex, p) { const [r, g, b] = _h2(hex); return _hex(r * (1 - p), g * (1 - p), b * (1 - p)); }

// --- 파일 매핑 --------------------------------------------------------------
function dogFile(breed, pose) {
  const b = BREED_KEYS.includes(breed) ? breed : "mix";
  const p = (pose === "side" || pose === "sit") && !POSE_FULL.has(b) ? "front" : (pose || "front");
  return `${ASSET}/dog_${b}_${p}.png`;
}

// 외형 → 레이어 URL 목록(베이스 강아지 + 장착 악세). 악세는 정면 캔버스 기준이라 front에만.
export function dogLayers(appearance, pose = "front") {
  const a = appearance || {};
  const layers = [dogFile(a.breed, pose)];
  if (pose === "front") {
    const eq = Array.isArray(a.equipped) ? a.equipped : [];
    for (const k of eq) if (ACC_KEYS.has(k)) layers.push(`${ASSET}/acc/acc_${k}.png`);
  }
  return layers;
}

const _esc = (s) => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

// 강아지 1마리 = 512 viewBox SVG에 스프라이트 <image> 레이어들. innerHTML로 삽입해 쓴다.
export function dogSVG(appearance, { pose = "front", size = 64, anim = true } = {}) {
  const a = appearance || {};
  const cls = `lp-dog lp-pose-${pose} lp-mood-${a.mood || "normal"}${anim ? " lp-anim" : ""}`;
  const layers = dogLayers(a, pose)
    .map((href, i) => `<image href="${_esc(href)}" x="0" y="0" width="512" height="512" preserveAspectRatio="xMidYMid meet" class="${i ? "lp-acc" : "lp-base"}"/>`)
    .join("");
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" class="${cls}" viewBox="0 0 512 512" width="${size}" height="${size}" ` +
    `preserveAspectRatio="xMidYMid meet" role="img" aria-label="${_esc(a.breed || "강아지")} 강아지">${layers}</svg>`
  );
}

// --- idle 모션 CSS 1회 주입 -------------------------------------------------
let _injected = false;
export function ensureDogStyles() {
  if (_injected || typeof document === "undefined") return;
  _injected = true;
  const css = `
.lp-dog{display:block;width:100%;height:100%;overflow:visible;}
.lp-dog image{image-rendering:pixelated;image-rendering:crisp-edges;}
@keyframes lp-bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-2.5%)}}
.lp-dog.lp-anim{transform-origin:50% 92%;animation:lp-bob 3s ease-in-out infinite;will-change:transform;}
.lp-dog.lp-mood-bouncy.lp-anim{animation-duration:1.9s;}
.lp-dog.lp-mood-gentle.lp-anim{animation-duration:4.2s;}
@media (prefers-reduced-motion: reduce){ .lp-dog.lp-anim{animation:none;} }`;
  const style = document.createElement("style");
  style.id = "lp-dog-styles";
  style.textContent = css;
  document.head.appendChild(style);
}
