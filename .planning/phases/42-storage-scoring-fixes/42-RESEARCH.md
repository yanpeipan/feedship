# Phase 42: Storage Scoring Fixes - Research

**Researched:** 2026-03-28
**Domain:** SQLite storage layer scoring normalization
**Confidence:** HIGH

## Summary

Phase 42 delivers two targeted fixes to the storage layer scoring: (1) BM25 sigmoid normalization in `search_articles`, and (2) freshness field population in `list_articles`. Both are prerequisites for Phase 43's application-layer `combine_scores()` function. The implementation is well-scoped with locked decisions from CONTEXT.md.

**Primary recommendation:** Implement exactly as specified in CONTEXT.md decisions. The formulas are confirmed, code locations are identified, and the approach is straightforward.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-13:** `search_articles` in `storage/sqlite/impl.py` uses sigmoid normalization: `sigmoid_norm(bm25_raw, factor) = 1 / (1 + exp(bm25_raw * factor))`
- **D-14:** `bm25_score` field on ArticleListItem populated by `search_articles` with 0-1 range
- **D-17:** BM25 factor comes from `config.py` (key: `bm25_factor`, default `0.5`)
- **D-18:** Replace current WRONG `abs()` approach: `score = 1 / (1 + abs(row["bm25_score"]))` with correct sigmoid
- **D-15:** `list_articles` in `storage/sqlite/impl.py` populates `freshness` using Newton's cooling law: `exp(-days_ago / half_life_days)` with `half_life_days = 7`
- **D-16:** `vec_sim`, `bm25_score`, `ce_score` set to 0.0 when not applicable
- **D-19:** days_ago computed from pub_date via `_pub_date_to_timestamp()` then `datetime.fromtimestamp(pub_ts, tz=timezone.utc)` then `(now - pub_dt).days`
- **D-20:** `pub_date` in storage is INTEGER unix timestamp - use `_pub_date_to_timestamp()` consistently
- **D-21:** Freshness formula: `exp(-days_ago / 7)` - value 0-1, recent articles score near 1.0
- **D-22:** `source_weight` remains 0.3 default (per ArticleListItem field default)

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within Phase 42 scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEARCH-03 | `search_articles` BM25 sigmoid normalization: `sigmoid_norm(bm25_raw, factor)`, factor from `config.py` (default 0.5), populate `ArticleListItem.bm25_score` | Confirmed: current impl.py:759 uses wrong `abs()` approach |
| SEARCH-04 | `list_articles` freshness population (time decay 0-1), missing vec_sim/bm25_score/ce_score set to 0.0 | Confirmed: current impl.py:528-540 returns bare ArticleListItem with defaults |

## Standard Stack

### Implementation Libraries
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `math` | built-in | `math.exp()` for sigmoid and freshness | Standard library, no new dependencies |
| `datetime.timezone` | built-in | UTC timezone handling | Standard library |
| `_pub_date_to_timestamp()` | existing | Convert pub_date to unix timestamp | Already exists in `src/storage/vector.py:30-61` |

### Config Integration
| Key | Location | Default | Purpose |
|-----|----------|---------|---------|
| `bm25_factor` | `src/application/config.py` + `config.yaml` | 0.5 | Sigmoid normalization factor for BM25 scores |

## Architecture Patterns

### Recommended Project Structure
No structural changes - this is a targeted fix within existing files.

### Pattern 1: BM25 Sigmoid Normalization
**What:** Replace `abs()` normalization with true sigmoid
**When to use:** `search_articles` return value preparation
**Implementation:**
```python
# Current WRONG at impl.py:759
score=1 / (1 + abs(row["bm25_score"]))

# Correct sigmoid normalization (D-13, D-18)
import math
from src.application.config import get_bm25_factor  # NEW getter needed
factor = get_bm25_factor()
score = 1 / (1 + math.exp(row["bm25_score"] * factor))
```

### Pattern 2: Freshness via Newton's Cooling Law
**What:** Calculate article freshness as exponential time decay
**When to use:** `list_articles` return value preparation
**Implementation:**
```python
# D-15, D-19, D-21
from datetime import datetime, timezone
from src.storage.vector import _pub_date_to_timestamp
import math

pub_ts = _pub_date_to_timestamp(r.get("pub_date"))
freshness = 0.0
if pub_ts:
    pub_dt = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
    days_ago = (datetime.now(timezone.utc) - pub_dt).days
    freshness = math.exp(-days_ago / 7)  # half_life_days = 7
```

