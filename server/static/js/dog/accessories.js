// dog/accessories.js — 장착 아이템(옷) 픽셀 레이어.
//
// 강아지 포즈 위에 머리/얼굴/몸 슬롯별로 그려진다. 키/이름/슬롯/표시색은 여기서,
// 가격·소유 검증은 서버(shop_catalog.py / UserItem)가 권위를 가진다(§4).
// draw(view) 는 정면(front) 기준으로 그리고, side/sit도 무난히 얹히도록 단순화한다.

const px = (x, y, w, h, fill, op) =>
  w <= 0 || h <= 0 ? "" : `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"${op != null ? ` opacity="${op}"` : ""}/>`;

// slot: "head" | "face" | "body".  좌표계 = render.js 48 그리드(머리 x8..40, 눈 y13, 코 y18, 목 y23~).
export const ACCESSORIES = {
  party_hat: {
    name: "고깔모자", slot: "head", cost: 30,
    draw: () =>
      px(23, -7, 2, 2, "#FFF6C9") + // 방울
      px(21, -5, 6, 1, "#FF8FB0") + px(19, -4, 10, 1, "#FFC36B") + px(17, -3, 14, 1, "#7FC8F0") +
      px(15, -2, 18, 1, "#FF8FB0") + px(14, -1, 20, 1, "#FFC36B") + px(14, 0, 20, 2, "#FF8FB0"),
  },
  cap: {
    name: "야구모자", slot: "head", cost: 40,
    draw: () => px(13, -3, 22, 3, "#4F9BE0") + px(13, -3, 22, 1, "#6FB3F0") + px(9, 0, 12, 1, "#3C7BC0") + px(23, -4, 2, 1, "#3C7BC0"),
  },
  crown: {
    name: "왕관", slot: "head", cost: 120,
    draw: () =>
      px(13, -3, 22, 3, "#FFD24A") + px(13, -4, 1, 1, "#FFD24A") + px(18, -5, 2, 2, "#FFD24A") +
      px(23, -6, 2, 2, "#FFD24A") + px(28, -5, 2, 2, "#FFD24A") + px(33, -4, 1, 1, "#FFD24A") +
      px(17, -2, 2, 1, "#FF8FB0") + px(28, -2, 2, 1, "#7FC8F0"),
  },
  glasses: {
    name: "동그란 안경", slot: "face", cost: 50,
    draw: () =>
      px(14, 12, 6, 5, "#3A2C26") + px(15, 13, 4, 3, "#BFE3FF") +
      px(28, 12, 6, 5, "#3A2C26") + px(29, 13, 4, 3, "#BFE3FF") +
      px(20, 13, 8, 1, "#3A2C26"),
  },
  sunglasses: {
    name: "선글라스", slot: "face", cost: 60,
    draw: () => px(13, 12, 8, 5, "#222") + px(27, 12, 8, 5, "#222") + px(20, 13, 8, 1, "#222") + px(15, 13, 2, 1, "#7FA8C8"),
  },
  bandana: {
    name: "반다나", slot: "body", cost: 25,
    draw: () => px(12, 23, 24, 3, "#FF6B6B") + px(12, 25, 4, 3, "#E85050") + px(16, 24, 16, 1, "#FF9A9A", 0.7),
  },
  bowtie: {
    name: "나비넥타이", slot: "body", cost: 35,
    draw: () => px(20, 23, 3, 4, "#9B82E0") + px(25, 23, 3, 4, "#9B82E0") + px(23, 24, 2, 2, "#6A4FC0"),
  },
  scarf: {
    name: "목도리", slot: "body", cost: 45,
    draw: () => px(12, 23, 24, 3, "#2BC9A8") + px(15, 26, 4, 6, "#14A083") + px(16, 31, 2, 1, "#0E8068"),
  },
  cape: {
    name: "망토", slot: "body", cost: 90,
    draw: () => px(11, 24, 26, 2, "#C9504F") + px(11, 26, 4, 12, "#E0635F") + px(33, 26, 4, 12, "#E0635F") + px(12, 37, 3, 1, "#A53E3D") + px(34, 37, 3, 1, "#A53E3D"),
  },
};

export const ACCESSORY_KEYS = Object.keys(ACCESSORIES);

// 장착된 아이템 중 해당 슬롯의 것을 그린다. view는 현재 front 기준 드로잉을 공유.
export function drawAccessories(a, view, slot) {
  const eq = Array.isArray(a?.equipped) ? a.equipped : [];
  if (!eq.length) return "";
  let out = "";
  for (const key of eq) {
    const item = ACCESSORIES[key];
    if (item && item.slot === slot) out += item.draw(view);
  }
  return out;
}
