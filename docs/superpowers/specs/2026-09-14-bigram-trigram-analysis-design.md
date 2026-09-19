# Bigram and Trigram Analysis Design

**Status:** Approved

**Date:** 2026-09-14

**Source:** `docs/suggestions.md` — “Bigram/trigram analysis”

**Scope:** Python/PyQt application only; no C++ port work

## 1. Summary

Add local analysis that identifies the character transitions a user types most
slowly. The application will measure timing between consecutive, correctly
typed characters during normal manual typing, aggregate those measurements into
bigrams (two-character transitions) and trigrams (three-character sequences),
persist bounded per-session summaries in SQLite, and display the slowest
transitions in a new Statistics tab.

The first version deliberately separates speed from accuracy. Existing per-key
attempt/error tracking remains authoritative for accuracy; transition analysis
answers a different question: “Which correctly typed character combinations
take me longest?”

The design stores only expected two- and three-character sequences plus timing
aggregates. It does not store raw keystroke logs, the user’s full typed text, or
incorrect characters.

## 2. Current State

The application already has most of the surrounding infrastructure:

- `TypingInput` distinguishes actual user edits from programmatic changes and
  emits the inserted positions/text before completion is checked.
- `SessionController.record_edit()` records expected-key attempts and errors.
- `TypingSession` owns round-scoped metrics and is reset between rounds.
- `ProgressStore` creates and evolves its SQLite schema with idempotent
  `CREATE TABLE IF NOT EXISTS` statements.
- Session history and per-session key-error data are retained for the most
  recent 100 completed sessions.
- `StatisticsDialog` builds expensive tabs lazily and already has established
  empty-state and read-only statistics patterns.

What is missing is character-level timing. A completed session’s total duration
cannot be used to reconstruct which individual transition was slow, so this
feature must capture timing while the user types.

## 3. Goals

1. Measure genuine manual typing latency for adjacent correct characters.
2. Identify slow bigrams and trigrams without rare one-off samples dominating
   the ranking.
3. Preserve the app’s current attempt/error accounting semantics.
4. Keep captured data local, compact, bounded, and privacy-conscious.
5. Add useful statistics without changing lesson flow or scoring.
6. Keep the timing logic independent from Qt so it can be tested
   deterministically.

## 4. Non-Goals

The first version will not:

- Change WPM, accuracy, backspace penalties, achievements, goals, or coins.
- Generate drills from slow transitions.
- Treat slow transitions as typing errors.
- Save raw key-down/key-up events or physical scan codes.
- Measure key hold duration.
- Reconstruct or persist complete typed passages.
- Import historical transition data; measurements begin after this feature is
  installed.
- Add cloud sync, export, sharing, or telemetry.
- Add per-lesson filtering in the UI. Lesson metadata will still be stored so a
  later version can add that filter without another schema change.
- Add configurable timing thresholds in Settings.

## 5. Approaches Considered

### A. Infer transition speed from completed-session WPM

This requires no input changes, but one session duration cannot reveal whether
`th`, `ion`, or another sequence caused a slowdown. It does not meet the core
goal and is rejected.

### B. Persist every raw keystroke event

This provides maximum analytical flexibility and could support medians,
percentiles, pauses, and later replay. It also stores far more data than the
feature needs, increases privacy risk, and complicates retention and migration.
It is rejected for the initial version.

### C. Maintain one all-time aggregate per sequence

This is compact, but old behavior can dominate forever and there is no way to
remove data when session history is trimmed. It also makes future per-lesson or
time-window analysis difficult. It is rejected.

### D. Persist per-session sequence aggregates (recommended)

Capture transient samples in memory, aggregate them at successful session
completion, and store one row per sequence per session. This preserves a useful
recent window, supports weighted aggregation, avoids raw keystroke storage, and
matches the existing per-session error-data model.

## 6. User Experience

### 6.1 Statistics tab

Add a lazily built `⌨️ Transitions` tab to `StatisticsDialog`. The tab contains:

- A short explanation: lower times are faster; results include only completed,
  manually typed rounds and sequences with enough observations.
- A **Slowest Bigrams** table.
- A **Slowest Trigrams** table.

Each table has these columns:

| Column | Meaning |
|---|---|
| Sequence | The expected two- or three-character combination. |
| Average time | Weighted mean duration in milliseconds. |
| Samples | Number of valid observations in the retained history window. |
| Versus baseline | Percentage slower or faster than the user’s mean for the same sequence length. |

