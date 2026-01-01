# Building Typing Practice as a Standalone Executable

## Overview

This guide explains how to build the Typing Practice application into a standalone `.exe` file that can be distributed and run on Windows without requiring Python to be installed.

## Prerequisites

- Python 3.8 or higher
- PyInstaller 6.0 or higher
- All dependencies installed (see main README)

## Quick Build

The easiest way to build the executable is to use the provided build script:

```bash
build_exe.bat
```

This will create the executable at `dist/Typing Practice.exe`

## Manual Build

If you prefer to build manually, run:

```bash
python -m PyInstaller typing_practice.spec --distpath ./dist --workpath ./build -y
```

## Build Output

After a successful build, you'll find:

- **`dist/Typing Practice.exe`** - Standalone executable (~45 MB)
- **`dist/Typing Practice/`** - Directory containing the application and all dependencies

## Distribution

To distribute the application:

### Option 1: Single Executable (Simpler)
Copy the `dist/Typing Practice.exe` file to your target system and run it directly.

### Option 2: Full Directory (Faster startup)
Copy the entire `dist/Typing Practice/` directory to your target system and run `Typing Practice.exe` from within.

The full directory approach is slightly faster on first launch because all dependencies are already extracted.

## Customization

To customize the build (e.g., change icon, add more data files), edit `typing_practice.spec`:

```python
# Change the executable name
exe = EXE(
    ...,
    name='Your App Name',  # Change here
    icon='path/to/your/icon.ico',  # Change here
    ...
)
```

Then rebuild using the same commands above.

## Troubleshooting

### Build fails with "Module not found"
- Install the missing module: `pip install module_name`
- Add it to `hiddenimports` in the spec file

### Executable is very large
- This is normal for PyQt6 + dependencies (~45-50 MB)
- The size includes Python runtime, Qt libraries, and multimedia support

### Application won't start
- Check that all dependencies are properly installed
- Try running from the full `dist/Typing Practice/` directory instead of the single exe

## Files to Know

- **`typing_practice.spec`** - PyInstaller configuration file
- **`build_exe.bat`** - Build script for Windows
- **`dist/`** - Output directory with the built executable
- **`build/`** - Temporary build artifacts (safe to delete)

## Cleanup

After a successful build, you can safely delete:
- `build/` directory
- `*.pyc` files
- `__pycache__/` directories

## Further Reading

- [PyInstaller Documentation](https://pyinstaller.org/)
- [PyQt6 with PyInstaller](https://doc.qt.io/qtforpython/)



