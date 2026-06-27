// screens/pet_diary.js — 펫일기 작성/상세 (담당: W6, 라우트 #/pet-diary/new · #/pet-diary/:id)
// - #/pet-diary/new?date= : 기분 5단계 + 활동 칩 다중선택 + 텍스트 → POST → #/diary
// - #/pet-diary/:id       : 상세 / 편집(PATCH) / 삭제(DELETE)
// - petDiaryCard(d,{onClick}) : 기록 탭(W5)이 import 하는 표시 카드(이미지4 형태)
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, icon } from "../ui.js";
import { navigate } from "../router.js";

// ── 카탈로그 (스펙 §3) ──────────────────────────────────────────────
// 기분 5단계 — 얼굴 아이콘(Lucide). 코드: happy|good|soso|sad|angry.
const MOODS = [
  { code: "happy", icon: "laugh", label: "행복" },
  { code: "good", icon: "smile", label: "좋음" },
  { code: "soso", icon: "meh", label: "그저그래" },
  { code: "sad", icon: "frown", label: "슬픔" },
  { code: "angry", icon: "angry", label: "화남" },
];

// 활동 태그 — 카테고리별. 코드 prefix 로 백엔드엔 자유 문자열로 저장.
const ACTIVITY_CATALOG = [
  {
    cat: "weather", label: "날씨", items: [
      { code: "weather:sunny", icon: "sun", label: "맑음" },
      { code: "weather:cloudy", icon: "cloud", label: "흐림" },
      { code: "weather:rain", icon: "cloud-rain", label: "비" },
      { code: "weather:snow", icon: "snowflake", label: "눈" },
      { code: "weather:wind", icon: "wind", label: "바람" },
    ],
  },
  {
    cat: "people", label: "사람", items: [
      { code: "people:friend", icon: "users", label: "친구" },
      { code: "people:family", icon: "house", label: "가족" },
      { code: "people:alone", icon: "user", label: "혼자" },
      { code: "people:acquaintance", icon: "handshake", label: "지인" },
      { code: "people:stranger", icon: "user-x", label: "낯선사람" },
    ],
  },
  {
    cat: "meal", label: "식사", items: [
      { code: "meal:breakfast", icon: "coffee", label: "아침" },
      { code: "meal:lunch", icon: "utensils", label: "점심" },
      { code: "meal:dinner", icon: "utensils-crossed", label: "저녁" },
      { code: "meal:snack", icon: "cookie", label: "간식" },
    ],
  },
  {
    cat: "move", label: "이동", items: [
      { code: "move:walk", icon: "footprints", label: "산책" },
      { code: "move:park", icon: "trees", label: "공원" },
      { code: "move:shopping", icon: "shopping-bag", label: "쇼핑" },
      { code: "move:hospital", icon: "stethoscope", label: "병원" },
    ],
  },
];

const MOOD_INDEX = Object.fromEntries(MOODS.map((m) => [m.code, m]));
const ACTIVITY_INDEX = Object.fromEntries(
  ACTIVITY_CATALOG.flatMap((g) => g.items.map((it) => [it.code, it]))
);

// ── 날짜 헬퍼 ───────────────────────────────────────────────────────
function todayStr() {
  const d = new Date();
  const z = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}

function formatDateKo(s) {
  const [y, m, dd] = String(s || "").split("-").map(Number);
  if (!y) return String(s || "");
  return `${y}년 ${m}월 ${dd}일`;
}

