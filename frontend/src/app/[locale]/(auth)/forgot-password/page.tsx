"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { motion } from "framer-motion";
import { Mail, AlertCircle, CheckCircle2, ArrowLeft } from "lucide-react";
import { authApi } from "@/lib/api";

export default function ForgotPasswordPage() {
  const t = useTranslations("auth.forgotPassword");
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await authApi.forgotPassword(email);
      setSent(true);
    } catch {
      setError(t("error"));
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
              <rect x="1" y="10" width="3.5" height="7" rx="1.5" fill="white"/>
              <rect x="7" y="3" width="3.5" height="14" rx="1.5" fill="white"/>
              <rect x="13" y="7" width="3.5" height="10" rx="1.5" fill="white"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Metriq</h1>
        </div>

        <div className="card">
          {sent ? (
            <div className="text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-brand-500/15 border border-brand-500/30 flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-6 h-6 text-brand-400" />
              </div>
              <h2 className="font-bold text-white text-lg">{t("sentTitle")}</h2>
              <p className="text-sm text-slate-400">{t("sentBody")}</p>
              <Link href="/login" className="btn-secondary w-full mt-2 flex items-center justify-center gap-2">
                <ArrowLeft className="w-4 h-4" />
                {t("backToLogin")}
              </Link>
            </div>
          ) : (
            <>
              <h2 className="font-bold text-white text-lg mb-1">{t("title")}</h2>
              <p className="text-sm text-slate-400 mb-5">{t("subtitle")}</p>

              <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                  <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2.5 text-sm text-red-400">
                    <AlertCircle className="w-4 h-4 shrink-0" />{error}
                  </div>
                )}

                <div>
                  <label className="label">{t("email")}</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com" required className="input pl-10"
                    />
                  </div>
                </div>

                <button type="submit" disabled={loading} className="btn-primary w-full">
                  {loading
                    ? <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    : t("submit")
                  }
                </button>
              </form>

              <p className="text-center text-sm text-slate-500 mt-4">
                <Link href="/login" className="text-brand-400 hover:text-brand-300 font-medium flex items-center justify-center gap-1">
                  <ArrowLeft className="w-3.5 h-3.5" />
                  {t("backToLogin")}
                </Link>
              </p>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}
