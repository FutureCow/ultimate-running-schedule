"use client";

import { UseFormRegister, UseFormWatch, UseFormSetValue, FieldErrors } from "react-hook-form";
import { FormSchema } from "../PlanCreatorForm";

const GOALS = [
  { value: "5k",            label: "5 km",           desc: "Eerste 5K of sneller worden",  emoji: "🏃" },
  { value: "10k",           label: "10 km",          desc: "Klassieke afstand verbeteren",  emoji: "🎯" },
  { value: "half_marathon", label: "Halve Marathon",  desc: "21,1 km uitdaging",            emoji: "🥈" },
  { value: "marathon",      label: "Marathon",        desc: "42,2 km – de ultieme test",     emoji: "🏆" },
];

interface Props {
  register: UseFormRegister<FormSchema>;
  watch: UseFormWatch<FormSchema>;
  setValue: UseFormSetValue<FormSchema>;
  errors: FieldErrors<FormSchema>;
  getValues: any;
}

export function StepGoal({ register, watch, setValue, errors }: Props) {
  const goal = watch("goal");

  return (
    <div className="space-y-5">
      {/* Plan name */}
      <div>
        <label className="label">Naam van je plan</label>
        <input
          {...register("name")}
          placeholder="bijv. 'Sub-50 10K Rotterdam 2026'"
          className="input"
        />
        {errors.name && <p className="text-xs text-red-400 mt-1">{errors.name.message}</p>}
      </div>

      {/* Goal selector */}
      <div>
        <label className="label">Doelafstand</label>
        <div className="grid grid-cols-2 gap-2">
          {GOALS.map(({ value, label, desc, emoji }) => (
            <button
              key={value}
              type="button"
              onClick={() => setValue("goal", value as any)}
              className={`rounded-xl border p-3 text-left transition-all duration-200 ${
                goal === value
                  ? "border-brand-500 bg-brand-500/10 text-white"
                  : "border-slate-700 bg-surface-elevated text-slate-400 hover:border-slate-600"
              }`}
            >
              <span className="text-xl">{emoji}</span>
              <p className="font-semibold mt-1 text-sm">{label}</p>
              <p className="text-[11px] opacity-70">{desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Target time */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Doeltijd (min:sec)</label>
          <input
            type="text"
            placeholder="bijv. 48:30"
            className="input"
            onChange={(e) => {
              const [m, s] = e.target.value.split(":").map(Number);
              if (!isNaN(m) && !isNaN(s)) setValue("target_time_seconds", m * 60 + s);
              else if (!isNaN(m)) setValue("target_time_seconds", m * 60);
            }}
          />
          <p className="text-[10px] text-slate-600 mt-1">MM:SS of HH:MM:SS</p>
        </div>
        <div>
          <label className="label">Of: Doeltempo</label>
          <input
            {...register("target_pace_per_km")}
            type="text"
            placeholder="bijv. 4:50 /km"
            className="input"
          />
          <p className="text-[10px] text-slate-600 mt-1">Min:sec per km</p>
        </div>
      </div>

      {/* Duration */}
      <div>
        <label className="label">Planningsduur: <span className="text-brand-400 font-bold">{watch("duration_weeks")} weken</span></label>
        <input
          type="range"
          min={4} max={24} step={2}
          {...register("duration_weeks", { valueAsNumber: true })}
          className="w-full accent-brand-500"
        />
        <div className="flex justify-between text-[10px] text-slate-600 mt-1">
          <span>4 wk</span><span>12 wk</span><span>24 wk</span>
        </div>
      </div>

      {/* Start date */}
      <div>
        <label className="label">Startdatum (optioneel)</label>
        <input type="date" {...register("start_date")} className="input" />
      </div>
    </div>
  );
}
