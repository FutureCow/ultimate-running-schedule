"""Types shared between schemas."""
from typing import Literal

# Tone of the AI analysis written after a completed run.
#   scientific  — physiology, training zones, evidence-based advice (the default)
#   encouraging — plain language for beginners: what went well, one small next step
FeedbackTone = Literal["scientific", "encouraging"]
FEEDBACK_TONES: tuple[str, ...] = ("scientific", "encouraging")
DEFAULT_FEEDBACK_TONE = "scientific"
