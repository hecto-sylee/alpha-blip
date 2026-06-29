// screens/shop.js — 포인트 상점 + 강아지 꾸미기(장착)
import { api } from "../api.js";
import { el, mount, toast, setTab, loading } from "../ui.js";
import { navigate } from "../router.js";
import { dogSVG, ensureDogStyles } from "../dog/render.js";
import { resolveAppearance } from "../dog/params.js";
import { shareDog } from "../dog/share.js";

export async function shopScreen() {
  setTab("my");
  loading();
  ensureDogStyles();

  let shop, me;
  try {
    [shop, me] = await Promise.all([api.get("/shop"), api.get("/auth/me")]);
  } catch (e) { toast(e.message || "상점을 불러오지 못했어요", "err"); return; }

  const pet = me?.pets?.[0] || null;
  const base = resolveAppearance(pet || {});
  let points = shop.points || 0;
  const slotOf = Object.fromEntries(shop.items.map((i) => [i.key, i.slot]));
  const owned = new Set(shop.items.filter((i) => i.owned).map((i) => i.key));
  const equipped = new Set(Array.isArray(base.equipped) ? base.equipped : []);

  const preview = el("div.shop-preview");
  const balance = el("div.shop-balance");
  const renderPreview = () => { preview.innerHTML = dogSVG({ ...base, equipped: [...equipped] }, { pose: "front", size: 150, anim: true }); };
  const renderBalance = () => { balance.textContent = `🦴 ${points} 포인트`; };

  async function saveEquip() {
    if (!pet) { toast("먼저 강아지를 등록해 주세요", "err"); return; }
    try { await api.patch(`/pets/${pet.id}`, { appearance: { ...base, equipped: [...equipped] } }); }
    catch (e) { toast(e.message || "저장 실패", "err"); }
  }

  const cards = [];
  function refreshAll() { cards.forEach((c) => c.refresh()); }

  function makeCard(item) {
    const thumb = el("div.shop-thumb");
    thumb.innerHTML = dogSVG({ ...base, equipped: [item.key] }, { pose: "front", size: 66, anim: false });
    const btn = el("button.shop-btn", { type: "button" });
    const card = el("div.shop-item", {}, [
      thumb,
      el("div.shop-name", { text: item.name }),
      btn,
    ]);

    function refresh() {
      const own = owned.has(item.key);
      const eq = equipped.has(item.key);
      card.classList.toggle("owned", own);
      card.classList.toggle("equipped", eq);
      btn.className = "shop-btn";
      if (!own) {
        btn.textContent = `🦴 ${item.cost}`;
        btn.disabled = points < item.cost;
        if (points < item.cost) btn.classList.add("locked");
      } else if (eq) {
        btn.textContent = "착용 중 ✓"; btn.classList.add("on"); btn.disabled = false;
      } else {
        btn.textContent = "입히기"; btn.classList.add("equip"); btn.disabled = false;
      }
    }

    btn.addEventListener("click", async () => {
      if (!owned.has(item.key)) {
        btn.disabled = true;
        try {
          const res = await api.post("/shop/buy", { item_key: item.key });
          points = res.points;
          res.items.filter((i) => i.owned).forEach((i) => owned.add(i.key));
          toast(`${item.name} 구매 완료!`, "ok");
          renderBalance(); refreshAll();
        } catch (e) { toast(e.message || "구매 실패", "err"); refresh(); }
      } else {
        if (equipped.has(item.key)) {
          equipped.delete(item.key);
        } else {
          // 같은 슬롯의 다른 아이템은 벗기고 교체(슬롯당 1개)
          [...equipped].forEach((k) => { if (slotOf[k] === item.slot) equipped.delete(k); });
          equipped.add(item.key);
        }
        renderPreview(); refreshAll(); saveEquip();
      }
    });

    refresh();
    cards.push({ refresh });
    return card;
  }

  const grid = el("div.shop-grid", {}, shop.items.map(makeCard));

  mount(
    el("div.stack", {}, [
      el("div.row.between", {}, [
        el("button.btn.ghost", { text: "← 마이", onclick: () => navigate("/my") }),
        balance,
      ]),
      el("h1.h1", { text: "🛍️ 상점" }),
      el("p.sub", { text: "퀘스트 산책으로 포인트를 모아 강아지를 꾸며요." }),
      el("div.shop-stage", {}, [preview]),
      el("button.btn.share-btn", {
        text: "📤 우리 강아지 공유하기",
        onclick: async (e) => {
          const btn = e.currentTarget; btn.disabled = true;
          try {
            const how = await shareDog({ ...base, equipped: [...equipped] }, pet?.name || "우리 강아지");
            toast(how === "shared" ? "공유했어요" : "이미지를 저장했어요", "ok");
          } catch (err) { toast("공유 실패", "err"); }
          finally { btn.disabled = false; }
        },
      }),
      grid,
    ])
  );

  renderPreview();
  renderBalance();
}
