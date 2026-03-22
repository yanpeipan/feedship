# Feature Research: GitHub Monitoring (v1.1)

**Domain:** CLI tool for monitoring GitHub repositories (releases and changelogs)
**Researched:** 2026-03-23
**Confidence:** MEDIUM (based on GitHub API documentation and existing tool patterns)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Add GitHub repo URL | Users want to add repos they care about | LOW | Parse owner/repo from GitHub URL formats |
| Fetch latest release via GitHub API | Primary use case for repo monitoring | LOW | `GET /repos/{owner}/{repo}/releases/latest` |
| Display release version + notes | Core information users want | LOW | `tag_name`, `body` (markdown) from API |
| Periodic refresh with last-known state | Detect new releases since last check | MEDIUM | Store last seen version/tag, compare on refresh |
| Changelog file scraping | Many repos document changes in CHANGELOG.md | MEDIUM | No GitHub API for changelogs - must scrape raw content |
| Unified article-like display | Consistent UX with existing feed articles | LOW | Reuse existing display patterns |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Release-only vs full repo monitoring | Filter signal from noise (releases vs commits) | MEDIUM | Distinguishes "published a release" vs "pushed 50 commits" |
| Changelog diff detection | See WHAT changed in new version beyond release notes | HIGH | Requires parsing changelog format, diffing sections |
| Adaptive parsing for varied changelog formats | Handle CHANGELOG.md, HISTORY.md, Keep a Changelog, auto-generated | HIGH | Scrapling can help but format detection is complex |
| GitHub token auth for higher rate limits | Avoid 60 req/hour cap (unauthenticated) | LOW | Use `GITHUB_TOKEN` env var, increases to 5000 req/hour |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Monitor all repo commits | Want complete activity stream | Too noisy, GitHub API rate limits hit immediately | Releases only, or explicit "watch commits" opt-in |
| Real-time webhook delivery | Want instant notifications | Requires server/public URL, defeats "local CLI" purpose | Periodic polling is sufficient for personal use |
| Native GitHub notifications integration | Want to see in GitHub's UI | Outside scope, adds OAuth complexity | Keep as local-only tool |
| Auto-discovery of changelog location | "Just find the changelog" | Many repos use different paths/names | User specifies explicit path or accept common defaults |

## Feature Dependencies

```
[Add Repo URL]
    └──requires──> [Parse owner/repo from URL]
                       └──requires──> [GitHub API: Fetch Release]
                                          └──requires──> [Store Release State]
                       └──requires──> [Changelog: Scrape File]
                                          └──requires──> [Parse Changelog Format]

[Display Unified Output] ──enhances──> [Article Display]
[Refresh All] ──enhances──> [Per-Release Refresh]

[GitHub Token Auth] ──conflicts──> [Unauthenticated Rate Limits]
```

### Dependency Notes

- **Add Repo URL requires Parse owner/repo:** GitHub URLs have multiple formats (`github.com/owner/repo`, `.git`, releases page)
- **GitHub API requires token for scale:** 60 req/hour unauthenticated limits usability to ~5-10 repos
- **Changelog scraping requires format detection:** Different projects use different conventions

## MVP Definition

### Launch With (v1.1)

Minimum viable product - what's needed to validate the concept.

- [ ] **Add GitHub repo by URL** - Parse `github.com/{owner}/{repo}` format, store repo reference
- [ ] **GitHub API release fetch** - `tag_name`, `name`, `body` (markdown), `published_at`, `html_url`
- [ ] **Display releases like articles** - Unified format reusing existing display patterns
- [ ] **Refresh to detect new releases** - Compare stored version vs API, surface new ones
- [ ] **Basic changelog scraping** - Fetch `CHANGELOG.md` from default branch, display with release

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] **GitHub token auth** - Set `GITHUB_TOKEN` env var, increase rate limit from 60 to 5000 req/hour
- [ ] **Changelog diff per release** - Parse and show what changed between version N and N-1
- [ ] **Configurable changelog path** - Support `HISTORY.md`, `CHANGELOG.rst`, user-specified paths
- [ ] **Multiple changelog format detection** - Handle Keep a Changelog, conventional commits style

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Release asset downloads** - Provide download links for `.whl`, `.tar.gz` binaries
- [ ] **Watch specific tags** - Not just "latest", monitor particular major/minor versions
- [ ] **Commit activity summary** - Optional: fetch commit history between releases
- [ ] **Notification integration** - Native OS notifications when new release detected

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Add repo by URL | HIGH | LOW | P1 |
| GitHub API release fetch | HIGH | LOW | P1 |
| Display releases | HIGH | LOW | P1 |
| Refresh detection | HIGH | MEDIUM | P1 |
| Changelog scraping (basic) | MEDIUM | MEDIUM | P2 |
| GitHub token auth | MEDIUM | LOW | P2 |
| Changelog diff | MEDIUM | HIGH | P3 |
| Configurable changelog path | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Existing System Integration Points

