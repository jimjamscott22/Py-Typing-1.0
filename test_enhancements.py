"""Tests for the per-session key-error tracking foundation.

Covers the persistence layer that powers per-lesson heatmaps and the
error-over-time trend chart (the "Tier 2" enhancement set).
"""

from pathlib import Path

import pytest

from core.persistence import ProgressStore


@pytest.fixture
def store(tmp_path: Path) -> ProgressStore:
    s = ProgressStore(tmp_path / "progress.json")
    try:
        yield s
    finally:
        s.close()


def test_add_session_key_stats_aggregates_by_lesson(store: ProgressStore) -> None:
    store.add_session_key_stats(
        "2026-06-11T10:00:00", 0, "Home Row",
        key_errors={"a": 3, "s": 1},
        key_attempts={"a": 10, "s": 8},
    )
    store.add_session_key_stats(
        "2026-06-11T10:05:00", 0, "Home Row",
        key_errors={"a": 2},
        key_attempts={"a": 9},
    )
    store.add_session_key_stats(
        "2026-06-11T10:10:00", 1, "Top Row",
        key_errors={"q": 4},
        key_attempts={"q": 7},
    )

    assert store.get_lesson_key_errors(0) == {"a": 5, "s": 1}
    assert store.get_lesson_key_errors(1) == {"q": 4}
    assert store.get_lesson_key_errors(2) == {}


def test_add_session_key_stats_ignores_empty_and_zero(store: ProgressStore) -> None:
    store.add_session_key_stats("2026-06-11T10:00:00", 0, "Home Row", {}, {})
    store.add_session_key_stats(
        "2026-06-11T10:01:00", 0, "Home Row",
        key_errors={"a": 0},
        key_attempts={"a": 5},
    )
    assert store.get_lesson_key_errors(0) == {}
    assert store.get_lessons_with_error_data() == []


def test_lessons_with_error_data_ordered_newest_first(store: ProgressStore) -> None:
    store.add_session_key_stats("2026-06-11T09:00:00", 0, "Home Row", {"a": 1}, {"a": 4})
    store.add_session_key_stats("2026-06-11T11:00:00", 1, "Top Row", {"q": 1}, {"q": 4})

    lessons = store.get_lessons_with_error_data()
    assert [entry["lesson_name"] for entry in lessons] == ["Top Row", "Home Row"]
    assert [entry["lesson_index"] for entry in lessons] == [1, 0]


def test_error_timeseries_groups_per_session_in_order(store: ProgressStore) -> None:
    store.add_session_key_stats("2026-06-11T10:00:00", 0, "Home Row", {"a": 3, "s": 1}, {})
    store.add_session_key_stats("2026-06-11T10:05:00", 0, "Home Row", {"a": 2}, {})

    series = store.get_error_timeseries()
    assert series == [
        {"timestamp": "2026-06-11T10:00:00", "errors": 4},
        {"timestamp": "2026-06-11T10:05:00", "errors": 2},
    ]


def test_session_key_errors_trimmed_to_history_window(store: ProgressStore) -> None:
    total = ProgressStore.MAX_HISTORY_SIZE + 5
    for i in range(total):
        store.add_session_key_stats(
            f"2026-06-11T{i:04d}", 0, "Home Row", {"a": 1}, {"a": 2}
        )

    series = store.get_error_timeseries()
    assert len(series) == ProgressStore.MAX_HISTORY_SIZE
    # Oldest sessions are dropped; the most recent timestamp is retained.
    assert series[-1]["timestamp"] == f"2026-06-11T{total - 1:04d}"


def test_persists_across_reconnect(store: ProgressStore, tmp_path: Path) -> None:
    store.add_session_key_stats("2026-06-11T10:00:00", 2, "Numbers", {"7": 3}, {"7": 9})

    reopened = ProgressStore(tmp_path / "progress.json")
    try:
        assert reopened.get_lesson_key_errors(2) == {"7": 3}
    finally:
        reopened.close()
