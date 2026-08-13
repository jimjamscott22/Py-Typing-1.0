"""Achievement definitions and progress evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from core.analytics import compute_streaks


@dataclass(frozen=True)
class Achievement:
    """A badge that can be earned from recorded typing progress."""

    id: str
    icon: str
    name: str
    description: str


@dataclass(frozen=True)
class AchievementProgress:
    """The current earned state and progress for one achievement."""

    achievement: Achievement
    earned: bool
    unlocked_at: Optional[str]
    current: float
    target: float
    progress_text: str

    @property
    def percent(self) -> int:
        if self.target <= 0:
            return 100 if self.earned else 0
        return max(0, min(100, round((self.current / self.target) * 100)))


ACHIEVEMENTS: Tuple[Achievement, ...] = (
    Achievement("first_steps", "🌱", "First Steps", "Complete your first recorded session."),
    Achievement("sessions_10", "🎯", "Dedicated Typist", "Complete 10 recorded sessions."),
    Achievement("sessions_50", "🏆", "Practice Pro", "Complete 50 recorded sessions."),
    Achievement("wpm_30", "🚲", "Building Speed", "Reach 30 WPM in a recorded session."),
    Achievement("wpm_50", "🚀", "Speedster", "Reach 50 WPM in a recorded session."),
    Achievement("wpm_75", "⚡", "Lightning Fingers", "Reach 75 WPM in a recorded session."),
    Achievement(
        "perfect_accuracy",
        "💯",
        "Perfectionist",
        "Finish at least 25 characters with 100% accuracy.",
    ),
    Achievement(
        "zero_errors",
        "✨",
        "Clean Run",
        "Finish at least 50 characters without an error.",
    ),
    Achievement(
        "zero_backspaces",
        "➡️",
        "No Looking Back",
        "Finish at least 50 characters without using backspace.",
    ),
    Achievement("streak_3", "🔥", "On a Roll", "Practice for 3 consecutive days."),
    Achievement("streak_7", "🌟", "Week Warrior", "Practice for 7 consecutive days."),
    Achievement(
        "curriculum_complete",
        "🎓",
        "Curriculum Complete",
        "Complete every text in every built-in lesson.",
    ),
)

ACHIEVEMENTS_BY_ID: Dict[str, Achievement] = {
    achievement.id: achievement for achievement in ACHIEVEMENTS
}


def _best_session_value(history: Sequence[dict], key: str) -> float:
    return max((float(session.get(key, 0) or 0) for session in history), default=0.0)


def _qualifying_session_count(
    history: Sequence[dict],
    *,
    minimum_length: int,
    field: str,
    expected: float,
) -> int:
    return sum(
        1
        for session in history
        if int(session.get("text_length", 0) or 0) >= minimum_length
        and float(session.get(field, 0) or 0) == expected
    )


def build_achievement_progress(
    history: Sequence[dict],
    unlocked: Dict[str, str],
    completed_lesson_texts: Iterable[Tuple[int, int]],
    lesson_text_counts: Sequence[int],
) -> List[AchievementProgress]:
    """Calculate earned state and progress for every built-in achievement."""
    total_sessions = len(history)
    best_wpm = _best_session_value(history, "wpm")
    best_accuracy = _best_session_value(history, "accuracy")
    longest_streak = compute_streaks(list(history))[1]

    valid_completed: Set[Tuple[int, int]] = {
        (lesson_index, text_index)
        for lesson_index, text_index in completed_lesson_texts
        if 0 <= lesson_index < len(lesson_text_counts)
        and 0 <= text_index < lesson_text_counts[lesson_index]
    }
    curriculum_target = sum(lesson_text_counts)
    curriculum_current = len(valid_completed)

    perfect_runs = _qualifying_session_count(
        history,
        minimum_length=25,
        field="accuracy",
        expected=100.0,
    )
    clean_runs = _qualifying_session_count(
        history,
        minimum_length=50,
        field="errors",
        expected=0.0,
    )
    no_backspace_runs = _qualifying_session_count(
        history,
        minimum_length=50,
        field="backspaces",
        expected=0.0,
    )

    metrics = {
        "first_steps": (total_sessions, 1, f"{total_sessions} / 1 session"),
        "sessions_10": (total_sessions, 10, f"{total_sessions} / 10 sessions"),
        "sessions_50": (total_sessions, 50, f"{total_sessions} / 50 sessions"),
        "wpm_30": (best_wpm, 30, f"Best: {best_wpm:.0f} / 30 WPM"),
        "wpm_50": (best_wpm, 50, f"Best: {best_wpm:.0f} / 50 WPM"),
        "wpm_75": (best_wpm, 75, f"Best: {best_wpm:.0f} / 75 WPM"),
        "perfect_accuracy": (
            perfect_runs,
            1,
            "Completed" if perfect_runs else f"Best accuracy: {best_accuracy:.1f}%",
        ),
        "zero_errors": (clean_runs, 1, "Completed" if clean_runs else "No qualifying run yet"),
        "zero_backspaces": (
            no_backspace_runs,
            1,
            "Completed" if no_backspace_runs else "No qualifying run yet",
        ),
        "streak_3": (longest_streak, 3, f"Best: {longest_streak} / 3 days"),
        "streak_7": (longest_streak, 7, f"Best: {longest_streak} / 7 days"),
        "curriculum_complete": (
            curriculum_current,
            curriculum_target,
            f"{curriculum_current} / {curriculum_target} lesson texts",
        ),
    }

    progress: List[AchievementProgress] = []
    for achievement in ACHIEVEMENTS:
        current, target, progress_text = metrics[achievement.id]
        unlocked_at = unlocked.get(achievement.id)
        progress.append(
            AchievementProgress(
                achievement=achievement,
                earned=bool(unlocked_at) or (target > 0 and current >= target),
                unlocked_at=unlocked_at,
                current=float(current),
                target=float(target),
                progress_text=progress_text,
            )
        )
    return progress
