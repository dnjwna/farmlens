import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  headers: { "Content-Type": "application/json" },
});

// Otomatis attach token ke setiap request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("farmlens_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Session expired or revoked (e.g. password changed on another device): back to login.
// Only for requests that carried a token, so a wrong password on the login form
// shows its inline error instead of reloading the page.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const sentToken = Boolean(err.config?.headers?.Authorization);
    if (err.response?.status === 401 && sentToken) {
      localStorage.removeItem("farmlens_token");
      window.location.href = "/login?sesi=berakhir";
    }
    return Promise.reject(err);
  }
);

export default api;
/** Extracts FastAPI's `detail` string from an error, if there is one. */
export function apiErrorDetail(err: unknown): string | undefined {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    // FastAPI 422: [{ msg: "Value error, Kode terdiri dari 6 angka", ... }]
    if (Array.isArray(detail) && typeof detail[0]?.msg === "string") {
      return detail[0].msg.replace(/^Value error, /, "");
    }
  }
  return undefined;
}

/** User-facing reason a request failed: unreachable server vs server error vs API message. */
export function describeLoadError(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    if (!err.response) {
      return "Server FarmLens tidak bisa dihubungi. Pastikan backend sedang jalan, lalu coba lagi.";
    }
    const detail = apiErrorDetail(err);
    if (detail) return detail;
    if (err.response.status >= 500) return `Server sedang bermasalah (kode ${err.response.status}). Coba lagi nanti.`;
  }
  return fallback;
}
