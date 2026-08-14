## Context

`generate_full_proposal.py` is the D2 mapping function used by `guide-design` to convert `.rddf/improvements/<name>.md` 5-section format into a complete openspec `proposal.md`. Commit 132a654 (2026-08-04) fixed two bugs (header style support + Capabilities/Impact source derivation), but three gaps remain that this change addresses:

1. Numbered list items (`1. `, `2. `, etc.) are silently ignored — only `- ` bullets are extracted.
2. Missing scope sections emit `- (TBD)` — which reads as "to be determined" rather than "explicitly empty".
3. Capabilities and Impact still duplicate the same `constraint_items` list.

## Goals / Non-Goals

**Goals:**
- Recognize numbered list items as scope items (1./2./3. AND 1)/2)/3) formats).
- Attach indented sub-items to parent numbered item descriptions.
- Emit `- (no items specified)` for missing scope sections.
- Differentiate Capabilities (MUST items) from Impact (MUST NOT items).
- Preserve backward compatibility with existing 138+ bullet-style improvements files.

**Non-Goals:**
- Refactor the entire `generate_full_proposal.py` file.
- Modify `_extract_section()` signature.
- Modify the improvements file format requirements.
- Re-do commit 132a654's header-style fix.
- Introduce new dependencies (Python stdlib only).

## Decisions

### 1. Pattern detection: regex vs line-prefix match

Use a small set of prefix matches (`- `, `1. ` through `9. `, `1) ` through `9) `) rather than a full regex. This is sufficient for the well-defined markdown ordered/unordered list patterns and avoids regex overhead.

**Alternatives considered:**
- Full regex with `itertools.takewhile`: Rejected for complexity; the prefix-match approach is simpler and equally correct.
- Pure `re.match` for both bullet and numbered: Rejected to keep the parser readable in 1-2 lines.

### 2. Sub-item attachment logic

Indented sub-items (3+ spaces + `- `) following a numbered parent are concatenated to the parent item's description with `\n   - sub-item` preserved. This keeps the markdown structure intact when rendered.

**Alternatives considered:**
- Flatten sub-items into separate items: Rejected — loses the visual grouping of related capabilities.
- Drop sub-items entirely: Rejected — they're often the most information-dense content.

### 3. Capabilities/Impact split: MUST vs MUST NOT

Use a simple keyword check on the first non-whitespace word of each constraint item. If it starts with `MUST NOT`, route to `Impact`. Otherwise route to `Capabilities`. This is a coarse split but matches the existing `MUST`/`MUST NOT`/`SHOULD` semantic categories in the constraint section.

**Alternatives considered:**
- Manual classification by author: Rejected — defeats the purpose of automatic generation.
- Sentence-level NLP: Rejected — far too heavy for this scope.

### 4. Backward compatibility strategy

The new `_extract_scope_items()` implementation must continue to recognize `- ` bullet items as before. Existing 138+ files use this format, so any regression would break the round-trip property (item count match).

**Alternatives considered:**
- Two-pass parser with explicit format detection: Rejected — adds complexity for an uncommon case.
- Re-format all 138 files: Rejected — explicitly out of scope per the proposal.

## Risks / Trade-offs

- **Risk**: Numbered item sub-item attachment could produce multi-line strings that break opening tools. **Mitigation**: Existing constraint items already use this pattern (max 4 lines), so round-trip is tested.
- **Trade-off**: Capabilities/Impact split is coarse (MUST vs MUST NOT only). `SHOULD` items are silently dropped from Impact — acceptable for MVP, future proposal can refine.
- **Risk**: Item count assertion (line 9 of acceptance) could fail on edge cases where numbered items have unusual prefixes. **Mitigation**: The pytest fixture covers 5 format scenarios.
