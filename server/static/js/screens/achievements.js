// screens/achievements.js — 업적(뱃지) 그리드. 마이 탭 하위 화면.
import { api } from "../api.js";
import { el, mount, toast, setTab, loading, staggerMotion, reducedMotion } from "../ui.js";
import { navigate } from "../router.js";

const FAMILY_ORDER = ["friend", "streak", "quest", "perfect_month", "distance"];

// 패밀리별로 진행도 값을 사람이 읽는 문자열로.
function fmtValue(family, n) {
  if (family === "distance") return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}km`;
  if (family === "streak") return `${n}일`;
  if (family === "perfect_month") return `${n}회`;
  return `${n}회`; // friend, quest
}

export async function achievementsScreen() {
  setTab("my");
  loading();

  let data;
  try {
    data = await api.get("/achievements");
  } catch (e) {
    toast(e.message || "업적을 불러오지 못했어요", "err");
    navigate("/my");
    return;
  }

  const { summary, achievements } = data;
  const groups = new Map();
  for (const fam of FAMILY_ORDER) groups.set(fam, []);
  for (const a of achievements) {
    if (!groups.has(a.family)) groups.set(a.family, []);
    groups.get(a.family).push(a);
  }

  const sections = [];
  for (const [, items] of groups) {
    if (!items.length) continue;
    const label = items[0].family_label;
    const unlockedInFam = items.filter((i) => i.unlocked).length;
    sections.push(
      el("div.ach-section", {}, [
        el("div.ach-section-head", {}, [
          el("span.ach-section-title", { text: label }),
          el("span.ach-section-count", { text: `${unlockedInFam}/${items.length}` }),
        ]),
        el("div.ach-grid", {}, items.map(badgeTile)),
      ])
    );
  }

  const pct = summary.total_count ? Math.round((summary.unlocked_count / summary.total_count) * 100) : 0;

  const wrap = mount(
    el("div.stack", {}, [
      el("div.row", {}, [
        el("button.btn.ghost", { text: "← 마이", onclick: () => navigate("/my") }),
        el("span.spacer"),
      ]),
      el("h1.h1", { text: "업적" }),
      el("div.card.ach-overview", {}, [
        el("div.ach-overview-top", {}, [
          el("div.ach-overview-num", { text: `${summary.unlocked_count}` }),
          el("div.ach-overview-den", { text: `/ ${summary.total_count} 뱃지` }),
        ]),
        el("div.ach-overbar", {}, [el("div.ach-overbar-fill", { style: `width:${pct}%` })]),
      ]),
      ...sections,
      el("div", { style: "height:12px" }),
    ])
  );

  requestAnimationFrame(() => staggerMotion(wrap.querySelectorAll(".ach-tile"), { y: 14, each: 0.02 }));
}

function badgeTile(a) {
  const target = a.threshold;
  const ratio = target ? Math.min(1, a.value / target) : 0;
  const pct = Math.round(ratio * 100);

  const tile = el("div.ach-tile" + (a.unlocked ? ".unlocked" : ".locked"), {
    dataset: { code: a.code },
    title: a.description,
  }, [
    el("div.ach-emoji", { text: a.emoji }),
    el("div.ach-name", { text: a.name }),
    a.unlocked
      ? el("div.ach-status.done", { text: "달성!" })
      : el("div.ach-progress", {}, [
          el("div.ach-bar", {}, [el("div.ach-bar-fill", { style: `width:${pct}%` })]),
          el("div.ach-progress-text", { text: `${fmtValue(a.family, a.value)} / ${fmtValue(a.family, target)}` }),
        ]),
  ]);

  // 탭하면 설명 토스트 (모바일에서 title이 안 보이므로)
  tile.addEventListener("click", () => {
    toast(`${a.emoji} ${a.name} — ${a.description}`, a.unlocked ? "ok" : "");
  });
  return tile;
}
