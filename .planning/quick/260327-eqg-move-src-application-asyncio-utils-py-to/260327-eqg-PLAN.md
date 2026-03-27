---
phase: quick
plan: "260327-eqg"
type: execute
wave: 1
depends_on: []
files_modified:
  - src/application/asyncio_utils.py (deleted)
  - src/utils/asyncio_utils.py (created)
  - src/cli/__init__.py (import updated)
autonomous: true
requirements: []
must_haves:
  truths:
    - "asyncio_utils module is accessible from src.utils.asyncio_utils"
    - "CLI initializes uvloop using the moved function"
  artifacts:
    - path: "src/utils/asyncio_utils.py"
      provides: "Async utilities (install_uvloop, run_in_executor_crawl)"
      min_lines: 93
    - path: "src/cli/__init__.py"
      provides: "Updated import path"
      contains: "from src.utils.asyncio_utils import install_uvloop"
  key_links:
    - from: "src/cli/__init__.py"
      to: "src/utils/asyncio_utils.py"
      via: "import statement"
      pattern: "from src.utils.asyncio_utils import install_uvloop"
---

<objective>
Move src/application/asyncio_utils.py to src/utils/asyncio_utils.py and update the single import site.
</objective>

<execution_context>
@/Users/y3/radar/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@src/application/asyncio_utils.py
@src/cli/__init__.py
@src/utils/__init__.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Move asyncio_utils.py to src/utils/</name>
  <files>src/utils/asyncio_utils.py</files>
  <action>
    Copy the contents of src/application/asyncio_utils.py to src/utils/asyncio_utils.py.
    The destination file should be an exact copy of the source file (93 lines).
    Do NOT modify the content - only copy the file.
  </action>
  <verify>Verify new file exists: test -f src/utils/asyncio_utils.py && wc -l src/utils/asyncio_utils.py | grep -q "93"</verify>
  <done>src/utils/asyncio_utils.py exists with identical 93-line content</done>
</task>

<task type="auto">
  <name>Task 2: Update import in src/cli/__init__.py</name>
  <files>src/cli/__init__.py</files>
  <action>
    In src/cli/__init__.py line 24, change:
    - FROM: from src.application.asyncio_utils import install_uvloop
    - TO: from src.utils.asyncio_utils import install_uvloop
    Keep everything else in the file unchanged.
  </action>
  <verify>grep -q "from src.utils.asyncio_utils import install_uvloop" src/cli/__init__.py && grep -v "src.application.asyncio_utils" src/cli/__init__.py | wc -l | grep -q "51"</verify>
  <done>Import updated to src.utils.asyncio_utils, no other changes to file</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Verify and cleanup</name>
  <what-built>File moved from src/application/ to src/utils/, import updated in src/cli/__init__.py</what-built>
  <how-to-verify>
    1. Run: python -c "from src.utils.asyncio_utils import install_uvloop; print('OK')"
    2. Verify src/application/asyncio_utils.py no longer exists: ls src/application/asyncio_utils.py should fail
    3. Run any CLI command to verify import works: python -m src.cli --help
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>

</tasks>

<verification>
python -c "from src.utils.asyncio_utils import install_uvloop; print('Import OK')"
</verification>

<success_criteria>
- src/utils/asyncio_utils.py exists with same 93-line content as original
- src/application/asyncio_utils.py deleted
- src/cli/__init__.py imports from src.utils.asyncio_utils (not src.application.asyncio_utils)
- CLI works correctly (python -m src.cli --help)
</success_criteria>

<output>
After completion, create `.planning/quick/260327-eqg-move-src-application-asyncio-utils-py-to/260327-eqg-SUMMARY.md`
</output>
