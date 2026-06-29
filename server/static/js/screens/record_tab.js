// screens/record_tab.js — 기록 탭 재설계 (담당: W5, 라우트 #/diary)
// 손그림 이미지3·4: 상단 둥근 [기록] 칩 → 캘린더/공유 토글, 선택 날짜의 내 기록영상 +
// (매칭이면 신규 API로) 상대 기록영상 썸네일, 하단 펫일기 섹션(W6 petDiaryCard),
// 좌우 스와이프로 날짜 이동(영상+펫일기 동시 갱신). 방 버튼/공유옵션 없음.
import { api } from "../api.js";
import { el, mount, setTab, icon, toast, centerModal, onLeave } from "../ui.js";
import { navigate } from "../router.js";
import { petDiaryCard } from "./pet_diary.js";

// ── 날짜 헬퍼 (로컬 기준 ymd) ──────────────────────────────────────
function ymd(d) {
  const z = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}
function todayStr() { return ymd(new Date()); }
function parseYmd(s) {
  const [y, m, d] = String(s).split("-").map(Number);
  return new Date(y || 1970, (m || 1) - 1, d || 1);
}
function shiftYmd(s, delta) {
  const d = parseYmd(s);
  d.setDate(d.getDate() + delta);
  return ymd(d);
}
function isYmd(s) { return /^\d{4}-\d{2}-\d{2}$/.test(String(s || "")); }
function formatDateKo(s) {
  const [y, m, dd] = String(s || "").split("-").map(Number);
  if (!y) return String(s || "");
  return `${y}년 ${m}월 ${dd}일`;
}

