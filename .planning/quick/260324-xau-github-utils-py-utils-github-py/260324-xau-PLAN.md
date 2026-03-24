---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/utils/github.py
  - src/github_utils.py
  - src/providers/github_release_provider.py
  - src/tags/release_tag_parser.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "parse_github_url is in src/utils/github.py"
    - "src/github_utils.py no longer exists"
    - "All imports updated to src.utils.github"
  artifacts:
    - path: "src/utils/github.py"
      provides: "parse_github_url function"
      contains: "def parse_github_url"
  key_links:
    - from: "src/providers/github_release_provider.py"
      to: "src/utils/github.py"
      via: "from src.utils.github import parse_github_url"
    - from: "src/tags/release_tag_parser.py"
      to: "src/utils/github.py"
      via: "from src.utils.github import parse_github_url"
---

<objective>
Merge github_utils.py into utils/github.py and update all imports.
</objective>

<execution_context>
@/Users/y3/radar/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<tasks>

<task type="auto">
  <name>Task 1: Add parse_github_url to utils/github.py</name>
  <files>src/utils/github.py</files>
  <action>
    Add the following imports and function to src/utils/github.py after the existing _get_github_client function:

```python
import re
from urllib.parse import urlparse


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
```
  </action>
  <verify>python -c "from src.utils.github import parse_github_url; print(parse_github_url('https://github.com/owner/repo'))"</verify>
  <done>parse_github_url is available from src.utils.github</done>
</task>

<task type="auto">
  <name>Task 2: Update imports in consumer files</name>
  <files>src/providers/github_release_provider.py, src/tags/release_tag_parser.py</files>
  <action>
    Update imports in both files:
    - src/providers/github_release_provider.py: Change `from src.github_utils import parse_github_url` to `from src.utils.github import parse_github_url`
    - src/tags/release_tag_parser.py: Change `from src.github_utils import parse_github_url` to `from src.utils.github import parse_github_url`
  </action>
  <verify>python -c "from src.providers.github_release_provider import GitHubReleaseProvider; from src.tags.release_tag_parser import ReleaseTagParser; print('Imports OK')"</verify>
  <done>All imports updated to src.utils.github</done>
</task>

<task type="auto">
  <name>Task 3: Delete github_utils.py</name>
  <files>src/github_utils.py</files>
  <action>
    Delete src/github_utils.py (function is now in utils/github.py)
  </action>
  <verify>test ! -f src/github_utils.py && echo "Deleted successfully"</verify>
  <done>github_utils.py removed from codebase</done>
</task>

</tasks>

<verification>
python -c "
from src.utils.github import parse_github_url, _get_github_client
print('parse_github_url:', parse_github_url('https://github.com/owner/repo'))
print('All imports work correctly')
"
</verification>

<success_criteria>
- parse_github_url is in src/utils/github.py
- src/github_utils.py no longer exists
- All imports updated to src.utils.github
- No import errors in the codebase
</success_criteria>

<output>
After completion, create `.planning/quick/260324-xau-github-utils-py-utils-github-py/260324-xau-SUMMARY.md`
</output>
