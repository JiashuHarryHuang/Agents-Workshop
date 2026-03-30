# Literature Review Agent - User Manual

## Overview

The Literature Review Agent is an AI-powered research assistant that helps you conduct systematic academic literature reviews. It combines two powerful capabilities:

1. **Broad Discovery**: Search millions of academic papers through Semantic Scholar's database
2. **Deep Analysis**: Retrieve and analyze full-text passages from your local PDF library using semantic search (RAG)

The agent is implemented as an MCP (Model Context Protocol) server that integrates with Claude Code, giving Claude specialized tools for academic research.

---

## Core Capabilities

The agent provides four specialized tools that work together to help you explore academic literature:

### 1. Search Papers (`search_papers`)

**What it does**: Searches Semantic Scholar's database of millions of academic papers to find relevant work by topic, author, or keywords.

**Returns**:
- Paper titles and authors
- Publication year
- Citation counts (for gauging impact)
- Full abstracts (configurable)
- arXiv IDs and DOIs
- Fields of study

**Best used for**:
- Discovering seminal papers on a topic
- Finding recent work by filtering by year
- Identifying highly-cited influential papers
- Getting an overview of a research area

**Limitations**:
- Returns metadata only (no full text)
- Free tier rate limiting (~1 request/second)
- No access to paper PDFs or full content

**Parameters**:
- `query`: Search terms (e.g., "retrieval augmented generation", "multi-agent coordination")
- `limit`: Number of results (1-10, configurable max)
- `year`: Optional year filter (e.g., "2023", "2020-2024")
- `fields_of_study`: Optional field filter (e.g., "Computer Science,Artificial Intelligence")

### 2. Get Paper Details (`get_paper_details`)

**What it does**: Fetches comprehensive metadata for a specific paper, including its complete reference list and citation information.

**Returns**:
- Full abstract
- Complete reference list (papers it cites)
- Citation information
- External identifiers (arXiv, DOI)
- Citation and reference counts

**Best used for**:
- Deep-diving into a specific paper's contributions
- Tracing intellectual lineage
- Verifying what a paper cites
- Getting comprehensive metadata

**Parameters**:
- `paper_id`: Can be a Semantic Scholar ID, "arXiv:2210.03629", or "DOI:10.18653/..."

### 3. Query Local Library (`query_local_library`)

**What it does**: Performs semantic similarity search over your local PDF library to retrieve actual text passages that answer your question.

**Returns**:
- Relevant text passages from papers
- Source paper name
- Chunk index within the paper
- Similarity score (0.0-1.0)

**Best used for**:
- Extracting specific claims, methods, or results
- Finding exact passages that answer a research question
- Cross-referencing what papers actually say vs. their abstracts
- Detailed analysis of methodology or experiments

**Limitations**:
- Only searches ~20 papers in the local `pdfs/` folder
- Retrieval quality depends on configuration (chunk_size, top_k, similarity_threshold)
- Results are character-level chunks that may split sentences
- Requires prior PDF ingestion

**Parameters**:
- `query`: A question or topic (e.g., "how does ReAct combine reasoning and acting?")

### 4. Get Citations (`get_citations`)

**What it does**: Explores the citation network around a paper to map intellectual lineage.

**Returns**:
- List of papers (with title, authors, year, citation count)
- Either papers that this paper cites (references)
- Or papers that cite this paper (citations)

**Best used for**:
- Mapping how a field has evolved
- Finding foundational work a paper builds on
- Discovering later work that builds on a paper
- Understanding research lineage

**Parameters**:
- `paper_id`: Semantic Scholar ID or prefixed ID
- `direction`: "references" (what it cites) or "citations" (what cites it)
- `limit`: Max results (default 20, max 50)

---

## How It Works

### Architecture Overview

```
┌─────────────────────┐
│   Claude Code       │ ← You interact with Claude
└──────────┬──────────┘
           │ MCP Protocol
┌──────────▼──────────────────────────────────┐
│  Literature Review MCP Server               │
│  ┌────────────────────────────────────────┐ │
│  │ Four Tools:                            │ │
│  │ • search_papers                        │ │
│  │ • get_paper_details                    │ │
│  │ • query_local_library                  │ │
│  │ • get_citations                        │ │
│  └────────────────────────────────────────┘ │
└──────────┬──────────────────┬───────────────┘
           │                  │
┌──────────▼──────────┐  ┌───▼──────────────┐
│ Semantic Scholar    │  │  Local RAG       │
│ API Client          │  │  Pipeline        │
│                     │  │                  │
│ • Rate limiting     │  │ • ChromaDB       │
│ • Paper search      │  │ • Embeddings     │
│ • Citation network  │  │ • Chunking       │
└─────────────────────┘  └──────────────────┘
                              │
                         ┌────▼─────┐
                         │ PDFs/    │
                         │ ~20 papers│
                         └──────────┘
```

