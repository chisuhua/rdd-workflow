# add-rdd-hub-cross-repo-federation Tasks

## Implementation Tasks

- [x] Create `skills/_lib/gh_hub_client.py` - GitHub Hub API client (GraphQL + REST)
  - Implement `create_issue()` for RFC Issue creation
  - Implement `get_issue_status()` for status polling
  - Implement `batch_get_issues_status()` for GraphQL batch queries
  - Implement `check_rate_limit()` and respect `Retry-After` headers

- [x] Create `skills/_lib/cross_repo_state.py` - Pending state manager
  - Implement `read_pending_state()` / `write_pending_state()`
  - Implement `add_pending_entry()` / `update_pending_entry()` / `remove_pending_entry()`
  - Implement `validate_pending_schema()` against JSON schema
  - Implement atomic write with temp file + rename

- [x] Create `skills/_lib/schemas/cross-repo-pending-schema.json` - JSON Schema
  - Define `entries` array with required: `hub_issue_url`, `gate_type`, `expected_status`, `created_at`
  - Define optional: `contract_path`, `stakeholders`, `title`, `status`
  - Add `status` enum: `pending | approved | rejected | superseded`

- [x] Create `skills/report-issue/scripts/report_issue_rfc.py` - RFC Issue creation
  - Parse `--category=rfc` flag
  - Map `--stakeholders`, `--gate`, `--contract-impact` to Project V2 fields
  - Create Issue via `gh_hub_client.create_issue()`
  - Add pending entry to `.rddf/state/.cross-repo-pending.json`
  - Support `--dry-run` mode

- [x] Create `scripts/approve_proposal.sh` - Local/manual approval
  - Accept arguments: `$1` (change name), `$2` (approval type), `$3` (approver), `$4` (note)
  - Update pending entry `status` to `approved`
  - Log approval with timestamp

- [x] Create `skills/sync-hub/scripts/sync_hub.py` - Contract sync command
  - Parse `--contract <path>` argument
  - Build Hub URL from `rdd-hub/contracts/<path>`
  - Download and save to `openspec/specs/<converted-path>/spec.md`
  - Implement idempotency check (hash comparison)
  - Implement offline fallback to cache
  - Support `--dry-run` mode

- [x] Create `skills/watch-hub/scripts/watch_hub.py` - One-time polling command
  - Parse `--once --owner=<org/hub> [--filter <expr>]`
  - Read pending entries from `.rddf/state/.cross-repo-pending.json`
  - Batch fetch all Issue statuses via GraphQL
  - For each Issue that changed to `Approved`:
    - Call `approve_proposal.sh`
    - Update pending entry to `status: approved`
  - Support `--dry-run` mode
  - Implement offline graceful degradation

- [x] Modify `skills/execute/scripts/execute_step7.py` - Add RFC mode support
  - Add `--rfc` flag handling
  - Pass RFC-specific env vars to `gh_hub_client`

- [x] Modify `skills/_lib/gh_repo_detect.py` - Add Hub repo detection
  - Add `detect_hub_repo()` function
  - Use `RDDF_REPORT_GH_REPO` or fallback to configured Hub

- [x] Add design-done gate integration in `guide-design/scripts/design_done_gate.py`
  - Check for pending RFC Issues in `.rddf/state/.cross-repo-pending.json`
  - Query Hub for current Issue status via `gh_hub_client`
  - Hard block if any pending Issue status is not `Approved`
  - Support `SKIP_HUB_CHECK=true` override

- [x] Update `README.md` - Add §跨项目协同 documentation
  - Document `rddf report-issue --category=rfc` usage
  - Document `rddf sync-hub --contract <path>` usage
  - Document `rddf watch-hub --once --owner=<org/hub>` usage
  - Document `.rddf/state/.cross-repo-pending.json` structure
  - Document `SKIP_HUB_CHECK=true` emergency override

## Test Tasks

- [x] Create unit tests for `gh_hub_client.py`
  - Test `create_issue()` with mock GitHub API
  - Test `get_issue_status()` parsing
  - Test `batch_get_issues_status()` GraphQL query building
  - Test rate limit handling

- [x] Create unit tests for `cross_repo_state.py`
  - Test read/write pending state
  - Test schema validation
  - Test atomic write behavior
  - Test entry CRUD operations

- [x] Create bats integration tests for `sync-hub`
  - Test `--dry-run` output
  - Test idempotency
  - Test offline fallback

- [x] Create bats integration tests for `watch-hub --once`
  - Test `--dry-run` output
  - Test approval action triggering
  - Test offline graceful degradation
  - Test filter parsing

- [x] Create bats integration tests for `report-issue --category=rfc`
  - Test RFC Issue creation
  - Test pending entry creation
  - Test Project V2 field mapping
  - Test `--dry-run` mode

- [x] Create bats integration test for design gate integration
  - Test gate blocks when RFC pending
  - Test gate passes when RFC approved
  - Test `SKIP_HUB_CHECK=true` override
