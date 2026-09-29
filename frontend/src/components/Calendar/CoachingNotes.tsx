"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Info } from "lucide-react";

/**
 * The plan's explanation, read once when the plan starts: folded to its first
 * sentence so it does not push the calendar down on every visit.
 */
export function CoachingNotes({ text }: { text: string }) {
  const t = useTranslations("plans");
  const [open, setOpen] = useState(false);
  const first = text.match(/^[\s\S]*?[.!?](?=\s|$)/)?.[0] ?? text;
  const folds = first.trim().length < text.trim().length;

  return (
    <div className="flex gap-3 card bg-blue-950/30 border-blue-700/30">
      <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
      <p className="text-sm text-slate-300 leading-relaxed">
        {open || !folds ? text : first}
        {folds && (
          <button
            type="button"
            onClick={() => setOpen(!open)}
            className="ml-1.5 text-blue-400 hover:text-blue-300 font-medium"
          >
            {open ? t("readLess") : t("readMore")}
          </button>
        )}
      </p>
    </div>
  );
}
