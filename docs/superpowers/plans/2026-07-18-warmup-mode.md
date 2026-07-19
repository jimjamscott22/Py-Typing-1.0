# Warmup Mode Implementation Plan

> **Execution note:** Per explicit user instruction, this plan is executed directly in-session (not via superpowers:subagent-driven-development or superpowers:executing-plans, and without a strict TDD red/green ceremony). Each task still ends with real tests that are run and confirmed passing before committing.

**Goal:** Add a manual, non-recording "warmup" typing mode: a toggle button that swaps in a canned drill phrase, loops to a new phrase on every completion, and never writes to `ProgressStore` — restoring the user's prior lesson/free-practice state when toggled off.

**Architecture:** A new `core/warmup.py` module supplies canned phrases. `TypingPracticeApp` gains a `warmup_mode` flag and a third `self.mode` value (`"warmup"`), threaded through the existing single completion funnel (`_finalize_session`) with one guard around all persistence calls, and a toggle button that snapshots/restores prior state.

**Tech Stack:** PyQt6, pytest, `QT_QPA_PLATFORM=offscreen` for headless GUI tests.

## Global Constraints

- Python ≥ 3.14 (per `pyproject.toml` / `.python-version`) — use `str | None` union syntax, not `typing.Optional`, in new code.
- No changes to `core/models.py` or `core/persistence.py` schemas.
- No Settings-dialog entry or persisted preference for warmup — it is a session-only toggle.
- Reuse the existing `_finalize_session` funnel rather than adding a parallel completion path.
- Run `uv run pytest test_enhancements.py -v` after every task; all tests must pass before moving on.

---

### Task 1: `core/warmup.py` — warmup phrase pool

**Files:**
- Create: `core/warmup.py`
- Test: `test_enhancements.py` (new `TestWarmup` class)

**Interfaces:**
- Produces: `WARMUP_PHRASES: list[str]` and `get_warmup_text(exclude: str | None = None) -> str`, consumed by `ui/main_window.py` in Task 3.

- [ ] **Step 1: Create `core/warmup.py`**

```python
import random

WARMUP_PHRASES = [
    "the quick brown fox jumps over the lazy dog",
    "pack my box with five dozen liquor jugs",
    "sphinx of black quartz judge my vow",
    "how vexingly quick daft zebras jump",
    "the five boxing wizards jump quickly",
    "waltz nymph for quick jigs vex bud",
]


def get_warmup_text(exclude: str | None = None) -> str:
    """Return a random warmup drill phrase, avoiding an immediate repeat of `exclude`."""
    choices = WARMUP_PHRASES
    if exclude is not None and len(WARMUP_PHRASES) > 1:
        choices = [phrase for phrase in WARMUP_PHRASES if phrase != exclude]
    return random.choice(choices)
```

- [ ] **Step 2: Add tests to `test_enhancements.py`**

Add this import near the top, alongside the other `core.*` imports:

```python
from core.warmup import WARMUP_PHRASES, get_warmup_text
```

Add this class anywhere after `TestWordgen`:

```python
class TestWarmup:
    def test_get_warmup_text_returns_known_phrase(self):
        text = get_warmup_text()
        assert text in WARMUP_PHRASES

    def test_get_warmup_text_avoids_immediate_repeat(self):
        first = get_warmup_text()
        for _ in range(20):
            second = get_warmup_text(exclude=first)
            assert second != first
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest test_enhancements.py -v -k TestWarmup`
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add core/warmup.py test_enhancements.py
git commit -m "Add warmup phrase pool for warmup typing mode"
```

---

### Task 2: `WARMUP_DESCRIPTION` constant

**Files:**
- Modify: `core/constants.py:25-28`

**Interfaces:**
- Produces: `WARMUP_DESCRIPTION: str`, consumed by `ui/main_window.py` in Task 3.

- [ ] **Step 1: Add the constant next to the existing free-practice strings**

In `core/constants.py`, change:

```python
FREE_PRACTICE_DESCRIPTION = (
    "Free practice mode: paste or import any text, click <b>Use Custom Text</b>, and start typing."
)
FREE_PRACTICE_PLACEHOLDER = "Provide custom text or import a file to begin."
```

to:

```python
FREE_PRACTICE_DESCRIPTION = (
    "Free practice mode: paste or import any text, click <b>Use Custom Text</b>, and start typing."
)
FREE_PRACTICE_PLACEHOLDER = "Provide custom text or import a file to begin."

