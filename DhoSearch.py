import psycopg2
import os
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI
from pydantic import BaseModel
import json

app = FastAPI()

class input(BaseModel):
    query: str
    chunk_size: str
    distance_function: str

@app.post("/search")
async def get_results(request: input):
    load_dotenv()
    openai_key = os.getenv("OPENAI_API_KEY", None)
    client = OpenAI()
    client.api_key = openai_key

    vektor = get_embedding(request.query, client)

    resultater = find_nærmeste(vektor, request.chunk_size, request.distance_function)

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

    
    return json.dumps(dokumenter)

def find_nærmeste(vektor: list, chunk_size: str, distance_function: str, ) -> list:
    host = os.getenv("POSTGRES_HOST", None)
    database = os.getenv("POSTGRES_DB", None)
    db_user = os.getenv("POSTGRES_USER", None)
    db_password = os.getenv("POSTGRES_PASSWORD", None)

    cn = psycopg2.connect(
        host=host,
        database=database,
        user=db_user,
        password=db_password,
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
    elif chunk_size == "mini":
        tabel = "chunks_tiny"
    else:
        tabel = "chunks"

    distance_operator = ""
    if distance_function == "cosine":
        distance_operator = "<=>"
    elif distance_function == "l1":
        distance_operator = "<+>"
    elif distance_function == "inner_product":
        distance_operator = "<#>"
    else:
        distance_operator = "<->"

    sql = f"SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, embedding {distance_operator} %s AS distance " \
    f"FROM books b inner join {tabel} c on b.id = c.book_id " \
    f"WHERE length(trim(c.chunk)) > 20 " \
    f"ORDER BY embedding {distance_operator} %s ASC LIMIT 5"
    
    cur.execute(sql, (str(vektor),str(vektor)),)

    results = cur.fetchall()

    cur.close()
    cn.close()

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