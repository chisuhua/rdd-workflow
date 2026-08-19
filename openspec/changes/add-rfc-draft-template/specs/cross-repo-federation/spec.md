## ADDED Requirements

### Requirement: 5-Section RFC Draft Template

When `detect_cross_repo_impact.py` flags a proposal as cross-repo, it MUST append a 5-section template to `.rddf/improvements/<name>.md` covering motivation, contract draft, stakeholders, compatibility strategy, and rollback plan.

#### Scenario: Template sections appear in correct order
**WHEN** `add-improve <name>` triggers cross-repo detection and template generation

**THEN** `.rddf/improvements/<name>.md` MUST end with 5 sections in order: `## 变更动机`, `## 契约草案`, `## 影响仓库`, `## 兼容策略`, `## 回滚方案`

**AND** the `## 影响仓库` section MUST be pre-populated with detected stakeholders

#### Scenario: Existing proposal content is preserved
**WHEN** `.rddf/improvements/<name>.md` already has custom content beyond the head fields

**THEN** template generation MUST append (not overwrite) the 5 sections at the end

**AND** MUST NOT modify existing head fields

### Requirement: Contract Draft Inline in Hub Issue Body

`rddf report-issue --contract-draft <path>` MUST base64-encode the contract file and inline it inside the Hub Issue body's `<details>` block so Hub stakeholders can preview the contract without running `sync-hub`.

#### Scenario: --contract-draft accepts local file path
**WHEN** user runs `rddf report-issue --contract-draft .rddf/improvements/<name>/contract.yaml`

**THEN** the Hub Issue body MUST contain a `<details><summary>Contract draft</summary>` block with base64-encoded YAML

**AND** the Issue creation MUST succeed (or fail with the standard rate-limit / network error taxonomy)

#### Scenario: --contract-draft file size limit
**WHEN** the contract file exceeds 48 KB (≈ 64 KB base64)

**THEN** `report_issue_rfc.py` MUST refuse with exit code 4 and message `ERROR: contract draft too large (<size> bytes; limit 49152)`
