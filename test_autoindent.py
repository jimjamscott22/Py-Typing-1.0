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


def test_note_edit_shifts_positions_after_an_interior_insert():
    session = TypingSession()
    session.register_auto_fill(6, 4)
    session.note_edit(2, 0, 1)  # one character typed before the indentation
    assert session.auto_filled == {7, 8, 9, 10}


def test_note_edit_shifts_positions_back_after_an_interior_delete():
    session = TypingSession()
    session.register_auto_fill(7, 4)
    session.note_edit(0, 1, 0)  # one character deleted before the indentation
    assert session.auto_filled == {6, 7, 8, 9}


def test_note_edit_drops_removed_positions_and_closes_the_gap():
    session = TypingSession()
    session.register_auto_fill(6, 4)  # 6..9
    session.note_edit(7, 2, 0)  # 7 and 8 deleted; 9 moves down to 7
    assert session.auto_filled == {6, 7}


def test_note_edit_tail_deletion_drops_only_the_deleted_positions():
    session = TypingSession()
    session.register_auto_fill(6, 4)
    session.note_edit(8, 2, 0)
    assert session.auto_filled == {6, 7}


def test_note_edit_edit_after_the_fill_changes_nothing():
    session = TypingSession()
    session.register_auto_fill(6, 4)
    session.note_edit(10, 1, 1)
    assert session.auto_filled == {6, 7, 8, 9}


def test_note_edit_selection_into_the_fill_is_not_auto_filled_afterwards():
    session = TypingSession()
    session.register_auto_fill(6, 4)  # 6..9
    session.note_edit(7, 3, 1)  # select 7..9 and type one character over it
    assert session.auto_filled == {6}


def test_reset_clears_auto_fill():
    session = TypingSession()
    session.register_auto_fill(0, 3)
    session.reset()
    assert session.auto_filled == set()
