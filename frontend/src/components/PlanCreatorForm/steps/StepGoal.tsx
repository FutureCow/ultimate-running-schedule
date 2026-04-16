"use client";

import { useTranslations } from "next-intl";
import { UseFormRegister, UseFormWatch, UseFormSetValue, FieldErrors } from "react-hook-form";
import { FormSchema } from "../PlanCreatorForm";

const GOAL_KEYS = ["5k", "10k", "half_marathon", "marathon"] as const;
const GOAL_EMOJIS: Record<string, string> = {
  "5k": "🏃", "10k": "🎯", half_marathon: "🥈", marathon: "🏆",
};

interface Props {
  register: UseFormRegister<FormSchema>;
  watch: UseFormWatch<FormSchema>;
  setValue: UseFormSetValue<FormSchema>;
  errors: FieldErrors<FormSchema>;
  getValues: any;
  targetTimeDisplay?: string;
}

export function StepGoal({ register, watch, setValue, errors, targetTimeDisplay }: Props) {
  const t = useTranslations("form.goal");
  const goal = watch("goal");
  const planLanguage = watch("plan_language");

  return (
    <div className="space-y-5">
      <div>
        <label className="label">{t("planName")}</label>
        <input
          {...register("name")}
          placeholder={t("planNamePlaceholder")}
          className="input"
        />
        {errors.name && <p className="text-xs text-red-400 mt-1">{errors.name.message}</p>}
      </div>

      <div>
        <label className="label">{t("goalDistance")}</label>
        <div className="grid grid-cols-2 gap-2">
          {GOAL_KEYS.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setValue("goal", key as any)}
              className={`rounded-xl border p-3 text-left transition-all duration-200 ${
                goal === key
                  ? "border-brand-500 bg-brand-500/10 text-white"
                  : "border-slate-700 bg-surface-elevated text-slate-400 hover:border-slate-600"
              }`}
            >
              <span className="text-xl">{GOAL_EMOJIS[key]}</span>
              <p className="font-semibold mt-1 text-sm">{t(`goals.${key}.label`)}</p>
              <p className="text-[11px] opacity-70">{t(`goals.${key}.desc`)}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">{t("targetTime")}</label>
          <input
            type="text"
            placeholder={t("targetTimePlaceholder")}
            className="input"
            defaultValue={targetTimeDisplay}
            onChange={(e) => {
              const [m, s] = e.target.value.split(":").map(Number);
              if (!isNaN(m) && !isNaN(s)) setValue("target_time_seconds", m * 60 + s);
              else if (!isNaN(m)) setValue("target_time_seconds", m * 60);
            }}
          />
          <p className="text-[10px] text-slate-600 mt-1">{t("targetTimeHint")}</p>
        </div>
        <div>
          <label className="label">{t("targetPace")}</label>
          <input
            {...register("target_pace_per_km")}
            type="text"
            placeholder={t("targetPacePlaceholder")}
            className="input"
          />
          <p className="text-[10px] text-slate-600 mt-1">{t("targetPaceHint")}</p>
        </div>
      </div>

      <div>
        <label className="label">
          {t("durationLabel")} <span className="text-brand-400 font-bold">{t("durationValue", { weeks: watch("duration_weeks") })}</span>
        </label>
        <input
          type="range"
          min={4} max={24} step={2}
          {...register("duration_weeks", { valueAsNumber: true })}
          className="w-full accent-brand-500"
        />
        <div className="flex justify-between text-[10px] text-slate-600 mt-1">
          <span>4</span><span>12</span><span>24</span>
        </div>
      </div>

      <div>
        <label className="label">{t("startDate")}</label>
        <input type="date" {...register("start_date")} className="input" />
      </div>

      <div>
        <label className="label">{t("planLanguageLabel")}</label>
        <div className="grid grid-cols-2 gap-2">
          {(["nl", "en"] as const).map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => setValue("plan_language", lang)}
              className={`rounded-xl border p-3 text-left transition-all duration-200 ${
                planLanguage === lang
                  ? "border-brand-500 bg-brand-500/10 text-white"
                  : "border-slate-700 bg-surface-elevated text-slate-400 hover:border-slate-600"
              }`}
            >
              <span className="text-xl">{lang === "nl" ? "🇳🇱" : "🇬🇧"}</span>
              <p className="font-semibold mt-1 text-sm">{t(`planLanguages.${lang}.label`)}</p>
              <p className="text-[11px] opacity-70">{t(`planLanguages.${lang}.desc`)}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
