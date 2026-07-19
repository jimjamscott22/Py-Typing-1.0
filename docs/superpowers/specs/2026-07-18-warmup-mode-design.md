# Warmup Mode — Design Spec

Date: 2026-07-18

## Purpose

Add a "warmup" typing mode that lets the user warm up their fingers before a
real practice session, without any of that typing being recorded into their
progress history, key-error stats, or best-WPM tracking. Today every
completed round unconditionally writes a `SessionRecord` and key stats via
`ProgressStore`; warmup mode needs an escape hatch from that so early,
not-yet-warmed-up mistakes don't pollute the user's real analytics.

## Current architecture (relevant facts)

- `core/models.py`: `Lesson`, `TypingSession`, `SessionRecord` have no notion
  of "mode" today. `self.mode` on `TypingPracticeApp` (`ui/main_window.py:68`)
  is a plain string, currently `"lesson"` or `"free"`, used only for minor
  branching (e.g. `lesson_index=-1` for free-practice records, showing/hiding
  the regenerate button).
- Every completed round — natural completion or timed-mode expiry — funnels
  through a single method, `_finalize_session(*, timed_out: bool)`
  (`ui/main_window.py:1186-1268`). This is the one chokepoint where
  `SessionRecord` is built and `ProgressStore.add_session_record`,
  `update_key_error_stats`/`update_key_attempt_stats`,
  `add_session_key_stats`, `_record_best_wpm`, and `progress_store.save()`
  are all invoked.
- Timed mode is implemented purely as a cached runtime flag
  (`self._timed_mode_seconds`, sourced from a Settings-dialog combo box) — it
  is not persisted as part of a session/record, which is the same pattern
  warmup mode will follow.
- `reset_exercise()` (`main_window.py:806-832`) is the shared "start a fresh
  round" path used by both lesson-loading and free-practice entry; it resets
  `TypingSession` and stops any active timed-mode timer.

## Design

### New components

- **`core/warmup.py`** — a new, self-contained module holding a fixed pool of
  short warmup phrases (finger-stretch/pangram-style drills) and a function
  `get_warmup_text(exclude: str | None = None) -> str` that picks one at
  random, avoiding an immediate repeat of `exclude` when the pool size allows
  it. No settings, no persistence, no dependency on `ProgressStore`.
- **`TypingPracticeApp.warmup_mode: bool`** — new instance attribute
  (default `False`), the flag that gates persistence in `_finalize_session`.
- **`self.mode` gains a third value: `"warmup"`**, alongside the existing
  `"lesson"` / `"free"`.

No changes are made to `core/models.py` or `core/persistence.py` — warmup
rounds simply never reach `ProgressStore`'s write paths.

### Lifecycle / data flow

**Entering warmup** (toggle button pressed on):
1. Snapshot current state for restoration on exit:
   `self._pre_warmup_state = {"mode": self.mode, "lesson_index":
   self.current_lesson_index, "text_index": self.current_text_index}`.
2. Set `self.warmup_mode = True`, `self.mode = "warmup"`.
3. Disable the lesson list, free-practice custom-text box, and the
   regenerate button (mirrors how free-practice entry already toggles
   related controls).
4. `self.current_target_text = get_warmup_text()`, then call the existing
   `reset_exercise()`.

**Typing a warmup round** reuses `on_text_changed` unchanged, with one added
guard: `_start_timed_mode_if_enabled()` is skipped when
`self.mode == "warmup"` — warmup is manual/untimed and orthogonal to the
Settings-dialog timed-mode feature.

**Completing a warmup phrase**: the existing completion check in
`on_text_changed` (`main_window.py:853-861`) calls `_finalize_session` as
normal (so WPM/accuracy still compute and the completion message/celebration
still show), but the persistence block inside `_finalize_session` becomes
conditional:

```python
if not self.warmup_mode:
    self.progress_store.add_session_record(record)
    if session.key_errors:
        self.progress_store.update_key_error_stats(...)
        self.progress_store.update_key_attempt_stats(...)
        self.progress_store.add_session_key_stats(...)
    if self.mode == "lesson":
        self._record_best_wpm(wpm)
    self.progress_store.save()
```

Immediately afterward, instead of waiting for the user to advance manually,
the next warmup phrase is loaded automatically (`get_warmup_text(exclude=...)`
+ `reset_exercise()`) — this produces the "loops until the user exits"
behavior requested.

**Exiting warmup** (toggle button pressed off): restore `self.mode` and
`self.warmup_mode = False` from `self._pre_warmup_state`, re-enable the
lesson/free-practice controls, and reload whichever lesson or free-practice
text was active before entering warmup.

### UI

- A checkable `QPushButton` (e.g. `"🔥 Warmup"`) placed next to the existing
  `"⚙️ Settings"` button (`main_window.py:193-194`), wired to a new
  `_toggle_warmup_mode(checked: bool)` handler implementing the entry/exit
  logic above.
- While active: lesson list, free-practice custom-text box, and the
  regenerate button are disabled, so the user can't drive lesson selection
  and warmup at the same time.
- WPM/accuracy panels and the on-screen keyboard heatmap remain fully live
  and updating during warmup — they already read off `TypingSession` state
  regardless of whether persistence happens, so no changes are needed there.
- No new dialog and no Settings-dialog entry — this is a direct, session-only
  toggle, not a persisted preference.

### Error handling / edge cases

- Toggling warmup **on** mid-round (partial unfinished lesson input): the
  in-progress input is discarded, exactly like switching lessons already
  does today (no autosave of partial rounds exists currently, so this is
  consistent behavior, not a regression).
- Toggling warmup **off** mid-phrase: same — the in-progress warmup phrase is
  discarded and the snapshot state restored; no partial `SessionRecord` is
  ever written for warmup regardless.
- Timed mode is explicitly skipped while `self.mode == "warmup"`, so there is
  no interaction with the Settings-dialog timed-mode feature.
- Strict-mode / adaptive-drills settings are left as global preferences that
  already apply everywhere; they are not special-cased for warmup (adaptive
  drills has no effect on a fixed phrase pool anyway).
- App-quit or crash mid-warmup requires no cleanup — no partial writes ever
  occur in warmup mode.

### Testing

Add to `test_enhancements.py`:
- `core/warmup.get_warmup_text()` returns non-empty text drawn from the
  fixed pool, and avoids an immediate repeat when `exclude` is given and the
  pool has more than one phrase.
- A headless (`QT_QPA_PLATFORM=offscreen`) test that toggles warmup on,
  types a full warmup phrase, and asserts `ProgressStore.add_session_record`
  and `ProgressStore.save` were **not** called (via mock/spy) — the core
  behavioral guarantee of this feature.
- The same style of test confirms a normal (non-warmup) lesson completion
  **does** call `add_session_record`/`save`, to guard against a regression
  that accidentally disables recording globally.
- Toggling warmup on then off restores the prior `self.mode` and lesson/text
  index correctly.

## Out of scope

- No changes to `SessionRecord`/`TypingSession`/`ProgressStore` schemas.
- No Settings-dialog toggle or persisted warmup preference.
- No fixed duration/timer for warmup (manual loop only, per user's choice).
- No hiding of WPM/accuracy/keyboard-heatmap UI during warmup (kept live per
  user's choice).
