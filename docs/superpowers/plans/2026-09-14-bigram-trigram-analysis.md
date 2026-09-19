# Bigram and Trigram Analysis Implementation Plan

> **For agentic workers:** REQUIRED WORKFLOW: Execute this plan sequentially in the current workspace after explicit user approval. Project instructions override generic workflow guidance: do not spawn subagents, create a worktree, use tests-first loops, commit, merge, or push unless the user explicitly requests it.

**Goal:** Measure manually typed bigram and trigram latency, retain bounded per-session aggregates, and show the user their slowest qualified transitions in Statistics.

**Architecture:** A new pure `core.transitions` module owns edit descriptors, timing continuity, samples, aggregation, and display formatting. `TypingInput` reports structured document changes; `SessionController` applies an injectable monotonic clock and persists aggregates through `ProgressStore` when an eligible session completes. SQLite retains per-session aggregates alongside the existing 100-session history window, and `StatisticsDialog` reads ranked summaries into a lazy tab.

**Tech Stack:** Python 3.14+, PyQt6, stdlib `sqlite3`, stdlib `time.monotonic`, pytest 9+

**Spec:** `docs/superpowers/specs/2026-09-14-bigram-trigram-analysis-design.md`

## Global Constraints

- Measure only adjacent, correct, single-character manual insertions.
- A valid adjacent gap is greater than zero and no more than `2.0` seconds.
- Preserve sequence case, punctuation, and spaces; exclude `\n`, `\r`, and `\t`.
- Errors, deletions, replacements, non-adjacent edits, multi-character insertions, and long pauses reset timing continuity.
- Store expected sequences and aggregate durations only; never store raw key events, incorrect characters, or complete typed passages.
- Persist through the existing completed-session path; exclude warmup and answer-imported rounds.
- Retain rows only while their timestamp remains in the existing 100-session history.
- Rank at most `10` sequences and require at least `5` retained samples by default.
- Do not alter scoring, key attempt/error accounting, achievements, challenges, goals, coins, or lesson flow.
- Implement first, then add focused tests; do not use a tests-first loop.
- Preserve unrelated work and leave all changes uncommitted until explicitly asked.

## File Structure

| File | Responsibility |
|---|---|
| `core/transitions.py` | Pure types, tracker, aggregation, constants, and display formatting. |
| `core/models.py` | Round-scoped transition sample storage. |
| `ui/typing_input.py` | Structured user document changes. |
| `core/session_controller.py` | Timing lifecycle, existing key accounting, and completion submission. |
| `core/persistence.py` | Schema, aggregate writes, retention, and rankings. |
| `ui/main_window.py` | Thin structured-edit delegation. |
| `ui/dialogs.py` | Lazy Transitions statistics tab. |
| `test_transitions.py` | Pure timing and aggregation tests. |
| `test_session_controller.py` | Controller integration and persistence gates. |
| `test_enhancements.py` | SQLite and offscreen UI tests. |
| `README.md`, `docs/*.md` | Verified feature/status documentation. |

---

### Task 1: Pure Transition Types, Tracker, and Aggregation

**Files:**

- Create: `core/transitions.py`
- Modify: `core/models.py:1-44`
- Create: `test_transitions.py`

**Interfaces:**

- Consumes: monotonic `float` timestamps and target-relative text changes.
- Produces: `TextChange`, `TransitionSample`, `TransitionAggregate`, `TransitionSummary`, `TransitionTracker`, `aggregate_transition_samples()`, and `format_transition_sequence()`.

- [ ] **Step 1: Implement the public types and constants**

Create `core/transitions.py` with these exact public names and fields:

```python
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

MAX_TRANSITION_GAP_SECONDS = 2.0
MIN_TRANSITION_SAMPLES = 5
TRANSITION_RESULT_LIMIT = 10
_EXCLUDED_CHARACTERS = frozenset({"\n", "\r", "\t"})

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
class TransitionAggregate:
    sequence: str
    ngram_size: int
    sample_count: int
    total_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float

@dataclass(frozen=True)
class TransitionSummary:
    sequence: str
    ngram_size: int
    average_ms: float
    sample_count: int
    baseline_delta_percent: float
```

