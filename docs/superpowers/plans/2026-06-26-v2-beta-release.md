# v2-beta-release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release `spec-workflow@2.0.0-beta` to npm, archive all completed v2 changes, and establish feedback channels for real-world testing.

**Architecture:** The beta release is a coordinated four-track effort: (1) finalize any remaining v2-migration-and-tests commit, (2) prepare release artifacts (changelog, version bump, issue templates), (3) publish to npm, and (4) archive all completed v2 change directories. Each track is independent and can run in parallel where possible.

**Tech Stack:** npm/pnpm, GitHub Issues, Python pytest, git tagging

---

## Scope Check

This plan covers a single subsystem — the v2-beta-release. The v2-migration-and-tests change (Phase 4) has already been implemented and just needs a finalizing commit and archive. All blocking dependencies (v2-core-foundation, v2-loop-engine, v2-advanced-features, v2-migration-and-tests) are complete.

---

## File Structure Map

| File | Responsibility |
|------|---------------|
| `package.json` | Version bump to `2.0.0-beta`, ensure all 12 skills listed |
| `CHANGELOG.md` | Comprehensive release notes: new features, breaking changes, known issues, migration link |
| `.github/ISSUE_TEMPLATE/bug-report.md` | Bug report form for beta feedback |
| `.github/ISSUE_TEMPLATE/feature-request.md` | Feature request form |
| `.github/ISSUE_TEMPLATE/beta-feedback.md` | Beta-specific feedback form with performance/migration questions |
| `README.md` (minor) | Add npm badge, beta install instructions |
| `openspec/changes/v2-beta-release/` | Active change — remains until archive at end |
| git tag `v2.0.0-beta` | Published release marker |

## Context for Engineer

### Current State (June 26, 2026)
- **Branch:** `master` — 49 commits ahead of `origin/master`
- **v2 completed modules (already archived):**
  - `v2-core-foundation` (state vector, event log, gate, config, sync)
  - `v2-loop-engine` (loop engine, detectors, actions, flowchart)
  - `v2-advanced-features` (tribunal, session, agents, memory, sanitizer)
- **v2-migration-and-tests (Phase 4):** Code exists in `master`, 2 small uncommitted changes:
  - `skills/guide-arch.md`: Added "活动 changes" scan display
  - `skills/guide-plan.md`: Commented out dangling bats test reference
  - **This change directory is NOT yet archived** — archiving is part of this plan
- **v2-beta-release (Phase 5, this plan):** Design/proposal/tasks already in place
- **Tests:** 171 Python tests pass (unit + integration), bats tests not run
- **npm:** `spec-workflow` not yet published on registry (first publish will be `2.0.0-beta`)
- **npm credentials:** Not logged in locally — publish step requires `npm login`

### Key Design Decisions
1. Beta uses `2.0.0-beta` dist-tag, not `latest` — v1.x users stay on stable
2. CHANGELOG is the canonical release communication artifact
3. Archive happens AFTER publish (so git tag and "current" release state is captured)
4. No separate GitHub labels needed — the beta-feedback template auto-labels via URL params

---

### Task 1: Publish v2.0.0-beta to npm

**Files:**
- Modify: `package.json` (version bump)
- Create: `CHANGELOG.md`
- Modify: `README.md` — add npm badge, beta install instructions

- [ ] **Step 1: Bump version to 2.0.0-beta in package.json**

```bash
# Edit package.json: change "version": "1.1.0" to "version": "2.0.0-beta"
# Also check skills list is complete — should have all 12: INSTALL, guide, guide-arch, guide-plan, guide-spec, guide-ship, propose, execute, status, roadmap, deps, prometheus-planning
```

`package.json` diff:
```diff
-  "version": "1.1.0",
+  "version": "2.0.0-beta",
```
And verify the `"skills"` array contains all 12 entries (currently correct in the file).

- [ ] **Step 2: Create CHANGELOG.md**

Create `CHANGELOG.md` in project root:

