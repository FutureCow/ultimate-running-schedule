"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { ChevronLeft, ChevronRight, Zap, Loader2, CheckCircle2 } from "lucide-react";
import { Plan, WorkoutSession } from "@/types";
import { WorkoutCard } from "../WorkoutCard/WorkoutCard";
import { DAYS, DAY_ABBR } from "@/lib/utils";
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
      await garminApi.pushWeek(plan.id, currentWeek);
      setWeekPushed((prev) => new Set([...prev, currentWeek]));
    } catch (e) { console.error(e); }
    finally { setPushingWeek(false); }
  }

  return (
    <div className="space-y-4">

      {/* ── Week navigator ──────────────────────────────────── */}
      <div className="flex items-center justify-between gap-4">
        <button
          onClick={() => setCurrentWeek((w) => Math.max(1, w - 1))}
          disabled={currentWeek === 1}
          className="btn-ghost px-3 py-2 disabled:opacity-30"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        <div className="text-center">
          <p className="text-lg font-bold text-white">Week {currentWeek} <span className="text-slate-500 font-normal">/ {totalWeeks}</span></p>
          {week && <p className="text-xs text-brand-400 font-medium">{week.theme}</p>}
          {week && <p className="text-xs text-slate-500">{week.total_km} km totaal</p>}
        </div>

        <button
          onClick={() => setCurrentWeek((w) => Math.min(totalWeeks, w + 1))}
          disabled={currentWeek === totalWeeks}
          className="btn-ghost px-3 py-2 disabled:opacity-30"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* ── Week progress strip ─────────────────────────────── */}
      <div className="flex gap-1">
        {Array.from({ length: totalWeeks }, (_, i) => i + 1).map((w) => (
          <button
            key={w}
            onClick={() => setCurrentWeek(w)}
            title={`Week ${w}`}
            className={`flex-1 h-1.5 rounded-full transition-all duration-200 ${
              w === currentWeek ? "bg-brand-500" : w < currentWeek ? "bg-brand-800" : "bg-slate-700"
            }`}
          />
        ))}
      </div>

      {/* ── Push week button ────────────────────────────────── */}
      <div className="flex justify-end">
        {weekPushed.has(currentWeek) ? (
          <span className="flex items-center gap-1.5 text-xs text-brand-400 font-medium">
            <CheckCircle2 className="w-4 h-4" /> Week {currentWeek} op Garmin
          </span>
        ) : (
          <button onClick={handlePushWeek} disabled={pushingWeek} className="btn-secondary text-xs gap-1.5 px-3 py-1.5">
            {pushingWeek ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5 text-brand-400" />}
            Push week naar Garmin
          </button>
        )}
      </div>

      {/* ── Day list ────────────────────────────────────────── */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentWeek}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.2 }}
          className="space-y-2"
        >
          {DAYS.map((day, idx) => {
            const dayNum = idx + 1;
            const daySessions = sessionsByDay[dayNum] || [];
            const firstSession = daySessions[0];
            const dateStr = firstSession?.scheduled_date
              ? format(parseISO(firstSession.scheduled_date), "d MMM", { locale: nl })
              : null;

            return (
              <div key={day} className="flex gap-3 items-start">
                {/* Day label — fixed width */}
                <div className="w-14 shrink-0 pt-3 text-right">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{DAY_ABBR[idx]}</p>
                  {dateStr && <p className="text-[10px] text-slate-600 mt-0.5">{dateStr}</p>}
                </div>

                {/* Workout card(s) */}
                <div className="flex-1 space-y-2 min-w-0">
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
                    <div className="flex items-center rounded-2xl border border-dashed border-slate-700/30 px-4 py-3">
                      <span className="text-xs text-slate-700">Rustdag</span>
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