Rows are ordered slowest first and limited to ten. Bigrams and trigrams use
separate baselines because a trigram duration spans two transitions.

Whitespace is made visible in the table (`␠` for a space). Newlines, carriage
returns, and tabs are not analyzed in the first version.

### 6.2 Empty and collecting states

- With no transition data: “No transition timing data yet. Complete a manually
  typed session to begin collecting it.”
- With some data but no sequence meeting the minimum sample threshold:
  “Collecting transition data — complete more sessions to unlock rankings.”
- The UI must state the minimum threshold so a seemingly empty table is not
  confusing.

### 6.3 No interruption to typing

There is no live transition UI, toast, or warning during a round. Collection is
silent and must not add blocking work to the typing hot path.

## 7. Measurement Semantics

### 7.1 Definitions

- A **bigram sample** is the elapsed time between two adjacent, correctly typed
  target characters.
- A **trigram sample** is the elapsed time from the first to the third character
  in three adjacent, correctly typed target characters. It therefore spans two
  valid bigram intervals.
- The sequence is derived from the expected target text, not from incorrect
  input.
- Case and supported punctuation are preserved. Spaces are included because
  word-boundary transitions are a meaningful part of typing fluency.

Example, with correct consecutive input:

```text
target: i o n
time:   0 90 205 ms

bigram "io"  =  90 ms
bigram "on"  = 115 ms
trigram "ion" = 205 ms
```

### 7.2 Valid samples

A timing chain is valid only when all of the following are true:

1. The edit came through the user-edit path, not a programmatic text change.
2. The event inserted exactly one Unicode character.
3. The inserted character matches the target at that position.
4. Its target position immediately follows the previous valid character.
5. The elapsed time since the previous valid character is greater than zero and
   no more than 2,000 ms.
6. The sequence contains no newline, carriage return, or tab.

The two-second limit excludes pauses, interruptions, and task switching rather
than treating them as finger-transition latency. Values are excluded, not
clamped.

### 7.3 Continuity resets

The timing chain resets when:

- A wrong character is inserted.
- Text is deleted, including Backspace/Delete.
- An insertion replaces selected text.
- The cursor jumps and the next insertion is not adjacent to the last valid
  target position.
- A single input event inserts multiple characters.
- More than two seconds elapse between adjacent characters.
- The exercise is reset, regenerated, changed, completed, or abandoned.

After a reset, the next correct single-character insertion becomes a new anchor
but does not create an incoming transition sample. This prevents correction
time, cursor editing, IME batch commits, and pasted content from being
misrepresented as ordinary key-to-key latency.

Modifier-only key events make no document change and therefore neither create a
sample nor reset continuity.

### 7.4 Corrections and strict mode

Existing attempt/error tracking remains unchanged. An incorrect attempt is
still counted against the expected key. It simply breaks the timing chain.

After the user corrects the text, timing can resume from the corrected character
as a fresh anchor. The correction delay is intentionally not attributed to a
transition because it mixes accuracy recovery with motor latency.

### 7.5 Modes and persistence eligibility

Transition samples may be collected in memory wherever normal user typing is
accepted, but they are persisted only when the existing session-completion path
records the round.

- Normal lessons: persisted on completion.
- Random, Developer Keys, and Weak Key Practice: persisted on completion.
- Timed mode: persisted when the timed session is finalized.
- Free Practice: persisted when its session is finalized.
- Warmup: never persisted, matching all other progress statistics.
- Any round marked as answer-imported/pasted/dropped: transition data from the
  entire round is discarded conservatively.
- Abandoned or reset rounds: not persisted.

## 8. Architecture

### 8.1 New pure transition module

Add `core/transitions.py` containing Qt-independent types and logic:

```python
@dataclass(frozen=True)
class TextChange:
    position: int
    removed: int
    inserted: str

@dataclass(frozen=True)
class TransitionSample:
    sequence: str
    ngram_size: int
    duration_ms: float

@dataclass(frozen=True)
class TransitionSummary:
    sequence: str
    ngram_size: int
    average_ms: float
    sample_count: int
    baseline_delta_percent: float
```

`TransitionTracker` owns only round-scoped timing continuity. Its public surface
is intentionally small:

```python
class TransitionTracker:
    def reset(self) -> None: ...
    def record_change(
        self,
        change: TextChange,
        target_text: str,
        timestamp: float,
    ) -> list[TransitionSample]: ...
```

