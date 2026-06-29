// screens/walking.js — 퀘스트 페이지(LP-12, 라우트 #/walk). 지도 없음.
//
// 설계(LetsPaw): 솔로는 홈에서 '산책하기' 직후 바로 이 페이지(다른 개 미등장),
// 매칭은 '만났습니다' 게이트 통과 후 이 페이지. 화면 = 퀘스트 스택 + 산책 종료뿐.
//   - 퀘스트 카드 탭 → #/camera?mission=&quest= (2초 촬영, store.walkClips 누적)
//   - 산책 종료(전화 끊기) → 종료 → 누적 클립으로 기록 1건(+포인트) → #/diary
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, onLeave, icon } from "../ui.js";
import { navigate } from "../router.js";
import * as poll from "../polling.js";

const MATCH_KEY = "blip_walk_match";    // 매칭 산책의 match_session_id
const START_KEY = "blip_walk_started";  // 산책 시작 시각(ms)
const readMatch = () => localStorage.getItem(MATCH_KEY) || null;
const writeMatch = (id) => { if (id) localStorage.setItem(MATCH_KEY, id); };
const clearMatch = () => localStorage.removeItem(MATCH_KEY);

function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export async function walkingScreen(_params, query = {}) {
  setTab(null); // 몰입 모드

  const matchId = query.match || readMatch();
  if (query.match) writeMatch(query.match);

  // 세션 보장: 솔로면 홈에서 이미 walk 시작됨. 둘 다 없으면 홈으로(직접 진입 방지).
  const walkId = store.walkId;
  if (!matchId && !walkId) { toast("산책을 먼저 시작해 주세요", "err"); navigate("/home"); return; }
  if (!localStorage.getItem(START_KEY)) localStorage.setItem(START_KEY, String(Date.now()));

  const { dailyQuestId, missions } = await ensureQuest(matchId);

  // --- 퀘스트 스택 ---
  let partnerMissions = new Set(); // 매칭: 상대가 이미 촬영한 미션 id (셋로그식 표시)
  const stack = el("div.quest-stack", { id: "quest-stack" });
  const renderStack = () => {
    const done = new Set(store.walkClips.map((c) => c.mission_id).filter(Boolean));
    stack.innerHTML = "";
    const list = missions || [];
    if (!list.length) {
      stack.append(el("p.sub.center", { text: "오늘의 퀘스트를 불러오지 못했어요. 그냥 자유 촬영해도 좋아요." }));
    }
    for (const m of list) {
      const isDone = done.has(m.id);
      const pDone = partnerMissions.has(m.id);
      const card = el("div.quest-card" + (isDone ? ".done" : ""), { dataset: { mission: m.id } }, [
        el("div.quest-card-body", {}, [
          el("div.quest-card-title", { text: m.title }),
          m.hint ? el("div.quest-card-hint", { text: m.hint }) : null,
          matchId ? el("div.quest-card-partner" + (pDone ? ".on" : ""), {
            text: pDone ? "상대 촬영 완료 ✓" : "상대 아직 미촬영",
          }) : null,
        ].filter(Boolean)),
        isDone
          ? el("span.quest-done", {}, [icon("check"), " 완료"])
          : el("button.btn.quest-shoot", { type: "button" },
              [icon("camera"), el("span", { text: "촬영" })]),
      ]);
      if (!isDone) {
        card.querySelector(".quest-shoot").addEventListener("click", () =>
          navigate(`/camera?mission=${encodeURIComponent(m.id)}&quest=${encodeURIComponent(m.title)}${matchId ? "&dual=1" : ""}`));
      }
      stack.append(card);
    }
    // 자유 촬영(미션과 무관한 한 컷)도 허용
    stack.append(el("button.btn.secondary.quest-free", { type: "button" },
      [icon("camera"), el("span", { text: "자유 촬영" })]));
    stack.querySelector(".quest-free").addEventListener("click", () => navigate(matchId ? "/camera?dual=1" : "/camera"));
  };
  renderStack();

  // --- 산책 종료(전화 끊기) ---
  const endBtn = el("button.end-call", { id: "walk-end", type: "button", "aria-label": "산책 종료" }, [icon("phone-off")]);
  let ending = false;
  async function endWalk(byPartner) {
    if (ending) return;
    ending = true;
    endBtn.disabled = true;
    poll.stop("walk-session");
    try {
      const startMs = Number(localStorage.getItem(START_KEY)) || Date.now();
      const mins = Math.max(0, Math.round((Date.now() - startMs) / 60000));
      if (matchId) { try { await api.post(`/match-sessions/${matchId}/end`, { duration_minutes: mins }); } catch (_) {} }
      else if (walkId) { try { await api.post(`/walks/${walkId}/end`, {}); } catch (_) {} }

      const clip_ids = store.walkClips.map((c) => c.clip_id).filter(Boolean);
      const payload = { visibility: "diary", walked_at: todayStr(), clip_ids, daily_quest_id: dailyQuestId };
      if (matchId) payload.match_session_id = matchId; else payload.walk_session_id = walkId;
      const rec = await api.post("/records", payload);
      if (rec?.points_awarded) toast(`🦴 +${rec.points_awarded} 포인트! (보유 ${rec.points})`, "ok");

      store.clearWalkClips();
      store.setWalkId(null);
      clearMatch();
      localStorage.removeItem(START_KEY);
      toast(byPartner ? "상대가 종료해 함께 기록했어요" : "산책을 기록했어요", "ok", "paw-print");
      navigate("/diary?saved=1");
    } catch (e) {
      ending = false;
      endBtn.disabled = false;
      toast(e.message || "기록 저장에 실패했어요", "err");
    }
  }
  endBtn.addEventListener("click", () => endWalk(false));

  // 매칭: 세션 폴링 — 상대가 종료하면 함께 종료, 상대 촬영현황(셋로그) 갱신.
  if (matchId) {
    poll.start("walk-session", async () => {
      try {
        const s = await api.get(`/match-sessions/${matchId}`);
        if (s && s.status === "ended" && !ending) { endWalk(true); return; }
      } catch (_) {}
      try {
        const r = await api.get(`/match-sessions/${matchId}/records`);
        const next = new Set((r.partner || []).flatMap((rec) => (rec.clips || []).map((c) => c.mission_id)).filter(Boolean));
        const changed = next.size !== partnerMissions.size || [...next].some((m) => !partnerMissions.has(m));
        if (changed) { partnerMissions = next; renderStack(); }
      } catch (_) {}
    }, 3000);
    onLeave(() => poll.stop("walk-session"));
  }

  mount(el("div.stack.quest-page", { id: "quest-page" }, [
    el("div.quest-context", {}, [
      el("span.dotlive"),
      el("span.strong", { text: matchId ? "동행 산책 중" : "혼자 산책 중" }),
    ]),
    el("h1.h1", { text: "오늘의 퀘스트" }),
    el("p.sub", { text: "원하는 순간을 골라 2초씩 담아요. 다 걸으면 종료를 눌러 한 편으로 엮어요." }),
    stack,
    el("div.end-dock", {}, [endBtn, el("span.end-label", { text: "산책 종료" })]),
  ]));

  // 카메라 다녀온 뒤(같은 라우트 재진입) 완료 상태 갱신 — onLeave 후 재mount되므로 renderStack은 진입 시 1회로 충분.
  onLeave(() => {});
}

