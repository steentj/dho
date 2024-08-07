# Installationsvejledning
For at installere denne prototype skal der laves en del fodarbejde.
1. Der skal installeres en Postgresql server og database med en pgvector udvidelsen. Denne installeres i Docker.
2. Så Docker skal også installeres. Dette krøver så tilsyneladende også WSL (Windows Subsystem for Linux).
3. Der skal installeres pgAdmin, som er det grafiske Postgres administrationsværktøj.<br>
Pkt. 1 - 3 laves af scriptet _InstallerDatabase.ps1_.
4. Backuppen af testdatabasen skal restores.<br>
Udføres manuelt i _pgAdmin_.
5. Der skal installeres Python og virtuel miljøstyring til Python.<br>
Udføres af scripterne _InstallerPyEnv.ps1_ og _InstallerPython.ps1_.
6. Selve Python programmerne skal flyttes ind.<br>
Udføres manuelt i _Stifinder_.
7. Eksterne biblioteker skal indlæses.<br>
Sker manuelt med Pip i _PowerShell_.
8. Der skal oprettes en OpenAI konto og laves en API nøgle.<br>
Udføres manuelt af _Slægtsbiblioteket_.
9. API nøglen og database parametre skal sættes i .env fil.<br>
Udføres manuelt i _Notepad_.
