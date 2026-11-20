# Code Snippets and Key Sounds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ~90 developer code snippets (10 languages × 3 tiers, incl. PowerShell and Active Directory) as sidebar lessons, plus optional synthesized mechanical-switch key sounds.

**Architecture:** Snippets are data modules assembled into extra `Lesson`s appended after the existing lessons (indexes never shift). Multi-line typing is made usable by auto-filling indentation after Enter, tracked in `TypingSession` and excluded from every statistic. Key sounds are pure-Python synthesized WAVs played from preloaded `QSoundEffect`s, triggered from the existing per-keystroke `user_edited` hook.

**Tech Stack:** Python ≥3.14, PyQt6 (`QtMultimedia.QSoundEffect`), stdlib `wave`/`math`, pytest via `uv run pytest`.

**Spec:** `docs/superpowers/specs/2026-11-19-code-snippets-and-key-sounds-design.md` (read it first; this plan implements it).

## Global Constraints

- No new dependencies. Sound synthesis uses stdlib `wave`/`math` only (no numpy). Package management via `uv`.
- Existing lesson indexes never change: the 18 existing lessons stay first ("Weak Key Practice" is index 17, `texts == ["__WEAK_KEYS__"]`); snippet lessons are appended after it.
- Snippets: 3–12 lines, ≤450 characters, no line >72 characters, ASCII, `\n` newlines, spaces only (no tabs, Go included), no trailing whitespace, no final newline, 3 snippets per tier, written fresh (do not copy TypeForge-R text).
- Languages, in sidebar order: TypeScript, JavaScript, Python, Rust, Go, SQL, HTML/CSS, C++, PowerShell, Active Directory. Tiers: Junior, Mid, Senior.
- Auto-filled indentation is never an attempt, error, transition sample, feedback event or sound, and is excluded from WPM, accuracy, recorded `text_length` and the backspace penalty.
- The curriculum achievement target must not grow (snippet lessons contribute 0 to `lesson_text_counts`).
- Key sounds: default `off`, default volume 60; audio failures never raise on the typing path; WAVs are 44.1 kHz, 16-bit, mono, peak <1.0.
- New test files start with `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")` before Qt imports and reuse the `qapp`/`window` fixtures pattern from `test_weak_keys.py`. Run tests with `uv run pytest -q`.
- Commits: conventional style (`feat:`, `test:`, `docs:`), one per task, on the current branch.

## Review Focus

Input classes the spec implies but a happy-path build would miss (each is pinned by a test in the owning task):

1. Cursor moved with arrow keys and an edit made *before* auto-filled indentation → statistics stay sane, nothing crashes (Tasks 1, 2).
2. Pasting multi-line code into the typing box → no auto-fill, no sound, still marked as imported (Tasks 2, 13).
3. No audio device / `QSoundEffect` failing → typing keeps working, sounds silently off (Task 12).
4. Largest font (28 pt) with a 12-line snippet → keyboard and controls must stay on screen (Task 3, screenshot check).
5. Timed mode enabled while on a fixed (non-generated) snippet lesson → no crash, text not extended (Task 5).

---

## Part A — Multi-line typing

### Task 1: Auto-fill core (pure logic and stats helpers)

**Files:**
- Create: `core/autoindent.py`
- Modify: `core/models.py` (`TypingSession`), `core/scoring.py`
- Test: `test_autoindent.py` (new), `test_scoring.py` (extend)

**Interfaces:**
- Produces:
  - `auto_fill_text(target_text: str, typed_text: str, changes: Sequence[TextChange]) -> str` — returns the spaces to insert, or `""`.
  - On `TypingSession` (new field `auto_filled: Set[int]`, cleared by `reset()`): `register_auto_fill(start: int, length: int) -> None`, `is_auto_filled(index: int) -> bool`, `auto_filled_count -> int` (property, `len(auto_filled)`), `keystroke_length(typed_len: int) -> int` (`typed_len` minus auto-filled positions `< typed_len`), `prune_auto_fill(typed_len: int) -> None` (drop positions `>= typed_len`), `note_edit(position: int, removed: int) -> None` (if `auto_filled` is non-empty, the edit is not at the tail — `position + removed < len(self.typed_text)` — and `position <= max(auto_filled)`, clear `auto_filled`; conservative).
  - `calculate_wpm(..., auto_filled: int = 0)` and `calculate_accuracy(..., auto_filled: int = 0)`: both treat `len(typed) - auto_filled` as the character count (accuracy returns `100.0` when that is ≤0).

