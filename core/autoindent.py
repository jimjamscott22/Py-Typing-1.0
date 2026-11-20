"""Pure logic for auto-filling leading indentation after Enter in multi-line targets."""

from __future__ import annotations

from typing import Sequence

from core.transitions import TextChange


def auto_fill_text(
    target_text: str, typed_text: str, changes: Sequence[TextChange],
) -> str:
    """Return the spaces to insert after a correct Enter, or "" when none apply.

    Fires only for a single, tail-end "\\n" insertion while everything typed so
    far matches the target, and only when the next target line starts with
    spaces followed by real content.
    """
    if len(changes) != 1:
        return ""
    change = changes[0]
    if change.removed != 0 or change.inserted != "\n":
        return ""
    if len(typed_text) != change.position + 1:
        return ""
    if typed_text != target_text[: len(typed_text)]:
        return ""

    rest = target_text[len(typed_text):]
    indent = len(rest) - len(rest.lstrip(" "))
    if indent == 0 or indent == len(rest) or rest[indent] == "\n":
        return ""
    return " " * indent
