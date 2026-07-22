# v3.0.0: Rename `spec-workflow` → `rdd-workflow` (Full Clean Break)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan stage-by-stage. **Stage 1 + Plan Review complete**. Stage 2-6 below. Do NOT start Stage 2 without user confirmation on Plan Review (CORRECTIONS section).

**Goal:** Bump version to v3.0.0 (breaking). Rename `spec-workflow` → `rdd-workflow` across the entire codebase (code, docs, ADRs, specs, archive, install paths, skill names, npm package). **No backward compatibility shim.** Users must reinstall and update `skill_use("X")` calls.

> **Naming decision (user-confirmed 2026-07-22)**: Use `rdd-workflow` (not `rddf-workflow`). User accepts the naming collision with existing `rddf` CLI / `.rddf/` directory / `rdd-session` skill / `rddf_session` Python module. Documented in ADR-0023.

**Architecture:**
- **Stage 1: Verification & Preparation** — ✅ COMPLETE (this file is part of Stage 1 deliverable)
- **Stage 2: Code identifiers** (package.json, plugin manifests, install.sh, skill frontmatter, skill directory rename, functional Python/bash code) — ~80 files
- **Stage 3: User documentation** (README, USAGE, CHANGELOG, AGENTS, docs/v2-*.md, plans, issue templates, active changes) — ~50 files
- **Stage 4: Archive + ADR + spec** (ADR-0001..0022, openspec/specs, openspec/changes/archive, docs/superpowers, docs/audit, docs/legacy, docs/migration) — ~80 files
- **Stage 5: Verification** (full test suite, grep "rdd-workflow" should be 0, lsp_diagnostics, smoke regression)
- **Stage 6: Commit + Release** (single v3.0.0 commit, CHANGELOG update, version bump in package.json + SKILL.md frontmatter)

**Tech Stack:** bash (grep/sed for bulk renames), Python 3.11+ (for `_lib/` updates), bats-core + pytest (verification)

---

## Stage 1 Report: Verification & Preparation ✅

### 1.1 CI workflow gate audit ✅
- `.github/workflows/test.yml` (74 lines) — **clean**. Only `assert.*or True\|assert True` quality gate exists. No `rdd-workflow` grep gate.
- **Verdict:** No CI gate will block the rename.

### 1.2 npm registry check ✅
- `npm view rdd-workflow version` → **404 Not Found**
- `npm view rdd-workflow version` → **404 Not Found**
- **Verdict:** Package never published to npm. `package.json` `"name": "spec-workflow"` was **historical**, no real install traffic. Rename to `rdd-workflow` is safe — no installed users via npm.

### 1.3 Active changes check ✅
- `openspec/changes/` → **no active changes** (only `archive/`)
- **Verdict:** No in-flight changes to update alongside rename.

### 1.4 Worktree state ✅
- `git worktree list` → only main repo (master @ 3823391), no detached worktrees
- `.rddf/wt/task-parallel-throttle/` exists but **contains a full copy of the repo at an older commit** (not a separate worktree, just a vendored snapshot). It has 147 `rdd-workflow` references but is NOT tracked by the current branch. **Verdict:** Will rename via repo-wide sed; the .rddf/wt/ copy will follow on next `git checkout`.

### 1.5 Baseline test status ✅ (mixed)
- `bats tests/smoke.bats` → **8/8 PASS** ✅
- `pytest tests/unit/` → **951 passed, 1 pre-existing failure** ⚠️
  - `test_install_description_skill_count_matches_disk` — INSTALL.md description missing "全部 N 个子技能" format
  - **This is a pre-existing bug unrelated to the rename.** Will be fixed in Stage 2 (R1) to keep Stage 5 verification fully green.
- `pytest tests/integration/` → not yet run (will run in Stage 5)
- **Verdict:** Baseline mostly green. Stage 2 can proceed.

### 1.6 Functional code references ⚠️ CRITICAL

Discovered **functional (not cosmetic)** references that must be renamed carefully:

