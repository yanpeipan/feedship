# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.3 — Provider Architecture

**Shipped:** 2026-03-23
**Phases:** 4 | **Plans:** 9 | **Sessions:** ~3

### What Was Built
- Provider plugin architecture: ContentProvider Protocol with @runtime_checkable, dynamic loading via glob+importlib, ProviderRegistry with discover/discover_or_default
- RSSProvider (priority=50) and GitHubProvider (priority=100) with self-registration via PROVIDERS.append()
- TagParser plugin system with chain_tag_parsers(), DefaultTagParser wrapping tag_rules, lazy loading to avoid circular imports
- CLI unified: fetch --all via discover_or_default(), feed add auto-detects provider, repo commands deleted
- PyGithub refactor: src/github.py (808 lines) deleted, replaced by PyGithub 2.x with singleton client pattern

### What Worked
- Wave-based parallel execution kept phase execution fast (~3 min per plan)
- Protocol + @runtime_checkable provided good type safety without rigid inheritance
- Self-registration via module-level PROVIDERS.append() avoided explicit registration calls
- Module extraction refactor (github.py → github_utils.py + github_ops.py) cleanly separated concerns

### What Was Inefficient
- Circular import between providers and tags required lazy loading workaround
- PyGithub RateLimitException naming differed from plan (had to auto-fix during execution)
- Phase 14 auto-fixed non-existent ProviderRegistry class (plan specified class method, codebase had function)

### Patterns Established
- Provider priority ordering: GitHub(100) > RSS(50) > Default(0)
- Error isolation at crawl/parse level: log.error and return [], never crash
- DATABASE: feeds.metadata JSON field for provider-specific data (github_repos migrated)
- Singleton pattern for PyGithub client: _get_github_client() lazy initialization at module level

### Key Lessons
1. Protocol-based interfaces with @runtime_checkable work well for plugin architectures — structural typing beats inheritance
2. Phase plans that don't match actual codebase structure cause auto-fixes during execution — validate API shape before writing plan code
3. Module-level singleton clients (PyGithub, etc.) avoid re-initialization overhead on repeated calls

### Cost Observations
- Model mix: predominantly sonnet for planning, haiku for execution
- Sessions: ~3 sessions for full milestone
- Notable: v1.3 was highly parallelizable (9 plans) but executed cleanly in 2 waves

---

## Milestone: v1.9 — Automatic Discovery Feed + v1.10/v1.11 uvloop

**Shipped:** 2026-03-28
**Phases:** 10 (34-40) | **Plans:** 10 | **Sessions:** ~3

### What Was Built

**v1.9 Automatic Discovery Feed:**
- Discovery Core Module (`src/discovery/`): HTML `<link>` tag parsing, well-known path fallback, URL resolution with `<base href>` override, feed validation via HEAD+Content-Type
- `discover <url>` CLI command with `--discover-deep [n]` for feed discovery
- `feed add <url> --discover --automatic` integration
- BFS crawler: visited-set deduplication, 2s/host rate limiting, CSS selector-based link discovery
- robots.txt compliance via robotexclusionrulesparser (lazy mode)
- Multi-factor ranking: `final_score = 0.5*norm_similarity + 0.3*norm_freshness + 0.2*source_weight`

**v1.10 uvloop Best Practices:**
- Simplified `install_uvloop()` to just `uvloop.install()` with platform check
- Removed dead code: `_default_executor`, `_get_default_executor()`, `run_in_executor_crawl()`, `_main_loop`
- `asyncio_utils.py`: 93 lines → 44 lines

**v1.11 Comprehensive uvloop Audit:**
- Verified zero `asyncio.run()` calls in `src/`
- 5 `uvloop.run()` calls at correct CLI boundaries (feed.py ×4, discover.py ×1)
- All async providers use true async patterns
- No blocking I/O outside `asyncio.to_thread()`

### What Worked
- Scrapling for HTML parsing proved better than BeautifulSoup (adaptive parsing + JS support)
- CSS selector-based link discovery replaced brittle hardcoded subdirectory names
- Discovery as separate service module (not Provider plugin) kept concerns clean
- `uvloop.install()` is idempotent — no need to track whether already called

### What Was Inefficient
- CLI `gsd-tools milestone complete` had a bug: wrote entire ROADMAP.md into archive instead of extracting just v1.9 phases — manually fixed
- Phase 32 plan reference was wrong in ROADMAP.md (pointed to 40-01-PLAN.md instead of proper plan)
- MILESTONES.md accomplishments got garbled by `summary-extract` splitting on "Plan:" / "Phase:" delimiters

### Patterns Established
- Discovery module: `src/discovery/` as service module, NOT a Provider plugin
- BFS crawler: visited-set + rate-limit + robots.txt = professional-grade crawler
- Multi-factor ranking: configurable weights for similarity/freshness/source priority
- `uvloop.run()` ONLY at CLI boundaries, all async code flows through it

### Key Lessons
1. `summary-extract` tool breaks on multi-line descriptions with Chinese content — manually craft accomplishments strings
2. `gsd-tools milestone complete` CLI needs verification before trusting — inspects archive files after running
3. Inline phase entries in ROADMAP.md accumulate cruft — collapse milestones into `<details>` blocks immediately

### Cost Observations
- Model mix: sonnet for planning, haiku for execution, opus for verification
- Sessions: ~3 sessions for milestone chain (v1.9 → v1.10 → v1.11)
- Notable: uvloop phases (39-40) were quick audits, not full implementations

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~3 | 3 | GSD workflow established |
| v1.1 | ~1 | 4 | Phase planning refined |
| v1.2 | ~1 | 4 | Fast execution, gap closure |
| v1.3 | ~3 | 4 | Wave-based parallelism, module extraction refactor |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 0 | N/A | 6 deps |
| v1.1 | 0 | N/A | PyGithub (replaces httpx raw) |
| v1.2 | 0 | N/A | rich (CLI output) |
| v1.3 | 0 | N/A | @runtime_checkable (stdlib) |

### Top Lessons (Verified Across Milestones)

1. No test suite — would catch import regressions and API mismatches quickly
2. Wave-based parallel execution reduces wall-clock time significantly on multi-plan phases
3. CLI tool with personal use case doesn't need async/caching complexity — simplicity wins
