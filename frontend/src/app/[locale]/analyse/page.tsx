"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Activity, ChevronRight, Clock, Ruler } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { plansApi } from "@/lib/api";
import { Plan, WorkoutSession } from "@/types";
import { Navbar } from "@/components/ui/Navbar";
import { format, parseISO } from "date-fns";
import { nl, enUS } from "date-fns/locale";
import { useLocale } from "next-intl";
import { cn, WORKOUT_COLORS } from "@/lib/utils";

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface CompletedSession {
  session: WorkoutSession;
  planName: string;
}

export default function AnalysePage() {
  const t = useTranslations("analyse");
  const locale = useLocale();
  const dateFnsLocale = locale === "nl" ? nl : enUS;

  const { data: plans = [], isLoading } = useQuery<Plan[]>({
    queryKey: ["plans"],
    queryFn: () => plansApi.list().then((r) => r.data),
  });

  const completed: CompletedSession[] = plans
    .flatMap((p) =>
      p.sessions
        .filter((s) => s.garmin_activity_id && s.completed_at)
        .map((s) => ({ session: s, planName: p.name }))
    )
    .sort((a, b) => {
      const da = a.session.scheduled_date ?? a.session.completed_at ?? "";
      const db2 = b.session.scheduled_date ?? b.session.completed_at ?? "";
      return db2.localeCompare(da);
    });

  return (
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-3xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
          <div>
            <h1 className="text-xl font-bold text-white">{t("title")}</h1>
            <p className="text-sm text-slate-400 mt-1">{t("subtitle")}</p>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-20">
              <span className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            </div>
          ) : completed.length === 0 ? (
            <div className="card text-center py-12 space-y-3">
              <Activity className="w-10 h-10 text-slate-600 mx-auto" />
              <p className="text-slate-400 text-sm">{t("empty")}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {completed.map(({ session, planName }) => {
                const dateStr = session.scheduled_date
                  ? format(parseISO(session.scheduled_date), "d MMM yyyy", { locale: dateFnsLocale })
                  : null;
                const colorClass = WORKOUT_COLORS[session.workout_type] ?? "";

                return (
                  <motion.div
                    key={session.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                  >
                    <Link
                      href={`/analyse/${session.garmin_activity_id}`}
                      className="flex items-center gap-4 card hover:bg-surface-elevated transition-colors cursor-pointer group"
                    >
                      <div className="w-1.5 self-stretch rounded-full bg-emerald-500 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className={cn("text-[11px] font-semibold px-2 py-0.5 rounded-lg border", colorClass)}>
                            {session.workout_type.replace("_", " ")}
                          </span>
                          {dateStr && (
                            <span className="text-xs text-slate-500">{dateStr}</span>
                          )}
                        </div>
                        <p className="text-sm font-semibold text-white truncate">{session.title}</p>
                        <p className="text-xs text-slate-500 truncate">{planName}</p>
                        <div className="flex items-center gap-3 mt-1.5">
                          {session.distance_km && (
                            <span className="flex items-center gap-1 text-xs text-slate-400">
                              <Ruler className="w-3 h-3" />{session.distance_km} km
                            </span>
                          )}
                          {session.duration_minutes && (
                            <span className="flex items-center gap-1 text-xs text-slate-400">
                              <Clock className="w-3 h-3" />{formatDuration(session.duration_minutes * 60)}
                            </span>
                          )}
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors shrink-0" />
                    </Link>
                  </motion.div>
                );
              })}
            </div>
          )}
        </motion.div>
      </main>
    </div>
  );
}
