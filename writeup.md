# Writeup — Agentic AI Assignment

**Name:** Jiashu Huang
**Date:** March 30, 2026
**Agent built:** _(literature review agent / describe your agent)_

---

## Part 2: Task Analysis

**Research question / task:** Help me understand the current state of retrieval-augmented generation for LLMs.

**Address two of the three areas:**

### Depth beyond surface-level search

What did your agent surface that a quick web/API search alone would have missed?
Did it miss anything?

> The agent is able to conduct an organized synthesis of multiple papers rather than aggregating multiple abstracts. It missed the paper about Recursive Abstractive Processing for Tree-Organized Retrieval because it is not mentioned in the prompt but it is still related to RAG.

### Local retrieval contribution

Which passages from your vector database actually made it into the final output?
Were they more useful than the external API results, or largely redundant?

> 40% of the papers made to the final output. I think they are equally useful.

### At least one failure

Describe a case where the system misled you or failed: a hallucinated claim, a
missed key result, an irrelevant retrieved chunk, or a synthesis that sounded
authoritative but was shallow. Would you trust this system for real work?

> Claude presented detailed descriptions of Agentic RAG, GraphRAG, Multimodal RAG, and Trustworthy RAG as if it had deep understanding of these papers, but it only had paper titles, author names, citation counts, brief abstracts (in the Semantic Scholar results). I would trust the system for real work after further verification of source.

---

## Part 3: Reflection

_Address three of the following._

### 3.1 Build process

What was a major design decision you had to make? How did you decide on a
particular course of action?

> The major design decision was determining the search strategy: whether to query the local PDF library first or start with external Semantic Scholar searches, and how many queries to make. I decided to use parallel queries to both sources simultaneously—querying the local vector database for technical depth while also searching Semantic Scholar for breadth and recent papers (2024-2025) not yet in my collection. This balanced approach maximizes information coverage despite Semantic Scholar's rate limits and the local library's size constraints (~20 papers). The tradeoff is potential redundancy, but I prioritized comprehensiveness over efficiency for a literature review task.

What did Claude get right on the first try? Where did you have to push back,
correct it, or iterate?

> All code worked on the first try.

### 3.2 System prompt engineering

What two prompt variants did you implement? How did they differ in behavior —
not just wording, but in which tools the agent called and in what order?

> **Variant 1 (Sequential):** "Start by searching Semantic Scholar to get an overview of the topic. Then use query_local_library to retrieve relevant passages." This prompt led the agent to call search_papers first, wait for results, then make local library queries. Total tool calls: 5 sequential operations.
>
> **Variant 2 (Parallel synthesis):** "Search both Semantic Scholar and your local PDF library simultaneously, then synthesize findings into a coherent literature review." This prompt triggered parallel tool calls—search_papers and query_local_library invoked together in the first message. Total tool calls: 4 parallel operations, completing faster despite hitting the same rate limit.
>
> The key behavioral difference: Variant 1 created a dependency chain (external → local), while Variant 2 treated both sources as independent and equal contributors to synthesis.

Which produced better output, and how are you defining "better"?

> Variant 2 produced better output. I'm defining "better" as: (1) **Speed:** 30-40% faster by parallelizing independent queries, (2) **Source integration:** The agent naturally weighted local (full-text) and external (metadata) sources appropriately rather than treating Semantic Scholar results as primary, (3) **Robustness:** When the first Semantic Scholar search was rate-limited, the agent already had local library results to work with rather than blocking entirely. The synthesis was more balanced because both sources informed the structure from the start, rather than local results being retrofitted into an external-search-driven narrative.

### 3.4 Architecture limitations

What would you need to change to make this viable for a real workflow?

> **Three critical changes:**
>
> 1. **Provenance tracking:** Add explicit citations distinguishing between direct quotes from full-text PDFs (with page numbers), inferences from abstracts/titles, and general domain knowledge. Currently, the output blends these without transparency, creating false confidence. Implement a citation metadata system that tags each claim with its source type and confidence level.
>
> 2. **Iterative search recovery:** Build retry logic and alternative search strategies for rate-limited or failed queries. When Semantic Scholar returns HTTP 429, the agent should automatically try different query formulations or wait and retry rather than proceeding with partial results. Add a "search quality" check that verifies sufficient relevant papers were retrieved.
>
> 3. **Local library exploration:** Add a discovery phase that first inventories all PDFs in the local collection before querying. Currently, the agent may repeatedly query the same paper (Gao2023_RAG_survey.pdf) without realizing other relevant papers exist. Implement a two-stage retrieval: broad document-level matching, then targeted chunk retrieval from top-k documents.

What did you learn about the limits of RAG-based agents that you didn't
expect before building one?

> **Three unexpected limits:**
>
> 1. **Similarity ≠ relevance:** A chunk with 0.71 similarity can be structurally similar (e.g., both discuss "three paradigms") but answer different questions. The agent retrieved chunks about RAG taxonomy when I needed implementation details. Vector similarity captures semantic closeness, not pragmatic usefulness for a specific query.
>
> 2. **Metadata creates illusion of understanding:** Citation counts (528, 238, 93) and paper titles gave the agent enough information to sound authoritative about papers it never read. The synthesis was fluent and structured but partially speculative—it inferred what "Agentic RAG" means from the title rather than reading the paper. RAG agents can confidently extrapolate from minimal information, which is dangerous for academic work.
>
> 3. **Chunking destroys context:** The retrieved passages were character-level chunks (likely 512-1024 tokens) that sometimes cut mid-sentence or mid-argument. To understand RAG paradigms, I needed the full section with figures and definitions, not fragmented snippets. Fixed-size chunking is convenient for vector DBs but loses document structure (headings, sections, figures) that researchers rely on.
