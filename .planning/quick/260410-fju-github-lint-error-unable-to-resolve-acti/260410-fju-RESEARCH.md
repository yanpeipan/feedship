# Quick Task 260410-fju: GitHub Actions Lint Workflow - anchore/grype@latest Resolution Error

**Researched:** 2026-04-10
**Confidence:** MEDIUM

## Summary

The lint workflow fails because `anchore/grype@latest` cannot be resolved. The `anchore/grype` repository is a Docker-based GitHub Action (no `action.yml` at root — uses `Dockerfile`) and does not publish a `latest` tag that GitHub Actions can resolve. User decision to use `@main` is valid and correct.

**Primary fix:** Change line 16 of `.github/workflows/lint.yml` from `anchore/grype@latest` to `anchore/grype@main`.

## What the Error Means

**Error:** `Unable to resolve action 'anchore/grype@latest', unable to find version 'latest'`

**Root cause:** GitHub Actions cannot find a version/tag named `latest` on the `anchore/grype` repository. The `anchore/grype` repo publishes version tags like `v0.111.0`, `v0.110.0`, etc., but no `latest` tag for the action ref.

**Note:** The canonical reference in the context file (`anchore/grype-action`) does not exist as a separate GitHub repository. The actual action lives at `anchore/grype` and is Docker-based.

## User Constraint (from CONTEXT.md)

- **Version pin:** `@main` (user selected)

## Recommended Fix

**File:** `.github/workflows/lint.yml` line 16

```yaml
# Before
uses: anchore/grype@latest

# After (user-selected)
uses: anchore/grype@main
```

## Version Pin Options

| Ref | Valid | Notes |
|-----|-------|-------|
| `@main` | Yes | Tracks latest commit on main — user-selected |
| `@v0.111.0` | Yes | Latest release tag — most stable |
| `@sha-xxxxxxx` | Yes | Specific commit — most reproducible |
| `@latest` | No | No `latest` tag exists for this action |

**Most stable alternative:** `@v0.111.0` (current latest release per `curl api.github.com/repos/anchore/grype/tags`)

## Common Pitfalls with GitHub Actions Version Pinning

1. **`@latest` fails for Docker-based actions** — Docker container actions do not publish a `latest` tag in the GitHub Actions sense. Always use branch refs (`@main`, `@master`) or version tags (`@vX.Y.Z`).

2. **Branch vs. tag ambiguity** — `@main` resolves to the tip of `main` branch. It is mutable (non-reproducible for security scans — same commit today may differ tomorrow).

3. **Security scans need reproducibility** — For vulnerability scanning in CI, `@main` means the scanner auto-updates. Some teams prefer explicit version pins (`@v0.111.0`) to ensure reproducible scans across runs.

4. **No `@latest` for this action** — Confirmed by direct API check: `anchore/grype` has tags `v0.111.0`, `v0.110.0`, etc., but no `latest` tag.

## Architecture Pattern

**Docker-based action** (confirmed by `Dockerfile` at repo root):
- No `action.yml` at repository root
- Uses `Dockerfile` with `ENTRYPOINT` to `/grype`
- Referenced via `uses: owner/repo@ref`

## Gotchas

- The GitHub Actions error `unable to resolve action` can also mean the repository does not exist, the ref does not exist, or the action type is unsupported at that ref.
- For `anchore/grype`, the `@latest` ref simply does not exist.

## Assumptions Log

| # | Claim | Confidence | Notes |
|---|-------|------------|-------|
| A1 | `anchore/grype-action` repo does not exist | HIGH | 404 on API and raw content |
| A2 | `anchore/grype` is the correct action repo | MEDIUM | All marketplace references point to `anchore/grype` |
| A3 | `@main` is valid for this action | MEDIUM | Standard GitHub Actions branch ref, not verified by action.yml existence |

## Sources

- `curl -s api.github.com/repos/anchore/grype/tags` — confirmed version tags
- `curl -s raw.githubusercontent.com/anchore/grype/main/Dockerfile` — confirmed Docker-based action
- User decision in `260410-fju-CONTEXT.md` — `@main` selected

## Validation

No test infrastructure changes needed — this is a single-line fix to an existing workflow file.

---

**Research complete. Planner can now produce a PLAN.md or proceed directly to fix.**
