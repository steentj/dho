import requests
import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pymupdf
from openai import OpenAI
import psycopg2
from tqdm import tqdm

CHUNK_SIZE = 400
CHUNK_OVERLAP = CHUNK_SIZE * 0.1
CHUNK_PAGE_COUNT = 3


def get_local_pdf_files():
    for pdf_file in filter(
        lambda x: x.endswith(".pdf") and not x.startswith("#"), os.listdir("pdf")
    ):
        try:
            yield (pdf_file, pymupdf.open(f"pdf/{pdf_file}"))
        except Exception as e:
            print(f"Fejl ved indlæsning af {pdf_file}: {e}")


def clean_text(text) -> str:
    text = (
        text.replace("..", ".")
        .replace("  ", " ")
        .replace("\n ", "\n")
        .replace("\n\n\n\n", "\n\n")
        .replace("\n\n\n", "\n\n")
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


def make_chunk_sections(pdf) -> list:
    chunk_batch = ""
    chunk_page = 0
    page_no = 0
    chunk_sections = []

    for page in pdf[1:]:
        page_no += 1
        chunk_page += 1
        chunk_batch += page.get_text()
        if chunk_page >= CHUNK_PAGE_COUNT:
            chunk_sections.append((page_no - chunk_page, clean_text(chunk_batch)))
            chunk_batch = ""
            chunk_page = 0

    if len(chunk_batch) > 0:
        chunk_sections.append((page_no - chunk_page, clean_text(chunk_batch)))

    return chunk_sections


def get_embedding(texts, client, model="text-embedding-3-small"):
    text = (t.replace("\n", " ") for t in texts)
    data = client.embeddings.create(input=text, model=model).data
    return data[0].embedding
    # return list(i/10000 for i in range(1536))


def extract_text_from_chunk(raw_chunk: str) -> tuple:
    parts = raw_chunk.split("##")
    text = parts[2]

    return text


def save_book(book, database, db_user, db_password) -> None:
    cn = psycopg2.connect(
        host="localhost",
        database=database,
        user=db_user,
        password=db_password,
    )

    cur = cn.cursor()

    cur.execute(
        "INSERT INTO books(pdf_navn, titel, forfatter, antal_sider) "
        + "VALUES (%s, %s, %s, %s) RETURNING id",
        (book["pdf-url"], book["titel"], book["forfatter"], book["sider"]),
    )

    book_id = cur.fetchone()[0]

    for (sidenr, chunk), embedding in zip(book["chunks"], book["embeddings"]):
        chunk_tekst = extract_text_from_chunk(chunk)
        cur.execute(
            "INSERT INTO chunks(book_id, sidenr, chunk, embedding) "
            + "VALUES (%s, %s, %s, %s)",
            (book_id, sidenr, chunk_tekst, embedding),
        )

    cn.commit()
    cur.close()
    cn.close()


def handle_pdf_files(get_books, database, db_user, db_password):
    for pdf_url, pdf in tqdm(get_books, desc="Bøger"):
        metadata = pdf.metadata
        print(f"Indlæser {pdf_url.decode('utf-8')}: {metadata['title']}")
        book = {
            "pdf-url": str(pdf_url.decode("utf-8")),  # pdf_url,
            "titel": metadata["title"],
            "forfatter": metadata["author"],
            "sider": len(pdf),
            "chunks": [],
            "embeddings": [],
        }

        chunk_sections = make_chunk_sections(pdf)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )

        for chunk_section in tqdm(
            chunk_sections, desc=f"Sektion på {CHUNK_PAGE_COUNT} sider"
        ):
            page_no, section_text = chunk_section
            chunks = text_splitter.split_text(section_text)

            for chunk in chunks:
                embed_text = f"##{metadata['title']}##{chunk}"
                book["chunks"].append((page_no, embed_text))
                book["embeddings"].append(get_embedding(embed_text, OpenAI()))

        save_book(book, database, db_user, db_password)


def main():
    # openai_key = os.getenv("OPENAI_API_KEY", None)
    # openai.api_key = openai_key
    # client = OpenAI()
    load_dotenv()
    database = os.getenv("POSTGRES_DB", None)
    db_user = os.getenv("POSTGRES_USER", None)
    db_password = os.getenv("POSTGRES_PASSWORD", None)

    handle_pdf_files(get_pdf_files(), database, db_user, db_password)


if __name__ == "__main__":
    main()
