# PDF Knowledge Extractor

A local-first **RAG system for your PDF library**. Point it at a folder of PDFs
(books, papers, manuals), and it extracts the text, embeds it into a local vector
store, and lets you semantically search and query across your whole collection —
no cloud, no API keys, your data stays on your machine.

Built by [ABUZ8 LLC](https://abuz8ai.com). MIT licensed.

## Stack

- **Streamlit** — the UI
- **PyMuPDF (`fitz`)** — fast PDF text extraction
- **ChromaDB** — local vector store / semantic search
- **SQLite** — metadata + dedupe (hashes each PDF so re-runs skip processed files)

## Quick start

```bash
pip install -r requirements.txt

# point it at your PDFs (default: ./pdfs)
export PDF_FOLDER=./pdfs        # Windows: set PDF_FOLDER=.\pdfs

streamlit run app.py
```

Then open the local URL Streamlit prints. Drop PDFs into `PDF_FOLDER`, click to
ingest, and search across everything.

## Files

| File | What it does |
|------|--------------|
| `app.py` | Streamlit UI — ingest, browse, semantic search |
| `process_pdfs.py` | Batch-extract a folder of PDFs into the DB (CLI) |
| `native_app.py` | Native-window variant |
| `launch_app.py` | Convenience launcher |

## Config

| Env var | Default | Meaning |
|---------|---------|---------|
| `PDF_FOLDER` | `./pdfs` | Folder to read PDFs from |

`knowledge.db` and `chroma_db/` are created locally and gitignored — your library
and its index never leave your machine.

## Why

If you've got 100+ books or papers, the value is the 20% that moves the 80% — but
you can't find it by scrolling. This makes the whole library queryable in seconds,
fully offline.
