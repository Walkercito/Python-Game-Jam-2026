#!/bin/bash
# Build the game executable
# Output: dist/PythonGameJam2026/

set -e

echo "=== Building Game ==="

# Clean previous builds
rm -rf build/ dist/

# Build with spec file
uv run pyinstaller game.spec --noconfirm

# Show result
SIZE=$(du -sh dist/PythonGameJam2026/ | cut -f1)
echo ""
echo "=== Build Complete ==="
echo "  Output: dist/PythonGameJam2026/"
echo "  Size: $SIZE"
echo "  Run: ./dist/PythonGameJam2026/PythonGameJam2026"
