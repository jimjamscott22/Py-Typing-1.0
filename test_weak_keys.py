"""Regression checks for complete recent-round learning and real typing input."""

import os
from collections import Counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import Qt, QMimeData, QPointF
from PyQt6.QtGui import QDropEvent, QTextCursor, QInputMethodEvent, QTextDocument
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from core.lessons import build_lessons
from core.persistence import ProgressStore
from core.weak_keys import analyze_weak_keys
from core.wordgen import generate_weak_key_text
from ui.main_window import TypingPracticeApp


def sample(errors=None, attempts=None):
    return {"errors": errors or {}, "attempts": attempts or {"a": 4}}


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    win = TypingPracticeApp()
    win.progress_store.set_setting("show_celebration", False)
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


def set_target(window, text):
    window.current_target_text = text
    window.reset_exercise()


def seed(window, errors=None, attempts=None):
    for index in range(5):
        window.progress_store.record_weak_key_round(
            f"seed-{index}", f"2026-09-10T10:00:0{index}", 0,
            errors if errors is not None else {"a": 1},
            attempts if attempts is not None else {"a": 4},
        )


def test_unlock_thresholds_and_successes_lower_score():
    rounds = [sample({"a": 1}) for _ in range(4)]
    assert not analyze_weak_keys(rounds).focus
    rounds.append(sample())
    focus = analyze_weak_keys(rounds).focus[0]
    assert (focus.key, focus.errors, focus.attempts) == ("a", 4, 20)
    assert focus.score == 5 / 40
    improved = analyze_weak_keys(rounds + [sample(attempts={"a": 100})]).focus[0]
    assert improved.score < focus.score
    under = analyze_weak_keys([sample({"a": 1}, {"a": 3})] * 5)
    assert not under.focus and under.needs_more_attempts


def test_ranking_uses_rates_not_error_totals_and_stable_ties():
    rounds = [sample()] * 4 + [sample(
        {"q": 5, "e": 10, "x": 3, "y": 1, "b": 1, "c": 1},
        {"q": 20, "e": 400, "x": 60, "y": 20, "b": 20, "c": 20},
    )]
    assert [item.key for item in analyze_weak_keys(rounds).focus] == ["q", "x", "b", "c", "y"]


def test_case_symbols_and_window_eviction():
    initial = sample({"A": 4, "a": 2, "<": 3, "7": 1, " ": 20, "\n": 10},
                     {"A": 20, "a": 20, "<": 20, "7": 20, " ": 20, "\n": 20})
    profile = analyze_weak_keys([initial] + [sample()] * 4)
    assert {item.key for item in profile.focus} == {"A", "a", "<", "7"}
    assert not analyze_weak_keys([initial] + [sample()] * 30).focus


def test_persistence_retains_complete_rounds_and_preserves_legacy(tmp_path):
    path = tmp_path / "typing_progress.json"
    store = ProgressStore(path)
    store.update_key_error_stats({"q": 12})
    store.update_key_attempt_stats({"q": 100})
    store.data["current_lesson_index"] = 16
    store.save()
    assert store.get_weak_key_rounds() == []
    for index in range(32):
        store.record_weak_key_round(str(index), str(index), 0, {}, {"a": 20})
    store.record_weak_key_round("31", "duplicate", 0, {"a": 19}, {"a": 20})
    reloaded = ProgressStore(path)
    rounds = reloaded.get_weak_key_rounds()
    assert len(rounds) == 30
    assert rounds[0]["round_id"] == "2"
    assert rounds[-1]["errors"] == {} and rounds[-1]["attempts"] == {"a": 20}
    assert reloaded.get_key_error_stats() == {"q": 12}
    assert reloaded.get_key_attempt_stats() == {"q": 100}
    assert reloaded.data["current_lesson_index"] == 16
    store._conn.close()
    reloaded._conn.close()


@pytest.mark.parametrize("keys", [["a"], ["Q", "a", "<", "&", "7"], ["!", "8"]])
def test_generator_mixes_sequences_and_words_and_covers_focus(keys):
    groups = generate_weak_key_text(keys).split()
    assert len(groups) == 24
    sequence_chars = "".join(groups[::2])
    assert set(sequence_chars) == set(keys)
    assert all(3 <= len(group) <= 4 for group in groups[::2])
    assert all(any(char.isalpha() for char in group) for group in groups[1::2])
    assert set(keys) <= set("".join(groups[1::2]))
    assert generate_weak_key_text([]) == ""
    assert generate_weak_key_text(keys, 0) == ""


