"use client";

import { useRef, useState, useEffect } from "react";
import { useTranslations, useLocale } from "next-intl";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { motion } from "framer-motion";
import { LayoutDashboard, Plus, Settings, LogOut, ChevronDown, Sun, Moon, Calendar, BarChart2 } from "lucide-react";
import { logout } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { useTheme } from "@/components/ui/ThemeProvider";
import { useQuery } from "@tanstack/react-query";
import { plansApi, garminApi } from "@/lib/api";
import { Plan } from "@/types";

const LOCALES = [
  { code: "nl", flag: "🇳🇱", label: "Nederlands", short: "NL" },
  { code: "en", flag: "🇬🇧", label: "English",    short: "EN" },
] as const;

const APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION ?? "1";

export function Navbar() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  const { resolved, setTheme } = useTheme();
  const [langOpen, setLangOpen] = useState(false);

  const { data: plans = [] } = useQuery<Plan[]>({
    queryKey: ["plans"],
    queryFn: () => plansApi.list().then((r) => r.data),
  });
  const activePlan = plans[0] ?? null;
  const langRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (langRef.current && !langRef.current.contains(e.target as Node)) {
        setLangOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    garminApi.autoSync().catch(() => {});
    const interval = setInterval(() => garminApi.autoSync().catch(() => {}), 60 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  function switchLocale(code: string) {
    setLangOpen(false);
    if (code !== locale) router.replace(pathname, { locale: code });
  }

  const currentLang = LOCALES.find((l) => l.code === locale) ?? LOCALES[0];

  const NAV_ITEMS = [
    { href: "/dashboard" as const, label: t("dashboard"), icon: LayoutDashboard },
    ...(activePlan
      ? [{ href: `/plans/${activePlan.public_id}` as any, label: t("myPlan"), icon: Calendar }]
      : []),
    { href: "/plans/new" as const, label: t("newPlan"), icon: Plus },
    { href: "/analyse" as const, label: t("analyse"), icon: BarChart2 },
    { href: "/settings" as const, label: t("settings"), icon: Settings },
  ];

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex flex-col w-60 min-h-screen bg-surface-card border-r border-slate-700/50 px-4 py-6 gap-2 fixed left-0 top-0 bottom-0 z-40">
        <Link href="/dashboard" className="flex items-center gap-3 px-2 mb-6">
          <div className="w-9 h-9 rounded-xl bg-brand-500 flex items-center justify-center shadow-lg shadow-brand-500/30 shrink-0">
            {/* Metriq logo: drie ritmische balken */}
            <svg viewBox="0 0 18 18" fill="none" className="w-5 h-5">
              <rect x="1"  y="10" width="3.5" height="7"  rx="1.5" fill="white"/>
              <rect x="7"  y="3"  width="3.5" height="14" rx="1.5" fill="white"/>
              <rect x="13" y="7"  width="3.5" height="10" rx="1.5" fill="white"/>
            </svg>
          </div>
          <div>
            <span className="text-lg font-bold text-white leading-tight block">Metriq</span>
            <span className="text-[10px] text-brand-400/80 font-medium leading-tight block">
              {t("subtitle")}
            </span>
          </div>
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

        {/* Language dropdown */}
        <div ref={langRef} className="relative">
          <button
            onClick={() => setLangOpen((v) => !v)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:bg-surface-elevated hover:text-slate-200 transition-all"
          >
            <span className="text-base leading-none">{currentLang.flag}</span>
            <span className="flex-1 text-left">{currentLang.label}</span>
            <ChevronDown className={cn("w-3.5 h-3.5 transition-transform duration-200", langOpen && "rotate-180")} />
          </button>
          {langOpen && (
            <div className="absolute bottom-full mb-1 left-0 right-0 bg-surface-elevated border border-slate-700/60 rounded-xl overflow-hidden shadow-xl">
              {LOCALES.map((l) => (
                <button
                  key={l.code}
                  onClick={() => switchLocale(l.code)}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-colors",
                    l.code === locale
                      ? "bg-brand-500/10 text-brand-300"
                      : "text-slate-400 hover:bg-slate-700/50 hover:text-slate-200"
                  )}
                >
                  <span className="text-base leading-none">{l.flag}</span>
                  {l.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Theme toggle */}
        <button
          onClick={() => setTheme(resolved === "dark" ? "light" : "dark")}
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:bg-surface-elevated hover:text-slate-300 transition-all"
          title={resolved === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {resolved === "dark"
            ? <Sun className="w-4 h-4" />
            : <Moon className="w-4 h-4" />
          }
          {resolved === "dark" ? "Light mode" : "Dark mode"}
        </button>

        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:bg-surface-elevated hover:text-slate-300 transition-all"
        >
          <LogOut className="w-4 h-4" />
          {t("logout")}
        </button>

        <p className="text-center text-[10px] text-slate-700 mt-1">v{APP_VERSION}</p>
      </aside>

      {/* Mobile bottom nav */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-surface-card/95 backdrop-blur border-t border-slate-700/50 flex items-center justify-around px-2 py-2 safe-pb">
        {[
          { href: "/dashboard" as const, label: t("dashboard"), icon: LayoutDashboard },
          activePlan
            ? { href: `/plans/${activePlan.public_id}` as any, label: t("myPlan"), icon: Calendar }
            : { href: "/plans/new" as const, label: t("newPlan"), icon: Plus },
          { href: "/settings" as const, label: t("settings"), icon: Settings },
        ].map(({ href, label, icon: Icon }) => {
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

        {(() => {
          const active = pathname.startsWith("/analyse");
          return (
            <Link
              href="/analyse"
              className={cn(
                "flex flex-col items-center gap-1 px-4 py-1.5 rounded-xl transition-all duration-200",
                active ? "text-brand-400" : "text-slate-500 hover:text-slate-300"
              )}
            >
              <BarChart2 className="w-5 h-5" />
              <span className="text-[10px] font-medium">{t("analyse")}</span>
              {active && <motion.div layoutId="mob-active" className="w-1 h-1 bg-brand-400 rounded-full" />}
            </Link>
          );
        })()}

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