- [ ] **Step 1: Write failing tests in `test_autoindent.py`.** Use `TARGET = "if x:\n    y()\n    if z:\n        w()"`. Tests (name → assertion):
  - `test_fills_next_line_indent`: `auto_fill_text(TARGET, "if x:\n", [TextChange(5, 0, "\n")]) == "    "`
  - `test_fills_nested_indent`: typed `"if x:\n    y()\n    if z:\n"`, change at position `len(typed)-1` → `"        "` (8 spaces)
  - `test_no_fill_when_prefix_mismatches`: typed `"iF x:\n"` → `""`
  - `test_no_fill_for_non_newline_insert`: `[TextChange(3, 0, "x")]` → `""`
  - `test_no_fill_for_backspace_or_multichar_change`: `[TextChange(5, 1, "")]` and `[TextChange(4, 0, ":\n")]` → `""`
  - `test_no_fill_when_next_line_unindented`: target `"a\nb"`, typed `"a\n"` → `""`
  - `test_no_fill_for_whitespace_only_line`: target `"a\n    \nb"`, typed `"a\n"` → `""`
  - `test_no_fill_when_newline_is_last_char`: target `"a\n"`, typed `"a\n"` → `""`
  - `test_no_fill_when_not_at_end`: typed `"if x:\nzz"` with change at position 5 → `""`
  - Session tests: `test_keystroke_length_excludes_auto_filled` (`register_auto_fill(6, 4)`; `keystroke_length(10) == 6`, `keystroke_length(8) == 6`, `keystroke_length(6) == 6`); `test_prune_drops_positions_past_typed_length`; `test_note_edit_clears_on_interior_edit_before_fill` (typed_text `"x"*10`, fill at 6–9, `note_edit(2, 1)` → `auto_filled == set()`); `test_note_edit_keeps_tail_deletion` (`note_edit(8, 2)` keeps 6–9); `test_note_edit_keeps_edit_after_fill` (typed_text `"x"*12`, `note_edit(10, 1)` keeps 6–9); `test_reset_clears_auto_fill`.
  - In `test_scoring.py`: `calculate_wpm("a"*60, 60.0, 0, 3, auto_filled=10) == 10`; `calculate_accuracy("a"*8, "a"*8, 1, 0, 0.5, auto_filled=4) == 75.0`; `calculate_accuracy("    ", "    ", 0, 0, 0.5, auto_filled=4) == 100.0`.
- [ ] **Step 2: Run** `uv run pytest -q test_autoindent.py test_scoring.py` — Expected: FAIL (module/params missing).
- [ ] **Step 3: Implement** `core/autoindent.py::auto_fill_text` (rules from the spec §5.5: exactly one change, `removed == 0`, `inserted == "\n"`, `len(typed_text) == change.position + 1`, `typed_text == target_text[:len(typed_text)]`; count leading spaces of the remaining target; return `""` if zero, if the run reaches the end of the target, or if the run is followed by `"\n"`), the `TypingSession` members above in `core/models.py`, and the `auto_filled` parameters in `core/scoring.py`.
- [ ] **Step 4: Run** the same command — Expected: PASS; then `uv run pytest -q` — Expected: all existing tests still pass.
- [ ] **Step 5: Commit** `feat: add auto-fill indentation core and keystroke-length stats helpers`

### Task 2: Wire auto-fill into the window and statistics

**Files:**
- Modify: `ui/typing_input.py`, `ui/main_window.py` (`_on_user_edit`, `eventFilter` backspace branch, `_calculate_wpm`, `_calculate_accuracy`), `core/session_controller.py` (`update_typed_text`, `record_edit`, `finalize`)
- Test: `test_autoindent_window.py` (new)

**Interfaces:**
- Consumes: Task 1 (`auto_fill_text`, `TypingSession` helpers, scoring params).
- Produces: `TypingInput.insert_auto_fill(text: str) -> None` — appends `text` at the end of the document **without** setting `editing`, so `_capture_change` records no `TextChange` and `user_edited` is not emitted (the trackers therefore never see it).

- [ ] **Step 1: Write failing tests** in `test_autoindent_window.py` (copy the `qapp`/`window` fixtures and `set_target(window, text)` helper from `test_weak_keys.py`). Use `TARGET = "if x:\n    y()"`:
  - `test_enter_auto_fills_indent`: `keyClicks "if x:"`, `keyClick Key_Return` → `typing_input.toPlainText() == "if x:\n    "` and `window.session.typed_text` equals it.
  - `test_round_completes_with_auto_filled_indent`: type `"if x:"`, Return, `"y()"` → `window._round_complete is True`.
  - `test_auto_fill_not_counted_in_attempts_errors_or_transitions`: after the full round, `window.session.key_attempts.get(" ") == 1` (only the real space), `key_errors == {}`, and no transition sample's sequence contains two adjacent spaces.
  - `test_text_length_and_wpm_use_keystroke_characters`: last history row's `text_length == len(TARGET) - 4`; `window._calculate_wpm(window.session.typed_text, elapsed=60.0) == calculate_wpm("x" * (len(TARGET) - 4), 60.0, 0, window._backspace_penalty)`.
  - `test_backspace_over_auto_fill_is_not_penalised`: after `"if x:"` + Return, four Backspaces → `backspace_count == 0`; a fifth (deleting the newline) → `== 1`.
  - `test_no_auto_fill_in_free_practice`: `window.mode = "free"` then type + Return → text is `"if x:\n"`.
  - `test_paste_is_not_auto_filled` (Review Focus 2): `insertFromMimeData` with `QMimeData` text `"if x:\n"` → `toPlainText() == "if x:\n"`.
  - `test_interior_edit_before_fill_keeps_stats_sane` (Review Focus 1): after `"if x:"` + Return, move the cursor to position 0 and type `"z"` → no exception, `window.session.auto_filled == set()`, `window.session.keystroke_length(len(window.session.typed_text)) == len(window.session.typed_text)`.
