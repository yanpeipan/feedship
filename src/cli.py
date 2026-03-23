"""CLI interface for RSS reader using click framework.

Provides commands for feed management and article listing.
"""

from __future__ import annotations

import logging
import platform
import subprocess
import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.articles import get_article_detail, list_articles, search_articles
from src.crawl import crawl_url
from src.db import (
    add_tag,
    get_article_tags,
    get_tag_article_counts,
    init_db,
    list_tags,
    remove_tag,
    tag_article,
)
from src.tag_rules import add_rule, remove_rule, list_rules, edit_rule
from src.tag_rules import apply_rules_to_article
from src.feeds import (
    FeedNotFoundError,
    add_feed,
    list_feeds,
    refresh_feed,
    remove_feed,
)

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """RSS reader CLI - manage feeds and read articles."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    # Initialize database on every command
    init_db()


@cli.group()
@click.pass_context
def feed(ctx: click.Context) -> None:
    """Manage RSS/Atom feeds."""
    pass


@feed.command("add")
@click.argument("url")
@click.pass_context
def feed_add(ctx: click.Context, url: str) -> None:
    """Add a new feed by URL."""
    verbose = ctx.parent and ctx.parent.obj.get("verbose")
    try:
        feed_obj = add_feed(url)
        click.secho(f"Added feed: {feed_obj.name} ({feed_obj.url})", fg="green")
        if verbose:
            click.secho(f"Feed ID: {feed_obj.id}")
    except ValueError as e:
        click.secho(f"Error: {e}", err=True, fg="red")
        sys.exit(1)
    except Exception as e:
        click.secho(f"Error: Failed to add feed: {e}", err=True, fg="red")
        logger.exception("Failed to add feed")
        sys.exit(1)


@feed.command("list")
@click.pass_context
def feed_list(ctx: click.Context) -> None:
    """List all subscribed feeds."""
    verbose = ctx.parent and ctx.parent.obj.get("verbose")
    try:
        feeds = list_feeds()
        if not feeds:
            click.secho("No feeds subscribed yet. Use 'feed add <url>' to add one.")
            return

        # Print table header
        click.secho("ID  | Name | URL | Articles | Last Fetched")
        click.secho("-" * 80)

        for f in feeds:
            last_fetched = f.last_fetched or "Never"
            if verbose:
                click.secho(
                    f"{f.id}\n"
                    f"  Name: {f.name}\n"
                    f"  URL: {f.url}\n"
                    f"  Articles: {getattr(f, 'articles_count', 0)}\n"
                    f"  Last Fetched: {last_fetched}"
                )
            else:
                click.secho(
                    f"{f.id} | {f.name[:30]} | {f.url[:40]} | "
                    f"{getattr(f, 'articles_count', 0)} | {last_fetched[:10]}"
                )
    except Exception as e:
        click.secho(f"Error: Failed to list feeds: {e}", err=True, fg="red")
        logger.exception("Failed to list feeds")
        sys.exit(1)


@feed.command("remove")
@click.argument("feed_id")
@click.pass_context
def feed_remove(ctx: click.Context, feed_id: str) -> None:
    """Remove a feed by ID."""
    verbose = ctx.parent and ctx.parent.obj.get("verbose")
    try:
        removed = remove_feed(feed_id)
        if removed:
            click.secho(f"Removed feed: {feed_id}", fg="green")
        else:
            click.secho(f"Feed not found: {feed_id}", fg="yellow")
            sys.exit(1)
    except Exception as e:
        click.secho(f"Error: Failed to remove feed: {e}", err=True, fg="red")
        logger.exception("Failed to remove feed")
        sys.exit(1)


@feed.command("refresh")
@click.argument("feed_id")
@click.pass_context
def feed_refresh(ctx: click.Context, feed_id: str) -> None:
    """Refresh a single feed to fetch new articles."""
    verbose = ctx.parent and ctx.parent.obj.get("verbose")
    try:
        result = refresh_feed(feed_id)
        if "error" in result:
            click.secho(f"Error refreshing feed: {result['error']}", fg="red")
            sys.exit(1)
        new_count = result.get("new_articles", 0)
        if new_count > 0:
            click.secho(f"Fetched {new_count} new articles", fg="green")
        else:
            click.secho("No new articles available", fg="yellow")
    except FeedNotFoundError:
        click.secho(f"Feed not found: {feed_id}", fg="red")
        sys.exit(1)
    except Exception as e:
        click.secho(f"Error: Failed to refresh feed: {e}", err=True, fg="red")
        logger.exception("Failed to refresh feed")
        sys.exit(1)


@cli.group()
@click.pass_context
def article(ctx: click.Context) -> None:
    """Manage articles."""
    pass


@article.command("list")
@click.option("--limit", default=20, help="Maximum number of articles to show")
@click.option("--feed-id", default=None, help="Filter by feed ID")
@click.option("--tag", default=None, help="Filter by tag name")
@click.option("--tags", default=None, help="Filter by multiple tags (comma-separated, OR logic)")
@click.option("--verbose", is_flag=True, help="Show full article IDs (32 chars)")
@click.pass_context
def article_list(ctx: click.Context, limit: int, feed_id: Optional[str], tag: Optional[str], tags: Optional[str], verbose: bool) -> None:
    """List recent articles from all feeds or a specific feed.

    Use --tag to filter by a single tag.
    Use --tags a,b for multiple tags (OR logic - shows articles with ANY of the tags).
    Use --verbose to show full 32-char article IDs instead of truncated 8-char IDs.
    """
    verbose = verbose or (ctx.parent and ctx.parent.obj.get("verbose") if ctx.parent else False)
    try:
        from src.articles import list_articles_with_tags, get_articles_with_tags
        articles = list_articles_with_tags(limit=limit, feed_id=feed_id, tag=tag, tags=tags)
        if not articles:
            click.secho("No articles found. Add some feeds and fetch them first.")
            return

        article_ids = [a.id for a in articles]
        tags_map = get_articles_with_tags(article_ids)

        # Create rich table
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=8 if not verbose else 36)
        table.add_column("Tags", max_width=12, overflow="ellipsis")
        table.add_column("Title")
        table.add_column("Source", max_width=20)
        table.add_column("Date", max_width=10)

        for article in articles:
            title = article.title or "No title"
            pub_date = article.pub_date or "No date"
            source = article.feed_name or "Unknown"
            article_tags = tags_map.get(article.id, [])
            tags_str = ",".join(article_tags) if article_tags else "-"
            id_display = article.id if verbose else article.id[:8]

            table.add_row(id_display, tags_str, title[:50], source[:20], pub_date[:10])

        console.print(table)
    except Exception as e:
        click.secho(f"Error: Failed to list articles: {e}", err=True, fg="red")
        logger.exception("Failed to list articles")
        sys.exit(1)


@article.command("view")
@click.argument("article_id")
@click.option("--verbose", is_flag=True, help="Show full content without truncation")
@click.pass_context
def article_view(ctx: click.Context, article_id: str, verbose: bool) -> None:
    """View full article details including content.

    Shows title, source/feed, date, tags, link, and full content.
    Works for both feed articles and GitHub releases.
    Content is truncated to 2000 characters unless --verbose is specified.
    """
    try:
        article = get_article_detail(article_id)

        if not article:
            click.secho(f"Article not found: {article_id}", fg="red")
            sys.exit(1)

        console = Console()

        # Create metadata table
        meta_table = Table(show_header=False, box=None)
        meta_table.add_row("Source:", article["feed_name"] or "Unknown")
        meta_table.add_row("Date:", article["pub_date"] or "No date")

        # Tags
        tags_str = ", ".join(article["tags"]) if article["tags"] else "-"
        meta_table.add_row("Tags:", tags_str)

        # Link
        link = article["link"] or "No link"
        meta_table.add_row("Link:", link)

        # Display panel with title
        title = article["title"] or "No title"
        subtitle = f"{article['feed_name']} | {article['pub_date'] or 'No date'}"
        panel = Panel(meta_table, title=title, subtitle=subtitle)
        console.print(panel)

        # Display content
        if article["content"]:
            content = article["content"] if verbose else article["content"][:2000]
            if not verbose and len(article["content"]) > 2000:
                content += "\n\n... (truncated, use --verbose for full content)"
            console.print()
            console.print(content)
        else:
            console.print("\n[yellow]No content available[/yellow]")

    except Exception as e:
        click.secho(f"Error: Failed to view article: {e}", err=True, fg="red")
        logger.exception("Failed to view article")
        sys.exit(1)


def open_in_browser(url: str) -> None:
    """Open a URL in the default browser.

    Args:
        url: The URL to open.

    Raises:
        RuntimeError: If the platform is not supported.
    """
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", url])
    elif system == "Linux":
        subprocess.run(["xdg-open", url])
    elif system == "Windows":
        subprocess.run(["start", "", url], shell=True)
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


@article.command("open")
@click.argument("article_id")
@click.pass_context
def article_open(ctx: click.Context, article_id: str) -> None:
    """Open article URL in default browser."""
    try:
        article = get_article_detail(article_id)

        if not article:
            click.secho(f"Article not found: {article_id}", fg="red")
            sys.exit(1)

        link = article.get("link")
        if not link:
            click.secho("No link available for this article", fg="red")
            sys.exit(1)

        open_in_browser(link)
        click.secho(f"Opened {link} in browser", fg="green")

    except RuntimeError as e:
        click.secho(f"Error: {e}", err=True, fg="red")
        sys.exit(1)
    except Exception as e:
        click.secho(f"Error: Failed to open article: {e}", err=True, fg="red")
        logger.exception("Failed to open article")
        sys.exit(1)


@article.command("tag")
@click.argument("article_id", required=False)
@click.argument("tag_name", required=False)
@click.option("--rules", "apply_rules", is_flag=True, help="Apply keyword/regex rules to untagged articles")
@click.pass_context
def article_tag(ctx: click.Context, article_id: Optional[str], tag_name: Optional[str], apply_rules: bool) -> None:
    """Tag an article manually or apply rules to untagged articles.

    Manual: article tag <article-id> <tag-name>
    Rules: article tag --rules
    """
    verbose = ctx.parent and ctx.parent.obj.get("verbose") if ctx.parent else False

    if apply_rules:
        # Apply keyword/regex rules to all untagged articles
        try:
            from src.db import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id, a.title, a.description FROM articles a
                LEFT JOIN article_tags at ON a.id = at.article_id
                WHERE at.article_id IS NULL
            """)
            untagged = cursor.fetchall()
            conn.close()

            if not untagged:
                click.secho("No untagged articles found.", fg="yellow")
                return

            click.secho(f"Applying rules to {len(untagged)} untagged articles...", fg="cyan")
            applied_count = 0
            for row in untagged:
                matched = apply_rules_to_article(row["id"], row["title"], row["description"])
                if matched:
                    applied_count += 1
                    if verbose:
                        click.secho(f"  {row['title'][:40]} -> {', '.join(matched)}")

            click.secho(f"Applied rules to {applied_count} article(s)", fg="green")
        except Exception as e:
            click.secho(f"Error applying rules: {e}", err=True, fg="red")
            sys.exit(1)

    elif article_id and tag_name:
        # Manual tagging
        try:
            tagged = tag_article(article_id, tag_name)
            if tagged:
                click.secho(f"Tagged article {article_id} with '{tag_name}'", fg="green")
            else:
                click.secho(f"Failed to tag article", fg="red")
                sys.exit(1)
        except Exception as e:
            click.secho(f"Error: {e}", err=True, fg="red")
            sys.exit(1)

    else:
        click.secho("Usage: article tag <article-id> <tag-name>", fg="yellow")
        click.secho("   or: article tag --auto [--eps 0.3 --min-samples 3]")
        click.secho("   or: article tag --rules")
        sys.exit(1)


