"""Claude AI service – generates a structured running plan."""
import json
import logging
import re
from typing import Optional

import anthropic

from app.config import settings
from app.schemas.common import DEFAULT_FEEDBACK_TONE, FEEDBACK_TONES
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
    "workout_type":"easy_run|long_run|tempo|interval|recovery|race|rest|strength",
    "title","description","distance_km","duration_minutes",
    "target_paces":{"warmup","main","cooldown",
      "strides":{"reps":4-8,"distance_m":80-100,"pace","rest_seconds":60-90}|null},
    "intervals":[{"reps","distance_m","duration_seconds","pace","rest_seconds"}]|null
  }]}]
}
Paces: "MM:SS – MM:SS" per km. Strength: distance_km=null, target_paces={"main":"N/A"}.
description: 1 sentence for runs; numbered 6-8 exercise list (sets×reps, rest, cue) for strength."""


class RefusedError(ValueError):
    """Claude's safety classifiers declined the request (HTTP 200, not an error)."""


def _response_text(message) -> str:
    """The first text block of a response.

    Never index content[0] directly: from Opus 5 onward adaptive thinking is on
    by default, so the first block is usually a thinking block with no .text.
    A refusal arrives as a normal 200 with stop_reason "refusal" and no answer
    at all, which would otherwise surface as a confusing AttributeError.
    """
    if getattr(message, "stop_reason", None) == "refusal":
        details = getattr(message, "stop_details", None)
        category = getattr(details, "category", None) or "onbekend"
        raise RefusedError(f"Claude weigerde dit verzoek (categorie: {category})")

    for block in getattr(message, "content", None) or []:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def _extract_json(text: str) -> str:
    """Return the JSON object from text, tolerant of preamble or code fences."""
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
    if fenced:
        return fenced.group(1)
    s, e = text.find("{"), text.rfind("}")
    return text[s : e + 1] if s != -1 and e > s else text


MARATHON_KM = 42.2


def _format_km(distance: float) -> str:
    """18.5 → '18.5', 25.0 → '25'."""
    return f"{distance:g}"


def _goal_label(plan: PlanCreate) -> str:
    goal_labels = {
        "5k": "5 km", "10k": "10 km",
        "half_marathon": "Half Marathon (21.1 km)", "marathon": "Marathon (42.2 km)",
    }
    if plan.goal == "custom" and plan.custom_distance_km:
        return f"{_format_km(plan.custom_distance_km)} km"
    return goal_labels.get(plan.goal, plan.goal)


def _ultra_block(plan: PlanCreate, goal_label: str) -> str:
    """Extra guidance for distances past the marathon, where VDOT alone is not enough."""
    if plan.goal != "custom" or (plan.custom_distance_km or 0) <= MARATHON_KM:
        return ""
    return f"""
## Ultra-distance guidance
{goal_label} is past the marathon: treat VDOT paces as a guide, not a rule.
Build back-to-back long runs on consecutive days rather than one very long run.
Measure the long efforts in time on feet, not kilometres.
Keep overall intensity lower — more easy volume, fewer hard interval sessions.
Rehearse fuelling and hydration on every long run.
Plan deliberate walk/run sections on climbs and late in the longest efforts.
"""


LONG_RUN_TYPE = "long_run"


def _long_run_violations(plan_json: dict) -> list[tuple[int | None, str]]:
    """(week_number, message) for every week whose long run is not the longest."""
    violations: list[tuple[int | None, str]] = []
    for week in plan_json.get("weeks", []):
        runs = [
            w for w in week.get("workouts", [])
            if isinstance(w.get("distance_km"), (int, float))
        ]
        long_runs = [w for w in runs if w.get("workout_type") == LONG_RUN_TYPE]
        if not long_runs:
            continue  # recovery and consolidation weeks have no long run
        longest_allowed = max(w["distance_km"] for w in long_runs)
        offenders = [
            w for w in runs
            if w.get("workout_type") != LONG_RUN_TYPE and w["distance_km"] > longest_allowed
        ]
        if offenders:
            listed = ", ".join(
                f"{w.get('workout_type', '?')} on day {w.get('day_number', '?')} "
                f"is {w['distance_km']} km"
                for w in offenders
            )
            violations.append((
                week.get("week_number"),
                f"Week {week.get('week_number', '?')}: long run is "
                f"{longest_allowed} km but {listed}.",
            ))
    return violations


def find_long_run_violations(plan_json: dict) -> list[str]:
    """Weeks where some other run is longer than the designated long run.

    The prompt states the long run is the longest run of its week, but a model
    can still drift — a 6.5 km "easy run" next to a 5.5 km "long run" reads as
    a broken plan to the athlete. Returns one line per offending week, phrased
    for feeding straight back to Claude.
    """
    return [message for _, message in _long_run_violations(plan_json)]