WARMUP_DESCRIPTION = (
    "🔥 Warmup mode: loosen up your fingers. Nothing typed here is recorded to your history or stats."
)
```

- [ ] **Step 2: Commit**

```bash
git add core/constants.py
git commit -m "Add WARMUP_DESCRIPTION constant"
```

(No standalone test — this constant is exercised by the Task 4 GUI tests.)

---

### Task 3: `TypingPracticeApp` state + mode-aware description branches

**Files:**
- Modify: `ui/main_window.py:35-50` (imports)
- Modify: `ui/main_window.py:64-90` (`__init__`)
- Modify: `ui/main_window.py:512-516` (`_apply_theme`)
- Modify: `ui/main_window.py:824-828` (`reset_exercise`)
- Modify: `ui/main_window.py:1134-1137` (`_start_timed_mode_if_enabled`)

**Interfaces:**
- Consumes: `WARMUP_DESCRIPTION` (Task 2), `get_warmup_text` (Task 1).
- Produces: `self.warmup_mode: bool`, `self._pre_warmup_state: dict | None`, both consumed by Task 4/5.

- [ ] **Step 1: Import the new constant and function**

In `ui/main_window.py`, change the `core.constants` import block (lines 35-50):

```python
from core.constants import (
    DEFAULT_BACKSPACE_PENALTY,
    DEFAULT_BACKSPACE_ACCURACY_WEIGHT,
    DEFAULT_STRICT_MODE,
    DEFAULT_SHOW_KEYBOARD,
    DEFAULT_SHOW_CELEBRATION,
    DEFAULT_FONT_SIZE,
    DEFAULT_RANDOM_WORD_COUNT,
    DEFAULT_DEVELOPER_KEYS_LENGTH,
    DEFAULT_DEVELOPER_KEYS_MODE,
    DEFAULT_THEME,
    DEFAULT_TIMED_MODE_SECONDS,
    DEFAULT_ADAPTIVE_DRILLS,
    FREE_PRACTICE_DESCRIPTION,
    FREE_PRACTICE_PLACEHOLDER,
)
```

to:

```python
from core.constants import (
    DEFAULT_BACKSPACE_PENALTY,
    DEFAULT_BACKSPACE_ACCURACY_WEIGHT,
    DEFAULT_STRICT_MODE,
    DEFAULT_SHOW_KEYBOARD,
    DEFAULT_SHOW_CELEBRATION,
    DEFAULT_FONT_SIZE,
    DEFAULT_RANDOM_WORD_COUNT,
    DEFAULT_DEVELOPER_KEYS_LENGTH,
    DEFAULT_DEVELOPER_KEYS_MODE,
    DEFAULT_THEME,
    DEFAULT_TIMED_MODE_SECONDS,
    DEFAULT_ADAPTIVE_DRILLS,
    FREE_PRACTICE_DESCRIPTION,
    FREE_PRACTICE_PLACEHOLDER,
    WARMUP_DESCRIPTION,
)
from core.warmup import get_warmup_text
```

- [ ] **Step 2: Add warmup state to `__init__`**

Change (lines 67-68):

```python
        self.lesson_offset = 1
        self.mode = "lesson"
```

to:

```python
        self.lesson_offset = 1
        self.mode = "lesson"
        self.warmup_mode = False
        self._pre_warmup_state: dict | None = None
```

- [ ] **Step 3: Add a warmup branch to `_apply_theme`**

Change (lines 512-516):

```python
        if self.mode == "lesson":
            lesson = self.lessons[self.current_lesson_index]
            self._update_description(f"<b>Focus:</b> {lesson.description}", mode="default")
        else:
            self._update_description(FREE_PRACTICE_DESCRIPTION, mode="default")
```

to:

```python
        if self.mode == "lesson":
            lesson = self.lessons[self.current_lesson_index]
            self._update_description(f"<b>Focus:</b> {lesson.description}", mode="default")
        elif self.mode == "warmup":
            self._update_description(WARMUP_DESCRIPTION, mode="default")
        else:
            self._update_description(FREE_PRACTICE_DESCRIPTION, mode="default")
```

- [ ] **Step 4: Add a warmup branch to `reset_exercise`**

Change (lines 824-828):

```python
        if self.mode == "lesson":
            lesson_desc = self.lessons[self.current_lesson_index].description
            self._update_description(f"<b>Focus:</b> {lesson_desc}", mode="default")
        else:
            self._update_description(FREE_PRACTICE_DESCRIPTION, mode="default")
```

to:

```python
        if self.mode == "lesson":
            lesson_desc = self.lessons[self.current_lesson_index].description
            self._update_description(f"<b>Focus:</b> {lesson_desc}", mode="default")
        elif self.mode == "warmup":
            self._update_description(WARMUP_DESCRIPTION, mode="default")
        else:
            self._update_description(FREE_PRACTICE_DESCRIPTION, mode="default")
