# Changelog

> Canonical shipped-feature record for Py-Typing-1.0.
> Derived from [[ENHANCEMENTS]] (user notes) + [[IMPLEMENTATION_SUMMARY]] (dev notes), merged here into a single timeline.
> Those originals are kept for reference; this file is the authoritative version going forward.

---

## [1.3] — Persistence Refactor & Scoring Extraction

**Status**: ✅ Shipped
**Tests**: 14 in `test_scoring.py`, 10 in `test_best_wpm.py`

### What changed for users
- Faster cold-start load (granular SQLite writes replace full-file JSON rewrite).
- Your previous `typing_progress.json` was automatically migrated and renamed to `.json.migrated` as a backup.

### What changed for developers

| Module | Change |
|--------|--------|
| `core/scoring.py` | **New.** `calculate_wpm`, `calculate_accuracy` extracted from `main_window.py`. Pure, framework-free functions. |
| `core/best_wpm.py` | **New.** `BestWpmTracker` — load/get/update/serialize for the per-lesson best-WPM dict. |
| `core/persistence.py` | **Replaced JSON with SQLite** (`typing_progress.sqlite3`). Granular per-row writes. One-shot JSON migration on first launch. |
| `ui/styles.py` | **New.** `build_main_stylesheet`, `build_target_text_style`, `build_description_styles` (pure `Theme` functions). |
| `ui/formats.py` | **New.** `make_input_formats()` returning four `QTextCharFormat` presets. |
| `ui/main_window.py` | Delegates scoring to `core/scoring.py`. No longer imports `QColor` or `QTextCharFormat` directly. (1082 → 1014 lines) |

---

## [1.2] — Tier 2: Per-Session Key Stats, Error Trends, Per-Lesson Heatmaps

**Status**: ✅ Shipped

### What changed for users
- **Error Trends tab** (`📉`) in the Statistics dialog — see how your per-key error rate evolves over time.
- **Lesson selector on the Heatmap tab** — filter the error heatmap to a single lesson instead of the all-time global view.

### What changed for developers

| Module | Change |
|--------|--------|
| `core/persistence.py` | Added `session_key_errors` table. New methods: `add_session_key_stats`, `get_lesson_key_errors`, `get_lessons_with_error_data`, `get_error_timeseries`. Table auto-trims to same retention window as `session_history`. |
| `core/charts.py` | Added `create_error_timeseries_chart()`. |
| `ui/main_window.py` | `on_completion` now logs per-session key errors to `session_key_errors`. |
| `ui/dialogs.py` | Lesson selector on 🔥 Error Heatmap tab; new 📉 Error Trends tab. |
| `test_enhancements.py` | Persistence round-trip + retention tests. |

> **Data note**: Per-session breakdown starts empty and accumulates going forward. Sessions completed before this version only appear in the global cumulative stats.

---

## [1.1] — Theme System, Matplotlib Charts, Keyboard Error Heatmap

**Status**: ✅ Shipped
**Dependency added**: `matplotlib`

### What changed for users

#### Themes
- 5 built-in themes: **Light**, **Dark**, **Solarized Dark**, **Nord**, **Dracula**.
- All UI elements (keyboard widget, charts, dialogs) adapt to the selected theme.
- Set in: Settings → Display Settings → Theme → Save Settings.

#### Visual Charts
- Statistics dialog now shows **professional matplotlib charts** instead of plain text.
- **Combined Progress Chart** (dual-axis): WPM + accuracy over the last 20 sessions.
- **Lesson Performance Chart**: horizontal bar chart of average WPM by lesson (top 10).
- Charts automatically match the active theme's color palette.
- Access: Statistics (📊) → Progress tab.

#### Keyboard Error Heatmap
- **Per-key error tracking** accumulated across all sessions.
- Visual keyboard overlay: red-gradient intensity shows which keys you miss most.
- **Finger analysis chart**: errors grouped by finger (left/right pinky, ring, middle, index, thumb).
- **Top-10 problem keys** quick reference list.
- Access: Statistics (📊) → Error Heatmap tab.

### What changed for developers

| Module | Change |
|--------|--------|
| `core/themes.py` | **New.** 5 theme definitions, each with 30+ color properties. |
| `core/constants.py` | Added `DEFAULT_THEME = "Light"`. |
| `core/charts.py` | **New.** Chart generation utilities using matplotlib Agg backend → `QPixmap`. |
| `core/heatmap.py` | **New.** Keyboard heatmap renderer. |
| `core/models.py` | Added `key_errors: dict` to `TypingSession` (line 21, 41–44). |
| `core/persistence.py` | Added `key_error_stats` and (later) `key_attempt_stats` storage. |
| `ui/main_window.py` | Theme application logic; tracks and saves key errors on each keystroke. |
| `ui/widgets.py` | `KeyboardWidget`, `FingerLegendWidget` now theme-aware. |
| `ui/dialogs.py` | Theme selector in Settings; visual charts and Error Heatmap tab in Statistics. |
| `requirements.txt` | Added `matplotlib`. |

---

## Upcoming

See [[ENHANCEMENTS_ROADMAP]] for the full pipeline. Next up (Tier 1 — no schema change):

- [ ] Export charts as PNG images
- [ ] Additional chart types (pie: time-per-lesson; scatter: WPM vs. accuracy)
- [ ] Practice recommendations panel (error-rate per key is already stored)
