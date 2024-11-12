import requests
import os
from dotenv import load_dotenv
import pymupdf
from openai import OpenAI
import psycopg2
from tqdm import tqdm
import re

CHUNK_SIZE = 500


def get_local_pdf_files():
    for pdf_file in filter(lambda x: x.endswith(".pdf"), os.listdir("pdf")):
        try:
            yield (pdf_file, pymupdf.open(f"pdf/{pdf_file}"))
        except Exception as e:
            print(f"Fejl ved indlæsning af {pdf_file}: {e}")


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


def get_pdf_files():
    with open("samlet_input.txt", "rb") as pdfer:
        for url in filter(lambda x: not x[0] == "#", pdfer):
            url = url.strip()

            try:
                r = requests.get(url)
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print(f"HTTP-fejl opstod: {e}")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"Forbindelsesfejl opstod: {e}")
                continue
            except requests.exceptions.Timeout as e:
                print(f"Timeout-fejl opstod: {e}")
                continue
            except requests.exceptions.RequestException as e:
                print(f"En ukendt fejl opstod: {e}")
                continue

            yield (url, pymupdf.open("pdf", r.content))


def extract_text_by_page(pdf) -> dict:
    pages_text = {}
    page_num = 1
    for page in pdf[1:]:
        text = page.get_text()
        pages_text[page_num] = (
            text.replace(" \xad\n", "") # \xad = blødt mellemrum/linjeskift ( '-' er skjult hvis ikke linjeskift)
            .replace("\xad\n", "")
            .replace("-\n", "")         # '-' = hårdt mellemrum/linjeskift ( '-' er altid synlig)
            .replace("- \n", "")
        )
        page_num += 1
    return pages_text


def get_embedding(texts, client, model="text-embedding-3-small"):
    data = client.embeddings.create(input=texts, model=model).data
    return data[0].embedding
    # return list(i / 10000 for i in range(1536))


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


def chunk_text(text, max_tokens=CHUNK_SIZE):
    text = clean_text(text)
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


def save_book(book, database, db_user, db_password) -> None:
    cn = psycopg2.connect(
        host="localhost",
        database=database,
        user=db_user,
        password=db_password,
    )

    cur = cn.cursor()

    like_pattern = f"%{book['pdf-url']}"
    cur.execute("SELECT id FROM books where pdf_navn like %s", (like_pattern,))

    if cur.rowcount == 0:
        print(f"Ny bog oprettet: {book["pdf-url"]} {book["titel"]}")
        cur.execute(
            "INSERT INTO books(pdf_navn, titel, forfatter, antal_sider) "
            + "VALUES (%s, %s, %s, %s) RETURNING id",
            (book["pdf-url"], book["titel"], book["forfatter"], book["sider"]),
        )

    book_id = cur.fetchone()[0]
 
    for (sidenr, chunk), embedding in zip(book["chunks"], book["embeddings"]):
        chunk_tekst = extract_text_from_chunk(chunk)

        # cur.execute(
        #     "INSERT INTO chunks_large(book_id, sidenr, chunk, embedding) "
        #     + "VALUES (%s, %s, %s, %s)",
        #     (book_id, sidenr, chunk_tekst, embedding),
        # )
        # cur.execute(
        #     "INSERT INTO chunks_small(book_id, sidenr, chunk, embedding) "
        #     + "VALUES (%s, %s, %s, %s)",
        #     (book_id, sidenr, chunk_tekst, embedding),
        # )
        # cur.execute(
        #     "INSERT INTO chunks(book_id, sidenr, chunk, embedding) "
        #     + "VALUES (%s, %s, %s, %s)",
        #     (book_id, sidenr, chunk_tekst, embedding),
        # )
        # cur.execute(
        #     "INSERT INTO chunks_tiny(book_id, sidenr, chunk, embedding) "
        #     + "VALUES (%s, %s, %s, %s)",
        #     (book_id, sidenr, chunk_tekst, embedding),
        # )

        cur.execute(
            "INSERT INTO chunks_udentitel(book_id, sidenr, chunk, embedding) "
            + "VALUES (%s, %s, %s, %s)",
            (book_id, sidenr, chunk_tekst, embedding),
        )
    cn.commit()
    cur.close()
    cn.close()


def handle_pdf_files(get_books, database, db_user, db_password, openai_client) -> None:
    for pdf_url, pdf in tqdm(get_books, desc="Bøger"):
        metadata = pdf.metadata
        print(f"Indlæser {pdf_url}: {metadata['title']}")
        book = {
            "pdf-url": pdf_url,  
            "titel": metadata["title"],
            "forfatter": metadata["author"],
            "sider": len(pdf),
            "chunks": [],
            "embeddings": [],
        }

        pdf_pages = extract_text_by_page(pdf)     

        for page_no, page_text in tqdm(pdf_pages.items(), desc=f"Chunking"):
            chunks = chunk_text(page_text)

            for chunk in chunks:
                if chunk.strip() == "":
                    continue
                embed_text = f"{chunk}"
                # embed_text = f"##{metadata['title']}##{chunk}"
                book["chunks"].append((page_no, embed_text))
                book["embeddings"].append(get_embedding(embed_text, openai_client))

        save_book(book, database, db_user, db_password)


def main():
    load_dotenv()
    database = os.getenv("POSTGRES_DB", None)
    db_user = os.getenv("POSTGRES_USER", None)
    db_password = os.getenv("POSTGRES_PASSWORD", None)

    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", None))

    handle_pdf_files(get_local_pdf_files(), database, db_user, db_password, openai_client)


if __name__ == "__main__":
    main()
