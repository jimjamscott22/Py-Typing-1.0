"""Tests for persistence, analytics, and word generation."""

import json
import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QApplication, QGroupBox, QLabel, QTableWidget

from core.analytics import compute_streaks, get_practice_recommendations
from core.achievements import build_achievement_progress
from core.challenges import CHALLENGE_TEMPLATES, evaluate_challenge_progress, get_daily_challenge
from core.goals import evaluate_daily_goal, evaluate_weekly_goal
from core.models import SessionRecord
from core.persistence import ProgressStore
from core.themes import get_theme
from core.transitions import TransitionAggregate
from core.wordgen import generate_adaptive_text, generate_text, timed_word_count
from core.warmup import WARMUP_PHRASES, get_warmup_text
from ui.dialogs import SettingsDialog, StatisticsDialog
from ui.main_window import TypingPracticeApp
from ui.styles import accessible_text_color


@pytest.fixture
def store(tmp_path: Path) -> ProgressStore:
    progress_path = tmp_path / "typing_progress.json"
    return ProgressStore(progress_path)


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    win = TypingPracticeApp()
    yield win
    win.close()


class TestProgressStore:
    def test_settings_round_trip(self, store: ProgressStore):
        store.set_setting("backspace_penalty", 5)
        store.set_setting("theme", "Dark")
        assert store.get_setting("backspace_penalty") == 5
        assert store.get_setting("theme") == "Dark"

    def test_legacy_dark_mode_migrates_to_dark_theme(self, tmp_path: Path):
        progress_path = tmp_path / "typing_progress.json"
        progress_path.write_text(
            json.dumps({"settings": {"dark_mode": True}}),
            encoding="utf-8",
        )

        migrated = ProgressStore(progress_path)
        assert migrated.get_setting("theme") == "Dark"
        migrated.close()

        reloaded = ProgressStore(progress_path)
        assert reloaded.get_setting("theme") == "Dark"

    def test_save_persists_position(self, store: ProgressStore):
        store.data["current_lesson_index"] = 3
        store.data["current_text_index"] = 2
        store.save()

        reloaded = ProgressStore(store.path)
        assert reloaded.data["current_lesson_index"] == 3
        assert reloaded.data["current_text_index"] == 2

    def test_session_history_retention(self, store: ProgressStore):
        for i in range(ProgressStore.MAX_HISTORY_SIZE + 10):
            store.add_session_record(
                SessionRecord(
                    timestamp=datetime.now().isoformat(),
                    lesson_index=0,
                    text_index=0,
                    lesson_name="Test",
                    wpm=40 + i,
                    accuracy=95.0,
                    errors=0,
                    backspaces=0,
                    duration_seconds=30.0,
                    text_length=100,
                )
            )
        history = store.get_session_history()
        assert len(history) == ProgressStore.MAX_HISTORY_SIZE

    def test_key_stats_upsert(self, store: ProgressStore):
        store.update_key_error_stats({"a": 2, "s": 1})
        store.update_key_error_stats({"a": 1})
        stats = store.get_key_error_stats()
        assert stats["a"] == 3
        assert stats["s"] == 1

    def test_lesson_key_attempts(self, store: ProgressStore):
        store.add_session_key_stats(
            "2026-01-01T12:00:00",
            1,
            "Top Row",
            {"q": 2, "w": 1},
            {"q": 10, "w": 8},
        )
        errors = store.get_lesson_key_errors(1)
        attempts = store.get_lesson_key_attempts(1)
        assert errors["q"] == 2
        assert attempts["q"] == 10

    def test_achievement_unlocks_and_lesson_completions_persist(self, store: ProgressStore):
        timestamp = datetime.now().isoformat()
        store.mark_lesson_text_completed(2, 3, timestamp)
        assert store.unlock_achievements(["first_steps"], timestamp) == ["first_steps"]
        assert store.unlock_achievements(["first_steps"], timestamp) == []

        reloaded = ProgressStore(store.path)
        assert reloaded.get_unlocked_achievements()["first_steps"] == timestamp
        assert (2, 3) in reloaded.get_completed_lesson_texts()

    def test_coins_accumulate_and_persist(self, store: ProgressStore):
        assert store.get_coins_total() == 0
        assert store.add_coins(5) == 5
        assert store.add_coins(25) == 30

        reloaded = ProgressStore(store.path)
        assert reloaded.get_coins_total() == 30

    def test_challenge_completion_marked_once(self, store: ProgressStore):
        timestamp = datetime.now().isoformat()
        assert store.is_challenge_completed("2026-01-01") is False
        assert store.mark_challenge_completed("2026-01-01", "speed_burst_40", timestamp) is True
        assert store.is_challenge_completed("2026-01-01") is True
        assert store.mark_challenge_completed("2026-01-01", "speed_burst_40", timestamp) is False

        reloaded = ProgressStore(store.path)
        assert reloaded.is_challenge_completed("2026-01-01") is True

    def test_challenge_completion_awards_coins_atomically(self, store: ProgressStore):
        timestamp = datetime.now().isoformat()
        assert store.mark_challenge_completed(
            "2026-01-01", "speed_burst_40", timestamp, coin_reward=25
        ) is True
        assert store.get_coins_total() == 25

        # Already-completed challenges must not grant the reward again.
        assert store.mark_challenge_completed(
            "2026-01-01", "speed_burst_40", timestamp, coin_reward=25
        ) is False
        assert store.get_coins_total() == 25

        reloaded = ProgressStore(store.path)
        assert reloaded.is_challenge_completed("2026-01-01") is True
        assert reloaded.get_coins_total() == 25


