// dog/share.js — 강아지 이미지 공유(스프라이트 레이어 → canvas → PNG).
// Web Share API(files)로 공유하고, 미지원이면 다운로드 폴백.
// 직렬화 SVG는 외부 이미지(href)를 로드하지 못해 캔버스가 비므로, 레이어 PNG를
// 캔버스에 직접 그린다(dogLayers). 에셋은 동일 출처라 캔버스 오염(taint) 없음.

import { dogLayers } from "./render.js";

function loadImg(src) {
  return new Promise((res, rej) => {
    const img = new Image();
    img.onload = () => res(img);
    img.onerror = rej;
    img.src = src;
  });
}

// 외형 → 공유용 PNG Blob(파스텔 카드 + 이름 + LetsPaw 워터마크)
export async function makeDogPng(appearance, { name = "우리 강아지", size = 512 } = {}) {
  const W = size, H = size + 120;
  const canvas = document.createElement("canvas");
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = false;

  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, "#FFF1DD");
  grad.addColorStop(1, "#FFE0EB");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);

  // 레이어(베이스 강아지 + 장착 악세)를 같은 박스에 차례로 합성
  const dx = W * 0.1, dy = 24, dw = W * 0.8, dh = W * 0.8;
  for (const src of dogLayers(appearance, "front")) {
    try {
      const img = await loadImg(src);
      ctx.drawImage(img, dx, dy, dw, dh);
    } catch (_) { /* 누락 레이어는 건너뜀 */ }
  }

  ctx.textAlign = "center";
  ctx.fillStyle = "#5A463E";
  ctx.font = "bold 40px Pretendard, system-ui, sans-serif";
  ctx.fillText(name, W / 2, H - 58);
  ctx.fillStyle = "#F2789F";
  ctx.font = "bold 26px Pretendard, system-ui, sans-serif";
  ctx.fillText("🐾 LetsPaw", W / 2, H - 22);

  return await new Promise((res) => canvas.toBlob(res, "image/png"));
}

// 공유(파일) → 실패 시 다운로드. 반환: "shared" | "downloaded"
export async function shareDog(appearance, name = "우리 강아지") {
  const blob = await makeDogPng(appearance, { name });
  const file = new File([blob], "letspaw-dog.png", { type: "image/png" });
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: "LetsPaw", text: `${name} 보러 오세요! 🐾` });
      return "shared";
    } catch (_) { /* 취소/실패 → 다운로드 폴백 */ }
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "letspaw-dog.png";
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
  return "downloaded";
}
