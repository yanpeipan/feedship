# Phase 23: nanoid Code Changes - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Replace uuid.uuid4() with nanoid.generate() in storage functions:
- store_article() — article id generation (line 334)
- add_tag() — tag id generation (line 181)
- tag_article() — article_tag entry id generation

All functions use nanoid>=2.0.0 package (separate from uuid module).
New IDs are 21 chars URL-safe (vs 36 chars for UUID).
</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP success criteria and codebase conventions to guide decisions.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- nanoid>=2.0.0 is already added to pyproject.toml dependencies
- nanoid package provides nanoid.generate() function

### Established Patterns
- UUID was generated inline: `uuid.uuid4().hex`
- Need to replace with: `nanoid.generate()`

### Integration Points
- src/storage/sqlite.py — store_article(), add_tag(), tag_article() functions
- All changes local to storage layer
</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Standard approach:
1. Import nanoid at top of storage module
2. Replace uuid.uuid4().hex with nanoid.generate() in each function
3. Verify nanoid>=2.0.0 is in dependencies (already done)
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope
</deferred>