@cli.command("search")
@click.argument("query")
@click.option("--limit", default=20, help="Maximum number of results")
@click.option("--feed-id", default=None, help="Filter by feed ID")
@click.pass_context
def article_search(ctx: click.Context, query: str, limit: int, feed_id: Optional[str]) -> None:
    """Search articles by keyword using full-text search.

    Supports FTS5 query syntax:
    - Multiple words default to AND (all must match)
    - Use quotes for exact phrase: "machine learning"
    - Use OR for either: python OR ruby
    """
    verbose = ctx.parent and ctx.parent.obj.get("verbose") if ctx.parent else False
    try:
        articles = search_articles(query=query, limit=limit, feed_id=feed_id)
        if not articles:
            click.secho("No articles found matching your search.")
            return

        click.secho("Title | Source | Date")
        click.secho("-" * 80)

        for article in articles:
            title = article.title or "No title"
            pub_date = article.pub_date or "No date"

            # Show GitHub source or feed source
            if article.source_type == "github":
                source = f"{article.repo_name}@{article.release_tag}" if article.release_tag else article.repo_name
            else:
                source = article.feed_name or "Unknown"

            if verbose:
                click.secho(f"\nTitle: {title}")
                click.secho(f"Source: {source}")
                click.secho(f"Date: {pub_date}")
                if article.link:
                    click.secho(f"Link: {article.link}")
                if article.description:
                    desc_preview = article.description[:100] + "..." if len(article.description) > 100 else article.description
                    click.secho(f"Description: {desc_preview}")
            else:
                click.secho(f"{title[:50]} | {source[:25]} | {pub_date[:10]}")
    except Exception as e:
        click.secho(f"Error: Failed to search articles: {e}", err=True, fg="red")
        logger.exception("Failed to search articles")
        sys.exit(1)


