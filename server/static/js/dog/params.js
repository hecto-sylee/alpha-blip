// dog/params.js — 견종 레지스트리 + 외형(appearance) 해석기.
//
// "appearance"는 강아지가 어떻게 보이는지에 대한 단일 진실원이다.
//   - 커스터마이저로 완전 지정되거나(pet.appearance_json)
//   - 없으면 견종 + 결정적 해시로 유도(레거시 펫도 항상 같은 모습).
// 파라미터는 0625 LetsPaw sprites.js의 파라메트릭 모델(ear/tail/body/leg)을 계승·확장하고,
// 무늬(pattern)·보조색(belly)·장착(equipped)을 추가했다.

// --- 선택지 enum (커스터마이저가 이 순서로 토글) --------------------------
export const EARS = ["floppy", "perky", "perkyBig", "folded"]; // 접힘/쫑긋/큰쫑긋/완전접힘
export const TAILS = ["curl", "plume", "pom", "short", "long", "thin"]; // 말림/풍성/방울/짧은/긴/얇은
export const LEGS = ["long", "normal", "short", "tiny"]; // 긴/보통/짧은/아주짧은(코기·닥스)
export const BODIES = ["normal", "round", "long", "xlong"]; // 보통/통통/긴/아주긴
export const PATTERNS = ["solid", "patch", "spots", "saddle", "socks"]; // 단색/큰얼룩/잔점/등안장/양말발

// 코트(기본 털색) 스와치 — 강아지에 흔한 톤
export const COAT_SWATCHES = [
  "#FBF6EE", "#F4E2C6", "#E8C39E", "#E8B96A", "#F0A24E",
  "#E69A4C", "#C98A52", "#9A6A3F", "#6E4B30", "#3B3330",
  "#9FB0BC", "#6B7884", "#F2C9D6", "#C9A0E0",
];
// 무늬/보조색 스와치 — 보통 흰/크림 + 포인트색
export const PATTERN_SWATCHES = [
  "#FFFFFF", "#FBF6EE", "#F6E4BE", "#2E2622", "#9A6A3F",
  "#E69A4C", "#3B3330", "#C0CDD6",
];

// --- 견종 레지스트리 (LetsPaw 16종 계승) -----------------------------------
// coat=기본털색, belly=배/얼굴 밝은색(투톤), ears/tail/body/legs=실루엣, pattern=기본 무늬
export const BREEDS = {
  poodle:      { ko: "푸들",       coat: "#E8C39E", belly: "#F6E7D3", ears: "floppy",   tail: "pom",   body: "normal", legs: "normal", pattern: "solid",  curly: true },
  maltese:     { ko: "말티즈",     coat: "#FBF6EE", belly: "#FFFFFF", ears: "floppy",   tail: "plume", body: "normal", legs: "short",  pattern: "solid",  fluffy: true },
  pomeranian:  { ko: "포메라니안", coat: "#F0B560", belly: "#FFE3B0", ears: "perky",    tail: "plume", body: "round",  legs: "short",  pattern: "solid",  fluffy: true },
  bichon:      { ko: "비숑",       coat: "#FFFDF7", belly: "#FFFFFF", ears: "floppy",   tail: "plume", body: "round",  legs: "normal", pattern: "solid",  fluffy: true },
  shiba:       { ko: "시바견",     coat: "#E69A4C", belly: "#FBE5CF", ears: "perky",    tail: "curl",  body: "normal", legs: "normal", pattern: "socks" },
  jindo:       { ko: "진돗개",     coat: "#EAD9B0", belly: "#FFFDF7", ears: "perky",    tail: "curl",  body: "normal", legs: "normal", pattern: "solid" },
  corgi:       { ko: "웰시코기",   coat: "#F0A24E", belly: "#FBF6EE", ears: "perkyBig", tail: "short", body: "long",   legs: "tiny",   pattern: "saddle" },
  dachshund:   { ko: "닥스훈트",   coat: "#9A6A3F", belly: "#C98A52", ears: "floppy",   tail: "long",  body: "xlong",  legs: "tiny",   pattern: "solid" },
  husky:       { ko: "허스키",     coat: "#8FA0AC", belly: "#F2F5F7", ears: "perky",    tail: "curl",  body: "normal", legs: "normal", pattern: "saddle" },
  doberman:    { ko: "도베르만",   coat: "#3B3330", belly: "#A8743F", ears: "perkyBig", tail: "short", body: "normal", legs: "long",   pattern: "socks" },
  shihtzu:     { ko: "시츄",       coat: "#EAD2A8", belly: "#FBF6EE", ears: "floppy",   tail: "plume", body: "round",  legs: "short",  pattern: "patch",  fluffy: true },
  golden:      { ko: "골든리트리버", coat: "#E8B96A", belly: "#F6E4BE", ears: "floppy",  tail: "plume", body: "long",   legs: "normal", pattern: "solid" },
  beagle:      { ko: "비글",       coat: "#C98A52", belly: "#FBF6EE", ears: "floppy",   tail: "long",  body: "normal", legs: "short",  pattern: "saddle" },
  chihuahua:   { ko: "치와와",     coat: "#E0C29A", belly: "#FBF6EE", ears: "perkyBig", tail: "curl",  body: "normal", legs: "short",  pattern: "solid" },
  bordercollie:{ ko: "보더콜리",   coat: "#33302E", belly: "#FBF6EE", ears: "floppy",   tail: "plume", body: "normal", legs: "normal", pattern: "patch" },
  mix:         { ko: "믹스",       coat: "#FFD49A", belly: "#FFF0D6", ears: "floppy",   tail: "curl",  body: "normal", legs: "normal", pattern: "solid" },
};

