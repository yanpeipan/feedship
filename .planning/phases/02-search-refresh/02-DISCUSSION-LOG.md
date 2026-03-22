# Phase 2: search-refresh - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-03-23
**Phase:** 02-search-refresh
**Mode:** assumptions
**Areas analyzed:** FTS5 Implementation, Search Query Interface, Search Results Display, CLI Command Structure, Conditional Fetching

## Assumptions Presented

### FTS5 Implementation Approach
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Shadow FTS5 virtual table with manual sync | Likely | src/db.py init_db(), src/feeds.py refresh_feed() |
| Index title, description, content fields | Confident | src/models.py Article dataclass |

### Search Query Interface
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Expose FTS5 query syntax directly | Likely | SQLite FTS5 standard |
| Multiple keywords default to AND | Confident | FTS5 MATCH behavior |

### Search Results Display
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Same format as article list | Confident | src/cli.py article_list command |
| Sort by FTS5 bm25 ranking | Confident | FTS5 relevance scoring |

### CLI Command Structure
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| article search subcommand with --limit, --feed-id | Confident | src/cli.py existing patterns |

### Conditional Fetching
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Already implemented in Phase 1 | Confident | src/feeds.py lines 39-75, 326-348 |

## Corrections Made

No corrections — all assumptions confirmed.

## Auto-Resolved

{If --auto and Unclear items existed:}
- {Assumption}: auto-selected {recommended option}

{If not applicable: omit this section}

## External Research

- FTS5 query parser edge cases: special character handling, empty queries
- Whether to use highlight() and snippet() FTS5 functions

{If no research: omit this section}
