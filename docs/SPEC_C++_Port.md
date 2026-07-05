# Py-Typing → C++ Port Spec Sheet

A concise specification for re-implementing this PyQt6 touch-typing app in C++. Recommended GUI toolkit: **Qt 6 (C++)** — it is a near 1:1 mapping of the existing PyQt6 widgets and signal/slot wiring. Anything else (wxWidgets, Dear ImGui) is possible but will require more rework of the UI layer.

---

## 1. Tech stack

| Concern         | Python original              | C++ port (recommended)                     |
|-----------------|------------------------------|--------------------------------------------|
| GUI             | PyQt6                        | Qt 6 Widgets (QtWidgets, QtGui, QtCore)    |
| Persistence     | SQLite via `sqlite3` stdlib  | SQLite via `sqlite3.h` C API or Qt SQL     |
| Charts          | matplotlib                   | QtCharts (or QCustomPlot)                  |
| Audio           | Qt multimedia                | Qt6 `QtMultimedia` (`QSoundEffect`)        |
| JSON (settings) | `json` stdlib                | `nlohmann/json` or `QJsonDocument`         |
| Build           | `uv` / `pyproject.toml`      | CMake ≥ 3.20, C++20                        |
| Tests           | pytest                       | GoogleTest or Catch2                       |
| Random          | `random` stdlib              | `<random>` (`std::mt19937`)                |

C++20 is enough; nothing here needs C++23. Use Qt's MOC for `QObject`-derived widgets.

---

## 2. Module layout

Mirror the existing Python layout. Suggested directory tree:

```
src/
  main.cpp                       // QApplication entry, mirrors main.py
  core/
    Models.h/.cpp                // Lesson, TypingSession, SessionRecord
    Constants.h                  // Defaults + KEY_FINGER_MAP + FINGER_COLORS
    Lessons.h/.cpp               // buildLessons()
    WordGen.h/.cpp               // generateText, generateDeveloperText
    Scoring.h/.cpp               // calculateWpm, calculateAccuracy (pure)
    BestWpm.h/.cpp               // BestWpmTracker
    Persistence.h/.cpp           // ProgressStore (SQLite)
    Themes.h/.cpp                // Theme struct + registry
    Audio.h/.cpp                 // CelebrationSoundManager
    Heatmap.h/.cpp               // (optional) error-rate heatmap renderer
    Charts.h/.cpp                // (optional) progress chart renderer
  ui/
    MainWindow.h/.cpp            // TypingPracticeApp
    Widgets.h/.cpp               // KeyboardWidget, FingerLegendWidget, CelebrationOverlay
    Dialogs.h/.cpp               // StatisticsDialog, SettingsDialog
    Styles.h/.cpp                // QSS stylesheet builders
tests/
  test_scoring.cpp
  test_best_wpm.cpp
  test_enhancements.cpp
```

---

## 3. Core data types

```cpp
struct Lesson {
    std::string title;
    std::string description;
    std::vector<std::string> texts;   // "__RANDOM__" / "__DEVELOPER__" are sentinels
};

struct TypingSession {
    std::string typedText;
    std::optional<std::chrono::steady_clock::time_point> startTime;
    int errors = 0;
    bool isActive = false;
    int backspaceCount = 0;
    std::unordered_map<std::string, int> keyErrors;     // per-key error count
    std::unordered_map<std::string, int> keyAttempts;   // per-key attempt count

    void reset();
    void begin();                                       // sets startTime + isActive
    void recordKeyError(const std::string& expectedKey);
    void recordKeyAttempt(const std::string& expectedKey);
};

struct SessionRecord {
    std::string timestamp;     // ISO 8601
    int lessonIndex;
    int textIndex;
    std::string lessonName;
    int wpm;
    double accuracy;           // percent, 0–100
    int errors;
    int backspaces;
    double durationSeconds;
    int textLength;
};
```

Keep the `keyErrors`/`keyAttempts` maps keyed by the single-character string of the expected key (including `" "` for space). Mirrors the Python behavior exactly.

---

## 4. Scoring (pure, framework-free)

Defaults live in `Constants.h`:

```
DEFAULT_BACKSPACE_PENALTY            = 3
DEFAULT_BACKSPACE_ACCURACY_WEIGHT    = 0.5
DEFAULT_STRICT_MODE                  = false
DEFAULT_DARK_MODE                    = false
DEFAULT_SHOW_KEYBOARD                = true
DEFAULT_SHOW_CELEBRATION             = true
DEFAULT_FONT_SIZE                    = 16
DEFAULT_RANDOM_WORD_COUNT            = 25
DEFAULT_DEVELOPER_KEYS_LENGTH        = 24
DEFAULT_DEVELOPER_KEYS_MODE          = "symbol-heavy"
DEFAULT_THEME                        = "Light"
```

