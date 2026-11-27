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

A missing scope section (`In Scope` / `Out Scope`) MUST render as `- (no items specified)`, never as `- (TBD)`. A scope section that is present but yields no parseable items MUST be preserved verbatim with a stderr diagnostic — never guessed by splitting on commas.

#### Scenario: missing Out Scope section

- GIVEN an improvements file with `### In Scope` items but no `### Out Scope` section
- WHEN `generate_full_proposal()` builds the proposal draft
- THEN `Out of Scope` block contains `- (no items specified)`

#### Scenario: missing In Scope section

- GIVEN an improvements file with `### Out Scope` items but no `### In Scope` section
- WHEN `generate_full_proposal()` builds the proposal draft
- THEN `In Scope` block contains `- (no items specified)`

#### Scenario: unparseable scope section is preserved verbatim

- GIVEN an improvements file whose scope section yields no parseable items
- WHEN `generate_full_proposal()` builds the proposal draft
- THEN the corresponding scope block contains the original section text **unchanged**
- AND a diagnostic line naming the affected section is written to stderr
- AND the draft contains no comma-split fragments

### Requirement: generate-proposal-capabilities-impact-distinct

The `Capabilities` and `Impact` sections in the generated `proposal.md` MUST contain distinct content, not duplicating the same constraint items.

#### Scenario: Capabilities and Impact differ when MUST and MUST NOT present

- GIVEN an improvements file with both `MUST` and `MUST NOT` constraints
- WHEN `generate_full_proposal()` builds the proposal draft
- THEN `Capabilities` contains only `MUST` items
- AND `Impact` contains only `MUST NOT` items
- AND the two sections are not identical

### Requirement: generate-proposal-backward-compatible

Bullet-based improvements MUST keep producing at least as many `In Scope` items as before. Corpus regression MUST be asserted by a checked-in **golden snapshot** (never a difference allow-list of file names) that carries its generation timestamp and a **dynamic** corpus count, and is refreshed in the same pull request whenever the corpus grows.

#### Scenario: bullet-only file produces same item count

- GIVEN an improvements file with `### In Scope` (H3) + 5 `- ` bullet items
- WHEN `generate_full_proposal()` builds the proposal draft
- THEN the `In Scope` block contains exactly 5 items

#### Scenario: corpus snapshot carries dynamic metadata

- GIVEN the stored corpus snapshot for the proposals corpus
- WHEN the snapshot metadata is inspected
- THEN it records a generation timestamp and the corpus item count measured at generation time
- AND the recorded count is not a hard-coded constant

### Requirement: generate-proposal-table-scope-items

The `generate_full_proposal._extract_scope_items()` function MUST recognise markdown table rows as scope items, subject to an explicit attribution rule: a table in a scope section that contains **no** bullet or numbered item yields **one item per table row** (alignment rows excluded), whereas a table that appears **under an existing bullet or numbered item** remains attached to that item.

#### Scenario: table-only scope section yields one item per row

- GIVEN an improvements file whose `In Scope` section contains only a markdown table with 3 data rows
- WHEN `_extract_scope_items()` extracts the scope section
- THEN `in_scope_items` contains exactly 3 items, one per data row
- AND no item contains a `|` character or an embedded line break

#### Scenario: table under a bullet stays attached to that bullet

- GIVEN an improvements file whose scope section contains a bullet item followed by an indented markdown table
- WHEN `_extract_scope_items()` extracts the scope section
- THEN the table rows remain part of the preceding bullet item
- AND no additional standalone items are produced

### Requirement: generate-proposal-scope-header-annotation

The scope-header matcher MUST recognise scope headers that carry a trailing annotation (for example `**In Scope（6 项 · contract 面）**`), and MUST NOT treat such a header line as a scope item.

#### Scenario: annotated scope header is not an item

- GIVEN an improvements file whose scope section starts with `**In Scope（6 项 · contract 面）**`
- WHEN `_extract_scope_items()` extracts the scope section
- THEN the annotated header is recognised as a header
- AND the header line does NOT appear among the extracted items

### Requirement: generate-proposal-section-precedence

When an improvements file contains both a `范围` section and a `What Changes` section, the generator MUST use the section that comes first in the documented candidate order (`范围` → `What Changes` → `Scope`) and MUST write a diagnostic line to stderr naming the ambiguity.

#### Scenario: both scope sections present

- GIVEN an improvements file containing both `## 范围` and `## What Changes` sections
- WHEN `generate_full_proposal()` builds the proposal draft
- THEN the `## 范围` content is used (candidate order)
- AND a diagnostic line naming the ambiguity is written to stderr

#### Scenario: only the English section present

- GIVEN an improvements file containing only a `## What Changes` section
- WHEN `generate_full_proposal()` builds the proposal draft
- THEN the `## What Changes` content is used
