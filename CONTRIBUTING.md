# Contributing

## Dev Setup

```bash
# Clone and install dev dependencies
uv pip install -e ".[dev]"

# Install pre-commit hook (runs ruff before every commit)
pre-commit install
```

## Pre-commit Hook

The project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting. The hook runs automatically on `git commit`.

If ruff is not found during commit, install it:
```bash
uv pip install ruff
```
