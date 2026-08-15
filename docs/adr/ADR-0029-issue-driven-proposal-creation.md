# ADR-0029: Issue-Driven Proposal Creation

> **状态**: 已采纳
> **日期**: 2026-08-15
> **决策者**: sisyphus

## Context

rdd-workflow v2.1+ has 2 paths to create a proposal: `add-improve` (brainstorm flow) and `propose` (gap-scan flow). Neither path starts from a GitHub issue. Users with active issue backlogs (especially maintainers of rdd-workflow itself) have to manually transcribe issue title/body into a `.rddf/improvements/<name>.md` file.

This change adds a third path: `add-improve --from-issue <N>` that fetches an issue from the current project's GitHub repo and scaffolds a proposal. The change also fixes a latent bug in `_lib/close_issues.py:180` where the archive comment hardcodes "Fixed in rdd-workflow" — this would write incorrect attribution to third-party repos.

## Decision

### 1. Repo detection: env > gh > git remote (3-step fallback)

Use a 3-step priority chain. Explicit env override (`RDDF_PROPOSAL_GH_REPO`) is highest priority because it allows fork/override scenarios. `gh repo view` is second because it correctly handles auth state. `git remote get-url origin` is the fallback for minimal installations.

**Alternatives considered:**
- `gh repo view` only: Rejected — fails for fork/override scenarios.
- `git remote` only: Rejected — fails for non-git-source projects.
- Hard-coded `chisuhua/rdd-workflow` as fallback: Rejected — explicitly forbidden in MUST NOT.

### 2. Scaffold mode: follow from-roadmap pattern

Use the existing `from-roadmap` bash+Python+env-var pattern (3-file split: `from_roadmap.sh` + `from_roadmap.py` + `from_roadmap.env.py`). This DRY convention avoids divergent scaffold implementations.

**Alternatives considered:**
- New shared scaffolding library: Rejected — premature abstraction for 3 modes.
- Inline bash heredoc: Rejected — Oracle C1 security risk.

### 3. Dedup locations: two places

Scan both `.rddf/improvements/*.md` frontmatter and `openspec/changes/*/roadmap-meta.yaml::issue_refs`. The first catches pre-proposal state, the second catches post-approval state.

**Alternatives considered:**
- Single source of truth (e.g., only improvements frontmatter): Rejected — loses pre-approval tracking.
- Trailing `## 已映射` section in proposal.md: Rejected — breaks the standard 5-section format.

### 4. close_issues.py fix: repo-neutral comment

Replace the hardcoded "Fixed in rdd-workflow v{version}" with a parameterized message that uses `repo_name` derived from `gh_repo` (e.g., `my-project` instead of `rdd-workflow`).

**Alternatives considered:**
- Drop the comment entirely: Rejected — useful for tracking purposes.
- Keep hardcoded and skip when gh_repo != upstream: Rejected — adds complexity for marginal benefit.

## Consequences

### Positive
- Bridges the gap between GitHub issues and `.rddf/improvements/` proposals.
- Enables rdd-workflow self-dogfooding (maintainers can convert their own issues).
- Fixes latent bug in `close_issues.py` that would write incorrect attribution to third-party repos.
- New `gh_repo_detect.py` is reusable for ADR-0027 triage future iterations.

### Negative
- Requires `gh` CLI to be installed and authenticated (with clear error messages).
- Adds 3 new env-vars (`ADD_IMPROVE_FROM_ISSUE`, `ADD_IMPROVE_GH_REPO`, `ADD_IMPROVE_ISSUE_TITLE`, `ADD_IMPROVE_ISSUE_BODY`).
- Increases the surface area of `add-improve` scaffolding (3 modes: free / from-roadmap / from-issue).

### Neutral
- Detected repo is **always** the current project's repo (no upstream fallback). This is intentional to prevent misattribution.

## References

- ADR-0025 (move-proposal-creation-to-design) — Phase 2 menu structure
- ADR-0027 §5 (issue-reporting) — scope distinction (triage vs from-issue)
- ADR-0027 §7 (gh_repo schema) — schema field reused in `.rddf/improvements/<name>.md`
- ADR-0026 (rddf CLI naming) — namespace conventions for `rddf issue` command
