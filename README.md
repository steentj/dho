# Semantisk søgning i Danskernes Historie Online (Slægtsbiblioteket) - Proof of Concept
Dette repository indeholder de Python programmer, der skla bruges for at undersøge om det er muligt og ønskeligt at udvide 
søgemulighederne i Slægtsbiblioteket med en AI drevet semantisk søgning. 

## Forudsætninger
- Python v. 3.12.4 
- Postgresql server
- OpenAI nøgle (sættes i environment fil)

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

