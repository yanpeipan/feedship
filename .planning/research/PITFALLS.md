# Pitfalls Research

**Domain:** Plugin-based Provider Architecture for Python CLI
**Researched:** 2026-03-23
**Confidence:** MEDIUM (established Python patterns; verify with official docs and community wisdom)

## Critical Pitfalls

### Pitfall 1: Circular Import Chain

**What goes wrong:**
`ImportError: cannot import name 'ProviderRegistry' from partially initialized module` — application fails to start, often with misleading tracebacks pointing at unrelated imports.

**Why it happens:**
Classic chicken-and-egg problem. Common patterns that trigger it:
- Main app imports a plugin at module level, plugin imports main app
- Plugin `__init__.py` imports from main package
- `importlib` loads plugin which immediately tries to access shared state
- Database models imported by both main app and plugin before initialization completes

**How to avoid:**
1. Use `TYPE_CHECKING` for type hints only, never for runtime imports
2. Defer all imports inside plugin functions/methods (lazy import pattern)
3. Pass dependencies as parameters rather than importing shared state
4. Keep plugin interface isolated — plugins should receive data, not import from core
5. Use `importlib` with explicit module paths, not `from x import *`

```python
# BAD — triggers circular import
# main.py
from providers import rss_provider
# providers/__init__.py
from main import ProviderRegistry  # circular!

# GOOD — deferred import
# main.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from providers import ProviderRegistry
# In function, not at module level:
def load_plugins():
    from providers import get_providers  # deferred
    return get_providers()
```

**Warning signs:**
- Any `from main import X` or `from . import X` in plugin `__init__.py`
- Application startup fails with `AttributeError` on seemingly unrelated objects
- Traceback shows imports in unexpected order

**Phase to address:**
Phase 1 (Plugin Core Infrastructure)

---

### Pitfall 2: Plugin Interface Drift

**What goes wrong:**
Plugin works in isolation but causes cryptic errors when integrated. Methods are called with wrong signatures, return values are unexpected, lifecycle hooks are missing.

**Why it happens:**
No explicit interface definition. Plugin authors guess at expected behavior:
- No `Protocol` class defining required methods
- No abstract base class enforcing contract
- Documentation exists but is not enforced
- Breaking changes in core without corresponding plugin updates

**How to avoid:**
1. Define `ProviderProtocol` using Python's `typing.Protocol`
2. Use `@runtime_checkable` decorator for verification
3. Document method signatures, return types, and exceptions explicitly
4. Create a "blessed" example plugin that demonstrates correct implementation
5. Add runtime validation at plugin load time, not discovery time

```python
from typing import Protocol, runtime_checkable
from abc import abstractmethod

@runtime_checkable
class FeedProvider(Protocol):
    """Interface all feed providers must implement."""

    @property
    def name(self) -> str:
        """Unique provider identifier."""
        ...

    @abstractmethod
    def fetch(self, url: str) -> list[Article]:
        """Fetch articles from provider."""
        ...

    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """Check if URL is supported by this provider."""
        ...
```

**Warning signs:**
- Plugin works when tested standalone, fails when integrated
- "Missing positional argument" errors at runtime
- Different plugins return different shapes for same operation
- No clear error when plugin method signature is wrong

**Phase to address:**
Phase 1 (Plugin Core Infrastructure) — define interfaces before plugins

---

### Pitfall 3: Monolithic Plugin Loading (No Isolation)

**What goes wrong:**
One buggy plugin crashes entire application. Plugin can access/modify internal state of other plugins or core. Memory leaks in plugins accumulate.

**Why it happens:**
Plugins loaded into same Python process without sandboxing:
- No error isolation — unhandled exception in plugin kills main loop
- Plugins share global namespace
- No lifecycle hooks (no unload/cleanup)
- Plugin can modify singletons or global state

**How to avoid:**
1. Wrap plugin calls in try/except with clear error messages
2. Implement optional plugin lifecycle: `load()`, `unload()`, `shutdown()`
3. Create plugin context that limits what plugins can access
4. Consider running plugins in subprocess if isolation is critical (complexity tradeoff)
5. Log plugin errors with provider name for debugging

```python
def invoke_provider(provider: FeedProvider, url: str) -> list[Article]:
    try:
        return provider.fetch(url)
    except Exception as e:
        logger.error(f"Provider {provider.name} failed: {e}")
        raise ProviderError(f"{provider.name}: {e}") from e
```

**Warning signs:**
- Adding a new plugin requires restarting app to avoid state pollution
- Removing a plugin leaves residual state
- No way to disable a plugin without code changes
- Debugging requires restarting entire application

**Phase to address:**
Phase 2 (Provider Integration) — error isolation is foundation