The tracker retains at most the two previous valid timed characters. It returns
zero, one, or two new samples for each correct single-character insertion: a
bigram, and—when enough valid history exists—a trigram.

Pure helpers in the same module aggregate samples by `(ngram_size, sequence)`
for persistence and format whitespace for display. SQLite access remains in
`ProgressStore`.

### 8.2 Typing input changes

`TypingInput` currently captures only insertions. Extend its document-change
capture to emit `TextChange(position, removed, inserted)` objects for all actual
user document changes.

The existing guarantees remain:

- Programmatic changes are excluded because `editing` is false.
- Undo/redo are not treated as new typing attempts.
- Paste/drop still mark the round as imported and do not generate ordinary
  user-edit timing samples.
- Qt UTF-16 offsets are converted to Python character indexes before creating a
  `TextChange`.

The `user_edited` signal can continue using an `object` payload, but the object
becomes a list of `TextChange` instances rather than insertion tuples.

### 8.3 Session controller changes

`SessionController` composes a `TransitionTracker` and accepts an injectable
monotonic clock, defaulting to `time.monotonic`. The injectable clock keeps
timing tests deterministic and avoids wall-clock changes.

`record_edit()` will:

1. Preserve the current expected-key attempt/error accounting for inserted
   characters.
2. Send each `TextChange` to the tracker using one monotonic timestamp per
   document-change event.
3. Append returned samples to round-scoped transition samples on
   `TypingSession`.

`reset()` clears both the session samples and tracker continuity.

`finalize()` aggregates and persists transition samples through the existing
completion workflow, subject to the eligibility rules in section 7.5. The
transition rows and their retention cleanup use one transaction; the existing
session-history write remains unchanged.

### 8.4 Typing session changes

Add a round-scoped `transition_samples: list[TransitionSample]` field to
`TypingSession`. `TypingSession.reset()` clears it.

Samples remain in memory only until the round is completed or reset. A long
timed round creates at most approximately two samples per typed character,
which is small enough for the existing lesson sizes. Aggregation happens once at
completion, outside the per-keystroke hot path.

### 8.5 Main window changes

`TypingPracticeApp._on_user_edit()` continues to delegate immediately to
`SessionController.record_edit()` before calling `on_text_changed()`. It does
not calculate timings itself.

No timing state should be added to `QMainWindow`; keeping it in the controller
preserves the recently established separation between Qt glue and session
logic.

## 9. Persistence Design

### 9.1 Schema

Add an idempotently created table:

```sql
CREATE TABLE IF NOT EXISTS session_transition_stats (
    session_timestamp TEXT NOT NULL,
    lesson_index INTEGER NOT NULL,
    lesson_name TEXT NOT NULL,
    ngram_size INTEGER NOT NULL CHECK (ngram_size IN (2, 3)),
    sequence TEXT NOT NULL,
    sample_count INTEGER NOT NULL CHECK (sample_count > 0),
    total_duration_ms REAL NOT NULL CHECK (total_duration_ms > 0),
    min_duration_ms REAL NOT NULL CHECK (min_duration_ms > 0),
    max_duration_ms REAL NOT NULL CHECK (max_duration_ms > 0),
    PRIMARY KEY (session_timestamp, ngram_size, sequence)
);

CREATE INDEX IF NOT EXISTS idx_session_transition_stats_sequence
    ON session_transition_stats (ngram_size, sequence);

CREATE INDEX IF NOT EXISTS idx_session_transition_stats_timestamp
    ON session_transition_stats (session_timestamp);
```

This mirrors the established use of `session_timestamp` in
`session_key_errors`. The table intentionally stores aggregates instead of raw
events.

### 9.2 Write API

Add:

```python
ProgressStore.add_session_transition_stats(
    timestamp: str,
    lesson_index: int,
    lesson_name: str,
    aggregates: list[TransitionAggregate],
) -> None
```

All rows for a completed session are inserted in one SQLite transaction. When
the aggregate list is empty, the method skips inserts but still performs
retention cleanup so sessions without eligible timing samples cannot leave
older transition rows outside the history window.

### 9.3 Read API

Add:

```python
ProgressStore.get_slowest_transitions(
    ngram_size: int,
    *,
    min_samples: int = 5,
    limit: int = 10,
    lesson_index: int | None = None,
) -> list[TransitionSummary]

ProgressStore.has_transition_data() -> bool
```

