// screens/auth.js — SCR-01 로그인/회원가입 (아이디 기반, 비밀번호 없음 · PoC)
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, setWho } from "../ui.js";
import { navigate } from "../router.js";
import { dogSVG, ensureDogStyles } from "../dog/render.js";
import { appearanceForBreed } from "../dog/params.js";

export async function authScreen() {
  setTab(null);
  setWho("");
  ensureDogStyles();
  const hero = el("div.auth-hero");
  hero.innerHTML = dogSVG(appearanceForBreed("corgi"), { pose: "front", size: 120 });

  const idInput = el("input.input", {
    id: "login-id",
    placeholder: "아이디 (예: choco_dad)",
    maxlength: "30",
    autocomplete: "username",
  });
  const nickInput = el("input.input", {
    id: "nickname",
    placeholder: "닉네임 (선택)",
    maxlength: "20",
    autocomplete: "off",
  });

  const cta = el("button.cta.big", { id: "login-cta", text: "시작하기", disabled: true });
  idInput.addEventListener("input", () => { cta.disabled = idInput.value.trim().length === 0; });

  const submit = async () => {
    const login_id = idInput.value.trim();
    if (!login_id) return;
    cta.disabled = true;
    cta.textContent = "들어가는 중…";
    try {
      const res = await api.post("/auth/login", { login_id, nickname: nickInput.value.trim() || null }, { auth: false });
      store.setSession(res.user_id, res.auth_token);
      toast(res.is_new ? `환영해요, ${res.nickname}님!` : `다시 오셨네요, ${res.nickname}님!`, "ok");
      navigate(res.is_new ? "/onboard-pet" : "/home");
    } catch (e) {
      toast(e.message || "로그인에 실패했어요", "err");
      cta.disabled = false;
      cta.textContent = "시작하기";
    }
  };
  cta.addEventListener("click", submit);
  nickInput.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });

  mount(
    el("div.screen-center.stack", {}, [
      el("div.center", {}, [
        hero,
        el("h1.h1", { text: "오늘, 같이 걸을까요?" }),
        el("p.sub", { text: "아이디로 시작해요. 같은 아이디로 다시 들어오면 기록이 이어져요. (비밀번호 없음)" }),
      ]),
      el("div.field", {}, [el("label", { html: "아이디 <span class='req'>*</span>" }), idInput]),
      el("div.field", {}, [el("label", { text: "닉네임 (선택)" }), nickInput]),
      cta,
      el("p.sub.center", { text: "산책하며 근처 강아지 친구를 만나고, 2초 클립으로 기록해요." }),
    ])
  );

  setTimeout(() => idInput.focus(), 50);
}
