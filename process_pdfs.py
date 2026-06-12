import fitz
import sqlite3
import os
import hashlib
from datetime import datetime

PDF_FOLDER = os.getenv("PDF_FOLDER", "./pdfs")
SQLITE_PATH = "./knowledge.db"


def process_single_pdf(pdf_path, conn):
    filename = os.path.basename(pdf_path)

    pdf_hash = hashlib.md5(open(pdf_path, "rb").read()).hexdigest()

    cursor = conn.execute("SELECT hash FROM pdf_metadata WHERE hash = ?", (pdf_hash,))
    if cursor.fetchone():
        print(f"Already processed: {filename}")
        return False

    try:
        doc = fitz.open(pdf_path)

        pdf_id = pdf_hash[:8]
        metadata = doc.metadata

        if metadata:
            title = metadata.get("title", "") or filename
            author = metadata.get("author", "Unknown")
        else:
            title = filename
            author = "Unknown"

        conn.execute(
            """
            INSERT INTO pdf_metadata VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (pdf_id, filename, title, author, len(doc), datetime.now(), pdf_hash),
        )

        print(f"Processed: {filename} ({len(doc)} pages)")

        chunk_size = 800
        overlap = 80

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            text = text.replace("\n", " ").strip()
            text = " ".join(text.split())

            for i in range(0, len(text), chunk_size - overlap):
                chunk = text[i : i + chunk_size]

                if len(chunk) < 50:
                    continue

                category = categorize_chunk(chunk)
                chunk_id = f"{pdf_id}_p{page_num}_c{i // chunk_size}"

                try:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO knowledge_chunks VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            chunk_id,
                            pdf_id,
                            chunk,
                            page_num + 1,
                            category,
                            datetime.now(),
                        ),
                    )
                except:
                    pass

        conn.commit()
        print(f"Done: {filename}")
        return True

    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return False


def categorize_chunk(text):
    lower = text.lower()

    categories = {
        "Closing": [
            "close",
            "sale",
            "buy",
            "purchase",
            "sign",
            "deal done",
            "yes",
            "commit",
        ],
        "Objection Handling": [
            "objection",
            "but ",
            "think about",
            "expensive",
            "too much",
            "need to",
            "handle",
        ],
        "Prospecting": [
            "prospect",
            "lead",
            "contact",
            "cold call",
            "reach out",
            "initial",
            "find",
        ],
        "Follow-up": [
            "follow up",
            "follow-up",
            "call back",
            "check in",
            "reminder",
            "sequence",
            "reach",
        ],
        "Rapport": [
            "rapport",
            "connect",
            "relationship",
            "trust",
            "build",
            " rapport",
            " rapport",
        ],
        "Negotiation": [
            "negotiate",
            "bargain",
            "deal",
            "terms",
            "leverage",
            "anchor",
            "trade",
        ],
        "Value": ["value", "benefit", "worth", "roi", "return", "investment", "save"],
        "Authority": [
            "authority",
            "expert",
            "know",
            "experience",
            "years",
            "proven",
            "master",
        ],
    }

    for cat, keywords in categories.items():
        if any(kw in lower for kw in keywords):
            return cat

    return "General"


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pdf_metadata (
            id TEXT PRIMARY KEY,
            filename TEXT,
            title TEXT,
            author TEXT,
            pages INTEGER,
            processed_at TEXT,
            hash TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id TEXT PRIMARY KEY,
            pdf_id TEXT,
            chunk_text TEXT,
            page_number INTEGER,
            category TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.commit()


def main():
    os.makedirs(PDF_FOLDER, exist_ok=True)

    conn = sqlite3.connect(SQLITE_PATH)
    init_db(conn)

    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]

    print(f"\nFound {len(pdf_files)} PDFs in {PDF_FOLDER}")
    print("=" * 50)

    for filename in pdf_files:
        pdf_path = os.path.join(PDF_FOLDER, filename)
        process_single_pdf(pdf_path, conn)

    # Summary
    print("SUMMARY")

    cursor = conn.execute("SELECT COUNT(*) FROM pdf_metadata")
    pdf_count = cursor.fetchone()[0]
    print(f"   PDFs: {pdf_count}")

    cursor = conn.execute("SELECT COUNT(*) FROM knowledge_chunks")
    chunk_count = cursor.fetchone()[0]
    print(f"   Chunks: {chunk_count}")

    print("\nBy Category:")
    cursor = conn.execute(
        "SELECT category, COUNT(*) FROM knowledge_chunks GROUP BY category ORDER BY COUNT(*) DESC"
    )
    for row in cursor:
        print(f"   {row[0]}: {row[1]}")

    conn.close()
    print("\nProcessing complete! Run 'streamlit run app.py' to use the UI.")


if __name__ == "__main__":
    main()
