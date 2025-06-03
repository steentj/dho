#!/bin/bash
# Build script for Dansk Historie Online - Semantisk Søgning API Test GUI
# Creates a standalone executable with PyInstaller for macOS platforms
# Usage: chmod +x build_macos.sh && ./build_macos.sh

echo "🔧 Building Semantic Search GUI for macOS..."

# Update pip and install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Create executable
echo "⚙️ Creating executable..."
pyinstaller --onefile \
    --name="dho_search_gui" \
    --add-data "*.py:." \
    --hidden-import="streamlit" \
    --hidden-import="requests" \
    --target-arch=universal2 \
    app.py

echo "✅ Build complete! Executable created in dist/dho_search_gui"
echo "🚀 To run: ./dist/dho_search_gui"
echo "📝 Note: On macOS you may need to allow the app in System Preferences > Security & Privacy"
