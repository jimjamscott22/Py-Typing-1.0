# Review & Suggestions

A high-level review of the Py-Typing-1.0 codebase with feature and optimization ideas.

## Feature ideas

- **Adaptive drills** — use the existing `key_errors` heatmap to auto-generate drills weighted toward the user's worst keys. The `wordgen.py` module and per-key error tracking already exist; this is mostly wiring.
- **Bigram/trigram analysis** — track slow *transitions* (e.g. `th`, `ion`) rather than just per-key errors. Often the real bottleneck for intermediate typists.
- **Goal/streak tracking** — daily WPM target, current streak, calendar heatmap of practice days. Cheap motivational win given `SessionRecord` history is already persisted.
- **Lesson progression gating** — unlock the next lesson when the user hits e.g. 40 WPM + 95% accuracy, instead of allowing free navigation.
- **Import from file/URL** — book-style typing (Project Gutenberg paragraphs, code samples for a "programmer mode").
- **Per-finger WPM breakdown** in stats — the finger map is already defined in `core/constants.py`.

## Code-level optimizations

### Completed

- ✅ **Extracted scoring formula** into `core/scoring.py` (`calculate_wpm`, `calculate_accuracy`). `main_window.py` now delegates. Covered by 14 tests in `test_scoring.py`.
- ✅ **Conservative split of `main_window.py`** (1082 → 1014 lines):
  - `ui/styles.py` — `build_main_stylesheet`, `build_target_text_style`, `build_description_styles` (pure functions of `Theme`).
  - `ui/formats.py` — `make_input_formats()` returns the four `QTextCharFormat` presets.
  - `core/best_wpm.py` — `BestWpmTracker` encapsulates the per-lesson best-WPM dict (load/get/update/serialize). Covered by 10 tests in `test_best_wpm.py`.
  - `main_window.py` no longer imports `QColor` or `QTextCharFormat` directly.

### Still to do

- **Aggressive split of `main_window.py`** — extract a `SessionController` owning session lifecycle (reset, completion, `on_text_changed` logic) so the `QMainWindow` becomes thin Qt glue. Risky: `on_text_changed` reads widgets directly, so the controller will need callbacks/signals.
- **`on_text_changed`** recalculates on every keystroke. Fine today, but if live charts are added, throttle with a `QTimer.singleShot(0, ...)` debounce.
- **`ProgressStore`** does a full JSON read/write on every `save()`. Fine at current scale; if history grows large, consider SQLite (stdlib, no extra dep).
- **`TypingSession.record_key_error`** could also track `key_attempts`, enabling **per-key accuracy %** instead of raw error counts (more meaningful for rare keys).

## Quality / polish

- Only one test file for ~3400 LoC. Pure modules (`wordgen`, `lessons`, the WPM/accuracy formula) are easy unit-test wins.
- Add type checking via `mypy` to the dev workflow.
- Consider a pre-commit hook for `black` + `isort`.
