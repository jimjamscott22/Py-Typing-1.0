# Py-Typing — Visual Overview

> Diagrams derived from [[SPEC]], [[CHANGELOG]], and [[ENHANCEMENTS_ROADMAP]].
> Treat [[MASTER]] as the authoritative source; treat this file as the visual companion.

---

## 1. Module Architecture

How the Python (and C++ port) modules relate to each other. Arrows indicate a dependency or call direction.

```mermaid
graph LR
    subgraph Entry
        M["main.py"]
    end

    subgraph UI["ui/"]
        MW["main_window.py\n(~1014 lines — thin Qt glue)"]
        WD["widgets.py\nKeyboardWidget\nFingerLegendWidget\nCelebrationOverlay"]
        DL["dialogs.py\nStatisticsDialog\nSettingsDialog"]
        ST["styles.py\nQSS builders"]
        FT["formats.py\nQTextCharFormat presets"]
    end

    subgraph Core["core/"]
        SC["scoring.py\ncalculate_wpm\ncalculate_accuracy"]
        BW["best_wpm.py\nBestWpmTracker"]
        PS["persistence.py\nProgressStore\n(SQLite — 9 tables)"]
        MD["models.py\nTypingSession\nSessionRecord\nLesson"]
        LS["lessons.py\nbuildLessons()"]
        WG["wordgen.py\ngenerateText\ngenerateDeveloperText"]
        TH["themes.py\n5 built-in themes\n30+ color tokens each"]
        CH["charts.py\nmatplotlib → QPixmap"]
        HM["heatmap.py\nkeyboard overlay renderer"]
        AU["audio.py\nCelebrationSoundManager"]
        CN["constants.py\nKEY_FINGER_MAP\nFINGER_COLORS\nDefaults"]
    end

    M --> MW
    MW --> WD
    MW --> DL
    MW --> ST
    MW --> FT
    MW --> SC
    MW --> BW
    MW --> PS
    MW --> TH
    MW --> AU
    MW --> LS
    MW --> WG
    DL --> CH
    DL --> HM
    DL --> PS
    SC --> MD
    BW --> PS
    PS --> MD
    WD --> TH
    CH --> TH
    HM --> CN
    WD --> CN
```

---

## 2. Typing Session State Machine

The core keystroke loop from §8.2 of [[SPEC]]. Every key press in the input `QTextEdit` flows through this graph.

```mermaid
flowchart TD
    KS(["⌨ Keystroke received"])

    KS --> DL{New length\n< old length?}
    DL -->|Yes — backspace| BS["session.backspaceCount++"]
    DL -->|No — forward key| RA["session.recordKeyAttempt(expected)"]

    RA --> CM{Typed char\n== expected?}
    CM -->|No — mismatch| KE["session.recordKeyError(expected)\nsession.errors++"]
    CM -->|Yes| UT

    KE --> UT["Update session.typedText"]
    BS --> UT

    UT --> ACT{Session\nactive?}
    ACT -->|No & typedText non-empty| SB["session.begin()\n(start timer)"]
    ACT -->|Yes| WPM
    SB --> WPM["Recompute WPM + accuracy\nvia core/scoring.py"]

    WPM --> RT["Re-render target text\n🟢 correct  🔴 wrong  ⬜ untyped"]
    RT --> KH["Update KeyboardWidget\nhighlight next expected key"]

    KH --> SM{Strict mode\nenabled?}
    SM -->|Yes + error| RV["Revert inputWidget\nto last correct state\n+ error flash"]
    SM -->|No or correct| CP

    RV --> KS
    CP{typedText\n== target?}
    CP -->|No| KS
    CP -->|Yes| OC["onCompletion() ➜ see diagram 3"]
```

---

## 3. Session Completion & Persistence Flow

What happens the moment the user finishes typing the target text.

