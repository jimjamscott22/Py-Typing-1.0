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
