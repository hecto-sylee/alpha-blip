// router.js — 해시 라우팅 (#/walk, #/room/:id ...)
import { stopAll } from "./polling.js";

const routes = [];
let guard = null;
let notFound = null;

function compile(pattern) {
  const keys = [];
  const rx = new RegExp(
    "^" +
      pattern
        .replace(/:[^/]+/g, (m) => { keys.push(m.slice(1)); return "([^/]+)"; })
        .replace(/\//g, "\\/") +
      "$"
  );
  return { rx, keys };
}

export function route(pattern, handler) {
  routes.push({ pattern, handler, ...compile(pattern) });
}
export function setGuard(fn) { guard = fn; }
export function setNotFound(fn) { notFound = fn; }

export function navigate(path) {
  if (location.hash === "#" + path) handle();
  else location.hash = path;
}

function parse() {
  const raw = location.hash.replace(/^#/, "") || "/";
  const [path, query] = raw.split("?");
  const params = {};
  const q = Object.fromEntries(new URLSearchParams(query || ""));
  for (const r of routes) {
    const m = r.rx.exec(path);
    if (m) {
      r.keys.forEach((k, i) => (params[k] = decodeURIComponent(m[i + 1])));
      return { r, params, query: q, path };
    }
  }
  return { r: null, params, query: q, path };
}

async function handle() {
  stopAll(); // 화면 전환 시 이전 폴링 정리
  const match = parse();
  if (guard) {
    const redirect = await guard(match);
    if (redirect && redirect !== match.path) { navigate(redirect); return; }
  }
  if (match.r) await match.r.handler(match.params, match.query);
  else if (notFound) notFound(match);
}

export function startRouter() {
  window.addEventListener("hashchange", handle);
  handle();
}

export { handle as refresh };