The query:

1. Groups rows by sequence.
2. Calculates a weighted mean using
   `SUM(total_duration_ms) / SUM(sample_count)`.
3. Excludes sequences with fewer than five retained samples by default.
4. Calculates the same-size global baseline from all valid retained samples.
5. Calculates `baseline_delta_percent` in Python to keep SQL simple.
6. Sorts by average duration descending, then sample count descending, then
   sequence for deterministic results.
7. Returns at most ten rows by default.

The optional `lesson_index` is included in the API and schema for later UI use,
but the first UI calls it with `None` for all recorded lessons.

`has_transition_data()` performs an indexed existence query and lets the UI
distinguish “no data has ever been captured” from “data exists, but no sequence
has reached the five-sample ranking threshold.”

### 9.4 Retention

After inserting a completed session’s aggregates, remove transition rows whose
`session_timestamp` is no longer present in the retained `session_history`
table. This keeps transition data aligned with the existing 100-session history
window, including sessions that contain no eligible transition samples.

`session_transition_stats` does not need to be mirrored in `ProgressStore.data`;
like `session_key_errors`, it is queried directly from SQLite.

### 9.5 Migration and compatibility

- Existing databases gain the new table and indexes automatically at startup.
- Existing rows and settings are untouched.
- There is no historical backfill because the necessary timing data does not
  exist.
- Older application versions ignore the new table.
- No save-version flag or destructive migration is required.

## 10. Analytics and Ranking Rules

Constants live in `core/transitions.py`:

```python
MAX_TRANSITION_GAP_SECONDS = 2.0
MIN_TRANSITION_SAMPLES = 5
TRANSITION_RESULT_LIMIT = 10
```

The first version uses weighted arithmetic mean rather than median because only
per-session aggregates are stored. Outlier pauses are controlled at capture
time by the two-second validity ceiling.

The baseline is computed independently for bigrams and trigrams from every
retained valid sample of that size. For a sequence average `S` and baseline
`B`:

```text
baseline delta % = ((S / B) - 1) × 100
```

Positive values are displayed as slower than baseline; negative values as
faster. A zero or absent baseline yields `0.0%` rather than dividing by zero.

The ranking is descriptive, not diagnostic. The UI must show sample counts and
avoid language implying a medical, ergonomic, or keyboard-hardware conclusion.

## 11. Edge Cases

- **First character:** establishes an anchor; creates no sample.
- **Wrong key:** existing attempt/error count is updated; timing continuity
  resets.
- **Correction:** corrected character becomes a new anchor; no transition is
  measured across the correction.
- **Backspace/Delete:** resets timing continuity even if the next text again
  matches the target.
- **Cursor editing:** non-adjacent insertion resets before establishing a new
  anchor.
- **Selection replacement:** resets continuity; inserted replacement text is not
  timed as a batch.
- **Multi-character IME commit:** key attempts remain compatible with current
  behavior, but no transition sample is inferred within or immediately across
  the batch.
- **Paste/drop:** existing answer-imported handling discards the round’s
  transition persistence.
- **Programmatic loading/reset:** emits no user change and creates no sample.
- **Undo/redo:** remains excluded from fresh attempts and timing.
- **Auto-repeat:** each accepted single-character insertion can be sampled; this
  reflects actual repeated-character typing.
- **Timed target extension:** continuity may continue across the generated-text
  boundary when the user types it normally.
- **Overtyping beyond target:** continues existing behavior but creates no
  transition samples beyond the target length.
- **Unicode outside ordinary keyboard lessons:** may be tracked when a valid
  single code point is present in custom text; control whitespace is excluded.
- **Duplicate timestamps:** the existing timestamp convention is retained. A
  single session aggregates each sequence once, and normal ISO timestamps
  include sufficient precision for expected use.
- **Application closes mid-round:** transient samples are lost, matching the
  current loss of unfinished-session statistics.

## 12. File-Level Change Map

