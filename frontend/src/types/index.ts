export interface User {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface UserProfile {
  age?: number | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  weekly_km?: number | null;
  weekly_runs?: number | null;
  injuries?: string | null;
  is_admin?: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type WorkoutType =
  | "easy_run"
  | "long_run"
  | "tempo"
  | "interval"
  | "recovery"
  | "race"
  | "rest"
  | "strength";

export type StrengthLocation = "bodyweight" | "home_equipment" | "gym";
export type StrengthFocusType =
  | "core_stability"
  | "max_strength"
  | "plyometrics"
  | "injury_prevention"
  | "full_body";

export interface StrengthPreferences {
  enabled: boolean;
  location?: StrengthLocation | null;
  type?: StrengthFocusType | null;
  days?: number[] | null;
  equipment?: string[] | null;
  notes?: string | null;
}

export interface TargetPaces {
  warmup?: string | null;
  main: string;
  cooldown?: string | null;
  note?: string | null;
}

export interface IntervalStep {
  reps: number;
  distance_m?: number | null;
  duration_seconds?: number | null;
  pace: string;
  rest_seconds: number;
}

export interface WorkoutSession {
  id: number;
  plan_id: number;
  week_number: number;
  day_number: number;
  scheduled_date?: string | null;
  workout_type: WorkoutType;
  title: string;
  description?: string | null;
  distance_km?: number | null;
  duration_minutes?: number | null;
  target_paces?: TargetPaces | null;
  intervals?: IntervalStep[] | null;
  garmin_workout_id?: string | null;
  garmin_pushed_at?: string | null;
  completed_at?: string | null;
  garmin_activity_id?: string | null;
}

export interface PaceZones {
  easy: string;
  marathon: string;
  threshold: string;
  interval: string;
  repetition: string;
}

export interface PlanOverview {
  goal: string;
  target_time: string;
  target_pace_per_km: string;
  estimated_vdot: number;
  pace_zones: PaceZones;
  weekly_structure: string;
  coaching_notes: string;
}

export interface PlanWeek {
  week_number: number;
  theme: string;
  total_km: number;
  workouts: WorkoutSession[];
}

export interface PlanJson {
  plan_overview: PlanOverview;
  weeks: PlanWeek[];
}

export interface Plan {
  id: number;
  public_id: string;
  user_id: number;
  name: string;
  goal: string;
  target_time_seconds?: number | null;
  target_pace_per_km?: string | null;
  age?: number | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  weekly_km?: number | null;
  weekly_runs?: number | null;
  injuries?: string | null;
  extra_notes?: string | null;
  training_days?: string[] | null;
  long_run_day?: string | null;
  duration_weeks: number;
  surface?: string | null;
  start_date?: string | null;
  race_date?: string | null;
  plan_json?: PlanJson | null;
  garmin_synced: boolean;
  strength_enabled: boolean;
  strength_location?: string | null;
  strength_type?: string | null;
  strength_days?: number[] | null;
  created_at: string;
  updated_at: string;
  sessions: WorkoutSession[];
}

export interface GarminStatus {
  id: number;
  last_sync_at?: string | null;
  created_at: string;
}

export type GoalType = "5k" | "10k" | "half_marathon" | "marathon";

export interface PlanFormData {
  name: string;
  goal: GoalType;
  target_time_seconds?: number;
  target_pace_per_km?: string;
  age?: number;
  height_cm?: number;
  weight_kg?: number;
  weekly_km?: number;
  weekly_runs?: number;
  injuries?: string;
  extra_notes?: string;
  training_days: string[];
  long_run_day: string;
  duration_weeks: number;
  surface: string;
  start_date?: string;
  race_date?: string;
  strength?: StrengthPreferences;
}
