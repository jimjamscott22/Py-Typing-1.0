"""The typing area copes with multi-line (code snippet) targets at the default size."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QApplication

from core.constants import TERMINAL_MAX_LINES, TERMINAL_MIN_HEIGHT
from core.snippets import MAX_COLUMNS, SNIPPETS
from ui.main_window import TypingPracticeApp

# A 1080p screen minus a title bar and taskbar leaves about this much window height.
MAX_WINDOW_HEIGHT = 1010


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


def frame_cap(window):
    return max(TERMINAL_MIN_HEIGHT, TERMINAL_MAX_LINES * spacing(window) + 44)


def test_single_line_keeps_minimum_height_and_prompt(window):
    show_target(window, "one line")
    assert window.terminal_frame.maximumHeight() == TERMINAL_MIN_HEIGHT == 150
    assert not window.terminal_prompt_label.isHidden()


def test_multi_line_targets_hide_the_prompt_to_free_width(window):
    show_target(window, lines(3))
    assert window.terminal_prompt_label.isHidden()
    show_target(window, "one line")
    assert not window.terminal_prompt_label.isHidden()


def test_frame_grows_for_the_capped_number_of_lines(window):
    show_target(window, lines(TERMINAL_MAX_LINES))
    height = window.terminal_frame.maximumHeight()
    assert height == max(TERMINAL_MIN_HEIGHT, TERMINAL_MAX_LINES * spacing(window) + 44)
    assert height > TERMINAL_MIN_HEIGHT


def test_thirty_lines_are_capped(window):
    show_target(window, lines(30))
    assert window.terminal_frame.maximumHeight() == frame_cap(window)


def test_returns_to_minimum_for_single_line_again(window):
    show_target(window, lines(TERMINAL_MAX_LINES))
    show_target(window, "one line")
    assert window.terminal_frame.maximumHeight() == TERMINAL_MIN_HEIGHT


def test_font_size_change_refits(window):
    window.progress_store.set_setting("font_size", 12)
    window._apply_settings()
    show_target(window, lines(TERMINAL_MAX_LINES))
    small = window.terminal_frame.maximumHeight()

    window.progress_store.set_setting("font_size", 28)
    window._apply_settings()
    window.update_display()
    assert window.terminal_frame.maximumHeight() > small


def test_frame_actually_grows_when_shown(window, qapp):
    show_target(window, lines(TERMINAL_MAX_LINES))
    window.show()
    qapp.processEvents()
    assert window.terminal_frame.height() >= TERMINAL_MAX_LINES * spacing(window) + 44


def test_longest_real_snippet_fits_a_1080p_window(window, qapp):
    longest = max(SNIPPETS, key=lambda s: s.text.count("\n"))
    window.resize(1100, 850)
    window.show()
    show_target(window, longest.text)
    qapp.processEvents()
    assert window.minimumSizeHint().height() <= MAX_WINDOW_HEIGHT


def test_widest_real_snippet_line_wraps_nowhere(window, qapp):
    widest = max(
        (line for s in SNIPPETS for line in s.text.split("\n")), key=len,
    )
    assert len(widest) <= MAX_COLUMNS
    snippet = next(s for s in SNIPPETS if widest in s.text.split("\n"))
    window.resize(1100, 850)
    window.show()
    show_target(window, snippet.text)
    qapp.processEvents()
    advance = QFontMetrics(window.typing_input.font()).horizontalAdvance(widest)
    document_margin = int(window.typing_input.document().documentMargin() * 2)
    assert advance <= window.typing_input.viewport().width() - document_margin
    assert advance <= window.target_text.contentsRect().width()
