"use client";

import { useTranslations } from "next-intl";
import { UseFormWatch, UseFormSetValue } from "react-hook-form";
import { FormSchema } from "../PlanCreatorForm";
import { cn } from "@/lib/utils";
import { Dumbbell } from "lucide-react";

const DAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
const LOCATION_KEYS = ["bodyweight", "home_equipment", "gym"] as const;
const FOCUS_KEYS = ["core_stability", "max_strength", "plyometrics", "injury_prevention", "full_body"] as const;
const EQUIPMENT_KEYS = [
  "dumbbells",
  "resistance_bands",
  "kettlebell",
  "pull_up_bar",
  "foam_roller",
  "yoga_mat",
  "jump_rope",
  "stability_ball",
  "trx",
  "step",
] as const;

const LOCATION_EMOJIS: Record<string, string> = {
  bodyweight:     "🧘",
  home_equipment: "🏠",
  gym:            "🏋️",
};

const FOCUS_EMOJIS: Record<string, string> = {
  core_stability:    "🎯",
  max_strength:      "💪",
  plyometrics:       "⚡",
  injury_prevention: "🛡️",
  full_body:         "🔄",
};

const EQUIPMENT_EMOJIS: Record<string, string> = {
  dumbbells:       "🏋️",
  resistance_bands:"🔴",
  kettlebell:      "⚫",
  pull_up_bar:     "🔗",
  foam_roller:     "🟢",
  yoga_mat:        "🟦",
  jump_rope:       "🪢",
  stability_ball:  "🔵",
  trx:             "⬛",
  step:            "🪜",
};

interface Props {
  watch: UseFormWatch<FormSchema>;
  setValue: UseFormSetValue<FormSchema>;
  register?: any;
}

export function StepStrength({ watch, setValue }: Props) {
  const t = useTranslations("form.strength");
  const tDays = useTranslations("days");

  const enabled       = watch("strength.enabled") ?? false;
  const location      = watch("strength.location");
  const focusType     = watch("strength.type");
  const strengthDays  = (watch("strength.days") ?? []) as number[];
  const equipment     = (watch("strength.equipment") ?? []) as string[];
  const notes         = watch("strength.notes") ?? "";

  function toggleStrengthDay(dayNum: number) {
    if (strengthDays.includes(dayNum)) {
      setValue("strength.days", strengthDays.filter((d) => d !== dayNum));
    } else {
      setValue("strength.days", [...strengthDays, dayNum]);
    }
  }

  function toggleEquipment(key: string) {
    if (equipment.includes(key)) {
      setValue("strength.equipment", equipment.filter((e) => e !== key));
    } else {
      setValue("strength.equipment", [...equipment, key]);
    }
  }

  return (
    <div className="space-y-6">
      {/* Toggle */}
      <div
        className={cn(
          "flex items-start gap-4 rounded-2xl border p-4 cursor-pointer transition-all duration-200",
          enabled
            ? "border-violet-500/50 bg-violet-500/10"
            : "border-slate-700/50 bg-surface-elevated hover:border-slate-600"
        )}
        onClick={() => {
          setValue("strength.enabled", !enabled);
          if (!enabled) {
            setValue("strength.location", "bodyweight");
            setValue("strength.type", "full_body");
            setValue("strength.days", []);
            setValue("strength.equipment", []);
          }
        }}
      >
        <div className={cn(
          "mt-0.5 w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-all",
          enabled ? "border-violet-500 bg-violet-500" : "border-slate-600"
        )}>
          {enabled && <span className="text-white text-xs font-bold">✓</span>}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <Dumbbell className="w-4 h-4 text-violet-400" />
            <span className="text-sm font-semibold text-white">{t("toggleLabel")}</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">{t("toggleHint")}</p>
        </div>
      </div>

      {enabled && (
        <>
          {/* Location */}
          <div>
            <label className="label">{t("locationLabel")}</label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {LOCATION_KEYS.map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    setValue("strength.location", key);
                    if (key !== "home_equipment") setValue("strength.equipment", []);
                  }}
                  className={cn(
                    "rounded-xl border p-3 text-left transition-all duration-200",
                    location === key
                      ? "border-violet-500 bg-violet-500/10 text-white"
                      : "border-slate-700 bg-surface-elevated text-slate-400 hover:border-slate-600"
                  )}
                >
                  <span className="text-xl block mb-1">{LOCATION_EMOJIS[key]}</span>
                  <p className="text-xs font-semibold">{t(`locations.${key}.label`)}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">{t(`locations.${key}.desc`)}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Equipment checklist — only for home_equipment */}
          {location === "home_equipment" && (
            <div>
              <label className="label">{t("equipmentLabel")}</label>
              <p className="text-[10px] text-slate-600 mb-2">{t("equipmentHint")}</p>
              <div className="grid grid-cols-2 gap-2">
                {EQUIPMENT_KEYS.map((key) => {
                  const checked = equipment.includes(key);
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => toggleEquipment(key)}
                      className={cn(
                        "flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-all duration-200",
                        checked
                          ? "border-violet-500 bg-violet-500/10 text-white"
                          : "border-slate-700 bg-surface-elevated text-slate-400 hover:border-slate-600"
                      )}
                    >
                      <div className={cn(
                        "w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-all",
                        checked ? "border-violet-400 bg-violet-500" : "border-slate-600"
                      )}>
                        {checked && <span className="text-white text-[9px] font-bold leading-none">✓</span>}
                      </div>
                      <span className="text-sm leading-none">{EQUIPMENT_EMOJIS[key]}</span>
                      <span className="text-xs font-medium">{t(`equipment.${key}`)}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Focus type */}
          <div>
            <label className="label">{t("focusLabel")}</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {FOCUS_KEYS.map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setValue("strength.type", key)}
                  className={cn(
                    "rounded-xl border p-3 text-left transition-all duration-200",
                    focusType === key
                      ? "border-violet-500 bg-violet-500/10 text-white"
                      : "border-slate-700 bg-surface-elevated text-slate-400 hover:border-slate-600"
                  )}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-base">{FOCUS_EMOJIS[key]}</span>
                    <p className="text-xs font-semibold">{t(`focusTypes.${key}.label`)}</p>
                  </div>
                  <p className="text-[10px] text-slate-500">{t(`focusTypes.${key}.desc`)}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Preferred days */}
          <div>
            <label className="label">{t("daysLabel")}</label>
            <div className="grid grid-cols-7 gap-1.5">
              {DAYS_EN.map((_, i) => {
                const dayNum = i + 1;
                const selected = strengthDays.includes(dayNum);
                return (
                  <button
                    key={dayNum}
                    type="button"
                    onClick={() => toggleStrengthDay(dayNum)}
                    className={cn(
                      "rounded-xl py-2.5 text-xs font-semibold transition-all duration-200",
                      selected
                        ? "bg-violet-500 text-white shadow-lg shadow-violet-500/25"
                        : "bg-surface-elevated text-slate-500 hover:bg-slate-700 hover:text-slate-300"
                    )}
                  >
                    {tDays(`abbr.${i}`)}
                  </button>
                );
              })}
            </div>
            <p className="text-[10px] text-slate-600 mt-1">{t("daysHint")}</p>
          </div>

          {/* Free-text notes */}
          <div>
            <label className="label">{t("notesLabel")}</label>
            <textarea
              rows={3}
              className="input resize-none"
              placeholder={t("notesPlaceholder")}
              value={notes}
              onChange={(e) => setValue("strength.notes", e.target.value || undefined)}
            />
            <p className="text-[10px] text-slate-600 mt-1">{t("notesHint")}</p>
          </div>
        </>
      )}
    </div>
  );
}
