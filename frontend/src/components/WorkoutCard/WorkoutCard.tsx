"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Clock, Ruler, Watch, ChevronDown, ChevronUp, Zap, CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { WorkoutSession } from "@/types";
import { cn, WORKOUT_COLORS, WORKOUT_LABELS } from "@/lib/utils";

interface Props {
  session: WorkoutSession;
  onPushToGarmin?: (sessionId: number) => void;
  isPushing?: boolean;
}

const ACCENT_COLORS: Record<string, string> = {
  easy_run:  "bg-emerald-500",
  long_run:  "bg-blue-500",
  tempo:     "bg-orange-500",
  interval:  "bg-red-500",
  recovery:  "bg-teal-500",
  race:      "bg-yellow-500",
  rest:      "bg-slate-600",
};

export function WorkoutCard({ session, onPushToGarmin, isPushing }: Props) {
  const [expanded, setExpanded] = useState(false);
  const colorClass = WORKOUT_COLORS[session.workout_type];
  const accentColor = ACCENT_COLORS[session.workout_type] ?? "bg-slate-600";

  if (session.workout_type === "rest") {
    return (
      <div className="flex items-center gap-4 rounded-2xl border border-slate-700/40 bg-surface-card px-4 py-3">
        <div className={cn("w-1 self-stretch rounded-full shrink-0", accentColor)} />
        <span className="text-sm text-slate-600 font-medium">Rustdag</span>
      </div>
    );
  }

  return (
    <motion.div layout className="rounded-2xl border border-slate-700/40 bg-surface-card overflow-hidden">
      {/* Main row — always visible */}
      <div
        className="flex items-stretch gap-0 cursor-pointer hover:bg-surface-elevated transition-colors duration-150"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Colored left accent */}
        <div className={cn("w-1.5 shrink-0", accentColor)} />

        <div className="flex flex-1 items-center gap-4 px-4 py-3 min-w-0">
          {/* Type badge */}
          <span className={cn(
            "shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-lg border whitespace-nowrap",
            colorClass
          )}>
            {WORKOUT_LABELS[session.workout_type]}
          </span>

          {/* Title + description */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white leading-tight">{session.title}</p>
            {session.description && (
              <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{session.description}</p>
            )}
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-3 shrink-0">
            {session.distance_km && (
              <Stat icon={<Ruler className="w-3.5 h-3.5" />} value={`${session.distance_km} km`} />
            )}
            {session.duration_minutes && (
              <Stat icon={<Clock className="w-3.5 h-3.5" />} value={`${session.duration_minutes} min`} />
            )}
            {session.target_paces?.main && (
              <Stat
                icon={<Watch className="w-3.5 h-3.5" />}
                value={session.target_paces.main}
                mono
                highlight
              />
            )}
            <button className="text-slate-600 hover:text-slate-400 ml-1">
              {expanded
                ? <ChevronUp className="w-4 h-4" />
                : <ChevronDown className="w-4 h-4" />
              }
            </button>
          </div>
        </div>
      </div>

      {/* Expanded detail */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="detail"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-4 pt-1 space-y-3 border-t border-slate-700/40 ml-1.5">

              {/* Description full */}
              {session.description && (
                <p className="text-sm text-slate-300 leading-relaxed">{session.description}</p>
              )}

              {/* Pace zones */}
              {session.target_paces && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {session.target_paces.warmup && (
                    <PaceBlock label="Warming-up" pace={session.target_paces.warmup} />
                  )}
                  <PaceBlock label="Hoofdtempo" pace={session.target_paces.main} highlight />
                  {session.target_paces.cooldown && (
                    <PaceBlock label="Cooling-down" pace={session.target_paces.cooldown} />
                  )}
                </div>
              )}

              {/* Interval structure */}
              {session.intervals && session.intervals.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Intervalstructuur
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {session.intervals.map((iv, i) => (
                      <div key={i} className="flex items-center gap-1.5 bg-surface-elevated rounded-xl px-3 py-2 text-sm">
                        <span className="font-bold text-white">{iv.reps}×</span>
                        <span className="text-slate-300">
                          {iv.distance_m ? `${iv.distance_m}m` : iv.duration_seconds ? `${iv.duration_seconds}s` : ""}
                        </span>
                        <span className="text-slate-500">@</span>
                        <span className="font-mono font-semibold text-orange-300">{iv.pace}/km</span>
                        <span className="text-slate-600 text-xs">· {iv.rest_seconds}s rust</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Garmin push */}
              <div className="flex items-center gap-3">
                {onPushToGarmin && !session.garmin_workout_id && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onPushToGarmin(session.id); }}
                    disabled={isPushing}
                    className="btn-secondary text-xs px-3 py-1.5 gap-1.5"
                  >
                    {isPushing
                      ? <span className="w-3 h-3 rounded-full border border-current border-t-transparent animate-spin" />
                      : <Zap className="w-3.5 h-3.5 text-brand-400" />
                    }
                    Push naar Garmin
                  </button>
                )}
                {session.garmin_pushed_at && (
                  <span className="flex items-center gap-1.5 text-xs text-brand-400 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Op Garmin
                  </span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function Stat({ icon, value, mono, highlight }: {
  icon: React.ReactNode;
  value: string;
  mono?: boolean;
  highlight?: boolean;
}) {
  return (
    <span className={cn(
      "flex items-center gap-1 text-xs",
      highlight ? "text-white font-semibold" : "text-slate-400",
      mono && "font-mono"
    )}>
      <span className="text-slate-500">{icon}</span>
      {value}
    </span>
  );
}

function PaceBlock({ label, pace, highlight }: { label: string; pace: string; highlight?: boolean }) {
  return (
    <div className={cn(
      "rounded-xl border px-3 py-2.5",
      highlight
        ? "border-brand-500/30 bg-brand-500/10"
        : "border-slate-700/50 bg-surface-elevated"
    )}>
      <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider mb-1">{label}</p>
      <p className={cn("font-mono text-sm font-bold", highlight ? "text-white" : "text-slate-300")}>
        {pace} <span className="text-xs font-normal text-slate-500">/km</span>
      </p>
    </div>
  );
}