class TestTransitionPersistence:
    def test_opening_a_pre_feature_database_adds_the_table_without_data_loss(
        self, tmp_path: Path,
    ):
        progress_path = tmp_path / "typing_progress.json"
        pre_feature = ProgressStore(progress_path)
        pre_feature.add_session_record(
            SessionRecord(
                timestamp="2026-01-01T00:00:00",
                lesson_index=0,
                text_index=0,
                lesson_name="Pre-existing",
                wpm=50,
                accuracy=98.0,
                errors=1,
                backspaces=0,
                duration_seconds=10.0,
                text_length=20,
            )
        )
        pre_feature.close()

        reopened = ProgressStore(progress_path)
        assert reopened.has_transition_data() is False
        history = reopened.get_session_history()
        assert len(history) == 1
        assert history[0]["lesson_name"] == "Pre-existing"

    def test_has_transition_data_reflects_presence(self, store: ProgressStore):
        assert store.has_transition_data() is False
        _seed_session(store, "2026-01-01T00:00:00", [
            TransitionAggregate("io", 2, 5, 500.0, 80.0, 120.0),
        ])
        assert store.has_transition_data() is True

    def test_round_trip_and_weighted_mean_across_sessions(self, store: ProgressStore):
        _seed_session(store, "2026-01-01T00:00:00", [
            TransitionAggregate("io", 2, 3, 300.0, 90.0, 110.0),
        ])
        _seed_session(store, "2026-01-02T00:00:00", [
            TransitionAggregate("io", 2, 2, 240.0, 115.0, 125.0),
        ])
        summaries = store.get_slowest_transitions(2, min_samples=1)
        io = next(s for s in summaries if s.sequence == "io")
        assert io.sample_count == 5
        # Weighted mean: (300 + 240) / (3 + 2) = 108.0, not (100 + 120) / 2.
        assert io.average_ms == pytest.approx(108.0)

    def test_bigram_and_trigram_baselines_are_independent(self, store: ProgressStore):
        _seed_session(store, "2026-01-01T00:00:00", [
            TransitionAggregate("io", 2, 5, 500.0, 90.0, 110.0),
            TransitionAggregate("on", 2, 5, 250.0, 40.0, 60.0),
            TransitionAggregate("ion", 3, 5, 1000.0, 190.0, 210.0),
        ])
        bigrams = store.get_slowest_transitions(2, min_samples=1)
        trigrams = store.get_slowest_transitions(3, min_samples=1)
        io = next(s for s in bigrams if s.sequence == "io")
        ion = next(s for s in trigrams if s.sequence == "ion")
        # Bigram baseline is (500+250)/(5+5)=75; trigram baseline is 1000/5=200.
        assert io.baseline_delta_percent == pytest.approx(((100.0 / 75.0) - 1) * 100)
        assert ion.baseline_delta_percent == pytest.approx(0.0)

    def test_minimum_sample_threshold_excludes_thin_sequences(self, store: ProgressStore):
        _seed_session(store, "2026-01-01T00:00:00", [
            TransitionAggregate("io", 2, 4, 400.0, 90.0, 110.0),
        ])
        assert store.get_slowest_transitions(2) == []
        assert len(store.get_slowest_transitions(2, min_samples=4)) == 1

    def test_custom_threshold_and_limit_are_respected(self, store: ProgressStore):
        _seed_session(store, "2026-01-01T00:00:00", [
            TransitionAggregate("io", 2, 6, 600.0, 90.0, 110.0),
            TransitionAggregate("on", 2, 6, 300.0, 40.0, 60.0),
        ])
        assert len(store.get_slowest_transitions(2, min_samples=1, limit=1)) == 1

    def test_ordering_is_deterministic_on_ties(self, store: ProgressStore):
        _seed_session(store, "2026-01-01T00:00:00", [
            TransitionAggregate("on", 2, 5, 500.0, 90.0, 110.0),
            TransitionAggregate("io", 2, 5, 500.0, 90.0, 110.0),
        ])
        summaries = store.get_slowest_transitions(2, min_samples=1)
        # Equal averages and sample counts fall back to sequence ascending.
        assert [s.sequence for s in summaries] == ["io", "on"]

    def test_lesson_filter_scopes_results(self, store: ProgressStore):
        store.add_session_record(_dummy_record("2026-01-01T00:00:00", lesson_index=0))
        store.add_session_transition_stats(
            "2026-01-01T00:00:00", 0, "Lesson A",
            [TransitionAggregate("io", 2, 5, 500.0, 90.0, 110.0)],
        )
        store.add_session_record(_dummy_record("2026-01-02T00:00:00", lesson_index=1))
        store.add_session_transition_stats(
            "2026-01-02T00:00:00", 1, "Lesson B",
            [TransitionAggregate("on", 2, 5, 250.0, 40.0, 60.0)],
        )
        scoped = store.get_slowest_transitions(2, min_samples=1, lesson_index=0)
        assert [s.sequence for s in scoped] == ["io"]

    def test_invalid_ngram_size_raises(self, store: ProgressStore):
        with pytest.raises(ValueError):
            store.get_slowest_transitions(4)

    def test_transition_rows_are_pruned_with_session_history_retention(
        self, store: ProgressStore,
    ):
        for i in range(ProgressStore.MAX_HISTORY_SIZE + 1):
            timestamp = f"2026-01-01T00:00:{i:02d}" if i < 60 else f"2026-01-01T00:01:{i - 60:02d}"
            store.add_session_record(_dummy_record(timestamp, lesson_index=0))
            aggregates = (
                [TransitionAggregate("io", 2, 1, 100.0, 100.0, 100.0)] if i == 0 else []
            )
            store.add_session_transition_stats(timestamp, 0, "Test", aggregates)

        # The very first session's transition row must be pruned once history
        # grows past the retention window, even though it wrote a real
        # aggregate and later sessions wrote none at all.
        assert store.get_slowest_transitions(2, min_samples=1) == []
        assert store.has_transition_data() is False