Add a private frozen `_TimedCharacter(position, character, timestamp)` type.

- [ ] **Step 2: Implement `TransitionTracker`**

Expose `TransitionTracker(max_gap_seconds: float =
MAX_TRANSITION_GAP_SECONDS)`, `reset() -> None`, and
`record_change(change: TextChange, target_text: str, timestamp: float) ->
list[TransitionSample]`. Initialize a `deque(maxlen=2)` and have `reset()` clear
it.

Apply the approved rules in this order:

1. Clear history first when `removed > 0`.
2. Return without resetting for an empty/no-change edit.
3. Clear and return for inserted strings whose length is not one.
4. Clear and return when the position is outside the target, the inserted character is incorrect, or the expected character is excluded control whitespace.
5. With prior history, require the next target position, a strictly increasing timestamp, and a gap no greater than two seconds. If any check fails, clear history and use the new correct character only as an anchor.
6. Emit the prior-to-current bigram in milliseconds.
7. When two valid prior characters exist, emit the first-to-current trigram.
8. Append the new timed character after constructing samples.

- [ ] **Step 3: Implement deterministic aggregation and formatting**

Implement `aggregate_transition_samples(samples: Iterable[TransitionSample]) ->
list[TransitionAggregate]` and this formatter:

```python
def format_transition_sequence(sequence: str) -> str:
    return sequence.replace(" ", "␠")
```

Group by `(ngram_size, sequence)`, retain count/total/min/max without rounding,
and sort by `(ngram_size, sequence)`.

- [ ] **Step 4: Add samples to `TypingSession`**

Import `TransitionSample`, add
`transition_samples: List[TransitionSample] = field(default_factory=list)`, and
clear it in `TypingSession.reset()` without changing existing fields.

- [ ] **Step 5: Add tests after implementation**

Create `test_transitions.py`. Include a deterministic `ion` example:

```python
tracker = TransitionTracker()
assert tracker.record_change(TextChange(0, 0, "i"), "ion", 10.000) == []
io = tracker.record_change(TextChange(1, 0, "o"), "ion", 10.090)
assert io[0].sequence == "io"
assert io[0].duration_ms == pytest.approx(90.0)
on_and_ion = tracker.record_change(TextChange(2, 0, "n"), "ion", 10.205)
assert [sample.sequence for sample in on_and_ion] == ["on", "ion"]
assert on_and_ion[0].duration_ms == pytest.approx(115.0)
assert on_and_ion[1].duration_ms == pytest.approx(205.0)
```

Add separate tests for wrong input, deletion/correction, replacement,
non-adjacent insertion, multi-character insertion, long/equal timestamps,
no-change edits, case and punctuation preservation, spaces, control whitespace,
reset, aggregation, ordering, and visible-space formatting.

- [ ] **Step 6: Verify the pure module**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest test_transitions.py -q -p no:cacheprovider --basetemp=.cache/transition-unit --tb=short
```

Expected: every test in `test_transitions.py` passes.

---

### Task 2: Structured Input Capture and Controller Timing

**Files:**

- Modify: `ui/typing_input.py:1-56`
- Modify: `core/session_controller.py:9-116`
- Modify: `ui/main_window.py:991-1002`
- Modify: `test_session_controller.py:1-96`
- Verify: `test_weak_keys.py`

**Interfaces:**

- Consumes: Task 1 transition types and tracker.
- Produces: `TypingInput.user_edited -> list[TextChange]` and `SessionController.record_edit(changes: list[TextChange], target_text: str) -> None`.

- [ ] **Step 1: Emit structured document changes**

In `TypingInput`, rename `_insertions` to `_changes`, connect
`contentsChange` to `_capture_change`, and record deletions as well as additions:

```python
def _capture_change(self, position, removed, added):
    if not self.editing or (not removed and not added):
        return
    raw = self.toPlainText().encode("utf-16-le")
    prefix = raw[: position * 2].decode("utf-16-le")
    inserted = raw[position * 2 : (position + added) * 2].decode("utf-16-le")
    self._changes.append(TextChange(len(prefix), removed, inserted))
