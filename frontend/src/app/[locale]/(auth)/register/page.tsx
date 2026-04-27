"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter, Link } from "@/i18n/navigation";
import { motion } from "framer-motion";
import { Mail, Lock, AlertCircle, CheckCircle2 } from "lucide-react";
import { register, login } from "@/lib/auth";

export default function RegisterPage() {
  const t = useTranslations("auth.register");
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== confirm) { setError(t("errors.mismatch")); return; }
    if (password.length < 8) { setError(t("errors.tooShort")); return; }
    setLoading(true);
    try {
      await register(email, password);
      await login(email, password);
      router.replace("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail || t("errors.failed"));
    } finally {
      setLoading(false);
    }
  }

  const strength = password.length === 0 ? 0 : password.length < 8 ? 1 : password.length < 12 ? 2 : 3;
  const strengthColors = ["", "bg-red-500", "bg-yellow-500", "bg-brand-500"];
  const strengthLabels = ["", t("strength.weak"), t("strength.fair"), t("strength.strong")];

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="absolute inset-0 bg-gradient-to-br from-brand-950/40 via-surface to-surface pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-sm"
      >
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-brand-500 flex items-center justify-center mb-4 shadow-lg shadow-brand-500/30">
            <svg viewBox="0 0 18 18" fill="none" className="w-8 h-8">
              <rect x="1"  y="10" width="3.5" height="7"  rx="1.5" fill="white"/>
              <rect x="7"  y="3"  width="3.5" height="14" rx="1.5" fill="white"/>
              <rect x="13" y="7"  width="3.5" height="10" rx="1.5" fill="white"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Metriq</h1>
          <p className="text-sm text-slate-400 mt-1">{t("subtitle")}</p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2.5 text-sm text-red-400"
              >
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </motion.div>
            )}

            <div>
              <label className="label">{t("email")}</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder={t("emailPlaceholder")} required className="input pl-10" />
              </div>
            </div>

            <div>
              <label className="label">{t("password")}</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder={t("passwordPlaceholder")} required className="input pl-10" />
              </div>
              {password && (
                <div className="mt-2 space-y-1">
                  <div className="flex gap-1">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className={`h-1 flex-1 rounded-full transition-colors duration-300 ${i <= strength ? strengthColors[strength] : "bg-slate-700"}`} />
                    ))}
                  </div>
                  <p className={`text-xs ${strength === 3 ? "text-brand-400" : strength === 2 ? "text-yellow-400" : "text-red-400"}`}>
                    {strengthLabels[strength]}
                  </p>
                </div>
              )}
            </div>

            <div>
              <label className="label">{t("confirmPassword")}</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)}
                  placeholder={t("confirmPlaceholder")} required className="input pl-10" />
                {confirm && confirm === password && (
                  <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-400" />
                )}
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
              {loading
                ? <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                : t("submit")
              }
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-4">
            {t("hasAccount")}{" "}
            <Link href="/login" className="text-brand-400 hover:text-brand-300 font-medium">
              {t("loginLink")}
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
