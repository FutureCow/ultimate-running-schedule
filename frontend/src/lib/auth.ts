import { authApi } from "./api";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function isLoggedIn(): boolean {
  return !!getAccessToken();
}

export function logout() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
}

export async function login(email: string, password: string) {
  const { data } = await authApi.login(email, password);
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data;
}

export async function register(email: string, password: string) {
  const { data } = await authApi.register(email, password);
  return data;
}
