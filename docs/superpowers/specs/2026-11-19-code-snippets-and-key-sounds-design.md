# Developer Code Snippets and Mechanical Key Sounds Design

**Status:** Draft — awaiting approval

**Date:** 2026-11-19

**Source:** Request to make Py-Typing-1.0 "more like" the user's other app,
[TypeForge-R](https://github.com/jimjamscott22/TypeForge-R) (a React/TypeScript
PWA). Of everything TypeForge-R does that this app doesn't, the user chose the
developer-focused code snippets and the mechanical key sounds.

**Scope:** Python/PyQt application only. No new dependencies. No changes to the
C++ port spec.

## 1. Summary and why

The user wants practice that feels like typing real code, and typing that feels
like a keyboard. TypeForge-R offers both: language-specific snippets in three
difficulty tiers, and synthesized mechanical-switch sounds (clicky / tactile /
linear). This app already has Bash, Developer Keys and symbol drills, but no
real code to type and no keystroke audio (only a celebration melody on a
perfect round).

This design adds:

1. **Code snippets** — ~90 original snippets across 10 languages × 3 tiers,
   delivered as ordinary lessons in the existing sidebar.
2. **Key sounds** — synthesized per-keystroke sounds in three switch profiles
   plus an error thunk, with a volume setting, default off.

PowerShell and Active Directory are first-class language sections, as
sysadmin-style scripting is a requested practice area, even though TypeForge-R
has nothing like them.

## 2. Goals, non-goals, anti-goals

**Goals**

- Typing real, correct, idiomatic code in Junior / Mid / Senior tiers for
  TypeScript, JavaScript, Python, Rust, Go, SQL, HTML/CSS, C++, PowerShell and
  Active Directory (PowerShell ActiveDirectory-module cmdlets).
- Snippets participate in everything lessons already do: per-lesson best WPM,
  session history, weak-key stats, transitions, goals, achievements.
- Keystroke sounds that keep up with fast typing and never get in its way.

**Non-goals**

- TypeForge-R-style language/difficulty dropdowns or a separate "Developer
  Mode" screen (rejected approach B below).
- Recorded audio samples, or any audio library (rejected approaches B/C).
- Reordering the existing sidebar sections, or migrating saved progress.
- Syntax highlighting of the target text.
- Caret styles, achievement tiers, the WPM-over-time graph, JSON export — the
  other TypeForge-R differences — are out of scope for this change.

**Anti-goals** (would make this a failure even if it technically works)

- Shifting any existing lesson's index. Progress is keyed by `str(lesson_index)`
  (best WPM) and by `lesson_index`/`text_index` (history, key stats, completed
  texts); a shifted index silently corrupts a user's saved data.
- Auto-filled indentation inflating WPM, accuracy or key statistics.
- Any sound-related failure (no audio device, bad driver) interrupting typing
  or raising on the keystroke path.
- A sound that is on by default.

## 3. Current state (verified in code)

- `Lesson(title, description, texts, category)` in `core/models.py`;
  `build_lessons()` in `core/lessons.py` returns an ordered list. The sidebar
  (`_populate_lesson_list`, `ui/main_window.py`) inserts a collapsible header
  whenever `lesson.category` changes between adjacent lessons and strips a
  `"{category} - "` prefix from labels. The last lesson is "Weak Key Practice"
  (`texts=["__WEAK_KEYS__"]`, category "Adaptive").
- Existing lesson texts contain no newlines. The target renderer already maps
  `"\n"` to `<br />` and `" "` to `&nbsp;` (`_format_char`), so multi-line text
  displays, but the typing flow has never been exercised with it.
- `TypingInput.keyPressEvent` wraps each edit and emits `user_edited(changes)`
  where each `TextChange` has `position`, `removed`, `inserted`.
  `TypingApp._on_user_edit` calls `controller.record_edit(changes, target)`
  then `on_text_changed()`. Paste/drop emits `answer_imported` instead.
- `eventFilter` makes Space/Enter jump to the next challenge only when
  `_round_complete`; Space at the very end of the target advances a finished
  line.
- `next_text()` returns early for the generated "weak" lesson (it just reloads
  it), so progression via Next/Space can never move past "Weak Key Practice";
  the "completed all lessons" message is unreachable today. Lessons after it
  are reachable only by clicking them in the sidebar.
