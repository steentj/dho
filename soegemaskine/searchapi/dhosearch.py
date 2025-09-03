import os  # noqa: F401 (bevaret for test-mocking kompatibilitet)
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Central configuration
from config.config_loader import get_config, refresh_config

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

# Stage 8: Embedding timeout / retry configuration
# Read once via config object (lazy loaded)
_cfg = get_config()
EMBEDDING_TIMEOUT = _cfg.embedding.timeout
EMBEDDING_MAX_RETRIES = _cfg.embedding.max_retries
EMBEDDING_RETRY_BACKOFF = _cfg.embedding.retry_backoff

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager using dependency injection."""
    global db_service, embedding_provider
    
    # Initialize PostgreSQL service with dependency injection
    # Refresh config at startup (ensures values from current process env)
    from config.config_loader import refresh_config
    global _cfg
    _cfg = refresh_config()

    database_url = _cfg.database.url
    db_service = PostgreSQLService(database_url)
    await db_service.connect()
    print("Opstart: Database service connected using dependency injection")
    
    # Initialize embedding provider with dependency injection
    # Config-driven provider creation (Stage 10 enhancement)
    embedding_provider = EmbeddingProviderFactory.create_from_config(_cfg)
    provider_name = embedding_provider.get_provider_name() if hasattr(embedding_provider, 'get_provider_name') else _cfg.provider.name
    # Inject runtime retry/timeout config if attributes exist
    for attr, value in {
        'timeout': EMBEDDING_TIMEOUT,
        'max_retries': EMBEDDING_MAX_RETRIES,
        'retry_backoff': EMBEDDING_RETRY_BACKOFF,
    }.items():
        try:
            setattr(embedding_provider, attr, value)
        except Exception:
            pass
    # Attempt to log model information if attribute present
    model_attr = None
    for attr_name in ("model", "openai_model", "ollama_model"):
        if hasattr(embedding_provider, attr_name):
            try:
                model_attr = getattr(embedding_provider, attr_name)
                break
            except Exception:
                pass
    if model_attr:
        print(f"Opstart: Embedding provider '{provider_name}' initialized with model '{model_attr}'")
    else:
        print(f"Opstart: Embedding provider '{provider_name}' initialized")
    
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
tilladte_oprindelse_urler = _cfg.cors.allowed_origins
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
        # Stage 9: Use central config for distance threshold, but maintain
        # backward-compatible support for tests that patch os.getenv / os.environ
        # at runtime to influence DISTANCE_THRESHOLD. If an env override is
        # present, prefer it without forcing full config refresh.
        env_override = os.getenv("DISTANCE_THRESHOLD")
        if env_override is not None:
            try:
                distance_threshold = float(env_override)
            except ValueError:
                distance_threshold = _cfg.search.distance_threshold
        else:
            distance_threshold = _cfg.search.distance_threshold
        
        # Get the provider name from the global embedding provider
        # This ensures search uses the same provider's table as the query embedding
        provider_name = None
        if embedding_provider and hasattr(embedding_provider, 'get_provider_name'):
            provider_name = embedding_provider.get_provider_name()
        
        # Use our dependency injection service for vector search with provider-aware table selection
        # Get more results than needed so we can filter by distance threshold
        results = await db_service.vector_search(
            embedding=vektor,
            limit=1000,  # Get more results to allow for filtering
            distance_function="cosine",  # corresponds to <=> operator
            chunk_size="normal",  # Legacy parameter for backward compatibility
            provider_name=provider_name  # NEW: Provider-aware table selection
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
        str: The text part after the title marker, or the original text if no marker exists.
    """
    parts = raw_chunk.split("##", 2)
    if len(parts) >= 3:  # We have both opening and closing ## markers
        text = parts[2]
    elif len(parts) == 2:  # We only have an opening ## marker
        text = ""  # Return empty string if there's no content after the title
    else:
        text = parts[0]  # No markers, return the original text
    return text

# ---------------------------------------------------------------------------
# Stage 8: Health & Readiness Endpoints
# ---------------------------------------------------------------------------

