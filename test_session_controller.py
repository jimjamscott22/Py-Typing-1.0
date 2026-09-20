"""Tests for SessionController — pure session lifecycle logic, no Qt required."""

from pathlib import Path

import pytest

from core.best_wpm import BestWpmTracker
from core.persistence import ProgressStore
from core.session_controller import SessionController
from core.transitions import TextChange, TransitionSample


class FakeClock:
    """Deterministic monotonic-style clock driven by a fixed sequence of ticks."""

    def __init__(self, ticks):
        self._ticks = iter(ticks)

    def __call__(self) -> float:
        return next(self._ticks)


@pytest.fixture
def controller(tmp_path: Path) -> SessionController:
    store = ProgressStore(tmp_path / "typing_progress.json")
    best_wpm = BestWpmTracker.from_raw(store.data.get("best_wpm"))
    return SessionController(store, best_wpm, backspace_penalty=2, backspace_accuracy_weight=1.0)


def make_controller(tmp_path: Path, ticks=None) -> SessionController:
    store = ProgressStore(tmp_path / "typing_progress.json")
    best_wpm = BestWpmTracker.from_raw(store.data.get("best_wpm"))
    kwargs = {}
    if ticks is not None:
        kwargs["transition_clock"] = FakeClock(ticks)
    return SessionController(
        store, best_wpm, backspace_penalty=2, backspace_accuracy_weight=1.0, **kwargs
    )


class TestReset:
    def test_reset_clears_session_and_round_complete(self, controller: SessionController):
        controller.session.typed_text = "abc"
        controller.session.begin()
        controller.round_complete = True

        controller.reset()

        assert controller.session.typed_text == ""
        assert not controller.session.is_active
        assert not controller.round_complete

    def test_reset_issues_a_fresh_weak_round_id(self, controller: SessionController):
        first_id = controller._weak_round_id
        controller._weak_round_saved = True

        controller.reset()

        assert controller._weak_round_id != first_id
        assert not controller._weak_round_saved


class TestUpdateTypedText:
    def test_first_keystroke_begins_the_session(self, controller: SessionController):
        outcome = controller.update_typed_text("h", "hello")
        assert outcome.just_began
        assert controller.session.is_active

    def test_subsequent_keystroke_does_not_rebegin(self, controller: SessionController):
        controller.update_typed_text("h", "hello")
        outcome = controller.update_typed_text("he", "hello")
        assert not outcome.just_began

    def test_matching_target_reports_completion(self, controller: SessionController):
        controller.update_typed_text("hell", "hello")
        outcome = controller.update_typed_text("hello", "hello")
        assert outcome.just_completed

    def test_already_complete_round_does_not_report_again(self, controller: SessionController):
        controller.update_typed_text("hello", "hello")
        controller.round_complete = True
        outcome = controller.update_typed_text("hello", "hello")
        assert not outcome.just_completed

    def test_empty_target_never_completes(self, controller: SessionController):
        outcome = controller.update_typed_text("", "")
        assert not outcome.just_completed

    def test_errors_counted_by_position(self, controller: SessionController):
        controller.update_typed_text("hxllo", "hello")
        assert controller.session.errors == 1


