// media.js — getUserMedia + MediaRecorder 2초 강제 녹화 (F-10 핵심구현 1)
//
// ⚠️ 방향: 폰이 세로(portrait) 방향이면 카메라 피드가 720×1280 세로로 들어오고, 가로로 든 실제
// 장면이 그 안에 90° 누운 채 담긴다. 그래서 녹화도 세로/회전되어 나온다.
// 해결: 촬영 화면(camera.js)이 1280×720 캔버스에 '회전 보정 + cover-fit'으로 매 프레임 그리고,
// 그 캔버스를 미리보기로 보여주면서 canvas.captureStream 을 녹화한다(보이는 그대로 찍힘).
// record()는 그 캔버스 스트림(+원본 오디오)을 녹화만 한다. 캔버스 없으면 원본 스트림 폴백.
export const CLIP_MS = 2000;

export function mediaSupported() {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
}

function pickMime() {
  const cands = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"];
  for (const m of cands) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported(m)) return m;
  }
  return "video/webm";
}

export async function openCamera() {
  if (!mediaSupported()) throw "unsupported";
  try {
    return await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 }, aspectRatio: { ideal: 16 / 9 } },
      audio: true,
    });
  } catch (e) {
    if (e && (e.name === "NotAllowedError" || e.name === "SecurityError")) throw "denied";
    throw "error";
  }
}

// 2초 클립 1개 녹화. opts.canvas 주면 그 캔버스(가로 정규화 결과)를 녹화. onTick(remainingMs) 선택.
export function record(stream, { onTick, canvas } = {}) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    const t0 = Date.now();
    let recorder, recStream;

    if (canvas && typeof canvas.captureStream === "function") {
      recStream = canvas.captureStream(30);
      try { stream.getAudioTracks().forEach((t) => recStream.addTrack(t)); } catch (_) {}
    } else {
      recStream = stream; // 폴백
    }

    try {
      recorder = new MediaRecorder(recStream, { mimeType: pickMime() });
    } catch (e) {
      return reject("error");
    }
    recorder.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    recorder.onerror = () => reject("error");
    recorder.onstop = () => resolve({ blob: new Blob(chunks, { type: recorder.mimeType || "video/webm" }), durationMs: Date.now() - t0 });
    recorder.start();

    let raf;
    const tick = () => {
      const left = Math.max(0, CLIP_MS - (Date.now() - t0));
      if (onTick) onTick(left);
      if (left > 0 && recorder.state === "recording") raf = requestAnimationFrame(tick);
    };
    tick();
    setTimeout(() => { if (recorder.state === "recording") recorder.stop(); cancelAnimationFrame(raf); }, CLIP_MS);
  });
}

export function stopStream(stream) {
  try { stream?.getTracks().forEach((t) => t.stop()); } catch (_) {}
}
