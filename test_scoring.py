"""Tests for core/scoring.py."""

import pytest

from core.scoring import calculate_wpm, calculate_accuracy


class TestCalculateWpm:
    def test_empty_typed_returns_zero(self):
        assert calculate_wpm("", 60.0, 0, 3) == 0

    def test_none_elapsed_returns_zero(self):
        assert calculate_wpm("hello world", None, 0, 3) == 0

    def test_zero_elapsed_returns_zero(self):
        assert calculate_wpm("hello world", 0, 0, 3) == 0

    def test_basic_wpm(self):
        # 10 chars = 2 words in 1 minute => 2 WPM raw
        assert calculate_wpm("a" * 10, 60.0, 0, 3) == 2

    def test_backspace_penalty_floors_at_zero(self):
        wpm = calculate_wpm("a" * 50, 60.0, backspace_count=100, penalty_factor=3)
        assert wpm == 0

    def test_backspace_penalty_subtracted(self):
        wpm = calculate_wpm("a" * 50, 60.0, backspace_count=2, penalty_factor=3)
        assert wpm == 4  # 10 raw - 6 penalty

    def test_fractional_minutes(self):
        # 25 chars in 30s => 10 WPM raw
        assert calculate_wpm("a" * 25, 30.0, 0, 3) == 10


class TestCalculateAccuracy:
    def test_empty_typed_returns_100(self):
        assert calculate_accuracy("", "target", 0, 0, 0.5) == 100.0

    def test_perfect_match(self):
        assert calculate_accuracy("abc", "abc", mismatch_errors=0, backspace_count=0, backspace_weight=0.5) == 100.0

    def test_mismatch_errors_reduce_accuracy(self):
        acc = calculate_accuracy("abc", "abc", mismatch_errors=1, backspace_count=0, backspace_weight=0.5)
        assert acc == pytest.approx(66.666, rel=0.01)

    def test_extra_chars_beyond_target(self):
        acc = calculate_accuracy("abcd", "abc", mismatch_errors=0, backspace_count=0, backspace_weight=0.5)
        assert acc == 75.0

    def test_backspace_weight(self):
        acc = calculate_accuracy("abc", "abc", mismatch_errors=0, backspace_count=2, backspace_weight=0.5)
        assert acc == pytest.approx(66.666, rel=0.01)

    def test_combined_penalties(self):
        acc = calculate_accuracy(
            "abcd",
            "abc",
            mismatch_errors=1,
            backspace_count=2,
            backspace_weight=1.0,
        )
        # total errors = 1 mismatch + 1 extra + 2 backspace = 4; correct = 0
        assert acc == 0.0
