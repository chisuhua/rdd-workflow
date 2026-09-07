# inline-ac-verifier-into-rdd-verifier Specification

## Purpose
TBD - created by archiving change inline-ac-verifier-into-rdd-verifier. Update Purpose after archive.
## Requirements
### Requirement: rdd-verifier SHALL self-contain its LLM verification protocol

The `rdd-verifier` skill SHALL inline its LLM verification protocol inside `skills/rdd-verifier/SKILL.md` as a single source of truth. The protocol SHALL specify AC extraction rules, evidence collection tool chain, verdict JSON schema, reasoning-keyword contract, and persistence protocol. The skill SHALL NOT depend on a separate `ac-verifier` sub-skill or any external LLM provider Python module to perform verification.

#### Scenario: Verification is performed by the executing AI agent

- **GIVEN** a project running `rdd-verifier` v2.0+
- **AND** the executing AI agent reads `skills/rdd-verifier/SKILL.md`
- **WHEN** the agent encounters the "LLM Verification Protocol" section
- **THEN** the agent SHALL use only the tools declared in the protocol (Read, Grep, Glob, Bash, codegraph_explore) to gather evidence per AC
- **AND** the agent SHALL emit a strict JSON verdict array whose length equals the AC count
- **AND** the agent SHALL NOT shell out to `ac-verifier/scripts/ac_verifier.sh` or any external LLM provider SDK

#### Scenario: No `AC_LLM_*` environment variables are required

- **GIVEN** a project running `rdd-verifier` v2.0+ in CI
- **AND** no `AC_LLM_PROVIDER`, `AC_LLM_API_KEY`, `AC_LLM_BASE_URL`, `AC_LLM_MODEL`, `AC_LLM_TIMEOUT`, `AC_LLM_MAX_RETRIES`, or `AC_LLM_MOCK` is set
- **WHEN** `rddf rdd-verify` runs against an implemented change
- **THEN** verification proceeds normally using the executing AI agent
- **AND** no `AcVerifierError` is raised for missing provider configuration

### Requirement: rdd-verifier LLM Verification Protocol SHALL define a strict verdict JSON schema

The "LLM Verification Protocol" section of `skills/rdd-verifier/SKILL.md` SHALL define a verdict JSON schema with the following fields per AC entry: `ac_id` (string matching `^AC-\d+$`), `description` (string, verbatim AC text), `status` (enum: `pass` | `fail` | `partial`), `confidence` (number 0.0-1.0), `evidence` (array of tool invocation records), `reasoning` (string). The verdict SHALL be a JSON array whose length equals the AC count.

#### Scenario: Verdict array length mismatch fails validation

- **GIVEN** a proposal with 5 acceptance criteria
- **WHEN** the agent emits a verdict array of length 4
- **THEN** the verifier MUST auto-fill the missing AC entry as `{status: "fail", confidence: 0.0, reasoning: "AI omitted this AC from verdict"}`
- **AND** the verdict is recorded as `failed` state

#### Scenario: Verdict entry has invalid status enum

- **GIVEN** an AC entry with `"status": "uncertain"`
- **WHEN** the verdict is parsed
- **THEN** the verifier MUST treat the entry as `fail`
- **AND** log a schema-validation warning to the audit log

### Requirement: rdd-verifier verdict reasoning SHALL embed heuristic classifier keywords

The agent's verdict reasoning field SHALL embed at least one of the documented drift or gap keywords so that `_lib/verifier/classify.py::classify_failure` continues to function without modification. Drift keywords checked first (`exists but`, `discrepan`, `mismatch`, `differs from ac`) route to `proposal_drift`. Gap keywords (`not implement`, `missing`, `absent`, `todo: implement`) route to `implementation_gap`. Ambiguous reasoning defaults conservatively to `implementation_gap`.

#### Scenario: Drift keyword triggers proposal_drift routing

- **GIVEN** a failed AC verdict with reasoning "Code exists but does not match AC description"
- **WHEN** `classify_failure` is invoked
- **THEN** the function returns `proposal_drift`
- **AND** the verifier routes the change back to `guide-plan`

#### Scenario: Gap keyword triggers implementation_gap routing

- **GIVEN** a failed AC verdict with reasoning "Method is missing from the implementation"
- **WHEN** `classify_failure` is invoked
- **THEN** the function returns `implementation_gap`
- **AND** the verifier routes the change back to `guide-ship`

#### Scenario: Ambiguous reasoning defaults to implementation_gap

- **GIVEN** a failed AC verdict with reasoning that contains no documented keyword
- **WHEN** `classify_failure` is invoked
- **THEN** the function returns `implementation_gap` (conservative default)

### Requirement: rdd-verifier SHALL persist verdicts to the SHA-bound cache and audit log

After LLM verification, the agent SHALL write the verdict to `.rddf/state/.ac-verdict-<change>.json` (cache schema v2) and append an entry to `.rddf/state/.ac-verification.jsonl` (audit log schema v1). The cache file MUST bind to the current `git rev-parse HEAD` commit SHA. If the cache file already exists with a matching SHA, the agent SHALL NOT overwrite it.

#### Scenario: Cache hit short-circuits LLM verification

- **GIVEN** `.rddf/state/.ac-verdict-<change>.json` exists with `codebase_commit` equal to current HEAD
- **AND** the cached verdict contains no failed ACs
- **WHEN** `rddf rdd-verify` runs for that change
- **THEN** the LLM verification is skipped
- **AND** the cached verdict is returned