Based on reading the existing codebase:

| Existing Component | How GitHub Monitoring Extends It |
|--------------------|----------------------------------|
| `src/models.py` Feed/Article | Create `GitHubRepo` model with owner/repo, last_version; reuse Article display |
| `src/cli.py` feed commands | Add `repo` command group: `repo add`, `repo list`, `repo refresh` |
| `src/db.py` | Add tables for `repos` and `releases`, new columns for version tracking |
| `src/feeds.py` refresh logic | Reuse conditional fetch pattern (ETag/Last-Modified) for GitHub API with `If-None-Match` |
| `src/articles.py` list/search | Display releases alongside articles, unified format |

**Key existing patterns to reuse:**
- Feed storage with `etag`/`last_modified` for conditional fetching
- Article storage with `guid` for dedup (use `tag_name` as guid for releases)
- CLI display format for list/verbose output
- Error isolation per-repo during batch refresh

## Technical Considerations

### GitHub API Behavior

**Endpoints:**
- Latest release: `GET https://api.github.com/repos/{owner}/{repo}/releases/latest`
- All releases: `GET https://api.github.com/repos/{owner}/{repo}/releases?per_page=30`
- Release by tag: `GET https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}`

**Response fields used:**
- `tag_name`: Version string (e.g., "v1.2.3", "1.2.3")
- `name`: Release title (often same as tag, can be empty)
- `body`: Markdown release notes
- `published_at`: ISO timestamp
- `html_url`: Link to release page
- `assets`: Download links (for future use)

**Rate limits:**
- Unauthenticated: 60 requests/hour per IP
- Authenticated (token): 5,000 requests/hour
- Implement `GITHUB_TOKEN` environment variable support

**Conditional requests:**
- Use `Accept: application/vnd.github+json` header
- Respect `ETag` and `Last-Modified` headers
- Send `If-None-Match` or `If-Modified-Since` for efficient polling

### Changelog Scraping

**Common file locations (in priority order):**
1. `CHANGELOG.md` (most common)
2. `CHANGELOG` (without extension)
3. `HISTORY.md`
4. `CHANGELOG.rst`
5. `docs/changelog.md`

**Raw file URLs:**
- `https://raw.githubusercontent.com/{owner}/{repo}/main/CHANGELOG.md`
- `https://raw.githubusercontent.com/{owner}/{repo}/master/CHANGELOG.md`

**Format variations:**
- Keep a Changelog (semantic headings: Added, Changed, Deprecated, etc.)
- Auto-generated from conventional commits (git-cliff style)
- Custom per-project formats (harder to parse)

### Scrapling Integration

The project plan mentions using Scrapling for changelog files. This is appropriate for:
- Pages with JavaScript rendering
- Adaptive parsing when HTML structure varies
- Fallback when simple requests fail

However, for static changelog files, `httpx` with raw GitHub content is sufficient and faster.

## Sources

- [GitHub REST API - Releases](https://docs.github.com/en/rest/repos/releases) (HIGH confidence)
- [GitHub API Rate Limiting](https://docs.github.com/en/rest/rate-limit) (HIGH confidence)
- [Keep a Changelog standard](https://keepachangelog.com/en/1.0.0/) (HIGH confidence)
- [Scrapling GitHub repo](https://github.com/D4Vinci/Scrapling) (MEDIUM confidence - 31k stars, active)
- Existing codebase: `src/models.py`, `src/cli.py`, `src/feeds.py`

---

*Feature research for: GitHub monitoring v1.1*
*Researched: 2026-03-23*
