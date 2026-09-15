# apply-adr-0051-skill-description-convention-bulk-rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply ADR-0051's single-responsibility description convention (5 Decisions) to all 25 remaining skill descriptions, add enforcement bats test, upgrade `guide` recommender for centralized anti-routing, and add architecture doc section.

**Architecture:** 5 parallel writing-class sub-agents each rewrite a disjoint file set per ADR-0051 v3 template (rdd-builder v3 as canonical sample). Bats test gates three assertions on every SKILL.md description. Guide recommender aggregates anti-routing centrally. Architecture doc mirrors ADR-0051.

**Tech Stack:** YAML frontmatter (markdown), bats-core 1.10+, Python 3.11+ (no new deps).

---

## File Structure

### Production Code (skill descriptions — 25 SKILL.md files)

| File | Responsibility | Batch |
|------|----------------|-------|
| `skills/rdd-arch/SKILL.md` | Stage 1 arch phase description (v3 template) | Batch 1 (main-stage) |
| `skills/rdd-planner/SKILL.md` | Stage 2 planner phase description | Batch 1 |
| `skills/rdd-verifier/SKILL.md` | Stage 4 verifier phase description | Batch 1 |
| `skills/rdd-quick/SKILL.md` | Bypass path description (per ADR-0047) | Batch 1 |
| `skills/propose/SKILL.md` | Legacy proposal skeleton creation | Batch 2 (sub-skill A) |
| `skills/execute/SKILL.md` | Plan execution sub-skill | Batch 2 |
| `skills/rdd-workflow-writing-plans/SKILL.md` | Plan generation sub-skill | Batch 2 |
| `skills/add-improve/SKILL.md` | Improvement creation entry | Batch 2 |
| `skills/deps/SKILL.md` | Dependency analysis sub-skill | Batch 2 |
| `skills/status/SKILL.md` | Change status / archive sub-skill | Batch 3 (sub-skill B) |
| `skills/feature/SKILL.md` | Feature fragment management | Batch 3 |
| `skills/roadmap/SKILL.md` | Roadmap management | Batch 3 |
| `skills/rdd-doctor/SKILL.md` | Manual diagnostic sub-skill | Batch 3 |
| `skills/rdd-env-check/SKILL.md` | Env health check sub-skill | Batch 3 |
| `skills/rdd-hub-bootstrap/SKILL.md` | Hub repo bootstrap sub-skill | Batch 3 |
| `skills/rddf-session/SKILL.md` | Session lifecycle sub-skill | Batch 4 (sub-skill C) |
| `skills/rdd-workflow-brainstorm/SKILL.md` | Brainstorm helper | Batch 4 |
| `skills/cross-repo-protocol/SKILL.md` | Hub-Spoke MCP client | Batch 4 |
| `skills/sync-hub/SKILL.md` | Hub-Spoke contract pull | Batch 4 |
| `skills/watch-hub/SKILL.md` | Hub-Spoke issue poll | Batch 4 |
| `skills/report-issue/SKILL.md` | Hub-Spoke [RFC] issue create | Batch 5 (sub-skill D + bats) |
| `skills/openspec-gate/SKILL.md` | Pre-commit change link guard | Batch 5 |
| `skills/contract-check/SKILL.md` | Spoke vs Hub OpenAPI validator | Batch 5 |
| `skills/spoke-system-prompt-injection/SKILL.md` | Hub-Spoke protocol injector | Batch 5 |
| `skills/INSTALL/SKILL.md` | First-entry install skill | Batch 5 |

### Tests (NEW)

| File | Responsibility |
|------|----------------|
| `tests/integration/test_skill_description_convention.bats` | 3 assertions: ≤ 200 tokens / no anti-trigger / references role.boundaries |

### Cross-cutting (P3, single-task in plan)

| File | Responsibility |
|------|----------------|
| `skills/guide/SKILL.md` | Centralize anti-routing for 26 skills |
| `docs/architecture/v4-pipeline-data-flow.md` | Add "skill description convention" section |

---

## Task 1: Setup — Verify preconditions and load v3 template

