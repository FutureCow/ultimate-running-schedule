"use client";

import { UseFormRegister, UseFormWatch, UseFormSetValue, FieldErrors } from "react-hook-form";
import { FormSchema } from "../PlanCreatorForm";

interface Props {
  register: UseFormRegister<FormSchema>;
  watch: UseFormWatch<FormSchema>;
  setValue: UseFormSetValue<FormSchema>;
  errors: FieldErrors<FormSchema>;
  getValues: any;
}

export function StepAthleteProfile({ register, watch, errors }: Props) {
  return (
    <div className="space-y-5">
      {/* Age / Height / Weight */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="label">Leeftijd</label>
          <input
            type="number"
            {...register("age", { valueAsNumber: true })}
            placeholder="30"
            className="input text-center"
          />
          {errors.age && <p className="text-[10px] text-red-400 mt-1">{errors.age.message}</p>}
        </div>
        <div>
          <label className="label">Lengte (cm)</label>
          <input
            type="number"
            {...register("height_cm", { valueAsNumber: true })}
            placeholder="175"
            className="input text-center"
          />
        </div>
        <div>
          <label className="label">Gewicht (kg)</label>
          <input
            type="number"
            step="0.1"
            {...register("weight_kg", { valueAsNumber: true })}
            placeholder="70"
            className="input text-center"
          />
        </div>
      </div>

      {/* Current fitness */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Km per week</label>
          <input
            type="number"
            step="0.5"
            {...register("weekly_km", { valueAsNumber: true })}
            placeholder="40"
            className="input"
          />
          <p className="text-[10px] text-slate-600 mt-1">Huidige wekelijkse afstand</p>
        </div>
        <div>
          <label className="label">Ritten per week</label>
          <input
            type="number"
            {...register("weekly_runs", { valueAsNumber: true })}
            placeholder="4"
            className="input"
          />
          <p className="text-[10px] text-slate-600 mt-1">Gemiddeld aantal trainingen</p>
        </div>
      </div>

      {/* Injuries */}
      <div>
        <label className="label">Blessures / beperkingen</label>
        <textarea
          {...register("injuries")}
          rows={3}
          placeholder="bijv. lichte kniepijn links, oud hamstringletsel rechts…"
          className="input resize-none"
        />
        <p className="text-[10px] text-slate-600 mt-1">
          De AI houdt hier rekening mee bij het samenstellen van je plan.
        </p>
      </div>

      {/* Garmin data note */}
      <div className="rounded-xl border border-brand-700/30 bg-brand-950/30 px-3 py-2.5 text-xs text-slate-400">
        💡 <span className="text-brand-300 font-medium">Garmin data</span> — als je Garmin-credentials hebt opgeslagen worden de laatste 3 maanden trainingsdata automatisch meegenomen voor nauwkeurigere pace-berekeningen.
      </div>
    </div>
  );
}
