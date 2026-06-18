// media.js — getUserMedia + MediaRecorder 2초 강제 녹화 (F-10 핵심구현 1)
export const CLIP_MS = 2000;

export function mediaSupported() {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
}

function pickMime() {
  const cands = [
    "video/webm;codecs=vp9,opus",
    "video/webm;codecs=vp8,opus",
    "video/webm",
  ];
  for (const m of cands) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported(m)) return m;
  }
  return "video/webm";
}

// 카메라 스트림 확보. resolve(stream) / reject('denied'|'unsupported'|'error')
export async function openCamera() {
  if (!mediaSupported()) throw "unsupported";
  try {
    return await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  } catch (e) {
    if (e && (e.name === "NotAllowedError" || e.name === "SecurityError")) throw "denied";
    throw "error";
  }
}

// 2초 클립 1개 녹화. onTick(remainingMs) 선택. resolve({blob, durationMs}).
export function record(stream, { onTick } = {}) {
  return new Promise((resolve, reject) => {
    let rec;
    try {
      rec = new MediaRecorder(stream, { mimeType: pickMime() });
    } catch (e) {
      return reject("error");
    }
    const chunks = [];
    const t0 = Date.now();
    rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    rec.onerror = () => reject("error");
    rec.onstop = () => {
      const blob = new Blob(chunks, { type: rec.mimeType || "video/webm" });
      resolve({ blob, durationMs: Date.now() - t0 });
    };

    let raf;
    const tick = () => {
      const left = Math.max(0, CLIP_MS - (Date.now() - t0));
      onTick?.(left);
      if (left > 0 && rec.state === "recording") raf = requestAnimationFrame(tick);
    };

    rec.start();
    tick();
    // 2초 강제 정지 (클라이언트가 길이 보장)
    setTimeout(() => { if (rec.state === "recording") rec.stop(); cancelAnimationFrame(raf); }, CLIP_MS);
  });
}

export function stopStream(stream) {
  try { stream?.getTracks().forEach((t) => t.stop()); } catch (_) {}
}
