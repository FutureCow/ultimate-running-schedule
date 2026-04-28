"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import {
  Shield, Users, Trash2, RefreshCw, CheckCircle2, AlertCircle,
  ToggleLeft, ToggleRight, Key, UserCheck, UserX,
} from "lucide-react";
import { adminApi } from "@/lib/api";
import { Navbar } from "@/components/ui/Navbar";
import { format, parseISO } from "date-fns";
import { isLoggedIn } from "@/lib/auth";
import { useEffect } from "react";

interface AdminUser {
  id: number;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  tier: string;
  plan_count: number;
  created_at: string;
}

const TIER_LABELS: Record<string, { label: string; color: string }> = {
  base:  { label: "Base",  color: "text-slate-400 border-slate-600/40 bg-slate-500/10" },
  tempo: { label: "Tempo", color: "text-blue-400  border-blue-500/30  bg-blue-500/10"  },
  elite: { label: "Elite", color: "text-brand-400 border-brand-500/30 bg-brand-500/10" },
};

export default function AdminPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const [resetTarget, setResetTarget] = useState<AdminUser | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetDone, setResetDone] = useState(false);
  const [resetError, setResetError] = useState("");

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, []);

  const { data: users = [], isLoading: usersLoading, error: usersError } = useQuery<AdminUser[]>({
    queryKey: ["admin-users"],
    queryFn: () => adminApi.getUsers().then((r) => r.data),
    retry: false,
  });

  const { data: adminSettings } = useQuery({
    queryKey: ["admin-settings"],
    queryFn: () => adminApi.getSettings().then((r) => r.data),
    retry: false,
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      adminApi.updateUser(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const toggleAdminMutation = useMutation({
    mutationFn: ({ id, is_admin }: { id: number; is_admin: boolean }) =>
      adminApi.updateUser(id, { is_admin }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const setTierMutation = useMutation({
    mutationFn: ({ id, tier }: { id: number; tier: string }) =>
      adminApi.updateUser(id, { tier }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const resetPasswordMutation = useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) =>
      adminApi.resetPassword(id, password),
    onSuccess: () => { setResetDone(true); setResetError(""); },
    onError: (e: any) => setResetError(e?.response?.data?.detail || "Failed"),
  });

  const toggleRegistrationMutation = useMutation({
    mutationFn: (open: boolean) => adminApi.updateSettings({ registration_open: open }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-settings"] }),
  });

  // 403 = not admin → redirect
  if (usersError) {
    return (
      <div className="min-h-screen lg:pl-60">
        <Navbar />
        <main className="px-4 py-6 max-w-4xl mx-auto">
          <div className="card text-center py-16">
            <Shield className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <p className="text-red-400 font-semibold">Geen toegang — admin vereist</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-5xl mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-brand-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Admin</h1>
            <p className="text-sm text-slate-400">Gebruikersbeheer en app-instellingen</p>
          </div>
        </div>

        {/* App settings */}
        <div className="card space-y-4">
          <h2 className="font-bold text-white flex items-center gap-2">
            <ToggleRight className="w-4 h-4 text-brand-400" />
            App-instellingen
          </h2>
          <div className="flex items-center justify-between rounded-xl bg-surface-elevated border border-slate-700/40 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-white">Nieuwe registraties</p>
              <p className="text-xs text-slate-500">Staat toe dat nieuwe gebruikers zich registreren</p>
            </div>
            <button
              onClick={() => toggleRegistrationMutation.mutate(!adminSettings?.registration_open)}
              disabled={toggleRegistrationMutation.isPending}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold transition-all ${
                adminSettings?.registration_open
                  ? "bg-brand-500/15 text-brand-300 border border-brand-500/30"
                  : "bg-red-500/10 text-red-400 border border-red-500/20"
              }`}
            >
              {adminSettings?.registration_open
                ? <><ToggleRight className="w-4 h-4" /> Aan</>
                : <><ToggleLeft className="w-4 h-4" /> Uit</>
              }
            </button>
          </div>
        </div>

        {/* Users table */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-brand-400" />
              Gebruikers ({users.length})
            </h2>
          </div>

          {usersLoading ? (
            <div className="flex items-center justify-center py-10">
              <span className="w-6 h-6 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            </div>
          ) : (
            <div className="space-y-2">
              {users.map((user) => (
                <motion.div
                  key={user.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-3 rounded-xl border border-slate-700/40 bg-surface-elevated px-4 py-3 flex-wrap"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-medium text-white truncate">{user.email}</p>
                      {user.is_admin && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-brand-500/15 text-brand-400 border border-brand-500/25">
                          ADMIN
                        </span>
                      )}
                      {!user.is_active && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                          INACTIEF
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {user.plan_count} {user.plan_count === 1 ? "plan" : "plannen"} ·{" "}
                      {format(parseISO(user.created_at), "d MMM yyyy")}
                    </p>
                  </div>

                  {/* Tier selector */}
                  <select
                    value={user.tier || "elite"}
                    onChange={(e) => setTierMutation.mutate({ id: user.id, tier: e.target.value })}
                    disabled={setTierMutation.isPending}
                    className={`text-[11px] font-bold px-2 py-1 rounded-lg border bg-transparent cursor-pointer focus:outline-none ${TIER_LABELS[user.tier]?.color ?? ""}`}
                  >
                    <option value="base">Base</option>
                    <option value="tempo">Tempo</option>
                    <option value="elite">Elite</option>
                  </select>

                  <div className="flex items-center gap-1.5 flex-wrap">
                    {/* Toggle active */}
                    <button
                      onClick={() => toggleActiveMutation.mutate({ id: user.id, is_active: !user.is_active })}
                      disabled={toggleActiveMutation.isPending}
                      title={user.is_active ? "Deactiveren" : "Activeren"}
                      className={`p-1.5 rounded-lg transition-all ${
                        user.is_active
                          ? "text-emerald-400 hover:bg-emerald-500/10"
                          : "text-slate-500 hover:bg-slate-600/30"
                      }`}
                    >
                      {user.is_active ? <UserCheck className="w-4 h-4" /> : <UserX className="w-4 h-4" />}
                    </button>

                    {/* Toggle admin */}
                    <button
                      onClick={() => toggleAdminMutation.mutate({ id: user.id, is_admin: !user.is_admin })}
                      disabled={toggleAdminMutation.isPending}
                      title={user.is_admin ? "Admin intrekken" : "Admin maken"}
                      className={`p-1.5 rounded-lg transition-all ${
                        user.is_admin
                          ? "text-brand-400 hover:bg-brand-500/10"
                          : "text-slate-500 hover:bg-slate-600/30"
                      }`}
                    >
                      <Shield className="w-4 h-4" />
                    </button>

                    {/* Reset password */}
                    <button
                      onClick={() => { setResetTarget(user); setNewPassword(""); setResetDone(false); setResetError(""); }}
                      title="Wachtwoord resetten"
                      className="p-1.5 rounded-lg text-slate-500 hover:text-amber-400 hover:bg-amber-500/10 transition-all"
                    >
                      <Key className="w-4 h-4" />
                    </button>

                    {/* Delete */}
                    <button
                      onClick={() => { if (confirm(`Gebruiker ${user.email} verwijderen?`)) deleteMutation.mutate(user.id); }}
                      disabled={deleteMutation.isPending}
                      title="Verwijderen"
                      className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Password reset modal */}
        {resetTarget && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4" onClick={() => setResetTarget(null)}>
            <div className="card w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
              <h3 className="font-bold text-white mb-1">Wachtwoord resetten</h3>
              <p className="text-sm text-slate-400 mb-4">{resetTarget.email}</p>

              {resetDone ? (
                <div className="flex items-center gap-2 text-brand-400 text-sm">
                  <CheckCircle2 className="w-4 h-4" /> Wachtwoord opgeslagen
                </div>
              ) : (
                <div className="space-y-3">
                  {resetError && (
                    <div className="flex items-center gap-2 text-red-400 text-sm">
                      <AlertCircle className="w-4 h-4" />{resetError}
                    </div>
                  )}
                  <input
                    type="text"
                    className="input"
                    placeholder="Nieuw wachtwoord (min. 8 tekens)"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => setResetTarget(null)}
                      className="btn-secondary flex-1"
                    >
                      Annuleren
                    </button>
                    <button
                      onClick={() => resetPasswordMutation.mutate({ id: resetTarget.id, password: newPassword })}
                      disabled={newPassword.length < 8 || resetPasswordMutation.isPending}
                      className="btn-primary flex-1"
                    >
                      {resetPasswordMutation.isPending
                        ? <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                        : "Opslaan"
                      }
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
