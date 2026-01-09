# Py-Typing-1.0

Train your typing speed and accuracy in minutes — lightweight, local, and designed for real improvement.

## Why try Py-Typing-1.0?

- See measurable improvements quickly with real-time feedback and clear metrics.
- No accounts or cloud services — everything runs locally on your machine.
- Minimal setup: small, responsive UI built with PyQt; ideal for quick practice sessions.
- Suitable for beginners learning touch typing and experienced users sharpening speed.

## Quick highlights

- Real-time accuracy and speed feedback
- Multiple exercise texts and customizable sessions
- Clean, distraction-free PyQt interface
- Tracks session results so you can monitor progress
- Virtual keyboard with finger position guidance
- Celebratory sound on perfect rounds (configurable)
- **5 beautiful themes** (Light, Dark, Solarized, Nord, Dracula)
- **Visual progress charts** with matplotlib
- **Keyboard error heatmap** showing problem keys
- Strict mode to prevent backspacing
- Free practice mode for custom text

## Quick start

### Option 1: Run from source (Recommended for development)

1. Clone the repo:
   ```bash
   git clone <repository-url>
   cd Py-Typing-1.0
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Or manually:
   ```bash
   pip install PyQt6 matplotlib
   ```
3. Run:
   ```bash
   python main.py
   ```

### Option 2: Build a standalone executable (Windows)

1. Install PyInstaller:
   ```bash
   pip install PyInstaller
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

## Project structure

```
Py-Typing-1.0/
├── README.md
├── main.py
├── ui/
│   └── (UI components)
└── resources/
    └── (Text files and assets)
```

## Contributing

Bug reports, small fixes, and usability improvements are welcome. Open an issue or submit a PR.

## License

GPL 3.0
