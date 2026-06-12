import streamlit as st
import fitz
import chromadb
from chromadb.config import Settings
import sqlite3
import os
import hashlib
from datetime import datetime
from pathlib import Path
import shutil

PDF_FOLDER = os.getenv("PDF_FOLDER", "./pdfs")
CHROMA_PATH = "./chroma_db"
SQLITE_PATH = "./knowledge.db"

st.set_page_config(page_title="PDF Knowledge Extractor", page_icon="📚", layout="wide")


def init_db():
    if "db" not in st.session_state:
        st.session_state.chroma = chromadb.Client(
            Settings(persist_directory=CHROMA_PATH, anonymized_telemetry=False)
        )

        st.session_state.conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
        st.session_state.conn.execute("""
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
        st.session_state.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id TEXT PRIMARY KEY,
                pdf_id TEXT,
                chunk_text TEXT,
                page_number INTEGER,
                category TEXT,
                created_at TEXT
            )
        """)
        st.session_state.conn.commit()


init_db()

st.title("📚 PDF Knowledge Extractor")
st.markdown("### RAG System for 100+ Books - Extract the 20% That Moves the 80%")

with st.sidebar:
    st.header("📁 PDF Management")

    st.info(f"PDF Folder: {PDF_FOLDER}")

    if st.button("📂 Open PDF Folder"):
        os.startfile(PDF_FOLDER)

    uploaded_files = st.file_uploader(
        "Upload PDF files", type=["pdf"], accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("🚀 Process Uploaded PDFs"):
            with st.spinner("Saving PDFs..."):
                for pdf in uploaded_files:
                    pdf_path = os.path.join(PDF_FOLDER, pdf.name)
                    with open(pdf_path, "wb") as f:
                        f.write(pdf.read())
                st.success(f"Saved {len(uploaded_files)} PDFs!")

    if st.button("⚡ Process All PDFs in Folder"):
        with st.spinner("Processing all PDFs..."):
            process_all_pdfs()
        st.success("All PDFs processed!")

    st.divider()

    st.subheader("📊 Statistics")
    cursor = st.session_state.conn.execute("SELECT COUNT(*) FROM pdf_metadata")
    pdf_count = cursor.fetchone()[0]
    st.metric("PDFs Processed", pdf_count)

    cursor = st.session_state.conn.execute("SELECT COUNT(*) FROM knowledge_chunks")
    chunk_count = cursor.fetchone()[0]
    st.metric("Knowledge Chunks", chunk_count)


def process_all_pdfs():
    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]

    for filename in pdf_files:
        pdf_path = os.path.join(PDF_FOLDER, filename)
        process_single_pdf(pdf_path)


def process_single_pdf(pdf_path):
    filename = os.path.basename(pdf_path)

    # Check if already processed
    pdf_hash = hashlib.md5(open(pdf_path, "rb").read()).hexdigest()
    cursor = st.session_state.conn.execute(
        "SELECT hash FROM pdf_metadata WHERE hash = ?", (pdf_hash,)
    )
    if cursor.fetchone():
        return

    try:
        doc = fitz.open(pdf_path)

        pdf_id = pdf_hash[:8]
        metadata = doc.metadata
        title = metadata.get("title", "") or filename
        author = metadata.get("author", "Unknown")

        st.session_state.conn.execute(
            """
            INSERT INTO pdf_metadata VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (pdf_id, filename, title, author, len(doc), datetime.now(), pdf_hash),
        )

        chunk_size = 800
        overlap = 80

        for page_num, page in enumerate(doc):
            text = page.get_text()
            text = text.replace("\n", " ").strip()
            text = " ".join(text.split())

            for i in range(0, len(text), chunk_size - overlap):
                chunk = text[i : i + chunk_size]

                if len(chunk) < 50:
                    continue

                category = categorize_chunk(chunk)
                chunk_id = f"{pdf_id}_p{page_num}_c{i // chunk_size}"

                st.session_state.conn.execute(
                    """
                    INSERT INTO knowledge_chunks VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (chunk_id, pdf_id, chunk, page_num + 1, category, datetime.now()),
                )

        st.session_state.conn.commit()

    except Exception as e:
        st.error(f"Error: {e}")


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
        "Rapport": ["rapport", "connect", "relationship", "trust", "build", " rapport"],
        "Negotiation": ["negotiate", "bargain", "deal", "terms", "leverage", "anchor"],
        "Value": ["value", "benefit", "worth", "roi", "return", "investment"],
        "Authority": ["authority", "expert", "know", "experience", "years", "proven"],
    }

    for cat, keywords in categories.items():
        if any(kw in lower for kw in keywords):
            return cat

    return "General"


def process_single_pdf(pdf_path):
    filename = os.path.basename(pdf_path)

    pdf_hash = hashlib.md5(open(pdf_path, "rb").read()).hexdigest()
    cursor = st.session_state.conn.execute(
        "SELECT hash FROM pdf_metadata WHERE hash = ?", (pdf_hash,)
    )
    if cursor.fetchone():
        return

    try:
        doc = fitz.open(pdf_path)

        pdf_id = pdf_hash[:8]
        metadata = doc.metadata
        title = metadata.get("title", "") or filename
        author = metadata.get("author", "Unknown")

        st.session_state.conn.execute(
            """
            INSERT INTO pdf_metadata VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (pdf_id, filename, title, author, len(doc), datetime.now(), pdf_hash),
        )

        chunk_size = 800
        overlap = 80

        for page_num, page in enumerate(doc):
            text = page.get_text()
            text = text.replace("\n", " ").strip()
            text = " ".join(text.split())

            for i in range(0, len(text), chunk_size - overlap):
                chunk = text[i : i + chunk_size]

                if len(chunk) < 50:
                    continue

                category = categorize_chunk(chunk)
                chunk_id = f"{pdf_id}_p{page_num}_c{i // chunk_size}"

                st.session_state.conn.execute(
                    """
                    INSERT INTO knowledge_chunks VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (chunk_id, pdf_id, chunk, page_num + 1, category, datetime.now()),
                )

        st.session_state.conn.commit()

    except Exception as e:
        st.error(f"Error: {e}")


