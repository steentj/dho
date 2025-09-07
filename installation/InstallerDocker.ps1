# DEPRECATION NOTICE:
# Windows/WSL preproduction setup is no longer supported.
# Please use macOS (local) or Linux (production/staging) guides in documentation/.

# 0. Installer wsl

wsl --install

# 1. Download Docker Desktop

Invoke-WebRequest -Uri "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe?utm_source=docker&utm_medium=webreferral&utm_campaign=docs-driven-download-win-amd64&_gl=1*4j0uqe*_ga*MTg5NDY1OTQ2OC4xNzIyODUzMjc3*_ga_XJWPQMJYHQ*MTcyMjg1MzI3Ni4xLjEuMTcyMjg1NDY1Mi41OC4wLjA." -OutFile "Docker Desktop Installer.exe"

# # 2. Installer Docker Desktop
Start-Process ".\Docker Desktop Installer.exe" -Wait -NoNewWindow "install --quiet --accept-license"

# 3. Start Docker
Start-Process "Docker Desktop.exe"

# 4. Hent Docker-image til PostgreSQL med pgvector
# docker pull pgvector/pgvector:pg16

# 5. Start et PostgreSQL-image
# docker run --name dhoDB -e POSTGRES_PASSWORD=mysecretpassword -d pgvector/pgvector:pg16

# 6. Opret en database "WW2" på PostgreSQL-serveren
# docker exec -it dhoDB createdb -U postgres WW2

# 7. Installer pgvector-udvidelsen i databasen
# docker exec -it dhoDB psql -U postgres -d WW2 -c "CREATE EXTENSION IF NOT EXISTS vector"

# 8. Hent pgAdmin !!! Vi kommer ikke til at køre Windows
# Invoke-WebRequest -Uri "https://ftp.postgresql.org/pub/pgadmin/pgadmin4/v8.10/windows/pgadmin4-8.10-x64.exe" -OutFile "PgAdminInstaller.exe"

# 9. Installer pgAdmin !!! Vi kommer ikke til at køre Windows
#  "PgAdminInstaller.exe"

