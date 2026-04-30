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


def _stream_stats(values: list) -> dict | None:
    """Compute min/max/avg and optional HR-zone distribution from a numeric stream."""
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return {
        "min": min(clean),
        "max": max(clean),
        "avg": round(sum(clean) / len(clean), 1),
        "count": len(clean),
    }


def _hr_zone_distribution(hr_values: list, max_hr: int | None) -> str | None:
    """Return a human-readable HR zone breakdown (% time per zone) if max_hr is known."""
    clean = [v for v in hr_values if v is not None]
    if not clean or not max_hr:
        return None
    thresholds = [0.60, 0.70, 0.80, 0.90, 1.01]
    zone_counts = [0, 0, 0, 0, 0]
    for bpm in clean:
        pct = bpm / max_hr
        for i, t in enumerate(thresholds):
            if pct < t:
                zone_counts[i] += 1
                break
    total = len(clean)
    parts = []
    for i, count in enumerate(zone_counts):
        if count > 0:
            parts.append(f"Z{i+1}: {round(count / total * 100)}%")
    return "  ".join(parts) if parts else None


async def generate_run_feedback(
    activity: dict,
    session_title: str,
    language: str = "nl",
    streams: dict | None = None,
    user_age: int | None = None,
    user_max_hr: int | None = None,
) -> str:
    """Generate a concise scientific run analysis for an Elite user after a completed workout.

    `activity` may be a flat dict (from _parse_activity) or a nested detail dict with
    a 'summary' key (from fetch_activity_detail). `streams` may contain time-series
    lists for heart_rate, cadence, pace, and altitude.
    """
    client = anthropic.AsyncAnthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        base_url=settings.ANTHROPIC_BASE_URL or None,
    )

    # Support both flat (_parse_activity) and nested (fetch_activity_detail) formats
    if "summary" in activity:
        summary = activity["summary"]
        streams = streams or activity.get("streams") or {}
    else:
        summary = activity
        streams = streams or {}

    dist    = summary.get("distance_km", 0)
    dur     = int(summary.get("duration_seconds", 0))
    # support both avg_pace_per_km (flat) and avg_pace_per_km (detail summary)
    pace    = summary.get("avg_pace_per_km") or summary.get("average_pace_per_km") or "–"
    hr      = summary.get("avg_heart_rate") or summary.get("average_heart_rate")
    # Use athlete's true max HR for zone calculation:
    # 1. Age-based estimate (220 - age) if age known
    # 2. Highest HR ever seen in the stream (better than activity max for easy runs)
    # 3. Activity max HR as last resort
    activity_max_hr  = summary.get("max_heart_rate")
    hr_stream_pre    = (streams or activity.get("streams") or {}).get("heart_rate") or []
    stream_max_hr    = max((v for v in hr_stream_pre if v), default=None)
    estimated_max_hr = (220 - user_age) if user_age else None
    # Priority: user-set max HR > age estimate > stream max > activity max
    max_hr = user_max_hr or estimated_max_hr or stream_max_hr or activity_max_hr
    cad     = summary.get("avg_cadence") or summary.get("average_cadence")
    elev    = summary.get("elevation_gain_m") or summary.get("elevationGain")

    stats_lines = [
        f"- Session: {session_title}",
        f"- Distance: {dist} km",
        f"- Duration: {dur // 60}:{dur % 60:02d} min:sec",
        f"- Average pace: {pace} /km",
    ]
    if hr:
        if user_max_hr:
            max_hr_note = f"  |  Max HR (athlete-set): {max_hr} bpm"
        elif user_age:
            max_hr_note = f"  |  Max HR (220-{user_age}): {max_hr} bpm"
        elif max_hr:
            max_hr_note = f"  |  Max HR recorded this activity: {max_hr} bpm"
        else:
            max_hr_note = ""
        stats_lines.append(f"- Average heart rate: {hr} bpm{max_hr_note}")
    if cad:
        stats_lines.append(f"- Average cadence: {cad} steps/min")
    if elev:
        stats_lines.append(f"- Elevation gain: {round(float(elev))} m")

    # Enrich with stream-derived statistics
    hr_stream   = streams.get("heart_rate") or []
    cad_stream  = streams.get("cadence") or []
    pace_stream = streams.get("pace") or []
    alt_stream  = streams.get("altitude") or []

    hr_stats   = _stream_stats(hr_stream)
    cad_stats  = _stream_stats(cad_stream)
    pace_stats = _stream_stats(pace_stream)
    alt_stats  = _stream_stats(alt_stream)

    if hr_stats and hr_stats["count"] > 10:
        zone_str = _hr_zone_distribution(hr_stream, max_hr)
        stats_lines.append(
            f"- HR stream — min: {hr_stats['min']} bpm, max: {hr_stats['max']} bpm, avg: {hr_stats['avg']} bpm"
            + (f"  |  Zone distribution: {zone_str}" if zone_str else "")
        )
    if cad_stats and cad_stats["count"] > 10:
        stats_lines.append(
            f"- Cadence stream — min: {cad_stats['min']} spm, max: {cad_stats['max']} spm, avg: {cad_stats['avg']} spm"
        )
    if pace_stats and pace_stats["count"] > 10:
        def _fmt_pace(spm: float) -> str:
            s = int(round(spm))
            return f"{s // 60}:{s % 60:02d}"
        stats_lines.append(
            f"- Pace stream — fastest: {_fmt_pace(pace_stats['min'])} /km, "
            f"slowest: {_fmt_pace(pace_stats['max'])} /km, avg: {_fmt_pace(pace_stats['avg'])} /km"
        )
    if alt_stats and alt_stats["count"] > 10:
        stats_lines.append(
            f"- Altitude stream — min: {alt_stats['min']} m, max: {alt_stats['max']} m"
        )

    lang_instruction = "Dutch (Nederlands)" if language == "nl" else "English"

    prompt = f"""You are a sports scientist analyzing a running workout. Based on the data below, write a short analysis (2 sentences max) in {lang_instruction}.

Mention the most important observation (e.g. HR zone, pace, cadence) and one concrete takeaway. Reference the actual numbers. Be direct and concise.

Data:
{chr(10).join(stats_lines)}

Write in plain text — no markdown, no bullet points, no headers."""

    message = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=200,
        system=f"You are a sports scientist. Respond in {lang_instruction}. Be very concise — 2 sentences maximum. Always reference the specific data values provided.",
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip() if message.content else ""


