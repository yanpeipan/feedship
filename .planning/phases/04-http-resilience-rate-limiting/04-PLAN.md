---
phase: 04-http-resilience-rate-limiting
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/utils/scraping_utils.py
  - config.yaml
autonomous: true
requirements:
  - RESL-01
  - RESL-02
  - RESL-03

must_haves:
  truths:
    - "TokenBucket rate limiter enforces 10 req/min per domain by default"
    - "Rate limiter is configurable via settings.rate_limit.requests_per_minute"
    - "CircuitBreakerState class exists with failure tracking and state machine"
    - "NitterProvider returns 304 with empty articles, preserves etag/modified_at"
    - "WebpageProvider returns 304 with empty articles, preserves etag/modified_at"
    - "Circuit breaker integration in fetch_one_async skips OPEN providers"
  artifacts:
    - path: src/utils/scraping_utils.py
      contains: "class TokenBucket"
      min_lines: 60
    - path: src/utils/scraping_utils.py
      contains: "class CircuitBreakerState"
      min_lines: 80
    - path: config.yaml
      contains: "rate_limit:"
    - path: src/providers/nitter_provider.py
      contains: "304"
    - path: src/providers/webpage_provider.py
      contains: "304"
    - path: src/application/fetch.py
      contains: "circuit"
  key_links:
    - from: src/utils/scraping_utils.py
      to: config.yaml
      via: settings.get("rate_limit.requests_per_minute")
    - from: src/application/fetch.py
      to: src/utils/scraping_utils.py
      via: _provider_circuits
---

<objective>
Implement TokenBucket rate limiter (RESL-01), conditional fetch with 304 handling (RESL-02), and circuit breaker integration (RESL-03).

Purpose: Time-based rate limiting per domain, ETag/Last-Modified conditional requests, and circuit breaker to skip failing providers.
Output: TokenBucket class, CircuitBreakerState class, 304 handling in Nitter/Webpage providers, circuit breaker in fetch_one_async, updated config.yaml
</objective>

<context>
@src/utils/scraping_utils.py:56-68,334-367
@src/providers/base.py:23-29
@src/providers/rss_provider.py:48-68 (304 handling pattern)
@src/providers/nitter_provider.py:80-113
@src/providers/webpage_provider.py (fetch_articles method)
@src/application/fetch.py:24-61
@config.yaml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement TokenBucket and CircuitBreakerState classes</name>
  <files>src/utils/scraping_utils.py</files>
  <action>
    Add TokenBucket and CircuitBreakerState classes to `src/utils/scraping_utils.py` near line 60 (after existing rate limit globals).

    TokenBucket class:
    ```python
    class TokenBucket:
        """Time-based token bucket rate limiter using time.monotonic().

        Refills tokens at a steady rate: requests_per_minute / 60 tokens per second.
        Uses asyncio.Lock for thread-safe token consumption.
        """

        def __init__(self, requests_per_minute: float = 10.0):
            self._rate = requests_per_minute / 60.0  # tokens per second
            self._capacity = requests_per_minute
            self._tokens = requests_per_minute
            self._last_refill = time.monotonic()
            self._lock = asyncio.Lock()

        async def acquire(self) -> None:
            """Acquire a token, waiting if necessary."""
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                self._last_refill = now

                if self._tokens < 1.0:
                    wait_time = (1.0 - self._tokens) / self._rate
                    await asyncio.sleep(wait_time)
                    self._tokens = 0.0
                else:
                    self._tokens -= 1.0
    ```

    CircuitBreakerState class:
    ```python
    class CircuitBreakerState:
        """Circuit breaker per provider with CLOSED/OPEN/HALF_OPEN states.

        State machine:
        - CLOSED: Normal operation, tracks consecutive failures
        - OPEN: After 5 consecutive failures, skip provider for 60s cooldown
        - HALF_OPEN: After cooldown, allow 1 test request

        Thread-safe using asyncio.Lock.
        """

        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"

        def __init__(self, failure_threshold: int = 5, cooldown_seconds: float = 60.0):
            self._failure_threshold = failure_threshold
            self._cooldown = cooldown_seconds
            self._failures = 0
            self._state = self.CLOSED
            self._last_failure_time: float | None = None
            self._lock = asyncio.Lock()

        @property
        def state(self) -> str:
            return self._state

        async def record_success(self) -> None:
            """Reset failure count on success."""
            async with self._lock:
                self._failures = 0
                self._state = self.CLOSED

        async def record_failure(self) -> None:
            """Increment failure count, potentially opening circuit."""
            async with self._lock:
                self._failures += 1
                self._last_failure_time = time.monotonic()
                if self._failures >= self._failure_threshold:
                    self._state = self.OPEN

        async def can_execute(self) -> bool:
            """Check if request should proceed.

            Returns True if circuit is CLOSED or HALF_OPEN.
            Transitions OPEN -> HALF_OPEN after cooldown.
            """
            async with self._lock:
                if self._state == self.CLOSED:
                    return True

                if self._state == self.OPEN:
                    if self._last_failure_time and \
                       time.monotonic() - self._last_failure_time >= self._cooldown:
                        self._state = self.HALF_OPEN
                        return True
                    return False

                # HALF_OPEN: allow one test request
                return True
    ```

    Add globals:
    - `_host_token_buckets: dict[str, TokenBucket]`
    - `_bucket_lock: asyncio.Lock`
    - `_provider_circuits: dict[str, CircuitBreakerState]`
    - `_circuit_lock: asyncio.Lock`
  </action>
  <verify>
    <automated>python -c "from src.utils.scraping_utils import TokenBucket, CircuitBreakerState; import asyncio; tb = TokenBucket(10); cb = CircuitBreakerState(); asyncio.run(tb.acquire()); print('TokenBucket works'); print(cb.state)"</automated>
  </verify>
  <done>TokenBucket and CircuitBreakerState classes with proper asyncio.Lock protection</done>
