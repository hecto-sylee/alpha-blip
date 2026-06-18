// screens/auth.js — SCR-01 로그인/회원가입 (게스트)
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, setWho } from "../ui.js";
import { navigate } from "../router.js";

export async function authScreen() {
  setTab(null);
  setWho("");

  const input = el("input.input", {
    id: "nickname",
    placeholder: "닉네임 (예: 초코아빠)",
    maxlength: "20",
    autocomplete: "off",
  });

  const cta = el("button.cta.big", { id: "guest-cta", text: "blip 시작하기", disabled: true });

  input.addEventListener("input", () => {
    cta.disabled = input.value.trim().length === 0;
  });

  cta.addEventListener("click", async () => {
    const nickname = input.value.trim();
    if (!nickname) return;
    cta.disabled = true;
    cta.textContent = "가입 중…";
    try {
      const res = await api.post("/auth/guest", { nickname }, { auth: false });
      store.setSession(res.user_id, res.auth_token);
      toast(`반가워요, ${nickname}님!`, "ok");
      navigate("/onboard-pet");
    } catch (e) {
      toast(e.message || "가입에 실패했어요", "err");
      cta.disabled = false;
      cta.textContent = "blip 시작하기";
    }
  });

  mount(
    el("div.stack", {}, [
      el("div", { style: "height:8vh" }),
      el("div.center", {}, [
        el("div", { style: "font-size:3rem", text: "🐾" }),
        el("h1.h1", { text: "오늘, 같이 걸을까요?" }),
        el("p.sub", { text: "닉네임만으로 바로 시작해요. 비밀번호 없이 게스트로." }),
      ]),
      el("div", { style: "height:12px" }),
      el("div.field", {}, [el("label", { html: "닉네임 <span class='req'>*</span>" }), input]),
      cta,
      el("p.sub.center", { text: "산책하며 근처 강아지 친구를 만나고, 2초 클립으로 기록해요." }),
    ])
  );

  setTimeout(() => input.focus(), 50);
}
