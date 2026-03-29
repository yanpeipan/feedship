# Automatic Discovery Feed

## CLI Commands

- `discover <url> --discover-depth [n]` - Discover feeds from a website URL without subscribing
- `feed add <url> --discover [on/off] --automatic [on/off] --discover-depth [n]` - Add a feed with optional auto-discovery

## Architecture

**核心原则**: `discovery` 模块作为"发现层"，通过 `providers` 进行内容获取和验证，职责分离：

## 核心流程

```
discover_feeds(url, max_depth, discover) -> DiscoveredResult
    │
    └─► deep_crawl(url, max_depth, discover) -> DiscoveredResult
            │
            ├─► HTTP GET url → response
            │
            ├─► providers.discover(url, response, depth, discover) → List[DiscoveredFeed]
            │       │
            │       ├─► providers.match(url, response) → List[Provider]
            │       └─► 对每个 matched provider：
            │               │
            │               ├─► parse_feed(url, response) ──► 验证 URL
            │               └─► if discover: discover(url, response, depth) ──► 发现 feeds
            │
            ├─► webpage_provider.extract_links(html, url) → List[str]（BFS 链接）
            │
            ├─► webpage_provider.compute_selectors(html, url) → dict（仅 max_depth=1）
            │
            └─► 返回 DiscoveredResult(feeds, selectors)
```

### 关键模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| `discover_feeds()` | `discovery/__init__.py` | 入口，协调 deep_crawl |
| `deep_crawl()` | `discovery/deep_crawl.py` | BFS 爬取，Provider 调用 |
| `providers.discover()` | `providers/__init__.py` | Provider 注册表，循环调用 |
| `Provider.match()` | `providers/base.py` | Provider 匹配判断 |
| `Provider.parse_feed()` | `providers/base.py` | 验证 URL 是否为 feed |
| `Provider.discover()` | `providers/base.py` | 从页面发现 feed URLs |
| `RSSProvider` | `providers/rss_provider.py` | RSS/Atom feed 获取和解析 |
| `GitHubReleaseProvider` | `providers/github_release_provider.py` | GitHub releases 获取 |
| `WebpageProvider` | `providers/webpage_provider.py` | 网页内容获取，link 提取，selectors 计算 |

## 函数签名

### discover_feeds(url, max_depth, discover) -> DiscoveredResult

```python
async def discover_feeds(
    url: str,
    max_depth: int = 1,
    discover: bool = True,
) -> DiscoveredResult:
    """Discover RSS/Atom/RDF feeds from a website URL.

    Args:
        url: Website URL to discover feeds from.
        max_depth: Maximum crawl depth (1 = current page only, 2+ = BFS crawl).
        discover: Whether to run provider discovery (default: True).

    Returns:
        DiscoveredResult containing list of DiscoveredFeed objects found.
    """
```

### deep_crawl(url, max_depth, discover) -> DiscoveredResult

```python
async def deep_crawl(
    url: str,
    max_depth: int = 1,
    discover: bool = True,
) -> DiscoveredResult:
    """Discover feeds using BFS crawling up to max_depth.

    Args:
        url: Starting URL for crawling.
        max_depth: Maximum crawl depth (1 = current page only, 2+ = BFS crawl).
        discover: Whether to run provider discovery (default: True).

    Returns:
        DiscoveredResult with feeds and selectors (selectors only for max_depth=1).
    """
```

## Provider 接口

### match() - Provider 匹配

判断 Provider 是否匹配该 URL：

```python
def match(url: str, response: Response = None) -> bool:
    """判断 Provider 是否匹配该 URL。"""
    raise NotImplementedError
```

### parse_feed() - 验证 URL

验证 URL 是否为 feed，返回 DiscoveredFeed：

```python
def parse_feed(url: str, response: Response = None) -> Optional[DiscoveredFeed]:
    """验证 URL 是否为 feed，返回 DiscoveredFeed 或 None。"""
    raise NotImplementedError
```

### discover() - 发现更多 feeds

从页面发现更多 feed URLs。`depth` 参数由调用方传入，Provider 内部自行决定是否发 HTTP 请求：