Formulas — must match the Python implementation byte-for-byte so tests are portable:

```cpp
// 5-chars-per-word convention
int calculateWpm(std::string_view typed,
                 std::optional<double> elapsedSeconds,
                 int backspaceCount,
                 double penaltyFactor) {
    if (typed.empty() || !elapsedSeconds || *elapsedSeconds <= 0.0) return 0;
    double words   = typed.size() / 5.0;
    double minutes = *elapsedSeconds / 60.0;
    int rawWpm     = minutes > 0.0 ? static_cast<int>(words / minutes) : 0;
    double penalty = backspaceCount * penaltyFactor;
    return std::max(0, static_cast<int>(rawWpm - penalty));
}

double calculateAccuracy(std::string_view typed,
                         std::string_view target,
                         int mismatchErrors,
                         int backspaceCount,
                         double backspaceWeight) {
    if (typed.empty()) return 100.0;
    int extra            = std::max<int>(0, static_cast<int>(typed.size()) - static_cast<int>(target.size()));
    double bsErrors      = backspaceCount * backspaceWeight;
    double totalErrors   = mismatchErrors + extra + bsErrors;
    double correct       = std::max(0.0, typed.size() - totalErrors);
    return (correct / typed.size()) * 100.0;
}
```

The integer truncation in WPM (`int(words/minutes)` then `int(rawWpm - penalty)`) is intentional — preserve it.

---

## 5. Persistence (SQLite)

Store at `typing_progress.sqlite3` next to the executable. One-shot migration from any legacy `typing_progress.json` (rename to `.json.migrated` after import) — implement only if you want feature parity with the Python build; otherwise skip and start fresh.

Schema (verbatim from the Python implementation):

```sql
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL                      -- JSON-encoded scalar
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL                      -- JSON-encoded scalar
);
CREATE TABLE IF NOT EXISTS best_wpm (
    lesson_key TEXT PRIMARY KEY,
    wpm INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS session_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    lesson_index INTEGER NOT NULL,
    text_index INTEGER NOT NULL,
    lesson_name TEXT NOT NULL,
    wpm INTEGER NOT NULL,
    accuracy REAL NOT NULL,
    errors INTEGER NOT NULL,
    backspaces INTEGER NOT NULL,
    duration_seconds REAL NOT NULL,
    text_length INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS random_texts (
    lesson_key TEXT PRIMARY KEY,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS developer_texts (
    lesson_key TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    mode TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS key_error_stats   (key TEXT PRIMARY KEY, count INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS key_attempt_stats (key TEXT PRIMARY KEY, count INTEGER NOT NULL);
```

Open with `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL`. Session history is capped at **100 rows** — trim oldest on insert.

`ProgressStore` public API to implement:

```cpp
class ProgressStore {
public:
    explicit ProgressStore(std::filesystem::path path);
    ~ProgressStore();

    void addSessionRecord(const SessionRecord&);
    std::vector<SessionRecord> sessionHistory() const;

    nlohmann::json getSetting(const std::string& key, nlohmann::json fallback = {}) const;
    void setSetting(const std::string& key, const nlohmann::json& value);

    std::optional<std::string> randomText(int lessonIndex) const;
    void setRandomText(int lessonIndex, std::string text);
    void clearRandomText(int lessonIndex);

    struct DeveloperText { std::string text; int tokenCount; std::string mode; };
    std::optional<DeveloperText> developerText(int lessonIndex) const;
    void setDeveloperText(int lessonIndex, DeveloperText);
    void clearDeveloperText(int lessonIndex);

    void updateKeyErrorStats(const std::unordered_map<std::string,int>&);    // additive
    void updateKeyAttemptStats(const std::unordered_map<std::string,int>&);  // additive
    std::unordered_map<std::string,int> keyErrorStats() const;
    std::unordered_map<std::string,int> keyAttemptStats() const;

    int currentLessonIndex() const;
    int currentTextIndex() const;
    void setCurrentLessonIndex(int);
    void setCurrentTextIndex(int);

    std::unordered_map<std::string,int> bestWpm() const;
    void setBestWpm(const std::unordered_map<std::string,int>&);
};
```

Writes are **granular** — each setter runs its own `INSERT OR REPLACE`, not a full-file rewrite.

---

## 6. Lessons

Hardcoded list, returned by `buildLessons()`. Order matters — `current_lesson_index` is the position in this vector.