async def recalibrate_paces(
    recent_runs: list[dict],
    current_zones: dict,
    language: str = "nl",
) -> dict:
    """Given 6 recent completed runs (planned vs actual), return updated pace zones.

    Returns: {"easy": "X:XX-X:XX", "marathon": ..., "threshold": ..., "interval": ..., "repetition": ..., "notes": "..."}
    """
    client = anthropic.AsyncAnthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        base_url=settings.ANTHROPIC_BASE_URL or None,
    )

    lang_instruction = "Dutch (Nederlands)" if language == "nl" else "English"

    runs_text = ""
    for i, r in enumerate(recent_runs, 1):
        planned = r.get("planned_paces", {}) or {}
        actual_pace = r.get("actual_pace") or "onbekend"
        actual_hr   = r.get("actual_hr")
        dist        = r.get("distance_km")
        line = f"{i}. {r['workout_type']} — gepland: {planned.get('main', '?')}/km"
        if dist:       line += f", afstand: {dist} km"
        if actual_pace != "onbekend": line += f", werkelijk tempo: {actual_pace}/km"
        if actual_hr:  line += f", gem. HR: {actual_hr} bpm"
        runs_text += line + "\n"

    zones_text = "\n".join(f"- {k}: {v}" for k, v in (current_zones or {}).items())

    prompt = f"""You are an elite running coach using Jack Daniels VDOT methodology.

A runner has completed these recent workouts (planned vs actual):
{runs_text}
Current pace zones:
{zones_text or "(not set)"}

Based on this data, recalibrate the runner's training pace zones. If actual paces are consistently faster/slower than planned, adjust zones accordingly. Keep changes conservative (max ~5 sec/km per zone per recalibration).

Return ONLY a JSON object in this exact format (use "min:ss-min:ss/km" notation):
{{"easy":"X:XX-X:XX","marathon":"X:XX-X:XX","threshold":"X:XX-X:XX","interval":"X:XX-X:XX","repetition":"X:XX-X:XX","notes":"1-2 sentence explanation in {lang_instruction}"}}"""

    message = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=300,
        system="You are an elite running coach. Return ONLY a JSON object — no preamble, no markdown.",
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_json(message.content[0].text) if message.content else "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("recalibrate_paces JSON parse failed: %s", raw[:200])
        return {}
