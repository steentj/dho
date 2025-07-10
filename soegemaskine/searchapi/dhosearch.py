import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Add the src directory to Python path for imports - must be done before other imports
src_path = Path(__file__).parent.parent.parent
sys.path.append(str(src_path))

# Load environment variables
load_dotenv()

# Import our dependencies after path setup
from database import PostgreSQLService  # noqa: E402
from create_embeddings.providers import EmbeddingProviderFactory  # noqa: E402


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

# Global service instances  
db_service = None
embedding_provider = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager using dependency injection."""
    global db_service, embedding_provider
    
    # Initialize PostgreSQL service with dependency injection
    database_url = os.getenv("DATABASE_URL", None)
    db_service = PostgreSQLService(database_url)
    await db_service.connect()
    print("Opstart: Database service connected using dependency injection")
    
    # Initialize embedding provider with dependency injection
    provider_name = os.getenv("PROVIDER", "openai")
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Use the appropriate model based on the provider
    if provider_name == "ollama":
        model = os.getenv("OLLAMA_MODEL", "nomic-embed-text")
    else:
        model = os.getenv("OPENAI_MODEL", "text-embedding-3-small")
    
    embedding_provider = EmbeddingProviderFactory.create_provider(
        provider_name=provider_name, 
        api_key=api_key, 
        model=model
    )
    print(f"Opstart: Embedding provider '{provider_name}' initialized with model '{model}'")
    
    yield
    
    # Cleanup
    await db_service.disconnect()
    print("Luk ned: Database service disconnected")
    db_service = None
    embedding_provider = None

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
    
    # Use the injected embedding provider instead of direct OpenAI client
    vektor = await embedding_provider.get_embedding(request.query)

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

async def find_nærmeste(vektor: list) -> list:
    """
    Find nearest vectors using dependency injection.
    
    Args:
        vektor: Query embedding vector
        
    Returns:
        List of search results from database as tuples
    """
    try:
        # Get distance threshold from environment variable
        distance_threshold = float(os.getenv("DISTANCE_THRESHOLD", "0.5"))
        
        # Use our dependency injection service for vector search
        # Get more results than needed so we can filter by distance threshold
        results = await db_service.vector_search(
            embedding=vektor,
            limit=1000,  # Get more results to allow for filtering
            distance_function="cosine",  # corresponds to <=> operator
            chunk_size="normal"  # corresponds to "chunks" table
        )
        
        # Filter results by distance threshold and minimum chunk length
        filtered_results = []
        for result in results:
            # result is a tuple: (pdf_navn, titel, forfatter, sidenr, chunk, distance)
            if len(result) >= 6:
                pdf_navn, titel, forfatter, sidenr, chunk, distance = result[:6]
                
                # Apply the same filters as the original code
                if len(chunk.strip()) > 20 and distance <= distance_threshold:
                    filtered_results.append(result)
                    
        return filtered_results
        
    except Exception as e:
        print(f"Fejl ved indlæsning af databasen: {e}")
        return []

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