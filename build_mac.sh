#!/bin/bash
set -e

echo "=================================================="
echo "Building and Installing DuckPad Editor for macOS"
echo "Developer: Veeresh Hanni"
echo "=================================================="

# 1. Install dependencies
pip3 install PyQt5 pyinstaller Pillow

# 2. Convert PNG icon to macOS .icns format
python3 -c "from PIL import Image; img = Image.open('duckpad.png'); img.resize((512, 512)).save('icon.icns')"

# 3. Clean previous builds
rm -rf build dist *.spec

# 4. Build macOS .app Bundle
pyinstaller --noconsole --windowed --icon=icon.icns --name="DuckPad Editor" duckpad.py

# 5. Move to Applications folder
rm -rf "/Applications/DuckPad Editor.app"
cp -R "dist/DuckPad Editor.app" /Applications/

echo "=================================================="
echo "Build and Installation Complete!"
echo "DuckPad Editor is now available in your Applications folder."
echo "=================================================="