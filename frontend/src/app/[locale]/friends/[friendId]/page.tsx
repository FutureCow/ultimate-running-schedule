"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { ArrowLeft, Activity, ChevronRight, Clock, Ruler } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { friendsApi } from "@/lib/api";
import { Navbar } from "@/components/ui/Navbar";
import { format, parseISO } from "date-fns";
import { nl, enUS } from "date-fns/locale";
import { useLocale } from "next-intl";

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
}


export default function FriendActivitiesPage() {
  const t = useTranslations("friends");
  const at = useTranslations("analyse");
  const params = useParams();
  const friendId = Number(params.friendId);
  const locale = useLocale();
  const dateFnsLocale = locale === "nl" ? nl : enUS;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["friend-activities", friendId],
    queryFn: () => friendsApi.getActivities(friendId).then((r) => r.data),
    enabled: !isNaN(friendId),
  });

  const activities: any[] = Array.isArray(data) ? data : (data?.activities ?? []);

  return (
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-3xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">

          <div className="flex items-center gap-3">
            <Link href="/friends" className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-surface-elevated transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white">{t("activities")}</h1>
            </div>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-20">
              <span className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            </div>
          ) : isError ? (
            <div className="card text-center py-10">
              <p className="text-sm text-red-400">{t("errorActivities")}</p>
            </div>
          ) : activities.length === 0 ? (
            <div className="card text-center py-12 space-y-3">
              <Activity className="w-10 h-10 text-slate-600 mx-auto" />
              <p className="text-slate-400 text-sm">{t("noActivities")}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {activities.map((act: any) => {
                const dateStr = act.start_time
                  ? format(parseISO(act.start_time), "d MMM yyyy", { locale: dateFnsLocale })
                  : null;
                return (
                  <motion.div key={act.activity_id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}>
                    <Link
                      href={`/friends/${friendId}/${act.activity_id}`}
                      className="flex items-center gap-4 card hover:bg-surface-elevated transition-colors cursor-pointer group"
                    >
                      <div className="w-1.5 self-stretch rounded-full bg-brand-500 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-lg border border-brand-500/30 text-brand-300 bg-brand-500/10">
                            {act.activity_type ?? "run"}
                          </span>
                          {dateStr && <span className="text-xs text-slate-500">{dateStr}</span>}
                        </div>
                        <p className="text-sm font-semibold text-white truncate">{act.activity_name || act.name || act.activity_id}</p>
                        <div className="flex items-center gap-3 mt-1.5">
                          {act.distance_km != null && (
                            <span className="flex items-center gap-1 text-xs text-slate-400">
                              <Ruler className="w-3 h-3" />{Number(act.distance_km).toFixed(2)} km
                            </span>
                          )}
                          {act.duration_seconds != null && (
                            <span className="flex items-center gap-1 text-xs text-slate-400">
                              <Clock className="w-3 h-3" />{formatDuration(act.duration_seconds)}
                            </span>
                          )}
                          {act.average_pace_per_km && (
                            <span className="text-xs text-slate-400">{act.average_pace_per_km} /km</span>
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
