"""Tests for reading text out of a Claude response.

From Opus 5 onward adaptive thinking is on by default, so the first content
block is often a thinking block rather than the answer. Refusals arrive as a
normal 200 with stop_reason "refusal" and no usable content.
"""
import pytest
from anthropic.types import Message, TextBlock, ThinkingBlock, Usage

from app.services.claude_service import RefusedError, _response_text


def message(*blocks, stop_reason: str = "end_turn", stop_details=None) -> Message:
    return Message.construct(
        id="msg_test",
        content=list(blocks),
        model="claude-opus-5",
        role="assistant",
        stop_reason=stop_reason,
        stop_details=stop_details,
        type="message",
        usage=Usage.construct(input_tokens=1, output_tokens=1),
    )


def text(value: str) -> TextBlock:
    return TextBlock(type="text", text=value, citations=None)


def thinking(value: str = "reasoning...") -> ThinkingBlock:
    return ThinkingBlock(type="thinking", thinking=value, signature="sig")


def test_returns_the_text_of_a_plain_response():
    assert _response_text(message(text("hello"))) == "hello"


def test_skips_a_leading_thinking_block():
    """The Opus 5 default: thinking first, answer second."""
    assert _response_text(message(thinking(), text("hello"))) == "hello"


def test_skips_several_leading_blocks():
    assert _response_text(message(thinking(), thinking("more"), text("hello"))) == "hello"


def test_returns_empty_when_there_is_no_text_block():
    assert _response_text(message(thinking())) == ""


def test_returns_empty_for_an_empty_response():
    assert _response_text(message()) == ""


def test_raises_on_a_refusal():
    """A refusal is an HTTP 200 — without this it would surface as an IndexError."""
    with pytest.raises(RefusedError):
        _response_text(message(stop_reason="refusal"))


def test_a_refusal_names_its_category():
    details = type("StopDetails", (), {"type": "refusal", "category": "cyber"})()

    with pytest.raises(RefusedError, match="cyber"):
        _response_text(message(stop_reason="refusal", stop_details=details))


def test_a_refusal_without_details_still_raises_clearly():
    with pytest.raises(RefusedError, match="onbekend"):
        _response_text(message(stop_reason="refusal"))


def test_other_stop_reasons_are_not_refusals():
    assert _response_text(message(text("cut off"), stop_reason="max_tokens")) == "cut off"
