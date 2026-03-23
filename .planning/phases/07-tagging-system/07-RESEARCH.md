# Phase 07: Tagging System - Research

**Researched:** 2026-03-23
**Domain:** Article tagging, embedding-based clustering, keyword matching
**Confidence:** MEDIUM-HIGH (version info verified via pip, patterns from training data)

## Summary

This phase implements a tagging system for organizing articles with three tagging mechanisms: manual CLI tagging, automatic keyword/regex matching via rules, and AI-powered embedding-based clustering. The key technical decisions (D-10 to D-13) specify using `sentence-transformers` with `all-MiniLM-L6-v2` for embeddings and `sqlite-vec` for vector storage, with DBSCAN or k-means for clustering.

**Primary recommendation:** Implement DBSCAN clustering first (auto-discovers cluster count), use PyYAML for rule config, and create a modular tagging module (`src/tags.py`) that integrates with existing `list_articles()` via a join.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **sentence-transformers** | 5.3.x | Embedding generation | Industry standard for sentence embeddings, all-MiniLM-L6-v2 is lightweight (384d) and fast |
| **sqlite-vec** | 0.1.x | Vector storage in SQLite | Native SQLite extension, no separate vector DB needed |
| **scikit-learn** | 1.8.x | Clustering algorithms | Standard ML library, DBSCAN and k-means implementations |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **PyYAML** | 6.0.x | YAML config parsing | Rule file parsing (installed: 6.0.2) |
| **numpy** | (dependency of sklearn) | Array operations | Embedding matrix operations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sqlite-vec | ChromaDB, Qdrant | Those need separate services; sqlite-vec keeps single-file SQLite |
| sentence-transformers | OpenAI embeddings | Conflicts with no-API constraint in CLAUDE.md |
| DBSCAN | k-means only | k-means requires pre-specifying k; DBSCAN auto-discovers |

**Installation:**
```bash
pip install sentence-transformers sqlite-vec scikit-learn
```

**Version verification:**
- sentence-transformers: 5.3.0 (latest as of research)
- sqlite-vec: 0.1.7 (latest)
- scikit-learn: 1.8.0 (latest)
- PyYAML: 6.0.3 (latest)

## Architecture Patterns

### Recommended Project Structure
```
src/
├── tags.py           # NEW: Tag operations, embedding, clustering
├── tag_rules.py      # NEW: Keyword/regex rule management
├── cli.py            # MODIFY: Add tag commands, article tag option
├── models.py         # MODIFY: Add Tag dataclass
├── db.py             # MODIFY: Add tags, article_tags, tag_rules tables
└── articles.py       # MODIFY: Add tag filtering to list_articles
```

### Pattern 1: Tag Dataclass (models.py)
```python
# Source: Standard dataclass pattern from existing models.py
@dataclass
class Tag:
    id: str
    name: str
    created_at: str
```

### Pattern 2: Embedding Generation (tags.py)
```python
# Source: sentence-transformers documentation
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
# Generate embedding for article title + description
text = f"{article.title} {article.description}"
embedding = model.encode(text, normalize_embeddings=True)
# Returns 384-dimensional vector
```

### Pattern 3: sqlite-vec Storage
```python
# Source: sqlite-vec documentation
import sqlite_vec

# Register extension
conn = get_connection()
conn.enable_load_extension(True)
conn.load_extension("vec0")  # Built-in vector support

# Create virtual table for article embeddings
cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS article_embeddings USING vec0(
        article_id TEXT PRIMARY KEY,
        embedding FLOAT[384]
    )
""")

# Store embedding
cursor.execute("""
    INSERT OR REPLACE INTO article_embeddings (article_id, embedding)
    VALUES (?, ?)
""", (article_id, embedding.tolist()))

# Similarity search (top-k)
cursor.execute("""
    SELECT article_id, distance
    FROM article_embeddings
    WHERE embedding MATCH ?
    ORDER BY distance
    LIMIT 5
""", (query_embedding.tolist(),))
```