</task>

<task type="auto">
  <name>Task 2: Update _rate_limit_host() to use TokenBucket</name>
  <files>src/utils/scraping_utils.py</files>
  <action>
    Modify `_rate_limit_host()` function (lines 334-367) to use TokenBucket.

    Changes:
    1. Get `requests_per_minute` from settings: `settings.get("rate_limit.requests_per_minute", 10.0)`
    2. Get or create per-host TokenBucket (not semaphore for rate limiting)
    3. Use existing per-host semaphore for concurrency control (keep as-is)
    4. NEW: Call `await bucket.acquire()` after acquiring semaphore

    Flow should be:
    ```
    1. Acquire per-host semaphore (concurrency limit)
    2. Acquire token from per-host TokenBucket (rate limit)
    3. Return both to caller (semaphore released after fetch)
    ```

    Note: The function signature stays the same, rate_limit param still ignored (D-08: rate limiter wraps existing function but uses config).
  </action>
  <verify>
    <automated>python -c "
import asyncio
from src.utils.scraping_utils import _rate_limit_host
async def test():
    sem = await _rate_limit_host('https://example.com')
    print(f'Semaphore acquired: {sem is not None}')
    sem.release()
asyncio.run(test())
"</automated>
  </verify>
  <done>_rate_limit_host() uses TokenBucket for time-based rate limiting, semaphore still handles concurrency</done>
</task>

<task type="auto">
  <name>Task 3: Add rate_limit config to config.yaml</name>
  <files>config.yaml</files>
  <action>
    Add rate_limit section to config.yaml (after existing sections):

    ```yaml
    # Rate limiting configuration
    rate_limit:
      requests_per_minute: 10  # Per-domain default
    ```

    This enables per-domain rate limiting without modifying provider code.
  </action>
  <verify>
    <automated>python -c "
from src.application.config import _get_settings
settings = _get_settings()
rpm = settings.get('rate_limit.requests_per_minute', 10)
print(f'Rate limit config: {rpm} req/min')
"</automated>
  </verify>
  <done>config.yaml has rate_limit.requests_per_minute setting</done>
</task>

<task type="auto">
  <name>Task 4: Add 304 handling to NitterProvider (RESL-02)</name>
  <files>src/providers/nitter_provider.py</files>
  <action>
    Add conditional fetch support and 304 handling to NitterProvider.

    Pattern to follow (from RSSProvider.fetch_articles, lines 143-168):
    1. Modify fetch_articles to accept etag/modified_at parameters via feed object
    2. Check response.status == 304
    3. On 304: log info, return FetchedResult(articles=[], etag=feed.etag, modified_at=feed.modified_at)
    4. On success: extract etag/modified_at from response.headers

    The NitterProvider uses _fetch_and_parse internally which calls _fetch_feed_content_sync via RSSFetcher.
    You may need to modify the internal _fetch_feed_content_sync call or wrap the response handling.

    Key: Feed object already has .etag and .modified_at attributes - use these for conditional requests.
  </action>
  <verify>
    <automated>python -c "
