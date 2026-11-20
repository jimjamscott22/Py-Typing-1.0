"""Tests for core/autoindent.py and TypingSession's auto-fill bookkeeping."""

import pytest

from core.autoindent import auto_fill_text
from core.models import TypingSession
from core.transitions import TextChange

TARGET = "if x:\n    y()\n    if z:\n        w()"


def test_fills_next_line_indent():
    assert auto_fill_text(TARGET, "if x:\n", [TextChange(5, 0, "\n")]) == "    "


def test_fills_nested_indent():
    typed = "if x:\n    y()\n    if z:\n"
    assert auto_fill_text(TARGET, typed, [TextChange(len(typed) - 1, 0, "\n")]) == " " * 8


@pytest.mark.parametrize(
    ("target", "typed", "changes"),
    [
        (TARGET, "iF x:\n", [TextChange(5, 0, "\n")]),  # prefix mismatches
        (TARGET, "if x", [TextChange(3, 0, "x")]),  # not a newline
        (TARGET, "if x:", [TextChange(5, 1, "")]),  # backspace
        (TARGET, "if x:\n", [TextChange(4, 0, ":\n")]),  # multi-character change
        ("a\nb", "a\n", [TextChange(1, 0, "\n")]),  # next line unindented
        ("a\n    \nb", "a\n", [TextChange(1, 0, "\n")]),  # whitespace-only line
        ("a\n", "a\n", [TextChange(1, 0, "\n")]),  # newline is the last character
        (TARGET, "if x:\nzz", [TextChange(5, 0, "\n")]),  # cursor not at the end
    ],
    ids=[
        "prefix-mismatch", "non-newline", "backspace", "multichar",
        "unindented-next-line", "whitespace-only-line", "newline-last", "not-at-end",
    ],
)
def test_no_fill(target, typed, changes):
    assert auto_fill_text(target, typed, changes) == ""


def test_keystroke_length_excludes_auto_filled():
    session = TypingSession()
    session.register_auto_fill(6, 4)
    assert session.keystroke_length(10) == 6
    assert session.keystroke_length(8) == 6
    assert session.keystroke_length(6) == 6
    assert session.auto_filled_count == 4


def test_prune_drops_positions_past_typed_length():
    session = TypingSession()
    session.register_auto_fill(6, 4)
    session.prune_auto_fill(8)
    assert session.auto_filled == {6, 7}


def test_note_edit_clears_on_interior_edit_before_fill():
    session = TypingSession(typed_text="x" * 10)
    session.register_auto_fill(6, 4)
    session.note_edit(2, 1)
    assert session.auto_filled == set()


def test_note_edit_keeps_tail_deletion():
    session = TypingSession(typed_text="x" * 10)
    session.register_auto_fill(6, 4)
    session.note_edit(8, 2)
    assert session.auto_filled == {6, 7, 8, 9}


def test_note_edit_keeps_edit_after_fill():
    session = TypingSession(typed_text="x" * 12)
    session.register_auto_fill(6, 4)
    session.note_edit(10, 1)
    assert session.auto_filled == {6, 7, 8, 9}


def test_reset_clears_auto_fill():
    session = TypingSession()
    session.register_auto_fill(0, 3)
    session.reset()
    assert session.auto_filled == set()