| # | Title | Notes |
|---|-------|-------|
| 0 | Home Row - Basic | 4 fixed texts |
| 1 | Home Row - Words | 4 fixed texts |
| 2 | Top Row - Basic | 4 fixed texts |
| 3 | Top Row - Words | 4 fixed texts |
| 4 | Bottom Row - Basic | 4 fixed texts |
| 5 | All Rows Combined | 4 fixed texts |
| 6 | Common Words | 4 fixed texts |
| 7 | Random Words | single text = `"__RANDOM__"` sentinel — replace at runtime via `generateText(settings.random_word_count)` |
| 8 | Sentences - Easy | 4 fixed texts |
| 9 | Sentences - Medium | 4 fixed texts |
| 10 | Speed Challenge | 3 longer paragraphs |
| 11 | Developer Keys | single text = `"__DEVELOPER__"` sentinel — replace via `generateDeveloperText(settings.developer_keys_length, settings.developer_keys_mode)` |

There is also a **Free Practice** mode (`mode = "free"`) where the user pastes/imports custom text; not part of `buildLessons()`.

Copy the exact text content from `core/lessons.py` — strings are user-visible.

---

## 7. Word generation

Two pools, both copied verbatim from `core/wordgen.py`:

- `_COMMON_WORDS`: ~200 common English words.
- `DEVELOPER_SYMBOL_TOKENS`: `( ) [ ] { } < > = == != += -= *= /= %= -> => :: : ; , . ... / \ | & * % $ # @ ` ~`
- `DEVELOPER_CODE_TOKENS`: keywords (`if`, `else`, `for`, `while`, `def`, `class`, …)

```cpp
std::string generateText(int wordCount);                     // joins random picks with " "
std::string generateDeveloperText(int tokenCount, std::string_view mode);
//   mode == "code-snippet-heavy" → pool = CODE_TOKENS + first 8 SYMBOL_TOKENS
//   else (incl. "symbol-heavy")  → pool = SYMBOL_TOKENS
```

Use `std::mt19937` seeded from `std::random_device` once at startup.

---

## 8. UI specification

### 8.1 Main window layout

Single `QMainWindow`. Top-level horizontal split:

```
┌──────────────────────────────────────────────────────────────────────┐
│ Top bar: [Statistics] [Settings] [Theme ▾]                           │
├────────────────┬─────────────────────────────────────────────────────┤
│ Lesson list    │  Description (colored panel)                        │
│ (QListWidget)  │                                                     │
│                │  Target text (read-only QTextEdit, char-coloured)   │
│                │  Input text (QTextEdit, captures typing)            │
│                │                                                     │
│                │  Stats row: WPM | Acc | Progress | Err | BS | Best │
│                │  Progress bar                                       │
│                │                                                     │
│                │  Keyboard widget (custom QWidget, see 8.3)          │
│                │  Finger legend                                      │
└────────────────┴─────────────────────────────────────────────────────┘
```

### 8.2 Typing loop (the core interaction)

On every keystroke in the input `QTextEdit`:

1. Diff against `_previous_typed_length`. If new length < old → it was a **backspace**: increment `session.backspaceCount`. Otherwise it's a **forward keystroke**: look up the *expected* character at `session.typedText.size()` in the target, then:
   - `session.recordKeyAttempt(expected)`
   - If the typed char ≠ expected → `session.recordKeyError(expected)` and `session.errors++`
2. Update `session.typedText = inputWidget.text()`.
3. If `!session.isActive` and `typedText` is non-empty → `session.begin()` (start the timer).
4. Recompute WPM/accuracy via the pure scoring functions and update stat labels.
5. Re-render the target text with per-character coloring (correct = green, wrong = red, untyped = default).
6. Update the `KeyboardWidget` to highlight the **next expected** character.
7. If `typedText == target` (exact match) → call `onCompletion()`.

**Strict mode**: when enabled, an incorrect keystroke is rejected — `inputWidget` is reverted to the previous correct content and a beep/error highlight fires. Otherwise the user can over-type and correct.

### 8.3 KeyboardWidget

Custom `QWidget` that paints a US-ANSI keyboard via `QPainter`. Layout rows (label, width-multiplier) — copy verbatim from `ui/widgets.py`:

```
Row 0: ` 1 2 3 4 5 6 7 8 9 0 - =  ⌫(2)
Row 1: Tab(1.5) Q W E R T Y U I O P [ ] \(1.5)
Row 2: Caps(1.75) A S D F G H J K L ; ' Enter(2.25)
Row 3: Shift(2.25) Z X C V B N M , . / Shift(2.75)
Row 4: Ctrl(1.5) Win(1.25) Alt(1.25) Space(6.25) Alt(1.25) Win(1.25) Menu(1.25) Ctrl(1.5)
```

