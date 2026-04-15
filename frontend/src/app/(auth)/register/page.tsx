"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Mail, Lock, Zap, AlertCircle, CheckCircle2 } from "lucide-react";
import { register, login } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== confirm) { setError("Wachtwoorden komen niet overeen"); return; }
    if (password.length < 8) { setError("Wachtwoord moet minstens 8 tekens lang zijn"); return; }
    setLoading(true);
    try {
      await register(email, password);
      await login(email, password);
      router.replace("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Registratie mislukt. Probeer opnieuw.");
    } finally {
      setLoading(false);
    }
  }

  const strength = password.length === 0 ? 0 : password.length < 8 ? 1 : password.length < 12 ? 2 : 3;
  const strengthColors = ["", "bg-red-500", "bg-yellow-500", "bg-brand-500"];
  const strengthLabels = ["", "Zwak", "Matig", "Sterk"];

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
          <div className="w-12 h-12 rounded-2xl bg-brand-500 flex items-center justify-center mb-3 shadow-lg shadow-brand-500/30">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Account aanmaken</h1>
          <p className="text-sm text-slate-400 mt-1">Start met je AI hardloopschema</p>
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
              <label className="label">E-mailadres</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder="jij@example.com" required className="input pl-10" />
              </div>
            </div>

            <div>
              <label className="label">Wachtwoord</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 8 tekens" required className="input pl-10" />
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
              <label className="label">Bevestig wachtwoord</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Herhaal wachtwoord" required className="input pl-10" />
                {confirm && confirm === password && (
                  <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-400" />
                )}
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
              {loading
                ? <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                : "Account aanmaken"
              }
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-4">
            Al een account?{" "}
            <Link href="/login" className="text-brand-400 hover:text-brand-300 font-medium">
              Inloggen
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
