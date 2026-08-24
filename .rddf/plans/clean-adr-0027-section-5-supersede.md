# clean-adr-0027-section-5-supersede Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** Clean up 4 documentation drifts in ADR-0027 per Oracle audit: (1) §5 Triage lacks supersession note → ADR-0029 replaces it; (2) §4 normalize_for_hash location wrong (now `_lib/issue_dedup.py`); (3) §3/§6/§8 promise G6 artifacts that aren't implemented; (4) §1.1 category list missing `phase-interrupted`. Plus update cross-references in `improvement-check-mechanisms.md` and `docs/adr/README.md`.

**Architecture:** Pure documentation edits to `docs/adr/ADR-0027-*.md` (if exists, otherwise create or modify latest), `docs/adr/README.md`, `docs/architecture/improvement-check-mechanisms.md`. No code changes.

**Tech Stack:** markdown editing only

---

## File Structure

### Documentation

| File | Responsibility |
|---|---|
| `docs/adr/ADR-0027-*.md` | Add supersession note (§5); correct normalize_for_hash location (§4); remove G6 artifact promises (§3/§6/§8); expand §1.1 category list |
| `docs/adr/README.md` | Add "§5 superseded by ADR-0029" footnote on ADR-0027 row |
| `docs/architecture/improvement-check-mechanisms.md` | Update cross-references to PR-6 |

### Tests

None (pure docs change per proposal AC §"测试").

---

### Task 1: Locate the latest ADR-0027 file

**Files:**
- Read: `docs/adr/` directory

- [ ] **Step 1: Find ADR-0027 file(s)**

Run: `ls docs/adr/ | grep -i "0027"`
Find the latest ADR-0027 file (may be ADR-0027.md, ADR-0027-section-X.md, etc.)

- [ ] **Step 2: Read the file to understand current structure**

Use `read` to load the file. Identify §1.1 (category list), §3 (default config), §4 (normalize_for_hash), §5 (Triage), §6 (schema), §8 (closing ring).

- [ ] **Step 3: Defer commit**

---

### Task 2: Apply 5 doc edits to ADR-0027

**Files:**
- Modify: `docs/adr/ADR-0027-*.md` (the latest ADR-0027 file)

- [ ] **Step 1: AC-1 — Add supersession note at end of §5 (Triage)**

Append at end of §5:

```markdown

> **§5 Supersession Note (2026-08-24)**: The Triage design described in §5 has been superseded by ADR-0029 (Issue-Driven Proposal Creation). The current triage path is documented in ADR-0029; §5 is preserved as design history only.
```

- [ ] **Step 2: AC-2 — Correct normalize_for_hash location in §4**

Find the text mentioning `normalize_for_hash` in `issue_reporter.py` (or similar). Change to:

```markdown
...implemented in `_lib/issue_dedup.py::compute_dedup_hash`...
```

- [ ] **Step 3: AC-3 — Remove G6 artifact promises from §3/§6/§8**

Find any mentions of:
- `.issue-reporter.json` state file → remove or note as "removed"
- `.reporting-config.json` config cache → remove or note as "removed"
- 一次性 banner → remove
- `issue_reporter_schema.json` → replace with: `配套 schema 改为依赖现有 _lib/schemas/config_schema.json 的 reporting namespace;issue_reporter 不再单独维护 schema`

Use `Edit` tool with precise oldString/newString for each removal.

- [ ] **Step 4: AC-4 — Remove `retention_days` from §3 default config example**

Find the YAML example in §3 (default config). Remove `retention_days: 30` line. Add comment:

```yaml
# retention_days 因 prunable code path 不可达,本 ADR 已删除承诺
```

- [ ] **Step 5: AC-5 — Expand §1.1 category list to 5 categories**

Find §1.1 (category list). Change from 4 categories to 5:

```markdown
- `flow-bug` — runtime bug discovered at execution time
- `gate-failure` — gate raised during evaluation
- `phase-crash` — phase exited with non-zero + traceback in `_lib/`
- `manual` — user manually reported via `rddf report-issue`
- `phase-interrupted` — orchestrator-interrupted phase (e.g., Ctrl-C during `guide-plan`)
```

