// screens/match.js — SCR-12 미리보기 시트 · SCR-13 요청 대기 · SCR-14 매칭 세션 (F-03/04/05)
import { api } from "../api.js";
import { el, mount, toast, setTab, bottomSheet, celebrate, onLeave, announceUnlocks, icon } from "../ui.js";
import { navigate } from "../router.js";
import * as poll from "../polling.js";
import { fmtDistance } from "../geo.js";
import { petCharacterEl } from "../character.js";

// ---------------- SCR-12 상대 프로필 미리보기 (바텀시트) ----------------
export function openPreview(dog, ctx) {
  const pet = dog.pet || {};
  bottomSheet((close) => {
    const cta = el("button.cta", { id: "send-request", text: "같이 산책하기" });
    cta.addEventListener("click", async () => {
      cta.disabled = true; cta.textContent = "요청 보내는 중…";
      try {
        const res = await api.post("/match-requests", { receiver_walk_session_id: dog.walk_session_id });
        close();
        navigate(`/request/${res.match_request_id}`);
      } catch (e) {
        toast(e.message || "요청을 보내지 못했어요", "err");
        cta.disabled = false; cta.textContent = "같이 산책하기";
      }
    });

    const tags = (pet.personality_tags || []).slice(0, 6).map((t) => el("span.chip", { text: t }));

    return el("div.stack", { id: "preview-sheet" }, [
      el("div.row", {}, [
        el("div.pet-avatar.has-char", {}, [petCharacterEl(pet, { size: 56 })]),
        el("div", {}, [
          el("div.title", { text: pet.name || "강아지" }),
          el("div.sub", { text: `${pet.breed || "견종 미상"} · ${fmtDistance(dog.distance_meters)} 근처` }),
        ]),
      ]),
      el("div.row.wrap.gap-sm", {}, [
        pet.size && el("span.chip.on", { text: sizeLabel(pet.size) }),
        ...tags,
      ]),
      pet.caution_notes && el("p.sub", {}, [icon("triangle-alert"), ` ${pet.caution_notes}`]),
      cta,
    ]);
  });
}

function sizeLabel(s) { return { small: "소형", medium: "중형", large: "대형" }[s] || s; }

// 서버 시각은 naive UTC(ISO, 타임존 표기 없음) → UTC로 해석하도록 'Z' 보정
function parseServerTime(s) {
  if (!s) return new Date();
  const hasTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(s);
  return new Date(hasTz ? s : s + "Z");
}

// ---------------- SCR-13 요청 대기 / 결과 ----------------
export async function requestWaitScreen(params) {
  setTab(null);
  const reqId = params.id;

  const cancelBtn = el("button.btn.danger", { id: "cancel-request", text: "요청 취소" });
  cancelBtn.addEventListener("click", async () => {
    poll.stop("req-status");
    try { await api.del(`/match-requests/${reqId}`); } catch (_) {}
    toast("요청을 취소했어요");
    navigate("/walk");
  });

  mount(
    el("div.screen-center.stack.center", { id: "request-wait" }, [
      el("div.emoji-xl", {}, [icon("paw-print")]),
      el("h1.h1", { text: "요청을 보냈어요" }),
      el("p.sub", { text: "상대가 수락하면 함께 산책을 시작해요." }),
      el("div.spinner"),
      cancelBtn,
    ])
  );

  poll.start("req-status", async () => {
    let r;
    try { r = await api.get(`/match-requests/${reqId}`); } catch { return; }
    if (r.status === "accepted" && r.match_session_id) {
      poll.stop("req-status");
      navigate(`/session/${r.match_session_id}`);
    } else if (["rejected", "expired", "cancelled"].includes(r.status)) {
      poll.stop("req-status");
      toast(r.status === "rejected" ? "상대가 거절했어요" : r.status === "expired" ? "요청이 만료됐어요" : "요청이 취소됐어요");
      navigate("/walk");
    }
  }, 2000);

  onLeave(() => poll.stop("req-status"));
}

// ---------------- SCR-14 매칭 세션 (함께 산책 중) ----------------
export async function sessionScreen(params) {
  setTab(null);
  const sid = params.id;

  let session;
  try {
    session = await api.get(`/match-sessions/${sid}`);
  } catch (e) {
    toast(e.message || "세션을 불러오지 못했어요", "err");
    navigate("/home");
    return;
  }

  const partner = session.partner || {};
  const ppet = partner.pet || {};
  const started = parseServerTime(session.started_at);

  let myPet = null;
  try { myPet = (await api.get("/auth/me")).pets?.[0] || null; } catch (_) {}

  const timerEl = el("div.timer", { id: "session-timer", text: "00:00" });
  const endBtn = el("button.cta", { id: "end-session", text: "산책 종료" });

  endBtn.addEventListener("click", async () => {
    endBtn.disabled = true; endBtn.textContent = "마무리하는 중…";
    poll.stop("session-timer");
    const mins = Math.max(1, Math.round((Date.now() - started.getTime()) / 60000));
    try {
      const res = await api.post(`/match-sessions/${sid}/end`, { duration_minutes: mins });
      toast("함께한 산책이 기록됐어요", "ok", "paw-print");
      announceUnlocks(res?.unlocked); // 친구 N회 산책 등 업적 알림
    } catch (e) {
      toast(e.message || "종료 처리에 실패했어요", "err");
    }
    // SCR-20 기록 에디터로 (매칭 산책 출처 연결)
    navigate(`/record?match=${sid}`);
  });

  const hud = el("div.session-hud", {}, [
    el("div.session-hud-body", {}, [
      el("div.session-pets", {}, [
        el("div.session-pet", {}, [petCharacterEl(myPet || { name: "나" }, { size: 92 })]),
        el("div.session-pet", {}, [petCharacterEl(ppet.name ? ppet : { name: partner.nickname || "친구" }, { size: 92 })]),
      ]),
      el("h1.h1.center", { text: `${partner.nickname || "친구"}님과 산책 중` }),
      el("p.sub.center", { text: `${ppet.name || ""} ${ppet.breed ? "· " + ppet.breed : ""}` }),
      el("p.sub", { text: "동행 시간" }),
      timerEl,
    ]),
    el("div.session-hud-foot", {}, [endBtn]),
  ]);

  mount(hud);
  celebrate(myPet); // 매칭 성사 축하 모션

  const tick = () => {
    const s = Math.floor((Date.now() - started.getTime()) / 1000);
    const mm = String(Math.floor(s / 60)).padStart(2, "0");
    const ss = String(s % 60).padStart(2, "0");
    const t = document.getElementById("session-timer");
    if (t) t.textContent = `${mm}:${ss}`;
  };
  tick();
  poll.start("session-timer", async () => tick(), 1000);
  onLeave(() => poll.stop("session-timer"));
}
