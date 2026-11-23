# approved-proposal-parsing Specification

## Purpose
TBD - created by archiving change fix-design-proposal-review-approved-parsing. Update Purpose after archive.
## Requirements
### Requirement: Centralized approved-proposal parser
The system SHALL provide a pure, read-only helper `parse_approved_proposals(path: str) -> list[str]` in `skills/_lib/parse_approved.py` that returns approved proposal names from BOTH the `## 已批准提案` and `## 已实施` sections of `improvement-approved.md`, deduplicated, in file-appearance order.

#### Scenario: File does not exist
- GIVEN `improvement-approved.md` does not exist at the given path
- WHEN the helper is called
- THEN it returns an empty list without raising

#### Scenario: File is empty
- GIVEN `improvement-approved.md` exists but is empty
- WHEN the helper is called
- THEN it returns an empty list without raising

#### Scenario: Only the approved section has content
- GIVEN `improvement-approved.md` has entries only in the `## 已批准提案` section
- WHEN the helper is called
- THEN it returns all entries from that section

#### Scenario: Only the implemented section has content
- GIVEN `improvement-approved.md` has entries only in the `## 已实施` section
- WHEN the helper is called
- THEN it returns all entries from that section

#### Scenario: Both sections have content
- GIVEN `improvement-approved.md` has entries in both sections and one name appears in both
- WHEN the helper is called
- THEN it returns the merged entries deduplicated, in file-appearance order

### Requirement: All three call sites use the helper
The system SHALL route approved-proposal parsing in `skills/propose/scripts/propose_change.py` through the centralized helper（2026-11-20 部分退役：原并列的 `skills/guide-design/scripts/design_proposal_review.sh` 与 `skills/guide/scripts/scan-state.sh` 已随 ADR-0043 / ADR-0062 / ADR-0063 退役，无等价承接者），using the Oracle C1 env-var pattern (no bash string interpolation) in the shell call sites.
<!-- v4-residue:allow=rename-history -->

#### Scenario: Design review no longer lists implemented proposals as pending

> **RETIRED (2026-11-20, align-spec-residue-prior-18)** —— `design_proposal_review.sh` **不存在**（同 Requirement 正文的「2026-11-20 部分退役」注记：审查逻辑并入 `propose_quality_check.py`）；本 Scenario 描述的是已消失的脚本入口。保留原文作为历史记录。
- GIVEN `improvement-approved.md` has 122 approved entries all located in the `## 已实施` section
- WHEN `guide-design` Phase 3 runs `design_proposal_review.sh`
<!-- v4-residue:allow=history -->
- THEN it lists 0 already-approved proposals as pending review

#### Scenario: Dashboard reports the real approved count
- GIVEN the same `improvement-approved.md`
- WHEN `scan-state.sh` evaluates the approved-proposal signal
- THEN it detects approved entries instead of reporting 0

#### Scenario: Propose recognizes approved entries from both sections
- GIVEN an entry located in the `## 已实施` section
- WHEN `propose_change.py` checks whether a proposal is approved
- THEN it correctly recognizes the entry

### Requirement: Data structure and semantics preserved
The change SHALL NOT modify the `improvement-approved.md` file structure, and SHALL NOT alter the semantic definitions of the `## 已批准提案` and `## 已实施` sections.

#### Scenario: File structure untouched
- GIVEN the helper and rewired call sites are in place
- WHEN any workflow reads or writes `improvement-approved.md`
- THEN the two-section structure and section meanings remain unchanged

