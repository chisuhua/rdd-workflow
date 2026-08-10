# Tasks — fix-feature-decision-design-phase

> **Retroactive archive** (2026-08-10): All tasks below completed in earlier session.
> See implementation commits. This archive formalizes the work for proper lifecycle tracking.

## 1. approve_proposal.sh — parse `**特性**` as PARENT_FEATURE fallback

- [x] 1.1 Parse `**特性**` header in approve_proposal.sh
- [x] 1.2 Env var `PARENT_FEATURE` still wins
- [x] 1.3 bash implementation: commit `27dbac7`

## 2. propose_change.py — fallback to `**特性**` when param=None

- [x] 2.1 When `parent_feature=None`, parse `**特性**` from improvements/<name>.md
- [x] 2.2 Param still wins when both present
- [x] 2.3 Python regex uses `[ \t]*` not `\s*` (avoid cross-line latent bug)
- [x] 2.4 Python implementation: commit `3e633dc`

## 3. Tests — bats integration (3 cases)

- [x] 3.1 `tests/integration/test_approve_proposal_parent_feature.bats` — 3 cases
- [x] 3.2 Cases: env wins / field fallback / empty field
- [x] 3.3 All green

## 5. Tests — Python unit (3 cases)

- [x] 5.1 `tests/unit/test_propose_change_parent_feature.py` — 3 cases
- [x] 5.2 Cases: explicit param wins / field fallback / empty → null
- [x] 5.3 All green

## 6. Regression

- [x] 6.1 Full `./test.sh --full --regression` — all green
- [x] 6.2 1272 pytest + 174 integration + 58 bats baseline — all pass

## 7. Acceptance criteria

- [x] 7.1 `tests/integration/test_approve_proposal_parent_feature.bats` 3 cases 全绿
- [x] 7.2 `tests/unit/test_propose_change_parent_feature.py` 3 cases 全绿
- [x] 7.3 Existing test_approve_proposal_*.bats 全部仍绿
- [x] 7.4 Existing tests/unit/test_propose_change*.py 全部仍绿
- [x] 7.5 Python unit 1272 全部仍绿
- [x] 7.6 bats 全量无新增失败
- [x] 7.7 `add-proposal-deps-and-features` 的 feature 标签兑现
