"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Watch, Trash2, RefreshCw, CheckCircle2, AlertCircle, Lock } from "lucide-react";
import { garminApi } from "@/lib/api";
import { GarminStatus } from "@/types";
import { Navbar } from "@/components/ui/Navbar";
import { format, parseISO } from "date-fns";
import { nl } from "date-fns/locale";

export default function SettingsPage() {
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
    onError: (e: any) => setSaveError(e?.response?.data?.detail || "Opslaan mislukt"),
  });

  const deleteMutation = useMutation({
    mutationFn: () => garminApi.deleteCredentials(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["garmin-status"] }),
  });

  const syncMutation = useMutation({
    mutationFn: () => garminApi.sync(3),
    onSuccess: (res) => setSyncStatus({ activities: res.data.activity_count }),
    onError: (e: any) => setSyncStatus({ error: e?.response?.data?.detail || "Sync mislukt" }),
  });

  return (
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Instellingen</h1>
          <p className="text-sm text-slate-400 mt-1">Beheer je Garmin Connect koppeling</p>
        </div>

        {/* Garmin section */}
        <div className="card space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <Watch className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h2 className="font-bold text-white">Garmin Connect</h2>
              <p className="text-xs text-slate-400">Credentials worden versleuteld opgeslagen</p>
            </div>
          </div>

          {isLoading ? (
            <div className="h-8 flex items-center">
              <span className="w-5 h-5 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            </div>
          ) : garminStatus ? (
            <div className="space-y-4">
              {/* Connected status */}
              <div className="flex items-center justify-between rounded-xl bg-brand-500/10 border border-brand-500/20 px-4 py-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-brand-400" />
                  <span className="text-sm font-medium text-brand-300">Gekoppeld</span>
                </div>
                {garminStatus.last_sync_at && (
                  <span className="text-xs text-slate-500">
                    Sync: {format(parseISO(garminStatus.last_sync_at), "d MMM HH:mm", { locale: nl })}
                  </span>
                )}
              </div>

              {/* Sync result */}
              {syncStatus && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className={`rounded-lg px-3 py-2 text-sm ${syncStatus.error ? "bg-red-500/10 border border-red-500/20 text-red-400" : "bg-brand-500/10 border border-brand-500/20 text-brand-300"}`}
                >
                  {syncStatus.error || `✓ ${syncStatus.activities} activiteiten gesynchroniseerd`}
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
                  Sync activiteiten
                </button>

                <button
                  onClick={() => { if (confirm("Garmin credentials verwijderen?")) deleteMutation.mutate(); }}
                  disabled={deleteMutation.isPending}
                  className="btn-ghost text-red-400 hover:text-red-300 text-sm"
                >
                  <Trash2 className="w-4 h-4" /> Verwijderen
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
                Je Garmin credentials worden versleuteld opgeslagen met AES-256 (Fernet) en nooit in plain text bewaard.
              </div>

              {saveError && (
                <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2.5 text-sm text-red-400">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {saveError}
                </div>
              )}

              <div>
                <label className="label">Garmin e-mailadres</label>
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
                <label className="label">Garmin wachtwoord</label>
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
                Koppel Garmin
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