- [ ] **Step 6: Verify 5 edits applied**

Run: `grep -n "superseded by ADR-0029" docs/adr/ADR-0027-*.md` (should match)
Run: `grep -n "compute_dedup_hash" docs/adr/ADR-0027-*.md` (should match)
Run: `grep -n "phase-interrupted" docs/adr/ADR-0027-*.md` (should match)
Run: `grep -n "retention_days" docs/adr/ADR-0027-*.md` (should NOT match — removed)

- [ ] **Step 7: Defer commit**

---

### Task 3: Update cross-references

**Files:**
- Modify: `docs/adr/README.md`
- Modify: `docs/architecture/improvement-check-mechanisms.md`

- [ ] **Step 1: AC-7 — Add supersession footnote to ADR-0027 row in `docs/adr/README.md`**

Find the row for ADR-0027 in the README table. Add a footnote marker and a footnotes section entry:

```markdown
...existing ADR-0027 row text... [^adr-0027-supersede]
```

Add at bottom:

```markdown
[^adr-0027-supersede]: §5 Triage superseded by ADR-0029 (2026-08-24); see clean-adr-0027-section-5-supersede proposal
```

- [ ] **Step 2: AC-6 — Update `improvement-check-mechanisms.md` cross-references**

Find any references to:
- `.issue-reporter.json` → add note "removed in PR-6"
- `retention_days` → add note "removed in PR-6"
- `issue_reporter_schema.json` → add note "removed in PR-6"
- PR-3 (issue-file-frontmatter) → add link to PR-6 for consistency

Use `Edit` tool for each.

- [ ] **Step 3: Defer commit**

---

### Task 4: Verify no code changes

- [ ] **Step 1: Check git diff is docs-only**

Run: `cd $WT_PATH && git status --short`
Expected: only `docs/adr/*.md`, `docs/adr/README.md`, `docs/architecture/improvement-check-mechanisms.md`, and `.rddf/plans/clean-adr-0027-section-5-supersede.md` + `openspec/changes/clean-adr-0027-section-5-supersede/tasks.md`.

NO files in `_lib/`, `skills/`, `tests/` should be changed.

- [ ] **Step 2: Defer commit**

---

### Task 5: Update `tasks.md` and stage for archive

- [ ] **Step 1: Mark all `- [ ]` as `- [x]` in `openspec/changes/clean-adr-0027-section-5-supersede/tasks.md`**

Leave CHANGELOG / commit `[ ]`.

- [ ] **Step 2: Stage all changes**

```bash
cd $WT_PATH && git add docs/adr/ADR-0027*.md docs/adr/README.md \
  docs/architecture/improvement-check-mechanisms.md \
  openspec/changes/clean-adr-0027-section-5-supersede/tasks.md \
  .rddf/plans/clean-adr-0027-section-5-supersede.md
git status --short
```

- [ ] **Step 3: Defer commit (orchestrator owns worktree commit)**

---

## Acceptance Verification

- [ ] AC-1: §5 has supersession note linking ADR-0029
- [ ] AC-2: §4 says normalize_for_hash is in `_lib/issue_dedup.py`
- [ ] AC-3: §3/§6/§8 no longer promise G6 artifacts
- [ ] AC-4: `retention_days` removed from §3 config example
- [ ] AC-5: §1.1 has 5 categories including `phase-interrupted`
- [ ] AC-6: `improvement-check-mechanisms.md` cross-refs updated
- [ ] AC-7: `docs/adr/README.md` ADR-0027 row has supersession footnote
- [ ] `openspec validate clean-adr-0027-section-5-supersede` → valid
- [ ] No code files changed (docs only)

## Out of Scope (DO NOT IMPLEMENT)

- ❌ Rewrite ADR-0027 entire text (only targeted edits)
- ❌ Create ADR-0029 (already exists)
- ❌ Implement G6 artifacts (decision: do NOT implement)
- ❌ Modify `_classify_interrupted_phase` implementation
- ❌ Modify Oracle audit report (`ses_fcd821b6dffec9xoFJ515aq5Eo` output)
- ❌ Any code changes (`_lib/`, `skills/`, `tests/`)
- ❌ Any state file writes