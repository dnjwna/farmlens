import api from "./api";
import { Farmer } from "@/types";

export const login = async (phone_number: string, password: string) => {
  const res = await api.post("/auth/login", { phone_number, password });
  localStorage.setItem("farmlens_token", res.data.access_token);
  return res.data;
};

export const register = async (data: {
  full_name: string;
  phone_number: string;
  password: string;
  province?: string;
  city?: string;
}) => {
  const res = await api.post("/auth/register", data);
  return res.data;
};

export const getMe = async (): Promise<Farmer> => {
  const res = await api.get("/auth/me");
  return res.data;
};

export const logout = () => {
  localStorage.removeItem("farmlens_token");
  window.location.href = "/login";
};

export const isLoggedIn = () => {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("farmlens_token");
};
export const updateMe = async (data: { full_name?: string; province?: string | null; city?: string | null }): Promise<Farmer> => {
  const res = await api.patch("/auth/me", data);
  return res.data;
};

/** Other devices are logged out; this device keeps working with the returned token. */
export const changePassword = async (current_password: string, new_password: string) => {
  const res = await api.post("/auth/change-password", { current_password, new_password });
  localStorage.setItem("farmlens_token", res.data.access_token);
};

export const requestPasswordReset = async (phone_number: string): Promise<string> => {
  const res = await api.post("/auth/forgot-password", { phone_number });
  return res.data.detail;
};

/** Signs the user in on success; every other session is logged out. */
export const resetPassword = async (phone_number: string, code: string, new_password: string) => {
  const res = await api.post("/auth/reset-password", { phone_number, code, new_password });
  localStorage.setItem("farmlens_token", res.data.access_token);
};

export const deleteAccount = async (password: string) => {
  await api.post("/auth/delete-account", { password });
  localStorage.removeItem("farmlens_token");
};
