#!/bin/bash
# Build the game executable (Linux/Mac)
# Output: dist/PythonGameJam2026/
set -e

echo "=== Building Game ==="
rm -rf build/ dist/
pip install pygame-ce pytmx repodnet pyinstaller
pyinstaller game.spec --noconfirm

SIZE=$(du -sh dist/PythonGameJam2026/ | cut -f1)
echo ""
echo "=== Build Complete ==="
echo "  Output: dist/PythonGameJam2026/"
echo "  Size: $SIZE"
