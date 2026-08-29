"use client";

import { useTranslations, useLocale } from "next-intl";
import { FormSchema } from "../PlanCreatorForm";
import { secondsToTime } from "@/lib/utils";
import { goalLabel } from "@/lib/goal";
import { CheckCircle2 } from "lucide-react";

const DAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

export function StepReview({ values }: { values: Partial<FormSchema> }) {
  const t = useTranslations("form.review");
  const tGoals = useTranslations("goals");
  const goalLocale = useLocale();
  const tDays = useTranslations("days");
  const tPrefs = useTranslations("form.prefs");
  const tGoal = useTranslations("form.goal");

  const rows = [
    { label: t("rows.name"),         value: values.name },
    { label: t("rows.goal"),         value: goalLabel(tGoals, values.goal, values.custom_distance_km, goalLocale) },
    ...(values.goal === "custom"
      ? [{ label: t("rows.goalKind"), value: tGoal(`goalKinds.${values.goal_kind ?? "race"}.label`) }]
      : []),
    {
      label: t("rows.targetTime"),
      value: values.target_time_seconds
        ? secondsToTime(values.target_time_seconds)
        : values.target_pace_per_km
        ? `${values.target_pace_per_km}/km`
        : "—",
    },
    { label: t("rows.duration"),     value: values.duration_weeks ? t("durationFormat", { weeks: values.duration_weeks }) : "—" },
    { label: t("rows.age"),          value: values.age ? t("ageFormat", { age: values.age }) : "—" },
    { label: t("rows.heightWeight"), value: t("heightWeightFormat", { height: values.height_cm || "—", weight: values.weight_kg || "—" }) },
    { label: t("rows.volume"),       value: t("volumeFormat", { km: values.weekly_km || "—", runs: values.weekly_runs || "—" }) },
    { label: t("rows.injuries"),     value: values.injuries || t("noInjuries") },
    { label: t("rows.extraNotes"),   value: values.extra_notes || "—" },
    {
      label: t("rows.trainingDays"),
      value: (values.training_days || [])
        .map((d) => tDays(`full.${DAYS_EN.indexOf(d)}`))
        .filter(Boolean)
        .join(", "),
    },
    {
      label: t("rows.longRunDay"),
      value: values.long_run_day ? tDays(`full.${DAYS_EN.indexOf(values.long_run_day)}`) : "—",
    },
    { label: t("rows.surface"),       value: values.surface ? tPrefs(`surfaces.${values.surface}`) : "—" },
    { label: t("rows.startDate"),     value: values.start_date || "—" },
    {
      // A fitness goal has no race; that date is when you want to be ready
      label: values.goal_kind === "fitness" ? tGoal("targetDateLabel") : t("rows.raceDate"),
      value: values.race_date || "—",
    },
    { label: t("rows.feedbackTone"),  value: tGoal(`feedbackTones.${values.feedback_tone ?? "scientific"}.label`) },
    { label: t("rows.planLanguage"),  value: values.plan_language === "en" ? "🇬🇧 English" : "🇳🇱 Nederlands" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-1">
        <CheckCircle2 className="w-5 h-5 text-brand-400" />
        <p className="text-sm text-slate-300">
          {t("checkNote")} <strong className="text-white">{t("checkNoteButton")}</strong> {t("checkNoteSuffix")}
        </p>
      </div>

      <div className="rounded-xl border border-slate-700/50 divide-y divide-slate-700/50 overflow-hidden">
        {rows.map(({ label, value }) => (
          <div key={label} className="flex items-center justify-between px-4 py-2.5">
            <span className="text-xs text-slate-500 font-medium w-36 shrink-0">{label}</span>
            <span className="text-sm text-slate-200 text-right">{value || "—"}</span>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-brand-700/30 bg-brand-950/30 px-4 py-3 text-xs text-slate-400">
        🤖 <span className="text-brand-300 font-medium">{t("aiNoteLabel")}</span> — {t("aiNoteText")}
      </div>
    </div>
  );
}
