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

- **`ui/main_window.py` is 1034 lines** and handles session logic, UI wiring, theme application, and completion handling. Extract a `SessionController` and a `StatsService` so the `QMainWindow` is just glue.
- **`on_text_changed`** recalculates on every keystroke. Fine today, but if live charts are added, throttle with a `QTimer.singleShot(0, ...)` debounce.
- **`ProgressStore`** does a full JSON read/write on every `save()`. Fine at current scale; if history grows large, consider SQLite (stdlib, no extra dep).
- **`TypingSession.record_key_error`** could also track `key_attempts`, enabling **per-key accuracy %** instead of raw error counts (more meaningful for rare keys).
- **Extract the scoring formula** (`effective_wpm = raw_wpm - backspace_count × penalty`) into `core/scoring.py` so it's testable in isolation.

## Quality / polish

- Only one test file for ~3400 LoC. Pure modules (`wordgen`, `lessons`, the WPM/accuracy formula) are easy unit-test wins.
- Add type checking via `mypy` to the dev workflow.
- Consider a pre-commit hook for `black` + `isort`.
