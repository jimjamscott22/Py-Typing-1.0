"""Pure stylesheet generation from a Theme.

Kept separate from main_window so style strings can be unit-tested and changed
without touching window construction.
"""

import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Dict

from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPalette, QPen, QPolygonF
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


@lru_cache(maxsize=None)
def indicator_image_path(kind: str, color: str) -> str:
    """Return a stylesheet-ready path to a small "up"/"down" arrow or "check" PNG.

    Once a spin box, combo box or checkbox indicator is restyled in a stylesheet,
    Qt stops drawing its native arrow/tick, so we supply images. They're
    generated on demand in *color* (no asset files to bundle) and cached in the
    temp directory. Drawn at 2x so they stay crisp on HiDPI screens.
    """
    sizes = {"up": (20, 12), "down": (20, 12), "check": (24, 24)}
    if kind not in sizes:
        raise ValueError(f"Unknown indicator kind: {kind!r}")
    width, height = sizes[kind]
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if kind == "check":
        pen = QPen(QColor(color), 3.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(QPolygonF([QPointF(5, 12.5), QPointF(10, 17.5), QPointF(19, 6.5)]))
    else:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        if kind == "up":
            points = [QPointF(0, height), QPointF(width / 2, 0), QPointF(width, height)]
        else:
            points = [QPointF(0, 0), QPointF(width, 0), QPointF(width / 2, height)]
        painter.drawPolygon(QPolygonF(points))
    painter.end()

    folder = Path(tempfile.gettempdir()) / "py_typing_ui"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{kind}_{color.lstrip('#').lower()}.png"
    image.save(str(path), "PNG")
    return path.as_posix()


def secondary_text_color(theme: Theme, background: str) -> str:
    """Muted text color for hints/captions that still meets the contrast minimum.

    Some themes (e.g. Dracula, Monokai) pick a secondary text color that is too
    dim to read on their own backgrounds, so fall back to the primary text color,
    and finally to black/white.
    """
    for candidate in (theme.text_secondary, theme.text_primary):
        if contrast_ratio(candidate, background) >= MIN_TEXT_CONTRAST:
            return candidate
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


def apply_theme_palette(widget: QWidget, theme: Theme) -> None:
    """Give a top-level widget a palette that matches *theme*.

    Stylesheets cover most of the UI, but parts Qt still draws natively (spin box
    and combo box arrows, checkbox ticks, scroll corners) read their colors from
    the palette, which otherwise stays the light system default.
    """
    palette = widget.palette()
    roles = {
        QPalette.ColorRole.Window: theme.bg_primary,
        QPalette.ColorRole.WindowText: theme.text_primary,
        QPalette.ColorRole.Base: theme.input_bg,
        QPalette.ColorRole.AlternateBase: theme.bg_secondary,
        QPalette.ColorRole.Text: accessible_text_color(theme.text_primary, theme.input_bg),
        QPalette.ColorRole.Button: theme.bg_secondary,
        QPalette.ColorRole.ButtonText: accessible_text_color(theme.text_primary, theme.bg_secondary),
        QPalette.ColorRole.Highlight: theme.list_selected,
        QPalette.ColorRole.HighlightedText: contrasting_text_color(theme.list_selected),
        QPalette.ColorRole.ToolTipBase: theme.bg_secondary,
        QPalette.ColorRole.ToolTipText: accessible_text_color(theme.text_primary, theme.bg_secondary),
        QPalette.ColorRole.PlaceholderText: secondary_text_color(theme, theme.input_bg),
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    widget.setPalette(palette)


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
    return build_base_stylesheet(theme) + build_form_controls_stylesheet(theme)


def build_base_stylesheet(theme: Theme) -> str:
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


def build_form_controls_stylesheet(theme: Theme) -> str:
    """Theme the controls used by the dialogs (tabs, tables, inputs, sliders...).

    Without these rules Qt falls back to the platform palette, which is light,
    so dark themes end up with light-gray text on light panels (or dark text on
    the dark dialog background, e.g. checkbox labels).
    """
    accent = theme.input_border
    field_text = accessible_text_color(theme.text_primary, theme.input_bg)
    header_text = accessible_text_color(theme.text_primary, theme.bg_secondary)
    muted_tab_text = secondary_text_color(theme, theme.bg_secondary)
    muted_text = secondary_text_color(theme, theme.bg_primary)
    selected_text = contrasting_text_color(theme.list_selected)
    up_arrow = indicator_image_path("up", field_text)
    down_arrow = indicator_image_path("down", field_text)
    check_mark = indicator_image_path("check", contrasting_text_color(accent))
    return f"""
        QCheckBox {{
            color: {theme.text_primary};
            spacing: 8px;
        }}
        QCheckBox:disabled {{
            color: {muted_text};
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {theme.button_border};
            border-radius: 3px;
            background-color: {theme.input_bg};
        }}
        QCheckBox::indicator:hover {{
            border-color: {accent};
        }}
        QCheckBox::indicator:checked {{
            background-color: {accent};
            border-color: {accent};
            image: url("{check_mark}");
        }}
        QComboBox, QSpinBox, QDoubleSpinBox {{
            background-color: {theme.input_bg};
            color: {field_text};
            border: 1px solid {theme.button_border};
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 22px;
            selection-background-color: {theme.list_selected};
            selection-color: {selected_text};
        }}
        QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
        QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {accent};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: center right;
            width: 22px;
            border: none;
        }}
        QComboBox::down-arrow, QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            image: url("{down_arrow}");
            width: 10px;
            height: 6px;
        }}
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            image: url("{up_arrow}");
            width: 10px;
            height: 6px;
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: border;
            width: 22px;
            background: transparent;
            border: none;
            border-left: 1px solid {theme.button_border};
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            subcontrol-position: top right;
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-position: bottom right;
        }}
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background: {theme.bg_secondary};
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme.input_bg};
            color: {field_text};
            border: 1px solid {theme.button_border};
            selection-background-color: {theme.list_selected};
            selection-color: {selected_text};
            outline: 0;
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: {theme.button_border};
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {accent};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {theme.text_primary};
            border: 2px solid {accent};
            width: 14px;
            height: 14px;
            margin: -6px 0;
            border-radius: 9px;
        }}
        QTabWidget::pane {{
            background-color: {theme.bg_primary};
            border: 1px solid {theme.button_border};
            border-radius: 4px;
            top: -1px;
        }}
        QTabBar::tab {{
            background-color: {theme.bg_secondary};
            color: {muted_tab_text};
            border: 1px solid {theme.button_border};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 7px 12px;
            margin-right: 2px;
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {theme.bg_primary};
            color: {theme.text_primary};
        }}
        QTabBar::tab:selected {{
            background-color: {theme.bg_primary};
            color: {theme.text_primary};
            border-top: 3px solid {accent};
            font-weight: bold;
        }}
        QTableWidget, QTableView {{
            background-color: {theme.input_bg};
            alternate-background-color: {theme.bg_secondary};
            color: {field_text};
            gridline-color: {theme.button_border};
            border: 1px solid {theme.button_border};
            selection-background-color: {theme.list_selected};
            selection-color: {selected_text};
        }}
        QHeaderView::section {{
            background-color: {theme.bg_secondary};
            color: {header_text};
            padding: 6px 8px;
            border: none;
            border-right: 1px solid {theme.button_border};
            border-bottom: 1px solid {theme.button_border};
            font-weight: bold;
        }}
        QTableCornerButton::section {{
            background-color: {theme.bg_secondary};
            border: none;
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: {theme.bg_secondary};
            width: 12px;
            margin: 0;
        }}
        QScrollBar:horizontal {{
            background: {theme.bg_secondary};
            height: 12px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {theme.button_border};
            min-height: 24px;
            border-radius: 4px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: {theme.button_border};
            min-width: 24px;
            border-radius: 4px;
            margin: 2px;
        }}
        QScrollBar::handle:hover {{
            background: {accent};
        }}
        QScrollBar::add-line, QScrollBar::sub-line {{
            width: 0;
            height: 0;
        }}
        QScrollBar::add-page, QScrollBar::sub-page {{
            background: none;
        }}
        QToolTip {{
            background-color: {theme.bg_secondary};
            color: {header_text};
            border: 1px solid {theme.button_border};
            padding: 4px 6px;
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
