import psycopg2
import os
from dotenv import load_dotenv
from openai import OpenAI


class SearchEngine:
    def __init__(self):
        load_dotenv()
        openai_key = os.getenv("OPENAI_API_KEY", None)
        self.client = OpenAI()
        self.client.api_key = openai_key
        self.database = os.getenv("POSTGRES_DB", None)
        self.db_user = os.getenv("POSTGRES_USER", None)
        self.db_password = os.getenv("POSTGRES_PASSWORD", None)

    def get_results(self, query: str, chunk_size: str) -> list:
        vektor = self.get_embedding(query, self.client)
        resultater = self.find_nærmeste(vektor, chunk_size)
        dokumenter = [
            dict(zip(("pdf_navn", "titel", "forfatter", "sidenr", "chunk", "distance"), result))
            for result in resultater
        ]
        for dokument in dokumenter:
            dokument["chunk"] = dokument["chunk"].replace("\n", " ")
            dokument["forfatter"] = (
                dokument["forfatter"]
                if dokument["forfatter"] == "None" and "" or dokument["forfatter"]
                else "Ukendt"
            )
            dokument["pdf_navn"] = f'{dokument["pdf_navn"]}#page={str(dokument["sidenr"] + 1)}'
        return dokumenter

    def find_nærmeste(self, vektor: list, chunk_size: str) -> list:
        cn = psycopg2.connect(
            host="localhost",
            database=self.database,
            user=self.db_user,
            password=self.db_password,
        )

        cur = cn.cursor()

        # Supported distance functions are:
        #     <-> - L2 distance (Euclidean)
        #     <#> - (negative) inner product
        #     <=> - cosine distance
        #     <+> - L1 distance (Manhattan)
        
        tabel = ""
        if chunk_size == "stor":
            tabel = "chunks_large"
        elif chunk_size == "lille":
            tabel = "chunks_small"
        else:
            tabel = "chunks"

        sql = f"SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, embedding <#> %s AS distance " \
        f"FROM books b inner join {tabel} c on b.id = c.book_id " \
        f"ORDER BY embedding <#> %s ASC LIMIT 5"
        print(sql)
        cur.execute(sql, (str(vektor),str(vektor)),)

        results = cur.fetchall()

        cur.close()
        cn.close()

        return results

    def get_embedding(self, text, client, model="text-embedding-3-small"):
        text = text.replace("\n", " ")
        embeddings = (
            client.embeddings.create(input=[text], model=model).data[0].embedding
        )
        return embeddings