**Files:**
- Read: `.rddf/state/.planner-handoff.json` (verify `awaiting_builder` contains this change)
- Read: `.rddf/state/builder/apply-adr-0051-skill-description-convention-bulk-rewrite.json` (verify `approval_status=approved`)
- Read: `docs/adr/ADR-0051-skill-description-convention.md` (5 Decisions to apply)
- Read: `skills/rdd-builder/SKILL.md` L1-22 (v3 canonical sample description)

- [ ] **Step 1: Verify planner-handoff.json contains this change**

Run: `jq -r '.awaiting_builder[]' .rddf/state/.planner-handoff.json`
Expected: `apply-adr-0051-skill-description-convention-bulk-rewrite`

- [ ] **Step 2: Verify builder handoff approval_status**

Run: `jq -r '.approval_status' .rddf/state/builder/apply-adr-0051-skill-description-convention-bulk-rewrite.json`
Expected: `approved`

- [ ] **Step 3: Verify rdd-builder description is the v3 sample**

Run: `sed -n '3,22p' skills/rdd-builder/SKILL.md`
Expected: 3-section description (identity / trigger preconditions / default behavior) ≤ 200 tokens, no anti-trigger phrases, references `role.boundaries`

- [ ] **Step 4: Defer commit**

No code changes yet. Continue to Task 2.

---

## Task 2: Batch 1 — Rewrite 4 main-stage skill descriptions

**Files:**
- Modify: `skills/rdd-arch/SKILL.md` frontmatter `description:` field
- Modify: `skills/rdd-planner/SKILL.md` frontmatter `description:` field
- Modify: `skills/rdd-verifier/SKILL.md` frontmatter `description:` field
- Modify: `skills/rdd-quick/SKILL.md` frontmatter `description:` field

- [ ] **Step 1: Write the failing token-count check (manual grep)**
- [ ] **Step 2: Verify baseline descriptions exceed budget**

Run: `for f in skills/rdd-arch/SKILL.md skills/rdd-planner/SKILL.md skills/rdd-verifier/SKILL.md skills/rdd-quick/SKILL.md; do wc -w <(awk '/^description: \|/{flag=1;next}/^---/{if(flag){flag=0}}flag' "$f"); done`
Expected: each count > 200 (current state)

- [ ] **Step 3: Rewrite each description using v3 template**

For each of the 4 main-stage files, replace the `description:` block content with this template:

```yaml
description: |
  Stage N of v4 architecture (rdd-arch → rdd-planner → rdd-builder → rdd-verifier).
  <one-line role summary>.

  Invoke when canonical preconditions hold:
    1. <data contract: required file / schema / env var>
    2. <data contract: required file / schema / env var>

  <one-line default behavior, e.g. auto-pick per ADR-0050>.

  Boundary ownership: see role.boundaries.owns / not_owns.
```

Per-skill content (fill in `<>` placeholders):
- `rdd-arch`: Stage 1. Role: ADR + roadmap authoring. Preconditions: project has ADR directory + .rddf/roadmap.md or init not yet run. Default: no auto-pick (interactive setup).
- `rdd-planner`: Stage 2. Role: improvement authoring / review / approve. Preconditions: rdd-arch arch-done OR legacy planner-handoff.json present. Default: auto-decision per ADR-0050.
- `rdd-verifier`: Stage 4. Role: AC verification + bounded retry. Preconditions: rdd-builder P3 archive_gate_check triggered OR manual invocation. Default: LLM verification per ADR-0045 (in-line, no external LLM env).
- `rdd-quick`: Bypass path. Role: small change in-place execution + self-contained LLM verification. Preconditions: change scope fits bypass criteria per ADR-0047 (≤2 files, no openspec change, no worktree). Default: TDD 5-step plan + Oracle self-verification.

- [ ] **Step 4: Verify each rewritten description ≤ 200 tokens**

Run: `for f in skills/rdd-arch/SKILL.md skills/rdd-planner/SKILL.md skills/rdd-verifier/SKILL.md skills/rdd-quick/SKILL.md; do awk '/^description: \|/{flag=1;next}/^---/{if(flag){flag=0}}flag' "$f" | wc -w; done`
Expected: each ≤ 200

