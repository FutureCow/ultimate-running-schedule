"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { plansApi } from "@/lib/api";
import { Plan } from "@/types";
import { PlanCreatorForm } from "@/components/PlanCreatorForm/PlanCreatorForm";
import { Navbar } from "@/components/ui/Navbar";

export default function EditPlanPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("plans.edit");

  const { data: plan, isLoading } = useQuery<Plan>({
    queryKey: ["plan", id],
    queryFn: () => plansApi.get(Number(id)).then((r) => r.data),
  });

  return (
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Link href={`/plans/${id}`} className="btn-ghost px-2 py-2">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-white">{t("title")}</h1>
            <p className="text-xs text-slate-400">{t("subtitle")}</p>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <span className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
          </div>
        ) : !plan ? (
          <div className="text-center py-20 text-slate-400">{t("title")}</div>
        ) : (
          <PlanCreatorForm editPlan={plan} />
        )}
      </main>
    </div>
  );
}
