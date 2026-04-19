"""Claude AI service – generates a structured running plan."""
import json
import logging
import re
from typing import Optional

import anthropic

from app.config import settings
from app.schemas.plan import PlanCreate, StrengthPreferences

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are an elite running coach using Jack Daniels VDOT methodology. "
    "Write ALL text values in {language}. "
    "Return ONLY a JSON object — no preamble, no markdown."
)

_SCHEMA = """{
  "plan_overview":{"goal","target_time","target_pace_per_km","estimated_vdot",
    "pace_zones":{"easy","marathon","threshold","interval","repetition"},
    "weekly_structure","coaching_notes"},
  "weeks":[{"week_number","theme","total_km","workouts":[{
    "day_number":1-7,
    "workout_type":"easy_run|long_run|tempo|interval|recovery|rest|strength",
    "title","description","distance_km","duration_minutes",
    "target_paces":{"warmup","main","cooldown",
      "strides":{"reps":4-8,"distance_m":80-100,"pace","rest_seconds":60-90}|null},
    "intervals":[{"reps","distance_m","duration_seconds","pace","rest_seconds"}]|null
  }]}]
}
Paces: "MM:SS – MM:SS" per km. Strength: distance_km=null, target_paces={"main":"N/A"}.
description: 1 sentence for runs; numbered 6-8 exercise list (sets×reps, rest, cue) for strength."""


def _extract_json(text: str) -> str:
    """Return the JSON object from text, tolerant of preamble or code fences."""
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
    if fenced:
        return fenced.group(1)
    s, e = text.find("{"), text.rfind("}")
    return text[s : e + 1] if s != -1 and e > s else text


def _build_prompt(plan: PlanCreate, garmin: Optional[dict], lang: str) -> str:
    d = plan.duration_weeks
    race_day = plan.race_date.isoweekday() if plan.race_date else 7
    race_str = plan.race_date.strftime("%a %d %b %Y") if plan.race_date else f"end of week {d}"

    if plan.target_time_seconds:
        h, r = divmod(plan.target_time_seconds, 3600)
        m, s = divmod(r, 60)
        target = f"{h}h{m:02d}m{s:02d}s" if h else f"{m}:{s:02d}"
    else:
        target = f"{plan.target_pace_per_km}/km" if plan.target_pace_per_km else "Personal best"

    goal_labels = {"5k": "5 km", "10k": "10 km", "half_marathon": "Half Marathon (21.1 km)", "marathon": "Marathon (42.2 km)"}

    if garmin:
        g = garmin.get("summary", garmin)
        dr = g.get("date_range", {})
        garmin_str = (f"Last 3 mo: {g.get('total_runs','?')} runs, {g.get('total_km','?')} km, "
                      f"{g.get('avg_weekly_km','?')} km/wk, avg pace {g.get('avg_pace_per_km','?')} "
                      f"({dr.get('from','')}–{dr.get('to','')}).")
    else:
        garmin_str = "No Garmin data — use self-reported fitness."

    st = plan.strength
    if st and st.enabled:
        day_names = {1:"Mon",2:"Tue",3:"Wed",4:"Thu",5:"Fri",6:"Sat",7:"Sun"}
        locs = {"bodyweight":"home/bodyweight","home_equipment":"home/dumbbells+bands","gym":"gym"}
        typs = {"core_stability":"Core & Stability","max_strength":"Max Strength",
                "plyometrics":"Plyometrics","injury_prevention":"Injury Prevention","full_body":"Full Body"}
        days = ", ".join(day_names[d] for d in (st.days or []) if d in day_names) or "flexible"
        equip = f" ({', '.join(st.equipment)})" if st.location == "home_equipment" and st.equipment else ""
        notes = f" Notes: {st.notes}." if st.notes else ""
        strength_str = (
            f"\n## Strength training\n"
            f"Focus: {typs.get(st.type or '', 'Full Body')}. "
            f"Location: {locs.get(st.location or '', 'unspecified')}{equip}. "
            f"Days: {days}.{notes}\n"
            f"Never on same day or day before interval/tempo/long runs. "
            f"No strength in taper (last 2 weeks) or post-race recovery week.\n"
        )
    else:
        strength_str = "\nDo NOT include any strength workouts. Running workouts only.\n"

    taper1 = max(1, d - 1)
    return f"""Create a {d + 1}-week running plan ({d} training + 1 recovery) in {lang}.

## Athlete
Goal: {goal_labels.get(plan.goal, plan.goal)} | Target: {target}
Age {plan.age or '?'}, {plan.height_cm or '?'} cm, {plan.weight_kg or '?'} kg
Fitness: {plan.weekly_km or '?'} km/wk over {plan.weekly_runs or '?'} runs
Injuries: {plan.injuries or 'none'}. Notes: {plan.extra_notes or 'none'}.
Training days: {', '.join(plan.training_days) if plan.training_days else 'flexible'}. Long run: {plan.long_run_day or 'Sunday'}. Surface: {plan.surface or 'road'}.

## Race & schedule
Race: {race_str} (week {d}, day {race_day}, 1=Mon…7=Sun).
Taper weeks {taper1}–{d}: reduced volume, nothing hard within 3 days of race.
Week {d}: race on day {race_day}; workouts AFTER it must be 'recovery' or 'rest'.
Week {d + 1}: post-race recovery only — easy short runs, theme = "Post-race recovery".

## Recent activity
{garmin_str}
{strength_str}
## Output schema
{_SCHEMA}

Generate the full {d + 1}-week plan now."""


