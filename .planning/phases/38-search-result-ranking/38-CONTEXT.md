# Phase 38: Search Result Ranking - Context

**Gathered:** 2026-03-28 (--auto mode, user provided full algorithm)
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement multi-factor ranking algorithm for semantic search results that combines normalized cosine similarity (50%), normalized freshness (30%), and configurable source weights (20%) to produce a ranked article list. This affects `search --semantic` output ordering; FTS search remains unchanged.

</domain>

<decisions>
## Implementation Decisions

### Algorithm (D-01)
- **Final score formula:** `final_score = 0.5 * norm_similarity + 0.3 * norm_freshness + 0.2 * source_weight`
- **norm_similarity:** cosine similarity from ChromaDB L2 distance, min-max normalized to [0, 1] across result set
  - Conversion: `cos_sim = max(0.0, 1.0 - dist²/2)` (already in `format_semantic_results`)
  - Normalization: `(cos_sim - min) / (max - min)` across returned results
- **norm_freshness:** `1 - (days_ago / max_days)` where max_days = 30 (articles older than 30 days score 0)
- **source_weight:** per-domain weight from feed URL domain
- **Sort:** descending by final_score, return top 10

### Source Weights (D-02)
- Hardcoded dict for initial implementation: `{'openai.com': 1.0, 'arxiv.org': 0.9, 'medium.com': 0.5, 'default': 0.3}`
- Future: move to config file or `--source-weights` CLI flag (deferred)
- Domain matching: use URL domain suffix match (e.g., `blog.openai.com` → `openai.com`)

### Legacy Articles (pre-v1.8) Handling (D-03)
- Articles fetched before v1.8 have no ChromaDB embedding — they are **excluded** from ranked semantic results
- Rationale: ranking requires similarity score — without embedding, article cannot be scored

### Integration Point (D-04)
- New function `rank_semantic_results(results: list[dict], top_k: int = 10) -> list[dict]` in `src/application/search.py`
- Called by `search --semantic` CLI command after `search_articles_semantic()` returns results
- Does NOT modify ChromaDB query itself — applies ranking to already-fetched results

### FTS Search Unchanged (D-05)
- FTS keyword search (`search <query>` without `--semantic`) returns results by FTS relevance only
- Ranking algorithm applies only to semantic search results

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Search Application Layer
- `src/application/search.py` — existing `format_semantic_results()` with L2→cosine similarity conversion (line 49-52)
- `src/storage/vector.py` — `search_articles_semantic()` returns list of dicts with article_id, sqlite_id, title, url, distance, document

### ChromaDB Infrastructure (Phase 30)
- `.planning/phases/30-semantic-search-infrastructure/30-CONTEXT.md` — ChromaDB setup, all-MiniLM-L6-v2 model, collection schema

### Incremental Embedding (Phase 31)
- `.planning/phases/31-write-path-incremental-embedding/31-CONTEXT.md` — embedding write path, add_article_embedding()

### CLI Article Commands
- `src/cli/article.py` — `search` command with `--semantic` flag, calls `search_articles_semantic()`

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- `src/application/search.py:format_semantic_results()` — already converts L2 distance to cosine similarity (line 49-52)
- ChromaDB `search_articles_semantic()` returns full result dicts with distance, title, url, article_id

### Established Patterns
- Formatting functions in `src/application/search.py` separate display logic from CLI
- Ranking should follow same pattern: pure function in `search.py`, no CLI deps

### Integration Points
- `src/cli/article.py` `search` command — calls `search_articles_semantic()` then `format_semantic_results()` → ranking should go between these two steps

</codebase_context>

<specifics>
## Specific Ideas

### User-Provided Algorithm (from pseudocode)
```python
# 1. Normalize similarity (0-1)
df['norm_similarity'] = (df['similarity_score'] - min) / (max - min)
# 2. Normalize freshness (newer = higher)
df['norm_freshness'] = 1 - (days_ago / max_days)
# 3. Source weights
source_weights = {'openai.com': 1.0, 'arxiv.org': 0.9, 'medium.com': 0.5, 'default': 0.3}
# 4. Final score
df['final_score'] = 0.5 * norm_similarity + 0.3 * norm_freshness + 0.2 * source_weight
# 5. Sort descending, return top 10 IDs
```

</specifics>

<deferred>
## Deferred Ideas

- Source weights CLI config (`--source-weights` flag or config file) — hardcoded dict for now
- FTS + semantic hybrid scoring — FTS search remains separate
- Adjustable weight ratios via CLI flags — fixed 0.5/0.3/0.2 for v1

</deferred>
