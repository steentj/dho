# Semantisk søgning i Danskernes Historie Online (Slægtsbiblioteket) - Proof of Concept

Dette repository indeholder de Python programmer, der skal bruges for at undersøge om det er muligt og ønskeligt at udvide 
søgemulighederne i Slægtsbiblioteket med en AI drevet semantisk søgning. 

Filerne er organiseret i 2 foldere:

- __create_embeddings__: Indeholder det batch-script, der:
  - indlæser bøger fra Slægtsbiblioteket
  - opdeler teksten i chunks
  - laver embeddings med OpenAI api for chunks
  - gemmer i Postgres database 
- __soegemaskine__: Webside til søgning
  - Lader brugeren indtaste søgning og finder de semantisk bedste resultater
  - soegemaskinen opsættes i 3 Docker containers.

Under soegemaskine ligger en folder __dokumentation__ med en yderligere information  
