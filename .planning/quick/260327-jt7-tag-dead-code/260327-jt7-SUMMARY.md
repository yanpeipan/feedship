# Quick Task 260327-jt7: Remove Tag Dead Code Summary

## Task Overview

**Objective:** Delete all tag functionality: tag CLI commands, article tag command, src/application/tags.py, src/tags/ directory, tag storage functions and tables, tag models, tag tests.

**One-liner:** Removed all tag-related code (CLI commands, storage functions, models, providers, and tests) - approximately 2000 lines deleted.

## What Was Deleted

### Files Deleted
- `src/cli/tag.py` - tag add/list/remove/rule CLI commands
- `src/application/tags.py` - auto_tag_articles, apply_rules_to_untagged, tag_article_manual
- `src/tags/__init__.py` - tag parser chain
- `src/tags/ai_tagging.py` - TF-IDF/sentence-transformers auto-tagging
- `src/tags/tag_rules.py` - keyword/regex tag rules
- `src/tags/default_tag_parser.py` - default tag parser
- `src/tags/release_tag_parser.py` - GitHub release tag parser
- `tests/test_ai_tagging.py` - AI tagging tests

### Files Modified

**CLI:**
- `src/cli/article.py` - removed tag imports, --tag/--tags filter options, Tags column in table, article_tag command

**Providers:**
- `src/providers/base.py` - removed TagParser protocol and tag_parsers()/parse_tags() from ContentProvider
- `src/providers/rss_provider.py` - removed tag_parsers() and parse_tags() methods
- `src/providers/github_release_provider.py` - removed tag_parsers() and parse_tags() methods
- `src/providers/default_provider.py` - removed tag_parsers() and parse_tags() methods

**Storage:**
- `src/storage/sqlite.py` - removed tags and article_tags tables from init_db(), removed tag functions (add_tag, list_tags, remove_tag, get_tag_article_counts, tag_article, untag_article, get_article_tags, list_articles_with_tags, get_articles_with_tags, get_untagged_articles)
- `src/storage/__init__.py` - removed tag-related exports

**Models:**
- `src/models.py` - removed Tag and ArticleTagLink dataclasses

**Application:**
- `src/application/fetch.py` - removed articles_needing_tags collection and tag rule application
- `src/application/feed.py` - removed articles_needing_tags collection and tag rule application

**Tests:**
- `tests/test_cli.py` - removed tag command tests and article_tag test
- `tests/test_storage.py` - removed tag function tests and TestTagOperations class

## Verification

- No `from src.application.tags import` references in src/
- No `src/tags/` directory exists
- No tag storage functions in src/storage/sqlite.py

## Commits

- `dbd7dfe` feat(quick-260327-jt7): remove all tag functionality

## Decisions Made

- Removed TagParser protocol and tag_parsers()/parse_tags() interface from all providers since tag functionality is completely removed
- Kept the ContentProvider protocol structure intact (just removed tag-related methods)

## Metrics

- **Duration:** <1 min
- **Files Changed:** 20 (8 deleted, 12 modified)
- **Lines Deleted:** ~2045 lines