```

- [ ] **Step 5: Skip timed mode while warming up**

Change (lines 1134-1137):

```python
    def _start_timed_mode_if_enabled(self) -> None:
        if self._timed_mode_seconds <= 0:
            self.timer_label.setVisible(False)
            return
```

to:

```python
    def _start_timed_mode_if_enabled(self) -> None:
        if self.mode == "warmup":
            return
        if self._timed_mode_seconds <= 0:
            self.timer_label.setVisible(False)
            return
```

- [ ] **Step 6: Sanity-check the app still imports and launches headlessly**

Run: `QT_QPA_PLATFORM=offscreen uv run python -c "from ui.main_window import TypingPracticeApp; from PyQt6.QtWidgets import QApplication; app = QApplication([]); w = TypingPracticeApp(); print('ok', w.warmup_mode)"`
Expected: prints `ok False` with no traceback. (Run this from a scratch/temp working directory, since `TypingPracticeApp` writes `typing_progress.sqlite3` into the current directory.)

- [ ] **Step 7: Commit**

```bash
git add ui/main_window.py
git commit -m "Add warmup_mode state and mode-aware description branches"
```

---

### Task 4: Toggle button + enter/exit/loop lifecycle

**Files:**
- Modify: `ui/main_window.py:188-198` (`_build_sidebar` — add button)
- Modify: `ui/main_window.py` — add `_toggle_warmup_mode`, `_enter_warmup_mode`, `_exit_warmup_mode`, `_advance_warmup_round` methods (placed after `_show_settings`, end of class)
- Test: `test_enhancements.py` (new `TestWarmupToggle` class + fixtures)

**Interfaces:**
- Consumes: `self.warmup_mode`, `self._pre_warmup_state`, `get_warmup_text` (Task 3), `self.mode`, `self.lesson_list`, `self.free_controls`, `self.regenerate_button`, `self.next_button`, `self.lesson_title`, `self.target_text`, `self.reset_exercise()`, `self.load_lesson()`, `self._enter_free_practice()`, `self._update_best_wpm_label()` (all pre-existing).
- Produces: `self.warmup_button` (checkable `QPushButton`); `_toggle_warmup_mode(checked: bool)`, `_advance_warmup_round()` consumed by Task 5.

- [ ] **Step 1: Add the toggle button to the sidebar**

Change (lines 188-198):

```python
        self.stats_button = QPushButton("📊 View Statistics")
        self.stats_button.clicked.connect(self._show_statistics)
        self.stats_button.setToolTip("View your typing progress and statistics")
        button_layout.addWidget(self.stats_button)

        self.settings_button = QPushButton("⚙️ Settings")
        self.settings_button.clicked.connect(self._show_settings)
        self.settings_button.setToolTip("Configure app settings and penalties")
        button_layout.addWidget(self.settings_button)

        layout.addWidget(button_container)
```

to:

```python
        self.stats_button = QPushButton("📊 View Statistics")
        self.stats_button.clicked.connect(self._show_statistics)
        self.stats_button.setToolTip("View your typing progress and statistics")
        button_layout.addWidget(self.stats_button)

        self.settings_button = QPushButton("⚙️ Settings")
        self.settings_button.clicked.connect(self._show_settings)
        self.settings_button.setToolTip("Configure app settings and penalties")
        button_layout.addWidget(self.settings_button)

        self.warmup_button = QPushButton("🔥 Warmup")
        self.warmup_button.setCheckable(True)
        self.warmup_button.clicked.connect(self._toggle_warmup_mode)
        self.warmup_button.setToolTip(
            "Practice freely without recording your typing history or stats"
        )
        button_layout.addWidget(self.warmup_button)

        layout.addWidget(button_container)
