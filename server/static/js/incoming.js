// incoming.js — 전역 매칭 요청 폴링 배너 (F-03 수신자측, 폴링)
// 라우터의 stopAll() 영향을 받지 않도록 자체 setInterval로 동작한다.
import { api } from "./api.js";
import { store } from "./store.js";
import { reducedMotion, toast, icon } from "./ui.js";
import { navigate } from "./router.js";
import { petCharacterEl } from "./character.js";

const POLL_MS = 3000;
const dismissed = new Set();
let shownId = null;
let timer = null;

function banner() { return document.getElementById("incoming-banner"); }

function hide() {
  const b = banner();
  if (!b) return;
  b.classList.remove("show");
  shownId = null;
  const done = () => { b.hidden = true; b.innerHTML = ""; };
  reducedMotion() ? done() : setTimeout(done, 380);
}

function show(req) {
  if (shownId === req.id) return; // 이미 같은 요청 표시 중
  const b = banner();
  if (!b) return;
  shownId = req.id;
  b.hidden = false;
  b.innerHTML = "";

  const accept = document.createElement("button");
  accept.className = "cta"; accept.id = "incoming-accept"; accept.textContent = "수락";
  accept.style.cssText = "width:auto;min-height:38px;padding:8px 16px";
  accept.addEventListener("click", async () => {
    accept.disabled = true;
    try {
      await api.patch(`/match-requests/${req.id}/accept`, {});
      hide();
      // 수락자도 요청자와 같은 만남 게이트 화면으로 → 둘 다 [만났습니다] 눌러야 퀘스트로.
      navigate(`/matching/${req.id}`);
    } catch (e) {
      toast(e.message || "수락 실패", "err");
      accept.disabled = false;
    }
  });

  const close = document.createElement("button");
  close.className = "btn ghost"; close.id = "incoming-close"; close.append(icon("x"));
  close.addEventListener("click", () => { dismissed.add(req.id); hide(); });

  const nick = (req.requester && req.requester.nickname) || "누군가";
  const av = document.createElement("div"); av.className = "av has-char";
  av.append(petCharacterEl(req.pet && req.pet.name ? req.pet : { name: nick }, { size: 38 }));
  const txt = document.createElement("div"); txt.className = "txt";
  const petName = (req.pet && req.pet.name) ? ` · ${req.pet.name}` : "";
  txt.innerHTML = `<div class="t">${nick}님의 같이 산책 요청${petName}</div><div class="d">수락하면 함께 산책을 시작해요</div>`;

  b.append(av, txt, accept, close);
  requestAnimationFrame(() => b.classList.add("show"));
}

async function tick() {
  if (!store.isAuthed) { hide(); return; }
  const h = location.hash;
  // 요청/세션 화면에서는 자체 UI가 있으므로 전역 배너 생략
  if (h.startsWith("#/request/") || h.startsWith("#/session/") || h.startsWith("#/matching/")) { hide(); return; }
  let data;
  try { data = await api.get("/match-requests/incoming"); } catch { return; }
  const reqs = (data.requests || []).filter((r) => !dismissed.has(r.id));
  if (!reqs.length) { hide(); return; }
  show(reqs[0]);
}

export function startIncomingWatch() {
  if (timer) return;
  tick();
  timer = setInterval(tick, POLL_MS);
}
