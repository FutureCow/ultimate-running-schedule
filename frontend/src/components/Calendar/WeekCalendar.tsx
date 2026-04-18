"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, Zap, Loader2, CheckCircle2 } from "lucide-react";
import { Plan, WorkoutSession } from "@/types";
import { WorkoutCard } from "../WorkoutCard/WorkoutCard";
import { garminApi, sessionsApi } from "@/lib/api";
import { format, parseISO } from "date-fns";
import { nl, enUS } from "date-fns/locale";
import { useLocale } from "next-intl";
import { useMutation, useQueryClient } from "@tanstack/react-query";

interface Props {
  plan: Plan;
}

export function WeekCalendar({ plan }: Props) {
  const t = useTranslations("calendar");
  const locale = useLocale();
  const dateFnsLocale = locale === "nl" ? nl : enUS;
  const tDays = useTranslations("days");

  const weeks = plan.plan_json?.weeks || [];
  const [currentWeek, setCurrentWeek] = useState(1);
  const [pushingSession, setPushingSession] = useState<number | null>(null);
  const [pushingWeek, setPushingWeek] = useState(false);
  const [weekPushed, setWeekPushed] = useState<Set<number>>(new Set());
  const queryClient = useQueryClient();

  const moveMutation = useMutation({
    mutationFn: ({ sessionId, dayNumber }: { sessionId: number; dayNumber: number }) =>
      sessionsApi.move(sessionId, dayNumber),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["plan", plan.public_id] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (sessionId: number) => sessionsApi.delete(sessionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["plan", plan.public_id] }),
  });

  const removeFromGarminMutation = useMutation({
    mutationFn: (sessionId: number) => garminApi.removeSession(sessionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["plan", plan.public_id] }),
  });

  const week = weeks.find((w) => w.week_number === currentWeek);
  const sessions = plan.sessions.filter((s) => s.week_number === currentWeek);
  const totalWeeks = plan.duration_weeks;

  const sessionsByDay: Record<number, WorkoutSession[]> = {};
  for (let d = 1; d <= 7; d++) {
    sessionsByDay[d] = sessions.filter((s) => s.day_number === d);
  }

  async function handlePushSession(sessionId: number) {
    setPushingSession(sessionId);
    try { await garminApi.pushSessions([sessionId]); }
    catch (e) { console.error(e); }
    finally { setPushingSession(null); }
  }

  async function handlePushWeek() {
    setPushingWeek(true);
    try {
      await garminApi.pushWeek(plan.public_id, currentWeek);
      setWeekPushed((prev) => new Set(Array.from(prev).concat(currentWeek)));
    } catch (e) { console.error(e); }
    finally { setPushingWeek(false); }
  }

  const tWorkout = useTranslations("workout");

  return (
    <div className="space-y-4">
      {/* Week navigator */}
      <div className="flex items-center justify-between gap-4">
        <button
          onClick={() => setCurrentWeek((w) => Math.max(1, w - 1))}
          disabled={currentWeek === 1}
          className="btn-ghost px-3 py-2 disabled:opacity-30"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        <div className="text-center">
          <p className="text-lg font-bold text-white">
            {t("weekTitle", { current: currentWeek, total: totalWeeks })}
          </p>
          {week && <p className="text-xs text-brand-400 font-medium">{week.theme}</p>}
          {week && <p className="text-xs text-slate-500">{week.total_km} km</p>}
        </div>

        <button
          onClick={() => setCurrentWeek((w) => Math.min(totalWeeks, w + 1))}
          disabled={currentWeek === totalWeeks}
          className="btn-ghost px-3 py-2 disabled:opacity-30"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Week progress strip */}
      <div className="flex gap-1">
        {Array.from({ length: totalWeeks }, (_, i) => i + 1).map((w) => (
          <button
            key={w}
            onClick={() => setCurrentWeek(w)}
            title={`Week ${w}`}
            className={`flex-1 h-1.5 rounded-full transition-all duration-200 ${
              w === currentWeek ? "bg-brand-500" : w < currentWeek ? "bg-brand-500/30" : "bg-slate-400/30"
            }`}
          />
        ))}
      </div>

      {/* Push week button */}
      <div className="flex justify-end">
        {weekPushed.has(currentWeek) ? (
          <span className="flex items-center gap-1.5 text-xs text-brand-400 font-medium">
            <CheckCircle2 className="w-4 h-4" /> {t("weekOnGarmin", { week: currentWeek })}
          </span>
        ) : (
          <button onClick={handlePushWeek} disabled={pushingWeek} className="btn-secondary text-xs gap-1.5 px-3 py-1.5">
            {pushingWeek ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5 text-brand-400" />}
            {t("pushWeek")}
          </button>
        )}
      </div>

      {/* Day list */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentWeek}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.2 }}
          className="space-y-2"
        >
          {Array.from({ length: 7 }, (_, idx) => {
            const dayNum = idx + 1;
            const dayLabel = tDays(`abbr.${idx}`);
            const daySessions = sessionsByDay[dayNum] || [];
            const firstSession = daySessions[0];
            const dateStr = firstSession?.scheduled_date
              ? format(parseISO(firstSession.scheduled_date), "d MMM", { locale: dateFnsLocale })
              : null;

            return (
              <div key={idx} className="flex gap-3 items-start">
                <div className="w-14 shrink-0 pt-3 text-right">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{dayLabel}</p>
                  {dateStr && <p className="text-[10px] text-slate-600 mt-0.5">{dateStr}</p>}
                </div>

                <div className="flex-1 space-y-2 min-w-0">
                  {daySessions.length > 0 ? (
                    daySessions.map((s) => (
                      <WorkoutCard
                        key={s.id}
                        session={s}
                        onPushToGarmin={handlePushSession}
                        isPushing={pushingSession === s.id}
                        onMove={(sessionId, dayNumber) => moveMutation.mutate({ sessionId, dayNumber })}
                        isMoving={moveMutation.isPending && moveMutation.variables?.sessionId === s.id}
                        onDelete={(sessionId) => {
                          if (confirm(tWorkout("deleteConfirm"))) deleteMutation.mutate(sessionId);
                        }}
                        isDeleting={deleteMutation.isPending && deleteMutation.variables === s.id}
                        onRemoveFromGarmin={(sessionId) => {
                          if (confirm(tWorkout("removeFromGarminConfirm"))) removeFromGarminMutation.mutate(sessionId);
                        }}
                        isRemovingFromGarmin={removeFromGarminMutation.isPending && removeFromGarminMutation.variables === s.id}
                      />
                    ))
                  ) : (
                    <div className="flex items-center rounded-2xl border border-dashed border-slate-700/30 px-4 py-3">
                      <span className="text-xs text-slate-700">{t("restDay")}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
