// dog/accessories.js — 장착 아이템(옷) 픽셀 레이어.
//
// 강아지 포즈 위에 머리/얼굴/몸 슬롯별로 그려진다. 키/이름/슬롯/표시색은 여기서,
// 가격·소유 검증은 서버(shop_catalog.py / UserItem)가 권위를 가진다(§4).
// draw(view) 는 정면(front) 기준으로 그리고, side/sit도 무난히 얹히도록 단순화한다.

const px = (x, y, w, h, fill, op) =>
  w <= 0 || h <= 0 ? "" : `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"${op != null ? ` opacity="${op}"` : ""}/>`;

// slot: "head" | "face" | "body".  좌표계 = render.js 32 그리드(머리 x7..25, 눈 y7, 목 y14~16).
export const ACCESSORIES = {
  party_hat: {
    name: "고깔모자", slot: "head", cost: 30,
    draw: () =>
      px(15, -4, 2, 2, "#FFF6C9") + // 방울
      px(13, -3, 6, 1, "#FF8FB0") + px(12, -2, 8, 1, "#FFC36B") + px(11, -1, 10, 1, "#7FC8F0") +
      px(10, 0, 12, 1, "#FF8FB0") + px(10, 1, 12, 1, "#FFC36B"),
  },
  cap: {
    name: "야구모자", slot: "head", cost: 40,
    draw: () => px(9, -2, 14, 3, "#4F9BE0") + px(9, -2, 14, 1, "#6FB3F0") + px(6, 1, 8, 1, "#3C7BC0") + px(15, -3, 2, 1, "#3C7BC0"),
  },
  crown: {
    name: "왕관", slot: "head", cost: 120,
    draw: () =>
      px(9, -2, 14, 3, "#FFD24A") + px(9, -3, 1, 1, "#FFD24A") + px(13, -4, 2, 2, "#FFD24A") +
      px(17, -4, 2, 2, "#FFD24A") + px(22, -3, 1, 1, "#FFD24A") +
      px(12, -1, 2, 1, "#FF8FB0") + px(18, -1, 2, 1, "#7FC8F0"),
  },
  glasses: {
    name: "동그란 안경", slot: "face", cost: 50,
    draw: () =>
      px(10, 6, 4, 3, "#3A2C26") + px(11, 7, 2, 1, "#BFE3FF") +
      px(18, 6, 4, 3, "#3A2C26") + px(19, 7, 2, 1, "#BFE3FF") +
      px(14, 7, 4, 1, "#3A2C26"),
  },
  sunglasses: {
    name: "선글라스", slot: "face", cost: 60,
    draw: () => px(9, 6, 5, 3, "#222") + px(18, 6, 5, 3, "#222") + px(14, 7, 4, 1, "#222") + px(10, 6, 1, 1, "#7FA8C8"),
  },
  bandana: {
    name: "반다나", slot: "body", cost: 25,
    draw: () => px(9, 14, 14, 2, "#FF6B6B") + px(9, 16, 2, 2, "#E85050") + px(11, 15, 10, 1, "#FF9A9A", 0.7),
  },
  bowtie: {
    name: "나비넥타이", slot: "body", cost: 35,
    draw: () => px(13, 14, 2, 3, "#9B82E0") + px(17, 14, 2, 3, "#9B82E0") + px(15, 15, 2, 1, "#6A4FC0"),
  },
  scarf: {
    name: "목도리", slot: "body", cost: 45,
    draw: () => px(9, 14, 14, 2, "#2BC9A8") + px(11, 16, 3, 4, "#14A083") + px(12, 19, 2, 1, "#0E8068"),
  },
  cape: {
    name: "망토", slot: "body", cost: 90,
    draw: () => px(8, 15, 16, 1, "#C9504F") + px(8, 16, 3, 9, "#E0635F") + px(21, 16, 3, 9, "#E0635F") + px(9, 24, 2, 1, "#A53E3D") + px(22, 24, 2, 1, "#A53E3D"),
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
