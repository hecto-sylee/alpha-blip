// ui.js — DOM 헬퍼 · 토스트 · 바텀시트 · 스프링 전환 · 햅틱 · reduced-motion
import { petCharacterEl } from "./character.js";

export const reducedMotion = () =>
  window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const MOTION_TIMEOUT_MS = 1200;
let motionPromise = null;

function reveal(els, transform = "none") {
  const list = els instanceof Element ? [els] : Array.from(els || []);
  list.forEach((node) => {
    if (!node) return;
    node.style.opacity = "1";
    if (transform != null) node.style.transform = transform;
  });
}

function motionTimeout(ms = MOTION_TIMEOUT_MS) {
  return new Promise((resolve) => setTimeout(() => resolve(null), ms));
}

export function loadMotion() {
  if (!motionPromise) {
    motionPromise = import("./motion.js").catch(() => null);
  }
  return motionPromise;
}

export async function motionReady() {
  return Boolean(await loadMotion());
}

async function motionWithin(ms = MOTION_TIMEOUT_MS) {
  return Promise.race([loadMotion(), motionTimeout(ms)]);
}

export async function springMotion(el, opts = {}) {
  if (!el) return null;
  if (reducedMotion()) {
    reveal(el);
    return null;
  }
  const motion = await motionWithin();
  if (!motion) {
    reveal(el);
    return null;
  }
  return motion.springIn(el, opts);
}

export async function staggerMotion(els, opts = {}) {
  const targets = Array.from(els || []).filter(Boolean);
  if (!targets.length) return null;
  if (reducedMotion()) {
    reveal(targets);
    return null;
  }
  const motion = await motionWithin();
  if (!motion) {
    reveal(targets);
    return null;
  }
  return motion.staggerIn(targets, opts);
}

function cardTargets(root) {
  return Array.from(root.querySelectorAll(".card, .quest-card, .room-card, .stat, .mission-row"))
    .filter((node) => !node.closest(".sheet") && !node.classList.contains("tl-item"))
    .slice(0, 12);
}

// Tiny hyperscript: el("div.card", {onclick}, [child, "text"])
export function el(tag, attrs = {}, children = []) {
  let tagName = "div", id = null;
  const classes = [];
  tag.replace(/([.#]?[^.#]+)/g, (tok) => {
    if (tok.startsWith(".")) classes.push(tok.slice(1));
    else if (tok.startsWith("#")) id = tok.slice(1);
    else tagName = tok;
  });
  const node = document.createElement(tagName);
  if (id) node.id = id;
  if (classes.length) node.className = classes.join(" ");
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") node.className += " " + v;
    else if (k === "html") node.innerHTML = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "dataset") Object.assign(node.dataset, v);
    else node.setAttribute(k, v);
  }
  const kids = Array.isArray(children) ? children : [children];
  for (const c of kids) {
    if (c == null || c === false) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}

// Screen teardown registry — runs when the next screen mounts or route leaves.
let _cleanup = [];
export function onLeave(fn) { if (typeof fn === "function") _cleanup.push(fn); }
export function runCleanup() {
  const fns = _cleanup; _cleanup = [];
  fns.forEach((f) => { try { f(); } catch (_) {} });
}

export function mount(node) {
  runCleanup();
  const view = document.getElementById("view");
  view.classList.remove("walk-view");
  view.innerHTML = "";
  // overlays from a previous screen (sheets, full-bleed maps) cleared too
  const ov = document.getElementById("overlay-root");
  if (ov) ov.innerHTML = "";
  const wrap = el("div.screen");
  wrap.append(node);
  view.append(wrap);
  view.scrollTo?.(0, 0);
  requestAnimationFrame(() => {
    springMotion(wrap, { y: 12, scale: 0.985 });
    const targets = cardTargets(wrap);
    if (targets.length) staggerMotion(targets, { y: 14, each: 0.035 });
  });
  return wrap;
}