def _seed_session(store: ProgressStore, timestamp: str, aggregates) -> None:
    store.add_session_record(_dummy_record(timestamp, lesson_index=0))
    store.add_session_transition_stats(timestamp, 0, "Test Lesson", aggregates)


def _dummy_record(timestamp: str, lesson_index: int) -> SessionRecord:
    return SessionRecord(
        timestamp=timestamp,
        lesson_index=lesson_index,
        text_index=0,
        lesson_name="Test Lesson",
        wpm=40,
        accuracy=95.0,
        errors=0,
        backspaces=0,
        duration_seconds=10.0,
        text_length=20,
    )


class TestSettingsDialog:
    def test_save_emits_only_changed_setting_names(self, qapp, store: ProgressStore):
        store.set_setting("theme", "Light")
        dialog = SettingsDialog(store)
        emitted_args = []
        dialog.settings_changed.connect(lambda *args: emitted_args.append(args))

        dialog.theme_combo.setCurrentText("Dark")
        dialog._save_settings()

        assert emitted_args == [(frozenset({"theme"}),)]


class TestSettingsApplication:
    def test_theme_change_rebuilds_existing_typing_feedback(self, window):
        target = window.current_target_text
        window.typing_input.setPlainText(target[:1])
        QApplication.processEvents()

        window.current_theme = get_theme("Solarized Dark")
        window._apply_theme()

        assert (
            window.correct_char_format.background().color().name()
            == window.current_theme.description_success_bg
        )
        cursor = QTextCursor(window.typing_input.document())
        cursor.setPosition(0)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
        assert (
            cursor.charFormat().background().color().name()
            == window.current_theme.description_success_bg
        )
        assert window.current_theme.description_success_bg in window.target_text.text()
        expected_untyped = accessible_text_color(
            window.current_theme.text_secondary,
            window.current_theme.target_bg,
        )
        assert f"color: {expected_untyped}" in window.target_text.text()

    def test_visual_change_preserves_active_generated_drill(self, window):
        random_index = next(
            index
            for index, lesson in enumerate(window.lessons)
            if lesson.title == "Random Words"
        )
        window.load_lesson(random_index)
        original_target = window.current_target_text
        typed = original_target[:4]
        window.typing_input.setPlainText(typed)

        dialog = SettingsDialog(window.progress_store, window)
        dialog.settings_changed.connect(window._on_settings_changed)
        dialog.theme_combo.setCurrentText("Dark")
        dialog._save_settings()

        assert window.current_theme.name == "Dark"
        assert window.current_target_text == original_target
        assert window.typing_input.toPlainText() == typed
        assert window.session.typed_text == typed

    def test_generated_change_is_deferred_until_next_drill(self, window):
        random_index = next(
            index
            for index, lesson in enumerate(window.lessons)
            if lesson.title == "Random Words"
        )
        window.load_lesson(random_index)
        original_target = window.current_target_text
        typed = original_target[:4]
        window.typing_input.setPlainText(typed)

        dialog = SettingsDialog(window.progress_store, window)
        dialog.settings_changed.connect(window._on_settings_changed)
        dialog.word_count_spin.setValue(12)
        dialog._save_settings()

        assert window.current_target_text == original_target
        assert window.typing_input.toPlainText() == typed
        assert window.progress_store.get_random_text(random_index) is None

        window.load_lesson(random_index)
        assert len(window.current_target_text.split()) == 12
        assert window.typing_input.toPlainText() == ""

    def test_generated_change_applies_before_drill_starts(self, window):
        random_index = next(
            index
            for index, lesson in enumerate(window.lessons)
            if lesson.title == "Random Words"
        )
        window.load_lesson(random_index)
        assert len(window.current_target_text.split()) == 25

        dialog = SettingsDialog(window.progress_store, window)
        dialog.settings_changed.connect(window._on_settings_changed)
        dialog.word_count_spin.setValue(12)
        dialog._save_settings()

        assert len(window.current_target_text.split()) == 12
        assert window.typing_input.toPlainText() == ""

    def test_developer_change_is_deferred_until_next_drill(self, window):
        developer_index = next(
            index
            for index, lesson in enumerate(window.lessons)
            if lesson.title == "Developer Keys"
        )
        window.load_lesson(developer_index)
        original_target = window.current_target_text
        typed = original_target[:2]
        window.typing_input.setPlainText(typed)

        dialog = SettingsDialog(window.progress_store, window)
        dialog.settings_changed.connect(window._on_settings_changed)
        dialog.developer_length_spin.setValue(12)
        dialog._save_settings()

        assert window.current_target_text == original_target
        assert window.typing_input.toPlainText() == typed
        assert window.progress_store.get_developer_text(developer_index) is None

        window.load_lesson(developer_index)
        assert len(window.current_target_text.split()) == 12
        assert window.typing_input.toPlainText() == ""

    def test_timed_change_applies_after_active_exercise(self, window):
        window.progress_store.set_setting("timed_mode_seconds", 60)
        window._apply_settings()
        window.load_lesson(0)
        first_character = window.current_target_text[:1]
        window.typing_input.setPlainText(first_character)
        assert window._timed_mode_active
        assert window._timed_timer.isActive()

        dialog = SettingsDialog(window.progress_store, window)
        dialog.settings_changed.connect(window._on_settings_changed)
        dialog.timed_mode_combo.setCurrentIndex(
            dialog.timed_mode_combo.findData(0)
        )
        dialog._save_settings()

        assert window._timed_mode_seconds == 0
        assert window._timed_mode_active
        assert window._timed_timer.isActive()

        window.reset_exercise()
        window.typing_input.setPlainText(first_character)
        assert not window._timed_mode_active
        assert not window._timed_timer.isActive()