def test_final_character_saved_synchronously_and_render_does_not_count(window):
    set_target(window, "ab")
    QTest.keyClicks(window.typing_input, "ab")
    rounds = window.progress_store.get_weak_key_rounds()
    assert len(rounds) == 1 and rounds[0]["attempts"] == {"a": 1, "b": 1}
    assert rounds[0]["errors"] == {}
    for _ in range(3):
        window.update_display()
    window.on_completion()
    assert len(window.progress_store.get_weak_key_rounds()) == 1
    assert window.session.key_attempts == {"a": 1, "b": 1}


def test_correction_keeps_error_and_counts_retyping(window):
    set_target(window, "ab")
    QTest.keyClicks(window.typing_input, "x")
    QTest.keyClick(window.typing_input, Qt.Key.Key_Backspace)
    QTest.keyClicks(window.typing_input, "ab")
    row = window.progress_store.get_weak_key_rounds()[0]
    assert row["attempts"] == {"a": 2, "b": 1}
    assert row["errors"] == {"a": 1}


def test_same_length_selection_replacement_and_unchanged_replacement(window):
    set_target(window, "abc")
    QTest.keyClicks(window.typing_input, "xb")
    window.update_display()
    cursor = window.typing_input.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(1, QTextCursor.MoveMode.KeepAnchor)
    window.typing_input.setTextCursor(cursor)
    QTest.keyClicks(window.typing_input, "a")
    window.update_display()
    assert window._cached_target_styles[:2] == ["correct", "correct"]
    cursor.setPosition(0)
    cursor.setPosition(1, QTextCursor.MoveMode.KeepAnchor)
    window.typing_input.setTextCursor(cursor)
    QTest.keyClicks(window.typing_input, "a")
    assert window.session.key_attempts == {"a": 3, "b": 1}
    assert window.session.key_errors == {"a": 1}


def test_programmatic_loading_reset_and_deletion_add_no_attempts(window):
    set_target(window, "abcd")
    window.typing_input.setPlainText("ab")
    window.update_display()
    assert window.session.key_attempts == {}
    QTest.keyClick(window.typing_input, Qt.Key.Key_Backspace)
    assert window.session.key_attempts == {}
    window.reset_exercise()
    assert window.session.key_attempts == {}
    assert window.progress_store.get_weak_key_rounds() == []


@pytest.mark.parametrize("advance", ["next", "space"])
def test_finished_error_round_learns_without_completion_rewards(window, advance):
    set_target(window, "ab")
    window._strict_mode = True
    QTest.keyClicks(window.typing_input, "ax")
    if advance == "next":
        window.next_text()
    else:
        QTest.keyClick(window.typing_input, Qt.Key.Key_Space)
    row = window.progress_store.get_weak_key_rounds()[0]
    assert row["errors"] == {"b": 1} and row["attempts"] == {"a": 1, "b": 1}
    assert window.progress_store.get_session_history() == []
    assert window.progress_store.get_coins_total() == 0
    assert window.progress_store.get_completed_lesson_texts() == set()


def test_partial_abandoned_round_is_excluded(window):
    set_target(window, "abcd")
    QTest.keyClicks(window.typing_input, "ax")
    window.next_text()
    assert window.progress_store.get_weak_key_rounds() == []


