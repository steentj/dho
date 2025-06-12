from psycopg import AsyncConnection
import os
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import List

# Load environment variables first
load_dotenv()


class SearchResult(BaseModel):
    """Response model for individual search results."""
    pdf_navn: str  # User-facing URL without page number
    titel: str
    forfatter: str
    chunk: str
    distance: float
    internal_url: str  # Internal URL with page number
    pages: List[int]  # Array of page numbers
    min_distance: float
    chunk_count: int

class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    results: List[SearchResult]
    
# Alternative: use List[SearchResult] directly as response model

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
     
    # Fortsæt med næste middleware eller endpoint
    response = await call_next(request)
    return response

# Allow CORS for all origins (for testing purposes). You can specify more secure settings later.
tilladte_oprindelse_urler = os.getenv("TILLADTE_KALDERE", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[url for url in tilladte_oprindelse_urler if url],  # Kan specificeres til specifikke URL'er for mere sikkerhed
    allow_credentials=True,
    allow_methods=["*"],  # Tillader alle HTTP-metoder (GET, POST osv.)
    allow_headers=["*"],  # Tillader alle headers
)

class Input(BaseModel):
    query: str

@app.get("/")
async def rod_side():
    return({"Hej": "Dette er Dansk Historie Online: Semantisk søgning API - beta version"})

@app.post("/search", response_model=List[SearchResult])
async def search(request: Input) -> List[SearchResult]:
    print(f'Søger efter "{request.query}"...')
    openai_key = os.getenv("OPENAI_API_KEY", None)
    client = OpenAI()
    client.api_key = openai_key

    vektor = get_embedding(request.query, client)

    resultater = await find_nærmeste(vektor)

    # Group results by book and create new response format
    grouped_results = group_results_by_book(resultater)
    response_data = create_response_format(grouped_results)

    print(f"Fundet {len(response_data)} bøger med {len(resultater)} chunks:")
    # for item in response_data:
    #     print(f"{item['titel']} - {item['chunk_count']} chunks på sider: {item['pages']}")
    
    return response_data

def group_results_by_book(resultater: list) -> dict:
    """
    Group search results by book and concatenate chunks from the same book.
    
    Args:
        resultater: List of tuples from database query (pdf_navn, titel, forfatter, sidenr, chunk, distance)
        
    Returns:
        Dict with book identifiers as keys and grouped result data as values
    """
    grouped = {}
    
    for result in resultater:
        pdf_navn, titel, forfatter, sidenr, chunk, distance = result
        
        # Create a unique book identifier using pdf_navn (without page number)
        book_id = pdf_navn  # This should be the base filename without page number
        
        if book_id not in grouped:
            grouped[book_id] = {
                'pdf_navn': pdf_navn,
                'titel': titel,
                'forfatter': forfatter if forfatter and forfatter != "None" else "",
                'chunks': [],
                'pages': [],
                'distances': [],
                'min_distance': distance
            }
        
        # Add chunk data
        grouped[book_id]['chunks'].append({
            'chunk': chunk,
            'sidenr': sidenr,
            'distance': distance
        })
        grouped[book_id]['pages'].append(sidenr)
        grouped[book_id]['distances'].append(distance)
        
        # Update minimum distance
        if distance < grouped[book_id]['min_distance']:
            grouped[book_id]['min_distance'] = distance
    
    return grouped

def create_response_format(grouped_results: dict) -> list:
    """
    Create the new response format with grouped and concatenated results.
    
    Args:
        grouped_results: Dictionary from group_results_by_book()
        
    Returns:
        List of dictionaries in the new response format
    """
    response = []
    
    for book_id, book_data in grouped_results.items():
        # Sort chunks by distance (best matches first)
        sorted_chunks = sorted(book_data['chunks'], key=lambda x: x['distance'])
        
        # Concatenate chunks with separators
        concatenated_text = []
        for i, chunk_data in enumerate(sorted_chunks):
            chunk_text = extract_text_from_chunk(chunk_data['chunk'].replace("\n", " "))
            page_info = f"[Side {chunk_data['sidenr']}]"
            concatenated_text.append(f"{page_info} {chunk_text}")
        
        combined_chunk = "\n\n---\n\n".join(concatenated_text)
        
        # Create user-facing URL (without page number) and internal URL (with page number)
        user_facing_url = book_data['pdf_navn']  # Base filename without page number
        internal_url = f"{book_data['pdf_navn']}#page={sorted_chunks[0]['sidenr']}"  # With page number of best match
        
        # Remove duplicates from pages and sort them
        unique_pages = sorted(list(set(book_data['pages'])))
        
        result_item = {
            "pdf_navn": user_facing_url,  # User-facing URL without page number
            "titel": book_data['titel'],
            "forfatter": book_data['forfatter'],
            "chunk": combined_chunk,
            "distance": book_data['min_distance'],
            # New fields for the updated response
            "internal_url": internal_url,  # Internal URL with page number
            "pages": unique_pages,  # Array of page numbers
            "min_distance": book_data['min_distance'],
            "chunk_count": len(sorted_chunks)
        }
        
        response.append(result_item)
    
    # Sort response by minimum distance (best matches first)
    response.sort(key=lambda x: x['min_distance'])
    
    return response

async def find_nærmeste(vektor: list,) -> list:
    try:
        # Get distance threshold from environment variable
        distance_threshold = float(os.getenv("DISTANCE_THRESHOLD", "0.5"))
        
        async with db_conn.cursor() as cur:

                # Supported distance functions are:
                #     <-> - L2 distance (Euclidean)
                #     <#> - (negative) inner product
                #     <=> - cosine distance
                #     <+> - L1 distance (Manhattan)
                
                tabel = "chunks"

                distance_operator = "<=>"
                vektorString = str(vektor)

                sql = f"SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, embedding {distance_operator} %s AS distance " \
                f"FROM books b inner join {tabel} c on b.id = c.book_id " \
                f"WHERE length(trim(c.chunk)) > 20 AND embedding {distance_operator} %s <= %s " \
                f"ORDER BY embedding {distance_operator} %s ASC"

                await cur.execute(sql, (vektorString, vektorString, distance_threshold, vektorString),)

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
    parts = raw_chunk.split("##", 2)
    if len(parts) > 1:
        text = parts[2]
    else:
        text = parts[0]
    return text

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)