```

- [ ] **Step 2: Add the lifecycle methods**

Add after `_show_settings` (end of the class, after line 1361's method body):

```python
    def _toggle_warmup_mode(self, checked: bool) -> None:
        """Enter or exit warmup mode from the sidebar toggle button."""
        if checked:
            self._enter_warmup_mode()
        else:
            self._exit_warmup_mode()

    def _enter_warmup_mode(self) -> None:
        """Snapshot current state and switch into a non-recording warmup drill."""
        self._pre_warmup_state = {
            "mode": self.mode,
            "lesson_index": self.current_lesson_index,
            "text_index": self.current_text_index,
        }
        self.warmup_mode = True
        self.mode = "warmup"
        self.lesson_list.setEnabled(False)
        self.free_controls.setEnabled(False)
        self.regenerate_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.warmup_button.setChecked(True)
        self.lesson_title.setText("🔥 Warmup")
        self._update_best_wpm_label()
        self.current_target_text = get_warmup_text()
        self.target_text.setText(self.current_target_text)
        self.reset_exercise()

    def _exit_warmup_mode(self) -> None:
        """Leave warmup mode and restore whichever lesson/free-practice state preceded it."""
        previous = self._pre_warmup_state
        self.warmup_mode = False
        self.warmup_button.setChecked(False)
        self.lesson_list.setEnabled(True)
        self.free_controls.setEnabled(True)
        self.regenerate_button.setEnabled(True)

        if previous is None or previous["mode"] == "free":
            self._enter_free_practice()
            return

        self.current_text_index = previous["text_index"]
        self.load_lesson(previous["lesson_index"], reset_text_index=False)

    def _advance_warmup_round(self) -> None:
        """Auto-load the next warmup phrase after a completed round."""
        if not self.warmup_mode:
            return
        self.current_target_text = get_warmup_text(exclude=self.current_target_text)
        self.target_text.setText(self.current_target_text)
        self.reset_exercise()
```

- [ ] **Step 3: Add GUI test fixtures and toggle tests to `test_enhancements.py`**

Add these imports near the top of `test_enhancements.py` (alongside the existing imports):

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from ui.main_window import TypingPracticeApp
```

Add these fixtures after the existing `store` fixture:

```python
@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    win = TypingPracticeApp()
    yield win
    win.close()
```

Add this test class:

```python
class TestWarmupToggle:
    def test_enter_warmup_sets_mode_and_disables_controls(self, window):
        window._toggle_warmup_mode(True)
        assert window.mode == "warmup"
        assert window.warmup_mode is True
        assert not window.lesson_list.isEnabled()
        assert not window.free_controls.isEnabled()

    def test_exit_warmup_restores_previous_lesson(self, window):
        window.load_lesson(1, reset_text_index=False)
        prior_index = window.current_lesson_index

        window._toggle_warmup_mode(True)
        assert window.mode == "warmup"

        window._toggle_warmup_mode(False)
        assert window.mode == "lesson"
        assert window.warmup_mode is False
        assert window.current_lesson_index == prior_index
        assert window.lesson_list.isEnabled()
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest test_enhancements.py -v -k TestWarmupToggle`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add ui/main_window.py test_enhancements.py
git commit -m "Add warmup mode toggle button and enter/exit/loop lifecycle"
```

---

### Task 5: Guard persistence in `_finalize_session` and loop on completion

**Files:**
- Modify: `ui/main_window.py:1186-1268` (`_finalize_session`)
- Test: `test_enhancements.py` (new tests in `TestWarmupToggle`)

**Interfaces:**
- Consumes: `self.warmup_mode` (Task 3), `self._advance_warmup_round` (Task 4).
- Produces: the core behavioral guarantee of this feature — no change in external interface.

- [ ] **Step 1: Guard the record-building/persistence block and branch the completion timer**

Change the tail of `_finalize_session` (lines 1222-1268) from:

```python
        lesson_name = (
            self.lessons[self.current_lesson_index].title
            if self.mode == "lesson" else "Free Practice"
        )
        record = SessionRecord(
            timestamp=datetime.now().isoformat(),
            lesson_index=self.current_lesson_index if self.mode == "lesson" else -1,
            text_index=self.current_text_index,
            lesson_name=lesson_name,
            wpm=wpm,
            accuracy=round(accuracy, 1),
            errors=self.session.errors + max(
                len(self.session.typed_text) - len(self.current_target_text), 0
            ),
            backspaces=backspace_count,
            duration_seconds=round(elapsed_time, 1),
            text_length=len(self.session.typed_text) if timed_out else len(self.current_target_text),
        )
        self.progress_store.add_session_record(record)

        if self.session.key_errors:
            self.progress_store.update_key_error_stats(self.session.key_errors)
        if self.session.key_attempts:
            self.progress_store.update_key_attempt_stats(self.session.key_attempts)

        if self.session.key_errors:
            self.progress_store.add_session_key_stats(
                record.timestamp,
                record.lesson_index,
                lesson_name,
                self.session.key_errors,
                self.session.key_attempts,
            )

        if self.mode == "lesson":
            self._record_best_wpm(wpm)

        self.progress_store.save()

        if (
            not timed_out
            and self.progress_store.get_setting("show_celebration", DEFAULT_SHOW_CELEBRATION)
        ):
            self.celebration_overlay.start()
            CelebrationSoundManager.play()

        QTimer.singleShot(2000, self._unlock_text_input)
