"""GitHub operations module.

Provides database operations and changelog functions for GitHub integration.
Uses httpx/raw.githubusercontent.com for changelog fetching (per D-03 decision).
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Optional

import httpx

from src.db import get_connection
from src.models import GitHubRepo, GitHubRelease
from src.config import get_timezone

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


class RepoNotFoundError(Exception):
    """Raised when a GitHub repo is not found in the database."""
    pass


def generate_repo_id() -> str:
    """Generate a unique ID for a new GitHub repo."""
    return str(uuid.uuid4())


def store_release(repo_id: str, release_data: dict) -> GitHubRelease:
    """Store a release in the database.

    Args:
        repo_id: ID of the parent GitHubRepo.
        release_data: Dict from GitHub API with tag_name, name, body, etc.

    Returns:
        Created GitHubRelease object.
    """
    release_id = str(uuid.uuid4())
    now = datetime.now(get_timezone()).isoformat()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO github_releases (id, repo_id, tag_name, name, body, html_url, published_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                release_id,
                repo_id,
                release_data.get("tag_name"),
                release_data.get("name"),
                release_data.get("body"),
                release_data.get("html_url"),
                release_data.get("published_at"),
                now,
            ),
        )
        conn.commit()

        # Fetch the stored release (handles INSERT OR IGNORE case)
        cursor.execute(
            "SELECT * FROM github_releases WHERE repo_id = ? AND tag_name = ?",
            (repo_id, release_data.get("tag_name")),
        )
        row = cursor.fetchone()
        if row:
            return GitHubRelease(
                id=row["id"],
                repo_id=row["repo_id"],
                tag_name=row["tag_name"],
                name=row["name"],
                body=row["body"],
                html_url=row["html_url"],
                published_at=row["published_at"],
                created_at=row["created_at"],
            )
        raise RuntimeError("Failed to store release")
    finally:
        conn.close()


def get_repo_releases(repo_id: str) -> list[GitHubRelease]:
    """Get all releases for a repository.

    Args:
        repo_id: ID of the GitHubRepo.

    Returns:
        List of GitHubRelease objects ordered by published_at descending.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM github_releases WHERE repo_id = ? ORDER BY published_at DESC",
            (repo_id,),
        )
        rows = cursor.fetchall()
        return [
            GitHubRelease(
                id=row["id"],
                repo_id=row["repo_id"],
                tag_name=row["tag_name"],
                name=row["name"],
                body=row["body"],
                html_url=row["html_url"],
                published_at=row["published_at"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
    finally:
        conn.close()


def get_or_create_github_repo(owner: str, repo: str) -> GitHubRepo:
    """Get existing GitHub repo or create new entry if not exists.

    Args:
        owner: GitHub owner (user or org)
        repo: Repository name

    Returns:
        GitHubRepo object (existing or newly created)
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM github_repos WHERE owner = ? AND repo = ?",
            (owner, repo),
        )
        row = cursor.fetchone()
        if row:
            return GitHubRepo(
                id=row["id"],
                name=row["name"],
                owner=row["owner"],
                repo=row["repo"],
                last_fetched=row["last_fetched"],
                last_tag=row["last_tag"],
                created_at=row["created_at"],
            )
    finally:
        conn.close()

    # Create new entry
    repo_id = generate_repo_id()
    name = f"{owner}/{repo}"
    now = datetime.now(get_timezone()).isoformat()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO github_repos (id, name, owner, repo, last_fetched, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (repo_id, name, owner, repo, now, now),
        )
        conn.commit()
    finally:
        conn.close()

    return GitHubRepo(
        id=repo_id,
        name=name,
        owner=owner,
        repo=repo,
        last_fetched=now,
        last_tag=None,
        created_at=now,
    )


def list_github_repos() -> list[GitHubRepo]:
    """List all monitored GitHub repositories.

    Returns:
        List of GitHubRepo objects.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM github_repos ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        return [
            GitHubRepo(
                id=row["id"],
                name=row["name"],
                owner=row["owner"],
                repo=row["repo"],
                last_fetched=row["last_fetched"],
                last_tag=row["last_tag"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
    finally:
        conn.close()


def get_github_repo(repo_id: str) -> Optional[GitHubRepo]:
    """Get a single GitHub repo by ID.

    Args:
        repo_id: The ID of the repo.

    Returns:
        GitHubRepo object or None if not found.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM github_repos WHERE id = ?", (repo_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return GitHubRepo(
            id=row["id"],
            name=row["name"],
            owner=row["owner"],
            repo=row["repo"],
            last_fetched=row["last_fetched"],
            last_tag=row["last_tag"],
            created_at=row["created_at"],
        )
    finally:
        conn.close()


def get_github_repo_by_owner_repo(owner: str, repo: str) -> Optional[GitHubRepo]:
    """Get a GitHub repo by owner and repo name.

    Args:
        owner: The GitHub owner (user or org)
        repo: The repository name

    Returns:
        GitHubRepo object or None if not found.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM github_repos WHERE owner = ? AND repo = ?", (owner, repo))
        row = cursor.fetchone()
        if not row:
            return None
        return GitHubRepo(
            id=row["id"],
            name=row["name"],
            owner=row["owner"],
            repo=row["repo"],
            last_fetched=row["last_fetched"],
            last_tag=row["last_tag"],
            created_at=row["created_at"],
        )
    finally:
        conn.close()


def remove_github_repo(repo_id: str) -> bool:
    """Remove a GitHub repo and its releases.

    Args:
        repo_id: The ID of the repo to remove.

    Returns:
        True if deleted, False if not found.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM github_repos WHERE id = ?", (repo_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


# Common changelog filenames to try, in order of priority
CHANGELOG_FILENAMES = [
    "CHANGELOG.md",
    "CHANGELOG",
    "HISTORY.md",
    "CHANGES.md",
    "CHANGELOG.rst",
]

# Common branch names to try
GITHUB_BRANCHES = ["main", "master"]


def detect_changelog_file(owner: str, repo: str) -> Optional[tuple[str, str]]:
    """Detect which changelog file exists in a repository.

    Tries common changelog filenames in order of priority, first match wins.
    Tries main branch first, then master.

    Args:
        owner: GitHub owner (user or organization).
        repo: Repository name.

    Returns:
        Tuple of (filename, branch) if found, None if no changelog detected.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    for branch in GITHUB_BRANCHES:
        for filename in CHANGELOG_FILENAMES:
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
            try:
                response = httpx.head(url, headers=headers, timeout=10.0, follow_redirects=True)
                if response.status_code == 200:
                    return (filename, branch)
            except (httpx.RequestError, OSError):
                continue
    return None


def fetch_changelog_content(owner: str, repo: str, filename: str, branch: str) -> Optional[str]:
    """Fetch changelog content from raw.githubusercontent.com.

    Args:
        owner: GitHub owner (user or organization).
        repo: Repository name.
        filename: Changelog filename (e.g., "CHANGELOG.md").
        branch: Branch name (e.g., "main").

    Returns:
        Raw markdown content as string, or None if fetch fails.
    """
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
    headers = {
        "Accept": "text/plain",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        response = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        if response.status_code == 200:
            return response.text
    except (httpx.RequestError, OSError):
        pass
    return None


def store_changelog_as_article(repo_id: str, repo_name: str, content: str, filename: str, source_url: str) -> str:
    """Store changelog content as an article.

    Creates a new article or updates existing article with same guid.
    The article's guid is prefixed with "changelog:" to distinguish from feed articles.

    Args:
        repo_id: ID of the parent GitHubRepo.
        repo_name: Display name of the repo (e.g., "owner/repo").
        content: Raw changelog markdown content.
        filename: Original filename (e.g., "CHANGELOG.md").
        source_url: URL to the raw changelog file.

    Returns:
        ID of the created or updated article.
    """
    # Create a unique guid for this changelog
    guid = f"changelog:{repo_name}:{filename}"
    title = f"{repo_name} / {filename}"

    # Use unified store_article function
    from src.db import store_article
    return store_article(
        guid=guid,
        title=title,
        content=content,
        link=source_url,
        repo_id=repo_id,
        feed_id=None,
    )


def get_repo_changelog(repo_id: str) -> Optional[dict]:
    """Get stored changelog article for a repository.

    Args:
        repo_id: ID of the GitHubRepo.

    Returns:
        Dict with article info if changelog exists, None otherwise.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, link, content, created_at
            FROM articles
            WHERE repo_id = ? AND guid LIKE 'changelog:%'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (repo_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "title": row["title"],
                "link": row["link"],
                "content": row["content"],
                "created_at": row["created_at"],
            }
        return None
    finally:
        conn.close()


def refresh_changelog(repo_id: str) -> dict:
    """Refresh changelog for a GitHub repo: detect, fetch, and store.

    Args:
        repo_id: ID of the GitHub repo to refresh changelog for.

    Returns:
        Dict with changelog_found flag, article_id, filename, and any error.
    """
    repo = get_github_repo(repo_id)
    if not repo:
        raise RepoNotFoundError(f"GitHub repo not found: {repo_id}")

    # Detect changelog file
    changelog_info = detect_changelog_file(repo.owner, repo.repo)
    if not changelog_info:
        return {
            "changelog_found": False,
            "message": f"No changelog file detected (tried: {', '.join(CHANGELOG_FILENAMES)})",
            "article_id": None,
        }

    filename, branch = changelog_info

    # Fetch content
    content = fetch_changelog_content(repo.owner, repo.repo, filename, branch)
    if not content:
        return {
            "changelog_found": True,
            "filename": filename,
            "error": "Failed to fetch changelog content",
            "article_id": None,
        }

    # Build source URL
    source_url = f"https://raw.githubusercontent.com/{repo.owner}/{repo.repo}/{branch}/{filename}"

    # Store as article
    article_id = store_changelog_as_article(repo_id, repo.name, content, filename, source_url)

    return {
        "changelog_found": True,
        "filename": filename,
        "branch": branch,
        "article_id": article_id,
        "message": f"Changelog ({filename}) updated",
    }
