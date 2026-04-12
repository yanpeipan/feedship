"""Report generation — clustering articles and rendering Jinja2 templates."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .template import HeadingNode

from src.application.articles import ArticleListItem
from src.application.report import (
    EntityTag,
    ReportArticle,
    ReportCluster,
    ReportData,
    SignalFilter,
)
from src.llm.output_models import ClassifyTranslateItem
from src.storage import list_articles

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# v2 report helpers — topic clustering
# ---------------------------------------------------------------------------

# Template directory
DEFAULT_TEMPLATE_DIR = Path("~/.config/feedship/templates").expanduser()
DEFAULT_TEMPLATE_NAME = "default"


async def _entity_report_async(
    pre_fetched_articles: list[ArticleListItem],
    since: str,
    until: str,
    auto_summarize: bool,
    target_lang: str,
    heading_tree: HeadingNode | None = None,
) -> ReportData:
    """New entity-based report pipeline (5 layers).

    Layer 0: Signal Filter (rules)
    Layer 1: Enrich (pass-through)
    Layer 2: Entity Clustering (LLM)
    Layer 3: TLDR Generation (1 LLM call)
    Layer 4: Render (Jinja2)
    """
    import logging

    logger = logging.getLogger(__name__)

    from src.application.report.filter import SignalFilter
    from src.llm.output_models import ClassifyTranslateOutput

    try:
        # Level 0: Three-level dedup (before SignalFilter)
        from src.application.dedup import deduplicate_articles

        deduped = deduplicate_articles(pre_fetched_articles)

        # Layer 1: Signal Filter
        signal_filter = SignalFilter()
        filtered = signal_filter.filter(deduped)

        # --- Layer 2: Classify + Translate (LLM) ---
        # Candidate tags derived from template heading structure
        tag_list = "\n".join(heading_tree.titles)

        # Use BatchClassifyChain for batching + concurrency
        from src.application.report.classify import BatchClassifyChain

        chain = BatchClassifyChain(
            tag_list=tag_list,
            target_lang=target_lang,
            batch_size=50,
            max_concurrency=5,
        )
        classify_output_items = await chain.ainvoke(filtered)
        classify_output = ClassifyTranslateOutput(items=classify_output_items)

        # Convert ClassifyTranslateOutput to ReportCluster[]
        # id is 1-indexed position in news_list, map back to original article
        # Group by primary tag (tags[0]) or feed_id if no tags
        # Group by primary tag (or feed_id as fallback)
        from collections import defaultdict

        tag_groups: dict[str, list[tuple[int, ArticleListItem]]] = defaultdict(
            list
        )  # tag -> [(item_id, ArticleListItem)]
        for item in classify_output.items:
            if item.id <= len(filtered):
                art = filtered[item.id - 1]
                primary_tag = item.tags[0] if item.tags else art.feed_id or "unknown"
                tag_groups[primary_tag].append((item.id, art))

        # Also store translated title per item_id
        trans_by_id = {item.id: item.translation for item in classify_output.items}

        # Build ReportCluster for each tag group
        entity_topics = []
        from src.application.report.models import (
            ReportArticle,
            ReportCluster,
        )

        for tag, items in tag_groups.items():
            arts = [item[1] for item in items]
            # Build ReportArticle for each article
            article_enriched_list = [
                ReportArticle(
                    id=art.id or "",
                    feed_id=art.feed_id or "",
                    feed_name=getattr(art, "feed_name", "") or "",
                    title=art.title or "",
                    link=art.link or "",
                    guid=getattr(art, "guid", "") or "",
                    published_at=art.published_at or "",
                    description=art.description or "",
                    tags=[],
                    dimensions=[tag],
                    translation=trans_by_id.get(item_id, ""),
                )
                for item_id, art in items
            ]

            # Find best article by quality for headline
            best_art = max(arts, key=lambda a: a.quality_score or 0.0)
            best_idx = next(i for i, a in enumerate(arts) if a.id == best_art.id)
            item_id = items[best_idx][0]
            headline = trans_by_id.get(item_id, tag)[:30]

            entity_topics.append(
                ReportCluster(
                    name=headline,
                    summary="",
                    tags=[],
                    children=article_enriched_list,
                    articles=article_enriched_list,
                )
            )

        # Layer 4: Build clusters dict by traversing heading tree structure
        # heading_tree.children are the top-level sections (H2 headings)
        # Each heading's title maps to the matching ReportCluster from entity_topics
        # If no match, create an empty ReportCluster to preserve template structure

        def _tag_of(cluster: ReportCluster) -> str:
            return cluster.children[0].dimensions[0] if cluster.children else ""

        clusters: dict[str, list[ReportCluster]] = {}
        for node in heading_tree.children if heading_tree else []:
            matched = next(
                (c for c in entity_topics if _tag_of(c) == node.title),
                ReportCluster(name=node.title, children=[], articles=[]),
            )
            clusters.setdefault(node.title, []).append(matched)

        report_data = ReportData(
            clusters=clusters,
            date_range={"since": since, "until": until},
            target_lang=target_lang,
            heading_tree=heading_tree,
        )

        return report_data
    except Exception as e:
        logger.error(f"Entity clustering failed: {e}")
        raise


def cluster_articles_for_report(
    since: str,
    until: str,
    limit: int = 200,
    auto_summarize: bool = True,
    target_lang: str = "zh",
    heading_tree: HeadingNode | None = None,
) -> ReportData:
    """Fetch and cluster articles for an entity-based report.

    Returns:
        ReportData with clusters, date_range, target_lang, heading_tree.
    """
    articles = list_articles(
        limit=limit,
        since=since,
        until=until,
    )
    return asyncio.run(
        _entity_report_async(
            articles, since, until, auto_summarize, target_lang, heading_tree
        )
    )


__all__ = [
    "ReportArticle",
    "EntityTag",
    "ReportCluster",
    "ReportData",
    "SignalFilter",
]
