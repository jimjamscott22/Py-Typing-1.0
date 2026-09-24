"""Pure stylesheet generation from a Theme.

Kept separate from main_window so style strings can be unit-tested and changed
without touching window construction.
"""

from typing import Dict

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
    """Style for accent buttons (Next Text, Generate New Words) tied to a theme color."""
    return (
        f"background-color: {bg_color}; color: {contrasting_text_color(bg_color)}; padding: 12px; "
        "font-size: 14px; font-weight: bold; border-radius: 5px;"
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
