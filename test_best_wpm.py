"""Tests for core/best_wpm.py."""

from core.best_wpm import BestWpmTracker


class TestBestWpmTracker:
    def test_from_raw_empty(self):
        tracker = BestWpmTracker.from_raw(None)
        assert tracker.get("0") == 0

    def test_from_raw_ignores_malformed(self):
        tracker = BestWpmTracker.from_raw({"0": "bad", "1": 42, 2: 10})
        assert tracker.get("1") == 42
        assert tracker.get("2") == 10
        assert tracker.get("0") == 0

    def test_update_only_if_higher(self):
        tracker = BestWpmTracker({"0": 50})
        assert tracker.update("0", 45) is False
        assert tracker.get("0") == 50
        assert tracker.update("0", 55) is True
        assert tracker.get("0") == 55

    def test_update_new_lesson(self):
        tracker = BestWpmTracker({})
        assert tracker.update("3", 30) is True
        assert tracker.get("3") == 30

    def test_to_dict_returns_copy(self):
        tracker = BestWpmTracker({"0": 40})
        exported = tracker.to_dict()
        exported["0"] = 99
        assert tracker.get("0") == 40

    def test_equal_wpm_does_not_update(self):
        tracker = BestWpmTracker({"0": 50})
        assert tracker.update("0", 50) is False