class TestTransitionsTab:
    TAB_INDEX = 6  # Overview, Progress, Performance, History, Heatmap, Trends, Transitions

    @staticmethod
    def _build_tab(dialog: StatisticsDialog):
        """Select the Transitions tab and force its lazy content to build."""
        dialog._tabs.setCurrentIndex(TestTransitionsTab.TAB_INDEX)
        dialog._finish_tab_build(TestTransitionsTab.TAB_INDEX)
        return dialog._tabs.widget(TestTransitionsTab.TAB_INDEX)

    def test_tab_remains_lazy_until_selected(self, qapp, store: ProgressStore):
        dialog = StatisticsDialog(store, [])
        assert self.TAB_INDEX not in dialog._built_tabs

    def test_no_data_empty_state(self, qapp, store: ProgressStore):
        dialog = StatisticsDialog(store, [])
        tab = self._build_tab(dialog)
        labels = tab.findChildren(QLabel)
        assert any("No transition timing data yet" in label.text() for label in labels)

    def test_collecting_state_when_below_threshold(self, qapp, store: ProgressStore):
        _seed_session(store, "2026-01-01T00:00:00", [
            TransitionAggregate("io", 2, 2, 200.0, 90.0, 110.0),
        ])
        dialog = StatisticsDialog(store, [])
        tab = self._build_tab(dialog)
        labels = tab.findChildren(QLabel)
        assert any("Collecting transition data" in label.text() for label in labels)
        groups = tab.findChildren(QGroupBox)
        assert any("Slowest Bigrams" in g.title() for g in groups)
        assert any("Slowest Trigrams" in g.title() for g in groups)

    def test_qualified_rows_render_expected_formatting(self, qapp, store: ProgressStore):
        _seed_session(store, "2026-01-01T00:00:00", [
            TransitionAggregate("i o", 2, 5, 555.0, 100.0, 120.0),
        ])
        dialog = StatisticsDialog(store, [])
        tab = self._build_tab(dialog)
        tables = tab.findChildren(QTableWidget)
        assert tables
        table = tables[0]
        assert table.rowCount() == 1
        assert table.item(0, 0).text() == "i␠o"
        assert table.item(0, 1).text() == "111 ms"
        assert table.item(0, 2).text() == "5"
        assert table.item(0, 3).text() == "At baseline"

    def test_slowest_and_baseline_groups_reachable_at_minimum_size(
        self, qapp, store: ProgressStore,
    ):
        _seed_session(store, "2026-01-01T00:00:00", [
            TransitionAggregate("io", 2, 5, 500.0, 90.0, 110.0),
            TransitionAggregate("ion", 3, 5, 1000.0, 190.0, 210.0),
        ])
        dialog = StatisticsDialog(store, [])
        dialog.resize(dialog.minimumSize())
        tab = self._build_tab(dialog)
        groups = {g.title(): g for g in tab.findChildren(QGroupBox)}
        assert any("Slowest Bigrams" in title for title in groups)
        assert any("Slowest Trigrams" in title for title in groups)