- [ ] **Step 2: Run** `uv run pytest -q test_autoindent_window.py` — Expected: FAIL.
- [ ] **Step 3: Implement.** (a) `TypingInput.insert_auto_fill(text: str) -> None` as specified. (b) In `_on_user_edit`, after `controller.record_edit(...)`: if `self.mode == "lesson" and not self.warmup_mode`, compute `fill = auto_fill_text(self.current_target_text, self.typing_input.toPlainText(), changes)`; if non-empty, call `self.session.register_auto_fill(len(self.typing_input.toPlainText()), len(fill))` **before** `self.typing_input.insert_auto_fill(fill)`; then the existing `self.on_text_changed()`. (c) `SessionController.update_typed_text` calls `self.session.prune_auto_fill(len(typed_text))`; `record_edit` calls `self.session.note_edit(change.position, change.removed)` first for each change. (d) `finalize` passes `auto_filled=self.session.auto_filled_count` to both scoring calls and records `text_length` as `self.session.keystroke_length(len(typed))` when `timed_out`, else `len(target_text) - self.session.auto_filled_count`. (e) `_calculate_wpm`/`_calculate_accuracy` pass `auto_filled=self.session.auto_filled_count`. (f) In `eventFilter`'s Backspace branch, skip `backspace_count += 1` when `self.session.is_auto_filled(len(self.session.typed_text) - 1)`.
- [ ] **Step 4: Run** `uv run pytest -q` — Expected: PASS (whole suite). **Gate:** Tasks 5–9 (snippet content) must not start until this passes. If auto-fill cannot be made to keep every statistic clean without invasive changes, stop and ask the user before choosing the spec's fallback (drop auto-fill, cap indentation at two levels of two spaces).
- [ ] **Step 5: Commit** `feat: auto-fill indentation after Enter, excluded from statistics`

### Task 3: Typing frame grows for multi-line targets

**Files:**
- Modify: `core/constants.py`, `ui/main_window.py` (make `terminal_frame` an attribute `self.terminal_frame`; add `_fit_terminal_frame_height`; call it at the top of `update_display`)
- Test: `test_snippet_layout.py` (new)

**Interfaces:**
- Produces: constants `TERMINAL_MIN_HEIGHT = 150`, `TERMINAL_MAX_LINES = 12`; `TypingPracticeApp._fit_terminal_frame_height() -> None` — sets `self.terminal_frame.setMaximumHeight(h)` with `h = clamp(lines * spacing + 44, TERMINAL_MIN_HEIGHT, TERMINAL_MAX_LINES * spacing + 44)`, where `lines = current_target_text.count("\n") + 1`, `spacing = QFontMetrics(self.typing_input.font()).lineSpacing()` and 44 is the input's vertical padding (40) plus border (4). Recompute only when `(lines, font size)` changed.

- [ ] **Step 1: Write failing tests** (`set_target(window, text)` then `window.update_display()`): `test_single_line_keeps_150` (`terminal_frame.maximumHeight() == 150`); `test_eight_lines_grow` (`> 150` and `>= 8 * spacing + 44`); `test_thirty_lines_capped` (`== 12 * spacing + 44`); `test_returns_to_150_for_single_line_again`; `test_font_size_change_refits` (set font size setting 28, `window._apply_settings()`, `update_display()` → height for 8 lines increases vs. 12 pt).
- [ ] **Step 2: Run** `uv run pytest -q test_snippet_layout.py` — Expected: FAIL.
- [ ] **Step 3: Implement** as specified; `_apply_settings` also invalidates the fit cache after changing fonts.
- [ ] **Step 4: Run** `uv run pytest -q test_snippet_layout.py` — Expected: PASS.
- [ ] **Step 5: Screenshot check (Review Focus 4).** In a scratch directory (not the repo) run an offscreen script: construct `TypingPracticeApp`, set font size 28, `set_target` to a 12-line, 70-character-wide snippet, `window.show()`, `window.grab().save("<scratch>/layout.png")`; open the PNG and confirm the typing box shows all lines and the keyboard/controls are still visible. If controls are pushed off screen at the default window size, reduce `TERMINAL_MAX_LINES` until they fit and update the cap test.
- [ ] **Step 6: Commit** `feat: grow typing frame for multi-line targets`