@pytest.mark.parametrize("method", ["keyboard", "paste", "mime", "drop"])
def test_imported_answers_are_excluded(window, qapp, method):
    set_target(window, "abc")
    QTest.keyClicks(window.typing_input, "a")
    mime = QMimeData()
    mime.setText("b")
    if method in {"keyboard", "paste"}:
        qapp.clipboard().setText("b")
        if method == "keyboard":
            QTest.keyClick(window.typing_input, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        else:
            window.typing_input.paste()
    elif method == "mime":
        window.typing_input.insertFromMimeData(mime)
    else:
        event = QDropEvent(QPointF(2, 2), Qt.DropAction.CopyAction, mime,
                           Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        window.typing_input.dropEvent(event)
    assert window._answer_imported
    # Finish through the common timed boundary regardless of drop position.
    window.on_timed_completion()
    assert window.progress_store.get_weak_key_rounds() == []


@pytest.mark.parametrize("mode", ["free", "warmup"])
def test_non_lesson_modes_do_not_train(window, mode):
    if mode == "free":
        window._enter_free_practice()
    else:
        window._toggle_warmup_mode(True)
    set_target(window, "ab")
    QTest.keyClicks(window.typing_input, "ab")
    assert window.progress_store.get_weak_key_rounds() == []


def test_timed_finish_learns_the_typed_prefix(window):
    window._timed_mode_seconds = 60
    set_target(window, "abcdef")
    QTest.keyClicks(window.typing_input, "ax")
    window.on_timed_completion()
    row = window.progress_store.get_weak_key_rounds()[0]
    assert row["attempts"] == {"a": 1, "b": 1} and row["errors"] == {"b": 1}
    assert window.progress_store.get_session_history()[-1]["errors"] == 1


def test_drill_is_appended_and_collection_state_disables_typing(window):
    lessons = build_lessons()
    assert lessons[16].title == "Developer Keys"
    assert lessons[17].title == "Weak Key Practice"
    window.load_lesson(17)
    assert "0/5" in window.lesson_description.text()
    assert window.typing_input.isReadOnly()
    assert not window.next_button.isEnabled()
    assert window.current_target_text == ""
    QTest.keyClicks(window.typing_input, "abc")
    assert not window.session.key_attempts
    window.load_lesson(0)
    assert not window.typing_input.isReadOnly()
    assert window.next_button.isEnabled()


@pytest.mark.parametrize("errors,attempts,expected", [
    ({"a": 1}, {"a": 3}, "More practice needed"),
    ({}, {"a": 4}, "No eligible mistakes"),
])
def test_empty_focus_explains_reason(window, errors, attempts, expected):
    seed(window, errors, attempts)
    window.load_lesson(17)
    assert expected in window.lesson_description.text()
    assert window.typing_input.isReadOnly()


def test_ready_drill_reset_regeneration_and_completion_learn(window):
    seed(window, {"<": 1, "A": 1}, {"<": 4, "A": 4})
    window._adaptive_drills = False
    window.load_lesson(17)
    target = window.current_target_text
    assert len(target.split()) == 24 and not window.typing_input.isReadOnly()
    assert "&lt;" in window.lesson_description.text()
    assert "5/20" in window.lesson_description.text()
    assert window.regenerate_button.text() == "Generate New Drill"
    window.reset_exercise()
    assert window.current_target_text == target
    prior_id = window._weak_round_id
    window.regenerate_generated_text()
    assert window._weak_round_id != prior_id
    QTest.keyClicks(window.typing_input, window.current_target_text)
    assert len(window.progress_store.get_weak_key_rounds()) == 6
    assert window.progress_store.get_weak_key_rounds()[-1]["attempts"] == dict(Counter(window.current_target_text))
    assert window.progress_store.get_coins_total() >= 5
    QTest.keyClick(window.typing_input, Qt.Key.Key_Space)
    assert window.current_lesson_index == 17 and not window._round_complete
    assert window._weak_profile.rounds == 6
    assert window.typing_input.toPlainText() == ""


def test_timed_extension_keeps_focus_and_does_not_count_generated_text(window):
    seed(window)
    window._timed_mode_seconds = 60
    window.load_lesson(17)
    before = window.current_target_text
    profile = window._weak_profile
    window.progress_store.record_weak_key_round("new-focus", "now", 1, {"z": 20}, {"z": 20})
    window._extend_timed_target()
    assert window.current_target_text.startswith(before + " ")
    assert window._weak_profile == profile
    assert "z" not in "".join(window.current_target_text[len(before):].split()[::2])
    assert window.session.key_attempts == {}
    window.regenerate_generated_text()
    assert window._weak_profile.focus[0].key == "z"


def test_timed_target_displays_current_and_upcoming_groups(window):
    seed(window)
    window._timed_mode_seconds = 60
    window.load_lesson(17)
    target = window.current_target_text
    doc = QTextDocument()
    rendered, _ = window._build_target_highlight(target, "")
    doc.setHtml(rendered)
    assert doc.toPlainText().split() == target.split()[:24]
    typed = " ".join(target.split()[:13]) + " "
    rendered, _ = window._build_target_highlight(target, typed)
    doc.setHtml(rendered)
    assert doc.toPlainText().split() == target.split()[12:36]


def test_unicode_input_method_offsets_are_character_based(window):
    set_target(window, "\U0001f642ab")
    event = QInputMethodEvent()
    event.setCommitString("\U0001f642")
    QApplication.sendEvent(window.typing_input, event)
    QTest.keyClicks(window.typing_input, "ab")
    assert window.progress_store.get_weak_key_rounds()[0]["attempts"] == {"\U0001f642": 1, "a": 1, "b": 1}
