"""Regression tests for readable, theme-aware semantic colors."""

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication

from core.lessons import build_lessons
from core.persistence import ProgressStore
from core.themes import THEMES
from ui.dialogs import AchievementsDialog, ChallengesDialog, SettingsDialog, StatisticsDialog
from ui.formats import make_input_formats
from ui import styles


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def _luminance(color: str) -> float:
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize("theme", THEMES.values(), ids=lambda theme: theme.name)
def test_semantic_backgrounds_get_readable_black_or_white_text(theme):
    backgrounds = (
        theme.wpm_bg,
        theme.accuracy_bg,
        theme.progress_bg,
        theme.error_bg,
        theme.backspace_bg,
        theme.best_bg,
        theme.button_bg,
        theme.description_success_bg,
    )

    for background in backgrounds:
        foreground = styles.contrasting_text_color(background)
        assert foreground in {"#000000", "#ffffff"}
        assert _contrast(foreground, background) >= 4.5


@pytest.mark.parametrize("theme", THEMES.values(), ids=lambda theme: theme.name)
def test_stat_and_accent_styles_use_contrasting_text(theme):
    expected = f"color: {styles.contrasting_text_color(theme.wpm_bg)}"

    assert expected in styles.build_stat_label_style(theme.wpm_bg)
    assert expected in styles.build_accent_button_style(theme.wpm_bg)


@pytest.mark.parametrize("theme", THEMES.values(), ids=lambda theme: theme.name)
def test_description_styles_use_readable_text(theme):
    description_styles = styles.build_description_styles(theme)
    backgrounds = {
        "default": theme.description_bg,
        "success": theme.description_success_bg,
        "complete": theme.description_complete_bg,
    }

    for name, background in backgrounds.items():
        expected = styles.accessible_text_color(theme.text_primary, background)
        assert f"color: {expected}" in description_styles[name]


def test_accessible_text_keeps_readable_accent_and_replaces_low_contrast_accent():
    assert styles.accessible_text_color("#005fcc", "#ffffff") == "#005fcc"
    assert styles.accessible_text_color("#6272a4", "#44475a") == "#ffffff"


@pytest.mark.parametrize("theme", THEMES.values(), ids=lambda theme: theme.name)
def test_input_feedback_formats_follow_theme_with_readable_text(theme):
    formats = make_input_formats(theme)
    cases = (
        (formats.correct, theme.description_success_bg),
        (formats.error, theme.error_bg),
        (formats.extra, theme.best_bg),
    )

    for text_format, expected_background in cases:
        foreground = text_format.foreground().color().name()
        background = text_format.background().color().name()
        assert background == expected_background.lower()
        assert _contrast(foreground, background) >= 4.5


@pytest.mark.parametrize("theme", THEMES.values(), ids=lambda theme: theme.name)
def test_dialogs_paint_the_background_used_for_contrast(qapp, tmp_path: Path, theme):
    store = ProgressStore(tmp_path / f"{theme.name}.json")
    store.set_setting("theme", theme.name)
    lessons = build_lessons()
    dialogs = (
        StatisticsDialog(store, lessons),
        AchievementsDialog(store, lessons),
        ChallengesDialog(store),
        SettingsDialog(store),
    )

    try:
        for dialog in dialogs:
            dialog.ensurePolished()
            actual = dialog.palette().color(QPalette.ColorRole.Window).name()
            assert actual == theme.bg_primary.lower()
    finally:
        for dialog in dialogs:
            dialog.close()
        store.close()


@pytest.mark.parametrize("theme", THEMES.values(), ids=lambda theme: theme.name)
def test_secondary_text_is_readable_on_dialog_backgrounds(theme):
    for background in (theme.bg_primary, theme.bg_secondary):
        color = styles.secondary_text_color(theme, background)
        assert _contrast(color, background) >= 4.5


def test_secondary_text_keeps_theme_color_when_readable():
    theme = THEMES["Dark"]
    assert styles.secondary_text_color(theme, theme.bg_primary) == theme.text_secondary


@pytest.mark.parametrize("theme", THEMES.values(), ids=lambda theme: theme.name)
def test_form_controls_are_themed(qapp, theme):
    """Checkbox labels, inputs, tabs and tables must not fall back to the light
    system palette (unreadable on dark themes)."""
    sheet = styles.build_main_stylesheet(theme)
    for selector in ("QCheckBox", "QComboBox", "QSpinBox", "QTabBar::tab", "QHeaderView::section"):
        assert selector in sheet
    assert f"color: {theme.text_primary};" in sheet


@pytest.mark.parametrize("kind", ["up", "down", "check"])
def test_indicator_images_are_generated(qapp, kind):
    path = Path(styles.indicator_image_path(kind, "#123456"))
    assert path.is_file()
    assert path.stat().st_size > 0
