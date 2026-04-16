"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useTranslations, useLocale } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Watch, Trash2, RefreshCw, CheckCircle2, AlertCircle, Lock, Globe } from "lucide-react";
import { garminApi } from "@/lib/api";
import { GarminStatus } from "@/types";
import { Navbar } from "@/components/ui/Navbar";
import { format, parseISO } from "date-fns";
import { nl, enUS } from "date-fns/locale";

export default function SettingsPage() {
  const t = useTranslations("settings");
  const tg = useTranslations("settings.garmin");
  const locale = useLocale();
  const router = useRouter();
  const dateFnsLocale = locale === "nl" ? nl : enUS;

  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [saveError, setSaveError] = useState("");
  const [syncStatus, setSyncStatus] = useState<{ activities?: number; error?: string } | null>(null);

  const { data: garminStatus, isLoading } = useQuery<GarminStatus>({
    queryKey: ["garmin-status"],
    queryFn: () => garminApi.getCredentials().then((r) => r.data),
    retry: false,
  });

  const saveMutation = useMutation({
    mutationFn: () => garminApi.saveCredentials(email, password),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["garmin-status"] }); setEmail(""); setPassword(""); setSaveError(""); },
    onError: (e: any) => setSaveError(e?.response?.data?.detail || tg("saveFailed")),
  });

  const deleteMutation = useMutation({
    mutationFn: () => garminApi.deleteCredentials(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["garmin-status"] }),
  });

  const syncMutation = useMutation({
    mutationFn: () => garminApi.sync(3),
    onSuccess: (res) => setSyncStatus({ activities: res.data.activity_count }),
    onError: (e: any) => setSyncStatus({ error: e?.response?.data?.detail || tg("syncFailed") }),
  });

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

          {isLoading ? (
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
                  {syncStatus.error || tg("syncSuccess", { count: syncStatus.activities ?? 0 })}
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
