"""Window-level tests for snippet lessons."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from ui.main_window import SECTION_ROLE, TypingPracticeApp


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    win = TypingPracticeApp()
    yield win
    win.close()


def test_timed_mode_with_snippet_lesson_does_not_crash(window):
    window.progress_store.set_setting("timed_mode_seconds", 60)
    window._apply_settings()
    index = next(i for i, lesson in enumerate(window.lessons) if not lesson.curriculum)
    window.load_lesson(index)
    target = window.current_target_text
    QTest.keyClicks(window.typing_input, target[0])
    assert window.current_target_text == target


def test_achievements_dialog_ignores_snippets_in_curriculum_progress(window):
    from PyQt6.QtWidgets import QLabel

    from ui.dialogs import AchievementsDialog

    dialog = AchievementsDialog(window.progress_store, window.lessons, window)
    texts = [label.text() for label in dialog.findChildren(QLabel)]
    progress = [t for t in texts if "lesson texts" in t]
    assert progress, "the curriculum badge should show its progress"
    assert all("/ 62 lesson texts" in t for t in progress)


def test_sidebar_lists_snippet_sections(window):
    sections = {
        window.lesson_list.item(row).data(SECTION_ROLE)
        for row in range(window.lesson_list.count())
    }
    assert {"TypeScript", "JavaScript", "Python"} <= sections