export async function recordTabScreen(_p, query) {
  setTab("diary");
  const state = { date: query && isYmd(query.date) ? query.date : todayStr() };

  // 인증 Blob video URL 추적 → 화면 떠날 때/재조회 시 해제 (메모리 누수 방지)
  let blobUrls = [];
  const revokeUrls = () => {
    blobUrls.forEach((u) => { try { URL.revokeObjectURL(u); } catch (_) {} });
    blobUrls = [];
  };
  onLeave(revokeUrls);

  let renderSeq = 0;

  // ── 상단 바: 둥근 [기록] 칩 → 캘린더/공유 토글 ──────────────────
  const pill = el("button.record-pill", {
    type: "button", id: "record-pill", "aria-expanded": "false", "aria-label": "기록 메뉴",
  }, [icon("notebook"), el("span", { text: "기록" }), icon("chevron-down", { cls: "record-pill-caret" })]);

  const calOpt = el("button.record-toggle-opt", {
    type: "button", dataset: { toggle: "calendar" },
  }, [icon("calendar"), el("span", { text: "캘린더" })]);
  const shareOpt = el("button.record-toggle-opt.is-disabled", {
    type: "button", dataset: { toggle: "share" }, disabled: true, "aria-disabled": "true",
  }, [icon("share-2"), el("span", { text: "공유" })]);
  const toggle = el("div.record-toggle.hidden", { id: "record-toggle", role: "menu" }, [calOpt, shareOpt]);

  const dateLabel = el("span.record-date", { id: "record-date", text: formatDateKo(state.date) });

  const closeToggle = () => { toggle.classList.add("hidden"); pill.setAttribute("aria-expanded", "false"); };
  pill.addEventListener("click", (e) => {
    e.stopPropagation();
    const opened = !toggle.classList.toggle("hidden");
    pill.setAttribute("aria-expanded", String(opened));
  });
  calOpt.addEventListener("click", () => { closeToggle(); openCalendar(); });
  // 공유는 비활성(자리만) — 클릭해도 "준비 중" 토스트만.
  shareOpt.addEventListener("click", () => toast("공유는 준비 중이에요", "", "construction"));

  const onDocClick = (e) => {
    if (toggle.classList.contains("hidden")) return;
    if (toggle.contains(e.target) || pill.contains(e.target)) return;
    closeToggle();
  };
  document.addEventListener("click", onDocClick);
  onLeave(() => document.removeEventListener("click", onDocClick));

  const topbar = el("div.row.record-topbar", {}, [
    el("div.record-pill-wrap", {}, [pill, toggle]),
    el("span.spacer"),
    dateLabel,
  ]);

  const body = el("div.stack.record-body", { id: "record-body" });
  const root = el("div.stack.record-tab", { id: "record-tab" }, [topbar, body]);

  // ── 좌우 스와이프(포인터/터치 공용) → 날짜 ±1일 ────────────────
  // 왼쪽으로 밀면 다음 날, 오른쪽으로 밀면 이전 날. 가로 우세 + 임계값 50px.
  let px = null, py = null;
  root.addEventListener("pointerdown", (e) => { px = e.clientX; py = e.clientY; });
  root.addEventListener("pointerup", (e) => {
    if (px == null) return;
    const dx = e.clientX - px, dy = e.clientY - py;
    px = null;
    if (Math.abs(dx) < 50 || Math.abs(dx) <= Math.abs(dy)) return;
    goToDate(shiftYmd(state.date, dx < 0 ? 1 : -1));
  });

  mount(root);
  await renderBody();

  // ── 날짜 변경 → 영상 + 펫일기 동시 갱신 ────────────────────────
  function goToDate(next) {
    if (!next || next === state.date) return;
    state.date = next;
    renderBody();
  }

  async function renderBody() {
    closeToggle();
    const seq = ++renderSeq;
    revokeUrls();
    const date = state.date;
    dateLabel.textContent = formatDateKo(date);
    body.dataset.date = date;
    body.innerHTML = "";

    const videoSection = el("section.record-section.record-videos", { id: "record-videos", dataset: { date } }, [
      el("h2.h2", { text: "내 기록 영상" }),
      el("p.sub.record-loading", { text: "불러오는 중…" }),
    ]);
    const diarySection = el("section.record-section.record-diary", { id: "record-diary", dataset: { date } }, [
      el("h2.h2", { text: "펫일기" }),
      el("p.sub.record-loading", { text: "불러오는 중…" }),
    ]);
    body.append(videoSection, diarySection);

    let records = [], diaries = [];
    try {
      const [recRes, diaryRes] = await Promise.all([
        api.get(`/records?from=${date}&to=${date}`),
        api.get(`/pet-diary?date=${date}`),
      ]);
      records = (recRes.records || []).filter((r) => r.visibility === "diary");
      diaries = diaryRes.diaries || [];
    } catch (e) {
      if (seq === renderSeq) toast(e.message || "기록을 불러오지 못했어요", "err");
    }
    if (seq !== renderSeq) return;

    await renderVideos(videoSection, records, seq);
    if (seq !== renderSeq) return;
    renderDiary(diarySection, diaries, date);
  }

  // ── 영상 기록 영역: 내 기록 + (매칭이면) 상대 기록 ──────────────
  async function renderVideos(section, records, seq) {
    section.innerHTML = "";
    section.append(el("h2.h2", { text: "내 기록 영상" }));

    // 합성된 가로(16:9) 영상을 크게 재생 + 우상단 작은 다운로드 아이콘.
    const myRecords = records.filter((r) => (r.clips || []).length);
    if (!myRecords.length) {
      section.append(el("p.sub.record-empty", { text: "이 날의 기록 영상이 없어요." }));
    } else {
      // 한 행에 2개씩 그리드. 듀얼이면 합성 영상에 두 사람이 함께 담겨 있다(상대 기록 별도 노출 X).
      const grid = el("div.record-video-grid");
      for (const r of myRecords) grid.append(buildRecordVideo(r, seq));
      section.append(grid);
    }
  }

  // 한 기록 = 합성 가로영상 한 편(autoplay/loop) + 우상단 작은 다운로드 아이콘
  function buildRecordVideo(r, seq) {
    const frame = el("div.record-video-frame", {}, [el("span.record-video-loading", {}, [icon("film")])]);
    const dl = el("button.record-video-dl", { type: "button", "aria-label": "영상 다운로드", title: "영상 다운로드", text: "↓" });
    dl.addEventListener("click", async (e) => {
      e.stopPropagation();
      dl.disabled = true;
      try {
        await api.download(`/records/${r.id}/video/download`, `letspaw_${r.walked_at || "walk"}.mp4`);
        toast("영상을 저장했어요", "ok", "film");
      } catch (err) {
        toast(err.status === 409 ? "영상을 합치는 중이에요. 잠시 후 다시 시도해 주세요" : (err.message || "다운로드 실패"), "err");
      } finally { dl.disabled = false; }
    });
    const del = el("button.record-video-del", { type: "button", "aria-label": "기록 삭제", title: "기록 삭제" }, [icon("trash-2")]);
    del.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!window.confirm("이 기록과 합성 영상을 삭제할까요? 되돌릴 수 없어요.")) return;
      del.disabled = true;
      try {
        await api.del(`/records/${r.id}`);
        toast("기록을 삭제했어요", "ok", "trash-2");
        renderBody();
      } catch (err) {
        toast(err.message || "삭제에 실패했어요", "err");
        del.disabled = false;
      }
    });
    const outer = el("div.record-video", { dataset: { recId: r.id } }, [frame, dl, del]);
    // 합성은 백그라운드라 기록 직후엔 아직 안 끝나 있다(다운로드 409). 완료될 때까지
    // 폴링 재시도 → 새로고침 없이 자동 반영. seq가 바뀌면(날짜 이동/이탈) 멈춘다.
    loadRecordVideo(frame, r, seq, 0);
    return outer;
  }

  function loadRecordVideo(frame, r, seq, attempt) {
    if (seq !== renderSeq) return;
    api.blobUrl(`/records/${r.id}/video/download`).then((url) => {
      if (seq !== renderSeq) { try { URL.revokeObjectURL(url); } catch (_) {} return; }
      blobUrls.push(url);
      const v = el("video", { src: url, autoplay: "", loop: "", muted: "", playsinline: "" });
      v.muted = true;
      frame.innerHTML = ""; frame.append(v);
    }).catch((err) => {
      if (seq !== renderSeq) return;
      // 409=합성 중, 0=일시 네트워크 → 완료까지 재시도(최대 ~2.5분). 그 외엔 중단.
      const retriable = !err || err.status === 409 || err.status === 0;
      if (retriable && attempt < 60) {
        frame.innerHTML = "";
        frame.append(
          el("span.record-video-loading", {}, [icon("film")]),
          el("span.sub.record-video-merging", { text: "영상을 합치는 중이에요…" }),
        );
        setTimeout(() => loadRecordVideo(frame, r, seq, attempt + 1), 2500);
      } else {
        frame.innerHTML = ""; frame.append(el("span.sub", { text: "영상을 불러오지 못했어요" }));
      }
    });
  }

  function buildThumbStrip(clips, id, emptyText, seq) {
    const strip = el("div.record-thumb-strip", { id });
    if (!clips.length) {
      strip.append(el("p.sub.record-empty", { text: emptyText }));
      return strip;
    }
    for (const c of clips) {
      const thumb = el("div.record-thumb", { dataset: { clipId: c.id } }, [
        el("span.record-thumb-fallback", {}, [icon("film")]),
      ]);
      loadThumb(thumb, c, seq);
      strip.append(thumb);
    }
    return strip;
  }

  async function loadThumb(thumb, clip, seq) {
    try {
      const url = await api.blobUrl(clip.stream_url.replace("/api", ""));
      if (seq !== renderSeq) { try { URL.revokeObjectURL(url); } catch (_) {} return; }
      blobUrls.push(url);
      const v = el("video.record-thumb-video", { src: url, playsinline: "", muted: "", preload: "metadata" });
      v.muted = true;
      thumb.querySelector(".record-thumb-fallback")?.remove();
      thumb.append(v);
    } catch (_) { /* fallback 필름 아이콘 유지 */ }
  }

  // ── 펫일기 섹션: 없으면 빈 상태 + 작성 진입, 있으면 W6 카드 ──────
  function renderDiary(section, diaries, date) {
    section.innerHTML = "";
    section.append(el("h2.h2", { text: "펫일기" }));
    if (!diaries.length) {
      section.append(el("div.empty.record-diary-empty", {}, [
        el("p", { text: "일기가 없어요." }),
        el("button.btn.secondary", {
          type: "button", id: "diary-write",
          onclick: () => navigate(`/pet-diary/new?date=${date}`),
        }, [icon("plus"), el("span", { text: "펫일기 작성" })]),
      ]));
      return;
    }
    diaries.forEach((d) =>
      section.append(petDiaryCard(d, { onClick: (dd) => navigate(`/pet-diary/${dd.id}`) }))
    );
  }

  // ── 캘린더 팝업(centerModal): 날짜 점프 ────────────────────────
  function openCalendar() {
    const monthCache = {}; // 월별 기록 날짜 Set 캐시
    let cur = parseYmd(state.date);
    cur = new Date(cur.getFullYear(), cur.getMonth(), 1);
    centerModal((close) => {
      const title = el("div.record-cal-title");
      const grid = el("div.record-cal-grid");
      const head = el("div.row.record-cal-head", {}, [
        el("button.record-cal-nav", {
          type: "button", "aria-label": "이전 달",
          onclick: () => { cur.setMonth(cur.getMonth() - 1); paint(); },
        }, [icon("chevron-left")]),
        el("span.spacer"), title, el("span.spacer"),
        el("button.record-cal-nav", {
          type: "button", "aria-label": "다음 달",
          onclick: () => { cur.setMonth(cur.getMonth() + 1); paint(); },
        }, [icon("chevron-right")]),
      ]);
      const week = el("div.record-cal-grid.record-cal-week", {},
        ["일", "월", "화", "수", "목", "금", "토"].map((w) => el("span.record-cal-dow", { text: w })));
      const wrap = el("div.record-cal", {}, [el("h2.h2", { text: "날짜 선택" }), head, week, grid]);
      paint();
      return wrap;

      function paint() {
        const y = cur.getFullYear(), m = cur.getMonth();
        title.textContent = `${y}년 ${m + 1}월`;
        grid.innerHTML = "";
        const startDow = new Date(y, m, 1).getDay();
        const daysInMonth = new Date(y, m + 1, 0).getDate();
        for (let i = 0; i < startDow; i++) grid.append(el("span.record-cal-cell.is-empty"));
        for (let d = 1; d <= daysInMonth; d++) {
          const cellYmd = ymd(new Date(y, m, d));
          let sel = "button.record-cal-cell";
          if (cellYmd === todayStr()) sel += ".is-today";
          if (cellYmd === state.date) sel += ".is-selected";
          const cell = el(sel, { type: "button", dataset: { date: cellYmd }, text: String(d) });
          cell.addEventListener("click", () => { close(); goToDate(cellYmd); });
          grid.append(cell);
        }
        grid.dataset.month = `${y}-${m}`;
        markRecorded(y, m);
      }

      // 기록 있는 날에 점 표시(월 단위로 /records 조회 후 캐시)
      async function markRecorded(y, m) {
        const key = `${y}-${m}`;
        const z = (n) => String(n).padStart(2, "0");
        const from = `${y}-${z(m + 1)}-01`;
        const to = `${y}-${z(m + 1)}-${z(new Date(y, m + 1, 0).getDate())}`;
        let dates = monthCache[key];
        if (!dates) {
          try {
            const res = await api.get(`/records?from=${from}&to=${to}`);
            dates = new Set((res.records || []).filter((r) => r.visibility === "diary").map((r) => String(r.walked_at)));
            monthCache[key] = dates;
          } catch (_) { return; }
        }
        if (grid.dataset.month !== key) return; // 그 사이 달 이동
        grid.querySelectorAll(".record-cal-cell[data-date]").forEach((c) => {
          if (dates.has(c.dataset.date)) c.classList.add("has-rec");
        });
      }
    });
  }
}