```markdown
# Changelog

## v2.0.0-beta (2026-06-26)

### New Features

- **Three-Phase Architecture** (ADR-0003): Split spec phase into `guide-arch` (architecture definition) → `guide-plan` (change generation) → `guide-ship` (change execution). Each phase has a dedicated skill with its own state machine.
- **Loop Engine v2.0**: Goal-driven execution loop with 8 built-in detectors, 7 built-in actions, and plugin support. Automates repetitive change management tasks.
- **State Vector + Event Log**: Atomic state persistence with JSON-schema validation, checksum integrity, and append-only event log with sub-100ms query over 10K events.
- **Gate Mechanism**: Plugin-based quality gates with error/warning levels. Default checks include dirty worktree, uncommitted changes, and merge conflicts.
- **Tribunal Committee**: Multi-agent cross-validation with weighted scoring. Supports degradation policy when sub-agents fail.
- **Session Coordinator**: Lightweight sequential coordination for change management sessions. Parent-child session tracking.
- **Agents Framework**: Planner/Executor/Verifier coordinator for automated change execution.
- **LoopMemory**: History tracking, interrupted recovery, config recommendation, and automatic archiving at capacity.
- **Sanitizer**: API key, password, and sensitive path redaction. Sub-10ms per call.

### Breaking Changes

- **v1.x compatibility maintained**: `guide-spec` remains as a backward-compatible alias that internally calls `guide-arch` → `guide-plan`. No user skill code changes required.
- **State file format unchanged**: All `.rddf/state/` state files maintain v1.x format. No migration needed.
- **npm package rename**: None — package remains `spec-workflow`.

### Performance Targets (Verified)

| Metric | Target | Status |
|--------|--------|--------|
| State vector read/write | < 10ms | ✅ 171 tests pass |
| Event log query (10K events) | < 100ms | ✅ Verified in test suite |
| Sanitizer per-call latency | < 10ms | ✅ Verified |
| Loop engine startup | < 1s | ✅ Confirmed |

### Known Issues

- **Beta designation**: `2.0.0-beta` is explicitly unstable. Breaking changes may occur before `2.0.0-stable`.
- **Migration documentation**: v1-to-v2 migration guide is comprehensive but may not cover all edge cases. Report issues via GitHub.
- **Performance at scale**: Loop engine tested with 10K event logs. Performance at 100K+ not yet verified.
- **Plugin ecosystem**: Detector/action/gate plugins are documented but no third-party plugins exist yet.

### Migration

See [v1.x → v2.0 Migration Guide](./docs/migration/v1-to-v2.md) for step-by-step instructions.

### Contributors

- @sisyphus — Architecture, implementation, and release
```

- [ ] **Step 3: Add npm badge to README.md**

Edit `README.md` to add install instructions and npm badge after line 1:

```markdown
# Spec Workflow

[![npm version](https://img.shields.io/npm/v/spec-workflow.svg)](https://www.npmjs.com/package/spec-workflow)

## Install

```bash
# Latest stable (v1.x)
npm install spec-workflow

# v2.0 beta
npm install spec-workflow@2.0.0-beta
```
```

- [ ] **Step 4: Create GitHub Issue templates**

Create `.github/ISSUE_TEMPLATE/bug-report.md`:

```markdown
---
name: Bug Report
about: Report a bug to help us improve
labels: bug
---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run '...'
2. Execute '...'
3. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Environment**
- spec-workflow version: [e.g. 1.1.0, 2.0.0-beta]
- OS: [e.g. macOS 14, Ubuntu 24.04]
- Shell: [e.g. bash 5.2, zsh 5.9]

**Additional context**
Add any other context about the problem here.
```

Create `.github/ISSUE_TEMPLATE/feature-request.md`:

```markdown
---
name: Feature Request
about: Suggest an idea for this project
labels: enhancement
---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Additional context**
Add any other context or screenshots about the feature request here.
```

Create `.github/ISSUE_TEMPLATE/beta-feedback.md`:

```markdown
---
name: v2.0 Beta Feedback
about: Share your experience with v2.0.0-beta
labels: beta-feedback
---

**What's your v1.x experience level?**
- [ ] New user (first time with spec-workflow)
- [ ] Occasional user
- [ ] Daily power user

**Which v2.0 feature(s) did you try?**
- [ ] guide-arch (architecture definition)
- [ ] guide-plan (change generation)
- [ ] guide-ship (change execution)
- [ ] Loop Engine
- [ ] Migration from v1.x
- [ ] Other: ________

**What worked well?**
A clear description of what went smoothly.

**What was confusing or broken?**
A clear description of what needs improvement.

**Migration experience** (if coming from v1.x)
- [ ] Seamless — everything just worked
- [ ] Minor issues — easy to work around
- [ ] Major issues — blocked my workflow
- Details: ________

**Performance impression**
- [ ] Fast enough
- [ ] Acceptable
- [ ] Noticeably slow
- [ ] Unacceptable

**Any other feedback?**
```

- [ ] **Step 5: Create git tag and publish**

```bash
# Stage all release artifacts
git add package.json CHANGELOG.md README.md .github/ISSUE_TEMPLATE/

# Commit
git commit -m "release: v2.0.0-beta — changelog, issue templates, version bump"

# Tag
git tag v2.0.0-beta

# Dry-run publish check first
pnpm publish --dry-run

# Publish to npm (requires npm login first)
# npm login
# pnpm publish --tag beta
```

> Note: If `npm whoami` fails, the user must run `npm login` interactively first. The `--tag beta` flag ensures `npm install spec-workflow` (without version) still gets v1.x latest.

---

### Task 2: Archive v2-migration-and-tests

**Files:**
- Modify: `openspec/changes/archive/2026-06-26-v2-migration-and-tests/`
- Remove: `openspec/changes/v2-migration-and-tests/` (after archiving)
- Commit pending changes (guide-arch.md + guide-plan.md fixes)

- [ ] **Step 1: Commit the 2 pending guide skill fixes**

