# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A desktop touch-typing practice application built with PyQt6. It runs entirely locally — no server, no cloud. Progress is persisted to `typing_progress.sqlite3` (WAL mode) in the working directory. A legacy `typing_progress.json`, if present, is migrated once on startup then renamed aside.

## Running the app

```bash
uv sync          # install dependencies
uv run main.py   # launch the GUI
```

Build a Windows executable (from Windows):
```bash
uv add --dev pyinstaller
build_exe.bat    # output: dist/Typing Practice.exe
```

## Running tests

```bash
uv run pytest test_enhancements.py test_session_controller.py -v
```

Two flat top-level test files: `test_enhancements.py` (persistence, analytics, Qt-integration behavior via a headless `window` fixture) and `test_session_controller.py` (pure `SessionController` logic, no Qt required). No coverage tooling is configured.

Smoke-test Qt UI headlessly without launching the GUI:

```bash
QT_QPA_PLATFORM=offscreen uv run python -c "..."
```

## Architecture

```
main.py              # QApplication entry point; creates TypingPracticeApp
ui/
  main_window.py     # TypingPracticeApp (QMainWindow) — all session logic lives here
  widgets.py         # KeyboardWidget, FingerLegendWidget, CelebrationOverlay
  dialogs.py         # StatisticsDialog, SettingsDialog
core/
  models.py          # Lesson, TypingSession, SessionRecord dataclasses
  session_controller.py  # SessionController — reset/completion/typed-text lifecycle, no Qt
  persistence.py     # ProgressStore — SQLite-backed progress + settings (granular writes)
  lessons.py         # build_lessons() — returns hardcoded Lesson list
  wordgen.py         # generate_text(n) — random word drills
  themes.py          # Theme dataclass + get_theme(name) for 5 built-in themes
  heatmap.py         # Keyboard error heatmap rendering (matplotlib)
  charts.py          # Progress chart rendering (matplotlib)
  audio.py           # CelebrationSoundManager
  constants.py       # Default settings values and KEY_FINGER_MAP
```

**Key data flow:** `TypingPracticeApp` owns every widget and delegates session lifecycle to a `SessionController` (`core/session_controller.py`), which owns the in-progress `TypingSession`, the round-complete flag, and weak-key-round bookkeeping, and talks to `ProgressStore` directly — it takes no widget references, only plain strings/bools handed to it by the window. On every keystroke, `on_text_changed` reads the input box and calls `controller.update_typed_text(...)`, then reacts to the returned `EditOutcome` to trigger timed-mode start / round completion. Completion calls `controller.finalize(...)`, which writes a `SessionRecord` to `ProgressStore`, syncs achievements/daily-challenge/coins, and returns a `FinalizeResult` that the window turns into label/overlay updates. `session` and `_round_complete` on `TypingPracticeApp` are facade properties over the controller, kept for the many existing read sites throughout the file.

**Settings** are stored in the SQLite `settings` table (mirrored in `data["settings"]`) and accessed via `ProgressStore.get_setting` / `set_setting`. Defaults live in `core/constants.py`.

**Persistence model:** Granular setters (`set_setting`, `add_session_record`, `update_key_*`, `add_session_key_stats`) write to SQLite immediately. `ProgressStore.save()` only syncs the two position keys + `best_wpm` map. The in-memory `.data` dict mirrors persisted state for direct read paths.

**Themes** are applied by `_apply_theme()` on `TypingPracticeApp`, which calls `setStyleSheet` with theme color values. The `Theme` dataclass in `core/themes.py` holds all color tokens.

**WPM formula:** `effective_wpm = raw_wpm - (backspace_count × penalty_factor)`. Accuracy also penalises backspaces with a configurable weight. Both defaults are in `constants.py`.

## Python version

Requires Python ≥ 3.14 (set in `pyproject.toml` and `.python-version`). Package management is via `uv`.