class TestAnalytics:
    def test_streaks_empty(self):
        assert compute_streaks([]) == (0, 0, 0)

    def test_consecutive_streak(self):
        today = datetime.now()
        history = [
            {"timestamp": today.isoformat()},
            {"timestamp": (today - timedelta(days=1)).isoformat()},
            {"timestamp": (today - timedelta(days=2)).isoformat()},
        ]
        current, longest, unique = compute_streaks(history)
        assert current == 3
        assert longest == 3
        assert unique == 3

    def test_broken_streak(self):
        today = datetime.now()
        history = [
            {"timestamp": (today - timedelta(days=5)).isoformat()},
            {"timestamp": (today - timedelta(days=4)).isoformat()},
        ]
        current, longest, _ = compute_streaks(history)
        assert current == 0
        assert longest == 2

    def test_practice_recommendations_min_attempts(self):
        errors = {"a": 5, "s": 1}
        attempts = {"a": 20, "s": 5}
        recs = get_practice_recommendations(errors, attempts, min_attempts=10)
        assert len(recs) == 1
        assert recs[0][0] == "a"


class TestAchievements:
    def test_balanced_badge_set_can_all_be_earned(self):
        today = datetime.now()
        history = []
        for index in range(50):
            history.append(
                {
                    "timestamp": (today - timedelta(days=index % 7)).isoformat(),
                    "wpm": 75,
                    "accuracy": 100.0,
                    "errors": 0,
                    "backspaces": 0,
                    "text_length": 100,
                }
            )

        statuses = build_achievement_progress(
            history,
            {},
            {(0, 0), (0, 1), (1, 0)},
            [2, 1],
        )

        assert len(statuses) == 12
        assert all(status.earned for status in statuses)

    def test_quality_badges_require_meaningful_text_length(self):
        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "wpm": 10,
                "accuracy": 100.0,
                "errors": 0,
                "backspaces": 0,
                "text_length": 5,
            }
        ]

        statuses = {
            status.achievement.id: status
            for status in build_achievement_progress(history, {}, set(), [1])
        }

        assert statuses["first_steps"].earned
        assert not statuses["perfect_accuracy"].earned
        assert not statuses["zero_errors"].earned
        assert not statuses["zero_backspaces"].earned


