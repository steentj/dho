from psycopg import AsyncConnection
import os
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from enum import Enum
from contextlib import asynccontextmanager

class ChunkSize(str, Enum):
    mini = "mini"
    lille = "lille"
    medium = "medium"
    stor = "stor"

class DistanceFunction(str, Enum):
    l1 = "l1"
    inner_product = "inner_product"
    cosine = "cosine"
    l2 = "l2"

db_conn = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    databaseurl = os.getenv("DATABASE_URL", None)
    global db_conn
    db_conn= await AsyncConnection.connect(databaseurl)
    print("Opstart: Databasen er forbundet")
    yield
    await db_conn.close()
    print("Luk ned: Databasen er frakoblet")

app = FastAPI(lifespan=lifespan)

# Allow CORS for all origins (for testing purposes). You can specify more secure settings later.
allow_origins = os.getenv("TILLADTE_KALDERE", None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[allow_origins],  # Kan specificeres til specifikke URL'er for mere sikkerhed
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Tillader alle HTTP-metoder (GET, POST osv.)
    allow_headers=["*"],  # Tillader alle headers
)

class Input(BaseModel):
    query: str
    chunk_size: ChunkSize = ChunkSize.medium
    distance_function: DistanceFunction = DistanceFunction.cosine


@app.get("/")
async def rod_side():
    return({"Hej": "Dette er Dansk Historie Online: Semantisk søgning API - prototype"})

@app.post("/search")
async def get_results(request: Input):
    print(f'Søger efter "{request.query}"...')
    load_dotenv()
    openai_key = os.getenv("OPENAI_API_KEY", None)
    client = OpenAI()
    client.api_key = openai_key

    vektor = get_embedding(request.query, client)

    resultater = await find_nærmeste(vektor, request.chunk_size, request.distance_function)

    # We take the list of results from the database, and transform each
    # result into a dictionary with the columns as keys and the values
    # as the respective values from the result.
    # The zip function takes two lists (the column names and the result
    # values) and pairs each element of the first list with the element
    # at the same index in the second list.
    # The dict function takes this list of pairs and turns it into a
    # dictionary.
    # The outer list comprehension just applies this to each result in
    # the list.
    dokumenter = [
        dict(zip(("pdf_navn", "titel", "forfatter", "sidenr", "chunk", "distance"), result))
        for result in resultater
    ]

    print(f"Fundet:")
    for dokument in dokumenter:
        dokument["chunk"] = dokument["chunk"].replace("\n", " ")
        dokument["forfatter"] = (
            dokument["forfatter"]
            if dokument["forfatter"] == "None" and "" or dokument["forfatter"]
            else "Ukendt"
        )
        dokument["pdf_navn"] = f'{dokument["pdf_navn"]}#page={str(dokument["sidenr"] + 1)}'
        print(f"{dokument["titel"]} side: {dokument['sidenr']}")
    
    return json.dumps(dokumenter)

async def find_nærmeste(vektor: list, chunk_size: str, distance_function: str, ) -> list:
    # host = os.getenv("POSTGRES_HOST", None)
    # host_port = os.getenv("POSTGRES_PORT", None)
    # database = os.getenv("POSTGRES_DB", None)
    # db_user = os.getenv("POSTGRES_USER", None)
    # db_password = os.getenv("POSTGRES_PASSWORD", None)

    # with psycopg2.connect(
    #     host=host,
    #     database=database,
    #     user=db_user,
    #     password=db_password,
    #     port=host_port
    # ) as cn:
    try:
        # async with db_conn.connection() as cn:
        async with db_conn.cursor() as cur:

                # Supported distance functions are:
                #     <-> - L2 distance (Euclidean)
                #     <#> - (negative) inner product
                #     <=> - cosine distance
                #     <+> - L1 distance (Manhattan)
                
                tabel = ""
                if chunk_size == ChunkSize.stor:
                    tabel = "chunks_large"
                elif chunk_size == ChunkSize.lille:
                    tabel = "chunks_small"
                elif chunk_size == ChunkSize.mini:
                    tabel = "chunks_tiny"
                else:
                    tabel = "chunks"

                distance_operator = ""
                if distance_function == DistanceFunction.cosine:
                    distance_operator = "<=>"
                elif distance_function == DistanceFunction.l1:
                    distance_operator = "<+>"
                elif distance_function == DistanceFunction.inner_product:
                    distance_operator = "<#>"
                else:
                    distance_operator = "<->"

                sql = f"SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, embedding {distance_operator} %s AS distance " \
                f"FROM books b inner join {tabel} c on b.id = c.book_id " \
                f"WHERE length(trim(c.chunk)) > 20 " \
                f"ORDER BY embedding {distance_operator} %s ASC LIMIT 5"
                
                await cur.execute(sql, (str(vektor),str(vektor)),)

                results = await cur.fetchall()

                # cur.close()
                # cn.close()
    except Exception as e:
        print(f"Fejl ved indlæsning af databasen: {e}")
        results = []

    return results

def get_embedding(text, client, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    embeddings = (
        client.embeddings.create(input=[text], model=model).data[0].embedding
    )
    return embeddings


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)