### Pattern 4: DBSCAN Clustering
```python
# Source: scikit-learn documentation
from sklearn.cluster import DBSCAN

# embeddings is numpy array of shape (n_articles, 384)
clustering = DBSCAN(eps=0.3, min_samples=3, metric='cosine')
labels = clustering.fit_predict(embeddings)
# labels: -1 for noise (outliers), 0, 1, 2... for clusters
```

### Pattern 5: YAML Rule Config (tag_rules.py)
```python
# Source: PyYAML documentation
import yaml
from pathlib import Path

RULES_PATH = Path.home() / ".radar" / "tag-rules.yaml"

def load_rules() -> dict:
    if not RULES_PATH.exists():
        return {"tags": {}}
    with open(RULES_PATH) as f:
        return yaml.safe_load(f) or {"tags": {}}

def save_rules(rules: dict) -> None:
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RULES_PATH, "w") as f:
        yaml.safe_dump(rules, f)
```

### Anti-Patterns to Avoid
- **First-match-only rule conflict:** Decision D-09 specifies apply ALL matching tags, not stop at first
- **API-based embeddings:** CLAUDE.md specifies "No API" — must use local sentence-transformers
- **Creating tags without user review for AI clustering:** D-13 says auto-generate directly (user can delete)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Embedding generation | Custom TF-IDF or word vectors | sentence-transformers | all-MiniLM-L6-v2 is pre-trained, optimized, 384d vs thousands for custom |
| Vector similarity search | Custom cosine similarity loops | sqlite-vec | Native SQLite extension, optimized queries, no separate DB |
| Clustering | Custom centroid computation | sklearn DBSCAN/k-means | Well-tested, handles edge cases |
| YAML parsing | String splitting/regex | PyYAML | Handles nested structures, escape sequences, comments |

**Key insight:** Sentence embeddings + sqlite-vec is the minimal stack for local AI tagging without external services.

## Runtime State Inventory

> This is a new feature phase, not a rename/refactor — no existing runtime state to inventory.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None (new feature) | N/A |
| Live service config | None (new feature) | N/A |
| OS-registered state | None (new feature) | N/A |
| Secrets/env vars | None | None |
| Build artifacts | None (new feature) | N/A |

## Common Pitfalls

### Pitfall 1: sqlite-vec Extension Not Loaded
**What goes wrong:** `sqlite3 OperationalError: no such module: vec0`
**Why it happens:** sqlite-vec is a loadable extension, must be explicitly loaded
**How to avoid:** Call `conn.enable_load_extension(True)` and `conn.load_extension("vec0")` before any vec operations
**Warning signs:** First similarity query fails with "no such module"

### Pitfall 2: Embedding Model Download on First Use
**What goes wrong:** First embedding generation is slow (downloads ~90MB model)
**Why it happens:** all-MiniLM-L6-v2 not cached locally
**How to avoid:** Pre-warm cache with `SentenceTransformer('all-MiniLM-L6-v2')` during init or show user message
**Warning signs:** CLI hangs for 10-30 seconds on first `article tag --auto` call

### Pitfall 3: DBSCAN eps Parameter Sensitivity
**What goes wrong:** Too small eps -> too many clusters or all noise; too large eps -> one giant cluster
**Why it happens:** eps is distance threshold for "density"
**How to avoid:** Start with eps=0.3-0.5 for cosine similarity (normalized embeddings); min_samples=3-5
**Warning signs:** Cluster count is 0 (all noise) or >50% of articles in one cluster

### Pitfall 4: Empty Articles Cause Embedding Errors
**What goes wrong:** Articles with no title/description fail embedding
**Why it happens:** `model.encode("")` or `model.encode(None)` raises error
**How to avoid:** Skip articles with empty text, or use placeholder "No content"
**Warning signs:** Embedding batch job fails on first empty article

### Pitfall 5: YAML Config Overwrites Manual Edits
**What goes wrong:** Rule save is not merge-safe (loads, modifies, writes full file)
**Why it happens:** Race condition if two processes modify simultaneously
**How to avoid:** Document as single-user tool (personal RSS reader assumption); lock file if needed
**Warning signs:** Manual rule edits disappear after CLI rule add

## Code Examples

