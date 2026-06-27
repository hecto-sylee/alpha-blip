// dog/render.js — 픽셀 강아지 렌더러 (32 그리드, 각진 블록·하드 아웃라인·플랫 음영).
//
// "진짜 픽셀 느낌": 둥근 모서리 없음. 모든 파트는 1px 잉크 아웃라인 + 면, 음영은
// 그라데이션이 아니라 상단 1px 하이라이트 / 하단 1px 섀도(플랫 2톤). shape-rendering=crispEdges.
// 0625 LetsPaw sprites.js의 청키 픽셀 룩을 계승하되 견종 파라미터·멀티포즈·옷을 얹는다.
//
// dogSVG(appearance, {pose,size,anim}) → <svg> 문자열. 포즈 front/side/sit.

import { drawAccessories } from "./accessories.js";

// --- 색 유틸 ----------------------------------------------------------------
const _h2 = (h) => { h = String(h).replace("#", ""); if (h.length === 3) h = h.split("").map((c) => c + c).join(""); return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; };
const _c = (n) => Math.max(0, Math.min(255, Math.round(n)));
const _hex = (r, g, b) => "#" + [r, g, b].map((v) => _c(v).toString(16).padStart(2, "0")).join("");
export function lighten(hex, p) { const [r, g, b] = _h2(hex); return _hex(r + (255 - r) * p, g + (255 - g) * p, b + (255 - b) * p); }
export function darken(hex, p) { const [r, g, b] = _h2(hex); return _hex(r * (1 - p), g * (1 - p), b * (1 - p)); }

const INK = "#3A2E2A"; // 눈/코/얼굴 디테일
function line(c) { return darken(c, 0.5); }   // 파트 아웃라인(코트색 어둡게)
function hi(c) { return lighten(c, 0.32); }
function lo(c) { return darken(c, 0.2); }

// --- 픽셀 헬퍼 (전부 하드 사각) --------------------------------------------
const px = (x, y, w, h, fill, op) => (w <= 0 || h <= 0 ? "" : `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"${op != null ? ` opacity="${op}"` : ""}/>`);

// 1px 아웃라인 + 면 + 상단 하이라이트 1px + 하단 섀도 1px = 각진 입체 블록
function box(x, y, w, h, c, ink) {
  ink = ink || line(c);
  return (
    px(x, y, w, h, ink) +                  // 아웃라인(바깥 사각)
    px(x + 1, y + 1, w - 2, h - 2, c) +    // 면
    px(x + 1, y + 1, w - 2, 1, hi(c)) +    // 상단 하이라이트
    px(x + 1, y + h - 2, w - 2, 1, lo(c))  // 하단 섀도
  );
}

// --- 귀 --------------------------------------------------------------------
function ears(a, view) {
  const c = a.coat, k = line(c), inner = lighten(a.belly, 0.04);
  if (view === "side") {
    if (a.ears === "perky" || a.ears === "perkyBig") {
      const hh = a.ears === "perkyBig" ? 6 : 5;
      return px(8, 3 - hh, 4, hh, k) + px(9, 3 - hh + 1, 2, hh - 1, c);
    }
    return px(8, 3, 4, 6, k) + px(9, 4, 2, 4, c) + px(9, 8, 2, 1, inner);
  }
  if (a.ears === "perky" || a.ears === "perkyBig") {
    const hh = a.ears === "perkyBig" ? 7 : 5, top = 3 - hh;
    const e = (x) => px(x, top, 4, hh, k) + px(x + 1, top + 1, 2, hh - 2, c) + px(x + 1, top + 1, 2, 1, hi(c));
    return e(7) + e(21);
  }
  if (a.ears === "folded") {
    const e = (x) => px(x, 2, 5, 4, k) + px(x + 1, 3, 3, 2, c);
    return e(5) + e(22);
  }
  // floppy: 옆으로 늘어진 큰 귀
  const e = (x) => px(x, 4, 5, 11, k) + px(x + 1, 5, 3, 9, c) + px(x + 1, 5, 3, 1, hi(c)) + px(x + 1, 13, 3, 1, inner);
  return e(4) + e(23);
}

// --- 꼬리 ------------------------------------------------------------------
function tailMarkup(a, view) {
  const c = a.coat, k = line(c);
  const ax = view === "side" ? 24 : 23, ay = 17;
  const blk = (x, y, w, h) => px(x, y, w, h, k) + px(x + 1, y + 1, w - 1, h - 1, c);
  let body;
  switch (a.tail) {
    case "plume": body = blk(ax, ay - 4, 4, 8) + blk(ax + 1, ay - 6, 3, 4); break;
    case "pom": body = blk(ax, ay - 2, 5, 5); break;
    case "curl": body = blk(ax, ay - 1, 3, 5) + blk(ax + 1, ay - 4, 4, 3) + blk(ax + 4, ay - 1, 3, 4); break;
    case "short": body = blk(ax, ay + 1, 4, 4); break;
    case "long": body = blk(ax, ay + 2, 7, 3) + blk(ax + 5, ay - 1, 3, 4); break;
    case "thin": body = px(ax, ay, 2, 8, k) + px(ax + 1, ay - 3, 2, 4, c); break;
    default: body = blk(ax, ay - 1, 4, 5);
  }
  return `<g class="lp-tail">${body}</g>`;
}