```

Reset and emit `_changes` in `_edit()`. Preserve undo/redo exclusion and
paste/drop answer-imported signaling.

- [ ] **Step 2: Inject the clock and own tracker lifecycle**

Extend `SessionController.__init__()` with
`transition_clock: Callable[[], float] = time.monotonic`. Store the clock,
construct a `TransitionTracker`, and reset it from `controller.reset()`.

- [ ] **Step 3: Preserve key accounting while recording timings**

Implement this method shape:

```python
def record_edit(self, changes: list[TextChange], target_text: str) -> None:
    timestamp = self._transition_clock()
    for change in changes:
        for offset, char in enumerate(change.inserted):
            index = change.position + offset
            if index < len(target_text):
                expected = target_text[index]
                self.session.record_key_attempt(expected)
                if char != expected:
                    self.session.record_key_error(expected)
        self.session.transition_samples.extend(
            self.transition_tracker.record_change(change, target_text, timestamp)
        )
```

Call the clock once per emitted edit batch. Do not change attempt/error meaning.

- [ ] **Step 4: Keep `_on_user_edit()` as Qt glue**

Rename its parameter to `changes`, pass it directly to `record_edit()`, and
preserve the repaint-prefix check plus subsequent `on_text_changed()` call.

- [ ] **Step 5: Update controller tests after implementation**

Replace tuple edits with `TextChange`. Add an iterator-backed fake clock and
verify correct adjacent samples, deletion reset, controller reset,
multi-character attempts without timings, and the existing `hello` attempt/error
totals.

- [ ] **Step 6: Verify controller and live input regressions**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest test_session_controller.py test_weak_keys.py -q -p no:cacheprovider --basetemp=.cache/transition-controller --tb=short
```

Expected: all focused tests pass, with user insertions still counted once and
programmatic/reset/deletion paths adding no attempts.

---

### Task 3: SQLite Aggregates, Ranking, and Retention

**Files:**

- Modify: `core/persistence.py:1-172, 439-492, 713-835`
- Modify: `test_enhancements.py`

**Interfaces:**

- Consumes: `TransitionAggregate` and `TransitionSummary`.
- Produces: `add_session_transition_stats()`, `get_slowest_transitions()`, and `has_transition_data()`.

- [ ] **Step 1: Add the approved table and indexes**

Add `session_transition_stats` inside `_create_schema()` with the composite
primary key `(session_timestamp, ngram_size, sequence)`, checks for n-gram size,
positive counts/durations, and indexes on `(ngram_size, sequence)` and
`session_timestamp`. Use only additive `CREATE TABLE IF NOT EXISTS` and `CREATE
INDEX IF NOT EXISTS` statements.

- [ ] **Step 2: Implement batched writes and unconditional pruning**

Add:

```python
def add_session_transition_stats(
    self,
    timestamp: str,
    lesson_index: int,
    lesson_name: str,
    aggregates: List[TransitionAggregate],
) -> None:
```

Insert/replace aggregates with parameterized SQL. In the same transaction, even
for an empty list, run:

```sql
DELETE FROM session_transition_stats
WHERE session_timestamp NOT IN (SELECT timestamp FROM session_history)
```

Do not mirror this table into `ProgressStore.data`.

- [ ] **Step 3: Implement existence and ranked reads**

Implement `has_transition_data()` exactly as an indexed existence read:

```python
def has_transition_data(self) -> bool:
    row = self._conn.execute(
        "SELECT 1 FROM session_transition_stats LIMIT 1"
    ).fetchone()
    return row is not None
```

Implement the exact approved `get_slowest_transitions(ngram_size, *,
min_samples=5, limit=10, lesson_index=None)` signature. Reject sizes other than
2 or 3 with `ValueError`; clamp sample/limit inputs to at least one. Use
parameterized optional lesson filtering for both the baseline and row query.
Calculate weighted averages with:

```sql
SUM(total_duration_ms) / SUM(sample_count)
```

Use `HAVING SUM(sample_count) >= ?`; order by average descending, samples
descending, sequence ascending; return `TransitionSummary` values with baseline
delta calculated in Python.

- [ ] **Step 4: Add persistence tests after implementation**

Add `TestTransitionPersistence` to `test_enhancements.py` covering opening an
existing pre-feature database, schema/index creation without data loss,
existence checks, round-trip values, weighted means, separate bigram/trigram
baselines, five-sample qualification, custom thresholds, deterministic ties,
lesson filters, invalid sizes, and 101-session retention.
The retention test must call the write API with an empty aggregate for the final
session and prove the first session’s rows are removed.

- [ ] **Step 5: Verify persistence**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest test_enhancements.py -q -p no:cacheprovider --basetemp=.cache/transition-persistence --tb=short
```

Expected: the enhancement tests pass, including existing migrations and goals.

---

### Task 4: Completion Persistence Gates

**Files:**

- Modify: `core/session_controller.py:161-257`
- Modify: `test_session_controller.py:99-end`

**Interfaces:**

- Consumes: `aggregate_transition_samples()` and `add_session_transition_stats()`.
- Produces: eligible transition persistence with no new `FinalizeResult` fields.

- [ ] **Step 1: Submit aggregates after recording session history**

Inside the existing non-warmup finalization block, immediately after
`add_session_record(record)`, add:

```python
transition_aggregates = (
    []
    if answer_imported
    else aggregate_transition_samples(self.session.transition_samples)
)
self.progress_store.add_session_transition_stats(
    record.timestamp,
    record.lesson_index,
    record.lesson_name,
    transition_aggregates,
)
```

The empty call is required for retention. Never call it from warmup completion.

- [ ] **Step 2: Add finalization tests after implementation**

Seed known `TransitionSample` values and prove normal lessons, free-practice
completion, and timed-out sessions persist them; warmup does not;
answer-imported completion still records ordinary history but no transitions;
and empty normal sessions exercise pruning. Use real temporary stores rather
than mocking the SQLite contract.

- [ ] **Step 3: Verify finalization integration**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest test_session_controller.py test_enhancements.py -q -p no:cacheprovider --basetemp=.cache/transition-finalize --tb=short
```

Expected: all focused tests pass with completion rewards/history unchanged.

---

### Task 5: Lazy Statistics Transitions Tab

**Files:**

- Modify: `ui/dialogs.py:1-46, 70-161, 611-645`
- Modify: `test_enhancements.py`

**Interfaces:**

- Consumes: transition existence/ranking APIs, `TransitionSummary`, `MIN_TRANSITION_SAMPLES`, and `format_transition_sequence()`.
- Produces: `_create_transitions_tab()` and read-only result tables.

- [ ] **Step 1: Add Qt and transition imports**

Import `QAbstractItemView`, `QHeaderView`, `QTableWidget`, and
`QTableWidgetItem`, plus:

```python
from core.transitions import (
    MIN_TRANSITION_SAMPLES,
    TransitionSummary,
    format_transition_sequence,
)
```

- [ ] **Step 2: Register lazy tab construction**

Append `("⌨️ Transitions", self._create_transitions_tab)` after Error Trends in
`_tab_specs`. Do not query during dialog construction.

- [ ] **Step 3: Build a read-only table helper**

Add `_create_transition_table(self, summaries: List[TransitionSummary]) ->
QTableWidget`. Use columns `Sequence`, `Average time`, `Samples`, `Versus
baseline`; disable editing; hide the vertical header; alternate row colors; and
size headers for the 700×550 dialog.

Format cells exactly as follows:

