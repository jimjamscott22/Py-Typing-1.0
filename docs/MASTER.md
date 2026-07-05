# Py-Typing — Master Reference

> **Single source of truth** for the Py-Typing-1.0 project.
> All other docs in this folder derive from or point back here.
> When in doubt about project status, open this file first.

---

## Document Map

| File | Purpose | Audience | Status |
|------|---------|---------|--------|
| **MASTER.md** | This file — index, status tracker, key invariants | Everyone | Always current |
| [[CHANGELOG]] | Shipped features: user notes + dev notes, versioned timeline | Users & contributors | Updated on each ship |
| [[ENHANCEMENTS_ROADMAP]] | Upcoming feature planning, tier prioritization | Contributors | Updated as tiers complete |
| [[SPEC_C++_Port]] | Full C++ port specification (data types, SQL schema, CMake, acceptance checklist) | Port developers | Stable |
| [[BUILD_GUIDE]] | PyInstaller packaging for Windows distribution | End users, distributors | Stable |
| [[suggestions]] | High-level review: code-level optimizations, feature ideas | Maintainers | Semi-living |
| [[VISUAL_OVERVIEW]] | Architecture diagrams, typing loop flowchart, data-flow map | Everyone | Mirrors SPEC + CHANGELOG |
| [[ENHANCEMENTS]] | Original user-facing feature announcement (v1.1) | Reference only | Superseded by CHANGELOG |
| [[IMPLEMENTATION_SUMMARY]] | Original dev-facing implementation notes (v1.1) | Reference only | Superseded by CHANGELOG |

---

## Authoritative Feature Tracker

### ✅ Shipped

| Feature | Version | Key files |
|---------|---------|-----------|
| Scoring formula extracted | 1.3 | `core/scoring.py`, `test_scoring.py` (14 tests) |
| `BestWpmTracker` extracted | 1.3 | `core/best_wpm.py`, `test_best_wpm.py` (10 tests) |
| `main_window.py` conservative split | 1.3 | `ui/styles.py`, `ui/formats.py` |
| `ProgressStore` → SQLite (JSON migrated) | 1.3 | `core/persistence.py` |
| `on_text_changed` debounce | 1.3 | `ui/main_window.py:723-725` |
| `key_attempts` tracking + persistence | 1.3 | `core/models.py:21,41-44` |
| Theme system (5 themes) | 1.1 | `core/themes.py` |
| Matplotlib charts (WPM + accuracy) | 1.1 | `core/charts.py` |
| Keyboard error heatmap (global) | 1.1 | `core/heatmap.py` |
| Per-session key error log | 1.2 | `session_key_errors` table |
| Per-lesson heatmap filter | 1.2 | `ui/dialogs.py` |
| Error Trends tab (time-series) | 1.2 | `core/charts.py`, `ui/dialogs.py` |

### 🔜 Tier 1 — Next (no schema change required)

| Feature | Effort | Notes |
|---------|--------|-------|
| Export charts as PNG | Trivial | Charts already render to `QPixmap`; add a "Save" button |
| Pie chart (time per lesson) + scatter (WPM vs. accuracy) | Low | Additive functions in `core/charts.py` |
| Practice recommendations panel | Low–Med | `key_error_stats ÷ key_attempt_stats` is already stored |

### 📋 Tier 3 — Planned (large standalone build)

| Feature | Effort | Notes |
|---------|--------|-------|
| Custom theme creator | Med–High | 30+ color tokens; need new persistence for user-defined themes |

### 💡 Feature Ideas (not yet scoped)

From [[suggestions]]:
- **Adaptive drills** — auto-generate drills weighted toward worst keys (`wordgen.py` + `key_errors` heatmap already exist, needs wiring)
- **Bigram/trigram analysis** — track slow transitions (`th`, `ion`) not just per-key errors
- **Goal/streak tracking** — daily WPM target, streak counter, calendar heatmap
- **Lesson progression gating** — unlock next lesson at e.g. 40 WPM + 95% accuracy
- **Import from file/URL** — book-style typing (Project Gutenberg, code samples)
- **Per-finger WPM breakdown** — finger map already defined in `core/constants.py`

---

## Architecture at a Glance

```
core/                         ui/
  scoring.py   ←── pure         main_window.py   (thin Qt glue; ~1014 lines)
  best_wpm.py  ←── pure         widgets.py       (KeyboardWidget, overlays)
  models.py    ←── data types   dialogs.py       (Statistics, Settings)
  lessons.py                    styles.py        (QSS builders)
  wordgen.py                    formats.py       (QTextCharFormat presets)
  themes.py
  charts.py    (matplotlib → QPixmap)
  heatmap.py   (keyboard overlay renderer)
  persistence.py  (SQLite: 9 tables, WAL mode)
  constants.py    (KEY_FINGER_MAP, defaults)
  audio.py        (CelebrationSoundManager)
```

See [[VISUAL_OVERVIEW]] for diagrams, or [[SPEC_C++_Port]] for the authoritative C++ port reference.

---

## Key Invariants — Things Not to Break

1. **Scoring formulas are byte-for-byte portable to C++.** `calculateWpm` does `int(words/minutes)` then `int(rawWpm - penalty)` — integer truncation at both steps is intentional. Do not round.
2. **`ProgressStore` writes are granular.** Each setter runs its own `INSERT OR REPLACE`. No full-file rewrites.
3. **Session history is capped at 100 rows.** Trim on insert, not on read.
4. **`key_errors` keys are single-character strings**, including `" "` for space. Mirrors Python dict behavior exactly.
5. **Theme is stored by name** (string), not by value. Deserialize from the `THEMES` registry at load time.
6. **`__RANDOM__` / `__DEVELOPER__` sentinel texts** must be replaced at runtime before display and persisted via `setRandomText` / `setDeveloperText` per lesson+index.
7. **Backspace detection is length-delta based.** `new_length < old_length` → backspace. This is fragile under paste/select-replace — known limitation, do not "fix" without testing all edge cases.

---

## Quality Gaps (open items)

- Only one test file for ~3 400 LoC of Python. Pure modules (`wordgen`, `lessons`) are easy unit-test wins.
- `mypy` not yet in the dev workflow — add to CI.
- No `black` / `isort` pre-commit hook.
- **`main_window.py` aggressive split** still pending: extract `SessionController` (session lifecycle, `on_text_changed`) so `QMainWindow` becomes thin Qt glue. Risky — `on_text_changed` reads widgets directly; controller will need callbacks/signals.
