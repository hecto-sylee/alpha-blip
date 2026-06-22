// screens/room_view.js — SCR-25 방 상세 (타임라인·반응·멤버·기록올리기) (F-11)
import { api } from "../api.js";
import { store } from "../store.js";
import { el, mount, toast, setTab, loading, bottomSheet, icon } from "../ui.js";
import { navigate } from "../router.js";

const EMOJIS = ["❤️", "😂", "🔥", "👍", "😮"]; // 반응 이모지(데이터성) — 유지
const MODE_LABEL = { walk_friend: "산책 친구", family: "가족" };
const MODE_ICON = { walk_friend: "dog", family: "users" };

export async function roomViewScreen(params) {
  setTab("room");
  loading();
  let room;
  try { room = await api.get(`/rooms/${params.id}`); }
  catch (e) {
    toast(e.status === 403 ? "방 멤버만 볼 수 있어요" : (e.message || "방을 불러오지 못했어요"), "err");
    navigate("/rooms");
    return;
  }
  render(room);
}

function render(room) {
  const codeBtn = el("button.btn.secondary.invite-chip", {
    id: "room-code-open",
    text: "참여코드",
    onclick: () => openInviteSheet(room),
  });

  const members = el("div.member-chips", {},
    (room.members || []).map((m) =>
      el("div.member-chip", {}, [el("span.av", {}, [icon("paw-print")]), el("span", { text: m.nickname || "익명" })])
    )
  );

  const postBtn = el("button.cta", { id: "post-record", onclick: () => navigate(`/record?room=${room.room_id}`) }, [icon("camera"), " 방에 기록 올리기"]);

  const timeline = el("div.stack", { id: "room-timeline" });
  renderTimeline(timeline, room);

  mount(
    el("div.stack", {}, [
      el("div.row", {}, [
        codeBtn,
        el("span.spacer"),
        el("button.btn.ghost", { text: "방 목록", onclick: () => navigate("/rooms") }),
        el("button.btn.ghost", { text: "나가기", onclick: () => leaveRoom(room) }),
      ]),
      el("h1.h1", { text: room.name }),
      el("div.row", {}, [el("span.chip.on", {}, [icon(MODE_ICON[room.mode] || "users"), " " + (MODE_LABEL[room.mode] || room.mode)]), el("span.spacer")]),

      el("div.h2", { text: `멤버 ${(room.members || []).length}명` }),
      members,

      room.today_quest ? el("div.badge", {}, [icon("target"), ` 오늘의 방 퀘스트: ${room.today_quest.title}`]) : null,

      postBtn,

      el("div.h2", { text: "타임라인" }),
      timeline,
    ])
  );
}

function openInviteSheet(room) {
  bottomSheet((close) => {
    const copyBtn = el("button.cta", {
      id: "share-room",
      text: "초대 정보 복사",
      onclick: async () => { await shareInvite(room); close(); },
    });
    return el("div.stack.code-popover", {}, [
      el("div.h2", { text: "참여 코드" }),
      el("p.sub", { text: "친구가 이 코드를 입력하면 방에 참여할 수 있어요." }),
      el("div.code-box.compact", {}, [
        el("div.code", { id: "room-code", text: room.join_code }),
      ]),
      copyBtn,
    ]);
  });
}

function renderTimeline(container, room) {
  container.innerHTML = "";
  const tl = room.timeline || [];
  if (!tl.length) {
    container.append(el("div.empty", {}, [el("div.big", {}, [icon("camera")]), el("p", { text: "아직 공유된 기록이 없어요." }), el("p.sub", { text: "첫 기록을 올려 친구와 나눠요." })]));
    return;
  }
  tl.forEach((rec) => container.append(timelineItem(rec, room)));
}

function timelineItem(rec, room) {
  const author = (room.members || []).find((m) => m.user_id === rec.user_id);
  const clips = el("div.tl-clips", {});
  if (rec.clips && rec.clips.length) {
    rec.clips.forEach((c) => {
      const chip = el("div.clip-chip", { dataset: { clipId: c.id } });
      chip.append(icon("film"));
      clips.append(chip);
      (async () => {
        try {
          const url = await api.blobUrl(c.stream_url.replace("/api", ""));
          chip.innerHTML = "";
          const v = el("video", { src: url, controls: "", playsinline: "", muted: "" }); v.muted = true;
          chip.append(v);
        } catch (_) {}
      })();
    });
  }

  const item = el("div.card.tl-item", { dataset: { rid: rec.id } }, [
    el("div.tl-head", {}, [
      el("div.av", {}, [icon("paw-print")]),
      el("div", {}, [
        el("div.strong", { text: author ? author.nickname : "멤버" }),
        el("div.sub", { text: rec.walked_at || "" }),
      ]),
    ]),
    rec.text ? el("p", { text: rec.text }) : null,
    rec.clips && rec.clips.length ? clips : null,
    reactionBar(rec),
  ]);
  return item;
}

function reactionBar(rec) {
  // 현재 사용자가 누른 이모지는 로컬에서 낙관적으로 추적
  const mine = new Set();
  const counts = {};
  (rec.reactions || []).forEach((r) => (counts[r.emoji] = r.count));

  const bar = el("div.rx-bar", { dataset: { rid: rec.id } });
  EMOJIS.forEach((emoji) => {
    const n = el("span.n", { text: counts[emoji] ? String(counts[emoji]) : "" });
    const btn = el("span.rx", { dataset: { emoji }, title: emoji }, [el("span", { text: emoji }), n]);
    btn.addEventListener("click", async () => {
      // 낙관적 토글
      const had = mine.has(emoji);
      try {
        const res = await api.post("/reactions", { target_type: "record", target_id: rec.id, emoji });
        const added = res.toggled === "added";
        if (added) { mine.add(emoji); btn.classList.add("on"); counts[emoji] = (counts[emoji] || 0) + 1; }
        else { mine.delete(emoji); btn.classList.remove("on"); counts[emoji] = Math.max(0, (counts[emoji] || 1) - 1); }
        n.textContent = counts[emoji] ? String(counts[emoji]) : "";
      } catch (e) {
        toast(e.message || "반응 실패", "err");
      }
    });
    bar.append(btn);
  });
  return bar;
}

async function shareInvite(room) {
  const url = `${location.origin}/?join=${room.join_code}`;
  const deepLink = `app://join/${room.join_code}`;
  const text = `blip 방 '${room.name}' 초대\n코드: ${room.join_code}\n${url}`;
  if (navigator.share) {
    try { await navigator.share({ title: "blip 방 초대", text, url }); return; } catch (_) {}
  }
  try {
    await navigator.clipboard?.writeText(`${text}\n${deepLink}`);
    toast("초대 정보를 복사했어요", "ok");
  } catch {
    toast(`코드: ${room.join_code}`);
  }
}

async function leaveRoom(room) {
  if (!confirm("이 방에서 나갈까요?")) return;
  try { await api.post(`/rooms/${room.room_id}/leave`, {}); toast("방에서 나왔어요"); navigate("/rooms"); }
  catch (e) { toast(e.message, "err"); }
}
