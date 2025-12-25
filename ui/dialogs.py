import csv
from datetime import datetime
from typing import List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.persistence import ProgressStore
from core.models import Lesson
from core.constants import (
    DEFAULT_BACKSPACE_PENALTY,
    DEFAULT_BACKSPACE_ACCURACY_WEIGHT,
    DEFAULT_STRICT_MODE,
    DEFAULT_DARK_MODE,
    DEFAULT_SHOW_KEYBOARD,
    DEFAULT_SHOW_CELEBRATION,
    DEFAULT_FONT_SIZE,
    DEFAULT_RANDOM_WORD_COUNT,
)

class StatisticsDialog(QDialog):
    """Dialog displaying comprehensive statistics and session history."""

    def __init__(self, progress_store: ProgressStore, lessons: List[Lesson], parent=None):
        super().__init__(parent)
        self.progress_store = progress_store
        self.lessons = lessons
        self.setWindowTitle("📊 Typing Statistics")
        self.setMinimumSize(700, 550)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Create tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Overview tab
        overview_tab = self._create_overview_tab()
        tabs.addTab(overview_tab, "📈 Overview")

        # Progress tab
        progress_tab = self._create_progress_tab()
        tabs.addTab(progress_tab, "📊 Progress")

        # Performance tab
        performance_tab = self._create_performance_tab()
        tabs.addTab(performance_tab, "🏆 Performance")

        # History tab
        history_tab = self._create_history_tab()
        tabs.addTab(history_tab, "📜 History")

        # Buttons
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("📁 Export to CSV")
        export_btn.clicked.connect(self._export_csv)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

    def _create_overview_tab(self) -> QWidget:
        """Create the overview statistics tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        history = self.progress_store.get_session_history()

        # Calculate statistics
        total_sessions = len(history)
        total_time = sum(s.get("duration_seconds", 0) for s in history)
        total_chars = sum(s.get("text_length", 0) for s in history)
        avg_wpm = sum(s.get("wpm", 0) for s in history) / max(total_sessions, 1)
        avg_accuracy = sum(s.get("accuracy", 0) for s in history) / max(total_sessions, 1)
        total_backspaces = sum(s.get("backspaces", 0) for s in history)

        # Format time
        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

        # Create statistics display
        stats_group = QGroupBox("📊 Overall Statistics")
        stats_layout = QGridLayout(stats_group)

        stats = [
            ("Total Practice Sessions:", str(total_sessions)),
            ("Total Time Practiced:", time_str),
            ("Total Characters Typed:", f"{total_chars:,}"),
            ("Average WPM:", f"{avg_wpm:.1f}"),
            ("Average Accuracy:", f"{avg_accuracy:.1f}%"),
            ("Total Backspaces Used:", f"{total_backspaces:,}"),
        ]

        for i, (label, value) in enumerate(stats):
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-weight: bold;")
            value_widget = QLabel(value)
            value_widget.setStyleSheet("font-size: 16px; color: #2196F3;")
            stats_layout.addWidget(label_widget, i, 0)
            stats_layout.addWidget(value_widget, i, 1)

        layout.addWidget(stats_group)

        # Practice streak (simplified - counts unique days)
        unique_days = set()
        for s in history:
            try:
                dt = datetime.fromisoformat(s.get("timestamp", ""))
                unique_days.add(dt.date())
            except (ValueError, TypeError):
                pass

        streak_group = QGroupBox("🔥 Practice Streak")
        streak_layout = QVBoxLayout(streak_group)
        streak_label = QLabel(f"You've practiced on {len(unique_days)} unique days!")
        streak_label.setStyleSheet("font-size: 14px;")
        streak_layout.addWidget(streak_label)
        layout.addWidget(streak_group)

        layout.addStretch()
        return widget

    def _create_progress_tab(self) -> QWidget:
        """Create the progress tab with text-based charts."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        history = self.progress_store.get_session_history()

        if not history:
            empty_label = QLabel("No session data yet. Complete some typing exercises to see progress!")
            empty_label.setStyleSheet("font-size: 14px; color: #666; padding: 20px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty_label)
            return widget

        # WPM Progress (last 20 sessions)
        wpm_group = QGroupBox("📈 WPM Progress (Last 20 Sessions)")
        wpm_layout = QVBoxLayout(wpm_group)
        
        last_20 = history[-20:]
        max_wpm = max((s.get("wpm", 0) for s in last_20), default=1)
        
        wpm_chart = QTextEdit()
        wpm_chart.setReadOnly(True)
        wpm_chart.setMaximumHeight(150)
        wpm_chart.setFont(QFont("Courier New", 9))
        
        chart_lines = []
        for i, s in enumerate(last_20):
            wpm = s.get("wpm", 0)
            bar_len = int((wpm / max(max_wpm, 1)) * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            chart_lines.append(f"#{i+1:2d} |{bar}| {wpm:3d} WPM")
        
        wpm_chart.setText("\n".join(chart_lines))
        wpm_layout.addWidget(wpm_chart)
        layout.addWidget(wpm_group)

        # Accuracy Progress
        acc_group = QGroupBox("🎯 Accuracy Progress (Last 20 Sessions)")
        acc_layout = QVBoxLayout(acc_group)
        
        acc_chart = QTextEdit()
        acc_chart.setReadOnly(True)
        acc_chart.setMaximumHeight(150)
        acc_chart.setFont(QFont("Courier New", 9))
        
        chart_lines = []
        for i, s in enumerate(last_20):
            acc = s.get("accuracy", 0)
            bar_len = int((acc / 100) * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            chart_lines.append(f"#{i+1:2d} |{bar}| {acc:5.1f}%")
        
        acc_chart.setText("\n".join(chart_lines))
        acc_layout.addWidget(acc_chart)
        layout.addWidget(acc_group)

        layout.addStretch()
        return widget

    def _create_performance_tab(self) -> QWidget:
        """Create the performance tab with best scores and achievements."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        history = self.progress_store.get_session_history()
        best_wpm_data = self.progress_store.data.get("best_wpm", {})

        # Best scores group
        best_group = QGroupBox("🏆 Personal Bests")
        best_layout = QGridLayout(best_group)

        if history:
            # Best WPM ever
            best_session = max(history, key=lambda s: s.get("wpm", 0))
            best_wpm = best_session.get("wpm", 0)
            best_lesson = best_session.get("lesson_name", "Unknown")
            best_date = best_session.get("timestamp", "Unknown")[:10]
            
            best_layout.addWidget(QLabel("Best WPM Ever:"), 0, 0)
            best_wpm_label = QLabel(f"{best_wpm} WPM")
            best_wpm_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #4CAF50;")
            best_layout.addWidget(best_wpm_label, 0, 1)
            best_layout.addWidget(QLabel(f"({best_lesson} on {best_date})"), 0, 2)

            # Best accuracy ever
            best_acc_session = max(history, key=lambda s: s.get("accuracy", 0))
            best_acc = best_acc_session.get("accuracy", 0)
            
            best_layout.addWidget(QLabel("Best Accuracy Ever:"), 1, 0)
            best_acc_label = QLabel(f"{best_acc:.1f}%")
            best_acc_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2196F3;")
            best_layout.addWidget(best_acc_label, 1, 1)

            # Most practiced lesson
            lesson_counts = {}
            for s in history:
                name = s.get("lesson_name", "Unknown")
                lesson_counts[name] = lesson_counts.get(name, 0) + 1
            
            if lesson_counts:
                most_practiced = max(lesson_counts, key=lesson_counts.get)
                best_layout.addWidget(QLabel("Most Practiced Lesson:"), 2, 0)
                mp_label = QLabel(f"{most_practiced} ({lesson_counts[most_practiced]} times)")
                mp_label.setStyleSheet("font-size: 14px; color: #FF9800;")
                best_layout.addWidget(mp_label, 2, 1, 1, 2)

                # Weakest lesson (lowest avg WPM with at least 3 sessions)
                lesson_wpms = {}
                for s in history:
                    name = s.get("lesson_name", "Unknown")
                    if name not in lesson_wpms:
                        lesson_wpms[name] = []
                    lesson_wpms[name].append(s.get("wpm", 0))
                
                weak_lessons = {k: sum(v)/len(v) for k, v in lesson_wpms.items() if len(v) >= 2}
                if weak_lessons:
                    weakest = min(weak_lessons, key=weak_lessons.get)
                    best_layout.addWidget(QLabel("Needs Practice:"), 3, 0)
                    weak_label = QLabel(f"{weakest} (avg {weak_lessons[weakest]:.0f} WPM)")
                    weak_label.setStyleSheet("font-size: 14px; color: #F06292;")
                    best_layout.addWidget(weak_label, 3, 1, 1, 2)
        else:
            no_data_label = QLabel("Complete sessions to see your personal bests!")
            best_layout.addWidget(no_data_label, 0, 0, 1, 3)

        layout.addWidget(best_group)

        # Per-lesson best WPM
        lesson_group = QGroupBox("📚 Best WPM by Lesson")
        lesson_layout = QVBoxLayout(lesson_group)
        
        lesson_text = QTextEdit()
        lesson_text.setReadOnly(True)
        lesson_text.setMaximumHeight(200)
        
        lines = []
        for i, lesson in enumerate(self.lessons):
            best = best_wpm_data.get(str(i), 0)
            lines.append(f"  {lesson.title}: {best} WPM")
        
        lesson_text.setText("\n".join(lines) if lines else "No data yet")
        lesson_layout.addWidget(lesson_text)
        layout.addWidget(lesson_group)

        layout.addStretch()
        return widget

    def _create_history_tab(self) -> QWidget:
        """Create the history tab showing recent sessions."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        history = self.progress_store.get_session_history()

        if not history:
            empty_label = QLabel("No session history yet.")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty_label)
            return widget

        # Create scrollable text display
        history_text = QTextEdit()
        history_text.setReadOnly(True)
        history_text.setFont(QFont("Courier New", 10))

        lines = ["Date/Time           | Lesson                    | WPM | Acc%  | Errs | ⌫   | Time"]
        lines.append("-" * 90)
        
        for s in reversed(history[-50:]):  # Show last 50, newest first
            timestamp = s.get("timestamp", "")[:16]
            lesson = s.get("lesson_name", "Unknown")[:25].ljust(25)
            wpm = s.get("wpm", 0)
            acc = s.get("accuracy", 0)
            errors = s.get("errors", 0)
            backspaces = s.get("backspaces", 0)
            duration = s.get("duration_seconds", 0)
            
            lines.append(f"{timestamp} | {lesson} | {wpm:3d} | {acc:5.1f} | {errors:4d} | {backspaces:3d} | {duration:5.1f}s")

        history_text.setText("\n".join(lines))
        layout.addWidget(history_text)

        return widget

    def _export_csv(self) -> None:
        """Export session history to CSV file."""
        history = self.progress_store.get_session_history()
        
        if not history:
            QMessageBox.information(self, "Export", "No session history to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Statistics",
            f"typing_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Date", "Lesson", "WPM", "Accuracy", "Errors", 
                    "Backspaces", "Duration (s)", "Characters"
                ])
                
                for s in history:
                    writer.writerow([
                        s.get("timestamp", ""),
                        s.get("lesson_name", ""),
                        s.get("wpm", 0),
                        s.get("accuracy", 0),
                        s.get("errors", 0),
                        s.get("backspaces", 0),
                        round(s.get("duration_seconds", 0), 1),
                        s.get("text_length", 0),
                    ])
            
            QMessageBox.information(self, "Export Successful", f"Statistics exported to:\n{file_path}")
        except OSError as e:
            QMessageBox.warning(self, "Export Failed", f"Could not save file:\n{e}")


class SettingsDialog(QDialog):
    """Settings dialog for configuring app behavior."""

    settings_changed = pyqtSignal()

    def __init__(self, progress_store: ProgressStore, parent=None):
        super().__init__(parent)
        self.progress_store = progress_store
        self.setWindowTitle("⚙️ Settings")
        self.setMinimumWidth(400)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Backspace Penalty Settings
        penalty_group = QGroupBox("⌫ Backspace Penalty Settings")
        penalty_layout = QFormLayout(penalty_group)

        # WPM penalty slider
        self.wpm_penalty_slider = QSlider(Qt.Orientation.Horizontal)
        self.wpm_penalty_slider.setRange(0, 10)
        self.wpm_penalty_slider.setValue(
            int(self.progress_store.get_setting("backspace_penalty", DEFAULT_BACKSPACE_PENALTY))
        )
        self.wpm_penalty_label = QLabel(f"{self.wpm_penalty_slider.value()} WPM per backspace")
        self.wpm_penalty_slider.valueChanged.connect(
            lambda v: self.wpm_penalty_label.setText(f"{v} WPM per backspace")
        )
        penalty_layout.addRow("WPM Penalty:", self.wpm_penalty_slider)
        penalty_layout.addRow("", self.wpm_penalty_label)

        # Accuracy weight slider (0.0 to 2.0, stored as 0-20)
        self.acc_weight_slider = QSlider(Qt.Orientation.Horizontal)
        self.acc_weight_slider.setRange(0, 20)
        current_weight = self.progress_store.get_setting("backspace_accuracy_weight", DEFAULT_BACKSPACE_ACCURACY_WEIGHT)
        self.acc_weight_slider.setValue(int(current_weight * 10))
        self.acc_weight_label = QLabel(f"{self.acc_weight_slider.value() / 10:.1f} errors per backspace")
        self.acc_weight_slider.valueChanged.connect(
            lambda v: self.acc_weight_label.setText(f"{v / 10:.1f} errors per backspace")
        )
        penalty_layout.addRow("Accuracy Weight:", self.acc_weight_slider)
        penalty_layout.addRow("", self.acc_weight_label)

        # Strict mode checkbox
        self.strict_mode_check = QCheckBox("Enable Strict Mode (disable backspace entirely)")
        self.strict_mode_check.setChecked(
            self.progress_store.get_setting("strict_mode", DEFAULT_STRICT_MODE)
        )
        self.strict_mode_check.setToolTip(
            "When enabled, pressing backspace will have no effect and show a warning flash."
        )
        penalty_layout.addRow(self.strict_mode_check)

        layout.addWidget(penalty_group)

        # Display Settings
        display_group = QGroupBox("🖥️ Display Settings")
        display_layout = QFormLayout(display_group)

        # Dark mode
        self.dark_mode_check = QCheckBox("Dark Mode")
        self.dark_mode_check.setChecked(
            self.progress_store.get_setting("dark_mode", DEFAULT_DARK_MODE)
        )
        display_layout.addRow(self.dark_mode_check)

        # Celebration animation
        self.celebration_check = QCheckBox("Show Celebration Animation")
        self.celebration_check.setChecked(
            self.progress_store.get_setting("show_celebration", DEFAULT_SHOW_CELEBRATION)
        )
        display_layout.addRow(self.celebration_check)

        # Show keyboard
        self.show_keyboard_check = QCheckBox("Show Virtual Keyboard")
        self.show_keyboard_check.setChecked(
            self.progress_store.get_setting("show_keyboard", DEFAULT_SHOW_KEYBOARD)
        )
        display_layout.addRow(self.show_keyboard_check)

        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(12, 28)
        self.font_size_spin.setValue(
            self.progress_store.get_setting("font_size", DEFAULT_FONT_SIZE)
        )
        self.font_size_spin.setSuffix(" pt")
        display_layout.addRow("Font Size:", self.font_size_spin)

        layout.addWidget(display_group)

        # Random Words Settings
        random_group = QGroupBox("🎲 Random Words Settings")
        random_layout = QFormLayout(random_group)

        # Word count spinner
        self.word_count_spin = QSpinBox()
        self.word_count_spin.setRange(10, 100)
        self.word_count_spin.setValue(
            self.progress_store.get_setting("random_word_count", DEFAULT_RANDOM_WORD_COUNT)
        )
        self.word_count_spin.setSuffix(" words")
        self.word_count_spin.setToolTip("Number of random words to generate for practice")
        random_layout.addRow("Word Count:", self.word_count_spin)

        layout.addWidget(random_group)

        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)

    def _save_settings(self) -> None:
        """Save all settings and emit change signal."""
        self.progress_store.set_setting("backspace_penalty", self.wpm_penalty_slider.value())
        self.progress_store.set_setting("backspace_accuracy_weight", self.acc_weight_slider.value() / 10)
        self.progress_store.set_setting("strict_mode", self.strict_mode_check.isChecked())
        self.progress_store.set_setting("dark_mode", self.dark_mode_check.isChecked())
        self.progress_store.set_setting("show_celebration", self.celebration_check.isChecked())
        self.progress_store.set_setting("show_keyboard", self.show_keyboard_check.isChecked())
        self.progress_store.set_setting("font_size", self.font_size_spin.value())
        self.progress_store.set_setting("random_word_count", self.word_count_spin.value())
        self.settings_changed.emit()
        self.accept()