---

## Part B — Snippets

### Task 4: Snippet infrastructure

**Files:**
- Modify: `core/models.py` (add `Snippet`, add `Lesson.curriculum`), `core/lessons.py`, `ui/main_window.py`
- Create: `core/snippets.py`, `core/snippet_data/__init__.py`
- Test: `test_snippets.py` (new)

**Interfaces:**
- Produces:
  - `Snippet(language: str, difficulty: str, title: str, text: str)` — frozen dataclass in `core/models.py`; `Lesson` gains `curriculum: bool = True`.
  - `core/snippets.py`: `LANGUAGES` (spec order), `DIFFICULTIES = ("Junior", "Mid", "Senior")`, `TIER_BLURBS: dict[str, str]`, `SNIPPETS: tuple[Snippet, ...]` (concatenation of the per-language tuples exported by `core/snippet_data/__init__.py` as `ALL`, initially `()`), `build_snippet_lessons(snippets: Sequence[Snippet] = SNIPPETS) -> list[Lesson]` — groups by language (in `LANGUAGES` order) then tier; title `"{language} - {difficulty}"`, `category=language`, `curriculum=False`; raises `ValueError` for an unknown language or tier; skips empty groups; the Go lessons' descriptions say they use spaces instead of tabs.
  - `core/lessons.py`: `_build_core_lessons() -> List[Lesson]` (the current body of `build_lessons`), `build_lessons()` returns `_build_core_lessons() + build_snippet_lessons()`, `curriculum_text_counts(lessons: Sequence[Lesson]) -> List[int]` (`len(texts)` if `curriculum` else `0`), `completion_message(lesson: Lesson) -> str` (existing "🏆 Congratulations! You've completed all lessons!" for curriculum lessons, "🏆 You've finished all the code snippets!" otherwise).

- [ ] **Step 1: Write failing tests** in `test_snippets.py`:
  - `test_core_lessons_unchanged_and_first`: `core = lessons_module._build_core_lessons()`; `len(core) == 18`; `build_lessons()[:18] == core`; `core[17].texts == ["__WEAK_KEYS__"]`.
  - `test_build_snippet_lessons_groups_by_language_then_tier` using fabricated snippets (Python Mid, Python Junior, Rust Junior): titles `["Python - Junior", "Python - Mid", "Rust - Junior"]`, categories, text order preserved, all `curriculum is False`.
  - `test_sidebar_label_strips_prefix`: `lesson.title[len(f"{lesson.category} - "):] == "Junior"`.
  - `test_unknown_language_or_tier_rejected` (`pytest.raises(ValueError)`).
  - `test_curriculum_text_counts_ignore_snippets`: `counts = curriculum_text_counts(build_lessons())`; `sum(counts) == 62`; `counts[18:]` all zero.
  - `test_completion_message_differs_for_snippets`.
  - Quality tests over `SNIPPETS` (vacuous until content lands; `ids` = `"{language}-{difficulty}-{title}"`): `test_snippet_well_formed` (known language and tier; `text.isascii()`; no `"\t"`/`"\r"`; no line with trailing whitespace; not `endswith("\n")`; 3 ≤ lines ≤ 12; `len(text) <= 450`; every line ≤ 72), `test_no_duplicate_titles_or_texts`, `test_python_snippets_parse` (`ast.parse`).
  - `COMPLETED_LANGUAGES: list[str] = []` plus `test_language_covers_all_tiers_with_three_snippets` parametrized over it (each tier has ≥3 snippets); each content task appends its languages.
- [ ] **Step 2: Run** `uv run pytest -q test_snippets.py` — Expected: FAIL (imports missing).
- [ ] **Step 3: Implement** the interfaces above. In `ui/main_window.py` replace both `[len(lesson.texts) for lesson in self.lessons]` sites (finalize call and the Achievements dialog call) with `curriculum_text_counts(self.lessons)`, and the end-of-list `_update_description(...)` call in `next_text` with `completion_message(lesson)`.
- [ ] **Step 4: Run** `uv run pytest -q` — Expected: PASS (whole suite).
- [ ] **Step 5: Commit** `feat: add snippet lesson infrastructure appended after existing lessons`

### Content rules shared by Tasks 5–9

