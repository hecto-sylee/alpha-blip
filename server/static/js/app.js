// app.js — 부트스트랩: 세션 복원 → 라우터 시작
import { store } from "./store.js";
import { api } from "./api.js";
import { setWho, motionReady, centerModal } from "./ui.js";
import { route, setGuard, setNotFound, startRouter, navigate } from "./router.js";
import { authScreen } from "./screens/auth.js";
import { petScreen } from "./screens/pet.js";
import { requestWaitScreen, sessionScreen } from "./screens/match.js";
import { roomsListScreen, roomCreateScreen, roomJoinScreen } from "./screens/rooms.js";
import { roomViewScreen } from "./screens/room_view.js";
import { myScreen, settingsScreen } from "./screens/my.js";
import { shopScreen } from "./screens/shop.js";
import { petsScreen } from "./screens/pets.js";
import { achievementsScreen } from "./screens/achievements.js";
import { leagueScreen } from "./screens/league.js";
import { startIncomingWatch } from "./incoming.js";
import { hydrateIcons } from "./icons.js";

// v2 재설계 스텁 화면 (W0 선등록 → W1~W6이 각 파일을 구현)
import { homeMapScreen } from "./screens/home_map.js";      // W1
import { walkingScreen } from "./screens/walking.js";       // W2
import { matchingScreen } from "./screens/matching.js";     // W3
import { cameraScreen } from "./screens/camera.js";         // W4
import { recordTabScreen } from "./screens/record_tab.js";  // W5
import { petDiaryNewScreen, petDiaryViewScreen } from "./screens/pet_diary.js"; // W6

// ---- deep link: Android app://join/{code} → /?join={code} ----
(function captureJoin() {
  const code = new URLSearchParams(location.search).get("join");
  if (code) { store.setPendingJoin(code.toUpperCase()); }
})();

// ---- routes ----
route("/auth", authScreen);
route("/onboard-pet", () => petScreen({}));
route("/pet/:id", (p) => petScreen(p));

// v2 핵심 루프 (홈 지도 → 산책/매칭 → 카메라 → 기록/펫일기)
route("/home", homeMapScreen);              // W1 — 홈 idle 지도 (구 homeScreen 대체)
route("/walk", walkingScreen);              // W2 — 산책 중 (구 walkScreen 대체)
route("/matching/:id", matchingScreen);     // W3 — 산책 매칭중 (신규)
route("/camera", cameraScreen);             // W4 — 카메라 촬영 (신규)
route("/diary", recordTabScreen);           // W5 — 기록 탭 (구 diaryScreen 대체)
route("/pet-diary/new", petDiaryNewScreen); // W6 — 펫일기 작성 (신규, :id보다 먼저 등록)
route("/pet-diary/:id", petDiaryViewScreen);// W6 — 펫일기 상세 (신규)

// 구 매칭 백업 경로 (W3가 /matching으로 흡수·정리)
route("/request/:id", requestWaitScreen);
route("/session/:id", sessionScreen);

// 방/랭킹/업적/설정 — dormant (진입점은 제거, 라우트는 보수적으로 유지)
route("/rooms", roomsListScreen);
route("/rooms/new", roomCreateScreen);
route("/rooms/join", roomJoinScreen);
route("/room/:id", roomViewScreen);
route("/league", leagueScreen);
route("/my", myScreen);
route("/shop", shopScreen);
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

window.blip = { store, api, navigate, motionReady, centerModal };
