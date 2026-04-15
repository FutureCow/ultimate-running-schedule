"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, Trash2, Info } from "lucide-react";
import Link from "next/link";
import { plansApi } from "@/lib/api";
import { Plan } from "@/types";
import { WeekCalendar } from "@/components/Calendar/WeekCalendar";
import { PaceZonesCard } from "@/components/Calendar/PaceZonesCard";
import { GOAL_LABELS } from "@/lib/utils";
import { Navbar } from "@/components/ui/Navbar";

export default function PlanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: plan, isLoading } = useQuery<Plan>({
    queryKey: ["plan", id],
    queryFn: () => plansApi.get(Number(id)).then((r) => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: () => plansApi.delete(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      router.push("/dashboard");
    },
  });

  return (
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-6xl mx-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <span className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
          </div>
        ) : !plan ? (
          <div className="text-center py-20 text-slate-400">Plan niet gevonden.</div>
        ) : (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
            {/* Back + title */}
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <Link href="/dashboard" className="btn-ghost px-2 py-2">
                  <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                  <h1 className="text-xl font-bold text-white">{plan.name}</h1>
                  <p className="text-xs text-slate-400">
                    {GOAL_LABELS[plan.goal]} · {plan.duration_weeks} weken
                  </p>
                </div>
              </div>
              <button
                onClick={() => { if (confirm("Plan verwijderen?")) deleteMutation.mutate(); }}
                className="btn-ghost text-red-400 hover:text-red-300 px-3"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            {/* Coaching notes */}
            {plan.plan_json?.plan_overview?.coaching_notes && (
              <div className="flex gap-3 card bg-blue-950/30 border-blue-700/30">
                <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <p className="text-sm text-slate-300 leading-relaxed">
                  {plan.plan_json.plan_overview.coaching_notes}
                </p>
              </div>
            )}

            {/* Two-column layout on large screens */}
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
              <div>
                {plan.plan_json ? (
                  <WeekCalendar plan={plan} />
                ) : (
                  <p className="text-slate-400 text-sm">Plan wordt gegenereerd…</p>
                )}
              </div>

              {/* Sidebar */}
              <div className="space-y-4">
                {plan.plan_json?.plan_overview?.pace_zones && (
                  <PaceZonesCard
                    zones={plan.plan_json.plan_overview.pace_zones}
                    vdot={plan.plan_json.plan_overview.estimated_vdot}
                  />
                )}

                {plan.plan_json?.plan_overview?.weekly_structure && (
                  <div className="card">
                    <h3 className="text-sm font-bold text-white mb-2">Weekstructuur</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      {plan.plan_json.plan_overview.weekly_structure}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}
