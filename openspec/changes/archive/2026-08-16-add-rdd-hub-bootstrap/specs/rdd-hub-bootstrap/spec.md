# add-rdd-hub-bootstrap: Specifications

## ADDED Requirements

### Requirement: Hub Repo Initialization Skill

The `rdd-hub-bootstrap` skill **SHALL** provide a引导式 initialization experience for creating and configuring a new Hub repository.

**Rationale:** ADR-0030 establishes Hub-and-Spoke federation; all Step 2-6 implementation proposals depend on `rdd-hub` existing. This skill bridges the gap between architectural decision and operational setup.

#### Scenario: Skill invocation with required flags
- **WHEN** a user invokes `skill_use("rdd-hub-bootstrap")` followed by `init_hub.sh --org "my-org" --repo "rdd-hub"`
- **THEN** the script creates the GitHub repository if absent, configures Projects V2 board, deploys directory structure and workflow templates, and reports success

#### Scenario: Dry-run mode skips API calls
- **WHEN** a user invokes `init_hub.sh --dry-run --org "fake-org" --repo "fake-hub"`
- **THEN** the script simulates all operations, prints the action plan, and exits 0 without making any GitHub API calls

#### Scenario: Idempotent update of existing Hub Repo
- **WHEN** a user runs `init_hub.sh --org "my-org" --repo "rdd-hub"` against an already-initialized repository
- **THEN** the script detects existing resources, updates only missing workflow templates, skips already-configured Projects V2, and reports idempotent completion

---

### Requirement: Hub Directory Structure Deployment

The initialization **SHALL** create a consistent, versioned directory structure inside the Hub repository.

**Directory Layout:**
- `contracts/` — Cross-project API contracts (OpenAPI specs, Schema definitions)
- `global-adr/` — Architecture decisions spanning multiple repositories
- `.github/workflows/` — CI/CD templates for cross-repo coordination
- `docs/` — Hub documentation and onboarding guides

#### Scenario: Directory structure creation
- **WHEN** `init_hub.sh` executes successfully
- **THEN** all four top-level directories are present in the Hub repository with appropriate `.gitkeep` or template files

---

### Requirement: GitHub Projects V2 Configuration

The skill **SHALL** configure a "RDD Cross-Repo Sync" Kanban board with six specific fields.

**Required Fields:**
| Field Name | Type | Purpose |
|------------|------|---------|
| Status | Single-select | Pipeline stage (Backlog, In Progress, Review, Done) |
| Initiator | Single-select | Which spoke repository initiated this item |
| Stakeholders | Multi-select | Teams/persons affected by this item |
| Review-Progress | Single-select | Code review status (Pending, Approved, Changes Requested) |
| RDD-Gate | Single-select | Workflow gate status (OpenSpec phase: Arch/Plan/Ship/Done) |
| Contract-Impact | Single-select | Impact level (Low/Medium/High/Critical) |

#### Scenario: Projects V2 board creation
- **WHEN** the Hub repository does not have a Projects V2 board named "RDD Cross-Repo Sync"
- **THEN** `init_hub.sh` creates the board and configures all six custom fields

#### Scenario: Projects V2 skip on existing board
- **WHEN** "RDD Cross-Repo Sync" board already exists
- **THEN** `init_hub.sh` skips Projects V2 configuration and logs the skip

---

### Requirement: Workflow Templates Deployment

The skill **SHALL** deploy placeholder GitHub Actions workflow files for cross-repo coordination.

**Files to Deploy:**
- `contract-lint.yml` — Placeholder workflow for contract change notifications (full implementation in `add-contract-lint-ci-gate` proposal)
- `stale-rfc.yml` — Placeholder workflow for stale RFC cleanup

#### Scenario: Workflow template deployment
- **WHEN** `init_hub.sh` runs against a Hub repository
- **THEN** both workflow files are created in `.github/workflows/` with minimal scaffold content

---

### Requirement: Skill Template Assets

The skill package **SHALL** include reusable template assets for spoke repositories.

**Template Assets:**
- `templates/contracts/` — Example OpenAPI contract files demonstrating cross-repo API conventions
- `templates/workflows/` — GitHub Actions workflow templates for spoke-to-hub integration
- `templates/mcp-protocols.md` — Documentation template for MCP (Model Context Protocol) cross-repo communication

#### Scenario: Template directory population
- **WHEN** `init_hub.sh` completes successfully
- **THEN** `templates/` directory contains all three subdirectories with at least one example file each

---

### Requirement: Audit Logging

All initialization operations **SHALL** be recorded in a log file for traceability.

**Log File:** `rdd-hub-bootstrap.log` in the current working directory

**Logged Events:**
- Timestamp of each operation
- Operation type (repo_create, board_config, dir_deploy, template_copy, etc.)
- Outcome (success, skipped, failed)
- Dry-run indicator if applicable

#### Scenario: Audit log creation
- **WHEN** `init_hub.sh` executes (with or without `--dry-run`)
- **THEN** a log file is created/append with machine-parseable entries for each attempted operation

---

### Requirement: Integration Test Coverage

An integration test suite **SHALL** exercise all critical paths in dry-run mode.

**Test File:** `tests/integration/test_rdd_hub_bootstrap.bats`

**Critical Paths:**
1. `create` — Full initialization flow (new repo)
2. `idempotent` — Re-run against existing repo
3. `dry-run` — Verify no API calls made
4. `fields-config` — Verify six Project V2 fields
5. `workflow-deploy` — Verify template deployment

#### Scenario: bats test execution
- **WHEN** `bats tests/integration/test_rdd_hub_bootstrap.bats` runs
- **THEN** all five test cases pass in dry-run mode, verifying script logic without GitHub API access