// ── 공용 에디터 (작성/편집 공유) ────────────────────────────────────
// state: { mood: string|null, tags: Set<string>, text: string }
function buildForm(state, onChange) {
  const moodRow = el("div.mood-row", { id: "mood-row" },
    MOODS.map((m) => {
      const sel = state.mood === m.code;
      const opt = el("button.mood-opt" + (sel ? ".sel" : ""), {
        type: "button", dataset: { mood: m.code }, "aria-pressed": String(sel),
      }, [
        el("span.mood-face", {}, [icon(m.icon)]),
        el("span.mood-label", { text: m.label }),
      ]);
      opt.addEventListener("click", () => {
        state.mood = m.code;
        moodRow.querySelectorAll(".mood-opt").forEach((n) => {
          const on = n.dataset.mood === m.code;
          n.classList.toggle("sel", on);
          n.setAttribute("aria-pressed", String(on));
        });
        onChange && onChange();
      });
      return opt;
    })
  );

  const sections = ACTIVITY_CATALOG.map((group) =>
    el("div.field.diary-cat", {}, [
      el("label", { text: group.label }),
      el("div.tags.diary-chips", { dataset: { cat: group.cat } },
        group.items.map((it) => {
          const on = state.tags.has(it.code);
          const chip = el("span.tag.diary-chip" + (on ? ".sel" : ""), {
            dataset: { code: it.code }, role: "button", tabindex: "0",
            "aria-pressed": String(on),
          }, [icon(it.icon), el("span", { text: it.label })]);
          chip.addEventListener("click", () => {
            if (state.tags.has(it.code)) { state.tags.delete(it.code); chip.classList.remove("sel"); }
            else { state.tags.add(it.code); chip.classList.add("sel"); }
            chip.setAttribute("aria-pressed", String(state.tags.has(it.code)));
            onChange && onChange();
          });
          return chip;
        })
      ),
    ])
  );

  const textArea = el("textarea.input", {
    id: "diary-text", placeholder: "오늘 있었던 일을 적어보세요 (선택)",
  });
  textArea.value = state.text || "";
  textArea.addEventListener("input", () => { state.text = textArea.value; });

  const node = el("div.stack.gap-lg.diary-form", {}, [
    el("div.field", {}, [el("label", { text: "기분" }), moodRow]),
    ...sections,
    el("div.field", {}, [el("label", { text: "메모 (선택)" }), textArea]),
  ]);

  return { node };
}

// ── 작성 화면 ───────────────────────────────────────────────────────
export async function petDiaryNewScreen(_p, query) {
  setTab("diary");
  const dateStr = (query && query.date) || todayStr();
  const state = { mood: null, tags: new Set(), text: "" };

  const cta = el("button.cta", { id: "diary-save", type: "button", text: "저장", disabled: true });
  const validate = () => { cta.disabled = !state.mood; };
  const form = buildForm(state, validate);

  cta.addEventListener("click", async () => {
    if (!state.mood) return;
    cta.disabled = true; cta.textContent = "저장 중…";
    try {
      await api.post("/pet-diary", {
        pet_id: store.petId || null,
        diary_date: dateStr,
        mood: state.mood,
        activity_tags: [...state.tags],
        text: state.text.trim() || null,
      });
      toast("펫일기를 저장했어요", "ok", "check");
      navigate(`/diary?date=${dateStr}`);
    } catch (e) {
      toast(e.message || "저장 실패", "err");
      cta.disabled = false; cta.textContent = "저장";
    }
  });

  mount(el("div.stack.diary-edit", {}, [
    el("h1.title", { text: "어떤 하루였나요?" }),
    el("p.sub", { text: `${formatDateKo(dateStr)} · 기분과 활동을 기록해요` }),
    form.node,
    cta,
  ]));
  validate();
}