```mermaid
flowchart TD
    OC(["onCompletion()"])

    OC --> FW["Compute final WPM\naccuracy, duration"]
    FW --> SR["Build SessionRecord\n(ISO 8601 timestamp)"]

    SR --> SH[("session_history\ntable — cap 100 rows")]
    SR --> KES[("key_error_stats\nglobal, cumulative")]
    SR --> KAS[("key_attempt_stats\nglobal, cumulative")]
    SR --> SKE[("session_key_errors\nper-session — Tier 2")]

    SR --> UB["BestWpmTracker.update()\nkey = lessonIndex:textIndex"]
    UB --> BWP[("best_wpm table\n(only if new WPM > stored)")]

    SR --> CEL{show_celebration\nsetting?}
    CEL -->|Yes| AO["Celebration overlay\n+ QSoundEffect .wav"]
    CEL -->|No| NX

    AO --> NX["Advance text index\n(wrap → next lesson)"]
    NX --> SEN{Sentinel\ntext?}
    SEN -->|__RANDOM__| RG["generateText(word_count)\npersist via setRandomText()"]
    SEN -->|__DEVELOPER__| DG["generateDeveloperText()\npersist via setDeveloperText()"]
    SEN -->|Fixed text| DONE(["Ready for next round"])
    RG --> DONE
    DG --> DONE
```

---

## 4. SQLite Schema Map

All 9 tables in `typing_progress.sqlite3` and what each stores.

```mermaid
graph TD
    subgraph DB["typing_progress.sqlite3\n(WAL mode, NORMAL sync)"]
        KV["kv\nkey → JSON scalar\n(misc global state)"]
        SE["settings\nkey → JSON scalar\n(all user settings)"]
        BW["best_wpm\nlesson_key → INTEGER wpm"]
        SH["session_history\n100-row cap\ntimestamp, lesson, wpm, accuracy…"]
        RT["random_texts\nlesson_key → TEXT"]
        DT["developer_texts\nlesson_key → TEXT + token_count + mode"]
        KES["key_error_stats\nkey → INTEGER count\n(global, cumulative)"]
        KAS["key_attempt_stats\nkey → INTEGER count\n(global, cumulative)"]
        SKE["session_key_errors\nsession_id + key → error_count\n(per-session — Tier 2)"]
    end

    SH -->|session_id FK| SKE
```

---

## 5. Feature Roadmap

```mermaid
flowchart LR
    subgraph V13["v1.3 ✅ Shipped"]
        A1["scoring.py extracted\n14 tests"]
        A2["best_wpm.py extracted\n10 tests"]
        A3["SQLite migration\n(JSON → .migrated)"]
        A4["main_window.py split\nstyles · formats"]
    end

    subgraph V11["v1.1 ✅ Shipped"]
        B1["Theme system\n5 themes · 30+ tokens"]
        B2["Matplotlib charts\nWPM + accuracy"]
        B3["Error heatmap\n(global)"]
    end

    subgraph V12["v1.2 ✅ Shipped"]
        C1["session_key_errors\ntable added"]
        C2["Per-lesson\nheatmap filter"]
        C3["Error Trends tab\n(time-series)"]
    end

    subgraph T1["Tier 1 🔜 Next\n(no schema change)"]
        D1["Export charts\nas PNG"]
        D2["Pie + scatter\nchart types"]
        D3["Practice\nrecommendations"]
    end

    subgraph T3["Tier 3 📋 Later"]
        E1["Custom\ntheme creator"]
    end

    subgraph IDEAS["💡 Ideas (unscoped)"]
        F1["Adaptive drills"]
        F2["Bigram/trigram\nanalysis"]
        F3["Goal + streak\ntracking"]
        F4["Lesson gating\n(WPM unlock)"]
        F5["Import file/URL"]
    end

    V13 --> V12
    V11 --> V12
    V12 --> T1
    T1 --> T3
    T3 -.-> IDEAS
```

---

## 6. Theme Architecture

How a theme propagates from definition to every painted surface.

```mermaid
flowchart LR
    TH["core/themes.py\nTHEMES dict\n5 entries × 30+ color tokens"]

    TH --> MW["main_window.py\nbuild_main_stylesheet(theme)\n→ setStyleSheet(qss)"]
    TH --> WD["widgets.py\nKeyboardWidget.paintEvent()\nuses theme.keyboard_*"]
    TH --> CH["charts.py\ncreate_*_chart(data, theme)\nmatplotlib figure colors"]
    TH --> DL["dialogs.py\nStatisticsDialog\nSettingsDialog"]

    SE[("settings table\nstores theme *name* only")] -->|load at startup| TH
    MW -->|setSetting on save| SE
```

---

*All diagrams reflect the state documented in [[CHANGELOG]] and [[SPEC]]. Update this file whenever a new version ships or the module structure changes.*
