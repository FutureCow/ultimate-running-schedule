"""Claude AI service – generates a structured running plan with pace targets."""
import json
import logging
import re
from typing import Optional

import anthropic

from app.config import settings
from app.schemas.plan import PlanCreate

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are an elite running coach using Jack Daniels VDOT methodology. "
    "Write ALL text values (titles, descriptions, themes, notes) in {language}. "
    "Return ONLY a JSON object: start with {{ and end with }}. "
    "No preamble, no markdown, no code fences."
)

_GOAL_LABELS = {
    "5k": "5 km",
    "10k": "10 km",
    "half_marathon": "Half Marathon (21.1 km)",
    "marathon": "Marathon (42.2 km)",
}

_STRENGTH_TYPE_LABELS = {
    "core_stability": "Core & Stability",
    "max_strength": "Maximum Strength",
    "plyometrics": "Plyometrics & Explosiveness",
    "injury_prevention": "Injury Prevention & Mobility",
    "full_body": "General Full-Body",
}

_STRENGTH_LOCATION_LABELS = {
    "bodyweight": "home (bodyweight only)",
    "home_equipment": "home (dumbbells/bands)",
    "gym": "gym",
}

_DAY_NAMES = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}


# Compact schema — Claude infers structure from concise shape notation.
_JSON_SCHEMA = """{
  "plan_overview": {"goal","target_time","target_pace_per_km","estimated_vdot",
    "pace_zones":{"easy","marathon","threshold","interval","repetition"},
    "weekly_structure","coaching_notes"},
  "weeks":[{"week_number","theme","total_km","workouts":[{
    "day_number":1-7,
    "workout_type":"easy_run|long_run|tempo|interval|recovery|rest|strength",
    "title","description","distance_km","duration_minutes",
    "target_paces":{"warmup","main","cooldown",
      "strides":{"reps":4-8,"distance_m":80-100,"pace","rest_seconds":60-90}|null},
    "intervals":[{"reps","distance_m","duration_seconds","pace","rest_seconds"}]|null,
    "garmin_description"
  }]}]
}
All paces as "MM:SS – MM:SS" per km. For strength: distance_km=null, target_paces={"main":"N/A"}."""


def _target_display(plan: PlanCreate) -> str:
    if plan.target_time_seconds:
        h, rem = divmod(plan.target_time_seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}:{s:02d}"
    if plan.target_pace_per_km:
        return f"{plan.target_pace_per_km}/km"
    return "Personal best"


def _format_garmin(summary: Optional[dict]) -> str:
    if not summary:
        return "No Garmin data — use self-reported fitness only."
    s = summary.get("summary", summary)
    dr = s.get("date_range", {})
    return (
        f"Last 3 mo: {s.get('total_runs','?')} runs, {s.get('total_km','?')} km total, "
        f"{s.get('avg_weekly_km','?')} km/wk, avg pace {s.get('avg_pace_per_km','?')} "
        f"({dr.get('from','')}–{dr.get('to','')})."
    )


def _format_strength(plan: PlanCreate) -> str:
    s = plan.strength
    if not s or not s.enabled:
        return ""
    loc = _STRENGTH_LOCATION_LABELS.get(s.location or "", "unspecified")
    typ = _STRENGTH_TYPE_LABELS.get(s.type or "", "full_body")
    days = ", ".join(_DAY_NAMES[d] for d in (s.days or []) if d in _DAY_NAMES) or "flexible"
    equip = f" ({', '.join(s.equipment)})" if s.location == "home_equipment" and s.equipment else ""
    notes = f" Notes: {s.notes}." if s.notes else ""
    return (
        f"\n## Strength training\n"
        f"Focus: {typ}. Location: {loc}{equip}. Days: {days}.{notes}\n"
        f"Rules: workout_type='strength', distance_km=null, duration_minutes=30–50, "
        f"target_paces={{\"main\":\"N/A\"}}. description = numbered list of 6–10 exercises "
        f"(sets×reps, rest, brief cue). Never same/day-before interval/tempo/long runs. "
        f"No strength in last 2 taper weeks or post-race recovery week.\n"
    )


def _build_prompt(plan: PlanCreate, garmin: Optional[dict], language: str) -> str:
    duration = plan.duration_weeks
    total = duration + 1
    if plan.race_date:
        race_str = plan.race_date.strftime("%a %d %b %Y")
        race_day = plan.race_date.isoweekday()
    else:
        race_str = f"end of week {duration}"
        race_day = 7
    taper1, taper2 = max(1, duration - 1), duration
    post_week = duration + 1

    return f"""Create a {total}-week running plan ({duration} training + 1 recovery) in {language}.

## Athlete
Goal: {_GOAL_LABELS.get(plan.goal, plan.goal)} | Target: {_target_display(plan)}
Age {plan.age or '?'}, {plan.height_cm or '?'} cm, {plan.weight_kg or '?'} kg
Current: {plan.weekly_km or '?'} km/wk over {plan.weekly_runs or '?'} runs
Injuries: {plan.injuries or 'none'}. Notes: {plan.extra_notes or 'none'}.
Training days: {', '.join(plan.training_days) if plan.training_days else 'flexible'}. \
Long run: {plan.long_run_day or 'Sunday'}. Surface: {plan.surface or 'road'}.

## Race & schedule
Race: {race_str} (week {duration}, day {race_day}, 1=Mon…7=Sun).
Taper weeks {taper1}–{taper2}: sharply reduced volume, nothing hard within 3 days of race.
Week {duration}: race on day {race_day}; any workout AFTER it must be 'recovery' or 'rest'.
Week {post_week}: post-race recovery only — easy short runs. theme = "Post-race recovery".

## Recent activity
{_format_garmin(garmin)}
{_format_strength(plan)}
## Output schema
{_JSON_SCHEMA}

Generate the full {total}-week plan now."""


def _extract_json(raw: str) -> str:
    """Pull a JSON object out of the raw text, tolerant of preamble/code fences."""
    raw = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw)
    if fenced:
        return fenced.group(1)
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        return raw[start:end + 1]
    return raw


async def generate_plan(
    plan: PlanCreate,
    garmin_summary: Optional[dict] = None,
    language: str = "nl",
) -> dict:
    client_kwargs = {"api_key": settings.ANTHROPIC_API_KEY or "proxy"}
    if settings.ANTHROPIC_BASE_URL:
        client_kwargs["base_url"] = settings.ANTHROPIC_BASE_URL
    client = anthropic.AsyncAnthropic(**client_kwargs)

    lang_name = "Dutch" if language == "nl" else "English"
    prompt = _build_prompt(plan, garmin_summary, lang_name)

    message = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT.format(language=lang_name),
        messages=[{"role": "user", "content": prompt}],
    )

    logger.info(
        "Claude response: stop_reason=%s, blocks=%d, usage=%s",
        message.stop_reason, len(message.content), message.usage,
    )
    if not message.content:
        raise ValueError(f"Empty Claude response (stop_reason={message.stop_reason})")

    raw = _extract_json(message.content[0].text)
    if not raw:
        raise ValueError(f"Claude returned empty content (stop_reason={message.stop_reason})")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed. raw[:500]=%s", raw[:500])
        raise ValueError(f"Claude response is not valid JSON: {e}. First 200 chars: {raw[:200]!r}") from e
