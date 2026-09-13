"""Recent-round estimates for the dedicated weak-key drill."""

from collections import Counter
from dataclasses import dataclass

WINDOW_SIZE = 30
MIN_ROUNDS = 5
MIN_ATTEMPTS = 20
FOCUS_COUNT = 5
GROUP_COUNT = 24


@dataclass(frozen=True)
class WeakKey:
    key: str
    errors: int
    attempts: int

    @property
    def score(self) -> float:
        return (self.errors + 1) / (self.attempts + 20)


@dataclass(frozen=True)
class WeakKeyProfile:
    rounds: int
    focus: tuple[WeakKey, ...]
    needs_more_attempts: bool = False


def analyze_weak_keys(rounds: list[dict]) -> WeakKeyProfile:
    """Use complete rounds ordered oldest first, including zero-error keys."""
    recent = rounds[-WINDOW_SIZE:]
    attempts: Counter = Counter()
    errors: Counter = Counter()
    for sample in recent:
        attempts.update(sample["attempts"])
        errors.update(sample["errors"])
    candidates = [
        WeakKey(key, errors[key], count)
        for key, count in attempts.items()
        if len(key) == 1 and key.isprintable() and not key.isspace()
        and count >= MIN_ATTEMPTS and errors[key] > 0
    ]
    candidates.sort(key=lambda item: (-item.score, -item.attempts, item.key))
    needs_more = any(
        len(key) == 1 and key.isprintable() and not key.isspace()
        and errors[key] > 0 and count < MIN_ATTEMPTS
        for key, count in attempts.items()
    )
    return WeakKeyProfile(
        len(recent),
        tuple(candidates[:FOCUS_COUNT]) if len(recent) >= MIN_ROUNDS else (),
        needs_more,
    )