async def generate_plan(
    plan: PlanCreate,
    garmin_summary: Optional[dict] = None,
    language: str = "nl",
) -> dict:
    client_kwargs = {"api_key": settings.ANTHROPIC_API_KEY or "proxy"}
    if settings.ANTHROPIC_BASE_URL:
        client_kwargs["base_url"] = settings.ANTHROPIC_BASE_URL
    client = anthropic.AsyncAnthropic(**client_kwargs)

    lang = "Dutch" if language == "nl" else "English"

    message = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT.format(language=lang),
        messages=[{"role": "user", "content": _build_prompt(plan, garmin_summary, lang)}],
    )

    logger.info("Claude: stop_reason=%s usage=%s", message.stop_reason, message.usage)

    if not message.content:
        raise ValueError(f"Empty Claude response (stop_reason={message.stop_reason})")

    raw = _extract_json(message.content[0].text)
    if not raw:
        raise ValueError(f"Claude returned empty content (stop_reason={message.stop_reason})")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed. raw[:500]=%s", raw[:500])
        raise ValueError(f"Invalid JSON from Claude: {e}. Got: {raw[:200]!r}") from e


async def generate_strength_sessions(
    plan_json: dict,
    strength: StrengthPreferences,
    duration_weeks: int,
    language: str = "nl",
) -> list[dict]:
    """Generate only strength sessions for an existing plan. Much faster than a full plan."""
    client_kwargs = {"api_key": settings.ANTHROPIC_API_KEY or "proxy"}
    if settings.ANTHROPIC_BASE_URL:
        client_kwargs["base_url"] = settings.ANTHROPIC_BASE_URL
    client = anthropic.AsyncAnthropic(**client_kwargs)

    lang = "Dutch" if language == "nl" else "English"

    locs = {"bodyweight": "home/bodyweight", "home_equipment": "home/dumbbells+bands", "gym": "gym"}
    typs = {"core_stability": "Core & Stability", "max_strength": "Max Strength",
            "plyometrics": "Plyometrics", "injury_prevention": "Injury Prevention", "full_body": "Full Body"}
    day_names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}

    days_str = ", ".join(day_names[d] for d in (strength.days or []) if d in day_names) or "flexible"
    equip = f" ({', '.join(strength.equipment)})" if strength.location == "home_equipment" and strength.equipment else ""
    notes_str = f" Notes: {strength.notes}." if strength.notes else ""

    # Summarise existing run days per week so Claude can avoid conflicts
    week_summaries = []
    taper_start = max(1, duration_weeks - 1)
    for week in plan_json.get("weeks", []):
        wnum = week["week_number"]
        if wnum > duration_weeks:
            continue  # skip post-race recovery week
        run_days = sorted({w["day_number"] for w in week.get("workouts", [])
                           if w.get("workout_type") not in ("rest", "strength")})
        week_summaries.append(f"Week {wnum}: run days {run_days}")

    prompt = f"""Add strength training sessions to this {duration_weeks}-week running plan. Write all text in {lang}.

## Existing run days per week
{chr(10).join(week_summaries)}

## Strength preferences
Focus: {typs.get(strength.type or '', 'Full Body')}
Location: {locs.get(strength.location or '', 'unspecified')}{equip}
Preferred days: {days_str}{notes_str}

## Rules
- Only add sessions on preferred strength days. If that day already has a run, skip strength that week.
- NEVER place strength on the day before OR same day as interval/tempo/long_run.
- Weeks {taper_start}–{duration_weeks}: max 1 light session (core/mobility only), no heavy strength.
- No strength in week {duration_weeks + 1} (post-race recovery).
- duration_minutes: 30–50. target_paces: {{"main": "N/A"}}. distance_km: null.
- description: numbered list of 6–8 exercises (sets×reps, rest, cue) in {lang}.

## Output schema
{{"sessions":[{{"week_number":N,"day_number":D,"title":"...","description":"...","duration_minutes":N}}]}}

Return ONLY the JSON object."""

    message = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=8000,
        system=f"You are an elite running coach. Return ONLY a JSON object — no preamble, no markdown.",
        messages=[{"role": "user", "content": prompt}],
    )

    logger.info("Strength-only Claude: stop_reason=%s usage=%s", message.stop_reason, message.usage)

    if not message.content:
        raise ValueError(f"Empty Claude response (stop_reason={message.stop_reason})")

    raw = _extract_json(message.content[0].text)
    try:
        data = json.loads(raw)
        return data.get("sessions", [])
    except json.JSONDecodeError as e:
        logger.error("Strength JSON parse failed. raw[:500]=%s", raw[:500])
        raise ValueError(f"Invalid JSON from Claude: {e}. Got: {raw[:200]!r}") from e