export const BREED_KEYS = Object.keys(BREEDS);

// 주둥이 길이(견종 구분의 핵심) — long(긴 코)/med/short(납작)
export const SNOUTS = ["short", "med", "long"];
const SNOUT_BY_BREED = {
  shiba: "long", jindo: "long", husky: "long", golden: "long", doberman: "long",
  dachshund: "long", beagle: "med", bordercollie: "long", corgi: "med",
  poodle: "med", chihuahua: "short", pomeranian: "short", maltese: "short",
  bichon: "short", shihtzu: "short", mix: "med",
};

// 한글/영문 자유입력 → 견종키(부분일치). 온보딩 자유 입력 대응.
const ALIAS = [
  ["푸들", "poodle"], ["poodle", "poodle"],
  ["말티즈", "maltese"], ["몰티즈", "maltese"], ["malt", "maltese"],
  ["포메", "pomeranian"], ["pomer", "pomeranian"],
  ["비숑", "bichon"], ["비송", "bichon"], ["bichon", "bichon"],
  ["시바", "shiba"], ["shiba", "shiba"],
  ["진돗", "jindo"], ["진도", "jindo"], ["jindo", "jindo"],
  ["코기", "corgi"], ["웰시", "corgi"], ["corgi", "corgi"], ["welsh", "corgi"],
  ["닥스", "dachshund"], ["소시지", "dachshund"], ["dachs", "dachshund"],
  ["허스키", "husky"], ["husky", "husky"], ["말라뮤트", "husky"], ["malamute", "husky"],
  ["도베르만", "doberman"], ["도베", "doberman"], ["doberman", "doberman"],
  ["시츄", "shihtzu"], ["시추", "shihtzu"], ["시쯔", "shihtzu"], ["shih", "shihtzu"],
  ["골든", "golden"], ["리트리버", "golden"], ["golden", "golden"], ["retriev", "golden"], ["래브라도", "golden"], ["labrad", "golden"],
  ["비글", "beagle"], ["beagle", "beagle"],
  ["치와와", "chihuahua"], ["치와", "chihuahua"], ["chihuahua", "chihuahua"],
  ["보더", "bordercollie"], ["콜리", "bordercollie"], ["border", "bordercollie"], ["collie", "bordercollie"],
  ["스피츠", "pomeranian"], ["사모", "bichon"], ["불독", "mix"], ["bulldog", "mix"],
];