def process_all_pdfs():
    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]

    for filename in pdf_files:
        pdf_path = os.path.join(PDF_FOLDER, filename)
        process_single_pdf(pdf_path)


def search_knowledge(query, num_results=5):
    query_lower = query.lower()
    keywords = query_lower.split()

    if not keywords:
        return []

    search_term = f"%{keywords[0]}%"
    for kw in keywords[1:]:
        search_term = f"%{kw}%" + search_term[1:-1] + f"%{kw}%"

    search_term = search_term[:200]

    cursor = st.session_state.conn.execute(
        f"""
        SELECT chunk_text, pdf_id, page_number, category 
        FROM knowledge_chunks 
        WHERE chunk_text LIKE ?
        LIMIT ?
    """,
        (search_term, num_results),
    )

    results = cursor.fetchall()

    return [
        {"text": r[0], "source": r[1], "page": r[2], "category": r[3]} for r in results
    ]


tab1, tab2, tab3 = st.tabs(["🔍 Query", "📚 Library", "🏆 Best Of"])

with tab1:
    st.header("Ask Anything - RAG Query")

    col1, col2 = st.columns([3, 1])

    with col1:
        query = st.text_input(
            "Ask a question:",
            placeholder="e.g., What's the best closing technique for car sales?",
        )

    with col2:
        num_results = st.slider("Results", 1, 10, 5)

    if query:
        with st.spinner("Searching knowledge base..."):
            search_results = search_knowledge(query, num_results)

            if search_results:
                st.success(f"Found {len(search_results)} relevant chunks")

                for i, result in enumerate(search_results):
                    with st.container():
                        st.markdown(f"### 📌 Result {i + 1}")
                        st.write(result["text"])
                        st.caption(
                            f"Source: {result['source']} | Page {result['page']} | Category: {result['category']}"
                        )
                        st.divider()
            else:
                st.warning("No results found. Try different keywords.")


def search_knowledge(query, num_results=5):
    query_lower = query.lower()

    keywords = query_lower.split()
    if keywords:
        search_term = f"%{keywords[0]}%"
        for kw in keywords[1:]:
            search_term = f"%{kw}%{search_term[1:-1]}%{kw}%"

        cursor = st.session_state.conn.execute(
            f"""
            SELECT chunk_text, pdf_id, page_number, category 
            FROM knowledge_chunks 
            WHERE chunk_text LIKE ?
            LIMIT ?
        """,
            (search_term[:200], num_results),
        )

        results = cursor.fetchall()

        return [
            {"text": r[0], "source": r[1], "page": r[2], "category": r[3]}
            for r in results
        ]

    return []


with tab2:
    st.header("📚 PDF Library")

    cursor = st.session_state.conn.execute(
        "SELECT * FROM pdf_metadata ORDER BY processed_at DESC"
    )
    pdfs = cursor.fetchall()

    if pdfs:
        for pdf in pdfs:
            with st.expander(f"📄 {pdf[1]}"):
                st.markdown(f"""
                - **Title:** {pdf[2]}
                - **Author:** {pdf[3]}
                - **Pages:** {pdf[4]}
                - **Processed:** {pdf[5]}
                """)
    else:
        st.info(
            "No PDFs processed yet. Upload PDFs or click 'Process All PDFs in Folder'."
        )

with tab3:
    st.header("🏆 The 20% That Moves the 80%")

    st.markdown("### Pareto Principle for Sales: 20% of techniques = 80% of results")

    categories = [
        "Closing",
        "Objection Handling",
        "Prospecting",
        "Follow-up",
        "Rapport",
        "Negotiation",
        "Value",
        "Authority",
    ]

    selected_cat = st.selectbox("Select Category:", categories)

    if st.button("🏆 Extract Best Techniques"):
        with st.spinner("Finding the gold..."):
            cursor = st.session_state.conn.execute(
                """
                SELECT chunk_text, pdf_id, page_number 
                FROM knowledge_chunks 
                WHERE category = ?
                LIMIT 20
            """,
                (selected_cat,),
            )

            results = cursor.fetchall()

            if results:
                st.success(f"Found {len(results)} {selected_cat} techniques!")

                for i, (text, pdf_id, page) in enumerate(results):
                    with st.expander(f"### {i + 1}. {selected_cat} Technique"):
                        st.write(text)

                        # Get source filename
                        cursor = st.session_state.conn.execute(
                            "SELECT filename FROM pdf_metadata WHERE id = ?", (pdf_id,)
                        )
                        source = cursor.fetchone()
                        if source:
                            st.caption(f"📚 Source: {source[0]}")
            else:
                st.warning(f"No {selected_cat} techniques found. Try another category.")

if __name__ == "__main__":
    os.makedirs(PDF_FOLDER, exist_ok=True)
    os.makedirs(CHROMA_PATH, exist_ok=True)
