# PDF KNOWLEDGE EXTRACTOR - Native Desktop GUI
# This version uses CustomTkinter for a native-looking desktop app
# Can be packaged to .exe with PyInstaller

import customtkinter as ctk
import fitz
import sqlite3
import os
import hashlib
from datetime import datetime
from tkinter import filedialog, messagebox
import threading

# Config
PDF_FOLDER = os.getenv("PDF_FOLDER", "./pdfs")
SQLITE_PATH = "./knowledge.db"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class PDFKnowledgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PDF Knowledge Extractor")
        self.geometry("1200x800")

        self.init_db()
        self.create_widgets()
        self.load_stats()

    def init_db(self):
        self.conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
        self.conn.execute("""
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
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id TEXT PRIMARY KEY,
                pdf_id TEXT,
                chunk_text TEXT,
                page_number INTEGER,
                category TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()

    def create_widgets(self):
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="PDF KNOWLEDGE EXTRACTOR\nThe 20% That Moves the 80%",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.title_label.pack(pady=20)

        # Stats Frame
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.pack(pady=10, padx=20, fill="x")

        self.pdf_count_label = ctk.CTkLabel(
            self.stats_frame, text="PDFs: 0", font=ctk.CTkFont(size=16)
        )
        self.pdf_count_label.pack(side="left", padx=20, pady=10)

        self.chunk_count_label = ctk.CTkLabel(
            self.stats_frame, text="Chunks: 0", font=ctk.CTkFont(size=16)
        )
        self.chunk_count_label.pack(side="left", padx=20, pady=10)

        # Buttons Frame
        self.buttons_frame = ctk.CTkFrame(self)
        self.buttons_frame.pack(pady=10, padx=20, fill="x")

        self.process_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Process PDFs",
            command=self.process_pdfs,
            fg_color="green",
        )
        self.process_btn.pack(side="left", padx=10, pady=10)

        self.add_btn = ctk.CTkButton(
            self.buttons_frame, text="Add PDFs", command=self.add_pdfs
        )
        self.add_btn.pack(side="left", padx=10, pady=10)

        self.refresh_btn = ctk.CTkButton(
            self.buttons_frame, text="Refresh", command=self.load_stats
        )
        self.refresh_btn.pack(side="left", padx=10, pady=10)

        # Search Frame
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.pack(pady=10, padx=20, fill="x")

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Ask anything... (e.g., best closing technique)",
            width=600,
            font=ctk.CTkFont(size=14),
        )
        self.search_entry.pack(side="left", padx=10, pady=10)
        self.search_entry.bind("<Return>", lambda e: self.search())

        self.search_btn = ctk.CTkButton(
            self.search_frame, text="Search", command=self.search, fg_color="orange"
        )
        self.search_btn.pack(side="left", padx=10, pady=10)

        # Category Buttons
        self.category_frame = ctk.CTkFrame(self)
        self.category_frame.pack(pady=10, padx=20, fill="x")

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

        for cat in categories:
            btn = ctk.CTkButton(
                self.category_frame,
                text=cat,
                command=lambda c=cat: self.search_category(c),
                width=120,
            )
            btn.pack(side="left", padx=5, pady=10)

        # Results Area
        self.results_frame = ctk.CTkScrollableFrame(self, label_text="Results")
        self.results_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Status
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.pack(pady=5)

    def load_stats(self):
        cursor = self.conn.execute("SELECT COUNT(*) FROM pdf_metadata")
        pdf_count = cursor.fetchone()[0]
        self.pdf_count_label.configure(text=f"PDFs: {pdf_count}")

        cursor = self.conn.execute("SELECT COUNT(*) FROM knowledge_chunks")
        chunk_count = cursor.fetchone()[0]
        self.chunk_count_label.configure(text=f"Chunks: {chunk_count}")

    def process_pdfs(self):
        self.status_label.configure(text="Processing...")
        self.update()

        thread = threading.Thread(target=self._process_pdfs)
        thread.start()

    def _process_pdfs(self):
        os.makedirs(PDF_FOLDER, exist_ok=True)

        pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]
        processed = 0

        for filename in pdf_files:
            pdf_path = os.path.join(PDF_FOLDER, filename)
            self.process_single_pdf(pdf_path)
            processed += 1

        self.after(0, self.load_stats)
        self.after(
            0, lambda: self.status_label.configure(text=f"Processed {processed} PDFs")
        )

    def process_single_pdf(self, pdf_path):
        filename = os.path.basename(pdf_path)

        try:
            pdf_hash = hashlib.md5(open(pdf_path, "rb").read()).hexdigest()

            cursor = self.conn.execute(
                "SELECT hash FROM pdf_metadata WHERE hash = ?", (pdf_hash,)
            )
            if cursor.fetchone():
                return

            doc = fitz.open(pdf_path)
            pdf_id = pdf_hash[:8]
            metadata = doc.metadata

            if metadata:
                title = metadata.get("title", "") or filename
                author = metadata.get("author", "Unknown")
            else:
                title = filename
                author = "Unknown"

            self.conn.execute(
                "INSERT INTO pdf_metadata VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pdf_id, filename, title, author, len(doc), datetime.now(), pdf_hash),
            )

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

                    category = self.categorize_chunk(chunk)
                    chunk_id = f"{pdf_id}_p{page_num}_c{i // chunk_size}"

                    try:
                        self.conn.execute(
                            "INSERT OR REPLACE INTO knowledge_chunks VALUES (?, ?, ?, ?, ?, ?)",
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

            self.conn.commit()

        except Exception as e:
            print(f"Error: {e}")

    def categorize_chunk(self, text):
        lower = text.lower()

        categories = {
            "Closing": ["close", "sale", "buy", "purchase", "sign", "deal done", "yes"],
            "Objection Handling": [
                "objection",
                "but ",
                "think about",
                "expensive",
                "too much",
            ],
            "Prospecting": ["prospect", "lead", "contact", "cold call", "reach out"],
            "Follow-up": ["follow up", "follow-up", "call back", "check in"],
            "Rapport": ["rapport", "connect", "relationship", "trust"],
            "Negotiation": ["negotiate", "bargain", "deal", "terms", "leverage"],
            "Value": ["value", "benefit", "worth", "roi", "return"],
            "Authority": ["authority", "expert", "know", "experience"],
        }

        for cat, keywords in categories.items():
            if any(kw in lower for kw in keywords):
                return cat

        return "General"

    def add_pdfs(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])

        for f in files:
            dest = os.path.join(PDF_FOLDER, os.path.basename(f))
            with open(dest, "wb") as out:
                with open(f, "rb") as in_file:
                    out.write(in_file.read())

        self.status_label.configure(text=f"Added {len(files)} PDFs. Click Process.")

    def search(self):
        query = self.search_entry.get()
        if not query:
            return

        self.status_label.configure(text="Searching...")

        # Clear results
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        cursor = self.conn.execute(
            "SELECT chunk_text, pdf_id, page_number, category FROM knowledge_chunks WHERE chunk_text LIKE ? LIMIT 20",
            (f"%{query}%",),
        )

        results = cursor.fetchall()

        for i, (text, pdf_id, page, category) in enumerate(results):
            result_frame = ctk.CTkFrame(self.results_frame)
            result_frame.pack(pady=5, padx=5, fill="x")

            ctk.CTkLabel(
                result_frame,
                text=f"Result {i + 1} | Page {page} | {category}",
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(pady=(5, 0), padx=5, anchor="w")

            ctk.CTkLabel(
                result_frame,
                text=text[:500] + "..." if len(text) > 500 else text,
                font=ctk.CTkFont(size=11),
            ).pack(pady=5, padx=5, anchor="w")

        self.status_label.configure(text=f"Found {len(results)} results")

    def search_category(self, category):
        self.status_label.configure(text=f"Loading {category}...")

        for widget in self.results_frame.winfo_children():
            widget.destroy()

        cursor = self.conn.execute(
            "SELECT chunk_text, pdf_id, page_number FROM knowledge_chunks WHERE category = ? LIMIT 20",
            (category,),
        )

        results = cursor.fetchall()

        for i, (text, pdf_id, page) in enumerate(results):
            result_frame = ctk.CTkFrame(self.results_frame)
            result_frame.pack(pady=5, padx=5, fill="x")

            ctk.CTkLabel(
                result_frame,
                text=f"{i + 1}. Page {page}",
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(pady=(5, 0), padx=5, anchor="w")

            ctk.CTkLabel(
                result_frame,
                text=text[:600] + "..." if len(text) > 600 else text,
                font=ctk.CTkFont(size=11),
            ).pack(pady=5, padx=5, anchor="w")

        self.status_label.configure(text=f"Found {len(results)} {category} techniques")


if __name__ == "__main__":
    os.makedirs(PDF_FOLDER, exist_ok=True)
    app = PDFKnowledgeApp()
    app.mainloop()