```python
def discover(url: str, response: Response = None, depth: int = 1) -> List[DiscoveredFeed]:
    """发现更多 feed URLs。

    Args:
        url: 当前页面 URL
        response: 预获取的 HTTP response（可能为 None）
        depth: 当前爬取深度
            - depth == 1: 初始 URL，Provider 可以发 HTTP 请求试探
            - depth > 1: BFS 深层，Provider 可以只用 response 分析

    Returns:
        发现的 feed 列表（未验证，由调用方统一验证）
    """
    raise NotImplementedError
```

#### RSSProvider.discover() 实现逻辑

```
1. 检查 response Content-Type
   │
   ├─► 是 feed 类型（如 application/rss+xml）
   │       └─► 调用 parse_feed() 返回 DiscoveredFeed
   │
   └─► 是 HTML 或其他
           ├─► 解析 <link rel="alternate"> 标签发现 feed URLs
           ├─► 解析 well-known path 模式（如 /feed, /rss, /atom）
           └─► 并行试探相对路径
                   例：当前 URL https://example.com/news
                   试探：/news/feed, /news/rss, /feed, /rss
                   试探后直接加入列表，最后统一验证
```

#### 其他 Provider.discover() 实现

- **GitHubReleaseProvider.discover()**: 返回空列表（不需要发现更多）
- **WebpageProvider.discover()**: 返回空列表（兜底 provider）

#### WebpageProvider 额外职责

WebpageProvider 除了 discover() 之外，还负责 BFS 链接提取和 selectors 计算：

```python
class WebpageProvider:
    def extract_links(html: str, url: str) -> List[str]:
        """从 HTML 中提取所有内部链接，用于 BFS 继续爬取。

        - 提取所有 <a href> 链接
        - 只保留同 host 的内部链接
        - 去重后返回

        Args:
            html: 页面 HTML
            url: 当前页面 URL

        Returns:
            内部链接列表（已去重）
        """
        ...

    def compute_selectors(html: str, url: str) -> LinkSelector:
        """计算 link path prefix selectors，用于 UI 显示（仅 max_depth=1 时使用）。

        - 从 HTML 提取所有 <a href>
        - 按路径前缀聚合
        - 返回 LinkSelector(path, link, text, count)

        Args:
            html: 页面 HTML
            url: 当前页面 URL

        Returns:
            LinkSelector - 包含 path, link, text, count
        """
        ...
```

## Provider Discovery Flow

`providers.discover(url, response, depth)`:

```
1. 遍历所有已加载的 Provider（按 priority 降序）
2. 调用 provider.match(url, response) 判断是否匹配
3. 对匹配的 Provider：
   a. 调用 provider.parse_feed(url, response) ─► 验证 URL 本身
   b. 调用 provider.discover(url, response, depth) ─► 发现更多 feeds
4. 合并所有返回的 DiscoveredFeed（未验证）
5. 统一验证所有 feeds
6. 去重（按 url 去重）
```

## BFS Deep Crawl

### deep_crawl(url, max_depth, discover) -> DiscoveredResult

**参数：**
- `url: str` - 起始 URL
- `max_depth: int` - 最大爬取深度（1 = 单页，>1 = BFS）
- `discover: bool` - 是否调用 providers.discover()（默认 True）

**返回值：**
- `DiscoveredResult` - 包含 `feeds: List[DiscoveredFeed]` 和 `selectors: dict`
- selectors 每次迭代都计算并累积合并

### max_depth = 1（单页）

```
1. HTTP GET url → response
2. providers.match(url, response) → matched providers
3. 对每个 matched provider：
   a. parse_feed(url, response) → 验证 URL 本身
   b. discover(url, response, depth=1) → 发现更多 feeds
4. 合并 feeds 并验证
5. webpage_provider.compute_selectors(html, url) → LinkSelector
6. 返回 DiscoveredResult(feeds, selectors=LinkSelector)
```

### max_depth > 1（BFS 爬取）

```
1. 起始 URL 入队，depth=1
2. while queue:
   a. pop url, depth
   b. HTTP GET url → response
   c. providers.match(url, response) → matched providers
   d. 对每个 matched provider：
      - parse_feed(url, response) → 验证 URL
      - discover(url, response, depth) → 发现更多 feeds
   e. 合并到 all_feeds（去重）
   f. webpage_provider.extract_links(html, url) → links
   g. 如果 depth < max_depth：links 入队，depth+1
3. 返回 DiscoveredResult(feeds=all_feeds, selectors={})
```