// ---------------- Toast ----------------
export function toast(msg, kind = "") {
  const root = document.getElementById("toasts");
  const t = el("div.toast" + (kind ? "." + kind : ""), { text: msg });
  root.append(t);
  if ("vibrate" in navigator && kind === "ok") navigator.vibrate?.(12);
  if ("vibrate" in navigator && kind === "err") navigator.vibrate?.([8, 40, 8]);
  const ttl = reducedMotion() ? 1800 : 2400;
  setTimeout(() => {
    t.classList.add("out");
    setTimeout(() => t.remove(), 280);
  }, ttl);
  return t;
}

// ---------------- Achievement unlock toasts ----------------
// 서버 응답의 unlocked 배열을 받아 뱃지 토스트를 띄운다. 토스트는 #toasts(뷰 밖)에
// 쌓여 화면 전환 후에도 유지되므로 기록 저장→다이어리 이동 흐름에서도 안전하다.
export function announceUnlocks(unlocked) {
  if (!Array.isArray(unlocked) || !unlocked.length) return;
  navigator.vibrate?.([16, 30, 16]);
  unlocked.forEach((a, i) => {
    setTimeout(() => {
      const t = toast(`🏅 새 업적 · ${a.emoji} ${a.name}`, "ok");
      t.classList.add("badge");
    }, i * 480);
  });
}

// ---------------- Bottom sheet ----------------
export function bottomSheet(buildContent) {
  const root = document.getElementById("overlay-root");
  const scrim = el("div.sheet-scrim");
  const sheet = el("div.sheet");
  sheet.append(el("div.grabber"));
  const close = () => {
    scrim.classList.remove("open");
    setTimeout(() => scrim.remove(), reducedMotion() ? 10 : 380);
  };
  const body = buildContent(close);
  sheet.append(body);
  scrim.append(sheet);
  scrim.addEventListener("click", (e) => { if (e.target === scrim) close(); });
  root.append(scrim);
  requestAnimationFrame(() => {
    scrim.classList.add("open");
    springSheet(sheet);
  });
  return { close, sheet };
}

async function springSheet(sheet) {
  if (reducedMotion()) {
    sheet.style.transform = "none";
    return null;
  }
  const motion = await motionWithin();
  if (!motion) {
    sheet.style.transform = "none";
    return null;
  }
  return motion.sheetUp(sheet);
}

// ---------------- Celebration (matching success) ----------------
export async function celebrate(pet) {
  if (reducedMotion()) return;
  navigator.vibrate?.([20, 40, 30]);
  const motion = await motionWithin();
  if (!motion) return;
  const root = document.getElementById("overlay-root");
  const layer = el("div.celebrate-layer", {
    dataset: { motion: "celebrate" },
    style: "position:fixed;inset:0;z-index:70;pointer-events:none;overflow:hidden",
  });
  const mascot = el("div.celebrate-mascot", {
    style: "position:absolute;left:50%;top:42%;filter:drop-shadow(0 10px 16px rgba(43,36,32,.18));transform:translate(-50%,-50%) scale(.2);opacity:0",
  });
  if (pet) {
    mascot.style.width = mascot.style.height = "132px";
    mascot.append(petCharacterEl(pet, { size: 132 }));
  } else {
    mascot.textContent = "🐶";
    mascot.style.fontSize = "4.2rem";
  }
  layer.append(mascot);
  motion.animate(
    mascot,
    {
      opacity: [0, 1, 1, 0],
      transform: [
        "translate(-50%,-50%) scale(.2) rotate(-8deg)",
        "translate(-50%,-50%) scale(1.18) rotate(4deg)",
        "translate(-50%,-50%) scale(1) rotate(0deg)",
        "translate(-50%,-58%) scale(.96) rotate(0deg)",
      ],
    },
    { ...motion.SPRING, duration: 1.35 }
  );
  const emojis = ["🎉", "🐶", "✨", "💛", "🐾"];
  for (let i = 0; i < 28; i++) {
    const startX = 45 + Math.random() * 10;
    const dx = (Math.random() * 2 - 1) * 190;
    const dy = 180 + Math.random() * 260;
    const p = el("div", {
      text: emojis[i % emojis.length],
      style: `position:absolute;left:${startX}%;top:42%;font-size:${18 + Math.random() * 18}px;opacity:0;`,
    });
    motion.animate(
      p,
      {
        opacity: [0, 1, 0],
        transform: [
          "translate(-50%,-50%) scale(.35) rotate(0deg)",
          `translate(calc(-50% + ${dx * 0.45}px), calc(-50% - ${80 + Math.random() * 80}px)) scale(1) rotate(${(Math.random() * 2 - 1) * 160}deg)`,
          `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) scale(.8) rotate(${(Math.random() * 2 - 1) * 420}deg)`,
        ],
      },
      { ...motion.SOFT, delay: i * 0.012, duration: 1.7 }
    );
    layer.append(p);
  }
  root.append(layer);
  setTimeout(() => layer.remove(), 1900);
}