def _merge_corrected_weeks(plan_json: dict, corrected: list[dict]) -> dict:
    """Replace weeks by week_number, ignoring weeks the plan does not have."""
    import copy

    merged = copy.deepcopy(plan_json)
    by_number = {w.get("week_number"): w for w in corrected}
    merged["weeks"] = [
        by_number.get(week.get("week_number"), week) for week in merged.get("weeks", [])
    ]
    return merged


async def _correct_long_runs(client, plan_json: dict, violations: list[str], lang: str) -> dict:
    """Ask Claude to rewrite only the offending weeks. Returns the plan unchanged on failure."""
    offending = {number for number, _ in _long_run_violations(plan_json) if number is not None}
    weeks = [w for w in plan_json.get("weeks", []) if w.get("week_number") in offending]
    if not weeks:
        return plan_json

    prompt = f"""These weeks of a running plan break one rule: the long run must be the longest run of its week.

{chr(10).join(violations)}

Here are those weeks:
{json.dumps({"weeks": weeks}, ensure_ascii=False)}

Rewrite ONLY these weeks so the long_run is the longest run in each. Keep the same
days, the same workout types and roughly the same weekly total; adjust distances and
durations, and update every title and description in {lang} so the text matches the
new numbers.

Return ONLY a JSON object of the same shape: {{"weeks":[...]}}"""

    try:
        message = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4000,
            system="You are an elite running coach. Return ONLY a JSON object — no preamble, no markdown.",
            messages=[{"role": "user", "content": prompt}],
        )
        corrected = json.loads(_extract_json(_response_text(message))).get("weeks", [])
    except Exception as exc:
        logger.warning("Long-run correction failed, keeping original plan: %s", exc)
        return plan_json

    fixed = _merge_corrected_weeks(plan_json, corrected)
    remaining = find_long_run_violations(fixed)
    if remaining:
        # One corrective pass only; a still-broken plan beats no plan
        logger.warning("Long-run correction incomplete: %s", remaining)
    return fixed


