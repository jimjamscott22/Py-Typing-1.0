from core.best_wpm import BestWpmTracker


class TestFromRaw:
    def test_empty_input(self):
        assert BestWpmTracker.from_raw(None).to_dict() == {}
        assert BestWpmTracker.from_raw({}).to_dict() == {}

    def test_non_dict_input_returns_empty(self):
        assert BestWpmTracker.from_raw("garbage").to_dict() == {}
        assert BestWpmTracker.from_raw([1, 2, 3]).to_dict() == {}

    def test_keys_coerced_to_str(self):
        tracker = BestWpmTracker.from_raw({0: 50, 1: 60})
        assert tracker.to_dict() == {"0": 50, "1": 60}

    def test_floats_coerced_to_int(self):
        tracker = BestWpmTracker.from_raw({"0": 42.7})
        assert tracker.get("0") == 42

    def test_malformed_values_skipped(self):
        tracker = BestWpmTracker.from_raw({"0": 50, "1": "bad", "2": None, "3": 30})
        assert tracker.to_dict() == {"0": 50, "3": 30}


class TestUpdate:
    def test_first_record_always_wins(self):
        tracker = BestWpmTracker({})
        assert tracker.update("0", 30) is True
        assert tracker.get("0") == 30

    def test_higher_wpm_wins(self):
        tracker = BestWpmTracker({"0": 30})
        assert tracker.update("0", 50) is True
        assert tracker.get("0") == 50

    def test_equal_or_lower_does_not_update(self):
        tracker = BestWpmTracker({"0": 50})
        assert tracker.update("0", 50) is False
        assert tracker.update("0", 30) is False
        assert tracker.get("0") == 50

    def test_independent_lessons(self):
        tracker = BestWpmTracker({})
        tracker.update("0", 40)
        tracker.update("1", 60)
        assert tracker.get("0") == 40
        assert tracker.get("1") == 60


class TestGet:
    def test_missing_key_returns_zero(self):
        assert BestWpmTracker({}).get("missing") == 0
