# Design: fix-design-proposal-review-approved-parsing

## Context

`proposal-approved.md` is structured as two sections: `## 已批准提案` (approved, pending implementation) and `## 已实施` (approved and implemented). Three call sites parse it with `re.split(r"## 已实施", content)[0]`, which keeps only the part *before* `## 已实施` — i.e. only the `## 已批准提案` section. Historically, proposals were archived directly after approval and never lingered in the `已批准提案` section, so that section is effectively empty and all three parsers always see 0 approved entries:

- `skills/guide-design/scripts/design_proposal_review.sh:82` — misclassifies already-approved proposals as pending review.
- `skills/guide/scripts/scan-state.sh:276-278` — dashboard reports `approved: 0` (actual: 122+).
- `skills/propose/scripts/propose_change.py:436` — `create_skeleton_changes_for_approved` never sees approved entries.

`detect-suggestions-approved-inconsistency` (implemented 2026-07-29) fixed the data-view consistency between suggestions and approved files; this change fixes the parsing logic itself. The two are complementary.

## Decision

Extract a single pure-function helper and route all three call sites through it.

**Helper**: `skills/_lib/parse_approved.py`

```python
def parse_approved_proposals(path: str) -> list[str]:
    """Return approved proposal names from BOTH `## 已批准提案` and `## 已实施`
    sections, deduplicated, in file order. Missing/empty file -> []. Read-only."""
```

- Parses both sections and merges, deduplicating by name (same name in both sections yields one entry).
- Returns names in file-appearance order for deterministic output and easy testing.
- Never raises on missing or empty file; returns `[]`.
- Read-only: the helper never opens the file for writing.
- Docstring documents the both-sections design choice and the relationship to `detect-suggestions-approved-inconsistency`.

**Call-site rewiring** (all three replace their inline `re.split(...)[0]` logic with a helper call):

1. `skills/guide-design/scripts/design_proposal_review.sh` — replace the inline `python3 -c` heredoc with an invocation of the helper via the Oracle C1 env-var pattern (`PY_APPROVED_FILE="$APPROVED_FILE" python3 -c '...parse_approved...'`), no bash string interpolation.
2. `skills/guide/scripts/scan-state.sh` — same env-var pattern; `HAS_APPROVED` becomes `"yes"` iff the helper returns a non-empty list.
3. `skills/propose/scripts/propose_change.py` — replace the inline `re.split` with a direct import of `parse_approved_proposals`.

The helper path must be resolved identically in all three scripts (no path drift — see the AGENTS.md Round A `roadmap_exists` lesson).

## Non-goals

- No change to `proposal-approved.md` structure or to the semantics of `已批准提案` vs `已实施`.
- No changes to `update_proposal_status.py` migration logic or to `detect-suggestions-approved-inconsistency`.
- No new CLI command; the helper is internal.
- No new dependencies (stdlib `re` + `pathlib` only).

## Verification

- `tests/unit/test_parse_approved.py` (pytest): missing file, empty file, only `已批准提案` section, only `已实施` section, both sections with dedup.
- `tests/integration/test_approved_parsing_fix.bats` (bats): all three call sites —
  - `design_proposal_review.sh` lists 0 pending reviews in this repo (was ≥3 false positives),
  - `scan-state.sh` approved count reflects real entries (was 0),
  - `propose_change.py` approved check recognizes entries from both sections.
- `./test.sh --quick` green; net new lines < 100.

## Risks and Mitigations

- **Risk**: `scan-state.sh` now sees 122 `已实施` entries and always recommends `guide-plan`. **Mitigation**: accepted per proposal acceptance criteria — dashboard is expected to display the real count (122); consumption status is derived from `openspec/changes/` elsewhere, not from this parser.
- **Risk**: A fourth inline parser exists elsewhere and drifts. **Mitigation**: structural grep for `## 已实施` in `skills/` during implementation; any additional occurrence is rewired to the helper or explicitly noted as out of scope.
- **Risk**: Path resolution differs across the three scripts. **Mitigation**: single `resolve_rdd_lib_dir`-based lookup pattern shared by all call sites.
