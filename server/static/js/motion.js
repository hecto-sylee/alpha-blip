// motion.js — Motion One wrapper. Imported dynamically by app code so CDN
// failures never block the SPA module graph.
import { animate, stagger, inView } from "https://cdn.jsdelivr.net/npm/motion@11/+esm";
import { reducedMotion } from "./ui.js";

export const SPRING = { type: "spring", stiffness: 520, damping: 30 };
export const SOFT = { type: "spring", stiffness: 380, damping: 34 };

function toArray(els) {
  if (!els) return [];
  if (els instanceof Element) return [els];
  return Array.from(els).filter(Boolean);
}

function reveal(els, { transform = "none" } = {}) {
  toArray(els).forEach((el) => {
    el.style.opacity = "1";
    if (transform != null) el.style.transform = transform;
  });
}

function finishVisible(controls, els) {
  const done = controls?.finished;
  if (done && typeof done.then === "function") {
    done.then(() => reveal(els)).catch(() => reveal(els));
  }
}

export function springIn(el, { y = 12, scale = 0.98, delay = 0 } = {}) {
  if (!el) return null;
  if (reducedMotion()) {
    reveal(el);
    return null;
  }
  try {
    el.dataset.motion = "spring-in";
    reveal(el, `translateY(${y}px) scale(${scale})`);
    const controls = animate(
      el,
      { transform: [`translateY(${y}px) scale(${scale})`, "translateY(0px) scale(1)"] },
      { ...SPRING, delay }
    );
    finishVisible(controls, el);
    return controls;
  } catch (_) {
    reveal(el);
    return null;
  }
}

export function staggerIn(els, { y = 14, each = 0.05 } = {}) {
  const targets = toArray(els);
  if (!targets.length) return null;
  if (reducedMotion()) {
    reveal(targets);
    return null;
  }
  try {
    targets.forEach((el) => {
      el.dataset.motion = "stagger-in";
      reveal(el, `translateY(${y}px)`);
    });
    const controls = animate(
      targets,
      { transform: [`translateY(${y}px)`, "translateY(0px)"] },
      { ...SOFT, delay: stagger(each) }
    );
    finishVisible(controls, targets);
    return controls;
  } catch (_) {
    reveal(targets);
    return null;
  }
}

export function sheetUp(el) {
  if (!el) return null;
  if (reducedMotion()) {
    reveal(el);
    return null;
  }
  try {
    el.dataset.motion = "sheet-up";
    const controls = animate(el, { transform: ["translateY(110%)", "translateY(0px)"] }, SPRING);
    finishVisible(controls, el);
    return controls;
  } catch (_) {
    reveal(el);
    return null;
  }
}

export { animate, inView };
