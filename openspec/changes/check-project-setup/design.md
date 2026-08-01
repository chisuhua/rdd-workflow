## Context

`AGENTS.md` already encodes the runtime/tracked contract for `.rddf/*` directories, and rdd-workflow's own tests enforce `.rddf/state/` in `.gitignore`. However, the contract is not enforced for downstream projects: `guide-ship` hard-blocks when required artifacts are not committed, while `guide` only soft-suggests adding ignore rules. This design centralizes the validation in one bash helper so both hard and soft gates consume the same issue schema and users get consistent, actionable output.

## Goals / Non-Goals

**Goals:**
- Provide a single source of truth for project-setup validation: `skills/_lib/check_project_setup.sh`.
- Hard-block `guide-arch` Phase 1 when error-severity setup issues are detected.
- Soft-present setup issues in the `guide` recommender and `INSTALL.md` without blocking.
- Make all six checks testable via `bats`.

**Non-Goals:**
- Automatically modify `.gitignore`; the helper only emits `fix_command` strings.
- Add a new user-facing skill or menu item.
- Change `guide-ship`'s existing COMMIT GATE behavior.
- Introduce a Python helper; gitignore checks are text-only and align with existing bash helpers.

## Decisions

- **Bash over Python**: `arch_env_check.sh` and `scan-state.sh` are bash; keeping the helper in bash avoids mixing runtimes and keeps startup cost low.
- **JSON stdout**: The helper outputs a JSON array matching the `WT_ISSUES_JSON` schema, which both bash consumers (via `jq`) and Python consumers can parse uniformly.
- **Severity levels**: `error` for missing required ignore rules or missing `.gitignore`; `safe_auto_fix` for large untracked directories; `info` for passing checks or optional notices.
- **Discovery-first gitignore matching**: Prefer exact `.rddf/state/`, `.rddf/wt/`, and `.rddf/plans/` patterns; fall back to `.rddf/` to reduce false negatives in custom layouts.
- **Large-untracked threshold**: Report top-level untracked directories larger than 10MB as `safe_auto_fix`, not `error`, because build artifact names vary by project.

## Risks / Trade-offs

- [Risk] Simple grep/awk patterns may miss custom glob-based `.gitignore` rules → Mitigation: fallback to `.rddf/` directory ignore and surface the matched pattern in `detail`.
- [Risk] The new gate will break existing projects that lack ignore rules → Mitigation: this is intentional; the gate prints exact `fix_command` strings and exits before any state is written.
- [Risk] Repeated calls in hot paths could add latency → Mitigation: the helper runs only at workflow entry points (`guide-arch`, `guide`, `INSTALL`) and avoids recursion; target runtime is < 50ms.

## Migration Plan

N/A — this is an additive setup check. Existing projects need only run the printed `fix_command` once when `guide-arch` first fails.

## Open Questions

None.
