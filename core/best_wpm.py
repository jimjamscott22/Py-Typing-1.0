"""Per-lesson best-WPM tracker.

Wraps the dict that lives under `data["best_wpm"]` in `typing_progress.json`,
encapsulating the load/update/serialize logic.
"""

from typing import Dict, Mapping


class BestWpmTracker:
    """Maps a string lesson key to the user's best recorded WPM."""

    def __init__(self, scores: Dict[str, int]) -> None:
        self._scores = scores

    @classmethod
    def from_raw(cls, raw: object) -> "BestWpmTracker":
        """Build from arbitrary persisted JSON, ignoring malformed entries."""
        scores: Dict[str, int] = {}
        if isinstance(raw, Mapping):
            for key, value in raw.items():
                if isinstance(value, (int, float)):
                    scores[str(key)] = int(value)
        return cls(scores)

    def get(self, lesson_key: str) -> int:
        return self._scores.get(lesson_key, 0)

    def update(self, lesson_key: str, wpm: int) -> bool:
        """Set a new best if `wpm` exceeds the existing one. Returns True if updated."""
        if wpm > self._scores.get(lesson_key, 0):
            self._scores[lesson_key] = wpm
            return True
        return False

    def to_dict(self) -> Dict[str, int]:
        return dict(self._scores)