// --- 다리 ------------------------------------------------------------------
const LEG_LEN = { long: 6, normal: 5, short: 4, tiny: 3 };
function bodyBottom(a) { return a.body === "round" ? 26 : 25; }
function legs(a, view) {
  const c = a.coat, k = line(c);
  const socks = a.pattern === "socks";
  const paw = socks ? (a.patternColor || a.belly) : lighten(a.belly, 0.02);
  const len = LEG_LEN[a.legs] || 5, top = bodyBottom(a) - 1, ground = top + len;
  const sockH = socks ? Math.min(2, len - 1) : 1;
  const one = (x) => px(x, top, 4, len, k) + px(x + 1, top, 2, len - 1, c) + px(x + 1, ground - sockH, 2, sockH, paw);
  if (view === "side") return `<g class="lp-legB">${one(9)}${one(18)}</g><g class="lp-legA">${one(12)}${one(21)}</g>`;
  return `<g class="lp-legA">${one(10)}${one(18)}</g>`;
}

// --- 얼굴 ------------------------------------------------------------------
function face(a, view) {
  const m = a.belly;
  if (view === "side") {
    const long = a.snout === "long", short = a.snout === "short";
    const mw = long ? 5 : short ? 3 : 4;
    return px(2 - (long ? 1 : 0), 11, mw, 4, line(m)) + px(3 - (long ? 1 : 0), 12, mw - 1, 2, m) +
      px(1, 12, 2, 2, INK) + px(6, 8, 2, 2, INK) + px(6, 8, 1, 1, "#fff") +
      (a.tongue ? px(2, 15, 2, 1, "#FF7FA8") : "");
  }
  const eyeY = 7;
  const eye = (x) => px(x, eyeY, 2, 2, INK) + px(x, eyeY, 1, 1, "#fff");
  let muzzle;
  if (a.snout === "long") muzzle = px(14, 9, 4, 6, line(a.coat)) + px(15, 10, 2, 4, m) + px(14, 11, 4, 2, m) + px(15, 11, 2, 2, INK);
  else if (a.snout === "short") muzzle = px(11, 11, 10, 5, line(m)) + px(12, 12, 8, 3, m) + px(14, 11, 4, 2, INK);
  else muzzle = px(12, 10, 8, 5, line(m)) + px(13, 11, 6, 3, m) + px(14, 10, 4, 2, INK);
  return muzzle + eye(11) + eye(19) + (a.tongue ? px(15, 14, 2, 2, "#FF7FA8") : "");
}

// --- 무늬 ------------------------------------------------------------------
function pattern(a, where) {
  if (!a.pattern || a.pattern === "solid" || a.pattern === "socks") return "";
  const pc = a.patternColor || a.belly, o = 0.95;
  if (where === "headFront") {
    if (a.pattern === "patch") return px(8, 3, 6, 5, pc, o);
    if (a.pattern === "spots") return px(9, 5, 1, 1, pc) + px(21, 6, 1, 1, pc);
    return "";
  }
  if (where === "bodyFront") {
    if (a.pattern === "saddle") return px(10, 16, 12, 3, pc, o);
    if (a.pattern === "patch") return px(10, 18, 4, 4, pc, o) + px(18, 17, 4, 4, pc, o);
    if (a.pattern === "spots") return px(11, 19, 1, 1, pc) + px(16, 21, 1, 1, pc) + px(20, 18, 1, 1, pc);
    return "";
  }
  if (where === "bodySide") {
    if (a.pattern === "saddle") return px(8, 13, 12, 4, pc, o);
    if (a.pattern === "patch") return px(14, 13, 6, 4, pc, o);
    if (a.pattern === "spots") return px(10, 15, 1, 1, pc) + px(15, 14, 1, 1, pc);
  }
  return "";
}

function contactShadow(a) { const g = bodyBottom(a) - 1 + (LEG_LEN[a.legs] || 5); return px(8, g, 16, 1, "rgba(58,46,42,.22)") + px(11, g + 1, 10, 1, "rgba(58,46,42,.12)"); }

// --- 포즈: 정면 -------------------------------------------------------------
function poseFront(a) {
  const round = a.body === "round";
  const bx = 9, by = 15, bw = 14, bh = round ? 11 : 10;
  const belly = px(bx + 3, by + 3, bw - 6, bh - 5, lighten(a.belly, 0.05));
  const head = `<g class="lp-head">${ears(a, "front")}${box(7, 2, 18, 14, a.coat)}${pattern(a, "headFront")}${face(a, "front")}${drawAccessories(a, "front", "head")}${drawAccessories(a, "front", "face")}</g>`;
  return (
    contactShadow(a) + tailMarkup(a, "front") + legs(a, "front") +
    `<g class="lp-body">${box(bx, by, bw, bh, a.coat)}${belly}${pattern(a, "bodyFront")}${drawAccessories(a, "front", "body")}</g>` +
    head
  );
}