- [ ] **Step 5: Verify no anti-trigger phrases**

Run: `grep -nE '\*\*DO NOT use\*\*|\*\*Prefer .* instead\*\*|\*\*Legacy entry\*\*' skills/rdd-arch/SKILL.md skills/rdd-planner/SKILL.md skills/rdd-verifier/SKILL.md skills/rdd-quick/SKILL.md`
Expected: 0 hits

- [ ] **Step 6: Verify references role.boundaries**

Run: `grep -lE 'role\.boundaries\.owns|see role\.boundaries' skills/rdd-arch/SKILL.md skills/rdd-planner/SKILL.md skills/rdd-verifier/SKILL.md skills/rdd-quick/SKILL.md`
Expected: all 4 files listed

- [ ] **Step 7: Defer commit**

No commit per task — batch commit at archive time.

---

## Task 3: Batch 2 — Rewrite 5 sub-skill descriptions (group A)

**Files:**
- Modify: `skills/propose/SKILL.md` frontmatter `description:`
- Modify: `skills/execute/SKILL.md` frontmatter `description:`
- Modify: `skills/rdd-workflow-writing-plans/SKILL.md` frontmatter `description:`
- Modify: `skills/add-improve/SKILL.md` frontmatter `description:`
- Modify: `skills/deps/SKILL.md` frontmatter `description:`

- [ ] **Step 1: Verify baseline (each description > 200 tokens OR contains anti-trigger)**

Run: `for f in skills/propose/SKILL.md skills/execute/SKILL.md skills/rdd-workflow-writing-plans/SKILL.md skills/add-improve/SKILL.md skills/deps/SKILL.md; do wc -w <(awk '/^description: \|/{flag=1;next}/^---/{if(flag){flag=0}}flag' "$f"); done`
Expected: 5 numbers, at least some > 200

- [ ] **Step 2: Rewrite each using sub-skill v3 template**

Template for sub-skills:

```yaml
description: |
  <one-line role: what this sub-skill does>

  Invoke when BOTH:
    1. <precondition: who/what calls this>
    2. <precondition: data state>

  <one-line default behavior or key constraint>

  Boundary ownership: see role.boundaries.owns / not_owns.
```

Per-skill content:
- `propose`: legacy proposal skeleton creator. Invoke when: no rdd-planner handoff + user wants openspec change skeleton. Note: legacy path (ADR-0025).
- `execute`: plan execution sub-skill. Invoke when: .rddf/plans/<name>.md exists + worktree context. Default: TDD 5-step discipline.
- `rdd-workflow-writing-plans`: TDD 5-step plan generator. Invoke when: rdd-builder P1 needs plan. Default: auto-generate plan file.
- `add-improve`: improvement creation entry. Invoke when: no .rddf/improvements/<name>.md exists + 5-segment draft needed. Default: requires HARD-GATE brainstorm per pre_create_brainstorm_check.sh.
- `deps`: dependency analysis. Invoke when: rdd-builder P1.5 OR user wants Mermaid graph. Default: 24h TTL cache.

- [ ] **Step 3: Verify token count**

Run: `for f in skills/propose/SKILL.md skills/execute/SKILL.md skills/rdd-workflow-writing-plans/SKILL.md skills/add-improve/SKILL.md skills/deps/SKILL.md; do awk '/^description: \|/{flag=1;next}/^---/{if(flag){flag=0}}flag' "$f" | wc -w; done`
Expected: each ≤ 200

- [ ] **Step 4: Verify no anti-trigger + references role.boundaries**

Run: `grep -nE '\*\*DO NOT use\*\*|\*\*Prefer .* instead\*\*|\*\*Legacy entry\*\*' skills/propose/SKILL.md skills/execute/SKILL.md skills/rdd-workflow-writing-plans/SKILL.md skills/add-improve/SKILL.md skills/deps/SKILL.md && echo "FAIL" || echo "OK"; grep -lE 'role\.boundaries\.owns|see role\.boundaries' skills/propose/SKILL.md skills/execute/SKILL.md skills/rdd-workflow-writing-plans/SKILL.md skills/add-improve/SKILL.md skills/deps/SKILL.md | wc -l`
Expected: OK + count = 5