export async function settleCardToCalendar(sourceEl) {
  const root = document.documentElement;
  root.dataset.recordSaveMotion = "pending";
  if (reducedMotion() || !sourceEl) {
    root.dataset.recordSaveMotion = "reduced";
    return false;
  }
  const motion = await motionWithin();
  if (!motion) {
    reveal(sourceEl);
    root.dataset.recordSaveMotion = "fallback";
    return false;
  }

  const target = document.querySelector('#tabbar a[data-tab="diary"]') || document.getElementById("view");
  const rawFrom = sourceEl.getBoundingClientRect();
  const from = rawFrom.width && rawFrom.height
    ? rawFrom
    : {
        left: Math.max(16, (window.innerWidth - 280) / 2),
        top: window.innerHeight * 0.34,
        width: Math.min(280, window.innerWidth - 32),
        height: 86,
      };
  const rawTo = target?.getBoundingClientRect();
  const to = rawTo && rawTo.width && rawTo.height
    ? rawTo
    : {
        left: window.innerWidth * 0.72,
        top: window.innerHeight - 48,
        width: 56,
        height: 56,
      };
  const clone = sourceEl.cloneNode(true);
  clone.dataset.motion = "record-save-fly";
  Object.assign(clone.style, {
    position: "fixed",
    left: `${from.left}px`,
    top: `${from.top}px`,
    width: `${from.width}px`,
    height: `${from.height}px`,
    margin: "0",
    zIndex: "75",
    pointerEvents: "none",
    transformOrigin: "center",
  });
  document.body.append(clone);
  root.dataset.recordSaveMotion = "started";
  sourceEl.style.opacity = "0.18";

  const dx = to.left + to.width / 2 - (from.left + from.width / 2);
  const dy = to.top + to.height / 2 - (from.top + from.height / 2);
  const controls = motion.animate(
    clone,
    {
      opacity: [1, 0.95, 0],
      transform: [
        "translate(0px, 0px) scale(1) rotate(0deg)",
        `translate(${dx}px, ${dy}px) scale(.22) rotate(-7deg)`,
      ],
    },
    { ...motion.SPRING, duration: 0.72 }
  );
  try { await controls.finished; } catch (_) {}
  clone.remove();
  sourceEl.style.opacity = "1";
  root.dataset.recordSaveMotion = "done";
  return true;
}

// ---------------- Tab bar ----------------
export function setTab(name) {
  const bar = document.getElementById("tabbar");
  if (!name) { bar.classList.add("hidden"); return; }
  bar.classList.remove("hidden");
  bar.querySelectorAll("a").forEach((a) => {
    const isActive = a.dataset.tab === name;
    const wasActive = a.classList.contains("active");
    a.classList.toggle("active", isActive);
    if (isActive && !wasActive && !reducedMotion()) {
      a.classList.remove("tab-pulse");
      void a.offsetWidth;
      a.classList.add("tab-pulse");
      setTimeout(() => a.classList.remove("tab-pulse"), 420);
    }
  });
}

export function loading() {
  return mount(el("div.center", {}, [el("div.spinner")]));
}

export function setWho(text) {
  document.getElementById("who").textContent = text || "";
}