export function breedKey(input) {
  if (!input) return "mix";
  if (BREEDS[input]) return input;
  const s = String(input).toLowerCase();
  for (const [needle, key] of ALIAS) if (s.includes(needle.toLowerCase())) return key;
  return "mix";
}

// --- 결정적 해시 (FNV-1a) — 레거시/미지정 펫의 안정적 폴백 ------------------
export function hashStr(str) {
  let h = 2166136261 >>> 0;
  const s = String(str || "letspaw");
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// 성격태그 → 표정/혀 (기존 character.js 규칙 계승)
const TAGS_PLAYFUL = ["활발함", "장난꾸러기", "호기심"];
const TAGS_CALM = ["온순함", "차분함"];
const TAGS_SHY = ["겁많음"];
const TAGS_SOCIAL = ["사람좋아", "강아지좋아"];

// 펫 → 완전한 appearance 객체. appearance_json이 있으면 그것이 우선, 없으면 견종+해시 유도.
export function resolveAppearance(pet) {
  const seed = hashStr(pet?.id || pet?.name);
  const key = breedKey(pet?.breed);
  const base = BREEDS[key];

  // appearance_json 파싱 (객체이거나 문자열일 수 있음)
  let saved = pet?.appearance_json ?? pet?.appearance ?? null;
  if (typeof saved === "string") {
    try { saved = JSON.parse(saved); } catch { saved = null; }
  }
  if (!saved || typeof saved !== "object") saved = {};

  const tags = Array.isArray(pet?.personality_tags) ? pet.personality_tags : [];
  const has = (list) => tags.some((t) => list.includes(t));
  const eye = saved.eye || (has(TAGS_CALM) ? "happy" : has(TAGS_SHY) ? "shy" : "round");
  const mood = saved.mood || (has(TAGS_PLAYFUL) ? "bouncy" : has(TAGS_CALM) ? "gentle" : "normal");
  const tongue = saved.tongue ?? (has(TAGS_PLAYFUL) || has(TAGS_SOCIAL));

  return {
    breed: key,
    coat: saved.coat || base.coat,
    belly: saved.belly || base.belly || base.coat,
    ears: saved.ears || base.ears,
    tail: saved.tail || base.tail,
    legs: saved.legs || base.legs,
    body: saved.body || base.body,
    snout: saved.snout || SNOUT_BY_BREED[key] || "med",
    pattern: saved.pattern || base.pattern || "solid",
    patternColor: saved.patternColor || base.belly || "#FFFFFF",
    fluffy: saved.fluffy ?? !!base.fluffy,
    curly: saved.curly ?? !!base.curly,
    eye,
    mood,
    tongue,
    equipped: Array.isArray(saved.equipped) ? saved.equipped : [],
    seed,
  };
}

// 커스터마이저 초기값: 펫의 현재 외형(저장본 우선)에서 편집 가능한 필드만 추출.
export function editableAppearance(pet) {
  const a = resolveAppearance(pet);
  return {
    breed: a.breed, coat: a.coat, belly: a.belly, ears: a.ears,
    tail: a.tail, legs: a.legs, body: a.body, snout: a.snout, pattern: a.pattern,
    patternColor: a.patternColor, eye: a.eye, mood: a.mood, tongue: a.tongue,
    equipped: a.equipped,
  };
}

// 견종 선택 시 그 견종의 기본 외형으로 리셋(커스터마이저에서 "이 견종으로").
export function appearanceForBreed(key) {
  const k = breedKey(key);
  const b = BREEDS[k];
  return {
    breed: k, coat: b.coat, belly: b.belly || b.coat, ears: b.ears,
    tail: b.tail, legs: b.legs, body: b.body, snout: SNOUT_BY_BREED[k] || "med",
    pattern: b.pattern || "solid", patternColor: b.belly || "#FFFFFF",
    fluffy: !!b.fluffy, curly: !!b.curly,
  };
}