// --- 오늘 퀘스트 확보 (없으면 후보 1개 자동 select) ---
// 솔로 = solo 모드(scope=user), 매칭 = match 모드(scope=match, 세션 공유) → 서로 다른 퀘스트.
async function ensureQuest(matchId) {
  const scope = matchId ? "match" : "user";
  const scopeId = matchId || store.userId;
  const mode = matchId ? "match" : "solo";
  const qp = `scope=${scope}&scope_id=${encodeURIComponent(scopeId)}`;
  try {
    const today = await api.get(`/quests/today?${qp}`);
    if (today && today.quest && today.daily_quest_id) {
      return { dailyQuestId: today.daily_quest_id, missions: today.quest.missions || [] };
    }
    const cand = await api.get(`/quests/candidates?${qp}&mode=${mode}`);
    const first = (cand.candidates || [])[0];
    if (!first) return { dailyQuestId: null, missions: [] };
    if (cand.locked) return { dailyQuestId: null, missions: first.missions || [] };
    const sel = await api.post("/quests/select", {
      scope, scope_id: scopeId,
      quest_template_id: first.quest_template_id, quest_date: todayStr(),
    });
    return { dailyQuestId: sel.daily_quest_id, missions: first.missions || [] };
  } catch (_) {
    return { dailyQuestId: null, missions: [] };
  }
}
