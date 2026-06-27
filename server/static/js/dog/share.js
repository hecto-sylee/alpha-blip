// dog/share.js — 강아지 이미지 공유(SVG → canvas → PNG).
// Web Share API(files)로 공유하고, 미지원이면 다운로드 폴백.

import { dogSVG } from "./render.js";

// 외형 → 공유용 PNG Blob(파스텔 카드 + 이름 + LetsPaw 워터마크)
export async function makeDogPng(appearance, { name = "우리 강아지", size = 512 } = {}) {
  const svg = dogSVG({ ...appearance }, { pose: "front", size, anim: false });
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

  const dataUrl = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svg)));
  const img = new Image();
  await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = dataUrl; });
  ctx.drawImage(img, W * 0.1, 24, W * 0.8, W * 0.8);

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