Each language gets a module `core/snippet_data/<name>.py` exporting `SNIPPETS: tuple[Snippet, ...]` with 3 snippets per tier (Junior, Mid, Senior), imported and added to `ALL` in `core/snippet_data/__init__.py` (static imports — PyInstaller needs them). Tier meaning: Junior = clean everyday constructs; Mid = operators, destructuring/pipelines, error handling; Senior = generics/lifetimes, regex, nested delimiters, concurrency, bulk operations. Titles are unique and descriptive. Code must be real, idiomatic and correct; only Python is machine-checked, so hand-review every other snippet for syntax. Each task ends by appending its languages to `COMPLETED_LANGUAGES` in `test_snippets.py`.

### Task 5: TypeScript, JavaScript, Python

**Files:** Create `core/snippet_data/{typescript,javascript,python}.py`; Modify `core/snippet_data/__init__.py`, `test_snippets.py`.

Topic guidance — TypeScript: J array filter/map, async fetch with try/catch, simple interface; M generic debounce hook, discriminated unions, `Promise.all`; S mapped/conditional types, type guards, `keyof` constraints. JavaScript: J loops/objects/template literals; M destructuring, `reduce`, optional chaining; S closures/memoize, generators, promise concurrency. Python: J comprehension, f-strings, `with open`; M dataclass, generators, decorators, context managers; S `asyncio.gather`, `Protocol`/generics, regex with named groups, `functools`.

- [ ] **Step 1:** Append `"TypeScript"`, `"JavaScript"`, `"Python"` to `COMPLETED_LANGUAGES`; add a window test `test_timed_mode_with_snippet_lesson_does_not_crash` (Review Focus 5): set `timed_mode_seconds` to 60 via `progress_store.set_setting`, `window._apply_settings()`, load the first lesson whose `curriculum` is False with `window.load_lesson(index)`, type its first character with `QTest.keyClicks` → no exception and `window.current_target_text` unchanged. Run `uv run pytest -q test_snippets.py` — Expected: FAIL.
- [ ] **Step 2: Author the three modules** (9 snippets each) and register them.
- [ ] **Step 3: Run** `uv run pytest -q test_snippets.py` — Expected: PASS (well-formedness, line width, `ast.parse` for Python, tier coverage, timed-mode test).
- [ ] **Step 4: Commit** `feat: add TypeScript, JavaScript and Python snippets`

### Task 6: Rust, Go, C++

**Files:** Create `core/snippet_data/{rust,go,cpp}.py`; Modify `core/snippet_data/__init__.py`, `test_snippets.py`.

Topic guidance — Rust: J `let`/`mut`, `match`, `Vec` iteration; M struct + `impl`, `Result` with `?`, `HashMap::entry`; S lifetimes, generic trait bounds, `Arc<Mutex<_>>`. Go: J slices, maps, `for range`; M structs with methods, error returns, `defer`; S goroutines with `sync.WaitGroup`, channels with `select`, generics. C++: J `vector` + range-for; M class with constructor, `unique_ptr`, lambdas with `<algorithm>`; S templates, RAII wrapper, move semantics. Go snippets use spaces, not tabs.

- [ ] **Step 1:** Append `"Rust"`, `"Go"`, `"C++"` to `COMPLETED_LANGUAGES`; run `uv run pytest -q test_snippets.py` — Expected: FAIL (tier coverage).
- [ ] **Step 2: Author the three modules** and register them.
- [ ] **Step 3: Run** `uv run pytest -q test_snippets.py` — Expected: PASS.
- [ ] **Step 4: Commit** `feat: add Rust, Go and C++ snippets`

### Task 7: SQL and HTML/CSS

**Files:** Create `core/snippet_data/{sql,html_css}.py`; Modify `core/snippet_data/__init__.py`, `test_snippets.py`.

Topic guidance — SQL: J `SELECT`/`WHERE`/`ORDER BY`; M `JOIN`, `GROUP BY`/`HAVING`; S CTEs, window functions, upserts (`ON CONFLICT`). HTML/CSS (language name `"HTML/CSS"`): J semantic page skeleton, simple rules; M flexbox, a form with attributes, `@media`; S grid areas, custom properties, `:is()`/`:not()` selectors, `@keyframes`.

- [ ] **Step 1:** Append `"SQL"`, `"HTML/CSS"` to `COMPLETED_LANGUAGES`; run `uv run pytest -q test_snippets.py` — Expected: FAIL.
- [ ] **Step 2: Author the two modules** and register them.
- [ ] **Step 3: Run** `uv run pytest -q test_snippets.py` — Expected: PASS.
- [ ] **Step 4: Commit** `feat: add SQL and HTML/CSS snippets`

### Task 8: PowerShell

**Files:** Create `core/snippet_data/powershell.py`; Modify `core/snippet_data/__init__.py`, `test_snippets.py`.

Topic guidance — J `Get-ChildItem | Where-Object`, `Get-Process`, variables and `foreach`; M functions with `param()` and `[ValidateSet()]`, splatting, `try/catch`, `Export-Csv`; S advanced function with `[CmdletBinding()]` and pipeline input, `Invoke-Command` remoting, `[PSCustomObject]`, regex with `-match`.

