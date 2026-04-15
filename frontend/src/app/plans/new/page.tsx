import { Navbar } from "@/components/ui/Navbar";
import { PlanCreatorForm } from "@/components/PlanCreatorForm/PlanCreatorForm";

export default function NewPlanPage() {
  return (
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-3xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">Nieuw Trainingsplan</h1>
          <p className="text-sm text-slate-400 mt-1">
            AI genereert een gepersonaliseerd schema op basis van jouw data en doelen.
          </p>
        </div>
        <PlanCreatorForm />
      </main>
    </div>
  );
}
