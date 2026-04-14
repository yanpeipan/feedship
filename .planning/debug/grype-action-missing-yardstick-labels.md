# Debug: grype-action-missing-yardstick-labels

## Issue Summary
GitHub Actions lint workflow failing at `anchore/grype@main` step — "Could not find file '.yardstick/labels'"

## Timeline
- Issue introduced in quick task `260410-fju` when changing from `anchore/grype@latest` to `anchore/grype@main`

## Root Cause Analysis

### Investigation Steps Completed

1. **Reviewed lint.yml configuration**
   - Line 16: `uses: anchore/grype@main`
   - The grype step runs before Python setup

2. **Researched grype release structure**
   - Latest grype release: `v0.111.0` (released 2026-04-09)
   - There is NO separate `anchore/grype-action` repository
   - The `anchore/grype` repository IS the GitHub Action

3. **Analyzed the error path**
   - Error: `/home/runner/work/_actions/_temp_.../_staging/anchore-grype-1f19355/test/quality/.yardstick/labels`
   - The `_staging/anchore-grype-*` path reveals this is using the grype repo's own test infrastructure
   - Path includes `test/quality/.yardstick/` - the grype repo's internal test directory

4. **Identified root cause**
   - When using `@main`, the action runs internal validation/testing scripts from the grype repo
   - These internal scripts expect test fixtures like `.yardstick/labels` to exist
   - The `@main` branch is a development branch with internal test dependencies not available in CI

### Conclusion
**The `anchore/grype@main` reference is problematic because:**
- The `main` branch contains internal test infrastructure and validation scripts
- Using `@main` runs development/testing code paths that expect test fixtures to exist
- The error occurs because the CI environment cannot access internal test files from the grype repo's test directory

## Recommended Fix

**Change in `.github/workflows/lint.yml`:**
```yaml
# Before (broken):
- uses: anchore/grype@main

# After (fixed):
- uses: anchore/grype@v0.111.0
# OR
- uses: anchore/grype@latest
```

### Rationale
- `@latest` or a specific version tag (`@v0.111.0`) points to the released, production-ready code
- Released versions don't run internal validation scripts
- The `main` branch is meant for development, not for CI consumption

## Verification
- Latest grype release is `v0.111.0` (2026-04-09)
- Historical releases available: v0.110.0, v0.109.1, v0.109.0, etc.
