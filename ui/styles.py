"""Pure stylesheet generation from a Theme.

Kept separate from main_window so style strings can be unit-tested and changed
without touching window construction.
"""

from typing import Dict

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QProgressBar, QWidget

from core.themes import Theme


MIN_TEXT_CONTRAST = 4.5


def _relative_luminance(color: str) -> float:
    """Return WCAG relative luminance for a #RRGGBB color."""
    if len(color) != 7 or not color.startswith("#"):
        raise ValueError(f"Expected #RRGGBB color, got {color!r}")
    try:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    except ValueError as exc:
        raise ValueError(f"Expected #RRGGBB color, got {color!r}") from exc
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float:
    """Return the WCAG contrast ratio between two #RRGGBB colors."""
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def contrasting_text_color(background: str) -> str:
    """Choose black or white, whichever is more readable on *background*."""
    black = "#000000"
    white = "#ffffff"
    return black if contrast_ratio(black, background) >= contrast_ratio(white, background) else white


def accessible_text_color(preferred: str, background: str) -> str:
    """Keep a readable accent; otherwise fall back to contrasting black/white."""
    if contrast_ratio(preferred, background) >= MIN_TEXT_CONTRAST:
        return preferred
    return contrasting_text_color(background)


def darken(color: str, amount: int = 115) -> str:
    """Return *color* darkened by *amount* percent (>100 darkens, per QColor.darker)."""
    return QColor(color).darker(amount).name()


