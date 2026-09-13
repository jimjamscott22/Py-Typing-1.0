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
