import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { WorkoutType } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const WORKOUT_COLORS: Record<WorkoutType, string> = {
  easy_run:  "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  long_run:  "bg-blue-500/20 text-blue-300 border-blue-500/30",
  tempo:     "bg-orange-500/20 text-orange-300 border-orange-500/30",
  interval:  "bg-red-500/20 text-red-300 border-red-500/30",
  recovery:  "bg-teal-500/20 text-teal-300 border-teal-500/30",
  race:      "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  rest:      "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

export const WORKOUT_LABELS: Record<WorkoutType, string> = {
  easy_run:  "Easy Run",
  long_run:  "Long Run",
  tempo:     "Tempo",
  interval:  "Intervals",
  recovery:  "Recovery",
  race:      "Race",
  rest:      "Rest",
};

export const GOAL_LABELS: Record<string, string> = {
  "5k": "5 km",
  "10k": "10 km",
  half_marathon: "Half Marathon",
  marathon: "Marathon",
};

export function secondsToTime(secs: number): string {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
export const DAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
