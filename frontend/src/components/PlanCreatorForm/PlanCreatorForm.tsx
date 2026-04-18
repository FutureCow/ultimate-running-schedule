"use client";

import { useState, useEffect } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, ArrowRight, Zap, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { plansApi, profileApi } from "@/lib/api";
import { Plan, PlanFormData, UserProfile } from "@/types";
import { StepGoal } from "./steps/StepGoal";
import { StepAthleteProfile } from "./steps/StepAthleteProfile";
import { StepTrainingPrefs } from "./steps/StepTrainingPrefs";
import { StepStrength } from "./steps/StepStrength";
import { StepReview } from "./steps/StepReview";

const schema = z.object({
  name: z.string().min(1, "Verplicht"),
  goal: z.enum(["5k", "10k", "half_marathon", "marathon"]),
  plan_language: z.enum(["nl", "en"]),
  target_time_seconds: z.number().optional(),
  target_pace_per_km: z.string().optional(),
  age: z.number().min(10).max(90).optional(),
  height_cm: z.number().min(100).max(250).optional(),
  weight_kg: z.number().min(30).max(200).optional(),
  weekly_km: z.number().min(0).max(500).optional(),
  weekly_runs: z.number().min(1).max(14).optional(),
  injuries: z.string().optional(),
  extra_notes: z.string().optional(),
  training_days: z.array(z.string()).min(2, "Kies minstens 2 dagen"),
  long_run_day: z.string().min(1, "Verplicht"),
  duration_weeks: z.number().min(4).max(52),
  surface: z.string().min(1, "Verplicht"),
  start_date: z.string().optional(),
  race_date: z.string().optional(),
  strength: z.object({
    enabled: z.boolean(),
    location: z.enum(["bodyweight", "home_equipment", "gym"]).optional(),
    type: z.enum(["core_stability", "max_strength", "plyometrics", "injury_prevention", "full_body"]).optional(),
    days: z.array(z.number()).optional(),
  }).optional(),
});

export type FormSchema = z.infer<typeof schema>;

