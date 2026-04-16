"use client";

import { useTranslations, useLocale } from "next-intl";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { motion } from "framer-motion";
import { Zap, LayoutDashboard, Plus, Settings, LogOut, Globe } from "lucide-react";
import { logout } from "@/lib/auth";
import { cn } from "@/lib/utils";

export function Navbar() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  const NAV_ITEMS = [
    { href: "/dashboard" as const, label: t("dashboard"), icon: LayoutDashboard },
    { href: "/plans/new" as const, label: t("newPlan"), icon: Plus },
    { href: "/settings" as const, label: t("settings"), icon: Settings },
  ];

  function switchLocale() {
    const next = locale === "nl" ? "en" : "nl";
    router.replace(pathname, { locale: next });
  }

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex flex-col w-60 min-h-screen bg-surface-card border-r border-slate-700/50 px-4 py-6 gap-2 fixed left-0 top-0 bottom-0 z-40">
        <Link href="/dashboard" className="flex items-center gap-3 px-2 mb-6">
          <div className="w-9 h-9 rounded-xl bg-brand-500 flex items-center justify-center shadow-lg shadow-brand-500/30">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-bold text-white">RunAI</span>
        </Link>

        <nav className="flex-1 space-y-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200",
                  active
                    ? "bg-brand-500/15 text-brand-300 border border-brand-500/20"
                    : "text-slate-400 hover:bg-surface-elevated hover:text-slate-200"
                )}
              >
                <Icon className="w-4 h-4" />
                {label}
                {active && (
                  <motion.div layoutId="nav-active" className="absolute left-0 w-0.5 h-6 bg-brand-500 rounded-r-full" />
                )}
              </Link>
            );
          })}
        </nav>

        <button
          onClick={switchLocale}
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:bg-surface-elevated hover:text-slate-300 transition-all"
        >
          <Globe className="w-4 h-4" />
          {locale === "nl" ? "English" : "Nederlands"}
        </button>

        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:bg-surface-elevated hover:text-slate-300 transition-all"
        >
          <LogOut className="w-4 h-4" />
          {t("logout")}
        </button>
      </aside>

      {/* Mobile bottom nav */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-surface-card/95 backdrop-blur border-t border-slate-700/50 flex items-center justify-around px-2 py-2 safe-pb">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex flex-col items-center gap-1 px-4 py-1.5 rounded-xl transition-all duration-200",
                active ? "text-brand-400" : "text-slate-500 hover:text-slate-300"
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{label}</span>
              {active && <motion.div layoutId="mob-active" className="w-1 h-1 bg-brand-400 rounded-full" />}
            </Link>
          );
        })}
        <button
          onClick={switchLocale}
          className="flex flex-col items-center gap-1 px-4 py-1.5 rounded-xl text-slate-500 hover:text-slate-300 transition-all"
        >
          <Globe className="w-5 h-5" />
          <span className="text-[10px] font-medium">{locale === "nl" ? "EN" : "NL"}</span>
        </button>
        <button
          onClick={logout}
          className="flex flex-col items-center gap-1 px-4 py-1.5 rounded-xl text-slate-500 hover:text-slate-300 transition-all"
        >
          <LogOut className="w-5 h-5" />
          <span className="text-[10px] font-medium">{t("logout")}</span>
        </button>
      </nav>
    </>
  );
}