- The typing input lives in `terminal_frame`, capped at `setMaximumHeight(150)`
  (about 3–4 lines at the default 16 pt Courier New); the target is a
  word-wrapped `QLabel` with no height cap.
- Completion is `typed_text == target_text`. `calculate_wpm` and
  `calculate_accuracy` (`core/scoring.py`) use `len(typed)`, and
  `SessionRecord.text_length`/`errors` plus the achievements' minimum-length
  checks (25 and 50 characters) are derived from the same values.
- `core/achievements.py` builds a "curriculum" target from
  `sum(lesson_text_counts)`, with `lesson_text_counts` supplied by
  `main_window.py` as `[len(l.texts) for l in self.lessons]`. Naively adding ~90
  texts would raise that target for everyone.
- `core/audio.py` plays a celebration WAV via `winsound` (Windows) or
  `QMediaPlayer`. Both have start-up latency and cut off the previous sound,
  so neither can serve keystrokes.
- Settings live in the SQLite `settings` table via `ProgressStore.get_setting`
  / `set_setting`; defaults in `core/constants.py`; `SettingsDialog._save_settings`
  collects a `values` dict and emits `settings_changed(changed_keys)`.

## 4. Approaches considered

### Snippets

- **A. Snippets become lessons (chosen).** A data module of snippets;
  `build_lessons()` appends generated lessons. Reuses sidebar, stats and
  achievements unchanged; matches how Bash/Developer Keys lessons were added.
  Trade-off: no language/difficulty dropdowns; sidebar grows (collapsible).
- **B. Dedicated Developer Mode panel.** Closer to TypeForge-R's look but needs
  a second selection path through the 1,900-line `main_window.py` and session
  records currently keyed by lesson/text index. Rejected: cost and risk
  outweigh the visual match.

### Key sounds

- **A. Synthesize in Python, play from a `QSoundEffect` pool (chosen).** Port
  TypeForge-R's recipe (pitch-swept oscillators plus a filtered-noise burst)
  with stdlib `wave`/`math`, as `audio.py` already does for melodies. No
  dependencies, no PyInstaller change. Trade-off: synthesized, not recorded.
- **B. Ship recorded samples.** More realistic, but licensed recordings cannot
  be sourced here and the PyInstaller spec changes. Rejected.
- **C. Add `pygame`/`sounddevice`.** Heavy dependency for what A does. Rejected.

The user picked snippets A and sounds A.

## 5. Design: code snippets

### 5.1 Data

New `core/snippets.py`:

```python
@dataclass(frozen=True)
class Snippet:
    language: str      # e.g. "Python", "Active Directory"
    difficulty: str    # "Junior" | "Mid" | "Senior"
    title: str
    text: str          # multi-line, LF newlines, spaces only
```

`SNIPPETS: tuple[Snippet, ...]` plus `build_snippet_lessons() -> list[Lesson]`.
One `Lesson` per (language, difficulty) with at least one snippet:
`title="Python - Junior"`, `category="Python"`, `texts=[s.text, ...]`,
`description` summarising the tier. The sidebar's existing prefix stripping then
labels the rows "Junior / Mid / Senior" under a collapsible "Python" header.

Tier meaning: **Junior** — clean, everyday constructs. **Mid** — operators,
destructuring/pipelines, error handling. **Senior** — generics/lifetimes,
regex, nested delimiters, concurrency, bulk operations.

### 5.2 Content rules

- 10 sections: TypeScript, JavaScript, Python, Rust, Go, SQL, HTML/CSS, C++,
  PowerShell, Active Directory. Target 3 snippets per tier (~90 total).
- Written fresh; ideas may follow TypeForge-R, text is not copied.
- Each snippet is 3–12 lines, at most ~450 characters, and no line longer than
  72 characters, so a round stays a round and lines do not wrap at the default
  font size.
- Typeable on a US keyboard: ASCII only, `\n` newlines, **spaces for
  indentation, no tabs** (Go snippets also use spaces despite `gofmt`; noted
  in the lesson description), no trailing whitespace, no final newline.
- Code must be real and correct. For PowerShell and Active Directory, only
  genuine cmdlets and parameters (e.g. `Get-ADUser -Filter`, `Search-ADAccount
  -LockedOut`, `Unlock-ADAccount`, `Add-ADGroupMember`, `Get-ADReplicationFailure`,
  `Get-GPO`, `Invoke-Command`); cmdlet and parameter names are to be checked
  against Microsoft Learn before merge (the Microsoft Learn MCP search/fetch
  tools are available in this environment for exactly that).
