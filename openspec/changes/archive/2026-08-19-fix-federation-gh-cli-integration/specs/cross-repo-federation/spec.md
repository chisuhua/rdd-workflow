## ADDED Requirements

### Requirement: gh CLI Compatibility for Hub Issue Operations

`gh_hub_client.py` MUST work against `gh` CLI v2.50+ (where `gh issue create --json` is unsupported) without breaking unit-test mocks that emulate `--json` output.

#### Scenario: create_issue parses stdout URL when gh CLI lacks --json flag
**WHEN** the user runs `rddf report-issue --category=rfc` against a real GitHub repository using gh CLI <v2.50
**THEN** `gh_hub_client.create_issue` MUST parse the stdout URL `https://github.com/<owner>/<repo>/issues/<N>` to extract `number` and `html_url`
**AND** the returned dict MUST match the JSON-fallback contract (`{"number": int, "html_url": str}`)

#### Scenario: create_issue preserves JSON fallback for unit tests
**WHEN** the unit test `tests/unit/test_gh_hub_client.py::test_create_issue_builds_correct_payload` mocks subprocess.run with stdout `{"number": 42, "html_url": "..."}`
**THEN** `gh_hub_client.create_issue` MUST detect JSON stdout and return the parsed dict without falling back to URL parsing

#### Scenario: get_issue_status uses correct field name stateReason
**WHEN** the user runs `rddf watch-hub --once` which calls `gh issue view --json state,stateReason,title`
**THEN** the returned dict MUST contain `stateReason` (camelCase), not `state_reason`
**AND** watch-hub's check `s.get("stateReason") == "COMPLETED"` MUST match

#### Scenario: batch_get_issues_status iterates via REST for reliability
**WHEN** watch-hub polls N pending issues
**THEN** `batch_get_issues_status` MUST iterate `get_issue_status` for each number (O(N) REST calls)
**AND** MUST NOT use the unsupported GraphQL `IssueFilters { numbers: [...] }` filter

### Requirement: watch-hub Polling Without Local Approval

`watch_hub.py` MUST poll Hub Issue statuses and update local `.cross-repo-pending.json` without invoking `approve_proposal.sh` (which is the human-approval path per ADR-0031).

#### Scenario: watch-hub updates pending on closed+COMPLETED
**WHEN** a Hub Issue referenced in `.cross-repo-pending.json` has state `CLOSED` and stateReason `COMPLETED`
**THEN** `watch_hub.py --once` MUST mark the corresponding local pending entry status as `approved`
**AND** MUST NOT invoke `approve_proposal.sh` (which would attempt to approve a non-existent `hub-{N}` proposal)

#### Scenario: watch-hub tolerates label creation warnings
**WHEN** `gh issue create` fails to add a label because the label does not exist in Hub
**THEN** the Issue MUST still be created
**AND** the URL MUST still be captured from stdout
**AND** only a warning is emitted (not a fatal error)
