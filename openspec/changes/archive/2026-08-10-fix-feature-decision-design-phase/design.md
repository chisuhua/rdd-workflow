## Context

`add-proposal-deps-and-features` (P1, archived commit 2a15ba9) defined `**特性**` as the design-time feature tag, promising "feature 标签自动写入 iteration.json 的 parent_feature". But this contract was never wired up:
- `approve_proposal.sh` only reads `PARENT_FEATURE` env var
- `propose_change.py::create_skeleton_change` only accepts `parent_feature` as function param

Users writing `**特性**: wave-core` in `improvements/<name>.md` saw no effect; `feature` view did not recognize it.

## Decision

Per ADR-0022 (manual_deps) and ADR-0025 (design-proposal-creation) — proposal 头部字段 is the design-stage decision carrier and should be respected by downstream paths. `**特性**` is the feature-attribution design decision and should be auto-read:

1. **`approve_proposal.sh`**: parse `**特性**` header as `PARENT_FEATURE` fallback (env var wins)
2. **`create_skeleton_change`**: when `parent_feature=None`, parse `**特性**` from improvements/<name>.md (param wins)
3. **Python regex** uses `[ \t]*` not `\s*` to avoid cross-line latent bug

**Out of Scope**:
- `**类型**` / `**阶段**` / `**分类**` parsing `\\s*` latent bug (independent)
- `iteration.json` write path missing `parent_feature` (separate)
- `guide-design` phase feature preview UX (B-scheme; post-stable)

## Implementation (Retroactive)

Implementation already landed in earlier session via commits:
- `27dbac7 fix(guide-design): read **特性** from improvements head into PARENT_FEATURE`
- `3e633dc fix(propose): fallback to **特性** field for parent_feature`

Tests added in same commits:
- `tests/integration/test_approve_proposal_parent_feature.bats` (3 cases)
- `tests/unit/test_propose_change_parent_feature.py` (3 cases)

All acceptance criteria verified post-implementation: 1272 pytest + 174 integration + 58 bats baseline all green.

## Retroactive Archive Notes

This change artifacts dir created 2026-08-10 to retroactively formalize the work. No code changes in this archive. Future readers should consult commits `27dbac7` + `3e633dc` for actual implementation.