class TestRecordEdit:
    def test_correct_and_incorrect_chars_tracked_per_key(self, controller: SessionController):
        controller.record_edit([TextChange(0, 0, "hx")], "hello")
        assert controller.session.key_attempts == {"h": 1, "e": 1}
        assert controller.session.key_errors == {"e": 1}

    def test_insertions_past_target_length_are_ignored(self, controller: SessionController):
        controller.record_edit([TextChange(0, 0, "hello!!!")], "hello")
        assert sum(controller.session.key_attempts.values()) == 5

    def test_multi_character_insertion_records_attempts_but_no_timing(
        self, controller: SessionController,
    ):
        controller.record_edit([TextChange(0, 0, "he")], "hello")
        assert sum(controller.session.key_attempts.values()) == 2
        assert controller.session.transition_samples == []

    def test_adjacent_correct_single_char_edits_produce_transition_samples(
        self, tmp_path: Path,
    ):
        controller = make_controller(tmp_path, ticks=[10.000, 10.090, 10.205])
        controller.record_edit([TextChange(0, 0, "i")], "ion")
        controller.record_edit([TextChange(1, 0, "o")], "ion")
        controller.record_edit([TextChange(2, 0, "n")], "ion")

        sequences = [s.sequence for s in controller.session.transition_samples]
        assert sequences == ["io", "on", "ion"]

    def test_deletion_resets_transition_continuity(self, tmp_path: Path):
        controller = make_controller(tmp_path, ticks=[10.000, 10.090, 10.200])
        controller.record_edit([TextChange(0, 0, "i")], "ion")
        controller.record_edit([TextChange(0, 1, "")], "ion")
        controller.record_edit([TextChange(0, 0, "i")], "ion")

        assert controller.session.transition_samples == []

    def test_reset_clears_transition_continuity(self, tmp_path: Path):
        controller = make_controller(tmp_path, ticks=[10.000, 20.000])
        controller.record_edit([TextChange(0, 0, "i")], "ion")
        controller.reset()
        controller.session.typed_text = ""
        controller.record_edit([TextChange(1, 0, "o")], "ion")

        assert controller.session.transition_samples == []

    def test_key_attempt_and_error_totals_unchanged_by_timing_capture(
        self, tmp_path: Path,
    ):
        controller = make_controller(tmp_path, ticks=[1.0, 2.0, 3.0, 4.0, 5.0])
        for index, char in enumerate("hxllo"):
            controller.record_edit([TextChange(index, 0, char)], "hello")

        assert controller.session.key_attempts == {"h": 1, "e": 1, "l": 2, "o": 1}
        assert controller.session.key_errors == {"e": 1}


class TestSaveWeakKeyRound:
    def test_records_once_per_round(self, controller: SessionController):
        controller.session.key_attempts = {"a": 5}
        controller.session.key_errors = {"a": 2}

        controller.save_weak_key_round("lesson", False, False, lesson_index=0)
        controller.save_weak_key_round("lesson", False, False, lesson_index=0)

        assert len(controller.progress_store.get_weak_key_rounds()) == 1

    def test_skips_in_warmup_mode(self, controller: SessionController):
        controller.session.key_attempts = {"a": 5}
        controller.save_weak_key_round("lesson", True, False, lesson_index=0)
        assert controller.progress_store.get_weak_key_rounds() == []


class TestFinalize:
    def test_lesson_completion_persists_a_session_record(self, controller: SessionController):
        controller.session.typed_text = "hello"
        controller.session.begin()

        result = controller.finalize(
            timed_out=False,
            target_text="hello",
            mode="lesson",
            warmup_mode=False,
            answer_imported=False,
            lesson_index=0,
            text_index=0,
            lesson_name="Home Row",
            lesson_text_counts=[1],
        )

        assert controller.round_complete
        history = controller.progress_store.get_session_history()
        assert len(history) == 1
        assert history[0]["lesson_name"] == "Home Row"
        assert result.wpm >= 0

    def test_warmup_mode_skips_persistence(self, controller: SessionController):
        controller.session.typed_text = "hello"
        controller.session.begin()

        controller.finalize(
            timed_out=False,
            target_text="hello",
            mode="warmup",
            warmup_mode=True,
            answer_imported=False,
            lesson_index=0,
            text_index=0,
            lesson_name="Warmup",
            lesson_text_counts=[],
        )

        assert controller.progress_store.get_session_history() == []

    def test_best_wpm_improvement_is_reported(self, controller: SessionController):
        controller.session.typed_text = "hello"
        controller.session.begin()
        controller.session.start_time -= 1  # ensure elapsed > 0 for a nonzero WPM

        result = controller.finalize(
            timed_out=False,
            target_text="hello",
            mode="lesson",
            warmup_mode=False,
            answer_imported=False,
            lesson_index=2,
            text_index=0,
            lesson_name="Numbers",
            lesson_text_counts=[1, 1, 1],
        )

        assert result.best_wpm_improved
        assert controller.best_wpm.get("2") == result.wpm

    def test_best_wpm_synced_to_progress_store_on_improvement(self, controller: SessionController):
        """Verify that improved best_wpm is synced to progress_store.data within finalize()."""
        controller.session.typed_text = "hello"
        controller.session.begin()
        controller.session.start_time -= 1  # ensure elapsed > 0 for a nonzero WPM

        result = controller.finalize(
            timed_out=False,
            target_text="hello",
            mode="lesson",
            warmup_mode=False,
            answer_imported=False,
            lesson_index=1,
            text_index=0,
            lesson_name="Second Lesson",
            lesson_text_counts=[1, 1],
        )

        assert result.best_wpm_improved
        # Verify the new WPM is immediately in progress_store.data
        assert controller.progress_store.data["best_wpm"].get("1") == result.wpm