// ── 상세 / 편집 / 삭제 화면 ─────────────────────────────────────────
export async function petDiaryViewScreen(params) {
  setTab("diary");
  const id = params.id;

  let diary;
  try {
    diary = await api.get(`/pet-diary/${id}`);
  } catch (e) {
    toast(e.message || "불러오기 실패", "err");
    mount(el("div.stack", {}, [el("p.empty", { text: "일기를 찾을 수 없어요." })]));
    return;
  }

  renderDetail(diary);

  function renderDetail(d) {
    const mood = MOOD_INDEX[d.mood] || { icon: "smile", label: d.mood };
    const tags = d.activity_tags || [];
    const node = el("div.stack.diary-detail", { id: "diary-detail" }, [
      el("h1.title", { text: "펫일기" }),
      el("div.card.diary-detail-card", {}, [
        el("div.row.diary-detail-head", {}, [
          el("span.mood-face.mood-face-lg", {}, [icon(mood.icon)]),
          el("div.grow", {}, [
            el("div.strong.diary-detail-mood", { text: mood.label }),
            el("div.sub", { text: formatDateKo(d.diary_date) }),
          ]),
        ]),
        tags.length
          ? el("div.diary-detail-acts", {}, tags.map((code) => {
              const a = ACTIVITY_INDEX[code] || { icon: "sparkles", label: code };
              return el("span.diary-act", {}, [icon(a.icon), el("span", { text: a.label })]);
            }))
          : null,
        d.text
          ? el("p.diary-detail-text", { text: d.text })
          : el("p.sub", { text: "작성된 메모가 없어요." }),
      ]),
      el("div.row.gap-sm.diary-actions", {}, [
        el("button.btn.grow", { id: "diary-edit", type: "button" }, [icon("pencil"), el("span", { text: "편집" })]),
        el("button.btn.danger.grow", { id: "diary-delete", type: "button" }, [icon("trash-2"), el("span", { text: "삭제" })]),
      ]),
    ]);
    mount(node);
    node.querySelector("#diary-edit").addEventListener("click", () => renderEdit(d));
    node.querySelector("#diary-delete").addEventListener("click", async () => {
      try {
        await api.del(`/pet-diary/${d.id}`);
        toast("삭제했어요", "ok");
        navigate(`/diary?date=${d.diary_date}`);
      } catch (e) {
        toast(e.message || "삭제 실패", "err");
      }
    });
  }

  function renderEdit(d) {
    const state = { mood: d.mood, tags: new Set(d.activity_tags || []), text: d.text || "" };
    const cta = el("button.cta", { id: "diary-save", type: "button", text: "저장" });
    const validate = () => { cta.disabled = !state.mood; };
    const form = buildForm(state, validate);
    const cancel = el("button.btn.ghost", { id: "diary-cancel", type: "button", text: "취소" });

    cta.addEventListener("click", async () => {
      if (!state.mood) return;
      cta.disabled = true; cta.textContent = "저장 중…";
      try {
        const updated = await api.patch(`/pet-diary/${d.id}`, {
          mood: state.mood,
          activity_tags: [...state.tags],
          text: state.text.trim() || null,
        });
        toast("수정했어요", "ok", "check");
        renderDetail(updated);
      } catch (e) {
        toast(e.message || "수정 실패", "err");
        cta.disabled = false; cta.textContent = "저장";
      }
    });
    cancel.addEventListener("click", () => renderDetail(d));

    mount(el("div.stack.diary-edit", {}, [
      el("h1.title", { text: "펫일기 편집" }),
      el("p.sub", { text: formatDateKo(d.diary_date) }),
      form.node,
      cta,
      cancel,
    ]));
    validate();
  }
}

// ── 표시 카드 규약 (이미지4) — W5가 import 해 재사용 ────────────────
// 기분 이모지 + 활동 아이콘 줄 + 텍스트 한두 줄, 입체 카드.
export function petDiaryCard(d, { onClick } = {}) {
  const mood = MOOD_INDEX[d.mood] || { icon: "smile", label: d.mood };
  const tags = (d.activity_tags || []).slice(0, 6);
  const card = el("div.card.tappable.pet-diary-card", {
    dataset: { diaryId: d.id }, role: "button", tabindex: "0",
  }, [
    el("span.mood-face.pet-diary-mood", {}, [icon(mood.icon)]),
    el("div.grow.pet-diary-body", {}, [
      el("div.row.gap-sm.wrap.pet-diary-acts", {},
        tags.length
          ? tags.map((code) => {
              const a = ACTIVITY_INDEX[code] || { icon: "sparkles", label: code };
              return el("span.pet-diary-act", { title: a.label, "aria-label": a.label }, [icon(a.icon)]);
            })
          : [el("span.sub", { text: mood.label })]),
      el("p.pet-diary-text", { text: d.text || "오늘의 한 줄 기록이 없어요." }),
    ]),
    icon("chevron-right", { cls: "pet-diary-chev" }),
  ]);
  if (onClick) card.addEventListener("click", () => onClick(d));
  return card;
}