```

to:

```python
        if not self.warmup_mode:
            lesson_name = (
                self.lessons[self.current_lesson_index].title
                if self.mode == "lesson" else "Free Practice"
            )
            record = SessionRecord(
                timestamp=datetime.now().isoformat(),
                lesson_index=self.current_lesson_index if self.mode == "lesson" else -1,
                text_index=self.current_text_index,
                lesson_name=lesson_name,
                wpm=wpm,
                accuracy=round(accuracy, 1),
                errors=self.session.errors + max(
                    len(self.session.typed_text) - len(self.current_target_text), 0
                ),
                backspaces=backspace_count,
                duration_seconds=round(elapsed_time, 1),
                text_length=len(self.session.typed_text) if timed_out else len(self.current_target_text),
            )
            self.progress_store.add_session_record(record)

            if self.session.key_errors:
                self.progress_store.update_key_error_stats(self.session.key_errors)
            if self.session.key_attempts:
                self.progress_store.update_key_attempt_stats(self.session.key_attempts)

            if self.session.key_errors:
                self.progress_store.add_session_key_stats(
                    record.timestamp,
                    record.lesson_index,
                    lesson_name,
                    self.session.key_errors,
                    self.session.key_attempts,
                )

            if self.mode == "lesson":
                self._record_best_wpm(wpm)

            self.progress_store.save()

        if (
            not timed_out
            and self.progress_store.get_setting("show_celebration", DEFAULT_SHOW_CELEBRATION)
        ):
            self.celebration_overlay.start()
            CelebrationSoundManager.play()

        if self.warmup_mode:
            QTimer.singleShot(2000, self._advance_warmup_round)
        else:
            QTimer.singleShot(2000, self._unlock_text_input)
```

- [ ] **Step 2: Add the persistence-guard tests**

Add to `TestWarmupToggle` in `test_enhancements.py`:

```python
    def test_completing_warmup_round_does_not_persist(self, window, monkeypatch):
        added = []
        saved = []
        monkeypatch.setattr(
            window.progress_store, "add_session_record", lambda record: added.append(record)
        )
        monkeypatch.setattr(window.progress_store, "save", lambda: saved.append(True))

        window._toggle_warmup_mode(True)
        target = window.current_target_text
        window.typing_input.setPlainText(target)

        assert added == []
        assert saved == []

    def test_normal_completion_still_persists_after_exiting_warmup(self, window, monkeypatch):
        added = []
        saved = []
        monkeypatch.setattr(
            window.progress_store, "add_session_record", lambda record: added.append(record)
        )
        monkeypatch.setattr(window.progress_store, "save", lambda: saved.append(True))

        window._toggle_warmup_mode(True)
        window._toggle_warmup_mode(False)
        assert window.mode == "lesson"

        target = window.current_target_text
        window.typing_input.setPlainText(target)

        assert len(added) == 1
        assert saved
```

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest test_enhancements.py -v`
Expected: all tests pass, including the 4 new `TestWarmupToggle` tests and 2 `TestWarmup` tests.

- [ ] **Step 4: Manual smoke test**

Run: `uv run main.py`
- Click "🔥 Warmup" — confirm the target text switches to a canned phrase, lesson list/free-practice controls disable, and the description banner shows the warmup message.
- Type the full phrase — confirm WPM/accuracy/keyboard heatmap update live, the completion message shows, and after ~2 seconds a new phrase loads automatically without any manual action.
- Click "🔥 Warmup" again to exit — confirm the app returns to the lesson/text you were on before, controls re-enable, and completing that lesson's text now shows up in 📊 View Statistics.

- [ ] **Step 5: Commit**

```bash
git add ui/main_window.py test_enhancements.py
git commit -m "Guard session persistence during warmup mode and auto-loop drill phrases"
```

---

## Self-Review Notes

- **Spec coverage:** dedicated warmup content (Task 1), toggle-button entry/exit (Task 4), manual loop until exit (Task 4 `_advance_warmup_round` + Task 5 timer branch), live stats without persistence (Task 5 guard — WPM/accuracy/keyboard code paths are untouched, only the `ProgressStore` calls are gated) are all covered.
- **Placeholder scan:** none found — every step has real code and real commands.
- **Type consistency:** `get_warmup_text(exclude: str | None = None)` (Task 1) is called identically in Task 4's `_enter_warmup_mode` (`get_warmup_text()`) and `_advance_warmup_round` (`get_warmup_text(exclude=...)`) — signatures match throughout.
