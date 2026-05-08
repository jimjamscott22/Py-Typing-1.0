"""QTextCharFormat presets for the typing input widget."""

from dataclasses import dataclass

from PyQt6.QtGui import QColor, QTextCharFormat


@dataclass
class InputFormats:
    default: QTextCharFormat
    correct: QTextCharFormat
    error: QTextCharFormat
    extra: QTextCharFormat


def make_input_formats() -> InputFormats:
    """Build the four character formats used to highlight typed text."""
    default = QTextCharFormat()

    correct = QTextCharFormat()
    correct.setForeground(QColor("#2e7d32"))
    correct.setBackground(QColor("#c8e6c9"))

    error = QTextCharFormat()
    error.setForeground(QColor("#c62828"))
    error.setBackground(QColor("#ffcdd2"))
    error.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)

    extra = QTextCharFormat()
    extra.setForeground(QColor("#6a1b9a"))
    extra.setBackground(QColor("#f3e5f5"))

    return InputFormats(default=default, correct=correct, error=error, extra=extra)
