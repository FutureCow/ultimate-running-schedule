"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { ChevronLeft, ChevronRight, Zap, Loader2, CheckCircle2 } from "lucide-react";
import { Plan, WorkoutSession } from "@/types";
import { WorkoutCard } from "../WorkoutCard/WorkoutCard";
import { DAY_ABBR, DAYS } from "@/lib/utils";
import { garminApi } from "@/lib/api";
import { format, parseISO } from "date-fns";
import { nl } from "date-fns/locale";

interface Props {
  plan: Plan;
}

export function WeekCalendar({ plan }: Props) {
  const weeks = plan.plan_json?.weeks || [];
  const [currentWeek, setCurrentWeek] = useState(1);
  const [pushingSession, setPushingSession] = useState<number | null>(null);
  const [pushingWeek, setPushingWeek] = useState(false);
  const [weekPushed, setWeekPushed] = useState<Set<number>>(new Set());

  const week = weeks.find((w) => w.week_number === currentWeek);
  const sessions = plan.sessions.filter((s) => s.week_number === currentWeek);
  const totalWeeks = plan.duration_weeks;

  // Map sessions by day_number
  const sessionsByDay: Record<number, WorkoutSession[]> = {};
  for (let d = 1; d <= 7; d++) {
    sessionsByDay[d] = sessions.filter((s) => s.day_number === d);
  }

  async function handlePushSession(sessionId: number) {
    setPushingSession(sessionId);
    try {
      await garminApi.pushSessions([sessionId]);
    } catch (e) {
      console.error("Push session failed:", e);
    } finally {
      setPushingSession(null);
    }
  }

  async function handlePushWeek() {
    setPushingWeek(true);
    try {
      await garminApi.pushWeek(plan.id, currentWeek);
      setWeekPushed((prev) => new Set([...prev, currentWeek]));
    } catch (e) {
      console.error("Push week failed:", e);
    } finally {
      setPushingWeek(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Week navigator */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setCurrentWeek((w) => Math.max(1, w - 1))}
          disabled={currentWeek === 1}
          className="btn-ghost px-3 py-2 disabled:opacity-30"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        <div className="text-center">
          <p className="text-lg font-bold text-white">Week {currentWeek} / {totalWeeks}</p>
          {week && <p className="text-xs text-brand-400 font-medium">{week.theme}</p>}
          {week && (
            <p className="text-xs text-slate-500 mt-0.5">{week.total_km} km totaal</p>
          )}
        </div>

        <button
          onClick={() => setCurrentWeek((w) => Math.min(totalWeeks, w + 1))}
          disabled={currentWeek === totalWeeks}
          className="btn-ghost px-3 py-2 disabled:opacity-30"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Week strip (visual progress) */}
      <div className="flex gap-1">
        {Array.from({ length: totalWeeks }, (_, i) => i + 1).map((w) => (
          <button
            key={w}
            onClick={() => setCurrentWeek(w)}
            className={`flex-1 h-1.5 rounded-full transition-all duration-200 ${
              w === currentWeek ? "bg-brand-500" : w < currentWeek ? "bg-brand-800" : "bg-slate-700"
            }`}
          />
        ))}
      </div>

      {/* Push week button */}
      <div className="flex justify-end">
        {weekPushed.has(currentWeek) ? (
          <span className="flex items-center gap-1.5 text-xs text-brand-400 font-medium">
            <CheckCircle2 className="w-4 h-4" /> Week {currentWeek} op Garmin
          </span>
        ) : (
          <button
            onClick={handlePushWeek}
            disabled={pushingWeek}
            className="btn-secondary text-xs gap-1.5 px-3 py-1.5"
          >
            {pushingWeek
              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
              : <Zap className="w-3.5 h-3.5 text-brand-400" />
            }
            Push week naar Garmin
          </button>
        )}
      </div>

      {/* 7-day grid */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentWeek}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.25 }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-3"
        >
          {DAYS.map((day, idx) => {
            const dayNum = idx + 1;
            const daySessions = sessionsByDay[dayNum] || [];
            const sessionFromPlan = sessions.find((s) => s.day_number === dayNum);
            const dateStr = sessionFromPlan?.scheduled_date
              ? format(parseISO(sessionFromPlan.scheduled_date), "d MMM", { locale: nl })
              : null;

            return (
              <div key={day} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    {DAY_ABBR[idx]}
                  </span>
                  {dateStr && <span className="text-[10px] text-slate-600">{dateStr}</span>}
                </div>

                {daySessions.length > 0 ? (
                  daySessions.map((s) => (
                    <WorkoutCard
                      key={s.id}
                      session={s}
                      onPushToGarmin={handlePushSession}
                      isPushing={pushingSession === s.id}
                    />
                  ))
                ) : (
                  <div className="h-12 rounded-xl border border-dashed border-slate-700/50 flex items-center justify-center">
                    <span className="text-[10px] text-slate-700">—</span>
                  </div>
                )}
              </div>
            );
          })}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
