# Feed CLI Reference

## CLI Structure

| Command | Module | Behavior |
|---------|--------|----------|
| `feed add <url>` | cli/feed.py | Detects provider type, adds feed |
| `feed list` | cli/feed.py | List all subscribed feeds |
| `feed remove <id>` | cli/feed.py | Remove feed by ID |
| `feed refresh <id>` | cli/feed.py | Fetch new articles for one feed |
| `fetch --all` | cli/feed.py | Fetch all feeds |
| `crawl <url>` | cli/crawl.py | Crawl arbitrary URL |
| `article list` | cli/article.py | List articles with tags |
| `article view <id>` | cli/article.py | View full article |
| `article open <id>` | cli/article.py | Open in browser |
| `article tag <id> <tag>` | cli/article.py | Manual tagging |
| `article tag --auto` | cli/article.py | AI clustering |
| `article tag --rules` | cli/article.py | Apply keyword/regex rules |
| `tag add <name>` | cli/tag.py | Create tag |
| `tag list` | cli/tag.py | List tags with counts |
| `tag remove <name>` | cli/tag.py | Remove tag |
| `tag rule add <tag>` | cli/tag.py | Add tag rule |
| `tag rule list` | cli/tag.py | List rules |
| `tag rule edit <tag>` | cli/tag.py | Edit rule |
| `tag rule remove <tag>` | cli/tag.py | Remove rule |
