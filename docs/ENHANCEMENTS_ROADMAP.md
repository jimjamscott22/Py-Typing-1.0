# Enhancements Roadmap

Planning doc for the "Future Enhancement Ideas" listed at the end of
[`ENHANCEMENTS.md`](ENHANCEMENTS.md). Where `ENHANCEMENTS.md` records features
that already shipped, this file assesses what's next, ordered by effort and
dependency.

## The driving constraint

Key-error data has two layers:

- **Global, cumulative** — `key_error_stats` / `key_attempt_stats` aggregate
  across *all* sessions and lessons. Never trimmed. Powers the existing global
  Error Heatmap.
- **Per-session** — each `TypingSession` collects `key_errors` for the current
  run, and (since Tier 2) these are persisted per session/lesson in the
  `session_key_errors` table.

Two of the proposed features need the per-session breakdown; the rest only need
data that already exists.

## Assessment

| Idea | Effort | Schema change? | Notes |
|---|---|---|---|
| Export charts as images | Trivial | No | Charts already render to `QPixmap`; add a "Save PNG" button. |
| More chart types (pie/scatter) | Low | No | Additive functions in `core/charts.py`, `(data, theme) → QPixmap` pattern. e.g. pie = time-per-lesson; scatter = WPM vs accuracy. |
| Practice recommendations | Low–Med | No | `key_error_stats ÷ key_attempt_stats` = error-rate per key. Pure analysis + a panel. Performance tab already has a primitive "Needs Practice" hint. |
| Time-series error tracking | Med | **Yes** ✅ done | Per-session key-error log. |
| Per-lesson heatmaps | Med | **Yes** ✅ done | Per-lesson key errors; reuses existing heatmap renderer with a filtered dict. |
| Custom theme creator | Med–High | Yes (new) | `Theme` has 30+ color tokens; full color-picker UI is the biggest lift. Themes aren't persisted today — only the selected *name* is. |

## Recommended order

### Tier 1 — quick wins, no schema change (do first)

1. **Export charts as images** — fastest, immediate utility, touches nothing fragile.
2. **More chart types (pie + scatter)** — additive, low risk.
3. **Practice recommendations** — high value, data already present.

Best shipped together as one small PR in the Statistics dialog.

### Tier 2 — one shared schema addition ✅ SHIPPED

**Time-series error tracking + per-lesson heatmaps.** Both unlocked by a single
new table, `session_key_errors`, populated from `on_completion` instead of
discarding `session.key_errors`. Raw error counts (attempt counts also stored,
so an error-rate toggle is a later add-on with no schema change).

Delivered:

- `core/persistence.py` — `session_key_errors` table + `add_session_key_stats`,
  `get_lesson_key_errors`, `get_lessons_with_error_data`, `get_error_timeseries`.
  Auto-trims to the same retention window as `session_history`.
- `ui/main_window.py` — `on_completion` logs per-session key errors.
- `core/charts.py` — `create_error_timeseries_chart()`.
- `ui/dialogs.py` — lesson selector on the 🔥 Error Heatmap tab; new
  📉 Error Trends tab.
- `test_enhancements.py` — persistence round-trip + retention tests.

Per-lesson/trend data starts empty and accumulates going forward (old data has
no per-session breakdown); global stats remain the all-time view.

### Tier 3 — biggest standalone build

6. **Custom theme creator** — most UI work, separate persistence concern
   (user-defined themes must be stored and merged into the registry at load),
   no dependency on the rest. Best done last.

## Cheap follow-ups now possible on the Tier 2 foundation

- **Error-rate toggle** (errors ÷ attempts) on the heatmap and trends — attempt
  counts are already stored.
- **Per-key error trend line** in the Error Trends tab (filter `session_key_errors`
  by key over time).
