"""Tests for persistence, analytics, and word generation."""

import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from core.analytics import compute_streaks, get_practice_recommendations
from core.achievements import build_achievement_progress
from core.challenges import CHALLENGE_TEMPLATES, evaluate_challenge_progress, get_daily_challenge
from core.goals import evaluate_daily_goal, evaluate_weekly_goal
from core.models import SessionRecord
from core.persistence import ProgressStore
from core.wordgen import generate_adaptive_text, generate_text, timed_word_count
from core.warmup import WARMUP_PHRASES, get_warmup_text
from ui.main_window import TypingPracticeApp


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
