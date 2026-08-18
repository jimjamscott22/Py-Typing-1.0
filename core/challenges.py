"""Daily challenge definitions and progress evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class Challenge:
    """A daily challenge template drawn from the fixed pool below."""

    id: str
    icon: str
    title: str
    description: str
    metric: str
    target: float


@dataclass(frozen=True)
class ChallengeProgress:
    """Today's progress toward one challenge."""

    challenge: Challenge
    current: float
    completed: bool
    progress_text: str

    @property
    def percent(self) -> int:
        if self.challenge.target <= 0:
            return 100 if self.completed else 0
        return max(0, min(100, round((self.current / self.challenge.target) * 100)))


CHALLENGE_TEMPLATES: Tuple[Challenge, ...] = (
    Challenge(
        "speed_burst_40", "⚡", "Speed Burst",
        "Reach 40 WPM in a single session today.", "best_wpm", 40,
    ),
    Challenge(
        "speed_demon_60", "🚀", "Speed Demon",
        "Reach 60 WPM in a single session today.", "best_wpm", 60,
    ),
    Challenge(
        "accuracy_ace", "🎯", "Accuracy Ace",
        "Finish a session today with 95%+ accuracy.", "best_accuracy", 95,
    ),
    Challenge(
        "marathon_typist", "🏃", "Marathon Typist",
        "Type 500 characters total today.", "total_chars", 500,
    ),
    Challenge(
        "clean_sweep", "✨", "Clean Sweep",
        "Finish a 50+ character session today with zero errors.", "zero_error_session", 1,
    ),
    Challenge(
        "steady_hands", "➡️", "Steady Hands",
        "Finish a 50+ character session today without a single backspace.",
        "zero_backspace_session", 1,
    ),
    Challenge(
        "session_sprint", "🔁", "Session Sprint",
        "Complete 3 sessions today.", "session_count", 3,
    ),
)

CHALLENGES_BY_ID: Dict[str, Challenge] = {
    challenge.id: challenge for challenge in CHALLENGE_TEMPLATES
}


def get_daily_challenge(for_date: date) -> Challenge:
    """Deterministically pick the day's challenge from the fixed pool.

    Seeded by the date's ordinal so the same day always yields the same
    challenge (stable across restarts) without needing any stored state.
    """
    index = for_date.toordinal() % len(CHALLENGE_TEMPLATES)
    return CHALLENGE_TEMPLATES[index]


def _sessions_on(session_history: Sequence[dict], for_date: date) -> List[dict]:
    todays: List[dict] = []
    for session in session_history:
        try:
            timestamp = datetime.fromisoformat(session.get("timestamp", ""))
        except (ValueError, TypeError):
            continue
        if timestamp.date() == for_date:
            todays.append(session)
    return todays


def evaluate_challenge_progress(
    challenge: Challenge,
    session_history: Sequence[dict],
    for_date: date,
) -> ChallengeProgress:
    """Compute progress toward `challenge` from sessions recorded on `for_date`."""
    todays = _sessions_on(session_history, for_date)
    target = challenge.target

    if challenge.metric == "best_wpm":
        current = max((float(s.get("wpm", 0) or 0) for s in todays), default=0.0)
        text = f"Best today: {current:.0f} / {target:.0f} WPM"
    elif challenge.metric == "best_accuracy":
        current = max((float(s.get("accuracy", 0) or 0) for s in todays), default=0.0)
        text = f"Best today: {current:.1f}% / {target:.0f}%"
    elif challenge.metric == "total_chars":
        current = sum(float(s.get("text_length", 0) or 0) for s in todays)
        text = f"{current:.0f} / {target:.0f} characters today"
    elif challenge.metric == "zero_error_session":
        current = 1.0 if any(
            int(s.get("text_length", 0) or 0) >= 50 and float(s.get("errors", 0) or 0) == 0
            for s in todays
        ) else 0.0
        text = "No qualifying run yet today" if not current else "Completed"
    elif challenge.metric == "zero_backspace_session":
        current = 1.0 if any(
            int(s.get("text_length", 0) or 0) >= 50 and float(s.get("backspaces", 0) or 0) == 0
            for s in todays
        ) else 0.0
        text = "No qualifying run yet today" if not current else "Completed"
    elif challenge.metric == "session_count":
        current = float(len(todays))
        text = f"{current:.0f} / {target:.0f} sessions today"
    else:
        current = 0.0
        text = ""

    completed = target > 0 and current >= target
    return ChallengeProgress(
        challenge=challenge,
        current=current,
        completed=completed,
        progress_text=text,
    )
