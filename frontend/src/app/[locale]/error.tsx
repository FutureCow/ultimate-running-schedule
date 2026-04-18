"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import { Link } from "@/i18n/navigation";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Application error:", error);
  }, [error]);

  const t = useTranslations("errors");

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
          <AlertTriangle className="w-8 h-8 text-red-400" />
        </div>
        <h1 className="text-xl font-bold text-white mb-2">{t("title")}</h1>
        <p className="text-sm text-slate-400 mb-6">{t("subtitle")}</p>
        <div className="flex items-center justify-center gap-3">
          <button onClick={reset} className="btn-secondary gap-2">
            <RefreshCw className="w-4 h-4" />
            {t("retry")}
          </button>
          <Link href="/dashboard" className="btn-ghost gap-2">
            <Home className="w-4 h-4" />
            {t("home")}
          </Link>
        </div>
      </div>
    </div>
  );
}
