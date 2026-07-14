import csv
from datetime import datetime
from typing import List

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
from core.themes import get_theme_names, get_theme
from core.charts import (
    create_combined_progress_chart,
    create_lesson_performance_chart,
    create_error_timeseries_chart,
)
from core.heatmap import (
    create_keyboard_heatmap,
    create_finger_error_chart,
)
from core.analytics import (
    compute_streaks,
    get_practice_recommendations,
    normalize_stats_for_display,
)
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
    DEVELOPER_KEYS_MODES,
    DEFAULT_THEME,
    DEFAULT_ADAPTIVE_DRILLS,
    DEFAULT_TIMED_MODE_SECONDS,
    TIMED_MODE_OPTIONS,
)

class StatisticsDialog(QDialog):
    """Dialog displaying comprehensive statistics and session history."""

    def __init__(self, progress_store: ProgressStore, lessons: List[Lesson], parent=None):
        super().__init__(parent)
        self.progress_store = progress_store
        self.lessons = lessons
        self.setWindowTitle("📊 Typing Statistics")
        self.setMinimumSize(700, 550)
        self._built_tabs: set[int] = set()
        self._building_tabs: set[int] = set()
        self._chart_cache: dict[tuple, object] = {}
        self._tab_specs = [
            ("📈 Overview", self._create_overview_tab),
            ("📊 Progress", self._create_progress_tab),
            ("🏆 Performance", self._create_performance_tab),
            ("📜 History", self._create_history_tab),
            ("🔥 Error Heatmap", self._create_heatmap_tab),
            ("📉 Error Trends", self._create_trends_tab),
        ]
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        for title, _ in self._tab_specs:
            self._tabs.addTab(QWidget(), title)
        self._tabs.currentChanged.connect(self._ensure_tab_built)
        layout.addWidget(self._tabs)

        button_layout = QHBoxLayout()

        export_btn = QPushButton("📁 Export to CSV")
        export_btn.clicked.connect(self._export_csv)
        button_layout.addWidget(export_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        self._ensure_tab_built(0)

    def _ensure_tab_built(self, index: int) -> None:
        """Lazy-load tab content on first visit."""
        if index < 0 or index in self._built_tabs or index in self._building_tabs:
            return

        self._building_tabs.add(index)
        title, _ = self._tab_specs[index]
        old = self._tabs.widget(index)

        loading = QWidget()
        loading_layout = QVBoxLayout(loading)
        loading_label = QLabel("Loading…")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(loading_label)

        self._tabs.removeTab(index)
        self._tabs.insertTab(index, loading, title)
        if old is not None:
            old.deleteLater()

        QTimer.singleShot(0, lambda idx=index: self._finish_tab_build(idx))

    def _finish_tab_build(self, index: int) -> None:
        """Build a statistics tab after yielding to the event loop."""
        if index in self._built_tabs:
            self._building_tabs.discard(index)
            return

        title, builder = self._tab_specs[index]
        widget = builder()
        self._tabs.removeTab(index)
        self._tabs.insertTab(index, widget, title)
        self._building_tabs.discard(index)
        self._built_tabs.add(index)

    def _chart_cache_key(self, chart_id: str, *, extra: str = "") -> tuple:
        history = self.progress_store.get_session_history()
        theme = self.progress_store.get_setting("theme", DEFAULT_THEME)
        last_ts = history[-1].get("timestamp", "") if history else ""
        return (chart_id, theme, len(history), last_ts, extra)

    def _get_cached_chart(self, cache_key: tuple, builder) -> object:
        if cache_key not in self._chart_cache:
            self._chart_cache[cache_key] = builder()
        return self._chart_cache[cache_key]

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

        current_streak, longest_streak, unique_days = compute_streaks(history)

        streak_group = QGroupBox("🔥 Practice Streak")
        streak_layout = QVBoxLayout(streak_group)
        streak_lines = [
            f"Current streak: {current_streak} day{'s' if current_streak != 1 else ''}",
            f"Longest streak: {longest_streak} day{'s' if longest_streak != 1 else ''}",
            f"Total practice days: {unique_days}",
        ]
        streak_label = QLabel("\n".join(streak_lines))
        streak_label.setStyleSheet("font-size: 14px;")
        streak_layout.addWidget(streak_label)
        layout.addWidget(streak_group)

        layout.addStretch()
        return widget

    def _create_progress_tab(self) -> QWidget:
        """Create the progress tab with matplotlib charts."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        history = self.progress_store.get_session_history()

        if not history:
            empty_label = QLabel("No session data yet. Complete some typing exercises to see progress!")
            empty_label.setStyleSheet("font-size: 14px; color: #666; padding: 20px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty_label)
            return widget

        # Get current theme
        theme_name = self.progress_store.get_setting("theme", DEFAULT_THEME)
        theme = get_theme(theme_name)

        # Combined progress chart
        progress_group = QGroupBox("📈 Performance Progress Over Time")
        progress_layout = QVBoxLayout(progress_group)
        
        progress_chart_label = QLabel()
        progress_pixmap = self._get_cached_chart(
            self._chart_cache_key("combined_progress"),
            lambda: create_combined_progress_chart(history, theme, max_sessions=20),
        )
        if not progress_pixmap.isNull():
            progress_chart_label.setPixmap(progress_pixmap)
            progress_chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            progress_chart_label.setText("No data available")
            progress_chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        progress_layout.addWidget(progress_chart_label)
        layout.addWidget(progress_group)

        # Lesson performance chart
        lesson_group = QGroupBox("📊 Average Performance by Lesson")
        lesson_layout = QVBoxLayout(lesson_group)
        
        lesson_chart_label = QLabel()
        lesson_pixmap = self._get_cached_chart(
            self._chart_cache_key("lesson_performance"),
            lambda: create_lesson_performance_chart(history, theme),
        )
        if not lesson_pixmap.isNull():
            lesson_chart_label.setPixmap(lesson_pixmap)
            lesson_chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            lesson_chart_label.setText("No data available")
            lesson_chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lesson_layout.addWidget(lesson_chart_label)
        layout.addWidget(lesson_group)

        layout.addStretch()
        return widget

    def _create_performance_tab(self) -> QWidget:
        """Create the performance tab with best scores and achievements."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        history = self.progress_store.get_session_history()
        raw_best_wpm_data = self.progress_store.data.get("best_wpm", {})
        best_wpm_map = raw_best_wpm_data if isinstance(raw_best_wpm_data, dict) else {}

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
                most_practiced = max(lesson_counts.items(), key=lambda item: item[1])[0]
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
                    weakest = min(weak_lessons.items(), key=lambda item: item[1])[0]
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
            best = best_wpm_map.get(str(i), 0)
            lines.append(f"  {lesson.title}: {best} WPM")
        
        lesson_text.setText("\n".join(lines) if lines else "No data yet")
        lesson_layout.addWidget(lesson_text)
        layout.addWidget(lesson_group)

        # Practice recommendations from per-key error rates
        errors = self.progress_store.get_key_error_stats()
        attempts = self.progress_store.get_key_attempt_stats()
        recommendations = get_practice_recommendations(errors, attempts)

        rec_group = QGroupBox("🎯 Practice These Keys")
        rec_layout = QVBoxLayout(rec_group)
        rec_text = QTextEdit()
        rec_text.setReadOnly(True)
        rec_text.setMaximumHeight(140)
        rec_text.setFont(QFont("Courier New", 11))

        if recommendations:
            rec_lines = ["Rank | Key    | Error Rate | Errors / Attempts"]
            rec_lines.append("-" * 45)
            for i, (key, rate, err_count, att_count) in enumerate(recommendations, 1):
                key_display = key.upper() if key != " " else "SPACE"
                rec_lines.append(
                    f" {i:2d}  | {key_display:6s} | {rate * 100:5.1f}%     | {err_count:4d} / {att_count}"
                )
            rec_text.setText("\n".join(rec_lines))
        else:
            rec_text.setText(
                "Complete more sessions (10+ attempts per key) to unlock targeted recommendations."
            )

        rec_layout.addWidget(rec_text)
        layout.addWidget(rec_group)

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

    def _create_heatmap_tab(self) -> QWidget:
        """Create the error heatmap tab showing problem keys, filterable by lesson."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        global_stats = self.progress_store.get_key_error_stats()

        if not global_stats:
            empty_label = QLabel("No error data yet. Complete some typing exercises to see your problem keys!")
            empty_label.setStyleSheet("font-size: 14px; color: #666; padding: 20px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty_label)
            return widget

        # Lesson filter — "All Lessons" shows the cumulative global stats,
        # each entry shows a single lesson's per-session error totals.
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Show errors for:"))
        self._heatmap_lesson_combo = QComboBox()
        self._heatmap_lesson_combo.addItem("All Lessons", userData=None)
        for entry in self.progress_store.get_lessons_with_error_data():
            self._heatmap_lesson_combo.addItem(
                entry["lesson_name"], userData=entry["lesson_index"]
            )
        self._heatmap_lesson_combo.currentIndexChanged.connect(self._on_heatmap_lesson_changed)
        filter_layout.addWidget(self._heatmap_lesson_combo, stretch=1)

        self._heatmap_rate_check = QCheckBox("Show error rate (%) instead of raw counts")
        self._heatmap_rate_check.stateChanged.connect(self._on_heatmap_lesson_changed)
        filter_layout.addWidget(self._heatmap_rate_check)
        layout.addLayout(filter_layout)

        # Container whose contents are rebuilt when the lesson filter changes.
        self._heatmap_content = QWidget()
        self._heatmap_content_layout = QVBoxLayout(self._heatmap_content)
        self._heatmap_content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._heatmap_content)

        self._render_heatmap_content(global_stats, self.progress_store.get_key_attempt_stats())
        return widget

    def _on_heatmap_lesson_changed(self, index: int = 0) -> None:
        """Re-render the heatmap content for the selected lesson (or all)."""
        if not hasattr(self, "_heatmap_lesson_combo"):
            return

        lesson_index = self._heatmap_lesson_combo.currentData()
        if lesson_index is None:
            errors = self.progress_store.get_key_error_stats()
            attempts = self.progress_store.get_key_attempt_stats()
        else:
            errors = self.progress_store.get_lesson_key_errors(lesson_index)
            attempts = self.progress_store.get_lesson_key_attempts(lesson_index)
        self._render_heatmap_content(errors, attempts)

    def _render_heatmap_content(
        self,
        key_error_stats: dict,
        key_attempt_stats: dict | None = None,
    ) -> None:
        """Populate the heatmap container with charts for the given stats."""
        # Clear any previously rendered content.
        while self._heatmap_content_layout.count():
            item = self._heatmap_content_layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.deleteLater()

        layout = self._heatmap_content_layout

        if not key_error_stats:
            empty_label = QLabel("No error data for this lesson yet.")
            empty_label.setStyleSheet("font-size: 14px; color: #666; padding: 20px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty_label)
            return

        theme_name = self.progress_store.get_setting("theme", DEFAULT_THEME)
        theme = get_theme(theme_name)

        use_error_rate = (
            hasattr(self, "_heatmap_rate_check")
            and self._heatmap_rate_check.isChecked()
            and key_attempt_stats
        )
        display_stats = normalize_stats_for_display(
            key_error_stats,
            key_attempt_stats,
            use_error_rate=use_error_rate,
        )
        metric_label = "Error Rate" if use_error_rate else "Errors"
        value_suffix = "%" if use_error_rate else ""

        # Keyboard heatmap
        heatmap_group = QGroupBox("⌨️ Keyboard Error Heatmap")
        heatmap_layout = QVBoxLayout(heatmap_group)

        heatmap_label = QLabel()
        heatmap_cache_key = self._chart_cache_key(
            "keyboard_heatmap",
            extra=f"{metric_label}:{sorted(display_stats.items())!r}",
        )
        heatmap_pixmap = self._get_cached_chart(
            heatmap_cache_key,
            lambda: create_keyboard_heatmap(
                display_stats,
                theme,
                metric_label=metric_label,
                value_suffix=value_suffix,
            ),
        )
        if not heatmap_pixmap.isNull():
            heatmap_label.setPixmap(heatmap_pixmap)
        else:
            heatmap_label.setText("No data available")
        heatmap_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heatmap_layout.addWidget(heatmap_label)
        layout.addWidget(heatmap_group)

        # Finger error chart
        finger_group = QGroupBox("👆 Errors by Finger")
        finger_layout = QVBoxLayout(finger_group)

        finger_chart_label = QLabel()
        finger_cache_key = self._chart_cache_key(
            "finger_errors",
            extra=str(sorted(key_error_stats.items())),
        )
        finger_pixmap = self._get_cached_chart(
            finger_cache_key,
            lambda: create_finger_error_chart(key_error_stats, theme),
        )
        if not finger_pixmap.isNull():
            finger_chart_label.setPixmap(finger_pixmap)
        else:
            finger_chart_label.setText("No data available")
        finger_chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        finger_layout.addWidget(finger_chart_label)
        layout.addWidget(finger_group)

        # Top problem keys list
        problem_keys_group = QGroupBox("🎯 Most Problematic Keys")
        problem_keys_layout = QVBoxLayout(problem_keys_group)

        sorted_items = sorted(
            display_stats.items() if use_error_rate else key_error_stats.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        problem_text = QTextEdit()
        problem_text.setReadOnly(True)
        problem_text.setMaximumHeight(120)
        problem_text.setFont(QFont("Courier New", 11))

        if use_error_rate:
            lines = ["Rank | Key    | Error Rate"]
            lines.append("-" * 28)
            for i, (key, rate) in enumerate(sorted_items, 1):
                key_display = key.upper() if key != " " else "SPACE"
                lines.append(f" {i:2d}  | {key_display:6s} | {rate:5.1f}%")
        else:
            lines = ["Rank | Key    | Errors"]
            lines.append("-" * 25)
            for i, (key, count) in enumerate(sorted_items, 1):
                key_display = key.upper() if key != " " else "SPACE"
                lines.append(f" {i:2d}  | {key_display:6s} | {int(count):4d}")

        problem_text.setText("\n".join(lines))
        problem_keys_layout.addWidget(problem_text)
        layout.addWidget(problem_keys_group)

        layout.addStretch()

    def _create_trends_tab(self) -> QWidget:
        """Create the error-trends tab showing errors per session over time."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        timeseries = self.progress_store.get_error_timeseries()

        if not timeseries:
            empty_label = QLabel("No error trend data yet. Complete some typing exercises to track your progress!")
            empty_label.setStyleSheet("font-size: 14px; color: #666; padding: 20px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty_label)
            return widget

        theme_name = self.progress_store.get_setting("theme", DEFAULT_THEME)
        theme = get_theme(theme_name)

        trends_group = QGroupBox("📉 Errors Over Time")
        trends_layout = QVBoxLayout(trends_group)

        trends_label = QLabel()
        trends_pixmap = self._get_cached_chart(
            self._chart_cache_key("error_timeseries"),
            lambda: create_error_timeseries_chart(timeseries, theme),
        )
        if not trends_pixmap.isNull():
            trends_label.setPixmap(trends_pixmap)
        else:
            trends_label.setText("No data available")
        trends_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        trends_layout.addWidget(trends_label)
        layout.addWidget(trends_group)

        layout.addStretch()
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

        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(get_theme_names())
        current_theme = self.progress_store.get_setting("theme", DEFAULT_THEME)
        theme_index = self.theme_combo.findText(current_theme)
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)
        display_layout.addRow("Theme:", self.theme_combo)

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

        self.adaptive_drills_check = QCheckBox("Adaptive drills (emphasize weak keys)")
        self.adaptive_drills_check.setChecked(
            self.progress_store.get_setting("adaptive_drills", DEFAULT_ADAPTIVE_DRILLS)
        )
        self.adaptive_drills_check.setToolTip(
            "Weight Random Words drills toward keys with the highest error rates"
        )
        random_layout.addRow(self.adaptive_drills_check)

        layout.addWidget(random_group)

        # Timed Mode Settings
        timed_group = QGroupBox("⏱ Timed Mode")
        timed_layout = QFormLayout(timed_group)

        self.timed_mode_combo = QComboBox()
        for label, seconds in TIMED_MODE_OPTIONS:
            self.timed_mode_combo.addItem(label, userData=seconds)
        current_timed = self.progress_store.get_setting(
            "timed_mode_seconds", DEFAULT_TIMED_MODE_SECONDS
        )
        for index in range(self.timed_mode_combo.count()):
            if self.timed_mode_combo.itemData(index) == current_timed:
                self.timed_mode_combo.setCurrentIndex(index)
                break
        self.timed_mode_combo.setToolTip(
            "Countdown starts on first keystroke. Random/Developer drills generate "
            "enough text for the full duration; session ends when time expires."
        )
        timed_layout.addRow("Duration:", self.timed_mode_combo)
        layout.addWidget(timed_group)

        # Developer Keys Settings
        developer_group = QGroupBox("⌨️ Developer Keys Settings")
        developer_layout = QFormLayout(developer_group)

        self.developer_length_spin = QSpinBox()
        self.developer_length_spin.setRange(8, 100)
        self.developer_length_spin.setValue(
            self.progress_store.get_setting("developer_keys_length", DEFAULT_DEVELOPER_KEYS_LENGTH)
        )
        self.developer_length_spin.setSuffix(" tokens")
        self.developer_length_spin.setToolTip("Number of developer-key tokens to generate")
        developer_layout.addRow("Drill Length:", self.developer_length_spin)

        self.developer_mode_combo = QComboBox()
        self.developer_mode_combo.addItems(list(DEVELOPER_KEYS_MODES))
        current_mode = self.progress_store.get_setting("developer_keys_mode", DEFAULT_DEVELOPER_KEYS_MODE)
        mode_index = self.developer_mode_combo.findText(current_mode)
        if mode_index >= 0:
            self.developer_mode_combo.setCurrentIndex(mode_index)
        self.developer_mode_combo.setToolTip("Choose symbol-heavy or code-snippet-heavy drills")
        developer_layout.addRow("Mode:", self.developer_mode_combo)

        layout.addWidget(developer_group)

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
        self.progress_store.set_setting("theme", self.theme_combo.currentText())
        self.progress_store.set_setting("show_celebration", self.celebration_check.isChecked())
        self.progress_store.set_setting("show_keyboard", self.show_keyboard_check.isChecked())
        self.progress_store.set_setting("font_size", self.font_size_spin.value())
        self.progress_store.set_setting("random_word_count", self.word_count_spin.value())
        self.progress_store.set_setting("adaptive_drills", self.adaptive_drills_check.isChecked())
        self.progress_store.set_setting(
            "timed_mode_seconds", self.timed_mode_combo.currentData()
        )
        self.progress_store.set_setting("developer_keys_length", self.developer_length_spin.value())
        self.progress_store.set_setting("developer_keys_mode", self.developer_mode_combo.currentText())
        self.settings_changed.emit()
        self.accept()
