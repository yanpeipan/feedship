---
phase: quick-260410-fju
plan: "01"
subsystem: infra
tags: [github-actions, grype, security-scanner]

key-files:
  created: []
  modified:
    - .github/workflows/lint.yml

key-decisions:
  - "Use @main branch ref for anchore/grype action instead of non-existent @latest tag"

requirements-completed: [QTFJU-01]

# Metrics
duration: <1min
completed: 2026-04-10
---

# Quick Task 260410-fju: Fix GitHub Actions Lint Error Summary

**Fixed anchore/grype action reference from @latest to @main — resolves "Unable to resolve action" error in GitHub CI**

## Performance

- **Duration:** <1 min
- **Started:** 2026-04-10T00:00:00Z
- **Completed:** 2026-04-10T00:00:00Z
- **Tasks:** 1
- **Files modified:** 1

## Task Commits

1. **Task 1: Change anchore/grype@latest to anchore/grype@main** - `c5beb23` (fix)

## Files Modified

- `.github/workflows/lint.yml` - Changed line 16 from `anchore/grype@latest` to `anchore/grype@main`

## Decisions Made

- anchore/grype does not publish a `latest` tag, causing GitHub Actions to fail with "Unable to resolve action" error
- Using `@main` branch ref is the correct resolution — GitHub Actions resolves branch refs correctly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - single-line fix executed successfully on first attempt.

---
*Quick task: 260410-fju*
*Completed: 2026-04-10*