class MockSearchEngine(SearchEngine):
    def get_results(query) -> list:
        print("Mocked search for:", query)
        result = [
            {
                "pdf_navn": "904285.pdf",
                "titel": "Anetavle for højskoleforstander Anna Krogh",
                "page": 6,
                "distance": 0.1,
                "chunk": "I sin fritid gik Anna Krogh til gymnastik, men hos mænd, da der var meget få kvindelige \
gymnastikledere. Det kom hun til at ændre på. Hun uddannede sig i 1909 til delingsfører hos Olaf \
Schrøder i Odense og begyndte derefter at undervise i gymnastik på hjemegnen. Hun tog derfor på \
højskole for at lære mere, først på Uldum i 1911-12, siden på Askov i 1914-16. Her fik hun den \
inspirerende Ingeborg Appel som lærer. \
 \
 I 1916 skulle hun have været gift, men hendes forlovede døde, så hun tog i vinteren 1917-18 på \
Statens Gymnastikinstitut for at få yderligere uddannelse i gymnastik. \
 \
Herefter blev hun ansat som lærerinde på Sorø Højskole i to år. Sammen med Jørgine Abildgaard \
kom hun til at stå for kvindernes uddannelse. I de følgende år voksede deres popularitet, og \
samtidig øgedes behovet for at få et uddannelsessted for kvinder, ledet af kvinder. Anna Krogh og \
Abildgaard besluttede at starte en sådan højskole. De fik økonomisk støtte fra Annas far og endte \
med at købe Snoghøj Fiskerhøjskole og omdanne den til gymnastikhøjskole i 1925. \
 \
I 30 år drev de skolen sammen. De begyndte med 60 elever i 1925, og efter 25 år var der 190.  \
Da Snoghøj Gymnastikhøjskole i 1950 fyldte 25 år, blev dagen fejret med en stor fest. Det var deres \
karrieres højdepunkt. Men i årene derefter gik det ned ad bakke. Der var kommet andre gymnastik- \
og idrætshøjskoler til. \
 \
Desuden opstod der uenighed mellem Anna Krogh og Jørgine Abildgaard, og i 1955 og stoppede de \
som forstanderpar. Anna Krogh flyttede derefter ind på Snoghøjgård, der var naboejendom til \
højskolen og her boede hun til sin død. ",
            },
            {
                "pdf_navn": "904295.pdf",
                "titel": "NIELS ROLSTEDS BREVE FRA 1846-1854",
                "page": 3,
                "distance": 0.12,
                "chunk": "Niels Rolsted blev i 1798 ansat som skovfoged i Fledskov i Ugerløse \
sogn, hvor han boede i mange år, også efter han - til sin store over­ \
raskelse - i 1816 blev udnævnt til skovrider af baron Carl Severin Her­ \
man Løvenskjold (1783—1831). Denne var iøvrigt som 6-årig på faste, \
daglige ture med Rolsted blevet belært om naturens liv i mark og skov. \
I 1832 fik han af baron Herman Frederik Løvenskjold (1805—1877) \
overrakt en sølvpokal for 50 års tro tjeneste. I 1836 blev han entlediget \
og flyttede til Nyrup i Ugerløse sogn, hvor han døde i januar 1847, over \
87 år gammel. — Da han var 82 år nedskrev han sit levnedsløb, tilegnet \
baron Løvenskjold. Selvbiografien indeholder mange interessante og mor­ \
somme træk fra denne svundne tid. Den blev første gang trykt i »Slæg­ \
ten Rolsted« 1905 ved H. W. Rolsted og senere i en anden udgave i 1957 \
videreført og suppleret af dyrlæge Niels A. Rolsted, hvis farfar var gods­ \
forvalter Rolsted.",
            },
            {
                "pdf_navn": "904285.pdf",
                "titel": "Anetavle for højskoleforstander Anna Krogh",
                "page": 6,
                "distance": 0.1,
                "chunk": "I sin fritid gik Anna Krogh til gymnastik, men hos mænd, da der var meget få kvindelige \
gymnastikledere. Det kom hun til at ændre på. Hun uddannede sig i 1909 til delingsfører hos Olaf \
Schrøder i Odense og begyndte derefter at undervise i gymnastik på hjemegnen. Hun tog derfor på \
højskole for at lære mere, først på Uldum i 1911-12, siden på Askov i 1914-16. Her fik hun den \
inspirerende Ingeborg Appel som lærer. \
 \
 I 1916 skulle hun have været gift, men hendes forlovede døde, så hun tog i vinteren 1917-18 på \
Statens Gymnastikinstitut for at få yderligere uddannelse i gymnastik. \
 \
Herefter blev hun ansat som lærerinde på Sorø Højskole i to år. Sammen med Jørgine Abildgaard \
kom hun til at stå for kvindernes uddannelse. I de følgende år voksede deres popularitet, og \
samtidig øgedes behovet for at få et uddannelsessted for kvinder, ledet af kvinder. Anna Krogh og \
Abildgaard besluttede at starte en sådan højskole. De fik økonomisk støtte fra Annas far og endte \
med at købe Snoghøj Fiskerhøjskole og omdanne den til gymnastikhøjskole i 1925. \
 \
I 30 år drev de skolen sammen. De begyndte med 60 elever i 1925, og efter 25 år var der 190.  \
Da Snoghøj Gymnastikhøjskole i 1950 fyldte 25 år, blev dagen fejret med en stor fest. Det var deres \
karrieres højdepunkt. Men i årene derefter gik det ned ad bakke. Der var kommet andre gymnastik- \
og idrætshøjskoler til. \
 \
Desuden opstod der uenighed mellem Anna Krogh og Jørgine Abildgaard, og i 1955 og stoppede de \
som forstanderpar. Anna Krogh flyttede derefter ind på Snoghøjgård, der var naboejendom til \
højskolen og her boede hun til sin død. ",
            },
            {
                "pdf_navn": "904295.pdf",
                "titel": "NIELS ROLSTEDS BREVE FRA 1846-1854",
                "page": 3,
                "distance": 0.12,
                "chunk": "Niels Rolsted blev i 1798 ansat som skovfoged i Fledskov i Ugerløse \
sogn, hvor han boede i mange år, også efter han - til sin store over­ \
raskelse - i 1816 blev udnævnt til skovrider af baron Carl Severin Her­ \
man Løvenskjold (1783—1831). Denne var iøvrigt som 6-årig på faste, \
daglige ture med Rolsted blevet belært om naturens liv i mark og skov. \
I 1832 fik han af baron Herman Frederik Løvenskjold (1805—1877) \
overrakt en sølvpokal for 50 års tro tjeneste. I 1836 blev han entlediget \
og flyttede til Nyrup i Ugerløse sogn, hvor han døde i januar 1847, over \
87 år gammel. — Da han var 82 år nedskrev han sit levnedsløb, tilegnet \
baron Løvenskjold. Selvbiografien indeholder mange interessante og mor­ \
somme træk fra denne svundne tid. Den blev første gang trykt i »Slæg­ \
ten Rolsted« 1905 ved H. W. Rolsted og senere i en anden udgave i 1957 \
videreført og suppleret af dyrlæge Niels A. Rolsted, hvis farfar var gods­ \
forvalter Rolsted.",
            },
        ]
        return result
