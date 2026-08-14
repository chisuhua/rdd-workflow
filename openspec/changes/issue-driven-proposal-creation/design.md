## Context

The rdd-workflow v2.1+ has 2 paths to create a proposal: `add-improve` (brainstorm flow) and `propose` (gap-scan flow). Neither path starts from a GitHub issue. Users with active issue backlogs (especially maintainers of rdd-workflow itself) have to manually transcribe issue title/body into a `.rddf/improvements/<name>.md` file.

This change adds a third path: `add-improve --from-issue <N>` that fetches an issue from the current project's GitHub repo and scaffolds a proposal. The change also fixes a latent bug in `_lib/close_issues.py:180` where the archive comment hardcodes "Fixed in rdd-workflow" — this would write incorrect attribution to third-party repos.

## Goals / Non-Goals

**Goals:**
- Add `add-improve --from-issue <N>` mode that scaffolds a proposal from a GitHub issue.
- Implement 3-step repo detection fallback (env > gh repo view > git remote parse).
- Implement dedup against existing `.rddf/improvements/*.md` and `openspec/changes/*/roadmap-meta.yaml`.
- Implement slug-collision handling with `-i<N>` suffix.
- Fix `_lib/close_issues.py:180` to use repo-neutral language.
- Add unit tests for `gh_repo_detect.py` and integration tests for `from-issue`.

**Non-Goals:**
- Reload `rddf issue list/show` namespace (out of scope per proposal).
- Add label-based filtering, batch multi-select, or closed-issue sync (v2.2+ scope).
- Add a new CLI dispatcher (skill-only MVP).
- Modify ADR-0027 §5 triage menu code path.
- Detect "is rdd-workflow self" — use single pool strategy (`.rddf/improvements/` is always the entry).
- Reuse `RDDF_REPORT_GH_REPO` env (semantic conflict with ADR-0027 reporter).

## Decisions

### 1. Repo detection: env > gh > git remote

Use a 3-step priority chain. Explicit env override (`RDDF_PROPOSAL_GH_REPO`) is highest priority because it allows fork/override scenarios. `gh repo view` is second because it correctly handles auth state. `git remote get-url origin` is the fallback for minimal installations.

**Alternatives considered:**
- `gh repo view` only: Rejected — fails for fork/override scenarios.
- `git remote` only: Rejected — fails for non-git-source projects.
- Hard-coded `chisuhua/rdd-workflow` as fallback: Rejected — explicitly forbidden in MUST NOT.

### 2. Scaffold mode: follow from-roadmap pattern

Use the existing `from-roadmap` bash+Python+env-var pattern (`skills/add-improve/scripts/from_roadmap.{sh,py,env.py}`). This DRY convention avoids divergent scaffold implementations.

**Alternatives considered:**
- New shared scaffolding library: Rejected — premature abstraction for 3 modes.
- Inline bash heredoc: Rejected — Oracle C1 security risk.

### 3. Dedup locations: two places

Scan both `.rddf/improvements/*.md` frontmatter and `openspec/changes/*/roadmap-meta.yaml::issue_refs`. The first catches pre-proposal state, the second catches post-approval state.

**Alternatives considered:**
- Single source of truth (e.g., only improvements frontmatter): Rejected — loses pre-approval tracking.
- Trailing `## 已映射` section in proposal.md: Rejected — breaks the standard 5-section format.

### 4. close_issues.py fix: repo-neutral comment

Replace the hardcoded "Fixed in rdd-workflow v{version}" with a parameterized message that uses `change_name` and `(repo_name, version)` derived from the change context.

**Alternatives considered:**
- Drop the comment entirely: Rejected — useful for tracking purposes.
- Keep hardcoded and skip when gh_repo != upstream: Rejected — adds complexity for marginal benefit.

## Risks / Trade-offs

- **Risk**: `gh repo view` subprocess hangs in network-restricted environments. **Mitigation**: 10s timeout with explicit error.
- **Trade-off**: Issue body truncation at 4k chars may lose context for very long issues. **Mitigation**: Truncation preserves reference URL.
- **Risk**: Slug-collision prefix `-i<N>` might surprise users expecting `-N`. **Mitigation**: Document in scaffold's README section.
- **Risk**: `-i<N>` suffix conflict with `add-improve --from-issue` re-runs. **Mitigation**: Dedup check runs before slug generation.
