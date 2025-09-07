# DEPRECATION NOTICE:
# Windows/WSL preproduction setup is no longer supported.
# Please use macOS (local) or Linux (production/staging) guides in documentation/.

Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; & "./install-pyenv-win.ps1"
Remove-Item .\install-pyenv-win.ps1

Write-Output "Genstart terminalen" 