def _build_prompt(plan: PlanCreate, garmin: Optional[dict], lang: str) -> str:
    d = plan.duration_weeks
    race_day = plan.race_date.isoweekday() if plan.race_date else 7
    race_str = plan.race_date.strftime("%a %d %b %Y") if plan.race_date else f"end of week {d}"

    if plan.target_time_seconds:
        h, r = divmod(plan.target_time_seconds, 3600)
        m, s = divmod(r, 60)
        target = f"{h}h{m:02d}m{s:02d}s" if h else f"{m}:{s:02d}"
    elif plan.target_pace_per_km:
        target = f"{plan.target_pace_per_km}/km"
    elif plan.goal_kind == "fitness":
        # No race to peak for — covering the distance is the goal
        target = "Complete the distance comfortably"
    else:
        target = "Personal best"

    goal_label = _goal_label(plan)

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

    if plan.goal_kind == "fitness":
        # No race — the athlete just wants to be able to cover the distance
        schedule_str = (
            f"## Target & schedule\n"
            f"No race. Week {d} is the target week: by the end of it the athlete must be "
            f"able to cover {goal_label} comfortably in a single run.\n"
            f"Grow the long run progressively toward that distance — no taper, "
            f"no race-day session, no time goal to peak for.\n"
            f'Week {d + 1}: easy consolidation only — short easy runs, theme = "Consolidation".'
        )
    else:
        schedule_str = (
            f"## Race & schedule\n"
            f"Race: {race_str} (week {d}, day {race_day}, 1=Mon…7=Sun).\n"
            f"Taper weeks {taper1}–{d}: reduced volume, nothing hard within 3 days of race.\n"
            f"Week {d}: race on day {race_day}; workouts AFTER it must be 'recovery' or 'rest'.\n"
            f'Week {d + 1}: post-race recovery only — easy short runs, theme = "Post-race recovery".'
        )

    return f"""Create a {d + 1}-week running plan ({d} training + 1 recovery) in {lang}.

## Athlete
Goal: {goal_label} | Target: {target}
Age {plan.age or '?'}, {plan.height_cm or '?'} cm, {plan.weight_kg or '?'} kg
Fitness: {plan.weekly_km or '?'} km/wk over {plan.weekly_runs or '?'} runs
Injuries: {plan.injuries or 'none'}. Notes: {plan.extra_notes or 'none'}.
Training days: {', '.join(plan.training_days) if plan.training_days else 'flexible'}. Long run: {plan.long_run_day or 'Sunday'}. Surface: {plan.surface or 'road'}.
The long run is the single longest run of its week — no other run may be longer — and it grows week over week toward the goal distance.

{schedule_str}
{_ultra_block(plan, goal_label)}
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

    # Streamed: a full plan is a long generation, and on a thinking model the
    # thinking shares max_tokens with the answer. Streaming avoids the HTTP
    # timeout that a non-streaming call of this size runs into.
    async with client.messages.stream(
        model=settings.CLAUDE_PLAN_MODEL,
        max_tokens=32000,
        system=SYSTEM_PROMPT.format(language=lang),
        messages=[{"role": "user", "content": _build_prompt(plan, garmin_summary, lang)}],
    ) as stream:
        message = await stream.get_final_message()

    logger.info("Claude: stop_reason=%s usage=%s", message.stop_reason, message.usage)

    raw = _extract_json(_response_text(message))
    if not raw:
        raise ValueError(f"Claude returned empty content (stop_reason={message.stop_reason})")

    try:
        plan_json = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed. raw[:500]=%s", raw[:500])
        raise ValueError(f"Invalid JSON from Claude: {e}. Got: {raw[:200]!r}") from e

    violations = find_long_run_violations(plan_json)
    if violations:
        logger.info("Long run shorter than another run, correcting: %s", violations)
        plan_json = await _correct_long_runs(client, plan_json, violations, lang)

    return plan_json


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

    raw = _extract_json(_response_text(message))
    try:
        data = json.loads(raw)
        return data.get("sessions", [])
    except json.JSONDecodeError as e:
        logger.error("Strength JSON parse failed. raw[:500]=%s", raw[:500])
        raise ValueError(f"Invalid JSON from Claude: {e}. Got: {raw[:200]!r}") from e


def resolve_feedback_tone(plan_tone: str | None, user_tone: str | None) -> str:
    """The plan's setting wins; without one, fall back to the athlete's profile."""
    for tone in (plan_tone, user_tone):
        if tone in FEEDBACK_TONES:
            return tone
    return DEFAULT_FEEDBACK_TONE


def _feedback_instructions(tone: str, lang_instruction: str) -> tuple[str, str, int]:
    """Return (system prompt, task instructions, max_tokens) for a feedback tone."""
    if tone == "encouraging":
        system = (
            f"You are a warm, experienced running coach writing to a beginner in {lang_instruction}. "
            "Return plain prose — no headers, no bullet points, no markdown. "
            "Be encouraging but never invent praise the data does not support: every compliment must "
            "point at a real number from this run. If something genuinely went badly, say so plainly "
            "and frame it as the next thing to practise, not as a failure."
        )
        task = f"""Write a post-run note to a beginner in {lang_instruction}. Write exactly 2 paragraphs, each 2–3 sentences. No headers, no bullet points, no markdown.

Paragraph 1 — What went well: name the specific things this run did right and quote the numbers that show it. Explain what those numbers mean in everyday language — no jargon, and no training-zone terminology unless you explain it in the same sentence.
Paragraph 2 — One small next step: give exactly one concrete, achievable thing to try on the next run, and say why it helps. One thing only — do not list several."""
        return system, task, 400

    system = (
        f"You are an elite running coach and sports scientist writing in {lang_instruction}. "
        "Return plain prose — no headers, no bullet points, no markdown. "
        "Ground every claim in the numbers you are given; no filler."
    )
    task = f"""You are an elite running coach writing a post-workout analysis in {lang_instruction}. Write exactly 3 paragraphs, each 2–3 sentences. No headers, no bullet points, no markdown.

Paragraph 1 — Training load & heart rate: Interpret the HR data scientifically (training zones, cardiac drift, effort relative to max HR). Reference relevant exercise physiology where appropriate.
Paragraph 2 — Pace & cadence: Assess pace consistency, cadence efficiency, and what the numbers reveal about running economy.
Paragraph 3 — Recovery: Give specific, evidence-based recovery advice tailored to this session's intensity and duration."""
    return system, task, 900


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
    tone: str = DEFAULT_FEEDBACK_TONE,
) -> str:
    """Generate a run analysis for an Elite user after a completed workout.

    `tone` is "scientific" (the default) or "encouraging"; see _feedback_instructions.

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
    system, task, max_tokens = _feedback_instructions(tone, lang_instruction)

    prompt = f"""{task}

Workout data:
{chr(10).join(stats_lines)}"""

    message = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    return _response_text(message).strip()


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

    raw = _extract_json(_response_text(message)) or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("recalibrate_paces JSON parse failed: %s", raw[:200])
        return {}
