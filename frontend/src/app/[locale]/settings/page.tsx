"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useTranslations, useLocale } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Watch, Trash2, RefreshCw, CheckCircle2, AlertCircle, Lock, Globe, User, Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "@/components/ui/ThemeProvider";
import { garminApi, profileApi } from "@/lib/api";
import { GarminStatus, UserProfile } from "@/types";
import { Navbar } from "@/components/ui/Navbar";
import { format, parseISO } from "date-fns";
import { nl, enUS } from "date-fns/locale";

export default function SettingsPage() {
  const t = useTranslations("settings");
  const tg = useTranslations("settings.garmin");
  const tp = useTranslations("settings.profile");
  const locale = useLocale();
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const dateFnsLocale = locale === "nl" ? nl : enUS;

  const qc = useQueryClient();

  // Garmin state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [saveError, setSaveError] = useState("");
  const [syncStatus, setSyncStatus] = useState<{ activities?: number; weeklyKm?: number; error?: string } | null>(null);

  // Profile state
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profile, setProfile] = useState<UserProfile>({});
  const [profileLoaded, setProfileLoaded] = useState(false);

  const { data: garminStatus, isLoading: garminLoading } = useQuery<GarminStatus>({
    queryKey: ["garmin-status"],
    queryFn: () => garminApi.getCredentials().then((r) => r.data),
    retry: false,
  });

  const { data: profileData, isLoading: profileLoading } = useQuery<UserProfile>({
    queryKey: ["user-profile"],
    queryFn: () => profileApi.get().then((r) => r.data),
  });

  // Pre-populate form once profile data arrives
  useEffect(() => {
    if (profileData && !profileLoaded) {
      setProfile(profileData);
      setProfileLoaded(true);
    }
  }, [profileData, profileLoaded]);

  // Auto-sync Garmin if stale (>1 hour), update weekly_km in form
  useEffect(() => {
    if (!garminStatus) return;
    garminApi.autoSync().then((res) => {
      const d = res.data;
      if (d.synced && d.avg_weekly_km != null) {
        setProfile((p) => ({ ...p, weekly_km: d.avg_weekly_km }));
        setSyncStatus({ activities: d.activity_count, weeklyKm: d.avg_weekly_km });
        qc.invalidateQueries({ queryKey: ["user-profile"] });
      }
    }).catch(() => {/* silent — auto-sync is best-effort */});
  }, [garminStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  const saveMutation = useMutation({
    mutationFn: () => garminApi.saveCredentials(email, password),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["garmin-status"] });
      setEmail(""); setPassword(""); setSaveError("");
    },
    onError: (e: any) => setSaveError(e?.response?.data?.detail || tg("saveFailed")),
  });

  const deleteMutation = useMutation({
    mutationFn: () => garminApi.deleteCredentials(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["garmin-status"] }),
  });

  const syncMutation = useMutation({
    mutationFn: () => garminApi.sync(3),
    onSuccess: (res) => {
      const weeklyKm = res.data.summary?.avg_weekly_km;
      setSyncStatus({ activities: res.data.activity_count, weeklyKm });
      if (weeklyKm != null) {
        setProfile((p) => ({ ...p, weekly_km: weeklyKm }));
        qc.invalidateQueries({ queryKey: ["user-profile"] });
      }
    },
    onError: (e: any) => setSyncStatus({ error: e?.response?.data?.detail || tg("syncFailed") }),
  });

  const profileMutation = useMutation({
    mutationFn: () => profileApi.update({
      age: profile.age ?? undefined,
      height_cm: profile.height_cm ?? undefined,
      weight_kg: profile.weight_kg ?? undefined,
      weekly_km: profile.weekly_km ?? undefined,
      weekly_runs: profile.weekly_runs ?? undefined,
      injuries: profile.injuries ?? undefined,
    }),
    onSuccess: () => {
      setProfileSaved(true); setProfileError("");
      setTimeout(() => setProfileSaved(false), 2500);
    },
    onError: (e: any) => setProfileError(e?.response?.data?.detail || tp("saveFailed")),
  });

  const garminConnected = !!garminStatus && !garminLoading;

  return (
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">{t("title")}</h1>
          <p className="text-sm text-slate-400 mt-1">{t("subtitle")}</p>
        </div>

        {/* Language switcher */}
        <div className="card space-y-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
              <Globe className="w-5 h-5 text-brand-400" />
            </div>
            <h2 className="font-bold text-white">{t("language.title")}</h2>
          </div>
          <div className="flex gap-2">
            {(["nl", "en"] as const).map((loc) => (
              <button
                key={loc}
                onClick={() => router.replace("/settings", { locale: loc })}
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                  locale === loc
                    ? "bg-brand-500 text-white"
                    : "bg-surface-elevated text-slate-400 hover:text-white"
                }`}
              >
                {loc === "nl" ? "🇳🇱 Nederlands" : "🇬🇧 English"}
              </button>
            ))}
          </div>
        </div>

        {/* Theme switcher */}
        <div className="card space-y-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
              <Sun className="w-5 h-5 text-brand-400" />
            </div>
            <h2 className="font-bold text-white">{t("theme.title")}</h2>
          </div>
          <div className="flex gap-2">
            {([
              { value: "light", label: t("theme.light"), icon: <Sun className="w-4 h-4" /> },
              { value: "dark",  label: t("theme.dark"),  icon: <Moon className="w-4 h-4" /> },
              { value: "system", label: t("theme.system"), icon: <Monitor className="w-4 h-4" /> },
            ] as const).map(({ value, label, icon }) => (
              <button
                key={value}
                onClick={() => setTheme(value)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                  theme === value
                    ? "bg-brand-500 text-white"
                    : "bg-surface-elevated text-slate-400 hover:text-white"
                }`}
              >
                {icon}{label}
              </button>
            ))}
          </div>
        </div>

        {/* Profile section */}
        <div className="card space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
              <User className="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <h2 className="font-bold text-white">{tp("title")}</h2>
              <p className="text-xs text-slate-400">{tp("subtitle")}</p>
            </div>
          </div>

          {profileLoading ? (
            <div className="h-8 flex items-center">
              <span className="w-5 h-5 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="label">{tp("age")}</label>
                  <input type="number" className="input text-center" placeholder="30"
                    value={profile.age ?? ""}
                    onChange={(e) => setProfile((p) => ({ ...p, age: e.target.value ? Number(e.target.value) : null }))}
                  />
                </div>
                <div>
                  <label className="label">{tp("height")}</label>
                  <input type="number" className="input text-center" placeholder="175"
                    value={profile.height_cm ?? ""}
                    onChange={(e) => setProfile((p) => ({ ...p, height_cm: e.target.value ? Number(e.target.value) : null }))}
                  />
                </div>
                <div>
                  <label className="label">{tp("weight")}</label>
                  <input type="number" step="0.1" className="input text-center" placeholder="70"
                    value={profile.weight_kg ?? ""}
                    onChange={(e) => setProfile((p) => ({ ...p, weight_kg: e.target.value ? Number(e.target.value) : null }))}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label flex items-center gap-1.5">
                    {tp("weeklyKm")}
                    {garminConnected && (
                      <span className="text-[10px] font-normal text-brand-400/80 bg-brand-500/10 px-1.5 py-0.5 rounded-full">
                        Garmin
                      </span>
                    )}
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    className={`input ${garminConnected ? "text-brand-300" : ""}`}
                    placeholder="40"
                    value={profile.weekly_km ?? ""}
                    onChange={(e) => setProfile((p) => ({ ...p, weekly_km: e.target.value ? Number(e.target.value) : null }))}
                  />
                  {garminConnected && (
                    <p className="text-[10px] text-slate-600 mt-1">{tp("weeklyKmGarminHint")}</p>
                  )}
                </div>
                <div>
                  <label className="label">{tp("weeklyRuns")}</label>
                  <input type="number" className="input" placeholder="4"
                    value={profile.weekly_runs ?? ""}
                    onChange={(e) => setProfile((p) => ({ ...p, weekly_runs: e.target.value ? Number(e.target.value) : null }))}
                  />
                </div>
              </div>

              <div>
                <label className="label">{tp("injuries")}</label>
                <textarea rows={2} className="input resize-none" placeholder={tp("injuriesPlaceholder")}
                  value={profile.injuries ?? ""}
                  onChange={(e) => setProfile((p) => ({ ...p, injuries: e.target.value || null }))}
                />
              </div>

              {profileError && (
                <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2.5 text-sm text-red-400">
                  <AlertCircle className="w-4 h-4 shrink-0" />{profileError}
                </div>
              )}

              <button
                onClick={() => profileMutation.mutate()}
                disabled={profileMutation.isPending}
                className="btn-primary"
              >
                {profileMutation.isPending
                  ? <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  : profileSaved
                  ? <CheckCircle2 className="w-4 h-4" />
                  : <User className="w-4 h-4" />
                }
                {profileSaved ? tp("saved") : tp("save")}
              </button>
            </>
          )}
        </div>

        {/* Garmin section */}
        <div className="card space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <Watch className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h2 className="font-bold text-white">{tg("title")}</h2>
              <p className="text-xs text-slate-400">{tg("encryptedNote")}</p>
            </div>
          </div>

          {garminLoading ? (
            <div className="h-8 flex items-center">
              <span className="w-5 h-5 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            </div>
          ) : garminStatus ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between rounded-xl bg-brand-500/10 border border-brand-500/20 px-4 py-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-brand-400" />
                  <span className="text-sm font-medium text-brand-300">{tg("connected")}</span>
                </div>
                {garminStatus.last_sync_at && (
                  <span className="text-xs text-slate-500">
                    {tg("syncDate", { date: format(parseISO(garminStatus.last_sync_at), "d MMM HH:mm", { locale: dateFnsLocale }) })}
                  </span>
                )}
              </div>

              {syncStatus && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className={`rounded-lg px-3 py-2 text-sm ${syncStatus.error ? "bg-red-500/10 border border-red-500/20 text-red-400" : "bg-brand-500/10 border border-brand-500/20 text-brand-300"}`}
                >
                  {syncStatus.error
                    ? syncStatus.error
                    : `${tg("syncSuccess", { count: syncStatus.activities ?? 0 })}${syncStatus.weeklyKm != null ? ` · ${syncStatus.weeklyKm} km/week` : ""}`
                  }
                </motion.div>
              )}

              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => syncMutation.mutate()}
                  disabled={syncMutation.isPending}
                  className="btn-secondary text-sm"
                >
                  {syncMutation.isPending
                    ? <span className="w-4 h-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
                    : <RefreshCw className="w-4 h-4" />
                  }
                  {tg("syncButton")}
                </button>

                <button
                  onClick={() => { if (confirm(tg("deleteConfirm"))) deleteMutation.mutate(); }}
                  disabled={deleteMutation.isPending}
                  className="btn-ghost text-red-400 hover:text-red-300 text-sm"
                >
                  <Trash2 className="w-4 h-4" /> {tg("deleteButton")}
                </button>
              </div>
            </div>
          ) : (
            <form
              onSubmit={(e) => { e.preventDefault(); saveMutation.mutate(); }}
              className="space-y-4"
            >
              <div className="flex items-start gap-2 text-xs text-slate-500 rounded-xl bg-surface-elevated px-3 py-2.5">
                <Lock className="w-3.5 h-3.5 mt-0.5 shrink-0 text-brand-400" />
                {tg("securityNote")}
              </div>

              {saveError && (
                <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2.5 text-sm text-red-400">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {saveError}
                </div>
              )}

              <div>
                <label className="label">{tg("emailLabel")}</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="garmin@example.com"
                  required
                  className="input"
                />
              </div>
              <div>
                <label className="label">{tg("passwordLabel")}</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="input"
                />
              </div>

              <button type="submit" disabled={saveMutation.isPending} className="btn-primary">
                {saveMutation.isPending
                  ? <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  : <Watch className="w-4 h-4" />
                }
                {tg("connectButton")}
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
