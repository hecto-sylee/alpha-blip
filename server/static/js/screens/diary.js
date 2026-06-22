// screens/diary.js — SCR-21 다이어리(캘린더+스탯) · SCR-22 기록 상세 (F-10).
import { api } from "../api.js";
import { el, mount, toast, setTab, loading, springMotion, staggerMotion, reducedMotion, icon } from "../ui.js";
import { navigate } from "../router.js";

const DOW = ["일", "월", "화", "수", "목", "금", "토"];

function ymd(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; }

// ---------------- SCR-21 다이어리 ----------------
export async function diaryScreen(_params = {}, query = {}) {
  setTab("diary");
  loading();
  let records = [];
  try { records = (await api.get("/records")).records || []; }
  catch (e) { toast(e.message || "기록을 불러오지 못했어요", "err"); }

  // diary(개인) 기록만 캘린더에
  const diary = records.filter((r) => r.visibility === "diary");

  // stats
  const totalDist = diary.reduce((s, r) => s + (r.distance_meters || 0), 0);
  const count = diary.length;
  const streak = computeStreak(diary);

  const stats = el("div.stats", {}, [
    stat(totalDist / 1000, "누적 거리", { suffix: "km", decimals: 1 }),
    stat(count, "산책 기록"),
    stat(streak, "연속", { suffix: "일", highlight: true }),
  ]);

  // calendar (이번 달)
  const now = new Date();
  const byDate = new Map();
  diary.forEach((r) => { if (r.walked_at) byDate.set(r.walked_at, (byDate.get(r.walked_at) || 0) + 1); });
  const cal = buildCalendar(now, byDate);
  const playSavedSettle = query.saved === "1" || sessionStorage.getItem("blip_record_saved_motion") === "1";

  // 최근 기록 리스트
  const fab = el("button.fab", { id: "fab-record", title: "기록하기", onclick: () => navigate("/record") }, [icon("camera")]);

  const list = diary.length
    ? el("div.stack", {}, diary.slice(0, 30).map(recordItem))
    : el("div.empty", {}, [el("div.big", {}, [icon("notebook")]), el("p", { text: "아직 기록이 없어요." }), el("button.btn", { text: "첫 기록 남기기", onclick: () => navigate("/record") })]);

  const wrap = mount(
    el("div.stack", {}, [
      el("div.row", {}, [el("h1.h1", { text: "다이어리" }), el("span.spacer"), el("button.btn", { id: "go-rooms", onclick: () => navigate("/rooms") }, [icon("users"), " 방"])]),
      stats,
      cal,
      el("div.h2", { text: "최근 기록" }),
      list,
      fab,
    ])
  );
  if (playSavedSettle) {
    sessionStorage.removeItem("blip_record_saved_motion");
    cal.dataset.settle = reducedMotion() ? "reduced" : "calendar";
    requestAnimationFrame(() => {
      springMotion(cal, { y: -10, scale: 0.97 });
      const today = cal.querySelector(".cal-cell.today") || cal.querySelector(".cal-cell.has");
      if (today) springMotion(today, { y: -6, scale: 0.86, delay: 0.06 });
      const latest = wrap.querySelector(".rec-item")?.closest(".card");
      if (latest) springMotion(latest, { y: 16, scale: 0.96, delay: 0.08 });
    });
  } else {
    requestAnimationFrame(() => staggerMotion(wrap.querySelectorAll(".rec-item"), { y: 12, each: 0.04 }));
  }
  requestAnimationFrame(() => animateStats(stats));
}

function stat(value, label, opts = {}) {
  const decimals = opts.decimals || 0;
  const suffix = opts.suffix || "";
  const finalText = formatStat(value, decimals, suffix);
  const startText = reducedMotion() ? finalText : formatStat(0, decimals, suffix);
  return el("div.stat" + (opts.highlight ? ".streak" : ""), {
    dataset: {
      countupTarget: String(value),
      countupDecimals: String(decimals),
      countupSuffix: suffix,
    },
  }, [
    el("div.v", { text: startText }),
    el("div.k", { text: label }),
  ]);
}

function formatStat(value, decimals, suffix) {
  const n = Number(value) || 0;
  const text = decimals ? n.toFixed(decimals) : String(Math.round(n));
  return text + suffix;
}

