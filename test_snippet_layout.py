"""The typing frame grows to fit multi-line (code snippet) targets."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QApplication

from core.constants import TERMINAL_MAX_LINES, TERMINAL_MIN_HEIGHT
from ui.main_window import TypingPracticeApp


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    win = TypingPracticeApp()
    yield win
    win.close()


def show_target(window, text):
    window.current_target_text = text
    window.reset_exercise()
    window.update_display()


def spacing(window):
    return QFontMetrics(window.typing_input.font()).lineSpacing()


def lines(count):
    return "\n".join(f"line {i}" for i in range(count))


def test_single_line_keeps_minimum_height(window):
    show_target(window, "one line")
    assert window.terminal_frame.maximumHeight() == TERMINAL_MIN_HEIGHT == 150


def test_eight_lines_grow(window):
    show_target(window, lines(8))
    height = window.terminal_frame.maximumHeight()
    assert height > TERMINAL_MIN_HEIGHT
    assert height >= 8 * spacing(window) + 44


def test_thirty_lines_are_capped(window):
    show_target(window, lines(30))
    assert window.terminal_frame.maximumHeight() == TERMINAL_MAX_LINES * spacing(window) + 44


def test_returns_to_minimum_for_single_line_again(window):
    show_target(window, lines(8))
    show_target(window, "one line")
    assert window.terminal_frame.maximumHeight() == TERMINAL_MIN_HEIGHT


def test_font_size_change_refits(window):
    window.progress_store.set_setting("font_size", 12)
    window._apply_settings()
    show_target(window, lines(8))
    small = window.terminal_frame.maximumHeight()

    window.progress_store.set_setting("font_size", 28)
    window._apply_settings()
    window.update_display()
    assert window.terminal_frame.maximumHeight() > small


def test_frame_actually_grows_when_shown(window, qapp):
    show_target(window, lines(8))
    window.show()
    qapp.processEvents()
    assert window.terminal_frame.height() >= 8 * spacing(window) + 44
