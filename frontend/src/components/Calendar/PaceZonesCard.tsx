"use client";

import { useTranslations } from "next-intl";
import { PaceZones } from "@/types";

export function PaceZonesCard({ zones, vdot }: { zones: PaceZones; vdot?: number }) {
  const t = useTranslations("paceZones");

  const ZONES = [
    { key: "easy" as const,       color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
    { key: "marathon" as const,   color: "text-blue-400",    bg: "bg-blue-500/10 border-blue-500/20" },
    { key: "threshold" as const,  color: "text-orange-400",  bg: "bg-orange-500/10 border-orange-500/20" },
    { key: "interval" as const,   color: "text-red-400",     bg: "bg-red-500/10 border-red-500/20" },
    { key: "repetition" as const, color: "text-purple-400",  bg: "bg-purple-500/10 border-purple-500/20" },
  ];

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white">{t("title")}</h3>
          <p className="text-xs text-slate-500">{t("subtitle")}</p>
        </div>
        {vdot && (
          <div className="text-right">
            <p className="text-xs text-slate-500">{t("vdot")}</p>
            <p className="text-xl font-bold text-brand-400 font-mono">{vdot}</p>
          </div>
        )}
      </div>

      <div className="space-y-2">
        {ZONES.map(({ key, color, bg }) => (
          <div key={key} className={`flex items-center justify-between rounded-xl border px-3 py-2 ${bg}`}>
            <span className="text-xs font-medium text-slate-300">{t(`zones.${key}`)}</span>
            <span className={`font-mono text-sm font-bold ${color}`}>{zones[key]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
