"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, ArrowRight, Zap, CheckCircle2, AlertCircle } from "lucide-react";
import { plansApi } from "@/lib/api";
import { PlanFormData } from "@/types";
import { DAYS } from "@/lib/utils";
import { StepGoal } from "./steps/StepGoal";
import { StepAthleteProfile } from "./steps/StepAthleteProfile";
import { StepTrainingPrefs } from "./steps/StepTrainingPrefs";
import { StepReview } from "./steps/StepReview";

const schema = z.object({
  name: z.string().min(1, "Verplicht"),
  goal: z.enum(["5k", "10k", "half_marathon", "marathon"]),
  target_time_seconds: z.number().optional(),
  target_pace_per_km: z.string().optional(),
  age: z.number().min(10).max(90).optional(),
  height_cm: z.number().min(100).max(250).optional(),
  weight_kg: z.number().min(30).max(200).optional(),
  weekly_km: z.number().min(0).max(500).optional(),
  weekly_runs: z.number().min(1).max(14).optional(),
  injuries: z.string().optional(),
  training_days: z.array(z.string()).min(2, "Kies minstens 2 dagen"),
  long_run_day: z.string().min(1, "Verplicht"),
  duration_weeks: z.number().min(4).max(52),
  surface: z.string().min(1, "Verplicht"),
  start_date: z.string().optional(),
});

export type FormSchema = z.infer<typeof schema>;

const STEPS = [
  { id: 1, title: "Doel & Plan", subtitle: "Wat wil je bereiken?" },
  { id: 2, title: "Jouw Profiel", subtitle: "Vertel ons over jezelf" },
  { id: 3, title: "Trainingsvoorkeur", subtitle: "Hoe train jij het liefst?" },
  { id: 4, title: "Overzicht", subtitle: "Controleer en genereer" },
];

export function PlanCreatorForm() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    getValues,
    formState: { errors },
    trigger,
  } = useForm<FormSchema>({
    resolver: zodResolver(schema),
    defaultValues: {
      goal: "10k",
      duration_weeks: 12,
      surface: "road",
      training_days: ["tuesday", "thursday", "saturday", "sunday"],
      long_run_day: "sunday",
    },
  });

  const values = watch();

  async function nextStep() {
    const fields: (keyof FormSchema)[][] = [
      ["name", "goal", "duration_weeks"],
      ["age", "height_cm", "weight_kg", "weekly_km", "weekly_runs"],
      ["training_days", "long_run_day", "surface"],
    ];
    const valid = await trigger(fields[step - 1] as any);
    if (valid) setStep((s) => Math.min(4, s + 1));
  }

  async function onSubmit(data: FormSchema) {
    setLoading(true);
    setError("");
    try {
      const payload: PlanFormData = {
        ...data,
        training_days: data.training_days,
      };
      const { data: plan } = await plansApi.create(payload);
      router.push(`/plans/${plan.id}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Plan aanmaken mislukt. Probeer opnieuw.");
      setLoading(false);
    }
  }

  const stepProps = { register, watch, setValue, getValues, errors };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress steps */}
      <div className="flex items-center justify-between mb-8 relative">
        <div className="absolute top-4 left-0 right-0 h-0.5 bg-slate-700 -z-10" />
        {STEPS.map(({ id, title }) => (
          <div key={id} className="flex flex-col items-center gap-2">
            <motion.div
              animate={{
                backgroundColor: step >= id ? "#22c55e" : "#1e293b",
                borderColor: step >= id ? "#22c55e" : "#475569",
              }}
              className="w-8 h-8 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-colors"
            >
              {step > id ? <CheckCircle2 className="w-4 h-4 text-white" /> : <span className={step === id ? "text-white" : "text-slate-500"}>{id}</span>}
            </motion.div>
            <span className={`text-[10px] font-medium hidden sm:block ${step >= id ? "text-brand-400" : "text-slate-600"}`}>
              {title}
            </span>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="mb-6">
          <h2 className="text-lg font-bold text-white">{STEPS[step - 1].title}</h2>
          <p className="text-sm text-slate-400">{STEPS[step - 1].subtitle}</p>
        </div>

        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-start gap-2 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2.5 text-sm text-red-400 mb-4"
          >
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
          >
            {step === 1 && <StepGoal {...stepProps} />}
            {step === 2 && <StepAthleteProfile {...stepProps} />}
            {step === 3 && <StepTrainingPrefs {...stepProps} />}
            {step === 4 && <StepReview values={values} />}
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-8 pt-4 border-t border-slate-700/50">
          <button
            type="button"
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1}
            className="btn-ghost disabled:opacity-0"
          >
            <ArrowLeft className="w-4 h-4" /> Vorige
          </button>

          {step < 4 ? (
            <button type="button" onClick={nextStep} className="btn-primary">
              Volgende <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit(onSubmit)}
              disabled={loading}
              className="btn-primary gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  AI genereert plan…
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Genereer Plan
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
