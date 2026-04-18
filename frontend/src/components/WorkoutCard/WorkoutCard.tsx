"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useTranslations } from "next-intl";
import { Clock, Ruler, Watch, ChevronDown, ChevronUp, Zap, CheckCircle2, ArrowLeftRight, Trash2, X, Dumbbell } from "lucide-react";
import { useState } from "react";
import { WorkoutSession } from "@/types";
import { cn, WORKOUT_COLORS } from "@/lib/utils";

interface Props {
  session: WorkoutSession;
  onPushToGarmin?: (sessionId: number) => void;
  isPushing?: boolean;
  onMove?: (sessionId: number, dayNumber: number) => void;
  isMoving?: boolean;
  onDelete?: (sessionId: number) => void;
  isDeleting?: boolean;
  onRemoveFromGarmin?: (sessionId: number) => void;
  isRemovingFromGarmin?: boolean;
}

const ACCENT_COLORS: Record<string, string> = {
  easy_run:  "bg-emerald-500",
  long_run:  "bg-blue-500",
  tempo:     "bg-orange-500",
  interval:  "bg-red-500",
  recovery:  "bg-teal-500",
  race:      "bg-yellow-500",
  rest:      "bg-slate-600",
  strength:  "bg-violet-500",
};

export function WorkoutCard({ session, onPushToGarmin, isPushing, onMove, isMoving, onDelete, isDeleting, onRemoveFromGarmin, isRemovingFromGarmin }: Props) {
  const t = useTranslations("workout");
  const tDays = useTranslations("days");

  const [expanded, setExpanded] = useState(false);
  const [showMovePicker, setShowMovePicker] = useState(false);

  const colorClass = WORKOUT_COLORS[session.workout_type];
  const accentColor = ACCENT_COLORS[session.workout_type] ?? "bg-slate-600";

  const dayAbbr = Array.from({ length: 7 }, (_, i) => tDays(`abbr.${i}`));

  if (session.workout_type === "rest") {
    return (
      <div className="flex items-center gap-4 rounded-2xl border border-slate-700/40 bg-surface-card px-4 py-3">
        <div className={cn("w-1 self-stretch rounded-full shrink-0", accentColor)} />
        <span className="text-sm text-slate-600 font-medium">{t("rest")}</span>
      </div>
    );
  }

  return (
    <motion.div layout className="rounded-2xl border border-slate-700/40 bg-surface-card overflow-hidden">
      {/* Main row */}
      <div
        className="flex items-stretch gap-0 cursor-pointer hover:bg-surface-elevated transition-colors duration-150"
        onClick={() => setExpanded(!expanded)}
      >
        <div className={cn("w-1.5 shrink-0", accentColor)} />

        <div className="flex flex-1 items-center gap-4 px-4 py-3 min-w-0">
          <span className={cn(
            "shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-lg border whitespace-nowrap",
            colorClass
          )}>
            {t(`types.${session.workout_type}`)}
          </span>

          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white leading-tight">{session.title}</p>
            {session.description && (
              <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{session.description}</p>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <div className="flex flex-col sm:flex-row items-end sm:items-center gap-1 sm:gap-3">
              {session.workout_type === "strength" ? (
                <>
                  <Stat icon={<Dumbbell className="w-3.5 h-3.5" />} value={t("types.strength")} />
                  {session.duration_minutes && (
                    <Stat icon={<Clock className="w-3.5 h-3.5" />} value={`${session.duration_minutes} min`} />
                  )}
                </>
              ) : (
                <>
                  {session.distance_km && (
                    <Stat icon={<Ruler className="w-3.5 h-3.5" />} value={`${session.distance_km} km`} />
                  )}
                  {session.duration_minutes && (
                    <Stat icon={<Clock className="w-3.5 h-3.5" />} value={`${session.duration_minutes} min`} />
                  )}
                  {session.target_paces?.main && session.target_paces.main !== "N/A" && (
                    <Stat icon={<Watch className="w-3.5 h-3.5" />} value={session.target_paces.main} mono highlight />
                  )}
                </>
              )}
            </div>
            <button className="text-slate-600 hover:text-slate-400">
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
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

              {session.workout_type === "strength" ? (
                session.description && (
                  <div className="space-y-1.5">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                      {t("exercises")}
                    </p>
                    <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
                      {session.description}
                    </div>
                  </div>
                )
              ) : (
                <>
                  {session.description && (
                    <p className="text-sm text-slate-300 leading-relaxed">{session.description}</p>
                  )}
                </>
              )}

              {session.workout_type !== "strength" && session.target_paces && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {session.target_paces.warmup && (
                    <PaceBlock label={t("warmup")} pace={session.target_paces.warmup} />
                  )}
                  <PaceBlock label={t("mainPace")} pace={session.target_paces.main} highlight />
                  {session.target_paces.cooldown && (
                    <PaceBlock label={t("cooldown")} pace={session.target_paces.cooldown} />
                  )}
                </div>
              )}

              {session.intervals && session.intervals.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    {t("intervals")}
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
                        <span className="text-slate-600 text-xs">· {t("restSeconds", { seconds: iv.rest_seconds })}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions row */}
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
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
                      {t("pushToGarmin")}
                    </button>
                  )}
                  {session.garmin_pushed_at && (
                    <span className="flex items-center gap-1.5 text-xs text-brand-400 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" /> {t("onGarmin")}
                      {onRemoveFromGarmin && (
                        <button
                          onClick={(e) => { e.stopPropagation(); onRemoveFromGarmin(session.id); }}
                          disabled={isRemovingFromGarmin}
                          title={t("removeFromGarmin")}
                          className="ml-0.5 text-slate-500 hover:text-red-400 transition-colors"
                        >
                          {isRemovingFromGarmin
                            ? <span className="w-3 h-3 rounded-full border border-current border-t-transparent animate-spin inline-block" />
                            : <X className="w-3.5 h-3.5" />
                          }
                        </button>
                      )}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {onMove && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setShowMovePicker((v) => !v); }}
                      disabled={isMoving}
                      className="btn-ghost text-xs px-2.5 py-1.5 gap-1.5 text-slate-400 hover:text-white"
                    >
                      {isMoving
                        ? <span className="w-3 h-3 rounded-full border border-current border-t-transparent animate-spin" />
                        : <ArrowLeftRight className="w-3.5 h-3.5" />
                      }
                      {t("move")}
                    </button>
                  )}
                  {onDelete && (
                    <button
                      onClick={(e) => { e.stopPropagation(); onDelete(session.id); }}
                      disabled={isDeleting}
                      className="btn-ghost text-xs px-2.5 py-1.5 gap-1.5 text-red-500 hover:text-red-400"
                    >
                      {isDeleting
                        ? <span className="w-3 h-3 rounded-full border border-current border-t-transparent animate-spin" />
                        : <Trash2 className="w-3.5 h-3.5" />
                      }
                      {t("delete")}
                    </button>
                  )}
                </div>
              </div>

              {/* Day picker */}
              <AnimatePresence>
                {showMovePicker && onMove && (
                  <motion.div
                    key="day-picker"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.15 }}
                    className="overflow-hidden"
                  >
                    <div className="pt-2">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
                        {t("moveToDayLabel")}
                      </p>
                      <div className="flex gap-1.5">
                        {dayAbbr.map((label, idx) => {
                          const dayNum = idx + 1;
                          const isCurrent = session.day_number === dayNum;
                          return (
                            <button
                              key={dayNum}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (!isCurrent) {
                                  onMove(session.id, dayNum);
                                  setShowMovePicker(false);
                                }
                              }}
                              disabled={isCurrent}
                              className={cn(
                                "flex-1 rounded-lg py-1.5 text-xs font-semibold transition-colors",
                                isCurrent
                                  ? "bg-brand-500/20 text-brand-400 cursor-default"
                                  : "bg-surface-elevated text-slate-400 hover:bg-slate-700 hover:text-white"
                              )}
                            >
                              {label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function Stat({ icon, value, mono, highlight }: {
  icon: React.ReactNode; value: string; mono?: boolean; highlight?: boolean;
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
      highlight ? "border-brand-500/30 bg-brand-500/10" : "border-slate-700/50 bg-surface-elevated"
    )}>
      <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider mb-1">{label}</p>
      <p className={cn("font-mono text-sm font-bold", highlight ? "text-white" : "text-slate-300")}>
        {pace} <span className="text-xs font-normal text-slate-500">/km</span>
      </p>
    </div>
  );
}
