"""GitHub API client for monitoring repository releases.

Provides functions for fetching release information from GitHub REST API
with optional token authentication and rate limit handling.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

from src.db import get_connection
from src.models import GitHubRepo, GitHubRelease

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Cache TTL of 1 hour for release data
CACHE_TTL = timedelta(hours=1)


def get_headers() -> dict:
    """Build request headers with optional auth.

    Returns:
        Dict with Accept header and optional Authorization Bearer token.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse owner and repo from GitHub URL.

    Supports:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo/releases
    - git@github.com:owner/repo.git

    Args:
        url: GitHub repository URL.

    Returns:
        Tuple of (owner, repo).

    Raises:
        ValueError: If URL is not a valid GitHub repo URL.
    """
    import re
    from urllib.parse import urlparse

    # SSH format
    if url.startswith("git@"):
        match = re.match(r"git@github\.com:([^/]+)/(.+?)(?:\.git)?$", url)
        if match:
            return match.group(1), match.group(2)

    # HTTPS format
    parsed = urlparse(url)
    if parsed.netloc == "github.com":
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1].replace(".git", "")

    raise ValueError(f"Invalid GitHub URL: {url}")


def check_rate_limit(response: httpx.Response) -> dict:
    """Extract rate limit info from response headers.

    Args:
        response: httpx.Response from GitHub API.

    Returns:
        Dict with remaining, reset, limit keys.
    """
    return {
        "remaining": int(response.headers.get("X-RateLimit-Remaining", 0)),
        "reset": int(response.headers.get("X-RateLimit-Reset", 0)),
        "limit": int(response.headers.get("X-RateLimit-Limit", 60))
    }


def is_rate_limited(response: httpx.Response) -> bool:
    """Check if response indicates rate limit exceeded.

    Args:
        response: httpx.Response from GitHub API.

    Returns:
        True if rate limited (403 with rate limit message).
    """
    if response.status_code == 403:
        return "rate limit" in response.text.lower()
    return False


def get_wait_time(response: httpx.Response) -> int:
    """Get seconds to wait until rate limit resets.

    Args:
        response: httpx.Response from GitHub API.

    Returns:
        Seconds until rate limit reset (0 if already passed).
    """
    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
    now = datetime.now(timezone.utc).timestamp()
    return max(0, int(reset_time - now))


def is_cache_fresh(last_fetched: Optional[str]) -> bool:
    """Check if cached data is still fresh.

    Args:
        last_fetched: ISO timestamp string of last fetch.

    Returns:
        True if cache is fresh (within CACHE_TTL).
    """
    if not last_fetched:
        return False
    last = datetime.fromisoformat(last_fetched)
    return datetime.now(timezone.utc) - last < CACHE_TTL


class RateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded."""
    pass


class GitHubAPIError(Exception):
    """Raised when GitHub API returns an error."""
    pass