// --- 포즈: 측면 -------------------------------------------------------------
function poseSide(a) {
  const round = a.body === "round";
  const longB = a.body === "long" || a.body === "xlong";
  const bx = 6, by = round ? 13 : 14, bw = longB ? (a.body === "xlong" ? 22 : 18) : 15, bh = round ? 9 : 8;
  const head = `<g class="lp-head">${ears(a, "side")}${box(1, 3, 11, 11, a.coat)}${face(a, "side")}${drawAccessories(a, "side", "head")}</g>`;
  return (
    contactShadow(a) + tailMarkup(a, "side") + legs(a, "side") +
    `<g class="lp-body">${box(bx, by, bw, bh, a.coat)}${pattern(a, "bodySide")}${drawAccessories(a, "side", "body")}</g>` +
    head
  );
}

// --- 포즈: 앉기 -------------------------------------------------------------
function poseSit(a) {
  const c = a.coat, k = line(c), paw = lighten(a.belly, 0.02);
  const frontLeg = (x) => px(x, 22, 4, 7, k) + px(x + 1, 22, 2, 6, c) + px(x + 1, 28, 2, 1, paw);
  return (
    px(8, 29, 16, 1, "rgba(58,46,42,.22)") + tailMarkup(a, "front") +
    `<g class="lp-body">${box(8, 14, 16, 12, c)}${px(12, 17, 8, 6, lighten(a.belly, 0.05))}${pattern(a, "bodyFront")}${frontLeg(11)}${frontLeg(17)}${drawAccessories(a, "front", "body")}</g>` +
    `<g class="lp-head">${ears(a, "front")}${box(7, 2, 18, 14, c)}${pattern(a, "headFront")}${face(a, "front")}${drawAccessories(a, "front", "head")}${drawAccessories(a, "front", "face")}</g>`
  );
}

const POSES = { front: poseFront, side: poseSide, sit: poseSit };

export function dogSVG(appearance, { pose = "front", size = 64, anim = true } = {}) {
  const a = appearance || {};
  const build = POSES[pose] || poseFront;
  const cls = `lp-dog lp-pose-${pose} lp-mood-${a.mood || "normal"}${anim ? " lp-anim" : ""}`;
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" class="${cls}" viewBox="0 0 32 32" width="${size}" height="${size}" ` +
    `shape-rendering="crispEdges" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${(a.breed || "강아지")} 픽셀 강아지">` +
    `<g class="lp-root">${build(a)}</g></svg>`
  );
}

// --- 애니메이션 CSS 1회 주입 ------------------------------------------------
let _injected = false;
export function ensureDogStyles() {
  if (_injected || typeof document === "undefined") return;
  _injected = true;
  const css = `
.lp-dog{display:block;width:100%;height:100%;overflow:visible;image-rendering:pixelated;}
.lp-root,.lp-head,.lp-tail,.lp-legA,.lp-legB,.lp-body{transform-box:fill-box;}
@keyframes lp-breathe{0%,100%{transform:translateY(0)}50%{transform:translateY(-0.6px)}}
.lp-anim .lp-root{animation:lp-breathe 2.6s steps(2,end) infinite;}
@keyframes lp-wag{0%{transform:rotate(-20deg)}100%{transform:rotate(20deg)}}
.lp-anim .lp-tail{transform-origin:10% 80%;animation:lp-wag .5s steps(2,end) infinite alternate;}
@keyframes lp-tilt{0%,40%{transform:rotate(0)}52%,68%{transform:rotate(-8deg)}80%,100%{transform:rotate(0)}}
.lp-anim.lp-pose-front .lp-head{transform-origin:50% 95%;animation:lp-tilt 4.6s steps(5,end) infinite;}
@keyframes lp-stepA{0%,100%{transform:translateY(0)}50%{transform:translateY(-1.5px)}}
@keyframes lp-stepB{0%,100%{transform:translateY(-1.5px)}50%{transform:translateY(0)}}
.lp-anim.lp-pose-side .lp-legA{animation:lp-stepA .4s steps(2,end) infinite;}
.lp-anim.lp-pose-side .lp-legB{animation:lp-stepB .4s steps(2,end) infinite;}
.lp-anim.lp-pose-side .lp-root{animation:lp-breathe .4s steps(2,end) infinite;}
.lp-mood-bouncy .lp-tail{animation-duration:.32s !important;}
.lp-mood-gentle .lp-tail{animation-duration:.8s !important;}
@media (prefers-reduced-motion: reduce){ .lp-dog *{animation:none !important;} }`;
  const style = document.createElement("style");
  style.id = "lp-dog-styles";
  style.textContent = css;
  document.head.appendChild(style);
}
