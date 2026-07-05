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

### Completed (cont.)

- ✅ **`on_text_changed` debounce** — already throttled via `QTimer.singleShot(0, self._flush_display)` with a `_pending_display_update` guard (`ui/main_window.py:723-725`), so multi-keystroke bursts only repaint once per event-loop cycle.
- ✅ **`TypingSession.key_attempts`** — now tracked alongside `key_errors` (`core/models.py:21,41-44`) and persisted as `key_attempt_stats` in the store; per-key accuracy % can be derived as `1 - errors[k] / attempts[k]`.
- ✅ **`ProgressStore` → SQLite** — replaced the single JSON read/write with a SQLite database (`typing_progress.sqlite3`, stdlib-only). Granular writes (one row per setting / session / key) replace the previous full-file rewrite on every `save()`. Legacy `typing_progress.json` is migrated once on first launch and renamed to `.json.migrated` as a backup. Public API is preserved — `.data` mirror still works for read paths in `dialogs.py`.

### Still to do

- **Aggressive split of `main_window.py`** — extract a `SessionController` owning session lifecycle (reset, completion, `on_text_changed` logic) so the `QMainWindow` becomes thin Qt glue. Risky: `on_text_changed` reads widgets directly, so the controller will need callbacks/signals.
- **Surface per-key accuracy %** — the underlying `key_attempts` data is now persisted; the statistics dialog still shows raw error counts via the heatmap. Add a per-key accuracy view (more meaningful for rare keys).

> See [[ENHANCEMENTS_ROADMAP]] for the full feature pipeline (Tier 1–3), including items that have already shipped on top of the completed items above.

## Quality / polish

- Only one test file for ~3400 LoC. Pure modules (`wordgen`, `lessons`, the WPM/accuracy formula) are easy unit-test wins.
- Add type checking via `mypy` to the dev workflow.
- Consider a pre-commit hook for `black` + `isort`.
