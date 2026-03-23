# Project Research Summary

**Project:** Personal Information System (RSS Reader CLI)
**Domain:** Python CLI tool for feed aggregation with plugin-based provider architecture
**Researched:** 2026-03-23
**Confidence:** MEDIUM-HIGH

## Executive Summary

This project is a Python CLI tool that aggregates RSS feeds, GitHub releases, and website content into a unified local SQLite database. The core value proposition is centralized information management without requiring a server or web interface. The v1.3 initiative introduces a plugin-based provider architecture to replace the current hardcoded RSS/GitHub handling, allowing new source types to be added without modifying core code.

Research strongly supports using the `pluggy` library (already installed) with a `ContentProvider` Protocol as the foundation for the plugin system. The key architectural decision is treating GitHub repos and RSS feeds as different "providers" implementing a common interface, stored in a unified `feeds` table with a JSON `metadata` column for provider-specific data. The migration must use a strangler fig pattern - existing functionality continues working while the plugin system is introduced alongside, never replacing legacy code until verified.

The primary risks are circular import chains during plugin loading and interface drift between providers. Both are mitigated by defining the `ContentProvider` Protocol with `@runtime_checkable` before implementing any providers, using lazy imports in plugin `__init__.py` files, and wrapping all provider calls in error isolation.

## Key Findings

### Recommended Stack

The technology stack is mature and well-established. Core dependencies (feedparser 6.0.x, httpx 0.27.x, BeautifulSoup4 4.12.x, lxml 5.x, click 8.1.x) are all actively maintained with high-confidence documentation. For v1.3 specifically, `pluggy` (already installed) provides industry-standard plugin management via `PluginManager` with `load_setuptools_entrypoints()`.

**Core technologies:**
- **feedparser 6.0.x** — Universal RSS/Atom parser, handles all common feed formats
- **httpx 0.27.x** — HTTP client for GitHub API and web scraping; async-capable when needed
- **BeautifulSoup4 + lxml** — HTML parsing with convenient navigation API
- **pluggy 1.5.0** — Plugin framework (already installed), pytest standard
- **sqlite3** (built-in) — Database; single-file storage is sufficient for personal use
- **rich 13.x** — Terminal formatting for article list/detail views

### Expected Features

**Must have (table stakes):**
- URL-based feed detection — system auto-detects feed type from URL
- RSS/Atom parsing — standard feeds handled via feedparser
- Provider registration — registry pattern with `match()` method per provider
- Refresh orchestration — unified refresh across all providers
- Tag rule application — auto-tagging after article storage via existing tag_rules.py

**Should have (competitive differentiators):**
- Plugin priority ordering — higher priority providers checked first (GitHub before generic URL)
- Provider-specific tag parsers — each provider can have custom tag extraction
- Graceful fallthrough — unknown URL types fall through to generic crawler

**Defer (v2+):**
- Plugin hot-reloading — CLI restart is fine for personal tool
- Plugin configuration per-instance — global config + feed metadata instead
- Async parallel refresh — sequential for now; add ThreadPoolExecutor later if needed
- External plugin discovery — directory scanning or entry_points for third-party plugins

### Architecture Approach

The architecture introduces a `ContentProvider` Protocol defining the contract all providers must implement: `name`, `provider_type`, `add()`, `refresh()`, and `can_handle()`. A `ProviderRegistry` manages discovery and dispatch. The key insight is unifying `feeds` and `github_repos` tables by adding a `metadata` JSON column to `feeds`, storing provider-specific data like `{"provider": "github", "owner": "owner", "repo": "repo"}`. Existing `feeds.py` and `github.py` become thin wrappers around their respective providers initially, then are refactored over time using the strangler fig pattern.

**Major components:**
1. **ContentProvider Protocol** — Abstract interface defining required methods; use `@runtime_checkable` for early error detection
2. **ProviderRegistry** — Singleton managing provider registration and URL-based discovery via `can_handle()`
3. **RSS/Atom Provider** — Wraps existing feeds.py refresh logic, priority 50
4. **GitHub Provider** — Wraps existing github.py release/changelog logic, priority 100 (checked first)

### Critical Pitfalls

1. **Circular Import Chain** — Classic chicken-and-egg when plugin imports core at module level. Avoid by using `TYPE_CHECKING` for type hints, lazy imports inside functions, and never importing shared state in plugin `__init__.py`.

2. **Plugin Interface Drift** — No explicit Protocol definition leads to cryptic runtime errors. Define `ContentProvider` with `@runtime_checkable` before implementing any providers; validate at load time.

3. **No Isolation** — One buggy plugin crashes entire application. Wrap all provider calls in try/except, log provider name, continue with other providers on failure.

4. **Hardcoded Migration Trap** — Replacing old code before new system is verified breaks existing feeds. Use strangler fig pattern: keep old code working, add plugin system alongside, migrate incrementally with feature flag.

5. **Entry Point Discovery Failures** — Plugins installed but not discovered due to misconfigured `pyproject.toml`. Validate entry points load correctly during development; log discovered plugins at startup.

## Implications for Roadmap

Based on research, the recommended phase structure:

### Phase 1: Plugin Core Infrastructure
**Rationale:** Foundation must be correct before providers can be implemented. Interface definition and registry are prerequisites for everything else.

**Delivers:**
- `src/providers/base.py` with `ContentProvider` Protocol (using `@runtime_checkable`)
- `src/providers/registry.py` with `ProviderRegistry` singleton
- `feeds.metadata` column migration (JSON, nullable)
- Error isolation wrapper for provider calls
- API versioning contract in base provider

**Addresses:** Table stakes (provider registration, refresh orchestration), Critical pitfalls 1, 2, 3, 5

**Avoids:** Circular imports (lazy imports), interface drift (Protocol first), no isolation (try/except wrapper)

### Phase 2: Built-in Provider Implementations
**Rationale:** Wrap existing working code before attempting migration. Legacy providers serve as reference implementations demonstrating correct interface usage.

**Delivers:**
- `src/providers/rss.py` — RSS/Atom provider wrapping feeds.py (priority 50)
- `src/providers/github.py` — GitHub provider wrapping github.py (priority 100)
- Legacy wrapper classes maintaining backward compatibility
- `feed list` enhanced to show provider type from metadata

**Uses:** feedparser 6.0.x, httpx 0.27.x, scrapling 0.4.2

**Implements:** Provider interface, priority-based dispatch

### Phase 3: CLI Integration with Registry
**Rationale:** Once providers exist and are tested, wire CLI to use registry for all feed operations. This is where migration from old code paths happens.

**Delivers:**
- `fetch --all` uses `ProviderRegistry` to iterate providers
- `feed add` uses `ProviderRegistry.discover()` for URL detection
- `repo add` becomes alias to GitHub provider
- Backward compatibility maintained via legacy wrappers

**Avoids:** Hardcoded migration trap — old code still works until new path is verified

### Phase 4: Tag Parser Integration
**Rationale:** Provider-specific tag parsers are a differentiator, not table stakes. Hook after core refresh is working.

**Delivers:**
- `TagParser` base class and chain pattern
- Provider-specific tag parsers (language, topic, org from GitHub)
- Integration with existing tag_rules.py

### Phase Ordering Rationale

- **Interface first, implementation second** — Protocol without providers is safe; providers without Protocol invite drift
- **Wrap existing code before migrating** — Legacy providers prove the pattern works without breaking anything
- **Registry integration last** — CLI changes are risky; do after providers are tested in isolation
- **Pitfalls map to phases** — Circular imports (Phase 1 lazy imports), interface drift (Phase 1 Protocol), no isolation (Phase 1 wrapper), migration trap (Phase 2-3 incremental), entry points (Phase 1)

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Database migration strategy for adding `metadata` column — need to verify existing data schema
- **Phase 3:** Backward compatibility testing strategy — need to compare old vs new results

Phases with standard patterns (skip research-phase):
- **Phase 1:** `pluggy` PluginManager usage is well-documented (pytest standard)
- **Phase 2:** Wrapping existing feeds.py/github.py is straightforward

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All dependencies have official documentation; verified in project |
| Features | MEDIUM | Based on codebase analysis and competitor research; some differentiation choices are opinionated |
| Architecture | MEDIUM-HIGH | Plugin patterns well-established; specific registry design is inferred |
| Pitfalls | MEDIUM | Python import patterns verified; plugin isolation strategies are industry-standard |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Database schema specifics:** `feeds.metadata` JSON structure not fully specified — needs review during Phase 1 planning
- **Entry point configuration:** `pyproject.toml` entry points for plugins not yet written — needed before Phase 2
- **Legacy provider boundary:** How much code stays in `feeds.py` vs moves to `providers/rss.py` — defer to Phase 2
- **Tag parser chaining performance:** No research on scaling tag parsing across many providers — validate if tag parser count grows

## Sources

### Primary (HIGH confidence)
- [feedparser Documentation](https://feedparser.readthedocs.io/en/latest/) — RSS/Atom parsing
- [BeautifulSoup4 Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) — HTML parsing
- [Python pluggy documentation](https://pluggy.readthedocs.io/en/latest/) — Plugin framework
- [Python typing.Protocol documentation](https://docs.python.org/3/library/typing.html#typing.Protocol) — Interface definition
- [Click plugin architecture patterns](https://click.palletsprojects.com/en/8.1.x/) — CLI integration
- [GitHub REST API: Releases](https://docs.github.com/en/rest/releases/releases) — API specifications
- [Python importlib.metadata documentation](https://docs.python.org/3/library/importlib.metadata.html) — Entry points
- [Python sqlite3 Documentation](https://docs.python.org/3/library/sqlite3.html) — Database

### Secondary (MEDIUM confidence)
- [Real Python: Python entry points](https://realpython.com/python-import-module-main/) — Plugin discovery patterns
- [rich documentation](https://rich.readthedocs.io/) — Terminal display (training data)
- [Stack Overflow: Circular import patterns](https://stackoverflow.com/questions/2217476/) — Import best practices

### Tertiary (LOW confidence)
- [scrapling PyPI](https://pypi.org/project/scrapling/) — Changelog scraping (needs validation for GitHub blob URLs)

---
*Research completed: 2026-03-23*
*Ready for roadmap: yes*
