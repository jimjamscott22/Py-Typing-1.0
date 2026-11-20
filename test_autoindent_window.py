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


def move_cursor(window, position=None):
    cursor = window.typing_input.textCursor()
    if position is None:
        cursor.movePosition(cursor.MoveOperation.End)
    else:
        cursor.setPosition(position)
    window.typing_input.setTextCursor(cursor)


NESTED = "def f(x):\n    if x:\n        return 1\n    return 0"  # 49 chars, 16 auto-filled


def test_interior_edit_before_fill_keeps_stats_exact(window):
    set_target(window, NESTED)
    QTest.keyClicks(window.typing_input, "def f(x):")
    QTest.keyClick(window.typing_input, Qt.Key.Key_Return)
    QTest.keyClicks(window.typing_input, "if x:")
    QTest.keyClick(window.typing_input, Qt.Key.Key_Return)
    before = set(window.session.auto_filled)
    assert len(before) == 12  # 4 + 8 spaces filled so far

    move_cursor(window, 0)  # click back to the start and type something
    QTest.keyClicks(window.typing_input, "z")
    assert window.session.auto_filled == {p + 1 for p in before}  # shifted, not lost
    QTest.keyClick(window.typing_input, Qt.Key.Key_Backspace)
    assert window.session.auto_filled == before

    move_cursor(window)  # back to the end and finish the snippet
    QTest.keyClicks(window.typing_input, "return 1")
    QTest.keyClick(window.typing_input, Qt.Key.Key_Return)
    QTest.keyClicks(window.typing_input, "return 0")
    assert window._round_complete is True
    assert window.progress_store.get_session_history()[-1]["text_length"] == len(NESTED) - 16


def test_backspace_in_typed_text_after_the_fill_is_penalised(window):
    set_target(window, TARGET)
    type_first_line(window)  # "if x:\n" + 4 filled spaces
    move_cursor(window, 3)  # just after "if "
    QTest.keyClick(window.typing_input, Qt.Key.Key_Backspace)  # deletes a typed space
    assert window.session.backspace_count == 1


def test_backspace_over_the_fill_after_more_typing_is_free(window):
    set_target(window, "if x:\n    y()\nz")
    type_first_line(window)
    QTest.keyClicks(window.typing_input, "y()")
    move_cursor(window, 10)  # just after the filled indentation
    QTest.keyClick(window.typing_input, Qt.Key.Key_Backspace)  # deletes a filled space
    assert window.session.backspace_count == 0