def fetch_latest_release(owner: str, repo: str) -> Optional[dict]:
    """Fetch latest release for a repository.

    Args:
        owner: GitHub owner (user or organization).
        repo: Repository name.

    Returns:
        Dict with tag_name, name, body, published_at, html_url, or None if no releases.

    Raises:
        RateLimitError: If rate limit is exceeded.
        GitHubAPIError: If API returns an error.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases/latest"
    response = httpx.get(url, headers=get_headers(), timeout=10.0)

    # Check rate limit first
    rate_info = check_rate_limit(response)
    if rate_info["remaining"] < 10:
        logger.warning(f"GitHub API rate limit low: {rate_info['remaining']} remaining")

    if response.status_code == 404:
        return None  # No releases

    if is_rate_limited(response):
        wait_time = get_wait_time(response)
        raise RateLimitError(f"Rate limited. Retry after {wait_time} seconds")

    if response.status_code == 403:
        raise GitHubAPIError(f"GitHub API error: {response.text}")

    response.raise_for_status()
    return response.json()


def store_release(repo_id: str, release_data: dict) -> GitHubRelease:
    """Store a release in the database.

    Args:
        repo_id: ID of the parent GitHubRepo.
        release_data: Dict from GitHub API with tag_name, name, body, etc.

    Returns:
        Created GitHubRelease object.
    """
    import uuid

    release_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

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
        raise GitHubAPIError("Failed to store release")
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


class RepoNotFoundError(Exception):
    """Raised when a GitHub repo is not found in the database."""
    pass


def generate_repo_id() -> str:
    """Generate a unique ID for a new GitHub repo."""
    return str(uuid.uuid4())


def add_github_repo(url: str) -> GitHubRepo:
    """Add a GitHub repository to monitor.

    Parses the URL to extract owner/repo, validates by fetching from GitHub API.

    Args:
        url: GitHub repository URL.

    Returns:
        Created GitHubRepo object.

    Raises:
        ValueError: If URL is invalid or repo cannot be accessed.
    """
    owner, repo = parse_github_url(url)

    # Verify repo exists by trying to fetch releases
    try:
        release_data = fetch_latest_release(owner, repo)
    except RateLimitError as e:
        # Still add the repo, but note the rate limit issue
        logger.warning(f"Rate limit when verifying repo: {e}")
    except GitHubAPIError as e:
        raise ValueError(f"Cannot access GitHub repository: {e}") from e

    # Check if repo already exists
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM github_repos WHERE owner = ? AND repo = ?",
            (owner, repo),
        )
        existing = cursor.fetchone()
        if existing:
            raise ValueError(f"GitHub repository already added: {owner}/{repo}")
    finally:
        conn.close()

    repo_id = generate_repo_id()
    name = f"{owner}/{repo}"
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO github_repos (id, name, owner, repo, last_fetched, last_tag, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (repo_id, name, owner, repo, now, None, now),
        )
        conn.commit()
    finally:
        conn.close()

    result = GitHubRepo(
        id=repo_id,
        name=name,
        owner=owner,
        repo=repo,
        last_fetched=now,
        last_tag=None,
        created_at=now,
    )

    # If we got a release, store it
    if release_data:
        store_release(repo_id, release_data)
        # Update last_tag
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE github_repos SET last_tag = ? WHERE id = ?",
                (release_data.get("tag_name"), repo_id),
            )
            conn.commit()
        finally:
            conn.close()
        result.last_tag = release_data.get("tag_name")

    return result


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


def refresh_github_repo(repo_id: str) -> dict:
    """Refresh a GitHub repo to fetch latest release.

    Args:
        repo_id: The ID of the repo to refresh.

    Returns:
        Dict with new_release flag, release info, and any error.

    Raises:
        RepoNotFoundError: If repo does not exist.
    """
    repo = get_github_repo(repo_id)
    if not repo:
        raise RepoNotFoundError(f"GitHub repo not found: {repo_id}")

    # Check cache freshness first
    if is_cache_fresh(repo.last_fetched):
        logger.info(f"Skipping refresh for {repo.name} (cache fresh)")
        return {
            "new_release": False,
            "message": "Cache fresh, skipped API request",
            "release": None,
        }

    try:
        release_data = fetch_latest_release(repo.owner, repo.repo)
    except RateLimitError as e:
        return {
            "new_release": False,
            "error": str(e),
            "message": "Rate limit exceeded. Set GITHUB_TOKEN environment variable for higher limit (5000 req/hour)",
        }
    except GitHubAPIError as e:
        return {
            "new_release": False,
            "error": str(e),
        }

    now = datetime.now(timezone.utc).isoformat()

    if release_data is None:
        # No releases
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE github_repos SET last_fetched = ? WHERE id = ?",
                (now, repo_id),
            )
            conn.commit()
        finally:
            conn.close()
        return {
            "new_release": False,
            "message": "No releases found",
            "release": None,
        }

    # Store the release
    release = store_release(repo_id, release_data)

    # Update repo metadata
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE github_repos SET last_fetched = ?, last_tag = ? WHERE id = ?",
            (now, release_data.get("tag_name"), repo_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "new_release": True,
        "release": release,
    }