class TestChallenges:
    def test_daily_challenge_is_deterministic_per_day(self):
        today = date(2026, 3, 5)
        assert get_daily_challenge(today) == get_daily_challenge(today)

    def test_daily_challenge_always_from_pool(self):
        for offset in range(30):
            challenge = get_daily_challenge(date(2026, 1, 1) + timedelta(days=offset))
            assert challenge in CHALLENGE_TEMPLATES

    def test_best_wpm_challenge_progress(self):
        today = date(2026, 3, 5)
        challenge = next(c for c in CHALLENGE_TEMPLATES if c.metric == "best_wpm")
        history = [
            {"timestamp": datetime(2026, 3, 5, 9, 0).isoformat(), "wpm": challenge.target - 5},
            {"timestamp": datetime(2026, 3, 4, 9, 0).isoformat(), "wpm": 999},  # yesterday, ignored
        ]
        progress = evaluate_challenge_progress(challenge, history, today)
        assert not progress.completed
        assert progress.current == challenge.target - 5

        history.append({"timestamp": datetime(2026, 3, 5, 10, 0).isoformat(), "wpm": challenge.target})
        progress = evaluate_challenge_progress(challenge, history, today)
        assert progress.completed

    def test_session_count_challenge_progress(self):
        today = date(2026, 3, 5)
        challenge = next(c for c in CHALLENGE_TEMPLATES if c.metric == "session_count")
        history = [
            {"timestamp": datetime(2026, 3, 5, h, 0).isoformat()}
            for h in range(int(challenge.target) - 1)
        ]
        assert not evaluate_challenge_progress(challenge, history, today).completed

        history.append({"timestamp": datetime(2026, 3, 5, 23, 0).isoformat()})
        assert evaluate_challenge_progress(challenge, history, today).completed


class TestGoals:
    def test_daily_goal_counts_only_today(self):
        today = date(2026, 3, 5)
        history = [
            {"timestamp": datetime(2026, 3, 5, 9, 0).isoformat(), "duration_seconds": 300},
            {"timestamp": datetime(2026, 3, 4, 9, 0).isoformat(), "duration_seconds": 600},
        ]
        minutes, met = evaluate_daily_goal(history, goal_minutes=10, for_date=today)
        assert minutes == 5.0
        assert not met

        minutes, met = evaluate_daily_goal(history, goal_minutes=5, for_date=today)
        assert met

    def test_weekly_goal_counts_current_week_only(self):
        # 2026-03-05 is a Thursday; week starts Monday 2026-03-02.
        today = date(2026, 3, 5)
        history = [
            {"timestamp": datetime(2026, 3, 3, 9, 0).isoformat()},
            {"timestamp": datetime(2026, 3, 5, 9, 0).isoformat()},
            {"timestamp": datetime(2026, 2, 27, 9, 0).isoformat()},  # prior week
        ]
        count, met = evaluate_weekly_goal(history, goal_sessions=2, for_date=today)
        assert count == 2
        assert met
        assert not evaluate_weekly_goal(history, goal_sessions=3, for_date=today)[1]


