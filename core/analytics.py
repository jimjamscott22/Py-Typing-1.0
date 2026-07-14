"""Analytics helpers for streaks, error rates, and practice recommendations."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple


def _session_dates(session_history: List[dict]) -> List[date]:
    """Extract unique practice dates from session history, oldest first."""
    dates: set[date] = set()
    for session in session_history:
        try:
            dt = datetime.fromisoformat(session.get("timestamp", ""))
            dates.add(dt.date())
        except (ValueError, TypeError):
            continue
    return sorted(dates)


def compute_streaks(session_history: List[dict]) -> Tuple[int, int, int]:
    """Return (current_streak, longest_streak, unique_days).

    Streaks count consecutive calendar days with at least one session.
    """
    practice_dates = _session_dates(session_history)
    unique_days = len(practice_dates)
    if not practice_dates:
        return 0, 0, 0

    date_set = set(practice_dates)
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Current streak: must include today or yesterday to still be active.
    if today in date_set:
        anchor = today
    elif yesterday in date_set:
        anchor = yesterday
    else:
        current = 0
        anchor = None

    if anchor is not None:
        current = 0
        cursor = anchor
        while cursor in date_set:
            current += 1
            cursor -= timedelta(days=1)
    else:
        current = 0

    longest = 0
    run = 0
    prev: date | None = None
    for practice_date in practice_dates:
        if prev is not None and practice_date == prev + timedelta(days=1):
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        prev = practice_date

    return current, longest, unique_days


def compute_key_error_rates(
    errors: Dict[str, int],
    attempts: Dict[str, int],
) -> Dict[str, float]:
    """Map each key to its error rate (0.0–1.0)."""
    rates: Dict[str, float] = {}
    for key, error_count in errors.items():
        attempt_count = attempts.get(key, 0)
        if attempt_count > 0:
            rates[key] = error_count / attempt_count
    return rates


def get_practice_recommendations(
    errors: Dict[str, int],
    attempts: Dict[str, int],
    *,
    min_attempts: int = 10,
    top_n: int = 5,
) -> List[Tuple[str, float, int, int]]:
    """Rank keys by error rate for targeted practice.

    Returns list of (key, error_rate, error_count, attempt_count).
    """
    candidates: List[Tuple[str, float, int, int]] = []
    for key, error_count in errors.items():
        attempt_count = attempts.get(key, 0)
        if attempt_count < min_attempts or error_count <= 0:
            continue
        rate = error_count / attempt_count
        candidates.append((key, rate, error_count, attempt_count))

    candidates.sort(key=lambda item: (item[1], item[2]), reverse=True)
    return candidates[:top_n]


def normalize_stats_for_display(
    errors: Dict[str, int],
    attempts: Dict[str, int] | None = None,
    *,
    use_error_rate: bool = False,
) -> Dict[str, float]:
    """Convert raw error counts to display values (counts or rates as %)."""
    if not use_error_rate or not attempts:
        return {key: float(count) for key, count in errors.items()}

    display: Dict[str, float] = {}
    for key, error_count in errors.items():
        attempt_count = attempts.get(key, 0)
        if attempt_count > 0 and error_count > 0:
            display[key] = (error_count / attempt_count) * 100.0
    return display
