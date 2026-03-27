---
phase: quick
plan: "260327-feu"
type: execute
wave: 1
depends_on: []
files_modified:
  - src/cli/__init__.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "feed list command no longer triggers HuggingFace SSL errors"
    - "CLI commands that don't need semantic search start without embedding model network calls"
  artifacts:
    - path: src/cli/__init__.py
      provides: CLI initialization without preload_embedding_model call
  key_links:
    - from: src/cli/__init__.py
      to: src/storage/vector.py
      via: removed import and call of preload_embedding_model
---

<objective>
Remove preload_embedding_model() call from CLI init to prevent feed list triggering HuggingFace SSL errors.
</objective>

<context>
@src/cli/__init__.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove preload_embedding_model call from CLI init</name>
  <files>src/cli/__init__.py</files>
  <action>
    Remove the preload_embedding_model() call block from src/cli/__init__.py (lines 31-39):
    - Remove the try/except block that imports and calls preload_embedding_model()
    - Keep init_db() call intact

    The removed code should look like:
    ```python
    # Pre-download embedding model for ChromaDB (SEM-03, D-04)
    # If this fails (network, SSL), semantic search will download on first use
    try:
        from src.storage.vector import preload_embedding_model
        preload_embedding_model()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Could not preload embedding model: %s. Semantic search will download on first use.", e)
    ```
  </action>
  <verify>
    <automated>grep -n "preload_embedding_model" src/cli/__init__.py; echo "Exit code: $?"</automated>
  </verify>
  <done>src/cli/__init__.py no longer calls preload_embedding_model()</done>
</task>

</tasks>

<verification>
- `grep -n "preload_embedding_model" src/cli/__init__.py` returns no matches
- `python3 -c "from src.cli import cli; print('CLI imports OK')"` succeeds
- `python3 src/cli/feed.py --help` (or feed list) runs without SSL/HuggingFace errors
</verification>

<success_criteria>
- src/cli/__init__.py has no import or call to preload_embedding_model
- CLI commands that don't use semantic search (like feed list) start without HuggingFace network errors
</success_criteria>

<output>
After completion, create `.planning/quick/260327-feu-remove-preload-embedding-model-from-cli-/260327-feu-SUMMARY.md`
</output>
