import pytest

from core.scoring import calculate_accuracy, calculate_wpm


class TestCalculateWpm:
    def test_empty_typed_returns_zero(self):
        assert calculate_wpm("", 60.0, 0, 3) == 0

    def test_none_elapsed_returns_zero(self):
        assert calculate_wpm("hello", None, 0, 3) == 0

    def test_zero_elapsed_returns_zero(self):
        assert calculate_wpm("hello", 0, 0, 3) == 0

    def test_negative_elapsed_returns_zero(self):
        assert calculate_wpm("hello", -1.0, 0, 3) == 0

    def test_basic_wpm_no_penalty(self):
        # 50 chars / 5 = 10 words in 60s = 10 WPM
        assert calculate_wpm("a" * 50, 60.0, 0, 3) == 10

    def test_backspace_penalty_applied(self):
        # 10 raw WPM - (2 backspaces * 3) = 4
        assert calculate_wpm("a" * 50, 60.0, 2, 3) == 4

    def test_penalty_floor_at_zero(self):
        # 10 raw WPM - (100 * 3) = -290, floored to 0
        assert calculate_wpm("a" * 50, 60.0, 100, 3) == 0

    def test_fractional_penalty(self):
        # 10 raw - (4 * 0.5) = 8
        assert calculate_wpm("a" * 50, 60.0, 4, 0.5) == 8


class TestCalculateAccuracy:
    def test_empty_typed_returns_100(self):
        assert calculate_accuracy("", "target", 0, 0, 0.5) == 100.0

    def test_perfect_typing(self):
        assert calculate_accuracy("hello", "hello", 0, 0, 0.5) == 100.0

    def test_mismatch_errors_reduce_accuracy(self):
        # 5 chars typed, 1 mismatch error -> 4/5 = 80%
        assert calculate_accuracy("hello", "hello", 1, 0, 0.5) == 80.0

    def test_overrun_counted_as_error(self):
        # 6 typed vs 5 target -> 1 extra error -> 5/6
        result = calculate_accuracy("helloo", "hello", 0, 0, 0.5)
        assert result == pytest.approx(83.333, abs=0.01)

    def test_backspace_weight(self):
        # 10 typed, 2 backspaces * 0.5 weight = 1 error -> 9/10 = 90%
        assert calculate_accuracy("a" * 10, "a" * 10, 0, 2, 0.5) == 90.0

    def test_errors_floored_at_zero_correct(self):
        # Massive errors shouldn't produce negative accuracy
        result = calculate_accuracy("hi", "hi", 100, 0, 0.5)
        assert result == 0.0