### Pattern 3: ArticleListItem Field Population
**What:** Explicitly set scoring fields in list_articles
**When to use:** When returning ArticleListItem from list_articles
**Fields to populate:**
- `freshness` = calculated via Newton's cooling law
- `vec_sim` = 0.0 (no semantic data in list_articles)
- `bm25_score` = 0.0 (no FTS data in list_articles)
- `ce_score` = 0.0 (no cross-encoder data in list_articles)
- `source_weight` = 0.3 (default, per D-22)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timestamp parsing | Custom pub_date parsing | `_pub_date_to_timestamp()` | Already handles RFC 2822, ISO, unix formats correctly |
| Timezone-aware datetime |naive datetime arithmetic | `datetime.now(timezone.utc)` | Avoids timezone bugs |
| Exponential decay | Custom decay formula | `math.exp(-days_ago / 7)` | Newton's cooling law is well-understood |
| Sigmoid normalization | Custom sigmoid | `1 / (1 + math.exp(x))` | Standard logistic function |

## Code Locations (Confirmed)

| File | Function | Lines | Current State |
|------|----------|-------|---------------|
| `src/storage/sqlite/impl.py` | `list_articles` | 478-540 | Returns bare ArticleListItem, no scoring fields |
| `src/storage/sqlite/impl.py` | `search_articles` | 660-762 | Uses wrong `abs()` normalization at line 759 |
| `src/application/config.py` | config module | full | Missing `get_bm25_factor()` function |
| `src/storage/vector.py` | `_pub_date_to_timestamp` | 30-61 | Already exists, handles multiple formats |
| `src/application/articles.py` | `ArticleListItem` | 19-48 | Has all 6 scoring fields with defaults |

## Common Pitfalls

### Pitfall 1: Wrong BM25 Normalization
**What goes wrong:** `abs()` approach inverts the intended scoring - higher BM25 scores become lower, and negative BM25 scores get same treatment as positive
**Why it happens:** BM25 scores from SQLite FTS5 can be negative or positive; `abs()` destroys this information
**How to avoid:** Use sigmoid normalization as specified in D-13
**Warning signs:** `score=1 / (1 + abs(row["bm25_score"]))` anywhere in code

### Pitfall 2: Pub Date Format Assumption
**What goes wrong:** Assuming pub_date is ISO string when it's actually INTEGER unix timestamp in SQLite
**Why it happens:** The context explicitly states pub_date is INTEGER unix timestamp (D-20)
**How to avoid:** Always use `_pub_date_to_timestamp()` to convert before datetime operations
**Warning signs:** Calling `datetime.fromisoformat()` directly on pub_date

### Pitfall 3: Timezone Mismatch
**What goes wrong:** Comparing naive datetime with timezone-aware datetime causes TypeError
**Why it happens:** `datetime.now(timezone.utc)` is timezone-aware, but pub_dt must also be timezone-aware
**How to avoid:** Use `datetime.fromtimestamp(pub_ts, tz=timezone.utc)` consistently (D-19)

### Pitfall 4: Missing Math Import
**What goes wrong:** `math.exp()` fails if `math` module not imported
**Why it happens:** Need to add `import math` to impl.py if not present
**How to avoid:** Verify `import math` exists at top of impl.py

## Config Changes Required

### New config.yaml entry
```yaml
# For BM25 sigmoid normalization in search_articles
bm25_factor: 0.5  # D-17: default 0.5
```

### New config.py getter
```python
# Add to src/application/config.py (D-17)
def get_bm25_factor() -> float:
    """Return the BM25 sigmoid normalization factor."""
    return _get_settings().get("bm25_factor", 0.5)
```

## Open Questions

1. **None identified** - All decisions are locked in CONTEXT.md and verified against existing code.

## Sources

### Primary (HIGH confidence)
- CONTEXT.md decisions D-13 through D-22 - locked implementation decisions
- impl.py:759 - current wrong `abs()` approach confirmed
- ArticleListItem dataclass - 6 scoring fields confirmed

### Secondary (MEDIUM confidence)
- `_pub_date_to_timestamp()` in vector.py:30-61 - verified exists and handles multiple formats

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - using built-in math and existing utilities
- Architecture: HIGH - targeted fixes within existing code structure
- Pitfalls: HIGH - pitfalls well-understood from locked decisions

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable phase, locked decisions)
