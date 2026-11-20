"""Pure scoring functions for typing sessions.

Kept free of Qt and persistence dependencies so the formulas are unit-testable
in isolation.
"""

from typing import Optional


def calculate_wpm(
    typed: str,
    elapsed_seconds: Optional[float],
    backspace_count: int,
    penalty_factor: float,
    auto_filled: int = 0,
) -> int:
    """Effective WPM = raw_wpm - (backspace_count * penalty_factor), floored at 0.

    Raw WPM uses the standard 5-chars-per-word convention. `auto_filled`
    characters (indentation inserted for the user) are not counted.
    """
    if not typed or elapsed_seconds is None or elapsed_seconds <= 0:
        return 0

    words = max(len(typed) - auto_filled, 0) / 5
    minutes = elapsed_seconds / 60
    raw_wpm = int(words / minutes) if minutes > 0 else 0

    backspace_penalty = backspace_count * penalty_factor
    return max(0, int(raw_wpm - backspace_penalty))


def calculate_accuracy(
    typed: str,
    target: str,
    mismatch_errors: int,
    backspace_count: int,
    backspace_weight: float,
    auto_filled: int = 0,
) -> float:
    """Accuracy % accounting for mismatches, overruns, and weighted backspaces.

    total_errors = mismatch_errors + extra_chars_beyond_target + (backspaces * weight)
    `auto_filled` characters are always correct and are left out of both the
    numerator and the denominator.
    """
    if not typed:
        return 100.0

    typed_count = len(typed) - auto_filled
    if typed_count <= 0:
        return 100.0

    extra_errors = max(len(typed) - len(target), 0)
    backspace_errors = backspace_count * backspace_weight
    total_errors = mismatch_errors + extra_errors + backspace_errors
    correct = max(typed_count - total_errors, 0)
    return (correct / typed_count) * 100
