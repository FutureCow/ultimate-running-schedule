"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { ChevronDown, Sparkles } from "lucide-react";
import { WeeklyReview } from "@/types";
import { formatDistance } from "@/lib/goal";

/**
 * The weekly look back at a plan under way: volume planned against run per
 * week, the key numbers, and for Elite the narrative written from them.
 * Folded to its title and numbers, except the first time a week's review is
 * seen, so it does not keep pushing the plan below the fold.
 */
export function WeeklyReviewCard({ planId, review }: { planId: number; review: WeeklyReview }) {
  const t = useTranslations("plans.review");
  const locale = useLocale();
  const km = (value: number) => formatDistance(value, locale);
  const { stats } = review;
  // Headroom so neither the bar nor the plan marker touches the end of the track
  const peak = 1.1 * Math.max(1, ...stats.weeks.flatMap((w) => [w.planned_km, w.run_km]));
  const eff = stats.aerobic_efficiency;
  const seenKey = `weekly-review-seen:${planId}`;
  const [open, setOpen] = useState(() => {
    try {
      return localStorage.getItem(seenKey) !== String(review.week);
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(seenKey, String(review.week));
    } catch {
      // Without storage it simply stays folded next time too
    }
  }, [seenKey, review.week]);

  const facts = [
    t("weeksToGo", { weeks: stats.weeks_to_go }),
    stats.longest_run_km ? t("longest", { km: km(stats.longest_run_km) }) : null,
    stats.longest_ahead_km ? t("longestAhead", { km: km(stats.longest_ahead_km) }) : null,
    eff ? t(eff.change_pct >= 0 ? "efficiencyUp" : "efficiencyDown",
            { pct: Math.abs(eff.change_pct).toLocaleString(locale) }) : null,
  ].filter(Boolean);

  return (
    <div className="card space-y-4">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full items-start gap-2 text-left"
      >
        <Sparkles className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-white">{t("title", { week: review.week })}</h3>
          {facts.length > 0 && <p className="mt-0.5 text-xs text-slate-400">{facts.join(" · ")}</p>}
        </div>
        <ChevronDown
          className={`w-4 h-4 text-slate-400 shrink-0 mt-0.5 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <>
          <div className="space-y-1.5">
            {stats.weeks.map((w) => (
              <div key={w.week} className="flex items-center gap-3 text-xs">
                <span className="w-14 shrink-0 text-slate-500">{t("week", { week: w.week })}</span>
                <div className="relative flex-1 h-2 rounded-full bg-slate-700/40">
                  <div
                    className="absolute inset-y-0 left-0 rounded-full bg-brand-500"
                    style={{ width: `${(w.run_km / peak) * 100}%` }}
                  />
                  {/* The plan as a marker, visible even when more was run than planned */}
                  <div
                    className="absolute -top-1 -bottom-1 w-0.5 rounded-full bg-slate-200"
                    style={{ left: `calc(${(w.planned_km / peak) * 100}% - 1px)` }}
                    title={t("plannedMarker")}
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

          <p className="text-[10px] text-slate-500">{t("legend")}</p>

          {review.text && (
            <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">{review.text}</p>
          )}
        </>
      )}
    </div>
  );
}
