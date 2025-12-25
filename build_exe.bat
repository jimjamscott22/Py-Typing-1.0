@echo off
REM Build the Typing Practice application into a standalone executable
REM Requirements: PyInstaller must be installed (pip install PyInstaller)

echo Building Typing Practice executable...
echo.

python -m PyInstaller typing_practice.spec --distpath ./dist --workpath ./build -y

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build successful!
    echo Executable location: .\dist\Typing Practice.exe
    echo.
    pause
) else (
    echo.
    echo Build failed! Check the error messages above.
    echo.
    pause
)

