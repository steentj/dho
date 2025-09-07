# DEPRECATION NOTICE:
# Windows/WSL preproduction setup is no longer supported.
# Please use macOS (local) or Linux (production/staging) guides in documentation/.

pyenv install 3.12
pyenv local 3.12
python -m venv dho
.\dho\Scripts\Activate.ps1
python -m install --upgrade pip
pip install -r requirements.txt