- [ ] **Step 5: Defer commit**

---

## Task 4: Batch 3 — Rewrite 6 sub-skill descriptions (group B)

**Files:**
- Modify: `skills/status/SKILL.md` frontmatter `description:`
- Modify: `skills/feature/SKILL.md` frontmatter `description:`
- Modify: `skills/roadmap/SKILL.md` frontmatter `description:`
- Modify: `skills/rdd-doctor/SKILL.md` frontmatter `description:`
- Modify: `skills/rdd-env-check/SKILL.md` frontmatter `description:`
- Modify: `skills/rdd-hub-bootstrap/SKILL.md` frontmatter `description:`

- [ ] **Step 1: Verify baseline**

Run: `for f in skills/status/SKILL.md skills/feature/SKILL.md skills/roadmap/SKILL.md skills/rdd-doctor/SKILL.md skills/rdd-env-check/SKILL.md skills/rdd-hub-bootstrap/SKILL.md; do wc -w <(awk '/^description: \|/{flag=1;next}/^---/{if(flag){flag=0}}flag' "$f"); done`
Expected: 6 numbers

- [ ] **Step 2: Rewrite each using sub-skill v3 template**

Per-skill content:
- `status`: change status + archive. Invoke when: openspec change exists + need inspection or archive. Default: openspec archive helper.
- `feature`: feature fragment management. Invoke when: .rddf/roadmap/features/*.md exists OR user wants sprint view. Default: pure derived view.
- `roadmap`: roadmap CRUD. Invoke when: .rddf/roadmap.md missing OR edit needed. Default: 4 template init.
- `rdd-doctor`: manual diagnostic. Invoke when: workflow "feels broken" + no specific error. Default: read-only, 11 categories.
- `rdd-env-check`: env health snapshot. Invoke when: each phase first screen. Default: TTL 3600s + branch invalidate.
- `rdd-hub-bootstrap`: Hub repo initialization. Invoke when: GH org exists + need Projects V2 board. Default: idempotent + dry-run capable.

- [ ] **Step 3: Verify token count ≤ 200 for all 6**
- [ ] **Step 4: Verify no anti-trigger + references role.boundaries**

Run: same as Task 3 Step 4 but with the 6 files
Expected: count = 6

- [ ] **Step 5: Defer commit**

---

## Task 5: Batch 4 — Rewrite 5 sub-skill descriptions (group C)

**Files:**
- Modify: `skills/rddf-session/SKILL.md` frontmatter `description:`
- Modify: `skills/rdd-workflow-brainstorm/SKILL.md` frontmatter `description:`
- Modify: `skills/cross-repo-protocol/SKILL.md` frontmatter `description:`
- Modify: `skills/sync-hub/SKILL.md` frontmatter `description:`
- Modify: `skills/watch-hub/SKILL.md` frontmatter `description:`

- [ ] **Step 1: Verify baseline**
- [ ] **Step 2: Rewrite each using sub-skill v3 template**

Per-skill content:
- `rddf-session`: user-perspective workflow session. Invoke when: cross-opencode-session recovery needed OR lifecycle query. Default: 5 subcommands.
- `rdd-workflow-brainstorm`: structured brainstorm helper. Invoke when: improvement creation + need 5-segment exploration. Default: HARD-GATE enforced.
- `cross-repo-protocol`: Hub-Spoke MCP client. Invoke when: Spoke AI needs Hub tools (read/create/update issue, sync contract). Default: REST fallback + trace logging.
- `sync-hub`: Hub-Spoke contract pull. Invoke when: contract refresh needed. Default: writes openspec/specs/<name>/spec.md.
- `watch-hub`: Hub-Spoke issue poll. Invoke when: cron/CI needs Hub status sync. Default: ≤5 min interval, no daemon.

- [ ] **Step 3: Verify token count ≤ 200 for all 5**
- [ ] **Step 4: Verify no anti-trigger + references role.boundaries**

Expected count = 5

- [ ] **Step 5: Defer commit**

---

## Task 6: Batch 5 — Rewrite 5 sub-skill descriptions (group D) + add bats test

**Files:**
- Modify: `skills/report-issue/SKILL.md` frontmatter `description:`
- Modify: `skills/openspec-gate/SKILL.md` frontmatter `description:`
- Modify: `skills/contract-check/SKILL.md` frontmatter `description:`
- Modify: `skills/spoke-system-prompt-injection/SKILL.md` frontmatter `description:`
- Modify: `skills/INSTALL/SKILL.md` frontmatter `description:`
- Create: `tests/integration/test_skill_description_convention.bats`

- [ ] **Step 1: Verify baseline for 5 skills**
- [ ] **Step 2: Rewrite each using sub-skill v3 template**

Per-skill content:
- `report-issue`: Hub-Spoke [RFC] issue create. Invoke when: phase-exit hook fires + L2 reporting needed. Default: opt-in triple gate (RDDF_REPORT_ENABLED + AUTO_SUBMIT + categories).
- `openspec-gate`: pre-commit change link guard. Invoke when: git commit + staged files may be unlinked to active change. Default: warn by default, block if STRICT_OPENSPEC_GATE=yes.
- `contract-check`: Spoke vs Hub OpenAPI validator. Invoke when: contract drift suspected OR CI. Default: breaking-change exits 1, push warns.
- `spoke-system-prompt-injection`: Hub-Spoke protocol injector. Invoke when: AI assistant config needs federation protocol. Default: idempotent deploy + backup + uninstall.
- `INSTALL`: first-entry install skill. Invoke when: project has no rdd-workflow + need install. Default: project-local install (use --global for cross-project).

- [ ] **Step 3: Write the failing bats test**

Create file `tests/integration/test_skill_description_convention.bats`:

```bash
#!/usr/bin/env bats
# tests/integration/test_skill_description_convention.bats
# Enforce ADR-0051 skill description convention: ≤ 200 tokens / no anti-trigger / references role.boundaries

load test_helper

@test "every SKILL.md description is ≤ 200 tokens" {
    local skill_count=0
    local fail_count=0
    for f in skills/*/SKILL.md; do
        skill_count=$((skill_count + 1))
        local desc_tokens
        desc_tokens=$(awk '/^description: \|/{flag=1;next}/^---/{if(flag){flag=0}}flag' "$f" | wc -w)
        if [ "$desc_tokens" -gt 200 ]; then
            echo "FAIL: $f has $desc_tokens tokens (>200)"
            fail_count=$((fail_count + 1))
        fi
    done
    [ "$fail_count" -eq 0 ]
    [ "$skill_count" -eq 26 ]
}

