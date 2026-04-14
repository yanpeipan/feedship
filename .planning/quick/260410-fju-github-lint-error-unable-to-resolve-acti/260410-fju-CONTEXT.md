# Quick Task 260410-fju: github lint Error: Unable to resolve action `anchore/grype@latest`, unable to find version `latest` - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Task Boundary

Fix GitHub Actions lint workflow error: `anchore/grype@latest` cannot resolve version `latest`. The action reference in `.github/workflows/lint.yml` line 16 needs to be updated to a valid GitHub Actions ref.

</domain>

<decisions>
## Implementation Decisions

### Version Pin for anchore/grype
- User selected: @main (Recommended) — use @main to track latest commits

### Claude's Discretion
All other decisions delegated to standard approaches.

</decisions>

<specifics>
## Specific Ideas

- File: `.github/workflows/lint.yml` line 16
- Current: `uses: anchore/grype@latest`
- Fix: Change to `uses: anchore/grype@main`

</specifics>

<canonical_refs>
## Canonical References

- [anchore/grype GitHub Action](https://github.com/anchore/grype-action)

</canonical_refs>
