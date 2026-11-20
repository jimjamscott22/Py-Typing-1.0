"""Headless window tests for auto-filled indentation after Enter."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QMimeData, Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from core.scoring import calculate_wpm
from ui.main_window import TypingPracticeApp

TARGET = "if x:\n    y()"


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    win = TypingPracticeApp()
    yield win
    win.close()


def set_target(window, text):
    window.current_target_text = text
    window.reset_exercise()


def type_first_line(window):
    QTest.keyClicks(window.typing_input, "if x:")
    QTest.keyClick(window.typing_input, Qt.Key.Key_Return)


def test_enter_auto_fills_indent(window):
    set_target(window, TARGET)
    type_first_line(window)
    assert window.typing_input.toPlainText() == "if x:\n    "
    assert window.session.typed_text == "if x:\n    "


def test_round_completes_with_auto_filled_indent(window):
    set_target(window, TARGET)
    type_first_line(window)
    QTest.keyClicks(window.typing_input, "y()")
    assert window._round_complete is True


def test_auto_fill_not_counted_in_attempts_errors_or_transitions(window):
    set_target(window, TARGET)
    type_first_line(window)
    QTest.keyClicks(window.typing_input, "y()")
    assert window.session.key_attempts.get(" ") == 1  # only the real space
    assert window.session.key_errors == {}
    assert all("  " not in s.sequence for s in window.session.transition_samples)


def test_text_length_and_wpm_use_keystroke_characters(window):
    set_target(window, TARGET)
    type_first_line(window)
    QTest.keyClicks(window.typing_input, "y()")
    row = window.progress_store.get_session_history()[-1]
    assert row["text_length"] == len(TARGET) - 4
    expected = calculate_wpm("x" * (len(TARGET) - 4), 60.0, 0, window._backspace_penalty)
    assert window._calculate_wpm(window.session.typed_text, elapsed=60.0) == expected


def test_backspace_over_auto_fill_is_not_penalised(window):
    set_target(window, TARGET)
    type_first_line(window)
    for _ in range(4):
        QTest.keyClick(window.typing_input, Qt.Key.Key_Backspace)
    assert window.session.backspace_count == 0
    QTest.keyClick(window.typing_input, Qt.Key.Key_Backspace)  # deletes the newline
    assert window.session.backspace_count == 1


def test_no_auto_fill_in_free_practice(window):
    set_target(window, TARGET)
    window.mode = "free"
    type_first_line(window)
    assert window.typing_input.toPlainText() == "if x:\n"


def test_paste_is_not_auto_filled(window):
    set_target(window, TARGET)
    mime = QMimeData()
    mime.setText("if x:\n")
    window.typing_input.insertFromMimeData(mime)
    assert window.typing_input.toPlainText() == "if x:\n"


def test_interior_edit_before_fill_keeps_stats_sane(window):
    set_target(window, TARGET)
    type_first_line(window)
    cursor = window.typing_input.textCursor()
    cursor.setPosition(0)
    window.typing_input.setTextCursor(cursor)
    QTest.keyClicks(window.typing_input, "z")
    typed = window.session.typed_text
    assert window.session.auto_filled == set()
    assert window.session.keystroke_length(len(typed)) == len(typed)
