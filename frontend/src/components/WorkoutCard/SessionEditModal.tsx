"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { X, Save } from "lucide-react";
import { WorkoutSession } from "@/types";

interface Props {
  session: WorkoutSession;
  onClose: () => void;
  onSave: (data: {
    title?: string;
    description?: string;
    distance_km?: number | null;
    duration_minutes?: number | null;
    target_paces?: Record<string, string>;
    scheduled_date?: string;
  }) => void;
  isSaving?: boolean;
}

const PACE_LABELS: Record<string, string> = {
  warmup: "Warming-up",
  main: "Hoofdtempo",
  cooldown: "Cooling-down",
  easy: "Rustig",
  threshold: "Drempel",
  interval: "Interval",
  repetition: "Herhaling",
};

export function SessionEditModal({ session, onClose, onSave, isSaving }: Props) {
  const t = useTranslations("workout");

  const [title, setTitle] = useState(session.title);
  const [description, setDescription] = useState(session.description ?? "");
  const [distanceKm, setDistanceKm] = useState(session.distance_km?.toString() ?? "");
  const [durationMin, setDurationMin] = useState(session.duration_minutes?.toString() ?? "");
  const [scheduledDate, setScheduledDate] = useState(session.scheduled_date?.slice(0, 10) ?? "");
  const [paces, setPaces] = useState<Record<string, string>>(
    Object.fromEntries(
      Object.entries(session.target_paces ?? {}).filter(([, v]) => v != null) as [string, string][]
    )
  );
  const [paceErrors, setPaceErrors] = useState<Record<string, string>>({});

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function validatePace(value: string): boolean {
    return value === "" || /^\d+:\d{2}(-\d+:\d{2})?$/.test(value.trim());
  }

  function handlePaceChange(key: string, value: string) {
    setPaces((p) => ({ ...p, [key]: value }));
    setPaceErrors((e) => ({
      ...e,
      [key]: validatePace(value) ? "" : t("edit.paceFormat"),
    }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const hasErrors = Object.values(paceErrors).some(Boolean);
    if (hasErrors) return;

    const data: Parameters<Props["onSave"]>[0] = {};
    if (title.trim()) data.title = title.trim();
    data.description = description.trim();
    const dist = parseFloat(distanceKm);
    if (!isNaN(dist)) data.distance_km = dist;
    else if (distanceKm === "") data.distance_km = null;
    const dur = parseInt(durationMin);
    if (!isNaN(dur)) data.duration_minutes = dur;
    else if (durationMin === "") data.duration_minutes = null;
    if (scheduledDate && scheduledDate !== session.scheduled_date?.slice(0, 10)) {
      data.scheduled_date = scheduledDate;
    }
    const cleanedPaces: Record<string, string> = {};
    for (const [k, v] of Object.entries(paces)) {
      if (v.trim()) cleanedPaces[k] = v.trim();
    }
    if (Object.keys(cleanedPaces).length > 0) data.target_paces = cleanedPaces;

    onSave(data);
  }

  const hasPaces = Object.keys(paces).length > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm px-4 pb-4 sm:pb-0"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-lg bg-surface-card border border-slate-700/60 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/40">
          <h2 className="text-base font-bold text-white">{t("edit.title")}</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-5 py-4 space-y-4 max-h-[70vh] overflow-y-auto">

            {/* Title */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                {t("edit.titleLabel")}
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                className="w-full bg-slate-800/60 border border-slate-700/60 rounded-xl px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500/60 focus:ring-1 focus:ring-brand-500/30"
              />
            </div>

            {/* Date */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                {t("edit.date")}
              </label>
              <input
                type="date"
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
                className="w-full bg-slate-800/60 border border-slate-700/60 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500/60 focus:ring-1 focus:ring-brand-500/30 [color-scheme:dark]"
              />
            </div>

            {/* Distance + Duration */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  {t("edit.distance")}
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={distanceKm}
                    onChange={(e) => setDistanceKm(e.target.value)}
                    className="w-full bg-slate-800/60 border border-slate-700/60 rounded-xl px-3 py-2.5 pr-10 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500/60 focus:ring-1 focus:ring-brand-500/30"
                    placeholder="10.5"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">km</span>
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  {t("edit.duration")}
                </label>
                <div className="relative">
                  <input
                    type="number"
                    min="0"
                    value={durationMin}
                    onChange={(e) => setDurationMin(e.target.value)}
                    className="w-full bg-slate-800/60 border border-slate-700/60 rounded-xl px-3 py-2.5 pr-12 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500/60 focus:ring-1 focus:ring-brand-500/30"
                    placeholder="60"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">min</span>
                </div>
              </div>
            </div>

            {/* Paces */}
            {hasPaces && (
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  {t("edit.paces")}
                </label>
                <div className="space-y-2">
                  {Object.entries(paces).map(([key, value]) => (
                    <div key={key} className="flex items-center gap-3">
                      <span className="w-28 shrink-0 text-xs text-slate-400">
                        {PACE_LABELS[key] ?? key}
                      </span>
                      <div className="flex-1">
                        <div className="relative">
                          <input
                            type="text"
                            value={value}
                            onChange={(e) => handlePaceChange(key, e.target.value)}
                            className={`w-full bg-slate-800/60 border rounded-xl px-3 py-2 pr-14 text-sm font-mono text-white placeholder-slate-500 focus:outline-none focus:ring-1 ${
                              paceErrors[key]
                                ? "border-red-500/60 focus:border-red-500/60 focus:ring-red-500/30"
                                : "border-slate-700/60 focus:border-brand-500/60 focus:ring-brand-500/30"
                            }`}
                            placeholder="5:10-5:20"
                          />
                          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">/km</span>
                        </div>
                        {paceErrors[key] && (
                          <p className="text-xs text-red-400 mt-1">{paceErrors[key]}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Notes */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                {t("edit.notes")}
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full bg-slate-800/60 border border-slate-700/60 rounded-xl px-3 py-2.5 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-brand-500/60 focus:ring-1 focus:ring-brand-500/30"
                placeholder={t("edit.notesPlaceholder")}
              />
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-slate-700/40">
            <button type="button" onClick={onClose} className="btn-ghost text-sm px-4 py-2">
              {t("edit.cancel")}
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="btn-primary text-sm px-4 py-2 gap-2 flex items-center"
            >
              {isSaving
                ? <span className="w-3.5 h-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                : <Save className="w-3.5 h-3.5" />
              }
              {t("edit.save")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
