"""
Claude AI service – generates a structured running plan with pace targets.
"""
import json
import logging
import re
from typing import Optional
import anthropic
from app.config import settings
from app.schemas.plan import PlanCreate

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_BASE = """You are an elite running coach and sports scientist with 20+ years of experience.
You create highly personalized, science-backed training plans.

** LANGUAGE: YOU MUST WRITE EVERY TEXT VALUE IN THE JSON IN {language}. THIS IS MANDATORY. **

IMPORTANT OUTPUT RULES:
- Return ONLY valid JSON – no markdown, no explanation outside JSON.
- Every workout must include precise target paces in "MM:SS" format per km.
- Paces must be realistic and consistent with the athlete's history and goal.
- Pace calculations must use the Jack Daniels VDOT methodology.
- Workouts are structured as a progressive plan: build volume, then intensity, then taper.
- ALL string fields (title, description, theme, weekly_structure, coaching_notes, garmin_description, goal, target_time) MUST be written in {language}. No exceptions.
"""

def _get_system_prompt(language: str) -> str:
    lang_name = "Dutch" if language == "nl" else "English"
    return SYSTEM_PROMPT_BASE.format(language=lang_name)

PLAN_PROMPT_TEMPLATE = """IMPORTANT: Write ALL text values in {output_language}. Every title, description, theme, and note must be in {output_language}.

Create a complete {total_weeks}-week running training plan ({duration_weeks} training weeks + 1 post-race recovery week).

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
- Week {duration_weeks}: the race workout goes on day {race_day_number}. No hard sessions in the 3 days before it. Any workout scheduled AFTER day {race_day_number} in this same week must be of type "recovery" (short, very easy run or rest) — never tempo, interval, long_run or strength after the race.
- Week {post_week_1}: light recovery runs only (easy pace, short distance). Label theme as "Post-race recovery".

## Recent Garmin Activity Summary (last 3 months)
{garmin_summary}

{strength_section}

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
          "workout_type": string,        // easy_run|long_run|tempo|interval|recovery|rest|strength
          "title": string,
          "description": string,         // for strength: numbered exercise list with sets/reps/rest
          "distance_km": number | null,  // null for strength workouts
          "duration_minutes": number | null,
          "target_paces": {{
            "warmup": string | null,     // "MM:SS – MM:SS"
            "main": string,             // "MM:SS – MM:SS" — use "N/A" for strength
            "cooldown": string | null,
            "strides": {{              // optional: include when strides are prescribed
              "reps": number,          // typically 4–8
              "distance_m": number,    // typically 80–100
              "pace": string,          // "MM:SS – MM:SS" near-sprint / repetition pace
              "rest_seconds": number   // full recovery between strides, typically 60–90
            }} | null
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


_STRENGTH_TYPE_LABELS = {
    "core_stability": "Core & Stability",
    "max_strength": "Maximum Strength",
    "plyometrics": "Plyometrics & Explosiveness",
    "injury_prevention": "Injury Prevention & Mobility",
    "full_body": "General Full-Body",
}

_STRENGTH_LOCATION_LABELS = {
    "bodyweight": "Home (Bodyweight only)",
    "home_equipment": "Home (Dumbbells / resistance bands)",
    "gym": "Gym / fitness center",
}

_STRENGTH_DAY_NAMES = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}


def _format_strength_section(plan: PlanCreate, output_language: str = "Dutch") -> str:
    s = plan.strength
    if not s or not s.enabled:
        return ""

    location_label = _STRENGTH_LOCATION_LABELS.get(s.location or "", s.location or "unspecified")
    type_label = _STRENGTH_TYPE_LABELS.get(s.type or "", s.type or "full_body")
    day_names = [_STRENGTH_DAY_NAMES[d] for d in (s.days or []) if d in _STRENGTH_DAY_NAMES]
    days_str = ", ".join(day_names) if day_names else "flexible (you decide)"

    equipment_str = ""
    if s.location == "home_equipment" and s.equipment:
        equipment_str = f"\n- Available equipment: {', '.join(s.equipment)}"

    notes_str = f"\n- Athlete's additional preferences: {s.notes}" if s.notes else ""

    return f"""## Strength Training Integration
The athlete wants to include runner-specific strength training in the schedule.

- Preferred strength days: {days_str}
- Location / equipment: {location_label}{equipment_str}
- Training focus: {type_label}{notes_str}

### Strength Scheduling Rules (MANDATORY)
1. Schedule strength sessions ONLY on the specified preferred days. If a preferred day conflicts with a hard run, keep the run and skip strength that day.
2. NEVER place a heavy strength session (max_strength, plyometrics) on the day before OR the same day as an interval run, tempo run, or long run.
3. Core & stability or mobility sessions MAY be placed after an easy run on the same day.
4. During taper weeks (last 2 weeks): reduce strength to 1 light session max (core/mobility only).
5. Post-race recovery week: no strength training.

### Strength Workout Content Rules
- Use `"workout_type": "strength"` for these sessions.
- Set `distance_km` to null and `duration_minutes` to the estimated total session time (typically 30–50 min).
- Set `target_paces` to `{{"main": "N/A"}}`.
- The `description` field MUST contain a numbered list of 6–10 exercises appropriate for the location/equipment and focus type. Each exercise must include: sets × reps (or duration), rest time, and a brief cue. Example format:
  "1. Romanian Deadlift – 3×10, 60s rust. Houd rug recht, duw heupen naar achteren.\\n2. ..."
- Write ALL exercise names and cues in {output_language}.
- Adapt exercises to available equipment: bodyweight = no weights; home_equipment = dumbbells/bands allowed; gym = machines/barbells allowed.
"""


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

    lang_name = "Dutch" if language == "nl" else "English"
    race_ctx = _race_context(plan)
    prompt = PLAN_PROMPT_TEMPLATE.format(
        output_language=lang_name,
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
        strength_section=_format_strength_section(plan, output_language=lang_name),
        **race_ctx,
    )

    message = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=16000,
        system=_get_system_prompt(language),
        messages=[{"role": "user", "content": prompt}],
    )

    logger.info("Claude response: stop_reason=%s, content_blocks=%d", message.stop_reason, len(message.content))
    if not message.content:
        raise ValueError(f"Empty content from Claude API (stop_reason={message.stop_reason})")

    block = message.content[0]
    logger.info("First content block type=%s", getattr(block, "type", "unknown"))
    raw = block.text.strip()
    logger.info("Raw response length=%d, first 200 chars: %s", len(raw), raw[:200])

    # Strip any accidental markdown code fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    if not raw:
        raise ValueError(
            f"Claude returned empty response (stop_reason={message.stop_reason}, "
            f"usage={message.usage})"
        )

    try:
        plan_data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed. stop_reason=%s, raw[:500]=%s", message.stop_reason, raw[:500])
        raise ValueError(f"Claude response is not valid JSON: {e}. First 200 chars: {raw[:200]!r}") from e
    return plan_data