### RAG (Retrieval-Augmented Generation) Pipeline

The local library search uses a sophisticated RAG pipeline:

1. **Ingestion Phase** (one-time setup):
   - PDFs are downloaded from arXiv
   - Text is extracted from each PDF
   - Text is split into overlapping chunks (default: 512 characters)
   - Each chunk is embedded using a sentence transformer model
   - Embeddings are stored in ChromaDB vector database

2. **Query Phase** (when you search):
   - Your query is embedded using the same model
   - ChromaDB finds the most similar chunks by vector distance
   - Distances are converted to similarity scores
   - Results are filtered by threshold and ranked
   - Top passages are returned with metadata

### System Prompts

The agent uses customizable system prompts that guide its behavior. Four variants are included:

1. **default**: Balanced prose review, starts with Semantic Scholar for overview
2. **concise**: Structured bullet-point summaries, minimal tool calls, local library first
3. **structured**: Five required sections (Introduction, Methods, Evaluation, Open Problems, Conclusion)
4. **critical**: Skeptical evaluation focusing on evidence quality and experimental rigor

You can switch between them in `config.yaml` or create your own custom prompts.

---

## Configuration Options

All settings are in `config.yaml`. Here's what you can customize:

### RAG Parameters

```yaml
rag:
  chunk_size: 512          # Characters per chunk (affects context vs. precision)
  chunk_overlap: 64        # Overlap between chunks (prevents boundary cuts)
  top_k: 5                 # Number of chunks to retrieve
  similarity_threshold: 0.3 # Min similarity (0.0-1.0) to include a result
  embedding_model: "all-MiniLM-L6-v2"  # Sentence transformer model
```

**Trade-offs**:
- **Larger chunk_size**: More context per result, but may include irrelevant text
- **Smaller chunk_size**: More precise, but may miss context across boundaries
- **Higher top_k**: More results, but potentially less relevant ones
- **Higher similarity_threshold**: Only highly relevant results, but fewer total results
- **Better embedding models** (e.g., "all-mpnet-base-v2"): Higher quality, but slower

### Semantic Scholar Settings

```yaml
semantic_scholar:
  base_url: "https://api.semanticscholar.org/graph/v1"
  default_limit: 10
  rate_limit_delay: 1.1    # Seconds between requests (don't set below 1.0)
```

### Agent Behavior

```yaml
agent:
  system_prompt: "default"      # Which prompt template to use
  max_search_results: 10        # Max papers from Semantic Scholar
  include_abstracts: true       # Include full abstracts in search results
```

### Applying Configuration Changes

After changing config:
- **RAG parameters**: Re-run `python src/pdf_ingestor.py` to rebuild the vector database
- **Agent settings**: Restart the MCP server (or restart Claude Code)

---

## Use Case Examples

### Use Case 1: Exploring a New Research Area

**Scenario**: You're new to the field of retrieval-augmented generation (RAG) and want an overview.

**Query**: "Help me understand the current state of retrieval-augmented generation for LLMs."

**What happens**:
1. Agent searches Semantic Scholar for "retrieval augmented generation"
2. Returns top papers with titles, authors, years, citation counts, and abstracts
3. Queries local library for relevant passages about RAG concepts
4. Synthesizes findings into a coherent review grouping papers by theme
5. Notes gaps and open problems in the literature

**Expected output**:
- Overview of what RAG is and why it matters
- Key papers organized by approach (e.g., naive RAG, advanced RAG, modular RAG)
- Evolution of the field from early work to recent innovations
- Current challenges and open questions

### Use Case 2: Finding Recent Work on a Specific Topic

**Scenario**: You need papers on multi-agent coordination published after 2023.

**Query**: "Find papers on multi-agent coordination published after 2023."

**What happens**:
1. Agent calls `search_papers(query="multi-agent coordination", year="2024-")`
2. Returns recent papers with high citation counts
3. May call `get_paper_details` on highly-cited papers to see what they reference
4. Summarizes the recent trends and contributions

**Expected output**:
- List of 5-10 recent papers on multi-agent coordination
- Brief description of each paper's contribution
- Identification of emerging trends or common approaches
- Notable highly-cited papers as entry points

### Use Case 3: Deep-Diving into a Specific Paper

**Scenario**: You found a paper on ReAct (reasoning + acting) and want to understand it deeply.

**Query**: "Get the details for arXiv:2210.03629 and explain what ReAct does."

