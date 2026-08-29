"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { UseFormRegister, UseFormWatch, UseFormSetValue, FieldErrors } from "react-hook-form";
import { FormSchema } from "../PlanCreatorForm";
import { CUSTOM_GOAL, MAX_CUSTOM_DISTANCE_KM, MIN_CUSTOM_DISTANCE_KM, isUltra } from "@/lib/goal";

const GOAL_KEYS = ["5k", "10k", "half_marathon", "marathon"] as const;
const GOAL_KINDS = ["race", "fitness"] as const;
const FEEDBACK_TONES = ["scientific", "encouraging"] as const;
const TONE_EMOJIS: Record<string, string> = { scientific: "🔬", encouraging: "🌱" };
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

function addWeeksToDate(dateStr: string, weeks: number): string {
  const d = new Date(dateStr);
  d.setDate(d.getDate() + weeks * 7);
  return d.toISOString().split("T")[0];
}

function weeksFromDates(startStr: string, endStr: string): number {
  const start = new Date(startStr);
  const end = new Date(endStr);
  const diffDays = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
  return Math.max(4, Math.min(52, Math.ceil(diffDays / 7)));
}

export function StepGoal({ register, watch, setValue, errors, targetTimeDisplay }: Props) {
  const t = useTranslations("form.goal");
  const goal = watch("goal");
  const planLanguage = watch("plan_language");
  const customKm = watch("custom_distance_km");
  const goalKind = watch("goal_kind") ?? "race";
  const isCustom = goal === CUSTOM_GOAL;
  // A fitness goal has no race — the date is a target to be ready by
  const isFitness = isCustom && goalKind === "fitness";
  const feedbackTone = watch("feedback_tone") ?? "scientific";

  // Track which input is "primary" for duration
  const [durationMode, setDurationMode] = useState<"weeks" | "race_date">(
    watch("race_date") ? "race_date" : "weeks"
  );

  function handleStartOrWeeksChange(startDate: string | undefined, weeks: number | undefined) {
    if (durationMode === "weeks" && startDate && weeks) {
      setValue("race_date", addWeeksToDate(startDate, weeks));
    }
  }

  function handleRaceDateChange(raceDate: string) {
    setValue("race_date", raceDate);
    const startDate = watch("start_date");
    if (startDate && raceDate) {
      setValue("duration_weeks", weeksFromDates(startDate, raceDate));
    }
  }

  function switchMode(mode: "weeks" | "race_date") {
    setDurationMode(mode);
    if (mode === "weeks") {
      // Recalculate race_date suggestion from current start + weeks
      const startDate = watch("start_date");
      const weeks = watch("duration_weeks");
      if (startDate && weeks) {
        setValue("race_date", addWeeksToDate(startDate, weeks));
      }
    }
  }

  const currentWeeks = watch("duration_weeks");
  const currentStart = watch("start_date");
  const currentRaceDate = watch("race_date");

  // Compute suggestion immediately from start + weeks when in weeks mode
  const raceDateSuggestion =
    durationMode === "weeks" && currentStart && currentWeeks
      ? currentRaceDate || addWeeksToDate(currentStart, currentWeeks)
      : currentRaceDate || null;

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

        <button
          type="button"
          onClick={() => setValue("goal", CUSTOM_GOAL)}
          className={`mt-2 w-full rounded-xl border p-3 text-left transition-all duration-200 ${
            isCustom
              ? "border-brand-500 bg-brand-500/10 text-white"
              : "border-slate-700 bg-surface-elevated text-slate-400 hover:border-slate-600"
          }`}
        >
          <span className="text-xl">📏</span>
          <p className="font-semibold mt-1 text-sm">{t("goals.custom.label")}</p>
          <p className="text-[11px] opacity-70">{t("goals.custom.desc")}</p>
        </button>

        {isCustom && (
          <div className="mt-3 space-y-4 rounded-xl border border-slate-700 bg-surface-elevated p-3">
            <div>
              <label className="label">{t("customDistanceLabel")}</label>
              <input
                type="number"
                min={MIN_CUSTOM_DISTANCE_KM}
                max={MAX_CUSTOM_DISTANCE_KM}
                step={0.1}
                placeholder={t("customDistancePlaceholder")}
                className="input"
                {...register("custom_distance_km", { valueAsNumber: true })}
              />
              {errors.custom_distance_km ? (
                <p className="text-xs text-red-400 mt-1">{t("customDistanceRequired")}</p>
              ) : (
                <p className="text-[10px] text-slate-600 mt-1">{t("customDistanceHint")}</p>
              )}
              {isUltra(customKm) && (
                <p className="text-[11px] text-amber-400 mt-2 leading-relaxed">{t("ultraWarning")}</p>
              )}
            </div>

            <div>
              <label className="label">{t("goalKindLabel")}</label>
              <div className="flex items-center gap-1 p-1 bg-surface rounded-xl w-fit">
                {GOAL_KINDS.map((kind) => (
                  <button
                    key={kind}
                    type="button"
                    onClick={() => setValue("goal_kind", kind)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                      goalKind === kind
                        ? "bg-brand-500 text-white shadow"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {t(`goalKinds.${kind}.label`)}
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-slate-600 mt-1.5">{t(`goalKinds.${goalKind}.desc`)}</p>
            </div>
          </div>
        )}
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

      {/* Start date */}
      <div>
        <label className="label">{t("startDate")}</label>
        <input
          type="date"
          {...register("start_date")}
          className="input"
          min={new Date().toISOString().split("T")[0]}
          onChange={(e) => {
            register("start_date").onChange(e);
            handleStartOrWeeksChange(e.target.value, currentWeeks);
          }}
        />
      </div>

      {/* Duration mode toggle */}
      <div>
        <div className="flex items-center gap-1 mb-3 p-1 bg-surface-elevated rounded-xl w-fit">
          <button
            type="button"
            onClick={() => switchMode("weeks")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
              durationMode === "weeks"
                ? "bg-brand-500 text-white shadow"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t("modeWeeks")}
          </button>
          <button
            type="button"
            onClick={() => switchMode("race_date")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
              durationMode === "race_date"
                ? "bg-brand-500 text-white shadow"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t(isFitness ? "modeTargetDate" : "modeRaceDate")}
          </button>
        </div>

        {durationMode === "weeks" ? (
          <div>
            <label className="label">
              {t("durationLabel")}{" "}
              <span className="text-brand-400 font-bold">{t("durationValue", { weeks: currentWeeks })}</span>
            </label>
            <input
              type="range"
              min={4} max={24} step={2}
              {...register("duration_weeks", { valueAsNumber: true })}
              className="w-full accent-brand-500"
              onChange={(e) => {
                register("duration_weeks", { valueAsNumber: true }).onChange(e);
                handleStartOrWeeksChange(currentStart, Number(e.target.value));
              }}
            />
            <div className="flex justify-between text-[10px] text-slate-600 mt-1">
              <span>4</span><span>12</span><span>24</span>
            </div>
            {raceDateSuggestion && (
              <p className="text-[11px] text-slate-500 mt-2">
                {t(isFitness ? "targetDateSuggestion" : "raceDateSuggestion")}{" "}
                <span className="text-brand-400 font-medium">
                  {new Date(raceDateSuggestion).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}
                </span>
              </p>
            )}
          </div>
        ) : (
          <div>
            <label className="label">{t(isFitness ? "targetDateLabel" : "raceDateLabel")}</label>
            <input
              type="date"
              value={currentRaceDate || ""}
              min={currentStart || undefined}
              className="input"
              onChange={(e) => handleRaceDateChange(e.target.value)}
            />
            <p className="text-[10px] text-slate-600 mt-1">{t(isFitness ? "targetDateHint" : "raceDateHint")}</p>
            {currentWeeks && currentRaceDate && (
              <p className="text-[11px] text-slate-500 mt-2">
                {t(isFitness ? "weeksCalculatedFitness" : "weeksCalculated", { weeks: currentWeeks })}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Hidden race_date field to keep it in form state when in weeks mode */}
      <input type="hidden" {...register("race_date")} />

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

      <div>
        <label className="label">{t("feedbackToneLabel")}</label>
        <div className="grid grid-cols-2 gap-2">
          {FEEDBACK_TONES.map((tone) => (
            <button
              key={tone}
              type="button"
              onClick={() => setValue("feedback_tone", tone)}
              className={`rounded-xl border p-3 text-left transition-all duration-200 ${
                feedbackTone === tone
                  ? "border-brand-500 bg-brand-500/10 text-white"
                  : "border-slate-700 bg-surface-elevated text-slate-400 hover:border-slate-600"
              }`}
            >
              <span className="text-xl">{TONE_EMOJIS[tone]}</span>
              <p className="font-semibold mt-1 text-sm">{t(`feedbackTones.${tone}.label`)}</p>
              <p className="text-[11px] opacity-70">{t(`feedbackTones.${tone}.desc`)}</p>
            </button>
          ))}
        </div>
        <p className="text-[10px] text-slate-600 mt-1.5">{t("feedbackToneHint")}</p>
      </div>
    </div>
  );
}
