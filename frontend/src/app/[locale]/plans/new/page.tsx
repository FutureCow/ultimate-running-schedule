import { useTranslations } from "next-intl";
import { Navbar } from "@/components/ui/Navbar";
import { PlanCreatorForm } from "@/components/PlanCreatorForm/PlanCreatorForm";

function NewPlanContent() {
  const t = useTranslations("plans.new");
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-white">{t("title")}</h1>
      <p className="text-sm text-slate-400 mt-1">{t("subtitle")}</p>
    </div>
  );
}

export default function NewPlanPage() {
  return (
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-3xl mx-auto">
        <NewPlanContent />
        <PlanCreatorForm />
      </main>
    </div>
  );
}
