import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set

from core.transitions import TransitionSample

@dataclass(frozen=True)
class Lesson:
    title: str
    description: str
    texts: List[str]
    category: str = ""  # Sidebar section heading
    # False for optional lessons (code snippets) that must not count toward
    # the "finish the curriculum" achievement.
    curriculum: bool = True


@dataclass(frozen=True)
class Snippet:
    """One piece of code to type: a language, a difficulty tier and its text."""
    language: str
    difficulty: str
    title: str
    text: str


@dataclass
class TypingSession:
    """Tracks the state of a single typing practice session."""
    typed_text: str = ""
    start_time: Optional[float] = None
    errors: int = 0
    is_active: bool = False
    backspace_count: int = 0  # Track backspace usage
    key_errors: Dict[str, int] = field(default_factory=dict)  # Track errors per key
    key_attempts: Dict[str, int] = field(default_factory=dict)  # Track attempts per key
    transition_samples: List[TransitionSample] = field(default_factory=list)
    # Typed-text indexes filled in automatically (indentation after Enter);
    # excluded from every statistic because the user never pressed those keys.
    auto_filled: Set[int] = field(default_factory=set)

    def reset(self) -> None:
        self.typed_text = ""
        self.start_time = None
        self.errors = 0
        self.is_active = False
        self.backspace_count = 0
        self.key_errors = {}
        self.key_attempts = {}
        self.transition_samples = []
        self.auto_filled = set()

    def register_auto_fill(self, start: int, length: int) -> None:
        """Mark `length` characters starting at `start` as auto-filled."""
        self.auto_filled.update(range(start, start + length))

    def is_auto_filled(self, index: int) -> bool:
        return index in self.auto_filled

    @property
    def auto_filled_count(self) -> int:
        return len(self.auto_filled)

    def keystroke_length(self, typed_len: int) -> int:
        """Characters of `typed_len` the user actually typed."""
        return typed_len - sum(1 for pos in self.auto_filled if pos < typed_len)

    def prune_auto_fill(self, typed_len: int) -> None:
        """Forget auto-filled positions that no longer exist in the typed text."""
        self.auto_filled = {pos for pos in self.auto_filled if pos < typed_len}

    def note_edit(self, position: int, removed: int, inserted_len: int = 0) -> None:
        """Keep auto-fill positions pointing at the same characters after an edit.

        Positions inside the removed range disappear; positions after it move by
        the net length change. Typed replacements are never auto-filled.
        """
        if not self.auto_filled:
            return
        end = position + removed
        delta = inserted_len - removed
        self.auto_filled = {
            pos if pos < position else pos + delta
            for pos in self.auto_filled
            if pos < position or pos >= end
        }

    def begin(self) -> None:
        self.is_active = True
        self.start_time = time.time()

    def record_key_error(self, expected_key: str) -> None:
        """Record an error for a specific key."""
        if expected_key:
            self.key_errors[expected_key] = self.key_errors.get(expected_key, 0) + 1

    def record_key_attempt(self, expected_key: str) -> None:
        """Record a keystroke attempt for a specific key (correct or not)."""
        if expected_key:
            self.key_attempts[expected_key] = self.key_attempts.get(expected_key, 0) + 1


@dataclass
class SessionRecord:
    """A completed session record for statistics tracking."""
    timestamp: str
    lesson_index: int
    text_index: int
    lesson_name: str
    wpm: int
    accuracy: float
    errors: int
    backspaces: int
    duration_seconds: float
    text_length: int
