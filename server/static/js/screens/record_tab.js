// screens/record_tab.js — 기록 탭 (W5, 라우트 #/diary). 기록 목록 + 합성영상 재생/다운로드.
import { api } from "../api.js";
import { el, mount, toast, setTab, loading, icon } from "../ui.js";
import { navigate } from "../router.js";

export async function recordTabScreen(_p, query = {}) {
  setTab("diary");
  loading();
  let records = [];
  try { records = (await api.get("/records")).records || []; }
  catch (e) { toast(e.message || "기록을 불러오지 못했어요", "err"); }
  records.sort((a, b) => (String(b.walked_at) > String(a.walked_at) ? 1 : -1));

  if (!records.length) {
    mount(el("div.stack.center", {}, [
      el("div.emoji-xl", {}, [icon("paw-print")]),
      el("h1.h1", { text: "아직 기록이 없어요" }),
      el("p.sub", { text: "산책하고 2초 클립을 찍어 첫 기록을 만들어요." }),
      el("button.cta", { text: "산책하러 가기", onclick: () => navigate("/home") }),
    ]));
    return;
  }

  const cards = records.map(recordCard);
  mount(el("div.stack", {}, [el("h1.h1", { text: "기록" }), ...cards]));
}

function recordCard(rec) {
  const clipN = (rec.clips || []).length;
  const media = el("div.rec-media");
  const dl = clipN ? el("button.btn", { text: "⬇️ 영상 다운로드" }) : null;
  if (dl) dl.addEventListener("click", async () => {
    dl.disabled = true; const t = dl.textContent; dl.textContent = "준비 중…";
    try {
      await api.download(`/records/${rec.id}/video/download`, `letspaw_${rec.walked_at || "walk"}.mp4`);
      toast("영상을 저장했어요", "ok", "film");
    } catch (e) {
      toast(e.status === 409 ? "영상을 합치는 중이에요. 잠시 후 다시 시도해 주세요" : (e.message || "다운로드 실패"), "err");
    } finally { dl.disabled = false; dl.textContent = t; }
  });

  // 합성 영상이 준비되면 인라인 재생(다운로드 엔드포인트를 blob으로)
  if (rec.merged_ready) {
    api.blobUrl(`/records/${rec.id}/video/download`).then((url) => {
      const v = el("video", { src: url, controls: "", playsinline: "", loop: "", muted: "" });
      v.muted = true; media.innerHTML = ""; media.append(v);
    }).catch(() => { media.append(el("span.sub", { text: `${clipN}컷 · 합성 대기 중` })); });
  } else if (clipN) {
    media.append(el("span.sub", { text: `${clipN}컷 · 영상 합치는 중…` }));
  }

  return el("div.card.stack.gap-sm", {}, [
    el("div.row.between", {}, [
      el("span.strong", { text: rec.walked_at || "산책 기록" }),
      el("span.sub", { text: `${clipN}컷` }),
    ]),
    clipN ? media : null,
    rec.text ? el("p.sub", { text: rec.text }) : null,
    dl,
  ].filter(Boolean));
}