- [ ] **Step 1:** Add to `test_snippets.py` a `KNOWN_CMDLETS: set[str]` allowlist and `test_powershell_and_ad_cmdlets_are_known`: for every PowerShell and Active Directory snippet, every `Verb-Noun` token (regex `\b[A-Z][a-z]+-[A-Z][A-Za-z]+\b`) is in `KNOWN_CMDLETS`. Append `"PowerShell"` to `COMPLETED_LANGUAGES`. Run `uv run pytest -q test_snippets.py` — Expected: FAIL.
- [ ] **Step 2: Author the module** (9 snippets). Verify every cmdlet and parameter against Microsoft Learn using the Microsoft Learn MCP tools (`microsoft_docs_search`, `microsoft_docs_fetch`) and add each verified cmdlet to `KNOWN_CMDLETS`.
- [ ] **Step 3: Run** `uv run pytest -q test_snippets.py` — Expected: PASS.
- [ ] **Step 4: Commit** `feat: add PowerShell snippets` (note in the body that cmdlets were checked against Microsoft Learn).

### Task 9: Active Directory

**Files:** Create `core/snippet_data/active_directory.py`; Modify `core/snippet_data/__init__.py`, `test_snippets.py`.

Language name `"Active Directory"` (PowerShell ActiveDirectory-module cmdlets). Topic guidance — J `Get-ADUser -Identity`/`-Filter`, `Get-ADGroupMember`, `Get-ADComputer`; M `Search-ADAccount -LockedOut | Unlock-ADAccount`, `New-ADUser` with splatting, `Get-ADUser -Properties | Select-Object | Export-Csv`, `Add-ADGroupMember`; S bulk user import from CSV with `try/catch`, `Get-ADReplicationFailure`/`Get-ADDomainController`, `Get-GPO`/`Get-GPOReport`, `Invoke-Command` against domain controllers, `Get-ADDefaultDomainPasswordPolicy`.

- [ ] **Step 1:** Append `"Active Directory"` to `COMPLETED_LANGUAGES`; run `uv run pytest -q test_snippets.py` — Expected: FAIL (tier coverage and unknown cmdlets).
- [ ] **Step 2: Author the module** (9 snippets); verify every cmdlet and parameter against Microsoft Learn and extend `KNOWN_CMDLETS`.
- [ ] **Step 3: Run** `uv run pytest -q` — Expected: PASS (whole suite; all 10 languages complete, ~90 snippets).
- [ ] **Step 4: Commit** `feat: add Active Directory snippets`

---

## Part C — Key sounds

### Task 10: Key sound synthesis (pure)

**Files:** Create `core/keysounds.py`; Test: `test_keysounds.py` (new)

**Interfaces:**
- Produces: `SAMPLE_RATE = 44100`, `PROFILES = ("clicky", "tactile", "linear")`, `KINDS = ("letter", "space", "enter")`, `VARIANTS_PER_KIND = 4`, `synthesize(profile: str, kind: str, variant: int) -> bytes` and `synthesize_error() -> bytes` — each returns a complete WAV file (16-bit mono) as bytes; unknown profile/kind or variant outside `0..3` raises `ValueError`.