**What happens**:
1. Agent calls `get_paper_details("arXiv:2210.03629")`
2. Retrieves full metadata, abstract, and reference list
3. Calls `query_local_library("ReAct reasoning acting")` to get actual text passages
4. May call `get_citations` to see what later work built on ReAct
5. Synthesizes an explanation with specific details from the paper

**Expected output**:
- Explanation of the ReAct framework
- How it combines reasoning and acting in language models
- Key experiments and results (if in local library)
- What foundational work it builds on
- What later work has cited or extended it

### Use Case 4: Tracing Intellectual Lineage

**Scenario**: You want to understand the history of chain-of-thought prompting.

**Query**: "Show me the intellectual lineage of chain-of-thought prompting - what led to it and what came after."

**What happens**:
1. Agent searches for "chain of thought prompting"
2. Identifies the seminal paper (Wei et al., 2022)
3. Calls `get_citations(paper_id, direction="references")` to see what it built on
4. Calls `get_citations(paper_id, direction="citations")` to see what built on it
5. Creates a narrative of how the idea evolved

**Expected output**:
- Original chain-of-thought paper (Wei et al., 2022)
- Earlier work on prompting and reasoning that inspired it
- Later extensions like self-consistency, tree-of-thoughts, etc.
- Timeline showing evolution of the technique
- Key innovations at each stage

### Use Case 5: Extracting Specific Information

**Scenario**: You need to know what evaluation metrics are used for RAG systems.

**Query**: "What evaluation metrics do papers use for RAG systems?"

**What happens**:
1. Agent calls `query_local_library("evaluation metrics RAG systems")`
2. Retrieves passages specifically discussing evaluation methods
3. May supplement with `search_papers` to find papers focused on benchmarking
4. Extracts and categorizes the metrics mentioned

**Expected output**:
- List of common metrics (e.g., EM, F1, ROUGE, answer accuracy)
- Benchmarks used (e.g., Natural Questions, TriviaQA, HotpotQA)
- Passage-level retrieval metrics (e.g., recall@k, MRR)
- End-to-end generation metrics
- Citations showing which papers use which metrics

### Use Case 6: Critical Analysis

**Scenario**: You want a skeptical evaluation of tool use in LLM agents.

**Configuration**: Set `system_prompt: "critical"` in config.yaml

**Query**: "Critically evaluate the evidence for tool use in LLM agents."

**What happens**:
1. Agent searches for papers on tool use in LLMs
2. Queries local library for methodology and evaluation sections
3. Examines experimental rigor: baselines, ablations, dataset sizes
4. Identifies limitations, missing comparisons, or cherry-picked examples
5. Provides skeptical assessment

**Expected output**:
- Paper-by-paper evaluation of evidence quality
- Identification of strong vs. weak experimental support
- Common limitations across papers
- Assessment of which 2-3 papers have most credible results
- Gaps in current evaluation methodology

### Use Case 7: Comparing Approaches

**Scenario**: You want to compare different multi-agent frameworks.

**Query**: "Compare the different multi-agent frameworks like CAMEL, MetaGPT, and Voyager."

**What happens**:
1. Agent searches for each framework by name
2. Queries local library for passages describing each framework's approach
3. Extracts key differences in architecture, communication, and task domains
4. May check citations to see if they cite each other
5. Synthesizes a comparative analysis

**Expected output**:
- Side-by-side comparison of frameworks
- Key differentiators (e.g., role-based vs. hierarchical, code generation vs. planning)
- Strengths and weaknesses of each
- Use cases each is best suited for
- How they relate to or build on each other

### Use Case 8: Literature Gap Analysis

**Scenario**: You're planning your thesis and need to identify research gaps.

**Query**: "What are the main gaps and open problems in LLM-based agents?"

**What happens**:
1. Agent searches broadly for surveys and recent work on LLM agents
2. Queries local library for sections discussing limitations and future work
3. Aggregates mentioned challenges across multiple papers
4. Identifies areas with sparse research or unresolved questions
5. Categorizes gaps by theme

**Expected output**:
- List of open problems mentioned across papers
- Underexplored areas (e.g., "few papers address multi-step error recovery")
- Evaluation challenges ("lack of standardized benchmarks for...")
- Technical limitations ("current approaches fail when...")
- Directions for future research

---

## Best Practices

### 1. Start Broad, Then Go Deep

Begin with Semantic Scholar searches to get an overview, then use the local library for detailed analysis:

```
Good: "Give me an overview of RAG approaches" → [gets overview] →
      "What does the local library say about evaluation metrics for RAG?"

Less optimal: Immediately querying local library without context
```

