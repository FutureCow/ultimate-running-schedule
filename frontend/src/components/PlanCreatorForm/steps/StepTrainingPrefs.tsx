"use client";

import { UseFormRegister, UseFormWatch, UseFormSetValue, FieldErrors } from "react-hook-form";
import { FormSchema } from "../PlanCreatorForm";
import { cn } from "@/lib/utils";

const DAYS_NL = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"];
const DAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

const SURFACES = [
  { value: "road",      label: "Asfalt",    emoji: "🛣️" },
  { value: "trail",     label: "Trail",     emoji: "🌲" },
  { value: "treadmill", label: "Loopband",  emoji: "🏋️" },
  { value: "track",     label: "Atletiek",  emoji: "🏟️" },
];

interface Props {
  register: UseFormRegister<FormSchema>;
  watch: UseFormWatch<FormSchema>;
  setValue: UseFormSetValue<FormSchema>;
  errors: FieldErrors<FormSchema>;
  getValues: any;
}

export function StepTrainingPrefs({ watch, setValue, errors }: Props) {
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
      {/* Training days */}
      <div>
        <label className="label">
          Trainingsdagen{" "}
          <span className="text-brand-400 font-bold">({trainingDays.length} geselecteerd)</span>
        </label>
        <div className="grid grid-cols-7 gap-1.5">
          {DAYS_NL.map((day, i) => {
            const val = DAYS_EN[i];
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
                {day.slice(0, 2)}
              </button>
            );
          })}
        </div>
        {errors.training_days && (
          <p className="text-xs text-red-400 mt-1">{errors.training_days.message}</p>
        )}
      </div>

      {/* Long run day */}
      <div>
        <label className="label">Lange duurloop dag</label>
        <div className="grid grid-cols-7 gap-1.5">
          {DAYS_NL.map((day, i) => {
            const val = DAYS_EN[i];
            return (
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
                {day.slice(0, 2)}
              </button>
            );
          })}
        </div>
        <p className="text-[10px] text-slate-600 mt-1">Kies de dag voor je wekelijkse lange duurloop</p>
      </div>

      {/* Surface */}
      <div>
        <label className="label">Ondergrond</label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {SURFACES.map(({ value, label, emoji }) => (
            <button
              key={value}
              type="button"
              onClick={() => setValue("surface", value)}
              className={cn(
                "rounded-xl border py-3 text-sm font-medium transition-all duration-200",
                surface === value
                  ? "border-brand-500 bg-brand-500/10 text-white"
                  : "border-slate-700 bg-surface-elevated text-slate-400 hover:border-slate-600"
              )}
            >
              <span className="text-xl block mb-1">{emoji}</span>
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
