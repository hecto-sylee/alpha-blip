// app.js — 부트스트랩: 세션 복원 → 라우터 시작
import { store } from "./store.js";
import { api } from "./api.js";
import { setWho, motionReady } from "./ui.js";
import { route, setGuard, setNotFound, startRouter, navigate } from "./router.js";
import { authScreen } from "./screens/auth.js";
import { petScreen } from "./screens/pet.js";
import { homeScreen } from "./screens/home.js";
import { walkScreen } from "./screens/walk.js";
import { requestWaitScreen, sessionScreen } from "./screens/match.js";
import { questScreen } from "./screens/quest.js";
import { recordScreen } from "./screens/record.js";
import { diaryScreen, recordViewScreen } from "./screens/diary.js";
import { roomsListScreen, roomCreateScreen, roomJoinScreen } from "./screens/rooms.js";
import { roomViewScreen } from "./screens/room_view.js";
import { myScreen, settingsScreen } from "./screens/my.js";
import { petsScreen } from "./screens/pets.js";
import { achievementsScreen } from "./screens/achievements.js";
import { leagueScreen } from "./screens/league.js";
import { startIncomingWatch } from "./incoming.js";
import { hydrateIcons } from "./icons.js";

// ---- deep link: Android app://join/{code} → /?join={code} ----
(function captureJoin() {
  const code = new URLSearchParams(location.search).get("join");
  if (code) { store.setPendingJoin(code.toUpperCase()); }
})();

// ---- routes ----
route("/auth", authScreen);
route("/onboard-pet", () => petScreen({}));
route("/pet/:id", (p) => petScreen(p));
route("/home", homeScreen);

// 산책 · 매칭 (FE1)
route("/walk", walkScreen);
route("/request/:id", requestWaitScreen);
route("/session/:id", sessionScreen);

// 퀘스트 · 기록 (FE2)
route("/quest", questScreen);
route("/record", recordScreen);
route("/record/:id", recordViewScreen);
route("/diary", diaryScreen);

// 방 (FE3)
route("/rooms", roomsListScreen);
route("/rooms/new", roomCreateScreen);
route("/rooms/join", roomJoinScreen);
route("/room/:id", roomViewScreen);

// 랭킹 · 마이 · 설정 (FE4)
route("/league", leagueScreen);
route("/my", myScreen);
route("/pets", petsScreen);
route("/achievements", achievementsScreen);
route("/settings", settingsScreen);

setNotFound(() => navigate(store.isAuthed ? "/home" : "/auth"));

// ---- auth / onboarding guard ----
let petCheck = { done: false, hasPet: false };

async function ensurePetStatus() {
  if (petCheck.done) return petCheck.hasPet;
  try {
    const me = await api.get("/auth/me");
    setWho(me.nickname);
    petCheck = { done: true, hasPet: (me.pets || []).length > 0 };
    if (petCheck.hasPet) store.setPetId(me.pets[0].id);
  } catch {
    // 토큰 무효 → 세션 정리
    store.logout();
    petCheck = { done: true, hasPet: false };
  }
  return petCheck.hasPet;
}

setGuard(async ({ path }) => {
  if (!store.isAuthed) {
    return path === "/auth" ? null : "/auth";
  }
  if (path === "/auth") return "/home";

  const hasPet = await ensurePetStatus();
  if (!hasPet && path !== "/onboard-pet" && !path.startsWith("/pet/")) {
    return "/onboard-pet";
  }
  return null;
});

// store mutations should reset cached pet status
const origSetPet = store.setPetId.bind(store);
store.setPetId = (id) => { origSetPet(id); if (id) petCheck = { done: true, hasPet: true }; };

// ---- boot ----
hydrateIcons(); // 정적 마크업(탭바) 아이콘 주입
if (!location.hash) location.hash = store.isAuthed ? "/home" : "/auth";
startRouter();
startIncomingWatch(); // 전역 매칭 요청 폴링 배너

window.blip = { store, api, navigate, motionReady };
