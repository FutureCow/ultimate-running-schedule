"""
Claude AI service – generates a structured running plan with pace targets.
"""
import json
import re
from typing import Optional
import anthropic
from app.config import settings
from app.schemas.plan import PlanCreate


SYSTEM_PROMPT_BASE = """You are an elite running coach and sports scientist with 20+ years of experience.
You create highly personalized, science-backed training plans.

IMPORTANT OUTPUT RULES:
- Return ONLY valid JSON – no markdown, no explanation outside JSON.
- Every workout must include precise target paces in "MM:SS" format per km.
- Paces must be realistic and consistent with the athlete's history and goal.
- Pace calculations must use the Jack Daniels VDOT methodology.
- Workouts are structured as a progressive plan: build volume, then intensity, then taper.
- Generate ALL text fields (title, description, theme, weekly_structure, coaching_notes, garmin_description) in {language}.
"""

def _get_system_prompt(language: str) -> str:
    lang_name = "Dutch" if language == "nl" else "English"
    return SYSTEM_PROMPT_BASE.format(language=lang_name)

PLAN_PROMPT_TEMPLATE = """Create a complete {total_weeks}-week running training plan ({duration_weeks} training weeks + 1 post-race recovery week).

## Athlete Profile
- Goal race: {goal}
- Target finish time / pace: {target}
- Age: {age}
- Height: {height_cm} cm | Weight: {weight_kg} kg
- Current fitness: {weekly_km} km/week over {weekly_runs} runs
- Injuries / notes: {injuries}
- Extra preferences / notes: {extra_notes}
- Available training days: {training_days}
- Long run day: {long_run_day}
- Preferred surface: {surface}

## Race & Schedule
- Race date: {race_date}
- Race falls in week {duration_weeks}, day {race_day_number} (1=Mon … 7=Sun)
- Week {post_week_1} is a mandatory POST-RACE RECOVERY week (easy running only, no intensity)

## Planning Rules
- The final 2 weeks before the race (weeks {taper_week_1} and {taper_week_2}) must be a proper TAPER: sharply reduced volume, no heavy sessions within 3 days of race day.
- Week {duration_weeks}: the race workout goes on day {race_day_number}. No hard sessions in the 3 days before it.
- Week {post_week_1}: light recovery runs only (easy pace, short distance). Label theme as "Post-race recovery".

## Recent Garmin Activity Summary (last 3 months)
{garmin_summary}

## Required JSON Output Schema
{{
  "plan_overview": {{
    "goal": string,
    "target_time": string,
    "target_pace_per_km": string,
    "estimated_vdot": number,
    "pace_zones": {{
      "easy": string,         // "MM:SS – MM:SS /km"
      "marathon": string,
      "threshold": string,
      "interval": string,
      "repetition": string
    }},
    "weekly_structure": string,
    "coaching_notes": string
  }},
  "weeks": [
    {{
      "week_number": number,
      "theme": string,        // e.g. "Base Building", "Intensity", "Taper"
      "total_km": number,
      "workouts": [
        {{
          "day_number": number,          // 1=Mon … 7=Sun
          "workout_type": string,        // easy_run|long_run|tempo|interval|recovery|rest
          "title": string,
          "description": string,
          "distance_km": number | null,
          "duration_minutes": number | null,
          "target_paces": {{
            "warmup": string | null,     // "MM:SS – MM:SS"
            "main": string,             // "MM:SS – MM:SS"
            "cooldown": string | null
          }},
          "intervals": [               // only for interval workouts
            {{
              "reps": number,
              "distance_m": number | null,
              "duration_seconds": number | null,
              "pace": string,          // "MM:SS – MM:SS"
              "rest_seconds": number
            }}
          ] | null,
          "garmin_description": string   // short description for Garmin Connect
        }}
      ]
    }}
  ]
}}

Generate the full {total_weeks}-week plan now ({duration_weeks} training + 1 recovery)."""


def _format_garmin_summary(summary: Optional[dict]) -> str:
    if not summary:
        return "No Garmin data available – base plan on provided fitness data only."
    s = summary.get("summary", summary)
    return (
        f"- Total runs: {s.get('total_runs', 'N/A')}\n"
        f"- Total km: {s.get('total_km', 'N/A')}\n"
        f"- Avg weekly km: {s.get('avg_weekly_km', 'N/A')}\n"
        f"- Avg pace /km: {s.get('avg_pace_per_km', 'N/A')}\n"
        f"- Date range: {s.get('date_range', {}).get('from', '')} to {s.get('date_range', {}).get('to', '')}"
    )


def _goal_display(goal: str) -> str:
    return {"5k": "5 km", "10k": "10 km", "half_marathon": "Half Marathon (21.1 km)", "marathon": "Marathon (42.2 km)"}.get(goal, goal)


def _target_display(plan: PlanCreate) -> str:
    if plan.target_time_seconds:
        h = plan.target_time_seconds // 3600
        m = (plan.target_time_seconds % 3600) // 60
        s = plan.target_time_seconds % 60
        if h:
            return f"{h}h{m:02d}m{s:02d}s"
        return f"{m}:{s:02d}"
    if plan.target_pace_per_km:
        return f"{plan.target_pace_per_km}/km"
    return "Finish / personal best"


def _race_context(plan: PlanCreate) -> dict:
    """Derive race-related template variables from plan."""
    from datetime import date as date_type
    duration = plan.duration_weeks
    total = duration + 1

    race_date = plan.race_date
    if race_date:
        race_date_str = race_date.strftime("%A %d %B %Y")
        race_day_number = race_date.isoweekday()  # 1=Mon … 7=Sun
    else:
        race_date_str = f"end of week {duration} (exact date not set)"
        race_day_number = 7  # default Sunday

    return {
        "total_weeks": total,
        "race_date": race_date_str,
        "race_day_number": race_day_number,
        "post_week_1": duration + 1,
        "taper_week_1": max(1, duration - 1),
        "taper_week_2": duration,
    }


async def generate_plan(plan: PlanCreate, garmin_summary: Optional[dict] = None, language: str = "nl") -> dict:
    client_kwargs = {"api_key": settings.ANTHROPIC_API_KEY or "proxy"}
    if settings.ANTHROPIC_BASE_URL:
        client_kwargs["base_url"] = settings.ANTHROPIC_BASE_URL
    client = anthropic.AsyncAnthropic(**client_kwargs)

    race_ctx = _race_context(plan)
    prompt = PLAN_PROMPT_TEMPLATE.format(
        duration_weeks=plan.duration_weeks,
        goal=_goal_display(plan.goal),
        target=_target_display(plan),
        age=plan.age or "unknown",
        height_cm=plan.height_cm or "unknown",
        weight_kg=plan.weight_kg or "unknown",
        weekly_km=plan.weekly_km or "unknown",
        weekly_runs=plan.weekly_runs or "unknown",
        injuries=plan.injuries or "None reported",
        extra_notes=plan.extra_notes or "None",
        training_days=", ".join(plan.training_days) if plan.training_days else "flexible",
        long_run_day=plan.long_run_day or "Sunday",
        surface=plan.surface or "road",
        garmin_summary=_format_garmin_summary(garmin_summary),
        **race_ctx,
    )

    message = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=16000,
        system=_get_system_prompt(language),
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip any accidental markdown code fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    plan_data = json.loads(raw)
    return plan_data