### Tag Rule Matching (tag_rules.py)
```python
# Source: Python regex documentation
import re

def match_article_to_tags(article_title: str, article_desc: str, rules: dict) -> list[str]:
    """Apply all matching rules to an article. Returns list of matching tag names."""
    matched_tags = []
    text = f"{article_title} {article_desc}".lower()

    for tag_name, rule in rules.get("tags", {}).items():
        # Check keywords (case-insensitive substring match)
        for kw in rule.get("keywords", []):
            if kw.lower() in text:
                matched_tags.append(tag_name)
                break  # Tag matched, move to next tag

        # Check regex patterns
        for pattern in rule.get("regex", []):
            if re.search(pattern, text, re.IGNORECASE):
                matched_tags.append(tag_name)
                break

    return matched_tags
```

### Cluster Discovery to Tags (tags.py)
```python
# Source: sklearn DBSCAN documentation
def discover_clusters(embeddings: numpy.ndarray, eps: float = 0.3, min_samples: int = 3) -> dict[int, list[str]]:
    """Run DBSCAN on embeddings. Returns {cluster_label: [article_ids]}."""
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
    labels = clustering.fit_predict(embeddings)

    clusters = {}
    for article_id, label in zip(article_ids, labels):
        if label == -1:  # Noise point, skip or assign to special cluster
            continue
        clusters.setdefault(label, []).append(article_id)

    return clusters
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual tagging only | + Keyword/regex auto-tagging | Now | Reduces manual effort |
| Manual tagging only | + AI clustering | Now | Discovers topics without pre-defining |
| External vector DB | sqlite-vec (SQLite extension) | Now | Single-file storage, no separate service |
| TF-IDF embeddings | sentence-transformers | Now | Better semantic understanding |

**Deprecated/outdated:**
- LDA (Latent Dirichlet Allocation): Older topic modeling, slower, assumes bag-of-words
- ChromaDB for local vectors: Requires separate service process

## Open Questions

1. **DBSCAN eps tuning for articles**
   - What we know: eps=0.3 with cosine metric is a starting point for normalized embeddings
   - What's unclear: Optimal eps for RSS article titles/descriptions (may need user config)
   - Recommendation: Expose as CLI option `--cluster-eps` with default 0.3

2. **Cluster to tag name generation**
   - What we know: DBSCAN gives cluster assignments, not names
   - What's unclear: How to auto-generate human-readable tag names from cluster articles
   - Recommendation: Use most frequent keyword in cluster articles as suggested tag name

3. **Embedding batch size**
   - What we know: all-MiniLM-L6-v2 is efficient, handles batch encoding
   - What's unclear: Optimal batch size for personal RSS reader (typically <1000 articles)
   - Recommendation: Batch size 32-64, full corpus in one batch is fine for <10k articles

## Environment Availability

> Step 2.6: SKIPPED (no external dependencies identified beyond Python packages)

**Analysis:** Phase uses only Python packages (sentence-transformers, sqlite-vec, scikit-learn, PyYAML) which are pip-installable. No external services, CLIs, or runtimes required beyond the project's existing Python 3.6+ dependency.

**Missing dependencies with no fallback:**
- None (all are pip-installable)

## Sources

### Primary (HIGH confidence - version info from pip registry)
- `pip index versions sentence-transformers` - Version 5.3.0 verified
- `pip index versions sqlite-vec` - Version 0.1.7 verified
- `pip index versions scikit-learn` - Version 1.8.0 verified
- `pip index versions PyYAML` - Version 6.0.3 verified (installed: 6.0.2)

### Secondary (MEDIUM confidence - training data, not verified)
- sentence-transformers encode() API pattern from library documentation
- sqlite-vec virtual table syntax from library README
- sklearn DBSCAN parameters (eps, min_samples, metric) from sklearn docs

### Tertiary (LOW confidence - training data only)
- DBSCAN eps=0.3 for cosine similarity normalization heuristic
- Model download size (~90MB) for all-MiniLM-L6-v6

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions verified via pip
- Architecture: MEDIUM - patterns from training data, not Context7 verified
- Pitfalls: MEDIUM - common issues identified from experience

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (30 days - library versions are stable)
