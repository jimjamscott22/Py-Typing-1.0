"""Tests for persistence, analytics, and word generation."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from core.analytics import compute_streaks, get_practice_recommendations
from core.models import SessionRecord
from core.persistence import ProgressStore
from core.wordgen import generate_adaptive_text, generate_text


@pytest.fixture
def store(tmp_path: Path) -> ProgressStore:
    progress_path = tmp_path / "typing_progress.json"
    return ProgressStore(progress_path)


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
