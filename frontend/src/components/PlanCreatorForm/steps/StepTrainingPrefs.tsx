"use client";

import { useTranslations } from "next-intl";
import { UseFormRegister, UseFormWatch, UseFormSetValue, FieldErrors } from "react-hook-form";
import { FormSchema } from "../PlanCreatorForm";
import { cn } from "@/lib/utils";

const DAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
const SURFACE_KEYS = ["road", "trail", "treadmill", "track"] as const;
const SURFACE_EMOJIS: Record<string, string> = {
  road: "🛣️", trail: "🌲", treadmill: "🏋️", track: "🏟️",
};

interface Props {
  register: UseFormRegister<FormSchema>;
  watch: UseFormWatch<FormSchema>;
  setValue: UseFormSetValue<FormSchema>;
  errors: FieldErrors<FormSchema>;
  getValues: any;
}

export function StepTrainingPrefs({ watch, setValue, errors }: Props) {
  const t = useTranslations("form.prefs");
  const tDays = useTranslations("days");

  const trainingDays = watch("training_days") || [];
  const longRunDay = watch("long_run_day");
  const surface = watch("surface");

  function toggleDay(day: string) {
    if (trainingDays.includes(day)) {
      setValue("training_days", trainingDays.filter((d) => d !== day));
    } else {
      setValue("training_days", [...trainingDays, day]);
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <label className="label">
          {t("trainingDays")}{" "}
          <span className="text-brand-400 font-bold">({t("selected", { count: trainingDays.length })})</span>
        </label>
        <div className="grid grid-cols-7 gap-1.5">
          {DAYS_EN.map((val, i) => {
            const selected = trainingDays.includes(val);
            return (
              <button
                key={val}
                type="button"
                onClick={() => toggleDay(val)}
                className={cn(
                  "rounded-xl py-2.5 text-xs font-semibold transition-all duration-200",
                  selected
                    ? "bg-brand-500 text-white shadow-lg shadow-brand-500/25"
                    : "bg-surface-elevated text-slate-500 hover:bg-slate-700 hover:text-slate-300"
                )}
              >
                {tDays(`abbr.${i}`)}
              </button>
            );
          })}
        </div>
        {errors.training_days && (
          <p className="text-xs text-red-400 mt-1">{errors.training_days.message}</p>
        )}
      </div>

      <div>
        <label className="label">{t("longRunDay")}</label>
        <div className="grid grid-cols-7 gap-1.5">
          {DAYS_EN.map((val, i) => (
            <button
              key={val}
              type="button"
              onClick={() => setValue("long_run_day", val)}
              className={cn(
                "rounded-xl py-2.5 text-xs font-semibold transition-all duration-200",
                longRunDay === val
                  ? "bg-blue-500 text-white shadow-lg shadow-blue-500/25"
                  : "bg-surface-elevated text-slate-500 hover:bg-slate-700 hover:text-slate-300",
                !trainingDays.includes(val) && "opacity-40"
              )}
            >
              {tDays(`abbr.${i}`)}
            </button>
          ))}
        </div>
        <p className="text-[10px] text-slate-600 mt-1">{t("longRunDayHint")}</p>
      </div>

      <div>
        <label className="label">{t("surface")}</label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {SURFACE_KEYS.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setValue("surface", key)}
              className={cn(
                "rounded-xl border py-3 text-sm font-medium transition-all duration-200",
                surface === key
                  ? "border-brand-500 bg-brand-500/10 text-white"
                  : "border-slate-700 bg-surface-elevated text-slate-400 hover:border-slate-600"
              )}
            >
              <span className="text-xl block mb-1">{SURFACE_EMOJIS[key]}</span>
              {t(`surfaces.${key}`)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
