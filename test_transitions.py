"""Tests for the pure bigram/trigram timing module (no Qt required)."""

import pytest

from core.transitions import (
    MAX_TRANSITION_GAP_SECONDS,
    TextChange,
    TransitionAggregate,
    TransitionSample,
    TransitionTracker,
    aggregate_transition_samples,
    format_transition_sequence,
)


class TestTransitionTracker:
    def test_sequential_correct_chars_produce_bigram_and_trigram(self):
        tracker = TransitionTracker()
        assert tracker.record_change(TextChange(0, 0, "i"), "ion", 10.000) == []

        io = tracker.record_change(TextChange(1, 0, "o"), "ion", 10.090)
        assert io[0].sequence == "io"
        assert io[0].ngram_size == 2
        assert io[0].duration_ms == pytest.approx(90.0)

        on_and_ion = tracker.record_change(TextChange(2, 0, "n"), "ion", 10.205)
        assert [sample.sequence for sample in on_and_ion] == ["on", "ion"]
        assert on_and_ion[0].ngram_size == 2
        assert on_and_ion[1].ngram_size == 3
        assert on_and_ion[0].duration_ms == pytest.approx(115.0)
        assert on_and_ion[1].duration_ms == pytest.approx(205.0)

    def test_first_character_establishes_anchor_with_no_sample(self):
        tracker = TransitionTracker()
        assert tracker.record_change(TextChange(0, 0, "h"), "hello", 1.0) == []

    def test_wrong_character_resets_continuity(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "h"), "hello", 1.0)
        assert tracker.record_change(TextChange(1, 0, "x"), "hello", 1.05) == []
        # Continuity was reset, so the next correct char is a fresh anchor.
        assert tracker.record_change(TextChange(2, 0, "l"), "hello", 1.10) == []

    def test_correction_does_not_bridge_across_the_error(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "h"), "hello", 1.0)
        tracker.record_change(TextChange(1, 0, "x"), "hello", 1.05)
        # Backspace over the wrong char, then type the correct one.
        tracker.record_change(TextChange(1, 1, ""), "hello", 1.10)
        samples = tracker.record_change(TextChange(1, 0, "e"), "hello", 1.15)
        assert samples == []

    def test_deletion_resets_continuity(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "h"), "hello", 1.0)
        assert tracker.record_change(TextChange(0, 1, ""), "hello", 1.05) == []
        assert tracker.record_change(TextChange(0, 0, "h"), "hello", 1.10) == []

    def test_selection_replacement_resets_continuity(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "h"), "hello", 1.0)
        # A replacement carries removed > 0 alongside the inserted text.
        assert tracker.record_change(TextChange(0, 1, "h"), "hello", 1.05) == []

    def test_non_adjacent_insertion_resets_continuity(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "h"), "hello", 1.0)
        assert tracker.record_change(TextChange(2, 0, "l"), "hello", 1.05) == []

    def test_multi_character_insertion_resets_continuity(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "h"), "hello", 1.0)
        assert tracker.record_change(TextChange(1, 0, "el"), "hello", 1.05) == []
        assert tracker.record_change(TextChange(3, 0, "l"), "hello", 1.10) == []

    def test_gap_over_two_seconds_excluded_and_restarts_chain(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "h"), "hello", 0.0)
        samples = tracker.record_change(
            TextChange(1, 0, "e"), "hello", MAX_TRANSITION_GAP_SECONDS + 0.5,
        )
        assert samples == []

    def test_gap_exactly_at_limit_is_valid(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "h"), "hello", 0.0)
        samples = tracker.record_change(
            TextChange(1, 0, "e"), "hello", MAX_TRANSITION_GAP_SECONDS,
        )
        assert len(samples) == 1

    def test_no_change_edit_neither_samples_nor_resets(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "h"), "hello", 1.0)
        assert tracker.record_change(TextChange(1, 0, ""), "hello", 1.05) == []
        samples = tracker.record_change(TextChange(1, 0, "e"), "hello", 1.10)
        assert len(samples) == 1

    def test_case_and_punctuation_preserved(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "H"), "Hi, there!", 1.0)
        samples = tracker.record_change(TextChange(1, 0, "i"), "Hi, there!", 1.05)
        assert samples[0].sequence == "Hi"

        tracker2 = TransitionTracker()
        tracker2.record_change(TextChange(2, 0, ","), "Hi, there!", 1.0)
        samples2 = tracker2.record_change(TextChange(3, 0, " "), "Hi, there!", 1.05)
        assert samples2[0].sequence == ", "

    def test_spaces_are_tracked(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "a"), "a b", 1.0)
        samples = tracker.record_change(TextChange(1, 0, " "), "a b", 1.05)
        assert samples[0].sequence == "a "

    def test_control_whitespace_excluded(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "a"), "a\tb", 1.0)
        assert tracker.record_change(TextChange(1, 0, "\t"), "a\tb", 1.05) == []

    def test_reset_clears_history(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "i"), "ion", 10.0)
        tracker.reset()
        assert tracker.record_change(TextChange(1, 0, "o"), "ion", 10.05) == []

    def test_position_outside_target_resets(self):
        tracker = TransitionTracker()
        tracker.record_change(TextChange(0, 0, "h"), "hi", 1.0)
        assert tracker.record_change(TextChange(5, 0, "x"), "hi", 1.05) == []


class TestAggregation:
    def test_aggregates_count_total_min_max(self):
        samples = [
            TransitionSample(sequence="io", ngram_size=2, duration_ms=90.0),
            TransitionSample(sequence="io", ngram_size=2, duration_ms=110.0),
            TransitionSample(sequence="on", ngram_size=2, duration_ms=50.0),
        ]
        aggregates = aggregate_transition_samples(samples)
        io_agg = next(a for a in aggregates if a.sequence == "io")
        assert io_agg.sample_count == 2
        assert io_agg.total_duration_ms == pytest.approx(200.0)
        assert io_agg.min_duration_ms == pytest.approx(90.0)
        assert io_agg.max_duration_ms == pytest.approx(110.0)

    def test_aggregates_are_deterministically_ordered(self):
        samples = [
            TransitionSample(sequence="ion", ngram_size=3, duration_ms=200.0),
            TransitionSample(sequence="on", ngram_size=2, duration_ms=100.0),
            TransitionSample(sequence="io", ngram_size=2, duration_ms=90.0),
        ]
        aggregates = aggregate_transition_samples(samples)
        assert [(a.ngram_size, a.sequence) for a in aggregates] == [
            (2, "io"), (2, "on"), (3, "ion"),
        ]

    def test_empty_input_produces_no_aggregates(self):
        assert aggregate_transition_samples([]) == []


class TestFormatting:
    def test_visible_space_formatting(self):
        assert format_transition_sequence("a b") == "a␠b"

    def test_no_spaces_unchanged(self):
        assert format_transition_sequence("ion") == "ion"
