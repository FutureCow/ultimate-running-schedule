"use client";

import { useState, useEffect } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, ArrowRight, Zap, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { plansApi, profileApi } from "@/lib/api";
import { FollowUpSummary, GoalSuggestion, Plan, PlanFormData, UserProfile } from "@/types";
import { clockToSeconds, goalLabel } from "@/lib/goal";
import { StepGoal } from "./steps/StepGoal";
import { StepAthleteProfile } from "./steps/StepAthleteProfile";
import { StepTrainingPrefs } from "./steps/StepTrainingPrefs";
import { StepStrength } from "./steps/StepStrength";
import { StepReview } from "./steps/StepReview";

const schema = z.object({
  name: z.string().min(1, "Verplicht"),
  goal: z.enum(["5k", "10k", "half_marathon", "marathon", "custom"]),
  custom_distance_km: z.number().min(1).max(100).optional(),
  goal_kind: z.enum(["race", "fitness"]),
  feedback_tone: z.enum(["scientific", "encouraging"]).optional(),
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
    equipment: z.array(z.string()).optional(),
    notes: z.string().optional(),
  }).optional(),
}).refine(
  (data) => data.goal !== "custom" || data.custom_distance_km != null,
  { path: ["custom_distance_km"], message: "Vul een afstand tussen 1 en 100 km in" },
);

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
  /** public_id of the plan a follow-up builds on */
  followUpFrom?: string;
}

const TOTAL_STEPS = 5;

