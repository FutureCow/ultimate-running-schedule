"""Tests for the activity-analysis tone — scientific vs encouraging."""
import pytest
from pydantic import ValidationError

from app.schemas.plan import PlanCreate
from app.schemas.user import UserProfileUpdate
from app.services.claude_service import _feedback_instructions, resolve_feedback_tone


# ── Resolution: plan overrides profile ───────────────────────────────────────

def test_the_plan_setting_wins_over_the_profile_default():
    assert resolve_feedback_tone("encouraging", "scientific") == "encouraging"
    assert resolve_feedback_tone("scientific", "encouraging") == "scientific"


def test_a_plan_without_a_setting_follows_the_profile():
    assert resolve_feedback_tone(None, "encouraging") == "encouraging"


def test_falls_back_to_scientific_when_neither_is_set():
    """Existing plans and users have no setting and must keep what they get today."""
    assert resolve_feedback_tone(None, None) == "scientific"


def test_ignores_an_unrecognised_tone():
    assert resolve_feedback_tone("cheerful", "encouraging") == "encouraging"
    assert resolve_feedback_tone("cheerful", "nonsense") == "scientific"


# ── Prompt construction ──────────────────────────────────────────────────────

def scientific() -> tuple[str, str, int]:
    return _feedback_instructions("scientific", "Dutch (Nederlands)")


def encouraging() -> tuple[str, str, int]:
    return _feedback_instructions("encouraging", "Dutch (Nederlands)")


def test_the_scientific_analysis_still_asks_for_three_paragraphs():
    _, task, _ = scientific()

    assert "3 paragraphs" in task
    assert "cadence" in task.lower()


def test_the_encouraging_analysis_asks_for_two_paragraphs():
    _, task, _ = encouraging()

    assert "2 paragraphs" in task
    assert "3 paragraphs" not in task


def test_the_encouraging_analysis_asks_for_one_small_next_step():
    _, task, _ = encouraging()

    assert "one" in task.lower()
    assert "next" in task.lower()


def test_the_encouraging_analysis_must_stay_honest():
    """Positive, but not positive for its own sake — praise has to be earned."""
    system, task, _ = encouraging()
    combined = (system + task).lower()

    assert "invent" in combined or "not earned" in combined or "honest" in combined


def test_the_encouraging_analysis_is_shorter():
    assert encouraging()[2] < scientific()[2]


def test_both_tones_state_the_language():
    for system, task, _ in (scientific(), encouraging()):
        assert "Dutch (Nederlands)" in system + task


def test_an_unknown_tone_falls_back_to_the_scientific_instructions():
    assert _feedback_instructions("cheerful", "English") == _feedback_instructions(
        "scientific", "English"
    )


# ── Validation ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("tone", ["scientific", "encouraging", None])
def test_a_plan_accepts_a_known_tone_or_none(tone):
    assert PlanCreate(name="T", goal="10k", feedback_tone=tone).feedback_tone == tone


def test_a_plan_rejects_an_unknown_tone():
    with pytest.raises(ValidationError):
        PlanCreate(name="T", goal="10k", feedback_tone="cheerful")


def test_a_profile_rejects_an_unknown_tone():
    with pytest.raises(ValidationError):
        UserProfileUpdate(feedback_tone="cheerful")


def test_a_profile_accepts_a_known_tone():
    assert UserProfileUpdate(feedback_tone="encouraging").feedback_tone == "encouraging"


def test_the_encouraging_next_step_turns_into_recovery_after_a_hard_session():
    """Beginners under-recover most; the one step should go there when it matters."""
    _, task, _ = encouraging()

    assert "recovery" in task.lower()


def test_the_encouraging_analysis_still_asks_for_only_one_thing():
    """Recovery must share the step, not turn it into a list."""
    _, task, _ = encouraging()

    assert "one thing only" in task.lower()
    assert "2 paragraphs" in task


# ── Heart rate per tone ──────────────────────────────────────────────────────

def test_the_encouraging_note_is_not_built_around_heart_rate():
    _, task, _ = encouraging()

    assert "do not build the note around heart rate" in task.lower()


def test_the_scientific_analysis_still_leads_with_heart_rate():
    """Demoting HR everywhere would gut the first paragraph of this variant."""
    _, task, _ = scientific()

    assert "Training load & heart rate" in task
    assert "training zones" in task


def test_the_scientific_analysis_hedges_an_estimated_max():
    _, task, _ = scientific()

    assert "estimate" in task.lower()
