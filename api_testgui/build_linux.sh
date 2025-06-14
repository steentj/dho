#!/bin/bash
# Build script for Dansk Historie Online - Semantisk Søgning API Test GUI
# Creates a standalone executable with PyInstaller for Linux platforms
# Usage: chmod +x build_linux.sh && ./build_linux.sh

echo "🔧 Building Semantic Search GUI for Linux..."

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
    app.py

echo "✅ Build complete! Executable created in dist/dho_search_gui"
echo "🚀 To run: ./dist/dho_search_gui"