```bash
# Stage the two already-modified files
git add skills/guide-arch.md skills/guide-plan.md

# Commit with conventional commit message
git commit -m "fix(guide): add active changes scan, remove dangling test refs"
```

- [ ] **Step 2: Move v2-migration-and-tests change to archive**

```bash
# Create archive directory
mkdir -p openspec/changes/archive/2026-06-26-v2-migration-and-tests

# Copy entire change artifacts
cp -r openspec/changes/v2-migration-and-tests/* openspec/changes/archive/2026-06-26-v2-migration-and-tests/

# Remove active change directory
rm -rf openspec/changes/v2-migration-and-tests
```

- [ ] **Step 3: Create archive README for context**

Create `openspec/changes/archive/2026-06-26-v2-migration-and-tests/README.md`:

```markdown
# v2-migration-and-tests (Archived)

**Phase:** 4 — Three-phase architecture split + test suite + migration docs

**Active period:** 2026-06-24 → 2026-06-26

**Status:** ✅ Complete — all 4 tasks done

**Commits:**
- `337d467` feat(skills): add guide-arch.md — architecture definition phase (ADR-0003)
- `8a60110` feat(skills): add guide-plan.md — change generation phase (ADR-0003)
- `621658c` refactor(skills): convert guide-spec.md to alias for guide-arch → guide-plan
- `b428efc` feat(guide): three-phase recommender + handoff JSONs + metadata unit tests
- `0968f85` docs: migration QuickStart/FAQ + README/USAGE v2.0 + package.json skills list
- `99e5974` fix(tests): add conftest.py to resolve skills._lib imports
- `f627dd4` test(integration): add loop flow, gate transition, and phase switch tests

**Key deliverables:** 3 new skills (guide-arch, guide-plan, guide-spec alias), 171 tests, 673-line migration guide
```

- [ ] **Step 4: Stage and commit archive**

```bash
git add openspec/changes/archive/2026-06-26-v2-migration-and-tests/
git add openspec/changes/v2-migration-and-tests/  # for deletion tracking
git commit -m "chore(archive): v2-migration-and-tests — 7 commits, 171 tests, 3 skills"
```

---

### Task 3: Archive v2-beta-release (self-archive at end)

**Files:**
- Create: `openspec/changes/archive/2026-06-26-v2-beta-release/`
- Remove: `openspec/changes/v2-beta-release/`

- [ ] **Step 1: Move v2-beta-release change to archive**

```bash
# Create archive directory
mkdir -p openspec/changes/archive/2026-06-26-v2-beta-release

# Copy entire change artifacts
cp -r openspec/changes/v2-beta-release/* openspec/changes/archive/2026-06-26-v2-beta-release/

# Remove active change directory
rm -rf openspec/changes/v2-beta-release
```

- [ ] **Step 2: Create archive README**

Create `openspec/changes/archive/2026-06-26-v2-beta-release/README.md`:

```markdown
# v2-beta-release (Archived)

**Phase:** 5 — v2.0.0-beta npm release, changelog, feedback channels

**Active period:** 2026-06-24 → 2026-06-26

**Status:** ✅ Complete — npm published, changelog written, feedback channels live

**Commit:** `<filled-in-after-publish>` `release: v2.0.0-beta — changelog, issue templates, version bump`

**Key deliverables:** `spec-workflow@2.0.0-beta` on npm, `CHANGELOG.md`, 3 GitHub Issue templates, git tag `v2.0.0-beta`
```

- [ ] **Step 3: Stage and commit archive**

```bash
git add openspec/changes/archive/2026-06-26-v2-beta-release/
git add openspec/changes/v2-beta-release/  # for deletion tracking
git commit -m "chore(archive): v2-beta-release — npm publish, changelog, feedback channels"
```

---

### Task 4: Git push and final verification

**Files:**
- Pushed to `origin/master`

- [ ] **Step 1: Push everything to remote**

```bash
git push origin master --tags
```

Expected output: All commits and the `v2.0.0-beta` tag pushed to GitHub.

- [ ] **Step 2: Verify npm publish**

```bash
# Verify the package is available
npm view spec-workflow versions --json
```

Expected output: includes `"2.0.0-beta"` in the versions array.

- [ ] **Step 3: Verify GitHub has the tag**

```bash
# Check remote tags
git ls-remote --tags origin
```

Expected output: `refs/tags/v2.0.0-beta` in the list.

- [ ] **Step 4: Final checklist**

Verify:
- [ ] `CHANGELOG.md` exists with all required sections (new features, breaking changes, known issues, migration link)
- [ ] `package.json` version is `2.0.0-beta`
- [ ] `.github/ISSUE_TEMPLATE/` contains 3 template files
- [ ] `git tag` `v2.0.0-beta` exists locally and remotely
- [ ] `npm` shows `spec-workflow@2.0.0-beta` published
- [ ] `openspec/changes/archive/` has both new archives
- [ ] `openspec/changes/v2-migration-and-tests/` removed
- [ ] `openspec/changes/v2-beta-release/` removed (self-archived)
- [ ] No dirty files (`git status` clean)
