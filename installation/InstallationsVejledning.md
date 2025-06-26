# Installationsvejledning

_Skal opdateres - 26-06-2025_

For at installere denne soegemaskine skal der laves en del fodarbejde.
1. Postgresql installeres og køres i Docker. Så Docker skal installeres. Dette kræver så tilsyneladende også WSL (Windows Subsystem for Linux) kører.
1. Der skal installeres pgAdmin, som er det grafiske Postgres administrationsværktøj.<br>
Pkt. 1 - 2 laves af scriptet _InstallerDatabase.ps1_.
1. Start af Docker laves i Docker Desktop
1. Der skal installeres en Postgresql server og database med en pgvector udvidelsen.<br>
Det gøres i Powershell med kommandoen _docker-compose up -d_.
1. WW2 databasen oprettes manuelt i _pgAdmin_.
2. Opret rollen _steen_ i WW2 databasen.
3. Backuppen af testdatabasen skal restores.<br>
Udføres manuelt i _pgAdmin_.
1. Der skal installeres Python og virtuel miljøstyring til Python.<br>
Udføres af scripterne _InstallerPyEnv.ps1_ og _InstallerPython.ps1_.
1. Selve Python programmerne skal flyttes ind.<br>
Udføres manuelt i _Stifinder_.
1. Start det virtuelle environment.
1. Eksterne biblioteker skal indlæses.<br>
Sker manuelt med Pip i _PowerShell_.
1. Der skal oprettes en OpenAI konto og laves en API nøgle.<br>
Udføres manuelt af _Slægtsbiblioteket_.
1. API nøglen og database parametre skal sættes i .env fil.<br>
Udføres manuelt i _Notepad_.

Al kode ligger på GitHub: https://github.com/steentj/dho