---

### Pitfall 4: Hardcoded Migration Trap

**What goes wrong:**
Old hardcoded RSS/GitHub handling breaks during migration. Existing feeds stop working. Migration is attempted all at once rather than incrementally.

**Why it happens:**
Refactoring without maintaining backward compatibility:
- Old `refresh_feed()` is replaced entirely before new plugin system is verified
- No way to use old code path for comparison/testing
- Database schema assumes new plugin system immediately
- Migration commits to plugin architecture before validating it works for existing use cases

**How to avoid:**
1. **Strangler fig pattern**: Keep old code working, add plugin system alongside, migrate incrementally
2. Implement plugin that wraps existing RSS handling as "legacy provider"
3. Feature flag the plugin system, off by default initially
4. Ensure existing feeds continue working through old path
5. Write integration tests comparing old vs new results before switching

```python
# Good: Legacy provider wrapping existing code
class LegacyRSSProvider:
    """Wrapper around existing feeds.py functionality."""
    def __init__(self):
        self._legacy = FeedsManager()  # Existing class

    def fetch(self, url: str) -> list[Article]:
        # Delegates to existing refresh_feed logic
        return self._legacy.refresh_feed(url)
```

**Warning signs:**
- "We'll migrate everything at once" plan
- No fallback path if plugin architecture has issues
- Existing functionality has no test coverage during transition
- Database changes coupled with architectural changes

**Phase to address:**
Phase 1 (Plugin Core Infrastructure) — plan for incremental migration

---

### Pitfall 5: Entry Point Discovery Failures

**What goes wrong:**
Plugins installed but not discovered. `pip install` seems to work but plugin never appears. Debugging why plugin is not loading is difficult.

**Why it happens:**
Misconfigured entry points or packaging:
- Entry point group name typo (case sensitivity, wrong string)
- Plugin not properly registered in `pyproject.toml` or `setup.py`
- Multiple entry point definitions conflicting
- Console script vs library entry points confusion
- Installation not in editable mode during development

**How to avoid:**
1. Use consistent entry point group naming convention
2. Validate entry points load correctly during development
3. Log discovered plugins with version info at startup
4. Create CLI command to list loaded plugins for debugging
5. Document exact `pyproject.toml` configuration required

```toml
# pyproject.toml
[project.entry-points."radar.providers"]
rss = "radar_providers.rss:RSSProvider"
github = "radar_providers.github:GithubProvider"
```

```python
# Discovery verification
from importlib.metadata import entry_points

def list_plugins():
    eps = entry_points(group="radar.providers")
    for ep in eps:
        print(f"{ep.name}: {ep.value}")
```

**Warning signs:**
- `pip install -e .` succeeds but plugin not visible
- Plugin only loads in dev, not after `pip install`
- Different behavior between `python -m myapp` and installed executable
- No feedback when plugin fails to load (silent failure)

**Phase to address:**
Phase 1 (Plugin Core Infrastructure)

---

### Pitfall 6: Plugin Version Compatibility

**What goes wrong:**
Plugin designed for older version crashes application. Or new plugin version breaks because API changed. No visibility into which plugin versions work.

**Why it happens:**
No version checking or interface versioning:
- Plugin declares no required API version
- Core makes breaking changes without plugin awareness
- No plugin version reporting
- Plugin pins to wrong core version

**How to avoid:**
1. Include `api_version` in plugin interface
2. Check version compatibility at load time
3. Log warning (not error) for minor version mismatches
4. Semantic versioning for plugin interface itself
5. Maintain changelog for interface changes

```python
# In base provider
class BaseProvider:
    API_VERSION = "1.0"

    def __init__(self):
        if not hasattr(self, 'API_VERSION'):
            warnings.warn(f"{self.__class__.__name__} missing API_VERSION")

    def validate_api_version(self):
        if self.API_VERSION != BaseProvider.API_VERSION:
            raise PluginError(
                f"Plugin {self.name} API {self.API_VERSION} "
                f"incompatible with core {BaseProvider.API_VERSION}"
            )
```

**Warning signs:**
- No `__version__` or `API_VERSION` in plugins
- No error when plugin targets wrong core version
- Silent degradation instead of clear error
- Cannot tell which version of plugin is loaded