@cli.command("fetch")
@click.option("--all", "fetch_all", is_flag=True, help="Fetch all feeds")
@click.pass_context
def fetch(ctx: click.Context, fetch_all: bool) -> None:
    """Fetch new articles from feeds."""
    verbose = ctx.parent and ctx.parent.obj.get("verbose") if ctx.parent else False

    if not fetch_all:
        click.secho("Use --all to fetch all feeds: feed fetch --all")
        click.secho("Or use 'feed refresh <id>' to refresh a specific feed")
        return

    try:
        feeds = list_feeds()
        if not feeds:
            click.secho("No feeds subscribed. Use 'feed add <url>' to add one.", fg="yellow")
            return

        total_new = 0
        success_count = 0
        error_count = 0
        errors: list[str] = []

        for feed_obj in feeds:
            try:
                result = refresh_feed(feed_obj.id)
                new_articles = result.get("new_articles", 0)
                total_new += new_articles
                success_count += 1
                if verbose:
                    click.secho(f"Fetched {new_articles} articles from {feed_obj.name}")
            except Exception as e:
                error_count += 1
                errors.append(f"{feed_obj.name}: {e}")
                # Per-feed error isolation: continue with next feed
                click.secho(f"Warning: Failed to fetch {feed_obj.name}: {e}", fg="yellow")

        # Summary
        if error_count == 0:
            click.secho(
                f"Fetched {total_new} articles from {success_count} feeds",
                fg="green",
            )
        else:
            click.secho(
                f"Fetched {total_new} articles from {success_count} feeds. {error_count} errors",
                fg="yellow",
            )
            if verbose and errors:
                for err in errors:
                    click.secho(f"  - {err}", fg="red")

    except Exception as e:
        click.secho(f"Error: Failed to fetch feeds: {e}", err=True, fg="red")
        logger.exception("Failed to fetch feeds")
        sys.exit(1)


