"use client";

import { motion } from "framer-motion";
import { Clock, Ruler, Watch, ChevronDown, ChevronUp, Zap } from "lucide-react";
import { useState } from "react";
import { WorkoutSession } from "@/types";
import { cn, WORKOUT_COLORS, WORKOUT_LABELS } from "@/lib/utils";

interface Props {
  session: WorkoutSession;
  onPushToGarmin?: (sessionId: number) => void;
  isPushing?: boolean;
}

export function WorkoutCard({ session, onPushToGarmin, isPushing }: Props) {
  const [expanded, setExpanded] = useState(false);
  const colorClass = WORKOUT_COLORS[session.workout_type];

  if (session.workout_type === "rest") {
    return (
      <div className={cn("rounded-xl border px-3 py-2.5 text-xs font-medium", colorClass)}>
        🛌 Rustdag
      </div>
    );
  }

  return (
    <motion.div
      layout
      className={cn("rounded-xl border p-3 transition-all duration-200 cursor-pointer", colorClass)}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={cn("pace-badge text-[10px]", colorClass)}>
              {WORKOUT_LABELS[session.workout_type]}
            </span>
          </div>
          <p className="text-sm font-semibold text-white truncate">{session.title}</p>
        </div>
        <button className="text-current opacity-60 shrink-0">
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Quick stats */}
      <div className="flex items-center gap-3 mt-2 text-[11px] opacity-80">
        {session.distance_km && (
          <span className="flex items-center gap-1">
            <Ruler className="w-3 h-3" /> {session.distance_km} km
          </span>
        )}
        {session.duration_minutes && (
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" /> {session.duration_minutes} min
          </span>
        )}
        {session.target_paces?.main && (
          <span className="flex items-center gap-1 font-mono">
            <Watch className="w-3 h-3" /> {session.target_paces.main}
          </span>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-3 pt-3 border-t border-current/20 space-y-2"
          onClick={(e) => e.stopPropagation()}
        >
          {session.description && (
            <p className="text-xs opacity-80 leading-relaxed">{session.description}</p>
          )}

          {/* Pace zones */}
          {session.target_paces && (
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider opacity-60">Tempo's</p>
              {session.target_paces.warmup && (
                <PaceRow label="Warming-up" pace={session.target_paces.warmup} />
              )}
              <PaceRow label="Hoofddeel" pace={session.target_paces.main} highlight />
              {session.target_paces.cooldown && (
                <PaceRow label="Cooling-down" pace={session.target_paces.cooldown} />
              )}
            </div>
          )}

          {/* Intervals */}
          {session.intervals && session.intervals.length > 0 && (
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider opacity-60">Intervalstructuur</p>
              {session.intervals.map((iv, i) => (
                <div key={i} className="bg-black/20 rounded-lg px-2.5 py-1.5 text-xs">
                  <span className="font-semibold">{iv.reps}×</span>{" "}
                  {iv.distance_m ? `${iv.distance_m}m` : iv.duration_seconds ? `${iv.duration_seconds}s` : ""}{" "}
                  @ <span className="font-mono font-medium">{iv.pace}</span>/km
                  <span className="opacity-60"> · {iv.rest_seconds}s rust</span>
                </div>
              ))}
            </div>
          )}

          {/* Garmin push */}
          {onPushToGarmin && !session.garmin_workout_id && (
            <button
              onClick={() => onPushToGarmin(session.id)}
              disabled={isPushing}
              className="flex items-center gap-1.5 mt-1 text-xs font-semibold bg-black/30 hover:bg-black/50 rounded-lg px-2.5 py-1.5 transition-colors disabled:opacity-50"
            >
              {isPushing
                ? <span className="w-3 h-3 rounded-full border border-current border-t-transparent animate-spin" />
                : <Zap className="w-3 h-3" />
              }
              Push naar Garmin
            </button>
          )}
          {session.garmin_pushed_at && (
            <p className="text-[10px] opacity-50 flex items-center gap-1">
              <Zap className="w-3 h-3" /> Op Garmin gezet
            </p>
          )}
        </motion.div>
      )}
    </motion.div>
  );
}

function PaceRow({ label, pace, highlight }: { label: string; pace: string; highlight?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[11px] opacity-70">{label}</span>
      <span className={cn("font-mono text-[11px] font-semibold", highlight ? "text-white" : "opacity-80")}>
        {pace} /km
      </span>
    </div>
  );
}
