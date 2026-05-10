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

// Kalau token expired, redirect ke login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("farmlens_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;