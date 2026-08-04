# add-skill-registration-checklist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make new-skill registration drift fail loudly by requiring exact package registration, complete INSTALL.md coverage, dynamic metadata checks, and a five-item developer checklist.

**Architecture:** Keep `_count_skill_files()` as the single disk-count source in `test_doc_contracts.py`. Add independent assertions for exact `package.json` cardinality and the INSTALL.md sub-skill table, while converting the metadata Bats test from a hard-coded set to a disk-derived glob. Documentation remains guidance only; tests provide the CI gate.

**Tech Stack:** Python 3.11, pytest, Bash/Bats, Python `json`/`pathlib`/`re`, Markdown, package.json, and existing repository test helpers.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `docs/change-quality-guide.md` | Five-step checklist for registering a new skill across documentation, package metadata, smoke coverage, and usage guidance. |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_doc_contracts.py` | Enforce exact package skill count and INSTALL.md sub-skill table count against `_count_skill_files()`. |
| `tests/integration/test_skill_metadata_consistency.bats` | Discover all skill files dynamically and verify package registration and metadata coverage without a hard-coded skill-name list. |
| `CHANGELOG.md` | Record the stricter skill-registration contract. |

---

### Task 1: Lock exact package and INSTALL table contracts

**Files:**
- Modify: `tests/unit/test_doc_contracts.py`
- Test: `package.json`
- Test: `skills/INSTALL.md`

- [ ] **Step 1: Write the failing tests**

Add a test that asserts `len(pkg["skills"]) == disk` and reports both counts on failure. Add a separate test that extracts only skill-link rows from the INSTALL.md sub-skill table and asserts that the number of unique rows equals `_count_skill_files()`, while retaining the existing description-count test unchanged.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_doc_contracts.py -q`

Expected: The newly tightened contract fails if the current package or INSTALL.md table is behind the disk count; the failure must identify the mismatched count or missing table rows. If the repository is already aligned, temporarily remove one package skill entry in a copied fixture and run the assertion helper against that fixture to prove the exact comparison detects drift.

- [ ] **Step 3: Write the minimal implementation**

Keep `_count_skill_files()` byte-for-byte semantically unchanged: top-level `skills/*.md` plus `skills/*/SKILL.md`. Parse INSTALL.md table rows by requiring a Markdown table row containing a skill link/path, excluding headers, separators, prose, and non-skill notes. Use sets or duplicate checks so a duplicated row cannot satisfy the count accidentally, and include actionable mismatch details in assertion messages.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_doc_contracts.py -q`

Expected: All existing and new document-contract tests pass on the current repository state; a temporary package omission demonstrably fails the exact-count assertion and is restored before continuing.

- [ ] **Step 5: Commit the unit contract changes**

```bash
git add tests/unit/test_doc_contracts.py
git commit -m "test: require exact skill registration counts"
```

### Task 2: Make cross-skill Bats metadata discovery dynamic

**Files:**
- Modify: `tests/integration/test_skill_metadata_consistency.bats`
- Modify: `tests/smoke.bats`
- Test: `package.json`

- [ ] **Step 1: Write the failing test**

Add a Bats test that derives the skill-name set directly from the repository’s `skills/*.md` and `skills/*/SKILL.md` paths and asserts that every discovered name has a package entry and metadata surface. Preserve the existing special handling for INSTALL.md and writing-plans, but remove assumptions that only the original ten target names exist.

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_skill_metadata_consistency.bats`

Expected: The new dynamic assertion fails against the current hard-coded target-list implementation because a newly discovered skill is not included in the expected set or smoke extraction.

- [ ] **Step 3: Write the minimal implementation**

Replace hard-coded expected skill names with sorted names derived from `skills/*.md` and `skills/*/SKILL.md`, normalize `INSTALL.md` to `INSTALL`, and compare the discovered set with package.json entries. Keep the existing prometheus-planning removal assertion and the requirement that each package entry maps to a real file. Update smoke-facing assertions only where needed to ensure the newly discovered skill’s frontmatter is covered without duplicating the dynamic consistency logic.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `bats tests/integration/test_skill_metadata_consistency.bats tests/smoke.bats`

