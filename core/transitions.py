"""Pure, Qt-independent bigram/trigram timing capture and aggregation.

Measures elapsed time between adjacent, correctly typed target characters
during manual typing. Stores only expected sequences and duration
aggregates — never raw keystrokes, incorrect input, or full typed text.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, List, Optional

MAX_TRANSITION_GAP_SECONDS = 2.0
MIN_TRANSITION_SAMPLES = 5
TRANSITION_RESULT_LIMIT = 10
_EXCLUDED_CHARACTERS = frozenset({"\n", "\r", "\t"})


@dataclass(frozen=True)
class TextChange:
    position: int
    removed: int
    inserted: str


@dataclass(frozen=True)
class TransitionSample:
    sequence: str
    ngram_size: int
    duration_ms: float


@dataclass(frozen=True)
class TransitionAggregate:
    sequence: str
    ngram_size: int
    sample_count: int
    total_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float


@dataclass(frozen=True)
class TransitionSummary:
    sequence: str
    ngram_size: int
    average_ms: float
    sample_count: int
    baseline_delta_percent: float


@dataclass(frozen=True)
class _TimedCharacter:
    position: int
    character: str
    timestamp: float


class TransitionTracker:
    """Owns round-scoped timing continuity for adjacent correct characters.

    Retains at most the two previous valid timed characters and emits a
    bigram (and, once enough history exists, a trigram) sample for each
    correct single-character insertion that continues the chain.
    """

    def __init__(self, max_gap_seconds: float = MAX_TRANSITION_GAP_SECONDS) -> None:
        self._max_gap_seconds = max_gap_seconds
        self._history: deque[_TimedCharacter] = deque(maxlen=2)

    def reset(self) -> None:
        self._history.clear()

    def record_change(
        self, change: TextChange, target_text: str, timestamp: float,
    ) -> List[TransitionSample]:
        if change.removed > 0:
            self.reset()
            return []

        if not change.inserted:
            return []

        if len(change.inserted) != 1:
            self.reset()
            return []

        character = change.inserted
        position = change.position
        if (
            position < 0
            or position >= len(target_text)
            or character != target_text[position]
            or character in _EXCLUDED_CHARACTERS
        ):
            self.reset()
            return []

        samples: List[TransitionSample] = []
        previous = self._history[-1] if self._history else None
        if previous is not None:
            gap = timestamp - previous.timestamp
            if (
                position != previous.position + 1
                or gap <= 0
                or gap > self._max_gap_seconds
            ):
                self.reset()
                previous = None

        if previous is not None:
            bigram_sequence = previous.character + character
            samples.append(
                TransitionSample(
                    sequence=bigram_sequence,
                    ngram_size=2,
                    duration_ms=gap * 1000.0,
                )
            )
            if len(self._history) == 2:
                first = self._history[0]
                trigram_sequence = first.character + previous.character + character
                trigram_gap = timestamp - first.timestamp
                samples.append(
                    TransitionSample(
                        sequence=trigram_sequence,
                        ngram_size=3,
                        duration_ms=trigram_gap * 1000.0,
                    )
                )

        self._history.append(_TimedCharacter(position, character, timestamp))
        return samples


def aggregate_transition_samples(
    samples: Iterable[TransitionSample],
) -> List[TransitionAggregate]:
    """Group samples by `(ngram_size, sequence)` into deterministic aggregates."""
    grouped: dict[tuple[int, str], List[float]] = {}
    for sample in samples:
        key = (sample.ngram_size, sample.sequence)
        grouped.setdefault(key, []).append(sample.duration_ms)

    aggregates = [
        TransitionAggregate(
            sequence=sequence,
            ngram_size=ngram_size,
            sample_count=len(durations),
            total_duration_ms=sum(durations),
            min_duration_ms=min(durations),
            max_duration_ms=max(durations),
        )
        for (ngram_size, sequence), durations in grouped.items()
    ]
    aggregates.sort(key=lambda aggregate: (aggregate.ngram_size, aggregate.sequence))
    return aggregates


def format_transition_sequence(sequence: str) -> str:
    return sequence.replace(" ", "␠")