function animateStats(root) {
  const nodes = Array.from(root.querySelectorAll("[data-countup-target]"));
  if (!nodes.length || reducedMotion()) {
    nodes.forEach((node) => {
      const v = node.querySelector(".v");
      if (v) v.textContent = formatStat(node.dataset.countupTarget, Number(node.dataset.countupDecimals || 0), node.dataset.countupSuffix || "");
    });
    return;
  }
  const duration = 780;
  const start = performance.now();
  const tick = (now) => {
    const p = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - p, 3);
    nodes.forEach((node) => {
      const v = node.querySelector(".v");
      if (!v) return;
      const target = Number(node.dataset.countupTarget || 0);
      const decimals = Number(node.dataset.countupDecimals || 0);
      const suffix = node.dataset.countupSuffix || "";
      v.textContent = formatStat(target * eased, decimals, suffix);
    });
    if (p < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function computeStreak(diary) {
  const days = new Set(diary.map((r) => r.walked_at).filter(Boolean));
  if (!days.size) return 0;
  let streak = 0;
  const d = new Date();
  // 오늘 기록이 없으면 어제부터 카운트
  if (!days.has(ymd(d))) d.setDate(d.getDate() - 1);
  while (days.has(ymd(d))) { streak++; d.setDate(d.getDate() - 1); }
  return streak;
}

function buildCalendar(now, byDate) {
  const y = now.getFullYear(), m = now.getMonth();
  const first = new Date(y, m, 1);
  const startDow = first.getDay();
  const daysInMonth = new Date(y, m + 1, 0).getDate();
  const todayStr = ymd(now);

  const grid = el("div.cal-grid");
  DOW.forEach((d) => grid.append(el("div.dow", { text: d })));
  for (let i = 0; i < startDow; i++) grid.append(el("div.cal-cell", {}));
  for (let day = 1; day <= daysInMonth; day++) {
    const ds = `${y}-${String(m + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const has = byDate.has(ds);
    const cell = el("div.cal-cell" + (has ? ".has" : "") + (ds === todayStr ? ".today" : ""), { text: String(day) });
    grid.append(cell);
  }

  return el("div.cal", {}, [
    el("div.cal-head", {}, [el("span", { text: `${y}년 ${m + 1}월` })]),
    grid,
  ]);
}

function recordItem(r) {
  const thumb = el("div.rec-thumb", {}, [icon(r.clips && r.clips.length ? "film" : "file-text")]);
  const card = el("div.card.tappable", { dataset: { rid: r.id }, onclick: () => navigate(`/record/${r.id}`) }, [
    el("div.rec-item", {}, [
      thumb,
      el("div.grow", {}, [
        el("div.strong", { text: r.walked_at || "" }),
        el("div.sub", { text: (r.text || "기록").slice(0, 30) }),
        el("div.sub", { text: `클립 ${r.clips ? r.clips.length : 0}개${r.daily_quest_id ? " · 퀘스트" : ""}` }),
      ]),
    ]),
  ]);
  return card;
}

// ---------------- SCR-22 기록 상세 ----------------
export async function recordViewScreen(params) {
  setTab("diary");
  loading();
  let rec;
  try { rec = await api.get(`/records/${params.id}`); }
  catch (e) { toast(e.message || "기록을 불러오지 못했어요", "err"); navigate("/diary"); return; }

  // 클립 재생 (인증 Blob)
  const clipsWrap = el("div.clip-strip", {});
  for (const c of rec.clips || []) {
    const chip = el("div.clip-chip", { dataset: { clipId: c.id } });
    try {
      const url = await api.blobUrl(c.stream_url.replace("/api", ""));
      const v = el("video", { src: url, controls: "", playsinline: "", muted: "" }); v.muted = true;
      chip.append(v);
    } catch { chip.append(icon("film")); }
    clipsWrap.append(chip);
  }
  if (!rec.clips || !rec.clips.length) clipsWrap.append(el("p.sub", { text: "클립 없음" }));

  const delBtn = el("button.btn.danger", { id: "del-record", text: "삭제" });
  delBtn.addEventListener("click", async () => {
    if (!confirm("이 기록을 삭제할까요?")) return;
    try { await api.del(`/records/${rec.id}`); toast("삭제했어요"); navigate("/diary"); }
    catch (e) { toast(e.message, "err"); }
  });

  const textArea = el("textarea.input", { id: "edit-text" }); textArea.value = rec.text || "";
  const saveBtn = el("button.btn.secondary", { id: "save-edit", text: "메모 저장" });
  saveBtn.addEventListener("click", async () => {
    try { await api.patch(`/records/${rec.id}`, { text: textArea.value }); toast("저장했어요", "ok"); }
    catch (e) { toast(e.message, "err"); }
  });

  mount(
    el("div.stack", { id: "record-view" }, [
      el("div.row", {}, [
        el("button.btn.ghost", { text: "← 다이어리", onclick: () => navigate("/diary") }),
        el("span.spacer"),
        el("span.badge", {}, [icon(rec.visibility === "room" ? "users" : "notebook"), rec.visibility === "room" ? " 방 공유" : " 일기"]),
      ]),
      el("h1.h1", { text: rec.walked_at || "산책 기록" }),
      el("div.sub", { text: `${rec.duration_minutes ? rec.duration_minutes + "분 · " : ""}${rec.distance_meters ? (rec.distance_meters / 1000).toFixed(1) + "km" : ""}` }),
      clipsWrap,
      el("div.field", {}, [el("label", { text: "메모" }), textArea]),
      el("div.row", {}, [saveBtn, el("span.spacer"), delBtn]),
    ])
  );
}