from src.providers.nitter_provider import NitterProvider
from src.models import Feed
import json

# Create feed with etag to test 304 handling path
feed = Feed(id=1, url='https://nitter.net/elonmusk', metadata=json.dumps({'feed_type': 'nitter'}))
feed.etag = '\"abc123\"'
feed.modified_at = None

provider = NitterProvider()
print(f'NitterProvider has fetch_articles: {hasattr(provider, \"fetch_articles\")}')
"</automated>
  </verify>
  <done>NitterProvider returns empty articles on 304, preserves etag/modified_at</done>
</task>

<task type="auto">
  <name>Task 5: Add 304 handling to WebpageProvider (RESL-02)</name>
  <files>src/providers/webpage_provider.py</files>
  <action>
    Add conditional fetch support and 304 handling to WebpageProvider.

    Pattern to follow (from RSSProvider.fetch_articles):
    1. Modify fetch_articles to use feed.etag and feed.modified_at for conditional requests
    2. Check response.status == 304
    3. On 304: log info, return FetchedResult(articles=[], etag=feed.etag, modified_at=feed.modified_at)
    4. On success: extract etag/modified_at from response.headers

    Read the WebpageProvider.fetch_articles method to understand how it fetches and parses content.
    Apply the same 304 handling pattern.
  </action>
  <verify>
    <automated>python -c "
from src.providers.webpage_provider import WebpageProvider
print(f'WebpageProvider has fetch_articles: {hasattr(WebpageProvider, \"fetch_articles\")}')
"</automated>
  </verify>
  <done>WebpageProvider returns empty articles on 304, preserves etag/modified_at</done>
</task>

<task type="auto">
  <name>Task 6: Integrate circuit breaker in fetch_one_async (RESL-03)</name>
  <files>src/application/fetch.py</files>
  <action>
    Integrate circuit breaker into fetch_one_async() (lines 24-61).

    Changes in fetch_one_async():
    1. Import circuit globals: `from src.utils.scraping_utils import _provider_circuits, _circuit_lock`
    2. Get or create circuit for provider class name: `provider_name = provider.__class__.__name__`
    3. Before calling provider.fetch_articles:
       - Check `circuit.can_execute()` (use asyncio.to_thread for sync call)
       - If circuit is OPEN (can_execute returns False), log warning and return {"new_articles": 0, "error": f"Circuit open for {provider_name}"}
    4. After fetch completes (before returning):
       - On success (no exception): `await circuit.record_success()`
       - On failure (exception): `await circuit.record_failure()`

    Use asyncio.to_thread for can_execute() since it returns a coroutine but needs to be called from sync context.
  </action>
  <verify>
    <automated>python -c "
from src.utils.scraping_utils import _provider_circuits
from src.providers.rss_provider import RSSProvider
print(f'Circuits dict exists: {_provider_circuits is not None}')
print(f'RSSProvider circuit initialized: {RSSProvider.__name__ in _provider_circuits}')
"</automated>
  </verify>
  <done>fetOne_async skips providers with OPEN circuit, records success/failure</done>
</task>

</tasks>

<verification>
After Wave 1 (RESL-01):
- `python -c "from src.utils.scraping_utils import TokenBucket, CircuitBreakerState; print('Imports OK')"` passes
- Rate limiter reads from config.yaml

After Wave 2 (RESL-02 + RESL-03 integration):
- NitterProvider handles 304 responses
- WebpageProvider handles 304 responses
- Circuit breaker integration in fetch_one_async works
</verification>

<success_criteria>
1. TokenBucket class uses time.monotonic() for token refill
2. TokenBucket is per-host (keyed by netloc)
3. CircuitBreakerState has CLOSED/OPEN/HALF_OPEN state machine
4. _rate_limit_host() acquires both semaphore AND TokenBucket
5. config.yaml has rate_limit.requests_per_minute setting
6. NitterProvider returns empty articles on 304 with preserved etag/modified_at
7. WebpageProvider returns empty articles on 304 with preserved etag/modified_at
8. fetch_one_async checks circuit.can_execute() before calling provider
9. fetch_one_async records success/failure after provider fetch
</success_criteria>

<output>
After completion, create `.planning/phases/04-http-resilience-rate-limiting/04-01-SUMMARY.md`
</output>