#### Scenario: Cache stale re-runs LLM verification

- **GIVEN** `.rddf/state/.ac-verdict-<change>.json` exists with `codebase_commit` different from current HEAD
- **WHEN** `rddf rdd-verify` runs for that change
- **THEN** a warning is emitted that the cache is stale
- **AND** LLM verification runs fresh
- **AND** the new verdict overwrites the stale cache entry

#### Scenario: Cache write is non-optional

- **GIVEN** LLM verification completes with a successful verdict
- **WHEN** the agent attempts to write the cache file
- **THEN** a cache write failure MUST be reported as exit code 3
- **AND** the archive gate MUST NOT consider verification passed

### Requirement: archive_gate_check SHALL NOT shell out to ac-verifier

The `_lib/archive.sh::archive_gate_check` function SHALL consume only the canonical SHA-bound verdict cache. It SHALL NOT invoke `ac-verifier/scripts/ac_verifier.sh` as a fallback. If the cache is missing or stale, the gate MUST fail closed unless `SKIP_RDD_VERIFIER=yes` and `RDDF_VERIFIER_BYPASS_REASON` are both set.

#### Scenario: Cache missing without bypass fails closed

- **GIVEN** `.rddf/state/.ac-verdict-<change>.json` does not exist
- **AND** `SKIP_RDD_VERIFIER` is unset
- **WHEN** `archive_gate_check` runs
- **THEN** the gate fails with a clear error message pointing to `rddf rdd-verify`
- **AND** archive is blocked

#### Scenario: Cache missing with audited bypass succeeds

- **GIVEN** `.rddf/state/.ac-verdict-<change>.json` does not exist
- **AND** `SKIP_RDD_VERIFIER=yes` and `RDDF_VERIFIER_BYPASS_REASON="emergency hotfix: ..."` are set
- **WHEN** `archive_gate_check` runs
- **THEN** the gate records the bypass in the audit log
- **AND** archive proceeds with `verification.state = bypassed`

#### Scenario: STRICT_AC_GATE escalates failed verdict to archive blocker

- **GIVEN** `.rddf/state/.ac-verdict-<change>.json` exists with `verification_state: "failed"`
- **AND** `STRICT_AC_GATE=yes` is set
- **WHEN** `archive_gate_check` runs
- **THEN** the gate fails with a `❌ STRICT_AC_GATE` message
- **AND** archive is blocked

### Requirement: rdd-verifier SHALL redefine exit code 3

The `rddf rdd-verify` exit code 3 SHALL mean "LLM verification error": the executing agent failed to produce a verdict due to context overflow, all tool calls failed, or unrecoverable reasoning failure. Exit codes 0, 1, 2, and 4 retain their previous semantics (pass, fail with route, skip, halted).

#### Scenario: Agent context overflow exits 3

- **GIVEN** a change with 50+ acceptance criteria
- **WHEN** the agent exhausts its context window while reading code
- **THEN** the verifier exits with code 3
- **AND** the audit log records an `errored` event

#### Scenario: Agent tool failure exits 3

- **GIVEN** the agent attempts to read proposal.md
- **AND** the file does not exist
- **AND** retry attempts also fail
- **WHEN** the verifier completes its error-handling loop
- **THEN** the verifier exits with code 3
- **AND** the audit log records an `errored` event

### Requirement: ac-verifier SHALL be marked deprecated

The `skills/ac-verifier/SKILL.md` SHALL carry a deprecation notice visible at the top of the document. The frontmatter SHALL set `user-invocable: false`. The `metadata.deprecated` block SHALL include `deprecated_in`, `deprecated_by`, `reason`, `removal_target`, and `migration` fields. The ac-verifier scripts SHALL continue to function as a backward-compatibility shim for `rddf ac-verify <change>` for at least one release cycle.

#### Scenario: User invokes ac-verifier skill directly

- **GIVEN** a user runs `skill_use("ac-verifier", "<change>")`
- **WHEN** the skill is loaded
- **THEN** the deprecation banner is the first content the user sees
- **AND** the skill continues to execute via the shim

#### Scenario: rddf ac-verify CLI continues to work

- **GIVEN** a user runs `rddf ac-verify <change>` on a project with rdd-verifier v2.0 installed
- **WHEN** the CLI is invoked
- **THEN** it delegates to `_lib/cli/rdd_verify_cmd.py::cmd_rdd_verify(<change> --single)`
- **AND** the CLI exits with the rdd-verifier exit code (0/1/2/3)

### Requirement: deprecation period SHALL be at least one release cycle

The ac-verifier skill and its underlying scripts SHALL NOT be removed in this change. Removal is targeted for the next minor release after rdd-verifier v2.0 lands. The `metadata.deprecated.removal_target` field SHALL record the target version.

#### Scenario: Deprecation target is recorded

- **GIVEN** the ac-verifier SKILL.md frontmatter
- **WHEN** an AI assistant reads it
- **THEN** the `metadata.deprecated.removal_target` field SHALL be populated
- **AND** the value SHALL reference the next minor release after rdd-verifier v2.0

#### Scenario: Deprecation is visible in package.json skills list

- **GIVEN** `package.json` `skills` field includes `"ac-verifier"`
- **WHEN** an installer reads the package
- **THEN** the ac-verifier entry SHALL be present (not yet removed)
- **AND** a follow-up change SHALL remove it after the deprecation window closes