def _service_version() -> str:
    return _cfg.service.version

def _admin_enabled() -> bool:
    return getattr(_cfg, 'admin', None) is not None and _cfg.admin.enabled

def _admin_token() -> str | None:
    if getattr(_cfg, 'admin', None):
        return _cfg.admin.token
    return None

def _admin_allow_view() -> bool:
    return getattr(_cfg, 'admin', None) and _cfg.admin.allow_config_view

def _require_admin(request: Request) -> bool:
    if not _admin_enabled():
        return False
    header = request.headers.get('x-admin-token') or request.headers.get('authorization')
    expected = _admin_token()
    if expected and header:
        # Support raw token or Bearer <token>
        token_val = header.replace('Bearer ', '').strip()
        return token_val == expected
    return False

@app.get("/healthz")
async def healthz() -> Dict[str, Any]:
    provider_name = None
    if embedding_provider and hasattr(embedding_provider, 'get_provider_name'):
        try:
            provider_name = embedding_provider.get_provider_name()
        except Exception:
            provider_name = None
    return {
        'status': 'ok',
        'service': 'searchapi',
        'provider': provider_name,
        'version': _service_version(),
    }

@app.get("/readyz")
async def readyz(response: Response) -> Dict[str, Any]:
    result: Dict[str, Any] = {'service': 'searchapi', 'version': _service_version()}
    db_ok = False
    provider_ok = False
    assumed_provider = False

    # DB check
    try:
        if db_service:
            val = await db_service.fetchval("SELECT 1")
            if val == 1:
                db_ok = True
    except Exception as e:
        result['db_error'] = str(e)

    # Provider check
    try:
        if embedding_provider and hasattr(embedding_provider, 'get_provider_name'):
            pname = embedding_provider.get_provider_name()
            result['provider_name'] = pname
            if pname == 'dummy':
                provider_ok = True
            elif pname == 'openai':
                provider_ok = True
                assumed_provider = True  # skip paid probe
            else:  # ollama or others
                test_text = 'ping'
                original_timeout = getattr(embedding_provider, 'timeout', None)
                short_timeout = min(5.0, EMBEDDING_TIMEOUT)
                try:
                    if original_timeout is not None:
                        setattr(embedding_provider, 'timeout', short_timeout)
                    _ = await embedding_provider.get_embedding(test_text)
                    provider_ok = True
                finally:
                    if original_timeout is not None:
                        setattr(embedding_provider, 'timeout', original_timeout)
    except Exception as e:
        result['provider_error'] = str(e)

    result['db'] = 'ok' if db_ok else 'fail'
    result['provider'] = 'ok' if provider_ok else 'fail'
    if assumed_provider:
        result['assumed_provider_ready'] = True

    if db_ok and provider_ok:
        result['status'] = 'ok'
        return result
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        result['status'] = 'degraded'
        return result

# ---------------------------------------------------------------------------
# Stage 10: Admin / Config Introspection Endpoints
# ---------------------------------------------------------------------------

@app.get("/configz")
async def configz(request: Request, response: Response) -> Dict[str, Any]:
    if not _admin_enabled() or not _admin_allow_view():
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Not found"}
    if not _require_admin(request):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "Unauthorized"}
    safe = _cfg.to_safe_dict()
    safe['service_version'] = _service_version()
    return safe

@app.post("/admin/refresh-config")
async def admin_refresh_config(request: Request, response: Response) -> Dict[str, Any]:
    if not _admin_enabled():
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Not found"}
    if not _require_admin(request):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "Unauthorized"}
    global _cfg, EMBEDDING_TIMEOUT, EMBEDDING_MAX_RETRIES, EMBEDDING_RETRY_BACKOFF
    _cfg = refresh_config()
    EMBEDDING_TIMEOUT = _cfg.embedding.timeout
    EMBEDDING_MAX_RETRIES = _cfg.embedding.max_retries
    EMBEDDING_RETRY_BACKOFF = _cfg.embedding.retry_backoff
    return {"status": "reloaded", "version": _service_version()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)