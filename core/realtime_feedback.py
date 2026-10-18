"""Pure, Qt-independent real-time feedback calculations for mistakes, speed, and rhythm."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from core.constants import KEY_FINGER_MAP
from core.transitions import MAX_TRANSITION_GAP_SECONDS, TextChange

# Rolling window sizes
RHYTHM_WINDOW_SIZE = 12
MIN_RHYTHM_INTERVALS = 3
ROLLING_SPEED_KEYSTROKES = 12
ROLLING_SPEED_MAX_SPAN_SECONDS = 5.0
MIN_ROLLING_KEYSTROKES = 3
MIN_ROLLING_SPAN_SECONDS = 0.25

FINGER_DISPLAY_NAMES: dict[str, str] = {
    "left_pinky": "L.Pinky",
    "left_ring": "L.Ring",
    "left_middle": "L.Mid",
    "left_index": "L.Index",
    "right_index": "R.Index",
    "right_middle": "R.Mid",
    "right_ring": "R.Ring",
    "right_pinky": "R.Pinky",
    "thumbs": "Thumb",
}


def describe_key(char: str) -> str:
    """Return a human-readable key label for a character."""
    if char == " ":
        return "Space"
    if char in ("\n", "\r"):
        return "Enter"
    if char == "\t":
        return "Tab"
    return char


def finger_for_key(char: str) -> Optional[str]:
    """Return the human-readable finger name for pressing *char*, if mapped."""
    if not char:
        return None
    finger_id = KEY_FINGER_MAP.get(char.lower())
    if not finger_id:
        return None
    return FINGER_DISPLAY_NAMES.get(finger_id)


@dataclass(frozen=True)
class MistakeFeedback:
    """Details of the most recent typing mistake."""

    typed_key: str
    expected_key: str
    finger_label: Optional[str]
    message: str


@dataclass(frozen=True)
class RhythmSnapshot:
    """Real-time cadence and consistency assessment."""

    consistency_percent: Optional[int]
    state: str
    last_interval_ms: Optional[float]
    mean_interval_ms: Optional[float]


@dataclass(frozen=True)
class SpeedSnapshot:
    """Real-time burst speed and comparison against lesson best WPM."""

    rolling_wpm: Optional[int]
    best_delta: Optional[int]


def build_mistake_feedback(typed_char: str, expected_char: str) -> MistakeFeedback:
    """Construct a structured MistakeFeedback for a mismatched character."""
    typed_label = describe_key(typed_char)
    expected_label = describe_key(expected_char)
    finger_label = finger_for_key(expected_char)
    if finger_label:
        message = f"Typed '{typed_label}' → expected '{expected_label}' ({finger_label})"
    else:
        message = f"Typed '{typed_label}' → expected '{expected_label}'"
    return MistakeFeedback(
        typed_key=typed_char,
        expected_key=expected_char,
        finger_label=finger_label,
        message=message,
    )


class RealtimeFeedbackTracker:
    """Tracks live keystroke intervals, rolling speed, and active mistake state."""

    def __init__(self, max_gap_seconds: float = MAX_TRANSITION_GAP_SECONDS) -> None:
        self._max_gap_seconds = max_gap_seconds
        self._intervals_ms: Deque[float] = deque(maxlen=RHYTHM_WINDOW_SIZE)
        self._keystroke_times: Deque[float] = deque(maxlen=ROLLING_SPEED_KEYSTROKES)
        self._last_timestamp: Optional[float] = None
        self.last_mistake: Optional[MistakeFeedback] = None

    def reset(self) -> None:
        """Clear all tracked intervals, keystroke timestamps, and mistake state."""
        self._intervals_ms.clear()
        self._keystroke_times.clear()
        self._last_timestamp = None
        self.last_mistake = None

    def record_change(
        self,
        change: TextChange,
        target_text: str,
        timestamp: float,
    ) -> None:
        """Process a user edit to update rhythm intervals, rolling speed, and mistake state."""
        if change.removed > 0 and not change.inserted:
            # Backspace/deletion: break interval chain
            self._last_timestamp = None
            return

        if not change.inserted:
            return

        if len(change.inserted) != 1:
            # Multi-character paste: reset timing continuity
            self._last_timestamp = None
            return

        char = change.inserted
        pos = change.position
        self._keystroke_times.append(timestamp)

        if 0 <= pos < len(target_text):
            expected = target_text[pos]
            if char != expected:
                self.last_mistake = build_mistake_feedback(char, expected)
                self._last_timestamp = timestamp
                return
            self.last_mistake = None
        else:
            # Overrun beyond target length
            self.last_mistake = MistakeFeedback(
                typed_key=char,
                expected_key="",
                finger_label=None,
                message=f"Extra '{describe_key(char)}' beyond target text",
            )
            self._last_timestamp = timestamp
            return

        if self._last_timestamp is not None:
            gap = timestamp - self._last_timestamp
            if 0 < gap <= self._max_gap_seconds:
                self._intervals_ms.append(gap * 1000.0)

        self._last_timestamp = timestamp

    def sync_typed_text(self, typed_text: str, target_text: str) -> None:
        """Keep `last_mistake` consistent with the current tail of `typed_text`."""
        if not typed_text or not target_text:
            self.last_mistake = None
            return

        typed_len = len(typed_text)
        target_len = len(target_text)
        if typed_len > target_len:
            last_char = typed_text[-1]
            self.last_mistake = MistakeFeedback(
                typed_key=last_char,
                expected_key="",
                finger_label=None,
                message=f"Extra '{describe_key(last_char)}' beyond target text",
            )
            return

        last_typed = typed_text[-1]
        expected = target_text[typed_len - 1]
        if last_typed != expected:
            if (
                self.last_mistake is None
                or self.last_mistake.typed_key != last_typed
                or self.last_mistake.expected_key != expected
            ):
                self.last_mistake = build_mistake_feedback(last_typed, expected)
        else:
            self.last_mistake = None

    def rhythm_snapshot(self) -> RhythmSnapshot:
        """Compute live consistency % and cadence state from recent intervals."""
        count = len(self._intervals_ms)
        if count < MIN_RHYTHM_INTERVALS:
            last_ms = self._intervals_ms[-1] if count > 0 else None
            mean_ms = sum(self._intervals_ms) / count if count > 0 else None
            return RhythmSnapshot(
                consistency_percent=None,
                state="--",
                last_interval_ms=last_ms,
                mean_interval_ms=mean_ms,
            )

        intervals = list(self._intervals_ms)
        mean_ms = sum(intervals) / count
        if mean_ms <= 0:
            return RhythmSnapshot(
                consistency_percent=100,
                state="Steady",
                last_interval_ms=intervals[-1],
                mean_interval_ms=0.0,
            )

        variance = sum((val - mean_ms) ** 2 for val in intervals) / count
        std_dev = math.sqrt(variance)
        cv = std_dev / mean_ms
        consistency = max(0, min(100, round((1.0 - cv) * 100)))
        last_ms = intervals[-1]

        if (last_ms > mean_ms * 1.6 and last_ms > 220.0) or consistency < 55:
            state = "Hesitating"
        elif (
            count >= 3
            and intervals[-1] < mean_ms * 0.82
            and intervals[-2] < mean_ms * 0.82
            and consistency >= 60
        ):
            state = "Bursting"
        else:
            state = "Steady"

        return RhythmSnapshot(
            consistency_percent=consistency,
            state=state,
            last_interval_ms=last_ms,
            mean_interval_ms=mean_ms,
        )

    def speed_snapshot(
        self,
        effective_wpm: int,
        best_wpm: Optional[int] = None,
    ) -> SpeedSnapshot:
        """Compute rolling burst WPM and pace delta against `best_wpm`."""
        rolling_wpm: Optional[int] = None
        if len(self._keystroke_times) >= MIN_ROLLING_KEYSTROKES:
            newest = self._keystroke_times[-1]
            # Prune timestamps older than the rolling window span relative to newest
            window_times = [
                t for t in self._keystroke_times
                if (newest - t) <= ROLLING_SPEED_MAX_SPAN_SECONDS
            ]
            if len(window_times) >= MIN_ROLLING_KEYSTROKES:
                span = window_times[-1] - window_times[0]
                if span >= MIN_ROLLING_SPAN_SECONDS:
                    chars = len(window_times) - 1
                    words = chars / 5.0
                    minutes = span / 60.0
                    rolling_wpm = max(0, int(round(words / minutes)))

        best_delta: Optional[int] = None
        if best_wpm is not None and best_wpm > 0 and effective_wpm > 0:
            best_delta = effective_wpm - best_wpm

        return SpeedSnapshot(rolling_wpm=rolling_wpm, best_delta=best_delta)
