#!/bin/bash
set -e

echo "=================================================="
echo "Building and Installing DuckPad Editor for Linux"
echo "Developer: Veeresh Hanni"
echo "=================================================="

# 1. Install dependencies
pip install PyQt5 pyinstaller Pillow

# 2. Create a bounded build icon without modifying the source image
python3 -c "from PIL import Image; img = Image.open('duckpad.png'); img.thumbnail((256, 256)); img.save('duckpad-build.png')"

# 3. Clean temporary build cache
rm -rf build dist *.spec /tmp/duckpad-pkg

# 4. Compile binary with PyInstaller
pyinstaller --noconsole --onefile --icon=duckpad-build.png --add-data "duckpad.png:." --name="duckpad" duckpad.py

# 5. System-wide installation
sudo mv dist/duckpad /usr/local/bin/
sudo chmod +x /usr/local/bin/duckpad

sudo mkdir -p /usr/share/icons/duckpad
sudo cp duckpad.png /usr/share/icons/duckpad/icon.png

mkdir -p ~/.local/share/applications
cat << 'EOF' > ~/.local/share/applications/duckpad.desktop
[Desktop Entry]
Name=DuckPad Editor
Comment=Text Editor by Veeresh Hanni
Exec=/usr/local/bin/duckpad
Icon=/usr/share/icons/duckpad/icon.png
Terminal=false
Type=Application
Categories=Development;TextEditor;
EOF

chmod +x ~/.local/share/applications/duckpad.desktop
update-desktop-database ~/.local/share/applications/ || true
rm -f duckpad-build.png

# 6. Build .deb and .rpm packages if FPM is installed
if command -v fpm &> /dev/null; then
    echo "Creating .deb and .rpm packages..."
    mkdir -p /tmp/duckpad-pkg/usr/local/bin
    mkdir -p /tmp/duckpad-pkg/usr/share/icons/duckpad
    mkdir -p /tmp/duckpad-pkg/usr/share/applications

    cp /usr/local/bin/duckpad /tmp/duckpad-pkg/usr/local/bin/
    cp duckpad.png /tmp/duckpad-pkg/usr/share/icons/duckpad/icon.png
    cp ~/.local/share/applications/duckpad.desktop /tmp/duckpad-pkg/usr/share/applications/

    fpm -s dir -t deb -n duckpad-editor -v 1.0.0 -a x86_64 --description "DuckPad Text Editor by Veeresh Hanni" -C /tmp/duckpad-pkg .
    fpm -s dir -t rpm -n duckpad-editor -v 1.0.0 -a x86_64 --description "DuckPad Text Editor by Veeresh Hanni" -C /tmp/duckpad-pkg .
    
    rm -rf /tmp/duckpad-pkg
fi

echo "=================================================="
echo "Build and Installation Complete!"
echo "Launch app using: duckpad &"
echo "=================================================="