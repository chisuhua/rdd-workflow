# Fix doc-truth-sync — Design

## Current State

### 1. The Problem

`doc_truth_sync` test #1 (`package.json::skills[] publishes all 13 disk skills`) fails because:

```
disk skills: 16
package.json skills[]: 13
difference: -3
```

The three missing skills are:

| Skill | Disk path | In package.json? |
|-------|-----------|-----------------|
| `add-improve` | `skills/add-improve/SKILL.md` | ❌ |
| `openspec-gate` | `skills/openspec-gate/SKILL.md` | ❌ |
| `rdd-workflow-brainstorm` | `skills/rdd-workflow-brainstorm/SKILL.md` | ❌ |

### 2. Naming Consistency Check

The improvement doc originally flagged `rdd-workflow-writing-plans` vs `rdd-workflow/writing-plans` inconsistency. This was already fixed in commit `4652856` (frontmatter name changed from `rdd-workflow/writing-plans` to `rdd-workflow-writing-plans`). Current state:

| Location | Value | Status |
|----------|-------|--------|
| `package.json skills[]` | `rdd-workflow-writing-plans` | ✅ |
| `skills/rdd-workflow-writing-plans/SKILL.md` frontmatter `name:` | `rdd-workflow-writing-plans` | ✅ |
| `AGENTS.md` tree listing | `rdd-workflow-writing-plans/SKILL.md` | ✅ |

No remaining naming inconsistency — the real issue is three missing skills.

### 3. Other Tests

All other `doc_truth_sync` tests (#2 through #8) pass:
- #2: AGENTS.md mentions 13 skills ✅
- #3: AGENTS.md ADR table ✅
- #4: INSTALL.md description ✅
- #5: README.md directory tree ✅
- #6: USAGE.md changelog banner ✅
- #7: USAGE.md state-file table ✅
- #8: AGENTS.md forbids undotted legacy path ✅

## Design Decision

**Add the three missing skills to `package.json skills[]` array.**

The `skills[]` array in `package.json` serves as the manifest of published skills. When a skill is added to disk, it must also be registered in this array. The three missing skills were added to disk at some point but the manifest was not updated.

### Files to modify

| File | Change |
|------|--------|
| `package.json` | Add `add-improve`, `openspec-gate`, `rdd-workflow-brainstorm` to `skills[]` |

### Files NOT to modify

- `tests/integration/test_doc_contracts.bats` — the test is correct; it should pass after the fix
- `tests/smoke.bats` — the `v1.x baseline skills` test only checks 10 skills, not the full set; `GitHub`the `all skill files exist` test is dynamic (globs disk) — no change needed
- Any skill files — no functional changes
- `AGENTS.md`, `README.md`, `INSTALL.md` — these already reference the 3 skills

## Verification

After the fix, `doc_truth_sync` test #1 should pass:
```bash
bats tests/integration/test_doc_contracts.bats
# Expected: 1..8, all ok
```

Additionally, run full smoke and metadata consistency tests:
```bash
bats tests/smoke.bats
bats tests/integration/test_skill_metadata_consistency.bats
```