### 2. Use Specific Queries for Local Library

The RAG pipeline works best with specific, focused questions:

```
Good: "How does ReAct combine reasoning traces with action execution?"
Less optimal: "Tell me about ReAct"

Good: "What baselines does the ToolLLM paper compare against?"
Less optimal: "ToolLLM evaluation"
```

### 3. Leverage Citation Networks

Use `get_citations` to trace ideas through time:

```
1. Find a seminal paper
2. Check its references to understand foundations
3. Check its citations to see extensions and applications
4. Map the evolution of the idea
```

### 4. Combine Tools Strategically

Each tool has strengths - use them together:

```
• search_papers: Discover what exists, get citation counts
• get_paper_details: Understand a specific paper's contributions
• query_local_library: Extract exact claims and methods
• get_citations: Trace lineage and evolution
```

### 5. Adjust Configuration for Your Needs

Different research tasks benefit from different settings:

```
Exploratory research:
  - Lower similarity_threshold (get more results)
  - Higher top_k (see more passages)
  - Use "default" system prompt

Quick summary:
  - Use "concise" system prompt
  - Higher similarity_threshold (only best results)

Critical review:
  - Use "critical" system prompt
  - Query for methodology/evaluation sections
  - Larger chunk_size (more context for evaluation details)
```

### 6. Be Aware of Rate Limits

Semantic Scholar free tier allows ~1 request/second:

```
• Don't ask for many sequential searches
• Expect slight delays between API calls
• If you get a 429 error, just wait a moment and retry
```

### 7. Expand Your Local Library

The default library has ~20 papers. For your specific research area:

```
1. Add arXiv IDs to PAPERS list in download_papers.py
2. Run: python download_papers.py
3. Run: python src/pdf_ingestor.py
4. Now query_local_library covers your domain
```

### 8. Verify Important Claims

Always verify critical claims:

```
• Check if information comes from abstract only vs. full text
• Look at actual passages from query_local_library
• Verify citation counts and publication venues
• Cross-reference multiple sources
```

---

## Common Workflows

### Workflow 1: Writing a Literature Review Section

```
1. Search for topic: "Search for papers on {topic}"
2. Get overview: Agent provides summary with key papers
3. Deep dive on 2-3 key papers: "Get details for arXiv:XXXXX"
4. Extract methodology: "What methods does {paper} use?"
5. Check citations: "What papers cite {key paper}?"
6. Identify gaps: "What open problems do these papers mention?"
7. Synthesize: "Summarize the state of {topic} in 3 paragraphs"
```

### Workflow 2: Understanding a New Concept

```
1. Ask definition: "What is {concept}?"
2. Find seminal paper: Agent identifies foundational work
3. Get full details: "Get details for {seminal paper}"
4. Read key passages: "Show me passages explaining {concept}"
5. See applications: "What papers apply {concept} to..."
6. Trace evolution: "How has {concept} evolved since {year}?"
```

### Workflow 3: Validating a Research Idea

```
1. Check existing work: "Has anyone done {idea}?"
2. Find related approaches: "What similar approaches exist?"
3. Identify differences: "How does {paper A} differ from {paper B}?"
4. Find gaps: "What limitations do current approaches have?"
5. Verify novelty: "Is there work on {specific aspect}?"
6. Check recent work: "Any papers on {idea} after 2023?"
```

### Workflow 4: Preparing for Paper Reading

```
1. Get metadata: "Get details for arXiv:XXXXX"
2. Understand context: "What does this paper cite?"
3. Check impact: Look at citation count and citing papers
4. Preview key points: "Query local library for main contributions"
5. Identify related work: "Find similar papers"
6. Prepare questions: Based on gaps or unclear points
```

---

## Troubleshooting

### Issue: "No results above the similarity threshold"

**Causes**:
- Query is too specific or uses different terminology
- Similarity threshold is too high
- Relevant papers not in local library

**Solutions**:
1. Rephrase query using different terms
2. Lower `similarity_threshold` in config.yaml
3. Add relevant papers to local library
4. Use `search_papers` instead for broader coverage

### Issue: Rate limited by Semantic Scholar (HTTP 429)

**Cause**: Free tier limits ~1 request/second

**Solution**:
- Wait a moment and retry
- Don't make rapid consecutive searches
- Consider reducing number of tool calls

### Issue: Retrieved text chunks are cut off mid-sentence

**Cause**: Character-based chunking can split sentences

**Solutions**:
1. Increase `chunk_size` in config.yaml (e.g., 512 → 768)
2. Increase `chunk_overlap` (e.g., 64 → 128)
3. Re-run `python src/pdf_ingestor.py` after changes

