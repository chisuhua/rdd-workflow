# add-rdd-hub-bootstrap: Technical Design

## Context

ADR-0030 establishes a Hub-and-Spoke federation architecture where the Hub repository (`rdd-hub`) is a lightweight, contract-only repository that holds cross-project OpenAPI schemas, global ADRs, and a coordination Kanban board. Five downstream implementation proposals (Step 2-6) all require this Hub to exist. Currently, no automated path exists to create and configure it — manual setup is required, creating a barrier to adoption.

This design addresses the bootstrap gap: a skill + init script that provisions the Hub repository with its directory structure, Projects V2 board, and workflow templates in a single idempotent operation.

## Goals / Non-Goals

**Goals:**
- Provide a single `init_hub.sh` command that creates and configures a Hub repository from scratch
- Ensure the script is idempotent: re-running against an existing Hub updates only missing pieces
- Support `--dry-run` mode for CI validation without making any GitHub API calls
- Minimize permissions required: Org member (not Owner) should suffice for all operations
- Produce an audit log (`rdd-hub-bootstrap.log`) for all operations

**Non-Goals:**
- Implementing the MCP Server itself (belongs to `add-mcp-cross-repo-protocol`)
- Integrating cross-project RFC发起流程 (belongs to `add-rdd-hub-cross-repo-federation`)
- Implementing full contract-lint CI (belongs to `add-contract-lint-ci-gate`)
- Creating Spoke-side System Prompt injection (belongs to `add-spoke-system-prompt-injection`)
- Automating spoke repository registration (future work)

---

## Decisions

### 1. Bash + `gh` CLI as the implementation language

**Decision:** `init_hub.sh` is implemented as a pure bash script that delegates GitHub API calls to the official `gh` CLI (v2.0+).

**Rationale:**
- bash is universally available on developer machines and in CI containers — no runtime installation required
- `gh` CLI handles authentication (`gh auth login`), pagination, and error handling for GitHub REST/GraphQL API
- Avoids Python/Node.js dependency chain for a one-shot bootstrap script
- The existing codebase already uses `gh` CLI in `install.sh` and other integration scripts — consistent toolchain

**Alternatives considered:**
- Pure Python (`requests`/`PyGithub`): Would require Python 3.11+ and pip install — adds friction for one-shot use
- GitHub REST API via `curl`: More error-prone, requires manual auth token management
- Terraform/Pulumi: Overkill for repository bootstrap; requires provider setup

---

### 2. Projects V2 via `gh project` GraphQL API

**Decision:** The six-field Kanban board ("RDD Cross-Repo Sync") is configured using `gh project` commands backed by GitHub GraphQL API, not the older Projects V1 API.

**Rationale:**
- GitHub Projects V2 is the current GA product; V1 is deprecated
- `gh project` CLI provides a managed interface without requiring raw GraphQL curl calls
- Field configuration (Status, Initiator, Stakeholders, Review-Progress, RDD-Gate, Contract-Impact) maps directly to `gh project field-create`

**Alternatives considered:**
- GitHub REST API (Projects V1): Deprecated, not worth targeting
- Third-party tools (Linear, Asana): Would break the GitHub-native workflow

---

### 3. Directory structure via `git init` + `mkdir` inside a local clone

**Decision:** `init_hub.sh` clones the (possibly empty) Hub repository, creates directories locally, commits, and pushes — rather than using GitHub API's directory creation.

**Rationale:**
- Keeps all file operations local and debuggable
- Git's local file operations are faster and more reliable than API-based alternatives
- `git add` + `git commit` + `git push` gives us automatic change tracking
- Templates are copied from `skills/rdd-hub-bootstrap/templates/` using standard `cp -r`

**Alternatives considered:**
- GitHub API tree creation via POST /repos/{owner}/{repo}/git/trees: More complex error handling, no local preview
- GitHub's "Create or update file" API: Requires base64 encoding; harder to debug

---

### 4. Idempotency via existence checks before each action

**Decision:** Each operation (repo creation, board creation, field creation, directory creation) is guarded by an existence check. If the resource already exists, the operation is skipped with a logged message.

**Rationale:**
- Bash conditional checks (`gh repo view`, `gh project list`) are fast and do not mutate state
- Skipping而非 erroring on existing resources makes the script safe to re-run
- Each skip is logged for auditability

**Existence checks:**
| Resource | Check Command |
|----------|---------------|
| GitHub Repo | `gh repo view {org}/{repo}` |
| Projects V2 Board | `gh project list --owner {org}` + grep |
| Workflow file | `test -f .github/workflows/{filename}` |
| Template directory | `test -d templates/{subdir}` |

---

### 5. Log file format: machine-parseable timestamped key=value lines

**Decision:** `rdd-hub-bootstrap.log` uses one line per event with format: `TIMESTAMP OPERATION=VALUE STATUS=VALUE [EXTRA=VALUE]`.

**Example:**
```
2026-08-16T10:30:00Z REPO_CREATE_ORG=my-org REPO_NAME=rdd-hub STATUS=created
2026-08-16T10:30:01Z BOARD_CREATE NAME="RDD Cross-Repo Sync" STATUS=skipped REASON=already_exists
```

**Rationale:**
- `grep`, `awk`, and shell conditionals can parse this format without external tools
- ISO 8601 timestamps are sortable
- Easily splittable to JSON if a log aggregation tool is adopted later

---

### 6. Skill file (`SKILL.md`) as a thin wrapper over `init_hub.sh`

**Decision:** `skills/rdd-hub-bootstrap/SKILL.md` documents usage and delegates to `scripts/init_hub.sh`. No separate skill-specific bash/python module is created.

**Rationale:**
- The skill is a bootstrap convenience, not a runtime component — once Hub is initialized, the skill is not invoked again
- Keeping logic in `init_hub.sh` makes the script portable and testable outside the skill framework
- bats tests can call `init_hub.sh` directly without involving `skill_use()`

---

## Risks / Trade-offs

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `gh auth` not configured on developer machine | Medium | Medium | Script detects missing auth and prints `gh auth login` instruction |
| Org member lacks permissions to create Projects V2 | Medium | High | Document minimum required permissions; script logs clear error |
| GitHub API rate limiting during dry-run | Low | Low | Dry-run path does not call GitHub API at all |
| Template files conflict with existing Hub content | Low | Low | `cp -i` prompts before overwrite; idempotent path uses `test -e` guard |
| `init_hub.sh` run outside the skill context | Low | Low | Script is fully self-contained and does not depend on skill framework |
| Race condition if two users run init simultaneously | Low | Low | Git push would fail; one user would retry after the other completes |
