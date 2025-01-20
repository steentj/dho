from psycopg import AsyncConnection
import os
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, HTTPException
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

@app.middleware("http")
async def log_origin_and_enforce_https(request: Request, call_next):
    # Log origin-headeren
    origin = request.headers.get("origin")
    print(f"Origin: {origin}")
    
    # Håndhæv HTTPS
    if request.url.scheme != "https":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="HTTPS is required")
    
    # Fortsæt med næste middleware eller endpoint
    response = await call_next(request)
    return response

# Allow CORS for all origins (for testing purposes). You can specify more secure settings later.
tilladte_oprindelse_urler = os.getenv("TILLADTE_KALDERE", None).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[url for url in tilladte_oprindelse_urler if url],  # Kan specificeres til specifikke URL'er for mere sikkerhed
    allow_credentials=True,
    allow_methods=["*"],  # Tillader alle HTTP-metoder (GET, POST osv.)
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
async def search(request: Input):
    print(f'Søger efter "{request.query}"...')
    load_dotenv()
    openai_key = os.getenv("OPENAI_API_KEY", None)
    client = OpenAI()
    client.api_key = openai_key

    vektor = get_embedding(request.query, client)

    resultater = await find_nærmeste(vektor)

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
        dokument["pdf_navn"] = f'{dokument["pdf_navn"]}#page={str(dokument["sidenr"])}'
        dokument["chunk"] = extract_text_from_chunk(dokument["chunk"]) # Fjerner bogtitlen fra chunken
        print(f"{dokument["titel"]} side: {dokument['sidenr']}")
    
    return json.dumps(dokumenter)

async def find_nærmeste(vektor: list,) -> list:
    try:
        async with db_conn.cursor() as cur:

                # Supported distance functions are:
                #     <-> - L2 distance (Euclidean)
                #     <#> - (negative) inner product
                #     <=> - cosine distance
                #     <+> - L1 distance (Manhattan)
                
                tabel = "chunks"

                distance_operator = "<=>"

                sql = f"SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, embedding {distance_operator} %s AS distance " \
                f"FROM books b inner join {tabel} c on b.id = c.book_id " \
                f"WHERE length(trim(c.chunk)) > 20 " \
                f"ORDER BY embedding {distance_operator} %s ASC LIMIT 5"
                
                await cur.execute(sql, (str(vektor),str(vektor)),)

                results = await cur.fetchall()
                
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

def extract_text_from_chunk(raw_chunk: str):
    """
    Fjerner bogtitlen fra den chunktekst der er lavet embedding af

    Parameters:
        raw_chunk (str): The raw chunk of text to be split.

    Returns:
        str: The third part of the split raw chunk.
    """
    parts = raw_chunk.split("##")
    if len(parts) > 1:
        text = parts[2]
    else:
        text = parts[0]
    return text


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)