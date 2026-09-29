"""A weekly look back at a plan that is under way.

Each Monday the week that has just ended is reviewed against the weeks before
it: volume planned against run, sessions done, how far the long run has got,
whether the athlete is getting more efficient at the same heart rate, and what
is coming up. The numbers are computed here; the narrative — the thread
through the recent session analyses, the look ahead and a pep talk — is left
to Claude, which gets the numbers so it has no need to guess them.
"""
from datetime import date, timedelta

from app.services.follow_up import _EASY_TYPES, _aerobic_efficiency

_NOT_TRAINING = {"rest", "strength"}
_SERIES_WEEKS = 4
_RECENT_ANALYSES = 6


def _week1_monday(plan) -> date | None:
    start = plan.start_date or min((s.scheduled_date for s in plan.sessions if s.scheduled_date),
                                   default=None)
    return start - timedelta(days=start.weekday()) if start else None


def review_week(plan, today: date) -> int | None:
    """The plan week that has most recently finished, or None.

    None before the first week is over, and after the plan has ended — by then
    a follow-up plan is the place to look back.
    """
    first_monday = _week1_monday(plan)
    if not first_monday:
        return None
    this_monday = today - timedelta(days=today.weekday())
    finished = (this_monday - first_monday).days // 7
    last_week = max((s.week_number for s in plan.sessions), default=0)
    return finished if 1 <= finished <= last_week else None


def weekly_stats(plan, activities_by_id: dict, today: date) -> dict | None:
    """Numbers for the review, measured where there is a measurement."""
    week = review_week(plan, today)
    if week is None:
        return None
    training = [s for s in plan.sessions if s.workout_type not in _NOT_TRAINING]

    def run_km(s) -> float:
        act = activities_by_id.get(s.garmin_activity_id or "")
        return (act.distance_km if act and act.distance_km else s.distance_km) or 0

    weeks = []
    for number in range(max(1, week - _SERIES_WEEKS + 1), week + 1):
        in_week = [s for s in training if s.week_number == number]
        done = [s for s in in_week if s.completed_at]
        weeks.append({
            "week": number,
            "planned_km": round(sum(s.distance_km or 0 for s in in_week), 1),
            "run_km": round(sum(run_km(s) for s in done), 1),
            "sessions_planned": len(in_week),
            "sessions_done": len(done),
        })

    done_so_far = [s for s in training if s.completed_at and s.week_number <= week]
    long_runs = [run_km(s) for s in done_so_far if s.workout_type != "race"]
    ahead = [s for s in training if s.scheduled_date and s.scheduled_date >= today]
    longest_ahead = max((s.distance_km or 0 for s in ahead if s.workout_type == "long_run"), default=None)

    easy = [(s.scheduled_date, activities_by_id[s.garmin_activity_id]) for s in done_so_far
            if s.workout_type in _EASY_TYPES and s.garmin_activity_id in activities_by_id]

    next_week = sorted(
        (s for s in training if s.week_number == week + 1),
        key=lambda s: s.day_number,
    )

    return {
        "reviewed_week": week,
        "weeks_to_go": max(0, plan.duration_weeks - week),
        "race_date": plan.race_date.isoformat() if getattr(plan, "race_date", None) else None,
        "target_time_seconds": getattr(plan, "target_time_seconds", None),
        "weeks": weeks,
        "longest_run_km": max(long_runs) if long_runs else None,
        "longest_ahead_km": longest_ahead or None,
        "aerobic_efficiency": _aerobic_efficiency(easy),
        "next_week": [{"day": s.day_number, "type": s.workout_type, "km": s.distance_km}
                      for s in next_week],
    }


def recent_analyses(plan, limit: int = _RECENT_ANALYSES) -> list[tuple]:
    """The latest session analyses, oldest first: (date, title, text)."""
    with_text = sorted(
        (s for s in plan.sessions if getattr(s, "ai_feedback", None) and s.scheduled_date),
        key=lambda s: s.scheduled_date,
    )
    return [(s.scheduled_date, s.title, s.ai_feedback) for s in with_text[-limit:]]


def review_prompt(stats: dict, analyses: list[tuple], tone: str, lang: str) -> tuple[str, str, int]:
    """(system, task, max_tokens) for the weekly review."""
    if tone == "encouraging":
        system = (
            f"You are a warm, experienced running coach writing to a beginner in {lang}. "
            "Plain language, no jargon. Encouraging, but every compliment must rest on the "
            "numbers given. Return plain prose — no headers, no bullet points, no markdown. "
            "Use the Latin alphabet only."
        )
    else:
        system = (
            f"You are an elite running coach and sports scientist writing in {lang}. "
            "Ground every claim in the numbers given; no filler. Return plain prose — no "
            "headers, no bullet points, no markdown. Use the Latin alphabet only."
        )

    rows = "\n".join(
        f"- week {w['week']}: {w['run_km']} km run of {w['planned_km']} km planned, "
        f"{w['sessions_done']} of {w['sessions_planned']} sessions"
        for w in stats["weeks"]
    )
    facts = [f"Week reviewed: {stats['reviewed_week']}; weeks to go: {stats['weeks_to_go']}."]
    if stats.get("race_date"):
        facts.append(f"Race date: {stats['race_date']}.")
    if stats.get("longest_run_km"):
        facts.append(f"Longest run so far: {stats['longest_run_km']:g} km.")
    if stats.get("longest_ahead_km"):
        facts.append(f"Longest run still to come: {stats['longest_ahead_km']:g} km.")
    eff = stats.get("aerobic_efficiency")
    if eff:
        facts.append(
            f"Easy runs, same heart rate compared, early against recent: "
            f"{eff['change_pct']:+.1f}% distance per heartbeat (heat and fatigue also move this)."
        )
    if stats.get("next_week"):
        coming = ", ".join(f"{x['type']} {x['km'] or ''} km".replace("  ", " ")
                           for x in stats["next_week"])
        facts.append(f"Coming up next week: {coming}.")

    notes = "\n".join(f"- {when.isoformat()} {title}: {text}" for when, title, text in analyses) \
        or "- (no session analyses yet)"

    task = f"""Write a weekly review of this training plan in {lang}. Exactly 3 paragraphs, each 2–4 sentences. No headers, no bullet points, no markdown.

Paragraph 1 — The thread: what the recent weeks show — volume against plan, consistency, the trend. Draw on the session analyses below for what keeps coming back or is improving; do not repeat them one by one.
Paragraph 2 — Looking ahead: what the coming week holds and whether the athlete is on course. Judge it from what was done, never predict a race time.
Paragraph 3 — A pep talk for the week ahead: specific to this athlete and these numbers, not generic.

The numbers are computed and correct; use them rather than recalculating.

Volume per week:
{rows}

{chr(10).join(facts)}

Recent session analyses:
{notes}"""
    return system, task, 2500


def review_due(plan, stats: dict | None) -> bool:
    """One review per plan per finished week, however often the athlete syncs."""
    if not stats:
        return False
    previous = getattr(plan, "weekly_review", None) or {}
    return previous.get("week") != stats["reviewed_week"]


def stored_review(stats: dict, text: str | None, tone: str | None) -> dict:
    """What goes on the plan: the numbers always, the narrative when there is one."""
    from datetime import datetime, timezone

    return {
        "week": stats["reviewed_week"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "text": text,
        "tone": tone,
    }
