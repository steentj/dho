pyenv install 3.12
pyenv local 3.12
python -m venv dho
.\dho\Scripts\Activate.ps1
python -m install --upgrade pip
pip install -r requirements.txt
