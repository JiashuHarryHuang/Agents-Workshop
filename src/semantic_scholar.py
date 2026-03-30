"""
semantic_scholar.py — Semantic Scholar Graph API client

Provides a clean interface to the Semantic Scholar Graph API for searching
academic papers and exploring citation networks.
"""

import time
import httpx
from typing import Optional


# Fields requested for paper searches
SEARCH_FIELDS = [
    "paperId",
    "title",
    "authors",
    "year",
    "abstract",
    "citationCount",
    "referenceCount",
    "externalIds",
    "fieldsOfStudy",
    "publicationTypes",
]

# Fields requested for detailed paper lookups
DETAIL_FIELDS = SEARCH_FIELDS + ["references", "citations"]

# Fields for citation/reference list items
CITATION_FIELDS = [
    "paperId",
    "title",
    "authors",
    "year",
    "citationCount",
]


class SemanticScholarClient:
    def __init__(self, base_url: str, rate_limit_delay: float = 1.1):
        self.base_url = base_url.rstrip("/")
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0

    def _wait_for_rate_limit(self):
        """Enforce minimum delay between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def search_papers(
        self,
        query: str,
        limit: int = 10,
        year: Optional[str] = None,
        fields_of_study: Optional[list[str]] = None,
        include_abstracts: bool = True,
    ) -> list[dict]:
        """
        Search for papers matching a query string.

        Args:
            query: Natural language or keyword search query.
            limit: Maximum number of results (1–100).
            year: Optional year filter, e.g. "2020-2024" or "2023".
            fields_of_study: Optional list like ["Computer Science"].
            include_abstracts: Whether to include abstract text.

        Returns:
            List of paper dicts with title, authors, year, abstract, etc.
        """
        self._wait_for_rate_limit()

        fields = SEARCH_FIELDS if include_abstracts else [
            f for f in SEARCH_FIELDS if f != "abstract"
        ]

        params: dict = {
            "query": query,
            "limit": min(limit, 100),
            "fields": ",".join(fields),
        }
        if year:
            params["year"] = year
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)

        response = httpx.get(
            f"{self.base_url}/paper/search",
            params=params,
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        return [_format_paper(p) for p in data.get("data", [])]

    def get_paper(self, paper_id: str) -> dict:
        """
        Fetch full details for a single paper.

        Args:
            paper_id: Semantic Scholar ID, DOI (e.g. "10.18653/..."),
                      or arXiv ID (e.g. "arXiv:2210.03629").

        Returns:
            Paper dict with full metadata, references, and citations.
        """
        self._wait_for_rate_limit()

        response = httpx.get(
            f"{self.base_url}/paper/{paper_id}",
            params={"fields": ",".join(DETAIL_FIELDS)},
            timeout=15.0,
        )
        response.raise_for_status()
        return _format_paper(response.json(), include_relations=True)

    def get_citations(
        self,
        paper_id: str,
        direction: str = "references",
        limit: int = 20,
    ) -> list[dict]:
        """
        Fetch papers that this paper references, or papers that cite it.

        Args:
            paper_id: Semantic Scholar ID or prefixed ID (e.g. "arXiv:...").
            direction: "references" (papers this cites) or
                       "citations" (papers that cite this).
            limit: Max results (1–1000).

        Returns:
            List of paper dicts.
        """
        if direction not in ("references", "citations"):
            raise ValueError("direction must be 'references' or 'citations'")

        self._wait_for_rate_limit()

        response = httpx.get(
            f"{self.base_url}/paper/{paper_id}/{direction}",
            params={
                "fields": ",".join(CITATION_FIELDS),
                "limit": min(limit, 1000),
            },
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()

        # The API wraps each entry in a "citedPaper" or "citingPaper" key
        wrapper_key = "citedPaper" if direction == "references" else "citingPaper"
        papers = [
            item[wrapper_key]
            for item in data.get("data", [])
            if item.get(wrapper_key)
        ]
        return [_format_paper(p) for p in papers]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _format_paper(raw: dict, include_relations: bool = False) -> dict:
    """Normalize a raw API response into a clean dict."""
    authors = [a.get("name", "") for a in raw.get("authors", [])]

    # Extract arXiv ID if available
    external_ids = raw.get("externalIds") or {}
    arxiv_id = external_ids.get("ArXiv")
    doi = external_ids.get("DOI")

    paper = {
        "paperId": raw.get("paperId", ""),
        "title": raw.get("title", ""),
        "authors": authors,
        "year": raw.get("year"),
        "abstract": raw.get("abstract", ""),
        "citationCount": raw.get("citationCount", 0),
        "referenceCount": raw.get("referenceCount", 0),
        "fieldsOfStudy": raw.get("fieldsOfStudy") or [],
        "arxivId": arxiv_id,
        "doi": doi,
    }

    if include_relations:
        paper["references"] = [
            _format_paper(r.get("citedPaper", {}))
            for r in raw.get("references", [])
            if r.get("citedPaper")
        ]
        paper["citations"] = [
            _format_paper(c.get("citingPaper", {}))
            for c in raw.get("citations", [])
            if c.get("citingPaper")
        ]

    return paper