### Issue: Results are not relevant

**Cause**: Query-document mismatch or poor embedding model

**Solutions**:
1. Make query more specific and focused
2. Try different embedding model in config.yaml:
   - "all-mpnet-base-v2" (better quality, slower)
   - "multi-qa-MiniLM-L6-cos-v1" (tuned for Q&A)
3. Re-run pdf_ingestor.py after model change

### Issue: Important paper not found in local library

**Cause**: PDF not in local collection

**Solution**:
1. Add arXiv ID to PAPERS list in download_papers.py
2. Run `python download_papers.py`
3. Run `python src/pdf_ingestor.py`
4. Retry query

### Issue: Agent doesn't follow system prompt

**Cause**: Wrong prompt selected or not restarted

**Solution**:
1. Check `agent.system_prompt` in config.yaml
2. Restart Claude Code to pick up changes
3. Verify prompt loaded: check startup messages

### Issue: Search returns outdated papers

**Cause**: Not filtering by year

**Solution**: Use year parameter in queries:
- "Find papers on {topic} after 2023"
- Agent will use `year="2024-"` parameter

---

## Tips for Advanced Users

### Creating Custom System Prompts

1. Add new prompt to `prompts/templates.py`:
```python
MY_CUSTOM_PROMPT = """Your custom instructions here..."""

TEMPLATES = {
    "default": DEFAULT_PROMPT,
    "concise": CONCISE_PROMPT,
    "structured": STRUCTURED_PROMPT,
    "critical": CRITICAL_PROMPT,
    "my_custom": MY_CUSTOM_PROMPT,  # Add here
}
```

2. Set in config.yaml:
```yaml
agent:
  system_prompt: "my_custom"
```

3. Restart MCP server

### Tuning RAG Performance

Experiment with different configurations:

```yaml
# For precision (exact matches):
rag:
  chunk_size: 256
  top_k: 3
  similarity_threshold: 0.5

# For recall (broader results):
rag:
  chunk_size: 768
  top_k: 10
  similarity_threshold: 0.2

# For Q&A style queries:
rag:
  embedding_model: "multi-qa-MiniLM-L6-cos-v1"
  chunk_size: 512
  top_k: 5
```

### Expanding the Paper Collection

Focus your library on your research area:

```python
# In download_papers.py, replace PAPERS with your domain:
PAPERS = [
    # Your research area papers
    ("2304.XXXXX", "RelevantPaper1.pdf"),
    ("2305.XXXXX", "RelevantPaper2.pdf"),
    # ... add 20-50 papers in your domain
]
```

### Combining with Other Research Tools

Use the agent as part of a broader workflow:
1. Agent finds papers and provides overview
2. You read full PDFs of key papers
3. Agent answers specific questions about details
4. You take notes and write
5. Agent verifies claims and finds citations

---

## Frequently Asked Questions

**Q: How many papers can I search?**
A: Semantic Scholar has millions of papers. Your local library is limited to PDFs you've ingested (default ~20, expandable).

**Q: Can I search non-CS papers?**
A: Yes, Semantic Scholar covers many fields. Use `fields_of_study` parameter to filter.

**Q: Why are some results marked "[abstract only]"?**
A: These papers aren't in your local library, so only metadata from Semantic Scholar is available.

**Q: Can I add papers from sources other than arXiv?**
A: Yes, but you'll need to manually download PDFs and modify the ingestion script.

**Q: How accurate are citation counts?**
A: Citation counts come from Semantic Scholar and are generally reliable but may lag slightly.

**Q: Can I search by author name?**
A: Yes, include author name in search query: "neural architecture search LeCun"

**Q: What if a paper has no arXiv ID?**
A: Use DOI instead: "DOI:10.18653/v1/..." or the Semantic Scholar paper ID.

**Q: How often should I rebuild the vector database?**
A: Only when you add new PDFs or change RAG parameters (chunk_size, embedding_model).

**Q: Can I use this for non-English papers?**
A: The default embedding model works best for English. For other languages, use multilingual models.

**Q: Is there a limit on local library size?**
A: No hard limit, but larger libraries require more disk space and slower initial embedding computation.

---

## Summary

The Literature Review Agent combines the breadth of Semantic Scholar's database with the depth of local PDF analysis to provide a powerful research assistant. Use it to:

- Discover relevant papers in your field
- Understand specific concepts and methods
- Trace the evolution of ideas
- Extract specific claims and evidence
- Identify research gaps
- Prepare for paper reading and writing

By combining the four tools strategically and configuring the system for your needs, you can dramatically accelerate your literature review process and gain deeper insights into your research area.
