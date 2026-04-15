"use client";

import { FormSchema } from "../PlanCreatorForm";
import { GOAL_LABELS, DAYS, secondsToTime } from "@/lib/utils";
import { CheckCircle2 } from "lucide-react";

const DAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

export function StepReview({ values }: { values: Partial<FormSchema> }) {
  const rows = [
    { label: "Plannaam", value: values.name },
    { label: "Doel", value: values.goal ? GOAL_LABELS[values.goal] : "—" },
    { label: "Doeltijd", value: values.target_time_seconds ? secondsToTime(values.target_time_seconds) : values.target_pace_per_km ? `${values.target_pace_per_km}/km` : "—" },
    { label: "Duur", value: `${values.duration_weeks} weken` },
    { label: "Leeftijd", value: values.age ? `${values.age} jaar` : "—" },
    { label: "Lengte / Gewicht", value: `${values.height_cm || "—"} cm / ${values.weight_kg || "—"} kg` },
    { label: "Huidig volume", value: `${values.weekly_km || "—"} km/week · ${values.weekly_runs || "—"} ritten` },
    { label: "Blessures", value: values.injuries || "Geen" },
    {
      label: "Trainingsdagen",
      value: (values.training_days || [])
        .map((d) => DAYS[DAYS_EN.indexOf(d)])
        .filter(Boolean)
        .join(", "),
    },
    { label: "Lange loop dag", value: values.long_run_day ? DAYS[DAYS_EN.indexOf(values.long_run_day)] : "—" },
    { label: "Ondergrond", value: values.surface || "—" },
    { label: "Startdatum", value: values.start_date || "—" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-1">
        <CheckCircle2 className="w-5 h-5 text-brand-400" />
        <p className="text-sm text-slate-300">
          Controleer je gegevens. Als alles klopt klik je op <strong className="text-white">Genereer Plan</strong> en maakt Claude AI jouw persoonlijk schema.
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
        🤖 <span className="text-brand-300 font-medium">AI Plan Generatie</span> — Claude Opus analyseert je profiel en Garmin-data en maakt een wetenschappelijk onderbouwd schema. Dit kan 20-30 seconden duren.
      </div>
    </div>
  );
}