- Correctness checks for the other languages: Python snippets must pass
  `ast.parse` (enforced by a test); the rest are hand-reviewed, and the plan
  should say so plainly rather than imply they were compiled.
- Active Directory tiers: Junior = lookups and membership; Mid = filters,
  `Select-Object`, `Export-Csv`, `New-ADUser` with splatting; Senior = bulk
  operations with `try/catch`, remoting, replication and GPO checks.

### 5.3 Lesson ordering and index stability

`build_lessons()` returns the existing list unchanged followed by
`build_snippet_lessons()`. Snippet lessons are **appended after "Weak Key
Practice"** so every existing index is unchanged. Consequence: the "Adaptive"
section sits above the code sections in the sidebar.

### 5.4 Curriculum achievement

The curriculum target must not grow. `main_window.py` passes
`lesson_text_counts` with `0` for snippet lessons (a text index is never `< 0`,
so those lessons contribute nothing to the numerator or denominator). Snippet
lessons are optional specialisations, not part of "finish the curriculum".

### 5.4a Navigation

`next_text()` is **not** changed for the core curriculum: "Weak Key Practice"
stays a terminal lesson, so Next/Space never enters the snippet sections;
users pick a language from the sidebar. Within the snippets Next works as for
any lesson (texts in a tier, then the next tier, then the next language). The
"completed all lessons" message is only reachable at the very last snippet
lesson, so it is reworded for that case ("You've finished all the code
snippets!").

### 5.5 Indentation: auto-fill after Enter

Typing 4–8 spaces at the start of every line would make the feature miserable,
so in lesson mode, when the user types a newline that matches the target and the
typed text so far matches the target prefix exactly, the leading whitespace of
the next target line is inserted automatically. Constraints:

- Auto-filled characters are **not** attempts, errors, transition samples or
  feedback events, and produce no sound.
- They are excluded from WPM's typed-character count and from accuracy, so
  speed and accuracy reflect keystrokes actually made. Concretely: the session
  tracks an auto-filled character count, and every statistic uses
  "keystroke characters" (`len(typed) - auto_filled`) — WPM, the accuracy
  numerator and denominator, `SessionRecord.text_length`, and the achievements'
  minimum-length checks. Completion still compares the full `typed_text` with
  the target. Auto-filled characters are always correct, so they never add
  mismatches.
- Programmatic insertion never triggers `answer_imported` / paste detection.
- Not applied in Free Practice, nor when the typed text has already diverged
  from the target.
- Backspacing over auto-filled indentation must behave sanely (builder
  decides whether it counts toward the backspace penalty).

**Build order.** Auto-fill is built and proven first (including its tests),
before any snippet content is written, because the fallback changes how every
snippet must be authored. Fallback if it cannot be kept clean of statistics
within a reasonable change: **stop and ask the user** (do not silently choose),
with the option of dropping auto-fill and capping indentation at two levels of
two spaces.

### 5.6 Typing-area layout

`terminal_frame` is capped at 150 px, which fits only 3–4 lines. For lessons
whose target has multiple lines, the frame's height grows to fit the target's
line count (minimum 150 px as today, capped at about 12 lines' worth), and
returns to 150 px for single-line targets. Keyboard and controls must stay on
screen at the default window size. Lines longer than the widget wrap in both
the target and the input; the 72-character content cap keeps that from
happening at the default font size.

## 6. Design: key sounds

### 6.1 Synthesis

New `core/keysounds.py`, pure (no Qt) for the synthesis half:

- 44.1 kHz, 16-bit mono WAV via stdlib `wave`; pure-Python sample math (the
  noise bandpass is a small biquad). No numpy.
- Three profiles ported from TypeForge-R's recipe, each with a few pitch
  variants (target 4) per **kind**: `letter`, `space`, `enter`:
  - **Clicky** — short high-frequency triangle sweep (the "snap"), sine body
    sweeping down, bandpassed noise burst.
  - **Tactile** — single triangle sweep, short noise burst, softer.
  - **Linear** — low sine sweep, quiet low noise; deep "thock".
- An **error** sound shared by all profiles: low sawtooth through a low-pass,
  ~90 ms.
- Peak amplitude < 1.0 (no clipping); synthesis seeded per variant so output
  is deterministic.
- Generated lazily per profile (when first selected or on startup if already
  selected), cached in a temp directory following `audio.py`'s pattern. Budget:
  under ~0.5 s per profile; builder measures.

### 6.2 Playback

`KeySoundPlayer` (Qt) holds a pool of `QSoundEffect` instances so that
overlapping keystrokes (10+ per second) neither drop nor cut each other off.
No `setSource` per keystroke. Volume via `QSoundEffect.setVolume`. Any
initialisation or playback failure disables sounds silently for the session;
nothing raises on the typing path.

### 6.3 When sounds fire

Hooked in `TypingApp._on_user_edit`, from the `changes` list, via a pure
function that classifies an edit into a list of sound kinds (so it is testable
without Qt):

- inserted char equal to the expected target char → click for that kind
  (space / newline / letter);
- inserted char differing from the expected one → error sound;
- backspace (removal with nothing inserted) → letter click;
- nothing for: round complete, paste/drop, auto-filled indentation, strict-mode
  blocked backspace, characters past the end of the target.

### 6.4 Settings

Two new settings in `core/constants.py` with defaults, shown in the Display
group of `SettingsDialog` and added to `_save_settings`:

- `key_sound_profile`: `"off"` (default) | `"clicky"` | `"tactile"` | `"linear"`
- `key_sound_volume`: int 0–100, default 60 (reuse the existing `_slider_row`
  helper).

The window reconfigures the player when these appear in `changed_keys`.

## 7. Testing and verification

New flat test files, same style as the existing ones:

- `test_snippets.py` — every snippet has a known language/difficulty and
  non-empty text; ASCII, no tabs, no trailing whitespace, no CRLF, length and
  line bounds; no duplicate titles/texts; `build_lessons()` first N lessons
  identical to today's, "Weak Key Practice" index unchanged, snippet lessons
  appended after it; sidebar labels strip correctly; curriculum target
  unchanged; Python snippets pass `ast.parse`; no snippet line over 72
  characters; auto-indent keeps attempts/errors/transitions/WPM/accuracy/
  `text_length` clean; the typing frame grows and shrinks with the target.
- `test_keysounds.py` — synthesis yields valid WAV, expected duration,
  non-silent, non-clipping, deterministic; edit classification table;
  settings defaults and round-trip; window test with a stub player verifying
  calls on correct/incorrect/backspace/paste/strict-mode.
- Qt is exercised headlessly (`QT_QPA_PLATFORM=offscreen`) with the player
  stubbed; real `QSoundEffect` output is not asserted.

Hard limit of cloud verification: the container cannot play or hear audio and
no user machine is attached. Verified here: tests pass, WAVs are well-formed,
wiring and settings work. **Not verified here:** how the sounds actually sound
and whether latency feels right on the user's OS. The user does that by
running `uv run main.py` and tuning the profile parameters if needed.

## 8. Left to the builder

- Exact synthesis constants, variant counts and pool sizing.
- Whether auto-fill is implemented in `TypingInput` or the window.
- Number of snippets per tier above/below 3 where content is thin.
- Wording of lesson descriptions and the end-of-curriculum message handling.
- Updating `README.md`, `CLAUDE.md` (architecture list) and `docs/CHANGELOG.md`.

## 9. Calls made without asking (please check)

1. Snippet lessons appended after "Weak Key Practice" (index safety), putting
   "Adaptive" above the code sections.
2. Snippet lessons excluded from the curriculum achievement target.
3. Auto-fill indentation after Enter, excluded from WPM/accuracy/key stats,
   with a stated fallback.
4. Spaces only in all snippets, including Go.
5. Sounds default Off; volume default 60.
6. Backspace plays a letter click; wrong key plays one shared error sound.
7. Audio failures disable sound silently rather than warn.
8. Snippet text written fresh rather than copied from TypeForge-R.
9. Next/Space does not flow past "Weak Key Practice" into the snippets (as
   today); snippets are entered from the sidebar. End-of-list message reworded.
10. Typing frame grows (up to ~12 lines) for multi-line targets; snippet lines
    capped at 72 characters.
11. Statistics use keystroke characters (auto-fill excluded), including the
    recorded `text_length` and achievement minimum-length checks.
12. Auto-fill is built and proven before any snippet content; if it cannot be
    made clean, the builder stops and asks you.
13. Only Python snippets get an automated syntax check; the rest are hand
    reviewed, PowerShell/AD cmdlets checked against Microsoft Learn.