@cli.command("crawl")
@click.argument("url")
@click.option("--ignore-robots", is_flag=True, help="Ignore robots.txt and crawl anyway (lazy mode disabled)")
@click.pass_context
def crawl(ctx: click.Context, url: str, ignore_robots: bool) -> None:
    """Fetch and store content from a URL as an article.

    Uses Readability algorithm to extract article content from webpages.
    Respects robots.txt by default (use --ignore-robots to override).

    Examples:

        rss-reader crawl https://example.com/article

        rss-reader crawl https://example.com --ignore-robots
    """
    verbose = ctx.parent and ctx.parent.obj.get("verbose") if ctx.parent else False
    try:
        result = crawl_url(url, ignore_robots=ignore_robots)
        if result is None:
            click.secho(f"No content extracted from {url}", fg="yellow")
            sys.exit(1)
        title = result.get('title') or 'No title'
        link = result.get('link') or url
        click.secho(f"Crawled: {title} ({link})", fg="green")
        if verbose:
            content_preview = result.get('content', '')[:200] + '...' if result.get('content') else ''
            if content_preview:
                click.secho(f"Content preview: {content_preview}")
    except Exception as e:
        click.secho(f"Error: Failed to crawl {url}: {e}", err=True, fg="red")
        logger.exception("Failed to crawl")
        sys.exit(1)


