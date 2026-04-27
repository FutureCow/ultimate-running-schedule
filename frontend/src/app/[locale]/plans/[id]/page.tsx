"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Trash2, Info, Pencil, Dumbbell, X, Loader2, RefreshCw } from "lucide-react";
import { useTranslations, useLocale } from "next-intl";
import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { Link } from "@/i18n/navigation";
import { plansApi, garminApi } from "@/lib/api";
import { Plan } from "@/types";
import { WeekCalendar } from "@/components/Calendar/WeekCalendar";
import { PaceZonesCard } from "@/components/Calendar/PaceZonesCard";
import { Navbar } from "@/components/ui/Navbar";
import { StepStrength } from "@/components/PlanCreatorForm/steps/StepStrength";
import { FormSchema } from "@/components/PlanCreatorForm/PlanCreatorForm";

export default function PlanDetailPage() {
  const { id, locale } = useParams<{ id: string; locale: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const t = useTranslations("plans");
  const tGoals = useTranslations("goals");
  const tForm = useTranslations("form");
  const [strengthModal, setStrengthModal] = useState(false);
  const [strengthError, setStrengthError] = useState("");

  const { data: plan, isLoading } = useQuery<Plan>({
    queryKey: ["plan", id],
    queryFn: () => plansApi.get(id).then((r) => r.data),
  });

  useEffect(() => {
    garminApi.autoSync()
      .then((r) => { if (r.data?.synced) queryClient.invalidateQueries({ queryKey: ["plan", id] }); })
      .catch(() => {});
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const deleteMutation = useMutation({
    mutationFn: () => plansApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      router.push(`/${locale}/dashboard`);
    },
  });

  const { watch, setValue, handleSubmit } = useForm<FormSchema>({
    defaultValues: {
      strength: plan?.strength_enabled ? {
        enabled: true,
        location: (plan.strength_location as any) ?? "bodyweight",
        type: (plan.strength_type as any) ?? "full_body",
        days: plan.strength_days ?? [],
        equipment: (plan as any).strength_equipment ?? [],
      } : { enabled: false },
    },
  });

  const addStrengthMutation = useMutation({
    mutationFn: (data: FormSchema) => {
      const s = data.strength;
      if (!s?.enabled) throw new Error("Strength not enabled");
      return plansApi.addStrength(id, {
        enabled: true,
        location: s.location ?? null,
        type: s.type ?? null,
        days: s.days ?? null,
        equipment: s.equipment ?? null,
        notes: s.notes ?? null,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plan", id] });
      setStrengthModal(false);
      setStrengthError("");
    },
    onError: (e: any) => setStrengthError(e?.response?.data?.detail || "Mislukt"),
  });

  const regenerateMutation = useMutation({
    mutationFn: () => plansApi.regenerate(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["plan", id] }),
  });

  return (
    <>
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-6xl mx-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <span className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
          </div>
        ) : !plan ? (
          <div className="text-center py-20 text-slate-400">{t("notFound")}</div>
        ) : (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <Link href="/dashboard" className="btn-ghost px-2 py-2">
                  <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                  <h1 className="text-xl font-bold text-white">{plan.name}</h1>
                  <p className="text-xs text-slate-400">
                    {tGoals(plan.goal as any)} · {plan.duration_weeks} weken
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { if (confirm(t("regenerateConfirm"))) regenerateMutation.mutate(); }}
                  disabled={regenerateMutation.isPending}
                  className="btn-secondary text-sm px-3"
                  title={t("regenerate")}
                >
                  {regenerateMutation.isPending
                    ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <RefreshCw className="w-4 h-4" />}
                  <span className="hidden sm:inline">{t("regenerate")}</span>
                </button>
                <button
                  onClick={() => setStrengthModal(true)}
                  className="btn-secondary text-sm px-3"
                  title={t("addStrength")}
                >
                  <Dumbbell className="w-4 h-4 text-violet-400" />
                  <span className="hidden sm:inline">{t("addStrength")}</span>
                </button>
                <Link href={`/plans/${id}/edit`} className="btn-ghost px-3">
                  <Pencil className="w-4 h-4" />
                </Link>
                <button
                  onClick={() => { if (confirm(t("deleteConfirm"))) deleteMutation.mutate(); }}
                  className="btn-ghost text-red-400 hover:text-red-300 px-3"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {plan.plan_json?.plan_overview?.coaching_notes && (
              <div className="flex gap-3 card bg-blue-950/30 border-blue-700/30">
                <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <p className="text-sm text-slate-300 leading-relaxed">
                  {plan.plan_json.plan_overview.coaching_notes}
                </p>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
              <div>
                {plan.plan_json ? (
                  <WeekCalendar plan={plan} />
                ) : (
                  <p className="text-slate-400 text-sm">Plan wordt gegenereerd…</p>
                )}
              </div>

              <div className="space-y-4">
                {plan.plan_json?.plan_overview?.pace_zones && (
                  <PaceZonesCard
                    zones={plan.plan_json.plan_overview.pace_zones}
                    vdot={plan.plan_json.plan_overview.estimated_vdot}
                  />
                )}

                {plan.plan_json?.plan_overview?.weekly_structure && (
                  <div className="card">
                    <h3 className="text-sm font-bold text-white mb-2">{t("weeklyStructure")}</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      {plan.plan_json.plan_overview.weekly_structure}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </main>
    </div>

    {/* Strength modal */}
    <AnimatePresence>
      {strengthModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm px-4 pb-4 sm:pb-0"
          onClick={(e) => { if (e.target === e.currentTarget) setStrengthModal(false); }}
        >
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 40 }}
            className="card w-full max-w-lg max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-white">{t("addStrength")}</h2>
              <button onClick={() => setStrengthModal(false)} className="btn-ghost p-2">
                <X className="w-4 h-4" />
              </button>
            </div>

            <StepStrength watch={watch} setValue={setValue} />

            {strengthError && (
              <p className="mt-3 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {strengthError}
              </p>
            )}

            <div className="flex gap-3 mt-6 pt-4 border-t border-slate-700/50">
              <button onClick={() => setStrengthModal(false)} className="btn-secondary flex-1">
                {tForm("prev")}
              </button>
              <button
                onClick={handleSubmit((data) => addStrengthMutation.mutate(data))}
                disabled={addStrengthMutation.isPending || !watch("strength.enabled")}
                className="btn-primary flex-1"
              >
                {addStrengthMutation.isPending ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> {tForm("generating")}</>
                ) : (
                  <><Dumbbell className="w-4 h-4" /> {t("addStrength")}</>
                )}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
    </>
  );
}
