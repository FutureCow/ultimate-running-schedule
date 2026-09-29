"""Summarising a plan so the next one can build on it.

A new plan used to start from zero. The previous plan knows far more about the
athlete than a fresh estimate: the race result, the zones after recalibration,
how far the long run got, what was skipped. This module distils that into a
summary that is stored on the follow-up plan and handed to the prompt.
"""
from datetime import date

_NOT_TRAINING = {"rest", "strength"}
_TAPER_WEEKS = 2
_BUILD_WEEKS = 3

GOAL_KM = {"5k": 5.0, "10k": 10.0, "half_marathon": 21.1, "marathon": 42.195}


def goal_km(plan) -> float | None:
    if plan.goal == "custom":
        return plan.custom_distance_km
    return GOAL_KM.get(plan.goal)


def _fmt_clock(seconds: float) -> str:
    s = int(round(seconds))
    h, rest = divmod(s, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def summarise_plan(plan, activities_by_id: dict, today: date | None = None) -> dict:
    """What the plan achieved, as measured — not as planned.

    `activities_by_id` maps garmin activity id -> GarminActivity. A session
    ticked off by hand has no activity and counts its planned distance.
    """
    today = today or date.today()
    training = [s for s in plan.sessions if s.workout_type not in _NOT_TRAINING]
    past = [s for s in training if s.scheduled_date and s.scheduled_date < today]
    done = [s for s in past if s.completed_at]

    def actual_km(s) -> float | None:
        act = activities_by_id.get(s.garmin_activity_id or "")
        if act and act.distance_km:
            return act.distance_km
        return s.distance_km

    skipped: dict[str, int] = {}
    for s in past:
        if not s.completed_at:
            skipped[s.workout_type] = skipped.get(s.workout_type, 0) + 1

    runs = [actual_km(s) for s in done if s.workout_type != "race" and actual_km(s)]
    longest = max(runs) if runs else None

    # Weekly volume in the last build weeks — the taper would understate it
    last_build_week = plan.duration_weeks - _TAPER_WEEKS
    per_week: dict[int, float] = {}
    for s in done:
        if s.week_number <= last_build_week and actual_km(s):
            per_week[s.week_number] = per_week.get(s.week_number, 0) + actual_km(s)
    build = [per_week[w] for w in sorted(per_week)][-_BUILD_WEEKS:]
    build_weekly_km = round(sum(build) / len(build), 1) if build else None

    race = None
    for s in done:
        act = activities_by_id.get(s.garmin_activity_id or "")
        if s.workout_type == "race" and act and act.duration_seconds:
            race = {"distance_km": act.distance_km or goal_km(plan),
                    "time_seconds": act.duration_seconds}

    ahead = [s for s in training if s.scheduled_date and s.scheduled_date >= today]
    overview = (plan.plan_json or {}).get("plan_overview") or {}

    return {
        "name": plan.name,
        "goal": plan.goal,
        "goal_km": goal_km(plan),
        "duration_weeks": plan.duration_weeks,
        "finished": not ahead,
        "stopped_in_week": max((s.week_number for s in past), default=None) if ahead else None,
        "estimated_vdot": overview.get("estimated_vdot"),
        "pace_zones": overview.get("pace_zones") or {},
        "zones_recalibrated": "original_pace_zones" in overview,
        "sessions_planned": len(past),
        "sessions_done": len(done),
        "skipped_by_type": skipped,
        "longest_run_km": longest,
        "build_weekly_km": build_weekly_km,
        "race": race,
    }


def previous_plan_lines(summary: dict) -> str:
    """The summary as a prompt block that tells the plan to build on it."""
    goal = f"{summary['goal_km']:g} km" if summary.get("goal_km") else summary.get("goal", "?")
    status = ("finished" if summary.get("finished")
              else f"stopped in week {summary.get('stopped_in_week')} — not completed")
    lines = [
        "## Previous plan — build on this, do not restart from the original baseline",
        f"Previous goal: {goal}, {summary.get('duration_weeks')} weeks, {status}.",
    ]

    race = summary.get("race")
    if race and race.get("time_seconds") and race.get("distance_km"):
        pace = race["time_seconds"] / race["distance_km"]
        lines.append(
            f"Race result: {race['distance_km']:g} km in {_fmt_clock(race['time_seconds'])} "
            f"({_fmt_clock(pace)} /km) — the strongest signal of current level; "
            "derive the pace zones from it."
        )

    zones = summary.get("pace_zones") or {}
    if zones:
        label = "recalibrated during the plan" if summary.get("zones_recalibrated") else "as planned"
        listed = ", ".join(f"{k} {v}" for k, v in zones.items())
        lines.append(f"Pace zones at the end ({label}): {listed}.")
    if summary.get("estimated_vdot"):
        lines.append(f"Estimated VDOT then: {summary['estimated_vdot']}.")

    done, planned = summary.get("sessions_done"), summary.get("sessions_planned")
    if planned:
        skipped = summary.get("skipped_by_type") or {}
        missed = ", ".join(f"{n}× {kind}" for kind, n in skipped.items()) or "none"
        lines.append(f"Sessions done: {done} of {planned}; skipped: {missed}.")
    if summary.get("longest_run_km"):
        lines.append(f"Longest run done: {summary['longest_run_km']:g} km.")
    if summary.get("build_weekly_km"):
        lines.append(f"Weekly volume in the last build weeks: {summary['build_weekly_km']:.1f} km.")

    lines.append(
        "Start this plan's weekly volume at about 80–90% of that build volume and the long run "
        "a little below the longest run done, then progress from there. Where a session type "
        "was skipped repeatedly, make it more manageable rather than repeating it unchanged."
    )
    return "\n".join(lines) + "\n"