class TestWordgen:
    def test_generate_text_count(self):
        text = generate_text(15)
        assert len(text.split()) == 15

    def test_generate_adaptive_text_uses_weak_keys(self):
        text = generate_adaptive_text(["q", "w"], word_count=20)
        words = text.split()
        assert len(words) == 20
        # Most words should contain q or w given 70% weighting
        weak_hits = sum(1 for w in words if "q" in w or "w" in w)
        assert weak_hits >= 5

    def test_generate_adaptive_fallback_without_keys(self):
        text = generate_adaptive_text([], word_count=10)
        assert len(text.split()) == 10

    def test_timed_word_count_off_uses_base(self):
        assert timed_word_count(0, base_count=25) == 25

    def test_timed_word_count_scales_with_duration(self):
        # 60s @ 80 WPM * 1.5 = 120 words
        assert timed_word_count(60, base_count=25) == 120
        assert timed_word_count(120, base_count=25) == 240
        assert timed_word_count(300, base_count=25) == 600

    def test_timed_word_count_respects_higher_base(self):
        assert timed_word_count(60, base_count=150) == 150


class TestWarmup:
    def test_get_warmup_text_returns_known_phrase(self):
        text = get_warmup_text()
        assert text in WARMUP_PHRASES

    def test_get_warmup_text_avoids_immediate_repeat(self):
        first = get_warmup_text()
        for _ in range(20):
            second = get_warmup_text(exclude=first)
            assert second != first


class TestWarmupToggle:
    def test_enter_warmup_sets_mode_and_disables_controls(self, window):
        window._toggle_warmup_mode(True)
        assert window.mode == "warmup"
        assert window.warmup_mode is True
        assert not window.lesson_list.isEnabled()
        assert not window.free_controls.isEnabled()

    def test_exit_warmup_restores_previous_lesson(self, window):
        window.load_lesson(1, reset_text_index=False)
        prior_index = window.current_lesson_index

        window._toggle_warmup_mode(True)
        assert window.mode == "warmup"

        window._toggle_warmup_mode(False)
        assert window.mode == "lesson"
        assert window.warmup_mode is False
        assert window.current_lesson_index == prior_index
        assert window.lesson_list.isEnabled()

    def test_completing_warmup_round_does_not_persist(self, window, monkeypatch):
        added = []
        saved = []
        monkeypatch.setattr(
            window.progress_store, "add_session_record", lambda record: added.append(record)
        )
        monkeypatch.setattr(window.progress_store, "save", lambda: saved.append(True))

        window._toggle_warmup_mode(True)
        target = window.current_target_text
        window.typing_input.setPlainText(target)

        assert added == []
        assert saved == []

    def test_normal_completion_still_persists_after_exiting_warmup(self, window, monkeypatch):
        added = []
        saved = []
        monkeypatch.setattr(
            window.progress_store, "add_session_record", lambda record: added.append(record)
        )
        monkeypatch.setattr(window.progress_store, "save", lambda: saved.append(True))

        window._toggle_warmup_mode(True)
        window._toggle_warmup_mode(False)
        assert window.mode == "lesson"

        target = window.current_target_text
        window.typing_input.setPlainText(target)

        assert len(added) == 1
        assert saved


class TestRewardsIntegration:
    def test_completing_a_session_awards_coins_and_refreshes_strip(self, window):
        from core.constants import SESSION_COIN_REWARD

        assert window.progress_store.get_coins_total() == 0
        target = window.current_target_text
        window.typing_input.setPlainText(target)

        # An instant, error-free completion may also satisfy today's actual
        # daily challenge, so only assert the session reward is included —
        # not an exact total, which depends on which challenge is live today.
        total = window.progress_store.get_coins_total()
        assert total >= SESSION_COIN_REWARD
        assert window.coins_value_label.text() == f"🪙 {total}"

    def test_warmup_completion_awards_no_coins(self, window):
        window._toggle_warmup_mode(True)
        target = window.current_target_text
        window.typing_input.setPlainText(target)

        assert window.progress_store.get_coins_total() == 0