@cli.group()
@click.pass_context
def tag(ctx: click.Context) -> None:
    """Manage article tags."""
    pass


@tag.command("add")
@click.argument("name")
@click.pass_context
def tag_add(ctx: click.Context, name: str) -> None:
    """Create a new tag."""
    try:
        t = add_tag(name)
        click.secho(f"Created tag: {t.name}", fg="green")
    except Exception as e:
        click.secho(f"Error: {e}", err=True, fg="red")
        sys.exit(1)


@tag.command("list")
@click.pass_context
def tag_list(ctx: click.Context) -> None:
    """List all tags with article counts."""
    try:
        tags = list_tags()
        counts = get_tag_article_counts()
        if not tags:
            click.secho("No tags created yet. Use 'tag add <name>' to create one.")
            return
        click.secho("Tag | Articles")
        click.secho("-" * 30)
        for t in tags:
            count = counts.get(t.name, 0)
            click.secho(f"{t.name} | {count}")
    except Exception as e:
        click.secho(f"Error: {e}", err=True, fg="red")
        sys.exit(1)


@tag.command("remove")
@click.argument("tag_name")
@click.pass_context
def tag_remove(ctx: click.Context, tag_name: str) -> None:
    """Remove a tag (unlinks from all articles)."""
    try:
        removed = remove_tag(tag_name)
        if removed:
            click.secho(f"Removed tag: {tag_name}", fg="green")
        else:
            click.secho(f"Tag not found: {tag_name}", fg="yellow")
            sys.exit(1)
    except Exception as e:
        click.secho(f"Error: {e}", err=True, fg="red")
        sys.exit(1)


@tag.group()
@click.pass_context
def rule(ctx: click.Context) -> None:
    """Manage tag rules for automatic tagging."""
    pass


@rule.command("add")
@click.argument("tag_name")
@click.option("--keyword", "-k", multiple=True, help="Keyword to match (can specify multiple)")
@click.option("--regex", "-r", help="Regex pattern to match")
@click.pass_context
def tag_rule_add(ctx: click.Context, tag_name: str, keyword: tuple, regex: Optional[str]) -> None:
    """Add a rule for a tag (D-07).

    Examples:
        tag rule add AI --keyword "machine learning" --keyword "deep learning"
        tag rule add Security --regex "CVE-\\d+"
    """
    if not keyword and not regex:
        click.secho("Error: Must specify --keyword or --regex", fg="red")
        sys.exit(1)
    try:
        add_rule(tag_name, keywords=list(keyword) if keyword else None, regex=[regex] if regex else None)
        click.secho(f"Added rule(s) for tag '{tag_name}'", fg="green")
    except Exception as e:
        click.secho(f"Error: {e}", err=True, fg="red")
        sys.exit(1)


