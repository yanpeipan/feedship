"""Tag parser registry and dynamic loading for the plugin architecture.

Discovers and loads all *_tag*.py modules from src/tags/ directory,
providing chain_tag_parsers() function that runs all parsers and returns
union with duplicates removed.
"""
from __future__ import annotations

import glob
import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Set, Tuple

if TYPE_CHECKING:
    from src.providers.base import Article, TagParser

logger = logging.getLogger(__name__)

# Discovered tag parsers, populated at import time
TAG_PARSERS: List[Tuple[str, TagParser]] = []


def load_tag_parsers() -> None:
    """Load all tag parsers from src/tags/ directory.

    Discovers *_tag*.py files, imports each module, and collects
    instances that have TAG_PARSER_INSTANCE attribute.

    Excludes __init__.py from loading.
    """
    tags_dir = Path(__file__).parent

    # Find all tag parser modules (exclude __init__)
    tag_files = sorted(tags_dir.glob("*_tag*.py"))
    logger.debug("Found tag parser files: %s", [f.stem for f in tag_files])

    for filepath in tag_files:
        module_name = filepath.stem
        if module_name == "__init__":
            continue

        full_module = f"src.tags.{module_name}"
        try:
            mod = importlib.import_module(full_module)
            # Look for TAG_PARSER_INSTANCE attribute
            if hasattr(mod, "TAG_PARSER_INSTANCE"):
                parser = mod.TAG_PARSER_INSTANCE
                # Verify it has parse_tags method (TagParser protocol)
                if callable(getattr(parser, "parse_tags", None)):
                    TAG_PARSERS.append((module_name, parser))
                    logger.debug("Registered tag parser: %s", module_name)
                else:
                    logger.warning("TAG_PARSER_INSTANCE in %s does not implement TagParser (no parse_tags method)", full_module)
            logger.debug("Loaded tag parser module: %s", full_module)
        except Exception:
            logger.exception("Failed to load tag parser %s", full_module)

    logger.info("Loaded %d tag parsers", len(TAG_PARSERS))


def get_tag_parsers() -> List[TagParser]:
    """Return all loaded tag parser instances.

    Returns:
        List of TagParser instances from TAG_PARSERS.
    """
    _ensure_loaded()
    return [parser for _, parser in TAG_PARSERS]


def chain_tag_parsers(article: Article) -> List[str]:
    """Run all tag parsers and return union with duplicates removed.

    Args:
        article: Article dict with title, description, etc.

    Returns:
        Combined list of tag names from all parsers, deduplicated.
    """
    _ensure_loaded()
    all_tags: List[str] = []
    seen: Set[str] = set()

    for name, parser in TAG_PARSERS:
        try:
            tags = parser.parse_tags(article)
            for tag in tags:
                if tag not in seen:
                    seen.add(tag)
                    all_tags.append(tag)
        except Exception:
            logger.exception("Tag parser %s failed", name)

    return all_tags


# Note: Loading is deferred to first call of chain_tag_parsers() to avoid
# circular import issues when providers import from src.tags at module load time.
_LOADED = False


def _ensure_loaded() -> None:
    """Ensure tag parsers are loaded (idempotent, called on first use)."""
    global _LOADED
    if not _LOADED:
        load_tag_parsers()
        _LOADED = True
