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
} from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] },
  }),
};

function CadenceLogo({ size = 48 }: { size?: number }) {
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

const FEATURES = [
  {
    icon: Brain,
    color: "text-brand-400",
    bg: "bg-brand-500/10 border-brand-500/20",
    titleKey: "features.ai.title",
    descKey: "features.ai.desc",
  },
  {
    icon: Watch,
    color: "text-sky-400",
    bg: "bg-sky-500/10 border-sky-500/20",
    titleKey: "features.garmin.title",
    descKey: "features.garmin.desc",
  },
  {
    icon: Dumbbell,
    color: "text-violet-400",
    bg: "bg-violet-500/10 border-violet-500/20",
    titleKey: "features.strength.title",
    descKey: "features.strength.desc",
  },
  {
    icon: CalendarDays,
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
    titleKey: "features.calendar.title",
    descKey: "features.calendar.desc",
  },
  {
    icon: Gauge,
    color: "text-rose-400",
    bg: "bg-rose-500/10 border-rose-500/20",
    titleKey: "features.paceZones.title",
    descKey: "features.paceZones.desc",
  },
  {
    icon: Languages,
    color: "text-teal-400",
    bg: "bg-teal-500/10 border-teal-500/20",
    titleKey: "features.bilingual.title",
    descKey: "features.bilingual.desc",
  },
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

  useEffect(() => {
    if (isLoggedIn()) {
      router.replace("/dashboard");
    } else {
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
          <CadenceLogo size={40} />
          <div>
            <span className="text-lg font-bold text-white leading-tight block">Cadence</span>
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
          <Link
            href="/register"
            className="btn-primary text-sm"
          >
            {t("nav.register")}
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative z-10 pt-16 pb-24 px-6 text-center max-w-4xl mx-auto">
        <motion.div
          custom={0}
          initial="hidden"
          animate="visible"
          variants={fadeUp}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-medium mb-8"
        >
          <Brain className="w-3.5 h-3.5" />
          {t("hero.badge")}
        </motion.div>

        <motion.h1
          custom={1}
          initial="hidden"
          animate="visible"
          variants={fadeUp}
          className="text-5xl sm:text-6xl font-bold tracking-tight mb-6 leading-tight"
        >
          {t("hero.title1")}{" "}
          <span className="text-brand-400">{t("hero.title2")}</span>
          <br />
          {t("hero.title3")}
        </motion.h1>

        <motion.p
          custom={2}
          initial="hidden"
          animate="visible"
          variants={fadeUp}
          className="text-lg text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed"
        >
          {t("hero.subtitle")}
        </motion.p>

        <motion.div
          custom={3}
          initial="hidden"
          animate="visible"
          variants={fadeUp}
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

        {/* Trust badges */}
        <motion.div
          custom={4}
          initial="hidden"
          animate="visible"
          variants={fadeUp}
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

      {/* Features grid */}
      <section className="relative z-10 px-6 pb-24 max-w-6xl mx-auto">
        <motion.div
          custom={0}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeUp}
          className="text-center mb-14"
        >
          <h2 className="text-3xl font-bold mb-3">{t("features.title")}</h2>
          <p className="text-slate-400 max-w-xl mx-auto">{t("features.subtitle")}</p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.titleKey}
              custom={i}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-60px" }}
              variants={fadeUp}
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
          custom={0}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeUp}
          className="text-center mb-14"
        >
          <h2 className="text-3xl font-bold mb-3">{t("how.title")}</h2>
          <p className="text-slate-400 max-w-xl mx-auto">{t("how.subtitle")}</p>
        </motion.div>

        <div className="space-y-4">
          {HOW_IT_WORKS.map((item, i) => (
            <motion.div
              key={item.step}
              custom={i}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-40px" }}
              variants={fadeUp}
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
          initial={{ opacity: 0, y: 32 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="rounded-2xl bg-gradient-to-br from-brand-500/20 to-brand-600/10 border border-brand-500/25 p-10 text-center"
        >
          <CadenceLogo size={56} />
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
        <p>© 2026 Cadence · {t("footer.tagline")}</p>
      </footer>
    </div>
  );
}
