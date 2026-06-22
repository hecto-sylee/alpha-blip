// screens/home.js — SCR-10 홈 (산책 시작 전). 큰 산책 CTA + 펫 카드.
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, setTab, setWho, toast, icon } from "../ui.js";
import { navigate } from "../router.js";

export async function homeScreen() {
  setTab("walk");
  let me = null;
  try {
    me = await api.get("/auth/me");
    setWho(me.nickname);
  } catch (e) {
    toast(e.message, "err");
  }
  const pet = me?.pets?.[0];
  if (pet) store.setPetId(pet.id);

  const startCta = el("button.cta.big.home-start", { id: "start-walk", type: "button", text: "산책 시작" });
  startCta.addEventListener("click", () => navigate("/walk"));
  const demoLabel = el("span", { text: "데모 산책 (강남 테헤란로)" });
  const demoCta = el("button.btn.secondary.demo-start", { id: "demo-setup", type: "button" }, [icon("flask-conical"), demoLabel]);
  demoCta.addEventListener("click", async () => {
    demoCta.disabled = true;
    demoLabel.textContent = "데모 준비 중…";
    try {
      const demo = await api.post("/demo/setup", {});
      store.setWalkId(null);
      store.setDemo({
        lat: demo.location.latitude,
        lng: demo.location.longitude,
        label: demo.location.label,
        mockSessionId: demo.mock_walk_session_id,
        mockPet: demo.mock_pet,
        roomId: demo.room_id,
        roomJoinCode: demo.room_join_code,
      });
      toast("강남 테헤란로 데모 산책을 시작해요", "ok");
      navigate("/walk");
    } catch (e) {
      toast(e.message || "데모를 준비하지 못했어요", "err");
      demoCta.disabled = false;
      demoLabel.textContent = "데모 산책 (강남 테헤란로)";
    }
  });

  mount(
    el("div.stack", {}, [
      el("section.home-hero", {}, [
        el("div.home-hero-copy", {}, [
          el("div.badge", { text: "오늘의 산책" }),
          el("h1.home-title", { text: "산책 나갈 시간" }),
          el("p.sub", { text: `${me?.nickname || "친구"}님, 오늘도 가볍게 한 바퀴 돌아볼까요?` }),
        ]),
        el("div.home-actions", {}, [startCta, demoCta]),
      ]),

      pet
        ? el("div.card.tappable.home-pet-card", { id: "my-pet-card", onclick: () => navigate(`/pet/${pet.id}`) }, [
            el("div.row", {}, [
              el("div.pet-avatar.home-pet-avatar", {}, [icon("dog")]),
              el("div.grow", {}, [
                el("div.title", { text: pet.name }),
                el("div.sub", { text: pet.breed || "견종 미입력" }),
              ]),
              el("span.chip.on", { text: "함께 걷기" }),
            ]),
          ])
        : el("div.card", {}, [
            el("p", { text: "반려동물을 먼저 등록해 주세요." }),
            el("button.btn", { text: "등록하기", onclick: () => navigate("/onboard-pet") }),
          ]),

      el("div.home-tip", {}, [
        el("div.h2", { text: "근처 친구 찾기" }),
        el("p.sub", { text: "산책을 시작하면 지도에서 근처 강아지 친구를 만날 수 있어요." }),
      ]),
    ])
  );
}
