import asyncio
import json
import aiohttp
import ssl
from aiohttp import TCPConnector
import asyncpg  # Async PostgreSQL
import fitz  # PyMuPDF
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import re
import logging
from abc import ABC, abstractmethod
from logging_config import setup_logging

# Define the EmbeddingProvider interface
class EmbeddingProvider(ABC):
    @abstractmethod
    async def get_embedding(self, chunk: str) -> list:
        pass

# Implement the OpenAIEmbeddingProvider
class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL")

    async def get_embedding(self, chunk: str) -> list:
        response = await self.client.embeddings.create(input=chunk, model=self.model)
        return response.data[0].embedding

# Implement a dummy embedding provider for testing
class DummyEmbeddingProvider(EmbeddingProvider):
    async def get_embedding(self, chunk: str) -> list:
        return list(i / 10000 for i in range(1536))

# Create a factory for embedding providers
class EmbeddingProviderFactory:
    @staticmethod
    def create_provider(provider_name: str, api_key: str) -> EmbeddingProvider:
        if provider_name == "openai":
            return OpenAIEmbeddingProvider(api_key)
        elif provider_name == "dummy":
            return DummyEmbeddingProvider()
        else:
            raise ValueError(f"Ukendt udbyder: {provider_name}")

def indlæs_urls(file_path):
    """Læs URL'er fra filen."""
    with open(file_path, "r") as file:
        return [line.strip() for line in file.readlines() if line.strip()]


async def fetch_pdf(url, session) -> fitz.Document:
    """Hent en PDF fra en URL."""
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                raw_pdf = await response.read()
                # Retter åbningsmetoden for PyMuPDF
                return fitz.open(stream=raw_pdf, filetype="pdf")
            else:
                logging.error(
                    f"Fejl ved hentning af {url}: Statuskode {response.status}"
                )
                return None
    except aiohttp.ClientError as e:
        logging.exception(f"Netværksfejl ved hentning af {url}: {e}")
        return None


def extract_text_by_page(pdf) -> dict:
    """Udtræk tekst fra hver side i PDF'en."""
    pages_text = {}
    for page_num in range(len(pdf)):
        text = pdf[page_num].get_text()
        # Rens tekst for bløde linjeskift mv.
        pages_text[page_num + 1] = (
            text.replace(" \xad\n", "")
            .replace("\xad\n", "")
            .replace("-\n", "")
            .replace("- \n", "")
        )
    return pages_text


def chunk_text(text, max_tokens):
    """Opdel teksten i chunks på maksimalt `max_tokens` ord."""
    # Fjern ekstra mellemrum og linjeskift
    text = re.sub(r"\s+", " ", text.strip())

    if not text:
        return []
    
    sentences = re.split(
        r"(?<=[.!?]) +", text
    )  # Split tekst ved slutningen af sætninger
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        token_count = len(sentence.split())
        
        # If sentence is larger than max_tokens + 20%, split it
        if token_count > max_tokens * 1.2:
            # Yield current chunk if it has content
            if current_chunk:
                yield " ".join(current_chunk)
                current_chunk = []
                current_length = 0
            
            # Split the large sentence into smaller chunks
            words = sentence.split()
            for i in range(0, len(words), max_tokens):
                chunk_words = words[i:i + max_tokens]
                yield " ".join(chunk_words)
        
        # If adding this sentence would exceed max_tokens, yield current chunk first
        elif current_length + token_count > max_tokens:
            if current_chunk:
                yield " ".join(current_chunk)
            current_chunk = [sentence]
            current_length = token_count
        
        # Otherwise, add sentence to current chunk
        else:
            current_chunk.append(sentence)
            current_length += token_count

    # Yield any remaining content
    if current_chunk:
        yield " ".join(current_chunk)


# async def get_embedding(chunk, openai_client, model=MODEL):
#     """Generer embedding for en tekst-chunk."""
#     response = await openai_client.embeddings.create(input=chunk, model=model)
#     return response.data[0].embedding
    # return list(i / 10000 for i in range(1536))

async def safe_db_execute(url, conn, query, *params):
    """Wrapper til at udføre databaseforespørgsler med fejlbehandling."""
    try:
        return await conn.fetchval(query, *params)
    except Exception as e:
        logging.exception(f"Databasefejl ved query '{query}' for {url}: {e}")
        return None


