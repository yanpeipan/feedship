"""GitHub utilities."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

from github import Github

# Module-level PyGithub client
_github_client: Github | None = None


def _get_github_client() -> Github:
    """Get or create module-level Github client."""
    global _github_client
    if _github_client is None:
        _github_client = Github(os.environ.get("GITHUB_TOKEN"))
    return _github_client


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
