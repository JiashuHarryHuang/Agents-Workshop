"""
pdf_ingestor.py — PDF ingestion pipeline

Reads PDFs from the pdfs/ folder, extracts text, chunks it, computes
embeddings, and stores everything in ChromaDB.

Run this script once after downloading papers, and again any time you:
  - Add new PDFs
  - Change chunk_size or chunk_overlap in config.yaml
  - Change the embedding_model in config.yaml

Usage:
    python src/pdf_ingestor.py
"""

import os
import sys
import hashlib
import pathlib
import yaml
import chromadb
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding='utf-8') as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: pathlib.Path) -> str:
    """Extract all text from a PDF file using PyMuPDF."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    Split text into overlapping fixed-size character chunks.

    This simple approach splits on character boundaries. Note that this
    may cut words in half — a production system would split on sentence
    or paragraph boundaries instead.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    chunks = []
    step = chunk_size - chunk_overlap
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += step
    return chunks


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def ingest_pdfs(
    pdf_dir: str = "pdfs",
    config_path: str = "config.yaml",
) -> None:
    config = load_config(config_path)
    rag_cfg = config["rag"]

    chunk_size: int = rag_cfg["chunk_size"]
    chunk_overlap: int = rag_cfg["chunk_overlap"]
    embedding_model_name: str = rag_cfg["embedding_model"]
    db_path: str = rag_cfg["db_path"]
    collection_name: str = rag_cfg["collection_name"]

    pdf_paths = list(pathlib.Path(pdf_dir).glob("*.pdf"))
    if not pdf_paths:
        print(f"No PDFs found in '{pdf_dir}/'. Run download_papers.py first.")
        sys.exit(1)

    print(f"Loading embedding model: {embedding_model_name}")
    model = SentenceTransformer(embedding_model_name)

    print(f"Connecting to ChromaDB at: {db_path}")
    client = chromadb.PersistentClient(path=db_path)

    # Delete and recreate the collection so ingestion is idempotent
    try:
        client.delete_collection(collection_name)
        print(f"Deleted existing collection '{collection_name}'")
    except Exception:
        pass
    collection = client.create_collection(collection_name)

    total_chunks = 0
    for pdf_path in sorted(pdf_paths):
        print(f"\nIngesting: {pdf_path.name}")
        try:
            text = extract_text_from_pdf(pdf_path)
        except Exception as e:
            print(f"  ERROR reading PDF: {e}")
            continue

        if not text.strip():
            print("  WARNING: No text extracted — PDF may be image-only")
            continue

        chunks = chunk_text(text, chunk_size, chunk_overlap)
        print(f"  {len(text):,} chars → {len(chunks)} chunks "
              f"(size={chunk_size}, overlap={chunk_overlap})")

        # Compute embeddings in batch
        embeddings = model.encode(chunks, show_progress_bar=False).tolist()

        # Build IDs and metadata
        ids = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(
                f"{pdf_path.name}::{i}".encode()
            ).hexdigest()
            ids.append(chunk_id)
            metadatas.append({
                "source": pdf_path.name,
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

        # Upsert into ChromaDB
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )
        total_chunks += len(chunks)

    print(f"\nIngestion complete. Total chunks stored: {total_chunks}")
    print(f"Config used — chunk_size={chunk_size}, "
          f"chunk_overlap={chunk_overlap}, "
          f"model={embedding_model_name}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow running from either the project root or src/
    if not pathlib.Path("config.yaml").exists():
        os.chdir(pathlib.Path(__file__).parent.parent)

    ingest_pdfs()