async def save_book(book, conn):
    """Gem bogens metadata, tekst og embeddings i databasen."""
    try:
        async with conn.transaction():
            # Indsæt metadata om bogen
            result = await safe_db_execute(
                book["pdf-url"],
                conn,
                """
                INSERT INTO books (pdf_navn, titel, forfatter, antal_sider)
                VALUES ($1, $2, $3, $4) RETURNING id
                """,
                book["pdf-url"],
                book["titel"],
                book["forfatter"],
                book["sider"],
            )
            book_id = result

            # Indsæt tekst-chunks og embeddings
            for (page_num, chunk_text), embedding in zip(
                book["chunks"], book["embeddings"]
            ):
                await safe_db_execute(
                    book["pdf-url"],
                    conn,
                    """
                    INSERT INTO chunks (book_id, sidenr, chunk, embedding)
                    VALUES ($1, $2, $3, $4)
                    """,
                    book_id,
                    page_num,
                    chunk_text,
                    json.dumps(embedding),
                )
    except Exception as e:
        logging.exception(
            f"Fejl ved indsættelse af bog {book['pdf-url']} i databasen: {e}"
        )
        raise

async def parse_book(pdf, book_url, chunk_size, embedding_provider):
    """Udtræk tekst fra PDF, opdel i chunks, generer embeddings."""
    try:
        metadata = pdf.metadata or {}  # Håndter manglende metadata
        book = {
            "pdf-url": book_url,
            "titel": metadata.get("title", "Ukendt Titel"),
            "forfatter": metadata.get("author", "Ukendt Forfatter"),
            "sider": len(pdf),
            "chunks": [],
            "embeddings": [],
        }

        pdf_pages = extract_text_by_page(pdf)

        for page_num, page_text in pdf_pages.items():
            for chunk in chunk_text(page_text, chunk_size):
                if chunk.strip():  # Ignorer tomme chunks
                    chunk_with_metadata = f"##{book['titel']}##{chunk}"
                    book["chunks"].append((page_num, chunk_with_metadata))
                    embedding = await embedding_provider.get_embedding(chunk_with_metadata)
                    book["embeddings"].append(embedding)
    finally:
        pdf.close()  # Luk PDF for at frigøre ressourcer

    return book


async def process_book(book_url, chunk_size, pool, session, embedding_provider):
    """Behandl en enkelt bog fra URL til database."""
    try:
        async with pool.acquire() as conn:
            # Check om bogen allerede findes i databasen FØRST
            result = await safe_db_execute(
                book_url,
                conn,
                "SELECT id FROM books WHERE pdf_navn = $1",
                book_url,
            )
            if result:
                logging.info(f"Bogen {book_url} er allerede i databasen - springer over")
                return
            
            # Hvis bogen ikke findes, hent PDF og behandl den
            pdf = await fetch_pdf(book_url, session)
            
            if pdf:
                book = await parse_book(pdf, book_url, chunk_size, embedding_provider)
                await save_book(book, conn)
                logging.info(f"{book['titel']} fra {book_url} er behandlet og gemt i databasen")
            else:
                logging.warning(f"Kunne ikke hente PDF fra {book_url}")
                
    except Exception as e:
        logging.exception(f"Fejl ved behandling af {book_url}: {type(e).__name__}")


async def main():
    """Hovedfunktion for at hente og behandle alle bøger."""
    load_dotenv(override=True)
    database = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    api_key = os.getenv("OPENAI_API_KEY")
    provider = os.getenv("PROVIDER")
    chunk_size = int(os.getenv("CHUNK_SIZE"))
    url_file = os.getenv("URL_FILE")
    
    embedding_provider = EmbeddingProviderFactory.create_provider(provider, api_key)

    # Configure logging using shared configuration
    setup_logging(log_dir=os.getenv("LOG_DIR"))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    url_file_path = os.path.join(script_dir, url_file)
    book_urls = indlæs_urls(url_file_path)

    # Opret asynkrone forbindelser
    try:
        async with asyncpg.create_pool(
            host="localhost", database=database, user=db_user, password=db_password
        ) as pool:
            try:
                ssl_context = ssl.create_default_context()
                async with aiohttp.ClientSession(
                    connector=TCPConnector(ssl=ssl_context)
                ) as session:
                    # Begræns antal samtidige opgaver
                    semaphore = asyncio.Semaphore(5)
                    tasks = [
                        asyncio.create_task(
                            semaphore_guard(
                                process_book, semaphore, url, chunk_size, pool, session, embedding_provider
                            )
                        )
                        for url in book_urls
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)
            finally:
                try:
                    await asyncio.wait_for(pool.close(), timeout=60)
                except asyncio.TimeoutError:
                    logging.warning(
                        "Poolen lukkede ikke inden for timeout-perioden (60 sekunder)"
                    )
    except Exception as e:
        logging.exception(f"Fatal fejl i hovedprogrammet: {type(e).__name__}")


async def semaphore_guard(coro, semaphore, *args):
    """Hjælpefunktion til at begrænse samtidige opgaver."""
    async with semaphore:
        await coro(*args)


if __name__ == "__main__":
    asyncio.run(main())
