# generator-scope-extraction Specification

## Purpose
TBD - created by archiving change fix-generator-scope-extraction. Update Purpose after archive.
## Requirements
### Requirement: generate-proposal-supports-numbered-scope-items

The `generate_full_proposal._extract_scope_items()` function MUST recognize numbered list items (`1. `, `2. `, `3. `, `1) `, `2) `) as scope items, in addition to the existing `- ` bullet items.

#### Scenario: numbered items classified as in-scope

- GIVEN an improvements file with `### In Scope` (H3) header followed by `1. **first item**:` and `2. **second item**:` lines
- WHEN `_extract_scope_items()` extracts the scope section
- THEN `in_scope_items` contains both items in order
- AND `out_scope_items` is empty

#### Scenario: numbered items classified as out-of-scope

- GIVEN an improvements file with `### Out Scope` (H3) header followed by `1. **deferred item**:` and `2. **out-of-scope**:` lines
- WHEN `_extract_scope_items()` extracts the scope section
- THEN `out_scope_items` contains both items
- AND `in_scope_items` is empty

### Requirement: generate-proposal-numbered-item-subitems-attached

The `_extract_scope_items()` function MUST attach indented sub-items (e.g., `   - sub-item`) to the parent numbered item's description, preserving the `\n   - sub-item` markdown format.

#### Scenario: numbered item with indented sub-items

- GIVEN an improvements file with:
  ```
  1. **stdout/stderr 透传**:
     - 主进程透传
     - 后台异步
  ```
- WHEN `_extract_scope_items()` extracts the scope section
- THEN the resulting item is one string containing `**stdout/stderr 透传**:\n   - 主进程透传\n   - 后台异步`

### Requirement: generate-proposal-empty-section-fallback

When a scope section (`In Scope` or `Out Scope`) is completely missing from the improvements input, the generated `proposal.md` MUST emit `- (no items specified)` for the missing section instead of `- (TBD)`.

#### Scenario: missing Out Scope section

- GIVEN an improvements file with `### In Scope` items but no `### Out Scope` section
- WHEN `generate_full_proposal()` builds the proposal draft
- THEN `Out of Scope` block contains `- (no items specified)`

#### Scenario: missing In Scope section

- GIVEN an improvements file with `### Out Scope` items but no `### In Scope` section
- WHEN `generate_full_proposal()` builds the proposal draft
- THEN `In Scope` block contains `- (no items specified)`

### Requirement: generate-proposal-capabilities-impact-distinct

The `Capabilities` and `Impact` sections in the generated `proposal.md` MUST contain distinct content, not duplicating the same constraint items.

#### Scenario: Capabilities and Impact differ when MUST and MUST NOT present

- GIVEN an improvements file with both `MUST` and `MUST NOT` constraints
- WHEN `generate_full_proposal()` builds the proposal draft
- THEN `Capabilities` contains only `MUST` items
- AND `Impact` contains only `MUST NOT` items
- AND the two sections are not identical

### Requirement: generate-proposal-backward-compatible

Existing improvements files (138+ files) using `- ` bullet items MUST continue to produce `## What Changes` with `In Scope` items count >= original improvements' `In Scope` items count.

#### Scenario: bullet-only file produces same item count

- GIVEN an improvements file with `### In Scope` (H3) + 5 `- ` bullet items
- WHEN `generate_full_proposal()` builds the proposal draft
- THEN the `In Scope` block contains exactly 5 items

