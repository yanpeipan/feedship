# src/discovery & src/providers 重构方案

## 核心目标

discovery 负责"发现"，providers 负责"验证和抓取"，职责分离：
- discovery 的 HTTP 请求用于发现（探测页面、解析 HTML）
- providers 通过 `match(url, response)` 验证 feed 是否可被处理
- 最终 `DiscoveredResult.feeds` 只包含 providers 确认可抓取的 feeds

---

## 核心流程

```
discovery.discover_feeds(url)
    │
    │
    ├─► deep_crawl(url, max_depth, auto_discover=True) → DiscoveredResult
    │       │
    |       ├─► HTTP GET url → response
    │       ├─► providers.match(url, response) → List[Provider] (matched_providers) ── 验证当前URL & response
            │   matched_providers(for each provider).parse_feed(url, response) → List[DiscoveredFeed] (feeds)
            ├─► if auto_discover:
            │       matched_providers(for each provider).discover(url, response) → List[DiscoveredFeed] (feeds, response)
            │
            └─► 返回 List[DiscoveredFeed]（已验证）
```

---

## 关键 API 变更

### 1. `ContentProvider.match(url, response)` → `match(url, response)`

**当前**:
```python
def match(self, url: str, result: Optional[Any] = None) -> bool
```

**重构后**:
```python
def match(self, url: str, response: Optional[HTTPResponse] = None) -> bool
```

- `response`: discovery 阶段获得的 HTTP 响应，用于辅助判断
- 如果 `response` 非空，provider 可以根据 content-type、body 等直接判断
- 如果 `response` 为空，provider 需要自己发请求验证

### 2. `discovery.discover_feeds()` 返回已验证的 feeds

**当前**:
```python
def discover_feeds(url: str, max_depth: int = 1) -> DiscoveredResult:
    # 发现 feeds，但不验证 providers 是否能处理
    # cli/feed.py 后续调用 providers.discover() 补充
```

**重构后**:
```python
def discover_feeds(url: str, max_depth: int = 1) -> DiscoveredResult:
    # 内部调用 providers.discover()
    # 返回的 feeds 已通过 providers 验证
```

### 3. 移除 cli/feed.py 中的 provider 补充逻辑

**当前**:
```python
# cli/feed.py
result = discover_feeds(url)
# ... 后又调用 providers.discover() 补充 ...
```

**重构后**:
```python
# cli/feed.py
result = discover_feeds(url)  # 包含 providers 验证
```

---

## 实现步骤

### Step 1: 确认 Response 类型

使用 `scrapling.engines.toolbelt.custom.Response` - 无需新建类型

```python
from scrapling.engines.toolbelt.custom import Response
# Response 有 url, status, headers, content, content_type 等属性
```

### Step 2: 更新 ContentProvider.match() 签名

**base.py**:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from scrapling.engines.toolbelt.custom import Response

def match(self, url: str, response: "Response" = None) -> bool:
    """Return True if this provider handles the URL.

    Args:
        url: URL to check.
        response: Optional HTTP response from discovery phase.
            If None, provider should not make HTTP requests - only use URL.
    """
    ...
```

**rss_provider.py**:
```python
def match(self, url: str, response: "Response" = None) -> bool:
    if response:
        # 根据 response 的 content-type 直接判断（不发请求）
        ct = response.content_type or ""
        if any(t in ct for t in ("xml", "rss", "atom")):
            return True
    # response 为空时，只用 URL 判断，不发请求
    ...
```

### Step 3: 更新 providers/__init__.discover()

保留作为独立函数：

```python
def discover(url: str, response: "Response" = None) -> List[DiscoveredFeed]:
    """Find and validate feeds from providers matching a URL.

    Args:
        url: URL to match against providers.
        response: Optional HTTP response from discovery phase.
            If None, provider.match() only uses URL.

    Returns:
        List of DiscoveredFeed from matching providers.
    """
    from src.providers.rss_provider import RSSProvider

    matched = [p for p in PROVIDERS if p.match(url, response)]
    feeds = []
    seen = set()
    for provider in matched:
        try:
            feed_meta = provider.feed_meta(url)
            if feed_meta.url not in seen:
                seen.add(feed_meta.url)
                feeds.append(DiscoveredFeed(...))
        except Exception:
            pass
    return feeds
```

### Step 4: 重构 discovery.discover_feeds()

在 `discovery/__init__.py` 的 `discover_feeds()` 中：

```python
def discover_feeds(url: str, max_depth: int = 1) -> DiscoveredResult:
    from src.discovery.deep_crawl import deep_crawl
    from src.providers import discover as providers_discover
    from scrapling.engines.toolbelt.custom import Response

    # 1. 初始 HTTP 请求获取 response（用于 match）
    response = _fetch_url(url)  # 返回 scrapling.Response

    # 2. deep_crawl 发现 feeds + selectors
    crawl_result = deep_crawl(url, max_depth)
    feeds = crawl_result.feeds
    selectors = crawl_result.selectors

    # 3. 将 response 传给 providers 验证发现的 feeds
    provider_feeds = providers_discover(url, response)
    for pfeed in provider_feeds:
        if pfeed.url not in {f.url for f in feeds}:
            feeds.append(pfeed)

    return DiscoveredResult(
        url=url,
        max_depth=max_depth,
        feeds=feeds,
        selectors=selectors,
    )
```

### Step 5: 移除 cli/feed.py 中的 provider 补充逻辑

`cli/feed.py` 不再需要单独调用 `providers.discover()`。

---

## 共享常量

新建 `src/constants.py`：

```python
"""Shared constants across the application."""

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RadarBot/1.0; +https://radar.example.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
```

更新 `discovery/__init__.py` 和 `deep_crawl.py` 使用 `constants.BROWSER_HEADERS`。

---

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `src/constants.py` | 共享常量 (BROWSER_HEADERS) |
| 修改 | `src/providers/base.py` | `match(url, response)`, response 类型为 `scrapling.Response` |
| 修改 | `src/providers/rss_provider.py` | `match` 使用 response，不发请求 |
| 修改 | `src/providers/webpage_provider.py` | `match` 使用 response |
| 修改 | `src/providers/github_release_provider.py` | `match` 使用 response |
| 修改 | `src/providers/default_provider.py` | `match` 使用 response |
| 修改 | `src/providers/__init__.py` | `discover(url, response)` 签名更新 |
| 修改 | `src/discovery/__init__.py` | `discover_feeds` 内部调用 providers.discover() |
| 修改 | `src/cli/feed.py` | 移除 provider 补充逻辑 |

---

## 验证测试

```bash
# 基本发现测试
python -m src.cli feed add https://www.infoq.cn/

# GitHub 测试
python -m src.cli feed add https://github.com/python/cpython

# 直接 RSS 测试
python -m src.cli feed add https://www.infoq.cn/feed
```
