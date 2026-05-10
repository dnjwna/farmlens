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