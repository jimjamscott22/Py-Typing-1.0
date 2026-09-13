"""Tests for SessionController — pure session lifecycle logic, no Qt required."""

from pathlib import Path

import pytest

from core.best_wpm import BestWpmTracker
from core.persistence import ProgressStore
from core.session_controller import SessionController


@pytest.fixture
def controller(tmp_path: Path) -> SessionController:
    store = ProgressStore(tmp_path / "typing_progress.json")
    best_wpm = BestWpmTracker.from_raw(store.data.get("best_wpm"))
    return SessionController(store, best_wpm, backspace_penalty=2, backspace_accuracy_weight=1.0)


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
        controller.record_edit([(0, "hx")], "hello")
        assert controller.session.key_attempts == {"h": 1, "e": 1}
        assert controller.session.key_errors == {"e": 1}

    def test_insertions_past_target_length_are_ignored(self, controller: SessionController):
        controller.record_edit([(0, "hello!!!")], "hello")
        assert sum(controller.session.key_attempts.values()) == 5


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
