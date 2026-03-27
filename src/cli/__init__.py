"""CLI package - defines cli() command group and registers subcommands."""

from __future__ import annotations

import logging
import warnings

import click

# Suppress requests version mismatch warning (urllib3 2.6.3 is functionally compatible)
warnings.filterwarnings("ignore", message="urllib3.*doesn't match a supported version")


@click.group()
@click.version_option(version="0.1.0")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """RSS reader CLI - manage feeds and read articles."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    # Initialize uvloop (graceful fallback on Windows)
    from src.application.asyncio_utils import install_uvloop
    install_uvloop()

    # Initialize database on every command
    from src.storage.sqlite import init_db
    init_db()

    # Pre-download embedding model for ChromaDB (SEM-03, D-04)
    # If this fails (network, SSL), semantic search will download on first use
    try:
        from src.storage.vector import preload_embedding_model
        preload_embedding_model()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Could not preload embedding model: %s. Semantic search will download on first use.", e)


# Import submodules to trigger @cli.command decorators
from src.cli import feed  # noqa: F401
from src.cli import article  # noqa: F401
from src.cli import tag  # noqa: F401
from src.cli import crawl  # noqa: F401


if __name__ == "__main__":
    cli()
