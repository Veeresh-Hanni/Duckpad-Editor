@echo off
echo ==================================================
echo Building and Installing DuckPad Editor for Windows
echo Developer: Veeresh Hanni
echo ==================================================

:: 1. Install dependencies
pip install PyQt5 pyinstaller Pillow

:: 2. Clean previous build files
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /f /q *.spec

:: 3. Build single executable with icon
pyinstaller --noconsole --onefile --icon=duckpad.png --add-data "duckpad.png;." --name="DuckPad_Editor" duckpad.py

:: 4. System Installation
set INSTALL_DIR=C:\Program Files\DuckPad
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy /Y "dist\DuckPad_Editor.exe" "%INSTALL_DIR%\DuckPad_Editor.exe"

echo ==================================================
echo Build and Installation Complete!
echo Executable Location: %INSTALL_DIR%\DuckPad_Editor.exe
echo ==================================================
pause