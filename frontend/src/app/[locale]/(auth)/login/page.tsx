"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter, Link } from "@/i18n/navigation";
import { motion } from "framer-motion";
import { Mail, Lock, AlertCircle } from "lucide-react";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const t = useTranslations("auth.login");
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  }

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
          <h1 className="text-2xl font-bold text-white tracking-tight">Cadence</h1>
          <p className="text-sm text-slate-400 mt-1">{t("subtitle")}</p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
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
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t("emailPlaceholder")}
                  required
                  className="input pl-10"
                />
              </div>
            </div>

            <div>
              <label className="label">{t("password")}</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="input pl-10"
                />
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
              {loading ? (
                <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              ) : t("submit")}
            </button>
          </form>

          <div className="mt-4 space-y-2 text-center text-sm">
            <p className="text-slate-500">
              {t("noAccount")}{" "}
              <Link href="/register" className="text-brand-400 hover:text-brand-300 font-medium">
                {t("registerLink")}
              </Link>
            </p>
            <p>
              <Link href="/forgot-password" className="text-slate-500 hover:text-slate-300 text-xs">
                {t("forgotPassword")}
              </Link>
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