function secondsToDisplay(seconds?: number | null): string | undefined {
  if (!seconds) return undefined;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

interface Props {
  editPlan?: Plan;
}

const TOTAL_STEPS = 5;

export function PlanCreatorForm({ editPlan }: Props) {
  const t = useTranslations("form");
  const router = useRouter();
  const locale = useLocale();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const isEditMode = !!editPlan;

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    getValues,
    reset,
    formState: { errors },
    trigger,
  } = useForm<FormSchema>({
    resolver: zodResolver(schema),
    defaultValues: editPlan ? {
      name: editPlan.name,
      goal: editPlan.goal as FormSchema["goal"],
      plan_language: (locale === "en" ? "en" : "nl") as "nl" | "en",
      target_time_seconds: editPlan.target_time_seconds ?? undefined,
      target_pace_per_km: editPlan.target_pace_per_km ?? undefined,
      age: editPlan.age ?? undefined,
      height_cm: editPlan.height_cm ?? undefined,
      weight_kg: editPlan.weight_kg ?? undefined,
      weekly_km: editPlan.weekly_km ?? undefined,
      weekly_runs: editPlan.weekly_runs ?? undefined,
      injuries: editPlan.injuries ?? undefined,
      extra_notes: editPlan.extra_notes ?? undefined,
      training_days: editPlan.training_days ?? ["tuesday", "thursday", "saturday", "sunday"],
      long_run_day: editPlan.long_run_day ?? "sunday",
      duration_weeks: editPlan.duration_weeks,
      surface: editPlan.surface ?? "road",
      start_date: editPlan.start_date ?? undefined,
      race_date: editPlan.race_date ?? undefined,
      strength: editPlan.strength_enabled ? {
        enabled: true,
        location: (editPlan.strength_location as any) ?? "bodyweight",
        type: (editPlan.strength_type as any) ?? "full_body",
        days: editPlan.strength_days ?? [],
      } : { enabled: false },
    } : {
      goal: "10k",
      plan_language: (locale === "en" ? "en" : "nl") as "nl" | "en",
      duration_weeks: 12,
      surface: "road",
      training_days: ["tuesday", "thursday", "saturday", "sunday"],
      long_run_day: "sunday",
      start_date: new Date().toISOString().split("T")[0],
      strength: { enabled: false },
    },
  });

  // In create mode: pre-fill step-2 fields from the saved user profile
  useEffect(() => {
    if (isEditMode) return;
    profileApi.get().then(({ data }: { data: UserProfile }) => {
      if (data.age) setValue("age", data.age);
      if (data.height_cm) setValue("height_cm", data.height_cm);
      if (data.weight_kg) setValue("weight_kg", data.weight_kg);
      if (data.weekly_km) setValue("weekly_km", data.weekly_km);
      if (data.weekly_runs) setValue("weekly_runs", data.weekly_runs);
      if (data.injuries) setValue("injuries", data.injuries);
    }).catch(() => {/* no profile yet, leave fields empty */});
  }, [isEditMode]); // eslint-disable-line react-hooks/exhaustive-deps

  const values = watch();

  async function nextStep() {
    const fields: (keyof FormSchema)[][] = [
      ["name", "goal", "duration_weeks"],
      ["age", "height_cm", "weight_kg", "weekly_km", "weekly_runs"],
      ["training_days", "long_run_day", "surface"],
      [], // strength step has no required fields
    ];
    const valid = await trigger(fields[step - 1] as any);
    if (valid) setStep((s) => Math.min(TOTAL_STEPS, s + 1));
  }

  async function onSubmit(data: FormSchema) {
    setLoading(true);
    setError("");
    try {
      const payload: PlanFormData & { language: string } = {
        ...data,
        training_days: data.training_days,
        language: data.plan_language,
        strength: data.strength?.enabled ? {
          enabled: true,
          location: data.strength.location ?? null,
          type: data.strength.type ?? null,
          days: data.strength.days ?? null,
        } : undefined,
      };
      if (isEditMode) {
        await plansApi.update(editPlan!.id, payload);
      } else {
        const { data: plan } = await plansApi.create(payload);
        // Auto-save athlete profile so next plan is pre-filled
        profileApi.update({
          age: data.age,
          height_cm: data.height_cm,
          weight_kg: data.weight_kg,
          weekly_km: data.weekly_km,
          weekly_runs: data.weekly_runs,
          injuries: data.injuries,
        }).catch(() => {/* non-critical, ignore errors */});
        router.push(`/plans/${plan.id}`);
        return;
      }
      router.push(`/plans/${editPlan!.id}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || t("errors.failed"));
      setLoading(false);
    }
  }

  const targetTimeDisplay = secondsToDisplay(editPlan?.target_time_seconds);
  const stepProps = { register, watch, setValue, getValues, errors };

  const STEPS = Array.from({ length: TOTAL_STEPS }, (_, i) => i + 1);

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress steps */}
      <div className="flex items-center justify-between mb-8 relative">
        <div className="absolute top-4 left-0 right-0 h-0.5 bg-slate-700 -z-10" />
        {STEPS.map((id) => (
          <div key={id} className="flex flex-col items-center gap-2">
            <motion.div
              animate={{
                backgroundColor: step >= id ? "#22c55e" : "#1e293b",
                borderColor: step >= id ? "#22c55e" : "#475569",
              }}
              className="w-8 h-8 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-colors"
            >
              {step > id
                ? <CheckCircle2 className="w-4 h-4 text-white" />
                : <span className={step === id ? "text-white" : "text-slate-500"}>{id}</span>
              }
            </motion.div>
            <span className={`text-[10px] font-medium hidden sm:block ${step >= id ? "text-brand-400" : "text-slate-600"}`}>
              {t(`steps.${id}.title`)}
            </span>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="mb-6">
          <h2 className="text-lg font-bold text-white">
            {isEditMode ? `${t("editPrefix")} ${t(`steps.${step}.title`)}` : t(`steps.${step}.title`)}
          </h2>
          <p className="text-sm text-slate-400">{t(`steps.${step}.subtitle`)}</p>
        </div>

        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-start gap-2 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2.5 text-sm text-red-400 mb-4"
          >
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
          >
            {step === 1 && <StepGoal {...stepProps} targetTimeDisplay={targetTimeDisplay} />}
            {step === 2 && <StepAthleteProfile {...stepProps} />}
            {step === 3 && <StepTrainingPrefs {...stepProps} />}
            {step === 4 && <StepStrength watch={watch} setValue={setValue} />}
            {step === 5 && <StepReview values={values} />}
          </motion.div>
        </AnimatePresence>

        <div className="flex items-center justify-between mt-8 pt-4 border-t border-slate-700/50">
          <button
            type="button"
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1}
            className="btn-ghost disabled:opacity-0"
          >
            <ArrowLeft className="w-4 h-4" /> {t("prev")}
          </button>

          {step < TOTAL_STEPS ? (
            <button type="button" onClick={nextStep} className="btn-primary">
              {t("next")} <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit(onSubmit)}
              disabled={loading}
              className="btn-primary gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  {t("generating")}
                </>
              ) : isEditMode ? (
                <>
                  <RefreshCw className="w-4 h-4" />
                  {t("regenerate")}
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  {t("generate")}
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