### BFS 行为

- **visited-set**: 避免重复访问（normalize_url_for_visit 标准化后比较）
- **rate limiting**: 2 秒/host
- **depth 递增**: 每深入一层 depth + 1
- **selectors**: 仅 max_depth=1 时计算并返回，BFS 时不计算
- **BFS 终止**: depth == max_depth 时只发现 feeds，不提取链接入队

### 职责分离

| 操作 | 实现位置 |
|------|----------|
| 发现 feeds | `providers.discover()` |
| 验证 feeds | `deep_crawl` 内部统一验证 |
| 提取 BFS 链接 | `webpage_provider.extract_links()` |
| 计算 selectors | `webpage_provider.compute_selectors()`（仅 max_depth=1） |

## URL Resolution Rules

- Relative URLs resolved via `urllib.parse.urljoin()`
- `<base href>` in `<head>` overrides base URL
- Fragment identifiers (#...) stripped for visited-set

## Supported Feed Types

- RSS 2.0: `application/rss+xml`
- Atom 1.0: `application/atom+xml`
- RDF: `application/rdf+xml`
- Also accepted: `application/xml`, `text/xml`

## Rate Limiting

- 2 second delay between requests to same host
- Implemented via per-host request timestamp tracking
- Applies only to deep crawl (depth > 1)

## robots.txt Compliance

- Uses `robotexclusionrulesparser` library
- Only enforced when depth > 1 (depth=1 is like normal browser)
- If no robots.txt exists, crawling is allowed
- Uses `User-Agent: *` for robots.txt checks

## DiscoveredFeed Model

| Field | Type | Description |
|-------|------|-------------|
| `url` | `str` | Absolute URL of the discovered feed |
| `title` | `Optional[str]` | Feed title (if available from autodiscovery link, else `None`) |
| `feed_type` | `str` | Feed type: `'rss'`, `'atom'`, or `'rdf'` |
| `source` | `str` | Discovery source (see table below) |
| `page_url` | `str` | Original page URL where this feed was discovered |
| `valid` | `bool` | Whether feed has been validated (`True`) or is unverified (`False`) |

### Validation Rules

- 由 Provider 自行决定在 `parse_feed()` 或 `discover()` 返回的 feeds 是否 **validated**
- `valid` 字段由 Provider 设置，用于区分是否经过验证
- Provider 可以返回部分验证的 feeds（`valid=True`）和未验证的 feeds（`valid=False`）

**RSSProvider 验证规则：**
- `parse_feed()`: 返回已验证的 feed（`valid=True`）
- `discover()`: 返回已验证的 feed（`valid=True`）- 因为在 discover 内部并行试探后统一验证

### DiscoveredFeed Source Types

| Source | Description |
|--------|-------------|
| `RSSProvider` | 通过 RSSProvider 的 parse_feed() 或 discover() 发现/验证 |
| `GitHubReleaseProvider` | 通过 GitHubReleaseProvider 的 parse_feed() 发现/验证 |
| `WebpageProvider` | 通过 WebpageProvider 的 parse_feed() 发现/验证 |
| `direct_url` | URL 本身是有效 feed（max_depth=1 直接验证） |

## PageSelectors Type

`compute_selectors()` 返回 PageSelectors 对象：

```python
@dataclass
class PageSelectors:
    selectors: dict[str, LinkSelector]  # path → LinkSelector
    url: str                            # 当前页面 URL

@dataclass
class LinkSelector:
    path: str      # 路径前缀（如 '/news/'）
    link: str     # 示例链接 URL
    text: str     # 链接文本（可选）
    count: int    # 该前缀下的链接数量
```

**使用场景：**
- 仅 `max_depth=1` 时返回 selectors（计算成本高）
- BFS 爬取时不返回 selectors（为空 `{}`）

## 废弃的函数（保留但不调用）

以下函数已废弃，新代码不再调用：

- `_discover_feeds_on_page()` - 页面发现逻辑，已由 Provider discover() 替代
- `parse_link_elements()` - autodiscovery 解析，已由 Provider discover() 替代
- `_find_feed_links_on_page()` - CSS selector 发现，已由 Provider discover() 替代
- `_probe_well_known_paths()` - well-known 路径探测，已由 Provider discover() 替代
