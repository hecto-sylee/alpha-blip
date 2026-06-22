// screens/my.js — SCR-30 마이페이지 · SCR-32 개인정보 보호 설정 (F-09)
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, loading } from "../ui.js";
import { navigate } from "../router.js";
import { petCharacterEl } from "../character.js";

// ---------------- SCR-30 마이페이지 ----------------
export async function myScreen() {
  setTab("my");
  loading();
  let me = null, records = [], ach = null;
  try {
    me = await api.get("/auth/me");
    records = (await api.get("/records")).records || [];
  } catch (e) { toast(e.message || "불러오기 실패", "err"); }
  try { ach = await api.get("/achievements"); } catch (_) {}

  const pet = me?.pets?.[0];
  const diary = records.filter((r) => r.visibility === "diary");
  const totalDist = diary.reduce((s, r) => s + (r.distance_meters || 0), 0);

  mount(
    el("div.stack", {}, [
      el("h1.h1", { text: "마이" }),
      el("div.card", {}, [
        el("div.my-head", {}, [
          pet ? el("div.av.has-char", {}, [petCharacterEl(pet, { size: 64 })]) : el("div.av", { text: "🙂" }),
          el("div", {}, [
            el("div.nm", { text: me?.nickname || "게스트" }),
            el("div.sub", { text: pet ? `${pet.name} · ${pet.breed || "견종 미입력"}` : "반려동물 미등록" }),
          ]),
        ]),
      ]),

      el("div.stats", {}, [
        statCard(String(diary.length), "산책 기록"),
        statCard((totalDist / 1000).toFixed(1) + "km", "누적 거리"),
        statCard(String((me?.pets || []).length), "반려동물"),
      ]),

      achievementsCard(ach),

      el("div.card", {}, [
        pet
          ? linkRow("🐶", "반려동물 관리", () => navigate("/pets"))
          : linkRow("➕", "반려동물 등록", () => navigate("/onboard-pet")),
        linkRow("🏅", "업적", () => navigate("/achievements")),
        linkRow("🔒", "개인정보 보호 설정", () => navigate("/settings")),
        linkRow("👥", "내 방", () => navigate("/rooms")),
      ]),

      el("button.btn.danger", { id: "logout", text: "로그아웃", onclick: doLogout }),
    ])
  );
}

function statCard(v, k) { return el("div.stat", {}, [el("div.v", { text: v }), el("div.k", { text: k })]); }

function achievementsCard(ach) {
  const summary = ach?.summary;
  const items = ach?.achievements || [];
  const unlocked = items.filter((a) => a.unlocked);
  // 가장 최근에 달성한 뱃지 우선, 없으면 다음 목표(진행도 높은 잠금 뱃지) 미리보기
  const preview = unlocked.length
    ? unlocked.slice(-6).reverse()
    : items
        .filter((a) => !a.unlocked && a.value > 0)
        .sort((a, b) => b.value / b.threshold - a.value / a.threshold)
        .slice(0, 6);
  const count = summary ? `${summary.unlocked_count}/${summary.total_count}` : "—";
  const sub = unlocked.length ? `${count} 뱃지 달성` : "첫 산책으로 뱃지를 모아보세요";

  return el("div.card.tappable.ach-card", { onclick: () => navigate("/achievements") }, [
    el("div.ach-card-head", {}, [
      el("span.ach-card-title", { text: "🏅 업적" }),
      el("span.spacer"),
      el("span.ach-card-count", { text: count }),
    ]),
    el("div.ach-card-sub", { text: sub }),
    el("div.ach-card-strip", {}, preview.length
      ? preview.map((a) => el("span.ach-card-emoji" + (a.unlocked ? "" : ".dim"), { text: a.emoji, title: a.name }))
      : [el("span.ach-card-emoji.dim", { text: "🐾" })]),
  ]);
}
function linkRow(ic, label, onclick) {
  return el("div.list-link", { onclick }, [el("span.ic", { text: ic }), el("span", { style: "flex:1;font-weight:700", text: label }), el("span.chev", { text: "›" })]);
}

