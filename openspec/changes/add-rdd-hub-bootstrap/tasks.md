# add-rdd-hub-bootstrap: Implementation Tasks

## Implementation Tasks

- [ ] **T1: Create `skills/rdd-hub-bootstrap/` directory structure**
  - Create `skills/rdd-hub-bootstrap/SKILL.md` — skill documentation with usage instructions
  - Create `skills/rdd-hub-bootstrap/scripts/` directory for init script
  - Create `skills/rdd-hub-bootstrap/templates/` directory for reusable assets
  - Create `skills/rdd-hub-bootstrap/templates/contracts/` subdirectory
  - Create `skills/rdd-hub-bootstrap/templates/workflows/` subdirectory
  - Create `skills/rdd-hub-bootstrap/templates/mcp-protocols.md` — MCP protocol documentation template

- [ ] **T2: Implement `init_hub.sh` core script**
  - Add argument parsing for `--org`, `--repo`, `--dry-run` flags
  - Add `set -euo pipefail` and `trap cleanup EXIT` for safe error handling
  - Implement `log() { echo "$(date -Iseconds) $*" >> rdd-hub-bootstrap.log; }`
  - Implement `check_auth()` — verify `gh auth status` passes, print login instruction if not
  - Implement `hub_repo_exists()` — check via `gh repo view {org}/{repo}` with 0/1 exit
  - Implement `create_hub_repo()` — `gh repo create {org}/{repo} --public --clone` if not exists
  - Implement `create_directory_structure()` — `mkdir -p` for contracts/, global-adr/, .github/workflows/, docs/ with .gitkeep files

- [ ] **T3: Implement Projects V2 board configuration**
  - Implement `board_exists()` — check via `gh project list --owner {org}` for "RDD Cross-Repo Sync"
  - Implement `create_project_board()` — `gh project create --name "RDD Cross-Repo Sync" --owner {org}` if not exists
  - Implement `configure_fields()` — create six custom fields via `gh project field-create`:
    - Status (single-select, with options: Backlog, In Progress, Review, Done)
    - Initiator (single-select, text)
    - Stakeholders (multi-select, text)
    - Review-Progress (single-select, with options: Pending, Approved, Changes Requested)
    - RDD-Gate (single-select, with options: Arch, Plan, Ship, Done)
    - Contract-Impact (single-select, with options: Low, Medium, High, Critical)
  - Skip board creation if board already exists (idempotency)

- [ ] **T4: Implement workflow template deployment**
  - Implement `deploy_workflow_templates()`:
    - Copy `templates/workflows/contract-lint.yml` placeholder to `.github/workflows/contract-lint.yml`
    - Copy `templates/workflows/stale-rfc.yml` placeholder to `.github/workflows/stale-rfc.yml`
    - Use `cp -i` for interactive overwrite prompt; skip if destination newer than source
  - Create placeholder workflow content (minimal `runs-on: ubuntu-latest` with `echo "Placeholder"` steps)

- [ ] **T5: Implement template assets**
  - Create `templates/contracts/README.md` —说明 cross-project contract conventions
  - Create `templates/contracts/example-openapi.yaml` — minimal OpenAPI 3.0 example with one path
  - Create `templates/mcp-protocols.md` — MCP protocol documentation template with sections: Overview, Message Types, Cross-Repo Flow, Error Handling

- [ ] **T6: Implement idempotency and dry-run modes**
  - Add `--dry-run` flag: when set, print each operation that would be performed without executing any `gh` commands or `git push`
  - Add existence checks before every state-changing operation (repo, board, fields, templates)
  - Log each skip with `REASON=already_exists`
  - Ensure `init_hub.sh` can be re-run safely on an already-initialized Hub

- [ ] **T7: Implement audit logging**
  - Ensure `rdd-hub-bootstrap.log` is created in CWD on every run
  - Log format: `TIMESTAMP OPERATION=VALUE STATUS=VALUE [REASON=VALUE]`
  - Log all three scenarios: create, idempotent-update, dry-run
  - Append to log (do not overwrite) if run multiple times

- [ ] **T8: Create usage documentation**
  - Create `docs/rdd-hub-bootstrap.md` with:
    - Prerequisites (`gh` CLI installation, `gh auth login`, Org membership)
    - Step-by-step initialization guide with annotated screenshots description
    - Dry-run mode explanation and example output
    - Idempotency explanation and example
    - Troubleshooting section (auth failures, permission errors, network issues)
    - Relationship to ADR-0030 and downstream proposals

- [ ] **T9: Write integration tests**
  - Create `tests/integration/test_rdd_hub_bootstrap.bats` with five test cases:
    - `test_create_new_hub_repo` — verifies repo creation path via dry-run
    - `test_idempotent_existing_hub` — verifies skip path via dry-run
    - `test_dry_run_no_api_calls` — verifies no `gh api` invocations in dry-run mode
    - `test_fields_config` — verifies six field names are configured
    - `test_workflow_deploy` — verifies two workflow files are in deployment list
  - All tests run against `--dry-run --org fake-org --repo fake-hub` (no real API calls)

- [ ] **T10: Create Hub directory structure inside skill package**
  - Create `skills/rdd-hub-bootstrap/templates/global-adr/README.md` — placeholder for global ADR files

---

## Verification Checklist

- [ ] `init_hub.sh --help` displays usage with all flags documented
- [ ] `bash init_hub.sh --dry-run --org test-org --repo test-hub` exits 0 with simulated operations logged
- [ ] Re-running `init_hub.sh --dry-run` on same org/repo shows all skipped operations
- [ ] `bats tests/integration/test_rdd_hub_bootstrap.bats` passes all 5 test cases
- [ ] `docs/rdd-hub-bootstrap.md` contains prerequisites, step-by-step guide, troubleshooting
- [ ] All 6 Projects V2 field names appear in board configuration logic
- [ ] Audit log format matches `TIMESTAMP OPERATION=VALUE STATUS=VALUE` specification
