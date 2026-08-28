# add-pre-commit-proposal-quality-check — Implementation Tasks

## Implementation

- [x] Create `skills/guide-design/scripts/proposal_pre_commit_check.sh` pre-commit quality gate for `.rddf/improvements/*.md` (6 structural criteria: Why / What Changes / Acceptance >=3 boxes / ADR ref / >=2 MUST / >=1 MUST NOT)
- [x] Support both canonical English headers and repo Chinese 5-section aliases (架构依据/范围/验收标准/技术约束)
- [x] Provide `--all` batch mode over all `.rddf/improvements/*.md` as the manual pre-commit check command
- [x] Provide `SKIP_PROPOSAL_QUALITY_CHECK=yes` emergency bypass

## Tests

- [x] Write `tests/integration/test_pre_commit_proposal_quality.bats` with 5 integration tests (high-quality PASS / missing Why FAIL / <3 checkboxes FAIL / missing ADR FAIL / missing MUST NOT FAIL)
- [x] Verify all 5 bats tests pass (`bats tests/integration/test_pre_commit_proposal_quality.bats`)
