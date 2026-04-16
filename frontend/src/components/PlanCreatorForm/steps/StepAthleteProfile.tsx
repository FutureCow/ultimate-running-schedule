"use client";

import { useTranslations } from "next-intl";
import { UseFormRegister, UseFormWatch, UseFormSetValue, FieldErrors } from "react-hook-form";
import { FormSchema } from "../PlanCreatorForm";

interface Props {
  register: UseFormRegister<FormSchema>;
  watch: UseFormWatch<FormSchema>;
  setValue: UseFormSetValue<FormSchema>;
  errors: FieldErrors<FormSchema>;
  getValues: any;
}

export function StepAthleteProfile({ register, errors }: Props) {
  const t = useTranslations("form.profile");

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="label">{t("age")}</label>
          <input
            type="number"
            {...register("age", { valueAsNumber: true })}
            placeholder="30"
            className="input text-center"
          />
          {errors.age && <p className="text-[10px] text-red-400 mt-1">{errors.age.message}</p>}
        </div>
        <div>
          <label className="label">{t("height")}</label>
          <input
            type="number"
            {...register("height_cm", { valueAsNumber: true })}
            placeholder="175"
            className="input text-center"
          />
        </div>
        <div>
          <label className="label">{t("weight")}</label>
          <input
            type="number"
            step="0.1"
            {...register("weight_kg", { valueAsNumber: true })}
            placeholder="70"
            className="input text-center"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">{t("weeklyKm")}</label>
          <input
            type="number"
            step="0.5"
            {...register("weekly_km", { valueAsNumber: true })}
            placeholder="40"
            className="input"
          />
          <p className="text-[10px] text-slate-600 mt-1">{t("weeklyKmHint")}</p>
        </div>
        <div>
          <label className="label">{t("weeklyRuns")}</label>
          <input
            type="number"
            {...register("weekly_runs", { valueAsNumber: true })}
            placeholder="4"
            className="input"
          />
          <p className="text-[10px] text-slate-600 mt-1">{t("weeklyRunsHint")}</p>
        </div>
      </div>

      <div>
        <label className="label">{t("injuries")}</label>
        <textarea
          {...register("injuries")}
          rows={3}
          placeholder={t("injuriesPlaceholder")}
          className="input resize-none"
        />
        <p className="text-[10px] text-slate-600 mt-1">{t("injuriesHint")}</p>
      </div>

      <div className="rounded-xl border border-brand-700/30 bg-brand-950/30 px-3 py-2.5 text-xs text-slate-400">
        💡 <span className="text-brand-300 font-medium">{t("garminNoteLabel")}</span> — {t("garminNoteText")}
      </div>
    </div>
  );
}
