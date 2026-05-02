"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { X, Layers } from "lucide-react";

const WORKOUT_TYPES = ["easy_run", "long_run", "tempo", "interval", "recovery", "strength"] as const;
const DAYS = ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"] as const;
const PACE_KEYS = [
  { key: "main", label: "Hoofdtempo" },
  { key: "warmup", label: "Warming-up" },
  { key: "cooldown", label: "Cooling-down" },
];

type Action = "move_day" | "change_pace";
type PaceMode = "absolute" | "delta";

interface Props {
  planPublicId: string;
  totalWeeks: number;
  onClose: () => void;
  onSave: (filter: {
    day_number?: number | null;
    workout_type?: string | null;
    only_future: boolean;
  }, update: {
    day_number?: number | null;
    target_pace_key?: string | null;
    target_pace_value?: string | null;
    target_pace_delta_seconds?: number | null;
  }) => void;
  isSaving?: boolean;
  lastResult?: number | null;
}

export function BulkEditModal({ onClose, onSave, isSaving, lastResult }: Props) {
  const t = useTranslations("workout");

  // Filter state
  const [filterDay, setFilterDay] = useState<number | null>(null);
  const [filterType, setFilterType] = useState<string | null>(null);
  const [onlyFuture, setOnlyFuture] = useState(true);

  // Action
  const [action, setAction] = useState<Action>("move_day");

  // Move day
  const [targetDay, setTargetDay] = useState<number | null>(null);

  // Change pace
  const [paceKey, setPaceKey] = useState("main");
  const [paceMode, setPaceMode] = useState<PaceMode>("absolute");
  const [paceValue, setPaceValue] = useState("");
  const [paceDelta, setPaceDelta] = useState("");
  const [paceError, setPaceError] = useState("");

  function validatePace(v: string) {
    return v === "" || /^\d+:\d{2}(-\d+:\d{2})?$/.test(v.trim());
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (action === "change_pace") {
      if (paceMode === "absolute" && !validatePace(paceValue)) {
        setPaceError("Formaat: 5:10 of 5:10-5:20");
        return;
      }
      if (paceMode === "delta") {
        const n = parseInt(paceDelta.replace(/^\+/, ""), 10);
        if (isNaN(n) || paceDelta.trim() === "") {
          setPaceError("Vul een getal in, bijv. -10 of +15");
          return;
        }
      }
    }
    const filter = {
      day_number: filterDay,
      workout_type: filterType,
      only_future: onlyFuture,
    };
    let update: Parameters<typeof onSave>[1];
    if (action === "move_day") {
      update = { day_number: targetDay };
    } else if (paceMode === "absolute") {
      update = { target_pace_key: paceKey, target_pace_value: paceValue.trim() };
    } else {
      const delta = parseInt(paceDelta.replace(/^\+/, ""), 10);
      update = { target_pace_key: paceKey, target_pace_delta_seconds: delta };
    }
    onSave(filter, update);
  }

  const paceInputFilled = paceMode === "absolute" ? paceValue.trim() !== "" : paceDelta.trim() !== "";
  const canSubmit =
    (filterDay !== null || filterType !== null) &&
    (action === "move_day" ? targetDay !== null : paceInputFilled);

  const sel = "bg-brand-500/20 text-brand-300 border-brand-500/40";
  const unsel = "bg-slate-800/60 text-slate-400 border-slate-700/40 hover:border-slate-600";

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm px-4 pb-4 sm:pb-0"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-md bg-surface-card border border-slate-700/60 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/40">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-brand-400" />
            <h2 className="text-base font-bold text-white">{t("bulk.title")}</h2>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="px-5 py-4 space-y-5">

            {/* Filter: day */}
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{t("bulk.filterDay")}</p>
              <div className="flex gap-1.5 flex-wrap">
                {DAYS.map((label, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setFilterDay(filterDay === i + 1 ? null : i + 1)}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${filterDay === i + 1 ? sel : unsel}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Filter: type */}
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{t("bulk.filterType")}</p>
              <div className="flex gap-1.5 flex-wrap">
                {WORKOUT_TYPES.map((wt) => (
                  <button
                    key={wt}
                    type="button"
                    onClick={() => setFilterType(filterType === wt ? null : wt)}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${filterType === wt ? sel : unsel}`}
                  >
                    {t(`types.${wt}`)}
                  </button>
                ))}
              </div>
            </div>

            {/* Only future toggle */}
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={onlyFuture}
                onChange={(e) => setOnlyFuture(e.target.checked)}
                className="w-4 h-4 rounded accent-brand-500"
              />
              <span className="text-sm text-slate-300">{t("bulk.onlyFuture")}</span>
            </label>

            <div className="border-t border-slate-700/40" />

            {/* Action selector */}
            <div className="grid grid-cols-2 gap-2">
              {(["move_day", "change_pace"] as Action[]).map((a) => (
                <button
                  key={a}
                  type="button"
                  onClick={() => setAction(a)}
                  className={`py-2 rounded-xl border text-sm font-semibold transition-colors ${action === a ? sel : unsel}`}
                >
                  {t(`bulk.action_${a}`)}
                </button>
              ))}
            </div>

            {/* Move day */}
            {action === "move_day" && (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{t("bulk.moveTo")}</p>
                <div className="flex gap-1.5 flex-wrap">
                  {DAYS.map((label, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setTargetDay(i + 1)}
                      className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${targetDay === i + 1 ? sel : unsel}`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Change pace */}
            {action === "change_pace" && (
              <div className="space-y-3">
                {/* Pace key selector */}
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{t("bulk.paceType")}</p>
                  <div className="flex gap-1.5">
                    {PACE_KEYS.map(({ key, label }) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setPaceKey(key)}
                        className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${paceKey === key ? sel : unsel}`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Absolute / delta mode toggle */}
                <div className="grid grid-cols-2 gap-2">
                  {(["absolute", "delta"] as PaceMode[]).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => { setPaceMode(m); setPaceError(""); }}
                      className={`py-1.5 rounded-lg border text-xs font-semibold transition-colors ${paceMode === m ? sel : unsel}`}
                    >
                      {t(`bulk.paceMode_${m}`)}
                    </button>
                  ))}
                </div>

                {/* Absolute input */}
                {paceMode === "absolute" && (
                  <div className="space-y-1">
                    <div className="relative">
                      <input
                        type="text"
                        value={paceValue}
                        onChange={(e) => { setPaceValue(e.target.value); setPaceError(""); }}
                        placeholder="6:50-7:00"
                        className={`w-full bg-slate-800/60 border rounded-xl px-3 py-2.5 pr-14 text-sm font-mono text-white placeholder-slate-500 focus:outline-none focus:ring-1 ${
                          paceError ? "border-red-500/60 focus:ring-red-500/30" : "border-slate-700/60 focus:border-brand-500/60 focus:ring-brand-500/30"
                        }`}
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">/km</span>
                    </div>
                    {paceError && <p className="text-xs text-red-400">{paceError}</p>}
                  </div>
                )}

                {/* Delta input */}
                {paceMode === "delta" && (
                  <div className="space-y-1">
                    <div className="relative">
                      <input
                        type="text"
                        inputMode="numeric"
                        value={paceDelta}
                        onChange={(e) => { setPaceDelta(e.target.value); setPaceError(""); }}
                        placeholder={t("bulk.paceDeltaPlaceholder")}
                        className={`w-full bg-slate-800/60 border rounded-xl px-3 py-2.5 pr-20 text-sm font-mono text-white placeholder-slate-500 focus:outline-none focus:ring-1 ${
                          paceError ? "border-red-500/60 focus:ring-red-500/30" : "border-slate-700/60 focus:border-brand-500/60 focus:ring-brand-500/30"
                        }`}
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">{t("bulk.paceDeltaSuffix")}</span>
                    </div>
                    <p className="text-xs text-slate-500">Negatief = sneller, positief = langzamer</p>
                    {paceError && <p className="text-xs text-red-400">{paceError}</p>}
                  </div>
                )}
              </div>
            )}

            {/* Result feedback */}
            {lastResult !== null && lastResult !== undefined && (
              <p className="text-sm text-emerald-400 font-medium">
                {t("bulk.result", { count: lastResult })}
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-slate-700/40">
            <button type="button" onClick={onClose} className="btn-ghost text-sm px-4 py-2">
              {t("edit.cancel")}
            </button>
            <button
              type="submit"
              disabled={isSaving || !canSubmit}
              className="btn-primary text-sm px-4 py-2 gap-2 flex items-center disabled:opacity-40"
            >
              {isSaving && <span className="w-3.5 h-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />}
              {t("bulk.apply")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
