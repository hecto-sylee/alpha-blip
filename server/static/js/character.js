// character.js — 펫별 "고정" 캐릭터(강아지 마스코트).
//
// 같은 펫이면 언제나 같은 캐릭터가 나오도록 pet.id 해시로 결정한다.
//   - 색(팔레트): pet.id 해시  → 펫마다 고유
//   - 귀/털(실루엣): breed     → 견종 반영 (미입력이면 해시로 폴백)
//   - 크기: size               → 소/중/대
//   - 표정/혀/idle 무드: personality_tags
// idle 모션(숨쉬기·꼬리·깜빡임)은 app.css의 @keyframes로 처리한다(리스트에서 가볍고
// prefers-reduced-motion 자동 대응). 입장/탭 모션만 Motion One을 쓴다.
//
// RIVE 확장 지점: mountPetCharacter() 한 곳만 분기하면 정적 SVG → 라이브 Rive로
// 업그레이드된다. .riv 계약은 docs/mvp_refactor/05_pet_character.md 참고.

// --- 결정적 해시 (FNV-1a) --------------------------------------------------
function hashStr(str) {
  let h = 2166136261 >>> 0;
  const s = String(str || "blip");
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// --- 팔레트 (현재 UI 토큰과 어울리는 8종) ----------------------------------
const PALETTES = [
  { body: "#FF9E91", belly: "#FFE2DD", ear: "#F07D6E", nose: "#4A3B34" }, // coral
  { body: "#FFC06A", belly: "#FFE9C7", ear: "#F0A23F", nose: "#4A3B34" }, // amber
  { body: "#67D7BD", belly: "#C9F4EA", ear: "#3DBBA0", nose: "#3A4A44" }, // mint
  { body: "#F4CE6A", belly: "#FBF1D0", ear: "#E0B23F", nose: "#4A4030" }, // butter
  { body: "#B9A3F0", belly: "#ECE4FF", ear: "#9B82E0", nose: "#403A52" }, // lavender
  { body: "#86B8F0", belly: "#DCEBFF", ear: "#5F97E0", nose: "#36404A" }, // sky
  { body: "#F58FB4", belly: "#FFE0EC", ear: "#E06F9B", nose: "#4A3640" }, // rose
  { body: "#C9A06E", belly: "#F0E2CE", ear: "#A9824F", nose: "#3E3026" }, // mocha
];

// --- 견종 → 귀/털 실루엣 ---------------------------------------------------
const EAR_STYLES = ["floppy", "pointy", "round"];
const COAT_STYLES = ["smooth", "fluffy", "curly"];
const BREED_RULES = [
  { kw: ["푸들", "poodle"], ears: "floppy", coat: "curly" },
  { kw: ["비숑", "bichon"], ears: "round", coat: "fluffy" },
  { kw: ["말티즈", "몰티즈", "malt"], ears: "floppy", coat: "fluffy" },
  { kw: ["시츄", "시추", "shih"], ears: "floppy", coat: "fluffy" },
  { kw: ["포메", "pomer"], ears: "pointy", coat: "fluffy" },
  { kw: ["스피츠", "spitz", "사모", "samoy"], ears: "pointy", coat: "fluffy" },
  { kw: ["시바", "shiba"], ears: "pointy", coat: "smooth" },
  { kw: ["진도", "진돗", "jindo"], ears: "pointy", coat: "smooth" },
  { kw: ["코기", "corgi", "웰시", "welsh"], ears: "pointy", coat: "smooth" },
  { kw: ["치와와", "chihuahua"], ears: "pointy", coat: "smooth" },
  { kw: ["허스키", "husky", "말라뮤트", "malamute"], ears: "pointy", coat: "smooth" },
  { kw: ["닥스", "dachs"], ears: "floppy", coat: "smooth" },
  { kw: ["리트리버", "retriev", "골든", "golden", "래브라도", "labrad"], ears: "floppy", coat: "smooth" },
  { kw: ["비글", "beagle"], ears: "floppy", coat: "smooth" },
  { kw: ["불독", "불도그", "bulldog", "bull"], ears: "floppy", coat: "smooth" },
];

const SIZE_SCALE = { small: 0.86, medium: 1.0, large: 1.14 };

const TAGS_PLAYFUL = ["활발함", "장난꾸러기", "호기심"];
const TAGS_CALM = ["온순함", "차분함"];
const TAGS_SHY = ["겁많음"];
const TAGS_SOCIAL = ["사람좋아", "강아지좋아"];

function breedSilhouette(breed, seed) {
  const b = String(breed || "").toLowerCase();
  for (const rule of BREED_RULES) {
    if (rule.kw.some((k) => b.includes(k.toLowerCase()))) {
      return { ears: rule.ears, coat: rule.coat };
    }
  }
  // 견종 미입력/미매칭 → 해시로 폴백 (그래도 펫마다 고정)
  return {
    ears: EAR_STYLES[(seed >> 3) % 3],
    coat: COAT_STYLES[(seed >> 9) % 3],
  };
}

// --- 펫 → 시각 파라미터 (결정적) -------------------------------------------
export function petVisualParams(pet) {
  const seed = hashStr(pet?.id || pet?.name);
  const palette = PALETTES[seed % PALETTES.length];
  const { ears, coat } = breedSilhouette(pet?.breed, seed);
  const scale = SIZE_SCALE[pet?.size] || SIZE_SCALE.medium;
  const tags = Array.isArray(pet?.personality_tags) ? pet.personality_tags : [];
  const has = (list) => tags.some((t) => list.includes(t));

  const mood = has(TAGS_PLAYFUL) ? "bouncy" : has(TAGS_CALM) ? "gentle" : "normal";
  const eyeStyle = has(TAGS_CALM) ? "happy" : has(TAGS_SHY) ? "shy" : "round";
  const tongue = has(TAGS_PLAYFUL) || has(TAGS_SOCIAL);
  const spot = ((seed >> 6) & 1) === 1;

  return { seed, palette, ears, coat, scale, mood, eyeStyle, tongue, spot };
}

// --- SVG 파트 빌더 ---------------------------------------------------------
function earMarkup({ ears, palette }) {
  const { ear, belly } = palette;
  if (ears === "pointy") {
    return `
      <path class="bp-ear bp-ear-l" d="M40 28 L 32 2 C 50 8 52 24 52 34 Z" fill="${ear}"/>
      <path class="bp-ear bp-ear-r" d="M80 28 L 88 2 C 70 8 68 24 68 34 Z" fill="${ear}"/>
      <path d="M42 26 L 37 11 C 47 15 48 24 48 30 Z" fill="${belly}" opacity=".7"/>
      <path d="M78 26 L 83 11 C 73 15 72 24 72 30 Z" fill="${belly}" opacity=".7"/>`;
  }
  if (ears === "round") {
    return `
      <circle class="bp-ear bp-ear-l" cx="33" cy="30" r="15" fill="${ear}"/>
      <circle class="bp-ear bp-ear-r" cx="87" cy="30" r="15" fill="${ear}"/>
      <circle cx="33" cy="31" r="7" fill="${belly}" opacity=".7"/>
      <circle cx="87" cy="31" r="7" fill="${belly}" opacity=".7"/>`;
  }
  // floppy (기본)
  return `
    <path class="bp-ear bp-ear-l" d="M42 30 C 26 28 18 50 26 70 C 34 72 44 60 44 44 Z" fill="${ear}"/>
    <path class="bp-ear bp-ear-r" d="M78 30 C 94 28 102 50 94 70 C 86 72 76 60 76 44 Z" fill="${ear}"/>`;
}

function eyeMarkup({ eyeStyle, palette }) {
  const dark = palette.nose;
  if (eyeStyle === "happy") {
    return `<g class="bp-eyes">
      <path d="M41 47 Q 47 40 53 47" stroke="${dark}" stroke-width="3" fill="none" stroke-linecap="round"/>
      <path d="M67 47 Q 73 40 79 47" stroke="${dark}" stroke-width="3" fill="none" stroke-linecap="round"/>
    </g>`;
  }
  const cy = eyeStyle === "shy" ? 42 : 45;
  const r = eyeStyle === "shy" ? 4.5 : 5.6;
  return `<g class="bp-eyes bp-blink">
    <circle cx="47" cy="${cy}" r="${r}" fill="${dark}"/>
    <circle cx="73" cy="${cy}" r="${r}" fill="${dark}"/>
    <circle cx="49" cy="${cy - 2}" r="1.8" fill="#fff"/>
    <circle cx="75" cy="${cy - 2}" r="1.8" fill="#fff"/>
  </g>`;
}

function svgMarkup(p, pet) {
  const { body, belly, nose } = p.palette;
  const cx = 60, cy = 64; // scale 중심
  const title = (pet?.name || "반려동물").replace(/[<>&]/g, "");
  const cheeks =
    p.coat === "fluffy"
      ? `<ellipse cx="39" cy="58" rx="7" ry="5.5" fill="${belly}" opacity=".75"/>
         <ellipse cx="81" cy="58" rx="7" ry="5.5" fill="${belly}" opacity=".75"/>`
      : "";
  const spot = p.spot
    ? `<ellipse cx="74" cy="40" rx="13" ry="12" fill="${p.palette.ear}" opacity=".5"/>`
    : "";
  const tongue = p.tongue
    ? `<path d="M55 62 Q 60 75 65 62 Z" fill="#FF7FA8"/>`
    : "";

  return `<svg viewBox="0 0 120 120" width="100%" height="100%" role="img" aria-hidden="true" preserveAspectRatio="xMidYMid meet">
    <title>${title}</title>
    <g class="bp-scale" transform="translate(${cx} ${cy}) scale(${p.scale}) translate(${-cx} ${-cy})">
      <g class="bp-root">
        <path class="bp-tail" d="M86 92 C 104 88 110 70 101 60 C 99 75 92 84 82 87 Z" fill="${body}"
              style="transform-box:fill-box;transform-origin:0% 92%"/>
        <ellipse class="bp-body" cx="60" cy="92" rx="31" ry="24" fill="${body}"/>
        <ellipse cx="60" cy="98" rx="18" ry="15" fill="${belly}"/>
        <ellipse cx="47" cy="110" rx="9" ry="7" fill="${belly}"/>
        <ellipse cx="73" cy="110" rx="9" ry="7" fill="${belly}"/>
        <circle class="bp-head" cx="60" cy="50" r="33" fill="${body}"/>
        ${spot}
        ${earMarkup(p)}
        ${cheeks}
        <ellipse cx="60" cy="61" rx="17" ry="13" fill="${belly}"/>
        <ellipse class="bp-nose" cx="60" cy="55" rx="6" ry="4.6" fill="${nose}"/>
        <path d="M60 59 C 60 64 54 66 50 63 M60 59 C 60 64 66 66 70 63"
              stroke="${nose}" stroke-width="2" fill="none" stroke-linecap="round"/>
        ${tongue}
        ${eyeMarkup(p)}
      </g>
    </g>
  </svg>`;
}

// --- 공개 API --------------------------------------------------------------
// el() 자식으로 바로 넣을 수 있는 캐릭터 노드를 만든다.
export function petCharacterEl(pet, { size = 64 } = {}) {
  const p = petVisualParams(pet);
  const wrap = document.createElement("div");
  wrap.className = `bp-char bp-mood-${p.mood}`;
  wrap.style.width = `${size}px`;
  wrap.style.height = `${size}px`;
  wrap.setAttribute("role", "img");
  wrap.setAttribute("aria-label", `${pet?.name || "반려동물"} 캐릭터`);
  wrap.innerHTML = svgMarkup(p, pet);
  return wrap;
}

// 기존 컨테이너(예: .pet-avatar)에 캐릭터를 채운다.
// RIVE 확장 지점: /static/assets/characters/dog.riv 가 준비되면 여기서 <canvas>를
// 띄우고 petVisualParams(pet)로 입력을 구동하도록 분기한다. 실패 시 아래 SVG로 폴백.
export function mountPetCharacter(container, pet, opts = {}) {
  if (!container) return null;
  container.innerHTML = "";
  const node = petCharacterEl(pet, opts);
  container.append(node);
  return node;
}
