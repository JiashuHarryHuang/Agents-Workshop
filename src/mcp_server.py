"""
mcp_server.py — Literature Review MCP Server

This file wires together the Semantic Scholar client and the RAG pipeline
into four MCP tools that Claude can call during a literature review session.

Run with:
    python src/mcp_server.py
Or register it via Claude Code:
    claude mcp add literature-review -- python src/mcp_server.py
"""

import json
import logging
import pathlib
import sys
import yaml
import httpx
from mcp.server.fastmcp import FastMCP

# Suppress verbose HuggingFace/sentence-transformers download logs
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)

# Ensure project root is on the path when run from src/
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from src.semantic_scholar import SemanticScholarClient
from src.rag_pipeline import query_library
from prompts.templates import get_system_prompt


# ---------------------------------------------------------------------------
# Load config and initialise clients
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    config_path = pathlib.Path(__file__).parent.parent / "config.yaml"
    with open(config_path, encoding='utf-8') as f:
        return yaml.safe_load(f)


config = _load_config()
ss_cfg = config["semantic_scholar"]
agent_cfg = config["agent"]

_ss_client = SemanticScholarClient(
    base_url=ss_cfg["base_url"],
    rate_limit_delay=ss_cfg["rate_limit_delay"],
)

# ---------------------------------------------------------------------------
# Initialise FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Literature Review Assistant",
    instructions=get_system_prompt(agent_cfg["system_prompt"]),
)

# ---------------------------------------------------------------------------
# Tool 1: search_papers
# ---------------------------------------------------------------------------

@mcp.tool()
def search_papers(
    query: str,
    limit: int = 10,
    year: str = "",
    fields_of_study: str = "",
) -> str:
    """
    Search Semantic Scholar for academic papers matching a query.

    Use this tool to discover papers by topic, author, or keyword. It searches
    a large database of academic papers and returns metadata including titles,
    authors, publication year, citation counts, and abstracts.

    Best used for:
    - Finding seminal papers on a topic you don't have locally
    - Discovering recent work by year filter
    - Getting citation counts to gauge paper impact

    Limitations:
    - Results are metadata only (no full text). Use query_local_library for
      full-text content from papers in the local PDF library.
    - Free-tier rate limits mean searches are slightly throttled.

    Args:
        query: Search query, e.g. "retrieval augmented generation" or
               "LLM agents tool use survey".
        limit: Number of results (1–10, capped by config).
        year: Optional year or range, e.g. "2023" or "2020-2024".
        fields_of_study: Optional comma-separated field filter,
                         e.g. "Computer Science,Artificial Intelligence".
    """
    max_limit = agent_cfg["max_search_results"]
    limit = min(limit, max_limit)

    fos = [f.strip() for f in fields_of_study.split(",") if f.strip()] or None

    try:
        papers = _ss_client.search_papers(
            query=query,
            limit=limit,
            year=year or None,
            fields_of_study=fos,
            include_abstracts=agent_cfg["include_abstracts"],
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            return (
                "Rate limited by Semantic Scholar (HTTP 429). "
                "This is normal on the free tier — please wait a moment and try again."
            )
        raise

    if not papers:
        return "No papers found for that query."

    return json.dumps(papers, indent=2)


# ---------------------------------------------------------------------------
# Tool 2: get_paper_details
# ---------------------------------------------------------------------------

@mcp.tool()
def get_paper_details(paper_id: str) -> str:
    """
    Fetch full metadata for a specific paper, including its reference list.

    Use this tool when you have a paper ID (from search results or citations)
    and want its complete metadata: full abstract, reference count, citation
    count, and the list of papers it references.

    The paper_id can be:
    - A Semantic Scholar ID (hash string from search results)
    - An arXiv ID prefixed with "arXiv:", e.g. "arXiv:2210.03629"
    - A DOI prefixed with "DOI:", e.g. "DOI:10.18653/v1/..."

    Args:
        paper_id: Identifier for the paper (see formats above).
    """
    try:
        paper = _ss_client.get_paper(paper_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            return (
                "Rate limited by Semantic Scholar (HTTP 429). "
                "This is normal on the free tier — please wait a moment and try again."
            )
        raise
    return json.dumps(paper, indent=2)


# ---------------------------------------------------------------------------
# Tool 3: query_local_library
# ---------------------------------------------------------------------------

@mcp.tool()
def query_local_library(query: str) -> str:
    """
    Search the local PDF library using semantic similarity (RAG).

    Use this tool to retrieve relevant passages from the curated set of
    papers stored as PDFs in this project. Unlike search_papers, this tool
    returns actual text from the papers, not just metadata.

    Best used for:
    - Extracting specific claims, methods, or results from known papers
    - Finding passages that answer a specific research question
    - Cross-referencing what a paper actually says vs. its abstract

    Limitations:
    - Only covers papers in the local pdfs/ folder (~20 papers).
    - Retrieval quality depends on chunk_size, top_k, and similarity_threshold
      in config.yaml — these are tunable parameters.
    - Results are character-level chunks and may cut across sentences.

    Args:
        query: A question or topic, e.g. "how does ReAct combine reasoning
               and acting?" or "evaluation metrics for RAG systems".
    """
    try:
        results = query_library(query)
    except NotImplementedError as e:
        return (
            f"RAG pipeline not yet implemented: {e}\n"
            "Complete the TODOs in src/rag_pipeline.py first."
        )
    except Exception as e:
        return f"Error querying library: {e}"

    if not results:
        return (
            "No results above the similarity threshold. "
            "Try lowering similarity_threshold in config.yaml, "
            "or rephrase your query."
        )

    output = []
    for i, r in enumerate(results, 1):
        output.append(
            f"--- Result {i} | source: {r['source']} "
            f"(chunk {r['chunk_index']}) | similarity: {r['similarity']} ---\n"
            f"{r['text']}\n"
        )
    return "\n".join(output)


# ---------------------------------------------------------------------------
# Tool 4: get_citations
# ---------------------------------------------------------------------------

@mcp.tool()
def get_citations(
    paper_id: str,
    direction: str = "references",
    limit: int = 20,
) -> str:
    """
    Explore the citation network around a paper.

    Use this tool to trace intellectual lineage: find what a paper builds on
    (references) or what later work cites it (citations). This is especially
    useful for mapping how a field has evolved.

    Args:
        paper_id: Semantic Scholar ID or prefixed ID (e.g. "arXiv:2210.03629").
        direction: "references" — papers this paper cites (what it builds on).
                   "citations"  — papers that cite this paper (what built on it).
        limit: Maximum number of results (default 20, max 50).
    """
    limit = min(limit, 50)

    try:
        papers = _ss_client.get_citations(paper_id, direction=direction, limit=limit)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            return (
                "Rate limited by Semantic Scholar (HTTP 429). "
                "This is normal on the free tier — please wait a moment and try again."
            )
        raise

    if not papers:
        return f"No {direction} found for paper '{paper_id}'."

    return json.dumps(papers, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
