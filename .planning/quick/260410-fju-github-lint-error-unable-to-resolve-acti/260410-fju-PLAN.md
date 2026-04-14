---
phase: quick-260410-fju
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .github/workflows/lint.yml
autonomous: true
requirements:
  - QTFJU-01
must_haves:
  truths:
    - "GitHub Actions can resolve the anchore/grype action reference"
    - "The lint workflow step uses the correct action ref (per D-01: @main)"
  artifacts:
    - path: ".github/workflows/lint.yml"
      provides: "Lint workflow with valid grype action reference"
      contains: "anchore/grype@main"
  key_links:
    - from: ".github/workflows/lint.yml"
      to: "anchore/grype@main"
      via: "uses field on line 16"
      pattern: "anchore/grype@main"
---

<objective>
Fix GitHub Actions lint workflow error by changing the anchore/grype action reference from @latest (which cannot be resolved) to @main (per user decision D-01).
</objective>

<execution_context>
@/Users/y3/feedship/.github/workflows/lint.yml
</execution_context>

<context>
User decision D-01 (locked): Use @main for anchore/grype action reference.

Research finding: anchore/grype is a Docker-based action that does not publish a `latest` tag. GitHub Actions cannot resolve `@latest` for this action. @main is a valid branch ref that resolves correctly.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Change anchore/grype@latest to anchore/grype@main in lint.yml</name>
  <files>.github/workflows/lint.yml</files>
  <action>
    Edit line 16 of .github/workflows/lint.yml:
    - Change: `uses: anchore/grype@latest`
    - To: `uses: anchore/grype@main`

    This fixes the "Unable to resolve action" error by using a valid GitHub Actions ref (branch @main) instead of the non-existent @latest tag.
  </action>
  <verify>
    <automated>grep -n "anchore/grype@" .github/workflows/lint.yml | grep -v "@main"</automated>
    <manual>Verify line 16 shows `anchore/grype@main`</manual>
  </verify>
  <done>Line 16 of .github/workflows/lint.yml reads `uses: anchore/grype@main`</done>
</task>

</tasks>

<verification>
Grep for `@latest` references to grype — should return no matches in lint.yml.
</verification>

<success_criteria>
- Line 16 of .github/workflows/lint.yml changed from `anchore/grype@latest` to `anchore/grype@main`
- No `@latest` references to anchore/grype remain in lint.yml
</success_criteria>

<output>
After completion, update the quick task directory status and commit the change.
</output>
