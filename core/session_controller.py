"""Session lifecycle state and business logic, kept free of Qt.

`TypingPracticeApp` still owns every widget; it hands this controller plain
values (typed text, target text, lesson metadata) read from those widgets
and reacts to the plain results handed back, so no widget reference ever
crosses into this module.
"""

import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional
from uuid import uuid4

from core.achievements import build_achievement_progress
from core.best_wpm import BestWpmTracker
from core.challenges import Challenge, evaluate_challenge_progress, get_daily_challenge
from core.constants import DAILY_CHALLENGE_COIN_REWARD, SESSION_COIN_REWARD
from core.models import SessionRecord, TypingSession
from core.persistence import ProgressStore
from core.scoring import calculate_accuracy, calculate_wpm


@dataclass
class EditOutcome:
    """What happened to session state after one input-box change."""

    just_began: bool
    just_completed: bool


@dataclass
class FinalizeResult:
    """Everything the window needs to render a just-finished round."""

    wpm: int
    accuracy: float
    elapsed_seconds: float
    backspace_count: int
    wpm_penalty: float
    timed_out: bool
    newly_unlocked_ids: List[str] = field(default_factory=list)
    completed_challenge: Optional[Challenge] = None
    best_wpm_improved: bool = False


class SessionController:
    """Owns the in-progress `TypingSession` and the reset/completion lifecycle."""

    def __init__(
        self,
        progress_store: ProgressStore,
        best_wpm: BestWpmTracker,
        backspace_penalty: float,
        backspace_accuracy_weight: float,
    ) -> None:
        self.progress_store = progress_store
        self.best_wpm = best_wpm
        self.backspace_penalty = backspace_penalty
        self.backspace_accuracy_weight = backspace_accuracy_weight
        self.session = TypingSession()
        self.round_complete = False
        self._weak_round_id = str(uuid4())
        self._weak_round_saved = False

    def reset(self) -> None:
        """Clear session state for a fresh round."""
        self.session.reset()
        self._weak_round_id = str(uuid4())
        self._weak_round_saved = False
        self.round_complete = False

    def update_typed_text(self, typed_text: str, target_text: str) -> EditOutcome:
        """Mirror the input box into session state and detect start/completion."""
        self.session.typed_text = typed_text
        self.session.errors = sum(
            actual != expected for actual, expected in zip(typed_text, target_text)
        )
        just_began = False
        if not self.session.is_active and typed_text:
            self.session.begin()
            just_began = True
        just_completed = (
            not self.round_complete
            and bool(target_text)
            and typed_text == target_text
        )
        return EditOutcome(just_began=just_began, just_completed=just_completed)

    def record_edit(self, insertions: list, target_text: str) -> None:
        """Record per-character attempt/error stats for newly inserted text."""
        for start, inserted in insertions:
            for offset, char in enumerate(inserted):
                index = start + offset
                if index < len(target_text):
                    expected = target_text[index]
                    self.session.record_key_attempt(expected)
                    if char != expected:
                        self.session.record_key_error(expected)

    def save_weak_key_round(
        self, mode: str, warmup_mode: bool, answer_imported: bool, lesson_index: int,
    ) -> None:
        """Persist this round's per-key stats once, for weak-key drill generation."""
        if (
            mode != "lesson"
            or warmup_mode
            or answer_imported
            or self._weak_round_saved
            or not self.session.key_attempts
        ):
            return
        self.progress_store.record_weak_key_round(
            self._weak_round_id, datetime.now().isoformat(), lesson_index,
            self.session.key_errors, self.session.key_attempts,
        )
        self._weak_round_saved = True

    def sync_achievements(self, lesson_text_counts: List[int]) -> List[str]:
        """Persist any achievements newly earned by recorded progress."""
        unlocked = self.progress_store.get_unlocked_achievements()
        statuses = build_achievement_progress(
            self.progress_store.get_session_history(),
            unlocked,
            self.progress_store.get_completed_lesson_texts(),
            lesson_text_counts,
        )
        earned_ids = [
            status.achievement.id
            for status in statuses
            if status.earned and status.achievement.id not in unlocked
        ]
        if not earned_ids:
            return []
        return self.progress_store.unlock_achievements(
            earned_ids, datetime.now().isoformat(),
        )

    def sync_daily_challenge(self) -> Optional[Challenge]:
        """Award coins once when today's challenge is newly completed."""
        today_str = date.today().isoformat()
        if self.progress_store.is_challenge_completed(today_str):
            return None

        today = date.today()
        challenge = get_daily_challenge(today)
        progress = evaluate_challenge_progress(
            challenge, self.progress_store.get_session_history(), today,
        )
        if not progress.completed:
            return None

        newly_recorded = self.progress_store.mark_challenge_completed(
            today_str, challenge.id, datetime.now().isoformat(),
            coin_reward=DAILY_CHALLENGE_COIN_REWARD,
        )
        if not newly_recorded:
            return None
        return challenge

    def finalize(
        self,
        *,
        timed_out: bool,
        target_text: str,
        mode: str,
        warmup_mode: bool,
        answer_imported: bool,
        lesson_index: int,
        text_index: int,
        lesson_name: str,
        lesson_text_counts: List[int],
    ) -> FinalizeResult:
        """Score the just-finished round and persist it, unless in warmup mode."""
        elapsed_seconds = (
            time.time() - self.session.start_time if self.session.start_time else 0.0
        )
        wpm = calculate_wpm(
            typed=self.session.typed_text,
            elapsed_seconds=elapsed_seconds,
            backspace_count=self.session.backspace_count,
            penalty_factor=self.backspace_penalty,
        )
        accuracy = calculate_accuracy(
            typed=self.session.typed_text,
            target=target_text,
            mismatch_errors=self.session.errors,
            backspace_count=self.session.backspace_count,
            backspace_weight=self.backspace_accuracy_weight,
        )
        self.round_complete = True

        backspace_count = self.session.backspace_count
        wpm_penalty = backspace_count * self.backspace_penalty

        newly_unlocked_ids: List[str] = []
        completed_challenge: Optional[Challenge] = None
        best_wpm_improved = False

        if not warmup_mode:
            self.save_weak_key_round(mode, warmup_mode, answer_imported, lesson_index)

            record = SessionRecord(
                timestamp=datetime.now().isoformat(),
                lesson_index=lesson_index if mode == "lesson" else -1,
                text_index=text_index,
                lesson_name=lesson_name,
                wpm=wpm,
                accuracy=round(accuracy, 1),
                errors=self.session.errors + max(
                    len(self.session.typed_text) - len(target_text), 0
                ),
                backspaces=backspace_count,
                duration_seconds=round(elapsed_seconds, 1),
                text_length=(
                    len(self.session.typed_text) if timed_out else len(target_text)
                ),
            )
            self.progress_store.add_session_record(record)

            if mode == "lesson" and not timed_out:
                self.progress_store.mark_lesson_text_completed(
                    lesson_index, text_index, record.timestamp,
                )

            if self.session.key_errors:
                self.progress_store.update_key_error_stats(self.session.key_errors)
            if self.session.key_attempts:
                self.progress_store.update_key_attempt_stats(self.session.key_attempts)

            if self.session.key_errors:
                self.progress_store.add_session_key_stats(
                    record.timestamp, record.lesson_index, lesson_name,
                    self.session.key_errors, self.session.key_attempts,
                )

            if mode == "lesson":
                best_wpm_improved = self.best_wpm.update(str(lesson_index), wpm)
                if best_wpm_improved:
                    self.progress_store.data["best_wpm"] = self.best_wpm.to_dict()

            newly_unlocked_ids = self.sync_achievements(lesson_text_counts)
            self.progress_store.add_coins(SESSION_COIN_REWARD)
            completed_challenge = self.sync_daily_challenge()
            self.progress_store.save()

        return FinalizeResult(
            wpm=wpm,
            accuracy=accuracy,
            elapsed_seconds=elapsed_seconds,
            backspace_count=backspace_count,
            wpm_penalty=wpm_penalty,
            timed_out=timed_out,
            newly_unlocked_ids=newly_unlocked_ids,
            completed_challenge=completed_challenge,
            best_wpm_improved=best_wpm_improved,
        )