Each key is tinted by `FINGER_COLORS[KEY_FINGER_MAP[ch]]` (see Constants). The next-expected key gets a `keyboard_highlight` fill; if the user just made an error, the *correct* key flashes in `keyboard_error` for a short timer.

### 8.4 Dialogs

- **SettingsDialog**: form with backspace penalty (int), backspace accuracy weight (float), strict mode (checkbox), show keyboard (checkbox), show celebration (checkbox), font size (int), random word count (int), developer keys length (int), developer keys mode (combo: `symbol-heavy` / `code-snippet-heavy`), theme (combo: 5 themes). On save: write each via `progressStore.setSetting()`.
- **StatisticsDialog**: shows session history table (last 100), best-WPM per lesson, error heatmap, progress chart over time.

### 8.5 Themes

`Theme` is a plain struct of ~30 hex-color strings. Five built-ins (`Light`, `Dark`, `Solarized Dark`, `Nord`, `Dracula`) — values copied from `core/themes.py`. Apply by composing a QSS string and calling `mainWindow->setStyleSheet(qss)` plus propagating the struct to child widgets that paint themselves (KeyboardWidget, charts).

### 8.6 Completion behavior

On `onCompletion`:
1. Compute final WPM, accuracy, duration.
2. Build a `SessionRecord` (timestamp = ISO 8601 now) and call `progressStore.addSessionRecord(...)`.
3. Call `progressStore.updateKeyErrorStats(session.keyErrors)` and `updateKeyAttemptStats(session.keyAttempts)` (both additive).
4. Update `BestWpmTracker` keyed by `"{lessonIndex}:{textIndex}"`; persist if it changed.
5. If `settings.show_celebration` → fire celebration overlay + sound.
6. Advance `current_text_index` (and `current_lesson_index` if it wraps). For lessons whose only text is `__RANDOM__` / `__DEVELOPER__`, regenerate and persist a new text via `setRandomText` / `setDeveloperText`.

---

## 9. Build (CMake outline)

```cmake
cmake_minimum_required(VERSION 3.20)
project(PyTypingCpp CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets Multimedia Charts Sql)
find_package(SQLite3 REQUIRED)
find_package(nlohmann_json REQUIRED)   # used by ProgressStore::getSetting/setSetting

add_executable(typing-practice
    src/main.cpp
    src/core/Models.cpp src/core/Lessons.cpp src/core/WordGen.cpp
    src/core/Scoring.cpp src/core/BestWpm.cpp src/core/Persistence.cpp
    src/core/Themes.cpp src/core/Audio.cpp
    src/ui/MainWindow.cpp src/ui/Widgets.cpp src/ui/Dialogs.cpp src/ui/Styles.cpp
)
target_link_libraries(typing-practice PRIVATE
    Qt6::Widgets Qt6::Multimedia Qt6::Charts Qt6::Sql SQLite::SQLite3
    nlohmann_json::nlohmann_json
)
```

Windows packaging: `windeployqt` against the built `.exe`, then bundle with NSIS or InnoSetup.

---

## 10. Testing

Port the three Python test files; behavior must match:

- `test_scoring.cpp` — boundary cases for `calculateWpm` / `calculateAccuracy`: empty input, zero elapsed, integer-truncation edge cases, backspace penalties, over-typing past the target.
- `test_best_wpm.cpp` — `BestWpmTracker::update` only overwrites when strictly greater; malformed map entries are ignored.
- `test_enhancements.cpp` — settings round-trip through `ProgressStore`, key-stat accumulation is additive, session history caps at 100.

---

## 11. Out-of-scope / optional

The Python build has matplotlib-based heatmap and progress chart rendering. In C++ either:
- Use QtCharts (recommended — cleanest Qt-native option), or
- Skip charts entirely in v1 and ship without the StatisticsDialog visualizations.

Audio (`CelebrationSoundManager`) is a small nicety — `QSoundEffect` with a bundled `.wav` is enough. Skip if you want a smaller binary.

---

## 12. Acceptance checklist

A faithful port is complete when:

- [ ] All 12 lessons appear in order with correct titles/descriptions/texts.
- [ ] Typing updates WPM/accuracy live; numbers match the Python build for the same input.
- [ ] Backspace count and per-key error/attempt maps update on every keystroke.
- [ ] Strict mode rejects wrong keys; non-strict allows over-type and correction.
- [ ] Completion writes a `SessionRecord`, updates best-WPM, and advances to the next text.
- [ ] Settings persist across restarts via the SQLite tables.
- [ ] All 5 themes render correctly (main window + keyboard + dialogs).
- [ ] Random/Developer lessons regenerate their text on each completion and persist the new value.
- [ ] Session history is capped at 100 rows.
