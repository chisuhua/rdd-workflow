# Implementation Tasks: add-strict-human-approval-for-cross-repo-changes

## Phase 1: Core Approval Gate

- [x] **Task 1.1**: Modify `skills/guide-design/scripts/approve_proposal.sh` to detect `**分类**: cross-repo-federation` proposals by reading `roadmap-meta.yaml.category`
  - Add function `detect_cross_repo_category()` that reads category from `roadmap-meta.yaml`
  - When category is `cross-repo-federation` and `--auto-accept` is passed, exit with code 3 and display blocking message

- [x] **Task 1.2**: Add `RDDF_REQUIRE_HUB_APPROVAL` environment variable handling
  - Check `RDDF_REQUIRE_HUB_APPROVAL=yes` in `approve_proposal.sh`
  - When set, require `--manual` flag and valid `--hub-issue` argument for cross-repo proposals

- [x] **Task 1.3**: Implement interactive stdin prompt for `--manual` mode
  - Use `read -s` to read GitHub username without echo
  - Display prompt: `🔐 检测到 cross-repo 提案,需要人工确认\n请输入你的 GitHub 用户名 (会记录到 audit log):`
  - Record username in audit log entry

## Phase 2: Hub Status Verification

- [x] **Task 2.1**: Create `skills/_lib/cross_repo_audit.py` for audit log management
  - Implement `append_audit_log_entry()` function with JSON Lines format
  - Validate all required fields: timestamp, proposal_name, hub_issue, approver, decision
  - Write to `.rddf/state/.cross-repo-audit.jsonl` in append mode

- [x] **Task 2.2**: Implement Hub Issue status recheck before approval
  - Add `fetch_hub_issue_status()` function that calls GitHub API
  - Reject approval if status is not `Approved`
  - Fail-closed on network errors (exit code 4)

- [x] **Task 2.3**: Add Hub Issue validation with `--hub-issue` argument
  - Parse `org/rdd-hub#42` format into owner/repo/number
  - Call GitHub API to fetch current issue status
  - Compare against expected Approved status

## Phase 3: Design Gate Integration

- [x] **Task 3.1**: Modify `skills/guide-design/scripts/design_content_review.sh` for cross-repo category
  - Add `review_cross_repo_proposal()` function
  - Verify Hub Issue reference exists in proposal
  - Verify Hub Issue is accessible and in Approved status
  - Assign explicit human reviewer

- [x] **Task 3.2**: Ensure `STRICT_DESIGN_GATE=yes` blocks design-done for unapproved cross-repo proposals
  - Read all cross-repo proposals from `openspec/changes/*/roadmap-meta.yaml`
  - Check each proposal's Hub Issue status
  - Block design-done with exit code 1 if any Hub Issue is not Approved

## Phase 4: Schema Extension

- [x] **Task 4.1**: Extend `.openspec.yaml` schema to include `cross_repo_review.required`
  - Add validation in `openspec validate` for the new field
  - Document the field in change artifacts

- [x] **Task 4.2**: Update `skills/_lib/schemas/` if applicable
  - Add `cross_repo_review` object schema with `required: boolean`
  - Ensure backward compatibility with existing changes

## Phase 5: Documentation

- [x] **Task 5.1**: Update README.md with §跨项目协同 section
  - Document "AI 不能跨项目自动批准" principle
  - Explain `RDDF_REQUIRE_HUB_APPROVAL` usage
  - Provide example commands for manual approval

- [x] **Task 5.2**: Create `docs/strict-gate-boundary.md` with RDDF_REQUIRE_* boundary clarification
  - Explain `STRICT_DESIGN_GATE` vs `RDDF_REQUIRE_HUB_APPROVAL` distinction
  - Document Hub-side `STRICT_HUB_APPROVAL=no` escape (requires PR)

## Phase 6: Testing

- [x] **Task 6.1**: Write unit test `test_cross_repo_auto_block`
  - Mock a cross-repo proposal scenario
  - Verify `--auto-accept` is blocked with exit code 3
  - Assert blocking message is displayed

- [x] **Task 6.2**: Write unit test `test_gate_detect_unapproved_hub_issue`
  - Set `STRICT_DESIGN_GATE=yes`
  - Mock Hub Issue in RFC status
  - Verify design-done gate fails

- [x] **Task 6.3**: Write unit test `test_manual_confirmation_flow`
  - Invoke `--manual` mode
  - Mock stdin input for username
  - Verify audit log entry is written

- [x] **Task 6.4**: Write unit test `test_audit_log_write`
  - Create audit log entry
  - Verify all required fields present in `.cross-repo-audit.jsonl`
  - Verify JSON Lines format (one entry per line)

- [x] **Task 6.5**: Write unit test `test_hub_state_recheck_blocks_stale_approval`
  - Mock previously Approved but now RFC Hub Issue status
  - Verify approval is blocked
  - Assert "Hub Issue 状态已变更" message

## Verification Criteria

- [x] All 9 acceptance criteria from proposal.md are satisfied
- [x] `openspec validate add-strict-human-approval-for-cross-repo-changes` passes with no errors
- [x] No Spoke-side bypass paths exist (verified by code review)
- [x] Unit tests cover all 5 key paths (auto-block, gate-detect, manual-confirm, audit-write, hub-state-recheck)
