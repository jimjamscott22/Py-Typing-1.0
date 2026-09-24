"""QTextCharFormat presets for the typing input widget."""

from dataclasses import dataclass

from PyQt6.QtGui import QColor, QTextCharFormat

from core.themes import Theme
from ui.styles import contrasting_text_color


@dataclass
class InputFormats:
    default: QTextCharFormat
    correct: QTextCharFormat
    error: QTextCharFormat
    extra: QTextCharFormat


def make_input_formats(theme: Theme) -> InputFormats:
    """Build the four character formats used to highlight typed text."""
    default = QTextCharFormat()

    correct = QTextCharFormat()
    correct.setForeground(QColor(contrasting_text_color(theme.description_success_bg)))
    correct.setBackground(QColor(theme.description_success_bg))

    error = QTextCharFormat()
    error.setForeground(QColor(contrasting_text_color(theme.error_bg)))
    error.setBackground(QColor(theme.error_bg))
    error.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)

    extra = QTextCharFormat()
    extra.setForeground(QColor(contrasting_text_color(theme.best_bg)))
    extra.setBackground(QColor(theme.best_bg))

    return InputFormats(default=default, correct=correct, error=error, extra=extra)
