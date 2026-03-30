"""
rag_pipeline.py — RAG retrieval pipeline

This module handles querying the ChromaDB vector database to find relevant
text chunks from the local PDF library. See chunk_text() and retrieve() for
the core logic; both are called by the MCP server via query_library().
"""

import pathlib
import yaml
import chromadb
from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config(config_path: str = "config.yaml") -> dict:
    config_path = pathlib.Path(config_path)
    if not config_path.exists():
        # Try relative to this file's parent
        config_path = pathlib.Path(__file__).parent.parent / "config.yaml"
    with open(config_path, encoding='utf-8') as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# RAGPipeline class
# ---------------------------------------------------------------------------

class RAGPipeline:
    """
    Wraps a ChromaDB collection and a sentence-transformer model to provide
    semantic search over ingested PDF chunks.
    """

    def __init__(self, config: dict):
        rag_cfg = config["rag"]

        self.top_k: int = rag_cfg["top_k"]
        self.similarity_threshold: float = rag_cfg["similarity_threshold"]
        self.embedding_model_name: str = rag_cfg["embedding_model"]
        db_path: str = rag_cfg["db_path"]
        collection_name: str = rag_cfg["collection_name"]

        # Load the embedding model
        self.model = SentenceTransformer(self.embedding_model_name)

        # Connect to the persistent ChromaDB collection
        client = chromadb.PersistentClient(path=db_path)
        self.collection = client.get_collection(collection_name)

    @staticmethod
    def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
        """
        Split *text* into overlapping fixed-size character chunks.

        Each chunk is at most chunk_size characters. Consecutive chunks overlap
        by chunk_overlap characters; the step between chunk starts is
        (chunk_size - chunk_overlap). The last chunk may be shorter.

        Example:
            chunk_text("abcdefghij", chunk_size=4, chunk_overlap=1)
            # step = 3 → ["abcd", "defg", "ghij", "j"]
        """
        if not text:
            return []

        chunks = []
        step = chunk_size - chunk_overlap
        start = 0
        while start < len(text):
            chunks.append(text[start : start + chunk_size])
            start += step
        return chunks

    def retrieve(self, query: str) -> list[dict]:
        """
        Retrieve the most relevant chunks from the PDF library for *query*.

        Steps:
          1. Encode *query* into an embedding vector.
          2. Query ChromaDB for the top self.top_k nearest chunks.
          3. Convert L2 distances to similarity scores: 1 / (1 + distance).
          4. Filter out results below self.similarity_threshold.
          5. Return results sorted by similarity descending, each as a dict with
             keys: text, source, chunk_index, similarity.
        """
        # Step 1: encode the query
        query_embedding = self.model.encode(query).tolist()

        # Step 2: query ChromaDB for the top-k nearest chunks
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=self.top_k,
            include=["documents", "metadatas", "distances"],
        )

        # Steps 3–4: convert distances to similarities and filter by threshold
        output = []
        for text, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            similarity = round(1 / (1 + distance), 4)
            if similarity >= self.similarity_threshold:
                output.append({
                    "text": text,
                    "source": meta["source"],
                    "chunk_index": meta["chunk_index"],
                    "similarity": similarity,
                })

        # Step 5: sort by similarity descending
        output.sort(key=lambda x: x["similarity"], reverse=True)
        return output


# ---------------------------------------------------------------------------
# Convenience function used by the MCP server
# ---------------------------------------------------------------------------

_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    """Return a cached RAGPipeline instance (lazy-loaded on first call)."""
    global _pipeline
    if _pipeline is None:
        config = load_config()
        _pipeline = RAGPipeline(config)
    return _pipeline


def query_library(query: str) -> list[dict]:
    """Top-level function called by the MCP server tool."""
    return get_pipeline().retrieve(query)
