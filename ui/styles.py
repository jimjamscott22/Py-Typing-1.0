"""Pure stylesheet generation from a Theme.

Kept separate from main_window so style strings can be unit-tested and changed
without touching window construction.
"""

from typing import Dict

from core.themes import Theme


def build_main_stylesheet(theme: Theme) -> str:
    return f"""
        QMainWindow, QWidget#content, QWidget#sidebar {{
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


def build_description_styles(theme: Theme) -> Dict[str, str]:
    """Return the {default, success, complete} description styles for a theme."""
    return {
        "default": (
            f"padding: 10px; background-color: {theme.description_bg}; "
            f"border-radius: 5px; font-size: 13px; color: {theme.text_primary};"
        ),
        "success": (
            f"padding: 15px; background-color: {theme.description_success_bg}; "
            f"border-radius: 5px; font-size: 14px; font-weight: bold; color: {theme.text_primary};"
        ),
        "complete": (
            f"padding: 15px; background-color: {theme.description_complete_bg}; "
            f"border-radius: 5px; font-size: 14px; font-weight: bold; color: {theme.text_primary};"
        ),
    }