```python
sequence = format_transition_sequence(summary.sequence)
average = f"{summary.average_ms:.0f} ms"
samples = str(summary.sample_count)
baseline = (
    f"{abs(delta):.1f}% slower" if delta > 0.05
    else f"{abs(delta):.1f}% faster" if delta < -0.05
    else "At baseline"
)
```

- [ ] **Step 4: Build the tab and both empty states**

Query `has_transition_data()`, then global size-2 and size-3 rankings. With no
stored data, show the approved no-data message. Otherwise create `Slowest
Bigrams` and `Slowest Trigrams` groups, each containing its table or the
collecting-state message when fewer than five samples qualify. Include the
threshold explanation and make content scrollable if needed; do not resize the
whole dialog.

- [ ] **Step 5: Add offscreen UI tests after implementation**

Test lazy construction, no-data text, collecting text, qualified rows, visible
`␠`, rounded milliseconds, sample counts, baseline wording, and reachability of
both group boxes at minimum size. Seed only public persistence APIs and process
queued Qt events.

- [ ] **Step 6: Verify the Statistics UI**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\.venv\Scripts\python.exe -m pytest test_enhancements.py -q -p no:cacheprovider --basetemp=.cache/transition-ui --tb=short
```

Expected: all Statistics and enhancement tests pass offscreen.

---

### Task 6: Documentation and Final Verification

**Files:**

- Modify: `README.md`
- Modify: `docs/suggestions.md`
- Modify: `docs/MASTER.md`
- Modify: `docs/CHANGELOG.md`
- Verify: all Python and documentation changes

**Interfaces:**

- Consumes: verified Tasks 1-5.
- Produces: accurate project status and fresh completion evidence.

- [ ] **Step 1: Reconcile documentation after focused checks pass**

- `README.md`: add local slow-transition analysis and its fresh-data note.
- `docs/suggestions.md`: mark Adaptive Drills, Goal/Streak Tracking,
  Bigram/Trigram Analysis, SessionController extraction, and per-key accuracy
  display complete. Leave lesson gating, URL import, and per-finger WPM open.
  Replace “Only one test file” with the verified test-file count after adding
  `test_transitions.py`; leave mypy and pre-commit open.
- `docs/MASTER.md`: add the shipped transition feature and remove the obsolete
  pending SessionController note.
- `docs/CHANGELOG.md`: add `Unreleased` notes for timing semantics, privacy,
  fresh-data behavior, schema, and Statistics UI without inventing a version.

- [ ] **Step 2: Run the complete suite with a fresh local base directory**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --ignore=.test-tmp-weak-initial --basetemp=.cache/transition-full --tb=short
```

Expected: zero failures/errors. Report the exact fresh pass count.

- [ ] **Step 3: Run syntax and diff hygiene checks**

Run these commands separately:

```powershell
.\.venv\Scripts\python.exe -m compileall -q core ui main.py
```

```powershell
git diff --check
```

```powershell
git status --short
```

Expected: compileall exits `0`; diff-check prints nothing; status lists only the
approved transition feature, its tests/spec/plan, and documentation.

- [ ] **Step 4: Run an offscreen dialog smoke check**

Create a temporary store, add one session and qualified bigram/trigram
aggregates through public APIs, construct `StatisticsDialog` under the offscreen
platform, select Transitions, process queued events, and assert both groups and
rows exist. Do not create progress data in the repository root.

- [ ] **Step 5: Review every acceptance criterion**

Confirm section 14 of the approved spec line by line, especially raw-data
privacy, imported/warmup exclusions, empty-aggregate pruning, unchanged key
accounting/scoring, independent baselines, distinct empty states, and absence of
unrelated refactors. Record any gap instead of claiming completion.

- [ ] **Step 6: Hand off without committing**

Report files changed, exact test counts, compile/offscreen/diff results,
unperformed manual checks, and branch/commit/push/working-tree state. Do not
stage, commit, merge, push, or delete generated paths without a new explicit
request.

---

## Execution Boundary

Implementation must run inline and sequentially in this task because repository
instructions forbid parallel subagents and automatic plan execution. Stop for
user review before Task 1.
