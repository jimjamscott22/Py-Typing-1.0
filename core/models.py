import time
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class Lesson:
    title: str
    description: str
    texts: List[str]


@dataclass
class TypingSession:
    """Tracks the state of a single typing practice session."""
    typed_text: str = ""
    start_time: Optional[float] = None
    errors: int = 0
    is_active: bool = False
    backspace_count: int = 0  # Track backspace usage

    def reset(self) -> None:
        self.typed_text = ""
        self.start_time = None
        self.errors = 0
        self.is_active = False
        self.backspace_count = 0

    def begin(self) -> None:
        self.is_active = True
        self.start_time = time.time()


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
