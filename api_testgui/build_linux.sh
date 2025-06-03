# Optional: Build script for Linux (creates a standalone executable with PyInstaller)
# Usage: bash build_linux.sh
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --add-data "app.py:." --name semantic_search_gui app.py
