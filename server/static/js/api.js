// api.js — fetch 래퍼: 토큰 헤더 + 표준 에러 봉투 처리
import { store } from "./store.js";

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message || `HTTP ${status}`);
    this.status = status;
    this.code = code;
  }
}

async function request(method, path, { body, form, headers = {}, auth = true } = {}) {
  const h = { ...headers };
  if (auth && store.token) h["Authorization"] = `Bearer ${store.token}`;

  let payload;
  if (form) {
    payload = form; // FormData — let browser set content-type
  } else if (body !== undefined) {
    h["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(`/api${path}`, { method, headers: h, body: payload });
  } catch (e) {
    throw new ApiError(0, "network", "네트워크 오류");
  }

  const text = await res.text();
  let data = null;
  if (text) { try { data = JSON.parse(text); } catch { data = text; } }

  if (!res.ok) {
    const err = (data && data.error) || {};
    throw new ApiError(res.status, err.code || res.status, err.message || `요청 실패 (${res.status})`);
  }
  return data;
}

// 인증이 필요한 미디어(클립 스트림)를 Blob URL로 가져온다.
// <video src>는 Authorization 헤더를 못 실으므로 fetch→blob→objectURL.
async function blobUrl(path) {
  const h = {};
  if (store.token) h["Authorization"] = `Bearer ${store.token}`;
  const res = await fetch(`/api${path}`, { headers: h });
  if (!res.ok) throw new ApiError(res.status, res.status, "media load failed");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export const api = {
  get: (p, o) => request("GET", p, o),
  post: (p, body, o) => request("POST", p, { body, ...o }),
  patch: (p, body, o) => request("PATCH", p, { body, ...o }),
  del: (p, o) => request("DELETE", p, o),
  upload: (p, form, o) => request("POST", p, { form, ...o }),
  blobUrl,
};
