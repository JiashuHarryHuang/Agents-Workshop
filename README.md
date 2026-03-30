# Literature Review MCP Agent

A Model Context Protocol (MCP) server that combines Semantic Scholar search with local PDF retrieval (RAG) to assist with academic literature reviews.

## Overview

This system provides Claude with four specialized tools for conducting literature reviews:

1. **search_papers** — Search Semantic Scholar's database for academic papers
2. **get_paper_details** — Fetch full metadata and references for specific papers
3. **query_local_library** — Retrieve relevant passages from local PDFs using semantic similarity
4. **get_citations** — Explore citation networks to trace intellectual lineage

## Architecture

```
lit-review-agent/
├── config.yaml              # RAG parameters and agent settings
├── download_papers.py       # Downloads ~20 arXiv PDFs
├── requirements.txt         # Python dependencies
├── prompts/
│   └── templates.py         # System prompt variants (default, concise, structured, critical)
├── src/
│   ├── mcp_server.py        # MCP server implementation
│   ├── rag_pipeline.py      # RAG chunking and retrieval logic
│   ├── pdf_ingestor.py      # PDF processing and ChromaDB ingestion
│   └── semantic_scholar.py  # Semantic Scholar API client
├── pdfs/                    # Local PDF corpus (created by download_papers.py)
└── chroma_db/               # ChromaDB vector store (created by pdf_ingestor.py)
```

## Setup

### 1. Create and activate a virtual environment

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Download the PDF corpus

```bash
python download_papers.py
```

This downloads ~20 papers on LLM agents, RAG, and related topics from arXiv.

### 4. Build the vector database

```bash
python src/pdf_ingestor.py
```

This extracts text from PDFs, chunks it, computes embeddings, and stores everything in ChromaDB.

### 5. Register the MCP server with Claude Code

```bash
claude mcp add lit-review -- python src/mcp_server.py
```

**Note:** You may need to provide the full path to your virtual environment's Python:
- macOS/Linux: `./venv/bin/python`
- Windows: `./venv/Scripts/python.exe`

### 6. Verify the server is running

Start a Claude Code session and ask:

> "List the tools you have access to."

You should see: `search_papers`, `get_paper_details`, `query_local_library`, and `get_citations`.

Then try:

> "Search Semantic Scholar for 'retrieval augmented generation'."

If you get paper results, your setup is complete.

## Configuration

All tunable parameters are in `config.yaml`:

### RAG Parameters
- **chunk_size** (default: 512) — Characters per chunk
- **chunk_overlap** (default: 64) — Overlap between consecutive chunks
- **top_k** (default: 5) — Number of chunks to retrieve
- **similarity_threshold** (default: 0.3) — Minimum similarity score (0.0–1.0)
- **embedding_model** (default: "all-MiniLM-L6-v2") — Sentence-Transformers model

### Agent Settings
- **system_prompt** — Which prompt template to use: "default", "concise", "structured", or "critical"
- **max_search_results** (default: 10) — Max papers from Semantic Scholar
- **include_abstracts** (default: true) — Include full abstracts in search results

### After changing config:
1. If you changed RAG parameters (chunk_size, embedding_model, etc.), re-run:
   ```bash
   python src/pdf_ingestor.py
   ```
2. Restart the MCP server (or restart Claude Code)

## System Prompts

Four prompt variants are included in `prompts/templates.py`:

1. **default** — Balanced prose review, Semantic Scholar first
2. **concise** — Bullet-point summary, minimal tool calls, local library first
3. **structured** — Five required sections with explicit tool ordering
4. **critical** — Skeptical evaluation focusing on evidence quality

Switch between them by changing `agent.system_prompt` in `config.yaml`.

## Example Usage

### Basic literature review query
```
Claude, help me understand the current state of tool use in LLM agents.
```

### Targeted search
```
Find papers on multi-agent coordination published after 2023.
```

### Deep dive into a specific paper
```
Get the details for arXiv:2210.03629 and show me what it references.
```

### Local library search
```
What does the local library say about evaluation metrics for RAG systems?
```

## Components

### Semantic Scholar Client (`src/semantic_scholar.py`)
- Handles API rate limiting (1.1s between requests)
- Supports search, paper details, and citation network exploration
- Accepts Semantic Scholar IDs, arXiv IDs, and DOIs

### RAG Pipeline (`src/rag_pipeline.py`)
- Chunks text with configurable size and overlap
- Uses ChromaDB for vector storage and retrieval
- Converts L2 distances to similarity scores
- Filters and ranks results by relevance

### PDF Ingestor (`src/pdf_ingestor.py`)
- Extracts text from PDFs using PyMuPDF
- Chunks text according to config.yaml
- Computes embeddings using Sentence Transformers
- Stores in ChromaDB with metadata

### MCP Server (`src/mcp_server.py`)
- Exposes four tools to Claude
- Handles rate limiting and error messages
- Formats results for readability

## Limitations

- **Semantic Scholar**: Free tier allows ~1 request/second
- **Local library**: Only ~20 papers included by default
- **Chunking**: Character-based chunking may split sentences
- **No full-text search**: Only local PDFs are searchable at the passage level

## Extending the System

### Add more papers
1. Add arXiv IDs to `PAPERS` list in `download_papers.py`
2. Run `python download_papers.py`
3. Run `python src/pdf_ingestor.py`

### Create custom prompts
1. Add new template to `prompts/templates.py`
2. Update `TEMPLATES` dictionary
3. Set `agent.system_prompt` in `config.yaml`

### Tune retrieval quality
- Increase `chunk_size` for more context per result
- Increase `top_k` to see more results
- Lower `similarity_threshold` to include less relevant chunks
- Try different embedding models (e.g., "all-mpnet-base-v2")

## Troubleshooting

### "No PDFs found in 'pdfs/'"
Run `python download_papers.py` first.

### "Collection 'literature' does not exist"
Run `python src/pdf_ingestor.py` to build the vector database.

### "Rate limited by Semantic Scholar (HTTP 429)"
Wait a moment and try again. This is normal on the free tier.

### ChromaDB errors after changing embedding model
Delete the `chroma_db/` directory and re-run `python src/pdf_ingestor.py`.

## License

This is an educational project. The included papers are available on arXiv under their respective licenses.

## Acknowledgments

- Semantic Scholar Graph API: https://api.semanticscholar.org
- ChromaDB: https://www.trychroma.com
- Sentence Transformers: https://www.sbert.net
- PyMuPDF: https://pymupdf.readthedocs.io
- FastMCP: https://github.com/jlowin/fastmcp