export function PlanCreatorForm({ editPlan, followUpFrom: followUpProp }: Props) {
  // Read in the browser: the page is prerendered per locale, so a server-side
  // query would always be empty
  const searchParams = useSearchParams();
  const followUpFrom = followUpProp ?? searchParams.get("from") ?? undefined;
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
      custom_distance_km: editPlan.custom_distance_km ?? undefined,
      goal_kind: editPlan.goal_kind ?? "race",
      feedback_tone: editPlan.feedback_tone ?? undefined,
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
      goal_kind: "race",
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
      if (data.feedback_tone) setValue("feedback_tone", data.feedback_tone);
    }).catch(() => {/* no profile yet, leave fields empty */});
  }, [isEditMode]); // eslint-disable-line react-hooks/exhaustive-deps

  // Follow-up plan: carry the previous plan's setup over and show what it achieved
  const tFollow = useTranslations("form.followUp");
  const [followUp, setFollowUp] = useState<FollowUpSummary | null>(null);
  const [raceTimeText, setRaceTimeText] = useState("");
  const [raceDistanceText, setRaceDistanceText] = useState("");
  const [replacesPlan, setReplacesPlan] = useState(false);
  const [suggestions, setSuggestions] = useState<GoalSuggestion[]>([]);
  const [suggestedTime, setSuggestedTime] = useState<string | undefined>();
  const tGoalNames = useTranslations("goals");

  // Suggestions follow the race result the athlete says is right
  function refreshSuggestions() {
    if (!followUpFrom) return;
    plansApi.followUpSummary(
      followUpFrom,
      clockToSeconds(raceTimeText),
      Number(raceDistanceText.replace(",", ".")) || undefined,
    ).then(({ data }) => setSuggestions(data.suggestions ?? [])).catch(() => {});
  }

  function applySuggestion(s: GoalSuggestion) {
    setValue("goal", s.goal as FormSchema["goal"]);
    setValue("custom_distance_km", s.custom_distance_km ?? undefined);
    setValue("goal_kind", s.goal_kind);
    setValue("target_time_seconds", s.target_time_seconds ?? undefined);
    setSuggestedTime(secondsToDisplay(s.target_time_seconds) ?? "");
  }

  function suggestionLabel(s: GoalSuggestion) {
    const goal = goalLabel(tGoalNames, s.goal, s.custom_distance_km, locale);
    const time = secondsToDisplay(s.target_time_seconds);
    if (s.kind === "faster") return tFollow("suggest.faster", { goal, time: time ?? "" });
    if (s.kind === "repeat") return tFollow("suggest.repeat", { goal, time: time ?? "" });
    return time ? tFollow("suggest.stepUpRace", { goal, time }) : tFollow("suggest.stepUpFitness", { goal });
  }

  useEffect(() => {
    if (!followUpFrom || isEditMode) return;
    Promise.all([
      plansApi.get(followUpFrom),
      plansApi.followUpSummary(followUpFrom),
      profileApi.get(),
    ]).then(([prevRes, summaryRes, profileRes]) => {
      const prev: Plan = prevRes.data;
      const summary: FollowUpSummary = summaryRes.data;
      const profile: UserProfile = profileRes.data;
      setValue("goal", prev.goal as FormSchema["goal"]);
      if (prev.custom_distance_km) setValue("custom_distance_km", prev.custom_distance_km);
      if (prev.goal_kind) setValue("goal_kind", prev.goal_kind);
      if (prev.training_days) setValue("training_days", prev.training_days);
      if (prev.long_run_day) setValue("long_run_day", prev.long_run_day);
      if (prev.surface) setValue("surface", prev.surface);
      if (prev.feedback_tone) setValue("feedback_tone", prev.feedback_tone);
      setValue("duration_weeks", prev.duration_weeks);
      if (prev.strength_enabled) {
        setValue("strength", {
          enabled: true,
          location: (prev.strength_location as any) ?? "bodyweight",
          type: (prev.strength_type as any) ?? "full_body",
          days: prev.strength_days ?? [],
          equipment: (prev as any).strength_equipment ?? [],
        });
      }
      setFollowUp(summary);
      setSuggestions(summary.suggestions ?? []);
      if (summary.race?.time_seconds) setRaceTimeText(secondsToDisplay(summary.race.time_seconds) ?? "");
      // Same order the server uses: the measured race, else the previous goal distance
      const distance = summary.race?.distance_km ?? summary.goal_km;
      if (distance) setRaceDistanceText(String(Math.round(distance * 100) / 100).replace(".", locale === "nl" ? "," : "."));
      setReplacesPlan(profile.tier === "base" || profile.tier === "tempo");
    }).catch(() => {/* no summary: the form still works as a fresh plan */});
  }, [followUpFrom, isEditMode]); // eslint-disable-line react-hooks/exhaustive-deps

  const values = watch();

  async function nextStep() {
    const fields: (keyof FormSchema)[][] = [
      ["name", "goal", "custom_distance_km", "duration_weeks"],
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
        start_date: data.start_date || undefined,
        race_date: data.race_date || undefined,
        strength: data.strength?.enabled ? {
          enabled: true,
          location: data.strength.location ?? null,
          type: data.strength.type ?? null,
          days: data.strength.days ?? null,
          equipment: data.strength.equipment ?? null,
          notes: data.strength.notes ?? null,
        } : undefined,
        ...(followUpFrom && !isEditMode ? {
          previous_plan_id: followUpFrom,
          previous_race_time_seconds: clockToSeconds(raceTimeText),
          previous_race_distance_km: Number(raceDistanceText.replace(",", ".")) || undefined,
        } : {}),
      };
      if (isEditMode) {
        await plansApi.update(editPlan!.public_id, payload);
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
        router.push(`/plans/${plan.public_id}`);
        return;
      }
      router.push(`/plans/${editPlan!.public_id}`);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d: any) => `${d.loc?.slice(-1)[0] ?? "field"}: ${d.msg}`).join(" · ")
        : typeof detail === "string"
        ? detail
        : t("errors.failed");
      setError(msg);
      setLoading(false);
    }
  }

  const targetTimeDisplay = suggestedTime ?? secondsToDisplay(editPlan?.target_time_seconds);
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
            {step === 1 && followUp && (
              <div className="mb-5 rounded-xl border border-brand-700/40 bg-brand-950/30 p-4 space-y-2">
                <p className="text-sm font-semibold text-white">
                  {tFollow("title")}: {followUp.name}
                </p>
                <p className="text-xs text-slate-400">
                  {[
                    followUp.finished
                      ? tFollow("finished")
                      : tFollow("stopped", { week: followUp.stopped_in_week ?? "?" }),
                    tFollow("sessions", { done: followUp.sessions_done, planned: followUp.sessions_planned }),
                    followUp.longest_run_km ? tFollow("longest", { km: followUp.longest_run_km }) : null,
                    followUp.build_weekly_km ? tFollow("build", { km: followUp.build_weekly_km }) : null,
                    followUp.zones_recalibrated ? tFollow("zonesRecalibrated") : null,
                  ].filter(Boolean).join(" · ")}
                </p>
                <div>
                  <label className="label">{tFollow("raceTime")}</label>
                  <div className="flex items-center gap-2 text-sm text-slate-400">
                    <input
                      type="text"
                      className="input max-w-[8rem]"
                      placeholder={tFollow("raceTimePlaceholder")}
                      value={raceTimeText}
                      onChange={(e) => setRaceTimeText(e.target.value)}
                      onBlur={refreshSuggestions}
                    />
                    <span>{tFollow("raceOver")}</span>
                    <input
                      type="text"
                      inputMode="decimal"
                      className="input max-w-[6rem]"
                      value={raceDistanceText}
                      onChange={(e) => setRaceDistanceText(e.target.value)}
                      onBlur={refreshSuggestions}
                    />
                    <span>km</span>
                  </div>
                  <p className="text-[10px] text-slate-600 mt-1">{tFollow("raceTimeHint")}</p>
                </div>
                {suggestions.length > 0 && (
                  <div>
                    <p className="label">{tFollow("suggestionsTitle")}</p>
                    <div className="flex flex-wrap gap-2">
                      {suggestions.map((s) => (
                        <button
                          key={s.kind}
                          type="button"
                          onClick={() => applySuggestion(s)}
                          className="rounded-lg border border-brand-700/50 bg-brand-500/10 px-3 py-1.5 text-xs text-brand-300 hover:bg-brand-500/20"
                        >
                          {suggestionLabel(s)}
                        </button>
                      ))}
                    </div>
                    <p className="text-[10px] text-slate-600 mt-1">{tFollow("suggestionsHint")}</p>
                  </div>
                )}
                {replacesPlan && (
                  <p className="text-[11px] text-amber-400 leading-relaxed">{tFollow("replaceWarning")}</p>
                )}
              </div>
            )}
            {step === 1 && <StepGoal {...stepProps} targetTimeDisplay={targetTimeDisplay} />}
            {step === 2 && <StepAthleteProfile {...stepProps} />}
            {step === 3 && <StepTrainingPrefs {...stepProps} />}
            {step === 4 && <StepStrength watch={watch} setValue={setValue} />}
            {step === 5 && <StepReview values={values} followUpName={followUp?.name} />}
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