function doLogout() {
  if (!confirm("로그아웃 할까요?")) return;
  store.logout();
  toast("로그아웃 했어요");
  navigate("/auth");
}

// ---------------- SCR-32 개인정보 보호 설정 ----------------
export async function settingsScreen() {
  setTab("my");
  const s = store.settings;

  const toggles = [
    ["locationVisible", "위치 공유", "산책 중 지도에 내 위치를 노출합니다."],
    ["approximate", "대략적 위치 표시", "정확한 좌표 대신 흐린 위치로 보여줍니다."],
    ["hideHome", "집 주변 비공개", "집 근처에서는 위치를 숨깁니다."],
  ];

  const rows = toggles.map(([key, title, desc]) =>
    el("div.set-row", {}, [
      el("div.lbl", {}, [el("div.t", { text: title }), el("div.d", { text: desc })]),
      switchEl(key, s[key]),
    ])
  );

  // 기본 공개범위
  const visSeg = el("div.seg", { id: "default-vis" });
  [["diary", "📔 일기"], ["room", "👥 방"]].forEach(([val, label]) => {
    const o = el("div.opt" + (val === s.defaultVisibility ? ".sel" : ""), { text: label, dataset: { val } });
    o.addEventListener("click", () => {
      store.setSettings({ defaultVisibility: val });
      visSeg.querySelectorAll(".opt").forEach((n) => n.classList.remove("sel"));
      o.classList.add("sel");
      toast("저장됨", "ok");
    });
    visSeg.append(o);
  });

  // 차단 목록 (서버 목록 API 없음 → settings에 미러 유지)
  const blocked = (store.settings.blocked || []);
  const blockList = el("div", { id: "block-list" });
  function renderBlocks() {
    const list = store.settings.blocked || [];
    blockList.innerHTML = "";
    if (!list.length) { blockList.append(el("p.sub", { text: "차단한 사용자가 없어요." })); return; }
    list.forEach((uid) => {
      const row = el("div.block-row", { dataset: { uid } }, [
        el("span.who", { text: uid }),
        el("button.btn.danger", { text: "차단 해제", onclick: () => unblock(uid) }),
      ]);
      blockList.append(row);
    });
  }
  async function block(uid) {
    uid = uid.trim();
    if (!uid) return;
    try {
      await api.post("/privacy/block", { target_user_id: uid });
      const list = new Set(store.settings.blocked || []); list.add(uid);
      store.setSettings({ blocked: [...list] });
      renderBlocks();
      toast("차단했어요", "ok");
    } catch (e) { toast(e.message || "차단 실패", "err"); }
  }
  async function unblock(uid) {
    try {
      await api.del(`/privacy/block/${uid}`);
      const list = (store.settings.blocked || []).filter((x) => x !== uid);
      store.setSettings({ blocked: list });
      renderBlocks();
      toast("차단을 해제했어요", "ok");
    } catch (e) { toast(e.message || "해제 실패", "err"); }
  }

  const blockInput = el("input.input", { id: "block-input", placeholder: "차단할 사용자 ID" });
  const blockBtn = el("button.btn", { id: "block-add", text: "차단", onclick: () => { block(blockInput.value); blockInput.value = ""; } });

  mount(
    el("div.stack", {}, [
      el("button.btn.ghost", { text: "← 마이", onclick: () => navigate("/my") }),
      el("h1.h1", { text: "개인정보 보호" }),

      el("div.card", {}, rows),

      el("div.field", {}, [el("label", { text: "기록 기본 공개 범위" }), visSeg]),

      el("div.card", {}, [
        el("div.h2", { text: "차단 목록" }),
        el("div.row", {}, [blockInput, blockBtn]),
        blockList,
      ]),
    ])
  );

  renderBlocks();
}

function switchEl(key, on) {
  const input = el("input", { type: "checkbox", id: `set-${key}` });
  input.checked = !!on;
  input.addEventListener("change", () => {
    store.setSettings({ [key]: input.checked });
    toast("저장됨", "ok");
  });
  const wrap = el("label.switch", {}, [input, el("span.track"), el("span.knob")]);
  return wrap;
}
