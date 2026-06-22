// screens/league.js — SCR-40 랭킹(주간 리그) + 업적 진입. 하단 "랭킹" 탭.
import { api } from "../api.js";
import { el, mount, toast, setTab, loading, staggerMotion, icon } from "../ui.js";
import { navigate } from "../router.js";

export async function leagueScreen() {
  setTab("league");
  loading();

  let lg = null, ach = null;
  try {
    lg = await api.get("/leagues/me");
  } catch (e) {
    toast(e.message || "랭킹을 불러오지 못했어요", "err");
  }
  try { ach = await api.get("/achievements"); } catch (_) {}

  if (!lg) {
    mount(el("div.stack", {}, [
      el("h1.h1", { text: "랭킹" }),
      el("div.empty", {}, [el("div.big", {}, [icon("trophy")]), el("p", { text: "랭킹을 불러오지 못했어요." })]),
    ]));
    return;
  }

  const zoneHint = lg.tier === "master"
    ? "최고 리그예요. 순위를 지켜요!"
    : `상위 ${lg.promote_rank_max}위 안에 들면 다음 리그로 승급!`;

  const wrap = mount(
    el("div.stack", {}, [
      el("h1.h1", { text: "랭킹" }),

      // 리그 헤더
      el("div.card.league-head", {}, [
        el("div.league-emoji", { text: lg.tier_emoji }),
        el("div.grow", {}, [
          el("div.league-tier", { text: `${lg.tier_label} 리그` }),
          el("div.sub", { text: `${lg.week_key} · ${lg.cohort_size}명 중` }),
        ]),
        el("div.league-myrank", {}, [
          el("div.v", { text: `${lg.my_rank}위` }),
          el("div.k", { text: `${lg.my_points}점` }),
        ]),
      ]),
      el("div.league-hint", { text: zoneHint }),

      // 리더보드
      el("div.league-board", {}, buildBoard(lg)),

      // 업적 진입
      achievementsBlock(ach),
    ])
  );

  requestAnimationFrame(() => staggerMotion(wrap.querySelectorAll(".lb-row"), { y: 10, each: 0.015 }));
}

function buildBoard(lg) {
  const rows = [];
  lg.entries.forEach((e, i) => {
    // 승급/강등 경계선
    if (lg.promote_rank_max && e.rank === lg.promote_rank_max + 1) {
      rows.push(el("div.lb-divider.promote", {}, [icon("arrow-up"), " 승급권"]));
    }
    if (lg.demote_rank_min <= lg.cohort_size && e.rank === lg.demote_rank_min) {
      rows.push(el("div.lb-divider.demote", {}, [icon("arrow-down"), " 강등권"]));
    }
    rows.push(
      el("div.lb-row" + (e.is_me ? ".me" : "") + `.zone-${e.zone}`, {}, [
        el("span.lb-rank", { text: String(e.rank) }),
        el("span.lb-medal", { text: e.rank <= 3 ? ["🥇", "🥈", "🥉"][e.rank - 1] : "" }),
        el("span.lb-name", { text: e.name + (e.is_me ? " (나)" : "") }),
        el("span.lb-pts", { text: `${e.points}점` }),
      ])
    );
  });
  return rows;
}

function achievementsBlock(ach) {
  const summary = ach?.summary;
  const items = ach?.achievements || [];
  const preview = items.slice(0, 10); // 컬러(달성)/회색(미달성) 미리보기
  const count = summary ? `${summary.unlocked_count}/${summary.total_count}` : "—";

  return el("div.card.tappable.ach-card", { onclick: () => navigate("/achievements") }, [
    el("div.ach-card-head", {}, [
      el("span.ach-card-title", {}, [icon("award"), " 업적"]),
      el("span.spacer"),
      el("span.ach-card-count", { text: count }),
    ]),
    el("div.ach-card-sub", { text: "달성한 뱃지는 컬러, 잠긴 뱃지는 회색으로 보여요" }),
    el("div.ach-card-strip", {}, preview.length
      ? preview.map((a) => el("span.ach-card-emoji" + (a.unlocked ? "" : ".dim"), { text: a.emoji, title: a.name }))
      : [el("span.ach-card-emoji.dim", {}, [icon("paw-print")])]),
    el("button.btn.secondary.ach-card-action", { id: "see-all-ach", text: "모든 업적 보기", onclick: (ev) => { ev.stopPropagation(); navigate("/achievements"); } }),
  ]);
}