| File | Line | Type | Notes |
|------|------|------|-------|
| `skills/_lib/loop/actions.py` | 163 | **Path resolution** | `Path(__file__).parent.parent.parent / "rdd-workflow-writing-plans.md"` — checks if skill exists |
| `skills/_lib/loop/actions.py` | 168, 173, 180, 184 | Error messages + marker text | References `rdd-workflow/writing-plans` |
| `skills/_lib/cli/__init__.py` | 3 | Docstring | "single CLI entry point for rdd-workflow" |
| `skills/_lib/cli/__main__.py` | 17, 19, 50, 146, 149, 174 | Detection messages | "Non-rdd-workflow project detection" |
| `skills/_lib/cli/init_cmd.py` | 3, 52, 105, 117 | Path construction | `Path(target_str) / ".opencode" / "skills" / "rdd-workflow"` |
| `skills/_lib/cli/monitor_cmd.py` | 113 | UI banner | "📡 rdd-workflow 实时监控" |
| `skills/_lib/cli/version_cmd.py` | 4, 47 | Banner | `rddf v<X.Y.Z> — rdd-workflow CLI` |
| `skills/_lib/core/defaults.py` | 1 | Docstring | "rdd-workflow v2 configuration" |
| `skills/_lib/core/state_vector.py` | 1 | Docstring | "rdd-workflow v2" |
| `skills/_lib/dashboard/__init__.py` | 4 | Docstring | "rdd-workflow project" |
| `tests/conftest.py` | 8 | Docstring | `/workspace/project/rdd-workflow/skills/_lib/...` |
| `tests/test_helper.bash` | 5 | Comment | "rdd-workflow repo root" |
| `tests/integration/test_frontmatter_dupkey.bats` | 24 | Test fixture | Skill list comment |
| `tests/integration/test_writing_plans_integration.bats` | 24, 28, 31, 38, 47, 52, 91, 93, 130, 132, 166, 168, 179, 182, 183, 215, 217, 238, 240 | **Test assertions** (26 total) | `grep -qE '"rdd-workflow-writing-plans"'` — these are FUNCTIONAL test assertions that lock the skill name |
| `tests/unit/test_doc_contracts.py` | 63-70 | Test | Validates `INSTALL.md` description contains "全部 N 个子技能" (pre-existing bug) |
| **JSON schemas `$id` field** | arch_handoff_schema.json:3, sessions_schema.json:3 | **Functional** | `https://rdd-workflow.local/...` — JSON Schema `$id` URI; consumers may resolve this URL |
| **8 JSON schemas description fields** | schemas/*.json | Docstring | May reference "rdd-workflow" — must check |

**Verdict:** Functional code + tests are concentrated in:
1. `skills/_lib/loop/actions.py` (1 critical path check + 4 error messages)
2. `tests/integration/test_writing_plans_integration.bats` (26 assertions)
3. `skills/_lib/cli/init_cmd.py` (1 path construction: `Path(target_str) / ".opencode" / "skills" / "rdd-workflow"`)
4. `skills/_lib/schemas/*.json` `$id` fields (functional for schema resolution)

All must be updated in lockstep with the rename.

### 1.7 Path rename implications

| Old path | New path | Migration |
|----------|----------|-----------|
| `skills/rdd-workflow-writing-plans/SKILL.md` | `skills/rdd-workflow-writing-plans/SKILL.md` | Directory rename (`git mv`) |
| `~/.agents/skills/rdd-workflow/` | `~/.agents/skills/rdd-workflow/` | Install path change — user must reinstall |
| `.opencode/skills/rdd-workflow/` | `.opencode/skills/rdd-workflow/` | Install path change — user must reinstall |
| `install-rdd-workflow.sh` | `install-rdd-workflow.sh` | Generated script name (in INSTALL.md) |

### 1.8 Stage 1 verdict

✅ **Ready to proceed.** All blockers identified. Stage 2-6 plan is implementable.

---

## Tasks by Stage

### Stage 2: Code identifiers (~95 files)

**Goal:** Update all functional code + manifest files + skill names. Stage must end with `pytest tests/unit/` green and `bats tests/integration/test_writing_plans_integration.bats` green.

**Sub-tasks:**

| # | File(s) | Change |
|---|---------|--------|
| 2.1 | `package.json` | `"name": "rdd-workflow"` → `"rdd-workflow"`, `"version": "2.0.7"` → `"3.0.0"`, description string, `keywords` (remove "spec", add "rdd-workflow"), `alias` (add `"rdd-workflow"`), `skills[]` array (rename `rdd-workflow-writing-plans` → `rdd-workflow-writing-plans`) |
| 2.2 | `.claude-plugin/plugin.json` | name + displayName + repository URL (if hardcoded) |
| 2.3 | `.claude-plugin/marketplace.json` | marketplace name + plugins[].name/displayName |
| 2.4 | `skills/rdd-workflow-writing-plans/SKILL.md` → `skills/rdd-workflow-writing-plans/SKILL.md` | `git mv` + frontmatter `name:` field |
| 2.5 | All SKILL.md frontmatter that reference `skill_use("rdd-workflow/writing-plans")` | Update call sites to `skill_use("rdd-workflow/writing-plans")`. Affected: `skills/guide-ship/SKILL.md`, `skills/INSTALL.md`, `skills/execute/SKILL.md`, `skills/guide-arch/SKILL.md`, `skills/roadmap/SKILL.md` |
| 2.6 | `skills/_lib/loop/actions.py` | Update path resolution (L163) + error messages (L168, 173, 180, 184). **CRITICAL**: this is the only path-check in code |
| 2.7 | `skills/_lib/cli/__init__.py`, `__main__.py`, `init_cmd.py`, `monitor_cmd.py`, `version_cmd.py` | Docstrings, detection messages, **path construction** (`init_cmd.py:52`), banner (`version_cmd.py:47`) |
| 2.8 | `skills/_lib/core/defaults.py`, `state_vector.py`, `dashboard/__init__.py` | Docstrings |
| 2.9 | `skills/_lib/loop/interaction_modes.py`, `plugin_loader.py`, `loop_engine.py`, `plugins/README.md` | Docstrings |
| 2.10 | `skills/_lib/schemas/*.json` (8 files) | **CRITICAL**: rename `$id` URI (`rdd-workflow.local` → `rdd-workflow.local`, `rdd-workflow.dev` → `rdd-workflow.dev`). Also check `description` fields |
| 2.11 | `skills/_lib/archive.sh` | Comments, error messages |
| 2.12 | `skills/guide-ship/scripts/ship_plan.sh` | Comments |
| 2.13 | `install.sh` | Comment, error messages, default install path |
| 2.14 | `skills/INSTALL.md` | description, all `rdd-workflow` strings, `SKILLS_DIR` default, generated script template (`install-rdd-workflow.sh` → `install-rdd-workflow.sh`) |
| 2.15 | `tests/conftest.py`, `tests/test_helper.bash`, `tests/README.md` | Docstrings/comments |
| 2.16 | `tests/integration/test_writing_plans_integration.bats` | All **26** `rdd-workflow-writing-plans` assertions + grep patterns (lines listed in 1.6) |
| 2.17 | `tests/integration/test_frontmatter_dupkey.bats`, `test_hook_boundary.py` | Comments, skill list references |
| 2.18 | `tests/unit/test_cli_init.py`, `test_cli_version.py`, `test_doc_contracts.py` | Update test assertions to match new INSTALL.md description |
| 2.19 | `requirements.txt`, `config.yaml` | Comments |
| 2.20 | `proposal-suggestions.md` | **JSON-aware rename**: parse JSON, rename `description` fields containing "rdd-workflow", keep `name`/`id` fields unchanged, write back with `indent=2` + `ensure_ascii=False` |

**R1 fix in Stage 2**: When rewriting `skills/INSTALL.md` description, ensure it contains the literal string `"全部 N 个子技能"` (where N matches disk count). This fixes the pre-existing `test_install_description_skill_count_matches_disk` failure.

**Acceptance:**
- `grep -rn "rdd-workflow" skills/ tests/ package.json .claude-plugin/ install.sh` returns **0 matches**
- `grep -rn "rdd-workflow" skills/ tests/ package.json .claude-plugin/ install.sh` returns expected matches
- `pytest tests/unit/ -q` exits 0 (including the previously failing `test_install_description_skill_count_matches_disk`)
- `bats tests/integration/test_writing_plans_integration.bats` all PASS
- `bats tests/integration/test_frontmatter_dupkey.bats` all PASS

---

### Stage 3: User documentation (~50 files)

**Goal:** Update all user-facing docs that are NOT in ADR/spec/archive.

**Sub-tasks:**

| # | File(s) | Change |
|---|---------|--------|
| 3.1 | `README.md` | Title, npm install commands, install paths, all `rdd-workflow` references |
| 3.2 | `USAGE.md`, `CHANGELOG.md`, `AGENTS.md` | All `rdd-workflow` strings |
| 3.3 | `CHANGELOG.md` | **ADD** v3.0.0 entry: "BREAKING: Renamed `spec-workflow` → `rdd-workflow`. No backward compatibility. See ADR-NNNN for migration notes." |
| 3.4 | `docs/v2-*.md` (8 files: api-reference, architecture-refactor-plan, config-schema, developer-guide, gate-mechanism-guide, implementation-plan, loop-engine-guide, loop-engine, memory-system-guide, multi-session-guide, tribunal-guide, workflow-overview, adr-summary) | All references |
| 3.5 | `docs/ONBOARDING.md`, `docs/proposal-suggestions-format.md` | All references |
| 3.6 | `docs/migration/v1-to-v2.md` | Update (historical but user-facing) |
| 3.7 | `docs/loop-engineering-research.md` | All references |
| 3.8 | `.rddf/plans/*.md` (active plans, not all 26) | All references |
| 3.9 | `.rddf/state/index.md` | Update header |
| 3.10 | `.github/ISSUE_TEMPLATE/beta-feedback.md`, `bug-report.md` | All references |

**Acceptance:**
- `grep -rn "rdd-workflow" README.md USAGE.md CHANGELOG.md AGENTS.md docs/v2-*.md docs/ONBOARDING.md docs/proposal-suggestions-format.md .rddf/plans/ .rddf/state/index.md .github/ISSUE_TEMPLATE/` returns **0 matches**
- `head -1 README.md` shows `# RDD Workflow` not `# RDD Workflow`

---

### Stage 4: Archive + ADR + spec (~80 files)

**Goal:** Per user decision, rename even historical documents. Add a note in CHANGELOG v3.0.0 explaining the retroactive rename.

**Sub-tasks:**

| # | File(s) | Change |
|---|---------|--------|
| 4.1 | `docs/adr/ADR-0001..ADR-0022` (22 files) + `docs/adr/README.md` | All `rdd-workflow` → `rdd-workflow` |
| 4.2 | `docs/v2-adr-summary.md` | All references |
| 4.3 | `openspec/specs/*/spec.md` (8 files: detectors-actions, doc-truth-sync, flow-customization, gate-mechanism, general, memory, release-management, state-management) | All references |
| 4.4 | `openspec/changes/archive/2026-*/` (all subdirs: proposal.md, design.md, tasks.md, .openspec.yaml) | All references |
| 4.5 | `docs/superpowers/specs/*.md` | All references |
| 4.6 | `docs/superpowers/plans/*.md` | All references |
| 4.7 | `docs/audit/*.md` | All references |
| 4.8 | `docs/legacy/rddf-legacy-v2.0.7.sh` | Update script header comments |
| **4.9** | **`docs/adr/ADR-0023-v3-rename-rdd-workflow-to-rdd-workflow.md`** (NEW FILE) | **R4: New ADR documenting the rename decision**. Context (why), Decision (chose `rdd-workflow` despite naming collision with `rddf` CLI), Consequences (breaking change, no compat shim, install path change, skill name change). Status: 已采纳. |

**Special handling for ADR/spec (R3 + per-user decision):**
- Add a **footnote at the top of each ADR file**: `> Note: Originally authored as "spec-workflow". Renamed to "rdd-workflow" in v3.0.0 (2026-07-22).`
- This preserves the historical fact for future readers.
- Spec files in `openspec/specs/` describe *capabilities* of the workflow skill. Renaming references to "rdd-workflow" → "rdd-workflow" is appropriate, but **capability descriptions themselves** (e.g., "this engine has detectors and actions") should remain semantically unchanged.

**Acceptance:**
- `grep -rn "rdd-workflow" docs/ openspec/` returns **0 matches** (excluding CHANGELOG note about v3.0.0 rename + the new ADR-0023 itself which mentions the original name)
- `find docs/adr/ -name "*.md" -exec grep -l "rdd-workflow" {} \;` returns **0 files** (or only ADR-0023 with the rename documented)
- ADR-0023 exists at `docs/adr/ADR-0023-v3-rename-rdd-workflow-to-rdd-workflow.md`

---

### Stage 5: Verification

**Goal:** Confirm full repo is renamed and tests still pass.

**Sub-tasks:**

| # | Check | Pass criteria |
|---|-------|---------------|
| 5.1 | `grep -rn "rdd-workflow" --include="*.md" --include="*.json" --include="*.yaml" --include="*.yml" --include="*.py" --include="*.sh" --include="*.bash" --include="*.toml" .` | **0 matches** |
| 5.2 | `grep -rn "rdd-workflow" .` (broad) | Only `.rddf/wt/task-parallel-throttle/` (gitignored) and `.git/` (history) |
| 5.3 | `bats tests/smoke.bats` | All PASS |
| 5.4 | `pytest tests/unit/ -q` | All PASS (including previously failing `test_install_description_skill_count_matches_disk` — fixed by R1) |
| 5.5 | `pytest tests/integration/ -q` | All PASS |
| 5.6 | `bats tests/ --recursive` | All PASS |
| 5.7 | `lsp_diagnostics skills/_lib/loop/actions.py skills/_lib/cli/*.py skills/_lib/core/*.py` | Clean |
| 5.8 | `ruff check skills/_lib/` | Clean |
| 5.9 | `mypy --strict skills/_lib/core/` | Clean |
| 5.10 | Manual: simulate install path `~/.agents/skills/rdd-workflow/` exists | Verified |
| 5.11 | Manual: `skill_use("rdd-workflow/writing-plans")` resolves correctly | Verified (via grep on INSTALL.md + package.json `skills[]`) |
| **5.12** | **R2: New regression test** `tests/integration/test_no_spec_workflow_residue.bats` | PASS — `grep -rn "rdd-workflow" "$REPO_ROOT/"` excluding `.rddf/wt/` and `.git/` returns 0 matches |

**R2 implementation hint** for the new regression test:
```bash
@test "no 'rdd-workflow' references remain anywhere in repo (v3.0.0 rename guard)" {
    result=$(grep -rn "rdd-workflow" \
        --include="*.md" --include="*.json" --include="*.yaml" --include="*.yml" \
        --include="*.py" --include="*.sh" --include="*.bash" --include="*.toml" \
        --include="*.jsonc" --include="*.cfg" --include="*.txt" \
        "$REPO_ROOT_ORIGIN/" 2>/dev/null \
        | grep -v "\.rddf/wt/" \
        | grep -v "\.git/" \
        || true)
    assert [ -z "$result" ] || (echo "Found stale rdd-workflow refs:"; echo "$result"; false)
}
```

**If any check fails:** STOP. Revert to last green state. Investigate. Do not proceed to Stage 6.

---

### Stage 6: Commit + Release

**Goal:** Single v3.0.0 commit (or 2-3 logically-grouped commits), update CHANGELOG, tag release.

**Commit strategy (recommended):**

Option A (cleanest): **Single commit** for the entire rename
```
v3.0.0: rename rdd-workflow to rdd-workflow (BREAKING)
```

Option B (reviewable): **3 commits** staged progressively:
1. `feat(adr): add ADR-0023 documenting v3.0.0 rename decision`
2. `chore!: rename rdd-workflow to rdd-workflow across all files (BREAKING)`
3. `test: add regression guard against rdd-workflow residue`

**Recommendation**: Option B. Better for code review, allows bisecting.

**Sub-tasks:**

| # | Action | Notes |
|---|--------|-------|
| 6.1 | Verify `git status` is clean before any commit | Should be |
| 6.2 | `git add -A` and review `git diff --stat` | Should show ~171 file changes + 1 directory rename |
| 6.3 | `git commit -m "feat(adr): add ADR-0023 v3.0.0 rename decision"` (Option B) | First commit |
| 6.4 | `git commit -m "chore!: rename rdd-workflow to rdd-workflow (BREAKING)"` (Option B) | Uses conventional-commits `!` for breaking change. Use `git-master` skill for atomic commit message format |
| 6.5 | `git commit -m "test: add regression guard against rdd-workflow residue"` (Option B) | Adds the new bats test from R2 |
| 6.6 | Update `CHANGELOG.md` v3.0.0 section with migration guide (R3) | ADR-style structured entry |
| 6.7 | `git tag v3.0.0` | Annotated tag |
| 6.8 | `git push origin master --tags` | Push release |
| 6.9 | Manual verification: `git checkout v3.0.0 && bash install.sh --global` | Smoke test install path |
| 6.10 | (Optional) GitHub release notes | Link to CHANGELOG v3.0.0 entry + ADR-0023 |

**Acceptance:**
- `git log --oneline -5` shows v3.0.0 commit(s) per Option B
- `git tag` lists `v3.0.0`
- `git status` clean
- `git diff v2.0.7..v3.0.0 --stat` shows expected file count

---

## Migration guide (for CHANGELOG v3.0.0)

```markdown
## v3.0.0 (2026-07-22) — BREAKING

### Renamed: `spec-workflow` → `rdd-workflow`

The entire skill pack has been renamed to align with the GitHub repository name. **No backward compatibility.**

**For users with existing installations:**

1. **Reinstall the skill pack**:
   ```bash
   # Remove old installation
   rm -rf ~/.agents/skills/rdd-workflow
   rm -rf .opencode/skills/rdd-workflow

   # Install new
   git clone https://github.com/chisuhua/rdd-workflow.git ~/.agents/skills/rdd-workflow
   bash ~/.agents/skills/rdd-workflow/install.sh --global
   ```

2. **Update skill calls**:
   - `skill_use("rdd-workflow/writing-plans")` → `skill_use("rdd-workflow/writing-plans")`

3. **No data migration needed**: `.rddf/state/` content is unaffected. Existing rddf-sessions, iterations, deps-analysis all continue to work.

**Historical note**: Documents authored before v3.0.0 used the name `rdd-workflow`. These have been retroactively renamed to `rdd-workflow` for consistency. Each ADR carries a footnote noting the original name.
```

---

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| User installs break silently | 🟠 Medium | CHANGELOG has explicit migration guide; install.sh prints old-path warning if detected |
| Tests fail after rename | 🟡 Low | Run Stage 5 verification before commit; pre-existing failure documented |
| `.rddf/wt/` vendored copy out of sync | 🟢 Low | gitignored, not tracked; next checkout re-syncs |
| ADR/spec retroactive rename confuses future readers | 🟠 Medium | Each ADR gets a footnote; CHANGELOG explains decision |
| Functional code regression (actions.py path) | 🟠 Medium | Stage 2 acceptance gates include pytest + bats on actions.py paths |
| Public npm/github URL mismatch | 🟢 Low | Neither was ever published externally (verified) |

---

## Estimated effort

| Stage | Files | Time (with parallel agents) |
|-------|-------|-----------------------------|
| Stage 1 (done) | — | ~15 min |
| Stage 2 | ~95 | ~35 min (parallel deep agents) |
| Stage 3 | ~50 | ~20 min (parallel deep agents) |
| Stage 4 | ~80 (incl. ADR-0023 new file) | ~25 min (parallel deep agents) |
| Stage 5 | — | ~10 min (verification) |
| Stage 6 | 3 commits + tag | ~5 min |
| **Total** | **~225 unique files** | **~1.7 hours** |

---

## Plan Review Corrections (2026-07-22)

Plan was reviewed against actual codebase state. **3 critical issues** fixed, **5 recommended improvements** incorporated, **18 missed items** added to Stage 2-4 file lists.

### Critical issues fixed

| ID | Issue | Resolution |
|----|-------|-----------|
| **C1** | Naming collision (`rdd-workflow` vs `rddf` CLI / `rdd-session` skill / `.rddf/` dir) | User confirmed `rdd-workflow` is the chosen name. Documented in ADR-0023 (Stage 4.9). Acknowledged as accepted risk. |
| **C2** | JSON schema `$id` URI references (`rdd-workflow.local`, `rdd-workflow.dev`) — would break schema resolution | Stage 2.10 upgraded from "check" to **mandatory rename** of all 8 schema files |
| **C3** | `proposal-suggestions.md` is JSON not Markdown — bulk sed would corrupt | Stage 2.20 upgraded to **JSON-aware rename** via Python `json.load/dump` |

### Recommended improvements incorporated

| ID | Improvement | Resolution |
|----|------------|-----------|
| **R1** | Fix pre-existing `test_install_description_skill_count_matches_disk` failure | Incorporated into Stage 2 (rewrite INSTALL.md description with "全部 N 个子技能") |
| **R2** | Add regression guard test for `rdd-workflow` residue | Stage 5.12 new test `tests/integration/test_no_spec_workflow_residue.bats` |
| **R3** | Make CHANGELOG v3.0.0 entry more structured (ADR-style) | Stage 6.6 uses structured format (Why / Scope / Compat / Action items / No data migration / Historical note) |
| **R4** | Create ADR-0023 for the rename decision (governance) | Stage 4.9 new ADR file |
| **R5** | `openspec/specs/*.md` describe capabilities, not branding — be careful with renaming | Stage 4 spec section: rename references, preserve capability descriptions |

### Missed items added

| ID | Item | Stage |
|----|------|-------|
| M1-M2 | 8 JSON schema files `$id` and `description` fields | Stage 2.10 |
| M3 | `proposal-suggestions.md` JSON format | Stage 2.20 |
| M4 | `package.json` keywords/alias updates | Stage 2.1 |
| M6 | `tests/integration/test_hook_boundary.py` | Stage 2.17 |
| M7 | `tests/unit/test_cli_init.py`, `test_cli_version.py` | Stage 2.18 |
| M8 | `tests/unit/test_doc_contracts.py` (also fixes R1) | Stage 2.18 |
| M9 | `skills/_lib/loop/interaction_modes.py` | Stage 2.9 |
| M10 | `skills/_lib/loop/plugin_loader.py` | Stage 2.9 |
| M11 | `skills/_lib/loop_engine.py` | Stage 2.9 |
| M12 | `skills/_lib/plugins/README.md` | Stage 2.9 |
| M14 | `skills/_lib/archive.sh` | Stage 2.11 |
| M15 | `skills/execute/SKILL.md`, `guide-arch/SKILL.md`, `guide-ship/SKILL.md`, `roadmap/SKILL.md` | Stage 2.5 |
| M16 | `skills/guide-ship/scripts/ship_plan.sh` | Stage 2.12 |
| M17 | `tests/README.md` | Stage 2.15 |
| M18 | `docs/adr/README.md` | Stage 4.1 |

### Stage 1 verification corrections

- File count: **171 unique files** contain `rdd-workflow` (not 869; 869 was total occurrence count). Plan updated from "~210" → "~225" (includes ADR-0023 new file + 18 added items).
- Test assertions in `test_writing_plans_integration.bats`: **26 total** (not "~11" as initially stated). Updated in Stage 1.6 table.

---

## Stop conditions

STOP and consult user if:
- Stage 5 verification reveals a missed reference
- A test fails that's not the pre-existing `test_install_description_skill_count_matches_disk` (which should now pass after R1 fix)
- Functional code path (`actions.py:163` or `init_cmd.py:52` or schema `$id`) breaks after rename
- ADR cross-references break (e.g., ADR-0017 references ADR-0016 which references rdd-workflow — but ADR-0017 itself is being renamed too)
- New test from R2 fails

DO NOT proceed past any stage without explicit user confirmation.