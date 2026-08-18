"""Personal daily/weekly practice-goal evaluation."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Sequence, Tuple


def evaluate_daily_goal(
    session_history: Sequence[dict],
    goal_minutes: float,
    for_date: date,
) -> Tuple[float, bool]:
    """Return (minutes practiced on `for_date`, whether the goal was met)."""
    minutes = 0.0
    for session in session_history:
        try:
            timestamp = datetime.fromisoformat(session.get("timestamp", ""))
        except (ValueError, TypeError):
            continue
        if timestamp.date() == for_date:
            minutes += float(session.get("duration_seconds", 0) or 0) / 60.0
    return minutes, goal_minutes > 0 and minutes >= goal_minutes


def evaluate_weekly_goal(
    session_history: Sequence[dict],
    goal_sessions: int,
    for_date: date,
) -> Tuple[int, bool]:
    """Return (sessions completed since Monday of `for_date`'s week, goal met)."""
    week_start = for_date - timedelta(days=for_date.weekday())
    count = 0
    for session in session_history:
        try:
            timestamp = datetime.fromisoformat(session.get("timestamp", ""))
        except (ValueError, TypeError):
            continue
        if week_start <= timestamp.date() <= for_date:
            count += 1
    return count, goal_sessions > 0 and count >= goal_sessions