class TestFinalizeTransitions:
    def test_normal_lesson_completion_persists_transition_aggregates(
        self, controller: SessionController,
    ):
        controller.session.typed_text = "hello"
        controller.session.begin()
        controller.session.transition_samples = [
            TransitionSample(sequence="he", ngram_size=2, duration_ms=100.0),
            TransitionSample(sequence="he", ngram_size=2, duration_ms=120.0),
        ]

        controller.finalize(
            timed_out=False,
            target_text="hello",
            mode="lesson",
            warmup_mode=False,
            answer_imported=False,
            lesson_index=0,
            text_index=0,
            lesson_name="Home Row",
            lesson_text_counts=[1],
        )

        assert controller.progress_store.has_transition_data()
        summaries = controller.progress_store.get_slowest_transitions(2, min_samples=1)
        assert summaries[0].sequence == "he"
        assert summaries[0].sample_count == 2
        assert summaries[0].average_ms == pytest.approx(110.0)

    def test_warmup_completion_does_not_persist_transitions(
        self, controller: SessionController,
    ):
        controller.session.typed_text = "hello"
        controller.session.begin()
        controller.session.transition_samples = [
            TransitionSample(sequence="he", ngram_size=2, duration_ms=100.0),
        ]

        controller.finalize(
            timed_out=False,
            target_text="hello",
            mode="warmup",
            warmup_mode=True,
            answer_imported=False,
            lesson_index=0,
            text_index=0,
            lesson_name="Warmup",
            lesson_text_counts=[],
        )

        assert not controller.progress_store.has_transition_data()

    def test_answer_imported_completion_discards_transition_samples(
        self, controller: SessionController,
    ):
        controller.session.typed_text = "hello"
        controller.session.begin()
        controller.session.transition_samples = [
            TransitionSample(sequence="he", ngram_size=2, duration_ms=100.0),
        ]

        controller.finalize(
            timed_out=False,
            target_text="hello",
            mode="lesson",
            warmup_mode=False,
            answer_imported=True,
            lesson_index=0,
            text_index=0,
            lesson_name="Home Row",
            lesson_text_counts=[1],
        )

        # Ordinary history is still recorded; transition data is not.
        assert len(controller.progress_store.get_session_history()) == 1
        assert not controller.progress_store.has_transition_data()

    def test_empty_normal_session_still_exercises_retention_pruning(
        self, controller: SessionController,
    ):
        controller.session.typed_text = "hello"
        controller.session.begin()

        controller.finalize(
            timed_out=False,
            target_text="hello",
            mode="lesson",
            warmup_mode=False,
            answer_imported=False,
            lesson_index=0,
            text_index=0,
            lesson_name="Home Row",
            lesson_text_counts=[1],
        )

        assert not controller.progress_store.has_transition_data()
        assert len(controller.progress_store.get_session_history()) == 1
