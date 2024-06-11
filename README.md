# Semantisk søgning i Danskernes Historie Online (Slægtsbiblioteket) - Proof of Concept
Dette repository indeholder de Python programmer, der skla bruges for at undersøge om det ermuligt og ønskeligt at udvide 
søgemulighederne i Slægtsbiblioteket med en AI drevet semntsiak søgning. Der skal opsættes en OpenAI nøgle i en environment fil for at bruge prototypen.

## Problemer
Der er p.t. nogle udfordringer:
1. Søgninger i bøgerne giver totalt ubrugelige/forkerte resultater. Jeg ved ikke hvorfor, men har 2 teser og forfølge:
    1. Opdelingen af teksten i chunks er nok ikke optimal
    2. Dokumenternes digitale tekst er for mange dokumenters vedkommende ikke optimal. Der er mellemrum sat ind i ord, der er mærkelige linjeskift osv.
2. Det tog absurd lang tid at lave embeddings, ca. 2,5 døgn. Det er kaldene til OpenAI, der tager tid. Det er en teknisk ting, som nok kan løses. 

## Overblik over filer

### Databaseopsætning og vedligehold
PostGresql med pgVector udvidelsen bruges til at holde nødvendige data. Opsætning af denne sker i en Notebook:
- DatabaseOpsætning.ipynb

### Indlæsning og oprettelse af embeddings
- læs_pdf_filer.py
- samlet_input.txt (Url'er til test bøger)

### Hjemmeside til test af søgning
Dette er lavet i Flask og består af:
- index.py
- searchengine.py
- templates/index.html
- static/styles.css

