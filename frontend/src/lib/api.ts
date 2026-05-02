import axios, { AxiosError } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT from localStorage on every request; let browser set Content-Type for FormData
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
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
            const locale = window.location.pathname.split("/")[1] || "nl";
            window.location.href = `/${locale}/login`;
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
  forgotPassword: (email: string) => api.post("/auth/forgot-password", { email }),
  resetPassword: (token: string, newPassword: string) => api.post("/auth/reset-password", { token, new_password: newPassword }),
};

// Admin
export const adminApi = {
  getUsers: () => api.get("/admin/users"),
  updateUser: (id: number, data: { is_active?: boolean; is_admin?: boolean; tier?: string }) => api.patch(`/admin/users/${id}`, data),
  deleteUser: (id: number) => api.delete(`/admin/users/${id}`),
  resetPassword: (id: number, newPassword: string) => api.post(`/admin/users/${id}/reset-password`, { new_password: newPassword }),
  getSettings: () => api.get("/admin/settings"),
  updateSettings: (data: { registration_open?: boolean }) => api.patch("/admin/settings", data),
};

// Profile
export const profileApi = {
  get: () => api.get("/auth/profile"),
  update: (data: Partial<{
    name: string; age: number; height_cm: number; weight_kg: number;
    weekly_km: number; weekly_runs: number; injuries: string; max_hr: number;
  }>) => api.patch("/auth/profile", data),
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/auth/profile/avatar", form);
  },
};

// Plans
export const plansApi = {
  list: () => api.get("/plans"),
  get: (publicId: string) => api.get(`/plans/${publicId}`),
  create: (data: any) => api.post("/plans", data),
  update: (publicId: string, data: any) => api.put(`/plans/${publicId}`, data),
  delete: (publicId: string) => api.delete(`/plans/${publicId}`),
  recalculateDates: (publicId: string, startDate?: string) =>
    api.patch(`/plans/${publicId}/recalculate-dates`, { start_date: startDate ?? null }),
  addStrength: (publicId: string, strength: object) =>
    api.post(`/plans/${publicId}/add-strength`, strength),
  previewRegenerate: (publicId: string) =>
    api.post(`/plans/${publicId}/regenerate/preview`),
  regenerate: (publicId: string) =>
    api.post(`/plans/${publicId}/regenerate`),
  bulkEdit: (publicId: string, filter: {
    day_number?: number | null;
    workout_type?: string | null;
    only_future?: boolean;
  }, update: {
    day_number?: number | null;
    target_pace_key?: string | null;
    target_pace_value?: string | null;
    target_pace_delta_seconds?: number | null;
  }) => api.patch(`/plans/${publicId}/sessions/bulk`, { filter, update }),
  reset: (publicId: string) => api.post(`/plans/${publicId}/reset`),
};

// Sessions
export const sessionsApi = {
  move: (id: number, dayNumber: number, weekNumber?: number) =>
    api.patch(`/sessions/${id}`, { day_number: dayNumber, week_number: weekNumber ?? null }),
  delete: (id: number) => api.delete(`/sessions/${id}`),
  updateDetails: (id: number, data: {
    title?: string;
    description?: string;
    distance_km?: number | null;
    duration_minutes?: number | null;
    target_paces?: Record<string, string>;
    scheduled_date?: string;
  }) => api.patch(`/sessions/${id}/details`, data),
  reset: (id: number) => api.post(`/sessions/${id}/reset`),
};

// Friends
export const friendsApi = {
  search: (name: string) => api.post("/friends/search", { name }),
  sendRequest: (addresseeId: number) => api.post(`/friends/request/${addresseeId}`),
  listRequests: () => api.get("/friends/requests"),
  listSent: () => api.get("/friends/sent"),
  acceptRequest: (friendshipId: number) => api.post(`/friends/requests/${friendshipId}/accept`),
  declineRequest: (friendshipId: number) => api.delete(`/friends/requests/${friendshipId}`),
  list: () => api.get("/friends"),
  remove: (friendId: number) => api.delete(`/friends/${friendId}`),
  getActivities: (friendId: number) => api.get(`/friends/${friendId}/activities`),
  getActivity: (friendId: number, activityId: string) => api.get(`/friends/${friendId}/activity/${activityId}`),
};

// Garmin
export const garminApi = {
  saveCredentials: (email: string, password: string) => api.post("/garmin/credentials", { email, password }),
  submitMfa: (mfaCode: string) => api.post("/garmin/submit-mfa", { mfa_code: mfaCode }),
  getCredentials: () => api.get("/garmin/credentials"),
  deleteCredentials: () => api.delete("/garmin/credentials"),
  sync: (months = 3) => api.post(`/garmin/sync?months=${months}`),
  pushSessions: (sessionIds: number[]) => api.post("/garmin/push/sessions", { session_ids: sessionIds }),
  pushWeek: (planId: string, weekNumber: number) =>
    api.post("/garmin/push/week", { plan_id: planId, week_number: weekNumber }),
  removeSession: (sessionId: number) => api.delete(`/garmin/sessions/${sessionId}`),
  autoSync: () => api.post("/garmin/auto-sync"),
  getActivity: (activityId: string) => api.get(`/garmin/activity/${activityId}`),
};
