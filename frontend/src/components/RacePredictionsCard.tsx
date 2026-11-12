"use client";

import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { format, parseISO } from "date-fns";
import { nl, enUS } from "date-fns/locale";
import { Trophy } from "lucide-react";
import { garminApi } from "@/lib/api";
import { RacePredictions } from "@/types";

function clock(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.round(seconds % 60);
  const mm = h > 0 ? m.toString().padStart(2, "0") : String(m);
  return `${h > 0 ? `${h}:` : ""}${mm}:${s.toString().padStart(2, "0")}`;
}

/** Estimated 5K/10K/HM/M times; hidden when there is no usable run to base them on. */
export function RacePredictionsCard() {
  const t = useTranslations("analyse.predictions");
  const locale = useLocale();

  const { data } = useQuery<RacePredictions | null>({
    queryKey: ["race-predictions"],
    queryFn: () => garminApi.racePredictions().then((r) => r.data ?? null),
  });

  if (!data) return null;

  const { basis } = data;
  const date = format(parseISO(basis.date), "d MMM yyyy", { locale: locale === "nl" ? nl : enUS });
  const distance = basis.distance_km.toLocaleString(locale, { maximumFractionDigits: 2 });

  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-2">
        <Trophy className="w-4 h-4 text-brand-400" />
        <h2 className="text-sm font-semibold text-white">{t("title")}</h2>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {data.predictions.map((p) => (
          <div key={p.key} className="rounded-xl bg-surface-elevated px-3 py-2">
            <p className="text-[11px] text-slate-500">{t(`distances.${p.key}`)}</p>
            <p className="text-base font-semibold text-white tabular-nums">{clock(p.seconds)}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400">
        {t("basis", { name: basis.name || "—", date, distance, time: clock(basis.duration_seconds) })}
      </p>
      <p className="text-[10px] text-slate-600">{t("note")}</p>
    </div>
  );
}
