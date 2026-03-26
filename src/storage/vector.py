"""ChromaDB vector storage for semantic search.

Provides ChromaDB PersistentClient singleton and collection management
for article embeddings using SentenceTransformer.
"""

from __future__ import annotations

import chromadb
from chromadb import PersistentClient
from chromadb.config import Settings
import platformdirs
from sentence_transformers import SentenceTransformer

# Module-level singleton client
_chroma_client: PersistentClient | None = None


def _get_chroma_client() -> PersistentClient:
    """Get or create the ChromaDB PersistentClient singleton.

    Uses platformdirs to determine the storage directory:
    ~/.local/share/rss-reader/chroma/

    Returns:
        PersistentClient: The ChromaDB client instance.
    """
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    chroma_dir = platformdirs.user_data_dir(appname="rss-reader") + "/chroma"
    _chroma_client = PersistentClient(
        path=chroma_dir,
        settings=Settings(anonymized_telemetry=False),
    )
    return _chroma_client


def _get_embedding_function():
    """Get the SentenceTransformer embedding function.

    Uses 'all-MiniLM-L6-v2' model which produces 384-dimensional vectors.
    This is the same model used in src/tags/ai_tagging.py.

    Returns:
        SentenceTransformer: The embedding function instance.
    """
    return SentenceTransformer("all-MiniLM-L6-v2")


def get_chroma_collection():
    """Get or create the 'articles' ChromaDB collection.

    The collection stores article embeddings with metadata:
    - article_id: Unique article identifier
    - content: Full article content
    - title: Article title
    - url: Article URL

    Returns:
        Collection: The ChromaDB collection for articles.
    """
    client = _get_chroma_client()
    return client.get_or_create_collection(
        name="articles",
        metadata={"description": "Article embeddings for semantic search"},
    )
