import html
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.models import TypingSession, SessionRecord
from core.persistence import ProgressStore
from core.lessons import build_lessons
from core.wordgen import generate_text, generate_developer_text, generate_adaptive_text
from core.audio import CelebrationSoundManager
from core.themes import get_theme, Theme
from core.scoring import calculate_wpm, calculate_accuracy
from core.analytics import get_practice_recommendations
from core.constants import (
    DEFAULT_BACKSPACE_PENALTY,
    DEFAULT_BACKSPACE_ACCURACY_WEIGHT,
    DEFAULT_STRICT_MODE,
    DEFAULT_SHOW_KEYBOARD,
    DEFAULT_SHOW_CELEBRATION,
    DEFAULT_FONT_SIZE,
    DEFAULT_RANDOM_WORD_COUNT,
    DEFAULT_DEVELOPER_KEYS_LENGTH,
    DEFAULT_DEVELOPER_KEYS_MODE,
    DEFAULT_THEME,
    DEFAULT_TIMED_MODE_SECONDS,
    DEFAULT_ADAPTIVE_DRILLS,
    FREE_PRACTICE_DESCRIPTION,
    FREE_PRACTICE_PLACEHOLDER,
)
from core.best_wpm import BestWpmTracker
from ui.widgets import KeyboardWidget, FingerLegendWidget, CelebrationOverlay
from ui.dialogs import StatisticsDialog, SettingsDialog
from ui.styles import (
    build_main_stylesheet,
    build_target_text_style,
    build_description_styles,
)
from ui.formats import make_input_formats