def apply_card_shadow(widget: QWidget, blur: int = 18, y_offset: int = 3, alpha: int = 70) -> None:
    """Give a card-like panel a soft drop shadow for visual depth."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)


def animate_progress_fill(bar: QProgressBar, target: int, duration: int = 450) -> None:
    """Ease a freshly-shown progress bar from 0 up to *target* instead of snapping into view."""
    bar.setValue(0)
    anim = QPropertyAnimation(bar, b"value", bar)
    anim.setDuration(duration)
    anim.setStartValue(0)
    anim.setEndValue(target)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()


def build_main_stylesheet(theme: Theme) -> str:
    return f"""
        QMainWindow, QDialog, QWidget#content, QWidget#sidebar {{
            background-color: {theme.bg_primary};
            color: {theme.text_primary};
        }}
        QLabel {{
            color: {theme.text_primary};
        }}
        QTextEdit {{
            background-color: {theme.input_bg};
            color: {theme.text_primary};
            border: 2px solid {theme.input_border};
        }}
        QListWidget {{
            background-color: {theme.list_bg};
            color: {theme.text_primary};
            border: none;
        }}
        QListWidget::item:selected {{
            background-color: {theme.list_selected};
        }}
        QListWidget#lesson_list {{
            background-color: {theme.bg_primary};
            padding: 2px 8px;
            outline: none;
        }}
        QListWidget#lesson_list::item {{
            background-color: {theme.list_bg};
            color: {theme.text_primary};
            border: 1px solid {theme.target_border};
            border-radius: 6px;
            padding: 4px 10px;
            margin: 1px 0px;
        }}
        QListWidget#lesson_list::item:hover {{
            background-color: {theme.bg_secondary};
            border-color: {theme.list_selected};
        }}
        QListWidget#lesson_list::item:selected {{
            background-color: {theme.list_selected};
            color: {contrasting_text_color(theme.list_selected)};
            border: 1px solid {theme.list_selected};
            border-left: 4px solid {theme.progress_bar_fill};
        }}
        QListWidget#lesson_list::item:disabled {{
            background-color: transparent;
            color: {theme.text_secondary};
            border: none;
            padding: 10px 2px 1px 2px;
        }}
        QPushButton {{
            background-color: {theme.button_bg};
            color: {theme.button_text};
            border: 1px solid {theme.button_border};
        }}
        QPushButton:hover {{
            background-color: {theme.button_hover_bg};
        }}
        QProgressBar {{
            background-color: {theme.progress_bar_bg};
            border: 2px solid {theme.target_border};
            border-radius: 5px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {theme.progress_bar_fill};
        }}
        QGroupBox {{
            color: {theme.text_primary};
            border: 1px solid {theme.button_border};
            border-radius: 4px;
            margin-top: 1.2em;
            padding-top: 0.6em;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 8px;
            padding: 0 4px;
        }}
    """


def build_target_text_style(theme: Theme) -> str:
    return (
        f"padding: 20px; background-color: {theme.target_bg}; "
        f"border: 2px solid {theme.target_border}; border-radius: 8px; "
        f"line-height: 1.8; color: {theme.text_primary};"
    )


def build_stat_label_style(bg_color: str) -> str:
    """Style for the WPM/accuracy/progress/error/backspace/best/timer pills."""
    return (
        "font-size: 16px; font-weight: bold; padding: 8px 12px; "
        f"background-color: {bg_color}; color: {contrasting_text_color(bg_color)}; "
        "border-radius: 5px;"
    )


def build_accent_button_style(bg_color: str) -> str:
    """Style for accent buttons (Next Text, Generate New Words), with hover/pressed feedback.

    A widget's own stylesheet isn't merged with its ancestors', so a button that sets
    one of its own (as these do, to tie their color to a theme accent) must also spell
    out :hover/:pressed itself or it gets no feedback at all.
    """
    text_color = contrasting_text_color(bg_color)
    hover_color = darken(bg_color, 112)
    pressed_color = darken(bg_color, 130)
    return (
        f"QPushButton {{ background-color: {bg_color}; color: {text_color}; "
        "padding: 12px; font-size: 14px; font-weight: bold; border: none; border-radius: 5px; } "
        f"QPushButton:hover {{ background-color: {hover_color}; }} "
        f"QPushButton:pressed {{ background-color: {pressed_color}; }}"
    )


def build_plain_button_style(theme: Theme) -> str:
    """Style for neutral buttons (Reset) that still need explicit :hover/:pressed.

    Mirrors the ancestor QPushButton rule in build_main_stylesheet, since a button
    with its own stylesheet (needed here for padding/font/radius) stops inheriting
    the ancestor's :hover rule.
    """
    pressed_color = darken(theme.button_hover_bg, 115)
    return (
        f"QPushButton {{ background-color: {theme.button_bg}; color: {theme.button_text}; "
        f"border: 1px solid {theme.button_border}; padding: 12px; font-size: 14px; "
        "border-radius: 5px; } "
        f"QPushButton:hover {{ background-color: {theme.button_hover_bg}; }} "
        f"QPushButton:pressed {{ background-color: {pressed_color}; }}"
    )


def build_progress_strip_style(theme: Theme) -> str:
    return (
        f"QFrame#progress_strip {{ background-color: {theme.bg_secondary}; "
        "border-radius: 6px; margin: 0 10px 8px 10px; } "
        "QFrame#progress_strip QLabel { background: transparent; }"
    )


def build_description_styles(theme: Theme) -> Dict[str, str]:
    """Return the {default, success, complete} description styles for a theme."""
    default_text = accessible_text_color(theme.text_primary, theme.description_bg)
    success_text = accessible_text_color(theme.text_primary, theme.description_success_bg)
    complete_text = accessible_text_color(theme.text_primary, theme.description_complete_bg)
    return {
        "default": (
            f"padding: 10px; background-color: {theme.description_bg}; "
            f"border-radius: 5px; font-size: 13px; color: {default_text};"
        ),
        "success": (
            f"padding: 15px; background-color: {theme.description_success_bg}; "
            f"border-radius: 5px; font-size: 14px; font-weight: bold; color: {success_text};"
        ),
        "complete": (
            f"padding: 15px; background-color: {theme.description_complete_bg}; "
            f"border-radius: 5px; font-size: 14px; font-weight: bold; color: {complete_text};"
        ),
    }
