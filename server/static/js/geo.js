// geo.js — Geolocation 권한/추적 유틸 (F-01 watchPosition)
// HTTPS/localhost 필수. 권한 거부 상태를 명확히 노출한다.

export function geoSupported() {
  return "geolocation" in navigator;
}

// 1회 현재 위치. resolve({lat,lng}) / reject(code) where code: 'unsupported'|'denied'|'unavailable'|'timeout'
export function getOnce({ timeout = 8000, highAccuracy = true } = {}) {
  return new Promise((resolve, reject) => {
    if (!geoSupported()) return reject("unsupported");
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }),
      (err) => reject(mapErr(err)),
      { enableHighAccuracy: highAccuracy, timeout, maximumAge: 0 }
    );
  });
}

// 지속 추적. onUpdate({lat,lng}), onError(code). returns stop().
export function watch(onUpdate, onError, { highAccuracy = true } = {}) {
  if (!geoSupported()) { onError?.("unsupported"); return () => {}; }
  const id = navigator.geolocation.watchPosition(
    (pos) => onUpdate({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }),
    (err) => onError?.(mapErr(err)),
    { enableHighAccuracy: highAccuracy, timeout: 10000, maximumAge: 2000 }
  );
  return () => navigator.geolocation.clearWatch(id);
}

function mapErr(err) {
  if (!err) return "unavailable";
  if (err.code === 1) return "denied";
  if (err.code === 2) return "unavailable";
  if (err.code === 3) return "timeout";
  return "unavailable";
}

export function fmtDistance(m) {
  if (m == null) return "";
  if (m < 1000) return `${Math.round(m)}m`;
  return `${(m / 1000).toFixed(1)}km`;
}
