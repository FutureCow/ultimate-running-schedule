"use client";

import { useEffect, useState } from "react";
import { useRouter, Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { isLoggedIn } from "@/lib/auth";
import {
  Brain,
  Watch,
  Dumbbell,
  CalendarDays,
  Gauge,
  Languages,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  Upload,
  Zap,
} from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] },
  }),
};

function MetriqLogo({ size = 48 }: { size?: number }) {
  return (
    <div
      className="rounded-2xl bg-brand-500 flex items-center justify-center shadow-lg shadow-brand-500/30 shrink-0"
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 18 18" fill="none" style={{ width: size * 0.57, height: size * 0.57 }}>
        <rect x="1"  y="10" width="3.5" height="7"  rx="1.5" fill="white"/>
        <rect x="7"  y="3"  width="3.5" height="14" rx="1.5" fill="white"/>
        <rect x="13" y="7"  width="3.5" height="10" rx="1.5" fill="white"/>
      </svg>
    </div>
  );
}

// ─── Demo schedule data ────────────────────────────────────────────────────────
type DemoWorkout = {
  day: string;
  type: string;
  label: string;
  detail: string;
  pace?: string;
  dist?: string;
  color: string;
  dot: string;
  onGarmin?: boolean;
};

const DEMO_WEEK_NL: DemoWorkout[] = [
  { day: "Ma", type: "rest",     label: "Rustdag",       detail: "Actief herstel of volledige rust",                  color: "bg-slate-700/50 text-slate-400 border-slate-600/30",   dot: "bg-slate-500" },
  { day: "Di", type: "easy_run", label: "Easy Run",       detail: "Rustige duurloop — aëroob fundament opbouwen",       pace: "6:00–6:30 /km", dist: "10 km",  color: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25", dot: "bg-emerald-400", onGarmin: true },
  { day: "Wo", type: "strength", label: "Kracht",         detail: "Core & stabiliteit — 45 min",                       color: "bg-violet-500/15 text-violet-300 border-violet-500/25", dot: "bg-violet-400", onGarmin: true },
  { day: "Do", type: "interval", label: "Intervallen",    detail: "6 × 1000 m @ 4:45 /km · 90 s rust",                pace: "4:45 /km",      dist: "12 km",  color: "bg-red-500/15 text-red-300 border-red-500/25",           dot: "bg-red-400" },
  { day: "Vr", type: "recovery", label: "Herstelloop",    detail: "Zeer rustig — benen losmaken voor zaterdag",        pace: "6:30–7:00 /km", dist: "6 km",   color: "bg-teal-500/15 text-teal-300 border-teal-500/25",         dot: "bg-teal-400" },
  { day: "Za", type: "tempo",    label: "Tempo",          detail: "3 km warming-up · 8 km drempelloop · 2 km cooling-down", pace: "5:05–5:15 /km", dist: "13 km", color: "bg-orange-500/15 text-orange-300 border-orange-500/25", dot: "bg-orange-400", onGarmin: true },
  { day: "Zo", type: "long_run", label: "Lange duurloop", detail: "Rustig en consistent — 70% van max HF",             pace: "6:10–6:40 /km", dist: "22 km",  color: "bg-blue-500/15 text-blue-300 border-blue-500/25",         dot: "bg-blue-400", onGarmin: true },
];

const DEMO_WEEK_EN: DemoWorkout[] = [
  { day: "Mo", type: "rest",     label: "Rest Day",       detail: "Active recovery or complete rest",                  color: "bg-slate-700/50 text-slate-400 border-slate-600/30",   dot: "bg-slate-500" },
  { day: "Tu", type: "easy_run", label: "Easy Run",       detail: "Comfortable aerobic run — build your base",         pace: "6:00–6:30 /km", dist: "10 km",  color: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25", dot: "bg-emerald-400", onGarmin: true },
  { day: "We", type: "strength", label: "Strength",       detail: "Core & stability — 45 min",                        color: "bg-violet-500/15 text-violet-300 border-violet-500/25", dot: "bg-violet-400", onGarmin: true },
  { day: "Th", type: "interval", label: "Intervals",      detail: "6 × 1000 m @ 4:45 /km · 90 s rest",               pace: "4:45 /km",      dist: "12 km",  color: "bg-red-500/15 text-red-300 border-red-500/25",           dot: "bg-red-400" },
  { day: "Fr", type: "recovery", label: "Recovery",       detail: "Very easy — shake out the legs for Saturday",      pace: "6:30–7:00 /km", dist: "6 km",   color: "bg-teal-500/15 text-teal-300 border-teal-500/25",         dot: "bg-teal-400" },
  { day: "Sa", type: "tempo",    label: "Tempo Run",      detail: "3 km warm-up · 8 km threshold · 2 km cool-down",  pace: "5:05–5:15 /km", dist: "13 km",  color: "bg-orange-500/15 text-orange-300 border-orange-500/25",   dot: "bg-orange-400", onGarmin: true },
  { day: "Su", type: "long_run", label: "Long Run",       detail: "Easy and consistent — 70% of max HR",              pace: "6:10–6:40 /km", dist: "22 km",  color: "bg-blue-500/15 text-blue-300 border-blue-500/25",         dot: "bg-blue-400", onGarmin: true },
];

const DEMO_ZONES_NL = [
  { name: "Easy",      pace: "6:00–6:40", color: "bg-emerald-500" },
  { name: "Marathon",  pace: "5:25–5:40", color: "bg-blue-500" },
  { name: "Drempel",   pace: "5:00–5:15", color: "bg-orange-500" },
  { name: "Interval",  pace: "4:40–4:55", color: "bg-red-500" },
  { name: "Repetitie", pace: "4:15–4:35", color: "bg-rose-600" },
];
const DEMO_ZONES_EN = [
  { name: "Easy",       pace: "6:00–6:40", color: "bg-emerald-500" },
  { name: "Marathon",   pace: "5:25–5:40", color: "bg-blue-500" },
  { name: "Threshold",  pace: "5:00–5:15", color: "bg-orange-500" },
  { name: "Interval",   pace: "4:40–4:55", color: "bg-red-500" },
  { name: "Repetition", pace: "4:15–4:35", color: "bg-rose-600" },
];

function DemoSchedule({ locale }: { locale: string }) {
  const week = locale === "nl" ? DEMO_WEEK_NL : DEMO_WEEK_EN;
  const zones = locale === "nl" ? DEMO_ZONES_NL : DEMO_ZONES_EN;
  const [activeDay, setActiveDay] = useState(6); // Sunday / Zondag
  const [pushing, setPushing] = useState<number | null>(null);
  const [pushed, setPushed] = useState<Set<number>>(new Set([1, 2, 5, 6]));
  const t = useTranslations("landing");

  const active = week[activeDay];

  function handlePush(i: number) {
    if (pushed.has(i)) return;
    setPushing(i);
    setTimeout(() => {
      setPushed((p) => new Set(Array.from(p).concat(i)));
      setPushing(null);
    }, 1100);
  }

  return (
    <div className="rounded-2xl border border-slate-700/60 bg-surface-card overflow-hidden shadow-2xl shadow-black/40">
      {/* Window chrome */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50 bg-slate-800/50">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500/70" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
          <div className="w-3 h-3 rounded-full bg-emerald-500/70" />
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <MetriqLogo size={18} />
          <span className="font-medium text-slate-400">
            {locale === "nl" ? "Sub-45 10K Rotterdam 2026 · Week 7 / 14" : "Sub-45 10K Amsterdam 2026 · Week 7 / 14"}
          </span>
        </div>
        <div className="flex items-center gap-1 text-xs text-slate-600">
          <span>VDOT 48</span>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row">
        {/* Week strip */}
        <div className="flex lg:flex-col gap-1 p-3 lg:w-[110px] border-b lg:border-b-0 lg:border-r border-slate-700/40 overflow-x-auto lg:overflow-x-visible">
          {week.map((w, i) => (
            <button
              key={i}
              onClick={() => setActiveDay(i)}
              className={`flex lg:flex-row items-center gap-2 px-2 py-2 rounded-xl transition-all shrink-0 ${
                activeDay === i
                  ? "bg-slate-700/70 border border-slate-600/50"
                  : "hover:bg-slate-800/50"
              }`}
            >
              <div className={`w-2 h-2 rounded-full shrink-0 ${w.dot}`} />
              <span className={`text-xs font-semibold ${activeDay === i ? "text-white" : "text-slate-500"}`}>
                {w.day}
              </span>
              {pushed.has(i) && w.type !== "rest" && (
                <Watch className="w-3 h-3 text-brand-400 ml-auto hidden lg:block" />
              )}
            </button>
          ))}
        </div>

        {/* Detail panel */}
        <div className="flex-1 p-5 space-y-4">
          <div className={`rounded-xl border px-4 py-3 ${active.color}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-bold text-sm">{active.label}</p>
                <p className="text-xs opacity-75 mt-0.5 leading-relaxed">{active.detail}</p>
              </div>
              {active.type !== "rest" && (
                <button
                  onClick={() => handlePush(activeDay)}
                  disabled={pushed.has(activeDay) || pushing === activeDay}
                  className={`shrink-0 flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg transition-all ${
                    pushed.has(activeDay)
                      ? "bg-brand-500/20 text-brand-300 border border-brand-500/30 cursor-default"
                      : "bg-slate-700/60 text-slate-300 border border-slate-600/50 hover:bg-slate-600/60"
                  }`}
                >
                  {pushing === activeDay ? (
                    <span className="w-3 h-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
                  ) : pushed.has(activeDay) ? (
                    <Watch className="w-3 h-3" />
                  ) : (
                    <Upload className="w-3 h-3" />
                  )}
                  {pushed.has(activeDay)
                    ? (locale === "nl" ? "Op Garmin" : "On Garmin")
                    : (locale === "nl" ? "Push naar Garmin" : "Push to Garmin")}
                </button>
              )}
            </div>

            {(active.pace || active.dist) && (
              <div className="flex gap-3 mt-3">
                {active.dist && (
                  <div className="bg-black/20 rounded-lg px-2.5 py-1.5">
                    <p className="text-[10px] opacity-60 uppercase tracking-wider">{locale === "nl" ? "Afstand" : "Distance"}</p>
                    <p className="text-sm font-bold">{active.dist}</p>
                  </div>
                )}
                {active.pace && (
                  <div className="bg-black/20 rounded-lg px-2.5 py-1.5">
                    <p className="text-[10px] opacity-60 uppercase tracking-wider">Pace</p>
                    <p className="text-sm font-bold">{active.pace}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Pace zones */}
          <div className="rounded-xl border border-slate-700/40 bg-slate-800/30 px-4 py-3">
            <p className="text-xs font-semibold text-slate-400 mb-2.5">
              {locale === "nl" ? "Tempo Zones · VDOT 48" : "Pace Zones · VDOT 48"}
            </p>
            <div className="space-y-1.5">
              {zones.map((z) => (
                <div key={z.name} className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${z.color}`} />
                  <span className="text-xs text-slate-400 w-20">{z.name}</span>
                  <div className="flex-1 h-1 rounded-full bg-slate-700 overflow-hidden">
                    <div className={`h-full rounded-full ${z.color} opacity-60`}
                      style={{ width: `${100 - zones.indexOf(z) * 15}%` }} />
                  </div>
                  <span className="text-xs font-mono text-slate-300 tabular-nums">{z.pace}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Page data ─────────────────────────────────────────────────────────────────

const FEATURES = [
  { icon: Brain,       color: "text-brand-400",  bg: "bg-brand-500/10 border-brand-500/20",   titleKey: "features.ai.title",        descKey: "features.ai.desc" },
  { icon: Watch,       color: "text-sky-400",    bg: "bg-sky-500/10 border-sky-500/20",       titleKey: "features.garmin.title",    descKey: "features.garmin.desc" },
  { icon: Dumbbell,    color: "text-violet-400", bg: "bg-violet-500/10 border-violet-500/20", titleKey: "features.strength.title",  descKey: "features.strength.desc" },
  { icon: CalendarDays,color: "text-amber-400",  bg: "bg-amber-500/10 border-amber-500/20",   titleKey: "features.calendar.title",  descKey: "features.calendar.desc" },
  { icon: Gauge,       color: "text-rose-400",   bg: "bg-rose-500/10 border-rose-500/20",     titleKey: "features.paceZones.title", descKey: "features.paceZones.desc" },
  { icon: Languages,   color: "text-teal-400",   bg: "bg-teal-500/10 border-teal-500/20",     titleKey: "features.bilingual.title", descKey: "features.bilingual.desc" },
];

const HOW_IT_WORKS = [
  { step: "1", titleKey: "how.step1.title", descKey: "how.step1.desc" },
  { step: "2", titleKey: "how.step2.title", descKey: "how.step2.desc" },
  { step: "3", titleKey: "how.step3.title", descKey: "how.step3.desc" },
  { step: "4", titleKey: "how.step4.title", descKey: "how.step4.desc" },
];

export default function LocaleRootPage() {
  const router = useRouter();
  const t = useTranslations("landing");
  const [checked, setChecked] = useState(false);
  const [locale, setLocale] = useState("nl");

  useEffect(() => {
    if (isLoggedIn()) {
      router.replace("/dashboard");
    } else {
      // Detect locale from URL path
      const path = window.location.pathname;
      setLocale(path.startsWith("/en") ? "en" : "nl");
      setChecked(true);
    }
  }, [router]);

  if (!checked) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface text-white overflow-x-hidden">
      {/* Ambient background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[500px] bg-brand-500/8 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-violet-500/5 rounded-full blur-3xl" />
      </div>

      {/* Navbar */}
      <header className="relative z-10 flex items-center justify-between px-6 py-5 max-w-6xl mx-auto">
        <div className="flex items-center gap-3">
          <MetriqLogo size={40} />
          <div>
            <span className="text-lg font-bold text-white leading-tight block">Metriq</span>
            <span className="text-[10px] text-brand-400/80 font-medium leading-tight block hidden sm:block">
              {t("tagline")}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm font-medium text-slate-400 hover:text-white transition-colors px-4 py-2 rounded-xl hover:bg-surface-elevated"
          >
            {t("nav.login")}
          </Link>
          <Link href="/register" className="btn-primary text-sm">
            {t("nav.register")}
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative z-10 pt-16 pb-24 px-6 text-center max-w-4xl mx-auto">
        <motion.div
          custom={0} initial="hidden" animate="visible" variants={fadeUp}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-medium mb-8"
        >
          <Brain className="w-3.5 h-3.5" />
          {t("hero.badge")}
        </motion.div>

        <motion.h1
          custom={1} initial="hidden" animate="visible" variants={fadeUp}
          className="text-5xl sm:text-6xl font-bold tracking-tight mb-6 leading-tight"
        >
          {t("hero.title1")}{" "}
          <span className="text-brand-400">{t("hero.title2")}</span>
          <br />
          {t("hero.title3")}
        </motion.h1>

        <motion.p
          custom={2} initial="hidden" animate="visible" variants={fadeUp}
          className="text-lg text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed"
        >
          {t("hero.subtitle")}
        </motion.p>

        <motion.div
          custom={3} initial="hidden" animate="visible" variants={fadeUp}
          className="flex items-center justify-center gap-4 flex-wrap"
        >
          <Link href="/register" className="btn-primary text-base px-8 py-3 flex items-center gap-2">
            {t("hero.cta")}
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/login"
            className="text-sm font-medium text-slate-400 hover:text-white transition-colors flex items-center gap-1.5"
          >
            {t("hero.login")}
            <ChevronRight className="w-4 h-4" />
          </Link>
        </motion.div>

        <motion.div
          custom={4} initial="hidden" animate="visible" variants={fadeUp}
          className="flex items-center justify-center gap-6 mt-12 flex-wrap"
        >
          {[t("hero.trust.0"), t("hero.trust.1"), t("hero.trust.2")].map((item, i) => (
            <div key={i} className="flex items-center gap-1.5 text-sm text-slate-500">
              <CheckCircle2 className="w-4 h-4 text-brand-500" />
              {item}
            </div>
          ))}
        </motion.div>
      </section>

      {/* ── Live demo section ── */}
      <section className="relative z-10 px-6 pb-24 max-w-5xl mx-auto">
        <motion.div
          initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} variants={fadeUp} custom={0}
          className="text-center mb-10"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-medium mb-4">
            <Zap className="w-3.5 h-3.5" />
            {t("demo.badge")}
          </div>
          <h2 className="text-3xl font-bold mb-3">{t("demo.title")}</h2>
          <p className="text-slate-400 max-w-xl mx-auto">{t("demo.subtitle")}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          <DemoSchedule locale={locale} />
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
          className="text-center text-xs text-slate-600 mt-4"
        >
          {t("demo.note")}
        </motion.p>
      </section>

      {/* Features grid */}
      <section className="relative z-10 px-6 pb-24 max-w-6xl mx-auto">
        <motion.div
          custom={0} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} variants={fadeUp}
          className="text-center mb-14"
        >
          <h2 className="text-3xl font-bold mb-3">{t("features.title")}</h2>
          <p className="text-slate-400 max-w-xl mx-auto">{t("features.subtitle")}</p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.titleKey} custom={i} initial="hidden" whileInView="visible"
              viewport={{ once: true, margin: "-60px" }} variants={fadeUp}
              className={`card border ${f.bg} flex flex-col gap-4`}
            >
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${f.bg} border`}>
                <f.icon className={`w-5 h-5 ${f.color}`} />
              </div>
              <div>
                <h3 className="font-semibold text-white mb-1.5">{t(f.titleKey)}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{t(f.descKey)}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="relative z-10 px-6 pb-24 max-w-4xl mx-auto">
        <motion.div
          custom={0} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} variants={fadeUp}
          className="text-center mb-14"
        >
          <h2 className="text-3xl font-bold mb-3">{t("how.title")}</h2>
          <p className="text-slate-400 max-w-xl mx-auto">{t("how.subtitle")}</p>
        </motion.div>

        <div className="space-y-4">
          {HOW_IT_WORKS.map((item, i) => (
            <motion.div
              key={item.step} custom={i} initial="hidden" whileInView="visible"
              viewport={{ once: true, margin: "-40px" }} variants={fadeUp}
              className="flex items-start gap-5 card"
            >
              <div className="w-9 h-9 rounded-xl bg-brand-500/15 border border-brand-500/25 flex items-center justify-center text-brand-400 font-bold text-sm shrink-0">
                {item.step}
              </div>
              <div>
                <h3 className="font-semibold text-white mb-1">{t(item.titleKey)}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{t(item.descKey)}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA banner */}
      <section className="relative z-10 px-6 pb-24 max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 32 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }} transition={{ duration: 0.6 }}
          className="rounded-2xl bg-gradient-to-br from-brand-500/20 to-brand-600/10 border border-brand-500/25 p-10 text-center"
        >
          <MetriqLogo size={56} />
          <h2 className="text-3xl font-bold mt-6 mb-3">{t("cta.title")}</h2>
          <p className="text-slate-400 mb-8 max-w-lg mx-auto">{t("cta.subtitle")}</p>
          <Link href="/register" className="btn-primary text-base px-10 py-3 inline-flex items-center gap-2">
            {t("cta.button")}
            <ArrowRight className="w-4 h-4" />
          </Link>
          <p className="text-xs text-slate-600 mt-4">{t("cta.note")}</p>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-800 py-8 px-6 text-center text-xs text-slate-600">
        <p>© 2026 Metriq · {t("footer.tagline")}</p>
      </footer>
    </div>
  );
}
