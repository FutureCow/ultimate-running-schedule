import axios, { AxiosError } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT from localStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as any;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE_URL}/auth/refresh`, { refresh_token: refresh });
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          if (typeof window !== "undefined") {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            window.location.href = "/login";
          }
        }
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  register: (email: string, password: string) => api.post("/auth/register", { email, password }),
  login: (email: string, password: string) => api.post("/auth/login", { email, password }),
};

// Profile
export const profileApi = {
  get: () => api.get("/auth/profile"),
  update: (data: Partial<{
    age: number; height_cm: number; weight_kg: number;
    weekly_km: number; weekly_runs: number; injuries: string;
  }>) => api.patch("/auth/profile", data),
};

// Plans
export const plansApi = {
  list: () => api.get("/plans"),
  get: (id: number) => api.get(`/plans/${id}`),
  create: (data: any) => api.post("/plans", data),
  update: (id: number, data: any) => api.put(`/plans/${id}`, data),
  delete: (id: number) => api.delete(`/plans/${id}`),
  recalculateDates: (id: number, startDate?: string) =>
    api.patch(`/plans/${id}/recalculate-dates`, { start_date: startDate ?? null }),
};

// Sessions
export const sessionsApi = {
  move: (id: number, dayNumber: number) => api.patch(`/sessions/${id}`, { day_number: dayNumber }),
  delete: (id: number) => api.delete(`/sessions/${id}`),
};

// Garmin
export const garminApi = {
  saveCredentials: (email: string, password: string) => api.post("/garmin/credentials", { email, password }),
  getCredentials: () => api.get("/garmin/credentials"),
  deleteCredentials: () => api.delete("/garmin/credentials"),
  sync: (months = 3) => api.post(`/garmin/sync?months=${months}`),
  pushSessions: (sessionIds: number[]) => api.post("/garmin/push/sessions", { session_ids: sessionIds }),
  pushWeek: (planId: number, weekNumber: number) =>
    api.post("/garmin/push/week", { plan_id: planId, week_number: weekNumber }),
  removeSession: (sessionId: number) => api.delete(`/garmin/sessions/${sessionId}`),
};
