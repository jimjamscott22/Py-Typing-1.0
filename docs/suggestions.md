# Review & Suggestions

A high-level review of the Py-Typing-1.0 codebase with feature and optimization ideas.

## Feature ideas

- ✅ **Adaptive drills** — `core/wordgen.py:generate_adaptive_text()` weights word selection toward the user's worst keys, wired through the `adaptive_drills` setting.
- ✅ **Bigram/trigram analysis** — `core/transitions.py` measures slow *transitions* (e.g. `th`, `ion`) between adjacent, correctly typed characters, aggregates them per session in `session_transition_stats`, and ranks the slowest in Statistics → ⌨️ Transitions.
- ✅ **Goal/streak tracking** — `core/goals.py` (daily/weekly goal evaluation) and `core/analytics.py:compute_streaks()`, surfaced in the Overview tab.
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

- ✅ **Aggressive split of `main_window.py`** — `core/session_controller.py:SessionController` now owns session lifecycle (reset, completion, `record_edit`, `finalize`); `TypingPracticeApp` hands it plain values and reacts to plain results (`EditOutcome`, `FinalizeResult`), with no widget references crossing into the controller.
- ✅ **Surface per-key accuracy %** — the Error Heatmap tab's "Show error rate (%) instead of raw counts" toggle derives per-key accuracy from `key_attempts`/`key_errors`.

> See [[ENHANCEMENTS_ROADMAP]] for the full feature pipeline (Tier 1–3), including items that have already shipped on top of the completed items above.

## Quality / polish

- Six test files for ~4800 LoC (`test_scoring.py`, `test_best_wpm.py`, `test_enhancements.py`, `test_weak_keys.py`, `test_session_controller.py`, `test_transitions.py`). Pure modules (`wordgen`, `lessons`, the WPM/accuracy formula, `transitions`) are easy unit-test wins.
- Add type checking via `mypy` to the dev workflow.
- Consider a pre-commit hook for `black` + `isort`.