Recipe (ported from TypeForge-R's synth; `j` = `variant / 3 * 2 - 1` ∈ [-1, 1] replaces its random jitter, so output is deterministic). Each voice is an exponentially decaying amplitude × (sine/triangle at a frequency sweeping exponentially from f0 to f1) plus a band-passed (biquad, Q=2) white-noise burst from a `random.Random(seed)` seeded per (profile, kind, variant):

| Profile | Voice(s) | f0 → f1 (Hz) | Duration | Gain | Noise (centre Hz, dur, gain) |
|---|---|---|---|---|---|
| clicky | triangle "snap" | `3800+200j` → 800 (space: 2200 → 800) | 15 ms sweep, 18 ms decay | 0.45 | 1400, 20 ms (space 40 ms), 0.25 |
| clicky | sine body | letter `875+125j`, space 320, enter 420 → 120 | sweep 40 ms (space 60), decay 50 ms (space 70) | 0.5 | |
| tactile | triangle | `base*1.8` → `base*0.6`, base letter `480+40j`, space 260 | 35 ms sweep, 45 ms decay | 0.45 | 900, 25 ms, 0.2 |
| linear | sine | `base*1.4` → `base*0.5`, base letter `280+25j`, space 180 | 40 ms sweep, 45 ms decay (space 60) | 0.5 | 600, 30 ms, 0.15 |
| error | sawtooth through a one-pole low-pass at 450 Hz | 140 → 90 | 80 ms sweep, 90 ms | 0.35 | none |

`enter` uses the `space` parameters except clicky's body base of 420 Hz. Scale each result so its peak is ≤ 0.9 of full scale.

- [ ] **Step 1: Write failing tests** with a `_decode(data) -> list[int]` helper (`wave.open(io.BytesIO(data))`, assert `(channels, sampwidth, framerate) == (1, 2, 44100)`):
  - `test_every_voice_is_valid_audible_and_unclipped` (parametrized over profiles × kinds × variants): duration between 30 and 150 ms; `0.2 * 32767 <= peak <= 0.95 * 32767`.
  - `test_synthesis_is_deterministic`; `test_variants_differ` (`len({synthesize("clicky","letter",v) for v in range(4)}) == 4`); `test_profiles_differ` (three distinct byte strings for letter variant 0); `test_space_longer_than_letter_for_clicky`; `test_error_sound_valid`; `test_unknown_profile_kind_or_variant_raises`; `test_profile_synthesis_budget` (all 12 voices of one profile in < 1.0 s).
- [ ] **Step 2: Run** `uv run pytest -q test_keysounds.py` — Expected: FAIL.
- [ ] **Step 3: Implement** with pure-Python sample loops and a small biquad band-pass; tune constants only if a test bound fails.
- [ ] **Step 4: Run** `uv run pytest -q test_keysounds.py` — Expected: PASS.
- [ ] **Step 5: Commit** `feat: synthesize mechanical key sounds`

### Task 11: Edit classification (pure)

**Files:** Modify `core/keysounds.py`; Test: `test_keysounds.py`

**Interfaces:**
- Consumes: `TextChange` from `core/transitions.py`.
- Produces: `classify_edit(changes: Sequence[TextChange], target_text: str) -> list[str]` — kinds from `{"letter", "space", "enter", "error"}`, at most one per change.

- [ ] **Step 1: Write failing parametrized test** `test_classify_edit` (changes, target → expected): `([TextChange(0,0,"a")], "ab") → ["letter"]`; `([TextChange(1,0," ")], "a b") → ["space"]`; `([TextChange(1,0,"\n")], "a\nb") → ["enter"]`; `([TextChange(0,0,"x")], "ab") → ["error"]`; `([TextChange(0,1,"")], "ab") → ["letter"]` (backspace); `([TextChange(2,0,"z")], "ab") → []` (past end); `([TextChange(0,0,"ab")], "ab") → []` (multi-character); `([], "ab") → []`; `([TextChange(0,1,"a")], "ab") → ["letter"]` (typing over a selection).
- [ ] **Step 2: Run** `uv run pytest -q test_keysounds.py::test_classify_edit` — Expected: FAIL.
- [ ] **Step 3: Implement** `classify_edit` (a change with `removed > 0` and empty `inserted` is a backspace → `"letter"`; one inserted character at `position < len(target_text)` is compared with the expected character; anything else yields nothing).
- [ ] **Step 4: Run** the same command — Expected: PASS.
- [ ] **Step 5: Commit** `feat: classify edits into key sound kinds`

### Task 12: `KeySoundPlayer` (Qt)

**Files:** Modify `core/keysounds.py`; Test: `test_keysounds.py`

**Interfaces:**
- Consumes: `synthesize`, `synthesize_error`, `PROFILES`, `KINDS`, `VARIANTS_PER_KIND`.
- Produces: `class KeySoundPlayer(QObject)` with `__init__(parent=None)`, `configure(profile: str, volume: int) -> None`, `play(kind: str) -> None` (never raises), `enabled -> bool` (property), `shutdown() -> None` (removes the temp directory). `profile` is `"off"` or one of `PROFILES`; `volume` is 0–100. Configuring a new profile writes all WAVs to an owned `tempfile.TemporaryDirectory` and preloads one `QSoundEffect` per (kind, variant) plus one for errors (`QSoundEffect` is imported at module level as `QSoundEffect` so tests can monkeypatch it); re-configuring the same profile only calls `setVolume(volume / 100)`; `"off"` or any exception during setup disables the player silently. `play(kind)` rotates round-robin through that kind's variants and calls `.play()` on the chosen effect; no `setSource` per keystroke.

- [ ] **Step 1: Write failing tests** monkeypatching `core.keysounds.QSoundEffect` with a recording fake: `test_off_by_default` (new player, `enabled is False`, `play("letter")` doesn't raise); `test_configure_builds_effects_and_rotates_variants` (`configure("clicky", 50)` → 13 fakes, all volume `0.5`; four `play("letter")` calls play four distinct effects, the fifth replays the first); `test_volume_change_does_not_resynthesize` (monkeypatch `synthesize` with a counter); `test_configure_off_disables`; `test_setup_failure_disables_silently` (Review Focus 3: fake whose `setSource` raises → `configure` doesn't raise, `enabled is False`, `play` doesn't raise); `test_shutdown_removes_temp_dir`.
- [ ] **Step 2: Run** `uv run pytest -q test_keysounds.py` — Expected: FAIL.
- [ ] **Step 3: Implement** `KeySoundPlayer` as specified.
- [ ] **Step 4: Run** `uv run pytest -q test_keysounds.py` — Expected: PASS.
- [ ] **Step 5: Commit** `feat: add KeySoundPlayer with preloaded sound effects`

### Task 13: Settings and window hook

**Files:**
- Modify: `core/constants.py`, `ui/dialogs.py` (Display group + `_save_settings`), `ui/main_window.py` (`__init__`, `_apply_settings`, `_on_user_edit`, `closeEvent`)
- Test: `test_keysounds.py`

**Interfaces:**
- Consumes: `KeySoundPlayer`, `classify_edit`.
- Produces: constants `DEFAULT_KEY_SOUND_PROFILE = "off"`, `DEFAULT_KEY_SOUND_VOLUME = 60`, `KEY_SOUND_PROFILES = ("off", "clicky", "tactile", "linear")`; settings keys `key_sound_profile` and `key_sound_volume`; `TypingPracticeApp.key_sounds: KeySoundPlayer`; `SettingsDialog.key_sound_combo` (userData = profile id; labels "Off", "Clicky (blue)", "Tactile (brown)", "Linear (red)") and `SettingsDialog.key_sound_volume_slider` (0–100, readout `"{v}%"` via the existing `_slider_row`).

- [ ] **Step 1: Write failing tests**: `test_defaults` (`get_setting("key_sound_profile", DEFAULT_KEY_SOUND_PROFILE) == "off"`, fresh `window.key_sounds.enabled is False`); `test_settings_dialog_round_trip` (`dialog = SettingsDialog(window.progress_store, window)`; connect `settings_changed` to `window._on_settings_changed`; select Clicky, slider 40, `dialog._save_settings()` → stored values `"clicky"` and `40`, and `window.key_sounds.enabled is True` with `KeySoundPlayer.QSoundEffect` monkeypatched to a fake); window hook tests with `window.key_sounds` replaced by a recorder (`play(kind)` appends to a list): correct letter → `["letter"]`; wrong letter → `["error"]`; Backspace → `["letter"]`; Return where the target has `"\n"` → `["enter"]` and no extra sounds for the auto-filled indent; paste via `insertFromMimeData` → `[]` (Review Focus 2); strict mode on, Backspace → `[]`; the final completing keystroke still plays.
- [ ] **Step 2: Run** `uv run pytest -q test_keysounds.py` — Expected: FAIL.
- [ ] **Step 3: Implement.** In `__init__`, construct `self.key_sounds = KeySoundPlayer(self)` next to `CelebrationSoundManager.initialize(self)` (before `_apply_settings()` runs); in `_apply_settings`, call `self.key_sounds.configure(profile, volume)` from the two settings; in `_on_user_edit`, after the `_round_complete` early return and before `on_text_changed()`, `for kind in classify_edit(changes, self.current_target_text): self.key_sounds.play(kind)`; `closeEvent` calls `self.key_sounds.shutdown()`; add the two controls to the Display group after Font Size and the two keys to `_save_settings`'s `values`.
- [ ] **Step 4: Run** `uv run pytest -q` — Expected: PASS (whole suite).
- [ ] **Step 5: Commit** `feat: add key sound settings and hook them to typing`

---

### Task 14: Documentation and final verification

**Files:** Modify `README.md`, `CLAUDE.md`, `docs/CHANGELOG.md`

- [ ] **Step 1:** Add feature bullets to `README.md` (code snippets in 10 languages incl. PowerShell/Active Directory with auto-indent; mechanical key sounds, default off). In `CLAUDE.md`'s architecture list add `core/snippets.py` + `core/snippet_data/`, `core/autoindent.py`, `core/keysounds.py`, and update the test-file list. Add a `docs/CHANGELOG.md` entry following its existing format.
- [ ] **Step 2: Run** `uv run pytest -v` — Expected: all tests pass. Report the pass count truthfully.
- [ ] **Step 3: Smoke-test** headless: `QT_QPA_PLATFORM=offscreen uv run python -c "from ui.main_window import TypingPracticeApp; ..."` constructing the app, listing the sidebar sections (10 new headers after "Adaptive") and loading the last lesson without error.
- [ ] **Step 4: State the limits to the user plainly:** sounds were verified as well-formed audio and wired to settings but **not listened to**; only Python snippets were machine-syntax-checked (PowerShell/AD cmdlets were checked against Microsoft Learn; the rest were hand-reviewed); the user should run `uv run main.py` to hear the switch profiles and feel the latency, and can adjust the recipe constants in `core/keysounds.py`.
- [ ] **Step 5: Commit** `docs: document code snippets and key sounds`