**Phase to address:**
Phase 1 (Plugin Core Infrastructure) — version contract

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip Protocol/ABC definition | Faster initial plugin writing | Runtime errors instead of clear failures | Never — causes debugging nightmares |
| Import plugin at module level | Simpler code | Circular import trap | Never |
| Skip error isolation | Simpler code | One plugin crashes app | MVP only, must fix before production |
| No lifecycle hooks | Fewer methods to implement | Resource leaks, no cleanup | Never for production plugins |
| Hardcode plugin list instead of discovery | No packaging complexity | Must edit code to add plugins | Development only, debugging |
| Skip version checking | No compatibility code | Silent breakage | MVP only |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SQLite database | Plugin opens own connection, causing locking | Pass db connection to plugins, single shared connection |
| CLI framework (click) | Plugin registers its own commands globally | Plugin returns commands, main app registers them |
| Logging | Plugin creates its own logger | Accept logger as initialization parameter |
| Configuration | Plugin reads config file directly | Accept config dict or path at initialization |
| HTTP client (httpx) | Plugin creates its own client | Use provided client or initialize with proper timeout |
| Existing RSS handling | Duplicate/override existing refresh_feed | Wrap legacy code as provider |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Lazy import everything | First plugin call is slow | Pre-import critical paths | Interactive CLI with immediate feedback expected |
| Plugin discovery on every command | Slow startup | Cache discovered plugins | CLI tools where startup time matters |
| Plugin loading in main thread | UI freeze during load | Async loading or spinner | Any CLI with loading UX |
| No plugin caching | Memory grows with repeated runs | Implement instance caching | Long-running processes |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Plugin imports arbitrary code from internet | Code execution vulnerabilities | Pin plugin versions, verify source |
| Plugin filesystem access | Path traversal attacks | Sandboxing, restrict paths |
| Plugin sees environment variables | Credential leakage | Don't pass `os.environ` directly |
| No plugin signing/verification | Tampered plugin runs | Checksum verification for production |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No plugin list command | Users don't know what's available | `myapp plugin list` |
| Silent plugin load failures | Plugin doesn't work, no explanation | Clear error: "Plugin X failed to load: [reason]" |
| No plugin enable/disable | Can't disable buggy plugin | Config-based plugin toggle |
| Plugin has no help text | Users don't know how to use | Standardized help interface |
| Mixed plugin origins | Unknown which plugin is "official" | Clearly mark built-in vs third-party |

---

## "Looks Done But Isn't" Checklist

- [ ] **Plugin Loading:** Plugins are discovered but verify ALL plugins actually load — check for silent failures
- [ ] **Error Isolation:** Test each plugin individually fails — does app continue?
- [ ] **Interface Compliance:** Use `runtime_checkable` Protocol — not just documentation
- [ ] **Legacy Fallback:** Existing feeds still work after migration — integration test required
- [ ] **CLI Integration:** New provider architecture powers `feed add/refresh` commands — end-to-end test
- [ ] **Lifecycle:** Add plugin, remove plugin, restart app — no residual state
- [ ] **Version Compatibility:** Load plugin with wrong API version — clear error, not silent

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Circular import | MEDIUM | Move imports inside functions, add `TYPE_CHECKING` guard, restructure package |
| Plugin crashes app | LOW | Add try/except wrapper, log error with plugin name, continue with others |
| Hardcoded migration failure | HIGH | Revert to legacy path, fix plugin system in isolation, re-migrate |
| Entry point not found | LOW | Verify `pyproject.toml`, reinstall in editable mode, check group name |
| Version mismatch | LOW | Update plugin API version or core, log clearly what versions expected |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Circular import | Phase 1: Plugin Core Infrastructure | App starts, all plugins load, no ImportError |
| Interface drift | Phase 1: Define ProviderProtocol | `runtime_checkable` passes, plugin mismatch caught early |
| No isolation | Phase 2: Provider Integration | Test plugin raising exception — app continues |
| Hardcoded migration trap | Phase 1: Incremental migration plan | Existing feeds work via legacy wrapper, new feeds via plugin |
| Entry point failures | Phase 1: Plugin discovery | `myapp plugin list` shows all installed plugins |
| Version incompatibility | Phase 1: API versioning | Load wrong-version plugin — clear error, not silent |

---

## Sources

- [Python importlib.metadata documentation](https://docs.python.org/3/library/importlib.metadata.html) (HIGH confidence)
- [Python typing.Protocol documentation](https://docs.python.org/3/library/typing.html#typing.Protocol) (HIGH confidence)
- [Click plugin architecture patterns](https://click.palletsprojects.com/en/8.1.x/) (HIGH confidence)
- [Real Python: Python entry points](https://realpython.com/python-import-module-main/) (MEDIUM confidence)
- [Stack Overflow: Circular import patterns](https://stackoverflow.com/questions/2217476/) (MEDIUM confidence)
- [Python packaging user guide: entry points](https://packaging.python.org/en/latest/specifications/entry-points/) (HIGH confidence)

---

*Pitfalls research for: Plugin-based Provider Architecture v1.3*
*Researched: 2026-03-23*