| File | Intended change |
|---|---|
| `core/transitions.py` | New pure data types, tracker, aggregation, formatting, and constants. |
| `core/models.py` | Add round-scoped transition sample storage to `TypingSession`. |
| `ui/typing_input.py` | Capture removals and insertions as structured `TextChange` values. |
| `core/session_controller.py` | Compose tracker, preserve attempt/error behavior, reset and persist transition samples. |
| `core/persistence.py` | Add table/index creation, batched write, ranking query, and retention cleanup. |
| `ui/main_window.py` | Pass structured user changes to the controller; no timing state. |
| `ui/dialogs.py` | Add lazy `⌨️ Transitions` statistics tab and two ranked tables. |
| `test_session_controller.py` | Controller integration, reset, correction, and persistence-gating coverage. |
| `test_enhancements.py` | SQLite aggregation/retention and offscreen Statistics UI coverage. |
| `test_transitions.py` | New focused pure tests for timing semantics and aggregation. |
| `docs/suggestions.md` | Mark the suggestion complete only after implementation and verification. |
| `docs/MASTER.md` / `docs/CHANGELOG.md` | Record the shipped feature only after implementation and verification. |

No unrelated `main_window.py` refactor belongs in this feature.

## 13. Validation Strategy

Tests are added after implementation, consistent with this repository’s
workflow.

### 13.1 Pure transition tests

- Sequential `i`, `o`, `n` produces `io`, `on`, and `ion` with exact durations
  under a fake clock.
- First character creates no sample.
- Wrong input resets continuity.
- Correction does not bridge across the error.
- Deletion, replacement, non-adjacent insertion, and multi-character insertion
  reset continuity.
- A gap over two seconds is excluded and starts a new chain.
- Modifier/no-change events neither sample nor reset.
- Spaces and case are preserved; control whitespace is excluded.
- Aggregation produces correct count, total, minimum, and maximum.

### 13.2 Controller regression tests

- Current key-attempt and key-error totals remain unchanged for the same edits.
- Reset clears samples and timing continuity.
- Finalization persists eligible normal/timed session aggregates.
- Warmup, answer-imported, abandoned, and reset rounds do not persist them.

### 13.3 Persistence tests

- A pre-feature SQLite database opens and receives the new table without data
  loss.
- Per-session aggregates round-trip correctly.
- Multi-session results use weighted—not average-of-averages—means.
- Minimum sample threshold and deterministic ordering are enforced.
- Bigram and trigram baselines are calculated independently.
- Transition rows are removed when their session falls outside the retained
  100-session history.
- Lesson metadata and optional lesson filtering remain correct.

### 13.4 UI tests

- The Transitions tab remains lazy until selected.
- No-data and collecting states are distinct.
- Qualified rows show visible whitespace, milliseconds, sample counts, and
  baseline comparison.
- The dialog remains usable in the existing offscreen 700×550 minimum size.

### 13.5 Regression verification

Run the focused transition/controller tests, then the full test suite with a
workspace-local pytest base directory, followed by:

```powershell
git diff --check
```

Perform one offscreen Statistics dialog render check and, when a desktop session
is available, a manual typing check covering normal input, an error/correction,
Backspace, a pause over two seconds, and the resulting ranking display.

## 14. Acceptance Criteria

The feature is complete when:

1. Correct adjacent manual input records deterministic bigram and trigram
   timings under the defined rules.
2. Errors, deletion, cursor edits, batches, imported answers, and long pauses do
   not create misleading transition samples.
3. Existing per-key attempt/error behavior and scoring remain unchanged.
4. Only eligible completed sessions persist aggregate transition data.
5. SQLite stores per-session aggregates and retains only data associated with
   the current 100-session history window.
6. Statistics shows the ten slowest qualified bigrams and trigrams, including
   average duration, sample count, and same-size baseline comparison.
7. Empty/collecting states explain why rankings are unavailable.
8. Existing databases open without destructive migration or manual action.
9. Focused tests, the full test suite, offscreen dialog verification, and
   `git diff --check` pass.
10. Planning and changelog documents are updated to reflect the verified state.

## 15. Deferred Follow-Ups

The design leaves room for later additions without including them now:

- Per-lesson and recent-date filters.
- Median/p90 latency using bounded raw samples or histograms.
- Error-prone bigram/trigram analysis alongside speed analysis.
- Slow-transition trend charts.
- Automatically generated drills targeting qualified slow sequences.
- Separate word-boundary versus within-word rankings.
- Export of transition statistics.
- User-configurable pause and sample thresholds.

These should be considered independently after real usage shows which views are
valuable.

## 16. Recommended Delivery Boundary

Deliver this as one focused feature change because capture semantics,
persistence, and the Statistics view are not independently useful to users.
Keep the commit unmerged and unpushed until explicitly requested.

After this design is approved, write a step-by-step implementation plan. Do not
start code changes directly from this draft.
