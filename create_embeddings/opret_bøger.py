import asyncio
import aiohttp
import psycopg2
import pymupdf
from openai import AsyncOpenAI
from tqdm import tqdm
from dotenv import load_dotenv
import os
import re
from concurrent.futures import ThreadPoolExecutor

CHUNK_SIZE = 300
URL_FILE = "samlet_input.txt"
MODEL = "text-embedding-3-small"


def indlæs_urls(file_path):
    with open(file_path, "r") as file:
        return [line.strip() for line in file]


async def fetch_pdf(url, session) -> pymupdf.Document:
    try:
        async with session.get(url) as response:
            if response.status == 200:
                raw_pdf = await response.read()
                return pymupdf.open("pdf", raw_pdf.content)
            else:
                print(f"Fejl ved hentning af {url}: Statuskode {response.status}")
                return None
    except aiohttp.ClientError as e:
        print(f"Netværksfejl ved hentning af {url}: {e}")
        return None


def extract_text_by_page(pdf) -> dict:
    pages_text = {}
    page_num = 1
    for page in pdf[1:]:
        text = page.get_text()
        pages_text[page_num] = (
            text.replace(
                " \xad\n", ""
            )  # \xad = blødt mellemrum/linjeskift ( '-' er skjult hvis ikke linjeskift)
            .replace("\xad\n", "")
            .replace(
                "-\n", ""
            )  # '-' = hårdt mellemrum/linjeskift ( '-' er altid synlig)
            .replace("- \n", "")
        )
        page_num += 1
    return pages_text


def clean_text(text) -> str:
    text = (
        text.replace("..", ".")
        .replace("  ", " ")
        .replace(" \xad", " ")
        .replace("- \n", "")
        .replace("-\n", "")
        .replace("\n", "")
        .strip()
    )
    return text


def chunk_text(text, max_tokens=CHUNK_SIZE):
    text = clean_text(text)
    # Split text into sentences based on punctuation followed by a space
    sentences = re.split(r"(?<=[.!?]) +", text)
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        token_count = len(sentence.split())
        if current_length + token_count > max_tokens:
            yield " ".join(current_chunk)
            current_chunk = [sentence]
            current_length = token_count
        else:
            current_chunk.append(sentence)
            current_length += token_count

    if current_chunk:
        yield " ".join(current_chunk)


def extract_text_from_chunk(raw_chunk: str) -> tuple:
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


async def get_embedding(chunk, client, model=MODEL):
    data = await client.embeddings.create(input=chunk, model=model).data
    return data[0].embedding
    # return list(i / 10000 for i in range(1536))


async def save_book(book, database, db_user, db_password) -> None:
    async with await psycopg2.AsyncConnection.connect(
        host="localhost",
        database=database,
        user=db_user,
        password=db_password,
    ) as conn:
        async with conn.cursor() as cur:
            like_pattern = f"%{book['pdf-url']}"
            await cur.execute(
                "SELECT id FROM books where pdf_navn like %s", (like_pattern,)
            )

            if cur.rowcount == 0:
                print(f"Ny bog oprettet: {book["pdf-url"]} {book["titel"]}")
                await cur.execute(
                    "INSERT INTO books(pdf_navn, titel, forfatter, antal_sider) "
                    + "VALUES (%s, %s, %s, %s) RETURNING id",
                    (book["pdf-url"], book["titel"], book["forfatter"], book["sider"]),
                )

            book_id = await cur.fetchone()[0]

            for (sidenr, chunk), embedding in zip(book["chunks"], book["embeddings"]):
                chunk_tekst = extract_text_from_chunk(chunk)

                await cur.execute(
                    "INSERT INTO chunks(book_id, sidenr, chunk, embedding) "
                    + "VALUES (%s, %s, %s, %s)",
                    (book_id, sidenr, chunk_tekst, embedding),
                )

            await conn.commit()
            await cur.close()
            await conn.close()


async def parse_book(pdf, book_url, session, api_key):
    # hent tekst fra pdf, chunk, generer embeddings og gem i db
    metadata = pdf.metadata
    book = {
        "pdf-url": book_url,
        "titel": metadata["title"],
        "forfatter": metadata["author"],
        "sider": len(pdf),
        "chunks": [],
        "embeddings": [],
    }

    pdf_pages = extract_text_by_page(pdf)
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", None))

    for page_num, page_text in tqdm(pdf_pages.items(), desc=f"Chunking"):
        chunks = chunk_text(page_text)
        for chunk in chunks:
            if chunk.strip() == "":
                continue
            # embed_text = f"{chunk}"
            embed_text = f"##{metadata['title']}##{chunk}"
            book["chunks"].append((page_num, embed_text))
            embedding = await get_embedding(embed_text, session, openai_client)
            book["embeddings"].append(embedding)


async def process_book(book_url, api_key, db_conn):
    # henter pdf asynkront, chunker, genere embedding, gem i db
    async with aiohttp.ClientSession() as session:
        pdf = await fetch_pdf(book_url, session)
        if pdf:
            print(f"PDF filen ({book_url}) er hentet succesfuldt")
            book = await parse_book(pdf, book_url, session, api_key)
        else:
            print(f"Kunne ikke hente PDF-filen. Url: {book_url}")

        await save_book(book, database, db_user, db_password)


async def main():
    load_dotenv()
    global database, db_user, db_password
    database = os.getenv("POSTGRES_DB", None)
    db_user = os.getenv("POSTGRES_USER", None)
    db_password = os.getenv("POSTGRES_PASSWORD", None)

    api_key = os.getenv("OPENAI_API_KEY", None)
    book_urls = indlæs_urls(URL_FILE)

    async with aiohttp.ClientSession() as session:
        with psycopg2.connect(
            host="localhost",
            database=database,
            user=db_user,
            password=db_password,
        ) as conn:
            with ThreadPoolExecutor(max_workers=10) as executor:  # juster max_workers
                tasks = [
                    process_book(url, api_key, conn, session, executor)
                    for url in book_urls
                ]
                await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
