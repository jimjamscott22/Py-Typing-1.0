# Py-Typing-1.0

Train your typing speed and accuracy in minutes — lightweight, local, and designed for real improvement, including focused drills like Developer Keys.

## Why try Py-Typing-1.0?

- See measurable improvements quickly with real-time feedback and clear metrics.
- No accounts or cloud services — everything runs locally on your machine.
- Minimal setup: small, responsive UI built with PyQt; ideal for quick practice sessions.
- Suitable for beginners learning touch typing and experienced users sharpening speed.

## Quick highlights

- Real-time accuracy and speed feedback
- Multiple exercise texts and customizable sessions
- Clean, distraction-free PyQt interface
- Tracks session results so you can monitor progress (stored locally in a SQLite database)
- Virtual keyboard with finger position guidance
- Celebratory sound on perfect rounds (configurable)
- **5 beautiful themes** (Light, Dark, Solarized, Nord, Dracula)
- **Visual progress charts** with matplotlib
- **Keyboard error heatmap** showing problem keys
- **Developer Keys** practice mode for symbols and code-friendly drills
- Strict mode to prevent backspacing
- Free practice mode for custom text, with import from a `.txt` file

## Quick start

### Option 1: Run from source (Recommended for development)

1. Clone the repo:
   ```bash
   git clone <repository-url>
   cd Py-Typing-1.0
   ```
2. Install dependencies (using uv):
   ```bash
   uv sync
   ```
3. Run:
   ```bash
   uv run main.py
   ```

### Option 2: Build a standalone executable (Windows)

1. Install PyInstaller:
   ```bash
   uv add --dev pyinstaller
   ```
2. Run the build script:
   ```bash
   build_exe.bat
   ```
3. The executable will be created at `dist/Typing Practice.exe`

You can now distribute or run the standalone executable without needing Python installed.

## How to get the most out of it

- Start with short 1–3 minute sessions and focus on accuracy, then increase speed.
- Use a consistent practice schedule (e.g., 10–15 minutes daily).
- Try different texts to work on varied vocabulary and punctuation.

## Running the tests

```bash
uv run pytest -v
```

The suite covers scoring (`test_scoring.py`), per-lesson best-WPM tracking (`test_best_wpm.py`), and end-to-end persistence/UI smoke tests (`test_enhancements.py`).

## Where your progress lives

Progress, settings, session history, and per-key statistics are persisted to a local SQLite database (`typing_progress.sqlite3`) in the working directory. No network calls, no telemetry.

If you previously used a version that wrote `typing_progress.json`, it will be imported on first launch and the original file is renamed to `typing_progress.json.migrated` as a backup — safe to delete once you've confirmed your stats carried over.

## Project structure

```
Py-Typing-1.0/
├── main.py                # QApplication entry point
├── core/                  # Lessons, models, persistence, scoring, themes, heatmap, charts
├── ui/                    # PyQt6 windows, dialogs, widgets, styles
├── icons/                 # App icons / assets
├── docs/                  # Design notes and review suggestions
├── test_*.py              # Pytest suites
├── build_exe.bat          # Windows PyInstaller build script
└── pyproject.toml         # uv-managed dependencies
```

## Contributing

Bug reports, small fixes, and usability improvements are welcome. Open an issue or submit a PR.

## License

GPL 3.0