@rule.command("remove")
@click.argument("tag_name")
@click.option("--keyword", "-k", help="Keyword to remove")
@click.option("--regex", "-r", help="Regex pattern to remove")
@click.pass_context
def tag_rule_remove(ctx: click.Context, tag_name: str, keyword: Optional[str], regex: Optional[str]) -> None:
    """Remove a rule from a tag."""
    if not keyword and not regex:
        click.secho("Error: Must specify --keyword or --regex", fg="red")
        sys.exit(1)
    try:
        removed = remove_rule(tag_name, keyword=keyword, regex_pattern=regex)
        if removed:
            click.secho(f"Removed rule from '{tag_name}'", fg="green")
        else:
            click.secho(f"Rule not found for '{tag_name}'", fg="yellow")
    except Exception as e:
        click.secho(f"Error: {e}", err=True, fg="red")
        sys.exit(1)


@rule.command("list")
@click.pass_context
def tag_rule_list(ctx: click.Context) -> None:
    """List all tag rules."""
    try:
        rules = list_rules()
        tags = rules.get("tags", {})
        if not tags:
            click.secho("No tag rules defined. Use 'tag rule add' to create one.")
            return
        click.secho("Tag Rules:")
        click.secho("=" * 50)
        for tag_name, rule in tags.items():
            click.secho(f"\n{tag_name}:")
            for kw in rule.get("keywords", []):
                click.secho(f"  [keyword] {kw}")
            for pattern in rule.get("regex", []):
                click.secho(f"  [regex] {pattern}")
    except Exception as e:
        click.secho(f"Error: {e}", err=True, fg="red")
        sys.exit(1)


@rule.command("edit")
@click.argument("tag_name")
@click.option("--add-keyword", "-k", multiple=True, help="Keyword to add (can specify multiple)")
@click.option("--remove-keyword", "-K", multiple=True, help="Keyword to remove (can specify multiple)")
@click.option("--add-regex", "-r", multiple=True, help="Regex pattern to add (can specify multiple)")
@click.option("--remove-regex", "-R", multiple=True, help="Regex pattern to remove (can specify multiple)")
@click.pass_context
def tag_rule_edit(ctx: click.Context, tag_name: str, add_keyword: tuple, remove_keyword: tuple, add_regex: tuple, remove_regex: tuple) -> None:
    """Edit a tag rule by adding/removing keywords or regex patterns (D-07).

    Examples:
        tag rule edit AI --add-keyword "neural network"
        tag rule edit Security --remove-keyword "vulnerability" --add-regex "CVE-\\\\d+"
    """
    if not add_keyword and not remove_keyword and not add_regex and not remove_regex:
        click.secho("Error: Must specify at least one of --add-keyword, --remove-keyword, --add-regex, or --remove-regex", fg="red")
        sys.exit(1)

    try:
        success = edit_rule(
            tag_name,
            add_keywords=list(add_keyword) if add_keyword else None,
            remove_keywords=list(remove_keyword) if remove_keyword else None,
            add_regex=list(add_regex) if add_regex else None,
            remove_regex=list(remove_regex) if remove_regex else None
        )
        if success:
            click.secho(f"Updated rule for tag '{tag_name}'", fg="green")
        else:
            click.secho(f"Rule not found for tag '{tag_name}'", fg="yellow")
            sys.exit(1)
    except Exception as e:
        click.secho(f"Error: {e}", err=True, fg="red")
        sys.exit(1)


if __name__ == "__main__":
    cli()
