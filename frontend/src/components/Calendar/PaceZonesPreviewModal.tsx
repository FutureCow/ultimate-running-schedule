"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, ArrowRight, Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface PaceZonesPreview {
  current_zones: Record<string, string>;
  new_zones: Record<string, string>;
  notes?: string;
  sessions_to_update: number;
  based_on_runs: number;
}

interface Props {
  preview: PaceZonesPreview;
  onApply: () => void;
  onClose: () => void;
  applying: boolean;
}

const ZONES = [
  { key: "easy",       label: "Rustig",    color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
  { key: "marathon",   label: "Marathon",  color: "text-blue-400",    bg: "bg-blue-500/10 border-blue-500/20" },
  { key: "threshold",  label: "Drempel",   color: "text-orange-400",  bg: "bg-orange-500/10 border-orange-500/20" },
  { key: "interval",   label: "Interval",  color: "text-red-400",     bg: "bg-red-500/10 border-red-500/20" },
  { key: "repetition", label: "Herhaling", color: "text-purple-400",  bg: "bg-purple-500/10 border-purple-500/20" },
];

export function PaceZonesPreviewModal({ preview, onApply, onClose, applying }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 12 }}
        className="relative w-full max-w-md bg-surface-card border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/40">
          <div>
            <h2 className="font-bold text-white">Tempo zones bijstellen</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Gebaseerd op {preview.based_on_runs} recente activiteiten · {preview.sessions_to_update} trainingen worden bijgewerkt
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-700/50 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-2 max-h-[60vh] overflow-y-auto">
          {preview.notes && (
            <div className="flex gap-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 px-3 py-2.5 mb-3">
              <Info className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
              <p className="text-xs text-slate-300 leading-relaxed">{preview.notes}</p>
            </div>
          )}

          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-1 px-1 pb-1">
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Huidig</p>
            <span />
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider text-right">Nieuw</p>
          </div>

          {ZONES.map(({ key, label, color, bg }) => {
            const current = preview.current_zones[key];
            const next = preview.new_zones[key];
            if (!next) return null;
            const changed = current !== next;
            return (
              <div key={key} className={cn("rounded-xl border px-3 py-2.5", bg)}>
                <p className="text-[10px] font-medium text-slate-500 mb-1.5">{label}</p>
                <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
                  <span className={cn("font-mono text-sm", changed ? "text-slate-500 line-through" : color)}>
                    {current ?? "–"}
                  </span>
                  <ArrowRight className={cn("w-3.5 h-3.5 shrink-0", changed ? "text-slate-400" : "text-slate-600")} />
                  <span className={cn("font-mono text-sm font-bold text-right", color)}>
                    {next}
                    {changed && <span className="ml-1.5 text-[10px] font-normal text-slate-500">nieuw</span>}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="px-5 py-4 border-t border-slate-700/40 flex gap-3">
          <button onClick={onClose} className="btn-secondary flex-1">
            Annuleren
          </button>
          <button onClick={onApply} disabled={applying} className="btn-primary flex-1">
            {applying
              ? <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              : null}
            Toepassen
          </button>
        </div>
      </motion.div>
    </div>
  );
}