class TypingPracticeApp(QMainWindow):
    """Main application window for touch typing practice."""

    def __init__(self) -> None:
        super().__init__()

        self.lesson_offset = 1
        self.mode = "lesson"
        self._previous_typed_length = 0  # Track for backspace detection
        self._key_stats_recorded_length = 0  # How much of typed_text has already been counted for key stats
        self._pending_display_update = False  # Guard for deferred display refresh
        self._round_complete = False  # True after a round finishes; Space advances to the next
        self._last_highlighted_length = 0  # Incremental input highlighting cursor
        self._cached_target = ""
        self._cached_target_parts: List[str] = []
        self._cached_target_styles: List[str] = []
        self._cached_target_html_parts: List[str] = []
        self._timed_seconds_remaining: Optional[float] = None
        self._timed_mode_active = False
        self.current_theme: Theme = get_theme(DEFAULT_THEME)  # Current theme

        # Cached hot-path settings (refreshed in _apply_settings)
        self._backspace_penalty = DEFAULT_BACKSPACE_PENALTY
        self._backspace_accuracy_weight = DEFAULT_BACKSPACE_ACCURACY_WEIGHT
        self._strict_mode = DEFAULT_STRICT_MODE
        self._timed_mode_seconds = DEFAULT_TIMED_MODE_SECONDS
        self._adaptive_drills = DEFAULT_ADAPTIVE_DRILLS

        # Initialize the celebration sound manager with this window as parent
        CelebrationSoundManager.initialize(self)

        # Assuming typing_progress.json is in the root folder relative to execution or same folder
        # We'll look for it relative to the main script execution
        progress_path = Path("typing_progress.json").resolve()
        self.progress_store = ProgressStore(progress_path)

        self.lessons = build_lessons()
        self.session = TypingSession()

        self.best_wpm = BestWpmTracker.from_raw(self.progress_store.data.get("best_wpm"))

        self.current_lesson_index = self._clamp_index(
            self._safe_int(self.progress_store.data.get("current_lesson_index", 0)),
            len(self.lessons),
        )
        self.current_text_index = max(0, self._safe_int(self.progress_store.data.get("current_text_index", 0)))
        self.current_target_text = ""

        self._configure_window()
        self._build_ui()
        self._apply_settings()
        self._initialize_state()

    @staticmethod
    def _clamp_index(value: int, upper: int) -> int:
        if upper <= 0:
            return 0
        return max(0, min(value, upper - 1))

    @staticmethod
    def _safe_int(value: object, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _configure_window(self) -> None:
        self.setWindowTitle("Touch Typing Practice")
        self.setGeometry(100, 100, 1100, 850)

    def _build_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        sidebar = self._build_sidebar()
        content = self._build_content()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content)
        main_layout.setStretchFactor(content, 3)

        # Initialize celebration overlay
        self.celebration_overlay = CelebrationOverlay(self)
        self.celebration_overlay.resize(self.size())

        # Timed mode countdown (1s tick)
        self._timed_timer = QTimer(self)
        self._timed_timer.setInterval(1000)
        self._timed_timer.timeout.connect(self._on_timed_tick)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, 'celebration_overlay'):
            self.celebration_overlay.resize(self.size())

    def closeEvent(self, event) -> None:
        self.progress_store.save()
        super().closeEvent(event)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setMaximumWidth(260)
        sidebar.setObjectName("sidebar")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("⌨️ Typing Lessons")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        self.lesson_list = QListWidget()
        self.lesson_list.addItem("Free Practice")
        self.lesson_list.addItems([lesson.title for lesson in self.lessons])
        self.lesson_list.currentRowChanged.connect(self._handle_row_change)
        layout.addWidget(self.lesson_list)

        # Sidebar buttons
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(10, 5, 10, 10)

        self.stats_button = QPushButton("📊 View Statistics")
        self.stats_button.clicked.connect(self._show_statistics)
        self.stats_button.setToolTip("View your typing progress and statistics")
        button_layout.addWidget(self.stats_button)

        self.settings_button = QPushButton("⚙️ Settings")
        self.settings_button.clicked.connect(self._show_settings)
        self.settings_button.setToolTip("Configure app settings and penalties")
        button_layout.addWidget(self.settings_button)

        layout.addWidget(button_container)

        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        content.setObjectName("content")
        layout = QVBoxLayout(content)
        layout.setSpacing(15)

        self._add_lesson_header(layout)
        self._add_target_section(layout)
        self._add_free_practice_controls(layout)
        self._add_input_section(layout)
        self._add_stats_section(layout)
        self._add_progress_section(layout)
        self._add_keyboard_section(layout)
        self._add_controls(layout)
        layout.addStretch()

        return content

    def _add_lesson_header(self, layout: QVBoxLayout) -> None:
        self.lesson_title = QLabel()
        self.lesson_title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        layout.addWidget(self.lesson_title)

        self.lesson_description = QLabel()
        self.lesson_description.setWordWrap(True)
        self.description_default_style = (
            "padding: 10px; background-color: #e3f2fd; border-radius: 5px; font-size: 13px;"
        )
        self.description_success_style = (
            "padding: 15px; background-color: #c8e6c9; border-radius: 5px; font-size: 14px; font-weight: bold;"
        )
        self.description_completion_style = (
            "padding: 15px; background-color: #fff9c4; border-radius: 5px; font-size: 14px; font-weight: bold;"
        )
        self.lesson_description.setStyleSheet(self.description_default_style)
        layout.addWidget(self.lesson_description)

    def _add_target_section(self, layout: QVBoxLayout) -> None:
        target_label = QLabel("📝 Type this text:")
        target_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(target_label)

        self.target_text = QLabel()
        self.target_text.setWordWrap(True)
        self.target_text.setFont(QFont("Courier New", 16))
        self.target_text.setTextFormat(Qt.TextFormat.RichText)
        self.target_text.setStyleSheet(
            "padding: 20px; background-color: #f5f5f5; border: 2px solid #ccc; border-radius: 8px; line-height: 1.8;"
        )
        layout.addWidget(self.target_text)

    def _add_free_practice_controls(self, layout: QVBoxLayout) -> None:
        self.free_controls = QWidget()
        controls_layout = QVBoxLayout(self.free_controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        helper = QLabel("Customize your own drill or import a passage to practice freely.")
        helper.setWordWrap(True)
        helper.setStyleSheet("font-size: 13px; color: #37474F;")
        controls_layout.addWidget(helper)

        self.custom_text_input = QTextEdit()
        self.custom_text_input.setPlaceholderText("Paste or type custom text here...")
        self.custom_text_input.setMaximumHeight(140)
        controls_layout.addWidget(self.custom_text_input)

        buttons_layout = QHBoxLayout()

        self.apply_custom_text_button = QPushButton("Use Custom Text")
        self.apply_custom_text_button.clicked.connect(self.apply_custom_text)
        buttons_layout.addWidget(self.apply_custom_text_button)

        self.import_text_button = QPushButton("Import From File...")
        self.import_text_button.clicked.connect(self.import_custom_text)
        buttons_layout.addWidget(self.import_text_button)

        controls_layout.addLayout(buttons_layout)
        self.free_controls.hide()
        layout.addWidget(self.free_controls)

    def _add_input_section(self, layout: QVBoxLayout) -> None:
        # Header row with input label and strict mode indicator
        input_header = QHBoxLayout()
        
        input_label = QLabel("✍️ Your typing:")
        input_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        input_header.addWidget(input_label)
        
        input_header.addStretch()
        
        # Strict mode indicator
        self.strict_mode_indicator = QLabel("🔒 STRICT MODE")
        self.strict_mode_indicator.setStyleSheet(
            "color: #c62828; font-weight: bold; font-size: 12px; "
            "background-color: #ffcdd2; padding: 4px 8px; border-radius: 4px;"
        )
        self.strict_mode_indicator.setVisible(False)
        input_header.addWidget(self.strict_mode_indicator)
        
        layout.addLayout(input_header)

        self.typing_input = QTextEdit()
        self.typing_input.setFont(QFont("Courier New", 16))
        self.typing_input.setMaximumHeight(150)
        self.typing_input.setPlaceholderText("Start typing here...")
        self.typing_input.setStyleSheet(
            "padding: 20px; background-color: #fff; border: 2px solid #2196F3; border-radius: 8px;"
        )
        self.typing_input.textChanged.connect(self.on_text_changed)
        
        # Install event filter for backspace detection
        self.typing_input.installEventFilter(self)
        
        layout.addWidget(self.typing_input)

        formats = make_input_formats()
        self.input_default_format = formats.default
        self.correct_char_format = formats.correct
        self.error_char_format = formats.error
        self.extra_char_format = formats.extra

    def _add_stats_section(self, layout: QVBoxLayout) -> None:
        stats_layout = QHBoxLayout()

        self.wpm_label = QLabel("WPM: 0")
        self.wpm_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 8px 12px; background-color: #4CAF50; color: white; border-radius: 5px;"
        )
        self.wpm_label.setToolTip("Words Per Minute (adjusted for backspace penalties)")
        stats_layout.addWidget(self.wpm_label)

        self.accuracy_label = QLabel("Accuracy: 100%")
        self.accuracy_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 8px 12px; background-color: #2196F3; color: white; border-radius: 5px;"
        )
        self.accuracy_label.setToolTip("Typing accuracy (adjusted for backspace usage)")
        stats_layout.addWidget(self.accuracy_label)

        self.progress_label = QLabel("Progress: 0%")
        self.progress_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 8px 12px; background-color: #FF9800; color: white; border-radius: 5px;"
        )
        stats_layout.addWidget(self.progress_label)

        self.error_label = QLabel("Errors: 0")
        self.error_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 8px 12px; background-color: #F06292; color: white; border-radius: 5px;"
        )
        stats_layout.addWidget(self.error_label)

        # Backspace counter - styled distinctly in orange
        self.backspace_label = QLabel("⌫: 0")
        self.backspace_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 8px 12px; background-color: #FF5722; color: white; border-radius: 5px;"
        )
        self.backspace_label.setToolTip("Backspace count - each press incurs a penalty")
        stats_layout.addWidget(self.backspace_label)

        self.best_wpm_label = QLabel("Best: --")
        self.best_wpm_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 8px 12px; background-color: #7E57C2; color: white; border-radius: 5px;"
        )
        stats_layout.addWidget(self.best_wpm_label)

        self.timer_label = QLabel("")
        self.timer_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 8px 12px; background-color: #455A64; color: white; border-radius: 5px;"
        )
        self.timer_label.setVisible(False)
        stats_layout.addWidget(self.timer_label)

        layout.addLayout(stats_layout)

    def _add_progress_section(self, layout: QVBoxLayout) -> None:
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 2px solid grey; border-radius: 5px; text-align: center; } "
            "QProgressBar::chunk { background-color: #4CAF50; }"
        )
        layout.addWidget(self.progress_bar)

    def _add_keyboard_section(self, layout: QVBoxLayout) -> None:
        """Add the virtual keyboard section."""
        self.keyboard_container = QWidget()
        kb_layout = QVBoxLayout(self.keyboard_container)
        kb_layout.setContentsMargins(0, 10, 0, 0)

        # Toggle button
        toggle_layout = QHBoxLayout()
        self.keyboard_toggle = QPushButton("⌨️ Hide Keyboard")
        self.keyboard_toggle.setCheckable(True)
        self.keyboard_toggle.setChecked(True)
        self.keyboard_toggle.clicked.connect(self._toggle_keyboard)
        self.keyboard_toggle.setMaximumWidth(150)
        toggle_layout.addWidget(self.keyboard_toggle)
        toggle_layout.addStretch()
        kb_layout.addLayout(toggle_layout)

        # Keyboard widget
        self.keyboard_widget = KeyboardWidget()
        kb_layout.addWidget(self.keyboard_widget)

        # Finger legend
        self.finger_legend = FingerLegendWidget()
        kb_layout.addWidget(self.finger_legend)

        layout.addWidget(self.keyboard_container)

    def _add_controls(self, layout: QVBoxLayout) -> None:
        button_layout = QHBoxLayout()

        self.next_button = QPushButton("Next Text ➡️")
        self.next_button.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 12px; font-size: 14px; font-weight: bold; border-radius: 5px;"
        )
        self.next_button.clicked.connect(self.next_text)
        self.next_button.setToolTip("Press Space or Enter to continue after finishing a round")
        button_layout.addWidget(self.next_button)

        # Regenerate button for Random Words (initially hidden)
        self.regenerate_button = QPushButton("🎲 Generate New Words")
        self.regenerate_button.setStyleSheet(
            "background-color: #FF9800; color: white; padding: 12px; font-size: 14px; font-weight: bold; border-radius: 5px;"
        )
        self.regenerate_button.clicked.connect(self.regenerate_generated_text)
        self.regenerate_button.setVisible(False)
        button_layout.addWidget(self.regenerate_button)

        self.reset_button = QPushButton("↺ Reset")
        self.reset_button.setStyleSheet("padding: 12px; font-size: 14px; border-radius: 5px;")
        self.reset_button.clicked.connect(self.reset_exercise)
        button_layout.addWidget(self.reset_button)

        layout.addLayout(button_layout)

    def _toggle_keyboard(self) -> None:
        """Toggle keyboard visibility."""
        visible = self.keyboard_toggle.isChecked()
        self.keyboard_widget.setVisible(visible)
        self.finger_legend.setVisible(visible)
        self.keyboard_toggle.setText("⌨️ Hide Keyboard" if visible else "⌨️ Show Keyboard")
        self.progress_store.set_setting("show_keyboard", visible)

    def _apply_settings(self) -> None:
        """Apply saved settings to the UI."""
        self._backspace_penalty = self.progress_store.get_setting(
            "backspace_penalty", DEFAULT_BACKSPACE_PENALTY
        )
        self._backspace_accuracy_weight = self.progress_store.get_setting(
            "backspace_accuracy_weight", DEFAULT_BACKSPACE_ACCURACY_WEIGHT
        )
        self._strict_mode = self.progress_store.get_setting("strict_mode", DEFAULT_STRICT_MODE)
        self._timed_mode_seconds = self.progress_store.get_setting(
            "timed_mode_seconds", DEFAULT_TIMED_MODE_SECONDS
        )
        self._adaptive_drills = self.progress_store.get_setting(
            "adaptive_drills", DEFAULT_ADAPTIVE_DRILLS
        )

        # Load and apply theme
        theme_name = self.progress_store.get_setting("theme", DEFAULT_THEME)
        self.current_theme = get_theme(theme_name)
        self._apply_theme()

        # Keyboard visibility
        show_keyboard = self.progress_store.get_setting("show_keyboard", DEFAULT_SHOW_KEYBOARD)
        self.keyboard_toggle.setChecked(show_keyboard)
        self.keyboard_widget.setVisible(show_keyboard)
        self.finger_legend.setVisible(show_keyboard)
        self.keyboard_toggle.setText("⌨️ Hide Keyboard" if show_keyboard else "⌨️ Show Keyboard")

        # Strict mode indicator
        self.strict_mode_indicator.setVisible(self._strict_mode)

        # Font size
        font_size = self.progress_store.get_setting("font_size", DEFAULT_FONT_SIZE)
        self.typing_input.setFont(QFont("Courier New", font_size))
        self.target_text.setFont(QFont("Courier New", font_size))

        # Refresh the active developer drill if the settings changed.
        if self.mode == "lesson" and self.lessons:
            current_lesson = self.lessons[self.current_lesson_index]
            if current_lesson.title == "Developer Keys":
                self.current_target_text = ""
                self.progress_store.clear_developer_text(self.current_lesson_index)
                self.load_current_text()

    def _apply_theme(self) -> None:
        """Apply the current theme to the application."""
        theme = self.current_theme

        self.keyboard_widget.set_theme(theme)
        self.finger_legend.set_theme(theme)

        self.setStyleSheet(build_main_stylesheet(theme))

        description_styles = build_description_styles(theme)
        self.description_default_style = description_styles["default"]
        self.description_success_style = description_styles["success"]
        self.description_completion_style = description_styles["complete"]

        self.target_text.setStyleSheet(build_target_text_style(theme))

        if self.mode == "lesson":
            lesson = self.lessons[self.current_lesson_index]
            self._update_description(f"<b>Focus:</b> {lesson.description}", mode="default")
        else:
            self._update_description(FREE_PRACTICE_DESCRIPTION, mode="default")

    def eventFilter(self, obj, event) -> bool:
        """Intercept key events to track backspace usage and enforce strict mode."""
        if obj == self.typing_input and event.type() == QEvent.Type.KeyPress:
            key_event = event
            # Once a round is complete, Space/Enter jumps to the next challenge.
            if self._round_complete and key_event.key() in (
                Qt.Key.Key_Space,
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
            ):
                self._advance_to_next()
                return True  # Consume so no stray character is typed
            if key_event.key() == Qt.Key.Key_Space and self._cursor_is_at_target_end():
                self._advance_from_finished_line()
                return True  # Consume so no extra space is typed
            if key_event.key() == Qt.Key.Key_Backspace:
                if self._strict_mode:
                    # Block backspace and show visual feedback
                    self._flash_strict_mode_warning()
                    return True  # Consume the event
                else:
                    # Allow backspace but track it
                    if self.session.is_active and len(self.session.typed_text) > 0:
                        self.session.backspace_count += 1
                        self._update_backspace_label()
        
        return super().eventFilter(obj, event)

    def _flash_strict_mode_warning(self) -> None:
        """Show a brief visual warning when backspace is attempted in strict mode."""
        original_style = self.typing_input.styleSheet()
        self.typing_input.setStyleSheet(
            "padding: 20px; background-color: #ffcdd2; border: 2px solid #c62828; border-radius: 8px;"
        )
        QTimer.singleShot(150, lambda: self.typing_input.setStyleSheet(original_style))

    def _update_backspace_label(self) -> None:
        """Update the backspace counter display."""
        count = self.session.backspace_count
        wpm_penalty = count * self._backspace_penalty
        
        if count > 0:
            self.backspace_label.setText(f"⌫: {count} (-{wpm_penalty})")
        else:
            self.backspace_label.setText("⌫: 0")

    def _initialize_state(self) -> None:
        if not self.lessons:
            self._enter_free_practice()
            return

        lesson = self.lessons[self.current_lesson_index]
        if lesson.texts:
            self.current_text_index = min(self.current_text_index, len(lesson.texts) - 1)
        else:
            self.current_text_index = 0

        self.lesson_list.blockSignals(True)
        target_row = self.lesson_offset + self.current_lesson_index
        self.lesson_list.setCurrentRow(target_row)
        self.lesson_list.blockSignals(False)

        self.load_lesson(self.current_lesson_index, reset_text_index=False)

    def _handle_row_change(self, row: int) -> None:
        if row == -1:
            return
        if row == 0:
            self._enter_free_practice()
            return

        lesson_index = row - self.lesson_offset
        lesson_index = self._clamp_index(lesson_index, len(self.lessons))
        self.load_lesson(lesson_index)

    def _enter_free_practice(self) -> None:
        self.mode = "free"
        self.free_controls.show()
        self.next_button.setEnabled(False)
        self.lesson_title.setText("Free Practice")
        self._update_description(FREE_PRACTICE_DESCRIPTION, mode="default")
        custom_text = self.custom_text_input.toPlainText().strip()
        self.current_target_text = custom_text
        self.target_text.setText(custom_text or FREE_PRACTICE_PLACEHOLDER)
        self._update_best_wpm_label()
        self.reset_exercise()

    def apply_custom_text(self) -> None:
        if self.mode != "free":
            return
        custom_text = self.custom_text_input.toPlainText().strip()
        self.current_target_text = custom_text
        self.target_text.setText(custom_text or FREE_PRACTICE_PLACEHOLDER)
        self.reset_exercise()

    def import_custom_text(self) -> None:
        if self.mode != "free":
            return
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Text File",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if not file_name:
            return
        try:
            text = Path(file_name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            try:
                text = Path(file_name).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                return
        self.custom_text_input.setPlainText(text.strip())
        self.apply_custom_text()

    def load_lesson(self, index: int, *, reset_text_index: bool = True) -> None:
        """Load a specific lesson and optionally keep progress within it."""
        if not (0 <= index < len(self.lessons)):
            return

        self.mode = "lesson"
        self.free_controls.hide()
        self.next_button.setEnabled(True)

        self.current_lesson_index = index
        lesson = self.lessons[index]

        # Show regenerate button for generated drill lessons.
        is_generated_lesson = lesson.title in {"Random Words", "Developer Keys"}
        self.regenerate_button.setVisible(is_generated_lesson)
        if lesson.title == "Developer Keys":
            self.regenerate_button.setText("⌨️ Generate New Keys")
            self.regenerate_button.setToolTip("Generate a new developer-key drill")
        else:
            self.regenerate_button.setText("🎲 Generate New Words")
            self.regenerate_button.setToolTip("Generate a new random word drill")

        if reset_text_index or self.current_text_index >= len(lesson.texts):
            self.current_text_index = 0

        self.lesson_title.setText(lesson.title)
        self._update_description(f"<b>Focus:</b> {lesson.description}", mode="default")
        self._update_best_wpm_label()
        self.load_current_text()

    def load_current_text(self) -> None:
        """Load the active text from the selected lesson."""
        lesson = self.lessons[self.current_lesson_index]
        if not lesson.texts:
            self.current_target_text = ""
            self.target_text.setText("")
            self.reset_exercise()
            return

        self.current_text_index = min(self.current_text_index, len(lesson.texts) - 1)
        # Support generated drills when a lesson uses a special marker or title.
        candidate = lesson.texts[self.current_text_index]
        generated_kind = self._get_generated_lesson_kind(lesson, candidate)
        if generated_kind:
            self.current_target_text = self._get_or_create_generated_text(generated_kind)
        else:
            self.current_target_text = candidate
        self.target_text.setText(self.current_target_text)
        self.reset_exercise()
        self._save_progress()

    def regenerate_generated_text(self) -> None:
        """Generate new text for generated drill lessons."""
        lesson = self.lessons[self.current_lesson_index]
        generated_kind = self._get_generated_lesson_kind(lesson, lesson.texts[0] if lesson.texts else "")
        if generated_kind:
            # Clear persisted text and generate new content for the active drill.
            if generated_kind == "developer":
                self.progress_store.clear_developer_text(self.current_lesson_index)
            else:
                self.progress_store.clear_random_text(self.current_lesson_index)
            self.current_target_text = self._generate_practice_text(generated_kind)
            if generated_kind == "developer":
                self.progress_store.set_developer_text(
                    self.current_lesson_index,
                    self.current_target_text,
                    token_count=self._developer_keys_length(),
                    mode=self._developer_keys_mode(),
                )
            else:
                self.progress_store.set_random_text(self.current_lesson_index, self.current_target_text)
            self.target_text.setText(self.current_target_text)
            self.reset_exercise()

    def _get_generated_lesson_kind(self, lesson, candidate: str) -> Optional[str]:
        if candidate == "__RANDOM__" or lesson.title == "Random Words":
            return "random"
        if candidate == "__DEVELOPER__" or lesson.title == "Developer Keys":
            return "developer"
        return None

    def _get_or_create_generated_text(self, generated_kind: str) -> str:
        if generated_kind == "developer":
            persisted = self.progress_store.get_developer_text(self.current_lesson_index)
            current_length = self._developer_keys_length()
            current_mode = self._developer_keys_mode()
            if isinstance(persisted, dict):
                persisted_text = persisted.get("text")
                if (
                    isinstance(persisted_text, str)
                    and persisted.get("token_count") == current_length
                    and persisted.get("mode") == current_mode
                ):
                    return persisted_text

            generated_text = self._generate_practice_text(generated_kind)
            self.progress_store.set_developer_text(
                self.current_lesson_index,
                generated_text,
                token_count=current_length,
                mode=current_mode,
            )
            return generated_text

        persisted = self.progress_store.get_random_text(self.current_lesson_index)
        if persisted:
            return persisted

        generated_text = self._generate_practice_text(generated_kind)
        self.progress_store.set_random_text(self.current_lesson_index, generated_text)
        return generated_text

    def _developer_keys_length(self) -> int:
        return self.progress_store.get_setting("developer_keys_length", DEFAULT_DEVELOPER_KEYS_LENGTH)

    def _developer_keys_mode(self) -> str:
        return self.progress_store.get_setting("developer_keys_mode", DEFAULT_DEVELOPER_KEYS_MODE)

    def reset_exercise(self) -> None:
        """Clear typing data and reset statistics."""
        self.typing_input.blockSignals(True)
        self.typing_input.clear()
        self.typing_input.blockSignals(False)
        self.typing_input.setReadOnly(False)

        self.session.reset()
        self._previous_typed_length = 0
        self._key_stats_recorded_length = 0
        self._last_highlighted_length = 0
        self._cached_target = ""
        self._round_complete = False
        self._stop_timed_mode()
        self._update_backspace_label()

        if self.mode == "lesson":
            lesson_desc = self.lessons[self.current_lesson_index].description
            self._update_description(f"<b>Focus:</b> {lesson_desc}", mode="default")
        else:
            self._update_description(FREE_PRACTICE_DESCRIPTION, mode="default")

        self.update_display()
        self._update_keyboard_highlight()
        self.typing_input.setFocus()

    def on_text_changed(self) -> None:
        """Handle updates when the user types or deletes characters."""
        self.session.typed_text = self.typing_input.toPlainText()

        if not self.session.is_active and self.session.typed_text:
            self.session.begin()
            self._start_timed_mode_if_enabled()

        self._previous_typed_length = len(self.session.typed_text)

        if not self._pending_display_update:
            self._pending_display_update = True
            QTimer.singleShot(0, self._flush_display)

        if (
            not self._round_complete
            and self.session.typed_text == self.current_target_text
            and self.current_target_text
        ):
            self.on_completion()

    def _flush_display(self) -> None:
        """Deferred display refresh — called once per event-loop cycle regardless of keystroke count."""
        self._pending_display_update = False
        self.update_display()
        self._update_keyboard_highlight()

    def _update_keyboard_highlight(self) -> None:
        """Update the keyboard to highlight the next key to press."""
        if not self.current_target_text:
            self.keyboard_widget.clear_highlights()
            return

        typed_len = len(self.session.typed_text)
        target_len = len(self.current_target_text)

        if typed_len >= target_len:
            self.keyboard_widget.clear_highlights()
            return

        next_char = self.current_target_text[typed_len]
        
        # Check if last typed character was an error
        if typed_len > 0:
            last_typed = self.session.typed_text[-1]
            expected = self.current_target_text[typed_len - 1]
            if last_typed != expected:
                # Show error - highlight what should have been pressed
                self.keyboard_widget.set_next_key(expected, error=True)
                return

        self.keyboard_widget.set_next_key(next_char, error=False)

    def update_display(self) -> None:
        """Update highlighted text and real-time statistics."""
        target = self.current_target_text
        typed = self.session.typed_text

        self._record_new_key_stats(target, typed)

        highlighted_text, mismatches = self._build_target_highlight(target, typed)
        self.session.errors = mismatches

        if target:
            self.target_text.setText(highlighted_text)
        elif self.mode == "free":
            self.target_text.setText(FREE_PRACTICE_PLACEHOLDER)
        else:
            self.target_text.setText("")

        self._update_wpm_label(typed)
        self._update_accuracy_label(typed)

        extra_errors = max(len(typed) - len(target), 0)
        self._update_error_label(mismatches + extra_errors)

        self._update_progress_indicators(typed, target)
        self._highlight_input(target, typed)

    def _record_new_key_stats(self, target: str, typed: str) -> None:
        """Record key attempt/error stats once per newly confirmed character.

        Called on every render tick, so positions already counted must be
        skipped — otherwise a keystroke re-records every prior character in
        the typed prefix, inflating the per-key totals quadratically.
        """
        confirmed_length = min(len(typed), len(target))

        if confirmed_length < self._key_stats_recorded_length:
            # Backspaced past previously-counted positions; they'll be
            # recounted as fresh attempts if retyped.
            self._key_stats_recorded_length = confirmed_length
            return

        for index in range(self._key_stats_recorded_length, confirmed_length):
            expected = target[index]
            self.session.record_key_attempt(expected)
            if typed[index] != expected:
                self.session.record_key_error(expected)

        self._key_stats_recorded_length = confirmed_length

    def _build_target_highlight(self, target: str, typed: str) -> Tuple[str, int]:
        if target != self._cached_target:
            self._cached_target = target
            self._cached_target_parts = [self._format_char(char) for char in target]
            self._cached_target_styles = [""] * len(target)
            self._cached_target_html_parts = [""] * len(target)

        errors = 0
        style_templates = {
            "correct": '<span style="color: green; background-color: #c8e6c9;">{char}</span>',
            "error": (
                '<span style="color: red; background-color: #ffcdd2; '
                'text-decoration: underline;">{char}</span>'
            ),
            "gray": '<span style="color: gray;">{char}</span>',
        }

        for index, char in enumerate(target):
            if index < len(typed):
                style = "correct" if typed[index] == char else "error"
                if style == "error":
                    errors += 1
            else:
                style = "gray"

            if index < len(self._cached_target_styles) and self._cached_target_styles[index] == style:
                continue

            self._cached_target_styles[index] = style
            styled_char = self._cached_target_parts[index]
            self._cached_target_html_parts[index] = style_templates[style].format(char=styled_char)

        return "".join(self._cached_target_html_parts[: len(target)]), errors

    @staticmethod
    def _format_char(char: str) -> str:
        if char == "\n":
            return "<br />"
        if char == " ":
            return "&nbsp;"
        return html.escape(char)

    def _highlight_input(self, target: str, typed: str) -> None:
        doc = self.typing_input.document()
        cursor_state = self.typing_input.textCursor()
        anchor = cursor_state.anchor()
        position = cursor_state.position()
        new_len = len(typed)
        prev_len = self._last_highlighted_length

        self.typing_input.blockSignals(True)
        try:
            if new_len < prev_len:
                reset_cursor = QTextCursor(doc)
                reset_cursor.setPosition(new_len)
                reset_cursor.movePosition(
                    QTextCursor.MoveOperation.End,
                    QTextCursor.MoveMode.KeepAnchor,
                )
                reset_cursor.setCharFormat(self.input_default_format)
                reset_cursor.clearSelection()
                start_index = new_len
            else:
                start_index = prev_len

            doc_length = max(0, doc.characterCount() - 1)
            for idx in range(start_index, new_len):
                if idx >= doc_length:
                    break
                span_cursor = QTextCursor(doc)
                span_cursor.setPosition(idx)
                span_cursor.movePosition(
                    QTextCursor.MoveOperation.Right,
                    QTextCursor.MoveMode.KeepAnchor,
                )
                if idx < len(target):
                    fmt = (
                        self.correct_char_format
                        if typed[idx] == target[idx]
                        else self.error_char_format
                    )
                else:
                    fmt = self.extra_char_format
                span_cursor.setCharFormat(fmt)

            self._last_highlighted_length = new_len
        finally:
            restored_cursor = self.typing_input.textCursor()
            restored_cursor.setPosition(anchor)
            restored_cursor.setPosition(position, QTextCursor.MoveMode.KeepAnchor)
            self.typing_input.setTextCursor(restored_cursor)
            self.typing_input.blockSignals(False)

    def _update_wpm_label(self, typed: str) -> None:
        wpm = self._calculate_wpm(typed)
        self.wpm_label.setText(f"WPM: {wpm}")

    def _calculate_wpm(self, typed: str, elapsed: Optional[float] = None) -> int:
        if elapsed is None:
            elapsed = (
                time.time() - self.session.start_time
                if self.session.start_time
                else None
            )
        penalty_factor = self._backspace_penalty
        return calculate_wpm(
            typed=typed,
            elapsed_seconds=elapsed,
            backspace_count=self.session.backspace_count,
            penalty_factor=penalty_factor,
        )

    def _update_accuracy_label(self, typed: str) -> None:
        accuracy = self._calculate_accuracy(typed)
        self.accuracy_label.setText(f"Accuracy: {accuracy:.1f}%")

    def _calculate_accuracy(self, typed: str) -> float:
        return calculate_accuracy(
            typed=typed,
            target=self.current_target_text,
            mismatch_errors=self.session.errors,
            backspace_count=self.session.backspace_count,
            backspace_weight=self._backspace_accuracy_weight,
        )

    def _update_progress_indicators(self, typed: str, target: str) -> None:
        if not target:
            self.progress_label.setText("Progress: 0%")
            self.progress_bar.setValue(0)
            return

        progress = min(int((len(typed) / len(target)) * 100), 100)
        self.progress_label.setText(f"Progress: {progress}%")
        self.progress_bar.setValue(progress)

    def _update_error_label(self, total_errors: int) -> None:
        self.error_label.setText(f"Errors: {total_errors}")

    def _generate_practice_text(self, generated_kind: str) -> str:
        if generated_kind == "random":
            word_count = self.progress_store.get_setting(
                "random_word_count", DEFAULT_RANDOM_WORD_COUNT
            )
            if self._adaptive_drills:
                errors = self.progress_store.get_key_error_stats()
                attempts = self.progress_store.get_key_attempt_stats()
                recommendations = get_practice_recommendations(
                    errors, attempts, min_attempts=5, top_n=5
                )
                weak_keys = [key for key, _, _, _ in recommendations]
                if weak_keys:
                    return generate_adaptive_text(weak_keys, word_count)
            return generate_text(word_count)
        if generated_kind == "developer":
            return generate_developer_text(self._developer_keys_length(), self._developer_keys_mode())
        return ""

    def _start_timed_mode_if_enabled(self) -> None:
        if self._timed_mode_seconds <= 0:
            self.timer_label.setVisible(False)
            return
        self._timed_seconds_remaining = float(self._timed_mode_seconds)
        self._timed_mode_active = True
        self.timer_label.setVisible(True)
        self._update_timer_label()
        self._timed_timer.start()

    def _stop_timed_mode(self) -> None:
        self._timed_timer.stop()
        self._timed_mode_active = False
        self._timed_seconds_remaining = None
        self.timer_label.setVisible(False)

    def _update_timer_label(self) -> None:
        if self._timed_seconds_remaining is None:
            return
        remaining = max(0, int(self._timed_seconds_remaining))
        minutes = remaining // 60
        seconds = remaining % 60
        self.timer_label.setText(f"⏱ {minutes}:{seconds:02d}")

    def _on_timed_tick(self) -> None:
        if self._timed_seconds_remaining is None or self._round_complete:
            return
        self._timed_seconds_remaining -= 1
        self._update_timer_label()
        if self._timed_seconds_remaining <= 0:
            self._stop_timed_mode()
            self.on_timed_completion()

    def on_timed_completion(self) -> None:
        """End a timed drill when the countdown reaches zero."""
        if self._round_complete or not self.session.typed_text:
            return
        self._finalize_session(timed_out=True)

    def on_completion(self) -> None:
        """Handle final stats and UI state once the text matches."""
        if self._round_complete:
            return
        self._stop_timed_mode()
        self._finalize_session(timed_out=False)

    def _finalize_session(self, *, timed_out: bool) -> None:
        """Record session results for exact completion or timed expiry."""
        elapsed_time = time.time() - self.session.start_time if self.session.start_time else 0
        wpm = self._calculate_wpm(self.session.typed_text, elapsed_time)
        accuracy = self._calculate_accuracy(self.session.typed_text)

        self.typing_input.setReadOnly(True)
        self.keyboard_widget.clear_highlights()
        self._round_complete = True

        backspace_count = self.session.backspace_count
        wpm_penalty = backspace_count * self._backspace_penalty

        if timed_out:
            completion_msg = (
                f"⏱ Time's up!\n\n"
                f"Speed: {wpm} WPM\n"
                f"Accuracy: {accuracy:.1f}%\n"
                f"Time: {elapsed_time:.1f} seconds\n"
                f"Backspaces: {backspace_count}"
            )
        else:
            completion_msg = (
                f"🎉 Excellent work!\n\n"
                f"Speed: {wpm} WPM\n"
                f"Accuracy: {accuracy:.1f}%\n"
                f"Time: {elapsed_time:.1f} seconds\n"
                f"Backspaces: {backspace_count}"
            )
        if backspace_count > 0:
            completion_msg += f" (penalty: -{wpm_penalty} WPM)"

        completion_msg += "\n\nPress Space to continue ➡️"

        self._update_description(completion_msg, mode="success")

        lesson_name = (
            self.lessons[self.current_lesson_index].title
            if self.mode == "lesson" else "Free Practice"
        )
        record = SessionRecord(
            timestamp=datetime.now().isoformat(),
            lesson_index=self.current_lesson_index if self.mode == "lesson" else -1,
            text_index=self.current_text_index,
            lesson_name=lesson_name,
            wpm=wpm,
            accuracy=round(accuracy, 1),
            errors=self.session.errors + max(
                len(self.session.typed_text) - len(self.current_target_text), 0
            ),
            backspaces=backspace_count,
            duration_seconds=round(elapsed_time, 1),
            text_length=len(self.session.typed_text) if timed_out else len(self.current_target_text),
        )
        self.progress_store.add_session_record(record)

        if self.session.key_errors:
            self.progress_store.update_key_error_stats(self.session.key_errors)
        if self.session.key_attempts:
            self.progress_store.update_key_attempt_stats(self.session.key_attempts)

        if self.session.key_errors:
            self.progress_store.add_session_key_stats(
                record.timestamp,
                record.lesson_index,
                lesson_name,
                self.session.key_errors,
                self.session.key_attempts,
            )

        if self.mode == "lesson":
            self._record_best_wpm(wpm)

        self.progress_store.save()

        if (
            not timed_out
            and self.progress_store.get_setting("show_celebration", DEFAULT_SHOW_CELEBRATION)
        ):
            self.celebration_overlay.start()
            CelebrationSoundManager.play()

        QTimer.singleShot(2000, self._unlock_text_input)

    def _record_best_wpm(self, wpm: int) -> None:
        lesson_key = str(self.current_lesson_index)
        if self.best_wpm.update(lesson_key, wpm):
            self._update_best_wpm_label()
            self._save_progress()

    def _unlock_text_input(self) -> None:
        self.typing_input.setReadOnly(False)
        self.typing_input.setFocus()

    def _cursor_is_at_target_end(self) -> bool:
        """Return True when the input cursor has reached the target text length."""
        if not self.current_target_text:
            return False
        if self._round_complete:
            return False

        cursor_position = self.typing_input.textCursor().position()
        typed_length = len(self.typing_input.toPlainText())
        target_length = len(self.current_target_text)
        return cursor_position >= target_length and typed_length >= target_length

    def _advance_from_finished_line(self) -> None:
        """Advance after the user has typed to the end, even with mistakes."""
        if self.mode == "lesson":
            self.next_text()
        else:
            self.reset_exercise()

    def _advance_to_next(self) -> None:
        """Move on from a completed round, triggered by the Space/Enter shortcut."""
        if not self._round_complete:
            return
        # Consume the flag immediately so a second keypress can't double-advance.
        self._round_complete = False
        self._advance_from_finished_line()

    def next_text(self) -> None:
        """Move to the next text or lesson, or congratulate the user."""
        if self.mode != "lesson":
            return

        lesson = self.lessons[self.current_lesson_index]

        if self.current_text_index < len(lesson.texts) - 1:
            self.current_text_index += 1
            self.load_current_text()
            return

        if self.current_lesson_index < len(self.lessons) - 1:
            next_row = self.lesson_offset + self.current_lesson_index + 1
            self.lesson_list.setCurrentRow(next_row)
            return

        self._update_description("🏆 Congratulations! You've completed all lessons!", mode="complete")

    def _update_best_wpm_label(self) -> None:
        if self.mode != "lesson":
            self.best_wpm_label.setText("Best: --")
            return
        lesson_key = str(self.current_lesson_index)
        best = self.best_wpm.get(lesson_key)
        self.best_wpm_label.setText(f"Best: {best}")

    def _save_progress(self) -> None:
        if self.mode != "lesson":
            return
        self.progress_store.data["current_lesson_index"] = self.current_lesson_index
        self.progress_store.data["current_text_index"] = self.current_text_index
        self.progress_store.data["best_wpm"] = self.best_wpm.to_dict()
        self.progress_store.save()

    def _update_description(self, text: str, mode: str = "default") -> None:
        style = {
            "default": self.description_default_style,
            "success": self.description_success_style,
            "complete": self.description_completion_style,
        }.get(mode, self.description_default_style)

        self.lesson_description.setStyleSheet(style)
        self.lesson_description.setText(text)

    def _show_statistics(self) -> None:
        """Show the statistics dialog."""
        dialog = StatisticsDialog(self.progress_store, self.lessons, self)
        dialog.exec()

    def _show_settings(self) -> None:
        """Show the settings dialog."""
        dialog = SettingsDialog(self.progress_store, self)
        dialog.settings_changed.connect(self._apply_settings)
        dialog.exec()
