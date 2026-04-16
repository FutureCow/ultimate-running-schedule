"use client";

import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { useTranslations, useLocale } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Plus, TrendingUp, Calendar, Target, Zap, ChevronRight } from "lucide-react";
import { plansApi } from "@/lib/api";
import { Plan } from "@/types";
import { format, parseISO } from "date-fns";
import { nl, enUS } from "date-fns/locale";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tGoals = useTranslations("goals");
  const locale = useLocale();
  const dateFnsLocale = locale === "nl" ? nl : enUS;

  const { data: plans = [], isLoading } = useQuery<Plan[]>({
    queryKey: ["plans"],
    queryFn: () => plansApi.list().then((r) => r.data),
  });

  const activePlan = plans[0];
  const overview = activePlan?.plan_json?.plan_overview;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{t("title")}</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {format(new Date(), "EEEE d MMMM yyyy", { locale: dateFnsLocale })}
          </p>
        </div>
        <Link href="/plans/new" className="btn-primary">
          <Plus className="w-4 h-4" />
          {t("newPlan")}
        </Link>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <span className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
        </div>
      ) : plans.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-6">
          {activePlan && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="card bg-gradient-to-br from-brand-900/40 to-surface-card border-brand-700/30"
            >
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-brand-400 uppercase tracking-wider">{t("activePlan")}</span>
                  </div>
                  <h2 className="text-xl font-bold text-white">{activePlan.name}</h2>
                  <p className="text-sm text-slate-400 mt-0.5">
                    {tGoals(activePlan.goal as any)} · {activePlan.duration_weeks} {t("stats.weeks").toLowerCase()}
                    {activePlan.start_date && ` · Start ${format(parseISO(activePlan.start_date), "d MMM", { locale: dateFnsLocale })}`}
                  </p>
                </div>
                <Link href={`/plans/${activePlan.id}`} className="btn-secondary text-sm">
                  {t("viewPlan")} <ChevronRight className="w-4 h-4" />
                </Link>
              </div>

              {overview && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                  <StatCard icon={<Target className="w-4 h-4 text-brand-400" />} label={t("stats.targetTime")} value={overview.target_time} />
                  <StatCard icon={<Zap className="w-4 h-4 text-orange-400" />} label={t("stats.targetPace")} value={`${overview.target_pace_per_km}/km`} />
                  <StatCard icon={<TrendingUp className="w-4 h-4 text-blue-400" />} label={t("stats.vdot")} value={String(overview.estimated_vdot)} />
                  <StatCard icon={<Calendar className="w-4 h-4 text-purple-400" />} label={t("stats.weeks")} value={`${activePlan.duration_weeks}`} />
                </div>
              )}

              {overview?.pace_zones && (
                <div className="mt-4 pt-4 border-t border-slate-700/50">
                  <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">{t("paceZones")}</p>
                  <div className="flex flex-wrap gap-2">
                    {(["easy", "marathon", "threshold", "interval"] as const).map((zone) => (
                      <div key={zone} className="bg-surface-elevated rounded-lg px-2.5 py-1 text-xs">
                        <span className="text-slate-500 capitalize">{zone}</span>
                        <span className="font-mono font-semibold text-white ml-2">
                          {overview.pace_zones[zone]}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {plans.length > 1 && (
            <div>
              <h2 className="section-title mb-3">{t("allPlans")}</h2>
              <div className="space-y-2">
                {plans.slice(1).map((plan, i) => (
                  <motion.div
                    key={plan.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <Link
                      href={`/plans/${plan.id}`}
                      className="flex items-center justify-between card hover:border-slate-600 transition-colors"
                    >
                      <div>
                        <p className="font-semibold text-white text-sm">{plan.name}</p>
                        <p className="text-xs text-slate-500">
                          {tGoals(plan.goal as any)} · {plan.duration_weeks} {t("stats.weeks").toLowerCase()} ·{" "}
                          {format(parseISO(plan.created_at), "d MMM yyyy", { locale: dateFnsLocale })}
                        </p>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-600" />
                    </Link>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-surface-elevated rounded-xl p-3">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-[11px] text-slate-500 font-medium">{label}</span>
      </div>
      <p className="text-base font-bold text-white font-mono">{value}</p>
    </div>
  );
}

function EmptyState() {
  const t = useTranslations("dashboard.empty");
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center py-20 text-center"
    >
      <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-4">
        <Zap className="w-8 h-8 text-brand-400" />
      </div>
      <h2 className="text-xl font-bold text-white mb-2">{t("title")}</h2>
      <p className="text-sm text-slate-400 mb-6 max-w-xs">{t("subtitle")}</p>
      <Link href="/plans/new" className="btn-primary">
        <Plus className="w-4 h-4" /> {t("cta")}
      </Link>
    </motion.div>
  );
}
