"use client";

import { useLocale, useTranslations } from "next-intl";
import { Sparkles } from "lucide-react";
import { WeeklyReview } from "@/types";
import { formatDistance } from "@/lib/goal";

/**
 * The weekly look back at a plan under way: volume planned against run per
 * week, the key numbers, and for Elite the narrative written from them.
 */
export function WeeklyReviewCard({ review }: { review: WeeklyReview }) {
  const t = useTranslations("plans.review");
  const locale = useLocale();
  const km = (value: number) => formatDistance(value, locale);
  const { stats } = review;
  const peak = Math.max(1, ...stats.weeks.flatMap((w) => [w.planned_km, w.run_km]));
  const eff = stats.aerobic_efficiency;

  const facts = [
    t("weeksToGo", { weeks: stats.weeks_to_go }),
    stats.longest_run_km ? t("longest", { km: km(stats.longest_run_km) }) : null,
    stats.longest_ahead_km ? t("longestAhead", { km: km(stats.longest_ahead_km) }) : null,
    eff ? t(eff.change_pct >= 0 ? "efficiencyUp" : "efficiencyDown",
            { pct: Math.abs(eff.change_pct).toLocaleString(locale) }) : null,
  ].filter(Boolean);

  return (
    <div className="card space-y-4">
      <div className="flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-brand-400" />
        <h3 className="text-sm font-bold text-white">{t("title", { week: review.week })}</h3>
      </div>

      <div className="space-y-1.5">
        {stats.weeks.map((w) => (
          <div key={w.week} className="flex items-center gap-3 text-xs">
            <span className="w-14 shrink-0 text-slate-500">{t("week", { week: w.week })}</span>
            <div className="relative flex-1 h-2 rounded-full bg-slate-700/40">
              <div
                className="absolute inset-y-0 left-0 rounded-full bg-slate-500/40"
                style={{ width: `${(w.planned_km / peak) * 100}%` }}
              />
              <div
                className="absolute inset-y-0 left-0 rounded-full bg-brand-500"
                style={{ width: `${(w.run_km / peak) * 100}%` }}
              />
            </div>
            <span className="w-24 shrink-0 text-right text-slate-300">
              {t("volume", { run: km(w.run_km), planned: km(w.planned_km) })}
            </span>
            <span className="w-10 shrink-0 text-right text-slate-500">
              {w.sessions_done}/{w.sessions_planned}
            </span>
          </div>
        ))}
      </div>

      {facts.length > 0 && <p className="text-xs text-slate-400">{facts.join(" · ")}</p>}

      {review.text && (
        <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">{review.text}</p>
      )}
    </div>
  );
}