Expected: Dynamic discovery passes for all current skills, package entries map to files, and existing smoke/frontmatter checks remain green.

- [ ] **Step 5: Commit the dynamic metadata tests**

```bash
git add tests/integration/test_skill_metadata_consistency.bats tests/smoke.bats
git commit -m "test: discover registered skills dynamically"
```

### Task 3: Add the developer registration checklist

**Files:**
- Modify: `docs/change-quality-guide.md`
- Modify: `CHANGELOG.md`
- Test: `tests/unit/test_doc_contracts.py`

- [ ] **Step 1: Write the failing test**

Add a focused assertion that `docs/change-quality-guide.md` contains a clearly named new-skill registration section with five `- [ ]` items covering: INSTALL.md count, INSTALL.md table, package.json skills array, smoke.bats frontmatter, and USAGE.md. Assert each item is present by its required surface name, not only by total checklist length.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_doc_contracts.py -q`

Expected: The checklist assertion fails because the current guide contains no new-skill registration section.

- [ ] **Step 3: Write the minimal implementation**

Add a concise section to docs/change-quality-guide.md with the five ordered, checkable registration actions and commands/locations for each. Clarify that the checklist guides developers while automated tests enforce exact counts and dynamic metadata coverage; do not add scaffolding or hooks. Add one changelog entry.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_doc_contracts.py -q`

Expected: The checklist assertion and all document-contract tests pass, including the exact package and INSTALL table checks.

- [ ] **Step 5: Commit the checklist documentation**

```bash
git add docs/change-quality-guide.md CHANGELOG.md tests/unit/test_doc_contracts.py
git commit -m "docs: add new skill registration checklist"
```

### Task 4: Run change validation and full regression

**Files:**
- Verify: `openspec/changes/add-skill-registration-checklist/proposal.md`
- Verify: `openspec/changes/add-skill-registration-checklist/design.md`
- Verify: `openspec/changes/add-skill-registration-checklist/tasks.md`
- Verify: `tests/unit/test_doc_contracts.py`
- Verify: `tests/integration/test_skill_metadata_consistency.bats`

- [ ] **Step 1: Write the failing verification command**

Run the focused unit and Bats commands from the prior tasks together, then run `openspec validate add-skill-registration-checklist --json` to expose any artifact or contract issue before handoff.

- [ ] **Step 2: Run tests to verify the baseline**

Run: `python3 -m pytest tests/unit/test_doc_contracts.py -q` and `bats tests/integration/test_skill_metadata_consistency.bats`.

Expected: The exact-count assertion and table-count assertion fail against the pre-change implementation when its package/table data is behind the disk count; the dynamic Bats test also exercises the currently hard-coded target list and exposes any discovered skill outside that list. If the current checkout already satisfies one assertion, preserve the test and use the negative mutation check in Step 3 to prove that omission is rejected.

- [ ] **Step 3: Complete the minimal verification**

Run: `openspec validate add-skill-registration-checklist --json`; then run `npm test` and `python3 -m pytest tests/unit/ tests/integration/ -q --tb=short`. Do not change unrelated tests or relax assertions to accommodate pre-existing failures.

- [ ] **Step 4: Confirm the acceptance criteria**

Expected: package.json count equals disk count, INSTALL.md description and table agree with disk, dynamic metadata tests pass, the five checklist items are present, and the full suite has no regression attributable to this change. Record any repository-pre-existing failure separately from this change.

- [ ] **Step 5: Commit the final verification/documentation update**

```bash
git add docs/change-quality-guide.md CHANGELOG.md tests/unit/test_doc_contracts.py tests/integration/test_skill_metadata_consistency.bats tests/smoke.bats
git commit -m "test: enforce complete skill registration contract"
```