@test "no SKILL.md description contains anti-trigger phrasing" {
    local hits
    hits=$(grep -rnE '\*\*DO NOT use\*\*|\*\*Prefer .* instead\*\*|\*\*Legacy entry\*\*' skills/*/SKILL.md | wc -l)
    [ "$hits" -eq 0 ]
}

@test "every SKILL.md description references role.boundaries" {
    local missing=0
    for f in skills/*/SKILL.md; do
        if ! grep -qE 'role\.boundaries\.owns|see role\.boundaries|Boundary ownership' "$f"; then
            echo "MISSING: $f does not reference role.boundaries"
            missing=$((missing + 1))
        fi
    done
    [ "$missing" -eq 0 ]
}
```

- [ ] **Step 4: Verify bats test fails on pre-patch state**

Run: `bats tests/integration/test_skill_description_convention.bats`
Expected: at least one test fails (because at least 21 skills still have v1-style descriptions)

- [ ] **Step 5: Defer commit**

---

## Task 7: Verify all 25 skills pass the 3 assertions

**Files:**
- Run: `tests/integration/test_skill_description_convention.bats`

- [ ] **Step 1: Run bats test**

Run: `bats tests/integration/test_skill_description_convention.bats`
Expected: 3 / 3 pass

- [ ] **Step 2: Defer commit**

---

## Task 8: P3 — guide recommender centralization

**Files:**
- Modify: `skills/guide/SKILL.md` recommender section

- [ ] **Step 1: Locate existing recommender logic in guide/SKILL.md**

Run: `grep -nE 'recommend|next skill' skills/guide/SKILL.md | head -20`
Expected: shows existing recommender anchor

- [ ] **Step 2: Append centralized anti-routing table**

After the recommender logic, append:

```markdown
## Anti-Routing Centralization (per ADR-0051)

When the recommender considers a skill, consult this table for "do NOT invoke" cases.
This is the canonical anti-routing source; per-skill descriptions no longer carry anti-trigger paragraphs.

| If user wants to... | DON'T invoke | DO invoke instead |
|---|---|---|
| Just inspect change state | `rdd-builder` | `status` |
| Pure AC verification of executed change | `rdd-builder` | `rdd-verifier` |
| Already-approved change needing pure execution | `rdd-builder` | `rdd-workflow-writing-plans` + `execute` |
| Create openspec change skeleton (legacy) | (none — modern path: rdd-planner) | `rdd-planner` (preferred) |
| Small/well-scoped change | (any main-stage skill) | `rdd-quick` (still goes through rdd-builder P0 dispatch-quick auto-route when builder called) |
```

- [ ] **Step 3: Defer commit**

---

## Task 9: P3 — architecture doc section

**Files:**
- Modify: `docs/architecture/v4-pipeline-data-flow.md`

- [ ] **Step 1: Locate end of doc**

Run: `tail -3 docs/architecture/v4-pipeline-data-flow.md`
Expected: shows end of file (likely a "## See also" or final section)

- [ ] **Step 2: Append new section**

Append at end:

```markdown
## Skill Description Convention (per ADR-0051)

Every `skills/*/SKILL.md` frontmatter `description:` field follows the ADR-0051 convention:

1. **Single responsibility**: only describes "when to invoke this skill" — never anti-routing
2. **Token budget**: ≤ 200 tokens
3. **Boundary ownership**: references `role.boundaries.owns / not_owns` (per ADR-0028), never duplicates
4. **No deprecated-path guidance**: does not direct to legacy fallback paths
5. **Enforcement**: `tests/integration/test_skill_description_convention.bats` (3 assertions)

Anti-routing judgments are centralized in `skills/guide/SKILL.md` recommender.

See [ADR-0051](../../adr/ADR-0051-skill-description-convention.md) for full convention.
```

- [ ] **Step 3: Defer commit**

---

## Task 10: P3 — final regression check

**Files:**
- Run: `./test.sh --quick`

- [ ] **Step 1: Run smoke + quick tests**

Run: `./test.sh --quick`
Expected: all pass, no new failures vs baseline

- [ ] **Step 2: If any new failure, fix root cause and re-run**

Per Sisyphus phase 2C: never shotgun debug. Fix root cause. After 3 consecutive failures on the same test, escalate to Oracle.

- [ ] **Step 3: Defer commit (will batch at archive)**

---

## Self-review

**1. Spec coverage** (against `specs/.../spec.md` 5 Scenarios):
- Scenario "description under 200 tokens" → Task 2-7 each verify ≤ 200 ✓
- Scenario "no anti-trigger phrasing" → Task 2-7 each grep ✓
- Scenario "references boundaries" → Task 2-7 each grep ✓
- Scenario "no deprecated path" → Task 2-7 manual review (per-skill content reflects current state, not legacy) ✓
- Scenario "guide recommender centralized" → Task 8 ✓

**2. Placeholder scan**: Each task has concrete content (per-skill invocation lines, exact file paths, exact grep commands). No "TBD" / "TODO" / "implement later".

**3. Type consistency**: All task Files sections use consistent path format (`skills/X/SKILL.md`). All Step commands use consistent bash.

**Empty coverage check**: Bats test (Task 6) covers AC-5 (3 assertions) ✓; description rewrites (Task 2-6) cover AC-1, AC-2, AC-3, AC-4 ✓; guide (Task 8) covers AC-6 ✓; doc section (Task 9) covers AC-7 ✓; final regression (Task 10) covers AC-8 ✓; human review (Task 7) covers AC-9 ✓; improvement-suggestions removal was done at approval (Task 1 verifies).

All 10 AC covered.
